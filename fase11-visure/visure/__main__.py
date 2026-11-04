"""EuGEnio Visure – riga di comando.

  python -m visure leggi CARTELLA_O_PDF… [--patrimonio patrimonio.csv] [--uscita Visure_AAAA-MM-GG] [--ordina]
                                         [--regole mie_regole.toml] [--includi-intestatari]
  python -m visure controlla PDF…        controllo di anonimato prima di condividere una visura
  python -m visure web [--porta 8770]    pagina locale nel browser (solo 127.0.0.1)
  python -m visure esempi --uscita DIR   visure sintetiche di prova (serve reportlab)
  python -m visure modello FILE.dxf|ifc [--uscita modello.geojson] [--crs EPSG:7791 | --posa X,Y=LON,LAT …]
                                         [--rotazione GRADI] [--unita M] [--grande]
                                         DXF/IFC → GeoJSON per la pagina Modelli 3D (file pesanti, dal 04/11/2026)
  python -m visure prova [--modelli]     controllo di avvio (con --modelli anche la conversione dei modelli)
  python -m visure versione

Tutto in locale: nessuna credenziale, nessun accesso a SISTER o ad altri servizi dell'Agenzia delle Entrate, nessuna
connessione di rete.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import VERSIONE


def uscita_robusta() -> None:
    """UTF-8 con «replace» anche con l'uscita rediretta su Windows (cp1252/850): nessun UnicodeEncodeError per «→», «–»,
    «·» (05/11/2026; lo stesso fa l'avviatore prima di freeze_support)."""
    for flusso in (sys.stdout, sys.stderr):
        try:
            flusso.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def pdf_da(percorsi: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, percorsi):
        if p.is_dir():
            out += sorted(x for x in p.rglob("*") if x.suffix.lower() == ".pdf")
        elif p.suffix.lower() == ".pdf" and p.exists():
            out.append(p)
        else:
            print(f"salto {p}: non è un PDF o una cartella", file=sys.stderr)
    return out


def cmd_leggi(a) -> int:
    from .lettore import leggi_pdf
    from .regole import carica
    from .uscite import leggi_csv, scrivi
    R = carica(a.regole)
    files = pdf_da(a.percorsi)
    if not files:
        print("nessun PDF trovato", file=sys.stderr)
        return 2
    if a.includi_intestatari:
        print("ATTENZIONE: con --includi-intestatari il file intestatari_DATI_PERSONALI.csv contiene dati personali. "
              "Non condividerlo e non caricarlo su EuGEnio né altrove.", file=sys.stderr)
    visure = []
    for f in files:
        v = leggi_pdf(f, R, includi_intestatari=a.includi_intestatari)
        print(f"{f.name}: {v.esito}, {len(v.unita)} unità" + (f" – {v.nota}" if v.nota else ""))
        visure.append(v)
    patrimonio = colonne = None
    if a.patrimonio:
        patrimonio = leggi_csv(Path(a.patrimonio))
        colonne = list(patrimonio[0]) if patrimonio else []
    uscita = Path(a.uscita or f"Visure_{date.today():%Y-%m-%d}")
    ris = scrivi(uscita, visure, patrimonio, colonne, a.includi_intestatari,
                 {f.name: f for f in files}, a.ordina)
    print(f"{len(ris['unita'])} unità, {len(ris['edifici'])} edifici → {uscita}")
    return 0


def cmd_controlla(a) -> int:
    from .privacy import controlla_pdf, descrivi
    peggiore = 0
    for f in pdf_da(a.percorsi):
        e = controlla_pdf(f)
        print(descrivi(f.name, e))
        peggiore = max(peggiore, 1 if e["totale"] else 0)
    return peggiore


def cmd_web(a) -> int:
    from .web import avvia
    avvia(a.host, a.porta, apri=not a.non_aprire, regole=a.regole)
    return 0


def cmd_esempi(a) -> int:
    from .sintetici import PATRIMONIO_ESEMPIO, genera
    d = Path(a.uscita)
    for p in genera(d):
        print(p)
    (d / "patrimonio_esempio_visure.csv").write_text(PATRIMONIO_ESEMPIO, encoding="utf-8")
    print(d / "patrimonio_esempio_visure.csv")
    return 0


def cmd_prova(a) -> int:
    from .autotest import prova
    ok, msg = prova()
    print(("OK: " if ok else "ERRORE: ") + msg)
    if getattr(a, "modelli", False):
        from .modelli import prova as prova_modelli
        ok2, msg2 = prova_modelli()
        print(("OK: " if ok2 else "ERRORE: ") + msg2)
        ok = ok and ok2
    return 0 if ok else 1


def cmd_modello(a) -> int:
    import json
    from .modelli import converti, disponibile, errore_modello
    ok, msg = disponibile()
    if not ok:
        print(f"Conversione dei modelli non disponibile in questa installazione: {msg}", file=sys.stderr)
        return 2
    f = Path(a.file)
    uscita = Path(a.uscita or f.with_suffix(".geojson").name)
    try:
        r = converti(f, posa=a.posa, crs=a.crs, rotazione=a.rotazione, unita=a.unita, grande=a.grande, edificio=a.edificio)
    except Exception as e:  # noqa: BLE001
        m = errore_modello(e)
        if m is None:
            raise
        print(f"Modello non convertito: {m}", file=sys.stderr)
        return 1
    uscita.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    print(f"{len(r['features'])} corpi → {uscita}")
    for av in r.get("avvisi", []):
        print(f"  avviso: {av}")
    print("Apri il file nella pagina «Importa DXF/IFC» o «Modelli 3D» di EuGEnio: viene letto solo dal browser.")
    return 0


def principale(argv: list[str] | None = None) -> int:
    uscita_robusta()
    ap = argparse.ArgumentParser(prog="visure", description="EuGEnio Visure: lettore locale delle visure catastali")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("leggi", help="legge PDF e cartelle di visure")
    p.add_argument("percorsi", nargs="+")
    p.add_argument("--patrimonio", help="CSV di Patrimonio (anche il risultato scaricato dalla pagina) da arricchire")
    p.add_argument("--uscita", help="cartella dei risultati (predefinita Visure_AAAA-MM-GG)")
    p.add_argument("--regole", help="file TOML con regole proprie (sostituiscono le voci corrispondenti)")
    p.add_argument("--ordina", action="store_true", help="copia i PDF ordinati per comune, foglio e particella")
    p.add_argument("--includi-intestatari", action="store_true",
                   help="salva a parte intestatari e codici fiscali (DATI PERSONALI: solo per uso proprio)")
    p.set_defaults(f=cmd_leggi)
    p = sub.add_parser("controlla", help="controllo di anonimato")
    p.add_argument("percorsi", nargs="+")
    p.set_defaults(f=cmd_controlla)
    p = sub.add_parser("web", help="pagina locale nel browser")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--porta", type=int, default=8770)
    p.add_argument("--non-aprire", action="store_true", help="non aprire il browser")
    p.add_argument("--regole")
    p.set_defaults(f=cmd_web)
    p = sub.add_parser("esempi", help="visure sintetiche di prova")
    p.add_argument("--uscita", default="visure_sintetiche")
    p.set_defaults(f=cmd_esempi)
    p = sub.add_parser("modello", help="modello DXF o IFC → GeoJSON per la pagina Modelli 3D (file pesanti)")
    p.add_argument("file")
    p.add_argument("--uscita", help="file GeoJSON (predefinito: <nome>.geojson nella cartella attuale)")
    p.add_argument("--crs", help="sistema delle coordinate del disegno se è già georeferenziato (es. EPSG:7791)")
    p.add_argument("--posa", nargs="+", metavar="X,Y=LON,LAT",
                   help="due punti noti (coordinate del disegno, nelle sue unità = lon,lat) oppure uno solo più --rotazione")
    p.add_argument("--rotazione", type=float, default=0.0, help="azimut dell'asse +Y del disegno (gradi da nord, senso orario)")
    p.add_argument("--unita", type=float, help="metri per unità del disegno (predefinito: dal file, altrimenti 1)")
    p.add_argument("--edificio", default="MODELLO")
    p.add_argument("--grande", action="store_true", help="file molto grandi: fino a 500 MB, 8 GB di memoria, 30 minuti")
    p.set_defaults(f=cmd_modello)
    p = sub.add_parser("prova", help="controllo di avvio")
    p.add_argument("--modelli", action="store_true", help="controlla anche la conversione dei modelli DXF/IFC")
    p.set_defaults(f=cmd_prova)
    sub.add_parser("versione").set_defaults(f=lambda a: print(f"EuGEnio Visure {VERSIONE}") or 0)
    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(principale())
