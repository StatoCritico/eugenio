"""Free cooling e recupero nel browser (Chromium headless, Playwright; 14/11/2026), con la serie sintetica (?prova=1):

- la pagina si apre senza errori nei due temi, a 1366 e 375 px (niente scorrimento orizzontale della pagina);
- valori predefiniti: 4 gruppi (G1 ore d'ufficio e G2 tutte le ore visibili, G3/G4 spenti), tabelle per gruppo e mensile,
  cifre, legenda con i regimi e le ore, tabella delle condizioni di progetto;
- i controlli cambiano i risultati: εs più alta → più calore recuperato; T di mandata più alta → più ore di free cooling
  totale; economizzatore a temperatura → niente regime «entalpico»; regola a soglia → più ore di brina;
- Psicrometrico/Mollier, CSV scaricabili. Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITO = Path(__file__).resolve().parents[1] / "sito"
PAGINA = "aria-freecooling.html"


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
    pg.on("console", lambda m: pg.errori.append(m.text) if m.type == "error" else None)
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.add_init_script(("localStorage.setItem('tema','light');" if tema == "chiaro" else "") + "localStorage.removeItem('eugenio-aria-v1');")
    pg.goto(base + PAGINA + "?prova=1")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie() && window.EUGENIO_ARIA_PAGINA.risultati().length", timeout=30000)
    pg.wait_for_timeout(300)
    return ctx, pg


def risultati(pg):
    return pg.evaluate("window.EUGENIO_ARIA_PAGINA.ricalcola()")


def scrivi(pg, campo, valore):
    pg.fill(f"#fc-{campo}", valore)
    pg.wait_for_timeout(250)


@pytest.mark.parametrize("tema,larghezza", [("scuro", 1366), ("chiaro", 1366), ("scuro", 375), ("chiaro", 375)])
def test_pagina_predefinita(base, browser, tema, larghezza):
    ctx, pg = apri(browser, base, tema, larghezza)
    gruppi = pg.evaluate("window.EUGENIO_ARIA_PAGINA.gruppi.gruppi().map((g) => [g.nome, g.mostra, g.anni])")
    assert gruppi == [["Ore d'ufficio, tutto l'anno", True, 10], ["Tutto il giorno, tutto l'anno", True, 10],
                      ["Estate, ore d'ufficio", False, 10], ["Inverno, ore d'ufficio", False, 10]]
    r = risultati(pg)
    assert [g["nome"] for g in r] == gruppi[0][:1] + gruppi[1][:1]
    u = r[0]
    assert 2500 < u["ore"] / u["anni"] < 2700                         # 8–18 feriali ≈ 2.610 ore l'anno
    assert u["kwhFcH"] > 0 and u["kwhInverno"] > 0 and u["kwhEstate"] > 0 and u["kwhElettrici"] > 0
    assert sum(u["oreRegime"]) == pytest.approx(u["ore"] / u["anni"])
    o = pg.evaluate("window.EUGENIO_ARIA_PAGINA.opzioni()")
    assert (o["V"], o["quotaMinima"], o["tMandata"], o["tBilancio"], o["epsS"], o["epsL"]) == (10000, 30, 16, 12, 0.7, 0)
    assert pg.locator("#fc-tabella-gruppi tbody tr").count() >= 20
    assert pg.locator("#fc-tabella-mesi tbody tr").count() == 13
    assert pg.locator("#fc-tabella-progetto tbody tr").count() == 6
    legenda = pg.locator("#diagramma-aria .aria-legenda").inner_text()
    for t in ("Free cooling totale", "Recupero invernale", "Rischio brina", "ore l'anno", "T di mandata 16,0 °C", "h di ripresa"):
        assert t in legenda, t
    assert pg.evaluate("document.documentElement.scrollWidth") <= larghezza + 1
    pg.click("button[data-modo=mollier]")
    pg.wait_for_timeout(200)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.modo()") == "mollier"
    pg.screenshot(path=str(Path("/tmp") / f"fc_{tema}_{larghezza}.png"), full_page=larghezza < 500)
    assert not pg.errori, pg.errori
    ctx.close()


def test_i_controlli_cambiano_i_risultati(base, browser):
    ctx, pg = apri(browser, base)
    a = risultati(pg)[0]
    scrivi(pg, "epsS", "0,85")
    b = risultati(pg)[0]
    assert b["kwhInverno"] > a["kwhInverno"] * 1.1 and b["kwhEstate"] > a["kwhEstate"]
    scrivi(pg, "tMandata", "18")
    c = risultati(pg)[0]
    assert c["oreRegime"][1] > b["oreRegime"][1]                         # più ore di free cooling totale
    assert "T di mandata 18,0 °C" in pg.locator("#diagramma-aria .aria-legenda").inner_text()
    pg.select_option("#fc-economizzatore", "temperatura")
    pg.wait_for_timeout(250)
    d = risultati(pg)[0]
    assert d["oreRegime"][3] == 0 and "entalpico (aria calda" not in pg.locator("#diagramma-aria .aria-legenda").inner_text()
    pg.select_option("#fc-tipoRec", "entalpico")
    pg.wait_for_timeout(250)
    assert pg.input_value("#fc-epsL") == "0,60"
    pg.select_option("#fc-regolaBrina", "soglia")
    pg.wait_for_timeout(250)
    assert pg.locator("#fc-tSoglia").is_visible()
    scrivi(pg, "tSoglia", "5")
    e = risultati(pg)[1]
    assert e["oreBrina"] > 100 and e["kwhPerso"] > 0
    scrivi(pg, "V", "abc")
    assert pg.get_attribute("#fc-V", "aria-invalid") == "true"
    pg.click(".aria-fc-diagramma button")                                # valori predefiniti
    pg.wait_for_timeout(300)
    f = risultati(pg)[0]
    assert f["kwhInverno"] == pytest.approx(a["kwhInverno"]) and f["kwhFcH"] == pytest.approx(a["kwhFcH"])
    assert not pg.errori, pg.errori
    ctx.close()


def test_gruppo_nel_diagramma_progetto_e_csv(base, browser):
    ctx, pg = apri(browser, base)
    pg.select_option("#fc-gruppo-diagramma", index=1)
    pg.wait_for_timeout(250)
    assert "Tutto il giorno" in pg.locator("#aria-risultati").inner_text()
    # condizioni di progetto modificabili a mano
    pg.fill("#fc-prog-invT", "-15")
    pg.wait_for_timeout(200)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.progetto().inverno.t") == -15
    assert "Rischio brina" in pg.locator("#fc-tabella-progetto").inner_text()
    pg.click("#fc-prog-ripristina")
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.progetto().inverno.t") != -15
    for b, nome in (("#fc-csv-gruppi", "eugenio_freecooling_gruppi_"), ("#fc-csv-mesi", "eugenio_freecooling_mesi_"), ("#fc-csv-ore", "eugenio_freecooling_ore_")):
        with pg.expect_download() as dl:
            pg.click(b)
        assert dl.value.suggested_filename.startswith(nome)
        testo = Path(dl.value.path()).read_text(encoding="utf-8-sig")
        assert "Stima del potenziale" in testo and "CC BY 4.0" in testo
    svg = pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.svg()")
    # (14/11/2026) la legenda degli strati è nella fascia dell'immagine (prima una riga «Colori: …» delle fonti)
    assert "free cooling totale" in svg.lower() and "ore l'anno" in svg and "Dati sintetici di prova" in svg
    assert not pg.errori, pg.errori
    ctx.close()
