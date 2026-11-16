# Aggiornamento del 16/11/2026 (g) – Perugia in Modelli 3D con le altezze del LiDAR PST

Settima pubblicazione del 16/11, e la prima con il **metodo nuovo** (pull request di Claude, Merge di Paolo, release; decisione del 12/11, strada «1»). Va **sopra la `v2026.11.16f`**. Release **`v2026.11.16g`**, versione del
sito **`?v=20261116g`**, voce nelle Novità.

Con Perugia ci sono **tutti i capoluoghi di regione** in Modelli 3D.

## Cosa cambia per gli utenti

**Patrimonio › Modelli 3D** e le altre pagine 3D: a Perugia gli edifici del centro storico, di Fontivegge e di Sant'Andrea
delle Fratte hanno le **altezze misurate** dal rilievo laser del MASE (LiDAR PST 2014, DSM First − DTM 1 m). Prima c'era
solo il ripiego OpenStreetMap, con le altezze stimate a 9 m. Il terreno della vista 3D viene dallo stesso rilievo, a 1 m.

Limiti, scritti anche nell'attribuzione e per corpo:
- il rilievo è del **2014** ed è segnato «collaudato NO» nel quadro di unione del MASE;
- gli edifici costruiti dopo il 2014 hanno l'altezza di OpenStreetMap (`height` o `building:levels`), o quella stimata dai
  vicini o dall'uso;
- **manca il polo ospedaliero S. Maria della Misericordia**, a sud di 43,080 N: serve la tavola D43071235, non scaricata
  perché l'app del MASE si è bloccata. Il CREO è dentro. Fuori dalla zona coperta resta il ripiego OSM al volo.

## L'archivio

| Voce | Valore |
|---|---|
| Cartella | `odbl/umb/perugia/prodotti` (ODbL: le sagome sono OSM, mai nello stesso archivio dei CC BY) |
| Nome | «Perugia – OpenStreetMap con altezze LiDAR PST 2014 (centro, Fontivegge, S. Andrea delle Fratte)» |
| Attribuzione | «© OpenStreetMap contributors (ODbL 1.0); altezze da DSM − DTM 1 m: Ministero dell'Ambiente e della Sicurezza Energetica – Geoportale Nazionale, Banca dati PST (CC BY 4.0)» |
| Corpi | 5.834 (5.833 edifici), 38 celle, 6,7 MB (tar.gz 2,1 MB) |
| Gronda | min 1,91 m, mediana 11,05 m, max 52,38 m |
| Prove | Palazzo dei Priori 29,06 m, Cattedrale 28,61 m, Fontivegge 16,79 m |
| `controlla-archivio` | `problemi: []`, `avvisi: []` |
| Terreno | `dtm1_pst_perugia.tif` (COG 1 m, 49 MB) + `dtm1_pst_perugia.json`; 473,9 m in centro, 302,6 m a Fontivegge |

Dettagli dello scaricamento e dei controlli: `documenti/PERUGIA_PST_2026-11-16.md`.

## Cosa cambia nei file

- **Nuovi**: `fase10-edifici3d/edifici3d/adattatori/umbria.py` (adattatore `umbria_osm_pst` e comando `osm-geojson`),
  `fase10-edifici3d/fonti/umbria_perugia.toml` (zona `umb`, EPSG:7792), `fase10-edifici3d/tests/test_umbria.py`,
  `documenti/PERUGIA_PST_2026-11-16.md`.
- `fase10-edifici3d/edifici3d/__main__.py`: «ODbL 1.0» tra le licenze accettate da `controlla-archivio`; `dtm-server
  --regione pst_umbria`.
- `fase10-edifici3d/edifici3d/dtm_locale.py`: scheda `pst_umbria` (licenza, attribuzione, nome in legenda).
- `fase10-edifici3d/fonti/regioni.toml`: PST nazionale «attiva» (prova del 16/11, usata in `odbl/umb/perugia`); PNRR
  ancora non pubblicato.
- `fase10-edifici3d/tests/test_regionali.py`, `fase10-edifici3d/README.md`, `documenti/CITTA_RIFERIMENTO_CENTRO.md`.
- `fase5-sito/novita.toml` (voce nuova), versione `?v=20261116g` in tutte le pagine (`costruisci_pagine.py --versione`),
  `EUGENIO_PER_AGENTI.md` (le due copie) e `fase5-sito/sito/llms.txt`.

L'api non cambia: la rotta `/api/terreno` legge da sola le schede `.json` della cartella del terreno (ogni 5 minuti).
Cambia invece il codice dell'immagine `energia-edifici` (`controlla-archivio` deve accettare l'ODbL): va ricostruita (AG3).

## Test (16/11/2026, container, sopra il commit `0773192` della 16e; ripetuti alle 18:25 sul ramo della pull request, sopra la `v2026.11.16f`: `test_umbria.py` e `test_regionali.py` 19 passati, `test_agenti.py` e `test_terreno.py` 15 passati, `test_costruisci_pagine.py` 36 passati e 1 saltato, `costruisci_pagine.py --controlla` 0 file da rigenerare)

- `fase10-edifici3d`: 164 passati, 1 fallito. Il fallito è `test_puglia_ctr_divide_gli_isolati`, che fallisce anche senza
  la patch: nel repository pubblico manca `tests/dati/puglia_ctr_438074_campione.zip`.
- `test_umbria.py` e `test_regionali.py`: 19 passati. `python -m edifici3d regioni`: nessun errore.
- `fase4-server/tests/test_terreno.py`: 10 passati; con `CARTELLA_TERRENO` sul COG nuovo le quote sono quelle della tabella.
- `fase4-server/tests/test_agenti.py`: 5 passati (le due copie di `EUGENIO_PER_AGENTI.md` sono identiche).
- `fase5-sito`: 54 passati, 1 saltato; `costruisci_pagine.py --controlla`: 0 file da rigenerare.
- Pagina `modelli3d.html` in Chrome senza schermo, con l'archivio servito in locale: il 3D del Palazzo dei Priori si genera
  dall'archivio (cortile compreso), nessun errore JavaScript.

## Procedura AG1–AG6

I file di Perugia sono già sul PC, in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\perugia\`: li ha
copiati Claude dai Download e ha controllato le impronte (16/11, 18:25):
- `edifici_umb_perugia_2026-11-16.tar.gz`, `dtm1_pst_perugia.tif`, `dtm1_pst_perugia.json`,
  `SHA256SUMS_perugia_2026-11-16.txt`;
- `pst_perugia_DTM1x1_2014.zip` e `pst_perugia_DSMFirst1x1_2014.zip` (le tavole originali: restano sul PC come archivio,
  sul server non servono).

Il codice è nella **pull request** `claude/2026-11-16g-perugia` su GitHub: niente patch né script PowerShell.

### AG1. [Browser] Merge della pull request, poi release
1. Apri la pull request (il collegamento te lo manda Claude; l'elenco è su https://github.com/StatoCritico/eugenio/pulls).
2. Scheda **Files changed** per guardare le modifiche, poi **Merge pull request** → **Confirm merge**.
3. Scrivi a Claude «merge fatto»: crea lui la release `v2026.11.16g` con le note della voce delle Novità.

Cosa aspettarsi: la pull request risulta «Merged»; poi la release compare su https://github.com/StatoCritico/eugenio/releases.

Attenzione: con la release pubblicata, alle 4:40 l'aggiornamento notturno installa il codice, ma **non** archivio,
terreno e immagine `edifici-lidar` (AG2–AG4). Se non fai AG2–AG4 stasera, va bene lo stesso: Perugia resta col ripiego
OSM finché non li fai.

### AG2. [PC] Copia dei file sul server
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\perugia
ssh eugenio "mkdir -p ~/perugia_1611"
scp edifici_umb_perugia_2026-11-16.tar.gz dtm1_pst_perugia.tif dtm1_pst_perugia.json SHA256SUMS_perugia_2026-11-16.txt eugenio:~/perugia_1611/
```
Cosa aspettarsi: quattro righe `100%` (il COG è di 49 MB).

### AG3. [Server] Aggiornamento da GitHub e immagine degli edifici
```bash
ssh eugenio
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
```bash
cd ~/energia/fase4-server
docker compose --profile edifici build edifici-lidar
docker compose --profile edifici up -d --force-recreate edifici-coda
docker compose --profile edifici run --rm --entrypoint python edifici-lidar -c "from edifici3d.__main__ import TESTI_LICENZA; from edifici3d.dtm_locale import SCHEDE_DTM; print('ODbL 1.0' in TESTI_LICENZA, 'pst_umbria' in SCHEDE_DTM)"
```
Cosa aspettarsi:
- `Aggiornamento da … a v2026.11.16g`, `api e worker aggiornati e funzionanti`, `Release v2026.11.16g installata`;
- la build di `edifici-lidar` finisce senza errori (qualche minuto);
- l'ultima riga stampa `True True`.

Se l'aggiornamento notturno delle 4:40 ha già installato la `v2026.11.16g`, lo script dice che è già installata: va bene, fai lo stesso le tre righe di `edifici-lidar`.

### AG4. [Server] Archivio, terreno, `archivi.json`
Ancora in `~/energia/fase4-server`.
```bash
cd ~/perugia_1611 && sha256sum -c SHA256SUMS_perugia_2026-11-16.txt --ignore-missing; cd ~/energia/fase4-server
cp /srv/energia/dati/edifici/archivi.json ~/archivi_prima_20261116g.json
tar -xzf ~/perugia_1611/edifici_umb_perugia_2026-11-16.tar.gz -C /srv/energia/dati/edifici && ls /srv/energia/dati/edifici/odbl/umb/perugia/prodotti
docker compose --profile edifici run --rm -T edifici-lidar controlla-archivio /dati/edifici/odbl/umb/perugia/prodotti | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['corpi'], d['gronda_m'], d['problemi'], d['avvisi'])"
docker compose --profile edifici run --rm edifici-lidar archivi-json --archivio /dati/edifici > /dev/null
python3 -c "import json; d=json.load(open('/srv/energia/dati/edifici/archivi.json'))['archivi']; print(len(d)); [print(a['base'], a['licenza']) for a in d if '/umb/' in a['base']]"
cp ~/perugia_1611/dtm1_pst_perugia.tif ~/perugia_1611/dtm1_pst_perugia.json /srv/energia/dati/terreno/ && ls /srv/energia/dati/terreno/*.json
```
Cosa aspettarsi:
- tre righe `OK` (le due righe dei file ZIP del PST non ci sono: `--ignore-missing` le salta);
- `contesto  corpi.pmtiles  indice.json` (più `LICENZE.txt` una cartella sopra);
- `5834 {… 'mediana': 11.1, … 'max': 52.38, … 'oltre_60m': 0} [] []`;
- **`70`** (le 69 di prima più Perugia) e la riga `/edifici3d/odbl/umb/perugia/prodotti/ ODbL 1.0`;
- l'elenco delle schede del terreno con `dtm1_pst_perugia.json` accanto a quelle di prima.

Poi, dopo 5 minuti (l'api rilegge le schede del terreno ogni 5 minuti):
```bash
docker compose exec -T api python -c "import urllib.request as u, json; print([d['file'] for d in json.load(u.urlopen('http://localhost:8000/api/terreno/fonti'))['dtm']])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/terreno/15/17511/12026.png'); print(r.status, r.headers['X-Terreno-Fonte'], r.headers['X-Terreno-Nome'])"
docker compose exec -T api python -c "import urllib.request as u, json; d=json.load(u.urlopen('http://caddy/edifici3d/archivi.json'))['archivi']; print(len(d), [a['nome'] for a in d if '/umb/' in a['base']])"
```
Cosa aspettarsi: `dtm1_pst_perugia.tif` nell'elenco; `200 dtm DTM 1 m LiDAR PST del MASE (CC BY 4.0)`; `70` e il nome
dell'archivio di Perugia.

Cosa fare se va male:
- una riga `FAILED` in `sha256sum` → rifai AG2 per quel file;
- `controlla-archivio` rifiuta la licenza → l'immagine non è stata ricostruita: rifai AG3 (seconda parte);
- un numero diverso da `70` → mandami l'elenco: `python3 -c "import json; [print(a['base']) for a in json.load(open('/srv/energia/dati/edifici/archivi.json'))['archivi']]"`;
- `copernicus` invece di `dtm` nella tessera → la tessera era già in copia: aspetta 5 minuti e riprova (la copia cambia
  versione con il DTM nuovo).

Per tornare indietro: `rm -r /srv/energia/dati/edifici/odbl/umb/perugia /srv/energia/dati/terreno/dtm1_pst_perugia.*` e
`cp ~/archivi_prima_20261116g.json /srv/energia/dati/edifici/archivi.json`.

A prove finite: `rm -r ~/perugia_1611`.

### AG5. [Cloudflare] Purge Everything
`aggiorna_da_github.sh` ha già fatto il Purge in AG3, ma `archivi.json` è cambiato dopo. Rifallo:
https://dash.cloudflare.com → zona `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma.

Cosa aspettarsi: «Purge request successful» (o simile).

### AG6. [Browser] Prove
1. Apri https://eugenio.statocritico.it/novita.html: in cima la voce del 16/11 «Perugia in Modelli 3D, con le altezze dal
   rilievo laser».
2. Apri https://eugenio.statocritico.it/modelli3d.html, Comune «Perugia», Indirizzo «piazza IV Novembre», «Cerca
   l'indirizzo». Fai clic sul **Palazzo dei Priori** e premi «Genera il 3D». Cosa aspettarsi: corpi in grigio (non marroni
   come il ripiego OSM), gronda circa 29 m nella tabella dei corpi, fonte «DSM − DTM (…DSMFirst.tiff…)»; sotto la mappa
   l'attribuzione «© OpenStreetMap contributors (ODbL 1.0); altezze da DSM − DTM 1 m: Ministero dell'Ambiente…»; terreno
   in rilievo con «DTM 1 m LiDAR PST del MASE (CC BY 4.0)» in legenda.
3. Ripeti con la **Cattedrale di San Lorenzo** (circa 28,6 m) e con la **stazione di Fontivegge** (Indirizzo «piazza Vittorio
   Veneto»: circa 16,8 m).
4. Indirizzo «via Sant'Andrea delle Fratte»: vicino all'ospedale. Il CREO ha le altezze del LiDAR; il corpo principale
   dell'ospedale, più a sud, resta col ripiego OSM (marrone). È il limite noto.
5. Apri https://eugenio.statocritico.it/edifici3d/archivi.json: 70 archivi, l'ultimo è Perugia (ODbL).

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, stato: `?v=20261116g`, release `v2026.11.16g`; **70 archivi** di edifici; Perugia (ODbL, sagome OSM, altezze
  LiDAR PST 2014) chiude i capoluoghi di regione. Fonte nazionale PST «attiva».
- DA_FARE:
  - [ ] **Paolo**: AG1 (Merge), poi AG2–AG6; **Claude**: release `v2026.11.16g` dopo il Merge;
  - [ ] tavola **D43071235** (DTM + DSM First) per il polo ospedaliero di Perugia, quando l'app MASE torna utilizzabile; poi
    OSM sul riquadro allargato, `annota`, `prepara-regione` e ripubblicazione dell'archivio;
  - [ ] Perugia, resto del comune (511 tavole DTM 1×1, 26 richieste da 20): solo se serve;
  - [ ] confronto PST 2014 («collaudato NO») con il LiDAR PNRR quando sarà pubblicato;
  - [ ] `test_puglia_ctr_divide_gli_isolati`: aggiungere il campione `tests/dati/puglia_ctr_438074_campione.zip` al
    repository o far saltare il test quando manca.
