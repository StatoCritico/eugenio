"""Statistiche › «Suolo e aree agricole» (suolo.html, suolo.js; 22/11/2026, richiesta di Paolo).

Sui file: voce del menu (sperimentale), fonti e licenze, nessun collegamento per scaricare i dati (si scarica solo
l'immagine della mappa), nessun dato di mercato, metodo in metodo.html#suolo.
In Chromium (si salta se Playwright o Chromium non ci sono), con i file della pagina costruiti dai campioni inventati della
fase 16 (fase16-suolo/tests/campioni.py: Bologna, Imola, Aggius; anni 2006, 2012, 2015) e serviti al posto di
dati/suolo/: istogrammi, regione → province, provincia → comuni colorati, Consumi e Colture, periodo con i due indicatori
anche da tastiera, collegamento salvabile, 375 px senza scorrimento orizzontale, nessun errore JavaScript.
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
sys.path.insert(0, str(QUI.parent / "fase16-suolo"))
sys.path.insert(0, str(QUI.parent / "fase16-suolo" / "tests"))
import costruisci_pagine as C  # noqa: E402

PRONTA = "() => window.EUGENIO_SUOLO && window.EUGENIO_SUOLO.stato.pronto"


def test_menu_e_pagina():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert t.count('href="suolo.html"') == 2
    assert re.search(r'href="suolo.html">Suolo e aree agricole <span class="cantiere prova">sperimentale', t)
    assert t.index('href="suolo.html"') > t.index('href="carichi.html"')
    s = (SITO / "suolo.html").read_text(encoding="utf-8")
    assert '<p class="gruppo-servizio">Statistiche</p>' in s and "Servizio sperimentale non ancora verificato" in s
    assert s.count('aria-current="page"') == 2 and "ISPRA/SNPA" in s and "ISTAT" in s and "Copernicus" in s and "CC BY" in s
    assert re.search(r'<script src="collegamento\.js\?v=\w+"></script>', s) and s.index("collegamento.js") < s.index("suolo.js")
    assert 'id="anno-inizio"' in s and 'id="anno-fine"' in s and 'aria-label="Anno iniziale del periodo"' in s
    js = (SITO / "suolo.js").read_text(encoding="utf-8")
    for vietato in ("PUN", "TTF", "€/MWh", "pulsantiDati", ".csv", "xlsx", "toLocaleString"):
        assert vietato not in s + js, vietato
    assert "#suolo" in s and 'id="suolo"' in (SITO / "metodo.html").read_text(encoding="utf-8")
    assert 'href="suolo.html"' in (SITO / "esempi.html").read_text(encoding="utf-8")


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
    pytest.importorskip("openpyxl")
    import campioni
    from suolo import costruisci as K
    tmp = tmp_path_factory.mktemp("suolo")
    K.costruisci(campioni.raw(tmp / "raw"), tmp / "out", SITO / "dati" / "mappa")
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


def _rotte(pg, dati):
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="no"))
    pg.route("**/dati/suolo/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/suolo/")[1].split("?")[0])))


def _pagina(browser, base, dati, larghezza=1400, altezza=950, query="vista=italia", contesto=None):
    vista = {"width": larghezza, "height": altezza}
    pg = contesto.new_page() if contesto else browser.new_page(viewport=vista)
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    _rotte(pg, dati)
    pg.goto(f"{base}/suolo.html?{query}")
    pg.wait_for_function(PRONTA, timeout=20000)
    pg.wait_for_timeout(1200)
    return pg, errori


def _stato(pg):
    return pg.evaluate("() => { const S = window.EUGENIO_SUOLO.stato; return {barre: S.barre, modo: S.modo, inizio: S.inizio, "
                       "fine: S.fine, regione: S.regione, provincia: S.provincia, comuni: S.comuniColorati || 0, unita: S.unita}; }")


def test_pagina(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    st = _stato(pg)
    assert st["barre"] == 2 and st["modo"] == "suolo" and st["inizio"] == st["fine"] == 2015   # ER e Sardegna, ultimo anno
    assert pg.locator("#titolo-vista").inner_text() == "Italia"
    assert pg.locator("#tabella-suolo tfoot th").inner_text() == "Italia"
    assert pg.locator("#scarica-mappa button, #scarica-mappa a").count() >= 1               # solo l'immagine
    assert "7.222 ha di suolo consumato" in pg.locator("#cifre-suolo").inner_text()          # 5.080 + 2.040,5 + 101,5
    # clic sulla regione (sotto la base del suo istogramma) → province; secondo clic → Italia
    p = pg.evaluate("""() => { const S = window.EUGENIO_SUOLO.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon, r.lat]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y + 10]; }""")
    pg.mouse.click(*p)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.wait_for_timeout(1200)
    assert "Totale Emilia-Romagna" in pg.locator("#tabella-suolo tfoot").inner_text()
    assert "Bologna" in pg.locator("#tabella-suolo tbody").inner_text()
    assert pg.locator("#grafico-province svg[role=img]").count() == 1 and pg.locator("#blocco-scelta-provincia").is_visible()
    # provincia dal menu: comuni colorati e tabella dei comuni
    pg.select_option("#provincia-suolo", "037")
    pg.wait_for_function("() => window.EUGENIO_SUOLO.stato.comuniColorati === 2", timeout=10000)
    assert "comuni della provincia di Bologna" in pg.locator("#titolo-tabella").inner_text()
    assert "Imola" in pg.locator("#tabella-suolo tbody").inner_text() and "provincia=037" in pg.url
    assert "% consumato" in pg.locator("#legenda-suolo").inner_text()
    # secondo clic sulla regione → Italia
    p = pg.evaluate("""() => { const S = window.EUGENIO_SUOLO.stato, m = S.mappa, r = S.it.regioni.find((x) => x.cod === '08');
      const q = m.project([r.lon + 0.3, r.lat - 0.15]), b = m.getCanvas().getBoundingClientRect(); return [q.x + b.x, q.y + b.y]; }""")
    pg.mouse.click(*p)
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Italia'", timeout=10000)
    assert _stato(pg)["provincia"] is None and _stato(pg)["comuni"] == 0
    # Consumi: colonna impilata e «di cui su suolo agricolo» (incrocio dei campioni per il 2015)
    pg.click('[data-modo="consumi"]')
    pg.wait_for_timeout(1200)
    tab = pg.locator("#tabella-suolo").inner_text()
    assert "Consumo lordo" in tab and "Di cui su suolo agricolo" in tab and "Cantieri" in tab
    assert pg.locator("#unita-suolo").is_hidden() and "2012–2015" in pg.locator("#periodo-scelto").inner_text()
    piede = pg.locator("#tabella-suolo tfoot").inner_text()
    assert "33" in piede and "10,5" in piede                                                # lordo 2012–2015; agricolo 4,5 + 6
    # Colture: famiglie, Sardegna solo regionale
    pg.click('[data-modo="colture"]')
    pg.wait_for_timeout(1000)
    assert "Prati permanenti e pascoli" in pg.locator("#tabella-suolo thead").inner_text()
    pg.evaluate("() => window.EUGENIO_SUOLO.scegliRegione('20')")
    pg.wait_for_timeout(1200)
    assert "solo il dato regionale" in pg.locator("#nota-vista").inner_text()
    assert errori == []


def test_periodo_con_la_tastiera_e_unita(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    # indicatore iniziale all'inizio con il tasto Home: periodo 2006–2015
    pg.focus("#anno-inizio")
    pg.keyboard.press("Home")
    pg.wait_for_timeout(1200)
    st = _stato(pg)
    assert (st["inizio"], st["fine"]) == (2006, 2015) and pg.locator("#periodo-scelto").inner_text() == "2006–2015"
    assert "Suolo consumato: variazione dal 2006" in pg.locator("#tabella-suolo thead").inner_text()
    assert "+122" in pg.locator("#tabella-suolo tfoot").inner_text()                       # 7.222 − 7.100
    assert pg.locator("#legenda-suolo").inner_text().count("trattino") == 1
    # l'indicatore finale non passa prima di quello iniziale: con Home tutti e due sul 2006
    pg.focus("#anno-fine")
    pg.keyboard.press("Home")
    pg.wait_for_timeout(800)
    assert (_stato(pg)["inizio"], _stato(pg)["fine"]) == (2006, 2006)
    pg.keyboard.press("End")
    pg.wait_for_timeout(800)
    assert (_stato(pg)["inizio"], _stato(pg)["fine"]) == (2006, 2015)
    # unità: % del territorio
    pg.click('[data-unita="pct"]')
    pg.wait_for_timeout(1000)
    assert "% del territorio" in pg.locator("#tabella-suolo thead").inner_text() and _stato(pg)["unita"] == "pct"
    # Consumi 2006–2015: somma dei due periodi (96 + 33 = 129 ha di consumo lordo), media annua nel riquadretto
    pg.click('[data-modo="consumi"]')
    pg.wait_for_timeout(1200)
    assert "129" in pg.locator("#tabella-suolo tfoot").inner_text()
    assert errori == []


def test_collegamento(browser, base, dati):
    pg, errori = _pagina(browser, base, dati)
    pg.click('[data-modo="consumi"]')
    pg.evaluate("() => window.EUGENIO_SUOLO.scegliRegione('08')")
    pg.wait_for_function("() => document.getElementById('titolo-vista').textContent === 'Emilia-Romagna'", timeout=10000)
    pg.evaluate("() => window.EUGENIO_SUOLO.periodo(2012, 2015)")
    pg.uncheck("#strato-fondo")
    pg.wait_for_timeout(1500)
    link = pg.input_value("#collegamento-indirizzo")
    for parte in ("regione=08", "modo=consumi", "inizio=2012", "fine=2015", "fondo=0"):
        assert parte in link, parte
    ctx = browser.new_context(viewport={"width": 1400, "height": 950})
    pg2, errori2 = _pagina(browser, base, dati, query=link.split("?", 1)[1], contesto=ctx)
    pg2.wait_for_timeout(1500)
    st = _stato(pg2)
    assert (st["regione"], st["modo"], st["inizio"], st["fine"]) == ("08", "consumi", 2012, 2015)
    assert pg2.get_attribute('[data-modo="consumi"]', "aria-pressed") == "true" and not pg2.is_checked("#strato-fondo")
    assert pg2.input_value("#collegamento-indirizzo") == link
    ctx.close()
    # provincia e unità
    pg.click('[data-modo="suolo"]')
    pg.click('[data-unita="m2ab"]')
    pg.select_option("#provincia-suolo", "037")
    pg.wait_for_timeout(1500)
    link = pg.input_value("#collegamento-indirizzo")
    assert "provincia=037" in link and "unita=m2ab" in link
    ctx = browser.new_context(viewport={"width": 1400, "height": 950})
    pg3, errori3 = _pagina(browser, base, dati, query=link.split("?", 1)[1], contesto=ctx)
    pg3.wait_for_function("() => window.EUGENIO_SUOLO.stato.comuniColorati === 2", timeout=10000)
    assert _stato(pg3)["unita"] == "m2ab" and pg3.input_value("#provincia-suolo") == "037"
    ctx.close()
    assert errori == [] and errori2 == [] and errori3 == []


def test_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, 375, 800)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    pg.click('[data-modo="consumi"]')
    pg.wait_for_timeout(800)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert errori == []


def test_senza_dati(browser, base, tmp_path):
    pg = browser.new_page(viewport={"width": 1200, "height": 900})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="no"))
    pg.route("**/dati/suolo/**", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(f"{base}/suolo.html")
    pg.wait_for_function(PRONTA, timeout=20000)
    assert "non sono ancora disponibili" in pg.locator("#messaggio-mappa").inner_text() and errori == []
