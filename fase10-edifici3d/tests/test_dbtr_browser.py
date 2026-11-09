"""«Aggiungi DBTR» nel browser (Chromium headless, Playwright; 07/11/2026).

Sito vero servito in locale, API finte. Si controlla:
- lettura nel Web Worker di un GeoPackage e di uno Shapefile sintetici (dbtr_sintetici.py), parità con il Python;
- nessuna richiesta al server con il file finché il consenso non è spuntato; poi caricamento a pezzi con impronta e consenso,
  senza dati personali;
- apertura in Modelli 3D senza server: archivio «locale» dalla memoria del browser, zona coperta per la sessione;
- pagina interna con una coda finta: tabella, anteprima, Approva con l'intestazione X-EuGEnio-Interno.
Si salta se Playwright o Chromium non ci sono."""
from __future__ import annotations

import base64
import functools
import hashlib
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
pytest.importorskip("pyogrio")
QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent)); sys.path.insert(0, str(QUI))
import dbtr_sintetici as DS  # noqa: E402
import test_dbtr_parita as TP  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==")
FONTI = {"fonti": [{"id": "finta", "nome": "Ortofoto finta", "licenza": "CC BY 4.0", "citazione": "Prova", "scheda": "#",
                    "stato": "confermata", "copia": True, "zoom": [5, 20], "riquadro": [6, 35, 19, 48],
                    "tessere": "/api/ortofoto/finta/{z}/{x}/{y}.png"}]}


class Silenzioso(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def sito():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silenzioso, directory=str(SITO)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
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


class Pagina:
    def __init__(self, browser, sito):
        self.ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
        self.richieste, self.errori, self.dbtr = [], [], []
        self.pg = self.ctx.new_page()
        self.pg.on("request", lambda r: self.richieste.append((r.method, r.url, r.post_data_buffer)))
        self.pg.on("pageerror", lambda e: self.errori.append(str(e)))
        self.pg.on("dialog", lambda d: d.accept())
        self.ctx.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI)))
        self.ctx.route("**/api/ortofoto/finta/**", lambda r: r.fulfill(status=200, content_type="image/png", body=PNG))
        self.ctx.route("**/api/protezione", lambda r: r.fulfill(status=200, content_type="application/json",
                                                                body=json.dumps({"turnstile": None, "rotte": []})))
        self.ctx.route("**/api/dbtr/**", self._dbtr)
        self.ctx.route("**/edifici3d/**", lambda r: r.fulfill(status=404, body="no"))
        self.ctx.route("**/api/**", lambda r: r.fallback() if any(x in r.request.url for x in ("/api/ortofoto/", "/api/dbtr/", "/api/protezione"))
                       else r.fulfill(status=404, content_type="application/json", body="{}"))
        self.sito = sito

    def _dbtr(self, route):
        rq = route.request
        self.dbtr.append((rq.method, rq.url, dict(rq.headers), rq.post_data_buffer))
        if rq.url.endswith("/inizia"):
            d = json.loads(rq.post_data)
            body = {"id": "a" * 32, "gettone": "g" * 32, "pezzo_byte": 4096, "pezzi": -(-d["dimensione"] // 4096)}
        elif "/pezzo/" in rq.url:
            body = {"ricevuti": 1}
        elif rq.url.endswith("/fine"):
            body = {"stato": "ricevuto", "davanti": 0, "messaggio": "File ricevuto: è in coda per la preparazione sul server."}
        else:
            body = {"stato": "ricevuto", "messaggio": "File ricevuto: è in coda per la preparazione sul server."}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    def apri(self):
        self.pg.goto(f"{self.sito}/aggiungi-dbtr.html")
        self.pg.wait_for_function("() => document.querySelectorAll('#comune option').length > 100", timeout=30000)

    def carica(self, percorsi, regione="er"):
        self.pg.select_option("#regione", regione)
        self.pg.evaluate("() => { document.getElementById('messaggio').textContent = ''; }")
        self.pg.set_input_files("#file-dbtr", [str(p) for p in percorsi])
        self.pg.wait_for_function("() => /File letto|non letto/.test(document.getElementById('messaggio').textContent)", timeout=90000)
        return self.pg.inner_text("#messaggio")

    def chiudi(self):
        self.ctx.close()


@pytest.fixture()
def pagina(browser, sito):
    p = Pagina(browser, sito)
    yield p
    p.chiudi()


def test_lettura_e_parita_nel_browser_senza_invio(pagina, tmp_path):
    gp = DS.gpkg_er(tmp_path / "estraz_procons.gpkg")
    sh = DS.shp_er(tmp_path / "shp")
    pagina.apri()
    t = pagina.carica([gp])
    assert "File letto" in t, t
    js = pagina.pg.evaluate("window.EUGENIO_AGGIUNGI_DBTR.stato.features")
    assert TP.confronta(TP.py_er(gp), js) == 0
    assert "Convenzione" in pagina.pg.inner_text("#tabella-sintesi")
    t = pagina.carica(sorted(sh.iterdir()))                                     # parti dello Shapefile scelte insieme
    assert "File letto" in t, t
    assert TP.confronta(TP.py_er(sh), pagina.pg.evaluate("window.EUGENIO_AGGIUNGI_DBTR.stato.features")) == 0
    # nessun invio: solo GET, nessuna rotta /api/dbtr/, nessun nome di file negli indirizzi
    for metodo, url, corpo in pagina.richieste:
        assert metodo == "GET" and not corpo, (metodo, url)
        assert "estraz_procons" not in url and "/api/dbtr/" not in url
    assert pagina.pg.is_disabled("#proponi")                                    # consenso non spuntato di default
    assert not pagina.pg.is_checked("#consenso")
    assert not pagina.errori, pagina.errori


def test_proposta_con_consenso_a_pezzi(pagina, tmp_path):
    gp = DS.gpkg_er(tmp_path / "estraz_procons.gpkg")
    pagina.apri()
    assert "File letto" in pagina.carica([gp])
    pagina.pg.select_option("#comune", "099014")                                # Rimini
    assert pagina.pg.is_disabled("#proponi")
    pagina.pg.check("#consenso")
    pagina.pg.click("#proponi")
    pagina.pg.wait_for_function("() => /Grazie|non riuscito/.test(document.getElementById('messaggio-proposta').textContent)", timeout=60000)
    assert "Grazie" in pagina.pg.inner_text("#messaggio-proposta")
    ini = next(x for x in pagina.dbtr if x[1].endswith("/inizia"))
    corpo = json.loads(ini[3])
    dati = gp.read_bytes()
    assert corpo == {"regione": "er", "comune": "Rimini", "istat": "099014", "intero": True, "formato": "gpkg",
                     "dimensione": len(dati), "consenso": True, "impronta": hashlib.sha256(dati).hexdigest()}
    pezzi = [x for x in pagina.dbtr if "/pezzo/" in x[1]]
    assert len(pezzi) == -(-len(dati) // 4096) and b"".join(x[3] for x in pezzi) == dati
    assert all(x[2].get("x-eugenio-dbtr") == "g" * 32 for x in pezzi)
    assert any(x[1].endswith("/fine") for x in pagina.dbtr)
    assert not pagina.pg.is_checked("#consenso")                                 # dopo l'invio il consenso torna spento


def test_apertura_in_modelli_3d_senza_server(pagina, tmp_path):
    gp = DS.gpkg_er(tmp_path / "estraz_procons.gpkg")
    pagina.apri()
    assert "File letto" in pagina.carica([gp])
    pagina.pg.select_option("#comune", "099014")
    pagina.pg.uncheck("#intero")                                                 # solo una parte: zona = riquadro dei corpi
    pagina.pg.click("#apri-3d")
    pagina.pg.wait_for_url("**/modelli3d.html?dbtr=locale**", timeout=30000)
    pagina.pg.wait_for_function("() => window.EUGENIO_EDIFICIO3D && window.EUGENIO_EDIFICIO3D.stato.locale && /tuo file/.test(document.getElementById('messaggio').textContent)", timeout=30000)
    s = pagina.pg.evaluate("""async () => { const E = window.EUGENIO_EDIFICIO3D, st = E.stato;
        const f = st.locale.features[0], r = f.geometry.coordinates[0], lon = (r[0][0] + r[2][0]) / 2, lat = (r[0][1] + r[2][1]) / 2;
        return { n: st.locale.features.length, istat: st.locale.istat, attr: st.locale.indice.attribuzione,
          dentro: await E.coperto(lon, lat), fuori: await E.coperto(lon + 0.05, lat), messaggio: document.getElementById('messaggio').textContent,
          togli: !!document.getElementById('togli-locale') }; }""")
    assert s["n"] == 5 and s["istat"] is None and "letto solo in questo browser" in s["attr"]
    assert s["dentro"] is True and s["fuori"] is False and "tuo file" in s["messaggio"] and s["togli"]
    # scelta di un edificio del file e «Genera il 3D»
    ok = pagina.pg.evaluate("""async () => { const E = window.EUGENIO_EDIFICIO3D, f = E.stato.locale.features.find((x) => x.properties.id === 'U2');
        const r = f.geometry.coordinates[0]; return E.scegli('E2', (r[0][0] + r[1][0]) / 2, (r[0][1] + r[2][1]) / 2 + 0.00001); }""")
    assert ok
    corpi = pagina.pg.evaluate("window.EUGENIO_EDIFICIO3D.stato.corpi.map((c) => [c.id, c.gronda, c.colmo, c.buchi.length])")
    assert sorted(corpi) == [["U2", 12, None, 1], ["U3", 12.15, None, 0]]     # 09/11/2026 c: tetti tutti piani in partenza
    assert not [m for m in pagina.richieste if m[0] != "GET"]
    assert not pagina.errori, pagina.errori
    # stessa sessione, la pagina si riapre senza parametro: il file vale ancora; «Togli» lo toglie
    pagina.pg.goto(f"{pagina.sito}/modelli3d.html")
    pagina.pg.wait_for_function("() => window.EUGENIO_EDIFICIO3D && window.EUGENIO_EDIFICIO3D.stato.mappa", timeout=30000)
    assert pagina.pg.evaluate("!!window.EUGENIO_EDIFICIO3D.stato.locale")
    pagina.pg.click("#togli-locale")
    pagina.pg.wait_for_function("() => window.EUGENIO_EDIFICIO3D && window.EUGENIO_EDIFICIO3D.stato.mappa && !window.EUGENIO_EDIFICIO3D.stato.locale", timeout=30000)


def test_pagina_interna_con_coda_finta(browser, sito):
    ctx = browser.new_context(viewport={"width": 1300, "height": 1000})
    pg = ctx.new_page()
    errori, decisioni = [], []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    voce = {"id": "b" * 32, "stato": "in attesa di approvazione", "creata": "2026-11-07T10:00:00+0100", "regione": "er",
            "comune": "Lugo", "istat": "039012", "intero": True, "formato": "zip", "dimensione": 26_000_000, "anteprima": True,
            "controlli": {"sorgente": {"nome": "estraz_procons.gpkg"}, "crs": "EPSG:7791", "riquadro": [11.85, 44.36, 11.98, 44.47],
                          "dentro_regione": True, "metadati": {"file": 1, "regione_citata": True, "licenze": ["CC BY 3.0"]},
                          "problemi": [], "avvisi": [], "dati_personali": []},
            "esito": {"corpi": 19906, "edifici": 17000, "letti": 20080, "scartati": 174, "convenzione": "quote",
                      "gronda_m": {"mediana": 6.0, "p95": 12.0, "max": 41.0, "sotto_2m": 0, "oltre_60m": 0}, "riquadro": [11.85, 44.36, 11.98, 44.47],
                      "a_capanna": 0, "con_cortile": 50, "con_foglio_numero": 15000, "con_destinazione": 16000, "percorso": "cc-by/er/lugo/",
                      "sostituisce": True, "anomalie": [], "sospetti": [{"id": "x", "area": 8.3, "gronda": 114, "foglio": "54", "numero": "216"}]}}
    ant = {"type": "FeatureCollection", "totale": 1, "passo": 1, "features": [{"type": "Feature", "properties": {"g": 6, "c": None, "e": "E"},
           "geometry": {"type": "Polygon", "coordinates": [[[11.91, 44.41], [11.911, 44.41], [11.911, 44.411], [11.91, 44.41]]]}}]}
    def coda(r):
        r.fulfill(status=200, content_type="application/json", body=json.dumps({"coda": [voce], "storico": [], "utente": "paolo@esempio.it",
                  "attiva": True, "limiti": {"max_mb": 300, "al_giorno_per_ip": 3, "coda_max": 20}, "occupato_mb": 26}))
    def approva(r):
        decisioni.append((r.request.method, r.request.headers.get("x-eugenio-interno")))
        voce["stato"] = "approvato"
        r.fulfill(status=200, content_type="application/json", body=json.dumps({"stato": "approvato", "messaggio": "Approvata."}))
    ctx.route("**/api/interno/dbtr/coda", coda)
    ctx.route(f"**/api/interno/dbtr/{'b' * 32}/anteprima", lambda r: r.fulfill(status=200, content_type="application/geo+json", body=json.dumps(ant)))
    ctx.route(f"**/api/interno/dbtr/{'b' * 32}/approva", approva)
    ctx.route("**/api/interno/edifici/stato", lambda r: r.fulfill(status=200, content_type="application/json",
              body=json.dumps({"zone": [], "disco": {}, "generato": "2026-11-07T10:00:00+0100"})))
    ctx.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI)))
    ctx.route("**/api/ortofoto/finta/**", lambda r: r.fulfill(status=200, content_type="image/png", body=PNG))
    pg.goto(f"{sito}/interno/edifici.html")
    pg.wait_for_function("() => document.querySelector('#tabella-coda tbody tr')", timeout=30000)
    assert "Lugo" in pg.inner_text("#tabella-coda") and "19.906" in pg.inner_text("#tabella-coda")
    pg.click("#tabella-coda tbody tr")
    pg.wait_for_function("() => /Anteprima: 1 corpi/.test(document.getElementById('legenda-coda').textContent)", timeout=30000)
    testo = pg.inner_text("#esito-coda")
    assert "SOSTITUISCE" in testo and "114" in testo
    assert pg.is_enabled("#approva")
    pg.click("#approva")
    pg.wait_for_function("() => /approvato/.test(document.getElementById('titolo-dettaglio').textContent)", timeout=30000)
    assert decisioni == [("POST", "1")]
    assert pg.is_disabled("#approva")
    assert not errori, errori
    ctx.close()


def test_trascina_apri_e_togli_con_esito_accanto(pagina, tmp_path):
    """Prova 6 di Paolo (07/11/2026 sera): «Apri in Modelli 3D» e «Togli» sembravano non fare nulla. Il file si carica
    anche trascinandolo (nessuna finestra di sistema), l'esito dei due pulsanti compare accanto a loro; senza il comune il
    messaggio lo dice lì; «Togli» dice cosa ha tolto; poi «Apri» porta davvero a Modelli 3D."""
    gp = DS.gpkg_er(tmp_path / "estraz_procons.gpkg")
    pagina.apri()
    dati = list(gp.read_bytes())
    # trascina qui: DataTransfer con il file vero
    pagina.pg.evaluate("""(b) => { const f = new File([new Uint8Array(b)], 'estraz_procons.gpkg'), dt = new DataTransfer(); dt.items.add(f);
        const z = document.getElementById('trascina-dbtr');
        z.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, bubbles: true, cancelable: true }));
        z.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true })); }""", dati)
    pagina.pg.wait_for_function("() => /File letto/.test(document.getElementById('messaggio').textContent)", timeout=90000)
    assert pagina.pg.is_visible("#apri-3d")
    pagina.pg.click("#apri-3d")                                                   # comune non scelto
    pagina.pg.wait_for_function("() => /Scegli prima il comune/.test(document.getElementById('messaggio-3d').textContent)")
    assert "aggiungi-dbtr.html" in pagina.pg.url
    pagina.pg.click("#togli-locale")                                              # niente da togliere
    pagina.pg.wait_for_function("() => /non c'erano edifici/.test(document.getElementById('messaggio-3d').textContent)")
    pagina.pg.select_option("#comune", "099014")
    pagina.pg.uncheck("#intero")
    pagina.pg.click("#apri-3d")
    pagina.pg.wait_for_url("**/modelli3d.html?dbtr=locale**", timeout=30000)
    pagina.pg.go_back()
    pagina.pg.wait_for_function("() => document.querySelectorAll('#comune option').length > 100", timeout=30000)
    pagina.pg.evaluate("() => { const p = document.getElementById('passo-letto'); p.hidden = false; }")
    pagina.pg.click("#togli-locale")
    pagina.pg.wait_for_function("() => /tolti da questo browser/.test(document.getElementById('messaggio-3d').textContent)")
    assert "5 corpi" in pagina.pg.inner_text("#messaggio-3d")
    assert not [r for r in pagina.richieste if "/api/dbtr/" in r[1]] and not pagina.errori, pagina.errori


def test_pagina_interna_coda_vuota(browser, sito):
    ctx = browser.new_context(viewport={"width": 1300, "height": 900})
    pg = ctx.new_page()
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    ctx.route("**/api/interno/dbtr/coda", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(
        {"coda": [], "storico": [], "attiva": True, "limiti": {"max_mb": 300, "al_giorno_per_ip": 3, "coda_max": 20}, "occupato_mb": 0})))
    ctx.route("**/api/interno/edifici/stato", lambda r: r.fulfill(status=200, content_type="application/json",
              body=json.dumps({"zone": [], "disco": {}, "generato": "2026-11-07T10:00:00+0100"})))
    ctx.route("**/api/**", lambda r: r.fallback() if "/api/interno/" in r.request.url else r.fulfill(status=404, body="{}"))
    pg.goto(f"{sito}/interno/edifici.html")
    pg.wait_for_function("() => /Nessuna proposta in coda/.test(document.getElementById('tabella-coda').textContent)", timeout=30000)
    assert "Invia il file" in pg.inner_text("#tabella-coda") and not pg.query_selector("#tabella-coda table")
    assert not errori, errori
    ctx.close()
