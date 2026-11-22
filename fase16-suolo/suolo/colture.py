"""Superfici coltivate per famiglia di colture (ISTAT, stime congiunturali «Coltivazioni: superfici e produzione»,
SDMX 101_1015_DF_DCSP_COLTIVAZIONI_2, DATA_TYPE = ART: superficie totale in ettari), per regione e provincia.

Le voci ISTAT sono gerarchiche e cambiano negli anni (nuova classificazione dal 2020): per non contare due volte la stessa
superficie ogni famiglia è fatta di «concetti», e ogni concetto ha una o più alternative in ordine di preferenza. In ogni
anno si usa la prima alternativa che ha dati (a livello nazionale): per esempio i prati permanenti e pascoli sono la voce
PGRAPM dal 2024 e, prima, la somma di PERMGRASSE + POORINGS + OTHEZINGS + PGPNP; le olive sono OLIVTAB_OIL (olive da
tavola e da olio) e non anche OLIVO/OHROIE, che ne sono parti (OHROIE e OLIVO coincidono). Le voci di dettaglio che
duplicano un totale (arance per varietà, mele per destinazione, uve per vini DOP/IGP…) sono in ESCLUSE.
Una voce nuova che non è in nessun concetto né fra le escluse non si somma: compare nelle note del costruttore.
Verifica (dati scaricati il 22/11/2026): PGRAPM 2024 = somma esatta dei suoi quattro figli; la somma delle famiglie è
12,43 milioni di ha nel 2024 (12,68 nel 2020) contro 12,54 milioni di SAU del censimento 2020; le regioni sommano
esattamente all'Italia (salvo 2012: +3.459 ha, dati ISTAT).

Territori (istat_territori.json): regioni dai codici NUTS2 (Trentino-Alto Adige = Bolzano + Trento), province dai NUTS3
(Monza, Fermo e Barletta-Andria-Trani dal 2010: prima erano nelle province d'origine). La Sardegna è solo regionale: le sue
province nelle stime mescolano le vecchie (fino al 2016) e le nuove e non sommano al dato regionale.
Anni: dal 2006; un anno con molte meno voci del precedente (il 2026 provvisorio, novembre 2026: 125 voci contro 189) è
escluso (ANNO_COMPLETO).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

TERRITORI = Path(__file__).resolve().parent / "istat_territori.json"
ANNO_COMPLETO = 0.85          # quota minima di voci rispetto all'anno precedente

# (id, nome, colore, concetti); un concetto è una lista di alternative, ogni alternativa una lista di codici
def _c(*alt):
    return [list(a) if isinstance(a, (list, tuple)) else [a] for a in alt]


FAMIGLIE = [
    ("cereali", "Cereali", "#e0b13a", [
        _c("WHEATD"), _c("COMMEAT", ["PIGWETWINT", "PIGWETSPRING"]), _c("BARLEY", ["WNEALY", "PIGBRE"]), _c("MAIZE"),
        _c("RICE"), _c("ITRSOYEAN", ["RYE", "LNSOITERC"]), _c("MXSOASANDS", ["OATS", "SRNRIIXES"]), _c("SORGH"),
        _c("TITICALE"), _c("CEREAOG"), _c("BUCKWHEAT"), _c("PSEUDOCEREA", "QUINOA")]),
    ("industriali", "Legumi secchi, patate e piante industriali", "#a0522d", [
        _c(x) for x in ["BEANK", "BROAFIELD", "CHICS", "LENTIL", "LUPIN", "PEAPROT", "PEAS", "PULSEOPRO", "VETCH", "BEETS",
                        "POTA", "EARLATOES", "SWEEATOES", "OTHROOTSBULBSTUBPOT", "TOBAC", "HOPS", "GROU", "OTHOLNOSES",
                        "RAPE", "SESA", "SOYA", "SUNFLO", "TURNPE", "COTTON", "CROPOT", "FLAX", "HEMP", "CROOIN", "ENCRO",
                        "PARSNGROPEN"]]),
    ("ortive", "Ortive e fragole", "#d9534f", [
        _c("OFTTOT", "TOMATIOPFI"), _c("OFTP"), _c(["GARLIC", "SHALLOT"], "GARLDSHALL"), _c("CHICNOPEN"),
        _c(["HTABG", "RDCBAE"], "CABBNOPEN"), _c("SAVOBAGEIN"), _c("BRUSSPROUTS"), _c("CAULERAND"),
        _c("OTHBROCI", "OTHESSICAS"), _c("BROCINOPEN"), _c(["FRESADBEAN", "OTHFRELPULSNF"]), _c("GHERINOPEN", "GHERIN")]
        + [_c(x) for x in ["ASPAINGREOPEN", "BEETANDLEA", "CARRNDPARS", "CELEOPENF", "CHAROPENFI", "COURINOPE", "CUCUINOPE",
                           "EGGINOPE", "ENDINOPEN", "FENNOPENF", "FRESNEYBEA", "GLOBICHOKE", "LETTNOPEN", "MELOOPENFI",
                           "ONIOOPENF", "PEAENFIEL", "RADIOPEN", "REDRINOP", "SPINNOPEN", "TURNNOPEN", "WATENINOP",
                           "LEEKOPENFI", "OTHALEAFSNOB", "CELERIA", "ZUCCA", "STRAIEINO"]]),
    ("avvicendate", "Foraggere avvicendate (erbai e prati avvicendati)", "#9ccc65", [
        _c(x) for x in ["LUCERNE", "MIXEPORARY", "GRAM", "DRIESES", "OTHETURES", "CEROIS", "CERFORRLEY", "CERORLEY",
                        "FORARLEY", "COMMEGRASS", "OTHEEHERBA", "OTMFC", "OTHGRENOCER", "SAIN", "SPANPARCET", "LVRADBENDS",
                        "OTHEETEMPO", "LEGMIX"]]),
    ("prati", "Prati permanenti e pascoli", "#4f8a3a", [_c("PGRAPM", ["PERMGRASSE", "POORINGS", "OTHEZINGS", "PGPNP"])]),
    ("vite", "Vite", "#7b2d5e", [_c("WINEES"), _c("TABLEGRAPES"), _c("GAEOASINS"), _c("OTHGRPURP")]),
    ("olivo", "Olivo", "#808000", [_c("OLIVTAB_OIL", ["OLIVO", "OLIVT"])]),
    ("frutta", "Frutta, agrumi e frutta a guscio", "#f39c12", [
        _c("ORANGE", ["AACAE", "WIEOAGSBLAN", "RDOAGS", "OHROAGS"]), _c("LEMLIME", ["LEMON", "CDLMS"]),
        _c("APPLE", ["PLSFRFESHC", "PLSDSIEDFO"]), _c("PEAR", ["ERORSHCO", "ERETNDFOR"]),
        _c("PEACH", ["ECENEDEDF", "ECENEDEDFTR"]), _c("NECTA", ["ETRNSITENDE", "ETRNSITENDETR"]),
        _c("CHERR", ["SWCHERRIES", "ORCERE"]), _c("CRAT", ["REDCURRA", "BLACKCURRA"]),
        _c("OTHETFRUIT", ["GOOSEBERRI", "OTHETFRUITNOR", "ROWAN"])]
        + [_c(x) for x in ["CLEMENTINE", "MANDAR", "OHRIBRID", "STUAMNARIN", "POME", "BERG", "CEDA", "CHIN", "OTHAGRBCC",
                           "APRIC", "PLUM", "QUIN", "MEDLAR", "JAPAMEDLAR", "OTHPOMAFRUNOQM", "OTHNUTSFRUNOJ", "FIG", "KIWI",
                           "LOTU", "POMETES", "PRICKLYPEAR", "FRSTCZ", "AOAO", "BANA", "BUBRY", "ROUSPBERRI", "ALMO",
                           "CHEST", "HAZEL", "WALNU", "PISTS", "OTHNUTSOPI", "CARO"]]),
]
# voci che duplicano un totale o sono parti di voci già contate
ESCLUSE = {"CITRFR", "CICRADIFRE", "CICRADITRA", "CICRADIFRE_OPEN", "CICRADITRA_OPEN", "OTHFRELPULS", "OHROIE", "OHROIEOIL",
           "GRAPEDOPWINE", "GRAPEIGPWINE", "OTHGRWINODI", "CEREAOG_NO_FORAGENR"}


def codici_noti() -> set:
    return {c for _, _, _, conc in FAMIGLIE for k in conc for alt in k for c in alt} | ESCLUSE


def territori() -> dict:
    return json.loads(TERRITORI.read_text(encoding="utf-8"))


def leggi(csv_path: Path) -> dict:
    """{area: {anno: {codice: ha}}} dal CSV SDMX (solo DATA_TYPE = ART)."""
    out: dict = defaultdict(lambda: defaultdict(dict))
    with Path(csv_path).open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("DATA_TYPE") != "ART" or not r.get("OBS_VALUE"):
                continue
            try:
                v = float(r["OBS_VALUE"])
            except ValueError:
                continue
            out[r["REF_AREA"]][int(r["TIME_PERIOD"])][r["TYPE_OF_CROP"]] = v
    return out


def famiglie(csv_path: Path) -> dict:
    """{"anni": [...], "voci": [(id, nome, colore)], "regioni": {cod2: {anno: [ha × famiglia]}},
        "province": {cod3: {anno: [...]}}, "italia": {anno: [...]}, "scelte": {anno: {concetto: alternativa}},
        "note": [...]}"""
    dati = leggi(csv_path)
    t = territori()
    it = dati.get("IT", {})
    voci_per_anno = {a: len(v) for a, v in it.items()}
    anni = []
    for a in sorted(voci_per_anno):
        prima = voci_per_anno.get(a - 1)
        if prima and voci_per_anno[a] < ANNO_COMPLETO * prima:
            continue
        anni.append(a)
    note = [f"Colture: anno {a} escluso (voci {voci_per_anno[a]} contro {voci_per_anno.get(a - 1)} dell'anno prima, "
            f"dati provvisori incompleti)" for a in sorted(set(voci_per_anno) - set(anni))]
    # alternative scelte anno per anno (presenza a livello nazionale)
    scelte: dict = {}
    for a in anni:
        presenti = set(it.get(a, {}))
        scelte[a] = []
        for _, _, _, conc in FAMIGLIE:
            sc = []
            for k in conc:
                alt = next((x for x in k if presenti & set(x)), [])
                sc.append(alt)
            scelte[a].append(sc)
    ignote = sorted({c for a in anni for c in it.get(a, {})} - codici_noti())
    if ignote:
        note.append("Colture: voci ISTAT nuove non assegnate a una famiglia (non sommate): " + ", ".join(ignote))

    def vettore(valori: dict, a: int) -> list | None:
        if not valori:
            return None
        out = []
        for i in range(len(FAMIGLIE)):
            out.append(round(sum(valori.get(c, 0.0) for alt in scelte[a][i] for c in alt), 1))
        return out if any(out) else None

    regioni: dict = defaultdict(dict)
    for nuts, cod in t["regioni"].items():
        for a in anni:
            v = vettore(dati.get(nuts, {}).get(a, {}), a)
            if v is None:
                continue
            prima = regioni[cod].get(a)
            regioni[cod][a] = [round(x + y, 1) for x, y in zip(prima, v)] if prima else v
    province: dict = defaultdict(dict)
    for nuts, cod in t["province"].items():
        for a in anni:
            v = vettore(dati.get(nuts, {}).get(a, {}), a)
            if v is not None:
                province[cod][a] = v
    italia = {a: vettore(it.get(a, {}), a) for a in anni}
    ignorate = sorted(a for a in dati if len(a) >= 3 and a not in t["regioni"] and a not in t["province"]
                      and a not in t["ignorati"] and a not in t["sardegna_province"])
    if ignorate:
        note.append("Colture: codici territoriali ISTAT sconosciuti (aggiornare istat_territori.json): " + ", ".join(ignorate))
    return {"anni": anni, "voci": [(i, n, c) for i, n, c, _ in FAMIGLIE], "regioni": dict(regioni),
            "province": dict(province), "italia": italia, "note": note,
            "scelte": {a: {FAMIGLIE[i][0]: [x for x in s if x] for i, s in enumerate(v)} for a, v in scelte.items()}}
