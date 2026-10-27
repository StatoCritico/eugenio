#!/usr/bin/env python3
"""Scarica le serie ERA5 / ERA5-Land per le celle dei comuni italiani e le riduce a dati giornalieri.

Fonte: i file .om di Open-Meteo sul bucket pubblico AWS Open Data s3://openmeteo (accesso anonimo,
nessuna chiave, nessuna quota dell'API). Sono gli stessi dati che l'API storica di Open-Meteo serve
(CC BY 4.0), letti per riga della griglia invece che punto per punto.

Comandi:
  python scarica.py comuni                   # elenco comuni, baricentro edifici, quota DEM, celle di griglia
  python scarica.py meteo [--campione F]     # dati giornalieri per cella, anno per anno (riprendibile)
  python scarica.py stato                    # cosa è in cache e cosa manca

Lo scaricamento è riprendibile: ogni (dominio, anno) è un file cache/<dominio>/<anno>.parquet scritto in
modo atomico; rilanciando lo stesso comando si riparte dal primo anno mancante. L'anno in corso viene
riscaricato solo con --aggiorna (dati ERA5T preliminari, che crescono di giorno in giorno).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
from omblocchi import BUCKET, FSBlocchi  # noqa: E402

log = logging.getLogger("scarica")
warnings.filterwarnings("ignore", category=RuntimeWarning)   # medie di giorni tutti vuoti (mare, futuro)

DOMINI = {
    # ERA5-Land: 0,1° (~9 km), dal 1950; su Open-Meteo solo temperatura e punto di rugiada
    "era5_land": {"cartella": "copernicus_era5_land", "res": 0.1, "nlat": 1801, "nlon": 3600, "anno0": 1950,
                  "variabili": ["temperature_2m", "dew_point_2m"]},
    # ERA5: 0,25° (~28 km), dal 1940; radiazione e vento (e temperatura prima del 1950)
    "era5": {"cartella": "copernicus_era5", "res": 0.25, "nlat": 721, "nlon": 1440, "anno0": 1940,
             "variabili": ["temperature_2m", "dew_point_2m", "shortwave_radiation", "direct_radiation",
                           "wind_u_component_10m", "wind_v_component_10m"]},
}
ULTIMO_ANNO_FILE = 2021        # fino a qui year_<AAAA>.om, dopo chunk_<n>.om da 504 ore
ORE_CHUNK = 504
FUSO = 1                       # giorno civile in ora solare (UTC+1) tutto l'anno, senza salti d'ora legale
FILI = 24                      # richieste contemporanee verso S3


def pressione_vapore(td):
    """Pa, Magnus con coefficienti Alduchov-Eskridge, dal punto di rugiada (come legge10.py)."""
    return 610.94 * np.exp(17.625 * td / (td + 243.04))


# ----------------------------------------------------------------------------------------- celle
def quota_celle(fs: FSBlocchi, dom: str) -> np.ndarray:
    from omfiles import OmFileReader
    d = DOMINI[dom]
    return OmFileReader.from_fsspec(fs, f"{BUCKET}/data/{d['cartella']}/static/HSURF.om")[:]


def assegna_celle(comuni: pd.DataFrame, fs: FSBlocchi) -> pd.DataFrame:
    """Come cell_selection=land dell'API Open-Meteo: tra le 3×3 celle attorno al punto, quella di terra con
    quota più vicina a quella del comune; se nessuna è di terra, la cella di terra più vicina entro 7×7."""
    out = comuni.copy()
    for dom, d in DOMINI.items():
        h = quota_celle(fs, dom)
        res = d["res"]
        fi = (out.lat.to_numpy() + 90) / res
        fj = (out.lon.to_numpy() + 180) / res
        ci, cj, cz, cd = [], [], [], []
        for a, b, z in zip(fi, fj, out.quota_m.to_numpy()):
            i0, j0 = int(round(a)), int(round(b))
            scelta = None
            for raggio in (1, 3):
                cand = [(i, j) for i in range(i0 - raggio, i0 + raggio + 1) for j in range(j0 - raggio, j0 + raggio + 1)
                        if h[i, j] > -999]
                if cand:
                    if raggio == 1:
                        scelta = min(cand, key=lambda c: (abs(h[c] - z), (c[0] - a) ** 2 + (c[1] - b) ** 2))
                    else:
                        scelta = min(cand, key=lambda c: (c[0] - a) ** 2 + (c[1] - b) ** 2)
                    break
            if scelta is None:
                scelta = (i0, j0)
            ci.append(scelta[0]); cj.append(scelta[1])
            cz.append(max(float(h[scelta]), 0.0))   # cella di mare (-999): quota 0
            dlat = (scelta[0] - a) * res * 111.2
            dlon = (scelta[1] - b) * res * 111.2 * np.cos(np.radians(scelta[0] * res - 90))
            cd.append(float(np.hypot(dlat, dlon)))
        out[f"{dom}_i"] = ci
        out[f"{dom}_j"] = cj
        out[f"{dom}_quota"] = cz
        out[f"{dom}_dist_km"] = np.round(cd, 1)
    return out


# ----------------------------------------------------------------------------------- lettura ore
def _ore_epoca(t: dt.datetime) -> int:
    return int((t - dt.datetime(1970, 1, 1)).total_seconds() // 3600)


def leggi_ore(fs: FSBlocchi, dom: str, var: str, celle: np.ndarray, h0: int, h1: int) -> np.ndarray:
    """Valori orari [h0, h1) (ore dal 1970 UTC) per le celle (array N×2 di indici i, j). Ritorna N×(h1-h0)."""
    from omfiles import OmFileReader
    d = DOMINI[dom]
    base = f"{BUCKET}/data/{d['cartella']}/{var}/"
    pezzi = []   # (file, ora iniziale del file, a, b)
    t = h0
    while t < h1:
        anno = (dt.datetime(1970, 1, 1) + dt.timedelta(hours=t)).year
        if anno <= ULTIMO_ANNO_FILE:
            f0 = _ore_epoca(dt.datetime(anno, 1, 1))
            f1 = _ore_epoca(dt.datetime(anno + 1, 1, 1))
            nome = f"year_{anno}.om"
        else:
            n = t // ORE_CHUNK
            f0, f1 = n * ORE_CHUNK, (n + 1) * ORE_CHUNK
            nome = f"chunk_{n}.om"
        b = min(h1, f1)
        pezzi.append((base + nome, f0, t - f0, b - f0))
        t = b
    righe = {}
    for k, (i, j) in enumerate(celle):
        righe.setdefault(int(i), []).append((k, int(j)))
    out = np.full((len(celle), h1 - h0), np.nan, dtype=np.float32)

    def una_riga(arg):
        path, f0, a, b, i, lst = arg
        try:
            r = OmFileReader.from_fsspec(fs, path)
        except FileNotFoundError:
            return lst, None, a, b
        nt = r.shape[2]
        bb = min(b, nt)
        if a >= bb:
            return lst, None, a, b
        js = [j for _, j in lst]
        blocco = r[i:i + 1, min(js):max(js) + 1, a:bb][0]
        return lst, (blocco, min(js)), a, b

    pos = 0
    for path, f0, a, b in pezzi:
        if not fs.fs.exists(path):          # blocco futuro, non ancora pubblicato
            pos += b - a
            continue
        lavori = [(path, f0, a, b, i, lst) for i, lst in sorted(righe.items())]
        with ThreadPoolExecutor(FILI) as ex:
            for lst, ris, a_, b_ in ex.map(una_riga, lavori):
                if ris is None:
                    continue
                blocco, jmin = ris
                for k, j in lst:
                    out[k, pos:pos + blocco.shape[1]] = blocco[j - jmin]
        pos += b - a
        fs.svuota(path)
    return out


# ------------------------------------------------------------------------------- aggregazione
def giornaliero_anno(fs: FSBlocchi, dom: str, celle: np.ndarray, anno: int,
                     prima: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Giorni civili in ora solare (UTC+1) dell'anno.

    Si leggono le ore UTC dell'anno [1/1 00:00, 1/1 dell'anno dopo 00:00); il giorno locale D comprende le
    ore UTC da D-1 23:00 a D 22:00, quindi l'ultima ora letta (31/12 23:00 UTC) passa all'anno dopo (`ultima`)
    e la prima ora del 1° gennaio arriva da `prima` (l'anno prima). Senza `prima` (primo anno, o ripresa
    dopo un'interruzione senza il file carry) il 1° gennaio ha 23 ore: resta valido (≥ 20 ore)."""
    h0 = _ore_epoca(dt.datetime(anno, 1, 1))
    h1 = _ore_epoca(dt.datetime(anno + 1, 1, 1))
    ndays = (h1 - h0) // 24
    v, ultima = {}, {}
    for var in DOMINI[dom]["variabili"]:
        x = leggi_ore(fs, dom, var, celle, h0, h1)
        p = (prima or {}).get(var)
        if p is None or len(p) != len(celle):
            p = np.full((len(celle), FUSO), np.nan, np.float32)
        ultima[var] = x[:, -FUSO:].copy()
        x = np.concatenate([p, x[:, :-FUSO]], axis=1)
        v[var] = x.reshape(len(celle), ndays, 24)
    t = v["temperature_2m"]
    n_ore = np.isfinite(t).sum(axis=2)
    with np.errstate(all="ignore"):
        dati = {"t_media": np.nanmean(t, 2), "t_min": np.nanmin(t, 2), "t_max": np.nanmax(t, 2),
                "pv": np.nanmean(pressione_vapore(v["dew_point_2m"]), 2)}
        if "shortwave_radiation" in v:
            sw, dr = v["shortwave_radiation"], v["direct_radiation"]
            dati["ghi_kwh"] = np.nansum(sw, 2) / 1000.0
            dati["dif_kwh"] = np.nansum(np.clip(sw - dr, 0, None), 2) / 1000.0
            dati["vento"] = np.nanmean(np.hypot(v["wind_u_component_10m"], v["wind_v_component_10m"]), 2)
    giorni = pd.date_range(f"{anno}-01-01", periods=ndays, freq="D")
    df = pd.DataFrame({"cella": np.repeat(np.arange(len(celle)), ndays).astype(np.int32),
                       "data": np.tile(giorni.values, len(celle))})
    for k, a in dati.items():
        df[k] = np.round(a.reshape(-1), 2).astype(np.float32)
    df = df[n_ore.reshape(-1) >= 20].reset_index(drop=True)    # giorni con almeno 20 ore valide
    return df, ultima


# ------------------------------------------------------------------------------------- comandi
def cmd_comuni(args):
    from comuni_punti import costruisci
    sorg = QUI / "sorgenti"
    df = costruisci(sorg)
    fs = FSBlocchi()
    df = assegna_celle(df, fs)
    (QUI / "dati").mkdir(exist_ok=True)
    df.to_parquet(QUI / "dati" / "comuni.parquet", index=False)
    for dom in DOMINI:
        u = df[[f"{dom}_i", f"{dom}_j"]].drop_duplicates()
        log.info("%s: %d comuni in %d celle distinte (%.1f comuni per cella)", dom, len(df), len(u), len(df) / len(u))
    log.info("Metodo del punto: %s", df.metodo_punto.value_counts().to_dict())


def celle_dominio(comuni: pd.DataFrame, dom: str) -> pd.DataFrame:
    c = comuni[[f"{dom}_i", f"{dom}_j"]].drop_duplicates().sort_values([f"{dom}_i", f"{dom}_j"])
    c.columns = ["i", "j"]
    return c.reset_index(drop=True)


def cmd_meteo(args):
    comuni = pd.read_parquet(QUI / "dati" / "comuni.parquet")
    cache = QUI / (args.cache or "cache")
    if args.campione:
        ist = [x.strip().zfill(6) for x in Path(args.campione).read_text().split() if x.strip()]
        comuni = comuni[comuni.istat.isin(ist)]
        cache = QUI / (args.cache or "cache_campione")
    oggi = dt.date.today()
    fs = FSBlocchi()
    domini = args.domini.split(",") if args.domini else list(DOMINI)
    for dom in domini:
        d = DOMINI[dom]
        celle = celle_dominio(comuni, dom)
        cart = cache / dom
        cart.mkdir(parents=True, exist_ok=True)
        celle.to_parquet(cart / "celle.parquet", index=False)
        ultimo = oggi.year if not args.fino_a else args.fino_a
        anni = list(range(args.da or d["anno0"], ultimo + 1))
        for anno in anni:
            dest = cart / f"{anno}.parquet"
            in_corso = anno >= oggi.year - (1 if oggi.month <= 3 else 0)
            if dest.exists() and not (in_corso and args.aggiorna):
                continue
            t = time.time()
            b0 = fs.byte_scaricati
            fc = cart / f"carry_{anno - 1}.npz"
            prima = dict(np.load(fc)) if fc.exists() else None
            df, ultima = giornaliero_anno(fs, dom, celle[["i", "j"]].to_numpy(), anno, prima)
            np.savez(cart / f"carry_{anno}.npz", **ultima)
            tmp = dest.with_suffix(".part")
            df.to_parquet(tmp, index=False, compression="zstd")
            tmp.replace(dest)
            log.info("%s %d: %d celle, %d giorni-cella, %.0f MB letti, %.0f s", dom, anno, len(celle), len(df),
                     (fs.byte_scaricati - b0) / 1e6, time.time() - t)
    log.info("Fatto. Byte letti in totale: %.2f GB in %d richieste", fs.byte_scaricati / 1e9, fs.richieste)


def cmd_stato(args):
    cache = QUI / (args.cache or "cache")
    oggi = dt.date.today()
    for dom, d in DOMINI.items():
        cart = cache / dom
        presenti = sorted(int(p.stem) for p in cart.glob("[0-9]*.parquet")) if cart.exists() else []
        mancanti = [a for a in range(d["anno0"], oggi.year + 1) if a not in presenti]
        dim = sum(p.stat().st_size for p in cart.glob("*.parquet")) / 1e6 if cart.exists() else 0
        print(f"{dom}: {len(presenti)} anni in cache ({dim:.0f} MB), mancanti: {mancanti or 'nessuno'}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("comuni")
    m = sub.add_parser("meteo")
    m.add_argument("--campione", help="file con codici ISTAT (uno per riga): scarica solo le loro celle")
    m.add_argument("--cache", help="cartella cache (predefinita cache/ o cache_campione/)")
    m.add_argument("--domini", help="era5_land,era5 (predefinito: entrambi)")
    m.add_argument("--da", type=int, help="primo anno")
    m.add_argument("--fino-a", type=int, dest="fino_a", help="ultimo anno")
    m.add_argument("--aggiorna", action="store_true", help="riscarica anche l'anno in corso già in cache")
    s = sub.add_parser("stato")
    s.add_argument("--cache")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(QUI / "scarica.log")])
    {"comuni": cmd_comuni, "meteo": cmd_meteo, "stato": cmd_stato}[args.cmd](args)


if __name__ == "__main__":
    main()
