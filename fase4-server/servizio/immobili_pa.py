"""Immobili delle Pubbliche Amministrazioni (Territorio › Edifici pubblici, 17/11/2026).

Dati: censimento MEF «Patrimonio della PA» (dati al 31/12/2023, CC BY 4.0) agganciato alle particelle della cartografia
catastale dell'Agenzia delle Entrate (CC BY 4.0) dalla fase 7 (`python -m territorio immobili-pa` e `immobili-pa-sito`).
Le tessere della mappa sono un PMTiles statico servito da Caddy (`/edifici3d/immobili_pa/`); qui solo ricerca e schede,
lette dall'indice SQLite `DATI/immobili_pa/immobili_pa_<anno>.sqlite` (si usa il più recente), in sola lettura.

Rotte (limite per IP «immobili_pa»):
  GET /api/immobili-pa/info                       anno, conteggi, attribuzione, PMTiles; {"disponibile": false} se manca
  GET /api/immobili-pa/cerca?q=…&gruppo=C&limite=20   ricerca a parole (ente, comune, indirizzo, tipologia, foglio e
                                                  particella): tutte le parole devono esserci, anche iniziate; un
                                                  risultato per particella («altri_nella_particella»: unità in più)
  GET /api/immobili-pa/particella/{ref}           particella (centro, riquadro, area) e i suoi beni (al massimo 500)
  GET /api/immobili-pa/bene/{id}                  un bene (anche senza particella)

Nell'indice non ci sono il soggetto cedente e il suo codice fiscale (possono essere persone fisiche) né il CF dell'ente.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from . import config as C, protezione as P

router = APIRouter(prefix="/api/immobili-pa")

CAMPI_BENE = ("id_bene", "ref_ade", "aggancio", "natura", "tipologia", "amministrazione", "tipologia_amm", "gruppo",
              "regione", "provincia", "comune", "comune_cod", "indirizzo", "civico", "id_catastale", "lat", "lon",
              "geo_fonte", "superficie_mq", "cubatura_mc", "sup_pertinenze_mq", "epoca", "vincolo", "natura_giuridica",
              "titolo_proprieta", "quota_proprieta", "titolo_detenzione", "canone_annuo", "utilizzo", "finalita",
              "altra_finalita", "compendio", "tipologia_compendio", "a_terzi_intera", "a_terzi_parziale")
RE_REF = re.compile(r"^[A-Z0-9_]{11}\.[A-Z0-9]{1,8}$")


def cartella() -> Path:
    return Path(getattr(C, "CARTELLA_IMMOBILI_PA", None) or (C.DATI / "immobili_pa"))


def indice() -> Path | None:
    fs = sorted(cartella().glob("immobili_pa_*.sqlite"))
    return fs[-1] if fs else None


def _db() -> sqlite3.Connection:
    f = indice()
    if not f:
        raise HTTPException(503, "Gli immobili delle PA non sono ancora sul server.")
    db = sqlite3.connect(f"file:{f}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def _colonne(db: sqlite3.Connection) -> list[str]:
    presenti = {r[1] for r in db.execute("PRAGMA table_info(beni)")}
    return [c for c in CAMPI_BENE if c in presenti]


def _bene(r: sqlite3.Row, col: list[str]) -> dict:
    return {c: r[c] for c in col if r[c] not in (None, "")}


def domanda_fts(q: str) -> str | None:
    """Parole di almeno 2 caratteri (lettere e cifre), ciascuna come prefisso, tutte obbligatorie; None se vuota."""
    parole = [p for p in re.findall(r"[\w]+", (q or "").lower()) if len(p) >= 2][:8]
    return " AND ".join(f'"{p}"*' for p in parole) or None


@router.get("/info")
def info(req: Request):
    f = indice()
    if not f:
        return {"disponibile": False}
    db = _db()
    try:
        out = {k: json.loads(v) for k, v in db.execute("SELECT chiave, valore FROM info")}
    finally:
        db.close()
    return {"disponibile": True, **out}


@router.get("/cerca")
def cerca(req: Request, q: str = "", gruppo: str = "", limite: int = 20):
    P.limita(req, "immobili_pa")
    fts = domanda_fts(q)
    if not fts:
        raise HTTPException(400, "Scrivi almeno una parola di due lettere (ente, comune, indirizzo, tipologia…).")
    limite = max(1, min(int(limite), 50))
    db = _db()
    try:
        col = _colonne(db)
        sql = (f"SELECT {', '.join('b.' + c for c in col)}, p.lon AS p_lon, p.lat AS p_lat FROM cerca "
               "JOIN beni b ON b.rowid = cerca.rowid LEFT JOIN particelle p ON p.ref_ade = b.ref_ade "
               "WHERE cerca MATCH ?" + (" AND b.gruppo = ?" if gruppo else "") + " ORDER BY rank LIMIT ?")
        # si leggono più righe del necessario: le unità della stessa particella si raggruppano in un solo risultato
        arg = [fts] + ([gruppo[:1].upper()] if gruppo else []) + [limite * 8 + 1]
        righe = db.execute(sql, arg).fetchall()
    except sqlite3.OperationalError:
        raise HTTPException(400, "Ricerca non valida: usa solo parole e numeri.")
    finally:
        db.close()
    out, visti = [], {}
    for r in righe:
        chiave = r["ref_ade"] or f"b{r['id_bene']}"
        if chiave in visti:
            visti[chiave]["altri_nella_particella"] = visti[chiave].get("altri_nella_particella", 0) + 1
            continue
        if len(out) == limite:
            break
        b = _bene(r, col)
        visti[chiave] = b
        # punto per la mappa: centro della particella se c'è, altrimenti il punto del MEF
        if r["p_lon"] is not None:
            b["punto"] = [r["p_lon"], r["p_lat"]]
        elif b.get("lon") is not None and b.get("lat") is not None:
            b["punto"] = [b["lon"], b["lat"]]
        out.append(b)
    return {"risultati": out, "altri": len(out) == limite and len(righe) > len(visti)}


@router.get("/particella/{ref}")
def particella(req: Request, ref: str):
    P.limita(req, "immobili_pa")
    ref = ref.strip().upper()
    if not RE_REF.match(ref):
        raise HTTPException(400, "Riferimento della particella non valido.")
    db = _db()
    try:
        p = db.execute("SELECT * FROM particelle WHERE ref_ade = ?", [ref]).fetchone()
        if not p:
            raise HTTPException(404, "Particella senza beni pubblici censiti.")
        col = _colonne(db)
        beni = [_bene(r, col) for r in db.execute(f"SELECT {', '.join(col)} FROM beni WHERE ref_ade = ? LIMIT 500", [ref])]
    finally:
        db.close()
    return {"particella": {"ref_ade": ref, "punto": [p["lon"], p["lat"]], "riquadro": [p["ovest"], p["sud"], p["est"], p["nord"]],
                           "area_m2": p["area_m2"], "n_beni": p["n_beni"]}, "beni": beni}


@router.get("/bene/{id_bene}")
def bene(req: Request, id_bene: str):
    P.limita(req, "immobili_pa")
    if not re.fullmatch(r"\d{1,12}", id_bene or ""):
        raise HTTPException(400, "Identificativo del bene non valido.")
    db = _db()
    try:
        col = _colonne(db)
        r = db.execute(f"SELECT {', '.join(col)} FROM beni WHERE id_bene = ?", [id_bene]).fetchone()
    finally:
        db.close()
    if not r:
        raise HTTPException(404, "Bene non trovato.")
    return {"bene": _bene(r, col)}
