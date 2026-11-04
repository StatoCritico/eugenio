"""Analisi avanzate degli edifici (§ 9 della proposta, analisi 5 e 7–13): interfacce pubbliche e aggancio facoltativo.

Decisione del 03/11/2026 sulle metodiche UNI (RIEPILOGO): coefficienti, prospetti e passaggi presi dalle norme stanno
in un **modulo privato** sul server, fuori dal repository (`fase10-edifici3d/uni_privato/`, in `.gitignore` e fuori
dallo zip pubblico). Qui c'è solo ciò che serve al codice pubblico per parlare con quel modulo:
  - l'elenco delle analisi con la pagina del sito che le ospita (nessun dato delle norme);
  - la forma della richiesta e del risultato (dizionari JSON, versione dell'interfaccia `INTERFACCIA`);
  - il caricamento del modulo privato, se c'è, e lo stato di ogni analisi.

Se il modulo manca (mirror, repository pubblico, installazione nuova), o se le sue tabelle non sono ancora compilate a
mano, ogni analisi risponde «analisi non disponibile in questa installazione» e le pagine del sito lo scrivono così.

Dove si cerca il modulo privato (il primo che esiste):
  1. la variabile d'ambiente `UNI_PRIVATO` (cartella del pacchetto `uni_privato`, oppure la cartella che lo contiene);
  2. `/dati/uni_privato` (sul server: `/srv/energia/dati/uni_privato`, montato nel container dell'api);
  3. `fase10-edifici3d/uni_privato` accanto a questo pacchetto (sul PC di sviluppo).

Contratto con il modulo privato (versione 1):
  uni_privato.INTERFACCIA            int, deve valere `INTERFACCIA`
  uni_privato.stato() -> dict        {id: {"disponibile": bool, "motivo": str}} per le analisi che conosce
  uni_privato.calcola(id, richiesta) -> dict   risultato (vedi `controlla_risultato`); solleva NonDisponibile se manca
                                     qualcosa (tabella non compilata, passaggio non ancora scritto)

Il codice pubblico non legge mai le tabelle del modulo privato né le restituisce: il risultato contiene solo numeri
calcolati per l'edificio dell'utente, con le fonti citate per nome (mai prospetti o estratti delle norme).
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

log = logging.getLogger(__name__)

INTERFACCIA = 1
NON_DISPONIBILE = "analisi non disponibile in questa installazione"
QUI = Path(__file__).resolve().parent.parent


class NonDisponibile(Exception):
    """L'analisi non si può fare qui: modulo privato assente, tabelle da compilare o passaggio non scritto."""


@dataclass(frozen=True)
class Analisi:
    id: str
    nome: str
    pagina: str                         # pagina del sito (fase5-sito/sito)
    norme: bool                         # True se servono coefficienti o passaggi presi da norme (modulo privato)
    dati: tuple[str, ...]               # dati d'ingresso, in parole
    uscite: tuple[str, ...]             # cosa restituisce, in parole
    avvertenze: tuple[str, ...] = field(default_factory=tuple)


# Elenco delle analisi del § 9 gestite dal modulo privato. Testi descrittivi scritti da EuGEnio: nessun contenuto delle
# norme. Le pagine sono quelle del menu del 03/11/2026.
ANALISI: dict[str, Analisi] = {a.id: a for a in (
    Analisi("5", "Fabbisogno con le metodiche UNI", "edificio-fabbisogno.html", True,
            ("geometria dei corpi (indicatori dell'analisi 1)", "clima mensile e orario del comune",
             "ipotesi su involucro, impianti ed epoca di costruzione (modificabili dall'utente)"),
            ("fabbisogno per riscaldamento e raffrescamento", "confronto con il consumo reale", "scenari di intervento"),
            ("I risultati dipendono dalle ipotesi dell'utente: sono stime, non un attestato.",)),
    Analisi("7", "Comunità energetiche per cabina primaria", "edificio-cer.html", False,
            ("producibilità FV per edificio (analisi 6)", "consumi orari o mensili delle sedi",
             "perimetro della cabina primaria (fonte con licenza compatibile da trovare)"),
            ("energia condivisa stimata per cabina", "autoconsumo e quota condivisa per sede"),
            ("Nessun contenuto del GSE: i perimetri pubblicati dal GSE hanno licenza CC BY-NC-SA 3.0 IT, incompatibile.",)),
    Analisi("8", "Apporti solari sulle facciate", "edificio-involucro.html", True,
            ("facciate esposte segmento per segmento (Fase B)", "ombre del contesto", "clima orario",
             "superfici vetrate e schermature indicate dall'utente"),
            ("apporti estivi (surriscaldamento) e invernali persi per orientamento",)),
    Analisi("9", "Ostruzione del cielo e luce naturale", "fv-leed.html", False,
            ("scena 3D dei corpi entro 250 m", "orizzonte del terreno"),
            ("fattore di vista del cielo per facciata", "indicatori di prefattibilità LEED"),
            ("La prefattibilità LEED è indicativa: non sostituisce la verifica di un professionista accreditato.",)),
    Analisi("10", "Pompe di calore con le temperature orarie reali", "edificio-impianti.html", True,
            ("fabbisogno (analisi 5)", "temperature orarie dell'archivio meteo", "dati di targa della macchina"),
            ("COP orario e SCOP stagionale stimati", "energia elettrica assorbita")),
    Analisi("11", "Solare termico per l'acqua calda sanitaria", "edificio-impianti.html", True,
            ("tetti e ombre (analisi 6)", "clima orario", "fabbisogno di acqua calda indicato dall'utente"),
            ("copertura solare mensile e annua",)),
    Analisi("12", "Tetti freddi e tetti verdi", "edificio-involucro.html", True,
            ("tetti dei corpi", "ortofoto (solo per riconoscere il tetto)", "clima orario"),
            ("effetto sul fabbisogno estivo e sull'isola di calore",)),
    Analisi("13", "Clima che cambia: tendenza dei gradi giorno dal 1940", "edificio-clima.html", False,
            ("clima dal 1940 del comune (fase 9)", "firma energetica (analisi 3)"),
            ("tendenza dei gradi giorno", "consumi attesi con il clima che cambia"),
            ("Le proiezioni sono estrapolazioni della tendenza osservata, non scenari climatici ufficiali.",)),
)}


# ---------------------------------------------------------------------------------------------- modulo privato
_modulo: ModuleType | None = None
_caricato_da: Path | None = None
_motivo: str = "non ancora cercato"


def candidati() -> list[Path]:
    out = []
    if os.environ.get("UNI_PRIVATO"):
        out.append(Path(os.environ["UNI_PRIVATO"]))
    out += [Path("/dati/uni_privato"), QUI / "uni_privato"]
    return out


def _cartella_pacchetto(p: Path) -> Path | None:
    """Accetta la cartella del pacchetto (con __init__.py) o quella che contiene `uni_privato/`."""
    if (p / "__init__.py").is_file():
        return p
    if (p / "uni_privato" / "__init__.py").is_file():
        return p / "uni_privato"
    return None


def carica(forza: bool = False) -> ModuleType | None:
    """Il modulo privato, se c'è e parla la stessa interfaccia; altrimenti None (con il motivo in `motivo()`)."""
    global _modulo, _caricato_da, _motivo
    if _modulo is not None and not forza:
        return _modulo
    _modulo, _caricato_da = None, None
    for p in candidati():
        pac = _cartella_pacchetto(p)
        if pac is None:
            continue
        try:
            spec = importlib.util.spec_from_file_location("uni_privato", pac / "__init__.py",
                                                          submodule_search_locations=[str(pac)])
            m = importlib.util.module_from_spec(spec)
            sys.modules["uni_privato"] = m
            spec.loader.exec_module(m)
        except Exception as e:                       # un modulo privato rotto non deve far cadere il servizio
            sys.modules.pop("uni_privato", None)
            _motivo = f"modulo privato in {pac} non caricato: {type(e).__name__}"
            log.warning("%s (%s)", _motivo, e)
            return None
        if getattr(m, "INTERFACCIA", None) != INTERFACCIA:
            sys.modules.pop("uni_privato", None)
            _motivo = f"modulo privato in {pac} con interfaccia {getattr(m, 'INTERFACCIA', None)!r} (attesa {INTERFACCIA})"
            log.warning(_motivo)
            return None
        _modulo, _caricato_da, _motivo = m, pac, "caricato"
        log.info("modulo privato delle analisi caricato da %s", pac)
        return m
    _motivo = "modulo privato assente"
    return None


def motivo() -> str:
    return _motivo


def dimentica() -> None:
    """Per i test: la prossima chiamata a `carica` cerca di nuovo."""
    global _modulo, _caricato_da, _motivo
    _modulo, _caricato_da, _motivo = None, None, "non ancora cercato"
    sys.modules.pop("uni_privato", None)


def stato() -> dict:
    """Disponibilità di ogni analisi, per la rotta /api/analisi/stato e le pagine del sito. Non dice nulla del contenuto
    del modulo privato (né dove si trova): solo sì/no e un messaggio per l'utente."""
    m = carica()
    interno: dict = {}
    if m is not None:
        try:
            interno = m.stato() or {}
        except Exception as e:
            log.warning("stato del modulo privato non letto: %s", e)
            interno = {}
    righe = []
    for a in ANALISI.values():
        s = interno.get(a.id) or {}
        ok = bool(m is not None and s.get("disponibile"))
        righe.append({"id": a.id, "nome": a.nome, "pagina": a.pagina, "disponibile": ok,
                      "messaggio": "analisi disponibile in questa installazione" if ok else NON_DISPONIBILE})
    return {"interfaccia": INTERFACCIA, "modulo": m is not None, "analisi": righe}


def controlla_richiesta(richiesta: dict) -> dict:
    """Forma minima della richiesta: {"edificio": {"corpi": [...]}, "clima": {...}, "ipotesi": {...}, "opzioni": {...}}.
    I corpi sono quelli del § 7 (proprietà di `modello.Corpo.proprieta()`), senza dati personali."""
    if not isinstance(richiesta, dict):
        raise ValueError("la richiesta deve essere un oggetto JSON")
    ed = richiesta.get("edificio") or {}
    corpi = ed.get("corpi") if isinstance(ed, dict) else None
    if not isinstance(corpi, list) or not corpi:
        raise ValueError("servono i corpi dell'edificio (edificio.corpi)")
    if len(corpi) > 500:
        raise ValueError("troppi corpi (massimo 500)")
    for k in ("clima", "ipotesi", "opzioni"):
        if k in richiesta and not isinstance(richiesta[k], dict):
            raise ValueError(f"{k} deve essere un oggetto JSON")
    return richiesta


def controlla_risultato(r: dict) -> dict:
    """Il risultato che esce verso il sito: solo `valori` (numeri e testi brevi), `tabelle` (righe calcolate per
    l'edificio), `avvisi` e `fonti` (nomi delle norme o dei dati, senza estratti). Altre chiavi si scartano."""
    if not isinstance(r, dict):
        raise NonDisponibile(NON_DISPONIBILE)
    return {"valori": r.get("valori") or {}, "tabelle": r.get("tabelle") or [], "avvisi": r.get("avvisi") or [],
            "fonti": r.get("fonti") or [], "stima": True}


def calcola(id: str, richiesta: dict) -> dict:
    """Esegue l'analisi `id` con il modulo privato. NonDisponibile se il modulo non c'è o l'analisi non è pronta."""
    if id not in ANALISI:
        raise KeyError(id)
    m = carica()
    if m is None:
        raise NonDisponibile(NON_DISPONIBILE)
    s = (m.stato() or {}).get(id) or {}
    if not s.get("disponibile"):
        raise NonDisponibile(NON_DISPONIBILE)
    controlla_richiesta(richiesta)
    try:
        r = m.calcola(id, richiesta)
    except NonDisponibile:
        raise
    except Exception as e:
        if type(e).__name__ == "NonDisponibile":       # la classe gemella del modulo privato
            raise NonDisponibile(NON_DISPONIBILE) from e
        raise
    out = controlla_risultato(r)
    out["analisi"] = id
    out["nome"] = ANALISI[id].nome
    return out
