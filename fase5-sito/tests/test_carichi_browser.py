"""Statistiche › «Carichi elettrici» (carichi.html, carichi.js; 20/11/2026, richiesta di Paolo).

Sui file: voce del menu (sperimentale), fonti, mappa delle zone di mercato, nessun collegamento per scaricare i dati di
Terna (decisione di Paolo), nessun dato del GME.
In Chromium (si salta se Playwright o Chromium non ci sono), con i file della pagina costruiti da dati inventati
(fase 15, carichi.costruisci_carichi) e serviti al posto di dati/carichi/: i tre grafici, la zona dalla piccola mappa
(secondo clic → Italia) con la nota sulle fonti, ore e quarti d'ora, periodo a mano, scelte nell'indirizzo, zoom con la
rotella e vista iniziale col doppio clic, zoom nel riquadro grande, niente scorrimento orizzontale a 375 px, nessun
errore JavaScript.
"""
from __future__ import annotations

import functools
import json
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
sys.path.insert(0, str(QUI))
sys.path.insert(0, str(QUI.parent / "fase15-elettricita"))
sys.path.insert(0, str(QUI.parent / "fase15-elettricita" / "tests"))
import costruisci_pagine as C  # noqa: E402


def test_menu_e_pagina():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert t.count('href="carichi.html"') == 2
    assert re.search(r'href="carichi.html">Carichi elettrici <span class="cantiere prova">sperimentale', t)
    assert t.index('href="carichi.html"') > t.index('href="elettricita.html"')        # dopo «Produzione e consumi»
    s = (SITO / "carichi.html").read_text(encoding="utf-8")
    assert '<p class="gruppo-servizio">Statistiche</p>' in s and "Servizio sperimentale non ancora verificato" in s
    assert s.count('aria-current="page"') == 2 and "dati.terna.it" in s and "Come leggere i grafici" in s
    assert re.search(r'<script src="minimappa\.js\?v=\d{8}[a-z]"></script>\s*<script src="carichi\.js\?v=', s)
    assert 'class="mappa ' not in s and "mappa-area" not in s                          # niente mappa grande
    js = (SITO / "carichi.js").read_text(encoding="utf-8")
    for vietato in ("PUN", "TTF", "€/MWh", ".csv", "xlsx", " download", "Blob("):
        assert vietato not in s + js, vietato
    assert "#carichi" in s and 'id="carichi"' in (SITO / "metodo.html").read_text(encoding="utf-8")
    z = json.loads((SITO / "dati" / "mappa" / "zone.json").read_text(encoding="utf-8"))
    assert [x["id"] for x in z["zone"]] == ["NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"]
    assert sorted(c for x in z["zone"] for c in x["regioni"]) == [f"{i:02d}" for i in range(1, 21)]
    assert "fase5-sito/sito/dati/carichi/" in (QUI.parent / ".gitignore").read_text(encoding="utf-8")


class _Zitto(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Zitto, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="module")
def dati(tmp_path_factory):
    from elettricita import carichi as K
    import test_carichi as T
    tmp = tmp_path_factory.mktemp("car")
    K.costruisci_carichi(T._archivio(tmp), tmp / "out")
    return tmp / "out"


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        except Exception as e:  # pragma: no cover
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


PRONTO = "() => document.getElementById('stato-carichi').textContent.startsWith('Dati')"


def _pagina(browser, base, dati, query="", larghezza=1400, altezza=950):
    pg = browser.new_page(viewport={"width": larghezza, "height": altezza})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/dati/carichi/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/carichi/")[1].split("?")[0])))
    pg.goto(f"{base}/carichi.html{query}")
    pg.wait_for_function(PRONTO, timeout=20000)
    pg.wait_for_selector("#minimappa-zone path[data-zona]")
    pg.wait_for_timeout(300)
    return pg, errori


def _vista(pg, box):
    return pg.evaluate(f"() => document.querySelector('{box} svg.zoom-proprio').getAttribute('aria-label') && "
                       f"[...document.querySelectorAll('{box} svg.zoom-proprio text')].map((t) => t.textContent).join('|')")


def test_pagina(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    # predefinito: ultimi 12 mesi (qui tutti i dati inventati, settembre e ottobre 2026), quarti d'ora, Italia
    assert "da=2026-09-01" in pg.url and "a=2026-10-31" in pg.url and "passo=15" in pg.url and "zona=" not in pg.url
    assert pg.locator("#carichi-quarti").is_checked() and pg.locator("#zona-scelta").inner_text() == "Italia"
    for g in ("#grafico-profilo", "#grafico-durata", "#grafico-fonti"):
        assert pg.locator(f"{g} svg.zoom-proprio").count() == 1 and pg.locator(f"{g} .grafico-apri").count() == 1
    assert pg.locator("#grafico-fonti svg.zoom-proprio path[fill='#f7cb15']").count() == 1     # fotovoltaico
    assert pg.locator("#nota-zona-fonti").is_hidden()
    assert "Quarti d'ora" in pg.locator("#riepilogo-carichi").inner_text() and "5860" in pg.locator("#riepilogo-carichi").inner_text()
    # zona dalla piccola mappa, secondo clic → Italia
    pg.locator('#minimappa-zone path[data-zona="SICI"]').click()
    pg.wait_for_function("() => document.getElementById('zona-scelta').textContent === 'Sicilia'")
    pg.wait_for_function(PRONTO)
    assert "zona=SICI" in pg.url and pg.locator("#nota-zona-fonti").is_visible()
    assert pg.locator('#minimappa-zone path[data-zona="SICI"]').get_attribute("class") == "attiva"
    assert pg.locator("#titolo-profilo").inner_text() == "Profilo giornaliero – Sicilia"
    pg.locator('#minimappa-zone path[data-zona="SICI"]').click()
    pg.wait_for_function("() => document.getElementById('zona-scelta').textContent === 'Italia'")
    assert "zona=" not in pg.url
    # ore: la metà… un quarto dei punti; periodo a mano
    pg.locator("#carichi-quarti").uncheck()
    pg.wait_for_function(PRONTO)
    assert "passo=60" in pg.url and "Ore" in pg.locator("#riepilogo-carichi").inner_text()
    assert pg.evaluate("() => window.EUGENIO_CARICHI.stato.serie.T.length") == 61 * 24 + 1
    pg.fill("#carichi-da", "2026-10-25"); pg.dispatch_event("#carichi-da", "change")
    pg.fill("#carichi-a", "2026-10-25"); pg.dispatch_event("#carichi-a", "change")
    pg.wait_for_function("() => window.EUGENIO_CARICHI.stato.serie.T.length === 25")     # il giorno di 25 ore
    assert "da=2026-10-25" in pg.url and "a=2026-10-25" in pg.url
    pg.click("#ultimi-12")
    pg.wait_for_function("() => location.search.includes('da=2026-09-01')")
    # zoom con la rotella sul profilo, doppio clic = vista iniziale
    svg = pg.locator("#grafico-profilo svg.zoom-proprio")
    svg.scroll_into_view_if_needed()
    prima = _vista(pg, "#grafico-profilo")
    b = svg.bounding_box()
    pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    for _ in range(6):
        pg.mouse.wheel(0, -300)
    pg.wait_for_timeout(200)
    assert _vista(pg, "#grafico-profilo") != prima
    assert pg.evaluate("() => window.EUGENIO_CARICHI.stato.grafici.profilo.vista !== null")
    pg.mouse.move(b["x"] + b["width"] / 2 + 30, b["y"] + b["height"] / 2)
    assert pg.locator(".grafico-suggerimento").first.is_visible()
    pg.mouse.dblclick(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    pg.wait_for_timeout(200)
    assert _vista(pg, "#grafico-profilo") == prima
    # riquadro grande: + ingrandisce col disegno proprio, «Vista iniziale» torna
    pg.locator("#grafico-fonti .grafico-apri").click()
    pg.wait_for_selector("dialog.riquadro-grafico[open] svg.zoom-proprio")
    pg.keyboard.press("+"); pg.keyboard.press("+")
    pg.wait_for_timeout(200)
    assert pg.evaluate("() => window.EUGENIO_CARICHI.stato.grafici.fonti.vista !== null")
    vb = pg.locator("dialog svg.zoom-proprio").get_attribute("viewBox")
    assert vb.startswith("0 0 ")                                   # il viewBox non cambia: si ridisegnano i dati
    pg.click(".riquadro-vista")
    assert pg.evaluate("() => window.EUGENIO_CARICHI.stato.grafici.fonti.vista === null")
    pg.keyboard.press("Escape")
    assert errori == []


def test_indirizzo(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, "?zona=nord&da=2026-10-01&a=2026-10-10&passo=60")
    assert pg.locator("#zona-scelta").inner_text() == "Nord" and not pg.locator("#carichi-quarti").is_checked()
    assert pg.input_value("#carichi-da") == "2026-10-01" and pg.input_value("#carichi-a") == "2026-10-10"
    assert pg.evaluate("() => window.EUGENIO_CARICHI.stato.serie.T.length") == 10 * 24
    assert errori == []


def test_senza_dati(browser, base, tmp_path):
    pg = browser.new_page()
    pg.route("**/dati/carichi/**", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(f"{base}/carichi.html")
    pg.wait_for_function("() => document.querySelector('#stato-carichi.errore')")
    assert "non sono ancora disponibili" in pg.locator("#stato-carichi").inner_text()


def test_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, "", 375, 800)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert errori == []
