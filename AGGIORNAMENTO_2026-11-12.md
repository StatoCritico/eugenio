# Aggiornamento del 12/11/2026 – Aggiornamenti da GitHub (pull request e script sul server)

Da fare **con calma, alla prossima sessione** (nessuna urgenza: il sito e la newsletter non cambiano). Release
**`v2026.11.12`**; il sito resta **`?v=20261111b`**.

## Cosa cambia

**Decisione di Paolo del 12/11/2026 (strade «1» e «2a»)**
1. **Strada 1 – pull request**: Claude scrive sul repository `statocritico/eugenio` su un ramo suo e apre una pull
   request; Paolo la guarda su GitHub e la approva (Merge). Su `main` scrive solo il Merge di Paolo.
2. **Strada 2a – il server si aggiorna da GitHub**: dopo il Merge si crea la release; sul server
   `~/energia/fase4-server/aggiorna_da_github.sh` scarica quella release (repository pubblico, nessuna chiave), fa la
   copia di sicurezza, copia codice, convenzioni e sito, ricostruisce api e worker, torna indietro da solo se l'api non
   riparte, rifà gli indici dei prezzi e fa il Purge di Cloudflare. Fine dei pacchetti `codice.tar.gz`/`sito.tar.gz`.
3. Il token di Cloudflare per il Purge sta **solo** nel `.env` del server, con il **solo** permesso «Zone › Cache Purge».

**Cosa resta a mano**: i passi delle procedure che toccano il `.env`, il crontab, archivi grandi o servizi nuovi (lo
script li elenca alla fine e nell'email); i dati di terzi fuori da git (`mercati_energia/dati/`, `uni_privato`, fase 2)
arrivano ancora dal PC; `RIEPILOGO.md` e `DA_FARE.md` (fuori da git) Claude li scrive nel Project e nella cartella del PC.

**File nuovi o cambiati**: `fase4-server/aggiorna_da_github.sh` (nuovo), `fase4-server/.env.example` (`CF_ZONE_ID`,
`CF_PURGE_TOKEN` vuoti), `fase4-server/README.md` (sezione «Aggiornamento del server da GitHub» e riga della lista Prove
ID 4), questa procedura. Lo script è stato provato a vuoto (`--prova`) su cartelle finte: rileva `v2026.11.09f →
v2026.11.11`, 298 file, 3 convenzioni cambiate, la procedura del 11/11; uscita 0, nulla cambiato.

## Procedura X (circa 30 minuti)

### X1. [PC, browser] Collega GitHub a Claude
1. Su claude.ai apri **Impostazioni › Connettori** (Settings › Connectors) e collega **GitHub** con il tuo account
   (quello amministratore dell'organizzazione `statocritico`).
2. Se GitHub chiede su quali repository installare l'app di Claude: organizzazione **statocritico**, «Only select
   repositories» → **eugenio**.

Cosa aspettarsi: GitHub risulta collegato. Alla sessione dopo, Claude prova l'accesso in scrittura: se funziona te lo dice
e lavora con le pull request; se no, ti manda il messaggio che riceve.

### X2. [PC, browser] Proteggi `main` (consigliato)
1. Apri `https://github.com/statocritico/eugenio/settings/branches` → **Add branch ruleset** (o «Add rule»).
2. Nome `main`, destinazione il ramo predefinito, spunta **Require a pull request before merging** (approvazioni
   richieste: 0, così puoi fare Merge tu) e **Block force pushes**. Salva.

Cosa aspettarsi: la regola compare nell'elenco. Da qui in poi su `main` si scrive solo con il Merge di una pull request,
anche per Claude. Se tu vuoi ancora fare `git push` diretto dal PC, in «Bypass list» aggiungi il tuo ruolo (Admin).

### X3. [PC] Commit e release `v2026.11.12`
Ancora alla vecchia maniera (Claude non scrive ancora su GitHub). Il file `fase4-server/README.md` sul PC aveva già la
riga della lista Prove: lo zip la contiene uguale.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short
```
Cosa aspettarsi: **quattro righe**, `A  AGGIORNAMENTO_2026-11-12.md`, `M  fase4-server/.env.example`,
`M  fase4-server/README.md`, `A  fase4-server/aggiorna_da_github.sh`. Altre righe → fermati e mandamele.
```powershell
git update-index --chmod=+x fase4-server/aggiorna_da_github.sh
```
```powershell
git commit -m "12/11/2026: aggiornamento del server dalle release di GitHub (aggiorna_da_github.sh), lavoro con pull request; procedura AGGIORNAMENTO_2026-11-12"
```
```powershell
git push
```
```powershell
gh release create v2026.11.12 --target main --title "EuGEnio 12 novembre 2026 – Aggiornamento da GitHub" --notes "Nuovo script fase4-server/aggiorna_da_github.sh: il server si aggiorna da solo dalle release. Sito invariato (?v=20261111b)."
```
Cosa aspettarsi: il push finisce con `… main -> main`; la release stampa `…/releases/tag/v2026.11.12`.
Se il push è rifiutato per la regola di X2 → aggiungi il tuo ruolo nella «Bypass list» oppure fai X3 prima di X2.

### X4. [server] Strumenti
```bash
which git rsync flock curl docker
```
Cosa aspettarsi: cinque percorsi. Se ne manca uno (di solito `rsync`): `sudo apt-get install -y rsync` e ripeti.

### X5. [server] Primo scaricamento dello script
```bash
git clone https://github.com/statocritico/eugenio.git ~/eugenio-git
```
```bash
install -m 755 ~/eugenio-git/fase4-server/aggiorna_da_github.sh ~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: il clone finisce con `done.`; il secondo comando non stampa nulla. Da qui in poi lo script si aggiorna da
solo a ogni release.

### X6. [Cloudflare, poi server] Token per il Purge
1. Cloudflare → icona del profilo → **My Profile › API Tokens › Create Token › Create Custom Token**. Nome
   `eugenio-purge`; permessi: **Zone · Cache Purge · Purge**; Zone Resources: **Include · Specific zone ·
   statocritico.it**; nient'altro. Crea e **copia il token** (si vede una volta sola).
2. Pannello della zona `statocritico.it` → **Overview**, colonna di destra, sezione API: copia lo **Zone ID**.
3. Sul server apri il `.env`:
```bash
nano ~/energia/fase4-server/.env
```
   In fondo aggiungi due righe con i valori copiati (senza spazi né virgolette): `CF_ZONE_ID=…` e `CF_PURGE_TOKEN=…`.
   Salva (Ctrl+O, Invio, Ctrl+X). **Non mandarmi i valori.**
```bash
grep -c "^CF_ZONE_ID=.\|^CF_PURGE_TOKEN=." ~/energia/fase4-server/.env
```
Cosa aspettarsi: `2`.

### X7. [server] Prova a vuoto
```bash
du -sh ~/energia; df -h ~ | tail -1
```
Cosa aspettarsi: la dimensione di `~/energia` e lo spazio libero. Lo script tiene fino a 3 copie di `~/energia`: lo
spazio libero deve essere almeno **4 volte** la dimensione. Se non basta, mandami le due righe prima di andare avanti.
```bash
~/energia/fase4-server/aggiorna_da_github.sh --prova
```
Cosa aspettarsi, nelle ultime righe: `Release v2026.11.12 da installare (sito ?v=20261111b).`, l'elenco delle
convenzioni (nessuna o quelle già copiate l'11/11), `Purge: [prova] Purge Everything della zona`, le procedure
`AGGIORNAMENTO_2026-11-12.md` (questa, i passi a mano sono X4–X8) e `Prova finita: niente è stato cambiato.`
Se c'è un errore → mandami le ultime 20 righe.

### X8. [server] Primo aggiornamento vero
```bash
echo v2026.11.11 > ~/.eugenio_versione
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi (3–6 minuti per la build): `api e worker aggiornati e funzionanti`, `Sito aggiornato a ?v=20261111b`,
`Indici dei prezzi rifatti`, `Purge di Cloudflare: fatto`, e alla fine `Release v2026.11.12 installata`. Poi:
```bash
cat ~/.eugenio_versione; cd ~/energia/fase4-server && docker compose ps
```
Cosa aspettarsi: `v2026.11.12`; api e worker `Up`, api `(healthy)`. Il sito in incognito si apre come prima.
Se lo script dice `ERRORE: … Torno alla copia di sicurezza` → mandami le ultime 30 righe di `~/aggiorna_da_github.log`: il server
è già tornato com'era.

### X9. [server, più avanti] Aggiornamento automatico di notte (facoltativo)
Dopo **due o tre** aggiornamenti a mano andati bene. Prima salva il crontab di oggi:
```bash
crontab -l > ~/crontab_prima_aggiorna.txt; cat ~/crontab_prima_aggiorna.txt
```
Cosa aspettarsi: la riga di `edifici-lidar` delle 3:30 (e nient'altro di nuovo).
```bash
(crontab -l; echo '40 4 * * * $HOME/energia/fase4-server/aggiorna_da_github.sh --notte >/dev/null 2>&1') | crontab -
```
```bash
crontab -l
```
Cosa aspettarsi: le righe di prima più quella delle 4:40. Alle 4:40 lo script non fa nulla se non c'è una release nuova;
se c'è, la installa e manda l'email con l'esito e gli eventuali passi a mano. Per toglierla:
`crontab ~/crontab_prima_aggiorna.txt`.

## Come lavoreremo dalla prossima volta

1. Claude lavora su un ramo `claude/<data>-<tema>` e apre la **pull request** con la descrizione, i test fatti e gli
   eventuali passi a mano (in un file `AGGIORNAMENTO_<data>.md` come oggi, più corto).
2. **Paolo** su GitHub: scheda «Files changed», poi **Merge pull request**.
3. Claude (o Paolo con `gh release create`) crea la **release** `vAAAA.MM.GG` con le note dalla voce di `novita.toml`.
4. **Paolo** sul server: `~/energia/fase4-server/aggiorna_da_github.sh` (o niente, se c'è la riga di X9), più gli
   eventuali passi a mano; prova del sito in incognito.
5. `RIEPILOGO.md` e `DA_FARE.md` (fuori da git) Claude li aggiorna nel Project e nella cartella del PC; i file di terzi
   fuori da git restano consegnati sul PC.
