"""Altezze delle sagome dal Copernicus Urban Atlas Building Height 2012 (08/11/2026, decisione di Paolo per Napoli).

Fonte: «Urban Atlas Building Height 2012 (raster 10 m), Europe – version 3, Oct. 2022» del Copernicus Land Monitoring
Service (scheda EEA 42690e05-edf4-43fc-8020-33e130f62023, DOI 10.2909/42690e05-edf4-43fc-8020-33e130f62023). Accesso
«full, open and free» (Regolamento delegato UE 1159/2013) con tre condizioni: citare la fonte, dichiarare che il dato è
stato adattato, non far credere a un'approvazione ufficiale dell'UE. Attribuzione: «© European Union, Copernicus Land
Monitoring Service 2012, European Environment Agency (EEA)». URL del servizio nel TOML della zona (`[fonti.ua_bh]`).

**Attenzione (verifica dell'08/11/2026)**: l'ImageServer pubblico
`UrbanAtlas/UA_BuildingHeights_2012_10m` restituisce **classi**, non metri: la sua tabella degli attributi dice
1 = 2–4 m, 2 = 4–6, 3 = 6–8, 4 = 8–10, 5 = 10–15, 6 = 15–20, 7 = 20–30, 8 = 30–60, 9 = 60–100, 10 = 100–368 m
(i valori 8 e 6 letti con `identify` a Napoli sono quindi le classi 30–60 m e 15–20 m). Il GeoTIFF in metri si scarica
solo con un account del portale Copernicus Land: qui si usano le classi. Per ogni sagoma: **90° percentile delle classi
dei pixel validi dentro la sagoma** (centro del pixel dentro; per le sagome più piccole di un pixel, il pixel del punto
interno), poi l'altezza **centrale della classe** (3, 5, 7, 9, 12,5, 17,5, 25, 45, 80 m; 100 m per l'ultima, il suo
minimo), sempre dichiarata con la classe («Copernicus UA Building Height 2012: classe 15–20 m, 17,5 m»). Le sagome senza
pixel validi restano senza (poi stima). In più `stima_gronda`: mediana delle altezze UA dei vicini entro 100 m (almeno 3),
usata da `altezze_dsm.gronda_da_campi` per le sagome senza pixel.

  python -m edifici3d.altezze_ua --zona campania_napoli scarica --file napoli_dbt.geojson --crs-file EPSG:25833 --uscita ua_napoli.tif
  python -m edifici3d.altezze_ua annota --file napoli_dbt.geojson --crs-file EPSG:25833 --raster ua_napoli.tif --uscita napoli_ua.geojson

Altezze OSM come seconda fonte: **non usate** in un archivio CC BY (l'ODbL chiede la condivisione allo stesso modo del
database derivato; regola del progetto: CC BY e ODbL mai nella stessa cartella). Le sagome al volo restano la sede delle
altezze OSM.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

CLASSI = {1: (2, 4), 2: (4, 6), 3: (6, 8), 4: (8, 10), 5: (10, 15), 6: (15, 20), 7: (20, 30), 8: (30, 60), 9: (60, 100),
          10: (100, 368)}
NODATA = 65535
RAGGIO_VICINI = 100.0
MINIMO_VICINI = 3
ATTRIBUZIONE = "© European Union, Copernicus Land Monitoring Service 2012, European Environment Agency (EEA)"


def altezza_classe(c: int) -> float:
    lo, hi = CLASSI[c]
    return float(lo) if c == 10 else (lo + hi) / 2


def scarica(servizio: str, riquadro_3035: list, uscita: Path, passo: float = 10.0, blocco: int = 4000) -> dict:
    """exportImage a blocchi (al massimo `blocco` pixel per lato) del riquadro in EPSG:3035 → un GeoTIFF U16."""
    import httpx
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin
    x0, y0, x1, y1 = [round(v / passo) * passo for v in riquadro_3035]
    w, h = int((x1 - x0) / passo), int((y1 - y0) / passo)
    dati = np.full((h, w), NODATA, dtype="uint16")
    n = 0
    with httpx.Client(timeout=180, headers={"User-Agent": "EuGEnio (https://eugenio.statocritico.it)"}) as cl:
        for r0 in range(0, h, blocco):
            for c0 in range(0, w, blocco):
                bw, bh = min(blocco, w - c0), min(blocco, h - r0)
                bx0, by1 = x0 + c0 * passo, y1 - r0 * passo
                q = {"bbox": f"{bx0},{by1 - bh * passo},{bx0 + bw * passo},{by1}", "bboxSR": 3035, "imageSR": 3035,
                     "size": f"{bw},{bh}", "format": "tiff", "pixelType": "U16", "noData": NODATA,
                     "interpolation": "RSP_NearestNeighbor", "f": "image"}
                r = cl.get(servizio.rstrip("/") + "/exportImage", params=q)
                r.raise_for_status()
                with MemoryFile(r.content) as mf, mf.open() as src:
                    dati[r0:r0 + bh, c0:c0 + bw] = src.read(1)[:bh, :bw]
                n += 1
    uscita = Path(uscita)
    uscita.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(uscita, "w", driver="GTiff", width=w, height=h, count=1, dtype="uint16", crs="EPSG:3035",
                       transform=from_origin(x0, y1, passo, passo), nodata=NODATA, compress="deflate") as d:
        d.write(dati, 1)
    validi = int((dati != NODATA).sum())
    return {"uscita": str(uscita), "pixel": [w, h], "richieste": n, "pixel_validi": validi, "riquadro_3035": [x0, y0, x1, y1]}


def riquadro_3035(file: Path, crs_file: str | None, margine: float = 100.0) -> list:
    from pyproj import Transformer
    from shapely.geometry import shape
    d = json.loads(Path(file).read_text(encoding="utf-8"))
    crs = crs_file or ((d.get("crs") or {}).get("properties") or {}).get("name") or "EPSG:4326"
    xs, ys = [], []
    for f in d["features"]:
        if f.get("geometry"):
            b = shape(f["geometry"]).bounds
            xs += [b[0], b[2]]; ys += [b[1], b[3]]
    t = Transformer.from_crs(crs, "EPSG:3035", always_xy=True)
    X, Y = t.transform([min(xs), max(xs), min(xs), max(xs)], [min(ys), min(ys), max(ys), max(ys)])
    return [min(X) - margine, min(Y) - margine, max(X) + margine, max(Y) + margine]


def annota(file: Path, crs_file: str | None, raster: Path, uscita: Path, percentile: float = 90.0) -> dict:
    """Aggiunge a ogni sagoma `dsm_gronda`/`dsm_esito`/`dsm_fonte` (stessi campi di altezze_dsm.annota, così
    `gronda_da_campi` li usa per primi), `ua_classe`, `ua_pixel` e `stima_gronda` dai vicini."""
    import numpy as np
    import rasterio
    from pyproj import Transformer
    from rasterio.features import geometry_mask
    from rasterio.windows import from_bounds
    from shapely.geometry import shape
    from shapely.ops import transform
    from shapely.strtree import STRtree

    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)      # shapely.ops.transform (shapely 2.2)
    d = json.loads(Path(file).read_text(encoding="utf-8"))
    crs = crs_file or ((d.get("crs") or {}).get("properties") or {}).get("name") or "EPSG:4326"
    t = Transformer.from_crs(crs, "EPSG:3035", always_xy=True).transform
    conti = {"ok": 0, "fuori": 0}
    per_classe: dict[int, int] = {}
    centri, alt = [], []
    with rasterio.open(raster) as src:
        a_all = src.read(1)
        for f in d["features"]:
            p = f.setdefault("properties", {})
            for k in [k for k, v in p.items() if isinstance(v, list)]:      # «bbox» e simili: non servono
                p.pop(k)
            if not f.get("geometry"):
                continue
            g = transform(t, shape(f["geometry"]))
            if g.is_empty:
                continue
            win = from_bounds(*g.bounds, transform=src.transform).round_offsets().round_lengths()
            r0, c0 = max(int(win.row_off), 0), max(int(win.col_off), 0)
            r1 = min(int(win.row_off + max(win.height, 1)) + 1, src.height)
            c1 = min(int(win.col_off + max(win.width, 1)) + 1, src.width)
            vals = np.array([], dtype="uint16")
            if r1 > r0 and c1 > c0:
                sub = a_all[r0:r1, c0:c1]
                tr = src.window_transform(rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0))
                m = geometry_mask([g.__geo_interface__], out_shape=sub.shape, transform=tr, invert=True)
                vals = sub[m & (sub != NODATA) & (sub >= 1) & (sub <= 10)]
            if vals.size == 0:                                  # sagoma più piccola di un pixel: il pixel del punto interno
                pt = g.representative_point()
                rr, cc = src.index(pt.x, pt.y)
                if 0 <= rr < src.height and 0 <= cc < src.width and 1 <= a_all[rr, cc] <= 10:
                    vals = np.array([a_all[rr, cc]])
            if vals.size == 0:
                p["dsm_esito"] = "fuori"
                conti["fuori"] += 1
                continue
            cl = int(math.ceil(np.percentile(vals.astype("float64"), percentile) - 1e-9))
            cl = min(max(cl, 1), 10)
            h = altezza_classe(cl)
            lo, hi = CLASSI[cl]
            p.update({"dsm_gronda": h, "dsm_esito": "ok", "dsm_pixel": int(vals.size), "ua_classe": f"{lo}–{hi} m",
                      "dsm_fonte": f"Copernicus UA Building Height 2012 (10 m): classe {lo}–{hi} m, {h:g} m "
                                   f"({percentile:g}° percentile delle classi"})
            conti["ok"] += 1
            per_classe[cl] = per_classe.get(cl, 0) + 1
            centri.append(g.centroid); alt.append(h)
    # stima dai vicini per le sagome senza pixel
    if centri:
        albero = STRtree(centri)
        for f in d["features"]:
            p = f.get("properties") or {}
            if p.get("dsm_esito") != "fuori" or not f.get("geometry"):
                continue
            c = transform(t, shape(f["geometry"])).centroid
            vic = [alt[int(i)] for i in albero.query(c.buffer(RAGGIO_VICINI))]
            if len(vic) >= MINIMO_VICINI:
                p["stima_gronda"] = round(float(np.median(vic)), 1)
    uscita = Path(uscita)
    uscita.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return {"sagome": len(d["features"]), "con_classe_ua": conti["ok"], "senza_pixel": conti["fuori"],
            "stimate_dai_vicini": sum(1 for f in d["features"] if (f.get("properties") or {}).get("stima_gronda") is not None),
            "per_classe": {f"{CLASSI[k][0]}–{CLASSI[k][1]} m": v for k, v in sorted(per_classe.items())}, "uscita": str(uscita)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edifici3d.altezze_ua", description=__doc__.split("\n")[0])
    ap.add_argument("--zona", default="campania_napoli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scarica", help="raster delle classi UA del riquadro delle sagome (exportImage a blocchi)")
    s.add_argument("--file", type=Path, required=True); s.add_argument("--crs-file"); s.add_argument("--uscita", type=Path, required=True)
    n = sub.add_parser("annota", help="classe UA per sagoma → campi per prepara-regione")
    n.add_argument("--file", type=Path, required=True); n.add_argument("--crs-file")
    n.add_argument("--raster", type=Path, required=True); n.add_argument("--uscita", type=Path, required=True)
    n.add_argument("--percentile", type=float, default=90.0)
    a = ap.parse_args(argv)
    if a.cmd == "scarica":
        from . import fonti as F
        servizio = F.carica_zona(a.zona)["fonti"]["ua_bh"]["image_server"]
        r = scarica(servizio, riquadro_3035(a.file, a.crs_file), a.uscita)
    else:
        r = annota(a.file, a.crs_file, a.raster, a.uscita, a.percentile)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
