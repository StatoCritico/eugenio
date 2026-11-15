"""Free cooling e recupero di calore da una serie oraria: gemello Python della parte di calcolo di
fase5-sito/sito/aria_freecooling.js (pagina «Trattamento aria › Free cooling e recupero», 14/11/2026).

È una STIMA DEL POTENZIALE con un modello semplice e dichiarato, non una simulazione dell'edificio. Per ogni ora valida
(T e UR presenti) della serie del comune:

Modo dell'ora
    raffrescamento se T_e > T_bilancio (predefinita 12 °C: sopra l'edificio chiede freddo, sotto chiede caldo).

Portata
    ṁ = V/(3600·v_rif) [kg/s di aria secca] con v_rif come portataMassica di psicro.js: 0 aria esterna dell'ora,
    1 aria ambiente (estate o inverno secondo il modo), 2 aria standard 20 °C/101325 Pa, 3 densità fissa 1,2 kg/m³.
    Aria esterna minima ṁ_OA = f_min·ṁ.

Raffrescamento (ambiente/ripresa d'estate R, mandata a T_m)
    h_m(x) = h(T_m, min(x, x_sat(T_m)))                  la batteria porta l'aria a T_m (se serve, condensa fino a UR 100 %)
    senza economizzatore: ingresso batteria = miscela f_min aria esterna + (1 − f_min) ripresa
        Q_0 = ṁ·max(0, h_mix − h_m(x_mix))
    con economizzatore:
        «totale»   T_e ≤ T_m: si miscela aria esterna e ripresa fino a T_m, la batteria è spenta (Q = 0);
        «parziale» economizzatore attivo e T_e > T_m: 100 % aria esterna, Q = ṁ·max(0, h_e − h_m(x_e));
                   attivo = T_e < T_R (a temperatura) oppure h_e < h_R e x_e ≤ x_max (entalpico);
                   per l'entalpico le ore attive con T_e ≥ T_R sono il regime «entalpico» (aria calda ma secca);
        altrimenti aria esterna minima (Q = Q_0).
    energia evitata = Q_0 − Q (può essere negativa con l'economizzatore a temperatura e aria esterna umida).
    Recupero estivo (solo con l'economizzatore spento, quello scelto): uscita del recuperatore
        T = T_e + εs·(T_R − T_e), x = x_e + εl·(x_R − x_e); Q_rec = ṁ_OA·(h_e − h_uscita) se positivo.

Riscaldamento (ambiente/espulsione d'inverno R), solo se T_e < T_R
    stessa uscita del recuperatore (funzione «Recuperatore di calore» del foglio, portate bilanciate):
        Q_rec = ṁ_OA·max(0, h_uscita − h_e)
    espulsione in uscita: T_x = T_R − εs·(T_R − T_e), x_x = x_R − εl·(x_R − x_e)
    rischio brina: regola «rugiada» T_x < 0 °C e T_x < T_rugiada(x_x) (limite T_lim = 0 °C) oppure regola «soglia»
        T_e < T_soglia (predefinita −5 °C, scambiatori a piastre; T_lim = T_R − εs·(T_R − T_soglia));
    con lo sbrinamento a by-pass nelle ore a rischio: ε_eff = min(εs, (T_R − T_lim)/(T_R − T_e)) (≥ 0),
        εl_eff = εl·ε_eff/εs; energia persa = recupero pieno − recupero con by-pass.

Ventilatori
    nelle ore in cui il recuperatore recupera (Q_rec > 0) la perdita di carico ΔP (per lato, sui due flussi d'aria
    esterna ed espulsione) costa P_el = 2·(f_min·V/3600)·ΔP/η [W]; nelle altre ore il recuperatore è by-passato.

Regimi (codici): 0 nessuno, 1 free cooling totale, 2 parziale, 3 entalpico, 4 recupero estivo, 5 recupero invernale,
6 rischio brina; 255 ora senza dati.
"""
from __future__ import annotations

import math

import numpy as np

from . import psicro as P

REGIMI = ["nessuno", "totale", "parziale", "entalpico", "estivo", "invernale", "brina"]
SENZA_DATI = 255
PREDEFINITI = {
    "V": 10000.0, "riferimento": 0, "quotaMinima": 30.0,
    "estate": {"t": 26.0, "ur": 50.0}, "inverno": {"t": 20.0, "ur": 40.0},
    "tMandata": 16.0, "tBilancio": 12.0, "economizzatore": "entalpico", "xMax": None,
    "epsS": 0.7, "epsL": 0.0, "regolaBrina": "rugiada", "tSoglia": -5.0, "sbrinamento": True,
    "dP": 150.0, "etaV": 0.6,
}
X_MAX_RIF = (26.0, 60.0)          # x massima predefinita: x a 26 °C e UR 60 %


def _num(v, pred):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return pred
    return v if math.isfinite(v) else pred


def opzioni(o: dict | None, p: float) -> dict:
    """Opzioni complete e limitate ai campi sensati (stessa funzione in JS)."""
    o = dict(o or {})
    d = PREDEFINITI
    lim = lambda v, a, b: min(b, max(a, v))  # noqa: E731
    est, inv = o.get("estate") or {}, o.get("inverno") or {}
    r = {
        "V": lim(_num(o.get("V"), d["V"]), 0.0, 1e7),
        "riferimento": int(lim(round(_num(o.get("riferimento"), d["riferimento"])), 0, 3)),
        "quotaMinima": lim(_num(o.get("quotaMinima"), d["quotaMinima"]), 0.0, 100.0),
        "estate": {"t": lim(_num(est.get("t"), d["estate"]["t"]), 10.0, 40.0), "ur": lim(_num(est.get("ur"), d["estate"]["ur"]), 1.0, 100.0)},
        "inverno": {"t": lim(_num(inv.get("t"), d["inverno"]["t"]), 5.0, 35.0), "ur": lim(_num(inv.get("ur"), d["inverno"]["ur"]), 1.0, 100.0)},
        "tMandata": lim(_num(o.get("tMandata"), d["tMandata"]), 0.0, 35.0),
        "tBilancio": lim(_num(o.get("tBilancio"), d["tBilancio"]), -30.0, 40.0),
        "economizzatore": "temperatura" if o.get("economizzatore") == "temperatura" else "entalpico",
        "epsS": lim(_num(o.get("epsS"), d["epsS"]), 0.0, 1.0),
        "epsL": lim(_num(o.get("epsL"), d["epsL"]), 0.0, 1.0),
        "regolaBrina": "soglia" if o.get("regolaBrina") == "soglia" else "rugiada",
        "tSoglia": lim(_num(o.get("tSoglia"), d["tSoglia"]), -40.0, 20.0),
        "sbrinamento": o.get("sbrinamento", d["sbrinamento"]) is not False,
        "dP": lim(_num(o.get("dP"), d["dP"]), 0.0, 5000.0),
        "etaV": lim(_num(o.get("etaV"), d["etaV"]), 0.05, 1.0),
    }
    xm = _num(o.get("xMax"), math.nan)
    r["xMax"] = xm if xm > 0 else P.x_da_ur(X_MAX_RIF[0], X_MAX_RIF[1], p)
    return r


def potenza_ventilatore(o: dict) -> float:
    """kW elettrici in più nelle ore di recupero: 2 flussi × (f_min·V/3600) m³/s × ΔP Pa / η."""
    return 2 * (o["quotaMinima"] / 100 * o["V"] / 3600) * o["dP"] / o["etaV"] / 1000


def calcola(t, x, h, p: float, o: dict | None = None) -> dict:
    """Calcolo ora per ora su tutta la serie. t [°C], x [kg/kg], h [kJ/kg] array (NaN = ora senza dati).
    Restituisce regime (uint8), bandiere (uint8: 1 free cooling a temperatura, 2 entalpico, 4 modo raffrescamento),
    fcT, fcH (kW di freddo evitati: economizzatore a temperatura ed entalpico), rec (kW recuperati, caldo o freddo),
    perso (kW persi per lo sbrinamento), q0 (kW della batteria fredda senza economizzatore), m (kg/s)."""
    o = opzioni(o, p)
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    h = np.asarray(h, dtype=float)
    n = len(t)
    ok = np.isfinite(t) & np.isfinite(x) & np.isfinite(h)
    te = np.where(ok, t, 0.0)
    xe = np.where(ok, x, 0.0)
    he = np.where(ok, h, 0.0)
    E, I = o["estate"], o["inverno"]
    xrE, xrI = P.x_da_ur(E["t"], E["ur"], p), P.x_da_ur(I["t"], I["ur"], p)
    trE, trI = E["t"], I["t"]
    hrE, hrI = P.entalpia(trE, xrE), P.entalpia(trI, xrI)
    vE, vI = P.volume(trE, xrE, p), P.volume(trI, xrI, p)
    tS = o["tMandata"]
    xSatS = P.x_sat(tS, p)
    fm = o["quotaMinima"] / 100
    eS, eL = o["epsS"], o["epsL"]
    raff = te > o["tBilancio"]
    rif = o["riferimento"]
    if rif == 0:
        vref = P.volume(te, xe, p)
    elif rif == 1:
        vref = np.where(raff, vE, vI)
    elif rif == 2:
        vref = np.full(n, P.RA * 293.15 / 101.325)
    else:
        vref = (1 + xe) / 1.2
    m = o["V"] / 3600 / vref
    mOA = fm * m

    # ---- raffrescamento
    xin0 = fm * xe + (1 - fm) * xrE
    hin0 = fm * he + (1 - fm) * hrE
    q0 = m * np.maximum(0, hin0 - P.entalpia(tS, np.minimum(xin0, xSatS)))
    qOA = m * np.maximum(0, he - P.entalpia(tS, np.minimum(xe, xSatS)))
    tot = te <= tS
    onT = ~tot & (te < trE)
    onH = ~tot & (he < hrE) & (xe <= o["xMax"])
    fcT = np.where(tot, q0, np.where(onT, q0 - qOA, 0.0))
    fcH = np.where(tot, q0, np.where(onH, q0 - qOA, 0.0))
    on = onH if o["economizzatore"] == "entalpico" else onT
    tO = te + eS * (trE - te)
    xO = xe + eL * (xrE - xe)
    dh = he - P.entalpia(tO, xO)
    recE = np.where(~tot & ~on & (dh > 0), mOA * dh, 0.0)
    regE = np.where(tot, 1, np.where(on, np.where(te < trE, 2, 3), np.where(recE > 0, 4, 0)))

    # ---- riscaldamento
    fredda = te < trI
    tOi = te + eS * (trI - te)
    xOi = xe + eL * (xrI - xe)
    qPieno = mOA * np.maximum(0, P.entalpia(tOi, xOi) - he)
    tX = trI - eS * (trI - te)
    xX = xrI - eL * (xrI - xe)
    brina = np.zeros(n, dtype=bool)
    if o["regolaBrina"] == "soglia":
        brina = te < o["tSoglia"]
        tLim = trI - eS * (trI - o["tSoglia"])
    else:
        tLim = 0.0
        for i in np.nonzero(ok & ~raff & fredda & (tX < 0))[0]:
            brina[i] = tX[i] < P.t_rugiada(float(xX[i]), p)
    brina &= ok & ~raff & fredda
    qInv = qPieno.copy()
    perso = np.zeros(n)
    if o["sbrinamento"]:
        den = np.where(fredda, trI - te, 1.0)
        eEff = np.clip((trI - tLim) / den, 0.0, eS)
        lEff = eL * eEff / eS if eS > 0 else np.zeros(n)
        qBy = mOA * np.maximum(0, P.entalpia(te + eEff * (trI - te), xe + lEff * (xrI - xe)) - he)
        qInv = np.where(brina, qBy, qPieno)
        perso = np.where(brina, qPieno - qBy, 0.0)
    qInv = np.where(fredda, qInv, 0.0)
    regI = np.where(brina, 6, np.where(fredda & (qInv > 0), 5, 0))

    regime = np.where(raff, regE, regI).astype(np.uint8)
    regime[~ok] = SENZA_DATI
    band = (((tot | onT) & raff).astype(np.uint8) | (((tot | onH) & raff).astype(np.uint8) << 1) | (raff.astype(np.uint8) << 2))
    band[~ok] = 0
    z = lambda a: np.where(ok, a, 0.0)  # noqa: E731
    return {"opzioni": o, "n": n, "regime": regime, "bandiere": band,
            "fcT": z(np.where(raff, fcT, 0.0)), "fcH": z(np.where(raff, fcH, 0.0)),
            "rec": z(np.where(raff, recE, qInv)), "perso": z(np.where(raff, 0.0, perso)),
            "q0": z(np.where(raff, q0, 0.0)), "m": z(m), "pVent": potenza_ventilatore(o)}


def riassumi(R: dict, indici, anni: float, mese=None) -> dict:
    """Somme di un gruppo di ore (indici), per anno medio (anni della serie usata dal gruppo). mese (1–12 per ogni ora
    della serie) facoltativo: tabella mensile dell'anno medio."""
    o = R["opzioni"]
    idx = np.asarray(indici, dtype=np.int64)
    reg = R["regime"][idx]
    validi = reg != SENZA_DATI
    idx, reg = idx[validi], reg[validi]
    band = R["bandiere"][idx]
    a = max(float(anni), 1 / 8766)
    fcT, fcH, rec, perso = R["fcT"][idx], R["fcH"][idx], R["rec"][idx], R["perso"][idx]
    entalpico = o["economizzatore"] == "entalpico"
    fc = fcH if entalpico else fcT
    raff = (band & 4) > 0
    est = raff & (reg == 4)
    inv = ~raff & (rec > 0)
    nrec = int(np.count_nonzero(rec > 0))
    mx = lambda v: float(v.max()) if v.size else 0.0  # noqa: E731
    out = {
        "ore": int(idx.size), "anni": a,
        "oreRegime": [int(np.count_nonzero(reg == k)) / a for k in range(len(REGIMI))],
        "oreRaffrescamento": int(np.count_nonzero(raff)) / a,
        "oreFcT": int(np.count_nonzero(band & 1)) / a, "oreFcH": int(np.count_nonzero(band & 2)) / a,
        "kwhFcT": float(fcT.sum()) / a, "kwhFcH": float(fcH.sum()) / a, "kwhFc": float(fc.sum()) / a,
        "piccoFcT": mx(fcT), "piccoFcH": mx(fcH),
        "kwhInverno": float(rec[inv].sum()) / a, "kwhEstate": float(rec[est].sum()) / a,
        "piccoInverno": mx(rec[inv]), "piccoEstate": mx(rec[est]),
        "kwhPerso": float(perso.sum()) / a, "oreBrina": int(np.count_nonzero(reg == 6)) / a,
        "oreRecupero": nrec / a, "kwhElettrici": nrec * R["pVent"] / a,
    }
    out["rapporto"] = (out["kwhInverno"] + out["kwhEstate"]) / out["kwhElettrici"] if out["kwhElettrici"] > 0 else math.nan
    if mese is not None:
        mm = np.asarray(mese)[idx].astype(int) - 1
        sel = band & (2 if entalpico else 1)
        out["mensile"] = {
            "oreFc": (np.bincount(mm, weights=(sel > 0).astype(float), minlength=12) / a).tolist(),
            "kwhFc": (np.bincount(mm, weights=fc, minlength=12) / a).tolist(),
            "kwhInverno": (np.bincount(mm, weights=np.where(inv, rec, 0.0), minlength=12) / a).tolist(),
            "kwhEstate": (np.bincount(mm, weights=np.where(est, rec, 0.0), minlength=12) / a).tolist(),
            "oreBrina": (np.bincount(mm, weights=(reg == 6).astype(float), minlength=12) / a).tolist(),
            "kwhElettrici": (np.bincount(mm, weights=(rec > 0) * R["pVent"], minlength=12) / a).tolist(),
            "kwhPerso": (np.bincount(mm, weights=perso, minlength=12) / a).tolist(),
        }
    return out


def un_ora(t: float, ur: float, p: float, o: dict | None = None) -> dict:
    """Una sola ora (per i controlli a mano e le condizioni di progetto)."""
    x = P.x_da_ur(t, ur, p)
    R = calcola(np.array([t]), np.array([x]), np.array([P.entalpia(t, x)]), p, o)
    return {"regime": REGIMI[int(R["regime"][0])], "fcT": float(R["fcT"][0]), "fcH": float(R["fcH"][0]), "rec": float(R["rec"][0]),
            "perso": float(R["perso"][0]), "q0": float(R["q0"][0]), "m": float(R["m"][0]), "pVent": R["pVent"]}
