"""Archivio Parquet: un file per dataset e anno, aggiornato per chiave (upsert)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def _scrivi(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    df.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(p)


def aggiorna(cartella: Path, dataset: str, nuovi: pd.DataFrame, chiavi: list[str], col_data: str) -> int:
    """Inserisce o sostituisce le righe per chiave. Restituisce il numero di righe scritte."""
    if nuovi is None or nuovi.empty:
        return 0
    anni = pd.to_datetime(nuovi[col_data]).dt.year
    for anno, parte in nuovi.groupby(anni):
        p = cartella / dataset / f"{anno}.parquet"
        if p.exists():
            vecchio = pd.read_parquet(p)
            tutto = pd.concat([vecchio, parte], ignore_index=True)
        else:
            tutto = parte
        tutto = tutto.drop_duplicates(chiavi, keep="last").sort_values(chiavi).reset_index(drop=True)
        _scrivi(tutto, p)
    return len(nuovi)


def leggi(cartella: Path, dataset: str, dal=None, al=None, col_data: str | None = None) -> pd.DataFrame:
    d = cartella / dataset
    if not d.exists():
        return pd.DataFrame()
    file = sorted(d.glob("*.parquet"))
    if dal is not None:
        file = [f for f in file if int(f.stem) >= pd.Timestamp(dal).year]
    if al is not None:
        file = [f for f in file if int(f.stem) <= pd.Timestamp(al).year]
    if not file:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in file], ignore_index=True)
    if col_data and (dal is not None or al is not None):
        t = pd.to_datetime(df[col_data])
        if dal is not None:
            df = df[t >= pd.Timestamp(dal)]
        if al is not None:
            df = df[t <= pd.Timestamp(al)]
    return df.reset_index(drop=True)


def ultima_data(cartella: Path, dataset: str, col_data: str):
    d = cartella / dataset
    file = sorted(d.glob("*.parquet")) if d.exists() else []
    if not file:
        return None
    return pd.to_datetime(pd.read_parquet(file[-1], columns=[col_data])[col_data]).max().date()


def dimensioni(cartella: Path) -> dict[str, int]:
    out = {}
    for d in sorted(p for p in cartella.iterdir() if p.is_dir()) if cartella.exists() else []:
        out[d.name] = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    return out


def registra_esecuzione(cartella: Path, esito: dict) -> None:
    p = cartella / "ultima_esecuzione.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(esito, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def prima_data(cartella: Path, dataset: str, col_data: str):
    d = cartella / dataset
    file = sorted(d.glob("*.parquet")) if d.exists() else []
    if not file:
        return None
    return pd.to_datetime(pd.read_parquet(file[0], columns=[col_data])[col_data]).min().date()


def stato_storico(cartella: Path) -> dict:
    p = cartella / "storico.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def salva_stato_storico(cartella: Path, stato: dict) -> None:
    p = cartella / "storico.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(stato, indent=1, default=str), encoding="utf-8")
