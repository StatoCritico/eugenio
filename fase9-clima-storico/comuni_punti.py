"""Elenco dei comuni italiani con il punto da usare per il clima e la sua quota.

Stessa impostazione della fase 3 (meteo_storico/comuni.py):
  * elenco ufficiale ISTAT (Elenco-comuni-italiani.csv, aggiornato da istat.it);
  * punto = **baricentro degli edifici** delle sezioni di censimento ISTAT 2021 (pesi EDI21; se zero la
    popolazione, se zero l'area), dal dataset Gramscii su Hugging Face alla stessa revisione bloccata del
    sito (8aff37c2…), con verifica SHA256;
  * differenza rispetto alla fase 3: per i comuni nati da fusione dopo il 2021 si sommano le sezioni di
    TUTTI i comuni d'origine (alias), non solo del primo trovato;
  * in mancanza di sezioni, baricentro geometrico del poligono (coordinate SVG → UTM 32N → WGS84,
    trasformazione stimata nella fase 3);
  * quota del punto dal modello digitale del terreno Copernicus GLO-90 tramite l'API elevation di
    Open-Meteo (100 punti per chiamata: ~80 chiamate in tutto).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import requests

log = logging.getLogger(__name__)

GRAMSCII_REV = "8aff37c269d8c9ff7fd4748f0f0599810302185b"
GRAMSCII = f"https://huggingface.co/datasets/Gramscii-IT/european-territory-boundaries/resolve/{GRAMSCII_REV}/"
GRAMSCII_TREE = f"https://huggingface.co/api/datasets/Gramscii-IT/european-territory-boundaries/tree/{GRAMSCII_REV}/"
ISTAT_ELENCO = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
ELEVATION = "https://api.open-meteo.com/v1/elevation"

# trasformazione SVG Gramscii -> UTM 32N stimata nella fase 3 (x = S*E + AX ; y = -S*N + AY)
S, AX, AY = 0.0010012596459353985, -313.67365575107954, 5226.851664605516


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _scarica(url: str, dest: Path, sha: str | None = None) -> Path:
    if dest.exists() and dest.stat().st_size > 0 and (sha is None or _sha256(dest) == sha):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Scarico %s", url)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for b in r.iter_content(1 << 20):
                f.write(b)
    if sha and _sha256(tmp) != sha:
        raise RuntimeError(f"SHA256 non corrispondente per {url}")
    tmp.replace(dest)
    return dest


def _sha_gramscii(sorgenti: Path) -> dict[str, str]:
    """SHA256 dei file Gramscii: SHA256SUMS del dataset per i file principali, oid LFS per le sezioni."""
    out = {}
    s = _scarica(GRAMSCII + "SHA256SUMS", sorgenti / "SHA256SUMS")
    for riga in s.read_text().splitlines():
        if riga.strip():
            h, n = riga.split()
            out[n] = h
    cache = sorgenti / "sezioni" / "SHA256SUMS"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        lst = requests.get(GRAMSCII_TREE + "census-sections-2021", timeout=60).json()
        cache.write_text("".join(f"{x['lfs']['oid']}  {x['path'].split('/')[-1]}\n" for x in lst if "lfs" in x))
    for riga in cache.read_text().splitlines():
        h, n = riga.split()
        out["census-sections-2021/" + n] = h
    return out


def _centroide_svg(d: str) -> tuple[float, float] | None:
    A = sx = sy = 0.0
    for sub in re.split(r"(?=M)", d):
        pts = [tuple(map(float, p.split(","))) for p in re.findall(r"-?\d+\.?\d*,-?\d+\.?\d*", sub)]
        if len(pts) < 3:
            continue
        a = cx = cy = 0.0
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            c = x0 * y1 - x1 * y0
            a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
        if abs(a) < 1e-12:
            continue
        a *= 0.5
        A += abs(a); sx += cx / (6 * a) * abs(a); sy += cy / (6 * a) * abs(a)
    return (sx / A, sy / A) if A else None


def _svg_a_lonlat(x: float, y: float) -> tuple[float, float]:
    from pyproj import Transformer
    return Transformer.from_crs(32632, 4326, always_xy=True).transform((x - AX) / S, (AY - y) / S)


def _pesi_sezioni(path: Path) -> pd.DataFrame:
    """Per comune 2021 (PRO_COM): somme pesate delle coordinate dei centroidi delle sezioni."""
    import pyarrow.parquet as pq
    import shapely

    t = pq.read_table(path, columns=["PRO_COM", "POP21", "EDI21", "SHAPE_Area", "geometry"]).to_pandas()
    c = shapely.centroid(shapely.from_wkb(t.geometry.to_numpy()))
    t["x"], t["y"] = shapely.get_x(c), shapely.get_y(c)
    t["PRO_COM"] = t.PRO_COM.astype(str).str.zfill(6)
    righe = []
    for chiave, col in (("e", "EDI21"), ("p", "POP21"), ("a", "SHAPE_Area")):
        w = t[col].fillna(0).astype(float)
        g = pd.DataFrame({"pc": t.PRO_COM, "w": w, "wx": w * t.x, "wy": w * t.y}).groupby("pc").sum()
        g.columns = [f"{chiave}_{c}" for c in g.columns]
        righe.append(g)
    out = pd.concat(righe, axis=1)
    out["pop21"] = t.groupby("PRO_COM").POP21.sum()
    out["edi21"] = t.groupby("PRO_COM").EDI21.sum()
    return out


def quote_dem(lat: np.ndarray, lon: np.ndarray, pausa: float = 1.0) -> np.ndarray:
    out = np.full(len(lat), np.nan)
    for a in range(0, len(lat), 100):
        b = min(a + 100, len(lat))
        par = {"latitude": ",".join(f"{v:.5f}" for v in lat[a:b]),
               "longitude": ",".join(f"{v:.5f}" for v in lon[a:b])}
        for t in range(5):
            try:
                r = requests.get(ELEVATION, params=par, timeout=60)
                r.raise_for_status()
                out[a:b] = r.json()["elevation"]
                break
            except Exception as e:  # noqa: BLE001
                log.warning("elevation %s: %s (riprovo)", a, e)
                time.sleep(10 * (t + 1))
        time.sleep(pausa)   # ben sotto i 600 al minuto del piano gratuito
    return out


def costruisci(sorgenti: Path) -> pd.DataFrame:
    sha = _sha_gramscii(sorgenti)
    geo = json.loads(_scarica(GRAMSCII + "italy-municipalities.geo.json", sorgenti / "comuni.geo.json",
                              sha["italy-municipalities.geo.json"]).read_text(encoding="utf-8"))
    el = pd.read_csv(_scarica(ISTAT_ELENCO, sorgenti / "Elenco-comuni-italiani.csv"), sep=";",
                     encoding="latin-1", dtype=str, keep_default_na=False)   # "NA" = Napoli, "None" = comune
    el = pd.DataFrame({"regione_cod": el.iloc[:, 0].str.zfill(2), "istat": el.iloc[:, 4].str.zfill(6),
                       "nome": el.iloc[:, 6], "regione": el.iloc[:, 10], "provincia": el.iloc[:, 14]}
                      ).set_index("istat")
    alias = {}
    svg = {}
    for s in geo["shapes"]:
        validi = [a for a in s["aliases"] if a in el.index]
        if not validi:
            continue
        istat = validi[-1]
        alias[istat] = list(dict.fromkeys([istat, *s["aliases"]]))
        svg[istat] = _centroide_svg(s["d"])

    pesi = pd.concat([_pesi_sezioni(_scarica(GRAMSCII + f"census-sections-2021/R{r:02d}.parquet",
                                             sorgenti / "sezioni" / f"R{r:02d}.parquet",
                                             sha[f"census-sections-2021/R{r:02d}.parquet"]))
                      for r in range(1, 21)])
    pesi = pesi.groupby(level=0).sum()
    righe = []
    for istat, info in el.iterrows():
        al = [a for a in alias.get(istat, [istat]) if a in pesi.index]
        rec = {"istat": istat, "nome": info.nome, "provincia": info.provincia, "regione_cod": info.regione_cod,
               "regione": info.regione}
        if al:
            p = pesi.loc[al].sum()
            for k in ("e", "p", "a"):
                if p[f"{k}_w"] > 0:
                    rec.update(lon=p[f"{k}_wx"] / p[f"{k}_w"], lat=p[f"{k}_wy"] / p[f"{k}_w"],
                               metodo_punto="edifici_2021" if k == "e" else ("popolazione_2021" if k == "p" else "area_sezioni"),
                               pop21=int(p.pop21), edi21=int(p.edi21), sezioni_da=";".join(al))
                    break
        if "lat" not in rec and svg.get(istat):
            lon, lat = _svg_a_lonlat(*svg[istat])
            rec.update(lon=lon, lat=lat, metodo_punto="baricentro_geometrico")
        if "lat" not in rec:
            log.warning("Comune %s %s senza punto", istat, info.nome)
            continue
        righe.append(rec)
    df = pd.DataFrame(righe)
    df["lat"] = df.lat.round(5)
    df["lon"] = df.lon.round(5)
    log.info("Quote dal DEM (Open-Meteo elevation, Copernicus GLO-90) per %d punti", len(df))
    df["quota_m"] = quote_dem(df.lat.to_numpy(), df.lon.to_numpy())
    return df
