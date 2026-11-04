"""Piani delle visure catastali: dal testo («T-1-2», «S1-T», «PT», «piano terra», «da 1 a 3», «1°-2°», «ammezzato»,
«sottotetto») a livelli numerici, piani fuori terra e interrati.

Convenzioni (§ 13 della proposta): T, PT, R (rialzato) e «terra» = livello 0; S, S1, «seminterrato», «interrato» = -1;
S2 = -2; un numero n = livello n. Il trattino separa piani diversi (uso catastale: «T-1-2» sono tre piani). Ammezzato e
sottotetto si riportano tra le etichette ma non contano come piani: l'ammezzato sta dentro un piano, il sottotetto di
solito non è abitabile. Piani fuori terra = livello più alto + 1 (se c'è almeno un livello ≥ 0); interrati = quanti
livelli sotto lo 0 al massimo.
"""
from __future__ import annotations

import re
import unicodedata

TERRA = {"T", "PT", "P.T.", "PT.", "TERRA", "PIANOTERRA", "R", "PR", "RIALZATO", "PIANORIALZATO", "TR", "P.R."}
INTERRATO = {"S", "SEMINTERRATO", "SEMINT", "SEMINT.", "INTERRATO", "SOTTOSTRADA", "SS", "SI", "SEMI"}
AMMEZZATO = {"AMMEZZATO", "AMM", "AMM.", "AM", "M", "MEZZANINO", "SOPPALCO"}
SOTTOTETTO = {"SOTTOTETTO", "SOFFITTA", "MANSARDA", "SOTT", "SOTT.", "SOTTOT", "SOTTOT."}
PAROLE_VUOTE = {"PIANO", "PIANI", "P", "P.", "E", "ED", "AL", "IL", "DEL", ""}


def _senza_accenti(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def livelli(testo: str | None) -> tuple[list[int], list[str]]:
    """(livelli numerici ordinati senza ripetizioni, etichette non numeriche: «ammezzato», «sottotetto», «?xyz»)."""
    if not testo:
        return [], []
    s = _senza_accenti(str(testo)).upper().strip()
    s = s.replace("PIANO TERRA", "T").replace("PIANO RIALZATO", "R").replace("PIANO SEMINTERRATO", "S1")
    trovati: set[int] = set()
    altri: list[str] = []
    # «da 1 a 3», «dal 2 al 4»
    for a, b in re.findall(r"\bDA(?:L)?\s+(-?\d+)\D{0,3}\s+A(?:L)?\s+(-?\d+)", s):
        lo, hi = sorted((int(a), int(b)))
        if hi - lo <= 60:
            trovati.update(range(lo, hi + 1))
    s = re.sub(r"\bDA(?:L)?\s+-?\d+\D{0,3}\s+A(?:L)?\s+-?\d+", " ", s)
    # S-1, S-2 (interrati scritti col trattino) prima di dividere sui trattini
    s = re.sub(r"\bS\s*-\s*(\d)\b", r"S\1", s)
    # «-1», «-2» isolati (non «T-1», dove il trattino separa due piani)
    s = re.sub(r"(?:(?<=^)|(?<=[\s,;(]))-\s*(\d)\b", r"S\1", s)
    for t in re.split(r"[\s,;/+\-–]+", s):
        t = t.strip("()[]:")
        if t in PAROLE_VUOTE:
            continue
        m = re.fullmatch(r"(\d{1,2})(?:°|º|ª|O|A)?\.?", t)
        if m:
            trovati.add(int(m.group(1)))
            continue
        m = re.fullmatch(r"S(\d)", t) or re.fullmatch(r"(?:INT|SI)(\d)", t)
        if m:
            trovati.add(-int(m.group(1)))
            continue
        if t in TERRA:
            trovati.add(0)
        elif t in INTERRATO:
            trovati.add(-1)
        elif t in AMMEZZATO:
            if "ammezzato" not in altri:
                altri.append("ammezzato")
        elif t in SOTTOTETTO:
            if "sottotetto" not in altri:
                altri.append("sottotetto")
        elif re.fullmatch(r"[A-Z]{1,3}\d?", t) or len(t) > 1:
            altri.append("?" + t.lower())
    return sorted(trovati), altri


def etichetta(n: int) -> str:
    return "T" if n == 0 else (f"S{-n}" if n < 0 else str(n))


def riassumi(insieme: list[int], altri: list[str] | None = None) -> dict:
    """Riepilogo di un insieme di livelli (di un'unità o di tutto l'edificio)."""
    altri = [a for a in (altri or []) if not a.startswith("?")]
    if not insieme:
        return {"piani": ";".join(altri), "piani_fuori_terra": None, "piani_interrati": None, "piano_piu_alto": None}
    sopra = [x for x in insieme if x >= 0]
    sotto = [x for x in insieme if x < 0]
    return {
        "piani": ";".join([etichetta(x) for x in insieme] + altri),
        "piani_fuori_terra": (max(sopra) + 1) if sopra else 0,
        "piani_interrati": (-min(sotto)) if sotto else 0,
        "piano_piu_alto": etichetta(max(insieme)),
    }
