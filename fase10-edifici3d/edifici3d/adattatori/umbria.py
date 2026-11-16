"""Umbria – Perugia: sagome OpenStreetMap con le altezze del LiDAR PST del MASE (16/11/2026).

Perché OSM: la Regione Umbria pubblica i «Fabbricati 2005-2010» senza altezze e il DB GeoTopografico 10k Tevere-Trasimeno
come WMS «non commerciale»; i portali regionali (`umbriageo`, `siat`, `dati.umbria.it`) non rispondono dal nostro
ambiente (verifica dell'08/11/2026, `documenti/CITTA_RIFERIMENTO_CENTRO.md`). Le sagome vengono quindi da
**OpenStreetMap** (ODbL 1.0: archivio in `odbl/`, mai insieme agli archivi CC BY) e le altezze dal **DSM First − DTM
1 m del Piano Straordinario di Telerilevamento** (MASE, contratto 204, voli del 13–14/03/2014, «collaudato NO» nel quadro
di unione; CC BY 4.0, pagina «Distribuzione dati PST» del Geoportale Nazionale), scaricato dall'app
`https://sim.mase.gov.it/pst/` il 16/11/2026 (`documenti/PERUGIA_PST_2026-11-16.md`).

Altezza di ogni corpo, nell'ordine:
  1. DSM − DTM del PST (`altezze_dsm.annota`, mediana dei pixel dentro la sagoma ridotta di 1 m), esito «ok»/«pochi_pixel»;
  2. tag OSM `height`, poi `building:levels` × 3 m (edifici non presenti nel rilievo del 2014 o troppo piccoli);
  3. mediana dei vicini entro 100 m (`stima_gronda` di `annota`), poi stima dall'uso (`plausibilita.stima_uso`).
Sempre con la fonte dichiarata nel corpo (`fonte_altezza`, `qualita`).

  python -m edifici3d.adattatori.umbria osm-geojson --osm perugia.osm --crs EPSG:7792 --uscita perugia_osm.geojson
  python -m edifici3d.altezze_dsm annota --file perugia_osm.geojson --dsm dsm/*.tiff --dtm dtm/*.tiff \\
         --crs-raster EPSG:4326 --uscita perugia_pst.geojson
  python -m edifici3d --zona umbria_perugia prepara-regione --file perugia_pst.geojson --dtm dtm_perugia_7792.tif \\
         --archivio ARCH --comune perugia --parziale --nome "…"
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo
from .. import altezze_dsm as AD
from ..modello import uso_da

RILIEVO = "LiDAR PST 2014, 1 m"
ATTRIBUZIONE = ("© OpenStreetMap contributors (ODbL 1.0); altezze da DSM − DTM 1 m: Ministero dell'Ambiente e della "
                "Sicurezza Energetica – Geoportale Nazionale, Banca dati PST (CC BY 4.0)")


def _altezza_osm(p: dict) -> tuple[float | None, str]:
    from ..osm import altezza
    return altezza(p)


def _corpo_osm_pst(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    if g.area < 2:
        return None
    uso = uso_da(osm_building=p.get("building"))
    piccolo = g.area < 15
    es = p.get("dsm_esito")
    h_osm, fonte_osm = _altezza_osm(p)
    if p.get("dsm_gronda") is not None and es in ("ok", "pochi_pixel") and float(p["dsm_gronda"]) >= AD.SOGLIA_ALTO:
        r = AD.gronda_da_campi(p, uso, piccolo=piccolo, rilievo=RILIEVO)
    elif h_osm and 1.5 <= h_osm <= 250:
        perche = {"non_presente": "non presente nel rilievo PST 2014", "pochi_pixel": "sagoma piccola per il rilievo",
                  "fuori": "fuori dal rilievo"}.get(es, "fuori dal rilievo")
        r = {"gronda": round(float(h_osm), 2), "fonte": f"{fonte_osm} ({perche})", "origine": "osm",
             "qualita": "altezza da OpenStreetMap", "extra": {k: p[k] for k in ("dsm_esito", "dsm_pixel") if p.get(k) is not None}}
    else:
        r = AD.gronda_da_campi(p, uso, piccolo=piccolo, rilievo=RILIEVO)
    q = AD.quota_corpo(p, quota_dtm)
    if q is None:
        return None
    oid = str(p.get("osm_id"))
    edificio = str(p.get("osm_edificio") or oid)
    colmo = p.get("dsm_colmo")
    extra = {"regione": "Umbria", "osm_building": p.get("building"), "origine_altezza": r["origine"],
             "rilievo": RILIEVO, **r["extra"]}
    if r["origine"] == "dsm" and colmo is not None and float(colmo) > r["gronda"]:
        extra["colmo_dsm"] = round(float(colmo), 2)
    if p.get("name"):
        extra["nome"] = p["name"]
    return Corpo(id=f"pg{oid}", edificio=f"pg{edificio}", sagoma=g, quota_terreno=q, gronda=r["gronda"], tetto="piano",
                 fonte_sagoma=OSM_PST.fonte, licenza=OSM_PST.licenza, fonte_altezza=r["fonte"], qualita=r["qualita"],
                 uso=uso, extra=extra)


OSM_PST = Adattatore("umbria_osm_pst", "OpenStreetMap – edifici (sagome), Umbria", "ODbL 1.0", ATTRIBUZIONE,
                     "EPSG:7792", ("osm_id", "building"), False, _corpo_osm_pst)

ADATTATORI = (OSM_PST,)


def osm_geojson(osm_file, crs: str, uscita) -> dict:
    """XML OSM (API o Overpass `out body`) → GeoJSON delle sagome nel sistema `crs` (way chiuse e multipoligoni con i
    cortili, stesso lettore dell'archivio di prova e del ripiego al volo: `osm_campione.edifici_da_xml`)."""
    import json
    from pathlib import Path
    from shapely.geometry import mapping
    from ..osm_campione import edifici_da_xml
    el = edifici_da_xml(Path(osm_file).read_bytes(), crs=crs)
    feats = [{"type": "Feature", "geometry": mapping(g), "properties": {k: v for k, v in t.items() if v is not None}}
             for t, g in el]
    d = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": crs}}, "features": feats}
    Path(uscita).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return {"sagome": len(feats), "file": str(uscita)}


def main(argv=None) -> int:
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(prog="python -m edifici3d.adattatori.umbria")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("osm-geojson", help="XML OSM → GeoJSON delle sagome per altezze_dsm annota")
    s.add_argument("--osm", type=Path, required=True); s.add_argument("--crs", default="EPSG:7792")
    s.add_argument("--uscita", type=Path, required=True)
    a = ap.parse_args(argv)
    print(json.dumps(osm_geojson(a.osm, a.crs, a.uscita), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
