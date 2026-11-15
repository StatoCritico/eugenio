"""Pagina «Trattamento aria › Trasformazioni (UTA)» nel browser (Chromium headless, Playwright; 14/11/2026), con la serie
sintetica di prova (?prova=1):

- si apre senza errori nei due temi a 1366 e 375 px, senza scorrimento orizzontale della pagina; Psicrometrico/Mollier;
- con i dati gialli del foglio scritti a mano (5000 m³/h, 120 m, 32 °C/50 % e −5 °C/80 %, inverno 20 °C/40 %, dal 15/11/2026
  i valori di partenza del foglio) mostra gli stessi numeri di psicro_UTA.xlsx (batteria fredda 46,0 kW, condensa
  27,4 kg/h, post-riscaldamento 10,9 kW; recupero 27,2 kW, preriscaldamento 12,0 kW, acqua 24,3 kg/h, post-riscaldamento
  30,0 kW) e la stessa stima stagionale;
- condizioni esterne precompilate dalla serie (livello e statistica), modificabili e «ripristina dal clima»;
- righe: tipo, parametri, aggiungi, togli, sposta, preset, svuota; tutto ricordato in eugenio-aria-trasf-v1 e
  «Ripristina predefiniti»; nuvola delle ore facoltativa;
- scaricamenti: CSV, JSON e foglio Excel compilato (celle gialle con i dati della pagina).
Si salta se Playwright o Chromium non ci sono."""
from __future__ import annotations

import functools
import io
import json
import threading
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITO = Path(__file__).resolve().parents[1] / "sito"
PAGINA = "aria-trasformazioni.html"
K = "#aria-trasformazioni-"


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


def apri(browser, base, tema="scuro", larghezza=1366, pulito=True):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and pg.errori.append(m.text))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    init = "localStorage.setItem('tema','light');" if tema == "chiaro" else ""
    if pulito:
        init += "if (!sessionStorage.getItem('pulito')) { sessionStorage.setItem('pulito','1'); localStorage.removeItem('eugenio-aria-trasf-v1'); localStorage.removeItem('eugenio-aria-v1'); }"
    pg.add_init_script(init)
    pg.goto(base + PAGINA + "?prova=1")
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie() && window.EUGENIO_ARIA_PAGINA.clima()", timeout=20000)
    pg.wait_for_timeout(300)
    return ctx, pg


def scrivi(pg, sel, valore):
    pg.fill(sel, valore)
    pg.wait_for_timeout(250)


def val(pg, sel):
    return float(pg.get_attribute(sel, "data-valore"))


def leggi(pg, sel):
    return pg.locator(sel).first.inner_text().strip()


@pytest.mark.parametrize("larghezza", [1366, 375])
@pytest.mark.parametrize("tema", ["scuro", "chiaro"])
def test_si_apre_e_cambia_vista(base, browser, tema, larghezza):
    ctx, pg = apri(browser, base, tema, larghezza)
    assert pg.evaluate("document.documentElement.scrollWidth") <= larghezza
    for k in ("estate", "inverno"):
        assert pg.locator(f".aria-trasformazioni-lista[data-stagione={k}] .aria-trasformazioni-riga").count() == 6
        assert pg.locator(f"table.aria-trasformazioni-tabella[data-stagione={k}] tbody tr").count() == 7
    strati = {s["nome"] for s in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati()")}
    assert {"trasf-estate", "trasf-inverno", "E-estate", "A-estate", "I-estate", "E-inverno", "A-inverno", "I-inverno", "retta-estate", "retta-inverno"} <= strati
    assert "ore" not in strati                                                     # nuvola spenta di predefinito
    pg.click("button[data-modo=mollier]")
    pg.wait_for_timeout(200)
    assert pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.modo()") == "mollier"
    pg.click("button[data-modo=psicrometrico]")
    assert not pg.errori, pg.errori
    ctx.close()


def test_stessi_numeri_del_foglio(base, browser):
    ctx, pg = apri(browser, base)
    for sel, v in ((f"{K}quota", "120"), (f"{K}portata", "5000"), (f"{K}quota-esterna", "100"),
                   (f"{K}estate-te", "32"), (f"{K}estate-ure", "50"), (f"{K}estate-ta", "26"), (f"{K}estate-ura", "50"),
                   (f"{K}estate-qs", "5000"), (f"{K}estate-ql", "1500"),
                   (f"{K}inverno-te", "-5"), (f"{K}inverno-ure", "80"), (f"{K}inverno-ta", "20"), (f"{K}inverno-ura", "40"),
                   (f"{K}inverno-qs", "8000"), (f"{K}inverno-ql", "500"), (f"{K}gg", "2404")):
        scrivi(pg, sel, v)
    pg.wait_for_timeout(300)
    # riepilogo (valori del foglio: UTA!D36…D74)
    attesi = {"estate.frigoTotale": ("46,00", 46.0039), "estate.condensa": ("27,35", 27.3536), "estate.postRiscaldamento": ("10,93", 10.9325),
              "estate.frigoSensibile": ("27,00", 27.0007), "estate.frigoLatente": ("19,00", 19.0032), "estate.ventilatori": ("1,11", 1.1095),
              "inverno.recuperata": ("27,21", 27.2127), "inverno.preriscaldamento": ("12,02", 12.0201), "inverno.umidificazione": ("24,33", 24.3259),
              "inverno.postRiscaldamento": ("29,99", 29.9925), "inverno.ventilatori": ("1,28", 1.2787)}
    for chiave, (t, v) in attesi.items():
        sel = f'[data-riep="{chiave}"]'
        assert leggi(pg, sel) == t, chiave
        assert val(pg, sel) == pytest.approx(v, abs=6e-4), chiave
    assert leggi(pg, '[data-riep="estate.raggiungibile"]') == "SÌ" and leggi(pg, '[data-riep="inverno.raggiungibile"]') == "SÌ"
    # cifre arrotondate come nella richiesta
    assert leggi(pg, '[data-cifra="frigo"]').startswith("46,0") and leggi(pg, '[data-cifra="acqua"]').startswith("27,4")
    assert leggi(pg, '[data-cifra="recuperata"]').startswith("27,2") and leggi(pg, '[data-cifra="termica"]').startswith("42,0")
    # tabella delle trasformazioni: batteria fredda (riga 2) e preriscaldamento invernale (riga 3)
    fredda = 'table[data-stagione=estate] tr[data-riga="1"]'
    assert leggi(pg, f'{fredda} [data-k=Qt]') == "−46,00" and leggi(pg, f'{fredda} [data-k=acqua]') == "−27,35"
    assert val(pg, f'{fredda} [data-k=t]') == pytest.approx(15.2502, abs=2e-3)
    assert leggi(pg, 'table[data-stagione=inverno] tr[data-riga="2"] [data-k=Qt]') == "12,02"
    # punti E, A, I come le righe 18–20 e 48–50 del foglio (valori salvati nel foglio a 120 m)
    assert val(pg, '#aria-trasf-estate tr[data-punto=I] td:nth-child(2)') == pytest.approx(22.847641, abs=1e-5)
    assert val(pg, '#aria-trasf-estate tr[data-punto=I] td:nth-child(4)') == pytest.approx(10.261130, abs=1e-5)
    assert val(pg, '#aria-trasf-inverno tr[data-punto=E] td:nth-child(4)') == pytest.approx(2.007629, abs=1e-5)
    assert val(pg, '#aria-trasf-inverno tr[data-punto=E] td:nth-child(8)') == pytest.approx(0.773025, abs=1e-6)
    assert val(pg, '#aria-trasf-inverno tr[data-punto=I] td:nth-child(2)') == pytest.approx(24.378468, abs=1e-5)
    # gen.: ṁ aria secca (UTA!H9, I9)
    assert val(pg, '[data-gen="estate.mtot"]') == pytest.approx(1.54621, abs=1e-4) and val(pg, '[data-gen="inverno.mtot"]') == pytest.approx(1.79669, abs=1e-4)
    # stima stagionale (UTA!H78…H85)
    for c, v in {"mOA": 1.79669, "eps": 0.6, "fabbisogno": 52708.848, "recuperata": 31625.309, "netto": 21083.539, "combustibile": 2442.769,
                 "frigo": 23001.960, "elettrica": 7667.320}.items():
        assert val(pg, f'[data-stima="{c}"]') == pytest.approx(v, rel=1e-5), c
    assert leggi(pg, '[data-stima="fabbisogno"]') == "52.709"
    assert "OK" in leggi(pg, ".aria-trasformazioni-lista[data-stagione=estate] .aria-trasformazioni-riga:nth-child(4) .aria-trasformazioni-nota")
    assert not pg.errori, pg.errori
    ctx.close()


def test_clima_livello_e_valori_a_mano(base, browser):
    ctx, pg = apri(browser, base)
    clima = pg.evaluate("(() => { const c = window.EUGENIO_ARIA_PAGINA.clima(); return { te: c.estate.t, ti: c.inverno.t, ui: c.inverno.ur, he: c.entalpia.t }; })()")
    conf = lambda: pg.evaluate("window.EUGENIO_ARIA_PAGINA.configurazione()")  # noqa: E731
    c = conf()
    assert c["estate"]["esterno"]["t"] == pytest.approx(clima["te"], abs=0.051) and c["inverno"]["esterno"]["t"] == pytest.approx(clima["ti"], abs=0.051)
    assert c["inverno"]["esterno"]["ur"] == pytest.approx(min(100, clima["ui"]), abs=0.051)
    assert c["inverno"]["ambiente"] == {"t": 20, "ur": 40}                        # come il foglio (dal 15/11/2026)
    assert pg.input_value(f"{K}estate-te") == f"{round(clima['te'], 1):g}".replace(".", ",")
    assert "non valori di norma" in leggi(pg, "#aria-trasf-estate .aria-trasformazioni-gruppo .aiuto")
    assert pg.locator("#aria-trasf-estate .aria-trasformazioni-collegamento").is_hidden()
    frigo = val(pg, '[data-riep="estate.frigoTotale"]')
    # livello estivo 5 %: estate meno severa, meno potenza frigorifera
    pg.locator("#aria-livello select").nth(1).select_option("5")
    pg.wait_for_timeout(400)
    assert conf()["estate"]["esterno"]["t"] < c["estate"]["esterno"]["t"]
    assert val(pg, '[data-riep="estate.frigoTotale"]') < frigo
    # statistica dell'entalpia
    pg.select_option(f"{K}statistica", "entalpia")
    pg.wait_for_timeout(400)
    assert "Entalpia 5 %" in leggi(pg, "#aria-trasf-estate .aria-trasformazioni-gruppo .aiuto")
    # valore a mano: resta e compare «ripristina dal clima»
    scrivi(pg, f"{K}estate-te", "35,5")
    assert conf()["estate"]["esterno"]["t"] == 35.5
    assert pg.locator("#aria-trasf-estate .aria-trasformazioni-collegamento").is_visible()
    assert "Hai scritto a mano" in leggi(pg, "#aria-trasf-estate .aria-trasformazioni-gruppo .aiuto")
    assert "scritte a mano: estate" in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.svg()")
    pg.click("#aria-trasf-estate .aria-trasformazioni-collegamento")
    pg.wait_for_timeout(300)
    assert conf()["estate"]["esterno"]["t"] != 35.5 and pg.locator("#aria-trasf-estate .aria-trasformazioni-collegamento").is_hidden()
    # valore non valido: segnato, il calcolo tiene l'ultimo buono
    scrivi(pg, f"{K}portata", "abc")
    assert pg.get_attribute(f"{K}portata", "aria-invalid") == "true"
    assert not pg.errori, pg.errori
    ctx.close()


def test_righe_memoria_e_ripristino(base, browser):
    ctx, pg = apri(browser, base)
    lista = ".aria-trasformazioni-lista[data-stagione=estate]"
    riga = lambda i: f"{lista} .aria-trasformazioni-riga[data-riga='{i}']"  # noqa: E731
    frigo = val(pg, '[data-riep="estate.frigoTotale"]')
    post = val(pg, '[data-riep="estate.postRiscaldamento"]')
    # BF della batteria 0,10 → 0,2: più potenza di post-riscaldamento (la batteria fredda raffredda di più)
    pg.fill(f"{riga(1)} input[data-p='2']", "0,2")
    pg.wait_for_timeout(300)
    assert val(pg, '[data-riep="estate.postRiscaldamento"]') != pytest.approx(post, abs=1e-3)
    # tipo: post-riscaldamento → nessuna: l'immissione non si raggiunge più
    pg.select_option(f"{riga(2)} select", "Nessuna")
    pg.wait_for_timeout(300)
    assert leggi(pg, '[data-riep="estate.raggiungibile"]') == "NO"
    assert pg.locator('.messaggio[data-esito=estate]').get_attribute("data-raggiungibile") == "NO"
    assert "Riga inattiva" in leggi(pg, f"{riga(2)} .aria-trasformazioni-significato")
    # parametro non valido segnato
    pg.fill(f"{riga(3)} input[data-p='2']", "boh")
    assert pg.get_attribute(f"{riga(3)} input[data-p='2']", "aria-invalid") == "true"
    pg.fill(f"{riga(3)} input[data-p='2']", "")
    # sposta, aggiungi, togli
    pg.click(f"{riga(1)} button[data-azione=su]")
    pg.wait_for_timeout(300)
    assert pg.input_value(f"{riga(0)} select") == "Raffreddamento con deumidificazione"
    pg.click("#aria-trasf-estate button[data-azione=aggiungi]")
    pg.wait_for_timeout(200)
    assert pg.locator(f"{lista} .aria-trasformazioni-riga").count() == 7
    pg.click(f"{riga(6)} button[data-azione=togli]")
    pg.click(f"{riga(5)} button[data-azione=togli]")
    pg.wait_for_timeout(300)
    assert pg.locator(f"{lista} .aria-trasformazioni-riga").count() == 5
    memoria = json.loads(pg.evaluate("localStorage.getItem('eugenio-aria-trasf-v1')"))
    assert len(memoria["estate"]["righe"]) == 5 and memoria["estate"]["righe"][0][0] == "Raffreddamento con deumidificazione"
    # ricarica: la tabella resta
    pg.reload()
    pg.wait_for_function("window.EUGENIO_ARIA_PAGINA && window.EUGENIO_ARIA_PAGINA.scelta.serie() && window.EUGENIO_ARIA_PAGINA.clima()", timeout=20000)
    pg.wait_for_timeout(300)
    assert pg.locator(f"{lista} .aria-trasformazioni-riga").count() == 5
    assert pg.input_value(f"{riga(0)} select") == "Raffreddamento con deumidificazione"
    # svuota e preset
    pg.click("#aria-trasf-estate button[data-azione=svuota]")
    pg.wait_for_timeout(300)
    assert val(pg, '[data-riep="estate.frigoTotale"]') == 0
    pg.click("#aria-trasf-estate button[data-azione=preset]")
    pg.wait_for_timeout(300)
    assert [pg.input_value(f"{riga(i)} select") for i in range(4)] == ["Miscela con ricircolo", "Raffreddamento con deumidificazione", "Post-riscaldamento", "Ventilatore"]
    # nuvola delle ore
    pg.check(f"{K}nuvola")
    pg.wait_for_timeout(200)
    assert "ore" in {s["nome"] for s in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati()")}
    # ripristina predefiniti
    scrivi(pg, f"{K}portata", "7000")
    pg.click(f"{K}ripristina")
    pg.wait_for_timeout(300)
    assert pg.input_value(f"{K}portata") == "5000" and val(pg, '[data-riep="estate.frigoTotale"]') == pytest.approx(frigo, abs=1e-6)
    assert "ore" not in {s["nome"] for s in pg.evaluate("window.EUGENIO_ARIA_PAGINA.diagramma.strati()")}
    assert not pg.errori, pg.errori
    ctx.close()


def test_scaricamenti(base, browser):
    openpyxl = pytest.importorskip("openpyxl")
    ctx, pg = apri(browser, base)
    scrivi(pg, f"{K}portata", "4200")
    scrivi(pg, f"{K}estate-te", "33,5")
    frigo = val(pg, '[data-riep="estate.frigoTotale"]')
    with pg.expect_download() as dl:
        pg.click(f"{K}csv")
    csv = Path(dl.value.path()).read_text(encoding="utf-8-sig")
    assert "Portata di mandata [m³/h];4200" in csv and "T esterna [°C];33,5" in csv and "DATI SINTETICI DI PROVA" in csv
    assert f"Potenza frigorifera totale [kW];{round(frigo, 3):g}".replace(".", ",") in csv
    with pg.expect_download() as dl:
        pg.click(f"{K}json")
    j = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    assert j["configurazione"]["V"] == 4200 and j["risultati"]["estate"]["riepilogo"]["frigoTotale"] == pytest.approx(frigo)
    assert j["licenza"] == "CC BY 4.0" and j["serie"]["sintetica"] is True and len(j["risultati"]["inverno"]["righe"]) == 6
    with pg.expect_download(timeout=30000) as dl:
        pg.click(f"{K}xlsx")
    nome = dl.value.suggested_filename
    dati = Path(dl.value.path()).read_bytes()
    assert nome.endswith("psicro_UTA.xlsx") and zipfile.is_zipfile(io.BytesIO(dati))
    ws = openpyxl.load_workbook(io.BytesIO(dati))["UTA"]
    conf = pg.evaluate("window.EUGENIO_ARIA_PAGINA.configurazione()")
    assert ws["D10"].value == 4200 and ws["D18"].value == 33.5 and ws["D50"].value == 20 and ws["D51"].value == 40
    assert ws["D48"].value == conf["inverno"]["esterno"]["t"] and ws["C29"].value == "Raffreddamento con deumidificazione" and ws["D29"].value == "AUTO"
    assert ws["E29"].value == 0.1 and ws["D78"].value == 2259 and str(ws["H9"].value).startswith("=")
    assert "Download avviato" in leggi(pg, "#aria-trasf-scarica .messaggio")
    with pg.expect_download() as dl:
        pg.click(f"{K}svg")
    assert dl.value.suggested_filename == "eugenio-aria-trasformazioni-psicrometrico.svg"
    assert not pg.errori, pg.errori
    ctx.close()
