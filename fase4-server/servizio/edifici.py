"""Clima per le analisi degli edifici (fase 10, Fase A): firma energetica e producibilità fotovoltaica.

Rotte (limiti delle rotte dei dati, nessun dato di mercato):
  GET /api/edifici/gradi-giorno/{istat}?dal=AAAA-MM&al=AAAA-MM
      gradi giorno mensili reali (base 20 °C e 24 °C estivi) e temperatura media del comune, dall'archivio meteo
      giornaliero (ERA5 corretto verso ICON, fase 3). **Non** usa i gradi giorno Arpae della fase 2 (personali).
  GET /api/edifici/clima-orario/{istat}?anno=AAAA
      anno orario (UTC) di radiazione globale e diffusa orizzontale, temperatura e vento dall'archivio orario del comune
      (ICON storico, fase 3), per la producibilità FV nel browser. Se l'anno chiesto non c'è si usa l'ultimo completo.
Entrambe rispondono 503 con un messaggio chiaro finché l'archivio meteo non è sul server (come la Legge 10).
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from . import meteo, protezione as P

router = APIRouter(prefix="/api/edifici")
FONTE = "Elaborazione EuGEnio su dati Open-Meteo.com (ERA5/Copernicus corretto verso ICON), CC BY 4.0"
MANCA = "i dati meteo del comune non sono ancora sul server: arriveranno nei prossimi giorni"


def _comune(istat: str) -> str:
    try:
        cm = meteo.comuni()
    except FileNotFoundError:
        raise HTTPException(503, MANCA)
    if istat not in set(cm.istat):
        raise HTTPException(404, f"Comune {istat} non disponibile")
    return str(cm.set_index("istat").at[istat, "nome"])


def gradi_giorno_mensili(g: pd.DataFrame, dal: str | None = None, al: str | None = None) -> list[dict]:
    """Dal giornaliero (data, t_media, gg20, gc24) ai mesi: somma dei gradi giorno, media della temperatura, giorni."""
    if g.empty:
        return []
    d = g.copy()
    d["mese"] = pd.to_datetime(d["data"]).dt.strftime("%Y-%m")
    if dal:
        d = d[d.mese >= dal]
    if al:
        d = d[d.mese <= al]
    m = d.groupby("mese").agg(gg20=("gg20", "sum"), gc24=("gc24", "sum"), t_media=("t_media", "mean"),
                              giorni=("t_media", "count"))
    return [{"mese": k, "gg20": round(float(r.gg20), 1), "gc24": round(float(r.gc24), 1),
             "t_media": round(float(r.t_media), 2), "giorni": int(r.giorni)} for k, r in m.iterrows()]


def anno_orario(o: pd.DataFrame, anno: int | None) -> tuple[int, pd.DataFrame]:
    """Righe orarie dell'anno chiesto (o dell'ultimo con almeno 8.000 ore)."""
    if o.empty:
        raise ValueError("vuoto")
    t = pd.DatetimeIndex(pd.to_datetime(o["time"], utc=True))
    o = o.assign(_anno=t.year, time=t)
    conta = o.groupby("_anno").size()
    completi = sorted(a for a, n in conta.items() if n >= 8000)
    if not completi:
        raise ValueError("nessun anno completo")
    scelto = anno if anno in completi else completi[-1]
    return int(scelto), o[o._anno == scelto].drop(columns="_anno").sort_values("time")


@router.get("/gradi-giorno/{istat}")
def gradi_giorno(request: Request, istat: str, dal: str | None = None, al: str | None = None):
    P.limita(request, "dati")
    nome = _comune(istat)
    try:
        g = meteo.storico_giornaliero(istat)
    except FileNotFoundError:
        raise HTTPException(503, MANCA)
    return {"istat": istat, "comune": nome, "mesi": gradi_giorno_mensili(g, dal, al), "fonte": FONTE,
            "nota": "Gradi giorno dal clima reale del comune (base 20 °C; estivi base 24 °C): non sono i valori di legge."}


@router.get("/clima-orario/{istat}")
def clima_orario(request: Request, istat: str, anno: int | None = None):
    P.limita(request, "dati")
    nome = _comune(istat)
    o = meteo.storico_orario(istat)
    try:
        scelto, d = anno_orario(o, anno)
    except ValueError:
        raise HTTPException(503, MANCA)
    num = lambda c: [None if pd.isna(x) else round(float(x), 1) for x in d[c]] if c in d else []
    return {"istat": istat, "comune": nome, "anno": scelto, "inizio": d.time.iloc[0].isoformat(), "passo_ore": 1,
            "ghi": num("shortwave_radiation"), "dhi": num("diffuse_radiation"), "t": num("temperature_2m"),
            "vento": num("wind_speed_10m"), "fonte": FONTE,
            "nota": "W/m², media dell'ora precedente (UTC); temperatura in °C, vento in km/h a 10 m."}
