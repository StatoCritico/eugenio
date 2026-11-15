"""Trattamento aria › Ore di funzionamento nel browser (Chromium headless, Playwright; 14/11/2026), serie di prova (?prova=1):

- gruppi predefiniti esatti (Estate/Inverno × 5/20 anni, tutto il giorno, tutti mostrati), serie del passo 1 portata a
  20 anni, nuvole con i gruppi di 20 anni disegnati per primi, legenda con i nomi e le ore;
- i preset cambiano le ore; «Ore d'ufficio» (8–18 feriali) riduce le ore a circa 10/24 · 5/7 e il nome segue;
- Psicrometrico/Mollier e Punti/Densità cambiano il disegno; la casella della legenda nasconde il gruppo;
- anni del passo 1 scelti a mano: nota con il pulsante «Carica…»; zona di comfort, valori di progetto modificabili;
- CSV delle statistiche e delle ore, SVG con i gruppi nella fascia; tempi (filtro e ridisegno < 1 s);
- temi scuro e chiaro, 1366 e 375 px senza errori JavaScript e senza scorrimento orizzontale (screenshot in
  /tmp/eugenio-aria-ore/). Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITO = Path(__file__).resolve().parents[1] / "sito"
FOTO = Path("/tmp/eugenio-aria-ore")


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


def apri(browser, base, tema="scuro", larghezza=1366, prima=""):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.add_init_script(("localStorage.setItem('tema','light');" if tema == "chiaro" else "") + prima)
    pg.goto(base + "aria-ore.html?prova=1")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.risultati() && window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 20", timeout=30000)
    pg.wait_for_timeout(400)
    return ctx, pg


GRUPPI = "window.EUGENIO_ARIA_PAGINA.gruppi.gruppi().map((g) => ({ nome: g.nome, anni: g.anni, da: g.da, a: g.a, oraDa: g.oraDa, oraA: g.oraA, giorni: g.giorni, mostra: g.mostra, n: g.indici.length }))"
FIRMA = """() => { const c = document.querySelector('#diagramma-aria canvas'), g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0;
  for (let i = 0; i < d.length; i += 4 * 53) s = (s * 31 + d[i] + 3 * d[i + 1] + 7 * d[i + 2] + d[i + 3]) % 1000000007;
  return s; }"""


def gruppo(pg, i):
    return pg.locator("#aria-gruppi .aria-gruppo").nth(i)


def attendi(pg, ms=500):
    pg.wait_for_timeout(ms)


def test_predefiniti_esatti(base, browser):
    ctx, pg = apri(browser, base)
    g = pg.evaluate(GRUPPI)
    assert [x["nome"] for x in g] == ["Estate, ultimi 5 anni", "Inverno, ultimi 5 anni", "Estate, ultimi 20 anni", "Inverno, ultimi 20 anni"]
    assert [x["anni"] for x in g] == [5, 5, 20, 20]
    assert [(x["da"], x["a"]) for x in g] == [("01/06", "30/09"), ("01/11", "31/03")] * 2
    assert all(x["oraDa"] == 0 and x["oraA"] == 24 and x["giorni"] == "tutti" and x["mostra"] for x in g)
    assert g[2]["n"] > 3.8 * g[0]["n"] and g[3]["n"] > 3.8 * g[1]["n"]          # 20 anni ≈ 4 × 5 anni
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.scelta.anni()") == 20
    nuvole = pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati().filter((s) => s.tipo === 'nuvola').map((s) => s.nome)")
    ids = pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.gruppi().map((g) => 'nuvola-' + g.id)")
    assert nuvole == [ids[2], ids[3], ids[0], ids[1]]                              # prima i 20 anni, sotto
    leg = pg.locator("#diagramma-aria .aria-legenda").inner_text()
    for x in g:
        assert x["nome"] in leg
    assert "14." in leg or "18." in leg                                             # ore con le migliaia
    r = pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi.map((g) => [g.stat.ore, Math.round(g.stat.anni), g.progetto.ore])")
    assert [x[1] for x in r] == [5, 5, 20, 20] and all(x[0] == y["n"] == x[2] for x, y in zip(r, g))
    assert pg.get_attribute("button[data-modo=psicrometrico]", "aria-pressed") == "true"
    assert pg.locator("#ore-stat table tbody tr").count() == 15
    assert not pg.errori, pg.errori
    ctx.close()


def test_preset_e_ore_ufficio(base, browser):
    ctx, pg = apri(browser, base)
    prima = pg.evaluate(GRUPPI)
    gruppo(pg, 0).locator("button[data-preset=anno]").click()
    attendi(pg)
    dopo = pg.evaluate(GRUPPI)
    assert dopo[0]["n"] > 2.5 * prima[0]["n"] and dopo[0]["nome"] == "Tutto l'anno, ultimi 5 anni"
    assert [x["n"] for x in dopo[1:]] == [x["n"] for x in prima[1:]]
    gruppo(pg, 2).locator("button[data-preset=ufficio]").click()
    attendi(pg)
    uff = pg.evaluate(GRUPPI)[2]
    rapporto = uff["n"] / prima[2]["n"]
    assert abs(rapporto - 10 / 24 * 5 / 7) < 0.02, rapporto                       # 8 ≤ h < 18: 10 ore su 24, lun–ven
    assert uff["nome"] == "Estate, ultimi 20 anni, ore d'ufficio"
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi[2].stat.ore") == uff["n"]
    gruppo(pg, 2).locator("button[data-preset=giorno]").click()
    attendi(pg)
    assert pg.evaluate(GRUPPI)[2]["n"] == prima[2]["n"]
    # un nome scritto a mano resta
    gruppo(pg, 1).locator(".aria-gruppo-nome").fill("Riscaldamento")
    attendi(pg, 300)
    gruppo(pg, 1).locator("button[data-preset=ufficio]").click()
    attendi(pg)
    assert pg.evaluate(GRUPPI)[1]["nome"] == "Riscaldamento"
    assert "Riscaldamento" in pg.locator("#diagramma-aria .aria-legenda").inner_text()
    assert not pg.errori, pg.errori
    ctx.close()


def test_viste_legenda_e_aspetto(base, browser):
    ctx, pg = apri(browser, base)
    psi = pg.evaluate(FIRMA)
    pg.click("button[data-modo=mollier]")
    attendi(pg, 300)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.modo()") == "mollier" and pg.evaluate(FIRMA) != psi
    pg.click("button[data-modo=psicrometrico]")
    attendi(pg, 300)
    assert pg.evaluate(FIRMA) == psi
    pg.click("button[data-nuvola=densita]")
    attendi(pg, 300)
    assert pg.evaluate(FIRMA) != psi
    pg.click("button[data-nuvola=punti]")
    pg.select_option("#ore-raggio", "1.6")
    attendi(pg, 300)
    assert pg.evaluate(FIRMA) != psi
    # la casella della legenda è il «Mostra» del gruppo
    pg.locator("#diagramma-aria .aria-legenda input").nth(3).uncheck()
    attendi(pg)
    assert pg.evaluate(GRUPPI)[3]["mostra"] is False
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati().filter((s) => s.tipo === 'nuvola').length") == 3
    assert "spento" in gruppo(pg, 3).get_attribute("class")
    assert "(nascosto)" in pg.evaluate("document.querySelector('#ore-stat thead').textContent")
    assert not pg.errori, pg.errori
    ctx.close()


def test_anni_scelti_a_mano(base, browser):
    ctx, pg = apri(browser, base)
    pg.locator("#aria-anni").fill("2")                                           # 5 anni
    pg.locator("#aria-anni").dispatch_event("change")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 5")
    attendi(pg)
    nota = pg.locator("#aria-ore-nota-anni")
    assert "chiedono ultimi 20 anni" in nota.inner_text()
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi.map((g) => Math.round(g.stat.anni))") == [5, 5, 5, 5]
    nota.locator("button").click()
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 20")
    attendi(pg)
    assert nota.inner_text() == ""
    # un gruppo che chiede più anni allunga da solo la serie
    pg.locator("#aria-anni").fill("1")                                           # 2 anni
    pg.locator("#aria-anni").dispatch_event("change")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 2")
    gruppo(pg, 0).locator("input[type=range]").fill("3")                         # 10 anni
    gruppo(pg, 0).locator("input[type=range]").dispatch_event("input")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 20", timeout=15000)
    attendi(pg)
    assert "Ho portato la serie" in nota.inner_text()
    assert pg.evaluate(GRUPPI)[0]["nome"] == "Estate, ultimi 10 anni"
    assert not pg.errori, pg.errori
    ctx.close()


def test_zona_e_progetto(base, browser):
    ctx, pg = apri(browser, base)
    z0 = pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi.map((g) => g.zona)")
    assert all(z["dentro"] + z["fuori"] == z["ore"] for z in z0)
    assert z0[1]["riscaldare"] > 0.9 * z0[1]["ore"] and z0[0]["raffreddare"] > 0
    assert any(s["nome"] == "zona-comfort" for s in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati()"))
    pg.fill("#ore-zona-tMax", "28")
    attendi(pg, 600)
    z1 = pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi.map((g) => g.zona)")
    assert z1[0]["raffreddare"] < z0[0]["raffreddare"]
    assert "Nella zona" in pg.locator("#ore-zona-risultati").inner_text()
    # valori di progetto: precompilati dai percentili, modificabili, «Ripristina dai dati»
    campo = pg.locator(".aria-ore-campo[data-campo=invT]").first
    t0 = pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi[0].progetto.inverno.t")
    assert campo.input_value() == f"{t0:.1f}".replace(".", ",").replace("-", "-")
    punti = lambda: pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati().filter((s) => s.tipo === 'punto').length")
    assert punti() == 8
    campo.fill("-12,5")
    campo.dispatch_event("change")
    attendi(pg, 300)
    campo = pg.locator(".aria-ore-campo[data-campo=invT]").first
    assert campo.input_value() == "-12,5" and "modificato" in campo.get_attribute("class")
    assert not pg.locator("#ore-ripristina").is_disabled()
    pg.click("#ore-ripristina")
    attendi(pg, 300)
    assert pg.locator(".aria-ore-campo[data-campo=invT]").first.input_value() == f"{t0:.1f}".replace(".", ",")
    pg.uncheck("#ore-progetto-mostra")
    attendi(pg, 200)
    assert punti() == 0
    # livello di progetto: cambia i valori
    pg.locator("#aria-livello select").nth(1).select_option("5")
    attendi(pg, 600)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi[0].progetto.estate.t") < pg.evaluate("window.EUGENIO_ARIA_PAGINA.risultati().gruppi[0].stat.tMax")
    assert not pg.errori, pg.errori
    ctx.close()


def test_scaricamenti(base, browser):
    ctx, pg = apri(browser, base)
    with pg.expect_download() as dl:
        pg.click("#ore-csv")
    testo = Path(dl.value.path()).read_text(encoding="utf-8-sig")
    assert dl.value.suggested_filename == "eugenio-aria-ore-prova-statistiche.csv"
    for t in ("Statistiche", "Condizioni di progetto", "classi di temperatura (2 K)", "classi di umidità specifica", "T \\ x", "Zona di comfort", "Dati sintetici di prova"):
        assert t in testo, t
    pg.select_option("#ore-csv-gruppo", index=3)
    with pg.expect_download() as dl:
        pg.click("#ore-csv-orario")
    righe = Path(dl.value.path()).read_text(encoding="utf-8-sig").splitlines()
    n = pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.gruppi()[3].indici.length")
    assert dl.value.suggested_filename == "eugenio-aria-ore-prova-gruppo4-ore.csv"
    intest = next(i for i, r in enumerate(righe) if r.startswith("Ora UTC"))
    assert len(righe) - intest - 1 == min(n, 100000)
    assert righe[-1].count(";") == 6 and "," in righe[-1]
    svg = pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.svg()")
    assert "Gruppo 1 (rosso mattone): Estate, ultimi 5 anni" in svg and "Gruppo 4 (magenta)" in svg and "Zona di comfort" in svg
    assert "Dati sintetici di prova" in svg
    assert not pg.errori, pg.errori
    ctx.close()


def test_tempi(base, browser):
    ctx, pg = apri(browser, base)
    # tutta la serie (dal 1991, ~35 anni, ~310.000 ore) in tutti e 4 i gruppi: oltre 1,2 milioni di punti in tutto
    pg.locator("#aria-anni").fill("5")
    pg.locator("#aria-anni").dispatch_event("change")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA.scelta.serie().anni_richiesti === 0", timeout=30000)
    pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.imposta([0,1,2,3].map(() => ({ preset: 'anno', anni: 0 })))")
    attendi(pg, 800)
    ms = pg.evaluate("""() => { const A = window.EUGENIO_ARIA_PAGINA, s = A.scelta.serie(), G = window.EUGENIO_GRUPPI_ORE;
      let a = performance.now(); const idx = G.filtra(s, { da: '01/06', a: '30/09', oraDa: 8, oraA: 18, giorni: 'feriali' }); const filtro = performance.now() - a;
      a = performance.now(); A.diagramma.ridisegna(); A.diagramma.disegnaSubito(); const disegno = performance.now() - a;
      a = performance.now(); A.ricalcola(); const calcolo = performance.now() - a;
      return { n: s.n, filtro, disegno, calcolo, punti: A.gruppi.gruppi().reduce((m, g) => m + g.indici.length, 0) }; }""")
    assert ms["n"] > 300000 and ms["punti"] > 1200000
    assert ms["filtro"] < 100 and ms["disegno"] < 1000, ms
    assert ms["calcolo"] < 4000, ms
    assert not pg.errori, pg.errori
    ctx.close()


@pytest.mark.parametrize("larghezza", [1366, 375])
@pytest.mark.parametrize("tema", ["scuro", "chiaro"])
def test_temi_e_larghezze(base, browser, tema, larghezza):
    ctx, pg = apri(browser, base, tema, larghezza)
    assert pg.evaluate("document.documentElement.scrollWidth") <= larghezza + 1
    assert pg.locator("#passo-risultati").is_visible() and pg.locator("#passo-zona").is_visible()
    FOTO.mkdir(exist_ok=True)
    pg.screenshot(path=str(FOTO / f"pagina_{tema}_{larghezza}.png"), full_page=True)
    pg.locator("#diagramma-aria").screenshot(path=str(FOTO / f"diagramma_{tema}_{larghezza}.png"))
    pg.locator("#passo-risultati").screenshot(path=str(FOTO / f"risultati_{tema}_{larghezza}.png"))
    assert not pg.errori, pg.errori
    ctx.close()
