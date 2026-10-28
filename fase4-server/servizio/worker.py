"""Processo di aggiornamento (container "worker").

  previsioni meteo       ogni ORE_PREVISIONI ore
  storico meteo          ogni giorno dopo ORA_STORICO_UTC
  mercati (GME, TTF)     ogni notte alle ORA_MERCATI (ora italiana), con la sorveglianza delle fonti delle
                         convenzioni (email solo quando cambia qualcosa)
  newsletter dei dati    mensile, il giorno NOTIZIARIO_GIORNO (listmonk)
  verifica territorio    il 2 di ogni mese: nuovi comuni ISTAT o nuova versione dei confini Gramscii
  indirizzario ANNCSU    il giorno ANNCSU_GIORNO di ogni mese (o subito, se manca): civici georeferenziati
  indicatori sanità      il giorno INDICATORI_GIORNO di ogni mese, dalle 6 (fase 8: OpenBDAP, ReportER, ISTAT)
  clima dal 1940         nei giorni CLIMA_DATE (10/1 e 10/7), dalle 3 (fase 9: ERA5 dai file .om su AWS)
I file del sito (indicatori, clima) si scrivono in una cartella nuova e si scambiano con quella pubblicata solo a
lavoro finito e controllato: se qualcosa va storto restano quelli di prima.
Gli errori vengono segnalati per email all'amministratore (EMAIL_AMMINISTRATORE).

  python -m servizio.worker                 ciclo continuo
  python -m servizio.worker previsioni|storico|mercati|mensile|territorio|anncsu|indicatori|clima
                                            una sola esecuzione (anche con docker compose run --rm worker …)
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import subprocess
import sys
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
    s = esito.get("sorveglianza") or {}
    if s.get("da_segnalare"):
        from mercati_energia.sorveglianza import riepilogo
        avvisi.invia("convenzioni e fonti: novità", riepilogo(s))


def mensile() -> None:
    from . import notiziario as n
    n.mensile()


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


def _stato_leggi() -> dict:
    p = C.DATI / "worker_stato.json"
    try:
        return {k: dt.date.fromisoformat(v) for k, v in json.loads(p.read_text()).items()}
    except Exception:
        return {}


def _stato_scrivi(fatti: dict) -> None:
    (C.DATI / "worker_stato.json").write_text(json.dumps({k: str(v) for k, v in fatti.items()}))


def ciclo() -> None:
    ultimo_prev = 0.0
    fatti: dict[str, dt.date] = _stato_leggi()   # sopravvive ai riavvii: niente notiziari doppi
    if not (C.DATI / "previsioni" / "ultima.parquet").exists():
        _sicuro(meteo.aggiorna_previsioni, "previsioni")
        ultimo_prev = time.time()
    hm, mm = map(int, C.ORA_MERCATI_LOCALE.split(":"))
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
        if (loc.hour, loc.minute) >= (hm, mm) and fatti.get("mercati") != oggi:
            _sicuro(mercati, "mercati")
            fatti["mercati"] = oggi
        if loc.day == C.NOTIZIARIO_GIORNO and loc.hour >= 9 and fatti.get("mensile") != oggi:
            _sicuro(mensile, "newsletter mensile")
            fatti["mensile"] = oggi
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
        _stato_scrivi(fatti)
        time.sleep(300)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ciclo"
    {"ciclo": ciclo, "previsioni": meteo.aggiorna_previsioni, "storico": meteo.aggiorna_storico,
     "mercati": mercati, "mensile": mensile, "territorio": territorio, "anncsu": anncsu,
     "indicatori": indicatori, "clima": clima}[cmd]()
