# Aggiornamento di EuGEnio – sera del 28/10/2026

Cosa va online stasera, tutto insieme (versione del sito `?v=20261028d`):
- **report solo in PDF e dati grezzi in Excel o ODS**: Word e ODT spenti (l'API risponde 410), F.A.Q. riscritta;
- Dati storici anche in **ODS** (libreria odfpy, nuova dipendenza: per questo l'immagine dell'api va ricostruita);
- quanto pronto dal 27/10/2026 e non ancora pubblicato: regola della zona del DPR, «DPR aggiornato» come stima,
  testata unica e cambio di aspetto senza ricarica, sezione Nome e logo, avviso «servizio sperimentale»,
  email notturna dei mercati senza l'avviso GME; titolo dell'avviso sperimentale più grande;
- dati del sito rifatti con la nuova regola della zona: **clima dal 1940** e **anno tipo CTI**.

Il `.env` del server **non si tocca**: i formati dei report sono già giusti per impostazione predefinita
(`REPORT_FORMATI=pdf,xlsx,ods`). Il worker resta spento.

Tempo: circa 20 minuti, più ~10 minuti per la ricostruzione dell'immagine.

---

## A. Sul PC: preparare i pacchetti

**1. Aprire PowerShell** (tasto Windows → scrivi `PowerShell` → Invio).

**2. Andare nella cartella del codice.** Incolla e premi Invio:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
Alla fine il prompt finisce con `...\statocritico\eugenio>`.

**3. Pacchetto del codice del server** (fasi 3, 4, 6, 7, 8, 9; **senza** la fase 2, senza `.venv` e senza `.env`):
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico
```
Controllo: `dir ..\codice.tar.gz` deve mostrare un file di **meno di 1 MB**. Se è molto più grande, è entrata una
`.venv`: fermati e dimmelo.

**4. Pacchetto del sito** (senza `dati/indicatori`, che il server rifà da sé):
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
```
Controllo: `dir ..\sito.tar.gz` mostra un file di qualche MB.

**5. Copiare tutto sul server** (codice, sito e i dati rifatti di clima e CTI). Un comando alla volta:
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
scp ..\pacchetti\cti_dati.tar.gz eugenio:~/
scp ..\pacchetti\clima_dati.tar.gz.part00 ..\pacchetti\clima_dati.tar.gz.part01 ..\pacchetti\clima_dati.tar.gz.part02 ..\pacchetti\clima_dati.tar.gz.part03 ..\pacchetti\clima_dati.tar.gz.part04 eugenio:~/
```
Per ogni file compare una riga con `100%`. L'ultimo comando (~120 MB) richiede qualche minuto.

## B. Sul server: codice e immagine dell'api

**6. Entrare nel server.** Sempre in PowerShell:
```powershell
ssh eugenio
```
Il prompt diventa `ubuntu@eugenio:~$`. Da qui in poi i comandi sono **sul server**.

**7. Copia di sicurezza del codice di oggi** (serve solo se qualcosa va storto):
```bash
cp -a ~/energia ~/energia_prima_20261028
```
Nessun messaggio = tutto bene.

**8. Sostituire il codice con quello nuovo** (il `.env` resta quello del server):
```bash
tar -xzmf ~/codice.tar.gz -C ~/energia && ls ~/energia
```
Deve elencare `fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico` (e
`fase5-sito` se c'era già). Controlla anche che il `.env` ci sia ancora: `ls -l ~/energia/fase4-server/.env` deve
mostrare `-rw-------`.

**9. Ricostruire e riavviare l'api** (~5–10 minuti; il worker resta spento):
```bash
cd ~/energia/fase4-server && docker compose up -d --build api
```
Alla fine compare `Container fase4-server-api-1  Started` (o `Running`). Poi:
```bash
docker compose ps
```
`api`, `caddy`, `postgres`, `listmonk` e `cloudflared` devono essere `Up` (l'api può restare `health: starting` per
un minuto); `worker` **non** deve comparire.

## C. Sul server: sito e dati

**10. Pubblicare il sito:**
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261028d /srv/energia/sito/faq.html
```
Deve stampare un numero maggiore di 0.

**11. Pubblicare i dati del CTI** (7.918 file):
```bash
tar -xzmf ~/cti_dati.tar.gz -C /srv/energia/sito && ls /srv/energia/sito/dati/cti | head -3
```
Deve elencare delle cartelle numeriche (`01`, `02`, `03`…).

**12. Pubblicare i dati del clima dal 1940** (~15.800 file, un paio di minuti):
```bash
cat ~/clima_dati.tar.gz.part0* | tar -xzm -C /srv/energia/sito && ls /srv/energia/sito/dati/clima | head -3
```
Deve elencare `01`, `01.json`, `02`… Nessun messaggio d'errore di `tar`.

## D. Controlli

**13. Dal PC**, apri una seconda finestra di PowerShell e incolla (verifica che Word sia spento):
```powershell
curl.exe -s -X POST "https://eugenio.statocritico.it/api/report?formato=docx" -H "Content-Type: application/json" -d "{}"
```
Deve rispondere `{"detail":"Il formato Word (.docx) non è più disponibile: il servizio gratuito genera i report solo in
PDF e i dati grezzi in Excel o ODS (formati: PDF, Excel (.xlsx), OpenDocument (.ods))"}` (gli accenti possono uscire
storti nella finestra: non importa).

**14. Nel browser**, apri `https://eugenio.statocritico.it/legge10.html` e premi **Ctrl+F5**. Scegli un comune:
la sezione 3 «L'anno tipo del CTI» e la sezione 4 «Il clima dal 1940» devono comparire (la parte che usa l'API può ancora
dire che i dati meteo delle ultime stagioni non sono sul server: è normale finché manca l'archivio della fase 3).

**15. Report:** nella pagina **Patrimonio** carica il file d'esempio e, a elaborazione finita, controlla che i pulsanti
dei report siano **tre** (PDF, Excel, ODS) con sotto la riga «Il servizio gratuito genera il report in PDF e i dati
grezzi in Excel o ODS. Perché solo questi formati?». Scarica il **PDF** e l'**ODS** e aprili.

**16. F.A.Q.:** clic su «Perché solo questi formati?»: si apre la domanda «In che formati posso scaricare i report e i
dati? Perché non in Word?».

**17. Dati storici:** nella pagina **Dati storici** scegli un comune e scarica in **ODS**: il file deve aprirsi.

## E. Pulizia (solo se tutti i controlli sono andati bene)

**18. Sul server**, togli i pacchetti copiati:
```bash
rm ~/codice.tar.gz ~/sito.tar.gz ~/cti_dati.tar.gz ~/clima_dati.tar.gz.part0*
```
La copia `~/energia_prima_20261028` tienila qualche giorno, poi `rm -rf ~/energia_prima_20261028`.

**19. Esci dal server:** `exit`.

## F. Lo zip aggiornato (sul PC)

**20.** Nella finestra di PowerShell del punto 2 (cartella `eugenio`):
```powershell
tar -a -cf ..\eugenio_2026-10-28b.zip --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=.git --exclude=.env --exclude=iscrizioni .
```
Controllo: `dir ..\eugenio_2026-10-28b.zip` mostra un file di qualche MB. La cartella `iscrizioni` (documenti personali
per il GME) resta fuori dallo zip.

## Se qualcosa va storto

- **L'api non riparte** dopo il punto 9: `docker compose logs --tail 50 api` e mandami le ultime righe. Per tornare
  indietro: `cd ~ && rm -rf ~/energia && mv ~/energia_prima_20261028 ~/energia && cd ~/energia/fase4-server && docker compose up -d --build api`.
- **Il sito mostra ancora i pulsanti Word e ODT**: è la cache del browser; Ctrl+F5. Se restano, controlla il punto 10.

## Dopo (non stasera)

I lavori periodici delle fasi 8 e 9 (indicatori il 5 del mese, clima il 10/1 e il 10/7) sono nel codice appena copiato,
ma vanno ancora installati: permessi, `comuni.parquet` nella cartella di lavoro, prima esecuzione e righe nel cron.
Passi nel README della fase 4, sezione «Lavori periodici sui file del sito», e in `DA_FARE.md`.
