"""ReportER (SISEPS, Regione Emilia-Romagna): giornate di degenza, posti letto e popolazione per azienda.

Le tabelle si ottengono con POST /stats/report/TABLE e il corpo che usa il portale stesso
(flowId, macroScopeId, scopeId, tabId, activeFilterList). Gli importi arrivano come testo all'italiana
("861.172"; "." = nessun valore).
"""
from __future__ import annotations

import logging

from . import costanti as K
from .rete import FonteNonDisponibile, Rete

log = logging.getLogger("indicatori_ssn")


def numero(testo) -> float | None:
    """'1.124.403' → 1124403; '0,33' → 0.33; '.' o '' → None."""
    if testo is None:
        return None
    if isinstance(testo, (int, float)):
        return float(testo)
    s = str(testo).strip().replace(" ", "")
    if s in ("", ".", "-", "n.d."):
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def corpo(report: dict, anno: int, extra: dict | None = None) -> dict:
    flusso, ambito, sotto, scheda = report["coordinate"]
    filtri = {report["anno"]: str(anno), **report["fissi"], **(extra or {})}
    return {"macroareaId": 1, "flowId": flusso, "macroScopeId": ambito, "scopeId": sotto, "tabId": scheda,
            "representationType": "TABLE",
            "activeFilterList": [{"id": k, "values": [{"value": v}]} for k, v in filtri.items()],
            "saved": False}


def leggi_tabella(risposta: dict, colonna: str | None = None) -> tuple[dict[str, float | None], dict]:
    """Dalla risposta di ReportER: {azienda: valore della colonna} (di norma il TOTALE) e i metadati."""
    if risposta.get("status") != "OK" or not risposta.get("content"):
        raise FonteNonDisponibile(f"ReportER: risposta non valida ({risposta.get('contentType')})")
    c = risposta["content"]
    t = c["content"]["content"][0]
    nomi_col = [x["name"] for x in t["cols"]][1:]          # la prima è l'intestazione delle righe
    if colonna is None:
        i = len(nomi_col) - 1                              # ultima colonna: TOTALE
    else:
        if colonna not in nomi_col:
            raise FonteNonDisponibile(f"ReportER: manca la colonna {colonna!r} ({nomi_col})")
        i = nomi_col.index(colonna)
    valori = {}
    for riga, dati in zip(t["rows"], t["data"]):
        valori[str(riga["name"]).strip()] = numero(dati[i]) if i < len(dati) else None
    meta = c.get("metadata") or {}
    return valori, {"aggiornato": meta.get("lastUpdateDate"), "filtri": meta.get("tabFilterRecap"),
                    "fonte": meta.get("dataSource"), "colonne": nomi_col}


def per_ente(valori: dict[str, float | None]) -> tuple[dict[str, float], list[str]]:
    """Valori per codice ente del CE; le aziende sconosciute (escluso TOTALE) tornano a parte."""
    out, ignote = {}, []
    for nome, v in valori.items():
        if nome.upper() == "TOTALE":
            if v is not None:
                out[K.CONSOLIDATO] = v
            continue
        cod = K.AZIENDE_REPORTER.get(nome.upper())
        if cod is None:
            ignote.append(nome)
            continue
        if v is not None:
            out[cod] = out.get(cod, 0.0) + v
    return out, ignote


def scarica(rete: Rete, anni: list[int]) -> dict:
    """{misura: {anno: {codice_ente: valore}}} più i metadati di ogni tabella.
    misure: giornate (degenza ordinaria), accessi_dh, posti_letto, popolazione."""
    url = f"{K.REPORTER}/report/TABLE"
    dati = {"giornate": {}, "accessi_dh": {}, "posti_letto": {}, "popolazione": {}}
    meta, ignote = {}, set()
    for anno in anni:
        for misura, rep, extra in (
            ("giornate", K.REPORT_GIORNATE, {K.REPORT_GIORNATE["regime"]: "001"}),
            ("accessi_dh", K.REPORT_GIORNATE, {K.REPORT_GIORNATE["regime"]: "002"}),
            ("posti_letto", K.REPORT_POSTI_LETTO, None),
            ("popolazione", K.REPORT_POPOLAZIONE, None),
        ):
            try:
                risposta = rete.json("POST", url, corpo(rep, anno, extra))
                valori, m = leggi_tabella(risposta, "Residenti" if misura == "popolazione" else None)
            except FonteNonDisponibile as e:
                log.warning("ReportER %s %d non disponibile: %s", misura, anno, e)
                continue
            v, ig = per_ente(valori)
            ignote.update(ig)
            dati[misura][anno] = v
            meta.setdefault(misura, {})[anno] = m["aggiornato"]
    if ignote:
        log.warning("ReportER: aziende senza corrispondenza nel CE: %s", sorted(ignote))
    return {"dati": dati, "aggiornato": meta, "aziende_ignote": sorted(ignote)}
