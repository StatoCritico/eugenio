"""Mercato del giorno prima (MGP) del GME: serie aggiuntive, offerte pubbliche, curve ordinate di offerta e domanda.

SOLO USO INTERNO. I dati del GME si usano con la licenza personale e non commerciale dell'API: non si pubblicano, non si
esportano, non vanno sul sito né nella newsletter finché il GME non dà un permesso scritto. Questo modulo scrive solo
nell'archivio dei mercati (sul server /dati/mercati, cartella non servita dal sito) e non ha rotte API né comandi che
esportino le offerte o le curve.

Serie (API del GME, piattaforma PublicMarketResults, comparto MGP; "Servizio API del GME – Guida tecnica", 15/10/2025):
  ME_Liquidity          liquidità, volumi in borsa e fuori borsa                      → mgp_liquidita
  ME_Transits           transiti fra zone (da, a)                                       → mgp_transiti
  ME_Demand             fabbisogno per zona                                             → mgp_fabbisogno
  ME_DemandAndSupply    curve aggregate di domanda e offerta per zona e livello di prezzo
                        (equivale ai file «MGP_DomandaOfferta» dell'area download)      → mgp_domanda_offerta (un file al giorno)
                        e, sommate, offerta e domanda totali per zona e periodo         → mgp_offerta_domanda_totali
  Offers_PublicDomain   offerte pubbliche, tutte (accettate e no), pubblicate dal GME
                        7 giorni dopo; risposta .xml.zip                                → mgp_offerte (un file al giorno)
Prezzi (PUN Index GME e zonali) e quantità acquistate e vendute per zona sono già in gme.prezzi_mgp e gme.volumi_mgp
(lavoro notturno `mercati`).

Tempo: dal 1/10/2025 l'MGP è a 15 minuti (campo Period 1–96, fino a 100 nel giorno di 25 ore); prima orario (Hour 1–25).
Ogni riga ha `data`, `ora`, `periodo`, `minuti` (15 o 60) e `inizio_utc` contati dalla mezzanotte italiana. Nei file a
15 minuti il GME esprime le quantità in MW invece che in MWh (DT «Modifica al formato XSD … offerte a blocchi e a 15'»,
1/10/2025): l'energia di un quarto d'ora è MW × 0,25 h.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import zipfile
import xml.etree.ElementTree as ET
from typing import IO, Iterator

import numpy as np
import pandas as pd

from . import archivio
from .gme import ROMA, ClientGME

log = logging.getLogger(__name__)
SOGLIA_15MIN = dt.date(2025, 10, 1)

# ---------------------------------------------------------------------------------------------- serie JSON
# nome del dataset → (DataName del GME, campi del GME → colonne, chiavi oltre a inizio_utc e minuti)
SERIE = {
    "mgp_liquidita": ("ME_Liquidity", {"Liquidity": "liquidita", "ExchangeVolumes": "volumi_borsa",
                                       "OffExchangeVolumes": "volumi_fuori_borsa"}, []),
    "mgp_transiti": ("ME_Transits", {"From": "da", "To": "a", "Transit": "transito", "Notes": "note"}, ["da", "a"]),
    "mgp_fabbisogno": ("ME_Demand", {"Zone": "zona", "Demand": "fabbisogno"}, ["zona"]),
}
DOMANDA_OFFERTA = ("ME_DemandAndSupply", {"MarketZone": "zona", "Type": "tipo", "Quantity": "quantita",
                                          "AcceptedQuantity": "quantita_accettata", "ZonalPrice": "prezzo_zonale",
                                          "Price": "prezzo", "Notes": "note"})
NUMERICHE = {"liquidita", "volumi_borsa", "volumi_fuori_borsa", "transito", "fabbisogno", "quantita",
             "quantita_accettata", "prezzo_zonale", "prezzo"}
TEMPO = {"flowdate", "hour", "period", "market"}


def _colonna(df: pd.DataFrame, nome: str):
    """Colonna `nome` cercata senza badare alle maiuscole (la guida alterna 'FlowDate' e 'flowDate')."""
    for c in df.columns:
        if str(c).lower() == nome.lower():
            return df[c]
    return None


def tempo(df: pd.DataFrame) -> pd.DataFrame:
    """data, ora, periodo, minuti e inizio_utc da FlowDate/Hour/Period. A 15 minuti dal 1/10/2025 (se c'è Period),
    orario prima; conta gli intervalli dalla mezzanotte italiana, quindi regge i giorni di 23 e 25 ore."""
    giorno = pd.to_datetime(_colonna(df, "FlowDate").astype(str).str[:8], format="%Y%m%d")
    ora = pd.to_numeric(_colonna(df, "Hour"), errors="coerce") if _colonna(df, "Hour") is not None else \
        pd.Series(np.nan, index=df.index)
    per = pd.to_numeric(_colonna(df, "Period"), errors="coerce") if _colonna(df, "Period") is not None else \
        pd.Series(np.nan, index=df.index)
    quarti = (giorno >= pd.Timestamp(SOGLIA_15MIN)) & per.notna()
    minuti = np.where(quarti, 15, 60)
    passi = np.where(quarti, per.fillna(1) - 1, ora.fillna(1) - 1) * minuti
    mezzanotte = giorno.dt.tz_localize(ROMA).dt.tz_convert("UTC")
    return pd.DataFrame({
        "inizio_utc": mezzanotte + pd.to_timedelta(passi, unit="m"),
        "data": giorno.dt.date,
        "ora": ora.astype("Int16"),
        "periodo": pd.Series(np.where(quarti, per, ora), index=df.index).astype("Int16"),
        "minuti": minuti.astype("int16")}, index=df.index)


def normalizza(righe: list[dict], rinomina: dict[str, str]) -> pd.DataFrame:
    """Righe JSON del GME → colonne con nomi italiani e tempo normalizzato. I campi non previsti restano, in minuscolo
    (formati futuri), come testo."""
    if not righe:
        return pd.DataFrame()
    grezzo = pd.DataFrame(righe)
    out = tempo(grezzo)
    minuscole = {k.lower(): v for k, v in rinomina.items()}
    for c in grezzo.columns:
        cl = str(c).lower()
        if cl in TEMPO:
            continue
        nome = minuscole.get(cl, cl)
        if nome in NUMERICHE:
            out[nome] = pd.to_numeric(grezzo[c], errors="coerce").astype("float64")
        else:
            out[nome] = grezzo[c].astype("string")
    return out


def scarica_serie(cl: ClientGME, nome: str, dal: dt.date, al: dt.date) -> pd.DataFrame:
    """Una delle SERIE piccole (liquidità, transiti, fabbisogno) fra `dal` e `al` compresi."""
    data_name, rinomina, _ = SERIE[nome]
    return normalizza(cl.richiesta("MGP", data_name, dal, al), rinomina)


def chiavi(nome: str) -> list[str]:
    return ["inizio_utc", "minuti"] + SERIE[nome][2]


def _scopo(tipo) -> str | None:
    """BID (acquisto, domanda) o OFF (vendita, offerta) dal campo Type delle curve aggregate. La guida non elenca i valori:
    si riconoscono le parole più probabili, il testo originale resta nella colonna `tipo` (da verificare sui dati veri)."""
    t = str(tipo or "").upper()
    if any(p in t for p in ("BID", "ACQ", "DOMAND", "PURCH", "DEMAND", "BUY")):
        return "BID"
    if any(p in t for p in ("OFF", "VEND", "SELL", "SUPPL", "SALE")):
        return "OFF"
    return None


def domanda_offerta(cl: ClientGME, giorno: dt.date) -> pd.DataFrame:
    """Curve aggregate di domanda e offerta di un giorno (ME_DemandAndSupply): per zona, periodo, lato e livello di prezzo,
    quantità offerte e accettate."""
    data_name, rinomina = DOMANDA_OFFERTA
    df = normalizza(cl.richiesta("MGP", data_name, giorno, giorno), rinomina)
    if not df.empty and "tipo" in df:
        df["scopo"] = df["tipo"].map(_scopo).astype("string")
    return df


def totali_offerta_domanda(do: pd.DataFrame) -> pd.DataFrame:
    """Offerta e domanda totali (quantità offerte e accettate) per periodo, zona e lato, sommando le curve aggregate."""
    if do is None or do.empty:
        return pd.DataFrame()
    lato = do["scopo"].fillna(do["tipo"]) if "scopo" in do else do["tipo"]
    g = do.assign(lato=lato.astype(str)).groupby(["inizio_utc", "data", "ora", "periodo", "minuti", "zona", "lato"],
                                                  dropna=False, observed=True)
    out = g.agg(quantita=("quantita", "sum"), quantita_accettata=("quantita_accettata", "sum")).reset_index()
    return out


# ---------------------------------------------------------------------------------------------- offerte pubbliche (XML)
# Legenda della pagina «Download» MGP del GME e DT «Modifica al formato XSD … a 15'» (1/10/2025): dal passaggio ai 15
# minuti spariscono INTERVAL_NO e compaiono OFFER_TYPE, BLOCK_ID, PERIOD, GRANULARITY, MINIMUM_ACCEPTANCE_RATIO.
OFFERTE_DECIMALI = {"QUANTITY_NO", "AWARDED_QUANTITY_NO", "ENERGY_PRICE_NO", "AWARDED_PRICE_NO", "ADJ_QUANTITY_NO",
                    "ADJ_ENERGY_PRICE_NO", "MINIMUM_ACCEPTANCE_RATIO"}
OFFERTE_INTERE = {"MERIT_ORDER_NO": "Int32", "INTERVAL_NO": "Int16", "PERIOD": "Int16", "BID_OFFER_DATE_DT": "Int32",
                  "SUBMITTED_DT": "Int64"}
MINUTI_GRANULARITA = {"PT15": 15, "PT30": 30, "PT60": 60}
STATI_CURVA = ("ACC", "REJ", "PREJ")          # offerte che entrano nell'algoritmo di mercato (non INC, REP, REV, SUB)
BLOCCO_RIGHE = 100_000


def _locale(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_in(dati: bytes, profondita: int = 0) -> Iterator[tuple[str, IO[bytes]]]:
    """File XML contenuti nella risposta: ZIP (anche ZIP dentro ZIP, come in alcune risposte del GME) o XML semplice."""
    if dati[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(dati))
        for n in sorted(z.namelist()):
            if n.lower().endswith(".xml"):
                with z.open(n) as f:
                    yield n, f
            elif n.lower().endswith(".zip") and profondita < 3:
                yield from _xml_in(z.read(n), profondita + 1)
    elif dati.lstrip()[:1] == b"<":
        yield "risposta.xml", io.BytesIO(dati)


def _numero(s: pd.Series) -> pd.Series:
    """Decimali del GME: il punto o la virgola (gli XML degli esiti usano la virgola)."""
    s = s.astype("string").str.strip()
    virgola = s.str.contains(",", regex=False, na=False) & ~s.str.contains(".", regex=False, na=False)
    s = s.where(~virgola, s.str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce").astype("float64")


def _tipizza_offerte(righe: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(righe)
    for c in df.columns:
        if c in OFFERTE_DECIMALI:
            df[c] = _numero(df[c])
        elif c in OFFERTE_INTERE:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype(OFFERTE_INTERE[c])
        else:
            df[c] = df[c].astype("string").str.strip()
    return df


def leggi_offerte_xml(dati: bytes) -> pd.DataFrame:
    """Offerte pubbliche dalla risposta del GME (ZIP con XML «NewDataSet», un elemento per offerta con i campi della
    legenda come figli). Lettura a flusso, a blocchi di righe, per non tenere in memoria l'albero di un file da centinaia
    di MB. Riconosce un'offerta dalla presenza del campo PURPOSE_CD, quindi regge nomi diversi dell'elemento e campi
    nuovi (restano come testo). Aggiunge `data`, `periodo` (PERIOD, o INTERVAL_NO nei file orari) e `minuti` (da
    GRANULARITY; 60 nei file orari)."""
    parti, righe = [], []
    for nome, f in _xml_in(dati):
        pila: list[ET.Element] = []
        for evento, el in ET.iterparse(f, events=("start", "end")):
            if evento == "start":
                pila.append(el)
                continue
            pila.pop()
            if len(el) == 0:
                continue
            campi = {_locale(c.tag): (c.text or "") for c in el if len(c) == 0}
            if "PURPOSE_CD" in campi or _locale(el.tag) == "schema":
                if "PURPOSE_CD" in campi:
                    righe.append(campi)
                if pila:                          # l'elemento letto si stacca dal padre: memoria costante
                    pila[-1].remove(el)
                if len(righe) >= BLOCCO_RIGHE:
                    parti.append(_tipizza_offerte(righe))
                    righe = []
        log.debug("offerte pubbliche: letto %s", nome)
    if righe:
        parti.append(_tipizza_offerte(righe))
    if not parti:
        return pd.DataFrame()
    df = pd.concat(parti, ignore_index=True)
    return completa_offerte(df)


def completa_offerte(df: pd.DataFrame) -> pd.DataFrame:
    """Colonne normalizzate delle offerte: data, periodo, minuti."""
    n = len(df)
    vuoto = pd.Series(pd.NA, index=df.index)
    data = df.get("BID_OFFER_DATE_DT", vuoto)
    df["data"] = pd.to_datetime(data.astype("string"), format="%Y%m%d", errors="coerce").dt.date
    periodo = df["PERIOD"] if "PERIOD" in df else vuoto
    if "INTERVAL_NO" in df:
        periodo = periodo.fillna(df["INTERVAL_NO"])
    df["periodo"] = pd.to_numeric(periodo, errors="coerce").astype("Int16")
    gran = df["GRANULARITY"] if "GRANULARITY" in df else pd.Series([None] * n, index=df.index, dtype="string")
    df["minuti"] = gran.map(MINUTI_GRANULARITA).fillna(60).astype("int16")
    return df


def offerte_pubbliche(cl: ClientGME, giorno: dt.date, attese_quota: int = 1) -> pd.DataFrame:
    """Offerte pubbliche MGP di un giorno di flusso (Offers_PublicDomain, una richiesta). Vuoto se il GME non le ha
    ancora pubblicate (riserbo di 7 giorni)."""
    dati = cl.richiesta("MGP", "Offers_PublicDomain", giorno, giorno, grezzo=True, attese_quota=attese_quota)
    if not dati:
        return pd.DataFrame()
    df = leggi_offerte_xml(dati)
    if not df.empty and "MARKET_CD" in df:
        df = df[df["MARKET_CD"].isna() | (df["MARKET_CD"].str.upper() == "MGP")]
    ordine = [c for c in ("PURPOSE_CD", "ZONE_CD", "UNIT_REFERENCE_NO", "periodo", "MERIT_ORDER_NO") if c in df]
    return df.sort_values(ordine, kind="stable").reset_index(drop=True)   # righe simili vicine: file più piccoli


# ---------------------------------------------------------------------------------------------- curve ordinate
def _copre(offerte: pd.DataFrame, periodo: int, minuti: int) -> pd.Series:
    """Offerte che valgono per il periodo `periodo` di durata `minuti`: un'offerta oraria (PT60, PERIOD h) vale per i
    quattro quarti d'ora dell'ora h, una alla mezz'ora per due."""
    m_off = offerte["minuti"].astype(int)
    atteso = (periodo - 1) * minuti // m_off + 1
    return (m_off >= minuti) & (offerte["periodo"].astype("Int64") == atteso)


def curve_ordinate(offerte: pd.DataFrame, periodo: int, zona: str | list[str] | None = None,
                   minuti: int | None = None, stati: tuple[str, ...] | None = STATI_CURVA,
                   aggrega: bool = False) -> dict[str, pd.DataFrame]:
    """Curve ordinate di offerta (vendite, prezzo crescente) e di domanda (acquisti, prezzo decrescente) di un periodo,
    dalle offerte pubbliche di un giorno. `zona`: codice ZONE_CD, elenco di codici, o None per l'Italia (tutte le zone
    delle offerte). `minuti`: durata del periodo richiesto (predefinita: 15 dal 1/10/2025, 60 prima). `stati`: stati
    delle offerte da tenere (predefiniti accettate e rifiutate; None = tutte). `aggrega=True` somma le offerte allo
    stesso prezzo (curva a gradini). Ogni curva ha prezzo, quantita, quantita_accettata, cumulata, cumulata_accettata
    e, se non aggregata, i riferimenti dell'offerta. Uso interno: la funzione restituisce i dati, non li mostra."""
    if offerte is None or offerte.empty:
        return {"offerta": pd.DataFrame(), "domanda": pd.DataFrame()}
    if minuti is None:
        giorno = offerte["data"].dropna().iloc[0] if offerte["data"].notna().any() else SOGLIA_15MIN
        minuti = 15 if giorno >= SOGLIA_15MIN else 60
    df = offerte[_copre(offerte, periodo, minuti).fillna(False)]
    if zona is not None:
        df = df[df["ZONE_CD"].isin([zona] if isinstance(zona, str) else list(zona))]
    if stati is not None:
        df = df[df["STATUS_CD"].isin(stati)]
    out = {}
    for lato, scopo, crescente in (("offerta", "OFF", True), ("domanda", "BID", False)):
        p = df[df["PURPOSE_CD"] == scopo]
        c = pd.DataFrame({
            "prezzo": p["ENERGY_PRICE_NO"].astype("float64"),
            "quantita": p["QUANTITY_NO"].astype("float64"),
            "quantita_accettata": (p["AWARDED_QUANTITY_NO"] if "AWARDED_QUANTITY_NO" in p
                                   else pd.Series(0.0, index=p.index)).astype("float64").fillna(0.0),
            "stato": p["STATUS_CD"],
            "zona": p.get("ZONE_CD"), "unita": p.get("UNIT_REFERENCE_NO"),
            "tipo_offerta": p.get("OFFER_TYPE"), "granularita": p.get("GRANULARITY"),
            "merit_order": p.get("MERIT_ORDER_NO")})
        c = c.sort_values(["prezzo", "merit_order"], ascending=[crescente, True], na_position="last", kind="stable")
        if aggrega:
            c = (c.groupby("prezzo", sort=False)
                  .agg(quantita=("quantita", "sum"), quantita_accettata=("quantita_accettata", "sum"),
                       offerte=("quantita", "size")).reset_index())
            c = c.sort_values("prezzo", ascending=crescente, kind="stable")
        c = c.reset_index(drop=True)
        c["cumulata"] = c["quantita"].cumsum()
        c["cumulata_accettata"] = c["quantita_accettata"].cumsum()
        out[lato] = c
    return out


def curve(cartella, giorno: dt.date, periodo: int, zona: str | list[str] | None = None, **kw) -> dict[str, pd.DataFrame]:
    """Curve ordinate di un giorno, periodo e zona (o Italia) dalle offerte pubbliche in archivio (vedi curve_ordinate).
    Vuote se il giorno non è ancora stato scaricato."""
    return curve_ordinate(archivio.leggi_giorno(cartella, "mgp_offerte", giorno), periodo, zona, **kw)
