"""Prove nel browser delle correzioni del 09/11/2026 c (prove P9 di Paolo, punti 1–5 e modifiche delle 11:56): alberi di
nuovo visibili, tetti tutti piani in partenza e «(4) Coperture» con la tegola (piano ↔ falde all'inclinazione scelta,
ricordati nel browser, «Reset piani» con conferma nella pagina, esporta e importa), niente più «Rilievo ×1 ×1,5 ×2», fonte
dell'ortofoto scelta da sola tra quelle applicabili nel punto (Firenze, Susegana, Cesena, Bologna), nota quando una fonte
non risponde, nessuna tessera oltre lo zoom massimo della fonte. Rotte /api simulate, nessuna rete; si salta senza
Playwright o Chromium."""
from __future__ import annotations

import io
import json
import math
import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from test_mappe_browser import (FONTI, _diciannove_comuni, _servi_archivio, attendi, base, browser, pagina,  # noqa: E402,F401
                                webgl)

M3D = "window.EUGENIO_EDIFICIO3D.stato"
E = "window.EUGENIO_EDIFICIO3D"
PUNTI = json.loads((Path(__file__).parent / "punti_19_comuni.json").read_text(encoding="utf-8"))
CESENA = tuple(PUNTI["cesena"]["punti"][0])


def _cella(lon, lat):
    return f"{math.floor(lon / 0.01)}_{math.floor(lat / 0.01)}"


def _archivi_con_alberi(radice, edificio_grande=False):
    """19 archivi finti con `nomi_celle`, indice LiDAR dell'ER con l'elenco delle celle e una cella di alberi attorno al
    punto di Cesena (come quella della pipeline: [lon, lat, h, quota, lato])."""
    dati = _diciannove_comuni(radice)
    for ind in radice.glob("cc-by/er/*/prodotti/indice.json"):
        d = json.loads(ind.read_text(encoding="utf-8"))
        d["nomi_celle"] = sorted(p.stem for p in (ind.parent / "contesto").glob("*.json"))
        ind.write_text(json.dumps(d), encoding="utf-8")
    if edificio_grande:            # corpo di 20 × 10 m (il corpo di prova è di 4 m: troppo piccolo per un tetto a falde)
        lo, la = CESENA
        kx, ky = 111320 * math.cos(math.radians(la)), 110574
        p = radice / "cc-by" / "er" / "cesena" / "prodotti" / "contesto" / f"{_cella(lo, la)}.json"
        fc = json.loads(p.read_text(encoding="utf-8"))
        def corpo(i, dx, dy, w, hh, gronda):
            r = [[lo + (dx + a) / kx, la + (dy + b) / ky] for a, b in [(-w / 2, -hh / 2), (w / 2, -hh / 2), (w / 2, hh / 2), (-w / 2, hh / 2), (-w / 2, -hh / 2)]]
            return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [r]},
                    "properties": {"id": i, "edificio": i, "gronda": gronda, "colmo": gronda + 4, "tetto": "piano", "quota_terreno": 10,
                                   "fonte_sagoma": "DBTR Emilia-Romagna – UVL", "fonte_altezza": "DBTR H_UVL", "licenza": "CC BY 4.0"}}
        fc["features"] = [corpo("cesena-0", 0, 0, 20, 10, 9), corpo("cesena-v1", 40, 0, 16, 9, 7)] + fc["features"][1:]
        p.write_text(json.dumps(fc), encoding="utf-8")
    aj = json.loads((radice / "archivi.json").read_text(encoding="utf-8"))
    aj["lidar"] = "/edifici3d/cc-by/er/prodotti/"
    (radice / "archivi.json").write_text(json.dumps(aj), encoding="utf-8")
    lid = radice / "cc-by" / "er" / "prodotti" / "lidar"
    (lid / "alberi").mkdir(parents=True)
    lo, la = CESENA
    alberi = [[lo + 0.00012 * i, la + 0.00025, 9.0 + i, 10.0, 2.0] for i in range(-6, 7)]
    n = _cella(lo, la)
    (lid / "alberi" / f"{n}.json").write_text(json.dumps({"cella": n, "crs": "EPSG:4326", "campi": ["lon", "lat", "h", "quota", "lato"],
                                                          "tessere": {"T1": alberi}}), encoding="utf-8")
    ind = {"cella": 0.01, "attribuzioni": {"rer": {"descrizione": "LiDAR RER", "licenza": "CC BY 4.0", "attribuzione": "Regione Emilia-Romagna"}},
           "zone": {}, "celle": {"falde": [], "alberi": [n]}}
    (lid / "indice.json").write_text(json.dumps(ind), encoding="utf-8")
    return dati


def _apri_e_genera(pg, base, tmp_path, pagina_html="modelli3d.html", lon=None, lat=None):
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/edifici/osm?*", lambda r: r.fulfill(status=200, content_type="application/json",
             body=json.dumps({"type": "FeatureCollection", "features": [], "corpi": 0})))
    pg.goto(base + pagina_html)
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && {M3D}.archivi.filter((a) => !a.osm).length === 19", 30000)
    lon, lat = lon or CESENA[0], lat or CESENA[1]
    pg.evaluate(f"(() => {{ {M3D}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 18 }}); {E}.impostaPunto({lon}, {lat}, 'clic'); return {E}.puntoCambiato(); }})()")
    attendi(pg, f"{M3D}.daGenerare && {M3D}.daGenerare.edificio === 'cesena-0'", 25000)
    pg.evaluate("document.getElementById('genera-3d').click()")
    attendi(pg, f"{M3D}.in3d && {M3D}.corpi.length === 1", 25000)


def test_alberi_visibili_a_cesena(browser, base, tmp_path):
    """Punto 3: con la casella «Alberi» le chiome del LiDAR (cella dell'elenco di lidar/indice.json) si vedono nella vista 3D."""
    _archivi_con_alberi(tmp_path)
    ctx, pg = pagina(browser)
    _apri_e_genera(pg, base, tmp_path)
    assert pg.evaluate(f"{M3D}.alberi.size") == 13
    pg.check("#strato-alberi")
    attendi(pg, f"{M3D}.mappa.getLayoutProperty('alberi', 'visibility') === 'visible'")
    attendi(pg, f"{M3D}.mappa.querySourceFeatures('alberi').length > 0", 10000)
    assert not pg.is_hidden("#legenda-alberi")
    assert not pg.errori, pg.errori
    ctx.close()


def test_alberi_anche_nella_mappa_2d(browser, base, tmp_path):
    """Punto 3: con «Alberi» acceso le chiome si vedono anche nella mappa 2D (da zoom 15) attorno al centro."""
    _archivi_con_alberi(tmp_path)
    ctx, pg = pagina(browser)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && {M3D}.lidar && !!document.getElementById('strato-alberi')", 30000)
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{CESENA[0]}, {CESENA[1]}], zoom: 17 }})")
    pg.check("#strato-alberi")
    attendi(pg, f"{M3D}.mappa.getLayoutProperty('alberi-2d', 'visibility') === 'visible' && {M3D}.mappa.querySourceFeatures('alberi').length >= 13", 15000)
    assert not pg.errori, pg.errori
    ctx.close()


# ------------------------------------------------------------------ coperture: tegola, inclinazione, reset, esporta e importa
from test_mappe_browser import _archivio_tetti, _clic_su_corpo, _con_strati, _genera, _terreno_in_pendenza  # noqa: E402

S, EE = "window.EUGENIO_EDIFICIO3D.stato", "window.EUGENIO_EDIFICIO3D"


def _apri_tetti(browser, base, tmp_path, ctx=None):
    lon, lat = _archivio_tetti(tmp_path)
    if ctx is None:
        ctx, pg = pagina(browser)
    else:
        pg = ctx.new_page(); pg.errori = []; pg.on("pageerror", lambda e: pg.errori.append(str(e)))
        pg.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI)))
        pg.route("**/api/**", lambda r: r.fallback() if r.request.url.endswith("/api/ortofoto/fonti") else r.fulfill(status=404, body="{}"))
    _con_strati(pg)
    pg.route(re.compile(r"^http://127\.0\.0\.1:\d+/edifici3d/"), _servi_archivio(tmp_path))
    pg.route("**/api/terreno/**", _terreno_in_pendenza(lat))
    # confirm() del browser vietato (in passato ha bloccato Chrome): la conferma è nella pagina
    pg.add_init_script("window.confirm = () => { throw new Error('confirm() non si usa'); };")
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    return ctx, pg, lon, lat


def test_coperture_tra_edificio_e_corpi_senza_rilievo(browser, base):
    """Modifiche di Paolo delle 11:56: «(4) Coperture» tra «(3) Edificio» e «(5) Corpi» nel pannello di destra (tegola,
    Inclinazione 22°, «Reset piani», «Esporta tetti», «Importa tetti», riga di stato), in tutte le pagine 3D; sotto la
    mappa restano frecce, stato, Azzera, Colore e Alberi; niente più riga «Rilievo ×1 ×1,5 ×2»."""
    ctx, pg = pagina(browser)
    for nome in ("modelli3d.html", "fv-producibilita.html", "edificio-geometria.html"):
        pg.goto(base + nome)
        attendi(pg, "window.EUGENIO_EDIFICIO3D && !!window.EUGENIO_EDIFICIO3D.stato.mappa && !!document.getElementById('tegola').dataset.pronto", 30000)
        passi = pg.evaluate("[...document.querySelectorAll('.pannello .passo')].map((p) => [p.id, p.querySelector('h2').textContent.trim()])")
        ids = [p[0] for p in passi]
        assert ids[ids.index("passo-edificio") + 1] == "passo-coperture" and ids[ids.index("passo-coperture") + 1] == "passo-corpi", ids
        d = dict(passi)
        assert d["passo-edificio"] == "3Edificio" and d["passo-coperture"] == "4Coperture" and d["passo-corpi"] == "5Corpi", passi
        assert pg.get_attribute("#tegola", "title") == "Tetto a falde: clic su un edificio per cambiarlo"
        assert pg.locator("#tegola svg.icona-tegola").count() == 1 and pg.input_value("#inclinazione-tetti") == "22"
        for x in ("#reset-piani", "#esporta-tetti", "#importa-tetti", "#stato-tetti"):
            assert pg.locator(f"#passo-coperture {x}").count() == 1, x
        assert pg.is_hidden("#conferma-reset")
        assert pg.locator("#comandi-edificio #tegola").count() == 0 and pg.locator("#comandi-edificio #strato-alberi").count() == 1
        assert pg.locator("[data-gruppo='Rilievo']").count() == 0 and pg.locator("[data-esagera]").count() == 0
        assert "esagerato" not in pg.text_content("main")
    assert not pg.errori, pg.errori
    ctx.close()


def test_tegola_alterna_piano_e_falde_e_resta_dopo_il_ricaricamento(browser, base, tmp_path):
    """Punto 4: con la tegola accesa il cursore cambia e il clic non sceglie l'edificio; un clic su un corpo gli dà il tetto
    a falde con l'inclinazione corrente (anche a un vicino, in 3D: falde disegnate e versione piatta nascosta), un
    secondo clic lo riporta piano; la scelta resta dopo il ricaricamento (localStorage) e si vede nella mappa 2D."""
    ctx, pg, lon, lat = _apri_tetti(browser, base, tmp_path)
    _genera(pg, lon, lat, S, EE)
    pg.click("#tegola")
    assert "url(" in pg.evaluate(f"{S}.mappa.getCanvas().style.cursor")
    _clic_su_corpo(pg, S, "K2")
    attendi(pg, f"{S}.corpi.find((c) => c.id === 'K2').fonteTetto === 'falde'")
    assert "Corpo K2: tetto a falde di 22°" in pg.text_content("#stato-tetti") and "1 tetto a falde scelto" in pg.text_content("#stato-tetti")
    assert json.loads(pg.evaluate("localStorage.getItem('eugenio-tetti-v1')"))["tetti"]["cc-by/er|K2"]["i"] == 22
    # inclinazione 35° per il vicino V1
    pg.fill("#inclinazione-tetti", "35"); pg.dispatch_event("#inclinazione-tetti", "change")
    _clic_su_corpo(pg, S, "V1")
    attendi(pg, f"{S}.vicini.find((c) => c.id === 'V1').fonteTetto === 'falde'")
    assert pg.evaluate(f"{S}.vicini.find((c) => c.id === 'V1').inclinazione") == 35
    assert pg.evaluate(f"{S}.mappa.getSource('tetti-vicini').serialize().data.features.map((f) => f.properties.id)") == ["V1"]
    assert "V1" in json.dumps(pg.evaluate(f"{S}.mappa.getFilter('corpi')"))
    assert pg.evaluate(f"{S}.edificio") == "E-K"
    # secondo clic su K2: torna piano
    _clic_su_corpo(pg, S, "K2")
    attendi(pg, f"{S}.corpi.find((c) => c.id === 'K2').fonteTetto === 'piano'")
    _clic_su_corpo(pg, S, "K2")
    attendi(pg, f"{S}.corpi.find((c) => c.id === 'K2').fonteTetto === 'falde'")
    # Esc spegne la tegola; il clic torna a scegliere
    pg.keyboard.press("Escape")
    assert pg.get_attribute("#tegola", "aria-pressed") == "false"
    # ricaricamento: K2 e V1 (35°, l'inclinazione corrente al secondo clic su K2) restano a falde
    pg.reload()
    webgl(pg)
    _genera(pg, lon, lat, S, EE)
    t = pg.evaluate(f"Object.fromEntries([...{S}.corpi, ...{S}.vicini].map((c) => [c.id, [c.fonteTetto, c.inclinazione]]))")
    assert t["K2"] == ["falde", 35] and t["V1"] == ["falde", 35] and t["K1"] == ["piano", None], t     # K2 rifatto a 35°
    assert "2 tetti a falde scelti" in pg.text_content("#stato-tetti")
    # mappa 2D: bordo color mattone sui corpi scelti; con la tegola un clic in 2D cambia il tetto e non sceglie
    k1 = pg.evaluate(f"(() => {{ const c = {S}.corpi.find((x) => x.id === 'K1'); return {S}.proj.indietro(window.EUGENIO_EDIFICI.centroide(c.ring)); }})()")
    pg.evaluate("document.getElementById('torna-2d').click()")
    attendi(pg, f"!{S}.in3d")
    filtro = json.dumps(pg.evaluate(f"{S}.mappa.getFilter('corpi-2d-tetto')"))
    assert "K2" in filtro and "V1" in filtro and "K1" not in filtro, filtro
    pg.click("#tegola")
    scelto = pg.evaluate(f"{S}.daGenerare && {S}.daGenerare.edificio")
    pg.evaluate(f"{S}.mappa.jumpTo({{ center: {json.dumps(k1)}, zoom: 19 }})")
    pg.wait_for_timeout(500)
    pg.evaluate(f"(() => {{ const ll = {json.dumps(k1)}; {S}.mappa.fire('click', {{ lngLat: {{ lng: ll[0], lat: ll[1] }}, point: {S}.mappa.project(ll) }}); }})()")
    attendi(pg, "!!JSON.parse(localStorage.getItem('eugenio-tetti-v1')).tetti['cc-by/er|K1']")
    assert pg.evaluate(f"{S}.daGenerare && {S}.daGenerare.edificio") == scelto
    attendi(pg, f"JSON.stringify({S}.mappa.getFilter('corpi-2d-tetto')).includes('K1')")
    assert not pg.errori, pg.errori
    ctx.close()


def test_esporta_importa_e_reset_piani_con_conferma_nella_pagina(browser, base, tmp_path):
    """Esporta tetti (file JSON piccolo), «Reset piani» con la conferma nella pagina («Annulla» non cambia nulla, «Sì,
    riporta tutti piani» li azzera; mai confirm() del browser), Importa tetti li riporta."""
    ctx, pg, lon, lat = _apri_tetti(browser, base, tmp_path)
    _genera(pg, lon, lat, S, EE)
    pg.click("#tegola")
    _clic_su_corpo(pg, S, "K1"); _clic_su_corpo(pg, S, "K2")
    attendi(pg, f"{S}.corpi.filter((c) => c.fonteTetto === 'falde').length === 2")
    with pg.expect_download() as d:
        pg.click("#esporta-tetti")
    dest = tmp_path / "tetti.json"
    d.value.save_as(dest)
    dati = json.loads(dest.read_text(encoding="utf-8"))
    assert dati["tipo"] == "eugenio-tetti" and set(dati["tetti"]) == {"cc-by/er|K1", "cc-by/er|K2"} and dest.stat().st_size < 2000
    pg.click("#reset-piani")
    assert pg.is_visible("#conferma-reset") and "2 tetti" in pg.text_content("#conferma-reset")
    pg.click("#reset-no")
    assert pg.is_hidden("#conferma-reset") and pg.evaluate(f"{S}.corpi.filter((c) => c.fonteTetto === 'falde').length") == 2
    pg.click("#reset-piani"); pg.click("#reset-si")
    attendi(pg, f"{S}.corpi.every((c) => c.fonteTetto === 'piano')")
    assert json.loads(pg.evaluate("localStorage.getItem('eugenio-tetti-v1')"))["tetti"] == {}
    assert "Nessun tetto a falde scelto" in pg.text_content("#stato-tetti") and pg.is_disabled("#reset-piani")
    pg.set_input_files("#importa-tetti", str(dest))
    attendi(pg, f"{S}.corpi.filter((c) => c.fonteTetto === 'falde').length === 2")
    assert "Importati 2 tetti" in pg.text_content("#stato-tetti")
    # un file sbagliato non cambia nulla
    (tmp_path / "x.json").write_text('{"tetti": {"senza-barra": 30}}', encoding="utf-8")
    pg.set_input_files("#importa-tetti", str(tmp_path / "x.json"))
    attendi(pg, "/File dei tetti non letto: nessun tetto nel file/.test(document.getElementById('stato-tetti').textContent)")
    assert pg.evaluate(f"{S}.corpi.filter((c) => c.fonteTetto === 'falde').length") == 2
    assert not pg.errori, pg.errori
    ctx.close()


# ------------------------------------------------------------------ fonte dell'ortofoto scelta da sola (punto 5)
def _fonti_regionali():
    f = json.loads(json.dumps(FONTI))
    reg = {"rer2023": "08", "s2cloudless2016": "00", "pcn2012": "00"}
    for x in f["fonti"]:
        x["regione"] = reg[x["id"]]
    f["fonti"].append({"id": "toscana2023", "nome": "Ortofoto Regione Toscana 2023 (20 cm)", "licenza": "CC BY 4.0", "regione": "09",
                       "citazione": "Regione Toscana – Ortofoto 2023, 20 cm (CC BY 4.0)", "scheda": "https://geodati.gov.it/",
                       "stato": "confermata", "copia": True, "nei_report": True, "zoom": [12, 19], "riquadro": [9.68, 42.23, 12.38, 44.48],
                       "tessere": "/api/ortofoto/toscana2023/{z}/{x}/{y}.jpg?s=1", "spostabile": True, "spostamento_max": 20})
    ordine = {"rer2023": 1, "toscana2023": 1, "pcn2012": 8, "s2cloudless2016": 9}
    f["fonti"].sort(key=lambda x: (ordine[x["id"]], x["id"]))
    for x in f["fonti"]:
        x["zoom"] = {"rer2023": [12, 19], "toscana2023": [12, 19], "pcn2012": [12, 18], "s2cloudless2016": [5, 15]}[x["id"]]
    return f


def _tessere_finte(pg, vuote_rer_a=None, errore=None, chieste=None):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGBA", (256, 256), (0, 0, 0, 0)).save(b, "PNG"); vuota = b.getvalue()
    b = io.BytesIO(); Image.new("RGB", (256, 256), (90, 120, 80)).save(b, "JPEG"); foto = b.getvalue()
    fonti = _fonti_regionali()
    pg.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(fonti)))

    def tessera(r):
        u = r.request.url
        m = re.search(r"/api/ortofoto/([^/]+)/(\d+)/(\d+)/(\d+)\.", u)
        if chieste is not None:
            chieste.append((m.group(1), int(m.group(2))))
        fid, z, x, y = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        lon = x / 2 ** z * 360 - 180
        if errore and fid == errore[0]:
            return r.fulfill(status=errore[1], body=vuota if errore[1] == 200 else b"{}", headers=errore[2])
        if fid == "rer2023" and vuote_rer_a and abs(lon - vuote_rer_a) < 0.2:
            return r.fulfill(status=200, body=vuota, headers={"Content-Type": "image/png", "X-Ortofoto-Vuota": "1", "Access-Control-Expose-Headers": "X-Ortofoto-Vuota"})
        return r.fulfill(status=200, body=foto, headers={"Content-Type": "image/jpeg", "X-Ortofoto-Fonte": fid})
    pg.route(re.compile(r".*/api/ortofoto/(?!fonti)[^/]+/\d+/\d+/\d+\..*"), tessera)


LUOGHI = {"firenze": (11.2558, 43.7731), "susegana": (12.2563, 45.8537), "cesena": (12.2597, 44.1326), "bologna": (11.3426, 44.4949)}
ATTESE = {"firenze": ("toscana2023", ["toscana2023", "pcn2012", "s2cloudless2016"]),
          "susegana": ("pcn2012", ["pcn2012", "s2cloudless2016"]),
          "cesena": ("rer2023", ["rer2023", "pcn2012", "s2cloudless2016"]),
          "bologna": ("pcn2012", ["rer2023", "pcn2012", "s2cloudless2016"])}          # la RER non ha immagini a Bologna


def test_fonte_automatica_in_modelli3d(browser, base):
    """Punto 5: la casella mostra solo le fonti applicabili nel punto e propone la migliore: Firenze → Toscana (non la
    RER), Susegana → AGEA 2012 (solo AGEA e Sentinel), Cesena → RER, Bologna → AGEA (la RER non ha immagini). Una scelta a
    mano resta finché la fonte è applicabile; fuori dalla sua zona si torna all'automatico, con una nota."""
    ctx, pg = pagina(browser)
    _tessere_finte(pg, vuote_rer_a=LUOGHI["bologna"][0])
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!{M3D}.ortofoto", 30000)
    opz = "[...document.querySelectorAll('#sfondo-ortofoto option')].map((o) => o.value).filter(Boolean)"
    for luogo in ("firenze", "susegana", "cesena", "bologna"):
        lon, lat = LUOGHI[luogo]
        pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 17 }})")
        scelta, elenco = ATTESE[luogo]
        attendi(pg, f"{M3D}.ortofoto && {M3D}.ortofoto.id === '{scelta}' && JSON.stringify({opz}) === '{json.dumps(elenco, separators=(",", ":"))}'", 15000)
        assert pg.input_value("#sfondo-ortofoto") == scelta, luogo
    # scelta a mano a Cesena (AGEA): resta a Firenze (applicabile); la Toscana scelta a mano a Firenze, in Veneto no
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{LUOGHI['cesena'][0]}, {LUOGHI['cesena'][1]}], zoom: 17 }})")
    attendi(pg, f"{M3D}.ortofoto.id === 'rer2023'")
    pg.select_option("#sfondo-ortofoto", "pcn2012")
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{LUOGHI['firenze'][0]}, {LUOGHI['firenze'][1]}], zoom: 17 }})")
    attendi(pg, f"JSON.stringify({opz}).includes('toscana2023')")
    assert pg.evaluate(f"{M3D}.ortofoto.id") == "pcn2012"
    pg.select_option("#sfondo-ortofoto", "toscana2023")
    pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{LUOGHI['susegana'][0]}, {LUOGHI['susegana'][1]}], zoom: 17 }})")
    attendi(pg, f"{M3D}.ortofoto.id === 'pcn2012' && !{M3D}.manuale")
    assert "«Ortofoto Regione Toscana 2023 (20 cm)» non copre questo punto: torno alla scelta automatica" in pg.text_content("#messaggio-cerca")
    assert not pg.errori, pg.errori
    ctx.close()


def test_fonte_automatica_nella_pagina_ortofoto(browser, base):
    """Punto 5 nella pagina Ortofoto: stesse fonti applicabili e stessa scelta (Firenze, Susegana, Cesena, Bologna)."""
    ctx, pg = pagina(browser)
    _tessere_finte(pg, vuote_rer_a=LUOGHI["bologna"][0])
    pg.goto(base + "ortofoto.html?lat=44.1326&lon=12.2597&z=17")
    webgl(pg)
    st = "window.EUGENIO_ORTOFOTO.stato"
    attendi(pg, f"window.EUGENIO_ORTOFOTO && {st}.scelta", 30000)
    radio = "[...document.querySelectorAll('#fonti input[name=fonte]')].map((i) => i.value).filter(Boolean)"
    for luogo in ("firenze", "susegana", "cesena", "bologna"):
        lon, lat = LUOGHI[luogo]
        pg.evaluate(f"{st}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 17 }})")
        scelta, elenco = ATTESE[luogo]
        attendi(pg, f"{st}.scelta && {st}.scelta.id === '{scelta}' && JSON.stringify({radio}) === '{json.dumps(elenco, separators=(",", ":"))}'", 15000)
    assert not pg.errori, pg.errori
    ctx.close()


def test_nota_quando_la_fonte_non_risponde_e_limite_orario(browser, base):
    """Punto 2: tessere vuote con X-Ortofoto-Errore (la fonte non risponde) → dopo qualche errore la fonte si ferma e sotto
    la mappa compare «Ortofoto «…»: la fonte non risponde … riprovo da solo tra N minuti»; un 429 della fonte → nota del
    limite orario. Le tessere d'errore non danno righe rosse (sono risposte 200)."""
    for caso in ("errore", "limite"):
        ctx, pg = pagina(browser)
        rossi = []
        pg.on("console", lambda m: rossi.append(m.text) if m.type == "error" else None)
        if caso == "errore":
            h = {"Content-Type": "image/png", "X-Ortofoto-Errore": "fonte", "X-Ortofoto-Fonte": "pcn2012", "Retry-After": "120",
                 "Cache-Control": "no-store", "Access-Control-Expose-Headers": "X-Ortofoto-Errore, X-Ortofoto-Fonte, Retry-After"}
            _tessere_finte(pg, errore=("pcn2012", 200, h))
        else:
            h = {"Content-Type": "application/json", "Retry-After": "300", "X-EuGEnio-Limite": "ortofoto",
                 "Access-Control-Expose-Headers": "Retry-After, X-EuGEnio-Limite"}
            _tessere_finte(pg, errore=("pcn2012", 429, h))
        pg.goto(base + "modelli3d.html")
        webgl(pg)
        attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!{M3D}.ortofoto", 30000)
        pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{LUOGHI['susegana'][0]}, {LUOGHI['susegana'][1]}], zoom: 17 }})")
        attendi(pg, "!!document.getElementById('nota-limiti') && !document.getElementById('nota-limiti').hidden", 20000)
        nota = pg.text_content("#nota-limiti")
        if caso == "errore":
            assert "Ortofoto «Geoportale Nazionale (solo consultazione)»: la fonte non risponde" in nota and "riprovo da solo tra 2 minuti" in nota, nota
            assert not [x for x in rossi if "pcn2012" in x], rossi
        else:
            assert "Ortofoto: raggiunto il limite orario" in nota and "tra 5 minuti" in nota, nota
        # la nota sta sotto la mappa, prima dei comandi
        assert pg.evaluate("document.getElementById('nota-limiti').nextElementSibling.id") == "comandi-edificio"
        assert not pg.errori, pg.errori
        ctx.close()


def test_nessuna_tessera_oltre_lo_zoom_massimo(browser, base):
    """Punto 1: a zoom 20,5 la mappa ingrandisce le tessere dello zoom massimo della fonte (AGEA 18, RER 19) invece di
    chiederne di nuove (prima AGEA 2012 allo zoom 18–19 dava 502 a raffica)."""
    ctx, pg = pagina(browser)
    chieste = []
    _tessere_finte(pg, chieste=chieste)
    pg.goto(base + "modelli3d.html")
    webgl(pg)
    attendi(pg, f"window.EUGENIO_EDIFICIO3D && {M3D}.mappa && {M3D}.mappa.loaded() && !!{M3D}.ortofoto", 30000)
    for luogo, fonte in (("susegana", "pcn2012"), ("cesena", "rer2023")):
        lon, lat = LUOGHI[luogo]
        pg.evaluate(f"{M3D}.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 20.5 }})")
        attendi(pg, f"{M3D}.ortofoto && {M3D}.ortofoto.id === '{fonte}'", 15000)
        pg.wait_for_timeout(1500)
    massimi = {"pcn2012": 18, "rer2023": 19, "s2cloudless2016": 15, "toscana2023": 19}
    assert chieste and all(z <= massimi[f] for f, z in chieste), sorted({(f, z) for f, z in chieste if z > massimi[f]})
    assert {f for f, z in chieste if z == massimi[f]} >= {"pcn2012", "rer2023"}
    assert not pg.errori, pg.errori
    ctx.close()
