"""Incrocio agricolo (agricolo.py) su due raster minuscoli costruiti qui: carta dei cambiamenti (EPSG:7794) e carta di uso
del suolo (EPSG:3035) attorno al centro di Bologna. Si salta se mancano numpy, rasterio, pyproj o shapely."""
from __future__ import annotations

from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
pyproj = pytest.importorskip("pyproj")
pytest.importorskip("shapely")
from rasterio.transform import from_origin  # noqa: E402

from suolo import agricolo as A  # noqa: E402
from suolo.classi import GRUPPI  # noqa: E402

MAPPA = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "dati" / "mappa"
LON, LAT = 11.3426, 44.4938               # Bologna, piazza Maggiore


def _raster(percorso, crs, x0, y0, dati, dtype, nodata):
    with rasterio.open(percorso, "w", driver="GTiff", width=dati.shape[1], height=dati.shape[0], count=1, dtype=dtype,
                       crs=crs, transform=from_origin(x0, y0, 10, 10), nodata=nodata) as d:
        d.write(dati, 1)


def test_incrocio(tmp_path):
    x, y = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:7794", always_xy=True).transform(LON, LAT)
    camb = np.zeros((40, 40), dtype=np.uint32)
    camb[0:10, 0:10] = 2125            # 100 pixel di fotovoltaico a terra
    camb[20:25, 0:20] = 2111           # 100 pixel di edifici
    camb[30, 0:5] = 122111             # cantiere → edificio: non è nuovo consumo
    camb[31, 0:5] = 2201               # copertura non conteggiata
    _raster(tmp_path / "consumo_suolo_2024-2025.tif", "EPSG:7794", x - 200, y + 200, camb, "uint32", 0)
    # uso: tutto seminativo (11) tranne la metà sinistra, urbana (4)
    u, v = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform(LON, LAT)
    uso = np.full((80, 80), 11, dtype=np.int16)
    xu0, yu0 = u - 400, v + 400
    # i pixel delle righe 20–24 (edifici) cadono in una fascia di N fra y+0 e y−50 m nel sistema 7794: si mettono a
    # «urbano» le righe dell'uso che coprono quella fascia, con un margine
    fascia = pyproj.Transformer.from_crs("EPSG:7794", "EPSG:3035", always_xy=True)
    _, n_alto = fascia.transform(x - 100, y + 2)
    _, n_basso = fascia.transform(x - 100, y - 52)
    r0, r1 = int((yu0 - n_alto) // 10), int((yu0 - n_basso) // 10) + 1
    uso[r0:r1, :] = 4
    _raster(tmp_path / "Uso_del_suolo_2023.tif", "EPSG:3035", xu0, yu0, uso, "int16", -32768)
    e = A.agricolo(tmp_path / "consumo_suolo_2024-2025.tif", tmp_path / "Uso_del_suolo_2023.tif", MAPPA, tmp_path / "out.json")
    ids = [g for g, _, _, _ in GRUPPI]
    it = e["italia"]
    assert e["anno"] == 2025 and e["periodo"] == "2024–2025" and e["pixel_fuori_dai_comuni"] == 0
    assert it["lordo"][ids.index("fv")] == pytest.approx(1.0) and it["lordo"][ids.index("edifici")] == pytest.approx(1.0)
    assert sum(it["lordo"]) == pytest.approx(2.0)                       # 122111 e 2201 esclusi
    assert it["agricolo"][ids.index("fv")] == pytest.approx(1.0)        # fotovoltaico tutto su seminativo
    assert it["agricolo"][ids.index("edifici")] == pytest.approx(0.0)   # edifici su urbano
    assert it["usi"][0] == pytest.approx(1.0)                           # seminativi
    assert list(e["comuni"]) == ["037006"] and e["regioni"]["08"]["lordo"] == it["lordo"]
    assert e["usi_non_agricoli"]["IT"] == {"Urbano e aree assimilate": pytest.approx(1.0)}
    assert (tmp_path / "out.json").exists()
    # prototipo su altre regioni: niente in Emilia-Romagna
    e2 = A.agricolo(tmp_path / "consumo_suolo_2024-2025.tif", tmp_path / "Uso_del_suolo_2023.tif", MAPPA, None, regioni=["03"])
    assert sum(e2["italia"]["lordo"]) == 0 and e2["comuni"] == {}
