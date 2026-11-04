"""Prove della pagina di stato interna degli edifici (servizio/interno.py, fase 10, Fase C): verifica del JWT di
Cloudflare Access con una chiave RSA generata qui (nessuna rete), chiusura senza configurazione, contenuto dello stato.

Dalla cartella fase4-server: `python -m pytest tests`."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from servizio import config as C, interno as I, protezione as P  # noqa: E402

TEAM, AUD = "prova.cloudflareaccess.com", "aud-di-prova-123"
CHIAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ALTRA = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def gettone(chiave=CHIAVE, aud=AUD, iss=f"https://{TEAM}", scade=600, email="paolo@esempio.it"):
    ora = int(time.time())
    return jwt.encode({"aud": [aud], "iss": iss, "iat": ora, "exp": ora + scade, "email": email, "sub": "x"}, chiave,
                      algorithm="RS256", headers={"kid": "k1"})


class Chiavi:
    def get_signing_key_from_jwt(self, g):
        return type("K", (), {"key": CHIAVE.public_key()})()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "CF_ACCESS_TEAM_DOMAIN", f"https://{TEAM}/")
    monkeypatch.setattr(C, "CF_ACCESS_AUD", AUD)
    monkeypatch.setattr(C, "CF_ACCESS_EMAIL", "")
    monkeypatch.setattr(C, "EDIFICI_STATO", tmp_path / "stato")
    monkeypatch.setattr(C, "DATI", tmp_path)
    monkeypatch.setattr(I, "_client_chiavi", lambda: Chiavi())
    P.limiti.clear()
    app = FastAPI()
    app.include_router(I.router)
    (tmp_path / "stato").mkdir()
    (tmp_path / "stato" / "rn.json").write_text(json.dumps({
        "zona": "rn", "nome": "Rimini", "ordine": 1, "totale_tessere": 2, "conteggi": {"fatta": 1, "errore": 1},
        "qualita": {"buona": 3}, "fonti": [{"id": "rer_dsm", "stato": "in attesa", "motivo": "licenza da confermare"}],
        "esecuzioni": [{"inizio": "2026-11-04T03:30:00+01:00", "esito": "parziale"}] * 40,
        "errori": [{"tessera": "32_78504884", "errore": "HTTP 500"}],
        "tessere": {"32_78504884": {"stato": "fatta", "corpi": 3, "qualita": {"buona": 3}},
                    "32_78604884": {"stato": "errore", "tentativi": 1, "errore": "HTTP 500"}}}))
    (tmp_path / "stato" / "rotto.json").write_text("{non json")
    return TestClient(app)


def test_senza_intestazione_403(client):
    assert client.get("/api/interno/edifici/stato").status_code == 403


def test_gettone_valido(client):
    r = client.get("/api/interno/edifici/stato", headers={"Cf-Access-Jwt-Assertion": gettone()})
    assert r.status_code == 200
    assert r.headers["x-robots-tag"].startswith("noindex") and r.headers["cache-control"] == "no-store"
    d = r.json()
    (z,) = d["zone"]
    assert z["nome"] == "Rimini" and z["prossime"] == ["32_78604884"] and len(z["esecuzioni"]) == 30
    assert z["fonti"][0]["stato"] == "in attesa" and "dati" in d["disco"] and d["utente"] == "paolo@esempio.it"
    assert str(C.DATI) not in r.text                     # nessun percorso del server
    assert client.get("/api/interno/verifica", headers={"Cf-Access-Jwt-Assertion": gettone()}).status_code == 204


@pytest.mark.parametrize("g", [
    lambda: gettone(chiave=ALTRA),                        # firma di un'altra chiave
    lambda: gettone(aud="altra-applicazione"),
    lambda: gettone(iss="https://altro.cloudflareaccess.com"),
    lambda: gettone(scade=-3600),                         # scaduto
    lambda: "non.un.jwt",
    lambda: jwt.encode({"aud": AUD, "iss": f"https://{TEAM}", "exp": int(time.time()) + 60, "iat": int(time.time())},
                       "segreto", algorithm="HS256"),     # algoritmo simmetrico: rifiutato
])
def test_gettoni_rifiutati(client, g):
    assert client.get("/api/interno/edifici/stato", headers={"Cf-Access-Jwt-Assertion": g()}).status_code == 403


def test_email_ammesse(client, monkeypatch):
    monkeypatch.setattr(C, "CF_ACCESS_EMAIL", "altra@esempio.it")
    assert client.get("/api/interno/edifici/stato", headers={"Cf-Access-Jwt-Assertion": gettone()}).status_code == 403
    monkeypatch.setattr(C, "CF_ACCESS_EMAIL", "Paolo@Esempio.it, altra@esempio.it")
    assert client.get("/api/interno/edifici/stato", headers={"Cf-Access-Jwt-Assertion": gettone()}).status_code == 200


def test_chiusa_senza_configurazione(client, monkeypatch):
    monkeypatch.setattr(C, "CF_ACCESS_AUD", "")
    r = client.get("/api/interno/edifici/stato", headers={"Cf-Access-Jwt-Assertion": gettone()})
    assert r.status_code == 503 and "CF_ACCESS_AUD" in r.json()["detail"]


def test_previsioni_in_corso_per_la_pipeline():
    assert P.previsioni_in_corso() >= 0


def test_caddyfile_e_env():
    qui = Path(__file__).resolve().parents[1]
    c = (qui / "Caddyfile").read_text()
    assert "handle /api/interno/*" in c and "handle /interno/*" in c and "forward_auth api:8000" in c
    assert "not header Cf-Access-Jwt-Assertion *" in c and c.count('X-Robots-Tag "noindex, nofollow"') >= 2
    assert c.index("handle /api/interno/*") < c.index("handle /api/*")
    env = (qui / ".env.example").read_text()
    for k in ("CF_ACCESS_TEAM_DOMAIN=", "CF_ACCESS_AUD=", "CF_ACCESS_EMAIL="):
        assert f"\n{k}\n" in env                          # vuote: i valori veri solo nel .env del server
    sito = qui.parent / "fase5-sito" / "sito"
    robots = sito / "robots.txt"
    assert not robots.exists() or "interno" not in robots.read_text()
    pagina = (sito / "interno" / "edifici.html").read_text()
    assert 'name="robots" content="noindex, nofollow"' in pagina
    for f in sito.glob("*.html"):                         # nessun collegamento dalle pagine pubbliche
        assert "interno/" not in f.read_text(encoding="utf-8"), f.name


def test_report_edificio_con_falde():
    from servizio import report_servizi as RS
    doc = RS.report_edificio({"edificio": {"id": "E1"}, "falde": [
        {"corpo": "C1", "falda": "F1", "pendenza": 23.2, "orientamento": 180, "superficie": 304.7, "area_pianta": 280,
         "fonte": "LiDAR – Regione Emilia-Romagna"}, {"corpo": "C2", "falda": "F1", "pendenza": 0, "orientamento": None}]})
    (sez,) = [x for x in doc.sezioni if x.titolo == "Falde dei tetti"]
    assert sez.blocchi[0].righe[0][:4] == ["C1", "F1", 23.2, 180.0] and len(sez.blocchi[0].righe) == 2
