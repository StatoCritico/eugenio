"""Puglia – Carta Tecnica Regionale 1:5.000 (volo 2006), gruppo B dei lettori regionali (08/11/2026).

Fonte: Regione Puglia, SIT, CTR in Shapefile per elemento (`<elemento>_ctr.zip`: `CTR_<el>_pol`, `_poi`, `_lin`),
WGS84 / UTM 33N (EPSG:32633, nessun `.prj`), licenza IODL 2.0 (scheda RNDT `r_puglia:e5fdf473-…`).

I poligoni degli edifici non hanno altezze: le quote sono **punti** («quota gronda edificio», «quota piede
fabbricato»), e nel centro i poligoni sono **isolati interi** divisi in corpi da linee «dividente edificio civile».
Il lavoro su più strati lo fa `python -m edifici3d.b_regioni puglia-ctr` (divisione con le dividenti, cavedi tolti,
gronde dentro il corpo – o dell'isolato se il corpo non ne ha –, piedi entro 3 m – o dell'edificio, o la z del contorno
del poligono, che nella CTR sta al suolo); qui si legge il GeoJSON che ne esce (campi `id`, `edificio`, `quota_gronda`,
`quota_piede`, `fonte_gronda`, `fonte_piede`, `tipo`, `descr`, `elemento`, `quota_colmo`).

Altezza = quota di gronda − quota al piede; quota del terreno = DTM 8 m (IODL 2.0) se c'è, altrimenti la quota al piede.
"""
from __future__ import annotations

from ..regionali import Adattatore, Corpo, numero

_USI = {"capannone": "capannone", "silos": "capannone", "serbatoio": "capannone"}


def _corpo_puglia(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    gr, pi = numero(p.get("quota_gronda")), numero(p.get("quota_piede"))
    if gr is None or g.area < 2:
        return None
    base = pi if pi is not None else quota_dtm
    if base is None:
        return None
    h = gr - base
    if h < 1.5 or h > 250:
        return None
    fonte_g = str(p.get("fonte_gronda") or "punti di gronda")
    fonte_h = f"CTR Puglia: quota di gronda {gr:.1f} m ({fonte_g}) − quota al piede {base:.1f} m"
    fonte_h += f" ({p.get('fonte_piede')})" if pi is not None else " (DTM 8 m)"
    qualita = "CTR 1:5.000 (volo 2006), altezza ±1–2 m"
    if "isolato" in fonte_g:
        qualita += "; gronda media dell'isolato (il corpo non ha un punto suo)"
    tipo = str(p.get("tipo") or "")
    extra = {"tipo": tipo, "descrizione_ctr": p.get("descr"), "elemento": p.get("elemento"), "quota_gronda": gr,
             "quota_piede": pi, "punti_gronda": p.get("n_gronde"), "regione": "Puglia"}
    co = numero(p.get("quota_colmo"))
    if co is not None and co > gr:
        extra["quota_colmo"] = co
    return Corpo(id=str(p.get("id")), edificio=str(p.get("edificio") or p.get("id")), sagoma=g,
                 quota_terreno=quota_dtm if quota_dtm is not None else pi, gronda=round(float(h), 2), tetto="piano",
                 fonte_sagoma=PUGLIA.fonte, licenza=PUGLIA.licenza, fonte_altezza=fonte_h, qualita=qualita,
                 uso=_USI.get(tipo), extra={k: v for k, v in extra.items() if v is not None})


PUGLIA = Adattatore("puglia_ctr", "Regione Puglia – Carta Tecnica Regionale 1:5.000 (2006)", "IODL 2.0",
                    "Regione Puglia – Carta Tecnica Regionale 1:5.000, volo 2006 (IODL 2.0)", "EPSG:32633",
                    ("id", "edificio", "quota_gronda", "quota_piede", "tipo"), False, _corpo_puglia)


def coerenza(righe) -> str:
    n = len(righe)
    ok = sum(1 for p, _ in righe if numero(p.get("quota_gronda")) is not None and numero(p.get("quota_piede")) is not None
             and numero(p.get("quota_gronda")) - numero(p.get("quota_piede")) > 1.5)
    propri = sum(1 for p, _ in righe if str(p.get("fonte_gronda") or "").endswith("del corpo"))
    return f"gronda − piede > 1,5 m in {ok} su {n}; gronda dai punti del corpo in {propri} (gli altri dall'isolato)"


PUGLIA.coerenza = coerenza          # usata da regionali.controlla (proposta comune dei gruppi A e B)

ADATTATORI = (PUGLIA,)
