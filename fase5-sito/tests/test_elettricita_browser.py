"""Statistiche › «Produzione e consumi di elettricità» (elettricita.html, elettricita.js; 20/11/2026, richiesta di Paolo).

Sui file: voce del menu (sperimentale), fonti, nessun collegamento per scaricare i dati di Terna (decisione di Paolo:
si scarica solo l'immagine della mappa), nessun dato di mercato.
In Chromium (si salta se Playwright o Chromium non ci sono), con i file della pagina costruiti da dati inventati
(fase 15, costruisci) e serviti al posto di dati/elettricita/: istogrammi nella mappa, clic sulla regione → province,
secondo clic → Italia, cambio di grandezza e di anno, burden sharing con gli obiettivi, niente scorrimento orizzontale a
375 px, nessun errore JavaScript.
Emissioni (21/11/2026): selettore, anelli nella mappa, tre riquadri con i riferimenti MEF e ISPRA, righe delle zone di
mercato e totale Italia nella tabella, collegamento salvabile con la scelta.
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


def _pagina(browser, base, dati, larghezza=1400, altezza=950, query="vista=italia"):
    pg = browser.new_page(viewport={"width": larghezza, "height": altezza})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="no"))
    pg.route("**/dati/elettricita/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/elettricita/")[1].split("?")[0])))
    pg.goto(f"{base}/elettricita.html?{query}")
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


def test_emissioni(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    assert pg.locator('[data-modo="emissioni"]').is_visible()
    pg.click('[data-modo="emissioni"]')
    pg.wait_for_timeout(1500)
    # anelli: due regioni con la produzione nei dati inventati (Emilia-Romagna, Sardegna)
    st = pg.evaluate("() => { const S = window.EUGENIO_ELETTRICITA.stato; return { n: S.barre, anelli: S.anelli, anno: S.anno }; }")
    assert st == {"n": 2, "anelli": 2, "anno": 2021}
    assert "l'area cresce in proporzione alla produzione" in pg.locator("#legenda-elettricita").inner_text()
    # tre riquadri con i valori nazionali e i riferimenti (MEF 0,187 tep/MWh; ISPRA 2021)
    rq = pg.locator("#riquadri-emissioni")
    assert rq.is_visible() and rq.locator(".cifra").count() == 3
    testo = rq.inner_text()
    assert "Valori nazionali – 2021" in testo and "0,187 tep/MWh" in testo and "ISPRA 2021" in testo and "430/2026" in testo
    # fattore medio Italia 2021: 630 kt / 2250 GWh = 0,280; termoelettrico 630 / 1400 = 0,450
    assert rq.locator('[data-cifra="medio"] b').inner_text().startswith("0,280")
    assert rq.locator('[data-cifra="termo"] b').inner_text().startswith("0,450")
    # tabella: regioni, 7 righe di zona di mercato, totale Italia
    tab = pg.locator("#tabella-elettricita")
    assert tab.locator("tr.riga-zona").count() == 7 and "Zona Nord" in tab.inner_text() and "Sardegna (regione e zona)" in tab.inner_text()
    assert tab.locator("tfoot th").inner_text() == "Italia" and "Fattore medio" in tab.locator("thead").inner_text()
    assert pg.locator("#grafico-andamento svg[role=img]").count() == 1
    # regione scelta: anelli per provincia, fattori regionali, tabella sempre per regione con la riga scelta
    pg.evaluate("() => window.EUGENIO_ELETTRICITA.scegliRegione('08')")
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1500)
    assert pg.evaluate("() => window.EUGENIO_ELETTRICITA.stato.barre") >= 1
    assert "Emilia-Romagna:" in rq.inner_text() and tab.locator("tr.scelta").count() == 1
    assert "solo per regione" in pg.locator("#legenda-elettricita").inner_text()
    # collegamento: la scelta «emissioni» e l'anno vanno nell'indirizzo e si ripristinano
    pg.eval_on_selector("#anno-elettricita", "c => { c.value = 0; c.dispatchEvent(new Event('input', {bubbles: true})); c.dispatchEvent(new Event('change', {bubbles: true})); }")
    pg.wait_for_timeout(900)
    link = pg.url
    assert "modo=emissioni" in link and "anno=2020" in link and "regione=08" in link
    assert errori == []
    pg2, errori2 = _pagina(browser, base, dati, query=link.split("?", 1)[1])
    pg2.wait_for_function("() => window.EUGENIO_ELETTRICITA.stato.pronto", timeout=20000)
    pg2.wait_for_timeout(1000)
    assert pg2.get_attribute('[data-modo="emissioni"]', "aria-pressed") == "true"
    assert pg2.inner_text("#anno-scelto") == "2020" and "Valori nazionali – 2020" in pg2.locator("#riquadri-emissioni").inner_text()
    assert errori2 == []


def test_emissioni_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, 375, 800, query="vista=italia&modo=emissioni")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert pg.locator("#riquadri-emissioni .cifra").count() == 3
    assert errori == []
