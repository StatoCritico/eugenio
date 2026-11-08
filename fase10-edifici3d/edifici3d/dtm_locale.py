"""DTM 5×5 m dell'Emilia-Romagna dai quadranti preconfezionati (07/11/2026).

La Regione distribuisce il «DTM 5×5 – ultima edizione» (edizione 2025, EPSG:7791, CC BY 4.0, scheda RNDT
`r_emiro:2016-08-08T155835`) in quattro quadranti GeoTIFF zippati (NO, NE, SO, SE; 1,0–1,6 GB ciascuno, 1,4–1,9 GB
il TIFF dentro). Il TIFF non è a tessere né compresso: per un comune se ne legge **solo la finestra** che serve, anche
direttamente dentro lo zip (`/vsizip/`), senza estrarlo e senza caricare il quadrante in memoria. La finestra si
scrive in un GeoTIFF piccolo (deflate, a tessere) da passare a `prepara --dtm` o a `osm-campione --dtm`.

  python -m edifici3d dtm-ritaglia --file /dati/edifici/cc-by/er/grezzi/dtm5/DTM5x5_ed2025_SE_7791.zip \\
         --riquadro 775300 4874100 791400 4891000 --uscita /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif

`prepara --dtm` accetta anche direttamente lo zip o il TIFF del quadrante: ritaglia da sé sul riquadro dei corpi.
Il WCS (`dtm-wcs`) resta come riserva.
"""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path

log = logging.getLogger("edifici3d")
MARGINE = 300.0          # m attorno ai corpi: contesto di 250 m e ombre


def percorso_gdal(file: Path) -> str:
    """Percorso leggibile da rasterio: il TIFF dentro lo zip (/vsizip/) o il file così com'è."""
    file = Path(file)
    if file.suffix.lower() != ".zip":
        return str(file)
    with zipfile.ZipFile(file) as z:
        tif = [n for n in z.namelist() if n.lower().endswith((".tif", ".tiff")) and not n.endswith("/")]
        # tavole del Veneto (08/11/2026): un solo ESRI ASCII Grid per zip, senza .prj
        asc = [n for n in z.namelist() if n.lower().endswith(".asc") and not n.endswith("/")]
    if len(tif) == 1:
        return f"/vsizip/{file.resolve()}/{tif[0]}"
    if not tif and len(asc) == 1:
        return f"/vsizip/{file.resolve()}/{asc[0]}"
    raise ValueError(f"{file.name}: atteso un solo GeoTIFF (o ASCII Grid) nello zip, trovati {len(tif) or len(asc)}")


def grande(file: Path, soglia_mb: float = 300.0) -> bool:
    """Vero per i quadranti (zip o TIFF oltre la soglia): vanno ritagliati prima dell'uso."""
    file = Path(file)
    return file.suffix.lower() == ".zip" or file.stat().st_size > soglia_mb * 1e6


def ritaglia(file: Path, riquadro, uscita: Path, margine: float = 0.0) -> dict:
    """Finestra (x0, y0, x1, y1 nel sistema del DTM, più `margine`) del DTM → GeoTIFF deflate a tessere.
    Legge solo la finestra (memoria ~4 byte per cella: un comune di 16×17 km = 3220×3380 celle ≈ 44 MB)."""
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds, Window
    x0, y0, x1, y1 = (float(v) for v in riquadro)
    if not (x0 < x1 and y0 < y1):
        raise ValueError("riquadro: x_min y_min x_max y_max (EPSG:7791)")
    x0, y0, x1, y1 = x0 - margine, y0 - margine, x1 + margine, y1 + margine
    with rasterio.open(percorso_gdal(file)) as src:
        from rasterio.errors import WindowError
        w = from_bounds(x0, y0, x1, y1, src.transform).round_offsets().round_lengths()
        try:
            w = w.intersection(Window(0, 0, src.width, src.height))
        except WindowError:
            raise ValueError("il riquadro è fuori dal DTM (quadrante sbagliato?)") from None
        if w.width <= 0 or w.height <= 0:
            raise ValueError("il riquadro è fuori dal DTM (quadrante sbagliato?)")
        dati = src.read(1, window=w)
        prof = src.profile.copy()
        nodata = src.nodata
        trasf = src.window_transform(w)
        crs = src.crs
    if nodata is not None:
        validi = int((dati != nodata).sum())
    else:
        validi = int(np.isfinite(dati).sum())
    if validi == 0:
        raise ValueError("nessuna quota valida nel riquadro (quadrante sbagliato?)")
    prof.update(driver="GTiff", width=int(w.width), height=int(w.height), transform=trasf, compress="deflate",
                tiled=True, blockxsize=512, blockysize=512, predictor=3 if str(dati.dtype).startswith("float") else 2)
    uscita = Path(uscita)
    uscita.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(uscita, "w", **prof) as d:
        d.write(dati, 1)
    log.info("DTM ritagliato: %d×%d celle in %s", w.width, w.height, uscita)
    return {"file": str(uscita), "celle": [int(w.width), int(w.height)], "crs": str(crs),
            "riquadro": [round(trasf.c, 1), round(trasf.f + trasf.e * w.height, 1), round(trasf.c + trasf.a * w.width, 1), round(trasf.f, 1)],
            "quote_valide": validi, "byte": uscita.stat().st_size}


def per_corpi(file, corpi_o_riquadro, cartella: Path) -> Path | None:
    """DTM da usare per `prepara`: un file piccolo così com'è; un quadrante (zip o TIFF grande) ritagliato sul riquadro
    dei corpi (più MARGINE) in `cartella/_dtm_ritaglio.tif`; più quadranti (comuni a cavallo, es. NE e SE) ritagliati e
    uniti nello stesso file."""
    if file is None:
        return None
    file_l = [Path(x) for x in file] if isinstance(file, (list, tuple)) else [Path(file)]
    if len(file_l) == 1 and not grande(file_l[0]):
        return file_l[0]
    if isinstance(corpi_o_riquadro, (list, tuple)) and len(corpi_o_riquadro) == 4 and all(isinstance(v, (int, float)) for v in corpi_o_riquadro):
        riq = corpi_o_riquadro
    else:
        b = [c.sagoma.bounds for c in corpi_o_riquadro]
        riq = (min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b))
    dest = Path(cartella) / "_dtm_ritaglio.tif"
    if len(file_l) == 1:
        ritaglia(file_l[0], riq, dest, margine=MARGINE)
        return dest
    import rasterio
    from rasterio.merge import merge
    pezzi = []
    for k, f in enumerate(file_l):
        p = Path(cartella) / f"_dtm_pezzo{k}.tif"
        try:
            ritaglia(f, riq, p, margine=MARGINE)
            pezzi.append(p)
        except ValueError:            # il quadrante non tocca il riquadro
            continue
    if not pezzi:
        raise ValueError("nessun quadrante del DTM copre i corpi")
    srcs = [rasterio.open(p) for p in pezzi]
    try:
        mos, tr = merge(srcs)
        prof = srcs[0].profile.copy()
    finally:
        for x in srcs:
            x.close()
    prof.update(width=mos.shape[2], height=mos.shape[1], transform=tr)
    with rasterio.open(dest, "w", **prof) as d:
        d.write(mos)
    for p in pezzi:
        p.unlink()
    return dest


# ------------------------------------------------------------------------------------------------ DTM del server
# Schede dei DTM regionali per il server (08/11/2026: più DTM insieme, uno per zona). La rotta /api/terreno sceglie per ogni
# tessera il più dettagliato che la copre, poi Copernicus, poi piatto; il «nome» va nella legenda della pagina 3D.
SCHEDE_DTM = {
    "er": {"attribuzione": "Regione Emilia-Romagna – DTM 5×5 m (edizione 2025), CC BY 4.0", "licenza": "CC BY 4.0",
           "nome": "DTM 5 m Regione Emilia-Romagna (CC BY 4.0)", "scheda": "r_emiro:2016-08-08T155835", "crs": None},
    "veneto": {"attribuzione": "Regione del Veneto – DTM 5 m da voli LiDAR, IODL 2.0", "licenza": "IODL 2.0",
               "nome": "DTM 5 m da voli LiDAR Regione del Veneto (IODL 2.0)",
               "scheda": "https://idt2.regione.veneto.it/idt/downloader/download (modelli digitali, DTM 5 m da voli LiDAR)",
               "crs": "EPSG:6876"},
}


def elenco_file(file) -> list[Path]:
    """Un file, una cartella (zip, TIFF, ASCII Grid dentro) o un elenco → file ordinati."""
    out: list[Path] = []
    for f in (file if isinstance(file, (list, tuple)) else [file]):
        f = Path(f)
        if f.is_dir():
            out += sorted(x for x in f.iterdir() if x.suffix.lower() in (".zip", ".tif", ".tiff", ".asc"))
        else:
            out.append(f)
    if not out:
        raise ValueError("nessun file del DTM (zip, TIFF o ASCII Grid)")
    return out


def _data_file(file: Path) -> str | None:
    """Data dei dati: quella del file dentro lo zip (le tavole venete: 2024-06-03), altrimenti del file."""
    import datetime as dt
    try:
        if file.suffix.lower() == ".zip":
            with zipfile.ZipFile(file) as z:
                i = [x for x in z.infolist() if not x.is_dir()][0]
                return dt.date(*i.date_time[:3]).isoformat()
        return dt.date.fromtimestamp(file.stat().st_mtime).isoformat()
    except (OSError, IndexError, ValueError, zipfile.BadZipFile):
        return None


def cog_server(file, uscita: Path, attribuzione: str | None = None, scheda: str | None = None, crs: str | None = None,
               regione: str = "er", licenza: str | None = None, nome: str | None = None) -> dict:
    """DTM (uno o più file: zip, TIFF o ESRI ASCII Grid, anche una cartella) → **un COG unico per il server** (07/11/2026,
    decisione di Paolo: il DTM non va più negli archivi dei comuni; dall'08/11/2026 anche più tavole insieme, mosaicate).
    DEFLATE con predittore, tessere 512, panoramiche: la rotta `/api/terreno/{z}/{x}/{y}.png` (fase4-server/servizio/
    terreno.py) legge a finestra solo i pezzi che servono. Accanto scrive `<uscita>.json` con sistema, passo, riquadro in
    WGS84, licenza, attribuzione, nome per la legenda e data dei dati. `crs` (es. «EPSG:6876») per i file senza sistema
    (le tavole ASCII Grid del Veneto non hanno il .prj); se il file ne ha uno diverso, vale quello del file. Una volta per
    zona, sul server:

      docker compose --profile edifici run --rm edifici-lidar dtm-server \
          --file /dati/edifici/cc-by/er/grezzi/dtm5/DTM5x5_ed2025_SE_7791.zip --uscita /dati/terreno/dtm5_er_se.tif
      docker compose --profile edifici run --rm edifici-lidar dtm-server --regione veneto --crs EPSG:6876 \
          --file /dati/terreno/grezzi/veneto_tv --uscita /dati/terreno/dtm5_veneto_tv.tif
    """
    import json
    import time
    import rasterio
    from rasterio.crs import CRS
    from rasterio.shutil import copy as rcopy
    from rasterio.warp import transform_bounds
    sch = SCHEDE_DTM.get(regione, SCHEDE_DTM["er"])
    attribuzione = attribuzione or sch["attribuzione"]
    t0 = time.time()
    files = elenco_file(file)
    uscita = Path(uscita)
    uscita.parent.mkdir(parents=True, exist_ok=True)
    tmp = uscita.with_name(uscita.name + ".tmp.tif")
    crs_voluto = CRS.from_user_input(crs or sch["crs"]) if (crs or sch["crs"]) else None
    mosaico = uscita.with_name(uscita.name + ".mosaico.tif")
    with rasterio.Env(GDAL_CACHEMAX=512, GDAL_NUM_THREADS="2"):
        if len(files) == 1:
            sorgente = percorso_gdal(files[0])
            with rasterio.open(sorgente) as src:
                senza_crs = src.crs is None
        else:
            senza_crs = True
        if len(files) > 1 or (senza_crs and crs_voluto):
            # più tavole (o una senza sistema): mosaico in un GeoTIFF temporaneo, con il sistema dato
            from rasterio.merge import merge
            srcs = [rasterio.open(percorso_gdal(f)) for f in files]
            try:
                crs_f = {str(x.crs) for x in srcs if x.crs is not None}
                if len(crs_f) > 1:
                    raise ValueError(f"tavole in sistemi diversi: {sorted(crs_f)}")
                crs_m = CRS.from_user_input(crs_f.pop()) if crs_f else crs_voluto
                if crs_m is None:
                    raise ValueError("file senza sistema di riferimento: indica --crs (es. EPSG:6876 per il Veneto)")
                nd = srcs[0].nodata if srcs[0].nodata is not None else -9999.0
                mos, tr = merge(srcs, nodata=nd)
                prof = {"driver": "GTiff", "dtype": mos.dtype.name, "count": 1, "width": mos.shape[2], "height": mos.shape[1],
                        "transform": tr, "crs": crs_m, "nodata": nd, "tiled": True, "blockxsize": 512, "blockysize": 512,
                        "compress": "deflate", "BIGTIFF": "IF_SAFER"}
            finally:
                for x in srcs:
                    x.close()
            with rasterio.open(mosaico, "w", **prof) as d:
                d.write(mos)
            del mos
            sorgente = str(mosaico)
        with rasterio.open(sorgente) as src:
            pred = "3" if src.dtypes[0].startswith("float") else "2"
            rcopy(src, tmp, driver="COG", COMPRESS="DEFLATE", PREDICTOR=pred, BLOCKSIZE="512", OVERVIEWS="AUTO",
                  RESAMPLING="BILINEAR", BIGTIFF="IF_SAFER", NUM_THREADS="2")
            crs_o, b, res, nodata = src.crs, src.bounds, src.res, src.nodata
            lon0, lat0, lon1, lat1 = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    if mosaico.exists():
        mosaico.unlink()
    tmp.replace(uscita)
    date = sorted({d for d in (_data_file(f) for f in files) if d})
    scheda_json = {"file": uscita.name, "sorgente": files[0].name if len(files) == 1 else f"{len(files)} tavole ({files[0].name} … {files[-1].name})",
                   "tavole": len(files), "crs": str(crs_o), "passo_m": list(res),
                   "nodata": nodata, "riquadro": [round(v, 2) for v in b],
                   "riquadro_wgs84": [round(lon0, 6), round(lat0, 6), round(lon1, 6), round(lat1, 6)],
                   "licenza": licenza or sch["licenza"], "attribuzione": attribuzione, "nome": nome or sch["nome"],
                   "scheda": scheda or sch["scheda"], "regione": regione, "data": date[-1] if date else None,
                   "byte": uscita.stat().st_size, "secondi": round(time.time() - t0, 1)}
    uscita.with_suffix(".json").write_text(json.dumps(scheda_json, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("DTM per il server: %s (%.0f MB)", uscita, uscita.stat().st_size / 1e6)
    return scheda_json
