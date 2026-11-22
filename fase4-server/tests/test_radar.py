"""«Dati pluviometrici» (22/11/2026, servizio/radar.py): solo «Merging» del DPC ogni 30 minuti, fini statistici.

Nessuna prova chiama il DPC: frame sintetici costruiti come RainGrid sulla griglia vera dei CUM (0,01°, EPSG:4326) e un
client finto con le due chiamate della libreria (last_product, download).
"""
import asyncio
import datetime as dt
import io
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from servizio import config as C, protezione as P, radar as RD

ROMA = ZoneInfo("Europe/Rome")
UTC = dt.timezone.utc


def griglia(prodotto="CUM3", t=dt.datetime(2026, 11, 22, 5, tzinfo=UTC), valore=2.0, nan_box=None):
    from affine import Affine
    from rasterio.crs import CRS
    from dpc_radar import RainGrid
    d = np.zeros((1233, 1341), dtype="float32")
    d[300:400, 600:700] = valore                    # zona con pioggia attorno a lon 11,6–12,6, lat 43,6–44,6
    if nan_box:
        r0, r1, c0, c1 = nan_box
        d[r0:r1, c0:c1] = np.nan
    return RainGrid.from_geotiff(_tiff(d), prodotto, t)


def _tiff(d):
    import rasterio
    from affine import Affine
    b = io.BytesIO()
    v = np.where(np.isfinite(d), d, -9999.0).astype("float32")
    with rasterio.MemoryFile() as m:
        with m.open(driver="GTiff", width=d.shape[1], height=d.shape[0], count=1, dtype="float32", nodata=-9999.0,
                    crs="EPSG:4326", transform=Affine(0.01, 0, 5.6, 0, -0.01, 47.58)) as ds:
            ds.write(v, 1)
        return m.read()


@pytest.fixture
def cartelle(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    monkeypatch.setattr(C, "RADAR_DATI", tmp_path / "dati" / "radar")
    monkeypatch.setattr(C, "RADAR_SITO", tmp_path / "sito" / "radar")
    (tmp_path / "dati").mkdir()
    pd.DataFrame({"istat": ["099014", "037006", "080063"], "nome": ["Rimini", "Bologna", "Reggio di Calabria"],
                  "lat": [44.06, 44.49, 38.11], "lon": [12.57, 11.34, 15.65], "provincia": ["RN", "BO", "RC"],
                  "regione_cod": ["08", "08", "18"]}).to_parquet(tmp_path / "dati" / "comuni.parquet")
    RD._comuni_file.cache_clear()
    RD._fine_file.cache_clear()
    return tmp_path


def test_solo_merging():
    """Decisione di Paolo del 22/11/2026: niente radar puro (SRI, SRT1), niente bollettini di allerta."""
    assert RD.PRODOTTI == ("CUM3", "CUM6", "CUM12", "CUM24")
    assert C.RADAR_MIN >= 30 and C.RADAR_ARCHIVIO_ANNI == 10
    assert not hasattr(RD, "aggiorna_bollettino")
    assert "CC BY-SA 4.0" in RD.FONTE and "statistici" in RD.AVVERTENZE[0]


def test_momenti_ore_locali_e_ora_legale():
    # CUM24 a mezzanotte italiana: d'inverno le 23 UTC, d'estate le 22 UTC
    inv = RD.momenti("CUM24", dt.datetime(2026, 11, 20, tzinfo=UTC), dt.datetime(2026, 11, 22, 12, tzinfo=UTC))
    assert [t.hour for t in inv] == [23, 23]
    est = RD.momenti("CUM24", dt.datetime(2026, 7, 1, tzinfo=UTC), dt.datetime(2026, 7, 2, 23, tzinfo=UTC))
    assert [t.hour for t in est] == [22, 22]
    tre = RD.momenti("CUM3", dt.datetime(2026, 11, 22, 0, 10, tzinfo=UTC), dt.datetime(2026, 11, 22, 12, tzinfo=UTC))
    assert all(t.minute == 0 and t.astimezone(ROMA).hour % 3 == 0 for t in tre) and len(tre) == 4
    assert RD.nome(tre[0]) == "20261122T0200Z" and RD.da_nome("20261122T0200Z") == tre[0]


def test_classi_e_tratteggio():
    v = np.array([[0.0, 0.4, 0.5, 300.0, np.nan, np.nan]], dtype="float32")
    c = RD.classi(v, "mm")
    assert c[0, 0] == 0 and c[0, 1] == 0                  # sotto 0,5 mm: trasparente
    assert c[0, 2] == 3 and c[0, 3] == 2 + len(RD.SOGLIE["mm"])
    assert set(c[0, 4:]) <= {1, 2}                          # nessuna misura: tratteggio, mai trasparente


def test_png_archivio_e_valori(cartelle):
    t = dt.datetime(2026, 11, 22, 5, tzinfo=UTC)
    g = griglia(t=t, nan_box=(1000, 1100, 1000, 1100))
    p = RD.percorso_png("CUM3", t)
    assert RD.scrivi_png(g, p) > 0
    from PIL import Image
    im = Image.open(p)
    assert im.size == (RD.LARGHEZZA, RD.ALTEZZA) and im.mode == "P"
    a = RD.percorso_archivio("CUM3", t)
    RD.scrivi_archivio(g, a)
    letto = RD.leggi_archivio(a, "CUM3")
    assert letto.time == t and np.nanmax(letto.data) == pytest.approx(2.0)
    assert np.isnan(letto.data[1050, 1050])
    df = RD.campiona_comuni(g)
    v = dict(zip(df.istat, df.mm))
    assert v["099014"] == pytest.approx(2.0) and v["037006"] == pytest.approx(0.0)
    RD.aggiungi_valori(df, RD.percorso_valori("CUM3", t))
    RD.aggiungi_valori(df, RD.percorso_valori("CUM3", t))      # niente doppioni
    assert len(pd.read_parquet(RD.percorso_valori("CUM3", t))) == 3
    assert RD.valori_fatti(RD.percorso_valori("CUM3", t)) == {"20261122T0500Z"}


def test_giornalieri_e_totali_del_mese(cartelle):
    for g in range(1, 31):                                  # CUM24 di ogni mezzanotte italiana di novembre (giorni 1–30)
        fine = dt.datetime(2026, 11, g, tzinfo=ROMA) + dt.timedelta(days=1)
        df = pd.DataFrame({"istat": ["099014", "037006"], "fine": pd.Timestamp(fine.astimezone(UTC)),
                           "mm": np.array([1.0, np.nan if g == 5 else 2.0], dtype="float32")})
        RD.aggiungi_valori(df, RD.percorso_valori("CUM24", fine))
    gg = RD.giornalieri("099014", 3, dt.date(2026, 11, 10))
    assert [x["data"] for x in gg] == ["2026-11-08", "2026-11-09", "2026-11-10"] and gg[0]["mm"] == 1.0
    assert RD.giornalieri("037006", 1, dt.date(2026, 11, 5))[0]["mm"] is None       # nessuna misura, mai zero
    tot = RD.totali_mese(2026, 11).set_index("istat")
    assert tot.loc["099014", "mm"] == pytest.approx(30.0) and tot.loc["099014", "giorni"] == 30
    assert tot.loc["037006", "giorni"] == 29 and tot.loc["037006", "mm"] == pytest.approx(58.0)   # il 5 senza misura


def test_lavori_priorita_e_assenti(cartelle):
    adesso = dt.datetime(2026, 11, 22, 8, 10, tzinfo=UTC)
    disp = {p: dt.datetime(2026, 11, 22, 7, 30, tzinfo=UTC) for p in RD.PRODOTTI}
    lista = RD.lavori(disp, adesso, archivio_ok=True)
    assert all("ultimo" in c for _, _, c in lista[:4]) and {p for p, _, _ in lista[:4]} == set(RD.PRODOTTI)
    assert lista[0][1].minute == 30                         # l'ultimo frame anche alle :30 (controllato col precedente)
    resto = [t for _, t, _ in lista[4:]]
    assert resto == sorted(resto, reverse=True)             # poi dal più recente
    assert all(t.minute == 0 for t in resto)                # immagini e archivio solo alle ore piene
    cum24 = [c for p, _, c in lista[4:] if p == "CUM24"]
    assert cum24 and all({"valori", "archivio"} & c for c in cum24)
    t0 = next(t for p, t, c in lista[4:] if p == "CUM3")
    senza = RD.lavori(disp, adesso, assenti={"CUM3": [RD.nome(t0)]})
    assert not any(p == "CUM3" and t == t0 for p, t, _ in senza)
    no_arch = RD.lavori(disp, adesso, archivio_ok=False)
    assert not any("archivio" in c for _, _, c in no_arch)


class ClientFinto:
    """Le due chiamate della libreria usate dal worker; i frame arrivano dalla funzione `crea`."""
    def __init__(self, ultimo, crea):
        self.ultimo, self.crea, self.chiesti = ultimo, crea, []

    async def last_product(self, p):
        return SimpleNamespace(time=self.ultimo)

    async def download(self, p, t):
        self.chiesti.append((p, t))
        return _tiff(self.crea(p, t))

    async def aclose(self):
        pass


def test_giro_controllo_di_qualita(cartelle, monkeypatch):
    """Un CUM24 alle :30 con la «campana» di migliaia di mm (successo tra il 9/10 e il 3/11/2026) viene scartato: resta
    l'ultimo frame buono."""
    monkeypatch.setattr(C, "RADAR_RECUPERO_GIORNI", 1)
    monkeypatch.setattr(C, "RADAR_GIORNI_MAPPA", 1)
    monkeypatch.setattr(C, "RADAR_SCARICHI", 200)
    monkeypatch.setattr(RD, "registra_previsto", lambda *a, **k: 0)
    adesso = dt.datetime(2026, 11, 22, 8, 10, tzinfo=UTC)

    def buono(p, t):
        d = np.zeros((1233, 1341), dtype="float32")
        d[300:400, 600:700] = 3.0
        return d
    cl = ClientFinto(dt.datetime(2026, 11, 22, 7, 30, tzinfo=UTC), buono)
    e = RD.giro(adesso, cl)
    assert not e["errori"] and not e["scartati"] and e["png"] > 0 and e["valori"] > 0
    u = RD._leggi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {})
    assert u["CUM24"]["fine"] == "20261122T0730Z" and u["CUM24"]["verdetto"] == "consistent"
    ind = RD._leggi_json(C.RADAR_SITO / "indice.json", {})
    assert set(ind["prodotti"]) == set(RD.PRODOTTI) and ind["prodotti"]["CUM3"]["frame"]
    assert ind["licenze"]["radar"]["licenza"].startswith("CC BY-SA 4.0")

    def campana(p, t):
        d = buono(p, t)
        if p == "CUM24":
            d[500:540, 700:740] = 20584.0
        return d
    cl2 = ClientFinto(dt.datetime(2026, 11, 22, 8, 0, tzinfo=UTC), campana)
    e2 = RD.giro(adesso + dt.timedelta(minutes=30), cl2)
    assert any(s.startswith("CUM24 20261122T0800Z") for s in e2["scartati"])
    u2 = RD._leggi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {})
    assert u2["CUM24"]["fine"] == "20261122T0730Z"          # resta il precedente
    assert u2["CUM3"]["fine"] == "20261122T0800Z"


def test_rotte(cartelle, monkeypatch):
    t = dt.datetime(2026, 11, 22, 7, 30, tzinfo=UTC)
    (C.RADAR_DATI / "ultimi").mkdir(parents=True)
    for p in RD.PRODOTTI:
        RD.scrivi_archivio(griglia(p, t, valore=4.0), C.RADAR_DATI / "ultimi" / f"{p}.tif")
    RD._scrivi_json(C.RADAR_DATI / "ultimi" / "ultimi.json", {p: {"fine": RD.nome(t)} for p in RD.PRODOTTI})
    P.limiti.clear()
    app = FastAPI()
    app.include_router(RD.router)
    api = TestClient(app)
    j = api.get("/api/radar/punto", params={"lat": 44.06, "lon": 12.57}).json()
    assert j["valori"]["CUM24"]["valore"] == pytest.approx(4.0) and j["comune"]["istat"] == "099014"
    assert "SRI" not in j["valori"]
    assert api.get("/api/radar/punto", params={"lat": 60, "lon": 12}).status_code == 422
    assert api.get("/api/radar/comune/123").status_code == 422
    assert api.get("/api/radar/comune/999999").status_code == 404
    c = api.get("/api/radar/comune/099014", params={"giorni": 5}).json()
    assert c["nome"] == "Rimini" and c["giornalieri"] == [] and "CC BY-SA" in c["fonte"]
    s = api.get("/api/radar/stato").json()
    assert s["archivio_anni"] == 10
    P.limiti.clear()


def test_previsto(cartelle):
    (C.DATI / "previsioni").mkdir(parents=True)
    ore = pd.date_range("2026-11-21T23:00Z", periods=24, freq="h")
    pd.DataFrame({"istat": "099014", "time": ore, "precipitation": 0.5}).to_parquet(
        C.DATI / "previsioni" / "ultima.parquet")
    assert RD.registra_previsto(dt.date(2026, 11, 22)) == 1
    assert RD.previsti("099014", dt.date(2026, 11, 22), dt.date(2026, 11, 22)) == {"2026-11-22": 12.0}
    prev = {"099014": pd.DataFrame({"data": [dt.date.today()], "pioggia": [7.0]})}
    assert RD.registra_previsto_email(prev) == 1
    assert RD.previsti_email("099014") == {dt.date.today().isoformat(): 7.0}


def test_newsletter_pioggia(cartelle):
    """Sezioni della pioggia misurata: settimanale (misurata e prevista) e mensile per regione (solo comuni misurati
    tutti i giorni), sempre con la licenza CC BY-SA 4.0."""
    from servizio import notiziario as N
    for g in range(1, 31):
        fine = dt.datetime(2026, 11, g, tzinfo=ROMA) + dt.timedelta(days=1)
        df = pd.DataFrame({"istat": ["099014", "037006", "080063"], "fine": pd.Timestamp(fine.astimezone(UTC)),
                           "mm": np.array([1.0, 2.0, np.nan if g == 3 else 12.0], dtype="float32")})
        RD.aggiungi_valori(df, RD.percorso_valori("CUM24", fine))
    giorni = [dt.date(2026, 11, 16) + dt.timedelta(days=i) for i in range(7)]
    righe = N.righe_pioggia_settimana({"istat": "099014"}, giorni)
    assert "| lun 16 | 1,0 mm |" in righe and any("7,0 mm" in r for r in righe)
    tab = "\n".join(N.tabella_pioggia_regioni(2026, 11, ["08", "18"], {"08": "Emilia-Romagna", "18": "Calabria"}))
    assert "### Emilia-Romagna" in tab and "| BO | 60 mm | Bologna, 60 mm |" in tab
    assert "Calabria" not in tab                     # Reggio senza misura il 3: escluso, la regione resta vuota
    assert "CC BY-SA 4.0" in tab and "statistici" in tab
    assert N.tabella_pioggia_regioni(2026, 10, ["08"], {"08": "Emilia-Romagna"}) == []


def test_report_con_licenza_condivisa():
    """I file della pagina Dati pluviometrici portano la licenza CC BY-SA 4.0 (dati del DPC) nei testi della licenza."""
    from openpyxl import load_workbook
    from servizio import report as REP
    doc = REP.Documento(titolo="Dati pluviometrici – Rimini", licenza="CC BY-SA 4.0", sezioni=[
        {"titolo": "Pioggia", "blocchi": [{"tipo": "tabella", "intestazioni": ["Giorno", "Misurata (mm)"],
                                           "righe": [["2026-11-21", 1.5], ["2026-11-22", None]]}]}])
    wb = load_workbook(io.BytesIO(REP.genera(doc, "xlsx")))
    testi = " ".join(str(c.value) for ws in wb for r in ws.iter_rows() for c in r if c.value)
    piedi = " ".join(ws.oddFooter.left.text or "" for ws in wb)
    assert "CC BY-SA 4.0" in testi and "stessa licenza" in testi and "CC BY-SA 4.0" in piedi
    assert REP.genera(doc, "pdf")[:4] == b"%PDF"
    normale = REP.Documento(titolo="x")
    assert normale.licenza == "CC BY 4.0" and REP._lic(normale, REP.TESTO_LICENZA) == REP.TESTO_LICENZA
