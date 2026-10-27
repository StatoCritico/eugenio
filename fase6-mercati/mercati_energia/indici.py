"""Indici mensili derivati, quelli usati nelle formule di prezzo dei contratti.

  PUN_MENSILE             media aritmetica mensile del PUN Index GME (tutti gli intervalli)
  PUN_F1, PUN_F2, PUN_F3  medie mensili per fascia ARERA; PUN_F23 = fasce 2 e 3 insieme
  PZ_<ZONA>               media mensile del prezzo zonale MGP (es. PZ_NORD)
  PSV_MGPGAS_MENSILE      media mensile del prezzo dell'asta MGP-GAS
  PSV_MGPGAS_CONT_MENSILE media mensile dei prezzi medi ponderati della negoziazione continua MGP-GAS
  PSV_GME_MENSILE         la continua dove c'è, altrimenti l'asta: la serie PSV più lunga disponibile
  IGI_MENSILE             media mensile dell'IGI
  TTF_MENSILE             media mensile del TTF Neutral Gas Price
  PFOR, PFOR_GJ, PFOR_SMC indice PFOR,t ARERA ricostruito (€/MWh, €/GJ, €/Smc), uguale nei mesi del trimestre
  <nome importato>        indici importati da CSV (es. PSV_DA_ICIS, CMEM_ARERA)
Tutti in €/MWh, salvo gli indici importati (unità dichiarata nel file).
"""
from __future__ import annotations

import pandas as pd

from . import archivio
from .fasce import fascia


def _mese(d) -> pd.Series:
    return pd.to_datetime(d).dt.to_period("M").astype(str)


def calcola(cartella, festivi_extra: tuple = ()) -> pd.DataFrame:
    righe = []
    p = archivio.leggi(cartella, "mgp_prezzi")
    if not p.empty:
        loc = pd.to_datetime(p.inizio_utc, utc=True).dt.tz_convert("Europe/Rome")
        p = p.assign(mese=loc.dt.tz_localize(None).dt.to_period("M").astype(str))
        pun = p[p.zona.str.upper() == "PUN"].copy()
        if not pun.empty:
            # ogni intervallo pesa per la sua durata (quarti d'ora dopo il 1/10/2025, ore prima)
            pun["fascia"] = fascia(pun.inizio_utc, festivi_extra).to_numpy()
            pun["w"] = pun.minuti.astype(float)
            g = pun.groupby("mese").apply(lambda x: (x.prezzo * x.w).sum() / x.w.sum(), include_groups=False)
            righe += [("PUN_MENSILE", m, v, len(pun[pun.mese == m])) for m, v in g.items()]
            for f, nome in (("F1", "PUN_F1"), ("F2", "PUN_F2"), ("F3", "PUN_F3")):
                s = pun[pun.fascia == f]
                g = s.groupby("mese").apply(lambda x: (x.prezzo * x.w).sum() / x.w.sum(), include_groups=False)
                righe += [(nome, m, v, len(s[s.mese == m])) for m, v in g.items()]
            s = pun[pun.fascia != "F1"]
            g = s.groupby("mese").apply(lambda x: (x.prezzo * x.w).sum() / x.w.sum(), include_groups=False)
            righe += [("PUN_F23", m, v, len(s[s.mese == m])) for m, v in g.items()]
        z = p[p.zona.str.upper() != "PUN"].assign(w=lambda x: x.minuti.astype(float))
        for (zona, m), x in z.groupby(["zona", "mese"]):
            righe.append((f"PZ_{zona.upper()}", m, (x.prezzo * x.w).sum() / x.w.sum(), len(x)))
    for dataset, nome, filtro in (("mgp_gas", "PSV_MGPGAS_MENSILE", None), ("igi", "IGI_MENSILE", None),
                                  ("ttf_eex", "TTF_MENSILE", None)):
        d = archivio.leggi(cartella, dataset)
        if d.empty:
            continue
        if dataset == "mgp_gas":  # solo il prodotto giornaliero dell'asta MGP (non i weekend aggregati)
            d = d[d.mercato.str.upper().str.startswith("MGP")]
        d = d.groupby("data", as_index=False).prezzo.mean()
        g = d.groupby(_mese(d.data)).prezzo.agg(["mean", "count"])
        righe += [(nome, m, r["mean"], int(r["count"])) for m, r in g.iterrows()]
    try:  # PFOR,t ricostruito (forward importate o stima dal TTF spot)
        from . import pfor
        righe += pfor.come_indici(pfor.calcola(cartella))
    except Exception:  # noqa: BLE001 - un indice derivato non deve bloccare gli altri
        pass
    # PSV dal mercato a pronti del GME: media mensile dei prezzi medi ponderati giornalieri della
    # negoziazione continua MGP-GAS; dove manca, prezzo dell'asta MGP-GAS
    cont = archivio.leggi(cartella, "mgp_gas_continua")
    psv_g = None
    if not cont.empty:
        c = cont.dropna(subset=["prezzo_medio"])
        c = c[c.volumi_mwh.fillna(0) > 0]
        if not c.empty:
            psv_g = c.groupby("data").apply(lambda x: (x.prezzo_medio * x.volumi_mwh).sum() / x.volumi_mwh.sum(),
                                            include_groups=False).rename("prezzo").reset_index()
            g = psv_g.groupby(_mese(psv_g.data)).prezzo.agg(["mean", "count"])
            righe += [("PSV_MGPGAS_CONT_MENSILE", m, r["mean"], int(r["count"])) for m, r in g.iterrows()]
    asta = archivio.leggi(cartella, "mgp_gas")
    if not asta.empty:
        asta = asta[asta.mercato.str.upper().str.startswith("MGP")].groupby("data", as_index=False).prezzo.mean()
    parti = [x for x in (psv_g, asta if not asta.empty else None) if x is not None]
    unione = pd.concat(parti) if parti else pd.DataFrame()
    if not unione.empty:
        unione = unione.drop_duplicates("data", keep="first")   # la continua ha la precedenza
        g = unione.groupby(_mese(unione.data)).prezzo.agg(["mean", "count"])
        righe += [("PSV_GME_MENSILE", m, r["mean"], int(r["count"])) for m, r in g.iterrows()]
    imp = archivio.leggi(cartella, "indici_importati")
    if not imp.empty:
        righe += [(r.indice, r.mese, r.valore, None) for r in imp.itertuples()]
    out = pd.DataFrame(righe, columns=["indice", "mese", "valore", "n"])
    out["valore"] = out.valore.astype(float).round(4)
    out.to_parquet(cartella / "indici_mensili.parquet", index=False)
    return out


def leggi(cartella) -> pd.DataFrame:
    p = cartella / "indici_mensili.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["indice", "mese", "valore", "n"])
