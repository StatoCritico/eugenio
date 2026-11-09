# Aggiornamento del 09/11/2026 b – correzioni dalle prove N10 (sito `?v=20261109b`, release `v2026.11.09b`)

Punto di partenza: sito `?v=20261109a` online (procedura N1–N12 di `AGGIORNAMENTO_2026-11-09.md`, release `v2026.11.09`,
69 archivi). Il 09/11 alle 08:00 Paolo ha fatto le prove N10 e ha segnalato sei problemi. Questa procedura breve porta
online le correzioni con la versione del sito **`?v=20261109b`** e la release **`v2026.11.09b`**. Nessun archivio nuovo,
nessuna modifica al `.env` né al Caddyfile.

## Cosa cambia: punti 1–6

| Punto | Causa trovata | Correzione |
|---|---|---|
| **1** Righe rosse in Console | La pagina chiedeva `lidar/falde/<cella>.json` e `lidar/alberi/<cella>.json` per **tutte** le celle di 0,01° attorno al punto, appena `archivi.json` diceva dove sono le falde LiDAR dell'ER: anche a Roma, Susegana, Firenze (dove la pipeline non passa) e nelle zone ER non ancora elaborate. `lidar/indice.json` non diceva quali celle esistono. | **Scelta: la pagina non le chiede** (più robusto di un 204 dal server: niente richieste inutili, nessuna modifica a Caddy). `lidar/indice.json` ha ora l'elenco `celle.falde` e `celle.alberi`, scritto dalla pipeline a ogni tessera e, per l'indice che c'è già sul server, dal comando nuovo `lidar-celle` (passo P6). Con un indice senza elenco la pagina chiede solo dentro gli archivi dell'Emilia-Romagna. Importa DXF/IFC chiede le celle di contesto solo se sono in `nomi_celle`. Le celle `contesto/…` di Modelli 3D erano già filtrate (tutti i 69 archivi hanno `nomi_celle`); le tessere di ortofoto, strati e terreno hanno gli stessi limiti di zona e di zoom nella pagina e nel server. `passkeys-inject.js` è un'estensione del browser di Paolo: **da ignorare**. |
| **2** Colore e Alberi | Stavano nel pannello di destra sotto «Contorni degli edifici». | Sotto la mappa, nella riga di «Genera il 3D», dopo frecce, «Ortofoto al suo posto / spostata» e «Azzera»: etichetta «Colore» (il nome intero nel tooltip), pulsante a pillola, casella «Alberi». A 1366 px tutto su una riga; a colonna stretta il gruppo del colore va a capo intero, nessuno scorrimento di lato a 375 px. Tolti dal pannello di destra. Ortofoto non ha questi comandi. |
| **3** Ricerca | Due moduli, ognuno con il suo «Comune» e il suo «Reset»: con «bagno di romagna» nel blocco della particella e «Susegana» rimasto nel blocco dell'indirizzo (prova G) la ricerca andava a «via San Salvatore 13, Susegana». | **Un solo modulo** in Modelli 3D, Ortofoto e nelle 8 pagine 3D: Comune in cima, Indirizzo, Foglio e Particella affiancati, poi «Cerca l'indirizzo» (solo Comune e Indirizzo), «Cerca la particella» (solo Comune, Foglio e Particella), un solo «Reset». Solo il Comune: centro del comune. Invio: nel campo dell'indirizzo cerca l'indirizzo, in Foglio o Particella la particella. In più: un risultato in **un altro comune** (il server scrive «comune catastale … diverso da quello indicato») non sposta la mappa lì ma al centro del comune scritto, con l'avviso. Precedenza dei parametri e apertura su Cesena invariate. |
| **4** Bagno di Romagna | Conseguenza dei punti 3 e 6: la mappa era finita a Susegana (edifici marroni delle sagome venete senza quota, tetti piani) e l'ortofoto in collina era la Toscana con le scritte. | Verificato con l'archivio vero del 07/11 (`cc-by/er/bagno-di-romagna`, comune intero 040001): foglio 54 particella 216 → edificio DBTR (non OSM), corpo principale a capanna 22° («tetto ipotizzato a 22° (pianura: quota del terreno 511 m)»), corpo interno a padiglione 22°, nota «Tetti: 0 misurati dal LiDAR, 0 stimati dal colmo DBTR, 2 ipotizzati (22° pianura / 32° montagna: 2 a 22°), 0 piani», 18 vicini tutti DBTR, terreno dal DTM, nessun 404. Archivio, copertura e falde a posto. |
| **5** Susegana piatta | Le tessere `/api/terreno` usavano già il Copernicus fuori dai DTM regionali (provato dal container: 65–127 m) e la pagina chiedeva il terreno anche fuori dall'ER, **ma** la pagina spegne il terreno se gli edifici OSM o le sagome regionali non hanno la quota, e il server la leggeva solo dai DTM regionali: senza il DTM del Veneto (J5 bis forse non fatto) i corpi di Susegana restavano senza quota → vista piatta. | Le quote dei corpi (sagome regionali **e** edifici OSM) vengono dal DTM regionale e, dove manca, dal **Copernicus DEM 90 m** (stesse quote delle tessere; Susegana 70,9 m). Risposta con `quote_fonte`. Messaggio «Quote dei corpi dal terreno del server (DTM regionale o, dove manca, Copernicus DEM 90 m).». Esagerazione ×1,5 e ×2 provata. Verifiche [Server] in P5; J5 bis resta facoltativo (P5 bis). |
| **6** Scritte sul terreno bianco | Fonte `toscana2023` (WMS Geoscopio): **fuori dalla Toscana ma dentro il suo riquadro** (9,68–12,38 E, 42,23–44,48 N: Bagno di Romagna, Cesena, Bologna, La Spezia, Perugia) risponde 200 con un JPEG bianco di 1,7 kB con la scritta «Fonte dei dati: Regione Toscana – Base informativa territoriale…» (provato dal container il 09/11). A Bagno di Romagna la RER non ha immagini, la pagina passava alla Toscana e mostrava le scritte. | Campo nuovo `segnaposto = true` della fonte: il proxy rende queste tessere **vuote** (PNG trasparente con `X-Ortofoto-Vuota: 1`), anche quelle già nella copia su disco; la pagina passa alla fonte successiva (AGEA 2012 del Geoportale) e lo scrive, come per la RER. Indirizzi delle tessere toscane con `?s=1` (niente tessere bianche dalle copie di browser e Cloudflare). A Firenze la foto toscana resta (provato). |

## File toccati

- **fase 4**: `servizio/ortofoto.py` (`segnaposto`, `segnaposto_bianco`, `vuota_png`, `?s=1`), `servizio/terreno.py`
  (`quote_copernicus`, `quote_punti(ripiego=…)`), `servizio/edifici_osm.py` (quote anche per gli edifici OSM, `quote_fonte`),
  `README.md`; test `test_ortofoto.py`, `test_terreno.py`, `test_edifici_osm.py`, `test_edifici_regionali.py`.
- **fase 5**: `sito/cerca_luogo.js` (modulo unico), `sito/edificio3d.js` (colore e alberi sotto la mappa, `haCellaLidar`,
  messaggio delle quote), `sito/importa_modello.js`, `sito/stile.css`, `sito/dati/edifici3d/lidar/indice.json` (demo con
  l'elenco delle celle), `novita.toml` (voce `20261109b`), tutte le pagine (`?v=20261109b`), `novita.html`, `novita.xml`,
  `EUGENIO_PER_AGENTI.md`, `llms.txt`, `README.md`, `sito/README_stile.md`; test `test_mappe_browser.py`,
  `test_prove_0911_browser.py` e il nuovo `tests/test_prove_0911b_browser.py` (10 prove).
- **fase 10**: `edifici3d/pipeline.py` (`celle_presenti`, `aggiorna_celle_indice`, `aggiorna_celle_archivio`, elenco nelle
  celle di `_indice`), `edifici3d/__main__.py` (comando `lidar-celle`), `ortofoto/toscana.toml` (`segnaposto = true`),
  `ortofoto/emilia_romagna.toml` (campi documentati), `README.md`; test `test_fase_c.py`.
- Radice: `AGGIORNAMENTO_2026-11-09b.md` (questo), `DA_FARE.md`, `RIEPILOGO.md`, `EUGENIO_PER_AGENTI.md`.

## Test (container, 09/11/2026, una suite alla volta)

- fase 4: **239 passed** (236 + segnaposto della Toscana, quote dei punti con il ripiego Copernicus, sagome venete senza DTM).
- fase 10 (senza le prove nel browser): **175 passed** (174 + `lidar-celle`); `test_blocco2_browser.py`: **5 passed**.
- fase 5, tutta la cartella `tests` con Chromium: **98 passed, 1 saltato** (88 + le 10 prove di `test_prove_0911b_browser.py`).
- `costruisci_pagine.py --controlla`: `versione 20261109b: 0 file da rigenerare`.

## Procedura P1–P10

Tempo: circa 40 minuti, prove comprese. Ordine: PC → server → Cloudflare → browser → PC.

### P1. [PC] Zip sopra il clone
Scarica `eugenio_2026-11-09b.zip` in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Measure-Object
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-09b.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261109b" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: `Count : 0` prima (clone pulito dopo N11); dopo l'estrazione `Count : 1`; due righe nuove:
`?? AGGIORNAMENTO_2026-11-09b.md` e `?? fase5-sito/tests/test_prove_0911b_browser.py`.

Cosa fare se va male: `Count` diverso da 0 prima → `git status --short` e mandami l'uscita (niente estrazione finché non è
chiaro); `Count : 0` dopo → zip sbagliato, riscaricalo; altre righe `??` → mandamele.

### P2. [PC] Pagine e test della fase 5, segreti
```powershell
cd fase5-sito
```
```powershell
python costruisci_pagine.py --controlla
```
```powershell
python -m pytest -q tests
```
```powershell
cd ..
```
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x
```
Cosa aspettarsi: `versione 20261109b: 0 file da rigenerare`; test verdi (senza Chromium sul PC le prove nel browser si
saltano: va bene); quattro righe `.gitignore:…`.

Cosa fare se va male: test rossi → mandami le ultime 30 righe; meno di quattro righe → fermati e mandamele.

### P3. [PC] Pacchetti del codice e del sito
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=.venv-build --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude=uni_privato --exclude=node_modules .dockerignore fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d fase5-sito/novita.toml
```
```powershell
tar -tzf ..\codice.tar.gz | Select-String -Pattern "uni_privato|\.env$" | Measure-Object
```
```powershell
cd fase5-sito
```
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
```
```powershell
cd ..
```
Cosa aspettarsi: `Count : 0` (nessun modulo privato, nessun `.env`).

Cosa fare se va male: `Count` diverso da 0 → cancella `..\codice.tar.gz` e mandami le righe.

### P4. [PC] Copia dei pacchetti sul server
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: due righe con `100%`.

Cosa fare se va male: `Connection timed out` → rete aziendale: passa a casa o al telefono.

### P5. [Server] Copia di sicurezza, codice, rebuild di api ed edifici, verifiche di ortofoto e terreno
Entra con `ssh eugenio`, poi:
```bash
cp -a ~/energia ~/energia_prima_20261109b
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "def segnaposto_bianco\|def quote_copernicus\|def aggiorna_celle_archivio" ~/energia/fase4-server/servizio/ortofoto.py ~/energia/fase4-server/servizio/terreno.py ~/energia/fase10-edifici3d/edifici3d/pipeline.py
cd ~/energia/fase4-server
docker compose build api
docker compose up -d --force-recreate api worker
docker compose --profile edifici build edifici-lidar
docker compose --profile edifici up -d --force-recreate edifici-coda
sleep 60; docker compose ps api worker
docker compose exec -T api python -c "import urllib.request as u; [print(r.status, r.headers['Content-Type'], r.headers.get('X-Ortofoto-Vuota')) for r in (u.urlopen('http://localhost:8000/api/ortofoto/toscana2023/17/' + t + '.jpg?s=1') for t in ('69889/47741', '69634/47774'))]"
docker compose exec -T api python -c "import urllib.request as u, json; print([f['tessere'] for f in json.load(u.urlopen('http://localhost:8000/api/ortofoto/fonti'))['fonti'] if f['id'] == 'toscana2023'])"
docker compose exec -T api python -c "from pathlib import Path; from servizio import terreno as T; print(sorted(Path(d['percorso']).name for d in T.dtm_disponibili()))"
docker compose exec -T api python -c "import io, urllib.request as u, numpy as np; from PIL import Image; r = u.urlopen('http://localhost:8000/api/terreno/14/8749/5838.png'); a = np.asarray(Image.open(io.BytesIO(r.read())).convert('RGB')).astype(float); q = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768; print(r.headers['X-Terreno-Fonte'], round(q.min()), round(q.max()))"
docker compose exec -T api python -c "from servizio import terreno as T; f = []; print(T.quote_punti([(12.2563, 45.8537), (11.9914, 43.8892)], ripiego=True, fonti=f), f)"
```
Cosa aspettarsi: tre righe che finiscono con `:1`; le build finiscono con `Built`; api `Up … (healthy)`, worker `Up`; poi
`200 image/png 1` (Bagno di Romagna, fuori dalla Toscana: tessera vuota, non più bianca con la scritta) e
`200 image/jpeg None` (Firenze: foto vera); `['/api/ortofoto/toscana2023/{z}/{x}/{y}.jpg?s=1']`; l'elenco dei DTM:
`['dtm5_er_ne.tif', 'dtm5_er_se.tif']` **senza** `dtm5_veneto_tv.tif` vuol dire che J5 bis non è stato fatto (va bene:
c'è il Copernicus; per farlo vedi P5 bis), con `dtm5_veneto_tv.tif` che è stato fatto; la tessera del terreno di Susegana:
`copernicus 65 127` (senza J5 bis) oppure `dtm` o `dtm+copernicus` con numeri simili (con J5 bis): **mai** `piatta 0 0`;
le quote: `[70.88, Q] ['dtm', 'copernicus']` con Q tra 505 e 515 (Susegana 70,88 m dal Copernicus, Bagno di Romagna circa 510 m dal DTM
dell'ER; con J5 bis anche Susegana dal DTM, intorno a 70 m, e solo `['dtm']`).

Cosa fare se va male: api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe; la
tessera di Bagno di Romagna `image/jpeg None` → l'api è quella vecchia: rifai la build; `piatta 0 0` o quote `None` → il
server non raggiunge i file del Copernicus: `docker compose logs --tail 50 api | grep -i copernicus` e mandami le righe;
per tornare indietro: `rm -rf ~/energia && mv ~/energia_prima_20261109b ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker && docker compose --profile edifici build edifici-lidar`.

### P5 bis. [PC e Server] Facoltativo: DTM del Veneto (J4 bis e J5 bis del 07/11), solo se in P5 mancava
Serve solo per avere a Susegana e Conegliano il terreno a 5 m invece dei 90 m del Copernicus (la vista è già in rilievo
anche senza). Solo se la cartella `C:\Users\ingpa\Documents\claude\pj\statocritico\dtm_veneto\susegana_conegliano` c'è
(40 zip, 7 MB). Sul PC, da `C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio`:
```powershell
scp -r ..\dtm_veneto\susegana_conegliano eugenio:~/dtm_veneto_tv
```
Poi sul server (`ssh eugenio`):
```bash
mkdir -p /srv/energia/dati/terreno/grezzi && mv ~/dtm_veneto_tv /srv/energia/dati/terreno/grezzi/veneto_tv && ls /srv/energia/dati/terreno/grezzi/veneto_tv | wc -l
cd ~/energia/fase4-server && docker compose --profile edifici run --rm edifici-lidar dtm-server --regione veneto --crs EPSG:6876 --file /dati/terreno/grezzi/veneto_tv --uscita /dati/terreno/dtm5_veneto_tv.tif | grep -E '"(crs|tavole|licenza)"'
sleep 300; docker compose exec -T api python -c "import urllib.request as u; r = u.urlopen('http://localhost:8000/api/terreno/15/17497/11677.png'); print(r.status, r.headers['X-Terreno-Fonte'], r.headers['X-Terreno-Nome'])"
```
Cosa aspettarsi: 40 righe `100%`; `40`; `"crs": "EPSG:6876"`, `"tavole": 40`, `"licenza": "IODL 2.0"`; dopo 5 minuti
(l'api rilegge i DTM) `200 dtm DTM 5 m da voli LiDAR Regione del Veneto (IODL 2.0)`.

Cosa fare se va male: la cartella sul PC non c'è → salta P5 bis (resta il Copernicus); `copernicus` invece di `dtm` → la
tessera era già nella copia: va bene, le tessere nuove useranno il DTM; errore di `dtm-server` → mandami le ultime 20 righe.

### P6. [Server] Elenco delle celle LiDAR
Ancora in `~/energia/fase4-server`:
```bash
docker compose --profile edifici run --rm edifici-lidar lidar-celle --archivio /dati/edifici
docker compose exec -T api python -c "import urllib.request as u, json; a = json.load(u.urlopen('http://caddy/edifici3d/archivi.json')); print(len(a['archivi']), a.get('lidar')); i = json.load(u.urlopen('http://caddy/edifici3d/cc-by/er/prodotti/lidar/indice.json')) if a.get('lidar') else {}; print({k: len(v) for k, v in i.get('celle', {}).items()})"
```
Cosa aspettarsi: una lista JSON con una voce `{"indice": "cc-by/er/prodotti/lidar/indice.json", "falde": N, "alberi": M}`
(N e M numeri delle celle già elaborate dalla pipeline, anche 0), oppure `[]` se la pipeline non ha ancora scritto falde;
poi `69 /edifici3d/cc-by/er/prodotti/` e `{'falde': N, 'alberi': M}` con gli stessi numeri (oppure `69 None` e `{}`: niente
falde LiDAR sul server, la pagina non chiede nulla). Da qui in poi la pipeline notturna aggiorna l'elenco da sola (stessa
immagine `edifici-lidar` appena ricostruita).

Cosa fare se va male: `unrecognized arguments` o `invalid choice: 'lidar-celle'` → l'immagine `edifici-lidar` è quella
vecchia: rifai la build di P5; `69` diverso → mandami l'uscita (non cambia nulla negli archivi).

### P7. [Server] Sito e pulizia
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261109b /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/ortofoto.html /srv/energia/sito/interno/edifici.html
grep -c "cerca-luogo-modulo" /srv/energia/sito/cerca_luogo.js; grep -c "haCellaLidar" /srv/energia/sito/edificio3d.js
grep -c "20261109b" /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt; grep -c "una volta sola" /srv/energia/sito/novita.xml
rm -f ~/codice.tar.gz ~/sito.tar.gz
exit
```
Cosa aspettarsi: quattro righe con N > 0; `2` e `3`; due righe con N > 0 e `1` (la voce nuova delle Novità).

Cosa fare se va male: `20261109b` a 0 → `sito.tar.gz` vecchio: rifai P3 e P4 (solo il sito) e la prima riga.

### P8. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma (pagine, script e le
tessere bianche della Toscana già in copia).

Cosa aspettarsi: «Purge request successful» (o simile).

Cosa fare se va male: il pannello non si apre → rete aziendale.

### P9. [Browser] Prove (Ctrl+F5; F12 → Console, con «Errors» acceso)
Una riga rossa `…passkeys-inject.js… 404` (o simile) viene da un'**estensione del browser** (gestore di passkey), non da
EuGEnio: **ignorala**. Le righe gialle di WebGL («GPU stall…») non sono errori.

1. **Console pulita.** Modelli 3D: all'apertura (Cesena), poi «piazza Venezia», «Roma»; «via San Salvatore», «Susegana»;
   «piazza del Duomo», «Firenze»; Bagno di Romagna foglio 54 particella 216 (punto 4): in nessuna delle cinque prove righe
   rosse con `lidar/falde/`, `lidar/alberi/` o `contesto/` (F12 → Rete, filtro `lidar`: a Roma, Susegana e Firenze
   **nessuna** richiesta; a Cesena solo celle con risposta 200, o nessuna se in P6 c'era `[]`).
2. **Ricerca (punto 3).** Modelli 3D e Ortofoto: **Comune** una volta sola in cima, poi **Indirizzo**, poi **Foglio** e
   **Particella** affiancati, poi «Cerca l'indirizzo», «Cerca la particella» e **un solo «Reset»**. Scrivi Comune «bagno di
   romagna», Indirizzo «via san salvatore», Foglio 54, Particella 216, premi **«Cerca la particella»**: «Trovato: … particella
   foglio 54, 216», mappa sulla collina di Bagno di Romagna (non Susegana). Premi **«Cerca l'indirizzo»**: la mappa **non**
   va a Susegana (se Zornade trova la via a Susegana: «L'indirizzo trovato è nel comune di SUSEGANA, non in quello scritto
   (bagno di romagna). Ti porto al centro del comune di Bagno di Romagna…»). «Reset» svuota i quattro campi. Solo
   «Torino» nel Comune e «Cerca la particella»: centro di Torino. Senza parametri la pagina si apre ancora su Cesena,
   viale Ghirotti 286.
3. **Bagno di Romagna (punto 4).** Dopo «Cerca la particella» → «Genera il 3D»: edifici del DB topografico (grigi o nel
   colore scelto, **non** marroni), casa scelta con il tetto a capanna; sotto la mappa «Tetti: 0 misurati dal LiDAR, 0
   stimati dal colmo DBTR, 2 ipotizzati (22° pianura / 32° montagna: 2 a 22°), 0 piani»; nella tabella delle falde «tetto
   ipotizzato a 22° (pianura: quota del terreno 511 m)». Ortofoto: sotto la ricerca «… non ha immagini in questa zona: uso
   «Geoportale Nazionale – ortofoto AGEA 2012 …»»; **nessuna scritta** «Fonte dei dati: Regione Toscana» sulla mappa (punto 6).
4. **Colore e Alberi (punto 2).** Modelli 3D: sotto la mappa, sulla stessa riga, «Genera il 3D», le frecce ← ↑ ↓ →, «1 m»,
   «Ortofoto al suo posto», «Azzera», **«Colore»** con la pillola (Grigio) e **«Alberi»**; nel pannello di destra, sotto
   «Contorni degli edifici», **non** ci sono più. Con la finestra stretta (o il telefono, 375 px) vanno a capo in ordine,
   senza scorrimento di lato. Scegli Rosso: edifici rossi, resta dopo il ricaricamento.
5. **Susegana in rilievo (punto 5).** «via San Salvatore», «Susegana» → clic su un edificio → «Genera il 3D»: messaggio
   «… Quote dei corpi dal terreno del server (DTM regionale o, dove manca, Copernicus DEM 90 m).», terreno in rilievo
   (la collina del castello), legenda «Terreno: Copernicus DEM GLO-90 (© DLR e Airbus)» (o il DTM del Veneto con P5 bis);
   nella barra 3D «×2»: il rilievo si alza, legenda «rilievo esagerato ×2»; «×1» torna normale.
6. **Firenze (punto 6).** «piazza del Duomo», «Firenze»: ortofoto della Regione Toscana 2023 visibile (foto vera, non
   bianca); «Genera il 3D» come prima.

Cosa fare se va male: pagina vecchia (campi ancora in due blocchi) → P8 di nuovo e Ctrl+F5; righe rosse diverse da
`passkeys-inject.js` → F12 → Console, clic destro → «Save as…» o screenshot con le righe intere, e F12 → Rete con il filtro
sulla parola della riga; ancora scritte toscane → F12 → Rete, filtro `toscana`: mandami l'indirizzo di una tessera e le
intestazioni (deve avere `?s=1` e `X-Ortofoto-Vuota: 1` fuori dalla Toscana); Susegana ancora piatta → F12 → Rete, filtro
`edifici/osm`: mandami dalla risposta i campi `quote_dtm` e `quote_fonte`.

### P10. [PC] Commit, push e release `v2026.11.09b`
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_dbtr|estraz_procons|\.gpkg$|DTM5x5|archivi_edifici|archivi_citta|archivi_bari_roma|archivi_er_0911|dtm_veneto|\.tar\.gz$|giornaliero.*\.parquet"
```
```powershell
git commit -m "09/11/2026 b: correzioni dalle prove N10 - ricerca con un solo Comune, Indirizzo, Foglio e Particella e un solo Reset, risultati in un altro comune scartati; Colore e Alberi sotto la mappa accanto ad Azzera; celle LiDAR chieste solo se esistono (elenco in lidar/indice.json, comando lidar-celle); quote del terreno Copernicus per edifici OSM e sagome regionali fuori dai DTM (Susegana in rilievo); tessere segnaposto della Toscana trattate come vuote (Bagno di Romagna); sito ?v=20261109b; procedura AGGIORNAMENTO_2026-11-09b"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_b.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.09b --target main --title "EuGEnio 9 novembre 2026 (b) – ricerca con un solo comune e comandi sotto la mappa" --notes-file ..\note_release_b.md
```
Cosa aspettarsi: il terzo comando **non stampa nulla**; il push finisce con `… main -> main`; la release stampa
`https://github.com/StatoCritico/eugenio/releases/tag/v2026.11.09b`. Se tutto è a posto, sul server:
`ssh eugenio "rm -rf ~/energia_prima_20261109b"`.

Cosa fare se va male: righe dal terzo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`; `gh` chiede il login → `gh auth status` e mandami l'uscita (senza token); senza
`gh`: GitHub → Releases → Draft a new release, tag `v2026.11.09b`, titolo come sopra, testo di `..\note_release_b.md`.
