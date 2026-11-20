"""«Stato della rete elettrica» e «Cabine primarie» (17/11/2026, contratto comune dei tre agenti).

Database SQLite in C.RETE_DB (sul server /srv/energia/dati/rete/rete.sqlite), scritto **solo dal worker**:
  * interruzioni ogni C.RETE_INTERRUZIONI_MIN minuti (15) dallo strato pubblico di e-distribuzione
    `ITA_power_cut_map_layer_View/FeatureServer/0` (`raccogli_interruzioni`): una riga per `id_interruzione` con
    prima e ultima lettura in cui compare e `chiusa_il` (prima lettura completa in cui non compare più), più una riga
    per cabina secondaria (`cod_cs`) coinvolta; clienti = massimo visto. Date «gg/mm/aaaa HH:MM» in ora italiana → ISO.
    Durata stimata = ultima lettura in cui compare − `data_interruzione` (dichiarata nelle risposte).
  * saturazione ogni notte (`aggiorna_saturazione`): `comuniServiti` di e-distribuzione per tutte le province
    (gettone nuovo per ogni chiamata, intestazioni Origin/Referer, pausa ≥ 4 s, chi fallisce si ritenta alla fine;
    **il gettone non viene mai registrato**), `ProvinceCritiche_View` (elenco province) e `View_ComuniGestitiED2021Is`
    (`servitoed`: comuni dove il distributore è un altro). Una fotografia per mese e provincia (l'ultima del mese).
Letture: rotte /api/rete/… (in fondo al file) e la tabella di raccordo C.RETE_RACCORDO (`raccordo_cp.csv` dell'agente
DATI: posizioni OSM → ODbL, `COD_AC` del GSE, gestore). Nessuna geometria del GSE passa dal server.
Servizio delle aree convenzionali del GSE (`URL_GSE_AREE`, 20/11/2026): letto solo dal browser; qui il controllo mensile
del worker (`controlla_servizio_gse`, una richiesta ?f=json, nessun dato salvato).

Criticità del comune: `classe_comune` (regola del contratto; copia identica di `fase7-territorio/territorio/cabine.py`,
da unificare al merge).

  python -m servizio.worker rete-interruzioni | rete-saturazione      una sola esecuzione
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import re
import sqlite3
import threading
import time
import unicodedata
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import config as C, protezione as P

log = logging.getLogger("rete")
ROMA = ZoneInfo("Europe/Rome")

# ---------------------------------------------------------------------------------------------- fonti (un solo punto)
ARCGIS = "https://dpa-portalgis.enel.com/server/rest/services/Hosted"
URL_INTERRUZIONI = f"{ARCGIS}/ITA_power_cut_map_layer_View/FeatureServer/0/query"
URL_PROVINCE = f"{ARCGIS}/ProvinceCritiche_View/FeatureServer/0/query"
URL_COMUNI_ED = f"{ARCGIS}/View_ComuniGestitiED2021Is/FeatureServer/0/query"
PAGINA_AREE = "https://www.e-distribuzione.it/a-chi-ci-rivolgiamo/produttori/aree-critiche.html"
URL_GETTONE = "https://www.e-distribuzione.it/content/e-distribuzione/it/homepage/_jcr_content.tokenservice.html"
URL_COMUNI_SERVITI = "https://xs-portale-pubblico-api-mngmt.de-c1.eu1.cloudhub.io/v1/precar/determina40/comuniServiti"
INTESTAZIONI = {"User-Agent": "EuGEnio/1.0 (+https://eugenio.statocritico.it) - stato della rete elettrica",
                "Origin": "https://www.e-distribuzione.it", "Referer": PAGINA_AREE}
# (20/11/2026) servizio pubblico del GSE con le aree convenzionali delle cabine primarie (strato 0 = AC_2025): i perimetri
# li legge SOLO il browser dell'utente (rete.js, GSE.SERVIZIO, stesso indirizzo); qui serve solo al controllo mensile del
# worker (`controlla_servizio_gse`). Quando il GSE pubblicherà AC_Comuni_2027 il nome cambierà: va cambiato qui e in rete.js.
URL_GSE_AREE = "https://services-eu1.arcgis.com/sawHMGY9o8rHlY2j/arcgis/rest/services/AC_Comuni_2025/FeatureServer"
PAGINA_GSE_AREE = "https://www.gse.it/servizi-per-te/autoconsumo/mappa-interattiva-delle-cabine-primarie"
PAGINA_ARCGIS = 1000          # maxRecordCount degli strati e-distribuzione
MIN_COMUNI_ED = 1000          # sotto questa soglia la lettura dei comuni gestiti è incompleta: si tiene quella di prima

CAMPI_INTERRUZIONI = ("id_interruzione", "cod_cs", "latitudine", "longitudine", "comune", "provincia", "regione",
                      "descrizione_territoriale", "causa_disalimentazione", "causa_interruzione", "num_cli_disalim",
                      "data_interruzione", "data_prev_ripristino", "dataultimoaggiornamento", "cft", "note")

FONTE_ED = "Fonte: e-distribuzione S.p.A., mappa delle Aree critiche e mappa delle interruzioni"
LICENZE = {
    "e-distribuzione": {
        "attribuzione": FONTE_ED,
        "condizioni": "dati pubblici di e-distribuzione S.p.A. riproposti per uso non commerciale, con la fonte "
                      "citata; rimossi su richiesta del titolare",
        "url": [PAGINA_AREE, "https://www.e-distribuzione.it/mappa-interruzioni.html"]},
    "posizioni_cabine": {
        "attribuzione": "© contributori OpenStreetMap",
        "licenza": "ODbL 1.0 – https://opendatacommons.org/licenses/odbl/1-0/",
        "nota": "posizioni delle cabine primarie dalle sottostazioni OpenStreetMap (tabella di raccordo di EuGEnio)"},
    "codici_gse": {
        "attribuzione": "Codici delle aree convenzionali (COD_AC): GSE S.p.A., mappa interattiva delle cabine primarie",
        "nota": "solo i codici: i perimetri delle aree non passano dal server di EuGEnio"},
    "classificazione": {
        "attribuzione": "Criticità dei comuni: classificazione di EuGEnio sui livelli dei trasformatori di "
                        "e-distribuzione"},
}
NOTA_IN_PARTE = "servito in parte da un altro distributore"
REGOLA = ("Classificazione di EuGEnio: L = livello più alto tra i trasformatori che servono il comune (VERDE < GIALLO < "
          "ARANCIONE < ROSSO), q = quota dei trasformatori con livello L. L = VERDE: nessun riempimento; q > 0,5: colore "
          "pieno di L; altrimenti strisce tra il livello precedente e L (VERDE si disegna bianco).")
NOTA_DURATA = ("Durata stimata = ultima lettura in cui l'interruzione compare sulla mappa di e-distribuzione (letta ogni "
               f"{C.RETE_INTERRUZIONI_MIN} minuti) − data di inizio dichiarata: errore fino a una lettura.")

# ---------------------------------------------------------------------------------------------- regola (contratto)
LIVELLI = ("VERDE", "GIALLO", "ARANCIONE", "ROSSO")


def classe_comune(conteggi: dict) -> dict:
    """Criticità di un comune dai conteggi dei suoi trasformatori per livello (regola del contratto del 17/11/2026).
    Identica a `territorio.cabine.classe_comune` (fase 7): da unificare al merge."""
    c = {l: 0 for l in LIVELLI}
    for k, v in (conteggi or {}).items():
        k = str(k).strip().upper()
        if k in c:
            c[k] += int(v or 0)
    tot = sum(c.values())
    if tot <= 0:
        return {"livello": None, "quota": None, "pieno": None, "strisce": None}
    L = max((l for l in LIVELLI if c[l] > 0), key=LIVELLI.index)
    q = c[L] / tot
    out = {"livello": L, "quota": round(q, 3), "pieno": None, "strisce": None}
    if L == "VERDE":
        return out
    if q > 0.5:
        out["pieno"] = L
    else:
        out["strisce"] = [LIVELLI[LIVELLI.index(L) - 1], L]
    return out


def livello_cabina(conteggi: dict) -> str | None:
    """Livello peggiore tra i trasformatori della cabina; None senza dato (grigio sulla mappa)."""
    presenti = [l for l in LIVELLI if int((conteggi or {}).get(l) or 0) > 0]
    return presenti[-1] if presenti else None


def _livello(x) -> str | None:
    x = str(x or "").strip().upper()
    return x if x in LIVELLI else None


# ---------------------------------------------------------------------------------------------- database
SCHEMA_VERSIONE = 1
_SCHEMA = {1: """
CREATE TABLE IF NOT EXISTS meta (chiave TEXT PRIMARY KEY, valore TEXT);
CREATE TABLE IF NOT EXISTS province (
    cod TEXT PRIMARY KEY, nome TEXT, regione_cod TEXT, regione TEXT,
    livello_criticita INTEGER, livello_criticita2 INTEGER, letto_il TEXT);
CREATE TABLE IF NOT EXISTS comuni_ed (
    istat_2021 TEXT PRIMARY KEY, istat TEXT, nome TEXT, cod_prov TEXT, regione_cod TEXT, servitoed INTEGER,
    letto_il TEXT);
CREATE INDEX IF NOT EXISTS comuni_ed_istat ON comuni_ed (istat);
CREATE TABLE IF NOT EXISTS saturazione (
    mese TEXT, provincia TEXT, comune TEXT, comune_nome TEXT, cod_cp TEXT, nome_cp TEXT, cod_trasf TEXT,
    cod_montante TEXT, id_sezione TEXT, livello TEXT, letto_il TEXT,
    PRIMARY KEY (mese, comune, cod_cp, cod_trasf, cod_montante, id_sezione));
CREATE INDEX IF NOT EXISTS saturazione_prov ON saturazione (provincia, mese);
CREATE INDEX IF NOT EXISTS saturazione_cp ON saturazione (cod_cp);
CREATE TABLE IF NOT EXISTS saturazione_province (
    mese TEXT, provincia TEXT, letto_il TEXT, n_comuni INTEGER, n_righe INTEGER, PRIMARY KEY (mese, provincia));
CREATE TABLE IF NOT EXISTS tentativi_province (
    provincia TEXT PRIMARY KEY, ultimo_tentativo TEXT, esito TEXT, errore TEXT, ultimo_ok TEXT, in_errore_dal TEXT);
CREATE TABLE IF NOT EXISTS interruzioni (
    id_interruzione INTEGER PRIMARY KEY, causa_disalimentazione TEXT, causa_interruzione TEXT,
    data_interruzione TEXT, data_prev_ripristino TEXT, prev_ripristino_testo TEXT, descrizione_territoriale TEXT,
    provincia TEXT, area TEXT, comune TEXT, comuni TEXT, lat REAL, lon REAL, num_cli_disalim INTEGER, n_cs INTEGER,
    cft TEXT, note TEXT, aggiornato_fonte TEXT, prima_lettura TEXT, ultima_lettura TEXT, chiusa_il TEXT);
CREATE INDEX IF NOT EXISTS interruzioni_aperte ON interruzioni (chiusa_il);
CREATE INDEX IF NOT EXISTS interruzioni_inizio ON interruzioni (data_interruzione);
CREATE TABLE IF NOT EXISTS interruzioni_cs (
    id_interruzione INTEGER, cod_cs TEXT, comune TEXT, lat REAL, lon REAL, num_cli_disalim INTEGER,
    descrizione_territoriale TEXT, prima_lettura TEXT, ultima_lettura TEXT, PRIMARY KEY (id_interruzione, cod_cs));
CREATE INDEX IF NOT EXISTS interruzioni_cs_comune ON interruzioni_cs (comune);
CREATE TABLE IF NOT EXISTS letture (
    quando TEXT PRIMARY KEY, esito TEXT, righe INTEGER, interruzioni INTEGER, nuove INTEGER, chiuse INTEGER,
    durata_s REAL, errore TEXT);
"""}
_blocco_schema = threading.Lock()


def connetti(percorso: Path | None = None, scrittura: bool = True) -> sqlite3.Connection:
    """Connessione al database; in scrittura crea cartella, file e schema (versione in PRAGMA user_version)."""
    p = Path(percorso or C.RETE_DB)
    if not scrittura and not p.exists():
        raise FileNotFoundError(p)
    if scrittura:
        p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=30, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=30000")
    if scrittura:
        with _blocco_schema:
            prepara_schema(db)
    else:
        db.execute("PRAGMA query_only=1")
    return db


def prepara_schema(db: sqlite3.Connection) -> int:
    v = db.execute("PRAGMA user_version").fetchone()[0]
    if v > SCHEMA_VERSIONE:
        raise RuntimeError(f"database della rete in versione {v}, il codice conosce fino alla {SCHEMA_VERSIONE}")
    if v < SCHEMA_VERSIONE:
        db.execute("PRAGMA journal_mode=WAL")       # il worker scrive mentre l'api legge
        for n in range(v + 1, SCHEMA_VERSIONE + 1):
            db.executescript(_SCHEMA[n])
            db.execute(f"PRAGMA user_version={n}")
            log.info("Database della rete: schema alla versione %d", n)
    return SCHEMA_VERSIONE


@contextmanager
def transazione(db: sqlite3.Connection):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    db.execute("COMMIT")


def _meta(db, chiave, valore=None):
    if valore is None:
        r = db.execute("SELECT valore FROM meta WHERE chiave=?", (chiave,)).fetchone()
        return r[0] if r else None
    db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (chiave, str(valore)))


def adesso() -> dt.datetime:
    return dt.datetime.now(ROMA).replace(microsecond=0)


def iso(t: dt.datetime) -> str:
    return t.astimezone(ROMA).replace(microsecond=0).isoformat()


def data_it(testo) -> str | None:
    """«17/11/2026 14:00» in ora italiana → «2026-11-17T14:00:00+01:00»; None se non è una data
    (es. «In corso di definizione»)."""
    if not testo or not isinstance(testo, str):
        return None
    try:
        d = dt.datetime.strptime(testo.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        return None
    return d.replace(tzinfo=ROMA).isoformat()


def _minuti(da: str | None, a: str | None) -> int | None:
    if not da or not a:
        return None
    try:
        return max(0, int(round((dt.datetime.fromisoformat(a) - dt.datetime.fromisoformat(da)).total_seconds() / 60)))
    except ValueError:
        return None


def _istat6(x) -> str | None:
    if x is None or x == "":
        return None
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(6) if s.isdigit() and int(s) > 0 else None


def _norm(nome) -> str:
    s = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


# ---------------------------------------------------------------------------------------------- anagrafica comuni
@lru_cache(maxsize=2)
def _anagrafica_file(percorso: str, mtime: float) -> dict:
    import pandas as pd
    try:
        t = pd.read_parquet(percorso)
    except Exception:
        return {}
    col = [c for c in ("istat", "nome", "regione_cod", "provincia") if c in t.columns]
    if "istat" not in col:
        return {}
    t = t[col].astype(object).where(t[col].notna(), None)
    return {str(r["istat"]).zfill(6): {"nome": r.get("nome"), "regione_cod": (str(r["regione_cod"]).zfill(2)
                                                                            if r.get("regione_cod") else None)}
            for r in t.to_dict(orient="records")}


def anagrafica() -> dict:
    """ISTAT attuale → {nome, regione_cod} da DATI/comuni.parquet (tutti i comuni, fase 3); {} se manca."""
    p = C.DATI / "comuni.parquet"
    try:
        m = p.stat().st_mtime
    except OSError:
        return {}
    return _anagrafica_file(str(p), m)


def _regioni_province(db) -> dict:
    return {r["cod"]: r["regione_cod"] for r in db.execute("SELECT cod, regione_cod FROM province")}


def regione_di(istat: str | None, ana: dict, prov: dict) -> str | None:
    if not istat:
        return None
    a = ana.get(istat)
    if a and a.get("regione_cod"):
        return a["regione_cod"]
    return prov.get(istat[:3])


# ---------------------------------------------------------------------------------------------- client HTTP
def client(**kw) -> httpx.Client:
    return httpx.Client(headers=INTESTAZIONI, timeout=60, follow_redirects=True, **kw)


def controlla_servizio_gse(cl: httpx.Client | None = None) -> dict:
    """(20/11/2026) Il servizio delle aree convenzionali del GSE risponde? Una sola richiesta `URL_GSE_AREE?f=json`
    (descrizione del FeatureServer, nessun dato delle aree), niente salvato. Solleva RuntimeError se non risponde, se
    risponde con un errore ArcGIS o se lo strato 0 non c'è più (es. servizio rinominato in AC_Comuni_2027)."""
    proprio = cl is None
    cl = cl or httpx.Client(headers={"User-Agent": INTESTAZIONI["User-Agent"]}, timeout=30, follow_redirects=True)
    try:
        try:
            r = cl.get(URL_GSE_AREE, params={"f": "json"})
        except httpx.HTTPError as e:
            raise RuntimeError(f"servizio del GSE non raggiungibile: {type(e).__name__}: {e}") from e
        if r.status_code != 200:
            raise RuntimeError(f"servizio del GSE: HTTP {r.status_code}")
        try:
            j = r.json()
        except ValueError as e:
            raise RuntimeError("servizio del GSE: risposta non JSON") from e
        if not isinstance(j, dict) or j.get("error"):
            err = j.get("error") if isinstance(j, dict) else None
            raise RuntimeError(f"servizio del GSE: errore {((err or {}).get('code'))} {((err or {}).get('message') or '')}".strip())
        strati = {x.get("id"): x.get("name") for x in (j.get("layers") or []) if isinstance(x, dict)}
        if 0 not in strati:
            raise RuntimeError(f"servizio del GSE: manca lo strato 0 delle aree convenzionali (strati: {strati})")
        return {"ok": True, "servizio": URL_GSE_AREE, "strato_0": strati[0], "strati": len(strati)}
    finally:
        if proprio:
            cl.close()


def _arcgis_tutto(cl: httpx.Client, url: str, params: dict) -> list[dict]:
    """Tutte le righe di uno strato ArcGIS a pagine (resultOffset); solleva se una pagina dà errore."""
    righe, offset = [], 0
    while True:
        q = {"f": "json", "returnGeometry": "false", "resultOffset": offset, "resultRecordCount": PAGINA_ARCGIS,
             **params}
        r = cl.get(url, params=q)
        r.raise_for_status()
        j = r.json()
        if "error" in j:
            raise RuntimeError(f"ArcGIS: {j['error'].get('code')} {j['error'].get('message')}")
        f = j.get("features") or []
        righe += [x.get("attributes") or {} for x in f]
        if not j.get("exceededTransferLimit") or not f:
            return righe
        offset += len(f)
        if offset > 200_000:
            raise RuntimeError("ArcGIS: troppe pagine")


# ---------------------------------------------------------------------------------------------- interruzioni
def raccogli_interruzioni(cl: httpx.Client | None = None, ora: dt.datetime | None = None,
                          percorso: Path | None = None) -> dict:
    """Una lettura completa delle interruzioni in corso: aggiorna le righe viste, chiude quelle sparite."""
    ora = ora or adesso()
    quando = iso(ora)
    t0 = time.monotonic()
    proprio = cl is None
    cl = cl or client()
    db = connetti(percorso)
    try:
        try:
            righe = _arcgis_tutto(cl, URL_INTERRUZIONI, {"where": "1=1", "outFields": ",".join(CAMPI_INTERRUZIONI),
                                                         "orderByFields": "objectid1"})
        except Exception as e:
            with transazione(db):
                db.execute("INSERT OR REPLACE INTO letture VALUES (?, 'errore', NULL, NULL, NULL, NULL, ?, ?)",
                           (quando, time.monotonic() - t0, f"{type(e).__name__}: {e}"[:500]))
            raise
        esito = _registra_interruzioni(db, righe, quando)
        esito["durata_s"] = round(time.monotonic() - t0, 1)
        with transazione(db):
            db.execute("INSERT OR REPLACE INTO letture VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                       (quando, esito["esito"], esito["righe"], esito["interruzioni"], esito["nuove"],
                        esito["chiuse"], esito["durata_s"]))
            if esito["esito"] == "ok":
                _meta(db, "interruzioni_aggiornate", quando)
            if _meta(db, "raccolta_dal") is None:
                _meta(db, "raccolta_dal", quando)
            # registro delle letture: basta poco più di un anno
            limite = iso(ora - dt.timedelta(days=400))
            db.execute("DELETE FROM letture WHERE quando < ?", (limite,))
        log.info("Interruzioni: %s", esito)
        return esito
    finally:
        db.close()
        if proprio:
            cl.close()


def _registra_interruzioni(db: sqlite3.Connection, righe: list[dict], quando: str) -> dict:
    gruppi: dict[int, list[dict]] = {}
    for r in righe:
        try:
            i = int(r.get("id_interruzione"))
        except (TypeError, ValueError):
            continue
        gruppi.setdefault(i, []).append(r)
    aperte_prima = db.execute("SELECT COUNT(*) FROM interruzioni WHERE chiusa_il IS NULL").fetchone()[0]
    # nessuna riga mentre ne erano aperte molte: più probabile un guasto della fonte che un'Italia senza interruzioni
    sospetta = not gruppi and aperte_prima >= 10
    nuove = 0
    with transazione(db):
        for i, gr in gruppi.items():
            nuove += _registra_una(db, i, gr, quando)
        chiuse = 0
        if not sospetta:
            visti = set(gruppi)
            aperte = [r[0] for r in db.execute("SELECT id_interruzione FROM interruzioni WHERE chiusa_il IS NULL")]
            da_chiudere = [i for i in aperte if i not in visti]
            db.executemany("UPDATE interruzioni SET chiusa_il=? WHERE id_interruzione=?",
                           [(quando, i) for i in da_chiudere])
            chiuse = len(da_chiudere)
    return {"esito": "sospetta" if sospetta else "ok", "righe": len(righe), "interruzioni": len(gruppi),
            "nuove": nuove, "chiuse": chiuse}


def _registra_una(db, i: int, gr: list[dict], quando: str) -> int:
    for r in gr:
        cs = str(r.get("cod_cs") or "").strip() or "?"
        n = int(r.get("num_cli_disalim") or 0)
        db.execute("""INSERT INTO interruzioni_cs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id_interruzione, cod_cs) DO UPDATE SET comune=excluded.comune, lat=excluded.lat,
              lon=excluded.lon, num_cli_disalim=MAX(num_cli_disalim, excluded.num_cli_disalim),
              descrizione_territoriale=excluded.descrizione_territoriale, ultima_lettura=excluded.ultima_lettura""",
                   (i, cs, _istat6(r.get("comune")), r.get("latitudine"), r.get("longitudine"), n,
                    r.get("descrizione_territoriale"), quando, quando))
    princ = max(gr, key=lambda r: int(r.get("num_cli_disalim") or 0))
    clienti = sum(int(r.get("num_cli_disalim") or 0) for r in gr)
    inizi = [d for d in (data_it(r.get("data_interruzione")) for r in gr) if d]
    inizio = min(inizi, key=dt.datetime.fromisoformat) if inizi else None
    prev = [d for d in (data_it(r.get("data_prev_ripristino")) for r in gr) if d]
    prev_iso = max(prev, key=dt.datetime.fromisoformat) if prev else None
    prev_testo = None if prev_iso else (str(princ.get("data_prev_ripristino") or "").strip() or None)
    comuni = {c for c in (_istat6(r.get("comune")) for r in gr) if c}
    ex = db.execute("SELECT comuni, data_interruzione, num_cli_disalim, n_cs FROM interruzioni WHERE id_interruzione=?",
                    (i,)).fetchone()
    if ex:
        comuni |= set(filter(None, (ex["comuni"] or "").split(";")))
        if ex["data_interruzione"] and (not inizio or dt.datetime.fromisoformat(ex["data_interruzione"])
                                        < dt.datetime.fromisoformat(inizio)):
            inizio = ex["data_interruzione"]
        clienti = max(clienti, ex["num_cli_disalim"] or 0)
    n_cs = db.execute("SELECT COUNT(*) FROM interruzioni_cs WHERE id_interruzione=?", (i,)).fetchone()[0]
    valori = dict(causa_disalimentazione=princ.get("causa_disalimentazione"),
                  causa_interruzione=princ.get("causa_interruzione"), data_interruzione=inizio,
                  data_prev_ripristino=prev_iso, prev_ripristino_testo=prev_testo,
                  descrizione_territoriale=princ.get("descrizione_territoriale"), provincia=princ.get("provincia"),
                  area=princ.get("regione"), comune=_istat6(princ.get("comune")), comuni=";".join(sorted(comuni)),
                  lat=princ.get("latitudine"), lon=princ.get("longitudine"), num_cli_disalim=clienti, n_cs=n_cs,
                  cft=princ.get("cft"), note=(princ.get("note") or None),
                  aggiornato_fonte=data_it(princ.get("dataultimoaggiornamento")), ultima_lettura=quando)
    if ex:
        # ricompare dopo una chiusura (fonte che salta una lettura): si riapre
        db.execute(f"UPDATE interruzioni SET {', '.join(f'{k}=?' for k in valori)}, chiusa_il=NULL "
                   "WHERE id_interruzione=?", (*valori.values(), i))
        return 0
    valori.update(id_interruzione=i, prima_lettura=quando, chiusa_il=None)
    db.execute(f"INSERT INTO interruzioni ({', '.join(valori)}) VALUES ({', '.join('?' * len(valori))})",
               tuple(valori.values()))
    return 1


# ---------------------------------------------------------------------------------------------- saturazione
def data_richiesta() -> str:
    return dt.datetime.now(ROMA).isoformat(timespec="seconds")


def chiama_provincia(cl: httpx.Client, prov: str) -> dict:
    """comuniServiti di una provincia (ISTAT a 3 cifre). Gettone nuovo a ogni chiamata, mai scritto nei log:
    gli errori riportano solo codici e stati HTTP."""
    dr = data_richiesta()
    r = cl.post(URL_GETTONE, json={"data": f"DataRichiesta:{dr}Provincia:{prov}", "service": "areecritiche"},
                timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"servizio del gettone: HTTP {r.status_code}")
    try:
        tk = r.json()
        gettone = tk["responseData"]["token"]
    except Exception:
        raise RuntimeError("servizio del gettone: risposta non valida") from None
    if str(tk.get("responseCode")) != "0" or not gettone:
        raise RuntimeError(f"gettone rifiutato (codice {tk.get('responseCode')})")
    r = cl.post(URL_COMUNI_SERVITI, content=json.dumps({"Token": gettone, "DataRichiesta": dr, "Provincia": prov}),
                headers={"Content-Type": "application/json"}, timeout=60)
    del gettone
    if r.status_code != 200:
        raise RuntimeError(f"comuniServiti: HTTP {r.status_code}")
    j = r.json()
    if str(j.get("CodiceEsito", "0")) != "0":
        raise RuntimeError(f"comuniServiti: esito {j.get('CodiceEsito')} {j.get('DescrizioneEsito') or ''}".strip())
    return j


def leggi_province(cl: httpx.Client) -> list[dict]:
    righe = _arcgis_tutto(cl, URL_PROVINCE, {"where": "1=1", "outFields": "cod_pro,f1,f2,f4,livellocriticita,"
                                                                          "livellocriticita2",
                                             "orderByFields": "cod_pro"})
    out = {}
    for r in righe:
        try:
            cod = f"{int(r['cod_pro']):03d}"
        except (KeyError, TypeError, ValueError):
            continue
        out[cod] = {"cod": cod, "nome": r.get("f4"), "regione": r.get("f2"),
                    "regione_cod": f"{int(r['f1']):02d}" if r.get("f1") not in (None, "") else None,
                    "livello_criticita": r.get("livellocriticita"), "livello_criticita2": r.get("livellocriticita2")}
    return sorted(out.values(), key=lambda x: x["cod"])


def leggi_comuni_ed(cl: httpx.Client) -> list[dict]:
    righe = _arcgis_tutto(cl, URL_COMUNI_ED, {"where": "pro_com>0", "outFields": "pro_com_t,pro_com,comune,cod_prov,"
                                                                                "cod_reg,servitoed",
                                              "orderByFields": "pro_com"})
    out = {}
    for r in righe:
        istat = _istat6(r.get("pro_com_t") or r.get("pro_com"))
        if not istat:
            continue
        out[istat] = {"istat_2021": istat, "nome": (r.get("comune") or "").strip() or None,
                      "cod_prov": f"{int(r['cod_prov']):03d}" if r.get("cod_prov") else istat[:3],
                      "regione_cod": f"{int(r['cod_reg']):02d}" if r.get("cod_reg") else None,
                      "servitoed": int(r.get("servitoed") or 0)}
    return list(out.values())


def codici_attuali(comuni: list[dict], ana: dict) -> None:
    """ISTAT 2021 → codice attuale: uguale se esiste ancora, altrimenti per nome nella stessa regione; None se non
    si trova (comuni fusi dopo il 2021: restano fuori dalla mappa)."""
    if not ana:
        for c in comuni:
            c["istat"] = c["istat_2021"]
        return
    per_nome = {}
    for k, v in ana.items():
        per_nome.setdefault((_norm(v.get("nome")), v.get("regione_cod")), k)
    for c in comuni:
        if c["istat_2021"] in ana:
            c["istat"] = c["istat_2021"]
        else:
            c["istat"] = per_nome.get((_norm(c["nome"]), c["regione_cod"]))


def aggiorna_saturazione(cl: httpx.Client | None = None, percorso: Path | None = None, pausa: float | None = None,
                         ora: dt.datetime | None = None, ripassi: int = 2) -> dict:
    """Aggiornamento notturno: province, comuni serviti da e-distribuzione, saturazione per provincia."""
    pausa = C.RETE_PAUSA_S if pausa is None else pausa
    ora = ora or adesso()
    quando, mese = iso(ora), ora.strftime("%Y-%m")
    proprio = cl is None
    cl = cl or client()
    db = connetti(percorso)
    try:
        try:
            cl.get(PAGINA_AREE, timeout=30)          # come il browser: prima la pagina (biscotti)
        except Exception as e:
            log.warning("Pagina delle Aree critiche non raggiungibile: %s", type(e).__name__)
        province = leggi_province(cl)
        if not province:
            raise RuntimeError("elenco delle province vuoto")
        with transazione(db):
            db.executemany("INSERT OR REPLACE INTO province VALUES (?, ?, ?, ?, ?, ?, ?)",
                           [(p["cod"], p["nome"], p["regione_cod"], p["regione"], p["livello_criticita"],
                             p["livello_criticita2"], quando) for p in province])
        esito_comuni = None
        try:
            ced = leggi_comuni_ed(cl)
            if len(ced) < MIN_COMUNI_ED:
                raise RuntimeError(f"solo {len(ced)} comuni")
            codici_attuali(ced, anagrafica())
            with transazione(db):
                db.execute("DELETE FROM comuni_ed")
                db.executemany("INSERT INTO comuni_ed VALUES (?, ?, ?, ?, ?, ?, ?)",
                               [(c["istat_2021"], c["istat"], c["nome"], c["cod_prov"], c["regione_cod"],
                                 c["servitoed"], quando) for c in ced])
                _meta(db, "comuni_ed_aggiornati", quando)
            esito_comuni = len(ced)
        except Exception as e:
            log.warning("Comuni gestiti da e-distribuzione non aggiornati: %s", e)
            esito_comuni = f"errore: {type(e).__name__}"
        ok, falliti = [], {}
        da_fare = [p["cod"] for p in province]
        for passo in range(1 + max(0, ripassi)):
            if not da_fare:
                break
            if passo:
                log.info("Saturazione: nuovo tentativo per %s", ",".join(da_fare))
                time.sleep(max(pausa, 15 if pausa else 0))
            rimasti = []
            for k, prov in enumerate(da_fare):
                if k:
                    time.sleep(pausa)
                try:
                    j = chiama_provincia(cl, prov)
                    _salva_provincia(db, prov, j, mese, quando)
                    ok.append(prov)
                    falliti.pop(prov, None)
                except Exception as e:
                    falliti[prov] = f"{type(e).__name__}: {e}"[:300]
                    rimasti.append(prov)
                    with transazione(db):
                        _segna_errore(db, prov, quando, falliti[prov])
            da_fare = rimasti
        with transazione(db):
            if ok:
                _meta(db, "saturazione_aggiornata", quando)
            _meta(db, "saturazione_ultimo_giro", json.dumps({"quando": quando, "ok": len(ok), "falliti": falliti,
                                                             "comuni_ed": esito_comuni}))
        esito = {"province": len(province), "ok": len(ok), "falliti": falliti, "comuni_ed": esito_comuni}
        log.info("Saturazione: %d province su %d, fallite %s", len(ok), len(province), ",".join(falliti) or "nessuna")
        return esito
    finally:
        db.close()
        if proprio:
            cl.close()


def _salva_provincia(db, prov: str, j: dict, mese: str, quando: str) -> None:
    righe = []
    comuni = j.get("ElencoComuni") or []
    for c in comuni:
        istat = _istat6(c.get("CodiceIstat"))
        if not istat:
            continue
        for t in c.get("ElencoTrasformatori") or []:
            righe.append((mese, prov, istat, c.get("Descrizione"), t.get("CodCabinaPrimaria"),
                          t.get("NomeCabinaPrimaria"), str(t.get("CodTrasformatore") or ""),
                          str(t.get("CodiceMontante") or ""), str(t.get("IdSezioneATMT") or ""),
                          _livello(t.get("LivSaturTraformatore")) or str(t.get("LivSaturTraformatore") or ""),
                          quando))
    with transazione(db):
        # una fotografia per mese: l'ultima lettura riuscita del mese sostituisce quella di prima
        db.execute("DELETE FROM saturazione WHERE mese=? AND provincia=?", (mese, prov))
        db.executemany("INSERT OR REPLACE INTO saturazione VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", righe)
        db.execute("INSERT OR REPLACE INTO saturazione_province VALUES (?, ?, ?, ?, ?)",
                   (mese, prov, quando, len(comuni), len(righe)))
        db.execute("""INSERT INTO tentativi_province VALUES (?, ?, 'ok', NULL, ?, NULL)
            ON CONFLICT (provincia) DO UPDATE SET ultimo_tentativo=excluded.ultimo_tentativo, esito='ok',
              errore=NULL, ultimo_ok=excluded.ultimo_ok, in_errore_dal=NULL""", (prov, quando, quando))


def _segna_errore(db, prov: str, quando: str, errore: str) -> None:
    """Tentativo fallito: `in_errore_dal` resta quello del primo errore dopo l'ultima lettura riuscita."""
    db.execute("""INSERT INTO tentativi_province VALUES (?, ?, 'errore', ?, NULL, ?)
        ON CONFLICT (provincia) DO UPDATE SET ultimo_tentativo=excluded.ultimo_tentativo, esito='errore',
          errore=excluded.errore, in_errore_dal=COALESCE(in_errore_dal, excluded.in_errore_dal)""",
               (prov, quando, errore, quando))


def segna_giro_fallito(errore: str, ora: dt.datetime | None = None, percorso: Path | None = None) -> int:
    """Giro notturno interrotto prima delle province (elenco non letto, rete giù): tutte le province note contano come
    fallite, così l'avviso delle 72 ore vale anche in questo caso."""
    quando = iso(ora or adesso())
    db = connetti(percorso)
    try:
        prov = [r[0] for r in db.execute("SELECT cod FROM province")]
        with transazione(db):
            for p in prov:
                _segna_errore(db, p, quando, errore[:300])
        return len(prov)
    finally:
        db.close()


def province_ferme(ore: float | None = None, ora: dt.datetime | None = None, percorso: Path | None = None) -> list[str]:
    """Province non aggiornate con successo da più di `ore` ore consecutive (predefinito C.RETE_AVVISO_ORE)."""
    ore = C.RETE_AVVISO_ORE if ore is None else ore
    limite = (ora or adesso()) - dt.timedelta(hours=ore)
    db = connetti(percorso)
    try:
        righe = db.execute("SELECT provincia, in_errore_dal FROM tentativi_province WHERE esito='errore'").fetchall()
    finally:
        db.close()
    return sorted(r[0] for r in righe if r[1] and dt.datetime.fromisoformat(r[1]) < limite)


def avviso_una_volta(chiave: str, attivo: bool, percorso: Path | None = None) -> bool:
    """True solo la prima volta che la condizione `chiave` diventa vera (stato nel database, sopravvive ai riavvii);
    quando torna falsa si riarma."""
    db = connetti(percorso)
    try:
        with transazione(db):
            gia = _meta(db, f"avviso_{chiave}") == "1"
            _meta(db, f"avviso_{chiave}", "1" if attivo else "0")
        return attivo and not gia
    finally:
        db.close()


def ultima_lettura_ok(percorso: Path | None = None) -> dt.datetime | None:
    """Ora dell'ultima lettura riuscita delle interruzioni, None se non ce n'è (o il database non c'è)."""
    p = Path(percorso or C.RETE_DB)
    if not p.exists():
        return None
    db = connetti(p, scrittura=False)
    try:
        v = _meta(db, "interruzioni_aggiornate")
        return dt.datetime.fromisoformat(v) if v else None
    except sqlite3.Error:
        return None
    finally:
        db.close()


def ha_saturazione(percorso: Path | None = None) -> bool:
    p = Path(percorso or C.RETE_DB)
    if not p.exists():
        return False
    db = connetti(p, scrittura=False)
    try:
        return db.execute("SELECT 1 FROM saturazione_province LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        db.close()


# ---------------------------------------------------------------------------------------------- tabella di raccordo
CAMPI_RACCORDO = ("cod_ac", "gestore", "cod_cp_ed", "nome_cp_ed", "comuni_serviti", "osm_id", "osm_nome", "lat", "lon",
                  "punteggio_nome", "distanza_m", "esito", "data_raccordo", "versione_ac")


@lru_cache(maxsize=2)
def _raccordo_file(percorso: str, mtime: float) -> tuple[dict, list]:
    per_cp, altre = {}, []
    with open(percorso, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            r = {k: (r.get(k) or "").strip() for k in CAMPI_RACCORDO}
            for k in ("lat", "lon", "punteggio_nome", "distanza_m"):
                try:
                    r[k] = float(r[k]) if r[k] != "" else None
                except ValueError:
                    r[k] = None
            if r["cod_cp_ed"]:
                per_cp[r["cod_cp_ed"]] = r
            else:
                altre.append(r)
    return per_cp, altre


def raccordo() -> tuple[dict, list]:
    """(cabine e-distribuzione per codice, altre righe senza codice e-distribuzione: aree GSE di altri gestori)."""
    p = C.RETE_RACCORDO
    try:
        m = p.stat().st_mtime
    except OSError:
        return {}, []
    try:
        return _raccordo_file(str(p), m)
    except Exception:
        log.exception("Tabella di raccordo %s non leggibile", p)
        return {}, []


# ---------------------------------------------------------------------------------------------- letture per le rotte
def _db() -> sqlite3.Connection:
    try:
        return connetti(scrittura=False)
    except (FileNotFoundError, sqlite3.Error):
        raise HTTPException(503, "i dati della rete elettrica non sono ancora sul server: riprova più tardi")


_cache: dict[str, tuple] = {}
_blocco_cache = threading.Lock()


def _chiave_saturazione(db) -> tuple:
    rp = C.RETE_RACCORDO
    try:
        mr = rp.stat().st_mtime
    except OSError:
        mr = 0
    ap = C.DATI / "comuni.parquet"
    try:
        ma = ap.stat().st_mtime
    except OSError:
        ma = 0
    return (str(C.RETE_DB), _meta(db, "saturazione_aggiornata"), _meta(db, "comuni_ed_aggiornati"), mr, ma)


def stato_saturazione(db) -> dict:
    """Fotografia attuale (ultimo mese riuscito di ogni provincia) con comuni e cabine calcolati; in memoria finché
    il database o la tabella di raccordo non cambiano."""
    k = _chiave_saturazione(db)
    with _blocco_cache:
        if _cache.get("sat", (None,))[0] == k:
            return _cache["sat"][1]
    s = _calcola_saturazione(db)
    with _blocco_cache:
        _cache["sat"] = (k, s)
    return s


def _calcola_saturazione(db) -> dict:
    ana = anagrafica()
    prov_reg = _regioni_province(db)
    righe = db.execute("""WITH u AS (SELECT provincia, MAX(mese) AS mese FROM saturazione_province GROUP BY provincia)
        SELECT s.*, p.letto_il AS data FROM saturazione s JOIN u ON s.provincia=u.provincia AND s.mese=u.mese
        JOIN saturazione_province p ON p.provincia=s.provincia AND p.mese=s.mese""").fetchall()
    trasf_cp: dict[str, dict] = {}         # cod_cp → {cod_trasf: livello}
    trasf_com: dict[str, dict] = {}        # comune → {(cod_cp, cod_trasf): livello}
    cabine: dict[str, dict] = {}
    nomi_comuni: dict[str, str] = {}
    for r in righe:
        cp, tr, liv, com = r["cod_cp"], r["cod_trasf"], _livello(r["livello"]), r["comune"]
        cab = cabine.setdefault(cp, {"cod_cp_ed": cp, "nome_cp_ed": r["nome_cp"], "comuni": set(), "data": r["data"],
                                     "province": set()})
        cab["comuni"].add(com)
        cab["province"].add(r["provincia"])
        cab["data"] = max(cab["data"], r["data"])
        trasf_cp.setdefault(cp, {})
        if liv:
            trasf_cp[cp][tr] = liv
            trasf_com.setdefault(com, {})[(cp, tr)] = liv
        else:
            trasf_com.setdefault(com, {})
        nomi_comuni.setdefault(com, r["comune_nome"])
    data_prov = {r["provincia"]: r["letto_il"] for r in db.execute(
        """SELECT provincia, MAX(letto_il) AS letto_il FROM saturazione_province GROUP BY provincia""")}
    per_comune = {}
    for com, tt in trasf_com.items():
        cont = {l: 0 for l in LIVELLI}
        for liv in tt.values():
            cont[liv] += 1
        per_comune[com] = {"trasf": cont, **classe_comune(cont),
                           "cabine": sorted({cp for cp, _ in tt} | {cp for cp, c in cabine.items() if com in c["comuni"]}),
                           "data": data_prov.get(com[:3])}
    for cp, cab in cabine.items():
        cont = {l: 0 for l in LIVELLI}
        for liv in trasf_cp.get(cp, {}).values():
            cont[liv] += 1
        cab["trasf"] = cont
        cab["livello"] = livello_cabina(cont)
    servito0 = {r["istat"] for r in db.execute("SELECT istat FROM comuni_ed WHERE servitoed=0 AND istat IS NOT NULL")}
    # (17/11/2026, decisione di Paolo) un comune con trasformatori e-distribuzione nel dato mensile non è mai «non
    # concessionario»: se View_ComuniGestitiED2021Is lo segna servitoed = 0 (35 comuni, soprattutto milanesi) è
    # «servito in parte da un altro distributore» e si colora con la sua criticità
    in_parte = servito0 & set(trasf_com)
    non_conc = servito0 - in_parte
    ed_nomi = {r["istat"]: (r["nome"], r["regione_cod"]) for r in db.execute(
        "SELECT istat, nome, regione_cod FROM comuni_ed WHERE istat IS NOT NULL")}
    return {"cabine": cabine, "comuni": per_comune, "nomi": nomi_comuni, "non_concessionari": non_conc, "in_parte": in_parte,
            "ed": ed_nomi, "ana": ana, "prov_reg": prov_reg, "data_prov": data_prov,
            "data": max(data_prov.values()) if data_prov else None}


def _regioni_comuni(comuni, s) -> set:
    return {r for r in (regione_di(c, s["ana"], s["prov_reg"]) for c in comuni) if r}


def _cod_regione(regione: str | None) -> str | None:
    if regione is None or regione == "":
        return None
    if not re.fullmatch(r"\d{1,2}", regione) or not 1 <= int(regione) <= 20:
        raise HTTPException(422, "regione: codice ISTAT a 2 cifre (01–20)")
    return regione.zfill(2)


def _istat_param(istat: str) -> str:
    if not re.fullmatch(r"\d{6}", istat or ""):
        raise HTTPException(422, "codice ISTAT del comune a 6 cifre")
    return istat


def _risposta(dati, max_age: int) -> JSONResponse:
    return JSONResponse(dati, headers={"Cache-Control": f"public, max-age={max_age}"})


def _proprieta_cabina(cab: dict | None, rac: dict | None) -> dict:
    rac = rac or {}
    p = {k: rac.get(k) for k in CAMPI_RACCORDO if k not in ("lat", "lon")}
    if cab:
        p["cod_cp_ed"] = cab["cod_cp_ed"]
        p["nome_cp_ed"] = p.get("nome_cp_ed") or cab["nome_cp_ed"]
        p["comuni_serviti"] = ";".join(sorted(cab["comuni"]))
        p["gestore"] = p.get("gestore") or "e-distribuzione"
    p["livello"] = cab["livello"] if cab else None
    p["trasf"] = cab["trasf"] if cab else {l: 0 for l in LIVELLI}
    p["data_saturazione"] = cab["data"] if cab else None
    return p


def cabine_geojson(regione: str | None = None) -> dict:
    db = _db()
    try:
        s = stato_saturazione(db)
    finally:
        db.close()
    per_cp, altre = raccordo()
    feat, senza = [], 0
    voci = [(cp, cab, per_cp.get(cp)) for cp, cab in s["cabine"].items()]
    voci += [(cp, None, r) for cp, r in per_cp.items() if cp not in s["cabine"]]
    voci += [(None, None, r) for r in altre]
    for cp, cab, rac in voci:
        comuni = cab["comuni"] if cab else set(filter(None, ((rac or {}).get("comuni_serviti") or "").split(";")))
        if regione and regione not in _regioni_comuni(comuni, s):
            continue
        if not rac or rac.get("lat") is None or rac.get("lon") is None:
            senza += 1
            continue
        feat.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [rac["lon"], rac["lat"]]},
                     "properties": _proprieta_cabina(cab, rac)})
    return {"type": "FeatureCollection", "features": feat, "senza_posizione": senza,
            "data_saturazione": s["data"], "regione": regione,
            "attribuzione": f"{LICENZE['posizioni_cabine']['attribuzione']}; {FONTE_ED}; "
                            f"{LICENZE['codici_gse']['attribuzione']}",
            "licenza": LICENZE["posizioni_cabine"]["licenza"], "licenze": LICENZE}


def comuni_regione(regione: str | None) -> list[dict]:
    db = _db()
    try:
        s = stato_saturazione(db)
    finally:
        db.close()
    elenco: dict[str, str | None] = {}
    for k, v in s["ana"].items():
        if not regione or v.get("regione_cod") == regione:
            elenco[k] = v.get("nome")
    for k in list(s["comuni"]) + list(s["ed"]):
        if k not in elenco and (not regione or regione_di(k, s["ana"], s["prov_reg"]) == regione
                                or (k in s["ed"] and s["ed"][k][1] == regione)):
            elenco[k] = s["nomi"].get(k) or (s["ed"].get(k) or (None,))[0]
    out = []
    vuoto = {"trasf": {l: 0 for l in LIVELLI}, **classe_comune({}), "cabine": [], "data": None}
    for k in sorted(elenco):
        c = s["comuni"].get(k) or vuoto
        conc = k not in s["non_concessionari"]
        out.append({"istat": k, "nome": elenco[k], "concessionario": conc, "servito_in_parte": k in s["in_parte"],
                    "pieno": c["pieno"],
                    "strisce": c["strisce"], "livello": c["livello"], "quota": c["quota"], "trasf": c["trasf"],
                    "cabine": c["cabine"], "data": c["data"] or s["data_prov"].get(k[:3]),
                    "dato_disponibile": conc and k[:3] in s["data_prov"]})
    return out


def cabine_comune(istat: str) -> dict:
    db = _db()
    try:
        s = stato_saturazione(db)
        righe = db.execute("""WITH u AS (SELECT provincia, MAX(mese) AS mese FROM saturazione_province
                                         GROUP BY provincia)
            SELECT s.* FROM saturazione s JOIN u ON s.provincia=u.provincia AND s.mese=u.mese WHERE s.comune=?
            ORDER BY s.cod_cp, s.cod_trasf""", (istat,)).fetchall()
    finally:
        db.close()
    per_cp, altre = raccordo()
    cab: dict[str, dict] = {}
    for r in righe:
        c = cab.setdefault(r["cod_cp"], {"trasformatori": {}})
        c["trasformatori"].setdefault(r["cod_trasf"], {"cod_trasf": r["cod_trasf"], "livello": _livello(r["livello"]),
                                                       "montanti": []})
        c["trasformatori"][r["cod_trasf"]]["montanti"].append({"cod_montante": r["cod_montante"],
                                                               "id_sezione": r["id_sezione"]})
    out = []
    for cp, c in cab.items():
        info = s["cabine"].get(cp)
        rac = per_cp.get(cp)
        p = _proprieta_cabina(info, rac)
        p.update(lat=(rac or {}).get("lat"), lon=(rac or {}).get("lon"),
                 trasformatori_del_comune=list(c["trasformatori"].values()))
        out.append(p)
    for r in altre:
        if istat in (r.get("comuni_serviti") or "").split(";"):
            p = _proprieta_cabina(None, r)
            p.update(lat=r.get("lat"), lon=r.get("lon"), trasformatori_del_comune=[])
            out.append(p)
    crit = s["comuni"].get(istat)
    nome = (s["ana"].get(istat) or {}).get("nome") or s["nomi"].get(istat) or (s["ed"].get(istat) or (None,))[0]
    return {"istat": istat, "nome": nome, "concessionario": istat not in s["non_concessionari"],
            "servito_in_parte": istat in s["in_parte"],
            "nota": NOTA_IN_PARTE if istat in s["in_parte"] else None,
            "criticita": ({k: crit[k] for k in ("trasf", "livello", "quota", "pieno", "strisce")} if crit
                          else {"trasf": {l: 0 for l in LIVELLI}, **classe_comune({})}),
            "data_saturazione": (crit or {}).get("data") or s["data_prov"].get(istat[:3]),
            "cabine": out, "regola": REGOLA, "fonte": FONTE_ED,
            "attribuzione_posizioni": LICENZE["posizioni_cabine"]["attribuzione"],
            "licenza_posizioni": LICENZE["posizioni_cabine"]["licenza"], "licenze": LICENZE}


def _nomi(db, ana: dict) -> dict:
    """ISTAT → nome del comune: elenco del sito (fase 3) e, dove manca, quello di e-distribuzione."""
    out = {r["istat"]: r["nome"] for r in db.execute("SELECT istat, nome FROM comuni_ed WHERE istat IS NOT NULL")}
    out.update({k: v.get("nome") for k, v in ana.items() if v.get("nome")})
    return out


def _interruzione(r, ora: dt.datetime, nomi: dict) -> dict:
    attiva = r["chiusa_il"] is None
    fine = iso(ora) if attiva else r["ultima_lettura"]
    return {"id": r["id_interruzione"], "comune": r["comune"],
            "nome_comune": nomi.get(r["comune"] or ""),
            "comuni": [c for c in (r["comuni"] or "").split(";") if c],
            "descrizione": r["descrizione_territoriale"], "causa": r["causa_disalimentazione"],
            "codice_causa": r["causa_interruzione"], "clienti": r["num_cli_disalim"], "cabine_secondarie": r["n_cs"],
            "inizio": r["data_interruzione"], "ripristino_previsto": r["data_prev_ripristino"],
            "ripristino_testo": r["prev_ripristino_testo"], "aggiornato_fonte": r["aggiornato_fonte"],
            "prima_lettura": r["prima_lettura"], "ultima_lettura": r["ultima_lettura"], "chiusa_il": r["chiusa_il"],
            "attiva": attiva, ("durata_finora_min" if attiva else "durata_min"): _minuti(r["data_interruzione"], fine)}


def interruzioni_attive(regione: str | None = None, bbox: tuple | None = None) -> dict:
    db = _db()
    try:
        righe = db.execute("SELECT * FROM interruzioni WHERE chiusa_il IS NULL ORDER BY data_interruzione").fetchall()
        prov_reg = _regioni_province(db)
        agg = _meta(db, "interruzioni_aggiornate")
        ana = anagrafica()
        nomi = _nomi(db, ana)
    finally:
        db.close()
    ora, feat = adesso(), []
    for r in righe:
        if r["lat"] is None or r["lon"] is None:
            continue
        if bbox and not (bbox[0] <= r["lon"] <= bbox[2] and bbox[1] <= r["lat"] <= bbox[3]):
            continue
        comuni = [c for c in (r["comuni"] or "").split(";") if c] or [r["comune"]]
        if regione and regione not in {regione_di(c, ana, prov_reg) for c in comuni}:
            continue
        feat.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                     "properties": _interruzione(r, ora, nomi)})
    return {"type": "FeatureCollection", "features": feat, "aggiornate": agg, "nota_durata": NOTA_DURATA,
            "nota_posizione": "punto della cabina secondaria con più clienti disalimentati",
            "attribuzione": FONTE_ED, "licenze": {"e-distribuzione": LICENZE["e-distribuzione"]}}


def _mese(x: str | None, nome: str) -> str | None:
    if not x:
        return None
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", x):
        raise HTTPException(422, f"{nome}: mese nel formato aaaa-mm")
    return x


def interruzioni_comune(istat: str, da: str | None = None, a: str | None = None) -> dict:
    db = _db()
    try:
        righe = db.execute("""SELECT i.*, SUM(cs.num_cli_disalim) AS clienti_comune FROM interruzioni i
            JOIN interruzioni_cs cs ON cs.id_interruzione=i.id_interruzione WHERE cs.comune=?
            GROUP BY i.id_interruzione ORDER BY i.data_interruzione DESC""", (istat,)).fetchall()
        dal = _meta(db, "raccolta_dal")
        nomi = _nomi(db, anagrafica())
    finally:
        db.close()
    ora = adesso()
    sel = []
    for r in righe:
        m = (r["data_interruzione"] or r["prima_lettura"] or "")[:7]
        if (da and m < da) or (a and m > a):
            continue
        sel.append((m, r))

    def _somma(gruppo):
        chiuse = [_minuti(r["data_interruzione"], r["ultima_lettura"]) for _, r in gruppo if r["chiusa_il"]]
        chiuse = [d for d in chiuse if d is not None]
        cause = [(r["causa_disalimentazione"] or "").lower() for _, r in gruppo]
        return {"n": len(gruppo), "guasti": sum("guasto" in c for c in cause),
                "programmati": sum("programm" in c for c in cause),
                "clienti": sum(int(r["clienti_comune"] or 0) for _, r in gruppo),
                "durata_media_min": round(sum(chiuse) / len(chiuse)) if chiuse else None,
                "durata_max_min": max(chiuse) if chiuse else None}

    mesi: dict[str, list] = {}
    for m, r in sel:
        mesi.setdefault(m, []).append((m, r))
    per_causa, per_codice = {}, {}
    for _, r in sel:
        per_causa[r["causa_disalimentazione"] or "non indicata"] = per_causa.get(r["causa_disalimentazione"]
                                                                                 or "non indicata", 0) + 1
        per_codice[r["causa_interruzione"] or "?"] = per_codice.get(r["causa_interruzione"] or "?", 0) + 1

    def _voce(r):
        v = _interruzione(r, ora, nomi)
        v["clienti_comune"] = int(r["clienti_comune"] or 0)
        return v

    totale = _somma(sel)
    totale["attive"] = sum(1 for _, r in sel if r["chiusa_il"] is None)
    return {"istat": istat, "nome": nomi.get(istat), "dal": dal, "da": da, "a": a,
            "totale": totale,
            "per_mese": [{"mese": m, **_somma(g)} for m, g in sorted(mesi.items())],
            "per_causa": per_causa, "per_codice_causa": per_codice,
            "attive": [_voce(r) for _, r in sel if r["chiusa_il"] is None],
            "ultime": [_voce(r) for _, r in sel[:50]],
            "nota_durata": NOTA_DURATA + " Le medie e i massimi contano solo le interruzioni chiuse.",
            "nota_clienti": "clienti disalimentati nel comune: massimo visto per ogni cabina secondaria, sommato",
            "fonte": FONTE_ED, "licenze": {"e-distribuzione": LICENZE["e-distribuzione"]}}


def stato() -> dict:
    p = C.RETE_DB
    out = {"saturazione_aggiornata": None, "interruzioni_aggiornate": None, "attive": 0, "province_mancanti": [],
             "province_non_aggiornate": {}, "raccolta_dal": None}
    if p.exists():
        db = _db()
        try:
            prov = [r["cod"] for r in db.execute("SELECT cod FROM province ORDER BY cod")]
            con_dato = {r[0] for r in db.execute("SELECT DISTINCT provincia FROM saturazione_province")}
            tent = {r["provincia"]: r for r in db.execute("SELECT * FROM tentativi_province")}
            non_agg = {c: tent[c]["ultimo_ok"] for c in prov if c in tent and tent[c]["esito"] != "ok" and c in con_dato}
            out.update(saturazione_aggiornata=_meta(db, "saturazione_aggiornata"),
                         interruzioni_aggiornate=_meta(db, "interruzioni_aggiornate"),
                         attive=db.execute("SELECT COUNT(*) FROM interruzioni WHERE chiusa_il IS NULL").fetchone()[0],
                         province_mancanti=[c for c in prov if c not in con_dato], province_non_aggiornate=non_agg,
                         raccolta_dal=_meta(db, "raccolta_dal"), comuni_ed_aggiornati=_meta(db, "comuni_ed_aggiornati"))
        finally:
            db.close()
    per_cp, altre = raccordo()
    tutte = list(per_cp.values()) + altre
    out["raccordo"] = {"righe": len(tutte), "con_posizione": sum(1 for r in tutte if r.get("lat") is not None),
                         "data_raccordo": max((r["data_raccordo"] for r in tutte if r.get("data_raccordo")), default=None),
                         "versione_ac": max((r["versione_ac"] for r in tutte if r.get("versione_ac")), default=None)}
    out.update(intervallo_interruzioni_min=C.RETE_INTERRUZIONI_MIN, regola=REGOLA, nota_servito_in_parte=NOTA_IN_PARTE, nota_durata=NOTA_DURATA,
                 fonti={"interruzioni": URL_INTERRUZIONI.rsplit("/query", 1)[0],
                        "saturazione": "e-distribuzione, mappa delle Aree critiche (servizio comuniServiti)",
                        "comuni_gestiti": URL_COMUNI_ED.rsplit("/query", 1)[0],
                        "province": URL_PROVINCE.rsplit("/query", 1)[0],
                        "pagina_aree_critiche": PAGINA_AREE,
                        # (20/11/2026) solo l'indirizzo: le aree le legge il browser dal GSE, mai il server
                        "aree_convenzionali_gse": URL_GSE_AREE, "pagina_aree_convenzionali_gse": PAGINA_GSE_AREE},
                 licenze=LICENZE)
    return out


# ---------------------------------------------------------------------------------------------- rotte
router = APIRouter(prefix="/api/rete")


def _bbox(x: str | None) -> tuple | None:
    if not x:
        return None
    try:
        v = tuple(float(p) for p in x.split(","))
    except ValueError:
        v = ()
    if len(v) != 4 or not (v[0] < v[2] and v[1] < v[3]):
        raise HTTPException(422, "bbox: lon_min,lat_min,lon_max,lat_max")
    return v


@router.get("/stato")
def rotta_stato(request: Request):
    P.limita(request, "rete")
    return _risposta(stato(), 60)


@router.get("/cabine")
def rotta_cabine(request: Request, regione: str | None = None):
    P.limita(request, "rete")
    return _risposta(cabine_geojson(_cod_regione(regione)), 1800)


@router.get("/cabine/comune/{istat}")
def rotta_cabine_comune(request: Request, istat: str):
    P.limita(request, "rete")
    return _risposta(cabine_comune(_istat_param(istat)), 1800)


@router.get("/comuni")
def rotta_comuni(request: Request, regione: str | None = None):
    P.limita(request, "rete")
    return _risposta(comuni_regione(_cod_regione(regione)), 1800)


@router.get("/interruzioni/attive")
def rotta_attive(request: Request, regione: str | None = None, bbox: str | None = None):
    P.limita(request, "rete")
    return _risposta(interruzioni_attive(_cod_regione(regione), _bbox(bbox)), 120)


@router.get("/interruzioni/comune/{istat}")
def rotta_interruzioni_comune(request: Request, istat: str, da: str | None = None, a: str | None = None):
    P.limita(request, "rete")
    return _risposta(interruzioni_comune(_istat_param(istat), _mese(da, "da"), _mese(a, "a")), 300)
