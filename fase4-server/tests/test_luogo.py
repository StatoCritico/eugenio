"""Prove della ricerca di un luogo lato server (servizio/luogo.py, 17/11/2026): WFS catastale e Overpass simulati (nessuna
rete), copia in memoria, tetti per tutto il sito, spegnimento da .env, una sola riga, fonti. La logica (particella, metà
della via, scelte) è provata in fase7-territorio/tests/test_luogo.py."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fase7-territorio"))

from servizio import config as C, luogo as LG, protezione as P, strati as S   # noqa: E402

PARTICELLA = """<wfs:FeatureCollection xmlns:CP="x" xmlns:gml="y" xmlns:wfs="z"><wfs:member><CP:CadastralParcel gml:id="a">
<CP:msGeometry><gml:Polygon gml:id="b"><gml:exterior><gml:LinearRing><gml:posList srsDimension="2">44.0420 12.5890
44.0420 12.5900 44.0430 12.5900 44.0430 12.5890 44.0420 12.5890</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>
</CP:msGeometry><CP:NATIONALCADASTRALREFERENCE>H294_009900.2330</CP:NATIONALCADASTRALREFERENCE></CP:CadastralParcel>
</wfs:member></wfs:FeatureCollection>"""
OSM = {"elements": [{"type": "way", "tags": {"name": "Via Coriano", "highway": "secondary"},
                     "geometry": [{"lon": 12.600 - i * 0.0012, "lat": 44.040 - i * 0.00245} for i in range(21)]}]}
COMUNI = pd.DataFrame({"istat": ["099014"], "nome": ["Rimini"], "belfiore": ["H294"]})


class Risposta:
    def __init__(self, testo="", stato=200, js=None):
        self.text, self.status_code, self._js = testo, stato, js
        self.headers = {"content-type": "application/json" if js is not None else "text/xml"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("errore", request=None, response=None)

    def json(self):
        return self._js


@pytest.fixture()
def fonti(monkeypatch):
    """WFS e Overpass finti che contano le chiamate."""
    P.limiti.clear()
    for c in LG._copie.values():
        c.clear()
    monkeypatch.setattr(C, "LUOGO", True)
    monkeypatch.setattr(C, "CATASTO_WFS_TETTO_ORA", 3000)
    monkeypatch.setattr(C, "EDIFICI_OSM_TETTO_ORA", 300)
    conta = {"wfs": [], "overpass": []}

    class Client:
        def __init__(self, **k):
            assert k["headers"]["User-Agent"] == S.USER_AGENT
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url, params=None):
            conta["wfs"].append((url, params))
            return Risposta(PARTICELLA)
    monkeypatch.setattr(LG.httpx, "Client", Client)

    def chiedi(urls, query, formato="json", timeout=None, nome=""):
        conta["overpass"].append(query)
        return Risposta(js=OSM)
    monkeypatch.setattr(LG.S, "chiedi_overpass", chiedi)
    monkeypatch.setattr(LG.S, "istanze_overpass", lambda: ["https://overpass.invalid/api/interpreter"])
    return conta


def test_civico_particella_e_copia(fonti):
    riga = {"metodo": "indirizzo", "indirizzo": "via Settembrini 2", "civico": "", "fonte_punto": "ANNCSU",
            "indirizzo_trovato": "VIALE LUIGI SETTEMBRINI 2", "lat": 44.0425, "lon": 12.5895, "nota": "", "esito": "ok"}
    righe = [dict(riga)]
    LG.arricchisci(righe, "Rimini", COMUNI, None)
    r = righe[0]
    assert r["luogo_tipo"] == "particella" and r["particella_ade"]["riferimento"] == "H294_009900.2330"
    assert r["lat"] == 44.0425 and r["esito"] == "ok"                    # nessun campo tolto o cambiato
    assert r["luogo_riquadro"] == pytest.approx([12.5890, 44.0420, 12.5900, 44.0430])
    url, par = fonti["wfs"][0]
    assert url == C.CATASTO_WFS_URL and par["TYPENAMES"] == "CP:CadastralParcel" and len(fonti["wfs"]) == 1
    LG.arricchisci([dict(riga)], "Rimini", COMUNI, None)                 # stesso punto: dalla copia
    assert len(fonti["wfs"]) == 1
    assert LG.fonti(r) == ["Agenzia delle Entrate – Cartografia catastale (CC BY 4.0)"]


def test_via_senza_civico_overpass(fonti):
    righe = [{"metodo": "indirizzo", "indirizzo": "via Coriano", "civico": "", "fonte_punto": "ANNCSU", "lat": 44.016,
              "lon": 12.595, "nota": ""}]
    LG.arricchisci(righe, "rimini", COMUNI, None)
    r = righe[0]
    assert r["luogo_tipo"] == "via" and r["via_scelta"]["nome"] == "Via Coriano" and not fonti["wfs"]
    assert r["luogo_lat"] == pytest.approx(44.0155, abs=3e-4) and r["luogo_lon"] == pytest.approx(12.588, abs=3e-4)
    assert len(fonti["overpass"]) == 1 and 'area["ref:ISTAT"="099014"]' in fonti["overpass"][0]
    assert "Via Coriano" not in fonti["overpass"][0]                     # a Overpass solo le parole, non il testo
    assert LG.fonti(r) == ["© OpenStreetMap contributors (ODbL 1.0)"]


def test_tetti_spegnimento_e_piu_righe(fonti, monkeypatch):
    riga = {"metodo": "indirizzo", "indirizzo": "via Coriano", "civico": "", "fonte_punto": "ANNCSU", "lat": 44.016,
            "lon": 12.595, "nota": ""}
    monkeypatch.setattr(C, "EDIFICI_OSM_TETTO_ORA", 0)                   # tetto di Overpass pieno: nessuna chiamata
    righe = [dict(riga)]
    LG.arricchisci(righe, "Rimini", COMUNI, None)
    assert not fonti["overpass"] and righe[0]["luogo_tipo"] is None and "OpenStreetMap" in righe[0]["luogo_avviso"]
    monkeypatch.setattr(C, "CATASTO_WFS_TETTO_ORA", 0)
    righe = [{**riga, "indirizzo": "via Settembrini 2", "lat": 44.0425, "lon": 12.5895}]
    LG.arricchisci(righe, "Rimini", COMUNI, None)
    assert not fonti["wfs"] and "cartografia catastale non disponibile" in righe[0]["luogo_avviso"]
    # più righe (file del patrimonio) o LUOGO=false: niente
    righe = [dict(riga), dict(riga)]
    LG.arricchisci(righe, "Rimini", COMUNI, None)
    assert "luogo_tipo" not in righe[0]
    monkeypatch.setattr(C, "LUOGO", False)
    righe = [dict(riga)]
    LG.arricchisci(righe, "Rimini", COMUNI, None)
    assert "luogo_tipo" not in righe[0]


def test_errori_della_fonte_non_rompono_la_ricerca(fonti, monkeypatch):
    def guasto(urls, query, formato="json", timeout=None, nome=""):
        raise httpx.ConnectError("giù")
    monkeypatch.setattr(LG.S, "chiedi_overpass", guasto)
    righe = [{"metodo": "indirizzo", "indirizzo": "via Coriano", "civico": "", "fonte_punto": "ANNCSU", "lat": 44.016,
              "lon": 12.595, "nota": ""}]
    LG.arricchisci(righe, "Rimini", COMUNI, None)
    assert righe[0]["lat"] == 44.016 and righe[0]["luogo_tipo"] is None and righe[0]["luogo_avviso"]
    assert "luogo" in P._DINAMICI and P.soglia("luogo")[0] == C.LUOGO_ORA


def test_rotta_patrimonio_con_luogo(fonti, monkeypatch, tmp_path):
    """POST /api/patrimonio: con `luogo=1` e una riga i campi in più; senza, o con più righe, la risposta di prima."""
    fastapi = pytest.importorskip("fastapi.testclient")
    try:
        from servizio import app as A
    except Exception as e:                       # noqa: BLE001 - immagine senza le dipendenze dei report
        pytest.skip(f"app non importabile qui: {e}")
    import territorio.zornade as TZ
    from servizio import meteo

    class ZFinto:
        chiamate = 0
        def __init__(self, *a, **k):
            pass
        def geocodifica(self, q, limite=5):
            return [{"formatted_address": "Viale Luigi Settembrini 2, Rimini", "lat": 44.0425, "lng": 12.5895}]
        def particella_in_punto(self, lat, lon):
            return {"fid": 1, "label": "2330", "kind": "immobile", "cadastral_reference": "H294_009900.2330",
                    "municipality": {"code": "H294", "name": "Rimini"}, "centroid": {"lat": lat, "lng": lon}}
        def cerca_particella(self, *a, **k):
            return []
    monkeypatch.setattr(TZ, "Zornade", ZFinto)
    monkeypatch.setattr(C, "ZORNADE_API_KEY", "finta")
    monkeypatch.setattr(C, "ANNCSU_FILE", tmp_path / "manca.parquet")
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", ""); monkeypatch.setattr(C, "TURNSTILE_SECRET", "")
    monkeypatch.setattr(meteo, "comuni", lambda *a, **k: COMUNI.assign(provincia="RN"))
    cl = fastapi.TestClient(A.app)
    csv = "id;denominazione;indirizzo;civico;comune;foglio;particella\n1;ricerca;via Settembrini 2;;Rimini;;\n"
    r = cl.post("/api/patrimonio", files={"file": ("r.csv", csv.encode(), "text/csv")}, data={"luogo": "1"})
    assert r.status_code == 200, r.text
    x = r.json()["righe"][0]
    assert x["luogo_tipo"] == "particella" and x["particella_ade"]["mappale"] == "2330" and x["lat"] == 44.0425
    assert "Agenzia delle Entrate – Cartografia catastale (CC BY 4.0)" in r.json()["fonti"]
    r = cl.post("/api/patrimonio", files={"file": ("r.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200 and "luogo_tipo" not in r.json()["righe"][0]
    due = csv + "2;ricerca;via Settembrini 2;;Rimini;;\n"
    r = cl.post("/api/patrimonio", files={"file": ("r.csv", due.encode(), "text/csv")}, data={"luogo": "1"})
    assert r.status_code == 200 and all("luogo_tipo" not in x for x in r.json()["righe"])
