# Aggiornamento del 24/11/2026 (sera) – CER: mappa più ricca e aree non idonee

Ramo `claude/2026-11-24-cer-mappa`, **non ancora in una release** (regola del 20/11: release solo al via di Paolo;
versione del sito ancora `20261124a`, nessuna voce di Novità).

Richiesta di Paolo del 24/11 alle 17:08 (dopo «la pagina funziona»): schede al passaggio del mouse su cabine, edifici e
terreni; da vicino edifici e terreni con i confini; terreni a rombo; scheda dell'edificio con i consumi totali, del
terreno con dati catastali, superficie, FV previsto ed ente, della cabina con nome, codice del GSE e congestione; livelli
«Consumi» e «Potenza FV» (barre verticali in scala); livello delle aree non idonee del portale della Regione, con i
terreni esclusi; verifica della regola della superficie (il 10 % della legge regionale).

Fatto:

- **Schede**: c'erano già, ma non si vedevano: il riquadretto del righello ha la stessa classe e, nato prima, veniva
  preso al suo posto e nascosto a ogni movimento del mouse. Corretto in `rete.js` (vale per tutte le pagine con righello
  e schede). Contenuti nuovi come chiesti.
- **Terreni a rombo**, confini della particella dallo zoom 13 (tessere degli immobili delle PA, già sul server),
  **edifici ad anello** dallo zoom 16 con i contorni degli edifici accesi da soli.
- **Livelli** «Consumi» (barre accanto agli edifici, MWh) e «Potenza FV» (barre gialle sulle cabine, kWp), ognuno in
  scala tra le sue barre.
- **Aree non idonee**: zone A, B e C dei parchi, riserve e siti della Rete Natura 2000, lette dal browser dal WFS della
  Regione Emilia-Romagna (CC BY 4.0) attorno agli edifici e alle cabine; i terreni il cui centro cade dentro sono esclusi;
  aree contigue e zone D dei parchi solo segnalate. Sul geoportale della Regione non c'è più una carta «aree non idonee
  al fotovoltaico» in vigore: quella della DGR 46/2011 seguiva la DAL 28/2010, che non si applica più.
- **Regola del 10 %**: era della DAL 28/2010 (impianto al massimo sul 10 % della superficie agricola disponibile) e della
  DAL 125/2023; l'art. 21 della **L.R. 5/2026** le fa cessare, tranne le parti della DAL 125/2023 sulle colture di pregio.
  Oggi la superficie si conta con l'art. 5 (recinzione per il fisso; 30 % o proiezione dei moduli per l'agrivoltaico),
  come faceva già la pagina; il limite comunale è il 2,5 % della SAU. Il 10 % resta solo come **scelta prudente** per i
  terreni con colture certificate (casella nei parametri, **accesa** per difetto: Paolo, 18:32). Siti Natura 2000 esclusi come le zone dei parchi (Paolo, 18:32). La L.R. 27/10/2026 n. 15 ha tolto il limite di 1 MW per
  gli impianti delle CER fuori dalle aree idonee: il limite di 1 MW per impianto resta quello degli incentivi del GSE.
- **Ente promotore** (Paolo, 17:22: «tra i terreni vanno selezionati prioritariamente quelli dell'ente stesso … ad
  esempio come AUSL Romagna ne abbiamo parecchi»): ricerca dell'ente nei parametri; i suoi terreni ammessi vanno prima
  degli altri (★ nella tabella), anche tra quelli proposti per cabina.
- **Fase 17**: se il `comuni.parquet` non ha il codice catastale si usa da solo l'elenco ISTAT; senza tabella dei comuni
  il comando si ferma con un errore chiaro invece di ripiegare sul metodo lento (il blocco del CF5 del pomeriggio).

Prove: `fase5-sito/tests/test_fv_cer.py` (calcolo: area non idonea e 10 %; pagina: esclusione, schede, livelli, scheda
che compare davvero col mouse), suite della fase 5, `fase17-cer-fv/tests` (10).

## Passi (dopo il via di Paolo: pull request, Merge e release come sempre)

Niente da fare sul server oltre all'installazione della release: le aree non idonee si leggono dal browser e i confini
dei terreni dalle tessere che ci sono già.
