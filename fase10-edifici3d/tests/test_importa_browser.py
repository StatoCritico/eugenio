"""Prova nel browser (Chromium headless, Playwright) della pagina Patrimonio › Importa DXF/IFC (04/11/2026).

Il sito vero (fase5-sito/sito) è servito in locale; /api/ortofoto/fonti risponde con una fonte finta e le tessere sono un
PNG grigio, le altre rotte /api/ rispondono 404. Si controlla:
- parità con il comando Python sugli stessi file sintetici (DXF e IFC, letti con dxf-parser e web-ifc nel Web Worker);
- georeferenziazione manuale con due punti scelti sulla pianta e sulla mappa;
- apertura del risultato nella pagina Modelli 3D (memoria della scheda);
- nessuna richiesta al server con il contenuto del file (solo GET di librerie, pagine e tessere);
- le librerie pesanti (web-ifc, dxf-parser, Clipper, proj4) si scaricano solo in questa pagina, web-ifc solo con un IFC;
- messaggi chiari per i file rifiutati.
Si salta se Playwright o Chromium non ci sono.
"""
from __future__ import annotations

import base64
import functools
import json
import math
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
pytest.importorskip("ezdxf"); pytest.importorskip("ifcopenshell")

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent)); sys.path.insert(0, str(QUI))
import modelli_sintetici as MS  # noqa: E402
from edifici3d import importa as I  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"
PESANTI = ("lib/web-ifc/", "lib/dxf-parser/", "lib/clipper-lib/", "lib/proj4/", "modelli_worker.js", "modelli_import.js")
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
def modelli(tmp_path_factory):
    return MS.genera(tmp_path_factory.mktemp("modelli"))


@pytest.fixture(scope="module")
def risultati_py(modelli):
    return {n: I.importa_sicuro(p, posa=posa) for n, (p, posa) in modelli.items()}


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
        self.ctx = browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
        self.richieste = []
        self.errori = []
        self.pg = self.ctx.new_page()
        self.pg.on("request", lambda r: self.richieste.append((r.method, r.url, r.post_data_buffer)))
        self.pg.on("pageerror", lambda e: self.errori.append(str(e)))
        self.ctx.route("**/api/ortofoto/fonti", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(FONTI)))
        self.ctx.route("**/api/ortofoto/finta/**", lambda r: r.fulfill(status=200, content_type="image/png", body=PNG))
        self.ctx.route("**/api/**", lambda r: r.fallback() if "/api/ortofoto/" in r.request.url
                       else r.fulfill(status=404, content_type="application/json", body="{}"))
        self.sito = sito

    def apri(self, pagina="importa-dxf-ifc.html"):
        self.pg.goto(f"{self.sito}/{pagina}")
        self.pg.wait_for_function("() => window.EUGENIO_IMPORTA && window.EUGENIO_IMPORTA.stato.mappa && window.EUGENIO_IMPORTA.stato.mappa.loaded()", timeout=30000)

    def carica(self, percorso):
        self.pg.evaluate("() => { document.getElementById('messaggio').textContent = ''; }")
        self.pg.set_input_files("#file-modello", str(percorso))
        self.pg.wait_for_function("() => /File letto|non letto|già convertito/.test(document.getElementById('messaggio').textContent)", timeout=90000)
        return self.pg.inner_text("#messaggio")

    def posiziona(self, posa):
        pg = self.pg
        pg.evaluate("() => { window.EUGENIO_IMPORTA.stato.geojson = null; }")
        if posa is None:
            pg.check('input[name="posa"][value="file"]')
        elif posa["tipo"] == "crs":
            pg.check('input[name="posa"][value="crs"]'); pg.select_option("#crs", posa["crs"])
        elif posa["tipo"] == "due_punti":
            pg.check('input[name="posa"][value="due_punti"]')
            for i, (x, y, lon, lat) in enumerate(posa["punti"]):
                for c, v in zip(("x", "y", "lon", "lat"), (x, y, lon, lat)):
                    pg.fill(f'.punti-posa tr[data-punto="{i}"] [data-c="{c}"]', str(v).replace(".", ","))
        pg.click("#posiziona")
        pg.wait_for_function("() => window.EUGENIO_IMPORTA.stato.geojson || /non riuscita/.test(document.getElementById('messaggio-posa').textContent)", timeout=30000)
        return pg.evaluate("window.EUGENIO_IMPORTA.stato.geojson")

    def chiudi(self):
        self.ctx.close()


@pytest.fixture()
def pagina(browser, sito):
    p = Pagina(browser, sito)
    yield p
    p.chiudi()


def _solo_lettura(richieste, nomi_file):
    """Nessun invio al server: solo GET, nessun corpo, nessun nome di file negli indirizzi."""
    for metodo, url, corpo in richieste:
        assert metodo == "GET" and not corpo, (metodo, url)
        assert not any(n.split(".")[0] in url for n in nomi_file), url


def test_parita_dxf_e_ifc_nel_browser(pagina, modelli, risultati_py):
    pagina.apri()
    for nome, (percorso, posa) in modelli.items():
        assert "File letto" in pagina.carica(percorso), nome
        js = pagina.posiziona(posa)
        assert js, (nome, pagina.pg.inner_text("#messaggio-posa"))
        assert MS.confronta(risultati_py[nome], js) == [], nome
    assert not pagina.errori
    _solo_lettura(pagina.richieste, list(modelli))
    # web-ifc caricato solo quando è arrivato un IFC, e una volta sola
    assert sum("web-ifc.wasm" in u for _, u, _ in pagina.richieste) == 1


def test_georeferenziazione_manuale_sulla_pianta_e_sulla_mappa(pagina, modelli, risultati_py):
    pagina.apri()
    percorso, posa = modelli["casa_metri.dxf"]
    pagina.carica(percorso)
    pg = pagina.pg
    pg.check('input[name="posa"][value="due_punti"]')
    (x1, y1, lo1, la1), (x2, y2, lo2, la2) = posa["punti"]
    pg.evaluate(f"() => window.EUGENIO_IMPORTA.stato.mappa.jumpTo({{ center: [{(lo1 + lo2) / 2}, {la1}], zoom: 20 }})")
    pg.wait_for_timeout(300)
    for (x, y, lon, lat) in ((x1, y1, lo1, la1), (x2, y2, lo2, la2)):
        # clic sulla pianta vicino allo spigolo (0,3 m di scarto: si aggancia allo spigolo)
        pg.locator("#pianta").scroll_into_view_if_needed()
        sx, sy = pg.evaluate(f"""() => {{ const s = document.getElementById('pianta'), p = s.createSVGPoint();
            p.x = {x + 0.3}; p.y = {-(y + 0.2)}; const q = p.matrixTransform(s.getScreenCTM()); return [q.x, q.y]; }}""")
        pg.mouse.click(sx, sy)
        mx, my = pg.evaluate(f"""() => {{ const m = window.EUGENIO_IMPORTA.stato.mappa, p = m.project([{lon}, {lat}]),
            r = m.getCanvas().getBoundingClientRect(); return [r.left + p.x, r.top + p.y]; }}""")
        pg.mouse.click(mx, my)
        pg.wait_for_timeout(100)
    valori = pg.evaluate("() => [...document.querySelectorAll('.punti-posa input')].map((i) => i.value)")
    assert [float(v.replace(",", ".")) for v in valori[0:2]] == [x1, y1] and [float(v.replace(",", ".")) for v in valori[4:6]] == [x2, y2]
    pg.click("#posiziona")
    pg.wait_for_function("() => window.EUGENIO_IMPORTA.stato.geojson", timeout=30000)
    js = pg.evaluate("window.EUGENIO_IMPORTA.stato.geojson")
    assert not any("scala" in a for a in js["avvisi"])
    py = risultati_py["casa_metri.dxf"]
    assert len(js["features"]) == len(py["features"])
    for f in py["features"]:
        c = MS._centroide(f)
        d = min(math.hypot((MS._centroide(g)[0] - c[0]) * 111320 * math.cos(math.radians(c[1])), (MS._centroide(g)[1] - c[1]) * 111320)
                for g in js["features"])
        assert d < 0.5, f["properties"]["id"]                 # clic a zoom 20: ~0,1 m per pixel
    _solo_lettura(pagina.richieste, ["casa_metri"])


def test_apertura_nella_pagina_3d(pagina, modelli):
    pagina.apri()
    pagina.carica(modelli["casa_sito.ifc"][0])
    pagina.pg.wait_for_function("() => window.EUGENIO_IMPORTA.stato.geojson", timeout=30000)
    pagina.pg.click("#apri-3d")
    pagina.pg.wait_for_url("**/modelli3d.html*", timeout=30000)
    pagina.pg.wait_for_function("() => /letto solo in questo browser|non aperto/.test(document.getElementById('messaggio').textContent)", timeout=60000)
    t = pagina.pg.inner_text("#messaggio")
    assert "Modello «casa_sito»: 2 corpi" in t, t
    s = pagina.pg.evaluate("({ m: window.EUGENIO_EDIFICIO3D.stato.modello, n: window.EUGENIO_EDIFICIO3D.stato.corpi.length, "
                           "chiave: sessionStorage.getItem('eugenio-modello') })")
    assert s == {"m": "casa_sito", "n": 2, "chiave": None}
    assert "modello=locale" not in pagina.pg.url              # tolto dall'indirizzo dopo l'apertura
    _solo_lettura(pagina.richieste, ["casa_sito"])
    # il .geojson scaricato si riapre nella stessa pagina d'importazione
    pagina.apri()
    pagina.carica(modelli["casa_sito.ifc"][0])
    pagina.pg.wait_for_function("() => window.EUGENIO_IMPORTA.stato.geojson", timeout=30000)
    with pagina.pg.expect_download() as d:
        pagina.pg.click("#scarica")
    file = d.value.path()
    g = json.loads(Path(file).read_text(encoding="utf-8"))
    assert g["formato"] == "eugenio-modello-1" and len(g["features"]) == 2
    copia = Path(file).with_name("casa.geojson"); copia.write_text(json.dumps(g), encoding="utf-8")
    assert "già convertito" in pagina.carica(copia)


def test_librerie_pesanti_solo_nella_pagina_di_importazione(pagina, modelli):
    for nome in ("index.html", "patrimonio.html", "modelli3d.html", "ortofoto.html", "dati.html", "visure.html"):
        pagina.richieste.clear()
        pagina.pg.goto(f"{pagina.sito}/{nome}")
        pagina.pg.wait_for_load_state("networkidle")
        presi = [u for _, u, _ in pagina.richieste if any(x in u for x in PESANTI)]
        assert not presi, (nome, presi)
    pagina.richieste.clear()
    pagina.apri()
    pagina.carica(modelli["casa_utm.dxf"][0])
    urls = [u for _, u, _ in pagina.richieste]
    assert any("lib/dxf-parser/" in u for u in urls) and not any("lib/web-ifc/" in u for u in urls)   # DXF: niente web-ifc


def test_messaggi_dei_file_rifiutati(pagina, tmp_path):
    pagina.apri()
    b = tmp_path / "binario.dxf"; b.write_bytes(b"AutoCAD Binary DXF\r\n\x1a\x00" + b"\x00" * 64)
    assert "binario" in pagina.carica(b)
    r = tmp_path / "rotto.ifc"; r.write_text("ISO-10303-21;\nHEADER;\nnon è un IFC\n")
    t = pagina.carica(r)
    assert "non letto" in t and ("IFC" in t or "geometria" in t), t
    g = tmp_path / "grande.ifc"
    with open(g, "wb") as f:
        f.write(b"ISO-10303-21;\n"); f.seek(51 * 1024 * 1024); f.write(b"\n")
    pagina.pg.set_input_files("#file-modello", str(g))
    pagina.pg.wait_for_function("() => /non letto/.test(document.getElementById('messaggio').textContent)", timeout=30000)
    assert "50 MB" in pagina.pg.inner_text("#messaggio") and "PC" in pagina.pg.inner_text("#avviso-pesante")
    v = tmp_path / "vuoto.dxf"; v.write_text("0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n")
    assert "nessun corpo" in pagina.carica(v)
