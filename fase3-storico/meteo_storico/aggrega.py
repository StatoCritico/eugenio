"""Aggregazione giornaliera (giorno civile Europe/Rome) ed esportazione per il server."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def giornaliero(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index(pd.DatetimeIndex(df["time"]).tz_convert("Europe/Rome")).drop(columns="time")
    g = x.resample("D")
    out = pd.DataFrame({
        "t_media": g.temperature_2m.mean(),
        "t_min": g.temperature_2m.min(),
        "t_max": g.temperature_2m.max(),
        "ur_media": g.relative_humidity_2m.mean(),
        "rad_globale_kwh_m2": g.shortwave_radiation.sum() / 1000.0,   # W/m² medi orari → kWh/m²
        "rad_diffusa_kwh_m2": g.diffuse_radiation.sum() / 1000.0,
        "vento_medio_kmh": g.wind_speed_10m.mean(),
        "nuvolosita_media": g.cloud_cover.mean(),
        "pioggia_mm": g.precipitation.sum(),
        "neve_cm": g.snowfall.sum(),
        "ore": g.temperature_2m.count(),
    })
    out = out[out.ore >= 20].drop(columns="ore")
    out["gg20"] = (20 - out.t_media).clip(lower=0)       # gradi giorno riscaldamento (base 20 °C)
    out["gc24"] = (out.t_media - 24).clip(lower=0)       # gradi giorno raffrescamento (base 24 °C)
    out.index = out.index.date
    out.index.name = "data"
    return out.astype("float32").reset_index()


def esporta(archivio: Path, comuni: pd.DataFrame, dest: Path) -> None:
    """Prepara la cartella da copiare sul server (fase 4):
      comuni.json, giornaliero.parquet (ERA5 corretto, tutti i comuni),
      orario/<istat>.parquet (ICON storico, modalità di breve periodo),
      parametri_correzione.parquet, metriche.json
    """
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "orario").mkdir(exist_ok=True)
    parti, par = [], []
    for istat in comuni.istat:
        p = archivio / "orario" / "era5_corretto" / f"{istat}.parquet"
        if p.exists():
            g = giornaliero(pd.read_parquet(p))
            g.insert(0, "istat", istat)
            parti.append(g)
        q = archivio / "orario" / "icon" / f"{istat}.parquet"
        if q.exists():
            shutil.copyfile(q, dest / "orario" / f"{istat}.parquet")
        for sorgente in ("era5", "icon2i", "ifs"):
            c = archivio / "correzione" / "parametri" / sorgente / f"{istat}.parquet"
            if c.exists():
                par.append(pd.read_parquet(c))
    if parti:
        pd.concat(parti, ignore_index=True).to_parquet(dest / "giornaliero.parquet", index=False, compression="zstd")
    if par:
        pd.concat(par, ignore_index=True).to_parquet(dest / "parametri_correzione.parquet", index=False)
    for nome in ("comuni.json", "comuni.parquet"):
        if (archivio / nome).exists():
            shutil.copyfile(archivio / nome, dest / nome)
    for nome in ("metriche.json", "metriche_icon2i.json", "metriche_ifs.json"):
        m = archivio / "correzione" / nome
        if m.exists():
            shutil.copyfile(m, dest / nome)
    (dest / "LEGGIMI.txt").write_text(
        "Dati meteo: Open-Meteo.com (ERA5/ERA5-Land Copernicus, ICON DWD), CC BY 4.0.\n"
        "Comuni e sezioni di censimento: ISTAT, CC BY 4.0 (via Gramscii).\n"
        "giornaliero.parquet: ERA5-Seamless corretto verso ICON (vedi metriche.json).\n"
        "orario/: previsioni storiche ICON seamless, UTC.\n", encoding="utf-8")
    log.info("Esportati %d comuni in %s", len(parti), dest)
