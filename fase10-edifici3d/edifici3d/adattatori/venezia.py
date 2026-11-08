"""Venezia – DBGT del Comune di Venezia, classe 020101 «Unità volumetrica» (`UN_VOL`), 08/11/2026.

Fonte: «Carta Tecnica» su dati.venezia.it (Geodatabase del DBGT comunale, aggiornato al 10/09/2026), scaricata da Paolo
l'08/11/2026 dal browser (il portale è protetto da un controllo anti-robot: dal container non si raggiunge). Licenza
**IODL 2.0**, scritta in `Informazioni_e_licenza.pdf` dello scarico: «Il Geodatabase geografico e tutti i relativi file
… sono distribuiti con licenza IODL 2.0». URL e scheda in `fonti/venezia.toml`.

Verifiche sul file (08/11/2026, `Strato02_Immobili_Antropizzazioni/Tema0201_Edificato/UN_VOL.*`):
- Shapefile **Polygon 2D senza `.prj`**: sistema EPSG:3004 (Monte Mario / Gauss-Boaga fuso Est, dichiarato nel PDF);
  coordinate 2.298.667–2.331.670 E, 5.012.455–5.050.048 N; 178.391 volumi;
- campi `UN_VOL_AV, UN_VOL_POR, UN_VOL_QE, UN_VOL_EX, UN_VOL_QB, UN_VOL_QG, TIPO_MOD, ORIGINE, SCRIL, CODICE,
  UN_VOL_SUP, UN_VOL_VOL`; **nessun identificativo** del volume né dell'edificio;
- `UN_VOL_QG − UN_VOL_QB = UN_VOL_AV` in 178.291 volumi su 178.391: `UN_VOL_AV` è l'**altezza di gronda** sopra la
  quota della base `UN_VOL_QB`; `UN_VOL_QE` (quota di estrusione) è più alta della gronda nei tetti a falde: colmo =
  `UN_VOL_QE − UN_VOL_QB` (tenuto se supera la gronda di almeno 0,3 m e di non più di 25 m: tetto a capanna stimato, come il colmo del DBTR ER;
  campanile di San Marco: gronda 73,7 m, colmo 93,5 m, alto 98,6 m);
- `UN_VOL_AV` mediana 5,0 m, massimo 77,95 m (> 0 in 175.741; sotto 0,5 m scartati); `UN_VOL_QB` mediana 2,14 m (centro storico e isole a
  1–3 m s.l.m.: la quota del terreno è `UN_VOL_QB`);
- `UN_VOL_POR`: 01 (172.850), 04 (4.381), 03 (898), 91/95/02/08/09 (231, quasi tutti con altezza 0: scartati
  dall'altezza), 08 sotterraneo (scartato come negli altri DBGT).

Lo strato `EDIFC` (40.733 edifici, anch'esso senza identificativo) dà l'edificio di appartenenza e la destinazione
(`EDIFC_USO`, codici del catalogo nazionale): il passo `unisci` qui sotto assegna a ogni volume l'edificio che contiene
il suo punto interno (numero progressivo dell'edificio nel file) e un identificativo progressivo del volume, e scrive un
GeoJSON con il sistema dichiarato, pronto per `prepara-regione`:

  python -m edifici3d.adattatori.venezia unisci --un-vol UN_VOL.shp --edifc EDIFC.shp --uscita venezia_uv.geojson
  python -m edifici3d --zona venezia prepara-regione --file venezia_uv.geojson --archivio … --comune venezia \\
      --istat 027042 --nome "Venezia – DBGT del Comune (unità volumetriche)"

Anche `prepara-regione --file UN_VOL.shp --crs-file EPSG:3004` funziona (senza edifici: ogni volume è un edificio,
identificativo dal centroide).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .. import regionali as _R  # noqa: F401  (prima: registra gli adattatori, niente import circolari con -m)
from .a_dbgt import Nomi, adattatore, corpo_dbgt, minuscole, primo
from ..regionali import numero

MIN_FALDA = 0.3        # m: colmo almeno così sopra la gronda (come le UVL dell'ER)
MAX_FALDA = 25.0       # m: oltre, quota di estrusione non credibile come colmo (resta la sola gronda)
MIN_ALTEZZA = 0.5      # m: volumi più bassi (muretti, gradini, 0,01 m) scartati


def _corpo_venezia(p: dict, g, z, quota_dtm, *, ad):
    c = corpo_dbgt(p, g, None, quota_dtm, ad=ad)      # z: il file è 2D; base = UN_VOL_QB
    if c is None or c.gronda < MIN_ALTEZZA:
        return None
    pm = minuscole(p)
    qe, qb = numero(primo(pm, ("UN_VOL_QE",))), numero(primo(pm, ("UN_VOL_QB",)))
    if qe is not None and qb is not None:
        colmo = qe - qb
        if c.gronda + MIN_FALDA <= colmo <= c.gronda + MAX_FALDA:
            c.colmo = round(colmo, 2)                  # come il colmo del DBTR ER: tetto a falde stimato
            c.tetto, c.falde = "capanna", 2
            c.extra["colmo_db"] = c.colmo
        c.extra["quota_estrusione"] = qe
    uso = primo(pm, ("EDIFC_USO",))
    if uso is not None:
        from .campania import DBT_DESTINAZIONI, _uso_dbt   # dominio nazionale H_EDIFC_CATEGORIA_USO (030102 ospedale …)
        cu = str(uso).strip()
        c.extra["codice_uso"] = cu
        c.uso = _uso_dbt(cu)
        dest = DBT_DESTINAZIONI.get(cu) or DBT_DESTINAZIONI.get(cu[:4]) or DBT_DESTINAZIONI.get(cu[:2])
        if dest:
            c.extra["destinazione"] = dest
    return c


VENEZIA = adattatore(
    "venezia_dbgt", fonte="DBGT Comune di Venezia – Unità volumetrica (020101)", licenza="IODL 2.0",
    attribuzione="Comune di Venezia – DBGT, Unità volumetriche (IODL 2.0)", crs_file="EPSG:3004",
    campi_attesi=("UN_VOL_AV", "UN_VOL_POR", "UN_VOL_QB", "UN_VOL_QG", "UN_VOL_QE"),
    nomi=Nomi(id=("ID_UV",), edificio=("CEDIUV",), altezza=("UN_VOL_AV",), estrusione=(), base=("UN_VOL_QB",),
              porzione=("UN_VOL_POR",), altri=("UN_VOL_QG",)),
    regione="Veneto", nome_breve="DBGT Comune di Venezia", etichetta_altezza="UN_VOL_AV (= UN_VOL_QG − UN_VOL_QB)",
    qualita="DBGT comunale (aggiornato al 10/09/2026), altezza di gronda ±1 m")
VENEZIA.corpo = lambda p, g, z, q, _ad=VENEZIA: _corpo_venezia(p, g, z, q, ad=_ad)



def _coerenza(righe) -> str:
    n = ok = con_h = 0
    for p, _ in righe:
        pm = minuscole(p)
        h, qb, qg = (numero(primo(pm, (k,))) for k in ("UN_VOL_AV", "UN_VOL_QB", "UN_VOL_QG"))
        con_h += h is not None and h > 0
        if None in (h, qb, qg):
            continue
        n += 1
        ok += abs(qg - qb - h) < 0.05
    return (f"altezza > 0 in {con_h} su {len(righe)}; UN_VOL_QG − UN_VOL_QB = UN_VOL_AV in {ok} su {n} "
            "(quota del terreno = UN_VOL_QB)")


VENEZIA.coerenza = _coerenza
ADATTATORI = (VENEZIA,)


def unisci(un_vol: Path, edifc: Path | None, uscita: Path, crs: str = "EPSG:3004") -> dict:
    """UN_VOL (+ EDIFC) → GeoJSON con `ID_UV`, `CEDIUV`, `EDIFC_USO`, `EDIFC_SOT` e il sistema dichiarato."""
    import numpy as np
    import pyogrio.raw as PR
    from shapely import from_wkb
    from shapely.geometry import mapping
    from shapely.strtree import STRtree

    meta, _, geom, cols = PR.read(un_vol)
    campi = list(meta["fields"])
    vol = [from_wkb(b) if b is not None else None for b in geom]
    cediuv = [None] * len(vol)
    usi = [None] * len(vol)
    sot = [None] * len(vol)
    n_edi = 0
    if edifc:
        me, _, ge, ce = PR.read(edifc)
        fe = dict(zip(me["fields"], ce))
        edi = [from_wkb(b) if b is not None else None for b in ge]
        idx = [i for i, e in enumerate(edi) if e is not None and not e.is_empty]
        albero = STRtree([edi[i] for i in idx])
        n_edi = len(idx)
        for k, v in enumerate(vol):
            if v is None or v.is_empty:
                continue
            pt = v.representative_point()
            for j in albero.query(pt, predicate="within"):
                i = idx[int(j)]
                cediuv[k] = f"E{i + 1}"
                usi[k] = fe.get("EDIFC_USO", [None] * len(edi))[i]
                sot[k] = fe.get("EDIFC_SOT", [None] * len(edi))[i]
                break

    def val(x):
        if isinstance(x, (np.floating, float)):
            return None if math.isnan(float(x)) else float(x)
        if isinstance(x, np.integer):
            return int(x)
        return x

    feats = []
    for k, v in enumerate(vol):
        if v is None or v.is_empty:
            continue
        pr = {c: val(cols[i][k]) for i, c in enumerate(campi)}
        pr.update({"ID_UV": f"V{k + 1}", "CEDIUV": cediuv[k] or f"V{k + 1}", "EDIFC_USO": usi[k], "EDIFC_SOT": sot[k]})
        feats.append({"type": "Feature", "properties": pr, "geometry": mapping(v)})
    uscita = Path(uscita)
    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_text(json.dumps({"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": crs}},
                                  "features": feats}, ensure_ascii=False), encoding="utf-8")
    return {"volumi": len(feats), "edifici": n_edi, "volumi_con_edificio": sum(1 for c in cediuv if c), "uscita": str(uscita)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edifici3d.adattatori.venezia", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("unisci", help="UN_VOL + EDIFC → GeoJSON per prepara-regione (EPSG:3004)")
    u.add_argument("--un-vol", type=Path, required=True)
    u.add_argument("--edifc", type=Path)
    u.add_argument("--uscita", type=Path, required=True)
    u.add_argument("--crs", default="EPSG:3004")
    a = ap.parse_args(argv)
    print(json.dumps(unisci(a.un_vol, a.edifc, a.uscita, a.crs), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
