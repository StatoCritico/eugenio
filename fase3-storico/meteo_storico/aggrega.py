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


COMUNI_PER_BLOCCO = 25   # un blocco (row group) del parquet: ~110.000 righe, ~6 MB in memoria


def scrivi_giornaliero(parti, dest: Path) -> int:
    """Scrive giornaliero.parquet un blocco alla volta: `parti` produce DataFrame (istat, data, ...) già ordinati per
    comune. Un row group per blocco di comuni, così chi legge un comune (filtro su istat) apre un solo blocco.
    Restituisce il numero di righe. Memoria: un blocco alla volta (tutta Italia sono ~34 milioni di righe)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    tmp = dest.with_suffix(".parziale")
    writer, n = None, 0
    try:
        for df in parti:
            if df is None or not len(df):
                continue
            t = pa.Table.from_pandas(df, preserve_index=False,
                                     schema=writer.schema if writer is not None else None)
            if writer is None:
                writer = pq.ParquetWriter(tmp, t.schema, compression="zstd")
            writer.write_table(t)
            n += len(df)
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        return 0
    tmp.replace(dest)
    return n


def esporta(archivio: Path, comuni: pd.DataFrame, dest: Path) -> None:
    """Prepara la cartella da copiare sul server (fase 4):
      comuni.json, giornaliero.parquet (ERA5 corretto, tutti i comuni, ordinato per comune e data, un row group ogni
      COMUNI_PER_BLOCCO comuni), orario/<istat>.parquet (ICON storico, modalità di breve periodo),
      parametri_correzione.parquet, metriche.json.
    Funziona a blocchi: per tutta Italia (7.896 comuni) la memoria resta sotto qualche centinaio di MB.
    """
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "orario").mkdir(exist_ok=True)
    codici = sorted(comuni.istat)
    par, n_comuni = [], [0]

    def blocchi():
        buf = []
        for k, istat in enumerate(codici, 1):
            p = archivio / "orario" / "era5_corretto" / f"{istat}.parquet"
            if p.exists():
                g = giornaliero(pd.read_parquet(p))
                g.insert(0, "istat", istat)
                buf.append(g)
                n_comuni[0] += 1
            q = archivio / "orario" / "icon" / f"{istat}.parquet"
            if q.exists():
                shutil.copyfile(q, dest / "orario" / f"{istat}.parquet")
            for sorgente in ("era5", "icon2i", "ifs"):
                c = archivio / "correzione" / "parametri" / sorgente / f"{istat}.parquet"
                if c.exists():
                    par.append(pd.read_parquet(c))
            if len(buf) >= COMUNI_PER_BLOCCO:
                yield pd.concat(buf, ignore_index=True)
                buf = []
            if k % 500 == 0:
                log.info("esportazione: %d/%d comuni", k, len(codici))
        if buf:
            yield pd.concat(buf, ignore_index=True)

    righe = scrivi_giornaliero(blocchi(), dest / "giornaliero.parquet")
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
    log.info("Esportati %d comuni (%d righe giornaliere) in %s", n_comuni[0], righe, dest)
