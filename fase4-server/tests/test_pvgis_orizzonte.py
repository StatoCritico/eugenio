"""Prove del confronto PVGIS (servizio/pvgis.py) e dell'orizzonte lontano (servizio/orizzonte.py), fase 10, Fase B.

Risposte simulate, nessuna rete: PVGIS e il DEM su S3 sono stati provati dal vivo il 04/11/2026 (README della fase 10)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, orizzonte as Z, protezione as P, pvgis as V   # noqa: E402

RISPOSTA = {"inputs": {"meteo_data": {"radiation_db": "PVGIS-SARAH3", "year_min": 2005, "year_max": 2023,
                                      "horizon_db": "DEM-calculated"}},
            "outputs": {"totals": {"fixed": {"E_y": 1303.5, "H(i)_y": 1667.4, "l_total": -21.8, "SD_y": 54.3}},
                        "monthly": {"fixed": [{"month": m, "E_m": 100.0 + m} for m in range(1, 13)]}}}


def test_orizzonte_su_griglia_sintetica():
    # pianura a 0 m con un muro alto 1.000 m a 10 km verso est
    passo = 1 / 1200
    lat0, lon0 = 43.8, 12.2
    z = np.zeros((600, 900), dtype="float32")
    lat, lon = 44.05, 12.5
    m_lon = 111412.84 * np.cos(np.radians(lat))
    j = int((lon + 10000 / m_lon - lon0) / passo)
    z[:, j:j + 3] = 1000.0
    ang, dist = Z.profilo_da_griglia(z, lat0, lon0, passo, lat, lon, quota=0.0, raggio_m=20000, direzioni=72)
    est = ang[18]                                    # 90° = est
    atteso = np.degrees(np.arctan((1000 - 10000 ** 2 * (1 - Z.K_RIFRAZIONE) / (2 * Z.R_TERRA)) / 10000))
    assert est == pytest.approx(atteso, abs=0.2) and dist[18] == pytest.approx(10000, abs=150)
    assert ang[54] == 0.0                            # ovest: niente
    # la curvatura abbassa: a 20 km un muro di 30 m non si vede più da 0 m
    z2 = np.zeros_like(z)
    j2 = int((lon + 19000 / m_lon - lon0) / passo)
    z2[:, j2:j2 + 3] = 20.0
    a2, _ = Z.profilo_da_griglia(z2, lat0, lon0, passo, lat, lon, quota=0.0, raggio_m=20000, direzioni=72)
    assert a2[18] == 0.0


def test_rotta_orizzonte_con_copia(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(C, "DATI", tmp_path)
    P.limiti.clear()
    n = []

    def finto(lat, lon, h=0, direzioni=72, raggio_m=None):
        n.append(1)
        return {"lat": lat, "lon": lon, "h": h, "angoli": [1.0] * direzioni, "fonte": Z.FONTE}

    monkeypatch.setattr(Z, "calcola", finto)
    app = FastAPI()
    app.include_router(Z.router)
    c = TestClient(app)
    r = c.get("/api/edifici/orizzonte", params={"lat": 44.06, "lon": 12.567, "h": 10})
    assert r.status_code == 200 and len(r.json()["angoli"]) == 72 and "Copernicus" in r.json()["fonte"]
    c.get("/api/edifici/orizzonte", params={"lat": 44.0601, "lon": 12.5671, "h": 10})
    assert len(n) == 1                               # stesso punto arrotondato: dalla copia
    assert c.get("/api/edifici/orizzonte", params={"lat": 50, "lon": 12}).status_code == 422
    assert c.get("/api/edifici/orizzonte", params={"lat": 44, "lon": 12, "direzioni": 7}).status_code == 422


def test_riduzione_e_parametri():
    a = [0.0] * 72
    a[17] = 12.0                                     # 85°: finisce nella direzione 90° (gruppo 85–90)
    r = V.riduci_orizzonte(a)
    assert len(r) == 36 and r[9] == 12.0 and max(r) == 12.0
    p = V.parametri(44.06, 12.57, {"kwp": 5, "inclinazione": 30, "orientamento": 180, "orizzonte": a}, True)
    assert p["aspect"] == 0 and p["angle"] == 30 and p["userhorizon"].count(",") == 35 and p["usehorizon"] == 1
    assert V.parametri(44, 12, {"kwp": 5, "orientamento": 270}, False)["aspect"] == 90       # ovest
    assert V.parametri(44, 12, {"kwp": 5, "orientamento": 90}, False)["aspect"] == -90       # est
    assert "userhorizon" not in V.parametri(44, 12, {"kwp": 5, "orizzonte": a}, False)


def test_rotta_pvgis_copia_e_limiti(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(C, "DATI", tmp_path)
    P.limiti.clear()
    V.ritmo.svuota()
    chiamate = []
    monkeypatch.setattr(V, "_chiama", lambda p: chiamate.append(p) or RISPOSTA)
    app = FastAPI()
    app.include_router(V.router)
    c = TestClient(app)
    corpo = {"lat": 44.06, "lon": 12.567, "aree": [{"id": "A1", "kwp": 1, "inclinazione": 30, "orientamento": 180,
                                                    "orizzonte": [5.0] * 72}]}
    r = c.post("/api/edifici/pvgis", json=corpo)
    assert r.status_code == 200
    a = r.json()["aree"][0]
    assert a["con_orizzonte"]["kwh_anno"] == 1303.5 and len(a["con_orizzonte"]["kwh_mensili"]) == 12
    assert "PVGIS" in r.json()["fonte"] and len(chiamate) == 2 and "userhorizon" in chiamate[0]
    c.post("/api/edifici/pvgis", json=corpo)
    assert len(chiamate) == 2                         # dalla copia su disco
    assert c.post("/api/edifici/pvgis", json={"lat": 44, "lon": 12, "aree": []}).status_code == 422
    assert c.post("/api/edifici/pvgis", json={"lat": 44, "lon": 12, "aree": [{"kwp": 0}]}).status_code == 422
    assert c.post("/api/edifici/pvgis", json={"lat": 44, "lon": 12, "aree": [{"id": i, "kwp": 1} for i in range(13)]}).status_code == 422


def test_ritmo_globale_sotto_30_al_secondo():
    r = V.RitmoGlobale()
    assert all(r.attendi(3, massimo_s=0) for _ in range(3))
    assert r.attendi(3, massimo_s=0) is False        # quarta nello stesso secondo, senza attesa
    assert C.PVGIS_AL_SECONDO < 30
