"""Riga di comando della fase 8.

  python -m indicatori_ssn aggiorna --out <cartella> [--cache cache] [--rinnova] [--pausa 2] [--parziale]
      scarica (o legge dalla cache) CE, ReportER e ISTAT e scrive <cartella>/indice.json e <cartella>/RR.json
  python -m indicatori_ssn verifica --out <cartella>
      stampa i valori 2024 di controllo (AUSL della Romagna, Emilia-Romagna, Italia)

Se una fonte non risponde e manca la sua copia in cache, i file del sito non vengono toccati
(con --parziale si scrivono lo stesso, con gli anni mancanti vuoti).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import bdap, calcolo, costanti as K, istat, reporter
from .rete import FonteNonDisponibile, Rete

log = logging.getLogger("indicatori_ssn")


def scrivi_json(f: Path, dati) -> int:
    testo = json.dumps(dati, ensure_ascii=False, separators=(",", ":"))
    tmp = f.with_suffix(".tmp")
    tmp.write_text(testo, encoding="utf-8")
    tmp.replace(f)
    return len(testo.encode())


def aggiorna(out: Path, cache: Path, *, rinnova=False, pausa=2.0, parziale=False, anni=None) -> dict:
    anni = anni or K.ANNI
    rete = Rete(cache / "http", pausa=pausa, rinnova=rinnova)
    mancanti = []
    try:
        righe = {}
        for a in anni:
            try:
                righe[a] = bdap.leggi(bdap.scarica_anno(rete, a, cache / "bdap"))
            except FonteNonDisponibile as e:
                log.error("CE %d non disponibile: %s", a, e)
                mancanti.append(f"CE {a}")
        rep = reporter.scarica(rete, anni)
        for m, per_anno in rep["dati"].items():
            mancanti += [f"ReportER {m} {a}" for a in anni if a not in per_anno]
        pop = istat.scarica(rete, anni, cache / "istat")
        mancanti += [f"ISTAT {a}" for a in anni if a not in (pop["dati"].get("IT") or {})]
    finally:
        rete.chiudi()
    if mancanti and not parziale:
        raise FonteNonDisponibile("dati mancanti, file del sito non aggiornati: " + ", ".join(mancanti))
    if not righe:
        raise FonteNonDisponibile("nessun anno del CE disponibile")
    r = calcolo.costruisci(calcolo.raccogli_ce(righe), rep, pop, anni)
    r["indice"]["mancanti"] = mancanti
    out.mkdir(parents=True, exist_ok=True)
    dimensioni = {"indice.json": scrivi_json(out / "indice.json", r["indice"])}
    for cod, reg in r["regioni"].items():
        dimensioni[f"{cod}.json"] = scrivi_json(out / f"{cod}.json", reg)
    log.info("scritti %d file, %d byte in tutto", len(dimensioni), sum(dimensioni.values()))
    return {"dimensioni": dimensioni, "mancanti": mancanti}


def _formatta(x, dec=0, suff=""):
    if x is None:
        return "n.d."
    s = f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + suff


def controllo(out: Path, anno: int = 2024) -> list[tuple[str, dict]]:
    indice = json.loads((out / "indice.json").read_text(encoding="utf-8"))
    i = indice["anni"].index(anno)
    er = json.loads((out / "08.json").read_text(encoding="utf-8"))
    romagna = next(e for a in er["ambiti"] for e in a["enti"] if e["cod"] == "114")
    righe = []
    for nome, u in (("AUSL della Romagna", romagna), ("Emilia-Romagna (consolidato)", indice["consolidati"]["080"]),
                    ("Italia", indice["italia"])):
        righe.append((nome, calcolo.indicatori(u, i)))
    return righe


def stampa_controllo(out: Path, anno: int = 2024):
    for nome, d in controllo(out, anno):
        print(f"{nome}: spesa {_formatta(d['spesa'])} €; leva {_formatta(d['leva'], 1)}x; "
              f"incidenza {_formatta(d['incidenza'] and d['incidenza'] * 100, 2)} %; "
              f"peso {_formatta(d['peso'] and d['peso'] * 100, 2)} %; "
              f"{_formatta(d['per_giornata'], 2)} €/giornata; {_formatta(d['per_posto'])} €/posto letto; "
              f"{_formatta(d['per_cittadino'], 2)} €/cittadino")


def main(argv=None):
    p = argparse.ArgumentParser(prog="indicatori_ssn", description="Indicatori della spesa energetica degli enti del SSN")
    sub = p.add_subparsers(dest="comando", required=True)
    a = sub.add_parser("aggiorna", help="scarica i dati e scrive i JSON del sito")
    a.add_argument("--out", required=True, type=Path)
    a.add_argument("--cache", type=Path, default=Path("cache"))
    a.add_argument("--rinnova", action="store_true", help="riscarica anche ciò che è già in cache")
    a.add_argument("--pausa", type=float, default=2.0, help="secondi tra una richiesta e l'altra")
    a.add_argument("--parziale", action="store_true", help="scrive i file anche se manca qualche fonte")
    v = sub.add_parser("verifica", help="stampa i valori di controllo")
    v.add_argument("--out", required=True, type=Path)
    v.add_argument("--anno", type=int, default=2024)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.comando == "aggiorna":
        try:
            esito = aggiorna(args.out, args.cache, rinnova=args.rinnova, pausa=args.pausa, parziale=args.parziale)
        except FonteNonDisponibile as e:
            log.error("%s", e)
            return 2
        for f, n in esito["dimensioni"].items():
            print(f"{f}\t{n / 1024:.1f} kB")
        stampa_controllo(args.out)
        return 0
    stampa_controllo(args.out, args.anno)
    return 0


if __name__ == "__main__":
    sys.exit(main())
