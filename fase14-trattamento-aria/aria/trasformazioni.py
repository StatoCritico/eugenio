"""Pagina «Trattamento aria › Trasformazioni (UTA)» (14/11/2026): gemello Python della parte pura di
fase5-sito/sito/aria_trasformazioni.js.

- ``stima_stagionale``: la stima stagionale del foglio psicro_UTA.xlsx (UTA!B77:H85), solo calore sensibile dell'aria
  esterna di rinnovo da T esterna a 20 °C con i gradi giorno base 20 °C;
- ``celle_excel``: le celle gialle del foglio compilate da una configurazione della pagina (stesso ordine del JS);
- ``calcola_configurazione``: estate, inverno e stima come la pagina.

Le sequenze si calcolano con ``aria.psicro.sequenza`` (già in parità col JS e col foglio). Test:
tests/test_trasformazioni.py (parità con il JS in node e con il foglio ricalcolato da LibreOffice, se c'è)."""
from __future__ import annotations

import math
import re

from . import psicro as P

RIGHE_FOGLIO = 6
_MIGLIAIA = re.compile(r"^[-+]?\d{1,3}(\.\d{3})+(,\d*)?$")
_NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def numero(v) -> float:
    """numero scritto all'italiana ("1.234,5", "0,7") o all'inglese ("0.7"); NaN se non è un numero (come il JS)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if v is None:
        return math.nan
    s = re.sub(r"\s", "", str(v)).replace("−", "-")
    if not s:
        return math.nan
    if _MIGLIAIA.match(s):
        s = s.replace(".", "")
    s = s.replace(",", ".", 1)
    return float(s) if _NUM.match(s) else math.nan


def stima_stagionale(inv: dict, est: dict, righe_inverno, d: dict) -> dict:
    """inv, est = risultati di psicro.sequenza; righe_inverno = [[tipo, P1, P2, P3], …];
    d = {gg, ore, rendimento, pci, oreEq, eer}. εs = P1 della prima riga «Recuperatore di calore» (0 se non è un numero)."""
    rec = next((r for r in (righe_inverno or []) if P.codice_tipo(r[0]) == 3), None)
    lp = P.leggi_parametro(rec[1]) if rec else None
    eps = lp.v if lp and lp.ha else 0.0
    m_oa, cp = inv["mOA"], inv["cpA"]
    fabbisogno = m_oa * cp * d["gg"] * d["ore"]
    recuperata = fabbisogno * eps
    netto = fabbisogno - recuperata
    combustibile = netto / (d["rendimento"] * d["pci"]) if d["rendimento"] * d["pci"] > 0 else 0.0
    frigo = est["riepilogo"]["frigoTotale"] * d["oreEq"]
    elettrica = frigo / d["eer"] if d["eer"] > 0 else 0.0
    return {"mOA": m_oa, "eps": eps, "cp": cp, "fabbisogno": fabbisogno, "recuperata": recuperata, "netto": netto,
            "combustibile": combustibile, "frigo": frigo, "elettrica": elettrica}


def _testo_par(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v).replace(".", ",")
    return str(v)


def _par(v):
    s = _testo_par(v).strip()
    if not s:
        return None
    if s.upper() == "AUTO":
        return "AUTO"
    n = numero(s)
    return n if math.isfinite(n) else s


def celle_excel(c: dict) -> list:
    """[[cella, valore]] delle celle gialle del foglio UTA (prime 6 righe di ogni sequenza), come celleExcel del JS."""
    pi = c.get("pressioneImposta")
    rif = c.get("riferimento", 0)
    out = [["D6", c["quota"]], ["D8", pi if isinstance(pi, (int, float)) and math.isfinite(pi) else None], ["D10", c["V"]],
           ["D11", c["quotaEsterna"]], ["D14", P.RIF_PORTATA[rif] if 0 <= rif < len(P.RIF_PORTATA) else P.RIF_PORTATA[0]]]
    for k, r0, s0 in (("estate", 18, 28), ("inverno", 48, 58)):
        s = c[k]
        out += [[f"D{r0}", s["esterno"]["t"]], [f"D{r0 + 1}", s["esterno"]["ur"]], [f"D{r0 + 2}", s["ambiente"]["t"]],
                [f"D{r0 + 3}", s["ambiente"]["ur"]], [f"D{r0 + 4}", s["Qs"]], [f"D{r0 + 5}", s["Ql"]]]
        for i in range(RIGHE_FOGLIO):
            r = s["righe"][i] if i < len(s["righe"]) else ["Nessuna", "", "", ""]
            out += [[f"C{s0 + i}", P.TIPI[P.codice_tipo(r[0]) - 1]], [f"D{s0 + i}", _par(r[1])], [f"E{s0 + i}", _par(r[2])],
                    [f"F{s0 + i}", _par(r[3])]]
    st = c["stima"]
    out += [["D78", st["gg"]], ["D79", st["ore"]], ["D80", st["rendimento"]], ["D81", st["pci"]], ["D82", st["oreEq"]], ["D83", st["eer"]]]
    return out


def calcola_configurazione(c: dict) -> dict:
    """come calcolaConfigurazione del JS: {estate, inverno, stima}."""
    def opz(k):
        return {"p": c["p"], "V": c["V"], "quotaEsterna": c["quotaEsterna"], "riferimento": c.get("riferimento", 0), "stagione": k,
                "esterno": c[k]["esterno"], "ambiente": c[k]["ambiente"], "Qs": c[k]["Qs"], "Ql": c[k]["Ql"], "righe": c[k]["righe"]}
    est, inv = P.sequenza(opz("estate")), P.sequenza(opz("inverno"))
    return {"estate": est, "inverno": inv, "stima": stima_stagionale(inv, est, c["inverno"]["righe"], c["stima"])}
