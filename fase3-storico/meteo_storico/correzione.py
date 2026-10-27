"""Correzione della serie ERA5 verso il "clima" dei modelli di previsione ICON.

Perché: il modello di previsione dei consumi impara il legame consumo↔meteo sulla serie storica
(ERA5, 5–10 anni) ma in esercizio riceve le previsioni ICON. ERA5 (griglia 9–25 km) e ICON
(2–7 km sull'Italia) hanno scostamenti sistematici – tipicamente temperature più "lisce" in
ERA5 nelle valli e sulla costa, radiazione e vento diversi – che il modello scambierebbe per
cambiamenti di clima. Si stimano quindi, sul periodo in cui esistono entrambe le serie
(da novembre 2022), le differenze sistematiche e le si tolgono da tutta la serie ERA5.

Come, per ogni comune, variabile, mese e ora del giorno (UTC):
  * temperatura, umidità, nuvolosità: **correzione additiva** = media(ICON − ERA5)
    (umidità e nuvolosità poi limitate a 0–100 %);
  * radiazione globale e diffusa, vento: **correzione moltiplicativa** = Σ ICON / Σ ERA5
    (limitata a 0,5–2; radiazione solo nelle ore di luce; diffusa ≤ globale);
  * precipitazione e neve: fattore moltiplicativo **mensile** (non orario: troppo rumoroso),
    limitato a 0,3–3.
Ogni mese usa anche i dati del mese precedente e successivo (pesi 1/4, 1/2, 1/4) per avere
stime stabili con pochi anni di sovrapposizione.

Validazione: stima sui dati fino a 12 mesi fa, verifica sugli ultimi 12 mesi (mai visti),
confrontando l'errore ERA5→ICON prima e dopo la correzione. I risultati vanno sul sito.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import VARIABILI
from .scarica import leggi

log = logging.getLogger(__name__)

ADDITIVE = {"temperature_2m": None, "relative_humidity_2m": (0, 100), "cloud_cover": (0, 100)}
MOLTIPLICATIVE = {"shortwave_radiation": (0.5, 2.0), "diffuse_radiation": (0.5, 2.0), "wind_speed_10m": (0.5, 2.0)}
MENSILI = {"precipitation": (0.3, 3.0), "snowfall": (0.3, 3.0)}
SOGLIA_LUCE = 5.0  # W/m²: sotto questa soglia l'ora è considerata notte
PESI_MESI = {-1: 0.25, 0: 0.5, 1: 0.25}


def _sovrapposizione(era5: pd.DataFrame, icon: pd.DataFrame) -> pd.DataFrame:
    a = era5.set_index("time")
    b = icon.set_index("time")
    j = a.join(b, how="inner", lsuffix="_e", rsuffix="_i")
    j["mese"] = j.index.month
    j["ora"] = j.index.hour
    return j


def _somme(j: pd.DataFrame, v: str, per_ora: bool) -> pd.DataFrame:
    e, i = j[f"{v}_e"], j[f"{v}_i"]
    ok = e.notna() & i.notna()
    if v in MOLTIPLICATIVE and v != "wind_speed_10m":
        ok &= (e > SOGLIA_LUCE) | (i > SOGLIA_LUCE)
    chiavi = ["mese", "ora"] if per_ora else ["mese"]
    g = pd.DataFrame({"e": e[ok], "i": i[ok], "d": (i - e)[ok], "n": 1.0}).join(j.loc[ok, chiavi])
    return g.groupby(chiavi)[["e", "i", "d", "n"]].sum()


def _liscia(s: pd.DataFrame, per_ora: bool) -> pd.DataFrame:
    """Somme pesate su mese−1, mese, mese+1 (circolare)."""
    out = []
    ore = range(24) if per_ora else [None]
    for m in range(1, 13):
        for h in ore:
            acc = np.zeros(4)
            for dm, w in PESI_MESI.items():
                mm = (m - 1 + dm) % 12 + 1
                k = (mm, h) if per_ora else mm
                if k in s.index:
                    acc += w * s.loc[k, ["e", "i", "d", "n"]].to_numpy(dtype=float)
            out.append({"mese": m, "ora": h if per_ora else -1, "e": acc[0], "i": acc[1], "d": acc[2], "n": acc[3]})
    return pd.DataFrame(out)


def stima(j: pd.DataFrame) -> pd.DataFrame:
    """Tabella dei parametri: variabile, tipo, mese, ora (-1 = tutte), valore, n (campioni pesati)."""
    righe = []
    for v in VARIABILI:
        per_ora = v not in MENSILI
        t = _liscia(_somme(j, v, per_ora), per_ora)
        for r in t.itertuples():
            if v in ADDITIVE:
                tipo, val = "add", (r.d / r.n) if r.n >= 10 else 0.0
            else:
                lo, hi = (MOLTIPLICATIVE.get(v) or MENSILI[v])
                tipo = "mul"
                val = float(np.clip(r.i / r.e, lo, hi)) if (r.n >= 10 and r.e > 0) else 1.0
            righe.append({"variabile": v, "tipo": tipo, "mese": r.mese, "ora": r.ora, "valore": float(val),
                          "n": float(r.n)})
    return pd.DataFrame(righe)


def applica(df: pd.DataFrame, par: pd.DataFrame) -> pd.DataFrame:
    """Applica i parametri a una serie oraria (colonna `time` UTC). Restituisce una copia."""
    out = df.copy()
    t = pd.DatetimeIndex(out["time"])
    mese, ora = t.month.to_numpy(), t.hour.to_numpy()
    for v, g in par.groupby("variabile"):
        if v not in out:
            continue
        x = out[v].to_numpy(dtype="float64")
        tab = np.zeros((13, 24)) if g.tipo.iloc[0] == "add" else np.ones((13, 24))
        for r in g.itertuples():
            if r.ora < 0:
                tab[r.mese, :] = r.valore
            else:
                tab[r.mese, r.ora] = r.valore
        c = tab[mese, ora]
        x = x + c if g.tipo.iloc[0] == "add" else x * c
        lim = ADDITIVE.get(v)
        if lim:
            x = np.clip(x, *lim)
        if v in MOLTIPLICATIVE or v in MENSILI:
            x = np.maximum(x, 0)
        out[v] = x.astype("float32")
    if "diffuse_radiation" in out and "shortwave_radiation" in out:
        out["diffuse_radiation"] = np.minimum(out["diffuse_radiation"], out["shortwave_radiation"])
    return out


def _metriche(j: pd.DataFrame, corretto: pd.DataFrame) -> dict:
    m = {}
    jc = corretto.set_index("time").reindex(j.index)
    for v in VARIABILI:
        i = j[f"{v}_i"]
        for nome, e in (("prima", j[f"{v}_e"]), ("dopo", jc[v])):
            ok = e.notna() & i.notna()
            if v in MENSILI:  # confronto sui totali mensili
                d = (i[ok] - e[ok]).groupby([j.index[ok].year, j.index[ok].month]).sum()
            else:
                d = i[ok] - e[ok]
            m.setdefault(v, {})[nome] = {"bias": float(d.mean()), "rmse": float(np.sqrt((d ** 2).mean())),
                                         "n": int(ok.sum())}
    # temperatura media giornaliera e gradi giorno (base 20 °C), le grandezze che contano per l'energia
    for nome, col in (("prima", j["temperature_2m_e"]), ("dopo", jc["temperature_2m"])):
        tl = pd.DataFrame({"e": col, "i": j["temperature_2m_i"]})
        tl.index = tl.index.tz_convert("Europe/Rome")
        g = tl.resample("D").mean().dropna()
        d = g.i - g.e
        gg = (20 - g).clip(lower=0).resample("MS").sum()
        m.setdefault("t_media_giornaliera", {})[nome] = {"bias": float(d.mean()), "rmse": float(np.sqrt((d ** 2).mean()))}
        dg = gg.i - gg.e
        m.setdefault("gradi_giorno_mensili", {})[nome] = {"bias": float(dg.mean()), "rmse": float(np.sqrt((dg ** 2).mean()))}
    return m


def elabora_comune(archivio: Path, istat: str, sorgente: str = "era5", mesi_test: int = 12) -> dict | None:
    """Stima la correzione `sorgente` → ICON seamless (riferimento) per un comune.

    sorgente = "era5": corregge la serie storica e salva orario/era5_corretto/<istat>.parquet;
    sorgente = "icon2i" | "ifs": stima la correzione dei modelli di previsione verso lo stesso
    riferimento (usata dal server sulle previsioni), così storia e previsioni hanno lo stesso "clima".
    """
    sor = leggi(archivio, sorgente, istat)
    icon = leggi(archivio, "icon", istat)
    if sor is None or icon is None:
        return None
    j = _sovrapposizione(sor, icon)
    minimo = 24 * 365 if sorgente == "era5" else 24 * 270
    if len(j) < minimo:
        log.warning("%s %s: sovrapposizione troppo breve (%d ore)", sorgente, istat, len(j))
        return None
    # 1) validazione: stima sul passato, verifica sugli ultimi `mesi_test` mesi
    taglio = j.index.max() - pd.DateOffset(months=mesi_test)
    par_v = stima(j[j.index <= taglio])
    test = j[j.index > taglio]
    metriche = _metriche(test, applica(sor[sor.time > taglio], par_v))
    # 2) stima definitiva su tutto il periodo comune.
    #    Una variabile si corregge solo se la correzione ha ridotto l'errore sui mesi di verifica
    #    (per pioggia e neve, molto variabili, spesso non succede: restano come sono).
    par = stima(j)
    corrette = {v: metriche[v]["dopo"]["rmse"] < metriche[v]["prima"]["rmse"] for v in VARIABILI}
    for v, ok in corrette.items():
        if not ok:
            sel = par.variabile == v
            par.loc[sel, "valore"] = np.where(par.loc[sel, "tipo"] == "add", 0.0, 1.0)
            metriche[v]["dopo"] = dict(metriche[v]["prima"])
    metriche["variabili_corrette"] = corrette
    par.insert(0, "istat", istat)
    par.insert(1, "sorgente", sorgente)
    d = archivio / "correzione" / "parametri" / sorgente
    d.mkdir(parents=True, exist_ok=True)
    par.to_parquet(d / f"{istat}.parquet", index=False)
    if sorgente == "era5":
        out = archivio / "orario" / "era5_corretto"
        out.mkdir(parents=True, exist_ok=True)
        applica(sor, par).to_parquet(out / f"{istat}.parquet", index=False, compression="zstd")
    return {"istat": istat, "sorgente": sorgente, "ore_sovrapposizione": int(len(j)),
            "dal": str(j.index.min().date()), "al": str(j.index.max().date()), "test_dal": str(taglio.date()),
            "metriche": metriche}


def riassumi(risultati: list[dict], archivio: Path, sorgente: str = "era5") -> dict:
    """Mediana tra i comuni delle metriche prima/dopo, per la pagina di metodologia del sito."""
    ris = {"sorgente": sorgente, "riferimento": "icon_seamless", "comuni": len(risultati), "variabili": {}}
    if not risultati:
        return ris
    for v in risultati[0]["metriche"]:
        if v == "variabili_corrette":
            continue
        ris["variabili"][v] = {
            fase: {k: float(np.median([r["metriche"][v][fase][k] for r in risultati]))
                   for k in ("bias", "rmse")}
            for fase in ("prima", "dopo")
        }
    ris["quota_comuni_corretti"] = {
        v: float(np.mean([r["metriche"]["variabili_corrette"][v] for r in risultati])) for v in VARIABILI}
    ris["periodo"] = {"dal": min(r["dal"] for r in risultati), "al": max(r["al"] for r in risultati),
                      "test_dal": min(r["test_dal"] for r in risultati)}
    d = archivio / "correzione"
    d.mkdir(parents=True, exist_ok=True)
    suf = "" if sorgente == "era5" else f"_{sorgente}"
    (d / f"metriche_comuni{suf}.json").write_text(json.dumps(risultati, ensure_ascii=False))
    (d / f"metriche{suf}.json").write_text(json.dumps(ris, ensure_ascii=False, indent=1))
    return ris
