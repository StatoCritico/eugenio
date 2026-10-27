"""Prove di costruisci_pagine.py su una copia del sito."""
import re
import shutil
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

VOCI = {"index.html": "./", "patrimonio.html": "patrimonio.html", "legge10.html": "legge10.html",
        "dati.html": "dati.html", "indicatori.html": "indicatori.html", "metodo.html": "metodo.html",
        "faq.html": "faq.html", "sitografia.html": "sitografia.html", "mirror.html": "mirror.html",
        "contatti.html": "contatti.html", "licenza.html": None, "privacy.html": None}


@pytest.fixture()
def sito(tmp_path):
    d = tmp_path / "sito"
    d.mkdir()
    for f in (QUI / "sito").glob("*.html"):
        shutil.copy(f, d)
    for f in (QUI / "sito").glob("*.js"):
        shutil.copy(f, d)
    return d


def test_idempotente(sito):
    assert C.main(["--sito", str(sito)]) == 0
    prima = {f.name: f.read_text(encoding="utf-8") for f in sito.iterdir()}
    assert C.main(["--sito", str(sito), "--controlla"]) == 0
    assert C.main(["--sito", str(sito)]) == 0
    assert prima == {f.name: f.read_text(encoding="utf-8") for f in sito.iterdir()}


def test_voce_attiva_e_marcatori(sito):
    C.main(["--sito", str(sito)])
    for nome, href in VOCI.items():
        s = (sito / nome).read_text(encoding="utf-8")
        for parte in ("testa", "testata", "piede"):
            assert s.count(f"<!-- {parte} -->") == 1 and s.count(f"<!-- /{parte} -->") == 1, (nome, parte)
        attivi = re.findall(r'<a [^>]*aria-current="page"[^>]*>', s)
        if href is None:
            assert not attivi, nome
        else:
            assert len(attivi) == 2 and all(f'href="{href}"' in a for a in attivi), (nome, attivi)
            assert not any('class="marchio"' in a for a in attivi)


def test_versione(sito):
    C.main(["--sito", str(sito), "--versione", "20991231z"])
    for f in sito.iterdir():
        t = f.read_text(encoding="utf-8")
        assert not re.search(r"\?v=(?!20991231z)\d{8}", t), f.name
    assert 'const V = "20991231z"' in (sito / "cti_legge10.js").read_text(encoding="utf-8")
    assert C.main(["--sito", str(sito), "--versione", "20991231z", "--controlla"]) == 0


def test_modifica_del_modello_arriva_in_tutte_le_pagine(sito, monkeypatch, tmp_path):
    parti = tmp_path / "parti"
    shutil.copytree(C.PARTI, parti)
    p = parti / "piede.html"
    p.write_text(p.read_text(encoding="utf-8").replace("Contattaci", "Scrivici"), encoding="utf-8")
    monkeypatch.setattr(C, "PARTI", parti)
    C.main(["--sito", str(sito)])
    for nome in VOCI:
        assert "Scrivici</a>" in (sito / nome).read_text(encoding="utf-8")
