"""PMTiles vettoriali dei corpi e celle di contesto in GeoJSON.

Un PMTiles **per licenza** (`cc-by/<zona>/corpi.pmtiles`, `odbl/<zona>/corpi.pmtiles`): strato `corpi`, poligoni con
le proprietà del § 7 (corpo, edificio, quota del terreno, gronda, colmo, altezza da estrudere, tetto, falde, piani,
fonte della sagoma e dell'altezza, qualità, licenza). Zoom 13–16 (oltre il 16 MapLibre ingrandisce il 16).

Per i calcoli nella pagina 3D servono le sagome intere (le tessere vettoriali tagliano i poligoni ai bordi): si
scrivono anche celle GeoJSON di 0,01° × 0,01° (`contesto/<i>_<j>.json`, i = floor(lon·100), j = floor(lat·100)), così
la pagina legge solo le celle che coprono i 250 m attorno all'edificio. Tutti file statici serviti da Caddy.
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

from shapely.geometry import mapping, shape, box
from shapely.ops import transform

ESTENSIONE = 4096
ZOOM = (13, 16)
CELLA = 0.01
# campi di Corpo.extra che vanno anche nelle tessere e nelle celle (07/11/2026, DBTR: V_EDI_GPG e V_EDI_CT_USO_AVM)
# h_dbtr_scartata e stima_altezza: altezza del DBTR non plausibile portata alla stima (plausibilita.py, 07/11/2026)
EXTRA_PUBBLICI = ("foglio", "numero", "nome", "destinazione", "tipo_edificio", "altezza_dbtr", "h_dbtr_scartata", "stima_altezza")


def lonlat_a_tessera(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(max(min(lat, 85.0511), -85.0511))
    y = int((1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def limiti_mercatore(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """(ovest, sud, est, nord) della tessera in EPSG:3857."""
    r = 20037508.342789244
    t = 2 * r / 2 ** z
    return -r + x * t, r - (y + 1) * t, -r + (x + 1) * t, r - y * t


def a_mercatore(lon: float, lat: float) -> tuple[float, float]:
    r = 6378137.0
    return math.radians(lon) * r, math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * r


def scrivi_pmtiles(dest: Path, tiles: dict[tuple[int, int, int], bytes], tipo: str, limiti, zoom, metadati: dict) -> None:
    from pmtiles.tile import zxy_to_tileid, TileType, Compression
    from pmtiles.writer import write
    dest.parent.mkdir(parents=True, exist_ok=True)
    tt = {"mvt": TileType.MVT, "png": TileType.PNG, "jpg": TileType.JPEG}[tipo]
    lon0, lat0, lon1, lat1 = limiti
    with write(str(dest)) as w:
        for (z, x, y) in sorted(tiles, key=lambda k: zxy_to_tileid(*k)):
            w.write_tile(zxy_to_tileid(z, x, y), tiles[(z, x, y)])
        w.finalize({
            "tile_type": tt, "tile_compression": Compression.GZIP if tipo == "mvt" else Compression.NONE,
            "min_zoom": zoom[0], "max_zoom": zoom[1],
            "min_lon_e7": int(lon0 * 1e7), "min_lat_e7": int(lat0 * 1e7),
            "max_lon_e7": int(lon1 * 1e7), "max_lat_e7": int(lat1 * 1e7),
            "center_zoom": zoom[1] - 1, "center_lon_e7": int((lon0 + lon1) / 2 * 1e7),
            "center_lat_e7": int((lat0 + lat1) / 2 * 1e7)}, metadati)


def _proprieta_tessera(p: dict) -> dict:
    """Solo valori semplici (le tessere non portano liste né oggetti)."""
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.items()
            if isinstance(v, (str, int, float, bool)) and v is not None}


def corpi_pmtiles(feature: list[dict], dest: Path, licenza: str, attribuzione: str, zoom=ZOOM) -> int:
    """feature GeoJSON (WGS84) dei corpi, tutti con la stessa licenza → PMTiles MVT gzip. Restituisce le tessere."""
    import mapbox_vector_tile
    diverse = {f["properties"].get("licenza") for f in feature} - {licenza}
    if diverse:
        raise ValueError(f"corpi con licenza diversa da {licenza}: {diverse} (archivi separati per licenza)")
    geoms = [(shape(f["geometry"]), _proprieta_tessera(f["properties"])) for f in feature]
    if not geoms:
        raise ValueError("nessun corpo")
    lon0 = min(g.bounds[0] for g, _ in geoms); lat0 = min(g.bounds[1] for g, _ in geoms)
    lon1 = max(g.bounds[2] for g, _ in geoms); lat1 = max(g.bounds[3] for g, _ in geoms)
    merc = [(_valida(transform(lambda x, y, z=None: _merc_vett(x, y), g)), p) for g, p in geoms]
    merc = [(g, p) for g, p in merc if g is not None]
    tiles = {}
    for z in range(zoom[0], zoom[1] + 1):
        x0, y1 = lonlat_a_tessera(lon0, lat0, z)
        x1, y0 = lonlat_a_tessera(lon1, lat1, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                w, s, e, n = limiti_mercatore(z, x, y)
                margine = (e - w) * 64 / ESTENSIONE
                riq = box(w - margine, s - margine, e + margine, n + margine)
                dentro = []
                for g, p in merc:
                    if not g.intersects(riq):
                        continue
                    c = _solo_poligoni(g.intersection(riq))
                    if c is None:
                        continue
                    dentro.append({"geometry": c.wkt, "properties": p})
                if not dentro:
                    continue
                dati = mapbox_vector_tile.encode([{"name": "corpi", "features": dentro}],
                                                 default_options={"quantize_bounds": (w, s, e, n), "extents": ESTENSIONE,
                                                                  "y_coord_down": False})
                tiles[(z, x, y)] = gzip.compress(dati)
    scrivi_pmtiles(dest, tiles, "mvt", (lon0, lat0, lon1, lat1), zoom, {
        "name": "corpi", "attribution": attribuzione, "licenza": licenza,
        "vector_layers": [{"id": "corpi", "minzoom": zoom[0], "maxzoom": zoom[1],
                           "fields": {k: "String" for k in geoms[0][1]}}]})
    return len(tiles)


def _merc_vett(x, y):
    import numpy as np
    r = 6378137.0
    x = np.asarray(x); y = np.asarray(y)
    return np.radians(x) * r, np.log(np.tan(np.pi / 4 + np.radians(y) / 2)) * r


def celle_contesto(feature: list[dict], cartella: Path, licenza: str, attribuzione: str) -> int:
    """Celle GeoJSON 0,01° con le sagome intere (un corpo va in ogni cella che tocca)."""
    celle: dict[tuple[int, int], list] = {}
    for f in feature:
        g = shape(f["geometry"])
        x0, y0, x1, y1 = g.bounds
        for i in range(math.floor(x0 / CELLA), math.floor(x1 / CELLA) + 1):
            for j in range(math.floor(y0 / CELLA), math.floor(y1 / CELLA) + 1):
                celle.setdefault((i, j), []).append(f)
    cartella.mkdir(parents=True, exist_ok=True)
    for vecchia in cartella.glob("*.json"):          # una nuova preparazione sostituisce le celle della precedente
        vecchia.unlink()
    for (i, j), fs in celle.items():
        (cartella / f"{i}_{j}.json").write_text(json.dumps(
            {"type": "FeatureCollection", "licenza": licenza, "attribuzione": attribuzione, "features": fs},
            ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(celle)


def _solo_poligoni(g):
    """Solo le parti poligonali (Polygon/MultiPolygon) di una geometria; None se non ne restano.
    Serve perché l'arrotondamento delle coordinate può rendere autointersecante una sagoma con vertici
    vicinissimi e il ritaglio sulla tessera restituisce allora una GeometryCollection, che l'MVT rifiuta."""
    from shapely.geometry import MultiPolygon, Polygon
    if g is None or g.is_empty:
        return None
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    parti = []
    for q in getattr(g, "geoms", []):
        if isinstance(q, Polygon) and not q.is_empty:
            parti.append(q)
        elif isinstance(q, MultiPolygon):
            parti.extend(q.geoms)
    if not parti:
        return None
    return parti[0] if len(parti) == 1 else MultiPolygon(parti)


def _valida(g):
    """Sagoma valida (make_valid se serve), ridotta alle parti poligonali."""
    if g is not None and not g.is_valid:
        from shapely.validation import make_valid
        g = make_valid(g)
    return _solo_poligoni(g)


def feature_da_corpi(corpi, da_crs: str = "EPSG:7791") -> list[dict]:
    """Corpi (sagome in metri, sistema da_crs) → feature GeoJSON WGS84 con le proprietà per tessere e contesto."""
    from pyproj import Transformer
    t = Transformer.from_crs(da_crs, "EPSG:4326", always_xy=True)
    out = []
    for c in corpi:
        g = transform(t.transform, c.sagoma)
        p = c.proprieta()
        p["altezza"] = round(c.colmo if c.colmo else c.gronda, 2)
        for k in EXTRA_PUBBLICI:                       # dati dell'edificio del DBTR (foglio, numero, nome, uso)
            v = (c.extra or {}).get(k)
            if isinstance(v, (str, int, float)) and v != "":
                p[k] = v
        p = {k: v for k, v in p.items() if v is not None and v != ""}
        out.append({"type": "Feature", "id": c.id, "geometry": _arrotonda(mapping(g)), "properties": p})
    return out


def _arrotonda(geo: dict, cifre: int = 7) -> dict:
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], cifre), round(c[1], cifre)]
    return {"type": geo["type"], "coordinates": r(geo["coordinates"])}
