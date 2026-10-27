#!/usr/bin/env python3
"""Calcola gli indicatori climatici per comune dalla cache giornaliera di scarica.py.

  python calcola.py [--cache cache] [--uscita dati] [--dpr ../sito_fin/dati/dpr412.json] [--istat F]

Per ogni comune (serie giornaliera ricostruita come descritto nel README):
  * mensili per anno solare (impostazione UNI 10349-1): t media, media delle minime e delle massime,
    irradiazione giornaliera media globale e diffusa su piano orizzontale (MJ/m²), pressione parziale
    del vapore (Pa), vento medio a 10 m (m/s);
  * gradi giorno base 20 °C per stagione 1/7–30/6 (DPR 412/93): sul periodo di accensione della zona di
    legge del comune, sull'anno intero ("convenzionali"), e la zona climatica risultante per stagione;
  * temperature di progetto statistiche su finestre mobili di 10 anni solari e su periodi fissi di 30;
  * tendenze (regressione lineare, GG per decennio) e confronto con il DPR (media 10 e 30 stagioni).

Prodotti in <uscita>/:
  clima/<RR>/<istat>.json            sintesi del comune (GG, zone, tendenze, periodi, progetto)  ~4 kB
  clima/<RR>/<istat>_mensili.json    mensili anno per anno (caricati su richiesta)             ~20 kB
  clima/<RR>.json                    GG e zone per stagione di tutti i comuni della regione
  clima/indice.json                  metadati, fonti, periodi, scale dei numeri
  clima_stagioni.csv, clima_sintesi.csv, clima_mensili.parquet   nazionali, per il download
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
import indicatori as ind  # noqa: E402

log = logging.getLogger("calcola")

VAR_L = ["t_media", "t_min", "t_max", "pv"]                     # da ERA5-Land (dal 1950)
VAR_E = ["t_media", "t_min", "t_max", "pv", "ghi_kwh", "dif_kwh", "vento"]
MENSILI = ["t_media", "t_min", "t_max", "h_glob", "h_dif", "pv", "vento"]
K_ESTREMI = 120              # minimi/massimi giornalieri tenuti per anno (bastano per l'1% su 30 anni)
FINESTRA = 10                # anni della finestra mobile per le temperature di progetto
ANNI_OFFSET = (1950, 1979)   # sovrapposizione ERA5 / ERA5-Land per raccordare il decennio 1940-49
PERIODI_FISSI = [(1951, 1980), (1961, 1990), (1971, 2000), (1981, 2010), (1991, 2020)]
RIF_DPR = (1961, 1990)       # periodo della serie usato per riscalare il DPR (vedi README)
DPR_PREDEFINITO = Path("/home/claude/sito_fin/dati/dpr412.json")



# Licenza (eugenio.statocritico.it/licenza.html#dati): elaborazioni di EuGEnio con licenza CC BY 4.0, da citare
# come fonte. Le righe finali iniziano con "#", come nei file scaricati dal server (leggere con comment="#").
CITAZIONE = "Fonte: EuGEnio – eugenio.statocritico.it"
LICENZA = ("Elaborazioni di EuGEnio con licenza CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.it): "
           "si possono riutilizzare, anche modificate, citando EuGEnio come fonte nei documenti che le usano e "
           "mantenendo le fonti indicate sopra, che restano soggette alle loro licenze. "
           "Dettagli: https://eugenio.statocritico.it/licenza.html#dati")


def piede_csv(indice: dict) -> list[str]:
    """Righe finali dei CSV nazionali: fonte, avvertenza, licenza e formula di citazione."""
    data = dt.date.fromisoformat(indice["versione"]).strftime("%d/%m/%Y")
    return [f"# Fonte: {indice['attribuzione']}", f"# Avvertenza: {indice['avvertenza']}",
            f"# Licenza: {LICENZA}", f"# Come citare: {CITAZIONE} (dati aggiornati il {data})"]


def aggiungi_piede_csv(percorso: Path, indice: dict) -> None:
    with open(percorso, "a", encoding="utf-8", newline="") as f:
        f.write("\n".join(piede_csv(indice)) + "\n")


def carica_anno(cache: Path, dom: str, anno: int, ncelle: int, variabili):
    p = cache / dom / f"{anno}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    nd = (dt.date(anno + 1, 1, 1) - dt.date(anno, 1, 1)).days
    gi = (pd.to_datetime(df.data) - pd.Timestamp(anno, 1, 1)).dt.days.to_numpy()
    ce = df.cella.to_numpy()
    out = {}
    for v in variabili:
        a = np.full((ncelle, nd), np.nan, np.float32)
        a[ce, gi] = df[v].to_numpy()
        out[v] = a
    return out


def indice_celle(cache: Path, dom: str, comuni: pd.DataFrame) -> np.ndarray:
    c = pd.read_parquet(cache / dom / "celle.parquet")
    pos = {(int(i), int(j)): k for k, (i, j) in enumerate(zip(c.i, c.j))}
    return np.array([pos[(int(i), int(j))] for i, j in zip(comuni[f"{dom}_i"], comuni[f"{dom}_j"])]), len(c)


def calcola(cache: Path, comuni: pd.DataFrame, dpr: dict, quota: str = "dpr"):
    nc = len(comuni)
    iL, nL = indice_celle(cache, "era5_land", comuni)
    iE, nE = indice_celle(cache, "era5", comuni)
    z = comuni.quota_m.to_numpy(float)
    if quota == "dpr":
        zd = np.array([(dpr.get(i) or [None, None, None])[2] for i in comuni.istat], dtype=float)
        z = np.where(np.isfinite(zd), zd, z)
    comuni = comuni.assign(quota_rif=z)
    dzL = ind.correzione_quota(comuni.era5_land_quota, z).astype(np.float32)[:, None]
    dzE = ind.correzione_quota(comuni.era5_quota, z).astype(np.float32)[:, None]

    anni_E = sorted(int(p.stem) for p in (cache / "era5").glob("[0-9]*.parquet"))
    anni_L = set(int(p.stem) for p in (cache / "era5_land").glob("[0-9]*.parquet"))
    a0, a1 = anni_E[0], anni_E[-1]
    ny = a1 - a0 + 1
    mens = np.full((nc, ny, 12, len(MENSILI)), np.nan, np.float32)
    gmese = np.zeros((nc, ny, 12), np.int16)
    low = np.full((nc, ny, K_ESTREMI), np.nan, np.float32)
    high = np.full((nc, ny, K_ESTREMI), np.nan, np.float32)
    nval = np.zeros((nc, ny), np.int16)
    s0 = a0 - 1                                         # stagione (anno di inizio) del primo gennaio
    ns = a1 - s0 + 1
    gg = np.zeros((nc, ns, 6), np.float64)
    ggn = np.zeros((nc, ns, 6), np.int16)
    fonte = np.full(ny, " ", dtype="<U1")
    off_s = np.zeros((nc, 12, 4)); off_n = np.zeros((nc, 12, 4))
    offset = None
    senza_land = None

    ordine = [a for a in range(a0, a1 + 1) if a in anni_L] + [a for a in range(a0, a1 + 1) if a not in anni_L]
    for anno in ordine:
        E = carica_anno(cache, "era5", anno, nE, VAR_E)
        L = carica_anno(cache, "era5_land", anno, nL, VAR_L) if anno in anni_L else None
        if anno not in anni_L and offset is None:
            with np.errstate(invalid="ignore"):
                offset = np.where(off_n > 0, off_s / np.maximum(off_n, 1), 0.0).astype(np.float32)
        nd = E["t_media"].shape[1]
        date = pd.date_range(f"{anno}-01-01", periods=nd)
        mese = date.month.to_numpy() - 1
        yi = anno - a0
        x = {}
        for v in ("t_media", "t_min", "t_max"):
            x[v + "_E"] = E[v][iE] + dzE
        x["pv_E"] = E["pv"][iE]
        if L is not None:
            if senza_land is None:      # celle ERA5-Land senza dati (isole minuscole): si usa ERA5
                senza_land = ~np.isfinite(L["t_media"][iL]).any(axis=1)
                if senza_land.any():
                    log.warning("%d comuni senza dati ERA5-Land: uso ERA5 (%s)", senza_land.sum(),
                                ", ".join(comuni.nome[senza_land].tolist()[:10]))
            for v in ("t_media", "t_min", "t_max"):
                x[v] = np.where(senza_land[:, None], x[v + "_E"], L[v][iL] + dzL)
            x["pv"] = np.where(senza_land[:, None], x["pv_E"], L["pv"][iL])
            fonte[yi] = "L"
            if ANNI_OFFSET[0] <= anno <= ANNI_OFFSET[1]:
                for k, v in enumerate(("t_media", "t_min", "t_max", "pv")):
                    d = x[v] - x[v + "_E"]
                    for m in range(12):
                        sel = d[:, mese == m]
                        ok = np.isfinite(sel)
                        off_s[:, m, k] += np.where(ok, sel, 0).sum(1)
                        off_n[:, m, k] += ok.sum(1)
            # giorni mancanti in ERA5-Land (rari): ERA5 + scarto medio non ancora noto -> lasciati vuoti
        else:
            for k, v in enumerate(("t_media", "t_min", "t_max", "pv")):
                x[v] = x[v + "_E"] + offset[:, mese, k]
            fonte[yi] = "E"
        h_glob = E["ghi_kwh"][iE] * 3.6
        h_dif = E["dif_kwh"][iE] * 3.6
        vento = E["vento"][iE]
        serie = [x["t_media"], x["t_min"], x["t_max"], h_glob, h_dif, x["pv"], vento]
        with np.errstate(all="ignore"):
            for m in range(12):
                sel = mese == m
                for k, s in enumerate(serie):
                    mens[:, yi, m, k] = np.nanmean(s[:, sel], axis=1)
                gmese[:, yi, m] = np.isfinite(x["t_media"][:, sel]).sum(1)
        tmin = np.where(np.isfinite(x["t_min"]), x["t_min"], np.inf)
        tmax = np.where(np.isfinite(x["t_max"]), -x["t_max"], np.inf)
        k = min(K_ESTREMI, nd)
        low[:, yi, :k] = np.sort(np.partition(tmin, k - 1, axis=1)[:, :k], axis=1)
        high[:, yi, :k] = -np.sort(np.partition(tmax, k - 1, axis=1)[:, :k], axis=1)
        low[~np.isfinite(low)] = np.nan
        high[~np.isfinite(high)] = np.nan
        nval[:, yi] = np.isfinite(x["t_min"]).sum(1)
        # gradi giorno: luglio-dicembre -> stagione anno, gennaio-giugno -> stagione anno-1
        g = np.clip(ind.T_BASE - x["t_media"], 0, None)
        ok = np.isfinite(g)
        g = np.where(ok, g, 0)
        mk = ind.maschere_periodi(date.month.to_numpy(), date.day.to_numpy())
        seconda = date.month.to_numpy() >= 7
        for parte, s in ((~seconda, anno - 1), (seconda, anno)):
            si = s - s0
            for z_ in range(6):
                sel = mk[z_] & parte
                gg[:, si, z_] += g[:, sel].sum(1)
                ggn[:, si, z_] += ok[:, sel].sum(1)
        log.info("anno %d (%s) elaborato", anno, fonte[yi])

    # completezza: tutti i giorni del periodo presenti (i bisestili hanno un giorno in più)
    lung = ind.lunghezza_periodi()
    completo = ggn >= lung[None, None, :]
    gg = np.where(completo, gg, np.nan)
    stagioni = np.arange(s0, s0 + ns)
    anni = np.arange(a0, a1 + 1)
    anno_completo = (nval >= 365)
    mens = np.where((gmese >= 28)[..., None], mens, np.nan)
    fonte_st = []
    for s in stagioni:
        f1 = fonte[s - a0] if s - a0 >= 0 else " "
        f2 = fonte[s + 1 - a0] if s + 1 - a0 < ny else " "
        fonte_st.append(f1 if f1 == f2 else "M")
    return dict(comuni=comuni, anni=anni, stagioni=stagioni, mens=mens, gg=gg, low=low, high=high, nval=nval,
                anno_completo=anno_completo, fonte_anni="".join(fonte), fonte_stagioni="".join(fonte_st),
                offset=offset, senza_land=senza_land)


def progetto_finestra(low, high, nval, anni_idx):
    """θ invernale = 1° percentile dei minimi giornalieri, θ estiva = 99° dei massimi, sugli anni dati."""
    n = int(nval[anni_idx].sum())
    if n == 0:
        return np.nan, np.nan
    lo = low[anni_idx].reshape(-1)
    hi = high[anni_idx].reshape(-1)
    return (ind.quantile_da_estremi(lo, n, 0.01, True), ind.quantile_da_estremi(hi, n, 0.99, False))


def r1(v, nd=1):
    if v is None or not np.isfinite(v):
        return None
    return int(round(float(v))) if nd == 0 else round(float(v), nd)


def costruisci_uscite(R: dict, dpr: dict, uscita: Path, scrivi_json: bool = True):
    comuni, anni, stagioni = R["comuni"], R["anni"], R["stagioni"]
    mens, gg, low, high, nval = R["mens"], R["gg"], R["low"], R["high"], R["nval"]
    ok_st = np.isfinite(gg[:, :, 5]).any(0)            # stagioni complete per almeno un comune
    st_idx = np.where(ok_st)[0]
    st = stagioni[st_idx]
    ok_an = R["anno_completo"].any(0)
    an_idx = np.where(ok_an)[0]
    ultimo_anno = int(anni[an_idx[-1]])
    ultima_st = int(st[-1])
    periodi = [(a, b) for a, b in PERIODI_FISSI if b <= ultimo_anno]
    periodi += [(ultimo_anno - 29, ultimo_anno), (ultimo_anno - 9, ultimo_anno)]
    cart = uscita / "clima"
    cart.mkdir(parents=True, exist_ok=True)
    reg_out, righe_st, righe_sint = {}, [], []
    for c, r in enumerate(comuni.itertuples(index=False)):
        voce = dpr.get(r.istat)
        info_dpr = voce if voce and voce[0] is not None else None     # GG di legge univoci
        zona_legge = voce[1] if voce and voce[1] else None             # anche fusioni con zona unica
        g6 = gg[c][st_idx]                               # stagioni × 6 zone
        if zona_legge is None:                          # senza DPR: zona coerente sulla media 1991-2020
            sel = (st >= 1990) & (st <= 2019)
            zona_legge = ind.zona_coerente(np.nanmean(g6[sel], 0)) if sel.any() else "E"
            origine_zona = "calcolata 1991-2020 (il DPR non ha una zona unica per il comune)"
        else:
            origine_zona = "DPR 412/93" if info_dpr else "DPR 412/93 (zona comune a tutti i comuni d'origine)"
        kz = ind.NOMI_ZONE.index(zona_legge)
        gz = g6[:, kz]
        ga = g6[:, 5]
        zone_st = "".join(ind.zona_coerente(v) if np.isfinite(v[5]) else "-" for v in g6)
        x = st.astype(float)
        tend = {"tutta": ind.pendenza_per_decennio(x, gz),
                "dal_1981": ind.pendenza_per_decennio(x[st >= 1981], gz[st >= 1981]),
                "ultime_30": ind.pendenza_per_decennio(x[-30:], gz[-30:])}
        t_annua = np.nanmean(mens[c, :, :, 0], axis=1)
        t_annua = np.where(R["anno_completo"][c], t_annua, np.nan)
        tend_t = ind.pendenza_per_decennio(anni.astype(float), t_annua)
        m10, m30 = np.nanmean(gz[-10:]), np.nanmean(gz[-30:])
        conf = None
        if info_dpr:
            gd = float(info_dpr[0])
            conf = {"gg_dpr": gd, "zona_dpr": info_dpr[1], "alt_dpr": info_dpr[2],
                    "diff_10": r1(m10 - gd, 0), "diff_10_pct": r1(100 * (m10 - gd) / gd),
                    "diff_30": r1(m30 - gd, 0), "diff_30_pct": r1(100 * (m30 - gd) / gd),
                    "zona_10": ind.zona_da_gg(m10), "zona_30": ind.zona_da_gg(m30)}
            # DPR "aggiornato" per rapporto: GG_DPR × GG(ultime N) / GG(1961-1990), stessa serie di rianalisi.
            # Toglie gran parte dell'errore sistematico della cella (costa, città, fondovalle) e tiene il
            # cambiamento relativo. Periodo di riferimento 1961-1990 per ipotesi (il DPR non dichiara il suo).
            rif = np.nanmean(gz[(st >= RIF_DPR[0] - 1) & (st <= RIF_DPR[1] - 1)])
            if np.isfinite(rif) and rif > 0:
                conf.update({"riferimento_rapporto": f"{RIF_DPR[0]}-{RIF_DPR[1]}", "gg_rif": r1(rif, 0),
                             "dpr_aggiornato_10": r1(gd * m10 / rif, 0), "dpr_aggiornato_30": r1(gd * m30 / rif, 0),
                             "zona_aggiornata_10": ind.zona_da_gg(gd * m10 / rif),
                             "zona_aggiornata_30": ind.zona_da_gg(gd * m30 / rif)})
        # temperature di progetto su finestre mobili di FINESTRA anni solari completi
        prog_inv, prog_est, prog_fine = [], [], []
        for k in range(len(anni)):
            idx = np.arange(k - FINESTRA + 1, k + 1)
            if idx[0] < 0 or not R["anno_completo"][c, idx].all():
                continue
            a, b = progetto_finestra(low[c], high[c], nval[c], idx)
            prog_fine.append(int(anni[k])); prog_inv.append(r1(a)); prog_est.append(r1(b))
        per_out = {}
        for a, b in periodi:
            ia = np.where((anni >= a) & (anni <= b) & R["anno_completo"][c])[0]
            if (a, b) in periodi[-2:]:
                isel = np.arange(len(st))[-(b - a + 1):]   # ultime 10 / 30 stagioni complete
            else:
                isel = np.where((st >= a - 1) & (st <= b - 1))[0]   # 1991-2020 -> 30 stagioni 1990/91 ... 2019/20
            if len(ia) == 0:
                continue
            mm = np.nanmean(mens[c, ia], axis=0)       # 12 × 7
            pi, pe = progetto_finestra(low[c], high[c], nval[c], ia)
            gzp = np.nanmean(gz[isel]) if len(isel) else np.nan
            per_out[f"{a}-{b}"] = {
                "anni": len(ia), "stagioni": [f"{st[isel[0]]}/{str(st[isel[0]] + 1)[2:]}",
                                              f"{st[isel[-1]]}/{str(st[isel[-1]] + 1)[2:]}"] if len(isel) else None,
                "gg_zona": r1(gzp, 0), "gg_anno": r1(np.nanmean(ga[isel]), 0) if len(isel) else None,
                "zona": ind.zona_da_gg(gzp) if np.isfinite(gzp) else None,
                "zona_coerente": ind.zona_coerente(np.nanmean(g6[isel], 0)) if len(isel) else None,
                "theta_inv": r1(pi), "theta_est": r1(pe),
                "mensili": {v: [r1(mm[m, k], 2 if v.startswith("h_") else 1) if v != "pv" else r1(mm[m, k], 0)
                                for m in range(12)] for k, v in enumerate(MENSILI)}}
        sintesi = {
            "istat": r.istat, "nome": r.nome, "prov": r.provincia,
            "punto": {"lat": r.lat, "lon": r.lon, "quota_m": r1(r.quota_m, 0), "metodo": r.metodo_punto},
            "quota_correzione_m": r1(r.quota_rif, 0),
            "celle": {d: {"lat": round(getattr(r, f"{d}_i") * res - 90, 2), "lon": round(getattr(r, f"{d}_j") * res - 180, 2),
                          "quota_m": r1(getattr(r, f"{d}_quota"), 0), "dist_km": r1(getattr(r, f"{d}_dist_km"))}
                      for d, res in (("era5_land", 0.1), ("era5", 0.25))},
            "zona_riferimento": zona_legge, "origine_zona": origine_zona,
            "solo_era5": bool(R["senza_land"][c]) if R["senza_land"] is not None else False,
            "stagioni": {"prima": f"{st[0]}/{str(st[0] + 1)[2:]}", "da": int(st[0]),
                         "gg_zona": [r1(v, 0) for v in gz], "gg_anno": [r1(v, 0) for v in ga],
                         "zona": zone_st, "fonte": R["fonte_stagioni"][st_idx[0]:st_idx[-1] + 1]},
            "tendenze": {"gg_per_decennio": {k: r1(v, 0) for k, v in tend.items()},
                         "t_media_annua_per_decennio": r1(tend_t, 2),
                         "media_10": r1(m10, 0), "media_30": r1(m30, 0)},
            "confronto_dpr": conf,
            "dpr_origini": [{"nome": o[3], "gg": o[0], "zona": o[1], "alt": o[2]} for o in (voce[5] if voce and len(voce) > 5 else [])] or None,
            "dpr_nota": (voce[4] or None) if voce and len(voce) > 4 else None,
            "progetto": {"finestra_anni": FINESTRA, "fine": prog_fine, "inv": prog_inv, "est": prog_est},
            "periodi": per_out,
        }
        # mensili anno per anno, interi scalati (vedi indice.json)
        scala = {"t_media": 10, "t_min": 10, "t_max": 10, "h_glob": 10, "h_dif": 10, "pv": 1, "vento": 10}
        mm = {}
        for k, v in enumerate(MENSILI):
            a = mens[c, an_idx[0]:an_idx[-1] + 1, :, k] * scala[v]
            mm[v] = [None if not np.isfinite(q) else int(round(q)) for q in a.reshape(-1)]
        mensili = {"istat": r.istat, "da": int(anni[an_idx[0]]), "a": int(anni[an_idx[-1]]), "scala": scala,
                   "fonte": R["fonte_anni"][an_idx[0]:an_idx[-1] + 1], **mm}
        rr = r.regione_cod
        if scrivi_json:
            (cart / rr).mkdir(exist_ok=True)
            (cart / rr / f"{r.istat}.json").write_text(json.dumps(sintesi, ensure_ascii=False, separators=(",", ":")),
                                                       encoding="utf-8")
            (cart / rr / f"{r.istat}_mensili.json").write_text(json.dumps(mensili, separators=(",", ":")),
                                                               encoding="utf-8")
        reg_out.setdefault(rr, {})[r.istat] = {
            "n": r.nome, "p": r.provincia, "zl": zona_legge, "dpr": info_dpr[0] if info_dpr else None,
            "gg": [None if not np.isfinite(v) else int(round(v)) for v in gz], "z": zone_st,
            "m10": r1(m10, 0), "m30": r1(m30, 0), "t": r1(tend["tutta"], 0), "t81": r1(tend["dal_1981"], 0)}
        for k, s in enumerate(st):
            righe_st.append((r.istat, r.nome, r.provincia, f"{s}/{str(s + 1)[2:]}", zona_legge, r1(gz[k], 0),
                             r1(ga[k], 0), zone_st[k], R["fonte_stagioni"][st_idx[k]]))
        p91 = per_out.get("1991-2020", {})
        p10 = per_out.get(f"{ultimo_anno - 9}-{ultimo_anno}", {})
        righe_sint.append({
            "codice_istat": r.istat, "comune": r.nome, "provincia": r.provincia, "regione": r.regione,
            "quota_punto_m": r1(r.quota_m, 0), "quota_correzione_m": r1(r.quota_rif, 0), "zona_dpr": voce[1] if voce and voce[1] else None,
            "gg_dpr": info_dpr[0] if info_dpr else None, "zona_riferimento": zona_legge,
            "gg_1991_2020": p91.get("gg_zona"), "gg_ultime_10": r1(m10, 0), "gg_ultime_30": r1(m30, 0),
            "diff_ultime_10_pct": conf["diff_10_pct"] if conf else None,
            "diff_ultime_30_pct": conf["diff_30_pct"] if conf else None,
            "gg_dpr_aggiornato_10": conf.get("dpr_aggiornato_10") if conf else None,
            "gg_dpr_aggiornato_30": conf.get("dpr_aggiornato_30") if conf else None,
            "zona_dpr_aggiornata_10": conf.get("zona_aggiornata_10") if conf else None,
            "zona_da_gg_ultime_10": ind.zona_da_gg(m10), "zona_da_gg_ultime_30": ind.zona_da_gg(m30),
            "tendenza_gg_decennio": r1(tend["tutta"], 0), "tendenza_gg_decennio_dal_1981": r1(tend["dal_1981"], 0),
            "tendenza_t_annua_decennio": r1(tend_t, 2),
            "theta_inv_1991_2020": p91.get("theta_inv"), "theta_est_1991_2020": p91.get("theta_est"),
            "theta_inv_ultimi_10": p10.get("theta_inv"), "theta_est_ultimi_10": p10.get("theta_est")})
    indice = {
        "versione": dt.date.today().isoformat(),
        "stagioni": [f"{st[0]}/{str(st[0] + 1)[2:]}", f"{ultima_st}/{str(ultima_st + 1)[2:]}"],
        "anni_mensili": [int(anni[an_idx[0]]), int(anni[an_idx[-1]])], "periodi": [f"{a}-{b}" for a, b in periodi],
        "finestra_progetto_anni": FINESTRA,
        "scala_mensili": {"t_media": 10, "t_min": 10, "t_max": 10, "h_glob": 10, "h_dif": 10, "pv": 1, "vento": 10},
        "unita": {"t": "°C", "h_glob": "MJ/m² giorno", "h_dif": "MJ/m² giorno", "pv": "Pa", "vento": "m/s a 10 m",
                  "gg": "°C·giorno base 20 °C"},
        "fonte_codici": {"L": "ERA5-Land 0,1°", "E": "ERA5 0,25° raccordato a ERA5-Land (scarto medio mensile 1950-1979)",
                         "M": "stagione a cavallo dei due"},
        "attribuzione": "Dati meteo: Open-Meteo.com (CC BY 4.0), da ERA5 ed ERA5-Land. Contiene informazioni "
                        "modificate del Copernicus Climate Change Service (" + str(dt.date.today().year) + "). "
                        "Né la Commissione europea né l'ECMWF sono responsabili dell'uso di queste informazioni. "
                        "Comuni e sezioni di censimento: ISTAT (CC BY 4.0) via Gramscii.",
        "avvertenza": "Indicatori dal clima ricostruito (rianalisi), non sostituiscono i valori normativi "
                      "(UNI 10349, DPR 412/93) obbligatori per la relazione tecnica ex Legge 10.",
    }
    (cart / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    if scrivi_json:
        (cart / "regioni.json").write_text(json.dumps(dict(zip(comuni.istat, comuni.regione_cod)),
                                                      separators=(",", ":")), encoding="utf-8")
        for rr, d in reg_out.items():
            (cart / f"{rr}.json").write_text(json.dumps({"da": int(st[0]), "comuni": d}, ensure_ascii=False,
                                                        separators=(",", ":")), encoding="utf-8")
    pd.DataFrame(righe_st, columns=["codice_istat", "comune", "provincia", "stagione", "zona_riferimento",
                                    "gg_periodo_zona", "gg_anno_intero", "zona_da_gg_stagione", "fonte"]
                 ).to_csv(uscita / "clima_stagioni.csv", sep=";", index=False, decimal=",", encoding="utf-8-sig")
    pd.DataFrame(righe_sint).to_csv(uscita / "clima_sintesi.csv", sep=";", index=False, decimal=",", encoding="utf-8-sig")
    for nome in ("clima_stagioni.csv", "clima_sintesi.csv"):    # fonti, licenza e citazione in fondo
        aggiungi_piede_csv(uscita / nome, indice)
    # mensili nazionali (lunghi) in parquet
    nc, ny = mens.shape[:2]
    idx = pd.MultiIndex.from_product([comuni.istat, anni, range(1, 13)], names=["codice_istat", "anno", "mese"])
    dfm = pd.DataFrame(mens.reshape(nc * ny * 12, len(MENSILI)), index=idx, columns=MENSILI).dropna(how="all")
    dfm.round(2).reset_index().to_parquet(uscita / "clima_mensili.parquet", index=False, compression="zstd")
    return indice


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", default="cache")
    p.add_argument("--uscita", default="dati")
    p.add_argument("--dpr", default=str(DPR_PREDEFINITO), help="dpr412.json del sito (chiave ISTAT)")
    p.add_argument("--istat", help="file con i codici ISTAT da elaborare (campione)")
    p.add_argument("--quota", choices=["dem", "dpr"], default="dpr",
                   help="quota di riferimento per la correzione di temperatura: altitudine della casa comunale "
                        "del DPR (predefinita; DEM del baricentro edifici se il DPR non c'è) oppure sempre il DEM "
                        "del baricentro edifici")
    p.add_argument("--senza-json", action="store_true", help="solo CSV/parquet nazionali")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    comuni = pd.read_parquet(QUI / "dati" / "comuni.parquet")
    if a.istat:
        ist = [x.strip().zfill(6) for x in Path(a.istat).read_text().split() if x.strip()]
        comuni = comuni[comuni.istat.isin(ist)]
    comuni = comuni.reset_index(drop=True)
    dpr = {}
    if Path(a.dpr).exists():
        dpr = json.loads(Path(a.dpr).read_text(encoding="utf-8"))["comuni"]
        log.info("DPR 412: %d comuni da %s", len(dpr), a.dpr)
    else:
        log.warning("DPR 412 non trovato (%s): confronto omesso, zona calcolata", a.dpr)
    R = calcola(QUI / a.cache, comuni, dpr, a.quota)
    uscita = QUI / a.uscita
    uscita.mkdir(parents=True, exist_ok=True)
    costruisci_uscite(R, dpr, uscita, scrivi_json=not a.senza_json)
    log.info("Fatto: %d comuni", len(comuni))


if __name__ == "__main__":
    main()
