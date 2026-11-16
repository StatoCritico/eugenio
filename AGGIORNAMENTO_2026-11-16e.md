# Aggiornamento del 16/11/2026 (e) – Attribuzione obbligatoria: termini aggiuntivi della AGPL

Quinta pubblicazione del 16/11. Va **sopra la `v2026.11.16d`**: AE1 si fa dopo AD1. Release **`v2026.11.16e`**. La
versione del sito non cambia (resta `?v=20261116d`) e non c'è una voce nelle Novità, perché non cambia nessuna funzione
per gli utenti.

## Decisione di Paolo (16/11/2026, 14:11)

Paolo ha chiesto l'**attribuzione obbligatoria** per chi mette EuGEnio a disposizione di altri. Il codice resta
**AGPL-3.0**. Il testo di `LICENSE` non si tocca: la sezione 7 della AGPL permette al titolare di aggiungere termini,
scritti in un file a parte. I termini sono tre:

- **lettera b**: chi distribuisce EuGEnio, o lo fa usare in rete, anche modificato, deve conservare senza cambiarla la riga
  **«EuGEnio © 2026 Paolo Bianco – Stato Critico – https://eugenio.statocritico.it»**. La riga va nel piè o in una pagina
  raggiungibile da ogni pagina, e può essere preceduta da «Basato su». Non è richiesto nessun logo;
- **lettera c**: le versioni modificate devono essere riconoscibili come diverse da questa e non presentarsi come il sito
  ufficiale;
- **lettera e**: nessun diritto sui nomi e sul logo. È la regola «Nome e logo» del 27/10, ora scritta come termine della
  licenza.

**Uso interno**: Paolo ha chiesto se si può obbligare l'attribuzione anche lì. La risposta è no, finché il codice resta
AGPL: la sezione 2 dice che chi non distribuisce il programma può farlo girare e modificarlo senza condizioni. Per
arrivarci servirebbe una licenza non open source o un contratto, e non è stato fatto. Anche gli output di
un'installazione propria restano fuori dai termini. I report del sito ufficiale restano invece in CC BY 4.0, con la
citazione obbligatoria.

## Cosa cambia nei file

- **Nuovo** `TERMINI_AGGIUNTIVI.md` nella radice: testo in italiano, che prevale, e in inglese. Indica il titolare
  («Paolo Bianco – Stato Critico») e l'ambito: valgono per i file di Stato Critico, non per le librerie in
  `fase5-sito/sito/lib/` né per le cartelle `dati_terzi/`.
- **`fase5-sito/parti/piede.html`**: nel piè di tutte le pagine c'è la riga dell'attribuzione e il collegamento «termini
  aggiuntivi» → `licenza.html#attribuzione`. Le pagine sono rigenerate con `costruisci_pagine.py`.
- **`licenza.html`**: nuova sezione **«Attribuzione obbligatoria: i termini aggiuntivi»** (`#attribuzione`), che spiega
  anche che l'uso interno non ha obblighi. Il punto «Se lo usi così com'è» richiama l'attribuzione.
- **`mirror.html`**: nelle «Regole da rispettare» c'è la riga nuova «L'attribuzione resta».
- **`README.md`** (Licenze e condizioni dei dati) e **`fase5-sito/README.md`** (sezione nuova).
- **`EUGENIO_PER_AGENTI.md`** (le due copie) e **`llms.txt`**: la riga del codice dice «AGPL-3.0 con termini aggiuntivi» e
  riporta l'attribuzione da conservare.
- **Test**: `test_attribuzione_agpl_in_tutte_le_pagine` in `fase5-sito/tests/test_costruisci_pagine.py`.

## Test (16/11/2026, container, sopra il commit `d4d93dc` della 16c)

- `fase5-sito/tests/test_costruisci_pagine.py`: 35 passati e 1 saltato. Fallisce solo
  `test_inversa_utm_dei_confini_con_node`, perché nel container manca `pyproj`; fallisce allo stesso modo anche senza la
  patch.
- `fase4-server/tests/test_agenti.py`: 3 passati e 2 saltati. Le due copie di `EUGENIO_PER_AGENTI.md` sono identiche.
- La patch, applicata a un clone pulito della 16c e seguita da `costruisci_pagine.py`, dà lo stesso risultato del lavoro
  fatto.

## Procedura AE1–AE3

### AE1. [PC] Script, dopo AD1
Copia `pubblica_2026-11-16e.ps1` ed `eugenio_2026-11-16e.patch` nella cartella del clone, poi:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
powershell -ExecutionPolicy Bypass -File .\pubblica_2026-11-16e.ps1
```
Lo script:
1. controlla che la `v2026.11.16d` ci sia;
2. applica la patch;
3. rigenera le pagine;
4. fa girare il test dell'attribuzione;
5. fa il commit e il push;
6. crea la release `v2026.11.16e` con `gh`. Se `gh` non c'è, stampa il testo da incollare su
   https://github.com/StatoCritico/eugenio/releases/new.

Cosa aspettarsi: alla fine la riga verde `FATTO`. Se compare una riga rossa `FERMO: …`, mandamela.

### AE2. [Server] Aggiornamento da GitHub
```bash
ssh eugenio
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Release v2026.11.16e installata`, con il sito aggiornato e il Purge fatto. Cambiano solo file statici,
quindi non serve ricostruire l'api.

### AE3. [Browser]
1. Apri https://eugenio.statocritico.it/ e scorri fino al piè. Dopo «Licenza (codice AGPL con termini aggiuntivi, dati
   CC BY 4.0).» c'è la riga «EuGEnio © 2026 Paolo Bianco – Stato Critico – https://eugenio.statocritico.it».
2. Clicca «termini aggiuntivi»: si apre https://eugenio.statocritico.it/licenza.html#attribuzione con la sezione nuova.
3. Apri https://eugenio.statocritico.it/mirror.html#regole: c'è la riga «L'attribuzione resta».
4. Apri https://github.com/StatoCritico/eugenio/blob/main/TERMINI_AGGIUNTIVI.md: il file si legge.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, «Decisioni prese», sotto «Licenze, conferma»: **dal 16/11/2026 (Paolo)** la AGPL-3.0 ha i termini aggiuntivi
  della sezione 7 (`TERMINI_AGGIUNTIVI.md`): (b) attribuzione «EuGEnio © 2026 Paolo Bianco – Stato Critico –
  https://eugenio.statocritico.it» da conservare nel piè o nella pagina Licenza da chi distribuisce o fa usare in rete,
  (c) versioni modificate distinte, (e) nessun diritto su nomi e logo. Nessun obbligo per l'uso interno (sezione 2) né
  sugli output di un'installazione propria. Titolare indicato: «Paolo Bianco – Stato Critico».
- RIEPILOGO, stato: release `v2026.11.16e` dopo la `v2026.11.16d`; sito invariato (`?v=20261116d`).
- DA_FARE:
  - [ ] **Paolo**: AE1 dopo AD1, poi AE2 e AE3;
  - [ ] **Paolo**: confermare il titolare dei diritti scritto nei termini, «Paolo Bianco – Stato Critico», e l'anno
    2026;
  - [ ] da far vedere al legale, insieme alle questioni GME e BY-SA già aperte: testo di `TERMINI_AGGIUNTIVI.md`;
  - [ ] facoltativo: una riga d'intestazione nei file sorgente principali, «AGPL-3.0 con termini aggiuntivi: vedi
    TERMINI_AGGIUNTIVI.md». La sezione 7 chiede di metterla «nei file sorgente interessati o un avviso che dica dove
    trovarli». Oggi l'avviso sta nel README, nel piè e nella pagina Licenza.
