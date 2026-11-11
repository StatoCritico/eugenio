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


def test_novita_tra(tmp_path, monkeypatch):
    """(11/11/2026) Voci dal numero precedente (escluso) al giorno dell'invio (compreso)."""
    import datetime as dt
    f = tmp_path / "novita.toml"
    f.write_text(TOML, encoding="utf-8")
    monkeypatch.setattr(C, "NOVITA_TOML", f)
    r = N.novita_tra(dt.date(2026, 10, 12), dt.date(2026, 11, 12))
    assert r[0] == "## Novità di EuGEnio" and "**7 novembre: Prova di novembre**" in r and "- Una cosa migliorata." in r
    assert r[r.index("*Migliorato*") + 2] == "- Una cosa migliorata."
    assert not any("dicembre" in x for x in r) and r[-2].endswith("/novita.html")
    assert N.novita_tra(dt.date(2026, 11, 7), dt.date(2026, 11, 30)) == []          # il 7 era già nel numero prima
    assert "**3 dicembre: Prova di dicembre**" in N.novita_tra(dt.date(2026, 11, 12), dt.date(2026, 12, 12))
    assert len([x for x in N.novita_tra(None, dt.date(2026, 12, 3)) if x.startswith("**")]) == 2   # dall'inizio
    assert N.novita_tra(None, dt.date(2026, 11, 12), tmp_path / "manca.toml") == []


def test_numero_precedente(monkeypatch):
    import datetime as dt
    monkeypatch.setattr(C, "NOTIZIARIO_PRIMO_NUMERO", "2026-11")
    monkeypatch.setattr(C, "NOTIZIARIO_GIORNO", 12)
    assert N._numero_precedente(dt.date(2026, 11, 12)) is None
    assert N._numero_precedente(dt.date(2026, 12, 12)) == dt.date(2026, 11, 12)
    assert N._numero_precedente(dt.date(2027, 1, 12)) == dt.date(2026, 12, 12)


def test_novita_vere_senza_dati_di_mercato():
    """Le voci vere fino al primo numero (12/11/2026) entrano nella newsletter e non nominano dati GME o EEX."""
    import datetime as dt
    r = "\n".join(N.novita_tra(None, dt.date(2026, 11, 12)))
    assert "Novità di EuGEnio" in r and "19 comuni" in r and "Meet EuGEnio" in r and "*Nuovo*" in r and "*Verificato*" in r
    # (08/11/2026) solo funzioni per gli utenti: niente modifiche interne
    for x in ("anti-robot", "Turnstile", "llms.txt", "assistente AI", "proxy", "PMTiles", "WMS", "Caddy", "menu"):
        assert x not in r, x
    for v in ("PUN", "IGI", "TTF", "EEX"):
        assert f" {v} " not in f" {r} "
    # (11/11/2026) il PSV day-ahead pubblicato da ARERA è autorizzato da Paolo; quello del GME no
    for riga in r.splitlines():
        if " PSV " in f" {riga} ":
            assert "ARERA" in riga and "GME" not in riga, riga
