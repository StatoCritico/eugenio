# Dati di terzi della fase 13

Cartella separata, come stabilito per i dati di terzi (RIEPILOGO, «Dati GME quartorari e cogenerazione»): ogni file porta
fonte, licenza e data di lettura. **Nessun dato GME o EEX** (prezzi, MGP-gas, IG Index, MT-Gas, TEE) e **nessun contenuto
GSE** stanno qui.

| File | Fonte | Licenza | Uso |
|---|---|---|---|
| `ispra_fattori_emissione.json` | ISPRA, Rapporto 430/2026 «Settore elettrico: emissioni di CO2 e altri impatti. Edizione 2026», Tabella 1.7 (fattori del settore elettrico, g CO2/kWh, 2015 e 2020–2025, 2025 preliminare) e Tabella 1.4 (gas naturale, t CO2/TJ e t CO2/1000 Sm³, 2022–2024) | CC BY 4.0 (ISPRA); il rapporto: «Riproduzione autorizzata citando la fonte» | pagina Cogenerazione › Emissioni (copia identica in `fase5-sito/sito/dati/ispra_fattori_emissione.json`) |

Citazione da riportare con i risultati: «Fonte dei fattori di emissione: ISPRA, Rapporto 430/2026 (Tabelle 1.4 e 1.7)».
Valori ricopiati a mano dal PDF del rapporto il 05/11/2026 e controllati da un test (`fase5-sito/tests`). Da aggiornare
quando ISPRA pubblica l'edizione successiva (di solito in primavera): nuovo anno in `anni`, nota sui dati preliminari.
