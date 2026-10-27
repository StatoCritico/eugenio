"""TTF Neutral Gas Price (EEX): prezzo di riferimento giornaliero del gas al TTF olandese.

EEX pubblica gratuitamente il file degli ultimi 60 giorni; scaricandolo ogni notte l'archivio
si allunga senza buchi (60 giorni di margine se il server resta spento). Per lo storico
precedente si possono importare valori da CSV (comando `importa`).
Pagina: https://www.eex.com/en/markets/natural-gas/gas-market-transparency
Prima di ripubblicare i valori controllare le condizioni di licenza degli indici EEX.

Quotazioni dei future trimestrali TTF (`ttf_trimestrali`): sono i prezzi di regolamento
giornalieri che il sito eex.com mostra pubblicamente nel Market Data Hub, "for information purposes
only". EuGEnio le legge a quello scopo e le usa soltanto per calcolare il PFOR,t: non le mostra,
non le espone da nessuna rotta, non le rende scaricabili e non le inoltra a nessuno. Il sito pubblico
tiene solo i contratti ancora quotati e circa le ultime sei settimane di sedute: per questo vanno lette
ogni notte e accumulate (i trimestri già scaduti non si possono recuperare).
"""
from __future__ import annotations

import datetime as dt
import io
import time

import httpx
import pandas as pd

URL_TTF = "https://gasandregistry.eex.com/Gas/NGP/TTF_NGP_60_Days.csv"
FONTE = "Fonte: EEX – TTF Neutral Gas Price"

URL_TABELLA = "https://api.eex-group.com/pub/market-data/table-data"
FONTE_FORWARD = "EEX – Dutch TTF Natural Gas Quarter Future, settlement (sito eex.com, a scopo informativo)"
_INTESTAZIONI = {"User-Agent": "Mozilla/5.0 (EuGEnio; https://eugenio.statocritico.it)",
                 "Origin": "https://www.eex.com", "Referer": "https://www.eex.com/"}


def ttf_ngp() -> pd.DataFrame:
    r = httpx.get(URL_TTF, timeout=60, headers={"User-Agent": "Mozilla/5.0 (progetto-energia)"},
                  follow_redirects=True)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), sep=";", dtype=str)
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("Unnamed")]]
    cols = {c.lower(): c for c in df.columns}
    data = cols.get("delivery date")
    valore = next(c for k, c in cols.items() if k.startswith("index value"))
    volume = next((c for k, c in cols.items() if k.startswith("index volume")), None)
    out = pd.DataFrame({
        "data": pd.to_datetime(df[data]).dt.date,
        "prezzo": pd.to_numeric(df[valore], errors="coerce").astype("float32"),
        "volume_mwh": pd.to_numeric(df[volume], errors="coerce").astype("float64") if volume else None,
        "scambi": pd.to_numeric(df.get(cols.get("number of trades")), errors="coerce"),
    })
    return out.dropna(subset=["data", "prezzo"]).sort_values("data").reset_index(drop=True)


def _scadenza(trimestre: pd.Period) -> int:
    """2027Q1 → 202701 (anno e primo mese del trimestre, come li indica EEX)."""
    return trimestre.year * 100 + (trimestre.quarter - 1) * 3 + 1


def ttf_trimestrali(oggi: dt.date | None = None, trimestri: int = 4, giorni: int = 45,
                    pausa_s: float = 2.0, client: httpx.Client | None = None) -> pd.DataFrame:
    """Prezzi di regolamento dei future TTF per i prossimi `trimestri` trimestri, sedute degli ultimi
    `giorni` giorni. Una richiesta per trimestre, con una pausa tra l'una e l'altra.
    Righe: data (seduta), trimestre ('2027Q1'), prezzo (€/MWh), fonte."""
    oggi = oggi or dt.date.today()
    primo = pd.Period(oggi, "Q") + 1
    c = client or httpx.Client(timeout=60, headers=_INTESTAZIONI)
    righe = []
    try:
        for i in range(trimestri):
            q = primo + i
            r = c.get(URL_TABELLA, params={
                "shortCode": "G3BQ", "commodity": "NATGAS", "pricing": "F", "area": "TTF", "product": "Base",
                "maturity": _scadenza(q), "maturityType": "Quarter", "isRolling": "false",
                "startDate": (oggi - dt.timedelta(days=giorni)).isoformat(), "endDate": oggi.isoformat()})
            r.raise_for_status()
            js = r.json()
            col = {nome: k for k, nome in enumerate(js.get("header", []))}
            for riga in js.get("data", []):
                prezzo = riga[col["settlPx"]]
                if prezzo is not None:
                    righe.append({"data": dt.date.fromisoformat(riga[col["tradeDate"]][:10]),
                                  "trimestre": str(q), "prezzo": float(prezzo), "fonte": FONTE_FORWARD})
            if i < trimestri - 1 and pausa_s:
                time.sleep(pausa_s)
    finally:
        if client is None:
            c.close()
    return pd.DataFrame(righe, columns=["data", "trimestre", "prezzo", "fonte"])
