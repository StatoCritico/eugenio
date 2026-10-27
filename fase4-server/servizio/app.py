"""API HTTP (FastAPI). Tutte le rotte sono sotto /api; il sito statico è servito da Caddy.

I dati caricati dagli utenti sono elaborati in memoria e non vengono salvati.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque

import httpx
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from . import config as C, meteo, modello, report, storici
from .report_servizi import TIPI as TIPI_REPORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")
app = FastAPI(title="Previsioni energetiche – API", version="1.1.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json")
if C.ORIGINI_CORS:
    app.add_middleware(CORSMiddleware, allow_origins=C.ORIGINI_CORS, allow_methods=["GET", "POST"])

app.include_router(storici.router)   # pagina "Dati storici": /api/storici/...
# limite semplice per indirizzo IP: previsioni (pesanti), geocodifica (quota Zornade) e patrimonio, che si
# conta in edifici e non in richieste: il sito invia i file grandi a blocchi (il tunnel Cloudflare chiude le
# richieste che durano più di 100 secondi)
_storia: dict[tuple[str, str], deque] = defaultdict(deque)
LIMITI = {"previsione": (20, 3600), "zornade": (120, 3600), "patrimonio": (2000, 3600), "report": (60, 3600)}


def _limita(req: Request, tipo: str, peso: int = 1) -> None:
    ip = req.headers.get("x-forwarded-for", req.client.host if req.client else "?").split(",")[0].strip()
    n, finestra = LIMITI[tipo]
    q = _storia[(ip, tipo)]
    ora = time.time()
    while q and ora - q[0] > finestra:
        q.popleft()
    if len(q) + peso > n:
        unita = "edifici" if tipo == "patrimonio" else "richieste"
        raise HTTPException(429, f"Troppe richieste: massimo {n} {unita} all'ora")
    q.extend([ora] * peso)


def _istat_valido(istat: str) -> None:
    if istat not in set(meteo.comuni().istat):
        raise HTTPException(404, f"Comune {istat} non disponibile")


@app.get("/api/salute")
def salute():
    p = C.DATI / "previsioni" / "ultima.json"
    return {"stato": "ok", "previsioni": json.loads(p.read_text()) if p.exists() else None,
            "modello_caricato": modello._modello is not None}


@app.get("/api/comuni")
def comuni():
    cm = meteo.comuni()
    return cm[["istat", "nome", "belfiore", "provincia", "lat", "lon", "svg_x", "svg_y"]].to_dict(orient="records")


@app.get("/api/mappa")
def mappa(giorni: int = 7):
    """Gradi giorno (base 20 °C) e temperatura media previsti nei prossimi `giorni` per ogni comune."""
    p = C.DATI / "previsioni" / "ultima.parquet"
    if not p.exists():
        return {"comuni": {}}
    d = meteo._previsioni(p.stat().st_mtime)
    inizio = pd.Timestamp.now(tz="UTC").floor("h")
    d = d[(d.time >= inizio) & (d.time < inizio + pd.Timedelta(days=max(1, min(giorni, 15))))]
    g = d.groupby("istat").temperature_2m.agg(["mean", "count"])
    gg = d.assign(gg=(20 - d.temperature_2m).clip(lower=0) / 24).groupby("istat").gg.sum()
    return {"giorni": giorni, "comuni": {i: {"t": round(float(r["mean"]), 1), "gg": round(float(gg[i]), 1)}
                                          for i, r in g.iterrows()}}


@app.get("/api/metodologia")
def metodologia():
    out = {}
    for nome in ("metriche", "metriche_icon2i", "metriche_ifs"):
        p = C.DATI / f"{nome}.json"
        if p.exists():
            out[nome] = json.loads(p.read_text())
    return out


@app.get("/api/meteo/{istat}")
def meteo_comune(istat: str, modalita: str = "breve", giorni: int = 14):
    _istat_valido(istat)
    giorni = max(1, min(giorni, 3650))
    if modalita == "breve":
        st = meteo.storico_orario(istat)
        st = st[st.time >= st.time.max() - pd.Timedelta(days=min(giorni, 90))]
        pr = meteo.previsioni(istat)
        conv = lambda d: {"t": [t.isoformat() for t in pd.DatetimeIndex(d.time).tz_convert("Europe/Rome")],
                          **{c: [None if pd.isna(x) else round(float(x), 2) for x in d[c]]
                             for c in d.columns if c != "time"}}
        return {"storico": conv(st), "previsione": conv(pr)}
    st = meteo.storico_giornaliero(istat).tail(giorni)
    return {"storico": {"t": [str(x) for x in st.data],
                        **{c: [None if pd.isna(x) else round(float(x), 2) for x in st[c]]
                           for c in st.columns if c != "data"}}}


@app.post("/api/previsione")
async def previsione(request: Request, file: UploadFile = File(...), istat: str = Form(...),
                     modalita: str = Form("breve"), orizzonte: int = Form(72), tipo: str = Form("energia"),
                     covariate: str | None = Form(None), verifica: bool = Form(False)):
    _limita(request, "previsione")
    _istat_valido(istat)
    dati = await file.read(int(C.MAX_UPLOAD_MB * 1024 * 1024) + 1)
    if len(dati) > C.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File troppo grande (massimo {C.MAX_UPLOAD_MB:g} MB)")
    try:
        serie = modello.leggi_csv(dati)
        scelte = None if covariate is None else [c for c in covariate.split(",") if c]
        return await run_in_threadpool(modello.prevedi, serie, istat, modalita, orizzonte, tipo, scelte, verifica)
    except ValueError as e:
        raise HTTPException(422, str(e))
    finally:
        del dati


# ---------------------------------------------------------------------------------------------- Legge 10
@app.get("/api/clima-legge10/{istat}")
def clima_legge10(istat: str, anni: int = 10):
    """Dati climatici aggiornati dal clima reale del comune (non sostituiscono UNI 10349 / DPR 412)."""
    from meteo_storico import legge10
    _istat_valido(istat)
    try:
        from servizio.storici import zona_dpr
        ris = legge10.calcola(meteo.storico_giornaliero(istat), max(3, min(anni, 30)), zona_dpr=zona_dpr(istat))
    except FileNotFoundError:                      # archivio meteo della fase 3 non ancora copiato sul server
        raise HTTPException(503, "i dati meteo delle ultime stagioni non sono ancora sul server: "
                                 "arriveranno nei prossimi giorni")
    except ValueError as e:
        raise HTTPException(422, str(e))
    cm = meteo.comuni().set_index("istat")
    ris.update({"istat": istat, "comune": cm.at[istat, "nome"],
                "fonte": "Elaborazione su dati Open-Meteo.com (ERA5/Copernicus corretto), CC BY 4.0"})
    return ris


# ---------------------------------------------------------------------------------------------- patrimonio
@app.post("/api/patrimonio")
async def patrimonio_edifici(request: Request, file: UploadFile = File(...)):
    """CSV di edifici (indirizzo, dati catastali o coordinate) → particella, comune, punto.
    Gli indirizzi si cercano prima nell'ANNCSU (file locale aggiornato ogni mese dal worker), poi con Zornade.
    Il sito invia i file grandi a blocchi di qualche decina di righe e unisce i risultati."""
    from territorio import patrimonio
    from territorio.anncsu import Indirizzario
    from territorio.zornade import Zornade
    if not C.ZORNADE_API_KEY:
        raise HTTPException(503, "Geocodifica non configurata")
    dati = await file.read(int(C.MAX_UPLOAD_MB * 1024 * 1024) + 1)
    try:
        df = patrimonio.leggi(dati)
    except Exception as e:
        raise HTTPException(422, f"File non leggibile: {e}")
    finally:
        del dati
    if len(df) > C.MAX_EDIFICI:
        raise HTTPException(413, f"Troppi edifici ({len(df)}): massimo {C.MAX_EDIFICI} per caricamento")
    _limita(request, "patrimonio", len(df))
    z = Zornade(C.ZORNADE_API_KEY, C.DATI / "cache_zornade.sqlite")
    idx = Indirizzario(C.ANNCSU_FILE) if C.ANNCSU_FILE.exists() else None
    ris = await run_in_threadpool(patrimonio.geolocalizza, df, z, meteo.comuni(), False, idx)
    return {"riepilogo": patrimonio.riepilogo(ris), "geojson": patrimonio.geojson(ris),
            "righe": json.loads(ris.drop(columns=["dettaglio"], errors="ignore").to_json(orient="records")),
            "fonte": "Dati elaborati da Zornade (catasto Agenzia delle Entrate, ISTAT, OpenStreetMap ODbL)",
            "fonte_url": "https://zornade.com", "fonti": patrimonio.fonti(ris)}


# ---------------------------------------------------------------------------------------------- report
# File docx, pdf o xlsx generati in memoria dal documento ricevuto (o dalla risposta di un servizio):
# niente viene salvato su disco. Al massimo due report alla volta, per lasciare spazio alle previsioni.
_report_in_corso = asyncio.Semaphore(2)


def _formato_report(formato: str) -> str:
    f = (formato or "").lower().strip()
    if f not in report.FORMATI:
        raise HTTPException(400, f"Formato non supportato: scegliere tra {', '.join(report.FORMATI)}")
    return f


async def _corpo_limitato(request: Request) -> bytes:
    """Corpo della richiesta letto a pezzi, interrotto appena supera REPORT_MAX_MB (413)."""
    massimo = int(C.REPORT_MAX_MB * 1024 * 1024)
    troppo = HTTPException(413, f"Richiesta troppo grande (massimo {C.REPORT_MAX_MB:g} MB)")
    try:
        if int(request.headers.get("content-length") or 0) > massimo:
            raise troppo
    except ValueError:
        raise HTTPException(400, "Intestazione Content-Length non valida")
    corpo = bytearray()
    async for pezzo in request.stream():
        corpo += pezzo
        if len(corpo) > massimo:
            raise troppo
    if not corpo:
        raise HTTPException(400, "Corpo della richiesta vuoto: serve un documento JSON")
    return bytes(corpo)


def _nome_comune(istat: str) -> str | None:
    try:
        cm = meteo.comuni().set_index("istat")
        return str(cm.at[istat, "nome"]) if istat in cm.index else None
    except Exception:
        return None


async def _file_report(doc: report.Documento, formato: str) -> Response:
    async with _report_in_corso:
        try:
            contenuto = await run_in_threadpool(report.genera, doc, formato)
        except (ValueError, OSError) as e:
            raise HTTPException(422, f"Impossibile generare il report: {e}")
        except Exception as e:  # immagini non leggibili e simili (python-docx, fpdf2)
            if type(e).__module__.split(".")[0] in ("docx", "fpdf", "PIL"):
                raise HTTPException(422, f"Impossibile generare il report: {e}")
            raise
    nome = report.nome_file(doc, formato)
    return Response(contenuto, media_type=report.FORMATI[formato], headers={
        "Content-Disposition": f'attachment; filename="{nome}"', "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff"})


@app.get("/api/report/schema")
def report_schema():
    """Schema JSON del documento accettato da POST /api/report."""
    return report.Documento.model_json_schema()


@app.post("/api/report")
async def report_generico(request: Request, formato: str = "pdf"):
    """Documento generico (JSON, vedi /api/report/schema) → file docx, pdf o xlsx."""
    formato = _formato_report(formato)
    _limita(request, "report")
    corpo = await _corpo_limitato(request)
    try:
        doc = report.Documento.model_validate_json(corpo)
    except ValidationError as e:
        raise HTTPException(422, report.errori_in_italiano(e))
    finally:
        del corpo
    return await _file_report(doc, formato)


@app.post("/api/report/{tipo}")
async def report_servizio(request: Request, tipo: str, formato: str = "pdf"):
    """Report di un servizio a partire dalla risposta JSON già ottenuta dal sito:
    previsione (risposta di /api/previsione + "richiesta" facoltativa), legge10 (risposta di
    /api/clima-legge10/{istat}), patrimonio ({"righe": [...], "fonti": [...]})."""
    if tipo not in TIPI_REPORT:
        raise HTTPException(400, f"Tipo di report sconosciuto: scegliere tra {', '.join(TIPI_REPORT)}")
    formato = _formato_report(formato)
    _limita(request, "report")
    corpo = await _corpo_limitato(request)
    try:
        dati = json.loads(corpo)
    except ValueError:
        raise HTTPException(400, "Corpo della richiesta non valido: serve un oggetto JSON")
    finally:
        del corpo
    if not isinstance(dati, dict):
        raise HTTPException(422, "Il corpo deve essere un oggetto JSON (la risposta del servizio)")
    try:
        doc = TIPI_REPORT[tipo](dati, nome_comune=_nome_comune)
    except ValidationError as e:
        raise HTTPException(422, report.errori_in_italiano(e))
    except (TypeError, ValueError, KeyError, AttributeError) as e:
        log.warning("Report %s non costruibile: %s", tipo, e)
        raise HTTPException(422, "Dati non riconosciuti: inviare la risposta del servizio così come ricevuta")
    finally:
        del dati
    return await _file_report(doc, formato)


# ---------------------------------------------------------------------------------------------- mercati
# I dati GME (PUN, prezzi zonali, PSV, IGI) e TTF/PFOR restano interni: servono a simulazioni e analisi
# ma non sono esposti né scaricabili dall'API (condizioni d'uso GME ed EEX).


# ---------------------------------------------------------------------------------------------- Zornade
async def _zornade(percorso: str, params: dict) -> dict:
    if not C.ZORNADE_API_KEY:
        raise HTTPException(503, "Geocodifica non configurata")
    async with httpx.AsyncClient(timeout=20) as cl:
        r = await cl.get(f"{C.ZORNADE_URL}{percorso}", params=params, headers={"x-api-key": C.ZORNADE_API_KEY})
    if r.status_code != 200:
        raise HTTPException(502 if r.status_code >= 500 else r.status_code, "Errore del servizio di geocodifica")
    return r.json()


def _coord(d: dict) -> tuple[float | None, float | None]:
    for a, b in (("lat", "lng"), ("lat", "lon"), ("latitude", "longitude")):
        if a in d and b in d:
            return d[a], d[b]
    for k in ("centroid", "location", "point", "coordinates"):
        if isinstance(d.get(k), dict):
            return _coord(d[k])
    return None, None


@app.get("/api/geocodifica")
async def geocodifica(request: Request, q: str, comune: str | None = None):
    _limita(request, "zornade")
    if len(q) < 3:
        raise HTTPException(422, "Testo troppo corto")
    # Zornade lavora sul solo q ("via civico comune"): il parametro city riduce i risultati (prova del 25/10/2026)
    d = await _zornade("/geocode/search", {"q": f"{q} {comune}" if comune else q, "limit": 8})
    out = []
    for x in d.get("data", []):
        lat, lon = _coord(x)
        etichetta = (x.get("formatted_address") or x.get("display_name") or x.get("label") or x.get("address")
                     or x.get("name") or q)
        if lat is not None:
            out.append({"etichetta": etichetta, "lat": lat, "lon": lon})
    return {"risultati": out, "fonte": "Dati elaborati da Zornade", "fonte_url": "https://zornade.com"}


@app.get("/api/particella")
async def particella(request: Request, lat: float, lon: float):
    """Particella catastale e comune nel punto (Zornade /parcels/locate)."""
    _limita(request, "zornade")
    d = await _zornade("/parcels/locate", {"lat": lat, "lng": lon, "limit": 1})
    righe = d.get("data", [])
    if not righe:
        return {"particella": None}
    p = righe[0]
    mun = p.get("municipality") or {}
    belfiore = mun.get("code")
    cm = meteo.comuni()
    match = cm[cm.belfiore == belfiore]
    plat, plon = _coord(p)
    return {"particella": {"id": p.get("fid") or p.get("id"), "etichetta": p.get("label"),
                           "area_m2": p.get("area_m2"), "lat": plat, "lon": plon},
            "comune": {"belfiore": belfiore, "nome": mun.get("name"),
                       "istat": match.istat.iloc[0] if len(match) else None,
                       "disponibile": bool(len(match))},
            "fonte": "Dati elaborati da Zornade (fonti: Agenzia delle Entrate – catasto, ISTAT, OpenStreetMap ODbL)",
            "fonte_url": "https://zornade.com"}


@app.exception_handler(Exception)
async def errore(request: Request, exc: Exception):
    log.exception("Errore non gestito su %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Errore interno"})
