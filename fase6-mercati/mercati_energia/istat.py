"""Indicatori ISTAT su richiesta (SDMX REST, https://esploradati.istat.it/SDMXWS/rest).

ATTENZIONE: ISTAT accetta al massimo 5 richieste al minuto per indirizzo IP e blocca l'IP per
1–2 giorni se si supera il limite. Questo modulo distanzia le richieste di almeno 13 secondi e
mette in cache i risultati: va usato su richiesta, non in un ciclo.

Comandi utili per trovare dataflow e chiavi (cambiano quando ISTAT ribasa gli indici):
  python -m mercati_energia istat cerca FOI
  python -m mercati_energia istat struttura 169_746
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
    x = _get(f"{BASE}/dataflow/IT1", "application/xml").text
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
    """Dimensioni e codici del dataflow, per costruire la chiave."""
    x = _get(f"{BASE}/dataflow/IT1/{dataflow}/latest?references=all&detail=referencepartial",
             "application/xml").text
    dims = re.findall(r'<structure:Dimension[^>]*\bid="([^"]+)"[^>]*position="(\d+)"', x)
    out = [f"Dimensioni (ordine della chiave): {'.'.join(d for d, _ in sorted(dims, key=lambda t: int(t[1])))}"]
    for cl, corpo in re.findall(r'<structure:Codelist[^>]*\bid="([^"]+)"[^>]*>(.*?)</structure:Codelist>', x, re.S):
        codici = re.findall(r'<structure:Code[^>]*\bid="([^"]+)"[^>]*>\s*<common:Name xml:lang="it">([^<]+)', corpo)
        if codici:
            out.append(f"\n{cl}:")
            out += [f"  {c:12s} {n}" for c, n in codici[:60]]
            if len(codici) > 60:
                out.append(f"  … altri {len(codici) - 60}")
    return "\n".join(out)


def serie(cartella: Path, nome: str, definizione: dict, dal: str | None = None, forza: bool = False) -> pd.DataFrame:
    """Scarica (o legge dalla cache) una serie configurata:
       definizione = {dataflow, chiave (facoltativa, '' = tutto), filtri {DIM: valore}, descrizione}"""
    cache = cartella / "istat" / f"{nome}.parquet"
    if cache.exists() and not forza:
        return pd.read_parquet(cache)
    flusso = definizione["dataflow"]
    chiave = definizione.get("chiave") or "ALL"
    url = f"{BASE}/data/{flusso}/{chiave}/ALL/"
    if dal or definizione.get("dal"):
        url += f"?startPeriod={dal or definizione['dal']}"
    r = _get(url, "application/vnd.sdmx.data+csv;version=1.0.0")
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    for k, v in (definizione.get("filtri") or {}).items():
        if k in df.columns:
            df = df[df[k].isin(v if isinstance(v, list) else [v])]
    if df.empty:
        raise RuntimeError(f"ISTAT {nome}: nessun dato con chiave/filtri indicati. Controllare con `istat struttura {flusso}`")
    out = pd.DataFrame({"periodo": df["TIME_PERIOD"], "valore": pd.to_numeric(df["OBS_VALUE"], errors="coerce")})
    dims = [c for c in df.columns if c not in ("DATAFLOW", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS", "NOTE_OBS")]
    for c in dims:
        out[c] = df[c].to_numpy()
    out.insert(0, "serie", nome)
    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    return out
