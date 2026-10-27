"""Client dell'API Zornade v2 (dati catastali e territoriali per particella).

Piano gratuito: 10.000 richieste all'ora con chiave personale (https://app.zornade.com/api).
Attribuzione obbligatoria: con il piano gratuito deve essere un LINK cliccabile a https://zornade.com
("Dati elaborati da Zornade"); la sola scritta non basta. Più le fonti di ogni blocco (catasto Agenzia
delle Entrate CC BY 4.0, ISTAT, ISPRA, INGV, OpenStreetMap ODbL, ...), riportate in meta.licenses.
Vietate la ridistribuzione dei dati grezzi e l'estrazione massiva.

Comportamento verificato dal vivo il 25/10/2026:
  * /parcels/search vuole il NOME del comune (comune=Bologna), non il codice catastale, e il foglio
    senza zeri iniziali (foglio=190, non 0190);
  * /parcels/locate restituisce `foglio` vuoto: il foglio si ricava da cadastral_reference
    (A944_019000.170 → foglio 190, allegato 0, sviluppo 0, mappale 170);
  * /geocode/search lavora sul solo parametro q ("via civico comune"); copre ~18,7 milioni di civici
    (OpenAddresses e feed comunali), quindi alcune vie mancano.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)
URL = "https://api.zornade.com/api/v2"
ATTRIBUZIONE = "Dati elaborati da Zornade"
ATTRIBUZIONE_URL = "https://zornade.com"
ATTRIBUZIONE_HTML = f'<a href="{ATTRIBUZIONE_URL}">{ATTRIBUZIONE}</a>'
ATTRIBUZIONE_MD = f"[{ATTRIBUZIONE}]({ATTRIBUZIONE_URL})"


class ErroreZornade(RuntimeError):
    pass


def pulisci_cache(cache: Path, giorni: float = 365) -> int:
    """Cancella dalla cache le risposte più vecchie di `giorni` (le ricerche contengono indirizzi: non si
    tengono oltre il necessario). Restituisce il numero di righe cancellate."""
    if not Path(cache).exists():
        return 0
    with sqlite3.connect(cache) as db:
        n = db.execute("DELETE FROM cache WHERE t < ?", (time.time() - giorni * 86400,)).rowcount
    with sqlite3.connect(cache) as db:
        db.execute("VACUUM")
    return n


class Zornade:
    """Con cache su SQLite (le stesse ricerche non consumano quota) e ritmo massimo configurabile."""

    def __init__(self, chiave: str, cache: Path | None = None, richieste_al_secondo: float = 2.0):
        if not chiave:
            raise ErroreZornade("Chiave Zornade mancante (ZORNADE_API_KEY)")
        self.http = httpx.Client(timeout=30, headers={"x-api-key": chiave, "User-Agent": "progetto-energia/1.0"})
        self.pausa = 1.0 / richieste_al_secondo
        self._ultima = 0.0
        self._lock = threading.Lock()
        self.db = None
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(cache, check_same_thread=False)
            self.db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT, t REAL)")
        self.chiamate = 0

    def get(self, percorso: str, params: dict, cache_giorni: float = 90) -> dict:
        params = {k: v for k, v in params.items() if v not in (None, "")}
        k = percorso + "?" + json.dumps(params, sort_keys=True)
        if self.db:
            r = self.db.execute("SELECT v, t FROM cache WHERE k=?", (k,)).fetchone()
            if r and time.time() - r[1] < cache_giorni * 86400:
                return json.loads(r[0])
        for tentativo in range(5):
            with self._lock:
                attesa = self._ultima + self.pausa - time.time()
                if attesa > 0:
                    time.sleep(attesa)
                self._ultima = time.time()
            try:
                r = self.http.get(f"{URL}{percorso}", params=params)
            except httpx.HTTPError as e:
                log.warning("Zornade: errore di rete (%s)", e)
                time.sleep(5 * (tentativo + 1))
                continue
            self.chiamate += 1
            if r.status_code == 429:
                attesa = int(r.headers.get("retry-after", "60"))
                log.warning("Zornade: limite orario raggiunto, attendo %d s", attesa)
                time.sleep(attesa)
                continue
            if r.status_code >= 500:
                time.sleep(5 * (tentativo + 1))
                continue
            if r.status_code in (401, 403):
                raise ErroreZornade("Chiave Zornade non valida o scaduta")
            if r.status_code == 404:
                return {"data": [], "meta": {"non_trovato": True}}
            if r.status_code != 200:
                raise ErroreZornade(f"Zornade {r.status_code}: {r.text[:200]}")
            d = r.json()
            if self.db:
                self.db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (k, json.dumps(d), time.time()))
                self.db.commit()
            return d
        raise ErroreZornade("Zornade: troppi tentativi falliti")

    # ------------------------------------------------------------------ rotte usate
    def geocodifica(self, q: str, limite: int = 5) -> list[dict]:
        """q = "via civico comune" in un'unica stringa (il parametro city riduce i risultati)."""
        return self.get("/geocode/search", {"q": q, "limit": limite}).get("data", [])

    def particelle_in_punti(self, punti: list[tuple[float, float]]) -> list[dict]:
        """Una chiamata per più punti (modo points=): restituisce la lista delle particelle trovate."""
        s = ";".join(f"{lat:.6f},{lon:.6f}" for lat, lon in punti)
        return self.get("/parcels/locate", {"points": s, "limit": 200}).get("data", [])

    def particella_in_punto(self, lat: float, lon: float) -> dict | None:
        d = self.get("/parcels/locate", {"lat": round(lat, 6), "lng": round(lon, 6), "limit": 1}).get("data", [])
        return d[0] if d else None

    def cerca_particella(self, comune: str, foglio: str | None, mappale: str, sezione: str | None = None) -> list[dict]:
        """comune: NOME del comune (es. "Bologna"); foglio senza zeri iniziali."""
        return self.get("/parcels/search", {"comune": comune, "foglio": senza_zeri(foglio), "label": senza_zeri(mappale),
                                            "sezione": sezione, "limit": 20}).get("data", [])

    def dettaglio(self, fid: int, blocchi: str = "basic,cadastral,buildings,terrain") -> dict:
        return self.get(f"/parcels/{int(fid)}", {"include": blocchi}, cache_giorni=365)


def senza_zeri(v: str | None) -> str | None:
    """'0190' → '190'; lascia invariati i valori con lettere (es. 'A', '12/B')."""
    if v is None:
        return None
    v = str(v).strip()
    return str(int(v)) if v.isdigit() else v


_RIF = re.compile(r"^(?P<belfiore>[A-Z]\d{3})(?P<sezione>[A-Z])?_(?P<foglio>\d{4})(?P<allegato>\w)(?P<sviluppo>\w)\.(?P<mappale>.+)$")


def da_riferimento(rif: str | None) -> dict:
    """Scompone cadastral_reference: 'A944_019000.170' → belfiore A944, foglio '190', allegato '0',
    sviluppo '0', mappale '170'. Restituisce {} se il formato non è riconosciuto."""
    m = _RIF.match(rif or "")
    if not m:
        return {}
    d = m.groupdict()
    d["foglio"] = str(int(d["foglio"]))
    return d


def coordinate(d: dict) -> tuple[float | None, float | None]:
    """Estrae lat/lon da un risultato (le forme variano tra geocodifica e particelle)."""
    for a, b in (("lat", "lng"), ("lat", "lon"), ("latitude", "longitude")):
        if a in d and b in d and d[a] is not None:
            return float(d[a]), float(d[b])
    for k in ("centroid", "location", "point", "coordinates", "geometry"):
        v = d.get(k)
        if isinstance(v, dict):
            r = coordinate(v)
            if r[0] is not None:
                return r
    return None, None
