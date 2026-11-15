"""Email all'amministratore/autore: errori del notturno, password GME scaduta, nuovi comuni ISTAT,
esito degli invii della newsletter. SMTP: OCI Email Delivery (o qualunque SMTP con STARTTLS)."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from . import config as C

log = logging.getLogger(__name__)


def invia(oggetto: str, testo: str, html_alternativo: str | None = None) -> bool:
    if not C.EMAIL_AMMINISTRATORE:
        log.warning("Email non inviata (SMTP non configurato): %s", oggetto)
        return False
    return invia_a(C.EMAIL_AMMINISTRATORE, f"[EuGEnio] {oggetto}", testo, html_alternativo)


def invia_a(destinatario: str, oggetto: str, testo: str, html_alternativo: str | None = None) -> bool:
    """Email a un indirizzo qualsiasi (14/11/2026: collegamento personale della pagina «Dati per email», spedito prima che
    l'indirizzo sia in listmonk). Stesso SMTP degli avvisi."""
    if not (C.SMTP_SERVER and C.SMTP_MITTENTE and destinatario):
        log.warning("Email non inviata (SMTP non configurato): %s", oggetto)
        return False
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = oggetto, C.SMTP_MITTENTE, destinatario
    m.set_content(testo)
    if html_alternativo:
        m.add_alternative(html_alternativo, subtype="html")
    try:
        with smtplib.SMTP(C.SMTP_SERVER, C.SMTP_PORTA, timeout=30) as s:
            s.starttls()
            s.login(C.SMTP_UTENTE, C.SMTP_PASSWORD)
            s.send_message(m)
        return True
    except Exception:
        log.exception("Invio email non riuscito")
        return False
