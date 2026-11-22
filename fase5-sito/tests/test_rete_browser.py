"""Pagine della rete elettrica (17/11/2026, richiesta di Paolo): Statistiche › «Stato della rete elettrica»
(rete-elettrica.html, rete_elettrica.js) e Fotovoltaico › «Cabine primarie» (fv-cabine.html, fv_cabine.js), parte comune
rete.js.

Sui file: voci del menu (computer e telefono, sperimentali), script e fonti nelle pagine, indirizzo del servizio del GSE in un
solo punto del codice, regola della criticità (pieno/strisce) uguale a quella del contratto, nessun dato di mercato.
In Chromium (si salta se Playwright o Chromium non ci sono), senza rete:
  - ?prova=1 (dati sintetici del browser): strati spegnibili con la legenda, comune scelto con criticità, cabine e statistiche,
    CSV con la citazione in riga 1 e l'ODbL, corpo del PDF/Excel per POST /api/report;
  - API simulate (/api/rete/… e il servizio del GSE intercettati): richiesta punto → COD_AC senza geometria, poi i poligoni con
    where=COD_AC IN (…); strato GSE spento nell'immagine e riacceso dopo; GeoJSON separato con licenza, fonte, servizio,
    avviso e le sole proprietà del contratto; CSV dei dati con i soli codici;
  - elenco nello stesso formato di Patrimonio con lat/lon: i punti restano nel browser (nessuna chiamata a /api/patrimonio);
  - niente scorrimento orizzontale a 375 px, nessun errore JavaScript.
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


def _t(nome: str) -> str:
    return (SITO / nome).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------------- file
def test_menu_e_pagine():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert t.count('href="rete-elettrica.html"') == 2 and t.count('href="fv-cabine.html"') == 2
    gruppi = {g["id"]: g for g in C.gruppi_menu(t)}
    # (20/11/2026) dopo la rete viene «Produzione e consumi di elettricità»
    assert [v["pagina"] for v in gruppi["statistiche"]["voci"]][-4:] == ["rete-elettrica.html", "elettricita.html", "carichi.html",
                                                                         "suolo.html"]       # (22/11/2026) Suolo e aree agricole
    assert gruppi["fotovoltaico"]["voci"][0] == {"pagina": "fv-cabine.html", "nome": "Cabine primarie", "tipo": ""}
    assert re.search(r'href="rete-elettrica.html">Stato della rete elettrica <span class="cantiere prova">sperimentale', t)
    assert C.main(["--controlla"]) == 0
    for nome, gruppo, js in (("rete-elettrica.html", "Statistiche", "rete_elettrica.js"), ("fv-cabine.html", "Fotovoltaico", "fv_cabine.js")):
        s = _t(nome)
        assert f'<p class="gruppo-servizio">{gruppo}</p>' in s and "Servizio sperimentale non ancora verificato" in s
        assert s.count('aria-current="page"') == 2
        assert re.search(rf'<script src="rete\.js\?v=\d{{8}}[a-z]"></script>\s*<script src="{js}\?v=', s)
        assert "openstreetmap.org/copyright" in s and "ODbL" in s and "e-distribuzione" in s
        for vietato in ("PUN", "TTF", "€/MWh"):
            assert vietato not in s, (nome, vietato)
    assert "mappa-interattiva-delle-cabine-primarie" in _t("rete-elettrica.html")
    assert "CC BY-NC-SA 3.0 IT" in _t("fv-cabine.html") and "Scarica i confini delle aree (GSE, CC BY-NC-SA)" in _t("fv-cabine.html")


def test_servizio_gse_in_un_solo_punto():
    tutti = {f.name: f.read_text(encoding="utf-8") for f in SITO.glob("*.js")}
    con = [n for n, s in tutti.items() if "services-eu1.arcgis.com" in s]
    assert con == ["rete.js"] and tutti["rete.js"].count("services-eu1.arcgis.com") == 1
    r = tutti["rete.js"]
    # mai l'intero strato: le geometrie solo con where=COD_AC IN (…), al massimo 100 aree, semplificate
    assert "COD_AC IN (" in r and "MASSIMO: 100" in r and "maxAllowableOffset" in r and 'returnGeometry: "false"' in r
    assert "where=1=1" not in r and "1%3D1" not in r


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


def _pagina(browser, larghezza=1366, altezza=900):
    ctx = browser.new_context(viewport={"width": larghezza, "height": altezza}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    pg.route("**/api/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
    pg.route("https://services-eu1.arcgis.com/**", lambda r: r.abort())      # nessuna rete: nei casi di prova non serve
    return ctx, pg


def _aspetta(pg, js, ms=15000):
    pg.wait_for_function(js, timeout=ms)


def test_regola_della_criticita(base, browser):
    ctx, pg = _pagina(browser)
    pg.goto(base + "rete-elettrica.html?prova=1")
    c = lambda t: pg.evaluate(f"JSON.stringify(window.EUGENIO_RETE.classeComune({json.dumps(t)}))")   # noqa: E731
    assert json.loads(c({"VERDE": 5})) == {"livello": "VERDE", "quota": 1, "pieno": None, "strisce": None}
    assert json.loads(c({"VERDE": 3, "ROSSO": 1}))["strisce"] == ["ARANCIONE", "ROSSO"]
    assert json.loads(c({"VERDE": 1, "GIALLO": 1}))["strisce"] == ["VERDE", "GIALLO"]           # metà esatta: strisce
    assert json.loads(c({"VERDE": 1, "ARANCIONE": 2}))["pieno"] == "ARANCIONE"
    assert json.loads(c({}))["livello"] is None
    assert pg.evaluate("window.EUGENIO_RETE.coloreCabina({livello: 'VERDE', gestore: 'e-distribuzione S.p.A.'})") == "#ffffff"
    assert pg.evaluate("window.EUGENIO_RETE.coloreCabina({livello: 'ROSSO', gestore: 'Unareti'})") == "#9a9a9a"
    ctx.close()


def test_stato_della_rete_prova(base, browser, tmp_path):
    ctx, pg = _pagina(browser)
    corpi = []
    pg.route("**/api/report?formato=*", lambda r: (corpi.append(r.request.post_data),
             r.fulfill(status=200, headers={"Content-Disposition": 'attachment; filename="rete.xlsx"'}, body=b"PK")))
    pg.goto(base + "rete-elettrica.html?prova=1&regione=08")
    _aspetta(pg, "() => { const s = window.EUGENIO_RETE_PAGINA && window.EUGENIO_RETE_PAGINA.st; return s && s.righe.length > 300 && s.cabine; }")
    assert pg.locator(".rete-prova").is_visible()
    assert "dal 17/11/2026" in pg.locator("#stato-rete").inner_text()
    assert "Dato non disponibile per la provincia" in pg.locator("#avviso-province").inner_text()
    leg = pg.locator("#legenda-rete")
    assert "classificazione di EuGEnio" in leg.inner_text() and "altro distributore o senza dato" in leg.inner_text()
    # strati spegnibili uno per uno, con la legenda
    pg.uncheck("#strato-cabine")
    assert "altro distributore o senza dato" not in leg.inner_text()
    assert pg.evaluate("window.EUGENIO_RETE_PAGINA.st.mappa.getLayoutProperty('rete-cabine-punti', 'visibility')") == "none"
    pg.check("#strato-cabine")
    pg.uncheck("#strato-criticita")
    assert pg.evaluate("window.EUGENIO_RETE_PAGINA.st.mappa.getLayoutProperty('rete-strisce', 'visibility')") == "none"
    pg.check("#strato-criticita")
    # comune concessionario: criticità, cabine, statistiche con la data d'inizio e la durata stimata
    istat = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.righe.find((r) => r.concessionario && r.pieno).istat")
    pg.fill("#cerca-comune-rete", pg.evaluate(f"window.EUGENIO_RETE_PAGINA.st.righe.find((r) => r.istat === '{istat}').nome"))
    pg.click("#apri-comune")
    _aspetta(pg, "() => document.querySelector('#grafico-interruzioni svg')")
    s = pg.locator("#scheda-comune").inner_text()
    assert "pieno" in s and "Cabine primarie che servono il comune" in s and "dal 01/06/2026" in s and "stimata" in s
    assert f"comune={istat}" in pg.url
    # comune di un altro distributore: rimando al GSE
    altro = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.righe.find((r) => r.concessionario === false).istat")
    pg.evaluate(f"window.EUGENIO_RETE_PAGINA.apriComune('{altro}')")
    assert "Il distributore è un altro" in pg.locator("#scheda-comune").inner_text()
    assert pg.locator("#scheda-comune a[href*='gse.it']").count() == 1
    pg.evaluate(f"window.EUGENIO_RETE_PAGINA.apriComune('{istat}')")
    _aspetta(pg, "() => window.EUGENIO_RETE_PAGINA.st.dettaglio && window.EUGENIO_RETE_PAGINA.st.dettaglio.inter")
    # CSV: citazione in riga 1, avviso dei dati sintetici, ODbL in fondo
    with pg.expect_download() as d:
        pg.click("#scarica-dati button[data-formato=csv]")
    f = tmp_path / d.value.suggested_filename
    d.value.save_as(f)
    testo = f.read_text(encoding="utf-8-sig")
    righe = testo.splitlines()
    assert righe[0].startswith("Fonte: EuGEnio – eugenio.statocritico.it") and "SINTETICI" in righe[1]
    assert "Comuni – Emilia-Romagna" in testo and "Interruzioni per mese" in testo and "ODbL" in testo
    # Excel: il documento va a POST /api/report?formato=xlsx
    pg.click("#scarica-dati button[data-formato=xlsx]")
    _aspetta(pg, "() => /Download avviato/.test(document.getElementById('messaggio-dati').textContent)")
    doc = json.loads(corpi[-1])
    assert doc["titolo"] == "Stato della rete elettrica – Emilia-Romagna" and any("OpenStreetMap" in x["testo"] for x in doc["fonti"])
    assert all(len(b["intestazioni"]) <= 30 for s in doc["sezioni"] for b in s["blocchi"] if b["tipo"] == "tabella")
    # immagine: righe con le fonti
    o = pg.evaluate("JSON.stringify(window.EUGENIO_RETE_PAGINA.opzioniImmagine())")
    assert "OpenStreetMap" in o and "classificazione di EuGEnio" in o
    assert not pg.errori, pg.errori
    ctx.close()


CABINE = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [12.25, 44.14]},
     "properties": {"cod_ac": "AC001E00776", "gestore": "e-distribuzione", "cod_cp_ed": "DV001382982", "nome_cp_ed": "CESENA OVEST",
                    "comuni_serviti": "040007", "livello": "ARANCIONE", "trasf": {"VERDE": 2, "GIALLO": 0, "ARANCIONE": 1, "ROSSO": 0},
                    "data_saturazione": "2026-11-01", "esito": "sicuro"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [12.30, 44.10]},
     "properties": {"cod_ac": "AC001E00777", "gestore": "e-distribuzione", "cod_cp_ed": "DV001382983", "nome_cp_ed": "CESENA SUD",
                    "comuni_serviti": "040007;040001", "livello": "VERDE", "trasf": {"VERDE": 3}, "data_saturazione": "2026-11-01", "esito": "da_verificare"}},
]}


def test_cabine_primarie_con_api_e_gse_simulati(base, browser, tmp_path):
    ctx, pg = _pagina(browser)
    chiamate = []

    def api(r):
        u = urlparse(r.request.url)
        if u.path == "/api/rete/cabine":
            return r.fulfill(status=200, content_type="application/json", body=json.dumps(CABINE))
        return r.fulfill(status=404, content_type="application/json", body="{}")
    pg.route("**/api/**", api)

    def gse(r):
        q = {k: v[0] for k, v in parse_qs(urlparse(r.request.url).query).items()}
        chiamate.append(q)
        if "geometry" in q:
            corpo = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": None,
                     "properties": {"COD_AC": "AC001E00776", "RAG_SOC": "e-distribuzione S.p.A.", "COD_CONSEG": "30092025"}}]}
        else:
            corpo = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"COD_AC": "AC001E00776", "RAG_SOC": "e-distribuzione S.p.A.",
                     "COD_CONSEG": "30092025"}, "geometry": {"type": "Polygon", "coordinates": [[[12.2, 44.1], [12.3, 44.1], [12.3, 44.2], [12.2, 44.1]]]}}]}
        r.fulfill(status=200, content_type="application/geo+json", headers={"Access-Control-Allow-Origin": "*"}, body=json.dumps(corpo))
    pg.route(GSE + "/query**", gse)
    pg.goto(base + "fv-cabine.html?lat=44.1326&lon=12.2597")
    _aspetta(pg, "() => window.EUGENIO_CABINE && window.EUGENIO_CABINE.st.cabine.length === 2")
    # punto → COD_AC senza geometria
    p = chiamate[0]
    assert p["returnGeometry"] == "false" and p["geometryType"] == "esriGeometryPoint" and p["inSR"] == "4326" and p["outFields"] == "COD_AC,RAG_SOC,COD_CONSEG"
    testo = pg.locator("#elenco-cabine").inner_text()
    assert "CESENA OVEST" in testo and "Area GSE di: Punto dell'indirizzo" in testo and "CESENA SUD" in testo and "Serve il comune di" in testo
    assert "AC001E00776" in pg.locator("#elenco-punti").inner_text()
    # (19/11/2026) i confini dell'area del punto arrivano da soli (test_prove_1911_browser.py); poi «Aggiorna confini»
    _aspetta(pg, "() => window.EUGENIO_CABINE.st.aree && window.EUGENIO_CABINE.st.aree.centrale === 'AC001E00776'")
    pg.evaluate("window.EUGENIO_CABINE.st.aree = null")
    # «Aggiorna confini»: solo le aree spuntate non ancora lette (quella del punto c'è già: 19/11 sera, i confini si sommano),
    # con where=COD_AC IN (…), semplificate
    pg.click("#aggiorna-confini")
    _aspetta(pg, "() => window.EUGENIO_CABINE.st.aree")
    w = chiamate[-1]
    assert w["where"] == "COD_AC IN ('AC001E00777')" and w["maxAllowableOffset"] == "0.0002" and w["returnGeometry"] == "true"
    assert pg.locator("#attribuzione-gse").is_visible() and "CC BY-NC-SA 3.0 IT" in pg.locator("#attribuzione-gse").inner_text()
    # immagine: strato GSE spento durante la copia, riacceso dopo
    vis = "window.EUGENIO_CABINE.st.det.getLayoutProperty('fv-aree-linea', 'visibility')"
    assert pg.evaluate(vis) == "visible"
    pg.evaluate("window._o = window.EUGENIO_CABINE.opzioniImmagine(window.EUGENIO_CABINE.st.det, 'dettaglio')")
    assert pg.evaluate(vis) == "none" and "OpenStreetMap" in pg.evaluate("window._o.righe.join(' ')")
    pg.evaluate("window._o.dopo()")
    assert pg.evaluate(vis) == "visible"
    # una cabina tolta dalla spunta non va nella richiesta successiva
    pg.locator("#elenco-cabine input[type=checkbox]").nth(1).uncheck()
    # file separato dei confini (GeoJSON nel browser)
    with pg.expect_download() as d:
        pg.click("#scarica-aree-gse")
    assert re.fullmatch(r"aree_convenzionali_GSE_\d{4}-\d{2}-\d{2}\.geojson", d.value.suggested_filename)
    f = tmp_path / "aree.geojson"
    d.value.save_as(f)
    gj = json.loads(f.read_text(encoding="utf-8"))
    assert chiamate[-1]["where"] == "COD_AC IN ('AC001E00776')"
    assert gj["licenza"].startswith("CC BY-NC-SA 3.0 IT") and gj["servizio"] == GSE and "ricerca per POD" in gj["avviso"]
    assert gj["fonte"].startswith("GSE S.p.A. – Mappa interattiva delle cabine primarie") and gj["letto_il"]
    assert set(gj["features"][0]["properties"]) == {"COD_AC", "gestore", "COD_CONSEG", "sedi"}
    assert gj["features"][0]["properties"]["sedi"] == ["Punto dell'indirizzo"]
    # dati: solo i codici, niente geometrie del GSE
    with pg.expect_download() as d:
        pg.click("#scarica-dati button[data-formato=csv]")
    f = tmp_path / "dati.csv"
    d.value.save_as(f)
    t = f.read_text(encoding="utf-8-sig")
    assert t.splitlines()[0].startswith("Fonte: EuGEnio") and "AC001E00776" in t and "DV001382982" in t
    assert "Polygon" not in t and "30092025" not in t and "ODbL" in t
    assert not pg.errori, pg.errori
    ctx.close()


def test_cabine_primarie_elenco_e_colore(base, browser, tmp_path):
    ctx, pg = _pagina(browser)
    patrimonio = []
    pg.route("**/api/patrimonio", lambda r: (patrimonio.append(1), r.fulfill(status=500, body="{}")))
    pg.goto(base + "fv-cabine.html?prova=1&regione=08")
    _aspetta(pg, "() => window.EUGENIO_CABINE && window.EUGENIO_CABINE.st.det")
    f = tmp_path / "sedi.csv"
    f.write_text("id;denominazione;indirizzo;civico;comune;foglio;particella;lat;lon\n"
                 "A1;Ospedale;Viale Ghirotti;286;Cesena;;;44,1326;12,2597\nA2;Scuola;;;Forlì;;;44.2227;12.0407\n", encoding="utf-8")
    pg.set_input_files("#file-elenco", str(f))
    pg.click("#carica-elenco")
    _aspetta(pg, "() => window.EUGENIO_CABINE.st.punti.length === 2 && window.EUGENIO_CABINE.st.cabine.length > 0")
    assert not patrimonio and "2 punti aggiunti su 2 righe" in pg.locator("#messaggio-elenco").inner_text()
    assert "A1 · Ospedale" in pg.locator("#elenco-punti").inner_text()
    # (19/11/2026 sera) confini automatici anche per i punti dell'elenco
    _aspetta(pg, "() => window.EUGENIO_CABINE.st.aree && window.EUGENIO_CABINE.st.aree.centrali.length >= 1")
    # colore del punto scelto dal menu come in Modelli 3D
    pg.locator("#elenco-punti li").nth(1).click()
    pg.click("#colore-punti .vestito-pulsante")
    pg.click("#colore-punti-viola")
    assert pg.evaluate("window.EUGENIO_CABINE.st.punti[1].colore") == "#8a4fd0"
    assert pg.evaluate("window.EUGENIO_CABINE.st.punti[0].colore") != "#8a4fd0"
    assert not pg.errori, pg.errori
    ctx.close()


@pytest.mark.parametrize("pagina", ["rete-elettrica.html?prova=1", "fv-cabine.html?prova=1"])
def test_telefono_senza_scorrimento_orizzontale(base, browser, pagina):
    ctx, pg = _pagina(browser, 375, 740)
    pg.goto(base + pagina)
    pg.wait_for_timeout(1500)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert not pg.errori, pg.errori
    ctx.close()


# ---------------------------------------------------------------------------------------------- dati veri (se ci sono)
DATI_RETE = Path(__import__("os").environ.get("EUGENIO_DATI_RETE", "/home/claude/dati_rete"))
PROV_ER = ("033", "034", "035", "036", "037", "038", "039", "040", "099")


@pytest.mark.skipif(not (DATI_RETE / "cabine_primarie.geojson").exists(), reason="uscite dell'agente DATI non presenti")
def test_stato_della_rete_con_i_dati_veri_del_raccordo(base, browser):
    """Le uscite vere del raccordo (cabine_primarie.geojson, comuni_criticita.json, comuni_non_concessionari.json) servite
    come farebbe /api/rete: strisce ["VERDE", "GIALLO"], punti solo_gse grigi, comuni non concessionari col retino."""
    cab = json.loads((DATI_RETE / "cabine_primarie.geojson").read_text(encoding="utf-8"))
    crit = json.loads((DATI_RETE / "comuni_criticita.json").read_text(encoding="utf-8"))
    nonc = {c["istat"] for c in json.loads((DATI_RETE / "comuni_non_concessionari.json").read_text(encoding="utf-8"))["comuni"]
            if not c.get("con_trasformatori_ed")}
    comuni = [{"istat": k, "nome": v["nome"], "concessionario": k not in nonc, "pieno": v["pieno"], "strisce": v["strisce"], "livello": v["livello"],
               "quota": v["quota"], "trasf": v["trasf"], "cabine": v["cabine"], "dato_disponibile": k not in nonc}
              for k, v in crit["comuni"].items() if k[:3] in PROV_ER]
    comuni += [{"istat": k, "nome": "", "concessionario": False, "pieno": None, "strisce": None, "livello": None, "quota": None, "trasf": None,
                "cabine": [], "dato_disponibile": False} for k in nonc if k[:3] in PROV_ER]
    ctx, pg = _pagina(browser)

    def api(r):
        u = urlparse(r.request.url).path
        corpo = {"/api/rete/stato": {"saturazione_aggiornata": "2026-11-17T19:59:00+01:00", "interruzioni_aggiornate": "2026-11-17T20:00:00+01:00",
                                     "attive": 0, "province_mancanti": ["001"], "raccolta_dal": "2026-11-17T18:00:00+01:00"},
                 "/api/rete/cabine": cab, "/api/rete/comuni": comuni,
                 "/api/rete/interruzioni/attive": {"type": "FeatureCollection", "features": []}}.get(u)
        if corpo is None:
            return r.fulfill(status=404, content_type="application/json", body="{}")
        r.fulfill(status=200, content_type="application/json", body=json.dumps(corpo))
    pg.route("**/api/**", api)
    pg.goto(base + "rete-elettrica.html?regione=08")
    _aspetta(pg, "() => { const s = window.EUGENIO_RETE_PAGINA && window.EUGENIO_RETE_PAGINA.st; return s && s.righe.length > 300 && s.cabine && s.cabine.features.length > 1000; }")
    feats = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.disegnati.features.map((f) => f.properties)")
    strisce = {f.get("strisce") for f in feats if f.get("strisce")}
    assert strisce <= {"GIALLO", "ARANCIONE", "ROSSO"} and strisce
    assert any(f.get("conc") is False for f in feats)
    grigi = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.cabine.features.filter((f) => f.properties.esito === 'solo_gse').map((f) => f.properties._colore)")
    assert grigi and set(grigi) == {"#9a9a9a"}
    assert not pg.errori, pg.errori
    ctx.close()


def test_comune_servito_in_parte(base, browser, tmp_path):
    """(17/11/2026 sera, decisione di Paolo) comuni segnati «non serviti» da e-distribuzione ma con suoi trasformatori:
    colore della criticità (niente retino), bordo tratteggiato, nota «servito in parte da un altro distributore» nel
    riquadretto, nella scheda, nella legenda e nei file (colonna «Servito in parte da un altro distributore»)."""
    ctx, pg = _pagina(browser)
    pg.goto(base + "rete-elettrica.html?prova=1&regione=08")
    _aspetta(pg, "() => { const s = window.EUGENIO_RETE_PAGINA && window.EUGENIO_RETE_PAGINA.st; return s && s.disegnati && s.righe.length > 300; }")
    istat = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.righe.find((r) => r.servito_in_parte && r.livello).istat")
    p = pg.evaluate(f"window.EUGENIO_RETE_PAGINA.st.disegnati.features.find((f) => f.properties.istat === '{istat}').properties")
    assert p["in_parte"] is True and p["conc"] is True and (p.get("pieno") or p.get("strisce") or True)
    assert "servito in parte da un altro distributore" in pg.locator("#legenda-rete").inner_text()
    pg.evaluate(f"window.EUGENIO_RETE_PAGINA.apriComune('{istat}')")
    _aspetta(pg, "() => window.EUGENIO_RETE_PAGINA.st.dettaglio && window.EUGENIO_RETE_PAGINA.st.dettaglio.inter")
    s = pg.locator("#scheda-comune").inner_text()
    assert "Servito in parte da un altro distributore" in s and "Criticità" in s and "Il distributore è un altro" not in s
    with pg.expect_download() as d:
        pg.click("#scarica-dati button[data-formato=csv]")
    f = tmp_path / "rete.csv"
    d.value.save_as(f)
    righe = f.read_text(encoding="utf-8-sig").splitlines()
    testa = next(r.split(";") for r in righe if r.startswith("ISTAT;"))
    k = testa.index("Servito in parte da un altro distributore")
    riga = next(r.split(";") for r in righe if r.startswith(istat + ";"))
    assert riga[k] == "sì" and riga[3] == "e-distribuzione"
    assert not pg.errori, pg.errori
    ctx.close()
