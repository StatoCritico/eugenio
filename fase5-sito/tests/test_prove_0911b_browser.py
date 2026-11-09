"""Prove nel browser delle correzioni del 09/11/2026 b (prove N10 di Paolo, punti 1–6): ricerca con un solo Comune e un
solo «Reset» (il pulsante usa solo i suoi campi, mai un risultato in un altro comune), «Colore» e «Alberi» sotto la mappa
accanto ad «Azzera», celle LiDAR chieste solo se esistono (nessun 404), terreno in rilievo con gli edifici OSM o le sagome
regionali con la quota (Copernicus), fonti di ortofoto con tessere segnaposto saltate da sole. Rotte /api simulate, nessuna
rete; si salta senza Playwright o Chromium."""
from __future__ import annotations

import io
import json
import math
import re

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import (FONTI, _diciannove_comuni, _servi_archivio, attendi, base, browser, pagina,  # noqa: E402,F401
                                webgl)

M3D = "window.EUGENIO_EDIFICIO3D.stato"
E = "window.EUGENIO_EDIFICIO3D"
BAGNO_54_216 = (11.99140, 43.88922)            # particella foglio 54 n. 216 (DBTR di Bagno di Romagna)
SUSEGANA = (12.2563, 45.8537)


def _riga_csv(post: str) -> str:
    """La riga dei dati del CSV mandato a /api/patrimonio (multipart)."""
    return next(x for x in post.replace("\r", "").split("\n") if x.startswith("1;ricerca;"))


@pytest.mark.parametrize("nome,larghezza", [("modelli3d.html", 1366), ("ortofoto.html", 1366), ("modelli3d.html", 375)])
def test_ricerca_con_un_solo_comune_e_un_solo_reset(browser, base, nome, larghezza):
    """Punto 3: Comune una volta sola in cima, poi Indirizzo, Foglio e Particella affiancati, poi «Cerca l'indirizzo»,
    «Cerca la particella» e un solo «Reset» che svuota tutto; a 375 px nessuno scorrimento di lato."""
    ctx, pg = pagina(browser, larghezza=larghezza)
    pg.goto(base + nome)
    attendi(pg, "!!document.getElementById('cerca-luogo-modulo')", 30000)
    assert pg.locator("#cerca-comune").count() == 1 and pg.locator("#catasto-comune").count() == 0
    assert pg.locator(".cerca-reset").count() == 1 and pg.locator("#cerca-luogo-modulo form").count() == 0
    ids = pg.evaluate("[...document.querySelectorAll('#cerca-luogo-modulo input, #cerca-luogo-modulo button')].map((x) => x.id)")
    assert ids == ["cerca-comune", "cerca-via", "catasto-foglio", "catasto-particella", "cerca-indirizzo", "cerca-particella", "cerca-reset"], ids
    pos = pg.evaluate("""(() => Object.fromEntries(['cerca-comune', 'cerca-via', 'catasto-foglio', 'catasto-particella', 'cerca-indirizzo',
        'cerca-particella', 'cerca-reset'].map((i) => { const r = document.getElementById(i).getBoundingClientRect(); return [i, [r.top, r.left, r.right]]; })))()""")
    assert pos["cerca-comune"][0] < pos["cerca-via"][0] < pos["catasto-foglio"][0] < pos["cerca-indirizzo"][0]
    assert abs(pos["catasto-foglio"][0] - pos["catasto-particella"][0]) < 2 and pos["catasto-foglio"][2] < pos["catasto-particella"][1]
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    for i, v in (("#cerca-comune", "Bagno di Romagna"), ("#cerca-via", "via San Salvatore"), ("#catasto-foglio", "54"), ("#catasto-particella", "216")):
        pg.fill(i, v)
    pg.click("#cerca-reset")
    assert [pg.input_value(x) for x in ("#cerca-comune", "#cerca-via", "#catasto-foglio", "#catasto-particella")] == ["", "", "", ""]
    assert not pg.errori, pg.errori
    ctx.close()


def test_ogni_pulsante_usa_solo_i_suoi_campi_e_mai_un_altro_comune(browser, base):
    """Punto 3 e 4 (Bagno di Romagna finito a Susegana): con tutti i campi pieni «Cerca la particella» manda solo Comune,
    Foglio e Particella; «Cerca l'indirizzo» solo Comune e Indirizzo; un risultato in un altro comune (Zornade trova «via San
    Salvatore 13, Susegana») non sposta la mappa lì ma al centro del comune scritto, con l'avviso; Invio nel campo della
    particella cerca la particella."""
    ctx, pg = pagina(browser)
    mandati = []
    risposte = {
        "particella": {"righe": [{"id": "1", "lat": BAGNO_54_216[1], "lon": BAGNO_54_216[0], "esito": "ok", "fonte_punto": "catasto",
                                  "comune_catasto": "BAGNO DI ROMAGNA", "foglio_catasto": "54", "mappale": "216", "nota": ""}]},
        "indirizzo": {"righe": [{"id": "1", "lat": SUSEGANA[1], "lon": SUSEGANA[0], "esito": "verificare", "fonte_punto": "Zornade",
                                 "indirizzo_trovato": "VIA SAN SALVATORE 13", "comune_catasto": "SUSEGANA", "foglio_catasto": "33", "mappale": "149",
                                 "nota": "comune catastale SUSEGANA diverso da quello indicato"}]}}

    def patrimonio(r):
        riga = _riga_csv(r.request.post_data or "")
        mandati.append(riga)
        tipo = "indirizzo" if riga.split(";")[2] else "particella"
        r.fulfill(status=200, content_type="application/json", body=json.dumps(risposte[tipo]))
    pg.route("**/api/patrimonio", patrimonio)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!document.getElementById('cerca-comune')", 30000)
    pg.fill("#cerca-comune", "bagno di romagna"); pg.fill("#cerca-via", "via san salvatore")
    pg.fill("#catasto-foglio", "54"); pg.fill("#catasto-particella", "216")
    pg.click("#cerca-particella")
    attendi(pg, f"/foglio 54, 216/.test(document.getElementById('messaggio-cerca').textContent) && !{M3D}.mappa.isMoving()")
    assert mandati == ["1;ricerca;;;bagno di romagna;54;216"], mandati
    c = pg.evaluate(f"(() => {{ const c = {M3D}.mappa.getCenter(); return [c.lng, c.lat]; }})()")
    assert abs(c[0] - BAGNO_54_216[0]) < 1e-3 and abs(c[1] - BAGNO_54_216[1]) < 1e-3, c
    pg.click("#cerca-indirizzo")
    attendi(pg, "/centro del comune di Bagno di Romagna/.test(document.getElementById('messaggio-cerca').textContent)")
    assert mandati[-1] == "1;ricerca;via san salvatore;;bagno di romagna;;", mandati
    msg = pg.text_content("#messaggio-cerca")
    assert "nel comune di SUSEGANA, non in quello scritto (bagno di romagna)" in msg, msg
    pg.wait_for_timeout(1300)
    c = pg.evaluate(f"(() => {{ const c = {M3D}.mappa.getCenter(); return [c.lng, c.lat]; }})()")
    assert abs(c[1] - 43.84) < 0.1 and abs(c[0] - 11.96) < 0.1, c                     # Bagno di Romagna, non Susegana
    pg.focus("#catasto-particella"); pg.keyboard.press("Enter")
    attendi(pg, "/foglio 54, 216/.test(document.getElementById('messaggio-cerca').textContent)")
    assert mandati[-1] == "1;ricerca;;;bagno di romagna;54;216" and len(mandati) == 3, mandati
    assert not pg.errori, pg.errori
    ctx.close()


def _demo_nascosta(pg):
    pg.evaluate("['apri-demo', 'esci-demo', 'torna-2d'].forEach((i) => { const e = document.getElementById(i); if (e) e.hidden = true; })")
    pg.wait_for_timeout(200)


@pytest.mark.parametrize("larghezza", [1366, 375])
def test_colore_e_alberi_sotto_la_mappa_accanto_ad_azzera(browser, base, larghezza):
    """Punto 2: «Colore» (degli edifici) e «Alberi» sotto la mappa, nella riga di «Genera il 3D», dopo le frecce, lo stato
    dell'ortofoto e «Azzera»; non più nel pannello di destra. A 1366 px tutto su una riga; a 375 px vanno a capo in ordine,
    senza scorrimento di lato."""
    ctx, pg = pagina(browser, larghezza=larghezza)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, "!!document.querySelector('#comandi-edificio #colore-edifici') && !!document.querySelector('#sposta-ortofoto .sposta-azzera')", 30000)
    _demo_nascosta(pg)
    assert pg.evaluate("document.getElementById('aspetto-3d').parentElement.id") == "comandi-edificio"
    assert pg.evaluate("!document.querySelector('.pannello #colore-edifici') && !document.querySelector('.pannello #strato-alberi')")
    assert pg.evaluate("[...document.getElementById('comandi-edificio').children].filter((e) => !e.hidden).map((e) => e.id)") == \
        ["genera-3d", "sposta-ortofoto", "aspetto-3d"]
    r = pg.evaluate("""(() => Object.fromEntries([['frecce', '#sposta-ortofoto .freccia'], ['azzera', '#sposta-ortofoto .sposta-azzera'],
        ['colore', '#colore-edifici .vestito-pulsante'], ['alberi', '.casella-alberi'], ['genera', '#genera-3d']].map(([k, s]) => {
        const b = document.querySelector(s).getBoundingClientRect(); return [k, [b.top + b.height / 2, b.left, b.right]]; })))()""")
    assert r["azzera"][2] <= r["colore"][1] or r["colore"][0] > r["azzera"][0] + 10, r      # dopo «Azzera» (o sotto)
    assert r["colore"][2] < r["alberi"][1] and abs(r["colore"][0] - r["alberi"][0]) < 6, r
    if larghezza >= 1366:
        centri = [r[k][0] for k in ("genera", "frecce", "azzera", "colore", "alberi")]
        assert max(centri) - min(centri) <= 6, r
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert pg.evaluate("[...document.querySelectorAll('#comandi-edificio *')].every((e) => e.getBoundingClientRect().right <= innerWidth + 1)")
    assert pg.get_attribute("#colore-edifici .vestito-pulsante", "aria-label") == "Colore degli edifici: Grigio"
    assert not pg.errori, pg.errori
    ctx.close()


def _con_lidar(radice, celle):
    """19 archivi finti (con `nomi_celle`, come quelli veri) e l'indice LiDAR dell'ER (con o senza l'elenco delle celle)."""
    dati = _diciannove_comuni(radice)
    for ind in radice.glob("cc-by/er/*/prodotti/indice.json"):
        d = json.loads(ind.read_text(encoding="utf-8"))
        d["nomi_celle"] = sorted(p.stem for p in (ind.parent / "contesto").glob("*.json"))
        ind.write_text(json.dumps(d), encoding="utf-8")
    aj = json.loads((radice / "archivi.json").read_text(encoding="utf-8"))
    aj["lidar"] = "/edifici3d/cc-by/er/prodotti/"
    (radice / "archivi.json").write_text(json.dumps(aj), encoding="utf-8")
    lid = radice / "cc-by" / "er" / "prodotti" / "lidar"
    (lid / "falde").mkdir(parents=True)
    ind = {"cella": 0.01, "attribuzioni": {"rer": {"descrizione": "LiDAR RER", "licenza": "CC BY 4.0", "attribuzione": "Regione Emilia-Romagna"}}, "zone": {}}
    if celle is not None:
        ind["celle"] = {"falde": celle, "alberi": []}
    for n in celle or []:
        (lid / "falde" / f"{n}.json").write_text(json.dumps({"cella": n, "corpi": {}}), encoding="utf-8")
    (lid / "indice.json").write_text(json.dumps(ind), encoding="utf-8")
    return dati


@pytest.mark.parametrize("con_elenco", [True, False])
def test_celle_lidar_solo_quelle_che_esistono(browser, base, tmp_path, con_elenco):
    """Punto 1 (righe rosse in Console): la pagina chiede `lidar/falde/<cella>.json` e `lidar/alberi/<cella>.json` solo per
    le celle dell'elenco di `lidar/indice.json`; senza elenco (indice di prima) solo dentro gli archivi dell'Emilia-Romagna,
    mai a Roma o in Veneto. Con l'elenco nessuna risposta 404 da /edifici3d/ in tutto il giro (Cesena, Roma, Susegana)."""
    from pathlib import Path
    punti = json.loads((Path(__file__).parent / "punti_19_comuni.json").read_text(encoding="utf-8"))
    cesena = tuple(punti["cesena"]["punti"][0])
    cella = f"{math.floor(cesena[0] / 0.01)}_{math.floor(cesena[1] / 0.01)}"
    _con_lidar(tmp_path, [cella] if con_elenco else None)
    ctx, pg = pagina(browser)
    lidar, errori_404 = [], []
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/edifici/osm?*", lambda r: r.fulfill(status=200, content_type="application/json",
             body=json.dumps({"type": "FeatureCollection", "features": [], "corpi": 0})))
    pg.on("request", lambda r: lidar.append(r.url.split("/lidar/")[1]) if re.search(r"/lidar/(falde|alberi)/", r.url) else None)
    # (gli archivi finti non hanno corpi.pmtiles: quelli veri sì)
    pg.on("response", lambda r: errori_404.append(r.url) if "/edifici3d/" in r.url and r.status >= 400 and not r.url.endswith(".pmtiles") else None)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.lidar && {M3D}.archivi.filter((a) => !a.osm).length === 19", 30000)
    for lon, lat in (cesena, (12.4964, 41.8945), SUSEGANA):
        pg.evaluate(f"(() => {{ {M3D}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }}); {E}.impostaPunto({lon}, {lat}, 'clic'); return {E}.puntoCambiato(); }})()")
        pg.wait_for_timeout(1200)
    if con_elenco:
        assert lidar == [f"falde/{cella}.json"], lidar                    # una sola cella, quella che c'è; nessun albero
    else:
        assert lidar and all(re.match(r"(falde|alberi)/12\d\d_44\d\d\.json$", x) for x in lidar), lidar   # solo attorno a Cesena
    if con_elenco:
        assert errori_404 == [], errori_404
    assert not pg.errori, pg.errori
    ctx.close()


def _terreno_copernicus(quota=70.0):
    """Tessere Terrarium che salgono verso nord, con X-Terreno-Fonte: copernicus (fuori dai DTM regionali)."""
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
            h = np.broadcast_to(np.clip(quota + (lat - SUSEGANA[1]) * 111000 * 0.2, 0, 3000), (256, 256)) + 32768
            rgb = np.zeros((256, 256, 3), dtype="uint8"); rgb[..., 0] = (h // 256).astype("uint8"); rgb[..., 1] = (h % 256).astype("uint8")
            b = io.BytesIO(); Image.fromarray(rgb, "RGB").save(b, format="PNG"); cache[(z, x, y)] = b.getvalue()
        return r.fulfill(status=200, body=cache[(z, x, y)], headers={"Content-Type": "image/png", "X-Terreno-Fonte": "copernicus",
                                                                     "Access-Control-Expose-Headers": "X-Terreno-Fonte"})
    return terreno


def test_susegana_in_rilievo_con_le_quote_copernicus(browser, base, tmp_path):
    """Punto 5 («c'è ma è piatta»): fuori dai DTM regionali il server dà ai corpi OSM la quota del Copernicus DEM: la pagina
    accende il terreno (non più piatto), la legenda dice Copernicus e l'esagerazione ×1,5 e ×2 funziona."""
    _diciannove_comuni(tmp_path)
    lon0, lat0 = SUSEGANA
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574

    def q(i, dx, dy, w, hh, quota):
        r = [[lon0 + (dx + a) / kx, lat0 + (dy + b) / ky] for a, b in [(0, 0), (w, 0), (w, hh), (0, hh), (0, 0)]]
        return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [r]},
                "properties": {"id": i, "edificio": i, "gronda": 7.0, "altezza": 7.0, "fonte_sagoma": "OpenStreetMap", "licenza": "ODbL 1.0",
                               "fonte_altezza": "OSM building:levels × 3 m", "tetto": "piano", "uso": "residenziale", "quota_terreno": quota}}
    risposta = {"type": "FeatureCollection", "features": [q("w1", 0, 0, 16, 10, 70.9), q("w2", 30, 0, 12, 12, 71.1)], "corpi": 2,
                "licenza": "ODbL 1.0", "centro": [round(lon0, 3), round(lat0, 3)], "raggio": 400, "quote_dtm": 2, "quote_fonte": "copernicus",
                "scheda": "https://www.openstreetmap.org/copyright", "nota": "Ripiego"}
    ctx, pg = pagina(browser)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_copernicus())
    pg.route("**/api/edifici/osm?*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(risposta)))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.osmAttivo && {M3D}.mappa.getSource('terreno')", 30000)
    lon, lat = lon0 + 8 / kx, lat0 + 5 / ky
    pg.evaluate(f"(() => {{ {M3D}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }}); {E}.impostaPunto({lon}, {lat}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{M3D}.daGenerare && {M3D}.daGenerare.edificio === 'w1'", 25000)
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{M3D}.in3d && {M3D}.corpi.length === 1 && !!{M3D}.mappa.getTerrain()", 25000)
    assert "Quote dei corpi dal terreno del server (DTM regionale o, dove manca, Copernicus DEM 90 m)." in pg.text_content("#messaggio")
    attendi(pg, "/Terreno: Copernicus DEM GLO-90/.test(document.getElementById('legenda-terreno').textContent)")
    for x in (1.5, 2, 1):
        pg.evaluate(f"{E}.esagera({x})")
        assert pg.evaluate(f"{M3D}.mappa.getTerrain().exaggeration") == x
    assert abs(pg.evaluate(f"{M3D}.mappa.getCenterElevation()") - 70.9) < 15
    assert not pg.errori, pg.errori
    ctx.close()


def test_fonte_con_tessere_segnaposto_saltata_da_sola(browser, base):
    """Punto 6 (scritte «Fonte dei dati: Regione Toscana…» sul terreno bianco): a Bagno di Romagna la RER non ha immagini e
    la Toscana risponde fuori dalla regione con tessere segnaposto, che il server dichiara vuote (X-Ortofoto-Vuota): la
    pagina passa da sola ad AGEA 2012 e lo scrive."""
    fonti = json.loads(json.dumps(FONTI))
    fonti["fonti"].insert(1, {"id": "toscana2023", "nome": "Ortofoto Regione Toscana 2023 (20 cm)", "licenza": "CC BY 4.0",
                              "citazione": "Regione Toscana – Ortofoto 2023, 20 cm (CC BY 4.0)", "scheda": "https://geodati.gov.it/",
                              "stato": "confermata", "copia": True, "nei_report": True, "zoom": [12, 20], "riquadro": [9.68, 42.23, 12.38, 44.48],
                              "tessere": "/api/ortofoto/toscana2023/{z}/{x}/{y}.jpg?s=1", "spostabile": True, "spostamento_max": 20})
    ordine = {"rer2023": 1, "toscana2023": 1, "pcn2012": 8, "s2cloudless2016": 9}          # come il server: priorità, poi id
    fonti["fonti"].sort(key=lambda f: (ordine[f["id"]], f["id"]))
    from PIL import Image
    b = io.BytesIO(); Image.new("RGBA", (256, 256), (0, 0, 0, 0)).save(b, "PNG"); vuota = b.getvalue()
    b = io.BytesIO(); Image.new("RGB", (256, 256), (90, 120, 80)).save(b, "JPEG"); foto = b.getvalue()
    ctx, pg = pagina(browser)
    pg.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(fonti)))
    hv = {"X-Ortofoto-Vuota": "1", "Access-Control-Expose-Headers": "X-Ortofoto-Vuota"}
    pg.route(re.compile(r".*/api/ortofoto/(rer2023|toscana2023)/.*"), lambda r: r.fulfill(status=200, body=vuota, headers={"Content-Type": "image/png", **hv}))
    pg.route(re.compile(r".*/api/ortofoto/pcn2012/.*"), lambda r: r.fulfill(status=200, body=foto, headers={"Content-Type": "image/jpeg"}))
    lo, la = BAGNO_54_216
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!{M3D}.ortofoto", 30000)
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{lo}, {la}], zoom: 17 }})")
    attendi(pg, f"{M3D}.ortofoto && {M3D}.ortofoto.id === 'pcn2012'", 30000)
    assert pg.input_value("#sfondo-ortofoto") == "pcn2012"
    attendi(pg, "/non ha immagini in questa zona: uso «Geoportale Nazionale/.test(document.getElementById('messaggio-cerca').textContent)")
    assert {"rer2023", "toscana2023"} <= set(pg.evaluate(f"[...{M3D}.vuote].map((k) => k.split('@')[0])"))
    assert not pg.errori, pg.errori
    ctx.close()
