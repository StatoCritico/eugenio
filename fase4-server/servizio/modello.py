"""Previsione dei consumi con TiRex-2 e covariate meteo/calendario.

Due modalità:
  * breve  – passo orario, storia fino a 90 giorni, orizzonte fino a 15 giorni (meteo previsto:
             ICON-2I fino a 72 h, poi IFS: oltre le 72 h l'incertezza meteo cresce);
  * lungo  – passo giornaliero, storia fino a 3 anni (ERA5 corretto), orizzonte fino a 1 anno:
             per i primi 15 giorni meteo previsto, poi **climatologia** (media dello stesso giorno
             negli anni disponibili) – è uno scenario "anno tipo", non una previsione meteo.
Il tempo è gestito in UTC (orario) o per giorno civile Europe/Rome (giornaliero).
"""
from __future__ import annotations

import logging
import os
import threading

# TiRex-2 prova a compilare parti del modello con torch.compile, che sul server (immagine senza g++) fallisce con
# «No working C++ compiler found»: si usa l'esecuzione normale, su CPU la differenza di velocità è trascurabile.
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

import numpy as np
import pandas as pd

from meteo_storico.aggrega import giornaliero

from . import calendario, config as C, meteo

log = logging.getLogger(__name__)
_modello = None
_carica = threading.Lock()
_calcolo = threading.Semaphore(1)  # 2 OCPU: una previsione alla volta

QUANTILI = ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"]
COVARIATE_ORARIE = {
    "temperatura": "temperature_2m", "umidita": "relative_humidity_2m", "radiazione": "shortwave_radiation",
    "diffusa": "diffuse_radiation", "vento": "wind_speed_10m", "nuvolosita": "cloud_cover",
    "pioggia": "precipitation", "neve": "snowfall",
}
COVARIATE_GIORNALIERE = {
    "temperatura": "t_media", "gradi_giorno": "gg20", "gradi_raffrescamento": "gc24", "umidita": "ur_media",
    "radiazione": "rad_globale_kwh_m2", "diffusa": "rad_diffusa_kwh_m2", "vento": "vento_medio_kmh",
    "nuvolosita": "nuvolosita_media", "pioggia": "pioggia_mm", "neve": "neve_cm",
}
PREDEFINITE = {"breve": ["temperatura", "radiazione", "umidita"],
               "lungo": ["temperatura", "gradi_giorno", "gradi_raffrescamento", "radiazione"]}


def modello():
    global _modello
    with _carica:
        if _modello is None:
            try:   # anche se torch era già stato importato prima di questo modulo
                import torch._dynamo
                torch._dynamo.config.disable = True
            except Exception:  # versioni di torch senza questa opzione
                pass
            from tirex2 import load_model
            log.info("Carico %s su %s", C.MODELLO, C.DISPOSITIVO)
            _modello = load_model(C.MODELLO, device=C.DISPOSITIVO)
    return _modello


# ---------------------------------------------------------------------------------------------- serie utente
def leggi_csv(contenuto: bytes) -> pd.Series:
    """CSV con due colonne: data/ora e valore. Separatore ; o , ; decimali con . o , ."""
    testo = contenuto.decode("utf-8-sig", errors="replace")
    prima = testo.splitlines()[0] if testo else ""
    sep = ";" if prima.count(";") >= prima.count(",") and ";" in prima else ("\t" if "\t" in prima else ",")
    from io import StringIO
    df = pd.read_csv(StringIO(testo), sep=sep, dtype=str)
    if df.shape[1] < 2:
        raise ValueError("Servono almeno due colonne: data/ora e valore")
    if len(df) > C.MAX_RIGHE:
        raise ValueError(f"Troppe righe ({len(df)}): massimo {C.MAX_RIGHE}")
    testi = df.iloc[:, 0].str.strip()
    iso = testi.str.match(r"^\d{4}-\d{2}-\d{2}").mean() > 0.9   # AAAA-MM-GG: niente giorno-prima
    t = pd.to_datetime(testi, dayfirst=not iso, errors="coerce", format="ISO8601" if iso else "mixed")
    v = pd.to_numeric(df.iloc[:, 1].str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                      if df.iloc[:, 1].str.contains(",", regex=False).any() else df.iloc[:, 1], errors="coerce")
    s = pd.Series(v.to_numpy(dtype="float64"), index=t).dropna()
    s = s[~s.index.isna()].sort_index()
    if len(s) < 30:
        raise ValueError("Troppo pochi valori validi (almeno 30)")
    return s


def _a_utc(indice: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if indice.tz is None:
        indice = indice.tz_localize("Europe/Rome", ambiguous="infer", nonexistent="shift_forward")
    return indice.tz_convert("UTC")


def prepara(s: pd.Series, modalita: str, tipo: str) -> pd.Series:
    """Riporta la serie al passo della modalità. tipo: 'energia' (somma) o 'potenza'/'media' (media)."""
    agg = "sum" if tipo == "energia" else "mean"
    if modalita == "breve":
        try:
            idx = _a_utc(pd.DatetimeIndex(s.index))
        except Exception:  # orari ambigui non deducibili: si scartano i doppioni
            s = s[~s.index.duplicated()]
            idx = pd.DatetimeIndex(s.index).tz_localize("Europe/Rome", ambiguous="NaT",
                                                         nonexistent="shift_forward").tz_convert("UTC")
        s = pd.Series(s.to_numpy(), index=idx)
        s = s[~s.index.isna()]
        passo = pd.Series(s.index).diff().median()
        if passo < pd.Timedelta(hours=1):
            s = s.resample("h").agg(agg).where(s.resample("h").count() > 0)
        else:
            s = s.resample("h").mean()
        s.index = s.index.tz_localize(None)  # UTC naive
        return s.iloc[-C.CONTESTO_ORARIO:]
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_convert("Europe/Rome").tz_localize(None)
    s = pd.Series(s.to_numpy(), index=idx)
    passo = pd.Series(s.index).diff().median()
    if passo < pd.Timedelta(days=1):
        s = s.resample("D").agg(agg).where(s.resample("D").count() > 0)
    else:
        s = s.resample("D").mean()
    return s.iloc[-C.CONTESTO_GIORNALIERO:]


# ---------------------------------------------------------------------------------------------- covariate
class MeteoMancante(Exception):
    """Nessun dato meteo del comune sul server (archivio della fase 3 o previsioni non ancora presenti)."""


def _utc(indice) -> pd.DatetimeIndex:
    """Indice orario in UTC anche quando una delle parti concatenate era vuota (indice di tipo object)."""
    return pd.DatetimeIndex(pd.to_datetime(indice, utc=True))


def _meteo_orario(istat: str) -> tuple[pd.DataFrame, pd.Series]:
    st = meteo.storico_orario(istat)
    pr = meteo.previsioni(istat)
    if not len(st) and not len(pr):
        raise MeteoMancante(istat)
    fonte = pd.concat([pd.Series("osservato (ICON)", index=pd.DatetimeIndex(st.time)),
                       pd.Series(np.where(pr.peso_icon2i >= 0.999, "previsione ICON-2I",
                                          np.where(pr.peso_icon2i <= 0.001, "previsione IFS", "miscela ICON-2I/IFS")),
                                 index=pd.DatetimeIndex(pr.time))])
    df = pd.concat([st.set_index("time"), pr.drop(columns="peso_icon2i").set_index("time")])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    fonte = fonte[~fonte.index.duplicated(keep="last")].sort_index()
    df.index = _utc(df.index).tz_localize(None)
    fonte.index = _utc(fonte.index).tz_localize(None)
    return df, fonte


def _meteo_giornaliero(istat: str, fino_a: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series]:
    try:
        st = meteo.storico_giornaliero(istat)
    except FileNotFoundError as e:
        raise MeteoMancante(istat) from e
    if not len(st):
        raise MeteoMancante(istat)
    st = st.set_index("data")
    st.index = pd.DatetimeIndex(st.index)
    fonte = pd.Series("osservato (ERA5 corretto)", index=st.index)
    # ERA5 arriva con ~6 giorni di ritardo: i giorni mancanti si prendono dallo storico ICON
    # (stesso "clima" di riferimento della correzione)
    so = meteo.storico_orario(istat)
    if len(so):
        gi = giornaliero(so).set_index("data")
        gi.index = pd.DatetimeIndex(gi.index)
        gi = gi[gi.index > st.index.max()]
        st = pd.concat([st, gi])
        fonte = pd.concat([fonte, pd.Series("osservato (ICON)", index=gi.index)])
    pr = meteo.previsioni(istat)
    if len(pr):
        g = giornaliero(pr.drop(columns="peso_icon2i")).set_index("data")
        g.index = pd.DatetimeIndex(g.index)
        g = g[g.index > st.index.max()]
        st = pd.concat([st, g])
        fonte = pd.concat([fonte, pd.Series("previsione", index=g.index)])
    # climatologia per i giorni oltre le previsioni: media dello stesso giorno dell'anno (±3 giorni)
    if fino_a > st.index.max():
        futuri = pd.date_range(st.index.max() + pd.Timedelta(days=1), fino_a, freq="D")
        base = st[st.index < st.index.max() - pd.Timedelta(days=15)]
        doy = base.index.dayofyear
        clima = []
        for g in futuri:
            d = np.abs(((doy - g.dayofyear) + 183) % 366 - 183)
            clima.append(base[d <= 3].mean(numeric_only=True))
        cl = pd.DataFrame(clima, index=futuri)
        st = pd.concat([st, cl])
        fonte = pd.concat([fonte, pd.Series("climatologia", index=futuri)])
    return st, fonte


def _covariate(modalita: str, istat: str, indice_tot: pd.DatetimeIndex, scelte: list[str]):
    if modalita == "breve":
        met, fonte = _meteo_orario(istat)
        nomi = {k: COVARIATE_ORARIE[k] for k in scelte if k in COVARIATE_ORARIE}
        cal_idx = indice_tot.tz_localize("UTC").tz_convert("Europe/Rome")
    else:
        met, fonte = _meteo_giornaliero(istat, indice_tot.max())
        nomi = {k: COVARIATE_GIORNALIERE[k] for k in scelte if k in COVARIATE_GIORNALIERE}
        cal_idx = indice_tot
    cov = pd.DataFrame(index=indice_tot)
    for k, col in nomi.items():
        cov[k] = met[col].reindex(indice_tot).astype("float32")
    mancanti = cov.isna().mean()
    cov = cov.interpolate(limit_direction="both").astype("float32")
    cal = calendario.caratteristiche(pd.DatetimeIndex(cal_idx), orario=(modalita == "breve"))
    cal.index = indice_tot
    cov = cov.join(cal)
    return cov, fonte.reindex(indice_tot), mancanti


# ---------------------------------------------------------------------------------------------- previsione
def _esegui(target: pd.Series, cov: pd.DataFrame, orizzonte: int, freq: str) -> pd.DataFrame:
    n = len(target)
    df = cov.iloc[:n].copy()
    df["valore"] = target.to_numpy(dtype="float32")
    df.index.name = "timestamp"
    fut = cov.iloc[n:n + orizzonte].copy()
    fut.index.name = "timestamp"
    with _calcolo:
        out = modello().forecast_df(df.reset_index(), orizzonte, timestamp_column="timestamp", target="valore",
                                    future_covariates=list(cov.columns), future_df=fut.reset_index(),
                                    output_type="pandas")
    out.columns = [str(c) for c in out.columns]
    return out


def prevedi(s: pd.Series, istat: str, modalita: str, orizzonte: int, tipo: str = "energia",
            covariate: list[str] | None = None, verifica: bool = False) -> dict:
    if modalita not in ("breve", "lungo"):
        raise ValueError("modalita deve essere 'breve' o 'lungo'")
    massimo = C.MAX_ORIZZONTE_ORE if modalita == "breve" else C.MAX_ORIZZONTE_GIORNI
    orizzonte = int(min(max(orizzonte, 1), massimo))
    freq = "h" if modalita == "breve" else "D"
    serie = prepara(s, modalita, tipo)
    scelte = covariate if covariate is not None else PREDEFINITE[modalita]
    avvisi = []
    if verifica:
        # verifica: si nascondono gli ultimi `orizzonte` passi e li si prevede con il meteo osservato
        if len(serie) <= orizzonte * 2:
            raise ValueError("Serie troppo corta per la verifica con questo orizzonte")
        reale = serie.iloc[-orizzonte:]
        serie = serie.iloc[:-orizzonte]
    idx_fut = pd.date_range(serie.index.max() + pd.Timedelta(1, unit=freq), periods=orizzonte, freq=freq)
    idx_tot = serie.index.append(idx_fut)
    cov = None
    if scelte:
        try:
            cov, fonte, mancanti = _covariate(modalita, istat, idx_tot, scelte)
            for k, q in mancanti.items():
                if q > 0.2:
                    avvisi.append(f"Meteo '{k}' mancante per il {q:.0%} del periodo: valori interpolati.")
        except MeteoMancante:
            # finché i dati meteo del comune non sono sul server si prevede col solo calendario, dicendolo
            avvisi.append("I dati meteo di questo comune non sono ancora sul server: la previsione usa solo il "
                          "calendario (ora, giorno della settimana, festività), senza meteo. Arriveranno nei "
                          "prossimi giorni.")
    if cov is None:
        cal_idx = idx_tot.tz_localize("UTC").tz_convert("Europe/Rome") if modalita == "breve" else idx_tot
        cov = calendario.caratteristiche(pd.DatetimeIndex(cal_idx), orario=(modalita == "breve"))
        cov.index = idx_tot
        fonte = pd.Series("—", index=idx_tot)
    out = _esegui(serie, cov, orizzonte, freq)
    f_fut = fonte.reindex(idx_fut).fillna("—").tolist()
    if modalita == "breve" and any(x in ("previsione IFS", "miscela ICON-2I/IFS") for x in f_fut):
        avvisi.append("Oltre le 72 ore il meteo proviene dal modello globale ECMWF IFS (0,25°): "
                      "l'incertezza della previsione meteo cresce rapidamente con l'orizzonte.")
    if modalita == "lungo" and "climatologia" in f_fut:
        avvisi.append("Oltre i 15 giorni il meteo non è prevedibile: si usa la climatologia (media degli "
                      "anni precedenti per lo stesso periodo). Il risultato è uno scenario 'anno tipo'.")
    if not verifica and (pd.Timestamp.now(tz="UTC").tz_localize(None) - serie.index.max()) > pd.Timedelta(days=16):
        avvisi.append("I dati caricati terminano più di due settimane fa: la 'previsione' parte dalla fine "
                      "dei dati e usa il meteo osservato, non quello previsto.")

    def _etichette(idx):
        if modalita == "breve":
            return [t.isoformat() for t in idx.tz_localize("UTC").tz_convert("Europe/Rome")]
        return [t.date().isoformat() for t in idx]

    mostra = serie.iloc[-(min(len(serie), orizzonte * 4 if modalita == "lungo" else 24 * 14)):]
    ris = {
        "modalita": modalita, "passo": "ora" if modalita == "breve" else "giorno", "istat": istat,
        "covariate": list(cov.columns),
        "storico": {"t": _etichette(mostra.index), "v": [None if np.isnan(x) else round(float(x), 4) for x in mostra]},
        "previsione": {"t": _etichette(idx_fut),
                       **{q: [round(float(x), 4) for x in out[q]] for q in QUANTILI if q in out},
                       "fonte_meteo": f_fut},
        "avvisi": avvisi,
    }
    if verifica:
        med = out["0.5"].to_numpy()
        r = reale.to_numpy()
        ok = ~np.isnan(r)
        err = med[ok] - r[ok]
        den = np.abs(r[ok]).sum()
        dentro = ((r[ok] >= out["0.1"].to_numpy()[ok]) & (r[ok] <= out["0.9"].to_numpy()[ok])).mean()
        ris["verifica"] = {
            "reale": [None if np.isnan(x) else round(float(x), 4) for x in r],
            "mae": float(np.abs(err).mean()), "wape": float(np.abs(err).sum() / den) if den else None,
            "bias": float(err.mean()), "copertura_80": float(dentro),
        }
    return ris
