"""Pagina iniziale (index.html, home.js; 23/11/2026): disegno fermo (un fondale WebP per tema) adattato alla finestra, con
i 16 bersagli come unici elementi attivi. I titoli compaiono a turno; sostando su un bersaglio compare la descrizione breve;
il clic apre sull'immagine la scheda flottante con le pagine della parte; il clic su una pagina la apre con il menu del
gruppo fissato in orizzontale. In Chromium (si salta se Playwright o Chromium non ci sono)."""
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


def _apri(browser, base, larghezza=1366, altezza=800, tema=None, **kw):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza}, **kw)
    if tema:
        ctx.add_init_script(f"localStorage.setItem('tema', '{tema}')")
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.goto(base)
    pg.wait_for_function("getComputedStyle(document.getElementById('scena-home')).getPropertyValue('--sh-w') !== ''")
    return ctx, pg, errori


def test_scena_nella_finestra_e_solo_bersagli(browser, base):
    ctx, pg, errori = _apri(browser, base)
    q = pg.locator(".sh-quadro").bounding_box()
    # (23/11/2026) sta tutta nella finestra a pagina non scorsa, sotto titolo e testo, col rapporto del quadro (CSS, 16:9)
    assert q["width"] <= 1366 and q["y"] + q["height"] <= 800 + 1
    rapporto = pg.evaluate("(a => a[0] / (a[1] || 1))(getComputedStyle(document.querySelector('.sh-quadro')).aspectRatio.split('/').map(parseFloat))")
    assert abs(q["width"] / q["height"] - rapporto) < 0.01 and abs(rapporto - 16 / 9) < 0.01
    # il testo di presentazione va su tutta la larghezza della colonna
    sotto, home = pg.locator(".home-sotto").bounding_box(), pg.locator(".home-apertura").bounding_box()
    assert sotto["width"] >= home["width"] - 2
    # titoli dei bersagli: argomenti del menu, mai gli oggetti del disegno
    titoli = pg.evaluate("[...document.querySelectorAll('.sh-titolo')].map(t => t.textContent)")
    assert "Pompe di calore" in titoli and not any(" sul " in t or " sulla " in t for t in titoli), titoli
    assert pg.evaluate("document.documentElement.scrollWidth") <= 1366
    # niente animazioni; il fondale del tema scuro si carica
    assert pg.evaluate("document.getAnimations().filter(a => a.playState === 'running').length") == 0
    assert pg.evaluate("(i => i.complete && i.naturalWidth > 0)(document.querySelector('.sh-fondo-scuro'))")
    # solo i 16 bersagli più il collegamento verde al file per gli LLM (24/11/2026) sono attivi (nessuna sagoma .parte)
    assert pg.locator(".sh-punto").count() == 17 and pg.locator("a.sh-punto.sh-file[href='EUGENIO_PER_AGENTI.md']").count() == 1 and pg.locator("#scena-home .parte").count() == 0
    # all'inizio solo «Da dove cominciare», con un pulsante per gruppo
    assert pg.locator(".home-scheda:visible").count() == 1 and pg.locator("#home-scelte button").count() == 7
    assert not errori, errori
    ctx.close()


def test_titoli_a_turno(browser, base):
    ctx, pg, errori = _apri(browser, base)
    visti = set()
    for _ in range(10):
        pg.wait_for_timeout(500)
        accesi = pg.evaluate("[...document.querySelectorAll('.sh-punto.sh-acceso')].map(p => p.dataset.parte)")
        assert len(accesi) <= 1
        visti.update(accesi)
    assert len(visti) >= 2
    assert not errori, errori
    ctx.close()


def test_descrizione_scheda_flottante_e_menu_fissato(browser, base):
    ctx, pg, errori = _apri(browser, base)
    # sostando sull'UTA compare la descrizione breve, sull'immagine
    pg.hover('.sh-punto[data-parte="uta"]')
    pg.wait_for_selector("#sh-descr", state="visible")
    assert "trattamento aria" in pg.locator("#sh-descr").inner_text().lower()
    # il cogeneratore è «prossimamente»
    pg.hover('.sh-punto[data-parte="cogenerazione"]')
    pg.wait_for_function("document.querySelector('#sh-descr').innerText.toLowerCase().includes('prossimamente')")
    # clic sul traliccio: scheda flottante dentro l'immagine, con le pagine della rete elettrica
    pg.click('.sh-punto[data-parte="traliccio"]')
    q, s = pg.locator(".sh-quadro").bounding_box(), pg.locator("#sh-scheda").bounding_box()
    assert s["x"] >= q["x"] and s["y"] >= q["y"] and s["x"] + s["width"] <= q["x"] + q["width"] + 1
    voci = pg.locator("#sh-scheda li a").all_inner_texts()
    assert any("Carichi elettrici" in v for v in voci) and any("Stato della rete elettrica" in v for v in voci)
    assert pg.locator('.sh-punto[data-parte="traliccio"]').get_attribute("aria-expanded") == "true"
    pg.keyboard.press("Escape")
    assert pg.locator("#sh-scheda").is_hidden()
    # da tastiera: Invio sul recupero apre la sua scheda; la pagina si apre con il menu del gruppo fissato
    pg.locator('.sh-punto[data-parte="recupero"]').focus()
    pg.keyboard.press("Enter")
    assert pg.locator("#sh-scheda").is_visible()
    pg.locator('#sh-scheda a[href="aria-freecooling.html"]').click()
    pg.wait_for_url("**/aria-freecooling.html")
    pg.wait_for_selector("nav.riga-fissata ul.riga-voci a[href='aria-freecooling.html']")
    assert pg.evaluate("document.documentElement.dataset.menuFissato") == "aria"
    assert not errori, errori
    ctx.close()


def test_pagina_di_altro_gruppo_fissa_il_suo_menu(browser, base):
    """fv-cabine.html sta nel traliccio (Statistiche) ma il suo menu è Fotovoltaico."""
    ctx, pg, errori = _apri(browser, base)
    pg.click('.sh-punto[data-parte="traliccio"]')
    assert pg.locator('#sh-scheda a[href="fv-cabine.html"]').get_attribute("data-gruppo") == "fotovoltaico"
    assert not errori, errori
    ctx.close()


def test_tema_chiaro_e_vecchi_indirizzi(browser, base):
    ctx, pg, errori = _apri(browser, base, tema="light")
    assert pg.locator(".sh-fondo-chiaro").is_visible() and not pg.locator(".sh-fondo-scuro").is_visible()
    pg.click('.sh-punto[data-parte="fotovoltaico"]')
    assert pg.locator("#sh-scheda").is_visible()
    # i vecchi collegamenti di Previsioni (/?comune=…) passano a previsioni.html con le stesse scelte
    pg.goto(base + "?comune=040007&cosa=clima")
    pg.wait_for_url("**/previsioni.html?comune=040007*")
    assert not errori, errori
    ctx.close()


def test_telefono(browser, base):
    ctx, pg, errori = _apri(browser, base, larghezza=375, altezza=740, has_touch=True)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    pg.tap('.sh-punto[data-parte="territorio"]')
    # sul telefono la scheda sale dal fondo dello schermo, tutta visibile
    s = pg.locator("#sh-scheda").bounding_box()
    assert s["x"] >= 0 and s["x"] + s["width"] <= 375 and s["y"] >= 0 and s["y"] + s["height"] <= 740
    assert not errori, errori
    ctx.close()
