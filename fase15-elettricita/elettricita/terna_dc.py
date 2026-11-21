"""Statistiche annuali di Terna dal Download Center di dati.terna.it (20/11/2026).

È la stessa interfaccia che usa la pagina https://dati.terna.it/download-center (POST JSON su
/api/sitecore/dati/downloadcenter/recordsv2, nessuna chiave): non consuma la quota dell'API ufficiale
(developer.terna.it, 300 chiamate al giorno). Si usa per gli archivi annuali consolidati (dal 2000), che cambiano una
volta l'anno; le serie quartorarie le legge invece il worker con l'API ufficiale.

Una richiesta al secondo; gli anni con più di 50 000 righe (Market dal 2019) si leggono a pagine (pageIndex 0, 1, 2…)
finché le righe arrivano al totale dichiarato (Count). Ogni anno in <raw>/<dataset>_<anno>.json con le colonne di Terna:
{"Columns": {...}, "Count": n, "Data": [[...], ...]}.

  python -m elettricita.terna_dc <cartella_raw> [--ultimi N] [--dataset A,B]
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.request
from pathlib import Path

log = logging.getLogger("elettricita.terna_dc")

URL = "https://dati.terna.it/api/sitecore/dati/downloadcenter/recordsv2"
AGENTE = "EuGEnio (https://eugenio.statocritico.it) - statistiche annuali"

# dataset del Download Center → colonna d'ordinamento richiesta dal servizio
DATASET = {
    # capacità (potenza efficiente, MW), per regione e provincia, lorda e netta
    "GenerationPlants": "Anno",            # per fonte: Eolico, Fotovoltaico, Geotermoelettrico, Idrico, Termoelettrico
    "CapacityRenewableSources": "Anno",    # rinnovabili: Bioenergie, Eolico, Fotovoltaico, Geotermoelettrico, Idrico
    "CapacityThermal": "Anno",             # termoelettrica per categoria e sottocategoria
    # produzione (GWh), per regione e provincia
    "ElectricityBySource": "Anno",         # per fonte, lorda e netta
    "ProductionRenewableSources": "Anno",  # rinnovabili, con le bioenergie
    # consumi (GWh) per settore, regione e provincia
    "ElectricalEnergy": "Consumo (GWh)",
    # richiesta per regione (dal 2005)
    "ConsumptionBySource": "Anno",         # copertura della domanda per fonte
    "ElectricityByType": "Anno",           # rinnovabili, tradizionali, saldo import/export
    # (20/11/2026, richiesta di Paolo) calore della cogenerazione, produzione termoelettrica per tecnologia, autoconsumo
    "ThermalHeat": "Anno",                 # calore prodotto dagli impianti cogenerativi [GWh], per tipo di impianto
    "ProductionThermal": "Anno",           # produzione termoelettrica per categoria (cogenerativa o no) e sottocategoria
    "GrossVsCO2Emissions": "Anno",         # produzione lorda ed emissioni di CO2 per combustibile e regione
    "Market": "Consumo (GWh)",             # consumi per mercato: autoconsumo, mercato libero, mercato tutelato
    # consumi per attività economica (Ateco) e classe, per regione e provincia
    "IndustrialSector": "Consumo (GWh)",
    "ServiceSector": "Consumo (GWh)",
    "Total": "Consumo (GWh)",
}


def _post(corpo: dict, tentativi: int = 3) -> dict:
    dati = json.dumps(corpo).encode()
    for i in range(tentativi):
        try:
            req = urllib.request.Request(URL, data=dati, headers={"Content-Type": "application/json", "User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception:
            if i == tentativi - 1:
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError("irraggiungibile")


def anni_disponibili(dataset: str) -> list[int]:
    d = _post({"filterDataset": dataset, "orderByColumn": DATASET[dataset], "orderByDir": "desc", "pageIndex": "0",
               "pageSize": "1", "db": "dati"})
    return sorted(int(a) for a in d.get("Years") or [])


PAGINA = 50000  # righe per richiesta (il massimo che il servizio restituisce)


def scarica_anno(dataset: str, anno: int, pausa: float = 1.0) -> dict:
    """Tutte le righe di un anno, una pagina alla volta (pageIndex 0, 1, 2…), una richiesta ogni `pausa` secondi,
    finché le righe ricevute arrivano a `Count`; alla fine controlla che siano esattamente `Count`."""
    righe: list = []
    colonne: dict = {}
    totale = None
    pagina = 0
    while True:
        if pagina:
            time.sleep(pausa)
        d = _post({"filterDataset": dataset, "filterYear": str(anno), "orderByColumn": DATASET[dataset],
                   "orderByDir": "desc", "pageIndex": str(pagina), "pageSize": str(PAGINA), "db": "dati"})
        colonne = colonne or d.get("Columns") or {}
        if totale is None:
            totale = int(d.get("Count") or 0)
        dati = d.get("Data") or []
        righe.extend(dati)
        pagina += 1
        if len(righe) >= totale or not dati:
            break
    if len(righe) != totale:
        raise RuntimeError(f"{dataset} {anno}: {totale} righe, ricevute {len(righe)} in {pagina} pagine")
    return {"Columns": colonne, "Count": totale, "Data": righe}


def scarica(raw: Path, dataset: list[str] | None = None, ultimi: int | None = None, pausa: float = 1.0) -> dict:
    """Scarica gli anni che mancano in `raw` e, con `ultimi`, riscarica sempre gli ultimi N anni disponibili (i dati
    provvisori diventano consolidati con l'annuario). Restituisce {dataset: [anni scaricati]}."""
    raw.mkdir(parents=True, exist_ok=True)
    fatti: dict[str, list[int]] = {}
    for ds in dataset or list(DATASET):
        anni = anni_disponibili(ds)
        time.sleep(pausa)
        rifare = set(anni[-ultimi:]) if ultimi else set()
        for a in anni:
            f = raw / f"{ds}_{a}.json"
            if f.exists() and a not in rifare:
                continue
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(scarica_anno(ds, a, pausa), ensure_ascii=False), encoding="utf-8")
            tmp.replace(f)
            fatti.setdefault(ds, []).append(a)
            time.sleep(pausa)
        log.info("Terna %s: anni %s–%s, scaricati %s", ds, anni[0] if anni else "-", anni[-1] if anni else "-",
                 fatti.get(ds, []))
    return fatti


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("raw", type=Path)
    p.add_argument("--ultimi", type=int, default=None)
    p.add_argument("--dataset", default=None)
    a = p.parse_args()
    scarica(a.raw, a.dataset.split(",") if a.dataset else None, a.ultimi)


if __name__ == "__main__":
    main()
