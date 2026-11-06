"""File per gli agenti AI (06/11/2026): EUGENIO_PER_AGENTI.md nella radice del repository e nel sito, identico, con la
versione del sito in testa, e allineato alle rotte reali dell'API in tutti e due i sensi:
  * ogni percorso /api/… citato nel file esiste nell'app (anche gli esempi con valori, confrontati con i modelli);
  * ogni rotta pubblica dell'app (escluse /api/interno/…) è citata nel file con il suo modello, per esempio
    `/api/meteo/{istat}`.
Così un'API nuova o tolta fa fallire il test finché il file non viene aggiornato (regola di manutenzione in RIEPILOGO.md).
Dalla cartella fase4-server, con PYTHONPATH=../fase3-storico:../fase10-edifici3d:../fase7-territorio."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(QUI))
RADICE = QUI.parent
SITO = RADICE / "fase5-sito" / "sito"
NOME = "EUGENIO_PER_AGENTI.md"
CITATI = re.compile(r"/api/[A-Za-z0-9_\-./{}]*")


@pytest.fixture(scope="module")
def testo() -> str:
    return (RADICE / NOME).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rotte() -> set[str]:
    pytest.importorskip("fastapi")
    from servizio.app import app
    percorsi = set(app.openapi()["paths"])
    return percorsi | {app.docs_url, app.openapi_url}


def _regex(modello: str) -> re.Pattern:
    parti = re.split(r"(\{[^}]+\})", modello)
    return re.compile("^" + "".join("[^/?#]+" if p.startswith("{") else re.escape(p) for p in parti if p) + "$")


def _citati(testo: str) -> set[str]:
    out = set()
    for m in CITATI.findall(testo):
        p = m.rstrip(".,;:)").rstrip("/")
        if p and p != "/api":
            out.add(p)
    return out


def test_file_nella_radice_e_nel_sito_identico(testo):
    sito = SITO / NOME
    assert sito.exists(), "manca la copia nel sito"
    assert sito.read_bytes() == (RADICE / NOME).read_bytes(), "le due copie di EUGENIO_PER_AGENTI.md sono diverse"
    llms = (SITO / "llms.txt").read_text(encoding="utf-8")
    assert llms.startswith("# EuGEnio") and f"/{NOME}" in llms


def test_versione_e_regola_in_testa(testo):
    versione = re.search(r"\?v=(\d{8}[a-z]?)", (SITO / "index.html").read_text(encoding="utf-8")).group(1)
    testa = "\n".join(testo.splitlines()[:8])
    assert "Ultimo aggiornamento" in testa and f"?v={versione}" in testa, \
        f"in testa al file manca «Ultimo aggiornamento» con la versione del sito ?v={versione}"
    assert "Regola di manutenzione" in testa
    llms = (SITO / "llms.txt").read_text(encoding="utf-8")
    assert f"?v={versione}" in llms, "llms.txt non ha la versione attuale del sito"


def test_niente_segreti_ne_dati_interni(testo):
    for vietato in ("TURNSTILE_SECRET", "ZORNADE_API_KEY", "CLOUDFLARE_TUNNEL_TOKEN", "x-api-key", "fase2", "uni_privato",
                    "/api/interno"):
        assert vietato not in testo, vietato


def test_percorsi_citati_esistono(testo, rotte):
    modelli = [_regex(r) for r in rotte]
    mancanti = sorted(p for p in _citati(testo) if not any(m.match(p) for m in modelli))
    assert not mancanti, f"percorsi citati in {NOME} che l'API non ha: {mancanti}"


def test_rotte_pubbliche_citate(testo, rotte):
    citati = _citati(testo)
    pubbliche = {r for r in rotte if r.startswith("/api/") and not r.startswith("/api/interno/")}
    mancanti = sorted(r for r in pubbliche if r not in citati)
    assert not mancanti, f"rotte dell'API non descritte in {NOME} (aggiungile, con il modello del percorso): {mancanti}"
