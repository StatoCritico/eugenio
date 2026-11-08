"""Integrazione dell'08/11/2026: adattatore del DBGT del Comune di Venezia e altezze Copernicus Urban Atlas (Napoli).
Dati sintetici con gli stessi campi dei file veri, nessuna rete."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon, box, mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edifici3d import altezze_dsm as AD, altezze_ua as UA, fonti as F, regionali as R  # noqa: E402


def _uv(av, qb, qg, qe, por="01", **kw):
    return {"UN_VOL_AV": av, "UN_VOL_QB": qb, "UN_VOL_QG": qg, "UN_VOL_QE": qe, "UN_VOL_POR": por, "UN_VOL_EX": "0",
            "CODICE": "020101", **kw}


def test_venezia_regole_e_toml():
    ad = R.ADATTATORI["venezia_dbgt"]
    z = F.carica_zona("venezia")
    assert z["fonti"]["edifici"]["adattatore"] == "venezia_dbgt" and z["fonti"]["edifici"]["licenza"] == "IODL 2.0"
    assert z["archivi"]["IODL 2.0"] == "iodl" and z["zona"]["codice"] == "ven" and ad.crs_file == "EPSG:3004"
    g = box(0, 0, 10, 12)
    c = ad.corpo(_uv(20.53, 2.5, 23.03, 23.18, ID_UV="V3", CEDIUV="E7", EDIFC_USO="030102"), g, None, None)
    assert c.gronda == 20.53 and c.quota_terreno == 2.5 and c.colmo is None and c.edificio == "E7" and c.uso == "ospedale"
    assert c.extra["destinazione"] == "sede di ospedale"
    c = ad.corpo(_uv(7.13, 2.72, 9.85, 12.48, ID_UV="V2"), g, None, None)
    assert c.colmo == pytest.approx(9.76) and c.tetto == "capanna" and c.id == "V2"
    # campanile: colmo entro 25 m sopra la gronda; quota di estrusione assurda → resta la gronda
    assert ad.corpo(_uv(73.72, 2.0, 75.72, 95.48), g, None, None).colmo == pytest.approx(93.48)
    assert ad.corpo(_uv(5.0, 2.0, 7.0, 60.0), g, None, None).colmo is None
    assert ad.corpo(_uv(4.0, 2.0, 6.0, 6.0, por="08"), g, None, None) is None          # sotterraneo
    assert ad.corpo(_uv(0.3, 2.0, 2.3, 2.3), g, None, None) is None                     # sotto 0,5 m
    assert ad.corpo(_uv(0.0, 2.0, 2.0, 2.0, por="91"), g, None, None) is None
    righe = [(_uv(5.0, 2.0, 7.0, 7.5), g), (_uv(5.0, 2.0, 7.1, 7.5), g)]
    assert "UN_VOL_QG − UN_VOL_QB = UN_VOL_AV in 1 su 2" in R.controlla(righe, ad)["coerenza"]


def test_venezia_unisci_raw(tmp_path):
    import pyogrio.raw as PR
    from shapely import to_wkb
    vol = [box(0, 0, 10, 10), box(20, 0, 30, 10), box(100, 100, 105, 105)]
    edi = [box(-1, -1, 31, 11)]
    PR.write(tmp_path / "UN_VOL.shp", np.array([to_wkb(g) for g in vol], dtype=object),
             [np.array([5.0, 6.0, 3.0]), np.array([2.0, 2.0, 1.0]), np.array([7.0, 8.0, 4.0]), np.array(["01", "01", "04"], dtype=object)],
             ["UN_VOL_AV", "UN_VOL_QB", "UN_VOL_QG", "UN_VOL_POR"], geometry_type="Polygon", driver="ESRI Shapefile")
    PR.write(tmp_path / "EDIFC.shp", np.array([to_wkb(g) for g in edi], dtype=object), [np.array(["0302"], dtype=object)],
             ["EDIFC_USO"], geometry_type="Polygon", driver="ESRI Shapefile")
    from edifici3d.adattatori import venezia as V
    r = V.unisci(tmp_path / "UN_VOL.shp", tmp_path / "EDIFC.shp", tmp_path / "v.geojson")
    assert r == {"volumi": 3, "edifici": 1, "volumi_con_edificio": 2, "uscita": str(tmp_path / "v.geojson")}
    d = json.loads((tmp_path / "v.geojson").read_text())
    assert d["crs"]["properties"]["name"] == "EPSG:3004"
    p = [f["properties"] for f in d["features"]]
    assert p[0]["CEDIUV"] == p[1]["CEDIUV"] == "E1" and p[2]["CEDIUV"] == "V3" and p[0]["EDIFC_USO"] == "0302"


def test_ua_classi_annota_e_gronda(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin
    assert UA.altezza_classe(6) == 17.5 and UA.altezza_classe(10) == 100 and UA.altezza_classe(1) == 3
    x0, y1 = 4680000.0, 1985000.0
    a = np.full((10, 10), UA.NODATA, dtype="uint16")
    a[0:3, 0:3] = 6                     # 15–20 m
    a[0:3, 3] = 8                       # un pixel più alto: il 90° percentile lo prende se è oltre il 10 %
    with rasterio.open(tmp_path / "ua.tif", "w", driver="GTiff", width=10, height=10, count=1, dtype="uint16",
                       crs="EPSG:3035", transform=from_origin(x0, y1, 10, 10), nodata=UA.NODATA) as d:
        d.write(a, 1)
    fs = [{"type": "Feature", "properties": {"id": 1}, "geometry": mapping(box(x0, y1 - 30, x0 + 30, y1))},
          {"type": "Feature", "properties": {"id": 2, "bbox": [1, 2]}, "geometry": mapping(box(x0, y1 - 30, x0 + 40, y1))},
          {"type": "Feature", "properties": {"id": 3}, "geometry": mapping(box(x0 + 60, y1 - 90, x0 + 80, y1 - 70))}]
    (tmp_path / "s.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": fs,
                                                    "crs": {"type": "name", "properties": {"name": "EPSG:3035"}}}))
    r = UA.annota(tmp_path / "s.geojson", None, tmp_path / "ua.tif", tmp_path / "o.geojson")
    assert r["con_classe_ua"] == 2 and r["senza_pixel"] == 1 and r["stimate_dai_vicini"] == 0
    p = [f["properties"] for f in json.loads((tmp_path / "o.geojson").read_text())["features"]]
    assert p[0]["dsm_gronda"] == 17.5 and p[0]["ua_classe"] == "15–20 m" and p[0]["dsm_pixel"] == 9
    assert p[1]["dsm_gronda"] == 45.0 and "bbox" not in p[1] and p[2]["dsm_esito"] == "fuori"
    g = AD.gronda_da_campi(p[0], "residenziale")
    assert g["gronda"] == 17.5 and g["origine"] == "ua" and "Copernicus UA Building Height 2012" in g["fonte"]
    assert "9 pixel" in g["fonte"] and g["extra"]["altezza_classe_ua"] == "15–20 m"
    assert AD.gronda_da_campi(p[2], "residenziale")["origine"] == "uso"
    z = F.carica_zona("campania_napoli")
    assert "Copernicus Land Monitoring Service 2012" in z["fonti"]["edifici"]["attribuzione"]
    assert "CC BY 4.0" in z["fonti"]["edifici"]["attribuzione"] and z["fonti"]["edifici"]["licenza"] == "CC BY 4.0"
