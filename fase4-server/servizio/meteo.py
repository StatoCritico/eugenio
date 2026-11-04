"""Dati meteo sul server: previsioni (ICON-2I + IFS) e aggiornamento giornaliero dello storico.

Riferimento comune di "clima": ICON seamless. Lo storico ERA5 e le previsioni ICON-2I / IFS sono
riportati a questo riferimento con i parametri stimati nella fase 3 (parametri_correzione.parquet),
così il modello vede passato e futuro con le stesse caratteristiche.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from meteo_storico import VARIABILI
from meteo_storico.aggrega import giornaliero
from meteo_storico.correzione import applica
from meteo_storico.limiti import Limitatore
from meteo_storico.scarica import FONTI, client, richiesta

from . import config as C

log = logging.getLogger(__name__)
_blocco = threading.Lock()
URL_PREVISIONI = "https://api.open-meteo.com/v1/forecast"


# ---------------------------------------------------------------------------------------------- utilità
def _salva(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    df.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(p)


def comuni(aggiornati: bool = False) -> pd.DataFrame:
    """Comuni serviti (REGIONI; vuoto = tutta Italia). Con `aggiornati=True` solo quelli il cui meteo recente e le cui
    previsioni si aggiornano ogni giorno con l'API gratuita (REGIONI_AGGIORNATE): per gli altri restano lo storico
    esportato dalla fase 3 e, nelle previsioni dei consumi, la climatologia."""
    df = pd.read_parquet(C.DATI / "comuni.parquet")
    if C.SOLO_COMUNI:
        return df[df.istat.isin(C.SOLO_COMUNI)]
    if C.REGIONI:
        df = df[df.regione_cod.isin(C.REGIONI)]
    if aggiornati and C.REGIONI_AGGIORNATE:
        df = df[df.regione_cod.isin(C.REGIONI_AGGIORNATE)]
    return df


@lru_cache(maxsize=1)
def _parametri(mtime: float) -> pd.DataFrame:
    p = C.DATI / "parametri_correzione.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def parametri(istat: str, sorgente: str) -> pd.DataFrame | None:
    p = C.DATI / "parametri_correzione.parquet"
    if not p.exists():
        return None
    par = _parametri(p.stat().st_mtime)
    sel = par[(par.istat == istat) & (par.sorgente == sorgente)]
    return sel if len(sel) else None


def _url(fonte_storica: str | None) -> str:
    if C.OPEN_METEO_LOCALE:
        return C.OPEN_METEO_LOCALE.rstrip("/") + (FONTI[fonte_storica]["percorso_locale"] if fonte_storica else "/v1/forecast")
    return FONTI[fonte_storica]["url"] if fonte_storica else URL_PREVISIONI


def _lim() -> Limitatore:
    return Limitatore(C.DATI / "stato_api.json", illimitato=bool(C.OPEN_METEO_LOCALE))


def _a_blocchi(df: pd.DataFrame, n: int = 50):
    for i in range(0, len(df), n):
        yield df.iloc[i:i + n]


# ---------------------------------------------------------------------------------------------- previsioni
def miscela(breve: pd.DataFrame | None, lungo: pd.DataFrame | None, emissione: pd.Timestamp) -> pd.DataFrame:
    """ICON-2I fino a 48 h, transizione lineare 48→72 h, poi IFS. Colonne: time, variabili, peso_icon2i."""
    tempi = [pd.DatetimeIndex(d.time) for d in (breve, lungo) if d is not None and len(d)]
    if not tempi:
        return pd.DataFrame(columns=["time", *VARIABILI, "peso_icon2i"])
    idx = tempi[0]
    for t in tempi[1:]:
        idx = idx.union(t)
    b = breve.set_index("time").reindex(idx) if breve is not None and len(breve) else None
    l = lungo.set_index("time").reindex(idx) if lungo is not None and len(lungo) else None
    ore = (idx - emissione) / pd.Timedelta(hours=1)
    w = np.clip((C.MISCELA_A_H - ore) / (C.MISCELA_A_H - C.MISCELA_DA_H), 0, 1).to_numpy(dtype="float64")
    out = pd.DataFrame(index=idx)
    pesi = np.zeros(len(idx))
    for v in VARIABILI:
        xb = b[v].to_numpy(dtype="float64") if b is not None else np.full(len(idx), np.nan)
        xl = l[v].to_numpy(dtype="float64") if l is not None else np.full(len(idx), np.nan)
        wb = np.where(np.isnan(xb), 0.0, np.where(np.isnan(xl), 1.0, w))
        out[v] = (np.nan_to_num(xb) * wb + np.nan_to_num(xl) * (1 - wb)).astype("float32")
        out.loc[np.isnan(xb) & np.isnan(xl), v] = np.nan
        if v == "temperature_2m":
            pesi = wb
    out["peso_icon2i"] = pesi.astype("float32")
    out.index.name = "time"
    return out.reset_index()


def aggiorna_previsioni() -> Path:
    cm = comuni(aggiornati=True)
    http, lim = client(), _lim()
    emissione = pd.Timestamp.now(tz="UTC").floor("D")
    parti = []
    for blocco in _a_blocchi(cm):
        brevi = richiesta(http, lim, _url(None), blocco, C.MODELLO_BREVE, forecast_days=4)
        lunghi = richiesta(http, lim, _url(None), blocco, C.MODELLO_LUNGO, forecast_days=C.GIORNI_PREVISIONE)
        for r, b, l in zip(blocco.itertuples(), brevi, lunghi):
            pb, pl = parametri(r.istat, "icon2i"), parametri(r.istat, "ifs")
            if pb is not None and len(b):
                b = applica(b, pb)
            if pl is not None and len(l):
                l = applica(l, pl)
            m = miscela(b, l, emissione)
            m.insert(0, "istat", r.istat)
            parti.append(m)
    df = pd.concat(parti, ignore_index=True)
    p = C.DATI / "previsioni" / "ultima.parquet"
    with _blocco:
        _salva(df, p)
        (p.with_suffix(".json")).write_text(json.dumps({
            "emissione": emissione.isoformat(), "aggiornato": pd.Timestamp.now(tz="UTC").isoformat(),
            "comuni": int(df.istat.nunique()), "fino_a": df.time.max().isoformat(),
            "modelli": {"0-48h": C.MODELLO_BREVE, "48-72h": "miscela lineare", "72h+": C.MODELLO_LUNGO}}))
    log.info("Previsioni aggiornate: %d comuni, fino a %s", df.istat.nunique(), df.time.max())
    return p


@lru_cache(maxsize=2)
def _previsioni(mtime: float) -> pd.DataFrame:
    return pd.read_parquet(C.DATI / "previsioni" / "ultima.parquet")


def previsioni(istat: str) -> pd.DataFrame:
    p = C.DATI / "previsioni" / "ultima.parquet"
    if not p.exists():
        return pd.DataFrame(columns=["time", *VARIABILI, "peso_icon2i"])
    d = _previsioni(p.stat().st_mtime)
    return d[d.istat == istat].drop(columns="istat").reset_index(drop=True)


# ---------------------------------------------------------------------------------------------- storico
def aggiorna_storico(giorni: int = 15) -> None:
    """Aggiunge gli ultimi giorni: ICON storico (orario) ed ERA5 corretto (giornaliero)."""
    cm = comuni(aggiornati=True)
    http, lim = client(), _lim()
    oggi = dt.datetime.now(dt.timezone.utc).date()
    # ICON seamless storico → orario/<istat>.parquet
    ini, fin = oggi - dt.timedelta(days=5), oggi - dt.timedelta(days=1)
    for blocco in _a_blocchi(cm):
        for r, df in zip(blocco.itertuples(), richiesta(http, lim, _url("icon"), blocco, "icon_seamless",
                                                          inizio=ini, fine=fin)):
            p = C.DATI / "orario" / f"{r.istat}.parquet"
            vecchio = pd.read_parquet(p) if p.exists() else None
            nuovo = pd.concat([vecchio, df]) if vecchio is not None else df
            _salva(nuovo.drop_duplicates("time", keep="last").sort_values("time"), p)
    # ERA5 → correzione → giornaliero.parquet
    ini, fin = oggi - dt.timedelta(days=giorni), oggi - dt.timedelta(days=FONTI["era5"]["ritardo_giorni"])
    nuovi = []
    for blocco in _a_blocchi(cm):
        for r, df in zip(blocco.itertuples(), richiesta(http, lim, _url("era5"), blocco, "era5_seamless",
                                                          inizio=ini, fine=fin)):
            par = parametri(r.istat, "era5")
            g = giornaliero(applica(df, par) if par is not None else df)
            g.insert(0, "istat", r.istat)
            nuovi.append(g)
    if nuovi:
        with _blocco:
            aggiorna_giornaliero(C.DATI / "giornaliero.parquet", pd.concat(nuovi, ignore_index=True))
    log.info("Storico aggiornato (%s)", lim.riepilogo())


def aggiorna_giornaliero(p: Path, nuovi: pd.DataFrame) -> None:
    """Unisce `nuovi` (istat, data, ...) a giornaliero.parquet un blocco (row group) alla volta: per tutta Italia il
    file ha ~34 milioni di righe e non sta nella memoria del worker. I comuni nuovi vanno in coda."""
    import pyarrow.parquet as pq
    from meteo_storico.aggrega import scrivi_giornaliero
    nuovi = nuovi.copy()
    nuovi["data"] = pd.to_datetime(nuovi["data"]).dt.date        # stesso tipo del file (date32)
    nuovi = nuovi.sort_values(["istat", "data"])
    if not p.exists():
        scrivi_giornaliero([nuovi.reset_index(drop=True)], p)
        return
    pf = pq.ParquetFile(p)
    da_unire = set(nuovi.istat)
    visti: set = set()

    def blocchi():
        for i in range(pf.num_row_groups):
            df = pf.read_row_group(i).to_pandas()
            df["data"] = pd.to_datetime(df["data"]).dt.date
            qui = da_unire & set(df.istat.unique())
            if qui:
                df = pd.concat([df, nuovi[nuovi.istat.isin(qui)]], ignore_index=True)
                df = df.drop_duplicates(["istat", "data"], keep="last").sort_values(["istat", "data"])
                visti.update(qui)
            yield df.reset_index(drop=True)
        resto = nuovi[~nuovi.istat.isin(visti)]
        if len(resto):
            yield resto.reset_index(drop=True)

    scrivi_giornaliero(blocchi(), p)


@lru_cache(maxsize=64)
def _giornaliero_comune(istat: str, mtime: float) -> pd.DataFrame:
    """Solo il blocco del comune (filtro sul parquet): il file nazionale non si carica mai tutto in memoria."""
    d = pd.read_parquet(C.DATI / "giornaliero.parquet", filters=[("istat", "=", istat)])
    return d[d.istat == istat].drop(columns="istat").sort_values("data").reset_index(drop=True)


def storico_giornaliero(istat: str) -> pd.DataFrame:
    p = C.DATI / "giornaliero.parquet"
    return _giornaliero_comune(istat, p.stat().st_mtime).copy()


def storico_orario(istat: str) -> pd.DataFrame:
    p = C.DATI / "orario" / f"{istat}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["time", *VARIABILI])
