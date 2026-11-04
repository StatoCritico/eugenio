"""DBTR Emilia-Romagna – Unità volumetriche (UVL): lettura e controllo degli attributi.

Attributi visti il 03/11/2026 con il GetFeatureInfo del WMS `dbtr` (strato UVL_Unita_volumetrica):
  Objectid, Id_e (corpo), Edi_id_e (edificio), Ty_porz/D_ty_porz (tipo di porzione), Ty_intr/D_ty_intr/H_intr,
  Base/D_base, Tetto/D_tetto, B_uvl (quota della base, m s.l.m.), H_uvl (altezza, m), V_uvl, H_GRONDA, H_COLMO,
  Tipo_fonte (es. «DTM DSM 2008», «SIT»), Data_da/Data_a (periodo della fonte), Qualita, Metodo/D_metodo,
  Dt_ini_val, Data_agg, SHAPE.AREA, SHAPE.LEN. Numeri con la virgola decimale e «Null» per i vuoti.
Nei campioni di Rimini, Bologna, Ravenna e Parma H_GRONDA e H_COLMO erano vuoti e **non c'è un campo dei piani**:
per ora l'altezza è H_uvl, trattata come gronda («gronda o colmo da verificare» resta nel rapporto); i piani si
stimano (modello.stima_piani). Il controllo automatico qui sotto lo rifà sul GeoPackage completo.
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
CAMPI_ALTEZZA = ("H_uvl", "H_GRONDA", "H_COLMO")
CAMPI_PIANI = ("N_piani", "Piani", "NUM_PIANI", "N_PIANI", "Piani_ft", "PIANI")       # cercati, nessuno visto finora
CAMPI_ATTESI = ("Id_e", "Edi_id_e", "B_uvl", "H_uvl", "H_GRONDA", "H_COLMO", "Tipo_fonte", "Qualita", "D_tetto",
                "D_ty_porz", "Data_da", "Data_a")


def _vuoto(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("", "Null", "NULL", "null")


def controlla(proprieta: list[dict]) -> dict:
    """Controllo automatico degli attributi UVL: quali campi ci sono, quanto sono pieni, e le risposte alle domande
    aperte (l'altezza è di gronda o di colmo? c'è il numero di piani?)."""
    n = len(proprieta)
    campi = sorted({k for p in proprieta for k in p})
    pieni = {c: sum(1 for p in proprieta if not _vuoto(p.get(c))) for c in campi}
    alt = [numero(p.get("H_uvl")) for p in proprieta]
    alt = [a for a in alt if a is not None]
    gr = [(numero(p.get("H_uvl")), numero(p.get("H_GRONDA")), numero(p.get("H_COLMO"))) for p in proprieta]
    confronto = Counter()
    for h, g, c in gr:
        if h is None:
            continue
        if g is not None and abs(h - g) < 0.05:
            confronto["H_uvl = H_GRONDA"] += 1
        if c is not None and abs(h - c) < 0.05:
            confronto["H_uvl = H_COLMO"] += 1
        if g is not None and c is not None and c < g:
            confronto["colmo sotto la gronda (errore)"] += 1
    multipli3 = sum(1 for a in alt if a <= 9.01 and abs(a / 3 - round(a / 3)) < 0.01)
    piani = [c for c in CAMPI_PIANI if c in campi]
    domande = []
    if pieni.get("H_GRONDA", 0) == 0 and pieni.get("H_COLMO", 0) == 0:
        domande.append("H_GRONDA e H_COLMO sempre vuoti: non si sa se H_uvl è di gronda o di colmo; si usa H_uvl come "
                       "gronda (da chiedere all'Archivio Cartografico o da confrontare col LiDAR)")
    elif confronto:
        domande.append("H_uvl coincide con " + ", ".join(f"{k} ({v})" for k, v in confronto.items()))
    if not piani:
        domande.append("nessun campo con il numero di piani: piani stimati dall'altezza (§ 8)")
    else:
        domande.append("campi dei piani trovati: " + ", ".join(piani))
    mancanti = [c for c in CAMPI_ATTESI if c not in campi]
    return {"corpi": n, "campi": campi, "pieni": pieni, "mancanti": mancanti,
            "altezza": {"conteggio": len(alt), "min": min(alt, default=None), "max": max(alt, default=None),
                        "mediana": sorted(alt)[len(alt) // 2] if alt else None, "fino_a_9m_multipli_di_3": multipli3},
            "confronto_altezze": dict(confronto), "campi_piani": piani,
            "fonti": dict(Counter(str(p.get("Tipo_fonte")) for p in proprieta).most_common(10)),
            "tetti": dict(Counter(str(p.get("D_tetto")) for p in proprieta).most_common(10)),
            "domande": domande}


def rapporto(c: dict) -> str:
    """Rapporto leggibile del controllo (lo stampa il comando `edifici3d controlla-uvl`)."""
    r = [f"Controllo degli attributi UVL: {c['corpi']} corpi, {len(c['campi'])} campi"]
    if c["mancanti"]:
        r.append("Campi attesi mancanti: " + ", ".join(c["mancanti"]))
    r.append("Riempimento dei campi principali:")
    for k in CAMPI_ATTESI:
        if k in c["pieni"]:
            r.append(f"  {k:<12} {c['pieni'][k]:>8} pieni su {c['corpi']} ({100 * c['pieni'][k] / max(c['corpi'], 1):.0f} %)")
    a = c["altezza"]
    r.append(f"Altezza H_uvl: {a['conteggio']} valori, da {a['min']} a {a['max']} m, mediana {a['mediana']} m; "
             f"fino a 9 m multipli di 3: {a['fino_a_9m_multipli_di_3']} (valori «qualitativi» arrotondati)")
    r.append("Fonti dell'altezza: " + ", ".join(f"{k} ({v})" for k, v in c["fonti"].items()))
    r.append("Tetti: " + ", ".join(f"{k} ({v})" for k, v in c["tetti"].items()))
    r.append("Esito:")
    r += [f"  - {d}" for d in c["domande"]]
    return "\n".join(r)


def corpo_da(proprieta: dict, geometria, quota_dtm: float | None = None) -> Corpo | None:
    """Una UVL → Corpo. Geometria già nel sistema proiettato (EPSG:7791). Scarta le UVL senza altezza o area."""
    g = shape(geometria) if isinstance(geometria, dict) else geometria
    if g is None or g.is_empty or g.area < 1:
        return None
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda x: x.area)
    h = numero(proprieta.get("H_GRONDA")) or numero(proprieta.get("H_uvl"))
    if not h or h <= 0:
        return None
    colmo = numero(proprieta.get("H_COLMO"))
    base = numero(proprieta.get("B_uvl"))
    fonte_h = "DBTR H_GRONDA" if numero(proprieta.get("H_GRONDA")) else "DBTR H_uvl (gronda o colmo da verificare)"
    tf = proprieta.get("Tipo_fonte")
    if not _vuoto(tf):
        fonte_h += f", da {tf}"
    return Corpo(
        id=str(proprieta.get("Id_e") or proprieta.get("Objectid")), edificio=str(proprieta.get("Edi_id_e") or proprieta.get("Id_e")),
        sagoma=g, quota_terreno=quota_dtm if quota_dtm is not None else base, gronda=float(h),
        colmo=colmo if colmo and colmo > h else None, tetto="capanna" if colmo and colmo > h else "piano",
        falde=2 if colmo and colmo > h else 0, fonte_sagoma=FONTE, licenza=LICENZA, fonte_altezza=fonte_h,
        qualita=f"DBTR qualità {proprieta.get('Qualita')}; altezza ±3 m" if not _vuoto(proprieta.get("Qualita")) else "altezza ±3 m",
        extra={"tipo_porzione": proprieta.get("D_ty_porz")})


def leggi_gpkg(percorso: Path, strato: str = "UVL_Unita_volumetrica", riquadro=None) -> list[tuple[dict, object]]:
    """(proprietà, geometria shapely) dal GeoPackage regionale; riquadro (x0, y0, x1, y1) in EPSG:7791 facoltativo."""
    import pyogrio
    from shapely import from_wkb
    meta, tabella = pyogrio.read_arrow(str(percorso), layer=strato, bbox=riquadro)
    righe = tabella.to_pylist()
    col = meta.get("geometry_name") or "geometry"
    return [({k: v for k, v in r.items() if k != col}, from_wkb(r[col])) for r in righe]


def leggi_geojson_wms(percorso: Path) -> list[dict]:
    """Proprietà da una risposta GetFeatureInfo in GeoJSON (senza geometria): per il controllo degli attributi."""
    d = json.loads(Path(percorso).read_text(encoding="utf-8"))
    return [f.get("properties", {}) for f in d.get("features", [])]


def url_getfeatureinfo(wms: str, lat: float, lon: float, strato: str = "UVL_Unita_volumetrica", raggio: float = 0.0015) -> str:
    """GetFeatureInfo WMS 1.3.0 (asse lat, lon in EPSG:4326) attorno a un punto, in GeoJSON."""
    bbox = f"{lat - raggio},{lon - raggio},{lat + raggio},{lon + raggio}"
    return (f"{wms}?service=WMS&version=1.3.0&request=GetFeatureInfo&layers={strato}&query_layers={strato}"
            f"&crs=EPSG:4326&bbox={bbox}&width=101&height=101&i=50&j=50&feature_count=50&info_format=application/geojson")
