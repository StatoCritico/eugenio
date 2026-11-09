"""Alberi indicativi da OpenStreetMap dove manca il LiDAR (09/11/2026 d, richiesta di Paolo: «gli alberi di Cesena non ci
sono»: le chiome LiDAR della pipeline esistono solo nella fascia costiera della zona di Rimini).

Rotta:
  GET /api/alberi/osm/{i}_{j}.json     alberi della cella di 0,01° (i = floor(lon / 0,01), j = floor(lat / 0,01), come le
                                       celle `lidar/alberi/` della pipeline), nello stesso formato delle celle LiDAR:
                                       {"cella", "campi": ["lon", "lat", "h", "quota", "lato"], "alberi": [[…], …],
                                        "fonte", "licenza", "stima": true, …}

Da OpenStreetMap (ODbL 1.0, © contributori OpenStreetMap, tramite l'API Overpass, stesse istanze del ripiego degli edifici):
  * `natural=tree` (punti): una chioma; altezza da `height` o `est_height` (m), altrimenti **8 m**; diametro della chioma
    da `diameter_crown`, altrimenti **5 m** (tra 2 e 20 m; altezza tra 2 e 40 m);
  * `natural=tree_row` (linee): una chioma ogni **6 m** lungo la linea, stessi valori;
  * boschi e aree `natural=wood` / `landuse=forest`: **non usati** (estensione e altezza troppo incerte per le ombre di un
    edificio; un riempimento piatto non aggiungerebbe nulla di affidabile).
Sono **chiome indicative**: la pagina le dichiara come stima nella nota, in legenda, nell'immagine e nel report, e le usa
anche come ostacoli per le ombre (segnalate come stima). Dove c'è il LiDAR vince il LiDAR: la pagina chiede questa rotta solo
per le celle che non sono nell'elenco `celle.alberi` di `lidar/indice.json`.

Limiti: come le tessere OSM dei contorni (limite per IP «edifici_osm», tetto di Overpass del sito «overpass»); la copia su
disco (CARTELLA_ORTOFOTO/alberi_osm/, EDIFICI_OSM_GIORNI giorni) conta solo nel tetto anti-abuso «edifici_osm_copia».
Una fonte che non risponde dà una cella vuota pulita (200, no-store, `X-Ortofoto-Errore: fonte`, Retry-After).

Open data comunali o regionali con licenza compatibile (censimenti del verde di Cesena, Rimini, Bologna; strati ER di
alberi o chiome): da verificare (DA_FARE); quando ci saranno andranno prima di OpenStreetMap, dopo il LiDAR.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import math
import re
import time

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from . import config as C, ortofoto as O, protezione as P, strati as S

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alberi")

CELLA = 0.01
H_TIPICA, CHIOMA_TIPICA, PASSO_FILARE = 8.0, 5.0, 6.0
LICENZA = "ODbL 1.0"
FONTE = "© contributori OpenStreetMap (ODbL 1.0), tramite l'API Overpass: chiome indicative, altezza stimata"
ITALIA = (6.6, 35.4, 18.6, 47.1)
guasti = O.Guasti()


def query(i: int, j: int) -> str:
    s, w, n, e = j * CELLA, i * CELLA, (j + 1) * CELLA, (i + 1) * CELLA
    b = f"({s:.4f},{w:.4f},{n:.4f},{e:.4f})"
    return f'[out:json][timeout:25];(node["natural"="tree"]{b};way["natural"="tree_row"]{b};);out tags geom;'


def _numero(v, minimo: float, massimo: float) -> float | None:
    m = re.match(r"\s*([0-9]+(?:[.,][0-9]+)?)", str(v or ""))
    if not m:
        return None
    x = float(m.group(1).replace(",", "."))
    return min(massimo, max(minimo, x))


def altezza_e_chioma(tag: dict) -> tuple[float, float, bool]:
    """(altezza, diametro della chioma, stimati?) dai tag OSM."""
    h = _numero(tag.get("height"), 2, 40) or _numero(tag.get("est_height"), 2, 40)
    d = _numero(tag.get("diameter_crown"), 2, 20)
    return (h or H_TIPICA), (d or CHIOMA_TIPICA), not (h and d)


def alberi_da_overpass(d: dict, i: int, j: int) -> list[list[float]]:
    """[lon, lat, h, quota (null), lato della chioma] per ogni albero, solo dentro la cella."""
    out = []
    dentro = lambda lo, la: i * CELLA <= lo < (i + 1) * CELLA and j * CELLA <= la < (j + 1) * CELLA
    for el in d.get("elements", [])[:20000]:
        tag = el.get("tags") or {}
        h, chioma, _ = altezza_e_chioma(tag)
        if el.get("type") == "node" and tag.get("natural") == "tree" and "lon" in el:
            if dentro(el["lon"], el["lat"]):
                out.append([round(el["lon"], 7), round(el["lat"], 7), round(h, 1), None, round(chioma, 1)])
        elif el.get("type") == "way" and tag.get("natural") == "tree_row":
            g = [(p["lon"], p["lat"]) for p in el.get("geometry") or [] if "lon" in p]
            for (a0, b0), (a1, b1) in zip(g, g[1:]):
                kx = 111320 * math.cos(math.radians((b0 + b1) / 2))
                L = math.hypot((a1 - a0) * kx, (b1 - b0) * 110574)
                n = max(1, int(L // PASSO_FILARE))
                for k in range(n):
                    t = (k + 0.5) / n
                    lo, la = a0 + t * (a1 - a0), b0 + t * (b1 - b0)
                    if dentro(lo, la):
                        out.append([round(lo, 7), round(la, 7), round(h, 1), None, round(chioma, 1)])
    return out


def _copia(nome: str):
    return C.CARTELLA_ORTOFOTO / "alberi_osm" / f"{nome}.json"


def leggi_copia(nome: str) -> dict | None:
    f = _copia(nome)
    try:
        if f.exists() and time.time() - f.stat().st_mtime < C.EDIFICI_OSM_GIORNI * 86400:
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return None


def _vuota(motivo: str, riprova: float) -> Response:
    return Response(json.dumps({"alberi": [], "stima": True}), media_type="application/json", headers={
        "Cache-Control": "no-store", "X-Ortofoto-Errore": motivo, "Retry-After": str(max(1, int(math.ceil(riprova)))),
        "Access-Control-Expose-Headers": "X-Ortofoto-Errore, Retry-After"})


@router.get("/osm/{nome}.json")
async def alberi_osm(request: Request, nome: str):
    if not C.EDIFICI_OSM:
        raise HTTPException(404, "Il ripiego OpenStreetMap è spento su questo server.")
    m = re.fullmatch(r"(-?\d{1,5})_(-?\d{1,5})", nome)
    if not m:
        raise HTTPException(404, "Cella non valida")
    i, j = int(m.group(1)), int(m.group(2))
    if not (ITALIA[0] <= (i + 0.5) * CELLA <= ITALIA[2] and ITALIA[1] <= (j + 0.5) * CELLA <= ITALIA[3]):
        raise HTTPException(404, "Cella fuori dall'Italia")
    d = leggi_copia(nome)
    if d is not None:
        P.limita(request, "edifici_osm_copia")
    else:
        if (resta := guasti.ferma_per("overpass")) > 0:
            return _vuota("ferma", resta)
        P.limita(request, "edifici_osm")
        if not P.tetto_globale("overpass", C.EDIFICI_OSM_TETTO_ORA):
            return _vuota("ferma", 600)
        t0 = time.monotonic()
        try:
            r = await asyncio.wait_for(asyncio.to_thread(S.chiedi_overpass, S.istanze_overpass(), query(i, j), "json",
                                                         C.ORTOFOTO_TIMEOUT_S, "Alberi OSM"), timeout=C.ORTOFOTO_TIMEOUT_S + 6)
            if r.status_code != 200:
                raise httpx.HTTPError(f"risposta {r.status_code}")
            alberi = alberi_da_overpass(r.json(), i, j)
        except (httpx.HTTPError, asyncio.TimeoutError, OSError, ValueError) as e:
            log.warning("Alberi OSM %s: Overpass non risponde (%s dopo %.1f s)", nome, type(e).__name__, time.monotonic() - t0)
            return _vuota("fonte", guasti.errore("overpass") or 60)
        guasti.buona("overpass")
        d = {"cella": nome, "crs": "EPSG:4326", "campi": ["lon", "lat", "h", "quota", "lato"], "alberi": alberi,
             "fonte": FONTE, "licenza": LICENZA, "scheda": "https://www.openstreetmap.org/copyright", "stima": True,
             "data": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            f = _copia(nome)
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")
            tmp.replace(f)
        except OSError as e:
            log.warning("Alberi OSM: copia non scritta (%s)", e)
    return Response(json.dumps(d, separators=(",", ":")), media_type="application/json",
                    headers={"Cache-Control": "public, max-age=86400", "X-Alberi-Fonte": "osm"})
