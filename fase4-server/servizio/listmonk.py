"""Client dell'API di listmonk (notizie.statocritico.it) per i servizi email personali (14/11/2026).

Tre liste, una per servizio: «EuGEnio mensile» (LISTA_MENSILE, pubblica, doppia conferma: c'è anche nel modulo di
listmonk), «EuGEnio settimanale» e «EuGEnio avvisi meteo» (private: si gestiscono solo dalla pagina del sito «Dati per
email», perché senza comuni scelti non avrebbero niente da spedire). Le scelte dell'iscritto stanno negli attributi,
sotto la chiave `eugenio`: {"regioni": [...], "comuni": [...], "avvisi": [...], "aggiornato": "..."}; gli altri
attributi restano com'erano.

I messaggi personali partono con l'API transazionale (/api/tx) e un modello «tx» che contiene solo l'oggetto e l'HTML
preparati dal worker (MODELLO_TX, creato da solo se manca).
"""
from __future__ import annotations

import logging
import re

import httpx

from . import config as C

log = logging.getLogger(__name__)
MODELLO_TX = "EuGEnio – messaggio personale"
CHIAVE = "eugenio"
EMAIL_VALIDA = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]{1,63}(\.[A-Za-z0-9\-]{1,63})+$")


class NonConfigurato(RuntimeError):
    pass


def attivo() -> bool:
    return bool(C.LISTMONK_API_UTENTE and C.LISTMONK_API_TOKEN)


def _h() -> dict:
    if not attivo():
        raise NonConfigurato("listmonk non configurato (LISTMONK_API_UTENTE, LISTMONK_API_TOKEN)")
    return {"Authorization": f"token {C.LISTMONK_API_UTENTE}:{C.LISTMONK_API_TOKEN}"}


def _url(percorso: str) -> str:
    return f"{C.LISTMONK_URL.rstrip('/')}/api/{percorso.lstrip('/')}"


def _get(percorso: str, **params) -> dict:
    r = httpx.get(_url(percorso), headers=_h(), params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", {})


def _invia(metodo: str, percorso: str, dati: dict) -> dict:
    r = httpx.request(metodo, _url(percorso), headers=_h(), json=dati, timeout=30)
    r.raise_for_status()
    try:
        return r.json().get("data", {})
    except ValueError:
        return {}


# ---------------------------------------------------------------------------------------------- liste
def _liste() -> list[dict]:
    d = _get("lists", per_page="all")
    return d.get("results", []) if isinstance(d, dict) else list(d or [])


def lista(nome: str, configurata: int = 0, crea: bool = True) -> int | None:
    """Numero della lista: quello del .env se c'è, altrimenti cercata per nome e, se manca, creata (privata, doppia
    conferma: le iscrizioni dalla pagina del sito arrivano già confermate dal collegamento personale)."""
    if configurata:
        return configurata
    for l in _liste():
        if l.get("name") == nome:
            return int(l["id"])
    if not crea:
        return None
    d = _invia("POST", "lists", {"name": nome, "type": "private", "optin": "double",
                                 "tags": ["eugenio"], "description": "Gestita dalla pagina «Newsletter e avvisi» di EuGEnio"})
    log.info("listmonk: creata la lista «%s» (%s)", nome, d.get("id"))
    return int(d["id"])


def liste_servizi(crea: bool = True) -> dict[str, int | None]:
    return {"mensile": C.LISTA_MENSILE or None,
            "settimanale": lista(C.NOME_LISTA_SETTIMANALE, C.LISTA_SETTIMANALE, crea),
            "avvisi": lista(C.NOME_LISTA_AVVISI, C.LISTA_AVVISI, crea)}


def doppia_conferma(lista_id: int) -> bool:
    try:
        d = _get(f"lists/{lista_id}")
    except httpx.HTTPError:
        return True
    return d.get("optin", "double") == "double"


# ---------------------------------------------------------------------------------------------- iscritti
def iscritto(email: str) -> dict | None:
    """L'iscritto con questo indirizzo (minuscolo), o None. L'indirizzo è già controllato con EMAIL_VALIDA: niente apici
    nella condizione SQL che listmonk riceve."""
    email = email.strip().lower()
    if not EMAIL_VALIDA.match(email):
        return None
    d = _get("subscribers", query=f"subscribers.email = '{email}'", per_page=1)
    ris = d.get("results") or []
    return ris[0] if ris else None


def iscritto_da_id(sid: int) -> dict | None:
    try:
        return _get(f"subscribers/{int(sid)}") or None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


def liste_attive(s: dict) -> set[int]:
    """Liste a cui l'iscritto riceve davvero (non cancellato)."""
    return {int(l["id"]) for l in s.get("lists", []) if l.get("subscription_status") != "unsubscribed"}


def scelte(s: dict | None) -> dict:
    a = ((s or {}).get("attribs") or {}).get(CHIAVE) or {}
    return {"regioni": list(a.get("regioni") or []), "comuni": list(a.get("comuni") or []),
            "avvisi": list(a.get("avvisi") or [])}


def salva(email: str, nome: str, attive: set[int], spente: set[int], attributi: dict) -> dict:
    """Crea o aggiorna l'iscritto: liste `attive` già confermate (l'indirizzo è confermato dal collegamento personale),
    via dalle liste `spente`, attributi `eugenio` sostituiti (gli altri restano)."""
    email = email.strip().lower()
    s = iscritto(email)
    if s is None:
        if not attive:
            return {}
        return _invia("POST", "subscribers", {"email": email, "name": nome or email.split("@")[0],
                                              "status": "enabled", "lists": sorted(attive),
                                              "attribs": {CHIAVE: attributi}, "preconfirm_subscriptions": True})
    attr = dict(s.get("attribs") or {})
    attr[CHIAVE] = attributi
    tutte = (liste_attive(s) | attive) - spente
    d = _invia("PUT", f"subscribers/{s['id']}", {"email": s["email"], "name": nome or s.get("name") or email,
                                                 "status": s.get("status", "enabled"), "lists": sorted(tutte),
                                                 "attribs": attr, "preconfirm_subscriptions": True})
    togli = spente & {int(l["id"]) for l in s.get("lists", [])}
    if togli:
        cancella(int(s["id"]), togli)
    return d


def cancella(sid: int, liste: set[int]) -> None:
    """Toglie l'iscritto dalle liste (resta in listmonk: cancellazione dei dati con il collegamento di listmonk)."""
    _invia("PUT", "subscribers/lists", {"ids": [int(sid)], "action": "unsubscribe", "target_list_ids": sorted(liste)})


def destinatari(lista_id: int) -> list[dict]:
    """Iscritti attivi della lista: abilitati, non cancellati e, se la lista è a doppia conferma, confermati."""
    doppia = doppia_conferma(lista_id)
    d = _get("subscribers", list_id=lista_id, per_page="all")
    out = []
    for s in d.get("results") or []:
        if s.get("status") != "enabled":
            continue
        stato = next((l.get("subscription_status") for l in s.get("lists", []) if int(l["id"]) == lista_id), None)
        if stato == "unsubscribed" or (doppia and stato != "confirmed"):
            continue
        out.append(s)
    return out


# ---------------------------------------------------------------------------------------------- messaggi personali
CORPO_TX = "{{ .Tx.Data.html | Safe }}"


def modello_tx() -> int:
    """Numero del modello transazionale (creato la prima volta): oggetto e corpo vengono dai dati del messaggio."""
    d = _get("templates")
    for m in d if isinstance(d, list) else d.get("results", []):
        if m.get("name") == MODELLO_TX and m.get("type") == "tx":
            return int(m["id"])
    d = _invia("POST", "templates", {"name": MODELLO_TX, "type": "tx", "subject": "{{ .Tx.Data.oggetto }}",
                                     "body": CORPO_TX})
    log.info("listmonk: creato il modello transazionale (%s)", d.get("id"))
    return int(d["id"])


def messaggio(sid: int, modello: int, oggetto: str, html: str, via: str | None = None) -> None:
    """Un messaggio a un iscritto. `via`: indirizzo di cancellazione con un clic (intestazioni List-Unsubscribe)."""
    dati = {"subscriber_id": int(sid), "template_id": int(modello), "content_type": "html",
            "data": {"oggetto": oggetto, "html": html}}
    if via:
        dati["headers"] = [{"List-Unsubscribe": f"<{via}>"}, {"List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}]
    _invia("POST", "tx", dati)
