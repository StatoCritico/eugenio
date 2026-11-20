#!/usr/bin/env python3
"""Piccola mappa delle zone di mercato elettrico per la pagina «Carichi elettrici» (20/11/2026).

Unisce le regioni di sito/dati/mappa/italia.json (confini ISTAT generalizzati, stesso viewBox) nelle zone di mercato e
scrive sito/dati/mappa/zone.json = {"viewBox", "fonte", "zone": [{"id", "nome", "regioni", "d"}]}; la pagina
(carichi.js) lo usa per la piccola mappa accanto al titolo.

Zone in vigore dal 1° gennaio 2021 (ARERA 103/2019; Terna, «Individuazione zone della rete rilevante»; GME,
«Zone geografiche», documento del 18/10/2023), ancora le stesse nel 2026 (sono le zone dei dati «Fabbisogno Italia» di
Terna del 2026):
  Nord        Valle d'Aosta, Piemonte, Liguria, Lombardia, Trentino-Alto Adige, Veneto, Friuli-Venezia Giulia,
              Emilia-Romagna
  Centro-Nord Toscana, Marche
  Centro-Sud  Umbria, Lazio, Abruzzo, Campania
  Sud         Molise, Puglia, Basilicata
  Calabria, Sicilia, Sardegna

  python costruisci_zone.py        # richiede shapely
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

QUI = Path(__file__).resolve().parent
MAPPA = QUI / "sito" / "dati" / "mappa"

ZONE = [
    ("NORD", "Nord", ["01", "02", "03", "04", "05", "06", "07", "08"]),
    ("CNOR", "Centro-Nord", ["09", "11"]),
    ("CSUD", "Centro-Sud", ["10", "12", "13", "15"]),
    ("SUD", "Sud", ["14", "16", "17"]),
    ("CALA", "Calabria", ["18"]),
    ("SICI", "Sicilia", ["19"]),
    ("SARD", "Sardegna", ["20"]),
]
FONTE = ("Zone di mercato elettrico in vigore dal 1° gennaio 2021 (ARERA, delibera 103/2019/R/eel; GME, «Zone "
         "geografiche»); confini: ISTAT, unità amministrative a fini statistici (generalizzati, CC BY 4.0)")


def anelli(d: str) -> list[list[tuple[float, float]]]:
    out = []
    for parte in re.split(r"(?=M)", d):
        pts = [(float(x), float(y)) for x, y in re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", parte)]
        if len(pts) >= 3:
            out.append(pts)
    return out


def regione(d: str):
    """Poligono della regione con la regola pari-dispari (i buchi, come San Marino e il Vaticano, restano buchi)."""
    g = None
    for a in anelli(d):
        p = Polygon(a).buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    return g


def percorso(g) -> str:
    parti = []
    poligoni = g.geoms if isinstance(g, MultiPolygon) else [g]
    for p in poligoni:
        for anello in [p.exterior, *p.interiors]:
            c = list(anello.coords)[:-1]
            if len(c) < 3:
                continue
            parti.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in c) + "Z")
    return "".join(parti)


def main() -> None:
    it = json.loads((MAPPA / "italia.json").read_text(encoding="utf-8"))
    per_cod = {r["cod"]: r for r in it["regioni"]}
    zone = []
    for zid, nome, cods in ZONE:
        g = unary_union([regione(per_cod[c]["d"]) for c in cods])
        # chiude le fessure tra regioni confinanti (confini generalizzati separatamente) e semplifica un poco
        g = g.buffer(0.8, join_style=2).buffer(-0.8, join_style=2).simplify(0.3)
        g = MultiPolygon([p for p in (g.geoms if isinstance(g, MultiPolygon) else [g]) if p.area > 1.5])
        zone.append({"id": zid, "nome": nome, "regioni": cods, "d": percorso(g)})
    f = MAPPA / "zone.json"
    f.write_text(json.dumps({"viewBox": it["viewBox"], "fonte": FONTE, "zone": zone}, ensure_ascii=False,
                            separators=(",", ":")), encoding="utf-8")
    print(f"{f}: {f.stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
