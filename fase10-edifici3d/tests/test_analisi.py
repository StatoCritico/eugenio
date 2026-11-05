"""Aggancio facoltativo al modulo privato delle analisi 5 e 7–13 (Fase E). Nessun dato di norme: il modulo privato
dei test è finto e scritto qui."""
from __future__ import annotations

from pathlib import Path

import pytest

from edifici3d import analisi as A

QUI = Path(__file__).resolve().parent.parent
RICHIESTA = {"edificio": {"corpi": [{"id": "C1", "area": 100.0, "gronda": 9.0}]}, "ipotesi": {}}

FINTO = '''
INTERFACCIA = {interfaccia}
class NonDisponibile(Exception):
    pass
def stato():
    return {{"5": {{"disponibile": True, "motivo": "pronta"}}, "7": {{"disponibile": False, "motivo": "da compilare"}}}}
def calcola(id, richiesta):
    if id == "7":
        raise NonDisponibile("tabella da compilare")
    return {{"valori": {{"fabbisogno_kwh": 1234.5}}, "tabelle": [], "avvisi": [], "fonti": ["norma citata per nome"],
            "interno": "questa chiave non deve uscire"}}
'''


@pytest.fixture
def privato(tmp_path, monkeypatch):
    def fai(interfaccia=1, rotto=False):
        d = tmp_path / "uni_privato"
        d.mkdir(exist_ok=True)
        (d / "__init__.py").write_text("raise RuntimeError('rotto')" if rotto else FINTO.format(interfaccia=interfaccia),
                                       encoding="utf-8")
        monkeypatch.setattr(A, "candidati", lambda: [tmp_path])
        A.dimentica()
        return d
    yield fai
    A.dimentica()


@pytest.fixture
def senza(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "candidati", lambda: [tmp_path / "non_ce"])
    A.dimentica()
    yield
    A.dimentica()


def test_elenco_analisi():
    assert set(A.ANALISI) == {"5", "7", "8", "9", "10", "11", "12", "13"}
    sito = QUI.parent / "fase5-sito" / "sito"
    for a in A.ANALISI.values():
        assert (sito / a.pagina).is_file(), a.pagina


def test_senza_modulo_tutto_non_disponibile(senza):
    s = A.stato()
    assert s["modulo"] is False
    # 05/11/2026: 7, 9 e 13 sono nel codice pubblico (pagine del sito), le altre restano al modulo privato
    assert all(not r["disponibile"] and r["messaggio"] == A.NON_DISPONIBILE for r in s["analisi"] if not r.get("pubblica"))
    assert {r["id"] for r in s["analisi"] if r.get("pubblica") and r["disponibile"]} == {"7", "9", "13"}
    assert {a.id for a in A.ANALISI.values() if a.norme} == {"5", "8", "10", "11", "12"}
    with pytest.raises(A.NonDisponibile):
        A.calcola("5", RICHIESTA)


def test_modulo_finto(privato):
    privato()
    s = {r["id"]: r for r in A.stato()["analisi"]}
    assert s["5"]["disponibile"] and not s["10"]["disponibile"] and s["7"]["pubblica"] and s["13"]["pubblica"]
    r = A.calcola("5", RICHIESTA)
    assert r["valori"]["fabbisogno_kwh"] == 1234.5 and "interno" not in r and r["stima"] is True
    with pytest.raises(ValueError, match="nella sua pagina"):
        A.calcola("7", RICHIESTA)                       # pubblica: si calcola nella pagina, non sul server
    with pytest.raises(KeyError):
        A.calcola("99", RICHIESTA)
    with pytest.raises(ValueError):
        A.calcola("5", {"edificio": {"corpi": []}})


def test_interfaccia_diversa_o_modulo_rotto(privato):
    privato(interfaccia=2)
    assert A.stato()["modulo"] is False and "interfaccia" in A.motivo()
    privato(rotto=True)
    assert A.stato()["modulo"] is False and "non caricato" in A.motivo()


def test_modulo_privato_fuori_dal_repository():
    gi = (QUI.parent / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "fase10-edifici3d/uni_privato/" in gi
