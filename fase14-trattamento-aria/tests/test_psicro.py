"""Psicrometria (aria/psicro.py) contro il riferimento indipendente di psychrolib 2.5 SI (tests/dati/reference_cases.json):
griglia di stati a 0, 500 e 1000 m e casi UTA a–e, con le convenzioni del foglio psicro_UTA.xlsx (post-riscaldamento AUTO a
T_imm − ΔT del ventilatore, nel caso d riscaldatore fino a T_imm e poi vapore). Più condizioni di progetto e gruppi di ore."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pytest

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent))
from aria import psicro as P  # noqa: E402

RIF = json.loads((QUI / "dati" / "reference_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("chiave", sorted(RIF["states"]))
def test_griglia_stati(chiave):
    s = RIF["states"][chiave]
    st = P.stato(s["T_C"], {"ur": s["RH_pct"]}, s["p_Pa"])
    assert P.pressione(int(chiave.split("_")[0][1:])) == pytest.approx(s["p_Pa"], abs=0.05)
    assert st["psat"] == pytest.approx(s["psat_Pa"], rel=2e-6)
    assert st["xg"] == pytest.approx(s["x_gkg"], abs=1e-3)
    assert st["h"] == pytest.approx(s["h_kJkg"], abs=1e-3)
    assert st["v"] == pytest.approx(s["v_m3kg"], abs=1e-4)
    assert st["tdew"] == pytest.approx(s["Tdew_C"], abs=2e-3)
    assert st["twb"] == pytest.approx(s["Twb_C"], abs=2e-3)
    # le funzioni inverse ritrovano lo stesso stato
    # vicino a 0 °C il bulbo umido è quello della bisezione di psychrolib (tolleranza 0,001 K): x ritrovata entro ~1e-6
    assert P.stato(s["T_C"], {"twb": st["twb"]}, s["p_Pa"])["x"] == pytest.approx(st["x"], rel=1e-6, abs=1e-6)
    assert P.stato(s["T_C"], {"tdew": st["tdew"]}, s["p_Pa"])["x"] == pytest.approx(st["x"], rel=1e-6)
    assert P.stato_hx(st["h"], st["x"], s["p_Pa"])["t"] == pytest.approx(s["T_C"], abs=1e-9)
    y = P.mollier_y(st["t"], st["x"])
    assert y == pytest.approx((st["h"] - 2501 * st["x"]) / 1.006, abs=1e-9)
    assert P.t_da_mollier(y, st["x"]) == pytest.approx(st["t"], abs=1e-9)


def _stesso_stato(st, r, nome):
    assert st["t"] == pytest.approx(r["T_C"], abs=2e-3), nome
    assert st["xg"] == pytest.approx(r["x_gkg"], abs=2e-3), nome
    assert st["h"] == pytest.approx(r["h_kJkg"], abs=5e-3), nome
    assert st["ur"] == pytest.approx(r["RH_pct"], abs=0.01), nome


ESTATE = dict(p=101325.0, stagione="estate", esterno={"t": 32, "ur": 50}, ambiente={"t": 26, "ur": 50}, Qs=5000, Ql=1500)
INVERNO = dict(p=101325.0, stagione="inverno", esterno={"t": -5, "ur": 80}, ambiente={"t": 20, "ur": 50}, Qs=8000, Ql=500)


@pytest.mark.parametrize("V", [1000, 5000])
@pytest.mark.parametrize("caso,qe", [("a", 100), ("b", 70)])
def test_estate(caso, qe, V):
    r = RIF["ahu"][f"{caso}_{V}"]
    s = P.sequenza({**ESTATE, "V": V, "quotaEsterna": qe})       # sequenza predefinita del foglio (PRESET estate)
    assert s["mtot"] == pytest.approx(r["m_da_kgs"], rel=1e-4)
    assert s["immissione"]["t"] == pytest.approx(r["supply_T_imm_C"], abs=1e-3)
    assert s["immissione"]["xg"] == pytest.approx(r["supply_x_imm_gkg"], abs=1e-3)
    righe = s["righe"]
    if caso == "b":
        _stesso_stato(righe[0]["uscita"], r["states"]["MIX"], "MIX")
    _stesso_stato(righe[1]["uscita"], r["states"]["COIL_OUT"], "COIL_OUT")
    assert righe[1]["dettagli"]["tADP"] == pytest.approx(r["states"]["ADP"]["T_C"], abs=2e-3)
    W = r["powers"]
    assert s["riepilogo"]["frigoTotale"] == pytest.approx(W["cooling_total_kW"], rel=5e-4)
    assert s["riepilogo"]["frigoLatente"] == pytest.approx(W["cooling_latent_kW"], rel=5e-4)
    assert s["riepilogo"]["condensa"] == pytest.approx(W["condensate_kgh"], rel=5e-4)
    assert s["riepilogo"]["ventilatori"] == pytest.approx(W["fan_heat_kW"], rel=2e-3)
    var = r["variant_postheat_to_Timm_minus_fan"]
    assert righe[2]["uscita"]["t"] == pytest.approx(var["postheat_out_T_C"], abs=2e-3)
    assert s["riepilogo"]["postRiscaldamento"] == pytest.approx(var["postheat_kW"], abs=2e-3)
    assert s["uscita"]["t"] == pytest.approx(var["supply_T_C"], abs=2e-3)
    assert s["raggiungibile"] is r["postheat_feasible"]
    if not r["postheat_feasible"]:
        assert "PUNTO DI IMMISSIONE NON RAGGIUNGIBILE" in righe[2]["nota"] and s["raggiungibileTesto"] == "NO"


@pytest.mark.parametrize("V", [1000, 5000])
def test_inverno_adiabatico(V):
    r = RIF["ahu"][f"c_{V}"]
    s = P.sequenza({**INVERNO, "V": V, "righe": [("Recuperatore di calore", 0.6), ("Preriscaldamento", "AUTO", None, 90),
                                                ("Umidificazione adiabatica", "AUTO"), ("Post-riscaldamento", "AUTO")]})
    for i, nome in enumerate(("HR_OUT", "PREHEAT_OUT", "HUM_OUT", "SUPPLY")):
        _stesso_stato(s["righe"][i]["uscita"], r["states"][nome], nome)
    W, R = r["powers"], s["riepilogo"]
    assert R["recuperata"] == pytest.approx(W["heat_recovery_kW"], rel=5e-4)
    assert R["preriscaldamento"] == pytest.approx(W["preheat_kW"], rel=5e-4)
    assert R["postRiscaldamento"] == pytest.approx(W["postheat_kW"], rel=5e-4)
    assert R["umidificazione"] == pytest.approx(W["humidifier_water_kgh"], rel=5e-4)
    assert s["raggiungibile"] and s["verifiche"] != "OK" if V == 1000 else s["verifiche"] == "OK"   # 1000 m³/h: ΔT > 15 K


@pytest.mark.parametrize("V", [1000, 5000])
def test_inverno_vapore(V):
    r = RIF["ahu"][f"d_{V}"]
    s = P.sequenza({**INVERNO, "V": V, "righe": [("Recuperatore di calore", 0.6), ("Post-riscaldamento", "AUTO"),
                                                ("Umidificazione a vapore", "AUTO")]})
    var = r["variant_heat_to_Timm_then_steam"]
    assert s["riepilogo"]["postRiscaldamento"] == pytest.approx(var["heater_kW"], rel=5e-4)
    assert s["uscita"]["t"] == pytest.approx(var["supply_T_C"], abs=2e-3)
    assert s["riepilogo"]["umidificazione"] == pytest.approx(r["powers"]["steam_kgh"], rel=5e-4)
    assert s["righe"][2]["Qt"] == pytest.approx(r["powers"]["steam_enthalpy_kW"], rel=5e-4)
    assert s["uscita"]["xg"] == pytest.approx(r["supply_x_imm_gkg"], abs=1e-3)


def test_trasformazioni_singole_e():
    r = RIF["ahu"]["e1_1000"]
    A = P.stato(20, {"ur": 50})
    m = 1000 / 3600 / A["v"]
    assert m == pytest.approx(r["m_da_kgs"], rel=1e-4)
    o = P.trasforma("Riscaldamento sensibile", A, [22], {"p": 101325.0, "ambiente": A, "mdot": m})
    _stesso_stato(o["uscita"], r["states"]["OUT"], "e1")
    assert o["Qt"] == pytest.approx(r["powers"]["heating_kW"], rel=5e-4)
    r = RIF["ahu"]["e2_1000"]
    B = P.stato(28, {"xg": 14.11})
    m = 1000 / 3600 / B["v"]
    o = P.trasforma("Umidificazione adiabatica", B, [None, 100], {"p": 101325.0, "ambiente": B, "mdot": m})
    _stesso_stato(o["uscita"], r["states"]["OUT"], "e2")
    assert o["acqua"] == pytest.approx(r["powers"]["water_kgh"], rel=5e-4)
    assert "h costante = 64,19 kJ/kg." in o["nota"]
    assert B["twb"] == pytest.approx(r["Twb_in_C_thermodynamic"], abs=2e-3)


def test_inverse_e_adp():
    p = P.pressione(300)
    for h in (0, 25, 60, 110):
        t = P.t_sat_da_h(h, p)
        assert P.entalpia(t, P.x_sat(t, p)) == pytest.approx(h, abs=1e-6)
    A = P.stato(30, {"ur": 50}, p)
    adp = P.adp_da_bf(A["x"], 0.009, 0.1, p)
    out_t = adp["t"] + 0.1 * (A["t"] - adp["t"])
    r = P.adp_retta(A["t"], A["x"], out_t, 0.009, p)
    assert r["t"] == pytest.approx(adp["t"], abs=1e-6) and r["x"] == pytest.approx(adp["x"], rel=1e-6)


def test_avvisi_come_il_foglio():
    A = P.stato(26, {"ur": 50})
    ctx = {"p": 101325.0, "ambiente": A, "immissione": {"t": 15, "x": 0.009}, "mdot": 1.0, "mtot": 1.0, "fgen": 0}
    n = P.trasforma("Raffreddamento sensibile", A, [10], ctx)["nota"]
    assert n.startswith("OLTRE SATURAZIONE") and "T uscita sotto la T di rugiada dell'aria in ingresso" in n
    assert P.trasforma("Riscaldamento sensibile", A, [], ctx)["nota"] == "Parametro mancante: la riga non modifica lo stato. "
    assert P.trasforma("Pompa di calore", A, [], ctx)["nota"] == "Tipo non riconosciuto. "
    o = P.trasforma("Raffreddamento con deumidificazione", A, [None, 0.1, -2], ctx)
    assert "ADP < 0 °C: rischio di brina." in o["nota"] and o["avvisi"][0].startswith("ADP = -2,0 °C")
    assert P.trasforma("Umidificazione a vapore", A, [None, 60], ctx)["acqua"] > 0
    assert P.fisso(-0.004, 2) == "0,00" and P.fisso(2.345, 2) == "2,35" and P.fisso(1234.5, 0) == "1235"


def _serie_sintetica(anni=3, seme=7):
    r = np.random.default_rng(seme)
    n = int(anni * 8766)
    i = np.arange(n)
    t = 13 + 10.5 * -np.cos(2 * np.pi * (i / 24 - 15) / 365.25) + 4 * np.cos(2 * np.pi * (i % 24 - 14) / 24) + r.normal(0, 2, n)
    ur = np.clip(72 - 18 * np.cos(2 * np.pi * (i % 24 - 14) / 24) + r.normal(0, 8, n), 15, 100)
    t, ur = np.round(t * 10) / 10, np.round(ur)
    t[r.integers(0, n, 30)] = np.nan
    return t.astype(np.float32), ur.astype(np.float32)


def test_condizioni_progetto():
    t, ur = _serie_sintetica()
    c = P.condizioni_progetto(t, ur, 101325.0)                   # predefiniti 99 % / 1 %
    assert c["livelli"] == {"inverno": 99.0, "estate": 1.0}
    ok = np.isfinite(t)
    assert c["ore"] == ok.sum()
    assert c["inverno"]["t"] == pytest.approx(np.quantile(t[ok].astype(float), 0.01), abs=0.05)
    assert c["estate"]["t"] == pytest.approx(np.quantile(t[ok].astype(float), 0.99), abs=0.05)
    assert 0 < c["inverno"]["ur"] <= 100 and c["estate"]["twb"] < c["estate"]["t"]
    c4 = P.condizioni_progetto(t, ur, 101325.0, inverno=99.6, estate="0,4")
    assert c4["livelli"] == {"inverno": 99.6, "estate": 0.4}
    assert c4["inverno"]["t"] < c["inverno"]["t"] and c4["estate"]["t"] > c["estate"]["t"]
    assert c4["entalpia"]["h"] > c["entalpia"]["h"] and c4["umidita"]["x"] > c["umidita"]["x"]
    assert P.livelli(120, -1) == {"inverno": 99.0, "estate": 1.0}
    assert P.SCELTE_LIVELLO == {"inverno": (99.6, 99.0, 95.0), "estate": (0.4, 1.0, 5.0)}


def test_ora_legale_e_gruppi():
    inizio = dt.datetime(2025, 12, 31, 22, tzinfo=dt.timezone.utc)
    C = P.campi_orari(inizio, 2 * 8760)
    assert (C["anno"][0], C["mese"][0], C["giorno"][0], C["ora"][0]) == (2025, 12, 31, 23)
    k = int((dt.datetime(2026, 3, 29, 1, tzinfo=dt.timezone.utc) - inizio).total_seconds() // 3600)
    assert C["ora"][k - 1] == 1 and C["ora"][k] == 3                       # 29/3/2026: dalle 02 alle 03
    k = int((dt.datetime(2026, 10, 25, 0, tzinfo=dt.timezone.utc) - inizio).total_seconds() // 3600)
    assert list(C["ora"][k:k + 3]) == [2, 2, 3]                            # 25/10/2026: le 02 due volte
    assert C["dow"][k] == 6                                                # domenica
    inv = P.filtra_gruppo(C, {"da": "01/11", "a": "31/03"})
    assert set(np.unique(C["mese"][inv])) == {1, 2, 3, 11, 12}
    uff = P.filtra_gruppo(C, {"oraDa": 8, "oraA": 18, "giorni": "feriali"})
    assert set(np.unique(C["ora"][uff])) == set(range(8, 18)) and C["dow"][uff].max() <= 4
    notte = P.filtra_gruppo(C, {"oraDa": 22, "oraA": 6})
    assert set(np.unique(C["ora"][notte])) == {22, 23, 0, 1, 2, 3, 4, 5}


# (14/11/2026, verifica indipendente) bulbo umido vicino a 0 °C: l'equazione ha un salto tra il ramo «acqua» e quello
# «ghiaccio»; prima si prendeva la radice «acqua» anche dove psychrolib dà quella «ghiaccio» (fino a 0,68 K di scarto).
# Valori attesi da psychrolib 2.5.0 SI, GetTWetBulbFromRelHum(T, UR/100, p(z)).
TWB_PSYCHROLIB = [(5.95, 27.8, 12, -0.09163), (-0.25, 97.5, 0, -0.390397), (0.45, 97.5, 0, 0.307073),
                  (1.15, 79.0, 0, -0.187265), (1.5, 82.7, 0, 0.452418), (2.2, 67.9, 0, 0.167634),
                  (2.9, 56.8, 0, -0.153748), (3.6, 49.4, 0, -0.121423), (4.3, 45.7, 0, 0.44253),
                  (5.35, 34.6, 0, 0.424901), (6.75, 19.8, 0, -0.255307)]


@pytest.mark.parametrize("t,ur,z,atteso", TWB_PSYCHROLIB)
def test_bulbo_umido_vicino_a_zero_come_psychrolib(t, ur, z, atteso):
    p = P.pressione(z)
    assert P.stato(t, ur, p)["twb"] == pytest.approx(atteso, abs=1e-3)
    V = P.vettori([t], [ur], p)
    assert V["twb"][0] == pytest.approx(atteso, abs=1e-3)
