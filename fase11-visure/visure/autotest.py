"""Controllo di avvio (lo usa l'avviatore prima di passare a una versione nuova, e il comando `prova`).

Legge una piccola visura sintetica incorporata (dati inventati) e controlla i campi principali: se qualcosa non torna
la versione non si usa e l'avviatore torna alla precedente.
"""
from __future__ import annotations

import base64
import zlib

# visura sintetica A/2 (sintetici.visura_a2), PDF compresso
PDF = (
    "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"
)
ATTESO = {"comune": "RIMINI", "codice_comune": "H294", "foglio": "77", "particella": "210", "subalterno": "9",
          "categoria": "A/2", "consistenza": 5.5, "superficie_catastale": 98, "rendita_euro": 568.1,
          "piani_fuori_terra": 3}


def prova() -> tuple[bool, str]:
    try:
        from .lettore import leggi_testo
        from .testo import estrai
        pagine = estrai(zlib.decompress(base64.b64decode(PDF)))
        v = leggi_testo(pagine, file="autotest.pdf")
        if len(v.unita) != 1:
            return False, f"unità lette: {len(v.unita)} invece di 1"
        u = v.unita[0]
        diversi = [k for k, x in ATTESO.items() if u.get(k) != x]
        if diversi:
            return False, "campi diversi dall'atteso: " + ", ".join(diversi)
        if any(s in repr(u) for s in ("PRVLCU75B41H294K", "PROVA LUCIA")):
            return False, "dati personali nei campi dell'unità"
        return True, "lettore a posto"
    except Exception as e:  # noqa: BLE001
        return False, f"errore: {e}"
