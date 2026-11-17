"""python -m territorio <comando> …

  patrimonio EDIFICI.csv --comuni comuni.parquet [--anncsu anncsu_civici.parquet] [--uscita risultato] [--dettagli]
      geolocalizza un patrimonio edilizio (coordinate → catasto → indirizzo)
  anncsu-scarica --dest CARTELLA [--comuni comuni.parquet --regioni 08] [--zip file.zip]
      scarica l'indirizzario ANNCSU (mensile, CC BY 4.0) e lo salva come anncsu_civici.parquet
  cabine-raccordo --dati-cp CARTELLA --osm italy.osm.pbf --aree-gse CARTELLA --istat CARTELLA --dest CARTELLA
                  [--mappa ../fase5-sito/sito/dati/mappa] [--scarica-gse] [--comuni-ed comuni_gestiti.json]
      raccordo cabine primarie e-distribuzione ↔ aree GSE (COD_AC) ↔ sottostazioni OSM, criticità dei comuni,
      comuni non concessionari (le aree GSE si scaricano solo nella cartella di lavoro, mai nel repository)

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
    p.add_argument("comando", choices=["patrimonio", "anncsu-scarica", "cabine-raccordo"])
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
    p.add_argument("--dati-cp", help="cabine-raccordo: cartella di cabine_edistribuzione.py (grezzi/PPP.json)")
    p.add_argument("--osm", help="cabine-raccordo: italy.osm.pbf o JSON/GeoJSON delle sottostazioni già estratte")
    p.add_argument("--aree-gse", help="cabine-raccordo: cartella di lavoro dei poligoni GSE (fuori dal repository)")
    p.add_argument("--scarica-gse", action="store_true", help="cabine-raccordo: scarica prima i poligoni GSE")
    p.add_argument("--istat", help="cabine-raccordo: cartella con i CSV ISTAT (elenco, soppressi, variazioni)")
    p.add_argument("--mappa", default=str(Path(__file__).resolve().parents[2] / "fase5-sito" / "sito" / "dati" / "mappa"),
                   help="cabine-raccordo: file di mappa dei comuni del sito")
    p.add_argument("--linee-luoghi", help="cabine-raccordo: JSON {linee, luoghi} già estratti (altrimenti, con "
                                          "--verifica e il PBF, si estraggono)")
    p.add_argument("--documenti", nargs="*", default=[], help="cabine-raccordo: testi (pdftotext -layout) delle "
                                                             "appendici dei Piani di Sviluppo e-distribuzione")
    p.add_argument("--eccezioni", default=str(Path(__file__).resolve().parents[1] / "cabine_eccezioni.csv"),
                   help="cabine-raccordo: CSV delle verifiche a mano (predefinito fase7-territorio/cabine_eccezioni.csv)")
    p.add_argument("--verifica", action="store_true", help="cabine-raccordo: secondo passaggio di verifica")
    p.add_argument("--comuni-ed", help="cabine-raccordo: JSON degli attributi di View_ComuniGestitiED2021Is "
                                       "(se manca si scarica)")
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

    if a.comando == "cabine-raccordo":
        from . import cabine
        for k in ("dati_cp", "osm", "aree_gse", "istat", "dest"):
            if not getattr(a, k):
                p.error(f"cabine-raccordo richiede --{k.replace('_', '-')}")
        if a.scarica_gse:
            cabine.scarica_aree_gse(Path(a.aree_gse))
        cg = json.loads(Path(a.comuni_ed).read_text(encoding="utf-8")) if a.comuni_ed else cabine.scarica_comuni_gestiti()
        linee = luoghi = docs = None
        if a.verifica:
            if a.linee_luoghi:
                ll = json.loads(Path(a.linee_luoghi).read_text(encoding="utf-8"))
                linee, luoghi = ll["linee"], ll["luoghi"]
            elif a.osm.endswith(".pbf"):
                linee, luoghi = cabine.estrai_linee_luoghi(Path(a.osm))
            else:
                p.error("--verifica richiede --linee-luoghi oppure il PBF in --osm")
            docs = [d for f in a.documenti for d in cabine.schede_piano_sviluppo(
                Path(f).read_text(encoding="utf-8"), Path(f).stem)]
        r = cabine.costruisci(Path(a.dati_cp), Path(a.osm), Path(a.aree_gse), Path(a.mappa), Path(a.istat),
                              Path(a.dest), comuni_gestiti=cg, linee=linee, luoghi=luoghi, documenti=docs,
                              eccezioni=cabine.leggi_eccezioni(Path(a.eccezioni)))
        for x in r["avvisi_eccezioni"]:
            print("Avviso:", x)
        if r["verifica"]:
            print(f"Secondo passaggio: prima {r['verifica']['prima']}, dopo {r['verifica']['dopo']}")
        print(f"Cabine e-distribuzione: {r['cabine']}; esiti: {dict(r['esiti'])}; aree GSE {r['versione_ac']}")
        print(f"Creati in {a.dest}: raccordo_cp.csv, cabine_primarie.geojson, comuni_criticita.json, "
              "comuni_non_concessionari.json, osm_sottostazioni.geojson")
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
