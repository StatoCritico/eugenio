"""«Aggiungi DBTR» – coda sul server dei DB topografici proposti dagli utenti (07/11/2026, decisione di Paolo).

La pagina Patrimonio › Aggiungi edifici (DB topografico) legge il file nel browser (nulla va al server); **solo se l'utente
spunta il consenso** (casella non spuntata di default) lo stesso file arriva qui, a pezzi, per l'archivio comune:

  POST   /api/dbtr/inizia              regione, comune, (istat, comune intero), formato, nome e dimensione del file, consenso;
                                       Turnstile, 3 file al giorno per IP, coda e disco con tetti → id e gettone
  PUT    /api/dbtr/{id}/pezzo/{n}      pezzo n (DBTR_PEZZO_MB, 32 MB) nel corpo della richiesta, gettone nell'intestazione
  POST   /api/dbtr/{id}/fine           file completo: impronta SHA-256, controllo leggero (zip senza percorsi «..», link
                                       simbolici, bombe; o GeoPackage) → «ricevuto», poi lo prepara il servizio edifici-coda
  GET    /api/dbtr/{id}                stato della propria proposta (gettone): in coda, in preparazione, in attesa di
                                       approvazione, installato, rifiutato
  DELETE /api/dbtr/{id}                ritiro della propria proposta prima dell'approvazione (file cancellati)

Rotte interne (Cloudflare Access + JWT verificato come in interno.py, più l'intestazione X-EuGEnio-Interno contro le
richieste da altri siti): GET /api/interno/dbtr/coda, GET /api/interno/dbtr/{id}/anteprima, GET …/registro,
POST …/approva (lo installa il servizio edifici-coda entro un minuto), POST …/rifiuta (file cancellati subito).

Nessun dato personale: niente email né nome, solo comune e regione; l'IP non si scrive nella richiesta (i limiti per IP
restano in memoria come per le altre rotte). Il file si conserva fino all'approvazione (poi diventa parte dell'archivio
pubblico CC BY) o al rifiuto (cancellato); i caricamenti lasciati a metà si cancellano dopo 6 ore.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse

from . import config as C, interno, protezione as P

try:
    from edifici3d import coda as K          # stessa logica del servizio edifici-coda (solo libreria standard in testa)
except ImportError:  # pragma: no cover - immagine senza la fase 10
    K = None

log = logging.getLogger(__name__)
router = APIRouter()
INTESTAZIONE = "X-EuGEnio-Dbtr"
APERTI = ("caricamento", "ricevuto", "in preparazione", "in attesa di approvazione", "controlli non superati", "approvato")
MB = 1024 * 1024


def _attiva():
    if not C.DBTR_CODA or K is None:
        raise HTTPException(404, "Proposta all'archivio comune non disponibile su questo server.")


def _gettone(rid: str) -> str:
    return P._firma("dbtr:" + rid)


def _richiesta(request: Request, rid: str) -> dict:
    """Richiesta dell'utente (gettone nell'intestazione o nel parametro g)."""
    g = request.headers.get(INTESTAZIONE) or request.query_params.get("g") or ""
    if not K.ID.fullmatch(rid or "") or not hmac.compare_digest(g, _gettone(rid)):
        raise HTTPException(404, "Proposta non trovata.")
    r = K.leggi_richiesta(C.CARTELLA_CODA_DBTR, rid)
    if r is None:
        e = K.leggi_esito(C.CARTELLA_CODA_DBTR, rid)
        if e:
            return e
        raise HTTPException(404, "Proposta non trovata (ritirata, scaduta o rifiutata).")
    return r


def _occupato(cartella: Path) -> int:
    n = 0
    for p in cartella.rglob("*") if cartella.is_dir() else []:
        try:
            if p.is_file():
                n += p.stat().st_size
        except OSError:
            pass
    return n


def _libero(cartella: Path) -> float:
    q = cartella
    while not q.exists() and q != q.parent:
        q = q.parent
    return shutil.disk_usage(q).free / 1024 ** 3


def _pezzi(dimensione: int) -> int:
    pz = int(C.DBTR_PEZZO_MB * MB)
    return max(1, -(-dimensione // pz))


@router.post("/api/dbtr/inizia")
def inizia(request: Request, regione: str = Body(..., max_length=8), comune: str = Body(..., max_length=80),
           istat: str | None = Body(None, max_length=6), intero: bool = Body(False), formato: str = Body(..., max_length=8),
           dimensione: int = Body(...), consenso: bool = Body(False), impronta: str | None = Body(None, max_length=64)):
    """Apre una proposta: niente dati personali, solo comune e regione."""
    _attiva()
    P.richiedi_sessione(request)
    if consenso is not True:
        raise HTTPException(422, "Serve il consenso esplicito per mandare il file al server.")
    if regione not in K.REGIONI:
        raise HTTPException(422, "Regione non prevista: Emilia-Romagna, Lombardia, Friuli Venezia Giulia o Liguria.")
    if formato not in K.FORMATI:
        raise HTTPException(422, "Formato non previsto: zip (GeoPackage o Shapefile) o GeoPackage.")
    try:
        nome = K.nome_comune(comune)
        cartella_comune = K.slug(nome)
    except K.FileNonValido as e:
        raise HTTPException(422, str(e))
    if istat is not None and istat != "" and not (len(istat) == 6 and istat.isdigit()):
        raise HTTPException(422, "Codice ISTAT del comune: sei cifre.")
    if impronta and not (len(impronta) == 64 and all(c in "0123456789abcdef" for c in impronta)):
        raise HTTPException(422, "Impronta SHA-256 non valida.")
    if not (100 <= dimensione <= C.DBTR_MAX_MB * MB):
        raise HTTPException(413, f"File troppo grande: al massimo {C.DBTR_MAX_MB:g} MB (oltre, scrivici dalla pagina Contattaci).")
    coda = Path(C.CARTELLA_CODA_DBTR)
    coda.mkdir(parents=True, exist_ok=True)
    K.pulizia(coda)
    aperte = [r for r in K.richieste(coda) if r.get("stato") in APERTI]
    if len(aperte) >= C.DBTR_CODA_MAX:
        raise HTTPException(503, "La coda delle proposte è piena: riprova tra qualche giorno.")
    if _occupato(coda) + dimensione > C.DBTR_CODA_MAX_GB * 1024 ** 3 or _libero(coda) - dimensione / 1024 ** 3 < C.DBTR_LIBERO_MIN_GB:
        raise HTTPException(503, "Spazio della coda esaurito: riprova tra qualche giorno.")
    P.limita(request, "dbtr")
    rid = secrets.token_hex(16)
    d = K.cartella_richiesta(coda, rid)
    d.mkdir(parents=True)
    with open(d / "caricato.part", "wb") as f:
        f.truncate(dimensione)
    r = {"id": rid, "stato": "caricamento", "creata": K.adesso(), "t": round(time.time(), 3), "regione": regione, "comune": nome,
         "comune_slug": cartella_comune, "istat": istat or None, "intero": bool(intero and istat), "formato": formato,
         "dimensione": dimensione, "pezzi": _pezzi(dimensione), "ricevuti": [], "impronta": impronta}
    K.scrivi_richiesta(coda, r)
    return {"id": rid, "gettone": _gettone(rid), "pezzo_byte": int(C.DBTR_PEZZO_MB * MB), "pezzi": r["pezzi"]}


@router.put("/api/dbtr/{rid}/pezzo/{n}")
async def pezzo(request: Request, rid: str, n: int):
    _attiva()
    r = _richiesta(request, rid)
    if r.get("stato") != "caricamento":
        raise HTTPException(409, "Caricamento già chiuso.")
    if not (0 <= n < r["pezzi"]):
        raise HTTPException(422, "Pezzo fuori dal file.")
    P.limita(request, "dbtr_pezzi")
    pz = int(C.DBTR_PEZZO_MB * MB)
    atteso = min(pz, r["dimensione"] - n * pz)
    d = K.cartella_richiesta(C.CARTELLA_CODA_DBTR, rid)
    scritti = 0
    with open(d / "caricato.part", "r+b") as f:
        f.seek(n * pz)
        async for b in request.stream():
            scritti += len(b)
            if scritti > atteso:
                raise HTTPException(413, "Pezzo più grande del previsto.")
            f.write(b)
    if scritti != atteso:
        raise HTTPException(422, f"Pezzo incompleto ({scritti} byte su {atteso}): riprova.")
    r = K.leggi_richiesta(C.CARTELLA_CODA_DBTR, rid) or r
    r["ricevuti"] = sorted(set(r.get("ricevuti", [])) | {n})
    K.scrivi_richiesta(C.CARTELLA_CODA_DBTR, r)
    return {"ricevuti": len(r["ricevuti"]), "pezzi": r["pezzi"]}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(MB), b""):
            h.update(b)
    return h.hexdigest()


@router.post("/api/dbtr/{rid}/fine")
async def fine(request: Request, rid: str):
    _attiva()
    r = _richiesta(request, rid)
    if r.get("stato") != "caricamento":
        raise HTTPException(409, "Caricamento già chiuso.")
    mancano = sorted(set(range(r["pezzi"])) - set(r.get("ricevuti", [])))
    if mancano:
        raise HTTPException(422, f"Mancano {len(mancano)} pezzi del file: riprova il caricamento.")
    coda = Path(C.CARTELLA_CODA_DBTR)
    d = K.cartella_richiesta(coda, rid)
    file = d / "caricato.bin"
    (d / "caricato.part").replace(file)
    try:
        if r.get("impronta") and await run_in_threadpool(_sha256, file) != r["impronta"]:
            raise K.FileNonValido("il file arrivato è diverso da quello letto nel browser (impronta SHA-256): riprova")
        tipo = await run_in_threadpool(K.controlla_file, file)
        if tipo["formato"] != r["formato"] and not (r["formato"] == "zip" and tipo["formato"] == "zip"):
            r["formato"] = tipo["formato"]
    except K.FileNonValido as e:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(422, f"File rifiutato: {e}.")
    r["stato"] = "ricevuto"
    r["ricevuto"] = K.adesso()
    r["contenuto"] = {k: tipo.get(k) for k in ("voci", "estratto") if k in tipo}
    r.pop("ricevuti", None)
    K.scrivi_richiesta(coda, r)
    davanti = sum(1 for x in K.richieste(coda) if x.get("stato") in ("ricevuto", "in preparazione") and x["creata"] < r["creata"])
    return {"stato": "ricevuto", "davanti": davanti, "messaggio": _testo_stato(r)}


def _testo_stato(r: dict) -> str:
    s = r.get("stato")
    return {
        "caricamento": "Caricamento non finito.",
        "ricevuto": "File ricevuto: è in coda per la preparazione sul server (una proposta alla volta, di solito entro un'ora; "
                    "di notte dopo le 7).",
        "in preparazione": "Il server sta controllando e preparando il file.",
        "in attesa di approvazione": "Controlli superati: la proposta aspetta l'approvazione di Stato Critico.",
        "controlli non superati": "Il file non ha superato i controlli automatici: Stato Critico lo guarderà comunque prima di "
                                  "decidere; puoi ritirare la proposta.",
        "approvato": "Approvato: gli edifici entrano nell'archivio comune entro qualche minuto.",
        "installato": "Approvato e aggiunto all'archivio comune: grazie! Gli edifici si vedono in Modelli 3D per tutti.",
        "rifiutato": "Proposta non accolta: il file è stato cancellato dal server.",
    }.get(s, s or "")


@router.get("/api/dbtr/{rid}")
def stato(request: Request, rid: str, response: Response):
    _attiva()
    P.limita(request, "dati")
    r = _richiesta(request, rid)
    response.headers["Cache-Control"] = "no-store"
    out = {"stato": r.get("stato"), "messaggio": _testo_stato(r), "comune": r.get("comune"), "regione": r.get("regione")}
    if r.get("esito"):
        out["corpi"] = r["esito"].get("corpi")
    return out


@router.delete("/api/dbtr/{rid}")
def ritira(request: Request, rid: str):
    _attiva()
    r = _richiesta(request, rid)
    if r.get("stato") in ("in preparazione", "approvato", "installato", "rifiutato"):
        raise HTTPException(409, "La proposta non si può più ritirare in questo stato.")
    shutil.rmtree(K.cartella_richiesta(C.CARTELLA_CODA_DBTR, rid), ignore_errors=True)
    return {"stato": "ritirata", "messaggio": "Proposta ritirata: il file è stato cancellato dal server."}


# ---------------------------------------------------------------------------------------------- pagina interna
def _interno(request: Request, scrive: bool = False) -> dict:
    P.limita(request, "interno")
    chi = interno.richiedi_accesso(request)
    if scrive:
        if request.headers.get("x-eugenio-interno") != "1" or request.headers.get("sec-fetch-site", "same-origin") == "cross-site":
            raise HTTPException(403, "Richiesta non ammessa.")
    if K is None:
        raise HTTPException(404, "Coda non disponibile.")
    return chi


@router.get("/api/interno/dbtr/coda")
def coda_interna(request: Request, response: Response):
    chi = _interno(request)
    for k, v in interno.NOINDEX.items():
        response.headers[k] = v
    coda = Path(C.CARTELLA_CODA_DBTR)
    voci = []
    for r in K.richieste(coda):
        r = {k: v for k, v in r.items() if k not in ("ricevuti",)}
        r["anteprima"] = (coda / r["id"] / "anteprima.geojson").is_file()
        voci.append(r)
    storico = []
    try:
        storico = [json.loads(x) for x in (coda / "storico.jsonl").read_text(encoding="utf-8").splitlines()[-30:]]
    except (OSError, ValueError):
        pass
    return {"coda": voci, "storico": storico[::-1], "utente": str(chi.get("email", ""))[:120], "attiva": C.DBTR_CODA,
            "limiti": {"max_mb": C.DBTR_MAX_MB, "al_giorno_per_ip": C.DBTR_CARICAMENTI_GIORNO, "coda_max": C.DBTR_CODA_MAX},
            "occupato_mb": round(_occupato(coda) / MB, 1)}


@router.get("/api/interno/dbtr/{rid}/anteprima")
def anteprima(request: Request, rid: str):
    _interno(request)
    p = K.cartella_richiesta(C.CARTELLA_CODA_DBTR, rid) / "anteprima.geojson"
    if not p.is_file():
        raise HTTPException(404, "Anteprima non ancora pronta.")
    return FileResponse(p, media_type="application/geo+json", headers=interno.NOINDEX)


@router.get("/api/interno/dbtr/{rid}/registro")
def registro(request: Request, rid: str):
    _interno(request)
    p = K.cartella_richiesta(C.CARTELLA_CODA_DBTR, rid) / "registro.txt"
    t = p.read_text(encoding="utf-8", errors="replace")[-20000:] if p.is_file() else "(nessun registro)"
    return PlainTextResponse(t, headers=interno.NOINDEX)


@router.post("/api/interno/dbtr/{rid}/approva")
def approva(request: Request, rid: str):
    chi = _interno(request, scrive=True)
    coda = Path(C.CARTELLA_CODA_DBTR)
    r = K.leggi_richiesta(coda, rid) if K.ID.fullmatch(rid) else None
    if not r:
        raise HTTPException(404, "Richiesta non trovata.")
    if r.get("stato") != "in attesa di approvazione":
        raise HTTPException(409, f"Si approvano solo le richieste in attesa di approvazione (questa è «{r.get('stato')}»).")
    r["stato"] = "approvato"
    r["approvata"] = K.adesso()
    r["approvata_da"] = str(chi.get("email", ""))[:120]
    K.scrivi_richiesta(coda, r)
    log.info("DBTR %s (%s, %s) approvato", rid, r.get("comune"), r.get("regione"))
    return {"stato": "approvato", "messaggio": "Approvata: il servizio edifici-coda la installa entro un minuto "
                                               "(archivio precedente in _precedenti/, archivi.json rigenerato)."}


@router.post("/api/interno/dbtr/{rid}/rifiuta")
def rifiuta(request: Request, rid: str):
    _interno(request, scrive=True)
    coda = Path(C.CARTELLA_CODA_DBTR)
    r = K.leggi_richiesta(coda, rid) if K.ID.fullmatch(rid) else None
    if not r:
        raise HTTPException(404, "Richiesta non trovata.")
    if r.get("stato") in ("in preparazione", "approvato"):
        raise HTTPException(409, f"Non si rifiuta una richiesta «{r.get('stato')}»: aspetta la fine.")
    shutil.rmtree(K.cartella_richiesta(coda, rid), ignore_errors=True)
    K.scrivi_esito(coda, rid, "rifiutato", r)
    log.info("DBTR %s (%s, %s) rifiutato, file cancellati", rid, r.get("comune"), r.get("regione"))
    return {"stato": "rifiutato", "messaggio": "Rifiutata: file cancellati."}

