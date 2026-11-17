"""Processo di aggiornamento (container "worker").

  previsioni meteo       ogni ORE_PREVISIONI ore      } solo i comuni delle REGIONI_AGGIORNATE (vuoto = tutte le
  storico meteo          ogni giorno dopo ORA_STORICO_UTC } REGIONI servite); giornaliero aggiornato a blocchi di comuni
  archivio psicrometrico ogni giorno subito dopo lo storico: ore nuove di temperatura e umidità in CARTELLA_PSICRO
                         (ICON del server, poi ERA5 da S3 per gli altri comuni); niente se la cartella non c'è
  mercati (GME, TTF)     ogni notte alle ORA_MERCATI (ora italiana), con la sorveglianza delle fonti delle
                         convenzioni (email solo quando cambia qualcosa), i listini delle convenzioni e, subito dopo,
                         gli indici dei prezzi pubblicabili per il sito (prezzi: /sito/dati/prezzi/indici.json)
  newsletter dei dati    mensile, il giorno NOTIZIARIO_GIORNO (listmonk; dal 14/11/2026 un messaggio per iscritto con
                         le sue regioni)
  previsioni per email   ogni settimana, giorno SETTIMANALE_GIORNO dalle SETTIMANALE_ORA: la settimana dopo per i comuni
                         di ogni iscritto (14/11/2026)
  avvisi meteo           ogni giorno dalle AVVISI_ORA: pioggia forte, neve, vento molto forte domani nei comuni scelti
  verifica territorio    il 2 di ogni mese: nuovi comuni ISTAT o nuova versione dei confini Gramscii
  indirizzario ANNCSU    il giorno ANNCSU_GIORNO di ogni mese (o subito, se manca): civici georeferenziati
  indicatori sanità      il giorno INDICATORI_GIORNO di ogni mese, dalle 6 (fase 8: OpenBDAP, ReportER, ISTAT)
  clima dal 1940         nei giorni CLIMA_DATE (10/1 e 10/7), dalle 3 (fase 9: ERA5 dai file .om su AWS)
  rete: interruzioni     ogni RETE_INTERRUZIONI_MIN minuti (15), in un thread a parte, così i lavori lunghi non le
                         fermano (17/11/2026, servizio/rete.py, database RETE_DB)
  rete: saturazione      ogni notte alle RETE_SATURAZIONE_ORA (01:15, ora italiana): comuniServiti per tutte le province,
                         comuni gestiti da e-distribuzione, elenco delle province; subito se il database non ne ha ancora
                         (email solo se interruzioni non lette, o più di 5 province ferme, da più di 72 ore)
I file del sito (indicatori, clima) si scrivono in una cartella nuova e si scambiano con quella pubblicata solo a
lavoro finito e controllato: se qualcosa va storto restano quelli di prima.
Gli errori vengono segnalati per email all'amministratore (EMAIL_AMMINISTRATORE).

  python -m servizio.worker                 ciclo continuo
  python -m servizio.worker previsioni|storico|psicro|mercati|prezzi|mensile|settimanale|avvisi|territorio|anncsu|indicatori|clima
                            |rete-interruzioni|rete-saturazione
                                            una sola esecuzione (anche con docker compose run --rm worker …)
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from . import avvisi, config as C, meteo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("worker")
ROMA = ZoneInfo("Europe/Rome")


def _sicuro(f, nome) -> bool:
    try:
        f()
        return True
    except Exception as e:
        log.exception("Errore in %s", nome)
        avvisi.invia(f"errore in {nome}", f"{type(e).__name__}: {e}")
        return False


def psicro() -> dict:
    """Archivio psicrometrico (14/11/2026, menu «Trattamento aria»): aggiunge le ore nuove ai file di CARTELLA_PSICRO.
    Prima le ore ICON appena aggiunte dallo storico in DATI/orario (comuni di REGIONI_AGGIORNATE), poi, per i comuni
    rimasti indietro, ERA5/ERA5-Land dai file .om su S3 (~5 giorni di ritardo; PSICRO_S3=false lo spegne). Senza la
    cartella (archivio non ancora copiato) o mentre `scarica-psicro` ci sta scrivendo non fa nulla."""
    if not C.CARTELLA_PSICRO.is_dir():
        log.info("Archivio psicrometrico: cartella %s assente, niente da aggiornare", C.CARTELLA_PSICRO)
        return {"saltato": "cartella assente"}
    from meteo_storico import psicro as ps
    esito = ps.aggiorna(C.CARTELLA_PSICRO, C.DATI / "orario", usa_s3=C.PSICRO_S3, giorni_max=C.PSICRO_GIORNI_MAX)
    log.info("Archivio psicrometrico: %s", esito)
    return esito


def mercati() -> None:
    from mercati_energia import notturno
    from mercati_energia.config import carica
    esito = notturno.esegui(carica(C.MERCATI_CONFIG))
    # credenziali GME non ancora inserite: è una configurazione, non un guasto, quindi niente email ogni notte
    errori = [e for e in esito["errori"] if not str(e).startswith("Credenziali GME mancanti")]
    if len(errori) < len(esito["errori"]):
        log.info("Mercati: GME saltato, credenziali non configurate")
    if errori:
        avvisi.invia("dati di mercato: aggiornamento incompleto", json.dumps(esito, indent=1, default=str))
    _sicuro(prezzi, "indici dei prezzi")      # un errore qui non ferma l'avviso della sorveglianza
    s = esito.get("sorveglianza") or {}
    if s.get("da_segnalare"):
        from mercati_energia.sorveglianza import riepilogo
        avvisi.invia("convenzioni e fonti: novità", riepilogo(s))


def prezzi() -> None:
    """Indici dei prezzi pubblicabili (11/11/2026): listini delle convenzioni, PSV ARERA, PFOR ricostruito, mai PUN né
    TTF. File del sito /sito/dati/prezzi/indici.json, letto dalla pagina Statistiche › Indici dei prezzi e dalla
    newsletter. Gira dopo i mercati di ogni notte (e da solo con `python -m servizio.worker prezzi`)."""
    if not Path(C.MERCATI_CONFIG).exists():          # mirror o prove senza dati di mercato: niente file, niente email
        log.info("Indici dei prezzi: configurazione dei mercati assente (%s)", C.MERCATI_CONFIG)
        return
    from mercati_energia import prezzi_pubblici
    from mercati_energia.config import carica
    cfg = carica(C.MERCATI_CONFIG)
    dati = prezzi_pubblici.scrivi(cfg.cartella, cfg.convenzioni, C.SITO_DATI / "prezzi" / "indici.json")
    log.info("Indici dei prezzi: %s", {s["id"]: len(s["indici"]) for s in dati["sezioni"]})


def mensile() -> None:
    from . import notiziario as n
    n.mensile()


def settimanale() -> None:
    """Previsioni della settimana dopo per i comuni di ogni iscritto (14/11/2026)."""
    from . import notiziario as n
    if C.NOTIZIE_PERSONALI and n.L.attivo():
        n.settimanale()


def avvisi_meteo() -> None:
    """Avvisi meteo per domani: pioggia forte, neve, vento molto forte (14/11/2026; non sono allerte)."""
    from . import notiziario as n
    if C.NOTIZIE_PERSONALI and n.L.attivo():
        n.avvisi_meteo()


def territorio() -> None:
    import pandas as pd
    from meteo_storico import territorio as t
    v = t.verifica(pd.read_parquet(C.DATI / "comuni.parquet"))
    if v["da_aggiornare"]:
        avvisi.invia("comuni o confini da aggiornare",
                     "Variazioni rilevate (rieseguire la fase 3 `comuni` e `territorio-blocca`):\n"
                     + json.dumps(v, indent=1, ensure_ascii=False))


def anncsu() -> None:
    """Riscarica l'indirizzario nazionale (~270 MB, ~1 minuto di conversione); lo ZIP si cancella dopo."""
    from territorio import anncsu as a
    dest = C.ANNCSU_FILE.parent
    a.scarica(dest)
    (dest / "anncsu_INDIR_ITA.zip").unlink(missing_ok=True)
    # stessa cadenza mensile: via dalla cache le ricerche Zornade più vecchie di un anno (informativa privacy)
    from territorio.zornade import pulisci_cache
    log.info("Cache Zornade: %d risposte scadute cancellate", pulisci_cache(C.DATI / "cache_zornade.sqlite", 365))


def _pubblica(nuova: Path, finale: Path) -> None:
    """Sostituisce la cartella pubblicata `finale` con `nuova` (stesso disco: due rename, il sito resta senza la
    cartella per qualche microsecondo); la vecchia si cancella dopo."""
    vecchia = finale.with_name(f".{finale.name}_vecchia")
    shutil.rmtree(vecchia, ignore_errors=True)
    if finale.exists():
        finale.rename(vecchia)
    nuova.rename(finale)
    shutil.rmtree(vecchia, ignore_errors=True)


def _conta_json(cartella: Path) -> int:
    return sum(1 for _ in cartella.rglob("*.json")) if cartella.exists() else 0


def indicatori() -> None:
    """Indicatori della sanità (fase 8): CE OpenBDAP, ReportER, ISTAT → JSON statici del sito (dati/indicatori/).
    Se una fonte manca, cli.aggiorna solleva FonteNonDisponibile: email all'amministratore, file del mese prima."""
    from indicatori_ssn import cli
    finale = C.SITO_DATI / "indicatori"
    nuova = C.SITO_DATI / ".indicatori_nuova"
    shutil.rmtree(nuova, ignore_errors=True)
    esito = cli.aggiorna(nuova, C.DATI / "indicatori_cache", rinnova=True, pausa=2.0)
    if not (nuova / "indice.json").exists() or _conta_json(nuova) < 0.9 * _conta_json(finale):
        raise RuntimeError(f"indicatori: file nuovi incompleti ({_conta_json(nuova)} contro {_conta_json(finale)})")
    _pubblica(nuova, finale)
    log.info("Indicatori: %d file, %d byte", len(esito["dimensioni"]), sum(esito["dimensioni"].values()))


def clima() -> None:
    """Clima dal 1940 (fase 9). Aggiorna la cache giornaliera per cella con l'anno in corso (e i mancanti) dai file
    .om di Open-Meteo su AWS, ricalcola gli indicatori di tutti i comuni (~5 min, ~1,5 GB di RAM) e pubblica
    dati/clima/ e i due CSV nazionali. In processi separati, così la memoria torna libera alla fine.
    La prima volta (cache vuota) scarica tutto: ~1 ora e 27 GB letti da S3, 630 MB su disco."""
    L = C.CLIMA_LAVORO
    comuni = L / "comuni.parquet"
    if not comuni.exists():
        raise FileNotFoundError(f"manca {comuni}: copiarlo dal PC (README della fase 9)")
    L.mkdir(parents=True, exist_ok=True)
    py = [sys.executable]
    subprocess.run(py + [str(C.CLIMA_CODICE / "scarica.py"), "--log", str(L / "scarica.log"), "meteo",
                         "--cache", str(L / "cache"), "--comuni", str(comuni), "--aggiorna"], check=True)
    tmp = C.SITO_DATI / ".clima_nuova"       # stesso disco della cartella pubblicata: il rename è immediato
    shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run(py + [str(C.CLIMA_CODICE / "calcola.py"), "--cache", str(L / "cache"), "--comuni", str(comuni),
                         "--uscita", str(tmp), "--dpr", str(C.SITO_DATI / "dpr412.json")], check=True)
    finale = C.SITO_DATI / "clima"
    n_nuovi, n_vecchi = _conta_json(tmp / "clima"), _conta_json(finale)
    if not (tmp / "clima" / "indice.json").exists() or n_nuovi < 0.99 * n_vecchi:
        raise RuntimeError(f"clima: file nuovi incompleti ({n_nuovi} contro {n_vecchi}), pubblicati quelli di prima")
    (tmp / "clima_mensili.parquet").replace(L / "clima_mensili.parquet")    # 83 MB, non serve al sito
    _pubblica(tmp / "clima", finale)
    for nome in ("clima_stagioni.csv", "clima_sintesi.csv"):
        (tmp / nome).replace(C.SITO_DATI / nome)
    shutil.rmtree(tmp, ignore_errors=True)
    log.info("Clima dal 1940: %d file pubblicati", n_nuovi)


def rete_interruzioni() -> dict:
    """Una lettura delle interruzioni in corso di e-distribuzione (17/11/2026, servizio/rete.py)."""
    from . import rete
    return rete.raccogli_interruzioni()


def rete_saturazione() -> dict:
    """Saturazione dei trasformatori per tutte le province, comuni gestiti, province (17/11/2026). Le province che non
    rispondono (Torino: 500 dal 17/11/2026) si ritentano alla fine e ogni notte. Email (decisione di Paolo del 17/11)
    SOLO se più di RETE_AVVISO_PROVINCE province non sono aggiornate con successo da più di RETE_AVVISO_ORE ore
    consecutive, una volta per episodio; gli altri errori vanno solo nel registro (mai in _sicuro, che manda email)."""
    from . import rete
    try:
        esito = rete.aggiorna_saturazione()
    except Exception as e:
        log.exception("Saturazione: giro notturno non riuscito")
        try:
            rete.segna_giro_fallito(f"{type(e).__name__}: {e}")
        except Exception:
            log.exception("Saturazione: errore non registrato nel database")
        esito = {"errore": f"{type(e).__name__}: {e}"}
    try:
        ferme = rete.province_ferme()
        if rete.avviso_una_volta("province", len(ferme) > C.RETE_AVVISO_PROVINCE):
            avvisi.invia(f"rete elettrica: {len(ferme)} province non aggiornate da più di {C.RETE_AVVISO_ORE:g} ore",
                         "Province (ISTAT) senza saturazione aggiornata: " + ", ".join(ferme)
                         + "\n\nUltimo giro: " + json.dumps(esito, indent=1, ensure_ascii=False, default=str))
        esito["ferme_72h"] = ferme
    except Exception:
        log.exception("Saturazione: controllo delle province ferme non riuscito")
    return esito


class _Errori:
    """Letture delle interruzioni fallite (decisione di Paolo del 17/11/2026): un'email SOLO quando non si leggono da più
    di RETE_AVVISO_ORE ore consecutive (dall'ultima lettura riuscita, presa dal database all'avvio), una per episodio;
    nessuna email quando ripartono né per errori più brevi."""
    def __init__(self, ultimo_ok: float | None = None, ore: float | None = None):
        self.ore = C.RETE_AVVISO_ORE if ore is None else ore
        self.ultimo_ok = time.time() if ultimo_ok is None else ultimo_ok
        self.n, self.avvisato = 0, False

    def esegui(self, f, adesso: float | None = None) -> bool:
        adesso = time.time() if adesso is None else adesso
        try:
            f()
        except Exception as e:
            self.n += 1
            log.warning("Interruzioni: lettura fallita (%d di fila): %s: %s", self.n, type(e).__name__, e)
            if not self.avvisato and adesso - self.ultimo_ok > self.ore * 3600:
                self.avvisato = True
                avvisi.invia(f"rete elettrica: interruzioni non lette da più di {self.ore:g} ore",
                             f"{self.n} letture fallite di fila; ultimo errore: {type(e).__name__}: {e}")
            return False
        self.n, self.avvisato, self.ultimo_ok = 0, False, adesso
        return True


def prossima_lettura(adesso: float, minuti: int, scarto_s: int = 180) -> float:
    """Prossimo istante multiplo di `minuti` più `scarto_s` (la mappa di e-distribuzione si aggiorna al minuto 1)."""
    passo = minuti * 60
    t = (adesso - scarto_s) // passo * passo + passo + scarto_s
    return t if t > adesso else t + passo


def ciclo_interruzioni(fermo: threading.Event | None = None) -> None:
    ultimo = None
    try:
        from . import rete
        u = rete.ultima_lettura_ok()
        ultimo = u.timestamp() if u else None
    except Exception:
        pass
    errori = _Errori(ultimo_ok=ultimo)
    fermo = fermo or threading.Event()
    while not fermo.is_set():
        errori.esegui(rete_interruzioni)
        fermo.wait(max(5.0, prossima_lettura(time.time(), C.RETE_INTERRUZIONI_MIN) - time.time()))


def _stato_leggi() -> dict:
    p = C.DATI / "worker_stato.json"
    try:
        return {k: dt.date.fromisoformat(v) for k, v in json.loads(p.read_text()).items()}
    except Exception:
        return {}


def _stato_scrivi(fatti: dict) -> None:
    (C.DATI / "worker_stato.json").write_text(json.dumps({k: str(v) for k, v in fatti.items()}))


def _rete_ha_saturazione() -> bool:
    try:
        from . import rete
        return rete.ha_saturazione()
    except Exception:
        return False


def ciclo() -> None:
    log.info("Meteo: regioni servite %s, aggiornate ogni giorno %s", ",".join(C.REGIONI) or "tutte",
             ",".join(C.REGIONI_AGGIORNATE) or "tutte quelle servite")
    ultimo_prev = 0.0
    fatti: dict[str, dt.date] = _stato_leggi()   # sopravvive ai riavvii: niente notiziari doppi
    if not (C.DATI / "previsioni" / "ultima.parquet").exists():
        _sicuro(meteo.aggiorna_previsioni, "previsioni")
        ultimo_prev = time.time()
    hm, mm = map(int, C.ORA_MERCATI_LOCALE.split(":"))
    hr, mr = map(int, C.RETE_SATURAZIONE_ORA.split(":"))
    if C.RETE_ATTIVA:
        threading.Thread(target=ciclo_interruzioni, daemon=True, name="interruzioni").start()
    while True:
        utc = dt.datetime.now(dt.timezone.utc)
        loc = utc.astimezone(ROMA)
        oggi = loc.date()
        if time.time() - ultimo_prev >= C.ORE_PREVISIONI * 3600:
            _sicuro(meteo.aggiorna_previsioni, "previsioni")
            ultimo_prev = time.time()
        if utc.hour >= C.ORA_STORICO_UTC and fatti.get("storico") != utc.date():
            if _sicuro(meteo.aggiorna_storico, "storico"):
                fatti["storico"] = utc.date()
        # (14/11/2026) subito dopo lo storico (che porta le ore ICON nuove); una volta al giorno anche se fallisce
        if utc.hour >= C.ORA_STORICO_UTC and fatti.get("psicro") != utc.date():
            _sicuro(psicro, "archivio psicrometrico")
            fatti["psicro"] = utc.date()
        if (loc.hour, loc.minute) >= (hm, mm) and fatti.get("mercati") != oggi:
            _sicuro(mercati, "mercati")
            fatti["mercati"] = oggi
        if loc.day == C.NOTIZIARIO_GIORNO and loc.hour >= 9 and fatti.get("mensile") != oggi:
            _sicuro(mensile, "newsletter mensile")
            fatti["mensile"] = oggi
        if loc.weekday() == C.SETTIMANALE_GIORNO and loc.hour >= C.SETTIMANALE_ORA and fatti.get("settimanale") != oggi:
            _sicuro(settimanale, "previsioni settimanali per email")
            fatti["settimanale"] = oggi
        if loc.hour >= C.AVVISI_ORA and fatti.get("avvisi_meteo") != oggi:
            _sicuro(avvisi_meteo, "avvisi meteo per email")
            fatti["avvisi_meteo"] = oggi
        if loc.day == 2 and loc.hour >= 8 and fatti.get("territorio") != oggi:
            _sicuro(territorio, "verifica territorio")
            fatti["territorio"] = oggi
        if loc.hour >= 4 and fatti.get("anncsu") != oggi and (
                loc.day == C.ANNCSU_GIORNO or (not C.ANNCSU_FILE.exists() and "anncsu" not in fatti)):
            _sicuro(anncsu, "indirizzario ANNCSU")
            fatti["anncsu"] = oggi
        if loc.day == C.INDICATORI_GIORNO and loc.hour >= 6 and fatti.get("indicatori") != oggi:
            _sicuro(indicatori, "indicatori della sanità")
            fatti["indicatori"] = oggi
        if (loc.day, loc.month) in C.CLIMA_DATE and loc.hour >= 3 and fatti.get("clima") != oggi:
            _sicuro(clima, "clima dal 1940")
            fatti["clima"] = oggi
        if C.RETE_ATTIVA and fatti.get("rete_saturazione") != oggi and ((loc.hour, loc.minute) >= (hr, mr) or (
                "rete_saturazione" not in fatti and not _rete_ha_saturazione())):
            try:                        # niente _sicuro: email solo con la soglia delle 72 ore (decisione del 17/11)
                rete_saturazione()
            except Exception:
                log.exception("Errore in saturazione della rete elettrica")
            fatti["rete_saturazione"] = oggi
        _stato_scrivi(fatti)
        time.sleep(300)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ciclo"
    {"ciclo": ciclo, "previsioni": meteo.aggiorna_previsioni, "storico": meteo.aggiorna_storico, "psicro": psicro,
     "mercati": mercati, "prezzi": prezzi, "mensile": mensile, "settimanale": settimanale, "avvisi": avvisi_meteo, "territorio": territorio, "anncsu": anncsu,
     "indicatori": indicatori, "clima": clima, "rete-interruzioni": rete_interruzioni,
     "rete-saturazione": rete_saturazione}[cmd]()
