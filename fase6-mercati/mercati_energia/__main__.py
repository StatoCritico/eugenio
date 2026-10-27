"""python -m mercati_energia [-c config.toml] <comando>

  notturno                         aggiornamento di GME, TTF e indici mensili (quello del timer)
  stato                            ultimo aggiornamento, giorni in archivio, dimensioni
  indici [--indice PUN_MENSILE]    indici mensili calcolati
  importa FILE.csv                 importa indici mensili (es. PSV day-ahead ICIS, CMEM ARERA, PFOR_ARERA)
  importa-forward FILE.csv         quotazioni forward trimestrali TTF (data;trimestre;prezzo) per il PFOR
  pfor [--dal 2022Q4 --al 2027Q1]  indice PFOR,t ricostruito, trimestre per trimestre
  istat cerca TESTO | istat struttura DATAFLOW | istat scarica NOME [--forza]
  eurostat scarica NOME [--forza]
  convenzioni elenco | convenzioni prezzi ID LOTTO --dal AAAA-MM --al AAAA-MM
  convenzioni costo ID LOTTO --consumi consumi.csv [--pod N] [--potenza KW]
  quote-gme                        quote residue dell'API del GME
  sorveglianza [stato]             controlla subito le fonti delle convenzioni (quello della notte) o ne mostra lo stato
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

import pandas as pd

from . import archivio, convenzioni, eurostat, gme, importa, indici, istat, notturno, pfor
from .config import carica


def _mesi(dal: str, al: str) -> list[str]:
    return [str(p) for p in pd.period_range(dal, al, freq="M")]


def main(argv=None):
    p = argparse.ArgumentParser(prog="mercati_energia", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-c", "--config", default="config.toml")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("comando")
    p.add_argument("argomenti", nargs="*")
    p.add_argument("--indice")
    p.add_argument("--forza", action="store_true")
    p.add_argument("--dal")
    p.add_argument("--al")
    p.add_argument("--consumi")
    p.add_argument("--pod", type=int, default=1)
    p.add_argument("--potenza", type=float)
    p.add_argument("--csv", help="salva il risultato in questo file CSV")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cfg = carica(a.config)
    arg = a.argomenti
    out = None

    if a.comando == "notturno":
        e = notturno.esegui(cfg)
        print(json.dumps(e, indent=1, ensure_ascii=False, default=str))
        return 1 if e["errori"] else 0
    if a.comando == "stato":
        f = cfg.cartella / "ultima_esecuzione.json"
        print(f.read_text(encoding="utf-8") if f.exists() else "Nessuna esecuzione registrata")
        st = archivio.stato_storico(cfg.cartella)
        for ds in ("mgp_prezzi", "mgp_volumi", "mgp_gas", "mgp_gas_continua", "igi", "ttf_eex", "ttf_forward",
                   "indici_importati"):
            s = st.get(ds, {})
            print(f"{ds:18s} dal {archivio.prima_data(cfg.cartella, ds, 'data')} al "
                  f"{archivio.ultima_data(cfg.cartella, ds, 'data')}"
                  + ("" if ds not in st else ("  storico completo" if s.get("completo") else
                                              f"  storico in recupero (raggiunto {s.get('raggiunto')})")))
        tot = sum(archivio.dimensioni(cfg.cartella).values())
        print(f"Spazio occupato: {tot / 1e6:.1f} MB")
    elif a.comando == "indici":
        out = indici.leggi(cfg.cartella)
        if a.indice:
            out = out[out.indice == a.indice.upper()]
    elif a.comando == "importa":
        print(f"Importate {importa.importa_csv(cfg.cartella, arg[0])} righe")
        indici.calcola(cfg.cartella, tuple(cfg.festivi_extra))
    elif a.comando == "importa-forward":
        print(f"Importate {pfor.importa_forward(cfg.cartella, arg[0])} quotazioni")
        indici.calcola(cfg.cartella, tuple(cfg.festivi_extra))
    elif a.comando == "pfor":
        out = pfor.calcola(cfg.cartella, a.dal or "2022Q4", a.al)
    elif a.comando == "istat":
        if arg[0] == "cerca":
            out = istat.cerca(cfg.cartella, " ".join(arg[1:]))
        elif arg[0] == "struttura":
            print(istat.struttura(arg[1]))
        elif arg[0] == "scarica":
            nomi = arg[1:] or list(cfg.istat)
            out = pd.concat([istat.serie(cfg.cartella, n, cfg.istat[n], a.dal, a.forza) for n in nomi])
    elif a.comando == "eurostat":
        nomi = arg[1:] or list(cfg.eurostat)
        out = pd.concat([eurostat.serie(cfg.cartella, n, cfg.eurostat[n], a.forza) for n in nomi])
    elif a.comando == "convenzioni":
        tutte = {c.id: c for c in convenzioni.carica_tutte(cfg.convenzioni)} if cfg.convenzioni else {}
        if arg[0] == "elenco":
            for c in tutte.values():
                manca = convenzioni.da_compilare(c)
                print(f"{c.id:28s} {c.ente:32s} {c.commodity:10s} {c.dal}→{c.al} lotti: "
                      f"{', '.join(l.id for l in c.lotti)}" + (f"  [da compilare: {len(manca)} valori]" if manca else ""))
        elif arg[0] == "prezzi":
            out = convenzioni.prezzi(tutte[arg[1]], arg[2], _mesi(a.dal, a.al), indici.leggi(cfg.cartella))
        elif arg[0] == "costo":
            consumi = pd.read_csv(a.consumi, sep=None, engine="python", dtype={"mese": str, "fascia": str})
            out = convenzioni.costo(tutte[arg[1]], arg[2], consumi, indici.leggi(cfg.cartella), a.pod, a.potenza)
    elif a.comando == "sorveglianza":
        from . import sorveglianza
        if arg and arg[0] == "stato":
            f = cfg.cartella / "sorveglianza" / "stato.json"
            st = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"pagine": {}, "documenti": {}}
            out = pd.DataFrame([{"url": u, "controllata": s.get("controllata"), "cambiata": s.get("cambiata"),
                                 "errori": s.get("errori", 0)} for u, s in st["pagine"].items()])
            print(f"Documenti scaricati: {len(st['documenti'])}")
        else:
            e = sorveglianza.esegui(cfg.cartella, cfg.convenzioni)
            print(sorveglianza.riepilogo(e) or f"Nessuna novità ({e['controllate']} pagine controllate)")
    elif a.comando == "quote-gme":
        print(json.dumps(gme.ClientGME(cfg.gme.utente, cfg.gme.password()).quote(), indent=1))
    else:
        p.error(f"comando sconosciuto: {a.comando}")
    if out is not None:
        if a.csv:
            out.to_csv(a.csv, sep=";", decimal=",", index=False)
            print(f"Salvato {a.csv}")
        else:
            with pd.option_context("display.max_rows", 200, "display.width", 200):
                print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
