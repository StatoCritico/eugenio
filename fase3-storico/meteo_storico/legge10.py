"""Dati climatici "aggiornati" per i calcoli della Legge 10/1991, dal clima reale del comune.

Per ogni comune, dagli ultimi N anni della serie ERA5 corretta (fase 3), calcola le grandezze che
la relazione tecnica prende dalla UNI 10349 e dal DPR 412/1993:
  * dati mensili (impostazione UNI 10349-1): temperatura media, media delle minime e delle
    massime, irradiazione giornaliera media su piano orizzontale (globale e diffusa, MJ/m²),
    pressione parziale del vapore (Pa), velocità media del vento (m/s);
  * gradi giorno (base 20 °C) sul periodo convenzionale di riscaldamento della zona (DPR 412/93,
    art. 9) e sull'anno intero, con la zona climatica che ne risulterebbe (tabella art. 2);
  * gradi giorno anno per anno e tendenza (GG per decennio);
  * temperatura esterna di progetto invernale ed estiva, come stima statistica: quantili 0,4% e
    99,6% delle ore (se c'è la serie oraria) o dei minimi/massimi giornalieri;
  * confronto con i valori ufficiali, se forniti (GG e zona del DPR 412, θe di progetto UNI 10349-3).

IMPORTANTE: per la relazione tecnica ai sensi della Legge 10 e dei decreti attuativi restano
obbligatori i valori normativi (UNI 10349:2016, DPR 412/93 e aggiornamenti). Questi dati servono
per diagnosi energetiche, analisi di sensibilità, verifica dei consumi reali e scenari climatici.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# DPR 412/93 art. 2 (zone) e art. 9 (periodi di accensione)
ZONE = [("A", 0, 600), ("B", 601, 900), ("C", 901, 1400), ("D", 1401, 2100), ("E", 2101, 3000), ("F", 3001, 1e9)]
PERIODI = {"A": ((12, 1), (3, 15)), "B": ((12, 1), (3, 31)), "C": ((11, 15), (3, 31)),
           "D": ((11, 1), (4, 15)), "E": ((10, 15), (4, 15)), "F": None}


def zona_da_gg(gg: float) -> str:
    for z, lo, hi in ZONE:
        if gg <= hi:
            return z
    return "F"


def margine_fascia(zona: str, gg: float) -> float:
    """Distanza in GG dal bordo più vicino della fascia della zona (art. 2): per A conta solo il limite
    superiore, per F solo quello inferiore."""
    _, lo, hi = next(x for x in ZONE if x[0] == zona)
    if zona == "A":
        return hi - gg
    if zona == "F":
        return gg - (lo - 1)
    return min(gg - (lo - 1), hi - gg)


def zona_risultante(gg_zona: dict, zona_dpr: str | None = None) -> str:
    """Zona che risulta dai GG (regola del 27/10/2026, uguale in fase9-clima-storico e cti_try).

    "Coerenti" sono le zone i cui GG, calcolati sul loro stesso periodo di accensione, cadono nella loro fascia
    (a cavallo D/E possono esserlo due zone). Si prende la zona del DPR 412/93 se è tra le coerenti; altrimenti
    (o senza zona DPR) la coerente più lontana dai bordi della propria fascia (a parità la prima in ordine A…F);
    se nessuna è coerente, la zona dei GG sull'anno intero."""
    coerenti = [z for z in PERIODI if zona_da_gg(gg_zona[z]) == z]
    if not coerenti:
        return zona_da_gg(gg_zona["F"])
    if zona_dpr in coerenti:
        return zona_dpr
    return max(coerenti, key=lambda z: margine_fascia(z, gg_zona[z]))


def _nel_periodo(date: pd.DatetimeIndex, zona: str) -> np.ndarray:
    per = PERIODI[zona]
    if per is None:
        return np.ones(len(date), dtype=bool)
    (m1, g1), (m2, g2) = per
    md = date.month * 100 + date.day
    return (md >= m1 * 100 + g1) | (md <= m2 * 100 + g2)


def _stagione(date: pd.DatetimeIndex) -> np.ndarray:
    """Stagione di riscaldamento indicata con l'anno di inizio (1 luglio – 30 giugno)."""
    return np.where(date.month >= 7, date.year, date.year - 1)


def pressione_vapore(t: pd.Series, ur: pd.Series) -> pd.Series:
    """Pa, formula di Magnus (coefficienti Alduchov-Eskridge)."""
    return ur / 100.0 * 610.94 * np.exp(17.625 * t / (t + 243.04))


def gradi_giorno(g: pd.DataFrame, zona: str) -> pd.Series:
    """GG per stagione sul periodo della zona."""
    d = pd.DatetimeIndex(g.data)
    gg = (20 - g.t_media).clip(lower=0).to_numpy()
    m = _nel_periodo(d, zona)
    return pd.Series(gg[m]).groupby(_stagione(d)[m]).sum()


def calcola(giornaliero: pd.DataFrame, anni: int = 10, orario: pd.DataFrame | None = None,
            ufficiali: dict | None = None, fino_a: str | None = None, zona_dpr: str | None = None) -> dict:
    """giornaliero: colonne data, t_media, t_min, t_max, ur_media, rad_globale_kwh_m2, rad_diffusa_kwh_m2,
    vento_medio_kmh (formato di meteo_storico.aggrega.giornaliero). Usa le ultime `anni` stagioni complete.
    zona_dpr: zona del comune nell'Allegato A del DPR 412/93, se c'è: decide la zona risultante quando più zone
    sono coerenti (vedi zona_risultante)."""
    g = giornaliero.copy()
    g["data"] = pd.to_datetime(g.data)
    if fino_a:
        g = g[g.data <= pd.Timestamp(fino_a)]
    d = pd.DatetimeIndex(g.data)
    g["stagione"] = _stagione(d)
    conteggio = g.groupby("stagione").size()
    complete = [s for s, n in conteggio.items() if n >= 360]
    stagioni = complete[-anni:]
    if not stagioni:
        raise ValueError("Serie troppo corta: serve almeno una stagione completa (1 luglio – 30 giugno)")
    g = g[g.stagione.isin(stagioni)]
    d = pd.DatetimeIndex(g.data)

    # --- dati mensili, impostazione UNI 10349-1
    g["mese"] = d.month
    g["pv"] = pressione_vapore(g.t_media, g.ur_media)
    m = g.groupby("mese").agg(t_media=("t_media", "mean"), t_min_media=("t_min", "mean"),
                              t_max_media=("t_max", "mean"),
                              h_globale_mj=("rad_globale_kwh_m2", "mean"), h_diffusa_mj=("rad_diffusa_kwh_m2", "mean"),
                              pv_pa=("pv", "mean"), vento_ms=("vento_medio_kmh", "mean"), ur_media=("ur_media", "mean"))
    m["h_globale_mj"] *= 3.6
    m["h_diffusa_mj"] *= 3.6
    m["vento_ms"] /= 3.6
    mensili = m.astype(float).round(2).reset_index().to_dict(orient="records")

    # --- gradi giorno e zona climatica
    gg_anno_intero = (20 - g.t_media).clip(lower=0).groupby(g.stagione).sum()
    gg_zona = {z: float(gradi_giorno(g, z).mean()) for z in PERIODI}
    # zona risultante: tra le zone coerenti, quella del DPR se c'è, altrimenti la più centrale nella sua fascia
    zona_calc = zona_risultante(gg_zona, zona_dpr or (ufficiali or {}).get("zona"))
    zona_rif = (ufficiali or {}).get("zona") or zona_calc
    serie_gg = gradi_giorno(g, zona_rif)
    if len(serie_gg) >= 5:   # con meno stagioni la tendenza non è significativa
        pend = float(np.polyfit(serie_gg.index.astype(float), serie_gg.to_numpy(), 1)[0]) * 10
    else:
        pend = None

    # --- temperature di progetto (stima statistica)
    if orario is not None and len(orario):
        t = pd.to_numeric(orario.temperature_2m, errors="coerce").dropna()
        progetto = {"invernale": round(float(t.quantile(0.004)), 1), "estiva": round(float(t.quantile(0.996)), 1),
                    "metodo": "quantili 0,4% / 99,6% delle temperature orarie"}
    else:
        progetto = {"invernale": round(float(g.t_min.quantile(0.01)), 1),
                    "estiva": round(float(g.t_max.quantile(0.99)), 1),
                    "metodo": "1° percentile dei minimi e 99° dei massimi giornalieri (manca la serie oraria)"}

    out = {
        "stagioni": [f"{s}/{str(s + 1)[2:]}" for s in stagioni],
        "giorni": int(len(g)),
        "mensili": mensili,
        "gradi_giorno": {
            "zona_di_riferimento": zona_rif,
            "gg_periodo_zona": round(float(serie_gg.mean()), 0),
            "gg_anno_intero": round(float(gg_anno_intero.mean()), 0),
            "gg_per_periodo_di_ogni_zona": {z: round(v, 0) for z, v in gg_zona.items()},
            "zona_risultante": zona_calc,
            "per_stagione": {f"{s}/{str(s + 1)[2:]}": round(float(v), 0) for s, v in serie_gg.items()},
            "tendenza_gg_per_decennio": None if pend is None else round(pend, 0),
            "minimo": round(float(serie_gg.min()), 0), "massimo": round(float(serie_gg.max()), 0),
        },
        "temperatura_progetto": progetto,
        "avvertenza": "Valori dal clima osservato (ERA5 corretto). Per la relazione tecnica ex Legge 10 "
                      "restano obbligatori i valori normativi (UNI 10349, DPR 412/93).",
    }
    if ufficiali:
        conf = {}
        if ufficiali.get("gg"):
            conf["gg_ufficiali"] = ufficiali["gg"]
            conf["differenza_gg"] = round(out["gradi_giorno"]["gg_periodo_zona"] - float(ufficiali["gg"]), 0)
            conf["differenza_percentuale"] = round(100 * conf["differenza_gg"] / float(ufficiali["gg"]), 1)
        if ufficiali.get("zona"):
            conf["zona_ufficiale"] = ufficiali["zona"]
            conf["zona_cambierebbe"] = zona_calc != ufficiali["zona"]
        if ufficiali.get("theta_progetto"):
            conf["theta_progetto_ufficiale"] = ufficiali["theta_progetto"]
            conf["differenza_theta"] = round(progetto["invernale"] - float(ufficiali["theta_progetto"]), 1)
        out["confronto_ufficiali"] = conf
    return out


def ufficiali_da_csv(path, istat: str) -> dict | None:
    """CSV facoltativo con i valori normativi: istat;gg;zona;theta_progetto (separatore ; e decimali ,)."""
    df = pd.read_csv(path, sep=";", dtype=str)
    r = df[df.istat.str.zfill(6) == istat]
    if r.empty:
        return None
    r = r.iloc[0]
    num = lambda x: float(str(x).replace(",", ".")) if pd.notna(x) and str(x).strip() else None  # noqa: E731
    return {"gg": num(r.get("gg")), "zona": (r.get("zona") or "").strip().upper() or None,
            "theta_progetto": num(r.get("theta_progetto"))}
