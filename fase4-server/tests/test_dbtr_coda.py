"""«Aggiungi DBTR» (07/11/2026): rotte di caricamento a pezzi, file malevoli, coda, approvazione e rifiuto interni.

Dalla cartella fase4-server con PYTHONPATH che comprende ../fase10-edifici3d (README). Nessuna rete: Turnstile spento,
JWT di Cloudflare Access firmato con una chiave generata qui (come test_interno.py)."""
from __future__ import annotations

import hashlib
import io
import os
import json
import stat
import sys
import time
import zipfile
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(QUI))
pytest.importorskip("fastapi")
jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from servizio import config as C, dbtr_coda as D, interno as I, protezione as P  # noqa: E402

K = pytest.importorskip("edifici3d.coda")
TEAM, AUD = "prova.cloudflareaccess.com", "aud-prova"
CHIAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def gettone_access():
    ora = int(time.time())
    return jwt.encode({"aud": [AUD], "iss": f"https://{TEAM}", "iat": ora, "exp": ora + 600, "email": "paolo@esempio.it"},
                      CHIAVE, algorithm="RS256")


class Chiavi:
    def get_signing_key_from_jwt(self, g):
        return type("K", (), {"key": CHIAVE.public_key()})()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "CARTELLA_CODA_DBTR", tmp_path / "coda")
    monkeypatch.setattr(C, "DBTR_PEZZO_MB", 0.01)            # pezzi di ~10 kB: si prova il caricamento a più pezzi
    monkeypatch.setattr(C, "DBTR_LIBERO_MIN_GB", 0.0)
    monkeypatch.setattr(C, "TURNSTILE_SITEKEY", ""); monkeypatch.setattr(C, "TURNSTILE_SECRET", "")
    monkeypatch.setattr(C, "CF_ACCESS_TEAM_DOMAIN", TEAM); monkeypatch.setattr(C, "CF_ACCESS_AUD", AUD)
    monkeypatch.setattr(C, "CF_ACCESS_EMAIL", "")
    monkeypatch.setattr(I, "_client_chiavi", lambda: Chiavi())
    P.limiti.clear()
    app = FastAPI()
    app.include_router(D.router)
    return TestClient(app)


def zip_buono() -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("estrazione/estraz_procons.gpkg", b"SQLite format 3\x00" + os.urandom(30000))
        z.writestr("estrazione/metadati.xml", "<x>Regione Emilia-Romagna CC BY 4.0</x>")
        z.writestr("estrazione/leggimi.exe", b"MZ")
    return b.getvalue()


def carica(client, dati: bytes, **campi):
    corpo = {"regione": "er", "comune": "Rimini", "istat": "099014", "intero": True, "formato": "zip",
             "dimensione": len(dati), "consenso": True, "impronta": hashlib.sha256(dati).hexdigest(), **campi}
    r = client.post("/api/dbtr/inizia", json=corpo)
    if r.status_code != 200:
        return r, None
    d = r.json()
    h = {D.INTESTAZIONE: d["gettone"]}
    for n in range(d["pezzi"]):
        rr = client.put(f"/api/dbtr/{d['id']}/pezzo/{n}", content=dati[n * d["pezzo_byte"]:(n + 1) * d["pezzo_byte"]], headers=h)
        assert rr.status_code == 200, rr.text
    return client.post(f"/api/dbtr/{d['id']}/fine", headers=h), d


def test_caricamento_a_pezzi_e_stato(client, tmp_path):
    dati = zip_buono()
    r, d = carica(client, dati)
    assert r.status_code == 200, r.text
    assert r.json()["stato"] == "ricevuto" and d["pezzi"] > 1
    rich = K.leggi_richiesta(tmp_path / "coda", d["id"])
    assert rich["stato"] == "ricevuto" and rich["comune_slug"] == "rimini" and rich["intero"] is True
    assert not {"ip", "rete", "indirizzo", "email", "nome_file"} & set(rich)                        # nessun dato personale
    assert (tmp_path / "coda" / d["id"] / "caricato.bin").read_bytes() == dati
    s = client.get(f"/api/dbtr/{d['id']}", headers={D.INTESTAZIONE: d["gettone"]})
    assert s.json()["stato"] == "ricevuto" and "coda" in s.json()["messaggio"]
    assert client.get(f"/api/dbtr/{d['id']}", headers={D.INTESTAZIONE: "x" * 32}).status_code == 404       # gettone sbagliato


def test_consenso_regione_nome_dimensione(client):
    dati = zip_buono()
    assert carica(client, dati, consenso=False)[0].status_code == 422
    assert carica(client, dati, regione="tos")[0].status_code == 422
    assert carica(client, dati, comune="../../etc")[0].status_code == 422
    assert carica(client, dati, comune="Rimini<script>")[0].status_code == 422
    assert carica(client, dati, dimensione=400 * 1024 * 1024)[0].status_code == 413


def _zip(voci) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, contenuto, *extra in voci:
            info = zipfile.ZipInfo(nome)
            if extra:
                info.external_attr = extra[0]
            z.writestr(info, contenuto, compress_type=zipfile.ZIP_DEFLATED)
    return b.getvalue()


@pytest.mark.parametrize("dati, parola", [
    (_zip([("../../evil.gpkg", b"SQLite format 3\x00" + bytes(2000))]), "percorso"),
    (_zip([("/etc/passwd.shp", bytes(2000))]), "percorso"),
    (_zip([("C:/win/a.shp", bytes(2000))]), "percorso"),
    (_zip([("link.shp", b"/etc/passwd" + bytes(2000), (stat.S_IFLNK | 0o777) << 16)]), "simbolico"),
    (_zip([("bomba.gpkg", bytes(60 * 1024 * 1024))]), "compressione"),
    (_zip([("solo.exe", bytes(3000)), ("leggimi.txt", b"x" * 2000)]), "GeoPackage"),
    (b"MZ" + bytes(5000), "zip"),
], ids=["risale", "assoluto", "unita", "link", "bomba", "senza-dati", "non-zip"])
def test_file_malevoli_rifiutati_e_cancellati(client, tmp_path, dati, parola):
    r, d = carica(client, dati)
    assert r.status_code == 422 and parola in r.json()["detail"], r.text
    assert not (tmp_path / "coda" / d["id"]).exists()                       # file cancellato subito


def test_impronta_diversa(client, tmp_path):
    dati = zip_buono()
    r, d = carica(client, dati, impronta="0" * 64)
    assert r.status_code == 422 and "impronta" in r.json()["detail"]


def test_limite_giornaliero_per_ip(client, monkeypatch):
    monkeypatch.setattr(C, "DBTR_CARICAMENTI_GIORNO", 2)
    dati = zip_buono()
    assert carica(client, dati)[0].status_code == 200
    assert carica(client, dati)[0].status_code == 200
    r = carica(client, dati)[0]
    assert r.status_code == 429 and "al giorno" in r.json()["detail"]


def test_coda_piena(client, monkeypatch):
    monkeypatch.setattr(C, "DBTR_CODA_MAX", 1)
    dati = zip_buono()
    assert carica(client, dati)[0].status_code == 200
    assert carica(client, dati)[0].status_code == 503


def test_spenta(client, monkeypatch):
    monkeypatch.setattr(C, "DBTR_CODA", False)
    assert carica(client, zip_buono())[0].status_code == 404


def test_ritiro(client, tmp_path):
    r, d = carica(client, zip_buono())
    h = {D.INTESTAZIONE: d["gettone"]}
    assert client.delete(f"/api/dbtr/{d['id']}", headers=h).json()["stato"] == "ritirata"
    assert not (tmp_path / "coda" / d["id"]).exists()


def _interna(client, metodo, url, scrive=False):
    h = {"cf-access-jwt-assertion": gettone_access()}
    if scrive:
        h["x-eugenio-interno"] = "1"
    return getattr(client, metodo)(url, headers=h)


def test_interno_coda_approva_rifiuta(client, tmp_path):
    coda = tmp_path / "coda"
    _, d1 = carica(client, zip_buono())
    _, d2 = carica(client, zip_buono(), comune="Riccione", istat="099013")
    assert client.get("/api/interno/dbtr/coda").status_code == 403                # senza Access
    lista = _interna(client, "get", "/api/interno/dbtr/coda").json()
    assert [x["comune"] for x in lista["coda"]] == ["Rimini", "Riccione"] and lista["utente"] == "paolo@esempio.it"
    # si approvano solo le richieste preparate
    assert _interna(client, "post", f"/api/interno/dbtr/{d1['id']}/approva", scrive=True).status_code == 409
    r = K.leggi_richiesta(coda, d1["id"]); r["stato"] = "in attesa di approvazione"; K.scrivi_richiesta(coda, r)
    (coda / d1["id"] / "anteprima.geojson").write_text('{"type":"FeatureCollection","features":[]}')
    assert _interna(client, "get", f"/api/interno/dbtr/{d1['id']}/anteprima").status_code == 200
    # senza l'intestazione della pagina (richiesta da un altro sito): rifiutata
    assert _interna(client, "post", f"/api/interno/dbtr/{d1['id']}/approva").status_code == 403
    assert _interna(client, "post", f"/api/interno/dbtr/{d1['id']}/approva", scrive=True).json()["stato"] == "approvato"
    assert K.leggi_richiesta(coda, d1["id"])["approvata_da"] == "paolo@esempio.it"
    assert _interna(client, "post", f"/api/interno/dbtr/{d2['id']}/rifiuta", scrive=True).json()["stato"] == "rifiutato"
    assert not (coda / d2["id"]).exists()
    s = client.get(f"/api/dbtr/{d2['id']}", headers={D.INTESTAZIONE: d2["gettone"]}).json()
    assert s["stato"] == "rifiutato" and "cancellato" in s["messaggio"]
    st = (coda / "storico.jsonl").read_text().splitlines()
    assert json.loads(st[-1])["comune"] == "Riccione" and json.loads(st[-1])["stato"] == "rifiutato"


def test_caddyfile_compose_ed_env():
    cf = (QUI / "Caddyfile").read_text(encoding="utf-8")
    assert "handle /api/dbtr/*" in cf and "max_size 40MB" in cf
    assert cf.index("handle /api/dbtr/*") < cf.index("handle /api/* {")
    dc = (QUI / "docker-compose.yml").read_text(encoding="utf-8")
    assert "edifici-coda:" in dc and "cpu_shares: 128" in dc and '"coda", "--ciclo"' in dc
    env = (QUI / ".env.example").read_text(encoding="utf-8")
    for k in ("DBTR_CODA=", "CARTELLA_CODA_DBTR=", "DBTR_MAX_MB=300", "DBTR_PEZZO_MB=32"):
        assert k in env
    assert C.DBTR_PEZZO_MB * 1.2 < 40 or C.DBTR_PEZZO_MB == 0.01
    assert "dbtr" in P.TIPI_PROTETTI


def test_caddyfile_elenchi_degli_edifici_senza_copia_lunga():
    """07/11/2026 sera: archivi.json e gli indice.json si riconvalidano sempre (prima un giorno di copia nel browser:
    Paolo vedeva ancora l'elenco vecchio con l'archivio di prova); i PMTiles restano in copia."""
    cf = (QUI / "Caddyfile").read_text(encoding="utf-8")
    blocco = cf[cf.index("handle_path /edifici3d/*"):]
    blocco = blocco[:blocco.index("file_server")]
    assert "@elenchi path /archivi.json */indice.json" in blocco
    assert 'header @elenchi Cache-Control "no-cache"' in blocco
    # 08/11/2026: Caddy ordina i «header» per matcher e quello senza matcher vinceva; ora due matcher che si escludono
    assert "@copiabili not path /archivi.json */indice.json" in blocco
    assert 'header @copiabili Cache-Control "public, max-age=86400"' in blocco
    import re
    senza_matcher = re.search(r"header \{[^}]*\}", blocco)
    assert senza_matcher is None or "Cache-Control" not in senza_matcher.group(0)
