"""Statistiche › «Produzione e consumi di elettricità» (elettricita.html, elettricita.js; 20/11/2026, richiesta di Paolo).

Sui file: voce del menu (sperimentale), fonti, nessun collegamento per scaricare i dati di Terna (decisione di Paolo:
si scarica solo l'immagine della mappa), nessun dato di mercato.
In Chromium (si salta se Playwright o Chromium non ci sono), con i file della pagina costruiti da dati inventati
(fase 15, costruisci) e serviti al posto di dati/elettricita/: istogrammi nella mappa, clic sulla regione → province,
secondo clic → Italia, cambio di grandezza e di anno, burden sharing con gli obiettivi, niente scorrimento orizzontale a
375 px, nessun errore JavaScript.
"""
from __future__ import annotations

import functools
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
    assert t.count('href="elettricita.html"') == 2
    assert re.search(r'href="elettricita.html">Produzione e consumi di elettricità <span class="cantiere prova">sperimentale', t)
    s = (SITO / "elettricita.html").read_text(encoding="utf-8")
    assert '<p class="gruppo-servizio">Statistiche</p>' in s and "Servizio sperimentale non ancora verificato" in s
    assert s.count('aria-current="page"') == 2 and "dati.terna.it" in s and "21 giugno 2024" in s
    assert re.search(r'<script src="rete\.js\?v=\d{8}[a-z]"></script>\s*<script src="elettricita\.js\?v=', s)
    js = (SITO / "elettricita.js").read_text(encoding="utf-8")
    for vietato in ("PUN", "TTF", "€/MWh", "pulsantiDati", ".csv", "xlsx"):
        assert vietato not in s + js, vietato
    assert "#elettricita" in s and 'id="elettricita"' in (SITO / "metodo.html").read_text(encoding="utf-8")


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
    from elettricita import costruisci as K
    import test_costruisci as T
    tmp = tmp_path_factory.mktemp("el")
    K.costruisci(T._raw(tmp), tmp / "out", SITO / "dati" / "mappa")
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


def _pagina(browser, base, dati, larghezza=1400, altezza=950):
    pg = browser.new_page(viewport={"width": larghezza, "height": altezza})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="no"))
    pg.route("**/dati/elettricita/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/elettricita/")[1].split("?")[0])))
    pg.goto(f"{base}/elettricita.html?vista=italia")
    pg.wait_for_function("() => window.EUGENIO_ELETTRICITA && window.EUGENIO_ELETTRICITA.stato.mappa && window.EUGENIO_ELETTRICITA.stato.mappa.getSource('el-barre')", timeout=20000)
    pg.wait_for_timeout(1500)
    return pg, errori


def test_pagina(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    n = pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.barre")
    assert n == 2                                               # Emilia-Romagna e Sardegna nei dati inventati
    assert pg.locator("#titolo-vista").inner_text() == "Italia"
    assert pg.locator("#tabella-elettricita tfoot th").inner_text() == "Italia"
    assert pg.locator("#scarica-mappa button, #scarica-mappa a").count() >= 1   # solo l'immagine
    # clic sulla regione (sotto la base del suo istogramma) → province; secondo clic → Italia
    p = pg.evaluate("""() => { const S = window.EUGENIO_ELETTRICITA.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon, r.lat]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y + 10]; }""")
    pg.mouse.click(*p)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1500)
    assert "Totale Emilia-Romagna" in pg.locator("#tabella-elettricita tfoot").inner_text()
    assert "Forlì-Cesena" in pg.locator("#tabella-elettricita tbody").inner_text()
    assert pg.locator("#grafico-province svg[role=img]").count() == 1
    p = pg.evaluate("""() => { const S = window.EUGENIO_ELETTRICITA.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon + 0.3, r.lat - 0.15]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y]; }""")
    pg.mouse.click(*p)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Italia'", timeout=10000)
    # carichi: per le province nessuna barra e la nota
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.click('[data-modo="richiesta"]')
    pg.wait_for_timeout(1500)
    assert pg.locator("#nota-province").is_visible() and "solo per regione" in pg.locator("#messaggio-mappa").inner_text()
    # burden sharing all'Italia: obiettivi della Tabella A
    pg.click("#torna-italia")
    pg.click('[data-modo="burden"]')
    pg.wait_for_timeout(1500)
    testo = pg.locator("#tabella-elettricita").inner_text()
    assert "Obiettivo 2030" in testo and "6.330" in testo and "6330" not in testo     # punto delle migliaia anche a 4 cifre
    assert pg.locator("#anno-scelto").inner_text() == "2021"
    assert errori == []


def test_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, 375, 800)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert errori == []
