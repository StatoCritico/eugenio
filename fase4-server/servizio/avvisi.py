"""Email all'amministratore/autore: errori del notturno, password GME scaduta, nuovi comuni ISTAT,
esito degli invii della newsletter. SMTP: OCI Email Delivery (o qualunque SMTP con STARTTLS).

(20/11/2026) Ogni email spedita da qui porta la **nostra** intestazione List-Unsubscribe (HTTPS, un clic, RFC 8058).
OCI Email Delivery aggiunge la sua solo alle email che non ne hanno una HTTPS: con la sua, «Annulla iscrizione» di Gmail
mette l'indirizzo nella lista di soppressione di OCI e da lì nessuna email gli arriva più, nemmeno il collegamento per
reiscriversi (successo a Paolo il 19–20/11). Con la nostra il clic arriva a EuGEnio: `/api/email/via-tutto` toglie
l'iscritto dai servizi, `/api/email/servizio` (email per l'amministratore) non fa niente.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from . import config as C

log = logging.getLogger(__name__)

PIEDE_SERVIZIO = ("\n\n--\nEmail del servizio EuGEnio per l'amministratore. Non usare «Annulla iscrizione» del programma di "
                  "posta: si spengono togliendo EMAIL_AMMINISTRATORE dal file .env del server.\n")
SPIEGAZIONE_BLOCCO = ("indirizzo nella lista di soppressione di OCI Email Delivery (di solito dopo «Annulla iscrizione» "
                      "dal programma di posta): toglierlo da cloud.oracle.com › Email Delivery › Suppression List "
                      "(compartimento radice)")


class IndirizzoBloccato(Exception):
    """Il servizio di posta (OCI) rifiuta il destinatario perché è nella lista di soppressione."""


def url_servizio() -> str:
    """Cancellazione con un clic delle email del servizio: la rotta risponde e non fa niente."""
    return f"{C.SITO_URL}/api/email/servizio"


def invia(oggetto: str, testo: str, html_alternativo: str | None = None) -> bool:
    if not C.EMAIL_AMMINISTRATORE:
        log.warning("Email non inviata (SMTP non configurato): %s", oggetto)
        return False
    return invia_a(C.EMAIL_AMMINISTRATORE, f"[EuGEnio] {oggetto}", testo + PIEDE_SERVIZIO, html_alternativo)


def invia_a(destinatario: str, oggetto: str, testo: str, html_alternativo: str | None = None,
            cancella: str | None = None, solleva_bloccato: bool = False) -> bool:
    """Email a un indirizzo qualsiasi (14/11/2026: collegamento personale della pagina «Dati per email», spedito prima che
    l'indirizzo sia in listmonk). Stesso SMTP degli avvisi. `cancella`: indirizzo HTTPS per la cancellazione con un clic
    (predefinito: la rotta che non fa niente). Con `solleva_bloccato` un destinatario nella lista di soppressione di OCI
    solleva IndirizzoBloccato invece di dare False."""
    if not (C.SMTP_SERVER and C.SMTP_MITTENTE and destinatario):
        log.warning("Email non inviata (SMTP non configurato): %s", oggetto)
        return False
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = oggetto, C.SMTP_MITTENTE, destinatario
    # (20/11/2026) nostra intestazione HTTPS: OCI non mette la sua (che porta alla soppressione dell'indirizzo)
    m["List-Unsubscribe"] = f"<{cancella or url_servizio()}>"
    m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    m.set_content(testo)
    if html_alternativo:
        m.add_alternative(html_alternativo, subtype="html")
    try:
        with smtplib.SMTP(C.SMTP_SERVER, C.SMTP_PORTA, timeout=30) as s:
            s.starttls()
            s.login(C.SMTP_UTENTE, C.SMTP_PASSWORD)
            s.send_message(m)
        return True
    except smtplib.SMTPRecipientsRefused as e:
        if "suppress" in str(e).lower():
            log.warning("Email non inviata: %s", SPIEGAZIONE_BLOCCO)
            if solleva_bloccato:
                raise IndirizzoBloccato() from None
            return False
        log.exception("Invio email non riuscito")
        return False
    except Exception:
        log.exception("Invio email non riuscito")
        return False
