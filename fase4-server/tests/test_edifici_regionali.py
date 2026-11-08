"""Sagome regionali al volo con le altezze OSM (08/11/2026, servizio/edifici_osm.py e edifici3d/sagome_regionali.py):
WFS del Veneto e Overpass simulati (nessuna rete). In Veneto la rotta /api/edifici/osm dà le sagome della Regione (IODL
2.0) con l'altezza dell'edificio OSM sovrapposto, poi la mediana dei vicini con l'altezza OSM, poi 9 m; gli edifici OSM
senza sagoma regionale restano; bbox nel sistema nativo EPSG:6876; copia su disco; quote dal DTM del server; WFS giù →
solo OSM con l'avviso; EDIFICI_REGIONALI=false → solo OSM. La prova dal vivo su Susegana è in AGGIORNAMENTO_2026-11-07.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
FASE10 = Path(__file__).resolve().parents[2] / "fase10-edifici3d"
sys.path.insert(0, str(FASE10))
pytest.importorskip("pyproj")

from servizio import config as C, edifici_osm as EO, protezione as P, strati as S, terreno as T   # noqa: E402

LON, LAT = 12.246, 45.850                # Susegana, via San Salvatore


def _6876():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", "EPSG:6876", always_xy=True), Transformer.from_crs("EPSG:6876", "EPSG:4326", always_xy=True)


def _wfs():
    """Cinque sagome regionali (MultiPolygon con z = 0, come il WFS vero) attorno al centro della cella."""
    a, _ = _6876()
    x0, y0 = a.transform(LON, LAT)
    def q(dx, dy, w, h):
        return [[[[x0 + dx, y0 + dy, 0], [x0 + dx + w, y0 + dy, 0], [x0 + dx + w, y0 + dy + h, 0], [x0 + dx, y0 + dy + h, 0], [x0 + dx, y0 + dy, 0]]]]
    fs = [("1", q(0, 0, 20, 10), "01"), ("2", q(40, 0, 12, 12), "01"), ("3", q(80, 0, 15, 10), "01"),
          ("4", q(0, 40, 30, 20), "08"), ("5", q(300, 300, 10, 10), "01")]
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "id": f"edifici_veneto_feb2022.{i}",
            "geometry": {"type": "MultiPolygon", "coordinates": g}, "properties": {"edi_ty": "01", "edi_uso": u, "edi_stat": "03"}}
            for i, g, u in fs]}


def _xml():
    """Edifici OSM: w1 sopra la sagoma 1 (height 12), w2 sopra la 2 (3 piani), w3 sopra la 3 (piani 2), w9 lontano da tutte
    (nessuna sagoma regionale: resta OSM), w4 sopra la 4 senza altezza."""
    a, b = _6876()
    x0, y0 = a.transform(LON, LAT)
    nodi, vie, k = [], [], 1
    def via(i, dx, dy, w, h, tag):
        nonlocal k
        refs = []
        for px, py in [(dx, dy), (dx + w, dy), (dx + w, dy + h), (dx, dy + h)]:
            lo, la = b.transform(x0 + px, y0 + py)
            nodi.append(f'<node id="{k}" lat="{la:.7f}" lon="{lo:.7f}"/>'); refs.append(k); k += 1
        nd = "".join(f'<nd ref="{r}"/>' for r in refs + refs[:1])
        vie.append(f'<way id="{i}">{nd}<tag k="building" v="yes"/>{tag}</way>')
    via(1, 1, 1, 18, 8, '<tag k="height" v="12"/>')
    via(2, 40, 0, 12, 12, '<tag k="building:levels" v="3"/>')
    via(3, 80, 0, 15, 10, '<tag k="building:levels" v="2"/>')
    via(4, 0, 40, 30, 20, "")
    via(9, 150, -150, 10, 10, '<tag k="building:levels" v="4"/>')
    return ('<?xml version="1.0" encoding="UTF-8"?><osm version="0.6">' + "".join(nodi) + "".join(vie) + "</osm>").encode()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "CARTELLA_EDIFICI_INTERNA", tmp_path / "edifici")
    monkeypatch.setattr(C, "CARTELLA_TERRENO", tmp_path / "terreno")
    monkeypatch.setattr(T, "_dtm_cache", None)
    EO._archivi_cache.update(mtime=None, archivi=[]); EO._celle_cache.clear()
    for k, v in {"EDIFICI_OSM": True, "EDIFICI_REGIONALI": True, "EDIFICI_OSM_URL": [], "TURNSTILE_SITEKEY": "", "TURNSTILE_SECRET": ""}.items():
        monkeypatch.setattr(C, k, v)
    monkeypatch.setattr(EO.time, "sleep", lambda s: None)
    P.limiti.clear()
    xml = _xml()
    monkeypatch.setattr(S, "_scarica", lambda url, dati=None, timeout=None: httpx.Response(200, content=xml, headers={"content-type": "application/osm3s+xml"}))
    monkeypatch.setattr(S, "istanze_overpass", lambda: ["https://principale/api/interpreter"])
    wfs = {"chiamate": [], "risposta": _wfs(), "stato": 200}

    def finto_get(url, timeout=None, headers=None):
        wfs["chiamate"].append(url)
        if wfs["stato"] != 200:
            raise httpx.ConnectError("giù")
        return httpx.Response(200, json=wfs["risposta"], headers={"content-type": "application/json;charset=UTF-8"})
    monkeypatch.setattr(EO.httpx, "get", finto_get)
    app = FastAPI()
    app.include_router(EO.router)
    yield TestClient(app), wfs, tmp_path
    P.limiti.clear()


def test_sagome_venete_con_altezze_osm(client):
    c, wfs, tmp = client
    r = c.get(f"/api/edifici/osm?lon={LON}&lat={LAT}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert r.headers["x-licenza"] == "IODL 2.0; ODbL 1.0"
    s = d["sagome"]
    assert s["regione"] == "Veneto" and s["licenza"] == "IODL 2.0" and s["corpi"] == 5 and s["con_altezza_osm"] == 3 and s["osm_aggiunti"] == 1
    assert "Sagome dalla Regione del Veneto (IODL 2.0), altezze da OpenStreetMap" in d["nota"]
    fs = {f["properties"]["id"]: f["properties"] for f in d["features"]}
    assert fs["veneto_1"]["gronda"] == 12 and fs["veneto_1"]["origine_altezza"] == "osm_height" and "w1" in fs["veneto_1"]["fonte_altezza"]
    assert fs["veneto_2"]["gronda"] == 9 and fs["veneto_2"]["origine_altezza"] == "osm_piani"
    assert fs["veneto_1"]["licenza"] == "IODL 2.0; altezza ODbL 1.0" and fs["veneto_1"]["fonte_sagoma"].startswith("Regione del Veneto")
    # la 4 (OSM sovrapposto senza altezza): mediana dei tre vicini con l'altezza OSM; la 5 (lontana): 9 m fissi
    assert fs["veneto_4"]["origine_altezza"] == "osm_vicini" and fs["veneto_4"]["gronda"] == 9 and fs["veneto_4"]["uso"] == "capannone"
    assert fs["veneto_5"]["origine_altezza"] in ("fissa", "osm_vicini")
    assert "w9" in fs and fs["w9"]["licenza"] == "ODbL 1.0"                           # OSM senza sagoma regionale
    assert not any(k in fs for k in ("w1", "w2", "w3", "w4"))                          # i doppioni OSM non ci sono
    assert d["altezze"]["osm_height"] == 1 and d["altezze"]["osm_vicini"] >= 1
    # bbox nel sistema nativo (in EPSG:4326 il WFS del Veneto non trova nulla), riquadro di 800 m sul centro della cella
    u = wfs["chiamate"][0]
    assert "bbox=" in u and u.split("bbox=")[1].split("&")[0].endswith(",EPSG:6876") and "typeNames=rv:edifici_veneto_feb2022" in u
    x0, y0, x1, y1 = (float(v) for v in u.split("bbox=")[1].split(",")[:4])
    assert abs((x1 - x0) - 800) < 2 and 3.0e6 < x0 < 3.03e6
    # copia su disco: un altro punto della cella non richiama il WFS
    assert list((tmp / "edifici_regionali" / "veneto").glob("*.json"))
    c.get(f"/api/edifici/osm?lon={LON + 0.0004}&lat={LAT}")
    assert len(wfs["chiamate"]) == 1


def test_quote_dal_dtm_veneto(client):
    """Con il DTM del Veneto sul server i corpi hanno la quota (vista 3D col terreno anche fuori dal DBTR)."""
    c, _, tmp = client
    import rasterio
    from rasterio.transform import from_origin
    from edifici3d import dtm_locale as DL
    a, _ = _6876()
    x0, y0 = a.transform(LON, LAT)
    (tmp / "terreno").mkdir()
    src = tmp / "g.tif"
    with rasterio.open(src, "w", driver="GTiff", width=400, height=400, count=1, dtype="float32", crs="EPSG:6876",
                       transform=from_origin(x0 - 1000, y0 + 1000, 5, 5), nodata=-9999) as d:
        d.write(np.full((400, 400), 87.5, dtype="float32"), 1)
    DL.cog_server(src, tmp / "terreno" / "dtm5_veneto_tv.tif", regione="veneto")
    d = c.get(f"/api/edifici/osm?lon={LON}&lat={LAT}").json()
    assert d["quote_dtm"] == len(d["features"]) and all(abs(f["properties"]["quota_terreno"] - 87.5) < 0.01 for f in d["features"])


def test_wfs_giu_e_spegnimento(client, monkeypatch):
    c, wfs, _ = client
    wfs["stato"] = 503
    d = c.get(f"/api/edifici/osm?lon={LON}&lat={LAT}").json()
    assert "sagome" not in d and "non ha risposto" in d["avviso_sagome"] and d["licenza"] == "ODbL 1.0"
    assert {f["properties"]["id"] for f in d["features"]} == {"w1", "w2", "w3", "w4", "w9"}
    wfs["stato"] = 200
    monkeypatch.setattr(C, "EDIFICI_REGIONALI", False)
    d = c.get(f"/api/edifici/osm?lon={LON + 0.0004}&lat={LAT}").json()
    assert "sagome" not in d and "avviso_sagome" not in d


def test_fuori_dal_veneto_solo_osm(client):
    c, wfs, _ = client
    wfs["risposta"] = {"type": "FeatureCollection", "features": []}
    d = c.get(f"/api/edifici/osm?lon={LON}&lat={LAT}").json()                       # WFS vuoto: resta OSM
    assert "sagome" not in d and d["licenza"] == "ODbL 1.0"


def test_fonti_accese_sono_attive_e_senza_altezze():
    """Ogni fonte di sagome_regionali.toml è «attiva» in regioni.toml, con licenza compatibile e senza altezze."""
    import tomllib
    from edifici3d import sagome_regionali as SR
    reg = tomllib.loads((FASE10 / "fonti" / "regioni.toml").read_text(encoding="utf-8"))
    for f in SR.carica():
        r = next(x for x in reg["regione"] if x["nome"] == f["regione"])
        e = next(x for x in r["fonte"] if x["tema"] == "edifici" and x["nome"] == f["fonte"])
        assert e["stato"] == "attiva" and e["licenza"] in reg["licenze_compatibili"] and str(e.get("altezza", "")).startswith("no")
        assert f["licenza"] == e["licenza"]
    assert SR.fonte_nel_punto(LON, LAT)["id"] == "veneto" and SR.fonte_nel_punto(12.9, 43.9) is None
