# Aggiornamento del 16/11/2026 (f) – Aggiornamento notturno: email solo se qualcosa va storto

Sesta pubblicazione del 16/11. Va **sopra la `v2026.11.16e`**. Release **`v2026.11.16f`**. Il sito non cambia (resta
`?v=20261116d`) e non c'è una voce nelle Novità, perché non cambia nessuna funzione per gli utenti.

## Decisione di Paolo (16/11/2026, 17:51)

Paolo ha messo nel crontab del server la riga dell'aggiornamento notturno (procedura X9 di `AGGIORNAMENTO_2026-11-12.md`):
```
40 4 * * * $HOME/energia/fase4-server/aggiorna_da_github.sh --notte >/dev/null 2>&1
```
Fino alla `v2026.11.16e`, con `--notte` lo script mandava un'email a ogni release installata, anche quando andava tutto
bene. Paolo vuole invece l'email **solo se qualcosa va storto**; se va tutto bene, nessuna email.

## Cosa cambia

Il file cambiato è `fase4-server/aggiorna_da_github.sh`. L'email all'amministratore parte solo in tre casi:

1. **Aggiornamento fallito**: la build non riesce, i container non partono o l'api non risponde entro 3 minuti. Lo
   script torna da solo alla versione di prima e manda l'email «aggiornamento a … fallito». Era già così e vale anche
   quando lo script si lancia a mano.
2. **Errore imprevisto di notte**: per esempio GitHub irraggiungibile, rsync o disco pieno. L'oggetto è «aggiornamento
   notturno interrotto», con la riga dello script e il registro da guardare. Prima lo script si fermava senza dire
   nulla.
3. **Release installata con problemi minori**: il Purge di Cloudflare o gli indici dei prezzi non sono riusciti.
   L'oggetto è «server aggiornato a …, ma con problemi», con cosa fare a mano.

Se va tutto bene, l'esito resta solo nel registro `~/aggiorna_da_github.log`. Nel registro c'è anche l'elenco delle
procedure `AGGIORNAMENTO_*.md` con i passi a mano: lo script non li manda più per email, perché quei passi sono comunque
scritti nella procedura che accompagna ogni release.

Correzioni minori nello stesso file:
- `--help` stampava anche tre righe di codice dopo l'intestazione;
- senza il file `.env` lo script si fermava al Purge invece di scrivere «non fatto»;
- il promemoria finale nomina le due righe del crontab, non più «1 riga».

Gli altri file cambiati sono `fase4-server/README.md`, nella sezione «Aggiornamento del server da GitHub», e questo
file.

## Prove (16/11/2026, container)

Le prove usano un repository di prova con due release e docker e curl finti:

| Caso | Uscita | Email |
|---|---|---|
| notte, release nuova, tutto bene (con e senza Purge configurato) | 0 | nessuna |
| notte, nessuna release nuova | 0 | nessuna |
| notte, Purge che risponde `"success":false` | 0 | «server aggiornato a v2026.11.16f, ma con problemi» |
| notte, build dell'immagine che fallisce | 1 | «aggiornamento a v2026.11.16f fallito», server tornato alla `v2026.11.16e` |
| notte, repository irraggiungibile | 128 | «aggiornamento notturno interrotto» |
| a mano, release nuova, tutto bene | 0 | nessuna |
| a mano, release già installata | 0 | nessuna |

`bash -n` senza errori.

## Procedura AF1–AF3

### AF1. [PC] Script
Copia `pubblica_2026-11-16f.ps1` ed `eugenio_2026-11-16f.patch` nella cartella del clone, poi:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
powershell -ExecutionPolicy Bypass -File .\pubblica_2026-11-16f.ps1
```
Lo script fa questi passi:
1. controlla che la `v2026.11.16e` ci sia;
2. applica la patch;
3. fa il commit e il push;
4. crea la release `v2026.11.16f` con `gh`. Se `gh` non c'è, stampa il testo da incollare su
   https://github.com/StatoCritico/eugenio/releases/new.

Cosa aspettarsi: alla fine la riga verde `FATTO`. Se compare una riga rossa `FERMO: …`, mandamela.

### AF2. [Server] Aggiornamento subito, a mano
Va fatto subito, non stanotte. Stanotte alle 4:40 girerebbe ancora lo script vecchio, che manderebbe l'email «server
aggiornato».
```bash
ssh eugenio
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi:
- `Aggiornamento da v2026.11.16e a v2026.11.16f`;
- `api e worker aggiornati e funzionanti`;
- `Purge di Cloudflare: fatto`;
- `Release v2026.11.16f installata`;
- in fondo `Controlla: docker compose ps … e crontab -l (edifici-lidar alle 3:30, aggiorna_da_github.sh --notte alle
  4:40)`.

### AF3. [Server] Controllo
```bash
grep -c "email solo se qualcosa va storto" ~/energia/fase4-server/aggiorna_da_github.sh; crontab -l
```
Cosa aspettarsi: `1`, poi le due righe del crontab (3:30 e 4:40). Da stanotte, se non ci sono release nuove o va tutto
bene, nessuna email.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, decisioni di Paolo del 16/11: aggiornamento notturno dalle release alle 4:40 (X9), **email solo se qualcosa
  va storto**.
- RIEPILOGO, stato: release `v2026.11.16f`, sito invariato (`?v=20261116d`).
- DA_FARE: [ ] **Paolo**: AF1, AF2, AF3.
