"""Prezzi di elettricità e gas per i clienti non domestici (PMI), Eurostat – su richiesta.

I dati italiani sono forniti a Eurostat da ISTAT/ARERA; semestrali (S1, S2), per fascia di consumo:
  elettricità nrg_pc_205: IA <20 MWh, IB 20–499 MWh, IC 500–1.999 MWh, ID 2.000–19.999 MWh, ...
  gas         nrg_pc_203: I1 <1.000 GJ, I2 1.000–9.999 GJ, I3 10.000–99.999 GJ, ...
Livelli di tassazione: X_TAX (senza imposte), X_VAT (senza IVA), I_TAX (tutto incluso).
"""
from __future__ import annotations

import itertools
import logging
from pathlib import Path

import httpx
import pandas as pd

log = logging.getLogger(__name__)
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
FONTE = "Fonte: Eurostat"


def dataset(codice: str, filtri: dict) -> pd.DataFrame:
    params = []
    for k, v in filtri.items():
        for x in (v if isinstance(v, list) else [v]):
            params.append((k, x))
    r = httpx.get(f"{BASE}/{codice}", params=params, timeout=120)
    r.raise_for_status()
    d = r.json()
    ids, size = d["id"], d["size"]
    cat = [d["dimension"][i]["category"] for i in ids]
    codici = [sorted(c["index"], key=c["index"].get) for c in cat]
    righe = []
    for pos, combo in enumerate(itertools.product(*codici)):
        v = d["value"].get(str(pos))
        if v is not None:
            righe.append({**dict(zip(ids, combo)), "valore": v})
    df = pd.DataFrame(righe)
    if not df.empty and "nrg_cons" in df:
        etichette = d["dimension"]["nrg_cons"]["category"].get("label", {})
        df["fascia_consumo"] = df.nrg_cons.map(etichette)
    return df


def serie(cartella: Path, nome: str, definizione: dict, forza: bool = False) -> pd.DataFrame:
    cache = cartella / "eurostat" / f"{nome}.parquet"
    if cache.exists() and not forza:
        return pd.read_parquet(cache)
    df = dataset(definizione["dataset"], definizione.get("filtri", {}))
    df.insert(0, "serie", nome)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    return df
