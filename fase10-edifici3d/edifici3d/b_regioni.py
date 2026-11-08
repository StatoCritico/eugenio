"""Lettori regionali del gruppo B (08/11/2026): preparazione dei file di Toscana, Puglia, Marche, Sicilia e FVG per
`prepara-regione` (gli adattatori stanno in `edifici3d/adattatori/b_*.py`).

Gli adattatori leggono una riga alla volta (proprietà + poligono); qui si fanno i passi che chiedono più righe o più
file insieme, e si scrive un GeoJSON «pronto» che `prepara-regione --file` legge con l'adattatore della zona:

- `toscana-wfs`: unità volumetriche «multiscala» dal WFS MapServer della Regione Toscana (GML 3.1.1, EPSG:3003, al più
  3.000 oggetti per richiesta): riquadri di 1 km divisi in quattro quando tornano pieni, doppioni tolti per `uv_pk`;
- `puglia-ctr`: CTR 1:5.000 per elemento (SHP `_pol`, `_poi`, `_lin`): poligoni degli edifici divisi dalle linee
  «dividente edificio civile», cavedi tolti, punti «quota gronda edificio» assegnati ai pezzi e «quota piede fabbricato»
  entro 3 m;
- `puglia-dtm`: DTM 8 m per elemento (ASCII Grid con la virgola decimale) → un GeoTIFF nel sistema della zona;
- `marche-dbgt`: DBGT 2019 `edificio` + `punto_quotato` (tutta la regione) → edifici del comune con la quota al piede
  (punto «al piede» dentro la sagoma o entro 1 m) e la quota di gronda del punto «in gronda»; le righe ripetute
  per gli edifici con più usi (stesso `gid`) diventano una, con gli usi in `usi`;
- `palermo-uv`: unità volumetriche del Comune di Palermo con i doppioni tolti (stessa sagoma ripetuta con altezze
  diverse: si tiene la più alta);
- `fvg-wfs`: CTRN ed. 2 del FVG da più strati (fogli) del WFS, nel confine del comune;
- `toscana-dtm`: DTM LiDAR 2023 del Comune di Firenze (zip di tessere ASCII 0,5 m, Deflate64) → GeoTIFF a passo più
  grosso, una tessera alla volta (`unzip -p`), senza estrarre lo zip.

Confine del comune: i file `dati/mappa/RR.json` del sito (ISTAT, unità amministrative 2026 generalizzate, CC BY 4.0,
percorsi SVG in UTM 32N con la scala di `fase3-storico/meteo_storico/comuni.py`), con un margine (150 m) perché sono
generalizzati a circa 100 m: si tengono gli edifici il cui punto interno cade nel confine allargato.

Comandi (dalla cartella fase10-edifici3d):
  python -m edifici3d.b_regioni toscana-wfs --istat 048017 --uscita firenze_uv.geojson
  python -m edifici3d.b_regioni toscana-dtm --zip MDT_LIDAR_2023_ASCII.zip --passo 2 --uscita dtm_firenze_7791.tif
  python -m edifici3d.b_regioni puglia-ctr --ctr 438061_ctr.zip 438062_ctr.zip … --uscita bari_ctr.geojson
  python -m edifici3d.b_regioni puglia-dtm --asc 438061_asc.zip … --crs EPSG:25833 --uscita dtm_bari_25833.tif
  python -m edifici3d.b_regioni marche-dbgt --edifici edificio.zip --punti punto_quotato.zip --istat 042002 --uscita ancona.geojson
  python -m edifici3d.b_regioni palermo-uv --file unita_volumetriche_7792.zip --uscita palermo_uv.geojson
  python -m edifici3d.b_regioni fvg-wfs --istat 032006 --strati EDIFICI:EDIFICATO_CTRN_ED2_110 EDIFICI:EDIFICATO_CTRN_ED2_131 --uscita trieste.geojson
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import statistics as st
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

log = logging.getLogger(__name__)
QUI = Path(__file__).resolve().parent.parent
MAPPE = QUI.parent / "fase5-sito" / "sito" / "dati" / "mappa"
UA = {"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"}

# scala dei percorsi SVG dei file di mappa del sito (confini_gl.js): svg = S·E + AX, −S·N + AY, in UTM 32N (WGS84)
_S, _AX, _AY = 0.0010012596459353985, -313.67365575107954, 5226.851664605516
REGIONE_ISTAT = {"048": "09", "072": "16", "042": "11", "082": "19", "032": "06"}   # provincia → regione (i 5 comuni)


# --------------------------------------------------------------------------------------------- confine del comune
def confine_comune(istat: str, crs: str, margine: float = 150.0, cartella: Path | None = None):
    """Confine ISTAT generalizzato del comune (shapely, nel sistema `crs`), allargato di `margine` metri."""
    from pyproj import Transformer
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    cartella = Path(cartella or MAPPE)
    reg = REGIONE_ISTAT.get(istat[:3])
    file = [cartella / f"{reg}.json"] if reg else sorted(cartella.glob("[0-2][0-9].json"))
    for f in file:
        m = json.loads(f.read_text(encoding="utf-8"))
        c = next((x for x in m.get("comuni", []) if x.get("istat") == istat), None)
        if c is None:
            continue
        anelli = []
        for parte in str(c["d"]).split("M"):
            p = parte.replace("Z", "").strip()
            if not p:
                continue
            pts = [tuple(map(float, q.split(","))) for q in p.split("L")]
            pts = [((x - _AX) / _S, (_AY - y) / _S) for x, y in pts]
            if len(pts) >= 3:
                anelli.append(Polygon(pts).buffer(0))
        g = unary_union(anelli)
        tr = Transformer.from_crs("EPSG:32632", crs, always_xy=True)
        import numpy as np
        import shapely
        g = shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
        return g.buffer(margine) if margine else g
    raise ValueError(f"comune {istat} non trovato in {cartella}")


def _dentro(geom, confine) -> bool:
    return confine is None or confine.contains(geom.representative_point())


def scrivi_geojson(feature: list[dict], dest: Path, crs: str, meta: dict | None = None) -> Path:
    out = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": crs}}, "features": feature}
    if meta:
        out["eugenio"] = meta
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(dest)
    return dest


def _semplice(v):
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _leggi(percorso, strato=None, bbox=None, geometria=True):
    import warnings
    import pyogrio.raw as R
    from shapely import from_wkb
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        meta, _f, geom, campi = R.read(str(percorso), layer=strato, bbox=tuple(bbox) if bbox else None,
                                       read_geometry=geometria)
    nomi = list(meta["fields"])
    righe = [{k: _semplice(v) for k, v in zip(nomi, val)} for val in zip(*campi)] if nomi else []
    geoms = list(from_wkb(geom)) if geometria and geom is not None else [None] * len(righe)
    return righe, geoms, meta


# --------------------------------------------------------------------------------------------- Toscana (WFS GML)
def toscana_wfs(servizio: str, strato: str, riquadro, dest: Path, confine=None, lato: float = 1000.0,
                limite: int = 3000, pausa: float = 0.5, client=None) -> dict:
    """Unità volumetriche dal WFS 1.1.0 di MapServer (GML) nel riquadro (EPSG:3003): riquadri di `lato` metri, divisi in
    quattro se tornano `limite` oggetti; doppioni tolti per `uv_pk`. Con `confine` (EPSG:3003) si saltano i riquadri
    fuori e si tengono i volumi col punto interno dentro. Scrive un GeoJSON in EPSG:3003."""
    import tempfile
    import httpx
    from shapely.geometry import box, mapping
    cl = client or httpx.Client(timeout=httpx.Timeout(30, read=180), follow_redirects=True, headers=UA)
    x0, y0, x1, y1 = riquadro
    coda = [(x, y, min(x + lato, x1), min(y + lato, y1)) for x in _passi(x0, x1, lato) for y in _passi(y0, y1, lato)]
    visti, feat, richieste, divisi = set(), [], 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        while coda:
            q = coda.pop(0)
            if confine is not None and not confine.intersects(box(*q)):
                continue
            sep = "&" if "?" in servizio else "?"
            url = (f"{servizio}{sep}service=WFS&version=1.1.0&request=GetFeature&typeName={strato}"
                   f"&bbox={q[0]},{q[1]},{q[2]},{q[3]},EPSG:3003&srsName=EPSG:3003&maxFeatures={limite}")
            for tentativo in range(3):
                try:
                    r = cl.get(url)
                    r.raise_for_status()
                    break
                except httpx.HTTPError:
                    if tentativo == 2:
                        raise
                    time.sleep(5 * (tentativo + 1))
            richieste += 1
            f = Path(tmp) / "r.gml"
            f.write_bytes(r.content)
            if b"featureMember" not in r.content:
                if b"ExceptionReport" in r.content or b"ServiceException" in r.content:
                    raise RuntimeError(f"WFS: {r.text[:400]}")
                continue
            righe, geoms, _ = _leggi(f)
            if len(righe) >= limite and (q[2] - q[0]) > 60:
                mx, my = (q[0] + q[2]) / 2, (q[1] + q[3]) / 2
                coda[:0] = [(q[0], q[1], mx, my), (mx, q[1], q[2], my), (q[0], my, mx, q[3]), (mx, my, q[2], q[3])]
                divisi += 1
                continue
            for p, g in zip(righe, geoms):
                k = p.get("uv_pk") or p.get("featureid") or p.get("gml_id")
                if k in visti or g is None or g.is_empty:
                    continue
                if confine is not None and not _dentro(g, confine):
                    continue
                visti.add(k)
                p.pop("gml_id", None)
                feat.append({"type": "Feature", "properties": p, "geometry": mapping(g)})
            time.sleep(pausa)
    scrivi_geojson(feat, dest, "EPSG:3003", {"fonte": "Regione Toscana – Edificato multiscala, unità volumetriche (CC BY 4.0)",
                                             "servizio": servizio, "strato": strato, "richieste": richieste})
    return {"oggetti": len(feat), "richieste": richieste, "riquadri_divisi": divisi, "file": str(dest)}


def _passi(a, b, passo):
    v = a
    while v < b:
        yield v
        v += passo


def toscana_dtm(zip_dtm: Path, dest: Path, passo: float = 2.0, riquadro=None, crs: str = "EPSG:7791") -> dict:
    """DTM LiDAR del Comune di Firenze (zip di tessere ASCII Grid 0,5 m, nomi `32_<E>_<N>`, Deflate64): una tessera alla
    volta con `unzip -p` (niente estrazione su disco), media a blocchi fino a `passo` metri, mosaico GeoTIFF float32.
    Il sistema reale delle tessere è RDN2008/UTM 32N (EPSG:7791) anche se la scheda dice Roma40 (verifica dell'08/11/2026)."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    voci = subprocess.run(["unzip", "-Z1", str(zip_dtm)], capture_output=True, text=True, check=True).stdout.split()
    voci = [v for v in voci if v.lower().endswith(".asc")]
    teste = {}
    for v in voci:
        m = re.search(r"(\d{6})_(\d{7})", Path(v).stem)
        if m:
            teste[v] = (float(m.group(1)), float(m.group(2)))
    if riquadro:
        x0, y0, x1, y1 = riquadro
        teste = {v: t for v, t in teste.items() if t[0] < x1 and t[0] + 500 > x0 and t[1] < y1 and t[1] + 500 > y0}
    if not teste:
        raise ValueError("nessuna tessera nel riquadro")
    xs = [t[0] for t in teste.values()]
    ys = [t[1] for t in teste.values()]
    X0, Y0, X1, Y1 = min(xs), min(ys), max(xs) + 500, max(ys) + 500
    W, H = int(round((X1 - X0) / passo)), int(round((Y1 - Y0) / passo))
    out = np.full((H, W), np.nan, dtype="float32")
    lette = 0
    for v in sorted(teste):
        testo = subprocess.run(["unzip", "-p", str(zip_dtm), v], capture_output=True, check=True).stdout
        a, (xll, yll, cs) = _asc(testo)
        f = int(round(passo / cs))
        h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
        a = a[:h, :w].reshape(h // f, f, w // f, f)
        with np.errstate(all="ignore"):
            b = np.nanmean(a, axis=(1, 3)).astype("float32")
        r0, c0 = int(round((Y1 - (yll + h * cs)) / passo)), int(round((xll - X0) / passo))
        r0 = max(0, r0)
        hh, ww = min(b.shape[0], H - r0), min(b.shape[1], W - c0)
        blocco = out[r0:r0 + hh, c0:c0 + ww]
        np.copyto(blocco, b[:hh, :ww], where=np.isnan(blocco))
        lette += 1
    prof = dict(driver="GTiff", width=W, height=H, count=1, dtype="float32", crs=crs,
                transform=from_origin(X0, Y1, passo, passo), nodata=-9999.0, compress="DEFLATE", predictor=3, tiled=True)
    out[~np.isfinite(out)] = -9999.0
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dest, "w", **prof) as d:
        d.write(out, 1)
    return {"tessere": lette, "riquadro": [X0, Y0, X1, Y1], "passo": passo, "file": str(dest)}


def _asc(testo: bytes, virgola: bool = False):
    """ASCII Grid (ESRI) → (array float32 con NaN, (xll, yll, cella)); `virgola`: decimali con la virgola (Puglia)."""
    import numpy as np
    if virgola:
        testo = testo.replace(b",", b".")
    righe = testo.split(b"\n", 6)
    testa = {}
    for r in righe[:6]:
        k, v = r.split()[:2]
        testa[k.decode().lower()] = float(v)
    corpo = righe[6] if len(righe) > 6 else b""
    nc, nr = int(testa["ncols"]), int(testa["nrows"])
    a = np.array(corpo.split(), dtype="float32")[: nc * nr].reshape(nr, nc)
    nd = testa.get("nodata_value")
    if nd is not None:
        a[a == nd] = np.nan
    xll = testa.get("xllcorner", testa.get("xllcenter", 0) - testa["cellsize"] / 2)
    yll = testa.get("yllcorner", testa.get("yllcenter", 0) - testa["cellsize"] / 2)
    return a, (xll, yll, testa["cellsize"])


# --------------------------------------------------------------------------------------------- Puglia (CTR 1:5.000)
# codici LAYER degli edifici della CTR (prime 4 cifre o codice intero); esclusi tettoie, cavedi, lucernai, diroccati,
# interrati, aree (portico, aggetto, sottopassaggio), muri e gradinate
PUGLIA_EDIFICI = {
    "31110000": "edificio civile", "31111000": "edificio in costruzione", "31130000": "trullo",
    "31210000": "capannone", "31310000": "chiesa", "31340000": "campanile", "31350000": "cappella cimitero",
    "31540000": "castello", "31620000": "baracca", "31720000": "silos", "31730000": "serbatoio", "31740000": "ciminiera",
    "35180000": "cabina elettrica", "34320000": "faro",
}
PUGLIA_PREFISSI = ("3111", "3112", "3113", "3121", "3131", "3132", "3133", "3134", "3135")   # altre varianti di edificio
PUGLIA_ESCLUSI = {"31114000", "31110100", "31214000"}         # diroccato, interrato, capannone diroccato
PUGLIA_CAVEDIO = "31670000"
PUGLIA_GRONDA, PUGLIA_PIEDE, PUGLIA_COLMO = "quota gronda edificio", "quota piede fabbricato", "quota colmo edificio"
PUGLIA_DIVIDENTE = ("dividente edificio",)


def _puglia_edificio(layer: str) -> str | None:
    layer = str(layer or "").strip()
    if layer in PUGLIA_ESCLUSI:
        return None
    if layer in PUGLIA_EDIFICI:
        return PUGLIA_EDIFICI[layer]
    if layer.startswith(PUGLIA_PREFISSI):
        return "edificio"
    return None


def _shp_da_zip(zipfile_: Path, suffisso: str) -> str:
    import zipfile
    with zipfile.ZipFile(zipfile_) as z:
        n = next((x for x in z.namelist() if x.lower().endswith(f"_{suffisso}.shp")), None)
    if n is None:
        raise ValueError(f"{zipfile_}: manca *_{suffisso}.shp")
    return f"/vsizip/{Path(zipfile_).resolve()}/{n}"


def _allunga(linea, d: float = 0.3):
    """Linea con i due estremi allungati di `d` metri (le dividenti si fermano a pochi cm dal contorno)."""
    from shapely.geometry import LineString
    c = list(linea.coords)
    if len(c) < 2:
        return linea

    def est(a, b):
        dx, dy = a[0] - b[0], a[1] - b[1]
        n = math.hypot(dx, dy) or 1.0
        return (a[0] + dx / n * d, a[1] + dy / n * d)
    c[0] = est(c[0], c[1])
    c[-1] = est(c[-1], c[-2])
    return LineString([(x[0], x[1]) for x in c])


def _dividi(poligono, linee):
    """Poligono diviso dalle linee (poligonizzazione del contorno + linee); i pezzi fuori (cavedi, buchi) si tolgono."""
    from shapely.ops import polygonize, unary_union
    if not linee:
        return [poligono]
    tagli = [l.intersection(poligono.buffer(0.5)) for l in linee]
    tagli = [t for t in tagli if not t.is_empty]
    if not tagli:
        return [poligono]
    rete = unary_union([poligono.boundary] + tagli)
    pezzi = [p for p in polygonize(rete) if p.area > 0.5 and poligono.contains(p.representative_point())]
    pezzi = [p.intersection(poligono) for p in pezzi]
    out = []
    for p in pezzi:
        if p.geom_type == "Polygon" and p.area > 0.5:
            out.append(p)
        elif p.geom_type in ("MultiPolygon", "GeometryCollection"):
            out += [q for q in getattr(p, "geoms", []) if q.geom_type == "Polygon" and q.area > 0.5]
    tot = sum(p.area for p in out)
    if not out or abs(tot - poligono.area) > 0.05 * poligono.area + 1:
        return [poligono]                # poligonizzazione non riuscita: si tiene il poligono intero
    return out


def puglia_ctr(zips: list[Path], dest: Path, crs_file: str = "EPSG:32633", confine=None, raggio_piede: float = 3.0) -> dict:
    """CTR 1:5.000 della Puglia per elemento → corpi pronti per l'adattatore `puglia_ctr` (GeoJSON in `crs_file`)."""
    from shapely.geometry import Point, mapping
    from shapely.strtree import STRtree
    edifici, cavedi, linee, gronde, piedi, colmi = [], [], [], [], [], []
    for zf in zips:
        el = re.search(r"(\d{6})", Path(zf).name)
        el = el.group(1) if el else Path(zf).stem
        r, g, _ = _leggi(_shp_da_zip(zf, "pol"))
        for p, geom in zip(r, g):
            if geom is None or geom.is_empty:
                continue
            lay = str(p.get("LAYER") or "")
            if lay == PUGLIA_CAVEDIO:
                cavedi.append(_pol2d(geom))
                continue
            tipo = _puglia_edificio(lay)
            if tipo:
                g2 = _pol2d(geom)
                if g2 is not None and g2.area >= 2:
                    zs = [c[2] for c in _coord_z(geom)]
                    edifici.append({"el": el, "layer": lay, "descr": p.get("DESCR"), "tipo": tipo, "g": g2,
                                    "z_contorno": st.median(zs) if zs else None, "z_min": min(zs) if zs else None})
        r, g, _ = _leggi(_shp_da_zip(zf, "poi"))
        for p, geom in zip(r, g):
            d = str(p.get("DESCR") or "").strip().lower()
            if geom is None or d not in (PUGLIA_GRONDA, PUGLIA_PIEDE, PUGLIA_COLMO):
                continue
            pt = geom if geom.geom_type == "Point" else list(geom.geoms)[0]
            z = pt.z if pt.has_z else None
            if z is None or z <= -100:
                continue
            {PUGLIA_GRONDA: gronde, PUGLIA_PIEDE: piedi, PUGLIA_COLMO: colmi}[d].append((Point(pt.x, pt.y), z))
        r, g, _ = _leggi(_shp_da_zip(zf, "lin"))
        for p, geom in zip(r, g):
            if geom is not None and str(p.get("DESCR") or "").lower().startswith(PUGLIA_DIVIDENTE):
                for l in getattr(geom, "geoms", [geom]):
                    linee.append(_allunga(_lin2d(l)))
    # doppioni ai bordi degli elementi (lo stesso edificio in due elementi vicini): si tiene il primo
    albero = STRtree([e["g"] for e in edifici])
    tenuti, tolti = [], 0
    preso = [False] * len(edifici)
    for i, e in enumerate(edifici):
        doppio = False
        for j in albero.query(e["g"]):
            j = int(j)
            if j < i and preso[j] and edifici[j]["el"] != e["el"]:
                a = edifici[j]["g"]
                inter = a.intersection(e["g"]).area
                if inter > 0.8 * min(a.area, e["g"].area):
                    doppio = True
                    break
        if doppio:
            tolti += 1
            continue
        preso[i] = True
        tenuti.append(e)
    edifici = tenuti
    # cavedi tolti dai poligoni (se il poligono non ha già il buco)
    if cavedi:
        tc = STRtree(cavedi)
        for e in edifici:
            dentro = [cavedi[int(j)] for j in tc.query(e["g"]) if e["g"].contains(cavedi[int(j)].representative_point())]
            if dentro:
                from shapely.ops import unary_union
                g2 = e["g"].difference(unary_union(dentro))
                if g2.geom_type == "MultiPolygon":
                    g2 = max(g2.geoms, key=lambda x: x.area)
                if g2.geom_type == "Polygon" and g2.area > 2:
                    e["g"] = g2
    tl = STRtree(linee) if linee else None
    tg = STRtree([p for p, _ in gronde]) if gronde else None
    tp = STRtree([p for p, _ in piedi]) if piedi else None
    tco = STRtree([p for p, _ in colmi]) if colmi else None
    feat, cont = [], Counter()
    for k, e in enumerate(edifici):
        g = e["g"]
        if confine is not None and not _dentro(g, confine):
            cont["fuori dal confine"] += 1
            continue
        ll = [linee[int(j)] for j in tl.query(g)] if tl is not None else []
        pezzi = _dividi(g, ll) if ll else [g]
        cont["divisi"] += len(pezzi) > 1
        gr_ed = [gronde[int(j)][1] for j in tg.query(g, predicate="intersects")] if tg is not None else []
        pi_ed = [piedi[int(j)][1] for j in tp.query(g.buffer(raggio_piede), predicate="intersects")] if tp is not None else []
        ed_id = f"{e['el']}_{k}"
        for n, pz in enumerate(pezzi):
            zona = pz.buffer(0.3)
            gr = [gronde[int(j)][1] for j in tg.query(zona, predicate="intersects")] if tg is not None else []
            pi = [piedi[int(j)][1] for j in tp.query(pz.buffer(raggio_piede), predicate="intersects")] if tp is not None else []
            co = [colmi[int(j)][1] for j in tco.query(zona, predicate="intersects")] if tco is not None else []
            fonte_g = "punti di gronda del corpo"
            if not gr and gr_ed:
                gr, fonte_g = gr_ed, "punti di gronda dell'edificio (isolato)"
            fonte_p = "punti al piede entro 3 m"
            if not pi and pi_ed:
                pi, fonte_p = pi_ed, "punti al piede dell'edificio"
            if not pi and e["z_min"] is not None and e["z_min"] > -50:
                pi, fonte_p = [e["z_min"]], "quota del contorno del poligono"
            prop = {"id": f"{ed_id}_{n}" if len(pezzi) > 1 else ed_id, "edificio": ed_id, "elemento": e["el"],
                    "layer": e["layer"], "descr": e["descr"], "tipo": e["tipo"],
                    "quota_gronda": round(st.median(gr), 2) if gr else None, "n_gronde": len(gr),
                    "quota_piede": round(min(pi), 2) if pi else None, "quota_colmo": round(max(co), 2) if co else None,
                    "fonte_gronda": fonte_g if gr else None, "fonte_piede": fonte_p if pi else None,
                    "pezzi": len(pezzi)}
            cont["corpi"] += 1
            cont["senza gronda"] += not gr
            feat.append({"type": "Feature", "properties": prop, "geometry": mapping(pz)})
    scrivi_geojson(feat, dest, crs_file, {"fonte": "Regione Puglia – Carta Tecnica Regionale 1:5.000 (IODL 2.0)",
                                          "elementi": [Path(z).name for z in zips]})
    return {"edifici": len(edifici), "doppioni_ai_bordi": tolti, "corpi": cont["corpi"], "edifici_divisi": cont["divisi"],
            "corpi_senza_gronda": cont["senza gronda"], "fuori_dal_confine": cont["fuori dal confine"],
            "punti_gronda": len(gronde), "punti_piede": len(piedi), "linee_dividenti": len(linee), "file": str(dest)}


def _coord_z(g):
    if g.geom_type == "Polygon":
        return [c for c in g.exterior.coords if len(c) > 2]
    if g.geom_type == "MultiPolygon":
        return [c for p in g.geoms for c in p.exterior.coords if len(c) > 2]
    return []


def _pol2d(g):
    from shapely.geometry import Polygon
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda x: x.area)
    if g.geom_type != "Polygon":
        return None
    p = Polygon([(c[0], c[1]) for c in g.exterior.coords], [[(c[0], c[1]) for c in r.coords] for r in g.interiors])
    if not p.is_valid:
        p = p.buffer(0)
        if p.geom_type == "MultiPolygon":
            p = max(p.geoms, key=lambda x: x.area)
    return p if p.geom_type == "Polygon" else None


def _lin2d(l):
    from shapely.geometry import LineString
    return LineString([(c[0], c[1]) for c in l.coords])


def puglia_dtm(zips: list[Path], dest: Path, crs_file: str = "EPSG:32633", crs: str = "EPSG:25833") -> dict:
    """DTM 8 m della Puglia (un ASCII Grid con la virgola decimale per elemento) → mosaico GeoTIFF nel sistema `crs`.
    Le celle a 0 m sul mare restano (sono quota vera della costa); −9999 è il vuoto."""
    import zipfile
    import numpy as np
    import rasterio
    from rasterio.merge import merge
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin
    memorie, aperti = [], []
    for zf in zips:
        with zipfile.ZipFile(zf) as z:
            n = next(x for x in z.namelist() if x.lower().endswith(".asc"))
            a, (xll, yll, cs) = _asc(z.read(n), virgola=True)
        m = MemoryFile()
        with m.open(driver="GTiff", width=a.shape[1], height=a.shape[0], count=1, dtype="float32", crs=crs_file,
                    transform=from_origin(xll, yll + a.shape[0] * cs, cs, cs), nodata=np.nan) as d:
            d.write(a, 1)
        memorie.append(m)
        aperti.append(m.open())
    mos, t = merge(aperti, nodata=np.nan)
    for a in aperti:
        a.close()
    tmp = Path(dest).with_suffix(".tmp.tif")
    with rasterio.open(tmp, "w", driver="GTiff", width=mos.shape[2], height=mos.shape[1], count=1, dtype="float32",
                       crs=crs_file, transform=t, nodata=np.nan) as d:
        d.write(mos[0], 1)
    from .regionali import riproietta_dtm
    riproietta_dtm(tmp, Path(dest), crs, passo=8.0) if crs != crs_file else tmp.replace(dest)
    tmp.unlink(missing_ok=True)
    return {"elementi": len(zips), "file": str(dest), "crs": crs}


# --------------------------------------------------------------------------------------------- Marche (DBGT 2019)
MARCHE_PIEDE = "al piede"         # sed_name del punto «su manufatto / edificio – al piede»
MARCHE_GRONDA = "gronda"          # «in gronda o su copertura»


def marche_dbgt(edifici: Path, punti: Path, dest: Path, confine=None, riquadro=None, raggio: float = 1.0) -> dict:
    """DBGT 2019 della Regione Marche: `edificio` (quota di gronda `edifc_qm`) + `punto_quotato` (punti al piede e in
    gronda) → edifici del comune con `quota_piede` (minimo dei punti al piede dentro la sagoma o entro `raggio` m) e
    `quota_gronda_punto` (massimo dei punti in gronda dentro). GeoJSON in EPSG:7792."""
    from shapely.geometry import mapping
    from shapely.strtree import STRtree
    bbox = riquadro or (confine.bounds if confine is not None else None)
    re_, ge_, _ = _leggi(edifici, bbox=bbox)
    rp, gp, _ = _leggi(punti, bbox=bbox)
    piedi, gronde, tipi = [], [], Counter()
    for p, g in zip(rp, gp):
        if g is None:
            continue
        s = str(p.get("sed_name") or "").lower()
        tipi[s] += 1
        for pt in getattr(g, "geoms", [g]):
            z = numero_z(p.get("pt_quo_q"), pt)
            if z is None:
                continue
            from shapely.geometry import Point
            if MARCHE_PIEDE in s:
                piedi.append((Point(pt.x, pt.y), z))
            elif MARCHE_GRONDA in s or "copertura" in s:
                gronde.append((Point(pt.x, pt.y), z))
    tp = STRtree([p for p, _ in piedi]) if piedi else None
    tg = STRtree([p for p, _ in gronde]) if gronde else None
    feat, cont, per_gid = [], Counter(), {}
    for p, g in zip(re_, ge_):
        k = p.get("gid")
        if k is not None and k in per_gid:            # un edificio con più usi = più righe con lo stesso gid
            q = per_gid[k]
            if p.get("uso_name") and p.get("uso_name") not in q["usi"]:
                q["usi"].append(p.get("uso_name"))
            cont["righe d'uso unite"] += 1
            continue
        g2 = _pol2d(g) if g is not None else None
        if g2 is None or g2.area < 2:
            cont["geometria non valida"] += 1
            continue
        if confine is not None and not _dentro(g2, confine):
            cont["fuori dal confine"] += 1
            continue
        pi = [piedi[int(j)][1] for j in tp.query(g2.buffer(raggio), predicate="intersects")] if tp is not None else []
        gr = [gronde[int(j)][1] for j in tg.query(g2, predicate="intersects")] if tg is not None else []
        q = dict(p)
        q["quota_piede"] = round(min(pi), 2) if pi else None
        q["quota_gronda_punto"] = round(max(gr), 2) if gr else None
        q["usi"] = [p.get("uso_name")] if p.get("uso_name") else []
        if k is not None:
            per_gid[k] = q
        cont["con piede"] += bool(pi)
        feat.append({"type": "Feature", "properties": q, "geometry": mapping(g2)})
    for f in feat:
        f["properties"]["usi"] = "; ".join(f["properties"]["usi"])
    scrivi_geojson(feat, dest, "EPSG:7792", {"fonte": "Regione Marche – DBGT 2019 (CC BY 4.0)"})
    return {"edifici": len(feat), "con_piede": cont["con piede"], "righe_uso_unite": cont["righe d'uso unite"], "fuori_dal_confine": cont["fuori dal confine"],
            "punti_piede": len(piedi), "punti_gronda": len(gronde), "tipi_punto": dict(tipi.most_common(8)), "file": str(dest)}


def numero_z(v, pt=None):
    try:
        z = float(str(v).replace(",", ".")) if v is not None else None
    except ValueError:
        z = None
    if (z is None or z <= -100) and pt is not None and pt.has_z:
        z = pt.z
    return z if z is not None and z > -100 else None


# --------------------------------------------------------------------------------------------- Palermo
def palermo_uv(file: Path, dest: Path, confine=None) -> dict:
    """Unità volumetriche del Comune di Palermo: doppioni (stessa sagoma, stesso ID, altezze diverse) ridotti al più
    alto; resto invariato. GeoJSON in EPSG:7792 con i nomi dei campi del file."""
    from shapely.geometry import mapping
    righe, geoms, meta = _leggi(file)
    migliori: dict = {}
    ordine = []
    for p, g in zip(righe, geoms):
        if g is None or g.is_empty:
            continue
        k = (p.get("ID"), g.wkb)
        h = p.get("ALTEZZA") or 0
        if k not in migliori:
            ordine.append(k)
            migliori[k] = (p, g, 1)
        else:
            q, gq, n = migliori[k]
            migliori[k] = ((p, g, n + 1) if h > (q.get("ALTEZZA") or 0) else (q, gq, n + 1))
    feat, fuori = [], 0
    for k in ordine:
        p, g, n = migliori[k]
        if confine is not None and not _dentro(g, confine):
            fuori += 1
            continue
        p = dict(p)
        if n > 1:
            p["doppioni"] = n
        feat.append({"type": "Feature", "properties": p, "geometry": mapping(g)})
    scrivi_geojson(feat, dest, str(meta.get("crs") or "EPSG:7792"),
                   {"fonte": "Comune di Palermo – Carta tecnica comunale, unità volumetriche (CC BY 4.0)"})
    return {"letti": len(righe), "scritti": len(feat), "doppioni_tolti": len(righe) - len(ordine), "fuori_dal_confine": fuori,
            "file": str(dest)}


# --------------------------------------------------------------------------------------------- FVG (più fogli)
def fvg_wfs(fonte: dict, strati: list[str], riquadro, dest: Path, confine=None, max_oggetti: int = 200000) -> dict:
    """CTRN del FVG da più strati (uno per foglio) del WFS, riquadro in EPSG:6708; si tengono gli elementi nel confine;
    doppioni tra fogli (stessa sagoma) tolti."""
    import tempfile
    from shapely.geometry import shape
    from .regionali import scarica_campione
    feat, visti, per_strato = [], set(), {}
    with tempfile.TemporaryDirectory() as tmp:
        for s in strati:
            f = Path(tmp) / "s.geojson"
            r = scarica_campione(dict(fonte, strato=s), riquadro, f, max_oggetti, pagina=5000)
            d = json.loads(f.read_text(encoding="utf-8"))
            n = 0
            for x in d.get("features", []):
                g = shape(x["geometry"]) if x.get("geometry") else None
                if g is None or g.is_empty:
                    continue
                if confine is not None and not _dentro(g, confine):
                    continue
                k = (round(g.centroid.x, 1), round(g.centroid.y, 1), round(g.area))
                if k in visti:
                    continue
                visti.add(k)
                x["properties"]["strato"] = s.split(":")[-1]
                feat.append(x)
                n += 1
            per_strato[s] = {"scaricati": r["oggetti"], "tenuti": n}
    scrivi_geojson(feat, dest, fonte.get("crs_servizio", "EPSG:6708"),
                   {"fonte": "Regione Autonoma Friuli Venezia Giulia – IRDAT, Edificato CTRN (CC BY 4.0)"})
    return {"oggetti": len(feat), "strati": per_strato, "file": str(dest)}


# --------------------------------------------------------------------------------------------- comandi
def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from . import fonti as F
    p = argparse.ArgumentParser(prog="edifici3d.b_regioni", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for nome in ("toscana-wfs", "puglia-ctr", "marche-dbgt", "palermo-uv", "fvg-wfs"):
        s = sub.add_parser(nome)
        s.add_argument("--uscita", type=Path, required=True)
        s.add_argument("--istat", help="comune (6 cifre): si tengono gli edifici nel confine ISTAT (+150 m)")
        s.add_argument("--riquadro", nargs=4, type=float, help="x0 y0 x1 y1 nel sistema del file o del servizio")
        s.add_argument("--confini", type=Path, help="cartella dati/mappa del sito (predefinita: fase5-sito/sito/dati/mappa)")
        if nome == "toscana-wfs":
            s.add_argument("--zona", default="toscana")
            s.add_argument("--lato", type=float, default=1000.0)
        if nome == "puglia-ctr":
            s.add_argument("--ctr", type=Path, nargs="+", required=True, help="zip <elemento>_ctr.zip")
        if nome == "marche-dbgt":
            s.add_argument("--edifici", type=Path, required=True); s.add_argument("--punti", type=Path, required=True)
        if nome == "palermo-uv":
            s.add_argument("--file", type=Path, required=True)
        if nome == "fvg-wfs":
            s.add_argument("--zona", default="friuli_venezia_giulia")
            s.add_argument("--strati", nargs="+", required=True)
    d = sub.add_parser("puglia-dtm")
    d.add_argument("--asc", type=Path, nargs="+", required=True); d.add_argument("--uscita", type=Path, required=True)
    d.add_argument("--crs", default="EPSG:25833")
    t = sub.add_parser("toscana-dtm")
    t.add_argument("--zip", type=Path, required=True); t.add_argument("--uscita", type=Path, required=True)
    t.add_argument("--passo", type=float, default=2.0); t.add_argument("--riquadro", nargs=4, type=float)
    t.add_argument("--istat", help="tessere che toccano il confine del comune (riquadro)")
    t.add_argument("--confini", type=Path)
    a = p.parse_args(argv)
    sistemi = {"toscana-wfs": "EPSG:3003", "puglia-ctr": "EPSG:32633", "marche-dbgt": "EPSG:7792", "palermo-uv": "EPSG:7792",
               "fvg-wfs": "EPSG:6708", "toscana-dtm": "EPSG:7791"}
    confine = confine_comune(a.istat, sistemi[a.cmd], cartella=a.confini) if getattr(a, "istat", None) else None
    if a.cmd == "toscana-wfs":
        f = F.carica_zona(a.zona)["fonti"]["edifici"]
        rq = a.riquadro or (confine.bounds if confine is not None else None)
        if rq is None:
            raise SystemExit("--istat o --riquadro")
        esito = toscana_wfs(f["servizio"], f["strato"], rq, a.uscita, confine, a.lato)
    elif a.cmd == "toscana-dtm":
        rq = a.riquadro or (confine_comune(a.istat, "EPSG:7791", 0, a.confini).bounds if a.istat else None)
        esito = toscana_dtm(a.zip, a.uscita, a.passo, rq)
    elif a.cmd == "puglia-ctr":
        esito = puglia_ctr(a.ctr, a.uscita, confine=confine)
    elif a.cmd == "puglia-dtm":
        esito = puglia_dtm(a.asc, a.uscita, crs=a.crs)
    elif a.cmd == "marche-dbgt":
        esito = marche_dbgt(a.edifici, a.punti, a.uscita, confine, a.riquadro)
    elif a.cmd == "palermo-uv":
        esito = palermo_uv(a.file, a.uscita, confine)
    else:
        f = F.carica_zona(a.zona)["fonti"]["edifici"]
        rq = a.riquadro or (confine.bounds if confine is not None else None)
        if rq is None:
            raise SystemExit("--istat o --riquadro")
        esito = fvg_wfs(f, a.strati, rq, a.uscita, confine)
    print(json.dumps(esito, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
