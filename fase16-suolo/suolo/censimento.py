"""SAU e superficie agricola non utilizzata dal 7° Censimento generale dell'agricoltura (ISTAT, 2020; SDMX
DF_DCAT_CENSAGRIC2020_SURF_ALL: ARU = superficie agricola utilizzata, AA_UNUT = superficie agricola non utilizzata, ha),
per comune, sommate per le province e le regioni della mappa del sito (ISTAT 2026).

I codici comunali del censimento sono quelli del 2020: coincidono con i codici delle mappe del sito, che per la Sardegna
hanno ancora i codici vecchi (090, 091, 092, 095, 111); attraverso la mappa ogni comune va nella sua provincia del 2026
(per la Sardegna le nuove province 112–119). I comuni del 2020 che non sono più nella mappa (fusioni) vanno nella
provincia indicata dalle prime tre cifre del codice, se esiste ancora; altrimenti finiscono nelle note.
Attenzione (documento di ricerca del 22/11/2026): la somma per comune (12,43 milioni di ha nella prima lettura) è un po'
più bassa del totale nazionale del censimento (12,54): ISTAT attribuisce la superficie al comune del centro aziendale.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


def sau(csv_path: Path, mappa: dict, provincia_di: dict) -> dict:
    """{"province": {cod3: [sau, non_utilizzata]}, "regioni": {cod2: [...]}, "italia": [...], "nazionale": [...] | None,
        "note": [...]}; `mappa` è mappa.carica() (province, regioni); `provincia_di` = {codice comunale della mappa: codice
    della provincia 2026} (costruisci.py lo ricava dall'elenco ISPRA: nelle mappe i comuni sardi hanno ancora le sigle
    delle province vecchie, SU, SS…)."""
    valori: dict = defaultdict(lambda: [0.0, 0.0])
    nazionale = None
    with Path(csv_path).open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            k = {"ARU": 0, "AA_UNUT": 1}.get(r.get("DATA_TYPE"))
            if k is None or not r.get("OBS_VALUE"):
                continue
            area = r["REF_AREA"]
            if area == "IT":
                nazionale = nazionale or [0.0, 0.0]
                nazionale[k] = float(r["OBS_VALUE"])
            elif len(area) == 6 and area.isdigit():
                valori[area][k] += float(r["OBS_VALUE"])
    province: dict = defaultdict(lambda: [0.0, 0.0])
    fuori = []
    for pc, v in valori.items():
        cod = provincia_di.get(pc) or (pc[:3] if pc[:3] in mappa["province"] else None)
        if not cod:
            fuori.append(pc)
            continue
        province[cod] = [a + b for a, b in zip(province[cod], v)]
    regioni: dict = defaultdict(lambda: [0.0, 0.0])
    for cod, v in province.items():
        r = mappa["province"][cod]["regione"]
        regioni[r] = [a + b for a, b in zip(regioni[r], v)]
    italia = [sum(v[i] for v in regioni.values()) for i in range(2)]
    note = []
    if fuori:
        persi = sum(valori[p][0] for p in fuori)
        note.append(f"Censimento 2020: {len(fuori)} comuni senza provincia nella mappa ({persi:.0f} ha di SAU non assegnati): "
                    + ", ".join(sorted(fuori)[:20]))
    r1 = lambda v: [round(x, 1) for x in v]
    return {"province": {k: r1(v) for k, v in sorted(province.items())}, "regioni": {k: r1(v) for k, v in sorted(regioni.items())},
            "italia": r1(italia), "nazionale": r1(nazionale) if nazionale else None, "note": note}
