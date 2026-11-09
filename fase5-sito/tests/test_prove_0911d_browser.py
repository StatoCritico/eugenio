"""Prove nel browser delle correzioni del 09/11/2026 d (prove Q8 di Paolo): tegola spenta dalla ricerca, tetto a falde
anche per i corpi con cortile (falde che scendono verso il bordo e verso il cortile), maniglia per l'altezza della mappa,
clic nella vista 3D sul volume più vicino alla camera, chiome indicative da OpenStreetMap dove manca il LiDAR (dove c'è vince
il LiDAR), tessere «occupata» che non fermano la fonte e tessere d'errore delle particelle senza righe rosse. Rotte /api
simulate, nessuna rete; si salta senza Playwright o Chromium."""
from __future__ import annotations

import io
import json
import math
import re

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import (SITO, _con_strati, _genera, _servi_archivio, _terreno_in_pendenza, attendi, base,  # noqa: E402,F401
                                browser, pagina, webgl)
from test_prove_0911c_browser import CESENA, M3D, _archivi_con_alberi, _cella  # noqa: E402

S, EE = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"


def _archivio_corte(radice):
    """Edificio E-C a corte (40 × 30 m con un cortile di 20 × 10 m al centro), un corpo C2 a L e un vicino V1."""
    import sys
    sys.path.insert(0, str(SITO.parents[1] / "fase10-edifici3d"))
    from shapely.geometry import Polygon, box
    from edifici3d import modello as M
    from edifici3d.__main__ import prepara_corpi
    x0, y0 = 785540.0, 4884790.0
    c = dict(fonte_sagoma="DBTR Emilia-Romagna – UVL", licenza="CC BY 4.0", fonte_altezza="DBTR H_UVL (altezza del corpo, ±3 m)", quota_terreno=100)
    corte = Polygon([(x0, y0), (x0 + 40, y0), (x0 + 40, y0 + 30), (x0, y0 + 30)], [[(x0 + 10, y0 + 10), (x0 + 30, y0 + 10), (x0 + 30, y0 + 20), (x0 + 10, y0 + 20)]])
    elle = Polygon([(x0 + 50, y0), (x0 + 80, y0), (x0 + 80, y0 + 10), (x0 + 60, y0 + 10), (x0 + 60, y0 + 30), (x0 + 50, y0 + 30)])
    corpi = [M.Corpo(id="C1", edificio="E-C", sagoma=corte, gronda=12, **c), M.Corpo(id="C2", edificio="E-C", sagoma=elle, gronda=9, **c),
             M.Corpo(id="V1", edificio="E-V", sagoma=box(x0 - 40, y0, x0 - 20, y0 + 20), gronda=20, **c)]
    out = radice / "cc-by" / "er" / "prodotti"
    prepara_corpi(corpi, None, out, "CC BY 4.0", "Regione Emilia-Romagna – DBTR, CC BY 4.0", extra={"nome": "DBTR Emilia-Romagna"})
    (radice / "archivi.json").write_text(json.dumps({"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}]}), encoding="utf-8")
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:7791", "EPSG:4326", always_xy=True).transform(x0 + 5, y0 + 15)


def _apri(browser, base, tmp_path, archivio=_archivio_corte, nome="modelli3d.html"):
    lon, lat = archivio(tmp_path)
    ctx, pg = pagina(browser)
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(lat))
    pg.goto(base + nome)
    webgl(pg)
    return ctx, pg, lon, lat


def _clic_corpo(pg, corpo, alto=True):
    if alto:
        pg.evaluate(f"{S}.mappa.jumpTo({{ pitch: 0, bearing: 0 }})")
        pg.wait_for_timeout(300)
    pg.evaluate(f"""(() => {{ const c = [...{S}.corpi, ...{S}.vicini].find((x) => x.id === '{corpo}');
        const p = window.EUGENIO_EDIFICI.centroide(c.ring), q = c.buchi && c.buchi.length ? [c.ring[0][0] + 4, c.ring[0][1] + 4] : p;
        const ll = {S}.proj.indietro(q);
        {S}.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: {S}.mappa.project(ll) }}); }})()""")


def test_tetto_a_falde_con_il_cortile(browser, base, tmp_path):
    """Punto 3 (via Ovidio a Rimini, Bufalini): il corpo a corte prende le falde (8: quattro verso la strada, quattro verso
    il cortile), anche il corpo a L; tabella, falde a gradini, immagine e report; un'area FV su una falda verso il cortile
    ne prende orientamento e inclinazione."""
    ctx, pg, lon, lat = _apri(browser, base, tmp_path)
    _genera(pg, lon, lat, S, EE, edificio="E-C", n=2)
    pg.click("#tegola")
    _clic_corpo(pg, "C1")
    attendi(pg, f"{S}.corpi.find((c) => c.id === 'C1').fonteTetto === 'falde'")
    assert "scende anche verso il cortile" in pg.text_content("#stato-tetti")
    _clic_corpo(pg, "C2")
    attendi(pg, f"{S}.corpi.find((c) => c.id === 'C2').fonteTetto === 'falde'")
    f = pg.evaluate(f"{S}.corpi.find((c) => c.id === 'C1').falde.map((x) => [x.orientamento, x.area_pianta, x.pendenza])")
    # orientamenti rispetto al nord vero: la griglia di EPSG:7791 (UTM 32) a 12,3° E è ruotata di circa 2°
    o = sorted(x[0] for x in f)
    assert len(f) == 8 and all(abs(a - b) <= 4 for a, b in zip(o, [0, 0, 90, 90, 180, 180, 270, 270])), f
    assert abs(sum(x[1] for x in f) - 1000) < 30 and all(x[2] == 22 for x in f), f
    c1 = pg.evaluate(f"(() => {{ const c = {S}.corpi.find((x) => x.id === 'C1'); return [c.tetto, c.colmo, c.inclinazione]; }})()")
    assert c1[0] == "padiglione" and abs(c1[1] - (12 + 5 * math.tan(math.radians(22)))) < 0.4, c1
    assert len(pg.evaluate(f"{S}.corpi.find((c) => c.id === 'C2').falde")) >= 4                  # corpo a L
    assert pg.evaluate(f"{S}.mappa.getSource('falde').serialize().data.features.length") > 30
    assert "tetto a falde scelto dall'utente (22°)" in pg.text_content("#tabella-falde")
    rep = pg.evaluate(f"{EE}.corpoReport()")
    assert len([x for x in rep["falde"] if x["corpo"] == "C1"]) == 8
    # area FV su una falda verso il cortile (lato sud del cortile: scende verso nord, orientamento 0)
    pg.evaluate("document.getElementById('tegola').click()")
    pg.evaluate("document.getElementById('aggiungi-fv').click()")
    pg.evaluate(f"""(() => {{ const c = {S}.corpi.find((x) => x.id === 'C1'), r = c.ring, x0 = Math.min(...r.map((p) => p[0])), y0 = Math.min(...r.map((p) => p[1]));
        const ll = {S}.proj.indietro([x0 + 20, y0 + 8.5]);
        {S}.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: {S}.mappa.project(ll) }}); }})()""")
    attendi(pg, f"{S}.aree.length === 1")
    a = pg.evaluate(f"[{S}.aree[0].corpo, {S}.aree[0].orientamento, {S}.aree[0].inclinazione, {S}.aree[0].montaggio]")
    assert a[0] == "C1" and (a[1] <= 4 or a[1] >= 356) and a[2:] == [22, "aderente"], a
    assert not pg.errori, pg.errori
    ctx.close()


def test_tegola_spenta_dalla_ricerca(browser, base, tmp_path):
    """Punto 2: la tegola si spegne con «Cerca l'indirizzo», «Cerca la particella», «Reset» e Invio nei campi."""
    ctx, pg, lon, lat = _apri(browser, base, tmp_path)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {S}.mappa && !!document.getElementById('cerca-reset') && !!document.getElementById('tegola').dataset.pronto", 30000)
    for azione in ("#cerca-indirizzo", "#cerca-particella", "#cerca-reset", "invio"):
        pg.click("#tegola")
        assert pg.get_attribute("#tegola", "aria-pressed") == "true"
        if azione == "invio":
            pg.fill("#cerca-via", "via Ovidio"); pg.focus("#cerca-via"); pg.keyboard.press("Enter")
        else:
            pg.click(azione)
        attendi(pg, "document.getElementById('tegola').getAttribute('aria-pressed') === 'false'", 5000)
        assert pg.evaluate(f"{S}.tegola") is False, azione
    assert not pg.errori, pg.errori
    ctx.close()


def test_maniglia_per_l_altezza_della_mappa(browser, base):
    """Punto 4: maniglia sotto la mappa (Modelli 3D, Fotovoltaico, Ortofoto): trascinandola la mappa cresce, MapLibre si
    adatta (canvas della stessa altezza), l'altezza resta dopo il ricaricamento; doppio clic: predefinita. In
    fv-producibilita la mappa non è più bassa di quella di Modelli 3D."""
    ctx, pg = pagina(browser)
    altezze = {}
    for nome, mid in (("modelli3d.html", "mappa3d"), ("fv-producibilita.html", "mappa3d"), ("ortofoto.html", "mappa-ortofoto")):
        pg.goto(base + nome)
        attendi(pg, f"!!document.querySelector('#{mid} canvas') && !!document.querySelector('#{mid} + .maniglia-mappa')", 30000)
        pg.wait_for_timeout(500)
        altezze[nome] = pg.evaluate(f"document.getElementById('{mid}').getBoundingClientRect().height")
        pg.evaluate(f"document.querySelector('#{mid} + .maniglia-mappa').scrollIntoView({{ block: 'center' }})")
        pg.wait_for_timeout(200)
        b = pg.locator(f"#{mid} + .maniglia-mappa").bounding_box()
        pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        pg.mouse.down(); pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2 + 120, steps=6); pg.mouse.up()
        pg.wait_for_timeout(400)
        h1 = pg.evaluate(f"document.getElementById('{mid}').getBoundingClientRect().height")
        assert abs(h1 - (altezze[nome] + 120)) < 4 or h1 == pg.evaluate("Math.round(innerHeight * 0.92)"), (nome, altezze[nome], h1)
        assert abs(pg.evaluate(f"document.querySelector('#{mid} canvas').getBoundingClientRect().height") - h1) < 2
        assert pg.evaluate(f"localStorage.getItem('altezza-mappa:{nome[:-5]}:{mid}')") == str(round(h1))
        pg.reload()
        attendi(pg, f"!!document.querySelector('#{mid} canvas')", 30000)
        pg.wait_for_timeout(400)
        assert abs(pg.evaluate(f"document.getElementById('{mid}').getBoundingClientRect().height") - h1) < 2
        pg.dblclick(f"#{mid} + .maniglia-mappa")
        pg.wait_for_timeout(300)
        assert pg.evaluate(f"localStorage.getItem('altezza-mappa:{nome[:-5]}:{mid}')") is None
    assert altezze["fv-producibilita.html"] >= altezze["modelli3d.html"] - 2, altezze
    assert not pg.errori, pg.errori
    ctx.close()


def test_clic_in_3d_sul_volume_piu_vicino(browser, base, tmp_path):
    """Punto 5: MapLibre trova i prismi estrusi sotto il puntatore (pareti e tetti), nell'ordine degli strati; la pagina
    sceglie il più vicino alla camera. Con la camera dalla parte del vicino V1 (alto 20 m) vince V1, dall'altra parte resta
    l'edificio scelto; vale anche per la tegola."""
    ctx, pg, lon, lat = _apri(browser, base, tmp_path)
    _genera(pg, lon, lat, S, EE, edificio="E-C", n=2)
    finto = f"""(bearing) => {{ const m = {S}.mappa, o = m.queryRenderedFeatures.bind(m);
        const c1 = {S}.corpi.find((x) => x.id === 'C1'), v1 = {S}.vicini.find((x) => x.id === 'V1');
        const g = (c) => ({{ type: 'Polygon', coordinates: [c.ring.map({S}.proj.indietro)] }});
        m.jumpTo({{ center: {S}.proj.indietro([-10, 0]), zoom: 18, pitch: 60, bearing }});
        m.queryRenderedFeatures = () => [{{ layer: {{ id: 'scelto' }}, properties: {{ id: 'C1' }}, geometry: g(c1) }},
                                         {{ layer: {{ id: 'corpi' }}, properties: {{ id: 'V1', edificio: 'E-V', altezza: 20 }}, geometry: g(v1) }}];
        setTimeout(() => {{ m.queryRenderedFeatures = o; }}, 50);
        m.fire('click', {{ lngLat: m.getCenter(), point: m.project(m.getCenter()) }}); }}"""
    pg.evaluate(f"({finto})(270)")             # camera a est: C1 più vicino → resta E-C
    pg.wait_for_timeout(600)
    assert pg.evaluate(f"{S}.edificio") == "E-C"
    pg.evaluate(f"({finto})(90)")              # camera a ovest, dalla parte di V1 → V1
    attendi(pg, f"{S}.edificio === 'E-V'", 15000)
    # MapLibre considera già il volume: un punto sullo schermo sopra la pianta di V1 (la sua parete) lo trova
    # (senza terreno: con il terreno in pendenza la quota delle tessere che arrivano sposta il punto sullo schermo)
    pg.evaluate(f"{S}.mappa.setTerrain(null); {S}.mappa.jumpTo({{ center: {S}.proj.indietro([0, 0]), zoom: 18.5, pitch: 70, bearing: 0 }})")
    conta = f"""(() => {{ const m = {S}.mappa, v = {S}.corpi[0], p = m.project({S}.proj.indietro(window.EUGENIO_EDIFICI.centroide(v.ring)));
        const ids = ['scelto', ...{S}.sorgentiCorpi].filter((i) => m.getLayer(i));
        return [m.queryRenderedFeatures([p.x, p.y], {{ layers: ids }}).length, m.queryRenderedFeatures([p.x, p.y - 60], {{ layers: ids }}).length]; }})()"""
    # si aspetta che la mappa abbia disegnato il prisma (con il container carico può servire più di un secondo)
    attendi(pg, f"(() => {{ const t = {conta}; return t[0] >= 1 && t[1] >= 1; }})()", 15000)   # 60 px sopra la pianta: la parete del prisma alto 20 m
    assert not pg.errori, pg.errori
    ctx.close()


def test_alberi_da_openstreetmap_dove_manca_il_lidar(browser, base, tmp_path):
    """Aggiunta di Paolo (14:27, «gli alberi di Cesena non ci sono»): dove la cella non ha il LiDAR la pagina chiede gli
    alberi indicativi OSM (/api/alberi/osm/<cella>.json), più chiari, dichiarati in nota, legenda e immagine; dove la cella
    ha il LiDAR vince il LiDAR (nessuna richiesta OSM per quella cella)."""
    _archivi_con_alberi(tmp_path)                    # LiDAR solo nella cella di CESENA
    ctx, pg = pagina(browser)
    chieste = []
    lo, la = CESENA

    def osm(r):
        n = r.request.url.split("/api/alberi/osm/")[1].split(".json")[0]
        chieste.append(n)
        i, j = (int(v) for v in n.split("_"))
        al = [[i * 0.01 + 0.002 + 0.0001 * k, j * 0.01 + 0.005, 10.0, None, 5.0] for k in range(5)]
        r.fulfill(status=200, content_type="application/json", body=json.dumps({"cella": n, "alberi": al, "stima": True,
                  "fonte": "© contributori OpenStreetMap (ODbL 1.0)", "licenza": "ODbL 1.0"}))
    pg.route("**/api/alberi/osm/**", osm)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && {M3D}.lidar && !!document.getElementById('strato-alberi')", 30000)
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{lo}, {la}], zoom: 17 }})")
    pg.check("#strato-alberi")
    attendi(pg, f"[...{M3D}.alberi.values()].some((a) => a[5] === 'osm')", 15000)
    assert _cella(lo, la) not in chieste and chieste                                    # vince il LiDAR nella sua cella
    assert pg.evaluate(f"[...{M3D}.alberi.values()].filter((a) => a[5] !== 'osm').length") == 13
    attendi(pg, "/indicative da OpenStreetMap/.test(document.getElementById('legenda-alberi').textContent)")
    # Bologna: nessun LiDAR, solo OSM
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [11.3426, 44.4949], zoom: 17 }})")
    attendi(pg, f"[...{M3D}.alberi.values()].some((a) => a[5] === 'osm' && Math.abs(a[1] - 44.495) < 0.01)", 15000)
    attendi(pg, "/chiome indicative da OpenStreetMap/.test(document.getElementById('messaggio').textContent)")
    assert not pg.errori, pg.errori
    ctx.close()


def test_tessere_occupate_non_fermano_la_fonte(browser, base):
    """Punto 1 (Sentinel-2 «non risponde, ferma per 30 s»; 503 a raffica delle particelle): «occupata» non ferma la fonte
    e non scrive la nota; gli errori veri della fonte delle particelle fermano solo le particelle, con la nota; nessuna
    riga rossa nostra (le tessere d'errore sono risposte 200)."""
    from PIL import Image
    b = io.BytesIO(); Image.new("RGBA", (256, 256), (0, 0, 0, 0)).save(b, "PNG"); vuota = b.getvalue()
    ctx, pg = pagina(browser)
    rossi = []
    pg.on("console", lambda m: rossi.append(m.text) if m.type == "error" else None)
    h = lambda mot, fid: {"Content-Type": "image/png", "X-Ortofoto-Errore": mot, "X-Ortofoto-Fonte": fid, "Retry-After": "20",
                          "Cache-Control": "no-store", "Access-Control-Expose-Headers": "X-Ortofoto-Errore, X-Ortofoto-Fonte, Retry-After"}
    pg.route(re.compile(r".*/api/ortofoto/(rer2023|s2cloudless2016)/\d.*"), lambda r: r.fulfill(status=200, body=vuota, headers=h("occupata", "rer2023" if "rer2023" in r.request.url else "s2cloudless2016")))
    _con_strati(pg)
    pg.route(re.compile(r".*/api/ortofoto/strati/catasto/\d.*"), lambda r: r.fulfill(status=200, body=vuota, headers={**h("fonte", "catasto"), "X-Strato": "catasto"}))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!{M3D}.ortofoto", 30000)
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{CESENA[0]}, {CESENA[1]}], zoom: 18 }})")
    pg.wait_for_timeout(2500)
    g = pg.evaluate("Object.fromEntries(Object.entries(window.EUGENIO_LIMITI.guasti).map(([k, v]) => [k, v.fino > Date.now()]))")
    assert not any(v for k, v in g.items() if k.startswith("ortofoto:")), g             # «occupata» non ferma la fonte
    if pg.locator("#caselle-strati input").count():
        pg.locator("#caselle-strati input").first.check()
        attendi(pg, "/la fonte non risponde/.test((document.getElementById('nota-limiti') || {}).textContent || '')", 20000)
        assert "Particelle catastali" in pg.text_content("#nota-limiti")
    assert not [x for x in rossi if "/api/" in x], rossi
    assert not pg.errori, pg.errori
    ctx.close()


def test_indicatore_di_caricamento_delle_tessere(browser, base):
    """Aggiunta delle 15:49: con tessere lente l'orologio «Carico le tessere… (N)» compare sulla mappa (dopo 400 ms, con
    aria-live), dopo 3 s dice la fonte lenta, poi sparisce quando le tessere sono arrivate; non entra nel PNG (è HTML sopra
    la mappa); con prefers-reduced-motion la lancetta non gira."""
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (256, 256), (90, 120, 80)).save(b, "JPEG"); foto = b.getvalue()
    ctx, pg = pagina(browser)
    lenta, sospese = {"si": True}, []

    def tessera(r):            # tessere AGEA «lente»: si tengono in sospeso e si rispondono più tardi
        if lenta["si"]:
            sospese.append(r)
        else:
            r.fulfill(status=200, body=foto, headers={"Content-Type": "image/jpeg", "X-Ortofoto-Fonte": "pcn2012"})
    pg.route(re.compile(r".*/api/ortofoto/pcn2012/\d.*"), tessera)
    pg.route(re.compile(r".*/api/ortofoto/(rer2023|s2cloudless2016)/\d.*"), lambda r: r.fulfill(status=200, body=foto, headers={"Content-Type": "image/jpeg"}))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!document.querySelector('#mappa3d .carico-mappa')", 30000)
    el = "#mappa3d .carico-mappa"
    assert pg.get_attribute(el, "aria-live") == "polite" and pg.get_attribute(el, "role") == "status"
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [12.2563, 45.8537], zoom: 17 }})")          # Susegana: AGEA, lenta
    attendi(pg, "[...document.querySelectorAll('#sfondo-ortofoto option')].some((o) => o.value === 'pcn2012')")
    pg.select_option("#sfondo-ortofoto", "pcn2012")
    attendi(pg, f"!document.querySelector('{el}').hidden && /Carico le tessere… \\(\\d+\\)/.test(document.querySelector('{el}').textContent)", 10000)
    attendi(pg, f"/Ortofoto «Geoportale Nazionale \\(solo consultazione\\)»: risposta lenta/.test(document.querySelector('{el}').textContent)", 10000)
    lenta["si"] = False
    for r in sospese:
        try:
            r.fulfill(status=200, body=foto, headers={"Content-Type": "image/jpeg", "X-Ortofoto-Fonte": "pcn2012"})
        except Exception:  # noqa: BLE001 - richiesta già annullata dalla mappa
            pass
    attendi(pg, f"document.querySelector('{el}').hidden", 30000)
    # «Genera il 3D»: lavoro lungo segnalato sulla mappa
    pg.evaluate("window.__fine = window.EUGENIO_LIMITI.lavoro('Genero il 3D…'); 1")
    attendi(pg, f"/Genero il 3D/.test(document.querySelector('{el}').textContent) && !document.querySelector('{el}').hidden", 15000)
    pg.evaluate("window.__fine(); 1")
    attendi(pg, f"document.querySelector('{el}').hidden", 15000)
    # niente lampeggi: una tessera veloce non fa comparire l'indicatore
    pg.evaluate(f"{M3D}.mappa.panBy([40, 0], {{ duration: 0 }})")
    pg.wait_for_timeout(300)
    assert pg.is_hidden(el)
    # fuori dal PNG: l'indicatore è HTML, l'immagine copia solo la tela della mappa
    assert pg.evaluate(f"document.querySelector('{el}').parentElement === {M3D}.mappa.getContainer() && document.querySelector('{el}').tagName") == "DIV"
    pg.emulate_media(reduced_motion="reduce")
    assert pg.evaluate(f"getComputedStyle(document.querySelector('{el} .carico-clessidra')).animationName") == "none"
    assert not pg.errori, pg.errori
    ctx.close()
