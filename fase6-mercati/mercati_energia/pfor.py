"""Ricostruzione dell'indice PFOR,t dell'ARERA (discontinuato dal 1° ottobre 2022).

Definizione originale (TIVG, art. 6.2 lett. c, fino al 30/9/2022): PFOR,t, in euro/GJ, è la
"media aritmetica delle quotazioni forward trimestrali OTC relative al trimestre t-esimo del gas,
presso l'hub TTF, rilevate da ICIS-Heren con riferimento al secondo mese solare antecedente il
trimestre t-esimo". Le quotazioni sono in euro/MWh e si convertono in euro/GJ dividendo per 3,6
(esempio ARERA, delib. 241/2020: III trimestre 2020 → media di maggio 2020 = 5,861184 €/MWh →
1,628107 €/GJ). Il valore è unico per il trimestre: i tre mesi hanno lo stesso PFOR.
Dal 1/10/2022 la delibera 374/2022 lo ha sostituito con la media mensile del PSV day-ahead (CMEM,m).

Qui lo si ricalcola con lo stesso metodo su dati aggiornati, in due modi:
  forward   come ARERA: quotazioni giornaliere del prodotto TTF "trimestre t" rilevate nel secondo
            mese prima del trimestre. Ogni notte si leggono i prezzi di regolamento dei future
            trimestrali TTF che il sito EEX mostra a scopo informativo (eex.ttf_trimestrali): sono
            usati solo qui, mai mostrati né esportati. Al posto delle quotazioni OTC ICIS-Heren
            (a pagamento) si usano quelle della borsa EEX sullo stesso prodotto; si possono anche
            importare da CSV con `importa-forward` (data;trimestre;prezzo, es. 2026-11-03;2027-Q1;31,2).
            Il sito EEX tiene solo i contratti ancora quotati: il primo trimestre ricostruito così è il
            I/2027 (rilevazione: novembre 2026);
  spot      STIMA per i trimestri precedenti, quando mancano le forward: media del TTF Neutral Gas
            Price giornaliero (EEX) nello stesso mese di rilevazione. Risente dell'andamento del
            mercato a pronti, non della curva a termine: va dichiarato come stima.
Per i trimestri fino al III/2022 si possono importare i valori ufficiali ARERA (indice PFOR_ARERA).
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from . import archivio

PCS_GJ_SMC = 0.03852   # potere calorifico superiore convenzionale ARERA, GJ/Smc


def mese_rilevazione(trimestre: pd.Period) -> pd.Period:
    """Secondo mese solare antecedente il trimestre (es. 2020Q3 → maggio 2020)."""
    return trimestre.asfreq("M", how="start") - 2


def _trimestre(testo: str) -> pd.Period:
    t = str(testo).strip().upper().replace(" ", "").replace("-", "").replace("/", "")
    # forme accettate: 2027Q1, Q12027, Q127, 1Q2027
    if t[:4].isdigit():
        return pd.Period(f"{t[:4]}Q{t[-1]}", freq="Q")
    if t.startswith("Q"):
        anno = t[2:]
        anno = int(anno) + 2000 if len(anno) == 2 else int(anno)
        return pd.Period(f"{anno}Q{t[1]}", freq="Q")
    return pd.Period(f"{t[2:]}Q{t[0]}", freq="Q")


def importa_forward(cartella: Path, file: Path) -> int:
    testo = Path(file).read_text(encoding="utf-8-sig")
    sep = ";" if testo.splitlines()[0].count(";") >= 2 else ","
    df = pd.read_csv(io.StringIO(testo), sep=sep, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    out = pd.DataFrame({
        "data": pd.to_datetime(df["data"], dayfirst=not df["data"].str.match(r"^\d{4}-").all()).dt.date,
        "trimestre": df["trimestre"].map(lambda x: str(_trimestre(x))),
        "prezzo": pd.to_numeric(df["prezzo"].str.replace(",", ".", regex=False), errors="coerce"),
        "fonte": df.get("fonte", pd.Series([None] * len(df))),
    }).dropna(subset=["prezzo"])
    return archivio.aggiorna(cartella, "ttf_forward", out, ["data", "trimestre"], "data")


def scarica_forward(sorgente: dict) -> pd.DataFrame:
    """Download automatico delle forward da una fonte a cui si ha accesso (abbonamento EEX DataSource,
    ICE, report di un fornitore...), configurata in [pfor.sorgente]: url di un CSV, credenziali da
    variabili d'ambiente, nomi delle colonne. Senza fonte configurata non fa nulla."""
    import os

    import httpx
    url = sorgente.get("url")
    if not url:
        return pd.DataFrame()
    auth = None
    if sorgente.get("utente_env"):
        auth = (os.environ.get(sorgente["utente_env"], ""), os.environ.get(sorgente.get("password_env", ""), ""))
    r = httpx.get(url, auth=auth, timeout=120, follow_redirects=True)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep=sorgente.get("separatore", ";"), dtype=str)
    col = sorgente.get("colonne", {})
    out = pd.DataFrame({
        "data": pd.to_datetime(df[col.get("data", "data")], dayfirst=sorgente.get("giorno_prima", False)).dt.date,
        "trimestre": df[col.get("trimestre", "trimestre")].map(lambda x: str(_trimestre(x))),
        "prezzo": pd.to_numeric(df[col.get("prezzo", "prezzo")].str.replace(",", ".", regex=False), errors="coerce"),
        "fonte": sorgente.get("nome", url),
    })
    return out.dropna(subset=["prezzo"])


def calcola(cartella: Path, dal: str = "2022Q4", al: str | None = None) -> pd.DataFrame:
    """PFOR per trimestre e mese. Usa le forward dove ci sono, altrimenti la stima dallo spot."""
    fw = archivio.leggi(cartella, "ttf_forward")
    spot = archivio.leggi(cartella, "ttf_eex")
    if al is None:
        al = str(pd.Timestamp.today().to_period("Q") + 1)   # il trimestre prossimo è già calcolabile
    righe = []
    for q in pd.period_range(pd.Period(dal, "Q"), pd.Period(al, "Q"), freq="Q"):
        m = mese_rilevazione(q)
        valore, metodo, n = None, None, 0
        if not fw.empty:
            s = fw[(fw.trimestre == str(q)) & (pd.to_datetime(fw.data).dt.to_period("M") == m)]
            if len(s):
                valore, metodo, n = float(s.prezzo.mean()), "forward", len(s)
        if valore is None and not spot.empty:
            s = spot[pd.to_datetime(spot.data).dt.to_period("M") == m]
            if len(s):
                valore, metodo, n = float(s.prezzo.mean()), "stima_spot", len(s)
        if valore is None:
            continue
        # provvisorio finché il mese di rilevazione non è finito o se mancano troppe sedute
        completo = (n >= 15 if metodo == "forward" else n >= 28) and m < pd.Timestamp.today().to_period("M")
        for mese in pd.period_range(q.asfreq("M", "start"), q.asfreq("M", "end"), freq="M"):
            righe.append({"mese": str(mese), "trimestre": str(q), "mese_rilevazione": str(m), "metodo": metodo,
                          "quotazioni": n, "provvisorio": not completo,
                          "pfor_eur_mwh": round(valore, 6), "pfor_eur_gj": round(valore / 3.6, 6),
                          "pfor_eur_smc": round(valore / 3.6 * PCS_GJ_SMC, 6)})
    return pd.DataFrame(righe)


def come_indici(df: pd.DataFrame) -> list[tuple]:
    """Righe per indici_mensili: PFOR (€/MWh), PFOR_GJ (€/GJ), PFOR_SMC (€/Smc)."""
    out = []
    for r in df.itertuples():
        out += [("PFOR", r.mese, r.pfor_eur_mwh, r.quotazioni), ("PFOR_GJ", r.mese, r.pfor_eur_gj, r.quotazioni),
                ("PFOR_SMC", r.mese, r.pfor_eur_smc, r.quotazioni)]
    return out
