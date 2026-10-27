"""Import di indici mensili da CSV, per i valori che non si possono scaricare liberamente.

Esempi: PSV day-ahead ICIS (riportato in fattura o nei comunicati ARERA), CMEM ARERA, TTF mensile
storico, prezzi pubblicati da una centrale di committenza.

Formato (separatore ; o ,):  indice;mese;valore;unita;fonte
                              PSV_DA;2026-09;41,25;EUR/MWh;comunicato ARERA 2/10/2026
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from . import archivio


def importa_csv(cartella: Path, file: Path) -> int:
    testo = Path(file).read_text(encoding="utf-8-sig")
    sep = ";" if testo.splitlines()[0].count(";") >= 2 else ","
    df = pd.read_csv(io.StringIO(testo), sep=sep, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    mancanti = {"indice", "mese", "valore"} - set(df.columns)
    if mancanti:
        raise ValueError(f"Colonne mancanti: {', '.join(sorted(mancanti))}")
    df["valore"] = pd.to_numeric(df.valore.str.replace(",", ".", regex=False), errors="coerce")
    df["mese"] = pd.to_datetime(df.mese.str.strip(), format="mixed").dt.to_period("M").astype(str)
    df["indice"] = df.indice.str.strip().str.upper()
    for c in ("unita", "fonte"):
        if c not in df:
            df[c] = None
    df["data"] = pd.to_datetime(df.mese + "-01").dt.date
    df = df.dropna(subset=["valore"])
    return archivio.aggiorna(cartella, "indici_importati", df[["indice", "mese", "data", "valore", "unita", "fonte"]],
                             ["indice", "mese"], "data")
