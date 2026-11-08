"""Friuli Venezia Giulia – CTRN edizione 2 (gruppo B dei lettori regionali, 08/11/2026).

Gli strati `EDIFICI:EDIFICATO_CTRN_ED2_<foglio>` del WFS IRDAT hanno campi diversi dall'edizione 1 letta da `fvg_ctrn`
(`regionali.py`, da non toccare): `ID1` al posto di `ID`, niente `X`/`Y`, e in più `DATA_VOLO` (a Trieste 2003-05-23),
`TIPO` («CONFERMATO»/«MODIFICATO»…), `ELEMENTO_CTRN`, `CODICE_ORIGINARIO`. Verificati dal vivo l'08/11/2026 sul foglio
110 (Cattinara, 151 edifici): `QUOTA_GRONDA − QUOTA_PIEDE = ALTEZZA`. Con `fvg_ctrn` gli elementi dell'ED2 avrebbero
tutti id «None» (un edificio solo): da qui l'adattatore `fvg_ctrn_ed2`, con la stessa regola d'altezza; in più
si scartano tettoie e pensiline («TETTOIA, PENSILINA»: niente pareti) e gli elementi più bassi di 1 m.
"""
from __future__ import annotations

from ..regionali import FVG, Adattatore, Corpo, numero


def _id(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _corpo_fvg_ed2(p: dict, g, z: float | None, quota_dtm: float | None) -> Corpo | None:
    h = numero(p.get("ALTEZZA"))
    piede, gronda = numero(p.get("QUOTA_PIEDE")), numero(p.get("QUOTA_GRONDA"))
    if (h is None or h <= 0) and piede is not None and gronda is not None:
        h = gronda - piede
    if not h or h < 1.0 or g.area < 1:
        return None
    nome = str(p.get("NOME") or "").strip()
    if nome.upper().startswith("TETTOIA"):            # tettoie e pensiline: nessuna parete, non sono prismi
        return None
    i = _id(p.get("ID1")) or _id(p.get("ID"))
    if i is None:
        return None
    strato = str(p.get("strato") or "")
    if strato:
        i = f"{strato.rsplit('_', 1)[-1]}_{i}"          # gli ID1 ripartono a ogni foglio
    q = quota_dtm if quota_dtm is not None else piede
    uso = None
    if "CIVIL" in nome.upper():
        uso = "residenziale"
    elif any(k in nome.upper() for k in ("INDUSTR", "CAPANN", "STABILIM", "OPIFIC")):
        uso = "capannone"
    volo = str(p.get("DATA_VOLO") or "").rstrip("Z") or None
    extra = {"codice": p.get("CODICE"), "nome": nome, "quota_piede": piede, "quota_gronda": gronda, "tipo": p.get("TIPO"),
             "elemento": p.get("ELEMENTO_CTRN"), "volo": volo, "regione": "Friuli Venezia Giulia"}
    return Corpo(id=i, edificio=i, sagoma=g, quota_terreno=q, gronda=float(h), tetto="piano", fonte_sagoma=FVG_ED2.fonte,
                 licenza=FVG_ED2.licenza, fonte_altezza="CTRN FVG ed. 2 ALTEZZA (QUOTA_GRONDA − QUOTA_PIEDE)",
                 qualita="CTRN 1:5.000" + (f" (volo {volo})" if volo else "") + ", altezza ±1–2 m", uso=uso,
                 extra={k: v for k, v in extra.items() if v not in (None, "")})


FVG_ED2 = Adattatore("fvg_ctrn_ed2", "IRDAT FVG – Edificato CTRN, edizione 2", FVG.licenza, FVG.attribuzione, "EPSG:6708",
                     ("ID1", "ALTEZZA", "QUOTA_PIEDE", "QUOTA_GRONDA", "NOME", "DATA_VOLO"), False, _corpo_fvg_ed2)


def coerenza(righe) -> str:
    n = ok = 0
    for p, _ in righe:
        h, pi, gr = numero(p.get("ALTEZZA")), numero(p.get("QUOTA_PIEDE")), numero(p.get("QUOTA_GRONDA"))
        if None in (h, pi, gr):
            continue
        n += 1
        ok += abs(gr - pi - h) < 0.05
    return f"QUOTA_GRONDA − QUOTA_PIEDE = ALTEZZA in {ok} su {n}"


FVG_ED2.coerenza = coerenza          # usata da regionali.controlla (proposta comune dei gruppi A e B)

ADATTATORI = (FVG_ED2,)
