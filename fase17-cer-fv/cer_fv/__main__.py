"""python -m cer_fv scarica-agrea                     (in /srv/energia/dati/agrea/<anno>/, le ultime 3 campagne chiuse)
python -m cer_fv terreni --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /srv/energia/dati/cer_fv"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import agrea, terreni


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cer_fv", description="CER – Sviluppo impianti FV (fase 17)")
    s = p.add_subparsers(dest="comando", required=True)
    t = s.add_parser("terreni", help="terreni pubblici candidati con la probabilità di coltura DOP o certificata")
    t.add_argument("--immobili", type=Path, required=True, help="cartella con immobili_pa_<anno>.sqlite e il parquet delle particelle")
    t.add_argument("--agrea", type=Path, default=None, help="cartella con una sottocartella per campagna (<anno>/) dei piani colturali grafici")
    t.add_argument("--dest", type=Path, required=True)
    t.add_argument("--regole", type=Path, default=None)
    t.add_argument("--comuni", type=Path, default=None, help="comuni.parquet della fase 3 (istat, belfiore); predefinito DATI/clima_lavoro/comuni.parquet, se manca l'elenco ISTAT")
    g = s.add_parser("scarica-agrea", help="piani colturali grafici di AGREA (UtilizziGrafici) nella cartella dei dati")
    g.add_argument("--dest", type=Path, default=agrea.CARTELLA, help=f"predefinita {agrea.CARTELLA}")
    g.add_argument("--campagne", type=int, default=3, help="quante campagne chiuse (predefinito 3)")
    g.add_argument("--anni", type=int, nargs="*", default=None, help="anni precisi al posto delle ultime campagne chiuse")
    g.add_argument("--togli-vecchie", action="store_true", help="cancella da --dest le campagne non più usate")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if a.comando == "terreni":
        print(json.dumps(terreni.costruisci(a.immobili, a.dest, a.agrea, a.regole, a.comuni), ensure_ascii=False, indent=1))
    elif a.comando == "scarica-agrea":
        print(json.dumps(agrea.scarica(a.dest, a.campagne, a.anni, a.togli_vecchie), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
