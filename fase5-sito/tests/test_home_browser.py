"""Pagina iniziale (index.html, home.js; 22/11/2026): scena a strati di Claude Design, una per tema (scuro futuristica,
chiaro tecnica), con i fondali WebP, l'animazione delle stagioni in CSS e le 16 parti. Il mouse su una parte ferma
l'animazione e mostra le sue informazioni (CSS); il clic apre la scheda del gruppo con le pagine della parte in evidenza; il
clic su una voce apre la pagina con il menu del gruppo fissato. In Chromium (si salta se Playwright o Chromium non ci sono)."""
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


def _apri(browser, base, larghezza=1366, tema=None, **kw):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900}, **kw)
    if tema:
        ctx.add_init_script(f"localStorage.setItem('tema', '{tema}')")
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.goto(base)
    pg.wait_for_function("getComputedStyle(document.getElementById('scena-contenitore')).getPropertyValue('--k') !== ''")
    return ctx, pg, errori


def _centro(pg, sel):
    """Un punto della parte che il mouse prende davvero (le sagome trasparenti si sovrappongono)."""
    pg.locator(sel).first.scroll_into_view_if_needed()
    bb = pg.locator(sel).first.bounding_box()
    parte = pg.locator(sel).first.get_attribute("data-parte")
    for fy in (.5, .35, .65, .2, .8, .1, .9):
        for fx in (.5, .3, .7, .15, .85, .05, .95):
            x, y = bb["x"] + bb["width"] * fx, bb["y"] + bb["height"] * fy
            trovata = pg.evaluate(f"(document.elementFromPoint({x}, {y}) || document.body).closest('.parte')?.dataset.parte")
            if trovata == parte:
                return x, y
    raise AssertionError(f"nessun punto libero per {parte}")


def test_scena_informazioni_schede_e_menu_fissato(browser, base):
    ctx, pg, errori = _apri(browser, base)
    assert pg.locator(".scena.tema-scuro").is_visible() and not pg.locator(".scena.tema-chiaro").is_visible()
    # la scena (1200 × 875) sta nel contenitore
    larg = pg.evaluate("document.getElementById('scena-contenitore').clientWidth")
    bb = pg.locator(".scena.tema-scuro").bounding_box()
    assert abs(bb["width"] - larg) < 3 and pg.evaluate("document.documentElement.scrollWidth") <= 1366
    # i fondali si caricano
    assert pg.evaluate("[...document.querySelectorAll('.scena.tema-scuro img.fondale')].every(i => i.complete && i.naturalWidth > 0)")
    # all'inizio solo «Da dove cominciare», con un pulsante per gruppo
    assert pg.locator(".home-scheda:visible").count() == 1 and pg.locator("#home-scelte button").count() == 7
    # mouse sull'UTA: le sue informazioni nel riquadro della scena
    pg.mouse.move(*_centro(pg, '.scena.tema-scuro .parte[data-parte="uta"]'))
    pg.wait_for_selector(".scena.tema-scuro .info-uta", state="visible")
    assert "trattamento aria" in pg.locator(".scena.tema-scuro .info-uta").inner_text().lower()
    # mouse sul cogeneratore: «Prossimamente»
    pg.mouse.move(*_centro(pg, '.scena.tema-scuro .parte[data-parte="cogenerazione"]'))
    pg.wait_for_selector(".scena.tema-scuro .info-cogenerazione", state="visible")
    assert "prossimamente" in pg.locator(".scena.tema-scuro .info-cogenerazione").inner_text().lower()
    # clic sul traliccio: scheda Statistiche con le pagine della rete elettrica in evidenza
    pg.mouse.click(*_centro(pg, '.scena.tema-scuro .parte[data-parte="traliccio"]'))
    assert pg.evaluate("[...document.querySelectorAll('.home-scheda')].filter(s => !s.hidden).map(s => s.id)") == ["scheda-statistiche"]
    evid = pg.locator("#scheda-statistiche li.evidenza a").all_inner_texts()
    assert "Carichi elettrici" in evid and "Stato della rete elettrica" in evid
    assert "Rete elettrica" in pg.locator("#scheda-statistiche .scheda-parte").text_content()
    pg.locator("#scheda-statistiche .scheda-chiudi").click()
    assert pg.locator("#scheda-intro").is_visible()
    # da tastiera: Invio sul recupero apre la scheda Trattamento aria
    pg.locator('.scena.tema-scuro .parte[data-parte="recupero"]').focus()
    pg.keyboard.press("Enter")
    assert pg.locator("#scheda-aria").is_visible()
    assert pg.locator('#scheda-aria li.evidenza a').all_inner_texts() == ["Free cooling e recupero"]
    # voce scelta: la pagina si apre con il gruppo fissato in orizzontale sotto il menu
    pg.locator('#scheda-aria a[href="aria-ore.html"]').click()
    pg.wait_for_url("**/aria-ore.html")
    pg.wait_for_selector("nav.riga-fissata ul.riga-voci a[href='aria-ore.html']")
    assert pg.evaluate("document.documentElement.dataset.menuFissato") == "aria"
    assert not errori, errori
    ctx.close()


def test_tema_chiaro_e_vecchi_indirizzi(browser, base):
    ctx, pg, errori = _apri(browser, base, tema="light")
    assert pg.locator(".scena.tema-chiaro").is_visible() and not pg.locator(".scena.tema-scuro").is_visible()
    pg.mouse.click(*_centro(pg, '.scena.tema-chiaro .parte[data-parte="fotovoltaico"]'))
    assert pg.locator("#scheda-fotovoltaico").is_visible()
    # i vecchi collegamenti di Previsioni (/?comune=…) passano a previsioni.html con le stesse scelte
    pg.goto(base + "?comune=040007&cosa=clima")
    pg.wait_for_url("**/previsioni.html?comune=040007*")
    assert not errori, errori
    ctx.close()


def test_movimento_ridotto_e_telefono(browser, base):
    ctx, pg, errori = _apri(browser, base, larghezza=375, reduced_motion="reduce")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    # animazioni ferme con il movimento ridotto
    assert pg.evaluate("document.getAnimations().filter(a => a.playState === 'running').length") == 0
    pg.mouse.click(*_centro(pg, '.scena.tema-scuro .parte[data-parte="territorio"]'))
    assert pg.locator("#scheda-patrimonio").is_visible()
    assert not errori, errori
    ctx.close()
