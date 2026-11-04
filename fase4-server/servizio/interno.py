"""Pagine interne (fase 10, Fase C, § 12 della proposta): stato della pipeline notturna degli edifici.

Rotte (mai nel menu, nella mappa del sito o nel robots.txt; risposte con `X-Robots-Tag: noindex` e `no-store`):
  GET /api/interno/edifici/stato   zone, avanzamento delle tessere, ultime 30 esecuzioni, esiti per qualità, errori,
                                   spazio su disco, fonti con stato e motivo (dagli stato.json scritti dalla pipeline)
  GET /api/interno/verifica        204 se l'accesso è valido (usata da Caddy con forward_auth per /interno/*)

Protezione su tre livelli:
1. Cloudflare Access su `/interno/*` e `/api/interno/*` (configurazione manuale nel pannello di Cloudflare, passi in
   AGGIORNAMENTO_2026-11-04.md § Fase C): solo l'email di Paolo.
2. Caddy rifiuta (403) le richieste senza l'intestazione `Cf-Access-Jwt-Assertion`.
3. Qui il gettone JWT dell'intestazione si **verifica**: firma RS256 con le chiavi pubbliche del team
   (`https://<team>/cdn-cgi/access/certs`, tenute in memoria un'ora), `aud` = CF_ACCESS_AUD, `iss` = https://<team>,
   scadenza. Team e audience si leggono dal .env (CF_ACCESS_TEAM_DOMAIN, CF_ACCESS_AUD), mai dal codice; facoltativo
   CF_ACCESS_EMAIL (elenco di email ammesse). Senza team o audience nel .env le rotte rispondono 503: chiuse per
   impostazione (anche nei mirror).
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from . import config as C, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interno")
INTESTAZIONE = "cf-access-jwt-assertion"
NOINDEX = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
_chiavi: dict = {"client": None, "dominio": None}


def _dominio() -> str:
    d = (C.CF_ACCESS_TEAM_DOMAIN or "").strip().lower()
    d = re.sub(r"^https?://", "", d).strip("/")
    return d


def configurato() -> bool:
    return bool(_dominio() and C.CF_ACCESS_AUD)


def _client_chiavi():
    import jwt
    d = _dominio()
    if _chiavi["client"] is None or _chiavi["dominio"] != d:
        _chiavi["client"] = jwt.PyJWKClient(f"https://{d}/cdn-cgi/access/certs", cache_keys=True, lifespan=3600,
                                            timeout=10)
        _chiavi["dominio"] = d
    return _chiavi["client"]


def verifica_gettone(gettone: str, chiave=None) -> dict:
    """Controlla firma, audience, emittente e scadenza del JWT di Cloudflare Access; restituisce le affermazioni.
    `chiave` serve solo ai test (altrimenti si prende dal JWKS del team)."""
    import jwt
    if not gettone or len(gettone) > 8192:
        raise HTTPException(403, "Accesso riservato.")
    try:
        if chiave is None:
            chiave = _client_chiavi().get_signing_key_from_jwt(gettone).key
        dati = jwt.decode(gettone, chiave, algorithms=["RS256"], audience=C.CF_ACCESS_AUD,
                          issuer=f"https://{_dominio()}", leeway=60, options={"require": ["exp", "iat", "aud", "iss"]})
    except HTTPException:
        raise
    except Exception as e:
        log.warning("accesso interno rifiutato: %s", type(e).__name__)
        raise HTTPException(403, "Accesso riservato.")
    ammesse = {x.strip().lower() for x in C.CF_ACCESS_EMAIL.split(",") if x.strip()}
    if ammesse and str(dati.get("email", "")).lower() not in ammesse:
        raise HTTPException(403, "Accesso riservato.")
    return dati


def richiedi_accesso(request: Request, chiave=None) -> dict:
    if not configurato():
        raise HTTPException(503, "Pagina interna non configurata: mancano CF_ACCESS_TEAM_DOMAIN e CF_ACCESS_AUD nel .env.")
    return verifica_gettone(request.headers.get(INTESTAZIONE, ""), chiave)


# ---------------------------------------------------------------------------------------------- stato
def _gb(n: float) -> float:
    return round(n / 1024 ** 3, 2)


def disco() -> dict:
    out = {}
    for nome, p in (("dati", C.DATI), ("edifici", C.CARTELLA_EDIFICI_INTERNA)):
        q = Path(p)
        while not q.exists() and q != q.parent:
            q = q.parent
        try:
            u = shutil.disk_usage(q)
            out[nome] = {"percorso": nome, "totale_gb": _gb(u.total), "usato_gb": _gb(u.used), "libero_gb": _gb(u.free)}
        except OSError:
            pass
    return out


def stato_edifici() -> dict:
    """Zone dagli stato.json della pipeline (sola lettura); niente percorsi del server nella risposta."""
    zone = []
    cart = Path(C.EDIFICI_STATO)
    for p in sorted(cart.glob("*.json")) if cart.is_dir() else []:
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(s, dict) or "tessere" not in s:
            continue
        tessere = s.get("tessere") or {}
        da_fare = sorted(k for k, v in tessere.items() if v.get("stato") in ("da fare", "errore", "in corso"))
        zone.append({
            "zona": s.get("zona"), "nome": s.get("nome"), "ordine": s.get("ordine", 99), "prova": bool(s.get("prova")),
            "aggiornato": s.get("aggiornato"), "completata": s.get("completata"), "totale_tessere": s.get("totale_tessere", 0),
            "corpi": s.get("corpi"), "conteggi": s.get("conteggi", {}), "qualita": s.get("qualita", {}),
            "esecuzioni": (s.get("esecuzioni") or [])[-30:], "errori": (s.get("errori") or [])[-30:],
            "fonti": s.get("fonti", []), "limiti": s.get("limiti", {}), "disco_pipeline": s.get("disco"),
            "prossime": da_fare[:20],
            "saltate": sorted(k for k, v in tessere.items() if v.get("stato") == "saltata")[:50],
            "tessere": {k: {c: v.get(c) for c in ("stato", "fonte", "fatta", "corpi", "falde", "qualita", "tentativi",
                                                   "errore", "secondi", "byte_scaricati", "byte_prodotti")}
                        for k, v in list(tessere.items())[:3000]},
        })
    zone.sort(key=lambda z: (z["prova"], z["ordine"]))
    return {"zone": zone, "disco": disco(), "generato": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


@router.get("/verifica")
def verifica(request: Request):
    P.limita(request, "interno")
    richiedi_accesso(request)
    return Response(status_code=204, headers=NOINDEX)


@router.get("/edifici/stato")
def edifici_stato(request: Request, response: Response):
    P.limita(request, "interno")
    chi = richiedi_accesso(request)
    for k, v in NOINDEX.items():
        response.headers[k] = v
    d = stato_edifici()
    d["utente"] = str(chi.get("email", ""))[:120]
    return d
