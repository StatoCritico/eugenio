"""Confronto con PVGIS chiamato dal server (fase 10, Fase B, § 5 della proposta).

PVGIS (JRC, Commissione europea) non risponde alle chiamate dal browser (niente CORS): la pagina manda qui le aree FV
con l'orizzonte di ogni area (edifici vicini + terreno lontano) e il server chiama l'API non interattiva `PVcalc` con
`userhorizon`, una chiamata per area.

Rotta:
  POST /api/edifici/pvgis   {lat, lon, aree: [{id, kwp, inclinazione, orientamento (gradi da nord, 180 = sud),
                             perdite (%), orizzonte: [gradi, da nord in senso orario, passo uguale]}]}
      → per area: producibilità annua e mensile di PVGIS con il nostro orizzonte e senza (solo l'orizzonte del DEM di
        PVGIS), irradiazione sul piano, banca dati della radiazione e anni usati.

Regole:
  * ritmo verso PVGIS per tutto il sito sotto le **30 chiamate al secondo** dichiarate dal JRC (PVGIS_AL_SECONDO = 20,
    attesa breve e poi 503); limite per indirizzo «pvgis» (PVGIS_ORA confronti all'ora, un confronto = una richiesta);
  * risposte copiate su disco (DATI/pvgis/<impronta>.json) per PVGIS_CACHE_GIORNI giorni: stessa area, nessuna chiamata;
  * massimo 12 aree per richiesta; l'orizzonte si riduce a 36 direzioni (il massimo delle due vicine, prudente);
  * fonte e licenza nella risposta: PVGIS © Unione europea, riuso con citazione (decisione 2011/833/UE).
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time

import httpx
from fastapi import APIRouter, Body, HTTPException, Request

from . import config as C, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/edifici")

FONTE = ("PVGIS © Unione europea, Joint Research Centre (JRC) – Photovoltaic Geographical Information System, "
         "API non interattiva PVcalc; riuso con citazione (decisione 2011/833/UE)")
URL_SCHEDA = "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en"
MAX_AREE = 12


class RitmoGlobale:
    """Al massimo n chiamate al secondo per tutto il sito (finestra mobile di un secondo)."""

    def __init__(self):
        self._b = threading.Lock()
        self._t: list[float] = []

    def attendi(self, n: float, massimo_s: float = 5.0) -> bool:
        fine = time.monotonic() + massimo_s
        while True:
            with self._b:
                ora = time.monotonic()
                self._t = [x for x in self._t if ora - x < 1.0]
                if len(self._t) < max(1, int(n)):
                    self._t.append(ora)
                    return True
                aspetta = 1.0 - (ora - self._t[0])
            if time.monotonic() + aspetta > fine:
                return False
            time.sleep(max(0.01, aspetta))

    def svuota(self):
        with self._b:
            self._t.clear()


ritmo = RitmoGlobale()


def riduci_orizzonte(angoli: list[float], n: int = 36) -> list[float]:
    """Da m direzioni (m multiplo di n) a n, tenendo il massimo del gruppo centrato su ogni direzione."""
    a = [max(0.0, min(90.0, float(x))) for x in angoli if x is not None]
    m = len(a)
    if m == 0:
        return []
    if m <= n or m % n:
        return [round(x, 1) for x in a]
    k = m // n
    return [round(max(a[(i * k + j - k // 2) % m] for j in range(k)), 1) for i in range(n)]


def parametri(lat: float, lon: float, area: dict, con_orizzonte: bool) -> dict:
    """Parametri di PVcalc. aspect di PVGIS: 0 = sud, 90 = ovest, −90 = est (da noi 180 = sud, gradi da nord)."""
    orient = float(area.get("orientamento", 180)) % 360
    aspect = ((orient - 180 + 180) % 360) - 180
    p = {"lat": round(lat, 5), "lon": round(lon, 5), "peakpower": round(float(area["kwp"]), 3),
         "loss": round(float(area.get("perdite", 14)), 1), "angle": round(float(area.get("inclinazione", 0)), 1),
         "aspect": round(aspect, 1), "mountingplace": "building" if area.get("montaggio") == "aderente" else "free",
         "outputformat": "json", "usehorizon": 1}
    if con_orizzonte:
        o = riduci_orizzonte(area.get("orizzonte") or [])
        if o:
            p["userhorizon"] = ",".join(f"{x:g}" for x in o)
    return p


def _impronta(p: dict) -> str:
    return hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:32]


def _chiama(p: dict) -> dict:
    with httpx.Client(timeout=40, headers={"User-Agent": "EuGEnio/1.0 (+https://eugenio.statocritico.it)"}) as c:
        r = c.get(C.PVGIS_URL, params=p)
    if r.status_code != 200:
        try:
            msg = r.json().get("message", "")
        except ValueError:
            msg = r.text[:200]
        raise RuntimeError(f"PVGIS {r.status_code}: {msg}")
    return r.json()


def pvcalc(p: dict) -> dict:
    """Risposta di PVcalc (dalla copia su disco se c'è)."""
    f = C.DATI / "pvgis" / f"{_impronta(p)}.json"
    try:
        if f.exists() and time.time() - f.stat().st_mtime < C.PVGIS_CACHE_GIORNI * 86400:
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if not ritmo.attendi(C.PVGIS_AL_SECONDO):
        raise HTTPException(503, "PVGIS è molto richiesto in questo momento: riprova tra poco",
                            headers={"Retry-After": "5"})
    d = _chiama(p)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass
    return d


def riassunto(d: dict) -> dict:
    o = d.get("outputs", {})
    tot = (o.get("totals") or {}).get("fixed", {})
    mesi = [m.get("E_m") for m in (o.get("monthly") or {}).get("fixed", [])]
    md = (d.get("inputs") or {}).get("meteo_data", {})
    return {"kwh_anno": tot.get("E_y"), "kwh_mensili": mesi, "irradiazione_piano": tot.get("H(i)_y"),
            "perdite_totali": tot.get("l_total"), "variabilita_anno": tot.get("SD_y"),
            "banca_dati": md.get("radiation_db"), "anni": [md.get("year_min"), md.get("year_max")],
            "orizzonte": md.get("horizon_db")}


@router.post("/pvgis")
def confronto(request: Request, corpo: dict = Body(...)):
    try:
        lat, lon = float(corpo["lat"]), float(corpo["lon"])
        aree = list(corpo.get("aree") or [])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(422, "Servono lat, lon e aree")
    if not (35.0 <= lat <= 47.5 and 6.0 <= lon <= 19.0):
        raise HTTPException(422, "Punto fuori dall'Italia")
    if not aree or len(aree) > MAX_AREE:
        raise HTTPException(422, f"Da 1 a {MAX_AREE} aree per confronto")
    for a in aree:
        try:
            if not (0 < float(a["kwp"]) <= 1000 and 0 <= float(a.get("inclinazione", 0)) <= 90):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise HTTPException(422, "Ogni area vuole kwp (0–1000) e inclinazione (0–90°)")
    P.limita(request, "pvgis")
    out = []
    for a in aree:
        try:
            con = riassunto(pvcalc(parametri(lat, lon, a, True)))
            senza = riassunto(pvcalc(parametri(lat, lon, a, False)))
        except RuntimeError as e:
            log.warning("PVGIS: %s", e)
            raise HTTPException(502, f"PVGIS ha risposto con un errore: {str(e)[:200]}")
        except httpx.HTTPError as e:
            log.warning("PVGIS non raggiungibile: %s", e)
            raise HTTPException(502, "PVGIS non risponde: riprova più tardi")
        out.append({"id": str(a.get("id", ""))[:40], "con_orizzonte": con, "senza_orizzonte_utente": senza})
    return {"aree": out, "fonte": FONTE, "url": URL_SCHEDA,
            "nota": "Con orizzonte: PVGIS con il profilo calcolato da EuGEnio (edifici entro 250 m e terreno fino a "
                    f"{C.ORIZZONTE_RAGGIO_KM:g} km). Senza: PVGIS con il solo orizzonte del suo modello del terreno. "
                    "PVGIS usa i propri dati di radiazione (anni indicati), non il clima orario di EuGEnio."}
