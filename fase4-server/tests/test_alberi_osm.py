"""Alberi indicativi da OpenStreetMap dove manca il LiDAR (09/11/2026 d): cella di 0,01°, alberi e filari, altezze e
chiome dai tag o tipiche, copia su disco, limiti di Overpass, cella vuota pulita se Overpass non risponde."""
from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from servizio import alberi_osm as A, config as C, protezione as P

CESENA = "1225_4413"          # ospedale Bufalini


def _risposta():
    return {"elements": [
        {"type": "node", "id": 1, "lon": 12.2597, "lat": 44.1326, "tags": {"natural": "tree", "height": "14 m", "diameter_crown": "9"}},
        {"type": "node", "id": 2, "lon": 12.2598, "lat": 44.1327, "tags": {"natural": "tree", "est_height": "6"}},
        {"type": "node", "id": 3, "lon": 12.2650, "lat": 44.1326, "tags": {"natural": "tree"}},                 # fuori dalla cella (12,265 E): scartato
        {"type": "way", "id": 4, "tags": {"natural": "tree_row"},
         "geometry": [{"lon": 12.2550, "lat": 44.1350}, {"lon": 12.2550 + 31 / 79900, "lat": 44.1350}]}]}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CARTELLA_ORTOFOTO", tmp_path)
    monkeypatch.setattr(C, "EDIFICI_OSM", True)
    P.limiti.clear(); A.guasti.svuota()
    chiamate = []

    def finto(urls, q, formato, timeout, nome):
        chiamate.append(q)
        return httpx.Response(200, json=_risposta(), headers={"content-type": "application/json"})
    monkeypatch.setattr(A.S, "chiedi_overpass", finto)
    app = FastAPI(); app.include_router(A.router)
    return TestClient(app), chiamate


def test_cella_di_alberi_osm(client, tmp_path):
    c, chiamate = client
    r = c.get(f"/api/alberi/osm/{CESENA}.json")
    d = r.json()
    assert r.status_code == 200 and d["stima"] is True and d["licenza"] == "ODbL 1.0" and "OpenStreetMap" in d["fonte"]
    assert d["campi"] == ["lon", "lat", "h", "quota", "lato"]
    al = d["alberi"]
    assert [12.2597, 44.1326, 14.0, None, 9.0] in al and [12.2598, 44.1327, 6.0, None, 5.0] in al
    assert all(12.25 <= a[0] < 12.26 and 44.13 <= a[1] < 44.14 for a in al)                  # solo dentro la cella
    assert sum(1 for a in al if a[1] == 44.135) == 5                                           # filare di 31 m: un albero ogni 6 m
    assert 'node["natural"="tree"]' in chiamate[0] and 'way["natural"="tree_row"]' in chiamate[0]
    n = len(chiamate)
    assert c.get(f"/api/alberi/osm/{CESENA}.json").json()["alberi"] == al and len(chiamate) == n      # dalla copia
    assert c.get("/api/alberi/osm/abc.json").status_code == 404 and c.get("/api/alberi/osm/1_1.json").status_code == 404


def test_overpass_che_non_risponde_e_limite(client, monkeypatch):
    c, _ = client

    def giu(*a):
        raise httpx.ConnectError("giù")
    monkeypatch.setattr(A.S, "chiedi_overpass", giu)
    r = c.get("/api/alberi/osm/1226_4413.json")
    assert r.status_code == 200 and r.headers["x-ortofoto-errore"] == "fonte" and r.headers["cache-control"] == "no-store" and r.json()["alberi"] == []
    monkeypatch.setattr(C, "EDIFICI_OSM_ORA", 1)
    h = {"X-Forwarded-For": "198.51.100.30"}
    c.get("/api/alberi/osm/1227_4413.json", headers=h)
    r = c.get("/api/alberi/osm/1228_4413.json", headers=h)
    assert r.status_code == 429 and r.headers["x-eugenio-limite"] == "edifici_osm"
