"""Test senza rete: python -m pytest tests/"""
import base64
import datetime as dt
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mercati_energia import archivio, convenzioni, gme, indici
from mercati_energia.fasce import fascia, festivi, pasqua


def test_pasqua_e_festivi():
    assert pasqua(2026) == dt.date(2026, 4, 5)
    assert dt.date(2026, 4, 6) in festivi(2026)          # lunedì dell'Angelo
    assert dt.date(2027, 10, 4) in festivi(2027)         # San Francesco dal 2026
    assert dt.date(2025, 10, 4) not in festivi(2025)


def _utc(s):
    return pd.Series([pd.Timestamp(s, tz="Europe/Rome").tz_convert("UTC")])


@pytest.mark.parametrize("quando,attesa", [
    ("2026-10-21 10:00", "F1"), ("2026-10-21 07:30", "F2"), ("2026-10-21 19:00", "F2"),
    ("2026-10-21 23:15", "F3"), ("2026-10-24 12:00", "F2"), ("2026-10-25 12:00", "F3"),
    ("2026-12-08 10:00", "F3"), ("2026-04-06 10:00", "F3"),
])
def test_fasce(quando, attesa):
    assert fascia(_utc(quando)).iloc[0] == attesa


def test_inizio_intervallo_cambio_ora():
    # 25/10/2026: giornata di 25 ore; il periodo 9 (quarto d'ora 3) dopo le 02:00 legali
    g = pd.Series([20261025, 20261025, 20261025])
    t = gme.inizio_intervallo(g, None, pd.Series([1, 9, 13]), 15)
    assert t.iloc[0] == pd.Timestamp("2026-10-24 22:00", tz="UTC")
    assert t.iloc[1] == pd.Timestamp("2026-10-25 00:00", tz="UTC")   # 02:00 CEST
    assert t.iloc[2] == pd.Timestamp("2026-10-25 01:00", tz="UTC")   # 02:00 CET (ora ripetuta)


def test_decodifica_risposta():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("data.json", json.dumps([{"FlowDate": 20261001, "Hour": 1, "Period": "1", "Zone": "PUN",
                                              "Price": 100.5, "Market": "MGP"}]))
    righe = gme._decodifica(base64.b64encode(buf.getvalue()).decode())
    assert righe[0]["Price"] == 100.5


def _archivio_sintetico(tmp: Path):
    t = pd.date_range("2026-09-01", "2026-10-31 23:45", freq="15min", tz="Europe/Rome").tz_convert("UTC")
    loc = t.tz_convert("Europe/Rome")
    prezzo = np.where((loc.hour >= 8) & (loc.hour < 19), 120.0, 80.0)
    df = pd.DataFrame({"inizio_utc": t, "data": loc.date, "ora": None, "periodo": None, "minuti": 15,
                       "zona": "PUN", "prezzo": prezzo.astype("float32"), "note": None})
    archivio.aggiorna(tmp, "mgp_prezzi", df, ["inizio_utc", "zona"], "data")
    gas = pd.DataFrame({"data": pd.date_range("2026-09-01", "2026-10-31").date, "mercato": "MGP",
                        "prodotto": "GDA", "prezzo": np.float32(40.0), "volumi_mwh": np.float32(1)})
    archivio.aggiorna(tmp, "mgp_gas", gas, ["data", "mercato", "prodotto"], "data")


def test_indici_e_convenzione(tmp_path):
    _archivio_sintetico(tmp_path)
    ind = indici.calcola(tmp_path)
    pun_f1 = ind[(ind.indice == "PUN_F1") & (ind.mese == "2026-10")].valore.iloc[0]
    assert abs(pun_f1 - 120.0) < 1e-6
    f = tmp_path / "c.toml"
    f.write_text("""
[convenzione]
id = "prova"
ente = "Prova"
commodity = "elettricita"
dal = 2026-01-01
al = 2026-12-31
[[lotto]]
id = "1"
regola_prezzo = "indice_piu_spread"
fasce = ["F1", "F2", "F3"]
indice = "PUN_FASCE"
spread = { F1 = 10, F2 = 10, F3 = 10 }
perdite = 0.1
[lotto.corrispettivi]
fisso_pod_anno = 120
""", encoding="utf-8")
    c = convenzioni.carica(f)
    pr = convenzioni.prezzi(c, "1", ["2026-10"], ind)
    assert abs(pr[pr.fascia == "F1"].prezzo.iloc[0] - 130.0) < 1e-6
    consumi = pd.DataFrame({"mese": ["2026-10"] * 3, "fascia": ["F1", "F2", "F3"], "quantita": [10.0, 5.0, 5.0]})
    co = convenzioni.costo(c, "1", consumi, ind)
    pf = dict(zip(pr.fascia, pr.prezzo))
    atteso = (10 * pf["F1"] + 5 * pf["F2"] + 5 * pf["F3"]) * 1.1 + 10   # perdite 10%, fisso 120/12
    assert 80 < pf["F2"] < 130 and 80 < pf["F3"] < 130   # F2 e F3 includono ore del weekend a 120
    assert abs(co.euro_totale.iloc[0] - atteso) < 1e-3


def test_gas_e_segnaposto(tmp_path):
    _archivio_sintetico(tmp_path)
    ind = indici.calcola(tmp_path)
    f = tmp_path / "g.toml"
    f.write_text("""
[convenzione]
id = "gas"
ente = "Prova"
commodity = "gas"
dal = 2025-10-01
al = 2026-09-30
[[lotto]]
id = "A"
regola_prezzo = "indice_piu_spread"
indice = "PSV_DA"
indice_alternativo = "PSV_MGPGAS_MENSILE"
spread = 0.05
""", encoding="utf-8")
    pr = convenzioni.prezzi(convenzioni.carica(f), "A", ["2026-09"], ind)
    assert abs(pr.prezzo.iloc[0] - (40.0 * 0.03852 / 3.6 + 0.05)) < 1e-6
    assert "stima con PSV_MGPGAS_MENSILE" in pr.note.iloc[0]
    f.write_text(f.read_text().replace("spread = 0.05", 'spread = "DA_COMPILARE"'), encoding="utf-8")
    with pytest.raises(ValueError, match="da compilare"):
        convenzioni.prezzi(convenzioni.carica(f), "A", ["2026-09"], ind)


def test_modelli_si_caricano():
    for f in (Path(__file__).parent.parent / "convenzioni" / "modelli").glob("*.toml"):
        c = convenzioni.carica(f)
        assert c.lotti and convenzioni.da_compilare(c)


def test_pfor_esempio_arera(tmp_path):
    """Delibera 241/2020: III trim. 2020, media forward di maggio 2020 = 5,861184 €/MWh → 1,628107 €/GJ."""
    from mercati_energia import pfor
    assert str(pfor.mese_rilevazione(pd.Period("2020Q3", "Q"))) == "2020-05"
    giorni = pd.bdate_range("2020-05-01", "2020-05-29")
    f = tmp_path / "fw.csv"
    righe = ["data;trimestre;prezzo"] + [f"{d:%Y-%m-%d};Q3-2020;5,861184" for d in giorni]
    righe += ["2020-04-15;Q3-2020;99"]   # fuori dal mese di rilevazione: ignorata
    f.write_text("\n".join(righe), encoding="utf-8")
    pfor.importa_forward(tmp_path, f)
    r = pfor.calcola(tmp_path, "2020Q3", "2020Q3")
    assert list(r.mese) == ["2020-07", "2020-08", "2020-09"]
    assert (r.metodo == "forward").all()
    assert abs(r.pfor_eur_gj.iloc[0] - 1.628107) < 1e-6
    assert r.pfor_eur_gj.nunique() == 1


def test_pfor_stima_spot(tmp_path):
    from mercati_energia import archivio, pfor
    d = pd.DataFrame({"data": pd.date_range("2026-08-01", "2026-08-31").date, "prezzo": 36.0,
                      "volume_mwh": 1.0, "scambi": 1})
    archivio.aggiorna(tmp_path, "ttf_eex", d, ["data"], "data")
    r = pfor.calcola(tmp_path, "2026Q4", "2026Q4")
    assert (r.metodo == "stima_spot").all() and abs(r.pfor_eur_gj.iloc[0] - 10.0) < 1e-9
    assert abs(r.pfor_eur_smc.iloc[0] - 10.0 * 0.03852) < 1e-9


def test_ttf_trimestrali_eex_e_pfor(tmp_path):
    """Lettura dei future trimestrali TTF dalla risposta del sito EEX (simulata) e PFOR col metodo forward."""
    import httpx
    from mercati_energia import archivio, eex, pfor
    richieste = []

    def risposta(req):
        richieste.append(dict(req.url.params))
        m = req.url.params["maturity"]
        dati = [["G3BQ", int(m), f"2026-11-{g:02d}", 1, 1, 1, None, None, 30.0 if m == "202701" else 40.0]
                for g in (2, 3, 4)] + [["G3BQ", int(m), "2026-11-05", 1, 1, 1, None, None, None]]
        return httpx.Response(200, json={"header": ["shortCode", "maturityDate", "tradeDate", "totVolTrdd",
                                                    "grossOpenInt", "grossOpenIntSz", "netOpenInt", "netOpenIntSz",
                                                    "settlPx"], "data": dati})

    cl = httpx.Client(transport=httpx.MockTransport(risposta))
    df = eex.ttf_trimestrali(dt.date(2026, 11, 5), trimestri=2, pausa_s=0, client=cl)
    assert [r["maturity"] for r in richieste] == ["202701", "202704"]
    assert richieste[0]["shortCode"] == "G3BQ" and richieste[0]["maturityType"] == "Quarter"
    assert len(df) == 6 and set(df.trimestre) == {"2027Q1", "2027Q2"}   # le sedute senza prezzo si scartano
    archivio.aggiorna(tmp_path, "ttf_forward", df, ["data", "trimestre"], "data")
    r = pfor.calcola(tmp_path, "2027Q1", "2027Q1")
    assert (r.metodo == "forward").all() and abs(r.pfor_eur_mwh.iloc[0] - 30.0) < 1e-9
    assert list(r.mese) == ["2027-01", "2027-02", "2027-03"]


def test_storico_all_indietro(tmp_path, monkeypatch):
    from mercati_energia import notturno
    from mercati_energia.config import Config, Gme
    chiamate = []

    def finto_igi(cl, a, b):
        chiamate.append((a, b))
        giorni = pd.date_range(max(a, dt.date(2023, 7, 20)), b)
        return pd.DataFrame({"data": giorni.date, "prodotto": "DA", "prezzo": np.float32(30)}) if len(giorni) else pd.DataFrame()

    monkeypatch.setattr(notturno.gme, "ClientGME", lambda u, p: object())
    monkeypatch.setattr(notturno, "serie", lambda cfg: [("igi", finto_igi, dt.date(2020, 1, 1), ["data", "prodotto"])])
    cfg = Config(cartella=tmp_path, gme=Gme(utente="x", max_minuti_storico=5), ttf_eex=False)
    e = {"dataset": {}, "errori": []}
    notturno._gme(cfg, e)
    s = archivio.stato_storico(tmp_path)["igi"]
    assert s["completo"] and archivio.prima_data(tmp_path, "igi", "data") == dt.date(2023, 7, 20)
    assert dt.date.fromisoformat(s["inizia_il"]) <= dt.date(2023, 7, 20)
    n = len(chiamate)
    notturno._gme(cfg, e)                 # seconda notte: nessun nuovo recupero dello storico
    assert len(chiamate) - n <= 2


def test_tabella_arera():
    from mercati_energia import arera
    pagina = """<table><tr><th>2026</th><th>Euro/MWh</th><th>Euro/GJ</th></tr>
    <tr><td>settembre</td><td>78,8021</td><td>21,889472</td></tr><tr><td>agosto</td><td>64,1540</td><td>1</td></tr>
    <tr><td>2025</td><td></td><td></td></tr><tr><td>dicembre</td><td>30,6528</td><td>8,5</td></tr></table>
    <table><tr><th>Nome</th></tr><tr><td>CookieConsent</td></tr></table>"""
    d = arera.leggi_tabella(pagina).set_index("mese")
    assert d.loc["2026-09", "valore"] == 78.8021 and d.loc["2025-12", "valore"] == 30.6528
    assert (d.indice == "PSV_DA").all() and len(d) == 3


def test_tabella_arera_2022_23_e_storico():
    """La pagina 2022/23 ha le colonne GJ, Smc, MWh: si legge quella in €/MWh. Lo storico nel pacchetto
    copre ottobre 2022 – dicembre 2023 e coincide con la pagina."""
    from mercati_energia import arera
    pagina = """<table><tr><th>Mese</th><th>Euro/GJ</th><th>Euro/Smc*</th><th>Euro/MWh</th></tr>
    <tr><td><strong>2023</strong></td><td></td><td></td><td></td></tr>
    <tr><td>dicembre</td><td>10,085694</td><td>0,388501</td><td>36,3085</td></tr>
    <tr><td>2022</td><td></td><td></td><td></td></tr>
    <tr><td>ottobre</td><td>21,681788</td><td>0,835182</td><td>78,0544</td></tr></table>"""
    d = arera.leggi_tabella(pagina).set_index("mese")
    assert d.loc["2023-12", "valore"] == 36.3085 and d.loc["2022-10", "valore"] == 78.0544
    solo_gj = pagina.replace("<th>Euro/MWh</th>", "").replace("<td>36,3085</td>", "").replace("<td>78,0544</td>", "")
    assert arera.leggi_tabella(solo_gj).set_index("mese").loc["2023-12", "valore"] == 36.3085   # 10,085694 × 3,6
    s = arera.storico().set_index("mese")
    assert list(s.index) == [str(p) for p in pd.period_range("2022-10", "2023-12", freq="M")]
    assert s.loc["2022-10", "valore"] == 78.0544 and s.loc["2023-12", "valore"] == 36.3085
    assert (s.indice == "PSV_DA").all() and (s.unita == "EUR/MWh").all()
