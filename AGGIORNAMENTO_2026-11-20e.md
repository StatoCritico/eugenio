# Aggiornamento del 20/11/2026 e – Dati di Terna nel worker

Codice del server (fase 4) e immagine con la fase 15: il worker acquisisce e tiene aggiornati i dati di Terna per le pagine
«Produzione e consumi di elettricità» e «Carichi elettrici». Nessun cambio di versione del sito; le due pagine leggeranno
`dati/elettricita/` e `dati/carichi/` quando i costruttori della fase 15 saranno pronti (fino ad allora il worker scarica e
archivia, ma non pubblica nulla).

> **Dopo l'unione dei rami (ramo `claude/2026-11-20-insieme`)** i due costruttori della fase 15 ci sono già:
> `costruisci` (statistiche annuali) e `costruisci_carichi`, che legge direttamente l'archivio Parquet del worker
> (`/srv/energia/dati/terna/serie/carico_totale`, `produzione`, `rinnovabili`). Quindi, con questo ramo, il worker
> **pubblica** `dati/elettricita/` alla prima accensione e `dati/carichi/` dopo il primo `terna-api` riuscito; le due pagine
> si vedono però solo quando Paolo pubblica il sito con la versione nuova.

**Decisione di Paolo**: i dati di Terna si caricano sul server per le elaborazioni del sito ma non si scaricano dal sito e
non vanno mai nel repository. Niente prezzi, corrispettivi o MSD di Terna (cataloghi Market e Fees esclusi).

## Cosa cambia sul server

- **Worker**, tre lavori nuovi (dettagli nel README della fase 4, § «Dati di Terna»):
  - `terna-api`, **ogni giorno dalle 06:30**: il giorno prima dall'API ufficiale (6 serie: carico totale e di mercato,
    picco e valle, produzione, rinnovabili, bilancio), l'IMCEI mensile, **6 mesi di storico al giorno** dal Download
    Center di Terna (senza chiave, non consuma la quota) a partire da gennaio 2021: in ~12 giorni lo storico è completo.
    Archivio in `/srv/energia/dati/terna/serie/` (un Parquet per serie e mese).
  - `carichi`, subito dopo: file di «Carichi elettrici» in `/srv/energia/sito/dati/carichi/` (quando la fase 15 li sa fare).
  - `elettricita`, **il 5 del mese alle 05:00** (e subito alla prima accensione): statistiche annuali dal Download Center e
    file di «Produzione e consumi di elettricità» in `/srv/energia/sito/dati/elettricita/` (quando la fase 15 li sa fare).
- **Limiti dell'API di Terna**: 1 richiesta al secondo, 300 al giorno. Il worker si ferma a **250** al giorno (contatore in
  `/srv/energia/dati/terna/quota_api.json`); ne usa ~55 il primo giorno, ~20 nei giorni del recupero dell'IMCEI (circa una
  settimana), poi ~7. Una sola applicazione: non crearne altre per avere più quota.
- **`.env`**: due righe nuove, `TERNA_CLIENT_ID` e `TERNA_CLIENT_SECRET` (passo T3). Senza, l'API non parte (lo dice il
  registro, nessuna email) e lo storico dal Download Center va avanti lo stesso.
- **Email** all'amministratore solo per errori veri: archivio fermo da più di 3 giorni (con le chiavi: API ferma, per
  esempio chiavi revocate), Download Center che non risponde in due mesi di fila, file incompleti.
- **Nessuna modifica** al Caddyfile, ai volumi del compose o al crontab. `aggiorna_da_github.sh` copia anche
  `fase15-elettricita` e non tocca `dati/elettricita/` e `dati/carichi/` del sito.

## Procedura T1–T7

### T1. [Browser] Merge e release
Dopo il merge della pull request che contiene questo file, pubblica la release dal collegamento già compilato che ti manda
Claude (come le volte scorse). Se il server si aggiorna da solo di notte (`aggiorna_da_github.sh --notte`), salta T5.

### T2. [Browser] Applicazione su developer.terna.it
1. Apri https://developer.terna.it/member/register e registrati (se hai già un account: «Sign In» in alto a destra su
   https://developer.terna.it/). Conferma l'indirizzo dall'email che ti manda Terna.
2. Dopo l'accesso apri l'area delle applicazioni (istruzioni di Terna:
   https://developer.terna.it/docs/read/How_to_register_an_application) e fai clic su **«Create a new App»**.
3. Nome: `EuGEnio` (niente dati personali). Sito: `https://eugenio.statocritico.it`. Descrizione: `Carichi e produzione
   elettrica per EuGEnio (Stato Critico)`. Callback URL: lascialo vuoto.
4. Lascia il pacchetto **«Public»** selezionato (dà la chiave per tutte le API pubbliche), spunta «I agree to the Term of
   service» e conferma.
5. Cosa deve comparire: la pagina dell'applicazione con due valori, la **Key** (è il Client ID) e il **Secret**. Tienila
   aperta per T3. Non incollarli in email, chat o documenti.

### T3. [Server] Chiavi nel `.env`
```bash
ssh eugenio
```
```bash
cd ~/energia/fase4-server
cp .env ~/env_prima_terna       # copia di sicurezza (resta nella tua cartella, permessi del .env)
chmod 600 ~/env_prima_terna
nano .env
```
In fondo al file aggiungi due righe e incolla i valori di T2 dopo l'uguale, senza spazi né virgolette:
```
TERNA_CLIENT_ID=
TERNA_CLIENT_SECRET=
```
Salva con `Ctrl+O`, `Invio`, esci con `Ctrl+X`. Poi:
```bash
chmod 600 .env
ls -l .env
grep -c '^TERNA_CLIENT_' .env
```
Cosa deve comparire: `ls` mostra una riga che comincia con `-rw-------` (solo tu leggi e scrivi il file); `grep` scrive
`2`. Non usare `cat .env`: stamperebbe i segreti sullo schermo.

### T4. [Server] Cartella dei dati di Terna
```bash
sudo mkdir -p /srv/energia/dati/terna
sudo chown 1000:1000 /srv/energia/dati/terna
sudo setfacl -m u:1000:rwX -m d:u:1000:rwX -m u:ubuntu:rwX -m d:u:ubuntu:rwX /srv/energia/dati/terna
ls -ldn /srv/energia/dati/terna
```
Cosa deve comparire: una riga che comincia con `drwxrwxr-x+` e contiene `1000 1000`. La cartella del sito
`/srv/energia/sito/dati` è già scrivibile dal worker (indicatori e clima): niente da fare.

### T5. [Server] Codice nuovo, ricreare api e worker
Se la release non è ancora installata:
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa deve comparire alla fine: `Release v… installata` e, nel registro, `api e worker aggiornati e funzionanti`.
Il worker legge il `.env` solo quando viene ricreato: se la release era già installata prima di T3, ricreali a mano:
```bash
cd ~/energia/fase4-server
docker compose up -d --force-recreate api worker
docker compose ps
```
Cosa deve comparire: `api` e `worker` in stato `running` (l'api anche `healthy` dopo un minuto).

### T6. [Server] Primo lancio a mano
```bash
cd ~/energia/fase4-server
docker compose run --rm worker python -m servizio.worker terna-api 2>&1 | tee ~/terna_primo.log
```
(Il comando completo è `python -m servizio.worker terna-api`: con `docker compose run --rm worker terna-api` da solo il
container non saprebbe cosa lanciare.) Dura 2–4 minuti, una richiesta al secondo: la prima volta ~55 all'API (gli ultimi 7
giorni × 6 serie, il token, 12 mesi di IMCEI) e ~40 al Download Center; dal giorno dopo ~7 all'API.
Se il worker ricreato in T5 ha già cominciato da solo (dopo le 06:30 parte subito), il comando scrive `un altro
aggiornamento è in corso, niente da fare`: in quel caso guarda il registro del worker con
`docker compose logs --since 1h worker | grep -i terna` e controlla le stesse righe qui sotto.

Cosa controllare nel registro (righe `terna`):
- **non** deve comparire `TERNA_CLIENT_ID o TERNA_CLIENT_SECRET mancanti`: se compare, il `.env` non è stato letto
  (rifai T5) o le righe hanno un nome sbagliato (T3);
- **non** deve comparire `token non ottenuto: HTTP 401` o `HTTP 400`: chiavi sbagliate o applicazione non attiva (controlla
  T2, ricopia i valori, rifai T5);
- l'ultima riga `INFO terna Terna: {...}` deve contenere `'api': 'configurata'`, `'giorni_api': [...]` con i giorni
  scaricati (la prima volta fino a 7, fino a ieri), `'mesi_dc': ['carico_totale 2021-01', …]` (6 mesi per serie) e
  `'quota_usata': n` con n sotto 70 la prima volta (poi ~7 al giorno; il tetto è 250);
- `HTTP 429` o `HTTP 5xx … riprovo più tardi`: Terna è occupata, il worker riprova da solo dopo un'ora; niente da fare.

Poi:
```bash
ls /srv/energia/dati/terna/serie/
ls /srv/energia/dati/terna/serie/carico_totale | head
cat /srv/energia/dati/terna/quota_api.json
```
Cosa deve comparire: sei cartelle (`bilancio`, `carico_mercato`, `carico_totale`, `picco_valle`, `produzione`,
`rinnovabili`) più `imcei`; in `carico_totale` i file `2021-01.parquet` … `2021-06.parquet` e quello del mese in corso;
nella quota `{"giorno": "<oggi>", "richieste": n}`. Il file `stato.json` accanto dice da che mese riprende lo storico
domani. Le chiavi e il token non compaiono mai in questi file né nel registro.

### T7. [Server] Statistiche annuali (facoltativo, il worker lo fa da solo)
```bash
docker compose run --rm worker python -m servizio.worker elettricita 2>&1 | tail -5
```
Cosa deve comparire, finché il costruttore della fase 15 è «in lavorazione»: `costruisci della fase 15 non è ancora pronto
… niente pubblicato` (avviso normale, nessuna email) e i file `/srv/energia/dati/terna/statistiche/<Dataset>_<anno>.json`.
Quando la fase 15 sarà pronta comparirà `Statistiche di Terna: N file pubblicati in /sito/dati/elettricita`.

Nei giorni dopo: `docker compose logs --since 24h worker | grep -i terna` alle 06:30 mostra il giorno prima e i 6 mesi
successivi dello storico; dopo ~12 giorni lo storico arriva al mese scorso e restano solo le richieste giornaliere.

## Prove (20/11/2026)

`cd fase4-server && PYTHONPATH=../fase3-storico:../fase6-mercati:../fase7-territorio:../fase8-indicatori:../fase10-edifici3d:../fase15-elettricita python -m pytest -q`:
**393 passate** (nuove: `tests/test_terna.py` 35). Download Center provato davvero dal container di sviluppo (ottobre 2025
e gennaio–febbraio 2021, sei serie, colonne e ora legale verificate); l'API ufficiale **non** è stata provata con chiavi
vere (non ci sono ancora): la prova vera è T6.
