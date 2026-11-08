"""Regione Sardegna – DBGT 10k 2022 v05, Edificio, con altezze dal LiDAR 2008 (08/11/2026, lettori regionali, gruppo C).

Sagome: WFS `dbu:dbgt_10k_22_v05_02_edificio_ingombro_suolo` (CC BY 4.0, EPSG:7791, 499.171 edifici in regione),
campi `classid`, `stato` («costruito», «in costruzione», …), `tipologia` («generica», «chiesa», …), `uso` (testo:
«residenziale», «sede di ospedale», «sede di scuola», «commerciale», …), `nome`, `monumental`; **z = 0**: nessuna
altezza. Altezze da **DSM − DTM** del LiDAR 2008 a 1 m della fascia costiera (CC BY 4.0, tessere 1:2.000 con URL diretti
nel quadro d'unione WFS `dbu:QU2k_fasciacostiera2008_DTM_DSM1m`; si usa il «DSM buildings», senza vegetazione):
`altezze_dsm.annota`. Il rilievo è del 2008: gli edifici costruiti dopo risultano «non presenti nel rilievo» e prendono
la mediana dei vicini (dichiarata).
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo
from .. import altezze_dsm as AD

SCARTA_STATO = ("diruto", "demolit", "rudere", "distrutt")
USI = (("ospedal", "ospedale"), ("sanitari", "ospedale"), ("scuol", "scuola"), ("universit", "scuola"),
       ("residenz", "residenziale"), ("abitativ", "residenziale"), ("commerc", "commerciale"), ("albergh", "commerciale"),
       ("industr", "capannone"), ("artigian", "capannone"), ("agricol", "capannone"), ("uffic", "uffici"),
       ("amministr", "uffici"), ("caserm", "uffici"), ("sportiv", "palestra"))


def uso_da_testo(t: str) -> str | None:
    t = (t or "").lower()
    return next((u for k, u in USI if k in t), None)


def _corpo_sardegna(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    stato = str(p.get("stato") or "").lower()
    if any(s in stato for s in SCARTA_STATO) or g.area < 2:
        return None
    uso_t = str(p.get("uso") or "")
    uso = uso_da_testo(uso_t)
    tip = str(p.get("tipologia") or "")
    piccolo = g.area < 15 or any(k in tip.lower() for k in ("baracc", "tettoi", "serra", "cabina"))
    r = AD.gronda_da_campi(p, uso, piccolo=piccolo, rilievo="LiDAR 2008")
    q = AD.quota_corpo(p, quota_dtm)
    if q is None:
        return None
    cid = str(p.get("classid") or p.get("id"))
    extra = {"regione": "Sardegna", "destinazione": uso_t or None, "tipo_edificio": tip or None, "stato": stato or None,
             **r["extra"]}
    if p.get("nome"):
        extra["nome"] = str(p["nome"])
    return Corpo(id=f"sar_{cid}", edificio=f"sar_{cid}", sagoma=g, quota_terreno=q, gronda=r["gronda"], tetto="piano",
                 fonte_sagoma=SARDEGNA.fonte, licenza=SARDEGNA.licenza, fonte_altezza=r["fonte"], qualita=r["qualita"],
                 uso=uso, extra={k: v for k, v in extra.items() if v is not None})


SARDEGNA = Adattatore("sardegna_dbgt_lidar", "Regione Sardegna – DBGT 10k 2022, Edificio", "CC BY 4.0",
                      "Regione Autonoma della Sardegna – DBGT 10k 2022 e LiDAR 2008 fascia costiera (CC BY 4.0)",
                      "EPSG:7791", ("classid", "stato", "tipologia", "uso"), False, _corpo_sardegna)

ADATTATORI = (SARDEGNA,)
