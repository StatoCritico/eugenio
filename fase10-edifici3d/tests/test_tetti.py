"""Tetti a falda (08/11/2026): parità tra `edifici3d/tetti.py` e `fase5-sito/sito/edifici_calcoli.js` (in node) per la
stima dal colmo e per l'ipotesi automatica (capanna e padiglione, 22° in pianura e 32° in montagna, piani per capannoni,
corpi grandi, bassi, con cortile), più le regole pianura/montagna e i conteggi per archivio."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from edifici3d import tetti as T  # noqa: E402

SITO = QUI.parents[1] / "fase5-sito" / "sito"

RETT = [[0, 0], [20, 0], [20, 10], [0, 10]]                       # capanna (20 × 10)
QUAD = [[0, 0], [12, 0], [12, 11], [0, 11]]                       # padiglione (rapporto < 1,3)
RUOT = [[0, 0], [17.3, 10], [12.3, 18.66], [-5, 8.66]]             # rettangolo ruotato di 30°
ELLE = [[0, 0], [16, 0], [16, 6], [6, 6], [6, 12], [0, 12]]         # L (riempimento 62 %: piano)
GRANDE = [[0, 0], [60, 0], [60, 30], [0, 30]]                     # 1.800 m²
LARGO = [[0, 0], [40, 0], [40, 27], [0, 27]]                      # 1.080 m², lato corto 27 m

CASI = [
    {"nome": "capanna_pianura", "c": {"ring": RETT, "gronda": 9, "uso": "residenziale"}, "o": {"quota": 5, "istat": "099014"}},
    {"nome": "capanna_montagna_nord", "c": {"ring": RETT, "gronda": 7, "uso": "residenziale"}, "o": {"quota": 650, "istat": "040001"}},
    {"nome": "collina_centro_650", "c": {"ring": RETT, "gronda": 7}, "o": {"quota": 650, "istat": "058091"}},
    {"nome": "montagna_centro_720", "c": {"ring": RETT, "gronda": 7}, "o": {"quota": 720, "istat": "058091"}},
    {"nome": "padiglione_pianura", "c": {"ring": QUAD, "gronda": 9}, "o": {"quota": 10, "istat": "099014"}},
    {"nome": "padiglione_montagna", "c": {"ring": QUAD, "gronda": 6}, "o": {"quota": 900}},
    {"nome": "ruotato", "c": {"ring": RUOT, "gronda": 10}, "o": {"quota": 0}},
    {"nome": "senza_quota", "c": {"ring": RETT, "gronda": 9}, "o": {}},
    {"nome": "capannone", "c": {"ring": RETT, "gronda": 8, "uso": "capannone"}, "o": {"quota": 5}},
    {"nome": "commerciale", "c": {"ring": RETT, "gronda": 8, "uso": "commerciale"}, "o": {"quota": 5}},
    {"nome": "tipo_industriale", "c": {"ring": RETT, "gronda": 8, "tipo_edificio": "edificio industriale"}, "o": {}},
    {"nome": "grande", "c": {"ring": GRANDE, "gronda": 12}, "o": {}},
    {"nome": "lato_corto_27", "c": {"ring": LARGO, "gronda": 12}, "o": {}},
    {"nome": "basso", "c": {"ring": RETT, "gronda": 2.5}, "o": {}},
    {"nome": "elle", "c": {"ring": ELLE, "gronda": 9}, "o": {}},
    {"nome": "cortile", "c": {"ring": GRANDE[:], "buchi": [[[20, 10], [40, 10], [40, 20], [20, 20]]], "gronda": 12}, "o": {}},
    # (09/11/2026) cavedio di 3 × 3 m in una casa di 16 × 10 m: non è un cortile, tetto a falde
    {"nome": "cavedio", "c": {"ring": RETT, "buchi": [[[6, 4], [9, 4], [9, 7], [6, 7]]], "gronda": 10}, "o": {"quota": 511, "istat": "040001"}},
    # cortile vero in una casa piccola: 5 × 4 = 20 m² sotto i 25 m² ma oltre il 10 % della pianta
    {"nome": "cortile_quota", "c": {"ring": RETT, "buchi": [[[5, 3], [10, 3], [10, 7], [5, 7]]], "gronda": 10}, "o": {}},
]
COLMO = [
    {"nome": "colmo_capanna", "c": {"ring": RETT, "gronda": 9, "colmo": 12}},
    {"nome": "colmo_padiglione", "c": {"ring": QUAD, "gronda": 9, "colmo": 11.5}},
    {"nome": "colmo_monofalda", "c": {"ring": RUOT, "gronda": 9, "colmo": 11}, "tipo": "monofalda"},
    {"nome": "colmo_basso", "c": {"ring": RETT, "gronda": 9, "colmo": 9.2}},
]

NODE = """
const E = require(process.argv[1]); const casi = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const k of casi.ipotesi) out[k.nome] = E.tettoIpotizzato(k.c, k.o);
for (const k of casi.colmo) out[k.nome] = E.faldeStimate(k.c, k.tipo || null);
out.zone = casi.zone.map(([q, i]) => E.zonaAltimetrica(q, i));
console.log(JSON.stringify(out));
"""
ZONE = [[599, "099014"], [600, "099014"], [699, "058091"], [700, "058091"], [650, None], [650, "093001"], [650, "109001"], [None, "040001"]]


def py_ipotesi(k):
    c, o = k["c"], k["o"]
    return T.tetto_ipotizzato(c["ring"], c["gronda"], c.get("uso"), c.get("tipo_edificio"), c.get("buchi", ()), o.get("quota"), o.get("istat"))


def uguali(a, b, percorso=""):
    if isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b), (percorso, a, b)
        for k in a:
            uguali(a[k], b[k], f"{percorso}.{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), (percorso, a, b)
        for i, (x, y) in enumerate(zip(a, b)):
            uguali(x, y, f"{percorso}[{i}]")
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert isinstance(b, (int, float)) and math.isclose(a, b, abs_tol=1e-6), (percorso, a, b)
    else:
        assert a == b, (percorso, a, b)


@pytest.mark.skipif(not shutil.which("node"), reason="node non disponibile")
def test_parita_python_js(tmp_path):
    f = tmp_path / "casi.json"
    f.write_text(json.dumps({"ipotesi": CASI, "colmo": COLMO, "zone": ZONE}), encoding="utf-8")
    r = subprocess.run(["node", "-e", NODE, str(SITO / "edifici_calcoli.js"), str(f)], capture_output=True, text=True, check=True, timeout=60)
    js = json.loads(r.stdout)
    for k in CASI:
        uguali(py_ipotesi(k), js[k["nome"]], k["nome"])
    for k in COLMO:
        c = k["c"]
        uguali(T.falde_stimate(c["ring"], c["gronda"], c["colmo"], (), k.get("tipo")), js[k["nome"]], k["nome"])
    uguali([T.zona_altimetrica(q, i) for q, i in ZONE], js["zone"], "zone")


def test_ipotesi_geometria():
    r = T.tetto_ipotizzato(RETT, 9, "residenziale", quota=5, istat="099014")
    assert r["tipo"] == "capanna" and r["inclinazione"] == 22 and not r["montagna"]
    assert r["colmo"] == pytest.approx(9 + 5 * math.tan(math.radians(22)), abs=0.01)
    assert sorted(f["orientamento"] for f in r["falde"]) == [0, 180]
    assert all(f["pendenza"] == 22 for f in r["falde"])
    m = T.tetto_ipotizzato(QUAD, 6, quota=900)
    assert m["tipo"] == "padiglione" and m["inclinazione"] == 32 and m["montagna"] and len(m["falde"]) == 4
    assert m["colmo"] == pytest.approx(6 + 5.5 * math.tan(math.radians(32)), abs=0.01)
    # area in pianta delle falde = area del corpo
    assert sum(f["area_pianta"] for f in m["falde"]) == pytest.approx(132, abs=0.3)


def test_piani_plausibili():
    assert T.tetto_ipotizzato(RETT, 8, "capannone")["motivo"].startswith("uso produttivo")
    assert T.tetto_ipotizzato(RETT, 8, "commerciale")["motivo"].startswith("uso commerciale")
    assert T.tetto_ipotizzato(RETT, 8, tipo_edificio="edificio industriale")["piano"]
    assert T.tetto_ipotizzato(GRANDE, 12)["motivo"] == "corpo molto grande (1800 m²)"
    assert T.tetto_ipotizzato(LARGO, 12)["motivo"] == "lato corto oltre 25 m (27 m)"
    assert T.tetto_ipotizzato(RETT, 2.5)["motivo"].startswith("corpo basso")
    assert T.tetto_ipotizzato(ELLE, 9)["motivo"] == "forma poco rettangolare"


def test_zona_altimetrica_nord_e_centro_sud():
    assert not T.zona_altimetrica(599, "099014")["montagna"] and T.zona_altimetrica(600, "099014")["montagna"]
    assert not T.zona_altimetrica(699, "058091")["montagna"] and T.zona_altimetrica(700, "058091")["montagna"]
    assert T.comune_del_nord("093001") and not T.comune_del_nord("109001") and T.comune_del_nord(None) is None
    assert T.zona_altimetrica(None)["inclinazione"] == 22


def test_conta_tetti_cascata():
    def feat(i, ring, **p):
        lon0, lat0 = 12.5, 44.0
        kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
        g = {"type": "Polygon", "coordinates": [[[lon0 + x / kx, lat0 + y / ky] for x, y in ring + [ring[0]]]]}
        return {"type": "Feature", "geometry": g, "properties": {"id": i, "gronda": 9, **p}}
    fs = [feat("a", RETT, colmo=12), feat("b", RETT, quota_terreno=5), feat("c", QUAD, quota_terreno=800),
          feat("d", RETT, uso="capannone"), feat("e", RETT, quota_terreno=5)]
    n = T.conta_tetti(fs, "040001", lidar={"e": {"stato": "ok"}})
    assert (n["lidar"], n["colmo"], n["ipotesi"], n["pianura"], n["montagna"], n["piano"]) == (1, 1, 2, 1, 1, 1)
    assert n["motivi_piano"] == {"uso produttivo": 1}


def test_cavedio_non_e_un_cortile():
    """09/11/2026, prova 13 di Paolo (Bagno di Romagna, foglio 54 particella 216): un buco piccolo (cavedio o volume
    interno) non rende piano il tetto ipotizzato; un cortile vero sì."""
    casi = {k["nome"]: k for k in CASI}
    r = py_ipotesi(casi["cavedio"])
    assert not r.get("piano") and r["inclinazione"] == 22, r
    assert py_ipotesi(casi["cortile_quota"])["motivo"] == "corpo con cortile"
    assert py_ipotesi(casi["cortile"])["motivo"] == "corpo con cortile"
