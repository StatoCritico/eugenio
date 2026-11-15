"""Trattamento aria nel browser (Chromium headless, Playwright; 14/11/2026), con la serie sintetica di prova (?prova=1):

- le 4 pagine si aprono senza errori JavaScript nei due temi; la serie di prova arriva, il comune è scelto sulla mappa;
- i pulsanti «Psicrometrico» / «Mollier» cambiano il diagramma (aria-pressed, pixel diversi);
- una nuvola di 100.000 punti si disegna in meno di 1 secondo; PNG e SVG con «Fonte: EuGEnio»; ↗ apre il riquadro;
- gruppi di ore: i preset cambiano le ore contate e la legenda segue il nome;
- livello di progetto: predefinito 99 % / 1 %, scelta ricordata in eugenio-aria-v1 ed evento eugenio:aria-livello;
- menu: la tendina «Trattamento aria» sta nella finestra con il sottotitolo «Psicrometria», anche nella riga fissata.
Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITO = Path(__file__).resolve().parents[1] / "sito"
PAGINE = ["aria-trasformazioni.html", "aria-ore.html", "aria-latenti.html", "aria-freecooling.html"]


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


def apri(browser, base, pagina, tema="scuro", larghezza=1366, prima=""):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900})
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.add_init_script(("localStorage.setItem('tema','light');" if tema == "chiaro" else "") + prima)
    pg.goto(base + pagina + "?prova=1")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie()", timeout=20000)
    pg.wait_for_timeout(300)
    return ctx, pg


FIRMA = """() => { const c = document.querySelector('#diagramma-aria canvas'), g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0, n = 0;
  for (let i = 0; i < d.length; i += 4 * 97) { s = (s * 31 + d[i] + 3 * d[i + 1] + 7 * d[i + 2] + d[i + 3]) % 1000000007; if (d[i + 3]) n++; }
  return [s, n]; }"""


@pytest.mark.parametrize("tema", ["scuro", "chiaro"])
@pytest.mark.parametrize("pagina", PAGINE)
def test_pagine_e_viste(base, browser, pagina, tema):
    ctx, pg = apri(browser, base, pagina, tema)
    stato = pg.evaluate("window.EUGENIO_ARIA_PAGINA.scelta.stato()")
    # Ore di funzionamento: i gruppi predefiniti chiedono 20 anni e la pagina porta lì la serie del passo 1
    assert stato["sintetica"] and stato["prova"] and stato["istat"] and stato["anni"] == (20 if pagina == "aria-ore.html" else 10)
    assert pg.locator("#mappa path.scelto").count() == 1
    assert "Dati sintetici di prova" in pg.locator(".aria-disponibilita").inner_text()
    assert pg.get_attribute("button[data-modo=psicrometrico]", "aria-pressed") == "true"
    psi = pg.evaluate(FIRMA)
    assert psi[1] > 1000
    pg.click("button[data-modo=mollier]")
    pg.wait_for_timeout(250)
    assert pg.get_attribute("button[data-modo=mollier]", "aria-pressed") == "true"
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.modo()") == "mollier"
    assert pg.evaluate(FIRMA) != psi
    assert pg.locator(".aria-legenda .aria-voce-legenda").count() >= 1
    assert not pg.errori, pg.errori
    ctx.close()


def test_nuvola_grande_veloce_ed_esportazioni(base, browser):
    ctx, pg = apri(browser, base, "aria-trasformazioni.html")
    ms = pg.evaluate("""() => { const D = window.EUGENIO_ARIA_PAGINA.diagramma, n = 100000;
      const t = new Float32Array(n), x = new Float32Array(n);
      for (let i = 0; i < n; i++) { t[i] = -5 + 35 * ((i * 7919) % n) / n; x[i] = 0.002 + 0.014 * ((i * 104729) % n) / n; }
      D.nuvola('prova', '#d03030', { t, x }, { etichetta: 'prova 100.000' });
      const a = performance.now(); D.disegnaSubito(); return performance.now() - a; }""")
    assert ms < 1000, ms
    ms2 = pg.evaluate("""() => { const D = window.EUGENIO_ARIA_PAGINA.diagramma; D.modo('mollier'); const a = performance.now(); D.disegnaSubito(); return performance.now() - a; }""")
    assert ms2 < 1000, ms2
    svg = pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.svg()")
    assert svg.startswith("<svg") and "Fonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0)" in svg
    assert "Dati sintetici di prova, non reali." in svg and "data:image/png;base64" in svg and "coordinata di Mollier" in svg
    n = pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.png(1).then((b) => b.size)")
    assert n > 20000
    with pg.expect_download() as dl:
        pg.click(".aria-scarica button[data-formato=svg]")
    assert dl.value.suggested_filename == "eugenio-aria-trasformazioni-mollier.svg"
    assert "Download avviato" in pg.locator(".aria-messaggio-immagine").inner_text()
    pg.click("#diagramma-aria .grafico-apri")
    pg.wait_for_selector("dialog.riquadro-grafico[open] svg")
    assert pg.locator("dialog.riquadro-grafico[open] svg").count() >= 1
    pg.keyboard.press("Escape")
    assert not pg.errori, pg.errori
    ctx.close()


def test_suggerimento_sul_diagramma(base, browser):
    ctx, pg = apri(browser, base, "aria-ore.html")
    pg.locator("#diagramma-aria canvas").scroll_into_view_if_needed()
    pg.wait_for_timeout(200)
    box = pg.locator("#diagramma-aria canvas").bounding_box()
    pg.mouse.move(box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.75)
    testo = pg.locator(".aria-suggerimento").inner_text()
    assert "T " in testo and "UR " in testo and "g/kg" in testo and "kJ/kg" in testo
    ctx.close()


def test_gruppi_di_ore(base, browser):
    ctx, pg = apri(browser, base, "aria-ore.html")
    conta = lambda: pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.gruppi().map((g) => g.indici.length)")
    # la pagina parte con 4 gruppi (test proprio in test_aria_ore_browser.py): qui due gruppi per provare il modulo
    pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.imposta([{ preset: 'estate' }, { preset: 'inverno' }])")
    pg.wait_for_timeout(300)
    prima = conta()
    assert len(prima) == 2 and all(n > 1000 for n in prima)
    assert pg.locator(".aria-gruppo-nome").first.input_value() == "Estate"
    pg.locator(".aria-gruppo").first.locator("button[data-preset=ufficio]").click()
    pg.wait_for_timeout(300)
    dopo = conta()
    assert dopo[0] < prima[0] * 0.4 and dopo[1] == prima[1]
    assert pg.locator(".aria-gruppo-nome").first.input_value() == "Estate"          # il periodo resta nel nome
    pg.locator(".aria-gruppo-nome").first.fill("Uffici d'estate")
    pg.wait_for_timeout(300)
    assert "Uffici d'estate" in pg.locator(".aria-legenda").inner_text()
    pg.click(".aria-gruppi-piede button")                                             # Aggiungi un gruppo
    pg.wait_for_timeout(300)
    assert len(conta()) == 3
    assert pg.locator(".aria-zona").is_visible()                                      # zona climatica nota (DPR 412)
    assert not pg.errori, pg.errori
    ctx.close()


def test_livello_di_progetto(base, browser):
    ctx, pg = apri(browser, base, "aria-trasformazioni.html", prima="if (!sessionStorage.getItem('pulito')) { sessionStorage.setItem('pulito', '1'); localStorage.removeItem('eugenio-aria-v1'); }")
    L = pg.evaluate("window.EUGENIO_ARIA_PAGINA.livello.valori()")
    assert L == {"inverno": 99, "estate": 1}
    opzioni = pg.locator("#aria-livello select").first.locator("option").all_inner_texts()
    assert opzioni == ["99,6 %", "99 % (predefinito)", "95 %", "altro…"]
    assert pg.locator("#aria-livello select").nth(1).locator("option").all_inner_texts() == ["0,4 %", "1 % (predefinito)", "5 %", "altro…"]
    pg.evaluate("document.addEventListener('eugenio:aria-livello', (e) => { window.__livello = e.detail; })")
    pg.locator("#aria-livello select").first.select_option("99.6")
    assert pg.evaluate("window.__livello") == {"inverno": 99.6, "estate": 1}
    pg.locator("#aria-livello select").nth(1).select_option("altro")
    pg.locator("#aria-livello .aria-livello-libero").nth(1).fill("2,5")
    assert pg.evaluate("window.__livello") == {"inverno": 99.6, "estate": 2.5}
    memoria = json.loads(pg.evaluate("localStorage.getItem('eugenio-aria-v1')"))
    assert memoria["livelli"] == {"inverno": 99.6, "estate": 2.5} and memoria["istat"] and memoria["anni"] == 10
    assert "Estate 2,5 %" in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.svg()")
    pg.reload()
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie()", timeout=20000)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.livello.valori()") == {"inverno": 99.6, "estate": 2.5}
    assert pg.locator("#aria-livello .aria-livello-libero").nth(1).input_value() == "2,5"
    assert not pg.errori, pg.errori
    ctx.close()


def test_scelta_condivisa_tra_le_pagine(base, browser):
    ctx, pg = apri(browser, base, "aria-ore.html")
    pg.locator("#aria-anni").fill("1")                                    # 2 anni
    pg.locator("#aria-anni").dispatch_event("change")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 2")
    istat = pg.evaluate("window.EUGENIO_ARIA_PAGINA.scelta.stato().istat")
    pg.goto(base + "aria-latenti.html?prova=1")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie()", timeout=20000)
    st = pg.evaluate("window.EUGENIO_ARIA_PAGINA.scelta.stato()")
    assert st["anni"] == 2 and st["istat"] == istat
    assert not pg.errori, pg.errori
    ctx.close()


@pytest.mark.parametrize("larghezza", [1366, 1000, 900])
def test_menu_trattamento_aria(base, browser, larghezza):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 800})
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.goto(base + "faq.html")
    g = "details.voce-gruppo[data-gruppo=aria]"
    pg.hover(g + " > summary")
    assert pg.evaluate(f"document.querySelector('{g}').open")
    d = pg.evaluate(f"(() => {{ const b = document.querySelector('{g} .tendina').getBoundingClientRect(); return [b.left, b.right]; }})()")
    assert d[0] >= 0 and d[1] <= larghezza
    assert pg.locator(g + " .tendina > li").first.inner_text().strip().upper() == "PSICROMETRIA"
    assert pg.locator(g + " .tendina a").count() == 4
    pg.click(g + " > summary")                                                       # fissa il gruppo nella riga nera
    assert pg.locator("nav.riga-fissata .voce-sottotitolo").count() == 1
    assert pg.locator("nav.riga-fissata a").count() == 4
    assert not errori, errori
    ctx.close()


def test_moduli_comuni_togli_ore_legenda(base, browser):
    """(14/11/2026) «Togli» nascosto con un gruppo solo; ore scritte in chiaro (8–18 = 8:00–17:59); legenda nelle immagini."""
    ctx, pg = apri(browser, base, "aria-ore.html")
    pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.imposta([{ preset: 'estate' }])")
    pg.wait_for_timeout(300)
    togli = pg.locator(".aria-gruppo .aria-togli")
    assert togli.count() == 1 and not togli.is_visible()
    pg.locator(".aria-gruppo").first.locator("button[data-preset=ufficio]").click()
    pg.wait_for_timeout(300)
    assert "dalle 8 alle 18, cioè ore 8:00–17:59" in pg.locator(".aria-ore-spiega").first.inner_text()
    pg.click(".aria-gruppi-piede button")                                             # due gruppi: «Togli» visibile
    pg.wait_for_timeout(300)
    assert pg.locator(".aria-gruppo .aria-togli").first.is_visible()
    D = "window.EUGENIO_ARIA_PAGINA.diagramma"
    pg.evaluate(D + ".punto('prova-leg', { t: 20, ur: 50 }, { colore: 'estate', etichetta: 'Punto di prova', nota: '(123 ore)' })")
    svg = pg.evaluate(D + ".svg()")
    assert "Punto di prova (123 ore)" in svg
    png = pg.evaluate("async () => (await " + D + ".png(1)).size")
    assert png > 10000
    assert not pg.errori, pg.errori
    ctx.close()


def test_note_del_server_sotto_la_disponibilita(base, browser):
    """(14/11/2026, verifica indipendente) le note della risposta di /api/psicro/serie (archivio dal 1940 non ancora sul
    server, anni chiesti, ore senza dati) si vedono al passo 1, la prima in grassetto; la fonte è quella del server."""
    n = 24 * 400
    nota = ("L'archivio dal 1940 di questo comune non è ancora sul server: per ora c'è solo la serie oraria ICON dal "
            "14/11/2022 (circa 1,1 anni).")
    corpo = {"istat": "037006", "comune": "Bologna", "quota_m": 54, "pressione_pa": 100679, "inizio": "2025-10-10T00:00Z",
             "passo_h": 1, "n": n, "t": [150 + (i % 24) for i in range(n)], "ur": [60] * n, "dal": "2025-10-10T00:00Z",
             "al": "2026-11-13T23:00Z", "anni_richiesti": 10, "anni_dati": 1.1,
             "fonte": "ICON storico (DWD) della serie oraria del server", "licenza": "CC BY 4.0",
             "note": [nota, "Chiesti 10 anni: i dati partono dal 10/10/2025, quindi la serie copre circa 1,1 anni."]}
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/psicro/serie/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(corpo)))
    pg.route("**/api/**", lambda r: r.fallback() if "/api/psicro/serie/" in r.request.url else r.fulfill(status=404, body="{}"))
    pg.add_init_script("localStorage.setItem('eugenio-aria-v1', JSON.stringify({ istat: '037006', anni: 10 }));")
    pg.goto(base + "aria-latenti.html?comune=037006")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie()", timeout=20000)
    note = pg.locator("#scelta-aria .aria-note-serie")
    assert note.is_visible()
    assert note.locator("li.importante").inner_text() == nota
    assert "Chiesti 10 anni" in note.inner_text()
    disp = pg.locator("#scelta-aria .aria-disponibilita").inner_text()
    assert "Fonte: ICON storico (DWD) della serie oraria del server" in disp and "Hai chiesto" not in disp
    assert not errori, errori
    ctx.close()
