"""DBTR Emilia-Romagna – Unità volumetriche (UVL): lettura del GeoPackage, controllo degli attributi, corpi.

Due formati:
  * **GeoPackage dell'estrazione dal Geoportale** («Download DB Topografico», 05/11/2026, comune di Rimini,
    `estraz_procons.gpkg`, EPSG:7791): strati `V_UVL_GPG` (unità volumetriche), `V_EDI_GPG` (edifici: FOGLIO, NUMERO,
    NOME, D_TY_EDI, D_STAT_E, COD_COM), `V_EDI_GPGSA` (ingombro al suolo) e `V_EDI_CT_USO_AVM` (destinazione d'uso
    CT_USO/D_CT_USO per ID_E, senza geometria). Colonne **maiuscole**: ID_E (corpo), EDI_ID_E (edificio), H_UVL, B_UVL,
    H_GRONDA, H_COLMO, TIPO_FONTE, QUALITA, DATA_AGG, …
  * **WMS** (GetFeatureInfo, solo attributi, controllo su pochi punti): stessi campi con l'iniziale maiuscola (H_uvl, Id_e…).

Cosa dicono davvero le altezze (verifica del 07/11/2026 su 42.804 UVL di Rimini, confronto con il DTM 5 m RER 2025 e con
il DSM LiDAR 2019 della costa su 1.930 corpi; i metadati dicono solo «altezza qualitativa ±3 m, normalizzata a 3, 6 e 9 m
per i valori piccoli»):
  * **H_UVL intero** (32.710 corpi, 80 %): altezza del corpo sopra il terreno, in metri interi; rispetto al LiDAR è in
    mediana 1,2 m sotto la mediana del tetto e circa all'altezza della gronda (−0,9 m dal 10° percentile del tetto).
    → **gronda = H_UVL**.
  * **H_UVL con i decimali** (8.002 corpi, quasi tutti aggiornati nel 2025-26): è una **quota assoluta** (m s.l.m.,
    come B_UVL): H_UVL − B_UVL coincide con la mediana LiDAR del tetto (scarto mediano −0,1 m). → altezza = H_UVL − B_UVL
    se H_UVL > B_UVL + 1 m; se H_UVL ≤ B_UVL + 1 m (186 corpi, collina) è una quota senza altezza: il corpo si scarta.
    Lo stesso vale per i pochi **interi in collina** (B_UVL ≥ 15 m e H_UVL > B_UVL + 1 m: 46 corpi, H_UVL − B_UVL ~5 m).
  * **H_GRONDA e H_COLMO** (7.438 e 5.798 corpi) sono **quote assolute** (m s.l.m.), non altezze: H_COLMO − DTM coincide col
    95° percentile LiDAR del tetto (−0,2 m in mediana). → **colmo = H_COLMO − B_UVL** se più alto della gronda di almeno
    0,3 m. H_GRONDA − B_UVL invece è spesso vicino a 0 (1.418 corpi sotto il terreno, mediana 3,6 m sotto il LiDAR):
    **non si usa** come gronda, resta nelle proprietà per chi la vuole vedere.
  * H_UVL ≤ 0 (2.092 corpi: tettoie, baracche, cabine, piccoli corpi): niente altezza; si scartano come prima.
  * Nessun campo con il numero di piani: piani stimati dall'altezza (§ 8).

**La convenzione cambia da comune a comune** (prova del 07/11/2026 su Faenza, Shapefile, base ~33 m s.l.m.): lì H_UVL
con i decimali e H_COLMO sono **altezze** (H_COLMO − H_UVL ≈ 0,8 m, tutti sotto B_UVL), non quote. Le regole perciò
guardano il rapporto con B_UVL, corpo per corpo: H_UVL (o H_COLMO) più alto della base → quota; più basso → altezza.
A Lugo (base ~11 m) H_UVL è quasi sempre intero e senza H_COLMO.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from shapely.geometry import shape

from .modello import Corpo, numero

LICENZA = "CC BY 4.0"
FONTE = "DBTR Emilia-Romagna – UVL"
ATTRIBUZIONE = "Regione Emilia-Romagna – DBTR, CC BY 4.0"
STRATO_UVL = "V_UVL_GPG"
STRATO_EDI = "V_EDI_GPG"
STRATO_USO = "V_EDI_CT_USO_AVM"
CAMPI_ALTEZZA = ("H_UVL", "H_GRONDA", "H_COLMO")
CAMPI_PIANI = ("N_PIANI", "PIANI", "NUM_PIANI", "PIANI_FT")       # cercati, nessuno visto finora
CAMPI_ATTESI = ("ID_E", "EDI_ID_E", "B_UVL", "H_UVL", "H_GRONDA", "H_COLMO", "TIPO_FONTE", "QUALITA", "D_TETTO",
                "D_TY_PORZ", "DATA_DA", "DATA_A")
# codici ISTAT dei comuni con l'estrazione DBTR scaricata (06/11/2026), per nome dell'archivio (`prepara --comune`):
# la pagina Modelli 3D usa il confine ISTAT del comune per sapere dove vale il DBTR e dove serve il ripiego OSM
# (07/11/2026; il riquadro dei corpi sborda sui comuni vicini). Codici controllati su fase5-sito/sito/dati/mappa/08.json.
COMUNI_ISTAT = {
    "rimini": "099014", "riccione": "099013", "cattolica": "099002", "novafeltria": "099023", "santarcangelo": "099018",
    "santarcangelo-di-romagna": "099018", "montescudo-montecolombo": "099029", "montescudo-monte-colombo": "099029",
    "cesena": "040007", "forli": "040012", "forlimpopoli": "040013", "mercato-saraceno": "040020", "santa-sofia": "040043",
    "bagno-di-romagna": "040001", "savignano": "040045", "savignano-sul-rubicone": "040045", "faenza": "039010",
    "lugo": "039012", "russi": "039016", "brisighella": "039004", "cervia": "039007",
    "bellaria-igea-marina": "099001", "cesenatico": "040008", "modigliana": "040022", "bagnacavallo": "039002",
    "conselice": "039008", "alfonsine": "039001", "cotignola": "039009",
    "bologna": "037006",   # 08/11 + 09/11 (354168 e 354187): mancano solo i fogli 63–66, 89, 133, 250 (rurali)
    "castel-bolognese": "039006",   # 09/11 (354181): fogli 1–36, tutti
    # Ravenna (039014) manca apposta: le estrazioni del 06/11, dell'08/11 e del 09/11 coprono la città e parte del forese,
    # non tutto il comune, e con
    # il confine del comune il forese risulterebbe «coperto» senza edifici; finché non c'è il comune intero vale il
    # riquadro dei corpi
    # (aggiungere qui la riga, o `prepara --istat 039014`, quando arriva l'estrazione completa)
}
SOGLIA_ASSOLUTA = 1.0      # m: H_UVL decimale sopra B_UVL di almeno questo → quota assoluta del tetto
BASE_COLLINA = 15.0        # m s.l.m.: sopra, anche un H_UVL intero più alto della base di 1 m è una quota
MIN_FALDA = 0.3            # m: colmo almeno così sopra la gronda per un tetto a falde

# destinazione d'uso del DBTR (V_EDI_CT_USO_AVM.CT_USO) → uso per la stima dei piani (modello.INTERPIANI)
USI = {101: "residenziale", 705: "commerciale", 801: "capannone", 9: "capannone", 303: "scuola", 302: "ospedale",
       30102: "ospedale", 30101: "ospedale", 201: "uffici", 299: "uffici", 399: "uffici", 306: "uffici", 305: "uffici",
       100202: "palestra", 1002: "palestra", 100201: "palestra", 799: "commerciale"}


def _vuoto(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("", "Null", "NULL", "null", "nan")


def _maiuscole(p: dict) -> dict:
    """Stessi nomi per GeoPackage (maiuscoli) e WMS (H_uvl, Id_e…)."""
    return {str(k).upper(): v for k, v in p.items()}


def _num(v) -> float | None:
    if _vuoto(v):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        x = numero(v)
    return x if x is not None and math.isfinite(x) else None


def convenzione(proprieta) -> str:
    """Convenzione di H_UVL dell'estrazione (un comune): «quote» se gli H_UVL con i decimali stanno sopra la base
    (Rimini: quote del tetto), «altezze» se una parte apprezzabile sta sotto la base di oltre 1 m, cosa impossibile
    per una quota del tetto (Faenza, base ~33 m: altezze anche con i decimali). Prova del 07/11/2026."""
    sopra = sotto = 0
    for p in proprieta:
        p = _maiuscole(p)
        hu, b = _num(p.get("H_UVL")), _num(p.get("B_UVL"))
        if hu is None or hu <= 0 or b is None or b <= 0 or abs(hu - round(hu)) < 0.005:
            continue
        if hu < b - SOGLIA_ASSOLUTA:
            sotto += 1
        elif hu > b + SOGLIA_ASSOLUTA:
            sopra += 1
    return "altezze" if sotto >= max(5, 0.05 * (sopra + sotto)) else "quote"


def altezze(p: dict, conv: str = "quote") -> dict:
    """Gronda, colmo e fonte dell'altezza di una UVL (regole della docstring del modulo). Chiavi: gronda (m sopra il
    terreno o None), colmo (m o None), fonte (testo per la pagina e il report), tipo («relativa», «assoluta», «nessuna»)."""
    p = _maiuscole(p)
    hu, b = _num(p.get("H_UVL")), _num(p.get("B_UVL"))
    hc = _num(p.get("H_COLMO"))
    tf = p.get("TIPO_FONTE")
    da = f", da {tf}" if not _vuoto(tf) else ""
    if hu is None or hu <= 0:
        return {"gronda": None, "colmo": None, "fonte": "DBTR senza altezza", "tipo": "nessuna"}
    intero = abs(hu - round(hu)) < 0.005
    rel = f"DBTR H_UVL (altezza del corpo, ±3 m{da})"
    if b is None or b <= 0 or conv == "altezze":
        gronda, tipo, fonte = float(hu), "relativa", rel
    elif abs(hu - b) <= SOGLIA_ASSOLUTA and (b >= BASE_COLLINA or not intero):
        # H_UVL uguale alla base: una quota senza altezza (collina, 186 + 9 corpi a Rimini)
        return {"gronda": None, "colmo": None, "fonte": "DBTR: H_UVL è una quota, non un'altezza", "tipo": "nessuna"}
    elif hu > b + SOGLIA_ASSOLUTA and (not intero or b >= BASE_COLLINA):
        # quota del tetto: decimali più alti della base (Rimini, 2025-26), o interi più alti della base in collina
        gronda, tipo, fonte = round(hu - b, 2), "assoluta", f"DBTR H_UVL − B_UVL (quota del tetto meno quota della base{da})"
    else:
        # interi in pianura, e decimali sotto la base (Faenza: H_UVL è un'altezza anche con i decimali)
        gronda, tipo, fonte = float(hu), "relativa", rel
    colmo = None
    if hc and hc > 0 and tipo == "relativa":
        # H_COLMO: quota assoluta dove è più alta della base (Rimini), altezza dove è più bassa (Faenza, base ~33 m)
        c = round(hc - b, 2) if b and hc > b + gronda * 0.5 else round(hc, 2)
        if gronda + MIN_FALDA <= c <= gronda + 25:
            colmo = c
            fonte += "; colmo da H_COLMO − B_UVL" if c != round(hc, 2) else "; colmo da H_COLMO"
    return {"gronda": gronda, "colmo": colmo, "fonte": fonte, "tipo": tipo}


def controlla(proprieta: list[dict]) -> dict:
    """Controllo automatico degli attributi UVL: campi, riempimento e lettura delle altezze (relative, assolute,
    gronda/colmo come quote). Vale per il GeoPackage e per il WMS."""
    proprieta = [_maiuscole(p) for p in proprieta]
    n = len(proprieta)
    campi = sorted({k for p in proprieta for k in p})
    pieni = {c: sum(1 for p in proprieta if not _vuoto(p.get(c)) and _num(p.get(c)) != 0) for c in campi}
    alt = [_num(p.get("H_UVL")) for p in proprieta]
    alt = [a for a in alt if a is not None and a > 0]
    conv = convenzione(proprieta)
    tipi = Counter(altezze(p, conv)["tipo"] for p in proprieta)
    colmi = sum(1 for p in proprieta if altezze(p, conv)["colmo"])
    gronde = [a["gronda"] for a in (altezze(p, conv) for p in proprieta) if a["gronda"]]
    piani = [c for c in CAMPI_PIANI if c in campi]
    domande = []
    if pieni.get("H_GRONDA", 0) == 0 and pieni.get("H_COLMO", 0) == 0:
        domande.append("H_GRONDA e H_COLMO sempre vuoti: H_UVL è l'altezza del corpo (gronda, ±3 m)")
    else:
        domande.append(f"H_GRONDA ({pieni.get('H_GRONDA', 0)}) e H_COLMO ({pieni.get('H_COLMO', 0)}) pieni: colmo per {colmi} corpi "
                       "(H_COLMO − B_UVL dove è una quota, H_COLMO dove è un'altezza); H_GRONDA non si usa come gronda "
                       "(sotto H_UVL di qualche metro rispetto al LiDAR)")
    if tipi.get("assoluta"):
        domande.append(f"{tipi['assoluta']} corpi con H_UVL decimale sopra B_UVL: quota del tetto, altezza = H_UVL − B_UVL")
    if tipi.get("nessuna"):
        domande.append(f"{tipi['nessuna']} corpi senza altezza utilizzabile (H_UVL ≤ 0 o quota): scartati")
    if not piani:
        domande.append("nessun campo con il numero di piani: piani stimati dall'altezza (§ 8)")
    else:
        domande.append("campi dei piani trovati: " + ", ".join(piani))
    mancanti = [c for c in CAMPI_ATTESI if c not in campi]
    g = sorted(gronde)
    return {"corpi": n, "edifici": len({p.get("EDI_ID_E") for p in proprieta}), "campi": campi, "pieni": pieni,
            "mancanti": mancanti,
            "altezza": {"conteggio": len(alt), "min": min(alt, default=None), "max": max(alt, default=None),
                        "mediana": sorted(alt)[len(alt) // 2] if alt else None,
                        "interi": sum(1 for a in alt if abs(a - round(a)) < 0.005)},
            "gronda": {"conteggio": len(g), "mediana": g[len(g) // 2] if g else None,
                       "p95": g[int(len(g) * 0.95)] if g else None, "max": g[-1] if g else None},
            "tipi_altezza": dict(tipi), "colmi": colmi, "campi_piani": piani,
            "fonti": dict(Counter(str(p.get("TIPO_FONTE")) for p in proprieta).most_common(10)),
            "tetti": dict(Counter(str(p.get("D_TETTO")) for p in proprieta).most_common(10)),
            "domande": domande}


def rapporto(c: dict) -> str:
    """Rapporto leggibile del controllo (lo stampa il comando `edifici3d controlla-uvl`)."""
    r = [f"Controllo degli attributi UVL: {c['corpi']} corpi di {c['edifici']} edifici, {len(c['campi'])} campi"]
    if c["mancanti"]:
        r.append("Campi attesi mancanti: " + ", ".join(c["mancanti"]))
    r.append("Riempimento dei campi principali (valori diversi da vuoto e da 0):")
    for k in CAMPI_ATTESI:
        if k in c["pieni"]:
            r.append(f"  {k:<12} {c['pieni'][k]:>8} pieni su {c['corpi']} ({100 * c['pieni'][k] / max(c['corpi'], 1):.0f} %)")
    a, g = c["altezza"], c["gronda"]
    r.append(f"H_UVL > 0: {a['conteggio']} valori (interi {a['interi']}), da {a['min']} a {a['max']}, mediana {a['mediana']}")
    r.append(f"Altezza usata (gronda): {g['conteggio']} corpi, mediana {g['mediana']} m, 95° percentile {g['p95']} m, "
             f"massimo {g['max']} m; tipi: " + ", ".join(f"{k} {v}" for k, v in c["tipi_altezza"].items()))
    r.append("Fonti dell'altezza: " + ", ".join(f"{k} ({v})" for k, v in c["fonti"].items()))
    r.append("Tetti: " + ", ".join(f"{k} ({v})" for k, v in c["tetti"].items()))
    r.append("Esito:")
    r += [f"  - {d}" for d in c["domande"]]
    return "\n".join(r)


def corpo_da(proprieta: dict, geometria, quota_dtm: float | None = None, edificio: dict | None = None,
             conv: str = "quote") -> Corpo | None:
    """Una UVL → Corpo. Geometria già nel sistema proiettato (EPSG:7791); i fori (cortili) restano. Scarta le UVL senza
    altezza o area. `edificio`: riga di V_EDI_GPG (con «uso» da V_EDI_CT_USO_AVM) dell'edificio del corpo."""
    from shapely.validation import make_valid
    p = _maiuscole(proprieta)
    g = shape(geometria) if isinstance(geometria, dict) else geometria
    if g is None or g.is_empty:
        return None
    if not g.is_valid:
        g = make_valid(g)
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        parti = [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon"]
        if not parti:
            return None
        g = max(parti, key=lambda x: x.area)
    if g.geom_type != "Polygon" or g.area < 1:
        return None
    a = altezze(p, conv)
    if not a["gronda"] or a["gronda"] <= 0:
        return None
    h, colmo = a["gronda"], a["colmo"]
    base = _num(p.get("B_UVL"))
    q = _num(p.get("QUALITA"))
    extra = {"tipo_porzione": p.get("D_TY_PORZ"), "altezza_dbtr": a["tipo"]}
    hg = _num(p.get("H_GRONDA"))
    if hg:
        extra["quota_gronda_dbtr"] = round(hg, 2)
    if not _vuoto(p.get("DATA_AGG")):
        extra["aggiornato"] = str(int(_num(p.get("DATA_AGG")) or 0)) if _num(p.get("DATA_AGG")) else str(p.get("DATA_AGG"))
    uso = None
    if edificio:
        e = _maiuscole(edificio)
        for k_out, k_in in (("foglio", "FOGLIO"), ("numero", "NUMERO"), ("nome", "NOME"), ("tipo_edificio", "D_TY_EDI"),
                            ("stato_edificio", "D_STAT_E"), ("comune_catasto", "COD_COM"), ("destinazione", "D_CT_USO")):
            v = e.get(k_in)
            if not _vuoto(v) and not (k_in == "FOGLIO" and _num(v) == 0):
                v = str(v).strip()
                if k_in == "FOGLIO":
                    v = str(int(float(v)))
                if v and v != "Non assegnato":
                    extra[k_out] = v
        cu = _num(e.get("CT_USO"))
        uso = USI.get(int(cu)) if cu is not None else None
    return Corpo(
        id=str(p.get("ID_E") or p.get("OBJECTID")), edificio=str(p.get("EDI_ID_E") or p.get("ID_E")),
        sagoma=g, quota_terreno=quota_dtm if quota_dtm is not None else base, gronda=float(h),
        colmo=colmo, tetto="capanna" if colmo else "piano", falde=2 if colmo else 0, fonte_sagoma=FONTE, licenza=LICENZA,
        fonte_altezza=a["fonte"], uso=uso,
        qualita=(f"DBTR qualità {q:g}; altezza ±3 m" if q else "altezza ±3 m"), extra=extra)


def _leggi(percorso: Path, strato: str, riquadro=None, geometria: bool = True) -> tuple[list[dict], list, dict]:
    """Righe (dict) e geometrie shapely di uno strato; pyogrio senza pyarrow (non è nei requisiti)."""
    import pyogrio.raw as R
    from shapely import from_wkb
    meta, _fid, geom, campi = R.read(str(percorso), layer=strato, bbox=tuple(riquadro) if riquadro else None,
                                     read_geometry=geometria)
    nomi = list(meta["fields"])

    def semplice(v):
        if hasattr(v, "item"):
            if getattr(v, "size", 1) != 1:
                return None                      # liste (es. «bbox» dei GeoJSON di GeoServer, 08/11/2026): non servono
            v = v.item()
        return None if isinstance(v, float) and math.isnan(v) else v
    righe = [{k: semplice(v) for k, v in zip(nomi, valori)} for valori in zip(*campi)] if nomi else []
    geoms = list(from_wkb(geom)) if geometria and geom is not None else [None] * len(righe)
    return righe, geoms, meta


def strati(percorso: Path) -> list[str]:
    import pyogrio
    return [str(n) for n, _ in pyogrio.list_layers(str(percorso))]


def strato_uvl(percorso: Path, strato: str | None = None) -> str:
    """Strato delle UVL: quello dato, altrimenti V_UVL_GPG (estrazione) o UVL_Unita_volumetrica (nome del WMS)."""
    if strato:
        return strato
    s = strati(percorso)
    for nome in (STRATO_UVL, "UVL_Unita_volumetrica", "UVL_GPG"):
        if nome in s:
            return nome
    raise ValueError(f"strato delle UVL non trovato tra {s}: usa --strato")


def leggi_gpkg(percorso: Path, strato: str | None = None, riquadro=None) -> list[tuple[dict, object]]:
    """(proprietà, geometria shapely) delle UVL dal GeoPackage; riquadro (x0, y0, x1, y1) in EPSG:7791 facoltativo."""
    righe, geoms, _ = _leggi(percorso, strato_uvl(percorso, strato), riquadro)
    return list(zip(righe, geoms))


def leggi_edifici(percorso: Path, riquadro=None) -> dict[str, dict]:
    """Edifici (V_EDI_GPG) per ID_E, con la destinazione d'uso di V_EDI_CT_USO_AVM; {} se lo strato manca."""
    s = strati(percorso)
    if STRATO_EDI not in s:
        return {}
    righe, _, _ = _leggi(percorso, STRATO_EDI, riquadro, geometria=False)
    edifici = {str(r["ID_E"]): r for r in righe if r.get("ID_E")}
    if STRATO_USO in s:
        usi, _, _ = _leggi(percorso, STRATO_USO, None, geometria=False)
        for u in usi:
            e = edifici.get(str(u.get("ID_E")))
            if e is not None:
                e["CT_USO"], e["D_CT_USO"] = u.get("CT_USO"), u.get("D_CT_USO")
    return edifici


def leggi_geojson_wms(percorso: Path) -> list[dict]:
    """Proprietà da una risposta GetFeatureInfo in GeoJSON (senza geometria): per il controllo degli attributi."""
    d = json.loads(Path(percorso).read_text(encoding="utf-8"))
    return [f.get("properties", {}) for f in d.get("features", [])]


def url_getfeatureinfo(wms: str, lat: float, lon: float, strato: str = "UVL_Unita_volumetrica", raggio: float = 0.0015) -> str:
    """GetFeatureInfo WMS 1.3.0 (asse lat, lon in EPSG:4326) attorno a un punto, in GeoJSON."""
    bbox = f"{lat - raggio},{lon - raggio},{lat + raggio},{lon + raggio}"
    return (f"{wms}?service=WMS&version=1.3.0&request=GetFeatureInfo&layers={strato}&query_layers={strato}"
            f"&crs=EPSG:4326&bbox={bbox}&width=101&height=101&i=50&j=50&feature_count=50&info_format=application/geojson")
