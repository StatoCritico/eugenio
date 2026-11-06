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
