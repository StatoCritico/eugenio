"""Archivio di prova da OpenStreetMap per un quartiere (05/11/2026, seconda pubblicazione).

Serve a vedere il servizio vero di Modelli 3D (mappa 2D → «Genera il 3D» con sagome vere allineate all'ortofoto) prima
che il GeoPackage UVL del DBTR sia sul server: il DBTR si ottiene solo **prenotando un'estrazione** dalla pagina
«Download DB Topografico» del Geoportale della Regione (modulo con reCAPTCHA, consegna per email: la fa Paolo, a mano) e
il WFS del DBTR non risponde (401 il 03/11, 404 il 05/11/2026).

Fonti, tutte pubbliche e senza blocchi da aggirare:
  * sagome: **una sola** chiamata all'API di OpenStreetMap (`/api/0.6/map?bbox=…`, riquadro piccolo: al più ~2×2 km,
    come chiede la policy dell'API); archivio **ODbL** separato (`odbl/<nome>/prodotti/`), attribuzione «© OpenStreetMap
    contributors (ODbL 1.0)»;
  * altezze: `height` → `building:levels` × 3 m → **stima** dichiarata (predefinita 9 m, «altezza non presente in OSM»);
  * terreno: DTM 5×5 m della Regione Emilia-Romagna dal WCS pubblico `wcs/dtm5x5` (CC BY 4.0), un solo GetCoverage del
    riquadro; file `terreno.pmtiles` e `dtm_cog.tif` con la loro licenza scritta nell'indice (file separati dalle sagome).

  python -m edifici3d osm-campione --riquadro 12.5600 44.0555 12.5735 44.0640 --nome rimini-prova \\
         --archivio /srv/energia/dati/edifici [--altezza-stima 9] [--senza-dtm] [--osm file.osm] [--dtm grezzi/dtm5.tif]

Rigenerare l'archivio di prova con i fori dei multipoligoni, senza nessuna richiesta in rete (07/11/2026):
  python -m edifici3d osm-campione --riquadro … --nome rimini-prova --archivio … \\
         --osm …/odbl/rimini-prova/grezzi/mappa.osm --dtm …/odbl/rimini-prova/grezzi/dtm5.tif
"""
from __future__ import annotations

import json
import math
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import Polygon
from shapely.validation import make_valid

from . import osm as OSM
from .modello import Corpo, numero, uso_da

log = logging.getLogger("edifici3d")

API = "https://api.openstreetmap.org/api/0.6/map"
MAX_GRADI2 = 0.0004            # ~2×2 km alle nostre latitudini: un quartiere, non una città
USER_AGENT = "EuGEnio/1.0 (+https://eugenio.statocritico.it; archivio di prova di un quartiere)"


def url_mappa(riquadro: tuple[float, float, float, float]) -> str:
    lo0, la0, lo1, la1 = riquadro
    if not (lo0 < lo1 and la0 < la1):
        raise ValueError("riquadro: lon_min lat_min lon_max lat_max")
    if (lo1 - lo0) * (la1 - la0) > MAX_GRADI2:
        raise ValueError(f"riquadro troppo grande per l'API di OSM ({(lo1 - lo0) * (la1 - la0):.5f} gradi², massimo {MAX_GRADI2}): "
                         "per una zona più grande usa l'estratto Geofabrik sul server")
    return f"{API}?bbox={lo0:.6f},{la0:.6f},{lo1:.6f},{la1:.6f}"


def edifici_da_xml(testo: bytes | str, crs: str = "EPSG:7791") -> list[tuple[dict, Polygon]]:
    """XML dell'API OSM → [(tag, poligono in metri)] delle way chiuse con `building` e delle relazioni multipolygon
    `building` (07/11/2026): le way `outer` (anche aperte, unite tra loro) e `inner` si ricompongono con polygonize,
    i fori (cortili) restano (outer − inner); un multipoligono con più parti diventa più poligoni, `r<id>_<k>`."""
    from pyproj import Transformer
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    radice = ET.fromstring(testo)
    nodi = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in radice.iter("node")}
    vie = {}
    for w in radice.iter("way"):
        vie[w.get("id")] = ([nd.get("ref") for nd in w.iter("nd")], {x.get("k"): x.get("v") for x in w.iter("tag")})

    def metri(refs):
        xs, ys = t.transform([nodi[r][0] for r in refs], [nodi[r][1] for r in refs])
        return list(zip(xs, ys))

    def valido(g):
        """Poligoni validi (fori compresi) da una geometria qualsiasi."""
        if g is None or g.is_empty:
            return []
        if not g.is_valid:
            g = make_valid(g)
        if g.geom_type == "Polygon":
            return [g] if g.area > 0 else []
        return [x for x in getattr(g, "geoms", []) for x in valido(x)]

    def poligono(refs):
        if len(refs) < 4 or refs[0] != refs[-1] or any(r not in nodi for r in refs):
            return None
        parti = valido(Polygon(metri(refs)))
        return max(parti, key=lambda p: p.area) if parti else None

    def anelli(ruolo, membri):
        """Linee delle way di un ruolo, unite e chiuse in poligoni (le way aperte si saldano agli estremi)."""
        linee = []
        for m in membri:
            if (m.get("role") or "outer") != ruolo:          # ruolo vuoto = outer
                continue
            refs = vie.get(m.get("ref"), ([], {}))[0]
            if len(refs) >= 2 and all(r in nodi for r in refs):
                linee.append(LineString(metri(refs)))
        if not linee:
            return None
        poli = [p for p in polygonize(unary_union(linee)) if p.area > 0]
        if not poli:
            return None
        return unary_union([Polygon(p.exterior) for p in poli])     # le aree racchiuse, senza i buchi del polygonize

    out = []
    for wid, (refs, tag) in vie.items():
        if tag.get("building") and tag.get("building") != "no":
            g = poligono(refs)
            if g is not None:
                out.append(({**tag, "osm_id": f"w{wid}"}, g))
    for r in radice.iter("relation"):
        tag = {x.get("k"): x.get("v") for x in r.iter("tag")}
        if tag.get("type") != "multipolygon" or not tag.get("building") or tag.get("building") == "no":
            continue
        membri = [x for x in r.iter("member") if x.get("type") == "way"]
        esterno = anelli("outer", membri)
        if esterno is None:
            continue
        interno = anelli("inner", membri)
        g = esterno.difference(interno) if interno is not None else esterno
        for k, p in enumerate(sorted(valido(g), key=lambda p: -p.area)):
            out.append(({**tag, "osm_id": f"r{r.get('id')}_{k}", "osm_edificio": f"r{r.get('id')}"}, p))
    return out


def corpi_con_stima(elementi, altezza_stima: float | None) -> list[Corpo]:
    """Corpi OSM (osm.corpi_da_osm); senza altezza in OSM, la stima dichiarata (o niente se altezza_stima è None)."""
    corpi = OSM.corpi_da_osm(elementi)
    for c in corpi:
        if c.gronda <= 0 and altezza_stima:
            c.gronda = float(altezza_stima)
            c.piani = c.piani or max(1, round(altezza_stima / 3))
            c.fonte_altezza = f"stima: altezza non presente in OSM ({altezza_stima:g} m)"
            c.qualita = "stima"
    return corpi


def prepara(riquadro, archivio: Path, nome: str, altezza_stima: float | None = 9.0, dtm: bool = True,
            osm_file: Path | None = None, scarica=None, dtm_file: Path | None = None) -> dict:
    """Scarica (o legge) l'OSM del riquadro, prende il DTM 5 m (dal WCS, oppure `dtm_file`: il `grezzi/dtm5.tif` già
    scaricato o un quadrante del DTM, ritagliato) e prepara `odbl/<nome>/prodotti/`."""
    import re
    if not re.fullmatch(r"[a-z0-9-]{3,40}", nome):
        raise ValueError("nome: minuscole, cifre e trattini")
    from pyproj import Transformer
    from . import fonti as F
    from .__main__ import prepara_corpi
    if scarica is None:
        import httpx

        def scarica(url):
            with httpx.Client(timeout=120, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as c:
                r = c.get(url)
                r.raise_for_status()
                return r.content
    grezzi = archivio / "odbl" / nome / "grezzi"
    grezzi.mkdir(parents=True, exist_ok=True)
    if osm_file:
        xml = Path(osm_file).read_bytes()
    else:
        xml = scarica(url_mappa(riquadro))
        (grezzi / "mappa.osm").write_bytes(xml)
    elementi = edifici_da_xml(xml)
    corpi = corpi_con_stima(elementi, altezza_stima)
    log.info("OSM: %d edifici, %d corpi", len(elementi), len(corpi))
    attribuzione = OSM.ATTRIBUZIONE
    if dtm:
        f = F.fonti(F.carica_zona("emilia_romagna"))["dtm5"]
        t = Transformer.from_crs("EPSG:4326", "EPSG:7791", always_xy=True)
        x0, y0 = t.transform(riquadro[0], riquadro[1]); x1, y1 = t.transform(riquadro[2], riquadro[3])
        m = 300                                                        # margine per il contesto (250 m) e le ombre
        bb = (round(x0 - m, -1), round(y0 - m, -1), round(x1 + m, -1), round(y1 + m, -1))
        dest = grezzi / "dtm5.tif"
        if dtm_file:                                                   # file già sul disco: nessuna richiesta al WCS
            from . import dtm_locale as DL
            dtm_file = Path(dtm_file)
            if DL.grande(dtm_file):
                DL.ritaglia(dtm_file, bb, dest)
                dtm_file = dest
            log.info("DTM da file: %s", dtm_file)
        else:
            dati = scarica(F.url_wcs(f, bb))
            if not dati[:4] in (b"II*\x00", b"MM\x00*"):
                raise RuntimeError("il WCS del DTM non ha risposto con un GeoTIFF")
            dest.write_bytes(dati)
            dtm_file = dest
        from . import dtm as D
        for c in corpi:
            q = D.quota(dtm_file, c.sagoma)
            if q:
                c.quota_terreno = q["minimo"]
                c.extra["quota_mediana"] = round(q["mediana"], 2)
    uscita = archivio / "odbl" / nome / "prodotti"
    uscita.mkdir(parents=True, exist_ok=True)
    extra = {"nome": f"OpenStreetMap – {nome} (archivio di prova)", "prova": True,
             "fonti_file": {"corpi.pmtiles": "© OpenStreetMap contributors (ODbL 1.0)", "contesto/": "© OpenStreetMap contributors (ODbL 1.0)"}}
    if dtm_file:
        extra["fonti_file"].update({"terreno.pmtiles": "Regione Emilia-Romagna – DTM 5×5 m (CC BY 4.0)",
                                    "dtm_cog.tif": "Regione Emilia-Romagna – DTM 5×5 m (CC BY 4.0)"})
        extra["attribuzione_terreno"] = "Regione Emilia-Romagna – DTM 5×5 m (CC BY 4.0)"
    esito = prepara_corpi(corpi, dtm_file, uscita, OSM.LICENZA, attribuzione, crs="EPSG:7791", extra=extra)
    (archivio / "odbl" / nome / "LICENZE.txt").write_text(
        "Sagome degli edifici: © OpenStreetMap contributors, Open Database License 1.0 (https://www.openstreetmap.org/copyright).\n"
        "Il contenuto di prodotti/corpi.pmtiles e prodotti/contesto/ è un database derivato ODbL: si ridistribuisce con la stessa\n"
        "licenza e questa attribuzione.\n"
        "Altezze: tag OSM height o building:levels × 3 m; dove mancano, stima dichiarata di EuGEnio nel campo fonte_altezza.\n"
        + ("Terreno (prodotti/terreno.pmtiles, prodotti/dtm_cog.tif, grezzi/dtm5.tif): Regione Emilia-Romagna – DTM 5×5 m, CC BY 4.0\n"
           "(https://geoportale.regione.emilia-romagna.it/notizie/servizi-e-applicazioni/dtm-novita-2025), dal WCS pubblico dtm5x5.\n"
           if dtm_file else ""), encoding="utf-8")
    return esito


# ---------------------------------------------------------------------------------------------- ripiego al volo
# Decisione di Paolo del 07/11/2026: dove non c'è un archivio di qualità (DBTR: fuori dall'Emilia-Romagna e nei comuni ER
# non ancora preparati) Modelli 3D usa gli edifici OSM intorno al punto, chiesti al momento all'API Overpass dal server
# (fase4-server/servizio/edifici_osm.py, GET /api/edifici/osm). Stesse regole di questo archivio di prova (way chiuse,
# multipoligoni con i cortili e way aperte, altezza height → building:levels × 3 m → stima dichiarata); niente DTM.
RAGGIO_VOLO = 400              # m: i 250 m del contesto della pagina + lo spostamento del punto dentro la cella della copia


def query_punto(lon: float, lat: float, raggio: float = RAGGIO_VOLO) -> str:
    """Query Overpass (XML come l'API di OSM: nodi, way e relazioni con i loro membri) degli edifici entro `raggio` m."""
    a = f"around:{int(raggio)},{lat:.6f},{lon:.6f}"
    return (f'[out:xml][timeout:25];(way["building"]({a});relation["building"]["type"="multipolygon"]({a}););'
            "(._;>;);out body qt;")


def crs_metrico(lon: float) -> str:
    """Fuso UTM WGS84 del punto (32, 33 o 34 N), per aree e lunghezze corrette in tutta Italia."""
    return f"EPSG:326{32 if lon < 12 else 33 if lon < 18 else 34}"


def errore_overpass(testo: bytes | str) -> str | None:
    """Overpass risponde 200 anche quando la query va in timeout o finisce la memoria: lo dice in <remark>."""
    t = testo.decode("utf-8", "replace") if isinstance(testo, bytes) else testo
    i = t.find("<remark>")
    if i < 0:
        return None
    r = t[i + 8:t.find("</remark>", i)].strip()
    return r[:200] if "error" in r.lower() else None


def corpi_al_volo(testo: bytes | str, lon: float, lat: float, altezza_stima: float = 9.0) -> dict:
    """XML di Overpass → FeatureCollection WGS84 con le stesse proprietà delle celle di contesto degli archivi (id, edificio,
    gronda, altezza, fonte della sagoma e dell'altezza, licenza ODbL, qualità). Corpi senza altezza in OSM: stima dichiarata."""
    from .tessere import feature_da_corpi
    crs = crs_metrico(lon)
    corpi = corpi_con_stima(edifici_da_xml(testo, crs), altezza_stima)
    fs = feature_da_corpi(corpi, crs) if corpi else []
    for f in fs:
        f["properties"]["origine_altezza"] = origine_altezza(f["properties"])
    d = {"type": "FeatureCollection", "features": fs, "licenza": OSM.LICENZA, "attribuzione": OSM.ATTRIBUZIONE, "corpi": len(corpi)}
    conta_altezze(d)
    return d


# ---------------------------------------------------------------------------------------------- altezze stimate (07/11/2026)
# Decisione di Paolo del 07/11/2026: vicino a un comune coperto dal DBTR, l'altezza dei corpi OSM senza `height` né
# `building:levels` è la **mediana dei corpi DBTR vicini** (entro RAGGIO_VICINI m, almeno MINIMO_VICINI corpi con
# l'altezza del DB topografico, non stimata); altrove resta la stima fissa di 9 m. Sempre dichiarata come stima, con
# l'origine per corpo («origine_altezza»): osm_height, osm_piani, dbtr_vicini, fissa. Stessa regola nella pagina
# (edificio3d.js, altezzeDaVicini) per il DB topografico caricato nel browser.
RAGGIO_VICINI = 200.0
MINIMO_VICINI = 3
ORIGINI = ("osm_height", "osm_piani", "dbtr_vicini", "osm_vicini", "fissa")   # osm_vicini: sagome regionali (08/11/2026)


def origine_altezza(p: dict) -> str:
    """Origine dell'altezza di un corpo OSM dalle sue proprietà."""
    if p.get("origine_altezza") in ORIGINI:
        return p["origine_altezza"]
    f = str(p.get("fonte_altezza", ""))
    if f.startswith("OSM height"):
        return "osm_height"
    if f.startswith("OSM building:levels"):
        return "osm_piani"
    return "fissa"


def conta_altezze(d: dict) -> dict:
    """Conteggi per origine (chiave «altezze») e i due totali di prima (altezze_stimate, altezze_osm)."""
    n = {k: 0 for k in ORIGINI}
    for f in d.get("features", []):
        n[origine_altezza(f["properties"])] += 1
    d["altezze"] = n
    d["altezze_stimate"] = n["dbtr_vicini"] + n["osm_vicini"] + n["fissa"]
    d["altezze_osm"] = n["osm_height"] + n["osm_piani"]
    return d


def _centro(geom: dict) -> tuple[float, float] | None:
    g = geom.get("coordinates") if geom else None
    if not g:
        return None
    anello = g[0][0] if geom.get("type") == "MultiPolygon" else g[0]
    if not anello:
        return None
    return sum(q[0] for q in anello) / len(anello), sum(q[1] for q in anello) / len(anello)


def mediana(v: list[float]) -> float:
    s = sorted(v)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def altezza_dbtr_valida(p: dict) -> float | None:
    """Gronda di un corpo DBTR utile come vicino: numerica, tra 2 e 80 m, non stimata né portata alla stima."""
    try:
        g = float(p.get("gronda"))
    except (TypeError, ValueError):
        return None
    if not 2.0 <= g <= 80.0 or p.get("h_dbtr_scartata") not in (None, "") or "stima" in str(p.get("fonte_altezza", "")).lower():
        return None
    return g


def altezze_da_vicini(features: list[dict], vicini: list[tuple[float, float, float]], raggio: float = RAGGIO_VICINI,
                      minimo: int = MINIMO_VICINI, nome_fonte: str = "DBTR") -> int:
    """Corpi OSM con l'altezza fissa (origine «fissa») → mediana delle gronde dei corpi `vicini` (lon, lat, gronda) entro
    `raggio` m dal loro centro, se sono almeno `minimo`. Modifica le feature sul posto; restituisce quante ne ha cambiate.
    Ricerca a griglia (celle di ~raggio): veloce anche con migliaia di corpi."""
    if not features or not vicini:
        return 0
    lat0 = sum(v[1] for v in vicini[:50]) / min(len(vicini), 50)
    kx, ky = 111320.0 * math.cos(math.radians(lat0)), 110574.0
    passo = raggio
    griglia: dict[tuple[int, int], list[tuple[float, float, float]]] = {}
    for lo, la, g in vicini:
        x, y = lo * kx, la * ky
        griglia.setdefault((int(x // passo), int(y // passo)), []).append((x, y, g))
    cambiati = 0
    for f in features:
        p = f.get("properties") or {}
        if origine_altezza(p) != "fissa":
            continue
        c = _centro(f.get("geometry"))
        if c is None:
            continue
        x, y = c[0] * kx, c[1] * ky
        i, j = int(x // passo), int(y // passo)
        hs = [g for di in (-1, 0, 1) for dj in (-1, 0, 1) for (vx, vy, g) in griglia.get((i + di, j + dj), ())
              if (vx - x) ** 2 + (vy - y) ** 2 <= raggio * raggio]
        if len(hs) < minimo:
            continue
        h = round(mediana(hs) * 2) / 2
        p.update({"gronda": h, "altezza": h, "piani": max(1, round(h / 3)), "qualita": "stima", "origine_altezza": "dbtr_vicini",
                  "fonte_altezza": f"stima: mediana dei corpi {nome_fonte} vicini ({len(hs)} entro {raggio:g} m: {h:g} m)"})
        p.pop("colmo", None)
        cambiati += 1
    return cambiati


def voce_archivi(nome: str) -> dict:
    """Riga per /edifici3d/archivi.json (dopo gli archivi CC BY, che sono più affidabili)."""
    return {"base": f"/edifici3d/odbl/{nome}/prodotti/", "nome": f"OpenStreetMap – {nome} (archivio di prova)", "licenza": "ODbL 1.0"}


if __name__ == "__main__":   # pragma: no cover
    print(json.dumps(voce_archivi("rimini-prova")))
