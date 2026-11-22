"""Classi della Carta nazionale del consumo di suolo (ISPRA, legenda v8) e gruppi usati dalla pagina «Suolo e aree agricole».

Classi di consumo (3° livello): 111 edifici, 112 strade pavimentate, 113 sede ferroviaria, 114 aeroporti, 115 porti,
116 altre aree impermeabili non edificate (piazzali, parcheggi…), 117 serre permanenti pavimentate, 118 discariche,
121 strade non pavimentate, 122 cantieri e altre aree in terra battuta, 123 aree estrattive non rinaturalizzate,
124 cave in falda, 125 fotovoltaico a terra ad alta densità, 126 altre coperture artificiali.
Nell'Excel degli indicatori sono le colonne csuolox111…csuolox126 (incremento rispetto al periodo precedente).
"""
from __future__ import annotations

# (id, nome, colore, classi)
GRUPPI = [
    ("edifici", "Edifici", "#c0392b", [111]),
    ("strade", "Strade e infrastrutture", "#6c6f7d", [112, 113, 114, 115, 121]),
    ("piazzali", "Piazzali e aree produttive", "#e08a3c", [116]),
    ("cantieri", "Cantieri", "#c9a227", [122]),
    ("cave", "Cave e discariche", "#8b6b4a", [118, 123, 124]),
    ("fv", "Fotovoltaico a terra", "#f7cb15", [125]),
    ("altro", "Altro (serre pavimentate, altre coperture)", "#9b7fc0", [117, 126]),
]
CLASSI = [c for _, _, _, cl in GRUPPI for c in cl]
GRUPPO_DI = {c: g for g, _, _, cl in GRUPPI for c in cl}

# Carta di uso del suolo ISPRA 2023 (10 m, Uso_del_suolo_2023.tif): usi agricoli
USI_AGRICOLI = {11: "Seminativi", 12: "Foraggere", 13: "Colture permanenti", 14: "Aree agroforestali", 16: "Altri usi agricoli"}
USI_ALTRI = {2: "Uso forestale", 3: "Cave e miniere", 4: "Urbano e aree assimilate", 5: "Usi d'acqua", 61: "Zone umide",
             62: "Altri usi non economici"}


def classe_nuovo_consumo(codice: int) -> int | None:
    """Codice della carta dei cambiamenti → classe di consumo se il pixel è nuovo consumo (da non consumato), altrimenti None.
    I codici a 4 cifre sono «2» (non consumato) seguito dalla classe d'arrivo: 2111…2126 consumo, 2201…2206 coperture
    non conteggiate. I codici a 6 cifre sono passaggi fra classi già consumate (122111 = cantiere → edificio) o ripristini
    (xxx002) e non sono nuovo consumo."""
    if 2000 <= codice < 3000:
        c = codice - 2000
        return c if c in GRUPPO_DI else None
    return None
