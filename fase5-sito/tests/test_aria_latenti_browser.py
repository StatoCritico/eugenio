"""Carichi latenti nel browser (Chromium headless, Playwright; 14/11/2026), con la serie sintetica di prova (?prova=1):

- predefiniti 26 °C / 50 % (estate) e 20 °C / 40 % (inverno), 10 anni, tutto il giorno; risultati e nuvole sul diagramma;
- i cursori cambiano i risultati in modo monotono (UR estiva più alta → meno ore da deumidificare; UR invernale più alta
  → più ore da umidificare) e le proprietà della condizione interna; la casella numerica segue il cursore e viceversa;
- portata proporzionale, CSV scaricabile, Psicrometrico/Mollier, temi scuro e chiaro, 1366 e 375 px senza errori JS e
  senza scorrimento orizzontale della pagina. Gli screenshot vanno in /tmp/latenti_*.png.
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


def apri(browser, base, tema="scuro", larghezza=1366):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    if tema == "chiaro":
        pg.add_init_script("localStorage.setItem('tema','light');")
    pg.goto(base + "aria-latenti.html?prova=1")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie() && window.EUGENIO_ARIA_PAGINA.risultati().estate"
                         " && window.EUGENIO_ARIA_PAGINA.risultati().inverno", timeout=20000)
    pg.wait_for_timeout(500)
    return ctx, pg


RIS = """() => { const r = window.EUGENIO_ARIA_PAGINA.risultati(), f = (x) => ({ ore: x.ore, oreGruppo: x.oreGruppo, oreAnno: x.oreAnno,
  energiaAnno: x.energiaAnno, picco: x.picco, anni: x.anni, xg: x.obiettivo.xg, t: x.obiettivo.t, ur: x.obiettivo.ur });
  return { estate: f(r.estate), inverno: f(r.inverno) }; }"""


def imposta_cursore(pg, sel, valore):
    pg.eval_on_selector(sel, "(r, v) => { r.value = v; r.dispatchEvent(new Event('input', { bubbles: true })); }", str(valore))
    pg.wait_for_timeout(120)


def test_predefiniti_e_cursori(base, browser):
    ctx, pg = apri(browser, base)
    r = pg.evaluate(RIS)
    assert (r["estate"]["t"], r["estate"]["ur"], r["inverno"]["t"], r["inverno"]["ur"]) == (26, 50, 20, 40)
    assert 9.9 < r["estate"]["anni"] <= 10 and 9.9 < r["inverno"]["anni"] <= 10
    assert r["estate"]["ore"] > 100 and r["inverno"]["ore"] > 100
    assert pg.input_value("#lat-estate-t") == "26" and pg.locator(".latenti-num").nth(1).input_value() == "50"
    assert pg.locator(".latenti-num").nth(3).input_value() == "40"
    assert "10,5" in pg.locator("#latenti-estate .latenti-proprieta").inner_text() or "g/kg" in pg.locator("#latenti-estate .latenti-proprieta").inner_text()
    gr = pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.estate.gruppi()[0]")
    assert gr["anni"] == 10 and gr["da"] == "01/06" and gr["oraDa"] == 0 and gr["oraA"] == 24
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.inverno.gruppi()[0].da") == "01/11"
    strati = {s["nome"] for s in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati()")}
    assert {"estate-si", "estate-no", "inverno-si", "inverno-no", "estate-linea", "inverno-punto"} <= strati
    assert not pg.locator("#passo-risultati").is_hidden()
    assert "ore da deumidificare" in pg.locator("#aria-risultati").inner_text()
    # UR estiva: più alta → meno ore da deumidificare
    ore = []
    for u in (40, 50, 60, 70):
        imposta_cursore(pg, "#lat-estate-ur", u)
        ore.append(pg.evaluate(RIS)["estate"]["ore"])
    assert ore == sorted(ore, reverse=True) and ore[0] > ore[-1]
    assert pg.locator(".latenti-num").nth(1).input_value() == "70"
    # UR invernale: più alta → più ore da umidificare
    ore = []
    for u in (25, 40, 55, 70):
        imposta_cursore(pg, "#lat-inverno-ur", u)
        ore.append(pg.evaluate(RIS)["inverno"]["ore"])
    assert ore == sorted(ore) and ore[0] < ore[-1]
    # T estiva più alta (UR fissa) → x obiettivo più alta → meno ore; casella → cursore
    prima = pg.evaluate(RIS)["estate"]
    pg.locator(".latenti-num").first.fill("28,5")
    pg.wait_for_timeout(150)
    dopo = pg.evaluate(RIS)["estate"]
    assert pg.input_value("#lat-estate-t") == "28.5" and dopo["t"] == 28.5 and dopo["xg"] > prima["xg"] and dopo["ore"] < prima["ore"]
    # «Condizioni di progetto» riporta a 26/50
    pg.locator("#latenti-estate .latenti-ripristina").click()
    pg.wait_for_timeout(150)
    r = pg.evaluate(RIS)["estate"]
    assert (r["t"], r["ur"]) == (26, 50)
    assert not pg.errori, pg.errori
    ctx.close()


def test_portata_csv_e_ore(base, browser):
    ctx, pg = apri(browser, base)
    a = pg.evaluate(RIS)
    pg.fill("#lat-portata", "2000")
    pg.wait_for_timeout(300)
    b = pg.evaluate(RIS)
    assert b["estate"]["ore"] == a["estate"]["ore"]
    assert abs(b["estate"]["energiaAnno"] / a["estate"]["energiaAnno"] - 2) < 1e-9
    # preset «Ore d'ufficio» nel gruppo estivo: meno ore
    pg.locator("#latenti-estate button[data-preset=ufficio]").click()
    pg.wait_for_timeout(400)
    c = pg.evaluate(RIS)
    assert c["estate"]["oreGruppo"] < a["estate"]["oreGruppo"] * 0.4 and c["inverno"]["oreGruppo"] == a["inverno"]["oreGruppo"]
    # anni del gruppo invernale: ultimo anno
    imposta_cursore(pg, "#latenti-inverno input[type=range][id^=aria-anni]", 0)
    pg.wait_for_timeout(400)
    d = pg.evaluate(RIS)
    assert d["inverno"]["anni"] <= 1.001 and d["inverno"]["oreGruppo"] < a["inverno"]["oreGruppo"] / 5
    with pg.expect_download() as dl:
        pg.click("#lat-csv")
    testo = Path(dl.value.path()).read_text(encoding="utf-8-sig")
    assert "Carichi latenti" in testo and "DATI SINTETICI" in testo and "Mese per mese" in testo and "curva di durata" in testo
    assert not pg.errori, pg.errori
    ctx.close()


@pytest.mark.parametrize("tema", ["scuro", "chiaro"])
@pytest.mark.parametrize("larghezza", [1366, 375])
def test_viste_temi_e_larghezze(base, browser, tema, larghezza):
    ctx, pg = apri(browser, base, tema, larghezza)
    firma = "() => { const c = document.querySelector('#diagramma-aria canvas'); return c.toDataURL().length; }"
    psi = pg.evaluate(firma)
    pg.click("button[data-modo=mollier]")
    pg.wait_for_timeout(250)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.modo()") == "mollier"
    assert pg.evaluate(firma) != psi
    pg.click("button[data-modo=psicrometrico]")
    pg.wait_for_timeout(200)
    assert pg.locator("#grafico-durata svg polyline").count() == 2
    assert pg.evaluate("document.documentElement.scrollWidth") <= larghezza + 1
    pg.screenshot(path=f"/tmp/latenti_{larghezza}_{tema}.png", full_page=True)
    assert not pg.errori, pg.errori
    ctx.close()
