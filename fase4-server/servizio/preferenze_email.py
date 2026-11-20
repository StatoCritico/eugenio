"""Pagina «Newsletter e avvisi» (dati-per-email.html, menu Clima e meteo; 14/11/2026, decisione di Paolo): ognuno sceglie i servizi e l'area dei dati che riceve.

Tre servizi separati, ognuno con la sua lista in listmonk (servizio/listmonk.py):
- **mensile**: fino a EMAIL_MAX_REGIONI regioni; indicatori regionali del mese e valori nazionali dei prezzi;
- **settimanale**: previsioni del tempo della settimana dopo per fino a EMAIL_MAX_COMUNI comuni;
- **avvisi meteo**: domani pioggia forte, neve o vento molto forte nei comuni scelti (gratuito, senza garanzie, non
  sostituisce le allerte della Protezione Civile e degli enti pubblici).

Nessuna password: si chiede un **collegamento personale** per email (verifica anti-robot e limiti per IP e per
indirizzo), valido EMAIL_LINK_GIORNI giorni. Il collegamento conferma che l'indirizzo è di chi lo usa, quindi le liste
scelte arrivano in listmonk già confermate. In fondo a ogni messaggio ci sono il collegamento per cambiare le scelte e
quello per cancellarsi da quel servizio (anche con un clic dal programma di posta, List-Unsubscribe).

Gettoni firmati (HMAC, NOTIZIE_CHIAVE o SESSIONE_CHIAVE): «v1.<scopo>.<scade>.<chi>[.<lista>].<firma>», dove <chi> è
«e<indirizzo in base64>» (collegamento chiesto dalla pagina) o «i<numero dell'iscritto>» (collegamenti nelle email, così
l'indirizzo non compare nei registri del server). Nella pagina il gettone viaggia dopo «#»: non arriva al server
nell'indirizzo, solo nel corpo della richiesta.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import logging
import time
from functools import lru_cache

import httpx
import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import avvisi, config as C, listmonk as L, protezione as P

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email")
PAGINA = "dati-per-email.html"
SERVIZI = ("mensile", "settimanale", "avvisi")
TIPI_AVVISO = ("pioggia", "neve", "vento")
AVVERTENZA_AVVISI = ("Il servizio di avvisi meteo è gratuito, non fornisce garanzie e non sostituisce le allerte della "
                     "Protezione Civile e degli enti pubblici.")


def soglie() -> dict[str, str]:
    return {"pioggia": f"almeno {C.AVVISO_PIOGGIA_24H_MM:g} mm di pioggia nelle 24 ore o {C.AVVISO_PIOGGIA_1H_MM:g} mm "
                       "in un'ora",
            "neve": f"almeno {C.AVVISO_NEVE_CM:g} cm di neve fresca",
            "vento": f"raffiche di almeno {C.AVVISO_VENTO_KMH:g} km/h"}


NOMI_AVVISO = {"pioggia": "Pioggia forte", "neve": "Neve", "vento": "Vento molto forte"}


# ---------------------------------------------------------------------------------------------- gettoni
def _chiave() -> bytes:
    k = C.NOTIZIE_CHIAVE or C.SESSIONE_CHIAVE
    if not k:
        raise HTTPException(503, "Servizio non ancora configurato.")
    return k.encode()


def _firma(corpo: str) -> str:
    return hmac.new(_chiave(), b"email:" + corpo.encode(), hashlib.sha256).hexdigest()[:32]


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _de64(s: str) -> str:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


def gettone(scopo: str, chi: str, giorni: float, lista: int | None = None, ora: float | None = None) -> str:
    """Gettone firmato. `chi`: indirizzo email (contiene «@») o numero dell'iscritto."""
    scade = int((time.time() if ora is None else ora) + giorni * 86400)
    c = f"e{_b64(chi)}" if "@" in str(chi) else f"i{int(chi)}"
    parti = ["v1", scopo, str(scade), c] + ([str(int(lista))] if lista is not None else [])
    corpo = ".".join(parti)
    return f"{corpo}.{_firma(corpo)}"


def leggi_gettone(g: str, scopo: str, ora: float | None = None) -> dict:
    """{"email": …} o {"id": …}, più "lista" se c'è; 401 se il gettone non è valido o è scaduto."""
    parti = (g or "").strip().split(".")
    if len(parti) not in (5, 6) or parti[0] != "v1" or parti[1] != scopo or not parti[2].isdigit():
        raise HTTPException(401, "Collegamento non valido: chiedine uno nuovo.")
    corpo = ".".join(parti[:-1])
    if not hmac.compare_digest(parti[-1], _firma(corpo)):
        raise HTTPException(401, "Collegamento non valido: chiedine uno nuovo.")
    if int(parti[2]) < (time.time() if ora is None else ora):
        raise HTTPException(401, "Collegamento scaduto: chiedine uno nuovo.")
    out: dict = {}
    try:
        if parti[3].startswith("e"):
            out["email"] = _de64(parti[3][1:]).lower()
        elif parti[3].startswith("i") and parti[3][1:].isdigit():
            out["id"] = int(parti[3][1:])
        else:
            raise ValueError
        if len(parti) == 6:
            out["lista"] = int(parti[4])
    except ValueError:
        raise HTTPException(401, "Collegamento non valido: chiedine uno nuovo.")
    return out


def url_preferenze(sid: int) -> str:
    return f"{C.SITO_URL}/{PAGINA}#t={gettone('pref', sid, 90)}"


def url_cancella(sid: int, lista: int) -> str:
    """Pagina che cancella dal servizio (per le persone)."""
    return f"{C.SITO_URL}/{PAGINA}#via={gettone('via', sid, 400, lista)}"


def url_cancella_un_clic(sid: int, lista: int) -> str:
    """Rotta POST per i programmi di posta (List-Unsubscribe-Post, RFC 8058)."""
    return f"{C.SITO_URL}/api/email/via?t={gettone('via', sid, 400, lista)}"


def url_cancella_tutto(sid: int) -> str:
    """(20/11/2026) Rotta POST per i programmi di posta sulle email fuori dai servizi (collegamento personale): toglie
    l'iscritto da tutti i servizi. Mai l'indirizzo email nel gettone (finirebbe nei registri del server)."""
    return f"{C.SITO_URL}/api/email/via-tutto?t={gettone('tutto', sid, 400)}"


# ---------------------------------------------------------------------------------------------- comuni e regioni
@lru_cache(maxsize=2)
def _comuni(mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(C.DATI / "comuni.parquet")
    col = [c for c in ("istat", "nome", "provincia", "regione_cod", "regione", "capoluogo") if c in df.columns]
    df = df[col].copy()
    df["istat"] = df.istat.astype(str)
    return df


def comuni_italia() -> pd.DataFrame:
    """Tutti i comuni di comuni.parquet, anche fuori dalle REGIONI servite: le previsioni dei servizi email si chiedono
    a Open-Meteo per i soli comuni scelti."""
    p = C.DATI / "comuni.parquet"
    return _comuni(p.stat().st_mtime)


def regioni() -> list[dict]:
    cm = comuni_italia()
    if "regione_cod" not in cm:
        return []
    nomi = cm.groupby("regione_cod").regione.first() if "regione" in cm else {}
    return [{"cod": str(k), "nome": str(nomi.get(k, k)).split("/")[0]} for k in sorted(cm.regione_cod.dropna().unique())]


def _pulisci_scelte(dati: dict) -> dict:
    """Controlla e normalizza le scelte della pagina; 422 con il motivo se qualcosa non va."""
    cm = comuni_italia()
    cod_regioni = {r["cod"] for r in regioni()}
    reg = [str(r).zfill(2) for r in (dati.get("regioni") or [])]
    reg = list(dict.fromkeys(reg))
    if len(reg) > C.EMAIL_MAX_REGIONI or any(r not in cod_regioni for r in reg):
        raise HTTPException(422, f"Scegli al massimo {C.EMAIL_MAX_REGIONI} regioni dall'elenco.")
    com = list(dict.fromkeys(str(c).zfill(6) for c in (dati.get("comuni") or [])))
    if len(com) > C.EMAIL_MAX_COMUNI or any(c not in set(cm.istat) for c in com):
        raise HTTPException(422, f"Scegli al massimo {C.EMAIL_MAX_COMUNI} comuni dall'elenco.")
    tipi = [t for t in TIPI_AVVISO if t in set(dati.get("avvisi") or [])]
    servizi = {s: bool(dati.get(s)) for s in ("mensile", "settimanale")}
    servizi["avvisi"] = bool(tipi)
    if (servizi["settimanale"] or servizi["avvisi"]) and not com:
        raise HTTPException(422, "Per le previsioni settimanali e gli avvisi scegli almeno un comune.")
    return {"servizi": servizi, "regioni": reg, "comuni": com, "avvisi": tipi}


def _descrivi(scelte: dict, attive: set[int], liste: dict) -> dict:
    cm = comuni_italia().set_index("istat")
    comuni = [{"istat": c, "nome": str(cm.nome.get(c, c)), "provincia": str(cm.provincia.get(c, "") or "")}
              for c in scelte["comuni"] if c in cm.index]
    return {"mensile": bool(liste.get("mensile")) and liste["mensile"] in attive,
            "settimanale": bool(liste.get("settimanale")) and liste["settimanale"] in attive,
            "avvisi": scelte["avvisi"] if liste.get("avvisi") and liste["avvisi"] in attive else [],
            "regioni": scelte["regioni"], "comuni": comuni}


# ---------------------------------------------------------------------------------------------- rotte
def _attiva() -> None:
    if not (C.NOTIZIE_PERSONALI and L.attivo() and (C.NOTIZIE_CHIAVE or C.SESSIONE_CHIAVE)):
        raise HTTPException(503, "Servizio non ancora configurato.")


@router.get("/opzioni")
def opzioni(request: Request):
    P.limita(request, "dati")
    attivo = bool(C.NOTIZIE_PERSONALI and L.attivo() and (C.NOTIZIE_CHIAVE or C.SESSIONE_CHIAVE))
    return {"attivo": attivo, "max_regioni": C.EMAIL_MAX_REGIONI, "max_comuni": C.EMAIL_MAX_COMUNI,
            "regioni": regioni() if attivo else [], "avvisi": [{"id": t, "nome": NOMI_AVVISO[t], "soglia": soglie()[t]}
                                                              for t in TIPI_AVVISO],
            "avvertenza": AVVERTENZA_AVVISI, "giorno_mensile": C.NOTIZIARIO_GIORNO,
            "settimanale": {"giorno": C.SETTIMANALE_GIORNO, "ora": C.SETTIMANALE_ORA}, "ora_avvisi": C.AVVISI_ORA}


@router.get("/comuni")
def comuni(request: Request):
    """Elenco nazionale dei comuni per la ricerca della pagina (anche fuori dalle regioni servite dal sito)."""
    P.limita(request, "dati")
    cm = comuni_italia()
    col = [c for c in ("istat", "nome", "provincia", "regione_cod") if c in cm.columns]
    t = cm[col].astype(object)
    return t.where(t.notna(), None).to_dict(orient="records")


def _testo_collegamento(url: str) -> tuple[str, str]:
    testo = (f"Ciao,\n\nqualcuno (speriamo tu) ha chiesto di scegliere i dati che EuGEnio ti manda per email.\n\n"
             f"Apri questo collegamento per scegliere servizi, regioni e comuni (vale {C.EMAIL_LINK_GIORNI} giorni):\n"
             f"{url}\n\nSe non sei stato tu, ignora questo messaggio: senza il collegamento non succede niente.\n\n"
             "EuGEnio, un servizio di Stato Critico – eugenio.statocritico.it\n")
    html = (f"<p>Ciao,</p><p>qualcuno (speriamo tu) ha chiesto di scegliere i dati che EuGEnio ti manda per email.</p>"
            f"<p><a href=\"{url}\">Scegli servizi, regioni e comuni</a> (il collegamento vale {C.EMAIL_LINK_GIORNI} "
            "giorni).</p><p>Se non sei stato tu, ignora questo messaggio: senza il collegamento non succede niente.</p>"
            "<p>EuGEnio, un servizio di Stato Critico – eugenio.statocritico.it</p>")
    return testo, html


@router.post("/link")
async def chiedi_link(request: Request, email: str = Body(..., embed=True, max_length=254)):
    """Spedisce il collegamento personale. La risposta è sempre la stessa: non dice se l'indirizzo è già iscritto."""
    _attiva()
    P.limita(request, "email_link")
    P.richiedi_sessione(request)
    email = email.strip().lower()
    if not L.EMAIL_VALIDA.match(email):
        raise HTTPException(422, "Indirizzo email non valido.")
    impronta = hashlib.sha256(b"dest:" + email.encode()).hexdigest()[:24]
    if P.limiti.prova(impronta, "email_dest", C.EMAIL_LINK_GIORNO, 86400):
        url = f"{C.SITO_URL}/{PAGINA}#t={gettone('pref', email, C.EMAIL_LINK_GIORNI)}"
        testo, html = _testo_collegamento(url)
        # (20/11/2026) nostra intestazione «Annulla iscrizione»: per chi è già iscritto toglie da tutti i servizi, per gli
        # altri non fa niente. Senza, OCI metterebbe la sua e l'indirizzo finirebbe nella lista di soppressione.
        try:
            s = await run_in_threadpool(L.iscritto, email)
        except Exception:                                   # listmonk lento o spento: il collegamento parte lo stesso
            s = None
        via_tutto = url_cancella_tutto(int(s["id"])) if s and s.get("id") else None
        try:
            ok = await run_in_threadpool(lambda: avvisi.invia_a(
                email, "EuGEnio – il tuo collegamento per newsletter e avvisi", testo, html,
                cancella=via_tutto, solleva_bloccato=True))
        except avvisi.IndirizzoBloccato:
            log.warning("Dati per email: collegamento chiesto da un indirizzo nella lista di soppressione di OCI")
            avvisi.invia("indirizzo bloccato dal servizio di posta",
                         f"{email} ha chiesto il collegamento per newsletter e avvisi, ma è nella lista di soppressione "
                         f"di OCI Email Delivery (di solito dopo «Annulla iscrizione» dal programma di posta).\n"
                         f"Se la richiesta è sua: cloud.oracle.com › Email Delivery › Suppression List (compartimento "
                         f"radice), togliere l'indirizzo e rispondergli di riprovare.")
            raise HTTPException(409, "Email non spedita: questo indirizzo è bloccato dal servizio di posta, di solito "
                                     "perché in passato è stato usato «Annulla iscrizione» del programma di posta su "
                                     "un'email di EuGEnio. Abbiamo avvisato l'amministratore, che può sbloccarlo: "
                                     f"scrivici da {C.SITO_URL}/contatti.html e ti rispondiamo quando è fatto.")
        if not ok:
            raise HTTPException(503, "Email non spedita: riprova tra qualche minuto.")
    else:
        log.info("Dati per email: troppi collegamenti allo stesso indirizzo nelle 24 ore (non spedito)")
    return {"inviato": True}


@router.post("/via-tutto")
async def via_tutto(request: Request, t: str | None = None):
    """(20/11/2026) «Annulla iscrizione» del programma di posta sull'email del collegamento personale: toglie l'iscritto
    da tutti i servizi (resta in listmonk; si reiscrive dalla pagina)."""
    _attiva()
    P.limita(request, "email_pref")
    g = leggi_gettone((t or "")[:2048], "tutto")
    if "id" not in g:
        raise HTTPException(401, "Collegamento non valido.")
    try:
        liste = {v for v in (await run_in_threadpool(L.liste_servizi, False)).values() if v}
        if liste:
            await run_in_threadpool(L.cancella, g["id"], liste)
    except httpx.HTTPError as e:
        log.warning("Dati per email: cancellazione da tutti i servizi non riuscita (%s)", e)
        raise HTTPException(503, "Cancellazione non riuscita: riprova tra poco.")
    log.info("Dati per email: iscritto %s tolto da tutti i servizi con un clic dal programma di posta", g["id"])
    return {"cancellato": "tutti"}


@router.post("/servizio")
async def servizio(request: Request):
    """(20/11/2026) «Annulla iscrizione» sulle email del servizio per l'amministratore: non c'è niente da cancellare (si
    spengono dal .env). La rotta esiste perché la nostra intestazione eviti quella di OCI, che bloccherebbe l'indirizzo."""
    P.limita(request, "email_pref")
    log.info("Email del servizio: richiesta di cancellazione con un clic ignorata (si spengono da EMAIL_AMMINISTRATORE)")
    return {"cancellato": None}


def _chi(t: dict) -> tuple[str, dict | None]:
    if "email" in t:
        return t["email"], L.iscritto(t["email"])
    s = L.iscritto_da_id(t["id"])
    if s is None:
        raise HTTPException(401, "Iscrizione non trovata: chiedi un collegamento nuovo.")
    return s["email"], s


@router.post("/leggi")
async def leggi(request: Request, t: str = Body(..., embed=True, max_length=2048)):
    _attiva()
    P.limita(request, "email_pref")
    g = leggi_gettone(t, "pref")

    def _fai():
        email, s = _chi(g)
        liste = L.liste_servizi(crea=False)
        return {"email": email, **_descrivi(L.scelte(s), L.liste_attive(s) if s else set(), liste)}
    try:
        return await run_in_threadpool(_fai)
    except httpx.HTTPError as e:
        log.warning("Dati per email: listmonk non risponde (%s)", e)
        raise HTTPException(503, "Servizio momentaneamente non disponibile: riprova tra poco.")


@router.post("/salva")
async def salva(request: Request, dati: dict = Body(...)):
    _attiva()
    P.limita(request, "email_pref")
    g = leggi_gettone(str(dati.get("t", ""))[:2048], "pref")
    sc = _pulisci_scelte(dati)

    def _fai():
        email, s = _chi(g)
        liste = L.liste_servizi(crea=True)
        attive = {liste[k] for k in SERVIZI if sc["servizi"][k] and liste.get(k)}
        spente = {liste[k] for k in SERVIZI if not sc["servizi"][k] and liste.get(k)}
        attr = {"regioni": sc["regioni"], "comuni": sc["comuni"], "avvisi": sc["avvisi"],
                "aggiornato": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        L.salva(email, (s or {}).get("name", ""), attive, spente, attr)
        return {"email": email, **_descrivi({"regioni": sc["regioni"], "comuni": sc["comuni"], "avvisi": sc["avvisi"]},
                                            attive, liste)}
    try:
        return await run_in_threadpool(_fai)
    except httpx.HTTPError as e:
        log.warning("Dati per email: salvataggio non riuscito (%s)", e)
        raise HTTPException(503, "Servizio momentaneamente non disponibile: riprova tra poco.")


@router.post("/via")
async def via(request: Request, t: str | None = None):
    """Cancella dal servizio del collegamento. Gettone nell'indirizzo (POST con un clic dei programmi di posta, corpo
    «List-Unsubscribe=One-Click») o nel corpo JSON {"t": …} (pagina del sito)."""
    _attiva()
    P.limita(request, "email_pref")
    if not t:
        try:
            corpo = await request.json()
            t = str(corpo.get("t", "")) if isinstance(corpo, dict) else ""
        except ValueError:
            t = ""
    g = leggi_gettone(t[:2048], "via")
    if "id" not in g or "lista" not in g:
        raise HTTPException(401, "Collegamento non valido.")
    try:
        liste = {v: k for k, v in (await run_in_threadpool(L.liste_servizi, False)).items() if v}
        if g["lista"] not in liste:
            raise HTTPException(404, "Servizio non trovato.")
        await run_in_threadpool(L.cancella, g["id"], {g["lista"]})
    except httpx.HTTPError as e:
        log.warning("Dati per email: cancellazione non riuscita (%s)", e)
        raise HTTPException(503, "Cancellazione non riuscita: riprova tra poco.")
    return {"cancellato": liste[g["lista"]], "preferenze": url_preferenze(g["id"]).split("#", 1)[1]}
