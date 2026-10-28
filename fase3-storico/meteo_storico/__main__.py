"""python -m meteo_storico <comando> [opzioni]

  comuni     costruisce l'elenco NAZIONALE dei comuni e i punti meteo (una volta; ~730 MB di sezioni ISTAT)
  scarica    scarica ERA5 e/o ICON storico dall'API (riprende da dove si era interrotto)
  scarica-s3 come `scarica`, ma leggendo direttamente i file di Open-Meteo su AWS: tutta Italia in poche ore
  correggi   stima e applica la correzione ERA5 → ICON, con validazione
  esporta    prepara la cartella da copiare sul server
  stato      quanto è stato scaricato e consumo dell'API
  tutto      comuni + scarica + correggi + esporta
  legge10    dati climatici aggiornati per la Legge 10 (--comuni, --anni, --ufficiali file.csv)
  territorio-verifica   nuove versioni dell'elenco ISTAT o dei confini Gramscii?
  territorio-blocca     adotta l'ultima versione Gramscii (poi rieseguire `comuni`)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path

import pandas as pd

from . import aggrega, comuni, correzione, gramscii, legge10, territorio
from .limiti import Limitatore
from .scarica import FONTI, Scaricatore


def _regioni(v: str | None):
    if not v or v == "tutte":
        return None
    return [x.strip().zfill(2) for x in v.split(",")]


def main(argv=None):
    p = argparse.ArgumentParser(prog="meteo_storico", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["comuni", "scarica", "scarica-s3", "correggi", "esporta", "stato", "tutto", "legge10",
                                          "territorio-verifica", "territorio-blocca"])
    p.add_argument("--archivio", default="archivio", help="cartella dell'archivio (anche su disco esterno)")
    p.add_argument("--regioni", default="08", help='codici ISTAT separati da virgola, o "tutte" (predefinito 08 = ER)')
    p.add_argument("--comuni", help="solo questi codici ISTAT (es. 037006,039014) – utile per provare")
    p.add_argument("--fonte", default="entrambe", choices=["era5", "icon", "entrambe", "icon2i", "ifs", "previsioni"],
                   help="entrambe = era5+icon (storico); previsioni = icon2i+ifs (per calibrare le previsioni)")
    p.add_argument("--dal", default="2015-01-01", help="inizio serie ERA5 (ICON parte comunque dal 14/11/2022)")
    p.add_argument("--al", help="fine (predefinito: ultimo giorno disponibile)")
    p.add_argument("--locale", help="URL di un'istanza Open-Meteo propria, es. http://127.0.0.1:8080 (niente limiti)")
    p.add_argument("--punti-per-richiesta", type=int, default=5)
    p.add_argument("--per-gruppo", type=int, default=400, help="scarica-s3: comuni letti insieme (memoria ~ gruppo)")
    p.add_argument("--senza-sezioni", action="store_true", help="non scaricare le sezioni di censimento")
    p.add_argument("--dest", default="pacchetto_server", help="cartella di destinazione di `esporta`")
    p.add_argument("--anni", type=int, default=10, help="legge10: stagioni da usare")
    p.add_argument("--ufficiali", help="legge10: CSV istat;gg;zona;theta_progetto con i valori normativi")
    p.add_argument("--uscita", default="legge10", help="legge10: cartella dei risultati")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    arch = Path(a.archivio)
    reg = _regioni(a.regioni)
    # zfill: PowerShell senza virgolette passa 037006,039014 come numeri e toglie gli zeri iniziali
    sel = [x.strip().zfill(6) for x in a.comuni.split(",") if x.strip()] if a.comuni else None
    cmd = a.comando

    if cmd in ("comuni", "tutto"):
        # l'elenco dei comuni e i loro punti sono sempre nazionali (7.896 comuni); --regioni vale per il meteo
        df = comuni.costruisci(arch, None, usa_sezioni=not a.senza_sezioni)
        comuni.salva(df, arch)
    if cmd in ("scarica", "tutto"):
        cm = comuni.carica(arch, reg, sel)
        fonti = {"entrambe": ["era5", "icon"], "previsioni": ["icon2i", "ifs"]}.get(a.fonte, [a.fonte])
        for f in fonti:
            s = Scaricatore(arch, f, a.locale, a.punti_per_richiesta)
            dal = dt.date.fromisoformat(a.dal) if f == "era5" else FONTI[f]["inizio"]
            s.scarica(cm, dal, dt.date.fromisoformat(a.al) if a.al else None)
            s.unisci(cm)
    if cmd == "scarica-s3":
        from . import s3
        cm = comuni.carica(arch, reg, sel)
        fonti = {"entrambe": ["era5", "icon"]}.get(a.fonte, [a.fonte])
        for f in fonti:
            if f not in ("era5", "icon"):
                raise SystemExit("scarica-s3: --fonte era5, icon o entrambe")
            dal = dt.date.fromisoformat(a.dal) if f == "era5" else s3.INIZIO_ICON
            s3.scarica(arch, cm, f, dal, dt.date.fromisoformat(a.al) if a.al else None, a.per_gruppo)
            Scaricatore(arch, f, "http://locale-non-usato", a.punti_per_richiesta).unisci(cm)
    if cmd in ("correggi", "tutto"):
        cm = comuni.carica(arch, reg, sel)
        for sorgente, mesi in (("era5", 12), ("icon2i", 6), ("ifs", 6)):
            if not (arch / "orario" / sorgente).exists():
                continue
            ris = []
            for i, istat in enumerate(cm.istat, 1):
                r = correzione.elabora_comune(arch, istat, sorgente, mesi)
                if r:
                    ris.append(r)
                if i % 25 == 0:
                    logging.info("correzione %s: %d/%d comuni", sorgente, i, len(cm))
            sint = correzione.riassumi(ris, arch, sorgente)
            print(json.dumps(sint, indent=1, ensure_ascii=False))
    if cmd in ("esporta", "tutto"):
        aggrega.esporta(arch, comuni.carica(arch, reg, sel), Path(a.dest))
    if cmd == "legge10":
        cm = comuni.carica(arch, reg, sel)
        dest = Path(a.uscita)
        dest.mkdir(parents=True, exist_ok=True)
        for r in cm.itertuples():
            p = arch / "orario" / "era5_corretto" / f"{r.istat}.parquet"
            if not p.exists():
                continue
            orario = pd.read_parquet(p)
            uff = legge10.ufficiali_da_csv(a.ufficiali, r.istat) if a.ufficiali else None
            ris = legge10.calcola(aggrega.giornaliero(orario), a.anni, orario, uff)
            ris.update({"istat": r.istat, "comune": r.nome})
            (dest / f"{r.istat}.json").write_text(json.dumps(ris, ensure_ascii=False, indent=1), encoding="utf-8")
            pd.DataFrame(ris["mensili"]).to_csv(dest / f"{r.istat}_mensili.csv", sep=";", decimal=",", index=False)
            gg = ris["gradi_giorno"]
            print(f"{r.istat} {r.nome:28s} zona {gg['zona_risultante']}  GG {gg['gg_periodo_zona']:.0f} "
                  f"(anno intero {gg['gg_anno_intero']:.0f}, tendenza {gg['tendenza_gg_per_decennio']} GG/10 anni)  "
                  f"θe progetto {ris['temperatura_progetto']['invernale']} °C")
    if cmd == "territorio-verifica":
        print(json.dumps(territorio.verifica(pd.read_parquet(arch / "comuni.parquet")), indent=1, ensure_ascii=False))
    if cmd == "territorio-blocca":
        u = gramscii.ultima_revisione()
        gramscii.blocca(u["revisione"])
        print(f"Revisione Gramscii bloccata: {u['revisione']} ({u['modificato']}). Ora rieseguire `comuni`.")
    if cmd == "stato":
        cm = comuni.carica(arch, reg, sel)
        for f in ("era5", "icon", "era5_corretto", "icon2i", "ifs"):
            n = sum((arch / "orario" / f / f"{i}.parquet").exists() for i in cm.istat)
            print(f"{f:14s} {n}/{len(cm)} comuni")
        print("API:", Limitatore(arch / "stato_api.json").riepilogo())


if __name__ == "__main__":
    sys.exit(main())
