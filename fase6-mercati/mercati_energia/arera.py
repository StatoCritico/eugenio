"""Valori pubblicati dall'ARERA, scaricati in automatico ogni notte.

CMEM,m – componente materia prima gas del Servizio di tutela della vulnerabilità: per delibera
374/2022 è la **media mensile del PSV day-ahead** (quotazioni ICIS-Heren), pubblicata entro i primi
due giorni lavorativi del mese successivo. È quindi, gratis e ufficiale, proprio l'indice "PSV
day-ahead mensile" a cui si legano molte convenzioni (es. CET): lo salviamo come indice `PSV_DA`
(€/MWh) con fonte ARERA.

- Dal 2024: pagina della tutela della vulnerabilità, letta ogni notte (`cmem`).
- Da ottobre 2022 a dicembre 2023: pagina del servizio di tutela 22/23, che non cambia più. I 15 valori
  sono nel file `dati/psv_da_arera_2022_2023.csv` (copiati il 26/10/2026 e controllati: €/MWh = €/GJ × 3,6
  ed €/Smc = €/GJ × 0,03852 per ogni mese) e vanno in archivio ogni notte insieme agli altri (`storico`),
  senza chiamate in rete. `leggi_tabella` sa leggere anche quella pagina, se servisse riscaricarla.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import httpx
import pandas as pd

URL_CMEM = "https://www.arera.it/area-operatori/prezzi-e-tariffe/valore-cmemm-vulnerabili"
URL_CMEM_2223 = "https://www.arera.it/area-operatori/prezzi-e-tariffe/valore-cmemm-servizio-di-tutela-22/23"
FILE_STORICO = Path(__file__).parent / "dati" / "psv_da_arera_2022_2023.csv"
FONTE = "ARERA, CMEM,m tutela della vulnerabilità (media mensile PSV day-ahead)"
MESI = {m: i for i, m in enumerate(["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
                                    "agosto", "settembre", "ottobre", "novembre", "dicembre"], 1)}


def _num(s: str) -> float | None:
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _colonna(intestazione: list[str]) -> tuple[int, float]:
    """Colonna da leggere e fattore per arrivare a €/MWh, dall'intestazione della tabella.

    La pagina della vulnerabilità ha Euro/MWh, Euro/GJ, Euro/Smc; quella del 2022/23 Euro/GJ, Euro/Smc,
    Euro/MWh. Senza intestazione riconoscibile si usa la seconda colonna, come prima."""
    testo = [c.lower().replace(" ", "") for c in intestazione]
    for i, c in enumerate(testo):
        if "mwh" in c:
            return i, 1.0
    for i, c in enumerate(testo):
        if "/gj" in c:
            return i, 3.6
    return 1, 1.0


def leggi_tabella(testo_html: str, fonte: str = FONTE) -> pd.DataFrame:
    tabelle = re.findall(r"<table.*?</table>", testo_html, re.S)
    righe = []
    for t in tabelle:
        anno, col, fattore = None, 1, 1.0
        for r in re.findall(r"<tr.*?</tr>", t, re.S):
            celle = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if not celle:
                continue
            if any("euro" in c.lower() for c in celle[1:]):
                col, fattore = _colonna(celle)
            if re.fullmatch(r"\d{4}", celle[0]):
                anno = int(celle[0])
            elif anno and celle[0].lower() in MESI and len(celle) > col and _num(celle[col]) is not None:
                righe.append({"indice": "PSV_DA", "mese": f"{anno}-{MESI[celle[0].lower()]:02d}",
                              "valore": round(_num(celle[col]) * fattore, 4), "unita": "EUR/MWh", "fonte": fonte})
        if righe:
            break   # la prima tabella con i valori; le altre sono quelle dei cookie
    df = pd.DataFrame(righe)
    if not df.empty:
        df["data"] = pd.to_datetime(df.mese + "-01").dt.date
    return df


def cmem() -> pd.DataFrame:
    r = httpx.get(URL_CMEM, timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (EuGEnio)"})
    r.raise_for_status()
    df = leggi_tabella(r.text)
    if df.empty:
        raise RuntimeError("ARERA: tabella CMEM non trovata (la pagina potrebbe essere cambiata)")
    return df


def storico() -> pd.DataFrame:
    """PSV_DA da ottobre 2022 a dicembre 2023 (CMEM,m del servizio di tutela), dal file nel pacchetto."""
    df = pd.read_csv(FILE_STORICO, sep=";", dtype=str, encoding="utf-8")
    df["valore"] = df.valore.str.replace(",", ".", regex=False).astype(float)
    df["data"] = pd.to_datetime(df.mese + "-01").dt.date
    return df[["indice", "mese", "valore", "unita", "fonte", "data"]]
