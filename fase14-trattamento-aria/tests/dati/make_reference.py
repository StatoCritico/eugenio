#!/usr/bin/env python3
"""Generate independent psychrometric / AHU reference cases using psychrolib (SI,
ASHRAE Handbook Fundamentals 2017). Output: reference_cases.json + reference_cases.md

All assumptions are listed in META["assumptions"] and in the markdown file.
"""
import json, math, os
import psychrolib as pl

pl.SetUnitSystem(pl.SI)

R4 = lambda v, n=4: None if v is None else round(float(v), n)

# ---------------------------------------------------------------- constants
CP_DA = 1.006       # kJ/kg K
CP_V = 1.86         # kJ/kg K
R0 = 2501.0         # kJ/kg latent heat at 0 degC
H_STEAM = 2676.0    # kJ/kg enthalpy of saturated steam ~100 degC
P0 = 101325.0


def p_alt(z):
    return 101325.0 * (1 - 2.25577e-5 * z) ** 5.2559


def psat_water_HW(t):
    """Hyland-Wexler saturation over liquid water (also extrapolated below 0 degC)."""
    T = t + 273.15
    return math.exp(-5.8002206e3 / T + 1.3914993 - 4.8640239e-2 * T + 4.1764768e-5 * T**2
                    - 1.4452093e-8 * T**3 + 6.5459673 * math.log(T))


def state_TW(t, W, p=P0):
    """Full state from dry bulb t (degC) and humidity ratio W (kg/kg)."""
    rh = pl.GetRelHumFromHumRatio(t, W, p)
    pv = pl.GetVapPresFromHumRatio(W, p)
    return {
        "T_C": R4(t, 3),
        "x_gkg": R4(W * 1000, 4),
        "h_kJkg": R4(pl.GetMoistAirEnthalpy(t, W) / 1000, 4),
        "RH_pct": R4(rh * 100, 3),
        "v_m3kg": R4(pl.GetMoistAirVolume(t, W, p), 5),
        "Tdew_C": R4(pl.GetTDewPointFromVapPres(t, pv), 3) if W > 1e-9 else None,
        "Twb_C": R4(pl.GetTWetBulbFromHumRatio(t, W, p), 3) if rh <= 1.0 + 1e-9 else None,
    }


def W_from_TRH(t, rh, p=P0):
    return pl.GetHumRatioFromRelHum(t, rh, p)


def T_from_hW(h_kJ, W):
    return pl.GetTDryBulbFromEnthalpyAndHumRatio(h_kJ * 1000, W)


def h_of(t, W):
    return pl.GetMoistAirEnthalpy(t, W) / 1000


def T_sat_from_W(W, p=P0):
    """Saturation temperature (dew point) for humidity ratio W."""
    return pl.GetTDewPointFromHumRatio(30.0, W, p)


def T_sat_from_h(h_kJ, p=P0):
    """Temperature on saturation curve with enthalpy h (bisection)."""
    lo, hi = -40.0, 80.0
    for _ in range(200):
        mid = (lo + hi) / 2
        hs = h_of(mid, pl.GetSatHumRatio(mid, p))
        if hs > h_kJ:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def supply_point(m, room_T, room_W, Qs_gain_kW, Ql_gain_kW):
    """Supply point from room loads (gains positive; a heat loss is a negative gain).
    T_imm = T_amb - Qs/(m*cp_moist), cp_moist = 1.006 + 1.86*x_amb
    x_imm = x_amb - Ql/(m*2501)"""
    cpm = CP_DA + CP_V * room_W
    T = room_T - Qs_gain_kW / (m * cpm)
    W = room_W - Ql_gain_kW / (m * R0)
    return T, W, cpm


def kw(v):
    return R4(v, 4)


# ---------------------------------------------------------------- grid
def build_grid():
    temps = [-10, -5, 0, 5, 10, 15, 20, 26, 32, 35, 40]
    rhs = [30, 50, 80, 100]
    alts = [0, 500, 1000]
    out = {}
    for z in alts:
        p = p_alt(z)
        for t in temps:
            for rh in rhs:
                W = W_from_TRH(t, rh / 100, p)
                pv = pl.GetVapPresFromHumRatio(W, p)
                key = f"z{z}_t{t}_rh{rh}"
                # liquid-water-referenced variant (relevant only for t < 0)
                psw = psat_water_HW(t)
                Ww = 0.621945 * rh / 100 * psw / (p - rh / 100 * psw)
                out[key] = {
                    "z_m": z, "p_Pa": R4(p, 2), "T_C": t, "RH_pct": rh,
                    "psat_Pa": R4(pl.GetSatVapPres(t), 3),
                    "pv_Pa": R4(pv, 3),
                    "x_gkg": R4(W * 1000, 4),
                    "h_kJkg": R4(h_of(t, W), 4),
                    "v_m3kg": R4(pl.GetMoistAirVolume(t, W, p), 5),
                    "Tdew_C": R4(pl.GetTDewPointFromVapPres(t, pv), 3),
                    "Twb_C": R4(pl.GetTWetBulbFromRelHum(t, rh / 100, p), 3),
                    "psat_water_Pa": R4(psw, 3),
                    "x_water_gkg": R4(Ww * 1000, 4),
                }
    return out


# ---------------------------------------------------------------- AHU cases
def summer_case(V, recirc_frac=0.0, BF=0.1, fan_dT=0.7):
    p = P0
    T_oa, RH_oa, T_r, RH_r = 32.0, 0.50, 26.0, 0.50
    Qs, Ql = 5.0, 1.5
    W_oa = W_from_TRH(T_oa, RH_oa, p)
    W_r = W_from_TRH(T_r, RH_r, p)
    v_oa = pl.GetMoistAirVolume(T_oa, W_oa, p)
    m = V / v_oa / 3600.0  # total dry-air mass flow through the coil, kg/s
    T_imm, W_imm, cpm = supply_point(m, T_r, W_r, Qs, Ql)
    st = {"OA": state_TW(T_oa, W_oa), "ROOM": state_TW(T_r, W_r)}
    res = {"inputs": {"V_m3h": V, "V_refers_to": "outdoor air state (v_OA)",
                      "T_oa_C": T_oa, "RH_oa_pct": 50, "T_room_C": T_r, "RH_room_pct": 50,
                      "Qs_kW": Qs, "Ql_kW": Ql, "BF": BF, "fan_dT_K": fan_dT,
                      "recirc_mass_frac": recirc_frac, "p_Pa": p}}
    # mixing
    if recirc_frac > 0:
        f = recirc_frac
        h_mix = (1 - f) * h_of(T_oa, W_oa) + f * h_of(T_r, W_r)
        W_mix = (1 - f) * W_oa + f * W_r
        T_mix = T_from_hW(h_mix, W_mix)
        st["MIX"] = state_TW(T_mix, W_mix)
        T_in, W_in = T_mix, W_mix
        res["m_oa_kgs"] = R4(m * (1 - f), 5)
        res["m_rec_kgs"] = R4(m * f, 5)
    else:
        T_in, W_in = T_oa, W_oa
    h_in = h_of(T_in, W_in)
    # coil: outlet x = x_imm ; straight line in (T,x) through ADP with BF
    W_adp = (W_imm - BF * W_in) / (1 - BF)
    T_adp = T_sat_from_W(W_adp, p)
    T_coil = T_adp + BF * (T_in - T_adp)
    W_coil = W_imm
    h_coil = h_of(T_coil, W_coil)
    st["ADP"] = state_TW(T_adp, W_adp)
    st["COIL_OUT"] = state_TW(T_coil, W_coil)
    # alternative: straight line in (h,x) -> T from h
    h_adp = h_of(T_adp, W_adp)
    h_coil_hx = h_adp + BF * (h_in - h_adp)
    T_coil_hx = T_from_hW(h_coil_hx, W_coil)
    # post-heating to T_imm, then fan +0.7 K (literal sequence of the spec)
    feasible = T_coil <= T_imm
    T_ph = max(T_coil, T_imm)
    st["POSTHEAT_OUT"] = state_TW(T_ph, W_imm)
    st["FAN_OUT_SUPPLY"] = state_TW(T_ph + fan_dT, W_imm)
    st["SUPPLY_TARGET"] = state_TW(T_imm, W_imm)
    Qc = m * (h_in - h_coil)
    Ql_c = m * (W_in - W_coil) * R0
    Qph = m * (h_of(T_ph, W_imm) - h_coil)
    Qfan = m * (h_of(T_ph + fan_dT, W_imm) - h_of(T_ph, W_imm))
    # variant: post-heat only to T_imm - fan_dT so that supply = T_imm
    T_ph2 = max(T_coil, T_imm - fan_dT)
    Qph2 = m * (h_of(T_ph2, W_imm) - h_coil)
    res.update({
        "m_da_kgs": R4(m, 5), "v_oa_m3kg": R4(v_oa, 5), "cp_moist_kJkgK": R4(cpm, 5),
        "supply_T_imm_C": R4(T_imm, 3), "supply_x_imm_gkg": R4(W_imm * 1000, 4),
        "coil_inlet": "MIX" if recirc_frac > 0 else "OA",
        "states": st,
        "powers": {
            "cooling_total_kW": kw(Qc),
            "cooling_latent_kW": kw(Ql_c),
            "cooling_sensible_kW": kw(Qc - Ql_c),
            "postheat_kW": kw(Qph),
            "fan_heat_kW": kw(Qfan),
            "condensate_kgh": R4(m * (W_in - W_coil) * 3600, 4),
        },
        "postheat_feasible": feasible,
        "variant_postheat_to_Timm_minus_fan": {
            "postheat_out_T_C": R4(T_ph2, 3), "postheat_kW": kw(Qph2),
            "supply_T_C": R4(T_ph2 + fan_dT, 3)},
        "variant_coil_line_in_h_x": {"COIL_OUT_T_C": R4(T_coil_hx, 3),
                                     "COIL_OUT_h_kJkg": R4(h_coil_hx, 4),
                                     "cooling_total_kW": kw(m * (h_in - h_coil_hx))},
    })
    if not feasible:
        res["note"] = ("T_imm is below the coil outlet temperature: with this airflow the "
                       "supply point cannot be reached with x_imm and BF=0.1 (post-heating=0; "
                       "the supply temperature is then the coil outlet + fan). A workbook "
                       "should flag this.")
    return res


def winter_case(V, steam=False, eps=0.6, hum_out_RH=0.90):
    p = P0
    T_oa, RH_oa, T_r, RH_r = -5.0, 0.80, 20.0, 0.50
    Qloss, Ql = 8.0, 0.5
    W_oa = W_from_TRH(T_oa, RH_oa, p)
    W_r = W_from_TRH(T_r, RH_r, p)
    v_oa = pl.GetMoistAirVolume(T_oa, W_oa, p)
    m = V / v_oa / 3600.0
    T_imm, W_imm, cpm = supply_point(m, T_r, W_r, -Qloss, Ql)
    st = {"OA": state_TW(T_oa, W_oa), "ROOM": state_TW(T_r, W_r)}
    # sensible heat recovery, balanced flows, constant x
    T_hr = T_oa + eps * (T_r - T_oa)
    st["HR_OUT"] = state_TW(T_hr, W_oa)
    h_hr = h_of(T_hr, W_oa)
    Q_hr = m * (h_hr - h_of(T_oa, W_oa))
    h_imm = h_of(T_imm, W_imm)
    dW = W_imm - W_oa
    res = {"inputs": {"V_m3h": V, "V_refers_to": "outdoor air state (v_OA)",
                      "T_oa_C": T_oa, "RH_oa_pct": 80, "T_room_C": T_r, "RH_room_pct": 50,
                      "Q_heat_loss_kW": Qloss, "Ql_gain_kW": Ql, "eps_HR": eps,
                      "humidifier": "steam" if steam else "adiabatic", "p_Pa": p},
           "m_da_kgs": R4(m, 5), "v_oa_m3kg": R4(v_oa, 5), "cp_moist_kJkgK": R4(cpm, 5),
           "supply_T_imm_C": R4(T_imm, 3), "supply_x_imm_gkg": R4(W_imm * 1000, 4)}
    if not steam:
        # pre-heat to the isenthalp through (x_imm, RH = hum_out_RH); adiabatic humidification
        # at constant h to x_imm; post-heat to T_imm.
        T_hum = pl.GetTDewPointFromHumRatio(40, W_imm, p)  # init
        # find T with RH(T, W_imm) = hum_out_RH
        lo, hi = -20.0, 60.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if pl.GetRelHumFromHumRatio(mid, W_imm, p) > hum_out_RH:
                lo = mid
            else:
                hi = mid
        T_hum = (lo + hi) / 2
        h_hum = h_of(T_hum, W_imm)
        T_pre = T_from_hW(h_hum, W_oa)
        st["PREHEAT_OUT"] = state_TW(T_pre, W_oa)
        st["HUM_OUT"] = state_TW(T_hum, W_imm)
        st["SUPPLY"] = state_TW(T_imm, W_imm)
        Qpre = m * (h_hum - h_hr)
        Qpost = m * (h_imm - h_hum)
        # variant with 100% saturation efficiency
        T_hum100 = T_sat_from_W(W_imm, p)
        h100 = h_of(T_hum100, W_imm)
        res.update({"states": st, "powers": {
            "heat_recovery_kW": kw(Q_hr), "preheat_kW": kw(Qpre), "postheat_kW": kw(Qpost),
            "total_heating_coils_kW": kw(Qpre + Qpost),
            "humidifier_water_kgh": R4(m * dW * 3600, 4),
            "humidifier_latent_kW_m_dx_2501": kw(m * dW * R0)},
            "humidifier_outlet_RH_assumed_pct": hum_out_RH * 100,
            "variant_humidify_to_saturation": {
                "PREHEAT_OUT_T_C": R4(T_from_hW(h100, W_oa), 3), "HUM_OUT_T_C": R4(T_hum100, 3),
                "preheat_kW": kw(m * (h100 - h_hr)), "postheat_kW": kw(m * (h_imm - h100))}})
    else:
        # heater then steam humidifier, outlet exactly at (T_imm, x_imm):
        # h_imm = h_heater_out + dW*2676
        h_heat = h_imm - dW * H_STEAM
        T_heat = T_from_hW(h_heat, W_oa)
        st["HEATER_OUT"] = state_TW(T_heat, W_oa)
        st["SUPPLY"] = state_TW(T_imm, W_imm)
        Qh = m * (h_heat - h_hr)
        Qsteam = m * dW * H_STEAM
        # what the T rise across the steam humidifier is
        res.update({"states": st, "powers": {
            "heat_recovery_kW": kw(Q_hr), "heater_kW": kw(Qh),
            "steam_enthalpy_kW": kw(Qsteam), "steam_kgh": R4(m * dW * 3600, 4),
            "total_air_enthalpy_rise_after_HR_kW": kw(m * (h_imm - h_hr))},
            "steam_dT_K": R4(T_imm - T_heat, 3),
            "variant_heat_to_Timm_then_steam": {
                "supply_T_C": R4(T_from_hW(h_of(T_imm, W_oa) + dW * H_STEAM, W_imm), 3),
                "heater_kW": kw(m * (h_of(T_imm, W_oa) - h_hr))},
            "steam_enthalpy_assumption": "h_steam = 2676 kJ/kg (saturated steam ~100 degC, ~1 bar)"})
    return res


def simple_heating(V=1000.0):
    p = P0
    T1, T2, RH1 = 20.0, 22.0, 0.50
    W = W_from_TRH(T1, RH1, p)
    v1 = pl.GetMoistAirVolume(T1, W, p)
    m = V / v1 / 3600
    Q = m * (h_of(T2, W) - h_of(T1, W))
    return {"inputs": {"V_m3h": V, "V_refers_to": "inlet state (20 degC, 50 %)",
                       "T_in_C": T1, "RH_in_pct": 50, "T_out_C": T2, "p_Pa": p},
            "m_da_kgs": R4(m, 5), "v_in_m3kg": R4(v1, 5),
            "states": {"IN": state_TW(T1, W), "OUT": state_TW(T2, W)},
            "powers": {"heating_kW": kw(Q),
                       "heating_kW_cp_moist": kw(m * (CP_DA + CP_V * W) * (T2 - T1)),
                       "heating_kW_rho1.2_cp1.006": kw(V * 1.2 * 1.006 * 2 / 3600)}}


def simple_adiabatic(V=1000.0):
    p = P0
    T1, W1 = 28.0, 14.11e-3
    h1 = h_of(T1, W1)
    T2 = T_sat_from_h(h1, p)
    W2 = pl.GetSatHumRatio(T2, p)
    v1 = pl.GetMoistAirVolume(T1, W1, p)
    m = V / v1 / 3600
    return {"inputs": {"V_m3h": V, "V_refers_to": "inlet state", "T_in_C": T1, "x_in_gkg": 14.11,
                       "p_Pa": p, "process": "constant h to RH=100 %"},
            "m_da_kgs": R4(m, 5),
            "states": {"IN": state_TW(T1, W1), "OUT": state_TW(T2, W2)},
            "Twb_in_C_thermodynamic": R4(pl.GetTWetBulbFromHumRatio(T1, W1, p), 3),
            "powers": {"water_kgh": R4(m * (W2 - W1) * 3600, 4)}}


def main():
    grid = build_grid()
    ahu = {}
    for V in (1000, 5000):
        ahu[f"a_{V}"] = summer_case(V)
        ahu[f"b_{V}"] = summer_case(V, recirc_frac=0.30)
        ahu[f"c_{V}"] = winter_case(V)
        ahu[f"d_{V}"] = winter_case(V, steam=True)
    ahu["e1_1000"] = simple_heating(1000)
    ahu["e2_1000"] = simple_adiabatic(1000)
    meta = {
        "reference": f"psychrolib {getattr(pl, '__version__', '')} SI (ASHRAE Handbook Fundamentals 2017, Hyland-Wexler)",
        "units": {"T": "degC", "x": "g/kg dry air", "h": "kJ/kg dry air", "v": "m3/kg dry air",
                  "RH": "%", "p/psat": "Pa", "powers": "kW", "water": "kg/h", "m": "kg/s dry air"},
        "assumptions": [
            "State properties (psat, x, h, v, Tdew, Twb, RH) from psychrolib SI. psychrolib uses saturation over ICE for t < 0.01 degC (psat, RH, Tdew/frost point, Twb). For t<0 the grid also gives psat_water_Pa / x_water_gkg (Hyland-Wexler liquid-water formula extrapolated), for workbooks that use saturation over water (e.g. Magnus).",
            "psychrolib enthalpy: h = 1.006 t + x (2501 + 1.86 t) kJ/kg_da; x = 0.621945 pv/(p-pv).",
            "Altitude pressure p = 101325 (1 - 2.25577e-5 z)^5.2559 (z in m). AHU cases at p = 101325 Pa.",
            "Volume flow V refers to the OUTDOOR air state (cases a-d): m_da = V / v_OA / 3600 kg/s, v_OA = moist-air specific volume per kg dry air at outdoor conditions. In case b V is the TOTAL coil flow (referred to v_OA) and recirculation is 30 % by dry-air mass. Cases e: V refers to the inlet state.",
            "Supply point from loads (gains positive): T_imm = T_room - Qs/(m cp_moist), cp_moist = 1.006 + 1.86 x_room [kJ/kg K, x in kg/kg]; x_imm = x_room - Ql/(m 2501). In winter the 8 kW heat loss is a negative sensible gain (T_imm = T_room + 8/(m cp_moist)) and the 0.5 kW latent is an internal latent GAIN (x_imm = x_room - 0.5/(m 2501)).",
            "Powers Q = m_da * delta h with h from psychrolib. Cooling coil: latent = m*dx*2501, sensible = total - latent. Condensate/water flow = m*dx*3600 kg/h.",
            "Cooling coil with bypass factor BF=0.1: outlet x fixed = x_imm; ADP on saturation on the straight line (in T-x coordinates) through coil inlet and outlet: x_ADP = (x_imm - BF x_in)/(1-BF), T_ADP = dew point of x_ADP, T_out = T_ADP + BF (T_in - T_ADP). Variant with the straight line in h-x coordinates given as variant_coil_line_in_h_x.",
            "Summer sequence (literal spec): coil -> post-heating to T_imm -> fan +0.7 K (supply = T_imm + 0.7). Variant 'post-heat to T_imm - 0.7' also given. If coil outlet T > T_imm (1000 m3/h summer) post-heating is 0 and the case is flagged infeasible.",
            "Mixing (case b): mass-weighted h and x of outdoor and room air, T from (h,x).",
            "Heat recovery (c,d): sensible only, balanced dry-air mass flows, exhaust at room conditions, T_out = T_oa + 0.6 (T_room - T_oa), x constant (no condensation considered).",
            "Case c: pre-heat to the isenthalp passing through (x_imm, RH=90 %), adiabatic humidification at constant h to x_imm (humidifier outlet RH 90 %), post-heat to T_imm. The pre/post split depends on that RH choice (variant to 100 % RH given), but the SUM pre+post = m (h_imm - h_HR) does not.",
            "Case d: heater then steam humidifier; steam enthalpy 2676 kJ/kg (saturated steam ~100 degC); outlet exactly (T_imm, x_imm): h_heater_out = h_imm - dx*2676. Variant 'heat to T_imm then steam' given.",
            "Case e1: inlet 20 degC / 50 % RH (RH not given in spec -> assumed 50 %).",
            "Case e2: adiabatic humidification at constant psychrolib enthalpy to RH = 100 % (not along constant Twb; thermodynamic Twb also reported).",
        ],
    }
    data = {"meta": meta, "states": grid, "ahu": ahu}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference_cases.json"), "w") as f:
        json.dump(data, f, indent=1)
    write_md(data)


def fmt(v, n=2):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v:.{n}f}"
    return str(v)


def write_md(d):
    L = ["# Reference psychrometric / AHU cases (psychrolib SI, ASHRAE 2017)", "",
         "Generated by `make_reference.py`. Machine-readable: `reference_cases.json`.", "",
         "## Assumptions", ""]
    L += [f"- {a}" for a in d["meta"]["assumptions"]]
    L += ["", "## AHU cases (p = 101325 Pa)", ""]
    for k, c in d["ahu"].items():
        L += [f"### {k}", "", "Inputs: " + ", ".join(f"{a}={b}" for a, b in c["inputs"].items()), ""]
        sc = {kk: vv for kk, vv in c.items() if kk not in ("inputs", "states", "powers")}
        for kk, vv in sc.items():
            L.append(f"- {kk}: {json.dumps(vv)}")
        L += ["", "| state | T °C | x g/kg | h kJ/kg | RH % | v m³/kg | Tdew °C | Twb °C |",
              "|---|---|---|---|---|---|---|---|"]
        for s, v in c["states"].items():
            L.append(f"| {s} | {fmt(v['T_C'])} | {fmt(v['x_gkg'],3)} | {fmt(v['h_kJkg'])} | "
                     f"{fmt(v['RH_pct'],1)} | {fmt(v['v_m3kg'],4)} | {fmt(v['Tdew_C'])} | {fmt(v['Twb_C'])} |")
        L += ["", "| quantity | value |", "|---|---|"]
        for q, v in c["powers"].items():
            L.append(f"| {q} | {fmt(v,3)} |")
        L.append("")
    L += ["## State grid", "",
          "psat over ice for t<0 (psychrolib); `psat_w`/`x_w` = over liquid water.", ""]
    for z in (0, 500, 1000):
        sub = {k: v for k, v in d["states"].items() if v["z_m"] == z}
        p = next(iter(sub.values()))["p_Pa"]
        L += [f"### z = {z} m, p = {p:.1f} Pa", "",
              "| t °C | RH % | psat Pa | x g/kg | h kJ/kg | v m³/kg | Tdew °C | Twb °C | psat_w Pa | x_w g/kg |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for v in sub.values():
            L.append(f"| {v['T_C']} | {v['RH_pct']} | {fmt(v['psat_Pa'],1)} | {fmt(v['x_gkg'],3)} | "
                     f"{fmt(v['h_kJkg'])} | {fmt(v['v_m3kg'],4)} | {fmt(v['Tdew_C'])} | {fmt(v['Twb_C'])} | "
                     f"{fmt(v['psat_water_Pa'],1)} | {fmt(v['x_water_gkg'],3)} |")
        L.append("")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference_cases.md"), "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
