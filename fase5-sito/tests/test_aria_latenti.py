"""Carichi latenti (aria-latenti.html, 14/11/2026): calcolo di aria_latenti.js (node) e del gemello Python
fase14-trattamento-aria/aria/latenti.py.

- casi a mano su poche ore (estate: Δx·2501, inverno: Δx·2676, portata con i 4 riferimenti, livello di progetto);
- monotonia: alzando l'UR obiettivo estiva calano le ore da deumidificare, alzando quella invernale crescono le ore da
  umidificare; risultati proporzionali alla portata;
- parità node ↔ Python su una serie sintetica di 3 anni (gruppi Estate, Inverno, Ore d'ufficio; diverse condizioni,
  portate e riferimenti): conteggi identici, energie, picchi, mesi, classi e curva di durata entro 1e-9 relativo.
Le prove con node si saltano se node manca.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

QUI = Path(__file__).resolve().parents[1]
SITO = QUI / "sito"
sys.path.insert(0, str(QUI.parent / "fase14-trattamento-aria"))
from aria import latenti as LAT  # noqa: E402
from aria import psicro as P  # noqa: E402

NODE = shutil.which("node")


def _serie(anni=3, seme=7):
    r = np.random.default_rng(seme)
    n = int(anni * 8766)
    ore = np.arange(n)
    giorno = ore / 24.0
    t = 13 + 11 * np.sin(2 * np.pi * (giorno - 110) / 365.25) + 5 * np.sin(2 * np.pi * (ore % 24 - 9) / 24) + r.normal(0, 2.5, n)
    ur = np.clip(70 - 15 * np.sin(2 * np.pi * (ore % 24 - 9) / 24) + r.normal(0, 12, n), 8, 100)
    t = np.round(t, 1)
    ur = np.round(ur)
    buchi = r.choice(n, 40, replace=False)
    t[buchi[:20]] = np.nan
    ur[buchi[20:]] = np.nan
    return {"inizio": "2022-01-01T00:00Z", "p": P.pressione(120), "t": t.astype(np.float32), "ur": ur.astype(np.float32)}


def _xh(s):
    v = P.vettori(s["t"].astype(float), s["ur"].astype(float), s["p"])
    return v["x"].astype(np.float32), v["h"].astype(np.float32)


# ------------------------------------------------------------------------------------------- casi a mano
def test_poche_ore_a_mano():
    p = 101325.0
    t = np.array([32.0, 24.0, 28.0], np.float32)
    ur = np.array([60.0, 40.0, 30.0], np.float32)
    v = P.vettori(t.astype(float), ur.astype(float), p)
    x, hh = v["x"], v["h"]
    r = LAT.calcola("estate", t, x, hh, [0, 1, 2], p, 26, 50, V=3600, riferimento=2)
    xt = P.stato(26, {"ur": 50}, p)["x"]
    m = 3600 / 3600 / (P.RA * 293.15 / 101.325)
    x32 = x.astype(np.float32).astype(float)
    attese = [m * (xi - xt) * 2501 for xi in x32 if xi > xt]
    assert r["ore"] == len(attese) == 1
    assert r["energia"] == pytest.approx(sum(attese), rel=1e-12)
    assert r["acqua"] == pytest.approx(sum(attese) / 2501 * 3600, rel=1e-12)
    # sensibile: 32 e 28 °C sopra 26 °C
    qs = sum(m * (1.006 + 1.86 * xi) * (ti - 26) for ti, xi in zip(t.astype(float), x32) if ti > 26)
    assert r["sensibile"] == pytest.approx(qs, rel=1e-12)
    assert r["shr"] == pytest.approx(qs / (qs + r["energia"]), rel=1e-12)
    # inverno con h vapore 2676 e riferimento 3 (densità fissa)
    t2 = np.array([0.0, 5.0, -3.0], np.float32)
    ur2 = np.array([80.0, 90.0, 70.0], np.float32)
    v2 = P.vettori(t2.astype(float), ur2.astype(float), p)
    ri = LAT.calcola("inverno", t2, v2["x"], v2["h"], [0, 1, 2], p, 20, 40, V=1000, riferimento=3, anni=0.5)
    xt2 = P.stato(20, {"ur": 40}, p)["x"]
    x2 = v2["x"].astype(np.float32).astype(float)
    att = sum(1000 / 3600 / ((1 + xi) / 1.2) * (xt2 - xi) * 2676 for xi in x2 if xi < xt2)
    assert ri["ore"] == 3 and ri["energia"] == pytest.approx(att, rel=1e-12)
    assert ri["energiaAnno"] == pytest.approx(att / 0.5) and ri["oreAnno"] == 6


def test_livello_e_curva():
    s = _serie(1)
    x, h = _xh(s)
    idx = np.nonzero(np.isfinite(x) & np.isfinite(s["t"]))[0]
    r = LAT.calcola("estate", s["t"], x, h, idx, s["p"], 24, 50, livello=1)
    assert r["piccoLivello"] <= r["picco"] and r["picco"] > 0
    assert r["curva"][0]["kW"] == pytest.approx(r["picco"])
    assert all(a["kW"] >= b["kW"] for a, b in zip(r["curva"], r["curva"][1:]))
    assert r["curva"][-1]["ore"] == pytest.approx(r["oreAnno"])
    assert sum(c["ore"] for c in r["classi"]) == pytest.approx(r["oreAnno"])
    assert sum(m["energia"] for m in r["mesi"]) == 0          # senza mesi: tutto zero
    r5 = LAT.calcola("estate", s["t"], x, h, idx, s["p"], 24, 50, livello=5)
    assert r5["piccoLivello"] <= r["piccoLivello"]


def test_monotonia_e_proporzionalita():
    s = _serie(2)
    x, h = _xh(s)
    idx = np.nonzero(np.isfinite(x) & np.isfinite(s["t"]))[0]
    ore_e = [LAT.calcola("estate", s["t"], x, h, idx, s["p"], 26, u)["ore"] for u in (40, 50, 60, 70)]
    assert ore_e == sorted(ore_e, reverse=True) and ore_e[0] > ore_e[-1]
    ore_i = [LAT.calcola("inverno", s["t"], x, h, idx, s["p"], 20, u)["ore"] for u in (30, 40, 50, 60)]
    assert ore_i == sorted(ore_i) and ore_i[0] < ore_i[-1]
    a = LAT.calcola("estate", s["t"], x, h, idx, s["p"], 26, 50, V=1000)
    b = LAT.calcola("estate", s["t"], x, h, idx, s["p"], 26, 50, V=2500)
    assert b["energia"] == pytest.approx(2.5 * a["energia"], rel=1e-12) and b["ore"] == a["ore"]


# ------------------------------------------------------------------------------------------- parità con node
NODO = r"""
const fs = require("fs"), S = process.argv[1], C = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const P = require(S + "/psicro.js"), G = require(S + "/gruppi_ore.js"), A = require(S + "/aria_latenti.js");
const f32 = (a) => Float32Array.from(a.map((v) => (v === null ? NaN : v)));
const serie = { inizio: C.inizio, n: C.t.length, t: f32(C.t), ur: f32(C.ur), p: C.p };
const V = P.vettori(serie.t, serie.ur, serie.p), campi = G.campiOrari(serie);
const num = (v) => (Number.isFinite(v) ? v : null);
const out = { x: Array.from(V.x, num), h: Array.from(V.h, num), mese: Array.from(campi.mese), gruppi: {}, casi: [] };
for (const [k, g] of Object.entries(C.gruppi)) out.gruppi[k] = { indici: Array.from(G.filtra(serie, g)), inizio: G.inizioAnni(serie, g.anni || 0) };
for (const c of C.casi) {
  const g = out.gruppi[c.gruppo];
  const r = A.calcola({ stagione: c.stagione, t: serie.t, x: V.x, h: V.h, indici: Uint32Array.from(g.indici), p: serie.p, tObiettivo: c.t,
    urObiettivo: c.ur, V: c.V, riferimento: c.rif, mese: campi.mese, anni: A.anniFinestra(serie.n, g.inizio), livello: c.livello });
  delete r.indiciSi; delete r.indiciNo;
  out.casi.push(r);
}
process.stdout.write(JSON.stringify(out, (k, v) => (typeof v === "number" && !Number.isFinite(v) ? null : v)));
"""


def _vicino(a, b, chiave=""):
    if isinstance(a, dict):
        for k in a:
            _vicino(a[k], b[k], f"{chiave}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), chiave
        for i, (u, v) in enumerate(zip(a, b)):
            _vicino(u, v, f"{chiave}[{i}]")
    elif isinstance(a, (int, float)) or a is None:
        if a is None or b is None or (isinstance(a, float) and math.isnan(a)):
            assert (a is None or math.isnan(a)) and (b is None or (isinstance(b, float) and math.isnan(b))), chiave
        else:
            assert b == pytest.approx(a, rel=1e-9, abs=1e-9), chiave
    else:
        assert a == b, chiave


@pytest.mark.skipif(not NODE, reason="node non installato")
def test_parita_node_python(tmp_path):
    s = _serie(3)
    gruppi = {"estate": {"da": "01/06", "a": "30/09", "anni": 2}, "inverno": {"da": "01/11", "a": "31/03", "anni": 0},
              "ufficio": {"da": "01/01", "a": "31/12", "oraDa": 8, "oraA": 18, "giorni": "feriali", "anni": 10}}
    casi = []
    for rif in (0, 1, 2, 3):
        for (t, u) in ((26, 50), (24.5, 45), (28, 65)):
            casi.append({"stagione": "estate", "gruppo": "estate", "t": t, "ur": u, "V": 1000 + 500 * rif, "rif": rif, "livello": 1})
        for (t, u) in ((20, 40), (21.5, 55), (18, 25)):
            casi.append({"stagione": "inverno", "gruppo": "inverno", "t": t, "ur": u, "V": 1000, "rif": rif, "livello": 0.4})
    casi.append({"stagione": "estate", "gruppo": "ufficio", "t": 25, "ur": 55, "V": 3000, "rif": 0, "livello": 5})
    casi.append({"stagione": "inverno", "gruppo": "ufficio", "t": 20, "ur": 40, "V": 3000, "rif": 0, "livello": 1})
    dati = {"inizio": s["inizio"], "p": s["p"], "t": [None if np.isnan(v) else float(v) for v in s["t"]],
            "ur": [None if np.isnan(v) else float(v) for v in s["ur"]], "gruppi": gruppi, "casi": casi}
    f = tmp_path / "casi.json"
    f.write_text(json.dumps(dati), encoding="utf-8")
    js = json.loads(subprocess.run([NODE, "-e", NODO, str(SITO), str(f)], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    x = np.array([np.nan if v is None else v for v in js["x"]], np.float32)
    h = np.array([np.nan if v is None else v for v in js["h"]], np.float32)
    # i vettori del gemello Python coincidono con quelli del browser (float32)
    xp, hp = _xh(s)
    ok = np.isfinite(x)
    assert np.array_equal(ok, np.isfinite(xp))
    assert np.max(np.abs(xp[ok].astype(float) - x[ok].astype(float))) < 1e-8
    # i gruppi (ultimi N anni) e i mesi locali coincidono con il gemello Python delle ore
    campi = P.campi_orari(dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc), len(s["t"]))
    assert np.array_equal(np.asarray(campi["mese"]), np.array(js["mese"]))
    mese = np.array(js["mese"])
    for c, rj in zip(casi, js["casi"]):
        g = js["gruppi"][c["gruppo"]]
        rp = LAT.calcola(c["stagione"], s["t"], x, h, g["indici"], s["p"], c["t"], c["ur"], V=c["V"], riferimento=c["rif"],
                         mese=mese, anni=LAT.anni_finestra(len(s["t"]), g["inizio"]), livello=c["livello"])
        assert rp["ore"] == rj["ore"] and rp["oreGruppo"] == rj["oreGruppo"], c
        rp = json.loads(json.dumps(rp, default=float))
        _vicino(rp, rj, f"{c['stagione']} {c['t']}/{c['ur']} rif {c['rif']}")
        assert rj["ore"] > 0


@pytest.mark.skipif(not NODE, reason="node non installato")
def test_ore_esattamente_all_obiettivo_non_contano(tmp_path):
    """(14/11/2026, verifica indipendente) un'ora a 26,0 °C e 50 % non va deumidificata (prima contava per
    l'arrotondamento in Float32, con Q ≈ 0); stessa regola in node e in Python, anche d'inverno a 20,0 °C e 40 %."""
    t = [26.0] * 10 + [27.0] * 3 + [20.0] * 10 + [15.0] * 4
    ur = [50.0] * 10 + [60.0] * 3 + [40.0] * 10 + [30.0] * 4
    s = {"inizio": "2025-07-01T00:00Z", "p": P.pressione(120), "t": np.array(t, np.float32), "ur": np.array(ur, np.float32)}
    casi = [{"stagione": "estate", "gruppo": "tutto", "t": 26, "ur": 50, "V": 1000, "rif": 0, "livello": 1},
            {"stagione": "inverno", "gruppo": "tutto", "t": 20, "ur": 40, "V": 1000, "rif": 0, "livello": 1}]
    dati = {"inizio": s["inizio"], "p": s["p"], "t": t, "ur": ur, "gruppi": {"tutto": {}}, "casi": casi}
    f = tmp_path / "casi.json"
    f.write_text(json.dumps(dati), encoding="utf-8")
    js = json.loads(subprocess.run([NODE, "-e", NODO, str(SITO), str(f)], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    x, h = _xh(s)
    for c, rj, attese in zip(casi, js["casi"], (3, 4)):
        rp = LAT.calcola(c["stagione"], s["t"], x, h, list(range(len(t))), s["p"], c["t"], c["ur"], V=1000, riferimento=0)
        assert rp["ore"] == rj["ore"] == attese, (c, rp["ore"], rj["ore"])
