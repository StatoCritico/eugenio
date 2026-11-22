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


def test_indice_sostituito_durante_il_servizio(client):
    """22/11/2026: la fase 7 scrive `.immobili_pa_<anno>.sqlite.nuovo` e poi lo sostituisce con os.replace. L'API non vede
    il provvisorio e, aprendo una connessione per richiesta (immutable=1), legge il file nuovo dalla richiesta dopo."""
    import os
    c, d = client
    f = d / "immobili_pa_2023.sqlite"
    _indice(f)
    nuovo = d / ".immobili_pa_2023.sqlite.nuovo"
    nuovo.write_bytes(b"a meta, non ancora un database")
    assert I.indice() == f
    assert c.get("/api/immobili-pa/cerca", params={"q": "perugia", "gruppo": "I"}).json()["risultati"] == []
    nuovo.unlink(); _indice(nuovo)
    db = sqlite3.connect(nuovo)        # nel nuovo indice l'università è un'Unione di Comuni (gruppo I, nuovo dal 22/11)
    db.execute("UPDATE beni SET gruppo = 'I' WHERE id_bene = '2'"); db.commit(); db.close()
    os.replace(nuovo, f)
    r = c.get("/api/immobili-pa/cerca", params={"q": "perugia", "gruppo": "i"}).json()["risultati"]
    assert [x["id_bene"] for x in r] == ["2"] and r[0]["gruppo"] == "I"


# ---------------------------------------------------------------------------------------------- ricerca per ente (22/11/2026)
CF_CESENA, CF_AUSL = "00143280402", "02483810392"


def _indice_enti(cartella: Path) -> Path:
    """Indice vero, costruito con la fase 7 (immobili_pa_sito.indice_sqlite) da due parquet scritti qui: Comune di Cesena
    con due unità nella stessa particella e un terreno; AUSL che ha in uso una delle due unità (con un soggetto cedente
    che non deve uscire) e un bene senza particella; 250 terreni dell'AUSL in 250 particelle per la paginazione."""
    pd = pytest.importorskip("pandas")
    shapely = pytest.importorskip("shapely")
    s = pytest.importorskip("territorio.immobili_pa_sito")
    base = {"settore": "S13", "macrocategoria": "Amministrazioni Locali", "titolo_proprieta": "Piena proprietà",
            "titolo_detenzione": "", "cedente": "", "cedente_cf": "", "regione": "EMILIA ROMAGNA", "provincia": "FC",
            "comune": "Cesena", "comune_cod": "C573", "civico": "", "geo_fonte": "IDENTIFICATIVI_CATASTALI",
            "georeferenziato": "Sì", "lat": 44.139, "lon": 12.243, "cubatura_mc": None, "sup_riferimento_mq": None,
            "epoca": "", "vincolo": "Nessuno", "utilizzo": "Utilizzato direttamente", "a_terzi_intera": "No",
            "a_terzi_parziale": "No", "id_catastale": ""}
    cesena = {"amministrazione": "COMUNE DI CESENA", "amm_cf": CF_CESENA, "tipologia_amm": "Comuni", "amm_regione": "EMILIA ROMAGNA",
              "amm_provincia": "FC", "amm_comune": "CESENA"}
    ausl = {"amministrazione": "AZIENDA USL DELLA ROMAGNA", "amm_cf": CF_AUSL, "tipologia_amm": "Enti Locali del Servizio Sanitario",
            "amm_regione": "EMILIA ROMAGNA", "amm_provincia": "RA", "amm_comune": "RAVENNA"}
    righe = [
        {**base, **cesena, "id_bene": "1", "natura": "FABBRICATO", "ref_ade": "C573_001000.1", "indirizzo": "Via Roma",
         "civico": "3", "tipologia": "Edificio scolastico", "superficie_mq": 1000.0, "epoca": "Dal 1961 al 1970"},
        {**base, **cesena, "id_bene": "2", "natura": "FABBRICATO", "ref_ade": "C573_001000.1", "indirizzo": "Via Roma",
         "tipologia": "Ufficio", "superficie_mq": 0.0, "sup_riferimento_mq": 200.0, "utilizzo": "Non utilizzato"},
        {**base, **cesena, "id_bene": "3", "natura": "TERRENO", "ref_ade": "C573_002000.5", "indirizzo": "",
         "tipologia": "Terreno agricolo", "superficie_mq": 5000.0},
        {**base, **ausl, "id_bene": "2", "natura": "FABBRICATO", "ref_ade": "C573_001000.1", "indirizzo": "Via Roma",
         "tipologia": "Ufficio", "superficie_mq": 0.0, "sup_riferimento_mq": 200.0, "titolo_proprieta": "",
         "titolo_detenzione": "in uso gratuito", "cedente": "MARIO ROSSI", "cedente_cf": "RSSMRA00A01H501X"},
        {**base, **ausl, "id_bene": "4", "natura": "FABBRICATO", "ref_ade": None, "indirizzo": "Viale Ghirotti",
         "civico": "286", "tipologia": "Ospedale", "superficie_mq": 9000.0, "geo_fonte": "UTENTE", "lat": 44.14, "lon": 12.25},
    ]
    for i in range(250):
        righe.append({**base, **ausl, "id_bene": str(1000 + i), "natura": "TERRENO", "ref_ade": f"C573_{3000 + i:04d}00.1",
                      "indirizzo": "", "tipologia": "Terreno agricolo", "superficie_mq": float(100 + i)})
    beni = pd.DataFrame(righe)
    bf = cartella / "beni.parquet"; beni.to_parquet(bf)
    refs = sorted({r["ref_ade"] for r in righe if r["ref_ade"]})
    geoms = [shapely.box(12.24 + i * 0.001, 44.13, 12.2405 + i * 0.001, 44.1305) for i in range(len(refs))]
    part = pd.DataFrame({"ref_ade": refs, "area_m2": [2000.0] * len(refs), "n_beni": [1] * len(refs),
                         "geometry": [shapely.to_wkb(g) for g in geoms]})
    pf = cartella / "part.parquet"; part.to_parquet(pf)
    out = cartella / "immobili_pa_2023.sqlite"
    s.indice_sqlite(bf, pf, out, info={"anno": 2023})
    return out


@pytest.fixture()
def con_enti(client):
    c, d = client
    sub = d / "lavoro"; sub.mkdir()
    f = _indice_enti(sub)
    f.rename(d / f.name)
    s = sys.modules["territorio.immobili_pa_sito"]
    return c, s.chiave_ente(CF_CESENA), s.chiave_ente(CF_AUSL)


def _niente_segreti(testo: str):
    for x in (CF_CESENA, CF_AUSL, "MARIO ROSSI", "RSSMRA00A01H501X", "amm_cf", "cedente"):
        assert x not in testo, x


def test_ente_scheda_totali_e_insieme(con_enti):
    c, cesena, ausl = con_enti
    r = c.get(f"/api/immobili-pa/ente/{cesena}")
    assert r.status_code == 200
    _niente_segreti(r.text)
    e = r.json()["enti"][0]
    assert e["nome"] == "COMUNE DI CESENA" and e["chiave"] == cesena and e["gruppo"] == "C"
    assert e["totali_dichiarati"]["n_beni"] == 3 and e["totali"]["n_fabbricati"] == 2 and e["totali"]["n_terreni"] == 1
    assert e["totali"]["sup_fabbricati_mq"] == 1200 and e["totali"]["n_particelle"] == 2
    assert e["comuni"][0]["comune"] == "Cesena" and e["riquadro"][0] < e["riquadro"][2]
    # solo fabbricati
    e = c.get(f"/api/immobili-pa/ente/{cesena}", params={"natura": "E"}).json()["enti"][0]
    assert e["totali"]["n_beni"] == 2 and e["totali"]["n_terreni"] == 0
    # due enti: il bene 2 (del Comune, in uso all'AUSL) conta una volta
    d = c.get(f"/api/immobili-pa/ente/{cesena},{ausl}", params={"natura": "E"}).json()
    assert [x["nome"] for x in d["enti"]] == ["COMUNE DI CESENA", "AZIENDA USL DELLA ROMAGNA"]
    assert d["enti"][1]["totali"]["n_beni"] == 2 and d["enti"][1]["totali"]["n_detenzione"] == 1
    assert d["insieme"]["n_beni"] == 3 and d["insieme"]["sup_fabbricati_mq"] == 1000 + 200 + 9000
    assert d["insieme"]["n_detenzione"] == 0                    # il bene 2 è in proprietà del Comune, scelto insieme
    # solo in uso: l'AUSL ha il bene 2
    d = c.get(f"/api/immobili-pa/ente/{ausl}", params={"ruolo": "uso"}).json()
    assert d["enti"][0]["totali"]["n_beni"] == 1
    # errori
    assert c.get("/api/immobili-pa/ente/0123456789").status_code == 404
    assert c.get("/api/immobili-pa/ente/xyz").status_code == 400
    assert c.get(f"/api/immobili-pa/ente/{','.join([cesena] * 9)}").status_code == 400
    assert c.get(f"/api/immobili-pa/ente/{cesena}", params={"ruolo": "affitto"}).status_code == 400
    assert c.get(f"/api/immobili-pa/ente/{cesena}", params={"natura": "X"}).status_code == 400


def test_ente_punti(con_enti):
    c, cesena, ausl = con_enti
    r = c.get(f"/api/immobili-pa/ente/{ausl}/punti")
    assert r.status_code == 200 and "max-age" in r.headers["cache-control"] and r.headers["etag"]
    _niente_segreti(r.text)
    d = r.json()
    assert d["campi"] == ["lon", "lat", "n", "natura", "ruolo", "ref"]
    refs = {x[5]: x for x in d["righe"]}
    assert len(refs) == 252 and refs["b4"][:2] == [12.25, 44.14] and refs["C573_001000.1"][4] == "U"
    assert c.get(f"/api/immobili-pa/ente/{ausl}/punti", headers={"If-None-Match": r.headers["etag"]}).status_code == 304
    assert c.get("/api/immobili-pa/ente/0123456789/punti").status_code == 404


def test_ente_beni_paginazione_e_ordinamento(con_enti):
    c, cesena, ausl = con_enti
    r = c.get(f"/api/immobili-pa/ente/{cesena}/beni")
    _niente_segreti(r.text)
    d = r.json()
    assert d["totale"] == 2 and d["pagine"] == 1
    prima = d["righe"][0]
    assert prima["ref"] == "C573_001000.1" and prima["n_beni"] == 2 and prima["comune"] == "Cesena"
    assert prima["indirizzo"] == "Via Roma 3" and "Edificio scolastico" in prima["tipologie"] and prima["sup_mq"] == 1200
    # paginazione: 252 righe dell'AUSL, al massimo 200 per pagina
    d = c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"per_pagina": 500}).json()
    assert d["per_pagina"] == 200 and d["totale"] == 252 and d["pagine"] == 2 and len(d["righe"]) == 200
    d2 = c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"per_pagina": 500, "pagina": 2}).json()
    assert len(d2["righe"]) == 52 and not {x["ref"] for x in d["righe"]} & {x["ref"] for x in d2["righe"]}
    # ordinamento su lista chiusa
    d = c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"ordina": "sup_mq", "verso": "desc", "per_pagina": 3}).json()
    assert [x["sup_mq"] for x in d["righe"]] == [9000, 349, 348]
    d = c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"ordina": "indirizzo", "per_pagina": 2}).json()
    assert d["righe"][0]["indirizzo"] == "Via Roma"          # vuoti in fondo
    assert c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"ordina": "id_bene; DROP TABLE beni"}).status_code == 400
    assert c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"verso": "giu"}).status_code == 400
    # filtri
    d = c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"natura": "E"}).json()
    assert d["totale"] == 2 and {x["ref"] for x in d["righe"]} == {"C573_001000.1", "b4"}
    d = c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"natura": "E", "ruolo": "proprieta"}).json()
    assert [x["ref"] for x in d["righe"]] == ["b4"] and d["righe"][0]["ruoli"] == "P"
    assert c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"comune": "C573"}).json()["totale"] == 252
    assert c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"comune": "D704"}).json()["totale"] == 0
    assert c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"regione": "EMILIA ROMAGNA"}).json()["totale"] == 252
    assert c.get(f"/api/immobili-pa/ente/{ausl}/beni", params={"comune": "x'"}).status_code == 400
    assert c.get("/api/immobili-pa/ente/0123456789/beni").status_code == 404


def test_bene_con_piu_dichiarazioni_e_chiave_ente(con_enti):
    c, cesena, ausl = con_enti
    r = c.get("/api/immobili-pa/bene/2")
    _niente_segreti(r.text)
    d = r.json()
    assert len(d["dichiarazioni"]) == 2 and d["bene"] == d["dichiarazioni"][0]
    assert {x["ente_chiave"] for x in d["dichiarazioni"]} == {cesena, ausl}
    assert {x.get("titolo_detenzione", "") for x in d["dichiarazioni"]} == {"", "in uso gratuito"}
    p = c.get("/api/immobili-pa/particella/C573_001000.1")
    _niente_segreti(p.text)
    assert len(p.json()["beni"]) == 3 and all("ente" not in b for b in p.json()["beni"])
    r = c.get("/api/immobili-pa/cerca", params={"q": "cesena scolastico"})
    _niente_segreti(r.text)


def test_scheda_con_tutti_i_campi_pubblicabili(con_enti):
    """Scheda in sovraimpressione (22/11/2026 sera): ruolo, superficie di riferimento, sistema catastale e classificazione
    e sede dell'ente dichiarante; mai CF né cedente."""
    c, cesena, ausl = con_enti
    r = c.get("/api/immobili-pa/bene/2")
    _niente_segreti(r.text)
    per = {x["ente_chiave"]: x for x in r.json()["dichiarazioni"]}
    assert per[cesena]["ruolo"] == "P" and per[ausl]["ruolo"] == "U"
    assert per[cesena]["sup_riferimento_mq"] == 200.0
    assert per[cesena]["ente_settore"] == "S13" and per[cesena]["ente_macrocategoria"] == "Amministrazioni Locali"
    assert per[ausl]["ente_sede"] == {"comune": "RAVENNA", "provincia": "RA", "regione": "EMILIA ROMAGNA"}
    p = c.get("/api/immobili-pa/particella/C573_001000.1")
    _niente_segreti(p.text)
    assert {b["ruolo"] for b in p.json()["beni"]} == {"P", "U"}
    assert all(b.get("ente_chiave") and b.get("ente_sede") for b in p.json()["beni"])
    assert not set(I.CAMPI_BENE) & set(I.ESCLUSE)


def test_ente_con_indice_vecchio(client):
    """Indice di prima del 22/11/2026 (senza tabella enti): le rotte nuove rispondono «non disponibile»."""
    c, d = client
    _indice(d / "immobili_pa_2023.sqlite")
    for u in ("/api/immobili-pa/ente/0123456789", "/api/immobili-pa/ente/0123456789/punti",
              "/api/immobili-pa/ente/0123456789/beni"):
        r = c.get(u)
        assert r.status_code == 200 and r.json() == {"disponibile": False}, u
    assert len(c.get("/api/immobili-pa/bene/2").json()["dichiarazioni"]) == 1


def test_ente_limite_e_tetto(con_enti, monkeypatch):
    c, cesena, ausl = con_enti
    monkeypatch.setitem(P.LIMITI, "immobili_pa_ente", (4, 3600))
    assert c.get(f"/api/immobili-pa/ente/{ausl}/punti").status_code == 200        # pesa 3
    assert c.get(f"/api/immobili-pa/ente/{ausl}").status_code == 200
    r = c.get(f"/api/immobili-pa/ente/{ausl}/beni")
    assert r.status_code == 429 and r.headers["x-eugenio-limite"] == "immobili_pa_ente"
    P.limiti.clear()
    monkeypatch.setitem(P.LIMITI, "immobili_pa_ente", (100, 3600))
    monkeypatch.setattr(C, "IMMOBILI_PA_ENTE_TETTO_ORA", 1)
    assert c.get(f"/api/immobili-pa/ente/{ausl}").status_code == 200
    assert c.get(f"/api/immobili-pa/ente/{ausl}").status_code == 503
