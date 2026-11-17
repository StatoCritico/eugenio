# Aggiornamento del 18/11/2026 – Rete elettrica, cabine primarie, ricerca degli indirizzi, ortofoto AGEA

Release `v2026.11.18`, sito `?v=20261118a`. Contiene: pagine **Statistiche › Stato della rete elettrica** e
**Fotovoltaico › Cabine primarie** con il servizio della rete (passi R1–R6), la **ricerca degli indirizzi** con particella
e metà della via (R7), le **ortofoto AGEA 2022–2024** (R8), l'apertura di Costi energetici Sanità sull'Emilia-Romagna e il
ringraziamento in Contributi (niente da fare sul server).

**Prima**: se la release `v2026.11.17` (immobili delle PA) non è ancora stata installata, i suoi passi AI2–AI6 di
`AGGIORNAMENTO_2026-11-17.md` valgono anche con questa release (il codice è compreso): R4 sostituisce AI2.

## Cosa cambia sul server

- **Worker**: due lavori nuovi (`servizio/rete.py`):
  - **interruzioni** di e-distribuzione **ogni 15 minuti** (minuti 3, 18, 33, 48), in un thread a parte;
  - **saturazione dei trasformatori ogni notte alle 01:15** (ora italiana): tutte le ~110 province con `comuniServiti`
    (gettone nuovo a ogni chiamata, mai registrato; pausa di 4 s; ~10 minuti), comuni gestiti da e-distribuzione,
    elenco delle province. Torino oggi risponde 500: si ritenta ogni notte, la pagina dice «dato non disponibile».
    Alla prima accensione la saturazione parte **subito** (il database non ne ha ancora).
  - email all'amministratore solo oltre le 72 ore (interruzioni non lette, o più di 5 province ferme).
- **Database** SQLite `/srv/energia/dati/rete/rete.sqlite` (nel container `/dati/rete/rete.sqlite`), creato dal worker.
  Una fotografia della saturazione per mese (storico mensile per trasformatore), tutte le interruzioni viste.
- **API**: sei rotte `GET /api/rete/stato`, `/api/rete/cabine`, `/api/rete/comuni`, `/api/rete/cabine/comune/{istat}`,
  `/api/rete/interruzioni/attive`, `/api/rete/interruzioni/comune/{istat}` (README della fase 4, § «Stato della rete
  elettrica»; `EUGENIO_PER_AGENTI.md` § 4.10). Nessun Turnstile, limite di 1.200 richieste per IP all'ora.
- **Tabella di raccordo** `/srv/energia/dati/rete/raccordo_cp.csv` (posizioni OSM, ODbL; codici `COD_AC` del GSE): va
  copiata a mano (passo R3). Senza, le rotte funzionano ma le cabine non hanno posizione.
- **Nessuna modifica** al `.env` (variabili facoltative in `.env.example`), al Caddyfile, al compose o al crontab.

## Prova fatta il 17/11/2026 (dal container di sviluppo, fonti vere)

- Interruzioni: una lettura, 275 righe, 197 interruzioni, 1,1 s.
- Saturazione: 109 province su 110 (fallita solo Torino, `HTTP 500` dopo il secondo tentativo), 21.967 righe
  trasformatore–comune (le stesse dell'elenco raccolto il 17/11), 1.717 cabine primarie, 6.895 comuni, 7.903 comuni
  nell'elenco dei comuni gestiti; ~9 minuti. Nessun gettone nel registro né nel database.
- Rotte sul database vero: Emilia-Romagna 330 comuni, 23 non serviti da e-distribuzione; calcolo della criticità di tutta
  Italia ~1 s alla prima richiesta, poi in memoria.

## Test (17/11/2026)

`cd fase4-server && PYTHONPATH=../fase3-storico:../fase10-edifici3d:../fase7-territorio python -m pytest tests -q`:
**323 passate** (nuove: `tests/test_rete.py` 22, `tests/test_worker.py` 4; `test_agenti.py` con le sei rotte nuove).

## Procedura R1–R6

### R1. [Browser] Merge e release
Dopo il merge della pull request che contiene questo file, pubblica la release dal collegamento già compilato che ti manda
Claude (come le volte scorse).

### R2. [Server] Cartella del database
```bash
ssh eugenio
```
```bash
sudo mkdir -p /srv/energia/dati/rete
sudo chown 1000:1000 /srv/energia/dati/rete
sudo setfacl -m u:1000:rwX -m d:u:1000:rwX -m u:ubuntu:rwX -m d:u:ubuntu:rwX /srv/energia/dati/rete
ls -ldn /srv/energia/dati/rete
```
Cosa aspettarsi: una riga che comincia con `drwxrwxr-x+` e contiene `1000 1000` (proprietario e gruppo 1000, il `+` dice
che ci sono gli ACL). L'utente 1000 è quello dei container `api` e `worker`; `ubuntu` (1001) può copiarci la tabella.

### R3. [PC] Copia della tabella di raccordo
Dalla cartella in cui hai estratto `rete_elettrica_dati_2026-11-17.zip` (sottocartella `rete_elettrica_dati`):
```powershell
cd C:\Users\ingpa\Documents\claude\rete_elettrica_dati
scp raccordo_cp.csv eugenio:/srv/energia/dati/rete/raccordo_cp.csv
ssh eugenio "head -1 /srv/energia/dati/rete/raccordo_cp.csv; wc -l /srv/energia/dati/rete/raccordo_cp.csv"
```
Cosa aspettarsi: `100%`, poi l'intestazione
`cod_ac,gestore,cod_cp_ed,nome_cp_ed,comuni_serviti,osm_id,osm_nome,lat,lon,punteggio_nome,distanza_m,esito,data_raccordo,versione_ac,nota`
e il numero di righe (circa 2.150 più l'intestazione). Il servizio rilegge il file da solo quando cambia: per una
versione nuova basta ricopiarlo.

### R4. [Server] Aggiornamento da GitHub
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da … a v2026.11.18…`, `api e worker aggiornati e funzionanti`, `Release … installata`
(l'immagine dell'api si ricostruisce: cambia `fase4-server`). Se alle 4:40 l'aggiornamento notturno l'ha già installata,
lo script dice che è già installata: va bene, vai avanti.

### R5. [Server] Primo giro dei lavori
Il worker appena riavviato fa da sé la prima lettura delle interruzioni e, siccome il database non ha ancora la
saturazione, la prima saturazione (~10 minuti). Per seguirli:
```bash
cd ~/energia/fase4-server
docker compose logs -f --since 5m worker | grep -E "rete|Interruzioni|Saturazione"
```
Cosa aspettarsi, entro un minuto: `Database della rete: schema alla versione 1` e `Interruzioni: {'esito': 'ok', 'righe':
…, 'interruzioni': …}`; dopo ~10 minuti `Saturazione: 109 province su 110, fallite 001`. Esci con Ctrl+C.
Nessuna riga dei lavori della rete deve contenere il gettone: lo controlla questo comando, che deve stampare `0`:
```bash
docker compose logs worker | grep -iE "rete|interruz|saturaz" | grep -ci "token"
```
Se il worker non parte da solo (per esempio `RETE_ATTIVA=false` nel `.env`), si possono lanciare a mano:
```bash
docker compose run --rm worker python -m servizio.worker rete-interruzioni
docker compose run --rm worker python -m servizio.worker rete-saturazione
```

### R6. [Server] Prova delle rotte
```bash
curl -s https://eugenio.statocritico.it/api/rete/stato | python3 -m json.tool | head -30
curl -s "https://eugenio.statocritico.it/api/rete/comuni?regione=08" | python3 -c "import json,sys; c=json.load(sys.stdin); print(len(c), sum(not x['concessionario'] for x in c))"
curl -s "https://eugenio.statocritico.it/api/rete/cabine?regione=08" | python3 -c "import json,sys; g=json.load(sys.stdin); print(len(g['features']), g['senza_posizione'], g['licenza'])"
curl -s "https://eugenio.statocritico.it/api/rete/interruzioni/attive" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['features']))"
```
Cosa aspettarsi:
- `stato`: `saturazione_aggiornata` e `interruzioni_aggiornate` con la data di oggi, `"province_mancanti": ["001"]`,
  `raccordo.righe` intorno a 2.150;
- `comuni?regione=08`: circa `330` comuni e una ventina non concessionari;
- `cabine?regione=08`: qualche centinaio di cabine, il numero di quelle senza posizione e `ODbL 1.0 – https://…`;
- `interruzioni/attive`: il numero delle interruzioni in corso in Italia (di sera ~200).

Da quel momento: interruzioni ogni 15 minuti, saturazione ogni notte alle 01:15. Email all'amministratore (decisione
di Paolo del 17/11) **solo** se le interruzioni non si leggono da più di 72 ore consecutive, oppure se più di 5 province
non sono aggiornate con successo da più di 72 ore consecutive; una sola email per episodio, nessun'altra (Torino da sola
non ne manda mai). Gli altri errori restano nel registro del worker (`docker compose logs worker`).

### R7. [Server] Ricerca degli indirizzi: fonti raggiungibili
La ricerca con particella e metà della via usa due servizi pubblici: il **WFS della cartografia catastale dell'Agenzia
delle Entrate** e **Overpass** (OpenStreetMap). Senza, la ricerca torna come prima, con un avviso.
```bash
cd ~/energia/fase4-server
docker compose exec api python -c "import urllib.request as u; print(u.urlopen('https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php?service=WFS&request=GetCapabilities', timeout=20).status)"
docker compose exec api python -c "import urllib.request as u; print(u.urlopen('https://overpass-api.de/api/status', timeout=20).status)"
```
Cosa aspettarsi: `200` e `200`. Se il primo indirizzo non è quello giusto, vale quello di `CATASTO_WFS_URL` nel README della
fase 4 (§ «Ricerca di un luogo»). Poi, nel browser, Territorio › Ortofoto: cerca «Rimini, viale Settembrini 2» → la mappa
inquadra l'ospedale Infermi (particella foglio 99 n. 1); cerca «Rimini, via Coriano» → si vede tutta la via.

### R8. [Browser] Ortofoto AGEA
Territorio › Ortofoto, scegli un comune fuori dall'Emilia-Romagna (es. Milano, Palermo): le tessere arrivano in meno di un
secondo, sotto la mappa la citazione «AGEA – Agenzia per le Erogazioni in Agricoltura, ortofoto RGB 2024» (o 2022, 2023
secondo la regione). Nessun passo sul server: la fonte è in `fase10-edifici3d/ortofoto/italia.toml`, già nell'immagine
dell'api ricostruita in R4. Se compare «non risponde» su molte tessere, guarda `docker compose logs --since 10m api | grep
-i agea` e dimmelo (ritmo verso AGEA: 10 al secondo, 8.000 all'ora per tutto il sito).
