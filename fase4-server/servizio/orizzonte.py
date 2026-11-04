"""Orizzonte lontano dal Copernicus DEM 90 m (fase 10, Fase B, § 4 della proposta: raggio 20–30 km).

Riusa quello che la fase 3 fa già: la quota dei comuni viene dal Copernicus DEM GLO-90 nei file `.om` di Open-Meteo sul
bucket pubblico AWS (`data/copernicus_dem90/static/lat_<grado>.om`, 1200 righe per grado di latitudine, 432.000 colonne
per il giro del mondo, cioè 3″ ≈ 90 m), letti con `meteo_storico.s3.FSBlocchi` (blocchi allineati con cache). Qui si
legge la finestra di ±raggio attorno al punto (al più due file, se la finestra passa un grado intero) e si calcola, per
ogni direzione, l'angolo massimo sotto cui si vede il terreno, con la curvatura della Terra e la rifrazione standard
(k = 0,13). Gli edifici vicini (entro 250 m) li calcola la pagina: l'orizzonte finale di un punto è il massimo dei due.

Rotta:
  GET /api/edifici/orizzonte?lat=…&lon=…&h=…&direzioni=72
      h = altezza del punto sopra il terreno (m, tetto o facciata); risposta: angoli in gradi da nord in senso orario,
      quota del DEM nel punto, raggio, fonte. Risposte copiate su disco (DATI/orizzonte) per punto arrotondato a ~100 m.

Licenza del DEM: Copernicus DEM GLO-90 © DLR e Airbus (licenza Copernicus DEM, uso libero con attribuzione), letto
dai file di Open-Meteo (CC BY 4.0).
"""
from __future__ import annotations

import json
import logging
import math
import threading
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Request

from . import config as C, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/edifici")

FONTE = ("Orizzonte lontano: elaborazione EuGEnio sul Copernicus DEM GLO-90 (© DLR e Airbus, licenza Copernicus DEM), "
         "dai file di Open-Meteo.com (CC BY 4.0)")
RIGHE_GRADO = 1200
COLONNE = 360 * RIGHE_GRADO
R_TERRA = 6371000.0
K_RIFRAZIONE = 0.13
PASSO_M = 90.0
INIZIO_M = 250.0          # entro 250 m lavora la pagina con gli edifici e il terreno vicino


def profilo_da_griglia(z: np.ndarray, lat0: float, lon0: float, passo_gradi: float, lat: float, lon: float,
                       quota: float, raggio_m: float = 25000, direzioni: int = 72,
                       inizio_m: float = INIZIO_M, passo_m: float = PASSO_M) -> tuple[np.ndarray, np.ndarray]:
    """Angoli d'orizzonte (gradi) e distanze del punto più alto (m) per `direzioni` azimut da nord in senso orario.

    z: quote in una griglia regolare lat/lon (righe da sud a nord a partire da lat0, colonne da ovest a est da lon0,
    passo `passo_gradi`); quota: quota assoluta del punto (m). Campionamento lungo il raggio ogni `passo_m`, cella più
    vicina. Abbassamento per la curvatura con la rifrazione: d²·(1 − k) / (2R)."""
    az = np.radians(np.arange(direzioni) * 360.0 / direzioni)
    d = np.arange(inizio_m, raggio_m + passo_m / 2, passo_m)
    dn = np.outer(np.cos(az), d)                       # metri verso nord
    de = np.outer(np.sin(az), d)                       # metri verso est
    m_lat = 111132.954 - 559.822 * math.cos(2 * math.radians(lat))
    m_lon = 111412.84 * math.cos(math.radians(lat))
    la = lat + dn / m_lat
    lo = lon + de / m_lon
    i = np.floor((la - lat0) / passo_gradi).astype(int)
    j = np.floor((lo - lon0) / passo_gradi).astype(int)
    ok = (i >= 0) & (i < z.shape[0]) & (j >= 0) & (j < z.shape[1])
    q = np.full(i.shape, np.nan, dtype="float64")
    q[ok] = z[i[ok], j[ok]]
    q[q < -900] = np.nan                               # mare o vuoti del file
    caduta = d ** 2 * (1 - K_RIFRAZIONE) / (2 * R_TERRA)
    ang = np.degrees(np.arctan2(q - quota - caduta, d))
    ang = np.where(np.isfinite(ang), ang, -90.0)
    k = np.argmax(ang, axis=1)
    massimo = ang[np.arange(direzioni), k]
    return np.clip(massimo, 0.0, 90.0), np.where(massimo > 0, d[k], 0.0)


# ---------------------------------------------------------------------------------------------- lettura del DEM
_fs = None
_lettori: dict[int, object] = {}
_blocco = threading.Lock()


def _lettore(grado: int):
    global _fs
    from omfiles import OmFileReader
    from meteo_storico.s3 import BUCKET, FSBlocchi
    with _blocco:
        if _fs is None:
            _fs = FSBlocchi(max_blocchi=512)
        if grado not in _lettori:
            _lettori[grado] = OmFileReader.from_fsspec(_fs, f"{BUCKET}/data/copernicus_dem90/static/lat_{grado}.om")
        return _lettori[grado]


def finestra_dem(lat: float, lon: float, raggio_m: float) -> tuple[np.ndarray, float, float]:
    """Quote del DEM in ±raggio attorno al punto: (griglia, lat0, lon0) con passo 1/1200 di grado."""
    dlat = raggio_m / 111000.0 + 2 / RIGHE_GRADO
    dlon = raggio_m / (111320.0 * math.cos(math.radians(lat))) + 2 / RIGHE_GRADO
    r0, r1 = math.floor((lat - dlat) * RIGHE_GRADO), math.ceil((lat + dlat) * RIGHE_GRADO)
    c0, c1 = math.floor((lon + 180 - dlon) * RIGHE_GRADO), math.ceil((lon + 180 + dlon) * RIGHE_GRADO)
    if c0 < 0 or c1 > COLONNE:
        raise ValueError("finestra oltre l'antimeridiano")
    parti = []
    for grado in range(math.floor(r0 / RIGHE_GRADO), math.floor((r1 - 1) / RIGHE_GRADO) + 1):
        a = max(r0, grado * RIGHE_GRADO) - grado * RIGHE_GRADO
        b = min(r1, (grado + 1) * RIGHE_GRADO) - grado * RIGHE_GRADO
        parti.append(np.asarray(_lettore(grado)[a:b, c0:c1], dtype="float32"))
    return np.vstack(parti), r0 / RIGHE_GRADO, c0 / RIGHE_GRADO - 180


def quota_dem(z: np.ndarray, lat0: float, lon0: float, lat: float, lon: float) -> float:
    i = int((lat - lat0) * RIGHE_GRADO)
    j = int((lon - lon0) * RIGHE_GRADO)
    return float(z[i, j])


def calcola(lat: float, lon: float, h: float = 0.0, direzioni: int = 72, raggio_m: float | None = None) -> dict:
    raggio_m = raggio_m or C.ORIZZONTE_RAGGIO_KM * 1000
    z, lat0, lon0 = finestra_dem(lat, lon, raggio_m)
    q = quota_dem(z, lat0, lon0, lat, lon)
    if not math.isfinite(q) or q < -900:
        q = 0.0
    ang, dist = profilo_da_griglia(z, lat0, lon0, 1 / RIGHE_GRADO, lat, lon, q + h, raggio_m, direzioni)
    return {"lat": lat, "lon": lon, "h": h, "quota_dem": round(q, 1), "raggio_km": raggio_m / 1000,
            "direzioni": direzioni, "angoli": [round(float(x), 2) for x in ang],
            "distanze_km": [round(float(x) / 1000, 2) for x in dist], "fonte": FONTE,
            "nota": "Angoli in gradi sopra l'orizzonte astronomico, da nord in senso orario; terreno oltre 250 m "
                    "(gli edifici e il terreno vicino li calcola la pagina)."}


def _file_copia(lat: float, lon: float, h: float, direzioni: int) -> Path:
    return C.DATI / "orizzonte" / f"{lat:.3f}_{lon:.3f}_{round(h):d}_{direzioni}_{C.ORIZZONTE_RAGGIO_KM:g}.json"


@router.get("/orizzonte")
def orizzonte(request: Request, lat: float, lon: float, h: float = 0.0, direzioni: int = 72):
    if not (35.0 <= lat <= 47.5 and 6.0 <= lon <= 19.0):
        raise HTTPException(422, "Punto fuori dall'Italia")
    if direzioni not in (36, 72, 120, 360):
        raise HTTPException(422, "direzioni: 36, 72, 120 o 360")
    h = max(0.0, min(h, 300.0))
    lat, lon = round(lat, 3), round(lon, 3)            # ~100 m: l'orizzonte a 25 km non cambia
    p = _file_copia(lat, lon, h, direzioni)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    P.limita(request, "orizzonte")
    try:
        d = calcola(lat, lon, h, direzioni)
    except ImportError:
        raise HTTPException(503, "Lettura del DEM non installata sul server (omfiles)")
    except Exception as e:                              # S3 non raggiungibile o file mancante
        log.warning("Orizzonte %s %s: %s", lat, lon, e)
        raise HTTPException(503, "Il modello del terreno (Copernicus DEM) non è raggiungibile: riprova più tardi")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass
    return d
