"""Archivio di prova da OpenStreetMap per un quartiere (edifici3d/osm_campione.py, 05/11/2026): XML sintetico, nessuna rete.
La prova dal vivo (centro di Rimini, una chiamata all'API OSM e un GetCoverage del DTM 5 m) è nel README, sezione
«Cosa manca per passare dalla demo al servizio vero»."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edifici3d import osm_campione as OC   # noqa: E402

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
 <node id="1" lat="44.0600" lon="12.5660"/><node id="2" lat="44.0600" lon="12.5664"/>
 <node id="3" lat="44.0603" lon="12.5664"/><node id="4" lat="44.0603" lon="12.5660"/>
 <node id="5" lat="44.0606" lon="12.5670"/><node id="6" lat="44.0606" lon="12.5675"/>
 <node id="7" lat="44.0609" lon="12.5675"/><node id="8" lat="44.0609" lon="12.5670"/>
 <node id="9" lat="44.0610" lon="12.5680"/><node id="10" lat="44.0611" lon="12.5681"/>
 <way id="100"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="building" v="yes"/><tag k="building:levels" v="4"/></way>
 <way id="101"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/></way>
 <way id="102"><nd ref="9"/><nd ref="10"/><tag k="building" v="yes"/></way>
 <relation id="200"><member type="way" ref="101" role="outer"/><tag k="type" v="multipolygon"/><tag k="building" v="church"/></relation>
</osm>"""


def test_xml_corpi_e_stima():
    el = OC.edifici_da_xml(XML)
    assert sorted(t["osm_id"] for t, _ in el) == ["r200_0", "w100"]           # la way aperta 102 si scarta
    corpi = {c.id: c for c in OC.corpi_con_stima(el, 9.0)}
    assert corpi["w100"].gronda == 12.0 and "levels" in corpi["w100"].fonte_altezza
    assert corpi["r200_0"].gronda == 9.0 and corpi["r200_0"].fonte_altezza.startswith("stima")
    assert all(c.licenza == "ODbL 1.0" for c in corpi.values())
    assert 1000 < corpi["w100"].area < 1200                                   # ~32 × 33 m in EPSG:7791


def test_riquadro_piccolo_e_nome():
    assert OC.url_mappa((12.56, 44.0555, 12.5735, 44.064)).startswith("https://api.openstreetmap.org/api/0.6/map?bbox=12.560000,44.055500")
    with pytest.raises(ValueError, match="troppo grande"):
        OC.url_mappa((12.0, 44.0, 12.6, 44.2))
    with pytest.raises(ValueError):
        OC.prepara((12.56, 44.0555, 12.5735, 44.064), Path("/tmp"), "Nome Sbagliato", dtm=False, scarica=lambda u: XML)


def test_prepara_archivio_odbl(tmp_path):
    chiamate = []
    esito = OC.prepara((12.565, 44.059, 12.569, 44.062), tmp_path, "rimini-prova", 9.0, dtm=False,
                       scarica=lambda u: chiamate.append(u) or XML)
    assert len(chiamate) == 1 and esito["corpi"] == 2 and esito["licenza"] == "ODbL 1.0"
    p = tmp_path / "odbl" / "rimini-prova"
    assert (p / "prodotti" / "corpi.pmtiles").exists() and (p / "grezzi" / "mappa.osm").exists()
    ind = json.loads((p / "prodotti" / "indice.json").read_text(encoding="utf-8"))
    assert ind["prova"] is True and "OpenStreetMap" in ind["attribuzione"] and not (tmp_path / "cc-by").exists()
    assert "Open Database License" in (p / "LICENZE.txt").read_text(encoding="utf-8")
    assert OC.voce_archivi("rimini-prova")["base"] == "/edifici3d/odbl/rimini-prova/prodotti/"


def test_dtm_wcs_a_blocchi(tmp_path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from edifici3d import dtm_wcs as DW
    b = DW.blocchi((780000, 4878000, 795000, 4898000))
    assert len(b) == 4 and b[1] == (790000, 4878000, 795000, 4888000)
    with pytest.raises(ValueError, match="quadranti"):
        DW.blocchi((500000, 4800000, 800000, 5000000))

    def finto(url):                                      # GeoTIFF del blocco chiesto, quota = x/1000
        q = dict(x.split("=") for x in url.split("?")[1].split("&"))
        x0, y0, x1, y1 = (float(v) for v in q["bbox"].split(","))
        w, h = int((x1 - x0) / 5), int((y1 - y0) / 5)
        p = tmp_path / "t.tif"
        with rasterio.open(p, "w", driver="GTiff", width=w, height=h, count=1, dtype="float32", crs="EPSG:7791",
                           transform=from_origin(x0, y1, 5, 5)) as d:
            d.write(np.full((1, h, w), x0 / 1000, dtype="float32"))
        return p.read_bytes()
    e = DW.scarica((780000, 4878000, 790000, 4886000), tmp_path / "dtm.tif", finto, pausa=0)
    assert e["blocchi"] == 1 and e["celle"] == [2000, 1600] and "CC BY" in e["licenza"]
    with rasterio.open(tmp_path / "dtm.tif") as r:
        assert r.crs.to_epsg() == 7791 and float(r.read(1)[0, 0]) == 780.0


# 07/11/2026: multipoligoni con way aperte e fori (cortili)
XML_MP = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
 <node id="1" lat="44.0600" lon="12.5660"/><node id="2" lat="44.0600" lon="12.5670"/>
 <node id="3" lat="44.0607" lon="12.5670"/><node id="4" lat="44.0607" lon="12.5660"/>
 <node id="11" lat="44.0602" lon="12.5663"/><node id="12" lat="44.0602" lon="12.5667"/>
 <node id="13" lat="44.0605" lon="12.5667"/><node id="14" lat="44.0605" lon="12.5663"/>
 <way id="300"><nd ref="1"/><nd ref="2"/><nd ref="3"/></way>
 <way id="301"><nd ref="3"/><nd ref="4"/><nd ref="1"/></way>
 <way id="302"><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="14"/><nd ref="11"/></way>
 <relation id="400"><member type="way" ref="300" role="outer"/><member type="way" ref="301" role="outer"/>
  <member type="way" ref="302" role="inner"/><tag k="type" v="multipolygon"/><tag k="building" v="public"/></relation>
</osm>"""


def test_multipoligono_way_aperte_e_cortile():
    from pyproj import Transformer
    from shapely.geometry import Polygon
    el = OC.edifici_da_xml(XML_MP)
    assert [t["osm_id"] for t, _ in el] == ["r400_0"]
    g = el[0][1]
    assert g.geom_type == "Polygon" and len(g.interiors) == 1
    t = Transformer.from_crs("EPSG:4326", "EPSG:7791", always_xy=True)
    m = lambda pts: Polygon([t.transform(x, y) for x, y in pts])
    fuori = m([(12.5660, 44.0600), (12.5670, 44.0600), (12.5670, 44.0607), (12.5660, 44.0607)])
    dentro = m([(12.5663, 44.0602), (12.5667, 44.0602), (12.5667, 44.0605), (12.5663, 44.0605)])
    assert abs(g.area - (fuori.area - dentro.area)) < 1.0 and dentro.area > 900
    c = OC.corpi_con_stima(el, 9.0)[0]
    assert c.id == "r400_0" and abs(c.area - g.area) < 1e-6


def test_prepara_con_dtm_gia_scaricato(tmp_path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    dtm = tmp_path / "dtm5.tif"
    with rasterio.open(dtm, "w", driver="GTiff", width=400, height=400, count=1, dtype="float32", crs="EPSG:7791",
                       transform=from_origin(785000, 4886000, 5, 5)) as d:
        d.write(np.full((1, 400, 400), 7.5, dtype="float32"))
    chiamate = []
    esito = OC.prepara((12.565, 44.059, 12.569, 44.062), tmp_path, "rimini-prova", 9.0, dtm=True, osm_file=None,
                       scarica=lambda u: chiamate.append(u) or XML_MP, dtm_file=dtm)
    assert len(chiamate) == 1 and "openstreetmap" in chiamate[0]          # solo OSM, nessuna richiesta al WCS
    # dal 07/11/2026 il terreno 3D viene dalla rotta del server: il DTM dà solo le quote dei corpi
    assert esito["corpi"] == 1 and not (tmp_path / "odbl" / "rimini-prova" / "prodotti" / "terreno.pmtiles").exists()
    assert esito["terreno"] == "/api/terreno/{z}/{x}/{y}.png" and esito["quote_da_dtm"]
    ind = json.loads((tmp_path / "odbl" / "rimini-prova" / "prodotti" / "contesto" / f"{esito['nomi_celle'][0]}.json").read_text(encoding="utf-8"))
    f = ind["features"][0]
    assert len(f["geometry"]["coordinates"]) == 2 and f["properties"]["quota_terreno"] == 7.5   # il cortile resta


# ----------------------------------------------------------------------------------- 07/11/2026: ripiego OSM al volo
XML_DUE_PARTI = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Overpass API">
 <node id="1" lat="43.9040" lon="12.9060"/><node id="2" lat="43.9040" lon="12.9066"/>
 <node id="3" lat="43.9045" lon="12.9066"/><node id="4" lat="43.9045" lon="12.9060"/>
 <node id="5" lat="43.9041" lon="12.9062"/><node id="6" lat="43.9041" lon="12.9064"/>
 <node id="7" lat="43.9043" lon="12.9064"/><node id="8" lat="43.9043" lon="12.9062"/>
 <node id="11" lat="43.9050" lon="12.9070"/><node id="12" lat="43.9050" lon="12.9072"/>
 <node id="13" lat="43.9052" lon="12.9072"/><node id="14" lat="43.9052" lon="12.9070"/>
 <way id="300"><nd ref="1"/><nd ref="2"/><nd ref="3"/></way>
 <way id="301"><nd ref="3"/><nd ref="4"/><nd ref="1"/></way>
 <way id="302"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/></way>
 <way id="303"><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="14"/><nd ref="11"/></way>
 <relation id="400"><member type="way" ref="300" role="outer"/><member type="way" ref="301" role="outer"/>
  <member type="way" ref="302" role="inner"/><member type="way" ref="303" role="outer"/>
  <tag k="type" v="multipolygon"/><tag k="building" v="hospital"/><tag k="height" v="21.5"/></relation>
</osm>"""


def test_ripiego_al_volo_corpi_e_query():
    q = OC.query_punto(12.906, 43.904)
    assert q.startswith("[out:xml]") and "around:400,43.904000,12.906000" in q and "(._;>;);out body qt;" in q
    assert 'relation["building"]["type"="multipolygon"]' in q
    assert OC.crs_metrico(9.2) == "EPSG:32632" and OC.crs_metrico(12.9) == "EPSG:32633" and OC.crs_metrico(18.3) == "EPSG:32634"
    assert OC.errore_overpass(XML) is None
    assert "timed out" in OC.errore_overpass(b"<osm><remark> runtime error: Query timed out in \"query\" </remark></osm>")
    assert OC.errore_overpass(b"<osm><remark>nota qualsiasi</remark></osm>") is None
    d = OC.corpi_al_volo(XML_DUE_PARTI, 12.906, 43.904)
    assert d["licenza"] == "ODbL 1.0" and "OpenStreetMap" in d["attribuzione"] and d["corpi"] == 2 and d["altezze_stimate"] == 0
    fs = {f["properties"]["id"]: f for f in d["features"]}
    assert set(fs) == {"r400_0", "r400_1"}
    # i due pezzi del multipoligono (way outer aperte saldate + una chiusa) sono un edificio solo, con il cortile
    assert {f["properties"]["edificio"] for f in fs.values()} == {"r400"}
    grande = fs["r400_0"]
    assert len(grande["geometry"]["coordinates"]) == 2                                   # esterno + cortile
    lon, lat = grande["geometry"]["coordinates"][0][0]
    assert 12.9 < lon < 12.91 and 43.9 < lat < 43.91                                     # WGS84, non metri
    p = grande["properties"]
    assert p["gronda"] == 21.5 and p["fonte_altezza"] == "OSM height" and p["licenza"] == "ODbL 1.0" and p["uso"] == "ospedale"
    # senza altezza in OSM: stima dichiarata
    s = OC.corpi_al_volo(XML, 12.566, 44.06)
    st = {f["properties"]["id"]: f["properties"] for f in s["features"]}
    assert st["r200_0"]["qualita"] == "stima" and st["r200_0"]["fonte_altezza"].startswith("stima") and s["altezze_stimate"] == 1
    assert OC.corpi_al_volo(b"<osm></osm>", 12.9, 43.9)["features"] == []


def test_origine_e_conteggi_delle_altezze_al_volo():
    """07/11/2026 sera: ogni corpo OSM porta l'origine dell'altezza; i conteggi per origine sono nella risposta."""
    from edifici3d import osm_campione as OC
    xml = b"""<?xml version="1.0"?><osm version="0.6">
 <node id="1" lat="43.9040" lon="12.9060"/><node id="2" lat="43.9040" lon="12.9063"/><node id="3" lat="43.9042" lon="12.9063"/><node id="4" lat="43.9042" lon="12.9060"/>
 <node id="5" lat="43.9045" lon="12.9060"/><node id="6" lat="43.9045" lon="12.9063"/><node id="7" lat="43.9047" lon="12.9063"/><node id="8" lat="43.9047" lon="12.9060"/>
 <node id="9" lat="43.9050" lon="12.9060"/><node id="10" lat="43.9050" lon="12.9063"/><node id="11" lat="43.9052" lon="12.9063"/><node id="12" lat="43.9052" lon="12.9060"/>
 <way id="1"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="building" v="yes"/><tag k="height" v="21 m"/></way>
 <way id="2"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/><tag k="building" v="yes"/><tag k="building:levels" v="4"/></way>
 <way id="3"><nd ref="9"/><nd ref="10"/><nd ref="11"/><nd ref="12"/><nd ref="9"/><tag k="building" v="yes"/></way>
</osm>"""
    d = OC.corpi_al_volo(xml, 12.906, 43.904)
    org = {f["properties"]["id"]: f["properties"]["origine_altezza"] for f in d["features"]}
    assert sorted(org.values()) == ["fissa", "osm_height", "osm_piani"]
    assert d["altezze"] == {"osm_height": 1, "osm_piani": 1, "dbtr_vicini": 0, "osm_vicini": 0, "fissa": 1} and d["altezze_stimate"] == 1
    vicini = [(12.9061 + 0.0002 * k, 43.9051, g) for k, g in enumerate([5, 6, 7, 30])]
    assert OC.altezze_da_vicini(d["features"], vicini) == 1                 # solo il corpo a 9 m fissi
    p = next(f["properties"] for f in d["features"] if f["properties"]["origine_altezza"] == "dbtr_vicini")
    assert p["gronda"] == 6.5 and p["fonte_altezza"].startswith("stima: mediana dei corpi DBTR vicini (4 entro 200 m")
    assert OC.conta_altezze(d)["altezze"]["dbtr_vicini"] == 1
