"""Processo di aggiornamento (container "worker").

  previsioni meteo       ogni ORE_PREVISIONI ore      } solo i comuni delle REGIONI_AGGIORNATE (vuoto = tutte le
  storico meteo          ogni giorno dopo ORA_STORICO_UTC } REGIONI servite); giornaliero aggiornato a blocchi di comuni
  archivio psicrometrico ogni giorno subito dopo lo storico: ore nuove di temperatura e umidità in CARTELLA_PSICRO
                         (ICON del server, poi ERA5 da S3 per gli altri comuni); niente se la cartella non c'è
  mercati (GME, TTF)     ogni notte alle ORA_MERCATI (ora italiana), con la sorveglianza delle fonti delle
                         convenzioni (email solo quando cambia qualcosa), i listini delle convenzioni e, subito dopo,
                         gli indici dei prezzi pubblicabili per il sito (prezzi: /sito/dati/prezzi/indici.json)
  mercato del giorno    ogni notte alle ORA_MERCATO_MGP (04:15, ora italiana; 20/11/2026): MGP del GME, cioè liquidità,
  prima (mercato-mgp)    transiti, fabbisogno, curve aggregate di domanda e offerta e offerte pubbliche (tutte, pubblicate
                         dopo 7 giorni; un Parquet al giorno in /dati/mercati/mgp_offerte), storico all'indietro qualche
                         giorno per notte. SOLO USO INTERNO: niente sul sito, nessuna rotta, nessuna esportazione. Email
                         solo per credenziali GME rifiutate, fonte ferma da giorni, disco quasi pieno (fase6 mgp_notturno)
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
  aree GSE               una volta al mese, il giorno GSE_CONTROLLO_GIORNO (3) dalle GSE_CONTROLLO_ORA (7, ora italiana):
                         il servizio del GSE delle aree convenzionali risponde? Una richiesta ?f=json, nessun dato salvato,
                         email solo se non risponde (20/11/2026; le aree le legge solo il browser)
  dati di Terna          (20/11/2026, servizio/terna.py) ogni giorno dalle TERNA_API_ORA (06:30): il giorno prima dall'API
                         ufficiale (chiavi TERNA_CLIENT_ID/SECRET nel .env, 1 richiesta al secondo, tetto TERNA_API_TETTO
                         al giorno), l'IMCEI del mese, TERNA_STORICO_MESI mesi di storico dal Download Center (senza
                         chiave) e subito dopo i file di «Carichi elettrici» (carichi: /sito/dati/carichi/); dopo un 429
                         o un 5xx si riprova dopo TERNA_RIPROVA_MIN minuti
  statistiche Terna      il giorno ELETTRICITA_GIORNO (5) dalle ELETTRICITA_ORA (05:00), subito se l'archivio è vuoto:
                         statistiche annuali dal Download Center e file di «Produzione e consumi di elettricità»
                         (elettricita: /sito/dati/elettricita/, fase 15)
  suolo e aree agricole  (22/11/2026) il giorno SUOLO_GIORNO (6) dalle SUOLO_ORA (05:30), subito se il sito non ha i file:
                         indicatori ISPRA del consumo di suolo (groupware SINAnet, file con anno e versione più alti),
                         superfici coltivate e censimento ISTAT (SDMX), con SUOLO_CARTE anche le carte raster per
                         l'incrocio del suolo agricolo; ricostruisce solo se qualcosa è cambiato
                         (suolo: /sito/dati/suolo/, fase 16)
I file del sito (indicatori, clima) si scrivono in una cartella nuova e si scambiano con quella pubblicata solo a
lavoro finito e controllato: se qualcosa va storto restano quelli di prima.
Gli errori vengono segnalati per email all'amministratore (EMAIL_AMMINISTRATORE).

  python -m servizio.worker                 ciclo continuo
  python -m servizio.worker previsioni|storico|psicro|mercati|mercato-mgp|prezzi|mensile|settimanale|avvisi|territorio|anncsu|indicatori|clima
                            |rete-interruzioni|rete-saturazione|gse-aree|terna-api|elettricita|carichi|suolo|suolo-forza
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


def mercato_mgp() -> dict:
    """(20/11/2026) Mercato del giorno prima del GME, solo uso interno (fase 6, mercati_energia/mgp_notturno.py): serie
    aggiuntive, curve aggregate e offerte pubbliche in /dati/mercati. Email solo per i motivi in esito["da_segnalare"]
    (credenziali rifiutate, fonte ferma da giorni, disco quasi pieno, 3 notti fallite di fila), una volta per episodio."""
    if not Path(C.MERCATI_CONFIG).exists():
        log.info("Mercato del giorno prima: configurazione dei mercati assente (%s)", C.MERCATI_CONFIG)
        return {}
    from mercati_energia import mgp_notturno
    from mercati_energia.config import carica
    esito = mgp_notturno.esegui(carica(C.MERCATI_CONFIG))
    if esito.get("da_segnalare"):
        avvisi.invia("mercato del giorno prima (GME): da controllare", "\n\n".join(esito["da_segnalare"]))
    return esito


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


def gse_aree() -> dict:
    """(20/11/2026) Controllo mensile del servizio del GSE delle aree convenzionali (rete.controlla_servizio_gse): una sola
    richiesta ?f=json, nessun dato salvato; email all'amministratore SOLO se non risponde (il nome del servizio cambierà
    con AC_Comuni_2027: allora va aggiornato in servizio/rete.py e in fase5-sito/sito/rete.js)."""
    from . import rete
    try:
        esito = rete.controlla_servizio_gse()
    except Exception as e:
        log.warning("Servizio del GSE delle aree convenzionali: %s: %s", type(e).__name__, e)
        avvisi.invia("servizio del GSE delle aree convenzionali non risponde",
                     f"Controllo mensile di {rete.URL_GSE_AREE}?f=json non riuscito: {type(e).__name__}: {e}\n\n"
                     "Le pagine «Cabine primarie» e «Comunità energetiche» non possono leggere le aree convenzionali. "
                     "Se il GSE ha pubblicato un servizio nuovo (es. AC_Comuni_2027), aggiornare l'indirizzo in "
                     "fase4-server/servizio/rete.py (URL_GSE_AREE) e in fase5-sito/sito/rete.js (GSE.SERVIZIO).\n"
                     f"Mappa del GSE: {rete.PAGINA_GSE_AREE}")
        return {"ok": False, "errore": f"{type(e).__name__}: {e}"}
    log.info("Servizio del GSE delle aree convenzionali: risponde (%s)", esito.get("strato_0"))
    return esito


# ---------------------------------------------------------------------------------------------- dati di Terna (20/11/2026)
def terna_api() -> dict:
    """Serie di Terna (servizio/terna.py): giorno prima e IMCEI dall'API ufficiale, storico dal Download Center, riserva
    reciproca. Senza chiavi nel .env la parte dell'API non parte (riga nel registro, nessuna email). Dopo un
    aggiornamento riuscito rifà i file di «Carichi elettrici» (lavoro carichi). Esito con "rimandato": True dopo un 429 o
    un 5xx: il ciclo riprova dopo TERNA_RIPROVA_MIN minuti."""
    from . import terna
    esito = terna.aggiorna()
    if any(esito["righe"].values()):
        try:
            esito["carichi"] = carichi()
        except Exception as e:
            log.exception("Errore nei file di «Carichi elettrici»")
            avvisi.invia("errore nei file di «Carichi elettrici»", f"{type(e).__name__}: {e}")
            esito["carichi"] = {"errore": f"{type(e).__name__}: {e}"}
    return esito


def _costruisci_carichi():
    """costruisci_carichi(archivio, uscita) della fase 15, se c'è (la scrive un'altra sessione): None altrimenti."""
    import importlib
    for modulo in ("elettricita.carichi", "elettricita.costruisci_carichi", "elettricita.costruisci"):
        try:
            f = getattr(importlib.import_module(modulo), "costruisci_carichi", None)
        except ImportError:
            continue
        if callable(f):
            return f
    return None


def _controlla_cartella(nuova: Path, finale: Path, indice: str | None, nome: str) -> None:
    n_nuovi, n_vecchi = _conta_json(nuova), _conta_json(finale)
    if n_nuovi == 0 or (indice and not (nuova / indice).exists()) or n_nuovi < 0.9 * n_vecchi:
        raise RuntimeError(f"{nome}: file nuovi incompleti ({n_nuovi} contro {n_vecchi}), restano quelli di prima")


def carichi() -> dict:
    """File del sito per «Carichi elettrici» (fase 15, costruisci_carichi) dall'archivio TERNA_DATI/serie, pubblicati in
    /sito/dati/carichi con _pubblica solo se il controllo passa (almeno un file, non meno del 90 % di prima)."""
    from . import terna
    f = _costruisci_carichi()
    if f is None:
        log.info("Carichi elettrici: costruisci_carichi della fase 15 non ancora disponibile, niente da pubblicare")
        return {"saltato": "costruisci_carichi assente"}
    finale, nuova = C.SITO_DATI / "carichi", C.SITO_DATI / ".carichi_nuova"
    shutil.rmtree(nuova, ignore_errors=True)
    try:
        esito = f(terna.cartella_serie(), nuova)
    except NotImplementedError as e:
        shutil.rmtree(nuova, ignore_errors=True)
        log.warning("Carichi elettrici: costruisci_carichi non è ancora pronto (%s), niente pubblicato", e)
        return {"saltato": "costruisci_carichi non pronto"}
    try:
        _controlla_cartella(nuova, finale, None, "carichi")
    except RuntimeError:
        shutil.rmtree(nuova, ignore_errors=True)
        raise
    _pubblica(nuova, finale)
    log.info("Carichi elettrici: %d file pubblicati", _conta_json(finale))
    return esito if isinstance(esito, dict) else {"pubblicati": _conta_json(finale)}


def _archivio_elettricita_vuoto() -> bool:
    raw = C.TERNA_DATI / "statistiche"
    return not raw.is_dir() or not any(raw.glob("*.json"))


def elettricita() -> dict:
    """Statistiche annuali di Terna (fase 15): terna_dc.scarica (Download Center, nessuna chiave, nessuna quota; anni
    mancanti più gli ultimi 2, che passano da provvisori a consolidati) e costruisci → /sito/dati/elettricita, pubblicata
    con _pubblica solo se il controllo passa (italia.json presente, non meno del 90 % dei file di prima).
    Email all'amministratore solo per errori veri: Terna non risponde in due mesi diversi di fila, file incompleti.
    Se costruisci non è ancora pronto (NotImplementedError): avviso nel registro, niente pubblicato, nessuna email."""
    from elettricita import terna_dc
    from elettricita.costruisci import costruisci
    raw = C.TERNA_DATI / "statistiche"
    fstato = C.TERNA_DATI / "elettricita_stato.json"
    try:
        stato = json.loads(fstato.read_text())
    except Exception:
        stato = {}
    mese = dt.datetime.now(ROMA).strftime("%Y-%m")
    try:
        scaricati = terna_dc.scarica(raw, ultimi=2)
    except Exception as e:
        mesi = stato.setdefault("mesi_falliti", [])
        if mese not in mesi:
            mesi.append(mese)
        log.warning("Statistiche di Terna: Download Center non disponibile (%s: %s), mesi falliti di fila: %s",
                    type(e).__name__, e, mesi)
        if len(mesi) >= 2 and not stato.get("avvisato"):
            stato["avvisato"] = True
            avvisi.invia("statistiche di Terna: il Download Center non risponde da due mesi",
                         f"terna_dc.scarica non riuscito nei mesi {', '.join(mesi)}. Ultimo errore: {type(e).__name__}: {e}"
                         "\nLa pagina «Produzione e consumi di elettricità» mostra ancora i file di prima.")
        fstato.parent.mkdir(parents=True, exist_ok=True)
        fstato.write_text(json.dumps(stato))
        return {"errore": f"{type(e).__name__}: {e}"}
    fstato.parent.mkdir(parents=True, exist_ok=True)
    fstato.write_text(json.dumps({"ultimo_ok": mese}))
    finale, nuova = C.SITO_DATI / "elettricita", C.SITO_DATI / ".elettricita_nuova"
    shutil.rmtree(nuova, ignore_errors=True)
    try:
        esito = costruisci(raw, nuova)
    except NotImplementedError as e:
        shutil.rmtree(nuova, ignore_errors=True)
        log.warning("Statistiche di Terna: costruisci della fase 15 non è ancora pronto (%s), niente pubblicato", e)
        return {"scaricati": scaricati, "saltato": "costruisci non pronto"}
    try:
        _controlla_cartella(nuova, finale, "italia.json", "elettricita")
    except RuntimeError as e:
        shutil.rmtree(nuova, ignore_errors=True)
        log.warning("Statistiche di Terna: %s", e)
        avvisi.invia("statistiche di Terna: file incompleti", f"{e}\nScaricati: {json.dumps(scaricati)}")
        return {"scaricati": scaricati, "errore": str(e)}
    _pubblica(nuova, finale)
    log.info("Statistiche di Terna: %d file pubblicati in %s", _conta_json(finale), finale)
    return {"scaricati": scaricati, "costruisci": esito, "pubblicati": _conta_json(finale)}


def _suolo_mancante() -> bool:
    return not (C.SITO_DATI / "suolo" / "italia.json").exists()


def suolo(forza: bool = False) -> dict:
    """«Suolo e aree agricole» (fase 16): scarica.scarica (ISPRA groupware + ISTAT SDMX; con SUOLO_CARTE anche le carte
    raster), agricolo.agricolo se è arrivata una carta dei cambiamenti nuova (o manca il suo incrocio), costruisci →
    /sito/dati/suolo, pubblicata con _pubblica solo se i controlli passano (somme comuni = province = regioni = Italia,
    comuni abbinati, ultimo anno = edizione − 1, scarto con i file pubblicati sotto il 2 %, italia.json presente, non meno
    del 90 % dei file di prima). Niente da fare se non è cambiato nulla e il sito ha già i file. forza=True (comando
    suolo-forza) ricostruisce comunque e accetta scarti oltre il 2 % (nuova edizione con revisioni grandi, dopo un controllo).
    Email all'amministratore solo per errori veri: fonti che non rispondono in due mesi diversi di fila, controlli non
    superati (restano i file di prima)."""
    from suolo import scarica as scarica_suolo
    from suolo.costruisci import costruisci as costruisci_suolo
    raw = C.SUOLO_DATI
    fstato = raw / "lavoro_stato.json"
    try:
        stato = json.loads(fstato.read_text())
    except Exception:
        stato = {}
    mese = dt.datetime.now(ROMA).strftime("%Y-%m")
    try:
        sc = scarica_suolo.scarica(raw, carte=C.SUOLO_CARTE)
    except Exception as e:
        mesi = stato.setdefault("mesi_falliti", [])
        if mese not in mesi:
            mesi.append(mese)
        log.warning("Suolo: fonti non disponibili (%s: %s), mesi falliti di fila: %s", type(e).__name__, e, mesi)
        if len(mesi) >= 2 and not stato.get("avvisato"):
            stato["avvisato"] = True
            avvisi.invia("suolo e aree agricole: le fonti non rispondono da due mesi",
                         f"scarica non riuscito nei mesi {', '.join(mesi)}. Ultimo errore: {type(e).__name__}: {e}"
                         "\nLa pagina «Suolo e aree agricole» mostra ancora i file di prima.")
        raw.mkdir(parents=True, exist_ok=True)
        fstato.write_text(json.dumps(stato))
        return {"errore": f"{type(e).__name__}: {e}"}
    raw.mkdir(parents=True, exist_ok=True)
    fstato.write_text(json.dumps({"ultimo_ok": mese}))
    cambiati = sc["cambiati"]
    esito: dict = {"cambiati": cambiati}
    # incrocio agricolo: una volta per carta dei cambiamenti (agricolo_<anno>.json resta nell'archivio: la serie cresce)
    camb = (sc["stato"].get("cambiamenti") or {})
    uso = (sc["stato"].get("uso") or {})
    if C.SUOLO_CARTE and camb.get("nome") and uso.get("nome"):
        anno = int(camb["periodo"].split("-")[1])
        fagr = raw / f"agricolo_{anno}.json"
        if "cambiamenti" in cambiati or "uso" in cambiati or not fagr.exists():
            try:
                from suolo.agricolo import agricolo
                a = agricolo(raw / "carte" / camb["nome"], raw / "carte" / uso["nome"], C.SITO_DATI / "mappa", fagr, anno=anno)
                esito["agricolo"] = {"anno": anno, "lordo_ha": round(sum(a["italia"]["lordo"]), 1),
                                     "agricolo_ha": round(sum(a["italia"]["agricolo"]), 1), "secondi": a["secondi"]}
                cambiati = cambiati + ["agricolo"]
            except Exception as e:      # l'incrocio è un di più: la pagina si costruisce lo stesso
                log.exception("Suolo: incrocio agricolo non riuscito")
                avvisi.invia("suolo e aree agricole: incrocio agricolo non riuscito", f"{type(e).__name__}: {e}")
                esito["agricolo"] = {"errore": f"{type(e).__name__}: {e}"}
    finale, nuova = C.SITO_DATI / "suolo", C.SITO_DATI / ".suolo_nuova"
    if not cambiati and not forza and not _suolo_mancante():
        log.info("Suolo: niente di nuovo (file ISPRA %s)", (sc["stato"].get("ispra") or {}).get("nome"))
        return {**esito, "invariato": True}
    shutil.rmtree(nuova, ignore_errors=True)
    try:
        esito["costruisci"] = costruisci_suolo(raw, nuova, C.SITO_DATI / "mappa", finale / "italia.json", forza)
        _controlla_cartella(nuova, finale, "italia.json", "suolo")
    except (ValueError, RuntimeError) as e:
        shutil.rmtree(nuova, ignore_errors=True)
        log.warning("Suolo: %s", e)
        avvisi.invia("suolo e aree agricole: controlli non superati", f"{e}\nCambiati: {', '.join(cambiati)}. "
                     "Restano i file di prima. Se è una nuova edizione ISPRA con revisioni grandi, dopo un controllo: "
                     "python -m servizio.worker suolo-forza")
        return {**esito, "errore": str(e)}
    _pubblica(nuova, finale)
    log.info("Suolo: %d file pubblicati in %s", _conta_json(finale), finale)
    return {**esito, "pubblicati": _conta_json(finale)}


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
    ht, mt = map(int, C.TERNA_API_ORA.split(":"))
    he, me = map(int, C.ELETTRICITA_ORA.split(":"))
    terna_riprova, terna_tentativi = 0.0, 0   # dopo un 429 o un 5xx di Terna: quando riprovare, tentativi di oggi
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
        if (loc.hour, loc.minute) >= tuple(map(int, C.ORA_MERCATO_MGP.split(":"))) and fatti.get("mercato_mgp") != oggi:
            try:                        # niente _sicuro: le email le decide mgp_notturno (da_segnalare)
                mercato_mgp()
            except Exception:
                log.exception("Errore nel mercato del giorno prima")
            fatti["mercato_mgp"] = oggi
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
        if loc.day == C.GSE_CONTROLLO_GIORNO and loc.hour >= C.GSE_CONTROLLO_ORA and fatti.get("gse_aree") != oggi:
            try:                        # una sola richiesta al mese, anche se fallisce (l'email la manda gse_aree)
                gse_aree()
            except Exception:
                log.exception("Errore nel controllo del servizio del GSE")
            fatti["gse_aree"] = oggi
        # (20/11/2026) dati di Terna: una volta al giorno; dopo un 429 o un 5xx si riprova più tardi (al più
        # TERNA_RIPROVA_MAX volte), poi domani. Email solo da terna.py (archivio fermo da giorni) e per i carichi.
        if (loc.hour, loc.minute) >= (ht, mt) and fatti.get("terna_api") != oggi and time.time() >= terna_riprova:
            esito = None
            try:
                esito = terna_api()
            except Exception as e:
                log.exception("Errore nei dati di Terna")
                avvisi.invia("errore nei dati di Terna", f"{type(e).__name__}: {e}")
            if esito and esito.get("rimandato") and terna_tentativi < C.TERNA_RIPROVA_MAX:
                terna_tentativi += 1
                terna_riprova = time.time() + C.TERNA_RIPROVA_MIN * 60
            else:
                fatti["terna_api"], terna_tentativi, terna_riprova = oggi, 0, 0.0
        if fatti.get("elettricita") != oggi and (
                (loc.day == C.ELETTRICITA_GIORNO and (loc.hour, loc.minute) >= (he, me)) or _archivio_elettricita_vuoto()):
            try:                        # una volta al giorno anche se fallisce; le email le decide elettricita()
                elettricita()
            except Exception as e:
                log.exception("Errore nelle statistiche di Terna")
                avvisi.invia("errore nelle statistiche di Terna", f"{type(e).__name__}: {e}")
            fatti["elettricita"] = oggi
        # (22/11/2026) suolo e aree agricole: controllo mensile (ISPRA esce a fine ottobre, ISTAT in primavera e autunno)
        hs, ms = map(int, C.SUOLO_ORA.split(":"))
        if fatti.get("suolo") != oggi and (
                (loc.day == C.SUOLO_GIORNO and (loc.hour, loc.minute) >= (hs, ms)) or _suolo_mancante()):
            try:                        # una volta al giorno anche se fallisce; le email le decide suolo()
                suolo()
            except Exception as e:
                log.exception("Errore nel suolo e aree agricole")
                avvisi.invia("errore nel suolo e aree agricole", f"{type(e).__name__}: {e}")
            fatti["suolo"] = oggi
        _stato_scrivi(fatti)
        time.sleep(300)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ciclo"
    {"ciclo": ciclo, "previsioni": meteo.aggiorna_previsioni, "storico": meteo.aggiorna_storico, "psicro": psicro,
     "mercati": mercati, "mercato-mgp": mercato_mgp, "prezzi": prezzi, "mensile": mensile, "settimanale": settimanale, "avvisi": avvisi_meteo, "territorio": territorio, "anncsu": anncsu,
     "indicatori": indicatori, "clima": clima, "rete-interruzioni": rete_interruzioni,
     "rete-saturazione": rete_saturazione, "gse-aree": gse_aree, "terna-api": terna_api, "elettricita": elettricita,
     "carichi": carichi, "suolo": suolo, "suolo-forza": lambda: suolo(forza=True)}[cmd]()
