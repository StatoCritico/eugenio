"""Indicatori ISTAT su richiesta (SDMX REST, https://esploradati.istat.it/SDMXWS/rest).

ATTENZIONE: ISTAT accetta al massimo 5 richieste al minuto per indirizzo IP e blocca l'IP per
1–2 giorni se si supera il limite. Questo modulo distanzia le richieste di almeno 13 secondi e
mette in cache i risultati: va usato su richiesta, non in un ciclo.

Comandi utili per trovare dataflow e chiavi (cambiano quando ISTAT ribasa gli indici):
  python -m mercati_energia istat cerca FOI
  python -m mercati_energia istat struttura 169_748

Cambi di base (decisione del 28/10/2026): ogni serie configurata con `base` diventa una **serie unica nella base
più recente**. Gli anni pubblicati solo nella base precedente si riportano alla nuova dividendo per il coefficiente
di raccordo ISTAT (media dell'anno di base nella vecchia base / 100, es. FOI 2025 in base 2015 = 121,4 →
coefficiente 1,214). Ogni riga dice se è un valore originale o raccordato e con quale coefficiente.
"""
from __future__ import annotations

import io
import json
import logging
import re
import time
from pathlib import Path

import httpx
import pandas as pd

log = logging.getLogger(__name__)
BASE = "https://esploradati.istat.it/SDMXWS/rest"
FONTE = "Fonte: ISTAT"
_ULTIMA = [0.0]
PAUSA = 13.0


def _get(url: str, accept: str, timeout: float = 300) -> httpx.Response:
    attesa = _ULTIMA[0] + PAUSA - time.time()
    if attesa > 0:
        time.sleep(attesa)
    _ULTIMA[0] = time.time()
    r = httpx.get(url, headers={"Accept": accept, "User-Agent": "progetto-energia/1.0"}, timeout=timeout,
                  follow_redirects=True)
    if r.status_code >= 500:
        raise RuntimeError(f"ISTAT non raggiungibile ({r.status_code}): riprovare più tardi")
    r.raise_for_status()
    return r


def elenco_dataflow(cache: Path) -> pd.DataFrame:
    p = cache / "istat_dataflow.json"
    if p.exists() and time.time() - p.stat().st_mtime < 30 * 86400:
        return pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
    # l'elenco completo (~14 MB, ~5.000 dataflow) può richiedere più di 3 minuti
    x = _get(f"{BASE}/dataflow/IT1", "application/xml", timeout=420).text
    righe = []
    for fid, corpo in re.findall(r'<structure:Dataflow[^>]*\bid="([^"]+)"[^>]*>(.*?)</structure:Dataflow>', x, re.S):
        it = re.findall(r'<common:Name xml:lang="it">([^<]+)</common:Name>', corpo)
        en = re.findall(r'<common:Name xml:lang="en">([^<]+)</common:Name>', corpo)
        righe.append({"id": fid, "nome": (it or en or [""])[0], "nome_en": (en or [""])[0]})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(righe, ensure_ascii=False), encoding="utf-8")
    return pd.DataFrame(righe)


def cerca(cache: Path, testo: str) -> pd.DataFrame:
    df = elenco_dataflow(cache)
    m = df.nome.str.contains(testo, case=False, regex=False) | df.nome_en.str.contains(testo, case=False, regex=False)
    return df[m]


def struttura(dataflow: str) -> str:
    """Dimensioni e codici del dataflow, per costruire la chiave. Due richieste: il dataflow (per sapere qual è la
    sua struttura, DSD) e la struttura con le liste di codici (`references=all` sul dataflow risponde 501)."""
    df = _get(f"{BASE}/dataflow/IT1/{dataflow}", "application/xml").text
    m = re.search(r'<structure:Structure>\s*<Ref[^>]*\bid="([^"]+)"', df) or re.search(r'DataStructure=[^:]+:([^(]+)\(', df)
    if not m:
        raise RuntimeError(f"ISTAT: struttura (DSD) del dataflow {dataflow} non trovata")
    dsd = m.group(1)
    x = _get(f"{BASE}/datastructure/IT1/{dsd}/latest?references=children", "application/xml").text
    dims = re.findall(r'<structure:Dimension[^>]*\bid="([^"]+)"[^>]*position="(\d+)"', x)
    out = [f"Struttura {dsd}", f"Dimensioni (ordine della chiave): "
                                f"{'.'.join(d for d, _ in sorted(dims, key=lambda t: int(t[1])))}"]
    for cl, corpo in re.findall(r'<structure:Codelist[^>]*\bid="([^"]+)"[^>]*>(.*?)</structure:Codelist>', x, re.S):
        codici = re.findall(r'<structure:Code[^>]*\bid="([^"]+)"[^>]*>\s*<common:Name xml:lang="it">([^<]+)', corpo)
        if codici:
            out.append(f"\n{cl}:")
            out += [f"  {c:12s} {n}" for c, n in codici[:60]]
            if len(codici) > 60:
                out.append(f"  … altri {len(codici) - 60}")
    return "\n".join(out)


def raccorda(df: pd.DataFrame, base: dict) -> pd.DataFrame:
    """Serie unica nella base nuova. `df`: colonne periodo, valore, DATA_TYPE (e altre dimensioni).
    base = {tipo: DATA_TYPE della base nuova, precedente: DATA_TYPE della vecchia, anno: anno di base della nuova,
            coefficiente: facoltativo, se ISTAT lo pubblica diverso da quello calcolato, nome: es. "2025=100"}.
    Per ogni periodo vale il dato nella base nuova; dove manca, quello vecchio diviso per il coefficiente."""
    tipo, prec = str(base["tipo"]), str(base["precedente"])
    nome = base.get("nome") or f"{base.get('anno')}=100"
    nuovo = df[df["DATA_TYPE"].astype(str) == tipo].copy()
    vecchio = df[(df["DATA_TYPE"].astype(str) == prec) & ~df["periodo"].isin(nuovo["periodo"])].copy()
    nuovo["valore_originale"] = nuovo["valore"]
    nuovo["raccordato"] = False
    nuovo["coefficiente"] = float("nan")
    if not vecchio.empty:
        k = base.get("coefficiente")
        if k is None:
            anno = str(base["anno"])
            rif = df[(df["DATA_TYPE"].astype(str) == prec) & df["periodo"].astype(str).str.startswith(anno)]["valore"]
            if rif.empty:
                raise RuntimeError(f"ISTAT: per il raccordo manca l'anno {anno} nella base precedente ({prec}); "
                                   "indicare `coefficiente` in configurazione")
            # come ISTAT: media annua arrotondata a un decimale, divisa per 100
            k = round(round(float(rif.mean()), 1) / 100, 3)
        k = float(k)
        vecchio["valore_originale"] = vecchio["valore"]
        vecchio["valore"] = (vecchio["valore"] / k).round(4)
        vecchio["raccordato"] = True
        vecchio["coefficiente"] = k
        log.info("ISTAT: %d periodi riportati in base %s con coefficiente %.3f", len(vecchio), nome, k)
    out = pd.concat([vecchio, nuovo], ignore_index=True) if not vecchio.empty else nuovo
    out["base"] = nome
    return out.sort_values("periodo").reset_index(drop=True)


def serie(cartella: Path, nome: str, definizione: dict, dal: str | None = None, forza: bool = False) -> pd.DataFrame:
    """Scarica (o legge dalla cache) una serie configurata:
       definizione = {dataflow, chiave (facoltativa, '' = tutto), filtri {DIM: valore}, descrizione,
                      base (facoltativa: raccordo dei cambi di base, vedi `raccorda`)}"""
    flusso = definizione["dataflow"]
    cache = cartella / "istat" / f"{nome}_{flusso}.parquet"   # cambiando dataflow non si legge la cache vecchia
    if cache.exists() and not forza:
        return pd.read_parquet(cache)
    chiave = definizione.get("chiave") or "ALL"
    url = f"{BASE}/data/{flusso}/{chiave}/ALL/"
    if dal or definizione.get("dal"):
        url += f"?startPeriod={dal or definizione['dal']}"
    r = _get(url, "application/vnd.sdmx.data+csv;version=1.0.0")
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    for k, v in (definizione.get("filtri") or {}).items():
        if k not in df.columns:
            raise RuntimeError(f"ISTAT {nome}: la dimensione {k} non esiste nel dataflow {flusso} "
                               f"(colonne: {', '.join(df.columns)}). Controllare con `istat struttura {flusso}`")
        df = df[df[k].isin([str(x) for x in v] if isinstance(v, list) else [str(v)])]
    if df.empty:
        raise RuntimeError(f"ISTAT {nome}: nessun dato con chiave/filtri indicati. Controllare con `istat struttura {flusso}`")
    out = pd.DataFrame({"periodo": df["TIME_PERIOD"].to_numpy(),
                        "valore": pd.to_numeric(df["OBS_VALUE"], errors="coerce").to_numpy()})
    dims = [c for c in df.columns if c not in ("DATAFLOW", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS")
            and not c.startswith("NOTE_") and df[c].notna().any()]
    for c in dims:
        out[c] = df[c].to_numpy()
    if "OBS_STATUS" in df:
        out["stato"] = df["OBS_STATUS"].fillna("").to_numpy()      # "p" = provvisorio
    if definizione.get("base"):
        if "DATA_TYPE" not in out:
            raise RuntimeError(f"ISTAT {nome}: `base` richiede la dimensione DATA_TYPE, assente nel dataflow {flusso}")
        out = raccorda(out, definizione["base"])
    out.insert(0, "serie", nome)
    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    return out
