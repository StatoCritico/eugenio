#!/usr/bin/env python3
"""Costruisce sito/dati/dpr412.json e sito/dati/dpr412.csv dall'Allegato A del DPR 412/93.

Fonte (da citare): DPR 26 agosto 1993, n. 412, Allegato A, testo vigente su Normattiva
(esportazione Akoma Ntoso, ultimo aggiornamento all'atto 28/04/2022). Atto normativo,
non coperto da diritto d'autore (art. 5 L. 633/1941).

Abbinamento al codice ISTAT attuale con i file ISTAT:
  * Elenco-comuni-italiani.csv (comuni attuali);
  * Elenco comuni soppressi.csv (comuni soppressi, con il comune in cui sono confluiti);
  * Variazioni amministrative e territoriali dal 1991 (.xlsx: cambi di nome CD, di provincia AP,
    nuovi comuni CS, estinzioni ES).
Il CSV di Andrea Borruso (zone.csv) è usato solo come controllo incrociato, se presente.

Modifiche successive al 1993: l'Allegato A è stato modificato da 58 decreti (1994-2016). Il testo vigente le
contiene già (senza segni, tranne Casalattico tra (( ))); con --modifiche (file prodotto da
script/bisezione.py e script/storia_modifiche.py sul testo multivigente di Normattiva) ogni comune modificato
riceve in nota l'atto, la data di entrata in vigore e il valore originario del 1993.

Uso:
  python3 costruisci_dpr412.py --akn dpr412.akn.xml --istat CARTELLA_ISTAT --out sito/dati \
      [--borruso zone.csv] [--rapporto abbinamento_dpr412.md] [--modifiche modifiche_allegato_a.json]

Se --akn non esiste, il file va scaricato a mano da Normattiva (pagina dell'atto → "esporta in
Akoma ntoso"); la sessione del sito non permette uno scaricamento diretto affidabile.
Le cartelle ISTAT si scaricano da https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
(lo script le scarica da sé se mancano).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import html
import io
import json
import re
import sys
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

URL_NORMATTIVA = ("https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente."
                  "della.repubblica:1993-08-26;412!vig=")
URL_ISTAT = {
    "elenco": "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv",
    "soppressi": "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-soppressi.zip",
    "variazioni": ("https://www.istat.it/storage/codici-unita-amministrative/"
                   "Variazioni-amministrative-e-territoriali-dal-1991.zip"),
}
FONTE = ("DPR 26 agosto 1993, n. 412, Allegato A (testo vigente, Normattiva, ultimo aggiornamento "
         "all'atto 28/04/2022, con le modifiche dei decreti dal 1994 al 2016 verificate sul testo multivigente); "
         "abbinamento ai codici ISTAT attuali a cura di EuGEnio")

# Sigle del DPR (1993) → codice regione ISTAT. Comprende le province poi soppresse o rinominate.
REGIONE_SIGLA_1993 = {
    "TO": "01", "VC": "01", "NO": "01", "CN": "01", "AT": "01", "AL": "01", "BI": "01",
    "AO": "02",
    "VA": "03", "CO": "03", "SO": "03", "MI": "03", "BG": "03", "BS": "03", "PV": "03",
    "CR": "03", "MN": "03",
    "BZ": "04", "TN": "04",
    "VR": "05", "VI": "05", "BL": "05", "TV": "05", "VE": "05", "PD": "05", "RO": "05",
    "UD": "06", "GO": "06", "TS": "06", "PN": "06",
    "IM": "07", "SV": "07", "GE": "07", "SP": "07",
    "PC": "08", "PR": "08", "RE": "08", "MO": "08", "BO": "08", "FE": "08", "RA": "08", "FO": "08",
    "MS": "09", "LU": "09", "PT": "09", "FI": "09", "LI": "09", "PI": "09", "AR": "09", "SI": "09",
    "GR": "09",
    "PG": "10", "TR": "10",
    "PS": "11", "AN": "11", "MC": "11", "AP": "11",
    "VT": "12", "RI": "12", "RM": "12", "LT": "12", "FR": "12",
    "AQ": "13", "TE": "13", "PE": "13", "CH": "13",
    "CB": "14", "IS": "14",
    "CE": "15", "BN": "15", "NA": "15", "AV": "15", "SA": "15",
    "FG": "16", "BA": "16", "TA": "16", "BR": "16", "LE": "16",
    "PZ": "17", "MT": "17", "MR": "17",  # "MR" è un refuso del DPR per MT (Irsina)
    "CS": "18", "CZ": "18", "RC": "18",
    "TP": "19", "PA": "19", "ME": "19", "AG": "19", "CL": "19", "EN": "19", "CT": "19", "RG": "19",
    "SR": "19",
    "SS": "20", "NU": "20", "CA": "20", "OR": "20",
}

# Province attuali che possono contenere comuni di una provincia del 1993 (nuove province, scorpori).
PROVINCE_FIGLIE = {
    "NO": {"VB"}, "VC": {"BI", "VB"}, "CO": {"LC"}, "BG": {"LC"}, "MI": {"LO", "MB"},
    "FO": {"FC", "RN"}, "PS": {"PU", "RN"}, "FI": {"PO"}, "CZ": {"KR", "VV"}, "AP": {"FM"},
    "BA": {"BT"}, "FG": {"BT"}, "MR": {"MT"}, "BL": {"PN", "UD"}, "PN": {"BL"}, "AN": {"MC", "PU"},
    "SS": {"SS", "NU", "OR", "OT", "SU"}, "NU": {"NU", "OR", "SS", "OG", "SU", "CA"},
    "CA": {"SU", "CA", "OR", "NU", "CI", "VS"}, "OR": {"OR", "NU", "SU", "CA", "SS"},
}

# Correzioni di refusi del DPR (nome nel DPR → nome da cercare). Ognuna verificata a mano.
CORREZIONI = {
    ("RC", "BRUZZANO ZEFFIRI0"): "BRUZZANO ZEFFIRIO",
    ("CT", "PATERN0'"): "PATERNO'",
    ("CT", "SAN MICHELE DI GARANZIA"): "SAN MICHELE DI GANZARIA",
    ("AV", "MUSCO"): "NUSCO",  # 914 m, unico comune AV senza riga: Nusco
}

# Abbinamenti decisi a mano (provincia, nome DPR) → codice ISTAT attuale, con motivo.
# Riempito dopo l'esame degli scarti (vedi abbinamento_dpr412.md).
MANUALI: dict[tuple[str, str], tuple[str, str]] = {
    ("BG", "CORTENOVA"): ("016083", "nel DPR come CORTENOVA (BG, 133 m): è Cortenuova; Cortenova è in "
                                    "provincia di Como, oggi Lecco, ed è già nel DPR"),
    # Segnalazione dell'utente (27/10/2026): abbinare a Conversano. NON applicata: Conversano ha già una sua riga
    # (BA D 1642 219 CONVERSANO, 219 m come la sua casa comunale) e ne avrebbe due; ISOLA DI BARI (C, 1187 GG,
    # 5 m) sta in ordine alfabetico tra MODUGNO e MOLFETTA, cioè al posto di Mola di Bari, che altrimenti resterebbe
    # senza valore, e la quota di 5 m è quella di Mola (sul mare). Vedi abbinamento_dpr412.md.
    ("BA", "ISOLA DI BARI"): ("072028", "nel DPR come ISOLA DI BARI: è Mola di Bari (5 m, posto alfabetico tra "
                                        "Modugno e Molfetta; Conversano ha già una sua riga)"),
}

# Righe del DPR da non abbinare (provincia, nome, gg) → motivo.
ESCLUSE: dict[tuple[str, str, int], str] = {
    ("FR", "FERENTINO", 2587): ("seconda riga FERENTINO (2587 GG, 801 m) subito dopo quella da 2222 GG; "
                                "entrambe vengono dai due D.M. del 24 e 30 ottobre 2008 (G.U. n. 279 del 28/11/2008), "
                                "che hanno tolto la riga del 1993 (D, 1913 GG, 395 m); nessun comune della provincia "
                                "di Frosinone resta senza valore: si tiene la prima riga (2222 GG), che è anche quella "
                                "delle raccolte correnti. DA VERIFICARE sul testo dei due decreti"),
}


def norm(s: str) -> str:
    s = s.replace("0", "O") if re.search(r"[A-Za-z]0|0[A-Za-z']", s) else s
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper().replace("’", "'")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


MINUSCOLE = {"di", "del", "della", "dello", "dei", "degli", "delle", "da", "dal", "dalla", "in", "a", "al",
             "alla", "allo", "e", "ed", "sul", "sulla", "sullo", "con", "nel", "nella", "per", "sotto", "sopra"}


def leggibile(nome: str) -> str:
    """"CASTELLO DI SERRAVALLE" → "Castello di Serravalle", "VITO D'ASIO" → "Vito d'Asio"."""
    out = []
    for i, p in enumerate(nome.lower().split()):
        if "'" in p:
            a, b = p.split("'", 1)
            p = (a if a in ("d", "l", "dell", "all", "nell", "sull") and i else a.capitalize()) + "'" + b.capitalize()
        elif not (i and p in MINUSCOLE):
            p = "-".join(x.capitalize() for x in p.split("-"))
        out.append(p)
    return " ".join(out)


def compatto(s: str) -> str:
    """Chiave senza spazi, con J = I (Jesolo/Iesolo, Buja/Buia)."""
    return norm(s).replace(" ", "").replace("J", "I")


# ---------------------------------------------------------------- lettura DPR

def leggi_dpr(path: Path) -> list[dict]:
    t = path.read_text(encoding="utf-8")
    parti = re.findall(r'<doc name="Allegato A">(.*?)</doc>', t, flags=re.S)
    if len(parti) != 4:
        raise SystemExit(f"Attese 4 parti dell'Allegato A, trovate {len(parti)}")
    pat = re.compile(r"^\s*(\(\()?\s*([A-Z]{2})\s+([A-F0O])\s+([\dO]+)\s+([\dO]+)\s+(.+?)\s*(\)\))?\s*$")
    righe = []
    for i, p in enumerate(parti, 1):
        corpo = re.sub(r"<[^>]+>", "\n", p.split("<mainBody>")[-1])
        for l in html.unescape(corpo).split("\n"):
            m = pat.match(l)
            if not m:
                continue
            mod, pr, z, gg, alt, nome, _ = m.groups()
            righe.append(dict(parte=i, pr=pr, zona=z.replace("0", "O"), gg=int(gg.replace("O", "0")),
                              alt=int(alt.replace("O", "0")), nome=nome.strip(), modificato=bool(mod),
                              riga=l.strip()))
    return righe


# ---------------------------------------------------------------- ISTAT

def _scarica(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        print("Scarico", url, file=sys.stderr)
        with urllib.request.urlopen(url, timeout=120) as r:
            dest.write_bytes(r.read())
    return dest


def _da_zip(zpath: Path, suffisso: str) -> bytes:
    with zipfile.ZipFile(zpath) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(suffisso))
        return z.read(nome)


def leggi_istat(cartella: Path):
    import pandas as pd
    el = pd.read_csv(_scarica(URL_ISTAT["elenco"], cartella / "elenco.csv"), sep=";",
                     encoding="latin1", dtype=str, keep_default_na=False)
    cod_col = "Codice Comune formato alfanumerico"
    attuali = {}
    for _, r in el.iterrows():
        nomi = {r["Denominazione in italiano"], r["Denominazione (Italiana e straniera)"]}
        if r["Denominazione altra lingua"]:
            nomi.add(r["Denominazione altra lingua"])
        nomi |= set(str(r["Denominazione (Italiana e straniera)"]).split("/"))
        attuali[r[cod_col]] = dict(codice=r[cod_col], nome=r["Denominazione in italiano"],
                                   sigla=r["Sigla automobilistica"], regione=r["Codice Regione"],
                                   nomi={n for n in nomi if isinstance(n, str) and n.strip()})
    so = pd.read_csv(io.BytesIO(_da_zip(_scarica(URL_ISTAT["soppressi"], cartella / "soppressi.zip"),
                                        ".csv")), sep=";", encoding="latin1", dtype=str,
                     keep_default_na=False)
    soppressi = []
    for _, r in so.iterrows():
        soppressi.append(dict(anno=int(r["Anno"]), codice=r["Codice Comune"], nome=r["Denominazione Comune"],
                              sigla=r["Sigla Automobilistica"], verso=r["Codice del Comune associato alla variazione"],
                              verso_nome=r["Denominazione Comune associato alla variazione"],
                              data=r["Data evento"]))
    va = pd.read_excel(io.BytesIO(_da_zip(_scarica(URL_ISTAT["variazioni"], cartella / "variazioni.zip"),
                                          ".xlsx")), dtype=str, keep_default_na=False)
    va.columns = [c.strip() for c in va.columns]
    variazioni = []
    for _, r in va.iterrows():
        variazioni.append(dict(anno=int(r["Anno"]), tipo=str(r["Tipo variazione"]).strip(),
                               codice=r["Codice Comune formato alfanumerico"], nome=r["Denominazione Comune"],
                               verso=r["Codice del Comune associato alla variazione o nuovo codice Istat del Comune"],
                               verso_nome=r["Denominazione Comune associata alla variazione o nuova denominazione"],
                               testo=r["Contenuto del provvedimento"], data=r["Data decorrenza validità amministrativa"]))
    return attuali, soppressi, variazioni


class Storia:
    """Risale da un codice o nome storico al codice ISTAT attuale."""

    def __init__(self, attuali, soppressi, variazioni):
        self.attuali = attuali
        self.successivo: dict[str, str] = {}   # codice vecchio → codice nuovo (cambio provincia)
        self.confluito: dict[str, tuple[str, str]] = {}  # codice soppresso → (codice, data)
        self.nomi_storici: dict[str, set[tuple[str, str]]] = defaultdict(set)  # nome norm → {(codice, tipo)}
        self.nati_dopo: dict[str, list[str]] = defaultdict(list)  # codice nuovo comune → comuni d'origine
        for v in variazioni:
            if v["tipo"] == "AP" and v["verso"]:
                self.successivo[v["codice"]] = v["verso"]
            if v["tipo"] == "CD" and v["nome"]:
                self.nomi_storici[compatto(v["nome"])].add((v["codice"], "nome precedente"))
            if v["tipo"].startswith("CS") or v["tipo"] == "CS":
                self.nati_dopo[v["codice"]].append(v["verso_nome"])
        for s in soppressi:
            if s["anno"] < 1990 or not s["verso"]:
                continue
            self.confluito[s["codice"]] = (s["verso"], s["data"])
            self.nomi_storici[compatto(s["nome"])].add((s["codice"], "soppresso"))
        # comuni costituiti dopo il 1993 (fusioni o scorpori), riportati al codice attuale
        self.nuovi = {self.attuale(v["codice"]) for v in variazioni
                      if v["tipo"].startswith("CS") and v["anno"] >= 1993} - {None}
        # anche i codici di provincia precedenti delle tabelle 103/107/110 province non servono:
        # i nomi bastano, ma teniamo i codici AP per risalire

    def attuale(self, codice: str, passi=0) -> str | None:
        if passi > 20:
            return None
        if codice in self.attuali:
            return codice
        if codice in self.successivo:
            return self.attuale(self.successivo[codice], passi + 1)
        if codice in self.confluito:
            return self.attuale(self.confluito[codice][0], passi + 1)
        return None


# ---------------------------------------------------------------- abbinamento

def abbina(righe, attuali, storia: Storia):
    per_nome = defaultdict(list)          # nome normalizzato → codici attuali
    per_compatto = defaultdict(list)
    for c, a in attuali.items():
        for n in a["nomi"]:
            per_nome[norm(n)].append(c)
            per_compatto[compatto(n)].append(c)

    def compatibile(pr, cod):
        sig = attuali[cod]["sigla"]
        return sig == pr or sig in PROVINCE_FIGLIE.get(pr, set())

    def nel_territorio(pr, cod):
        """Stessa regione del 1993, oppure provincia "figlia" (Valmarecchia → RN, Sappada → UD)."""
        return attuali[cod]["regione"] == REGIONE_SIGLA_1993.get(pr) or compatibile(pr, cod)

    def scegli(pr, codici):
        codici = list(dict.fromkeys(c for c in codici if nel_territorio(pr, c)))
        if len(codici) > 1:
            codici = [c for c in codici if compatibile(pr, c)] or codici
        return codici

    def storici_di(pr, chiave):
        out = {}
        for cod, tipo in storia.nomi_storici.get(chiave, set()):
            att = storia.attuale(cod)
            if att and nel_territorio(pr, att):
                out.setdefault(att, (att, tipo, cod))
        st = list(out.values())
        if len(st) > 1:
            st = [x for x in st if compatibile(pr, x[0])] or st
        return st

    esiti = []
    for r in righe:
        chiave = (r["pr"], r["nome"])
        nome = CORREZIONI.get(chiave, r["nome"])
        e = dict(r, codice=None, modo=None, nota="", corretto=nome if nome != r["nome"] else "")
        esiti.append(e)
        if (r["pr"], r["nome"], r["gg"]) in ESCLUSE:
            e.update(modo="escluso", nota=ESCLUSE[(r["pr"], r["nome"], r["gg"])])
            continue
        if chiave in MANUALI:
            cod, motivo = MANUALI[chiave]
            e.update(codice=cod, modo="manuale", nota=motivo)
            continue
        cand = scegli(r["pr"], per_nome.get(norm(nome), [])) or \
            scegli(r["pr"], per_compatto.get(compatto(nome), []))
        if len(cand) == 1:
            e.update(codice=cand[0], modo="nome")
            continue
        if len(cand) > 1:
            e.update(modo="ambiguo", nota="omonimi: " + ", ".join(cand))
            continue
        st = storici_di(r["pr"], compatto(nome))
        if len(st) == 1:
            att, tipo, cod = st[0]
            e.update(codice=att, modo=tipo, codice_storico=cod)
        elif len(st) > 1:
            e.update(modo="ambiguo", nota="nomi storici: " + ", ".join(x[0] for x in st))

    # 2° giro sugli scarti: nome del DPR come inizio del nome attuale o storico
    # ("MONTAGNA" → "Montagna sulla Strada del Vino", "BASTIA" → "Bastia Umbra"), poi somiglianza.
    presi = {e["codice"] for e in esiti if e["codice"]}
    for e in esiti:
        if e["codice"] or e["modo"] in ("escluso", "ambiguo"):
            continue
        pr = e["pr"]
        n = norm(e["corretto"] or e["nome"])
        pref = [c for c, a in attuali.items() if c not in presi and nel_territorio(pr, c)
                and any(norm(x).startswith(n + " ") for x in a["nomi"])]
        pref = scegli(pr, pref)
        if len(pref) == 1:
            e.update(codice=pref[0], modo="nome ampliato",
                     nota=f"nel DPR come {e['nome']}, oggi {attuali[pref[0]]['nome']}")
            presi.add(pref[0])
            continue
        pref_st = [k for k in storia.nomi_storici if k.startswith(compatto(n))]
        st = [x for k in pref_st for x in storici_di(pr, k)]
        st = list({x[0]: x for x in st}.values())
        if len(st) == 1:
            e.update(codice=st[0][0], modo=st[0][1], codice_storico=st[0][2],
                     nota=f"nome storico che inizia con {e['nome']}")
            continue
        liberi = {norm(x): c for c, a in attuali.items() if c not in presi and nel_territorio(pr, c)
                  for x in a["nomi"]}
        m = difflib.get_close_matches(n, list(liberi), n=1, cutoff=0.84)
        if m:
            c = liberi[m[0]]
            e.update(codice=c, modo="somiglianza", nota=f"nome simile: {attuali[c]['nome']}")
            presi.add(c)
            continue
        m = difflib.get_close_matches(compatto(n), list(storia.nomi_storici), n=3, cutoff=0.88)
        st = list({x[0]: x for k in m for x in storici_di(pr, k)}.values())
        if len(st) == 1:
            e.update(codice=st[0][0], modo=st[0][1], codice_storico=st[0][2],
                     nota=f"nome storico simile ({m[0]})")
    return esiti


MODIFICHE: dict[tuple, dict] = {}     # (pr, nome, zona, gg, alt) della riga vigente → storia delle modifiche


def data_it(iso: str) -> str:
    a, m, g = iso.split("-")
    return f"{g}/{m}/{a}"


def leggi_modifiche(path: Path | None) -> None:
    if not path or not path.exists():
        return
    for x in json.loads(path.read_text(encoding="utf-8")):
        if x["nuova"]:
            pr, nome, z, gg, alt = x["nuova"]
            MODIFICHE[(pr, nome, z.replace("0", "O"), int(gg.replace("O", "0")), int(alt.replace("O", "0")))] = x


def nota_modifica(r: dict) -> str:
    """Nota per una riga vigente modificata dopo il 1993 (atto, entrata in vigore, valore del 1993)."""
    x = MODIFICHE.get((r["pr"], r["nome"], r["zona"], r["gg"], r["alt"]))
    if not x:
        return "riga modificata dopo il 1993" if r.get("modificato") else ""
    def atto(p):
        nomi = list(dict.fromkeys(re.sub(r"\s*\(in G\.U\..*\)$", "", a) for a in p["atti"]))
        num = re.search(r"n\.\s*(\d+)\)", p["atti"][0])
        gu = f"G.U. n. {num.group(1)} del {data_it(p['gu'])}" if num else f"G.U. del {data_it(p['gu'])}"
        if len(p["atti"]) > 1:   # più decreti nella stessa G.U.: Normattiva non dice quale ha cambiato la riga
            chi = (f"uno dei {len(p['atti'])} D.M. del {nomi[0][5:]}" if len(nomi) == 1 else
                   "uno dei D.M. " + ", ".join(n[5:] for n in nomi[:-1]) + " e " + nomi[-1][5:])
        else:
            chi = nomi[0]
        return f"{chi} ({gu}, in vigore dal {data_it(p['in_vigore_dal'])})"
    passi = x["passi"]
    if x["vecchia"] is None:
        return "riga aggiunta all'Allegato A con " + atto(passi[-1])
    v = x["vecchia"]
    parti = []
    for i, p in enumerate(passi):
        if p.get("valore") is None and i < len(passi) - 1:
            parti.append(atto(p) + " (riga tolta, poi reinserita)")
        elif i < len(passi) - 1:
            val = p["valore"]
            parti.append(atto(p) + f" ({val[3]} GG, zona {val[2]}, {val[4]} m)")
        else:
            parti.append(atto(p))
    n = x["nuova"]
    if len(passi) == 1 and list(v[2:]) == list(n[2:]):   # cambia solo il nome (correzione o nuova denominazione)
        return f"nome cambiato con {parti[0]}; nel testo originario del 1993: {v[1]} {v[0]}"
    testo = "valori modificati con " + " e poi con ".join(parti)
    return testo + f"; nel testo originario del 1993: {v[1]} {v[0]}, {v[3]} GG, zona {v[2]}, {v[4]} m"


def componi(esiti, attuali, storia: Storia):
    """Raggruppa per codice attuale e decide il valore: diretto, fusione, incorporazione."""
    per_codice = defaultdict(list)
    for e in esiti:
        if e["codice"]:
            per_codice[e["codice"]].append(e)
    dati = {}
    for cod, lst in per_codice.items():
        nome_att = norm(attuali[cod]["nome"])
        propri = [e for e in lst if e["modo"] in ("nome", "manuale", "somiglianza", "nome precedente",
                                                   "nome ampliato")]
        altri = [e for e in lst if e not in propri]
        if len(propri) == 1 and (cod not in storia.nuovi or len(lst) == 1):
            p = propri[0]
            nota = []
            if p["modo"] == "nome precedente":
                nota.append(f"nel DPR come {p['nome']} (cambio di nome)")
            elif p["modo"] in ("somiglianza", "nome ampliato") or p["corretto"]:
                nota.append(f"nel DPR come {p['nome']}")
            elif p["modo"] == "manuale":
                nota.append(p["nota"])
            if attuali[cod]["regione"] != REGIONE_SIGLA_1993.get(p["pr"]):
                nota.append(f"nel DPR in provincia di {p['pr']}, poi passato ad altra regione")
            if nota_modifica(p):
                nota.append(nota_modifica(p))
            if altri:
                nota.append("ha incorporato " + ", ".join(f"{leggibile(a['nome'])} ({a['gg']} GG, zona {a['zona']})"
                                                          for a in altri))
            dati[cod] = dict(gg=p["gg"], zona=p["zona"], alt=p["alt"], nome=p["nome"],
                             nota="; ".join(nota), tipo="incorporazione" if altri else "diretto",
                             origini=[dict(nome=a["nome"], gg=a["gg"], zona=a["zona"], alt=a["alt"])
                                      for a in altri])
        else:
            tutte = propri + altri
            zone = sorted({a["zona"] for a in tutte})
            dati[cod] = dict(gg=None, zona=zone[0] if len(zone) == 1 else None, alt=None,
                             nome=" + ".join(a["nome"] for a in tutte),
                             nota=("fusione di " + ", ".join(leggibile(a["nome"]) for a in tutte) +
                                   ": il DPR non ha un valore unico per il nuovo comune" +
                                   "".join(f"; {leggibile(a['nome'])}: {nota_modifica(a)}" for a in tutte
                                           if nota_modifica(a))),
                             tipo="fusione",
                             origini=[dict(nome=a["nome"], gg=a["gg"], zona=a["zona"], alt=a["alt"])
                                      for a in tutte])
    return dati


# ---------------------------------------------------------------- scrittura

# licenza (eugenio.statocritico.it/licenza.html#dati): i valori sono un atto pubblico; la raccolta e l'abbinamento
# ai codici ISTAT sono elaborazioni di EuGEnio con licenza CC BY 4.0, da citare come fonte
CITAZIONE = "Fonte: EuGEnio – eugenio.statocritico.it"
LICENZA = ("Valori dell'Allegato A: atto normativo, non coperto da diritto d'autore (art. 5 L. 633/1941). "
           "Raccolta e abbinamento ai codici ISTAT: EuGEnio, licenza CC BY 4.0 "
           "(https://creativecommons.org/licenses/by/4.0/deed.it); si possono riutilizzare, anche modificati, "
           "citando EuGEnio come fonte e mantenendo l'attribuzione a ISTAT (CC BY 4.0). "
           "Dettagli: https://eugenio.statocritico.it/licenza.html#dati")


def citazione(oggi: dt.date | None = None) -> str:
    return f"{CITAZIONE} (elenco del DPR 412/93 aggiornato il {(oggi or dt.date.today()):%d/%m/%Y})"


def scrivi(dati, attuali, storia, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    mancanti = {c: a for c, a in attuali.items() if c not in dati}
    compatto_ = {}
    for cod in sorted(attuali):
        if cod in dati:
            d = dati[cod]
            # il nome del DPR si ripete solo se diverso dal nome attuale (file più leggero)
            nome = "" if norm(d["nome"]) == norm(attuali[cod]["nome"]) else d["nome"]
            v = [d["gg"], d["zona"], d["alt"], nome, d["nota"]]
            if d["origini"]:
                v.append([[o["gg"], o["zona"], o["alt"], o["nome"]] for o in d["origini"]])
        else:
            origine = storia.nati_dopo.get(cod)
            nota = "non presente nel DPR"
            if origine:
                nota += " (comune istituito dopo il 1993 da " + ", ".join(sorted(set(map(str, origine)))) + ")"
            v = [None, None, None, "", nota]
        compatto_[cod] = v
    doc = {
        "fonte": FONTE,
        "url": URL_NORMATTIVA,
        "campi": ["gg", "zona", "alt", "nome_dpr (vuoto se uguale al nome attuale)", "nota",
                  "origini[gg,zona,alt,nome] (fusioni e incorporazioni)"],
        "licenza": LICENZA,
        "citazione": citazione(),
        "comuni": compatto_,
    }
    (out / "dpr412.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")),
                                     encoding="utf-8")
    with open(out / "dpr412.csv", "w", newline="", encoding="utf-8") as f:
        f.write(f"# Fonte: {FONTE}. {URL_NORMATTIVA}\n")
        w = csv.writer(f, delimiter=";")
        w.writerow(["codice_istat", "comune", "provincia", "gradi_giorno", "zona", "altitudine_m",
                    "nome_nel_dpr", "tipo", "nota"])
        for cod in sorted(attuali):
            a = attuali[cod]
            if cod not in dati:
                w.writerow([cod, a["nome"], a["sigla"], "", "", "", "", "assente", compatto_[cod][4]])
                continue
            d = dati[cod]
            if d["tipo"] == "fusione":
                for o in d["origini"]:
                    w.writerow([cod, a["nome"], a["sigla"], o["gg"], o["zona"], o["alt"], o["nome"],
                                "fusione", d["nota"]])
            else:
                w.writerow([cod, a["nome"], a["sigla"], d["gg"], d["zona"], d["alt"], d["nome"],
                            d["tipo"], d["nota"]])
        # licenza e formula di citazione in fondo, come nei file scaricati dal server (righe "#")
        f.write(f"# Licenza: {LICENZA}\r\n# Come citare: {citazione()}\r\n")
    return mancanti


def rapporto(esiti, dati, attuali, mancanti, storia, path: Path, borruso: Path | None):
    n = len(esiti)
    ok = [e for e in esiti if e["codice"]]
    da = defaultdict(int)
    for e in esiti:
        da[e["modo"] or "non abbinato"] += 1
    L = ["# Abbinamento DPR 412/93 → codici ISTAT attuali", "",
         f"Righe dell'Allegato A lette: {n}. Abbinate a un comune attuale: {len(ok)} "
         f"({100 * len(ok) / n:.2f} %).", "",
         f"Comuni attuali: {len(attuali)}; con un valore del DPR: "
         f"{sum(1 for d in dati.values() if d['tipo'] != 'fusione')}; fusioni (più valori d'origine): "
         f"{sum(1 for d in dati.values() if d['tipo'] == 'fusione')}; senza valore: {len(mancanti)} "
         f"(copertura {100 * len(dati) / len(attuali):.2f} %).", "",
         "## Scelte", "",
         "- Fonte: testo vigente dell'Allegato A su Normattiva, esportato in Akoma Ntoso "
         "(file 19931014_093G0451_VIGENZA_20220429.xml). Il testo vigente contiene già tutte le modifiche "
         "successive al 1993 (58 decreti dal 1994 al 2016, verificati sul testo multivigente: vedi la sezione "
         "«Modifiche all'Allegato A»); solo l'ultima (Casalattico, 2016) è segnata tra doppie parentesi (( )).",
         "- Il testo usa spesso la lettera O al posto dello zero nei numeri (es. 'CB E 2346 7O1 "
         "CAMPOBASSO'): nei campi numerici la O è letta come 0; 'MR' (Irsina) è letto come MT.",
         "- Abbinamento per nome normalizzato (senza accenti, apostrofi e trattini, J = I) dentro la "
         "regione del 1993, con le province nate dopo (BI, VB, LC, LO, MB, RN, PO, KR, VV, FM, BT, "
         "province sarde) e i passaggi di regione (Valmarecchia → RN nel 2009 e 2021, Sappada → UD nel 2017).",
         "- Se il nome non c'è tra i comuni attuali si cercano i nomi storici ISTAT dal 1991 (cambi di "
         "nome, comuni soppressi) e si risale al codice attuale seguendo cambi di provincia e fusioni.",
         "- Per gli scarti: nome del DPR come inizio del nome attuale (es. VENARIA → Venaria Reale), poi "
         "somiglianza dei nomi tra i soli comuni ancora liberi (soglia 0,84). Tutti i casi sono elencati "
         "sotto e sono stati controllati a mano.",
         "- Comune che ne ha incorporati altri (stesso codice ISTAT): resta il valore del DPR del comune "
         "che incorpora; i valori dei comuni incorporati sono riportati in nota.",
         "- Comune nuovo nato da fusione (nuovo codice ISTAT): il DPR non ha un valore unico; si riportano "
         "i valori dei comuni d'origine ('fusione'); la zona si indica solo se uguale per tutti.",
         "- Comuni istituiti dopo il 1993 per distacco da altri: non sono nel DPR; per l'art. 2 c. 3 il "
         "Sindaco adotta i gradi giorno del comune più vicino corretti per la quota. Restano senza valore.",
         "- Doppione FERENTINO: si tiene la riga da 2222 GG (vedi righe escluse). Le due righe (2222 GG a 581 m e "
         "2587 GG a 801 m) sono state scritte dai D.M. 24 e 30 ottobre 2008 al posto di quella del 1993 (1913 GG, "
         "zona D, 395 m): Normattiva non dice quale decreto ha scritto quale riga; le quote non sono quella della "
         "casa comunale (395 m), forse sono parti del territorio. Da verificare sul testo dei decreti in G.U.",
         "- ISOLA DI BARI (BA, C, 1187 GG, 5 m) è Mola di Bari: la segnalazione di abbinarla a Conversano "
         "(27/10/2026) non è applicata perché Conversano ha già una sua riga (D, 1642 GG, 219 m) e ne avrebbe due, "
         "mentre Mola di Bari resterebbe senza valore; la riga sta in ordine alfabetico tra MODUGNO e MOLFETTA "
         "(cioè al posto di MOLA DI BARI) e 5 m è la quota di Mola, sul mare. Le raccolte correnti danno a Mola "
         "di Bari C 1187 e a Conversano D 1642. Da rivedere solo se c'è una fonte che dica il contrario.",
         "",
         "## Modo di abbinamento", ""]
    L += [f"- {k}: {v}" for k, v in sorted(da.items(), key=lambda x: -x[1])]
    L += ["", "## Righe del DPR non abbinate o escluse", ""]
    L += [f"- {e['pr']} {e['nome']} ({e['gg']} GG, {e['zona']}, {e['alt']} m) — {e['modo'] or ''} {e['nota']}"
          for e in esiti if not e["codice"]] or ["- nessuna"]
    L += ["", "## Abbinamenti per somiglianza o manuali (da controllare)", ""]
    L += [f"- {e['pr']} {e['nome']} → {e['codice']} {attuali[e['codice']]['nome']} ({e['modo']}: {e['nota']})"
          for e in esiti if e["modo"] in ("somiglianza", "manuale")] or ["- nessuno"]
    def zona_da_gg(g):
        return "A" if g <= 600 else "B" if g <= 900 else "C" if g <= 1400 else "D" if g <= 2100 else \
            "E" if g <= 3000 else "F"
    L += ["", "## Zona non coerente con i gradi giorno nel testo del DPR (lasciata com'è)", ""]
    L += [f"- {e['pr']} {e['nome']}: {e['gg']} GG, zona {e['zona']} (dai GG sarebbe {zona_da_gg(e['gg'])})"
          for e in esiti if zona_da_gg(e["gg"]) != e["zona"]] or ["- nessuna"]
    L += ["", "## Correzioni di refusi applicate", ""]
    L += [f"- {k[0]} {k[1]} → {v}" for k, v in CORREZIONI.items()]
    L += ["", "## Cambi di nome", ""]
    L += [f"- {e['pr']} {e['nome']} → {attuali[e['codice']]['nome']} ({e['codice']})"
          for e in esiti if e["modo"] == "nome precedente"]
    L += ["", "## Fusioni (nuovo comune: il DPR non ha un valore unico)", ""]
    L += [f"- {c} {attuali[c]['nome']}: " + ", ".join(f"{o['nome']} {o['gg']} GG {o['zona']}" for o in d["origini"])
          for c, d in sorted(dati.items()) if d["tipo"] == "fusione"]
    L += ["", "## Incorporazioni (resta il valore del comune che incorpora)", ""]
    L += [f"- {c} {attuali[c]['nome']} ({d['gg']} GG {d['zona']}): {d['nota']}"
          for c, d in sorted(dati.items()) if d["tipo"] == "incorporazione"]
    if MODIFICHE:
        per_atto = defaultdict(list)
        for x in MODIFICHE.values():
            for pz in x["passi"]:
                per_atto[(pz["in_vigore_dal"], " e ".join(pz["atti"]), pz["gu"])].append(
                    dict(vecchia=x["vecchia"], nuova=pz.get("valore") or x["nuova"]))
        L += ["", "## Modifiche all'Allegato A dopo il 1993 (testo multivigente di Normattiva)", "",
              f"Righe vigenti modificate o aggiunte: {len(MODIFICHE)}; versioni dell'Allegato A con modifiche: "
              f"{len(per_atto)}. Per ogni atto: data della G.U., entrata in vigore della versione, righe "
              "(valore del 1993 → valore vigente). Nei dati la nota del comune riporta atto, data e valore del 1993.", ""]
        for (vig, atto, gu), lst in sorted(per_atto.items()):
            L.append(f"- **{atto}** (G.U. {data_it(gu)}, in vigore dal {data_it(vig)}): " + "; ".join(
                (f"{x['vecchia'][0]} {x['vecchia'][1]} {x['vecchia'][3]} {x['vecchia'][2]} {x['vecchia'][4]} m → "
                 if x["vecchia"] else "aggiunta ") + f"{x['nuova'][1]} {x['nuova'][3]} {x['nuova'][2]} {x['nuova'][4]} m"
                for x in lst))
        L += ["", "Come è stato fatto: la vista «multivigente» di Normattiva dà 46 versioni dell'Allegato A (originale "
              "del 1993 e 45 aggiornamenti, ognuna con la data «in vigore dal»); confrontando l'originale con la "
              "versione vigente si trovano le righe cambiate, e per ognuna si cerca con una ricerca binaria la versione "
              "che l'ha introdotta (script/bisezione.py e script/storia_modifiche.py, 183 pagine scaricate in più sessioni con pause di 7-90 secondi). "
              "Ogni versione è attribuita all'atto pubblicato in G.U. 15 giorni prima della sua entrata in vigore; "
              "quando nella stessa G.U. ci sono più decreti, la nota li cita tutti. Atti modificativi in elenco: 55 "
              "«modifica dell'Allegato A» più il D.M. 12 ottobre 2000 e il D.M. 7 aprile 2005 («Tabella A») e il D.M. 16 "
              "gennaio 2007 (indicato da Normattiva come modifica dell'«Allegato I», ma è la versione dell'Allegato A in "
              "vigore dal 21/02/2007). Esito: i valori pubblicati sono già quelli vigenti (nessun numero cambia "
              "rispetto all'abbinamento precedente); cambiano solo le note."]
    L += ["", "## Documento ENEA RdS 2012/106 (iris.enea.it, handle 20.500.12079/6599)", "",
          "Antonacci, Baggio, Corrado, Murano, Riva, «Aggiornamento parametri climatici nazionali e zonizzazione del "
          "clima nazionale ai fini della certificazione estiva», Report Ricerca di Sistema Elettrico RdS 2012/106, ENEA, "
          "settembre 2012, 317 pagine, accesso aperto con licenza CC BY-NC-SA 3.0 IT. Contiene: gli anni tipo CTI per "
          "la Sardegna e l'omogeneizzazione di quelli delle altre province; medie mensili (temperatura, irradiazione, "
          "pressione del vapore, vento) delle stazioni e dei capoluoghi, confrontate con la UNI 10349:1994 (Allegato "
          "A, quadri per provincia); gradi giorno invernali ed estivi per comune calcolati dagli anni tipo con "
          "temperature base 12-18 °C (UNI EN ISO 15927-6), mostrati SOLO come mappe; una tabella di gradi giorno a "
          "base 18 °C per i capoluoghi; il metodo della UNI 10349 per le località senza anno tipo (stazione più "
          "vicina sullo stesso versante, gradiente per zona). NON contiene aggiornamenti della tabella A del DPR "
          "412/93, né gradi giorno a 20 °C per comune in forma di tabella, né valori per i comuni istituiti dopo il "
          "1993: non c'è nulla da integrare nei dati del DPR (e la licenza NC non sarebbe compatibile con CC BY)."]
    L += ["", "## Comuni attuali senza valore nel DPR", ""]
    L += [f"- {c} {a['nome']} ({a['sigla']}): " +
          ("istituito dopo il 1993 da " + ", ".join(sorted(set(map(str, storia.nati_dopo[c]))))
           if c in storia.nati_dopo else "da verificare")
          for c, a in sorted(mancanti.items())] or ["- nessuno"]
    if borruso and borruso.exists():
        b = list(csv.DictReader(open(borruso, encoding="utf-8", errors="replace")))
        bk = {(x["pr"], x["comune"]) for x in b}
        nk = {(e["pr"], e["nome"]) for e in esiti}
        dd = {(e["pr"], e["nome"]): e for e in esiti}
        diff = [(k, x["gr-g"], dd[k]["gg"]) for x in b for k in [(x["pr"], x["comune"])]
                if k in dd and x["gr-g"].isdigit() and int(x["gr-g"]) != dd[k]["gg"]]
        L += ["", "## Controllo con il CSV di Andrea Borruso (zone.csv)", "",
              f"Righe nel CSV: {len(b)}; righe nel testo Normattiva: {len(esiti)}.",
              f"Righe Normattiva assenti nel CSV: {len(nk - bk)} "
              "(quasi tutte quelle con la lettera O al posto dello zero nei numeri, scartate nel CSV): " +
              ", ".join(f"{p} {nm}" for p, nm in sorted(nk - bk)) + ".",
              f"Righe del CSV assenti in Normattiva: {len(bk - nk)}: " +
              ", ".join(f"{p} {nm}" for p, nm in sorted(bk - nk)) + ".",
              f"Gradi giorno diversi a parità di nome: {len(diff)}: " +
              ", ".join(f"{k[0]} {k[1]} CSV {a} / DPR {c}" for k, a, c in diff) + "."]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--akn", type=Path, required=True)
    ap.add_argument("--istat", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--borruso", type=Path)
    ap.add_argument("--rapporto", type=Path, default=Path("abbinamento_dpr412.md"))
    ap.add_argument("--modifiche", type=Path,
                    default=Path(__file__).resolve().parent / "normattiva/multivigenza/modifiche_allegato_a.json")
    a = ap.parse_args()
    leggi_modifiche(a.modifiche)
    righe = leggi_dpr(a.akn)
    attuali, soppressi, variazioni = leggi_istat(a.istat)
    storia = Storia(attuali, soppressi, variazioni)
    esiti = abbina(righe, attuali, storia)
    dati = componi(esiti, attuali, storia)
    mancanti = scrivi(dati, attuali, storia, a.out)
    rapporto(esiti, dati, attuali, mancanti, storia, a.rapporto, a.borruso)
    ok = sum(1 for e in esiti if e["codice"])
    print(f"righe DPR {len(righe)}, abbinate {ok} ({100 * ok / len(righe):.2f} %), "
          f"comuni attuali coperti {len(dati)}/{len(attuali)}, senza valore {len(mancanti)}")


if __name__ == "__main__":
    main()
