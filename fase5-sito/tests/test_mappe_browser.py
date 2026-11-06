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
     "riquadro": [9.19, 43.73, 12.84, 45.16], "tessere": "/api/ortofoto/rer2023/{z}/{x}/{y}.jpg"},
    {"id": "s2cloudless2016", "nome": "Sentinel-2 cloudless 2016 (10 m)", "licenza": "CC BY 4.0", "citazione": "Sentinel-2 cloudless – EOX (2016)",
     "scheda": "https://cloudless.eox.at/", "stato": "confermata", "copia": True, "nei_report": True, "zoom": [5, 15],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/s2cloudless2016/{z}/{x}/{y}.jpg"},
    {"id": "pcn2012", "nome": "Geoportale Nazionale (solo consultazione)", "licenza": "da verificare", "citazione": "Geoportale Nazionale – AGEA 2012",
     "scheda": "https://gn.mase.gov.it/", "stato": "da confermare", "copia": False, "nei_report": False, "zoom": [12, 19],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/pcn2012/{z}/{x}/{y}.jpg"}]}


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


def test_altre_pagine_3d_in_un_tempo(browser, base):
    ctx, pg = pagina(browser)
    pg.goto(base + "fv-producibilita.html")
    webgl(pg)
    s = "window.EUGENIO_EDIFICIO3D.stato"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.edificio === 'E-DEMO'", 25000)
    assert pg.evaluate(f"{s}.in3d") is True
    assert pg.locator("#genera-3d").count() == 0
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
    """Chrome/Edge: la finestra del sistema si apre nel clic; «salvata» solo dopo la scrittura; «Annulla» = annullato."""
    ctx, pg = pagina(browser, finestra=True)
    ctx.add_init_script("""window.__scritti = []; window.__annulla = false;
      window.showSaveFilePicker = async (o) => { if (window.__annulla) { const e = new Error('annullato'); e.name = 'AbortError'; throw e; }
        return { name: o.suggestedName, createWritable: async () => { const parti = [];
          return { write: async (b) => parti.push(new Uint8Array(await b.arrayBuffer())), close: async () => window.__scritti.push({ nome: o.suggestedName, byte: parti.reduce((s, p) => s + p.length, 0), testa: Array.from(parti[0].slice(0, 4)) }) }; } }; };""")
    pg.goto(base + "ortofoto.html?lat=44.0594&lon=12.5683&z=16")
    webgl(pg)
    attendi(pg, "window.EUGENIO_ORTOFOTO && window.EUGENIO_ORTOFOTO.stato.scelta && document.querySelector('#scarica-ortofoto button')")
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
    pg.click("#cerca-indirizzo button[type=submit]")
    attendi(pg, f"/ANNCSU/.test(document.getElementById('messaggio-cerca').textContent) && Math.abs({st}.mappa.getCenter().lat - 44.0601) < 1e-4 && !{st}.mappa.isMoving()")
    assert pg.evaluate(f"{st}.mappa.getZoom()") >= 17.9
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
