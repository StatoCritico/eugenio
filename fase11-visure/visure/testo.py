"""Testo delle pagine di un PDF, con le posizioni delle colonne (modalità «layout» di pypdf, BSD-3-Clause).

Nessuna rete, nessun programma esterno: pypdf è puro Python e viaggia con l'avviatore .exe e con l'immagine Docker.
I PDF ricevuti si trattano come non fidati: si leggono solo il testo e il numero di pagine, con un limite di pagine.
"""
from __future__ import annotations

import logging
from pathlib import Path

MAX_PAGINE = 400

logging.getLogger("pypdf").setLevel(logging.ERROR)


def estrai(percorso: str | Path | bytes, max_pagine: int = MAX_PAGINE) -> list[str]:
    import io

    from pypdf import PdfReader
    sorgente = io.BytesIO(percorso) if isinstance(percorso, (bytes, bytearray)) else str(percorso)
    r = PdfReader(sorgente)
    if r.is_encrypted:
        try:
            r.decrypt("")       # molti PDF «protetti» hanno solo la password del proprietario
        except Exception as e:  # noqa: BLE001
            raise ValueError("PDF cifrato con password") from e
    pagine = []
    for i, p in enumerate(r.pages):
        if i >= max_pagine:
            break
        try:
            t = p.extract_text(extraction_mode="layout", layout_mode_space_vertically=False)
        except Exception:       # noqa: BLE001 - qualche PDF non regge la modalità layout
            t = p.extract_text() or ""
        pagine.append(t or "")
    return pagine
