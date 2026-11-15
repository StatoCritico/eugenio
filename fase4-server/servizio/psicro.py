"""Serie orarie di temperatura e umidità per il menu «Trattamento aria» (psicrometria, 14/11/2026).

Rotte (limiti delle rotte dei dati più un limite proprio, PSICRO_ORA richieste di serie per IP all'ora):
  GET /api/psicro/disponibilita/{istat}
      periodo coperto, quota del punto meteo e pressione atmosferica che ne deriva, fonte e licenza.
  GET /api/psicro/serie/{istat}?anni=1|2|5|10|20|0
      serie oraria continua in UTC (buchi = null) degli ultimi anni×12 mesi fino all'ultima ora disponibile (0 = tutta
      la serie): temperatura in decimi di °C interi e umidità relativa in % interi.
Archivio: CARTELLA_PSICRO/<istat>.parquet (fase 3, `scarica-psicro`, formato in meteo_storico/psicro.py). Finché il file
di un comune non c'è si usa la serie oraria ICON del server (DATI/orario/<istat>.parquet, dal 14/11/2022) e la risposta
lo dice in `note`; senza l'una e l'altra 503. La pressione viene dalla quota del punto meteo (Copernicus DEM 90 m, la
stessa a cui è riportata la temperatura); se manca, dall'altitudine della casa comunale del DPR 412/93.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from meteo_storico import psicro as A

from . import config as C, meteo, protezione as P

router = APIRouter(prefix="/api/psicro")
ANNI = (1, 2, 5, 10, 20, 0)
LICENZA = "CC BY 4.0 – Weather data by Open-Meteo.com (ERA5/ERA5-Land: Copernicus Climate Change Service; ICON: DWD)"
MANCA = ("l'archivio orario di temperatura e umidità di questo comune non è ancora sul server: arriverà nei prossimi "
         "giorni")
FONTE_RIPIEGO = "ICON storico (DWD) della serie oraria del server"


def pressione(quota: float | None) -> int:
    """Pa, atmosfera standard (stessa formula di psicro.js e dell'Excel): p = 101325·(1 − 2,25577e-5·z)^5,2559."""
    z = 0.0 if quota is None or not math.isfinite(quota) else float(quota)
    return int(round(101325 * (1 - 2.25577e-5 * z) ** 5.2559))


def _data(h: int) -> str:
    return A.tempo_da_ora(h).strftime("%d/%m/%Y")


def _num(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _nome(istat: str) -> str:
    try:
        cm = meteo.comuni()
    except FileNotFoundError:
        raise HTTPException(503, "l'elenco dei comuni non è ancora sul server: riprova più tardi")
    if istat not in set(cm.istat):
        raise HTTPException(404, f"Comune {istat} non disponibile")
    return str(cm.set_index("istat").at[istat, "nome"])


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


@lru_cache(maxsize=2)
def _celle(mtime: float) -> dict:
    p = C.CARTELLA_PSICRO / "celle.parquet"
    try:
        c = pd.read_parquet(p, columns=["istat", "quota"])
    except Exception:
        return {}
    return {str(i): float(q) for i, q in zip(c.istat, c.quota) if pd.notna(q)}


def quota(istat: str, dal_file: float | None = None) -> tuple[float | None, str | None]:
    """(quota in m, nota) – nota None se la quota è quella del punto meteo."""
    if dal_file is not None:
        return dal_file, None
    q = _celle(_mtime(C.CARTELLA_PSICRO / "celle.parquet")).get(istat)
    if q is not None:
        return q, None
    try:
        from . import storici
        d = storici.dpr412()
        alt = d.loc[d.istat == istat, "altitudine"].dropna()
        if len(alt):
            return float(alt.iloc[0]), "Pressione dall'altitudine della casa comunale (DPR 412/93): la quota del punto meteo non è ancora sul server."
    except Exception:
        pass
    return None, "Quota del comune non nota: pressione al livello del mare (101.325 Pa)."


@lru_cache(maxsize=8)
def _serie(percorso: str, mtime: float, ripiego: bool) -> A.Serie:
    if ripiego:
        return A.da_orario(Path(percorso), A.FONTE_ICON)
    return A.leggi(Path(percorso))


def carica(istat: str) -> tuple[A.Serie, bool, float | None]:
    """(serie, ripiego, quota dal file). 503 se non c'è né l'archivio né la serie oraria del server."""
    p = C.CARTELLA_PSICRO / f"{istat}.parquet"
    if p.exists():
        s = _serie(str(p), _mtime(p), False)
        try:
            q = A.info(p)["quota_m"]
        except Exception:
            q = None
        if len(s):
            return s, False, q
    o = C.DATI / "orario" / f"{istat}.parquet"
    if o.exists():
        s = _serie(str(o), _mtime(o), True)
        if len(s):
            return s, True, None
    raise HTTPException(503, MANCA)


def inizio_finestra(prima: int, ultima: int, anni: int) -> int:
    """Prima ora degli ultimi anni×12 mesi che finiscono con `ultima` (compresa); 0 = tutta la serie."""
    if anni == 0:
        return prima
    t = A.tempo_da_ora(ultima + 1) - pd.DateOffset(years=anni)
    return max(prima, int((t - A.EPOCA) // pd.Timedelta(hours=1)))


def anni_interi(prima: int, ultima: int) -> int:
    """Quanti anni interi (di 12 mesi) ci sono tra la prima e l'ultima ora."""
    fine, ini, n = A.tempo_da_ora(ultima + 1), A.tempo_da_ora(prima), 0
    while n < 200 and fine - pd.DateOffset(years=n + 1) >= ini:
        n += 1
    return n


def _anni(n_ore: int) -> float:
    return round(n_ore / 8766, 1)


def _fonti(fonte: np.ndarray, ora: np.ndarray, ripiego: bool) -> tuple[str, list[str]]:
    usate = [int(f) for f in np.unique(fonte)]
    if ripiego:
        return FONTE_RIPIEGO, []
    nomi, righe = [], []
    for f in sorted(usate, key=lambda x: int(np.argmax(fonte == x))):      # in ordine di tempo
        m = fonte == f
        nome = A.NOMI_FONTE.get(f, f"fonte {f}")
        nomi.append(nome)
        if len(usate) > 1:
            righe.append(f"{nome}: {int(m.sum()):,} ore dal {_data(int(ora[m][0]))} al {_data(int(ora[m][-1]))}"
                         .replace(",", "."))
    return "; ".join(nomi), righe


def _lista(v: np.ndarray) -> list:
    ok = np.isfinite(v)
    a = np.where(ok, v, 0).astype(np.int64).astype(object)
    a[~ok] = None
    return a.tolist()


def _base(istat: str) -> dict:
    nome = _nome(istat)
    s, ripiego, q_file = carica(istat)
    q, nota_q = quota(istat, q_file)
    return {"nome": nome, "s": s, "ripiego": ripiego, "quota": q, "nota_quota": nota_q}


@router.get("/disponibilita/{istat}")
def disponibilita(request: Request, istat: str):
    P.limita(request, "dati")
    b = _base(istat)
    s = b["s"]
    prima, ultima = int(s.ora[0]), int(s.ora[-1])
    fonte, _ = _fonti(s.fonte, s.ora, b["ripiego"])
    anni_completi = anni_interi(prima, ultima)
    note = [x for x in (b["nota_quota"],) if x]
    if b["ripiego"]:
        note.insert(0, f"L'archivio dal 1940 di questo comune non è ancora sul server: per ora c'è la serie oraria ICON "
                       f"dal {_data(prima)}.")
    return {"istat": istat, "comune": b["nome"], "quota_m": None if b["quota"] is None else round(b["quota"]),
            "pressione_pa": pressione(b["quota"]), "dal": A.iso(prima), "al": A.iso(ultima),
            "anni_completi": anni_completi, "anni_scelte": [a for a in ANNI if a == 0 or a <= max(anni_completi, 1)],
            "archivio": "orario_icon" if b["ripiego"] else "psicro", "fonte": fonte, "licenza": LICENZA, "note": note}


@lru_cache(maxsize=16)
def _risposta(istat: str, anni: int, chiave: tuple) -> bytes:
    """JSON compatto della serie (in copia: una serie di 87 anni sono ~760.000 ore)."""
    b = _base(istat)
    s, ripiego = b["s"], b["ripiego"]
    prima, ultima = int(s.ora[0]), int(s.ora[-1])
    h0 = inizio_finestra(prima, ultima, anni)
    m = s.ora >= h0
    n = ultima - h0 + 1
    idx = (s.ora[m] - h0).astype(np.int64)
    t = np.full(n, np.nan, dtype=np.float32)
    ur = np.full(n, np.nan, dtype=np.float32)
    t[idx] = s.t[m]
    ur[idx] = s.ur[m]
    fonte, righe_fonti = _fonti(s.fonte[m], s.ora[m], ripiego)
    note = []
    if ripiego:
        note.append(f"L'archivio dal 1940 di questo comune non è ancora sul server: per ora c'è solo la serie oraria "
                    f"ICON dal {_data(prima)} (circa {_num(_anni(ultima - prima + 1))} anni).")
    if anni and anni_interi(prima, ultima) < anni:
        note.append(f"Chiesti {anni} anni: i dati partono dal {_data(prima)}, quindi la serie copre circa "
                    f"{_num(_anni(n))} anni.")
    note += righe_fonti
    if h0 < A.ora_da_tempi(["1950-01-01T00:00Z"])[0] and not ripiego:
        note.append("Prima del 1950 i valori vengono da ERA5 a 0,25° (circa 28 km): meno dettagliati di quelli "
                    "successivi (ERA5-Land, 0,1°).")
    vuote = int(n - np.isfinite(t).sum())
    if vuote:
        note.append(f"{vuote:,} ore senza dati (null).".replace(",", "."))
    if b["nota_quota"]:
        note.append(b["nota_quota"])
    out = {"istat": istat, "comune": b["nome"], "quota_m": None if b["quota"] is None else round(b["quota"]),
           "pressione_pa": pressione(b["quota"]), "inizio": A.iso(h0), "passo_h": 1, "n": int(n),
           "t": _lista(t), "ur": _lista(ur), "dal": A.iso(h0), "al": A.iso(ultima), "anni_richiesti": anni,
           "anni_dati": _anni(n), "fonte": fonte, "licenza": LICENZA, "note": note}
    return json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@router.get("/serie/{istat}")
def serie(request: Request, istat: str, anni: int = 1):
    if anni not in ANNI:
        raise HTTPException(422, "anni deve essere 1, 2, 5, 10, 20 oppure 0 (tutta la serie)")
    P.limita(request, "dati")
    P.limita(request, "psicro")
    _nome(istat)
    p, o = C.CARTELLA_PSICRO / f"{istat}.parquet", C.DATI / "orario" / f"{istat}.parquet"
    chiave = (_mtime(p), _mtime(o), _mtime(C.CARTELLA_PSICRO / "celle.parquet"))
    return Response(_risposta(istat, anni, chiave), media_type="application/json")
