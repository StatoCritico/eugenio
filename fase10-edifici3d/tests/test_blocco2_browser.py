"""Prove nel browser (Chromium headless, Playwright) del blocco 2 del 05/11/2026 sulla demo sintetica del sito:
- Patrimonio → Modelli 3D: la sede (punto, colonne facoltative, colonne visura_…) passa nella memoria della scheda, la
  pagina 3D apre l'edificio che contiene il punto e applica la precedenza file → visura → stima;
- Tabella 11 del DM requisiti minimi con la quota vetrata stimata e inserita;
- alberi del rilievo LiDAR sintetico come ostacoli e sulla mappa;
- Importa DXF/IFC: posa agganciando il modello alla sagoma di un edificio dell'archivio (demo).
Nessuna richiesta al server con i dati della sede o del modello (solo GET di file statici). Si salta senza Playwright."""
from __future__ import annotations

import functools
import json
import math
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from edifici3d import sintetico as S  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"


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
            b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


@pytest.fixture()
def pg(browser):
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    p = ctx.new_page()
    p.errori, p.richieste = [], []
    p.on("pageerror", lambda e: p.errori.append(str(e)))
    p.on("request", lambda r: p.richieste.append((r.method, r.url, r.post_data_buffer)))
    ctx.route("**/api/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
    yield p
    ctx.close()


def _lonlat(x, y):
    from pyproj import Transformer
    return Transformer.from_crs(S.CRS, "EPSG:4326", always_xy=True).transform(x, y)


def test_sede_dal_patrimonio_alla_pagina_3d(pg, sito):
    lon, lat = _lonlat(S.X0 + 40, S.Y0 - 37)                    # dentro C7 (edificio E-VIC1)
    sede = {"nome": "S7 · Poliambulatorio di prova", "lat": lat, "lon": lon, "facoltative": {"superficie_lorda": 1234},
            "visura": {"visura_esito": "ok", "visura_piani_fuori_terra": "5", "visura_superficie_catastale": "980", "visura_uso": "uffici"}}
    pg.goto(f"{sito}/modelli3d.html")
    pg.evaluate(f"sessionStorage.setItem('eugenio-sede', {json.dumps(json.dumps(sede))})")
    pg.goto(f"{sito}/modelli3d.html?sede=locale")
    pg.wait_for_function("() => window.EUGENIO_EDIFICIO3D && window.EUGENIO_EDIFICIO3D.stato.edificio && window.EUGENIO_EDIFICIO3D.stato.superfici", timeout=60000)
    st = pg.evaluate("""() => { const s = window.EUGENIO_EDIFICIO3D.stato; return { e: s.edificio, csv: s.csv, vis: s.visura,
        sup: Object.fromEntries(Object.entries(s.superfici).filter(([k]) => k !== 'per_corpo').map(([k, v]) => [k, [v.valore, v.fonte]])),
        nota: document.getElementById('nota-sede').textContent, nascosta: document.getElementById('nota-sede').hidden,
        input: document.getElementById('csv-superficie_lorda').value, url: location.search } }""")
    assert st["e"] == "E-VIC1" and st["csv"] == {"superficie_lorda": 1234} and st["input"] == "1234"
    assert st["sup"]["superficie_lorda"] == [1234, "csv"] and st["sup"]["piani_fuori_terra"] == [5, "visura"]
    assert st["sup"]["superficie_catastale"] == [980, "visura"] and st["vis"]["uso"] == "uffici"
    assert not st["nascosta"] and "Poliambulatorio" in st["nota"] and "5 piani fuori terra" in st["nota"] and st["url"] == ""
    # obblighi: Tabella 11 con la quota stimata, poi con quella inserita
    pg.wait_for_function("() => /Tab. 11/.test(document.getElementById('obblighi').textContent)", timeout=30000)
    t = pg.inner_text("#obblighi")
    assert "stima" in t and "primo livello (intervento scelto)" in t
    pg.fill("#quota-vetrata", "30")
    pg.dispatch_event("#quota-vetrata", "change")
    pg.wait_for_function("() => /30 % \\(dato inserito\\)/.test(document.getElementById('obblighi').textContent)", timeout=10000)
    ob = pg.evaluate("window.EUGENIO_EDIFICIO3D.stato.obblighi")
    # Rimini, zona E: tra 28 % (0,58) e 33 % (0,62) → 0,596 per interpolazione lineare
    if ob["zona"] == "E":
        assert ob["ht_max_primo_livello"] == pytest.approx(0.596, abs=1e-3)
    assert ob["quota_vetrata"] == 30 and ob["quota_vetrata_fonte"] == "dato inserito"
    # un clic su un altro edificio toglie i dati della sede
    n_alberi = pg.evaluate("window.EUGENIO_EDIFICIO3D.stato.alberi.size")
    assert n_alberi > 0                                         # alberi del rilievo sintetico caricati
    vicini = pg.evaluate("window.EUGENIO_EDIFICIO3D.alberiVicini().length")
    ostacoli = pg.evaluate("window.EUGENIO_EDIFICIO3D.ostacoliRelativi().length")
    corpi = pg.evaluate("window.EUGENIO_EDIFICIO3D.stato.corpi.length + window.EUGENIO_EDIFICIO3D.stato.vicini.length")
    assert vicini > 0 and ostacoli == corpi + vicini                 # gli alberi entrano negli ostacoli delle ombre
    assert not pg.errori, pg.errori
    for metodo, url, corpo in pg.richieste:
        assert metodo == "GET" and not corpo and "Poliambulatorio" not in url, url


def test_pulsante_patrimonio_apre_la_pagina_3d(pg, sito):
    pg.goto(f"{sito}/patrimonio.html")
    pg.wait_for_function("() => typeof apriIn3d === 'function'", timeout=20000)
    lon, lat = _lonlat(S.X0 + 20, S.Y0 + 20)                    # dentro C3 (edificio E-DEMO)
    pg.evaluate(f"""() => {{ stato.righe = [{{ id: 'S1', denominazione: 'Sede di prova', esito: 'ok', lat: {lat}, lon: {lon},
        piani_fuori_terra: '4', superficie_netta: '1.500,5' }}]; elenco(); }}""")
    assert pg.locator("button.apri-3d").count() == 1
    sede = pg.evaluate("sedePer3d(0)")
    assert sede["facoltative"] == {"piani_fuori_terra": 4, "superficie_netta": 1500.5} and sede["nome"] == "S1 · Sede di prova"
    pg.evaluate("document.querySelector('button.apri-3d').click()")   # il passo dei risultati è nascosto finché non c'è un file
    pg.wait_for_url("**/modelli3d.html*", timeout=30000)
    pg.wait_for_function("() => window.EUGENIO_EDIFICIO3D && window.EUGENIO_EDIFICIO3D.stato.edificio && window.EUGENIO_EDIFICIO3D.stato.superfici", timeout=60000)
    assert pg.evaluate("window.EUGENIO_EDIFICIO3D.stato.edificio") == "E-DEMO"
    assert pg.evaluate("window.EUGENIO_EDIFICIO3D.stato.superfici.piani_fuori_terra.fonte") == "csv"


def test_posa_agganciata_alla_sagoma(pg, sito, tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    # pianta del corpo C7 (20 × 16 m) nelle coordinate di un disegno ruotato di 30° e con l'origine altrove
    from shapely import affinity
    from shapely.geometry import box
    c7 = next(g for p, g in S.uvl() if p["Id_e"] == "C7")
    loc = affinity.rotate(affinity.translate(c7, -c7.centroid.x + 5, -c7.centroid.y + 7), 30, origin=(0, 0))
    doc = ezdxf.new(); doc.header["$INSUNITS"] = 6
    doc.modelspace().add_lwpolyline(list(loc.exterior.coords)[:-1], close=True, dxfattribs={"thickness": 18.0, "layer": "CORPO"})
    f = tmp_path / "c7.dxf"; doc.saveas(f)
    pg.goto(f"{sito}/importa-dxf-ifc.html")
    pg.wait_for_function("() => window.EUGENIO_IMPORTA && window.EUGENIO_IMPORTA.stato.mappa && window.EUGENIO_IMPORTA.stato.mappa.loaded()", timeout=30000)
    pg.set_input_files("#file-modello", str(f))
    pg.wait_for_function("() => /File letto/.test(document.getElementById('messaggio').textContent)", timeout=60000)
    pg.check('input[name="posa"][value="sagoma"]')
    lon, lat = _lonlat(c7.centroid.x, c7.centroid.y)
    pg.wait_for_function("() => (window.EUGENIO_IMPORTA.stato.featArchivio || []).length > 0", timeout=30000)
    pg.evaluate(f"() => window.EUGENIO_IMPORTA.stato.mappa.jumpTo({{ center: [{lon}, {lat}], zoom: 19 }})")
    pg.wait_for_timeout(800)
    mx, my = pg.evaluate(f"""() => {{ const m = window.EUGENIO_IMPORTA.stato.mappa, p = m.project([{lon}, {lat}]),
        r = m.getCanvas().getBoundingClientRect(); return [r.left + p.x, r.top + p.y]; }}""")
    pg.mouse.click(mx, my)
    pg.wait_for_function("() => /Sagoma scelta/.test(document.getElementById('sagoma-scelta').textContent)", timeout=10000)
    assert "E-VIC1" in pg.inner_text("#sagoma-scelta")
    pg.click("#posiziona")
    pg.wait_for_function("() => window.EUGENIO_IMPORTA.stato.geojson", timeout=30000)
    msg = pg.inner_text("#messaggio-posa")
    r = pg.evaluate("window.EUGENIO_IMPORTA.stato.aggancio")
    assert "sovrapposizione" in msg and r["iou"] > 0.9 and abs(r["rapporto_aree"] - 1) < 0.02
    g = pg.evaluate("window.EUGENIO_IMPORTA.stato.geojson")
    xs = [q for f in g["features"] for q in f["geometry"]["coordinates"][0][:-1]]   # senza il vertice di chiusura
    cx, cy = sum(q[0] for q in xs) / len(xs), sum(q[1] for q in xs) / len(xs)
    assert math.hypot((cx - lon) * 111320 * math.cos(math.radians(lat)), (cy - lat) * 110574) < 1.0
    assert not pg.errori, pg.errori
    for metodo, url, corpo in pg.richieste:
        assert metodo == "GET" and not corpo and "c7" not in url.lower(), url


# ---------------------------------------------------------------- blocco 3 (05/11/2026): pagine senza GME e senza UNI
def test_emissioni_cogenerazione(pg, sito):
    pg.goto(f"{sito}/cog-emissioni.html")
    pg.wait_for_function("() => document.getElementById('anno-fattori').options.length > 0", timeout=20000)
    pg.click("#calcola-emissioni")
    pg.wait_for_function("() => !document.getElementById('passo-risultati').hidden", timeout=10000)
    t = pg.inner_text("#risultati-emissioni")
    assert "CO₂ del cogeneratore" in t and "199,6 g/kWh" in t                 # consumi elettrici 2025 (preliminare)
    assert pg.locator("#sensibilita tbody tr").count() == 4
    pg.check('input[name="modo-cog"][value="taglia"]')
    pg.click("#calcola-emissioni")
    assert "evita" in pg.inner_text("#messaggio-emissioni") or "in più" in pg.inner_text("#messaggio-emissioni")
    assert not pg.errori, pg.errori
    for metodo, url, corpo in pg.richieste:
        assert metodo == "GET" and not corpo and "/api/" not in url, url        # tutto nel browser


def test_clima_che_cambia_e_cer(pg, sito):
    import json as J
    serie = [2600 - 4 * i + (i * 37 % 11 - 5) * 15 for i in range(85)]
    pg.route("**/dati/clima/regioni.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=J.dumps({"099014": "08"})))
    pg.route("**/dati/clima/08/099014.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=J.dumps(
        {"nome": "Comune di prova", "stagioni": {"da": 1940, "gg_zona": serie}, "tendenze": {"gg_per_decennio": {"tutta": -40}}})))
    pg.goto(f"{sito}/edificio-clima.html?istat=099014")
    pg.wait_for_function("() => !document.getElementById('passo-clima-risultati').hidden", timeout=20000)
    assert "Comune di prova" in pg.inner_text("#messaggio-clima") and "Mann–Kendall" in pg.inner_text("#messaggio-clima")
    pg.fill("#firma-base", "300"); pg.fill("#firma-pendenza", "9"); pg.dispatch_event("#firma-pendenza", "change")
    assert "2050/51" in pg.inner_text("#risultati-clima") and "%" in pg.inner_text("#risultati-clima")
    pg.goto(f"{sito}/edificio-cer.html")
    pg.click("#cer-esempio")
    pg.wait_for_function("() => !document.getElementById('passo-cer-risultati').hidden", timeout=10000)
    assert "CP-ESEMPIO-1" in pg.inner_text("#risultati-cer") and pg.locator("#sedi-cer tbody tr").count() == 3
    assert not pg.errori, pg.errori
