"""File del sito per la pagina «Produzione e consumi di elettricità» (Statistiche) – in lavorazione (20/11/2026).

  costruisci(raw: Path, uscita: Path) -> dict
      legge <raw>/<dataset>_<anno>.json scritti da terna_dc.scarica e scrive in `uscita` i JSON statici della pagina
      (italia.json con le regioni, RR.json con le province della regione RR, burden_sharing.json). Il worker lo chiama
      in una cartella nuova e la pubblica con _pubblica (fase 4) solo se il controllo passa.

  python -m elettricita.costruisci <raw> <uscita>
"""
from __future__ import annotations
from pathlib import Path


def costruisci(raw: Path, uscita: Path) -> dict:
    raise NotImplementedError("in lavorazione")
