# Aggiornamento del 09/11/2026 c – correzioni dalle prove P9 (sito `?v=20261109c`, release `v2026.11.09c`)

Punto di partenza: sito `?v=20261109b` online (procedura P1–P9 di `AGGIORNAMENTO_2026-11-09b.md`, P5 bis fatto: DTM del
Veneto sul server). **P10 non è stato fatto**: nel clone sul PC le modifiche della `b` sono estratte ma non ancora
committate. Questa procedura le porta nel commit insieme a quelle della `c` e crea **una sola release `v2026.11.09c`**, con
le note delle due voci delle Novità (`20261109c` e `20261109b`). Il 09/11 alle 11:50 Paolo ha fatto le prove P9 e ha
chiesto cinque correzioni; alle 11:56 due modifiche al punto 4 e alla riga sotto la mappa. Nessun archivio nuovo, nessuna
modifica al `.env` (una riga facoltativa nuova, `ORTOFOTO_TIMEOUT_S`, non serve metterla) né al Caddyfile; si ricostruisce
solo l'api (l'immagine `edifici-lidar` non cambia).

## Cosa cambia: punti 1–5 e modifiche delle 11:56

| Punto | Causa trovata | Correzione |
|---|---|---|
| **1** Righe rosse `GET /api/ortofoto/pcn2012/18/… 502` | **Non** è uno zoom oltre il massimo: AGEA 2012 risponde dal container a 16, 17, 18 e 19 (Bagno di Romagna, Firenze, Cesena, 0,7–2,3 s a tessera) anche con 30 richieste insieme. La rotta delle tessere era **sincrona**: ogni tessera in attesa del turno verso la fonte (AGEA: 4 al secondo, una vista 3D inclinata ne chiede 50–80) teneva fermo uno dei 40 thread dell'api; le richieste in coda superavano i **30 s di `read_timeout` di Caddy**, che rispondeva **502**. Da qui anche l'ortofoto «a pezzi». | Rotta **asincrona** (attesa e chiamata alla fonte non occupano thread), chiamata alla fonte al più 12 s (`ORTOFOTO_TIMEOUT_S`), al più 2 × il ritmo in volo per fonte. Un errore della fonte (timeout, rete, 5xx, XML d'errore) o il turno non arrivato in tempo danno una **tessera vuota pulita**: `200`, PNG trasparente, `Cache-Control: no-store`, `X-Ortofoto-Errore: fonte`, `occupata` o `ferma`, `Retry-After` (niente riga rossa, niente copia). Dopo 6 errori di fila in 60 s la fonte è **ferma** 60 s (poi 120, fino a 5 minuti): tessere vuote subito, senza chiamarla. **Zoom massimi reali**: 20 cm a terra = zoom 19 (RER, Toscana, Trento, Bolzano: prima 20), AGEA 50 cm = zoom 18 (prima 19), Sentinel-2 10 m: 15 (EOX dà fino al 17, solo ingrandite). Le sorgenti della mappa hanno `maxzoom` dalla fonte: oltre, MapLibre ingrandisce le tessere che ha (provato: a zoom 20,5 nessuna tessera oltre il 18 per AGEA e oltre il 19 per la RER). |
| **1** Righe di Cloudflare | CSP «Connecting to 'data:' violates … connect-src», «Fetch API cannot load data:», «OTS parsing error» e gli avvisi gialli WebGPU («powerPreference option is currently ignored», «No available adapters») vengono dal **riquadro di Turnstile** (`challenges.cloudflare.com`, sua pagina e sua CSP): EuGEnio non usa WebGPU (né MapLibre 5.24 né il nostro codice chiamano `navigator.gpu`) e la nostra CSP ha solo `frame-ancestors`. Turnstile si carica già **solo alla prima richiesta protetta** (ricerca, edifici OSM, Patrimonio…): all'apertura di Modelli 3D su Cesena non si carica (provato). | Nessuna modifica possibile da parte nostra: righe **da ignorare** insieme a `passkeys-inject.js` (estensione del browser di Paolo). Scritto in Q8. |
| **2** Limiti e fonti non visibili | La nota sotto la mappa c'era solo per i 429; i 502 non arrivavano a nessuna nota. | `protezione.js` conta per fonte le tessere d'errore, i 5xx e la rete caduta: 4 errori in 60 s (o «ferma» dal server) → la fonte si ferma per il `Retry-After` e sotto la mappa compare «Ortofoto «Geoportale Nazionale – ortofoto AGEA 2012 …»: la fonte non risponde (o è molto richiesta). Mi fermo e riprovo da solo tra 2 minuti.»; finita la pausa le tessere si ricaricano e la nota sparisce; un errore isolato fa solo ricaricare le tessere poco dopo (i buchi si riempiono). 429 provato nel browser: «Ortofoto: raggiunto il limite orario … tra 5 minuti». |
| **3** Alberi | Nel browser, con le celle dell'elenco di `lidar/indice.json`, le chiome si vedono (provato a Cesena con una cella finta). La pipeline LiDAR però lavora **solo la fascia costiera della zona di Rimini** (DSM della costa 2019, larga 1–1,5 km): all'ospedale Bufalini le chiome molto probabilmente **non sono mai state calcolate**; e gli alberi si vedevano solo nella vista 3D, non nella mappa 2D dove sta la casella. | Chiome anche nella **mappa 2D** (da zoom 15, attorno al centro) e **nota** se lì non ce ne sono («… per ora la fascia costiera della zona di Rimini»). Verifica [Server] della cella del Bufalini in Q5. |
| **4** Falde automatiche (decisione di Paolo) | L'ipotesi automatica si fa ingannare dai tetti complessi (Infermi di Rimini piano → a falde; via Ovidio a falde → piani). | **Tutti i tetti partono piani.** Nel pannello di destra la sezione nuova **«(4) Coperture»** tra «(3) Edificio» e «(5) Corpi» (le altre si rinumerano): **tegola** isometrica on/off (cursore con la tegola; con la tegola accesa il clic non sceglie l'edificio; Esc la spegne), **Inclinazione** (22° all'inizio); un clic su un edificio (qualsiasi corpo, anche vicino, DBTR, OSM o sagome regionali, in 2D o 3D) gli dà le falde all'inclinazione corrente, un secondo clic lo riporta piano; **«Reset piani»** con conferma nella pagina («Sì, riporta tutti piani» / «Annulla», niente `confirm()`); **«Esporta tetti» / «Importa tetti»** (JSON); riga di stato («3 tetti a falde scelti»). Forma: capanna sul lato lungo, padiglione se quasi quadrato o se la pianta è complessa; restano piani solo i corpi con cortile o più stretti di 2 m (lo dice la riga di stato). Scelte **nel browser** (`localStorage`, chiave `eugenio-tetti-v1`: `archivio|id del corpo` → inclinazione). Nel PNG, nel report e nella tabella dei corpi «tetto a falde scelto dall'utente (22°)». `/fv-producibilita.html` e le altre pagine: «Forma dei tetti» = «Scelti dall'utente» / «Tutti piani». Falde LiDAR, stima dal colmo DBTR e ipotesi 22°/32° restano nel codice, **sospese**. Note e legenda senza «misurati, stimati dal colmo, ipotizzati». |
| **11:56 A** | — | Tolta la riga **«Rilievo ×1 ×1,5 ×2»**: terreno sempre al rilievo vero; codice, test e testi tolti. |
| **5** Fonte dell'ortofoto | La casella elencava le fonti per **riquadro**: il riquadro della Toscana arriva fino a Bologna e a Cesena; la scelta a mano restava anche fuori dalla zona della fonte. | La casella mostra **solo le fonti applicabili** nel punto (fonti nazionali nel riquadro, regionali solo nella loro regione, dai confini ISTAT del sito; entro ~150 m dal confine anche la regione accanto) e propone da sola la migliore: regionale a 20 cm dove ha immagini → AGEA 2012 → Sentinel-2. Firenze: Toscana, AGEA, Sentinel; Susegana: AGEA, Sentinel (AGEA scelta); Cesena: RER; Bologna: RER nell'elenco ma AGEA scelta (la RER lì non ha immagini). Scelta a mano tenuta finché la fonte è applicabile; fuori dalla sua zona si torna all'automatico con ««…» non copre questo punto: torno alla scelta automatica («…»).». Vale per Modelli 3D, le 8 pagine 3D, Ortofoto, Aggiungi edifici e Importa DXF/IFC. |

**Dove si registrano i tetti, alternativa futura (non fatta)**: tetti condivisi sul server, rotta `/api/tetti` protetta
dalla verifica anti-robot, un JSON per archivio (`archivio|id` → inclinazione e forma), proposte in coda e approvazione nella
pagina interna come «Aggiungi DBTR»; la pagina unirebbe le scelte del server (per tutti) a quelle del browser (personali,
con la precedenza). In `DA_FARE.md`.

## File toccati

- **fase 4**: `servizio/ortofoto.py` (rotta asincrona, `_chiama`, `Guasti`, `tessera_errore`, semaforo per fonte),
  `servizio/config.py` (`ORTOFOTO_TIMEOUT_S`), `.env.example`, `README.md`; test `test_ortofoto.py`.
- **fase 5**: `sito/edificio3d.js` (Coperture e tegola, tetti piani, vicini con le falde, alberi in 2D, fonte automatica,
  tolta l'esagerazione), `sito/edifici_calcoli.js` (`tettoScelto`, `faldeStimate(…, {forza})`), `sito/protezione.js`
  (fonti che non rispondono), `sito/confini_gl.js` (`fontiNelPunto`), `sito/ortofoto.js`, `sito/aggiungi_dbtr.js`,
  `sito/importa_modello.js`, `sito/stile.css`, le 9 pagine 3D (sezione «Coperture», testi dei tetti, legenda, fonti),
  `aggiungi-dbtr.html` e `importa-dxf-ifc.html` (`confini_gl.js`), tutte le pagine (`?v=20261109c`), `novita.toml`,
  `novita.html`, `novita.xml`, `EUGENIO_PER_AGENTI.md`, `llms.txt`, `README.md`, `sito/README_stile.md`; test
  `test_mappe_browser.py` (tetti, rilievo), `test_prove_0911b_browser.py`, `test_agenti_sito.py` e il nuovo
  `tests/test_prove_0911c_browser.py` (9 prove).
- **fase 10**: `ortofoto/*.toml` (zoom massimi reali), `edifici3d/tetti.py` (nota «sospeso nella vista»), `README.md`;
  test `test_dbtr_browser.py`.
- Radice: `AGGIORNAMENTO_2026-11-09c.md` (questo), `DA_FARE.md`, `RIEPILOGO.md`, `EUGENIO_PER_AGENTI.md`.

## Test (container, 09/11/2026, una suite alla volta)

- fase 4: **241 passed** (239 + fonte ferma dopo errori ripetuti e timeout, fermo che raddoppia; il test dell'errore della
  fonte ora vuole la tessera vuota pulita invece di 502 e 503).
- fase 10 (senza le prove nel browser): **175 passed** (`test_dbtr_browser.py`: il corpo U2 ora è piano); `test_blocco2_browser.py`: **5 passed** (una volta su tre, con il container carico, la prova Patrimonio → Modelli 3D è andata oltre i 60 s: rilanciata da sola passa).
- fase 5, tutta la cartella `tests` con Chromium: **107 passed, 1 saltato** (98 + 9 prove nuove; adeguati alla decisione sui tetti e al rilievo senza esagerazione `test_mappe_browser.py`, `test_prove_0911b_browser.py` e `test_agenti_sito.py`) (le 9 prove nuove di `test_prove_0911c_browser.py`:
  alberi in 3D e in 2D, «Coperture» tra Edificio e Corpi senza la riga del rilievo, tegola che alterna e resta dopo il
  ricaricamento, esporta, importa e «Reset piani», fonte automatica a Firenze, Susegana, Cesena e Bologna in Modelli 3D e in
  Ortofoto, nota della fonte che non risponde e del 429, nessuna tessera oltre lo zoom massimo).
- `costruisci_pagine.py --controlla`: `versione 20261109c: 0 file da rigenerare`.

## Procedura Q1–Q10

Tempo: circa 40 minuti, prove comprese. Ordine: PC → server → Cloudflare → browser → PC.

### Q1. [PC] Zip sopra il clone
Scarica `eugenio_2026-11-09c.zip` in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-09c.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261109c" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: `Count : 1`; quattro righe nuove (le due della `b` mai committate e le due della `c`):
`?? AGGIORNAMENTO_2026-11-09b.md`, `?? AGGIORNAMENTO_2026-11-09c.md`, `?? fase5-sito/tests/test_prove_0911b_browser.py`,
`?? fase5-sito/tests/test_prove_0911c_browser.py`.

Cosa fare se va male: `Count : 0` → zip sbagliato, riscaricalo; altre righe `??` → mandamele (niente commit finché non è
chiaro).

### Q2. [PC] Pagine e test della fase 5, segreti
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
Cosa aspettarsi: `versione 20261109c: 0 file da rigenerare`; test verdi (senza Chromium sul PC le prove nel browser si
saltano: va bene); quattro righe `.gitignore:…`.

Cosa fare se va male: test rossi → mandami le ultime 30 righe; meno di quattro righe → fermati e mandamele.

### Q3. [PC] Pacchetti del codice e del sito
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

### Q4. [PC] Copia dei pacchetti sul server
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: due righe con `100%`.

Cosa fare se va male: `Connection timed out` → rete aziendale: passa a casa o al telefono.

### Q5. [Server] Copia di sicurezza, codice, rebuild dell'api, verifiche delle tessere e degli alberi
Entra con `ssh eugenio`, poi:
```bash
cp -a ~/energia ~/energia_prima_20261109c
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "def tessera_errore\|class Guasti\|async def tessera" ~/energia/fase4-server/servizio/ortofoto.py
cd ~/energia/fase4-server
docker compose build api
docker compose up -d --force-recreate api worker
sleep 60; docker compose ps api worker
docker compose exec -T api python -c "import urllib.request as u, json; print({f['id']: f['zoom'] for f in json.load(u.urlopen('http://localhost:8000/api/ortofoto/fonti'))['fonti']})"
docker compose exec -T api python -c "import urllib.request as u; r = u.urlopen('http://localhost:8000/api/ortofoto/pcn2012/18/139802/95433.jpg'); print(r.status, r.headers['Content-Type'], r.headers.get('X-Ortofoto-Errore'))"
docker compose exec -T api python -c "import urllib.request as u, collections, concurrent.futures as cf; f = lambda i: (lambda r: (r.status, r.headers['Content-Type'], r.headers.get('X-Ortofoto-Errore')))(u.urlopen('http://localhost:8000/api/ortofoto/pcn2012/18/%d/%d.jpg' % (139790 + i % 8, 95420 + i // 8), timeout=40)); print(collections.Counter(cf.ThreadPoolExecutor(40).map(f, range(40))))"
docker compose exec -T api python -c "import urllib.request as u, json; i = json.load(u.urlopen('http://caddy/edifici3d/cc-by/er/prodotti/lidar/indice.json')); a = i.get('celle', {}).get('alberi', []); print(len(a), '1225_4413' in a, [c for c in a if c.startswith('122')][:5])"
```
Cosa aspettarsi: `3` (le tre funzioni nuove); la build finisce con `Built`; api `Up … (healthy)`, worker `Up`; poi
`{'rer2023': [12, 19], 'toscana2023': [12, 19], 'trento2015': [12, 19], 'bolzano2023': [12, 19], 'pcn2012': [12, 18], 's2cloudless2016': [5, 15]}`
(l'ordine può cambiare); la tessera di Bagno di Romagna allo zoom 18: `200 image/jpeg None`; con 40 tessere AGEA insieme
**nessun errore e nessun 502**: un `Counter` con `(200, 'image/jpeg', None)` per quasi tutte e, se la fonte è lenta, qualche
`(200, 'image/png', 'occupata')` (tessere vuote pulite che la pagina richiede da sola); gli alberi: `N True […]` se la
cella del Bufalini c'è, `N False […]` se le chiome lì non sono mai state calcolate (atteso: la pipeline ha solo il DSM della
costa; in Q8 la nota lo dice), oppure un errore `404` se `lidar/indice.json` non c'è (nessun albero sul server).

Cosa fare se va male: api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe; `zoom`
ancora `[12, 20]` → la build ha usato i TOML vecchi: rifai `tar -xzmf` e la build; righe `'fonte'` in quasi tutte le 40
tessere → AGEA non risponde dal server: `docker compose logs --tail 30 api | grep -i ortofoto` e mandami le righe (le pagine
lo diranno con la nota, nessuna riga rossa); per tornare indietro:
`rm -rf ~/energia && mv ~/energia_prima_20261109c ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker`.

### Q6. [Server] Sito e pulizia
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261109c /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/ortofoto.html /srv/energia/sito/fv-producibilita.html
grep -c "passo-coperture" /srv/energia/sito/modelli3d.html; grep -c "fontiNelPunto" /srv/energia/sito/confini_gl.js; grep -c "X-Ortofoto-Errore" /srv/energia/sito/protezione.js; grep -c "function tettoScelto" /srv/energia/sito/edifici_calcoli.js
grep -c "20261109c" /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt; grep -c "Tetti a falde scelti da te" /srv/energia/sito/novita.xml
rm -f ~/codice.tar.gz ~/sito.tar.gz
exit
```
Cosa aspettarsi: quattro righe con N > 0; poi `1`, `2`, N > 0, `1`; due righe con N > 0 e `1` (la voce nuova delle Novità).

Cosa fare se va male: `20261109c` a 0 → `sito.tar.gz` vecchio: rifai Q3 e Q4 (solo il sito) e la prima riga.

### Q7. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma (pagine e script nuovi).

Cosa aspettarsi: «Purge request successful» (o simile).

Cosa fare se va male: il pannello non si apre → rete aziendale.

### Q8. [Browser] Prove (Ctrl+F5; F12 → Console, con «Errors» acceso)
**Righe da ignorare** (non vengono da EuGEnio): `…passkeys-inject.js…` (estensione del browser, gestore di passkey) e tutte
quelle di **`challenges.cloudflare.com`**, che compaiono solo dopo una ricerca o un'altra richiesta protetta (verifica
anti-robot Turnstile, nel suo riquadro): «Connecting to 'data:' violates … connect-src», «Fetch API cannot load data:»,
«Failed to decode downloaded font» / «OTS parsing error», e gli avvisi gialli WebGPU «The powerPreference option is
currently ignored…» e «No available adapters». Le righe gialle di WebGL («GPU stall…») non sono errori.

1. **Niente 502 (punto 1).** Modelli 3D, Bagno di Romagna foglio 54 particella 216 → «Genera il 3D», inclina la vista e
   ingrandisci al massimo; poi «piazza del Duomo», «Firenze». F12 → Console: **nessuna** riga `…/api/ortofoto/… 502`.
   F12 → Rete, filtro `pcn2012`: nessuna richiesta con `/19/` o oltre; filtro `rer2023` o `toscana2023`: nessuna con `/20/`.
2. **Fonte automatica (punto 5).** Modelli 3D (e poi Ortofoto): apri la casella «fonte» nei livelli a destra.
   - Cesena (apertura): scelta «Ortofoto RER 2023-24 (20 cm)»; nell'elenco RER, Geoportale Nazionale, Sentinel-2, **non** la Toscana.
   - «piazza del Duomo», «Firenze»: scelta «Ortofoto Regione Toscana 2023»; nell'elenco Toscana, Geoportale, Sentinel, **non** la RER.
   - «via San Salvatore», «Susegana»: scelta il Geoportale Nazionale (AGEA 2012); nell'elenco solo Geoportale e Sentinel-2.
   - «piazza Maggiore», «Bologna»: RER nell'elenco, ma scelta da sola il Geoportale (la RER lì non ha immagini), con la nota
     «… non ha immagini in questa zona: uso «Geoportale Nazionale …»».
   - A Firenze scegli a mano la Toscana, poi vai a Susegana: torna da sola al Geoportale con la nota ««Ortofoto Regione
     Toscana 2023 (20 cm)» non copre questo punto: torno alla scelta automatica («Geoportale Nazionale …»).».
3. **Coperture (punto 4 e 11:56).** Nel pannello di destra: «3 Edificio», poi **«4 Coperture»**, poi «5 Corpi» e le altre
   rinumerate. In «Coperture»: pulsante con la **tegola** («Tegola»; tooltip «Tetto a falde: clic su un edificio per
   cambiarlo»), «Inclinazione» **22** °, «Reset piani» e «Esporta tetti» spenti, «Importa tetti», riga «Nessun tetto a falde
   scelto: tutti i tetti sono piani.». Sotto la mappa: frecce, stato, «Azzera», «Colore», «Alberi» (niente tegola). Nella
   barra della vista 3D **niente** gruppo «Rilievo ×1 ×1,5 ×2».
4. **Tetti piani e tegola.** Rimini, «Ospedale Infermi» (o viale Settembrini 2) → «Genera il 3D»: tutti i tetti **piani**,
   nota «Tetti: N piani.». Vai alle case di **via Ovidio**: accendi la tegola (diventa mattone, cursore con la tegola), clic
   su una casa: tetto a falde a 22°, riga di stato «Corpo …: tetto a falde di 22° (a capanna) …» e «1 tetto a falde scelto»;
   scrivi 30 in «Inclinazione», clic su un'altra casa vicina: falde a 30°; clic di nuovo sulla prima: torna piana. Con la
   tegola accesa il clic **non** cambia l'edificio scelto. Esc spegne la tegola. Ricarica la pagina (F5), «Genera il 3D»
   sullo stesso edificio: le falde scelte ci sono ancora; in 2D le case scelte hanno il bordo color mattone.
5. **Tabella, immagine, report.** Nella tabella «Corpi» (passo 5) la fonte dice «… tetto a falde scelto dall'utente (30°)
   (a capanna)»; nell'immagine PNG la riga «Tetti: … a falde scelti dall'utente (…), … piani.»; nel report la stessa nota.
6. **Esporta, Reset, Importa.** «Esporta tetti» scarica `eugenio_tetti_2026-11-09.json` (pochi byte). «Reset piani»: accanto
   compaiono «Riporto piani … tetti scelti?», «Sì, riporta tutti piani» e «Annulla» (nessuna finestra del browser);
   «Annulla» non cambia nulla; «Sì, riporta tutti piani» li fa tutti piani. «Importa tetti» con il file appena scaricato:
   «Importati N tetti …» e le falde tornano.
7. **Fotovoltaico.** `fv-producibilita.html` (indirizzo scritto a mano: la pagina è in lavorazione): «Forma dei tetti» ha
   solo «Scelti dall'utente (tegola in «Coperture»)» e «Tutti piani»; con «Tutti piani» le falde spariscono, con «Scelti
   dall'utente» tornano.
8. **Alberi (punto 3).** Rimini, lungomare (per esempio «viale Regina Elena 100»), zoom 17: casella «Alberi» → chiome verdi
   anche nella mappa 2D, e nella vista 3D. Al Bufalini di Cesena, se in Q5 la cella era `False`: la nota «Alberi: nessuna
   chioma dal LiDAR qui attorno … per ora la fascia costiera della zona di Rimini …».
9. **Fonte che non risponde (punto 2).** Non si provoca a mano: se durante le prove AGEA (o un'altra fonte) non risponde,
   sotto la mappa, prima di «Genera il 3D», compare «Ortofoto «…»: la fonte non risponde (o è molto richiesta). Mi fermo e
   riprovo da solo tra N minuti.» e nessuna riga rossa; dopo la pausa le tessere tornano da sole.

Cosa fare se va male: pagina vecchia (niente «Coperture») → Q7 di nuovo e Ctrl+F5; righe rosse diverse da quelle da
ignorare → F12 → Console, clic destro → «Save as…» o screenshot con le righe intere, e F12 → Rete con il filtro sulla parola
della riga; ancora `502` sulle ortofoto → F12 → Rete, clic sulla riga: mandami le intestazioni della risposta (con
`X-Ortofoto-Errore` è la tessera vuota pulita, va bene; un `502` senza intestazioni nostre viene da Caddy o da Cloudflare)
e, sul server, `docker compose logs --tail 30 api | grep -i ortofoto`; tetti che non restano dopo F5 → il browser blocca i
dati dei siti (finestra anonima o impostazioni): la riga di stato lo dice.

### Q9. [PC] Novità per la release
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
python -c "import tomllib; vv=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][:2]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=['https://eugenio.statocritico.it/novita.html','']; [t.extend(['## '+v['titolo']+' ('+v['versione']+')','']+sum([['### '+g[k]]+['- '+x for x in v[k]]+[''] for k in g if v.get(k)],[])) for v in vv]; open('../note_release_c.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
Get-Content ..\note_release_c.md -TotalCount 4
```
Cosa aspettarsi: la prima riga è l'indirizzo delle Novità, poi una riga vuota, poi `## Tetti a falde scelti da te e foto
aerea scelta da sola (20261109c)`; più sotto c'è anche la voce `20261109b` (mai rilasciata a parte).

Cosa fare se va male: errore di Python → mandami la riga.

### Q10. [PC] Commit, push e release `v2026.11.09c`
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_dbtr|estraz_procons|\.gpkg$|DTM5x5|archivi_edifici|archivi_citta|archivi_bari_roma|archivi_er_0911|dtm_veneto|\.tar\.gz$|giornaliero.*\.parquet"
```
```powershell
git commit -m "09/11/2026 b e c: ricerca con un solo Comune e un solo Reset, Colore e Alberi sotto la mappa, celle LiDAR solo se esistono, quote Copernicus fuori dai DTM, tessere segnaposto della Toscana vuote (b); tetti tutti piani e sezione Coperture con la tegola (inclinazione, Reset piani con conferma, esporta e importa, scelte nel browser), tolta l'esagerazione del rilievo, tessere di ortofoto asincrone con errori puliti e fonte ferma dopo errori ripetuti, zoom massimi reali, nota quando una fonte non risponde, fonte dell'ortofoto scelta da sola nel punto, alberi anche in 2D (c); sito ?v=20261109c; procedure AGGIORNAMENTO_2026-11-09b e 09c"
```
```powershell
git push
```
```powershell
gh release create v2026.11.09c --target main --title "EuGEnio 9 novembre 2026 (c) – tetti a falde scelti da te e foto aerea scelta da sola" --notes-file ..\note_release_c.md
```
Cosa aspettarsi: il secondo comando **non stampa nulla**; il push finisce con `… main -> main`; la release stampa
`https://github.com/StatoCritico/eugenio/releases/tag/v2026.11.09c`. Se tutto è a posto, sul server:
`ssh eugenio "rm -rf ~/energia_prima_20261109b ~/energia_prima_20261109c"`.

Cosa fare se va male: righe dal secondo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`; `gh` chiede il login → `gh auth status` e mandami l'uscita (senza token); senza
`gh`: GitHub → Releases → Draft a new release, tag `v2026.11.09c`, titolo come sopra, testo di `..\note_release_c.md`.
