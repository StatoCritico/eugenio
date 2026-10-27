"""Email all'amministratore/autore: errori del notturno, password GME scaduta, nuovi comuni ISTAT,
esito degli invii della newsletter. SMTP: OCI Email Delivery (o qualunque SMTP con STARTTLS)."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from . import config as C

log = logging.getLogger(__name__)


def invia(oggetto: str, testo: str, html_alternativo: str | None = None) -> bool:
    if not (C.SMTP_SERVER and C.EMAIL_AMMINISTRATORE and C.SMTP_MITTENTE):
        log.warning("Email non inviata (SMTP non configurato): %s", oggetto)
        return False
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = f"[EuGEnio] {oggetto}", C.SMTP_MITTENTE, C.EMAIL_AMMINISTRATORE
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
