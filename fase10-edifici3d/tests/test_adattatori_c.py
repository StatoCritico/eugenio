"""Prove dei lettori regionali del gruppo C (08/11/2026): altezze da DSM − DTM (`altezze_dsm`), adattatori di Trento
(Edifici P.A.T. 3D), Bolzano (INSPIRE), Sardegna (DBGT 10k + LiDAR 2008) e Campania (DBT/CTR 2020), sagome al volo in
ArcGIS REST e con l'uso per fonte (`sagome_regionali`). Campioni in tests/dati/ scaricati dal vivo l'08/11/2026 (licenza e
fonte nel file); nessuna rete: i servizi si provano con un trasporto httpx finto.

Dalla cartella fase10-edifici3d: `python -m pytest tests/test_adattatori_c.py`."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import httpx
import numpy as np
import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import altezze_dsm as A, fonti as F, regionali as R, sagome_regionali as S  # noqa: E402
from edifici3d.adattatori import bolzano as BZ, campania as CA  # noqa: E402

DATI = QUI / "dati"


def _raster(dest: Path, a: np.ndarray, x0: float, y1: float, passo: float = 0.5, crs: str = "EPSG:25832") -> Path:
    import rasterio
    from rasterio.transform import from_origin
    with rasterio.open(dest, "w", driver="GTiff", width=a.shape[1], height=a.shape[0], count=1, dtype="float32", crs=crs,
                       transform=from_origin(x0, y1, passo, passo), nodata=-9999.0) as d:
        d.write(a.astype("float32"), 1)
    return dest


def _scena(tmp_path: Path):
    """100 × 100 m a 0,5 m: terreno in pendenza (200 → 210 m da ovest a est), edificio 20 × 20 m alto 12 m con un
    albero alto 20 m appena fuori dal lato nord e un cortile di 4 × 4 m; un secondo «edificio» che nel DSM non c'è."""
    n = 200
    xs = np.arange(n) * 0.5 + 0.25
    dtm = np.tile(200 + xs / 10.0, (n, 1))
    dsm = dtm.copy()
    # righe: y = 100 − (r + 0,5) · 0,5; edificio x 20–40, y 20–40 → colonne 40–79, righe 120–159
    dsm[120:160, 40:80] += 12.0
    dsm[136:144, 56:64] = dtm[136:144, 56:64]          # cortile
    dsm[114:120, 50:70] += 20.0                         # chioma sopra il bordo nord (fuori dalla sagoma ridotta)
    s = _raster(tmp_path / "dsm.tif", dsm, 0, 100)
    t = _raster(tmp_path / "dtm.tif", dtm, 0, 100)
    return s, t


# ---------------------------------------------------------------------------------------------- altezze_dsm
def test_misura_gronda_pendio_cortile_e_non_presente(tmp_path):
    from shapely.geometry import box
    s, t = _scena(tmp_path)
    ds, dt = A.Raster(s), A.Raster(t)
    m = A.misura(box(20, 20, 40, 40), ds, dt)
    assert m["esito"] == "ok" and abs(m["gronda"] - 12.0) < 0.01           # pendio: differenza pixel per pixel
    assert m["alti"] < 1.0                                                  # il cortile resta fuori dai pixel alti
    assert 201.9 < m["quota"] < 203.1 and m["quota_min"] < m["quota"]
    assert A.misura(box(60, 60, 80, 80), ds, dt)["esito"] == "non_presente"
    assert A.misura(box(200, 200, 210, 210), ds, dt) is None                # fuori dal rilievo
    p = A.misura(box(20, 20, 21.6, 21.6), ds, dt)                           # sagoma piccola
    assert p["esito"] in ("pochi_pixel", "ok") and abs(p["gronda"] - 12.0) < 0.01


def test_annota_stima_vicini_e_confronto(tmp_path):
    from shapely.geometry import box
    s, t = _scena(tmp_path)
    coppie = A.accoppia([s], [t])
    righe = [({"id": "a", "H": 11.5}, box(20, 20, 40, 40)), ({"id": "b", "H": 0}, box(60, 60, 80, 80)),
             ({"id": "c", "H": 0}, box(45, 20, 55, 30)), ({"id": "d", "H": 9.0}, box(5, 5, 12, 12)),
             ({"id": "e", "H": 10.0}, box(5, 60, 12, 67))]
    out, res = A.annota(righe, lambda sg: A.misura_coppie(sg, coppie, "EPSG:25832"), "EPSG:25832",
                        campo_altezza="H", solo_senza=True, etichetta="prova")
    assert res["misurate"] == 2 and res["esiti"]["altezza dal DB"] == 3
    pb = out[1][0]
    assert pb["dsm_esito"] == "non_presente" and pb["stima_gronda"] == 10.0  # mediana di 11,5 / 9 / 10 entro 100 m
    assert "dsm_gronda" not in out[0][0]                                     # con l'altezza del DB non si misura
    r = A.confronta([("a", box(20, 20, 40, 40), 11.5), ("x", box(60, 60, 80, 80), 9.0)], coppie, "EPSG:25832")
    assert r["dsm_meno_db"]["n"] == 1 and r["dsm_meno_db"]["mediana"] == 0.5 and r["dsm_meno_db"]["entro_2m"] == 1.0
    assert r["esiti"] == {"ok": 1, "non_presente": 1}
    # file GeoJSON: proprietà a lista (bbox dei WFS) tolte, rilette dal lettore comune
    f = A.scrivi_geojson([({**p, "bbox": [1, 2]}, g) for p, g in out], tmp_path / "a.geojson", "EPSG:25832")
    righe2, crs = R.leggi_file(f)
    assert len(righe2) == 5 and "bbox" not in righe2[0][0] and "25832" in crs


def test_torre_dell_elefante_dal_lidar_2008():
    """Ritaglio reale del LiDAR 2008 di Cagliari: la Torre dell'Elefante (alta circa 31 m) misura 32,8 m."""
    from shapely.geometry import Point
    from pyproj import Transformer
    coppie = A.accoppia([DATI / "sardegna_lidar2008_dsm_campione.tif"], [DATI / "sardegna_lidar2008_dtm_campione.tif"])
    x, y = Transformer.from_crs("EPSG:4326", "EPSG:7791", always_xy=True).transform(9.11490, 39.21796)
    m = A.misura_coppie([("torre", Point(x, y).buffer(6))], coppie, "EPSG:7791")["torre"]
    assert m["esito"] == "ok" and 31.5 < m["gronda"] < 34.5


def test_mosaico_con_bordo_a_zero(tmp_path):
    a = tmp_path / "a.asc"
    b = tmp_path / "b.asc"
    a.write_text("ncols 4\nnrows 2\nxllcorner 0\nyllcorner 0\ncellsize 5\nnodata_value -9999\n"
                 "0 10 11 0\n0 10 11 0\n")
    b.write_text("ncols 4\nnrows 2\nxllcorner 15\nyllcorner 0\ncellsize 5\nnodata_value -9999\n"
                 "12 12 13 0\n12 12 13 0\n")
    import rasterio
    out = A.mosaico([str(a), str(b)], tmp_path / "m.tif", "EPSG:25833", zero_vuoto=True)
    with rasterio.open(out) as d:
        v = d.read(1)
    assert v.shape == (2, 7) and list(v[0]) == [-9999, 10, 11, 12, 12, 13, -9999]  # lo 0 di a non copre il 12 di b


def test_tessere_da_fonte_indice_e_griglia():
    def risposta(req):
        assert "inqlid2014_new" in str(req.url) and "EPSG%3A25832" in str(req.url)
        return httpx.Response(200, json={"features": [
            {"properties": {"n_tavola": "5h664551020"}, "geometry": {"type": "Polygon", "coordinates": [
                [[664500, 5102000], [665000, 5102000], [665000, 5102500], [664500, 5102500], [664500, 5102000]]]}}]})
    f, _ = A.fonte_lidar("trento")
    t = A.tessere_da_fonte(f, (664600, 5102100, 664700, 5102200), "EPSG:25832",
                           httpx.Client(transport=httpx.MockTransport(risposta)))
    assert t[0]["nome"] == "5h664551020" and t[0]["dtm"].endswith("/2014_lidar_dtm_asc/5h664551020_DTM.asc")
    assert t[0]["dsm"].endswith("5h664551020_DSMFirst.asc")
    g, _ = A.fonte_lidar("bolzano")
    t = A.tessere_da_fonte(g, (677100, 5151800, 677900, 5152200), "EPSG:25832")
    assert len(t) == 2 and "subset=E(677000,678000)" in t[0]["dsm"] and "DigitalTerrainModel-0.5m" in t[0]["dtm"]


# ---------------------------------------------------------------------------------------------- adattatori
def test_trento_pat3d_campione():
    righe, crs = R.leggi_file(DATI / "trento_pat3d_campione.geojson")
    corpi, res = R.corpi(righe, "trento_pat3d", "EPSG:25832", crs)
    assert res["corpi"] == len(righe) and all(c.licenza == "CC BY 4.0" for c in corpi)
    db = [c for c in corpi if "MED_ALT (altezza media" in c.fonte_altezza]
    dsm = [c for c in corpi if "DSM First − DTM" in c.fonte_altezza]
    stima = [c for c in corpi if "stima" in c.fonte_altezza]
    assert db and dsm and stima
    c = next(c for c in db if c.extra.get("mas_alt") and c.extra["mas_alt"] > 50)      # corpo principale del S. Chiara
    assert abs(c.gronda - 26.26) < 0.01 and c.quota_terreno > 180
    assert all(c.fonte_altezza.startswith("MED_ALT = 0") for c in dsm + stima)
    # cavedi esclusi; baracche senza misura a 3 m
    from shapely.geometry import box
    assert R.ADATTATORI["trento_pat3d"].corpo({"TIPO": "Cavedio", "MED_ALT": 5}, box(0, 0, 5, 5), None, 200) is None
    b = R.ADATTATORI["trento_pat3d"].corpo({"OBJECTID_1": 1, "TIPO": "Baracca", "MED_ALT": 0, "quota_DTM": 300},
                                           box(0, 0, 5, 5), None, None)
    assert b.gronda == 3.0 and b.quota_terreno == 300 and "manufatto piccolo" in b.fonte_altezza


def test_bolzano_unisci_parti_e_adattatore():
    e = json.loads((DATI / "bolzano_inspire_edifici_campione.geojson").read_text(encoding="utf-8"))
    p = json.loads((DATI / "bolzano_inspire_parti_campione.geojson").read_text(encoding="utf-8"))
    d = BZ.unisci_parti(e, p)
    assert len(d["features"]) == 11 and all(f["properties"].get("CURRENT_USE") for f in d["features"])
    assert d["features"][-1]["properties"]["ID"].startswith("e")                  # edificio senza parti: intero
    from shapely.geometry import shape
    from edifici3d.regionali import _poligono
    f0 = d["features"][0]
    g, _ = _poligono(shape(f0["geometry"]))
    ad = R.ADATTATORI["bolzano_inspire"]
    con = ad.corpo({**f0["properties"], "dsm_gronda": 17.4, "dsm_esito": "ok", "dsm_pixel": 300, "dsm_quota": 262.0,
                    "dsm_fonte": "DSM"}, g, None, None)
    assert con.gronda == 17.4 and con.quota_terreno == 262.0 and con.licenza == "CC0 1.0"
    assert con.edificio == f"bz{f0['properties']['BUILDING_ID']}"
    nuovo = ad.corpo({**f0["properties"], "dsm_esito": "non_presente", "dsm_pixel": 300, "dsm_quota": 262.0,
                      "stima_gronda": 14.0}, g, None, None)
    assert nuovo.gronda == 14.0 and "non presente nel rilievo" in nuovo.fonte_altezza and nuovo.extra["stima_altezza"] == "vicini"
    assert ad.corpo(f0["properties"], g, None, None) is None                      # né DTM né quota: scartato


def test_sardegna_dbgt_lidar_campione(tmp_path):
    righe, crs = R.leggi_file(DATI / "sardegna_dbgt_campione.geojson")
    coppie = A.accoppia([DATI / "sardegna_lidar2008_dsm_campione.tif"], [DATI / "sardegna_lidar2008_dtm_campione.tif"])
    out, res = A.annota(righe, lambda s: A.misura_coppie(s, coppie, "EPSG:7791"), "EPSG:7791", etichetta="LiDAR 2008")
    corpi, r = R.corpi(out, "sardegna_dbgt_lidar", "EPSG:7791", "EPSG:7791")
    assert r["corpi"] == 3 and all(2 < c.gronda < 30 for c in corpi)
    assert all("LiDAR 2008: mediana dei pixel" in c.fonte_altezza for c in corpi)
    assert {c.uso for c in corpi} <= {"residenziale", None} and all(c.extra["regione"] == "Sardegna" for c in corpi)
    from shapely.geometry import box
    assert R.ADATTATORI["sardegna_dbgt_lidar"].corpo({"stato": "diruto"}, box(0, 0, 9, 9), None, 5) is None


def test_campania_ctr_e_dbt_zip(tmp_path):
    righe, crs = R.leggi_file(DATI / "campania_ctr2020_campione.geojson")
    senza, r0 = R.corpi(righe, "campania_dbt", "EPSG:25833", "EPSG:4326")
    assert senza == []                                                           # CTR dal servizio: niente z, serve il DTM
    dtm = _raster(tmp_path / "dtm.tif", np.full((300, 300), 120.0), 433800, 4525000, 5.0, "EPSG:25833")
    corpi, r = R.corpi(righe, "campania_dbt", "EPSG:25833", "EPSG:4326", dtm)
    assert r["corpi"] == len(righe)                                              # il campione ha solo edifici
    from shapely.geometry import box
    for t in ("81220000", "31630000", "31670000", "31110100"):                    # area antropizzata, tettoia, cavedio, interrato
        assert CA.CAMPANIA.corpo({"tipo": t}, box(0, 0, 20, 20), None, 10.0) is None
    assert all(CA.ctr_edificio(c.extra["codice_ctr"]) for c in corpi)
    assert any(c.uso == "ospedale" for c in corpi)                               # Cardarelli, «3111000O»
    assert all("stima" in c.fonte_altezza and c.quota_terreno == 120.0 for c in corpi)
    # DBT sintetico con gli stessi file e campi dello zip di Napoli (CLASSREF → CLASSID, testi UTF-8 letti come Latin-1)
    import pyogrio.raw as W
    from shapely import to_wkb
    from shapely.geometry import Polygon
    d = tmp_path / "DBT"
    d.mkdir()
    g = [Polygon([(436000, 4521000, 10), (436020, 4521000, 10), (436020, 4521020, 10), (436000, 4521020, 10)]),
         Polygon([(436100, 4521000, 12), (436110, 4521000, 12), (436110, 4521010, 12), (436100, 4521010, 12)]),
         Polygon([(436200, 4521000, 5), (436210, 4521000, 5), (436210, 4521010, 5), (436200, 4521010, 5)])]
    W.write(str(d / "EDIFC_CR_EDF_IS.shp"), np.array([to_wkb(x) for x in g], dtype=object),
            [np.array(["1", "2", "3"])], ["CLASSREF"], driver="ESRI Shapefile", geometry_type="Polygon Z",
            crs="EPSG:25833")
    W.write(str(d / "EDIFC.dbf"), None, [np.array(["1", "2", "3"]), np.array(["01", "01", "01"]),
            np.array(["03", "03", "02"]), np.array(["01", "08", "01"])],
            ["CLASSID", "EDIFC_SOT", "EDIFC_STAT", "EDIFC_TY"], driver="ESRI Shapefile")
    W.write(str(d / "EDIFC_EDIFC_USO.dbf"), None, [np.array(["1", "2"]), np.array(["030102", "0801"])],
            ["CLASSREF", "EDIFC_USO"], driver="ESRI Shapefile")
    W.write(str(d / "EDIFC_EDIFC_NOME.dbf"), None, [np.array(["1"]),
            np.array(["Università Federico II"])], ["CLASSREF", "NOME"], driver="ESRI Shapefile")
    for f in d.glob("*.cpg"):                     # come nello zip: DBF in UTF-8 senza .cpg, letto come Latin-1
        f.unlink()
    z = tmp_path / "DBT_5K.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for f in d.iterdir():
            zf.write(f, f"DBT/{f.name}")
    gj = CA.leggi_dbt_zip(z)
    assert gj["legame"]["sagome"] == "CLASSREF" and gj["legame"]["sagome_legate"] == 3
    f = tmp_path / "n.geojson"
    gj.pop("legame")
    f.write_text(json.dumps(gj), encoding="utf-8")
    righe, crs = R.leggi_file(f)
    corpi, r = R.corpi(righe, "campania_dbt", "EPSG:25833", crs)
    assert r["corpi"] == 2                                                       # il diruto (stato 02) è scartato
    c1 = next(c for c in corpi if c.id == "cam_1")
    assert c1.uso == "ospedale" and c1.quota_terreno == 10 and c1.extra["nome"] == "Università Federico II"
    assert 6 <= c1.gronda <= 9 and "stima: uso" in c1.fonte_altezza
    assert next(c for c in corpi if c.id == "cam_2").uso == "capannone"


# ---------------------------------------------------------------------------------------------- sagome al volo
def test_url_veneto_resta_est_nord_e_arcgis():
    fs = {f["id"]: f for f in S.carica()}
    u = S.url_wfs(fs["veneto"], 12.3390, 45.4340, 300)
    x = int(u.split("bbox=")[1].split(",")[0])
    assert 3_000_000 < x < 3_100_000 and "EPSG:6876&" in u and "urn:" not in u   # forma breve, prima l'Est
    c = S.url_wfs(fs["campania"], 14.2268, 40.8640, 300)
    assert c.startswith(fs["campania"]["servizio"] + "/query?") and "inSR=7792" in c and "f=geojson" in c
    assert "tipo+LIKE" in c and "esriGeometryEnvelope" in c
    s = S.url_wfs(fs["sardegna"], 9.1075, 39.2510, 300)
    assert "EPSG:7791" in s and "edificio_ingombro_suolo" in s
    assert S.fonte_nel_punto(9.1075, 39.2510)["id"] == "sardegna" and S.fonte_nel_punto(14.25, 40.85)["id"] == "campania"
    assert "uso" in S.campi_tenuti(fs["sardegna"]) and "edi_uso" in S.campi_tenuti(fs["veneto"])


def test_unisci_arcgis_wgs84_e_uso_per_fonte():
    fs = {f["id"]: f for f in S.carica()}
    w = json.loads((DATI / "campania_ctr2020_campione.geojson").read_text(encoding="utf-8"))
    w["features"] = [f for f in w["features"] if CA.ctr_edificio(f["properties"]["tipo"])]
    r = S.unisci(w, fs["campania"], {}, 14.2268, 40.8640)
    assert r["sagome"]["corpi"] > 0 and all(f["properties"]["origine_altezza"] == "fissa" for f in r["features"])
    assert all(5 < f["properties"]["area"] < 50000 for f in r["features"])        # aree in m² (dai gradi)
    assert any(f["properties"]["uso"] == "ospedale" for f in r["features"])
    s = json.loads((DATI / "sardegna_wfs_campione.geojson").read_text(encoding="utf-8"))
    r = S.unisci(s, fs["sardegna"], {}, 9.1075, 39.2510)
    usi = {f["properties"]["codice_uso"]: f["properties"]["uso"] for f in r["features"]}
    assert usi.get("residenziale") == "residenziale" and r["sagome"]["licenza"] == "CC BY 4.0"
    if "sede di ospedale" in usi:
        assert usi["sede di ospedale"] == "ospedale"


def test_fonti_toml_del_gruppo_c():
    for z, cod, ad in (("trento", "tn", "trento_pat3d"), ("bolzano", "bz", "bolzano_inspire"),
                       ("sardegna", "sar", "sardegna_dbgt_lidar"), ("campania", "cam", "campania_dbt")):
        d = F.carica_zona(z)
        assert d["zona"]["codice"] == cod and d["fonti"]["edifici"]["adattatore"] == ad
        assert F.cartella(Path("/a"), d, d["fonti"]["edifici"]["licenza"], "").parts[-2:] == ("cc-by", cod)
