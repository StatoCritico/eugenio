"""Processo di aggiornamento (container "worker").

  previsioni meteo       ogni ORE_PREVISIONI ore
  storico meteo          ogni giorno dopo ORA_STORICO_UTC
  mercati (GME, TTF)     ogni notte alle ORA_MERCATI (ora italiana), con la sorveglianza delle fonti delle
                         convenzioni (email solo quando cambia qualcosa)
  newsletter dei dati    mensile, il giorno NOTIZIARIO_GIORNO (listmonk)
  verifica territorio    il 2 di ogni mese: nuovi comuni ISTAT o nuova versione dei confini Gramscii
  indirizzario ANNCSU    il giorno ANNCSU_GIORNO di ogni mese (o subito, se manca): civici georeferenziati
Gli errori vengono segnalati per email all'amministratore (EMAIL_AMMINISTRATORE).

  python -m servizio.worker                 ciclo continuo
  python -m servizio.worker previsioni|storico|mercati|mensile|territorio|anncsu   una sola esecuzione
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys
import time
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
    if esito["errori"]:
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
        _stato_scrivi(fatti)
        time.sleep(300)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ciclo"
    {"ciclo": ciclo, "previsioni": meteo.aggiorna_previsioni, "storico": meteo.aggiorna_storico,
     "mercati": mercati, "mensile": mensile, "territorio": territorio, "anncsu": anncsu}[cmd]()
