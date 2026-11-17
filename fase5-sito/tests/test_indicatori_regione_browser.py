"""Costi energetici Sanità (indicatori.html): regione all'apertura (17/11/2026, Paolo).

La pagina si apre sempre sull'Emilia-Romagna con l'AUSL della Romagna, anche se il browser ricorda un'altra regione
scelta in un'altra pagina; un'altra regione vale solo se è scritta nell'indirizzo (?regione=RR).
Stesso impianto di test_mappe_browser.py (Chromium headless, niente rete). Si salta se Playwright non c'è.
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import attendi, base, browser, pagina  # noqa: E402,F401  (fixture e aiuti condivisi)


def _apri(browser, url, ricordata):
    ctx, pg = pagina(browser)
    ctx.add_init_script(f"try {{ localStorage.setItem('eugenio-regione', '{ricordata}'); }} catch (e) {{}}")
    pg.goto(url)
    attendi(pg, "document.querySelector('#ente') && document.querySelector('#ente').options.length > 1", 20000)
    return ctx, pg


def test_si_apre_su_emilia_romagna_anche_con_altra_regione_ricordata(browser, base):
    ctx, pg = _apri(browser, base + "indicatori.html", "09")
    assert pg.input_value("#regione") == "08"
    assert pg.input_value("#ente") == "080-114"                      # AUSL della Romagna
    assert pg.evaluate("window.EUGENIO.regione") == "08"            # la piccola mappa segue
    assert not pg.errori, pg.errori
    ctx.close()


def test_regione_scritta_nell_indirizzo_vale(browser, base):
    ctx, pg = _apri(browser, base + "indicatori.html?regione=09", "08")
    assert pg.input_value("#regione") == "09"
    assert pg.input_value("#ente") != "080-114"
    assert not pg.errori, pg.errori
    ctx.close()
