"""Psicrometria dell'aria umida: gemello Python di fase5-sito/sito/psicro.js (14/11/2026).

Stesse formule del foglio psicro_UTA.xlsx (cartella foglio/) e di psychrolib 2.5 SI (ASHRAE Fundamentals 2017):

    p(z) = 101325·(1 − 2,25577e-5·z)^5,2559                  pressione dalla quota [Pa]
    psat(t) Hyland–Wexler, sul ghiaccio per t ≤ 0,01 °C        [Pa]
    x = 0,621945·pw/(p − pw)                                   [kg/kg aria secca]
    h = 1,006·t + x·(2501 + 1,86·t)                            [kJ/kg aria secca]
    v = 0,287042·(t + 273,15)·(1 + 1,607858·x)/(p/1000)        [m³/kg aria secca]
    Y di Mollier = (h − 2501·x)/1,006 = T·(1 + 1,86·x/1,006)

Unità: t in °C, x in kg/kg (xg in g/kg dove scritto), UR in %, potenze in kW, acqua in kg/h, carichi della sequenza in W.
Le funzioni hanno gli stessi nomi di psicro.js; i risultati coincidono (test di parità tests/test_parita_js.py).
Le serie orarie lunghe si trattano con NumPy (vettori, condizioni_progetto, campi_orari, filtra_gruppo).
"""
from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass

import numpy as np

EPS, RA, K0, R0, CPA, CPV = 0.621945, 0.287042, 273.15, 2501.0, 1.006, 1.86
H_VAPORE, BF_PRED, UR_PRERISC = 2676.0, 0.1, 90.0
fin = math.isfinite


# ---------------------------------------------------------------------------------------------- proprietà di base
def pressione(z: float) -> float:
    q = max(-500.0, min(8000.0, float(z or 0)))
    return 101325.0 * (1 - 2.25577e-5 * q) ** 5.2559


def ln_psat(t: float) -> float:
    T = t + K0
    if t <= 0.01:
        return (-5674.5359 / T + 6.3925247 - 0.009677843 * T + 0.00000062215701 * T * T
                + 0.0000000020747825 * T ** 3 - 9.484024e-13 * T ** 4 + 4.1635019 * math.log(T))
    return (-5800.2206 / T + 1.3914993 - 0.048640239 * T + 0.000041764768 * T * T
            - 0.000000014452093 * T ** 3 + 6.5459673 * math.log(T))


def d_ln_psat(t: float) -> float:
    T = t + K0
    if t <= 0.01:
        return (5674.5359 / T ** 2 - 0.009677843 + 2 * 0.00000062215701 * T + 3 * 0.0000000020747825 * T * T
                - 4 * 9.484024e-13 * T ** 3 + 4.1635019 / T)
    return 5800.2206 / T ** 2 - 0.048640239 + 2 * 0.000041764768 * T - 3 * 0.000000014452093 * T * T + 6.5459673 / T


def psat(t: float) -> float:
    return math.exp(ln_psat(t))


def x_da_pw(pw, p):
    return EPS * pw / (p - pw)


def pw_da_x(x, p):
    return max(p * x / (EPS + x), 0.001)


def x_sat(t, p):
    ps = psat(t)
    return EPS * ps / (p - ps)


def x_da_ur(t, ur, p):
    pw = ur / 100 * psat(t)
    return EPS * pw / (p - pw)


def entalpia(t, x):
    return CPA * t + x * (R0 + CPV * t)


def volume(t, x, p):
    return RA * (t + K0) * (1 + 1.607858 * x) / (p / 1000)


def t_da_hx(h, x):
    return (h - R0 * x) / (CPA + CPV * x)


def x_da_ht(h, t):
    return (h - CPA * t) / (R0 + CPV * t)


def cp_umido(x):
    return CPA + CPV * x


def mollier_y(t, x):
    """Coordinata di Mollier (ordinata in °C, a x = 0 coincide con T); x in kg/kg."""
    return t * (1 + CPV * x / CPA)


def t_da_mollier(y, x):
    return y / (1 + CPV * x / CPA)


def t_rugiada_pw(pw: float) -> float:
    if not pw > 0:
        return math.nan
    g = math.log(pw / 611.2)
    t = 243.12 * g / (17.62 - g) if pw >= 611.2 else 272.62 * g / (22.46 - g)
    lp = math.log(pw)
    for _ in range(50):
        d = (ln_psat(t) - lp) / d_ln_psat(t)
        t -= d
        if abs(d) < 1e-9:
            break
    return t


def t_rugiada(x, p):
    return t_rugiada_pw(pw_da_x(x, p))


def x_bulbo_umido(t, tw, p):
    ps = psat(tw)
    ws = EPS * ps / (p - ps)
    if tw >= 0:
        return ((2501 - 2.326 * tw) * ws - 1.006 * (t - tw)) / (2501 + 1.86 * t - 4.186 * tw)
    return ((2830 - 0.24 * tw) * ws - 1.006 * (t - tw)) / (2830 + 1.86 * t - 2.1 * tw)


ZONA_SALTO = 3.0                                 # K attorno a 0 °C in cui si usa sempre la bisezione di psychrolib


def t_bulbo_umido_psychrolib(t, x, p):
    """Come psychrolib GetTWetBulbFromHumRatio: bisezione tra T di rugiada e T (tolleranza 0,001 K), equazione «acqua» se
    il punto medio è ≥ 0 °C, «ghiaccio» sotto. Vicino a 0 °C sceglie la stessa radice di psychrolib."""
    w = max(x, 1e-7)
    inf, sup = t_rugiada(w, p), t
    tw = (inf + sup) / 2
    for _ in range(100):
        if not sup - inf > 0.001:
            break
        if x_bulbo_umido(t, tw, p) > w:
            sup = tw
        else:
            inf = tw
        tw = (sup + inf) / 2
    return tw


def t_bulbo_umido(t, x, p):
    """Newton dalla T (veloce, radice unica lontano da 0 °C); entro ZONA_SALTO da 0 °C, o se Newton non converge, la
    bisezione di psychrolib (stessa scelta tra la radice «acqua» e quella «ghiaccio»). Stesso risultato di psicro.js."""
    if not (fin(t) and fin(x)):
        return math.nan
    tw = t
    for _ in range(40):
        a = x_bulbo_umido(t, tw, p) - x
        b = x_bulbo_umido(t, tw + 0.001, p) - x
        if b == a:
            break
        d = a * 0.001 / (b - a)
        tw -= d
        if not (-100 < tw <= t + 1e-9):           # fuori campo (aria molto secca): bisezione
            break
        if abs(d) < 1e-7:
            return t_bulbo_umido_psychrolib(t, x, p) if abs(tw) < ZONA_SALTO else tw
    return t_bulbo_umido_psychrolib(t, x, p)


def t_isoentalpica_ur(h, phi, p, t0=None):
    def g(t):
        ps = psat(t)
        return x_da_ht(h, t) - EPS * phi * ps / (p - phi * ps)
    t = t0 if t0 is not None and fin(t0) else h / 2.5
    for _ in range(60):
        a, b = g(t), g(t + 0.001)
        if b == a:
            break
        d = a * 0.001 / (b - a)
        t -= d
        if abs(d) < 1e-9:
            break
    return t


def t_sat_da_h(h, p):
    return t_isoentalpica_ur(h, 1.0, p)


def adp_retta(t_in, x_in, t_out, x_out, p):
    """ADP: punto sulla saturazione della retta T–x per ingresso e uscita, oltre l'uscita (None se non c'è)."""
    dt_, dx = t_out - t_in, x_out - x_in

    def f(s):
        return x_in + s * dx - x_sat(t_in + s * dt_, p)
    if f(1) >= 0:                  # l'uscita è già satura o oltre
        return None
    lo, hi, k = 1.0, 1.5, 0
    while f(hi) < 0 and k < 60:
        hi = 1 + (hi - 1) * 2
        k += 1
    if f(hi) < 0:
        return None
    for _ in range(100):
        m = (lo + hi) / 2
        if f(m) < 0:
            lo = m
        else:
            hi = m
    s = (lo + hi) / 2
    return {"t": t_in + s * dt_, "x": x_in + s * dx}


def adp_da_bf(x_in, x_out, bf, p):
    x = (x_out - bf * x_in) / (1 - bf)
    return {"x": x, "t": t_rugiada(x, p)}


# ---------------------------------------------------------------------------------------------- stato dell'aria
def stato_tx(t, x, p=101325.0) -> dict:
    p = p or 101325.0
    t = max(-100.0, min(200.0, t))
    pw, ps = pw_da_x(x, p), psat(t)
    h, v = entalpia(t, x), volume(t, x, p)
    return {"t": t, "x": x, "xg": x * 1000, "ur": pw / ps * 100, "phi": pw / ps, "pw": pw, "psat": ps, "h": h, "v": v,
            "rho": (1 + x) / v, "tdew": t_rugiada_pw(pw), "twb": t_bulbo_umido(t, x, p), "p": p}


def stato(t, dato, p=101325.0) -> dict:
    """dato = UR % (numero) oppure {'ur'} | {'x'} (kg/kg) | {'xg'} (g/kg) | {'twb'} | {'tdew'} | {'h'}."""
    p = p or 101325.0
    if isinstance(dato, (int, float)):
        x = x_da_ur(t, dato, p)
    elif dato.get("ur") is not None:
        x = x_da_ur(t, dato["ur"], p)
    elif dato.get("x") is not None:
        x = dato["x"]
    elif dato.get("xg") is not None:
        x = dato["xg"] / 1000
    elif dato.get("twb") is not None:
        x = x_bulbo_umido(t, dato["twb"], p)
    elif dato.get("tdew") is not None:
        x = x_sat(dato["tdew"], p)
    elif dato.get("h") is not None:
        x = x_da_ht(dato["h"], t)
    else:
        raise ValueError("stato: serve UR, x, bulbo umido, rugiada o entalpia")
    return stato_tx(t, x, p)


def stato_hx(h, x, p=101325.0):
    return stato_tx(t_da_hx(h, x), x, p)


def fisso(n, d):
    """Come FIXED(n; d; VERO) del foglio, con la virgola decimale."""
    if not fin(n):
        return "—"
    s = f"{math.floor(abs(n) * 10 ** d + 0.5 + 1e-9) / 10 ** d:.{d}f}"
    return ("-" if n < 0 and float(s) != 0 else "") + s.replace(".", ",")


# ---------------------------------------------------------------------------------------------- trasformazioni
TIPI = ["Nessuna", "Miscela con ricircolo", "Recuperatore di calore", "Riscaldamento sensibile", "Raffreddamento sensibile",
        "Raffreddamento con deumidificazione", "Umidificazione adiabatica", "Umidificazione a vapore", "Preriscaldamento",
        "Post-riscaldamento", "Ventilatore"]
RIF_PORTATA = ["Aria esterna (condizioni di progetto)", "Aria ambiente", "Aria standard 20 °C, 101325 Pa (ρ = 1,204 kg/m³)",
               "Densità fissa ρ = 1,2 kg/m³"]
PRESET = {
    "estate": [("Miscela con ricircolo", "AUTO", None, None), ("Raffreddamento con deumidificazione", "AUTO", 0.1, None),
               ("Post-riscaldamento", "AUTO", None, None), ("Ventilatore", 0.7, None, None), ("Nessuna", None, None, None),
               ("Nessuna", None, None, None)],
    "inverno": [("Recuperatore di calore", 0.6, None, None), ("Miscela con ricircolo", "AUTO", None, None),
                ("Preriscaldamento", "AUTO", None, 90), ("Umidificazione adiabatica", "AUTO", None, None),
                ("Post-riscaldamento", "AUTO", None, None), ("Ventilatore", 0.7, None, None)],
}
DATI_PREDEFINITI = {"estate": {"esterno": {"t": 32, "ur": 50}, "ambiente": {"t": 26, "ur": 50}, "Qs": 5000, "Ql": 1500},
                    "inverno": {"esterno": {"t": -5, "ur": 80}, "ambiente": {"t": 20, "ur": 40}, "Qs": 8000, "Ql": 500},
                    "V": 5000, "quotaEsterna": 100, "quota": 120}
NUMERO = re.compile(r"^[-+]?(\d+([.,]\d*)?|[.,]\d+)([eE][-+]?\d+)?$")


def codice_tipo(tipo) -> int:
    if isinstance(tipo, (int, float)) and not isinstance(tipo, bool):
        return int(round(tipo)) if 1 <= tipo <= 11 else 1
    s = str(tipo or "").strip()
    return TIPI.index(s) + 1 if s in TIPI else 1


@dataclass
class Par:
    ha: bool
    v: float
    auto: bool


def leggi_parametro(v) -> Par:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return Par(True, float(v), False) if fin(v) else Par(False, 0.0, False)
    if isinstance(v, str):
        s = v.strip()
        if s.upper() == "AUTO":
            return Par(False, 0.0, True)
        if NUMERO.match(s):
            return Par(True, float(s.replace(",", ".")), False)
    return Par(False, 0.0, False)


def trasforma(tipo, ingresso: dict, par, ctx: dict) -> dict:
    """Una riga della sequenza, come trasforma() di psicro.js (stessi nomi dei campi)."""
    code = codice_tipo(tipo)
    P1, P2, P3 = (leggi_parametro(par[i] if par and i < len(par) else None) for i in range(3))
    p = ctx.get("p") or 101325.0
    A, imm = ctx["ambiente"], ctx.get("immissione") or {"t": math.nan, "x": math.nan}
    tin, xin = ingresso["t"], ingresso["x"]
    hin = entalpia(tin, xin)
    tdin = ingresso["tdew"] if fin(ingresso.get("tdew", math.nan)) else t_rugiada(xin, p)
    mdot, cpin = ctx["mdot"], cp_umido(xin)
    t, x, d, inf, fan = tin, xin, {}, False, 0.0
    if code == 2:
        f = max(0.0, min(1.0, P1.v if P1.ha else (ctx.get("fgen") or 0)))
        x = (1 - f) * xin + f * A["x"]
        h = (1 - f) * hin + f * A["h"]
        t = (h - R0 * x) / (CPA + CPV * x)
        d["frazione"] = f
    elif code == 3:
        if P1.ha:
            t = tin + P1.v * (A["t"] - tin)
            x = xin + (P2.v if P2.ha else 0) * (A["x"] - xin)
    elif code == 4:
        t = P1.v if P1.ha else (tin + P2.v / (mdot * cpin) if P2.ha else tin)
    elif code == 5:
        t = P1.v if P1.ha else (tin - P2.v / (mdot * cpin) if P2.ha else tin)
    elif code == 6:
        bf = P2.v if P2.ha else BF_PRED
        xt = P1.v / 1000 if P1.ha else (imm["x"] if P1.auto else -1)
        if P3.ha:
            xadp, tadp = x_sat(P3.v, p), P3.v
        else:
            xadp = (xt - bf * xin) / (1 - bf) if xt > 0 and bf < 1 else -1
            tadp = t_rugiada(xadp if xadp > 0 else EPS * 611.2 / (p - 611.2), p)
        ok = xadp > 0 and 0 <= bf < 1
        secca = P3.ha and xadp >= xin
        nessuna = (not P3.ha) and xt >= xin
        t = tin if (not ok or nessuna) else tadp + bf * (tin - tadp)
        x = xin if (not ok or nessuna or secca) else xadp + bf * (xin - xadp)
        d = {"bf": bf, "xObiettivo": xt, "xADP": xadp, "tADP": tadp, "ok": ok, "secca": secca, "nessuna": nessuna}
    elif code == 7:
        modo = 1 if (P1.ha or P1.auto) else (2 if P2.ha else (3 if P3.ha else 0))
        phit = min(1.0, max(0.01, P2.v / 100)) if modo == 2 else 1.0
        ts = t_isoentalpica_ur(hin, phit, p, tin)
        xs = x_da_ht(hin, ts)
        xt = P1.v / 1000 if P1.ha else (imm["x"] if P1.auto else 0)
        te = tin - max(0.0, min(1.0, P3.v)) * (tin - ts) if modo == 3 else tin
        x = [xin, max(xin, min(xt, xs)), max(xin, xs), max(xin, x_da_ht(hin, te))][modo]
        t = tin if x <= xin + 1e-9 else t_da_hx(hin, x)
        d = {"modo": modo, "xObiettivo": xt, "xSaturazione": xs, "tSaturazione": ts}
    elif code == 8:
        hv = P3.v if P3.ha else H_VAPORE
        modo = 1 if (P1.ha or P1.auto) else (2 if P2.ha else 0)
        xt = P1.v / 1000 if P1.ha else (imm["x"] if P1.auto else 0)
        phit = min(1.0, max(0.01, P2.v / 100))
        xu = xin
        if modo == 2:
            tk = tin
            for _ in range(60):
                ps = psat(tk)
                xk = EPS * phit * ps / (p - phit * ps)
                tn = (hin + (xk - xin) * hv - R0 * xk) / (CPA + CPV * xk)
                fine = abs(tn - tk) < 1e-10
                tk = tn
                if fine:
                    break
            ps = psat(tk)
            xu = EPS * phit * ps / (p - phit * ps)
        x = max(xin, xt) if modo == 1 else (max(xin, xu) if modo == 2 else xin)
        t = (hin + (x - xin) * hv - R0 * x) / (CPA + CPV * x)
        d = {"modo": modo, "hVapore": hv, "xObiettivo": xt}
    elif code == 9:
        phi = min(1.0, max(0.05, P3.v / 100)) if P3.ha else UR_PRERISC / 100
        pw = max(1.0, p * imm["x"] / (EPS + imm["x"]) / phi)
        tb = t_rugiada_pw(pw)
        h9 = entalpia(tb, imm["x"])
        ta = t_da_hx(h9, xin)
        t = P1.v if P1.ha else (max(tin, ta) if P1.auto else (tin + P2.v / (mdot * cpin) if P2.ha else tin))
        d = {"urObiettivo": phi * 100, "hObiettivo": h9, "tAuto": ta}
    elif code == 10:
        ta = imm["t"] - (ctx.get("ventilatoriValle") or 0)
        t = P1.v if P1.ha else (max(tin, ta) if P1.auto else (tin + P2.v / (mdot * cpin) if P2.ha else tin))
        inf = P1.auto and tin > ta + 0.05
        d = {"tAuto": ta}
    elif code == 11:
        fan = P1.v if P1.ha else (P2.v / (mdot * cpin) if P2.ha else 0.0)
        t = tin + fan
    usc = stato_tx(t, x, p)
    mix = code == 2
    Qt = 0.0 if mix else mdot * (usc["h"] - hin)
    Ql = 0.0 if mix else mdot * (usc["x"] - xin) * R0
    Qs = Qt - Ql
    acqua = 0.0 if mix else mdot * (usc["x"] - xin) * 3600
    tstr = tipo if isinstance(tipo, str) else ""
    sconosciuto = isinstance(tipo, str) and tstr.strip() != "" and tstr.strip() not in TIPI
    modo7 = 1 if (P1.ha or P1.auto) else (2 if P2.ha else (3 if P3.ha else 0))
    modo8 = 1 if (P1.ha or P1.auto) else (2 if P2.ha else 0)
    manca = ((code == 3 and not P1.ha) or (code in (4, 5, 11) and not (P1.ha or P2.ha))
             or (code in (9, 10) and not (P1.ha or P1.auto or P2.ha)) or (code == 6 and not (P1.ha or P1.auto or P3.ha))
             or (code == 7 and modo7 == 0) or (code == 8 and modo8 == 0))
    wmiss = ("Tipo non riconosciuto. " if sconosciuto else "") + ("Parametro mancante: la riga non modifica lo stato. " if manca else "")
    tout, xout = usc["t"], usc["x"]
    wtype = ""
    if code == 2:
        wtype = ("Frazione di ricircolo 0: nessuna miscela (100 % aria esterna). " if d["frazione"] == 0 else
                 f"Ricircolo {fisso(d['frazione'] * 100, 0)} % in massa; portata a monte {fisso(ctx['mtot'] * (1 - d['frazione']), 3)} kg/s. ")
    elif code == 3:
        wtype = f"Potenza recuperata {fisso(abs(Qt), 2)} kW. " if P1.ha else ""
    elif code == 4:
        wtype = "Attenzione: T uscita < T ingresso (non è un riscaldamento). " if tout < tin - 0.001 else ""
    elif code == 5:
        wtype = (("Attenzione: T uscita > T ingresso. " if tout > tin + 0.001 else "")
                 + ("T uscita sotto la T di rugiada dell'aria in ingresso: si forma condensa, usare «Raffreddamento con deumidificazione». "
                    if tout < tdin - 0.01 else ""))
    elif code == 6:
        if not d["ok"]:
            wtype = "Dati batteria non validi (x ADP ≤ 0 oppure BF ≥ 1). "
        elif d["nessuna"]:
            wtype = "x obiettivo ≥ x ingresso: nessuna deumidificazione necessaria (riga senza effetto). "
        else:
            wtype = (f"ADP = {fisso(d['tADP'], 1)} °C; SHR = {fisso(Qs / Qt if Qt != 0 else 0, 2)}; BF = {fisso(d['bf'], 2)}. "
                     + ("ADP < 0 °C: rischio di brina. " if d["tADP"] < 0 else "")
                     + ("Batteria secca (ADP sopra la rugiada). " if d["secca"] else ""))
    elif code == 7:
        wtype = (("x obiettivo oltre la saturazione: limitato a UR 100 %. " if d["modo"] == 1 and d["xObiettivo"] > d["xSaturazione"] + 1e-7 else "")
                 + ("Nessuna umidificazione (obiettivo ≤ ingresso). " if d["modo"] > 0 and xout <= xin + 1e-9 else "")
                 + (f"h costante = {fisso(hin, 2)} kJ/kg. " if d["modo"] > 0 else ""))
    elif code == 8:
        wtype = (("Nessuna umidificazione (obiettivo ≤ ingresso). " if d["modo"] > 0 and xout <= xin + 1e-9 else "")
                 + (f"Vapore {fisso(acqua, 2)} kg/h. " if d["modo"] > 0 else ""))
    elif code == 9:
        if P1.auto and d["tAuto"] <= tin:
            wtype = "Preriscaldamento non necessario (entalpia già sufficiente). "
        elif P1.auto:
            wtype = f"AUTO: fino a h = {fisso(d['hObiettivo'], 2)} kJ/kg (isoentalpica per x_imm a UR {fisso(d['urObiettivo'], 0)} %). "
    elif code == 10:
        if inf:
            wtype = (f"PUNTO DI IMMISSIONE NON RAGGIUNGIBILE: T ingresso ({fisso(tin, 1)} °C) > T richiesta ({fisso(d['tAuto'], 1)} °C). "
                     "Aumentare la portata o ridurre BF. ")
        elif P1.auto:
            wtype = f"AUTO: T = T_imm − ΔT ventilatori a valle = {fisso(d['tAuto'], 1)} °C. "
    wgen = "OLTRE SATURAZIONE (UR > 100 %): stato non fisico, nebbia/condensa. " if usc["phi"] > 1.0001 else ""
    nota = wmiss if code == 1 else (wmiss + wgen + wtype if (wmiss + wtype + wgen) else "OK")
    avvisi = [s.strip() for s in re.split(r"(?<=\.) (?=[A-ZÈÀ«])", nota) if s.strip()] if nota and nota != "OK" else []
    return {"codice": code, "tipo": TIPI[code - 1], "ingresso": ingresso, "t": usc["t"], "x": usc["x"], "uscita": usc,
            "mdot": mdot, "Qt": Qt, "Ql": Ql, "Qs": Qs, "acqua": acqua, "ventilatoreDT": fan, "nonRaggiungibile": bool(inf),
            "dettagli": d, "nota": nota, "avvisi": avvisi}


def portata_massica(V, riferimento, esterno, ambiente):
    i = int(round(riferimento)) if isinstance(riferimento, (int, float)) else (
        RIF_PORTATA.index(riferimento) if riferimento in RIF_PORTATA else 0)
    if not 0 <= i <= 3:
        i = 0
    xref = [esterno["x"], ambiente["x"], 0.0, esterno["x"]][i]
    vref = [esterno["v"], ambiente["v"], RA * 293.15 / 101.325, (1 + esterno["x"]) / 1.2][i]
    return {"mtot": V / 3600 / vref, "vref": vref, "rho": (1 + xref) / vref, "xref": xref, "riferimento": i}


def punto_immissione(ambiente, apporto_sensibile, apporto_latente, m, p=None):
    """Apporti in W, positivi se entrano nell'ambiente (in inverno le dispersioni sono un apporto sensibile negativo)."""
    cp = cp_umido(ambiente["x"])
    t = ambiente["t"] - apporto_sensibile / 1000 / (m * cp)
    x = ambiente["x"] - apporto_latente / 1000 / (m * R0)
    return stato_tx(t, x, p or ambiente.get("p") or 101325.0)


def sequenza(opz: dict | None = None) -> dict:
    """Una stagione del foglio UTA: stessi ingressi e uscite di sequenza() in psicro.js."""
    opz = opz or {}
    inverno = opz.get("stagione") == "inverno"
    pred = DATI_PREDEFINITI["inverno" if inverno else "estate"]
    p = max(30000.0, min(120000.0, opz["p"])) if opz.get("p") is not None else pressione(opz.get("quota", DATI_PREDEFINITI["quota"]))
    V = opz.get("V", DATI_PREDEFINITI["V"])
    qe = opz.get("quotaEsterna", DATI_PREDEFINITI["quotaEsterna"])
    e, a = opz.get("esterno") or pred["esterno"], opz.get("ambiente") or pred["ambiente"]
    Qs, Ql = opz.get("Qs", pred["Qs"]), opz.get("Ql", pred["Ql"])
    E, A = stato(e["t"], {"ur": e["ur"]}, p), stato(a["t"], {"ur": a["ur"]}, p)
    port = portata_massica(V, opz.get("riferimento", 0), E, A)
    mtot, cpA = port["mtot"], cp_umido(A["x"])
    I = stato_tx(A["t"] + Qs / 1000 / (mtot * cpA) if inverno else A["t"] - Qs / 1000 / (mtot * cpA),
                 A["x"] - Ql / 1000 / (mtot * R0), p)
    fgen = max(0.0, min(1.0, 1 - qe / 100))
    righe = []
    for r in opz.get("righe") or PRESET["inverno" if inverno else "estate"]:
        if isinstance(r, dict):
            righe.append({"tipo": r.get("tipo"), "par": [r.get("p1"), r.get("p2"), r.get("p3")]})
        else:
            r = list(r) + [None] * (4 - len(r))
            righe.append({"tipo": r[0], "par": r[1:4]})
    codici = [codice_tipo(r["tipo"]) for r in righe]
    mixidx = codici.index(2) if 2 in codici else -1
    fmix = 0.0
    if mixidx >= 0:
        pm = leggi_parametro(righe[mixidx]["par"][0])
        fmix = max(0.0, min(1.0, pm.v if pm.ha else fgen))
    base = {"p": p, "ambiente": A, "immissione": I, "mtot": mtot, "fgen": fgen}
    fans = [leggi_parametro(r["par"][0]).v if codici[i] == 11 and leggi_parametro(r["par"][0]).ha else 0.0 for i, r in enumerate(righe)]
    out = []
    for _ in range(8):
        out, cur = [], E
        for i, r in enumerate(righe):
            mdot = mtot * (1 - fmix) if (mixidx >= 0 and i < mixidx) else mtot
            o = trasforma(r["tipo"], cur, r["par"], {**base, "mdot": mdot, "ventilatoriValle": sum(fans[i + 1:])})
            o["n"] = i + 1
            out.append(o)
            cur = o["uscita"]
        nuovi = [o["ventilatoreDT"] for o in out]
        fermo = all(abs(v - fans[i]) < 1e-12 for i, v in enumerate(nuovi))
        fans = nuovi
        if fermo:
            break
    punti = [E] + [o["uscita"] for o in out]

    def somma(codes, k):
        return sum(o[k] for o in out if o["codice"] in codes)
    riepilogo = {"frigoTotale": -somma((5, 6), "Qt"), "frigoSensibile": -somma((5, 6), "Qs"), "frigoLatente": -somma((5, 6), "Ql"),
                 "preriscaldamento": somma((9,), "Qt"), "postRiscaldamento": somma((10, 4), "Qt"), "condensa": -somma((6,), "acqua"),
                 "umidificazione": somma((7, 8), "acqua"), "recuperata": abs(somma((3,), "Qt")), "ventilatori": somma((11,), "Qt")}
    if inverno:
        R = -Qs / (-Qs + Ql) if (-Qs + Ql) != 0 else 1.0
    else:
        R = Qs / (Qs + Ql) if (Qs + Ql) != 0 else 1.0
    dT = abs(A["t"] - I["t"])
    lim = 15 if inverno else 10
    verifiche = (("UR immissione > 100 %: punto impossibile, aumentare la portata. " if I["phi"] > 1 else "")
                 + (f"ΔT di immissione > {lim} K: rischio discomfort/stratificazione, aumentare la portata. " if dT > lim else "")
                 + ("Portata nulla. " if mtot <= 0 else "")
                 + ("Ricircolo previsto nei dati generali ma nessuna riga «Miscela» nella sequenza (calcolo a tutta aria esterna). "
                    if fgen > 0 and mixidx < 0 else "")
                 + ("x immissione ≤ 0: carico latente troppo alto. " if I["x"] <= 0 else ""))
    U = punti[-1]
    sc = {"t": U["t"] - I["t"], "ur": U["ur"] - I["ur"], "xg": U["xg"] - I["xg"], "h": U["h"] - I["h"]}
    inf = any(o["nonRaggiungibile"] for o in out)
    ragg = not (inf or abs(sc["t"]) > 0.3 or abs(sc["xg"]) > 0.1)
    if inf:
        esito = ("PUNTO DI IMMISSIONE NON RAGGIUNGIBILE: l'aria a monte del post-riscaldamento è già più calda della T di immissione "
                 "richiesta (post-riscaldamento = 0). Aumentare la portata o ridurre il fattore di bypass BF.")
    elif ragg:
        esito = "Lo stato in uscita dall'UTA coincide con il punto di immissione richiesto."
    else:
        esito = "L'uscita dell'UTA NON coincide con il punto di immissione: verificare tipi e parametri della sequenza (scostamenti sopra)."
    return {"stagione": "inverno" if inverno else "estate", "p": p, "V": V, "quotaEsterna": qe, **port,
            "mOA": mtot * (1 - fmix), "fgen": fgen, "fmix": fmix, "mixidx": mixidx + 1 if mixidx >= 0 else None, "cpA": cpA,
            "esterno": E, "ambiente": A, "immissione": I, "R": R, "dT": dT, "verifiche": verifiche or "OK", "punti": punti,
            "righe": out, "riepilogo": riepilogo, "uscita": U, "scostamento": sc, "raggiungibile": ragg,
            "raggiungibileTesto": "SÌ" if ragg else "NO", "esito": esito}


# ---------------------------------------------------------------------------------------------- serie orarie (NumPy)
def _ln_psat_v(t):
    T = t + K0
    ghiaccio = (-5674.5359 / T + 6.3925247 - 0.009677843 * T + 0.00000062215701 * T * T
                + 0.0000000020747825 * T ** 3 - 9.484024e-13 * T ** 4 + 4.1635019 * np.log(T))
    acqua = (-5800.2206 / T + 1.3914993 - 0.048640239 * T + 0.000041764768 * T * T
             - 0.000000014452093 * T ** 3 + 6.5459673 * np.log(T))
    return np.where(t <= 0.01, ghiaccio, acqua)


def _x_bu_v(t, tw, p):
    ps = np.exp(_ln_psat_v(tw))
    ws = EPS * ps / (p - ps)
    sopra = ((2501 - 2.326 * tw) * ws - 1.006 * (t - tw)) / (2501 + 1.86 * t - 4.186 * tw)
    sotto = ((2830 - 0.24 * tw) * ws - 1.006 * (t - tw)) / (2830 + 1.86 * t - 2.1 * tw)
    return np.where(tw >= 0, sopra, sotto)


def vettori(t, ur, p=101325.0) -> dict:
    """x (kg/kg), h, twb come array float64 (NaN dove manca T o UR); twb con Newton vettoriale (passo < 1e-7 K)."""
    t = np.asarray(t, dtype=float)
    ur = np.asarray(ur, dtype=float)
    ok = np.isfinite(t) & np.isfinite(ur) & (ur >= 0)
    tt = np.where(ok, t, 20.0)
    pw = np.minimum(np.where(ok, ur, 50.0), 100) / 100 * np.exp(_ln_psat_v(tt))
    x = EPS * pw / (p - pw)
    h = CPA * tt + x * (R0 + CPV * tt)
    # Newton vettoriale come t_bulbo_umido (partenza da T); le ore che non convergono o escono dal campo (aria molto
    # secca) si rifanno una per una con t_bulbo_umido, così il risultato è lo stesso del browser
    tw = tt.copy()
    attive = np.ones_like(tt, dtype=bool)
    fuori = np.zeros_like(tt, dtype=bool)
    for _ in range(40):
        a = _x_bu_v(tt, tw, p) - x
        b = _x_bu_v(tt, tw + 0.001, p) - x
        d = np.where(b != a, a * 0.001 / np.where(b != a, b - a, 1), 0)
        tw = np.where(attive, tw - d, tw)
        fuori |= attive & ~((tw > -100) & (tw <= tt + 1e-9))
        attive &= (np.abs(d) >= 1e-7) & ~fuori
        if not attive.any():
            break
    for i in np.nonzero((fuori | attive | (np.abs(tw) < ZONA_SALTO)) & ok)[0]:
        tw[i] = t_bulbo_umido_psychrolib(float(tt[i]), float(x[i]), p)
    nan = np.full_like(tt, np.nan)
    return {"x": np.where(ok, x, nan), "h": np.where(ok, h, nan), "twb": np.where(ok, tw, nan)}


def quantile(ordinati, q):
    n = len(ordinati)
    if not n:
        return math.nan
    pos = q * (n - 1)
    i = int(math.floor(pos))
    f = pos - i
    return float(ordinati[i] * (1 - f) + ordinati[i + 1] * f) if i + 1 < n else float(ordinati[i])


def _coincidente(valori, abbinati, meta):
    def calcola(v):
        d = meta
        for _ in range(12):
            m = (valori >= v - d) & (valori <= v + d) & np.isfinite(abbinati)
            n = int(m.sum())
            if n >= 10 or n == len(valori):
                return (float(abbinati[m].mean()) if n else math.nan), n
            d *= 2
        return math.nan, 0
    return calcola


LIVELLI_PREDEFINITI = {"inverno": 99.0, "estate": 1.0}
SCELTE_LIVELLO = {"inverno": (99.6, 99.0, 95.0), "estate": (0.4, 1.0, 5.0)}


def livelli(inverno=None, estate=None) -> dict:
    """Livelli di progetto in %: inverno = % delle ore con T superiore (99 → quantile 1 %), estate = % delle ore che lo
    superano (1 → quantile 99 %). Valori fuori campo → predefiniti 99 / 1 (decisione del 14/11/2026)."""
    def lv(v, pred, lo, hi):
        try:
            n = float(str(v).replace(",", ".")) if v is not None else math.nan
        except ValueError:
            n = math.nan
        return n if fin(n) and lo < n < hi else pred
    return {"inverno": lv(inverno, LIVELLI_PREDEFINITI["inverno"], 50, 100), "estate": lv(estate, LIVELLI_PREDEFINITI["estate"], 0, 50)}


def condizioni_progetto(t, ur, p=101325.0, indici=None, inverno=None, estate=None) -> dict:
    """Stesso metodo di condizioniProgetto() in psicro.js (percentili delle ore valide della serie, non valori di norma),
    livelli predefiniti 99 % / 1 %. I quantili si calcolano sui valori in float32, come nel browser."""
    L = livelli(inverno, estate)
    qi, qe = 1 - L["inverno"] / 100, 1 - L["estate"] / 100
    t = np.asarray(t, dtype=np.float32).astype(float)
    ur = np.asarray(ur, dtype=np.float32).astype(float)
    V = vettori(t, ur, p)
    x, h, tw = (np.asarray(V[k], dtype=np.float32).astype(float) for k in ("x", "h", "twb"))
    sel = np.arange(len(t)) if indici is None else np.asarray(indici)
    sel = sel[np.isfinite(x[sel])]
    n = len(sel)
    if n < 24:
        return {"ore": n, "livelli": L, "avviso": "Troppe poche ore valide per le condizioni di progetto."}
    tS, urS, xS, hS, wS = t[sel], ur[sel], x[sel], h[sel], tw[sel]

    def voce(valori, q, abbinati, meta):
        v = quantile(np.sort(valori.astype(np.float32)), q)
        m, k = _coincidente(valori, abbinati, meta)(v)
        return v, m, k
    w, s_, hh, xx, bb = (voce(tS, qi, urS, 0.5), voce(tS, qe, wS, 0.5), voce(hS, qe, tS, 1), voce(xS, qe, tS, 0.00025),
                         voce(wS, qe, tS, 0.5))
    return {
        "ore": n, "livelli": L,
        "inverno": {"t": w[0], "ur": w[1], "ore": w[2], "livello": L["inverno"]},
        "estate": {"t": s_[0], "twb": s_[1], "ore": s_[2], "livello": L["estate"]},
        "entalpia": {"h": hh[0], "t": hh[1], "ore": hh[2], "livello": L["estate"]},
        "umidita": {"x": xx[0], "xg": xx[0] * 1000, "t": xx[1], "ore": xx[2], "livello": L["estate"]},
        "bulboUmido": {"twb": bb[0], "t": bb[1], "ore": bb[2], "livello": L["estate"]},
    }


# ---------------------------------------------------------------------------------------------- gruppi di ore
def _ultima_domenica(anno, mese):
    g = dt.date(anno, mese + 1, 1) - dt.timedelta(days=1) if mese < 12 else dt.date(anno, 12, 31)
    return g - dt.timedelta(days=(g.weekday() + 1) % 7)


# ora legale in Italia prima del 1996 (tzdata, Europe/Rome): coppie [inizio, fine) in ore UTC dal 1970-01-01; stessa
# tabella di LEGALE_STORICA in gruppi_ore.js
LEGALE_STORICA = (-259009, -238127, -234599, -230063, -225695, -221687, -216959, -212977, -208583, -203711, -199849, -194977, -191447, -186239, -31681, -28658, -22777, -19921, -14041, -11185, -5137, -2281, 3599, 6455, 12167, 15191, 21071, 24095, 29975, 32831, 38543, 41567, 47447, 50303, 56183, 59039, 64751, 67775, 73655, 76679, 82391, 85415, 89953, 94153, 98521, 102889, 107257, 111625, 115993, 120361, 124729, 129265, 133633, 138001, 142369, 146737, 151105, 155473, 159841, 164209, 168577, 172945, 177313, 181849, 186217, 190585, 194953, 199321, 203689, 208057, 212425, 216793, 221161, 225529)
FINE_STORICA = 1996


def campi_orari(inizio_utc: dt.datetime, n: int) -> dict:
    """Ora locale Europe/Rome per n ore consecutive dall'inizio (UTC): dal 1996 regola europea (ora legale dall'ultima
    domenica di marzo alle 01 UTC all'ultima domenica di ottobre alle 01 UTC), prima le date storiche italiane di tzdata
    (LEGALE_STORICA); anno, mese, giorno, ora, giorno della settimana (0 = lunedì), mmgg = mese·100 + giorno. Stesso
    risultato di campiOrari() in gruppi_ore.js."""
    base = int(inizio_utc.replace(tzinfo=dt.timezone.utc).timestamp() // 3600) if inizio_utc.tzinfo is None else \
        int(inizio_utc.timestamp() // 3600)
    ore = base + np.arange(n, dtype=np.int64)
    anni = sorted({(base + k) // 8766 + 1970 for k in (0, n - 1)})
    off = np.ones(n, dtype=np.int64)
    for j in range(0, len(LEGALE_STORICA), 2):
        off[(ore >= LEGALE_STORICA[j]) & (ore < LEGALE_STORICA[j + 1])] = 2
    for a in range(max(anni[0] - 1, FINE_STORICA), max(anni[-1] + 2, FINE_STORICA)):
        da = int(dt.datetime.combine(_ultima_domenica(a, 3), dt.time(1), dt.timezone.utc).timestamp() // 3600)
        a_ = int(dt.datetime.combine(_ultima_domenica(a, 10), dt.time(1), dt.timezone.utc).timestamp() // 3600)
        off[(ore >= da) & (ore < a_)] = 2
    loc = ore + off
    giorni = loc // 24
    d = giorni.astype("datetime64[D]")
    y = d.astype("datetime64[Y]").astype(int) + 1970
    m = (d.astype("datetime64[M]").astype(int) % 12) + 1
    g = (d - d.astype("datetime64[M]")).astype(int) + 1
    return {"anno": y, "mese": m, "giorno": g, "ora": (loc % 24), "dow": (giorni + 3) % 7, "mmgg": m * 100 + g}


def filtra_gruppo(campi: dict, gruppo: dict, valide=None, n_ore_ultimo=None, indice_inizio_anni=0) -> np.ndarray:
    """Indici delle ore del gruppo: date da/a (gg/mm, anche a cavallo d'anno), ora da/a (0–24, anche a cavallo della
    mezzanotte; ora h compresa se da ≤ h < a), giorni 'tutti' o 'feriali', ore dall'indice indice_inizio_anni in poi."""
    def mmgg(s):
        g, m = (int(v) for v in s.split("/"))
        return m * 100 + g
    da, a = mmgg(gruppo.get("da", "01/01")), mmgg(gruppo.get("a", "31/12"))
    k = campi["mmgg"]
    ok_d = (k >= da) & (k <= a) if da <= a else (k >= da) | (k <= a)
    oda, oa = int(gruppo.get("oraDa", 0)), int(gruppo.get("oraA", 24))
    h = campi["ora"]
    if oda == oa or (oda == 0 and oa == 24):
        ok_h = np.ones_like(h, dtype=bool)
    elif oda < oa:
        ok_h = (h >= oda) & (h < oa)
    else:
        ok_h = (h >= oda) | (h < oa)
    ok_g = campi["dow"] < 5 if gruppo.get("giorni") == "feriali" else np.ones_like(h, dtype=bool)
    m = ok_d & ok_h & ok_g
    m[:indice_inizio_anni] = False
    if valide is not None:
        m &= valide
    return np.nonzero(m)[0].astype(np.uint32)
