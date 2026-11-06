"""DTM 5×5 m dell'Emilia-Romagna dal WCS pubblico, a blocchi, in un solo GeoTIFF (05/11/2026, seconda pubblicazione).

Il WCS `wcs/dtm5x5` della Regione (copertura DTM5X5_RDN32_RMD, CC BY 4.0) risponde a GetCoverage 1.0.0 in GeoTIFF
(provato dal container il 05/11/2026: blocco di 10×10 km = 2000×2000 celle, 15 MB, 35 s). Per un comune o una provincia
si chiede a blocchi di al più 10 km, uno alla volta, e si uniscono in un GeoTIFF solo, da passare a `prepara --dtm`.
Per tutta la regione conviene invece scaricare i quattro quadranti TIFF dalla scheda del DTM (~4,9 GB).

  python -m edifici3d dtm-wcs --riquadro 770000 4860000 800000 4890000 --uscita /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif
"""
from __future__ import annotations

import logging
import math
import time
from pathlib import Path

log = logging.getLogger("edifici3d")
LATO = 10_000.0           # m per blocco
MAX_BLOCCHI = 64          # ~80×80 km: oltre si usano i quadranti della scheda


def blocchi(riquadro, lato: float = LATO) -> list[tuple[float, float, float, float]]:
    x0, y0, x1, y1 = riquadro
    if not (x0 < x1 and y0 < y1):
        raise ValueError("riquadro: x_min y_min x_max y_max (EPSG:7791)")
    nx, ny = math.ceil((x1 - x0) / lato), math.ceil((y1 - y0) / lato)
    if nx * ny > MAX_BLOCCHI:
        raise ValueError(f"{nx * ny} blocchi: per una zona così grande scarica i quadranti TIFF dalla scheda del DTM")
    return [(x0 + i * lato, y0 + j * lato, min(x1, x0 + (i + 1) * lato), min(y1, y0 + (j + 1) * lato))
            for j in range(ny) for i in range(nx)]


def scarica(riquadro, uscita: Path, scarica_url=None, pausa: float = 1.0) -> dict:
    """Scarica i blocchi (ripresa: i blocchi già presenti in <uscita>.blocchi/ non si richiedono), li unisce e scrive
    `uscita` (GeoTIFF float32, EPSG:7791, compressione deflate)."""
    import rasterio
    from rasterio.merge import merge
    from . import fonti as F
    f = F.fonti(F.carica_zona("emilia_romagna"))["dtm5"]
    if scarica_url is None:
        import httpx

        def scarica_url(url):
            with httpx.Client(timeout=300, headers={"User-Agent": "EuGEnio/1.0 (+https://eugenio.statocritico.it)"}) as c:
                r = c.get(url)
                r.raise_for_status()
                return r.content
    cartella = Path(str(uscita) + ".blocchi")
    cartella.mkdir(parents=True, exist_ok=True)
    file = []
    for k, b in enumerate(blocchi(riquadro)):
        p = cartella / f"b{k:03d}.tif"
        if not p.exists():
            dati = scarica_url(F.url_wcs(f, b))
            if dati[:4] not in (b"II*\x00", b"MM\x00*"):
                raise RuntimeError(f"blocco {k}: il WCS non ha risposto con un GeoTIFF")
            p.write_bytes(dati)
            log.info("DTM: blocco %d (%s) %d byte", k, b, len(dati))
            time.sleep(pausa)
        file.append(p)
    srcs = [rasterio.open(p) for p in file]
    try:
        mosaico, trasf = merge(srcs)
        prof = srcs[0].profile.copy()
    finally:
        for s in srcs:
            s.close()
    prof.update(height=mosaico.shape[1], width=mosaico.shape[2], transform=trasf, compress="deflate", tiled=True,
                blockxsize=512, blockysize=512, driver="GTiff")
    uscita.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(uscita, "w", **prof) as d:
        d.write(mosaico)
    return {"blocchi": len(file), "celle": [int(mosaico.shape[2]), int(mosaico.shape[1])], "file": str(uscita),
            "licenza": f.licenza, "attribuzione": f.attribuzione}
