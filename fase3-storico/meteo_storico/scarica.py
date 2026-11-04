"""Download orario da Open-Meteo per i comuni, a pezzi di un anno, con ripresa automatica.

Struttura su disco (cartella archivio):
  grezzi/<fonte>/<istat>/<anno>.parquet   pezzi annuali come scaricati
  orario/<fonte>/<istat>.parquet          serie unite (dopo `unisci`)
Tempo in UTC (colonna `time`, datetime64[ns, UTC]), valori float32.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from . import VARIABILI
from .limiti import Limitatore, peso

log = logging.getLogger(__name__)

FONTI = {
    # serie lunga, omogenea: ERA5 + ERA5-Land (temperatura e umidità a 0,1°) ~5 giorni di ritardo
    "era5": {"url": "https://archive-api.open-meteo.com/v1/archive", "percorso_locale": "/v1/archive",
             "models": "era5_seamless", "inizio": dt.date(1950, 1, 1), "ritardo_giorni": 6},
    # previsioni storiche dei modelli ICON (D2 2 km, EU 7 km, globale): stessi modelli delle previsioni
    "icon": {"url": "https://historical-forecast-api.open-meteo.com/v1/forecast", "percorso_locale": "/v1/forecast",
             "models": "icon_seamless", "inizio": dt.date(2022, 11, 14), "ritardo_giorni": 1},
    # modelli usati per le previsioni del sito, solo per stimarne la correzione verso ICON seamless
    "icon2i": {"url": "https://historical-forecast-api.open-meteo.com/v1/forecast", "percorso_locale": "/v1/forecast",
               "models": "italia_meteo_arpae_icon_2i", "inizio": dt.date(2025, 4, 14), "ritardo_giorni": 1},
    "ifs": {"url": "https://historical-forecast-api.open-meteo.com/v1/forecast", "percorso_locale": "/v1/forecast",
            "models": "ecmwf_ifs025", "inizio": dt.date(2024, 2, 4), "ritardo_giorni": 1},
}


class Scaricatore:
    def __init__(self, archivio: Path, fonte: str, base_locale: str | None = None, punti_per_richiesta: int = 5):
        self.archivio = archivio
        self.fonte = fonte
        self.cfg = FONTI[fonte]
        self.url = (base_locale.rstrip("/") + self.cfg["percorso_locale"]) if base_locale else self.cfg["url"]
        self.lim = Limitatore(archivio / "stato_api.json", illimitato=bool(base_locale))
        self.n = punti_per_richiesta
        self.http = client()

    # ------------------------------------------------------------------ singola richiesta
    def _richiesta(self, punti: pd.DataFrame, inizio: dt.date, fine: dt.date) -> list[pd.DataFrame]:
        return richiesta(self.http, self.lim, self.url, punti, self.cfg["models"], inizio=inizio, fine=fine)

    # ------------------------------------------------------------------ logica a pezzi annuali
    def _pezzo(self, istat: str, anno: int) -> Path:
        return self.archivio / "grezzi" / self.fonte / istat / f"{anno}.parquet"

    def _da_fare(self, istat: str, anno: int, fine_disp: dt.date) -> bool:
        p = self._pezzo(istat, anno)
        if not p.exists():
            return True
        fine_anno = min(dt.date(anno, 12, 31), fine_disp)
        try:
            ultimo = pd.read_parquet(p, columns=["time"]).time.max()
        except Exception:
            return True
        if pd.isna(ultimo):
            return True
        return ultimo.date() < fine_anno

    def scarica(self, comuni: pd.DataFrame, dal: dt.date, al: dt.date | None = None) -> None:
        oggi = dt.datetime.now(dt.timezone.utc).date()
        fine_disp = oggi - dt.timedelta(days=self.cfg["ritardo_giorni"])
        al = min(al or fine_disp, fine_disp)
        dal = max(dal, self.cfg["inizio"])
        anni = list(range(dal.year, al.year + 1))
        lavori = [(anno, r) for anno in anni for r in comuni.itertuples() if self._da_fare(r.istat, anno, fine_disp)]
        log.info("%s: %d pezzi (comune×anno) da scaricare su %d", self.fonte, len(lavori), len(anni) * len(comuni))
        fatti = 0
        for anno in anni:
            gruppo = [r for a, r in lavori if a == anno]
            for i in range(0, len(gruppo), self.n):
                blocco = pd.DataFrame(gruppo[i:i + self.n])
                inizio = max(dt.date(anno, 1, 1), dal)
                fine = min(dt.date(anno, 12, 31), al)
                risultati = self._richiesta(blocco, inizio, fine)
                for r, df in zip(blocco.itertuples(), risultati):
                    p = self._pezzo(r.istat, anno)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    tmp = p.with_suffix(".tmp")
                    df.to_parquet(tmp, index=False, compression="zstd")
                    tmp.replace(p)
                fatti += len(blocco)
                log.info("%s %d: %d/%d pezzi (%s)", self.fonte, anno, fatti, len(lavori), self.lim.riepilogo())

    def unisci(self, comuni: pd.DataFrame) -> None:
        dest = self.archivio / "orario" / self.fonte
        dest.mkdir(parents=True, exist_ok=True)
        for istat in comuni.istat:
            pezzi = sorted((self.archivio / "grezzi" / self.fonte / istat).glob("*.parquet"))
            if not pezzi:
                continue
            df = pd.concat([pd.read_parquet(p) for p in pezzi], ignore_index=True)
            df = df.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
            tmp = dest / f"{istat}.tmp"
            df.to_parquet(tmp, index=False, compression="zstd")
            tmp.replace(dest / f"{istat}.parquet")
        log.info("%s: serie unite in %s", self.fonte, dest)


def leggi(archivio: Path, fonte: str, istat: str) -> pd.DataFrame | None:
    p = archivio / "orario" / fonte / f"{istat}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def client() -> httpx.Client:
    return httpx.Client(timeout=180, headers={"User-Agent": "progetto-energia/1.0 (open source)"})


def richiesta(http: httpx.Client, lim: Limitatore, url: str, punti: pd.DataFrame, models: str, *,
              inizio: dt.date | None = None, fine: dt.date | None = None,
              forecast_days: int | None = None, variabili: list[str] = VARIABILI) -> list[pd.DataFrame]:
    """Una chiamata Open-Meteo per più punti (colonne lat, lon). Restituisce un DataFrame orario per punto,
    con colonna `time` in UTC. Gestisce limiti, errori temporanei e ritentativi."""
    params = {
        "latitude": ",".join(f"{v:.5f}" for v in punti.lat),
        "longitude": ",".join(f"{v:.5f}" for v in punti.lon),
        "hourly": ",".join(variabili),
        "models": models,
        "timezone": "GMT",
        "timeformat": "unixtime",
    }
    if forecast_days:
        params["forecast_days"] = forecast_days
        giorni = forecast_days
    else:
        params["start_date"] = inizio.isoformat()
        params["end_date"] = fine.isoformat()
        giorni = (fine - inizio).days + 1
    w = peso(len(punti), giorni, len(variabili))
    for tentativo in range(8):
        lim.attendi(w)
        try:
            r = http.get(url, params=params)
        except httpx.HTTPError as e:
            log.warning("Errore di rete (%s), riprovo", e)
            time.sleep(min(300, 10 * 2 ** tentativo))
            continue
        lim.registra(w)
        if r.status_code == 429:
            motivo = r.json().get("reason", "") if r.headers.get("content-type", "").startswith("application/json") else r.text
            if "onthly" in motivo:
                raise RuntimeError(f"Open-Meteo: {motivo}")
            pausa = 65 if "inute" in motivo else 900 if "ourly" in motivo else 3600
            log.warning("Open-Meteo 429: %s – pausa %d s", motivo, pausa)
            time.sleep(pausa)
            continue
        if r.status_code >= 500:
            time.sleep(min(300, 10 * 2 ** tentativo))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Open-Meteo {r.status_code}: {r.text[:300]}")
        dati = r.json()
        if isinstance(dati, dict):
            dati = [dati]
        out = []
        for d in dati:
            h = d["hourly"]
            df = pd.DataFrame({"time": pd.to_datetime(np.asarray(h["time"], dtype="int64"), unit="s", utc=True)})
            for v in variabili:
                df[v] = np.asarray([np.nan if x is None else x for x in h.get(v, [None] * len(df))], dtype="float32")
            # elimina le ore finali senza dati (ritardo di pubblicazione / fine orizzonte)
            validi = df[variabili].notna().any(axis=1).to_numpy()
            df = df.iloc[: int(np.flatnonzero(validi)[-1]) + 1] if validi.any() else df.iloc[:0]
            df.attrs = {"elevation": d.get("elevation"), "lat_griglia": d.get("latitude"),
                        "lon_griglia": d.get("longitude")}
            out.append(df)
        return out
    raise RuntimeError("Troppi tentativi falliti")
