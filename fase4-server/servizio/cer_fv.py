"""Fotovoltaico › «CER – Sviluppo impianti FV» (24/11/2026): terreni pubblici candidati vicino a una cabina primaria.

Dati: `DATI/cer_fv/terreni_pubblici_<anno>.sqlite`, costruito sull'host dalla fase 17 (`python -m cer_fv terreni`) con
l'indice degli immobili delle PA (MEF «Patrimonio della PA» + cartografia catastale AdE, CC BY 4.0): solo **terreni in
proprietà** di enti pubblici, con la **probabilità di coltura DOP o certificata** (0-100 e classe) calcolata sui piani
colturali grafici di AGREA. I dati AGREA restano sul server: qui esce solo l'indicatore (decisione di Paolo, 24/11/2026).
Nessun codice fiscale, nessun soggetto cedente.

Rotte (limite per IP «cer_fv»):
  GET /api/cer-fv/info
  GET /api/cer-fv/terreni?lon=…&lat=…&raggio_km=5&min_m2=0&limite=100
      terreni entro il raggio (al massimo 15 km), dal più vicino; `distanza_m` dal punto; al massimo 300
"""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from . import config as C, protezione as P

router = APIRouter(prefix="/api/cer-fv")
RAGGIO_MAX_KM = 15
LIMITE_MAX = 300
CAMPI = ("ref", "lon", "lat", "area_m2", "comune_cod", "foglio", "particella", "comune", "provincia", "regione",
         "ente_chiave", "ente", "settore", "ente_sede", "n_enti", "enti", "tipologie", "utilizzo", "n_beni", "sup_mq",
         "prob_coltura", "classe_coltura", "campagne", "quota_dichiarata")
ATTRIBUZIONE = ("Terreni pubblici: MEF – Patrimonio della PA, dati al 31/12/2023 (CC BY 4.0), su cartografia catastale "
                "dell'Agenzia delle Entrate (CC BY 4.0), elaborati da EuGEnio. Probabilità di coltura DOP o certificata: "
                "indicatore di EuGEnio sui piani colturali grafici di AGREA (dati non ceduti); non è una certificazione.")


def cartella() -> Path:
    return Path(getattr(C, "CARTELLA_CER_FV", None) or (C.DATI / "cer_fv"))


def file_terreni() -> Path | None:
    f = sorted(cartella().glob("terreni_pubblici_*.sqlite"))
    return f[-1] if f else None


def _db() -> sqlite3.Connection:
    f = file_terreni()
    if not f:
        raise HTTPException(503, "Terreni pubblici non ancora disponibili sul server.")
    db = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _dist(lon1, lat1, lon2, lat2) -> float:
    r = math.pi / 180
    a = math.sin((lat2 - lat1) * r / 2) ** 2 + math.cos(lat1 * r) * math.cos(lat2 * r) * math.sin((lon2 - lon1) * r / 2) ** 2
    return 2 * 6371000 * math.asin(min(1.0, math.sqrt(a)))


@router.get("/info")
def info(req: Request):
    if not file_terreni():
        return {"disponibile": False}
    db = _db()
    try:
        out = {k: json.loads(v) for k, v in db.execute("SELECT chiave, valore FROM info")}
    finally:
        db.close()
    return {"disponibile": True, **out, "attribuzione": ATTRIBUZIONE}


@router.get("/terreni")
def terreni(req: Request, lon: float, lat: float, raggio_km: float = 5, min_m2: float = 0, limite: int = 100):
    P.limita(req, "cer_fv")
    if not (-20 < lon < 40 and 30 < lat < 50):
        raise HTTPException(400, "Coordinate fuori dall'Italia.")
    raggio_km = max(0.1, min(float(raggio_km), RAGGIO_MAX_KM))
    limite = max(1, min(int(limite), LIMITE_MAX))
    dlat = raggio_km / 111.32
    dlon = raggio_km / (111.32 * max(0.2, math.cos(lat * math.pi / 180)))
    db = _db()
    try:
        righe = db.execute(f"SELECT {', '.join('t.' + c for c in CAMPI)} FROM terreni_rt r JOIN terreni t ON t.id = r.id "
                           "WHERE r.ovest >= ? AND r.est <= ? AND r.sud >= ? AND r.nord <= ? AND t.area_m2 >= ?",
                           (lon - dlon, lon + dlon, lat - dlat, lat + dlat, float(min_m2))).fetchall()
    finally:
        db.close()
    out = []
    for r in righe:
        d = _dist(lon, lat, r["lon"], r["lat"])
        if d <= raggio_km * 1000:
            out.append({**{c: r[c] for c in CAMPI}, "distanza_m": round(d)})
    out.sort(key=lambda x: x["distanza_m"])
    return {"terreni": out[:limite], "altri": len(out) > limite, "raggio_km": raggio_km, "attribuzione": ATTRIBUZIONE}
