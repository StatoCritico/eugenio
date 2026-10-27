#!/usr/bin/env python3
"""Caratteri del sito ospitati in sito/font, con il loro font.css: i browser dei visitatori non chiamano
Google Fonts né altri servizi (privacy). Tutti con licenza SIL OFL 1.1.

  Hanken Grotesk (testo): carattere variabile, tondo pesi 100-900 e corsivo 400, da Google Fonts
                          (sottoinsiemi latin, latin-ext, cyrillic-ext, vietnamese)
  Barlow (titoli):        pesi 500, 600, 700, sottoinsiemi latin e latin-ext, dal pacchetto npm
                          @fontsource/barlow (versione bloccata qui sotto) tramite jsDelivr

  python scarica_font.py             # scarica i file .woff2 e riscrive font.css
  python scarica_font.py --solo-css  # niente rete: riscrive solo font.css dai file già presenti

Il vecchio carattere dei titoli (Bricolage Grotesque, file f0-f2) non si usa più.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

QUI = Path(__file__).resolve().parent
DEST = QUI / "sito" / "font"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"   # per avere woff2
HANKEN_CSS = ("https://fonts.googleapis.com/css2?family=Hanken+Grotesk:ital,wght@0,100..900;1,400&display=swap")
BARLOW_NPM = "https://cdn.jsdelivr.net/npm/@fontsource/barlow@5.3.0/files/barlow-{sub}-{peso}-normal.woff2"

R = {   # unicode-range dei sottoinsiemi (come Google Fonts e Fontsource)
    "cyrillic-ext": "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F",
    "vietnamese": "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, "
                  "U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB",
    "latin-ext": "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, "
                 "U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, "
                 "U+A720-A7FF",
    "latin": "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, "
             "U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
}

# (famiglia, stile, peso, sottoinsieme, file): l'ordine è quello di font.css
FACCE = [
    ("Hanken Grotesk", "normal", "100 900", "cyrillic-ext", "f3.woff2"),
    ("Hanken Grotesk", "normal", "100 900", "vietnamese", "f4.woff2"),
    ("Hanken Grotesk", "normal", "100 900", "latin-ext", "f5.woff2"),
    ("Hanken Grotesk", "normal", "100 900", "latin", "f6.woff2"),
    ("Hanken Grotesk", "italic", "400", "cyrillic-ext", "f9.woff2"),
    ("Hanken Grotesk", "italic", "400", "vietnamese", "f8.woff2"),
    ("Hanken Grotesk", "italic", "400", "latin-ext", "f7.woff2"),
    ("Hanken Grotesk", "italic", "400", "latin", "f10.woff2"),
] + [("Barlow", "normal", p, s, f"barlow-{p}-{s}.woff2") for p in ("500", "600", "700") for s in ("latin-ext", "latin")]

INTESTAZIONE = """/* Caratteri ospitati sul sito, niente richieste a terzi.
   Hanken Grotesk (testo): Google Fonts, OFL; il tondo è un carattere variabile (pesi 100-900).
   Barlow (titoli): @fontsource/barlow 5.3.0 da npm, OFL; pesi 500, 600, 700, sottoinsiemi latin e latin-ext. */
"""


def titolo(famiglia: str, stile: str, peso: str, sub: str) -> str:
    if famiglia == "Barlow":
        return f"Barlow {peso}, {sub}"
    return f"Hanken Grotesk{' corsivo' if stile == 'italic' else ''}, {sub}"


def font_css() -> str:
    blocchi = [INTESTAZIONE]
    for fam, stile, peso, sub, file in FACCE:
        blocchi.append(f"""
/* {titolo(fam, stile, peso, sub)} */
@font-face {{
  font-family: '{fam}';
  font-style: {stile};
  font-weight: {peso};
  font-display: swap;
  src: url({file}) format('woff2');
  unicode-range: {R[sub]};
}}
""")
    return "".join(blocchi)


def scarica(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()


def scarica_tutto(dest: Path) -> None:
    css = scarica(HANKEN_CSS).decode()
    # blocchi "/* latin */ @font-face { font-style: …; src: url(…) …; unicode-range: … }"
    hanken = {}
    for sub, corpo in re.findall(r"/\*\s*([a-z-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", css, re.S):
        stile = re.search(r"font-style:\s*(\w+)", corpo).group(1)
        hanken[(stile, sub)] = re.search(r"url\((https://[^)]+)\)", corpo).group(1)
    for fam, stile, peso, sub, file in FACCE:
        url = hanken.get((stile, sub)) if fam == "Hanken Grotesk" else BARLOW_NPM.format(sub=sub, peso=peso)
        if not url:
            sys.exit(f"Google Fonts non ha restituito {fam} {stile} {sub}")
        (dest / file).write_bytes(scarica(url))
        print("scaricato", file)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dest", type=Path, default=DEST)
    p.add_argument("--solo-css", action="store_true", help="non scarica: riscrive font.css dai file presenti")
    a = p.parse_args(argv)
    a.dest.mkdir(parents=True, exist_ok=True)
    if not a.solo_css:
        scarica_tutto(a.dest)
    mancanti = [f for *_, f in FACCE if not (a.dest / f).exists()]
    if mancanti:
        sys.exit(f"mancano in {a.dest}: {', '.join(mancanti)}")
    (a.dest / "font.css").write_text(font_css(), encoding="utf-8")
    print("font.css scritto in", a.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
