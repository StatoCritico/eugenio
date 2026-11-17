"""Prove delle rotte degli immobili delle PA (servizio/immobili_pa.py, 17/11/2026): indice SQLite costruito qui con la
stessa struttura di `territorio.immobili_pa_sito.indice_sqlite`; nessuna rete."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, immobili_pa as I, protezione as P   # noqa: E402


def _indice(f: Path):
    db = sqlite3.connect(f)
    db.execute("CREATE TABLE beni (id_bene, ref_ade, aggancio, natura, tipologia, amministrazione, tipologia_amm, regione,"
               " comune, indirizzo, civico, id_catastale, lat, lon, superficie_mq, gruppo)")
    db.execute("CREATE VIRTUAL TABLE cerca USING fts5(testo, tokenize='unicode61 remove_diacritics 2')")
    beni = [("1", "A045_000100.1", "esatto", "FABBRICATO", "Edificio scolastico", "COMUNE DI ACQUASPARTA (TR)", "Comuni",
             "UMBRIA", "Acquasparta", "Via Roma", "3", "A045:::1:1::2", 42.7334, 12.493, 1250, "C"),
            ("2", None, None, "TERRENO", "Terreno agricolo", "UNIVERSITA' DEGLI STUDI DI PERUGIA", "Università", "UMBRIA",
             "Perugia", "", "", "G478::12:5:::", 43.1, 12.38, 9000, "U")]
    db.executemany("INSERT INTO beni VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", beni)
    db.executemany("INSERT INTO cerca(rowid, testo) VALUES (?, ?)",
                   [(i + 1, " ".join(str(x or "") for x in (b[5], b[8], b[9], b[10], b[4], b[11]))) for i, b in enumerate(beni)])
    db.execute("CREATE TABLE particelle (ref_ade PRIMARY KEY, lon, lat, ovest, sud, est, nord, area_m2, n_beni)")
    db.execute("INSERT INTO particelle VALUES ('A045_000100.1', 12.493, 42.7335, 12.4925, 42.733, 12.4935, 42.734, 8800, 1)")
    db.execute("CREATE TABLE info (chiave PRIMARY KEY, valore)")
    db.execute("INSERT INTO info VALUES ('anno', '2023'), ('pmtiles', ?)", [json.dumps("/edifici3d/immobili_pa/immobili_pa_2023.pmtiles")])
    db.commit(); db.close()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CARTELLA_IMMOBILI_PA", tmp_path, raising=False)
    P.limiti.clear()
    app = FastAPI(); app.include_router(I.router)
    return TestClient(app), tmp_path


def test_senza_indice(client):
    c, _ = client
    assert c.get("/api/immobili-pa/info").json() == {"disponibile": False}
    assert c.get("/api/immobili-pa/cerca?q=scuola").status_code == 503


def test_ricerca_scheda_e_bene(client):
    c, d = client
    _indice(d / "immobili_pa_2023.sqlite")
    db = sqlite3.connect(d / "immobili_pa_2023.sqlite")     # seconda unità nella stessa particella: un solo risultato
    db.execute("INSERT INTO beni SELECT '3', ref_ade, aggancio, natura, 'Edificio scolastico', amministrazione, tipologia_amm, regione,"
               " comune, indirizzo, civico, id_catastale, lat, lon, 30, gruppo FROM beni WHERE id_bene = '1'")
    db.execute("INSERT INTO cerca(rowid, testo) SELECT 3, testo FROM cerca WHERE rowid = 1"); db.commit(); db.close()
    i = c.get("/api/immobili-pa/info").json()
    assert i["disponibile"] and i["anno"] == 2023 and i["pmtiles"].endswith(".pmtiles")
    r = c.get("/api/immobili-pa/cerca", params={"q": "acquasp scolast"}).json()["risultati"]
    assert [x["id_bene"] for x in r] == ["1"] and r[0]["punto"] == [12.493, 42.7335]     # centro della particella
    assert r[0]["altri_nella_particella"] == 1
    r = c.get("/api/immobili-pa/cerca", params={"q": "perugia", "gruppo": "U"}).json()["risultati"]
    assert r[0]["punto"] == [12.38, 43.1] and "ref_ade" not in r[0]                       # senza particella: punto MEF
    assert c.get("/api/immobili-pa/cerca", params={"q": "perugia", "gruppo": "C"}).json()["risultati"] == []
    assert c.get("/api/immobili-pa/cerca", params={"q": "\"; DROP"}).status_code in (200, 400)
    assert c.get("/api/immobili-pa/cerca", params={"q": "a"}).status_code == 400
    p = c.get("/api/immobili-pa/particella/a045_000100.1").json()
    assert p["particella"]["riquadro"][0] == 12.4925 and p["beni"][0]["tipologia"] == "Edificio scolastico"
    assert c.get("/api/immobili-pa/particella/xx").status_code == 400
    assert c.get("/api/immobili-pa/particella/A045_000100.9").status_code == 404
    assert c.get("/api/immobili-pa/bene/2").json()["bene"]["comune"] == "Perugia"
    assert c.get("/api/immobili-pa/bene/abc").status_code == 400


def test_limite_orario(client, monkeypatch):
    c, d = client
    _indice(d / "immobili_pa_2023.sqlite")
    monkeypatch.setitem(P.LIMITI, "immobili_pa", (2, 3600))
    assert c.get("/api/immobili-pa/bene/1").status_code == 200
    assert c.get("/api/immobili-pa/bene/1").status_code == 200
    assert c.get("/api/immobili-pa/bene/1").status_code == 429


def test_domanda_fts():
    assert I.domanda_fts("Scuola  Via Roma, 3") == '"scuola"* AND "via"* AND "roma"*'
    assert I.domanda_fts("a ; ") is None
