#!/usr/bin/env python3
"""Testata, piè e parte comune del <head> delle pagine del sito da un unico modello.

Le parti comuni stanno in parti/ (accanto a questo file):
  testa.html    script del tema e del vestito, foglio di stile e icone (nel <head>)
  testata.html  la testata: marchio, menu degli strumenti e delle informazioni, ✱ e ◐, menu del telefono
  piede.html    la riga finale del piè (simbolo e collegamenti); le fonti di ogni pagina strumento
                (.piede-fonti) restano nella pagina, sopra la riga
In ogni pagina sono racchiuse tra marcatori <!-- testa --> … <!-- /testa -->, <!-- testata --> … <!-- /testata -->,
<!-- piede --> … <!-- /piede -->; lo script rimette dentro il contenuto del modello, con la voce di menu della
pagina segnata da aria-current="page". Con --versione cambia anche il numero di versione (?v=…) in tutte le
pagine e negli script che lo usano, così i browser e Cloudflare non usano copie vecchie.

  python costruisci_pagine.py                      # rigenera le parti con la versione attuale
  python costruisci_pagine.py --versione 20261028a # e cambia la versione ovunque
  python costruisci_pagine.py --controlla          # esce con 1 se qualche pagina non è aggiornata (nessuna scrittura)

La prima volta, se una pagina non ha ancora i marcatori, li aggiunge attorno ai blocchi esistenti.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

QUI = Path(__file__).resolve().parent
SITO = QUI / "sito"
PARTI = QUI / "parti"
ESCLUSE = {"link.html"}                 # pagina di solo rimando, senza testata
VERS = re.compile(r"(?<=\?v=)\d{8}[a-z]?")      # ?v=20261027r
VERS_JS = re.compile(r'(const V = ")(\d{8}[a-z]?)(")')

# blocchi riconosciuti la prima volta, prima che ci siano i marcatori
PRIMA = {
    "testa": re.compile(r'<script>/\* tema e vestito.*?icona_16_chiaro\.svg\?v=\w+">', re.S),
    "testata": re.compile(r'<header class="testata">.*?</header>', re.S),
    "piede": re.compile(r'  <img class="piede-simbolo".*?<p class="piede-testi">.*?</p>', re.S),
}


def marcati(nome: str) -> re.Pattern:
    return re.compile(rf"(<!-- {nome} -->\n)(.*?)(\n *<!-- /{nome} -->)", re.S)


def versione_attuale(sito: Path) -> str:
    m = VERS.search((sito / "index.html").read_text(encoding="utf-8"))
    if not m:
        sys.exit("versione non trovata in index.html")
    return m.group(0)


def indirizzo(pagina: str) -> str:
    return "./" if pagina == "index.html" else pagina


def segna_voce(testata: str, pagina: str) -> str:
    """aria-current="page" sui collegamenti alla pagina stessa (menu del computer e del telefono, non il marchio)."""
    href = indirizzo(pagina)
    def sost(m: re.Match) -> str:
        tag = m.group(0)
        if 'class="marchio"' in tag or f'href="{href}"' not in tag or "aria-current" in tag:
            return tag
        return tag[:-1] + ' aria-current="page">'
    return re.sub(r"<a [^>]*>", sost, testata)


def costruisci(pagina: Path, parti: dict[str, str], versione: str) -> str:
    s = pagina.read_text(encoding="utf-8")
    for nome, testo in parti.items():
        if nome == "testata":
            testo = segna_voce(testo, pagina.name)
        testo = testo.replace("{{versione}}", versione).rstrip("\n")
        rx = marcati(nome)
        if rx.search(s):
            s = rx.sub(lambda m: m.group(1) + testo + m.group(3), s, count=1)
        else:
            m = PRIMA[nome].search(s)
            if not m:
                raise SystemExit(f"{pagina.name}: blocco «{nome}» non trovato")
            rientro = "  " if nome == "piede" else ""
            s = s[:m.start()] + f"{rientro}<!-- {nome} -->\n{testo}\n{rientro}<!-- /{nome} -->" + s[m.end():]
    return VERS.sub(versione, s)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sito", type=Path, default=SITO, help="cartella del sito (predefinita: sito/ accanto allo script)")
    p.add_argument("--versione", help="nuovo numero di versione, es. 20261028a")
    p.add_argument("--controlla", action="store_true", help="non scrive: esce con 1 se una pagina va rigenerata")
    a = p.parse_args(argv)
    sito = a.sito
    versione = a.versione or versione_attuale(sito)
    if not re.fullmatch(r"\d{8}[a-z]?", versione):
        sys.exit("versione: 8 cifre (aaaammgg) e al più una lettera")
    parti = {n: (PARTI / f"{n}.html").read_text(encoding="utf-8") for n in ("testa", "testata", "piede")}
    diverse = []
    for pagina in sorted(sito.glob("*.html")):
        if pagina.name in ESCLUSE:
            continue
        nuovo = costruisci(pagina, parti, versione)
        if nuovo != pagina.read_text(encoding="utf-8"):
            diverse.append(pagina.name)
            if not a.controlla:
                pagina.write_text(nuovo, encoding="utf-8")
    for js in sorted(sito.glob("*.js")):            # versioni scritte negli script (dati letti con fetch)
        t = js.read_text(encoding="utf-8")
        n = VERS_JS.sub(lambda m: m.group(1) + versione + m.group(3), VERS.sub(versione, t))
        if n != t:
            diverse.append(js.name)
            if not a.controlla:
                js.write_text(n, encoding="utf-8")
    azione = "da rigenerare" if a.controlla else "aggiornati"
    print(f"versione {versione}: {len(diverse)} file {azione}" + (f" ({', '.join(diverse)})" if diverse else ""))
    return 1 if (a.controlla and diverse) else 0


if __name__ == "__main__":
    sys.exit(main())
