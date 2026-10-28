"""Limitatore delle chiamate all'API del GME (limiti letti dal vivo il 28/10/2026: 10 connessioni al minuto,
100 all'ora; ogni chiamata conta, anche Auth, GetMyQuotas e le risposte 429)."""
import base64
import datetime as dt
import io
import json
import zipfile

import httpx
import pytest

from mercati_energia import gme

QUOTE = {"lastModifiedTime": None, "lastModifiedHour": None, "activeConnections": 0, "connectionsPerMinute": 0,
         "connectionsPerHour": 0, "dataPerMinute": 0, "dataPerHour": 0,
         "limits": {"maxConcurrentConnections": 5, "maxConnectionsPerMinute": 10, "maxConnectionsPerHour": 100,
                    "maxDataPerMinute": 2250000, "maxDataPerHour": 350000000}}


def _zip(righe) -> str:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("dati.json", json.dumps(righe))
    return base64.b64encode(b.getvalue()).decode()


class Orologio:
    def __init__(self, t0):
        self.t = t0
        self.attese = []

    def adesso(self):
        return self.t

    def dormi(self, s):
        self.attese.append(s)
        self.t += s


@pytest.fixture
def orologio(monkeypatch):
    o = Orologio(dt.datetime(2026, 10, 28, 21, 0, tzinfo=gme.ROMA).timestamp())
    monkeypatch.setattr(gme, "_adesso", o.adesso)
    monkeypatch.setattr(gme, "_dormi", o.dormi)
    return o


def _client(gestore):
    return gme.ClientGME("utente", "segreto", transport=httpx.MockTransport(gestore))


def _gestore(orologio, chiamate, quote=None, risposte_dati=None):
    def g(req: httpx.Request):
        chiamate.append((orologio.t, req.url.path.rsplit("/", 1)[-1]))
        if req.url.path.endswith("/Auth"):
            return httpx.Response(200, json={"Success": True, "token": "t"})
        if req.url.path.endswith("/GetMyQuotas"):
            return httpx.Response(200, json=quote or QUOTE)
        if risposte_dati:
            return risposte_dati.pop(0)
        return httpx.Response(200, json={"ContentResponse": _zip([{"FlowDate": 20261027, "Price": 1}])})
    return g


def test_mai_oltre_i_limiti(orologio):
    """300 richieste: in nessuna finestra mobile di 60 s o di un'ora si superano 8 e 90 connessioni."""
    chiamate = []
    cl = _client(_gestore(orologio, chiamate))
    for _ in range(300):
        assert cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2))
    tempi = [t for t, _ in chiamate]
    assert len(tempi) == 302                                  # Auth + GetMyQuotas una sola volta
    assert sum(1 for _, n in chiamate if n == "GetMyQuotas") == 1
    for i, t in enumerate(tempi):
        assert sum(1 for u in tempi[i:] if u < t + 60) <= 8
        assert sum(1 for u in tempi[i:] if u < t + 3600) <= 90
    durata_h = (tempi[-1] - tempi[0]) / 3600
    assert 2.9 < durata_h < 3.5                               # ~90 all'ora: nessuna attesa inutile


def test_connessioni_gia_usate_nella_finestra(orologio):
    """Come il 28/10/2026: 104 connessioni usate in una finestra iniziata 20 minuti fa → si aspetta la sua fine."""
    inizio = dt.datetime.fromtimestamp(orologio.t - 1200, gme.ROMA).replace(tzinfo=None).isoformat()
    q = dict(QUOTE, connectionsPerHour=104, lastModifiedHour=inizio)
    chiamate = []
    cl = _client(_gestore(orologio, chiamate, quote=q))
    cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2))
    t_dati = [t for t, n in chiamate if n == "RequestData"][0]
    assert t_dati - chiamate[0][0] >= 2400                    # attesa fino alla fine della finestra del GME
    assert t_dati - chiamate[0][0] < 2500


def test_finestra_scaduta_non_fa_aspettare(orologio):
    inizio = dt.datetime.fromtimestamp(orologio.t - 4000, gme.ROMA).replace(tzinfo=None).isoformat()
    q = dict(QUOTE, connectionsPerHour=104, lastModifiedHour=inizio)
    chiamate = []
    cl = _client(_gestore(orologio, chiamate, quote=q))
    cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2))
    assert orologio.attese == []


def test_limiti_letti_dalle_quote(orologio):
    q = dict(QUOTE, limits=dict(QUOTE["limits"], maxConnectionsPerHour=50, maxConnectionsPerMinute=5))
    cl = _client(_gestore(orologio, [], quote=q))
    cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2))
    assert cl.limiti["ora"] == 50 and cl.limiti["minuto"] == 5
    assert cl._max_ora() == 40 and cl._max_minuto() == 3


def test_429_ripetuti_non_martellano(orologio):
    """Dopo un 429 si aspetta 65 s, poi 15 minuti per tentativo; con Retry-After si usa quello."""
    chiamate = []
    risposte = [httpx.Response(429), httpx.Response(429), httpx.Response(429, headers={"Retry-After": "120"}),
                httpx.Response(200, json={"ContentResponse": _zip([{"a": 1}])})]
    cl = _client(_gestore(orologio, chiamate, risposte_dati=risposte))
    assert cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2)) == [{"a": 1}]
    assert [a for a in orologio.attese if a >= 60] == [65, 900, 121]


def test_429_sempre_errore_dopo_sei_tentativi(orologio):
    chiamate = []
    cl = _client(_gestore(orologio, chiamate, risposte_dati=[httpx.Response(429) for _ in range(6)]))
    with pytest.raises(gme.ErroreGME, match="troppi tentativi"):
        cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2))
    assert sum(1 for _, n in chiamate if n == "RequestData") == 6
    assert sum(orologio.attese) >= 65 + 4 * 900


def test_quote_non_lette_usa_i_predefiniti(orologio):
    def g(req):
        if req.url.path.endswith("/Auth"):
            return httpx.Response(200, json={"Success": True, "token": "t"})
        if req.url.path.endswith("/GetMyQuotas"):
            return httpx.Response(500, text="errore")
        return httpx.Response(200, json={"ContentResponse": _zip([{"a": 1}])})
    cl = _client(g)
    assert cl.richiesta("IGI", "GAS_IGIndex", dt.date(2026, 10, 1), dt.date(2026, 10, 2)) == [{"a": 1}]
    assert cl.limiti == gme.LIMITI_PREDEFINITI


def test_istante_roma():
    t = gme._istante_roma("2026-10-28T19:44:13.08")
    assert dt.datetime.fromtimestamp(t, gme.ROMA).strftime("%H:%M") == "19:44"
    assert gme._istante_roma(None) is None and gme._istante_roma("ieri") is None
