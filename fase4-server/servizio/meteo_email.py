"""Previsioni per i servizi email (14/11/2026): settimanale (settimana dopo) e avvisi meteo (domani).

Solo per i comuni scelti dagli iscritti, chiesti a Open-Meteo a blocchi di 50 con il limitatore del server (stesso
conteggio delle previsioni del sito): funzionano anche per i comuni fuori dalle REGIONI_AGGIORNATE. Modello: la scelta
automatica di Open-Meteo per ogni punto («best_match», i modelli ad area limitata più fini nei primi giorni), perché
servono anche raffiche e neve; le previsioni del sito (ICON-2I e IFS corretti) restano per i consumi.

Valori giornalieri per giorno civile italiano: temperatura minima, massima e media, pioggia totale e massima in un'ora
(mm, neve fusa compresa), neve fresca (cm), raffica massima (km/h), gradi giorno base 20 °C dalla media oraria.
"""
from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

from meteo_storico.scarica import client, richiesta

from . import config as C, meteo

log = logging.getLogger(__name__)
ROMA = "Europe/Rome"
VARIABILI_EMAIL = ["temperature_2m", "precipitation", "snowfall", "wind_gusts_10m"]
MODELLO_EMAIL = "best_match"
FONTE = ("Previsioni: Open-Meteo.com (CC BY 4.0), modelli scelti da Open-Meteo per ogni punto; elaborazione EuGEnio.")


def giornalieri(orario: pd.DataFrame) -> pd.DataFrame:
    """Da orario (time UTC e VARIABILI_EMAIL) a giornaliero italiano. Giorni con meno di 20 ore esclusi."""
    if orario is None or orario.empty:
        return pd.DataFrame(columns=["data", "tmin", "tmax", "tmedia", "pioggia", "pioggia_1h", "neve", "raffica",
                                     "gg20"])
    o = orario.copy()
    o["data"] = pd.to_datetime(o.time, utc=True).dt.tz_convert(ROMA).dt.date
    g = o.groupby("data").agg(tmin=("temperature_2m", "min"), tmax=("temperature_2m", "max"),
                              tmedia=("temperature_2m", "mean"), pioggia=("precipitation", "sum"),
                              pioggia_1h=("precipitation", "max"), neve=("snowfall", "sum"),
                              raffica=("wind_gusts_10m", "max"), ore=("temperature_2m", "count"))
    gg = o.assign(gg=(20 - o.temperature_2m).clip(lower=0) / 24).groupby("data").gg.sum()
    g["gg20"] = gg
    g = g[g.ore >= 20].drop(columns="ore")
    return g.reset_index()


def previsioni(istat: list[str], giorni: int) -> dict[str, pd.DataFrame]:
    """Previsioni giornaliere dei comuni (codici ISTAT) per i prossimi `giorni` giorni, oggi compreso."""
    istat = sorted(set(str(i) for i in istat))
    if not istat:
        return {}
    cm = pd.read_parquet(C.DATI / "comuni.parquet", columns=["istat", "lat", "lon"])
    cm = cm[cm.istat.astype(str).isin(istat)].reset_index(drop=True)
    http, lim = client(), meteo._lim()
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(cm), 50):
        blocco = cm.iloc[i:i + 50]
        dati = richiesta(http, lim, meteo._url(None), blocco, MODELLO_EMAIL, forecast_days=giorni,
                         variabili=VARIABILI_EMAIL)
        for r, df in zip(blocco.itertuples(), dati):
            out[str(r.istat)] = giornalieri(df)
    log.info("Previsioni per le email: %d comuni, %d giorni", len(out), giorni)
    return out


def superamenti(giorno: pd.Series | dict) -> list[str]:
    """Tipi di avviso superati in un giorno di previsione: pioggia, neve, vento (soglie del .env)."""
    g = dict(giorno)
    tipi = []

    def ok(x):
        return x is not None and not (isinstance(x, float) and np.isnan(x))
    if (ok(g.get("pioggia")) and g["pioggia"] >= C.AVVISO_PIOGGIA_24H_MM) or \
            (ok(g.get("pioggia_1h")) and g["pioggia_1h"] >= C.AVVISO_PIOGGIA_1H_MM):
        tipi.append("pioggia")
    if ok(g.get("neve")) and g["neve"] >= C.AVVISO_NEVE_CM:
        tipi.append("neve")
    if ok(g.get("raffica")) and g["raffica"] >= C.AVVISO_VENTO_KMH:
        tipi.append("vento")
    return tipi


def giorno(prev: pd.DataFrame, data: dt.date) -> dict | None:
    if prev is None or prev.empty:
        return None
    r = prev[prev.data == data]
    return None if r.empty else r.iloc[0].to_dict()
