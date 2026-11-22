"""Pagina iniziale (index.html, home.js; 22/11/2026, richiesta di Paolo): disegno dell'edificio con reti, territorio e
meteo, animato per stagione; il mouse su una parte mostra il gruppo di pagine; il clic apre la scheda; il clic su una
voce apre la pagina con il menu del gruppo fissato. In Chromium (si salta se Playwright o Chromium non ci sono)."""
from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SITO = Path(__file__).resolve().parents[1] / "sito"


class Silenzioso(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silenzioso, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def _apri(browser, base, larghezza=1366, **kw):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900}, **kw)
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.goto(base)
    pg.wait_for_selector("#scena-barra:not([hidden])")
    return ctx, pg, errori


def test_disegno_schede_e_menu_fissato(browser, base):
    ctx, pg, errori = _apri(browser, base)
    # all'inizio solo la scheda «Da dove cominciare», con un pulsante per gruppo
    assert pg.locator(".home-scheda:visible").count() == 1 and pg.locator("#scheda-intro").is_visible()
    assert pg.locator("#home-scelte button").count() == 7
    # mouse sull'edificio: riquadretto con il gruppo e le voci, parte in evidenza
    bb = pg.locator('.parte[data-gruppo="edificio"] polygon').first.bounding_box()
    pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
    pg.wait_for_selector("#scena-tip:not([hidden])")
    tip = pg.locator("#scena-tip").inner_text()
    assert "Edifici" in tip and "Obblighi di legge" in tip and "(in arrivo)" in tip
    assert "su" in pg.locator('.parte[data-gruppo="edificio"]').get_attribute("class")
    # clic sulle reti: si apre la scheda Statistiche, le altre restano chiuse
    pg.locator('.parte[data-gruppo="statistiche"] polygon').first.click(force=True)
    assert pg.evaluate("[...document.querySelectorAll('.home-scheda')].filter(s => !s.hidden).map(s => s.id)") == ["scheda-statistiche"]
    assert pg.locator('#home-scelte button[data-gruppo="statistiche"]').get_attribute("aria-pressed") == "true"
    # la × torna all'inizio
    pg.locator("#scheda-statistiche .scheda-chiudi").click()
    assert pg.locator("#scheda-intro").is_visible()
    # da tastiera: Invio su una parte apre la sua scheda
    pg.locator('.parte[data-gruppo="aria"]').focus()
    pg.keyboard.press("Enter")
    assert pg.locator("#scheda-aria").is_visible()
    # voce scelta: la pagina si apre con il gruppo fissato in orizzontale sotto il menu
    pg.locator('#scheda-aria a[href="aria-ore.html"]').click()
    pg.wait_for_url("**/aria-ore.html")
    pg.wait_for_selector("nav.riga-fissata ul.riga-voci a[href='aria-ore.html']")
    assert pg.evaluate("document.documentElement.dataset.menuFissato") == "aria"
    assert pg.locator("nav.riga-fissata ul.riga-voci").is_visible()
    assert pg.locator("nav.riga-fissata .riga-titolo").text_content().strip() == "Trattamento aria"
    assert not errori, errori
    ctx.close()


def test_stagioni_pausa_e_vecchi_indirizzi(browser, base):
    ctx, pg, errori = _apri(browser, base)
    scena = pg.locator("#scena")
    assert scena.get_attribute("data-stagione") == "estate" and scena.get_attribute("data-meteo") == "sole"
    pg.wait_for_function("document.getElementById('scena').dataset.meteo === 'pioggia'", timeout=8000)
    pg.locator("#scena-pausa").click()                     # ferma: la fase non cambia più
    fase = (scena.get_attribute("data-stagione"), scena.get_attribute("data-meteo"))
    pg.wait_for_timeout(5000)
    assert (scena.get_attribute("data-stagione"), scena.get_attribute("data-meteo")) == fase
    # i vecchi collegamenti di Previsioni (/?comune=…) passano a previsioni.html con le stesse scelte
    pg.goto(base + "?comune=040007&cosa=clima")
    pg.wait_for_url("**/previsioni.html?comune=040007*")
    assert not errori, errori
    ctx.close()


def test_movimento_ridotto_e_telefono(browser, base):
    ctx, pg, errori = _apri(browser, base, larghezza=375, reduced_motion="reduce")
    scena = pg.locator("#scena")
    pg.wait_for_timeout(5000)
    assert scena.get_attribute("data-meteo") == "sole"     # niente animazione da sola
    pg.locator("#scena-pausa").click()                     # il pulsante passa alla fase successiva
    assert scena.get_attribute("data-meteo") == "pioggia"
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    pg.locator('.parte[data-gruppo="patrimonio"] .sc-campo').nth(2).click(force=True)   # tocco: scheda, niente riquadretto
    assert pg.locator("#scheda-patrimonio").is_visible()
    assert not errori, errori
    ctx.close()
