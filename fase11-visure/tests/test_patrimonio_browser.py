"""Prova nel browser (Chromium headless con Playwright) dell'importazione delle visure nella pagina Patrimonio.

Il sito vero (fase5-sito/sito) è servito in locale; le rotte /api/… sono simulate: /api/patrimonio risponde come la
geolocalizzazione della fase 4 (belfiore, foglio_catasto, mappale, comune_catasto, lat, lon, esito). Si controlla
anche che al server non arrivi mai niente delle visure (né colonne visura_…, né categorie, né dati personali).
Si salta se Playwright o Chromium non ci sono.
"""
import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

SITO = Path(__file__).resolve().parents[2] / "fase5-sito" / "sito"
COMUNI = {"ravenna": ("H199", "RAVENNA", 44.4175, 12.2035), "rimini": ("H294", "RIMINI", 44.0594, 12.5684),
          "forlì": ("D704", "FORLI'", 44.2227, 12.0407), "forli": ("D704", "FORLI'", 44.2227, 12.0407),
          "cesena": ("C573", "CESENA", 44.1391, 12.2431)}
VIETATI = ["visura_", "B/2", "A/10", "categoria", "SMPPRS80A01H199Z", "PRVLCU75B41H294K", "ESEMPIO PERSONA", "intestat"]


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
def file_visure(sintetici, tmp_path_factory):
    from visure.__main__ import principale
    d = tmp_path_factory.mktemp("uscita")
    principale(["leggi", str(sintetici), "--uscita", str(d / "solo")])
    principale(["leggi", str(sintetici), "--patrimonio", str(sintetici / "patrimonio_esempio_visure.csv"), "--uscita", str(d / "patr")])
    return d


def csv_dal_multipart(corpo: bytes) -> str:
    t = corpo.decode("utf-8", errors="replace")
    m = re.search(r"\r\n\r\n(.*?)\r\n--", t, re.S)
    return m.group(1) if m else ""


def geolocalizza(csv_testo: str) -> dict:
    righe = [r for r in csv_testo.splitlines() if r.strip()]
    sep = ";" if righe[0].count(";") >= righe[0].count(",") else ","
    titoli = [t.strip().lower() for t in righe[0].split(sep)]
    out = []
    for r in righe[1:]:
        d = dict(zip(titoli, [c.strip() for c in r.split(sep)]))
        com = COMUNI.get(d.get("comune", "").lower())
        if com and d.get("particella"):
            b, nome, lat, lon = com
            out.append({**d, "metodo": "catasto", "fonte_punto": "catasto", "esito": "ok", "nota": "", "lat": lat, "lon": lon,
                        "belfiore": b, "comune_catasto": nome, "foglio_catasto": d.get("foglio"), "mappale": d["particella"],
                        "area_m2": 1000.0, "tipo_particella": "edificio"})
        else:
            out.append({**d, "esito": "non_trovato", "nota": "simulato", "lat": None, "lon": None})
    return {"righe": out, "fonti": ["Catasto: Agenzia delle Entrate (CC BY 4.0), via Zornade"]}


@pytest.fixture()
def pagina(sito):
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        ctx = b.new_context(accept_downloads=True)
        pg = ctx.new_page()
        inviati: list[str] = []
        errori: list[str] = []
        pg.on("pageerror", lambda e: errori.append(str(e)))

        def api(route, req):
            corpo = req.post_data_buffer or b""
            inviati.append(req.url + "\n" + corpo.decode("utf-8", errors="replace"))
            if "/api/protezione" in req.url:
                return route.fulfill(json={"turnstile": None})
            if "/api/patrimonio" in req.url:
                return route.fulfill(json=geolocalizza(csv_dal_multipart(corpo)))
            if "/api/report/" in req.url:
                return route.fulfill(body=b"%PDF-1.4 finto", content_type="application/pdf")
            return route.fulfill(status=404, json={"detail": "simulato"})
        pg.route("**/api/**", api)
        pg.goto(f"{sito}/patrimonio.html", wait_until="domcontentloaded")
        pg.wait_for_function("window.EUGENIO_VISURE_UI && window.EUGENIO_PATRIMONIO")
        yield pg, inviati, errori
        ctx.close()
        b.close()


def risultato(pg, n):
    pg.wait_for_function(f"document.querySelectorAll('#edifici .edificio').length === {n}", timeout=20000)


def controlla_inviati(inviati):
    for x in inviati:
        for v in VIETATI:
            assert v not in x, (v, x[:300])


def test_visure_dopo_la_geolocalizzazione(pagina, sintetici, file_visure, tmp_path):
    pg, inviati, errori = pagina
    pg.set_input_files("#file", str(sintetici / "patrimonio_esempio_visure.csv"))
    pg.click("#calcola")
    risultato(pg, 6)
    pg.set_input_files("#file-visure", str(file_visure / "solo" / "indice.csv"))
    pg.wait_for_selector("#riepilogo-visure .conteggi")
    testo = pg.inner_text("#riepilogo-visure")
    assert re.search(r"5\s*con la visura", testo) and re.search(r"1\s*senza visura", testo)
    assert "2 unità delle visure senza un edificio" in testo
    assert not pg.is_visible("#usa-visure") and pg.is_visible("#scarica-visure")
    schede = pg.inner_text("#edifici")
    assert "Visura (abbinata): 3 unità · A/10 ×2; C/6" in schede
    assert "piani S1;T;1;2;3;4 (5 fuori terra, 1 interrati)" in schede
    assert "Visura: nessuna per questa particella" in schede
    with pg.expect_download() as d:
        pg.click("#scarica-visure")
    csv = Path(d.value.path()).read_text(encoding="utf-8-sig")
    testa = csv.splitlines()[0].split(";")
    assert "visura_piani_fuori_terra" in testa and "visura_consistenza_m3" in testa
    assert "42300" in csv and "SMPPRS80A01H199Z" not in csv
    # il report si fa sul server: senza le colonne delle visure
    pg.click("#report button >> nth=0")
    pg.wait_for_timeout(500)
    assert any("/api/report/" in x for x in inviati)
    controlla_inviati(inviati)
    assert not errori, errori


def test_indice_caricato_al_passo_1(pagina, file_visure):
    pg, inviati, errori = pagina
    pg.set_input_files("#file", str(file_visure / "solo" / "indice.csv"))
    pg.click("#calcola")
    risultato(pg, 7)        # 7 particelle (5 di fabbricati, 2 di terreni)
    corpo = [x for x in inviati if "/api/patrimonio" in x][0]
    assert "id;comune;sezione;foglio;particella" in corpo and "Forlì" in corpo
    assert "particelle cercate come edifici" in pg.inner_text("#messaggio")
    schede = pg.inner_text("#edifici")
    assert schede.count("Visura (abbinata)") == 7
    controlla_inviati(inviati)
    assert not errori, errori


def test_patrimonio_con_visure_al_passo_1(pagina, file_visure):
    pg, inviati, errori = pagina
    pg.set_input_files("#file", str(file_visure / "patr" / "patrimonio_con_visure.csv"))
    pg.click("#calcola")
    risultato(pg, 6)
    corpo = [x for x in inviati if "/api/patrimonio" in x][0]
    assert "denominazione" in corpo
    schede = pg.inner_text("#edifici")
    assert schede.count("Visura (") == 5 and "B/5" in schede
    controlla_inviati(inviati)
    assert not errori, errori


def test_json_e_colonne_personali(pagina, sintetici, file_visure, tmp_path):
    pg, inviati, errori = pagina
    pg.set_input_files("#file", str(sintetici / "patrimonio_esempio_visure.csv"))
    pg.click("#calcola")
    risultato(pg, 6)
    pg.set_input_files("#file-visure", str(file_visure / "solo" / "visure.json"))
    pg.wait_for_selector("#riepilogo-visure .conteggi")
    assert re.search(r"5\s*con la visura", pg.inner_text("#riepilogo-visure"))
    # un indice modificato a mano con intestatari e codici fiscali: le colonne si scartano
    righe = (file_visure / "solo" / "indice.csv").read_text(encoding="utf-8-sig").splitlines()
    righe[0] += ";intestatari;codice_fiscale"
    righe[1:] = [r + ";ESEMPIO PERSONA;SMPPRS80A01H199Z" for r in righe[1:]]
    f = tmp_path / "indice_con_personali.csv"
    f.write_text("\n".join(righe), encoding="utf-8")
    pg.set_input_files("#file-visure", str(f))
    pg.wait_for_function("document.getElementById('messaggio-visure').textContent.includes('dati personali')")
    assert "intestatari, codice_fiscale" in pg.inner_text("#messaggio-visure")
    with pg.expect_download() as d:
        pg.click("#scarica-csv")
    csv = Path(d.value.path()).read_text(encoding="utf-8-sig")
    assert "SMPPRS80A01H199Z" not in csv and "ESEMPIO PERSONA" not in csv
    pg.click("#togli-visure")
    assert "Visura" not in pg.inner_text("#edifici")
    controlla_inviati(inviati)
    assert not errori, errori


def test_cerca_gli_edifici_delle_visure(pagina, file_visure):
    pg, inviati, errori = pagina
    pg.set_input_files("#file-visure", str(file_visure / "solo" / "edifici_visure.csv"))
    pg.wait_for_selector("#usa-visure", state="visible")
    pg.click("#usa-visure")
    risultato(pg, 7)
    assert pg.inner_text("#edifici").count("Visura (") == 7
    controlla_inviati(inviati)
    assert not errori, errori
