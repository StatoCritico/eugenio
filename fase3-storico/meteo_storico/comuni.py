"""Elenco dei comuni con il punto da usare per i dati meteo.

Per ogni comune (confini ISTAT 1/1/2026 dal repository Gramscii) calcola:
  * il **baricentro degli edifici** dalle sezioni di censimento ISTAT 2021 (pesato con EDI21, il
    numero di edifici; se zero con la popolazione; se zero con l'area): è il punto più
    rappresentativo del clima "dove si consuma energia", ed evita che per un comune montano si
    prenda il clima di una cima disabitata;
  * in mancanza (comuni nati da fusioni dopo il 2021 o sezioni non scaricate) il baricentro
    geometrico del poligono, riportato in coordinate geografiche con la trasformazione SVG→UTM 32N
    stimata sui comuni dell'Emilia-Romagna (errore medio ~70 m);
  * codice catastale (Belfiore, usato da Zornade), sigla provincia, regione;
  * il baricentro nel sistema di coordinate della mappa SVG (per le etichette del sito).
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

import httpx
import pandas as pd

from . import gramscii

log = logging.getLogger(__name__)

ISTAT_ELENCO = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"

# trasformazione stimata: x_svg = S*E + AX ; y_svg = -S*N + AY  (E, N in EPSG:32632)
S = 0.0010012596459353985
AX = -313.67365575107954
AY = 5226.851664605516

REGIONI = {
    "01": "Piemonte", "02": "Valle d'Aosta", "03": "Lombardia", "04": "Trentino-Alto Adige", "05": "Veneto",
    "06": "Friuli-Venezia Giulia", "07": "Liguria", "08": "Emilia-Romagna", "09": "Toscana", "10": "Umbria",
    "11": "Marche", "12": "Lazio", "13": "Abruzzo", "14": "Molise", "15": "Campania", "16": "Puglia",
    "17": "Basilicata", "18": "Calabria", "19": "Sicilia", "20": "Sardegna",
}


def scarica(url: str, dest: Path, max_giorni: float | None = None) -> Path:
    import time
    if dest.exists() and dest.stat().st_size > 0 and (
            max_giorni is None or time.time() - dest.stat().st_mtime < max_giorni * 86400):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Scarico %s", url)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for b in r.iter_bytes(1 << 20):
                f.write(b)
    tmp.replace(dest)
    return dest


def _poligoni(d: str) -> list[list[tuple[float, float]]]:
    out = []
    for sub in re.split(r"(?=M)", d):
        pts = [tuple(map(float, p.split(","))) for p in re.findall(r"-?\d+\.?\d*,-?\d+\.?\d*", sub)]
        if len(pts) >= 3:
            out.append(pts)
    return out


def _area_centroide(pts):
    a = cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a *= 0.5
    if abs(a) < 1e-12:
        return 0.0, pts[0][0], pts[0][1]
    return abs(a), cx / (6 * a), cy / (6 * a)


def svg_a_lonlat(x: float, y: float) -> tuple[float, float]:
    from pyproj import Transformer
    e = (x - AX) / S
    n = (AY - y) / S
    lon, lat = Transformer.from_crs(32632, 4326, always_xy=True).transform(e, n)
    return lon, lat


def lonlat_a_svg(lon: float, lat: float) -> tuple[float, float]:
    from pyproj import Transformer
    e, n = Transformer.from_crs(4326, 32632, always_xy=True).transform(lon, lat)
    return S * e + AX, -S * n + AY


def _baricentri_censimento(path: Path) -> dict[str, tuple[float, float, int, int]]:
    import pyarrow.parquet as pq
    from shapely import wkb

    t = pq.read_table(path, columns=["PRO_COM", "POP21", "EDI21", "SHAPE_Area", "geometry"]).to_pandas()
    acc = defaultdict(lambda: {"e": [0.0, 0.0, 0.0], "p": [0.0, 0.0, 0.0], "a": [0.0, 0.0, 0.0], "pop": 0, "edi": 0})
    for pc, pop, edi, area, g in zip(t.PRO_COM, t.POP21, t.EDI21, t.SHAPE_Area, t.geometry):
        c = wkb.loads(g).centroid
        k = acc[str(int(pc)).zfill(6)]
        for chiave, w in (("e", edi or 0), ("p", pop or 0), ("a", area or 0)):
            k[chiave][0] += w
            k[chiave][1] += c.x * w
            k[chiave][2] += c.y * w
        k["pop"] += int(pop or 0)
        k["edi"] += int(edi or 0)
    res = {}
    for pc, k in acc.items():
        for chiave in ("e", "p", "a"):
            w, sx, sy = k[chiave]
            if w > 0:
                res[pc] = (sx / w, sy / w, k["pop"], k["edi"])
                break
    return res


def costruisci(cartella: Path, regioni: list[str] | None, usa_sezioni: bool = True) -> pd.DataFrame:
    """regioni: codici ISTAT a due cifre (es. ["08"]); None = tutta Italia."""
    src = cartella / "sorgenti"
    geo = json.loads(gramscii.scarica("italy-municipalities.geo.json", src)
                     .read_text(encoding="utf-8"))
    el = pd.read_csv(scarica(ISTAT_ELENCO, src / "Elenco-comuni-italiani.csv", max_giorni=30), sep=";", encoding="latin-1",
                     dtype=str)
    # colonne per posizione (le intestazioni ISTAT contengono a capo e note)
    el = pd.DataFrame({
        "regione_cod": el.iloc[:, 0].str.zfill(2), "istat": el.iloc[:, 4].str.zfill(6),
        "nome": el.iloc[:, 6], "regione": el.iloc[:, 10], "provincia": el.iloc[:, 14],
        "belfiore": el.iloc[:, 19], "capoluogo": el.iloc[:, 13].fillna("0").str.strip() == "1",
    }).set_index("istat")

    righe = []
    for s in geo["shapes"]:
        # gli alias contengono anche i codici storici (es. riordino delle province sarde)
        validi = [a for a in s["aliases"] if a in el.index]
        if not validi:
            log.warning("Comune %s %s non presente nell'elenco ISTAT", s["aliases"], s["name"])
            continue
        istat = validi[-1]
        info = el.loc[istat]
        if regioni and info.regione_cod not in regioni:
            continue
        A = sx = sy = 0.0
        for pts in _poligoni(s["d"]):
            a, cx, cy = _area_centroide(pts)
            A += a
            sx += cx * a
            sy += cy * a
        if A == 0:
            continue
        righe.append({"istat": istat, "nome": info.nome, "belfiore": info.belfiore, "provincia": info.provincia,
                      "regione_cod": info.regione_cod, "regione": info.regione, "capoluogo": bool(info.capoluogo),
                      "svg_x": round(sx / A, 2), "svg_y": round(sy / A, 2), "alias": list(s["aliases"])})
    df = pd.DataFrame(righe).set_index("istat")

    bar = {}
    if usa_sezioni:
        for r in sorted(df.regione_cod.unique()):
            p = gramscii.scarica(f"census-sections-2021/R{r}.parquet", src)
            bar.update(_baricentri_censimento(p))
    lat, lon, metodo, pop, edi = [], [], [], [], []
    for istat, r in df.iterrows():
        k = next((a for a in [istat, *r.alias] if a in bar), None)
        if k:
            x, y, p, e = bar[k]
            lon.append(x); lat.append(y); metodo.append("edifici_2021"); pop.append(p); edi.append(e)
        else:
            x, y = svg_a_lonlat(r.svg_x, r.svg_y)
            lon.append(x); lat.append(y); metodo.append("baricentro_geometrico"); pop.append(None); edi.append(None)
    df["lat"] = [round(v, 5) for v in lat]
    df["lon"] = [round(v, 5) for v in lon]
    df["metodo_punto"] = metodo
    df["pop21"] = pop
    df["edi21"] = edi
    return df.reset_index()


def salva(df: pd.DataFrame, cartella: Path) -> None:
    cartella.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cartella / "comuni.parquet", index=False)
    cols = ["istat", "nome", "belfiore", "provincia", "regione_cod", "capoluogo", "lat", "lon", "svg_x", "svg_y",
            "metodo_punto"]
    (cartella / "comuni.json").write_text(
        json.dumps(df[cols].to_dict(orient="records"), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("Salvati %d comuni (%d con baricentro edifici)", len(df), (df.metodo_punto == "edifici_2021").sum())


def carica(cartella: Path, regioni: list[str] | None = None, istat: list[str] | None = None) -> pd.DataFrame:
    df = pd.read_parquet(cartella / "comuni.parquet")
    if regioni:
        df = df[df.regione_cod.isin(regioni)]
    if istat:
        df = df[df.istat.isin(istat)]
    return df
