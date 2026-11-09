"""API HTTP (FastAPI). Tutte le rotte sono sotto /api; il sito statico è servito da Caddy.

I dati caricati dagli utenti sono elaborati in memoria e non vengono salvati.
Limiti d'uso, tetti per tutto il sito e verifica anti-robot: servizio/protezione.py.
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pandas as pd
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from . import alberi_osm, analisi, config as C, dbtr_coda, edifici, edifici_osm, interno, meteo, modello, orizzonte, ortofoto, protezione as P, pvgis, report, storici, strati, tabelle, terreno
from .report_servizi import CON_FORMATO as REPORT_CON_FORMATO, TIPI as TIPI_REPORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")
app = FastAPI(title="Previsioni energetiche – API", version="1.2.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json")
if C.ORIGINI_CORS:
    app.add_middleware(CORSMiddleware, allow_origins=C.ORIGINI_CORS, allow_methods=["GET", "POST"],
                       allow_headers=[P.INTESTAZIONE_SESSIONE, "Content-Type"])

app.include_router(storici.router)   # pagina "Dati climatici": /api/storici/...
app.include_router(edifici.router)   # edifici 3D (fase 10): gradi giorno mensili e clima orario per firma e FV
app.include_router(alberi_osm.router)   # alberi indicativi da OpenStreetMap dove manca il LiDAR (09/11/2026 d)
app.include_router(edifici_osm.router)   # ripiego OpenStreetMap di Modelli 3D fuori dal DBTR (07/11/2026)
app.include_router(strati.router)   # strati sopra le ortofoto (particelle, contorni edifici), prima delle tessere
app.include_router(ortofoto.router)  # ortofoto (fase 10, Fase B): proxy con copia su disco, una fonte per TOML
app.include_router(pvgis.router)     # confronto PVGIS chiamato dal server (fase 10, Fase B)
app.include_router(orizzonte.router) # orizzonte lontano dal Copernicus DEM 90 m (fase 10, Fase B)
app.include_router(terreno.router)   # tessere del terreno 3D su richiesta dal DTM del server (07/11/2026)
app.include_router(interno.router)   # pagina di stato nascosta degli edifici (fase 10, Fase C), con Cloudflare Access
app.include_router(dbtr_coda.router)   # «Aggiungi DBTR»: proposte all'archivio comune e approvazione interna (07/11/2026)
app.include_router(analisi.router)   # analisi 5 e 7–13 (fase 10, Fase E): modulo privato facoltativo, altrimenti «non disponibile»
# limiti per indirizzo (IPv6 per rete /64) in finestra mobile di un'ora: previsioni (pesanti), geocodifica (quota
# Zornade), patrimonio (contato in edifici: il sito invia i file grandi a blocchi, perché il tunnel Cloudflare chiude
# le richieste che durano più di 100 secondi), report, conversioni e rotte dei dati (meteo, Legge 10, mappa, comuni)
_storia = P.limiti          # nomi di prima, usati dai test
LIMITI = P.LIMITI
_limita = P.limita
if not P.turnstile_attivo():
    log.warning("Verifica anti-robot spenta: mancano TURNSTILE_SITEKEY e TURNSTILE_SECRET nel .env")


def _istat_valido(istat: str) -> None:
    if istat not in set(meteo.comuni().istat):
        raise HTTPException(404, f"Comune {istat} non disponibile")


@app.get("/api/salute")
def salute():
    p = C.DATI / "previsioni" / "ultima.json"
    return {"stato": "ok", "previsioni": json.loads(p.read_text()) if p.exists() else None,
            "modello_caricato": modello._modello is not None, "previsioni_in_corso": P.previsioni_in_corso()}


# ---------------------------------------------------------------------------------------------- verifica anti-robot
@app.get("/api/protezione")
def protezione_config():
    """Chiave pubblica di Turnstile per la pagina (null = verifica spenta) e rotte che la richiedono."""
    return {"turnstile": C.TURNSTILE_SITEKEY if P.turnstile_attivo() else None,
            "intestazione": P.INTESTAZIONE_SESSIONE, "minuti": C.SESSIONE_MINUTI, "rotte": list(P.TIPI_PROTETTI)}


@app.post("/api/sessione")
async def sessione(request: Request, token: str = Body(..., embed=True, max_length=4096)):
    """Gettone Turnstile (monouso) → gettone di sessione firmato, valido SESSIONE_MINUTI per questa rete."""
    _limita(request, "sessione")
    if not P.turnstile_attivo():
        return {"sessione": None, "scade": None}
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or None
    if not await P.verifica_turnstile(token, ip):
        raise HTTPException(403, "Verifica anti-robot non superata: ricarica la pagina e riprova.")
    g, scade = P.crea_sessione(P.rete_sessione(request))      # 09/11/2026 e: rete e browser
    return {"sessione": g, "scade": scade}


# ---------------------------------------------------------------------------------------------- dati
@app.get("/api/comuni")
def comuni(request: Request):
    _limita(request, "dati")
    cm = meteo.comuni()
    # (07/11/2026 sera: la rotta rispondeva 500 sul server) colonne mancanti e valori vuoti (NaN) non fermano la risposta
    col = [c for c in ("istat", "nome", "belfiore", "provincia", "lat", "lon", "svg_x", "svg_y") if c in cm.columns]
    t = cm[col].astype(object)
    # (09/11/2026) l'elenco ISTAT letto con i valori mancanti di pandas: il comune «None» (TO) e la sigla «NA» (Napoli, 92
    # comuni) erano diventati vuoti; qui si rimettono (l'elenco nuovo della fase 3 li legge già come testi)
    if "nome" in t.columns and "istat" in t.columns:
        t.loc[t["nome"].isna() & (t["istat"] == "001168"), "nome"] = "None"
    if "provincia" in t.columns and "istat" in t.columns:
        t.loc[t["provincia"].isna() & t["istat"].astype(str).str.startswith("063"), "provincia"] = "NA"
    return t.where(t.notna(), None).to_dict(orient="records")


@app.get("/api/mappa")
def mappa(request: Request, giorni: int = 7):
    """Gradi giorno di riscaldamento (base 20 °C), estivi di raffrescamento (base 24 °C) e temperatura media previsti
    nei prossimi `giorni` per ogni comune: la pagina mostra il freddo o il caldo secondo quale dei due prevale."""
    _limita(request, "dati")
    p = C.DATI / "previsioni" / "ultima.parquet"
    if not p.exists():
        return {"comuni": {}}
    d = meteo._previsioni(p.stat().st_mtime)
    inizio = pd.Timestamp.now(tz="UTC").floor("h")
    d = d[(d.time >= inizio) & (d.time < inizio + pd.Timedelta(days=max(1, min(giorni, 15))))]
    g = d.groupby("istat").temperature_2m.agg(["mean", "count"])
    gg = d.assign(gg=(20 - d.temperature_2m).clip(lower=0) / 24).groupby("istat").gg.sum()
    gc = d.assign(gc=(d.temperature_2m - 24).clip(lower=0) / 24).groupby("istat").gc.sum()
    return {"giorni": giorni, "comuni": {i: {"t": round(float(r["mean"]), 1), "gg": round(float(gg[i]), 1),
                                             "gc": round(float(gc[i]), 1)} for i, r in g.iterrows()}}


@app.get("/api/metodologia")
def metodologia(request: Request):
    _limita(request, "dati")
    out = {}
    for nome in ("metriche", "metriche_icon2i", "metriche_ifs"):
        p = C.DATI / f"{nome}.json"
        if p.exists():
            out[nome] = json.loads(p.read_text())
    return out


@app.get("/api/meteo/{istat}")
def meteo_comune(request: Request, istat: str, modalita: str = "breve", giorni: int = 14):
    _limita(request, "dati")
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


@app.get("/api/clima-previsto/{istat}")
def clima_previsto(request: Request, istat: str, modalita: str = "breve", orizzonte: int = 72,
                   covariate: str | None = None):
    """«Solo clima» della pagina Previsioni: variabili meteo previste per il comune, senza file dei consumi."""
    _limita(request, "dati")
    _istat_valido(istat)
    scelte = None if covariate is None else [c for c in covariate.split(",") if c]
    try:
        return modello.solo_clima(istat, modalita, orizzonte, scelte)
    except modello.MeteoMancante:
        raise HTTPException(404, "I dati meteo di questo comune non sono ancora sul server")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/previsione")
async def previsione(request: Request, file: UploadFile = File(...), istat: str = Form(...),
                     modalita: str = Form("breve"), orizzonte: int = Form(72), tipo: str = Form("energia"),
                     covariate: str | None = Form(None), verifica: bool = Form(False)):
    P.richiedi_sessione(request)
    _limita(request, "previsione")
    _istat_valido(istat)
    dati = await file.read(int(C.MAX_UPLOAD_MB * 1024 * 1024) + 1)
    if len(dati) > C.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File troppo grande (massimo {C.MAX_UPLOAD_MB:g} MB)")
    try:
        serie = modello.leggi_csv(tabelle.in_csv(dati, C.MAX_RIGHE))   # anche .xlsx e .ods
        scelte = None if covariate is None else [c for c in covariate.split(",") if c]
        async with P.turno_previsione():         # al massimo PREVISIONI_PARALLELE insieme (2 OCPU)
            return await run_in_threadpool(modello.prevedi, serie, istat, modalita, orizzonte, tipo, scelte, verifica)
    except ValueError as e:
        raise HTTPException(422, str(e))
    finally:
        del dati


# ---------------------------------------------------------------------------------------------- Legge 10
@app.get("/api/clima-legge10/{istat}")
def clima_legge10(request: Request, istat: str, anni: int = 10):
    """Dati climatici aggiornati dal clima reale del comune (non sostituiscono UNI 10349 / DPR 412)."""
    from meteo_storico import legge10
    _limita(request, "dati")
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


# ---------------------------------------------------------------------------------------------- fogli di calcolo
@app.post("/api/converti")
async def converti(request: Request, file: UploadFile = File(...)):
    """Excel (.xlsx) od OpenDocument (.ods) → CSV col punto e virgola (primo foglio), per le pagine che leggono il file
    nel browser (patrimonio, valori per sede). Il file non viene salvato; i CSV tornano come sono."""
    _limita(request, "converti")
    dati = await file.read(int(C.MAX_UPLOAD_MB * 1024 * 1024) + 1)
    if len(dati) > C.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File troppo grande (massimo {C.MAX_UPLOAD_MB:g} MB)")
    try:
        t = tabelle.tipo(dati)
        nomi = tabelle.fogli(dati)
        testo = (await run_in_threadpool(tabelle.in_csv, dati, C.MAX_RIGHE)).decode("utf-8", errors="replace")
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:  # file danneggiato o non leggibile
        raise HTTPException(422, f"File non leggibile: {e}")
    finally:
        del dati
    return {"formato": t, "fogli": nomi, "foglio_usato": nomi[0] if nomi else None, "csv": testo}


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
    P.richiedi_sessione(request)
    dati = await file.read(int(C.MAX_UPLOAD_MB * 1024 * 1024) + 1)
    try:
        df = patrimonio.leggi(tabelle.in_csv(dati, C.MAX_EDIFICI))       # anche .xlsx e .ods
    except Exception as e:
        raise HTTPException(422, f"File non leggibile: {e}")
    finally:
        del dati
    if len(df) > C.MAX_EDIFICI:
        raise HTTPException(413, f"Troppi edifici ({len(df)}): massimo {C.MAX_EDIFICI} per caricamento")
    _limita(request, "patrimonio", len(df))
    P.zornade_disponibile(2 * len(df))      # al peggio una geocodifica e una particella per edificio
    z = Zornade(C.ZORNADE_API_KEY, C.DATI / "cache_zornade.sqlite")
    idx = Indirizzario(C.ANNCSU_FILE) if C.ANNCSU_FILE.exists() else None
    try:
        ris = await run_in_threadpool(patrimonio.geolocalizza, df, z, meteo.comuni(), False, idx)
    finally:
        P.zornade_conta(z.chiamate)          # solo le chiamate vere: la cache non consuma quota
    return {"riepilogo": patrimonio.riepilogo(ris), "geojson": patrimonio.geojson(ris),
            "righe": json.loads(ris.drop(columns=["dettaglio"], errors="ignore").to_json(orient="records")),
            "fonte": "Dati elaborati da Zornade (catasto Agenzia delle Entrate, ISTAT, OpenStreetMap ODbL)",
            "fonte_url": "https://zornade.com", "fonti": patrimonio.fonti(ris)}


# ---------------------------------------------------------------------------------------------- report
# File pdf, xlsx o ods generati in memoria dal documento ricevuto (o dalla risposta di un servizio): niente viene
# salvato su disco. Word (docx) e ODT sono spenti dal 28/10/2026 (config REPORT_FORMATI): rispondono 410.
# Al massimo due report alla volta, per lasciare spazio alle previsioni.
_report_in_corso = asyncio.Semaphore(2)


def _formato_report(formato: str) -> str:
    f = (formato or "").lower().strip()
    attivi = report.formati_attivi()
    if f in report.FORMATI and f not in attivi:
        nomi = ", ".join(report.NOMI_FORMATI[x] for x in attivi)
        raise HTTPException(410, f"Il formato {report.NOMI_FORMATI[f]} non è più disponibile: il servizio gratuito "
                                 f"genera i report solo in PDF e i dati grezzi in Excel o ODS (formati: {nomi})")
    if f not in attivi:
        raise HTTPException(400, f"Formato non supportato: scegliere tra {', '.join(attivi)}")
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
        except Exception as e:  # immagini non leggibili e simili (python-docx, fpdf2, odfpy)
            if type(e).__module__.split(".")[0] in ("docx", "fpdf", "PIL", "odf"):
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
    """Documento generico (JSON, vedi /api/report/schema) → file pdf, xlsx o ods (docx e odt spenti: 410)."""
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
    /api/clima-legge10/{istat}), patrimonio ({"righe": [...], "fonti": [...]}), indicatori, valori_sedi
    (totali, costi unitari, mappe e Pareto in SVG, tabelle: vedi report_servizi.report_valori_sedi)."""
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
        extra = {"formato": formato} if tipo in REPORT_CON_FORMATO else {}
        doc = TIPI_REPORT[tipo](dati, nome_comune=_nome_comune, **extra)
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
    P.zornade_disponibile(1)
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            r = await cl.get(f"{C.ZORNADE_URL}{percorso}", params=params, headers={"x-api-key": C.ZORNADE_API_KEY})
    finally:
        P.zornade_conta(1)
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
    P.richiedi_sessione(request)
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
        try:     # (08/11/2026) senza coordinate vere (vuote o 0,0) non è un punto: si scarta, la pagina offre il comune
            ok = lat is not None and lon is not None and not (abs(float(lat)) < 1e-6 and abs(float(lon)) < 1e-6)
        except (TypeError, ValueError):
            ok = False
        if ok:
            out.append({"etichetta": etichetta, "lat": lat, "lon": lon})
    return {"risultati": out, "fonte": "Dati elaborati da Zornade", "fonte_url": "https://zornade.com"}


@app.get("/api/particella")
async def particella(request: Request, lat: float, lon: float):
    """Particella catastale e comune nel punto (Zornade /parcels/locate)."""
    P.richiedi_sessione(request)
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
