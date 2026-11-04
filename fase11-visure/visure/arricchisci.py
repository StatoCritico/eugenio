"""Abbinamento delle unità delle visure agli edifici di Patrimonio e colonne aggiunte per edificio.

La stessa logica è nel sito, in fase5-sito/sito/visure_abbina.js (un test confronta i due risultati su un caso comune).

Chiave di un edificio, nell'ordine:
  1. «forte»: codice catastale del comune (Belfiore) + foglio + mappale trovati dalla geolocalizzazione di Patrimonio
     (colonne belfiore, foglio_catasto, mappale);
  2. «dichiarata»: comune (nome o codice Belfiore), sezione, foglio e particella scritti nel file dell'utente.
Un'unità va con l'edificio se foglio e particella coincidono (senza zeri iniziali), il comune coincide (codice se ci
sono tutti e due, altrimenti nome senza accenti né apostrofi) e la sezione non è diversa. Esito «ok» se il comune
coincide per codice e la sezione è certa, altrimenti «verificare»; «nessuna_visura» se nessuna unità coincide.

Colonne aggiunte (prefisso visura_, così non si confondono con i valori scritti dall'utente, che hanno la precedenza):
unità e subalterni, categorie, uso prevalente, piani (elenco, fuori terra, interrati, più alto), superficie catastale
(somma delle unità A, B, C), consistenza in m³ (somma delle unità B), rendita, superficie dei terreni, data, indirizzo,
esito e nota. Nessun dato personale.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

from . import piani as P

BELFIORE = re.compile(r"^[A-Z]\d{3}$")
PERTINENZE = {"C/2", "C/6", "C/7"}

# categorie catastali (quadro generale delle categorie, DPR 1142/1949 e successive) → descrizione breve e uso per le
# stime dei piani di fase 10 (edifici_calcoli.js, usoDa)
CATEGORIE = {
    "A/1": ("abitazione signorile", "residenziale"), "A/2": ("abitazione civile", "residenziale"),
    "A/3": ("abitazione economica", "residenziale"), "A/4": ("abitazione popolare", "residenziale"),
    "A/5": ("abitazione ultrapopolare", "residenziale"), "A/6": ("abitazione rurale", "residenziale"),
    "A/7": ("villino", "residenziale"), "A/8": ("villa", "residenziale"), "A/9": ("castello o palazzo storico", "residenziale"),
    "A/10": ("uffici e studi privati", "uffici"), "A/11": ("abitazione tipica dei luoghi", "residenziale"),
    "B/1": ("collegi, convitti, caserme", "altro"), "B/2": ("case di cura e ospedali senza fine di lucro", "ospedale"),
    "B/3": ("prigioni e riformatori", "altro"), "B/4": ("uffici pubblici", "uffici"),
    "B/5": ("scuole e laboratori scientifici", "scuola"), "B/6": ("biblioteche, musei, accademie", "altro"),
    "B/7": ("cappelle e oratori", "altro"), "B/8": ("magazzini sotterranei", "capannone"),
    "C/1": ("negozi e botteghe", "commerciale"), "C/2": ("magazzini e depositi", "capannone"),
    "C/3": ("laboratori per arti e mestieri", "capannone"), "C/4": ("fabbricati per esercizi sportivi", "palestra"),
    "C/5": ("stabilimenti balneari", "altro"), "C/6": ("stalle, scuderie, rimesse, autorimesse", "altro"),
    "C/7": ("tettoie", "altro"),
    "D/1": ("opifici", "capannone"), "D/2": ("alberghi e pensioni", "altro"), "D/3": ("teatri, cinema, sale", "altro"),
    "D/4": ("case di cura e ospedali con fine di lucro", "ospedale"), "D/5": ("istituti di credito", "uffici"),
    "D/6": ("fabbricati per attività sportive", "palestra"), "D/7": ("fabbricati industriali", "capannone"),
    "D/8": ("fabbricati commerciali", "commerciale"), "D/9": ("edifici galleggianti", "altro"),
    "D/10": ("fabbricati per funzioni produttive agricole", "capannone"),
    "E/1": ("stazioni per servizi di trasporto", "altro"), "E/3": ("costruzioni per speciali esigenze pubbliche", "altro"),
    "E/9": ("altri immobili a destinazione particolare", "altro"),
    "F/1": ("area urbana", "altro"), "F/2": ("unità collabente", "altro"), "F/3": ("in corso di costruzione", "altro"),
    "F/4": ("in corso di definizione", "altro"), "F/5": ("lastrico solare", "altro"),
    "F/6": ("in attesa di dichiarazione", "altro"),
}

COLONNE_EDIFICIO = [
    "visura_unita", "visura_subalterni", "visura_categorie", "visura_uso_prevalente", "visura_uso",
    "visura_piani", "visura_piani_fuori_terra", "visura_piani_interrati", "visura_piano_piu_alto",
    "visura_superficie_catastale", "visura_consistenza_m3", "visura_rendita_euro", "visura_terreni_m2",
    "visura_data", "visura_indirizzo", "visura_esito", "visura_nota",
]


def norma_comune(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").upper()
    s = re.sub(r"^\s*COMUNE\s+DI\s+", "", s)
    return re.sub(r"[^A-Z0-9]+", " ", s.replace("'", "").replace("’", "")).strip()


def norma_num(s) -> str:
    t = re.sub(r"\s+", "", str(s if s is not None else "")).upper()
    if t.endswith(".0") and t[:-2].isdigit():      # 120.0 letto come numero da un foglio di calcolo
        t = t[:-2]
    t = re.sub(r"^0+(?=[0-9A-Z])", "", t)
    return t


def _val(r: dict, *nomi):
    for n in nomi:
        v = r.get(n)
        if v not in (None, "") and str(v).strip().lower() not in ("nan", "none", "null"):
            return str(v).strip()
    return ""


def chiavi_edificio(r: dict) -> list[dict]:
    out = []
    b, f, p = _val(r, "belfiore"), _val(r, "foglio_catasto"), _val(r, "mappale")
    if b and f and p:
        out.append({"tipo": "forte", "belfiore": b.upper(), "nome": norma_comune(_val(r, "comune_catasto")),
                    "sezione": norma_num(_val(r, "sezione")), "foglio": norma_num(f), "particella": norma_num(p)})
    c, f, p = _val(r, "comune"), _val(r, "foglio"), _val(r, "particella", "mappale")
    if c and f and p:
        cu = c.strip().upper()
        out.append({"tipo": "dichiarata", "belfiore": cu if BELFIORE.match(cu) else "",
                    "nome": "" if BELFIORE.match(cu) else norma_comune(c), "sezione": norma_num(_val(r, "sezione")),
                    "foglio": norma_num(f), "particella": norma_num(p)})
    return out


def coincide(k: dict, u: dict) -> str | None:
    """None se non coincide, altrimenti «ok» o «verificare»."""
    if norma_num(u.get("particella")) != k["particella"] or norma_num(u.get("foglio")) != k["foglio"]:
        return None
    ub, un = str(u.get("codice_comune") or "").upper(), norma_comune(u.get("comune"))
    if k["belfiore"] and ub:
        if k["belfiore"] != ub:
            return None
        per_codice = True
    elif k["nome"] and un:
        if k["nome"] != un:
            return None
        per_codice = False
    else:
        return None
    us = norma_num(u.get("sezione"))
    if k["sezione"] and us and k["sezione"] != us:
        return None
    certa = (k["sezione"] == us)
    return "ok" if per_codice and certa else "verificare"


def _data_iso(d: str) -> str:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""


def _somma(xs) -> float | None:
    v = [float(x) for x in xs if x not in (None, "")]
    if not v:
        return None
    s = sum(v)
    return int(s) if s.is_integer() else round(s, 2)


def riassunto(unita: list[dict]) -> dict:
    """Colonne aggiunte per un edificio a partire dalle sue unità."""
    fab = [u for u in unita if u.get("catasto") == "F"]
    ter = [u for u in unita if u.get("catasto") == "T"]
    cat = Counter(u.get("categoria") for u in fab if u.get("categoria"))
    # uso prevalente: categoria con la superficie (o il volume, o il numero di unità) più grande; le pertinenze
    # (C/2, C/6, C/7) contano solo se non c'è altro
    peso: Counter = Counter()
    principali = [c for c in cat if c not in PERTINENZE]
    for u in fab:
        c = u.get("categoria")
        if not c or (principali and c in PERTINENZE):
            continue
        w = u.get("superficie_catastale") or (float(u["consistenza"]) / 3.0 if u.get("unita_consistenza") == "m³" and u.get("consistenza") else None) or 1
        peso[c] += float(w)
    prev = sorted(peso.items(), key=lambda x: (-x[1], x[0]))[0][0] if peso else None
    liv: set[int] = set()
    altri: list[str] = []
    for u in fab:
        l, a = P.livelli(u.get("piano"))
        liv.update(l)
        altri += [x for x in a if x not in altri]
    pp = P.riassumi(sorted(liv), altri)
    date = sorted((_data_iso(u.get("data_visura") or ""), u.get("data_visura")) for u in unita if u.get("data_visura"))
    ind = Counter(u.get("indirizzo") for u in fab if u.get("indirizzo"))
    sup = _somma(u.get("superficie_catastale") for u in fab if (u.get("categoria") or "")[:1] in ("A", "B", "C"))
    vol = _somma(u.get("consistenza") for u in fab if (u.get("categoria") or "").startswith("B") and u.get("unita_consistenza") == "m³")
    parziali = sum(1 for u in unita if u.get("esito") == "parziale")
    return {
        "visura_unita": len(unita),
        "visura_subalterni": len(fab),
        "visura_categorie": "; ".join(f"{c} ×{n}" if n > 1 else c for c, n in sorted(cat.items(), key=lambda x: (-x[1], x[0]))),
        "visura_uso_prevalente": f"{prev} {CATEGORIE.get(prev, ('', ''))[0]}".strip() if prev else "",
        "visura_uso": CATEGORIE.get(prev, ("", "altro"))[1] if prev else "",
        "visura_piani": pp["piani"],
        "visura_piani_fuori_terra": pp["piani_fuori_terra"],
        "visura_piani_interrati": pp["piani_interrati"],
        "visura_piano_piu_alto": pp["piano_piu_alto"],
        "visura_superficie_catastale": sup,
        "visura_consistenza_m3": vol,
        "visura_rendita_euro": _somma(u.get("rendita_euro") for u in fab),
        "visura_terreni_m2": _somma(u.get("superficie_m2") for u in ter),
        "visura_data": date[-1][1] if date else "",
        "visura_indirizzo": ind.most_common(1)[0][0] if ind else "",
        "visura_nota": f"{parziali} unità lette in parte" if parziali else "",
    }


def abbina(edifici: list[dict], unita: list[dict]) -> tuple[list[dict], list[dict]]:
    """(edifici con le colonne visura_…, unità non abbinate a nessun edificio)."""
    usate: set[int] = set()
    out, gruppi = [], []
    for r in edifici:
        trovate: list[int] = []
        esito = None
        for k in chiavi_edificio(r):
            es = [(i, coincide(k, u)) for i, u in enumerate(unita)]
            es = [(i, e) for i, e in es if e]
            if es:
                trovate = [i for i, _ in es]
                esito = "ok" if all(e == "ok" for _, e in es) else "verificare"
                break
        riga = dict(r)
        if trovate:
            usate.update(trovate)
            riga.update(riassunto([unita[i] for i in trovate]))
            riga["visura_esito"] = esito
        else:
            riga.update({c: "" for c in COLONNE_EDIFICIO})
            riga["visura_esito"] = "nessuna_visura"
            riga["visura_nota"] = ("nessuna visura per questa particella" if chiavi_edificio(r)
                                   else "mancano comune, foglio o particella")
        out.append(riga)
        gruppi.append(tuple(trovate))
    # la stessa particella in più righe del patrimonio prende le stesse unità: si segnala
    quante = Counter(g for g in gruppi if g)
    for r, g in zip(out, gruppi):
        if g and quante[g] > 1:
            r["visura_nota"] = ((r["visura_nota"] + "; ") if r["visura_nota"] else "") + "stessa particella in più righe"
    return out, [u for i, u in enumerate(unita) if i not in usate]


def edifici_da_unita(unita: list[dict]) -> list[dict]:
    """Un edificio per particella (comune, sezione, foglio, particella), senza file di Patrimonio."""
    gruppi: dict[tuple, list[dict]] = {}
    for u in unita:
        k = (str(u.get("codice_comune") or "").upper() or norma_comune(u.get("comune")), norma_num(u.get("sezione")),
             norma_num(u.get("foglio")), norma_num(u.get("particella")))
        gruppi.setdefault(k, []).append(u)
    out = []
    for (cod, sez, fog, par), uu in gruppi.items():
        r = {"id": f"V{len(out) + 1}", "comune": uu[0].get("comune") or "", "codice_comune": cod if BELFIORE.match(cod) else "",
             "sezione": sez, "foglio": fog, "particella": par}
        r.update(riassunto(uu))
        r["visura_esito"] = "ok"
        r["indirizzo"] = r["visura_indirizzo"]
        out.append(r)
    return out
