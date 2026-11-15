"""Free cooling e recupero (14/11/2026): aria/freecooling.py, controlli a mano su ore singole e parità con il sito
(fase5-sito/sito/aria_freecooling.js eseguito in node) su una serie oraria sintetica di 3 anni, 4 gruppi di ore e 6 insiemi
di opzioni (predefinite, economizzatore a temperatura, recuperatore entalpico, regola della brina a soglia, senza
sbrinamento, portata riferita all'ambiente/standard/densità fissa). La parità si salta se node manca."""
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
from aria import freecooling as F  # noqa: E402
from aria import psicro as P  # noqa: E402

NODE = shutil.which("node")
p0 = 101325.0


# ---------------------------------------------------------------------------------------------- controlli a mano

def _x(t, ur, p=p0):
    """umidità specifica da T e UR, scritta qui da capo (Hyland–Wexler sull'acqua) per non dipendere da psicro."""
    T = t + 273.15
    ps = math.exp(-5800.2206 / T + 1.3914993 - 0.048640239 * T + 0.000041764768 * T * T - 0.000000014452093 * T ** 3 + 6.5459673 * math.log(T))
    pw = ur / 100 * ps
    return 0.621945 * pw / (p - pw)


def _h(t, x):
    return 1.006 * t + x * (2501 + 1.86 * t)


def _m(t, x, V=10000.0, p=p0):
    return V / 3600 / (0.287042 * (t + 273.15) * (1 + 1.607858 * x) / (p / 1000))


def test_ora_a_10_gradi_predefiniti():
    """T_e = 10 °C, UR 70 %, opzioni predefinite: sotto la T di bilancio (12 °C) → recupero invernale sul 30 % di aria
    esterna, ε = 0,7 verso l'ambiente d'inverno 20 °C/40 %; nessun free cooling, nessuna brina."""
    r = F.un_ora(10, 70, p0)
    xe = _x(10, 70)
    m = _m(10, xe)
    t_out = 10 + 0.7 * (20 - 10)                     # 17 °C, x invariata (recuperatore sensibile)
    atteso = 0.3 * m * (_h(t_out, xe) - _h(10, xe))
    assert r["regime"] == "invernale"
    assert r["rec"] == pytest.approx(atteso, rel=1e-9)
    assert r["rec"] == pytest.approx(7.33, abs=0.01)     # ≈ 0,3·3,434 kg/s·7,11 kJ/kg
    assert r["fcT"] == r["fcH"] == r["perso"] == 0
    assert r["pVent"] == pytest.approx(2 * 3000 / 3600 * 150 / 0.6 / 1000)   # 0,417 kW


def test_ora_a_10_gradi_in_raffrescamento():
    """Stessa ora con T di bilancio 5 °C: è free cooling totale (T_e ≤ 16 °C), il freddo evitato è tutta la batteria
    della miscela con il 30 % di aria esterna, Q0 = ṁ·(h_mix − h(16 °C, x_mix))."""
    r = F.un_ora(10, 70, p0, {"tBilancio": 5})
    xe, xr = _x(10, 70), _x(26, 50)
    m = _m(10, xe)
    xmix, hmix = 0.3 * xe + 0.7 * xr, 0.3 * _h(10, xe) + 0.7 * _h(26, xr)
    q0 = m * (hmix - _h(16, xmix))
    assert r["regime"] == "totale"
    assert r["fcT"] == pytest.approx(q0, rel=1e-9) and r["fcH"] == pytest.approx(q0, rel=1e-9)
    assert r["rec"] == 0


def test_regimi_estivi_e_brina():
    assert F.un_ora(14, 60, p0)["regime"] == "totale"
    assert F.un_ora(22, 50, p0)["regime"] == "parziale"
    assert F.un_ora(29, 20, p0)["regime"] == "entalpico"                       # caldo ma secco: h < h ripresa
    assert F.un_ora(29, 20, p0, {"economizzatore": "temperatura"})["regime"] == "estivo"
    r = F.un_ora(32, 50, p0)
    xe = _x(32, 50)
    assert r["regime"] == "estivo"
    assert r["rec"] == pytest.approx(0.3 * _m(32, xe) * (_h(32, xe) - _h(32 - 0.7 * 6, xe)), rel=1e-9)
    # aria umida più fresca dell'ambiente: a temperatura il free cooling costa (risparmio negativo), l'entalpico no
    u = F.un_ora(24, 90, p0)
    assert u["fcT"] < 0 and u["fcH"] == 0 and u["regime"] == "nessuno"
    # −12 °C: espulsione a 20 − 0,7·32 = −2,4 °C, sotto 0 e sotto la rugiada → brina; by-pass fino a 0 °C (ε = 20/32)
    b = F.un_ora(-12, 80, p0)
    xe = P.x_da_ur(-12, 80, p0)                     # sotto 0 °C: psat sul ghiaccio (psicro)
    m = _m(-12, xe)
    pieno = 0.3 * m * (_h(-12 + 0.7 * 32, xe) - _h(-12, xe))
    by = 0.3 * m * (_h(-12 + 20, xe) - _h(-12, xe))
    assert b["regime"] == "brina"
    assert b["rec"] == pytest.approx(by, rel=1e-9) and b["perso"] == pytest.approx(pieno - by, rel=1e-9)
    assert F.un_ora(-12, 80, p0, {"sbrinamento": False})["rec"] == pytest.approx(pieno, rel=1e-9)
    # regola a soglia: −6 °C è brina, −4 no; il by-pass limita lo scambio a quello di −5 °C
    s = F.un_ora(-6, 80, p0, {"regolaBrina": "soglia"})
    assert s["regime"] == "brina" and s["perso"] > 0
    assert F.un_ora(-4, 80, p0, {"regolaBrina": "soglia"})["regime"] == "invernale"


def test_monotonia():
    """più efficienza → più recupero; T di mandata più alta → più ore di free cooling totale; UTA a tutt'aria esterna → zero."""
    rng = np.random.default_rng(1)
    t = rng.uniform(-10, 35, 5000)
    ur = rng.uniform(20, 95, 5000)
    V = P.vettori(t, ur, p0)
    idx = np.arange(5000)

    def r(**o):
        return F.riassumi(F.calcola(t, V["x"], V["h"], p0, o), idx, 1.0)
    a, b = r(), r(epsS=0.85)
    assert b["kwhInverno"] > a["kwhInverno"] and b["kwhEstate"] > a["kwhEstate"]
    c = r(tMandata=18)           # più ore di free cooling totale (le ore attive dell'entalpico non dipendono da T_m)
    assert c["oreRegime"][1] > a["oreRegime"][1] and c["oreFcH"] == a["oreFcH"] and c["oreFcT"] == a["oreFcT"]
    assert r(quotaMinima=100)["kwhFcT"] == pytest.approx(0, abs=1e-6)
    e = r(epsL=0.6)
    assert e["kwhEstate"] > a["kwhEstate"]
    assert a["kwhElettrici"] == pytest.approx(a["oreRecupero"] * F.potenza_ventilatore(F.opzioni({}, p0)))


# ---------------------------------------------------------------------------------------------- parità con il sito
OPZIONI = [{}, {"economizzatore": "temperatura", "tMandata": 14, "quotaMinima": 20},
           {"epsS": 0.75, "epsL": 0.6, "riferimento": 1, "tBilancio": 8, "estate": {"t": 24, "ur": 55}},
           {"regolaBrina": "soglia", "tSoglia": -2, "riferimento": 2, "inverno": {"t": 21, "ur": 30}, "dP": 220, "etaV": 0.5},
           {"sbrinamento": False, "riferimento": 3, "xMax": 0.011, "V": 4000},
           {"quotaMinima": 100, "tBilancio": -5, "epsS": 0.8}]
GRUPPI = [{"oraDa": 8, "oraA": 18, "giorni": "feriali"}, {}, {"da": "01/06", "a": "30/09", "anni": 2}, {"da": "01/11", "a": "31/03", "oraDa": 22, "oraA": 6}]


@pytest.fixture(scope="module")
def sito(tmp_path_factory):
    if not NODE:
        pytest.skip("node non installato")
    R = np.random.default_rng(20261114)
    n = 3 * 8766
    i = np.arange(n)
    t = np.round((12 + 13 * -np.cos(2 * np.pi * (i / 24 - 15) / 365.25) + 5 * np.cos(2 * np.pi * (i % 24 - 14) / 24) + R.normal(0, 3, n)) * 10) / 10
    ur = np.round(np.clip(70 - 20 * np.cos(2 * np.pi * (i % 24 - 14) / 24) + R.normal(0, 12, n), 10, 100))
    t[R.integers(0, n, 30)] = np.nan
    serie = {"inizio": "2023-01-01T00:00Z", "p": P.pressione(250),
             "t": [None if math.isnan(v) else float(v) for v in t], "ur": [float(v) for v in ur]}
    ore = [[10, 70, {}], [10, 70, {"tBilancio": 5}], [-12, 80, {}], [32, 50, {"epsL": 0.6}], [24, 90, {"economizzatore": "temperatura"}]]
    casi = {"serie": serie, "opzioni": OPZIONI, "gruppi": GRUPPI, "ore": ore}
    f = tmp_path_factory.mktemp("fc") / "casi.json"
    f.write_text(json.dumps(casi), encoding="utf-8")
    out = subprocess.run([NODE, str(QUI / "freecooling_node.js"), str(f)], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return casi, json.loads(out)


def _arr(v):
    return np.array([np.nan if a is None else a for a in v], dtype=float)


def test_parita_ora_per_ora(sito):
    casi, js = sito
    p = casi["serie"]["p"]
    t = np.array([np.nan if v is None else v for v in casi["serie"]["t"]], dtype=np.float32).astype(float)
    x, h = _arr(js["x"]), _arr(js["h"])            # x e h del browser (Float32): stesso ingresso nei due calcoli
    regimi = set()
    for o, r in zip(casi["opzioni"], js["casi"]):
        R = F.calcola(t, x, h, p, o)
        for k, v in R["opzioni"].items():
            assert r["opzioni"][k] == pytest.approx(v, rel=1e-12) if isinstance(v, float) else r["opzioni"][k] == v, (o, k)
        assert np.array_equal(np.array(r["regime"]), R["regime"]), o
        assert np.array_equal(np.array(r["bandiere"]), R["bandiere"]), o
        for k in ("fcT", "fcH", "rec", "perso", "q0"):
            assert np.allclose(np.array(r[k]), R[k], rtol=1e-10, atol=1e-10), (o, k)
        assert r["pVent"] == pytest.approx(R["pVent"], rel=1e-12)
        regimi |= set(R["regime"].tolist())
    assert {0, 1, 2, 3, 4, 5, 6, 255} <= regimi       # le prove passano per tutti i regimi


def test_parita_riassunti(sito):
    casi, js = sito
    p = casi["serie"]["p"]
    t = np.array([np.nan if v is None else v for v in casi["serie"]["t"]], dtype=np.float32).astype(float)
    x, h = _arr(js["x"]), _arr(js["h"])
    mese = np.array(js["mese"])
    for o, r in zip(casi["opzioni"], js["casi"]):
        R = F.calcola(t, x, h, p, o)
        for idx, anni, rj in zip(js["indici"], js["anni"], r["riassunti"]):
            rp = F.riassumi(R, np.array(idx), anni, mese)
            for k, v in rp.items():
                if k == "mensile":
                    for q, w in v.items():
                        assert rj[k][q] == pytest.approx(w, rel=1e-9, abs=1e-6), (o, q)
                elif isinstance(v, list):
                    assert rj[k] == pytest.approx(v, rel=1e-9, abs=1e-9), (o, k)
                elif isinstance(v, float) and math.isnan(v):
                    assert rj[k] is None, (o, k)
                else:
                    assert rj[k] == pytest.approx(v, rel=1e-9, abs=1e-9), (o, k)


def test_parita_ore_singole(sito):
    casi, js = sito
    p = casi["serie"]["p"]
    for (tt, u, o), r in zip(casi["ore"], js["ore"]):
        q = F.un_ora(tt, u, p, o)
        assert r["regime"] == q["regime"], (tt, u, o)
        for k in ("fcT", "fcH", "rec", "perso", "q0", "m"):
            assert r[k] == pytest.approx(q[k], rel=1e-10, abs=1e-12), (tt, u, o, k)
