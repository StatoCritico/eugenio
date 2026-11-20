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
class Mgp:
    """Lavoro `mercato-mgp` (20/11/2026): serie aggiuntive dell'MGP, curve aggregate, offerte pubbliche. Solo uso interno."""
    abilitato: bool = True
    max_minuti: int = 45                   # tempo massimo a notte, recupero dello storico compreso
    inizio_serie: dt.date | None = None    # liquidità, transiti, fabbisogno (None = [gme].inizio_orario, 1/4/2004)
    giorni_riverifica: int = 7             # serie piccole: riscarica gli ultimi N giorni (rettifiche)
    domanda_offerta: bool = True           # curve aggregate (ME_DemandAndSupply), un file al giorno
    domanda_offerta_inizio: dt.date = dt.date(2025, 10, 1)
    domanda_offerta_giorni_per_notte: int = 7
    offerte: bool = True                   # offerte pubbliche (Offers_PublicDomain), un file al giorno
    offerte_inizio: dt.date = dt.date(2025, 10, 1)
    offerte_giorni_per_notte: int = 3      # giorni dello storico all'indietro per notte
    offerte_ritardo_giorni: int = 8        # il GME le pubblica dopo 7 giorni: si chiedono fino a oggi − 8
    pausa_s: float = 20.0                    # pausa gentile fra due richieste grandi (curve, offerte)
    giorni_ferma: int = 4                  # email se una fonte non porta dati nuovi da tanti giorni
    offerte_max_gb: float = 12.0             # oltre, niente più storico delle offerte (i giorni nuovi sì)
    spazio_minimo_gb: float = 8.0            # spazio libero sotto cui ci si ferma (e si avvisa)


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
    mgp: Mgp = field(default_factory=Mgp)          # mercato del giorno prima: offerte pubbliche e serie aggiuntive

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
    m, base_mgp = raw.get("mgp", {}), Mgp()
    mgp = Mgp(**{k: (_data(v) if isinstance(getattr(base_mgp, k), dt.date) or k == "inizio_serie"
                     else type(getattr(base_mgp, k))(v))
                 for k, v in m.items() if k in Mgp.__dataclass_fields__})
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
        mgp=mgp,
    )
