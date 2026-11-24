# Aggiornamento del 24/11/2026 (sera) – CER: mappa più ricca e aree non idonee

Release **`v2026.11.24b`**, sito **`?v=20261124b`** (via di Paolo del 24/11 alle 18:34: «pubblichiamo»), ramo
`claude/2026-11-24-cer-mappa`.

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

## Passi

- **PV1** – [Browser] Merge della pull request su GitHub (collegamento nella risposta di Claude).
- **PV2** – [Browser] Release `v2026.11.24b` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.24b&target=main&title=v2026.11.24b%20%E2%80%93%20CER%20%E2%80%93%20Sviluppo%20impianti%20FV%3A%20mappa%20pi%C3%B9%20ricca%2C%20aree%20non%20idonee%20ed%20ente%20promotore&body=%2A%2ACER%20%E2%80%93%20Sviluppo%20impianti%20FV%3A%20mappa%20pi%C3%B9%20ricca%2C%20aree%20non%20idonee%20ed%20ente%20promotore%2A%2A%20%2824%2F11%2F2026%2C%20versione%2020261124b%29%0A%0AMigliorato%0A-%20Fotovoltaico%20%E2%80%BA%20CER%20%E2%80%93%20Sviluppo%20impianti%20FV%3A%20passando%20col%20mouse%20su%20un%20punto%20della%20mappa%20compare%20la%20sua%20scheda%3A%20consumi%20totali%20per%20gli%20edifici%3B%20foglio%20e%20particella%2C%20superficie%2C%20fotovoltaico%20previsto%20ed%20ente%20proprietario%20per%20i%20terreni%3B%20nome%2C%20codice%20del%20GSE%20e%20congestione%20per%20le%20cabine%20primarie.%0A-%20I%20terreni%20sono%20rombi%20e%2C%20avvicinandosi%2C%20mostrano%20i%20confini%20della%20particella%3B%20da%20vicino%20gli%20edifici%20diventano%20anelli%20e%20compaiono%20i%20loro%20contorni.%0A-%20Nuovi%20livelli%3A%20%C2%ABConsumi%C2%BB%20e%20%C2%ABPotenza%20FV%C2%BB%2C%20barre%20verticali%20in%20scala%20sugli%20edifici%20e%20sulle%20cabine%3B%20%C2%ABAree%20non%20idonee%C2%BB%20con%20parchi%20%28zone%20A%2C%20B%20e%20C%29%2C%20riserve%20e%20siti%20della%20Rete%20Natura%202000%20della%20Regione%20Emilia-Romagna%3A%20i%20terreni%20che%20ci%20cadono%20sono%20esclusi.%0A-%20Puoi%20indicare%20l%27ente%20promotore%20%28per%20esempio%20un%27azienda%20sanitaria%20o%20un%20Comune%29%3A%20i%20suoi%20terreni%20adatti%20vengono%20proposti%20per%20primi.%0A-%20Regole%20aggiornate%20alla%20L.R.%20Emilia-Romagna%205%2F2026%20come%20modificata%20dalla%20L.R.%2015%2F2026%3A%20fuori%20dalle%20aree%20idonee%20gli%20impianti%20a%20terra%20delle%20comunit%C3%A0%20energetiche%20non%20hanno%20pi%C3%B9%20il%20limite%20di%201%20MW%20%28resta%20quello%20degli%20incentivi%29%3B%20sui%20terreni%20con%20colture%20certificate%20l%27impianto%20occupa%20al%20massimo%20il%2010%20%25%20del%20terreno%20%28si%20pu%C3%B2%20togliere%29.%0A%0APagina%3A%20https%3A%2F%2Feugenio.statocritico.it%2Ffv-cer.html
- **PV3** – [Server] per averla subito (altrimenti la installa l'aggiornamento automatico delle 4:40):
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  cat ~/.eugenio_versione
  ```
  Deve dire `v2026.11.24b`.
- **PV4** – [Browser del PC, Ctrl+F5] https://eugenio.statocritico.it/fv-cer.html: scegli l'ente (per esempio «AUSL
  Romagna»), carica edifici e curve, «Calcola», «Cerca i terreni pubblici». Passando col mouse sui punti compaiono le
  schede; i terreni sono rombi (★ quelli dell'ente in tabella); accendi «Consumi» e «Potenza FV»; le aree non idonee
  sono rosse; avvicinandoti (zoom 13) compaiono i confini dei terreni, dallo zoom 16 i contorni degli edifici.


Niente da fare sul server oltre all'installazione della release: le aree non idonee si leggono dal browser e i confini
dei terreni dalle tessere che ci sono già.
