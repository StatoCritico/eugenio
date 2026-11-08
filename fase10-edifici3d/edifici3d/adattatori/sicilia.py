"""Sicilia (gruppo B dei lettori regionali, 08/11/2026): due fonti.

1. **Comune di Palermo – Carta tecnica comunale, unità volumetriche** (dataset 1294 di opendata.comune.palermo.it,
   CC BY 4.0, Shapefile PolygonZ in RDN2008 / UTM 33N, EPSG:7792): `ID`, `ID_UN_VOL`, `QUOTA_GRON` (quota di gronda),
   `QUOTA_PIED` (quota al piede), `ALTEZZA` (= gronda − piede in 100.432 su 100.432), `AREA`, `VOLUME`. Nessun edificio
   padre: ogni volume è un corpo e un edificio. Nel file 247 righe ripetono la stessa sagoma con altezze diverse:
   `python -m edifici3d.b_regioni palermo-uv` tiene la più alta. Nei DBF i nomi troncati (`QUOTA_GRON`, `QUOTA_PIED`)
   diventano `QUOTA_GRONDA`, `QUOTA_PIEDE` (`regionali.nomi_completi`): si leggono tutti e due.
2. **Regione Siciliana – CTR 1:10.000 ed. ATA 2012-13, strato «Edificato»** (SITR, ArcGIS REST
   `ctr_10000/ctr_2013_dbtrs/MapServer/35`, CC BY 4.0 per i dati senza costi di cessione): nessun campo di altezza, la z
   dei vertici è la **quota di gronda** (contro `QUOTA_GRON` del Comune: mediana +0,09 m al Civico); altezza = z − DTM,
   quindi **serve il DTM** (come la Liguria). Campi `CODICE` (B001 edificio civile, B002 capannone, B003 chiesa, B006
   baracca, B021 torre/ciminiera/silos…), `DESCRIZION`, `ANNORILEV` (in gran parte 2003), `FLAGSTATO`. Il DTM 2 m del
   SITR (ImageServer `mdt_2013`) ha la licenza ancora da chiarire: per ora solo prove interne.
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo, numero


def _primo(p: dict, *nomi):
    for n in nomi:
        v = numero(p.get(n))
        if v is not None:
            return v
    return None


def _id(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _corpo_palermo(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    h = _primo(p, "ALTEZZA")
    gr = _primo(p, "QUOTA_GRON", "QUOTA_GRONDA")
    pi = _primo(p, "QUOTA_PIED", "QUOTA_PIEDE")
    if (h is None or h <= 0) and gr is not None and pi is not None:
        h = gr - pi
    if h is None or h <= 0.5 or g.area < 1:
        return None
    i = _id(p.get("ID_UN_VOL") if p.get("ID_UN_VOL") is not None else p.get("ID"))
    extra = {"quota_gronda": gr, "quota_piede": pi, "regione": "Sicilia"}
    if p.get("doppioni"):
        extra["sagome_ripetute"] = p.get("doppioni")
    fonte_h = "UV Comune di Palermo ALTEZZA (QUOTA_GRON − QUOTA_PIED)"
    if quota_dtm is not None and pi is not None:
        fonte_h += f"; piede {pi:.1f} m, DTM {quota_dtm:.1f} m"
    return Corpo(id=i, edificio=i, sagoma=g, quota_terreno=quota_dtm if quota_dtm is not None else pi, gronda=float(h),
                 tetto="piano", fonte_sagoma=PALERMO.fonte, licenza=PALERMO.licenza, fonte_altezza=fonte_h,
                 qualita="carta tecnica comunale 1:2.000 (2013), altezza ±1 m",
                 extra={k: v for k, v in extra.items() if v is not None})


_CTR_SCARTA = ("B006",)            # baracche: si tengono solo se alte almeno 2 m (vedi sotto)
_CTR_USI = {"B001": None, "B002": "capannone", "B003": None}


def _corpo_sicilia_ctr(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    if z is None or quota_dtm is None or g.area < 2:
        return None
    stato = str(p.get("FLAGSTATO") or "").strip().upper()
    if stato in ("D", "E"):                      # demolito / eliminato (codici del DB SITR)
        return None
    h = z - quota_dtm
    cod = str(p.get("CODICE") or "").strip()
    if h < (2.0 if cod in _CTR_SCARTA else 1.5) or h > 300:
        return None
    i = _id(p.get("OBJECTID") if p.get("OBJECTID") is not None else p.get("IDENT"))
    return Corpo(id=i, edificio=i, sagoma=g, quota_terreno=quota_dtm, gronda=round(float(h), 2), tetto="piano",
                 fonte_sagoma=SICILIA_CTR.fonte, licenza=SICILIA_CTR.licenza,
                 fonte_altezza=f"CTR Sicilia 2012-13: quota di gronda {z:.1f} m − DTM {quota_dtm:.1f} m",
                 qualita="CTR 1:10.000 (rilievo prevalente 2003), altezza ±2–3 m", uso=_CTR_USI.get(cod),
                 extra={"codice": cod, "descrizione": p.get("DESCRIZION"), "anno_rilievo": p.get("ANNORILEV"),
                        "foglio": p.get("FOGLIO"), "quota_gronda": round(z, 2), "regione": "Sicilia"})


PALERMO = Adattatore("palermo_uv", "Comune di Palermo – Carta tecnica comunale, unità volumetriche", "CC BY 4.0",
                     "Comune di Palermo – Carta tecnica comunale, unità volumetriche (CC BY 4.0)", "EPSG:7792",
                     ("ID", "ID_UN_VOL", "ALTEZZA"), False, _corpo_palermo)
SICILIA_CTR = Adattatore("sicilia_ctr", "Regione Siciliana – CTR 1:10.000 ATA 2012-13, Edificato", "CC BY 4.0",
                         "Regione Siciliana – SITR, CTR 1:10.000 ed. ATA 2012-2013 (CC BY 4.0)", "EPSG:4326",
                         ("OBJECTID", "CODICE", "DESCRIZION", "ANNORILEV"), True, _corpo_sicilia_ctr)


def coerenza_palermo_uv(righe) -> str:
    n = ok = 0
    for p, _ in righe:
        h, gr, pi = _primo(p, "ALTEZZA"), _primo(p, "QUOTA_GRON", "QUOTA_GRONDA"), _primo(p, "QUOTA_PIED", "QUOTA_PIEDE")
        if None in (h, gr, pi):
            continue
        n += 1
        ok += abs(gr - pi - h) < 0.05
    return f"QUOTA_GRON − QUOTA_PIED = ALTEZZA in {ok} su {n}"


PALERMO.coerenza = coerenza_palermo_uv          # usata da regionali.controlla (proposta comune dei gruppi A e B)

ADATTATORI = (PALERMO, SICILIA_CTR)
