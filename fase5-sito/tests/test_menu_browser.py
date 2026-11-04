"""Prova nel browser (Chromium headless, Playwright) del menu dei servizi (04/11/2026).

- il mouse sul titolo di un gruppo apre la tendina verticale, l'uscita la chiude;
- il clic sul titolo fissa il gruppo nella riga nera sotto la barra, il clic su un altro gruppo la cambia, il secondo clic
  sullo stesso titolo la toglie; la scelta resta al cambio di pagina;
- le voci «licenza GME» non sono collegamenti e hanno il suggerimento «In attesa di autorizzazione dal GME»;
- a 375 px la riga scorre dentro di sé, la pagina non scorre in orizzontale e il pulsante × la chiude;
- nessun errore JavaScript.
Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

SITO = Path(__file__).resolve().parents[1] / "sito"
G = "details.voce-gruppo[data-gruppo={}]"


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
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def pagina(browser, larghezza, altezza=800):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza})
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    return ctx, pg


def aperto(pg, gruppo):
    return pg.evaluate(f"document.querySelector('{G.format(gruppo)}').open")


def fissato(pg):
    return pg.evaluate("document.documentElement.dataset.menuFissato || null")


def test_menu_computer(base, browser):
    ctx, pg = pagina(browser, 1366)
    pg.goto(base + "lidar.html")
    titolo = G.format("patrimonio") + " > summary"
    assert pg.get_attribute(titolo, "title") == "Clicca qui per fissare il menu Patrimonio sotto la barra"
    assert pg.get_attribute(titolo, "aria-pressed") == "false"
    # passaggio del mouse
    pg.hover(G.format("edificio") + " > summary")
    assert aperto(pg, "edificio")
    pg.mouse.move(700, 650)
    pg.wait_for_timeout(400)
    assert not aperto(pg, "edificio")
    # clic: si fissa, la tendina di quel gruppo non si apre
    pg.click(titolo)
    assert fissato(pg) == "patrimonio" and not aperto(pg, "patrimonio")
    assert pg.get_attribute(titolo, "aria-pressed") == "true"
    assert "richiudere la barra di Patrimonio" in pg.get_attribute(titolo, "title")
    riga = pg.locator("nav.riga-fissata")
    assert riga.evaluate("r => getComputedStyle(r).backgroundColor") == "rgb(0, 0, 0)"
    assert riga.locator(".riga-voci > li").count() == 6
    assert riga.locator("a[aria-current=page]").inner_text().startswith("LiDAR")
    pg.mouse.move(700, 650)
    pg.hover(titolo)
    pg.wait_for_timeout(100)
    assert not aperto(pg, "patrimonio")
    # un altro gruppo: la riga passa a quello; le voci GME nella riga non sono collegamenti
    pg.click(G.format("cogenerazione") + " > summary")
    assert fissato(pg) == "cogenerazione"
    assert riga.locator(".voce-gme").count() == 5 and riga.locator("a").count() == 1
    assert riga.locator(".voce-gme").first.get_attribute("title") == "In attesa di autorizzazione dal GME"
    # al cambio di pagina la riga resta
    pg.click("nav.riga-fissata a[href='cog-emissioni.html']")
    pg.wait_for_load_state("load")
    assert fissato(pg) == "cogenerazione" and riga.locator("a[aria-current=page]").count() == 1
    # voce GME nella tendina: niente collegamento, il clic non cambia pagina
    pg.hover(G.format("fotovoltaico") + " > summary")
    gme = pg.locator(G.format("fotovoltaico") + " .tendina .voce-gme")
    assert gme.count() == 1 and gme.get_attribute("aria-disabled") == "true"
    url = pg.url
    gme.click()
    pg.wait_for_timeout(150)
    assert pg.url == url
    # secondo clic sullo stesso titolo: la riga sparisce e torna la tendina
    pg.mouse.move(700, 650)
    pg.click(G.format("cogenerazione") + " > summary")
    assert fissato(pg) is None
    assert riga.evaluate("r => getComputedStyle(r).display") == "none"
    assert aperto(pg, "cogenerazione")
    pg.reload()
    assert fissato(pg) is None
    # tastiera: Tab apre, Esc chiude, Invio fissa e richiude
    pg.mouse.move(700, 650)
    pg.focus("a.marchio")
    pg.keyboard.press("Tab")
    while not pg.evaluate("document.activeElement.matches('details.voce-gruppo > summary')"):
        pg.keyboard.press("Tab")
    assert aperto(pg, "clima")
    pg.keyboard.press("Escape")
    assert not aperto(pg, "clima")
    pg.keyboard.press("Enter")
    assert fissato(pg) == "clima"
    pg.keyboard.press("ArrowDown")
    assert pg.evaluate("document.activeElement.closest('nav.riga-fissata') !== null")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Enter")
    assert fissato(pg) is None
    assert pg.evaluate("document.documentElement.scrollWidth") <= 1366
    assert not pg.errori, pg.errori
    ctx.close()


def test_menu_telefono(base, browser):
    ctx, pg = pagina(browser, 375, 740)
    pg.goto(base + "index.html")
    pg.evaluate("localStorage.setItem('menu-fissato', 'edificio')")
    pg.goto(base + "edificio-cer.html")
    riga = pg.locator("nav.riga-fissata")
    assert riga.evaluate("r => getComputedStyle(r).display") == "block"
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    assert riga.locator(".riga-voci").evaluate("u => u.scrollWidth > u.clientWidth && getComputedStyle(u).overflowX === 'auto'")
    box = riga.locator("a[aria-current=page]").bounding_box()
    assert box and box["x"] >= 0 and box["x"] < 375                       # la voce della pagina aperta è in vista
    # voce GME nel menu del telefono: niente collegamento, il tocco mostra la nota
    pg.click("details.menu-tutto > summary")
    pg.click("details.pannello-gruppo[data-gruppo=cogenerazione] > summary")
    gme = pg.locator("details.pannello-gruppo[data-gruppo=cogenerazione] .voce-gme").first
    url = pg.url
    gme.click()
    assert pg.url == url and "con-nota" in gme.get_attribute("class")
    pg.keyboard.press("Escape")
    pg.click("nav.riga-fissata .riga-chiudi")
    assert riga.evaluate("r => getComputedStyle(r).display") == "none"
    assert pg.evaluate("localStorage.getItem('menu-fissato')") is None
    assert not pg.errori, pg.errori
    ctx.close()
