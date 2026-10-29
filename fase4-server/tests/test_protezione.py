"""Prove della protezione dell'API (servizio/protezione.py): limiti per rete, tetti per tutto il sito, verifica
anti-robot con gettone di sessione e avvisi per i 429 ripetuti più giorni di fila.

Si eseguono dalla cartella fase4-server con `python -m pytest tests`. Non servono TiRex-2, la fase 3 né la rete:
Turnstile e le email sono simulati.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import sys
import types
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C                    # noqa: E402
from servizio import protezione as P                # noqa: E402

GIORNO = 86400
T0 = dt.datetime(2026, 11, 2, 12, 0, tzinfo=P.ROMA).timestamp()     # mezzogiorno, ora italiana


@pytest.fixture(autouse=True)
def pulito(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "PROTEZIONE_DIR", tmp_path / "protezione")
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", "")
    monkeypatch.setattr(C, "TURNSTILE_SECRET", "")
    P.limiti.clear()
    P.registro_429.svuota()
    P._avvisi_inviati.clear()
    inviati = []
    monkeypatch.setattr(P, "_invia_in_sottofondo", lambda oggetto, testo: inviati.append((oggetto, testo)))
    yield inviati
    P.limiti.clear()
    P.registro_429.svuota()


def richiesta(ip: str | None = "203.0.113.5", **intestazioni) -> Request:
    h = [(k.lower().replace("_", "-").encode(), v.encode()) for k, v in intestazioni.items()]
    if ip is not None:
        h.append((b"x-forwarded-for", ip.encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": h, "client": ("10.0.0.2", 1234)})


# ---------------------------------------------------------------------------------------------- indirizzi
def test_chiave_ip_ipv4_e_ipv6_per_rete():
    assert P.chiave_ip(richiesta("203.0.113.5")) == "203.0.113.5"
    assert P.chiave_ip(richiesta("203.0.113.5, 10.0.0.1")) == "203.0.113.5"
    a = P.chiave_ip(richiesta("2001:db8:1:2:aaaa::1"))
    b = P.chiave_ip(richiesta("2001:db8:1:2:ffff:ffff:ffff:fffe"))
    c = P.chiave_ip(richiesta("2001:db8:1:3::1"))
    assert a == b == "2001:db8:1:2::/64" and c != a
    assert P.chiave_ip(richiesta("::ffff:198.51.100.7")) == "198.51.100.7"
    assert P.chiave_ip(richiesta(None)) == "10.0.0.2"          # senza Caddy: l'indirizzo della connessione
    assert P.chiave_ip(richiesta("non-un-ip")) == "non-un-ip"


# ---------------------------------------------------------------------------------------------- finestre mobili
def test_limitatore_pesi_finestra_e_pulizia():
    L = P.Limitatore()
    assert L.prova("a", "t", 10, 3600, peso=6, ora=0)
    assert not L.prova("a", "t", 10, 3600, peso=5, ora=10)       # 6 + 5 > 10: non aggiunge nulla
    assert L.prova("a", "t", 10, 3600, peso=4, ora=20)
    assert L.usate("a", "t", 3600, ora=20) == 10
    assert L.usate("a", "t", 3600, ora=3601) == 4                # il primo peso è uscito dalla finestra
    assert L.prova("b", "t", 1, 3600, ora=30) and len(L) == 2
    L.prova("c", "t", 5, 3600, ora=L.PULIZIA_S + 4000)          # passa la pulizia: le code vuote spariscono
    assert len(L) == 1


def test_limita_e_messaggio(monkeypatch):
    monkeypatch.setitem(P.LIMITI, "report", (2, 3600))
    r = richiesta("198.51.100.1")
    P.limita(r, "report")
    P.limita(r, "report")
    with pytest.raises(HTTPException) as e:
        P.limita(r, "report")
    assert e.value.status_code == 429 and "massimo 2 richieste all'ora" in e.value.detail
    P.limita(richiesta("198.51.100.2"), "report")               # un altro indirizzo ha il suo conto
    monkeypatch.setattr(C, "STORICI_ESTRAZIONI_ORA", 1)          # limiti letti da config a ogni richiesta
    P.limita(r, "estrazione")
    with pytest.raises(HTTPException) as e:
        P.limita(r, "estrazione")
    assert "1 download all'ora" in e.value.detail


# ---------------------------------------------------------------------------------------------- tetti globali
def test_tetto_zornade_e_avviso(pulito, monkeypatch):
    monkeypatch.setattr(C, "ZORNADE_TETTO_ORA", 10)
    monkeypatch.setattr(C, "ZORNADE_AVVISO_QUOTA", 0.7)
    P.zornade_disponibile(10)
    P.zornade_conta(6)
    assert pulito == []
    P.zornade_conta(1)                                           # 7 su 10: avviso
    assert len(pulito) == 1 and "Zornade" in pulito[0][0]
    P.zornade_conta(1)                                           # una volta al giorno
    assert len(pulito) == 1
    P.zornade_disponibile(2)
    with pytest.raises(HTTPException) as e:
        P.zornade_disponibile(3)
    assert e.value.status_code == 503 and "quota" in e.value.detail


def test_turno_previsione(monkeypatch):
    monkeypatch.setattr(C, "PREVISIONI_PARALLELE", 1)
    monkeypatch.setattr(C, "PREVISIONI_ATTESA_S", 0.05)
    monkeypatch.setattr(P, "_previsioni", None)

    async def prova():
        async with P.turno_previsione():
            with pytest.raises(HTTPException) as e:
                async with P.turno_previsione():
                    pass
            assert e.value.status_code == 503
        async with P.turno_previsione():                        # liberato: si entra di nuovo
            return True
    assert asyncio.run(prova())
    P._previsioni = None


# ---------------------------------------------------------------------------------------------- sessione
def test_gettone_di_sessione(monkeypatch):
    monkeypatch.setattr(C, "SESSIONE_CHIAVE", "chiave-di-prova")
    monkeypatch.setattr(C, "SESSIONE_MINUTI", 30)
    g, scade = P.crea_sessione("203.0.113.5", ora=1000)
    assert scade == 1000 + 1800 and "203.0.113.5" not in g
    assert P.sessione_valida(g, "203.0.113.5", ora=1001)
    assert not P.sessione_valida(g, "203.0.113.6", ora=1001)      # altra rete
    assert not P.sessione_valida(g, "203.0.113.5", ora=2801)      # scaduto
    falso = g[:-1] + ("0" if g[-1] != "0" else "1")
    assert not P.sessione_valida(falso, "203.0.113.5", ora=1001)  # firma alterata
    parti = g.split(".")
    parti[1] = str(int(parti[1]) + 99999)
    assert not P.sessione_valida(".".join(parti), "203.0.113.5", ora=1001)   # scadenza allungata a mano
    assert not P.sessione_valida("", "203.0.113.5") and not P.sessione_valida("a.b.c", "203.0.113.5")
    monkeypatch.setattr(C, "SESSIONE_CHIAVE", "altra-chiave")      # chiave cambiata: i gettoni vecchi decadono
    assert not P.sessione_valida(g, "203.0.113.5", ora=1001)


def test_richiedi_sessione_solo_se_turnstile_acceso(monkeypatch):
    P.richiedi_sessione(richiesta())                             # spento: passa
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", "0xPUBBLICA")
    monkeypatch.setattr(C, "TURNSTILE_SECRET", "0xSEGRETA")
    with pytest.raises(HTTPException) as e:
        P.richiedi_sessione(richiesta())
    assert e.value.status_code == 401 and e.value.headers["X-EuGEnio-Verifica"] == "1"
    g, _ = P.crea_sessione("2001:db8:1:2::/64")
    P.richiedi_sessione(richiesta("2001:db8:1:2::77", **{"X-EuGEnio-Sessione": g}))   # stessa /64: valido


def test_verifica_turnstile(monkeypatch):
    monkeypatch.setattr(C, "TURNSTILE_SECRET", "0xSEGRETA")
    monkeypatch.setattr(C, "TURNSTILE_HOSTNAME", ["eugenio.statocritico.it"])
    visti = []

    def risposta(req: httpx.Request) -> httpx.Response:
        corpo = dict(x.split("=") for x in req.content.decode().split("&"))
        visti.append(corpo)
        if corpo["response"] == "buono":
            return httpx.Response(200, json={"success": True, "hostname": "eugenio.statocritico.it"})
        if corpo["response"] == "altro-sito":
            return httpx.Response(200, json={"success": True, "hostname": "copia.example.org"})
        if corpo["response"] == "rete":
            raise httpx.ConnectError("giù")
        return httpx.Response(200, json={"success": False, "error-codes": ["invalid-input-response"]})

    vero = httpx.AsyncClient
    monkeypatch.setattr(P.httpx, "AsyncClient", lambda **kw: vero(transport=httpx.MockTransport(risposta), **kw))
    assert asyncio.run(P.verifica_turnstile("buono", "203.0.113.5"))
    assert visti[-1] == {"secret": "0xSEGRETA", "response": "buono", "remoteip": "203.0.113.5"}
    assert not asyncio.run(P.verifica_turnstile("scaduto", "203.0.113.5"))
    assert not asyncio.run(P.verifica_turnstile("altro-sito", None))
    assert "remoteip" not in visti[-1]
    with pytest.raises(HTTPException) as e:
        asyncio.run(P.verifica_turnstile("rete", None))
    assert e.value.status_code == 503


# ---------------------------------------------------------------------------------------------- 429 ripetuti
def test_avviso_solo_dopo_piu_giorni_consecutivi(pulito, monkeypatch):
    monkeypatch.setattr(C, "AVVISO_429_SOGLIA", 3)
    monkeypatch.setattr(C, "AVVISO_429_GIORNI", 3)
    monkeypatch.setattr(C, "AVVISO_429_CONSERVA_GIORNI", 7)
    R = P.registro_429

    def giorno(k, volte, rete="203.0.113.9"):
        return [R.registra(rete, "previsione", ora=T0 + k * GIORNO + i) for i in range(volte)]

    assert not any(giorno(0, 10))            # primo giorno: tanti 429 ma nessun avviso
    assert not any(giorno(1, 3))
    assert pulito == []
    assert giorno(2, 4) == [False, False, True, False]   # terzo giorno di fila, alla soglia: un avviso
    assert len(pulito) == 1 and "3 giorni" in pulito[0][0] and "203.0.113.9" in pulito[0][1]
    assert not any(giorno(3, 5))             # stessa serie: nessun altro avviso
    assert len(pulito) == 1
    assert not any(giorno(4, 2))             # sotto la soglia: la serie si interrompe
    assert not any(giorno(5, 3)) and not any(giorno(6, 3))
    assert giorno(7, 3)[-1] is True          # nuova serie di tre giorni: nuovo avviso
    assert len(pulito) == 2
    assert not any(giorno(7, 5, rete="198.51.100.4"))     # un'altra rete ha i suoi giorni
    salvato = json.loads((C.PROTEZIONE_DIR / "429.json").read_text(encoding="utf-8"))
    giorni = sorted(salvato["giorni"])
    assert len(giorni) <= 7 and giorni[-1] == dt.datetime.fromtimestamp(T0 + 7 * GIORNO, P.ROMA).date().isoformat()


def test_registro_riletto_dal_file(monkeypatch):
    monkeypatch.setattr(C, "AVVISO_429_SOGLIA", 2)
    monkeypatch.setattr(C, "AVVISO_429_GIORNI", 2)
    R = P.registro_429
    R.registra("203.0.113.9", "dati", ora=T0)
    R.registra("203.0.113.9", "dati", ora=T0 + 1)                 # alla soglia: il file si scrive subito
    nuovo = P.Registro429()                                        # come dopo un riavvio dell'api
    nuovo.registra("203.0.113.9", "dati", ora=T0 + GIORNO)
    assert nuovo.registra("203.0.113.9", "dati", ora=T0 + GIORNO + 1)


def test_limita_conta_i_429(monkeypatch):
    monkeypatch.setitem(P.LIMITI, "report", (1, 3600))
    r = richiesta("192.0.2.44")
    P.limita(r, "report")
    for _ in range(3):
        with pytest.raises(HTTPException):
            P.limita(r, "report")
    oggi = dt.datetime.now(P.ROMA).date().isoformat()
    assert P.registro_429._carica()["giorni"][oggi]["192.0.2.44"] == 3


# ---------------------------------------------------------------------------------------------- rotte
@pytest.fixture(scope="module")
def client():
    """app.py senza TiRex-2 né fase 3 (come in test_report.py)."""
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
    yield TestClient(A.app), A
    for k, v in salvati.items():
        if v is None:
            sys.modules.pop(k, None)


def test_rotte_dei_dati_limitate_per_rete(client, monkeypatch, tmp_path):
    c, A = client
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(C, "LIMITE_DATI_ORA", 2)
    h = {"X-Forwarded-For": "2001:db8:aa:bb::1"}
    assert c.get("/api/metodologia", headers=h).status_code == 200
    assert c.get("/api/metodologia", headers={"X-Forwarded-For": "2001:db8:aa:bb::2"}).status_code == 200
    r = c.get("/api/metodologia", headers={"X-Forwarded-For": "2001:db8:aa:bb:cc::3"})   # stessa /64
    assert r.status_code == 429 and "all'ora" in r.json()["detail"]
    assert c.get("/api/metodologia", headers={"X-Forwarded-For": "2001:db8:aa:bc::1"}).status_code == 200
    assert c.get("/api/salute").status_code == 200                # la salute non ha limiti


def test_protezione_e_sessione_dal_sito(client, monkeypatch):
    c, A = client
    assert c.get("/api/protezione").json()["turnstile"] is None
    assert c.post("/api/sessione", json={"token": "x"}).json() == {"sessione": None, "scade": None}
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", "0xPUBBLICA")
    monkeypatch.setattr(C, "TURNSTILE_SECRET", "0xSEGRETA")
    monkeypatch.setattr(C, "ZORNADE_API_KEY", "chiave-finta")
    cfg = c.get("/api/protezione").json()
    assert cfg["turnstile"] == "0xPUBBLICA" and "0xSEGRETA" not in json.dumps(cfg)
    h = {"X-Forwarded-For": "203.0.113.20"}
    r = c.get("/api/geocodifica?q=via+zamboni+33", headers=h)
    assert r.status_code == 401 and r.headers["x-eugenio-verifica"] == "1"

    async def esito(token, ip):
        return token == "buono"
    monkeypatch.setattr(P, "verifica_turnstile", esito)
    assert c.post("/api/sessione", json={"token": "cattivo"}, headers=h).status_code == 403
    g = c.post("/api/sessione", json={"token": "buono"}, headers=h).json()["sessione"]

    async def finto_zornade(percorso, params):
        return {"data": [{"lat": 44.5, "lon": 11.3, "label": "Via Zamboni 33"}]}
    monkeypatch.setattr(A, "_zornade", finto_zornade)
    r = c.get("/api/geocodifica?q=via+zamboni+33", headers={**h, "X-EuGEnio-Sessione": g})
    assert r.status_code == 200 and r.json()["risultati"][0]["lat"] == 44.5
    r = c.get("/api/geocodifica?q=via+zamboni+33", headers={"X-Forwarded-For": "203.0.113.21", "X-EuGEnio-Sessione": g})
    assert r.status_code == 401                                   # gettone usato da un'altra rete
    for rotta in ("/api/previsione", "/api/patrimonio"):
        assert c.post(rotta, headers=h, files={"file": ("a.csv", b"x")}, data={"istat": "037006"}).status_code == 401
    assert c.post("/api/storici/estrai", headers=h, json={"dataset": "comuni"}).status_code == 401
    monkeypatch.setattr(C, "SESSIONI_ORA", 2)                     # anche le verifiche hanno un limite
    P.limiti.clear()
    c.post("/api/sessione", json={"token": "buono"}, headers=h)
    c.post("/api/sessione", json={"token": "buono"}, headers=h)
    assert c.post("/api/sessione", json={"token": "buono"}, headers=h).status_code == 429
