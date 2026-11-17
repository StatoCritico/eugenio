"""Pagine «Esempi» e «Contributi» (15/11/2026, richiesta di Paolo).

- Contributi: tra le «Altre pagine», prima di Contattaci (riga in alto e menu del telefono); collegamento alla discussione
  del forum Edilclima e a Contattaci; sezione «Ringraziamenti» con la frase di Paolo (15/11 sera), senza nomi per ora.
- Esempi (15/11 sera): tra le «Altre pagine», dopo Novità e prima di Contributi (riga in alto e menu del telefono), non
  più nel menu dei servizi; un titolo per gruppo nell'ordine del menu, con l'indice in cima; ogni collegamento
  interno porta a un file che esiste e mai a una pagina in lavorazione o in attesa del GME; ogni pagina accessibile del
  menu ha almeno un esempio, ogni pagina non accessibile è citata come «in arrivo».
- In Chromium (si salta se Playwright o Chromium non ci sono): la voce Esempi della riga in alto è visibile, su una riga
  sola con le altre voci e dentro la finestra da 861 px in su (sotto è nel pulsante Menu, tra le «Altre pagine»), porta
  alla pagina senza fissare la riga nera; la pagina non scorre in orizzontale a 1366, 1100, 1000, 900 e 375 px, nessun
  errore JavaScript.
"""
from __future__ import annotations

import functools
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent.parent
SITO = QUI / "sito"
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

FORUM = "https://forum.edilclima.it/viewtopic.php?t=38424"


def _testata() -> str:
    return (C.PARTI / "testata.html").read_text(encoding="utf-8")


def _pagina(nome: str) -> str:
    return (SITO / nome).read_text(encoding="utf-8")


def _main(s: str) -> str:
    return re.search(r"<main.*?</main>", s, re.S).group(0)


def test_pagine_esistono_e_sono_aggiornate():
    for nome in ("esempi.html", "contributi.html"):
        s = _pagina(nome)
        assert "<!-- testata -->" in s and 'class="articolo' in s, nome
        assert s.count('aria-current="page"') == 2, nome          # menu del computer e del telefono
    assert C.main(["--controlla"]) == 0


ALTRE = ["metodo.html", "faq.html", "sitografia.html", "mirror.html", "novita.html", "esempi.html", "contributi.html",
         "contatti.html"]   # (15/11/2026 sera) … Novità · Esempi · Contributi · Contattaci


def test_esempi_e_contributi_nelle_altre_pagine_prima_di_contattaci():
    t = _testata()
    info = re.search(r'<nav class="menu-info"[^>]*>(.*?)</nav>', t, re.S).group(1)
    assert re.findall(r'href="([^"]+)"', info) == ALTRE
    assert re.findall(r'>([^<]+)</a>', info)[-3:] == ["Esempi", "Contributi", "Contattaci"]
    altre = re.search(r"<h2>Altre pagine</h2>\s*<ul>(.*?)</ul>", t, re.S).group(1)       # menu del telefono
    assert re.findall(r'href="([^"]+)"', altre) == ALTRE


def test_esempi_non_piu_nel_menu_dei_servizi():
    t = _testata()
    gruppi = re.search(r'<ul class="menu-gruppi">(.*?)</ul>\s*</nav>', t, re.S).group(1)
    voci = re.findall(r'^        <li>(.*?)(?=^        <li>|\Z)', gruppi, re.S | re.M)
    assert len(voci) == 7 and 'data-gruppo="statistiche"' in voci[-1]
    assert "esempi.html" not in gruppi
    # telefono: dopo l'ultimo gruppo viene subito «Altre pagine»
    pannello = re.search(r'<nav class="menu-pannello".*?<h2>Altre pagine</h2>', t, re.S).group(0)
    assert re.search(r'data-gruppo="statistiche">.*?</details>\s*<h2>Altre pagine', pannello, re.S)
    assert t.count('href="esempi.html"') == 2                                          # riga in alto e telefono
    # niente più CSS della vecchia voce diretta
    css = (SITO / "stile.css").read_text(encoding="utf-8")
    assert "voce-diretta" not in css and "pannello-voce" not in css
    assert [g["id"] for g in C.gruppi_menu(t)][-1] == "statistiche"
    assert "esempi" not in (C.PARTI / "testa.html").read_text(encoding="utf-8")


def test_contributi_forum_contattaci_ringraziamenti():
    m = _main(_pagina("contributi.html"))
    assert f'href="{FORUM}"' in m and "meet EuGEnio (ovvero a cosa serve l'AI per i tecnici?" in m
    assert 'href="contatti.html"' in m
    assert 'id="ringraziamenti"' in m
    ringr = re.search(r'<h2 id="ringraziamenti">Ringraziamenti</h2>\s*<p>(.*?)</p>', m, re.S).group(1)
    assert re.sub(r"\s+", " ", ringr) == ("In questa pagina verranno ringraziati coloro che hanno contribuito allo "
                                          "sviluppo del sito.")                      # (15/11/2026 sera) frase di Paolo
    # (17/11/2026) primi utenti del forum ringraziati, con il collegamento al loro profilo
    assert "ringraziamo per il loro prezioso contributo i seguenti utenti del forum" in re.sub(r"\s+", " ", m)
    assert '<a href="https://forum.edilclima.it/memberlist.php?mode=viewprofile&amp;u=10826">Esa</a>' in m


def test_esempi_gruppi_indice_e_collegamenti():
    t = _testata()
    gruppi = C.gruppi_menu(t)
    m = _main(_pagina("esempi.html"))
    titoli = re.findall(r'<h2 id="([^"]+)">([^<]+)</h2>', m)
    assert [x[1] for x in titoli] == [g["titolo"] for g in gruppi]
    indice = re.search(r'<nav class="indice"[^>]*>(.*?)</nav>', m, re.S).group(1)
    assert re.findall(r'href="#([^"]+)"', indice) == [x[0] for x in titoli]
    vietate = {v["pagina"] for g in gruppi for v in g["voci"] if v["tipo"]}            # in lavorazione e GME
    assert len(vietate) >= 19
    collegate = set()
    for href in re.findall(r'<a [^>]*href="([^"]+)"', m):
        if href.startswith(("#", "http")):
            continue
        pagina = href.split("#")[0]
        assert pagina not in vietate, href
        assert (SITO / ("index.html" if pagina == "./" else pagina)).exists(), href
        collegate.add(pagina)
    # ogni pagina accessibile del menu ha almeno un esempio; le altre sono «in arrivo», per nome e senza collegamento
    for g in gruppi:
        sezione = re.search(rf'<h2 id="[^"]+">{re.escape(g["titolo"])}</h2>(.*?)(?=<h2 |</main>)', m, re.S).group(1)
        for v in g["voci"]:
            if v["tipo"]:
                arrivo = re.search(r'<p class="esempi-arrivo"><strong>In arrivo:</strong>(.*?)</p>', sezione, re.S)
                assert arrivo and v["nome"] in re.sub(r"\s+", " ", arrivo.group(1)), (g["titolo"], v["nome"])
            else:
                assert f'href="{v["pagina"]}"' in sezione, (g["titolo"], v["pagina"])
    # nessun dato di mercato
    for vietato in ("PUN", "TTF", "IGI", "€/MWh"):
        assert vietato not in m, vietato


# ---------------------------------------------------------------------------------------------- Chromium
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
    pw = pytest.importorskip("playwright.sync_api")     # qui e non in cima: le prove sui file restano anche senza Playwright
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def test_browser_voce_esempi_e_larghezze(base, browser):
    for larghezza in (1366, 1100, 1000, 900, 375):
        for nome in ("esempi.html", "contributi.html", "faq.html"):
            ctx = browser.new_context(viewport={"width": larghezza, "height": 800})
            pg = ctx.new_page()
            errori = []
            pg.on("pageerror", lambda e: errori.append(str(e)))
            pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
            pg.goto(base + nome)
            pg.wait_for_load_state("load")
            assert pg.evaluate("document.documentElement.scrollWidth") <= larghezza, (larghezza, nome)
            if larghezza > 860 and nome == "faq.html":
                # riga in alto: otto voci su una riga sola, dentro la finestra, Esempi tra Novità e Contributi
                righe = pg.evaluate("""() => [...document.querySelectorAll('.testata-alta .menu-info a')].map((a) => {
                  const r = a.getBoundingClientRect(); return [a.textContent.trim(), Math.round(r.top), r.left, r.right]; })""")
                assert [x[0] for x in righe][-4:] == ["Novità", "Esempi", "Contributi", "Contattaci"], righe
                assert len({x[1] for x in righe}) == 1 and righe[0][2] >= 0 and righe[-1][3] <= larghezza, (larghezza, righe)
                # la frase «un servizio per uno Stato Critico» non si sovrappone alle voci
                assert pg.locator(".testata-alta .sezione").bounding_box()["x"] + \
                    pg.locator(".testata-alta .sezione").bounding_box()["width"] <= righe[0][2], larghezza
                assert pg.locator("a.voce-diretta").count() == 0
                # ✱ e ◐ restano dentro la finestra anche quando i gruppi vanno a capo
                assert pg.locator(".testata-menu .tema").bounding_box()["x"] + 36 <= larghezza
                voce = pg.locator('.testata-alta .menu-info a[href="esempi.html"]')
                assert voce.is_visible()
                voce.click()
                pg.wait_for_load_state("load")
                assert pg.url.endswith("esempi.html")
                assert pg.evaluate("document.documentElement.dataset.menuFissato || null") is None
                assert pg.locator("details.voce-gruppo[open]").count() == 0
            if larghezza <= 860 and nome == "faq.html":
                # telefono: la riga in alto non c'è, Esempi e Contributi sono tra le «Altre pagine» del pulsante Menu
                assert not pg.locator(".testata-alta .menu-info").is_visible()
                pg.click(".menu-tutto > summary")
                voci = pg.locator(".menu-pannello h2:has-text('Altre pagine') + ul a").all_inner_texts()
                assert [v.strip() for v in voci][-3:] == ["Esempi", "Contributi", "Contattaci"], voci
                assert pg.locator('.menu-pannello a[href="esempi.html"]').count() == 1
            ctx.close()
            assert not errori, (larghezza, nome, errori)
