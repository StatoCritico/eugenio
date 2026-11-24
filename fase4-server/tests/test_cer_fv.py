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


# ---------------------------------------------------------------- (24/11/2026 sera) vincoli paesaggistici
def test_terreni_file_vecchio_senza_colonne_dei_vincoli(client, tmp_path):
    c, d = client
    d.mkdir(parents=True, exist_ok=True)
    vecchie = [x for x in COLONNE if x not in ("quota_vincolata", "vincoli", "vincoli_segnalati")]
    db = sqlite3.connect(d / "terreni_pubblici_2023.sqlite")
    db.execute(f"CREATE TABLE terreni ({', '.join(vecchie)})")
    db.execute("CREATE VIRTUAL TABLE terreni_rt USING rtree(id, ovest, est, sud, nord)")
    r = {x: None for x in vecchie}; r.update(id=1, ref="H294_1.1", lon=12.5, lat=44.05, area_m2=20000)
    db.execute(f"INSERT INTO terreni VALUES ({','.join('?' * len(vecchie))})", [r[x] for x in vecchie])
    db.execute("INSERT INTO terreni_rt VALUES (1, 12.5, 12.5, 44.05, 44.05)")
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)"); db.commit(); db.close()
    t = c.get("/api/cer-fv/terreni?lon=12.5&lat=44.05&raggio_km=1").json()["terreni"]
    assert len(t) == 1 and t[0]["quota_vincolata"] is None and "vincoli" in t[0]


def test_vincoli_nel_riquadro(client, tmp_path, monkeypatch):
    c, _ = client
    d = tmp_path / "vincoli"; d.mkdir()
    monkeypatch.setattr(C, "CARTELLA_VINCOLI", d, raising=False)
    assert c.get("/api/cer-fv/vincoli?bbox=12.4,44.0,12.6,44.1").json()["disponibile"] is False
    db = sqlite3.connect(d / "vincoli_er.sqlite")
    db.execute("CREATE TABLE v (id INTEGER PRIMARY KEY, codice, classe, nome, geojson)")
    db.execute("CREATE VIRTUAL TABLE v_rt USING rtree(id, ovest, est, sud, nord)")
    q = {"type": "Polygon", "coordinates": [[[12.5, 44.05], [12.51, 44.05], [12.51, 44.06], [12.5, 44.05]]]}
    db.execute("INSERT INTO v VALUES (1, 'boschi', 'escluso', 'foreste e boschi', ?)", (json.dumps(q),))
    db.execute("INSERT INTO v_rt VALUES (1, 12.5, 12.51, 44.05, 44.06)")
    db.execute("INSERT INTO v VALUES (2, 'boschi', 'escluso', 'lontano', ?)", (json.dumps(q),))
    db.execute("INSERT INTO v_rt VALUES (2, 11.0, 11.01, 44.5, 44.51)")
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.execute("INSERT INTO info VALUES ('attribuzione', ?)", (json.dumps("Regione Emilia-Romagna (CC BY 4.0)"),))
    db.commit(); db.close()
    r = c.get("/api/cer-fv/vincoli?bbox=12.4,44.0,12.6,44.1").json()
    assert [f["properties"]["nome"] for f in r["features"]] == ["foreste e boschi"] and "CC BY" in r["attribuzione"]
    assert c.get("/api/cer-fv/vincoli?bbox=10,43,12,45").status_code == 400            # riquadro troppo grande
    assert c.get("/api/cer-fv/vincoli?bbox=a,b").status_code == 400
