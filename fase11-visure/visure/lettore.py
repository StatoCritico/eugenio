"""Lettura delle visure catastali in PDF (per immobile e per soggetto, fabbricati e terreni).

Due formati, anche mescolati nello stesso documento:
  «etichette»  formato attuale: un blocco per unità («Immobile n. 1») con campi scritti come «Foglio 120 Particella 45
               Subalterno 3», «Categoria A/2, Classe 3, Consistenza 5,5 vani», «Indirizzo: … Piano 2»;
  «tabella»    formato a colonne: riga dei titoli (Sezione, Foglio, Particella, Sub, Zona, Micro, Categoria, Classe,
               Consistenza, Superficie, Rendita…) e una riga per unità; ogni cella va alla colonna con il titolo più
               vicino (il testo del PDF si estrae con le posizioni, modalità «layout» di pypdf).
Tutte le espressioni regolari stanno in regole.toml.

Dati personali: le righe con intestatari, codici fiscali, date e luoghi di nascita, diritti e quote si tolgono dal
testo **prima** di cercare i dati dell'immobile, quindi non possono finire nei campi delle unità. Si leggono a parte
solo con `includi_intestatari=True` (opzione esplicita), e restano comunque fuori dal CSV delle unità.

Nessun accesso alla rete: il lettore lavora solo sui file che riceve.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from . import piani as P
from .regole import Regole, carica

CATEGORIA = re.compile(r"\b([A-F])\s?/\s?0?([0-9]{1,2})\b")
NUMERO_N = re.compile(r"^\s*(\d{1,3})\s")
FT = r"(?:S\d|S|PT|T|R|\d{1,2}°?|terra|rialzato|seminterrato|interrato|ammezzato|sottotetto|mansarda)"
STOP_TABELLA = re.compile(r"^\s*(?:totale\s*:?\s*(?:vani|rendita|euro|m²|mq|\d)|immobile\s+\d+\s*:|"
                          r"unit[aà]\s+immobiliari\s+site|mappali\s+|rilasciata\s+da|visura\s+telematica|"
                          r"situazione\s+degli\s+atti|dati\s+della\s+richiesta|annotazion)", re.I)
FINE_PERSONALI = re.compile(r"^\s*(?:\d{1,2}\.\s*)?(?:immobil[ei]\b|unit[aà]\s+immobiliar|dati\s+identificativi|catasto\s|"
                            r"situazione\b|totale\b|rilasciata\b|visura\s+n|n\.\s+dati|unit[aà]\s+immobiliari\s+site|"
                            r"particella\s+n|dati\s+(?:di\s+)?classamento|comune\s+di\b|ultimo\s+atto)", re.I)

# campi del CSV delle unità (indice.csv), nell'ordine. Nessun dato personale.
CAMPI_UNITA = [
    "file", "pagina", "tipo_visura", "data_visura", "catasto", "formato",
    "comune", "codice_comune", "sezione", "foglio", "particella", "subalterno",
    "zona_censuaria", "microzona", "categoria", "classe", "consistenza", "unita_consistenza",
    "superficie_catastale", "superficie_escluse_aree_scoperte", "rendita_euro",
    "indirizzo", "piano", "piani", "piani_fuori_terra", "piani_interrati", "piano_piu_alto",
    "qualita", "porzione", "superficie_m2", "reddito_dominicale_euro", "reddito_agrario_euro",
    "esito", "nota",
]


def numero(s) -> float | None:
    """Numeri all'italiana: 1.880,00 → 1880.0; 6,5 → 6.5; 1.250 → 1250."""
    if s is None:
        return None
    t = str(s).strip().replace(" ", "").replace(" ", "")
    t = re.sub(r"[^\d.,-]", "", t)
    if not t or not re.search(r"\d", t):
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def intero_o_float(x: float | None):
    if x is None:
        return None
    return int(x) if float(x).is_integer() else round(x, 2)


def norma_categoria(s: str | None) -> str | None:
    if not s:
        return None
    m = CATEGORIA.search(s.upper())
    return f"{m.group(1)}/{int(m.group(2))}" if m else None


def norma_testo(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace(" ", " ").replace("’", "'")
    s = s.replace("m2 ", "m² ").replace("mq.", "m²").replace("m³", "m³")
    return s


@dataclass
class Visura:
    file: str
    pagine: int = 0
    tipo_visura: str | None = None
    data_visura: str | None = None
    esito: str = "letta"        # letta | non_riconosciuta | senza_testo | errore
    nota: str = ""
    unita: list[dict] = field(default_factory=list)
    intestatari: list[dict] = field(default_factory=list)   # solo con includi_intestatari
    righe_personali: int = 0     # quante righe con dati personali sono state tolte


# ------------------------------------------------------------------ dati personali
def separa_personali(righe: list[str], R: Regole) -> tuple[list[str], list[str]]:
    """(righe senza dati personali, righe personali). Una riga è personale se ha un codice fiscale, una nascita o un
    diritto/quota, o se sta in una sezione di intestatari (da «INTESTATO»/«Intestazione» alla riga che riprende con i
    dati dell'immobile)."""
    pulite, personali = [], []
    in_sezione = False
    for r in righe:
        if in_sezione and FINE_PERSONALI.search(r) and not R.c_e("personali", "sezione", r):
            in_sezione = False
        if R.c_e("personali", "sezione", r):
            in_sezione = True
        if in_sezione or any(R.c_e("personali", v, r) for v in ("codice_fiscale", "nascita", "diritto")):
            personali.append(r)
        else:
            pulite.append(r)
    return pulite, personali


def leggi_intestatari(personali: list[str], R: Regole) -> list[dict]:
    """Solo con l'opzione esplicita: nominativo (testo della riga senza codice fiscale), codici fiscali, diritto."""
    out = []
    for r in personali:
        cf = [m.group(1) for p in R.lista("personali", "codice_fiscale") for m in p.finditer(r)]
        dir_ = R.cerca("personali", "diritto", r)
        if not cf and not dir_:
            continue
        testo = re.sub(r"\s{2,}", " ", r).strip()
        out.append({"riga": testo, "codici_fiscali": ";".join(dict.fromkeys(cf)),
                    "diritto": r[dir_.start():].strip() if dir_ else ""})
    return out


# ------------------------------------------------------------------ campi di un'unità
def _piano(u: dict, testo: str | None) -> None:
    if testo:
        u["piano"] = testo.strip(" ;,")
    liv, altri = P.livelli(u.get("piano"))
    u.update(P.riassumi(liv, altri))


def _completa(u: dict) -> dict:
    """Esito dell'unità e campi derivati."""
    if u.get("categoria"):
        u["categoria"] = norma_categoria(u["categoria"])
    manca = []
    if u.get("catasto") == "F":
        for c in ("categoria", "consistenza", "rendita_euro"):
            if u.get(c) in (None, ""):
                manca.append(c)
        if (u.get("categoria") or "").startswith(("A", "B", "C")) and u.get("superficie_catastale") is None:
            manca.append("superficie_catastale")
        if not u.get("piano"):
            manca.append("piano")
    else:
        for c in ("qualita", "superficie_m2"):
            if u.get(c) in (None, ""):
                manca.append(c)
    # le categorie F (aree urbane, collabenti…) e le E non hanno sempre consistenza e rendita
    gruppo = (u.get("categoria") or "")[:1]
    if gruppo == "D":           # gruppo D: niente consistenza, solo rendita
        manca = [m for m in manca if m != "consistenza"]
    if gruppo in ("E", "F"):    # E ed F (aree urbane, collabenti…): consistenza e rendita non sempre presenti
        manca = [m for m in manca if m not in ("consistenza", "rendita_euro", "piano")]
    u["esito"] = "ok" if not manca else "parziale"
    if manca:
        u["nota"] = ((u.get("nota") or "") + "; " if u.get("nota") else "") + "manca: " + ", ".join(manca)
    for k in ("foglio", "particella", "subalterno"):
        if u.get(k):
            u[k] = re.sub(r"^0+(?=\w)", "", str(u[k]).strip().upper())
    return u


def campi_etichette(testo: str, R: Regole, catasto: str) -> dict:
    u: dict = {"catasto": catasto, "formato": "etichette"}
    v = lambda voce: R.valore("campi", voce, testo)   # noqa: E731
    for c in ("sezione", "foglio", "particella", "subalterno", "zona_censuaria", "microzona"):
        u[c] = v(c)
    if catasto == "F":
        u["categoria"] = v("categoria")
        u["classe"] = v("classe")
        m = R.cerca("campi", "consistenza", testo)
        if m:
            u["consistenza"] = intero_o_float(numero(m.group(1)))
            un = m.group(2).lower()
            u["unita_consistenza"] = "vani" if un == "vani" else ("m³" if un in ("m³", "m3", "mc") else "m²")
        u["superficie_catastale"] = intero_o_float(numero(v("superficie_totale")))
        u["superficie_escluse_aree_scoperte"] = intero_o_float(numero(v("superficie_escluse")))
        u["rendita_euro"] = intero_o_float(numero(v("rendita")))
        u["indirizzo"] = v("indirizzo")
        _piano(u, v("piano"))
    else:
        m = R.cerca("campi", "qualita", testo)
        if m:
            u["qualita"] = re.sub(r"\s+", " ", m.group(1)).strip().upper()
            if m.lastindex and m.lastindex >= 2:
                u["classe"] = m.group(2)
        if not u.get("classe"):
            u["classe"] = v("classe")
        m = R.cerca("campi", "superficie_ha", testo)
        if m:
            u["superficie_m2"] = int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
        else:
            u["superficie_m2"] = intero_o_float(numero(v("superficie_m2")))
        u["reddito_dominicale_euro"] = intero_o_float(numero(v("reddito_dominicale")))
        u["reddito_agrario_euro"] = intero_o_float(numero(v("reddito_agrario")))
        u["porzione"] = None
    return u


# ------------------------------------------------------------------ formato a tabella
def _segmenti(riga: str) -> list[tuple[int, int, str]]:
    """Pezzi di testo separati da almeno due spazi: (inizio, fine, testo)."""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", riga)]


def colonne_titoli(riga: str, R: Regole) -> list[tuple[float, str]]:
    """Centri delle colonne riconosciute nella riga dei titoli: [(centro, nome della colonna)]."""
    out = []
    alias = sorted(((a, k) for k, l in R.colonne.items() for a in l), key=lambda x: -len(x[0]))
    for ini, fine, t in _segmenti(riga):
        # un segmento può contenere più titoli separati da uno spazio («Zona Micro»): si prova parola per parola
        parole = [(m.start() + ini, m.end() + ini, m.group(0)) for m in re.finditer(r"\S+", t)]
        i = 0
        while i < len(parole):
            preso = False
            for a, k in alias:
                n = len(a.split())
                pezzo = " ".join(p[2] for p in parole[i:i + n]).lower().rstrip(":")
                if pezzo == a or (n == 1 and pezzo.rstrip(".") == a.rstrip(".")):
                    s, e = parole[i][0], parole[i + n - 1][1]
                    out.append(((s + e) / 2, k))
                    i += n
                    preso = True
                    break
            if not preso:
                i += 1
    return out


def celle(riga: str, cols: list[tuple[float, str]]) -> dict[str, str]:
    """Ogni pezzo della riga va alla colonna con il centro più vicino al suo inizio o al suo centro (il più vicino dei due:
    vanno bene sia le celle allineate a sinistra sia quelle centrate)."""
    out: dict[str, str] = {}
    if not cols:
        return out
    for ini, fine, t in _segmenti(riga):
        def dist(c):
            return min(abs(c[0] - ini - 1), abs(c[0] - (ini + fine) / 2))
        # i pezzi lunghi a sinistra della prima colonna utile vanno comunque alla più vicina
        nome = min(cols, key=dist)[1]
        out[nome] = (out[nome] + " " + t) if nome in out else t
    return out


def unita_da_riga(c: dict[str, str], extra: list[str], R: Regole, catasto: str) -> dict:
    u: dict = {"catasto": catasto, "formato": "tabella"}
    for k in ("sezione", "foglio", "particella", "subalterno", "zona_censuaria", "microzona", "classe", "porzione"):
        if c.get(k):
            u[k] = c[k].split()[0]
    testo_extra = "\n".join(extra)
    if catasto == "F":
        cat = norma_categoria(c.get("categoria") or "") or norma_categoria(" ".join(c.values()))
        u["categoria"] = cat
        cons = c.get("consistenza", "")
        m = re.search(r"([0-9][0-9.,]*)\s*(vani|m²|m2|mq|m³|m3|mc)", cons, re.I)
        if m:
            u["consistenza"] = intero_o_float(numero(m.group(1)))
            un = m.group(2).lower()
            u["unita_consistenza"] = "vani" if un == "vani" else ("m³" if un in ("m³", "m3", "mc") else "m²")
        sup = c.get("superficie", "")
        u["superficie_catastale"] = intero_o_float(numero(R.valore("campi", "superficie_totale", sup) or sup))
        u["superficie_escluse_aree_scoperte"] = intero_o_float(numero(
            R.valore("campi", "superficie_escluse", sup + "\n" + testo_extra)))
        ren = c.get("rendita", "")
        u["rendita_euro"] = intero_o_float(numero(re.sub(r"(?i)euro|€|l\.", "", ren))) if re.search(r"(?i)euro|€|\d,\d\d", ren) else None
        ind = " ".join(x for x in (c.get("indirizzo", ""), c.get("dati_derivanti", "") if "piano" in c.get("dati_derivanti", "").lower() else "") if x)
        tutto = ind + "\n" + testo_extra
        mi = re.match(rf"(.+?)(?=\s+pian[oi]:?\s+(?:da\s+\d|{FT}(?![\w°]))|\s*;|\s*$)", ind.strip(), re.I)
        u["indirizzo"] = mi.group(1).strip(" ,;") if mi and mi.group(1).strip() else (ind.strip() or None)
        _piano(u, R.valore("campi", "piano", tutto))
    else:
        q = c.get("qualita", "")
        mq = re.match(r"([A-Z][A-Z .']+?)(?:\s+(\d{1,2}|U))?\s*$", q.strip(), re.I)
        if mq:
            u["qualita"] = re.sub(r"\s+", " ", mq.group(1)).strip().upper()
            if mq.group(2) and not u.get("classe"):
                u["classe"] = mq.group(2)
        ha = c.get("superficie_ha") or c.get("superficie") or ""
        m = re.search(r"(\d{1,4})\s*[. ]\s*(\d{2})\s*[. ]\s*(\d{2})\b", ha)
        if m:
            u["superficie_m2"] = int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
        else:
            u["superficie_m2"] = intero_o_float(numero(ha))
        dom = c.get("reddito_dominicale", "") or ""
        agr = c.get("reddito_agrario", "") or ""
        if not agr and dom.lower().count("euro") >= 2:
            dom, agr = dom.lower().split("euro")[1], dom.lower().split("euro")[2]
        u["reddito_dominicale_euro"] = intero_o_float(numero(dom.lower().replace("euro", "")))
        u["reddito_agrario_euro"] = intero_o_float(numero(agr.lower().replace("euro", "")))
    return u


# ------------------------------------------------------------------ documento intero
def _comune(riga: str, R: Regole) -> tuple[str, str] | None:
    m = R.cerca("comune", "nome_codice", riga)
    if not m:
        return None
    nome = re.sub(r"\s+", " ", m.group(1)).strip(" -").upper()
    return nome, m.group(2).upper()


def _catasto_blocco(testo: str, R: Regole) -> str:
    if re.search(r"catasto\s+(?:dei\s+)?terreni", testo, re.I):
        return "T"
    if re.search(r"catasto\s+(?:dei\s+)?fabbricati", testo, re.I) or CATEGORIA.search(testo):
        return "F"
    return "T" if R.c_e("blocchi", "terreni", testo) else "F"


def leggi_testo(pagine: list[str], R: Regole | None = None, file: str = "", includi_intestatari: bool = False) -> Visura:
    """Legge il testo delle pagine (una stringa per pagina) e restituisce la visura con le unità trovate."""
    R = R or carica()
    vis = Visura(file=file, pagine=len(pagine))
    tutto = "\n".join(pagine)
    if not tutto.strip():
        vis.esito, vis.nota = "senza_testo", "il PDF non contiene testo (scansione?): serve una visura in PDF digitale"
        return vis
    if not any(R.c_e("documento", "riconoscimento", tutto) for _ in [0]):
        vis.esito, vis.nota = "non_riconosciuta", "il testo non sembra una visura catastale"
        return vis
    vis.tipo_visura = ("per soggetto" if R.c_e("documento", "per_soggetto", tutto)
                       else "per immobile" if R.c_e("documento", "per_immobile", tutto) else None)
    if vis.tipo_visura and R.c_e("documento", "storica", tutto):
        vis.tipo_visura += " (storica)"
    d = R.valore("documento", "data", tutto)
    vis.data_visura = d

    # righe con il numero di pagina, senza dati personali
    righe: list[tuple[int, str]] = []
    personali_tutte: list[str] = []
    for n, testo in enumerate(pagine, 1):
        rr = [norma_testo(x) for x in testo.splitlines()]
        pulite, pers = separa_personali(rr, R)
        personali_tutte += pers
        righe += [(n, x) for x in pulite]
    vis.righe_personali = len(personali_tutte)
    if includi_intestatari:
        vis.intestatari = leggi_intestatari(personali_tutte, R)

    comune: tuple[str, str] | None = None
    cols: list[tuple[float, str]] | None = None
    cat_tab = "F"
    riga_corr: tuple[int, dict, list[str], tuple | None] | None = None   # (pagina, celle, righe in più, comune)
    blocco: tuple[int, list[str], tuple | None] | None = None           # (pagina, righe, comune)

    def chiudi_riga():
        nonlocal riga_corr
        if riga_corr:
            pag, cc, extra, com = riga_corr
            u = unita_da_riga(cc, extra, R, cat_tab)
            _aggiungi(vis, u, pag, com)
            riga_corr = None

    def chiudi_blocco():
        nonlocal blocco
        if blocco:
            pag, rr, com = blocco
            testo = "\n".join(rr)
            c2 = None
            for x in rr:
                c2 = c2 or _comune(x, R)
            u = campi_etichette(testo, R, _catasto_blocco(testo, R))
            if u.get("foglio") and u.get("particella"):
                _aggiungi(vis, u, pag, c2 or com)
            blocco = None

    for pag, r in righe:
        c = _comune(r, R)
        if c:
            comune = c
        if R.c_e("tabella", "titoli_fabbricati", r) or R.c_e("tabella", "titoli_terreni", r):
            chiudi_riga()
            chiudi_blocco()
            cols = colonne_titoli(r, R)
            cat_tab = "T" if R.c_e("tabella", "titoli_terreni", r) and not re.search(r"categoria", r, re.I) else "F"
            continue
        if any(p.search(r) for p in R.lista("blocchi", "inizio")) and not (cols and NUMERO_N.match(r)):
            chiudi_riga()
            chiudi_blocco()
            cols = None
            blocco = (pag, [r], comune)
            continue
        if cols:
            if STOP_TABELLA.search(r):
                chiudi_riga()
                if not re.match(r"^\s*totale", r, re.I):
                    cols = None
                continue
            cc = celle(r, cols)
            n_ok = cc.get("n", "").strip().isdigit() or bool(NUMERO_N.match(r))
            ha_dati = (cat_tab == "F" and CATEGORIA.search(r)) or (cat_tab == "T" and len(re.findall(r"\b\d+\b", r)) >= 4)
            if n_ok and ha_dati and cc.get("foglio") and cc.get("particella"):
                chiudi_riga()
                riga_corr = (pag, cc, [], comune)
            elif riga_corr and r.strip():
                if len(riga_corr[2]) < 4:
                    riga_corr[2].append(r)
            continue
        if blocco:
            blocco[1].append(r)
    chiudi_riga()
    chiudi_blocco()

    # una visura per immobile senza blocchi «Immobile n.»: tutto il testo è un blocco solo
    if not vis.unita and re.search(r"categoria\s+[A-F]\s?/|qualit[aà]", tutto, re.I):
        testo = "\n".join(x for _, x in righe)
        u = campi_etichette(testo, R, _catasto_blocco(testo, R))
        if u.get("foglio") and u.get("particella"):
            _aggiungi(vis, u, 1, comune)
    if not vis.unita:
        vis.esito, vis.nota = "non_riconosciuta", "nessuna unità riconosciuta: adattare regole.toml (vedi README)"
    return vis


def _aggiungi(vis: Visura, u: dict, pagina: int, comune: tuple | None) -> None:
    u["file"] = vis.file
    u["pagina"] = pagina
    u["tipo_visura"] = vis.tipo_visura
    u["data_visura"] = vis.data_visura
    if comune:
        u.setdefault("comune", comune[0])
        u.setdefault("codice_comune", comune[1])
    vis.unita.append(_completa(u))


def leggi_pdf(percorso: str | Path, R: Regole | None = None, includi_intestatari: bool = False) -> Visura:
    from .testo import estrai
    p = Path(percorso)
    try:
        pagine = estrai(p)
    except Exception as e:      # PDF rovinato o cifrato: si segnala e si va avanti
        return Visura(file=p.name, esito="errore", nota=f"PDF non leggibile: {str(e)[:160]}")
    return leggi_testo(pagine, R, file=p.name, includi_intestatari=includi_intestatari)
