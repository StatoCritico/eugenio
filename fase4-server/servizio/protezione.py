"""Protezione dell'API: limiti d'uso, tetti per tutto il sito, verifica anti-robot e avvisi all'amministratore.

Cosa fa (decisione del 29/10/2026):
  * **limiti per indirizzo**: finestra mobile di un'ora per ogni tipo di richiesta. Gli IPv4 contano uno per uno,
    gli IPv6 per **rete /64** (chi ha IPv6 ne ha miliardi di indirizzi: contarli uno per uno non limiterebbe nulla);
    l'indirizzo arriva da Caddy, che mette in X-Forwarded-For il CF-Connecting-IP di Cloudflare (non falsificabile:
    il server è raggiungibile solo dal tunnel). I conteggi stanno in memoria e si azzerano a ogni riavvio; le chiavi
    vuote si cancellano ogni 10 minuti;
  * **tetti per tutti gli utenti insieme**: chiamate Zornade all'ora (la chiave gratuita ne ha 10.000 e le condizioni
    vietano l'estrazione massiva: oltre ZORNADE_TETTO_ORA si risponde 503) e previsioni ammesse insieme
    (PREVISIONI_PARALLELE: modello.py ne calcola una alla volta, le altre aspettano al massimo PREVISIONI_ATTESA_S
    secondi, poi 503);
  * **verifica Cloudflare Turnstile** sulle rotte che costano o consumano quote (previsione, patrimonio,
    geocodifica, particella, estrazione dei dati climatici): la pagina ottiene un gettone Turnstile, lo scambia con
    POST /api/sessione e riceve un **gettone di sessione** firmato (HMAC), valido SESSIONE_MINUTI e legato alla rete
    di chi l'ha chiesto, da mandare nell'intestazione X-EuGEnio-Sessione. Senza TURNSTILE_SITEKEY e
    TURNSTILE_SECRET la verifica è spenta (prove, mirror);
  * **avvisi email**: quando la quota Zornade dell'ora supera ZORNADE_AVVISO_QUOTA (una volta al giorno) e quando la
    stessa rete supera i limiti almeno AVVISO_429_SOGLIA volte al giorno per AVVISO_429_GIORNI giorni consecutivi
    (una volta per serie di giorni). I conteggi dei 429 stanno in PROTEZIONE_DIR/429.json per
    AVVISO_429_CONSERVA_GIORNI giorni (informativa privacy).
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import threading
import time
from collections import deque
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException, Request

from . import avvisi, config as C

log = logging.getLogger(__name__)
ROMA = ZoneInfo("Europe/Rome")
INTESTAZIONE_SESSIONE = "X-EuGEnio-Sessione"
TIPI_PROTETTI = ("previsione", "patrimonio", "geocodifica", "particella", "estrazione")


# ---------------------------------------------------------------------------------------------- indirizzo
def chiave_ip(req: Request) -> str:
    """Indirizzo del visitatore come chiave dei limiti: IPv4 intero, IPv6 come rete /64."""
    grezzo = req.headers.get("x-forwarded-for") or (req.client.host if req.client else "")
    grezzo = grezzo.split(",")[0].strip()
    try:
        ip = ipaddress.ip_address(grezzo)
    except ValueError:
        return grezzo or "?"
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


# ---------------------------------------------------------------------------------------------- finestre mobili
class Limitatore:
    """Conteggi pesati in finestra mobile, per (chiave, tipo). Sicuro tra thread."""

    PULIZIA_S = 600

    def __init__(self):
        self._code: dict[tuple[str, str], list] = {}      # (chiave, tipo) → [deque di (istante, peso), somma, finestra]
        self._blocco = threading.Lock()
        self._pulita = 0.0

    def _coda(self, chiave: str, tipo: str, finestra: float, ora: float) -> list:
        c = self._code.get((chiave, tipo))
        if c is None:
            c = self._code[(chiave, tipo)] = [deque(), 0, finestra]
        c[2] = finestra
        q = c[0]
        while q and ora - q[0][0] > finestra:
            c[1] -= q.popleft()[1]
        return c

    def _pulisci(self, ora: float) -> None:
        if ora - self._pulita < self.PULIZIA_S:
            return
        self._pulita = ora
        for k in list(self._code):
            c = self._code[k]
            q = c[0]
            while q and ora - q[0][0] > c[2]:
                c[1] -= q.popleft()[1]
            if not q:
                del self._code[k]

    def usate(self, chiave: str, tipo: str, finestra: float = 3600, ora: float | None = None) -> int:
        ora = time.time() if ora is None else ora
        with self._blocco:
            return self._coda(chiave, tipo, finestra, ora)[1]

    def prova(self, chiave: str, tipo: str, n: int, finestra: float = 3600, peso: int = 1,
              ora: float | None = None) -> bool:
        """Aggiunge `peso` se resta entro `n`; altrimenti non aggiunge nulla e restituisce False."""
        ora = time.time() if ora is None else ora
        with self._blocco:
            self._pulisci(ora)
            c = self._coda(chiave, tipo, finestra, ora)
            if c[1] + peso > n:
                return False
            c[0].append((ora, peso))
            c[1] += peso
            return True

    def aggiungi(self, chiave: str, tipo: str, peso: int, finestra: float = 3600, ora: float | None = None) -> int:
        """Aggiunge senza controllo (conteggi a consuntivo) e restituisce il totale nella finestra."""
        ora = time.time() if ora is None else ora
        with self._blocco:
            c = self._coda(chiave, tipo, finestra, ora)
            if peso > 0:
                c[0].append((ora, peso))
                c[1] += peso
            return c[1]

    def clear(self) -> None:
        with self._blocco:
            self._code.clear()

    def __len__(self) -> int:
        return len(self._code)


limiti = Limitatore()

# (massimo, finestra in secondi) dei limiti fissi; i tipi in _DINAMICI leggono il valore da config a ogni richiesta
LIMITI: dict[str, tuple[int, int]] = {"converti": (200, 3600), "previsione": (20, 3600), "zornade": (120, 3600),
                                      "patrimonio": (2000, 3600), "report": (60, 3600)}
_DINAMICI = {"dati": lambda: C.LIMITE_DATI_ORA, "sessione": lambda: C.SESSIONI_ORA,
             "stima": lambda: C.STORICI_STIME_ORA, "estrazione": lambda: C.STORICI_ESTRAZIONI_ORA}
_UNITA = {"patrimonio": "edifici", "estrazione": "download", "stima": "stime", "sessione": "verifiche"}


def soglia(tipo: str) -> tuple[int, int]:
    if tipo in LIMITI:
        return LIMITI[tipo]
    return _DINAMICI[tipo](), 3600


def limita(req: Request, tipo: str, peso: int = 1) -> None:
    """429 se l'indirizzo ha già usato tutto il suo limite orario per `tipo`."""
    chiave = chiave_ip(req)
    n, finestra = soglia(tipo)
    if not limiti.prova(chiave, tipo, n, finestra, peso):
        registro_429.registra(chiave, tipo)
        unita = _UNITA.get(tipo, "richieste")
        raise HTTPException(429, f"Troppe richieste: massimo {n} {unita} all'ora. Riprova più tardi.")


# ---------------------------------------------------------------------------------------------- tetti globali
_TUTTI = "*"
_avvisi_inviati: dict[str, str] = {}          # tipo di avviso → giorno dell'ultimo invio
_blocco_avvisi = threading.Lock()


def _invia_in_sottofondo(oggetto: str, testo: str) -> None:
    threading.Thread(target=avvisi.invia, args=(oggetto, testo), daemon=True, name="avviso").start()


def _una_volta_al_giorno(tipo: str, ora: float | None = None) -> bool:
    oggi = dt.datetime.fromtimestamp(time.time() if ora is None else ora, ROMA).date().isoformat()
    with _blocco_avvisi:
        if _avvisi_inviati.get(tipo) == oggi:
            return False
        _avvisi_inviati[tipo] = oggi
        return True


def zornade_disponibile(previste: int = 1) -> None:
    """503 se le chiamate Zornade previste farebbero superare il tetto orario di tutto il sito."""
    usate = limiti.usate(_TUTTI, "zornade", 3600)
    if usate + previste > C.ZORNADE_TETTO_ORA:
        raise HTTPException(503, "La geocodifica ha esaurito la quota di quest'ora per tutti gli utenti del sito: "
                                 "riprova tra un po'.")


def zornade_conta(chiamate: int) -> None:
    """Conta le chiamate Zornade fatte davvero (la cache non consuma quota) e avvisa oltre la soglia."""
    if chiamate <= 0:
        return
    usate = limiti.aggiungi(_TUTTI, "zornade", chiamate, 3600)
    tetto = C.ZORNADE_TETTO_ORA
    if tetto and usate >= C.ZORNADE_AVVISO_QUOTA * tetto and _una_volta_al_giorno("zornade"):
        log.warning("Zornade: %d chiamate nell'ultima ora (tetto %d)", usate, tetto)
        _invia_in_sottofondo(
            "quota Zornade quasi esaurita",
            f"Nell'ultima ora EuGEnio ha fatto {usate} chiamate a Zornade, il {100 * usate / tetto:.0f} % del tetto "
            f"orario del sito ({tetto}; la chiave gratuita ne permette 10.000).\n\n"
            "Se non è un uso normale (molti file del patrimonio caricati insieme), guarda nel registro di Caddy chi sta "
            "chiamando /api/patrimonio, /api/geocodifica e /api/particella. Oltre il tetto il sito risponde 503 "
            "(«quota di quest'ora esaurita») finché la finestra non si libera.\n\nQuesto avviso parte una volta al giorno.")


_previsioni: asyncio.Semaphore | None = None


@contextlib.asynccontextmanager
async def turno_previsione():
    """Al massimo PREVISIONI_PARALLELE previsioni ammesse insieme; chi aspetta oltre PREVISIONI_ATTESA_S riceve 503."""
    global _previsioni
    if _previsioni is None:
        _previsioni = asyncio.Semaphore(max(1, C.PREVISIONI_PARALLELE))
    try:
        await asyncio.wait_for(_previsioni.acquire(), C.PREVISIONI_ATTESA_S)
    except (asyncio.TimeoutError, TimeoutError):
        raise HTTPException(503, "Il server sta già calcolando altre previsioni: riprova tra un minuto.")
    try:
        yield
    finally:
        _previsioni.release()


# ---------------------------------------------------------------------------------------------- Turnstile e sessione
def turnstile_attivo() -> bool:
    return bool(C.TURNSTILE_SITEKEY and C.TURNSTILE_SECRET)


_chiave_casuale = secrets.token_bytes(32)


def _chiave_firma() -> bytes:
    return C.SESSIONE_CHIAVE.encode() if C.SESSIONE_CHIAVE else _chiave_casuale


def _impronta(rete: str) -> str:
    """La rete non entra in chiaro nel gettone: solo un'impronta firmata."""
    return hmac.new(_chiave_firma(), b"rete:" + rete.encode(), hashlib.sha256).hexdigest()[:16]


def _firma(corpo: str) -> str:
    return hmac.new(_chiave_firma(), corpo.encode(), hashlib.sha256).hexdigest()[:32]


def crea_sessione(rete: str, ora: float | None = None) -> tuple[str, int]:
    scade = int(time.time() if ora is None else ora) + 60 * C.SESSIONE_MINUTI
    corpo = f"1.{scade}.{_impronta(rete)}"
    return f"{corpo}.{_firma(corpo)}", scade


def sessione_valida(gettone: str | None, rete: str, ora: float | None = None) -> bool:
    parti = (gettone or "").strip().split(".")
    if len(parti) != 4 or parti[0] != "1" or not parti[1].isdigit():
        return False
    corpo = ".".join(parti[:3])
    if not hmac.compare_digest(parti[3], _firma(corpo)):
        return False
    if int(parti[1]) < (time.time() if ora is None else ora):
        return False
    return hmac.compare_digest(parti[2], _impronta(rete))


def richiedi_sessione(req: Request) -> None:
    """401 se la verifica anti-robot è accesa e manca un gettone di sessione valido per questa rete."""
    if not turnstile_attivo():
        return
    if not sessione_valida(req.headers.get(INTESTAZIONE_SESSIONE), chiave_ip(req)):
        raise HTTPException(401, "Serve la verifica anti-robot: ricarica la pagina e riprova.",
                            headers={"X-EuGEnio-Verifica": "1"})


async def verifica_turnstile(token: str, ip: str | None) -> bool:
    """Chiede a Cloudflare se il gettone Turnstile è valido (monouso, scade dopo 5 minuti)."""
    dati = {"secret": C.TURNSTILE_SECRET, "response": token}
    if ip and ip != "?" and "/" not in ip:
        dati["remoteip"] = ip
    try:
        async with httpx.AsyncClient(timeout=10) as cl:
            r = await cl.post(C.TURNSTILE_URL, data=dati)
        esito = r.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning("Turnstile: verifica non riuscita (%s)", e)
        raise HTTPException(503, "La verifica anti-robot non risponde: riprova tra poco.")
    if not esito.get("success"):
        log.info("Turnstile: gettone rifiutato %s", esito.get("error-codes"))
        return False
    if C.TURNSTILE_HOSTNAME and esito.get("hostname") not in C.TURNSTILE_HOSTNAME:
        log.info("Turnstile: nome del sito inatteso %s", esito.get("hostname"))
        return False
    return True


# ---------------------------------------------------------------------------------------------- 429 ripetuti
class Registro429:
    """Conteggio giornaliero dei 429 per rete, su file, con avviso quando si ripetono per più giorni consecutivi."""

    SCRIVI_OGNI_S = 60

    def __init__(self):
        self._blocco = threading.Lock()
        self._dati: dict | None = None
        self._scritto = 0.0
        self._cartella = None

    def _file(self):
        return C.PROTEZIONE_DIR / "429.json"

    def _carica(self) -> dict:
        if self._dati is not None and self._cartella == C.PROTEZIONE_DIR:
            return self._dati
        self._cartella = C.PROTEZIONE_DIR
        try:
            d = json.loads(self._file().read_text(encoding="utf-8"))
            assert isinstance(d.get("giorni"), dict) and isinstance(d.get("avvisati"), dict)
        except FileNotFoundError:
            d = {"giorni": {}, "avvisati": {}}
        except Exception:
            log.warning("429.json illeggibile: si riparte da zero")
            d = {"giorni": {}, "avvisati": {}}
        self._dati = d
        return d

    def _salva(self, ora: float) -> None:
        try:
            self._file().parent.mkdir(parents=True, exist_ok=True)
            tmp = self._file().with_suffix(".tmp")
            tmp.write_text(json.dumps(self._dati, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._file())
            self._scritto = ora
        except OSError as e:
            log.warning("429.json non scritto: %s", e)

    def serie(self, rete: str, giorno: dt.date) -> list[tuple[str, int]]:
        """Giorni consecutivi fino a `giorno` con almeno AVVISO_429_SOGLIA rifiuti, dal più vecchio."""
        d = self._carica()
        out = []
        while True:
            n = d["giorni"].get(giorno.isoformat(), {}).get(rete, 0)
            if n < C.AVVISO_429_SOGLIA:
                break
            out.append((giorno.isoformat(), n))
            giorno -= dt.timedelta(days=1)
        return out[::-1]

    def registra(self, rete: str, tipo: str, ora: float | None = None) -> bool:
        """Conta un 429; True se è partito l'avviso email."""
        ora = time.time() if ora is None else ora
        oggi = dt.datetime.fromtimestamp(ora, ROMA).date()
        avviso = None
        with self._blocco:
            d = self._carica()
            g = d["giorni"].setdefault(oggi.isoformat(), {})
            n = g[rete] = g.get(rete, 0) + 1
            if n == C.AVVISO_429_SOGLIA:
                s = self.serie(rete, oggi)
                if len(s) >= C.AVVISO_429_GIORNI and d["avvisati"].get(rete) != s[0][0]:
                    d["avvisati"][rete] = s[0][0]      # una volta per serie di giorni
                    avviso = s
            limite = (oggi - dt.timedelta(days=C.AVVISO_429_CONSERVA_GIORNI - 1)).isoformat()
            for k in [k for k in d["giorni"] if k < limite]:
                del d["giorni"][k]
            for k in [k for k, v in d["avvisati"].items() if v < limite]:
                del d["avvisati"][k]
            if avviso or n == C.AVVISO_429_SOGLIA or ora - self._scritto > self.SCRIVI_OGNI_S:
                self._salva(ora)
        if avviso:
            righe = "\n".join(f"  {g}: {n} richieste rifiutate" for g, n in avviso)
            log.warning("429 ripetuti da %s per %d giorni", rete, len(avviso))
            _invia_in_sottofondo(
                f"limiti superati per {len(avviso)} giorni di fila da {rete}",
                f"La rete {rete} ha superato i limiti dell'API almeno {C.AVVISO_429_SOGLIA} volte al giorno per "
                f"{len(avviso)} giorni consecutivi:\n{righe}\n\nUltimo limite superato oggi: {tipo}.\n\n"
                "Può essere un programma che usa il servizio al posto delle persone. Se vuoi bloccarlo: Cloudflare → "
                "statocritico.it → Security → WAF → Tools → IP Access Rules, valore "
                f"{rete}, azione Block (o Managed Challenge).\n\n"
                "Per questa serie di giorni non arriveranno altri avvisi su questa rete. I conteggi si cancellano dopo "
                f"{C.AVVISO_429_CONSERVA_GIORNI} giorni.")
        return bool(avviso)

    def svuota(self) -> None:
        with self._blocco:
            self._dati = {"giorni": {}, "avvisati": {}}


registro_429 = Registro429()
