"""Archivio meteo orario per tutti i comuni letto direttamente dai file .om di Open-Meteo su AWS (s3://openmeteo).

Alternativa a `scarica` (API pubblica, ~411 chiamate per comune: impraticabile per tutta Italia) e all'istanza
Open-Meteo propria (troppo lenta: ogni punto apre centinaia di file). Qui si leggono i file per righe di griglia,
tutte le celle di un gruppo di comuni insieme, come la fase 9. Accesso anonimo, nessuna chiave, nessuna quota.

Stesse serie e stesse regole dell'API (verificate il 28/10/2026 su Trento, Bologna, Firenze, Roma, Bari, Palermo):
  * ERA5-Seamless: temperatura e punto di rugiada da ERA5-Land (0,1°), il resto da ERA5 (0,25°), cella più vicina;
    temperatura e punto di rugiada riportati alla quota del comune (6,5 °C/km, quota dal Copernicus DEM 90 m),
    umidità da temperatura e punto di rugiada, diffusa = globale − diretta, vento da u/v, neve = acqua × 0,7 cm/mm;
  * ICON seamless: ICON-D2 (2 km) dove copre, altrimenti ICON-EU (7 km), ora per ora; cella delle 3×3 vicine con la
    quota più simile a quella del comune; temperatura riportata alla quota del comune; globale = diretta + diffusa.
    Su S3 c'è dal 24/05/2023. Il file ICON-D2 del 13–15/01/2024 (chunk 3914) differisce dall'API: escluso.

Struttura su disco uguale a `scarica`: grezzi/<fonte>/<istat>/<anno>.parquet, poi orario/<fonte>/<istat>.parquet,
così `correggi` ed `esporta` restano gli stessi. Riprendibile: i pezzi completi non si rifanno.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import VARIABILI

log = logging.getLogger(__name__)

BUCKET = "openmeteo"
EPOCA = dt.datetime(1970, 1, 1)
GRADIENTE = 0.0065                  # °C/m, come l'API di Open-Meteo
INIZIO_ICON = dt.date(2023, 5, 24)  # primo file ICON-D2 / ICON-EU su S3
FILI = 32

GRIGLIE = {
    "era5":      dict(cartella="copernicus_era5",      lat0=-90.0, lon0=-180.0, res=0.25,   ny=721,  nx=1440, ore=504, ultimo_anno=2021),
    "era5_land": dict(cartella="copernicus_era5_land", lat0=-90.0, lon0=-180.0, res=0.1,    ny=1801, nx=3600, ore=504, ultimo_anno=2021),
    "icon_d2":   dict(cartella="dwd_icon_d2",          lat0=43.18, lon0=-3.94,  res=0.02,   ny=746,  nx=1215, ore=121, ultimo_anno=None),
    "icon_eu":   dict(cartella="dwd_icon_eu",          lat0=29.5,  lon0=-23.5,  res=0.0625, ny=657,  nx=1377, ore=193, ultimo_anno=None),
}
# file noti per essere diversi dall'archivio dell'API (confronto del 28/10/2026): ore lasciate vuote
ESCLUSI = {"icon_d2": {3914}}


# ------------------------------------------------------------------------------------------- lettura S3
class FSBlocchi:
    """Adattatore fsspec per OmFileReader: letture a blocchi allineati con cache LRU (come la fase 9)."""

    def __init__(self, blocco_anno: int = 256 << 10, blocco_chunk: int = 64 << 10, max_blocchi: int = 2048):
        import fsspec
        self.fs = fsspec.filesystem("s3", anon=True)
        self.B_anno, self.B_chunk, self.max = blocco_anno, blocco_chunk, max_blocchi
        self.cache: OrderedDict = OrderedDict()
        self.dim: dict = {}
        self.lock = threading.Lock()
        self.letti = 0

    def size(self, path):
        if path not in self.dim:
            self.dim[path] = self.fs.size(path)
        return self.dim[path]

    def esiste(self, path) -> bool:
        try:
            self.size(path)
            return True
        except FileNotFoundError:
            return False

    def _B(self, path):
        return self.B_chunk if "/chunk_" in path else self.B_anno

    def _blocco(self, path, n):
        B, k = self._B(path), (path, n)
        with self.lock:
            if k in self.cache:
                self.cache.move_to_end(k)
                return self.cache[k]
        for t in range(6):
            try:
                dati = self.fs.cat_file(path, start=n * B, end=min((n + 1) * B, self.size(path)))
                break
            except Exception:
                if t == 5:
                    raise
                time.sleep(2 ** t)
        with self.lock:
            self.letti += len(dati)
            self.cache[k] = dati
            while len(self.cache) > self.max:
                self.cache.popitem(last=False)
        return dati

    def cat_file(self, path, start=None, end=None, **kw):
        tot = self.size(path)
        start = 0 if start is None else (start if start >= 0 else tot + start)
        end = tot if end is None else (end if end >= 0 else tot + end)
        B, parti = self._B(path), []
        for n in range(start // B, (end - 1) // B + 1):
            d = self._blocco(path, n)
            parti.append(d[max(start - n * B, 0):min(end - n * B, len(d))])
        return b"".join(parti)

    def svuota(self, path):
        with self.lock:
            for k in [k for k in self.cache if k[0] == path]:
                del self.cache[k]


def _ora(t: dt.datetime) -> int:
    return int((t - EPOCA).total_seconds() // 3600)


def _pezzi(g: dict, var: str, h0: int, h1: int):
    base = f"{BUCKET}/data/{g['cartella']}/{var}/"
    t = h0
    while t < h1:
        anno = (EPOCA + dt.timedelta(hours=t)).year
        if g["ultimo_anno"] and anno <= g["ultimo_anno"]:
            f0, f1, nome, n = _ora(dt.datetime(anno, 1, 1)), _ora(dt.datetime(anno + 1, 1, 1)), f"year_{anno}.om", None
        else:
            n = t // g["ore"]
            f0, f1, nome = n * g["ore"], (n + 1) * g["ore"], f"chunk_{n}.om"
        b = min(h1, f1)
        yield base + nome, n, t - f0, b - f0
        t = b


def leggi(fs: FSBlocchi, dominio: str, var: str, celle: np.ndarray, h0: int, h1: int) -> np.ndarray:
    """Valori orari [h0, h1) (ore dal 1970, UTC) per le celle (N×2: i, j). N×(h1−h0) float32, NaN dove manca."""
    from omfiles import OmFileReader
    g = GRIGLIE[dominio]
    righe: dict[int, list] = {}
    for k, (i, j) in enumerate(celle):
        if 0 <= i < g["ny"] and 0 <= j < g["nx"]:      # cella fuori dalla griglia: resta vuota
            righe.setdefault(int(i), []).append((k, int(j)))
    out = np.full((len(celle), h1 - h0), np.nan, dtype=np.float32)

    def una(arg):
        path, a, b, i, lst = arg
        r = OmFileReader.from_fsspec(fs, path)
        bb = min(b, r.shape[-1])
        if a >= bb:
            return lst, None
        js = [j for _, j in lst]
        j0, j1 = min(js), max(js) + 1
        if len(r.shape) == 2:            # file più vecchi: griglia appiattita (ny·nx, ore)
            return lst, (r[i * g["nx"] + j0:i * g["nx"] + j1, a:bb], j0)
        return lst, (r[i:i + 1, j0:j1, a:bb][0], j0)

    # tutti i file del periodo e tutte le righe in un'unica coda: la lettura è dominata dall'attesa della rete
    lavori, pos = [], 0
    for path, n, a, b in _pezzi(g, var, h0, h1):
        if n not in ESCLUSI.get(dominio, ()) and fs.esiste(path):
            lavori += [(path, a, b, i, lst, pos) for i, lst in sorted(righe.items())]
        pos += b - a

    def una_pos(arg):
        return arg[5], una(arg[:5])

    with ThreadPoolExecutor(FILI) as ex:
        for p0, (lst, ris) in ex.map(una_pos, lavori):
            if ris is None:
                continue
            blocco, j0 = ris
            for k, j in lst:
                out[k, p0:p0 + blocco.shape[1]] = blocco[j - j0]
    return out


def statico(fs: FSBlocchi, dominio: str, nome: str = "HSURF") -> np.ndarray:
    from omfiles import OmFileReader
    return OmFileReader.from_fsspec(fs, f"{BUCKET}/data/{GRIGLIE[dominio]['cartella']}/static/{nome}.om")[:]


def fine_dati(fs: FSBlocchi, dominio: str) -> int:
    """Ultima ora disponibile (ore dal 1970) secondo meta.json."""
    m = json.loads(fs.fs.cat_file(f"{BUCKET}/data/{GRIGLIE[dominio]['cartella']}/static/meta.json"))
    return int(m["data_end_time"]) // 3600


# --------------------------------------------------------------------------------------- quote e celle
def quote_dem(fs: FSBlocchi, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Quota dal Copernicus DEM 90 m di Open-Meteo (data/copernicus_dem90/static/lat_<grado>.om), come l'API."""
    from omfiles import OmFileReader
    out = np.full(len(lat), np.nan)
    gradi = np.floor(lat).astype(int)

    def una(args):
        k, r, la, lo = args
        y = int((la - math.floor(la)) * 1200)
        x = int((lo + 180) * r.shape[1] / 360)
        return k, float(r[y:y + 1, x:x + 1][0, 0])

    for gr in np.unique(gradi):
        r = OmFileReader.from_fsspec(fs, f"{BUCKET}/data/copernicus_dem90/static/lat_{gr}.om")
        sel = np.flatnonzero(gradi == gr)
        with ThreadPoolExecutor(FILI) as ex:
            for k, z in ex.map(una, [(k, r, lat[k], lon[k]) for k in sel]):
                out[k] = z
        fs.svuota(f"{BUCKET}/data/copernicus_dem90/static/lat_{gr}.om")
    return out


def _vicina(dom, lat, lon):
    g = GRIGLIE[dom]
    return int(round((lat - g["lat0"]) / g["res"])), int(round((lon - g["lon0"]) / g["res"]))


def _per_quota(h: np.ndarray, dom: str, lat: float, lon: float, z: float):
    """Tra le 3×3 celle attorno al punto, quella di terra con quota più simile (come l'API per ICON).
    Isole piccole e lagune (nessuna cella di terra, quota −999 = mare): la cella più vicina, come fa l'API.
    None solo se il punto è fuori dal dominio del modello (quota NaN: fuori dall'area calcolata)."""
    g = GRIGLIE[dom]
    i0, j0 = _vicina(dom, lat, lon)
    if not (0 <= i0 < g["ny"] and 0 <= j0 < g["nx"]):
        return None
    cand = [(i, j) for i in range(i0 - 1, i0 + 2) for j in range(j0 - 1, j0 + 2)
            if 0 <= i < g["ny"] and 0 <= j < g["nx"] and np.isfinite(h[i, j]) and h[i, j] > -999]
    if not cand:
        return (i0, j0) if np.isfinite(h[i0, j0]) else None
    a, b = (lat - g["lat0"]) / g["res"], (lon - g["lon0"]) / g["res"]
    return min(cand, key=lambda c: (abs(h[c] - z), (c[0] - a) ** 2 + (c[1] - b) ** 2))


VERSIONE_CELLE = 2   # 29/10/2026: isole e lagune prendono la cella più vicina invece di restare senza ICON


def _togli_cambiati(archivio: Path, vecchie: pd.DataFrame, nuove: pd.DataFrame) -> None:
    """Se la cella di un comune è cambiata, i pezzi già scaricati per quella fonte vanno rifatti."""
    import shutil
    v = vecchie.set_index("istat")
    for fonte, domini in (("era5", ("era5_land", "era5")), ("icon", ("icon_d2", "icon_eu"))):
        cambiati = []
        for r in nuove.itertuples():
            if r.istat not in v.index:
                continue
            if any((v.at[r.istat, f"{d}_i"], v.at[r.istat, f"{d}_j"]) != (getattr(r, f"{d}_i"), getattr(r, f"{d}_j"))
                   for d in domini):
                cambiati.append(r.istat)
        for istat in cambiati:
            shutil.rmtree(archivio / "grezzi" / fonte / istat, ignore_errors=True)
            (archivio / "orario" / fonte / f"{istat}.parquet").unlink(missing_ok=True)
        if cambiati:
            log.info("%s: celle cambiate per %d comuni, i loro pezzi si rifanno (%s…)", fonte, len(cambiati),
                     ", ".join(cambiati[:5]))


def celle(fs: FSBlocchi, comuni: pd.DataFrame, archivio: Path) -> pd.DataFrame:
    """Per ogni comune: quota DEM e celle di ERA5-Land, ERA5, ICON-D2 (−1 se fuori dominio) e ICON-EU.
    Salvato in archivio/celle_s3.parquet e riusato finché i punti non cambiano."""
    f = archivio / "celle_s3.parquet"
    if f.exists():
        c = pd.read_parquet(f)
        if "versione" not in c.columns:
            c["versione"] = 1
        prima = c.set_index("istat")[["lat", "lon"]]
        ora = comuni.set_index("istat")[["lat", "lon"]]
        if (int(c.versione.iloc[0]) == VERSIONE_CELLE and ora.index.isin(prima.index).all()
                and np.allclose(prima.loc[ora.index].to_numpy(), ora.to_numpy())):
            return c[c.istat.isin(comuni.istat)].set_index("istat").loc[comuni.istat].reset_index()
    out = comuni[["istat", "lat", "lon"]].copy().reset_index(drop=True)
    log.info("Quote del DEM per %d comuni…", len(out))
    out["quota"] = quote_dem(fs, out.lat.to_numpy(), out.lon.to_numpy())
    for dom in ("era5_land", "era5"):
        h = statico(fs, dom)
        ij = [_vicina(dom, a, b) for a, b in zip(out.lat, out.lon)]
        out[f"{dom}_i"] = [x[0] for x in ij]
        out[f"{dom}_j"] = [x[1] for x in ij]
        out[f"{dom}_h"] = [max(float(h[x]), 0.0) if h[x] > -999 else 0.0 for x in ij]
    for dom in ("icon_d2", "icon_eu"):
        h = statico(fs, dom)
        ij = [_per_quota(h, dom, a, b, z) for a, b, z in zip(out.lat, out.lon, out.quota)]
        out[f"{dom}_i"] = [x[0] if x else -1 for x in ij]
        out[f"{dom}_j"] = [x[1] if x else -1 for x in ij]
        out[f"{dom}_h"] = [max(float(h[x]), 0.0) if x else np.nan for x in ij]     # mare (−999): quota 0
    out["versione"] = VERSIONE_CELLE
    if f.exists():
        _togli_cambiati(archivio, pd.read_parquet(f), out)
    archivio.mkdir(parents=True, exist_ok=True)
    out.to_parquet(f, index=False)
    log.info("Celle: ICON-D2 per %d comuni su %d", int((out.icon_d2_i >= 0).sum()), len(out))
    return out


# -------------------------------------------------------------------------------------------- variabili
def umidita(t, td):
    return np.clip(100 * np.exp(17.625 * td / (243.04 + td)) / np.exp(17.625 * t / (243.04 + t)), 0, 100)


def _celle_uniche(c: pd.DataFrame, dom: str):
    ij = c[[f"{dom}_i", f"{dom}_j"]].to_numpy()
    uniche, inv = np.unique(ij, axis=0, return_inverse=True)
    return uniche, inv.reshape(-1)


def _leggi_dom(fs, c, dom, variabili, h0, h1):
    """Legge le celle distinte e restituisce, per ogni variabile, una matrice comuni × ore."""
    uniche, inv = _celle_uniche(c, dom)
    return {v: leggi(fs, dom, v, uniche, h0, h1)[inv] for v in variabili}


def era5(fs, c: pd.DataFrame, h0: int, h1: int) -> dict:
    """ERA5-Seamless come l'API: dict variabile → matrice comuni × ore."""
    land = _leggi_dom(fs, c, "era5_land", ["temperature_2m", "dew_point_2m"], h0, h1)
    e = _leggi_dom(fs, c, "era5", ["temperature_2m", "dew_point_2m", "shortwave_radiation", "direct_radiation",
                                     "wind_u_component_10m", "wind_v_component_10m", "cloud_cover", "precipitation",
                                     "snowfall_water_equivalent"], h0, h1)
    z = c.quota.to_numpy()[:, None]
    dl = (c.era5_land_h.to_numpy()[:, None] - z) * GRADIENTE
    de = (c.era5_h.to_numpy()[:, None] - z) * GRADIENTE
    # ERA5-Land manca sul mare (comuni costieri o isole piccole): si ripiega su ERA5, ora per ora
    usa_land = np.isfinite(land["temperature_2m"]) & np.isfinite(land["dew_point_2m"])
    t = np.where(usa_land, land["temperature_2m"] + dl, e["temperature_2m"] + de)
    td = np.where(usa_land, land["dew_point_2m"] + dl, e["dew_point_2m"] + de)
    sw = e["shortwave_radiation"]
    return {
        "temperature_2m": t, "relative_humidity_2m": umidita(t, td), "shortwave_radiation": sw,
        "diffuse_radiation": np.clip(sw - e["direct_radiation"], 0, None),
        "wind_speed_10m": np.hypot(e["wind_u_component_10m"], e["wind_v_component_10m"]) * 3.6,
        "cloud_cover": e["cloud_cover"], "precipitation": e["precipitation"],
        "snowfall": e["snowfall_water_equivalent"] * 0.7,
    }


VAR_ICON = ["temperature_2m", "relative_humidity_2m", "direct_radiation", "diffuse_radiation", "wind_u_component_10m",
            "wind_v_component_10m", "cloud_cover", "precipitation", "snowfall_water_equivalent",
            "snowfall_convective_water_equivalent"]


def _icon_dom(fs, c, dom, h0, h1):
    x = _leggi_dom(fs, c, dom, VAR_ICON, h0, h1)
    dz = (c[f"{dom}_h"].to_numpy()[:, None] - c.quota.to_numpy()[:, None]) * GRADIENTE
    neve = np.nan_to_num(x["snowfall_water_equivalent"]) + np.nan_to_num(x["snowfall_convective_water_equivalent"])
    neve[np.isnan(x["snowfall_water_equivalent"])] = np.nan
    return {
        "temperature_2m": x["temperature_2m"] + dz, "relative_humidity_2m": x["relative_humidity_2m"],
        "shortwave_radiation": x["direct_radiation"] + x["diffuse_radiation"], "diffuse_radiation": x["diffuse_radiation"],
        "wind_speed_10m": np.hypot(x["wind_u_component_10m"], x["wind_v_component_10m"]) * 3.6,
        "cloud_cover": x["cloud_cover"], "precipitation": x["precipitation"], "snowfall": neve * 0.7,
    }


def icon(fs, c: pd.DataFrame, h0: int, h1: int) -> dict:
    """ICON seamless come l'API: ICON-D2 dove c'è, altrimenti ICON-EU, ora per ora."""
    eu = _icon_dom(fs, c, "icon_eu", h0, h1)
    in_d2 = (c.icon_d2_i >= 0).to_numpy()
    if not in_d2.any():
        return eu
    d2 = _icon_dom(fs, c[in_d2].reset_index(drop=True), "icon_d2", h0, h1)
    # ore dei file esclusi: vuote anche nell'EU per i comuni coperti dal D2 (l'API lì non coincide con nessuno dei due)
    escl = np.zeros(h1 - h0, bool)
    for n in ESCLUSI["icon_d2"]:
        a, b = n * GRIGLIE["icon_d2"]["ore"] - h0, (n + 1) * GRIGLIE["icon_d2"]["ore"] - h0
        escl[max(a, 0):max(min(b, h1 - h0), 0)] = True
    out = {}
    for v in VARIABILI:
        x = eu[v].copy()
        y = d2[v]
        x[in_d2] = np.where(np.isfinite(y), y, x[in_d2])
        x[np.ix_(in_d2, escl)] = np.nan
        out[v] = x
    return out


ARROTONDA = {"temperature_2m": 1, "relative_humidity_2m": 0, "shortwave_radiation": 1, "diffuse_radiation": 1,
             "wind_speed_10m": 1, "cloud_cover": 0, "precipitation": 2, "snowfall": 2}


# ----------------------------------------------------------------------------------------------- scarico
def _pezzo(archivio: Path, fonte: str, istat: str, anno: int) -> Path:
    return archivio / "grezzi" / fonte / istat / f"{anno}.parquet"


def _completo(p: Path, fine: pd.Timestamp) -> bool:
    if not p.exists():
        return False
    try:
        ultimo = pd.read_parquet(p, columns=["time"]).time.max()
    except Exception:
        return False
    return pd.notna(ultimo) and ultimo >= fine


def scarica(archivio: Path, comuni: pd.DataFrame, fonte: str, dal: dt.date, al: dt.date | None = None,
            per_gruppo: int = 400) -> None:
    """Scarica `fonte` ("era5" o "icon") per i comuni, anno per anno e a gruppi di comuni vicini."""
    fs = FSBlocchi()
    c = celle(fs, comuni, archivio)
    if fonte == "era5":
        fine = min(fine_dati(fs, "era5"), fine_dati(fs, "era5_land"))
    else:
        dal = max(dal, INIZIO_ICON)
        adesso = _ora(dt.datetime.utcnow()) - 24          # ieri: le ore future nei file sono previsioni
        fine = min(adesso, fine_dati(fs, "icon_eu"))
    fine_t = EPOCA + dt.timedelta(hours=fine)
    if al:
        fine_t = min(fine_t, dt.datetime.combine(al, dt.time(23)))
    c = c.sort_values(["lat", "lon"]).reset_index(drop=True)      # gruppi compatti: righe di griglia condivise
    gruppi = [c.iloc[k:k + per_gruppo].reset_index(drop=True) for k in range(0, len(c), per_gruppo)]
    t0, b0 = time.time(), fs.letti
    for anno in range(dal.year, fine_t.year + 1):
        ini = max(dt.datetime(anno, 1, 1), dt.datetime.combine(dal, dt.time()))
        fin = min(dt.datetime(anno, 12, 31, 23), fine_t)
        if ini > fin:
            continue
        h0, h1 = _ora(ini), _ora(fin) + 1
        tempi = pd.date_range(ini, fin, freq="h", tz="UTC")
        for ng, gr in enumerate(gruppi, 1):
            da_fare = [not _completo(_pezzo(archivio, fonte, r.istat, anno), tempi[-1]) for r in gr.itertuples()]
            if not any(da_fare):
                continue
            sel = gr[da_fare].reset_index(drop=True)
            t1 = time.time()
            dati = era5(fs, sel, h0, h1) if fonte == "era5" else icon(fs, sel, h0, h1)
            for k, r in enumerate(sel.itertuples()):
                df = pd.DataFrame({"time": tempi})
                for v in VARIABILI:
                    df[v] = np.round(dati[v][k], ARROTONDA[v]).astype("float32")
                validi = df[VARIABILI].notna().any(axis=1).to_numpy()
                if validi.any():                          # come l'API: via le ore finali senza dati
                    df = df.iloc[: int(np.flatnonzero(validi)[-1]) + 1]
                p = _pezzo(archivio, fonte, r.istat, anno)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".tmp")
                df.to_parquet(tmp, index=False, compression="zstd")
                tmp.replace(p)
            log.info("%s %d gruppo %d/%d: %d comuni, %.0f s (totale %.1f GB letti, %.0f min)", fonte, anno, ng,
                     len(gruppi), len(sel), time.time() - t1, (fs.letti - b0) / 1e9, (time.time() - t0) / 60)
