"""Rotte /api/analisi (fase 10, Fase E): senza modulo privato tutto «non disponibile»; con un modulo finto (scritto qui,
nessun dato di norme) l'analisi pronta risponde e le altre danno 503. Dalla cartella fase4-server, con PYTHONPATH che
comprende ../fase10-edifici3d: `python -m pytest tests`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
A = pytest.importorskip("edifici3d.analisi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from servizio import analisi as R, protezione as P  # noqa: E402

FINTO = '''
INTERFACCIA = 1
def stato():
    return {"5": {"disponibile": True, "motivo": "pronta"}}
def calcola(id, richiesta):
    return {"valori": {"kwh": 10.0}, "fonti": ["prova"], "segreto": "non deve uscire"}
'''
CORPO = {"edificio": {"corpi": [{"id": "C1", "area": 50, "gronda": 6}]}}


@pytest.fixture
def client(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(R.router)
    monkeypatch.setattr(A, "candidati", lambda: [tmp_path])
    A.dimentica()
    yield TestClient(app), tmp_path
    A.dimentica()


def test_senza_modulo(client):
    c, _ = client
    r = c.get("/api/analisi/stato").json()
    assert r["modulo"] is False and len(r["analisi"]) == 8
    # dal 05/11/2026 le analisi 7, 9 e 13 sono pubbliche (si calcolano nelle pagine): sempre disponibili
    pub = {x["id"] for x in r["analisi"] if x.get("pubblica")}
    assert pub == {"7", "9", "13"} and all(x["disponibile"] for x in r["analisi"] if x["id"] in pub)
    assert {x["messaggio"] for x in r["analisi"] if x["id"] not in pub} == {"analisi non disponibile in questa installazione"}
    assert c.post("/api/analisi/13", json=CORPO).status_code == 422
    r = c.post("/api/analisi/5", json=CORPO)
    assert r.status_code == 503 and "non disponibile in questa installazione" in r.json()["detail"]
    assert c.post("/api/analisi/42", json=CORPO).status_code == 404


def test_con_modulo_finto(client):
    c, tmp = client
    (tmp / "uni_privato").mkdir()
    (tmp / "uni_privato" / "__init__.py").write_text(FINTO, encoding="utf-8")
    A.dimentica()
    s = {x["id"]: x["disponibile"] for x in c.get("/api/analisi/stato").json()["analisi"]}
    assert s["5"] is True and s["10"] is False
    r = c.post("/api/analisi/5", json=CORPO)
    assert r.status_code == 200 and r.json()["valori"]["kwh"] == 10.0 and "segreto" not in r.json()
    assert c.post("/api/analisi/10", json=CORPO).status_code == 503
    assert c.post("/api/analisi/5", json={"edificio": {}}).status_code == 422
    assert "uni_privato" not in c.get("/api/analisi/stato").text
