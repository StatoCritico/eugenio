"""Copertura delle fonti LiDAR della pipeline (Fase E, 05/11/2026).

Due strumenti, che scrivono file in `zone/coperture/` (piccoli, nel repository, con fonte e licenza dentro):

- **maschera da un raster a bassa risoluzione** (`python -m edifici3d lidar-copertura`): una sola richiesta al servizio
  della fonte per tutto il riquadro della zona, a passo grosso (100 m); le celle con un valore diventano poligoni, che si
  restringono di mezza cella (così il bordo resta dalla parte sicura) e si semplificano. Serve per le fonti che coprono
  solo una parte della zona, come il DSM della costa 2019 in provincia di Rimini.
- **indice dei file** di una fonte divisa in file irregolari (`python -m edifici3d lidar-indice`): dall'elenco della
  cartella pubblica si legge, file per file, solo l'intestazione del GeoTIFF (poche decine di kB con le richieste a
  intervalli di GDAL, mai il file intero) e se ne annota il riquadro. Un file alla volta con una pausa: nessun
  tentativo di aggirare limiti; un errore ferma l'indice (si può riprendere: i file già letti restano).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path


def maschera_da_raster(percorso: Path, passo: float | None = None, minimo: float = -1000.0):
    """GeoTIFF della fonte (anche a bassa risoluzione) → area con valori validi (shapely), ristretta di mezza cella."""
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import shape
    from shapely.ops import unary_union
    with rasterio.open(percorso) as src:
        a = src.read(1, masked=True)
        z = a.astype("float64").filled(np.nan)
        if src.nodata is not None:
            z[z == src.nodata] = np.nan
        valido = np.isfinite(z) & (z > minimo)
        passo = passo or abs(src.transform.a)
        poli = [shape(g) for g, v in shapes(valido.astype("uint8"), mask=valido, transform=src.transform) if v == 1]
    if not poli:
        return None
    area = unary_union(poli).buffer(-passo / 2).simplify(passo / 4)
    return area if not area.is_empty else None


def scrivi_maschera(area, dest: Path, crs: str, fonte: str, licenza: str, nota: str = "") -> Path:
    from shapely.geometry import mapping
    d = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": crs}},
         "fonte": fonte, "licenza": licenza, "creato": dt.date.today().isoformat(), "nota": nota,
         "features": [{"type": "Feature", "properties": {"area_km2": round(area.area / 1e6, 2)}, "geometry": mapping(area)}]}
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return dest


def maschera_fonte(z: dict, chiave: str, client=None, passo: float = 100.0) -> dict:
    """Scarica una volta la fonte a passo grosso sul riquadro della zona e scrive la maschera dichiarata nel TOML."""
    import httpx
    f = z["fonti"][chiave]
    c = f.get("copertura") or {}
    if not c.get("sorgente_url") or not c.get("maschera"):
        raise ValueError(f"{chiave}: servono copertura.sorgente_url e copertura.maschera nel TOML della zona")
    x0, y0, x1, y1 = z["zona"]["riquadro"]
    w, h = max(1, int(round((x1 - x0) / passo))), max(1, int(round((y1 - y0) / passo)))
    u = c["sorgente_url"].format(x0=x0, y0=y0, x1=x1, y1=y1, w=w, h=h)
    cl = client or httpx.Client(timeout=httpx.Timeout(30, read=300), follow_redirects=True,
                                headers={"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"})
    r = cl.get(u)
    r.raise_for_status()
    cartella = Path(z["_file"]).parent
    tmp = cartella / "coperture" / f".{chiave}_grezzo.tif"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(r.content)
    try:
        area = maschera_da_raster(tmp, passo)
    finally:
        tmp.unlink(missing_ok=True)
    if area is None:
        raise RuntimeError(f"{chiave}: nessuna cella valida nel riquadro della zona")
    dest = scrivi_maschera(area, cartella / c["maschera"], z["zona"]["crs"], f.get("attribuzione", chiave),
                           f.get("licenza", ""), f"maschera a {passo:g} m dal servizio della fonte, ristretta di {passo / 2:g} m")
    return {"maschera": str(dest), "area_km2": round(area.area / 1e6, 2), "celle": w * h}


_HREF = re.compile(r'href="([^"?/][^"]*\.(?:tif|tiff|TIF))"')


def elenco_cartella(url: str, client) -> list[str]:
    r = client.get(url)
    r.raise_for_status()
    return sorted(set(_HREF.findall(r.text)))


def intestazione(url: str) -> tuple[list[float], str | None]:
    """Riquadro di un GeoTIFF remoto leggendo solo l'intestazione (GDAL /vsicurl/ a intervalli)."""
    import rasterio
    with rasterio.Env(CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff,.TIF", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                      GDAL_HTTP_MAX_RETRY="1"):
        with rasterio.open("/vsicurl/" + url) as s:
            b = s.bounds
            crs = s.crs.to_string() if s.crs and s.crs.is_epsg_code else None
    return [round(b.left, 2), round(b.bottom, 2), round(b.right, 2), round(b.top, 2)], crs


def indice_fonte(z: dict, chiave: str, client=None, massimo: int | None = None, pausa: float = 0.3,
                 lettore=intestazione) -> dict:
    """Indice dei file di una fonte a più file (`indice`, `indice_elenco`, `url` con {file} nel TOML della zona)."""
    import httpx
    f = z["fonti"][chiave]
    if not f.get("indice") or not f.get("indice_elenco"):
        raise ValueError(f"{chiave}: servono indice e indice_elenco nel TOML della zona")
    cartella = Path(z["_file"]).parent
    dest = cartella / f["indice"]
    cl = client or httpx.Client(timeout=httpx.Timeout(30, read=120), follow_redirects=True,
                                headers={"User-Agent": "EuGEnio-edifici3d (eugenio.statocritico.it)"})
    vecchio = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
    fatti = {x["nome"]: x for x in vecchio.get("file", [])}
    nomi = elenco_cartella(f["indice_elenco"], cl)
    nuovi = 0
    for n in nomi:
        if n in fatti:
            continue
        if massimo is not None and nuovi >= massimo:
            break
        riq, _ = lettore(f["url"].format(file=n, tavola="", x0=0, y0=0, x1=0, y1=0, e_km=0, n_km=0, e_hm=0, n_hm=0, radice=""))
        fatti[n] = {"nome": n, "riquadro": riq}
        nuovi += 1
        if nuovi % 50 == 0:
            _scrivi_indice(dest, f, z, fatti, len(nomi))
        time.sleep(pausa)
    _scrivi_indice(dest, f, z, fatti, len(nomi))
    return {"indice": str(dest), "file_letti": len(fatti), "file_elencati": len(nomi), "nuovi": nuovi}


def _scrivi_indice(dest: Path, f: dict, z: dict, fatti: dict, elencati: int) -> None:
    d = {"fonte": f.get("attribuzione", ""), "licenza": f.get("licenza", ""), "crs": f.get("crs_file") or z["zona"]["crs"],
         "elenco": f.get("indice_elenco"), "creato": dt.date.today().isoformat(), "file_elencati": elencati,
         "file": sorted(fatti.values(), key=lambda x: x["nome"])}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(dest)
