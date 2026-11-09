# Aggiornamento del 09/11/2026 d – correzioni dalle prove Q8 (sito `?v=20261109d`, release `v2026.11.09d`)

Punto di partenza: sito `?v=20261109c` online (procedura Q1–Q10 di `AGGIORNAMENTO_2026-11-09c.md` fatta, release
`v2026.11.09c`). Esito di Q5 sul server: zoom giusti; la tessera singola AGEA 2012 allo zoom 18 «200 image/png fonte»; con
40 tessere insieme 32 «fonte» e 8 «occupata», **nessun 502**; alberi «45 False []». Nel browser, poco dopo, AGEA si vedeva a
Bagno di Romagna: in quel momento AGEA era lenta o rifiutava. Alle 14:26 Paolo ha mandato cinque richieste, alle 14:27
un'aggiunta sugli alberi. Nessun archivio nuovo, nessuna modifica al Caddyfile; nel `.env` nulla di obbligatorio (vedi S5).

## Cosa cambia

| Punto | Causa trovata | Correzione |
|---|---|---|
| **1** «Errori console piovono» (`…/api/ortofoto/strati/catasto/18|19/… 503`, qualche 502) | I **503 erano nostri**: la rotta delle particelle (`strati.py`) era rimasta sincrona; ogni tessera aspettava il turno verso l'Agenzia delle Entrate (2 chiamate al secondo per tutto il sito) tenendo un thread e dopo 8 s rispondeva «503 Fonte dello strato molto richiesta». Non il limite per IP (sarebbe 429) né la fonte. I 502: errori o lentezze dell'Agenzia. In più ogni chiamata chiedeva un blocco di 2×2 tessere ma ne teneva una sola: le altre tre si richiedevano una per una. | Strati come le ortofoto della c: rotta **asincrona**, chiamata alla fonte al più 18 s, semaforo, **tessera vuota pulita** (200, `no-store`, `X-Ortofoto-Errore`, `Retry-After`) invece di 502 e 503, strato **fermo** dopo 6 errori di fila; le **quattro tessere del blocco** vanno tutte in copia (un quarto delle chiamate); particelle fino allo zoom 19. **Terreno**: attesa del turno asincrona fino a 20 s (prima 503 dopo pochi secondi). |
| **1** «Sentinel-2 cloudless 2016 non risponde, ferma per 30 s» | La pagina contava come errore anche «occupata» (il nostro turno verso la fonte non arrivato in tempo), che con la mappa di contesto a zoom bassi capita spesso: 4 in un minuto → fonte ferma. Sentinel-2 rispondeva. | «Occupata» **non ferma più** la fonte: la tessera si richiede poco dopo (un timer per famiglia). Fermano solo gli errori veri. |
| **1** AGEA 2012 in Q5 | Il registro dell'api non diceva quanto durava un errore. | Tempo massimo della chiamata alla fonte **18 s** (prima 12) e nel registro il tempo di ogni errore. Passo **S5** di diagnosi: registro e GetMap diretta dal server con tempo e codice. |
| **2** Tegola | Restava accesa dopo una nuova ricerca. | Si spegne con «Cerca l'indirizzo», «Cerca la particella», «Reset», Invio nei campi e con un edificio scelto dalla ricerca. |
| **3** Via Ovidio (Rimini) e Bufalini: «corpo con cortile; resta piano» | `tettoScelto` rifiutava i corpi con cortile. | Falde **«a distanza dal bordo»** (approssimazione dello straight skeleton): ogni punto del tetto è alto gronda + tan(inclinazione) × distanza dal bordo più vicino, esterno o del cortile; una falda piana per lato (lati quasi allineati uniti), trovata su una griglia da 0,3 m. Il tetto scende verso la strada e verso il cortile. Vale per tutti i corpi con cortile e per le piante complesse (L, U, T); i rettangoli restano a capanna o a padiglione. Stesse falde di sempre: falde a gradini in 3D, tabella, PNG, report, aree FV (anche in fv-producibilita). Prova: corte 40 × 30 m con cortile 20 × 10 m → 8 falde (4 verso la strada, 4 verso il cortile), area FV sul lato del cortile con orientamento verso il cortile. |
| **4** Mappa da allungare; in fv-producibilita più bassa | La colonna della mappa ha l'altezza della finestra; solo Modelli 3D e Ortofoto avevano `flex-shrink: 0`: nelle pagine Edificio e Fotovoltaico la mappa si restringeva sotto il testo introduttivo più lungo. | **Maniglia** sotto ogni mappa MapLibre (Modelli 3D e pagine 3D, Ortofoto, Aggiungi edifici, Importa DXF/IFC): trascinamento col mouse o col dito, frecce con la tastiera, da 280 px al 92 % della finestra, ricordata nel browser per pagina, doppio clic per l'altezza predefinita; MapLibre si adatta durante e dopo (anche in 3D). E `flex-shrink: 0` per tutte le pagine 3D. Patrimonio ha la mappa SVG, che non ne ha bisogno. |
| **5** Clic nella vista 3D | MapLibre (`fill-extrusion`, non un layer nostro) trova già i prismi estrusi sotto il puntatore, pareti e tetti (provato: 60 px sopra la pianta di un corpo alto il corpo si trova), ma li restituisce **nell'ordine degli strati** (edificio scelto, falde, vicini…), non per distanza: la pagina prendeva il primo. | La pagina prende tra i corpi trovati **il più vicino alla camera** (posizione della camera di MapLibre, centro del prisma a metà altezza). Vale per la scelta e per la tegola, anche per i vicini; in 2D resta la sagoma. |
| **Indicatore** (15:49) | Con attese fino a 18–20 s per tessera la mappa sembrava ferma. | Piccolo **orologio** in basso a sinistra sulla mappa (sopra la scala) con «Carico le tessere… (N)» quando ci sono tessere in arrivo (ortofoto, particelle e contorni, terreno, edifici e alberi OSM: contate in `protezione.js`), con il nome della fonte se una tessera aspetta più di 3 s («Ortofoto «…»: risposta lenta»), e «Genero il 3D…» durante «Genera il 3D». Compare solo dopo 400 ms (niente lampeggi a ogni spostamento), sparisce quando tutto è arrivato; `aria-live="polite"`; con «riduci movimento» del sistema la lancetta non gira. È HTML sopra la mappa: **non entra nel PNG**. Su tutte le mappe MapLibre (Modelli 3D e pagine 3D, Ortofoto, Aggiungi edifici, Importa DXF/IFC). |
| **Alberi** (14:27) «gli alberi di Cesena non ci sono» | Le chiome LiDAR ci sono solo nella fascia costiera di Rimini (Q5: 45 celle, nessuna attorno al Bufalini). | Dove manca il LiDAR, con «Alberi» acceso, **chiome indicative da OpenStreetMap** (`natural=tree` e `natural=tree_row`, ODbL 1.0; altezza da `height`/`est_height` o 8 m; chioma da `diameter_crown` o 5 m; filari: una chioma ogni 6 m) dalla rotta nuova `/api/alberi/osm/<cella>.json` (limite e quota di Overpass già esistenti, copia sul server). Boschi (`natural=wood`, `landuse=forest`) **non usati**: estensione e altezza troppo incerte. Verde più chiaro, nota «Alberi: chiome indicative da OpenStreetMap…, altezza … stimata (8 m): entrano anche nelle ombre, come stima», legenda, immagine e report. **Dove c'è il LiDAR vince il LiDAR** (la cella LiDAR non si chiede a OSM). **Decisione**: le chiome OSM entrano nelle ombre, come stima, **solo con «Alberi» acceso** (le chiome LiDAR stanno sempre tra gli ostacoli). Fonti aperte comunali (censimenti del verde di Bologna, Rimini; Cesena: nessun dataset trovato) da verificare: in `DA_FARE.md`. |

## File toccati

- **fase 4**: `servizio/strati.py` (rotta asincrona, `elabora_blocco`, `tessera_errore`, `guasti`), `servizio/terreno.py`
  (attesa asincrona), `servizio/ortofoto.py` (tempo negli errori), `servizio/config.py` (`ORTOFOTO_TIMEOUT_S` 18),
  `servizio/alberi_osm.py` (nuovo), `servizio/app.py`, `.env.example`, `README.md`; test `test_strati.py`,
  `test_alberi_osm.py` (nuovo).
- **fase 5**: `sito/edificio3d.js` (tegola spenta dalla ricerca, `piuVicinoAllaCamera`, alberi OSM), `sito/edifici_calcoli.js`
  (`tettoDistanza`, `latiUniti`), `sito/protezione.js` («occupata», timer per famiglia, famiglia degli alberi OSM),
  `sito/divisore.js` (maniglia), `sito/stile.css` (maniglia, indicatore di caricamento), `protezione.js` anche per l'indicatore, tutte le pagine (`?v=20261109d`), `novita.toml`, `novita.html`,
  `novita.xml`, `EUGENIO_PER_AGENTI.md`, `llms.txt`, `README.md`, `sito/README_stile.md`; test nuovo
  `tests/test_prove_0911d_browser.py` (7 prove).
- **fase 10**: `ortofoto/strati/catasto.toml` (zoom 19), `README.md`.
- Radice: `AGGIORNAMENTO_2026-11-09d.md` (questo), `DA_FARE.md`, `RIEPILOGO.md`, `EUGENIO_PER_AGENTI.md`.

## Test (container, 09/11/2026, una suite alla volta)

- fase 4: **244 passed** (241 + blocco intero in copia e turno mancato degli strati, 2 prove degli alberi OSM).
- fase 10 (senza le prove nel browser): **175 passed**. `test_blocco2_browser.py`: **5 passed** al terzo giro (4 nei primi due): la prova
  «sede dal Patrimonio» (o «pulsante Patrimonio») a volte resta ferma perché la mappa della demo non emette `load`; succede
  **anche con il codice della c** rimesso al suo posto (provato): instabilità dell'ambiente di prova, non della d.
- fase 5, tutta la cartella `tests` con Chromium: **114 passed, 1 saltato** (107 + le 7 prove nuove di `test_prove_0911d_browser.py`: tetto a falde con il cortile e area FV sulla falda verso il cortile, tegola spenta dalla ricerca, maniglia dell'altezza in Modelli 3D, Fotovoltaico e Ortofoto, clic 3D sul volume più vicino, alberi OSM dove manca il LiDAR e LiDAR che vince, tessere «occupata» che non fermano la fonte e particelle senza righe rosse, indicatore di caricamento con tessere lente simulate).
- `costruisci_pagine.py --controlla`: `versione 20261109d: 0 file da rigenerare`.

## Procedura S1–S10

Tempo: circa 40 minuti, prove comprese. Ordine: PC → server → Cloudflare → browser → PC.

### S1. [PC] Zip sopra il clone
Scarica `eugenio_2026-11-09d.zip` in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Measure-Object
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-09d.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261109d" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: `Count : 0` prima (clone pulito dopo Q10); `Count : 1` dopo; quattro righe nuove:
`?? AGGIORNAMENTO_2026-11-09d.md`, `?? fase4-server/servizio/alberi_osm.py`, `?? fase4-server/tests/test_alberi_osm.py`
e `?? fase5-sito/tests/test_prove_0911d_browser.py`.

Cosa fare se va male: `Count` diverso da 0 prima → `git status --short` e mandami l'uscita; `Count : 0` dopo → zip
sbagliato, riscaricalo; altre righe `??` → mandamele.

### S2. [PC] Pagine e test della fase 5, segreti
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
Cosa aspettarsi: `versione 20261109d: 0 file da rigenerare`; test verdi (senza Chromium le prove nel browser si saltano);
quattro righe `.gitignore:…`.

Cosa fare se va male: test rossi → mandami le ultime 30 righe; meno di quattro righe → fermati e mandamele.

### S3. [PC] Pacchetti del codice e del sito
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
Cosa aspettarsi: `Count : 0`.

Cosa fare se va male: `Count` diverso da 0 → cancella `..\codice.tar.gz` e mandami le righe.

### S4. [PC] Copia dei pacchetti sul server
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: due righe con `100%`.

Cosa fare se va male: `Connection timed out` → rete aziendale: passa a casa o al telefono.

### S5. [Server] Diagnosi di AGEA 2012 (prima del rebuild, con l'api della c)
Entra con `ssh eugenio`, poi:
```bash
cd ~/energia/fase4-server
docker compose logs --since 3h api | grep -i "ortofoto pcn2012" | tail -20
docker compose exec -T api python -c "import time, httpx; from servizio import ortofoto as O; f = O.fonti()['pcn2012']; u = O.url_tessera(f, 18, 139802, 95433); [print((lambda t, r: (r.status_code, r.headers.get('content-type'), len(r.content), round(time.time() - t, 1)))(time.time(), httpx.get(u, timeout=40, follow_redirects=True))) for _ in range(3)]"
curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download} B in %{time_total} s\n" "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_12.map&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=OI.ORTOIMMAGINI.2012.32,OI.ORTOIMMAGINI.2012.33&STYLES=&CRS=EPSG:3857&BBOX=1334590.514,5448125.628,1334743.388,5448278.502&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg"
```
Cosa aspettarsi: le righe del registro dicono la causa degli errori di Q5 (`ReadTimeout` = AGEA lenta oltre 12 s;
`ConnectError`/`ConnectTimeout` = rete o rifiuto; `risposta 500 text/xml` = errore del servizio); poi tre righe
`(200, 'image/jpeg', N, T)` con T in secondi, e la riga di `curl` `200 image/jpeg N B in T s`.

Cosa fare se va male: niente di bloccante, il passo serve a capire. Annota i tempi T e mandameli:
- T sotto 5 s → AGEA ora va: in Q5 era un momento cattivo; con la d (18 s) basta;
- T tra 10 e 18 s → AGEA è lenta dal server: la d (18 s) aiuta;
- T oltre 18 s o `timed out` → aggiungi nel `.env` la riga `ORTOFOTO_TIMEOUT_S=20` (non di più: attesa 8 s + 20 s stanno
  sotto i 30 s di Caddy) e dimmelo;
- codice 403/429/503 in pochi decimi → AGEA rifiuta l'IP del server: dimmelo, scriveremo al Geoportale.

### S6. [Server] Copia di sicurezza, codice, rebuild dell'api, verifiche
Ancora in `~/energia/fase4-server`:
```bash
cp -a ~/energia ~/energia_prima_20261109d
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "def elabora_blocco\|async def tessera" ~/energia/fase4-server/servizio/strati.py && ls ~/energia/fase4-server/servizio/alberi_osm.py
docker compose build api
docker compose up -d --force-recreate api worker
sleep 60; docker compose ps api worker
docker compose exec -T api python -c "from servizio import config as C; print(C.ORTOFOTO_TIMEOUT_S)"
docker compose exec -T api python -c "import urllib.request as u, collections, concurrent.futures as cf; f = lambda i: (lambda r: (r.status, r.headers.get('X-Ortofoto-Errore')))(u.urlopen('http://localhost:8000/api/ortofoto/strati/catasto/19/%d/%d.png' % (279994 + i % 8, 190370 + i // 8), timeout=40)); print(collections.Counter(cf.ThreadPoolExecutor(32).map(f, range(32))))"
docker compose exec -T api python -c "import urllib.request as u, json; d = json.load(u.urlopen('http://localhost:8000/api/alberi/osm/1225_4413.json', timeout=40)); print(len(d.get('alberi', [])), d.get('licenza'), d.get('stima'))"
```
Cosa aspettarsi: `2` e il percorso del file; la build finisce con `Built`; api `Up … (healthy)`, worker `Up`; `18.0` (o il
valore messo nel `.env` in S5); per le 32 particelle di Cesena allo zoom 19 un `Counter` con solo `(200, None)` (tessere
vere) e, se l'Agenzia è lenta, qualche `(200, 'occupata')` o `(200, 'fonte')`: **mai** un'eccezione `HTTP Error 503` o
`502`; gli alberi OSM attorno al Bufalini: `N ODbL 1.0 True` con N > 0 (se OpenStreetMap ha alberi lì; `0 None True` se
Overpass non ha risposto: riprova tra un minuto).

Cosa fare se va male: api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe;
`HTTP Error 404` sugli alberi → l'api è quella vecchia: rifai la build; per tornare indietro:
`rm -rf ~/energia && mv ~/energia_prima_20261109d ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker`.

### S7. [Server] Sito e pulizia
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261109d /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/ortofoto.html /srv/energia/sito/fv-producibilita.html
grep -c "maniglia-mappa" /srv/energia/sito/divisore.js; grep -c "carico-mappa" /srv/energia/sito/protezione.js; grep -c "function tettoDistanza" /srv/energia/sito/edifici_calcoli.js; grep -c "piuVicinoAllaCamera" /srv/energia/sito/edificio3d.js; grep -c "alberi/osm" /srv/energia/sito/edificio3d.js
grep -c "20261109d" /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt; grep -c "anche con il cortile" /srv/energia/sito/novita.xml
rm -f ~/codice.tar.gz ~/sito.tar.gz
exit
```
Cosa aspettarsi: quattro righe con N > 0; poi N > 0, N > 0, `1`, N > 0, N > 0; due righe con N > 0 e `1`.

Cosa fare se va male: `20261109d` a 0 → `sito.tar.gz` vecchio: rifai S3 e S4 (solo il sito) e la prima riga.

### S8. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma.

Cosa aspettarsi: «Purge request successful» (o simile).

Cosa fare se va male: il pannello non si apre → rete aziendale.

### S9. [Browser] Prove (Ctrl+F5; F12 → Console, con «Errors» acceso)
Righe da ignorare (non vengono da EuGEnio): `…passkeys-inject.js…` e tutte quelle di `challenges.cloudflare.com` (CSP, OTS,
avvisi WebGPU), come in Q8.

1. **Console senza righe rosse nostre (punto 1).** Modelli 3D a Cesena, accendi «Confini delle particelle catastali» e
   ingrandisci fino a 19–20, sposta la mappa qualche volta; poi Bagno di Romagna (foglio 54, particella 216) e «Genera il
   3D». **Nessuna** riga rossa `…/api/ortofoto/… 503` o `502`. Le particelle arrivano tutte (al più qualche tessera dopo
   pochi secondi). Se la fonte non risponde davvero, sotto la mappa: «Particelle catastali e contorni degli edifici: la
   fonte non risponde…». Nessuna nota «Sentinel-2 … non risponde» se Sentinel-2 risponde.
2. **Tegola e ricerca (punto 2).** Accendi la tegola, poi «Cerca l'indirizzo» (o «Cerca la particella», o «Reset»): la
   tegola si spegne (bianca).
3. **Cortile (punto 3).** Rimini, **via Ovidio**: «Genera il 3D» sulla casa a corte, tegola, clic sul corpo principale: tetto
   a falde, riga di stato «… (a padiglione, che scende anche verso il cortile) …»; in 3D le falde scendono verso la strada e
   verso il cortile; nella tabella «Falde dei tetti» falde con orientamenti verso il cortile. Cesena, **ospedale Bufalini**
   (apertura della pagina): clic sui corpi con la corte: anche loro prendono le falde. In fv-producibilita un'area FV su una
   falda verso il cortile ne prende orientamento e inclinazione.
4. **Altezza della mappa (punto 4).** Sotto la mappa una barretta grigia: trascinala in giù (anche col dito sul telefono):
   la mappa si allunga, la vista (anche 3D) si adatta; dopo F5 l'altezza resta; doppio clic sulla barretta: torna
   all'altezza normale. In fv-producibilita la mappa non è più bassa di quella di Modelli 3D.
5. **Clic in 3D (punto 5).** Nella vista 3D inclinata, clic sulla parete o sul tetto di un edificio vicino alto (anche dove
   la sua pianta a terra è nascosta): si sceglie quell'edificio, non quello dietro né la pianta a terra; lo stesso con la
   tegola (cambia il tetto dell'edificio che vedi davanti).
6. **Alberi (14:27).** Cesena, Bufalini, casella «Alberi» accesa: chiome verde chiaro, sotto la mappa «Alberi: chiome
   indicative da OpenStreetMap (© contributori OpenStreetMap, ODbL 1.0), altezza dai dati OSM o stimata (8 m): entrano anche
   nelle ombre, come stima.»; in legenda «alberi: chiome indicative da OpenStreetMap (ODbL), altezza stimata»; nell'immagine
   PNG la riga «Alberi: chiome indicative da OpenStreetMap…». Prova anche in **viale Carlo Alberto dalla Chiesa** (Cesena) e
   a **Bologna**. Rimini, **lungomare**: chiome verde scuro dal LiDAR (vince il LiDAR); se OpenStreetMap non ha alberi in una
   zona, «Alberi: nessuna chioma qui attorno…».

7. **Indicatore di caricamento (15:49).** Modelli 3D, scegli a mano la fonte «Geoportale Nazionale» e sposta la mappa: in basso
   a sinistra, sopra la scala, compare l'orologio «Carico le tessere… (N)»; se AGEA è lenta, dopo 3 s «… Ortofoto
   «Geoportale Nazionale – ortofoto AGEA 2012 …»: risposta lenta»; quando le tessere sono arrivate sparisce. Con piccoli
   spostamenti veloci non lampeggia. Durante «Genera il 3D» dice «Genero il 3D…». Nell'immagine PNG scaricata l'orologio
   **non** c'è. Lo stesso in Ortofoto e in fv-producibilita.

Cosa fare se va male: pagina vecchia (niente barretta sotto la mappa) → S8 di nuovo e Ctrl+F5; righe rosse nostre → F12 →
Console, screenshot con le righe intere, e F12 → Rete, clic sulla riga: mandami le intestazioni della risposta (con
`X-Ortofoto-Errore` è una tessera vuota pulita: va bene); alberi assenti a Cesena → F12 → Rete, filtro `alberi/osm`: mandami
codice e intestazioni (con `X-Ortofoto-Errore: fonte` Overpass non ha risposto: riprova dopo un minuto).

### S10. [PC] Commit, push e release `v2026.11.09d`
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
git commit -m "09/11/2026 d: particelle e terreno asincroni con tessere d'errore pulite e blocco 2x2 in copia, occupata che non ferma la fonte, tempo massimo delle ortofoto 18 s; tegola spenta dalla ricerca; tetto a falde anche con il cortile; maniglia per l'altezza della mappa; clic 3D sul volume piu vicino; alberi indicativi da OpenStreetMap dove manca il LiDAR; sito ?v=20261109d; procedura AGGIORNAMENTO_2026-11-09d"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_d.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.09d --target main --title "EuGEnio 9 novembre 2026 (d) – tetti con il cortile, mappa più alta e alberi da OpenStreetMap" --notes-file ..\note_release_d.md
```
Cosa aspettarsi: il terzo comando **non stampa nulla**; il push finisce con `… main -> main`; la release stampa
`https://github.com/StatoCritico/eugenio/releases/tag/v2026.11.09d`. Se tutto è a posto, sul server:
`ssh eugenio "rm -rf ~/energia_prima_20261109b ~/energia_prima_20261109c ~/energia_prima_20261109d"`.

Cosa fare se va male: righe dal terzo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`; `gh` chiede il login → `gh auth status` e mandami l'uscita (senza token); senza
`gh`: GitHub → Releases → Draft a new release, tag `v2026.11.09d`, titolo come sopra, testo di `..\note_release_d.md`.
