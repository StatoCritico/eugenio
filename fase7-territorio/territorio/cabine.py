"""Cabine primarie: raccordo e-distribuzione ↔ aree convenzionali GSE ↔ sottostazioni OpenStreetMap, criticità dei comuni.

Fonti (tutte pubbliche, 17/11/2026):
- e-distribuzione S.p.A., mappa delle Aree critiche (servizio `comuniServiti`): per ogni comune i trasformatori AT/MT
  che lo servono, con codice e nome della cabina primaria e livello di saturazione (mensile). Nessuna licenza
  dichiarata: uso non commerciale, fonte citata, rimozione su richiesta.
- e-distribuzione, strato `View_ComuniGestitiED2021Is` (comuni ISTAT 2021 con `servitoed` 0/1).
- GSE S.p.A., aree convenzionali `AC_Comuni_2025` (CC BY-NC-SA 3.0 IT): i poligoni servono solo al calcolo, si
  scaricano una volta in una cartella di lavoro e **non si salvano mai nel repository né sul server**; nei file escono
  solo i codici `COD_AC` e il gestore.
- OpenStreetMap (`power=substation`, © contributori OpenStreetMap, ODbL): le posizioni delle cabine. Ogni file con
  coordinate porta l'attribuzione e la licenza ODbL.
- ISTAT: elenco dei comuni, comuni soppressi, variazioni dal 1991 (CC BY 4.0) per riportare i codici ai comuni attuali.

Le funzioni pure (nomi, punteggi, criticità, codici ISTAT) non usano la rete e sono riusate dal servizio notturno.
Le parti geometriche richiedono `shapely` e `scipy`; l'estrazione dal PBF richiede `osmium` (pyosmium).
"""
from __future__ import annotations

import csv
import datetime as dt
import difflib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

# ----------------------------------------------------------------------------------------------- fonti e licenze

SERVIZIO_GSE = "https://services-eu1.arcgis.com/sawHMGY9o8rHlY2j/arcgis/rest/services/AC_Comuni_2025/FeatureServer/0"
COMUNI_ED = ("https://dpa-portalgis.enel.com/server/rest/services/Hosted/View_ComuniGestitiED2021Is/FeatureServer/0")
FONTE_ED = ("e-distribuzione S.p.A., mappa delle Aree critiche (servizio comuniServiti) – "
            "https://www.e-distribuzione.it/a-chi-ci-rivolgiamo/produttori/aree-critiche.html")
FONTE_GSE = ("GSE S.p.A. – Mappa interattiva delle cabine primarie (codici COD_AC delle aree convenzionali) – "
             "https://www.gse.it/servizi-per-te/autoconsumo/mappa-interattiva-delle-cabine-primarie")
ATTRIBUZIONE_OSM = "© contributori OpenStreetMap, ODbL"
LICENZA_OSM = "ODbL 1.0 – https://opendatacommons.org/licenses/odbl/1-0/"
LICENZA_RACCORDO = ("Posizioni: © contributori OpenStreetMap, ODbL 1.0. Codici e nomi delle cabine: e-distribuzione "
                    "S.p.A. (uso non commerciale, fonte citata). Codici delle aree convenzionali: GSE S.p.A. "
                    "(CC BY-NC-SA 3.0 IT). Raccordo: elaborazione di EuGEnio.")
LIVELLI = ("VERDE", "GIALLO", "ARANCIONE", "ROSSO")
REGOLA_CRITICITA = (
    "Classificazione di EuGEnio sui trasformatori AT/MT che servono il comune (dato mensile e-distribuzione): "
    "L = livello più alto presente (VERDE < GIALLO < ARANCIONE < ROSSO), q = quota dei trasformatori con livello L. "
    "L = VERDE: nessun riempimento; q > 0,5: colore pieno di L; altrimenti strisce tra il livello precedente e L "
    "(VERDE/GIALLO = bianco/giallo, GIALLO/ARANCIONE, ARANCIONE/ROSSO).")

# --------------------------------------------------------------------------------------------- criticità (pure)


def classe_comune(conteggi: dict) -> dict:
    """Criticità di un comune dai conteggi dei trasformatori per livello (regola del contratto, 17/11/2026).

    `conteggi`: {"VERDE": n, "GIALLO": n, "ARANCIONE": n, "ROSSO": n} (chiavi mancanti = 0; altre chiavi ignorate).
    Restituisce {"livello", "quota", "pieno", "strisce"}: `pieno` è il livello da usare a tinta unita (o None),
    `strisce` la coppia [precedente, L] (o None). Senza trasformatori: livello None, nessun riempimento.
    """
    c = {k: int(conteggi.get(k, 0) or 0) for k in LIVELLI}
    tot = sum(c.values())
    if tot == 0:
        return {"livello": None, "quota": None, "pieno": None, "strisce": None}
    i = max(j for j, k in enumerate(LIVELLI) if c[k] > 0)
    L = LIVELLI[i]
    q = round(c[L] / tot, 4)
    if L == "VERDE":
        return {"livello": L, "quota": q, "pieno": None, "strisce": None}
    if q > 0.5:
        return {"livello": L, "quota": q, "pieno": L, "strisce": None}
    return {"livello": L, "quota": q, "pieno": None, "strisce": [LIVELLI[i - 1], L]}


def livello_peggiore(livelli) -> str | None:
    """Livello più alto tra quelli dati (i valori sconosciuti si ignorano)."""
    ii = [LIVELLI.index(x) for x in livelli if x in LIVELLI]
    return LIVELLI[max(ii)] if ii else None


# --------------------------------------------------------------------------------------------------- nomi (pure)

# parole che non distinguono una cabina dall'altra
PAROLE_VUOTE = {
    "CP", "CABINA", "PRIMARIA", "PRIMARIE", "SE", "SC", "SSE", "SS", "STAZIONE", "SOTTOSTAZIONE", "ELETTRICA",
    "ELETTRICO", "ENEL", "EDISTRIBUZIONE", "DISTRIBUZIONE", "TERNA", "SPA", "KV", "AT", "MT", "UW", "SM", "VS",
    "DI", "DEL", "DELLA", "DELLE", "DEI", "DEGLI", "DELLO", "DA", "IN", "E", "ED", "LA", "IL", "LO", "LE", "GLI",
    "I", "AL", "ALLA", "VIA", "VIALE", "LOC", "LOCALITA", "FRAZ", "FRAZIONE", "UMSPANNWERK",
}
SOSTITUZIONI = [  # (espressione sul testo già maiuscolo e senza accenti, sostituzione)
    (r"\bE[-\s]?DISTRIBUZIONE\b", " "),
    (r"\bC\s*\.\s*P\s*\.?(?=\s|$)", " CP "),
    (r"\bZ\s*\.\s*I\s*\.?(?=\s|$)", " ZI "),
    (r"\bZONA\s+IND(USTRIALE|\.?LE|\.)?\b", " ZI "),
    (r"\bZ\s*\.?\s*IND(USTRIALE|\.?LE|\.)?\b", " ZI "),
    (r"\bIND(\.?LE|USTRIALE|\.)?(?=\s|$|\.)", " ZI "),   # «LECCE IND.» = «Lecce Industriale» = zona industriale
    (r"\b\d+\s*KV\b", " "),
    (r"\bSTAZ\.?\b", " STAZIONE "),
    (r"\bM\.?TE\b", " MONTE "), (r"\bP\.?TO\b", " PORTO "), (r"\bP\.?TA\b", " PORTA "), (r"\bP\.?ZZA\b", " PIAZZA "),
    (r"\bB\.?GO\b", " BORGO "), (r"\bC\.?SO\b", " CORSO "), (r"\bC\.?LLO\b", " CASTELLO "),
    (r"\bN\.\s*E\.?(?=\s|$)", " NORDEST "), (r"\bN\.\s*O\.?(?=\s|$)", " NORDOVEST "),
    (r"\bS\.\s*E\.(?=\s|$)", " SUDEST "), (r"\bS\.\s*O\.?(?=\s|$)", " SUDOVEST "),
]
SANTI = {"SAN", "SANTA", "SANTO", "SANT", "SS", "STA", "STO", "S"}
ROMANI = {"II": "2", "III": "3", "IV": "4"}  # niente V/VI: sono anche sigle (VI = Vicenza)


def normalizza_nome(s: str) -> str:
    """Maiuscole, senza accenti né punteggiatura, abbreviazioni comuni sciolte (Z.I. → ZI, C.P. → CP …)."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"\b(D|L|DELL|DALL|NELL|SULL|ALL|UN|QUELL)'\s*", "", s)   # articoli elisi: D'ADDA → ADDA
    s = s.replace("'", " ")
    for a, b in SOSTITUZIONI:
        s = re.sub(a, b, s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def gettoni(s: str) -> list[str]:
    """Parole significative del nome: «S.», «SAN», «SANTA», «SANT'» diventano «S»; numeri romani in cifre;
    tensioni (≥ 30, es. 132, 150) e parole vuote (CP, SE, cabina, e-distribuzione…) tolte."""
    out = []
    for t in normalizza_nome(s).split():
        if t in SANTI:
            t = "S"
        elif t in ROMANI and out:
            t = ROMANI[t]
        if t in PAROLE_VUOTE and t != "S":
            continue
        if t.isdigit() and int(t) >= 30:
            continue
        out.append(t)
    # lettere isolate consecutive unite («V. T.» → VT, «N. E.» → NE), tranne la «S» dei santi
    out = _unisci_lettere(out)
    out = [{"NE": "NORDEST", "NO": "NORDOVEST", "SO": "SUDOVEST"}.get(t, t) if len(out) > 1 and i > 0 else t
           for i, t in enumerate(out)]
    out = [t for t in out if not re.fullmatch(r"TR\d*", t)]          # «TR3»: trasformatore, non nome
    # CS (cabina di smistamento), IC: sigle tecniche, tranne in prima posizione (CS = Cosenza)
    out = [t for i, t in enumerate(out) if not (i > 0 and t in ("CS", "IC", "CSA"))]
    # «S» da sola in fondo (es. «… SE» già tolto) non serve
    return [t for i, t in enumerate(out) if not (t == "S" and i == len(out) - 1 and len(out) > 1)]


def _unisci_lettere(tt: list[str]) -> list[str]:
    """Lettere isolate consecutive (non «S») unite in una sigla: V T → VT."""
    out, buf = [], ""
    for t in tt:
        if len(t) == 1 and t.isalpha() and t != "S":
            buf += t
            continue
        if buf:
            out.append(buf)
            buf = ""
        out.append(t)
    if buf:
        out.append(buf)
    return out


def somiglianza_gettone(a: str, b: str) -> float:
    """0..1 fra due parole: uguali 1; troncatura (FLUMINIMAGGI/FLUMINIMAGGIORE) 0,95; iniziale (Q → QUARTU) 0,7;
    errore di battitura (rapporto difflib ≥ 0,85) il rapporto; altrimenti 0."""
    if a == b:
        return 1.0
    if a.isdigit() or b.isdigit():
        return 0.0
    if len(a) == 1 or len(b) == 1:
        corta, lunga = (a, b) if len(a) == 1 else (b, a)
        return 0.7 if corta != "S" and lunga.startswith(corta) and len(lunga) > 1 else 0.0
    if min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)):
        return 0.95
    if min(len(a), len(b)) == 2 and max(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return 0.8  # «VIGEV.OV» = «Vigevano Ovest»
    r = difflib.SequenceMatcher(None, a, b).ratio()
    return r if r >= 0.85 else 0.0


def punteggio_nome(nome_ed: str, nomi_osm, generiche=frozenset()) -> float:
    """Somiglianza 0..1 fra il nome e-distribuzione e il migliore dei nomi OSM (name, alt_name, old_name…).

    Conta soprattutto quante parole del nome e-distribuzione si ritrovano (75 %), poi quante parole del nome OSM sono
    spiegate (25 %). Le parole `generiche` (es. il nome del comune servito, «PADOVA» in «PADOVA FIERA») valgono metà
    quando ci sono altre parole.
    """
    ge = gettoni(nome_ed)
    if not ge:
        return 0.0
    migliore = 0.0
    compatto = "".join(ge)
    for n in ([nomi_osm] if isinstance(nomi_osm, str) else nomi_osm):
        go = gettoni(n)
        if not go:
            continue
        if "".join(go) == compatto or normalizza_nome(n).replace(" ", "") == normalizza_nome(nome_ed).replace(" ", ""):
            return 1.0  # «SAN GEMINI» = «Sangemini»
        # nome OSM accorciato: «Canosa» per «CANOSA DI PUGLIA», «Barberino» per «BARBERINO DEL MUGELLO»
        if len(go) < len(ge) and len(ge[0]) >= 4 and all(somiglianza_gettone(a, b) >= 0.95 for a, b in zip(go, ge)):
            migliore = max(migliore, 0.8)
        # «EBOLI 1» = «Eboli»: il numero 1 manca spesso nel nome OSM
        ge_n = [t for t in ge if not (t == "1" and len(ge) > 1 and not any(u.isdigit() for u in go))]
        ge_n = ge_n or ge
        pesi = [0.5 if (t in generiche and len(ge_n) > 1) else 1.0 for t in ge_n]
        # sigle di iniziali: «ISOLA C.R.» = «Isola Capo Rizzuto», «PRATA P.U.» = «Prata Principato Ultra»
        iniz = {"".join(x[0] for x in go[k:k + n]) for n in (2, 3) for k in range(len(go) - n + 1)}
        trov = [max([somiglianza_gettone(t, u) for u in go] + [0.9 if 2 <= len(t) <= 3 and t in iniz else 0])
                for t in ge_n]
        richiamo = sum(p * x for p, x in zip(pesi, trov)) / sum(pesi)
        sigle = [t for t in ge_n if 2 <= len(t) <= 3 and t in iniz]
        spiegate = sum(max([somiglianza_gettone(u, t) for t in ge_n] + [0.9 if any(u[0] == x[0] or u[0] in x
                                                                              for x in sigle) else 0])
                       for u in go) / len(go)
        migliore = max(migliore, round(0.75 * richiamo + 0.25 * spiegate, 4))
    return round(migliore, 4)


# ----------------------------------------------------------------------------------------------- ISTAT (pure)

def chiave_comune(nome: str) -> str:
    """Nome del comune ridotto per il confronto (senza accenti, apostrofi, spazi; prima parte dei nomi bilingui)."""
    s = unicodedata.normalize("NFKD", str(nome or "").split("/")[0]).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", s)


def codice_attuale(codice: str, descrizione: str, attuali: dict, successivi: dict | None = None,
                   provincia=None) -> tuple[str | None, str]:
    """Riporta un codice ISTAT del comune (anche vecchio) al codice attuale.

    `attuali`: {codice: nome} dei comuni di oggi; `successivi`: {codice vecchio: codice nuovo} (cambi di provincia e
    comuni confluiti, dalle tabelle ISTAT); `descrizione`: testo e-distribuzione, che può contenere «(NUOVO=028108)»;
    `provincia`: codice (o insieme di codici) di provincia attuale per scegliere fra omonimi.
    Restituisce (codice, modo) con modo in {"uguale", "nuovo_ed", "variazioni", "nome", "ambiguo", "non_trovato"}.
    """
    codice = str(codice or "").zfill(6)
    m = re.search(r"NUOVO\s*=\s*(\d{6})", descrizione or "")
    if m and m.group(1) in attuali:
        return m.group(1), "nuovo_ed"
    if codice in attuali:
        return codice, "uguale"
    c, passi = codice, 0
    while successivi and c in successivi and passi < 10:
        c, passi = successivi[c], passi + 1
        if c in attuali:
            return c, "variazioni"
    nome = re.sub(r"^\s*\([^)]*\)\s*", "", descrizione or "")
    k = chiave_comune(nome)
    cand = [x for x, n in attuali.items() if chiave_comune(n) == k] if k else []
    if len(cand) > 1 and provincia:
        pp = {str(provincia).zfill(3)} if isinstance(provincia, (str, int)) else {str(x).zfill(3) for x in provincia}
        stessa = [x for x in cand if x[:3] in pp]
        cand = stessa or cand
    if len(cand) > 1:  # stessa regione: le prime due cifre del codice non bastano, si usa la provincia vecchia
        vicini = [x for x in cand if x[:3] == codice[:3]]
        cand = vicini or cand
    if len(cand) == 1:
        return cand[0], "nome"
    return (None, "ambiguo") if cand else (None, "non_trovato")


def leggi_elenco_istat(percorso: Path):
    """Elenco ISTAT dei comuni attuali (`Elenco-comuni-italiani.csv`, `;`, latin1).

    Restituisce (attuali {istat: nome}, province {istat: (sigla, capoluogo)}, regioni {istat: "08"}).
    """
    with open(percorso, encoding="latin1", newline="") as fh:
        righe = [{k.split("\n")[0].strip(): v for k, v in r.items()} for r in csv.DictReader(fh, delimiter=";")]
    attuali = {r["Codice Comune formato alfanumerico"]: r["Denominazione in italiano"] for r in righe}
    flag = next(k for k in righe[0] if k.startswith("Flag Comune capoluogo"))
    capoluogo = {r["Sigla automobilistica"]: r["Denominazione in italiano"] for r in righe if r[flag] == "1"}
    province = {r["Codice Comune formato alfanumerico"]: (r["Sigla automobilistica"],
                                                          capoluogo.get(r["Sigla automobilistica"], ""))
                for r in righe}
    regioni = {r["Codice Comune formato alfanumerico"]: r["Codice Regione"] for r in righe}
    return attuali, province, regioni


def leggi_successivi_istat(cartella: Path) -> dict:
    """{codice vecchio: codice successivo} dai CSV ISTAT «Elenco comuni soppressi» e «Variazioni … dal 1991»
    (cambi di provincia AP e comuni confluiti). I file si cercano in `cartella` (anche in sottocartelle)."""
    cartella = Path(cartella)
    succ = {}
    for f in cartella.rglob("*.csv"):
        testo = f.read_bytes().decode("latin1")
        righe = list(csv.reader(testo.splitlines(), delimiter=";"))
        if not righe:
            continue
        h = [x.strip() for x in righe[0]]
        if "Tipo variazione" in h:
            it, ic = h.index("Tipo variazione"), h.index("Codice Comune formato alfanumerico")
            iv = next(i for i, x in enumerate(h) if x.startswith("Codice del Comune associato"))
            for r in righe[1:]:
                if len(r) > iv and r[it].strip() == "AP" and r[iv].strip() and r[ic].strip() != r[iv].strip():
                    succ[r[ic].strip()] = r[iv].strip()
        elif "Codice del Comune associato alla variazione" in h and "Codice Comune" in h:
            ic, iv = h.index("Codice Comune"), h.index("Codice del Comune associato alla variazione")
            for r in righe[1:]:
                if len(r) > iv and r[iv].strip():
                    succ.setdefault(r[ic].strip(), r[iv].strip())
    return succ


# ------------------------------------------------------------------------------------ coordinate (UTM 32N, WGS84)

_A, _F, _K0, _L0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(9)
_E2 = _F * (2 - _F)
_EP2 = _E2 / (1 - _E2)
# trasformazione dei percorsi SVG dei file di mappa del sito (fase5-sito/costruisci_mappa.py, confini_gl.js)
SVG_S, SVG_AX, SVG_AY = 0.0010012596459353985, -313.67365575107954, 5226.851664605516


def utm(lon, lat):
    """lon, lat (gradi, anche array numpy) → E, N in metri nel fuso 32N esteso (serie di Snyder)."""
    import numpy as np
    lon, lat = np.radians(np.asarray(lon, float)), np.radians(np.asarray(lat, float))
    n = _A / np.sqrt(1 - _E2 * np.sin(lat) ** 2)
    t, c = np.tan(lat) ** 2, _EP2 * np.cos(lat) ** 2
    a = np.cos(lat) * (lon - _L0)
    e2 = _E2
    m = _A * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat
              - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * np.sin(2 * lat)
              + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * np.sin(4 * lat) - (35 * e2 ** 3 / 3072) * np.sin(6 * lat))
    x = _K0 * n * (a + (1 - t + c) * a ** 3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * _EP2) * a ** 5 / 120) + 500000
    y = _K0 * (m + n * np.tan(lat) * (a * a / 2 + (5 - t + 9 * c + 4 * c * c) * a ** 4 / 24
                                       + (61 - 58 * t + t * t + 600 * c - 330 * _EP2) * a ** 6 / 720))
    return x, y


def svg_utm(x, y):
    """Coordinate dei percorsi SVG dei file di mappa del sito → E, N UTM 32N in metri."""
    return (x - SVG_AX) / SVG_S, (SVG_AY - y) / SVG_S


def poligono_svg(d: str):
    """Percorso «M…L…Z M…» dei file di mappa → (Multi)Polygon shapely in metri UTM 32N."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    parti = []
    for parte in str(d or "").split("M"):
        p = parte.replace("Z", "").strip()
        if not p:
            continue
        pts = [svg_utm(*map(float, q.split(","))) for q in p.split("L") if "," in q]
        if len(pts) >= 3:
            parti.append(Polygon(pts).buffer(0))  # anelli che si toccano: buffer(0) li rende validi
    # i percorsi non distinguono i buchi (ogni anello è un poligono a sé): si uniscono, le enclavi restano piene
    return unary_union([q for q in parti if not q.is_empty]) if parti else None


def leggi_comuni_mappa(cartella: Path) -> dict:
    """{istat: {"nome", "geom" (UTM, m)}} dai file di mappa del sito (`fase5-sito/sito/dati/mappa/RR.json`)."""
    out = {}
    for f in sorted(Path(cartella).glob("[0-2][0-9].json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        for c in m.get("comuni") or []:
            out[c["istat"]] = {"nome": c["nome"], "regione": m.get("regione") or f.stem, "geom": poligono_svg(c["d"])}
    return out


# ------------------------------------------------------------------------------------------------ OpenStreetMap

CHIAVI_OSM = ["name", "alt_name", "old_name", "name:it", "short_name", "official_name", "loc_name", "ref",
              "ref:terna", "operator", "owner", "substation", "voltage"]
NOMI_OSM = ["name", "alt_name", "old_name", "name:it", "short_name", "official_name", "loc_name"]
DISTRIBUTORI = re.compile(r"E-?DISTRIBUZIONE|\bENEL\b(?!.*(PRODUZIONE|GREEN|GREENPOWER|SOLE))|ENEL DISTRIBUZIONE|"
                          r"ARETI|ACEA|UNARETI|EDYNA|\bSET\b|SET DISTRIBUZIONE|DEVAL|IRETI|INRETE|V-?RETI|DUERETI|"
                          r"ACEGAS|HERA|A2A|AEM|ASM|SELNET|AGSM|DOLOMITI|RETIPIU|\bAIR\b|LD RETI|ASSEM|SECAB|"
                          r"TERNI DISTRIBUZIONE|DISTRIBUZIONE ELETTRICA ADRIATICA", re.I)
OPERATORE_ED = re.compile(r"E-?DISTRIBUZIONE|^ENEL$|ENEL DISTRIBUZIONE|^ENEL S\.?P\.?A", re.I)
TIPI_ESCLUSI = {"minor_distribution", "traction", "industrial", "gas", "converter", "generation", "production",
                "transformer_tower", "transformer"}


def kv_massimo(voltage) -> int | None:
    """Tensione più alta in kV da «132000;20000» (None se assente o illeggibile)."""
    vals = [int(x) for x in re.split(r"[;,\s]+", str(voltage or "")) if x.isdigit()]
    return max(vals) // 1000 if vals else None


def candidata_osm(f: dict) -> bool:
    """Sottostazione OSM che può essere una cabina primaria (AT/MT).

    Esclusi: sottostazioni ferroviarie; utenti AT con gestore dichiarato che non è un distributore, Terna o Enel
    (acciaierie, aziende); i tipi `minor_distribution`, `industrial`, `generation`… salvo che il gestore sia un
    distributore o che l'alta tensione o il nome dicano «cabina primaria» (in OSM ci sono CP etichettate così, e CP
    dentro le stazioni delle centrali Enel: Cencenighe, Quero, Canterno). Le aree senza alcun attributo piccole
    (< 1.000 m²) sono di norma cabine secondarie."""
    op = f.get("operator") or f.get("owner") or ""
    if re.search(r"FERROVI|\bRFI\b|\bFS\b|TRENITALIA|\bATM\b|METRO", op, re.I) or f.get("substation") == "traction":
        return False
    if op and not (DISTRIBUTORI.search(op) or re.search(r"TERNA|ENEL", op, re.I)):
        return False  # gestore dichiarato che non è un distributore né Terna/Enel: utente AT (acciaieria, azienda…)
    nome = " ".join(str(f.get(k) or "") for k in NOMI_OSM)
    kv = kv_massimo(f.get("voltage"))
    if f.get("substation") in TIPI_ESCLUSI:
        cp = re.search(r"CABINA PRIMARIA|\bC\.?P\.?\b", nome, re.I)
        if not (cp or (kv and kv >= 40 and (DISTRIBUTORI.search(op) or re.search(r"ENEL", op, re.I)))):
            return False
    if kv is not None and kv < 30:
        return False
    if kv is not None and kv >= 40:
        return True
    if DISTRIBUTORI.search(op):
        return True
    if re.search(r"\bC\.?\s?P\b|CABINA PRIMARIA|SOTTOSTAZIONE", nome, re.I):
        return True
    if f.get("substation") in ("distribution", "transmission") and (nome.strip() or (f.get("area_m2") or 0) >= 1000):
        return True
    return bool(nome.strip()) and (f.get("area_m2") or 0) >= 1000 or (f.get("area_m2") or 0) >= 2500


def estrai_sottostazioni(pbf: Path) -> list[dict]:
    """Tutte le `power=substation` del PBF (nodi, way, relazioni) con il centroide delle aree, in tre letture
    (oggetti etichettati, way delle relazioni, posizioni dei nodi): non serve l'indice di tutti i nodi."""
    import osmium
    from shapely.geometry import LineString, MultiPoint
    from shapely.ops import polygonize, unary_union

    nodi, way, rel = {}, {}, {}
    for o in osmium.FileProcessor(str(pbf)).with_filter(osmium.filter.TagFilter(("power", "substation"))):
        tags = {k: o.tags[k] for k in CHIAVI_OSM if k in o.tags}
        if o.is_node():
            nodi[o.id] = (tags, o.location.lon, o.location.lat)
        elif o.is_way():
            way[o.id] = (tags, [n.ref for n in o.nodes])
        elif o.is_relation():
            rel[o.id] = (tags, [m.ref for m in o.members if m.type == "w"])
    serve_w = {w for _, ws in rel.values() for w in ws} - set(way)
    way_rel = {}
    if serve_w:
        for o in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(osmium.filter.IdFilter(serve_w)):
            way_rel[o.id] = [n.ref for n in o.nodes]
    serve_n = {r for _, refs in way.values() for r in refs} | {r for refs in way_rel.values() for r in refs}
    loc = {}
    for o in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(osmium.filter.IdFilter(serve_n)):
        loc[o.id] = (o.location.lon, o.location.lat)

    def centro(linee):
        linee = [l for l in linee if len(l) >= 2]
        if not linee:
            return None, 0
        polys = list(polygonize([LineString(l) for l in linee]))
        if polys:
            g = unary_union(polys)
            c = g.centroid if g.contains(g.centroid) else g.representative_point()
            return (c.x, c.y), round(g.area * 111320 ** 2 * math.cos(math.radians(c.y)))
        p = MultiPoint([q for l in linee for q in l]).centroid
        return (p.x, p.y), 0

    out = [{"osm_id": f"node/{i}", **t, "lon": lo, "lat": la, "area_m2": 0} for i, (t, lo, la) in nodi.items()]
    for i, (t, refs) in way.items():
        c, a = centro([[loc[r] for r in refs if r in loc]])
        if c:
            out.append({"osm_id": f"way/{i}", **t, "lon": c[0], "lat": c[1], "area_m2": a})
    for i, (t, ws) in rel.items():
        c, a = centro([[loc[r] for r in (way[w][1] if w in way else way_rel.get(w, [])) if r in loc] for w in ws])
        if c:
            out.append({"osm_id": f"relation/{i}", **t, "lon": c[0], "lat": c[1], "area_m2": a})
    return out


def estrai_linee_luoghi(pbf: Path) -> tuple[list[dict], list[dict]]:
    """Linee AT OSM (`power=line|cable`, nome ed estremi) e località (`place=*` con nome, solo nodi) dal PBF."""
    import osmium
    linee = {}
    for o in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(
            osmium.filter.TagFilter(("power", "line"), ("power", "cable"))):
        refs = [n.ref for n in o.nodes]
        if len(refs) >= 2:
            linee[o.id] = ({k: o.tags[k] for k in ("name", "ref", "voltage", "operator") if k in o.tags},
                           refs[0], refs[-1])
    serve = {r for _, a, b in linee.values() for r in (a, b)}
    loc, luoghi = {}, []
    tipi = {"city", "town", "village", "hamlet", "suburb", "neighbourhood", "quarter", "locality",
            "isolated_dwelling", "farm", "borough"}
    for o in osmium.FileProcessor(str(pbf), osmium.osm.NODE):
        if o.id in serve:
            loc[o.id] = (round(o.location.lon, 6), round(o.location.lat, 6))
        if "place" in o.tags and "name" in o.tags and o.tags["place"] in tipi:
            luoghi.append({"name": o.tags["name"], "place": o.tags["place"], "lon": round(o.location.lon, 6),
                           "lat": round(o.location.lat, 6)})
    return ([{"id": i, **t, "a": loc.get(a), "b": loc.get(b)} for i, (t, a, b) in linee.items()], luoghi)


def geojson_osm(sottostazioni: list[dict], data_pbf: str = "") -> dict:
    """Estratto delle sottostazioni come GeoJSON (ODbL)."""
    return {"type": "FeatureCollection", "attribuzione": ATTRIBUZIONE_OSM, "licenza": LICENZA_OSM,
            "fonte": f"OpenStreetMap, estratto Italia di openstreetmap.fr {data_pbf}".strip(),
            "features": [{"type": "Feature", "geometry": {"type": "Point",
                                                          "coordinates": [round(f["lon"], 6), round(f["lat"], 6)]},
                          "properties": {k: v for k, v in f.items() if k not in ("lon", "lat")}}
                         for f in sottostazioni]}


# ------------------------------------------------------------------------------------- dati e-distribuzione

def leggi_edistribuzione(cartella: Path, attuali: dict, successivi: dict | None = None):
    """Legge i JSON grezzi per provincia (`grezzi/PPP.json` di cabine_edistribuzione.py).

    Restituisce (cabine, trasformatori, mappa_codici):
    - cabine: {cod: {"nome", "province": set, "comuni": set(ISTAT attuali)}}
    - trasformatori: [(istat_attuale, cod_cabina, cod_trasformatore, livello, comune_ed)] senza doppioni
    - mappa_codici: {istat_ed: (istat_attuale, modo)}
    """
    cabine, tr, mappa = {}, {}, {}
    data = None
    for f in sorted(Path(cartella).glob("grezzi/*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        prov = (j.get("_provincia") or {}).get("codice") or j.get("Provincia")
        data = max(data or "", str(j.get("DataRisposta") or "")[:10]) or None
        elenco = j.get("ElencoComuni") or []
        # province attuali dei comuni della richiesta riconosciuti senza dubbi: servono a scegliere tra omonimi
        # (SAN TEODORO in Gallura e non in provincia di Messina)
        prime = [codice_attuale(c.get("CodiceIstat"), c.get("Descrizione") or "", attuali, successivi, prov)[0]
                 for c in elenco]
        vicine = {prov, *(x[:3] for x in prime if x)}
        for c in elenco:
            k = str(c.get("CodiceIstat") or "").zfill(6)
            if k not in mappa or mappa[k][0] is None:
                mappa[k] = codice_attuale(k, c.get("Descrizione") or "", attuali, successivi, vicine)
            ist = mappa[k][0] or k
            for t in c.get("ElencoTrasformatori") or []:
                cp = t.get("CodCabinaPrimaria")
                if not cp:
                    continue
                v = cabine.setdefault(cp, {"nome": (t.get("NomeCabinaPrimaria") or "").strip(), "province": set(),
                                           "comuni": set()})
                v["province"].add(prov)
                v["comuni"].add(ist)
                tr[(ist, cp, t.get("CodTrasformatore"), t.get("IdSezioneATMT"))] = (
                    ist, cp, t.get("CodTrasformatore"), t.get("LivSaturTraformatore"), c.get("Descrizione"))
    return cabine, list(tr.values()), mappa, data


def conteggi_cabina(trasformatori) -> dict:
    """{cod_cabina: {"VERDE": n, …}} contando una volta ogni trasformatore (codice + sezione AT/MT)."""
    visti, out = set(), defaultdict(lambda: dict.fromkeys(LIVELLI, 0))
    for ist, cp, tcod, liv, _ in trasformatori:
        if (cp, tcod) in visti or liv not in LIVELLI:
            continue
        visti.add((cp, tcod))
        out[cp][liv] += 1
    return dict(out)


def criticita_comuni(trasformatori, nomi: dict) -> dict:
    """{istat: {nome, trasf, livello, quota, pieno, strisce, cabine}} con `classe_comune`.
    Un trasformatore che serve due vecchi comuni ora fusi conta una volta."""
    per = defaultdict(dict)
    cab = defaultdict(set)
    for ist, cp, tcod, liv, _ in trasformatori:
        if liv in LIVELLI:
            per[ist][(cp, tcod)] = liv
            cab[ist].add(cp)
    out = {}
    for ist in sorted(per):
        cont = dict.fromkeys(LIVELLI, 0)
        for liv in per[ist].values():
            cont[liv] += 1
        out[ist] = {"nome": nomi.get(ist, ""), "trasf": cont, **classe_comune(cont), "cabine": sorted(cab[ist])}
    return out


# --------------------------------------------------------------------------------------------------- raccordo

SOGLIE = {
    "fascia_m": 3000,          # candidati OSM: dentro i comuni serviti + questa fascia
    "fascia_larga_m": 20000,   # seconda ricerca (solo nome quasi uguale) per le cabine non trovate
    "nome_sicuro": 0.75,       # punteggio del nome per «sicuro»
    "nome_minimo": 0.45,       # sotto: il nome non basta (resta «da_verificare» se il resto torna)
    "bordo_m": 100,            # sottostazione a meno di 100 m dal bordo dell'area GSE → da_verificare
    "copertura_area": 0.5,     # quota dell'area GSE dentro i comuni serviti (fascia 500 m) attesa per la sua cabina
    "punteggio_minimo": 0.30,  # sotto questo punteggio complessivo nessun abbinamento
}


def gestore_ed(rag_soc) -> bool:
    """True se la ragione sociale dell'area GSE è e-distribuzione."""
    return str(rag_soc or "").strip().lower().startswith("e-distribuzione")


def punteggio_coppia(nome: float, tipo: float, vicinanza: float) -> float:
    """Punteggio cabina e-distribuzione ↔ sottostazione OSM (0..1)."""
    return round(0.6 * nome + 0.15 * tipo + 0.25 * vicinanza, 4)


def punteggio_tipo(f: dict) -> float:
    """Quanto la sottostazione OSM somiglia a una cabina primaria di e-distribuzione dagli attributi."""
    op = f.get("operator") or f.get("owner") or ""
    kv = kv_massimo(f.get("voltage"))
    if OPERATORE_ED.search(op):
        return 1.0
    if op and DISTRIBUTORI.search(op):
        return 0.2  # altro distributore
    if re.search(r"TERNA", op, re.I) or f.get("substation") == "transmission":
        return 0.35 if (kv or 0) <= 150 else 0.15
    if f.get("substation") == "distribution":
        return 0.8
    if kv and 40 <= kv <= 150:
        return 0.7
    return 0.4


def nomi_di(f: dict) -> list[str]:
    return [f[k] for k in NOMI_OSM if f.get(k)]


def assegna(punteggi: dict, minimo: float = 0.0) -> dict:
    """Assegnazione globale uno a uno che massimizza la somma dei punteggi (algoritmo ungherese, scipy).

    `punteggi`: {(riga, colonna): punteggio}. Restituisce {riga: colonna} per le coppie con punteggio ≥ `minimo`.
    """
    if not punteggi:
        return {}
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    righe = sorted({r for r, _ in punteggi})
    col = sorted({c for _, c in punteggi})
    ir, ic = {r: i for i, r in enumerate(righe)}, {c: i for i, c in enumerate(col)}
    m = np.zeros((len(righe), len(col)))
    for (r, c), v in punteggi.items():
        m[ir[r], ic[c]] = v
    rr, cc = linear_sum_assignment(m, maximize=True)
    return {righe[a]: col[b] for a, b in zip(rr, cc) if m[a, b] >= minimo and m[a, b] > 0}


def espandi_sigla(nome: str, sigle: dict) -> str:
    """«ME RIVIERA» → «MESSINA RIVIERA» se ME è la sigla di una provincia dei comuni serviti (`sigle`:
    {sigla: nome del capoluogo})."""
    p = normalizza_nome(nome).split()
    if len(p) > 1 and p[0] in sigle:
        return " ".join([sigle[p[0]].upper()] + p[1:])
    return nome


def raccorda(cabine: dict, comuni: dict, sottostazioni: list[dict], aree: list[dict], soglie: dict | None = None,
             province: dict | None = None):
    """Abbina ogni cabina e-distribuzione a una sottostazione OSM e a un'area convenzionale GSE.

    - cabine: {cod: {"nome", "comuni": set(ISTAT attuali)}}
    - comuni: {istat: {"nome", "geom" (UTM m)}}
    - sottostazioni: dizionari OSM (lon, lat, osm_id, name…), già filtrate con `candidata_osm`
    - aree: [{"COD_AC", "RAG_SOC", "geom" (UTM m), "TXT1", "TXT2"}]
    - province: {istat comune: (sigla, nome del capoluogo)} per sciogliere «VI MONTEVIALE», «RA SUD» (facoltativo)
    Metodo: per ogni cabina i candidati OSM stanno nell'unione dei comuni serviti più una fascia di 3 km; punteggio
    coppia = 0,6 nome + 0,15 attributi + 0,25 vicinanza. Ogni candidato cade in un'area GSE; il punteggio cabina ↔
    area è 0,7 × migliore coppia nell'area + 0,3 × quota dell'area dentro i comuni serviti. Un'assegnazione globale
    (ungherese) dà a ogni area di e-distribuzione al più una cabina. Restituisce (righe, diagnostica).
    """
    from shapely import STRtree
    from shapely.geometry import Point
    from shapely.ops import unary_union

    s = dict(SOGLIE, **(soglie or {}))
    xs, ys = utm([f["lon"] for f in sottostazioni], [f["lat"] for f in sottostazioni])
    punti = [Point(x, y) for x, y in zip(list(xs), list(ys))]
    alb_p = STRtree(punti)
    geo_a = [a["geom"] for a in aree]
    alb_a = STRtree(geo_a)
    cod_com = list(comuni)
    alb_c = STRtree([comuni[c]["geom"] for c in cod_com])

    # area GSE e comune di ogni sottostazione
    area_di, bordo_di, comune_di = {}, {}, {}
    for i, p in enumerate(punti):
        for j in alb_a.query(p, predicate="within"):
            area_di[i] = int(j)
            bordo_di[i] = geo_a[j].boundary.distance(p)
            break
        for j in alb_c.query(p, predicate="within"):
            comune_di[i] = cod_com[int(j)]
            break

    coppie = {}       # (cab, i) → (punteggio, nome, vicinanza, distanza)
    unioni = {}
    for cp, v in cabine.items():
        g = [comuni[c]["geom"] for c in v["comuni"] if c in comuni and comuni[c]["geom"] is not None]
        if not g:
            continue
        u = unary_union(g)
        unioni[cp] = u
        generiche = {t for c in v["comuni"] if c in comuni for t in gettoni(comuni[c]["nome"])}
        sigle = {province[c][0]: province[c][1] for c in v["comuni"] if province and c in province}
        nome_ed = espandi_sigla(v["nome"], sigle)
        fascia = u.buffer(s["fascia_m"])
        for i in alb_p.query(fascia, predicate="intersects"):
            i = int(i)
            f = sottostazioni[i]
            d = u.distance(punti[i])
            vic = 1.0 if d == 0 else max(0.0, 1 - d / s["fascia_m"])
            pn = punteggio_nome(nome_ed, nomi_di(f), generiche)
            # nome del comune in cui sta la sottostazione (utile per quelle senza nome): vale al più 0,6
            cl = comune_di.get(i)
            if cl:
                pn = max(pn, round(0.6 * punteggio_nome(nome_ed, [comuni[cl]["nome"]]), 4))
            coppie[(cp, i)] = (punteggio_coppia(pn, punteggio_tipo(f), vic), pn, vic, d)

    # seconda ricerca, più larga (20 km), per le cabine senza un nome ben riconosciuto: i comuni serviti noti possono
    # essere incompleti (Torino manca) o la cabina stare lontano. Vale solo un nome quasi uguale; vicinanza 0.
    migliori_nome = defaultdict(float)
    for (cp, i), val in coppie.items():
        migliori_nome[cp] = max(migliori_nome[cp], val[1])
    for cp, u in unioni.items():
        if migliori_nome[cp] >= s["nome_sicuro"]:
            continue
        for i in alb_p.query(u.buffer(s["fascia_larga_m"]), predicate="intersects"):
            i = int(i)
            if (cp, i) in coppie:
                continue
            pn = punteggio_nome(cabine[cp]["nome"], nomi_di(sottostazioni[i]))
            if pn >= 0.9:
                coppie[(cp, i)] = (punteggio_coppia(pn, punteggio_tipo(sottostazioni[i]), 0.0), pn, 0.0,
                                   u.distance(punti[i]))

    # cabina ↔ area GSE (solo aree di e-distribuzione)
    ed = [j for j, a in enumerate(aree) if gestore_ed(a.get("RAG_SOC"))]
    ed_set = set(ed)
    copertura = {}
    for cp, u in unioni.items():
        ub = u.buffer(500)
        for j in alb_a.query(u, predicate="intersects"):
            j = int(j)
            if j in ed_set and geo_a[j].area > 0:
                q = geo_a[j].intersection(ub).area / geo_a[j].area
                if q > 0.05:
                    copertura[(cp, j)] = q
    migliore = {}     # (cab, area) → (punteggio coppia, indice OSM)
    for (cp, i), (pc, *_r) in coppie.items():
        j = area_di.get(i)
        if j is None or j not in ed_set:
            continue
        if pc > migliore.get((cp, j), (-1, None))[0]:
            migliore[(cp, j)] = (pc, i)
    punt_area = {}
    for k in set(migliore) | set(copertura):
        pc = migliore.get(k, (0, None))[0]
        punt_area[k] = round(0.7 * pc + 0.3 * copertura.get(k, 0), 4)
    scelta = assegna(punt_area, s["punteggio_minimo"])

    # coppie migliori senza vincolo di area (per i casi fuori dalle aree e-distribuzione)
    per_cab = defaultdict(list)
    for (cp, i), val in coppie.items():
        per_cab[cp].append((val[0], i))
    for v in per_cab.values():
        v.sort(reverse=True)
    osm_usati = {migliore[(cp, j)][1] for cp, j in scelta.items() if (cp, j) in migliore}

    osm_di = {cp: migliore[(cp, j)][1] for cp, j in scelta.items() if (cp, j) in migliore}
    righe, diag = [], Counter()
    for cp, v in sorted(cabine.items()):
        r = {"cod_cp_ed": cp, "nome_cp_ed": v["nome"], "comuni_serviti": ";".join(sorted(v["comuni"])),
             "cod_ac": "", "gestore": "", "osm_id": "", "osm_nome": "", "lon": None, "lat": None,
             "punteggio_nome": None, "distanza_m": None, "esito": "senza_posizione", "nota": ""}
        j = scelta.get(cp)
        i = migliore.get((cp, j), (0, None))[1] if j is not None else None
        note = []
        if i is None and per_cab.get(cp):
            # nessuna sottostazione nell'area assegnata (o nessuna area): la migliore libera con nome quasi uguale,
            # anche se sta in un'area già data a un'altra cabina (PALAU e PALAU 2 nella stessa area GSE) o fuori
            # dalle aree di e-distribuzione; il codice è quello dell'area che la contiene
            pc, i2 = next(((p, x) for p, x in per_cab[cp] if x not in osm_usati), (0, None))
            if i2 is not None and coppie[(cp, i2)][1] >= s["nome_sicuro"]:
                i = i2
                osm_usati.add(i)
                j2 = area_di.get(i)
                if j2 is None:
                    note.append("sottostazione fuori da tutte le aree GSE")
                elif j2 not in ed_set:
                    note.append("sottostazione fuori dalle aree e-distribuzione")
                else:
                    altra = next((c for c, a in scelta.items() if a == j2), None)
                    note.append(f"area GSE condivisa con {altra} ({cabine[altra]['nome']})" if altra else
                                "area GSE non assegnata dal calcolo globale")
                j = j2
        if i is None and per_cab.get(cp):
            # stessa cabina con due codici di unità territoriali diverse (LUNI: DY… in Liguria, DX… in Toscana):
            # stesso nome, sottostazione già data all'altro codice → si condivide
            for p_, x in per_cab[cp]:
                altro = next((c for c, ii in osm_di.items() if ii == x), None)
                if altro and coppie[(cp, x)][1] >= 0.95 and gettoni(cabine[altro]["nome"]) == gettoni(v["nome"]) \
                        and coppie[(cp, x)][3] <= s["fascia_m"]:
                    i, j = x, area_di.get(x)
                    note.append(f"stessa sottostazione di {altro} (stesso nome, altro codice e-distribuzione)")
                    break
        if i is not None:
            osm_di[cp] = i
        if j is not None:
            r["cod_ac"], r["gestore"] = aree[j]["COD_AC"], aree[j].get("RAG_SOC", "")
        if i is None:
            if j is not None:
                note.append(f"area GSE stimata dai comuni serviti (copertura {copertura.get((cp, j), 0):.2f}), "
                            "nessuna sottostazione OSM riconosciuta")
            r["nota"] = "; ".join(note)
            diag["senza_posizione"] += 1
            righe.append(r)
            continue
        f = sottostazioni[i]
        pc, pn, vic, d = coppie[(cp, i)]
        r.update(osm_id=f["osm_id"], osm_nome=f.get("name") or "", lon=round(f["lon"], 6), lat=round(f["lat"], 6),
                 punteggio_nome=pn, distanza_m=round(d))
        alternative = [p for p, x in per_cab[cp] if x != i]
        margine = pc - (alternative[0] if alternative else 0)
        sicuro = (pn >= s["nome_sicuro"] and vic >= 0.5 and j is not None and j in ed_set)
        if j is not None and bordo_di.get(i, 1e9) < s["bordo_m"]:
            note.append(f"a {bordo_di[i]:.0f} m dal bordo dell'area GSE")
            sicuro = False
        if j is None:
            note.append("nessuna area GSE contiene la sottostazione")
        elif j not in ed_set:
            note.append(f"area GSE di un altro gestore ({aree[j].get('RAG_SOC')})")
            sicuro = False
        if pn < s["nome_sicuro"]:
            note.append(f"nome poco simile ({pn:.2f})" if pn >= s["nome_minimo"] else
                        f"nome diverso o assente ({pn:.2f}): scelta per esclusione e posizione")
        if j is not None and copertura.get((cp, j), 1) < s["copertura_area"]:
            note.append(f"area GSE poco dentro i comuni serviti ({copertura.get((cp, j), 0):.2f})")
            sicuro = False
        if margine < 0.05 and alternative and pn < 0.95:
            note.append("altra sottostazione quasi equivalente")
            sicuro = False
        r["esito"] = "sicuro" if sicuro else "da_verificare"
        r["nota"] = "; ".join(note)
        diag[r["esito"]] += 1
        righe.append(r)
    return righe, {"esiti": dict(diag), "aree_assegnate": len(scelta), "coppie_candidate": len(coppie)}


def righe_solo_gse(aree: list[dict], usate: set, sottostazioni: list[dict]) -> list[dict]:
    """Aree GSE senza cabina e-distribuzione abbinata: una riga ciascuna, con la sottostazione OSM più plausibile
    che vi ricade (distributore e alta tensione prima, poi nome, poi superficie)."""
    from shapely import STRtree
    from shapely.geometry import Point
    xs, ys = utm([f["lon"] for f in sottostazioni], [f["lat"] for f in sottostazioni])
    punti = [Point(x, y) for x, y in zip(list(xs), list(ys))]
    alb = STRtree(punti)
    out = []
    for a in aree:
        if a["COD_AC"] in usate:
            continue
        cand = [int(i) for i in alb.query(a["geom"], predicate="contains")]

        def peso(i):
            f = sottostazioni[i]
            nome_txt = " ".join(str(a.get(k) or "") for k in ("TXT1", "TXT2"))
            pn = punteggio_nome(re.sub(r"^\S*\d{6,}\S*\s*-?\s*", "", nome_txt), nomi_di(f)) if nome_txt.strip() else 0
            return (punteggio_tipo(f) + pn + (0.2 if f.get("name") else 0) + min(f.get("area_m2") or 0, 20000) / 1e5)

        r = {"cod_ac": a["COD_AC"], "gestore": a.get("RAG_SOC", ""), "cod_cp_ed": "", "nome_cp_ed": "",
             "comuni_serviti": "", "osm_id": "", "osm_nome": "", "lon": None, "lat": None, "punteggio_nome": None,
             "distanza_m": None, "esito": "solo_gse",
             "nota": " ".join(x for x in (str(a.get("TXT1") or "").strip(), str(a.get("TXT2") or "").strip()) if x)}
        if cand:
            i = max(cand, key=peso)
            f = sottostazioni[i]
            r.update(osm_id=f["osm_id"], osm_nome=f.get("name") or "", lon=round(f["lon"], 6), lat=round(f["lat"], 6))
            if len(cand) > 1:
                r["nota"] = (r["nota"] + "; " if r["nota"] else "") + f"{len(cand)} sottostazioni OSM nell'area"
        out.append(r)
    return out


# colonne del contratto, più «nota» in fondo (motivo di «da_verificare», area stimata, …)
COLONNE_RACCORDO = ["cod_ac", "gestore", "cod_cp_ed", "nome_cp_ed", "comuni_serviti", "osm_id", "osm_nome", "lat",
                    "lon", "punteggio_nome", "distanza_m", "esito", "data_raccordo", "versione_ac", "nota"]


def scrivi_raccordo(righe: list[dict], percorso: Path, data: str, versione_ac: str) -> None:
    with open(percorso, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLONNE_RACCORDO, extrasaction="ignore")
        w.writeheader()
        for r in righe:
            w.writerow({**{k: ("" if r.get(k) is None else r.get(k)) for k in COLONNE_RACCORDO},
                        "data_raccordo": data, "versione_ac": versione_ac})


def geojson_cabine(righe: list[dict], conteggi: dict, data_saturazione: str, data: str, versione_ac: str) -> dict:
    """Punti delle cabine (solo le righe con posizione) con livello peggiore e conteggi dei trasformatori."""
    feats = []
    for r in righe:
        if r.get("lon") is None:
            continue
        cont = conteggi.get(r.get("cod_cp_ed"))
        p = {k: ("" if r.get(k) is None else r.get(k)) for k in COLONNE_RACCORDO if k not in ("lat", "lon")}
        p.update(data_raccordo=data, versione_ac=versione_ac,
                 livello=livello_peggiore([k for k, n in cont.items() if n]) if cont else None,
                 trasf=cont, data_saturazione=data_saturazione if cont else None)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                      "properties": p})
    return {"type": "FeatureCollection", "attribuzione": ATTRIBUZIONE_OSM, "licenza": LICENZA_RACCORDO,
            "fonti": [FONTE_ED, FONTE_GSE, "OpenStreetMap (power=substation)"], "data": data, "features": feats}


# ------------------------------------------------------------------------------- aree GSE (solo nel workspace)

def scarica_aree_gse(dest: Path, client=None) -> list[Path]:
    """Scarica UNA volta i poligoni delle aree convenzionali (strato 0, EPSG:4326, ~2 m di semplificazione) nella
    cartella di lavoro `dest`. Licenza CC BY-NC-SA 3.0 IT: i file servono solo al calcolo, **mai nel repository né
    sul server**."""
    import httpx
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    c = client or httpx.Client(timeout=300)
    n = c.get(f"{SERVIZIO_GSE}/query", params={"where": "1=1", "returnCountOnly": "true", "f": "json"}).json()["count"]
    out = []
    for off in range(0, n, 500):
        r = c.get(f"{SERVIZIO_GSE}/query", params={
            "where": "1=1", "outFields": "COD_AC,RAG_SOC,P_CAB_PRI,T_CAB_PRI,COD_CONSEG,TXT1,TXT2",
            "returnGeometry": "true", "outSR": "4326", "maxAllowableOffset": "0.00002", "geometryPrecision": "6",
            "orderByFields": "FID", "resultOffset": str(off), "resultRecordCount": "500", "f": "geojson"})
        r.raise_for_status()
        p = dest / f"L0_{off}.geojson"
        p.write_bytes(r.content)
        out.append(p)
    return out


def leggi_aree_gse(cartella: Path) -> list[dict]:
    """Aree GSE dai GeoJSON scaricati con `scarica_aree_gse`, con geometria in metri UTM 32N (codici doppi uniti)."""
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    from shapely.validation import make_valid
    per = {}
    for f in sorted(Path(cartella).glob("L0_*.geojson")):
        for ft in json.loads(f.read_text(encoding="utf-8"))["features"]:
            if not ft.get("geometry"):
                continue
            pr = ft["properties"]
            g = transform(lambda x, y, z=None: utm(x, y), make_valid(shape(ft["geometry"]))).buffer(0)
            if pr["COD_AC"] in per:
                per[pr["COD_AC"]]["geom"] = unary_union([per[pr["COD_AC"]]["geom"], g])
            else:
                per[pr["COD_AC"]] = {**{k: (v or "").strip() if isinstance(v, str) else v for k, v in pr.items()},
                                     "geom": g}
    return list(per.values())


def versione_aree(aree: list[dict]) -> str:
    """Etichetta della versione GSE: nome dello strato e data di consegna più frequente (COD_CONSEG)."""
    c = Counter(a.get("COD_CONSEG") for a in aree if (a.get("COD_CONSEG") or "").strip())
    return f"AC_Comuni_2025 (COD_CONSEG {c.most_common(1)[0][0]})" if c else "AC_Comuni_2025"


# ------------------------------------------------------------------------------- comuni non concessionari

def scarica_comuni_gestiti(client=None) -> list[dict]:
    """Attributi dello strato e-distribuzione `View_ComuniGestitiED2021Is` (comuni ISTAT 2021, `servitoed`)."""
    import httpx
    c = client or httpx.Client(timeout=120)
    out, off = [], 0
    while True:
        j = c.get(f"{COMUNI_ED}/query", params={
            "where": "1=1", "outFields": "fid,pro_com_t,comune,cod_reg,servitoed", "returnGeometry": "false",
            "orderByFields": "fid", "resultOffset": str(off), "resultRecordCount": "1000", "f": "json"}).json()
        feats = j.get("features") or []
        out += [f["attributes"] for f in feats]
        if len(feats) < 1000:
            return out
        off += 1000


def non_concessionari(righe: list[dict], attuali: dict, successivi: dict | None, regioni: dict,
                      con_trasformatori: set | None = None) -> list[dict]:
    """Comuni con `servitoed = 0` in tutte le parti, riportati al codice attuale. Un comune attuale nato dalla
    fusione di comuni serviti e non serviti resta «concessionario» (lo serve in parte e-distribuzione).
    `con_trasformatori`: comuni che compaiono comunque in `comuniServiti` (alcuni comuni milanesi di Unareti hanno
    trasformatori e-distribuzione): si segnalano con `con_trasformatori_ed = true`."""
    stato = defaultdict(set)
    nome21 = {}
    for r in righe:
        k = str(r.get("pro_com_t") or "").strip()
        if not k:
            continue
        stato[k].add(int(r.get("servitoed") or 0))
        nome21[k] = r.get("comune") or ""
    per_att = defaultdict(list)
    for k, st in stato.items():
        att, modo = codice_attuale(k, nome21[k], attuali, successivi)
        per_att[att or f"?{k}"].append((k, st, modo))
    out = []
    for att, lst in sorted(per_att.items()):
        if all(st == {0} for _, st, _ in lst):
            for k, _, modo in lst:
                out.append({"istat": att if not att.startswith("?") else None, "istat_2021": k,
                            "nome": attuali.get(att, nome21[k]), "nome_2021": nome21[k],
                            "regione": regioni.get(att, ""), "modo": modo,
                            "con_trasformatori_ed": bool(con_trasformatori and att in con_trasformatori)})
    return out


# ------------------------------------------------------------------------------------------- tutto insieme

def costruisci(dati_cp: Path, osm: Path, aree_gse: Path, mappa: Path, istat: Path, dest: Path,
               comuni_gestiti: list[dict] | None = None, data: str | None = None,
               linee: list[dict] | None = None, luoghi: list[dict] | None = None,
               documenti: list[dict] | None = None) -> dict:
    """Produce in `dest` i file del raccordo (vedi README della fase 7) e restituisce un riepilogo numerico.

    - dati_cp: cartella di cabine_edistribuzione.py (con `grezzi/PPP.json`)
    - osm: PBF dell'Italia (estrazione con pyosmium) oppure JSON già estratto con `estrai_sottostazioni`
    - aree_gse: cartella con i GeoJSON di `scarica_aree_gse` (solo workspace)
    - mappa: `fase5-sito/sito/dati/mappa` (confini dei comuni ISTAT 2026 generalizzati)
    - istat: cartella con Elenco-comuni-italiani.csv e i CSV dei soppressi e delle variazioni
    - comuni_gestiti: attributi di View_ComuniGestitiED2021Is (se None non si scrive il file dei non concessionari)
    - linee, luoghi, documenti: se dati, secondo passaggio di verifica (`secondo_passaggio`) prima di scrivere
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    data = data or dt.date.today().isoformat()
    attuali, province, regioni = leggi_elenco_istat(next(Path(istat).rglob("Elenco-comuni-italiani.csv")))
    succ = leggi_successivi_istat(istat)
    cab, tr, mappa_cod, data_sat = leggi_edistribuzione(dati_cp, attuali, succ)
    comuni = leggi_comuni_mappa(mappa)
    aree = leggi_aree_gse(aree_gse)
    versione = versione_aree(aree)
    osm = Path(osm)
    sott = estrai_sottostazioni(osm) if osm.suffix == ".pbf" else json.loads(osm.read_text(encoding="utf-8"))
    if isinstance(sott, dict):  # GeoJSON
        sott = [{**f["properties"], "lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1]}
                for f in sott["features"]]
    cand = [f for f in sott if candidata_osm(f)]
    (dest / "osm_sottostazioni.geojson").write_text(
        json.dumps(geojson_osm(cand, f"(letto il {data})"), ensure_ascii=False), encoding="utf-8")

    righe, diag = raccorda(cab, comuni, cand, aree, province=province)
    usate = {r["cod_ac"] for r in righe if r["cod_ac"]}
    righe += righe_solo_gse(aree, usate, cand)
    verifica = None
    if linee is not None or luoghi is not None or documenti is not None:
        senza_dati = None
        if comuni_gestiti is not None:  # serviti da e-distribuzione ma assenti da comuniServiti (Torino…)
            serviti = {codice_attuale(x.get("pro_com_t"), x.get("comune") or "", attuali, succ)[0]
                       for x in comuni_gestiti if int(x.get("servitoed") or 0) == 1 and str(x.get("pro_com_t") or "").strip()}
            senza_dati = serviti - {t[0] for t in tr} - {None}
        verifica = secondo_passaggio(righe, cab, comuni, aree, cand, linee or [], luoghi or [], province,
                                     documenti or [], data, senza_dati)
    righe.sort(key=lambda r: (r["cod_ac"] or "~", r["cod_cp_ed"]))
    scrivi_raccordo(righe, dest / "raccordo_cp.csv", data, versione)
    cont = conteggi_cabina(tr)
    (dest / "cabine_primarie.geojson").write_text(
        json.dumps(geojson_cabine(righe, cont, data_sat, data, versione), ensure_ascii=False), encoding="utf-8")
    crit = criticita_comuni(tr, attuali)
    (dest / "comuni_criticita.json").write_text(json.dumps(
        {"data": data_sat, "fonte": FONTE_ED, "regola": REGOLA_CRITICITA, "comuni": crit},
        ensure_ascii=False), encoding="utf-8")
    nc = None
    if comuni_gestiti is not None:
        nc = non_concessionari(comuni_gestiti, attuali, succ, regioni, set(crit))
        (dest / "comuni_non_concessionari.json").write_text(json.dumps(
            {"fonte": f"e-distribuzione S.p.A., strato View_ComuniGestitiED2021Is (servitoed = 0) – {COMUNI_ED}",
             "nota": "Comuni ISTAT 2021 ricondotti ai codici attuali con le tabelle ISTAT (soppressi, variazioni) "
                     "e, in mancanza, con il nome.",
             "data": data, "comuni": nc}, ensure_ascii=False), encoding="utf-8")
    return {"cabine": len(cab), "trasformatori": len(tr), "esiti": Counter(r["esito"] for r in righe),
            "diagnostica": diag, "versione_ac": versione, "data_saturazione": data_sat,
            "comuni_criticita": len(crit), "non_concessionari": len(nc) if nc is not None else None,
            "codici_istat": Counter(m for _, m in mappa_cod.values()), "osm_candidate": len(cand), "verifica": verifica,
            "osm_tutte": len(sott), "righe": righe, "aree": aree, "cabine_ed": cab, "trasf": tr,
            "mappa_codici": mappa_cod, "comuni": comuni, "attuali": attuali, "regioni": regioni}


# ------------------------------------------------------------------------- secondo passaggio (prove indipendenti)

def parti_linea(nome: str) -> list[str]:
    """Nomi delle stazioni nel nome di una linea AT OSM: «Calvizzano-CP Patria» → ["Calvizzano", "CP Patria"],
    «Linea 132 kV Camin – Padova Fiera» → ["Camin", "Padova Fiera"]. Le derivazioni «All.»/«Der.» restano nel nome."""
    s = re.sub(r"^\s*(linea|elettrodotto|el\.)\s*", "", str(nome or ""), flags=re.I)
    s = re.sub(r"\b\d+\s*kV\b", "", s, flags=re.I)
    parti = [p.strip(" .,;()") for p in re.split(r"\s*[-–—/]\s*", s)]
    return [p for p in parti if p and not re.fullmatch(r"[\d.\s]*", p)]


def prova_linee(nome_cabina: str, linee: list[dict], altrove=lambda p: False, concorrenti=(),
                soglia: float = 0.8) -> dict:
    """Prova dai nomi delle linee AT che arrivano a una sottostazione.

    Una linea «A - B» tocca due stazioni, quindi il nome della cabina nella linea non basta: la linea conferma se una
    parte è la cabina cercata (punteggio ≥ `soglia`, e nessuna delle `concorrenti`, le altre cabine e-distribuzione,
    le somiglia di più) e **tutte le altre parti sono stazioni già collocate altrove** (`altrove(parte)` vero: una
    sottostazione OSM con quel nome a più di 1 km, o una cabina già sicura). È contraria se una parte non collocata
    altrove somiglia (≥ 0,9) a un'altra cabina e nessuna parte somiglia alla cabina cercata.
    Restituisce {"conferma": [nomi linea], "contro": [nomi linea]}.
    """
    out = {"conferma": set(), "contro": set()}
    for l in linee:
        parti = parti_linea(l.get("name") or "")
        if len(parti) < 2:
            continue
        punt = [punteggio_nome(nome_cabina, [q]) for q in parti]
        mie = [k for k, x in enumerate(punt) if x >= soglia
               and not any(punteggio_nome(c, [parti[k]]) > x for c in concorrenti)]
        if mie:
            k = mie[0]
            if all(altrove(q) for j, q in enumerate(parti) if j != k):
                out["conferma"].add(l["name"])
        elif any(not altrove(q) and any(punteggio_nome(c, [q]) >= 0.9 for c in concorrenti) for q in parti):
            out["contro"].add(l["name"])
    return {k: sorted(v) for k, v in out.items()}


def prova_luoghi(nome_cabina: str, luoghi_vicini: list[dict], escludi=()) -> list[str]:
    """Località OSM (place=*) vicine alla sottostazione con il nome della cabina (es. VACCARO, RUGGIANELLO).
    `escludi`: nomi da non contare (il comune che contiene la sottostazione, che non distingue due CP dello stesso
    comune)."""
    esc = {" ".join(gettoni(e)) for e in escludi}
    return sorted({p["name"] for p in luoghi_vicini
                   if " ".join(gettoni(p["name"])) not in esc and punteggio_nome(nome_cabina, [p["name"]]) >= 0.9})


def misura_comuni(area_geom, unione_comuni, fascia: float = 500.0) -> tuple[float, float]:
    """(quota dell'area GSE dentro i comuni serviti, quota dei comuni serviti dentro l'area), con una fascia per i
    confini generalizzati."""
    if area_geom is None or unione_comuni is None or area_geom.area == 0:
        return 0.0, 0.0
    inter = area_geom.intersection(unione_comuni.buffer(fascia)).area
    return round(inter / area_geom.area, 4), round(min(1.0, inter / max(unione_comuni.area, 1)), 4)


def decidi_verifica(prove: dict) -> tuple[str, str]:
    """Esito del secondo passaggio per una cabina abbinata, dalle prove indipendenti dal nome.

    prove: {"quota_area": float, "migliore_per_area": bool, "linee": {"conferma": [...], "contro": [...]},
            "luoghi": [...], "nome": float, "esclusiva": bool, "documenti": [...], "area_ed": bool,
            "quota_senza_dati": float}
    Regole: area di un altro gestore → resta da verificare; nome uguale (o ≥ 0,8 e unica candidata nell'area) e area
    dentro comuni serviti da e-distribuzione ma senza dati (Torino) → sicuro; area che non tocca i comuni serviti (quota < 0,05) → errore; una linea AT col nome della cabina, una
    località omonima vicina o un documento → sicuro se l'area tocca i comuni serviti (≥ 0,2) e nessuna linea è
    contraria; altrimenti la sovrapposizione dei comuni basta se la cabina è la migliore per quell'area (quota ≥ 0,6)
    e il nome è almeno in parte simile o la sottostazione è l'unica candidata nell'area.
    Restituisce (esito, motivo) con esito in {"sicuro", "errore", "da_verificare"}.
    """
    qa = prove.get("quota_area", 0)
    lin = prove.get("linee") or {}
    if prove.get("area_ed") is False:
        return "da_verificare", "area GSE di un altro gestore: " + decidi_verifica({**prove, "area_ed": True})[1]
    nome = prove.get("nome", 0)
    if qa < 0.2 and prove.get("quota_senza_dati", 0) >= 0.8 and not lin.get("contro") \
            and (nome >= 0.95 or (nome >= 0.8 and prove.get("esclusiva"))):
        return "sicuro", (f"nome uguale; area GSE per {prove['quota_senza_dati']:.0%} in comuni serviti da "
                          "e-distribuzione ma senza dati comuniServiti (Torino), nessun'altra cabina nell'area")
    if qa < 0.05:
        return "errore", f"l'area GSE non tocca i comuni serviti (quota {qa:.2f})"
    forti = []
    if lin.get("conferma"):
        forti.append("linea AT «" + lin["conferma"][0] + "»")
    if prove.get("luoghi"):
        forti.append("località vicina «" + prove["luoghi"][0] + "»")
    if prove.get("documenti"):
        forti.append(prove["documenti"][0])
    if forti and qa >= 0.2 and not lin.get("contro"):
        return "sicuro", "; ".join(forti) + f"; area GSE nei comuni serviti {qa:.2f}"
    if lin.get("contro") and not lin.get("conferma"):
        return "da_verificare", "linea AT verso stazioni già collocate altrove: «" + lin["contro"][0] + "»"
    if prove.get("migliore_per_area") and qa >= 0.6 and (prove.get("nome", 0) >= 0.45 or prove.get("esclusiva")):
        perche = "nome in parte simile" if prove.get("nome", 0) >= 0.45 else "unica sottostazione candidata nell'area"
        return "sicuro", (f"comuni: area GSE per {qa:.0%} nei comuni serviti e cabina più coerente con l'area; "
                          + perche)
    return "da_verificare", (f"prove deboli (area nei comuni serviti {qa:.2f}"
                             + (", altra cabina più coerente con l'area" if not prove.get("migliore_per_area") else "")
                             + ")")


def schede_piano_sviluppo(testo: str, fonte: str) -> list[dict]:
    """Dal testo (pdftotext -layout) dell'appendice del Piano di Sviluppo e-distribuzione: per ogni scheda il nome
    delle CP citate («CP Gallo», «Cabina Primaria di Basciano») e i comuni nominati («nel Comune di Alfonsine»)."""
    out = []
    for blocco in re.split(r"SCHEDA INTERVENTO", testo)[1:]:
        cp = set(re.findall(r"\bC\.?P\.?\s+[«“\"]?\s*([A-ZÀ-Ú][\w'À-ú.]*(?:\s+(?:[A-ZÀ-Ú][\w'À-ú.]*|di|del|della|d'))*)",
                            blocco))
        cp |= set(re.findall(r"Cabina Primaria (?:di |della |del )?([A-ZÀ-Ú][\w'À-ú]*(?:\s+[A-ZÀ-Ú][\w'À-ú]*)*)",
                             blocco))
        com = set(re.findall(r"[Cc]omun[ei] di ([A-ZÀ-Ú][\w'À-ú]*(?:[\s-]+(?:[A-ZÀ-Ú][\w'À-ú]*|di|del|sul|in))*)",
                             blocco))
        if cp:
            titolo = re.search(r"[“\"]\s*(.+?)\s*[”\"]", blocco)
            out.append({"cp": sorted(cp), "comuni": sorted(com), "fonte": f"{fonte}, scheda «{titolo.group(1) if titolo else '?'}»"})
    return out


def secondo_passaggio(righe: list[dict], cabine: dict, comuni: dict, aree: list[dict], sottostazioni: list[dict],
                      linee: list[dict], luoghi: list[dict], province: dict | None = None,
                      documenti: list[dict] | None = None, data: str = "",
                      comuni_senza_dati: set | None = None) -> dict:
    """Verifica delle righe `da_verificare` e `senza_posizione` con prove indipendenti dall'abbinamento per nome:
    comuni serviti ↔ area GSE, esclusività dell'area, nomi delle linee AT OSM che entrano nella sottostazione,
    località OSM vicine, documenti e-distribuzione. Modifica `righe` sul posto (esito `sicuro`, `corretto` o
    `da_verificare`, prova in `nota`) e restituisce i conteggi prima/dopo e il dettaglio per riga.

    `sottostazioni` sono le candidate passate a `raccorda` (con lon, lat, osm_id, area_m2); `linee`: linee AT OSM con
    `name` e gli estremi `a`, `b` in [lon, lat]; `luoghi`: place=* OSM con name, lon, lat."""
    from shapely import STRtree
    from shapely.geometry import Point
    from shapely.ops import unary_union

    prima = Counter(r["esito"] for r in righe)
    idx_osm = {f["osm_id"]: k for k, f in enumerate(sottostazioni)}
    xs, ys = utm([f["lon"] for f in sottostazioni], [f["lat"] for f in sottostazioni])
    punti = [Point(x, y) for x, y in zip(list(xs), list(ys))]
    alb_p = STRtree(punti)
    geo_a = [a["geom"] for a in aree]
    alb_a = STRtree(geo_a)
    cod_com = list(comuni)
    alb_c = STRtree([comuni[c]["geom"] for c in cod_com])

    def area_di(k):
        for j in alb_a.query(punti[k], predicate="within"):
            return aree[int(j)]
        return None

    def comune_di(k):
        for j in alb_c.query(punti[k], predicate="within"):
            return cod_com[int(j)]
        return None

    senza = [comuni[c]["geom"] for c in (comuni_senza_dati or ()) if c in comuni and comuni[c]["geom"] is not None]
    unione_senza = unary_union(senza) if senza else None
    usate_da = Counter(r["cod_ac"] for r in righe if r.get("cod_cp_ed") and r.get("cod_ac"))
    senza = [comuni[c]["geom"] for c in (comuni_senza_dati or ()) if c in comuni and comuni[c]["geom"] is not None]
    unione_senza = unary_union(senza) if senza else None
    usate_da = Counter(r["cod_ac"] for r in righe if r.get("cod_cp_ed") and r.get("cod_ac"))
    unioni = {}
    for cp, v in cabine.items():
        g = [comuni[c]["geom"] for c in v["comuni"] if c in comuni and comuni[c]["geom"] is not None]
        unioni[cp] = unary_union(g) if g else None
    alb_u_cod = [cp for cp in unioni if unioni[cp] is not None]
    alb_u = STRtree([unioni[cp] for cp in alb_u_cod])

    # per ogni area di e-distribuzione le cabine ordinate per coerenza con i comuni (F = media armonica fra quota
    # dell'area nei comuni serviti e quota dei comuni serviti nell'area); la «migliore» si sceglie escludendo le
    # cabine già collocate con sicurezza in un'altra area
    coerenza = {}
    for a in aree:
        if not gestore_ed(a.get("RAG_SOC")):
            continue
        lst = []
        for j in alb_u.query(a["geom"], predicate="intersects"):
            cp = alb_u_cod[int(j)]
            qa, qc = misura_comuni(a["geom"], unioni[cp])
            lst.append((2 * qa * qc / (qa + qc) if qa + qc else 0, cp))
        coerenza[a["COD_AC"]] = sorted(lst, reverse=True)
    posto_sicuro = {r["cod_cp_ed"]: r["cod_ac"] for r in righe if r.get("cod_cp_ed") and r["esito"] == "sicuro"}

    def migliore(cod_ac):
        for f, cp in coerenza.get(cod_ac, []):
            if posto_sicuro.get(cp, cod_ac) == cod_ac:
                return cp
        return None

    estremi, rif = [], []
    for l in linee:
        if not l.get("name"):
            continue
        for e in (l.get("a"), l.get("b")):
            if e:
                x, y = utm(e[0], e[1])
                estremi.append(Point(float(x), float(y)))
                rif.append(l)
    alb_l = STRtree(estremi) if estremi else None
    lx, ly = utm([p["lon"] for p in luoghi], [p["lat"] for p in luoghi]) if luoghi else ([], [])
    pl = [Point(x, y) for x, y in zip(list(lx), list(ly))]
    alb_luoghi = STRtree(pl) if pl else None

    def linee_di(k):
        if alb_l is None:
            return []
        r = 150 + math.sqrt(sottostazioni[k].get("area_m2") or 0)
        return list({id(rif[int(j)]): rif[int(j)] for j in alb_l.query(punti[k].buffer(r))}.values())

    def luoghi_di(k, raggio=1500):
        if alb_luoghi is None:
            return []
        return [luoghi[int(j)] for j in alb_luoghi.query(punti[k].buffer(raggio))]

    # stazioni con nome collocate: sottostazioni OSM candidate con nome e posizioni delle cabine già abbinate
    collocate = [(punti[k], " ".join(gettoni(n))) for k, f in enumerate(sottostazioni) for n in nomi_di(f)]
    for r in righe:
        if r.get("cod_cp_ed") and r.get("osm_id") in idx_osm and r["esito"] == "sicuro":
            collocate.append((punti[idx_osm[r["osm_id"]]], " ".join(gettoni(cabine[r["cod_cp_ed"]]["nome"]))))
    per_gettone = defaultdict(list)
    for pt, n in collocate:
        if n:
            per_gettone[n.split()[0]].append((pt, n))

    def altrove_da(k):
        def altrove(parte):
            g = gettoni(parte)
            if not g:
                return True
            for pt, n in per_gettone.get(g[0], []) + per_gettone.get(g[-1], []):
                if pt.distance(punti[k]) > 1000 and punteggio_nome(parte, [n]) >= 0.9:
                    return True
            return False
        return altrove

    tutti_nomi = {cp: cabine[cp]["nome"] for cp in cabine}

    def nome_esteso(cp):
        sig = {province[c][0]: province[c][1] for c in cabine[cp]["comuni"] if province and c in province}
        return espandi_sigla(cabine[cp]["nome"], sig)

    def prove(cp, k):
        a = area_di(k)
        qa = misura_comuni(a["geom"], unioni.get(cp))[0] if a is not None else 0.0
        ne = nome_esteso(cp)
        concorrenti = [n for c, n in tutti_nomi.items() if c != cp and gettoni(n) != gettoni(cabine[cp]["nome"])]
        cl = comune_di(k)
        ccand = [int(j) for j in alb_p.query(a["geom"], predicate="contains")] if a is not None else []
        docs = []
        for d in documenti or []:
            if any(punteggio_nome(ne, [x]) >= 0.9 for x in d["cp"]) and cl and \
                    any(chiave_comune(x) == chiave_comune(comuni[cl]["nome"]) for x in d["comuni"]):
                docs.append(f"documento: {d['fonte']} (comune {comuni[cl]['nome']})")
        qs = misura_comuni(a["geom"], unione_senza)[0] if a is not None and unione_senza is not None else 0.0
        if a is not None and usate_da.get(a["COD_AC"], 0) > 1:
            qs = 0.0  # area con più cabine: il nome da solo non basta
        return {"area": a, "quota_area": qa, "quota_senza_dati": qs,
                "area_ed": a is None or gestore_ed(a.get("RAG_SOC")), "migliore_per_area": a is not None and migliore(a["COD_AC"]) == cp,
                "linee": prova_linee(ne, linee_di(k), altrove_da(k), concorrenti),
                "luoghi": prova_luoghi(ne, luoghi_di(k), [comuni[cl]["nome"]] if cl else []),
                "nome": punteggio_nome(ne, nomi_di(sottostazioni[k])), "esclusiva": len(ccand) <= 1,
                "documenti": docs}

    occupate = {r["osm_id"] for r in righe if r.get("cod_cp_ed") and r.get("osm_id")}
    aree_ed_usate = {r["cod_ac"] for r in righe if r.get("cod_cp_ed") and r.get("cod_ac")}
    solo_gse = {r["cod_ac"]: r for r in righe if r["esito"] == "solo_gse"}
    dettaglio = []

    def alternative(cp, escludi, largo=False):
        u = unioni.get(cp)
        if u is None:
            return []
        out = []
        vicini = {int(j) for j in alb_p.query(u.buffer(3000), predicate="intersects")}
        lontani = set()
        if largo and unione_senza is not None:  # cabine «torinesi»: comuni serviti noti incompleti o sbagliati
            ne = nome_esteso(cp)
            lontani = {int(j) for j in alb_p.query(u.buffer(100000), predicate="intersects")} - vicini
            lontani = {k for k in lontani if punteggio_nome(ne, nomi_di(sottostazioni[k])) >= 0.8}
            if not lontani:  # ovunque, ma solo se il nome è uguale e unico in Italia (AIRASCA ha un comune siciliano)
                uguali = [k for k, f in enumerate(sottostazioni) if punteggio_nome(ne, nomi_di(f)) >= 0.95]
                lontani = set(uguali) if len(uguali) == 1 else set()
        for k in sorted(vicini | lontani):
            f = sottostazioni[k]
            if f["osm_id"] in occupate or f["osm_id"] in escludi:
                continue
            a = area_di(k)
            if a is None or not gestore_ed(a.get("RAG_SOC")) or a["COD_AC"] in aree_ed_usate:
                continue
            pv = prove(cp, k)
            esito, motivo = decidi_verifica(pv)
            if esito == "sicuro" and (pv["linee"]["conferma"] or pv["luoghi"] or pv["documenti"] or pv["nome"] >= 0.75):
                out.append((len(pv["linee"]["conferma"]) + len(pv["luoghi"]) + pv["nome"], k, pv, motivo))
        return sorted(out, key=lambda x: -x[0])

    for r in righe:
        cp = r.get("cod_cp_ed")
        if not cp or r["esito"] not in ("da_verificare", "senza_posizione"):
            continue
        prima_esito = r["esito"]
        attuale = None
        if r.get("osm_id") and r["osm_id"] in idx_osm:
            k = idx_osm[r["osm_id"]]
            pv = prove(cp, k)
            esito, motivo = decidi_verifica(pv)
            attuale = (esito, motivo, pv)
            if esito == "sicuro":
                r["esito"] = "sicuro"
                posto_sicuro[cp] = r["cod_ac"]
                r["nota"] = f"2° passaggio: {motivo}" + (f" [1° passaggio: {r['nota']}]" if r.get("nota") else "")
                dettaglio.append((cp, prima_esito, "sicuro", motivo))
                continue
        alt = alternative(cp, {r.get("osm_id")}, largo=prima_esito == "senza_posizione")
        if alt:
            _, k, pv, motivo = alt[0]
            f = sottostazioni[k]
            vecchio = f"{r.get('osm_id') or 'nessuna sottostazione'} {r.get('cod_ac') or ''}".strip()
            occupate.add(f["osm_id"])
            occupate.discard(r.get("osm_id"))
            aree_ed_usate.discard(r.get("cod_ac"))
            aree_ed_usate.add(pv["area"]["COD_AC"])
            solo_gse.pop(pv["area"]["COD_AC"], {}).update(esito="_tolta")
            u = unioni.get(cp)
            r.update(osm_id=f["osm_id"], osm_nome=f.get("name") or "", lon=round(f["lon"], 6), lat=round(f["lat"], 6),
                     cod_ac=pv["area"]["COD_AC"], gestore=pv["area"].get("RAG_SOC", ""), punteggio_nome=pv["nome"],
                     distanza_m=round(u.distance(punti[k])) if u is not None else None, esito="corretto",
                     nota=f"2° passaggio: abbinamento cambiato (prima {vecchio}): {motivo}")
            posto_sicuro[cp] = r["cod_ac"]
            dettaglio.append((cp, prima_esito, "corretto", motivo))
            continue
        motivo = attuale[1] if attuale else "nessuna sottostazione OSM con prove sufficienti"
        if not attuale and r.get("cod_ac") and r["cod_ac"] in coerenza:
            a = next(x for x in aree if x["COD_AC"] == r["cod_ac"])
            qa = misura_comuni(a["geom"], unioni.get(cp))[0]
            if migliore(r["cod_ac"]) == cp and qa >= 0.8:
                motivo += (f"; COD_AC confermato dai comuni (area per {qa:.0%} nei comuni serviti, "
                           "cabina più coerente con l'area)")
        if attuale and attuale[0] == "errore":
            motivo = "da rivedere: " + motivo
        r["nota"] = f"2° passaggio: {motivo}" + (f" [1° passaggio: {r['nota']}]" if r.get("nota") else "")
        dettaglio.append((cp, prima_esito, r["esito"], motivo))
    righe[:] = [r for r in righe if r["esito"] != "_tolta"]
    # le aree tolte dai solo_gse restano coperte dalla riga corretta
    return {"prima": dict(prima), "dopo": dict(Counter(r["esito"] for r in righe)), "dettaglio": dettaglio}
