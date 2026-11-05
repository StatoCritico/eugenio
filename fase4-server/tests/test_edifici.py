"""Prove delle rotte degli edifici 3D (servizio/edifici.py) e del report «edificio» (fase 10, Fase A).

Dati meteo sintetici: nessun archivio vero. Dalla cartella fase4-server: `python -m pytest tests`."""
from __future__ import annotations

import io
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import edifici as E, report as R, report_servizi as RS   # noqa: E402


def giornaliero_sintetico():
    d = pd.date_range("2024-07-01", "2025-06-30", freq="D")
    t = 14 - 10 * np.cos(2 * np.pi * (d.dayofyear - 20) / 365)
    return pd.DataFrame({"data": d.date, "t_media": t, "gg20": np.clip(20 - t, 0, None), "gc24": np.clip(t - 24, 0, None)})


def test_gradi_giorno_mensili():
    m = E.gradi_giorno_mensili(giornaliero_sintetico())
    assert len(m) == 12 and m[0]["mese"] == "2024-07"
    gen = next(x for x in m if x["mese"] == "2025-01")
    assert gen["giorni"] == 31 and gen["gg20"] > 300
    assert E.gradi_giorno_mensili(giornaliero_sintetico(), dal="2025-01", al="2025-03")[0]["mese"] == "2025-01"
    assert E.gradi_giorno_mensili(pd.DataFrame()) == []


def test_anno_orario_sceglie_anno_completo():
    t = pd.date_range("2023-01-01", "2024-12-31 23:00", freq="h", tz="UTC")
    o = pd.DataFrame({"time": t, "shortwave_radiation": 100.0, "diffuse_radiation": 40.0, "temperature_2m": 12.0,
                      "wind_speed_10m": 5.0})
    a, d = E.anno_orario(o, 2030)
    assert a == 2024 and len(d) == 8784
    a, d = E.anno_orario(o, 2023)
    assert a == 2023
    with pytest.raises(ValueError):
        E.anno_orario(o.iloc[:100], None)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    finti = {"meteo_storico": {"VARIABILI": []}, "meteo_storico.aggrega": {"giornaliero": None},
             "meteo_storico.correzione": {"applica": None}, "meteo_storico.limiti": {"Limitatore": object},
             "meteo_storico.scarica": {"FONTI": {}, "client": None, "richiesta": None}}
    salvati = {k: sys.modules.get(k) for k in finti}
    for nome, attr in finti.items():
        if nome not in sys.modules:
            m = types.ModuleType(nome)
            m.__dict__.update(attr)
            sys.modules[nome] = m
    from servizio import app as A
    A._storia.clear()
    yield TestClient(A.app), A
    for k, v in salvati.items():
        if v is None:
            sys.modules.pop(k, None)


def test_rotte(client, monkeypatch):
    cl, A = client
    monkeypatch.setattr(A.meteo, "comuni", lambda: pd.DataFrame({"istat": ["099014"], "nome": ["Rimini"]}))
    monkeypatch.setattr(A.meteo, "storico_giornaliero", lambda istat: giornaliero_sintetico())
    r = cl.get("/api/edifici/gradi-giorno/099014")
    assert r.status_code == 200 and r.json()["comune"] == "Rimini" and len(r.json()["mesi"]) == 12
    assert cl.get("/api/edifici/gradi-giorno/000000").status_code == 404
    monkeypatch.setattr(A.meteo, "storico_orario", lambda istat: pd.DataFrame(columns=["time"]))
    r = cl.get("/api/edifici/clima-orario/099014")
    assert r.status_code == 503 and "non sono ancora sul server" in r.json()["detail"]

    def manca(istat):
        raise FileNotFoundError
    monkeypatch.setattr(A.meteo, "storico_giornaliero", manca)
    assert cl.get("/api/edifici/gradi-giorno/099014").status_code == 503


CORPO = {
    "titolo": "Edificio in 3D", "sintetico": True,
    "edificio": {"id": "E-DEMO", "nome": "Edificio dimostrativo", "comune": "Rimini"},
    "superfici": {"piani_fuori_terra": {"valore": 6, "fonte": "stima"}, "superficie_lorda": {"valore": 2468, "fonte": "stima"}},
    "geometria": {"volume_lordo": 10288, "s_su_v": 0.41, "pareti_per_orientamento": {"N": 300, "S": 280}},
    "corpi": [{"id": "C1", "area": 560, "gronda": 10, "tetto": "piano", "piani": 3, "licenza": "CC BY 4.0",
               "fonte_sagoma": "DBTR", "fonte_altezza": "DBTR H_uvl"}],
    "firma": {"base": 300, "pendenza": 9.0, "r2": 0.98, "unita": "Smc", "mesi": [{"mese": "2025-01", "consumo": 4170, "gg20": 430, "atteso": 4170}]},
    "consumi_normalizzati": [{"voce": "Gas per m² lordo", "valore": 9.4, "unita": "Smc/m²"}, {"voce": "PUN medio", "valore": 1, "unita": "€/MWh"}],
    "fv": {"aree": [{"nome": "Tetto C3", "area": 100, "inclinazione": 10, "orientamento": 180, "moduli": 40, "kwp": 17.2,
                     "kwh_anno": 21000, "perdita_ombre": 3.1}], "totale_kwh": 21000, "anno_clima": "2025"},
    "fonti": ["Dati sintetici di esempio (EuGEnio)"],
}


def leggi_pdf(b: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(b)).pages)


def test_report_edificio_pdf_e_fogli():
    doc = RS.report_edificio(CORPO, formato="pdf")
    t = leggi_pdf(R.genera(doc, "pdf"))
    assert "Dati sintetici di esempio" in t and "Firma energetica" in t and "Fotovoltaico sui tetti" in t
    assert "PUN" not in t                       # dati di mercato scartati
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(R.genera(RS.report_edificio(CORPO, formato="xlsx"), "xlsx")))
    testo = " ".join(str(c.value) for ws in wb for r in ws.iter_rows() for c in r if c.value is not None)
    assert "Tetto C3" in testo and "PUN" not in testo
    assert R.genera(RS.report_edificio(CORPO, formato="ods"), "ods")[:2] == b"PK"


def test_report_edificio_vuoto_non_fallisce():
    doc = RS.report_edificio({})
    assert R.genera(doc, "pdf")[:4] == b"%PDF"


# ---------------------------------------------------------------- Fase B (04/11/2026)
def _png_piccolo():
    import base64
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (40, 30), (120, 140, 90)).save(b, format="PNG")
    return base64.b64encode(b.getvalue()).decode()


CORPO_B = {**CORPO,
           "obblighi": {"intervento": "ristrutturazione importante di primo livello", "pubblico": True,
                        "righe": [{"voce": "Potenza minima FER sopra o dentro l'edificio P = k · S", "valore": "11,0 kW",
                                   "riferimento": "All. III, sez. B, punti 3 e 5"}]},
           "facciate": {"per_orientamento": [{"orientamento": "S", "area": 210, "kwh_m2": 1037, "kwh": 217770, "estate": 40000,
                                              "inverno": 23505, "perdita": 17.9}], "parti": 72, "orizzonte_lontano": True},
           "orizzonte_lontano": {"massimo": 2.1, "quota": 15, "raggio": 25, "fonte": "Copernicus"},
           "pvgis": {"aree": [{"id": "A1", "eugenio_kwh": 12000, "pvgis_kwh": 12381, "pvgis_senza_kwh": 12381,
                               "banca_dati": "PVGIS-SARAH3", "anni": [2005, 2023]}]},
           "priorita": {"pesi": {"intensita": 0.35}, "sedi": [{"posto": 1, "nome": "Scuola A", "punteggio": 80, "kwh_m2": 150,
                                                               "punteggi": {"intensita": 100}}]},
           "immagini_png": [{"titolo": "Vista", "png": None,
                             "ortofoto": {"id": "rer2023", "licenza": "CC BY 4.0", "citazione": "Regione Emilia-Romagna – Ortofoto RER 2023-24 (CC BY 4.0)",
                                          "scheda": "https://geoportale.regione.emilia-romagna.it/"}}]}


def test_report_edificio_fase_b():
    corpo = {**CORPO_B, "immagini_png": [{**CORPO_B["immagini_png"][0], "png": _png_piccolo()}]}
    doc = RS.report_edificio(corpo, formato="pdf")
    titoli = [s.titolo for s in doc.sezioni]
    for t in ("Obblighi di legge", "Sole sulle facciate", "Orizzonte lontano", "Confronto con PVGIS",
              "Classifica di priorità del patrimonio", "Figure"):
        assert t in titoli, t
    fig = next(s for s in doc.sezioni if s.titolo == "Figure").blocchi[0]
    assert "Ortofoto RER 2023-24" in fig.didascalia and "licenza CC BY 4.0" in fig.didascalia      # licenza e citazione
    assert any("Ortofoto" in f.testo for f in doc.fonti)
    t = leggi_pdf(R.genera(doc, "pdf"))
    assert "Allegato III" in t and "PVGIS" in t and "Scuola A" in t
    # senza citazione o da una fonte solo dal vivo la figura non entra
    senza = {**corpo, "immagini_png": [{**corpo["immagini_png"][0], "ortofoto": {"id": "rer2023", "licenza": "CC BY 4.0"}}]}
    assert "Figure" not in [s.titolo for s in RS.report_edificio(senza, formato="pdf").sezioni]
    pcn = {**corpo, "immagini_png": [{**corpo["immagini_png"][0], "ortofoto": {**corpo["immagini_png"][0]["ortofoto"], "id": "pcn2012"}}]}
    assert "Figure" not in [s.titolo for s in RS.report_edificio(pcn, formato="pdf").sezioni]
    # nei fogli niente immagini, ma le tabelle sì
    assert R.genera(RS.report_edificio(corpo, formato="xlsx"), "xlsx")[:2] == b"PK"


# ---------------------------------------------------------------- blocco 2 (05/11/2026): modello del cielo nel report
def test_report_edificio_dichiara_il_modello_del_cielo():
    import copy
    vecchio = leggi_pdf(R.genera(RS.report_edificio(CORPO, formato="pdf"), "pdf"))
    assert "trasposizione isotropa" in vecchio                     # pagine di prima: nessun campo modello_cielo
    c = copy.deepcopy(CORPO)
    c["fv"]["modello_cielo"] = "Perez (1990)"
    t = leggi_pdf(R.genera(RS.report_edificio(c, formato="pdf"), "pdf"))
    assert "trasposizione di Perez (1990)" in t and "isotropa" not in t
    assert RS._modello_cielo(None) == "isotropa" and RS._modello_cielo({"modello_cielo": "perez"}) == "di Perez (1990)"
