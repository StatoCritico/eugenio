"""Provincia autonoma di Trento – Edifici P.A.T. 3D (08/11/2026, lettori regionali, gruppo C).

Fonte: «Edifici P.A.T. 3D» (`ctp14_edificato_04072014`, CTP 2014, altezze dal LiDAR 2006-2009), CC BY 4.0, zip unico
di 107.676.038 byte (URL in `fonti/trento.toml`), Shapefile PolygonZ in ETRF89 / UTM 32N (≈ EPSG:25832), 147.481
edifici. Campi usati: `OBJECTID_1` (identificativo), `MED_ALT` (altezza media, m: usata come gronda), `MIN_ALT`,
`MAS_ALT` (minima e massima, in `extra`), `quota_DTM` (quota del terreno, m s.l.m.), `TIPO` («Civile», «Baracca»,
«Industriale», «Luoghi di culto», «Tettoia», «Serra», «Centrale-Cabina», «Cavedio»…), `NOTE` (nome di scuole e sedi).

Il 21 % degli edifici ha `MED_ALT` = 0 (55 % nel centro storico): per quelli l'altezza viene da **DSM − DTM** del
LiDAR PAT 2014/2018 a 0,5 m (`altezze_dsm.annota --solo-senza --campo-altezza MED_ALT`, campi `dsm_*`), altrimenti
dalla mediana dei vicini o dall'uso (3 m per baracche, tettoie, serre e cabine). Prova dell'08/11/2026 su 8 tessere
(S. Chiara e centro): DSM First − DTM contro `MED_ALT` mediana +0,22 m, 97 % entro 2 m (558 edifici) a S. Chiara;
+0,20 m, 87 % nel centro (268).
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo, numero
from .. import altezze_dsm as AD

PICCOLI = ("baracca", "tettoia", "serra", "centrale", "cabina", "tendone", "portico")
SCARTA = ("cavedio",)


def _uso(tipo: str, note: str) -> str | None:
    t, n = tipo.lower(), note.lower()
    if any(k in n for k in ("scuola", "nido", "liceo", "istituto", "universit", "ingegneria", "sociologia")):
        return "scuola"
    if "ospedal" in n:
        return "ospedale"
    if "industr" in t:
        return "capannone"
    if t == "civile":
        return "residenziale"
    return None


def _corpo_trento(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    tipo = str(p.get("TIPO") or "").strip()
    if any(s in tipo.lower() for s in SCARTA) or g.area < 2:
        return None
    note = str(p.get("NOTE") or "").strip()
    uso = _uso(tipo, note)
    med, mn, mx = numero(p.get("MED_ALT")), numero(p.get("MIN_ALT")), numero(p.get("MAS_ALT"))
    q_db = numero(p.get("quota_DTM"))
    q = AD.quota_corpo(p, quota_dtm, q_db if q_db and q_db > 0 else None)
    extra = {"regione": "Provincia autonoma di Trento", "tipo_edificio": tipo or None, "min_alt": mn, "mas_alt": mx,
             "quota_dtm_pat": q_db, "tavola_lidar": p.get("TAVOLA")}
    if note:
        extra["nome"] = note
    if med is not None and med > 0:
        h, fonte, qual = float(med), "Edifici P.A.T. 3D MED_ALT (altezza media dal LiDAR PAT 2006-2009)", \
            "Edifici P.A.T. 3D, altezza media ±1 m (LiDAR 2006-09)"
    else:
        r = AD.gronda_da_campi(p, uso, piccolo=any(k in tipo.lower() for k in PICCOLI), rilievo="LiDAR PAT 2014/2018")
        h, fonte, qual = r["gronda"], "MED_ALT = 0 nel DB; " + r["fonte"], r["qualita"]
        extra.update(r["extra"])
    if q is None:
        return None
    oid = str(p.get("OBJECTID_1") or p.get("OBJECTID"))
    return Corpo(id=f"tn{oid}", edificio=f"tn{oid}", sagoma=g, quota_terreno=q, gronda=round(h, 2), tetto="piano",
                 fonte_sagoma=TRENTO.fonte, licenza=TRENTO.licenza, fonte_altezza=fonte, qualita=qual, uso=uso,
                 extra={k: v for k, v in extra.items() if v is not None})


TRENTO = Adattatore("trento_pat3d", "Provincia autonoma di Trento – Edifici P.A.T. 3D", "CC BY 4.0",
                    "Provincia autonoma di Trento – Edifici P.A.T. 3D e LiDAR PAT 2014/2018 (CC BY 4.0)", "EPSG:25832",
                    ("OBJECTID_1", "MIN_ALT", "MED_ALT", "MAS_ALT", "quota_DTM", "TIPO"), False, _corpo_trento)

ADATTATORI = (TRENTO,)
