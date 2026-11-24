"""Prove della rotta /api/cer-fv (servizio/cer_fv.py, 24/11/2026): terreni pubblici vicino a una cabina primaria.

File costruito qui con la stessa struttura di `fase17-cer-fv/cer_fv/terreni.py` (tabella `terreni` + R*Tree); nessuna rete.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servizio import config as C, cer_fv as F, protezione as P   # noqa: E402

COLONNE = ["id"] + list(F.CAMPI)


def _file(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(d / "terreni_pubblici_2023.sqlite")
    db.execute(f"CREATE TABLE terreni ({', '.join(COLONNE)})")
    db.execute("CREATE VIRTUAL TABLE terreni_rt USING rtree(id, ovest, est, sud, nord)")
    righe = [(12.50, 44.05, 30000, 80, "alta"), (12.52, 44.05, 5000, 10, "bassa"), (12.60, 44.05, 90000, None, None),
             (12.505, 44.051, 15000, 40, "media")]
    for i, (lon, lat, area, p, cl) in enumerate(righe, 1):
        r = {c: None for c in COLONNE}
        r.update(id=i, ref=f"H294_0000{i}.1", lon=lon, lat=lat, area_m2=area, comune="RIMINI", ente="COMUNE DI RIMINI",
                 n_enti=1, prob_coltura=p, classe_coltura=cl, foglio="1", particella=str(i))
        db.execute(f"INSERT INTO terreni VALUES ({','.join('?' * len(COLONNE))})", [r[c] for c in COLONNE])
        db.execute("INSERT INTO terreni_rt VALUES (?,?,?,?,?)", (i, lon, lon, lat, lat))
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.execute("INSERT INTO info VALUES ('anno', '2023'), ('campagne_agrea', '[2022, 2023, 2024]')")
    db.commit(); db.close()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CARTELLA_CER_FV", tmp_path / "cer_fv", raising=False)
    P.limiti.clear()
    app = FastAPI(); app.include_router(F.router)
    return TestClient(app), tmp_path / "cer_fv"


def test_senza_file(client):
    c, _ = client
    assert c.get("/api/cer-fv/info").json() == {"disponibile": False}
    assert c.get("/api/cer-fv/terreni?lon=12.5&lat=44.05").status_code == 503


def test_terreni_vicini(client):
    c, d = client
    _file(d)
    i = c.get("/api/cer-fv/info").json()
    assert i["disponibile"] and i["anno"] == 2023 and i["campagne_agrea"] == [2022, 2023, 2024] and "AGREA" in i["attribuzione"]
    r = c.get("/api/cer-fv/terreni?lon=12.5&lat=44.05&raggio_km=3").json()
    assert [t["ref"] for t in r["terreni"]] == ["H294_00001.1", "H294_00004.1", "H294_00002.1"]   # il quarto è a ~8 km
    assert r["terreni"][0]["distanza_m"] == 0 and r["terreni"][2]["distanza_m"] == pytest.approx(1600, abs=20)
    assert r["terreni"][0]["prob_coltura"] == 80 and r["terreni"][0]["classe_coltura"] == "alta"
    assert "non ceduti" in r["attribuzione"]
    r = c.get("/api/cer-fv/terreni?lon=12.5&lat=44.05&raggio_km=3&min_m2=10000&limite=1").json()
    assert [t["ref"] for t in r["terreni"]] == ["H294_00001.1"] and r["altri"]
    assert c.get("/api/cer-fv/terreni?lon=12.5&lat=44.05&raggio_km=99").json()["raggio_km"] == 15
    assert c.get("/api/cer-fv/terreni?lon=2&lat=60").status_code == 400
    # nessun campo dei dati AGREA o personale
    assert not set(r["terreni"][0]) & {"desc_colt", "flag_bio", "flag_inte", "codice_fiscale", "cedente"}
