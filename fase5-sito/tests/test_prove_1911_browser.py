"""Richieste di Paolo del 19/11/2026, provate in Chromium (Playwright, senza rete; si salta se manca):

  - righello delle mappe con l'ortofoto (righello.js): pulsante accanto ai livelli sotto la mappa, punti col clic sinistro,
    chiusura sul primo punto con l'area, punto trascinabile, clic destro che azzera, riquadretto passando sopra, i clic
    della pagina fermati mentre è acceso; misure (distanza e area) controllate con valori noti;
  - Stato della rete elettrica: ortofoto sotto gli strati con la casella, citazione sotto la mappa e nell'immagine; cabine
    grandi come le interruzioni;
  - Cabine primarie: al clic sulla mappa di dettaglio i confini dell'area del punto e delle confinanti arrivano da soli;
    con il GSE simulato la domanda delle confinanti è un POST con il poligono e senza geometria nella risposta;
  - Modelli 3D: «Genera il 3D della vista» senza edificio scelto; clic su un volume e Maiuscolo + clic per più edifici,
    con volume e superfici sommati; in 2D Maiuscolo + clic aggiunge e toglie.
"""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse

import pytest

from test_mappe_browser import (_archivio_tetti, _con_strati, _servi_archivio, _terreno_in_pendenza, attendi, base,  # noqa: F401
                                browser, pagina, webgl)

GSE = "https://services-eu1.arcgis.com/sawHMGY9o8rHlY2j/arcgis/rest/services/AC_Comuni_2025/FeatureServer/0"
FONTI_RETE = {"fonti": [
    {"id": "s2cloudless2016", "nome": "Sentinel-2 cloudless 2016 (10 m)", "licenza": "CC BY 4.0", "citazione": "Sentinel-2 cloudless – EOX (2016)",
     "scheda": "https://cloudless.eox.at/", "stato": "confermata", "copia": True, "nei_report": True, "zoom": [0, 15],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/s2cloudless2016/{z}/{x}/{y}.jpg", "spostabile": False, "spostamento_max": 0},
    {"id": "agea", "nome": "AGEA 2022-2024 (20 cm)", "licenza": "CC BY 4.0", "citazione": "AGEA – ortofoto RGB 2022-2024 (CC BY 4.0)",
     "scheda": "https://geoportale.agea.gov.it/legal-notes", "stato": "confermata", "copia": True, "nei_report": True, "zoom": [10, 19],
     "riquadro": [6.6, 35.4, 18.6, 47.1], "tessere": "/api/ortofoto/agea/{z}/{x}/{y}.jpg", "spostabile": False, "spostamento_max": 0}]}


def _pagina_rete(browser, fonti=True):
    ctx, pg = pagina(browser)
    pg.route("https://services-eu1.arcgis.com/**", lambda r: r.abort())
    if fonti:
        pg.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI_RETE)))
    return ctx, pg


def _tela(pg, sel):
    c = pg.locator(f"{sel} canvas.maplibregl-canvas")
    c.scroll_into_view_if_needed()
    pg.wait_for_timeout(200)
    b = c.bounding_box()
    return b["x"], b["y"], b["width"], b["height"]


# ---------------------------------------------------------------------------------------------- misure
def test_misure_del_righello_con_valori_noti(browser, base):
    ctx, pg = _pagina_rete(browser)
    pg.goto(base + "rete-elettrica.html?prova=1")
    attendi(pg, "!!window.EUGENIO_RIGHELLO")
    R = "window.EUGENIO_RIGHELLO"
    # un grado di meridiano: 111,2 km circa (raggio medio 6371,0088 km)
    assert abs(pg.evaluate(f"{R}.distanza([12, 44], [12, 45])") - 111195) < 5
    # quadrato di 0,01° a 44° N: 0,01° di latitudine × 0,01° di longitudine × cos(44°)
    a = pg.evaluate(f"{R}.area([[12, 44], [12.01, 44], [12.01, 44.01], [12, 44.01]])")
    atteso = 1111.95 * 1111.95 * 0.71934
    assert abs(a - atteso) / atteso < 0.003, (a, atteso)
    assert pg.evaluate(f"{R}.lunghezza([[12, 44], [12, 44.01], [12.01, 44.01]], true)") > pg.evaluate(f"{R}.lunghezza([[12, 44], [12, 44.01], [12.01, 44.01]], false)")
    assert pg.evaluate(f"{R}.testoL(1234.5)") == "1,235 km" and pg.evaluate(f"{R}.testoL(12.345)") == "12,35 m"
    assert pg.evaluate(f"{R}.testoA(25000)") == "25.000 m² (2,50 ha)"
    ctx.close()


# ---------------------------------------------------------------------------------------------- rete elettrica
def test_rete_righello_ortofoto_e_cabine_piccole(browser, base):
    ctx, pg = _pagina_rete(browser)
    pg.goto(base + "rete-elettrica.html?prova=1&regione=08")
    webgl(pg)
    P = "window.EUGENIO_RETE_PAGINA.st"
    attendi(pg, f"{P}.righe.length > 300 && {P}.mappa.getLayer('contesto') && {P}.mappa.isStyleLoaded()", 25000)
    m = f"{P}.mappa"
    # cabine grandi come i punti blu delle interruzioni
    assert pg.evaluate(f"JSON.stringify({m}.getPaintProperty('rete-cabine-punti', 'circle-radius'))") == \
        pg.evaluate(f"JSON.stringify({m}.getPaintProperty('rete-interruzioni', 'circle-radius'))")
    # ortofoto sotto tutti gli strati della rete, con la casella e la citazione
    ordine = pg.evaluate(f"{m}.getStyle().layers.map((l) => l.id)")
    assert ordine.index("contesto") < ordine.index("rete-pieno") and ordine.index("contesto") < ordine.index("rete-cabine-punti")
    pg.evaluate(f"{m}.jumpTo({{ center: [12.25, 44.14], zoom: 13 }})")
    attendi(pg, f"{m}.getLayer('ortofoto') && /AGEA/.test(document.getElementById('attribuzione-ortofoto').textContent)")
    ordine = pg.evaluate(f"{m}.getStyle().layers.map((l) => l.id)")
    assert ordine.index("ortofoto") < ordine.index("rete-pieno")
    assert pg.locator("#attribuzione-ortofoto").is_visible() and "CC BY 4.0" in pg.text_content("#attribuzione-ortofoto")
    righe = " ".join(pg.evaluate("window.EUGENIO_RETE_PAGINA.opzioniImmagine().righe"))
    assert "Ortofoto: AGEA" in righe and "Contesto: Sentinel-2" in righe
    pg.uncheck("#strato-ortofoto")
    assert pg.evaluate(f"{m}.getLayoutProperty('ortofoto', 'visibility')") == "none"
    assert pg.evaluate(f"{m}.getLayoutProperty('contesto', 'visibility')") == "none" and not pg.locator("#attribuzione-ortofoto").is_visible()
    assert "Ortofoto" not in " ".join(pg.evaluate("window.EUGENIO_RETE_PAGINA.opzioniImmagine().righe"))
    pg.check("#strato-ortofoto")
    assert pg.evaluate(f"{m}.getLayoutProperty('ortofoto', 'visibility')") == "visible"
    # righello accanto alle caselle dei livelli
    b = pg.locator("#strati-rete button.righello")
    assert b.count() == 1 and b.get_attribute("aria-pressed") == "false"
    b.click()
    assert b.get_attribute("aria-pressed") == "true" and pg.locator("#strati-rete .righello-aiuto").is_visible()
    pg.evaluate(f"{m}.jumpTo({{ center: [12.25, 44.14], zoom: 14 }})")
    pg.wait_for_timeout(300)
    x, y, w, h = _tela(pg, "#mappa-rete")
    cx, cy = x + w / 2, y + h / 2
    for dx, dy in ((-120, -60), (120, -60), (120, 60)):
        pg.mouse.click(cx + dx, cy + dy)
    st = pg.evaluate("window.EUGENIO_RETE_PAGINA.st.mappa._eugenioRighello.misura()")
    assert len(st["punti"]) == 3 and not st["chiuso"] and 900 < st["lunghezza"] < 3000, st
    assert pg.evaluate(f"{P}.scelto") is None                   # i clic non hanno aperto il comune
    # clic sul primo punto: area chiusa, con il riquadretto passando sopra
    pg.mouse.click(cx - 120, cy - 60)
    st = pg.evaluate(f"{m}._eugenioRighello.misura()")
    assert st["chiuso"] and len(st["punti"]) == 3 and st["area"] > 50000, st
    pg.mouse.move(cx + 60, cy)                                  # dentro il triangolo
    attendi(pg, "getComputedStyle(document.querySelector('#mappa-rete .righello-etichetta')).display === 'block'")
    t = pg.text_content("#mappa-rete .righello-etichetta")
    assert "Area:" in t and "Perimetro:" in t and ("m²" in t or "ha" in t), t
    # un punto si trascina
    prima = pg.evaluate(f"{m}._eugenioRighello.misura().punti[1]")
    pg.mouse.move(cx + 120, cy - 60); pg.mouse.down(); pg.mouse.move(cx + 160, cy - 90, steps=5); pg.mouse.up()
    dopo = pg.evaluate(f"{m}._eugenioRighello.misura()")
    assert dopo["punti"][1] != prima and dopo["chiuso"] and len(dopo["punti"]) == 3
    assert abs(pg.evaluate(f"{m}.getCenter().lng") - 12.25) < 1e-6        # la mappa non si è spostata
    # clic destro: punti azzerati, righello acceso
    pg.mouse.click(cx, cy + 100, button="right")
    assert pg.evaluate(f"{m}._eugenioRighello.misura().punti.length") == 0 and b.get_attribute("aria-pressed") == "true"
    # Esc: spento; i clic tornano alla pagina
    pg.keyboard.press("Escape")
    assert b.get_attribute("aria-pressed") == "false"
    assert not pg.errori, pg.errori
    ctx.close()


@pytest.mark.parametrize("pagina_html,sel", [("ortofoto.html", "#mappa-ortofoto"), ("edifici-pubblici.html", "#mappa-pubblici"),
                                             ("modelli3d.html", "#mappa3d"), ("aggiungi-dbtr.html", "#mappa-dbtr"),
                                             ("fv-cabine.html?prova=1", "#mappa-dettaglio"), ("edificio-geometria.html", "#mappa3d")])
def test_righello_in_tutte_le_pagine_con_ortofoto(browser, base, pagina_html, sel):
    ctx, pg = _pagina_rete(browser)
    pg.goto(base + pagina_html)
    webgl(pg)
    attendi(pg, f"!!document.querySelector('{sel}') && !!document.querySelector('button.righello')", 25000)
    assert pg.locator("button.righello").count() == 1
    # subito sotto la mappa (dopo la maniglia) o nella riga dei comandi e dei livelli sotto la mappa
    sotto = pg.evaluate(f"""(() => {{ const m = document.querySelector('{sel}').getBoundingClientRect(),
        b = document.querySelector('button.righello').getBoundingClientRect(); return b.top >= m.bottom - 1 && b.top - m.bottom < 400; }})()""")
    assert sotto
    assert not pg.errori, pg.errori
    ctx.close()


# ---------------------------------------------------------------------------------------------- cabine primarie
def test_cabine_confini_automatici_al_clic_prova(browser, base):
    ctx, pg = _pagina_rete(browser)
    pg.goto(base + "fv-cabine.html?prova=1&regione=08")
    webgl(pg)
    S = "window.EUGENIO_CABINE.st"
    attendi(pg, f"{S}.det && {S}.det.isStyleLoaded() && {S}.det.getZoom() > 13", 25000)
    pg.wait_for_timeout(500)
    x, y, w, h = _tela(pg, "#mappa-dettaglio")
    pg.mouse.click(x + w / 2, y + h / 2)                      # clic sulla mappa: punto nuovo
    attendi(pg, f"{S}.punti.length === 1 && {S}.aree && {S}.aree.centrale", 20000)
    a = pg.evaluate(f"(() => {{ const a = {S}.aree; return {{ n: a.features.length, centrali: a.features.filter((f) => f.properties._centrale).map((f) => f.properties.COD_AC),"
                    f" area: {S}.punti[0].area.COD_AC, punto: a.punto }}; }})()")
    assert a["n"] >= 3 and a["centrali"] == [a["area"]] and a["punto"] == pg.evaluate(f"{S}.punti[0].k"), a
    assert pg.is_checked("#strato-fv-aree") and pg.locator("#attribuzione-gse").is_visible()
    assert "confinant" in pg.text_content("#messaggio-cabine") and "bordo spesso" in pg.text_content("#legenda-cabine")
    # bordo spesso per l'area del punto
    assert "_centrale" in json.dumps(pg.evaluate(f"{S}.top.getPaintProperty('fv-aree-linea', 'line-width')"))
    # l'immagine li spegne (stessa regola di «Aggiorna confini»)
    pg.evaluate(f"window._o = window.EUGENIO_CABINE.opzioniImmagine({S}.det, 'dettaglio')")
    assert pg.evaluate(f"{S}.det.getLayoutProperty('fv-aree-linea', 'visibility')") == "none"
    pg.evaluate("window._o.dopo()")
    assert not pg.errori, pg.errori
    ctx.close()


def test_cabine_confini_automatici_con_gse_simulato(browser, base):
    ctx, pg = pagina(browser)
    chiamate = []
    pg.route("**/api/rete/cabine*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"type": "FeatureCollection", "features": []})))

    def gse(r):
        dati = r.request.post_data if r.request.method == "POST" else urlparse(r.request.url).query
        q = {k: v[0] for k, v in parse_qs(dati or "").items()}
        q["_metodo"] = r.request.method
        chiamate.append(q)
        if q.get("geometryType") == "esriGeometryPoint":
            fs = [{"type": "Feature", "geometry": None, "properties": {"COD_AC": "AC001E00776", "RAG_SOC": "e-distribuzione S.p.A.", "COD_CONSEG": "1"}}]
        elif q.get("geometryType") == "esriGeometryPolygon":
            fs = [{"type": "Feature", "geometry": None, "properties": {"COD_AC": c}} for c in ("AC001E00776", "AC001E00777", "AC001E00778")]
        else:
            codici = re.findall(r"'([^']+)'", q.get("where", ""))
            fs = [{"type": "Feature", "properties": {"COD_AC": c, "RAG_SOC": "e-distribuzione S.p.A.", "COD_CONSEG": "1"},
                   "geometry": {"type": "Polygon", "coordinates": [[[12.2 + i * 0.1, 44.1], [12.3 + i * 0.1, 44.1], [12.3 + i * 0.1, 44.2], [12.2 + i * 0.1, 44.1]]]}}
                  for i, c in enumerate(codici)]
        r.fulfill(status=200, content_type="application/geo+json", headers={"Access-Control-Allow-Origin": "*"},
                  body=json.dumps({"type": "FeatureCollection", "features": fs}))
    pg.route(GSE + "/query**", gse)
    pg.goto(base + "fv-cabine.html?lat=44.1326&lon=12.2597")
    S = "window.EUGENIO_CABINE.st"
    attendi(pg, f"{S}.aree && {S}.aree.centrale === 'AC001E00776' && {S}.aree.features.length === 3", 20000)
    pg_ = [c for c in chiamate if c.get("geometryType") == "esriGeometryPolygon"]
    assert len(pg_) == 1 and pg_[0]["_metodo"] == "POST" and pg_[0]["returnGeometry"] == "false" and pg_[0]["distance"] == "30"
    assert json.loads(pg_[0]["geometry"])["rings"][0][0] == [12.2, 44.1]
    # i poligoni sempre e solo con where=COD_AC IN (…), mai l'intero strato
    assert all("where" in c and c["where"].startswith("COD_AC IN (") for c in chiamate if c.get("returnGeometry") == "true")
    assert any(c.get("where") == "COD_AC IN ('AC001E00776','AC001E00777','AC001E00778')" for c in chiamate)
    assert "2 aree confinanti" in pg.text_content("#messaggio-cabine")
    assert not pg.errori, pg.errori
    ctx.close()


# ---------------------------------------------------------------------------------------------- Modelli 3D
def _fuoco(pg, s, corpo, maiuscolo=False):
    """Clic (o Maiuscolo + clic) al centro di un corpo, vista dall'alto, nella vista 3D."""
    attendi(pg, f"!{s}.mappa.isMoving()", 10000)
    pg.evaluate(f"{s}.mappa.jumpTo({{ pitch: 0, bearing: 0 }})")
    # volume disegnato sotto il punto (tessere arrivate)
    attendi(pg, f"""(() => {{ const st = {s}, c = [...st.corpi, ...st.vicini].find((x) => x.id === '{corpo}');
        const ll = st.proj.indietro(window.EUGENIO_EDIFICI.centroide(c.ring));
        const ids = ['scelto', ...st.sorgentiCorpi].filter((id) => st.mappa.getLayer(id));
        return st.mappa.queryRenderedFeatures(st.mappa.project(ll), {{ layers: ids }}).length > 0; }})()""", 15000)
    pg.evaluate(f"""(() => {{ const c = [...{s}.corpi, ...{s}.vicini].find((x) => x.id === '{corpo}');
        const ll = {s}.proj.indietro(window.EUGENIO_EDIFICI.centroide(c.ring));
        {s}.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: {s}.mappa.project(ll), originalEvent: {{ shiftKey: {str(maiuscolo).lower()} }} }}); }})()""")


def test_modelli3d_vista_senza_edificio_e_piu_edifici(browser, base, tmp_path):
    lon, lat = _archivio_tetti(tmp_path)
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(lat))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    s, E = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {s}.mappa && {s}.archivi.length >= 1 && !document.getElementById('genera-3d').disabled", 25000)
    # lontano: «Genera il 3D della vista» chiede di avvicinarsi
    pg.evaluate(f"{s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 12 }})")
    assert "zona che vedi" in pg.get_attribute("#genera-3d", "title")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, "/avvicinati/.test(document.getElementById('messaggio').textContent)")
    assert pg.evaluate(f"{s}.in3d") is False
    # da vicino, senza edificio scelto: 3D della vista con tutti i corpi come vicini, nessun pannello dell'edificio
    pg.evaluate(f"{s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }})")
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.vicini.length === 4", 25000)
    assert pg.evaluate(f"{s}.corpi.length") == 0 and pg.evaluate(f"{s}.edificio") is None
    assert "3D della vista" in pg.text_content("#messaggio") and pg.locator("#passo-corpi").is_hidden()
    assert "vista 3D" in pg.evaluate(f"{E}.opzioniImmagine().titolo")
    # clic su un volume: lo sceglie
    _fuoco(pg, s, "V1")
    attendi(pg, f"{s}.edificio === 'E-V' && {s}.corpi.length === 1 && !!{s}.geometria && /V1/.test(document.getElementById('tabella-corpi').textContent)")
    v1 = pg.evaluate(f"{s}.geometria.volume_lordo")
    assert v1 > 0 and pg.locator("#passo-corpi").is_visible()
    # Maiuscolo + clic: aggiunge E-K, valori sommati
    _fuoco(pg, s, "K2", maiuscolo=True)
    attendi(pg, f"{s}.edifici.length === 2 && {s}.corpi.length === 4 && /K1/.test(document.getElementById('tabella-corpi').textContent)", 20000)
    d = pg.evaluate(f"""(() => {{ const E = window.EUGENIO_EDIFICI, st = {s};
        const k = st.corpi.filter((c) => c.edificio === 'E-K'), v = st.corpi.filter((c) => c.edificio === 'E-V');
        return {{ tot: st.geometria.volume_lordo, k: E.indicatori(k, []).volume_lordo, v: E.indicatori(v, []).volume_lordo,
          sup: st.geometria.superficie_disperdente, sk: E.indicatori(k, []).superficie_disperdente, sv: E.indicatori(v, []).superficie_disperdente,
          edifici: st.edifici, tabella: document.getElementById('tabella-corpi').textContent, scheda: document.getElementById('scheda-edificio').textContent }}; }})()""")
    assert abs(d["tot"] - (d["k"] + d["v"])) < 0.5 and abs(d["v"] - v1) < 0.5, d
    assert abs(d["sup"] - (d["sk"] + d["sv"])) < 0.5, d
    assert d["edifici"] == ["E-V", "E-K"] and all(c in d["tabella"] for c in ("K1", "K2", "K3", "V1"))
    assert "Edifici scelti insieme" in d["scheda"] and "edifici scelti insieme" in pg.text_content("#messaggio")
    assert "edifici E-V, E-K" in pg.evaluate(f"{E}.opzioniImmagine().titolo")
    # Maiuscolo + clic su uno già scelto: lo toglie
    _fuoco(pg, s, "V1", maiuscolo=True)
    attendi(pg, f"{s}.edifici.length === 1 && {s}.edificio === 'E-K' && {s}.corpi.length === 3", 20000)
    # in 2D: Maiuscolo + clic aggiunge e toglie; «Genera il 3D» li ricostruisce insieme
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{s}.in3d && {s}.mappa.getPitch() === 0", 10000)
    pg.evaluate(f"{E}.scegli2d('E-K', {lon}, {lat})")
    pg.evaluate(f"{s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }})")
    attendi(pg, f"{s}.mappa.loaded() && {s}.mappa.queryRenderedFeatures({{ layers: {s}.strati2d.filter((id) => {s}.mappa.getLayer(id)) }}).length >= 4", 20000)
    clic2d = f"""(id, maiuscolo) => {{ const st = {s}, f = st.mappa.queryRenderedFeatures({{ layers: st.strati2d.filter((x) => st.mappa.getLayer(x)) }})
        .find((x) => String(x.properties.id) === id); const g = f.geometry.coordinates[0], ll = [g.reduce((a, q) => a + q[0], 0) / g.length, g.reduce((a, q) => a + q[1], 0) / g.length];
        st.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: st.mappa.project(ll), originalEvent: {{ shiftKey: maiuscolo }} }}); }}"""
    pg.evaluate(f"({clic2d})('V1', true)")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.scelti.length === 2")
    assert "2 edifici scelti" in pg.text_content("#messaggio") and "2 edifici scelti" in pg.get_attribute("#genera-3d", "title")
    filtro = json.dumps(pg.evaluate(f"{s}.mappa.getFilter('corpi-2d-scelto')"))
    assert "E-K" in filtro and "E-V" in filtro
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{s}.in3d && {s}.corpi.length === 4 && {s}.edifici.length === 2", 25000)
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{s}.in3d")
    # «Torna alla mappa 2D» toglie la scelta (come prima): la si rifà e Maiuscolo + clic due volte su V1 la aggiunge e la toglie
    pg.evaluate(f"{E}.scegli2d('E-K', {lon}, {lat})")
    pg.evaluate(f"{s}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }})")
    attendi(pg, f"{s}.mappa.loaded() && {s}.mappa.queryRenderedFeatures({{ layers: {s}.strati2d.filter((id) => {s}.mappa.getLayer(id)) }}).length >= 4", 20000)
    pg.evaluate(f"({clic2d})('V1', true)")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.scelti.length === 2")
    pg.wait_for_timeout(450)
    pg.evaluate(f"({clic2d})('V1', true)")
    attendi(pg, f"{s}.daGenerare && {s}.daGenerare.scelti.length === 1 && {s}.daGenerare.edificio === 'E-K'")
    assert not pg.errori, pg.errori
    ctx.close()
