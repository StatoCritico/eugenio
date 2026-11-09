# Aggiornamento del 09/11/2026 – correzioni dalle prove J10, Roma, Bari e Bologna intere (sito `?v=20261109a`, release `v2026.11.09`)

Punto di partenza: release **`v2026.11.07b`** pubblicata l'08/11/2026 alle 22:42, sito `?v=20261107b` online con 43
archivi degli edifici. Nella notte del 09/11 Paolo ha fatto le prove J10 (`AGGIORNAMENTO_2026-11-07.md`, sezione I, passo
J10) e ha segnalato i problemi A–J. Questa procedura unica (decisione del 09/11: **un'unica pubblicazione**) porta online:

- le correzioni dei punti A–J (codice dell'api, pagine del sito, fase 10), con la nuova versione del sito **`?v=20261109a`**;
- gli archivi di **Roma** e **Bari per il comune intero** (prima: procedura M1–M10, ora dentro i passi N4, N6–N8 e N10);
- i **29 archivi DBTR dell'Emilia-Romagna del 09/11** (estrazioni 354181–354187): **Bologna intera**, Castel Bolognese
  intero, Ravenna con parte del forese, Misano rifatto con quasi tutto Coriano, 17 comuni della Romagna e 8 comuni vicini a
  Bologna (passi nuovi **N4 bis** e **N7 bis**; `archivi.json` passa da 43 a **69 voci**);
- la release **`v2026.11.09`**.

La procedura M1–M10 di questo file (prima stesura del 09/11) **non va più eseguita da sola**: i suoi passi e le sue prove
sono qui sotto. Se M1–M10 è già stata fatta, salta N6 e N7 e in N8 la riga di `archivi-json` (resta tutto il resto).

## Cosa cambia: punti A–J

| Punto | Causa trovata | Correzione |
|---|---|---|
| **A** 429 a valanga | Il limite per IP contava **anche le tessere servite dalla copia** (ortofoto 3000/h, terreno solo le nuove, edifici OSM 60/h compresa la copia); particelle e contorni consumavano lo **stesso** limite delle ortofoto; le tessere AGEA 2012 avevano `no-store` (richieste di nuovo a ogni ritorno); ritmo verso la fonte basso (RER 4/s, AGEA 2/s e 2000/h per tutto il sito, attesa 6 s). Dopo il primo 429 la pagina continuava a chiedere tessere e i contorni OSM rifiutati restavano vuoti fino al ricaricamento. L'IP è giusto: Caddy mette `CF-Connecting-IP` in `X-Forwarded-For` su **tutti** i blocchi `/api/` (nessun percorso condiviso). | Contano solo le tessere chieste davvero alla fonte: `ORTOFOTO_ORA` 12000, `STRATI_ORA` 12000 (nuovo), `TERRENO_ORA` 6000, `EDIFICI_OSM_ORA` 300 (le tessere OSM dei contorni ora contano qui e nel tetto di Overpass del sito); dalla copia tetto anti-abuso `TESSERE_COPIA_ORA` 60000 e `EDIFICI_OSM_COPIA_ORA` 3000. Il 429 porta `Retry-After` (quando si libera il 10 % del limite) e `X-EuGEnio-Limite`. Ritmo: RER 8/s, AGEA 4/s e 4000/h, attesa 8 s; AGEA 2012 con la copia **del solo browser** (`private, max-age=86400`, nessuna copia sul server né su Cloudflare). Nella pagina (`protezione.js`): dopo un 429 la fonte si ferma per il tempo del server (da 30 s a 20 minuti), le richieste successive non partono (nessuna riga in Console), **nota sotto la mappa prima di «Genera il 3D»** con la fonte, «limite orario» e «riprovo da solo tra N minuti»; alla ripresa le tessere si ricaricano e la nota sparisce alla prima risposta buona. Errori delle tessere di MapLibre non più in Console uno per uno. |
| **B** Previsioni | Il blocco «Servizio sperimentale…» era rimasto in `index.html`. | Tolto (come Dati climatici e Legge 10); test. |
| **C** Frecce dell'ortofoto | Croce di frecce su tre righe (griglia 3 × 3) e stato e «Azzera» in colonna. | Una riga: ← ↑ ↓ →, «1 m», «Ortofoto spostata: …» (accorciato con i puntini, intero nel tooltip) e «Azzera»; anche in Ortofoto e con la colonna stretta. |
| **D** Ricerca | 1–2: ordine dei campi e nessun «Reset». 3: `dati/mappa/01.json` (Piemonte) e `15.json` (Campania) contenevano **`NaN`**: il comune 001168 si chiama davvero «None» (TO) e la sigla di Napoli è «NA», e pandas li aveva letti come valori mancanti; il browser non legge JSON con `NaN`, quindi **tutto il Piemonte** (Torino compresa) e la Campania mancavano alla ricerca per comune. | Comune prima dell'Indirizzo, pulsante **«Reset»** in ogni blocco (Modelli 3D, Ortofoto, pagine 3D: `cerca_luogo.js`); i due file corretti; `costruisci_mappa.py` scrive JSON stretto; la fase 3 legge l'elenco ISTAT con `keep_default_na=False`; `/api/comuni` rimette «None» e «NA»; test su tutti i 7.896 comuni. |
| **E** Colore e alberi | — | Menu a discesa «Colore degli edifici» come quello dell'asterisco (stessa tastiera): grigio (predefinito), giallo, rosso, indaco, violetto; l'edificio scelto resta nel colore primario (arancio), gli edifici OSM restano marroni. Casella **«Alberi»**, spenta in partenza. Ricordati nel browser (`localStorage`, con try/catch), nel PNG («edifici vicini … in rosso», «alberi in verde») e in legenda. |
| **F** Bagno di Romagna | Il corpo principale della particella 54/216 (178 m², gronda 10,7 m, quota 511 m) ha un «buco» di 8,3 m² **occupato dall'altro corpo** della particella (un volume interno di 4 m): la regola «corpo con cortile» lo rendeva piano. Le regole pianura/montagna erano giuste (600 m resta). | Cortile solo se il buco è di almeno **25 m²** o del **10 %** della pianta, in JS (`edifici_calcoli.js`) e in Python (`tetti.py`), con le prove di parità: ora capanna a 22°. Nella mappa 3D le falde si disegnano per l'edificio scelto; i vicini restano volumi piani (come prima). |
| **G** Veneto | 429 del punto A. Le fonti ci sono e rispondono (prove dal container, 09/11): AGEA 2012 del Geoportale a Susegana (1,5 s a tessera), Sentinel-2, terreno Copernicus 64–248 m (DTM del Veneto solo se J5 bis è stato fatto). | Punto A. |
| **H** Bologna | **Ortofoto**: la RER non è lenta (0,3–0,5 s a tessera, misurate) ma la RER 2023-24 **non ha immagini** a Bologna, Modena, Parma, Imola, Ferrara, Faenza, Bagno di Romagna e Comacchio (tessere vuote, a ogni scala), mentre Cesena, Ravenna, Rimini, Forlì, Lugo le hanno; più il 429. I WMS AGEA della Regione ci sono ma sono esclusi dalla decisione del § 6. **Due Torri**: vedi sotto. | Il proxy dichiara le tessere vuote (`X-Ortofoto-Vuota: 1`); Modelli 3D, Ortofoto e pagine 3D, finché l'utente non sceglie a mano, passano da sole alla fonte successiva (AGEA 2012 del Geoportale, poi Sentinel-2) e lo dicono. Copia preventiva **non fatta**: la RER risponde in fretta e una copia dei 28 comuni fino allo zoom 18 vorrebbe centinaia di migliaia di tessere (decine di ore al ritmo della fonte). |
| **I** Città | 429 del punto A. Fonti verificate dal container (09/11): AGEA 2012 piena a Venezia, Roma, Bari, Napoli, Palermo, Trento, Genova Nervi; Trento anche PAT 2015; terreno Copernicus a Roma e Trento; particelle dell'Agenzia delle Entrate a Roma, Bologna, Torino. Genova: fuori dalle 4 tavole il ripiego OSM partiva, ma finiva subito nei 60 richieste/ora. | Punto A. |
| **J** «La mappa impazzisce» | Allo zoom 9–15,5 un clic che non cadeva su un edificio sceglieva il comune e faceva **`fitBounds` sul comune intero** (a Roma, senza edifici visibili per i 429, tutto il comune). Allo zoom < 9 lo stesso con la regione. | Un clic sulla mappa **non sposta mai la vista**: regione e comune si evidenziano soltanto, con il messaggio; ci si sposta con la piccola mappa, la ricerca, la rotella e il trascinamento. Testi di aiuto aggiornati. |

**Due Torri (archivio di Bologna dell'08/11)**: nel DBTR c'è **un solo volume** per le torri (UVL id 47888, 157,8 m²,
19,3 × 19,1 m, centro 44,49421 N 11,34678 E, edificio di tipo «Altro», foglio 0) **senza nessuna altezza** (`H_UVL` 0,
`B_UVL` 0, `H_GRONDA` e `H_COLMO` vuoti): la preparazione lo scarta (altezza assente). La Garisenda non ha un volume suo.
Nessun corpo dell'archivio tocca le sagome OSM delle torri (Asinelli 231 m², Garisenda 58 m²); attorno alla piazza il
corpo più alto è di 30,7 m. Le altezze vere sono Asinelli 97,2 m e Garisenda 47–48 m: per vederle serve una correzione
dell'archivio (vedi `DA_FARE.md`), non è un errore della pagina.

## Archivi di Roma e Bari (comune intero)

| Città | Prima (08/11) | Ora (09/11) | Cartella |
|---|---|---|---|
| **Roma** | foglio 374, 277.918 corpi, senza `istat` (zona coperta = riquadro) | **comune intero 058091**: fogli DBGT 2014 364, 365, 373, 374, 375, 386, 387; 384.621 corpi (250.170 edifici); zona coperta = confine ISTAT; nome «DB topografico Regione Lazio 2014 – Roma» | `cc-by/laz/roma` (CC BY 4.0) |
| **Bari** | 5 elementi CTR, 32.105 corpi, senza `istat` | **comune intero 072006**: 31 elementi CTR dei fogli 438 e 439, 73.205 corpi, DTM 8 m di 33 elementi; nome «Bari – CTR 2006 Regione Puglia» | `iodl/pug/bari` (IODL 2.0) |

- Roma: volumi tenuti secondo `COD_ISTAT` (058091); i 142 volumi col codice «058000» solo se cadono nel confine ISTAT; i
  volumi del foglio 374 di altri comuni (Fiumicino, Ciampino, Frascati, …: 18.806) non ci sono più; nessun doppione.
- Bari: edifici nel confine ISTAT +150 m; quote a terra dal DTM 8 m. `archivi.json`: **sempre 43 voci**, Roma e Bari con
  `"istat"`. Comando di preparazione `python -m edifici3d.b_regioni dbgt-fogli` (non serve sul server).

| File (in `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_bari_roma\`) | Dimensione | SHA-256 |
|---|---|---|
| `edifici_laz_roma_2026-11-09.tar.gz` | 126 MB | `357967f64d29afa2d07a2d48937929e4a9459f27d6e1c69302e1a1daf1ecb5ae` |
| `edifici_pug_bari_2026-11-09.tar.gz` | 25 MB | `4d9450e7d0c2f0eabc36902bdfe386b1c46d763c88f1b07b4fc668cd810d888f` |
| `SHA256SUMS_bari_roma_2026-11-09.txt` | 2 righe | — |

## Archivi DBTR dell'Emilia-Romagna del 09/11 (estrazioni 354181–354187)

Tre archivi online **si sostituiscono** (la cartella vecchia va messa da parte in N7 bis) e 26 sono nuovi; tutti in
`cc-by/er/<comune>` (CC BY 4.0), tutti con `"problemi": []` e `"avvisi": []`. Dettagli, fogli e scelte (Coriano, fogli
mancanti di Bologna, Verucchio e Fusignano) nel README della fase 10, sezione «Comuni dell'08/11 e del 09/11/2026».

| Archivio | Prima | Ora |
|---|---|---|
| `bologna` | 66.283 corpi, 281 fogli, con pezzi dei comuni vicini | **comune intero 037006**: 61.813 corpi, mancano solo i fogli rurali 63–66, 89, 133, 250; i comuni vicini hanno archivi loro |
| `ravenna` | 27.525 corpi (città) | 42.574 corpi, «DBTR Emilia-Romagna – Ravenna (città e parte del forese)», parziale |
| `misano-adriatico` | 11.964 corpi, Coriano 18 fogli | 14.347 corpi, Coriano 39 fogli su 46, «… Misano Adriatico, Morciano e Coriano (centro e frazioni principali)», parziale |
| `castel-bolognese` | — | comune intero 039006, 2.815 corpi |
| 17 comuni della Romagna | — | parziali, «… <Comune> (centro e frazioni principali)»: Gambettola, Predappio, Riolo Terme, Longiano, Gatteo, Massa Lombarda, Fusignano, Meldola, Verucchio, Castrocaro Terme e Terra del Sole, Bertinoro, Solarolo, Sant'Agata sul Santerno, Sarsina, Dovadola, Premilcuore, Sant'Agata Feltria |
| 8 comuni vicini a Bologna | — | parziali, «… <Comune> (zona verso Bologna)»: Casalecchio di Reno, San Lazzaro di Savena, Zola Predosa, Calderara di Reno, Castel Maggiore, Granarolo dell'Emilia, Sasso Marconi, Pianoro |

File in `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_er_0911\`: 29 `edifici_dbtr_<comune>_2026-11-09.tar.gz`
(91 MB in tutto; Bologna 35 MB, Ravenna 23 MB, Misano 8 MB, gli altri da 0,1 a 2,4 MB) e `SHA256SUMS_er_2026-11-09.txt`
(29 righe). La pagina legge ora fino a **150 archivi** (`edificio3d.js`, `ortofoto.js`: prima 60, che con 69 voci
avrebbero tagliato gli ultimi 9); in Ortofoto gli indici degli archivi si chiedono tutti insieme.

## File toccati

- **fase 4**: `servizio/protezione.py` (tipi `strati`, `tessere_copia`, `edifici_osm_copia`; `Limitatore.attesa`; 429 con
  `Retry-After` e `X-EuGEnio-Limite`), `servizio/config.py`, `servizio/ortofoto.py` (copia fuori dal limite, `X-Ortofoto-Vuota`,
  AGEA con la copia del browser), `servizio/strati.py`, `servizio/terreno.py`, `servizio/edifici_osm.py`
  (`regionali_in_copia`), `servizio/app.py` (`/api/comuni`), `.env.example`, `README.md`; test `test_ortofoto.py`,
  `test_strati.py`, `test_edifici_osm.py`.
- **fase 5**: `sito/protezione.js` (limiti delle fonti della mappa, `EUGENIO_LIMITI`), `sito/edificio3d.js` (colore,
  alberi, clic, fonti vuote; fino a 150 archivi), `sito/ortofoto.js` (fino a 150 archivi, indici chiesti insieme), `sito/strati_gl.js`, `sito/cerca_luogo.js`, `sito/sposta_ortofoto.js`,
  `sito/edifici_calcoli.js`, `sito/aggiungi_dbtr.js`, `sito/importa_modello.js`, `sito/stile.css`, `sito/index.html`
  (avviso tolto), `sito/dati/mappa/01.json` e `15.json`, `costruisci_mappa.py`, `costruisci_pagine.py` (versione anche in
  `interno/`), `novita.toml` (voce `20261109a`), tutte le pagine (`?v=20261109a`), `novita.html`, `novita.xml`,
  `EUGENIO_PER_AGENTI.md`, `llms.txt`, `README.md`, `sito/README_stile.md`; test `test_costruisci_pagine.py` e il nuovo
  `tests/test_prove_0911_browser.py`.
- **fase 3**: `meteo_storico/comuni.py`, `meteo_storico/territorio.py` (elenco ISTAT con «None» e «NA» come testi).
- **fase 10**: dal 09/11 notte `edifici3d/dividi.py` (nuovo: estrazioni raggruppate divise per comune),
  `edifici3d/__main__.py` (comando `dividi`), `edifici3d/b_regioni.py` (province dell'ER in `REGIONE_ISTAT`),
  `edifici3d/uvl.py` (`castel-bolognese` in `COMUNI_ISTAT`), test nuovo `tests/test_dividi.py`; `edifici3d/tetti.py` (cortili veri), `ortofoto/emilia_romagna.toml` e `italia.toml` (ritmo), `README.md`;
  test `test_tetti.py`. Dal 09/11 mattina: `edifici3d/b_regioni.py` (`dbgt-fogli`), `tests/test_adattatori_b.py`,
  `fonti/lazio.toml`, `fonti/puglia.toml`, `fonti/regioni.toml`.
- Radice: `AGGIORNAMENTO_2026-11-09.md` (questo), `DA_FARE.md`, `RIEPILOGO.md`, `EUGENIO_PER_AGENTI.md`.

## Test (container, 09/11/2026, una suite alla volta)

- fase 4: **236 passed** (232 + limite della copia e `Retry-After`, `Limitatore.attesa`, tessere vuote, limiti degli strati).
- fase 10 (senza le prove nel browser): **174 passed** (172 + cavedio + `test_dividi.py`, 09/11 notte).
- fase 5, tutta la cartella `tests` con Chromium: **88 passed, 1 saltato** (comprese le 7 prove nuove di
  `test_prove_0911_browser.py`); fase 10 `test_blocco2_browser.py`: **5 passed**.
- `costruisci_pagine.py --controlla`: `versione 20261109a: 0 file da rigenerare`.
- Ripetuti il 09/11 notte dopo gli archivi del 09/11 (limite di 150 archivi, `dividi`, novità): fase 4 **236**, fase 10
  **174**, fase 5 con Chromium **88 passed, 1 saltato**.

## Procedura N1–N12

Tempo: circa 1 ora e mezza, prove comprese, più la copia degli archivi (151 MB di Roma e Bari, 91 MB dell'Emilia-Romagna). Ordine: PC → server → Cloudflare →
browser → PC.

### N1. [PC] Zip sopra il clone
Scarica di nuovo `eugenio_2026-11-09.zip` (quello nuovo, con la versione `20261109a`: ha lo stesso nome dello zip della
prima stesura) in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Measure-Object
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-09.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261109a" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: `Count : 0` prima (clone pulito dopo J11), oppure un numero piccolo se avevi già estratto lo zip della
prima stesura (M10 non fatto: va bene, entra tutto nel commit di N11); dopo l'estrazione `Count : 1`; righe nuove:
`?? fase10-edifici3d/edifici3d/dividi.py`, `?? fase10-edifici3d/tests/test_dividi.py`,
`?? fase5-sito/tests/test_prove_0911_browser.py` e, se non l'avevi già, `?? AGGIORNAMENTO_2026-11-09.md` (tre o quattro righe).

Cosa fare se va male: `Count : 0` dopo l'estrazione → zip vecchio (prima stesura), riscaricalo; altre righe `??` →
mandamele (nessun commit finché non è chiaro).

### N2. [PC] Pagine e test della fase 5, segreti
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
Cosa aspettarsi: `versione 20261109a: 0 file da rigenerare`; test verdi (senza Chromium sul PC le prove nel browser si
saltano: va bene); quattro righe `.gitignore:…`.

Cosa fare se va male: test rossi → mandami le ultime 30 righe; meno di quattro righe → fermati e mandamele.

### N3. [PC] Pacchetti del codice e del sito
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

### N4. [PC] Copia sul server: pacchetti e archivi di Roma e Bari
Nella cartella `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_bari_roma\` devono esserci i due tar e
`SHA256SUMS_bari_roma_2026-11-09.txt` (se hai già fatto M1–M10, copia solo i due pacchetti: prima riga).
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
```powershell
ssh eugenio "mkdir -p ~/archivi_bari_roma"
```
```powershell
scp C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_bari_roma\*_2026-11-09.tar.gz C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_bari_roma\SHA256SUMS_bari_roma_2026-11-09.txt eugenio:~/archivi_bari_roma/
```
Cosa aspettarsi: due righe con `100%` (codice e sito), poi tre righe con `100%` (Roma 126 MB, Bari 25 MB, lo `SHA256SUMS`).

Cosa fare se va male: `No such file` → la cartella degli archivi sul PC non è piena: copiala da `archivi_bari_roma/` dei
file che ti ho dato; `Connection timed out` → rete aziendale: passa a casa o al telefono.

### N4 bis. [PC] Copia sul server: archivi DBTR dell'Emilia-Romagna del 09/11
Nella cartella `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_er_0911\` devono esserci i 29 tar
`edifici_dbtr_<comune>_2026-11-09.tar.gz` e `SHA256SUMS_er_2026-11-09.txt`.
```powershell
(Get-ChildItem C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_er_0911\edifici_dbtr_*_2026-11-09.tar.gz).Count
```
```powershell
ssh eugenio "mkdir -p ~/archivi_er_0911"
```
```powershell
scp C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_er_0911\*_2026-11-09.tar.gz C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_er_0911\SHA256SUMS_er_2026-11-09.txt eugenio:~/archivi_er_0911/
```
Cosa aspettarsi: `29`; poi 30 righe con `100%` (Bologna 35 MB, Ravenna 23 MB, gli altri piccoli, lo `SHA256SUMS`).

Cosa fare se va male: un numero diverso da 29 → la cartella sul PC non è piena: copiala di nuovo da `archivi_er_0911/` dei
file che ti ho dato; `Connection timed out` → rete aziendale: passa a casa o al telefono.

### N5. [Server] Copia di sicurezza, codice, limiti nel `.env`, rebuild di api ed edifici
Entra con `ssh eugenio`, poi:
```bash
cp -a ~/energia ~/energia_prima_20261109
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "TESSERE_COPIA_ORA" ~/energia/fase4-server/servizio/config.py
cd ~/energia/fase4-server
for kv in ORTOFOTO_ORA=12000 STRATI_ORA=12000 TESSERE_COPIA_ORA=60000 EDIFICI_OSM_ORA=300 EDIFICI_OSM_COPIA_ORA=3000 TERRENO_ORA=6000 ORTOFOTO_ATTESA_S=8; do k=${kv%%=*}; if grep -q "^$k=" .env; then sed -i "s|^$k=.*|$kv|" .env; else echo "$kv" >> .env; fi; done
grep -E '^(ORTOFOTO_ORA|STRATI_ORA|TESSERE_COPIA_ORA|EDIFICI_OSM_ORA|EDIFICI_OSM_COPIA_ORA|TERRENO_ORA|ORTOFOTO_ATTESA_S)=' .env
docker compose build api
docker compose up -d --force-recreate api worker
docker compose --profile edifici build edifici-lidar
docker compose --profile edifici up -d --force-recreate edifici-coda
sleep 60; docker compose ps api worker
docker compose exec -T api python -c "from servizio import config as C; print(C.ORTOFOTO_ORA, C.STRATI_ORA, C.TESSERE_COPIA_ORA, C.EDIFICI_OSM_ORA, C.EDIFICI_OSM_COPIA_ORA, C.TERRENO_ORA, C.ORTOFOTO_ATTESA_S)"
docker compose exec -T api python -c "import urllib.request as u; [print(r.status, r.headers['X-Ortofoto-Copia']) for r in (u.urlopen('http://localhost:8000/api/ortofoto/rer2023/13/4363/2971.jpg?t=1') for _ in range(2))]"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/rer2023/17/69665/47409.jpg?t=1'); print(r.status, r.headers.get('X-Ortofoto-Vuota'))"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/pcn2012/16/34894/23807.jpg'); print(r.status, r.headers['Cache-Control'])"
docker compose exec -T api python -c "import urllib.request as u, json; d=json.load(u.urlopen('http://localhost:8000/api/comuni')); print([(c['nome'], c['provincia']) for c in d if c['istat'] in ('001168', '063049')])"
docker compose --profile edifici run --rm --entrypoint python edifici-lidar -c "import edifici3d.tetti as T; print(T.CORTILE_MIN_M2, T.motivo_tetto_piano([[0,0],[20,0],[20,10],[0,10]], 10, buchi=[[[6,4],[9,4],[9,7],[6,7]]]))"
```
Cosa aspettarsi: `1`; sette righe del `.env` con i valori nuovi (`ORTOFOTO_ORA=12000` … `ORTOFOTO_ATTESA_S=8`); le build
finiscono con `Built`; api `Up … (healthy)`, worker `Up`; `12000 12000 60000 300 3000 6000 8.0`; la tessera di Brisighella
due volte, la seconda `200 si` (dalla copia: non consuma il limite); la tessera di Bologna `200 1` (la RER non ha
immagini lì: la pagina passerà a un'altra fonte); `200 private, max-age=86400` (AGEA 2012: copia solo nel browser);
`[('None', 'TO'), ('Napoli', 'NA')]`; `25.0 None` (cavedio: non è più un cortile).

Cosa fare se va male: api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe; numeri
diversi nella riga di config → controlla le sette righe del `.env` (devono essere senza spazi) e ricrea l'api; per
tornare indietro: `rm -rf ~/energia && mv ~/energia_prima_20261109 ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker`.

### N6. [Server] Archivi di Roma e Bari: impronte, cartelle vecchie da parte, estrazione
(Già fatto con M1–M10? Salta N6 e N7.)
```bash
cd ~/archivi_bari_roma && sha256sum -c SHA256SUMS_bari_roma_2026-11-09.txt; cd ~/energia/fase4-server
cp /srv/energia/dati/edifici/archivi.json ~/archivi_prima_bari_roma_20261109.json
mv /srv/energia/dati/edifici/cc-by/laz/roma ~/roma_parziale_20261108 && mv /srv/energia/dati/edifici/iodl/pug/bari ~/bari_parziale_20261108
for f in ~/archivi_bari_roma/*_2026-11-09.tar.gz; do tar -xzf "$f" -C /srv/energia/dati/edifici || echo "ERRORE $f"; done
du -sh /srv/energia/dati/edifici/cc-by/laz/roma /srv/energia/dati/edifici/iodl/pug/bari
```
Cosa aspettarsi: due righe che finiscono con `: OK`; nessun errore dal `mv`; nessuna riga «ERRORE»; Roma circa 390 MB,
Bari circa 80 MB.

Cosa fare se va male: `FAILED` → fermati, ricopia quel file con N4 e ripeti (le cartelle vecchie sono ancora al loro
posto); `No such file or directory` dal `mv` → `ls /srv/energia/dati/edifici/*/*/` e mandami l'uscita; una riga «ERRORE» o
disco pieno → torna indietro: `rm -rf /srv/energia/dati/edifici/cc-by/laz/roma /srv/energia/dati/edifici/iodl/pug/bari && mv ~/roma_parziale_20261108 /srv/energia/dati/edifici/cc-by/laz/roma && mv ~/bari_parziale_20261108 /srv/energia/dati/edifici/iodl/pug/bari`
e mandami l'errore.

### N7. [Server] `controlla-archivio` di Roma e Bari
```bash
docker compose --profile edifici run --rm edifici-lidar controlla-archivio /dati/edifici/cc-by/laz/roma/prodotti | grep -E '"(nome|corpi|mediana|max)"|problemi|avvisi' -A1 | head -20
docker compose --profile edifici run --rm edifici-lidar controlla-archivio /dati/edifici/iodl/pug/bari/prodotti | grep -E '"(nome|corpi|mediana|max)"|problemi|avvisi' -A1 | head -20
```
Cosa aspettarsi: Roma `"nome": "DB topografico Regione Lazio 2014 – Roma"`, `"corpi": 384621`, mediana 6,5 m,
`"problemi": []`, `"avvisi": []` (37 corpi oltre 60 m, sotto la soglia dello 0,1 %: torri dell'EUR e Vittoriano); Bari
`"nome": "Bari – CTR 2006 Regione Puglia"`, `"corpi": 73205`, mediana 6,6 m, massimo 65,16 m, `"problemi": []`, `"avvisi": []`.

Cosa fare se va male: `"problemi"` non vuoto → mandami l'uscita intera del comando di quella città; per tornare indietro
le righe di N6 «Cosa fare se va male».

### N7 bis. [Server] Archivi DBTR del 09/11: impronte, cartelle vecchie da parte, estrazione, controlli
Bologna, Ravenna e Misano si sostituiscono: le cartelle vecchie vanno da parte (non si cancellano finché N10 non è a posto).
```bash
cd ~/archivi_er_0911 && sha256sum -c SHA256SUMS_er_2026-11-09.txt | grep -vc ': OK$'; cd ~/energia/fase4-server
cp /srv/energia/dati/edifici/archivi.json ~/archivi_prima_er_20261109.json
E=/srv/energia/dati/edifici/cc-by/er; mv $E/bologna ~/bologna_20261108 && mv $E/ravenna ~/ravenna_citta_20261108 && mv $E/misano-adriatico ~/misano_20261108
for f in ~/archivi_er_0911/edifici_dbtr_*_2026-11-09.tar.gz; do tar -xzf "$f" -C /srv/energia/dati/edifici || echo "ERRORE $f"; done
ls -d $E/*/prodotti | wc -l; du -sh $E/bologna $E/ravenna $E/misano-adriatico
for c in $(ls ~/archivi_er_0911 | sed -n 's/^edifici_dbtr_\(.*\)_2026-11-09.tar.gz$/\1/p'); do printf '%s ' $c; docker compose --profile edifici run --rm -T edifici-lidar controlla-archivio /dati/edifici/cc-by/er/$c/prodotti 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['corpi'], d['gronda_m']['max'], d['problemi'], d['avvisi'])"; done
```
Cosa aspettarsi: `0` (nessuna riga diversa da `OK`); nessun errore dal `mv`; nessuna riga «ERRORE»; `54` (archivi DBTR
dell'Emilia-Romagna: 28 di prima + 26 nuovi; qualcuno in più solo se nel frattempo hai approvato proposte di «Aggiungi DBTR»); Bologna circa 79 MB, Ravenna circa 52 MB, Misano circa 18 MB; poi 29 righe
`<comune> <corpi> <gronda massima> [] []`, per esempio `bologna 61813 103.7 [] []`, `ravenna 42574 55.0 [] []`,
`misano-adriatico 14347 30.0 [] []`, `castel-bolognese 2815 24.0 [] []`, `gatteo 119 9.0 [] []` (circa 5 minuti).

Cosa fare se va male: un numero diverso da `0` nella prima riga → `sha256sum -c SHA256SUMS_er_2026-11-09.txt | grep -v OK`,
ricopia quei file con N4 bis e ripeti (le cartelle vecchie sono ancora al loro posto); `No such file or directory` dal `mv`
→ `ls /srv/energia/dati/edifici/cc-by/er/` e mandami l'uscita; una riga «ERRORE», disco pieno o una riga con `[...]` non
vuoto → torna indietro: `for c in $(ls ~/archivi_er_0911 | sed -n 's/^edifici_dbtr_\(.*\)_2026-11-09.tar.gz$/\1/p'); do rm -rf $E/$c; done; mv ~/bologna_20261108 $E/bologna && mv ~/ravenna_citta_20261108 $E/ravenna && mv ~/misano_20261108 $E/misano-adriatico`
e mandami l'uscita.

### N8. [Server] `archivi.json`, sito e pulizia
```bash
docker compose --profile edifici run --rm edifici-lidar archivi-json --archivio /dati/edifici
docker compose exec -T api python -c "import urllib.request as u, json; d=json.load(u.urlopen('http://caddy/edifici3d/archivi.json'))['archivi']; print(len(d)); [print(a['base'], a.get('istat'), a.get('parziale'), a['nome']) for a in d if '/laz/' in a['base'] or '/pug/' in a['base'] or a['base'].split('/')[4] in ('bologna', 'ravenna', 'misano-adriatico', 'castel-bolognese', 'pianoro')]"
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261109a /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/interno/edifici.html
grep -c "Servizio sperimentale non ancora verificato" /srv/energia/sito/index.html /srv/energia/sito/dati.html /srv/energia/sito/legge10.html
grep -c "NaN" /srv/energia/sito/dati/mappa/01.json /srv/energia/sito/dati/mappa/15.json
grep -c "comune intero dal 09/11/2026" /srv/energia/sito/EUGENIO_PER_AGENTI.md
```
Cosa aspettarsi: `69` (28 + 26 archivi DBTR dell'Emilia-Romagna, 15 città); sette righe:
`/edifici3d/cc-by/er/bologna/prodotti/ 037006 None DBTR Emilia-Romagna – Bologna`,
`/edifici3d/cc-by/er/castel-bolognese/prodotti/ 039006 None DBTR Emilia-Romagna – Castel Bolognese`,
`/edifici3d/cc-by/er/misano-adriatico/prodotti/ None None DBTR Emilia-Romagna – Misano Adriatico, Morciano e Coriano (centro e frazioni principali)`,
`/edifici3d/cc-by/er/pianoro/prodotti/ None None DBTR Emilia-Romagna – Pianoro (zona verso Bologna)`,
`/edifici3d/cc-by/er/ravenna/prodotti/ None None DBTR Emilia-Romagna – Ravenna (città e parte del forese)`,
`/edifici3d/cc-by/laz/roma/prodotti/ 058091 None DB topografico Regione Lazio 2014 – Roma`
e `/edifici3d/iodl/pug/bari/prodotti/ 072006 None Bari – CTR 2006 Regione Puglia` (l'ordine può cambiare); tre righe con N > 0; `0`, `0`, `0`;
`0` e `0`; `1` (Roma e Bari stanno sulla stessa riga). Se tutto è a posto, pulizia:
```bash
rm -rf ~/archivi_bari_roma ~/roma_parziale_20261108 ~/bari_parziale_20261108 ~/archivi_er_0911 ~/codice.tar.gz ~/sito.tar.gz
exit
```

Le cartelle vecchie di Bologna, Ravenna e Misano (`~/bologna_20261108`, `~/ravenna_citta_20261108`, `~/misano_20261108`)
si cancellano **dopo N10** (riga in fondo a N10). Cosa fare se va male: un numero diverso da 69 →
`cp ~/archivi_prima_bari_roma_20261109.json /srv/energia/dati/edifici/archivi.json`, rimetti le cartelle vecchie (N6 e
N7 bis) e mandami l'uscita; `istat` `None` → l'archivio estratto è quello vecchio: rifai N6–N8;
`20261109a` a 0 → `sito.tar.gz` vecchio: rifai N3 e N4 (solo il sito) e la riga `tar`; `NaN` non a 0 → idem.

### N9. [Cloudflare] Regola di rate limiting e Purge Everything
1. Cloudflare → `statocritico.it` → **Security** → **WAF** → **Rate limiting rules** → la regola su `/api/` («API
   EuGEnio») → guarda l'espressione (senza modificarla se è già così):
   ```
   (starts_with(http.request.uri.path, "/api/") and not starts_with(http.request.uri.path, "/api/ortofoto/") and not starts_with(http.request.uri.path, "/api/terreno/"))
   ```
   Se mancano le due esclusioni: **Edit expression**, incolla la riga sopra, **Save** (60 richieste in 10 s per IP restano).
2. **Caching** → **Configuration** → **Purge Everything** → conferma (pagine, `archivi.json`, gli `indice.json` e le
   tessere `corpi.pmtiles` vecchie di Roma e Bari).

Cosa aspettarsi: espressione con le due esclusioni; «Purge request successful» (o simile). Un 429 di Cloudflare non ha
l'intestazione `X-EuGEnio-Limite` dei 429 del server: in N10 si distingue in F12 → Rete.

Cosa fare se va male: non trovi la regola o ha un'altra forma → mandami uno screenshot dell'espressione (senza toccarla);
il pannello non si apre → rete aziendale.

### N10. [Browser] Prove (Ctrl+F5; F12 → Console)
**A – limiti.** 1. **Modelli 3D**, «corso Cavour», «Roma»: muovi, ingrandisci e inclina la mappa per qualche minuto, poi
Genera il 3D e ruota: la Console **non** si riempie di «AJAXError (429)»; F12 → Rete, filtro `ortofoto`: risposte 200,
molte con `X-Ortofoto-Copia: si`. 2. Prova della nota: nella Console scrivi
`EUGENIO_LIMITI.ferma('ortofoto', 120)` e Invio: **sotto la mappa, prima di «Genera il 3D»**, la nota «Ortofoto: raggiunto
il limite orario di richieste per il tuo indirizzo. Mi fermo e riprovo da solo tra 2 minuti.»; spostando la mappa nessuna
nuova tessera di ortofoto in Rete; dopo 2 minuti la nota diventa «riprovo adesso…», l'ortofoto torna e **la nota sparisce
da sola**. Stessa prova in **Ortofoto** (nota sopra «Scarica l'immagine»).

**B.** **Previsioni** (pagina iniziale): niente avviso giallo «Servizio sperimentale»; menu invariato.

**C.** Modelli 3D e Ortofoto, anche con la finestra stretta (o il telefono): le frecce ← ↑ ↓ →, «1 m», la scritta
«Ortofoto spostata: …» (o «Ortofoto al suo posto») e «Azzera» **sulla stessa riga**.

**D.** Modelli 3D: nel blocco dell'indirizzo **prima Comune, poi Indirizzo**; scrivi in tutti i campi e premi **«Reset»**
dei due blocchi: si svuotano solo i campi di quel blocco. Scrivi solo «torino» nel Comune della particella e premi «Cerca
la particella»: «Ti porto al centro del comune di Torino…», la mappa su Torino. Stessa cosa con «Napoli».

**E.** Modelli 3D, «Livelli della mappa»: «Colore degli edifici» con il pulsante a pillola; scegli **Rosso**: sagome 2D e
volumi 3D rossi, edificio scelto arancio, edifici OSM marroni, pallino della legenda rosso; ricarica la pagina: resta
rosso. Casella **«Alberi»** spenta in partenza; accesa, nella vista 3D (dove ci sono gli alberi del LiDAR) chiome verdi
arrotondate; PNG: «edifici vicini del DB topografico in rosso» e, con gli alberi, «alberi in verde (chiome dal LiDAR…)».

**F.** **Bagno di Romagna**, foglio 54 particella 216 → Genera il 3D: tetto a capanna; nota «Tetti: … 2 ipotizzati (22°
pianura / 32° montagna: 2 a 22°), 0 piani»; nella tabella dei corpi «tetto ipotizzato a 22° (pianura: quota del terreno 511 m)».

**G.** «via San Salvatore», «Susegana»: ortofoto (AGEA 2012 del Geoportale) visibile, sagome del Veneto; Genera il 3D:
terreno in rilievo (DTM del Veneto se J5 bis è stato fatto, altrimenti Copernicus), legenda «Terreno: …».

**H.** «via dell'Indipendenza 1», «Bologna»: sotto la ricerca il messaggio «Ortofoto RER 2023-24 (20 cm)» non ha immagini in questa
zona: uso «Geoportale Nazionale – ortofoto AGEA 2012 (50 cm, solo consultazione)», e la foto si vede subito. Le Due Torri **non** ci sono come volumi alti (vedi
sopra: nel DBTR non hanno altezza); a Cesena e Ravenna resta la RER.

**I.** Una prova per città, zoom 17: **Venezia** «piazza San Marco», **Roma** «piazza Venezia», **Bari** «corso Cavour 12»,
**Napoli** «via Antonio Cardarelli 9», **Palermo** «piazza Verdi», **Trento** «piazza Duomo»: ortofoto visibile (Trento: PAT
2015), Genera il 3D con il terreno (non nero); accendi «Confini delle particelle catastali» e «Contorni degli edifici»:
linee gialle e contorni visibili. **Genova**, «via Nervi» (fuori dalle 4 tavole): edifici OSM in marrone.

**J.** Modelli 3D su Roma a zoom 12–14: clic in punti diversi della mappa, anche lontano dagli edifici: la vista **non si
sposta mai**; il comune si evidenzia e il messaggio dice «Comune di Roma (RM): avvicinati con la rotella…».

**Roma e Bari intere.** 1. «piazza Anco Marzio», «Roma» (**Ostia**) → Genera il 3D: edifici del DB topografico (non
marroni), senza «Qui non c'è ancora il DBTR»; legenda «Regione Lazio – DBGT 2014 … (CC BY 4.0)». 2. «quadrato della
Concordia», «Roma» (**EUR**): Palazzo della Civiltà Italiana (gronda fino a circa 60 m); «viale Giorgio Ribotta», «Roma»:
Torre Europarco, gronda 111,3 m. 3. «largo Agostino Gemelli 8» e «viale del Policlinico 155», «Roma». 4. «via
dell'Aeroporto di Fiumicino», «Fiumicino»: **non** coperto dall'archivio di Roma (edifici OSM marroni: giusto). 5. «piazza
Capitaneo», «Bari» (**Palese**) e «via Principe di Piemonte», «Bari» (**Torre a Mare**): edifici della CTR, legenda «Regione
Puglia – Carta Tecnica Regionale 1:5.000, volo 2006 (IODL 2.0)». 6. «piazza Giulio Cesare 11» e «largo Abate Elia», «Bari»:
come prima.

**Archivi DBTR del 09/11.** Modelli 3D, per ognuno «Genera il 3D»: edifici del DB topografico (grigi, non marroni), senza
«Qui non c'è ancora il DBTR», legenda «Regione Emilia-Romagna – DBTR, CC BY 4.0». 1. «via del Triumvirato», «Bologna»
(aeroporto e Birra, fogli del nord arrivati il 09/11). 2. «viale delle Nazioni», «Ravenna» (**Marina di Ravenna**: prima
edifici OSM marroni). 3. «piazza Bernardi», «Castel Bolognese». 4. «piazza Malatesta», «Verucchio». 5. «via Porrettana»,
«Casalecchio di Reno». 6. «piazza Matteotti», «Massa Lombarda». 7. Coriano: cerca «Coriano», poi sposta il punto a
**Cerasolo** (circa 2,5 km a ovest del capoluogo): edifici del DBTR anche lì. 8. «piazza Maggiore», «Bologna»: come prima.

Se tutto è a posto, le cartelle vecchie si cancellano:
```powershell
ssh eugenio "rm -rf ~/bologna_20261108 ~/ravenna_citta_20261108 ~/misano_20261108"
```

Cosa fare se va male: pagina vecchia → N9 di nuovo e Ctrl+F5; ancora 429 in Console → F12 → Rete, clic su una tessera
rossa → Intestazioni: mandami `Retry-After` e `X-EuGEnio-Limite` (assente = 429 di Cloudflare: torna a N9, punto 1);
«Qui non c'è ancora il DBTR» a Ostia, Palese, Marina di Ravenna o Castel Bolognese → filtro `archivi.json`, mandami la
risposta (deve avere 69 voci); 3D nero o errori in Console →
screenshot e righe della Console.

### N11. [PC] Commit e push
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_dbtr|estraz_procons|\.gpkg$|DTM5x5|archivi_edifici|archivi_citta|archivi_bari_roma|archivi_er_0911|\.tar\.gz$|giornaliero.*\.parquet"
```
```powershell
git commit -m "09/11/2026: correzioni dalle prove J10 - limiti solo sulle tessere dalla fonte, copia con tetto anti-abuso, 429 con Retry-After, pausa della fonte e nota sotto la mappa; Previsioni non sperimentale; frecce dell'ortofoto su una riga; ricerca con Comune prima dell'Indirizzo e Reset, confini di Piemonte e Campania senza NaN (Torino); colore degli edifici e alberi in Modelli 3D; cavedi non piu cortili (Bagno di Romagna); fonti vuote della RER saltate da sole (Bologna); clic sulla mappa che non sposta la vista; Roma e Bari per il comune intero (b_regioni dbgt-fogli); archivi DBTR del 09/11 - Bologna intera, Ravenna con parte del forese, Castel Bolognese, Misano con Coriano, 17 comuni della Romagna e 8 vicini a Bologna (69 archivi), comando dividi per le estrazioni raggruppate, pagina fino a 150 archivi; sito ?v=20261109a; procedura AGGIORNAMENTO_2026-11-09"
```
```powershell
git push
```
Cosa aspettarsi: il terzo comando **non stampa nulla**; il push finisce con `… main -> main`.

Cosa fare se va male: righe dal terzo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`.

### N12. [PC] Release `v2026.11.09`
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.09 --target main --title "EuGEnio 9 novembre 2026 – Roma, Bari e Bologna intere, colori degli edifici e ricerca più comoda" --notes-file ..\note_release.md
```
Cosa aspettarsi: l'indirizzo `https://github.com/StatoCritico/eugenio/releases/tag/v2026.11.09`.

Cosa fare se va male: `gh` chiede il login → `gh auth status` e mandami l'uscita (senza token); senza `gh`: GitHub →
Releases → Draft a new release, tag `v2026.11.09`, titolo come sopra, testo di `..\note_release.md`.
