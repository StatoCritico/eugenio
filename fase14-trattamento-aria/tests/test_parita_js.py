"""Parità tra il sito (fase5-sito/sito/psicro.js e gruppi_ore.js, eseguiti in node) e il gemello Python aria/psicro.py:
2.000 stati a caso (−25…50 °C, UR 1–100 %, quote −100…2.500 m), 300 sequenze UTA a caso (tipi, parametri, AUTO, vuoti)
più i casi di riferimento, i vettori di una serie oraria sintetica di 3 anni, le condizioni di progetto (99 % / 1 % e
99,6 % / 0,4 %), i campi dell'ora locale (ora legale europea) e i filtri dei gruppi di ore. Si salta se node manca."""
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
from aria import psicro as P  # noqa: E402

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="node non installato")
R = np.random.default_rng(20261114)


def _par(r, tipo):
    """parametri a caso ma sensati per il tipo (a volte vuoti, AUTO o testo con la virgola)."""
    c = P.codice_tipo(tipo)
    scelte = {
        2: [["AUTO"], [round(r.uniform(0, 1), 2)], [None]],
        3: [[round(r.uniform(0.4, 0.8), 2)], [round(r.uniform(0.4, 0.8), 2), round(r.uniform(0.3, 0.7), 2)], [None]],
        4: [[round(r.uniform(15, 45), 1)], [None, round(r.uniform(1, 40), 1)], []],
        5: [[round(r.uniform(5, 25), 1)], [None, round(r.uniform(1, 40), 1)], []],
        6: [["AUTO", 0.1], [round(r.uniform(5, 12), 2), round(r.uniform(0.05, 0.2), 2)], [None, 0.1, round(r.uniform(4, 14), 1)], ["AUTO"]],
        7: [["AUTO"], [None, round(r.uniform(60, 100))], [None, None, round(r.uniform(0.5, 0.95), 2)], [round(r.uniform(3, 12), 2)]],
        8: [["AUTO"], [None, round(r.uniform(30, 70))], [round(r.uniform(4, 12), 2), None, 2600]],
        9: [["AUTO", None, 90], ["AUTO"], [round(r.uniform(10, 30), 1)], [None, round(r.uniform(2, 30), 1)]],
        10: [["AUTO"], [round(r.uniform(15, 40), 1)], [None, round(r.uniform(1, 30), 1)]],
        11: [[0.7], ["0,8"], [None, round(r.uniform(0.2, 3), 2)]],
    }.get(c, [[None]])
    return scelte[r.integers(0, len(scelte))]


def _casi():
    stati = [[float(r_) for r_ in (R.uniform(-25, 50), R.uniform(1, 100), P.pressione(R.uniform(-100, 2500)))] for _ in range(2000)]
    # (14/11/2026) stati vicino a 0 °C dove il bulbo umido ha due radici (scelta di psychrolib): JS = Python
    stati += [[float(t), float(u), P.pressione(z)] for t in np.arange(-2, 12, 0.5) for u in (10, 20, 28, 35, 50, 70, 90) for z in (0, 12, 800)]
    sequenze = []
    for k in range(300):
        inv = bool(k % 2)
        righe = []
        for _ in range(int(R.integers(1, 8))):
            tipo = P.TIPI[int(R.integers(0, 11))] if R.random() > 0.03 else "Pompa di calore"
            righe.append([tipo, *(_par(R, tipo) + [None, None, None])[:3]])
        sequenze.append({"p": P.pressione(float(R.uniform(0, 1500))), "V": float(R.uniform(800, 20000)), "quotaEsterna": float(R.choice([100, 70, 30])),
                         "riferimento": int(R.integers(0, 4)), "stagione": "inverno" if inv else "estate",
                         "esterno": {"t": float(R.uniform(-15, 5) if inv else R.uniform(26, 38)), "ur": float(R.uniform(30, 95))},
                         "ambiente": {"t": float(R.uniform(18, 22) if inv else R.uniform(23, 27)), "ur": float(R.uniform(35, 60))},
                         "Qs": float(R.uniform(0, 30000)), "Ql": float(R.uniform(0, 6000)), "righe": righe})
    est = dict(p=101325.0, stagione="estate", esterno={"t": 32, "ur": 50}, ambiente={"t": 26, "ur": 50}, Qs=5000, Ql=1500)
    inv = dict(p=101325.0, stagione="inverno", esterno={"t": -5, "ur": 80}, ambiente={"t": 20, "ur": 50}, Qs=8000, Ql=500)
    for V in (1000, 5000):
        sequenze += [{**est, "V": V}, {**est, "V": V, "quotaEsterna": 70}, {**inv, "V": V},
                     {**inv, "V": V, "righe": [["Recuperatore di calore", 0.6], ["Post-riscaldamento", "AUTO"], ["Umidificazione a vapore", "AUTO"]]}]
    n = 3 * 8766
    i = np.arange(n)
    t = np.round((13 + 10.5 * -np.cos(2 * np.pi * (i / 24 - 15) / 365.25) + 4 * np.cos(2 * np.pi * (i % 24 - 14) / 24) + R.normal(0, 2, n)) * 10) / 10
    ur = np.round(np.clip(72 - 18 * np.cos(2 * np.pi * (i % 24 - 14) / 24) + R.normal(0, 8, n), 12, 100))
    buchi = R.integers(0, n, 40)
    t[buchi] = np.nan
    inizio = "2023-03-01T00:00Z"
    serie = {"inizio": inizio, "p": P.pressione(54), "t": [None if math.isnan(v) else float(v) for v in t], "ur": [float(v) for v in ur]}
    gruppi = [{"da": "01/06", "a": "30/09"}, {"da": "01/11", "a": "31/03", "anni": 2}, {"oraDa": 8, "oraA": 18, "giorni": "feriali", "anni": 1},
              {"oraDa": 22, "oraA": 6, "da": "15/10", "a": "15/04", "anni": 5}, {"da": "29/02", "a": "01/03"}, {}]
    livelli = [{}, {"inverno": 99.6, "estate": 0.4}, {"inverno": 95, "estate": 5}]
    return {"stati": stati, "sequenze": sequenze, "serie": serie, "gruppi": gruppi, "livelli": livelli}


@pytest.fixture(scope="module")
def risultati(tmp_path_factory):
    casi = _casi()
    f = tmp_path_factory.mktemp("parita") / "casi.json"
    f.write_text(json.dumps(casi), encoding="utf-8")
    out = subprocess.run([NODE, str(QUI / "parita_node.js"), str(f)], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return casi, json.loads(out)


def test_stati(risultati):
    casi, js = risultati
    for (t, ur, p), r in zip(casi["stati"], js["stati"]):
        s = P.stato(t, {"ur": ur}, p)
        atteso = [s["x"], s["h"], s["v"], s["tdew"], s["twb"], s["ur"], s["rho"]]
        assert r == pytest.approx(atteso, rel=1e-10, abs=1e-8), (t, ur, p)


def test_sequenze(risultati):
    casi, js = risultati
    note = 0
    for o, r in zip(casi["sequenze"], js["sequenze"]):
        s = P.sequenza(o)
        assert r["mtot"] == pytest.approx(s["mtot"], rel=1e-12)
        assert r["immissione"] == pytest.approx([s["immissione"]["t"], s["immissione"]["x"]], rel=1e-10, abs=1e-12)
        for a, b in zip(r["righe"], s["righe"]):
            assert a[:6] == pytest.approx([b["t"], b["x"], b["Qt"], b["Ql"], b["Qs"], b["acqua"]], rel=1e-8, abs=1e-8), o
            assert a[6] == b["nota"], o
            note += b["nota"] not in ("", "OK")
        assert r["riepilogo"] == pytest.approx(s["riepilogo"], rel=1e-8, abs=1e-8)
        assert (r["verifiche"], r["raggiungibile"], r["esito"]) == (s["verifiche"], s["raggiungibile"], s["esito"])
        assert r["R"] == pytest.approx(s["R"], rel=1e-12)
    assert note > 300            # le prove passano davvero per gli avvisi


def test_vettori_e_progetto(risultati):
    casi, js = risultati
    S = casi["serie"]
    t = np.array([np.nan if v is None else v for v in S["t"]], dtype=np.float32)
    ur = np.array(S["ur"], dtype=np.float32)
    V = P.vettori(t.astype(float), ur.astype(float), S["p"])
    for k, tol in (("x", 1e-8), ("h", 2e-4), ("twb", 2e-3)):
        a = np.array([np.nan if v is None else v for v in js["vettori"][k]], dtype=float)
        assert np.array_equal(np.isnan(a), np.isnan(V[k]))
        assert np.nanmax(np.abs(a - V[k])) < tol, k
    for L, r in zip(casi["livelli"], js["progetto"]):
        c = P.condizioni_progetto(t, ur, S["p"], **L)
        assert r["ore"] == c["ore"] and r["livelli"] == pytest.approx(c["livelli"])
        for k in ("inverno", "estate", "entalpia", "umidita", "bulboUmido"):
            for q, v in c[k].items():
                assert r[k][q] == pytest.approx(v, rel=2e-4, abs=2e-3 if q in ("twb", "t", "ur", "h") else 1e-6), (L, k, q)


def test_ora_locale_e_gruppi(risultati):
    casi, js = risultati
    S = casi["serie"]
    n = len(S["t"])
    C = P.campi_orari(dt.datetime(2023, 3, 1, tzinfo=dt.timezone.utc), n)
    for k in ("anno", "mese", "giorno", "ora", "dow"):
        assert np.array_equal(np.array(js["campi"][k]), C[k]), k
    valide = np.array([v is not None for v in S["t"]])
    for g, r in zip(casi["gruppi"], js["gruppi"]):
        atteso = P.filtra_gruppo(C, g, valide=valide, indice_inizio_anni=r["inizio"])
        assert np.array_equal(np.array(r["indici"], dtype=np.uint32), atteso), g
    # «ultimi N anni» = N×12 mesi fino all'ultima ora
    assert js["gruppi"][2]["inizio"] == n - 8760 and js["gruppi"][3]["inizio"] == 0


def _locale_zoneinfo(inizio: dt.datetime, n: int) -> dict:
    """ora locale e giorno della settimana con zoneinfo (Europe/Rome), ora per ora (qualche secondo)."""
    from zoneinfo import ZoneInfo
    R = ZoneInfo("Europe/Rome")
    base = int(inizio.timestamp() // 3600)
    ora, dow = np.empty(n, dtype=np.int64), np.empty(n, dtype=np.int64)
    for i in range(n):
        d = dt.datetime.fromtimestamp((base + i) * 3600, R)
        ora[i], dow[i] = d.hour, d.weekday()
    return {"ora": ora, "dow": dow}


def test_regressione_1940_ora_legale_storica_e_giorno_della_settimana():
    """(14/11/2026, verifica indipendente) prima del 1970 il giorno della settimana di gruppi_ore.js era sbagliato (% di JS
    negativo) e prima del 1996 l'ora legale seguiva la regola europea attuale: ora JS = Python = zoneinfo, ora per ora."""
    inizio = dt.datetime(1939, 12, 31, 23, tzinfo=dt.timezone.utc)          # 01/01/1940 00:00 ora italiana
    n = int((dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc) - inizio).total_seconds() // 3600)
    py = P.campi_orari(inizio, n)
    zi = _locale_zoneinfo(inizio, n)
    assert np.array_equal(py["ora"], zi["ora"])
    assert np.array_equal(py["dow"], zi["dow"])
    assert (py["anno"][0], py["mese"][0], py["giorno"][0], py["ora"][0], py["dow"][0]) == (1940, 1, 1, 0, 0)   # lunedì
    gruppi = [{"oraDa": 8, "oraA": 18, "giorni": "feriali"}, {"da": "01/06", "a": "30/09", "oraDa": 22, "oraA": 6}]
    out = json.loads(subprocess.run([NODE, str(QUI / "campi_node.js"), "1939-12-31T23:00:00Z", str(n), json.dumps(gruppi)],
                                    capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    for k in ("ora", "dow", "giorno", "mese", "anno"):
        assert np.array_equal(np.array(out[k]), py[k]), k
    for g, nj in zip(gruppi, out["gruppi"]):
        assert nj == len(P.filtra_gruppo(py, g)), g
    # feriali dalle 8 alle 18 nel 1940–1969: circa 10/24 · 5/7 delle ore
    m = py["anno"] < 1970
    uff = P.filtra_gruppo(py, gruppi[0])
    frazione = np.isin(np.nonzero(m)[0], uff).mean()
    assert abs(frazione - 10 / 24 * 5 / 7) < 0.002


def test_finestra_ultimi_anni_come_il_server_anche_al_29_febbraio():
    """(14/11/2026) «ultimi N anni» = ultima ora + 1 h − N anni (pandas DateOffset, come inizio_finestra del server): con
    l'ultima ora il 29/02 il JS spostava al 01/03 (un giorno in meno)."""
    import pandas as pd
    casi, attesi = [], []
    ini = pd.Timestamp("2010-01-01T00:00Z")
    for fine in ("2028-02-29T10:00Z", "2028-02-29T23:00Z", "2026-11-09T05:00Z", "2024-03-01T00:00Z", "2027-02-28T22:00Z"):
        f = pd.Timestamp(fine)
        n = int((f - ini) / pd.Timedelta(hours=1)) + 1
        for anni in (1, 2, 5, 10):
            t = f + pd.Timedelta(hours=1) - pd.DateOffset(years=anni)
            casi.append([ini.strftime("%Y-%m-%dT%H:%M:%SZ"), n, anni])
            attesi.append(max(0, int((t - ini) / pd.Timedelta(hours=1))))
    out = json.loads(subprocess.run([NODE, str(QUI / "finestra_node.js"), json.dumps(casi)], capture_output=True, text=True,
                                    encoding="utf-8", check=True).stdout)
    assert out == attesi
