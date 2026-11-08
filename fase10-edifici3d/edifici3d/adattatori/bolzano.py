"""Provincia autonoma di Bolzano – INSPIRE «Edifici» e «Parti di un edificio» (08/11/2026, lettori regionali, gruppo C).

Fonte: WFS 2.0 `p_bz-Inspire:BU.BuildingPart` (parti, `aboveGroundEnvelope`, campi `ID`, `BUILDING_ID`) e
`p_bz-Inspire:BU.Building` (edifici, `CURRENT_USE`), CC0 1.0, EPSG:25832, **geometrie 2D senza altezze** (aggiornamento
2026-07-08). Le parti sono i corpi; l'edificio è `BUILDING_ID`; l'uso viene dall'edificio (`unisci_parti`).

Altezze da **DSM − DTM** 0,5 m della Provincia (CC0, WCS chiesto a 1 m, `fonti/bolzano.toml` → `[fonti.lidar]`,
rilievo ~2013): `altezze_dsm.annota` scrive i campi `dsm_*`. Le parti costruite dopo il rilievo (il nuovo corpo
dell'ospedale, 3.336 m², edificio 1199541) risultano «non presenti nel rilievo»: altezza stimata dai vicini, dichiarata.
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo
from .. import altezze_dsm as AD

USI = {"residential": "residenziale", "commerceAndServices": "commerciale", "industrial": "capannone",
       "agriculture": "capannone", "ancillary": None, "publicServices": "uffici", "office": "uffici"}


def unisci_parti(edifici: dict, parti: dict) -> dict:
    """GeoJSON di `BU.Building` e di `BU.BuildingPart` → parti con `CURRENT_USE` dell'edificio; gli edifici senza
    parti entrano interi (BUILDING_ID = ID)."""
    uso = {f["properties"]["ID"]: f["properties"].get("CURRENT_USE") for f in edifici.get("features", [])}
    con = set()
    out = []
    for f in parti.get("features", []):
        p = dict(f.get("properties") or {})
        p["CURRENT_USE"] = uso.get(p.get("BUILDING_ID"))
        con.add(p.get("BUILDING_ID"))
        out.append({"type": "Feature", "geometry": f["geometry"], "properties": p})
    for f in edifici.get("features", []):
        p = f["properties"]
        if p["ID"] not in con:
            out.append({"type": "Feature", "geometry": f["geometry"],
                        "properties": {"ID": f"e{p['ID']}", "BUILDING_ID": p["ID"], "CURRENT_USE": p.get("CURRENT_USE"),
                                       "HORIZONTAL_GEOM_REF": p.get("HORIZONTAL_GEOM_REF")}})
    d = {"type": "FeatureCollection", "features": out}
    if parti.get("crs") or edifici.get("crs"):
        d["crs"] = parti.get("crs") or edifici.get("crs")
    return d


def _corpo_bolzano(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    if g.area < 2:
        return None
    uso_i = str(p.get("CURRENT_USE") or "")
    uso = USI.get(uso_i)
    r = AD.gronda_da_campi(p, uso, piccolo=g.area < 15, rilievo="DSM 0,5 m (~2013)")
    q = AD.quota_corpo(p, quota_dtm)
    if q is None:
        return None
    eid = str(p.get("BUILDING_ID") or p.get("ID"))
    return Corpo(id=f"bz{p.get('ID')}", edificio=f"bz{eid}", sagoma=g, quota_terreno=q, gronda=r["gronda"], tetto="piano",
                 fonte_sagoma=BOLZANO.fonte, licenza=BOLZANO.licenza, fonte_altezza=r["fonte"], qualita=r["qualita"],
                 uso=uso, extra={"regione": "Provincia autonoma di Bolzano", "uso_inspire": uso_i or None,
                                 "edificio_inspire": eid, **r["extra"]})


BOLZANO = Adattatore("bolzano_inspire", "Provincia autonoma di Bolzano – INSPIRE Edifici e Parti di un edificio", "CC0 1.0",
                     "Provincia autonoma di Bolzano – INSPIRE Edifici (CC0 1.0); altezze da DSM − DTM 0,5 m (CC0 1.0)",
                     "EPSG:25832", ("ID", "BUILDING_ID", "CURRENT_USE"), False, _corpo_bolzano)

ADATTATORI = (BOLZANO,)


# ------------------------------------------------------------------------------------------------ sagome di un comune


def confine(istat: str, client=None) -> dict:
    """Confine del comune dal WFS INSPIRE della Provincia (AU.AdministrativeUnit, NATIONAL_CODE senza lo zero)."""
    import httpx
    from .. import fonti as F
    f = F.carica_zona("bolzano")["fonti"]["edifici"]
    cl = client or httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "EuGEnio-edifici3d"})
    r = cl.get(f["confine_wfs"].format(istat=str(int(istat))))
    r.raise_for_status()
    return r.json()


def sagome_comune(istat: str, uscita, cartella=None, client=None) -> dict:
    """Parti e edifici INSPIRE del comune (WFS a pagine sul riquadro del confine) → GeoJSON delle parti con l'uso,
    solo quelle con il punto interno dentro il confine; scrive accanto anche il confine."""
    import json
    from pathlib import Path
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from .. import fonti as F, regionali as R
    f = F.carica_zona("bolzano")["fonti"]["edifici"]
    uscita = Path(uscita)
    cartella = Path(cartella or uscita.parent)
    cartella.mkdir(parents=True, exist_ok=True)
    c = confine(istat, client)
    (cartella / f"confine_{istat}.json").write_text(json.dumps(c), encoding="utf-8")
    g = unary_union([shape(x["geometry"]) for x in c["features"]])
    rq = g.bounds
    R.scarica_campione(dict(f), rq, cartella / "parti.json", max_oggetti=200000, pagina=5000, client=client, pausa=0.5)
    R.scarica_campione(dict(f, strato=f["strato_edifici"]), rq, cartella / "edifici.json", max_oggetti=200000, pagina=5000,
                       client=client, pausa=0.5)
    d = unisci_parti(json.loads((cartella / "edifici.json").read_text(encoding="utf-8")),
                     json.loads((cartella / "parti.json").read_text(encoding="utf-8")))
    n0 = len(d["features"])
    d["features"] = [x for x in d["features"] if g.contains(shape(x["geometry"]).representative_point())]
    d["crs"] = {"type": "name", "properties": {"name": f.get("crs_servizio", "EPSG:25832")}}
    uscita.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return {"parti_nel_riquadro": n0, "parti_nel_comune": len(d["features"]), "file": str(uscita),
            "confine": str(cartella / f"confine_{istat}.json")}


def main(argv=None) -> int:
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(prog="python -m edifici3d.adattatori.bolzano")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sagome", help="parti INSPIRE di un comune (WFS) → GeoJSON per altezze_dsm annota")
    s.add_argument("--istat", required=True, help="codice ISTAT (es. 021008)"); s.add_argument("--uscita", type=Path, required=True)
    a = ap.parse_args(argv)
    print(json.dumps(sagome_comune(a.istat, a.uscita), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
