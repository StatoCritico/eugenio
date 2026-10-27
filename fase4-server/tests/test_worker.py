"""Lavori periodici del worker sui file del sito: indicatori (fase 8) e clima dal 1940 (fase 9).
Niente rete: la fase 8 è sostituita da un modulo finto, gli script della fase 9 da due script finti."""
from __future__ import annotations

import json
import sys
import textwrap
import types

import pytest

from servizio import config as C

# il worker importa servizio.meteo, che usa la fase 3: se non è installata bastano dei moduli segnaposto
try:
    from servizio import meteo  # noqa: F401
except ImportError:
    finti = {"meteo_storico": {"VARIABILI": []}, "meteo_storico.aggrega": {"giornaliero": None},
             "meteo_storico.correzione": {"applica": None}, "meteo_storico.limiti": {"Limitatore": object},
             "meteo_storico.scarica": {"FONTI": {}, "client": None, "richiesta": None}}
    for nome, attr in finti.items():
        m = sys.modules.get(nome) or types.ModuleType(nome)
        m.__dict__.update({k: v for k, v in attr.items() if k not in m.__dict__})
        sys.modules[nome] = m
    sys.modules.pop("servizio.meteo", None)
from servizio import worker as W  # noqa: E402


@pytest.fixture
def sito(tmp_path, monkeypatch):
    dati = tmp_path / "sito_dati"
    dati.mkdir()
    monkeypatch.setattr(C, "SITO_DATI", dati)
    monkeypatch.setattr(C, "DATI", tmp_path / "dati")
    return dati


def scrivi(cartella, nomi, testo="{}"):
    cartella.mkdir(parents=True, exist_ok=True)
    for n in nomi:
        (cartella / n).parent.mkdir(parents=True, exist_ok=True)
        (cartella / n).write_text(testo)


def test_pubblica_sostituisce_la_cartella(tmp_path):
    finale, nuova = tmp_path / "x", tmp_path / ".x_nuova"
    scrivi(finale, ["a.json", "vecchio.json"])
    scrivi(nuova, ["a.json"], '{"n": 2}')
    W._pubblica(nuova, finale)
    assert json.loads((finale / "a.json").read_text()) == {"n": 2}
    assert not (finale / "vecchio.json").exists() and not nuova.exists()
    assert not (tmp_path / ".x_vecchia").exists()


def finta_fase8(monkeypatch, file):
    cli = types.ModuleType("indicatori_ssn.cli")
    def aggiorna(out, cache, **kw):
        scrivi(out, file, '{"nuovo": true}')
        return {"dimensioni": {f: 15 for f in file}, "mancanti": []}
    cli.aggiorna = aggiorna
    pacchetto = types.ModuleType("indicatori_ssn")
    pacchetto.cli = cli
    monkeypatch.setitem(sys.modules, "indicatori_ssn", pacchetto)
    monkeypatch.setitem(sys.modules, "indicatori_ssn.cli", cli)


def test_indicatori_pubblica(sito, monkeypatch):
    scrivi(sito / "indicatori", ["indice.json", "08.json"])
    finta_fase8(monkeypatch, ["indice.json", "08.json", "09.json"])
    W.indicatori()
    assert json.loads((sito / "indicatori" / "09.json").read_text()) == {"nuovo": True}
    assert not (sito / ".indicatori_nuova").exists()


def test_indicatori_incompleti_lasciano_i_vecchi(sito, monkeypatch):
    scrivi(sito / "indicatori", ["indice.json"] + [f"{i:02d}.json" for i in range(1, 21)])
    finta_fase8(monkeypatch, ["indice.json", "08.json"])
    with pytest.raises(RuntimeError):
        W.indicatori()
    assert (sito / "indicatori" / "20.json").read_text() == "{}"


SCARICA = """
import sys, pathlib
a = sys.argv
pathlib.Path(a[a.index("--cache") + 1]).mkdir(parents=True, exist_ok=True)
open(a[a.index("--log") + 1], "a").write("scaricato\\n")
"""
CALCOLA = """
import sys, pathlib
a = sys.argv
u = pathlib.Path(a[a.index("--uscita") + 1])
n = int(pathlib.Path(a[a.index("--cache") + 1]).joinpath("..", "n").resolve().read_text())
(u / "clima" / "08").mkdir(parents=True)
(u / "clima" / "indice.json").write_text("{}")
for i in range(n):
    (u / "clima" / "08" / f"0370{i:02d}.json").write_text('{"nuovo": 1}')
for f in ("clima_stagioni.csv", "clima_sintesi.csv", "clima_mensili.parquet"):
    (u / f).write_text("nuovo")
"""


@pytest.fixture
def fase9(sito, tmp_path, monkeypatch):
    codice = tmp_path / "codice"
    codice.mkdir()
    (codice / "scarica.py").write_text(textwrap.dedent(SCARICA))
    (codice / "calcola.py").write_text(textwrap.dedent(CALCOLA))
    lavoro = tmp_path / "lavoro"
    lavoro.mkdir()
    (lavoro / "comuni.parquet").write_text("finto")
    monkeypatch.setattr(C, "CLIMA_CODICE", codice)
    monkeypatch.setattr(C, "CLIMA_LAVORO", lavoro)
    scrivi(sito / "clima", ["indice.json", "08/037006.json", "08/037007.json"])
    for f in ("clima_stagioni.csv", "clima_sintesi.csv"):
        (sito / f).write_text("vecchio")
    return lavoro


def test_clima_pubblica(sito, fase9):
    (fase9 / "n").write_text("5")
    W.clima()
    assert len(list((sito / "clima" / "08").glob("*.json"))) == 5
    assert (sito / "clima_sintesi.csv").read_text() == "nuovo"
    assert (fase9 / "clima_mensili.parquet").exists() and not (sito / "clima_mensili.parquet").exists()
    assert "scaricato" in (fase9 / "scarica.log").read_text()
    assert not (sito / ".clima_nuova").exists()


def test_clima_incompleto_lascia_i_vecchi(sito, fase9):
    (fase9 / "n").write_text("1")          # 2 file JSON contro i 3 pubblicati
    with pytest.raises(RuntimeError):
        W.clima()
    assert (sito / "clima" / "08" / "037007.json").exists()
    assert (sito / "clima_sintesi.csv").read_text() == "vecchio"


def test_clima_senza_comuni(sito, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CLIMA_LAVORO", tmp_path / "vuota")
    with pytest.raises(FileNotFoundError):
        W.clima()


def test_date_del_clima():
    assert (10, 7) in C.CLIMA_DATE and (10, 1) in C.CLIMA_DATE
