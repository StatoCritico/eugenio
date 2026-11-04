"""«Solo clima» della pagina Previsioni (04/11/2026): variabili meteo previste senza consumi né TiRex-2."""
import numpy as np
import pandas as pd
import pytest

from meteo_storico import VARIABILI
from servizio import meteo, modello


def _orario(monkeypatch, ore_storico=72, ore_previsione=120):
    ora = pd.Timestamp.now(tz="UTC").floor("h")
    ts = pd.date_range(ora - pd.Timedelta(hours=ore_storico), periods=ore_storico, freq="h")
    tp = pd.date_range(ora, periods=ore_previsione, freq="h")
    st = pd.DataFrame({"time": ts, **{v: np.full(ore_storico, 10.0) for v in VARIABILI}})
    peso = np.where(np.arange(ore_previsione) < 72, 1.0, 0.0)
    pr = pd.DataFrame({"time": tp, **{v: np.full(ore_previsione, 20.0) for v in VARIABILI}, "peso_icon2i": peso})
    monkeypatch.setattr(meteo, "storico_orario", lambda istat: st)
    monkeypatch.setattr(meteo, "previsioni", lambda istat: pr)


def test_solo_clima_orario(monkeypatch):
    _orario(monkeypatch)
    r = modello.solo_clima("037006", "breve", 96, ["temperatura", "radiazione", "sconosciuta"])
    assert r["passo"] == "ora" and r["solo_clima"] and len(r["storico"]["t"]) == modello.STORICO_SOLO_CLIMA["breve"]
    assert len(r["previsione"]["t"]) == 96 == len(r["previsione"]["fonte_meteo"])
    assert list(r["clima"]) == ["temperatura", "radiazione"]     # ordine della pagina; le sconosciute si scartano
    v = r["clima"]["temperatura"]
    assert v["unita"] == "°C" and v["storico"][0] == 10.0 and v["previsione"][-1] == 20.0
    assert r["previsione"]["fonte_meteo"][0] == "previsione ICON-2I" and r["previsione"]["fonte_meteo"][-1] == "previsione IFS"
    assert any("IFS" in a for a in r["avvisi"])


def test_solo_clima_orario_oltre_le_previsioni(monkeypatch):
    _orario(monkeypatch, ore_previsione=48)
    r = modello.solo_clima("037006", "breve", 200)
    assert len(r["previsione"]["t"]) == 48
    assert any("arrivano a 48 ore" in a for a in r["avvisi"])


def test_solo_clima_giornaliero_con_climatologia(monkeypatch):
    oggi = pd.Timestamp.now(tz="Europe/Rome").tz_localize(None).normalize()
    giorni = pd.date_range(oggi - pd.Timedelta(days=3 * 365), oggi - pd.Timedelta(days=6), freq="D")
    st = pd.DataFrame({"data": giorni.date, "t_media": 12.0, "gg20": 8.0, "gc24": 0.0, "rad_globale_kwh_m2": 3.0})
    monkeypatch.setattr(meteo, "storico_giornaliero", lambda istat: st)
    monkeypatch.setattr(meteo, "storico_orario", lambda istat: pd.DataFrame(columns=["time", *VARIABILI]))
    monkeypatch.setattr(meteo, "previsioni", lambda istat: pd.DataFrame(columns=["time", *VARIABILI, "peso_icon2i"]))
    r = modello.solo_clima("037006", "lungo", 60)
    assert r["passo"] == "giorno" and len(r["storico"]["t"]) == 30 and len(r["previsione"]["t"]) == 60
    assert r["previsione"]["fonte_meteo"][-1] == "climatologia" and r["fonte_storico"][0].startswith("osservato")
    assert r["clima"]["gradi_giorno"]["unita"] == "GG" and r["clima"]["gradi_giorno"]["previsione"][-1] == 8.0
    assert any("climatologia" in a for a in r["avvisi"])


def test_solo_clima_senza_meteo(monkeypatch):
    monkeypatch.setattr(meteo, "storico_orario", lambda istat: pd.DataFrame(columns=["time", *VARIABILI]))
    monkeypatch.setattr(meteo, "previsioni", lambda istat: pd.DataFrame(columns=["time", *VARIABILI, "peso_icon2i"]))
    with pytest.raises(modello.MeteoMancante):
        modello.solo_clima("037006", "breve", 72)
    with pytest.raises(ValueError):
        modello.solo_clima("037006", "medio", 72)


def test_rotta_clima_previsto(monkeypatch):
    from fastapi.testclient import TestClient
    from servizio import app as A
    A._storia.clear()
    _orario(monkeypatch)
    monkeypatch.setattr(A, "_istat_valido", lambda istat: None)
    c = TestClient(A.app)
    r = c.get("/api/clima-previsto/037006?modalita=breve&orizzonte=24&covariate=temperatura,umidita")
    assert r.status_code == 200
    d = r.json()
    assert list(d["clima"]) == ["temperatura", "umidita"] and len(d["previsione"]["t"]) == 24
    assert c.get("/api/clima-previsto/037006?modalita=medio").status_code == 422
    monkeypatch.setattr(meteo, "previsioni", lambda istat: pd.DataFrame(columns=["time", *VARIABILI, "peso_icon2i"]))
    monkeypatch.setattr(meteo, "storico_orario", lambda istat: pd.DataFrame(columns=["time", *VARIABILI]))
    r = c.get("/api/clima-previsto/037006")
    assert r.status_code == 404 and "non sono ancora sul server" in r.json()["detail"]


def test_previsione_con_clima_affiancato(monkeypatch):
    """La risposta della previsione porta anche le variabili meteo usate, negli stessi passi (schede e report)."""
    monkeypatch.setattr(modello, "_esegui", lambda target, cov, orizzonte, freq:
                        pd.DataFrame({q: np.full(orizzonte, 1.0) for q in modello.QUANTILI}))
    _orario(monkeypatch, ore_storico=24 * 20, ore_previsione=120)
    ora = pd.Timestamp.now(tz="UTC").floor("h").tz_localize(None)
    idx = pd.date_range(ora - pd.Timedelta(hours=24 * 15), ora - pd.Timedelta(hours=1), freq="h")
    s = pd.Series(np.random.default_rng(0).uniform(1, 2, len(idx)), index=idx)
    r = modello.prevedi(s, "037006", "breve", 48, covariate=["radiazione", "temperatura"])
    assert list(r["clima"]) == ["radiazione", "temperatura"]
    t = r["clima"]["temperatura"]
    assert len(t["storico"]) == len(r["storico"]["t"]) and len(t["previsione"]) == 48
    assert t["storico"][0] == 10.0 and t["previsione"][-1] == 20.0 and t["unita"] == "°C"   # date locali → UTC


# ---------------------------------------------------------------------------------------------- report
def _con_clima():
    from test_report import PREVISIONE
    d = {**PREVISIONE, "clima": {   # ordine della risposta diverso da quello della pagina: vale quello delle covariate
        "radiazione": {"unita": "W/m²", "storico": [0.0, 0.0], "previsione": [10.0, 20.0, 30.0]},
        "temperatura": {"unita": "°C", "storico": [12.5, 12.0], "previsione": [11.5, 11.0, 10.5]}}}
    d["richiesta"] = {**PREVISIONE["richiesta"], "covariate": ["temperatura", "radiazione"]}
    return d


def test_report_previsione_colonne_affiancate():
    from servizio import report as R, report_servizi as RS
    from test_report import libro_xlsx
    doc = RS.report_previsione(_con_clima(), formato="xlsx")
    assert "Grafici" not in [s.titolo for s in doc.sezioni]          # i grafici solo nel PDF
    ws = libro_xlsx(R.genera(doc, "xlsx"))["Previsione (kWh)"]
    testa = [c.value for c in ws[1]]
    assert testa[:5] == ["Data e ora", "P10", "P50 (mediana)", "P90", "Valore reale"]
    assert testa[5:8] == ["Temperatura (°C)", "Radiazione solare (W/m²)", "Meteo usato"]
    assert ws["F2"].value == pytest.approx(11.5) and ws["G4"].value == pytest.approx(30.0)


def test_report_previsione_pdf_grafici_in_sequenza():
    from servizio import report as R, report_servizi as RS
    from test_report import leggi_pdf
    doc = RS.report_previsione(_con_clima(), formato="pdf")
    graf = next(s for s in doc.sezioni if s.titolo == "Grafici")
    didascalie = [b.didascalia for b in graf.blocchi if getattr(b, "tipo", "") == "immagine"]
    assert didascalie[0].startswith("Consumi") and didascalie[1:] == ["Temperatura (°C)", "Radiazione solare (W/m²)"]
    t = leggi_pdf(R.genera(doc, "pdf"))
    assert "Grafici" in t and "Radiazione solare" in t


def test_report_solo_clima(monkeypatch):
    from servizio import report as R, report_servizi as RS
    from test_report import leggi_pdf, libro_xlsx
    _orario(monkeypatch)
    r = modello.solo_clima("037006", "breve", 24, ["temperatura", "umidita"])
    r["richiesta"] = {"comune": "Bologna", "covariate": ["temperatura", "umidita"]}
    doc = RS.report_previsione(r, formato="pdf")
    assert doc.titolo == "Previsione del clima" and R.nome_file(doc, "pdf") == "clima_previsto_037006_breve.pdf"
    t = leggi_pdf(R.genera(doc, "pdf"))
    assert "Bologna" in t and "Umidità" in t
    assert not any("TiRex" in f.testo for f in doc.fonti)          # nessun modello dei consumi tra le fonti
    wb = libro_xlsx(R.genera(RS.report_previsione(r, formato="xlsx"), "xlsx"))
    ws = next(w for w in wb.worksheets if w.title.startswith("Clima previsto"))
    assert [c.value for c in ws[1]] == ["Data e ora", "Temperatura (°C)", "Umidità (%)", "Meteo usato"]
    assert ws.max_row == 25
