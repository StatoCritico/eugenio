# Aggiornamento del 16/11/2026 (c) – Foglio Excel con la citazione di EuGEnio

Terza pubblicazione del 16/11, sopra la `v2026.11.16b`. Sito **`?v=20261116c`**, release **`v2026.11.16c`**.

## Cosa cambia

**Richiesta di Paolo del 16/11, 11:45.** Nel foglio `psicro_UTA.xlsx` serve il riferimento a EuGEnio, perché fa parte
degli obblighi di licenza. Va messo in cima a tutti i fogli, sotto tutti i grafici e nel piè di pagina della stampa di
tutte le pagine. Paolo ha fissato anche due regole.

**Regola dei file Excel**: in ogni file Excel prodotto da EuGEnio la citazione «Fonte: EuGEnio – eugenio.statocritico.it»
compare in tre posti:
- in cima a ogni foglio;
- sotto ogni grafico;
- nel piè di pagina della stampa di ogni pagina.

È scritta nel `README.md` della radice, sezione «Licenze e condizioni dei dati».

**Regola del file per gli agenti AI**: `EUGENIO_PER_AGENTI.md` (le due copie identiche) e `llms.txt` si aggiornano **a ogni
push**, almeno con la data e la versione del sito. È scritta nel `README.md` della radice, sezione «Per gli agenti AI».

**Il foglio passa alla versione 2.2** (`fase14-trattamento-aria/foglio/build_psicro.py`).
- **In cima a ogni foglio** compare «Fonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0)». Sta nella riga 1, a destra del
  titolo, in celle unite: UTA N1:T1, psicro e Mollier N1:U1, Calcoli K1:P1, Liste F1:I1. Nella Guida è in B1, con il testo
  lungo, e la guida parte da B2. **Nessun indirizzo** di UTA, Calcoli o Liste cambia, quindi «Foglio Excel con i miei dati»
  del sito funziona come prima.
- **Sotto ogni grafico** compare «Fonte: EuGEnio – eugenio.statocritico.it – diagramma calcolato con il foglio
  psicro_UTA.xlsx (CC BY 4.0)». Va nei fogli psicro e Mollier e sotto la copia ridotta del diagramma nel foglio UTA. La riga
  è la prima libera sotto il grafico, calcolata dall'altezza del grafico.
- **Nel piè di pagina di stampa** di tutti i fogli la citazione sta a sinistra, «Pagina N di M» al centro e la versione a
  destra.
- La Guida ha nel registro delle modifiche la voce v2.2.
- Novità: la voce del 16/11 ha anche il foglio Excel ed è passata alla versione `20261116c`. Le altre pagine sono state
  portate a `?v=20261116c`, così il browser scarica il foglio nuovo.

## Verifiche (16/11/2026, container)

- `check_workbook.py`: **414/414** controlli superati.
- PDF di LibreOffice di 12 pagine, con la citazione nel piè di ogni pagina, in cima a ogni foglio e sotto i due diagrammi.
- Test:

  | Prove | Passate | Saltate |
  |---|---|---|
  | Fase 14 | 181 | 1 |
  | Pagine di Trattamento aria | 58 | – |
  | Costruzione, menu, Esempi e Contributi, agenti | 53 | 1 |
  | `test_agenti` | 5 | – |

## Da fare dopo (non in questa pubblicazione)

Anche gli altri file Excel prodotti da EuGEnio vanno allineati alla regola: per esempio i report in Excel e ODS del server,
che oggi hanno la citazione nel foglio «Info», e il foglio CHP della fase 13. Il punto è segnato in `DA_FARE.md`.

## Procedura AC1–AC3

### AC1. [PC] Script
Lo script `pubblica_2026-11-16c.ps1` e la patch `eugenio_2026-11-16c.patch` sono già nel clone.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
powershell -ExecutionPolicy Bypass -File .\pubblica_2026-11-16c.ps1
```
Cosa aspettarsi: alla fine la riga verde `FATTO`. Se compare una riga rossa `FERMO: …`, mandamela.

### AC2. [Server] Aggiornamento da GitHub (a scarico finito)
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
- `Aggiornamento da … a v2026.11.16c`;
- `Sito della release: ?v=20261116c`;
- `Release v2026.11.16c installata`.

Se AB2 non era ancora fatto, va bene lo stesso: questa release porta dentro anche la `v2026.11.16` e la `v2026.11.16b`.

### AC3. [Browser e Excel]
1. Apri `https://eugenio.statocritico.it/aria-trasformazioni.html` con Ctrl+F5.
2. Scarica il foglio vuoto. In ogni foglio, in alto a destra, c'è «Fonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0)».
3. Sotto i diagrammi dei fogli psicro e Mollier c'è la riga con la citazione.
4. Con File → Stampa → Anteprima, nel piè di ogni pagina ci sono la citazione a sinistra, il numero di pagina al centro e
   «v2.2» a destra.
5. La Guida, in fondo, ha la voce v2.2.
6. Prova anche «Foglio Excel con i miei dati»: si apre e ricalcola come prima.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, regole di Paolo del 16/11:
  - la **regola dei file Excel**: citazione in cima a ogni foglio, sotto ogni grafico e nel piè di stampa di ogni pagina;
  - **`EUGENIO_PER_AGENTI.md` e `llms.txt` aggiornati a ogni push**.
- RIEPILOGO, stato: `?v=20261116c`, release `v2026.11.16c`, foglio `psicro_UTA.xlsx` v2.2.
- DA_FARE:
  - [ ] **Paolo**: AC1 subito; AC2 e AC3 a scarico finito.
  - [ ] Allineare alla regola dei file Excel gli altri Excel di EuGEnio: report Excel e ODS del server (Previsione,
    Patrimonio, Legge 10, Costi energetici Sanità), Dati climatici in Excel e foglio CHP della fase 13.
