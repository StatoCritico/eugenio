"""Newsletter automatica dei dati di EuGEnio (listmonk, notizie.statocritico.it).

Distinta dalla newsletter degli articoli di Stato Critico (Substack, scritta a mano). Una sola
lista, mensile, a cui ci si iscrive dal modulo pubblico con doppia conferma: il giorno
NOTIZIARIO_GIORNO arriva il riepilogo del mese appena concluso (gradi giorno osservati nei capoluoghi
rispetto agli anni precedenti) con gli ultimi prezzi Eurostat dell'energia per le PMI.
Con NOTIZIARIO_INVIO_AUTOMATICO=true (predefinito) le campagne partono da sole; altrimenti restano in
bozza in listmonk. I dati GME e TTF restano interni: non compaiono.
"""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import httpx
import pandas as pd

from . import avvisi, config as C, meteo

log = logging.getLogger(__name__)
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]
FONTE_METEO = "Fonte: elaborazione EuGEnio su dati Open-Meteo.com (ERA5/Copernicus corretto, DWD ICON), CC BY 4.0."


def _num(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _capoluoghi() -> pd.DataFrame:
    cm = meteo.comuni()
    return cm[cm.capoluogo].sort_values("nome") if "capoluogo" in cm else cm.head(0)


def _piede() -> list[str]:
    return ["", f"Previsioni dei consumi per il tuo edificio: {C.SITO_URL}", "",
            "EuGEnio è un servizio di Stato Critico (statocritico.it)."]


# ---------------------------------------------------------------------------------------------- mensile
def testo_mensile(anno: int, mese: int) -> tuple[str, str]:
    nome_mese = f"{MESI[mese - 1]} {anno}"
    righe = [f"# Il freddo di {nome_mese}, comune per comune", ""]
    cap = _capoluoghi()
    g = pd.read_parquet(C.DATI / "giornaliero.parquet", columns=["istat", "data", "gg20", "t_media"])
    g["data"] = pd.to_datetime(g.data)
    g = g[g.istat.isin(cap.istat) & (g.data.dt.month == mese)]
    if not g.empty:
        righe += ["Gradi giorno (base 20 °C) del mese e media dello stesso mese negli anni precedenti in archivio.", "",
                  "| Capoluogo | GG del mese | Media | Scarto | Temperatura media |", "|---|---:|---:|---:|---:|"]
        for r in cap.itertuples():
            x = g[g.istat == r.istat]
            ora = x[x.data.dt.year == anno]
            prima = x[x.data.dt.year < anno].groupby(x.data.dt.year).gg20.sum()
            if ora.empty or prima.empty or len(ora) < 25:
                continue
            gg, media = ora.gg20.sum(), prima.mean()
            scarto = f"{_num(100 * (gg / media - 1), 0)} %" if media > 1 else "—"
            righe.append(f"| {r.nome} | {_num(gg)} | {_num(media)} | {scarto} | {_num(ora.t_media.mean(), 1)} °C |")
        righe += ["", FONTE_METEO, ""]
    e = Path(C.DATI) / "mercati" / "eurostat" / "elettricita_pmi.parquet"
    if e.exists():
        d = pd.read_parquet(e)
        d = d[(d.tax == "X_VAT") & (d.nrg_cons.isin(["MWH20-499", "MWH500-1999"]))]
        if not d.empty:
            ult = d.time.max()
            righe += [f"## Elettricità per le PMI ({ult.replace('-S', ', semestre ')})", ""]
            nomi = {"MWH20-499": "fascia IB, 20–499 MWh/anno", "MWH500-1999": "fascia IC, 500–1.999 MWh/anno"}
            for r in d[d.time == ult].itertuples():
                righe.append(f"- {nomi[r.nrg_cons]}: {_num(r.valore * 1000, 0)} €/MWh, IVA esclusa")
            righe += ["", "Fonte: Eurostat (nrg_pc_205).", ""]
    righe += _piede()
    return f"EuGEnio – il freddo di {nome_mese}", "\n".join(righe)


# ---------------------------------------------------------------------------------------------- invio
def _campagna(lista: int, nome: str, oggetto: str, corpo: str) -> int | None:
    if not (C.LISTMONK_API_UTENTE and C.LISTMONK_API_TOKEN and lista):
        log.info("Newsletter: listmonk non configurato (%s)", nome)
        return None
    h = {"Authorization": f"token {C.LISTMONK_API_UTENTE}:{C.LISTMONK_API_TOKEN}"}
    r = httpx.post(f"{C.LISTMONK_URL}/api/campaigns", headers=h, timeout=30, json={
        "name": nome, "subject": oggetto, "lists": [lista], "type": "regular",
        "content_type": "markdown", "body": corpo})
    r.raise_for_status()
    cid = r.json()["data"]["id"]
    if C.NOTIZIARIO_INVIO_AUTOMATICO:
        httpx.put(f"{C.LISTMONK_URL}/api/campaigns/{cid}/status", headers=h, json={"status": "running"},
                  timeout=30).raise_for_status()
    else:
        avvisi.invia(f"newsletter in bozza: {oggetto}", f"Campagna {cid}: rileggerla e avviarla da {C.NOTIZIE_URL}/admin")
    log.info("Newsletter %s: campagna %s %s", nome, cid, "avviata" if C.NOTIZIARIO_INVIO_AUTOMATICO else "in bozza")
    return cid


def mensile(anno: int | None = None, mese: int | None = None) -> int | None:
    if anno is None:
        ieri = dt.date.today().replace(day=1) - dt.timedelta(days=1)
        anno, mese = ieri.year, ieri.month
    return _campagna(C.LISTA_MENSILE, f"Mensile {anno}-{mese:02d}", *testo_mensile(anno, mese))
