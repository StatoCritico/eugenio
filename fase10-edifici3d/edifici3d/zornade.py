"""Altezze degli edifici di Zornade (fase 10, Fase E): fonte alternativa e di confronto, **solo nell'archivio ODbL**.

Decisioni (RIEPILOGO, § 2 della proposta): niente scaricamento via API (l'estrazione massiva fa sospendere il token);
in ER la base resta il DBTR UVL (CC BY 4.0); le altezze di Zornade servono per le regioni senza un buon DB topografico e
come confronto. Lo strato edifici di Zornade è OpenStreetMap: **ODbL 1.0**. Quindi:
  - si legge solo un **estratto consegnato da Zornade** (GeoPackage, GeoJSON, Shapefile, FlatGeobuf, Parquet: quello che
    GDAL legge), mai l'API;
  - tutto ciò che contiene sagome o altezze di Zornade (corpi, PMTiles, celle, confronto per corpo) va solo in
    `<archivio>/odbl/<zona>/prodotti/zornade/`; un corpo CC BY che prende l'altezza da Zornade **diventa ODbL** e passa
    nell'archivio ODbL (mai il contrario);
  - attribuzione sempre: «© OpenStreetMap contributors (ODbL 1.0)» e «Dati elaborati da Zornade» con il link a
    https://zornade.com (piano gratuito: la sola scritta non basta), più le fonti delle altezze dichiarate nell'estratto;
  - condivisione allo stesso modo: il database derivato resta ODbL, con il file `LEGGIMI_ODbL.txt` accanto ai prodotti; le
    statistiche aggregate del confronto (medie, scarti) sono un'opera prodotta e si possono citare in CC BY 4.0 di
    EuGEnio mantenendo le due attribuzioni (stessa lettura di fase 4 e 7);
  - **scartate** le altezze che vengono da GlobalBuildingAtlas o da fonti non commerciali (CC BY-NC): Zornade ha detto
    che i 20,5 milioni del suo sito sono un residuo di GBA, che EuGEnio non può usare;
  - nessun dato personale: gli estratti di edifici non hanno intestatari; colonne diverse da quelle note si ignorano.

Colonne riconosciute (prima corrispondenza, senza maiuscole; sovrascrivibili con `mappa`): vedi `SINONIMI`.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
import statistics
from dataclasses import replace
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree

from .modello import Corpo, numero

LICENZA = "ODbL 1.0"
FONTE = "Zornade (sagome OpenStreetMap)"
ATTRIBUZIONE = ("© OpenStreetMap contributors (ODbL 1.0) – altezze: Dati elaborati da Zornade (https://zornade.com)")
ATTRIBUZIONE_HTML = ('© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> (ODbL 1.0) – '
                     'altezze: <a href="https://zornade.com">Dati elaborati da Zornade</a>')
SINONIMI = {
    "id": ("osm_id", "id_osm", "building_id", "id_edificio", "id", "fid"),
    "altezza": ("height_lidar", "lidar_height", "altezza_lidar", "height", "altezza", "height_m", "h", "h_m"),
    "gronda": ("eave_height", "h_gronda", "altezza_gronda"),
    "colmo": ("ridge_height", "h_colmo", "altezza_colmo"),
    "fonte": ("height_source", "fonte_altezza", "source_height", "source", "fonte"),
    "licenza": ("height_license", "licenza_altezza", "license", "licenza"),
    "qualita": ("height_quality", "quality", "qualita", "confidence"),
    "data": ("survey_date", "lidar_date", "data_rilievo", "data"),
    "piani": ("building:levels", "levels", "piani"),
    "uso": ("building", "tipo", "uso"),
}
# altezze che EuGEnio non può usare: GlobalBuildingAtlas (CC BY-NC) e qualunque licenza non commerciale
ESCLUSE = re.compile(r"global\s*building\s*atlas|\bgba\b|by[- ]?nc|non[- ]?commercial", re.I)
ALTEZZA_MIN, ALTEZZA_MAX = 2.0, 300.0
DEBOLI = ("nessuna", "stima", "OSM building:levels", "valore dell'utente")   # fonti di altezza che Zornade può sostituire


def colonne(campi: list[str], mappa: dict | None = None) -> dict[str, str]:
    """Nome effettivo di ogni colonna nota nell'estratto."""
    basso = {c.lower(): c for c in campi}
    out = {}
    for chiave, sin in SINONIMI.items():
        if mappa and mappa.get(chiave):
            if mappa[chiave] not in campi:
                raise ValueError(f"colonna {mappa[chiave]!r} (per {chiave}) assente nell'estratto")
            out[chiave] = mappa[chiave]
            continue
        for s in sin:
            if s in basso:
                out[chiave] = basso[s]
                break
    if "altezza" not in out and "gronda" not in out:
        raise ValueError("nessuna colonna di altezza riconosciuta (usa --mappa altezza=<colonna>)")
    return out


def corpo_da(prop: dict, g, col: dict[str, str], n: int = 0) -> tuple[Corpo | None, str]:
    """Una riga dell'estratto → Corpo ODbL (geometria già in metri). Restituisce (corpo, motivo dello scarto)."""
    if g is None or g.is_empty:
        return None, "senza geometria"
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda x: x.area)
    if g.geom_type != "Polygon" or g.area < 10:
        return None, "sagoma troppo piccola o non poligonale"
    v = lambda k: prop.get(col[k]) if k in col else None
    fonte = str(v("fonte") or "").strip()
    lic = str(v("licenza") or "").strip()
    if ESCLUSE.search(fonte) or ESCLUSE.search(lic):
        return None, "altezza GlobalBuildingAtlas o non commerciale (esclusa)"
    gronda = numero(v("gronda"))
    h = numero(v("altezza"))
    colmo = numero(v("colmo"))
    if gronda is None:
        gronda = h
    if gronda is None or not (ALTEZZA_MIN <= gronda <= ALTEZZA_MAX):
        return None, "altezza mancante o fuori scala"
    if colmo is not None and not (gronda < colmo <= ALTEZZA_MAX):
        colmo = None
    oid = str(v("id") or f"zornade{n}")
    piani = numero(v("piani"))
    qual = str(v("qualita") or "").strip()
    data = str(v("data") or "").strip()
    fonte_h = "Zornade" + (f" – {fonte}" if fonte else "") + (f" ({data})" if data else "")
    return Corpo(id=f"z:{oid}", edificio=f"z:{oid}", sagoma=g, quota_terreno=None, gronda=float(gronda), colmo=colmo,
                 tetto="capanna" if colmo else "piano", falde=2 if colmo else 0,
                 piani=int(piani) if piani else None, fonte_sagoma=FONTE, licenza=LICENZA, fonte_altezza=fonte_h,
                 qualita=("Zornade: " + qual) if qual else "altezza da Zornade",
                 uso=str(v("uso")) if v("uso") not in (None, "", "yes") else None,
                 extra={"zornade_id": oid}), ""


def leggi(percorso: Path, strato: str | None = None, crs: str = "EPSG:7791", mappa: dict | None = None,
          riquadro=None) -> tuple[list[Corpo], dict]:
    """Estratto Zornade → corpi in metri (sistema `crs`) e resoconto (letti, tenuti, scartati per motivo)."""
    from pyproj import CRS, Transformer
    from .uvl import _leggi
    righe, geoms, meta = _leggi(percorso, strato, riquadro)
    campi = list(meta["fields"])
    col = colonne(campi, mappa)
    da = CRS.from_user_input(meta.get("crs") or "EPSG:4326")
    t = Transformer.from_crs(da, CRS.from_user_input(crs), always_xy=True)
    corpi, scarti = [], {}
    for n, r in enumerate(righe):
        g = geoms[n]
        if g is not None:
            g = transform(t.transform, g)
        c, motivo = corpo_da({k: r.get(k) for k in campi}, g, col, n)
        if c:
            corpi.append(c)
        else:
            scarti[motivo] = scarti.get(motivo, 0) + 1
    return corpi, {"file": Path(percorso).name, "righe": len(righe), "corpi": len(corpi), "scartati": scarti,
                   "colonne": col, "crs_file": da.to_string(), "licenza": LICENZA}


# ---------------------------------------------------------------------------------------------- confronto
def abbina(base: list[Corpo], altri: list[Corpo], soglia: float = 0.5) -> list[tuple[Corpo, Corpo, float]]:
    """Coppie (corpo di base, corpo Zornade, IoU) con sovrapposizione IoU ≥ soglia; ogni corpo Zornade una volta sola."""
    if not base or not altri:
        return []
    albero = STRtree([c.sagoma for c in altri])
    usati, out = set(), []
    for b in base:
        migliore, iou_m = None, soglia
        for i in albero.query(b.sagoma):
            if i in usati:
                continue
            a = altri[i].sagoma
            inter = b.sagoma.intersection(a).area
            if inter <= 0:
                continue
            iou = inter / b.sagoma.union(a).area
            if iou >= iou_m:
                migliore, iou_m = i, iou
        if migliore is not None:
            usati.add(migliore)
            out.append((b, altri[migliore], round(iou_m, 3)))
    return out


def confronta(base: list[Corpo], zorn: list[Corpo], soglia: float = 0.5) -> dict:
    """Confronto delle altezze di gronda: righe per corpo (database derivato ODbL) e riepilogo aggregato."""
    coppie = abbina(base, zorn, soglia)
    righe = [{"corpo": b.id, "edificio": b.edificio, "fonte_base": b.fonte_altezza, "licenza_base": b.licenza,
              "zornade_id": z.extra.get("zornade_id"), "fonte_zornade": z.fonte_altezza, "iou": iou,
              "h_base": round(b.gronda, 2), "h_zornade": round(z.gronda, 2), "differenza": round(z.gronda - b.gronda, 2)}
             for b, z, iou in coppie]
    d = [r["differenza"] for r in righe]
    rias = {"corpi_base": len(base), "corpi_zornade": len(zorn), "abbinati": len(righe), "soglia_iou": soglia}
    if d:
        rias |= {"differenza_media_m": round(statistics.fmean(d), 2), "differenza_mediana_m": round(statistics.median(d), 2),
                 "scarto_assoluto_medio_m": round(statistics.fmean(abs(x) for x in d), 2),
                 "rmse_m": round(math.sqrt(statistics.fmean(x * x for x in d)), 2),
                 "entro_1m_pct": round(100 * sum(abs(x) <= 1 for x in d) / len(d), 1),
                 "entro_3m_pct": round(100 * sum(abs(x) <= 3 for x in d) / len(d), 1)}
    return {"righe": righe, "riepilogo": rias}


def applica_altezze(base: list[Corpo], zorn: list[Corpo], soglia: float = 0.5) -> list[Corpo]:
    """Catena del § 4 per le zone senza DBT: ai corpi con un'altezza debole (o assente) si dà l'altezza di Zornade.
    I corpi cambiati diventano **ODbL** (copia nuova, licenza della sagoma originale citata in `extra`); quelli con
    un'altezza migliore (utente, LiDAR, DBT) non si toccano. Restituisce solo i corpi cambiati: vanno nell'archivio ODbL."""
    out = []
    for b, z, iou in abbina(base, zorn, soglia):
        debole = (not b.gronda) or any(b.fonte_altezza.startswith(x) for x in DEBOLI)
        if not debole:
            continue
        out.append(replace(b, gronda=z.gronda, colmo=z.colmo, tetto=z.tetto, falde=z.falde, licenza=LICENZA,
                           fonte_altezza=z.fonte_altezza, qualita=z.qualita,
                           extra=dict(b.extra, licenza_sagoma=b.licenza, fonte_sagoma_originale=b.fonte_sagoma,
                                      zornade_id=z.extra.get("zornade_id"), iou=iou)))
    return out


# ---------------------------------------------------------------------------------------------- prodotti ODbL
def leggimi_odbl(fonti_altezze: list[str]) -> str:
    oggi = dt.date.today().isoformat()
    return (
        "Database derivato – licenza ODbL 1.0 (Open Database License)\n"
        f"Prodotto da EuGEnio (eugenio.statocritico.it) il {oggi}.\n\n"
        "Contenuto: sagome di edifici OpenStreetMap e altezze fornite da Zornade, eventualmente unite a sagome CC BY 4.0\n"
        "(per esempio aggregati della Protezione Civile): i corpi che contengono dati di Zornade sono rilasciati in ODbL 1.0.\n\n"
        "Attribuzione obbligatoria:\n"
        "  © OpenStreetMap contributors (ODbL 1.0) – https://www.openstreetmap.org/copyright\n"
        "  Dati elaborati da Zornade – https://zornade.com\n"
        + "".join(f"  {f}\n" for f in fonti_altezze if f) +
        "\nCondivisione allo stesso modo: chi ridistribuisce questo database, o un database derivato, deve farlo con la\n"
        "stessa licenza ODbL 1.0 e mantenere queste attribuzioni. Testo della licenza:\n"
        "  https://opendatacommons.org/licenses/odbl/1-0/\n"
        "Le mappe e le statistiche aggregate prodotte da questo database sono opere prodotte: si citano con le stesse\n"
        "attribuzioni («Fonte: EuGEnio – eugenio.statocritico.it»).\n\n"
        "I dati non contengono informazioni personali; vietato usarli per re-identificare persone. Non sostituiscono\n"
        "visure ed estratti catastali ufficiali.\n")


def prepara(corpi: list[Corpo], uscita: Path, resoconto: dict | None = None, confronto: dict | None = None,
            sintetico: bool = False, crs: str = "EPSG:7791") -> dict:
    """Scrive in `uscita` (deve stare sotto un archivio `odbl/`): corpi.pmtiles, contesto/<cella>.json, confronto.csv,
    confronto.json (riepilogo), LEGGIMI_ODbL.txt e indice.json. Rifiuta corpi con un'altra licenza."""
    from . import tessere as T
    uscita = Path(uscita)
    if "odbl" not in {p.lower() for p in uscita.parts}:
        raise ValueError(f"{uscita}: i dati di Zornade vanno solo nell'archivio ODbL (cartella odbl/)")
    altre = {c.licenza for c in corpi} - {LICENZA}
    if altre:
        raise ValueError(f"corpi con licenza {altre}: nell'archivio ODbL solo corpi ODbL")
    uscita.mkdir(parents=True, exist_ok=True)
    feat = T.feature_da_corpi(corpi, crs)
    for f in feat:
        f["properties"]["attribuzione"] = ATTRIBUZIONE
        if sintetico:
            f["properties"]["sintetico"] = True
    esito = {"corpi": len(corpi), "licenza": LICENZA, "attribuzione": ATTRIBUZIONE, "attribuzione_html": ATTRIBUZIONE_HTML,
             "fonte": FONTE, "resoconto": resoconto or {}, "creato": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if feat:
        esito["tessere_corpi"] = T.corpi_pmtiles(feat, uscita / "corpi.pmtiles", LICENZA, ATTRIBUZIONE)
        esito["celle"] = T.celle_contesto(feat, uscita / "contesto", LICENZA, ATTRIBUZIONE)
    fonti_h = sorted({c.fonte_altezza for c in corpi})
    (uscita / "LEGGIMI_ODbL.txt").write_text(leggimi_odbl(fonti_h[:20]), encoding="utf-8")
    if confronto is not None:
        with open(uscita / "confronto.csv", "w", newline="", encoding="utf-8") as f:
            campi = ["corpo", "edificio", "fonte_base", "licenza_base", "zornade_id", "fonte_zornade", "iou",
                     "h_base", "h_zornade", "differenza"]
            w = csv.DictWriter(f, fieldnames=campi)
            w.writeheader()
            w.writerows(confronto["righe"])
        rias = dict(confronto["riepilogo"], licenza="CC BY 4.0 (statistiche aggregate, opera prodotta)",
                    attribuzione=ATTRIBUZIONE + "; altezze di base: vedi fonte_base in confronto.csv")
        (uscita / "confronto.json").write_text(json.dumps(rias, ensure_ascii=False, indent=1), encoding="utf-8")
        esito["confronto"] = confronto["riepilogo"]
    if sintetico:
        esito["sintetico"] = True
        esito["avviso"] = AVVISO_CAMPIONE
    (uscita / "indice.json").write_text(json.dumps(esito, ensure_ascii=False, indent=1), encoding="utf-8")
    return esito


def corpi_da_contesto(cartella: Path, crs: str = "EPSG:7791") -> list[Corpo]:
    """Corpi della Fase A dalle celle `contesto/*.json` (WGS84) → metri, per il confronto."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    visti, out = set(), []
    for p in sorted(Path(cartella).glob("*.json")):
        for f in json.loads(p.read_text(encoding="utf-8")).get("features", []):
            pr = f.get("properties", {})
            cid = str(f.get("id") or pr.get("id"))
            if cid in visti:
                continue
            visti.add(cid)
            out.append(Corpo(id=cid, edificio=str(pr.get("edificio", cid)), sagoma=transform(t.transform, shape(f["geometry"])),
                             quota_terreno=pr.get("quota_terreno"), gronda=float(pr.get("gronda") or 0), colmo=pr.get("colmo"),
                             fonte_sagoma=pr.get("fonte_sagoma", ""), licenza=pr.get("licenza", ""),
                             fonte_altezza=pr.get("fonte_altezza", ""), qualita=pr.get("qualita", "")))
    return out


# ---------------------------------------------------------------------------------------------- campione sintetico
AVVISO_CAMPIONE = ("Campione sintetico che imita un estratto di Zornade: sagome e altezze inventate sull'isolato sintetico "
                   "di Rimini, per provare lettura, archivio ODbL e confronto; non sono dati di Zornade né di OSM.")


def campione(dest: Path, seme: int = 7) -> Path:
    """GeoJSON (WGS84) che imita un estratto di Zornade sull'isolato sintetico della Fase A: sagome leggermente spostate,
    altezze con scarti di qualche decimetro (alcune di metri), una riga senza altezza e una da GlobalBuildingAtlas, che
    il lettore deve scartare."""
    import random
    from pyproj import Transformer
    from shapely import affinity
    from shapely.geometry import mapping
    from . import sintetico as S
    rnd = random.Random(seme)
    t = Transformer.from_crs(S.CRS, "EPSG:4326", always_xy=True)
    feat = []
    for k, (prop, g) in enumerate(S.uvl()):
        h = numero(prop["H_uvl"])
        g2 = affinity.translate(g, rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6))
        dh = rnd.choice([rnd.gauss(0.3, 0.4), rnd.gauss(0.3, 0.4), rnd.gauss(-1.5, 1.0)])
        p = {"osm_id": f"w{900000 + k}", "height_lidar": round(h + dh, 1), "height_source": "LiDAR PNRR (sintetico)",
             "survey_date": "2025-09", "height_quality": "media", "building": "yes", "sintetico": True}
        if k == 2:
            p["height_lidar"] = None
        if k == 3:
            p["height_source"] = "Global Building Atlas"
        feat.append({"type": "Feature", "geometry": mapping(transform(t.transform, g2)), "properties": p})
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"type": "FeatureCollection", "name": "zornade_campione_sintetico",
                                "avviso": AVVISO_CAMPIONE, "features": feat}, ensure_ascii=False), encoding="utf-8")
    return dest
