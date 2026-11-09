"""Prove nel browser delle correzioni del 09/11/2026 (prove J10 di Paolo, punti A–J): limite orario di una fonte della
mappa (pausa, nota sotto la mappa, nessuna richiesta ripetuta), ricerca con Comune prima dell'Indirizzo, «Reset» e tutti i
comuni italiani (Torino), clic sulla mappa che non sposta la vista, colore degli edifici e alberi ricordati, frecce
dell'ortofoto su una riga. Rotte /api simulate, nessuna rete; si salta senza Playwright o Chromium."""
from __future__ import annotations

import io
import json

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import attendi, base, browser, pagina, webgl  # noqa: E402,F401  (fixture condivise)

M3D = "window.EUGENIO_EDIFICIO3D.stato"


def _jpeg():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (256, 256), (120, 120, 120)).save(b, "JPEG")
    return b.getvalue()


def test_limite_orario_ferma_la_fonte_e_lo_dice_sotto_la_mappa(browser, base):
    """Punto A: dopo un 429 con Retry-After la pagina non chiede più tessere a quella fonte, la nota sotto la mappa (prima
    di «Genera il 3D») dice quale fonte, il limite orario e tra quanto riprova; alla ripresa la nota sparisce."""
    ctx, pg = pagina(browser)
    chieste, stato = [], {"rifiuta": True}
    jpg = _jpeg()

    def servi(r):
        chieste.append(r.request.url)
        if stato["rifiuta"]:
            r.fulfill(status=429, content_type="application/json", body=json.dumps({"detail": "Troppe richieste"}),
                      headers={"Retry-After": "240", "X-EuGEnio-Limite": "ortofoto"})
        else:
            r.fulfill(status=200, content_type="image/jpeg", body=jpg)
    pg.route("**/api/ortofoto/rer2023/**", servi)
    rossi = []
    pg.on("console", lambda m: rossi.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, "!!document.getElementById('nota-limiti') && !document.getElementById('nota-limiti').hidden", 30000)
    t = pg.text_content("#nota-limiti")
    assert "Ortofoto" in t and "limite orario" in t and "4 minuti" in t, t
    assert pg.evaluate("document.getElementById('nota-limiti').nextElementSibling.id") == "comandi-edificio"
    pg.wait_for_timeout(800)
    n = len(chieste)
    # la mappa si sposta: nessuna nuova richiesta alla fonte ferma
    pg.evaluate(f"{M3D}.mappa.jumpTo({{center: [12.27, 44.14], zoom: 16.5}})")
    pg.wait_for_timeout(1500)
    assert len(chieste) == n, (n, len(chieste))
    assert not any("AJAXError" in x or "429" in x for x in rossi), rossi[:3]
    # fine della pausa: le tessere si ricaricano e la nota sparisce alla prima risposta buona
    stato["rifiuta"] = False
    pg.evaluate("(() => { const L = window.EUGENIO_LIMITI, p = L.pause.ortofoto; clearTimeout(p.timer); p.fino = Date.now() - 1; L.riprendi('ortofoto'); })()")
    attendi(pg, "document.getElementById('nota-limiti').hidden", 15000)
    assert len(chieste) > n
    assert not pg.errori, pg.errori
    ctx.close()


def test_ricerca_comune_prima_reset_e_torino(browser, base):
    """Punto D (09/11) e ricerca unificata (09/11 b): un solo Comune in cima, poi Indirizzo, Foglio e Particella; un solo
    «Reset» che svuota tutto; Torino trovata (prima il file del Piemonte aveva un NaN e il browser non lo leggeva)."""
    ctx, pg = pagina(browser)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!document.getElementById('cerca-comune')", 30000)
    ordine = pg.evaluate("[...document.querySelectorAll('#cerca-luogo-modulo input')].map((i) => i.id)")
    assert ordine == ["cerca-comune", "cerca-via", "catasto-foglio", "catasto-particella"], ordine
    pg.fill("#cerca-comune", "Roma"); pg.fill("#cerca-via", "corso Cavour 12")
    pg.fill("#catasto-foglio", "149"); pg.fill("#catasto-particella", "387")
    pg.click("#cerca-reset")
    assert [pg.input_value(x) for x in ("#cerca-comune", "#cerca-via", "#catasto-foglio", "#catasto-particella")] == ["", "", "", ""]
    c = pg.evaluate("window.EUGENIO_CERCA.centroComune('torino')")
    assert c and c["istat"] == "001272" and abs(c["lat"] - 45.07) < 0.1, c
    assert pg.evaluate("window.EUGENIO_CERCA.centroComune('Napoli')")["istat"] == "063049"
    pg.fill("#cerca-comune", "Torino")
    pg.click("#cerca-particella")
    attendi(pg, "/centro del comune di Torino/.test(document.getElementById('messaggio-cerca').textContent)")
    assert not pg.errori, pg.errori
    ctx.close()


def test_clic_sulla_mappa_non_sposta_la_vista(browser, base):
    """Punto J: un clic sulla mappa (anche su un comune, allo zoom dei comuni) non cambia centro né zoom."""
    ctx, pg = pagina(browser)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded()", 30000)
    pg.evaluate(f"{M3D}.mappa.jumpTo({{center: [12.4964, 41.8945], zoom: 13}})")
    pg.wait_for_timeout(2500)                     # confini dei comuni del Lazio caricati
    prima = pg.evaluate(f"(() => {{ const c = {M3D}.mappa.getCenter(); return [c.lng, c.lat, {M3D}.mappa.getZoom()]; }})()")
    box = pg.locator("#mappa3d").bounding_box()
    for dx in (0, 80, -120):
        pg.mouse.click(box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + 30)
        pg.wait_for_timeout(900)
    dopo = pg.evaluate(f"(() => {{ const c = {M3D}.mappa.getCenter(); return [c.lng, c.lat, {M3D}.mappa.getZoom()]; }})()")
    assert all(abs(a - b) < 1e-6 for a, b in zip(prima, dopo)), (prima, dopo)
    assert not pg.errori, pg.errori
    ctx.close()


def test_colore_degli_edifici_e_alberi_ricordati(browser, base):
    """Punto E: menu del colore (come quello dell'asterisco) e casella «Alberi» (spenta in partenza), ricordati nel browser."""
    ctx, pg = pagina(browser)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, "!!document.querySelector('#colore-edifici .vestito-pulsante')", 30000)
    assert pg.is_checked("#strato-alberi") is False
    assert pg.get_attribute("#colore-edifici .vestito-pulsante", "title") == "Colore degli edifici: Grigio"
    pg.click("#colore-edifici .vestito-pulsante")
    assert pg.is_visible("#colore-edifici-elenco")
    assert pg.evaluate("[...document.querySelectorAll('#colore-edifici-elenco li')].map((x) => x.dataset.colore)") == ["grigio", "giallo", "rosso", "indaco", "violetto"]
    pg.click("#colore-edifici-rosso")
    assert pg.is_hidden("#colore-edifici-elenco")
    assert pg.evaluate("localStorage.getItem('eugenio-colore-edifici')") == "rosso"
    # tastiera: freccia giù dal pulsante apre, Fine va all'ultimo, Invio sceglie
    pg.focus("#colore-edifici .vestito-pulsante"); pg.keyboard.press("ArrowDown"); pg.keyboard.press("End"); pg.keyboard.press("Enter")
    assert pg.evaluate("localStorage.getItem('eugenio-colore-edifici')") == "violetto"
    pg.check("#strato-alberi")
    assert pg.evaluate("localStorage.getItem('eugenio-alberi-3d')") == "1"
    pg.reload()
    attendi(pg, "!!document.querySelector('#colore-edifici .vestito-pulsante')", 30000)
    assert pg.get_attribute("#colore-edifici .vestito-pulsante", "title") == "Colore degli edifici: Violetto"
    assert pg.is_checked("#strato-alberi") is True
    assert not pg.errori, pg.errori
    ctx.close()


@pytest.mark.parametrize("nome,larghezza", [("ortofoto.html", 360), ("modelli3d.html", 375), ("modelli3d.html", 1366)])
def test_frecce_dell_ortofoto_su_una_riga(browser, base, nome, larghezza):
    """Punto C: frecce, «Ortofoto spostata: …» e «Azzera» affiancati sulla stessa riga anche con la colonna stretta."""
    ctx, pg = pagina(browser, larghezza=larghezza)
    pg.goto(base + nome)
    webgl(pg)
    attendi(pg, "!!document.querySelector('#sposta-ortofoto .sposta-azzera')", 30000)
    righe = pg.evaluate("""(() => { const g = document.querySelector('#sposta-ortofoto .sposta-ortofoto');
      const el = [...g.querySelectorAll('.freccia'), g.querySelector('.sposta-stato'), g.querySelector('.sposta-azzera')];
      return el.map((x) => { const r = x.getBoundingClientRect(); return [Math.round(r.top + r.height / 2), Math.round(r.right)]; }); })()""")
    centri = [r[0] for r in righe]
    assert max(centri) - min(centri) <= 4, righe
    assert pg.evaluate("[...document.querySelectorAll('#sposta-ortofoto .freccia')].map((b) => b.textContent).join('')") == "←↑↓→"
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    ctx.close()
