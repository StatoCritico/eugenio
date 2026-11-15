"""Prove nel browser (Chromium headless, Playwright) delle scelte di serie del 14/11/2026: ultimo anno · 5 · 10 · 20 ·
tutta la serie in Dati climatici (periodi rapidi e stagioni della Legge 10), nella pagina Legge 10 e in Cambiamento
climatico. Le rotte /api/ sono simulate (nessuna rete). Si salta se Playwright o Chromium non ci sono."""
from __future__ import annotations

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

SITO = Path(__file__).resolve().parents[1] / "sito"
_FONTE = "Open-Meteo.com"
CATALOGO = {
    "dataset": [
        {"id": "meteo_orario", "titolo": "Meteo orario (ICON storico)", "descrizione": "…", "fonte": _FONTE, "licenza": "CC BY 4.0",
         "licenza_url": "", "periodo": "date", "inizio": "2022-11-14", "fine": "2026-11-10", "area": True,
         "frequenze": [{"id": "oraria", "nome": "Oraria"}], "frequenza_nativa": "oraria",
         "variabili": [{"id": "temperature_2m", "nome": "Temperatura", "gruppo": "Meteo", "predefinita": True}]},
        {"id": "meteo_giornaliero", "titolo": "Meteo giornaliero (ERA5 corretto)", "descrizione": "…", "fonte": _FONTE,
         "licenza": "CC BY 4.0", "licenza_url": "", "periodo": "date", "inizio": "2015-01-01", "fine": "2026-11-10", "area": True,
         "frequenze": [{"id": "giornaliera", "nome": "Giornaliera"}], "frequenza_nativa": "giornaliera",
         "variabili": [{"id": "t_media", "nome": "Temperatura media", "gruppo": "Meteo", "predefinita": True}]},
        {"id": "legge10", "titolo": "Dati climatici per la Relazione Legge 10", "descrizione": "…", "fonte": _FONTE,
         "licenza": "CC BY 4.0", "licenza_url": "", "periodo": "stagioni", "inizio": "2015-01-01", "fine": "2026-11-10",
         "area": True, "frequenze": [], "variabili": [], "tipologie": [{"id": "mensili", "nome": "Mensili"}],
         "stagioni": {"min": 1, "max": 30, "predefinite": 10, "scelte": [1, 5, 10, 20, 0], "tutte": 0}}],
    "non_scaricabili": [], "regioni": ["08"], "comuni": 1, "limiti": {"righe_csv": 500000},
}
STAGIONI = [f"{a}/{str(a + 1)[2:]}" for a in range(2015, 2026)]


def legge10(anni: int) -> dict:
    st = STAGIONI if anni in (0, 20) else STAGIONI[-anni:]
    note = []
    if anni == 20:
        note.append("Chieste 20 stagioni: l'archivio ne ha 11 complete, dalla 2015/16; si usano tutte.")
    if len(st) < 5:
        note.append("Con meno di 5 stagioni i valori sono indicativi: un inverno può essere molto più mite o più freddo "
                    "del solito, e la tendenza non si calcola.")
    return {"istat": "037006", "comune": "Bologna", "stagioni": st, "stagioni_richieste": anni, "stagioni_disponibili": 11,
            "prima_stagione_disponibile": "2015/16", "note": note, "giorni": 365 * len(st),
            "mensili": [{"mese": m, "t_media": 10.0, "t_min_media": 5.0, "t_max_media": 15.0, "h_globale_mj": 10.0,
                         "h_diffusa_mj": 4.0, "pv_pa": 900.0, "vento_ms": 2.0, "ur_media": 70.0} for m in range(1, 13)],
            "gradi_giorno": {"zona_di_riferimento": "E", "gg_periodo_zona": 2100, "gg_anno_intero": 2300,
                             "gg_per_periodo_di_ogni_zona": {z: 2000 for z in "ABCDEF"}, "zona_risultante": "E",
                             "per_stagione": {s: 2100 for s in st}, "tendenza_gg_per_decennio": None if len(st) < 5 else -80,
                             "minimo": 2000, "massimo": 2200},
            "temperatura_progetto": {"invernale": -4.0, "estiva": 34.0, "metodo": "…"}, "avvertenza": "Valori dal clima osservato.",
            "fonte": "Open-Meteo.com"}


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
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium non disponibile: {e}")
        yield b
        b.close()


def pagina(browser, chiamate):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()

    def api(route):
        url = route.request.url
        chiamate.append(url)
        if "/api/storici/catalogo" in url:
            return route.fulfill(json=CATALOGO)
        if "/api/storici/stima" in url:
            return route.fulfill(json={"righe": 10, "colonne": 3, "dimensione": "1 kB", "comuni": 1, "dal": None, "al": None,
                                       "avvisi": [], "consentito": True, "motivo": "", "suggerimenti": []})
        if "/api/clima-legge10/" in url:
            anni = int(url.split("anni=")[1].split("&")[0])
            return route.fulfill(json=legge10(anni))
        if url.rstrip("/").endswith("/api/comuni"):
            return route.fulfill(json=[{"istat": "037006", "nome": "Bologna", "provincia": "BO", "lat": 44.49, "lon": 11.34}])
        return route.fulfill(status=404, body=json.dumps({"detail": "non simulata"}), content_type="application/json")
    pg.route("**/api/**", api)
    return ctx, pg


def test_dati_periodi_rapidi_e_stagioni(browser, base):
    chiamate = []
    ctx, pg = pagina(browser, chiamate)
    pg.goto(base + "dati.html?dataset=meteo_giornaliero")
    pg.wait_for_selector("#periodi-rapidi .filtro")
    etichette = pg.eval_on_selector_all("#periodi-rapidi .filtro", "bs => bs.map(b => b.textContent.trim())")
    assert etichette == ["ultimo mese", "ultimo anno", "5 anni", "10 anni", "20 anni", "tutta la serie"]
    pg.wait_for_function("document.getElementById('dal').value !== ''")
    pg.click("#periodi-rapidi [data-mesi='60']")
    assert pg.input_value("#dal") == "2021-11-11" and pg.input_value("#al") == "2026-11-10"
    assert pg.is_hidden("#nota-periodo")
    pg.click("#periodi-rapidi [data-mesi='240']")
    assert pg.input_value("#dal") == "2015-01-01"
    nota = pg.inner_text("#nota-periodo")
    assert pg.is_visible("#nota-periodo") and "Chiesti 20 anni" in nota and "01/01/2015" in nota and "11,9 anni" in nota
    pg.click("#periodi-rapidi [data-mesi='0']")
    assert pg.input_value("#dal") == "2015-01-01" and pg.is_hidden("#nota-periodo")
    pg.click("#periodi-rapidi [data-mesi='120']")
    assert pg.input_value("#dal") == "2016-11-11" and pg.is_hidden("#nota-periodo")
    # meteo orario (dal 14/11/2022): 5 anni chiesti → tutta la serie, con la nota
    pg.check("input[name='dataset'][value='meteo_orario']")
    pg.click("#periodi-rapidi [data-mesi='60']")
    assert pg.input_value("#dal") == "2022-11-14" and "14/11/2022" in pg.inner_text("#nota-periodo")
    # Legge 10: stagioni
    pg.check("input[name='dataset'][value='legge10']")
    opz = pg.eval_on_selector_all("#stagioni option", "os => os.map(o => [o.value, o.textContent.trim()])")
    assert opz == [["1", "ultima stagione"], ["5", "ultime 5"], ["10", "ultime 10"], ["20", "ultime 20"], ["0", "tutta la serie"]]
    assert "11 stagioni complete" in pg.inner_text("#nota-stagioni") and "2015/16 alla 2025/26" in pg.inner_text("#nota-stagioni")
    pg.select_option("#stagioni", "20")
    assert "Si usano tutte (11)" in pg.inner_text("#nota-stagioni")
    pg.select_option("#stagioni", "1")
    assert "indicativi" in pg.inner_text("#nota-stagioni")
    pg.wait_for_timeout(500)
    corpo = [c for c in chiamate if "/api/storici/stima" in c]
    assert corpo
    ctx.close()


def test_legge10_scelte(browser, base):
    chiamate = []
    ctx, pg = pagina(browser, chiamate)
    pg.goto(base + "legge10.html?comune=037006")
    opz = pg.eval_on_selector_all("#anni option", "os => os.map(o => [o.value, o.textContent.trim()])")
    assert opz == [["1", "ultima stagione"], ["5", "ultime 5"], ["10", "ultime 10"], ["20", "ultime 20"], ["0", "tutta la serie"]]
    assert pg.input_value("#anni") == "10"
    pg.wait_for_function("document.getElementById('periodo').textContent.length > 0", timeout=10000)
    assert "10 stagioni di riscaldamento, dalla 2016/17 alla 2025/26" in pg.inner_text("#periodo")
    pg.select_option("#anni", "1")
    pg.wait_for_function("document.getElementById('periodo').textContent.includes('Una stagione')")
    t = pg.inner_text("#periodo")
    assert "la 2025/26" in t and "indicativi" in t
    pg.select_option("#anni", "20")
    pg.wait_for_function("document.getElementById('periodo').textContent.includes('Chieste 20')")
    assert "11 stagioni" in pg.inner_text("#periodo")
    pg.select_option("#anni", "0")
    pg.wait_for_function("document.getElementById('periodo').textContent.includes('tutte quelle complete')")
    assert any("anni=0" in c for c in chiamate) and any("anni=1" in c for c in chiamate)
    ctx.close()


def test_cambiamento_climatico_ultime_stagioni(browser, base):
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    gg = [3000 - 8 * k for k in range(86)]          # stagioni 1940/41 … 2025/26, in calo

    def rotta(route):
        url = route.request.url
        if "dati/clima/regioni.json" in url:
            return route.fulfill(json={"037006": "08"})
        if "dati/clima/08/037006.json" in url:
            return route.fulfill(json={"nome": "Bologna", "stagioni": {"da": 1940, "gg_zona": gg}})
        if "/api/comuni" in url:
            return route.fulfill(json=[])
        return route.continue_()
    pg.route("**/*", rotta)
    pg.goto(base + "edificio-clima.html?istat=037006")
    opz = pg.eval_on_selector_all("#clima-dal option", "os => os.map(o => o.value)")
    assert opz == ["n5", "n10", "n20", "1991", "1981", "1961", "1940"] and pg.input_value("#clima-dal") == "1981"
    pg.wait_for_function("document.getElementById('messaggio-clima').textContent.includes('stagioni dal')")
    assert "45 stagioni dal 1981/82" in pg.inner_text("#messaggio-clima")
    for valore, testo in (("n5", "5 stagioni dal 2021/22"), ("n20", "20 stagioni dal 2006/07"), ("1940", "86 stagioni dal 1940/41")):
        pg.select_option("#clima-dal", valore)
        pg.wait_for_function(f"document.getElementById('messaggio-clima').textContent.includes('{testo}')")
    ctx.close()
