"""Configurazione (TOML) con override da variabili d'ambiente per i segreti."""
from __future__ import annotations

import datetime as dt
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Gme:
    abilitato: bool = True
    utente: str = ""
    password_file: str = ""
    inizio_quartorario: dt.date = dt.date(2025, 10, 1)
    inizio_orario: dt.date | None = dt.date(2004, 4, 1)   # MGP attivo dal 1/4/2004 (None = solo quartorario)
    inizio_gas: dt.date = dt.date(2010, 12, 1)            # mercato a pronti del gas (MGAS) da dicembre 2010
    inizio_igi: dt.date = dt.date(2023, 1, 1)             # IGI: il programma trova da solo il primo giorno
    max_minuti_storico: int = 60          # ogni notte, tempo massimo dedicato al recupero dello storico
    giorni_riverifica: int = 7             # ogni notte riscarica anche gli ultimi N giorni (correzioni)
    volumi: bool = True

    def password(self) -> str:
        if os.environ.get("GME_PASSWORD"):
            return os.environ["GME_PASSWORD"]
        p = Path(self.password_file) if self.password_file else None
        return p.read_text(encoding="utf-8").strip() if p and p.exists() else ""


@dataclass
class Config:
    cartella: Path
    gme: Gme
    ttf_eex: bool = True
    ttf_forward_eex: bool = True                   # future trimestrali TTF dal sito EEX, solo per il PFOR
    festivi_extra: list[dt.date] = field(default_factory=list)
    istat: dict = field(default_factory=dict)      # nome → {dataflow, chiave, descrizione}
    eurostat: dict = field(default_factory=dict)   # nome → {dataset, filtri, descrizione}
    convenzioni: Path | None = None
    arera_cmem: bool = True                        # PSV day-ahead mensile ufficiale (ARERA CMEM,m)
    sorveglianza: bool = True                      # controllo notturno delle fonti delle convenzioni
    pfor_sorgente: dict = field(default_factory=dict)   # fonte automatica delle forward TTF, se disponibile

    def percorso(self, *parti) -> Path:
        p = self.cartella.joinpath(*parti)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def _data(v):
    if v in (None, ""):
        return None
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


def carica(path: str | Path) -> Config:
    path = Path(path)
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    base = path.parent

    def p(v):
        q = Path(v)
        return q if q.is_absolute() else (base / q).resolve()

    g = raw.get("gme", {})
    gme = Gme(
        abilitato=g.get("abilitato", True),
        utente=os.environ.get("GME_UTENTE", g.get("utente", "")),
        password_file=str(p(g["password_file"])) if g.get("password_file") else "",
        inizio_quartorario=_data(g.get("inizio_quartorario", "2025-10-01")),
        inizio_orario=_data(g.get("inizio_orario", "2004-04-01")),
        inizio_gas=_data(g.get("inizio_gas", "2010-12-01")),
        inizio_igi=_data(g.get("inizio_igi", "2023-01-01")),
        max_minuti_storico=int(g.get("max_minuti_storico", 60)),
        giorni_riverifica=int(g.get("giorni_riverifica", 7)),
        volumi=bool(g.get("volumi", True)),
    )
    a = raw.get("archivio", {})
    return Config(
        cartella=p(os.environ.get("MERCATI_ARCHIVIO", a.get("cartella", "archivio_mercati"))),
        gme=gme,
        ttf_eex=raw.get("eex", {}).get("ttf", True),
        ttf_forward_eex=raw.get("eex", {}).get("ttf_trimestrali", True),
        festivi_extra=[_data(x) for x in raw.get("calendario", {}).get("festivi_extra", [])],
        istat=raw.get("istat", {}),
        eurostat=raw.get("eurostat", {}),
        convenzioni=p(raw["convenzioni"]["cartella"]) if raw.get("convenzioni", {}).get("cartella") else None,
        arera_cmem=raw.get("arera", {}).get("cmem", True),
        sorveglianza=raw.get("sorveglianza", {}).get("attiva", True),
        pfor_sorgente=raw.get("pfor", {}).get("sorgente", {}),
    )
