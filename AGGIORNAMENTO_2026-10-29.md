# Aggiornamento del 29/10/2026 sera

Cosa si pubblica:
- **sito `?v=20261029a`** (anche la seconda tornata: totali, costi unitari, due mappe consumi/costi, Pareto, report, vista isometrica):
  - riquadretti sulle mappe grandi di tutte le pagine;
  - Patrimonio con mappa 3D della sola regione;
  - scheda «Valori per sede» con barre a mattoncini ed esportazione SVG;
  - file Excel e OpenDocument accettati ovunque;
  - `protezione.js` in tutte le pagine (verifica anti-robot) e informativa privacy aggiornata;
- **server**: `servizio/tabelle.py` e la rotta `/api/converti`, con previsione e patrimonio che accettano .xlsx e .ods;
- **protezione dell'API** (`servizio/protezione.py`): limiti per rete (IPv6 per /64), tetto Zornade per tutto il sito,
  coda delle previsioni, limiti anche sulle rotte dei dati, verifica Cloudflare Turnstile sulle rotte che costano,
  email solo per i limiti superati più giorni di fila; in Cloudflare anche una regola di rate limiting su `/api/`;
- **meteo nazionale**: `s3.py` corretto per le isole (Ischia, Eolie, Lampedusa…) e ripresa del download.

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

## A. Sul PC (PowerShell)

**1.** Entra nella cartella del progetto:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```

**2.** Rimetti le parti comuni in tutte le pagine (aggiunge `protezione.js` nel `<head>`, la versione resta `20261029a`):
```powershell
cd fase5-sito
python costruisci_pagine.py
```
Deve comparire `versione 20261029a: 12 file aggiornati (…)` (il numero può essere un po' diverso, non 0).

**3.** Prepara il pacchetto del sito (sei ancora in `fase5-sito`). Restano fuori i dati degli indicatori, che il server
rifà da sé:
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
```
Controllo: `dir ..\sito.tar.gz` mostra l'ora di adesso.

**4.** Copia sul server sito, codice del server e codice della fase 3, un comando alla volta:
```powershell
scp ..\sito.tar.gz eugenio:~/
scp fase4-server\servizio\app.py fase4-server\servizio\tabelle.py fase4-server\servizio\report.py fase4-server\servizio\report_servizi.py eugenio:~/energia/fase4-server/servizio/
scp fase4-server\servizio\protezione.py fase4-server\servizio\config.py fase4-server\servizio\storici.py eugenio:~/energia/fase4-server/servizio/
scp fase3-storico\meteo_storico\s3.py fase3-storico\meteo_storico\__main__.py eugenio:~/energia/fase3-storico/meteo_storico/
```
Per ogni file deve comparire una riga con `100%`.

## B. In Cloudflare (browser, https://dash.cloudflare.com)

**5.** Crea la verifica anti-robot. Nel menu a sinistra apri **Turnstile** (nel menu nuovo può stare sotto «Application
security»), poi **Add widget** e compila:
- **Widget name**: `eugenio`;
- **Hostname management** → **Add Hostnames**: `eugenio.statocritico.it`, poi **Add**;
- **Widget Mode**: **Managed**;
- **Pre-clearance**: **No**.

Premi **Create**. Compaiono **Site Key** e **Secret Key**: lascia la pagina aperta, servono al passo 11. La Secret Key è
un segreto: non incollarla in chat né in un file del progetto.

**6.** Crea la regola di rate limiting. Apri il dominio **statocritico.it** → **Security** → **Security rules** (oppure
**WAF** → **Rate limiting rules**) → **Create rule** → **Rate limiting rule**, e compila:
- **Rule name**: `API EuGEnio`;
- **If incoming requests match**: Field **URI Path**, Operator **starts with** (se manca, **contains**), Value `/api/`;
- **With the same characteristics**: **IP**;
- **When rate exceeds**: Requests **60**, Period **10 seconds**;
- **Then take action**: **Block**, Duration **10 seconds**.

Premi **Deploy**. La regola compare nell'elenco come attiva.

**7.** Controlla che **Bot Fight Mode** sia spento: **Security** → **Settings** (oppure **Bots**) → **Bot Fight Mode**
su **Off**. Acceso bloccherebbe anche chi scarica i dati aperti con uno script.

## C. Sul server

**8.** Entra nel server con `ssh eugenio`.

**9.** Guarda a che punto è il download del meteo:
```bash
tail -5 ~/scarica_s3.log
du -sh /srv/lavoro/archivio
```
Stamattina si era fermato con l'errore «reversed ranges», quello delle isole. Se l'ultima riga è ancora quella, va solo
ripreso al passo 15. Se invece scorrono righe `icon …`, il download sta lavorando: entra nella sessione con
`tmux attach -t meteo`, fermalo con **Ctrl+C** e riprendilo al passo 15 con il codice nuovo. I pezzi già fatti restano.

**10.** Genera la chiave che firma i gettoni di sessione:
```bash
openssl rand -hex 32
```
Compare una riga di 64 caratteri: copiala (selezionala col mouse).

**11.** Apri il file delle impostazioni: `nano ~/energia/fase4-server/.env`. Vai in fondo (**Ctrl+End** o freccia giù) e
aggiungi tre righe, con i valori al posto dei puntini:
```
TURNSTILE_SITEKEY=...la Site Key del passo 5...
TURNSTILE_SECRET=...la Secret Key del passo 5...
SESSIONE_CHIAVE=...la riga del passo 10...
```
Salva con **Ctrl+O** e **Invio**, esci con **Ctrl+X**. Controllo (non mostra i valori):
```bash
grep -c "^TURNSTILE_SITEKEY=0x\|^TURNSTILE_SECRET=0x\|^SESSIONE_CHIAVE=." ~/energia/fase4-server/.env
```
Deve stampare **3**.

**12.** Pubblica il sito:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261029a /srv/energia/sito/patrimonio.html
grep -c protezione.js /srv/energia/sito/patrimonio.html
```
Il primo numero deve essere maggiore di 0, il secondo **1**.

**13.** Ricostruisci l'immagine e riavvia l'api (legge anche le chiavi nuove del `.env`). Il worker usa la stessa immagine:
```bash
cd ~/energia/fase4-server && docker compose up -d --build api
docker compose run --rm --no-deps -T worker python -m meteo_storico --help | grep -c scarica-s3
docker compose exec -T api grep -c "def in_csv" /app/servizio/tabelle.py
docker compose exec -T api python -c "from servizio import protezione as P; print(P.turnstile_attivo())"
```
Il secondo e il terzo comando devono stampare **1** o più, l'ultimo **True**.

**14.** Controlla la protezione dal server:
```bash
curl -s https://eugenio.statocritico.it/api/protezione; echo
curl -s -o /dev/null -w "%{http_code}\n" "https://eugenio.statocritico.it/api/geocodifica?q=via+zamboni+33+bologna"
```
Il primo mostra `"turnstile":"0x…"` (la Site Key, che è pubblica); il secondo stampa **401**: senza verifica le rotte
protette non rispondono più agli script.

**15.** Riprendi il download del meteo nella sessione `tmux`. Se la sessione non c'è più, `tmux new -s meteo` la ricrea:
```bash
tmux attach -t meteo
```
e dentro:
```bash
cd ~/energia/fase4-server
docker compose run --rm --no-deps -T -v /srv/lavoro/archivio:/archivio worker \
  python -m meteo_storico scarica-s3 --archivio /archivio --regioni tutte --dal 2015-01-01 --per-gruppo 800 \
  2>&1 | tee -a ~/scarica_s3.log
```
Dopo un minuto compare «icon: celle cambiate per 23 comuni, i loro pezzi si rifanno», poi le righe di ICON.
Staccati con **Ctrl+B** e poi **D**.

**16.** Pulizia: `rm ~/sito.tar.gz`, poi esci con `exit`.

## D. Prove dal browser (dopo **Ctrl+F5**)

**17.**
- **Menu:** l'ordine è Dati climatici, Legge 10, Previsioni, Patrimonio, Indicatori; lo stesso ordine hanno i capitoli di
  Come funziona.
- **Previsioni:** passando sopra un comune compare il riquadretto con nome, provincia e gradi giorno; passando sopra una
  regione vicina, il suo nome. Carica il file d'esempio e calcola la previsione: deve funzionare come prima, di solito
  **senza** nessun riquadro di verifica. Se compare il riquadro «Una verifica veloce…» in basso a destra, fai il clic
  richiesto: la previsione parte da sola.
- **Patrimonio:** si vede la sola regione. Carica il file d'esempio degli edifici (geolocalizzazione) e controlla che
  arrivino gli esiti. Poi scendi alla sezione dei valori per sede, scarica il «file di esempio», caricalo e premi
  «Trova le sedi e disegna le barre»: compaiono due mappe (consumi e costi), totali, prezzi medi, tabelle e Pareto.
  Prova a ruotare la mappa (trascinamento), a ruotare solo le barre (Alt+trascinamento o i cursori), a spegnere una
  colonna, a cambiare il colore e a scaricare il disegno SVG.
- **Patrimonio, report:** dopo aver disegnato le barre del file di esempio, scarica il report in PDF (totali, prezzi
  medi, mappe, Pareto, tabelle) e in Excel.
- **Dati climatici:** scarica un CSV piccolo (una provincia, un mese): deve arrivare come prima.
- **Un file Excel:** apri in Excel il file di esempio, salvalo come .xlsx e caricalo in Patrimonio: deve comparire la nota
  sul foglio letto.
- **Dal telefono:** ripeti la previsione col file d'esempio.
- **Privacy:** la pagina dice «Ultimo aggiornamento: 29 ottobre 2026» e parla di Cloudflare Turnstile.

## E. Repository e zip (sul PC)

**18.**
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git add -A
git commit -m "Protezione dell'API (limiti per rete, tetti, Turnstile), mappe con riquadretti, Patrimonio 3D, file Excel e ODS, meteo nazionale da S3"
git push
tar -a -cf ..\eugenio_2026-10-29.zip --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=.git --exclude=.env --exclude=iscrizioni .
```
Facoltativo, prima del commit: nella cartella `fase4-server`, `python -m pytest tests` deve finire con tutti i test
passati (13 nuovi in `test_protezione.py`).

## Se qualcosa va storto

- **L'api non riparte dopo il passo 13:** lancia `docker compose logs --tail 40 api` e mandami le ultime righe.
- **La verifica blocca tutti** (le pagine dicono «Verifica anti-robot non superata» o «Serve la verifica» anche dopo
  aver ricaricato): sul server apri il `.env` con nano, metti `#` davanti alle righe `TURNSTILE_SITEKEY` e
  `TURNSTILE_SECRET`, salva e lancia `cd ~/energia/fase4-server && docker compose up -d api`. La verifica si spegne e
  restano solo i limiti. Poi mandami `docker compose logs --tail 80 api | grep -i turnstile`.
- **La regola di Cloudflare blocca il patrimonio** (errore 429 di Cloudflare con un file grande): alza Requests da 60 a
  120 nella regola del passo 6.
- **Il sito mostra ancora la versione vecchia:** premi Ctrl+F5. Se non basta, controlla che il passo 12 stampi un numero
  maggiore di 0.
- **Il download si ferma di nuovo:** lancia `tail -30 ~/scarica_s3.log` e mandami le righe.
