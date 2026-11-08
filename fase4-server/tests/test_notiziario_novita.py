"""Sezione «Novità di EuGEnio» della newsletter mensile (07/11/2026): voci del mese da fase5-sito/novita.toml."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servizio import config as C, notiziario as N   # noqa: E402

TOML = '''
[[voce]]
data = "2026-12-03"
versione = "20261203a"
titolo = "Prova di dicembre"
nuovo = ["Una cosa nuova."]
verificato = ["Una pagina validata."]

[[voce]]
data = "2026-11-07"
versione = "20261107a"
titolo = "Prova di novembre"
migliorato = ["Una cosa migliorata."]
'''


def test_novita_del_mese(tmp_path, monkeypatch):
    f = tmp_path / "novita.toml"
    f.write_text(TOML, encoding="utf-8")
    monkeypatch.setattr(C, "NOVITA_TOML", f)
    r = N.novita_del_mese(2026, 11)
    assert r[0] == "## Novità di EuGEnio" and "**7 novembre: Prova di novembre**" in r and "- Una cosa migliorata." in r
    assert r[r.index("*Migliorato*") + 2] == "- Una cosa migliorata."
    assert not any("dicembre" in x for x in r) and r[-2].endswith("/novita.html")
    assert N.novita_del_mese(2026, 10) == []
    assert N.novita_del_mese(2026, 11, tmp_path / "manca.toml") == []


def test_novita_vere_senza_dati_di_mercato():
    """Le voci vere di novembre 2026 entrano nella newsletter e non nominano dati GME o EEX."""
    r = "\n".join(N.novita_del_mese(2026, 11))
    assert "Novità di EuGEnio" in r and "19 comuni" in r and "*Nuovo*" in r and "*Verificato*" in r
    # (08/11/2026) solo funzioni per gli utenti: niente modifiche interne
    for x in ("anti-robot", "Turnstile", "llms.txt", "assistente AI", "proxy", "PMTiles", "WMS", "Caddy", "menu"):
        assert x not in r, x
    for v in ("PUN", "PSV", "IGI", "TTF", "EEX"):
        assert f" {v} " not in f" {r} "
