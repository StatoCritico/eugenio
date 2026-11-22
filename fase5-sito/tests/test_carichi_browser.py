"""Statistiche › «Carichi elettrici» (carichi.html, carichi.js; 20/11/2026, richiesta di Paolo).

Sui file: voce del menu (sperimentale), fonti, mappa delle zone di mercato, nessun collegamento per scaricare i dati di
Terna (decisione di Paolo), nessun dato del GME.
In Chromium (si salta se Playwright o Chromium non ci sono), con i file della pagina costruiti da dati inventati
(fase 15, carichi.costruisci_carichi) e serviti al posto di dati/carichi/: i tre grafici, la zona dalla piccola mappa
(secondo clic → Italia) con la nota sulle fonti, ore e quarti d'ora, periodo a mano, scelte nell'indirizzo, zoom con la
rotella e vista iniziale col doppio clic, zoom nel riquadro grande, niente scorrimento orizzontale a 375 px, nessun
errore JavaScript. (22/11/2026) Potenza per fonte in MW: stessa vista del grafico al 100 %, pulsanti della finestra,
cursore «Sposta di un mese», caselle per fonte, fonti spente col colore dello sfondo (tema scuro, chiaro, riquadro).
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
    # predefinito: ultimi 12 mesi (qui tutti i dati inventati, settembre e ottobre 2026), quarti d'ora, Italia; (21/11/2026)
    # date già scritte nelle caselle, quarti d'ora e Italia non scritti nell'indirizzo
    assert "da=2026-09-01" in pg.url and "a=2026-10-31" in pg.url and "passo=" not in pg.url and "zona=" not in pg.url
    assert pg.input_value("#carichi-da") == "2026-09-01" and pg.input_value("#carichi-a") == "2026-10-31"
    assert pg.locator("#carichi-quarti").is_checked() and pg.input_value("#carichi-zona") == "ITA"
    assert pg.locator(".comandi-carichi").first.is_visible() and pg.locator(".carichi-sezione").first.is_visible()
    for g in ("#grafico-profilo", "#grafico-durata", "#grafico-fonti"):
        assert pg.locator(f"{g} svg.zoom-proprio").count() == 1 and pg.locator(f"{g} .grafico-apri").count() == 1
    assert pg.locator("#grafico-fonti svg.zoom-proprio path[fill='#f7cb15']").count() == 1     # fotovoltaico
    assert pg.locator("#nota-zona-fonti").is_hidden()
    riep = pg.locator("#riepilogo-carichi").inner_text()
    assert "Quarti d'ora" in riep and "5.860" in riep and "5860" not in riep      # punto delle migliaia anche a 4 cifre
    assi = pg.evaluate("() => [...document.querySelectorAll('#grafico-durata svg text')].map((t) => t.textContent)")
    assert "1.000 h" in assi and "1000 h" not in assi                                    # anche sull'asse delle ore
    # zona dalla piccola mappa, secondo clic → Italia
    pg.locator('#minimappa-zone path[data-zona="SICI"]').click()
    pg.wait_for_function("() => document.getElementById('carichi-zona').value === 'SICI'")
    pg.wait_for_function(PRONTO)
    assert "zona=SICI" in pg.url and pg.locator("#nota-zona-fonti").is_visible()
    assert pg.locator('#minimappa-zone path[data-zona="SICI"]').get_attribute("class").split() == ["attiva", "meta-tutte"]
    assert "zona2=SICI" in pg.url and pg.input_value("#carichi-zona-2") == "SICI"          # la mappa vale per le due metà
    assert pg.locator("#titolo-profilo").inner_text() == "Profilo giornaliero – Sicilia"
    pg.locator('#minimappa-zone path[data-zona="SICI"]').click()
    pg.wait_for_function("() => document.getElementById('carichi-zona').value === 'ITA'")
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
    assert pg.input_value("#carichi-zona") == "NORD" and not pg.locator("#carichi-quarti").is_checked()
    assert pg.input_value("#carichi-da") == "2026-10-01" and pg.input_value("#carichi-a") == "2026-10-10"
    assert pg.evaluate("() => window.EUGENIO_CARICHI.stato.serie.T.length") == 10 * 24
    assert errori == []
    # collegamenti salvati prima del 21/11/2026 con passo=15: quarti d'ora, e l'indirizzo perde il passo predefinito
    pg, errori = _pagina(browser, base, dati, "?da=2026-10-01&a=2026-10-02&passo=15")
    assert pg.locator("#carichi-quarti").is_checked() and pg.evaluate("() => window.EUGENIO_CARICHI.stato.serie.T.length") == 2 * 96
    assert "passo=" not in pg.url and "da=2026-10-01" in pg.url
    # quarti d'ora rimessi a mano dopo le ore: il passo sparisce di nuovo dall'indirizzo
    pg.locator("#carichi-quarti").uncheck(); pg.wait_for_function(PRONTO)
    assert "passo=60" in pg.url
    pg.locator("#carichi-quarti").check(); pg.wait_for_function("() => !location.search.includes('passo=')")
    assert errori == []


def test_senza_dati(browser, base, tmp_path):
    pg = browser.new_page()
    pg.route("**/dati/carichi/**", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(f"{base}/carichi.html")
    pg.wait_for_function("() => document.querySelector('#stato-carichi.errore')")
    assert "non sono ancora disponibili" in pg.locator("#stato-carichi").inner_text()
    # (21/11/2026, Paolo) senza dati niente titoli di sezioni vuote né comandi: resta solo il messaggio
    assert pg.locator("#stato-carichi").is_visible()
    assert pg.locator(".comandi-carichi").is_hidden() and pg.locator("#minimappa-zone").is_hidden()
    for sezione in ("#titolo-riepilogo", "#titolo-profilo", "#titolo-durata", "#titolo-fonti", "#titolo-regole"):
        assert pg.locator(sezione).is_hidden(), sezione


def test_telefono(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, "", 375, 800)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assert errori == []


# ---------------------------------------------------------------------------------------------- potenza per fonte (22/11/2026)
def _viste(pg):
    return pg.evaluate("() => { const g = window.EUGENIO_CARICHI.stato.grafici; return [g.assoluti.vista, g.fonti.vista]; }")


def _premuto(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#carichi-finestre [aria-pressed=true]')].map((b) => b.dataset.finestra)")


def test_potenza_per_fonte_e_finestra(browser, base, dati):
    """(22/11/2026, Paolo) grafico in MW prima di quello al 100 %, stessa vista per i due, pulsanti della finestra
    dall'ultimo giorno con i dati, cursore di un mese a scatto, finestra nell'indirizzo solo se non è tutto il periodo."""
    pg, errori = _pagina(browser, base, dati)
    s = (SITO / "carichi.html").read_text(encoding="utf-8")
    assert s.index('id="grafico-assoluti"') < s.index('id="grafico-fonti"')
    assert pg.locator("#grafico-assoluti svg.zoom-proprio path[data-fonte='fv'][fill='#f7cb15']").count() == 1
    assert pg.locator("#grafico-assoluti .grafico-apri").count() == 1
    assi = pg.evaluate("() => [...document.querySelectorAll('#grafico-assoluti svg text')].map((t) => t.textContent)")
    assert "MW" in assi
    # tutto il periodo (qui = tutto l'archivio di prova, due mesi): anche «Ultimi 3 mesi» e «Ultimo anno» coincidono
    assert _premuto(pg) == ["trimestre", "anno", "tutto"] and pg.locator("#carichi-scorri").is_disabled() and "finestra=" not in pg.url
    # Ultimo mese: dal 1° al 31 ottobre (ultimo giorno con i dati), uguale nei due grafici
    pg.click("[data-finestra=mese]")
    pg.wait_for_function("() => location.search.includes('finestra=')")
    a, b = _viste(pg)
    assert a is not None and a == b
    assert "finestra=2026-10-01_2026-10-31" in pg.url and _premuto(pg) == ["mese"]
    assert pg.locator("#carichi-scorri-testo").inner_text() == "dal 1 ott 2026 al 31 ott 2026"
    assert pg.locator("#carichi-scorri").is_enabled() and pg.get_attribute("#carichi-scorri", "max") == "1"
    assert pg.input_value("#carichi-scorri") == "1"
    # cursore: un mese indietro (anche con la tastiera)
    pg.focus("#carichi-scorri"); pg.keyboard.press("ArrowLeft")
    pg.wait_for_function("() => location.search.includes('finestra=2026-09-01_')")
    assert pg.input_value("#carichi-scorri") == "0" and _premuto(pg) == []
    assert pg.locator("#carichi-scorri-testo").inner_text().startswith("dal 1 set 2026")
    a, b = _viste(pg)
    assert a == b
    pg.keyboard.press("ArrowRight")
    pg.wait_for_function("() => location.search.includes('finestra=2026-10-01_2026-10-31')")
    # Ieri e Ultima settimana; pulsante dalla tastiera
    pg.focus("[data-finestra=giorno]"); pg.keyboard.press("Enter")
    pg.wait_for_function("() => location.search.includes('finestra=2026-10-31_2026-10-31')")
    pg.click("[data-finestra=settimana]")
    pg.wait_for_function("() => location.search.includes('finestra=2026-10-25_2026-10-31')")
    assert _premuto(pg) == ["settimana"]
    # Ultimo anno e Tutto il periodo = periodo intero (qui due mesi): niente finestra nell'indirizzo
    pg.click("[data-finestra=anno]")
    pg.wait_for_function("() => !location.search.includes('finestra=')")
    assert _viste(pg) == [None, None] and "tutto" in _premuto(pg)
    # rotella sul grafico in MW: anche il grafico al 100 % si ingrandisce; doppio clic sul secondo: tutti e due tornano
    svg = pg.locator("#grafico-assoluti svg.zoom-proprio")
    svg.scroll_into_view_if_needed()
    bb = svg.bounding_box()
    pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
    for _ in range(5):
        pg.mouse.wheel(0, -300)
    pg.wait_for_timeout(200)
    a, b = _viste(pg)
    assert a is not None and a == b
    pg.wait_for_function("() => /finestra=\\d{4}-\\d\\d-\\d\\dT\\d{4}_/.test(location.search)")   # con l'ora
    pg.mouse.move(bb["x"] + bb["width"] / 2 + 20, bb["y"] + bb["height"] / 2)
    sugg = pg.locator(".grafico-suggerimento").first.inner_text()
    assert "Fotovoltaico:" in sugg and "MW" in sugg and "fonti accese, in tutto" in sugg
    f = pg.locator("#grafico-fonti svg.zoom-proprio")
    f.scroll_into_view_if_needed()
    fb = f.bounding_box()
    pg.mouse.dblclick(fb["x"] + fb["width"] / 2, fb["y"] + fb["height"] / 2)
    pg.wait_for_function("() => !location.search.includes('finestra=')")
    assert _viste(pg) == [None, None]
    assert errori == []


def test_fonti_spente(browser, base, dati):
    """(22/11/2026, Paolo) caselle per fonte sotto il grafico in MW, «Accendi tutte» e «Spegni tutte»; nel grafico al
    100 % le fonti spente restano al loro posto col colore dello sfondo (tema scuro e chiaro, anche nel riquadro)."""
    pg, errori = _pagina(browser, base, dati)
    caselle = pg.locator("#grafico-assoluti input[data-fonte]")
    assert caselle.count() == 7
    energia = pg.locator('#grafico-assoluti [data-energia="fv"]').inner_text()
    assert re.fullmatch(r"· [\d.]+(,\d+)? GWh", energia.strip()), energia
    pg.locator('#grafico-assoluti input[data-fonte="fv"]').uncheck()
    pg.wait_for_function("() => location.search.includes('spente=fv')")
    assert pg.locator("#grafico-assoluti svg path[data-fonte='fv']").count() == 0
    spenta = pg.locator("#grafico-fonti svg path[data-fonte='fv']")
    assert spenta.count() == 1 and spenta.get_attribute("class") == "fonte-spenta"
    assert pg.locator("#grafico-fonti [data-fonte-legenda='fv']").get_attribute("class").endswith("spenta")
    # colore dello sfondo della pagina (tema scuro)
    def sfondo_ok(sel, dove="document.body"):
        return pg.evaluate(f"""() => {{ const p = document.querySelector("{sel}"), d = document.createElement('div');
            d.style.background = 'var(--carta)'; {dove}.appendChild(d);
            const c = getComputedStyle(d).backgroundColor; d.remove(); return [getComputedStyle(p).fill, c]; }}""")
    f, c = sfondo_ok("#grafico-fonti svg path.fonte-spenta")
    assert f == c, (f, c)
    # Spegni tutte, Accendi tutte (dalla tastiera)
    pg.focus("#grafico-assoluti [data-tutte='0']"); pg.keyboard.press("Enter")
    pg.wait_for_function("() => location.search.includes('spente=termo%2Cbio')")
    assert pg.locator("#grafico-assoluti input[data-fonte]:checked").count() == 0
    assert "Nessuna fonte accesa" in pg.locator("#grafico-assoluti svg.zoom-proprio").text_content()
    assert pg.locator("#grafico-fonti svg path.fonte-spenta").count() == pg.locator("#grafico-fonti svg path[data-fonte]").count()
    pg.click("#grafico-assoluti [data-tutte='1']")
    pg.wait_for_function("() => !location.search.includes('spente=')")
    assert pg.locator("#grafico-assoluti input[data-fonte]:checked").count() == 7
    # casella nel riquadro grande: le caselle della pagina seguono; spenta col colore del riquadro (--foglio)
    pg.locator("#grafico-assoluti .grafico-apri").click()
    pg.wait_for_selector("dialog.riquadro-grafico[open] input[data-fonte='eol']")
    pg.locator("dialog input[data-fonte='eol']").uncheck()
    assert not pg.locator('#grafico-assoluti input[data-fonte="eol"]').is_checked()
    assert pg.locator("dialog svg path[data-fonte='eol']").count() == 0
    pg.keyboard.press("Escape")
    pg.locator("#grafico-fonti .grafico-apri").click()
    pg.wait_for_selector("dialog.riquadro-grafico[open] svg path.fonte-spenta")
    f, c = pg.evaluate("""() => { const p = document.querySelector('dialog svg path.fonte-spenta'), d = document.createElement('div');
        d.style.background = 'var(--foglio)'; document.querySelector('dialog .riquadro-finestra').appendChild(d);
        const c = getComputedStyle(d).backgroundColor; d.remove(); return [getComputedStyle(p).fill, c]; }""")
    assert f == c, (f, c)
    pg.keyboard.press("Escape")
    assert errori == []
    # tema chiaro, aperto da un indirizzo con finestra e fonti spente
    ctx = browser.new_context(viewport={"width": 1200, "height": 900})
    ctx.add_init_script("localStorage.setItem('tema', 'light')")
    pg = ctx.new_page()
    err2 = []
    pg.on("pageerror", lambda e: err2.append(str(e)))
    pg.route("**/dati/carichi/**", lambda r: r.fulfill(path=str(dati / r.request.url.split("/dati/carichi/")[1].split("?")[0])))
    pg.goto(f"{base}/carichi.html?finestra=2026-10-10_2026-10-20&spente=saldo,nessuna,termo")
    pg.wait_for_function(PRONTO, timeout=20000)
    pg.wait_for_timeout(500)
    assert pg.evaluate("document.documentElement.dataset.theme") == "light"
    assert not pg.locator('#grafico-assoluti input[data-fonte="saldo"]').is_checked()
    assert not pg.locator('#grafico-assoluti input[data-fonte="termo"]').is_checked()
    assert pg.locator('#grafico-assoluti input[data-fonte="fv"]').is_checked()
    assert pg.locator("#carichi-scorri-testo").inner_text() == "dal 10 ott 2026 al 20 ott 2026"
    assert "finestra=2026-10-10_2026-10-20" in pg.url and "spente=termo%2Csaldo" in pg.url
    f, c = sfondo_ok("#grafico-fonti svg path.fonte-spenta")
    assert f == c and c != "rgba(0, 0, 0, 0)", (f, c)
    ctx.close()
    assert err2 == []


def test_telefono_fonti(browser, base, dati):
    pg, errori = _pagina(browser, base, dati, "?spente=fv", 375, 800)
    pg.click("[data-finestra=settimana]")
    pg.wait_for_function("() => location.search.includes('finestra=')")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 376
    assi = pg.evaluate("() => [...document.querySelectorAll('#grafico-assoluti svg text')].map((t) => t.textContent)")
    assert sum(1 for t in assi if re.fullmatch(r"\d+ ott", t)) >= 3                   # date sull'asse anche a 375 px
    assert errori == []


# ---------------------------------------------------------------------------------------------- due metà, anni, buchi (22/11/2026 b)
@pytest.fixture(scope="module")
def dati_anni(tmp_path_factory):
    """File della pagina scritti a mano: dicembre 2025 e gennaio 2026 a quarti d'ora, con il 14 e il 15 gennaio 2026
    senza dati (il buco visto durante lo scaricamento)."""
    import math
    out = tmp_path_factory.mktemp("car_anni")
    zone = {"NORD": .58, "CNOR": .08, "CSUD": .15, "SUD": .07, "CALA": .02, "SICI": .06, "SARD": .04}
    voci = [("termo", "Termoelettrico tradizionale", "#8a8f99"), ("bio", "Bioenergie", "#f0912a"),
            ("idro", "Idroelettrico (con i pompaggi)", "#7cc7e0"), ("geo", "Geotermico", "#d4561c"), ("eol", "Eolico", "#a9c641"),
            ("fv", "Fotovoltaico", "#f7cb15"), ("saldo", "Saldo con l'estero, pompaggi e accumuli (per differenza)", "#c7a0c0")]
    mesi = []
    for mese, inizio in (("2025-12", "2025-11-30T23:00:00Z"), ("2026-01", "2025-12-31T23:00:00Z")):
        n = 31 * 96
        car = {z: [] for z in ["ITA", *zone]}
        fon = {k: [] for k, _, _ in voci}
        for i in range(n):
            buco = mese == "2026-01" and 13 * 96 <= i < 15 * 96
            it = 30000 + 6000 * math.sin(i / 96 * 2 * math.pi)
            parti = {z: None if buco else int(it * q) for z, q in zone.items()}
            car["ITA"].append(None if buco else sum(parti.values()))
            for z, v in parti.items():
                car[z].append(v)
            fv = max(0, int(8000 * math.sin((i % 96 - 28) / 48 * math.pi)))
            valori = {"termo": 14000, "bio": 1500, "idro": 4000, "geo": 600, "eol": 3000, "fv": fv, "saldo": 3000}
            for k in fon:
                fon[k].append(None if buco else valori[k])
        (out / f"carico_{mese}.json").write_text(json.dumps({"mese": mese, "zone": car}), encoding="utf-8")
        (out / f"fonti_{mese}.json").write_text(json.dumps({"mese": mese, "voci": fon}), encoding="utf-8")
        mesi.append({"mese": mese, "inizio": inizio, "n": n, "completo": True, "ora_legale": [[0, 60]], "passo_carico": 15,
                     "fonti": True, "passo_fonti": 15, "rinnovabili": True, "scarto_italia_mw": 0})
    indice = {"fonte": "Terna (prova)", "fonte_generazione": "Terna (prova)", "aggiornato": "2026-02-01T06:00:00Z", "passo": 15,
              "zone": [{"id": "ITA", "nome": "Italia"}] + [{"id": z, "nome": n} for z, n in (
                  ("NORD", "Nord"), ("CNOR", "Centro-Nord"), ("CSUD", "Centro-Sud"), ("SUD", "Sud"), ("CALA", "Calabria"),
                  ("SICI", "Sicilia"), ("SARD", "Sardegna"))],
              "voci": [{"id": k, "nome": n, "colore": c} for k, n, c in voci], "mesi": mesi}
    (out / "indice.json").write_text(json.dumps(indice), encoding="utf-8")
    return out


ENTRAMBE = ("() => ['stato-carichi', 'stato-carichi-2'].every((id) => document.getElementById(id).textContent.startsWith('Dati'))")


def _due(browser, base, dati, query="", larghezza=1400, altezza=950):
    pg, errori = _pagina(browser, base, dati, query, larghezza, altezza)
    pg.wait_for_function(ENTRAMBE, timeout=20000)
    return pg, errori


def test_due_meta_zone_e_mappa(browser, base, dati):
    """(22/11/2026 b, Paolo) due metà con divisore e barre di scorrimento separate; zona da una casella a discesa per
    ogni metà; la piccola mappa sceglie la zona per tutte e due ed evidenzia le zone delle due metà con due stili."""
    pg, errori = _due(browser, base, dati)
    meta = pg.locator("#carichi-meta")
    assert meta.locator(":scope > .divisore[role=separator]").count() == 1
    for sel in ("#carichi-lato", "#carichi-lato-2"):
        assert pg.eval_on_selector(sel, "(e) => getComputedStyle(e).overflowY") == "auto"
    for id_ in ("carichi-zona", "carichi-da", "carichi-anno", "carichi-scorri", "grafico-profilo", "grafico-assoluti", "grafico-fonti"):
        assert pg.locator(f"#{id_}-2").count() == 1, id_
    assert pg.locator("#carichi-lato-2 label[for='carichi-da-2']").count() == 1
    assert pg.locator("#grafico-fonti-2 svg.zoom-proprio").count() == 1
    opzioni = pg.eval_on_selector("#carichi-zona", "(s) => [...s.options].map((o) => o.value)")
    assert opzioni == ["ITA", "NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"]
    # zone diverse dalle caselle: due stili sulla mappa, spiegati sotto
    pg.select_option("#carichi-zona-2", "CALA")
    pg.wait_for_function("() => location.search.includes('zona2=CALA')")
    pg.select_option("#carichi-zona", "NORD")
    pg.wait_for_function("() => location.search.includes('zona=NORD')")
    pg.wait_for_function(ENTRAMBE)
    classe = lambda z: (pg.locator(f'#minimappa-zone path[data-zona="{z}"]').get_attribute("class") or "").split()
    assert "meta-sx" in classe("NORD") and "meta-dx" in classe("CALA") and "attiva" not in classe("SICI")
    leg = pg.locator("#minimappa-legenda").inner_text()
    assert "Sinistra: Nord" in leg and "Destra: Calabria" in leg
    assert pg.locator("#titolo-profilo").inner_text() == "Profilo giornaliero – Nord"
    assert pg.locator("#titolo-profilo-2").inner_text() == "Profilo giornaliero – Calabria"
    assert pg.eval_on_selector('#minimappa-zone path[data-zona="CALA"]', "(p) => getComputedStyle(p).strokeDasharray") != "none"
    # clic sulla mappa: la zona in tutte e due; secondo clic: Italia in tutte e due
    pg.locator('#minimappa-zone path[data-zona="SARD"]').click()
    pg.wait_for_function("() => location.search.includes('zona=SARD') && location.search.includes('zona2=SARD')")
    assert classe("SARD") == ["attiva", "meta-tutte"] and "Tutte e due le metà: Sardegna" in pg.locator("#minimappa-legenda").inner_text()
    pg.locator('#minimappa-zone path[data-zona="SARD"]').click()
    pg.wait_for_function("() => !location.search.includes('zona')")
    assert pg.input_value("#carichi-zona") == "ITA" and pg.input_value("#carichi-zona-2") == "ITA"
    # periodi diversi: la metà destra non tocca la sinistra
    pg.fill("#carichi-da-2", "2026-10-01"); pg.dispatch_event("#carichi-da-2", "change")
    pg.wait_for_function("() => location.search.includes('da2=2026-10-01')")
    assert pg.input_value("#carichi-da") == "2026-09-01"
    # divisore dalla tastiera
    prima = pg.eval_on_selector("#carichi-lato-2", "(e) => e.offsetWidth")
    pg.focus("#carichi-meta > .divisore"); pg.keyboard.press("ArrowLeft"); pg.keyboard.press("ArrowLeft")
    assert pg.eval_on_selector("#carichi-lato-2", "(e) => e.offsetWidth") > prima
    assert errori == []


def test_anni_e_archivio(browser, base, dati_anni):
    """(22/11/2026 b, Paolo) anno intero col menu e con «‹ ›»; pulsanti e cursore scorrono su tutto l'archivio e spostano
    il periodo Dal/al quando la finestra ne esce."""
    pg, errori = _due(browser, base, dati_anni)
    assert pg.input_value("#carichi-da") == "2025-12-01" and pg.input_value("#carichi-a") == "2026-01-31"
    assert pg.eval_on_selector("#carichi-anno", "(s) => [...s.options].map((o) => o.value)") == ["", "2025", "2026"]
    assert pg.input_value("#carichi-anno") == ""
    pg.click("#anno-prima")
    pg.wait_for_function("() => location.search.includes('a=2025-12-31')")
    assert pg.input_value("#carichi-da") == "2025-12-01" and pg.input_value("#carichi-anno") == "2025"
    assert pg.locator("#anno-prima").is_disabled() and pg.locator("#anno-dopo").is_enabled()
    pg.wait_for_function(PRONTO)
    # cursore su tutto l'archivio: con dicembre scelto si va a gennaio (il periodo si sposta di un mese)
    assert pg.locator("#carichi-scorri").is_enabled() and pg.input_value("#carichi-scorri") == "0"
    pg.focus("#carichi-scorri"); pg.keyboard.press("ArrowRight")
    pg.wait_for_function("() => location.search.includes('a=2026-01-31')")
    assert pg.input_value("#carichi-da") == "2026-01-01"
    pg.select_option("#carichi-anno", "2025")
    pg.wait_for_function("() => location.search.includes('a=2025-12-31')")
    pg.wait_for_function(PRONTO)
    # «Ieri» con dicembre scelto: il periodo va all'ultimo giorno con i dati, con la stessa lunghezza
    pg.click("[data-finestra=giorno]")
    pg.wait_for_function("() => location.search.includes('finestra=2026-01-31_2026-01-31')")
    assert pg.input_value("#carichi-a") == "2026-01-31" and pg.input_value("#carichi-da") == "2026-01-01"
    assert pg.get_attribute("[data-finestra=giorno]", "aria-pressed") == "true"
    # metà destra indipendente: anno da menu
    pg.select_option("#carichi-anno-2", "2026")
    pg.wait_for_function("() => location.search.includes('da2=2026-01-01')")
    assert errori == []


def test_dati_mancanti(browser, base, dati_anni):
    """(22/11/2026 b, Paolo) il buco del 14–15 gennaio 2026: nota con i tratti mancanti, area tratteggiata con «dati
    mancanti» nei due grafici delle fonti, riquadretto che lo dice."""
    pg, errori = _due(browser, base, dati_anni, "?finestra=2026-01-10_2026-01-20")
    nota = pg.locator("#carichi-mancanti")
    assert nota.is_visible()
    t = nota.inner_text()
    assert "dal 14 gen 2026 al 15 gen 2026" in t and "potenza richiesta" in t and "produzione per fonte" in t
    for g in ("#grafico-assoluti", "#grafico-fonti"):
        assert pg.locator(f"{g} svg.zoom-proprio rect.carichi-mancanti-area").count() == 1, g
        assert "dati mancanti" in pg.locator(f"{g} svg.zoom-proprio").text_content(), g
    r = pg.locator("#grafico-assoluti svg.zoom-proprio rect.carichi-mancanti-area")
    r.scroll_into_view_if_needed()
    b = r.bounding_box()
    pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + 20)
    assert "dati mancanti" in pg.locator(".grafico-suggerimento").first.inner_text()
    # senza buchi nel periodo la nota sparisce
    pg.select_option("#carichi-anno", "2025")
    pg.wait_for_function("() => document.getElementById('carichi-mancanti').hidden")
    assert errori == []
