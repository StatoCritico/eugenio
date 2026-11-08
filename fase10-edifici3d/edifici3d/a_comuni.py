"""Comune intero dai servizi di una regione (gruppo A, 08/11/2026): volumi dal WFS o dall'ArcGIS REST, ritaglio sul
confine del comune e DTM 5 m dal WCS o dall'`exportImage` dell'ImageServer, pronti per `prepara-regione`.

Serve dove la Regione pubblica un servizio aperto senza limiti stretti (Basilicata: WFS `dbgt_0201:un_vol` e WCS
`rsdi_wcs`; Lombardia: DBGT ArcGIS e ImageServer `DTM5_RL_img`) e non c'è un file per comune comodo. Gli URL stanno nei
TOML della zona (`fonti/<regione>.toml`), mai qui. Una richiesta alla volta con una pausa; un errore HTTP ferma tutto.

Uso (dalla cartella fase10-edifici3d):

    python -m edifici3d.a_comuni --zona basilicata --istat 076063 --uscita /dati/grezzi/potenza
    python -m edifici3d.a_comuni --zona lombardia --riquadro 514200 5034400 516000 5040000 --uscita … [--solo-dtm]
    python -m edifici3d.a_comuni --zona piemonte --istat 001272 --file un_vol_torino_32632.geojson \
        --confine Com01012025_g_WGS84.shp --senza-dtm --uscita …      # file già scaricato, confine ISTAT (PRO_COM_T)

Scrive `<uscita>/un_vol.geojson` (solo i volumi con il punto interno dentro il confine, se c'è) e `<uscita>/dtm5.tif`
(GeoTIFF float32 nel sistema della zona, nodata −9999) e stampa il comando `prepara-regione` da usare.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

UA = {"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"}


def _client():
    import httpx
    return httpx.Client(timeout=httpx.Timeout(30, read=300), follow_redirects=True, headers=UA)


# ------------------------------------------------------------------------------------------------ confine del comune
def confine_wfs(fonte: dict, istat: str, client=None):
    """Confine del comune dallo strato WFS dei confini della fonte (`confini` nel TOML; Basilicata: `comune_ist` =
    «17» + ISTAT). Restituisce (geometria shapely nel sistema del servizio, proprietà)."""
    from shapely.geometry import shape
    cl = client or _client()
    r = cl.get(fonte["servizio"], params={"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                                          "typeNames": fonte["confini"], "outputFormat": "application/json",
                                          "srsName": fonte.get("crs_servizio", "EPSG:4326")})
    r.raise_for_status()
    for f in r.json()["features"]:
        p = f["properties"]
        cod = str(p.get("comune_ist") or p.get("pro_com_t") or p.get("istat") or "")
        if cod[-6:] == istat:
            return shape(f["geometry"]), p
    raise SystemExit(f"comune {istat} non trovato nello strato {fonte['confini']}")


def confine_file(percorso: Path, istat: str, crs: str):
    """Confine del comune da un file dei confini (ISTAT `Com<data>_g_WGS84.shp`, campo PRO_COM_T; o un GeoJSON con
    `comune_ist`/`PRO_COM_T`), portato nel sistema `crs`."""
    import pyogrio.raw as PR
    from pyproj import Transformer
    from shapely import from_wkb
    from shapely.ops import transform
    meta, _, geoms, campi = PR.read(str(percorso))
    nomi = [n.lower() for n in meta["fields"]]
    for i, g in enumerate(geoms):
        p = {n: campi[j][i] for j, n in enumerate(nomi)}
        cod = str(p.get("pro_com_t") or p.get("comune_ist") or p.get("pro_com") or "")
        if cod[-6:].zfill(6) == istat:
            geo = from_wkb(g)
            if meta.get("crs") and meta["crs"] != crs:
                tr = Transformer.from_crs(meta["crs"], crs, always_xy=True)
                geo = transform(lambda x, y, z=None: tr.transform(x, y), geo)
            return geo, {"istat": istat, "nome": str(p.get("comune") or p.get("nome_com") or "")}
    raise SystemExit(f"comune {istat} non trovato in {percorso}")


def ritaglia(fc: dict, confine) -> dict:
    """Tiene le feature il cui punto interno cade nel confine (un volume a cavallo va a un solo comune)."""
    from shapely.geometry import shape
    from shapely.prepared import prep
    pc = prep(confine)
    tenute = [f for f in fc["features"] if f.get("geometry") and pc.contains(shape(f["geometry"]).representative_point())]
    return {**fc, "features": tenute}


# ------------------------------------------------------------------------------------------------ DTM
def dtm_wcs(fonte: dict, riquadro, dest: Path, blocco: float = 10000.0, client=None, pausa: float = 1.0) -> Path:
    """DTM dal WCS 2.0.1 (`wcs`, `coverage` del TOML) a blocchi di `blocco` metri, cuciti in un GeoTIFF."""
    cl = client or _client()
    x0, y0, x1, y1 = riquadro
    pezzi = []
    tmp = Path(dest).with_suffix(".pezzi")
    tmp.mkdir(parents=True, exist_ok=True)
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            xa, ya = min(x + blocco, x1), min(y + blocco, y1)
            u = (f"{fonte['wcs']}?service=WCS&version=2.0.1&request=GetCoverage&coverageId={fonte['coverage']}"
                 f"&format=image/tiff&subset=E({x:.0f},{xa:.0f})&subset=N({y:.0f},{ya:.0f})")
            r = cl.get(u)
            r.raise_for_status()
            if not r.content.startswith((b"II*", b"MM\x00*")):
                raise RuntimeError(f"WCS: risposta non TIFF ({r.headers.get('content-type')}): {r.text[:300]}")
            p = tmp / f"{len(pezzi):03d}.tif"
            p.write_bytes(r.content)
            pezzi.append(p)
            x = xa
            time.sleep(pausa)
        y = ya
    return _cuci(pezzi, dest, fonte.get("crs"))


def dtm_arcgis(servizio: str, riquadro, crs: str, dest: Path, passo: float = 5.0, lato_px: int = 2000,
               client=None, pausa: float = 1.0) -> Path:
    """DTM da un ImageServer ArcGIS (`exportImage`, TIFF float32) a blocchi di `lato_px` celle, cuciti in un GeoTIFF."""
    cl = client or _client()
    x0, y0, x1, y1 = riquadro
    lato = passo * lato_px
    sr = crs.split(":")[-1]
    pezzi = []
    tmp = Path(dest).with_suffix(".pezzi")
    tmp.mkdir(parents=True, exist_ok=True)
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            xa, ya = min(x + lato, x1), min(y + lato, y1)
            w, h = max(1, round((xa - x) / passo)), max(1, round((ya - y) / passo))
            q = {"bbox": f"{x},{y},{xa},{ya}", "bboxSR": sr, "imageSR": sr, "size": f"{w},{h}", "format": "tiff",
                 "pixelType": "F32", "interpolation": "RSP_BilinearInterpolation", "f": "image"}
            r = cl.get(f"{servizio.rstrip('/')}/exportImage", params=q)
            r.raise_for_status()
            if not r.content.startswith((b"II*", b"MM\x00*")):
                raise RuntimeError(f"exportImage: risposta non TIFF: {r.text[:300]}")
            p = tmp / f"{len(pezzi):03d}.tif"
            p.write_bytes(r.content)
            pezzi.append(_georeferenzia(p, (x, y, xa, ya), w, h, crs))
            x = xa
            time.sleep(pausa)
        y = ya
    return _cuci(pezzi, dest, crs)


def _georeferenzia(p: Path, rq, w: int, h: int, crs: str) -> Path:
    """L'exportImage in TIFF di solito è georeferenziato; se non lo è, si scrive la georeferenza del riquadro chiesto."""
    import rasterio
    from rasterio.transform import from_bounds
    with rasterio.open(p) as s:
        if s.crs is not None and s.transform is not None and not s.transform.is_identity:
            return p
        a, prof = s.read(1), s.profile
    prof.update(crs=crs, transform=from_bounds(*rq, w, h), driver="GTiff")
    with rasterio.open(p, "w", **prof) as d:
        d.write(a, 1)
    return p


def _cuci(pezzi, dest: Path, crs: str | None) -> Path:
    import numpy as np
    import rasterio
    from rasterio.merge import merge
    srcs = [rasterio.open(p) for p in pezzi]
    nod = srcs[0].nodata if srcs[0].nodata is not None else -9999.0
    a, t = merge(srcs, nodata=nod)
    c = srcs[0].crs or crs
    for s in srcs:
        s.close()
    a = a[0].astype("float32")
    a[(a == nod) | ~np.isfinite(a) | (a < -1000)] = -9999.0
    with rasterio.open(dest, "w", driver="GTiff", width=a.shape[1], height=a.shape[0], count=1, dtype="float32",
                       crs=c, transform=t, nodata=-9999.0, compress="DEFLATE", tiled=True) as d:
        d.write(a, 1)
    for p in pezzi:
        Path(p).unlink(missing_ok=True)
    Path(pezzi[0]).parent.rmdir() if pezzi else None
    return Path(dest)


# ------------------------------------------------------------------------------------------------ comando
def main(argv=None) -> int:
    from . import fonti as F
    from . import regionali as R
    ap = argparse.ArgumentParser(prog="python -m edifici3d.a_comuni", description=__doc__.split("\n\n")[0])
    ap.add_argument("--zona", required=True)
    ap.add_argument("--istat", help="codice ISTAT del comune (6 cifre): confine dallo strato `confini` del TOML")
    ap.add_argument("--riquadro", nargs=4, type=float, help="x0 y0 x1 y1 nel sistema del servizio (senza --istat)")
    ap.add_argument("--uscita", type=Path, required=True)
    ap.add_argument("--max", type=int, default=400000)
    ap.add_argument("--pagina", type=int, default=2000)
    ap.add_argument("--margine", type=float, default=100.0, help="margine del DTM attorno al riquadro (m)")
    ap.add_argument("--file", type=Path, help="GeoJSON già scaricato (nel sistema della zona) da ritagliare, senza servizio")
    ap.add_argument("--confine", type=Path, help="file dei confini (ISTAT, PRO_COM_T) invece dello strato `confini` del TOML")
    ap.add_argument("--solo-dtm", action="store_true")
    ap.add_argument("--senza-dtm", action="store_true")
    a = ap.parse_args(argv)
    zona = F.carica_zona(a.zona)
    f = zona["fonti"]["edifici"]
    a.uscita.mkdir(parents=True, exist_ok=True)
    cl = _client()
    confine = None
    if a.istat and a.confine:
        confine, prop = confine_file(a.confine, a.istat, zona["zona"]["crs"])
    elif a.istat:
        confine, prop = confine_wfs(f, a.istat, cl)
    if a.istat:
        rq = confine.bounds
        (a.uscita / "confine.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": prop, "geometry": confine.__geo_interface__}]}), encoding="utf-8")
    elif a.riquadro:
        rq = tuple(a.riquadro)
    else:
        raise SystemExit("serve --istat o --riquadro")
    esito = {"riquadro": [round(v, 1) for v in rq]}
    if a.file:
        fc = json.loads(Path(a.file).read_text(encoding="utf-8"))
        esito["letti"] = len(fc["features"])
        if confine is not None:
            fc = ritaglia(fc, confine)
        (a.uscita / "un_vol.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        esito["nel_comune"] = len(fc["features"])
    elif not a.solo_dtm:
        grezzo = a.uscita / "un_vol_riquadro.geojson"
        esito["scaricati"] = R.scarica_campione(f, rq, grezzo, max_oggetti=a.max, pagina=a.pagina, client=cl)["oggetti"]
        fc = json.loads(grezzo.read_text(encoding="utf-8"))
        if confine is not None:
            fc = ritaglia(fc, confine)
        (a.uscita / "un_vol.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        grezzo.unlink()
        esito["nel_comune"] = len(fc["features"])
    if not a.senza_dtm:
        m = a.margine
        rd = (rq[0] - m, rq[1] - m, rq[2] + m, rq[3] + m)
        d = next((v for k, v in zona["fonti"].items() if k.startswith("dtm")), None)
        if d is None:
            raise SystemExit("nessuna fonte dtm* nel TOML della zona")
        if d.get("wcs"):
            dtm_wcs(d, rd, a.uscita / "dtm5.tif", client=cl)
        elif d.get("image_server"):
            dtm_arcgis(d["image_server"], rd, zona["zona"]["crs"], a.uscita / "dtm5.tif", passo=d.get("passo", 5.0), client=cl)
        else:
            raise SystemExit("la fonte dtm del TOML non ha né wcs né image_server")
        esito["dtm"] = str(a.uscita / "dtm5.tif")
    print(json.dumps(esito, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
