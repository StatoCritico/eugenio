# Aggiornamento del 16/11/2026 (d) – Citazione di EuGEnio in tutti i file Excel

Quarta pubblicazione del 16/11, sopra la `v2026.11.16c`. Sito **`?v=20261116d`**, release **`v2026.11.16d`**.

## Cosa cambia

Paolo ha chiesto, il 16/11 alle 12:05, di applicare la **regola dei file Excel** a tutti gli altri file Excel di EuGEnio.
Il lavoro è stato diviso tra due agenti, uno per i report e uno per Dati climatici; poi l'ho verificato e unito.

La regola: in ogni file Excel la citazione deve stare in cima a ogni foglio, sotto ogni grafico e nel piè di pagina di
stampa di ogni pagina.

- **Report** (Excel e ODS di Previsione, Legge 10, Patrimonio, Costi per sede, Indicatori, Edificio), in
  `fase4-server/servizio/report.py`:
  - la riga 1 di ogni foglio contiene «Fonte: EuGEnio – eugenio.statocritico.it, report del gg/mm/aaaa», con il
    collegamento alla pagina Licenza;
  - nel foglio Info la citazione sta sopra il logo; la vecchia riga «Prodotto da EuGEnio», che la ripeteva, è stata tolta;
  - nei fogli di dati le intestazioni passano alla riga 2;
  - le righe 1 e 2 si ripetono in cima a ogni pagina stampata;
  - nell'Excel il riquadro è bloccato in A3 e il filtro parte da A2;
  - il piè di stampa comincia con la citazione: in Excel con `oddFooter.left`, sotto i 255 caratteri ammessi; negli ODS è
    il piè della pagina «Default»;
  - negli Excel e negli ODS non ci sono grafici, che stanno solo nel PDF; un test controlla che resti così.
- **Dati climatici** (Excel e ODS dei download), in `fase4-server/servizio/storici.py`:
  - riga 1 di «Dati» e di «Info» con la citazione e il richiamo alla licenza;
  - in «Dati» le intestazioni passano alla riga 2;
  - nell'Excel il riquadro è bloccato in A3 e le righe 1–2 si ripetono in stampa;
  - piè di stampa con la citazione: in Excel a sinistra, con «Pagina N di M» a destra; negli ODS il piè c'era già ed è
    passato da 6 a 8 pt;
  - i file restano scritti a flusso.
- **Rilettura dei file**: `servizio/tabelle.py` (`/api/converti`, Previsioni, Patrimonio) salta una prima riga che contiene
  solo «Fonte: EuGEnio…». Così un file scaricato da EuGEnio e ricaricato funziona come prima. Una riga «Fonte: altro»
  invece resta.
- **Prove**:
  - `test_report.py`: nuovi `test_regola_file_excel_xlsx` e `test_regola_file_excel_ods`;
  - `test_storici.py`: nuovi `test_regola_excel_xlsx` e `test_regola_excel_ods`;
  - `test_tabelle.py`: nuovo test sul salto della riga di citazione;
  - `test_solo_clima.py`: righe adattate alle intestazioni in riga 2;
  - `test_report.py` e `test_protezione.py`: nelle fixture c'è anche il segnaposto `meteo_storico.psicro`, che mancava
    dal 14/11 e faceva fallire `test_protezione_e_sessione_dal_sito`.
- **Documenti**:
  - `EUGENIO_PER_AGENTI.md` (due copie): riga 1 con la citazione e intestazioni in riga 2 (con pandas `header=1`), e il
    salto della riga in `/api/converti`;
  - `llms.txt`;
  - README della radice (file allineati) e della fase 4 (sezione «Regola dei file Excel»);
  - voce del 16/11 nelle Novità.
- **Limiti**:
  - negli ODS non c'è il riquadro bloccato: odfpy non lo prevede, servirebbe un `settings.xml` scritto a mano;
  - il CSV non cambia: ha già la citazione nelle righe `#` in fondo.

Restano fuori, perché non sono nel repository e non si distribuiscono (hanno dati veri), i fogli interni sul PC: CHP v5,
database dei cogeneratori e fotovoltaico v3.

## Test (16/11/2026, container)

- Fase 4, tutta: **278 passati, 2 saltati**, compreso `test_protezione_e_sessione_dal_sito`, che prima falliva.
- Fase 5: costruzione, menu, Esempi e Contributi, agenti: **53 passati, 1 saltato**.
- LibreOffice e `pdftotext`, eseguiti dagli agenti: la citazione compare nel piè di ogni pagina. Le prove sono state:
  - report: 9 pagine su 9 in Excel e 7 su 7 in ODS;
  - Dati climatici: 3 pagine su 3 in ciascun formato.

## Procedura AD1–AD3

### AD1. [PC] Script
Lo script `pubblica_2026-11-16d.ps1` e la patch `eugenio_2026-11-16d.patch` sono già nel clone.
```powershell
powershell -ExecutionPolicy Bypass -File .\pubblica_2026-11-16d.ps1
```
Cosa aspettarsi: alla fine la riga verde `FATTO`. Se compare una riga rossa `FERMO: …`, mandamela.

### AD2. [Server] Aggiornamento da GitHub (a scarico finito)
```bash
ssh eugenio
```
```bash
ls /srv/energia/dati/psicro/.scarica_in_corso 2>/dev/null; tail -3 ~/scarica_psicro.log
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi:
- `Aggiornamento da … a v2026.11.16d`;
- codice: `report.py`, `storici.py`, `tabelle.py` e i test;
- `api e worker aggiornati e funzionanti`;
- `Release v2026.11.16d installata`.

Se le pubblicazioni b e c non erano ancora installate, entrano adesso.

### AD3. [Browser]
1. **Legge 10**, Bologna: scarica il report in Excel. Ogni foglio ha in riga 1 «Fonte: EuGEnio – eugenio.statocritico.it,
   report del …» e le intestazioni in riga 2. Scorrendo, le prime due righe restano ferme. Nell'anteprima di stampa, il
   piè comincia con la citazione.
2. Ripeti il punto 1 con l'ODS.
3. **Dati climatici**: scarica un Excel piccolo. Il controllo è lo stesso del punto 1.
4. **Previsioni**: ricarica proprio l'Excel di Dati climatici appena scaricato, come file dei consumi. Le colonne vengono
   riconosciute come prima: la riga della citazione è saltata.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, stato: `?v=20261116d`, release `v2026.11.16d`. Regola dei file Excel applicata a report, Dati climatici e
  `psicro_UTA.xlsx`.
- DA_FARE:
  - [ ] **Paolo**: AD1 subito, AD2 e AD3 a scarico finito;
  - [x] allineare gli altri Excel alla regola (16/11);
  - [ ] fogli interni sul PC (CHP v5, database dei cogeneratori, fotovoltaico v3), se Paolo lo chiede.
