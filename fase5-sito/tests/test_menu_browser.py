"""Prova nel browser (Chromium headless, Playwright) del menu dei servizi (04/11/2026).

- il mouse sul titolo di un gruppo apre la tendina verticale, l'uscita la chiude;
- il clic sul titolo fissa il gruppo nella riga nera sotto la barra, il clic su un altro gruppo la cambia, il secondo clic
  sullo stesso titolo la toglie; la scelta resta al cambio di pagina;
- le voci «licenza GME» non sono collegamenti e hanno il suggerimento «In attesa di autorizzazione dal GME»;
- (08/11/2026) sei gruppi; le voci «in lavorazione» (Edifici, Cogenerazione, Fotovoltaico) non sono collegamenti, hanno il
  triangolo giallo e il suggerimento «In lavorazione: disponibile prossimamente»; le tendine sono larghe quanto la voce più
  lunga (nessuna voce va a capo) e stanno nella finestra; frecce della tastiera nei gruppi senza collegamenti senza errori;
- a 375 px la riga scorre dentro di sé, la pagina non scorre in orizzontale e il pulsante × la chiude;
- nessun errore JavaScript.
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
G = "details.voce-gruppo[data-gruppo={}]"


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


def pagina(browser, larghezza, altezza=800):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza})
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    return ctx, pg


def aperto(pg, gruppo):
    return pg.evaluate(f"document.querySelector('{G.format(gruppo)}').open")


def fissato(pg):
    return pg.evaluate("document.documentElement.dataset.menuFissato || null")


def test_menu_computer(base, browser):
    ctx, pg = pagina(browser, 1366)
    pg.goto(base + "lidar.html")
    titolo = G.format("patrimonio") + " > summary"
    assert pg.get_attribute(titolo, "title") == "Clicca qui per fissare il menu Patrimonio sotto la barra"
    assert pg.get_attribute(titolo, "aria-pressed") == "false"
    # passaggio del mouse
    pg.hover(G.format("edificio") + " > summary")
    assert aperto(pg, "edificio")
    pg.mouse.move(700, 650)
    pg.wait_for_timeout(400)
    assert not aperto(pg, "edificio")
    # clic: si fissa, la tendina di quel gruppo non si apre
    pg.click(titolo)
    assert fissato(pg) == "patrimonio" and not aperto(pg, "patrimonio")
    assert pg.get_attribute(titolo, "aria-pressed") == "true"
    assert "richiudere la barra di Patrimonio" in pg.get_attribute(titolo, "title")
    riga = pg.locator("nav.riga-fissata")
    assert riga.evaluate("r => getComputedStyle(r).backgroundColor") == "rgb(0, 0, 0)"
    assert riga.locator(".riga-voci > li").count() == 8          # dal 07/11/2026 anche Aggiungi edifici e Scaricare i DB topografici
    assert riga.locator("a[aria-current=page]").inner_text().startswith("LiDAR")
    pg.mouse.move(700, 650)
    pg.hover(titolo)
    pg.wait_for_timeout(100)
    assert not aperto(pg, "patrimonio")
    # un altro gruppo: la riga passa a quello; le voci GME e quelle in lavorazione nella riga non sono collegamenti
    pg.click(G.format("cogenerazione") + " > summary")
    assert fissato(pg) == "cogenerazione"
    assert riga.locator(".voce-gme").count() == 6 and riga.locator("a").count() == 0
    assert riga.locator(".voce-gme").first.get_attribute("title") == "In attesa di autorizzazione dal GME"
    assert riga.locator(".voce-corso").count() == 1 and riga.locator(".voce-corso").get_attribute("title") == "In lavorazione: disponibile prossimamente"
    # al cambio di pagina (pagina in lavorazione aperta con l'indirizzo diretto) la riga resta, con la voce della pagina
    pg.goto(base + "cog-emissioni.html")
    pg.wait_for_load_state("load")
    assert fissato(pg) == "cogenerazione" and riga.locator("[aria-current=page]").count() == 1
    assert pg.locator(".avviso-lavorazione").is_visible() and "Pagina in lavorazione, non ancora verificata" in pg.locator(".avviso-lavorazione").inner_text()
    # voce GME e voci in lavorazione nella tendina: niente collegamento, il clic non cambia pagina
    pg.hover(G.format("fotovoltaico") + " > summary")
    gme = pg.locator(G.format("fotovoltaico") + " .tendina .voce-gme:not(.voce-corso)")
    assert gme.count() == 1 and gme.get_attribute("aria-disabled") == "true"
    corso = pg.locator(G.format("fotovoltaico") + " .tendina .voce-corso")
    assert corso.count() == 7 and pg.locator(G.format("fotovoltaico") + " .tendina a").count() == 0
    assert corso.first.get_attribute("title") == "In lavorazione: disponibile prossimamente"
    assert corso.first.locator("svg.segnale path[fill='#f5c400']").count() == 1           # triangolo giallo
    assert float(corso.first.evaluate("e => getComputedStyle(e).opacity")) < 1 and corso.first.evaluate("e => getComputedStyle(e).cursor") == "not-allowed"
    url = pg.url
    gme.click()
    corso.last.click()
    pg.wait_for_timeout(150)
    assert pg.url == url and "con-nota" in corso.last.get_attribute("class")
    # secondo clic sullo stesso titolo: la riga sparisce e torna la tendina
    pg.mouse.move(700, 650)
    pg.click(G.format("cogenerazione") + " > summary")
    assert fissato(pg) is None
    assert riga.evaluate("r => getComputedStyle(r).display") == "none"
    assert aperto(pg, "cogenerazione")
    pg.reload()
    assert fissato(pg) is None
    # tastiera: Tab apre, Esc chiude, Invio fissa e richiude
    pg.mouse.move(700, 650)
    pg.focus("a.marchio")
    pg.keyboard.press("Tab")
    while not pg.evaluate("document.activeElement.matches('details.voce-gruppo > summary')"):
        pg.keyboard.press("Tab")
    assert aperto(pg, "clima")
    pg.keyboard.press("Escape")
    assert not aperto(pg, "clima")
    pg.keyboard.press("Enter")
    assert fissato(pg) == "clima"
    pg.keyboard.press("ArrowDown")
    assert pg.evaluate("document.activeElement.closest('nav.riga-fissata') !== null")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Enter")
    assert fissato(pg) is None
    assert pg.evaluate("document.documentElement.scrollWidth") <= 1366
    assert not pg.errori, pg.errori
    ctx.close()


def test_menu_telefono(base, browser):
    ctx, pg = pagina(browser, 375, 740)
    pg.goto(base + "index.html")
    pg.evaluate("localStorage.setItem('menu-fissato', 'fotovoltaico')")      # (08/11/2026) Comunità energetiche nel Fotovoltaico
    pg.goto(base + "edificio-cer.html")
    riga = pg.locator("nav.riga-fissata")
    assert riga.evaluate("r => getComputedStyle(r).display") == "block"
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    assert riga.locator(".riga-voci").evaluate("u => u.scrollWidth > u.clientWidth && getComputedStyle(u).overflowX === 'auto'")
    box = riga.locator("[aria-current=page]").bounding_box()
    assert box and box["x"] >= 0 and box["x"] < 375                       # la voce della pagina aperta è in vista
    # voce GME nel menu del telefono: niente collegamento, il tocco mostra la nota
    pg.click("details.menu-tutto > summary")
    pg.click("details.pannello-gruppo[data-gruppo=cogenerazione] > summary")
    gme = pg.locator("details.pannello-gruppo[data-gruppo=cogenerazione] .voce-gme").first
    url = pg.url
    gme.click()
    assert pg.url == url and "con-nota" in gme.get_attribute("class")
    pg.keyboard.press("Escape")
    pg.click("nav.riga-fissata .riga-chiudi")
    assert riga.evaluate("r => getComputedStyle(r).display") == "none"
    assert pg.evaluate("localStorage.getItem('menu-fissato')") is None
    assert not pg.errori, pg.errori
    ctx.close()


def test_novita_telefono_e_pallino(base, browser):
    """Novità (07/11/2026): la pagina non scorre in orizzontale a 375 px, l'indice elenca le versioni; il pallino compare
    sul collegamento solo se l'ultima versione vista è più vecchia, e sparisce dopo aver aperto la pagina."""
    ctx, pg = pagina(browser, 375)
    pg.goto(base + "novita.html")
    pg.wait_for_load_state("load")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    assert pg.locator("main.novita h2").count() >= 8
    assert pg.evaluate("localStorage.getItem('novita-vista')") == pg.get_attribute("a.voce-novita >> nth=0", "data-ultima")
    pg.evaluate("localStorage.setItem('novita-vista', '20261001a')")
    pg.goto(base + "faq.html")
    pg.wait_for_load_state("load")
    assert pg.locator("a.voce-novita.con-novita").count() == 2                 # menu del computer e del telefono
    pg.goto(base + "novita.html"); pg.wait_for_load_state("load")
    pg.goto(base + "faq.html"); pg.wait_for_load_state("load")
    assert pg.locator("a.voce-novita.con-novita").count() == 0
    assert not pg.errori, pg.errori
    ctx.close()


def test_voce_novita_come_le_altre(browser, base):
    """«Novità» (07/11/2026 sera, prova 11 di Paolo: «blu elettrico»): stesso colore calcolato di «F.A.Q.» nella riga in
    alto e nel menu del telefono, in tutti e 5 i vestiti, tema chiaro e scuro, con e senza il pallino delle novità; nella
    propria pagina come «F.A.Q.» nella sua."""
    def colori(pg):
        return pg.evaluate("""() => { const c = (sel) => { const e = document.querySelector(sel); return e ? getComputedStyle(e).color : null; };
          return [c('.menu-info a.voce-novita'), c('.menu-info a[href="faq.html"]'), c('.menu-pannello a.voce-novita'), c('.menu-pannello a[href="faq.html"]'),
                  c('.menu-info a[aria-current="page"]')]; }""")
    for vestito in ("corallo", "ambra", "indaco", "lime", "verde"):
        for tema in ("dark", "light"):
            for pallino in (False, True):
                ctx = browser.new_context(viewport={"width": 1366, "height": 800})
                ctx.add_init_script(f"""try {{ localStorage.setItem('vestito', '{vestito}'); {"localStorage.setItem('tema', 'light');" if tema == "light" else ""}
                    localStorage.setItem('novita-vista', '{"20261001a" if pallino else "29991231z"}'); }} catch (e) {{}}""")
                pg = ctx.new_page()
                pg.goto(base + "metodo.html")
                n, f, n2, f2, _ = colori(pg)
                assert n == f and n2 == f2, (vestito, tema, pallino, n, f, n2, f2)
                assert pg.evaluate("document.querySelector('.menu-info a.voce-novita').classList.contains('con-novita')") == pallino
                pg.goto(base + "novita.html"); cur_n = colori(pg)[4]
                pg.goto(base + "faq.html"); cur_f = colori(pg)[4]
                assert cur_n == cur_f, (vestito, tema, cur_n, cur_f)
                ctx.close()


def test_menu_08_11_sei_gruppi_tendine_e_tastiera(base, browser):
    """(08/11/2026) Sei gruppi nell'ordine; Edifici con «Obblighi di legge» in cima e solo voci in lavorazione; Cambiamento
    climatico ultima voce di Clima e meteo; ogni voce di ogni tendina su una riga, tendina dentro la finestra (1366, 1000 e
    900 px); frecce della tastiera su un gruppo senza collegamenti: nessun errore."""
    for larghezza in (1366, 1000, 900):
        ctx, pg = pagina(browser, larghezza)
        pg.goto(base + "faq.html")
        titoli = pg.locator("details.voce-gruppo > summary").all_inner_texts()
        assert [t.strip() for t in titoli] == ["Clima e meteo", "Patrimonio", "Edifici", "Cogenerazione", "Fotovoltaico", "Statistiche"]
        for g in ("clima", "patrimonio", "edificio", "cogenerazione", "fotovoltaico", "statistiche"):
            pg.hover(G.format(g) + " > summary")
            assert aperto(pg, g)
            d = pg.evaluate(f"""() => {{ const t = document.querySelector('{G.format(g)} .tendina'), b = t.getBoundingClientRect();
              const righe = [...t.querySelectorAll(':scope > li > *')].map((e) => {{ const n = e.querySelector('.voce-nome') || e;
                const r = document.createRange(); r.selectNodeContents(n.firstChild); return r.getClientRects().length; }});
              return {{ left: b.left, right: b.right, righe }}; }}""")
            assert d["left"] >= 0 and d["right"] <= larghezza and set(d["righe"]) == {1}, (larghezza, g, d)
            pg.mouse.move(5, 700)
            pg.wait_for_timeout(250)
        assert pg.locator(G.format("clima") + " .tendina > li").last.text_content().strip().startswith("Cambiamento climatico")
        assert pg.locator(G.format("edificio") + " .tendina > li").first.text_content().strip().startswith("Obblighi di legge")
        assert pg.locator(G.format("edificio") + " .tendina a").count() == 0
        assert pg.locator(G.format("edificio") + " .tendina .voce-corso").count() == 8
        ctx.close()
    ctx, pg = pagina(browser, 1366)
    pg.goto(base + "faq.html")
    pg.focus(G.format("edificio") + " > summary")
    for k in ("ArrowDown", "ArrowDown", "ArrowUp", "End", "Escape"):
        pg.keyboard.press(k)
    assert not pg.errori, pg.errori
    ctx.close()
