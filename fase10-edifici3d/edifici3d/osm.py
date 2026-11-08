"""Edifici OpenStreetMap (archivio ODbL, separato dal CC BY).

In ER servono solo per le costruzioni recenti che il DBTR non ha ancora: si tengono gli edifici OSM che non si
sovrappongono (oltre il 30 % della loro area) a una UVL. Altezza: `height` → `building:levels` × 3 m → nessuna
(il corpo resta senza altezza e la pagina chiede un valore, segnalato come stima).
Il prodotto (PMTiles e celle) è un database derivato ODbL: va solo nell'archivio `odbl/`, con l'attribuzione
«© OpenStreetMap contributors (ODbL 1.0)».
"""
from __future__ import annotations

import re

from shapely.strtree import STRtree

from .modello import Corpo, numero, uso_da

LICENZA = "ODbL 1.0"
FONTE = "OpenStreetMap"
ATTRIBUZIONE = "© OpenStreetMap contributors (ODbL 1.0)"
SOGLIA_SOVRAPPOSIZIONE = 0.3


def altezza(tag: dict) -> tuple[float | None, str]:
    h = tag.get("height")
    if h:
        m = re.match(r"\s*([0-9]+(?:[.,][0-9]+)?)", str(h))
        if m:
            return float(m.group(1).replace(",", ".")), "OSM height"
    lv = numero(tag.get("building:levels"))
    if lv:
        return lv * 3.0, "OSM building:levels × 3 m"
    return None, "nessuna"


def corpi_da_osm(elementi: list[tuple[dict, object]], uvl: list[Corpo] = ()) -> list[Corpo]:
    """elementi: (tag, poligono in metri). Scarta quelli già coperti dalle UVL."""
    albero = STRtree([c.sagoma for c in uvl]) if uvl else None
    out = []
    for n, (tag, g) in enumerate(elementi):
        if g is None or g.is_empty or g.area < 10:
            continue
        if albero is not None:
            sopra = sum(uvl[i].sagoma.intersection(g).area for i in albero.query(g))
            if sopra > SOGLIA_SOVRAPPOSIZIONE * g.area:
                continue
        h, fonte_h = altezza(tag)
        uso = uso_da(osm_building=tag.get("building"))
        oid = str(tag.get("osm_id") or tag.get("@id") or f"osm{n}")
        edificio = str(tag.get("osm_edificio") or oid)        # i pezzi di un multipoligono restano un edificio solo
        out.append(Corpo(id=oid, edificio=edificio, sagoma=g, quota_terreno=None, gronda=h or 0.0,
                         piani=int(numero(tag.get("building:levels"))) if numero(tag.get("building:levels")) else None,
                         fonte_sagoma=FONTE, licenza=LICENZA, fonte_altezza=fonte_h, uso=uso,
                         qualita="altezza mancante: da indicare" if h is None else "altezza da OSM"))
    return out
