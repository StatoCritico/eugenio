"""Variabili di calendario note in futuro: festività italiane, giorno della settimana, ora."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np
import pandas as pd

FISSE = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]


def pasqua(anno: int) -> dt.date:
    """Algoritmo di Meeus/Jones/Butcher (calendario gregoriano)."""
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese = (h + l - 7 * m + 114) // 31
    giorno = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(anno, mese, giorno)


@lru_cache(maxsize=64)
def festivi(anno: int) -> frozenset[dt.date]:
    s = {dt.date(anno, m, g) for m, g in FISSE}
    if anno >= 2026:  # San Francesco, di nuovo festa nazionale dal 2026
        s.add(dt.date(anno, 10, 4))
    p = pasqua(anno)
    s |= {p, p + dt.timedelta(days=1)}
    return frozenset(s)


def caratteristiche(indice: pd.DatetimeIndex, orario: bool) -> pd.DataFrame:
    """indice in ora locale Europe/Rome."""
    giorni = indice.date
    fest = np.array([g in festivi(g.year) for g in giorni], dtype="float32")
    dow = indice.dayofweek.to_numpy()
    out = pd.DataFrame(index=indice)
    out["festivo"] = np.maximum(fest, (dow == 6).astype("float32"))
    out["sabato"] = (dow == 5).astype("float32")
    # ponti: giorno feriale tra un festivo e il fine settimana
    prima = np.array([(g - dt.timedelta(days=1)) in festivi(g.year) for g in giorni])
    dopo = np.array([(g + dt.timedelta(days=1)) in festivi(g.year) for g in giorni])
    out["ponte"] = (((dow == 0) & dopo) | ((dow == 4) & prima)).astype("float32")
    doy = indice.dayofyear.to_numpy()
    out["anno_sin"] = np.sin(2 * np.pi * doy / 365.25).astype("float32")
    out["anno_cos"] = np.cos(2 * np.pi * doy / 365.25).astype("float32")
    if orario:
        h = indice.hour.to_numpy()
        out["ora_sin"] = np.sin(2 * np.pi * h / 24).astype("float32")
        out["ora_cos"] = np.cos(2 * np.pi * h / 24).astype("float32")
    return out
