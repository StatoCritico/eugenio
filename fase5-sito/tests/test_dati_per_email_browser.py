"""Pagina «Dati per email» (14/11/2026) in Chromium, con l'API finta: collegamento personale, scelte (regioni fino a 3,
comuni fino a 5, avvisi con l'avvertenza), salvataggio, cancellazione da un servizio, gettone tolto dalla barra."""
from __future__ import annotations

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITO = Path(__file__).resolve().parent.parent / "sito"
AVVERTENZA = ("Il servizio di avvisi meteo è gratuito, non fornisce garanzie e non sostituisce le allerte della "
              "Protezione Civile e degli enti pubblici.")
OPZIONI = {"attivo": True, "max_regioni": 3, "max_comuni": 5, "giorno_mensile": 12, "avvertenza": AVVERTENZA,
           "settimanale": {"giorno": 6, "ora": 17}, "ora_avvisi": 15,
           "regioni": [{"cod": c, "nome": n} for c, n in (("01", "Piemonte"), ("03", "Lombardia"), ("05", "Veneto"),
                                                         ("08", "Emilia-Romagna"), ("09", "Toscana"))],
           "avvisi": [{"id": "pioggia", "nome": "Pioggia forte", "soglia": "almeno 40 mm di pioggia nelle 24 ore"},
                      {"id": "neve", "nome": "Neve", "soglia": "almeno 2 cm di neve fresca"},
                      {"id": "vento", "nome": "Vento molto forte", "soglia": "raffiche di almeno 75 km/h"}]}
COMUNI = [{"istat": i, "nome": n, "provincia": p, "regione_cod": r} for i, n, p, r in (
    ("040007", "Cesena", "FC", "08"), ("040008", "Cesenatico", "FC", "08"), ("037006", "Bologna", "BO", "08"),
    ("015146", "Milano", "MI", "03"), ("099014", "Rimini", "RN", "08"), ("039014", "Ravenna", "RA", "08"),
    ("040012", "Forlì", "FC", "08"))]


class Gestore(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Gestore, directory=str(SITO)))
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


def _pagina(browser, chiamate, stato=None):
    pg = browser.new_page(viewport={"width": 1200, "height": 900})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))

    def api(route):
        req = route.request
        percorso = req.url.split("/api/email", 1)[1].split("?")[0]
        corpo = json.loads(req.post_data) if req.post_data else None
        chiamate.append((percorso, corpo))
        risposte = {
            "/opzioni": OPZIONI, "/comuni": COMUNI, "/link": {"inviato": True},
            "/leggi": stato or {"email": "mario@esempio.it", "mensile": True, "settimanale": False, "avvisi": ["neve"],
                                "regioni": ["08"], "comuni": [{"istat": "040007", "nome": "Cesena", "provincia": "FC"}]},
            "/via": {"cancellato": "avvisi", "preferenze": "t=v1.pref.9.i3.f"}}
        if percorso == "/salva":
            nomi = {c["istat"]: c for c in COMUNI}
            r = {"email": "mario@esempio.it", "mensile": corpo["mensile"], "settimanale": corpo["settimanale"],
                 "avvisi": corpo["avvisi"], "regioni": corpo["regioni"],
                 "comuni": [{k: nomi[i][k] for k in ("istat", "nome", "provincia")} for i in corpo["comuni"]]}
        else:
            r = risposte[percorso]
        route.fulfill(status=200, content_type="application/json", body=json.dumps(r))
    pg.route("**/api/email/**", api)
    pg.route("**/api/protezione", lambda r: r.fulfill(status=200, content_type="application/json",
                                                      body=json.dumps({"turnstile": None, "rotte": []})))
    return pg, errori


def test_collegamento_personale(base, browser):
    chiamate = []
    pg, errori = _pagina(browser, chiamate)
    pg.goto(base + "dati-per-email.html")
    pg.wait_for_selector("#dpe-chiedi:not([hidden])")
    assert pg.locator("#dpe-scelte").is_hidden()
    pg.fill("#dpe-email", "sbagliato")
    pg.click("#dpe-manda")
    assert "valido" in pg.locator("#dpe-esito-email").inner_text()
    pg.fill("#dpe-email", "mario@esempio.it")
    pg.click("#dpe-manda")
    pg.wait_for_function("document.getElementById('dpe-esito-email').textContent.includes('Fatto')")
    assert ("/link", {"email": "mario@esempio.it"}) in chiamate
    # menu: Clima e meteo › «Newsletter e avvisi» porta qui; niente più «Iscriviti»
    assert pg.locator("a.iscriviti").count() == 0
    voce = pg.locator('details[data-gruppo="clima"] a[href="dati-per-email.html"]')
    assert voce.count() == 2 and voce.first.inner_text().strip() == "Newsletter e avvisi"
    assert not errori, errori
    pg.close()


def test_scelte_e_salvataggio(base, browser):
    chiamate = []
    pg, errori = _pagina(browser, chiamate)
    pg.goto(base + "dati-per-email.html#t=v1.pref.99.eabc.firma")
    pg.wait_for_selector("#dpe-scelte:not([hidden]) #dpe-regioni input")
    assert "#t=" not in pg.url                                         # gettone tolto dalla barra
    assert ("/leggi", {"t": "v1.pref.99.eabc.firma"}) in chiamate
    assert pg.locator("#dpe-mensile").is_checked() and not pg.locator("#dpe-settimanale").is_checked()
    assert pg.locator("#dpe-regioni input:checked").evaluate_all("(a) => a.map((x) => x.value)") == ["08"]
    assert pg.locator("#dpe-avvisi input:checked").evaluate_all("(a) => a.map((x) => x.value)") == ["neve"]
    assert pg.locator("#dpe-avvertenza").inner_text() == AVVERTENZA
    assert "75 km/h" in pg.locator("#dpe-avvisi").inner_text()
    # regioni: alla terza le altre si spengono
    pg.locator("#dpe-regioni input[value='03']").check()
    pg.locator("#dpe-regioni input[value='05']").check()
    assert pg.locator("#dpe-regioni input[value='09']").is_disabled()
    pg.locator("#dpe-regioni input[value='05']").uncheck()
    assert not pg.locator("#dpe-regioni input[value='09']").is_disabled()
    # comuni: ricerca senza accenti, fino a 5
    pg.fill("#dpe-cerca", "forli")
    pg.wait_for_selector("#dpe-risultati button")
    pg.locator("#dpe-risultati button").first.click()
    for nome in ("Bologna", "Milano", "Rimini"):
        pg.fill("#dpe-cerca", nome[:4])
        pg.wait_for_selector(f"#dpe-risultati button:has-text('{nome}')")
        pg.locator("#dpe-risultati button", has_text=nome).click()
    assert pg.locator("#dpe-comuni li").count() == 5 and pg.locator("#dpe-cerca").is_disabled()
    pg.locator("#dpe-comuni button[aria-label='Togli Milano']").click()
    assert pg.locator("#dpe-comuni li").count() == 4 and not pg.locator("#dpe-cerca").is_disabled()
    pg.locator("#dpe-settimanale").check()
    pg.locator("#dpe-avvisi input[value='vento']").check()
    pg.click("#dpe-salva")
    pg.wait_for_function("document.getElementById('dpe-esito').textContent.startsWith('Salvato')")
    corpo = [c for p, c in chiamate if p == "/salva"][0]
    assert corpo == {"t": "v1.pref.99.eabc.firma", "mensile": True, "regioni": ["03", "08"], "settimanale": True,
                     "comuni": ["040007", "040012", "037006", "099014"], "avvisi": ["neve", "vento"]}
    assert pg.locator("#dpe-esito").inner_text() == ("Salvato. Riceverai la newsletter mensile, le previsioni "
                                                     "settimanali e gli avvisi meteo.")
    # senza comuni le previsioni non si salvano
    while pg.locator("#dpe-comuni button").count():
        pg.locator("#dpe-comuni button").first.click()
    pg.click("#dpe-salva")
    assert "almeno un comune" in pg.locator("#dpe-esito").inner_text()
    assert len([p for p, _ in chiamate if p == "/salva"]) == 1
    assert not errori, errori
    pg.close()


def test_cancellazione(base, browser):
    chiamate = []
    pg, errori = _pagina(browser, chiamate)
    pg.goto(base + "dati-per-email.html#via=v1.via.99.i3.8.firma")
    pg.wait_for_function("document.getElementById('dpe-esito-via').textContent.includes('Fatto')")
    assert "non riceverai più gli avvisi meteo" in pg.locator("#dpe-esito-via").inner_text()
    assert ("/via", {"t": "v1.via.99.i3.8.firma"}) in chiamate
    pg.click("#dpe-esito-via a")
    pg.wait_for_selector("#dpe-scelte:not([hidden]) #dpe-regioni input")
    assert ("/leggi", {"t": "v1.pref.9.i3.f"}) in chiamate
    assert not errori, errori
    pg.close()


def test_servizio_spento(base, browser):
    pg = browser.new_page()
    pg.route("**/api/email/opzioni", lambda r: r.fulfill(status=200, content_type="application/json",
                                                         body=json.dumps({"attivo": False})))
    pg.goto(base + "dati-per-email.html")
    pg.wait_for_selector("#dpe-spento:not([hidden])")
    assert "subscription/form" in pg.locator("#dpe-spento a").get_attribute("href")
    pg.close()
