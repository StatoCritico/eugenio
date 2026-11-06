# Aggiornamento del 05/11/2026

Quattro blocchi di DA_FARE eseguiti uno dopo l'altro (richiesta di Paolo del 04/11/2026 sera), esclusi i lavori manuali,
le risposte attese (Regione, GME, Agenzia) e la pubblicazione: **edifici fuori dall'Emilia-Romagna**, **affinamenti
Edificio**, **analisi senza GME e senza UNI**, **valutazione Zornade**. Una sezione per blocco, qui sotto. Zip unico:
`eugenio_2026-11-05.zip` (rigenerato dopo ogni blocco).

Dopo le prove di Paolo sul sito pubblicato (`?v=20261104c`), un **blocco 5**: Ortofoto (confini, contesto, avvisi,
piccola mappa, immagine da scaricare), Modelli 3D in due tempi, causa degli edifici «storti», prove 5–7 della Parte 7,
pagina interna «in attesa», crontab, EuGEnio Visure (build verde, Code signing policy). Sezione in fondo.

Dopo le prove di Paolo sul sito pubblicato `?v=20261105a`, un **blocco 6** (seconda pubblicazione del 05/11, sito
**`?v=20261105b`**): immagini che si scaricano davvero, ricerca in Ortofoto, punto trascinabile, «Esci dalla demo» e livelli
in Modelli 3D (particelle catastali e contorni degli edifici dal proxy del server), menu con «S», «GME», il triangolo
giallo e il gruppo Statistiche, archivio di prova degli edifici del centro di Rimini e «Cosa manca per passare dalla demo
al servizio vero». Sezione «Blocco 6» in fondo; **procedura qui sotto** («Seconda pubblicazione del 05/11»).

La procedura del 04/11 (`PUBBLICAZIONE_2026-11-04.md`) è **già fatta** (online `?v=20261104c`); la procedura cumulativa
C1–C16 è **già fatta** la mattina del 05/11 (online `?v=20261105a`), il commit **C17 no**: si fa una volta sola, alla fine
della procedura D qui sotto, e comprende tutto il 05/11.

## Seconda pubblicazione del 05/11 (`?v=20261105b`) – procedura D1–D17

Si parte da qui:
- online c'è il sito **`?v=20261105a`**, pubblicato stamattina con C1–C16; api e worker ricreati stamattina (il worker usa
  l'immagine `energia-api`); nel crontab una sola riga, `edifici-lidar` alle 3:30;
- nel clone sul PC c'è lo zip della mattina estratto (C2) e **non ancora committato** (C17 non fatto); su GitHub l'ultimo
  commit è quello della codifica di EuGEnio Visure;
- il nuovo zip `eugenio_2026-11-05.zip` (stesso nome, ora più recente) contiene **tutto** il 05/11, mattina e pomeriggio;
  in più `edifici_rimini_prova_2026-11-05.tar.gz` (archivio di prova degli edifici, va solo sul server, **mai** nel clone).

Cosa cambia sul server: **rebuild dell'api** (nuovo `servizio/strati.py`: particelle e contorni degli edifici) e quindi
anche `docker compose up -d worker`; **rebuild dell'immagine `energia-edifici`** (comandi nuovi `dtm-wcs` e
`osm-campione`, pipeline invariata); pacchetto del sito; archivio di prova in `CARTELLA_EDIFICI`. **Caddyfile invariato**:
Caddy non si tocca (le rotte nuove stanno sotto `/api/ortofoto/`, già senza compressione, con timeout di 30 s ed escluse dalla
regola di rate limiting di Cloudflare). Etichette come sopra: **[PC]**, **[Server]**, **[Browser]**. Comandi da incollare
così come sono; nessun valore segreto.

### Parte 1 – PC: zip e controlli

**D1. [PC]** Entra nel clone e guarda lo stato (ci sono le modifiche del mattino, non ancora committate):
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git fetch
git status -sb | Select-Object -First 1
git status --short | Measure-Object
```
Cosa aspettarsi: la prima riga è `## main...origin/main` **senza** `[behind …]`; il `Count` è di qualche decina (lo zip del
mattino).

Cosa fare se va male: con `[behind N]` qualcuno ha spinto su GitHub dopo il commit della codifica: fermati e mandami
`git log --oneline origin/main -3`. Con `Count` 0 lo zip del mattino non era stato estratto: va bene lo stesso, si continua.

**D2. [PC]** Controlla lo zip nuovo ed estrailo sopra il clone (sostituisce i file del mattino; nessun file da cancellare):
```powershell
dir ..\eugenio_2026-11-05.zip
Expand-Archive -Path ..\eugenio_2026-11-05.zip -DestinationPath . -Force
Select-String -Path fase5-sito\sito\index.html -Pattern "20261105b" -List | Measure-Object
git status --short fase11-visure .github
```
Cosa aspettarsi: lo zip ha l'ora di oggi pomeriggio (dopo le 13) e circa 4,7 MB; `Count : 1`; l'ultimo comando elenca solo
`fase11-visure/README.md`, `fase11-visure/tests/test_metadati_exe.py` (`??`) e `.github/workflows/visure-windows.yml`.

Cosa fare se va male: `Count : 0` = è stato estratto lo zip del mattino (rifai `dir` e controlla l'ora); file di
`fase11-visure/visure/…` nell'elenco: fermati (l'impronta del pacchetto cambierebbe).

**D3. [PC]** Pagine già rigenerate e test della fase 5:
```powershell
cd fase5-sito
python costruisci_pagine.py --controlla
python -m pytest -q tests
cd ..
```
Cosa aspettarsi: `versione 20261105b: 0 file da rigenerare`; poi `38 passed`. Senza Playwright e Chromium sul PC i 9 test nel
browser si saltano: `29 passed, 9 skipped` va bene.

Cosa fare se va male: file da rigenerare = zip non estratto del tutto (rifai D2); un test rosso: mandami le ultime 30 righe.

**D4. [PC]** Test e impronta di EuGEnio Visure (come C4; i test della fase 4, 166 con gli 8 nuovi degli strati, li ho
eseguiti io nel container):
```powershell
cd fase11-visure
.\.venv\Scripts\python -m pytest -q tests
.\.venv\Scripts\python avviatore\costruisci_pacchetto.py
(Get-FileHash dist\visure-0.1.0.zip -Algorithm SHA256).Hash.ToLower()
cd ..
```
Cosa aspettarsi: `78 passed` (qualche `skipped` senza node o Chromium va bene); l'impronta è
`3fc84c6ae60536a1554ef6af225cd0ff57eea3c4cbda83171a296f5410a80851`, la stessa della build verde.

Cosa fare se va male: impronta diversa = sono cambiati `visure/` o `edifici3d/importa.py`/`__init__.py`: fermati e mandami
`git status fase11-visure fase10-edifici3d/edifici3d`.

**D5. [PC]** Fase 2, modulo UNI privato e segreti fuori da git (come C5):
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x
git ls-files fase2-gradi-giorno fase10-edifici3d/uni_privato
```
Cosa aspettarsi: quattro righe `.gitignore:…`; dal secondo comando **nessuna riga**.

### Parte 2 – PC: pacchetti e copia

**D6. [PC]** Pacchetto del codice del server (stesso comando di C6):
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=.venv-build --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude=uni_privato --exclude=node_modules .dockerignore fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d
dir ..\codice.tar.gz
tar -tzf ..\codice.tar.gz | Select-String -Pattern "uni_privato|fase2|(^|/)\.env$|\.venv"
tar -tzf ..\codice.tar.gz | Select-String -Pattern "strati"
```
Cosa aspettarsi: meno di 5 MB; il terzo comando **nessuna riga**; il quarto almeno tre righe (`servizio/strati.py`,
`ortofoto/strati/catasto.toml`, `ortofoto/strati/edifici.toml`).

**D7. [PC]** Pacchetto del sito `?v=20261105b`:
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
dir ..\sito.tar.gz
```
Cosa aspettarsi: l'ora di adesso, circa 5 MB.

**D8. [PC]** Copia sul server dei due pacchetti e dell'archivio di prova degli edifici (che hai scaricato accanto allo zip):
```powershell
dir ..\edifici_rimini_prova_2026-11-05.tar.gz
scp ..\codice.tar.gz ..\sito.tar.gz ..\edifici_rimini_prova_2026-11-05.tar.gz eugenio:~/
```
Cosa aspettarsi: l'archivio è di circa 0,9 MB; tre righe con `100%`.

### Parte 3 – Server

**D9. [Server]** Copia di sicurezza (nome **nuovo**: `…20261105b` è già quella del mattino) e codice nuovo:
```bash
cp -a ~/energia ~/energia_prima_20261105c
crontab -l > ~/crontab_prima_20261105c.txt; wc -l ~/crontab_prima_20261105c.txt
tar -xzmf ~/codice.tar.gz -C ~/energia && ls ~/energia/fase10-edifici3d/ortofoto/strati
test -d ~/energia/fase10-edifici3d/uni_privato && echo PRESENTE || echo assente
```
Cosa aspettarsi: `1 …crontab_prima_20261105c.txt`; `catasto.toml  edifici.toml`; `assente`.

Cosa fare se va male: se `cp` dice che la cartella esiste, usa `~/energia_prima_20261105d`.

**D10. [Server]** Rebuild dell'api, poi il worker (stessa immagine), poi l'immagine della pipeline degli edifici:
```bash
cd ~/energia/fase4-server && docker compose up -d --build api
docker compose up -d worker
docker compose --profile edifici build edifici-lidar
docker compose ps api worker
```
Cosa aspettarsi: l'api finisce con `Started`; la build di `energia-edifici` finisce con `Built` (o `naming to …`); dopo circa
un minuto `docker compose ps` mostra `api` `Up … (healthy)` e `worker` `Up`, tutti e due con IMAGE `energia-api` (non
`sha256:…`).

Cosa fare se va male: api non `healthy` dopo 2 minuti: `docker compose logs --tail 40 api` e mandami le righe. Per tornare
indietro: `rm -rf ~/energia && mv ~/energia_prima_20261105c ~/energia && cd ~/energia/fase4-server && docker compose up -d --build api && docker compose up -d worker`.

**D11. [Server]** Strati dal vivo, dentro l'api (uno alla volta):
```bash
docker compose exec -T api python -c "import urllib.request as u, json; print([s['id'] for s in json.load(u.urlopen('http://localhost:8000/api/ortofoto/strati'))['strati']])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/strati/catasto/18/140223/95259.png'); print(r.status, r.headers['Content-Type'], len(r.read()))"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/strati/dbtr_edifici/18/140223/95259.png'); print(r.status, r.headers['Content-Type'], len(r.read()))"
docker compose exec -T api python -c "import urllib.request as u, json; r=u.urlopen('http://localhost:8000/api/ortofoto/strati/osm_edifici/16/35055/23814.json'); print(r.status, len(json.load(r)['features']))"
```
Cosa aspettarsi: `['catasto', 'dbtr_edifici', 'osm_edifici']` (in quest'ordine o con `dbtr_edifici` prima); due righe
`200 image/png …` con qualche migliaio di byte; per OSM `200` e un numero di edifici maggiore di 0 (centro di Rimini).

Cosa fare se va male: `HTTP Error 502` sulle particelle o sul DBTR = il servizio della fonte non risponde dal server:
riprova tra qualche minuto e mandami `docker compose logs --tail 20 api`. `502` su **OSM** = Overpass non risponde dal
server (dal container di sviluppo era irraggiungibile): non blocca nulla, la pagina dice che le sagome OSM non sono
arrivate; se resta così, spegni solo quello strato aggiungendo `STRATI_SPENTI=osm_edifici` al `.env` e rifacendo
`docker compose up -d api`. `HTTP Error 429` = limite per indirizzo: aspetta un'ora.

Nota del 06/11/2026: dal server `overpass-api.de` rispondeva `502` (sovraccarico) e alla prova successiva `200` in ~15 s;
`maps.mail.ru` `200` in ~10 s; `overpass.private.coffee` e `overpass.kumi.systems` nessuna risposta in 30 s. Da questo
pacchetto lo strato prova anche l'istanza di riserva (`url_riserva` nel TOML) e aspetta fino a 45 s. Se avevi aggiunto
`STRATI_SPENTI=osm_edifici` al `.env`, toglilo (`sed -i '/^STRATI_SPENTI=osm_edifici$/d' .env`) e rifai
`docker compose up -d api worker`.

**D12. [Server]** Sito nuovo e controlli:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261105b /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/ortofoto.html /srv/energia/sito/indicatori.html /srv/energia/sito/interno/edifici.html
ls -l /srv/energia/sito/cerca_luogo.js /srv/energia/sito/strati_gl.js
grep -c "Costi energetici Sanità" /srv/energia/sito/indicatori.html
grep -c 'id="esci-demo"' /srv/energia/sito/modelli3d.html
```
Cosa aspettarsi: cinque righe `…:N` con N maggiore di 0; i due file nuovi; un numero maggiore di 0; `1`. Caddy serve subito
i file: **non** va riavviato.

**D13. [Server]** Archivio di prova degli edifici (centro di Rimini, OpenStreetMap ODbL + DTM RER CC BY):
```bash
grep CARTELLA_EDIFICI ~/energia/fase4-server/.env || echo "predefinita: /srv/energia/dati/edifici"
test -e /srv/energia/dati/edifici/archivi.json && echo "archivi.json PRESENTE" || echo "archivi.json assente"
tar -xzf ~/edifici_rimini_prova_2026-11-05.tar.gz -C /srv/energia/dati/edifici && ls /srv/energia/dati/edifici /srv/energia/dati/edifici/odbl/rimini-prova/prodotti
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://caddy/edifici3d/archivi.json'); print(r.status, r.headers['Content-Type'])"
```
(se il primo comando stampa una cartella diversa, usa quella al posto di `/srv/energia/dati/edifici` nei comandi seguenti)
Cosa aspettarsi: `archivi.json assente` (se dice PRESENTE fermati e mandami `cat /srv/energia/dati/edifici/archivi.json`:
va unito a mano); `ls` mostra `LEGGIMI_ARCHIVIO_PROVA.txt  archivi.json  odbl` (più quello che c'era) e `contesto
corpi.pmtiles  dtm_cog.tif  indice.json  terreno.pmtiles`; l'ultimo comando (dall'api verso Caddy, nella rete Docker;
si è ancora in `~/energia/fase4-server`) `200 application/json`.

Cosa fare se va male: `404` = Caddy non vede la cartella: `docker compose exec caddy ls /srv/edifici3d` deve mostrare
`archivi.json`; per togliere l'archivio di prova: `rm -r /srv/energia/dati/edifici/odbl/rimini-prova /srv/energia/dati/edifici/archivi.json /srv/energia/dati/edifici/LEGGIMI_ARCHIVIO_PROVA.txt`.

**D14. [Server] Crontab** (dopo ogni pubblicazione):
```bash
crontab -l
```
Cosa aspettarsi: **una sola riga**, `edifici-lidar` alle 3:30. Se ce ne sono altre: come C14 (mai `| crontab -` senza
partire da `crontab -l`).

**D15. [Server]** Pulizia:
```bash
rm ~/codice.tar.gz ~/sito.tar.gz ~/edifici_rimini_prova_2026-11-05.tar.gz
exit
```
Tieni `~/energia_prima_20261105c` qualche giorno (e cancella `~/energia_prima_20261105b` quando tutto funziona).

### Parte 4 – Prove nel browser (Ctrl+F5 sulla prima pagina; F12 → Console)

**D16. [Browser]**
1. **Menu**: nella barra c'è il sesto gruppo **Statistiche** (tendina con «Costi energetici Sanità», senza etichetta);
   «Indicatori» non è più tra le pagine in alto a destra. Fissa Patrimonio (clic sul titolo): nella riga nera «Ortofoto **S**»,
   «LiDAR ⚠» (triangolo giallo), «Modelli 3D **S**»; col mouse sopra compare «sperimentale» / «in sviluppo». Fissa
   Cogenerazione: le voci in attesa hanno **GME** (non cliccabili). Prova anche col tema chiaro (◐) e un altro vestito (✱).
2. **Costi energetici Sanità** (`indicatori.html`): titolo «Costi energetici Sanità», sopra «Statistiche», niente avviso
   «Servizio sperimentale».
3. **Ortofoto**: scrivi «via Gambalunga 27» e «Rimini» → «Cerca l'indirizzo»: la mappa va sul punto (pallino) a zoom 18.
   A destra, «Strati sopra la foto»: spunta **Confini delle particelle catastali** (linee e numeri gialli) e **Contorni degli
   edifici** (azzurri, DBTR); sotto la mappa la legenda con le fonti. **JPG** con la fonte Sentinel-2 (scegli «Sentinel-2
   cloudless» e rimpicciolisci a zoom 13): in Chrome/Edge si apre **«Salva con nome»**; salva e il messaggio dice «Immagine
   salvata: … (… kB)». Il file c'è nella cartella scelta e sotto la foto ha le righe di licenza (particelle, edifici, punto
   cercato). Con Firefox il messaggio dice «Download avviato…» con il collegamento «Salva …» (se il file non compare tra i
   download, il clic su quel collegamento lo salva). «Annulla» nella finestra = «Salvataggio annullato».
4. **Modelli 3D**: cerca «via Gambalunga 27» / «Rimini»: con l'archivio di prova l'edificio OSM del punto si colora e
   compare «Edificio … scelto nel punto trovato». **Trascina il pallino** su un altro edificio: la mappa non si sposta,
   l'edificio scelto cambia («Punto spostato in …»). Da vicino un clic fuori dagli edifici sposta il pallino. «Livelli della
   mappa»: togli e rimetti **Ortofoto**, **particelle**, **contorni**; la legenda segue. **Genera il 3D** → vista 3D (fonte per
   corpo «stima» per le altezze OSM mancanti) → **PNG** e **PDF** (con «Salva con nome» in Chrome). **Torna alla mappa 2D**.
5. **Demo**: apri `modelli3d.html?archivio=demo` (il pulsante «Prova la demo sintetica» compare solo quando sul server
   non c'è nessun archivio di edifici; con l'archivio di prova non c'è) → c'è **Esci dalla demo**; Genera il 3D su E-DEMO → «Torna alla mappa 2D» resta nella
   demo; **Esci dalla demo** riapre la mappa vera con ortofoto, strati e ricerca.
6. Console: nessuna riga rossa, a parte i 404 di `/edifici3d/cc-by/er/prodotti/indice.json` (il DBTR non è ancora sul
   server) e delle rotte `/api/edifici/…` dove il meteo manca.

Cosa fare se va male: pagina vecchia = Ctrl+F5 o Cloudflare **Caching → Configuration → Purge Everything**; il download
non parte nemmeno col collegamento «Salva …»: mandami browser e versione e il testo del messaggio sotto i pulsanti; strati
vuoti: F12 → Rete, filtra `strati`, e mandami il codice delle risposte.

### Parte 5 – Un solo commit e push per tutto il 05/11

**D17. [PC]** Nel clone (l'archivio di prova **non** è nel clone: sta solo sul server):
```powershell
git add -A
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_rimini_prova|\.pmtiles$"
git commit -m "05/11/2026: edifici fuori ER; affinamenti Edificio; Emissioni ISPRA, LEED descrittiva, analisi 7, 9, 13 pubbliche; valutazione Zornade; Ortofoto con confini, contesto, avvisi, minimappa e immagine; Modelli 3D in due tempi; demo mai sopra le foto vere; pagina interna 'in attesa'; Code signing policy di EuGEnio Visure; seconda pubblicazione: download delle immagini verificato (Salva con nome), ricerca in Ortofoto, punto trascinabile, Esci dalla demo, particelle catastali AdE e contorni edifici dal proxy, comandi osm-campione e dtm-wcs, menu con S/GME/triangolo e gruppo Statistiche (Costi energetici Sanità); sito ?v=20261105b"
git push
git log --oneline -2
```
Cosa aspettarsi: il secondo comando **non stampa nulla** (i `.pmtiles` della demo in `fase5-sito/sito/dati/edifici3d/`
erano già nel repository: se compaiono **solo** quelli come `M`, va bene); il push finisce con `… main -> main`; il log
mostra il commit nuovo sopra quello della codifica.

Cosa fare se va male: se il secondo comando stampa file da escludere, `git restore --staged <percorso>` e dimmelo; push
rifiutato: `git pull --rebase` e di nuovo `git push`. Il push non avvia la build di EuGEnio Visure.

---

## Procedura cumulativa C1–C17 (fatta la mattina del 05/11 fino a C16; C17 sostituito da D17)

**Correzione già fatta in fase 11 (05/11/2026, dal coordinatore)**: `avviatore/costruisci_pacchetto.py` usa ZIP_STORED
(con zlib e zlib-ng le impronte erano diverse tra Windows e Linux); impronta della 0.1.0 allora `4540d527…`; `test_abbina.py` legge l'uscita di node in UTF-8.

**Seconda correzione di fase 11 (05/11/2026, `.exe` fallito su GitHub Actions)**: con l'uscita rediretta Windows usa
cp1252 e `EuGEnioVisure.exe modello …` si fermava con `UnicodeEncodeError` sul carattere «→». Ora avviatore (prima di
`freeze_support`, quindi anche nei processi figli con «spawn»), `visure/__main__.py` e il processo figlio di
`edifici3d/importa.py` scrivono in UTF-8 con `errors="replace"`; test nuovo `tests/test_codifica.py` (comandi con
`PYTHONIOENCODING=cp1252` e uscita in una pipe); azioni del workflow `visure-windows.yml` aggiornate a versioni correnti
fissate allo SHA del commit (Node 24). **Impronta nuova della 0.1.0 =
`3fc84c6ae60536a1554ef6af225cd0ff57eea3c4cbda83171a296f5410a80851`** in `versioni_approvate.json` e in
`PUBBLICAZIONE_2026-11-04.md`. Questa correzione va su GitHub **con un commit a parte, prima** della procedura qui sotto
(push dell'utente del 05/11): il clone ha già workflow, avviatore, `visure/__main__.py`, `importa.py` e `test_codifica.py`.
Gli altri lavori di oggi non toccano `visure/`, `edifici3d/__init__.py` né `edifici3d/importa.py`: l'impronta resta valida.

### Testo originale della procedura cumulativa (dallo stato online `?v=20261104c`)

Vale per **tutti** i lavori del 05/11/2026 insieme: blocchi 1–4, blocco 5 (Ortofoto, Modelli 3D in due tempi, edifici
«storti», pagina interna) e le correzioni di EuGEnio Visure. Si parte da qui:
- online c'è il sito **`?v=20261104c`**, pubblicato nella notte con `PUBBLICAZIONE_2026-11-04.md` (procedura completa
  fatta, commit «Pubblicazione del 03-04/11/2026 …» su GitHub);
- su GitHub c'è già il **commit a parte** della correzione della codifica di EuGEnio Visure (workflow, `avviatore.py`,
  `visure/__main__.py`, `edifici3d/importa.py`, `tests/test_codifica.py`, impronta `3fc84c6a…`), con la build verde.

Etichette come in `PUBBLICAZIONE_2026-11-04.md`: **[PC]** PowerShell sul PC, **[Server]** terminale dopo `ssh eugenio`,
**[Browser]** il sito con Ctrl+F5 sulla prima pagina. Un'azione per passo. Nessun valore segreto va scritto qui, nei
documenti o nei messaggi.

### Parte 1 – PC: clone, zip e controlli

**C1. [PC]** Entra nel clone, controlla che sia pulito e allineato a GitHub (con il commit della codifica):
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git status
git pull --ff-only
git log --oneline -3
```
Cosa aspettarsi:
- `git status`: `nothing to commit, working tree clean`;
- `git pull`: `Already up to date.` oppure l'elenco dei file del commit della codifica, se l'avevi fatto da un'altra
  cartella;
- tra le tre righe del log c'è il commit della correzione della codifica e, sotto, «Pubblicazione del 03-04/11/2026 …».

Cosa fare se va male: se `git status` elenca dei file, fermati (lo zip li sovrascrive) e dimmi quali sono; se
`git pull` dice `Not possible to fast-forward`, fermati e mandami le righe.

**C2. [PC]** Controlla lo zip ed estrailo nel clone. `.git`, `.env`, `fase2-gradi-giorno` e `iscrizioni` non sono nello
zip e restano come sono:
```powershell
dir ..\eugenio_2026-11-05.zip
Expand-Archive -Path ..\eugenio_2026-11-05.zip -DestinationPath . -Force
git status --short | Measure-Object
git status --short fase11-visure .github
```
Cosa aspettarsi:
- lo zip ha la data del 05/11/2026 e l'ora più recente di quelli che hai;
- un `Count` di qualche decina (blocchi 1–5 e documenti);
- l'ultimo comando elenca solo `fase11-visure/README.md`, `fase11-visure/tests/test_metadati_exe.py` (nuovo, `??`) e
  `.github/workflows/visure-windows.yml` (testo della release con la «Code signing policy»). **Non** devono comparire
  `fase11-visure/visure/…` né `fase11-visure/avviatore/avviatore.py`: sono già nel commit della codifica.

Cosa fare se va male: se compaiono file di `fase11-visure/visure/`, lo zip non è quello giusto o il clone non ha il commit
della codifica: fermati (l'impronta del pacchetto cambierebbe). Se `Expand-Archive` dà errore, usa «Estrai tutto» di
Esplora file sulla cartella `eugenio` con «Sostituisci i file».

**C3. [PC]** Pagine del sito già rigenerate (il primo comando non scrive nulla) e test della fase 5:
```powershell
cd fase5-sito
python costruisci_pagine.py --controlla
python -m pytest -q tests
cd ..
```
Cosa aspettarsi: `versione 20261105a: 0 file da rigenerare`; poi `33 passed`. Senza Playwright e Chromium sul PC i 6 test
nel browser si saltano: `27 passed, 6 skipped` va bene; senza node si salta anche qualche test di calcolo.

Cosa fare se va male: se il primo comando elenca file da rigenerare, lo zip non è estratto del tutto (rifai C2); se un
test fallisce, mandami le ultime 30 righe.

**C4. [PC]** Test di EuGEnio Visure (stesso ambiente del passo 5 del 04/11):
```powershell
cd fase11-visure
.\.venv\Scripts\python -m pytest -q tests
.\.venv\Scripts\python avviatore\costruisci_pacchetto.py
(Get-FileHash dist\visure-0.1.0.zip -Algorithm SHA256).Hash.ToLower()
cd ..
```
Cosa aspettarsi: `78 passed` (qualche `skipped` senza node o Chromium va bene); l'impronta è
`3fc84c6ae60536a1554ef6af225cd0ff57eea3c4cbda83171a296f5410a80851`, la stessa della build verde.

Cosa fare se va male: un'impronta diversa vuol dire che sono cambiati file di `visure/` o di `edifici3d/importa.py` o
`__init__.py`: fermati e mandami `git status fase11-visure fase10-edifici3d/edifici3d`.

**C5. [PC]** Fase 2, modulo UNI privato e segreti fuori da git (come al passo 8 del 04/11):
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x
git ls-files fase2-gradi-giorno fase10-edifici3d/uni_privato
```
Cosa aspettarsi: quattro righe `.gitignore:…`; dal secondo comando **nessuna riga**.

### Parte 2 – PC: pacchetti e copia sul server

**C6. [PC]** Pacchetto del **codice del server** (fasi 3, 4, 6–10 e `.dockerignore`, senza fase 2, modulo privato,
ambienti e `.env`):
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=.venv-build --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude=uni_privato --exclude=node_modules .dockerignore fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d
dir ..\codice.tar.gz
tar -tzf ..\codice.tar.gz | Select-String -Pattern "uni_privato|fase2|(^|/)\.env$|\.venv"
```
Cosa aspettarsi: un file di pochi MB (meno di 5); l'ultimo comando non stampa **nulla**.

Cosa fare se va male: se stampa qualcosa o il file è molto più grande, fermati e dimmelo.

**C7. [PC]** Pacchetto del **sito** `?v=20261105a` (senza `dati/indicatori`, che il server rifà da sé):
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
dir ..\sito.tar.gz
```
Cosa aspettarsi: l'ora di adesso, circa 5 MB.

**C8. [PC]** Copia dei due pacchetti sul server:
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Per ognuno compare una riga con `100%`.

### Parte 3 – Server

**C9. [Server]** Copia di sicurezza del codice **e del crontab**, poi il codice nuovo:
```bash
cp -a ~/energia ~/energia_prima_20261105b
crontab -l > ~/crontab_prima_20261105b.txt; wc -l ~/crontab_prima_20261105b.txt
tar -xzmf ~/codice.tar.gz -C ~/energia && ls ~/energia
test -d ~/energia/fase10-edifici3d/uni_privato && echo PRESENTE || echo assente
```
Cosa aspettarsi: il numero di righe del crontab (almeno 4, vedi C14); `ls` elenca anche `fase10-edifici3d`; l'ultimo
comando stampa `assente`.

Cosa fare se va male: se `cp` dice che la cartella esiste già, usa un altro nome (es. `~/energia_prima_20261105c`).

**C10. [Server]** Immagine della pipeline degli edifici (blocchi 1 e 2) e **rebuild dell'api** (testo del report sul
modello del cielo, analisi 7, 9 e 13 pubbliche, stato «in attesa» della pagina interna):
```bash
cd ~/energia/fase4-server && docker compose --profile edifici build edifici-lidar && docker compose up -d --build api
docker compose up -d worker
docker compose ps api worker
```
Il worker usa la stessa immagine dell'api: va ricreato a ogni rebuild, altrimenti continua col codice vecchio (in
`docker compose ps` la colonna IMAGE deve dire `energia-api` per tutti e due, non `sha256:…`).
Cosa aspettarsi: l'immagine finisce con `Built` (o `naming to … energia-edifici`); dopo circa un minuto `docker compose ps
api` mostra `Up … (healthy)`.

Cosa fare se va male: se l'api non diventa `healthy`, `docker compose logs --tail 40 api` e mandami le ultime righe; per
tornare indietro: `rm -rf ~/energia && mv ~/energia_prima_20261105b ~/energia && cd ~/energia/fase4-server && docker compose up -d --build api`.

**C11. [Server]** Controlli dentro l'api, uno alla volta:
```bash
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/salute').read()[-60:])"
docker compose exec -T api grep -c "def situazione" /app/servizio/interno.py
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/analisi/stato').read()[:200])"
```
Cosa aspettarsi: un testo che finisce con `"previsioni_in_corso": 0}`; `1`; un testo con le analisi 7, 9 e 13
`"disponibile":true` (le altre `false`, il modulo UNI non c'è).

**C12. [Server]** Sito nuovo e controlli:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261105a /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/ortofoto.html /srv/energia/sito/interno/edifici.html
ls -l /srv/energia/sito/confini_gl.js /srv/energia/sito/esporta_mappa.js
grep -c 'id="genera-3d"' /srv/energia/sito/modelli3d.html /srv/energia/sito/fv-producibilita.html
grep -c "Code signing policy" /srv/energia/sito/visure.html
ls /srv/energia/sito/dati/edifici3d/lidar/alberi | head -3
```
Cosa aspettarsi:
- quattro righe `…:N` con N maggiore di 0;
- i due file nuovi;
- `modelli3d.html:1` e `fv-producibilita.html:0` (il flusso in due tempi è solo in Modelli 3D);
- `1`;
- almeno un file `.json` degli alberi della demo.

Caddy serve subito i file statici: **non** serve riavviarlo.

**C13. [Server]** Modulo UNI privato: se `/srv/energia/dati/uni_privato` **non** c'è (rinviato il 04/11), niente da fare.
Se c'è, sostituiscilo con quello dello zip privato del 05/11 (blocco 3), dopo `scp ..\eugenio_uni_privato_2026-11-05.zip
eugenio:~/` dal PC:
```bash
test -d /srv/energia/dati/uni_privato && echo PRESENTE || echo assente
rm -rf /srv/energia/dati/uni_privato_vecchio && mv /srv/energia/dati/uni_privato /srv/energia/dati/uni_privato_vecchio
unzip -q ~/eugenio_uni_privato_2026-11-05.zip -d /tmp/up && mv /tmp/up/fase10-edifici3d/uni_privato /srv/energia/dati/uni_privato
```
(il secondo e il terzo comando solo se il primo stampa `PRESENTE`).

**C14. [Server] Controllo del crontab** (da fare dopo **ogni** pubblicazione):
```bash
crontab -l
```
Cosa aspettarsi: **una sola riga**, quella di `edifici-lidar` alle 3:30. Mercati, previsioni, storico, indicatori e clima
li fa il worker (`cat /srv/energia/dati/worker_stato.json` mostra l'ultimo giorno di ciascuno).

Cosa fare se va male: se compaiono righe `servizio.worker …`, sono doppioni del worker: toglile partendo da `crontab -l`
(copia prima, poi `grep -v` in un file, controllo con `cat`, infine `crontab <file>`), **mai** con `… | crontab -`.

**C15. [Server]** Pulizia:
```bash
rm ~/codice.tar.gz ~/sito.tar.gz
exit
```
Tieni `~/energia_prima_20261105b` qualche giorno; quando tutto funziona: `rm -rf ~/energia_prima_20261105b`.

### Parte 4 – Prove nel browser (Ctrl+F5 sulla prima pagina; F12 → Console)

**C16. [Browser]** Le prove dei blocchi 2 e 3 (sezioni qui sotto, «Prove nel browser»), più queste:
1. **Ortofoto** (`ortofoto.html`): in alto a destra la piccola mappa d'Italia. Rimpicciolisci fino a vedere la regione
   (zoom sotto 12): resta il contesto Sentinel-2 con i confini di regioni e province, e in alto a sinistra l'avviso «…si
   vede dallo zoom 12: avvicinati…». Ingrandisci al massimo: l'immagine resta (ingrandita) con l'avviso «Oltre lo zoom
   20…». Clic sulla Toscana nella piccola mappa: la mappa va lì e la regione ha il bordo colorato; secondo clic: si torna
   all'Italia. Da zoom 9–15 un clic su un comune lo inquadra (secondo clic lo toglie). Sotto la mappa «Scarica
   l'immagine: JPG PNG PDF»: il file ha sotto la vista licenza e citazione dell'ortofoto, i confini ISTAT e «Fonte:
   EuGEnio». Con la fonte «Geoportale Nazionale» il download si rifiuta con un messaggio.
2. **Modelli 3D** (`modelli3d.html`): si apre la mappa **2D** dell'Emilia-Romagna con la piccola mappa, i confini e
   l'ortofoto; il messaggio a destra dice che l'archivio degli edifici non è ancora sul server e compare **«Prova la demo
   sintetica»**. Prova la ricerca: «via Gambalunga 27» / «Rimini» → «Cerca l'indirizzo»: la mappa va sul punto (con
   l'archivio vero sceglie anche l'edificio). Poi «Prova la demo sintetica»: isolato inventato **senza** foto sotto (il
   selettore dello sfondo dice «nessuna: la demo sintetica non va sopra le foto vere»); clic su E-DEMO → evidenziato →
   **Genera il 3D**: vista 3D con la barra «Zoom · Vista · Ruota · Inclina · Rollio», la riga «Fonte del 3D per corpo…»,
   «Scarica l'immagine» e **Torna alla mappa 2D**. Ctrl+trascinamento ruota e inclina, doppio clic torna alla vista 3D,
   con la mappa selezionata Ctrl+frecce ruotano. Torna alla mappa 2D: un altro clic sceglie un altro edificio.
3. **Patrimonio › Visure**: in fondo le sezioni «Disinstallare» e «Code signing policy».
4. **Pagina interna** (`/interno/edifici.html`, con Cloudflare Access): Rimini dice «In attesa: nessuna fonte DSM o LAS
   attiva e 0 corpi della Fase A (manca prepara).», non più «Zona in corso».
5. Console: nessuna riga rossa, a parte i 404 di `/edifici3d/archivi.json`, `/edifici3d/cc-by/er/prodotti/indice.json` e
   delle rotte `/api/edifici/…` finché archivio e meteo non sono sul server.

Cosa fare se va male: se una pagina sembra quella vecchia, Ctrl+F5 di nuovo o in Cloudflare **Caching → Configuration →
Purge Everything**; se la mappa resta bianca, F12 → Console e mandami le righe rosse.

### Parte 5 – Commit e push

**C17. [PC]** Nel clone:
```powershell
git add -A
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI"
git commit -m "05/11/2026: edifici fuori ER; affinamenti Edificio; Emissioni ISPRA, LEED descrittiva, analisi 7, 9, 13 pubbliche; valutazione Zornade; Ortofoto con confini, contesto, avvisi, minimappa e immagine; Modelli 3D in due tempi (2D, ricerca, Genera il 3D, fonti per corpo); demo sintetica mai sopra le foto vere; pagina interna 'in attesa'; Code signing policy di EuGEnio Visure; sito ?v=20261105a"
git push
```
Cosa aspettarsi: il secondo comando non stampa **nulla**; il push finisce con `abc1234..def5678  main -> main`.

Cosa fare se va male: se il secondo comando stampa qualcosa, togli quei file con `git restore --staged <percorso>` e
dimmelo; se il push è rifiutato, `git pull --rebase` e di nuovo `git push`. Il push modifica il workflow
`visure-windows.yml` solo nel testo della release: **non** avvia una build (parte con un tag, una pull request o a mano).

### Dopo la pubblicazione (da fare a mano, quando vuoi)

- EuGEnio Visure: domanda a **SignPath Foundation** (la pagina `visure.html#code-signing-policy` e il README della fase 11
  hanno la sezione richiesta), poi il tag `visure-v0.1.0` quando vorrai distribuirlo.
- Per una prima zona fuori ER, `prepara-regione` dal server; `lidar-corpi` su qualche tessera di Bolzano (blocchi 1 e 2).

---

## Blocco 1 – Edifici fuori dall'Emilia-Romagna

### Cosa è cambiato

- **Adattatori dei DB topografici → corpi** (`fase10-edifici3d/edifici3d/regionali.py`, stesso modello per corpo della
  fase 10) per le tre regioni con edifici attivi in `fonti/regioni.toml`:
  - **Lombardia, DBGT 020101 Unità volumetrica**: altezza `UN_VOL_AV`, edificio `CEDIUV`, terreno `UN_VOL_QE − UN_VOL_AV`
    (nelle porzioni «03» la base sta 3,5 m sotto terra);
  - **FVG, Edificato CTRN**: `ALTEZZA`, `QUOTA_PIEDE`, `QUOTA_GRONDA` (EPSG:6708), uno strato per foglio;
  - **Liguria, CTR 3D**: z di gronda − DTM 2023 (il DTM serve; WCS provato).
  Prove dal vivo su piccoli campioni (60 volumi a Milano, 22 elementi in FVG, 14 edifici in Liguria), con coerenza delle
  quote controllata; i campioni di prova sono in `tests/dati/` con la fonte. Comandi `regionale-campione`,
  `controlla-regione`, `prepara-regione`; TOML `fonti/lombardia.toml`, `fonti/friuli_venezia_giulia.toml`, `fonti/liguria.toml`.
- **Zone LiDAR fuori ER**: `zone/bolzano.toml` (DSM e DTM 0,5 m via WCS, CC0, chiesti a 1 m, DTM 2,5 m per i vuoti) e
  `zone/trento.toml` (DSM e DTM 1 m 2006-09, 1410 file per modello: indice in `zone/coperture/trento_pat_lidar_2009.json`
  costruito dalle sole intestazioni). Senza corpi della Fase A restano «in attesa» e `--zona auto` le salta.
- **Pipeline**: copertura per fonte (`[fonti.<id>.copertura]`: riquadri o maschera, quota minima degli edifici dentro),
  fonti a più file con indice e mosaico, DTM composto da più fonti; comandi `lidar-copertura` e `lidar-indice`.
- **DSM della costa 2019 acceso** in `zone/rimini.toml`, solo sulle tessere coperte dalla maschera
  `zone/coperture/rimini_rer_dsm_costa_2019.geojson` (27,8 km², fatta con una sola richiesta a 50 m), con priorità più
  bassa delle fonti RER 2023-24.
- `fonti/regioni.toml`: prove del 05/11 e `usata_in` per le fonti ora usate; conteggi invariati (17/48/19).

File toccati: `fase10-edifici3d/` (`edifici3d/regionali.py`, `edifici3d/coperture.py`, `edifici3d/pipeline.py`,
`edifici3d/__main__.py`, `fonti/*.toml`, `zone/*.toml`, `zone/coperture/`, `tests/test_regionali.py`, `tests/dati/`,
`tests/test_fase_c.py`, `README.md`). **Nessun file del sito**, nessuna modifica dell'api.

### Pubblicazione (blocco 1)

C6, C8, C9 e C10 della procedura cumulativa: codice nuovo sul server e immagine `energia-edifici` ricostruita. Il blocco 1 da solo
non richiede il rebuild dell'api né il pacchetto del sito (li chiede il blocco 2). Il cron delle 3:30 (Fase C) resta com'è: con i corpi della Fase A di Rimini sul server
la pipeline userà da sola il DSM della costa sulle tessere coperte.

### Prove (blocco 1)

- fase 10: tutti i test passano (15 nuovi in `tests/test_regionali.py`; `test_rimini_fonti_in_attesa` aggiornato perché il
  DSM della costa ora è acceso); fase 4: 150 test passano.

### Da fare a mano (blocco 1)

- Per una prima zona vera fuori ER: scaricare dal server il file ufficiale della Regione (o il servizio a pezzi con
  `regionale-campione`), poi `prepara-regione` (per la Liguria con il ritaglio del DTM 2023).
- Facoltativo: `python -m edifici3d lidar-indice --zona trento --fonte pat_dsm_2009` dal server, per controllare che
  l'indice non sia cambiato (riprende da dove era e aggiunge solo i file nuovi).

### Limiti noti (blocco 1)

- Edifici P.A.T. 3D (Trento) e BDTRE Piemonte: adattatori non scritti (lo zip di Trento è di 108 MB e non si legge a
  distanza; il Piemonte è irraggiungibile dal container). Bolzano non ha un DB topografico con altezze: le sue sagome
  verranno dai corpi del solo LiDAR (blocco 2) o da OSM (ODbL).
- Liguria: Gauss-Boaga → UTM con le trasformazioni predefinite di PROJ (errore dell'ordine del metro senza la griglia
  IGM); la z come quota di gronda è verificata su un punto, da confermare su un campione più ampio.

---

## Blocco 2 – Affinamenti Edificio

### Cosa è cambiato

- **Tabella 11 del DM requisiti minimi** (DM 26/6/2015, All. 1, App. A, § 2.1, nel testo del DM 28/10/2025; GU n. 283 del
  5/12/2025, pp. 39–40, letta il 05/11/2026 dal PDF della Gazzetta pubblicato dalla Regione FVG): H'T massimo per le
  ristrutturazioni importanti di primo livello, per zona e quota EX ANTE di superfici vetrate. Nel passo «Obblighi di
  legge» c'è il campo «Superfici vetrate»; se resta vuoto la quota è **stimata** dall'uso (finestre/pareti tipiche assunte
  da EuGEnio, segnate come stima nella pagina e nel report). Tra due colonne della tabella EuGEnio interpola in modo
  lineare (la norma non lo dice: scelta dichiarata); sotto il 9 % vale la prima colonna.
- **Trasposizione di Perez (1990)** al posto dell'isotropa per FV e facciate (circumsolare persa quando il sole è coperto
  dall'orizzonte del punto). Uguale a pvlib; confronto con PVGIS 5.3 su Rimini 2020: piano a 30° sud +0,8 % (isotropa
  −3,9 %), facciata sud +0,5 % (isotropa −7,4 %). Il report del tipo `edificio` dice quale trasposizione è stata usata.
- **Colonne `visura_…`**: nelle pagine dell'edificio (piani, superficie catastale, uso con la precedenza file → visura →
  stima) e in «Valori per sede» (superficie catastale come base dei consumi al m², segnata «v»; le colonne `visura_…` non
  diventano più valori da disegnare).
- **Patrimonio → Modelli 3D**: pulsante «Apri in Modelli 3D» su ogni sede con le coordinate; la pagina 3D apre l'edificio
  che contiene il punto, con le colonne facoltative e le visure (dati nella memoria della scheda, mai al server).
- **Importa DXF/IFC – posa sulla sagoma**: clic sulla sagoma di un edificio dell'archivio; la pagina ruota e sposta il
  modello per farlo coincidere, dice la sovrapposizione e avvisa se le aree non tornano.
- **Corpi dal solo LiDAR** (§ 7: raggruppamento per altezza, comando `lidar-corpi`) per le zone senza sagome, e **alberi
  dal DSM** (ostacoli per le ombre di FV e facciate, in verde sulla mappa 3D; la pipeline li scrive in `lidar/alberi/`).

File toccati: `fase5-sito/` (`sito/edifici_calcoli.js`, `edificio3d.js`, `patrimonio.js`, `valori_sedi.js`,
`importa_modello.js`, `importa-dxf-ifc.html`, le 9 pagine 3D, `stile.css`, demo `dati/edifici3d/`, tutte le pagine per la
versione `?v=20261105a`, `tests/`), `fase10-edifici3d/` (`edifici3d/lidar_corpi.py`, `pipeline.py`, `__main__.py`, test),
`fase4-server/servizio/report_servizi.py` e `tests/test_edifici.py`, README delle fasi 5, 10 e 11.

### Pubblicazione (blocco 2)

C6–C12 della procedura cumulativa (con il rebuild dell'api al passo C10).

### Prove nel browser (blocco 2, Ctrl+F5)

1. Apri `https://eugenio.statocritico.it/edificio-obblighi.html`, scegli un edificio (sulla demo, se l'archivio vero non c'è
   ancora): nel passo 5 compaiono le righe «Superfici vetrate…» con «stima» e «H'T massimo per ristrutturazione importante
   di primo livello (intervento scelto)» con il rimando alla Tab. 11. Scrivi `30` nel campo «Superfici vetrate»: la riga
   dice «30 % (dato inserito)».
2. In `patrimonio.html` carica il file d'esempio: sotto ogni sede trovata compare «Apri in Modelli 3D». Con l'archivio vero
   di Rimini il pulsante apre l'edificio della sede; con la sola demo la pagina dice che nessun edificio contiene il punto.
3. In `importa-dxf-ifc.html` carica un DXF, scegli «agganciato alla sagoma…», fai clic su un contorno tratteggiato e poi
   «Posiziona il modello»: il messaggio dice rotazione e sovrapposizione.
4. In `fv-producibilita.html`, sulla demo, i tre alberi dell'isolato sono in verde e fanno ombra con l'animazione del giorno.
5. F12 → Console: nessuna riga rossa (a parte i 404 delle rotte `/api/edifici/…` se l'archivio meteo non c'è ancora).

### Prove (blocco 2)

- fase 5: 25 test (6 nuovi); fase 10: 90 (7 nuovi, 3 in Chromium); fase 4: 151 (1 nuovo); fase 11: 71; tutti passano.
- Prova a mano in Chromium headless delle pagine Obblighi di legge (con una sede del Patrimonio e la Tabella 11), Patrimonio,
  Importa DXF/IFC: nessun errore JavaScript.

### Da fare a mano (blocco 2)

- Con i dati veri: provare «Apri in Modelli 3D» sulle sedi AUSL (serve l'archivio UVL di Rimini sul server) e la posa sulla
  sagoma con un DXF/IFC vero.
- Dal server: `python -m edifici3d lidar-corpi --zona bolzano --archivio /srv/energia/dati/edifici --riquadro 677000 5151000 680000 5154000`
  (tre tessere del centro di Bolzano) e controllo dei corpi nella pagina 3D con `?archivio=cc-by/bz/prodotti`.

### Limiti noti (blocco 2)

- La quota vetrata stimata usa rapporti finestre/pareti tipici scelti da EuGEnio, non misurati: il limite della Tabella 11
  va ricontrollato con il rilievo (la pagina e il report lo dicono).
- Corpi dal solo LiDAR: due corpi a contatto con altezze simili (entro 1,25 m) restano uniti; tettoie e mezzi alti possono
  finire tra gli alberi; provati solo sul campione sintetico.
- Perez usa la diretta ricavata da GHI e DHI orari dell'archivio (come prima): gli scarti con PVGIS dipendono anche dai
  dati della radiazione, non solo dal modello.

---

## Blocco 3 – Analisi senza GME e senza UNI

### Cosa è cambiato

- **Cogenerazione › Emissioni** (report 18) non più segnaposto: CO₂ del cogeneratore contro l'alternativa separata (rete
  + caldaia), da dati misurati o dalla taglia, con i fattori di **ISPRA, Rapporto 430/2026** (Tabella 1.7 per la rete,
  2015 e 2020–2025, 2025 preliminare; Tabella 1.4 per il gas naturale), tabella di sensibilità con i quattro fattori della
  rete e «fattore della rete di pareggio». Dati di terzi in `fase13-cogenerazione/dati_terzi/` con licenza e fonte
  (copia nel sito). **Nessun dato GME o EEX**: niente prezzi, niente strategia economica; tutto nel browser.
- **Prefattibilità LEED** (`fv-leed.html`): pagina descrittiva, temi del sistema LEED (rinnovabili in sito, prestazione
  energetica, luce naturale e viste, isola di calore, resilienza) con parole nostre, collegati alle pagine di EuGEnio che
  danno i dati e a cosa manca. **Nessun testo, tabella o soglia LEED** (protetti dall'USGBC), nessun punteggio; limiti
  scritti nella pagina.
- **Analisi 7, 9 e 13 nel codice pubblico** (nessuna norma UNI coinvolta: statistica, geometria e definizioni degli atti):
  - 13 **Clima che cambia** (`edificio-clima.html`): tendenza dei gradi giorno dal 1940 (minimi quadrati, Theil–Sen,
    Mann–Kendall), valori 2030/2040/2050 con l'intervallo al 95 %, consumi attesi con la firma energetica;
  - 7 **Comunità energetiche** (`edificio-cer.html`): energia condivisa oraria per cabina primaria da un CSV dell'utente
    (con esempio inventato), nessun prezzo né incentivo; **perimetri delle cabine primarie con licenza compatibile non
    trovati** (solo GSE, CC BY-NC-SA 3.0 IT, esclusi): il codice della cabina lo scrive l'utente;
  - 9 **Cielo visibile** delle facciate (nuova colonna della tabella delle facciate nelle pagine 3D).
  Tolte dal modulo privato (`a07_cer.py`, `a09_cielo.py`, `a13_clima.py` e le tabelle vuote `profili_consumo_per_uso`,
  `parametri_cer`, `soglie_leed`, `parametri_tendenza`): nuovo `eugenio_uni_privato_2026-11-05.zip`. In
  `edifici3d/analisi.py` le tre analisi hanno `pubblica = True` (sempre disponibili, anche sui mirror; `POST
  /api/analisi/7|9|13` risponde 422 «si calcola nella sua pagina»).

Nessuna decisione di RIEPILOGO cambia: la decisione del 03/11/2026 mette nel modulo privato solo ciò che viene dalle norme
UNI, e le tre analisi non ne usano (lo spostamento era già previsto come possibile nel README della fase 10).

File toccati: `fase5-sito/` (`cog-emissioni.html`, `emissioni_cog.js`, `edificio-clima.html`, `edificio-cer.html`,
`fv-leed.html`, `analisi_pubbliche.js`, `edifici_calcoli.js`, `edificio3d.js`, `dati/ispra_fattori_emissione.json`,
`esempi/cer_esempio_sintetico.csv`, `stile.css`, `parti/testata.html` e tutte le pagine per il menu, test),
`fase13-cogenerazione/` (`dati_terzi/`, README), `fase10-edifici3d/edifici3d/analisi.py` e test,
`fase4-server/tests/test_analisi.py`; modulo privato (zip a parte).

### Pubblicazione (blocco 3)

Gli stessi C6–C12 della procedura cumulativa (rebuild dell'api: `edifici3d/analisi.py` è nell'immagine); il modulo privato al passo C13. Il modulo
privato sul server (`/srv/energia/dati/uni_privato`), se c'è già, si sostituisce con quello dello zip nuovo:
```bash
rm -rf /srv/energia/dati/uni_privato_vecchio && mv /srv/energia/dati/uni_privato /srv/energia/dati/uni_privato_vecchio
unzip -q ~/eugenio_uni_privato_2026-11-05.zip -d /tmp/up && mv /tmp/up/fase10-edifici3d/uni_privato /srv/energia/dati/uni_privato
```
(prima `scp ..\eugenio_uni_privato_2026-11-05.zip eugenio:~/` dal PC). Se il modulo privato non è ancora sul server
(rinviato il 04/11), niente da fare.

### Prove nel browser (blocco 3, Ctrl+F5)

1. `cog-emissioni.html`: «Calcola le emissioni» con i valori d'esempio → tabella, barre marroni e tabella con quattro
   fattori della rete; nessuna richiesta a `/api/` (F12 → Rete).
2. `edificio-clima.html`: scrivi «Rimini» (o `099014`) e «Calcola» → grafico dal 1940 con la tendenza e la tabella
   2030/2040/2050; con base e pendenza della firma compare il consumo atteso.
3. `edificio-cer.html`: «Prova con l'esempio» → due cabine di esempio e tre sedi.
4. `fv-leed.html`: tabella dei temi, nessun numero di soglia.
5. Menu Cogenerazione: «Emissioni» cliccabile con «sperimentale», le altre voci restano «licenza GME».

### Prove (blocco 3)

- fase 5: 27 test; fase 10: 92 (2 nuovi nel browser); modulo privato: 6 passano e 5 saltano; fase 4: 151; tutti passano.

### Limiti noti (blocco 3)

- Emissioni: fattori medi annui nazionali; il «fattore giusto» della rete dipende dalla domanda (la pagina mostra tutti
  quelli di ISPRA). Il rendimento della caldaia predefinito (90 %) è indicativo.
- CER: niente perimetri delle cabine, niente requisiti dei soci né incentivi.
- Clima che cambia: estrapolazioni della tendenza, non scenari climatici.

---

## Blocco 4 – Valutazione Zornade

### Cosa è cambiato

- Nuovo `documenti/VALUTAZIONE_ZORNADE.md`: cosa offre Zornade (API catastale già in uso, strato edifici OSM, altezze
  LiDAR annunciate), cosa abbiamo senza (DB topografici di 6 territori, LiDAR ER/Bolzano/Trento, corpi dal solo LiDAR,
  OSM, GHSL), tabella analisi per analisi del menu, licenza ODbL e termini del 18/09/2026, rischi e dipendenze,
  alternative e raccomandazione. **Il § 14.2 resta aperto**; nessuna email a Zornade.
- Raccomandazione in breve: le altezze di Zornade servono **solo** nelle regioni senza DB topografico con altezze né DSM
  aperto, e solo finché il LiDAR PNRR non è usabile direttamente; non servono in ER, Lombardia, FVG, Liguria, Trento e
  Bolzano, né per falde e FV dettagliato. Rispondere senza impegni sull'estratto ER, chiedendo licenza, colonne,
  copertura, data e costo delle altezze; decidere dopo il controllo del PST del 7/11.

Solo documenti: nessuna pubblicazione sul server (il file va nel commit della procedura cumulativa).

---

## Blocco 5 – Prove sul sito pubblicato: Ortofoto, Modelli 3D, edifici «storti» (05/11/2026)

Feedback di Paolo dopo le prove su `?v=20261104c`: in Ortofoto «non si vedono i confini delle regioni, quindi se ingrandisco
sparisce tutto», mancano la piccola mappa d'Italia e lo scaricamento dell'immagine; Modelli 3D «non ci capisco niente»
(serve la mappa 2D con ricerca e selezione, poi il 3D); edifici «storti» rispetto all'ortofoto.

### Ortofoto

- **Perché «sparisce tutto»**: le ortofoto regionali (RER, Toscana, Bolzano, Trento) hanno tessere solo dallo **zoom 12**
  al 20 e solo nel loro riquadro; la mappa aveva come sfondo un colore pieno e nessun altro strato, quindi sotto lo zoom
  12 (o fuori dal riquadro) restava tutto nero, senza confini né riferimenti. Le tessere RER fino allo zoom 20 rispondono
  (provato dal vivo il 05/11: 200 `image/jpeg` a 12–20, 404 sotto il 12 per scelta del proxy).
- Ora (`ortofoto.js`): sotto la fonte scelta c'è sempre il **contesto Sentinel-2 cloudless 2016** (zoom 5–15, poi
  ingrandito); oltre lo zoom massimo di una fonte MapLibre **ingrandisce l'ultimo livello** (mappa fino a 21); `bounds` del
  riquadro su ogni sorgente (niente richieste fuori zona); un **avviso sulla mappa** dice «…si vede dallo zoom 12:
  avvicinati», «non copre questa zona» o «Oltre lo zoom 20… è ingrandita» e cosa si vede al suo posto; finché non si
  sceglie a mano si usa sempre la fonte migliore che copre la zona.
- **Confini sempre visibili** (`confini_gl.js`, nuovo, comune a Ortofoto e Modelli 3D): regioni sempre (con un alone per
  leggerle sulle foto), province da zoom 7, comuni da zoom 9 delle regioni in vista. Stessi file delle altre mappe
  (`dati/mappa/italia.json` e `RR.json`: ISTAT, unità amministrative a fini statistici 2026, generalizzati, CC BY 4.0, via
  Gramscii), riportati in WGS84 con l'inversa di Gauss–Krüger (scarto sotto il metro rispetto a pyproj; i confini
  generalizzati hanno ~100 m di precisione): **nessun dato nuovo da ospitare**.
- **Piccola mappa d'Italia** in alto a destra (`minimappa.js`, come nelle altre pagine): clic su una regione = la mappa va
  lì (bordo colorato); **secondo clic** = la scelta si toglie e si torna all'Italia (aggancio nuovo
  `EUGENIO.suStessaRegione`, usato solo da Ortofoto e Modelli 3D; le altre pagine non cambiano). Sulla mappa grande: clic su
  una regione (zoom sotto 9) o su un comune (zoom 9–15, secondo clic lo toglie).
- **Scarica l'immagine** in JPG, PNG o PDF (`esporta_mappa.js`, nuovo, senza librerie: il PDF A4 orizzontale è scritto nel
  browser con l'immagine JPEG e il testo Helvetica): la vista così com'è, ridisegnata a densità doppia, con sotto **licenza
  e citazione** di ogni fonte visibile (ortofoto con lo stato «uso da confermare», contesto, edifici, confini ISTAT,
  MapLibre) e «Fonte: EuGEnio – eugenio.statocritico.it (CC BY 4.0)», nell'immagine e come testo nel PDF. Rifiutato per
  le fonti «solo consultazione dal vivo» (Geoportale Nazionale).
- La colonna della mappa scorre da sola sul computer (prima i contenuti in più restavano tagliati sotto la finestra).

### Modelli 3D in due tempi

- **1) Mappa 2D** (MapLibre): Italia e regione (piccola mappa, confini), zoom con la rotella e trascinamento; sotto, la
  migliore ortofoto della zona e il contesto Sentinel-2. **Ricerca per indirizzo** (via e civico, comune) **o per dati
  catastali** (comune, foglio, particella): una riga a `POST /api/patrimonio`, la stessa rotta della pagina Patrimonio
  (ANNCSU sul server, poi Zornade per quello che manca e per le particelle): **nessuna dipendenza nuova da Zornade**
  (`VALUTAZIONE_ZORNADE.md` e § 14.2 rispettati). Clic sull'edificio = evidenziato; clic sullo stesso = tolto.
- **2) «Genera il 3D»**: alzato dell'edificio e dell'intorno (250 m) con, per ogni corpo, la fonte più affidabile che c'è:
  **falde LiDAR → corpi dal LiDAR / DB topografico regionale con le altezze → modello importato DXF/IFC → OpenStreetMap →
  stima**. Archivi in `/edifici3d/archivi.json` (`{"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": …}, …]}`, in
  ordine di affidabilità; se manca, il DBTR dell'Emilia-Romagna): i corpi di un archivio meno affidabile che cadono
  dentro quelli di uno migliore non si usano. La fonte di ogni corpo è scritta sotto la mappa («Fonte del 3D per corpo…»),
  nell'immagine scaricata e nelle note del report (la tabella «Corpi» a destra resta com'era).
- **Rotazione e zoom come la mappa 3D del Patrimonio** (`mappa3d.js`): trascinamento = spostamento, Ctrl+trascinamento o
  tasto destro = rotazione e inclinazione, rotella = zoom al puntatore, doppio clic = vista 3D iniziale; tastiera: frecce,
  Ctrl+frecce, Ctrl+Maiuscolo+frecce (rollio), + −, 0, 3, I; barra «Zoom · Vista (Dall'alto, 3D, Isometrica) · Ruota ·
  Inclina · Rollio». Isometrica approssimata (MapLibre non ha la proiezione ortografica: campo visivo di 8°).
- **Scarica l'immagine** (JPG, PNG, PDF con le attribuzioni) e **Torna alla mappa 2D** per sceglierne un altro.
- Senza archivio sul server (oggi) la pagina lo dice e offre **«Prova la demo sintetica»** (`?archivio=demo`): la demo
  non è più il punto d'ingresso. `?sede=locale` (dal Patrimonio), `?modello=locale` (da Importa DXF/IFC) e `?edificio=`
  aprono direttamente il 3D. Le altre 8 pagine 3D (Edificio, Fotovoltaico) restano in un tempo solo.
- La colonna di destra non cambia.

### Edifici «storti» rispetto all'ortofoto: la causa

- Non è un errore di sistema di riferimento. Sulla pagina pubblicata non c'è ancora l'archivio vero: si apriva la **demo
  sintetica**, i cui edifici sono **inventati** (`edifici3d/sintetico.py`): rettangoli allineati alla **griglia UTM 32N**
  (a Rimini la griglia è ruotata di ~2,5° rispetto al nord, per la convergenza dei meridiani) e posati su un punto
  qualsiasi vicino a Rimini, dove le strade vere sono a ~45°. Sopra l'ortofoto vera sembravano storti e spostati, perché
  non corrispondono a nessun edificio.
- Verifiche sui dati veri:
  - **UVL del WMS DBTR** (GetMap in EPSG:3857 sulle stesse tessere del proxy) sopra l'ortofoto RER 2023-24 a zoom 19, centro
    di Rimini: i contorni coincidono con i fili delle facciate entro **circa mezzo metro** (le gronde dei palazzi alti
    sporgono per lo spostamento prospettico della foto, come atteso);
  - **sagome OSM vere** (API OSM, riquadro di piazza Cavour; archivio di prova solo locale, mai pubblicato) passate per la
    catena della fase 10 (EPSG:4326 → 7791 → `feature_da_corpi` → PMTiles) e disegnate dalla pagina Modelli 3D sopra la
    stessa ortofoto: coincidono con i tetti, scarto entro **1 m**;
  - il proxy (`limiti_tessera` in EPSG:3857) e la proiezione locale della pagina (`E.proiezione`, scarto di millimetri a
    250 m) sono corretti.
- Correzione: la demo **non va mai sopra un'ortofoto vera** (anche nelle altre pagine 3D lo sfondo è spento e il
  selettore dice «nessuna: la demo sintetica non va sopra le foto vere»), resta dichiarata come sintetica e si apre solo a
  richiesta. In Ortofoto i contorni della demo non si sovrappongono (come prima).

### Prove 5–7 della Parte 7 di `PUBBLICAZIONE_2026-11-04.md` sul codice attuale

In Chromium headless, con un server locale (sito statico, ortofoto inoltrate al sito online, `/api/patrimonio` simulata,
nessun archivio: come online oggi), file sintetici di `fase10-edifici3d/tests/modelli_sintetici.py` e `fase11-visure`:
- **§ 43 Fotovoltaico ed Edificio**: Producibilità (area su un tetto di E-DEMO, 49.747 kWh/anno con l'avviso del clima
  sintetico e il grafico mensile), Sole sulle facciate (2019 m² in 210 pezzi, tabella per orientamento), Obblighi di legge
  (P = k · S, zona E 2139 GG, H'T Tab. 10 e 11; cambiando «Intervento» i valori cambiano), Pompe di calore (righe
  «analisi 10/11: analisi non disponibile in questa installazione»): **superate**. Confronto con PVGIS: il pulsante si
  abilita dopo la producibilità; il confronto richiede la rotta del server (`/api/edifici/pvgis`, provata dal vivo il 04/11),
  non provata qui.
- **§ 44 Importa DXF/IFC**: `casa_sito.ifc` → «File letto», 2 corpi (piano 4 m; capanna 7/10 m, 31° S e N), `web-ifc.wasm`
  caricato, **nessuna richiesta POST**; «Apri nella pagina Modelli 3D» → «Modello «casa_sito»: 2 corpi (letto solo in
  questo browser)», **ora direttamente in 3D**; `casa_metri.dxf` con i due punti noti → 6 corpi e l'avviso dei 3DSOLID;
  Modelli 3D non carica web-ifc, dxf-parser, clipper né proj4: **superate**.
- **§ 45 Patrimonio con le visure**: file d'esempio → «Trova gli edifici» (con la rotta simulata), `indice.csv` delle visure
  sintetiche → «Visure lette nel browser», 9 unità; «Scarica il risultato con le visure» → CSV con le colonne `visura_…`;
  la pagina Visure si apre: **superate**. Nessun errore JavaScript in nessuna pagina (solo i 404 attesi di archivio e rotte).
- Problemi trovati e corretti: nessuno nelle tre prove; durante le prove di Modelli 3D corretti i passi da tastiera (le
  animazioni brevi venivano interrotte da MapLibre: ora passi istantanei come in `mappa3d.js`) e le sagome 2D poco visibili
  sull'ortofoto (ora con il contorno).

### Pagina interna `/interno/edifici.html`

Con 0 tessere su 0 e nessuna fonte DSM/LAS attiva diceva «Zona in corso». Ora `servizio/interno.py` calcola la
`situazione` della zona, coerente con l'esito dell'ultima notte: «In attesa: nessuna fonte DSM o LAS attiva e 0 corpi della
Fase A (manca prepara).», «In attesa: …» con un solo motivo, «Non avviata: …», «Fermata: …», «Zona completata il …» o
«Zona in corso.»; la pagina la mostra (e la ricava da sola con un'api più vecchia). 7 test nuovi in
`fase4-server/tests/test_interno.py`. Serve il rebuild dell'api (passo C10).

### Crontab dell'host (05/11/2026)

**Correzione del 05/11 mattina.** Il crontab vuoto non era un guasto: il **worker è acceso dal 04/11** e fa da solo
mercati (2:30), previsioni, storico, indicatori e clima, e le righe del cron erano state tolte apposta (README della fase 4).
La notte del 04/11 i mercati li ha fatti il worker. Le tre righe rimesse il 04/11 notte (mercati girati due volte, senza
danni grazie al limitatore GME) sono state tolte: nel crontab resta solo `edifici-lidar` alle 3:30. Il worker girava
ancora sull'immagine del 03/11 perché le procedure ricostruivano solo l'api: ricreato con `docker compose up -d worker`.
Da ora: dopo ogni rebuild dell'api anche `docker compose up -d worker` (passo C10), `crontab -l` dopo ogni pubblicazione
con 1 riga attesa (passo C14), e **mai** `| crontab -` senza partire da `crontab -l`.

### EuGEnio Visure

- Build di GitHub Actions **verde** il 05/11 (commit della codifica, impronta `3fc84c6a…`). Sul PC: .exe di **88,3 MB**,
  `prova --modelli` in 7,9 s alla prima esecuzione (Linux 2,5 s), IFC e DXF di prova a 2 corpi, impronta e `--stato`
  coincidono. Attese corrette in `PUBBLICAZIONE_2026-11-04.md` (passo 52: ~90 MB, ~8 s).
- Con l'uscita in una pipe dentro PowerShell (`| Out-Host`) i caratteri accentati appaiono storpiati (codepage 850): è solo
  la decodifica di PowerShell; rimedio documentato `[Console]::OutputEncoding = [Text.Encoding]::UTF8`. Nessuna modifica
  al codice (né `visure/` né `importa.py`: l'impronta non cambia; né l'avviatore: niente nuova build).
- Per la domanda a SignPath Foundation: sezione **«Code signing policy»** («Free code signing provided by SignPath.io,
  certificate by SignPath Foundation», ruoli Authors/Reviewers/Approvers = Paolo Bianco con il profilo GitHub di
  StatoCritico, dichiarazione privacy) nella pagina `visure.html`, nel README della fase 11 e, come collegamento, nel testo
  della release del workflow; sezione «Disinstallare» (`%LOCALAPPDATA%\EuGEnio\Visure`); metadati dell'.exe
  (`versione_windows.txt`: ProductName «EuGEnio Visure», ProductVersion = FileVersion = 0.1.0) controllati da
  `tests/test_metadati_exe.py`.

### Rinviato (blocco 5)

- **Cartografia catastale dell'Agenzia delle Entrate (WMS INSPIRE)**: licenza **CC BY 4.0** (comunicato dell'Agenzia del
  24/09/2020 e `Fees` del GetCapabilities; uso anche commerciale con citazione), ma il servizio non offre EPSG:3857 (solo
  EPSG:6706, 4258, 25832–25834, 3044–3046) e non manda le intestazioni CORS: per usarlo come strato della mappa serve un
  passaggio nel proxy del server con la riproiezione. Non fatto: la ricerca per foglio e particella usa la rotta esistente.
- `archivi.json`: scritto a mano quando ci saranno più archivi; da far scrivere a `prepara`/`prepara-regione`.

### File toccati (blocco 5)

`fase5-sito/sito/` (`confini_gl.js` e `esporta_mappa.js` nuovi, `ortofoto.js`, `ortofoto.html`, `modelli3d.html`,
`edificio3d.js`, `minimappa.js`, `stile.css`, `visure.html`, `interno/edifici.js`), `fase5-sito/tests/`
(`test_mappe_browser.py` nuovo, `test_costruisci_pagine.py`), `fase4-server/servizio/interno.py` e
`tests/test_interno.py`, `fase11-visure/README.md` e `tests/test_metadati_exe.py`, `.github/workflows/visure-windows.yml`
(testo della release), README delle fasi 4, 5, 10 e 11, `RIEPILOGO.md`, `DA_FARE.md`, `PUBBLICAZIONE_2026-11-04.md`.

### Prove (blocco 5)

- fase 5: **33 test** (6 nuovi, 4 nel browser); fase 4: **158**; fase 10: **92**; fase 7: 13; fase 11: **78** (76 con la correzione
  della codifica, 2 nuovi).
- Chromium headless a 1366 e 375 px (nessuno scorrimento orizzontale), schermate in
  `/tmp/claude-0/-home-claude/b39a33ad-aac6-5872-933c-5ca739721e4f/scratchpad/modelli3d/` (sessione di lavoro, non nello zip).

### Limiti noti (blocco 5)

- Confini generalizzati (~100 m): orientamento, non misura. Isometrica approssimata. Il rollio non ha il gesto col mouse
  (in `mappa3d.js` Maiuscolo+tasto destro): solo pulsanti e tastiera.
- Online, finché l'archivio UVL non è sul server, il 3D si genera solo sulla demo; la ricerca porta comunque sul punto.

---

## Blocco 6 – Seconda pubblicazione del 05/11 (`?v=20261105b`): immagini, Ortofoto, Modelli 3D, strati, menu

Feedback di Paolo sulle prove di `?v=20261105a` (testuale nel messaggio del 05/11): in Ortofoto e in Modelli 3D «dice
immagine scaricata, ma in realtà il file non parte» (con Sentinel-2); manca la ricerca per indirizzo in Ortofoto; in Modelli
3D il punto dell'indirizzo (ANNCSU, a volte impreciso) va spostato, dalla demo non si esce, servono ortofoto, confini delle
particelle e contorni degli edifici attivabili; cosa manca per il servizio vero; menu con «S», «GME», il triangolo giallo e
il gruppo Statistiche con «Costi energetici Sanità».

### Immagine che «dice scaricata ma non parte»: causa e correzione

- Prove in Chromium headless **sul sito pubblicato** (`?v=20261105a`, Ortofoto a Rimini, zoom 16, RER e Sentinel-2) e in
  locale: JPG, PNG e PDF si scaricano **davvero** (file da 0,5–4 MB, immagine con la foto e la fascia delle licenze). Le
  tessere arrivano tutte dal proxy dello stesso sito (`/api/ortofoto/…`, anche Sentinel-2): niente canvas «sporcato» da
  CORS; `preserveDrawingBuffer` funziona (MapLibre 5, `canvasContextAttributes`); `toBlob` non restituisce null; il PDF
  non è vuoto. Il browser di Paolo non era raggiungibile da qui per vedere la sua console.
- La **causa vera nel codice** è che il messaggio «Immagine scaricata» era scritto subito dopo il clic **simulato** su un
  collegamento di download, **senza sapere** se il browser avesse salvato il file: un download automatico partito dopo
  qualche secondo di attesa (fino a 4 s per il ridisegno a densità doppia), bloccato o tenuto in sospeso dal browser
  (permesso «Download automatici», download nascosto nella bolla dei download, browser incorporato) dava comunque il
  messaggio di successo. Non è stato possibile ripetere il blocco nel Chromium automatico (che accetta sempre i download).
- Correzione (`esporta_mappa.js`): in Chrome ed Edge sul computer si apre la finestra **«Salva con nome»** del sistema,
  chiesta **dentro il clic** (prima di qualsiasi attesa); la pagina scrive il file e solo dopo la scrittura riuscita dice
  «Immagine salvata: nome (dimensione)»; «Annulla» = «Salvataggio annullato». Negli altri browser il download parte col
  collegamento e il messaggio dice «**Download avviato** dal browser: nome (dimensione)» con un collegamento «**Salva …**»
  da cliccare a mano (un clic vero dell'utente funziona anche quando il download automatico è bloccato), valido 10 minuti.
  Prima del file si controlla che la copia della mappa non sia vuota (tutta trasparente) e leggibile (CORS): altrimenti un
  messaggio chiaro. Attesa del ridisegno ridotta a 2,5 s.
- Prove: JPG, PNG e PDF non vuoti con Playwright (`expect_download`) su Ortofoto con RER, con Sentinel-2 e con le
  particelle e i contorni, su Modelli 3D in 2D, in 3D sull'archivio di prova e sulla demo; finestra «Salva con nome»
  simulata (file scritto, PNG valido; «Annulla» = nessun file).

### Ortofoto

- **Ricerca** per indirizzo (via e civico, comune) o per comune, foglio e particella: modulo comune **`cerca_luogo.js`**
  (prima il codice era solo in `edificio3d.js`), stessa rotta `POST /api/patrimonio` (ANNCSU, poi Zornade): **nessuna
  dipendenza nuova da Zornade**. La mappa va sul punto a zoom 18 con un pallino; il punto entra nelle righe dell'immagine.
- Passo nuovo «**Strati sopra la foto**»: confini delle particelle e contorni degli edifici (sotto), con legenda e fonti
  sotto la mappa e nell'immagine scaricata.

### Modelli 3D

- **Punto trascinabile**: dopo la ricerca il pallino si trascina (mouse e dito; la mappa resta ferma) e da zoom 15 un clic
  sulla mappa lo sposta; l'edificio scelto è quello che contiene il punto corretto (o il più vicino entro 30 m) e «Genera il
  3D» parte da lì. Regioni e comuni si scelgono col clic solo sotto lo zoom 15.
- **Esci dalla demo**: pulsante sempre visibile nella demo (2D e 3D), riapre `modelli3d.html` normale (mappa vera, ortofoto,
  strati, ricerca); «Torna alla mappa 2D» nella demo resta nella 2D della demo.
- **Livelli della mappa** con le caselle: **Ortofoto** (con la scelta della fonte come prima), **Confini delle particelle
  catastali**, **Contorni degli edifici**; nella demo sono spenti (dati veri sopra edifici inventati: no).
- Corretto anche: l'avviso «Dati sintetici di esempio» compariva a destra anche senza la demo (`.messaggio[hidden]`).

### Particelle catastali e contorni degli edifici (proxy del server)

- `fase4-server/servizio/strati.py`, rotte `GET /api/ortofoto/strati` e `/api/ortofoto/strati/{id}/{z}/{x}/{y}.png|json`
  (sotto `/api/ortofoto/`: Caddyfile e regola di Cloudflare invariati), copia su disco in `CARTELLA_ORTOFOTO/strati/`,
  ritmo verso la fonte, limite per indirizzo «ortofoto», `STRATI_SPENTI` nel `.env`; TOML in
  `fase10-edifici3d/ortofoto/strati/` (copiati nell'immagine con le ortofoto: Dockerfile invariato).
- **Particelle**: WMS INSPIRE dell'Agenzia delle Entrate, **CC BY 4.0** («Agenzia delle Entrate – Cartografia catastale, CC
  BY 4.0», con «linee ricolorate da EuGEnio»), richiesto in EPSG:4258 e **riproiettato** riga per riga in web mercator, blocco
  2×2 per lasciare fuori la scritta del servizio, solo linee e numeri in giallo, da zoom 16. **Provato dal vivo** dal
  container il 05/11 (GetCapabilities, GetMap PNG 512×512, Rimini a zoom 17 e 18): allineato all'ortofoto RER e al DBTR.
- **Contorni degli edifici**: Emilia-Romagna dal WMS del **DBTR** (strato `EDI_Edificio`, CC BY 4.0), **provato dal vivo**;
  fuori ER **OpenStreetMap** via Overpass (ODbL), **non raggiungibile dal container** (connessione chiusa): codice provato
  con risposte simulate, da provare dal server (passo D11). Lo strato regionale vale solo dove `fonti/regioni.toml` ha la
  fonte «edifici» attiva (test). Lombardia (ArcGIS `export`): immagine vuota alle scale utili, non accesa.

### Archivio di prova e «servizio vero»

- Prova dal container dei servizi pubblici, senza aggirare blocchi: **DBTR UVL non scaricabile** in automatico (WFS 404, il
  download è una **prenotazione** con reCAPTCHA e consegna per email; GetFeatureInfo del WMS senza geometria); **DTM 5 m dal
  WCS pubblico sì** (10×10 km in 35 s, 15 MB); **API di OpenStreetMap sì** (una chiamata per un quartiere).
- Comandi nuovi della fase 10: `osm-campione` (archivio ODbL di un quartiere) e `dtm-wcs` (DTM a blocchi in un GeoTIFF).
- **Archivio di prova** del centro di Rimini (`edifici_rimini_prova_2026-11-05.tar.gz`, 0,9 MB: 528 corpi OSM, terreno DTM
  RER, `archivi.json`, `LICENZE.txt`, `LEGGIMI_ARCHIVIO_PROVA.txt`), provato in Chromium con il proxy vero: ricerca di via
  Gambalunga 27 → edificio scelto → «Genera il 3D» → immagine con le attribuzioni. Altezze OSM quasi sempre assenti: stima
  dichiarata di 9 m (fonte per corpo «stima»). Va sul server al passo D13.

### Cosa manca per passare dalla demo al servizio vero (copia della tabella del README della fase 10)

Oggi sul server non c'è nessun archivio di edifici: Modelli 3D cerca il punto e mostra ortofoto e strati, ma il 3D si genera
solo sulla demo sintetica. Con l'**archivio di prova OSM** del centro di Rimini (passo D13 qui sopra)
il flusso vero funziona già lì (ricerca, punto trascinabile, «Genera il 3D», immagine e report), con altezze stimate. Il
servizio vero in Emilia-Romagna usa le **unità volumetriche del DBTR** (altezza per corpo, CC BY 4.0) e il **DTM 5 m**.

| # | Passo | Chi | Tempo e spazio (stime) |
|---|---|---|---|
| 1 | **Prenotare l'estrazione del DBTR** dal Geoportale: pagina «Download DB Topografico» (`https://geoportale.regione.emilia-romagna.it/download-data/download-dbtopografico`), area = comune o provincia di Rimini (o tutta la regione), classe **Unità volumetrica (UVL)** (facoltativo: Edificio), formato **GeoPackage**, sistema **RDN2008 / UTM 32N (EPSG:7791)**. Il modulo ha il reCAPTCHA e la consegna è per email: l'agente non può farlo (e non deve aggirarlo). Il WFS del DBTR non è un'alternativa (401 il 03/11, 404 il 05/11/2026). | **Paolo** | 5 minuti + attesa dell'email; GeoPackage stimato 50–150 MB per la provincia di Rimini, 1–3 GB per la regione (da verificare sul file) |
| 2 | Copiare il GeoPackage sul server: `scp UVL_rimini.gpkg eugenio:/srv/energia/dati/edifici/cc-by/er/grezzi/` (creare prima la cartella con `mkdir -p`). In alternativa metterlo in `C:\Users\ingpa\Documents\claude\pj\statocritico\edifici\`: l'agente lo legge dal PC, prepara l'archivio nel suo ambiente e ti restituisce un tar come quello di prova. | **Paolo** (o agente dal PC) | minuti |
| 3 | **DTM 5 m** della zona dal WCS pubblico, sul server: `docker compose --profile edifici run --rm edifici-lidar dtm-wcs --riquadro 770000 4860000 800000 4895000 --uscita /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif` (comune di Rimini e dintorni, 30×35 km, 12 blocchi). Per tutta la regione: i quattro quadranti TIFF della scheda del DTM (~4,9 GB) in `cc-by/er/grezzi/`. | **Paolo** (comando pronto) | ~7 minuti e ~180 MB per 30×35 km; ~1 h per i quadranti |
| 4 | **Controllo degli attributi**: `docker compose --profile edifici run --rm edifici-lidar controlla-uvl --gpkg /dati/edifici/cc-by/er/grezzi/UVL_rimini.gpkg` (rapporto su H_uvl, B_uvl, gronda/colmo, piani). | Paolo; l'agente legge il rapporto | 1–2 minuti |
| 5 | **`prepara`**: `docker compose --profile edifici run --rm edifici-lidar prepara --gpkg /dati/edifici/cc-by/er/grezzi/UVL_rimini.gpkg --dtm /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif --archivio /dati/edifici --riquadro 770000 4860000 800000 4895000`. Scrive `cc-by/er/prodotti/` (corpi.pmtiles, contesto/, dtm_cog.tif, terreno.pmtiles, indice.json). | Paolo | provincia di Rimini: 5–20 minuti, 50–200 MB; regione intera a zone (una provincia per volta), qualche ora e 1–3 GB |
| 6 | **`archivi.json`** in `/srv/energia/dati/edifici/`: il DBTR **prima** dell'archivio di prova OSM (o l'archivio di prova tolto): `{"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}, {"base": "/edifici3d/odbl/rimini-prova/prodotti/", "nome": "OpenStreetMap – rimini-prova (archivio di prova)"}]}`. | Paolo (testo pronto) | 1 minuto |
| 7 | **Caddy**: niente da fare. `/edifici3d/` è già servito dalla cartella `CARTELLA_EDIFICI` (sola lettura, Range, CORS, cache di un giorno); nessun riavvio. | — | — |
| 8 | **Prove**: Modelli 3D → «via Gambalunga 27, Rimini» → l'edificio UVL del punto (trascinare il punto se serve) → «Genera il 3D» (fonte «DB topografico regionale»); Ortofoto → «contorni dell'archivio 3D» accesi. | Paolo; l'agente corregge quello che non va | 10 minuti |
| 9 | **Dopo, da sola, la pipeline LiDAR** (cron delle 3:30, `edifici-lidar`, zona Rimini): trovati i corpi della Fase A, lavora le tessere coperte dal **DSM della costa 2019** (falde per corpo dal LiDAR, CC BY 4.0, fascia costiera); per il resto resta «in attesa» finché non arrivano DSM/LAS RER 2023-24 (email all'Archivio Cartografico) o il LiDAR PNRR. La pagina interna `/interno/edifici.html` passa da «In attesa: … 0 corpi della Fase A» a «Zona in corso». | automatico; l'agente legge lo stato | notti successive |

L'agente (Claude) ha già fatto: proxy di particelle e contorni, comandi `osm-campione` e `dtm-wcs`, archivio di prova OSM
del centro di Rimini, prove dal vivo di WMS AdE, WMS DBTR, WCS DTM e API OSM; può fare: leggere il GeoPackage dal PC e
preparare l'archivio (passo 2, alternativa), scrivere `archivi.json` da `prepara`, controllare i rapporti dei passi 4–5 e
le prove del passo 8. Resta a Paolo: la prenotazione del DBTR (reCAPTCHA ed email), i comandi sul server, l'email
all'Archivio Cartografico per DSM/LAS 2023-24.


### Menu

- Nelle tendine e nella riga fissata: «sperimentale» → **S**, «licenza GME» → **GME** (stessi colori), «in sviluppo» →
  **triangolo giallo con il punto esclamativo** (SVG in linea, giallo `#f5c400` con il bordo e il segno scuri `#1a1a1a`:
  si legge sul bianco del tema chiaro, sul fondo scuro e sul nero della riga, in tutti e cinque i vestiti). Testo intero nel
  `title` (suggerimento) e per i lettori di schermo (testo nascosto). Nel menu del telefono restano le parole intere (c'è
  spazio). Corretto uno scorrimento orizzontale fino a ~1.450 px sul telefono con la riga fissata (testi nascosti assoluti fuori
  dalla riga che scorre).
- Gruppo nuovo **Statistiche** in fondo (dopo Fotovoltaico), stesso comportamento degli altri (tendina, clic che fissa,
  suggerimento «Clicca qui per…», menu del telefono), con **Costi energetici Sanità** = `indicatori.html` (URL invariato),
  **senza** etichetta e senza l'avviso «Servizio sperimentale» (validata). «Indicatori» tolto dalle «Altre pagine». Titolo
  e intestazione della pagina («Statistiche» › «Costi energetici Sanità»), Come funziona, F.A.Q. e Licenza aggiornati; la
  newsletter non cita la pagina.

### File toccati (blocco 6)

`fase5-sito/` (`parti/testata.html`, `parti/testa.html`, `sito/esporta_mappa.js`, `ortofoto.js`, `ortofoto.html`,
`edificio3d.js`, `modelli3d.html`, `indicatori.html`, `metodo.html`, `faq.html`, `licenza.html`, `stile.css`,
`cerca_luogo.js` e `strati_gl.js` nuovi, tutte le pagine per il menu e `?v=20261105b`, `interno/edifici.html`, test),
`fase4-server/` (`servizio/strati.py` nuovo, `app.py`, `config.py`, `.env.example`, `tests/test_strati.py`),
`fase10-edifici3d/` (`ortofoto/strati/*.toml`, `edifici3d/osm_campione.py`, `edifici3d/dtm_wcs.py`, `__main__.py`,
`tests/test_osm_campione.py`), README delle fasi 4, 5 e 10, `README_stile.md`, `RIEPILOGO.md`, `DA_FARE.md`. **Non
toccati**: `fase11-visure/visure/`, `edifici3d/__init__.py`, `edifici3d/importa.py` (impronta della 0.1.0 ancora
`3fc84c6a…`, ricontrollata con `costruisci_pacchetto.py`), Caddyfile.

### Prove (blocco 6)

- fase 5: **38 test** (5 nuovi: menu, pagine, finestra «Salva con nome», Ortofoto con ricerca e strati, punto trascinabile
  ed «Esci dalla demo»); fase 4: **166** (8 nuovi in `test_strati.py`: riproiezione esatta, contorni, Overpass, rotte,
  copia, spegnimento); fase 10: **96** (4 nuovi); fase 7: 13; fase 11: 78.
- Chromium a 1366 e 375 px con il proxy vero (WMS AdE e DBTR, ortofoto RER) e l'archivio di prova: nessuno scorrimento
  orizzontale, nessun errore JavaScript; schermate in
  `/tmp/claude-0/-home-claude/b39a33ad-aac6-5872-933c-5ca739721e4f/scratchpad/correzioni05/` (sessione di lavoro, non nello zip).

### Limiti noti (blocco 6)

- Non è stato possibile vedere il download nel browser di Paolo: se anche con «Salva con nome» (Chrome/Edge) o col
  collegamento «Salva …» il file non arriva, serve il nome e la versione del browser.
- Particelle: la cartografia catastale non copre Trento, Bolzano e il tavolare; da zoom 16. Contorni DBTR da zoom 16, con
  qualche doppia linea dove il servizio disegna i bordi interni. OSM fuori ER da provare dal server.
- Archivio di prova: sagome OSM (completezza variabile), altezze stimate: serve solo a vedere il flusso vero.
