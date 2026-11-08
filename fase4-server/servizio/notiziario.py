"""Newsletter automatica dei dati di EuGEnio (listmonk, notizie.statocritico.it).

Distinta dalla newsletter degli articoli di Stato Critico (Substack, scritta a mano). Una sola
lista, mensile, a cui ci si iscrive dal modulo pubblico con doppia conferma: il giorno
NOTIZIARIO_GIORNO arriva il riepilogo del mese appena concluso (gradi giorno osservati nei capoluoghi
rispetto agli anni precedenti) con gli ultimi prezzi Eurostat dell'energia per le PMI e, dal 07/11/2026, la sezione
«Novità di EuGEnio» con le voci del mese di fase5-sito/novita.toml (registro delle versioni, pagina novita.html).
Con NOTIZIARIO_INVIO_AUTOMATICO=true (predefinito) le campagne partono da sole; altrimenti restano in
bozza in listmonk. I dati GME e TTF restano interni: non compaiono.
"""
from __future__ import annotations

import datetime as dt
import logging
import tomllib
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


def novita_del_mese(anno: int, mese: int, file: Path | None = None) -> list[str]:
    """Righe Markdown della sezione «Novità di EuGEnio»: le voci di novita.toml pubblicate nel mese (vuoto se nessuna)."""
    f = Path(file or C.NOVITA_TOML)
    try:
        voci = tomllib.loads(f.read_text(encoding="utf-8")).get("voce", [])
    except (OSError, ValueError) as e:
        log.info("Newsletter: novità non lette (%s)", e)
        return []
    voci = [v for v in voci if str(v.get("data", "")).startswith(f"{anno}-{mese:02d}-")]
    if not voci:
        return []
    righe = ["## Novità di EuGEnio", ""]
    for v in sorted(voci, key=lambda v: (v["data"], v.get("versione", ""))):
        g = dt.date.fromisoformat(v["data"])
        righe += [f"**{g.day} {MESI[g.month - 1]}: {v['titolo']}**", ""]
        if str(v.get("testo", "")).strip():      # voce senza elenchi (08/11/2026: «Meet EuGEnio», 26/10)
            righe += [str(v["testo"]).strip(), ""]
        # (08/11/2026) gruppi della pagina Novità: Nuovo, Migliorato, Verificato (righe vuote: elenchi Markdown giusti)
        for k, nome in (("nuovo", "Nuovo"), ("migliorato", "Migliorato"), ("verificato", "Verificato")):
            if v.get(k):
                righe += [f"*{nome}*", ""] + [f"- {x}" for x in v[k]] + [""]
    righe += [f"Tutte le novità: {C.SITO_URL}/novita.html", ""]
    return righe


# ---------------------------------------------------------------------------------------------- mensile
def testo_mensile(anno: int, mese: int) -> tuple[str, str]:
    nome_mese = f"{MESI[mese - 1]} {anno}"
    righe = [f"# Il freddo di {nome_mese}, comune per comune", ""]
    cap = _capoluoghi()
    # solo i capoluoghi (filtro sul parquet): il giornaliero nazionale non si carica mai tutto
    g = pd.read_parquet(C.DATI / "giornaliero.parquet", columns=["istat", "data", "gg20", "t_media"],
                        filters=[("istat", "in", [str(i) for i in cap.istat])] if len(cap) else None)
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
    righe += novita_del_mese(anno, mese)
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
