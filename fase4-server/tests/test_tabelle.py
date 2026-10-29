"""File caricati in Excel (.xlsx) od OpenDocument (.ods): convertiti nel CSV che previsione e patrimonio già leggono."""
import datetime as dt
import io

import pandas as pd
import pytest

from servizio import modello, tabelle


def _foglio(engine: str) -> bytes:
    ore = pd.date_range("2026-09-01", periods=48, freq="h")
    df = pd.DataFrame({"data e ora": ore, "consumo kWh": [1.5 + (i % 24) / 10 for i in range(48)]})
    b = io.BytesIO()
    with pd.ExcelWriter(b, engine=engine) as w:
        df.to_excel(w, index=False, sheet_name="Consumi")
        pd.DataFrame({"x": [1]}).to_excel(w, index=False, sheet_name="Altro")
    return b.getvalue()


@pytest.mark.parametrize("engine,atteso", [("openpyxl", "xlsx"), ("odf", "ods")])
def test_foglio_diventa_csv_leggibile(engine, atteso):
    dati = _foglio(engine)
    assert tabelle.tipo(dati) == atteso
    assert tabelle.fogli(dati) == ["Consumi", "Altro"]
    testo = tabelle.in_csv(dati).decode("utf-8")
    righe = testo.splitlines()
    assert righe[0] == "data e ora;consumo kWh"
    assert righe[1] == "2026-09-01;1.5"            # mezzanotte: solo la data
    assert righe[2] == "2026-09-01 01:00:00;1.6"
    s = modello.leggi_csv(testo.encode("utf-8"))
    assert len(s) == 48 and s.index[1] == pd.Timestamp("2026-09-01 01:00")


def test_csv_resta_uguale():
    dati = "data;valore\r\n2026-09-01;1\r\n".encode("utf-8")
    assert tabelle.tipo(dati) == "csv" and tabelle.in_csv(dati) is dati


def test_xls_e_zip_qualsiasi_rifiutati():
    with pytest.raises(ValueError, match="xls"):
        tabelle.in_csv(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 100)
    import zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("a.txt", "ciao")
    with pytest.raises(ValueError, match="non è un foglio"):
        tabelle.in_csv(b.getvalue())


def test_righe_vuote_in_fondo_e_limite():
    b = io.BytesIO()
    pd.DataFrame({"a": ["x", "y", None, None], "b": [1, 2, None, None]}).to_excel(b, index=False, engine="openpyxl")
    assert tabelle.in_csv(b.getvalue()).decode().splitlines() == ["a;b", "x;1", "y;2"]
    with pytest.raises(ValueError, match="Troppe righe"):
        tabelle.in_csv(b.getvalue(), max_righe=1)


def test_rotta_converti():
    from fastapi.testclient import TestClient
    from servizio import app as A
    A._storia.clear()
    c = TestClient(A.app)
    r = c.post("/api/converti", files={"file": ("consumi.ods", _foglio("odf"))})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["formato"] == "ods" and j["foglio_usato"] == "Consumi" and j["csv"].startswith("data e ora;consumo kWh")
    r = c.post("/api/converti", files={"file": ("vecchio.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64)})
    assert r.status_code == 422 and "xlsx" in r.json()["detail"]


def test_mappa_gradi_giorno_estivi(tmp_path, monkeypatch):
    """La mappa delle previsioni restituisce anche i gradi giorno estivi (base 24 °C), per il titolo «caldo»."""
    from fastapi.testclient import TestClient
    from servizio import app as A, config as C
    t0 = pd.Timestamp.now(tz="UTC").floor("h")
    t = pd.date_range(t0, periods=48, freq="h")
    d = pd.DataFrame({"istat": "037006", "time": t, "temperature_2m": 30.0})
    (tmp_path / "previsioni").mkdir()
    d.to_parquet(tmp_path / "previsioni" / "ultima.parquet")
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(A.meteo, "_previsioni", lambda mtime: d)
    j = TestClient(A.app).get("/api/mappa?giorni=7").json()["comuni"]["037006"]
    assert j["gg"] == 0 and j["gc"] == 12.0 and j["t"] == 30.0
