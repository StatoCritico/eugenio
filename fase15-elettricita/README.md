# Fase 15 – Statistiche dell'elettricità (Terna)

Modulo `elettricita` per due pagine della sezione Statistiche del sito (sperimentali):

| Modulo | Pagina | Dati di Terna |
|---|---|---|
| `terna_dc.py`, `costruisci.py` | «Produzione e consumi di elettricità» (`elettricita.html`) | statistiche annuali per regione e provincia |
| `carichi.py` | «Carichi elettrici» (`carichi.html`, 20/11/2026) | fabbisogno ogni 15 minuti per zona di mercato, produzione per fonte (Italia) |

**Decisione di Paolo (20/11/2026):** i dati di Terna si caricano sul sito per le elaborazioni ma **non si scaricano**
(nessun CSV, Excel o JSON da scaricare; al più immagini delle elaborazioni). I file costruiti stanno solo sul server:
`fase5-sito/sito/dati/elettricita/` e `fase5-sito/sito/dati/carichi/` sono in `.gitignore`.

Prove: `cd fase15-elettricita && python -m pytest -q` (solo dati inventati, niente rete).

## Carichi elettrici (`elettricita/carichi.py`)

### Fonte: Terna e non il GME

Paolo aveva chiesto la «potenza richiesta ricalcolata dall'energia scambiata in borsa». I dati del **GME** sono però
solo per uso interno e non si mostrano sul sito: la pagina usa il **fabbisogno di Terna** («Fabbisogno Italia»,
dataset `TotalLoad` del Download Center: carico effettivo in MW medi ogni 15 minuti, per zona di mercato e Italia;
comprende perdite e autoconsumi). Il punto unico per cambiare fonte è `FONTE_CARICO` in `carichi.py` (dataset
dell'archivio, colonne, scala, testo della fonte): se arrivasse la licenza del GME basta scrivere nell'archivio un
dataset con le stesse colonne e cambiare lì.

La produzione per fonte di Terna (`ActualGeneration`, `RenewableGeneration`) è **solo nazionale**: il grafico delle
fonti è sempre dell'Italia; con una zona scelta la pagina lo dice (nessuna ripartizione per zona inventata).

### Archivio (ingresso)

Una cartella con un file per dataset e mese: `<archivio>/<Dataset>_<AAAA>-<MM>.json` =
`{"Columns": {nome: tipo, …}, "Data": [[…], …]}`, cioè la risposta del Download Center così com'è.

| Dataset | Colonne usate | Unità |
|---|---|---|
| `TotalLoad` (obbligatorio) | `Date`, `Total Load [MW]`, `Bidding Zone` (Italy, North, Centre-North, Centre-South, South, Calabria, Sicily, Sardinia) | MW |
| `ActualGeneration` | `Date`, `Actual Generation`, `Primary Source` (Thermal, Hydro, Wind, Geothermal, Photovoltaic, Self-consumption) | GW medi |
| `RenewableGeneration` | `Date`, `Renewable Generation`, `Energy Source` (Biomass, Hydro, Wind, Geothermal, Photovoltaic) | GW medi |

`Date`: millisecondi dal 1/1/0001 in ora locale italiana (come il Download Center), oppure ISO `AAAA-MM-GGTHH:MM[:SS]`
in ora locale, oppure ISO con il fuso. Nel giorno del ritorno all'ora solare le 02:00–02:45 compaiono due volte senza
indicazione: la prima occorrenza vale come ora legale, la seconda come solare, e per ogni zona si sceglie poi l'ordine
che fa tornare la somma delle zone con l'Italia (`_ora_doppia`). I dati orari (la generazione fino al 2024) valgono per
i quattro quarti d'ora dell'ora. Una zona sconosciuta ferma la costruzione (configurazione zonale cambiata: aggiornare
`ZONE` e `fase5-sito/costruisci_zone.py`).

Scaricamento (una richiesta al secondo, pagine da 50.000 righe con `pageIndex` se `Count` le supera):

```
python -m elettricita.carichi scarica <archivio> --da 2025-11 [--a 2026-11] [--rifai-ultimo]
```

### File della pagina (uscita)

```
python -m elettricita.carichi costruisci <archivio> <uscita>      # costruisci_carichi(archivio, uscita)
```

- `indice.json`: fonti, data di costruzione, zone (`ITA`, `NORD`, `CNOR`, `CSUD`, `SUD`, `CALA`, `SICI`, `SARD`),
  voci con i colori (gli stessi di `costruisci.py`: termo #8a8f99, bio #f0912a, idro #7cc7e0, geo #d4561c,
  eol #a9c641, fv #f7cb15, saldo #c7a0c0) e i mesi: `inizio` (primo quarto d'ora, UTC = mezzanotte italiana del
  primo del mese), `n` (quarti d'ora con dati: il mese in corso è tagliato all'ultimo), `ora_legale` (`[[indice,
  minuti dall'UTC], …]` a ogni cambio), `passo_carico`, `fonti`, `passo_fonti` (15 o 60), `rinnovabili`.
- `carico_AAAA-MM.json`: `{"mese", "zone": {ITA: [MW interi o null] × n, …}}` (≈ 120 kB al mese).
- `fonti_AAAA-MM.json`: `{"mese", "voci": {termo, bio, idro, geo, eol, fv, saldo: [MW interi o null] × n}}`
  (≈ 100 kB al mese): fv, eol, geo, idro (con i pompaggi), bio dalla produzione rinnovabile (autoconsumi compresi);
  termo = produzione totale con gli autoconsumi meno le rinnovabili (senza `RenewableGeneration`: le rinnovabili di
  `ActualGeneration` e bio = 0); saldo = potenza richiesta dell'Italia − produzione (estero meno pompaggi e accumuli,
  può essere negativo).

La pagina scarica solo i mesi del periodo scelto (12 mesi ≈ 2,6 MB non compressi, molto meno con la compressione del
server).

### Come agganciarlo al worker (lo prepara un'altra sessione: `fase4-server` non è toccato qui)

Una volta al giorno, dopo l'aggiornamento di Terna:

1. `scarica(archivio, mesi_tra(<12 mesi fa o il primo mese da tenere>, <mese corrente>))` per i mesi mancanti, e
   `scarica(archivio, [<mese corrente>], rifai=True)` (anche il mese precedente nei primi giorni del mese);
   `archivio` fuori dal sito (per esempio `/srv/eugenio/archivio/terna_carichi/`).
2. `costruisci_carichi(archivio, <cartella nuova>)` e, se va a buon fine, pubblicazione atomica della cartella in
   `fase5-sito/sito/dati/carichi/` (come `_pubblica` per `dati/elettricita/`).
3. Il server deve comprimere i `.json` (gzip/brotli) e può tenerli in cache per un giorno.

Prova con i dati veri (20/11/2026): 13 mesi (novembre 2025 – 19 novembre 2026), 39 richieste in circa 2 minuti,
costruzione in 5 secondi, nessun quarto d'ora mancante tranne il 14–15 gennaio 2026 (192, assenti anche nei dati di
Terna); somma delle zone = Italia (scarto massimo 2 MW, arrotondamenti).

## Produzione e consumi di elettricità (`terna_dc.py`, `costruisci.py`)

Vedi le docstring dei due moduli e la sezione `metodo.html#elettricita` del sito.
