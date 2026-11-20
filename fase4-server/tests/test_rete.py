"""«Stato della rete elettrica» e «Cabine primarie» (17/11/2026, servizio/rete.py): regola della criticità, raccolta
delle interruzioni, saturazione notturna, tabella di raccordo e rotte /api/rete/….

  cd fase4-server && python -m pytest tests/test_rete.py -q
Niente rete: e-distribuzione (ArcGIS, gettone, comuniServiti) è sostituita da un httpx.MockTransport."""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from servizio import config as C, protezione as P, rete as R  # noqa: E402

ROMA = R.ROMA
T0 = dt.datetime(2026, 11, 17, 18, 2, tzinfo=ROMA)


# ---------------------------------------------------------------------------------------------- regola del contratto
@pytest.mark.parametrize("conteggi, atteso", [
    ({}, {"livello": None, "quota": None, "pieno": None, "strisce": None}),
    ({"VERDE": 0, "ROSSO": 0}, {"livello": None, "quota": None, "pieno": None, "strisce": None}),
    ({"VERDE": 3}, {"livello": "VERDE", "quota": 1.0, "pieno": None, "strisce": None}),
    ({"VERDE": 1, "GIALLO": 2}, {"livello": "GIALLO", "quota": 0.667, "pieno": "GIALLO", "strisce": None}),
    ({"VERDE": 3, "GIALLO": 1}, {"livello": "GIALLO", "quota": 0.25, "pieno": None, "strisce": ["VERDE", "GIALLO"]}),
    ({"GIALLO": 2, "ARANCIONE": 1}, {"livello": "ARANCIONE", "quota": 0.333, "pieno": None,
                                     "strisce": ["GIALLO", "ARANCIONE"]}),
    ({"VERDE": 2, "ROSSO": 3}, {"livello": "ROSSO", "quota": 0.6, "pieno": "ROSSO", "strisce": None}),
    ({"ARANCIONE": 3, "ROSSO": 2}, {"livello": "ROSSO", "quota": 0.4, "pieno": None, "strisce": ["ARANCIONE", "ROSSO"]}),
    ({"GIALLO": 1, "ROSSO": 1}, {"livello": "ROSSO", "quota": 0.5, "pieno": None, "strisce": ["ARANCIONE", "ROSSO"]}),
    ({"rosso": 1, "Verde": 0, "BLU": 7}, {"livello": "ROSSO", "quota": 1.0, "pieno": "ROSSO", "strisce": None}),
])
def test_classe_comune(conteggi, atteso):
    assert R.classe_comune(conteggi) == atteso


def test_livello_cabina_e_date():
    assert R.livello_cabina({"VERDE": 2, "GIALLO": 0}) == "VERDE"
    assert R.livello_cabina({"VERDE": 2, "ARANCIONE": 1, "GIALLO": 5}) == "ARANCIONE"
    assert R.livello_cabina({}) is None and R.livello_cabina(None) is None
    assert R.data_it("17/11/2026 14:00") == "2026-11-17T14:00:00+01:00"
    assert R.data_it("17/07/2026 14:00") == "2026-07-17T14:00:00+02:00"     # ora legale
    assert R.data_it("In corso di definizione") is None and R.data_it(None) is None
    assert R.NOTA_DURATA.startswith("Durata stimata")
    assert C.RETE_PAUSA_S >= 4


# ---------------------------------------------------------------------------------------------- interruzioni
def riga(id_, cs, comune, n, inizio="17/11/2026 14:00", prev="17/11/2026 20:00", causa="Guasto", codice="GM",
         lat=44.1, lon=12.2):
    return {"id_interruzione": id_, "cod_cs": cs, "comune": comune, "num_cli_disalim": n, "data_interruzione": inizio,
            "data_prev_ripristino": prev, "causa_disalimentazione": causa, "causa_interruzione": codice,
            "latitudine": lat, "longitudine": lon, "provincia": "Rimini", "regione": "Nord-est",
            "descrizione_territoriale": f"zona {id_}", "dataultimoaggiornamento": "17/11/2026 18:01", "cft": "D000X",
            "note": ""}


def trasporto_interruzioni(fonte: dict):
    """Strato ArcGIS finto a pagine di 2 righe; fonte["righe"] si cambia tra una lettura e l'altra."""
    def h(req: httpx.Request) -> httpx.Response:
        if fonte.get("guasto"):
            return httpx.Response(500)
        q = {k: v[0] for k, v in parse_qs(urlsplit(str(req.url)).query).items()}
        assert "ITA_power_cut_map_layer_View" in str(req.url) and q["returnGeometry"] == "false"
        off = int(q["resultOffset"])
        pag = fonte["righe"][off:off + 2]
        fonte["pagine"] = fonte.get("pagine", 0) + 1
        return httpx.Response(200, json={"features": [{"attributes": r} for r in pag],
                                         "exceededTransferLimit": off + 2 < len(fonte["righe"])})
    return h


@pytest.fixture
def db_vuoto(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RETE_DB", tmp_path / "rete" / "rete.sqlite")
    monkeypatch.setattr(C, "RETE_RACCORDO", tmp_path / "rete" / "raccordo_cp.csv")
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    R._cache.clear()
    return C.RETE_DB


def test_raccolta_interruzioni(db_vuoto):
    fonte = {"righe": [riga(1, "CS1", 99014, 10), riga(1, "CS2", 99014, 5, lat=44.2), riga(1, "CS3", 99013, 30),
                       riga(2, "CS9", 37006, 4, causa="Lavoro Programmato", codice="LV", prev="In corso di definizione"),
                       riga(3, "CS7", 37006, 1)]}
    cl = httpx.Client(transport=httpx.MockTransport(trasporto_interruzioni(fonte)))
    e = R.raccogli_interruzioni(cl, T0)
    assert e == {**e, "esito": "ok", "righe": 5, "interruzioni": 3, "nuove": 3, "chiuse": 0}
    assert fonte["pagine"] == 3                          # paginazione: 2 + 2 + 1
    db = R.connetti(db_vuoto, scrittura=False)
    i1 = db.execute("SELECT * FROM interruzioni WHERE id_interruzione=1").fetchone()
    assert i1["num_cli_disalim"] == 45 and i1["n_cs"] == 3 and i1["comuni"] == "099013;099014"
    assert i1["comune"] == "099013" and i1["data_interruzione"] == "2026-11-17T14:00:00+01:00"
    assert i1["data_prev_ripristino"] == "2026-11-17T20:00:00+01:00" and i1["chiusa_il"] is None
    i2 = db.execute("SELECT * FROM interruzioni WHERE id_interruzione=2").fetchone()
    assert i2["data_prev_ripristino"] is None and i2["prev_ripristino_testo"] == "In corso di definizione"
    assert db.execute("PRAGMA user_version").fetchone()[0] == R.SCHEMA_VERSIONE
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    db.close()

    # seconda lettura: la 3 sparisce (chiusa), la 1 ha meno clienti (resta il massimo), la 4 è nuova
    fonte["righe"] = [riga(1, "CS1", 99014, 2), riga(2, "CS9", 37006, 6, causa="Lavoro Programmato", codice="LV"),
                      riga(4, "CS5", 99014, 8, inizio="17/11/2026 18:10")]
    t1 = T0 + dt.timedelta(minutes=15)
    e = R.raccogli_interruzioni(cl, t1)
    assert (e["nuove"], e["chiuse"]) == (1, 1)
    db = R.connetti(db_vuoto, scrittura=False)
    r = {x["id_interruzione"]: x for x in db.execute("SELECT * FROM interruzioni")}
    assert r[3]["chiusa_il"] == R.iso(t1) and r[3]["ultima_lettura"] == R.iso(T0)
    assert r[1]["num_cli_disalim"] == 45 and r[1]["ultima_lettura"] == R.iso(t1)
    assert db.execute("SELECT num_cli_disalim FROM interruzioni_cs WHERE id_interruzione=1 AND cod_cs='CS1'"
                      ).fetchone()[0] == 10
    assert r[2]["num_cli_disalim"] == 6 and r[2]["data_prev_ripristino"] == "2026-11-17T20:00:00+01:00"
    db.close()

    # la 3 ricompare (la fonte aveva saltato una lettura): si riapre
    fonte["righe"].append(riga(3, "CS7", 37006, 1))
    R.raccogli_interruzioni(cl, t1 + dt.timedelta(minutes=15))
    db = R.connetti(db_vuoto, scrittura=False)
    assert db.execute("SELECT chiusa_il FROM interruzioni WHERE id_interruzione=3").fetchone()[0] is None
    db.close()


def test_interruzioni_lettura_vuota_sospetta_e_errore(db_vuoto):
    fonte = {"righe": [riga(k, f"CS{k}", 99014, 1) for k in range(1, 13)]}
    cl = httpx.Client(transport=httpx.MockTransport(trasporto_interruzioni(fonte)))
    R.raccogli_interruzioni(cl, T0)
    fonte["righe"] = []
    e = R.raccogli_interruzioni(cl, T0 + dt.timedelta(minutes=15))
    assert e["esito"] == "sospetta" and e["chiuse"] == 0
    fonte["guasto"] = True
    with pytest.raises(httpx.HTTPStatusError):
        R.raccogli_interruzioni(cl, T0 + dt.timedelta(minutes=30))
    db = R.connetti(db_vuoto, scrittura=False)
    esiti = [r[0] for r in db.execute("SELECT esito FROM letture ORDER BY quando")]
    assert esiti == ["ok", "sospetta", "errore"]
    assert db.execute("SELECT COUNT(*) FROM interruzioni WHERE chiusa_il IS NULL").fetchone()[0] == 12
    assert db.execute("SELECT valore FROM meta WHERE chiave='interruzioni_aggiornate'").fetchone()[0] == R.iso(T0)
    db.close()


# ---------------------------------------------------------------------------------------------- saturazione
def trasf(cp, nome, tr, liv, sez="271"):
    return {"CodCabinaPrimaria": cp, "NomeCabinaPrimaria": nome, "CodTrasformatore": tr, "CodiceMontante": "71",
            "IdSezioneATMT": sez, "LivSaturTraformatore": liv}


SERVITI = {
    "099": [{"CodiceIstat": "099014", "Descrizione": "RIMINI", "ElencoTrasformatori": [
                trasf("DV001", "RIMINI NORD", "01", "ROSSO"), trasf("DV001", "RIMINI NORD", "01", "ROSSO", sez="272"),
                trasf("DV001", "RIMINI NORD", "02", "GIALLO"), trasf("DV002", "RIMINI SUD", "01", "VERDE"),
                trasf("DV002", "RIMINI SUD", "02", "VERDE")]},
            {"CodiceIstat": "099013", "Descrizione": "RICCIONE", "ElencoTrasformatori": [
                trasf("DV002", "RIMINI SUD", "01", "VERDE")]}],
    "037": [{"CodiceIstat": "037006", "Descrizione": "BOLOGNA", "ElencoTrasformatori": [
                trasf("DE003", "BOLOGNA EST", "01", "ARANCIONE"), trasf("DE003", "BOLOGNA EST", "02", "ARANCIONE")]}],
}
PROVINCE = [{"cod_pro": 1, "f1": 1, "f2": "Piemonte", "f4": "Torino"},
            {"cod_pro": 37, "f1": 8, "f2": "Emilia-Romagna", "f4": "Bologna"},
            {"cod_pro": 99, "f1": 8, "f2": "Emilia-Romagna", "f4": "Rimini"}]
COMUNI_ED = [{"pro_com_t": "099014", "pro_com": 99014, "comune": "Rimini", "cod_prov": 99, "cod_reg": 8, "servitoed": 1},
             {"pro_com_t": "037006", "pro_com": 37006, "comune": "Bologna", "cod_prov": 37, "cod_reg": 8, "servitoed": 1},
             {"pro_com_t": "099013", "pro_com": 99013, "comune": "Riccione", "cod_prov": 99, "cod_reg": 8, "servitoed": 0},
             {"pro_com_t": "021008", "pro_com": 21008, "comune": "Bolzano", "cod_prov": 21, "cod_reg": 4, "servitoed": 0},
             {"pro_com_t": "037099", "pro_com": 37099, "comune": "Vecchio Fuso", "cod_prov": 37, "cod_reg": 8,
              "servitoed": 0},
             {"pro_com_t": " ", "pro_com": 0, "comune": " ", "cod_prov": 0, "cod_reg": 0, "servitoed": 1}]


def trasporto_saturazione(stato: dict):
    stato.setdefault("chiamate", [])
    stato.setdefault("gettoni", 0)

    def h(req: httpx.Request) -> httpx.Response:
        u = str(req.url)
        if req.method == "GET" and "aree-critiche" in u:
            return httpx.Response(200, text="<html></html>")
        if "ProvinceCritiche" in u or "View_ComuniGestiti" in u:
            q = {k: v[0] for k, v in parse_qs(urlsplit(u).query).items()}
            dati = PROVINCE if "ProvinceCritiche" in u else COMUNI_ED
            off = int(q["resultOffset"])
            return httpx.Response(200, json={"features": [{"attributes": r} for r in dati[off:off + 4]],
                                             "exceededTransferLimit": off + 4 < len(dati)})
        if "tokenservice" in u:
            if req.headers.get("origin") != "https://www.e-distribuzione.it" or "aree-critiche" not in req.headers.get(
                    "referer", ""):
                return httpx.Response(500)
            corpo = json.loads(req.content)
            assert corpo["service"] == "areecritiche" and corpo["data"].startswith("DataRichiesta:")
            stato["gettoni"] += 1
            return httpx.Response(200, json={"responseCode": "0",
                                             "responseData": {"token": f"GETTONE-SEGRETO-{stato['gettoni']}"}})
        if "comuniServiti" in u:
            corpo = json.loads(req.content)
            assert corpo["Token"] == f"GETTONE-SEGRETO-{stato['gettoni']}"     # un gettone nuovo per ogni chiamata
            stato["chiamate"].append(corpo["Provincia"])
            if corpo["Provincia"] == "001":
                return httpx.Response(500, text=f"errore interno {corpo['Token']}")
            return httpx.Response(200, json={"CodiceEsito": "0", "DescrizioneEsito": "OK",
                                             "Provincia": corpo["Provincia"],
                                             "ElencoComuni": SERVITI.get(corpo["Provincia"], [])})
        return httpx.Response(404)
    return h


def comuni_parquet(cartella: Path):
    import pandas as pd
    cartella.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"istat": ["099014", "099013", "037006", "037007", "021008", "001272"],
                  "nome": ["Rimini", "Riccione", "Bologna", "Nuovo Fuso", "Bolzano", "Torino"],
                  "regione_cod": ["08", "08", "08", "08", "04", "01"]}).to_parquet(cartella / "comuni.parquet")


@pytest.fixture
def saturato(db_vuoto, monkeypatch, caplog):
    pytest.importorskip("pyarrow")
    comuni_parquet(C.DATI)
    monkeypatch.setattr(R, "MIN_COMUNI_ED", 2)
    pause = []
    monkeypatch.setattr(R.time, "sleep", lambda s: pause.append(s))
    stato = {}
    cl = httpx.Client(headers=R.INTESTAZIONI, transport=httpx.MockTransport(trasporto_saturazione(stato)))
    caplog.set_level(logging.DEBUG)
    esito = R.aggiorna_saturazione(cl, pausa=4, ora=T0)
    return {"esito": esito, "stato": stato, "pause": pause, "cl": cl, "log": caplog}


def test_saturazione_notturna(saturato, db_vuoto):
    e, st = saturato["esito"], saturato["stato"]
    assert e["ok"] == 2 and list(e["falliti"]) == ["001"] and e["comuni_ed"] == 5
    assert st["chiamate"].count("001") == 3            # primo giro + 2 ripassi
    assert min(saturato["pause"]) >= 4 and 15 in saturato["pause"]
    testo_log = saturato["log"].text
    assert "GETTONE-SEGRETO" not in testo_log and "GETTONE-SEGRETO" not in json.dumps(e)
    assert b"GETTONE-SEGRETO" not in db_vuoto.read_bytes()
    db = R.connetti(db_vuoto, scrittura=False)
    assert db.execute("SELECT COUNT(*) FROM saturazione WHERE mese='2026-11'").fetchone()[0] == 8
    t = db.execute("SELECT esito, errore, ultimo_ok FROM tentativi_province WHERE provincia='001'").fetchone()
    assert t["esito"] == "errore" and "HTTP 500" in t["errore"] and "GETTONE" not in t["errore"] and t["ultimo_ok"] is None
    # comune 2021 fuso dopo il 2021 e ritrovato per nome? «Vecchio Fuso» non c'è: codice attuale nullo
    ced = {r["istat_2021"]: r["istat"] for r in db.execute("SELECT * FROM comuni_ed")}
    assert ced["021008"] == "021008" and ced["037099"] is None and "000000" not in ced
    db.close()


def test_saturazione_una_fotografia_al_mese(saturato, db_vuoto):
    cl = saturato["cl"]
    SERVITI["037"][0]["ElencoTrasformatori"][0]["LivSaturTraformatore"] = "ROSSO"
    try:
        R.aggiorna_saturazione(cl, pausa=4, ora=T0 + dt.timedelta(days=1), ripassi=0)
        R.aggiorna_saturazione(cl, pausa=4, ora=dt.datetime(2026, 12, 1, 1, 15, tzinfo=ROMA), ripassi=0)
    finally:
        SERVITI["037"][0]["ElencoTrasformatori"][0]["LivSaturTraformatore"] = "ARANCIONE"
    db = R.connetti(db_vuoto, scrittura=False)
    mesi = dict(db.execute("SELECT mese, COUNT(*) FROM saturazione GROUP BY mese").fetchall())
    assert mesi == {"2026-11": 8, "2026-12": 8}
    assert db.execute("SELECT livello FROM saturazione WHERE mese='2026-11' AND comune='037006' AND cod_trasf='01'"
                      ).fetchone()[0] == "ROSSO"           # l'ultima lettura del mese sostituisce la prima
    db.close()


# ---------------------------------------------------------------------------------------------- rotte
RACCORDO = """cod_ac,gestore,cod_cp_ed,nome_cp_ed,comuni_serviti,osm_id,osm_nome,lat,lon,punteggio_nome,distanza_m,esito,data_raccordo,versione_ac
AC001E00001,e-distribuzione,DV001,RIMINI NORD,099014,way/1,Rimini Nord,44.07,12.56,0.95,120,sicuro,2026-11-17,AC_Comuni_2025
AC001E00002,e-distribuzione,DE003,BOLOGNA EST,037006,way/2,CP Bologna Est,44.49,11.38,0.8,300,da_verificare,2026-11-17,AC_Comuni_2025
AC002A00001,Altro Distributore,,,021008,way/3,Bolzano Sud,46.48,11.33,,,solo_gse,2026-11-17,AC_Comuni_2025
"""


@pytest.fixture
def api(saturato, monkeypatch):
    C.RETE_RACCORDO.write_text(RACCORDO, encoding="utf-8")
    fonte = {"righe": [riga(1, "CS1", 99014, 10, lat=44.06, lon=12.57), riga(1, "CS2", 99013, 5),
                       riga(2, "CS9", 37006, 4, causa="Lavoro Programmato", codice="LV", lat=44.5, lon=11.34)]}
    cl = httpx.Client(transport=httpx.MockTransport(trasporto_interruzioni(fonte)))
    R.raccogli_interruzioni(cl, T0)
    fonte["righe"] = fonte["righe"][2:]                  # la 1 si chiude
    R.raccogli_interruzioni(cl, T0 + dt.timedelta(minutes=15))
    fonte["righe"].append(riga(5, "CS4", 99014, 7, inizio="17/11/2026 18:20", lat=44.05, lon=12.6))
    R.raccogli_interruzioni(cl, T0 + dt.timedelta(minutes=30))
    monkeypatch.setattr(R, "adesso", lambda: T0 + dt.timedelta(minutes=40))
    P.limiti.clear()
    app = FastAPI()
    app.include_router(R.router)
    yield TestClient(app)
    P.limiti.clear()


def test_rotta_stato(api):
    r = api.get("/api/rete/stato")
    assert r.status_code == 200 and r.headers["cache-control"] == "public, max-age=60"
    j = r.json()
    assert j["province_mancanti"] == ["001"] and j["attive"] == 2
    assert j["saturazione_aggiornata"] == R.iso(T0) and j["interruzioni_aggiornate"] == R.iso(T0 + dt.timedelta(minutes=30))
    assert j["raccolta_dal"] == R.iso(T0) and j["raccordo"]["righe"] == 3 and j["raccordo"]["con_posizione"] == 3
    assert "ODbL" in j["licenze"]["posizioni_cabine"]["licenza"] and "e-distribuzione" in j["licenze"]
    assert set(j["fonti"]) >= {"interruzioni", "saturazione", "comuni_gestiti"}


def test_rotta_cabine(api):
    r = api.get("/api/rete/cabine")
    assert r.status_code == 200 and r.headers["cache-control"] == "public, max-age=1800"
    g = r.json()
    assert g["type"] == "FeatureCollection" and "ODbL" in g["licenza"] and "OpenStreetMap" in g["attribuzione"]
    f = {x["properties"]["cod_ac"]: x for x in g["features"]}
    assert set(f) == {"AC001E00001", "AC001E00002", "AC002A00001"}
    assert g["senza_posizione"] == 1                     # DV002 senza riga di raccordo
    p = f["AC001E00001"]["properties"]
    assert f["AC001E00001"]["geometry"]["coordinates"] == [12.56, 44.07]
    assert p["livello"] == "ROSSO" and p["trasf"] == {"VERDE": 0, "GIALLO": 1, "ARANCIONE": 0, "ROSSO": 1}
    assert p["cod_cp_ed"] == "DV001" and p["data_saturazione"] == R.iso(T0) and p["gestore"] == "e-distribuzione"
    altro = f["AC002A00001"]["properties"]
    assert altro["livello"] is None and altro["gestore"] == "Altro Distributore"     # grigio
    assert all("rings" not in json.dumps(x["geometry"]) and x["geometry"]["type"] == "Point" for x in g["features"])
    r8 = api.get("/api/rete/cabine?regione=8").json()
    assert {x["properties"]["cod_ac"] for x in r8["features"]} == {"AC001E00001", "AC001E00002"}
    assert api.get("/api/rete/cabine?regione=04").json()["features"][0]["properties"]["cod_ac"] == "AC002A00001"
    assert api.get("/api/rete/cabine?regione=99").status_code == 422


def test_rotta_comuni(api):
    r = api.get("/api/rete/comuni?regione=08")
    assert r.status_code == 200
    c = {x["istat"]: x for x in r.json()}
    assert set(c) == {"099014", "099013", "037006", "037007"}
    rim = c["099014"]
    # trasformatori distinti: DV001/01 ROSSO (due sezioni, contato una volta), DV001/02 GIALLO, DV002/01 e /02 VERDE
    assert rim["trasf"] == {"VERDE": 2, "GIALLO": 1, "ARANCIONE": 0, "ROSSO": 1}
    assert (rim["livello"], rim["quota"], rim["pieno"], rim["strisce"]) == ("ROSSO", 0.25, None, ["ARANCIONE", "ROSSO"])
    assert rim["cabine"] == ["DV001", "DV002"] and rim["concessionario"] and rim["dato_disponibile"]
    assert c["037006"]["pieno"] == "ARANCIONE" and c["099013"]["livello"] == "VERDE"
    assert c["099013"]["pieno"] is None and c["099013"]["strisce"] is None
    # servitoed = 0 ma con trasformatori e-distribuzione: concessionario, colore della criticità, servito in parte
    assert c["099013"]["concessionario"] and c["099013"]["servito_in_parte"] and c["099013"]["dato_disponibile"]
    assert not rim["servito_in_parte"] and not c["037007"]["servito_in_parte"]
    assert c["037007"]["livello"] is None and c["037007"]["concessionario"]
    bz = {x["istat"]: x for x in api.get("/api/rete/comuni?regione=4").json()}
    assert bz["021008"]["concessionario"] is False and bz["021008"]["dato_disponibile"] is False
    assert bz["021008"]["servito_in_parte"] is False
    to = {x["istat"]: x for x in api.get("/api/rete/comuni?regione=01").json()}
    assert to["001272"]["concessionario"] and not to["001272"]["dato_disponibile"]    # Torino: dato non disponibile


def test_rotta_cabine_comune(api):
    j = api.get("/api/rete/cabine/comune/099014").json()
    assert j["concessionario"] and j["criticita"]["livello"] == "ROSSO" and j["nome"] == "Rimini"
    cab = {c["cod_cp_ed"]: c for c in j["cabine"]}
    assert set(cab) == {"DV001", "DV002"}
    assert cab["DV001"]["cod_ac"] == "AC001E00001" and cab["DV001"]["lat"] == 44.07
    assert cab["DV002"]["lat"] is None and cab["DV002"]["livello"] == "VERDE"
    t = {x["cod_trasf"]: x for x in cab["DV001"]["trasformatori_del_comune"]}
    assert t["01"]["livello"] == "ROSSO" and len(t["01"]["montanti"]) == 2
    ric = api.get("/api/rete/cabine/comune/099013").json()
    assert ric["concessionario"] and ric["servito_in_parte"] and ric["criticita"]["livello"] == "VERDE"
    assert not j["servito_in_parte"]
    bz = api.get("/api/rete/cabine/comune/021008").json()
    assert not bz["concessionario"] and [c["cod_ac"] for c in bz["cabine"]] == ["AC002A00001"]
    assert api.get("/api/rete/cabine/comune/99014").status_code == 422


def test_rotta_interruzioni_attive(api):
    r = api.get("/api/rete/interruzioni/attive")
    assert r.status_code == 200 and r.headers["cache-control"] == "public, max-age=120"
    g = r.json()
    p = {x["properties"]["id"]: x["properties"] for x in g["features"]}
    assert set(p) == {2, 5} and g["attribuzione"] == R.FONTE_ED and g["nota_durata"].startswith("Durata stimata")
    assert p[5]["inizio"] == "2026-11-17T18:20:00+01:00" and p[5]["durata_finora_min"] == 22   # 18:42 − 18:20
    assert p[2]["causa"] == "Lavoro Programmato" and p[2]["clienti"] == 4 and p[2]["attiva"]
    assert p[5]["nome_comune"] == "Rimini" and p[2]["nome_comune"] == "Bologna"
    assert {x["properties"]["id"] for x in api.get("/api/rete/interruzioni/attive?regione=08").json()["features"]} \
        == {2, 5}
    assert api.get("/api/rete/interruzioni/attive?regione=01").json()["features"] == []
    bb = api.get("/api/rete/interruzioni/attive?bbox=12.0,43.9,12.8,44.3").json()
    assert [x["properties"]["id"] for x in bb["features"]] == [5]
    assert api.get("/api/rete/interruzioni/attive?bbox=1,2,3").status_code == 422


def test_rotta_interruzioni_comune(api):
    j = api.get("/api/rete/interruzioni/comune/099014").json()
    assert j["dal"] == R.iso(T0) and j["nome"] == "Rimini"
    # 1 (chiusa: ultima lettura 18:02 − inizio 14:00 = 242 min, 10 clienti nel comune) e 5 (attiva, 7 clienti)
    assert j["totale"] == {"n": 2, "guasti": 2, "programmati": 0, "clienti": 17, "durata_media_min": 242,
                           "durata_max_min": 242, "attive": 1}
    assert j["per_mese"] == [{"mese": "2026-11", "n": 2, "guasti": 2, "programmati": 0, "clienti": 17,
                              "durata_media_min": 242, "durata_max_min": 242}]
    assert j["per_causa"] == {"Guasto": 2} and [a["id"] for a in j["attive"]] == [5]
    assert [u["id"] for u in j["ultime"]] == [5, 1] and j["ultime"][1]["durata_min"] == 242
    assert j["ultime"][1]["chiusa_il"] == R.iso(T0 + dt.timedelta(minutes=15))
    assert api.get("/api/rete/interruzioni/comune/099014?da=2026-12").json()["totale"]["n"] == 0
    assert api.get("/api/rete/interruzioni/comune/099014?da=2026-11&a=2026-11").json()["totale"]["n"] == 2
    assert api.get("/api/rete/interruzioni/comune/099014?da=2026-13").status_code == 422
    vuoto = api.get("/api/rete/interruzioni/comune/001272").json()
    assert vuoto["totale"]["n"] == 0 and vuoto["per_mese"] == [] and vuoto["totale"]["durata_media_min"] is None


def test_rotte_senza_database_e_limite(db_vuoto, monkeypatch):
    P.limiti.clear()
    app = FastAPI()
    app.include_router(R.router)
    t = TestClient(app)
    for u in ("/api/rete/cabine", "/api/rete/comuni?regione=08", "/api/rete/interruzioni/attive",
              "/api/rete/interruzioni/comune/099014", "/api/rete/cabine/comune/099014"):
        assert t.get(u).status_code == 503, u
    assert not db_vuoto.exists()                          # le rotte non creano il database
    j = t.get("/api/rete/stato").json()
    assert j["saturazione_aggiornata"] is None and j["raccordo"]["righe"] == 0
    monkeypatch.setattr(C, "RETE_ORA", 2)
    P.limiti.clear()
    assert [t.get("/api/rete/stato").status_code for _ in range(3)] == [200, 200, 429]
    P.limiti.clear()


# ---------------------------------------------------------------------------------------------- servizio del GSE (20/11/2026)
def _gse(risposta):
    viste = []

    def gestore(req: httpx.Request) -> httpx.Response:
        viste.append(req)
        return risposta(req) if callable(risposta) else risposta
    return httpx.Client(transport=httpx.MockTransport(gestore)), viste


def test_controllo_servizio_gse_risponde():
    cl, viste = _gse(httpx.Response(200, json={"currentVersion": 11.5, "layers": [
        {"id": 0, "name": "AC_2025"}, {"id": 2, "name": "Comuni"}, {"id": 5, "name": "Aree modificate 2025"}]}))
    e = R.controlla_servizio_gse(cl)
    assert e == {"ok": True, "servizio": R.URL_GSE_AREE, "strato_0": "AC_2025", "strati": 3}
    # una sola richiesta, alla descrizione del FeatureServer con f=json: nessuna query delle aree
    assert len(viste) == 1 and str(viste[0].url) == R.URL_GSE_AREE + "?f=json"
    assert R.URL_GSE_AREE.endswith("/AC_Comuni_2025/FeatureServer") and "/query" not in str(viste[0].url)


@pytest.mark.parametrize("risposta, testo", [
    (httpx.Response(503, text="non disponibile"), "HTTP 503"),
    (httpx.Response(200, text="<html>pagina</html>"), "non JSON"),
    (httpx.Response(200, json={"error": {"code": 400, "message": "Invalid URL"}}), "Invalid URL"),
    (httpx.Response(200, json={"layers": [{"id": 1, "name": "Altro"}]}), "strato 0"),
])
def test_controllo_servizio_gse_non_risponde(risposta, testo):
    cl, _ = _gse(risposta)
    with pytest.raises(RuntimeError, match=testo):
        R.controlla_servizio_gse(cl)


def test_controllo_servizio_gse_rete_assente():
    def guasto(req):
        raise httpx.ConnectError("nessuna rete", request=req)
    cl, _ = _gse(guasto)
    with pytest.raises(RuntimeError, match="non raggiungibile"):
        R.controlla_servizio_gse(cl)


def test_indirizzo_gse_uguale_nel_server_e_nel_browser():
    """Un solo indirizzo per lato: URL_GSE_AREE (server) e GSE.SERVIZIO di rete.js (browser) devono coincidere."""
    rete_js = (Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "rete.js").read_text(encoding="utf-8")
    import re
    m = re.search(r'const GSE_FS = "([^"]+)"', rete_js)
    assert m and m.group(1) == R.URL_GSE_AREE
    assert rete_js.count("services-eu1.arcgis.com") == 1
    py = Path(R.__file__).read_text(encoding="utf-8")
    assert py.count("services-eu1.arcgis.com") == 1
