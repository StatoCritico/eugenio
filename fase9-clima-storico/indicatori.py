"""Funzioni di calcolo degli indicatori climatici "alla maniera" di UNI 10349-1 e DPR 412/93.

Stesse convenzioni di fase3-storico/meteo_storico/legge10.py (zone, periodi di accensione, Magnus,
regola della "zona coerente", stagione 1 luglio – 30 giugno indicata con l'anno di inizio).
"""
from __future__ import annotations

import numpy as np

# DPR 412/93 art. 2 (zone) e art. 9 (periodi di accensione), identici a legge10.py
ZONE = [("A", 0, 600), ("B", 601, 900), ("C", 901, 1400), ("D", 1401, 2100), ("E", 2101, 3000), ("F", 3001, 1e9)]
NOMI_ZONE = "ABCDEF"
PERIODI = {"A": ((12, 1), (3, 15)), "B": ((12, 1), (3, 31)), "C": ((11, 15), (3, 31)),
           "D": ((11, 1), (4, 15)), "E": ((10, 15), (4, 15)), "F": None}
GRADIENTE = 0.0065      # °C/m, gradiente termico verticale standard (−6,5 °C/km)
T_BASE = 20.0


def zona_da_gg(gg: float) -> str:
    """Tabella art. 2 DPR 412/93; i valori decimali si arrotondano all'intero (601 = B)."""
    if gg is None or not np.isfinite(gg):
        return None
    g = round(gg)
    for z, lo, hi in ZONE:
        if g <= hi:
            return z
    return "F"


def maschere_periodi(mesi: np.ndarray, giorni: np.ndarray) -> np.ndarray:
    """Matrice booleana (6 zone × giorni): giorno compreso nel periodo di accensione della zona."""
    md = mesi * 100 + giorni
    out = np.ones((6, len(md)), dtype=bool)
    for k, z in enumerate(NOMI_ZONE):
        per = PERIODI[z]
        if per is not None:
            (m1, g1), (m2, g2) = per
            out[k] = (md >= m1 * 100 + g1) | (md <= m2 * 100 + g2)
    return out


def lunghezza_periodi() -> np.ndarray:
    """Giorni di ciascun periodo in una stagione non bisestile (per il controllo di completezza)."""
    import pandas as pd
    d = pd.date_range("2001-07-01", "2002-06-30")
    return maschere_periodi(d.month.to_numpy(), d.day.to_numpy()).sum(axis=1)


def zona_coerente(gg_per_zona: np.ndarray) -> str:
    """Come legge10.py: la zona i cui GG, calcolati sul suo stesso periodo di accensione, cadono nella sua
    fascia; se nessuna (casi limite), la zona dei GG sull'anno intero."""
    for k, z in enumerate(NOMI_ZONE):
        if np.isfinite(gg_per_zona[k]) and zona_da_gg(gg_per_zona[k]) == z:
            return z
    return zona_da_gg(gg_per_zona[5]) if np.isfinite(gg_per_zona[5]) else "-"


def pressione_vapore_da_td(td):
    return 610.94 * np.exp(17.625 * td / (td + 243.04))


def correzione_quota(z_cella, z_comune):
    """Δ°C da sommare alla temperatura della cella per portarla alla quota del comune (−6,5 °C/km)."""
    return GRADIENTE * (np.asarray(z_cella, float) - np.asarray(z_comune, float))


def pendenza_per_decennio(x: np.ndarray, y: np.ndarray, minimo: int = 10):
    ok = np.isfinite(y)
    if ok.sum() < minimo:
        return None
    return float(np.polyfit(x[ok].astype(float), y[ok], 1)[0] * 10)


def quantile_da_estremi(estremi: np.ndarray, n_tot: int, q: float, basso: bool) -> float:
    """Quantile (interpolazione lineare, come numpy/pandas) di una serie di n_tot valori di cui si conoscono
    solo gli estremi (i più bassi se basso=True, i più alti altrimenti), in numero sufficiente."""
    v = np.sort(estremi[np.isfinite(estremi)])
    if n_tot < 2 or len(v) == 0:
        return float("nan")
    pos = q * (n_tot - 1)
    if not basso:
        pos = (n_tot - 1) - pos        # posizione contata dall'alto
        v = v[::-1]
    k = int(np.floor(pos))
    if k + 1 >= len(v):
        return float("nan")            # estremi insufficienti
    f = pos - k
    return float(v[k] + (v[k + 1] - v[k]) * f)
