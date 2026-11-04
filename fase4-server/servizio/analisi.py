"""Analisi avanzate degli edifici (fase 10, Fase E; § 9 della proposta, analisi 5 e 7–13): aggancio facoltativo al
modulo privato delle metodiche UNI.

Rotte (limite «dati» per indirizzo):
  GET  /api/analisi/stato        per ogni analisi solo «disponibile» o «analisi non disponibile in questa
                                 installazione»; niente sul contenuto o sul percorso del modulo privato
  POST /api/analisi/{id}         esegue l'analisi (corpo JSON: edificio.corpi, clima, ipotesi, opzioni); 503 con il
                                 messaggio «analisi non disponibile in questa installazione» se il modulo manca o
                                 l'analisi non è pronta. Il risultato contiene solo numeri per l'edificio dell'utente e i
                                 nomi delle fonti (mai prospetti o estratti delle norme); niente viene salvato.

Il modulo privato sta fuori dal repository (`fase10-edifici3d/uni_privato/`); sul server in
`/srv/energia/dati/uni_privato`, cioè `/dati/uni_privato` nel container (o dove dice `UNI_PRIVATO`). Senza modulo
(mirror, installazione nuova) tutte le analisi sono «non disponibili» e il resto del servizio funziona come prima.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analisi")

try:                                    # pacchetto della fase 10 (nell'immagine: /app/edifici3d, solo analisi.py)
    from edifici3d import analisi as A
except Exception as e:                  # pragma: no cover - installazione senza fase 10
    A = None
    log.warning("edifici3d.analisi non disponibile: %s", e)

NON_DISPONIBILE = getattr(A, "NON_DISPONIBILE", "analisi non disponibile in questa installazione")


@router.get("/stato")
def stato(request: Request):
    P.limita(request, "dati")
    if A is None:
        return {"interfaccia": None, "modulo": False, "analisi": []}
    return A.stato()


@router.post("/{id}")
async def esegui(id: str, request: Request, richiesta: dict = Body(...)):
    P.limita(request, "dati")
    if A is None:
        raise HTTPException(503, NON_DISPONIBILE)
    if id not in A.ANALISI:
        raise HTTPException(404, f"Analisi {id} sconosciuta")
    try:
        return await run_in_threadpool(A.calcola, id, richiesta)
    except A.NonDisponibile:
        raise HTTPException(503, NON_DISPONIBILE)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception:
        log.exception("analisi %s non riuscita", id)
        raise HTTPException(500, "Analisi non riuscita: errore del server")
