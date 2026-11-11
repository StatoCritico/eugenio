"""Indici dei prezzi pubblicabili (11/11/2026, decisioni di Paolo): file per la pagina Statistiche › Indici dei prezzi e
per la newsletter.

Cosa entra, e solo questo (`INDICI_AMMESSI`):
- **energia elettrica**: i prezzi dei listini mensili pubblicati dalle centrali (Intercent-ER, lotti 1 e 2; Consip,
  corrispettivi dei 17 lotti), per lotto e fascia, così come li pubblicano (PUN + spread): **mai il PUN da solo**;
- **gas**: i prezzi dei listini gas Intercent-ER (€/Smc, per lotto e uso), il **PSV day-ahead mensile pubblicato da ARERA** (CMEM,m; autorizzato da Paolo l'11/11/2026) e il **PFOR,t
  ricostruito da EuGEnio** (stesso valore nei tre mesi del trimestre). Dei dati EEX (TTF giornaliero, future) non esce
  nessun valore: il PFOR è un'elaborazione nostra, con il metodo dichiarato.
Per ogni indice: l'anno in corso e l'anno prima, gennaio–dicembre (null dove il mese non c'è ancora).

Uscita JSON (scritta dal worker in /sito/dati/prezzi/indici.json):
  {"aggiornato", "anni": [prima, ora], "sezioni": [{"id", "titolo", "indici": [{"id", "titolo", "unita", "fonte",
   "licenza", "nota", "lotti": {"6": {"nome", "varianti": {"F1": {"2025": [12], "2026": [12]}, …}}}, "lotto_predefinito",
   "dettagli": {…}}]}], "in_attesa": [...]}
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import pandas as pd

from . import indici, listini

INDICI_AMMESSI = {"PSV_DA", "PFOR"}        # dagli indici mensili: nient'altro (niente PUN, PZ, TTF, IGI, PSV GME)
FASCE = ["F1", "F2", "F3", "F0"]
DEC_GAS = 4          # PSV e PFOR con quattro decimali (11/11/2026, Paolo, 23:36)
USI = ["Usi termici", "Usi non termici", "Cogenerazione"]          # varianti dei listini gas, in quest'ordine
NOMI_CENTRALI = {"Intercent-ER": "Intercent-ER", "Consip": "Consip"}
LICENZA_ARERA = "CC BY-SA 4.0"
NOTA_LISTINO = ("Prezzo dell'energia del listino della convenzione: PUN medio mensile per fascia più lo spread fisso "
                "del fornitore (garanzie d'origine comprese), IVA esclusa. Non comprende perdite di rete, "
                "dispacciamento, trasporto, oneri di sistema e imposte.")
NOTA_LISTINO_GAS = ("Prezzo del gas del listino della convenzione: PSV medio mensile più lo spread fisso del fornitore, "
                    "in €/Smc, IVA esclusa. Non comprende trasporto, oneri di sistema e accise. Il lotto 1 segue l'anno "
                    "termico (da ottobre a settembre).")
NOTA_CONSIP = ("Prezzo variabile dei corrispettivi mensili della convenzione Consip: PUN medio mensile per fascia "
               "più lo spread del lotto, al netto delle perdite di rete, IVA esclusa. Non comprende opzione verde, "
               "dispacciamento, trasporto, oneri di sistema e imposte.")
NOTA_PSV = ("Media mensile del PSV day-ahead che ARERA pubblica come CMEM,m per il servizio di tutela della "
            "vulnerabilità: è l'indice del gas di molte convenzioni (Intercent-ER GN23, CET).")
NOTA_PFOR = ("Indice PFOR,t dell'ARERA (TIVG art. 6.2 c): media delle quotazioni del gas al TTF per il trimestre, "
             "rilevate nel secondo mese prima del trimestre. ARERA lo ha calcolato fino al III trimestre 2022; dopo lo "
             "ricalcola EuGEnio con lo stesso metodo. I valori trimestrali fino al IV trimestre 2026 sono quelli "
             "dell'archivio di EuGEnio, in €/Smc, convertiti in €/MWh con il PCS ARERA (0,03852 GJ/Smc); dal I "
             "trimestre 2027 si calcolano dalle quotazioni trimestrali. È trimestrale: lo stesso valore nei tre mesi, per "
             "il confronto con il PSV.")


def _vuoto() -> list:
    return [None] * 12


def _metti(serie: dict, anno: int, mese: int, valore, dec: int = 2) -> None:
    if valore is None or (isinstance(valore, float) and math.isnan(valore)):
        return
    serie.setdefault(str(anno), _vuoto())[mese - 1] = round(float(valore), dec)


def _anni(oggi: dt.date) -> tuple[int, int]:
    return oggi.year - 1, oggi.year


def _listini(cartella: Path, cartella_convenzioni: Path | None, anni: tuple[int, int]) -> list[dict]:
    """Un indice per serie di listini (Intercent-ER, Consip…), con i lotti da scegliere e le fasce per lotto."""
    df = listini.leggi(cartella)
    if df.empty:
        return []
    df = df[pd.to_datetime(df.data).dt.year.isin(anni)]
    if "lotto_nome" not in df:
        df = df.assign(lotto_nome=None)
    fonti = {}
    for f in listini.fonti(cartella_convenzioni):
        fonti.setdefault(f["serie"], f)
    out = []
    for serie, x in df.groupby("serie", sort=False):
        f = fonti.get(serie, {})
        centrale = x.centrale.iloc[0]
        unita = x.unita.iloc[0] if "unita" in x else "€/MWh"
        dec = 4 if unita == "€/Smc" else 2
        lotti = {}
        for lotto, y in sorted(x.groupby("lotto"), key=lambda kv: (len(str(kv[0])), str(kv[0]))):
            varianti = {}
            for r in y.itertuples():
                d = pd.Timestamp(r.data)
                _metti(varianti.setdefault(r.fascia, {}), d.year, d.month, r.prezzo, dec)
            nomi = [n for n in y.lotto_nome.dropna().unique() if n]
            nome = f.get("lotti", {}).get(str(lotto)) or (f"Lotto {lotto}: {nomi[0]}" if nomi else f"Lotto {lotto}")
            ordine = [k for k in FASCE + USI if k in varianti] + sorted(k for k in varianti if k not in FASCE + USI)
            lotti[str(lotto)] = {"nome": nome, "varianti": {k: varianti[k] for k in ordine}}
        anni_titolo = {}
        for r in x.itertuples():
            anni_titolo.setdefault(r.titolo, set()).add(pd.Timestamp(r.data).year)
        per_anno = {(f"{min(a)}–{max(a)}" if len(a) > 1 else str(min(a))): t for t, a in anni_titolo.items()}
        predefinito = f.get("lotto_predefinito") if f.get("lotto_predefinito") in lotti else next(iter(lotti))
        nota = NOTA_CONSIP if centrale == "Consip" else NOTA_LISTINO_GAS if unita == "€/Smc" else NOTA_LISTINO
        out.append({"id": serie, "centrale": centrale, "decimali": dec, "titolo": f.get("nome") or NOMI_CENTRALI.get(centrale, centrale),
                    "unita": unita,
                    "fonte": f"{centrale}, " + ("listini" if centrale != "Consip" else "corrispettivi")
                    + " della convenzione " + "; ".join(f"{t} ({a})" for a, t in sorted(per_anno.items())),
                    "licenza": None, "nota": nota,
                    "lotti": lotti, "lotto_predefinito": predefinito, "dettagli": {}})
    # prima Intercent-ER, poi Consip (ordine della pagina e della newsletter)
    return sorted(out, key=lambda i: (0 if i["id"].startswith("intercenter") else 1, i["id"]))


FILE_PFOR = Path(__file__).parent / "dati" / "pfor_storico.csv"
PCS_GJ_SMC = 0.03852          # come pfor.py: €/Smc ÷ 0,03852 × 3,6 = €/MWh


def pfor_storico(file: Path | None = None) -> dict[tuple[int, int], float]:
    """Valori trimestrali del PFOR,t forniti da Paolo l'11/11/2026 (anno;trimestre;pfor_eur_smc, dal 2015), in €/MWh.
    Il file sta in mercati_energia/dati/, fuori dal repository come gli altri dati di terzi; manca → nessun valore."""
    f = Path(file or FILE_PFOR)
    if not f.exists():
        return {}
    df = pd.read_csv(f, sep=";", dtype=str)
    out = {}
    for r in df.itertuples():
        try:
            out[(int(r.anno), int(r.trimestre))] = float(str(r.pfor_eur_smc).replace(",", ".")) / PCS_GJ_SMC * 3.6
        except ValueError:
            continue
    return out


def _gas(cartella: Path, anni: tuple[int, int], file_pfor: Path | None = None) -> list[dict]:
    out = []
    im = indici.leggi(cartella)
    psv = im[im.indice == "PSV_DA"] if not im.empty else im
    if len(psv):
        s = {}
        for r in psv.itertuples():
            p = pd.Period(r.mese, "M")
            if p.year in anni:
                _metti(s, p.year, p.month, r.valore, DEC_GAS)
        if s:
            out.append({"id": "psv-da-arera", "titolo": "PSV day-ahead, media mensile (ARERA)", "unita": "€/MWh",
                        "fonte": "ARERA – CMEM,m, servizio di tutela della vulnerabilità", "licenza": LICENZA_ARERA,
                        "nota": NOTA_PSV, "decimali": DEC_GAS, "lotti": {"": {"nome": "", "varianti": {"": s}}},
                        "lotto_predefinito": "", "dettagli": {}})
    try:
        from . import pfor
        pf = pfor.calcola(cartella, dal=f"{anni[0]}Q1", al=f"{anni[1]}Q4")
    except Exception:  # noqa: BLE001 - senza PFOR la pagina mostra gli altri indici
        pf = pd.DataFrame()
    s, det = {}, {}
    storico = pfor_storico(file_pfor)
    for (anno, tr), v in storico.items():          # (11/11/2026) valori trimestrali di Paolo: hanno la precedenza
        if anno in anni:
            for m in range(3 * tr - 2, 3 * tr + 1):
                _metti(s, anno, m, v, DEC_GAS)
                det[f"{anno}-{m:02d}"] = {"trimestre": f"{anno} T{tr}", "metodo": "valore storico", "provvisorio": False}
    for r in pf.itertuples() if len(pf) else []:
        p = pd.Period(r.mese, "M")
        if p.year in anni and (p.year, (p.month - 1) // 3 + 1) not in storico:
            _metti(s, p.year, p.month, r.pfor_eur_mwh, DEC_GAS)
            det[r.mese] = {"trimestre": r.trimestre.replace("Q", " T"), "metodo": "quotazioni trimestrali"
                           if r.metodo == "forward" else "stima dalle quotazioni giornaliere",
                           "provvisorio": bool(r.provvisorio)}
    if s:
        out.append({"id": "pfor", "titolo": "PFOR,t ricostruito da EuGEnio", "unita": "€/MWh",
                    "fonte": "Elaborazione EuGEnio (metodo ARERA, TIVG art. 6.2 c)", "licenza": None,
                    "nota": NOTA_PFOR, "decimali": DEC_GAS, "lotti": {"": {"nome": "", "varianti": {"": s}}},
                    "lotto_predefinito": "", "dettagli": det})
    return out


def costruisci(cartella: Path, cartella_convenzioni: Path | None = None, oggi: dt.date | None = None,
               file_pfor: Path | None = None) -> dict:
    oggi = oggi or dt.date.today()
    anni = _anni(oggi)
    li = _listini(Path(cartella), cartella_convenzioni, anni)
    return {"aggiornato": oggi.isoformat(), "anni": list(anni),
            "sezioni": [{"id": "elettricita", "titolo": "Energia elettrica",
                         "indici": [i for i in li if i["unita"] != "€/Smc"]},
                        {"id": "gas", "titolo": "Gas naturale",
                         "indici": [i for i in li if i["unita"] == "€/Smc"] + _gas(Path(cartella), anni, file_pfor)}],
            "in_attesa": []}


def scrivi(cartella: Path, cartella_convenzioni: Path | None, uscita: Path, oggi: dt.date | None = None) -> dict:
    """Scrive il JSON in modo atomico (file temporaneo, poi rinomina)."""
    dati = costruisci(cartella, cartella_convenzioni, oggi)
    uscita = Path(uscita)
    uscita.parent.mkdir(parents=True, exist_ok=True)
    tmp = uscita.with_suffix(".tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(uscita)
    return dati
