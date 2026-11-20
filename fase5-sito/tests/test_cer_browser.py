"""Fotovoltaico › «Comunità energetiche» (edificio-cer.html, cer_sedi.js; 20/11/2026): aree convenzionali del GSE dal vivo.

Sui file: pagina ancora «in lavorazione» nel menu, script nell'ordine giusto, indirizzo del servizio del GSE solo in rete.js,
niente localStorage né dati di mercato in cer_sedi.js.
In Chromium (si salta se Playwright o Chromium non ci sono), senza rete, con il servizio del GSE e /api/rete/… simulati:
  - sede → COD_AC con distance=50 m e senza geometria, campo «Cabina» precompilato (modificabile) con la nota del GSE;
    sede sul confine (due aree, seconda richiesta senza margine) e sede in mare (nessuna area), con l'avviso;
  - menu delle cabine di e-distribuzione del comune (nome, COD_AC, saturazione); comune di un altro distributore con il
    rimando alla mappa del GSE; comune con trasformatori di e-distribuzione ma servitoed = 0: «servito in parte», mai
    «altro distributore»;
  - elenco di sedi: al massimo 4 richieste al GSE alla volta, stesse coordinate chieste una volta sola;
  - strato «Aree convenzionali (GSE)»: spento all'apertura (nessuna richiesta), messaggio sotto lo zoom 10, una richiesta
    per il riquadro dopo lo spostamento, etichette COD_AC, riquadro al clic (codice, gestore, data di consegna, link),
    attribuzione fissa; spento nell'immagine e riacceso dopo;
  - file scaricati: solo il codice con la nota «area convenzionale proposta dalla mappa del GSE; verifica ufficiale: GSE»;
  - energia condivisa ricalcolata con la cabina dell'elenco; telefono senza scorrimento orizzontale; nessun errore JS.
"""
from __future__ import annotations

import functools
import json
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

GSE = "https://services-eu1.arcgis.com/sawHMGY9o8rHlY2j/arcgis/rest/services/AC_Comuni_2025/FeatureServer/0"
NOTA_FILE = "area convenzionale proposta dalla mappa del GSE; verifica ufficiale: GSE"
S = "window.EUGENIO_CER_SEDI.st"


# ---------------------------------------------------------------------------------------------- file
def test_pagina_in_lavorazione_e_script():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert 'href="edificio-cer.html"' not in t and t.count('<span class="voce-gme voce-corso" data-pagina="edificio-cer.html"') == 2
    s = (SITO / "edificio-cer.html").read_text(encoding="utf-8")
    assert re.search(r'<script src="rete\.js\?v=\w+"></script>\s*<script src="cer_sedi\.js\?v=\w+"></script>\s*<script src="analisi_pubbliche\.js\?v=', s)
    assert 'id="strato-aree-gse" type="checkbox">' in s and "checked" not in re.search(r'<input id="strato-aree-gse"[^>]*>', s).group(0)
    piatto = re.sub(r"\s+", " ", s)
    assert "CC BY-NC-SA 3.0 IT" in piatto and "mappa-interattiva-delle-cabine-primarie" in s and NOTA_FILE in piatto
    assert C.main(["--controlla"]) == 0
    js = (SITO / "cer_sedi.js").read_text(encoding="utf-8")
    codice = "\n".join(r for r in js.splitlines() if not r.lstrip().startswith("//"))
    assert "arcgis.com" not in js and "localStorage" not in codice and "sessionStorage" not in codice
    assert not re.search(r"(?i)\b(pun|psv|igi|ttf)\b", js)
    r = (SITO / "rete.js").read_text(encoding="utf-8")
    assert "CONFINE_M: 50" in r and "ZOOM_MIN: 10" in r and "INSIEME: 4" in r and NOTA_FILE in r


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
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def _aspetta(pg, js, ms=15000):
    pg.wait_for_function(js, timeout=ms)


def _area(cod, rag="e-distribuzione S.p.A.", conseg="30092025", geom=None):
    return {"type": "Feature", "geometry": geom, "properties": {"COD_AC": cod, "RAG_SOC": rag, "COD_CONSEG": conseg}}


BOLOGNA = {"type": "Polygon", "coordinates": [[[11.30, 44.47], [11.38, 44.47], [11.38, 44.52], [11.30, 44.52], [11.30, 44.47]]]}
COMUNI = {
    # Bologna: e-distribuzione lo segna come non suo (concessionario false) ma ci sono trasformatori: «servito in parte»
    "037006": {"istat": "037006", "nome": "Bologna", "concessionario": False, "servito_in_parte": False, "cabine": [
        {"cod_cp_ed": "DV001", "nome_cp_ed": "BOLOGNA NORD", "cod_ac": "AC001E00693", "gestore": "e-distribuzione", "livello": "ARANCIONE",
         "trasf": {"VERDE": 1, "GIALLO": 0, "ARANCIONE": 1, "ROSSO": 0}, "lat": 44.51, "lon": 11.35,
         "trasformatori_del_comune": [{"cod_trasf": "01", "livello": "ARANCIONE", "montanti": []}]},
        {"cod_cp_ed": "DV002", "nome_cp_ed": "BOLOGNA SUD", "cod_ac": None, "gestore": "e-distribuzione", "livello": None,
         "trasf": {"VERDE": 0, "GIALLO": 0, "ARANCIONE": 0, "ROSSO": 0}, "lat": None, "lon": None, "trasformatori_del_comune": []}]},
    # Forlì (finto): servito da un altro distributore, nessuna cabina di e-distribuzione
    "040012": {"istat": "040012", "nome": "Forlì", "concessionario": False, "servito_in_parte": False, "cabine": []},
}


def _pagina(browser, larghezza=1366, altezza=900):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errori, pg.chiamate, pg.api = [], [], []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))

    def api(r):
        u = urlparse(r.request.url)
        pg.api.append(u.path)
        m = re.fullmatch(r"/api/rete/cabine/comune/(\d{6})", u.path)
        if m and m.group(1) in COMUNI:
            return r.fulfill(status=200, content_type="application/json", body=json.dumps(COMUNI[m.group(1)]))
        return r.fulfill(status=404, content_type="application/json", body="{}")
    pg.route("**/api/**", api)

    def gse(r):
        q = {k: v[0] for k, v in parse_qs(urlparse(r.request.url).query).items()}
        pg.chiamate.append(q)
        fs = []
        if q.get("geometryType") == "esriGeometryPoint":
            lon = float(q["geometry"].split(",")[0])
            if abs(lon - 11.3426) < 1e-6:
                fs = [_area("AC001E00693")]
            elif abs(lon - 12.0407) < 1e-6:                  # sul confine: due aree entro 50 m, il punto è nella prima
                fs = [_area("AC001E00800"), _area("AC001E00801", rag="Altro Distributore")] if "distance" in q else [_area("AC001E00800")]
        elif q.get("geometryType") == "esriGeometryEnvelope":
            fs = [_area("AC001E00693", geom=BOLOGNA)]
        r.fulfill(status=200, content_type="application/geo+json", headers={"Access-Control-Allow-Origin": "*"},
                  body=json.dumps({"type": "FeatureCollection", "features": fs}))
    pg.route(GSE + "/query**", gse)
    return ctx, pg


def _sede(pg, nome, lat, lon):
    pg.fill("#sede-nome", nome); pg.fill("#sede-lat", lat); pg.fill("#sede-lon", lon)
    pg.click("#sede-aggiungi")


def _riga(pg, k):
    return pg.locator(f"#tabella-sedi-cer tr[data-k='{k}']")


def test_sedi_aree_del_gse_e_cabine_del_comune(base, browser, tmp_path):
    ctx, pg = _pagina(browser)
    corpi = []
    pg.route("**/api/report?formato=*", lambda r: (corpi.append((r.request.url, r.request.post_data)),
             r.fulfill(status=200, headers={"Content-Disposition": 'attachment; filename="cer.xlsx"'}, body=b"PK")))
    pg.goto(base + "edificio-cer.html")
    _aspetta(pg, f"() => window.EUGENIO_CER_SEDI && {S}.mappa && {S}.mappa.loaded()")
    assert pg.chiamate == []                                  # nessuna richiesta al GSE senza un'azione dell'utente
    assert not pg.is_checked("#strato-aree-gse") and pg.locator("#attribuzione-aree-gse").is_hidden()
    # caso normale: COD_AC precompilato, richiesta con 50 m di margine e senza geometria
    _sede(pg, "Scuola A", "44,4949", "11,3426")
    _aspetta(pg, f"() => {S}.sedi[0].gse && {S}.sedi[0].gse.stato === 'ok' && document.querySelector('#tabella-sedi-cer tr[data-k=\"1\"] select')")
    q = pg.chiamate[0]
    assert q["geometry"] == "11.3426,44.4949" and q["geometryType"] == "esriGeometryPoint" and q["inSR"] == "4326"
    assert q["distance"] == "50" and q["units"] == "esriSRUnit_Meter" and q["returnGeometry"] == "false" and q["outFields"] == "COD_AC,RAG_SOC,COD_CONSEG"
    assert len(pg.chiamate) == 1                              # una sola area: nessuna seconda richiesta
    r1 = _riga(pg, 1)
    assert r1.locator("input").input_value() == "AC001E00693"
    testo = r1.inner_text()
    assert "proposta dalla mappa del GSE dalle coordinate; in caso di dubbio vale la ricerca per POD sulla mappa del GSE o nell'Area Clienti" in testo
    assert "Bologna" in testo
    # regola: trasformatori di e-distribuzione → «servito in parte», mai «altro distributore»; menu con nome, COD_AC, saturazione
    assert "servito in parte da un altro distributore" in testo and "altro distributore (non e-distribuzione)" not in testo
    opz = r1.locator("select option").all_inner_texts()
    assert opz[1] == "BOLOGNA NORD · AC001E00693 · saturazione: arancione"
    assert opz[2] == "BOLOGNA SUD · COD_AC non abbinato · saturazione: nessun dato"
    # campo modificabile; scelta dal menu
    r1.locator("input").fill("CP-MIA"); r1.locator("input").dispatch_event("change")
    assert pg.evaluate(f"{S}.sedi[0].cabina") == "CP-MIA" and "scritta a mano" in _riga(pg, 1).inner_text()
    _riga(pg, 1).locator("select").select_option("1")
    assert pg.evaluate(f"[{S}.sedi[0].cabina, {S}.sedi[0].origine]") == ["DV002", "menu"]
    _riga(pg, 1).locator("select").select_option("0")
    assert _riga(pg, 1).locator("input").input_value() == "AC001E00693"
    # confine: due aree entro 50 m → seconda richiesta senza margine, proposta quella che contiene il punto, avviso con tutte e due
    _sede(pg, "Scuola B", "44,2227", "12,0407")
    _aspetta(pg, f"() => {S}.sedi[1].gse && {S}.sedi[1].gse.stato === 'ok' && /altro distributore/.test(document.querySelector('#tabella-sedi-cer tr[data-k=\"2\"]').textContent)")
    seconda = [c for c in pg.chiamate if c.get("geometry") == "12.0407,44.2227"]
    assert len(seconda) == 2 and "distance" in seconda[0] and "distance" not in seconda[1]
    r2 = _riga(pg, 2)
    assert r2.locator("input").input_value() == "AC001E00800"
    t2 = r2.inner_text()
    assert "a meno di 50 m dal confine tra le aree AC001E00800" in t2 and "AC001E00801 (Altro Distributore)" in t2
    # Forlì: comune di un altro distributore → avviso e rimando alla mappa del GSE, nessun menu
    assert "Comune servito da un altro distributore (non e-distribuzione)" in t2 and r2.locator("select").count() == 0
    assert r2.locator("a[href*='gse.it']").count() == 1
    # mare: nessuna area → avviso, campo vuoto
    _sede(pg, "Boa", "44,2", "12,6")
    _aspetta(pg, f"() => {S}.sedi[2].gse && {S}.sedi[2].gse.stato === 'ok'")
    r3 = _riga(pg, 3)
    assert r3.locator("input").input_value() == "" and "Nessuna area convenzionale del GSE in questo punto (isola minore" in r3.inner_text()
    # le stesse coordinate non si chiedono di nuovo (memoria della pagina)
    n = len(pg.chiamate)
    _sede(pg, "Scuola A bis", "44.4949", "11.3426")
    _aspetta(pg, f"() => {S}.sedi[3].gse && {S}.sedi[3].gse.stato === 'ok'")
    assert len(pg.chiamate) == n and _riga(pg, 4).locator("input").input_value() == "AC001E00693"
    # niente in localStorage
    assert pg.evaluate("Object.keys(localStorage).filter((k) => /gse|cer|sedi|AC0/i.test(k) || /AC0/.test(localStorage.getItem(k) || ''))") == []
    # energia condivisa con la cabina dell'elenco (sede «Scuola A» dell'esempio)
    pg.click("#cer-esempio")
    _aspetta(pg, "() => !document.getElementById('passo-cer-risultati').hidden")
    assert "AC001E00693" in pg.inner_text("#risultati-cer") and "cabina dall'elenco delle sedi per 1 sede" in pg.inner_text("#messaggio-cer")
    _riga(pg, 1).locator("input").fill("CP-ESEMPIO-1"); _riga(pg, 1).locator("input").dispatch_event("change")
    _aspetta(pg, "() => !/AC001E00693/.test(document.getElementById('risultati-cer').textContent)")
    # file: solo i codici, con la nota
    with pg.expect_download() as d:
        pg.click("#scarica-cer button[data-formato=csv]")
    f = tmp_path / "cer.csv"
    d.value.save_as(f)
    t = f.read_text(encoding="utf-8-sig")
    assert t.splitlines()[0].startswith("Fonte: EuGEnio") and "AC001E00800" in t and NOTA_FILE in t and "Energia condivisa per cabina primaria" in t
    assert "Polygon" not in t and "rings" not in t and "coordinates" not in t
    pg.click("#scarica-cer button[data-formato=ods]")
    _aspetta(pg, "() => /Download avviato/.test(document.getElementById('messaggio-scarica-cer').textContent)")
    url, corpo = corpi[-1]
    assert url.endswith("formato=ods") and NOTA_FILE in corpo and "Polygon" not in corpo
    assert pg.locator("#scarica-cer button").all_inner_texts() == ["CSV", "Excel", "ODS", "PDF"]
    assert not pg.errori, pg.errori
    ctx.close()


def test_strato_aree_convenzionali(base, browser):
    ctx, pg = _pagina(browser)
    pg.goto(base + "edificio-cer.html")
    _aspetta(pg, f"() => window.EUGENIO_CER_SEDI && {S}.mappa && {S}.mappa.loaded()")
    pg.check("#strato-aree-gse")
    _aspetta(pg, "() => /da zoom 10/.test(document.getElementById('messaggio-aree-gse').textContent)")
    pg.wait_for_timeout(700)
    assert pg.chiamate == []                                  # sotto lo zoom 10 nessuna richiesta
    assert pg.locator("#attribuzione-aree-gse").is_visible()
    assert "Aree convenzionali: © GSE S.p.A. – mappa interattiva delle cabine primarie (CC BY-NC-SA 3.0 IT)" in pg.inner_text("#attribuzione-aree-gse")
    pg.evaluate(f"{S}.mappa.jumpTo({{ center: [11.34, 44.495], zoom: 12 }})")
    _aspetta(pg, f"() => {S}.aree && {S}.aree.features.length === 1")
    env = [c for c in pg.chiamate if c.get("geometryType") == "esriGeometryEnvelope"]
    assert len(env) == 1 and env[0]["returnGeometry"] == "true" and env[0]["f"] == "geojson" and env[0]["outSR"] == "4326"
    assert 0 < float(env[0]["maxAllowableOffset"]) < 0.001 and "where" not in env[0]
    assert pg.locator(".etichetta-ac", has_text="AC001E00693").count() == 1
    assert "1 area convenzionale nella zona, letta ora dal GSE" in pg.inner_text("#messaggio-aree-gse")
    # piccolo spostamento: stesso riquadro della griglia, nessuna richiesta nuova
    pg.evaluate(f"{S}.mappa.jumpTo({{ center: [11.3405, 44.4952], zoom: 12 }})")
    pg.wait_for_timeout(800)
    assert len([c for c in pg.chiamate if c.get("geometryType") == "esriGeometryEnvelope"]) == 1
    # clic sull'area: codice, gestore, data di consegna, link alla mappa del GSE
    _aspetta(pg, f"() => {S}.mappa.queryRenderedFeatures({S}.mappa.project([11.34, 44.495]), {{ layers: ['cer-aree-fondo'] }}).length > 0")
    xy = pg.evaluate(f"(() => {{ const p = {S}.mappa.project([11.34, 44.495]), r = {S}.mappa.getCanvas().getBoundingClientRect(); return [r.left + p.x, r.top + p.y]; }})()")
    pg.mouse.click(xy[0], xy[1])
    _aspetta(pg, "() => document.querySelector('.popup-ac')")
    p = pg.locator(".popup-ac")
    assert "Area convenzionale AC001E00693" in p.inner_text() and "Gestore: e-distribuzione S.p.A." in p.inner_text()
    assert "Data di consegna: 30/09/2025" in p.inner_text() and p.locator("a[href*='mappa-interattiva-delle-cabine-primarie']").count() == 1
    # immagine: strato spento durante la copia, riacceso dopo
    vis = f"{S}.mappa.getLayoutProperty('cer-aree-linea', 'visibility')"
    assert pg.evaluate(vis) == "visible"
    pg.evaluate("window._o = window.EUGENIO_CER_SEDI.opzioniImmagine()")
    assert pg.evaluate(vis) == "none" and pg.locator(".etichetta-ac").first.is_hidden()
    assert "non entrano nell'immagine" in pg.evaluate("window._o.righe.join(' ')")
    pg.evaluate("window._o.dopo()")
    assert pg.evaluate(vis) == "visible" and pg.locator(".etichetta-ac").first.is_visible()
    # zoom sotto 10: dati tolti, messaggio; casella spenta: attribuzione nascosta, strato spento
    pg.evaluate(f"{S}.mappa.jumpTo({{ zoom: 8 }})")
    _aspetta(pg, f"() => !{S}.aree && /da zoom 10/.test(document.getElementById('messaggio-aree-gse').textContent)")
    pg.uncheck("#strato-aree-gse")
    assert pg.locator("#attribuzione-aree-gse").is_hidden() and pg.evaluate(vis) == "none"
    assert not pg.errori, pg.errori
    ctx.close()


def test_elenco_di_sedi_quattro_richieste_alla_volta(base, browser, tmp_path):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    # servizio del GSE simulato nel browser, con risposte lente, per misurare le richieste contemporanee
    ctx.add_init_script("""(() => {
      const vero = window.fetch; window._gse = { ora: 0, max: 0, n: 0 };
      window.fetch = async (u, o) => {
        if (!String(u).includes('arcgis.com')) return vero(u, o);
        const g = window._gse; g.n++; g.ora++; g.max = Math.max(g.max, g.ora);
        await new Promise((ok) => setTimeout(ok, 150)); g.ora--;
        const f = { type: 'Feature', geometry: null, properties: { COD_AC: 'AC001E00693', RAG_SOC: 'e-distribuzione S.p.A.', COD_CONSEG: '30092025' } };
        return new Response(JSON.stringify({ type: 'FeatureCollection', features: [f] }), { status: 200, headers: { 'Content-Type': 'application/geo+json' } });
      };
    })()""")
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
    pg.goto(base + "edificio-cer.html")
    _aspetta(pg, "() => window.EUGENIO_CER_SEDI")
    f = tmp_path / "sedi.csv"
    righe = ["sede;lat;lon;cabina"] + [f"S{i};44,{4900 + i * 7};11,{3400 + i * 5};" for i in range(10)] + ["Con cabina;44,5;11,35;CP-X", "Senza nulla;;;"]
    f.write_text("\n".join(righe), encoding="utf-8")
    pg.set_input_files("#sedi-file", str(f))
    _aspetta(pg, f"() => {S}.sedi.length === 11 && {S}.sedi.every((s) => s.gse && s.gse.stato === 'ok')", 20000)
    g = pg.evaluate("window._gse")
    assert g["n"] == 11 and g["max"] == 4
    assert "11 sedi aggiunte" in pg.inner_text("#messaggio-sedi") and "1 righe senza coordinate" in pg.inner_text("#messaggio-sedi")
    # la cabina del file non viene sostituita dalla proposta del GSE
    assert pg.evaluate(f"{S}.sedi[10].cabina") == "CP-X" and "dal file delle sedi" in _riga(pg, 11).inner_text()
    assert pg.evaluate(f"{S}.sedi[0].cabina") == "AC001E00693"
    assert not errori, errori
    ctx.close()


def test_prova_e_telefono(base, browser):
    ctx, pg = _pagina(browser, 375, 740)
    pg.goto(base + "edificio-cer.html?prova=1")
    _aspetta(pg, f"() => window.EUGENIO_CER_SEDI && {S}.mappa")
    assert pg.locator(".rete-prova").is_visible()
    _sede(pg, "Scuola A", "44,4949", "11,3426")
    _aspetta(pg, "() => document.querySelector('#tabella-sedi-cer select')")
    assert pg.chiamate == [] and re.fullmatch(r"AC008E\d{5}", _riga(pg, 1).locator("input").input_value())
    assert "(sintetica)" in _riga(pg, 1).inner_text()
    pg.wait_for_timeout(500)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert not pg.errori, pg.errori
    ctx.close()
