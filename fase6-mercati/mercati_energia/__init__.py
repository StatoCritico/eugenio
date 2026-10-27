"""Dati di mercato dell'energia e indicatori economici per il progetto.

Aggiornamento notturno:
  * GME (API ufficiale, credenziali personali gratuite): MGP prezzi zonali e PUN Index GME
    (quartorari dal 1/10/2025), volumi MGP, MGP-GAS (prezzo del gas al PSV), indice IGI;
  * EEX: TTF Neutral Gas Price giornaliero (file pubblico degli ultimi 60 giorni, accumulato).
Su richiesta:
  * ISTAT (SDMX): FOI, NIC e altri indici configurabili;
  * Eurostat: prezzi di elettricità e gas per i clienti non domestici per fascia di consumo (PMI).
Più: indici mensili derivati (PUN per fasce F1/F2/F3, medie mensili PSV/IGI/TTF), import di indici
da CSV (es. PSV day-ahead ICIS da fattura o comunicati ARERA) e calcolo dei prezzi delle
convenzioni regionali (Intercent-ER, Consorzio Energia Toscana, ...).
"""
__version__ = "1.0.0"
