#!/usr/bin/env python3
"""Verifiche sul campione (o su qualunque cache):

  1. lettura S3 + correzione di quota  vs  API storica Open-Meteo (stesso punto, stesso modello);
  2. indicatori di calcola.py          vs  fase3-storico/meteo_storico/legge10.py sulle stesse ultime 10 stagioni;
  3. GG calcolati                      vs  DPR 412/93 (ordine di grandezza, zona).

  python verifica.py --cache cache_campione --uscita campione [--api ISTAT,ISTAT] [--anni 2000,2020]

Il punto 1 usa poche chiamate dell'API gratuita (~25 per comune e per anno, peso = giorni/14 × variabili/10).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
import indicatori as ind  # noqa: E402
from calcola import DPR_PREDEFINITO, carica_anno, indice_celle  # noqa: E402

LEGGE10 = Path("/home/claude/storici/fase3-storico")


def serie_comune(cache: Path, comuni: pd.DataFrame, istat: str, anni, quota=None) -> pd.DataFrame:
    """Serie giornaliera di un comune: T e pv da ERA5-Land corretti di quota, radiazione e vento da ERA5."""
    c = comuni.index[comuni.istat == istat][0]
    iL, nL = indice_celle(cache, "era5_land", comuni)
    iE, nE = indice_celle(cache, "era5", comuni)
    r = comuni.loc[c]
    dzL = ind.correzione_quota(r.era5_land_quota, r.quota_m if quota is None else quota)
    parti = []
    for a in anni:
        L = carica_anno(cache, "era5_land", a, nL, ["t_media", "t_min", "t_max", "pv"])
        E = carica_anno(cache, "era5", a, nE, ["ghi_kwh", "dif_kwh", "vento", "t_media"])
        if L is None or E is None:
            continue
        d = pd.DataFrame({"data": pd.date_range(f"{a}-01-01", periods=L["t_media"].shape[1])})
        for v in ("t_media", "t_min", "t_max"):
            d[v] = L[v][iL[c]] + dzL
        d["pv"] = L["pv"][iL[c]]
        d["ghi_kwh"] = E["ghi_kwh"][iE[c]]
        d["dif_kwh"] = E["dif_kwh"][iE[c]]
        d["vento_ms"] = E["vento"][iE[c]]
        parti.append(d)
    return pd.concat(parti, ignore_index=True).dropna(subset=["t_media"])


def confronto_api(cache, comuni, istat, anno):
    r = comuni[comuni.istat == istat].iloc[0]
    par = {"latitude": r.lat, "longitude": r.lon, "start_date": f"{anno}-01-01", "end_date": f"{anno}-12-31",
           "daily": "temperature_2m_mean,temperature_2m_min,temperature_2m_max", "timezone": "Etc/GMT-1",
           "models": "era5_land"}
    import time
    for t in range(6):
        try:
            j = requests.get("https://archive-api.open-meteo.com/v1/archive", params=par, timeout=120).json()
            break
        except requests.RequestException:
            time.sleep(5 * (t + 1))
    out_cella = (j["latitude"], j["longitude"])
    api = pd.DataFrame(j["daily"]).rename(columns={"time": "data"})
    api["data"] = pd.to_datetime(api.data)
    mia = serie_comune(cache, comuni.reset_index(drop=True), istat, [anno])
    m = api.merge(mia, on="data")
    out = {"istat": istat, "nome": r.nome, "anno": anno, "quota_api": j.get("elevation"), "quota_mia": r.quota_m,
           "cella_api": out_cella, "cella_mia": (round(r.era5_land_i * 0.1 - 90, 2), round(r.era5_land_j * 0.1 - 180, 2)),
           "giorni": len(m)}
    for a, b in (("temperature_2m_mean", "t_media"), ("temperature_2m_min", "t_min"), ("temperature_2m_max", "t_max")):
        d = m[b] - m[a]
        out[f"{b}_bias"] = round(float(d.mean()), 3)
        out[f"{b}_mae"] = round(float(d.abs().mean()), 3)
    gg_api = (20 - m.temperature_2m_mean).clip(lower=0).sum()
    gg_mio = (20 - m.t_media).clip(lower=0).sum()
    out["gg_anno_api"], out["gg_anno_mio"] = round(float(gg_api)), round(float(gg_mio))
    return out


def confronto_legge10(cache, comuni, istat, sintesi: dict, dpr: dict):
    sys.path.insert(0, str(LEGGE10))
    from meteo_storico import legge10
    ultimo = int(sintesi["stagioni"]["da"]) + len(sintesi["stagioni"]["gg_zona"]) - 1
    g = serie_comune(cache, comuni.reset_index(drop=True), istat, range(ultimo - 11, ultimo + 2),
                     quota=sintesi.get("quota_correzione_m"))
    es = ind.pressione_vapore_da_td(g.t_media)          # legge10 vuole l'umidità relativa
    g["ur_media"] = 100 * g.pv / es
    g["rad_globale_kwh_m2"], g["rad_diffusa_kwh_m2"], g["vento_medio_kmh"] = g.ghi_kwh, g.dif_kwh, g.vento_ms * 3.6
    uff = None
    if istat in dpr:
        uff = {"gg": dpr[istat][0], "zona": dpr[istat][1]}
    l10 = legge10.calcola(g, anni=10, ufficiali=uff, fino_a=f"{ultimo + 1}-06-30")
    gz = [v for v in sintesi["stagioni"]["gg_zona"][-10:]]
    return {"istat": istat, "nome": sintesi["nome"], "stagioni_l10": f"{l10['stagioni'][0]}–{l10['stagioni'][-1]}",
            "gg_l10": l10["gradi_giorno"]["gg_periodo_zona"], "gg_mio": round(float(np.mean(gz))),
            "gg_anno_l10": l10["gradi_giorno"]["gg_anno_intero"],
            "zona_l10": l10["gradi_giorno"]["zona_risultante"], "zona_mia_10": ind.zona_coerente(
                np.array([l10["gradi_giorno"]["gg_per_periodo_di_ogni_zona"][z] for z in ind.NOMI_ZONE])),
            "tend_l10": l10["gradi_giorno"]["tendenza_gg_per_decennio"],
            "theta_inv_l10": l10["temperatura_progetto"]["invernale"],
            "theta_inv_mio_10anni": sintesi["progetto"]["inv"][-1] if sintesi["progetto"]["inv"] else None,
            "theta_est_l10": l10["temperatura_progetto"]["estiva"],
            "theta_est_mio_10anni": sintesi["progetto"]["est"][-1] if sintesi["progetto"]["est"] else None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache", default="cache_campione")
    p.add_argument("--uscita", default="campione")
    p.add_argument("--api", default="037006,076063,001263")
    p.add_argument("--anni", default="2000,2020")
    p.add_argument("--dpr", default=str(DPR_PREDEFINITO))
    a = p.parse_args()
    cache, usc = QUI / a.cache, QUI / a.uscita
    comuni = pd.read_parquet(QUI / "dati" / "comuni.parquet")
    dpr = json.loads(Path(a.dpr).read_text(encoding="utf-8"))["comuni"] if Path(a.dpr).exists() else {}
    sint = pd.read_csv(usc / "clima_sintesi.csv", sep=";", decimal=",", dtype={"codice_istat": str},
                       comment="#")   # righe finali con fonti e licenza
    comuni = comuni[comuni.istat.isin(sint.codice_istat)].reset_index(drop=True)
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print("\n== 3. GG calcolati e DPR 412/93")
    print(sint[["codice_istat", "comune", "quota_punto_m", "zona_dpr", "gg_dpr", "gg_1991_2020", "gg_ultime_30",
                "gg_ultime_10", "diff_ultime_10_pct", "zona_da_gg_ultime_10", "tendenza_gg_decennio",
                "theta_inv_1991_2020", "theta_est_1991_2020"]].to_string(index=False))
    print("\n== 2. confronto con legge10.py (ultime 10 stagioni)")
    righe = []
    for istat in sint.codice_istat:
        rr = comuni.loc[comuni.istat == istat, "regione_cod"].iloc[0]
        s = json.loads((usc / "clima" / rr / f"{istat}.json").read_text(encoding="utf-8"))
        if s.get("solo_era5"):
            continue
        righe.append(confronto_legge10(cache, comuni, istat, s, dpr))
    print(pd.DataFrame(righe).to_string(index=False))
    print("\n== 1. lettura S3 + correzione di quota vs API Open-Meteo (era5_land, stesso punto)")
    righe = [confronto_api(cache, comuni, i, int(y)) for i in a.api.split(",") for y in a.anni.split(",")]
    print(pd.DataFrame(righe).to_string(index=False))


if __name__ == "__main__":
    main()
