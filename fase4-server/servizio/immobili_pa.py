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
  GET /api/immobili-pa/bene/{id}                  un bene (anche senza particella): «bene» è la prima dichiarazione,
                                                  «dichiarazioni» tutte (lo stesso bene può essere dichiarato da più enti,
                                                  di solito proprietario e detentore; prima del 22/11/2026 se ne vedeva una)
Ogni bene (in /particella, /bene e /cerca) ha i campi pubblicabili dell'indice (CAMPI_BENE: dal 22/11/2026 sera anche
superficie di riferimento, detenzione dell'intera unità, sistema catastale e ruolo P/U); con l'indice per ente anche
`ente_chiave`, `ente_settore`, `ente_macrocategoria` ed `ente_sede` (comune, provincia, regione) dell'ente dichiarante.

Ricerca per ente (22/11/2026; limite per IP «immobili_pa_ente» più un tetto orario per tutto il sito,
IMMOBILI_PA_ENTE_TETTO_ORA). L'ente si indica con la sua chiave (10 caratteri esadecimali derivati dal codice fiscale
nella fase 7; il codice fiscale non è nell'indice). Con un indice di prima del 22/11/2026 (senza tabella `enti`) le tre
rotte rispondono {"disponibile": false}, così l'ordine fra rilascio del sito e rifacimento dell'indice non conta.
  GET /api/immobili-pa/ente/{chiavi}?ruolo=proprieta,uso&natura=E,T
                                                  uno o più enti (chiavi separate da virgole, al massimo 8): dati
                                                  dell'ente, totali dichiarati, totali con i filtri, riquadro, totali per
                                                  comune; con più enti anche «insieme», calcolato sui beni distinti (un bene
                                                  dichiarato da due enti selezionati conta una volta)
  GET /api/immobili-pa/ente/{chiave}/punti        centri di tutte le particelle e dei beni senza particella con un punto
                                                  affidabile: {"campi": ["lon","lat","n","natura","ruolo","ref"], "righe":
                                                  […]}, una riga per particella, ruolo e natura (la pagina filtra da sé);
                                                  pesa 3 richieste; in copia nel browser per un giorno (ETag dell'indice)
  GET /api/immobili-pa/ente/{chiave}/beni?ruolo=&natura=&regione=&provincia=&comune=&ordina=sup_mq&verso=desc&pagina=1&per_pagina=100
                                                  elenco per particella (beni senza particella: una riga per bene) con il
                                                  numero di unità, paginato (al massimo 200 righe per pagina) e ordinato
                                                  su una lista chiusa di colonne (ORDINAMENTI)

Nell'indice non ci sono il soggetto cedente e il suo codice fiscale (possono essere persone fisiche) né il CF dell'ente:
nessuna rotta li restituisce (ESCLUSE, controllato nei test).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from . import config as C, protezione as P

router = APIRouter(prefix="/api/immobili-pa")

CAMPI_BENE = ("id_bene", "ref_ade", "aggancio", "natura", "tipologia", "amministrazione", "tipologia_amm", "gruppo",
              "regione", "provincia", "comune", "comune_cod", "indirizzo", "civico", "id_catastale", "lat", "lon",
              "geo_fonte", "superficie_mq", "cubatura_mc", "sup_pertinenze_mq", "epoca", "vincolo", "natura_giuridica",
              "titolo_proprieta", "quota_proprieta", "titolo_detenzione", "canone_annuo", "utilizzo", "finalita",
              "altra_finalita", "compendio", "tipologia_compendio", "a_terzi_intera", "a_terzi_parziale",
              # dal 22/11/2026 sera (scheda in sovraimpressione): già nell'indice rifatto il 22/11, prima non restituiti
              "sup_riferimento_mq", "detenzione_intera", "sistema_catastale", "ruolo")
RE_REF = re.compile(r"^[A-Z0-9_]{11}\.[A-Z0-9]{1,8}$")
RE_CHIAVE = re.compile(r"^[0-9a-f]{10}$")
ESCLUSE = ("amm_cf", "cedente", "cedente_cf")
MAX_ENTI = 8                       # enti insieme nella pagina (tavolozza di 8 colori)
PER_PAGINA_MAX = 200
PESO_PUNTI = 3
# colonne ordinabili dell'elenco per ente (lista chiusa: niente SQL composto dall'utente) → espressione SQL
ORDINAMENTI = {"regione": "c.regione", "provincia": "c.provincia", "comune": "c.comune", "indirizzo": "r.indirizzo",
               "tipologie": "r.tipologie", "n_beni": "r.n_beni", "sup_mq": "r.sup_mq", "area_m2": "r.area_m2",
               "epoca": "r.epoca", "utilizzo": "r.utilizzo", "titolo": "r.titolo", "ruoli": "r.ruoli"}
TESTUALI = {"regione", "provincia", "comune", "indirizzo", "tipologie", "epoca", "utilizzo", "titolo", "ruoli"}
RUOLI = {"proprieta": "P", "uso": "U"}
NATURE = {"E": "FABBRICATO", "T": "TERRENO"}


def cartella() -> Path:
    return Path(getattr(C, "CARTELLA_IMMOBILI_PA", None) or (C.DATI / "immobili_pa"))


def indice() -> Path | None:
    fs = sorted(cartella().glob("immobili_pa_*.sqlite"))
    return fs[-1] if fs else None


def _db() -> sqlite3.Connection:
    # una connessione per richiesta: quando la fase 7 sostituisce l'indice (file provvisorio `.…sqlite.nuovo`, che il
    # glob di indice() non vede, poi os.replace) le richieste già aperte finiscono sul file vecchio e le nuove leggono
    # quello nuovo; con immutable=1 non serve riavviare l'API (22/11/2026)
    f = indice()
    if not f:
        raise HTTPException(503, "Gli immobili delle PA non sono ancora sul server.")
    db = sqlite3.connect(f"file:{f}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def _ha_enti(db: sqlite3.Connection) -> bool:
    """L'indice ha le tabelle della ricerca per ente (fase 7 dal 22/11/2026)?"""
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='enti'").fetchone() is not None


def _chiavi_enti(db: sqlite3.Connection, ids) -> dict:
    """id dell'ente → dati pubblici dell'ente per la scheda (chiave, settore, macrocategoria, sede; mai il CF)."""
    ids = sorted({i for i in ids if isinstance(i, int)})
    if not ids or not _ha_enti(db):
        return {}
    righe = db.execute("SELECT id, chiave, settore, macrocategoria, sede_regione, sede_provincia, sede_comune FROM enti "
                       f"WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()
    return {r["id"]: r for r in righe}


def _colonne(db: sqlite3.Connection) -> list[str]:
    presenti = {r[1] for r in db.execute("PRAGMA table_info(beni)")}
    return [c for c in CAMPI_BENE if c in presenti]


def _bene(r: sqlite3.Row, col: list[str], chiavi: dict | None = None) -> dict:
    out = {c: r[c] for c in col if r[c] not in (None, "") and c not in ESCLUSE}
    if chiavi and "ente" in r.keys() and r["ente"] in chiavi:
        e = chiavi[r["ente"]]
        out["ente_chiave"] = e["chiave"]
        # classificazione e sede dell'ente dichiarante (campi MEF pubblicati, nella tabella enti: 22/11/2026 sera)
        for k, v in (("ente_settore", e["settore"]), ("ente_macrocategoria", e["macrocategoria"])):
            if v not in (None, ""):
                out[k] = v
        sede = {k: e[f"sede_{k}"] for k in ("comune", "provincia", "regione") if e[f"sede_{k}"] not in (None, "")}
        if sede:
            out["ente_sede"] = sede
    return out


def _con_ente(db: sqlite3.Connection, col: list[str]) -> str:
    """Colonne da leggere: quelle pubbliche più `ente` (solo per ricavare la chiave, non esce)."""
    presenti = {r[1] for r in db.execute("PRAGMA table_info(beni)")}
    return ", ".join(col + (["ente"] if "ente" in presenti else []))


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
        righe = db.execute(f"SELECT {_con_ente(db, col)} FROM beni WHERE ref_ade = ? LIMIT 500", [ref]).fetchall()
        ch = _chiavi_enti(db, [r["ente"] for r in righe if "ente" in r.keys()])
        beni = [_bene(r, col, ch) for r in righe]
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
        # tutte le dichiarazioni dello stesso bene (proprietario e detentore, 22/11/2026): prima c'era solo la prima
        righe = db.execute(f"SELECT {_con_ente(db, col)} FROM beni WHERE id_bene = ? LIMIT 50", [id_bene]).fetchall()
        ch = _chiavi_enti(db, [r["ente"] for r in righe if "ente" in r.keys()])
    finally:
        db.close()
    if not righe:
        raise HTTPException(404, "Bene non trovato.")
    tutte = [_bene(r, col, ch) for r in righe]
    return {"bene": tutte[0], "dichiarazioni": tutte}


# --------------------------------------------------------------------------------------------- ricerca per ente
def _limita_ente(req: Request, peso: int = 1) -> None:
    P.limita(req, "immobili_pa_ente", peso)
    if not P.tetto_globale("immobili_pa_ente", C.IMMOBILI_PA_ENTE_TETTO_ORA, peso):
        raise HTTPException(503, "Troppe richieste di elenchi per ente da tutto il sito in quest'ora: riprova tra un po'.")


def _filtri(ruolo: str, natura: str) -> tuple[list[str], list[str]]:
    """Ruoli (P, U) e nature (E, T) scelti; vuoto = tutti. 400 se un valore non è tra quelli previsti."""
    def lista(v, ammessi, nome):
        if not (v or "").strip():
            return list(ammessi.values()) if nome == "ruolo" else list(ammessi)
        out = []
        for x in v.split(","):
            x = x.strip()
            k = x.lower() if nome == "ruolo" else x.upper()
            if k not in ammessi:
                raise HTTPException(400, f"Valore non valido per {nome}: {x[:20]}")
            out.append(ammessi[k] if nome == "ruolo" else k)
        return sorted(set(out))
    return lista(ruolo, RUOLI, "ruolo"), lista(natura, NATURE, "natura")


def _enti_da_chiavi(db: sqlite3.Connection, chiavi: str, massimo: int) -> list[sqlite3.Row]:
    ks = [k.strip().lower() for k in (chiavi or "").split(",") if k.strip()]
    if not ks or len(ks) > massimo or not all(RE_CHIAVE.match(k) for k in ks):
        raise HTTPException(400, f"Chiave dell'ente non valida (10 caratteri esadecimali, al massimo {massimo} separate da virgole).")
    ks = list(dict.fromkeys(ks))
    righe = {r["chiave"]: r for r in db.execute(f"SELECT * FROM enti WHERE chiave IN ({','.join('?' * len(ks))})", ks)}
    mancanti = [k for k in ks if k not in righe]
    if mancanti:
        raise HTTPException(404, f"Ente non trovato: {', '.join(mancanti)}.")
    return [righe[k] for k in ks]


_TOTALI_SQL = ("COUNT(*) AS n_beni, SUM(natura = 'FABBRICATO') AS n_fabbricati, SUM(natura = 'TERRENO') AS n_terreni, "
               "SUM(CASE WHEN natura = 'FABBRICATO' THEN sup ELSE 0 END) AS sup_fabbricati_mq, "
               "SUM(CASE WHEN natura = 'TERRENO' THEN sup ELSE 0 END) AS sup_terreni_mq, "
               "SUM(utilizzo = 'Non utilizzato') AS n_non_utilizzati, SUM(utilizzo = 'Inutilizzabile') AS n_inutilizzabili, "
               "SUM(COALESCE(vincolo, '') NOT IN ('', 'Nessuno', 'ND')) AS n_vincolati, SUM(ruolo = 'U') AS n_detenzione, "
               "COUNT(DISTINCT NULLIF(comune_cod, '')) AS n_comuni")
_SUP = "COALESCE(NULLIF(superficie_mq, 0), NULLIF(sup_riferimento_mq, 0), 0)"


def _totali(db, ids: list[int], ruoli: list[str], nature: list[str]) -> dict:
    """Totali sui beni distinti degli enti `ids` con i filtri (un bene dichiarato da più enti conta una volta)."""
    qi, qr, qn = ",".join("?" * len(ids)), ",".join("?" * len(ruoli)), ",".join("?" * len(nature))
    arg = [*ids, *ruoli, *[NATURE[n] for n in nature]]
    # per ogni bene distinto: natura, superficie, utilizzo, vincolo e comune della prima dichiarazione; «in uso» se
    # nessuno degli enti scelti lo ha in proprietà
    r = db.execute(
        f"SELECT {_TOTALI_SQL} FROM (SELECT id_bene, MIN(natura) AS natura, MAX({_SUP}) AS sup, MIN(utilizzo) AS utilizzo, "
        f"MIN(vincolo) AS vincolo, MIN(ruolo) AS ruolo, MIN(comune_cod) AS comune_cod FROM beni "
        f"WHERE ente IN ({qi}) AND ruolo IN ({qr}) AND natura IN ({qn}) GROUP BY id_bene)", arg).fetchone()
    out = {k: (round(r[k]) if isinstance(r[k], float) else (r[k] or 0)) for k in r.keys()}
    p = db.execute(f"SELECT COUNT(DISTINCT ref) FROM ente_particelle WHERE ente IN ({qi}) AND ruolo IN ({qr}) "
                   f"AND natura IN ({qn}) AND ref NOT LIKE 'b%'", [*ids, *ruoli, *nature]).fetchone()[0]
    out["n_particelle"] = p or 0
    return out


CAMPI_ENTE = ("chiave", "nome", "tipologia_amm", "gruppo", "settore", "macrocategoria")
TOTALI_DICHIARATI = ("n_beni", "n_fabbricati", "n_terreni", "n_particelle", "n_senza_particella", "sup_fabbricati_mq",
                     "sup_terreni_mq", "cubatura_mc", "area_particelle_m2", "n_proprieta", "n_detenzione", "n_non_utilizzati",
                     "n_inutilizzabili", "n_vincolati", "n_a_terzi", "epoca_prevalente", "n_regioni", "n_comuni")


@router.get("/ente/{chiavi}")
def ente(req: Request, chiavi: str, ruolo: str = "", natura: str = ""):
    _limita_ente(req)
    ruoli, nature = _filtri(ruolo, natura)
    db = _db()
    try:
        if not _ha_enti(db):
            return {"disponibile": False}
        righe = _enti_da_chiavi(db, chiavi, MAX_ENTI)
        qr, qn = ",".join("?" * len(ruoli)), ",".join("?" * len(nature))
        out = []
        for e in righe:
            d = {k: e[k] for k in CAMPI_ENTE}
            d["id"] = e["id"]
            d["sede"] = {"regione": e["sede_regione"], "provincia": e["sede_provincia"], "comune": e["sede_comune"]}
            d["totali_dichiarati"] = {k: e[k] for k in TOTALI_DICHIARATI}
            d["riquadro"] = [e["ovest"], e["sud"], e["est"], e["nord"]] if e["ovest"] is not None else None
            d["totali"] = _totali(db, [e["id"]], ruoli, nature)
            d["comuni"] = [dict(r) for r in db.execute(
                "SELECT ep.comune_cod, c.comune, c.provincia, c.regione, COUNT(DISTINCT CASE WHEN ep.ref NOT LIKE 'b%' "
                "THEN ep.ref END) AS n_particelle, COUNT(DISTINCT ep.ref) AS n_righe, SUM(ep.n_beni) AS n_beni, "
                "ROUND(SUM(ep.sup_mq)) AS sup_mq FROM ente_particelle ep LEFT JOIN comuni c ON c.comune_cod = ep.comune_cod "
                f"WHERE ep.ente = ? AND ep.ruolo IN ({qr}) AND ep.natura IN ({qn}) GROUP BY ep.comune_cod "
                "ORDER BY c.regione, c.comune LIMIT 3000", [e["id"], *ruoli, *nature])]
            out.append(d)
        risposta = {"disponibile": True, "enti": out, "filtri": {"ruolo": ruoli, "natura": nature}}
        if len(righe) > 1:
            risposta["insieme"] = _totali(db, [e["id"] for e in righe], ruoli, nature)
    finally:
        db.close()
    return risposta


def _etag() -> str:
    f = indice()
    st = f.stat() if f else None
    return f'"pa-{st.st_mtime_ns:x}-{st.st_size:x}"' if st else '"pa-0"'


@router.get("/ente/{chiave}/punti")
def ente_punti(req: Request, chiave: str):
    tag = _etag()
    if req.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers={"ETag": tag})
    _limita_ente(req, PESO_PUNTI)
    db = _db()
    try:
        if not _ha_enti(db):
            return {"disponibile": False}
        e = _enti_da_chiavi(db, chiave, 1)[0]
        righe = [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in db.execute(
            "SELECT ROUND(lon, 5), ROUND(lat, 5), n_beni, natura, ruolo, ref FROM ente_particelle "
            "WHERE ente = ? AND lon IS NOT NULL", [e["id"]])]
    finally:
        db.close()
    corpo = {"disponibile": True, "chiave": e["chiave"], "id": e["id"], "campi": ["lon", "lat", "n", "natura", "ruolo", "ref"],
             "righe": righe}
    return JSONResponse(corpo, headers={"ETag": tag, "Cache-Control": "public, max-age=86400"})


@router.get("/ente/{chiave}/beni")
def ente_beni(req: Request, chiave: str, ruolo: str = "", natura: str = "", regione: str = "", provincia: str = "",
              comune: str = "", ordina: str = "", verso: str = "asc", pagina: int = 1, per_pagina: int = 100):
    _limita_ente(req)
    ruoli, nature = _filtri(ruolo, natura)
    if ordina and ordina not in ORDINAMENTI:
        raise HTTPException(400, f"Ordinamento non previsto: si può ordinare per {', '.join(ORDINAMENTI)}.")
    if verso not in ("asc", "desc"):
        raise HTTPException(400, "Verso dell'ordinamento: asc o desc.")
    if comune and not re.fullmatch(r"[A-Za-z0-9]{4}", comune):
        raise HTTPException(400, "Codice catastale del comune non valido.")
    per_pagina = max(1, min(int(per_pagina), PER_PAGINA_MAX))
    pagina = max(1, int(pagina))
    db = _db()
    try:
        if not _ha_enti(db):
            return {"disponibile": False}
        e = _enti_da_chiavi(db, chiave, 1)[0]
        dove = [f"ep.ente = ?", f"ep.ruolo IN ({','.join('?' * len(ruoli))})", f"ep.natura IN ({','.join('?' * len(nature))})"]
        arg: list = [e["id"], *ruoli, *nature]
        if comune:
            dove.append("ep.comune_cod = ?"); arg.append(comune.upper())
        for campo, v in (("regione", regione), ("provincia", provincia)):
            if v.strip():
                dove.append(f"ep.comune_cod IN (SELECT comune_cod FROM comuni WHERE {campo} = ?)"); arg.append(v.strip()[:60])
        w = " AND ".join(dove)
        totale = db.execute(f"SELECT COUNT(DISTINCT ep.ref) FROM ente_particelle ep WHERE {w}", arg).fetchone()[0]
        if ordina:
            espr = ORDINAMENTI[ordina]
            vuoto = f"({espr} IS NULL OR {espr} = '')" if ordina in TESTUALI else f"({espr} IS NULL)"
            ordine = f"{vuoto}, {espr} {'DESC' if verso == 'desc' else 'ASC'}, r.ref"
        else:
            ordine = "c.regione, c.comune, r.indirizzo = '', r.indirizzo, r.ref"        # ordine di partenza
        sql = ("SELECT r.*, c.comune, c.provincia, c.regione FROM (SELECT ep.ref, MIN(ep.lon) AS lon, MIN(ep.lat) AS lat, "
               "SUM(ep.n_beni) AS n_beni, SUM(CASE WHEN ep.natura = 'E' THEN ep.n_beni ELSE 0 END) AS n_fabbricati, "
               "SUM(CASE WHEN ep.natura = 'T' THEN ep.n_beni ELSE 0 END) AS n_terreni, ROUND(SUM(ep.sup_mq), 1) AS sup_mq, "
               "MAX(ep.area_m2) AS area_m2, MAX(ep.comune_cod) AS comune_cod, MAX(ep.indirizzo) AS indirizzo, "
               "GROUP_CONCAT(NULLIF(ep.tipologie, ''), ' · ') AS tipologie, MAX(ep.epoca) AS epoca, "
               "MAX(ep.utilizzo) AS utilizzo, MAX(ep.titolo) AS titolo, GROUP_CONCAT(DISTINCT ep.ruolo) AS ruoli "
               f"FROM ente_particelle ep WHERE {w} GROUP BY ep.ref) r LEFT JOIN comuni c ON c.comune_cod = r.comune_cod "
               f"ORDER BY {ordine} LIMIT ? OFFSET ?")
        righe = [{k: r[k] for k in r.keys() if r[k] not in (None, "")}
                 for r in db.execute(sql, [*arg, per_pagina, (pagina - 1) * per_pagina])]
    finally:
        db.close()
    return {"disponibile": True, "chiave": e["chiave"], "totale": totale, "pagina": pagina, "per_pagina": per_pagina,
            "pagine": max(1, -(-totale // per_pagina)), "ordina": ordina or None, "verso": verso if ordina else None,
            "righe": righe}
