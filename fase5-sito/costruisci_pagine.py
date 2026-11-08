#!/usr/bin/env python3
"""Testata, piè e parte comune del <head> delle pagine del sito da un unico modello.

Le parti comuni stanno in parti/ (accanto a questo file):
  testa.html    script del tema e del vestito, foglio di stile e icone (nel <head>)
  testata.html  la testata: marchio, menu dei servizi a cinque gruppi con sottomenu a tendina (dal 03/11/2026), altre
                pagine (Indicatori, Come funziona …), ✱ e ◐, menu del telefono, riga del menu fissato (04/11/2026,
                riempita da aspetto.js); le voci «licenza GME» non sono collegamenti (span.voce-gme)
  piede.html    la riga finale del piè (simbolo e collegamenti); le fonti di ogni pagina strumento
                (.piede-fonti) restano nella pagina, sopra la riga
In ogni pagina sono racchiuse tra marcatori <!-- testa --> … <!-- /testa -->, <!-- testata --> … <!-- /testata -->,
<!-- piede --> … <!-- /piede -->; lo script rimette dentro il contenuto del modello, con la voce di menu della
pagina segnata da aria-current="page" e il suo gruppo da data-attivo. Con --versione cambia anche il numero di versione (?v=…) in tutte le
pagine e negli script che lo usano, così i browser e Cloudflare non usano copie vecchie.

  python costruisci_pagine.py                      # rigenera le parti con la versione attuale
  python costruisci_pagine.py --versione 20261028a # e cambia la versione ovunque
  python costruisci_pagine.py --controlla          # esce con 1 se qualche pagina non è aggiornata (nessuna scrittura)

La prima volta, se una pagina non ha ancora i marcatori, li aggiunge attorno ai blocchi esistenti.

Menu dell'08/11/2026 (decisione di Paolo): le voci «in lavorazione» (span.voce-gme.voce-corso, triangolo giallo, title
«In lavorazione: disponibile prossimamente») non sono collegamenti, come le voci GME. Dal menu della testata lo script
ricava anche, per ogni pagina: l'elenco «Nello stesso gruppo» (<ul class="stesso-gruppo">, voci in lavorazione e GME
senza collegamento), l'etichetta del gruppo sopra il titolo (<p class="gruppo-servizio">) e, per le pagine in
lavorazione, l'avviso «Pagina in lavorazione, non ancora verificata» in cima (<!-- in-lavorazione --> … ). Le pagine
restano nel sito, raggiungibili solo con l'indirizzo diretto.

Novità (07/11/2026): da novita.toml (accanto a questo file, una voce per pubblicazione, la più recente in cima) genera
sito/novita.html (pagina di testo con l'indice laterale per versione) e il feed Atom sito/novita.xml; nella testata il
collegamento «Novità» porta la versione dell'ultima voce (data-ultima, pallino in aspetto.js se è più nuova dell'ultima
vista). A ogni pubblicazione si aggiunge una voce (regola permanente, README della fase 5).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
import tomllib
from pathlib import Path

QUI = Path(__file__).resolve().parent
SITO = QUI / "sito"
PARTI = QUI / "parti"
ESCLUSE = {"link.html"}                 # pagina di solo rimando, senza testata
NOVITA = QUI / "novita.toml"
SITO_PUBBLICO = "https://eugenio.statocritico.it/"
MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
        "novembre", "dicembre")
# (08/11/2026, decisione di Paolo) solo funzioni per gli utenti: servizi pubblicati, migliorati, verificati (validati)
GRUPPI_NOVITA = (("nuovo", "Nuovo"), ("migliorato", "Migliorato"), ("verificato", "Verificato"))
CAMPI_NOVITA = {"data", "versione", "titolo", "testo", "collegamenti", *(k for k, _ in GRUPPI_NOVITA)}
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
    """aria-current="page" sui collegamenti alla pagina stessa (menu del computer e del telefono, non il marchio).

    Le voci in attesa della licenza GME (dal 04/11/2026) non sono collegamenti: <span class="voce-gme" data-pagina=…>;
    sulla loro pagina prendono anch'esse aria-current, così il gruppo resta segnato con data-attivo."""
    href = indirizzo(pagina)
    def sost(m: re.Match) -> str:
        tag = m.group(0)
        if 'class="marchio"' in tag or f'href="{href}"' not in tag or "aria-current" in tag:
            return tag
        return tag[:-1] + ' aria-current="page">'
    def sost_gme(m: re.Match) -> str:
        tag = m.group(0)
        if f'data-pagina="{href}"' not in tag or "aria-current" in tag:
            return tag
        return tag[:-1] + ' aria-current="page">'
    testata = re.sub(r'<span class="voce-gme[^"]*"[^>]*>', sost_gme, re.sub(r"<a [^>]*>", sost, testata))
    return segna_gruppo(testata)


GRUPPO = re.compile(r'(<details class="(?:voce-gruppo|pannello-gruppo)"[^>]*)(>.*?</details>)', re.S)


def segna_gruppo(testata: str) -> str:
    """data-attivo sul gruppo del menu (computer e telefono) che contiene la pagina; sul telefono il gruppo è già aperto."""
    def sost(m: re.Match) -> str:
        if 'aria-current="page"' not in m.group(2):
            return m.group(0)
        aperto = " open" if "pannello-gruppo" in m.group(1) else ""
        return m.group(1) + " data-attivo" + aperto + m.group(2)
    return GRUPPO.sub(sost, testata)


# ------------------------------------------------------------------- gruppi del menu e pagine in lavorazione (08/11/2026)
CORSO_TITOLO = "In lavorazione: disponibile prossimamente"
GME_TITOLO = "In attesa di autorizzazione dal GME"
VOCE_TENDINA = re.compile(r'<li>(?:<a href="([^"]+)">(.*?)</a>|<span class="voce-gme( voce-corso)?" data-pagina="([^"]+)"[^>]*>'
                          r'<span class="voce-nome">(.*?)</span>.*?)</li>')
AVVISO_CORSO = re.compile(r"<!-- in-lavorazione -->\n.*?<!-- /in-lavorazione -->\n\n?", re.S)


def gruppi_menu(testata: str) -> list[dict]:
    """[{id, titolo, voci: [{pagina, nome, tipo}]}] dalle tendine della testata; tipo: "" (collegamento), "gme", "corso"."""
    out = []
    for m in re.finditer(r'<details class="voce-gruppo" data-gruppo="([^"]+)"><summary>([^<]+)</summary>\s*<ul class="tendina">(.*?)</ul>', testata, re.S):
        voci = []
        for v in VOCE_TENDINA.finditer(m.group(3)):
            if v.group(1):
                nome = re.sub(r"<span class=\"cantiere.*", "", v.group(2), flags=re.S).strip()
                voci.append({"pagina": v.group(1), "nome": nome, "tipo": ""})
            else:
                voci.append({"pagina": v.group(4), "nome": v.group(5), "tipo": "corso" if v.group(3) else "gme"})
        out.append({"id": m.group(1), "titolo": m.group(2), "voci": voci})
    return out


def pagine_in_corso(testata: str) -> set[str]:
    return {v["pagina"] for g in gruppi_menu(testata) for v in g["voci"] if v["tipo"] == "corso"}


def gruppo_di(gruppi: list[dict], pagina: str) -> dict | None:
    href = indirizzo(pagina)
    return next((g for g in gruppi if any(v["pagina"] == href for v in g["voci"])), None)


def elenco_stesso_gruppo(g: dict, pagina: str) -> str:
    href, righe = indirizzo(pagina), []
    for v in g["voci"]:
        if v["pagina"] == href:
            righe.append(f'    <li><a href="{v["pagina"]}" aria-current="page">{v["nome"]}</a></li>')
        elif v["tipo"] == "gme":
            righe.append(f'    <li><span class="voce-gme" aria-disabled="true" title="{GME_TITOLO}">{v["nome"]}'
                         '<span class="solo-lettori">: in attesa di autorizzazione dal GME</span></span></li>')
        elif v["tipo"] == "corso":
            righe.append(f'    <li><span class="voce-gme voce-corso" aria-disabled="true" title="{CORSO_TITOLO}">{v["nome"]}'
                         '<span class="solo-lettori">: in lavorazione, disponibile prossimamente</span></span></li>')
        else:
            righe.append(f'    <li><a href="{v["pagina"]}">{v["nome"]}</a></li>')
    return "\n".join(righe)


def avviso_corso() -> str:
    return ('<!-- in-lavorazione -->\n<div class="messaggio attenzione avviso-lavorazione" role="note"><div><strong>Pagina in lavorazione, '
            'non ancora verificata.</strong> Non è ancora collegata dal menu: funzioni e risultati possono essere incompleti o '
            'sbagliati e cambiare senza avviso. I servizi disponibili sono nel menu (Clima e meteo, Patrimonio, Statistiche).'
            '</div></div>\n<!-- /in-lavorazione -->\n\n')


def applica_gruppi(s: str, pagina: str, testata: str) -> str:
    gruppi = gruppi_menu(testata)
    g = gruppo_di(gruppi, pagina)
    if g:
        s = re.sub(r'(<ul class="stesso-gruppo">\n).*?(\n *</ul>)', lambda m: m.group(1) + elenco_stesso_gruppo(g, pagina) + m.group(2), s,
                   count=1, flags=re.S)
        s = re.sub(r'(<p class="gruppo-servizio">)[^<]*(</p>)', lambda m: m.group(1) + g["titolo"] + m.group(2), s, count=1)
    s = AVVISO_CORSO.sub("", s)
    if indirizzo(pagina) in pagine_in_corso(testata):
        s = s.replace("<!-- /testata -->\n\n", "<!-- /testata -->\n\n" + avviso_corso(), 1)
    return s


def costruisci(pagina: Path, parti: dict[str, str], versione: str) -> str:
    s = applica_gruppi(pagina.read_text(encoding="utf-8"), pagina.name, parti["testata"])
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


def _senza_parti(s: str) -> str:
    """La pagina senza il contenuto dei blocchi comuni (per confrontare la pagina delle novità con quella generata)."""
    for nome in ("testa", "testata", "piede"):
        s = marcati(nome).sub(lambda m: m.group(1) + m.group(3), s)
    return VERS.sub("V", s)


# ---------------------------------------------------------------------------------------------- Novità (07/11/2026)
def leggi_novita(file: Path = NOVITA) -> list[dict]:
    """Voci di novita.toml controllate: data, versione, titolo, almeno una riga (o il `testo`); la più recente in cima.
    La versione è facoltativa solo per una voce con il `testo` e senza elenchi (08/11/2026: «Meet EuGEnio» del 26/10,
    messa online, nessuna versione nota); la prima voce ha sempre la versione di index.html (test)."""
    if not file.exists():
        return []
    voci = tomllib.loads(file.read_text(encoding="utf-8")).get("voce", [])
    prima = None
    for v in voci:
        dt.date.fromisoformat(str(v.get("data", "")))
        if set(v) - CAMPI_NOVITA:     # per esempio i vecchi «cambiato» e «corretto»: non si perdono in silenzio
            raise SystemExit(f"novita.toml: campi sconosciuti {sorted(set(v) - CAMPI_NOVITA)} nella voce {ancora(v)}")
        solo_testo = bool(str(v.get("testo", "")).strip()) and not any(v.get(k) for k, _ in GRUPPI_NOVITA)
        versione_ok = re.fullmatch(r"\d{8}[a-z]?", str(v.get("versione", ""))) or (solo_testo and "versione" not in v)
        if not versione_ok or not str(v.get("titolo", "")).strip():
            raise SystemExit(f"novita.toml: voce {v.get('versione')!r} senza versione valida o senza titolo")
        if not any(v.get(k) for k, _ in GRUPPI_NOVITA) and not solo_testo:
            raise SystemExit(f"novita.toml: voce {ancora(v)} senza righe")
        if prima is not None and (v["data"], v.get("versione", "")) > prima:
            raise SystemExit("novita.toml: le voci vanno dalla più recente alla più vecchia")
        prima = (v["data"], v.get("versione", ""))
    return voci


def ancora(v: dict, voci: list[dict] | None = None) -> str:
    """Ancora e identificativo stabile della voce, **senza la versione** (08/11/2026, Paolo: la versione del sito resta
    solo in novita.toml): d<aaaammgg>, e per la seconda, terza… voce dello stesso giorno d<aaaammgg>-2, -3 (contate dalla
    più vecchia, così non cambiano quando se ne aggiunge una sopra)."""
    base = "d" + str(v["data"]).replace("-", "")
    if not voci:
        return base
    i = next(k for k, x in enumerate(voci) if x is v)
    n = sum(1 for x in voci[i + 1:] if x["data"] == v["data"])
    return base if n == 0 else f"{base}-{n + 1}"


def data_italiana(d: str) -> str:
    g = dt.date.fromisoformat(d)
    return f"{g.day} {MESI[g.month - 1]} {g.year}"


def _corpo_voce(v: dict, assoluti: bool = False) -> str:
    e = html.escape
    def url(u: str) -> str:
        return u if not assoluti or re.match(r"https?://", u) else SITO_PUBBLICO + u
    righe = []
    if str(v.get("testo", "")).strip():
        righe.append(f'<p class="novita-testo">{e(str(v["testo"]).strip())}</p>')
    for k, nome in GRUPPI_NOVITA:
        if v.get(k):
            righe.append(f'<p class="novita-tipo">{nome}</p>\n<ul>' + "".join(f"<li>{e(str(x))}</li>" for x in v[k]) + "</ul>")
    if v.get("collegamenti"):
        righe.append('<p class="novita-collegamenti">' + " · ".join(
            f'<a href="{e(url(str(c["indirizzo"])))}">{e(str(c["testo"]))}</a>' for c in v["collegamenti"]) + "</p>")
    return "\n".join(righe)


def pagina_novita(voci: list[dict]) -> str:
    """sito/novita.html con i marcatori di testa, testata e piede (li riempie costruisci())."""
    e = html.escape
    sezioni = []
    for v in voci:
        # (08/11/2026) nessuna versione del sito in pagina: data, titolo e gruppi
        sezioni.append(f'  <h2 id="{ancora(v, voci)}">{data_italiana(v["data"])} – {e(v["titolo"])}</h2>\n'
                       f'  <div class="novita-voce">\n    '
                       + _corpo_voce(v).replace("\n", "\n    ") + "\n  </div>")
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EuGEnio – Novità</title>
<meta name="description" content="Le novità di EuGEnio, versione per versione: servizi nuovi, servizi migliorati e servizi verificati.">
<!-- testa -->

<!-- /testa -->
</head>
<body>
<!-- testata -->

<!-- /testata -->

<main class="articolo novita" data-ultima="{voci[0]["versione"] if voci else ""}">
  <h1>Novità</h1>
  <p class="sotto">Le funzioni di EuGEnio per chi lo usa, pubblicazione per pubblicazione, dalla più recente: servizi
    nuovi, servizi migliorati e servizi verificati (non più sperimentali). Le stesse voci sono nel
    <a href="novita.xml">feed Atom</a> (per seguirle con un lettore di feed) e nelle
    <a href="https://github.com/statocritico/eugenio/releases">release del codice su GitHub</a>.</p>

{chr(10).join(sezioni)}
</main>

<footer class="piede">
  <!-- piede -->

  <!-- /piede -->
</footer>
<script src="aspetto.js?v={{{{versione}}}}"></script>
<script src="indice.js?v={{{{versione}}}}"></script>
</body>
</html>
"""


def feed_novita(voci: list[dict]) -> str:
    """Feed Atom (RFC 4287) delle voci, con indirizzi assoluti."""
    e = html.escape
    def quando(v):
        return f"{v['data']}T12:00:00Z"
    voci_xml = []
    for v in voci:
        contenuto = _corpo_voce(v, assoluti=True)
        voci_xml.append(f"""  <entry>
    <title>{e(data_italiana(v["data"]))} – {e(v["titolo"])}</title>
    <id>tag:eugenio.statocritico.it,2026:novita/{ancora(v, voci)}</id>
    <link rel="alternate" type="text/html" href="{SITO_PUBBLICO}novita.html#{ancora(v, voci)}"/>
    <updated>{quando(v)}</updated>
    <summary>{e(str(v.get("testo") or v["titolo"]).strip())}</summary>
    <content type="html">{e(contenuto)}</content>
  </entry>""")
    agg = quando(voci[0]) if voci else "2026-10-27T12:00:00Z"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="it">
  <title>Novità di EuGEnio</title>
  <subtitle>Le novità di EuGEnio (Stato Critico), versione per versione.</subtitle>
  <id>tag:eugenio.statocritico.it,2026:novita</id>
  <link rel="self" type="application/atom+xml" href="{SITO_PUBBLICO}novita.xml"/>
  <link rel="alternate" type="text/html" href="{SITO_PUBBLICO}novita.html"/>
  <updated>{agg}</updated>
  <author><name>Stato Critico</name><uri>https://statocritico.it</uri></author>
  <icon>{SITO_PUBBLICO}logo/corallo/icona_32_chiaro.svg</icon>
{chr(10).join(voci_xml)}
</feed>
"""


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
    voci = leggi_novita()
    parti["testata"] = parti["testata"].replace("{{novita}}", voci[0]["versione"] if voci else "")
    if voci:                                        # pagina e feed delle novità, generati da novita.toml
        for nome, testo in (("novita.html", pagina_novita(voci).replace("{{versione}}", versione)), ("novita.xml", feed_novita(voci))):
            f = sito / nome
            vecchio = f.read_text(encoding="utf-8") if f.exists() else None
            if nome.endswith(".html"):
                # confronto senza i blocchi comuni (li riempie il giro sulle pagine, qui sotto)
                if vecchio is None or _senza_parti(vecchio) != _senza_parti(testo):
                    diverse.append(nome)
                    if not a.controlla:
                        f.write_text(testo, encoding="utf-8")
            elif vecchio != testo:
                diverse.append(nome)
                if not a.controlla:
                    f.write_text(testo, encoding="utf-8")
    for pagina in sorted(sito.glob("*.html")):
        if pagina.name in ESCLUSE:
            continue
        nuovo = costruisci(pagina, parti, versione)
        if nuovo != pagina.read_text(encoding="utf-8"):
            if pagina.name not in diverse:
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
