"""Pagina «Trasformazioni (UTA)» (14/11/2026): parte pura di fase5-sito/sito/aria_trasformazioni.js e gemello Python
aria/trasformazioni.py.

- con i dati gialli del foglio, riepiloghi e stima stagionale = valori salvati nel foglio psicro_UTA.xlsx del sito;
- parità JS (node) ↔ Python su 60 configurazioni a caso (sequenze, carichi, portate, stima) e sulle celle del foglio;
- il foglio compilato nel browser (compilaXlsx con fflate) e ricalcolato da LibreOffice dà gli stessi numeri della pagina.
Le parti con node o LibreOffice si saltano se mancano."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from aria import psicro as P  # noqa: E402
from aria import trasformazioni as T  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"
FOGLIO = SITO / "strumenti" / "psicro_UTA.xlsx"
NODE = shutil.which("node")
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


def _riga(r):
    return [r[0], *["" if v is None else str(v).replace(".", ",") for v in r[1:]]]


def conf_foglio():
    """i dati gialli del foglio (ambiente invernale 20 °C / 40 %, dal 15/11/2026 come la pagina)."""
    D = P.DATI_PREDEFINITI
    return {"p": P.pressione(D["quota"]), "quota": D["quota"], "pressioneImposta": None, "V": D["V"], "quotaEsterna": D["quotaEsterna"],
            "riferimento": 0,
            "estate": {**{k: v for k, v in D["estate"].items()}, "righe": [_riga(r) for r in P.PRESET["estate"]]},
            "inverno": {**{k: v for k, v in D["inverno"].items()}, "righe": [_riga(r) for r in P.PRESET["inverno"]]},
            "stima": {"gg": 2404, "ore": 12, "rendimento": 0.9, "pci": 9.59, "oreEq": 500, "eer": 3}}


def test_numero_all_italiana():
    assert T.numero("0,7") == 0.7 and T.numero("1.234,5") == 1234.5 and T.numero(" -5 ") == -5 and T.numero("0.7") == 0.7
    assert math.isnan(T.numero("AUTO")) and math.isnan(T.numero("")) and math.isnan(T.numero(None)) and T.numero("−3") == -3


def test_come_il_foglio():
    openpyxl = pytest.importorskip("openpyxl")
    ws = openpyxl.load_workbook(FOGLIO, data_only=True)["UTA"]
    if ws["D36"].value is None:
        pytest.skip("il foglio non ha i risultati salvati")
    r = T.calcola_configurazione(conf_foglio())
    e, i, s = r["estate"]["riepilogo"], r["inverno"]["riepilogo"], r["stima"]
    attesi = {"D36": e["frigoTotale"], "D37": e["frigoSensibile"], "D38": e["frigoLatente"], "D40": e["postRiscaldamento"], "D41": e["condensa"],
              "D44": e["ventilatori"], "D69": i["preriscaldamento"], "D70": i["postRiscaldamento"], "D72": i["umidificazione"],
              "D73": i["recuperata"], "D74": i["ventilatori"], "H78": s["mOA"], "H79": s["eps"], "H80": s["fabbisogno"], "H81": s["recuperata"],
              "H82": s["netto"], "H83": s["combustibile"], "H84": s["frigo"], "H85": s["elettrica"]}
    for cella, v in attesi.items():
        assert ws[cella].value == pytest.approx(v, rel=1e-9, abs=1e-9), cella
    assert ws["H40"].value == r["estate"]["raggiungibileTesto"] == "SÌ" and ws["H70"].value == r["inverno"]["raggiungibileTesto"] == "SÌ"
    # i valori della richiesta (arrotondati come in pagina)
    assert round(e["frigoTotale"], 1) == 46.0 and round(e["condensa"], 1) == 27.4 and round(e["postRiscaldamento"], 1) == 10.9
    assert round(i["recuperata"], 1) == 27.2 and round(i["preriscaldamento"], 1) == 12.0 and round(i["umidificazione"], 1) == 24.3
    assert round(i["postRiscaldamento"], 1) == 30.0


def test_celle_del_foglio():
    c = conf_foglio()
    celle = dict(T.celle_excel(c))
    assert celle["D6"] == 120 and celle["D8"] is None and celle["D14"] == P.RIF_PORTATA[0]
    assert celle["C28"] == "Miscela con ricircolo" and celle["D28"] == "AUTO" and celle["E29"] == 0.1 and celle["D31"] == 0.7
    assert celle["C33"] == "Nessuna" and celle["F60"] == 90 and celle["C63"] == "Ventilatore" and celle["D78"] == 2404
    assert len(celle) == 5 + 2 * (6 + 6 * 4) + 6


R = np.random.default_rng(20261114)
TIPI_PAR = {
    "Miscela con ricircolo": lambda: [R.choice(["AUTO", f"{R.uniform(0, 1):.2f}".replace(".", ","), ""]), "", ""],
    "Recuperatore di calore": lambda: [f"{R.uniform(0.4, 0.8):.2f}", R.choice(["", f"{R.uniform(0.3, 0.7):.2f}"]), ""],
    "Riscaldamento sensibile": lambda: R.choice([[f"{R.uniform(15, 40):.1f}", "", ""], ["", f"{R.uniform(1, 30):.1f}", ""]]),
    "Raffreddamento sensibile": lambda: [f"{R.uniform(8, 25):.1f}", "", ""],
    "Raffreddamento con deumidificazione": lambda: ["AUTO", R.choice(["", "0,1", "0,15"]), ""],
    "Umidificazione adiabatica": lambda: R.choice([["AUTO", "", ""], ["", f"{R.uniform(60, 95):.0f}", ""], ["", "", "0,8"]]),
    "Umidificazione a vapore": lambda: R.choice([["AUTO", "", ""], ["", f"{R.uniform(30, 60):.0f}", ""]]),
    "Preriscaldamento": lambda: ["AUTO", "", R.choice(["", "90", "85"])],
    "Post-riscaldamento": lambda: R.choice([["AUTO", "", ""], [f"{R.uniform(15, 35):.1f}", "", ""]]),
    "Ventilatore": lambda: R.choice([["0,7", "", ""], ["", f"{R.uniform(0.3, 2):.2f}", ""]]),
    "Nessuna": lambda: ["", "", ""],
}


def conf_a_caso():
    def righe(n):
        return [[t, *TIPI_PAR[t]()] for t in R.choice(list(TIPI_PAR), size=n)]
    z = float(R.uniform(0, 1500))
    return {"p": P.pressione(z), "quota": round(z), "pressioneImposta": None, "V": float(R.uniform(800, 20000)),
            "quotaEsterna": float(R.choice([100, 60, 30])), "riferimento": int(R.integers(0, 4)),
            "estate": {"esterno": {"t": float(R.uniform(26, 38)), "ur": float(R.uniform(30, 70))}, "ambiente": {"t": float(R.uniform(24, 27)), "ur": float(R.uniform(40, 60))},
                       "Qs": float(R.uniform(0, 15000)), "Ql": float(R.uniform(0, 4000)), "righe": righe(int(R.integers(1, 9)))},
            "inverno": {"esterno": {"t": float(R.uniform(-12, 5)), "ur": float(R.uniform(50, 100))}, "ambiente": {"t": float(R.uniform(18, 22)), "ur": float(R.uniform(30, 55))},
                        "Qs": float(R.uniform(-2000, 12000)), "Ql": float(R.uniform(0, 1500)), "righe": righe(int(R.integers(1, 9)))},
            "stima": {"gg": float(R.uniform(600, 4000)), "ore": float(R.uniform(6, 24)), "rendimento": float(R.uniform(0.8, 3.5)),
                      "pci": 9.59, "oreEq": float(R.uniform(200, 1200)), "eer": float(R.uniform(2.5, 5))}}


def _vicini(a, b, chi):
    if isinstance(a, float) and isinstance(b, (int, float)):
        assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b, rel=1e-9, abs=1e-9), chi
    else:
        assert a == b, chi


@pytest.mark.skipif(not NODE, reason="node non installato")
def test_parita_js_python():
    conf = [conf_a_caso() for _ in range(60)] + [conf_foglio()]
    prova = r"""
const T = require(process.argv[1] + "/aria_trasformazioni.js"), conf = JSON.parse(require("fs").readFileSync(0, "utf8"));
console.log(JSON.stringify(conf.map((c) => { const r = T.calcolaConfigurazione(c);
  return { e: r.estate.riepilogo, i: r.inverno.riepilogo, s: r.stima, celle: T.celleExcel(c), re: r.estate.raggiungibileTesto, ri: r.inverno.raggiungibileTesto,
    note: [...r.estate.righe, ...r.inverno.righe].map((o) => o.nota) }; })));"""
    js = json.loads(subprocess.run([NODE, "-e", prova, str(SITO)], input=json.dumps(conf), capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    for n, (c, j) in enumerate(zip(conf, js)):
        r = T.calcola_configurazione(c)
        for k, chiave in (("e", "estate"), ("i", "inverno")):
            for q, v in r[chiave]["riepilogo"].items():
                _vicini(float(v), j[k][q], (n, chiave, q))
        for q, v in r["stima"].items():
            _vicini(float(v), j["s"][q], (n, "stima", q))
        assert j["re"] == r["estate"]["raggiungibileTesto"] and j["ri"] == r["inverno"]["raggiungibileTesto"], n
        assert j["note"] == [o["nota"] for o in r["estate"]["righe"] + r["inverno"]["righe"]], n
        py = T.celle_excel(c)
        assert [x[0] for x in py] == [x[0] for x in j["celle"]], n
        for (cella, a), (_, b) in zip(py, j["celle"]):
            _vicini(float(a) if isinstance(a, (int, float)) else a, b, (n, cella))


@pytest.mark.skipif(not (NODE and SOFFICE), reason="node o LibreOffice mancanti")
@pytest.mark.parametrize("quale", ["foglio", "caso"])
def test_foglio_compilato_e_ricalcolato(tmp_path, quale):
    openpyxl = pytest.importorskip("openpyxl")
    c = conf_foglio() if quale == "foglio" else {
        "p": 98000.0, "quota": 300, "pressioneImposta": 98000.0, "V": 3500, "quotaEsterna": 40, "riferimento": 1,
        "estate": {"esterno": {"t": 33.4, "ur": 41.5}, "ambiente": {"t": 25, "ur": 55}, "Qs": 9000, "Ql": 2500,
                   "righe": [["Miscela con ricircolo", "AUTO", "", ""], ["Raffreddamento con deumidificazione", "AUTO", "0,12", ""],
                             ["Post-riscaldamento", "AUTO", "", ""], ["Ventilatore", "0,8", "", ""]]},
        "inverno": {"esterno": {"t": -7.2, "ur": 85}, "ambiente": {"t": 21, "ur": 45}, "Qs": 6000, "Ql": 800,
                    "righe": [["Recuperatore di calore", "0,7", "0,5", ""], ["Miscela con ricircolo", "AUTO", "", ""], ["Preriscaldamento", "AUTO", "", ""],
                              ["Umidificazione a vapore", "AUTO", "", ""], ["Post-riscaldamento", "AUTO", "", ""], ["Ventilatore", "", "1,5", ""]]},
        "stima": {"gg": 2617, "ore": 10, "rendimento": 0.95, "pci": 9.59, "oreEq": 700, "eer": 3.5}}
    if quale == "foglio":
        c["pressioneImposta"] = None
    ingresso = tmp_path / "compilato.xlsx"
    prova = r"""
const [S, out] = process.argv.slice(1), fs = require("fs"), ff = require(S + "/lib/fflate/fflate.js"), T = require(S + "/aria_trasformazioni.js");
const c = JSON.parse(fs.readFileSync(0, "utf8"));
fs.writeFileSync(out, T.compilaXlsx(ff, new Uint8Array(fs.readFileSync(S + "/strumenti/psicro_UTA.xlsx")), T.celleExcel(c)));"""
    subprocess.run([NODE, "-e", prova, str(SITO), str(ingresso)], input=json.dumps(c), text=True, encoding="utf-8", check=True)
    grezzo = openpyxl.load_workbook(ingresso)["UTA"]
    assert grezzo["H9"].value.startswith("=")                                # formule al loro posto, senza risultati salvati
    for cella, v in T.celle_excel(c):
        assert grezzo[cella].value == v or (v is None and grezzo[cella].value in (None, "")), cella
    uscita = tmp_path / "out"
    subprocess.run([SOFFICE, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(uscita), str(ingresso)],
                   capture_output=True, timeout=180, check=True)
    ws = openpyxl.load_workbook(uscita / "compilato.xlsx", data_only=True)["UTA"]
    r = T.calcola_configurazione(c)
    e, i, s = r["estate"]["riepilogo"], r["inverno"]["riepilogo"], r["stima"]
    for cella, v in {"D9": c["p"], "D36": e["frigoTotale"], "D40": e["postRiscaldamento"], "D41": e["condensa"], "D69": i["preriscaldamento"],
                     "D70": i["postRiscaldamento"], "D72": i["umidificazione"], "D73": i["recuperata"], "H80": s["fabbisogno"],
                     "H83": s["combustibile"], "H85": s["elettrica"]}.items():
        assert ws[cella].value == pytest.approx(v, rel=1e-6, abs=1e-6), cella
    assert ws["H40"].value == r["estate"]["raggiungibileTesto"] and ws["H70"].value == r["inverno"]["raggiungibileTesto"]
