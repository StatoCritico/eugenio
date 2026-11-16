"""Adattatore umbria_osm_pst (16/11/2026): sagome OSM con le altezze del LiDAR PST, archivio ODbL di Perugia."""
from pathlib import Path

from shapely.geometry import box

from edifici3d import fonti as F, regionali as R
from edifici3d.adattatori import umbria as U
from edifici3d.__main__ import TESTI_LICENZA

OSM = """<?xml version="1.0"?><osm version="0.6">
<node id="1" lat="43.1100" lon="12.3880"/><node id="2" lat="43.1100" lon="12.3884"/>
<node id="3" lat="43.1103" lon="12.3884"/><node id="4" lat="43.1103" lon="12.3880"/>
<way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
<tag k="building" v="apartments"/><tag k="building:levels" v="5"/><tag k="name" v="Prova"/></way>
</osm>"""


def test_registrato_e_zona():
    assert "umbria_osm_pst" in R.ADATTATORI
    z = F.carica_zona("umbria_perugia")
    assert z["fonti"]["edifici"]["adattatore"] == "umbria_osm_pst"
    assert z["fonti"]["edifici"]["licenza"] == "ODbL 1.0" and "ODbL 1.0" in TESTI_LICENZA
    assert "OpenStreetMap" in z["fonti"]["edifici"]["attribuzione"] and "PST" in z["fonti"]["edifici"]["attribuzione"]
    # le sagome OSM vanno sempre in odbl/, mai insieme agli archivi CC BY
    assert F.cartella(Path("/a"), z, "ODbL 1.0", "").parts[-2:] == ("odbl", "umb")


def test_ordine_delle_altezze():
    g = box(0, 0, 20, 15)
    base = {"osm_id": "w1", "building": "apartments", "building:levels": "5"}
    # 1. DSM − DTM del PST
    c = U.OSM_PST.corpo({**base, "dsm_gronda": 14.2, "dsm_esito": "ok", "dsm_pixel": 200, "dsm_colmo": 16.0,
                         "dsm_fonte": "DSM − DTM (PST 2014"}, g, None, 300.0)
    assert c.gronda == 14.2 and c.extra["origine_altezza"] == "dsm" and c.extra["colmo_dsm"] == 16.0
    assert c.licenza == "ODbL 1.0" and c.id == "pgw1" and c.uso == "residenziale" and c.quota_terreno == 300.0
    # 2. non presente nel rilievo del 2014: tag OSM
    c = U.OSM_PST.corpo({**base, "dsm_esito": "non_presente", "dsm_pixel": 200}, g, None, 300.0)
    assert c.gronda == 15.0 and c.extra["origine_altezza"] == "osm" and "non presente" in c.fonte_altezza
    # 3. niente DSM né tag: mediana dei vicini, dichiarata
    c = U.OSM_PST.corpo({"osm_id": "w2", "building": "yes", "dsm_esito": "fuori", "stima_gronda": 9.5}, g, None, 300.0)
    assert c.gronda == 9.5 and c.qualita == "altezza stimata"
    # quota mancante: nessun corpo
    assert U.OSM_PST.corpo({**base, "dsm_esito": "fuori"}, g, None, None) is None


def test_osm_geojson(tmp_path):
    f = tmp_path / "a.osm"
    f.write_text(OSM, encoding="utf-8")
    r = U.osm_geojson(f, "EPSG:7792", tmp_path / "a.geojson")
    assert r["sagome"] == 1
    righe, crs = R.leggi_file(tmp_path / "a.geojson")
    assert righe[0][0]["osm_id"] == "w10" and righe[0][0]["name"] == "Prova"
    assert 1000 < righe[0][1].area < 1300                                   # ~32 × 33 m in metri (EPSG:7792)
