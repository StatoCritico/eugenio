"""Statistiche › Indici dei prezzi (11/11/2026) in Chromium: indici, lotti, fasce, tabella con la variazione, confronto
delle convenzioni sul file di consumi di esempio. Il file dei prezzi è servito da qui (sul server lo scrive il worker)."""
from __future__ import annotations

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITO = Path(__file__).resolve().parent.parent / "sito"


def _serie(prima: float, ora: float, mesi_ora: int = 10) -> dict:
    return {"2025": [round(prima + m, 2) for m in range(12)],
            "2026": [round(ora + m, 2) if m < mesi_ora else None for m in range(12)]}


INDICI = {"aggiornato": "2026-11-12", "anni": [2025, 2026], "in_attesa": [], "sezioni": [
    {"id": "elettricita", "titolo": "Energia elettrica", "indici": [
        {"id": "intercenter-ee19-2026", "centrale": "Intercent-ER", "titolo": "Intercent-ER – Energia elettrica",
         "unita": "€/MWh", "fonte": "Intercent-ER, listini", "licenza": None, "nota": "Prezzo del listino.",
         "lotto_predefinito": "1", "dettagli": {}, "lotti": {
             "1": {"nome": "Lotto 1 – sanità MT", "varianti": {"F1": _serie(150, 200), "F2": _serie(140, 190), "F3": _serie(120, 170)}},
             "2": {"nome": "Lotto 2 – BT", "varianti": {"F1": _serie(152, 202), "F2": _serie(142, 192), "F3": _serie(122, 172)}}}},
        {"id": "consip-ee22", "centrale": "Consip", "titolo": "Consip – Energia Elettrica 22", "unita": "€/MWh",
         "fonte": "Consip, corrispettivi", "licenza": None, "nota": "Prezzo variabile.", "lotto_predefinito": "6",
         "dettagli": {}, "lotti": {
             "1": {"nome": "Lotto 1: Valle d'Aosta, Piemonte", "varianti": {f: _serie(100, 100) for f in ("F1", "F2", "F3", "F0")}},
             "6": {"nome": "Lotto 6: Emilia Romagna", "varianti": {f: _serie(151, 201) for f in ("F1", "F2", "F3", "F0")}}}}]},
    {"id": "gas", "titolo": "Gas naturale", "indici": [
        {"id": "intercenter-gn22", "centrale": "Intercent-ER", "titolo": "Intercent-ER – Gas naturale", "unita": "€/Smc",
         "fonte": "Intercent-ER, listini", "licenza": None, "nota": "Prezzo del gas.", "lotto_predefinito": "1",
         "dettagli": {}, "lotti": {"1": {"nome": "Lotto 1 – PA", "varianti": {
             "Usi termici": {"2025": [None] * 9 + [0.3706, 0.3657, 0.3452], "2026": [0.4203] + [None] * 11}}}}},
        {"id": "psv-da-arera", "titolo": "PSV day-ahead, media mensile (ARERA)", "unita": "€/MWh", "fonte": "ARERA",
         "licenza": "CC BY-SA 4.0", "nota": "Media mensile.", "lotto_predefinito": "", "dettagli": {},
         "lotti": {"": {"nome": "", "varianti": {"": _serie(40, 50)}}}},
        {"id": "pfor", "titolo": "PFOR,t ricostruito da EuGEnio", "unita": "€/MWh", "fonte": "EuGEnio", "licenza": None,
         "nota": "Trimestrale.", "lotto_predefinito": "",
         "dettagli": {"2026-10": {"trimestre": "2026 T4", "metodo": "stima", "provvisorio": True}},
         "lotti": {"": {"nome": "", "varianti": {"": _serie(35, 45, 12)}}}}]}]}


class Gestore(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/dati/prezzi/indici.json":
            corpo = json.dumps(INDICI).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        super().do_GET()

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Gestore, directory=str(SITO)))
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


def test_pagina_indici_e_confronto(base, browser):
    pg = browser.new_page(viewport={"width": 1366, "height": 900})
    errori = []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.goto(base + "indici-prezzi.html")
    pg.wait_for_selector("#consip-ee22 table")
    # prima l'energia elettrica (Intercent-ER, Consip), poi il gas (Intercent-ER, PSV, PFOR)
    assert pg.locator("article.ip-indice").evaluate_all("(a) => a.map((x) => x.id)") == [
        "intercenter-ee19-2026", "consip-ee22", "confronto-consumi", "intercenter-gn22", "psv-da-arera", "pfor"]
    assert pg.locator("#consip-ee22 select").input_value() == "6"
    assert pg.locator("#consip-ee22 select option").count() == 2
    # tabella: ottobre con la variazione, novembre senza l'anno in corso e senza variazione
    righe = pg.locator("#intercenter-ee19-2026 tbody tr")
    assert righe.nth(9).inner_text().split("\t") == ["Ottobre", "159,00", "209,00", "+31,4 %"]
    assert righe.nth(10).inner_text().split("\t")[2:] == ["—", ""]
    pg.locator("#intercenter-ee19-2026 button.filtro", has_text="Fascia F3").click()
    assert pg.locator("#intercenter-ee19-2026 tbody tr").nth(0).inner_text().split("\t")[1] == "120,00"
    pg.locator("#consip-ee22 select").select_option("1")
    assert pg.locator("#consip-ee22 tbody tr").nth(0).inner_text().split("\t")[1:3] == ["100,00", "100,00"]
    assert pg.locator("#consip-ee22 button.filtro", has_text="Monoraria").count() == 1
    # gas in €/Smc con 4 decimali; PFOR con il trimestre e «provvisorio»
    assert pg.locator("#intercenter-gn22 tbody tr").nth(9).inner_text().split("\t")[1] == "0,3706"
    assert "2026 T4, provvisorio" in pg.locator("#pfor tbody tr").nth(9).inner_text()
    # barre affiancate: 2 per mese dove ci sono tutti e due gli anni
    assert pg.locator("#psv-da-arera svg rect").count() == 22
    # confronto sul file di esempio: un grafico con 6 barre, tabella con le 3 offerte
    pg.set_input_files("#file-consumi", str(SITO / "esempi" / "consumi_fasce_esempio.csv"))
    pg.wait_for_selector("#confronto-consumi table")
    assert "Letti 12 mesi." in pg.locator("#confronto-consumi .messaggio").inner_text()
    assert pg.locator("#confronto-consumi svg rect").count() == 6
    offerte = pg.locator("#confronto-consumi tbody th").all_inner_texts()
    assert offerte == ["Intercent-ER lotto 1", "Intercent-ER lotto 2", "Consip lotto 6"]
    assert "gennaio" in pg.locator("#confronto-consumi").inner_text() and "ottobre" in pg.locator("#confronto-consumi").inner_text()
    pg.select_option("#lotto-confronto", "1")
    assert pg.locator("#confronto-consumi tbody th").nth(2).inner_text() == "Consip lotto 1"
    assert not errori, errori
    pg.close()


def test_file_dei_consumi_sbagliato(base, browser, tmp_path):
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    pg.goto(base + "indici-prezzi.html")
    pg.wait_for_selector("#file-consumi")
    f = tmp_path / "consumi.csv"
    f.write_text("mese;kWh\ngennaio;100\n", encoding="utf-8")
    pg.set_input_files("#file-consumi", str(f))
    pg.wait_for_function("document.querySelector('#confronto-consumi .messaggio').textContent.includes('F1')")
    assert pg.locator("#confronto-consumi svg").count() == 0
    pg.close()
