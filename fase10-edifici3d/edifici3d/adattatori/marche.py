"""Marche – DBGT 2019 (CTR 1:10.000), classe `edificio` + `punto_quotato` (gruppo B dei lettori regionali, 08/11/2026).

Fonte: Regione Marche, `edificio.zip` e `punto_quotato.zip` di tutta la regione (Shapefile, RDN2008 / UTM 33N,
EPSG:7792), CC BY 4.0 (pagina «Elenco Opendata», D.G.R. 783/2017). Verificati l'08/11/2026: `edifc_qm` = quota di
gronda (uguale al punto «in gronda o su copertura» nel 98,5 % degli edifici di Ancona), un punto «su manufatto /
edificio – al piede» per edificio. La z dei poligoni è 0.

Il collegamento tra punti ed edifici lo fa `python -m edifici3d.b_regioni marche-dbgt` (punto al piede dentro la sagoma
o entro 1 m, il più basso; punto in gronda dentro la sagoma, il più alto) e scrive `quota_piede` e `quota_gronda_punto`
accanto ai campi del DBGT (`gid`, `classref`, `edifc_qm`, `stat_name`, `ty_name`, `por_name`, `uso_name`, `origine`).

Gli edifici con più usi hanno più righe con lo stesso `gid` nel DBGT: `marche-dbgt` le unisce (usi in `usi`).

Altezza = `edifc_qm` − quota al piede (senza punto al piede: − DTM). Si scartano ruderi, sotterranei e aggetti. Un solo
valore di gronda per edificio alla scala 1:10.000: le architetture complesse (cupole, torri) vengono appiattite.
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo, numero

_USI = (("resid", "residenziale"), ("istruz", "scuola"), ("scuol", "scuola"), ("sanit", "ospedale"), ("ospedal", "ospedale"),
        ("industr", "capannone"), ("commerc", "commerciale"), ("sport", "palestra"), ("amministr", "uffici"))


def _uso(t: str, tipo: str) -> str | None:
    t = t.lower()
    if "capannone" in tipo.lower():
        return "capannone"
    for k, u in _USI:
        if k in t:
            return u
    return None


def _corpo_marche(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    stato = str(p.get("stat_name") or "").lower()
    if "diruto" in stato or "rudere" in stato or "demol" in stato:
        return None
    por = str(p.get("por_name") or "").lower()
    if "sotterran" in por or "aggetto" in por:
        return None
    qm = numero(p.get("edifc_qm"))
    if qm is None or qm <= 0:
        qm = numero(p.get("quota_gronda_punto"))
    pi = numero(p.get("quota_piede"))
    base = pi if pi is not None else quota_dtm
    if qm is None or base is None or g.area < 2:
        return None
    h = qm - base
    if h < 1.5 or h > 250:
        return None
    fonte_h = f"DBGT Marche: edifc_qm {qm:.1f} m − " + (f"punto al piede {pi:.1f} m" if pi is not None else f"DTM {quota_dtm:.1f} m")
    uso_testo = str(p.get("uso_name") or "")
    tipo = str(p.get("ty_name") or "")
    gid = p.get("gid")
    gid = str(int(gid)) if isinstance(gid, float) else str(gid)
    return Corpo(id=gid, edificio=gid, sagoma=g, quota_terreno=quota_dtm if quota_dtm is not None else pi,
                 gronda=round(float(h), 2), tetto="piano", fonte_sagoma=MARCHE.fonte, licenza=MARCHE.licenza,
                 fonte_altezza=fonte_h, qualita="DBGT 1:10.000 (2019-2020), una gronda per edificio, altezza ±1–3 m",
                 uso=_uso(uso_testo, tipo),
                 extra={"tipo": tipo, "uso_dbgt": p.get("usi") or uso_testo, "porzione": p.get("por_name"), "stato": p.get("stat_name"),
                        "origine": p.get("origine"), "quota_gronda": qm, "quota_piede": pi, "regione": "Marche"})


MARCHE = Adattatore("marche_dbgt", "Regione Marche – DBGT 2019, edificio e punti quotati", "CC BY 4.0",
                    "Regione Marche – DBGT 2019 (CTR 1:10.000), edificio e punto quotato (CC BY 4.0)", "EPSG:7792",
                    ("gid", "edifc_qm", "quota_piede", "stat_name", "por_name", "uso_name"), False, _corpo_marche)


def coerenza(righe) -> str:
    n = len(righe)
    ok = sum(1 for p, _ in righe if numero(p.get("edifc_qm")) is not None and numero(p.get("quota_gronda_punto")) is not None
             and abs(numero(p.get("edifc_qm")) - numero(p.get("quota_gronda_punto"))) < 0.05)
    piede = sum(1 for p, _ in righe if numero(p.get("quota_piede")) is not None)
    return f"edifc_qm = punto in gronda in {ok} su {n}; punto al piede in {piede} su {n}"


MARCHE.coerenza = coerenza          # usata da regionali.controlla (proposta comune dei gruppi A e B)

ADATTATORI = (MARCHE,)
