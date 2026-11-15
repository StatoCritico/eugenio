"""Ore di funzionamento (14/11/2026): aria/ore.py e parità con fase5-sito/sito/aria_ore.js (node) sulla serie sintetica di
prova del sito (?prova=1, 5 anni con data di fine fissa): statistiche, classi di T e x, matrice T×x, zona di comfort con
più rettangoli; più i casi a mano (regole della zona) e i tempi su 750.000 ore. La parte node si salta se node manca."""
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

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from aria import ore as O  # noqa: E402
from aria import psicro as P  # noqa: E402

NODE = shutil.which("node")
GRUPPI = [
    {"da": "01/06", "a": "30/09", "anni": 5}, {"da": "01/11", "a": "31/03", "anni": 2},
    {"da": "01/06", "a": "30/09", "oraDa": 8, "oraA": 18, "giorni": "feriali", "anni": 1},
    {"oraDa": 22, "oraA": 6, "anni": 0}, {"da": "10/08", "a": "12/08", "oraDa": 14, "oraA": 15, "anni": 1}, {},
]
ZONE = [{"tMin": 20, "tMax": 26, "urMin": 30, "urMax": 60}, {"tMin": 18.5, "tMax": 24, "urMin": 40, "urMax": 55}, {"tMin": -5, "tMax": 40, "urMin": 0, "urMax": 100}]


# ------------------------------------------------------------------------------------------------ senza node
def test_zona_regole_a_mano():
    t = [10.0, 30.0, 22.0, 22.0, 22.0, 5.0, 26.0, 20.0]
    ur = [50.0, 50.0, 20.0, 80.0, 45.0, 20.0, 60.0, 30.0]
    z = O.zona(t, ur, 101325.0, np.arange(8), 20, 26, 30, 60)
    # 10 °C/50 %: riscaldo a 20 °C → UR ≈ 26 % → anche umidificare; 30 °C/50 %: raffreddo a 26 °C → UR ≈ 63 % → deumidificare
    assert z == {"ore": 8, "dentro": 3, "fuori": 5, "riscaldare": 2, "raffreddare": 1, "umidificare": 3, "deumidificare": 2}


def test_statistiche_e_classi_semplici():
    t = np.array([0.0, 1.0, 2.5, 3.0, np.nan], dtype=np.float32)
    ur = np.array([50, 50, 50, 50, 50], dtype=np.float32)
    s = O.statistiche(t, ur, 101325.0, np.arange(5), 0, 8766)
    assert s["ore"] == 4 and s["anni"] == 1 and s["oreAnno"] == 4 and s["tMin"] == 0 and s["tMax"] == 3
    assert s["tMedia"] == pytest.approx(1.625) and s["urMedia"] == 50
    assert s["x50"] == pytest.approx((P.x_da_ur(1, 50, 101325) + P.x_da_ur(2.5, 50, 101325)) / 2 * 1000, rel=1e-6)
    c = O.classi_t(t, ur, 101325.0, np.arange(5))
    assert [(r["da"], r["a"], r["ore"]) for r in c] == [(0, 2, 2), (2, 4, 2)]
    m = O.matrice_tx(t, ur, 101325.0, np.arange(5))
    assert sum(map(sum, m["ore"])) == 4
    assert O.statistiche(t, ur, 101325.0, np.array([4]), 0, 10)["ore"] == 0


# ------------------------------------------------------------------------------------------------ parità con il sito
@pytest.fixture(scope="module")
def js(tmp_path_factory):
    if not NODE:
        pytest.skip("node non installato")
    f = tmp_path_factory.mktemp("ore") / "casi.json"
    f.write_text(json.dumps({"istat": "037006", "anni": 5, "fine": "2026-11-01T12:00:00Z", "gruppi": GRUPPI, "zone": ZONE}), encoding="utf-8")
    out = subprocess.run([NODE, str(QUI / "parita_ore_node.js"), str(f)], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


def _serie(js):
    S = js["serie"]
    t = np.array([np.nan if v is None else v for v in S["t"]], dtype=np.float32)
    ur = np.array([np.nan if v is None else v for v in S["ur"]], dtype=np.float32)
    return S, t, ur


def _uguali(a, b, rel=2e-6, abs_=1e-6):
    if a is None or (isinstance(b, float) and math.isnan(b)):
        return a is None and (b is None or math.isnan(b))
    return a == pytest.approx(b, rel=rel, abs=abs_)


def test_gruppi_uguali_al_filtro_python(js):
    S, t, ur = _serie(js)
    C = P.campi_orari(dt.datetime.fromtimestamp(S["inizio"] / 1000, dt.timezone.utc), S["n"])
    valide = np.isfinite(t) & np.isfinite(ur)
    for g, r in zip(GRUPPI, js["gruppi"]):
        atteso = P.filtra_gruppo(C, g, valide=valide, indice_inizio_anni=r["i0"])
        assert np.array_equal(np.array(r["indici"], dtype=np.uint32), atteso), g
    assert len(js["gruppi"][0]["indici"]) > 14000 and len(js["gruppi"][4]["indici"]) == 3


def test_statistiche_parita(js):
    S, t, ur = _serie(js)
    for g, r in zip(GRUPPI, js["gruppi"]):
        s = O.statistiche(t, ur, S["p"], np.array(r["indici"]), r["i0"], S["n"])
        for k, v in s.items():
            assert _uguali(r["stat"][k], v, abs_=2e-3 if k == "twbMax" else 1e-6), (g, k, r["stat"][k], v)


def test_classi_e_matrice_parita(js):
    S, t, ur = _serie(js)
    for g, r in zip(GRUPPI, js["gruppi"]):
        idx = np.array(r["indici"])
        for nome, f in (("classiT", O.classi_t), ("classiX", O.classi_x)):
            py = f(t, ur, S["p"], idx)
            assert len(py) == len(r[nome]), (g, nome)
            for a, b in zip(r[nome], py):
                assert a["da"] == b["da"] and a["a"] == b["a"] and a["ore"] == b["ore"], (g, nome, a, b)
                for k in b:
                    assert _uguali(a[k], b[k], rel=1e-6, abs_=2e-3 if k == "twb" else 1e-5), (g, nome, k)
        M = O.matrice_tx(t, ur, S["p"], idx)
        assert r["matrice"] == M
        assert sum(c["ore"] for c in r["classiT"]) == len(idx)


def test_zona_parita(js):
    S, t, ur = _serie(js)
    for g, r in zip(GRUPPI, js["gruppi"]):
        for z, a in zip(ZONE, r["zone"]):
            b = O.zona(t, ur, S["p"], np.array(r["indici"]), z["tMin"], z["tMax"], z["urMin"], z["urMax"])
            assert a == b, (g, z)
            assert a["dentro"] + a["fuori"] == a["ore"]
    assert js["gruppi"][5]["zone"][2]["dentro"] > 0.9 * js["gruppi"][5]["zone"][2]["ore"]


def test_tempi_750000_ore(js):
    assert js["msFiltro"] < 300, js["msFiltro"]            # filtro di un gruppo: pochi millisecondi
    assert js["msCalcolo"] < 3000, js["msCalcolo"]         # statistiche, classi e zona di 750.000 ore
    assert js["nFiltro"] > 0
