"""Prove nel browser delle correzioni del 09/11/2026 e (prove di Paolo delle 21:05): l'indicatore di caricamento resta
piccolo (clessidra limitata, sotto 40 px di altezza, nell'angolo in basso a sinistra) a 375, 1366 e 1920 px, con lo zoom del
browser al 150 %, con la mappa allungata dalla maniglia, in 2D e in 3D; il gettone della verifica anti-robot è comune alle
schede (localStorage): con un gettone valido Turnstile non si carica. Rotte /api simulate; si salta senza Playwright o
Chromium."""
from __future__ import annotations

import json
import re

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import attendi, base, browser, pagina, webgl  # noqa: E402,F401

M3D = "window.EUGENIO_EDIFICIO3D.stato"


def _misura(pg, sel="#mappa3d"):
    return pg.evaluate(f"""(() => {{ const m = document.querySelector('{sel}').getBoundingClientRect(), e = document.querySelector('{sel} .carico-mappa'),
        r = e.getBoundingClientRect(), s = e.querySelector('svg').getBoundingClientRect();
        return {{ alto: r.height, largo: r.width, icona: [s.width, s.height], sx: r.left - m.left, giu: m.bottom - r.bottom, mw: m.width, mh: m.height,
                  font: parseFloat(getComputedStyle(e).fontSize) }}; }})()""")


@pytest.mark.parametrize("larghezza,altezza,scala", [(375, 800, 1), (1366, 900, 1), (1920, 1080, 1), (1280, 720, 1.5)])
def test_indicatore_piccolo_in_ogni_finestra(browser, base, larghezza, altezza, scala):
    """Punto 1 («impazzisce»: anello bianco di 600–700 px): la clessidra ha width e height espliciti e la regola generica
    «.mappa svg { width: 100% }» non la tocca più; riquadro sotto 40 px di altezza, icona al più 26 px, nell'angolo in basso a
    sinistra, anche con la mappa allungata dalla maniglia e nella vista inclinata. 1280 × 720 con scala 1,5 = 1920 px con lo
    zoom del browser al 150 %."""
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza}, device_scale_factor=scala)
    ctx.add_init_script("try { localStorage.setItem('altezza-mappa:modelli3d:mappa3d', '900'); } catch (e) {}")
    pg = ctx.new_page(); pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), lambda r: r.fulfill(status=404, body="{}"))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && !!document.querySelector('#mappa3d .carico-mappa')", 30000)
    pg.evaluate("window.__fine = window.EUGENIO_LIMITI.lavoro('Carico le tessere di prova con un testo abbastanza lungo da riempire la riga'); 1")
    attendi(pg, "!document.querySelector('#mappa3d .carico-mappa').hidden", 5000)
    for vista in ("2d", "3d"):
        if vista == "3d":
            pg.evaluate(f"{M3D}.mappa.jumpTo({{ pitch: 60, bearing: 30 }})")
            pg.wait_for_timeout(300)
        d = _misura(pg)
        assert d["alto"] < 40 and d["icona"][0] <= 26.5 and d["icona"][1] <= 26.5 and d["icona"][0] >= 15.5, (larghezza, scala, vista, d)
        assert 0 <= d["sx"] <= 20 and 0 <= d["giu"] <= 60 and d["largo"] <= d["mw"] - 60, (larghezza, scala, vista, d)
        assert 10.5 <= d["font"] <= 14.5, d
    assert pg.evaluate("document.getElementById('mappa3d').getBoundingClientRect().height") >= min(900, altezza * 0.92) - 2
    pg.evaluate("window.__fine(); 1")
    assert not pg.errori, pg.errori
    ctx.close()


def test_indicatore_in_ortofoto(browser, base):
    ctx, pg = pagina(browser, larghezza=1920, altezza=1080)
    pg.goto(base + "ortofoto.html?lat=44.1326&lon=12.2597&z=16")
    webgl(pg)
    attendi(pg, "window.EUGENIO_ORTOFOTO && window.EUGENIO_ORTOFOTO.stato.mappa && !!document.querySelector('#mappa-ortofoto .carico-mappa')", 30000)
    pg.evaluate("window.__fine = window.EUGENIO_LIMITI.lavoro('Prova'); 1")
    attendi(pg, "!document.querySelector('#mappa-ortofoto .carico-mappa').hidden", 5000)
    d = _misura(pg, "#mappa-ortofoto")
    assert d["alto"] < 40 and d["icona"][0] <= 26.5, d
    assert not pg.errori, pg.errori
    ctx.close()


def test_gettone_comune_alle_schede_senza_turnstile(browser, base):
    """Punto 2: con un gettone di sessione valido in localStorage (scritto da un'altra scheda o da una visita di prima) la
    richiesta protetta lo manda e Turnstile non si carica (nessuna riga di challenges.cloudflare.com); senza gettone la pagina
    carica Turnstile una volta sola anche con più richieste protette insieme."""
    ctx, pg = pagina(browser)
    script, mandati = [], []
    pg.route("**/api/protezione", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"turnstile": "0xPROVA"})))
    pg.route("https://challenges.cloudflare.com/**", lambda r: (script.append(r.request.url), r.fulfill(status=200, content_type="text/javascript", body="")))
    pg.route("**/api/edifici/osm?*", lambda r: (mandati.append(r.request.headers.get("x-eugenio-sessione")),
             r.fulfill(status=200, content_type="application/json", body=json.dumps({"type": "FeatureCollection", "features": []}))))
    ctx.add_init_script("try { localStorage.setItem('eugenio_sessione', JSON.stringify({ g: 'GETTONE-DI-PROVA', scade: Math.floor(Date.now() / 1000) + 3000, base: '' })); } catch (e) {}")
    pg.goto(base + "index.html")
    for _ in range(3):
        pg.evaluate("fetch('/api/edifici/osm?lon=12.9&lat=43.9').then((r) => r.status)")
    pg.wait_for_timeout(500)
    assert mandati == ["GETTONE-DI-PROVA"] * 3 and script == [], (mandati, script)
    # un'altra scheda dello stesso browser usa lo stesso gettone
    pg2 = ctx.new_page()
    pg2.route("**/api/edifici/osm?*", lambda r: (mandati.append(r.request.headers.get("x-eugenio-sessione")),
              r.fulfill(status=200, content_type="application/json", body="{}")))
    pg2.goto(base + "modelli3d.html")
    pg2.evaluate("fetch('/api/edifici/osm?lon=12.9&lat=43.9').then((r) => r.status)")
    pg2.wait_for_timeout(500)
    assert mandati[-1] == "GETTONE-DI-PROVA" and script == []
    ctx.close()
