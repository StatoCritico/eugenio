"""Clima e meteo › «Dati pluviometrici» (pluviometria.html, pluviometria.js, pioggia_gl.js; 22/11/2026, richiesta di Paolo).

Sui file: voce di menu prima di Previsioni, solo «Merging» (niente radar puro, niente bollettini di allerta), licenza
CC BY-SA 4.0 dichiarata, avviso «a fini statistici», niente dati di mercato; casella «Pioggia misurata» nella rete elettrica.
In Chromium (si salta se Playwright o Chromium non ci sono), senza rete, con dati/radar e /api/… intercettati:
  - passo scelto da solo con la durata (3 ore fino a 24 ore, 1 giorno per 7 giorni) e mai più lungo della durata;
  - cursore sulla fine del periodo, testo del periodo e dell'immagine, «Avvia» e «Ferma»;
  - interruzioni del periodo chieste a /api/rete/interruzioni/periodo solo con la casella accesa;
  - clic sulla mappa: valori nel punto e serie del comune (grafico e tabella), «–» dove non c'è misura;
  - CSV con la licenza CC BY-SA 4.0, corpo del PDF/Excel con licenza «CC BY-SA 4.0»;
  - collegamento salvabile con la fine del periodo come ora (non come posizione del cursore);
  - niente scorrimento orizzontale a 375 px, nessun errore JavaScript.
"""
from __future__ import annotations

import base64
import functools
import json
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
sys.path.insert(0, str(QUI))
import costruisci_pagine as C  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _t(nome: str) -> str:
    return (SITO / nome).read_text(encoding="utf-8")


def test_menu_file_e_licenza():
    t = (C.PARTI / "testata.html").read_text(encoding="utf-8")
    assert t.count('href="pluviometria.html"') == 2
    gruppi = {g["id"]: g for g in C.gruppi_menu(t)}
    assert [v["pagina"] for v in gruppi["clima"]["voci"]][:4] == ["dati.html", "legge10.html", "pluviometria.html", "previsioni.html"]
    s = _t("pluviometria.html")
    assert "<h1>Dati pluviometrici</h1>" in s and '<p class="gruppo-servizio">Clima e meteo</p>' in s
    assert "Servizio sperimentale non ancora verificato" in s and "a fini statistici, non di allerta" in s
    assert "CC BY-SA 4.0" in s and "radar.protezionecivile.gov.it" in s and "dpc-radar" in s
    assert re.search(r'<script src="pioggia_gl\.js\?v=\w+"></script>\s*<script src="pluviometria\.js\?v=\w+"></script>', s)
    for js in ("pluviometria.js", "pioggia_gl.js"):
        j = _t(js)
        for vietato in ('"SRI"', '"SRT1"', "allerta.geojson", "PUN", "TTF"):
            assert vietato not in j, (js, vietato)
    assert 'licenza: "CC BY-SA 4.0"' in _t("pluviometria.js")
    r = _t("rete-elettrica.html")
    assert 'id="strato-pioggia" type="checkbox" data-collegamento="pioggia"' in r and "pioggia_gl.js" in r
    assert 'id="strato-pioggia" type="checkbox" checked' not in r           # spenta in partenza
    assert C.main(["--controlla"]) == 0


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


def _nome(t: datetime) -> str:
    return t.strftime("%Y%m%dT%H%MZ")


def indice() -> dict:
    """Frame degli ultimi 7 giorni come li scrive il worker (ore locali multiple del passo; qui UTC+1, inverno)."""
    fine = datetime(2026, 11, 22, 5, tzinfo=timezone.utc)                     # 06:00 italiane
    fr = {}
    for p, h in (("CUM3", 3), ("CUM6", 6), ("CUM12", 12), ("CUM24", 24)):
        t, lista = fine, []
        while t > fine - timedelta(days=7):
            if (t.hour + 1) % h == 0:
                lista.append(_nome(t))
            t -= timedelta(hours=1)
        fr[p] = {"frame": sorted(lista), "unita": "mm", "passo_ore": h, "ultimo": "20261122T0730Z", "descrizione": p}
    fr["CUM24"]["frame"] = [n for n in fr["CUM24"]["frame"] if n.endswith("T2300Z")]
    return {"aggiornato": "2026-11-22T08:00:00Z", "raccolta_dal": "2026-11-15T00:00:00Z",
            "griglia": {"angoli": [[5.5, 48.0], [19.5, 48.0], [19.5, 35.0], [5.5, 35.0]]}, "prodotti": fr,
            "scala": {"mm": {"soglie": [0.5, 1, 2, 5], "colori": ["#c6e8ff", "#8cc8f5", "#4ea3e6", "#1f6fd1"]}},
            "mancante": {"testo": "nessuna misura (tratteggio grigio)"},
            "fonte": "Dati © Dipartimento della Protezione Civile («Merging» radar-pluviometri), CC BY-SA 4.0 – elaborazione EuGEnio",
            "giorni_mappa": 7, "archivio_anni": 10}


def _pagina(browser, chiesti, larghezza=1366):
    ctx = browser.new_context(viewport={"width": larghezza, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.errori = []
    pg.on("pageerror", lambda e: pg.errori.append(str(e)))
    ind = indice()

    def dati(route):
        u = route.request.url
        chiesti.append(u)
        if u.split("?")[0].endswith("/indice.json"):
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(ind))
        return route.fulfill(status=200, content_type="image/png", body=PNG)

    def api(route):
        u = route.request.url
        chiesti.append(u)
        if "/api/radar/punto" in u:
            v = {p: {"valore": x, "unita": "mm", "fine": "2026-11-22T07:30:00Z", "descrizione": p}
                 for p, x in (("CUM3", 1.6), ("CUM6", 2.0), ("CUM12", None), ("CUM24", 12.4))}
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(
                {"valori": v, "comune": {"istat": "099014", "nome": "Rimini"}}))
        if "/api/radar/comune/" in u:
            gg = [{"data": f"2026-11-{d:02d}", "mm": None if d == 18 else d / 2, "previsto_mm": 3.0 if d > 19 else None}
                  for d in range(14, 22)]
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(
                {"istat": "099014", "nome": "Rimini", "giornalieri": gg, "nota_giornalieri": "nota"}))
        if "/api/rete/interruzioni/periodo" in u:
            f = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [12.57, 44.06]},
                  "properties": {"id": 1, "inizio": "2026-11-22T03:00:00+01:00", "fine_stimata": "2026-11-22T05:00:00+01:00",
                                 "causa": "Guasto", "clienti": 10}}]
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"type": "FeatureCollection", "features": f}))
        if "/api/report" in u:
            chiesti.append("CORPO " + (route.request.post_data or ""))
            return route.fulfill(status=200, content_type="application/pdf", body=b"%PDF-1.4",
                                 headers={"Content-Disposition": 'attachment; filename="pioggia.pdf"'})
        return route.fulfill(status=404, content_type="application/json", body="{}")
    ctx.route("**/dati/radar/**", dati)
    ctx.route("**/api/**", api)
    return ctx, pg


def test_animazione_punto_file_e_collegamento(base, browser):
    chiesti: list[str] = []
    ctx, pg = _pagina(browser, chiesti)
    pg.goto(base + "pluviometria.html")
    pg.wait_for_function("document.getElementById('periodo-testo').textContent.includes('immagini')", timeout=20000)
    assert pg.input_value("#durata") == "24" and pg.input_value("#passo") == "3"
    assert "8 immagini da 3 ore" in pg.inner_text("#periodo-testo")
    assert "fino alle 06:00 di dom 22/11" in pg.inner_text("#frame-testo")
    assert pg.evaluate("[...document.querySelectorAll('#passo option')].filter(o=>o.disabled).length") == 0
    # 6 ore: i passi di 12 ore e 1 giorno si spengono; 7 giorni: passo di 1 giorno
    pg.select_option("#durata", "6")
    assert pg.evaluate("[...document.querySelectorAll('#passo option')].filter(o=>o.disabled).map(o=>o.value)") == ["12", "24"]
    pg.select_option("#durata", "168")
    assert pg.input_value("#passo") == "24" and "7 immagini da 1 giorno" in pg.inner_text("#periodo-testo")
    pg.select_option("#passo", "12")                                              # il passo si può cambiare
    assert "14 immagini da 12 ore" in pg.inner_text("#periodo-testo")
    pg.fill("#secondi", "0.2")
    pg.click("#avvia")
    pg.wait_for_timeout(900)
    assert pg.get_attribute("#avvia", "aria-pressed") == "true"
    assert re.match(r"\d+ di 14: pioggia delle 12 ore", pg.inner_text("#frame-testo"))
    pg.click("#avvia")
    assert pg.get_attribute("#avvia", "aria-pressed") == "false"
    # cursore: un passo indietro → la fine si sposta di 12 ore (da mezzanotte alle 12 del 21) e va nel collegamento come ora
    assert not any("/api/rete/interruzioni/periodo" in u for u in chiesti)       # casella spenta: niente richieste
    pg.check("#strato-interruzioni")
    pg.wait_for_function("1", timeout=1000)
    pg.wait_for_timeout(500)
    assert any("/api/rete/interruzioni/periodo" in u for u in chiesti)
    pg.evaluate("(()=>{const r=document.getElementById('fine'); r.value=String(+r.max-1); r.dispatchEvent(new Event('input')); r.dispatchEvent(new Event('change'));})()")
    pg.wait_for_timeout(800)
    assert "alle 12:00 di sab 21/11" in pg.inner_text("#periodo-testo")
    assert "fine=20261121T1100Z" in pg.url and "durata=168" in pg.url and "passo=12" in pg.url
    # punto e comune
    box = pg.query_selector("#mappa-pioggia").bounding_box()
    pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.wait_for_function("document.querySelector('#tabella-giorni table') !== null", timeout=15000)
    scheda = pg.inner_text("#scheda-punto")
    assert "1,6 mm" in scheda and "12 mm" in scheda and "–" in scheda
    assert pg.query_selector("#grafico-giorni svg") is not None
    tab = pg.inner_text("#tabella-giorni")
    assert "Prevista" in tab and "18/11/2026\t–" in tab and "7 giorni con misura" in tab
    assert re.search(r"lat=[\d.]+&lon=[\d.]+", pg.url)
    with pg.expect_download() as d:
        pg.click("#scarica-dati button[data-formato=csv]")
    csv = Path(d.value.path()).read_text(encoding="utf-8-sig")
    assert "CC BY-SA 4.0" in csv and "Rimini (ISTAT 099014)" in csv and "statistici" in csv
    pg.click("#scarica-dati button[data-formato=pdf]")
    pg.wait_for_timeout(800)
    corpo = json.loads(next(x for x in chiesti if x.startswith("CORPO "))[6:])
    assert corpo["licenza"] == "CC BY-SA 4.0" and any("CC BY-SA 4.0" in f["testo"] for f in corpo["fonti"])
    # collegamento: riapertura con la stessa fine
    url = pg.url
    pg2 = ctx.new_page()
    pg2.goto(url)
    pg2.wait_for_function("document.documentElement.dataset.collegamentoPronto !== undefined", timeout=20000)
    assert pg2.input_value("#durata") == "168" and pg2.input_value("#passo") == "12"
    assert "alle 12:00 di sab 21/11" in pg2.inner_text("#periodo-testo")
    assert pg.errori == []
    ctx.close()


def test_telefono(base, browser):
    ctx, pg = _pagina(browser, [], larghezza=375)
    pg.goto(base + "pluviometria.html")
    pg.wait_for_function("document.getElementById('periodo-testo').textContent.includes('immagini')", timeout=20000)
    assert not pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
    assert pg.errori == []
    ctx.close()
