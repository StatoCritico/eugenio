"""Carichi latenti dell'aria esterna: gemello Python della parte di calcolo di fase5-sito/sito/aria_latenti.js
(pagina «Trattamento aria › Carichi latenti», 14/11/2026).

Per ogni ora del gruppo (indici della serie oraria) con T e UR esterne note:

    x_t = x alla T e all'UR obiettivo (alla pressione del comune), h_t la sua entalpia
    ṁ   = V/(3600·v_rif) [kg/s di aria secca], v_rif come psicro.portataMassica, ora per ora:
          0 aria esterna di quell'ora (predefinito, come il foglio), 1 aria interna obiettivo, 2 aria standard
          20 °C 101325 Pa, 3 densità fissa 1,2 kg/m³ (v = (1 + x_e)/1,2)

  ESTATE (deumidificazione; l'UR obiettivo è un massimo)
    l'ora richiede deumidificazione se x_e > x_t
    potenza latente      Q_l = ṁ·(x_e − x_t)·2501                 [kW]   (r = 2501 kJ/kg, come il foglio)
    condensa             ṁ·(x_e − x_t)·3600                        [kg/h]
    parte sensibile      Q_s = ṁ·(1,006 + 1,86·x_e)·(T_e − T_t)    se T_e > T_t (raffreddamento fino a T obiettivo)
    totale (entalpia)    Q_t = ṁ·(h_e − h_t)                        se positivo
  INVERNO (umidificazione a vapore; l'UR obiettivo è un minimo)
    l'ora richiede umidificazione se x_e < x_t
    potenza del vapore   Q_l = ṁ·(x_t − x_e)·2676                  [kW]   (h vapore 2676 kJ/kg, come il foglio)
    acqua                ṁ·(x_t − x_e)·3600                        [kg/h]
    parte sensibile      Q_s = ṁ·(1,006 + 1,86·x_e)·(T_t − T_e)    se T_e < T_t (riscaldamento fino a T obiettivo)
    totale (entalpia)    Q_t = ṁ·(h_t − h_e)                        se positivo

Ogni ora vale 1 h: kWh = kW. Valori «all'anno» = somme divise per gli anni del gruppo (ore della finestra degli
ultimi N anni / 8766). Potenza al livello di progetto: quantile delle potenze di tutte le ore del gruppo (zeri compresi)
superato solo nel livello % delle ore (estate: livello estivo, predefinito 1 %; inverno: 100 − livello invernale).
SHR = ΣQ_s/(ΣQ_s + ΣQ_l). Classi di Δx da 1 g/kg (l'ultima aperta). Curva di durata: potenze delle ore trattate in
ordine decrescente, in ascissa le ore all'anno.

T ed x arrivano come nel browser (Float32Array): qui si arrotondano a float32 prima del calcolo, così i conteggi alle
soglie coincidono con il sito (test di parità fase5-sito/tests/test_aria_latenti.py).
"""
from __future__ import annotations

import math

import numpy as np

from . import psicro as P

R_LATENTE = P.R0          # 2501 kJ/kg
H_VAPORE = P.H_VAPORE     # 2676 kJ/kg
SOGLIA_DX = 1e-7          # kg/kg: ore esattamente all'obiettivo non contano (arrotondamento Float32), come aria_latenti.js
ORE_ANNO = 8766.0


def anni_finestra(n: int, indice_inizio: int) -> float:
    """anni coperti dalla finestra del gruppo: ore dall'inizio degli ultimi N anni alla fine della serie / 8766."""
    return max(0, n - indice_inizio) / ORE_ANNO


def calcola(stagione: str, t, x, h, indici, p: float, t_obiettivo: float, ur_obiettivo: float, V: float = 1000.0,
            riferimento: int = 0, mese=None, anni: float = 1.0, livello: float | None = None, classe_g: float = 1.0,
            n_classi: int = 10, punti_curva: int = 200) -> dict:
    """Carico latente (estate) o di umidificazione a vapore (inverno) dell'aria esterna sulle ore `indici`.

    t, x, h: serie (°C, kg/kg, kJ/kg); indici: ore del gruppo; mese: mese locale 1–12 di ogni ora (facoltativo);
    anni: anni del gruppo; livello: % delle ore in cui la potenza di progetto è superata (predefinito 1)."""
    inverno = stagione == "inverno"
    t32 = np.asarray(t, dtype=np.float32).astype(float)
    x32 = np.asarray(x, dtype=np.float32).astype(float)
    h32 = np.asarray(h, dtype=np.float32).astype(float)
    idx = np.asarray(indici, dtype=np.int64)
    ob = P.stato(t_obiettivo, {"ur": ur_obiettivo}, p)
    xt, ht, tt = ob["x"], ob["h"], t_obiettivo
    te, xe, he = t32[idx], x32[idx], h32[idx]
    ok = np.isfinite(te) & np.isfinite(xe)
    idx, te, xe, he = idx[ok], te[ok], xe[ok], he[ok]
    n = len(idx)
    rif = int(riferimento) if riferimento in (0, 1, 2, 3) else 0
    if rif == 0:
        vref = P.RA * (te + 273.15) * (1 + 1.607858 * xe) / (p / 1000)
    elif rif == 1:
        vref = np.full(n, ob["v"])
    elif rif == 2:
        vref = np.full(n, P.RA * 293.15 / 101.325)
    else:
        vref = (1 + xe) / 1.2
    m = V / 3600 / vref
    dx = (xt - xe) if inverno else (xe - xt)
    si = dx > SOGLIA_DX
    r = H_VAPORE if inverno else R_LATENTE
    ql = np.where(si, m * dx * r, 0.0)
    acqua = np.where(si, m * dx * 3600, 0.0)
    dt_ = (tt - te) if inverno else (te - tt)
    qs = np.where(dt_ > 0, m * (P.CPA + P.CPV * xe) * dt_, 0.0)
    dh = (ht - he) if inverno else (he - ht)
    qt = np.where(dh > 0, m * dh, 0.0)
    anni = anni if anni and anni > 0 else 1.0
    lv = 1.0 if livello is None else float(livello)
    ore = int(si.sum())
    E, A, S, T = float(ql.sum()), float(acqua.sum()), float(qs.sum()), float(qt.sum())
    ordinate = np.sort(ql)
    picco_livello = P.quantile(ordinate, 1 - lv / 100) if n else math.nan
    # mesi (anno medio)
    mesi = []
    mm = np.asarray(mese)[idx] if mese is not None else None
    for k in range(1, 13):
        sel = (mm == k) if mm is not None else np.zeros(n, bool)
        mesi.append({"mese": k, "ore": float((si & sel).sum()) / anni, "energia": float(ql[sel].sum()) / anni,
                     "acqua": float(acqua[sel].sum()) / anni, "sensibile": float(qs[sel].sum()) / anni,
                     "oreGruppo": float(sel.sum()) / anni})
    # classi di Δx (g/kg)
    dxg = dx[si] * 1000
    ci = np.minimum(np.floor(dxg / classe_g).astype(int), n_classi - 1)
    classi = []
    for k in range(n_classi):
        sel = ci == k
        classi.append({"da": k * classe_g, "a": None if k == n_classi - 1 else (k + 1) * classe_g,
                       "ore": float(sel.sum()) / anni, "energia": float(ql[si][sel].sum()) / anni})
    # curva di durata
    giu = np.sort(ql[si])[::-1]
    curva = []
    if ore:
        npt = min(punti_curva, ore)
        visti = set()
        for j in range(npt):
            rk = 0 if npt == 1 else int(math.floor(j * (ore - 1) / (npt - 1) + 0.5))
            if rk in visti:
                continue
            visti.add(rk)
            curva.append({"ore": (rk + 1) / anni, "kW": float(giu[rk])})
    tot_sl = S + E
    return {
        "stagione": "inverno" if inverno else "estate",
        "obiettivo": {"t": tt, "ur": ur_obiettivo, "x": xt, "xg": xt * 1000, "h": ht, "v": ob["v"], "rho": ob["rho"],
                      "tdew": ob["tdew"], "twb": ob["twb"]},
        "V": V, "riferimento": rif, "anni": anni, "livello": lv, "r": r,
        "oreGruppo": n, "ore": ore, "oreAnno": ore / anni, "quota": ore / n if n else 0.0,
        "energia": E, "energiaAnno": E / anni, "acqua": A, "acquaAnno": A / anni,
        "sensibile": S, "sensibileAnno": S / anni, "totale": T, "totaleAnno": T / anni,
        "picco": float(ql.max()) if n else 0.0, "piccoLivello": picco_livello,
        "acquaPicco": float(acqua.max()) if n else 0.0,
        "shr": S / tot_sl if tot_sl > 0 else math.nan,
        "portataMedia": float(m.mean()) if n else math.nan,
        "mesi": mesi, "classi": classi, "curva": curva,
    }
