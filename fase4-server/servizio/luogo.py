"""Ricerca di un luogo nelle pagine di mappa: particella del civico e metà della via (17/11/2026, segnalazione di Paolo).

La pagina (`fase5-sito/sito/cerca_luogo.js`) manda una riga a `POST /api/patrimonio` con il campo `luogo=1`; la rotta
geolocalizza la riga come sempre (ANNCSU, poi Zornade) e poi, **solo se la riga è una**, chiama `arricchisci`, che aggiunge
alla riga (senza togliere nulla) dove mettere il segnaposto e cosa inquadrare (`fase7-territorio/territorio/luogo.py`):
  * civico, foglio e particella → la particella della **cartografia catastale dell'Agenzia delle Entrate** (WFS INSPIRE,
    CC BY 4.0, nessuna chiave; lo stesso ente e la stessa licenza dello strato «Particelle» delle ortofoto, che usa il WMS):
    una chiamata GetFeature su un quadrato di 30 m attorno al punto;
  * via senza civico, o via non riconosciuta → le strade con quel nome nel comune da **Overpass** (OpenStreetMap, ODbL; le
    stesse istanze e la stessa riserva del ripiego OSM di Modelli 3D) più i civici ANNCSU della via: metà della via, oppure
    l'elenco da far scegliere.

Protezioni (come per le altre fonti esterne):
  * la rotta resta quella del patrimonio: verifica anti-robot (Turnstile) e limite per indirizzo «patrimonio»; in più il
    limite «luogo» (LUOGO_ORA ricerche per IP all'ora);
  * tetti per tutto il sito: CATASTO_WFS_TETTO_ORA chiamate all'ora al WFS dell'Agenzia, e per Overpass lo stesso tetto del
    ripiego OSM (EDIFICI_OSM_TETTO_ORA, contatore «overpass» comune); oltre il tetto la ricerca resta com'era, con l'avviso;
  * al WFS di norma **una** chiamata per ricerca (per un civico con più accessi una sola GetFeature sul riquadro degli
    accessi più 20 m, assegnati in locale; per accesso, al più 4 insieme, solo se il riquadro supera 640 m o il WFS lo
    rifiuta); al più 4 chiamate al WFS insieme e una a Overpass per tutto il sito, attesa del turno al più LUOGO_ATTESA_S
    secondi; chiamata al più LUOGO_TIMEOUT_S;
  * copia in memoria delle risposte (LUOGO_COPIA_ORE ore; al più COPIA_MAX voci): la stessa via o lo stesso punto non
    richiamano la fonte;
  * a Overpass va solo il codice ISTAT del comune e le parole del nome della via; al WFS un quadrato di 30 m (il punto del
    civico, già pubblico in ANNCSU), mai chi cerca;
  * LUOGO=false nel .env spegne tutto: la ricerca torna come prima del 17/11/2026.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict

import httpx
from . import config as C, protezione as P, strati as S

log = logging.getLogger(__name__)
COPIA_MAX = 2000
_copie: dict[str, OrderedDict] = {"wfs": OrderedDict(), "overpass": OrderedDict()}
# WFS: al più 4 chiamate insieme (ripiego per accesso di un civico con molti accessi); Overpass: una alla volta
_turni = {"wfs": threading.BoundedSemaphore(4), "overpass": threading.Lock()}


def _dalla_copia(fonte: str, chiave: str):
    c = _copie[fonte]
    v = c.get(chiave)
    if v and time.time() - v[0] < C.LUOGO_COPIA_ORE * 3600:
        c.move_to_end(chiave)
        return v[1]
    return None


def _in_copia(fonte: str, chiave: str, valore) -> None:
    c = _copie[fonte]
    c[chiave] = (time.time(), valore)
    c.move_to_end(chiave)
    while len(c) > COPIA_MAX:
        c.popitem(last=False)


def _scarica_wfs(parametri: dict) -> str:
    with httpx.Client(timeout=C.LUOGO_TIMEOUT_S, headers={"User-Agent": S.USER_AGENT}, follow_redirects=True) as cl:
        r = cl.get(C.CATASTO_WFS_URL, params=parametri)
    r.raise_for_status()
    if "CadastralParcel" not in r.text and "FeatureCollection" not in r.text:
        raise httpx.HTTPError("risposta del WFS catastale non valida")
    return r.text


def wfs(parametri: dict) -> str | None:
    """Testo XML della cartografia catastale per il riquadro; None se il tetto orario è pieno o la fonte è occupata."""
    chiave = "&".join(f"{k}={v}" for k, v in sorted(parametri.items()))
    v = _dalla_copia("wfs", chiave)
    if v is not None:
        return v
    if not P.tetto_globale("catasto_wfs", C.CATASTO_WFS_TETTO_ORA):
        log.warning("Ricerca luogo: tetto orario del WFS catastale raggiunto")
        return None
    if not _turni["wfs"].acquire(timeout=C.LUOGO_ATTESA_S):
        return None
    try:
        testo = _scarica_wfs(parametri)
    finally:
        _turni["wfs"].release()
    _in_copia("wfs", chiave, testo)
    return testo


def overpass(query: str) -> dict | None:
    """JSON di Overpass per la query; None se il tetto orario è pieno, la fonte è occupata o non risponde."""
    v = _dalla_copia("overpass", query)
    if v is not None:
        return v
    if not P.tetto_globale("overpass", C.EDIFICI_OSM_TETTO_ORA):
        log.warning("Ricerca luogo: tetto orario di Overpass raggiunto")
        return None
    if not _turni["overpass"].acquire(timeout=C.LUOGO_ATTESA_S):
        return None
    try:
        r = S.chiedi_overpass(S.istanze_overpass(), query, "json", timeout=C.LUOGO_TIMEOUT_S, nome="Ricerca luogo")
    finally:
        _turni["overpass"].release()
    if r.status_code != 200:
        log.info("Ricerca luogo: Overpass risponde %s", r.status_code)
        return None
    d = r.json()
    _in_copia("overpass", query, d)
    return d


def arricchisci(righe: list[dict], comune: str, comuni, idx) -> None:
    """Aggiunge i campi della ricerca di un luogo alla riga (una sola: per i file del patrimonio non si fa nulla). Il limite
    per IP «luogo» lo controlla la rotta prima di geolocalizzare. comuni: elenco con istat, nome, belfiore
    (meteo.comuni()); idx: Indirizzario ANNCSU o None."""
    if not C.LUOGO or len(righe) != 1:
        return
    from territorio import luogo as L
    istat = belfiore = None
    nome = str(comune or "").strip().lower()
    if nome:
        m = comuni[comuni.nome.str.lower() == nome]
        if len(m):
            istat, belfiore = str(m.istat.iloc[0]), str(m.belfiore.iloc[0])
    try:
        righe[0].update(L.arricchisci(righe[0], istat, belfiore, idx, wfs, overpass))
    except Exception as e:   # noqa: BLE001 - la ricerca resta quella di prima
        log.warning("Ricerca luogo: %s", e)
        righe[0]["luogo_avviso"] = "inquadratura migliore non disponibile ora"


def fonti(riga: dict) -> list[str]:
    """Fonti da citare per i campi aggiunti (segnaposto, riquadro, vie fra cui scegliere)."""
    f = [riga.get("luogo_fonte")] + [c.get("fonte") for c in riga.get("vie_candidate") or []]
    out = []
    for x in f:
        if x and x not in out:
            out.append(x)
    return out
