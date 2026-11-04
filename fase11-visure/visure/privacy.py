"""Controllo di anonimato delle visure prima di condividerle (per esempio come visure di prova per il progetto).

Conta, pagina per pagina, codici fiscali, partite IVA, date e luoghi di nascita, righe di intestatari e diritti, senza
mai stamparne il contenuto: dice solo dove guardare. Una visura è «anonimizzata» quando i conteggi sono tutti zero.
"""
from __future__ import annotations

from pathlib import Path

from .regole import Regole, carica
from .testo import estrai

VOCI = {"codice_fiscale": "codici fiscali o partite IVA", "nascita": "nascite (nato/nata a, il)",
        "diritto": "diritti e quote", "sezione": "righe di intestazione"}


def controlla_testo(pagine: list[str], R: Regole | None = None) -> dict:
    R = R or carica()
    out = {"pagine": {}, "totale": 0}
    for n, t in enumerate(pagine, 1):
        conta = {}
        for voce in VOCI:
            k = sum(len(p.findall(t)) for p in R.lista("personali", voce))
            if k:
                conta[voce] = k
        if conta:
            out["pagine"][n] = conta
            out["totale"] += sum(conta.values())
    return out


def controlla_pdf(percorso: str | Path, R: Regole | None = None) -> dict:
    return controlla_testo(estrai(percorso), R)


def descrivi(nome: str, esito: dict) -> str:
    if not esito["totale"]:
        return f"{nome}: nessun dato personale riconosciuto (controlla comunque a vista prima di condividere)"
    parti = [f"pag. {p}: " + ", ".join(f"{k} {VOCI[v]}" for v, k in c.items()) for p, c in esito["pagine"].items()]
    return f"{nome}: DATI PERSONALI PRESENTI – " + "; ".join(parti)
