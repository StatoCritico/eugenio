import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import indicatori as ind  # noqa: E402


def test_zone_dpr():
    assert ind.zona_da_gg(600) == "A"
    assert ind.zona_da_gg(600.4) == "A"
    assert ind.zona_da_gg(601) == "B"
    assert ind.zona_da_gg(2100) == "D"
    assert ind.zona_da_gg(3001) == "F"
    assert ind.zona_da_gg(float("nan")) is None


def test_periodi():
    lung = ind.lunghezza_periodi()
    # A 1/12-15/3 = 31+31+28+15 ; E 15/10-15/4 = 17+30+31+31+28+31+15 ; F = 365
    assert list(lung) == [105, 121, 137, 166, 183, 365]


def test_zona_coerente():
    # regola del 27/10/2026: D ed E entrambe coerenti (2050 sul periodo D, 2250 sul periodo E)
    g = np.array([1500, 1600, 1800, 2050, 2250, 2400])
    assert ind.zona_coerente(g, "D") == "D"          # vince la zona del DPR se è coerente
    assert ind.zona_coerente(g, "E") == "E"
    assert ind.zona_coerente(g) == "E"               # senza DPR: margine D = 50 GG, E = 150 GG
    assert ind.zona_coerente(g, "C") == "E"          # zona DPR non coerente: come senza DPR
    assert ind.zona_coerente(np.array([1500, 1600, 1800, 2150, 2350, 2600])) == "E"
    assert ind.zona_coerente(np.array([1500, 1600, 1800, 2080, 2120, 2400])) == "D"   # D 20, E 19
    assert ind.margine_fascia("F", 3050) == 50 and ind.margine_fascia("A", 550) == 50


def test_quantile_da_estremi_uguale_a_numpy():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 5, 3653)
    for q in (0.01, 0.99):
        basso = q < 0.5
        estremi = np.sort(x)[:120] if basso else np.sort(x)[-120:]
        assert abs(ind.quantile_da_estremi(estremi, len(x), q, basso) - np.quantile(x, q)) < 1e-9


def test_correzione_quota():
    # cella a 1000 m, comune a 500 m: il comune è 3,25 °C più caldo
    assert abs(ind.correzione_quota(1000, 500) - 3.25) < 1e-9


def test_gg_come_legge10():
    d = pd.date_range("2001-07-01", "2002-06-30")
    t = np.asarray(10 + 10 * np.cos(2 * np.pi * (d.dayofyear.to_numpy() - 200) / 365))
    mk = ind.maschere_periodi(d.month.to_numpy(), d.day.to_numpy())
    gg = np.clip(20 - t, 0, None)
    sys.path.insert(0, "/home/claude/storici/fase3-storico")
    try:
        from meteo_storico import legge10
    except ImportError:
        return
    g = pd.DataFrame({"data": d, "t_media": np.asarray(t)})
    for k, z in enumerate(ind.NOMI_ZONE):
        assert abs(legge10.gradi_giorno(g, z).iloc[0] - gg[mk[k]].sum()) < 1e-6
