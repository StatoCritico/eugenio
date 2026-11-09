"""Prove nel browser (Chromium headless, Playwright) di Ortofoto e Modelli 3D dopo le prove di Paolo del 05/11/2026.

Ortofoto: confini ISTAT sempre presenti, piccola mappa d'Italia, avviso quando la fonte non ha tessere a quello zoom,
immagine della vista in JPG e PDF con le attribuzioni, nessun download per le fonti «solo dal vivo».
Modelli 3D: si apre in 2D; senza archivio c'è il pulsante della demo; con la demo niente ortofoto sotto, scelta
dell'edificio, «Genera il 3D», fonte per corpo, «Torna alla mappa 2D»; le altre pagine 3D restano in un tempo solo.
Le rotte /api/ sono simulate (nessuna rete). Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import functools
import json
import math
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

SITO = Path(__file__).resolve().parents[1] / "sito"
FONTI = {"fonti": [
    {"id": "rer2023", "nome": "Ortofoto RER 2023-24 (20 cm)", "licenza": "CC BY 4.0", "citazione": "Regione Emilia-Romagna – Ortofoto RER 2023-24 (CC BY 4.0)",
     "scheda": "https://geoportale.regione.emilia-romagna.it/", "stato": "da confermare", "copia": True, "nei_report": True, "zoom": [12, 20],
     "riquadro": [9.19, 43.73, 12.84, 45.16], "tessere": "/api/ortofoto/rer2023/{z}/{x}/{y}.jpg?t=1", "spostabile": True, "spostamento_max": 20},
    {"id": "s2cloudless2016", "nome": "Sentinel-2 cloudless 2016 (10 m)", "licenza": "CC BY 4.0", "citazione": "Sentinel-2 cloudless – EOX (2016)",
     "scheda": "https://cloudless.eox.at/", "stato": "confermata", "copia": True, "nei_report": True, "zoom": [5, 15],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/s2cloudless2016/{z}/{x}/{y}.jpg", "spostabile": False, "spostamento_max": 0},
    {"id": "pcn2012", "nome": "Geoportale Nazionale (solo consultazione)", "licenza": "da verificare", "citazione": "Geoportale Nazionale – AGEA 2012",
     "scheda": "https://gn.mase.gov.it/", "stato": "da confermare", "copia": False, "nei_report": False, "zoom": [12, 19],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/pcn2012/{z}/{x}/{y}.jpg", "spostabile": True, "spostamento_max": 20}]}


class ConRange(SimpleHTTPRequestHandler):
    """File statici con le richieste Range (servono ai PMTiles della demo), come Caddy."""
    def log_message(self, *a):
        pass

    def send_head(self):
        rng = self.headers.get("Range")
        p = Path(self.translate_path(self.path))
        if not rng or not p.is_file():
            return super().send_head()
        dati = p.read_bytes()
        a, b = rng.replace("bytes=", "").split("-")
        a = int(a); b = int(b) if b else len(dati) - 1
        pezzo = dati[a:b + 1]
        self.send_response(206)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {a}-{a + len(pezzo) - 1}/{len(dati)}")
        self.send_header("Content-Length", str(len(pezzo)))
        self.end_headers()
        import io
        return io.BytesIO(pezzo)


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(ConRange, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def pagina(browser, larghezza=1366, altezza=900, finestra=False):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza}, accept_downloads=True)
    # senza la finestra «Salva con nome» (Firefox, Safari): download con il collegamento; la finestra si prova a parte
    if not finestra:
        ctx.add_init_script("try { delete window.showSaveFilePicker; window.showSaveFilePicker = undefined; } catch (e) {}")
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    # niente rete: fonti simulate, tessere assenti (la mappa deve restare utilizzabile lo stesso), archivi assenti
    pg.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI)))
    pg.route("**/api/**", lambda r: r.fallback() if r.request.url.endswith("/api/ortofoto/fonti") else r.fulfill(status=404, body="{}"))
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), lambda r: r.fulfill(status=404, body="{}"))   # non dati/edifici3d/ (demo)
    return ctx, pg


def webgl(pg):
    if not pg.evaluate("!!document.createElement('canvas').getContext('webgl2') || !!document.createElement('canvas').getContext('webgl')"):
        pytest.skip("WebGL non disponibile in questo Chromium")


def attendi(pg, js, ms=15000):
    pg.wait_for_function(js, timeout=ms)


def test_ortofoto_confini_minimappa_avviso_e_immagine(browser, base, tmp_path):
    ctx, pg = pagina(browser)
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=16")
    webgl(pg)
    attendi(pg, "window.EUGENIO_ORTOFOTO && window.EUGENIO_ORTOFOTO.stato.scelta && window.EUGENIO_ORTOFOTO.stato.mappa.getLayer('confini-regioni')")
    assert pg.locator(".minimappa svg path").count() >= 20
    st = "window.EUGENIO_ORTOFOTO.stato"
    assert pg.evaluate(f"{st}.scelta.id") == "rer2023"
    assert pg.evaluate(f"!!{st}.mappa.getLayer('contesto')")
    # sotto lo zoom minimo della fonte: avviso e contesto, nessun vuoto
    pg.evaluate(f"{st}.mappa.jumpTo({{zoom: 8}})")
    attendi(pg, "!document.querySelector('.avviso-mappa').hidden && /zoom 12/.test(document.querySelector('.avviso-mappa').textContent)")
    assert "contesto" in pg.locator(".avviso-mappa").text_content()
    # immagine della vista: JPG e PDF con le attribuzioni
    pg.evaluate(f"{st}.mappa.jumpTo({{zoom: 16}})")
    pg.wait_for_timeout(500)
    for f, testa in (("jpg", b"\xff\xd8"), ("pdf", b"%PDF")):
        with pg.expect_download() as d:
            pg.evaluate(f"document.querySelector('#scarica-ortofoto button[data-formato=\"{f}\"]').click()")
        dest = tmp_path / f"vista.{f}"
        d.value.save_as(dest)
        assert dest.read_bytes()[:4].startswith(testa)
    pdf = (tmp_path / "vista.pdf").read_bytes()
    assert b"Regione Emilia-Romagna" in pdf and b"EuGEnio" in pdf and b"ISTAT" in pdf
    # fonte solo dal vivo: nessun download
    pg.evaluate(f"{st}.manuale = true; document.querySelector('#fonti input[value=\"pcn2012\"]').click()")
    pg.evaluate("document.querySelector('#scarica-ortofoto button[data-formato=\"jpg\"]').click()")
    attendi(pg, "/solo in consultazione dal vivo/.test(document.getElementById('messaggio-immagine').textContent)")
    # piccola mappa: clic sulla Toscana, poi di nuovo = torna all'Italia
    pg.evaluate("document.querySelector('.minimappa path[data-cod=\"09\"]').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    attendi(pg, f"{st}.regione === '09'")
    pg.evaluate("document.querySelector('.minimappa path[data-cod=\"09\"]').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    attendi(pg, f"{st}.regione === null")
    assert not pg.errori, pg.errori
    ctx.close()


def test_modelli3d_senza_archivio_si_apre_in_2d(browser, base):
    ctx, pg = pagina(browser)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, "window.EUGENIO_EDIFICIO3D && window.EUGENIO_EDIFICIO3D.stato.mappa && !document.getElementById('apri-demo').hidden")
    s = "window.EUGENIO_EDIFICIO3D.stato"
    assert pg.evaluate(f"{s}.in3d") is False and pg.evaluate(f"{s}.mappa.getPitch()") == 0
    assert pg.evaluate(f"!!{s}.mappa.getLayer('confini-regioni')")
    assert pg.locator(".minimappa svg").count() == 1
    assert pg.locator("#genera-3d").is_disabled()
    assert not pg.errori, pg.errori
    ctx.close()


def test_modelli3d_demo_in_due_tempi(browser, base, tmp_path):
    ctx, pg = pagina(browser)
    pg.goto(base + "modelli3d.html?archivio=demo")
    webgl(pg)
    s = "window.EUGENIO_EDIFICIO3D.stato"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.indice && document.getElementById('sfondo-ortofoto').disabled")
    assert pg.evaluate(f"{s}.in3d") is False
    assert pg.evaluate(f"{s}.ortofoto") is None                         # la demo non va mai sopra una foto vera
    pg.evaluate(f"(() => {{ const c = {s}.indice.centro; window.EUGENIO_EDIFICIO3D.scegli2d('E-DEMO', c[0], c[1]); }})()")
    assert not pg.locator("#genera-3d").is_disabled()
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 3")
    assert "dati sintetici" in pg.locator("#fonti-corpi").text_content()
    assert pg.locator(".mappa3d-comandi").is_visible()
    note = pg.evaluate("window.EUGENIO_EDIFICIO3D.corpoReport().note.join(' ')")
    assert "Fonte del 3D per corpo" in note
    with pg.expect_download() as d:
        pg.evaluate("document.querySelector('#scarica-3d button[data-formato=\"pdf\"]').click()")
    dest = tmp_path / "m.pdf"
    d.value.save_as(dest)
    assert dest.read_bytes().startswith(b"%PDF") and b"sintetici" in dest.read_bytes()
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{s}.in3d && document.getElementById('torna-2d').hidden")
    assert not pg.errori, pg.errori
    ctx.close()


def test_altre_pagine_3d_come_modelli3d(browser, base):
    """07/11/2026 sera: le pagine Edificio e Fotovoltaico non aprono più un solo archivio (finivano sulla demo): si aprono
    in 2D come Modelli 3D, con ricerca e «Genera il 3D»; senza archivi niente demo automatica (pulsante «Prova la demo»)."""
    ctx, pg = pagina(browser)
    pg.goto(base + "fv-producibilita.html")
    webgl(pg)
    s = "window.EUGENIO_EDIFICIO3D.stato"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && !document.getElementById('apri-demo').hidden", 25000)
    assert pg.evaluate(f"{s}.in3d") is False and pg.evaluate(f"{s}.edificio") is None and pg.evaluate(f"{s}.osmAttivo") is True
    assert pg.get_attribute("#apri-demo", "href") == "fv-producibilita.html?archivio=demo"
    assert pg.locator("#cerca-edificio input").count() >= 1
    assert not pg.errori, pg.errori
    ctx.close()


# ---------------------------------------------------------------- seconda pubblicazione del 05/11/2026
STRATI = {"strati": [
    {"id": "catasto", "tema": "particelle", "nome": "Confini delle particelle catastali", "licenza": "CC BY 4.0",
     "citazione": "Agenzia delle Entrate – Cartografia catastale, CC BY 4.0", "scheda": "https://www.agenziaentrate.gov.it/",
     "stato": "confermata", "regioni": [], "zoom": [16, 20], "riquadro": [6.6, 35.4, 18.6, 47.1], "colore": "#ffd400",
     "legenda": "linee e numeri gialli: confini e numeri delle particelle catastali", "tipo": "immagine", "nota": "",
     "tessere": "/api/ortofoto/strati/catasto/{z}/{x}/{y}.png"},
    {"id": "dbtr_edifici", "tema": "edifici", "nome": "Contorni DBTR", "licenza": "CC BY 4.0",
     "citazione": "Regione Emilia-Romagna – DBTR, edifici, CC BY 4.0", "scheda": "https://geoportale.regione.emilia-romagna.it/",
     "stato": "confermata", "regioni": ["08"], "zoom": [16, 20], "riquadro": [9.19, 43.71, 12.84, 45.15], "colore": "#00e5ff",
     "legenda": "linee azzurre: contorni degli edifici del DBTR", "tipo": "immagine", "nota": "",
     "tessere": "/api/ortofoto/strati/dbtr_edifici/{z}/{x}/{y}.png"},
    {"id": "osm_edifici", "tema": "edifici", "nome": "Contorni OSM", "licenza": "ODbL 1.0",
     "citazione": "© contributori OpenStreetMap (ODbL 1.0)", "scheda": "https://www.openstreetmap.org/copyright",
     "stato": "confermata", "regioni": [], "zoom": [16, 16], "riquadro": [6.6, 35.4, 18.6, 47.1], "colore": "#00e5ff",
     "legenda": "linee azzurre: contorni degli edifici di OpenStreetMap", "tipo": "vettori", "nota": "",
     "tessere": "/api/ortofoto/strati/osm_edifici/{z}/{x}/{y}.json"}]}
RIGA = {"righe": [{"lat": 44.0601, "lon": 12.5672, "esito": "ok", "indirizzo_trovato": "VIA GAMBALUNGA 27", "comune_catasto": "RIMINI",
                   "fonte_punto": "ANNCSU", "mappale": "", "foglio_catasto": ""}]}


def _png_linea():
    import io
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    ImageDraw.Draw(im).line([(0, 128), (255, 128)], fill=(255, 212, 0, 255), width=3)
    b = io.BytesIO(); im.save(b, "PNG")
    return b.getvalue()


def _con_strati(pg):
    png = _png_linea()
    pg.route("**/api/ortofoto/strati", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(STRATI)))
    pg.route("**/api/ortofoto/strati/*/*/*/*.png", lambda r: r.fulfill(status=200, content_type="image/png", body=png))
    pg.route("**/api/patrimonio", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(RIGA)))


def test_immagine_con_la_finestra_salva_con_nome(browser, base):
    """Chrome/Edge: la finestra del sistema si apre solo con «chiedi dove salvarlo» spuntato (07/11/2026 sera), nel clic;
    «salvata» solo dopo la scrittura; «Annulla» = annullato. Senza la spunta: download diretto, nessuna finestra."""
    ctx, pg = pagina(browser, finestra=True)
    ctx.add_init_script("""window.__scritti = []; window.__annulla = false;
      window.showSaveFilePicker = async (o) => { if (window.__annulla) { const e = new Error('annullato'); e.name = 'AbortError'; throw e; }
        return { name: o.suggestedName, createWritable: async () => { const parti = [];
          return { write: async (b) => parti.push(new Uint8Array(await b.arrayBuffer())), close: async () => window.__scritti.push({ nome: o.suggestedName, byte: parti.reduce((s, p) => s + p.length, 0), testa: Array.from(parti[0].slice(0, 4)) }) }; } }; };""")
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=16")
    webgl(pg)
    attendi(pg, "window.EUGENIO_ORTOFOTO && window.EUGENIO_ORTOFOTO.stato.scelta && document.querySelector('#scarica-ortofoto button')")
    # 07/11/2026 sera: senza la spunta nessuna finestra del sistema, download diretto
    pg.evaluate("document.querySelector('#scarica-ortofoto button[data-formato=\"png\"]').click()")
    attendi(pg, "/Download avviato/.test(document.getElementById('messaggio-immagine').textContent)")
    assert pg.evaluate("window.__scritti.length") == 0
    pg.check("#scarica-ortofoto input[data-salva-con-nome]")
    pg.evaluate("document.querySelector('#scarica-ortofoto button[data-formato=\"png\"]').click()")
    attendi(pg, "/Immagine salvata/.test(document.getElementById('messaggio-immagine').textContent)")
    s = pg.evaluate("window.__scritti")
    assert len(s) == 1 and s[0]["nome"].endswith(".png") and s[0]["byte"] > 5000 and s[0]["testa"] == [137, 80, 78, 71]
    pg.evaluate("window.__annulla = true; document.querySelector('#scarica-ortofoto button[data-formato=\"pdf\"]').click()")
    attendi(pg, "/annullato/.test(document.getElementById('messaggio-immagine').textContent)")
    assert len(pg.evaluate("window.__scritti")) == 1
    assert not pg.errori, pg.errori
    ctx.close()


def test_ortofoto_ricerca_strati_e_immagine(browser, base, tmp_path):
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=15")
    webgl(pg)
    st = "window.EUGENIO_ORTOFOTO.stato"
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {st}.strati && document.getElementById('strato-particelle')")
    # ricerca per indirizzo: la mappa va sul punto con il segnaposto
    pg.fill("#cerca-via", "via Gambalunga 27"); pg.fill("#cerca-comune", "Rimini")
    pg.click("#cerca-indirizzo")
    attendi(pg, f"/ANNCSU/.test(document.getElementById('messaggio-cerca').textContent) && Math.abs({st}.mappa.getCenter().lat - 44.0601) < 1e-4 && !{st}.mappa.isMoving()")
    assert abs(pg.evaluate(f"{st}.mappa.getZoom()") - 17) < 0.05              # zoom comune di cerca_luogo.js (07/11/2026)
    assert pg.evaluate("window.EUGENIO_CERCA.ZOOM") == 17
    # strati: particelle e contorni degli edifici (in ER il DBTR), legenda e attribuzioni sotto la mappa
    pg.check("#strato-particelle"); pg.check("#strato-edifici")
    attendi(pg, "/Agenzia delle Entrate/.test(document.getElementById('legenda-strati').textContent) && /DBTR/.test(document.getElementById('legenda-strati').textContent)")
    assert pg.evaluate(f"{st}.mappa.getLayoutProperty('strato-particelle', 'visibility')") == "visible"
    assert pg.evaluate(f"{st}.mappa.getLayoutProperty('strato-dbtr_edifici', 'visibility')") == "visible"
    assert pg.evaluate(f"{st}.mappa.getLayoutProperty('strato-osm', 'visibility')") == "none"
    with pg.expect_download() as d:
        pg.evaluate("document.querySelector('#scarica-ortofoto button[data-formato=\"pdf\"]').click()")
    dest = tmp_path / "o.pdf"; d.value.save_as(dest)
    pdf = dest.read_bytes()
    assert pdf.startswith(b"%PDF") and b"Agenzia delle Entrate" in pdf and b"DBTR" in pdf and b"ANNCSU" in pdf
    attendi(pg, "/Download avviato/.test(document.getElementById('messaggio-immagine').textContent) && !!document.querySelector('#messaggio-immagine a.salva-a-mano')")
    # spento: la legenda sparisce
    pg.uncheck("#strato-particelle"); pg.uncheck("#strato-edifici")
    attendi(pg, "document.getElementById('legenda-strati').hidden")
    assert not pg.errori, pg.errori
    ctx.close()


def test_modelli3d_punto_trascinabile_strati_ed_esci_dalla_demo(browser, base):
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.goto(base + "modelli3d.html?archivio=demo")
    webgl(pg)
    s = "window.EUGENIO_EDIFICIO3D.stato"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.indice && !document.getElementById('esci-demo').hidden")
    assert pg.locator("#apri-demo").is_hidden() and pg.get_attribute("#esci-demo", "href") == "modelli3d.html"
    assert pg.locator("#strato-ortofoto").is_disabled()                     # demo: niente foto né strati veri
    assert pg.locator("#strato-particelle").count() == 0
    # punto messo vicino all'isolato, poi trascinato col mouse dentro E-DEMO: l'edificio si sceglie dal punto corretto
    pg.evaluate(f"(() => {{ const c = {s}.indice.centro; {s}.mappa.jumpTo({{ center: c, zoom: 18 }}); window.EUGENIO_EDIFICIO3D.impostaPunto(c[0] + 0.004, c[1] + 0.003, 'ricerca'); }})()")
    pg.wait_for_timeout(300)
    destinazione = pg.evaluate("""(async () => { const E = window.EUGENIO_EDIFICIO3D, st = E.stato;
      const fs = await (await fetch('dati/edifici3d/contesto/' + (() => { const c = st.indice.cella || 0.01; return Math.floor(st.indice.centro[0] / c) + '_' + Math.floor(st.indice.centro[1] / c); })() + '.json')).json();
      const f = fs.features.find((x) => x.properties.edificio === 'E-DEMO'); const r = f.geometry.coordinates[0];
      const lon = r.slice(0, -1).reduce((a, q) => a + q[0], 0) / (r.length - 1), lat = r.slice(0, -1).reduce((a, q) => a + q[1], 0) / (r.length - 1);
      st.mappa.jumpTo({ center: [lon, lat] }); E.impostaPunto(lon + 0.0004, lat + 0.0003, 'ricerca'); return [lon, lat]; })()""")
    pg.wait_for_timeout(500)
    box = pg.locator("#mappa3d").bounding_box()
    da = pg.evaluate(f"(() => {{ const p = {s}.mappa.project([{s}.punto.lon, {s}.punto.lat]); return [p.x, p.y]; }})()")
    a = pg.evaluate(f"(() => {{ const p = {s}.mappa.project({json.dumps(destinazione)}); return [p.x, p.y]; }})()")
    centro0 = pg.evaluate(f"{s}.mappa.getCenter().toArray()")
    pg.mouse.move(box["x"] + da[0], box["y"] + da[1]); pg.mouse.down()
    for k in range(1, 11):
        pg.mouse.move(box["x"] + da[0] + (a[0] - da[0]) * k / 10, box["y"] + da[1] + (a[1] - da[1]) * k / 10)
    pg.mouse.up()
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-DEMO'")
    assert pg.evaluate(f"{s}.punto.origine") == "spostato"
    assert pg.evaluate(f"{s}.mappa.getCenter().toArray()") == pytest.approx(centro0, abs=1e-7)     # la mappa non si è mossa
    assert pg.evaluate(f"Math.abs({s}.daGenerare.lon - {destinazione[0]}) < 2e-5")
    # 3D e ritorno al 2D della demo; poi «Esci dalla demo» riapre la pagina normale
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && !document.getElementById('esci-demo').hidden")
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{s}.in3d && {s}.indice.sintetico")
    pg.click("#esci-demo")
    pg.wait_for_url(re.compile(r"/modelli3d\.html$"))
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && !document.getElementById('apri-demo').hidden")
    assert pg.locator("#esci-demo").is_hidden() and not pg.locator("#strato-ortofoto").is_disabled()
    attendi(pg, "!!document.getElementById('strato-particelle') && !document.getElementById('strato-particelle').disabled")
    assert not pg.errori, pg.errori
    ctx.close()


# ----------------------------------------------------------------------------------- 07/11/2026: Livelli, fori, fuori zona
def test_livelli_della_mappa_nella_colonna_destra():
    h = (SITO / "modelli3d.html").read_text(encoding="utf-8")
    mappa = h[h.index('<section class="mappa-area"'):h.index('<section class="pannello"')]
    pannello = h[h.index('<section class="pannello"'):]
    assert 'id="livelli-mappa"' not in mappa and 'id="caselle-strati"' not in mappa and 'id="strato-ortofoto"' not in mappa
    assert 'id="legenda-strati"' in mappa and 'id="attribuzione-ortofoto"' in mappa          # legenda e fonti sotto la mappa
    i = pannello.index('<div class="passo" id="livelli-mappa">')
    assert i < pannello.index('id="passo-edificio"') and "Livelli della mappa</h2>" in pannello[i:i + 200]
    assert re.search(r'<h2><span class="n">\d+</span>Strati sopra la foto</h2>', (SITO / "ortofoto.html").read_text(encoding="utf-8"))
    # 07/11/2026 sera (prove di Paolo): la ricerca è il passo 1 della colonna destra, prima dei livelli, in tutte le pagine
    # 3D e in Ortofoto (la pagina non «salta» più tra la mappa e i campi)
    for nome in PAGINE_3D_TUTTE + ["ortofoto.html"]:
        h = (SITO / nome).read_text(encoding="utf-8")
        mappa = h[h.index('<section class="mappa-area"'):h.index('<section class="pannello"')]
        pannello = h[h.index('<section class="pannello"'):]
        cont = "cerca-luogo" if nome == "ortofoto.html" else "cerca-edificio"
        assert f'id="{cont}"' not in mappa and f'id="{cont}"' in pannello, nome
        primo = re.search(r'<div class="passo"[^>]*>\s*<h2><span class="n">(\d+)</span>([^<]+)</h2>', pannello)
        assert primo.group(1) == "1" and primo.group(2).startswith("Cerca"), (nome, primo.groups())
        assert pannello.index(f'id="{cont}"') < pannello.index('id="livelli-mappa"' if nome != "ortofoto.html" else "Fonte</h2>"), nome


def _archivio_con_cortile(cartella):
    """Archivio CC BY sintetico a Rimini: un edificio a corte (due corpi, uno con il cortile) e un vicino; indice con il
    riquadro della zona. Fatto con il codice della fase 10 (stessi file del server)."""
    import sys
    f10 = SITO.parents[1] / "fase10-edifici3d"
    sys.path.insert(0, str(f10))
    from shapely.geometry import Polygon, box
    from edifici3d import modello as M
    from edifici3d.__main__ import prepara_corpi
    x0, y0 = 785540.0, 4884790.0
    corte = Polygon([(x0, y0), (x0 + 40, y0), (x0 + 40, y0 + 40), (x0, y0 + 40)],
                    [[(x0 + 12, y0 + 12), (x0 + 28, y0 + 12), (x0 + 28, y0 + 28), (x0 + 12, y0 + 28)]])
    corpi = [M.Corpo(id="C1", edificio="E-CORTE", sagoma=corte, quota_terreno=6, gronda=15, fonte_sagoma="DBTR Emilia-Romagna – UVL",
                     licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)", extra={"foglio": "74", "numero": "1100"}),
             M.Corpo(id="C2", edificio="E-CORTE", sagoma=box(x0 + 40, y0, x0 + 55, y0 + 40), quota_terreno=6, gronda=9,
                     fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)"),
             M.Corpo(id="V1", edificio="E-VIC", sagoma=box(x0 - 30, y0, x0 - 10, y0 + 20), quota_terreno=6, gronda=12,
                     fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)")]
    out = cartella / "cc-by" / "er" / "prodotti"
    ind = prepara_corpi(corpi, None, out, "CC BY 4.0", "Regione Emilia-Romagna – DBTR, CC BY 4.0", extra={"nome": "DBTR Emilia-Romagna"})
    (cartella / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}]}),
                                           encoding="utf-8")
    return ind


def test_modelli3d_archivio_con_cortile_e_fuori_zona(browser, base, tmp_path):
    ind = _archivio_con_cortile(tmp_path)
    radice = tmp_path

    def edifici3d(r):
        rel = re.sub(r"^.*?/edifici3d/", "", r.request.url.split("?")[0])
        p = radice / rel
        if not p.is_file():
            return r.fulfill(status=404, body="{}")
        dati = p.read_bytes()
        rng = r.request.headers.get("range")
        tipo = "application/json" if p.suffix == ".json" else "application/octet-stream"
        if rng:
            a, b = rng.replace("bytes=", "").split("-")
            a = int(a); b = int(b) if b else len(dati) - 1
            return r.fulfill(status=206, body=dati[a:b + 1], headers={"Content-Type": tipo, "Content-Range": f"bytes {a}-{min(b, len(dati) - 1)}/{len(dati)}"})
        return r.fulfill(status=200, body=dati, headers={"Content-Type": tipo})
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), edifici3d)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s = "window.EUGENIO_EDIFICIO3D.stato"
    # 07/11/2026: dopo l'archivio c'è il ripiego OSM «virtuale» (qui la rotta risponde 404: non disponibile)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length === 2 && {s}.archivi[1].osm && !!{s}.mappa.getLayer('zone-coperte')")
    E = "window.EUGENIO_EDIFICIO3D"
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True)
    foro = t.transform(785560.0, 4884810.0)            # centro del cortile
    muro = t.transform(785545.0, 4884810.0)            # dentro il corpo C1
    # punto nel cortile: non è «dentro», ma è entro 30 m dai lati del cortile → sceglie l'edificio a corte
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{foro[0]}, {foro[1]}], zoom: 18 }}); {E}.impostaPunto({foro[0]}, {foro[1]}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-CORTE'")
    fs = pg.evaluate(f"(async () => {{ const st = {s}; const nomi = st.indice.nomi_celle; const r = await (await fetch('/edifici3d/cc-by/er/prodotti/contesto/' + nomi[0] + '.json')).json(); return r.features; }})()")
    c1 = next(f for f in fs if f["properties"]["id"] == "C1")
    assert len(c1["geometry"]["coordinates"]) == 2                                   # il cortile è nell'archivio
    assert pg.evaluate(f"{E}.edificioNelPunto([{json.dumps(c1)}], {foro[0]}, {foro[1]}) !== null")          # entro 30 m dal lato
    assert pg.evaluate(f"(() => {{ const E = window.EUGENIO_EDIFICI, pr = E.proiezione({foro[0]}, {foro[1]}); const g = {json.dumps(c1['geometry'])};"
                       f" return E.dentroCorpo([0, 0], {{ ring: g.coordinates[0].map(pr.avanti), buchi: g.coordinates.slice(1).map((r) => r.map(pr.avanti)) }}); }})()") is False
    # Genera il 3D: il corpo scelto porta il cortile nel GeoJSON della sorgente «scelto» e nell'area netta
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 2")
    d = pg.evaluate(f"(() => {{ const c = {s}.corpi.find((x) => x.id === 'C1'); return {{ buchi: c.buchi.length, area: window.EUGENIO_EDIFICI.areaCorpo(c),"
                    f" anelli: {E}.geojson([c]).features[0].geometry.coordinates.length, tabella: document.getElementById('tabella-corpi').textContent }}; }})()")
    assert d["buchi"] == 1 and d["anelli"] == 2 and abs(d["area"] - (1600 - 256)) < 15
    assert re.search(r"C11\.?3[34]\d", d["tabella"])                                 # area netta ~1.340 m² nella tabella
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{s}.in3d")
    # fuori dalla zona coperta (Bologna): messaggio chiaro con il nome dell'archivio
    pg.evaluate(f"(() => {{ {E}.impostaPunto(11.3426, 44.4949, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, "/fuori dalla zona coperta/.test(document.getElementById('messaggio').textContent)")
    assert "DBTR Emilia-Romagna" in pg.text_content("#messaggio") and pg.evaluate(f"{E}.coperto(11.3426, 44.4949)") is False
    assert "OpenStreetMap" in pg.text_content("#messaggio") and "non disponibile" in pg.text_content("#messaggio")
    assert pg.evaluate(f"{E}.coperto({muro[0]}, {muro[1]})") is True
    # ricerca: zoom 17
    pg.fill("#cerca-via", "via Gambalunga 27"); pg.fill("#cerca-comune", "Rimini")
    pg.click("#cerca-indirizzo")
    attendi(pg, f"/ANNCSU/.test(document.getElementById('messaggio-cerca').textContent) && !{s}.mappa.isMoving() && Math.abs({s}.mappa.getZoom() - 17) < 0.05")
    assert not pg.errori, pg.errori
    ctx.close()


# ----------------------------------------------------------------------------------- 07/11/2026: ripiego OpenStreetMap
XML_PESARO = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Overpass API">
 <node id="1" lat="43.9040" lon="12.9060"/><node id="2" lat="43.9040" lon="12.9066"/>
 <node id="3" lat="43.9045" lon="12.9066"/><node id="4" lat="43.9045" lon="12.9060"/>
 <node id="5" lat="43.9041" lon="12.9062"/><node id="6" lat="43.9041" lon="12.9064"/>
 <node id="7" lat="43.9043" lon="12.9064"/><node id="8" lat="43.9043" lon="12.9062"/>
 <node id="11" lat="43.9047" lon="12.9060"/><node id="12" lat="43.9047" lon="12.9063"/>
 <node id="13" lat="43.9049" lon="12.9063"/><node id="14" lat="43.9049" lon="12.9060"/>
 <node id="21" lat="43.9035" lon="12.9070"/><node id="22" lat="43.9035" lon="12.9073"/>
 <node id="23" lat="43.9037" lon="12.9073"/><node id="24" lat="43.9037" lon="12.9070"/>
 <way id="300"><nd ref="1"/><nd ref="2"/><nd ref="3"/></way>
 <way id="301"><nd ref="3"/><nd ref="4"/><nd ref="1"/></way>
 <way id="302"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/></way>
 <way id="303"><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="14"/><nd ref="11"/></way>
 <way id="304"><nd ref="21"/><nd ref="22"/><nd ref="23"/><nd ref="24"/><nd ref="21"/><tag k="building" v="house"/></way>
 <relation id="400"><member type="way" ref="300" role="outer"/><member type="way" ref="301" role="outer"/>
  <member type="way" ref="302" role="inner"/><member type="way" ref="303" role="outer"/>
  <tag k="type" v="multipolygon"/><tag k="building" v="hospital"/><tag k="building:levels" v="5"/></relation>
</osm>"""


def _osm_al_volo(xml, lon, lat):
    import sys
    sys.path.insert(0, str(SITO.parents[1] / "fase10-edifici3d"))
    from edifici3d import osm_campione as OC
    d = OC.corpi_al_volo(xml, lon, lat)
    d.update({"centro": [round(lon, 3), round(lat, 3)], "raggio": 400, "nota": "Ripiego", "scheda": "https://www.openstreetmap.org/copyright"})
    return d


def _quadrato(id_, lon, lat, lato=0.0001):
    return {"type": "Feature", "id": id_, "geometry": {"type": "Polygon", "coordinates": [[[lon, lat], [lon + lato, lat], [lon + lato, lat + lato],
            [lon, lat + lato], [lon, lat]]]}, "properties": {"id": id_, "edificio": id_, "gronda": 9.0, "altezza": 9.0, "fonte_sagoma": "OpenStreetMap",
            "licenza": "ODbL 1.0", "fonte_altezza": "stima: altezza non presente in OSM (9 m)", "qualita": "stima", "tetto": "piano"}}


def test_modelli3d_ripiego_osm_fuori_dal_dbtr(browser, base, tmp_path):
    """Punto fuori dal DBTR (Pesaro) → corpi OSM dal server, scelta, Genera il 3D, licenza ODbL in pagina, immagine e report;
    zona coperta = confine ISTAT del comune dell'archivio (il riquadro sborda su Riccione); corpi OSM in un comune coperto
    scartati; Overpass giù → messaggio chiaro e niente 3D."""
    _archivio_con_cortile(tmp_path)
    ind_p = tmp_path / "cc-by" / "er" / "prodotti" / "indice.json"
    ind = json.loads(ind_p.read_text(encoding="utf-8"))
    ind["riquadro"] = [ind["riquadro"][0], 43.995, 12.70, ind["riquadro"][3]]          # sborda su Riccione, come il DBTR vero
    ind_p.write_text(json.dumps(ind), encoding="utf-8")
    (tmp_path / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna – Rimini",
                                                                    "istat": "099014"}]}), encoding="utf-8")
    radice = tmp_path
    pesaro = _osm_al_volo(XML_PESARO, 12.906, 43.904)
    confine = {"features": []}
    chiamate = []

    def edifici3d(r):
        p = radice / re.sub(r"^.*?/edifici3d/", "", r.request.url.split("?")[0])
        if not p.is_file():
            return r.fulfill(status=404, body="{}")
        dati = p.read_bytes()
        rng = r.request.headers.get("range")
        tipo = "application/json" if p.suffix == ".json" else "application/octet-stream"
        if rng:
            a, b = rng.replace("bytes=", "").split("-")
            a = int(a); b = int(b) if b else len(dati) - 1
            return r.fulfill(status=206, body=dati[a:b + 1], headers={"Content-Type": tipo, "Content-Range": f"bytes {a}-{min(b, len(dati) - 1)}/{len(dati)}"})
        return r.fulfill(status=200, body=dati, headers={"Content-Type": tipo})

    def osm(r):
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(r.request.url).query)
        lon, lat = float(q["lon"][0]), float(q["lat"][0])
        chiamate.append((lon, lat))
        if abs(lon - 12.906) < 0.01 and abs(lat - 43.904) < 0.01:
            return r.fulfill(status=200, content_type="application/json", body=json.dumps(pesaro))
        if abs(lon - 12.24) < 0.02:                                                 # Cesena: Overpass giù
            return r.fulfill(status=502, content_type="application/json",
                             body=json.dumps({"detail": "OpenStreetMap (API Overpass) non risponde: riprova tra qualche minuto."}))
        return r.fulfill(status=200, content_type="application/json", body=json.dumps({"type": "FeatureCollection", "licenza": "ODbL 1.0", **confine}))
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), edifici3d)
    pg.route("**/api/edifici/osm?*", osm)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length === 2 && {s}.osmAttivo && !!{s}.mappa.getSource('corpi_1')")
    assert pg.evaluate(f"{s}.archivi[0].istat") == "099014" and pg.evaluate(f"{s}.archivi[1].osm") is True
    assert "OpenStreetMap" in pg.text_content("#messaggio")
    # zona coperta: il confine del comune di Rimini, non il riquadro che sborda su Riccione
    from pyproj import Transformer
    muro = Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True).transform(785545.0, 4884810.0)
    assert pg.evaluate(f"{E}.coperto({muro[0]}, {muro[1]})") is True
    # un punto di Riccione e uno di Rimini vicini, dentro il riquadro: si cercano sul confine con i confini ISTAT del sito
    coppia = pg.evaluate("""(async () => { const C = window.EUGENIO_CONFINI; let prima = null;
      for (let k = 0; k <= 300; k++) { const lon = 12.60 + k * 0.0002, lat = 44.035 - k * 0.00012; const c = await C.comuneNelPunto(lon, lat);
        if (c && prima && prima.c.istat === '099014' && c.istat === '099013') return [prima.p, [lon, lat]]; if (c) prima = { c, p: [lon, lat] }; }
      return null; })()""")
    assert coppia, "confine Rimini–Riccione non trovato"
    (lo_ri, la_ri), (lo_rc, la_rc) = coppia
    assert pg.evaluate(f"{E}.coperto({lo_rc + 0.002}, {la_rc - 0.001})") is False                  # Riccione, dentro il riquadro
    assert pg.evaluate(f"{E}.coperto({lo_ri - 0.002}, {la_ri + 0.001})") is True
    # corpi OSM: quello che cade nel comune di Rimini (coperto dal DBTR) si scarta, quello di Riccione resta
    confine["features"] = [_quadrato("w1", lo_ri - 0.002, la_ri + 0.001), _quadrato("w2", lo_rc + 0.002, la_rc - 0.001)]
    ids = pg.evaluate(f"(async () => (await {E}.edificiOsm({lo_rc + 0.0021}, {la_rc - 0.0009})).map((f) => f.properties.id))()")
    assert ids == ["w2"]
    # Pesaro (fuori ER): punto sull'ospedale → corpi OSM, edificio del multipoligono scelto, avviso del ripiego
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [12.9063, 43.9042], zoom: 18 }}); {E}.impostaPunto(12.9061, 43.90405, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'r400'")
    msg = pg.text_content("#messaggio")
    assert "OpenStreetMap" in msg and "ODbL" in msg and "stimate" in msg and "ripiego" in msg
    assert pg.evaluate(f"{s}.mappa.getSource('corpi_1').serialize().data.features.length") >= 3
    assert not pg.locator("#fonti-osm").is_hidden() and "ODbL" in pg.text_content("#fonti-osm")
    n = len(chiamate)
    # Genera il 3D: corpi OSM con il cortile, fonte e licenza dichiarate, terreno piano
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 2")
    d = pg.evaluate(f"""(() => {{ const st = {s}; return {{ lic: [...new Set(st.corpi.map((c) => c.licenza))], buchi: st.corpi.map((c) => c.buchi.length),
      quote: st.corpi.concat(st.vicini).map((c) => c.quota), fonti: document.getElementById('fonti-corpi').textContent,
      tab: document.getElementById('tabella-corpi').textContent, scheda: document.getElementById('scheda-edificio').textContent,
      msg: document.getElementById('messaggio').textContent, terreno: !!st.mappa.getTerrain() }}; }})()""")
    assert d["lic"] == ["ODbL 1.0"] and sorted(d["buchi"]) == [0, 1] and set(d["quote"]) == {0}
    assert "OpenStreetMap" in d["fonti"] and "ODbL 1.0" in d["tab"] and "ODbL 1.0" in d["scheda"] and not d["terreno"]
    assert "OpenStreetMap" in d["msg"] and "stimate" in d["msg"]
    assert len(chiamate) == n                                                      # stessa cella: nessuna nuova richiesta
    rep = pg.evaluate(f"{E}.corpoReport()")
    assert any("OpenStreetMap contributors" in f and "Open Database License" in f for f in rep["fonti"])
    assert not any("Regione Emilia-Romagna" in f for f in rep["fonti"]), rep["fonti"]   # niente attribuzione CC BY che non c'entra
    assert any("ripiego" in x and "stimate" in x for x in rep["note"]) and {c["licenza"] for c in rep["corpi"]} == {"ODbL 1.0"}
    pg.uncheck("#strato-ortofoto")              # a Pesaro c'è solo il Geoportale «solo dal vivo»: niente foto nell'immagine
    with pg.expect_download() as dl:
        pg.evaluate("document.querySelector('#scarica-3d button[data-formato=\"pdf\"]').click()")
    dest = tmp_path / "osm.pdf"; dl.value.save_as(dest)
    pdf = dest.read_bytes()
    assert pdf.startswith(b"%PDF") and b"OpenStreetMap" in pdf and b"ODbL" in pdf
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{s}.in3d")
    # Cesena (ER, comune non preparato): Overpass giù → messaggio chiaro, nessun edificio, niente 3D
    pg.evaluate(f"(() => {{ {E}.impostaPunto(12.2405, 44.1405, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, "/non ha risposto/.test(document.getElementById('messaggio').textContent)")
    t = pg.text_content("#messaggio")
    assert "OpenStreetMap" in t and "Overpass" in t and "fuori dalla zona coperta" in t
    assert pg.locator("#genera-3d").is_disabled() and pg.evaluate(f"{s}.daGenerare") is None
    # dentro Rimini: nessuna richiesta a OpenStreetMap (vale il DBTR)
    n = len(chiamate)
    pg.evaluate(f"(() => {{ {E}.impostaPunto({muro[0]}, {muro[1]}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-CORTE'")
    assert len(chiamate) == n and "OpenStreetMap" not in pg.text_content("#messaggio")
    assert not pg.errori, pg.errori
    ctx.close()


# ----------------------------------------------------------------------------------- 07/11/2026: terreno dal server
def test_modelli3d_terreno_dal_server_e_altezza_stimata(browser, base, tmp_path):
    """Il terreno 3D viene da /api/terreno/{z}/{x}/{y}.png (l'archivio non ha più terreno.pmtiles): qui il server simulato
    dà le tessere fino allo zoom 13 e risponde 404 sopra (come fuori dall'Italia): MapLibre usa la tessera di livello più
    basso, nessun errore. Un corpo con l'altezza del DBTR non plausibile mostra «altezza stimata (dato DBTR non plausibile)»."""
    import io
    import sys
    import numpy as np
    from PIL import Image
    sys.path.insert(0, str(SITO.parents[1] / "fase10-edifici3d"))
    from shapely.geometry import box
    from edifici3d import modello as M
    from edifici3d.__main__ import prepara_corpi
    x0, y0 = 785540.0, 4884790.0
    corpi = [M.Corpo(id="A1", edificio="E-A", sagoma=box(x0, y0, x0 + 30, y0 + 20), quota_terreno=100, gronda=12,
                     fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)"),
             M.Corpo(id="A2", edificio="E-A", sagoma=box(x0 + 30, y0, x0 + 33, y0 + 3), quota_terreno=100, gronda=8,
                     fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="stima: altezza DBTR non plausibile (114 m)",
                     qualita="altezza stimata (dato DBTR non plausibile)", extra={"h_dbtr_scartata": 114.0, "stima_altezza": "vicini"})]
    out = tmp_path / "cc-by" / "er" / "prodotti"
    ind = prepara_corpi(corpi, None, out, "CC BY 4.0", "Regione Emilia-Romagna – DBTR, CC BY 4.0", extra={"nome": "DBTR Emilia-Romagna"})
    assert not (out / "terreno.pmtiles").exists() and ind["terreno"] == "/api/terreno/{z}/{x}/{y}.png"
    (tmp_path / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}]}),
                                           encoding="utf-8")
    v = 100.0 + 32768.0                                  # terreno piatto a 100 m in Terrarium
    rgb = np.zeros((256, 256, 3), dtype="uint8"); rgb[..., 0] = int(v // 256); rgb[..., 1] = int(v % 256)
    b = io.BytesIO(); Image.fromarray(rgb, "RGB").save(b, format="PNG"); png = b.getvalue()
    richieste = []

    def terreno(r):
        if r.request.url.split("?")[0].endswith("/api/terreno/fonti"):
            return r.fulfill(status=200, content_type="application/json", body=json.dumps({"attivo": True, "dtm": []}))
        z = int(r.request.url.split("/api/terreno/")[1].split("/")[0])
        richieste.append(z)
        return r.fulfill(status=200, content_type="image/png", body=png) if z <= 13 else r.fulfill(status=404, body="")

    def edifici3d(r):
        p = tmp_path / re.sub(r"^.*?/edifici3d/", "", r.request.url.split("?")[0])
        if not p.is_file():
            return r.fulfill(status=404, body="{}")
        dati = p.read_bytes(); rng = r.request.headers.get("range")
        tipo = "application/json" if p.suffix == ".json" else "application/octet-stream"
        if rng:
            a, bb = rng.replace("bytes=", "").split("-"); a = int(a); bb = int(bb) if bb else len(dati) - 1
            return r.fulfill(status=206, body=dati[a:bb + 1], headers={"Content-Type": tipo, "Content-Range": f"bytes {a}-{min(bb, len(dati) - 1)}/{len(dati)}"})
        return r.fulfill(status=200, body=dati, headers={"Content-Type": tipo})
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), edifici3d)
    pg.route("**/api/terreno/**", terreno)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length >= 1 && {s}.mappa.getSource('terreno')")
    src = pg.evaluate(f"(() => {{ const x = {s}.mappa.getSource('terreno'); return {{ tiles: x.tiles, max: x.maxzoom }}; }})()")
    assert src["tiles"][0].endswith("/api/terreno/{z}/{x}/{y}.png") and src["max"] == 15
    pg.evaluate(f"{s}.mappa.on('error', (e) => {{ (window.__erroriMappa = window.__erroriMappa || []).push(String(e && e.error && e.error.message || e)); }})")
    from pyproj import Transformer
    lon, lat = Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True).transform(x0 + 15, y0 + 10)
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }}); {E}.impostaPunto({lon}, {lat}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-A'")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 2 && !!{s}.mappa.getTerrain()")
    attendi(pg, f"(() => {{ const q = {s}.mappa.queryTerrainElevation([{lon}, {lat}]); return q !== null && Math.abs(q - 100) < 1; }})()", 20000)
    assert max(richieste) >= 14 and min(richieste) <= 13          # chiede anche gli zoom alti, usa quelli bassi
    tab = pg.text_content("#tabella-corpi")
    assert "altezza stimata (dato DBTR non plausibile: 114 m)" in tab
    rep = pg.evaluate(f"{E}.corpoReport()")
    assert any("non plausibile" in (c.get("fonte_altezza") or "") for c in rep["corpi"])
    assert "Copernicus" in pg.evaluate(f"JSON.stringify({E}.opzioniImmagine())")
    assert not pg.evaluate("window.__erroriMappa || []") and not pg.errori, pg.errori
    ctx.close()
    # rotta del terreno assente (api non ancora ricostruita, TERRENO_ATTIVO=false): la mappa si apre lo stesso, piatta
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), edifici3d)
    pg.goto(base + "modelli3d.html")
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length >= 1")
    assert pg.evaluate(f"!{s}.mappa.getSource('terreno') && {s}.terrenoServer === false") and not pg.errori
    ctx.close()


# ----------------------------------------------------------------------------------- 07/11/2026 sera: pagine 3D unificate
PAGINE_3D_TUTTE = ["modelli3d.html", "edificio-geometria.html", "edificio-consumi.html", "edificio-obblighi.html", "fv-ombre.html",
                   "fv-producibilita.html", "fv-irradiazione.html", "fv-pvgis.html", "fv-dlgs199.html"]


def _servi_archivio(radice):
    def edifici3d(r):
        p = radice / re.sub(r"^.*?/edifici3d/", "", r.request.url.split("?")[0])
        if not p.is_file():
            return r.fulfill(status=404, body="{}")
        dati = p.read_bytes(); rng = r.request.headers.get("range")
        tipo = "application/json" if p.suffix == ".json" else "application/octet-stream"
        if rng:
            a, bb = rng.replace("bytes=", "").split("-"); a = int(a); bb = int(bb) if bb else len(dati) - 1
            return r.fulfill(status=206, body=dati[a:bb + 1], headers={"Content-Type": tipo, "Content-Range": f"bytes {a}-{min(bb, len(dati) - 1)}/{len(dati)}"})
        return r.fulfill(status=200, body=dati, headers={"Content-Type": tipo})
    return edifici3d


def _locale_sintetico(lon=11.9105, lat=44.4140, n=4):
    """DB topografico «letto nel browser» (stesse proprietà di tessere.feature_da_corpi): un edificio a due corpi e vicini."""
    fs = []
    for k in range(n):
        lo = lon + 0.0004 * k
        fs.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[lo, lat], [lo + 0.0002, lat], [lo + 0.0002, lat + 0.0002],
                   [lo, lat + 0.0002], [lo, lat]]]}, "properties": {"id": f"L{k}", "edificio": "E-LUGO" if k < 2 else f"V{k}", "gronda": 10 + k,
                   "altezza": 10 + k, "tetto": "piano", "quota_terreno": 14, "fonte_sagoma": "DBTR Emilia-Romagna – UVL (dal tuo file)",
                   "fonte_altezza": "DBTR H_UVL (altezza del corpo, ±3 m)", "licenza": "CC BY 4.0"}})
    fs[1]["geometry"]["coordinates"][0] = [[lon + 0.0002, lat], [lon + 0.0004, lat], [lon + 0.0004, lat + 0.0002], [lon + 0.0002, lat + 0.0002], [lon + 0.0002, lat]]
    return {"features": fs, "riquadro": [lon, lat, lon + 0.0004 * n, lat + 0.0002], "nome": "Lugo (prova)", "licenza": "CC BY 4.0",
            "attribuzione": "Regione Emilia-Romagna – DBTR, CC BY 4.0", "istat": None}


def test_pagine_3d_unificate_dbtr_osm_e_file_locale(browser, base, tmp_path):
    """Tutte le pagine 3D: archivio DBTR per comune da archivi.json (edificio a corte), «Genera il 3D», passo della pagina in
    evidenza; Edificio › Geometria e Fotovoltaico › Producibilità anche col ripiego OSM (Pesaro, Overpass simulato: altezze
    con la loro origine e nota sotto la mappa) e con il DB topografico caricato nel browser (?dbtr=locale)."""
    _archivio_con_cortile(tmp_path)
    (tmp_path / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna – Rimini",
                                                                    "istat": "099014"}]}), encoding="utf-8")
    pesaro = _osm_al_volo(XML_PESARO, 12.906, 43.904)
    assert {f["properties"]["origine_altezza"] for f in pesaro["features"]} == {"osm_piani", "fissa"}
    from pyproj import Transformer
    muro = Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True).transform(785545.0, 4884810.0)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    passi = {"edificio-geometria.html": "passo-geometria", "edificio-consumi.html": "passo-consumi", "edificio-obblighi.html": "passo-obblighi",
             "fv-ombre.html": "passo-ombre", "fv-producibilita.html": "passo-fv", "fv-irradiazione.html": "passo-facciate",
             "fv-pvgis.html": "passo-pvgis", "fv-dlgs199.html": "passo-obblighi"}
    for nome in PAGINE_3D_TUTTE:
        ctx, pg = pagina(browser)
        _con_strati(pg)
        pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
        pg.route("**/api/edifici/osm?*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(pesaro)))
        pg.goto(base + nome)
        webgl(pg)
        attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length === 2 && {s}.archivi[0].istat === '099014' && {s}.archivi[1].osm", 25000)
        assert pg.evaluate(f"{s}.base") == "/edifici3d/cc-by/er/prodotti/", nome            # mai la demo
        pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{muro[0]}, {muro[1]}], zoom: 18 }}); {E}.impostaPunto({muro[0]}, {muro[1]}, 'clic'); return {E}.puntoCambiato(); }})()")
        attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-CORTE'")
        pg.evaluate("document.getElementById('genera-3d').click()")
        attendi(pg, f"{s}.in3d && {s}.corpi.length === 2 && !{s}.sintetico")
        if nome in passi:
            assert pg.evaluate(f"document.getElementById('{passi[nome]}').classList.contains('in-evidenza')"), nome
        assert not pg.evaluate(f"{s}.corpi.some((c) => c.sintetico)") and pg.locator("#avviso-sintetico").is_hidden(), nome
        if nome in ("edificio-geometria.html", "fv-producibilita.html"):
            titolo = pg.evaluate(f"{E}.opzioniImmagine().titolo")
            assert titolo.startswith(pg.text_content("main h1").strip()), titolo
            pg.evaluate("document.getElementById('torna-2d').click()")
            attendi(pg, f"!{s}.in3d")
            # ripiego OSM a Pesaro: altezze con l'origine per corpo e nota sotto la mappa
            pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [12.9063, 43.9042], zoom: 18 }}); {E}.impostaPunto(12.9061, 43.90405, 'clic'); return {E}.puntoCambiato(); }})()")
            attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'r400'")
            attendi(pg, "!document.getElementById('nota-altezze-osm').hidden")
            nota = pg.text_content("#nota-altezze-osm")
            assert "Edifici OpenStreetMap nella vista" in nota and "con l'altezza dal dato OSM" in nota and "a 9 m fissi" in nota, nota
            pg.evaluate("document.getElementById('genera-3d').click()")
            attendi(pg, f"{s}.in3d && {s}.corpi.length === 2")
            nota = pg.text_content("#nota-altezze-osm")
            assert "dell'edificio e dei vicini" in nota and "2 con l'altezza dal dato OSM" in nota, nota
            rep = pg.evaluate(f"{E}.corpoReport()")
            assert any("Edifici OpenStreetMap dell'edificio e dei vicini" in x for x in rep["note"]), rep["note"]
            pg.uncheck("#strato-ortofoto")      # a Pesaro c'è solo il Geoportale «solo dal vivo»
            assert any("Edifici OpenStreetMap" in x for x in pg.evaluate(f"{E}.opzioniImmagine().righe"))
        assert not pg.errori, (nome, pg.errori)
        ctx.close()
    # DB topografico caricato nel browser (Lugo, fuori dagli archivi del server) e un corpo OSM vicino senza altezza:
    # l'altezza diventa la mediana dei corpi del file
    loc = _locale_sintetico()
    lugo_osm = {"type": "FeatureCollection", "licenza": "ODbL 1.0", "centro": [11.912, 44.414], "features": [
        _quadrato("w9", 11.9112, 44.4150)]}
    lugo_osm["features"][0]["properties"]["origine_altezza"] = "fissa"
    for nome in ("edificio-geometria.html", "fv-producibilita.html"):
        ctx, pg = pagina(browser)
        _con_strati(pg)
        pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
        pg.route("**/api/edifici/osm?*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(lugo_osm)))
        pg.goto(base + nome)
        attendi(pg, "!!window.EUGENIO_DBTR_LOCALE")
        pg.evaluate(f"window.EUGENIO_DBTR_LOCALE.salva({json.dumps(loc)})")
        pg.goto(base + nome + "?dbtr=locale")
        webgl(pg)
        attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.locale && {s}.archivi.some((a) => a.locale)", 25000)
        pg.evaluate(f"(() => {{ {E}.impostaPunto(11.9106, 44.4141, 'clic'); return {E}.puntoCambiato(); }})()")
        attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-LUGO'")
        pg.evaluate("document.getElementById('genera-3d').click()")
        attendi(pg, f"{s}.in3d && {s}.corpi.length === 2")
        assert pg.evaluate(f"{s}.corpi.every((c) => {s}.archivi[c.archivio].locale)")
        # OSM fuori dal riquadro del file: altezza dalla mediana dei corpi del file (10, 11, 12, 13 → 11,5 m)
        fs = pg.evaluate(f"(async () => (await {E}.edificiOsm(11.9113, 44.4151)).map((f) => f.properties))()")
        assert fs and fs[0]["origine_altezza"] == "dbtr_vicini" and fs[0]["gronda"] == 11.5, fs
        assert "del DB topografico del tuo file" in fs[0]["fonte_altezza"]
        pg.evaluate("window.EUGENIO_DBTR_LOCALE.togli()")
        assert not pg.errori, (nome, pg.errori)
        ctx.close()


# ----------------------------------------------------------------------------------- 07/11/2026 sera: prove di Paolo (F21)
def _diciannove_comuni(radice):
    """Archivi finti dei 19 comuni (riquadri e codici ISTAT veri, archivi.json come sul server) con un corpo di 4 m in
    ogni punto di prova: il corpo più grande del comune e, dove c'era, un corpo vicino al confine che con i confini ISTAT
    generalizzati cadeva «fuori» (07/11/2026, prima della correzione: 5 % dei corpi, Cattolica 13 %)."""
    dati = json.loads((Path(__file__).parent / "punti_19_comuni.json").read_text(encoding="utf-8"))
    voci = []
    for nome, d in dati.items():
        cart = radice / "cc-by" / "er" / nome / "prodotti"
        (cart / "contesto").mkdir(parents=True)
        celle = {}
        for k, (lo, la) in enumerate(d["punti"]):
            q = 0.00002
            f = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[lo - q, la - q], [lo + q, la - q], [lo + q, la + q], [lo - q, la + q], [lo - q, la - q]]]},
                 "properties": {"id": f"{nome}-{k}", "edificio": f"{nome}-{k}", "gronda": 6, "tetto": "piano", "quota_terreno": 10,
                                "fonte_sagoma": "DBTR Emilia-Romagna – UVL", "fonte_altezza": "DBTR H_UVL", "licenza": "CC BY 4.0"}}
            celle.setdefault(f"{math.floor(lo / 0.01)}_{math.floor(la / 0.01)}", []).append(f)
        for n, fs in celle.items():
            (cart / "contesto" / f"{n}.json").write_text(json.dumps({"type": "FeatureCollection", "features": fs}), encoding="utf-8")
        (cart / "indice.json").write_text(json.dumps({"riquadro": d["riquadro"], "cella": 0.01, "licenza": "CC BY 4.0", "istat": d["istat"],
                                                      "attribuzione": "Regione Emilia-Romagna – DBTR, CC BY 4.0", "nome": nome,
                                                      "centro": d["punti"][0]}), encoding="utf-8")
        v = {"base": f"/edifici3d/cc-by/er/{nome}/prodotti/", "nome": nome, "licenza": "CC BY 4.0", "riquadro": d["riquadro"]}
        if d["istat"]:
            v["istat"] = d["istat"]
        voci.append(v)
    (radice / "archivi.json").write_text(json.dumps({"archivi": voci}), encoding="utf-8")
    return dati


def test_diciannove_comuni_coperti_senza_osm(browser, base, tmp_path):
    """Bagno di Romagna «senza DBTR» nelle prove di Paolo: per un punto dentro ciascuno dei 19 comuni coperto() dice sì,
    l'edificio scelto è quello del DBTR e nessuna richiesta va a /api/edifici/osm; archivi.json chiesto con ?v= e senza
    copia (cache: no-cache)."""
    dati = _diciannove_comuni(tmp_path)
    ctx, pg = pagina(browser)
    osm, richieste_aj = [], []
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/edifici/osm?*", lambda r: (osm.append(r.request.url), r.fulfill(status=200, content_type="application/json",
             body=json.dumps({"type": "FeatureCollection", "features": []})))[1])
    pg.on("request", lambda r: richieste_aj.append(r.url) if "archivi.json" in r.url else None)
    pg.goto(base + "modelli3d.html")
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.filter((a) => !a.osm).length === 19", 30000)
    assert richieste_aj and all("?v=" in u for u in richieste_aj), richieste_aj
    fuori = pg.evaluate(f"""async (dati) => {{ const no = [];
        for (const [n, d] of Object.entries(dati)) for (const [lo, la] of d.punti) if (!(await {E}.coperto(lo, la))) no.push([n, lo, la]);
        return no; }}""", dati)
    assert fuori == [], fuori
    for nome in ("bagno-di-romagna", "cattolica", "santarcangelo"):
        lo, la = dati[nome]["punti"][-1]
        pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{lo}, {la}], zoom: 18 }}); {E}.impostaPunto({lo}, {la}, 'clic'); return {E}.puntoCambiato(); }})()")
        attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio.startsWith('{nome}-')")
    assert osm == [], osm
    assert not pg.errori, pg.errori
    ctx.close()


def _archivio_prove_paolo(radice):
    """Edificio E-T a due corpi su un pendio (quote 100 e 112 m): T1 con il colmo del DBTR (a capanna, 30×12 m), T2 piano;
    un vicino V1."""
    import sys
    sys.path.insert(0, str(SITO.parents[1] / "fase10-edifici3d"))
    from shapely.geometry import box
    from edifici3d import modello as M
    from edifici3d.__main__ import prepara_corpi
    x0, y0 = 785540.0, 4884790.0
    c = dict(fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)")
    corpi = [M.Corpo(id="T1", edificio="E-T", sagoma=box(x0, y0, x0 + 30, y0 + 12), quota_terreno=100, gronda=7, colmo=10, tetto="capanna", falde=2, **c),
             M.Corpo(id="T2", edificio="E-T", sagoma=box(x0, y0 + 60, x0 + 12, y0 + 72), quota_terreno=112, gronda=6, **c),
             M.Corpo(id="V1", edificio="E-V", sagoma=box(x0 - 40, y0, x0 - 20, y0 + 20), quota_terreno=100, gronda=9, **c)]
    out = radice / "cc-by" / "er" / "prodotti"
    prepara_corpi(corpi, None, out, "CC BY 4.0", "Regione Emilia-Romagna – DBTR, CC BY 4.0", extra={"nome": "DBTR Emilia-Romagna"})
    (radice / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}]}), encoding="utf-8")
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True)
    return t.transform(x0 + 15, y0 + 6), t.transform(x0 + 6, y0 + 66)


def _terreno_in_pendenza(lat0=44.05):
    """Tessere Terrarium con la quota che sale verso nord (0,2 m per pixel di tessera): pendio vero sotto i corpi."""
    import io
    import numpy as np
    from PIL import Image
    cache = {}

    def terreno(r):
        u = r.request.url.split("?")[0]
        if u.endswith("/api/terreno/fonti"):
            return r.fulfill(status=200, content_type="application/json", body=json.dumps({"attivo": True, "dtm": []}))
        z, x, y = (int(v) for v in u.split("/api/terreno/")[1].replace(".png", "").split("/"))
        if (z, x, y) not in cache:
            n = 2 ** z
            j = y + (np.arange(256)[:, None] + 0.5) / 256
            lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * j / n))))
            h = np.broadcast_to(np.clip(100 + (lat - lat0) * 111000 * 0.2, 0, 3000), (256, 256)) + 32768
            rgb = np.zeros((256, 256, 3), dtype="uint8"); rgb[..., 0] = (h // 256).astype("uint8"); rgb[..., 1] = (h % 256).astype("uint8")
            b = io.BytesIO(); Image.fromarray(rgb, "RGB").save(b, format="PNG"); cache[(z, x, y)] = b.getvalue()
        return r.fulfill(status=200, body=cache[(z, x, y)], headers={"Content-Type": "image/png", "X-Terreno-Fonte": "dtm",
                                                                     "Access-Control-Expose-Headers": "X-Terreno-Fonte"})
    return terreno


def test_modelli3d_prove_di_paolo(browser, base, tmp_path):
    """Punti 2–6 delle prove del 07/11/2026 sera: barra di scorrimento della colonna a sinistra (lontana dal divisore);
    rilievo ombreggiato, terreno in pendenza sotto i corpi (dal 09/11/2026 c senza esagerazione); legenda del terreno dalla
    fonte delle tessere; tetti piani (dal 09/11/2026 c; prima stimati dal colmo DBTR); isometrica a circa il
    doppio dell'edificio; edifici OSM in marrone; nuova ricerca nel 3D → mappa 2D dritta e 3D azzerato; mappa portata
    lontano → 2D."""
    (lon1, lat1), (lon2, lat2) = _archivio_prove_paolo(tmp_path)
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(lat1))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length >= 1 && {s}.mappa.getSource('terreno')")
    # 2: la colonna della mappa scorre con la barra a sinistra, il contenuto resta da sinistra a destra
    d = pg.evaluate("""() => { const a = document.querySelector('main > .mappa-area'), h = a.querySelector('h1');
        return [getComputedStyle(a).direction, getComputedStyle(h).direction, getComputedStyle(a).overflowY]; }""")
    assert d == ["rtl", "ltr", "auto"], d
    # OSM in marrone (archivio virtuale del ripiego)
    col = pg.evaluate(f"(() => {{ const k = {s}.archivi.findIndex((a) => a.osm); return k < 0 ? null : {s}.mappa.getPaintProperty({s}.sorgentiCorpi[k], 'fill-extrusion-color'); }})()")
    assert col == "#9a6440", col
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{lon1}, {lat1}], zoom: 18 }}); {E}.impostaPunto({lon1}, {lat1}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-T'")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 2 && !!{s}.mappa.getTerrain()")
    # «diventa nera» (Bagno di Romagna): la camera parte dalla quota del terreno sotto l'edificio, non da 0 m (dentro la
    # collina); cambiare la fonte dell'ortofoto non muove la camera (AGEA 2012 «saltava lontano»)
    assert abs(pg.evaluate(f"{s}.mappa.getCenterElevation()") - 100) < 15
    pg.wait_for_timeout(800)
    cam0 = pg.evaluate(f"(() => {{ const m = {s}.mappa; return [m.getZoom(), m.getPitch(), m.getCenter().lng, m.getCenter().lat]; }})()")
    opz = pg.evaluate("[...document.getElementById('sfondo-ortofoto').options].map((o) => o.value)")
    assert "s2cloudless2016" in opz and "pcn2012" in opz, opz                         # stesso elenco della pagina Ortofoto
    for fonte in ("pcn2012", "s2cloudless2016", "rer2023"):
        pg.select_option("#sfondo-ortofoto", fonte)
        pg.wait_for_timeout(500)
        cam = pg.evaluate(f"(() => {{ const m = {s}.mappa; return [m.getZoom(), m.getPitch(), m.getCenter().lng, m.getCenter().lat]; }})()")
        assert all(abs(x - y) < 1e-6 for x, y in zip(cam, cam0)), (fonte, cam, cam0)
    # 6: dal 09/11/2026 c tutti i tetti partono piani (anche T1, che ha il colmo nel DBTR); falde solo scelte con la tegola
    t = pg.evaluate(f"{s}.corpi.map((c) => [c.id, c.tettoStimato, c.tetto, (c.falde || []).length])")
    assert sorted(t) == [["T1", False, "piano", 0], ["T2", False, "piano", 0]], t
    assert pg.evaluate(f"{s}.mappa.getSource('falde').serialize().data.features.length") == 0
    assert "Tetti piani" in pg.text_content("#messaggio-falde") and "tetto piano" in pg.text_content("#tabella-corpi")
    rep = pg.evaluate(f"{E}.corpoReport()")
    assert rep["falde"] == [] and rep["tetti"]["conteggi"]["piano"] == 2
    # terreno in pendenza: le basi dei due corpi sono a quote diverse; ombreggiatura del rilievo visibile
    try:
        attendi(pg, f"""(() => {{ const m = {s}.mappa, a = m.queryTerrainElevation([{lon1}, {lat1}]), b = m.queryTerrainElevation([{lon2}, {lat2}]);
            window.__q = [a, b]; return a !== null && b !== null && b - a > 8; }})()""", 20000)
    except Exception:
        raise AssertionError(pg.evaluate("window.__q"))
    assert pg.evaluate(f"{s}.mappa.getLayoutProperty('rilievo', 'visibility')") == "visible"
    assert pg.evaluate(f"{s}.mappa.getLayer('rilievo').type") == "hillshade"
    attendi(pg, "/Terreno: DTM 5 m Regione Emilia-Romagna/.test(document.getElementById('legenda-terreno').textContent)")
    assert pg.evaluate(f"{s}.mappa.getTerrain().exaggeration") == 1        # 09/11/2026 c: niente più esagerazione
    righe = " ".join(pg.evaluate(f"{E}.opzioniImmagine().righe"))
    assert "esagerato" not in righe and "Tetti: 2 piani." in righe and "Colori:" in righe, righe
    # 3: isometrica, inquadratura circa il doppio dell'edificio
    pg.evaluate(f"{E}.vistaNominata('iso')")
    pg.wait_for_timeout(900)
    q = pg.evaluate(f"""(() => {{ const m = {s}.mappa, pts = {s}.corpi.flatMap((c) => c.ring).map((p) => m.project({s}.proj.indietro(p)));
        const w = Math.max(...pts.map((p) => p.x)) - Math.min(...pts.map((p) => p.x)), h = Math.max(...pts.map((p) => p.y)) - Math.min(...pts.map((p) => p.y));
        const c = m.getContainer(); return [Math.max(w, h), Math.min(c.clientWidth, c.clientHeight)]; }})()""")
    assert 0.25 * q[1] < q[0] < 0.75 * q[1], q
    # 5: nuova ricerca durante il 3D → mappa 2D dritta, 3D tolto
    pg.evaluate(f"{E}.trovato({lon1 + 0.01}, {lat1}, {{ fonte_punto: 'ANNCSU', indirizzo_trovato: 'via Prova 1', comune_catasto: 'Rimini' }})")
    attendi(pg, f"!{s}.in3d && {s}.corpi.length === 0 && {s}.mappa.getSource('scelto').serialize().data.features.length === 0")
    pg.wait_for_timeout(1200)
    assert pg.evaluate(f"[{s}.mappa.getPitch(), {s}.mappa.getBearing()]") == [0, 0]
    # mappa portata lontano dal 3D → 2D
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{lon1}, {lat1}], zoom: 18 }}); {E}.impostaPunto({lon1}, {lat1}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'E-T'")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 2")
    pg.evaluate(f"{s}.mappa.jumpTo({{ center: [{lon1 + 0.05}, {lat1}] }})")
    attendi(pg, f"!{s}.in3d && {s}.corpi.length === 0")
    assert not pg.errori, pg.errori
    ctx.close()


def test_ricerca_solo_comune_e_coordinate_zero(browser, base):
    """(A) solo il comune → centro del comune, nessuna chiamata a /api/patrimonio; (C) risposta con 0,0 (Novafeltria) →
    mai il golfo di Guinea: centro del comune con l'avviso. In Modelli 3D e in Ortofoto."""
    zero = {"righe": [{"id": "1", "lat": 0.0, "lon": 0.0, "esito": "verificare", "fonte_punto": "Zornade",
                       "nota": "indirizzo non trovato da Zornade (via xxiv maggio novafeltria)"}]}
    for nome, s_mappa in (("modelli3d.html", "window.EUGENIO_EDIFICIO3D.stato.mappa"), ("ortofoto.html", "window.EUGENIO_ORTOFOTO.stato.mappa")):
        ctx, pg = pagina(browser)
        chiamate = []
        pg.route("**/api/patrimonio", lambda r: (chiamate.append(1), r.fulfill(status=200, content_type="application/json", body=json.dumps(zero)))[1])
        pg.goto(base + nome)
        webgl(pg)
        attendi(pg, f"!!({s_mappa}) && !!document.getElementById('cerca-comune')", 25000)
        pg.fill("#cerca-comune", "Novafeltria")
        pg.click("#cerca-indirizzo")
        attendi(pg, "/centro del comune di Novafeltria/.test(document.getElementById('messaggio-cerca').textContent)")
        pg.wait_for_timeout(1300)
        c = pg.evaluate(f"(() => {{ const c = {s_mappa}.getCenter(); return [c.lng, c.lat, {s_mappa}.getZoom()]; }})()")
        assert chiamate == [] and abs(c[0] - 12.29) < 0.08 and abs(c[1] - 43.89) < 0.08 and c[2] < 15, c
        pg.fill("#cerca-via", "via XXIV Maggio 10")
        pg.click("#cerca-indirizzo")
        attendi(pg, "/senza coordinate/.test(document.getElementById('messaggio-cerca').textContent)")
        pg.wait_for_timeout(1300)
        c = pg.evaluate(f"(() => {{ const c = {s_mappa}.getCenter(); return [c.lng, c.lat]; }})()")
        assert chiamate == [1] and abs(c[0] - 12.29) < 0.08 and abs(c[1] - 43.89) < 0.08, c
        assert "0.00000" not in pg.text_content("#messaggio-cerca")
        assert not pg.errori, pg.errori
        ctx.close()


def test_telefono_senza_scorrimento_di_lato(browser, base):
    """07/11/2026 sera: ricerca nella colonna destra, barra a sinistra, zona «trascina qui», «chiedi dove salvarlo»: a 375
    px nessuna pagina scorre di lato e nessun errore JavaScript."""
    for nome in PAGINE_3D_TUTTE + ["ortofoto.html", "aggiungi-dbtr.html", "dati.html", "legge10.html", "faq.html"]:
        ctx, pg = pagina(browser, larghezza=375, altezza=800)
        pg.goto(base + nome)
        pg.wait_for_timeout(1500)
        w = pg.evaluate("document.documentElement.scrollWidth")
        assert w <= 376, (nome, w)
        assert not pg.errori, (nome, pg.errori)
        ctx.close()


# ----------------------------------------------------------------------------------- 08/11/2026: ortofoto spostata a mano
MOTIVO_VETTORI = "Accendi un'ortofoto e almeno uno strato vettoriale (particelle o contorni) per allineare la foto alla cartografia."


def _tessere_rer(pg):
    """Tessere RER simulate (JPEG grigio) e registro degli indirizzi chiesti; errori della console raccolti."""
    import io
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (256, 256), (120, 120, 120)).save(b, "JPEG")
    jpg, chieste = b.getvalue(), []
    def servi(r):
        chieste.append(r.request.url)
        r.fulfill(status=200, content_type="image/jpeg", body=jpg)
    pg.route("**/api/ortofoto/rer2023/**", servi)
    pg.console_rossi = []
    pg.on("console", lambda m: pg.console_rossi.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
    return chieste


def _frecce(pg):
    return pg.evaluate("""(() => { const g = document.querySelector('#sposta-ortofoto .sposta-ortofoto');
      const b = (d) => g.querySelector('.freccia-' + d);
      return { attive: ['n', 's', 'o', 'e'].map((d) => !b(d).disabled), titolo: b('n').title, gruppo: g.title,
               etichetta: b('n').getAttribute('aria-label'), stato: g.querySelector('.sposta-stato').textContent,
               descritto: b('n').getAttribute('aria-describedby') || '', azzera: !g.querySelector('.sposta-azzera').disabled }; })()""")


def test_ortofoto_frecce_spostano_la_foto_non_i_vettori(browser, base):
    ctx, pg = pagina(browser)
    _con_strati(pg)
    chieste = _tessere_rer(pg)
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=18")
    webgl(pg)
    st = "window.EUGENIO_ORTOFOTO.stato"
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {st}.strati && {st}.sposta && {st}.scelta && document.querySelector('#sposta-ortofoto .freccia-n')")
    # accanto a «Scarica l'immagine», sotto la mappa
    assert pg.evaluate("document.querySelector('.comandi-ortofoto #scarica-ortofoto') && document.querySelector('.comandi-ortofoto #sposta-ortofoto') ? 1 : 0") == 1
    # contorni dell'archivio assenti (404), nessuno strato acceso: frecce spente, con il motivo nel title e per i lettori di schermo
    f = _frecce(pg)
    assert f["attive"] == [False] * 4 and not f["azzera"]
    assert f["titolo"] == MOTIVO_VETTORI and f["gruppo"] == MOTIVO_VETTORI and MOTIVO_VETTORI in f["stato"] and f["descritto"]
    # particelle accese: frecce attive, etichetta della freccia
    pg.check("#strato-particelle")
    attendi(pg, "!document.querySelector('#sposta-ortofoto .freccia-n').disabled")
    f = _frecce(pg)
    assert f["attive"] == [True] * 4 and f["stato"] == "Ortofoto al suo posto" and not f["azzera"]
    assert f["etichetta"] == f["titolo"] == "Sposta l'ortofoto di 1 m verso nord rispetto alla cartografia"
    centro0 = pg.evaluate(f"{st}.mappa.getCenter().toArray()")
    vettori0 = pg.evaluate(f"JSON.stringify({st}.mappa.getSource('strato-particelle').tiles)")
    # due clic a est e uno a sud (anche da tastiera): le tessere dell'ortofoto cambiano indirizzo, i vettori e la camera no
    pg.click("#sposta-ortofoto .freccia-e"); pg.click("#sposta-ortofoto .freccia-e")
    pg.focus("#sposta-ortofoto .freccia-s"); pg.keyboard.press("ArrowDown")
    attendi(pg, "/Ortofoto spostata: 2 m E, 1 m S/.test(document.querySelector('#sposta-ortofoto .sposta-stato').textContent)")
    attendi(pg, f"{st}.mappa.getSource('ortofoto').tiles[0].endsWith('?t=1&de=2&dn=-1')")
    pg.wait_for_timeout(1500)
    assert any("de=2&dn=-1" in u for u in chieste), chieste[-3:]
    assert pg.evaluate(f"JSON.stringify({st}.mappa.getSource('strato-particelle').tiles)") == vettori0
    assert pg.evaluate(f"{st}.mappa.getSource('contesto').tiles[0]").endswith("s2cloudless2016/{z}/{x}/{y}.jpg")    # il contesto resta fermo
    assert pg.evaluate(f"{st}.mappa.getCenter().toArray()") == pytest.approx(centro0, abs=1e-9)
    # ~1 m alla scala corrente: allo zoom 18 a 44° N un metro è circa 4,7 pixel (lo spostamento lo fa il proxy, prova Python)
    mpp = pg.evaluate(f"40075016.686 * Math.cos({st}.mappa.getCenter().lat * Math.PI / 180) / (512 * 2 ** {st}.mappa.getZoom())")
    assert 0.18 < mpp < 0.25
    # riga nell'immagine scaricata e memoria della sessione
    righe = pg.evaluate("window.EUGENIO_ORTOFOTO.opzioniImmagine().righe")
    assert "Ortofoto spostata manualmente di 2 m E, 1 m S rispetto alla cartografia." in righe
    assert pg.evaluate("JSON.parse(sessionStorage.getItem('eugenio-sposta-ortofoto:ortofoto'))") == {"fonte": "rer2023", "de": 2, "dn": -1}
    # strati spenti: frecce spente, lo spostamento resta dichiarato
    pg.uncheck("#strato-particelle")
    attendi(pg, "document.querySelector('#sposta-ortofoto .freccia-n').disabled")
    assert "Ortofoto spostata: 2 m E, 1 m S" in _frecce(pg)["stato"]
    pg.check("#strato-particelle")
    attendi(pg, "!document.querySelector('#sposta-ortofoto .sposta-azzera').disabled")
    # «Azzera»: indirizzo originale (copia del server), riga sparita
    pg.click("#sposta-ortofoto .sposta-azzera")
    attendi(pg, f"{st}.mappa.getSource('ortofoto').tiles[0].endsWith('/rer2023/{{z}}/{{x}}/{{y}}.jpg?t=1')")
    assert not any("spostata" in r for r in pg.evaluate("window.EUGENIO_ORTOFOTO.opzioniImmagine().righe"))
    # Sentinel-2 (tessere già pronte, 10 m): frecce spente con il motivo; cambiare fonte azzera
    pg.click("#sposta-ortofoto .freccia-n")
    pg.evaluate(f"{st}.manuale = true; document.querySelector('#fonti input[value=\"s2cloudless2016\"]').click()")
    attendi(pg, "document.querySelector('#sposta-ortofoto .freccia-n').disabled")
    f = _frecce(pg)
    assert "pixel di 10 m" in f["titolo"] and "pixel di 10 m" in f["gruppo"] and "spostata" not in f["stato"]
    pg.evaluate("document.querySelector('#fonti input[value=\"rer2023\"]').click()")
    attendi(pg, "!document.querySelector('#sposta-ortofoto .freccia-n').disabled")
    assert _frecce(pg)["stato"] == "Ortofoto al suo posto"
    assert not pg.errori, pg.errori
    assert not pg.console_rossi, pg.console_rossi
    ctx.close()


def test_modelli3d_frecce_in_2d_e_3d(browser, base, tmp_path):
    """Modelli 3D (e le pagine unificate): frecce accanto a «Genera il 3D», attive con un'ortofoto spostabile accesa e
    gli edifici dell'archivio sulla mappa; spente con Sentinel-2 o con l'ortofoto spenta; nel 3D la camera non salta."""
    for nome in ("modelli3d.html", "fv-ombre.html"):
        ctx, pg = pagina(browser)
        _con_strati(pg)
        chieste = _tessere_rer(pg)
        pg.goto(base + nome)
        webgl(pg)
        s = "window.EUGENIO_EDIFICIO3D.stato"
        attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.sposta && {s}.fontiOrtofoto")
        pg.evaluate(f"{s}.mappa.jumpTo({{center: [12.5683, 44.0594], zoom: 18}})")
        attendi(pg, f"{s}.ortofoto && {s}.ortofoto.id === 'rer2023'")
        assert pg.evaluate("document.querySelector('#comandi-edificio #genera-3d') && document.querySelector('#comandi-edificio #sposta-ortofoto .freccia-e') ? 1 : 0") == 1
        attendi(pg, "!document.querySelector('#sposta-ortofoto .freccia-e').disabled")
        f = _frecce(pg)
        assert f["attive"] == [True] * 4 and f["titolo"] == "Sposta l'ortofoto di 1 m verso nord rispetto alla cartografia"
        pg.click("#sposta-ortofoto .freccia-o")
        attendi(pg, f"{s}.mappa.getSource('ortofoto').tiles[0].endsWith('?t=1&de=-1&dn=0')")
        righe = pg.evaluate("window.EUGENIO_EDIFICIO3D.opzioniImmagine ? window.EUGENIO_EDIFICIO3D.opzioniImmagine().righe : null")
        if righe is not None:
            assert "Ortofoto spostata manualmente di 1 m O rispetto alla cartografia." in righe
        # ortofoto spenta nei livelli: frecce spente con il motivo
        pg.uncheck("#strato-ortofoto")
        attendi(pg, "document.querySelector('#sposta-ortofoto .freccia-n').disabled")
        assert MOTIVO_VETTORI in _frecce(pg)["titolo"]
        pg.check("#strato-ortofoto")
        attendi(pg, "!document.querySelector('#sposta-ortofoto .freccia-n').disabled")
        # vista inclinata (come il 3D): la camera non si muove spostando la foto
        pg.evaluate(f"{s}.mappa.jumpTo({{pitch: 55, bearing: 30}})")
        cam0 = pg.evaluate(f"[{s}.mappa.getCenter().lng, {s}.mappa.getCenter().lat, {s}.mappa.getZoom(), {s}.mappa.getPitch(), {s}.mappa.getBearing()]")
        pg.click("#sposta-ortofoto .freccia-n")
        attendi(pg, f"{s}.mappa.getSource('ortofoto').tiles[0].endsWith('&de=-1&dn=1')")
        pg.wait_for_timeout(800)
        cam1 = pg.evaluate(f"[{s}.mappa.getCenter().lng, {s}.mappa.getCenter().lat, {s}.mappa.getZoom(), {s}.mappa.getPitch(), {s}.mappa.getBearing()]")
        assert cam1 == pytest.approx(cam0, abs=1e-9)
        for _ in range(40):
            if any("de=-1&dn=1" in u for u in chieste):
                break
            pg.wait_for_timeout(250)
        assert any("de=-1&dn=1" in u for u in chieste), chieste[-3:]
        # Sentinel-2 dal selettore: frecce spente con il motivo, spostamento azzerato
        pg.select_option("#sfondo-ortofoto", "s2cloudless2016")
        attendi(pg, "document.querySelector('#sposta-ortofoto .freccia-n').disabled")
        assert "pixel di 10 m" in _frecce(pg)["gruppo"]
        assert not pg.errori, (nome, pg.errori)
        assert not pg.console_rossi, (nome, pg.console_rossi)
        ctx.close()


def _archivio_tetti(radice):
    """Edificio E-K: K1 con il colmo del DBTR (30×12), K2 senza colmo (20×10), K3 capannone (20×22); un vicino V1 a 30 m.
    Quota 100 m. Dal 09/11/2026 c tutti piani in partenza (archivio «cc-by/er» nella chiave dei tetti)."""
    import sys
    sys.path.insert(0, str(SITO.parents[1] / "fase10-edifici3d"))
    from shapely.geometry import box
    from edifici3d import modello as M
    from edifici3d.__main__ import prepara_corpi
    x0, y0 = 785540.0, 4884790.0
    c = dict(fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)", quota_terreno=100)
    corpi = [M.Corpo(id="K1", edificio="E-K", sagoma=box(x0, y0, x0 + 30, y0 + 12), gronda=7, colmo=10, tetto="capanna", falde=2, **c),
             M.Corpo(id="K2", edificio="E-K", sagoma=box(x0, y0 + 12, x0 + 20, y0 + 22), gronda=9, **c),
             M.Corpo(id="K3", edificio="E-K", sagoma=box(x0 + 30, y0, x0 + 50, y0 + 22), gronda=8, uso="capannone", **c),
             M.Corpo(id="V1", edificio="E-V", sagoma=box(x0 - 40, y0, x0 - 20, y0 + 20), gronda=9, **c)]
    out = radice / "cc-by" / "er" / "prodotti"
    prepara_corpi(corpi, None, out, "CC BY 4.0", "Regione Emilia-Romagna – DBTR, CC BY 4.0", extra={"nome": "DBTR Emilia-Romagna"})
    (radice / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}]}), encoding="utf-8")
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True).transform(x0 + 10, y0 + 17)


def _genera(pg, lon, lat, s, E, edificio="E-K", n=3):
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length >= 1", 25000)
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }}); {E}.impostaPunto({lon}, {lat}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === '{edificio}'")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === {n}", 25000)


def _clic_su_corpo(pg, s, corpo):
    """Clic sulla mappa al centro del corpo (dell'edificio scelto o vicino), con la vista dall'alto (in prospettiva il
    punto a terra può stare dietro un corpo più alto, come per chi clicca)."""
    pg.evaluate(f"{s}.mappa.jumpTo({{ pitch: 0, bearing: 0 }})")
    pg.wait_for_timeout(300)
    pg.evaluate(f"""(() => {{ const c = [...{s}.corpi, ...{s}.vicini].find((x) => x.id === '{corpo}');
        const ll = {s}.proj.indietro(window.EUGENIO_EDIFICI.centroide(c.ring));
        {s}.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: {s}.mappa.project(ll) }}); }})()""")


def test_tetti_piani_e_tegola_in_modelli3d(browser, base, tmp_path):
    """09/11/2026 c (decisione di Paolo, sostituisce la cascata dell'08/11): tutti i tetti partono piani, anche K1 che ha il
    colmo del DBTR; con la tegola di «Coperture» un clic dà a K2 un tetto a falde di 22° (capanna sul lato lungo), anche al
    capannone K3 (nessuna regola automatica); nota, legenda, tabella dei corpi, immagine e report lo dicono."""
    lon, lat = _archivio_tetti(tmp_path)
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(lat))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    _genera(pg, lon, lat, s, E)
    assert pg.locator("#forma-tetti").count() == 0
    t = pg.evaluate(f"Object.fromEntries({s}.corpi.map((c) => [c.id, [c.fonteTetto, c.tetto, (c.falde || []).length, c.colmo, c.gronda]]))")
    assert all(v[:4] == ["piano", "piano", 0, None] for v in t.values()) and t["K1"][4] == 7, t
    assert pg.text_content("#nota-tetti").startswith("Tetti: 3 piani."), pg.text_content("#nota-tetti")
    pg.click("#tegola")
    assert pg.get_attribute("#tegola", "aria-pressed") == "true"
    _clic_su_corpo(pg, s, "K2"); _clic_su_corpo(pg, s, "K3")
    attendi(pg, f"{s}.corpi.filter((c) => c.fonteTetto === 'falde').length === 2")
    assert pg.evaluate(f"{s}.edificio") == "E-K"                      # con la tegola il clic non sceglie
    t = pg.evaluate(f"Object.fromEntries({s}.corpi.map((c) => [c.id, [c.fonteTetto, c.tetto, (c.falde || []).length, c.colmo]]))")
    assert t["K2"][:3] == ["falde", "capanna", 2] and abs(t["K2"][3] - (9 + 5 * math.tan(math.radians(22)))) < 0.02, t
    assert t["K3"][0] == "falde" and t["K1"][0] == "piano", t
    nota = pg.text_content("#nota-tetti")
    assert nota.startswith("Tetti: 2 a falde scelti dall'utente (22°), 1 piano."), nota
    assert "tetti a falde scelti dall'utente: 2" in pg.text_content("#legenda-falde")
    assert "tetto a falde scelto dall'utente (22°)" in pg.text_content("#tabella-corpi")
    assert "tetto a falde scelto dall'utente (22°)" in pg.text_content("#tabella-falde")
    assert "22°/32°" not in pg.text_content("main") and "ipotizzat" not in pg.text_content("main")
    righe = " ".join(pg.evaluate(f"{E}.opzioniImmagine().righe"))
    assert "Tetti: 2 a falde scelti dall'utente (22°), 1 piano." in righe and "Tetto a falde scelto dall'utente per 2 corpi" in righe, righe
    rep = pg.evaluate(f"{E}.corpoReport()")
    assert rep["tetti"]["conteggi"]["falde"] == 2 and rep["tetti"]["scelti"][0]["fonte"] == "tetto a falde scelto dall'utente"
    assert {c["id"]: c["fonte_tetto"] for c in rep["corpi"]} == {"K1": "piano", "K2": "falde", "K3": "falde"}
    assert not pg.errori, pg.errori
    ctx.close()


def test_forma_dei_tetti_a_scelta_in_fotovoltaico(browser, base, tmp_path):
    """09/11/2026 c: nelle pagine Edificio e Fotovoltaico «Forma dei tetti» ha due scelte, «Scelti dall'utente»
    (predefinita) e «Tutti piani»; il tetto a falde dato con la tegola (ricordato nel browser) cambia aree FV e
    producibilità; «Tutti piani» li appiattisce tutti, l'inclinazione corretta a mano resta; scelta nel report."""
    lon, lat = _archivio_tetti(tmp_path)
    ctx, pg = pagina(browser)
    ctx.add_init_script("""try { localStorage.setItem('eugenio-tetti-v1', JSON.stringify({ versione: 1,
        tetti: { 'cc-by/er|K1': { i: 30, t: 1 } } })); } catch (e) {}""")
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(lat))
    pg.goto(base + "fv-producibilita.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    _genera(pg, lon, lat, s, E)
    opz = pg.evaluate("[...document.querySelectorAll('#forma-tetti option')].map((o) => o.value)")
    assert opz == ["utente", "piani"], opz
    assert pg.input_value("#forma-tetti") == "utente" and pg.evaluate(f"{s}.formaTetti") == "utente"
    t = pg.evaluate(f"Object.fromEntries({s}.corpi.map((c) => [c.id, [c.fonteTetto, c.inclinazione]]))")
    assert t == {"K1": ["falde", 30], "K2": ["piano", None], "K3": ["piano", None]}, t
    assert "Forma dei tetti: «Scelti dall'utente" in pg.text_content("#nota-tetti")
    # due aree FV: su K1 (falda sud) e su K2; la seconda con l'inclinazione corretta a mano
    def area_su(corpo):
        pg.evaluate("document.getElementById('aggiungi-fv').click()")
        pg.evaluate(f"""(() => {{ const c = {s}.corpi.find((x) => x.id === '{corpo}'), f = (c.falde || []).find((x) => Math.abs(x.orientamento - 180) < 10);
            const p = f ? window.EUGENIO_EDIFICI.centroide(f.ring) : window.EUGENIO_EDIFICI.centroide(c.ring);
            const ll = {s}.proj.indietro(p); {s}.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: {s}.mappa.project(ll) }}); }})()""")
    area_su("K1"); area_su("K2")
    attendi(pg, f"{s}.aree.length === 2")
    a = pg.evaluate(f"{s}.aree.map((x) => [x.corpo, x.inclinazione, Math.abs(x.orientamento - 180) < 5, x.montaggio])")
    assert a == [["K1", 30, True, "aderente"], ["K2", 10, True, "telai"]], a
    pg.fill("#tabella-fv tbody tr:nth-child(2) input >> nth=0", "30")
    pg.dispatch_event("#tabella-fv tbody tr:nth-child(2) input >> nth=0", "change")
    pg.evaluate("document.getElementById('calcola-fv').click()")
    attendi(pg, f"!!{s}.fv", 60000)
    attendi(pg, "/Forma dei tetti: «Scelti dall'utente/.test(document.getElementById('messaggio-fv').textContent)")
    kwh0 = pg.evaluate(f"{s}.fv.find((x) => x.id === 'A1').kwh")
    # «Tutti piani»: K1 piano, l'area su K1 diventa a telai a 10° verso sud; quella corretta a mano resta a 30°
    pg.select_option("#forma-tetti", "piani")
    attendi(pg, f"{s}.formaTetti === 'piani' && !!{s}.fv", 60000)
    t = pg.evaluate(f"{s}.corpi.map((c) => [c.id, c.tetto, (c.falde || []).length])")
    assert all(x[1] == "piano" and x[2] == 0 for x in t), t
    a = pg.evaluate(f"{s}.aree.map((x) => [x.inclinazione, Math.abs(x.orientamento - 180) < 5, x.montaggio])")
    assert a == [[10, True, "telai"], [30, True, "telai"]], a           # K2 è piano: telai, a 30° corretti a mano
    attendi(pg, "/Forma dei tetti: «Tutti piani»/.test(document.getElementById('messaggio-fv').textContent)")
    assert pg.evaluate(f"{s}.fv.find((x) => x.id === 'A1').kwh") != kwh0
    assert pg.text_content("#nota-tetti").startswith("Tetti: 3 piani. Forma dei tetti: «Tutti piani»."), pg.text_content("#nota-tetti")
    pg.select_option("#forma-tetti", "utente")
    attendi(pg, f"{s}.formaTetti === 'utente' && !!{s}.fv && {s}.aree[0].inclinazione === 30", 60000)
    rep = pg.evaluate(f"{E}.corpoReport()")
    assert rep["tetti"]["scelta"].startswith("Scelti dall'utente") and rep["tetti"]["conteggi"]["falde"] == 1
    # telefono: niente scorrimento di lato
    pg.set_viewport_size({"width": 375, "height": 800})
    pg.wait_for_timeout(400)
    largo = pg.evaluate("""[document.documentElement.scrollWidth, window.innerWidth, [...document.querySelectorAll('main *')]
        .filter((e) => e.getBoundingClientRect().right > window.innerWidth + 1 && !e.closest('.tabella-scorre'))
        .slice(0, 2).map((e) => `${e.tagName}#${e.id}.${e.className}:${Math.round(e.getBoundingClientRect().right)} in ${e.parentElement.id}/${e.parentElement.className}/${e.parentElement.parentElement.id}`)]""")
    assert largo[0] <= largo[1] + 1, largo
    assert not pg.errori, pg.errori
    ctx.close()


def _risposta_veneto(lon0=12.246, lat0=45.850):
    """Risposta di /api/edifici/osm in Veneto (08/11/2026): sagome della Regione con l'altezza OSM o stimata, quote dal
    DTM del server, più un edificio OSM senza sagoma regionale."""
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
    def q(i, dx, dy, w, h, **p):
        r = [[lon0 + (dx + a) / kx, lat0 + (dy + b) / ky] for a, b in [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]]
        return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [r]}, "properties": {"id": i, "edificio": i, **p}}
    reg = dict(fonte_sagoma="Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0", regione_sagoma="veneto", uso="residenziale")
    fs = [q("veneto_1", 0, 0, 20, 10, gronda=6.0, altezza=6.0, origine_altezza="osm_piani", licenza="IODL 2.0; altezza ODbL 1.0", quota_terreno=80.0,
            fonte_altezza="OSM building:levels × 3 m (edificio OSM w1 sovrapposto per il 90 %)", **reg),
          q("veneto_2", 40, 0, 12, 12, gronda=9.0, altezza=9.0, origine_altezza="fissa", licenza="IODL 2.0", quota_terreno=82.0, qualita="stima",
            fonte_altezza="stima: 9 m fissi (nessun edificio OSM con l'altezza sovrapposto)", **reg),
          q("veneto_3", 0, 40, 30, 20, gronda=7.0, altezza=7.0, origine_altezza="osm_vicini", licenza="IODL 2.0", quota_terreno=84.0, qualita="stima",
            fonte_altezza="stima: mediana dei vicini con l'altezza da OpenStreetMap (3 entro 200 m: 7 m)", **{**reg, "uso": "capannone"}),
          q("w9", 120, -80, 10, 10, gronda=12.0, altezza=12.0, origine_altezza="osm_piani", licenza="ODbL 1.0", quota_terreno=79.0,
            fonte_sagoma="OSM way 9", fonte_altezza="OSM building:levels × 3 m")]
    return {"type": "FeatureCollection", "features": fs, "corpi": 4, "licenza": "IODL 2.0 (sagome); ODbL 1.0 (altezze e edifici OSM)",
            "sagome": {"regione": "Veneto", "nome": "Regione del Veneto – Edifici del Veneto (feb. 2022)", "licenza": "IODL 2.0",
                       "attribuzione": "Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0",
                       "scheda": "https://geodati.gov.it/resource/id/r_veneto:edifici_veneto", "corpi": 3, "con_altezza_osm": 1, "osm_aggiunti": 1},
            "centro": [lon0, lat0], "raggio": 400, "quote_dtm": 4, "data": "2026-11-08T10:00:00Z"}


def test_sagome_venete_con_altezze_osm_in_modelli3d(browser, base, tmp_path):
    """08/11/2026: in Veneto (fuori dal DBTR) il server dà le sagome della Regione con le altezze OSM: messaggio «Sagome
    dalla Regione del Veneto (IODL 2.0), altezze da OpenStreetMap dove ci sono, altrimenti stimate», marrone come OSM,
    licenze IODL 2.0 + ODbL in pagina, immagine e report, terreno vero (quote dal DTM del server), tetto ipotizzato."""
    _archivio_tetti(tmp_path)
    d = _risposta_veneto()
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(45.85))
    pg.route("**/api/edifici/osm?*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(d)))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.osmAttivo && {s}.archivi.some((a) => a.osm)", 25000)
    lon, lat = 12.246 + 10 / (111320 * math.cos(math.radians(45.85))), 45.850 + 5 / 110574
    pg.evaluate(f"(() => {{ {s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }}); {E}.impostaPunto({lon}, {lat}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.edificio === 'veneto_1'", 25000)
    msg = pg.text_content("#messaggio")
    assert "Sagome dalla Regione del Veneto (IODL 2.0), altezze da OpenStreetMap dove ci sono, altrimenti stimate." in msg, msg
    assert "Regione del Veneto" in pg.text_content("#fonti-osm")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 1", 25000)
    c = pg.evaluate(f"(() => {{ const c = {s}.corpi[0]; return [c.licenza, c.quota, c.fonteTetto, c.ipotesi && c.ipotesi.inclinazione, {E}.livelloFonte(c)]; }})()")
    assert c == ["IODL 2.0; altezza ODbL 1.0", 80, "piano", None, "sagome regionali con altezze OSM o stimate"], c     # 09/11/2026 c: piani
    assert pg.evaluate(f"!!{s}.mappa.getTerrain()")                                  # quote dal DTM: terreno acceso
    assert "Quote dei corpi dal terreno del server" in pg.text_content("#messaggio")
    nota = pg.text_content("#nota-altezze-osm")
    assert "con la sagoma della Regione" in nota and "dalla mediana dei vicini con l'altezza OSM" in nota, nota
    righe = " ".join(pg.evaluate(f"{E}.opzioniImmagine().righe"))
    assert "Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0" in righe and "ODbL" in righe, righe
    rep = pg.evaluate(f"{E}.corpoReport()")
    assert any("IODL 2.0" in f for f in rep["fonti"]) and any("Sagome dalla Regione del Veneto" in n for n in rep["note"])
    assert pg.evaluate(f"(() => {{ const k = {s}.archivi.findIndex((a) => a.osm); return {s}.mappa.getPaintProperty({s}.sorgentiCorpi[k], 'fill-extrusion-color'); }})()") == "#9a6440"
    assert not pg.errori, pg.errori
    ctx.close()


# ------------------------------------------------------------------- 08/11/2026: ricerca col solo comune, Cesena, barra a sinistra
PAGINE_RICERCA = ["modelli3d.html", "ortofoto.html"] + [p for p in PAGINE_3D_TUTTE if p != "modelli3d.html"]
MAPPA_DI = {"ortofoto.html": "window.EUGENIO_ORTOFOTO.stato.mappa"}
CESENA_BUFALINI = (12.2597, 44.1326)          # cerca_luogo.js, PARTENZA: particella foglio 149 n. 387 (DBTR di Cesena)


def _centro(pg, s_mappa):
    return pg.evaluate(f"(() => {{ const c = {s_mappa}.getCenter(); return [c.lng, c.lat, {s_mappa}.getZoom()]; }})()")


@pytest.mark.parametrize("nome", PAGINE_RICERCA)
def test_ricerca_solo_comune_in_ogni_pagina_e_apertura_su_cesena(browser, base, nome):
    """In ogni pagina con «Cerca l'indirizzo» e «Cerca la particella»: esempio «viale Ghirotti 286», «Cesena»; prima apertura
    su Cesena, ospedale Bufalini (zoom ~15,6); il solo comune, in tutti e due i moduli, porta al centro del comune senza
    chiamare il server e senza mai 0,0."""
    s_mappa = MAPPA_DI.get(nome, "window.EUGENIO_EDIFICIO3D.stato.mappa")
    ctx, pg = pagina(browser)
    chiamate = []
    pg.route("**/api/patrimonio", lambda r: (chiamate.append(1), r.fulfill(status=500, body="{}"))[1])
    pg.goto(base + nome)
    webgl(pg)
    attendi(pg, f"!!({s_mappa}) && {s_mappa}.loaded() && !!document.getElementById('cerca-comune')", 30000)
    pg.wait_for_timeout(600)
    lo, la, z = _centro(pg, s_mappa)
    assert abs(lo - CESENA_BUFALINI[0]) < 0.002 and abs(la - CESENA_BUFALINI[1]) < 0.002 and 15 <= z <= 16.5, (nome, lo, la, z)
    assert pg.get_attribute("#cerca-via", "placeholder") == "viale Ghirotti 286" and pg.get_attribute("#cerca-comune", "placeholder") == "Cesena"
    assert pg.locator("#catasto-comune").count() == 0 and pg.locator("#cerca-comune").count() == 1   # un solo Comune (09/11 b)
    pg.fill("#cerca-comune", "Bagno di Romagna")
    pg.click("#cerca-indirizzo")
    attendi(pg, "/centro del comune di Bagno di Romagna/.test(document.getElementById('messaggio-cerca').textContent)")
    pg.wait_for_timeout(1300)
    lo, la, z = _centro(pg, s_mappa)
    assert abs(lo - 11.96) < 0.1 and abs(la - 43.84) < 0.1 and z < 15, (nome, lo, la, z)
    pg.fill("#cerca-comune", "Cesena")
    pg.click("#cerca-particella")
    attendi(pg, "/centro del comune di Cesena/.test(document.getElementById('messaggio-cerca').textContent)")
    pg.wait_for_timeout(1300)
    lo, la, z = _centro(pg, s_mappa)
    assert abs(lo - 12.25) < 0.1 and abs(la - 44.12) < 0.1, (nome, lo, la)
    assert chiamate == [] and "0.00000" not in pg.text_content("#messaggio-cerca")
    assert not pg.errori, (nome, pg.errori)
    ctx.close()


def test_apertura_su_cesena_ha_la_precedenza_giusta(browser, base):
    """Parametri nell'indirizzo e regione scelta vincono su Cesena: Ortofoto con ?lat=&lon=; Modelli 3D con la regione
    Lombardia ricordata dalla piccola mappa."""
    ctx, pg = pagina(browser)
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=17")
    webgl(pg)
    s = "window.EUGENIO_ORTOFOTO.stato.mappa"
    attendi(pg, f"!!({s}) && {s}.loaded()", 30000)
    lo, la, z = _centro(pg, s)
    assert abs(lo - 12.5683) < 1e-3 and abs(la - 44.0594) < 1e-3 and abs(z - 17) < 0.01
    ctx.close()
    ctx, pg = pagina(browser)
    ctx.add_init_script("try { localStorage.setItem('eugenio-regione', '03'); } catch (e) {}")
    pg.goto(base + "modelli3d.html")
    s = "window.EUGENIO_EDIFICIO3D.stato.mappa"
    attendi(pg, f"!!({s}) && {s}.loaded()", 30000)
    pg.wait_for_timeout(1200)
    lo, la, z = _centro(pg, s)
    assert abs(lo - CESENA_BUFALINI[0]) > 0.5 and 44.6 < la < 46.7 and z < 10, (lo, la, z)          # Lombardia
    assert not pg.errori, pg.errori
    ctx.close()


def test_previsioni_ricerca_col_solo_comune(browser, base):
    """Previsioni: il solo nome del comune propone «Comune di Cesena (FC)» senza chiamare il server; con un indirizzo le
    risposte 0,0 non compaiono mai; esempio «viale Ghirotti 286, Cesena»."""
    ctx, pg = pagina(browser)
    geo = []
    risposta = {"risultati": [{"etichetta": "Cesena", "lat": 0, "lon": 0}, {"etichetta": "Viale Giovanni Ghirotti 286, Cesena", "lat": 44.1338, "lon": 12.2597}]}
    pg.route("**/api/geocodifica?*", lambda r: (geo.append(r.request.url), r.fulfill(status=200, content_type="application/json", body=json.dumps(risposta)))[1])
    pg.goto(base + "index.html")
    attendi(pg, "document.querySelectorAll('#mappa path[data-istat]').length > 300", 20000)
    assert "viale Ghirotti 286, Cesena" in pg.get_attribute("#cerca", "placeholder")
    pg.fill("#cerca", "Cesena")
    pg.wait_for_timeout(700)
    assert geo == [] and pg.locator("#risultati button").all_inner_texts() == ["Comune di Cesena (FC)"]
    pg.click("#risultati button")
    assert pg.input_value("#comune") == "040007" and "Cesena" in pg.text_content("#comune-scelto")
    pg.fill("#cerca", "viale Ghirotti 286, Cesena")
    attendi(pg, "document.querySelectorAll('#risultati button').length === 2", 5000)
    voci = pg.locator("#risultati button").all_inner_texts()
    assert voci == ["Comune di Cesena (FC)", "Viale Giovanni Ghirotti 286, Cesena"] and len(geo) == 1, voci
    assert not pg.errori, pg.errori
    ctx.close()


DUE_COLONNE = ["index.html", "legge10.html", "dati.html", "patrimonio.html", "ortofoto.html", "modelli3d.html", "fv-ombre.html",
               "importa-dxf-ifc.html", "aggiungi-dbtr.html", "indicatori.html"]


@pytest.fixture(scope="module")
def browser_con_barre(browser):
    """Chromium con le barre di scorrimento vere (Playwright le nasconde di predefinito con --hide-scrollbars), dalla
    stessa istanza di Playwright del browser del modulo."""
    b = browser.browser_type.launch(ignore_default_args=["--hide-scrollbars"])
    yield b
    b.close()


def test_barra_della_colonna_della_mappa_a_sinistra(browser_con_barre, base):
    """(08/11/2026) In tutte le pagine a due colonne la colonna della mappa, se scorre, ha la barra a sinistra (rtl sul
    contenitore, contenuto ltr); le mappe di Previsioni, Legge 10 e Dati climatici restano alte; a 375 px nessuno
    scorrimento di lato."""
    browser = browser_con_barre
    for nome in DUE_COLONNE:
        ctx, pg = pagina(browser, 1366, 640)
        pg.goto(base + nome)
        pg.wait_for_timeout(1500)
        d = pg.evaluate("""() => { const a = document.querySelector('main.strumento > .mappa-area'), f = a.firstElementChild, cs = getComputedStyle(a);
            const m = a.querySelector('.mappa, .mappa-gl');
            return { dir: cs.direction, oy: cs.overflowY, figlio: getComputedStyle(f).direction, scorre: a.scrollHeight > a.clientHeight + 1,
                     sinistra: a.clientLeft, alto: m ? m.getBoundingClientRect().height : null, testoAllineato: getComputedStyle(a.querySelector('h1') || f).textAlign }; }""")
        assert d["dir"] == "rtl" and d["oy"] == "auto" and d["figlio"] == "ltr", (nome, d)
        assert d["testoAllineato"] in ("start", "left"), (nome, d)
        if d["scorre"]:
            assert d["sinistra"] > 0, (nome, d)           # la barra occupa il bordo sinistro della colonna
        assert not pg.errori, (nome, pg.errori)
        ctx.close()
    # la colonna scorre davvero (finestra bassa): Modelli 3D e Patrimonio, barra a sinistra
    for nome in ("modelli3d.html", "patrimonio.html"):
        ctx, pg = pagina(browser, 1366, 560)
        pg.goto(base + nome)
        pg.wait_for_timeout(1500)
        d = pg.evaluate("() => { const a = document.querySelector('main.strumento > .mappa-area'); return [a.scrollHeight > a.clientHeight + 1, a.clientLeft, a.offsetWidth - a.clientWidth]; }")
        assert d[0] and d[1] > 0 and d[2] >= d[1], (nome, d)
        ctx.close()
    for nome in ("index.html", "legge10.html", "dati.html"):
        ctx, pg = pagina(browser, 1366, 900)
        pg.goto(base + nome)
        pg.wait_for_timeout(1200)
        h = pg.evaluate("document.querySelector('main.strumento > .mappa-area .mappa').getBoundingClientRect().height")
        assert h > 350, (nome, h)
        ctx.close()
    for nome in DUE_COLONNE + ["edificio-clima.html", "edificio-ecobonus.html", "edificio-conto-termico.html"]:
        ctx, pg = pagina(browser, 375, 800)
        pg.goto(base + nome)
        pg.wait_for_timeout(1000)
        assert pg.evaluate("document.documentElement.scrollWidth") <= 376, nome
        assert pg.evaluate("getComputedStyle(document.querySelector('main')).direction") == "ltr", nome
        ctx.close()
