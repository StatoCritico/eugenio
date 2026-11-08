"""Prove del ripiego OpenStreetMap di Modelli 3D (servizio/edifici_osm.py, decisione di Paolo del 07/11/2026): Overpass
simulato (nessuna rete), copia su disco per cella, limiti per IP, tetto per tutto il sito, verifica anti-robot, licenza
ODbL, spegnimento da .env, errori di Overpass. La prova dal vivo (Pesaro e Cesena) è in AGGIORNAMENTO_2026-11-07.md.

Si eseguono dalla cartella fase4-server con PYTHONPATH che comprende ../fase10-edifici3d (README della fase 4)."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fase10-edifici3d"))

from servizio import config as C, edifici_osm as EO, protezione as P, strati as S   # noqa: E402

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Overpass API 0.7.62">
 <node id="1" lat="43.9040" lon="12.9060"/><node id="2" lat="43.9040" lon="12.9066"/>
 <node id="3" lat="43.9045" lon="12.9066"/><node id="4" lat="43.9045" lon="12.9060"/>
 <node id="5" lat="43.9041" lon="12.9062"/><node id="6" lat="43.9041" lon="12.9064"/>
 <node id="7" lat="43.9043" lon="12.9064"/><node id="8" lat="43.9043" lon="12.9062"/>
 <node id="11" lat="43.9030" lon="12.9050"/><node id="12" lat="43.9030" lon="12.9053"/>
 <node id="13" lat="43.9032" lon="12.9053"/><node id="14" lat="43.9032" lon="12.9050"/>
 <way id="300"><nd ref="1"/><nd ref="2"/><nd ref="3"/></way>
 <way id="301"><nd ref="3"/><nd ref="4"/><nd ref="1"/></way>
 <way id="302"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/></way>
 <way id="303"><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="14"/><nd ref="11"/><tag k="building" v="house"/></way>
 <relation id="400"><member type="way" ref="300" role="outer"/><member type="way" ref="301" role="outer"/>
  <member type="way" ref="302" role="inner"/><tag k="type" v="multipolygon"/><tag k="building" v="hospital"/>
  <tag k="building:levels" v="5"/></relation>
</osm>"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "CARTELLA_EDIFICI_INTERNA", tmp_path / "edifici")
    EO._archivi_cache.update(mtime=None, archivi=[]); EO._celle_cache.clear()
    monkeypatch.setattr(C, "EDIFICI_OSM", True)
    monkeypatch.setattr(C, "EDIFICI_OSM_URL", [])
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", "")
    monkeypatch.setattr(C, "TURNSTILE_SECRET", "")
    monkeypatch.setattr(EO.time, "sleep", lambda s: None)
    P.limiti.clear()
    chiamate = []

    def finto(url, dati=None, timeout=None):
        chiamate.append((url, dati, timeout))
        if "riserva" in url:
            return httpx.Response(200, content=XML, headers={"content-type": "application/osm3s+xml"})
        return httpx.Response(504, text="Gateway Timeout", headers={"content-type": "text/html"})

    monkeypatch.setattr(S, "_scarica", finto)
    monkeypatch.setattr(S, "istanze_overpass", lambda: ["https://principale/api/interpreter", "https://riserva/api/interpreter"])
    app = FastAPI()
    app.include_router(EO.router)
    yield TestClient(app), chiamate
    P.limiti.clear()


def test_cella_e_query():
    assert EO.cella(12.9061, 43.9041) == (12.906, 43.904, "21952_6453")
    assert EO.cella(12.9069, 43.9049)[2] == "21952_6453" and EO.cella(12.9071, 43.9041)[2] == "21952_6454"


def test_corpi_osm_con_licenza_copia_e_riserva(client, tmp_path):
    c, chiamate = client
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers={"X-Forwarded-For": "203.0.113.5"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["licenza"] == "ODbL 1.0" and "OpenStreetMap" in d["attribuzione"] and r.headers["x-licenza"] == "ODbL 1.0"
    assert d["scheda"] == "https://www.openstreetmap.org/copyright" and "stima" in d["nota"]
    assert d["centro"] == [12.906, 43.904] and d["raggio"] == 400 and d["corpi"] == 2
    fs = {f["properties"]["id"]: f for f in d["features"]}
    assert set(fs) == {"r400_0", "w303"}
    assert len(fs["r400_0"]["geometry"]["coordinates"]) == 2                     # multipoligono con il cortile
    assert fs["r400_0"]["properties"]["edificio"] == "r400" and fs["r400_0"]["properties"]["gronda"] == 15.0
    assert fs["w303"]["properties"]["qualita"] == "stima" and fs["w303"]["properties"]["fonte_altezza"].startswith("stima")
    assert all(f["properties"]["licenza"] == "ODbL 1.0" for f in d["features"]) and d["altezze_stimate"] == 1
    # principale 504 → riserva; query piccola sul centro della cella (non il punto esatto), in XML
    assert [x[0] for x in chiamate] == ["https://principale/api/interpreter", "https://riserva/api/interpreter"]
    q = chiamate[0][1]
    assert "around:400,43.904000,12.906000" in q and q.startswith("[out:xml]") and chiamate[0][2] == C.EDIFICI_OSM_TIMEOUT_S
    assert (tmp_path / "edifici_osm" / "21952_6453.json").exists()
    # un altro punto della stessa cella: dalla copia, nessuna chiamata
    assert c.get("/api/edifici/osm?lon=12.9068&lat=43.9047").json()["corpi"] == 2 and len(chiamate) == 2


def test_copia_scaduta_e_pulizia(client, tmp_path, monkeypatch):
    import os
    import time
    c, chiamate = client
    assert c.get("/api/edifici/osm?lon=12.9061&lat=43.9041").status_code == 200
    f = tmp_path / "edifici_osm" / "21952_6453.json"
    vecchio = time.time() - (C.EDIFICI_OSM_GIORNI + 1) * 86400
    os.utime(f, (vecchio, vecchio))
    assert c.get("/api/edifici/osm?lon=12.9061&lat=43.9041").status_code == 200 and len(chiamate) == 4
    os.utime(f, (vecchio, vecchio))
    assert EO.pulisci() == 1 and not f.exists()


def test_limiti_tetto_e_spegnimento(client, monkeypatch):
    c, chiamate = client
    monkeypatch.setattr(C, "EDIFICI_OSM_ORA", 2)
    h = {"X-Forwarded-For": "203.0.113.7"}
    assert c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers=h).status_code == 200
    assert c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers=h).status_code == 200      # anche la copia conta
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers=h)
    assert r.status_code == 429 and "OpenStreetMap" in r.json()["detail"]
    # tetto per tutto il sito: la cella nuova non chiama Overpass
    monkeypatch.setattr(C, "EDIFICI_OSM_TETTO_ORA", 1)
    n = len(chiamate)
    r = c.get("/api/edifici/osm?lon=12.95&lat=43.90", headers={"X-Forwarded-For": "203.0.113.8"})
    assert r.status_code == 503 and "quota" in r.json()["detail"] and len(chiamate) == n
    # fuori dall'Italia
    assert c.get("/api/edifici/osm?lon=2.35&lat=48.85", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 400
    # spento dal .env
    monkeypatch.setattr(C, "EDIFICI_OSM", False)
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == 404 and "spento" in r.json()["detail"]


def test_overpass_giu_o_con_errore(client, monkeypatch, tmp_path):
    c, _ = client

    def giu(url, dati=None, timeout=None):
        raise httpx.ConnectTimeout("lento")
    monkeypatch.setattr(S, "_scarica", giu)
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041")
    assert r.status_code == 502 and "non risponde" in r.json()["detail"]
    assert not (tmp_path / "edifici_osm").exists() or not list((tmp_path / "edifici_osm").glob("*.json"))

    def timeout_dentro(url, dati=None, timeout=None):                 # Overpass: 200 con la query andata in timeout
        return httpx.Response(200, content=b'<osm><remark> runtime error: Query timed out in "query" at line 1 </remark></osm>',
                              headers={"content-type": "application/osm3s+xml"})
    monkeypatch.setattr(S, "_scarica", timeout_dentro)
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041")
    assert r.status_code == 502 and "non ha completato" in r.json()["detail"]

    def troppe(url, dati=None, timeout=None):
        return httpx.Response(429, text="Too Many Requests", headers={"content-type": "text/plain"})
    monkeypatch.setattr(S, "_scarica", troppe)
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041")
    assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_turno_occupato(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(C, "EDIFICI_OSM_ATTESA_S", 0.05)
    EO._turno.acquire()
    try:
        r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041")
        assert r.status_code == 503 and r.headers["retry-after"] == "10"
    finally:
        EO._turno.release()


def test_serve_la_verifica_anti_robot(client, monkeypatch):
    c, chiamate = client
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", "0xPUBBLICA")
    monkeypatch.setattr(C, "TURNSTILE_SECRET", "0xSEGRETA")
    h = {"X-Forwarded-For": "203.0.113.30"}
    r = c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers=h)
    assert r.status_code == 401 and r.headers["x-eugenio-verifica"] == "1" and not chiamate
    g, _ = P.crea_sessione("203.0.113.30")
    assert c.get("/api/edifici/osm?lon=12.9061&lat=43.9041", headers={**h, "X-EuGEnio-Sessione": g}).status_code == 200
    assert "edifici_osm" in P.TIPI_PROTETTI


def _archivio_vicino(radice: Path, gronde, lon0=12.9051, lat0=43.9031):
    """Archivio DBTR finto con corpi quadrati attorno a (lon0, lat0) nella cella di contesto 0,01°."""
    import json
    import math
    prod = radice / "cc-by" / "er" / "finto" / "prodotti"
    (prod / "contesto").mkdir(parents=True)
    fs = []
    for k, g in enumerate(gronde):
        lo, la = lon0 + 0.0003 * (k % 4), lat0 + 0.0003 * (k // 4)
        fs.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[lo, la], [lo + 1e-4, la], [lo + 1e-4, la + 1e-4],
                   [lo, la + 1e-4], [lo, la]]]}, "properties": {"id": f"U{k}", "edificio": f"E{k}", "gronda": g,
                   "fonte_altezza": "DBTR H_UVL (altezza del corpo, ±3 m)"}})
    # un corpo portato alla stima non conta
    fs.append({"type": "Feature", "geometry": fs[0]["geometry"], "properties": {"id": "S", "edificio": "S", "gronda": 40,
               "fonte_altezza": "stima: altezza DBTR non plausibile (114 m)", "h_dbtr_scartata": 114}})
    nome = f"{math.floor(lon0 / 0.01)}_{math.floor(lat0 / 0.01)}"
    (prod / "contesto" / f"{nome}.json").write_text(json.dumps({"type": "FeatureCollection", "features": fs}), encoding="utf-8")
    (prod / "indice.json").write_text(json.dumps({"riquadro": [12.8, 43.8, 13.0, 44.0], "cella": 0.01, "nome": "finto"}), encoding="utf-8")
    (radice / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/finto/prodotti/"}]}), encoding="utf-8")


def test_altezze_osm_dai_corpi_dbtr_vicini(client, tmp_path):
    """07/11/2026 (decisione di Paolo): corpi OSM senza height né piani → mediana dei corpi DBTR entro 200 m (almeno 3,
    non stimati); altrove 9 m; origine per corpo e conteggi nella risposta."""
    c, _ = client
    d = c.get("/api/edifici/osm", params={"lon": 12.9061, "lat": 43.9040}).json()
    org = {f["properties"]["id"]: f["properties"]["origine_altezza"] for f in d["features"]}
    assert org["w303"] == "fissa" and set(org.values()) == {"fissa", "osm_piani"}
    assert d["altezze"]["fissa"] == 1 and d["altezze"]["dbtr_vicini"] == 0 and d["altezze_stimate"] == 1
    # archivio DBTR vicino (la copia su disco resta com'era: le altezze si calcolano a ogni risposta)
    _archivio_vicino(tmp_path / "edifici", [6, 7, 8, 12, 13])
    d = c.get("/api/edifici/osm", params={"lon": 12.9061, "lat": 43.9040}).json()
    p = next(f["properties"] for f in d["features"] if f["properties"]["id"] == "w303")
    assert p["origine_altezza"] == "dbtr_vicini" and p["gronda"] == 8.0 and p["altezza"] == 8.0 and p["qualita"] == "stima"
    assert "mediana dei corpi DBTR vicini (5 entro 200 m: 8 m)" in p["fonte_altezza"]
    osp = [f["properties"] for f in d["features"] if f["properties"]["edificio"] == "r400"]
    assert osp and all(x["origine_altezza"] == "osm_piani" and x["gronda"] == 15 for x in osp)
    assert d["altezze"] == {"osm_height": 0, "osm_piani": len(osp), "dbtr_vicini": 1, "osm_vicini": 0, "fissa": 0}
    copia = next((C.DATI / "edifici_osm").glob("*.json")).read_text(encoding="utf-8")
    assert "\"origine_altezza\":\"dbtr_vicini\"" not in copia


def test_altezze_osm_pochi_vicini_restano_9_m():
    from edifici3d import osm_campione as OC
    f = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[12.0, 44.0], [12.0001, 44.0], [12.0001, 44.0001], [12.0, 44.0]]]},
         "properties": {"id": "w1", "gronda": 9.0, "fonte_altezza": "stima: altezza non presente in OSM (9 m)"}}
    assert OC.altezze_da_vicini([f], [(12.0, 44.0, 20.0), (12.0005, 44.0, 22.0)]) == 0          # due soli vicini
    assert OC.altezze_da_vicini([f], [(12.0, 44.0, 20.0), (12.0005, 44.0, 22.0), (12.01, 44.0, 5.0)]) == 0   # il terzo a ~800 m
    assert OC.altezze_da_vicini([f], [(12.0, 44.0, 20.0), (12.0005, 44.0, 22.0), (12.001, 44.001, 5.0)]) == 1
    assert f["properties"]["gronda"] == 20.0 and f["properties"]["origine_altezza"] == "dbtr_vicini"
