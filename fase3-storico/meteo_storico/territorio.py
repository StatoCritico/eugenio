"""Verifica degli aggiornamenti dell'elenco dei comuni (ISTAT) e dei confini (Gramscii).

ISTAT aggiorna l'elenco dei comuni a ogni variazione (fusioni, cambi di provincia, nuovi nomi),
di norma il 1° gennaio e talvolta in corso d'anno. Il comando confronta l'elenco attuale con
quello usato per costruire l'archivio e la revisione Gramscii bloccata con l'ultima pubblicata.
Pensato per girare ogni mese (worker del server) e avvisare l'amministratore.
"""
from __future__ import annotations

import hashlib
import io

import httpx
import pandas as pd

from . import gramscii
from .comuni import ISTAT_ELENCO


def elenco_istat() -> tuple[pd.DataFrame, str]:
    r = httpx.get(ISTAT_ELENCO, timeout=120, follow_redirects=True)
    r.raise_for_status()
    sha = hashlib.sha256(r.content).hexdigest()
    el = pd.read_csv(io.BytesIO(r.content), sep=";", encoding="latin-1", dtype=str)
    df = pd.DataFrame({"istat": el.iloc[:, 4].str.zfill(6), "nome": el.iloc[:, 6], "provincia": el.iloc[:, 14],
                       "belfiore": el.iloc[:, 19], "regione_cod": el.iloc[:, 0].str.zfill(2)})
    return df, sha


def verifica(comuni_attuali: pd.DataFrame) -> dict:
    nuovo, sha = elenco_istat()
    if "regione_cod" in comuni_attuali:   # si confrontano solo le regioni presenti nell'archivio
        nuovo = nuovo[nuovo.regione_cod.isin(set(comuni_attuali.regione_cod))]
    a = comuni_attuali.set_index("istat")
    n = nuovo.set_index("istat")
    aggiunti = sorted(set(n.index) - set(a.index))
    soppressi = sorted(set(a.index) - set(n.index))
    comuni_in_comune = sorted(set(a.index) & set(n.index))
    cambi = []
    for i in comuni_in_comune:
        for campo in ("nome", "provincia", "belfiore"):
            if campo in a.columns and str(a.at[i, campo]) != str(n.at[i, campo]):
                cambi.append({"istat": i, "campo": campo, "prima": a.at[i, campo], "dopo": n.at[i, campo]})
    ultima = gramscii.ultima_revisione()
    return {
        "istat_sha256": sha,
        "comuni_istat": len(nuovo),
        "aggiunti": [{"istat": i, "nome": n.at[i, "nome"]} for i in aggiunti],
        "soppressi": [{"istat": i, "nome": a.at[i, "nome"]} for i in soppressi],
        "modificati": cambi,
        "gramscii_bloccata": gramscii.revisione(),
        "gramscii_ultima": ultima["revisione"],
        "gramscii_modificata_il": ultima["modificato"],
        "da_aggiornare": bool(aggiunti or soppressi or cambi or ultima["revisione"] != gramscii.revisione()),
    }
