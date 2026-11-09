"""Prove degli adattatori del gruppo B (08/11/2026): Toscana (unità volumetriche multiscala), Puglia (CTR 1:5.000 con
punti di gronda e piede), Marche (DBGT 2019 edificio + punto quotato), Sicilia (unità volumetriche del Comune di Palermo
e CTR ATA 2012-13), FVG (CTRN edizione 2). Campioni piccoli scaricati dal vivo l'08/11/2026 in tests/dati/ (fonte e
licenza nel campo «name» dei GeoJSON o nel LEGGIMI dello zip). Nessuna rete."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))

from edifici3d import b_regioni as B, fonti as F, regionali as R  # noqa: E402
from edifici3d.adattatori import friuli_venezia_giulia as AF, marche as AM, puglia as AP, sicilia as AS, toscana as AT  # noqa: E402

DATI = QUI / "dati"


def _dtm(dest: Path, riquadro, valore, crs: str, passo: float = 1.0) -> Path:
    import rasterio
    from rasterio.transform import from_origin
    x0, y0, x1, y1 = riquadro
    w, h = int((x1 - x0) / passo), int((y1 - y0) / passo)
    with rasterio.open(dest, "w", driver="GTiff", width=w, height=h, count=1, dtype="float32", crs=crs,
                       transform=from_origin(x0, y1, passo, passo), nodata=-9999.0) as d:
        d.write(np.full((h, w), valore, dtype="float32"), 1)
    return dest


def test_registrati_e_zone():
    for k in ("toscana_uv", "puglia_ctr", "marche_dbgt", "palermo_uv", "sicilia_ctr", "fvg_ctrn_ed2"):
        assert k in R.ADATTATORI
    for zona, codice, ad in (("toscana", "tos", "toscana_uv"), ("puglia", "pug", "puglia_ctr"), ("marche", "mar", "marche_dbgt"),
                             ("sicilia", "sic", "palermo_uv"), ("sicilia_ctr", "sic", "sicilia_ctr")):
        z = F.carica_zona(zona)
        assert z["zona"]["codice"] == codice and z["fonti"]["edifici"]["adattatore"] == ad
    # IODL 2.0 in un archivio separato
    z = F.carica_zona("puglia")
    assert F.cartella(Path("/a"), z, "IODL 2.0", "") == Path("/a/iodl/pug")


# ---------------------------------------------------------------------------------------------------- Toscana
def test_toscana_uv_campione(tmp_path):
    righe, crs = R.leggi_file(DATI / "toscana_uv_campione.geojson")
    assert "3003" in crs and len(righe) == 31
    ctl = R.controlla(righe, "toscana_uv")
    assert not ctl["mancanti"]
    assert "su 31" in AT.coerenza(righe)
    corpi, res = R.corpi(righe, "toscana_uv", "EPSG:7791", crs)
    assert res["scarti"] == {"altezza assente o non valida, o elemento escluso": 2}           # sotterraneo e altro
    duomo = max(corpi, key=lambda c: c.gronda)
    assert 110 < duomo.gronda < 115 and duomo.licenza == "CC BY 4.0"                         # cupola: uv_av 112,57 m
    x0, y0, x1, y1 = duomo.sagoma.bounds                                                      # 3003 → 7791 a Firenze
    assert 681550 < x0 < 681700 and 4849050 < y0 < 4849200
    osp = next(c for c in corpi if (c.extra or {}).get("uso_ctr") == "Sede Di Ospedale")
    assert osp.uso == "ospedale"
    loggia = next(c for c in corpi if c.extra.get("porzione") == "Soffitto Di Loggia")
    assert loggia.extra.get("base_sopraelevata") is True
    # col DTM: terreno dal DTM, la loggia va dal terreno alla quota di estrusione
    allo = R.corpi(righe, "toscana_uv", "EPSG:7791", crs)[0]
    bb = [min(c.sagoma.bounds[0] for c in allo) - 50, min(c.sagoma.bounds[1] for c in allo) - 50,
          max(c.sagoma.bounds[2] for c in allo) + 50, max(c.sagoma.bounds[3] for c in allo) + 50]
    dtm = _dtm(tmp_path / "dtm.tif", bb, 40.0, "EPSG:7791", 2.0)
    con, _ = R.corpi(righe, "toscana_uv", "EPSG:7791", crs, dtm)
    lg = next(c for c in con if c.id == loggia.id)
    assert lg.quota_terreno == 40.0 and abs(lg.gronda - (lg.extra["quota_estrusione"] - 40.0)) < 0.01


# ---------------------------------------------------------------------------------------------------- Puglia
def test_puglia_ctr_divide_gli_isolati(tmp_path):
    out = tmp_path / "bari.geojson"
    e = B.puglia_ctr([DATI / "puglia_ctr_438074_campione.zip"], out)
    assert e["edifici"] == 3 and e["corpi"] == 10 and e["edifici_divisi"] == 2
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["crs"]["properties"]["name"] == "EPSG:32633"
    righe, crs = R.leggi_file(out)
    corpi, res = R.corpi(righe, "puglia_ctr", "EPSG:7792", crs)
    assert res["corpi"] == 10 and res["licenza"] == "IODL 2.0" and res["altezza"]["max"] == 35.2   # campanile
    assert 5 < res["altezza"]["mediana"] < 30
    # i pezzi di un edificio diviso coprono l'edificio (stessa area)
    per_ed = {}
    for f in d["features"]:
        per_ed.setdefault(f["properties"]["edificio"], []).append(f)
    diviso = next(v for v in per_ed.values() if len(v) > 1)
    assert all(f["properties"]["pezzi"] == len(diviso) for f in diviso)
    c = corpi[0]
    assert c.licenza == "IODL 2.0" and "quota al piede" in c.fonte_altezza and 656000 < c.sagoma.bounds[0] < 658000
    assert "su" in AP.coerenza(righe)


def test_puglia_adattatore_regole():
    g = box(0, 0, 10, 10)
    c = AP.PUGLIA.corpo({"id": "a", "edificio": "e", "quota_gronda": 20.0, "quota_piede": 5.0,
                         "fonte_gronda": "punti di gronda dell'edificio (isolato)"}, g, None, 4.5)
    assert c.gronda == 15.0 and c.quota_terreno == 4.5 and "isolato" in c.qualita
    assert AP.PUGLIA.corpo({"id": "a", "quota_gronda": 5.5, "quota_piede": 5.0}, g, None, None) is None   # < 1,5 m
    c = AP.PUGLIA.corpo({"id": "a", "quota_gronda": 12.0}, g, None, 2.0)                               # piede dal DTM
    assert c.gronda == 10.0 and "DTM" in c.fonte_altezza


def test_dividi_con_linea():
    from shapely.geometry import LineString
    p = box(0, 0, 20, 10)
    pezzi = B._dividi(p, [B._allunga(LineString([(10, 0.05), (10, 9.95)]))])
    assert len(pezzi) == 2 and abs(sum(x.area for x in pezzi) - 200) < 0.01


def test_asc_virgola():
    testo = b"ncols 2\nnrows 2\nxllcorner 100,5\nyllcorner 200,0\ncellsize 8\nNODATA_value -9999\n1,5 2\n-9999 4,25\n"
    a, (x, y, cs) = B._asc(testo, virgola=True)
    assert x == 100.5 and cs == 8 and a[0, 0] == 1.5 and np.isnan(a[1, 0]) and a[1, 1] == 4.25


# ---------------------------------------------------------------------------------------------------- Marche
def test_marche_dbgt_join_e_adattatore(tmp_path):
    out = tmp_path / "an.geojson"
    e = B.marche_dbgt(DATI / "marche_edificio_campione.geojson", DATI / "marche_punto_quotato_campione.geojson", out)
    assert e["edifici"] == 2 and e["con_piede"] == 1          # il secondo è tagliato dal riquadro
    righe, crs = R.leggi_file(out)
    assert "su" in AM.coerenza(righe)
    corpi, res = R.corpi(righe, "marche_dbgt", "EPSG:7792", crs)
    mole = max(corpi, key=lambda c: c.area)                 # Mole Vanvitelliana, 13,4 m sul punto al piede
    assert 12 < mole.gronda < 15 and mole.area > 5000 and mole.licenza == "CC BY 4.0"
    assert "punto al piede" in mole.fonte_altezza
    g = box(0, 0, 10, 10)
    assert AM.MARCHE.corpo({"gid": 1, "edifc_qm": 20, "quota_piede": 10, "stat_name": "diruto, rudere"}, g, None, None) is None
    assert AM.MARCHE.corpo({"gid": 1, "edifc_qm": 20, "quota_piede": 10, "por_name": "sotterraneo"}, g, None, None) is None
    c = AM.MARCHE.corpo({"gid": 1.0, "edifc_qm": 20, "ty_name": "capannone"}, g, None, 12.0)      # piede dal DTM
    assert c.gronda == 8.0 and c.uso == "capannone" and c.id == "1"


# ---------------------------------------------------------------------------------------------------- Sicilia
def test_palermo_uv_campione(tmp_path):
    righe, crs = R.leggi_file(DATI / "palermo_uv_campione.geojson")
    assert "7792" in crs
    assert AS.coerenza_palermo_uv(righe).startswith("QUOTA_GRON − QUOTA_PIED = ALTEZZA in 10 su 10")
    corpi, res = R.corpi(righe, "palermo_uv", "EPSG:7792", crs)
    torre = max(corpi, key=lambda c: c.gronda)
    assert torre.gronda == 71.1 and abs(torre.quota_terreno - 20.8) < 0.01           # torre di Piazzale Ungheria
    assert len({c.id for c in corpi}) == len(corpi)


def test_palermo_nomi_troncati_e_doppioni(tmp_path):
    g = box(0, 0, 10, 10)
    c = AS.PALERMO.corpo({"ID": 5.0, "ID_UN_VOL": 7.0, "QUOTA_GRONDA": 30.0, "QUOTA_PIEDE": 20.0, "ALTEZZA": 0}, g, None, None)
    assert c.gronda == 10.0 and c.id == "7" and c.quota_terreno == 20.0
    # doppioni: stessa sagoma e stesso ID, si tiene la più alta
    from shapely.geometry import mapping
    fs = [{"type": "Feature", "properties": {"ID": 1, "ID_UN_VOL": 1, "ALTEZZA": h, "QUOTA_GRON": 10 + h, "QUOTA_PIED": 10},
           "geometry": mapping(g)} for h in (4.4, 7.4, 4.4)]
    fs.append({"type": "Feature", "properties": {"ID": 2, "ID_UN_VOL": 2, "ALTEZZA": 3.0, "QUOTA_GRON": 13, "QUOTA_PIED": 10},
               "geometry": mapping(box(20, 0, 30, 10))})
    src = tmp_path / "pa.geojson"
    B.scrivi_geojson(fs, src, "EPSG:7792")
    e = B.palermo_uv(src, tmp_path / "out.geojson")
    assert e["scritti"] == 2 and e["doppioni_tolti"] == 2
    d = json.loads((tmp_path / "out.geojson").read_text(encoding="utf-8"))
    assert d["features"][0]["properties"]["ALTEZZA"] == 7.4 and d["features"][0]["properties"]["doppioni"] == 3


def test_sicilia_ctr_serve_il_dtm(tmp_path):
    righe, crs = R.leggi_file(DATI / "sicilia_ctr_campione.geojson")
    senza, res = R.corpi(righe, "sicilia_ctr", "EPSG:7792", crs)
    assert senza == [] and res["scarti"] == {"manca la quota del terreno (DTM)": 8}
    dtm = _dtm(tmp_path / "dtm.tif", (355700, 4218200, 356400, 4218900), 30.0, "EPSG:7792", 2.0)
    con, res = R.corpi(righe, "sicilia_ctr", "EPSG:7792", crs, dtm)
    assert res["corpi"] == 8
    c = con[0]
    assert abs(c.gronda - (c.extra["quota_gronda"] - 30.0)) < 0.01 and c.extra["anno_rilievo"] in (2003, 2007, 2012)


# ---------------------------------------------------------------------------------------------------- FVG ed. 2
def test_fvg_ctrn_ed2_campione():
    righe, crs = R.leggi_file(DATI / "fvg_ctrn_ed2_campione.geojson")
    assert "6708" in crs
    assert AF.coerenza(righe).endswith("su 23")
    corpi, res = R.corpi(righe, "fvg_ctrn_ed2", "EPSG:6708", crs)
    assert len({c.id for c in corpi}) == len(corpi) == res["corpi"]                     # con fvg_ctrn: tutti «None»
    torre = max(corpi, key=lambda c: c.gronda)
    assert abs(torre.gronda - 54.82) < 0.01 and torre.extra["volo"].startswith("2003-05")  # torri di Cattinara
    vecchio, _ = R.corpi(righe, "fvg_ctrn", "EPSG:6708", crs)
    assert len({c.id for c in vecchio}) == 1
    g = box(0, 0, 10, 10)
    assert AF.FVG_ED2.corpo({"ID1": 1, "ALTEZZA": 3.0, "NOME": "TETTOIA, PENSILINA"}, g, None, None) is None


def test_confine_comune():
    g = B.confine_comune("048017", "EPSG:7791", margine=0)
    assert 95e6 < g.area < 106e6                                                      # Firenze, 102 km²
    assert g.contains(box(681600, 4849100, 681700, 4849200))                          # Duomo


def _foglio_dbgt(dest: Path, righe):
    """Shapefile UN_VOL sintetico (PolygonZ, campi del DBGT Lazio) con righe (id, istat, altezza, poligono)."""
    import pyogrio.raw as PR
    import shapely
    from shapely.geometry import Polygon
    dest.parent.mkdir(parents=True, exist_ok=True)
    geoms = [shapely.to_wkb(Polygon([(x, y, 20.0) for x, y in p.exterior.coords])) for _i, _c, _h, p in righe]
    campi = [np.array([r[0] for r in righe], dtype=object), np.array([r[1] for r in righe], dtype=object),
             np.array([r[2] for r in righe], dtype=float)]
    PR.write(str(dest), np.array(geoms, dtype=object), campi, fields=["CLASSID", "COD_ISTAT", "UN_VOL_AV"],
             crs="EPSG:25833", driver="ESRI Shapefile", geometry_type="Polygon Z")
    return dest


def test_dbgt_fogli_comune_doppioni_e_id(tmp_path):
    """Unione dei fogli DBGT (09/11/2026): solo il comune, codice vuoto deciso dal confine, doppioni ai bordi tolti,
    id ripetuto con geometria diversa rinominato, z conservata."""
    import pyogrio.raw as PR
    import shapely
    a = _foglio_dbgt(tmp_path / "rm374" / "UN_VOL.shp", [
        ("RM374_1", "058091", 10.0, box(0, 0, 10, 10)),
        ("RM374_2", "058120", 8.0, box(20, 0, 30, 10)),          # altro comune (Fiumicino)
        ("RM374_3", "058000", 6.0, box(40, 0, 50, 10)),          # codice di comodo, nel confine
        ("RM374_4", "058000", 6.0, box(500, 0, 510, 10)),        # codice di comodo, fuori
        ("COMUNE_9", "058091", 5.0, box(60, 0, 70, 10))])
    b = _foglio_dbgt(tmp_path / "rm387" / "UN_VOL.shp", [
        ("RM387_1", "058091", 10.0, box(0, 0, 10, 10)),          # doppione del bordo (stessa geometria e altezza)
        ("COMUNE_9", "058091", 7.0, box(80, 0, 90, 10)),         # id ripetuto, geometria diversa
        ("RM387_2", "058091", 9.0, box(100, 0, 110, 10))])
    out = B.dbgt_fogli([a, b], tmp_path / "roma.gpkg", "058091", confine=box(-5, -5, 200, 20))
    assert out["tenuti"] == 5
    assert out["fogli"]["374"] == {"letti": 5, "codice del comune": 2, "altro comune": 1, "codice vuoto, nel confine": 1,
                                   "codice vuoto, fuori dal confine": 1, "tenuti": 3}
    assert out["fogli"]["387"]["doppioni tolti"] == 1 and out["id ripetuti (suffisso del foglio)"] == 1
    meta, _f, geom, campi = PR.read(str(tmp_path / "roma.gpkg"))
    ids = list(campi[list(meta["fields"]).index("CLASSID")])
    assert ids == ["RM374_1", "RM374_3", "COMUNE_9", "COMUNE_9_387", "RM387_2"]
    assert shapely.has_z(shapely.from_wkb(geom[0]))
    righe, _crs = R.leggi_file(tmp_path / "roma.gpkg")
    assert len(righe) == 5
