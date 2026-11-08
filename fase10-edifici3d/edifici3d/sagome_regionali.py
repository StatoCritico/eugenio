"""Sagome regionali al volo con le altezze di OpenStreetMap (08/11/2026, decisione di Paolo).

Livello della cascata delle fonti delle pagine 3D tra il DB topografico con le altezze (archivi DBTR dei comuni) e il
ripiego OpenStreetMap: dove la Regione pubblica le sagome degli edifici con una licenza aperta e un servizio WFS ma
**senza altezze** (il Veneto, IODL 2.0: `fonti/sagome_regionali.toml`; dall'08/11/2026 anche le regioni di
`fonti/sagome_regionali.d/`: Sardegna in WFS, Campania in ArcGIS REST; Bolzano e Trento no, vedi il README), il server chiede le sagome intorno al punto
e dà a ognuna l'altezza:
  1. dell'**edificio OSM che le si sovrappone di più** (almeno il 10 % della sagoma regionale) con il tag `height`, poi
     `building:levels` × 3 m (origine `osm_height` / `osm_piani`, licenza dell'altezza ODbL 1.0);
  2. altrimenti la **mediana dei corpi DBTR vicini** (entro 200 m, almeno 3: `dbtr_vicini`, la fa il server con gli
     archivi che ha) o, senza, la **mediana dei vicini con l'altezza da OSM** (sagome regionali appena abbinate ed edifici
     OSM con height o piani, entro 200 m, almeno 3: `osm_vicini`);
  3. altrimenti **9 m** fissi (`fissa`).
Sempre dichiarata per corpo (`fonte_altezza`, `origine_altezza`). Gli edifici OSM che non si sovrappongono a nessuna
sagoma regionale (meno del 20 % della loro area: costruiti dopo il 2022, oltre il confine della regione) restano come
corpi OSM. Tetti: la cascata dei tetti del sito (ipotesi 22°/32°, `tetti.py`).
"""
from __future__ import annotations

import math
import tomllib
from pathlib import Path

FONTI = Path(__file__).resolve().parents[1] / "fonti" / "sagome_regionali.toml"
SOVRAPPOSIZIONE_MIN = 0.10        # quota della sagoma regionale coperta dall'edificio OSM per prenderne l'altezza
OSM_DOPPIO = 0.20                 # quota dell'edificio OSM coperta da sagome regionali oltre la quale non si aggiunge
ALTEZZA_FISSA = 9.0
RAGGIO_VICINI = 200.0
MINIMO_VICINI = 3
# usi del catalogo nazionale dei DB topografici (stesso schema del DBTR ER, uvl.USI): prime due cifre di edi_uso
USI = {"01": "residenziale", "02": "uffici", "0302": "ospedale", "0303": "scuola", "03": "uffici", "07": "commerciale",
       "08": "capannone", "09": "capannone", "1002": "palestra"}


def carica(file: Path = FONTI) -> list[dict]:
    """Fonti di `sagome_regionali.toml` più quelle dei file `sagome_regionali.d/*.toml` accanto (una regione per file,
    08/11/2026), nell'ordine: prima il file principale, poi gli altri per nome."""
    fonti: list[dict] = []
    file = Path(file)
    for f in [file] + sorted((file.parent / "sagome_regionali.d").glob("*.toml")):
        try:
            fonti += tomllib.loads(f.read_text(encoding="utf-8")).get("fonte", [])
        except (OSError, ValueError):
            continue
    return fonti


def fonte_nel_punto(lon: float, lat: float, fonti: list[dict] | None = None) -> dict | None:
    for f in fonti if fonti is not None else carica():
        r = f.get("riquadro_wgs84") or []
        if len(r) == 4 and r[0] <= lon <= r[2] and r[1] <= lat <= r[3]:
            return f
    return None


def url_wfs(fonte: dict, lon: float, lat: float, raggio: float) -> str:
    """URL delle sagome intorno al punto. WFS (predefinito): GetFeature 2.0.0 con il bbox nel sistema nativo, in forma
    breve «x0,y0,x1,y1,EPSG:nnnn» con l'ordine **Est, Nord** (verifica dell'08/11/2026: al Veneto in EPSG:6876 la forma
    breve E, N dà 129 sagome a Susegana, 757 a San Marco e 26 all'Ospedale dell'Angelo; la forma
    `urn:ogc:def:crs:EPSG::6876` vuole invece N, E – è quella del documento delle città – e in EPSG:4326 il WFS
    restituisce 0 elementi). ArcGIS REST (`servizio_tipo = "arcgis"`, 08/11/2026, Campania): `…/MapServer/<n>/query` con
    l'inviluppo nel sistema nativo (`inSR`), il filtro `filtro` (where) e la risposta in GeoJSON (WGS84: `crs_risposta`)."""
    from pyproj import Transformer
    from urllib.parse import urlencode
    x, y = Transformer.from_crs("EPSG:4326", fonte["crs"], always_xy=True).transform(lon, lat)
    if fonte.get("servizio_tipo") == "arcgis":
        q = {"where": fonte.get("filtro") or "1=1",
             "geometry": f"{x - raggio:.0f},{y - raggio:.0f},{x + raggio:.0f},{y + raggio:.0f}",
             "geometryType": "esriGeometryEnvelope", "inSR": fonte["crs"].split(":")[-1],
             "spatialRel": "esriSpatialRelIntersects", "outFields": fonte.get("campi") or "*", "returnGeometry": "true",
             "f": "geojson", "resultRecordCount": int(fonte.get("massimo", 2000))}
        return f"{fonte['servizio'].rstrip('/')}/query?{urlencode(q)}"
    b = f"{x - raggio:.0f},{y - raggio:.0f},{x + raggio:.0f},{y + raggio:.0f},{fonte['crs']}"
    return (f"{fonte['wfs']}?service=WFS&version=2.0.0&request=GetFeature&typeNames={fonte['tipo']}&bbox={b}"
            f"&outputFormat=application/json&count={int(fonte.get('massimo', 5000))}")


def campi_tenuti(fonte: dict) -> tuple:
    """Proprietà delle sagome da tenere nella copia del server (oltre alla geometria): quelle del catalogo nazionale
    (edi_ty, edi_uso, edi_stat) più il campo dell'uso della fonte, se diverso (`campo_uso`)."""
    c = ["edi_ty", "edi_uso", "edi_stat"]
    if fonte.get("campo_uso") and fonte["campo_uso"] not in c:
        c.append(fonte["campo_uso"])
    return tuple(c)


def uso_della_fonte(fonte: dict, p: dict) -> tuple:
    """(uso, codice) di una sagoma: con `campo_uso` e la tabella `usi` della fonte (prefisso o parte del testo → uso,
    08/11/2026: Sardegna «sede di ospedale», Campania codici CTR «3111000O»), altrimenti `edi_uso` del catalogo
    nazionale (Veneto)."""
    campo = fonte.get("campo_uso")
    if not campo:
        return uso_da_codice(p.get("edi_uso")), p.get("edi_uso")
    v = str(p.get(campo) or "").strip()
    if not v:
        return None, None
    usi = fonte.get("usi") or {}
    for k in sorted(usi, key=len, reverse=True):
        if v.startswith(k) or (len(k) > 3 and k.lower() in v.lower()):
            return (usi[k] or None), v
    return None, v


def uso_da_codice(cod) -> str | None:
    c = str(cod or "").strip()
    return USI.get(c[:4]) or USI.get(c[:2]) if c else None


def _poligoni(geom: dict, area_min: float = 1.0):
    from shapely.geometry import shape
    from shapely.validation import make_valid
    if not geom:
        return None
    g = shape({"type": geom["type"], "coordinates": _senza_z(geom["coordinates"])})
    if not g.is_valid:
        g = make_valid(g)
    g = g if g.geom_type in ("Polygon", "MultiPolygon") else None
    return g if g is not None and not g.is_empty and g.area > area_min else None


def _senza_z(c):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
        return list(c[:2])
    return [_senza_z(x) for x in c]


def _mediana(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def unisci(wfs: dict, fonte: dict, osm: dict, lon: float, lat: float) -> dict:
    """GeoJSON del WFS regionale (sistema nativo) + risposta del ripiego OSM (WGS84) → FeatureCollection WGS84 delle sagome
    regionali con l'altezza da OSM (o dai vicini o 9 m) più gli edifici OSM senza sagoma regionale. Stesse proprietà delle
    celle di contesto degli archivi (id, edificio, gronda, altezza, piani, fonti, licenza, qualità, origine_altezza)."""
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    from shapely.strtree import STRtree
    from pyproj import Transformer
    from .osm_campione import crs_metrico
    met = crs_metrico(lon)
    nat_met = Transformer.from_crs(fonte.get("crs_risposta") or fonte["crs"], met, always_xy=True).transform
    wgs_met = Transformer.from_crs("EPSG:4326", met, always_xy=True).transform
    met_wgs = Transformer.from_crs(met, "EPSG:4326", always_xy=True).transform
    # edifici OSM in metri, con l'altezza dal dato (height o piani) se c'è
    osm_f = [f for f in (osm or {}).get("features", []) if f.get("geometry")]
    osm_g = []
    for f in osm_f:
        try:
            g = transform(wgs_met, shape(f["geometry"]))
            osm_g.append(g if g.is_valid else g.buffer(0))
        except Exception:   # noqa: BLE001
            osm_g.append(None)
    validi = [(i, g) for i, g in enumerate(osm_g) if g is not None and not g.is_empty]
    albero = STRtree([g for _, g in validi]) if validi else None
    reg = []
    for k, f in enumerate((wfs or {}).get("features", [])):
        try:
            g = _poligoni(f.get("geometry"), 0.0 if fonte.get("crs_risposta") else 1.0)   # gradi: l'area si guarda dopo
        except Exception:   # noqa: BLE001
            g = None
        if g is None:
            continue
        g = transform(nat_met, g)
        if g.area < 4:
            continue
        reg.append((f, g))
    coperta = [0.0] * len(osm_f)
    out = []
    for f, g in reg:
        p0 = f.get("properties") or {}
        rid = str(f.get("id") or p0.get("id") or len(out)).split(".")[-1]
        meglio, area_max = None, 0.0
        for j in (albero.query(g) if albero is not None else []):
            i, og = validi[int(j)]
            try:
                a = g.intersection(og).area
            except Exception:   # noqa: BLE001
                continue
            coperta[i] += a
            if a > area_max:
                meglio, area_max = i, a
        uso, cod = uso_della_fonte(fonte, p0)
        p = {"id": f"{fonte['id']}_{rid}", "edificio": f"{fonte['id']}_{rid}", "fonte_sagoma": fonte["attribuzione"],
             "licenza": fonte["licenza"], "regione_sagoma": fonte["id"], "area": round(g.area, 1),
             "uso": uso, "codice_uso": cod, "codice_tipo": p0.get("edi_ty")}
        po = (osm_f[meglio].get("properties") or {}) if meglio is not None else {}
        if meglio is not None and area_max >= SOVRAPPOSIZIONE_MIN * g.area and po.get("origine_altezza") in ("osm_height", "osm_piani"):
            h = float(po.get("gronda") or po.get("altezza"))
            p.update(gronda=h, altezza=h, piani=max(1, round(h / 3)), origine_altezza=po["origine_altezza"], licenza=f"{fonte['licenza']}; altezza ODbL 1.0",
                     qualita="altezza da OpenStreetMap", osm_id=po.get("id"),
                     fonte_altezza=f"{po.get('fonte_altezza') or 'OSM'} (edificio OSM {po.get('id')} sovrapposto per il {100 * area_max / g.area:.0f} %)")
        else:
            p.update(gronda=ALTEZZA_FISSA, altezza=ALTEZZA_FISSA, piani=3, origine_altezza="fissa", qualita="stima",
                     fonte_altezza=f"stima: {ALTEZZA_FISSA:g} m fissi (nessun edificio OSM con l'altezza sovrapposto)")
        out.append({"type": "Feature", "geometry": mapping(transform(met_wgs, g)), "properties": p, "_g": g})
    # edifici OSM senza sagoma regionale: restano come corpi OSM
    extra = []
    for i, f in enumerate(osm_f):
        g = osm_g[i]
        if g is None or g.is_empty or coperta[i] > OSM_DOPPIO * g.area:
            continue
        extra.append(f)
    for f in out:
        f.pop("_g", None)
    d = {"type": "FeatureCollection", "features": out + extra, "corpi": len(out) + len(extra),
         "sagome": {"regione": fonte["regione"], "nome": fonte["nome"], "licenza": fonte["licenza"], "attribuzione": fonte["attribuzione"],
                    "scheda": fonte["scheda"], "corpi": len(out), "con_altezza_osm": sum(1 for f in out if f["properties"]["origine_altezza"] != "fissa"),
                    "osm_aggiunti": len(extra)},
         "licenza": f"{fonte['licenza']} (sagome); ODbL 1.0 (altezze e edifici OSM)",
         "attribuzione": f"{fonte['attribuzione']}; altezze ed edifici aggiunti © OpenStreetMap contributors (ODbL 1.0)"}
    return d


def altezze_da_vicini_osm(features: list[dict], raggio: float = RAGGIO_VICINI, minimo: int = MINIMO_VICINI) -> int:
    """Sagome regionali ancora a 9 m fissi → mediana dei vicini con l'altezza da OSM (sagome abbinate ed edifici OSM con
    height o piani) entro `raggio` m, se sono almeno `minimo` (origine `osm_vicini`)."""
    from .osm_campione import _centro
    con = []
    for f in features:
        p = f.get("properties") or {}
        if p.get("origine_altezza") in ("osm_height", "osm_piani"):
            c = _centro(f.get("geometry"))
            if c is not None:
                con.append((c[0], c[1], float(p.get("gronda"))))
    if not con:
        return 0
    lat0 = sum(v[1] for v in con) / len(con)
    kx, ky = 111320.0 * math.cos(math.radians(lat0)), 110574.0
    n = 0
    for f in features:
        p = f.get("properties") or {}
        if p.get("origine_altezza") != "fissa" or not p.get("regione_sagoma"):
            continue
        c = _centro(f.get("geometry"))
        if c is None:
            continue
        hs = [h for lo, la, h in con if ((lo - c[0]) * kx) ** 2 + ((la - c[1]) * ky) ** 2 <= raggio * raggio]
        if len(hs) < minimo:
            continue
        h = round(_mediana(hs) * 2) / 2
        p.update(gronda=h, altezza=h, piani=max(1, round(h / 3)), qualita="stima", origine_altezza="osm_vicini",
                 fonte_altezza=f"stima: mediana dei vicini con l'altezza da OpenStreetMap ({len(hs)} entro {raggio:g} m: {h:g} m)")
        n += 1
    return n
