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
         --archivio /srv/energia/dati/edifici [--altezza-stima 9] [--senza-dtm] [--osm file.osm]
"""
from __future__ import annotations

import json
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
    """XML dell'API OSM → [(tag, poligono in metri)] delle way chiuse con `building` e degli anelli esterni dei
    multipoligoni `building` (i fori si ignorano: per i prismi contano le sagome esterne)."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    radice = ET.fromstring(testo)
    nodi = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in radice.iter("node")}
    vie = {}
    for w in radice.iter("way"):
        vie[w.get("id")] = ([nd.get("ref") for nd in w.iter("nd")], {x.get("k"): x.get("v") for x in w.iter("tag")})

    def poligono(refs):
        if len(refs) < 4 or refs[0] != refs[-1] or any(r not in nodi for r in refs):
            return None
        xs, ys = t.transform([nodi[r][0] for r in refs], [nodi[r][1] for r in refs])
        g = Polygon(list(zip(xs, ys)))
        if not g.is_valid:
            g = make_valid(g)
            if g.geom_type == "MultiPolygon":
                g = max(g.geoms, key=lambda p: p.area)
            if g.geom_type != "Polygon":
                return None
        return g

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
        for k, m in enumerate(x for x in r.iter("member") if x.get("type") == "way" and x.get("role") == "outer"):
            if m.get("ref") in vie:
                g = poligono(vie[m.get("ref")][0])
                if g is not None:
                    out.append(({**tag, "osm_id": f"r{r.get('id')}_{k}"}, g))
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
            osm_file: Path | None = None, scarica=None) -> dict:
    """Scarica (o legge) l'OSM del riquadro, prende il DTM 5 m dal WCS e prepara `odbl/<nome>/prodotti/`."""
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
    dtm_file = None
    attribuzione = OSM.ATTRIBUZIONE
    if dtm:
        f = F.fonti(F.carica_zona("emilia_romagna"))["dtm5"]
        t = Transformer.from_crs("EPSG:4326", "EPSG:7791", always_xy=True)
        x0, y0 = t.transform(riquadro[0], riquadro[1]); x1, y1 = t.transform(riquadro[2], riquadro[3])
        m = 300                                                        # margine per il contesto (250 m) e le ombre
        bb = (round(x0 - m, -1), round(y0 - m, -1), round(x1 + m, -1), round(y1 + m, -1))
        url = F.url_wcs(f, bb)
        dtm_file = grezzi / "dtm5.tif"
        dati = scarica(url)
        if not dati[:4] in (b"II*\x00", b"MM\x00*"):
            raise RuntimeError("il WCS del DTM non ha risposto con un GeoTIFF")
        dtm_file.write_bytes(dati)
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


def voce_archivi(nome: str) -> dict:
    """Riga per /edifici3d/archivi.json (dopo gli archivi CC BY, che sono più affidabili)."""
    return {"base": f"/edifici3d/odbl/{nome}/prodotti/", "nome": f"OpenStreetMap – {nome} (archivio di prova)", "licenza": "ODbL 1.0"}


if __name__ == "__main__":   # pragma: no cover
    print(json.dumps(voce_archivi("rimini-prova")))
