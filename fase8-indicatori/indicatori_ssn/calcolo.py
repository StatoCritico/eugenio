"""Dalle righe del CE, dalle tabelle di ReportER e dalla popolazione ISTAT agli indicatori e ai file del sito.

Unità di confronto
  ente          il conto economico della singola azienda (codice ente del CE)
  regione       il conto economico consolidato regionale (codice 999), senza gli scambi tra aziende
  Italia        la somma dei 21 consolidati di regioni e province autonome

Indicatori (spesa = BA1610 + BA1660 + BA1670, oppure una sola componente)
  leva          valore della produzione (AZ9999) / spesa                 volte
  incidenza     spesa / valore della produzione                         %
  peso          spesa / costi della produzione (BZ9999)                  %
  per_giornata  spesa / giornate di degenza ordinaria, ospedali pubblici €   (solo Emilia-Romagna)
  per_posto     spesa / posti letto pubblici al 31/12                    €   (solo Emilia-Romagna)
  per_cittadino spesa / residenti al 31/12                               €   (AUSL ER: SISEPS; regioni, Italia: ISTAT)
"""
from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict

from . import costanti as K

log = logging.getLogger("indicatori_ssn")

COMPONENTI = {"totale": K.COMPONENTI, "riscaldamento": ["BA1610"], "elettricita": ["BA1660"], "altre": ["BA1670"]}
NOMI_COMPONENTI = {"totale": "Totale energia e utenze", "riscaldamento": "Riscaldamento (BA1610)",
                   "elettricita": "Energia elettrica (BA1660)", "altre": "Altre utenze, gas e acqua (BA1670)"}


SIGLE = {"ASL", "AUSL", "USL", "ULSS", "ASP", "ASST", "ATS", "AO", "AOU", "AOUP", "IRCCS", "ASUR", "AST", "ASM",
         "ASREM", "ASUGI", "ASUFC", "ASFO", "ARCS", "ARES", "AREUS", "AREU", "ATS", "INRCA", "ISPO", "ISPRO", "IOR",
         "ESTAR", "ARNAS", "ASLTO", "SSR", "SSN", "GSA", "ASSL", "AUSL-IRCCS", "AOR", "ASO", "ISMETT", "IRST", "CRO",
         "ARPA", "AREAS", "ATS-ASSL", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII"}
PICCOLE = {"di", "del", "della", "dello", "dei", "degli", "delle", "e", "ed", "la", "lo", "il", "le", "gli", "i",
           "a", "al", "alla", "da", "dal", "dalla", "in", "per", "con", "su", "sul", "sulla", "d", "l",
           "dell", "nell", "all", "dall", "sull"}


def nome_leggibile(nome: str) -> str:
    """'AZIENDA USL DELLA ROMAGNA' → 'Azienda USL della Romagna'. Sigle maiuscole, preposizioni minuscole,
    il resto con l'iniziale maiuscola; i nomi già scritti in minuscolo restano come sono."""
    s = " ".join(str(nome or "").split())
    if not s or s != s.upper():
        return s
    out = []
    import re
    parti = re.split(r"(\s+|[-'’/().,])", s)
    for i, parola in enumerate(parti):
        if not parola or re.fullmatch(r"\s+|[-'’/().,]", parola):
            out.append(parola)
            continue
        segue = parti[i + 1] if i + 1 < len(parti) else ""
        if parola == "N" and out:
            out.append("n")
        elif len(parola) == 1 and segue == ".":                      # sigle puntate: A.S.L.
            out.append(parola)
        elif parola in SIGLE or (re.search(r"\d", parola) and len(parola) <= 4) or (len(parola) <= 4 and not re.search(r"[AEIOU]", parola) and parola.isalpha()):
            out.append(parola)
        elif parola.lower() in PICCOLE and out and "".join(out).strip():
            out.append(parola.lower())
        else:
            out.append(parola[:1] + parola[1:].lower())
    return "".join(out)


def _arrotonda(x):
    if x is None:
        return None
    r = round(x, 2)
    return int(r) if float(r).is_integer() else r


def _tipo_preferito(tipi: set[str]) -> str:
    """Se un dataset avesse più tipi di rilevazione, vale il consuntivo, poi il IV trimestre."""
    for chiave in ("CONSUNTIVO", "IV", "QUARTO"):
        for t in sorted(tipi):
            if chiave in t.upper():
                return t
    return sorted(tipi)[-1]


def raccogli_ce(righe_per_anno: dict[int, list[dict]]) -> dict:
    """{(regione, ente): {"nomi": {anno: nome}, "valori": {anno: {voce: importo}}, "tipo": {anno: tipo}}}"""
    unita: dict = {}
    for anno, righe in righe_per_anno.items():
        tipi = {r["tipo_rilevazione"] for r in righe if r.get("tipo_rilevazione")}
        scelto = _tipo_preferito(tipi) if len(tipi) > 1 else None
        if scelto:
            log.warning("CE %d: tipi di rilevazione %s, uso %s", anno, sorted(tipi), scelto)
        for r in righe:
            if scelto and r.get("tipo_rilevazione") != scelto:
                continue
            if r["importo"] == "":
                continue
            k = (r["cod_regione"], r["cod_ente"])
            u = unita.setdefault(k, {"nomi": {}, "valori": {}, "tipo": {}, "regione": {}})
            u["nomi"][anno] = r["ente"]
            u["regione"][anno] = r["regione"]
            u["tipo"][anno] = r.get("tipo_rilevazione", "")
            v = u["valori"].setdefault(anno, {})
            v[r["voce"]] = v.get(r["voce"], 0.0) + float(r["importo"])
    return unita


def serie(valori: dict[int, dict], voce: str, anni: list[int]) -> list:
    return [_arrotonda(valori.get(a, {}).get(voce)) if a in valori and voce in valori[a] else None for a in anni]


def unita_json(cod, reg, nome, valori, anni, *, gg=None, dh=None, pl=None, pop=None, fonte_pop=None,
               nomi=None, extra=None) -> dict:
    u = {"cod": cod, "reg": reg, "nome": nome,
         "v": {voce: serie(valori, voce, anni) for voce in K.VOCI_USCITA}}
    for chiave, s in (("gg", gg), ("dh", dh), ("pl", pl), ("pop", pop)):
        if s and any(x is not None for x in s):
            u[chiave] = [_arrotonda(x) for x in s]
    if fonte_pop and "pop" in u:
        u["fonte_pop"] = fonte_pop
    if nomi:
        distinti = []
        for a in anni:
            if a in nomi and (not distinti or distinti[-1][2] != nomi[a]):
                distinti.append([a, a, nomi[a]])
            elif a in nomi:
                distinti[-1][1] = a
        if len(distinti) > 1:
            u["nomi"] = distinti
    if extra:
        u.update(extra)
    return u


def _dalla_mappa(m: dict[int, dict[str, float]], cod: str, anni: list[int]) -> list:
    return [(m.get(a) or {}).get(cod) for a in anni]


def costruisci(ce: dict, rep: dict | None, pop_istat: dict | None, anni: list[int] | None = None,
               oggi: dt.date | None = None) -> dict:
    """Restituisce {"indice": {...}, "regioni": {"08": {...}, ...}} pronti per i file JSON."""
    anni = anni or K.ANNI
    oggi = oggi or dt.date.today()
    rep_d = (rep or {}).get("dati", {})
    istat_d = (pop_istat or {}).get("dati", {})
    consolidati, per_regione = {}, defaultdict(list)
    for (reg, ente), u in sorted(ce.items()):
        if reg not in K.REGIONI_CE:
            log.warning("codice regione sconosciuto %s (ente %s), saltato", reg, ente)
            continue
        mappa, nuts, nome_reg = K.REGIONI_CE[reg]
        ultimo = max(u["nomi"])
        nome = nome_leggibile(u["nomi"][ultimo])
        if ente == K.GSA:
            continue
        kw = {}
        if reg == K.REGIONE_REPORTER and rep_d:
            kw = {"gg": _dalla_mappa(rep_d.get("giornate", {}), ente, anni),
                  "dh": _dalla_mappa(rep_d.get("accessi_dh", {}), ente, anni),
                  "pl": _dalla_mappa(rep_d.get("posti_letto", {}), ente, anni),
                  "pop": _dalla_mappa(rep_d.get("popolazione", {}), ente, anni), "fonte_pop": "siseps"}
        if ente == K.CONSOLIDATO:
            if not kw:
                kw = {"pop": [(istat_d.get(nuts) or {}).get(a) for a in anni], "fonte_pop": "istat"}
            else:
                kw["pop_istat"] = [(istat_d.get(nuts) or {}).get(a) for a in anni]
            pi = kw.pop("pop_istat", None)
            cons = unita_json(ente, reg, f"{nome_reg} – consolidato {'provinciale' if nome_reg.startswith('Provincia') else 'regionale'}", u["valori"], anni,
                              extra={"pop_istat": [_arrotonda(x) for x in pi]} if pi and any(pi) else None, **kw)
            consolidati[reg] = cons
        else:
            per_regione[reg].append(unita_json(ente, reg, nome, u["valori"], anni,
                                               nomi={a: nome_leggibile(n) for a, n in u["nomi"].items()}, **kw,
                                               extra={"anni_presenti": [min(u["valori"]), max(u["valori"])]}))
    # Italia: somma dei consolidati
    tot = {a: defaultdict(float) for a in anni}
    n_reg = [0] * len(anni)
    for reg, cons in consolidati.items():
        for i, a in enumerate(anni):
            if cons["v"]["AZ9999"][i] is None:
                continue
            n_reg[i] += 1
            for voce in K.VOCI_USCITA:
                x = cons["v"][voce][i]
                if x is not None:
                    tot[a][voce] += x
    valori_it = {a: dict(tot[a]) for a in anni if n_reg[anni.index(a)]}
    # se in un anno manca il consolidato di qualche regione (Calabria 2021), la popolazione dell'Italia è quella
    # delle sole regioni comprese, così la spesa per cittadino resta coerente
    mancanti, pop_it = [], []
    for i, a in enumerate(anni):
        via = [reg for reg in K.REGIONI_CE if reg not in consolidati or consolidati[reg]["v"]["AZ9999"][i] is None]
        mancanti.append([K.REGIONI_CE[r][2] for r in via] if n_reg[i] else [])
        p = (istat_d.get("IT") or {}).get(a)
        if p is not None and n_reg[i]:
            togli = [(istat_d.get(K.REGIONI_CE[r][1]) or {}).get(a) for r in via]
            p = None if any(x is None for x in togli) else p - sum(togli)
        pop_it.append(p)
    italia = unita_json("IT", "IT", "Italia – somma dei consolidati regionali", valori_it, anni,
                        pop=pop_it, fonte_pop="istat",
                        extra={"n_regioni": n_reg, "regioni_mancanti": mancanti})
    incompleti = [a for a, n in zip(anni, n_reg) if 0 < n < len(K.REGIONI_CE)]
    if incompleti:
        log.warning("Italia: consolidati mancanti negli anni %s", incompleti)

    regioni_out, elenco = {}, []
    for mappa in sorted(K.NOMI_REGIONI_MAPPA):
        ambiti = []
        for reg, (m, _, nome_reg) in K.REGIONI_CE.items():
            if m != mappa:
                continue
            ambiti.append({"ce": reg, "nome": nome_reg,
                           "enti": sorted(per_regione.get(reg, []), key=lambda e: e["cod"])})
        regioni_out[mappa] = {"mappa": mappa, "nome": K.NOMI_REGIONI_MAPPA[mappa], "anni": anni, "ambiti": ambiti,
                              "licenza": K.LICENZA, "citazione": K.citazione(oggi)}
        elenco.append({"mappa": mappa, "nome": K.NOMI_REGIONI_MAPPA[mappa], "ce": [a["ce"] for a in ambiti],
                       "enti": sum(len(a["enti"]) for a in ambiti), "file": f"{mappa}.json"})
    indice = {
        "versione": 1, "aggiornato": oggi.isoformat(), "anni": anni, "provvisori": sorted(K.PROVVISORI & set(anni)),
        "voci": {v: K.VOCI[v] for v in K.VOCI_USCITA}, "componenti": NOMI_COMPONENTI,
        "fonti": K.FONTI, "elaborazione": K.ELABORAZIONE, "licenza": K.LICENZA, "citazione": K.citazione(oggi),
        "serie_popolazione": {str(a): s for a, s in sorted(((pop_istat or {}).get("serie") or {}).items())},
        "reporter_aggiornato": (rep or {}).get("aggiornato", {}),
        "regioni": elenco, "italia": italia, "consolidati": consolidati,
        "anni_incompleti_italia": incompleti,
    }
    return {"indice": indice, "regioni": regioni_out}


# ------------------------------------------------------------------------------------------------ indicatori
def _div(a, b):
    return None if a is None or b in (None, 0) else a / b


def spesa(u: dict, i: int, componente: str = "totale"):
    vals = [u["v"][v][i] for v in COMPONENTI[componente]]
    if all(x is None for x in vals):
        return None
    return sum(x or 0 for x in vals)


def indicatori(u: dict, i: int, componente: str = "totale") -> dict:
    s = spesa(u, i, componente)
    az, bz = u["v"]["AZ9999"][i], u["v"]["BZ9999"][i]
    g = (u.get("gg") or [None] * (i + 1))[i]
    p = (u.get("pl") or [None] * (i + 1))[i]
    c = (u.get("pop") or [None] * (i + 1))[i]
    return {"spesa": s, "leva": _div(az, s), "incidenza": _div(s, az), "peso": _div(s, bz),
            "per_giornata": _div(s, g), "per_posto": _div(s, p), "per_cittadino": _div(s, c)}
