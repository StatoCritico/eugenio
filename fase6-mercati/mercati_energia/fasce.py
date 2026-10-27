"""Fasce orarie ARERA (F1, F2, F3) e festività nazionali.

F1: lunedì–venerdì 8–19, esclusi i festivi nazionali
F2: lunedì–venerdì 7–8 e 19–23; sabato 7–23 (esclusi i festivi)
F3: lunedì–sabato 0–7 e 23–24; domenica e festivi tutto il giorno
Il 4 ottobre (San Francesco) è festa nazionale dal 2026: incluso da quell'anno. Se ARERA
indicasse diversamente, o per altri giorni, usare `festivi_extra` / `escludi` nella configurazione.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np
import pandas as pd

FISSE = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]


def pasqua(anno: int) -> dt.date:
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(anno, (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1)


@lru_cache(maxsize=128)
def festivi(anno: int, extra: tuple[dt.date, ...] = ()) -> frozenset[dt.date]:
    s = {dt.date(anno, m, g) for m, g in FISSE}
    if anno >= 2026:
        s.add(dt.date(anno, 10, 4))
    s.add(pasqua(anno) + dt.timedelta(days=1))
    s |= {x for x in extra if x.year == anno}
    return frozenset(s)


def fascia(istanti_utc: pd.Series, extra: tuple[dt.date, ...] = ()) -> pd.Series:
    """Fascia ARERA dell'intervallo che inizia in `istanti_utc` (ora locale italiana)."""
    loc = pd.DatetimeIndex(pd.to_datetime(istanti_utc, utc=True)).tz_convert("Europe/Rome")
    giorni = loc.date
    fest = np.array([g in festivi(g.year, extra) for g in giorni])
    dow, h = loc.day_of_week.to_numpy(), loc.hour.to_numpy()
    domfest = fest | (dow == 6)
    f1 = ~domfest & (dow <= 4) & (h >= 8) & (h < 19)
    f2 = ~domfest & (((dow <= 4) & (((h >= 7) & (h < 8)) | ((h >= 19) & (h < 23)))) | ((dow == 5) & (h >= 7) & (h < 23)))
    out = np.where(f1, "F1", np.where(f2, "F2", "F3"))
    return pd.Series(out, index=getattr(istanti_utc, "index", None))
