"""DTM: Cloud Optimized GeoTIFF, quota del terreno per corpo e tessere del terreno per MapLibre.

- `a_cog`: un GeoTIFF qualsiasi (quadrante del DTM 5 m in EPSG:7791, o risposta WCS) → COG compresso (DEFLATE,
  predittore 3, panoramiche), servito da Caddy come file statico (lettura a pezzi con Range).
- `quota`: minimo e mediana del DTM dentro la sagoma di un corpo (§ 7: quota del terreno).
- `terrarium_pmtiles`: tessere raster-dem in codifica Terrarium (PNG, rosso·256 + verde + blu/256 − 32768) in un
  PMTiles, il formato che MapLibre legge per il terreno (`raster-dem`, `encoding: terrarium`) con il protocollo pmtiles.
  MapLibre non legge i COG direttamente: il COG resta per le analisi sul server e per chi scarica i dati.
"""
from __future__ import annotations

import gzip
import io
import math
from pathlib import Path

import numpy as np

from . import tessere

TERRARIUM_ZOOM = (10, 15)


def a_cog(sorgente: Path, dest: Path) -> Path:
    import rasterio
    from rasterio.shutil import copy as rcopy
    dest.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(sorgente) as src:
        rcopy(src, dest, driver="COG", COMPRESS="DEFLATE", PREDICTOR="3" if src.dtypes[0].startswith("float") else "2",
              BLOCKSIZE="512", OVERVIEWS="AUTO", RESAMPLING="BILINEAR")
    return dest


def quota(dtm: Path, sagoma, crs_sagoma: str | None = None) -> dict | None:
    """Minimo e mediana del DTM dentro la sagoma (stesso sistema del DTM). None se fuori dal DTM."""
    import rasterio
    from rasterio.mask import mask
    with rasterio.open(dtm) as src:
        try:
            dati, _ = mask(src, [sagoma.__geo_interface__], crop=True, all_touched=True, filled=False)
        except ValueError:
            return None
    v = dati[0].compressed() if hasattr(dati[0], "compressed") else dati[0].ravel()
    v = v[np.isfinite(v)]
    if not v.size:
        return None
    return {"minimo": float(v.min()), "mediana": float(np.median(v))}


def codifica_terrarium(z: np.ndarray) -> np.ndarray:
    """Quote (m) → immagine RGB Terrarium (uint8, h×w×3); i vuoti diventano 0 m."""
    v = np.nan_to_num(z.astype("float64"), nan=0.0) + 32768.0
    r = np.floor(v / 256.0)
    g = np.floor(v - r * 256.0)
    b = np.floor((v - r * 256.0 - g) * 256.0)
    return np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype("uint8")


def decodifica_terrarium(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype("float64")
    return rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0


def _png(rgb: np.ndarray) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(b, format="PNG", optimize=True)
    return b.getvalue()


def terrarium_pmtiles(dtm: Path, dest: Path, zoom: tuple[int, int] = TERRARIUM_ZOOM, attribuzione: str = "",
                      nome: str = "terreno") -> int:
    """Tessere Terrarium 256×256 in web mercator dal DTM (qualsiasi sistema), dentro i limiti del DTM."""
    import rasterio
    from rasterio.warp import reproject, Resampling, transform_bounds
    from rasterio.transform import from_bounds
    tiles: dict[tuple[int, int, int], bytes] = {}
    with rasterio.open(dtm) as src:
        lon0, lat0, lon1, lat1 = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
        dati = src.read(1, masked=True).filled(np.nan).astype("float32")
        for z in range(zoom[0], zoom[1] + 1):
            x0, y1 = tessere.lonlat_a_tessera(lon0, lat0, z)
            x1, y0 = tessere.lonlat_a_tessera(lon1, lat1, z)
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    w, s, e, n = tessere.limiti_mercatore(z, x, y)
                    out = np.full((256, 256), np.nan, dtype="float32")
                    reproject(dati, out, src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
                              dst_transform=from_bounds(w, s, e, n, 256, 256), dst_crs="EPSG:3857", dst_nodata=np.nan,
                              resampling=Resampling.bilinear)
                    if np.isnan(out).all():
                        continue
                    tiles[(z, x, y)] = _png(codifica_terrarium(out))
    tessere.scrivi_pmtiles(dest, tiles, tipo="png", limiti=(lon0, lat0, lon1, lat1), zoom=zoom,
                           metadati={"name": nome, "attribution": attribuzione, "encoding": "terrarium",
                                     "description": "DTM in codifica Terrarium per MapLibre (raster-dem)"})
    return len(tiles)
