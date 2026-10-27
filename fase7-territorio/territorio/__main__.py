"""python -m territorio <comando> …

  patrimonio EDIFICI.csv --comuni comuni.parquet [--anncsu anncsu_civici.parquet] [--uscita risultato] [--dettagli]
      geolocalizza un patrimonio edilizio (coordinate → catasto → indirizzo)
  anncsu-scarica --dest CARTELLA [--comuni comuni.parquet --regioni 08] [--zip file.zip]
      scarica l'indirizzario ANNCSU (mensile, CC BY 4.0) e lo salva come anncsu_civici.parquet

La chiave Zornade si legge da ZORNADE_API_KEY (variabile d'ambiente) o da --chiave-file.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from . import anncsu, patrimonio
from .zornade import Zornade


def _comuni(percorso: str) -> pd.DataFrame:
    return pd.read_parquet(percorso) if percorso.endswith(".parquet") else pd.read_json(percorso, dtype={"istat": str})


def main(argv=None):
    p = argparse.ArgumentParser(prog="territorio", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["patrimonio", "anncsu-scarica"])
    p.add_argument("file", nargs="?", help="patrimonio: CSV degli edifici")
    p.add_argument("--comuni", help="comuni.parquet o comuni.json della fase 3")
    p.add_argument("--anncsu", help="patrimonio: anncsu_civici.parquet (prima fonte per gli indirizzi)")
    p.add_argument("--uscita", default=None, help="prefisso dei file di uscita (predefinito: accanto all'ingresso)")
    p.add_argument("--chiave-file")
    p.add_argument("--cache", default=".cache_zornade.sqlite")
    p.add_argument("--dettagli", action="store_true", help="aggiunge i blocchi edifici/terreno della particella")
    p.add_argument("--dest", help="anncsu-scarica: cartella di destinazione (fuori dal repository)")
    p.add_argument("--regioni", help='anncsu-scarica: solo queste regioni ISTAT (es. "08"), serve --comuni')
    p.add_argument("--zip", help="anncsu-scarica: usa uno ZIP già scaricato invece di scaricarlo")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if a.comando == "anncsu-scarica":
        if not a.dest:
            p.error("anncsu-scarica richiede --dest")
        istat = None
        if a.regioni:
            if not a.comuni:
                p.error("--regioni richiede --comuni")
            reg = [x.strip().zfill(2) for x in a.regioni.split(",")]
            cm = _comuni(a.comuni)
            istat = set(cm[cm.regione_cod.isin(reg)].istat)
        f = anncsu.scarica(Path(a.dest), zip_locale=Path(a.zip) if a.zip else None, istat=istat)
        print(f"Creato {f}")
        return 0

    if not a.file or not a.comuni:
        p.error("patrimonio richiede il file degli edifici e --comuni")
    chiave = os.environ.get("ZORNADE_API_KEY") or (Path(a.chiave_file).read_text().strip() if a.chiave_file else "")
    df = patrimonio.leggi(a.file)
    idx = anncsu.Indirizzario(a.anncsu) if a.anncsu else None
    ris = patrimonio.geolocalizza(df, Zornade(chiave, Path(a.cache)), _comuni(a.comuni), a.dettagli, idx)
    base = Path(a.uscita) if a.uscita else Path(a.file).with_suffix("")
    ris.to_csv(f"{base}_geolocalizzato.csv", sep=";", index=False)
    Path(f"{base}_punti.geojson").write_text(json.dumps(patrimonio.geojson(ris), ensure_ascii=False), encoding="utf-8")
    print(patrimonio.riepilogo(ris))
    print(f"Creati {base}_geolocalizzato.csv e {base}_punti.geojson")
    return 0


if __name__ == "__main__":
    sys.exit(main())
