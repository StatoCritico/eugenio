# Aggiornamento del 04/11/2026

> **Per pubblicare segui `PUBBLICAZIONE_2026-11-04.md`**: procedura unica, nell'ordine giusto, per tutto il 03/11 e il
> 04/11 (commit e push, GitHub Actions, Cloudflare, server, prove nel browser, .exe). I passi qui sotto restano come
> descrizione di cosa è cambiato; dove differiscono, vale `PUBBLICAZIONE_2026-11-04.md` (incoerenze elencate in fondo a
> quel file).

> **Nota del 04/11/2026 notte**: con la sezione «Importa DXF/IFC» (in fondo) il sito è passato alla versione
> **`?v=20261104b`**, che comprende tutto quello delle sezioni qui sotto. Dove una sezione scrive `20261104a`, leggi
> `20261104b` (i controlli A1 e B2 della Fase B sono già aggiornati).

> **Nota del 04/11/2026 notte, dopo**: con la sezione «Menu fissabile e voci GME non cliccabili» (qui sotto) il sito passa
> a **`?v=20261104c`**, che sostituisce `?v=20261104b` per tutte le sezioni di questo file.

## Menu fissabile e voci GME non cliccabili (`?v=20261104c`)

Richiesta di Paolo: «passando il mouse sopra una voce del menu principale si apre in verticale, cliccando si fissa con le
voci in orizzontale in una riga con sfondo nero sotto la barra dei menu; cliccando di nuovo sulla voce principale la barra
sparisce e ritorna il menu verticale a scomparsa; un tooltip avvisa "clicca qui per …" secondo le varie fasi; solo per le
voci del menu principale, le altre restano come prima. Le voci in attesa del GME non sono cliccabili (tooltip "In attesa
di autorizzazione dal GME")».

Cosa fa ora il menu (solo i cinque gruppi Clima e meteo, Patrimonio, Edificio, Cogenerazione, Fotovoltaico):
- **mouse sopra** (o Tab sul titolo): la tendina verticale si apre; esce il mouse: si chiude (dopo 180 ms); Esc la chiude;
- **clic sul titolo** (o Invio, Spazio): il gruppo si fissa; sotto la barra compare una riga nera a tutta larghezza con le
  voci affiancate, la voce della pagina aperta sottolineata nell'accento del vestito, le etichette «sperimentale», «in
  sviluppo» e «licenza GME» in piccolo; il titolo diventa una linguetta nera e la sua tendina non si apre più;
- **clic su un altro gruppo**: la riga passa a quello; **secondo clic sullo stesso titolo**: la riga sparisce e torna la
  tendina;
- suggerimento sul titolo, che cambia con lo stato: «Clicca qui per fissare il menu Patrimonio sotto la barra» / «Clicca
  qui per richiudere la barra di Patrimonio e tornare al menu a tendina» (anche per i lettori di schermo; `aria-pressed`);
- la scelta resta al cambio di pagina (memoria del browser); la riga ha già il suo posto prima che si carichino gli
  script, quindi la pagina non salta;
- sul computer le voci che non stanno in una riga vanno a capo (Edificio a 1366 px: due righe); sul **telefono** (sotto
  861 px) la riga fissata resta, scorre in orizzontale dentro di sé, parte dalla voce della pagina aperta e ha il pulsante
  × per chiuderla; il menu del telefono è come prima;
- nera in tutti e cinque i vestiti, in tema scuro e chiaro.

Voci «licenza GME» (Spark spread, Cogeneratore sull'edificio, Confronto tra alternative, Rischio prezzo, Budget CAR,
Prezzo catturato): non più collegamenti né nella tendina, né nella riga, né nel menu del telefono, né negli elenchi «Nello
stesso gruppo» delle pagine segnaposto `cog-*.html` e `fv-leed.html`; aspetto attenuato, suggerimento «In attesa di
autorizzazione dal GME» (con un tocco compare anche scritto, per il telefono). Le pagine restano sul sito ma nessun
collegamento interno porta lì (controllato da un test; resta solo il collegamento di ogni pagina a sé stessa nel suo
elenco «Nello stesso gruppo»).

File cambiati (solo `fase5-sito`): `parti/testata.html`, `parti/testa.html`, `costruisci_pagine.py`, `sito/aspetto.js`,
`sito/stile.css`, `sito/cog-*.html` e `sito/fv-leed.html` (elenchi), tutte le pagine `sito/*.html` e gli script con la
versione (rigenerati con `costruisci_pagine.py --versione 20261104c`), `sito/interno/edifici.html` (versione a mano),
`tests/test_costruisci_pagine.py`, `tests/test_menu_browser.py` (nuovo). Documenti: `sito/README_stile.md` § «Menu a
gruppi», `fase5-sito/README.md`, `RIEPILOGO.md`, `DA_FARE.md`, `PUBBLICAZIONE_2026-11-04.md`.

**Nessun rebuild** dell'api né riavvio di Caddy: sono solo file statici (Caddy legge `fase5-sito/sito` montato in sola
lettura). Prove: 19 test di fase 5 (5 nuovi, 2 in Chromium a 1366 e 375 px), fasi 10 e 11 invariate e tutte passano.
Per pubblicare: sezione «Aggiornamento menu (?v=20261104c)» in cima a `PUBBLICAZIONE_2026-11-04.md`.

## Previsioni: schede, «Solo clima», comune deselezionabile

Richiesta di Paolo: cambiando comune il file dei consumi va tolto; un'opzione per le sole previsioni del clima; in tutte
le pagine un secondo clic sul comune scelto lo toglie; il grafico diviso in schede (Consumo e una per ogni parametro
climatico attivo, ognuna col suo grafico, la freccina del riquadro e «Scarica la previsione»); report con tutti i
valori (CSV ed Excel/ODS in colonne affiancate, PDF con i grafici in sequenza: prima i consumi, poi i parametri
nell'ordine della pagina).

**Sito** (`fase5-sito/sito`, versione `?v=20261104a`):
- `app.js`: cambio o deselezione del comune → via file, risultati e risposte in arrivo, con messaggio; scelta «Cosa
  prevedere» (consumi / solo clima); risultato a schede; CSV con tutte le colonne e le righe del passato.
- `index.html`: scelta «Cosa prevedere», testi della mappa e del file; `stile.css`: `.schede-previsione`.
- `minimappa.js`: funzioni comuni `EUGENIO.alterna` e `EUGENIO.togliScelto`; `legge10.js` e `legge10.html`: secondo
  clic che toglie il comune (anche `?comune=` e i risultati); `dati.js`: un comune già scelto nella ricerca si toglie.

**Server** (`fase4-server`, serve il rebuild dell'api):
- nuova rotta `GET /api/clima-previsto/{istat}` (`modello.solo_clima`): variabili meteo osservate e previste senza file
  né TiRex-2; limite «dati».
- `/api/previsione` restituisce anche `clima` (variabili meteo usate, negli stessi passi).
- `report_servizi.report_previsione`: colonne affiancate, sezione «Grafici» nel PDF (SVG disegnati dal server),
  report «Previsione del clima» per il Solo clima. I dati GME/EEX non c'entrano: solo meteo Open-Meteo e consumi
  dell'utente.

**Prove**: fase 4 `python -m pytest tests` (con `PYTHONPATH` su fase3, fase7 e fase10) 135 test passano, 10 nuovi in
`tests/test_solo_clima.py`; fase 5 11 test passano; prova in Chromium headless (Playwright) con rotte simulate dal
codice vero della fase 4: schede, riquadro, CSV, PDF, Excel, Solo clima, cambio e deselezione del comune, Legge 10.

**Da fare**: provare col meteo vero sul server (soprattutto la climatologia del lungo termine).

## Fase B – ortofoto, facciate, orizzonte lontano, PVGIS, obblighi e priorità (edifici 3D, § 15)

Cosa si pubblica (insieme alle Previsioni qui sopra: stesso sito `?v=20261104a`, stesso rebuild dell'api):
- **sito**: pagina Patrimonio › **Ortofoto** (mappa, selettore delle fonti, licenza e citazione sotto la mappa); pagina 3D
  con i passi Obblighi di legge, Facciate al sole, Confronto con PVGIS, Classifica di priorità e lo sfondo con l'ortofoto;
  pagine nuove Fotovoltaico › Sole e irradiazione, › Confronto con PVGIS, › D.Lgs. 199/2021, Edificio › Obblighi di legge
  (prima segnaposto); file nuovi `ortofoto.js`; cambiati `edificio3d.js`, `edifici_calcoli.js`, `ombre_worker.js`,
  `stile.css`, `sitografia.html`, il menu;
- **server**: `servizio/ortofoto.py`, `servizio/orizzonte.py`, `servizio/pvgis.py` (nuovi), `app.py`, `config.py`,
  `protezione.py`, `report_servizi.py`; `Caddyfile`, `api/Dockerfile` (copia i TOML delle ortofoto), `.env.example`;
- **fase 10**: cartella `ortofoto/` con i TOML delle fonti e il comando `ortofoto-sito` (AGEA a mano).

Scelta da fare prima di pubblicare (decisione del § 6: la RER è «da confermare con la Regione»): la RER 2023-24 è CC BY 4.0
e il proxy la serve già con lo stato «uso da confermare» scritto in pagina. Se preferisci aspettare la risposta
dell'Archivio Cartografico, al passo B1 aggiungi anche `ORTOFOTO_SPENTE=rer2023` (la pagina offre allora Sentinel-2 e il
Geoportale Nazionale).
**Decisa il 04/11/2026** (RIEPILOGO): la RER si pubblica **accesa** con «uso da confermare»; al passo B1 non serve
`ORTOFOTO_SPENTE`.

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

### A. Sul PC (PowerShell)

**A1.** Estrai `eugenio_2026-11-04.zip` sopra la cartella del progetto (sovrascrivi), poi:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase5-sito
python costruisci_pagine.py --controlla
```
Deve comparire `versione 20261104b: 0 file da rigenerare` (fino al 04/11 notte era `20261104a`).

**A2.** Prepara il pacchetto del sito (sei in `fase5-sito`):
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
```

**A3.** Copia sul server, un comando alla volta (ognuno deve mostrare `100%`):
```powershell
scp ..\sito.tar.gz eugenio:~/
scp fase4-server\servizio\ortofoto.py fase4-server\servizio\orizzonte.py fase4-server\servizio\pvgis.py fase4-server\servizio\app.py fase4-server\servizio\config.py fase4-server\servizio\protezione.py fase4-server\servizio\report_servizi.py fase4-server\servizio\modello.py eugenio:~/energia/fase4-server/servizio/
scp fase4-server\Caddyfile fase4-server\.env.example eugenio:~/energia/fase4-server/
scp fase4-server\api\Dockerfile eugenio:~/energia/fase4-server/api/
scp -r fase10-edifici3d eugenio:~/energia/
```
(`modello.py` è delle Previsioni: se l'hai già copiato con la sezione di sopra, ricopiarlo non fa danni.)

### B. Sul server (`ssh eugenio`)

**B1.** Cartelle delle copie e riga facoltativa nel `.env`:
```bash
mkdir -p /srv/energia/dati/ortofoto /srv/energia/dati/orizzonte /srv/energia/dati/pvgis
grep -q ORTOFOTO_ ~/energia/fase4-server/.env || printf "ORTOFOTO_SPENTE=\nORTOFOTO_MAX_GB=15\n" >> ~/energia/fase4-server/.env
grep ORTOFOTO_ ~/energia/fase4-server/.env
```
Devono comparire le due righe `ORTOFOTO_…`. (Per spegnere la RER: `nano ~/energia/fase4-server/.env` e scrivi
`ORTOFOTO_SPENTE=rer2023`.)

**B2.** Sito, api e caddy:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261104b /srv/energia/sito/ortofoto.html
cd ~/energia/fase4-server && docker compose up -d --build api && docker compose up -d --force-recreate caddy
```
La prima riga stampa un numero maggiore di 0; la ricostruzione dell'api dura qualche minuto.

**B3.** Controlli dentro l'api (uno alla volta):
```bash
docker compose exec -T api ls /app/ortofoto_fonti
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/ortofoto/fonti').read()[:200])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/s2cloudless2016/12/2190/1478.jpg'); print(r.status, r.headers['Content-Type'])"
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/edifici/orizzonte?lat=44.06&lon=12.567&h=10').read()[:150])"
```
Attesi: `emilia_romagna.toml  italia.toml  toscana.toml`; `b'{"fonti":[{"id":"rer2023"…` (o senza `rer2023` se l'hai
spenta); `200 image/jpeg`; un testo con `"angoli"`. Un errore `HTTP Error 503` sull'ultima riga vuol dire che il server
non raggiunge S3 o che manca `omfiles`: mandami la riga.

**B4.** Pulizia: `rm ~/sito.tar.gz`, poi `exit`.

### C. Cloudflare (dal browser)

**C1.** La regola di rate limiting «API EuGEnio» (60 richieste in 10 s su `/api/`) bloccherebbe le tessere delle
ortofoto (una mappa ne chiede 20–40 insieme). Apri **statocritico.it** → **Security** → **Security rules** (o **WAF** →
**Rate limiting rules**) → **API EuGEnio** → **Edit** → **Edit expression** e scrivi:
```
(starts_with(http.request.uri.path, "/api/") and not starts_with(http.request.uri.path, "/api/ortofoto/"))
```
Premi **Save**. Le tessere restano limitate dal server (3.000 all'ora per indirizzo) e dalla cache di Cloudflare.

### D. Prove nel browser (Ctrl+F5)

**D1.** Menu › Patrimonio › **Ortofoto**: si apre Rimini con l'ortofoto RER (o Sentinel-2, se l'hai spenta); sotto la
mappa la riga «Ortofoto: … – licenza CC BY 4.0…». A destra cambia fonte: la riga cambia con lei.

**D2.** Menu › Fotovoltaico › **Sole e irradiazione su tetti e facciate**: clic su «Calcola il sole sulle facciate»: dopo
qualche secondo la tabella per orientamento e le facciate colorate sulla mappa.

**D3.** Menu › Fotovoltaico › **Confronto con PVGIS**: «Aggiungi un'area», clic su un tetto, «Calcola la producibilità»,
poi «Confronta con PVGIS»: tabella EuGEnio / PVGIS e grafico mensile.

**D4.** Menu › Edificio › **Obblighi di legge**: tabella con la potenza minima P = k · S, la zona climatica e H'T massimo;
cambia «Intervento» e «edificio pubblico»: i valori cambiano.

**D5.** Scegli «Sfondo della mappa: Ortofoto RER…» e scarica il **PDF**: nella sezione «Figure» c'è la vista con
l'ortofoto e la didascalia con licenza e citazione.

### E. Repository (sul PC)

```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git status
git add -A
git commit -m "Fase B edifici 3D: proxy delle ortofoto, facciate, orizzonte lontano, PVGIS, obblighi D.Lgs. 199/2021, classifica di priorità; Previsioni a schede"
git push
```
Prima del push `git status` non deve mostrare `fase2-gradi-giorno` né file `.env`.

### Da fare a mano (Fase B)

- Alla risposta dell'Archivio Cartografico: `stato = "confermata"` in `fase10-edifici3d/ortofoto/emilia_romagna.toml`
  (poi passi A3 per il solo TOML e rebuild dell'api), oppure `ORTOFOTO_SPENTE=rer2023`.
- Per un sito puntuale con ortofoto AGEA: procedura in `fase10-edifici3d/README.md` § «Ortofoto AGEA per un sito».

### Se qualcosa va storto (Fase B)

- **Le tessere non arrivano** (mappa grigia): `docker compose logs --tail 40 api | grep -i ortofoto` e mandami le righe;
  se vedi `429` nella console del browser, il passo C1 non è stato fatto.
- **L'api non riparte**: `docker compose logs --tail 40 api`.

## Fase C – LiDAR, pipeline notturna, pagina di stato e modelli DXF/IFC (edifici 3D, § 15)

Cosa si pubblica (insieme alle sezioni di sopra: stesso sito `?v=20261104a`, stesso rebuild dell'api):
- **fase 10**: `edifici3d/lidar.py`, `pipeline.py`, `campione.py`, `importa.py` (nuovi), `__main__.py`, `fonti.py`,
  cartella `zone/` (`rimini.toml`, `campione.toml`), `fonti/emilia_romagna.toml` (WCS del DTM 5 m corretto),
  `requirements.txt`, `Dockerfile` (container della pipeline);
- **server**: `servizio/interno.py` (nuovo), `app.py`, `config.py`, `protezione.py`, `report_servizi.py`; `Caddyfile`,
  `docker-compose.yml` (servizio `edifici-lidar`), `api/requirements.txt` (PyJWT, cryptography), `.env.example`;
- **sito**: `edificio3d.js`, `stile.css`, le 9 pagine 3D, `dati/edifici3d/lidar/` (falde del campione sintetico),
  cartella nuova `interno/` (`edifici.html`, `edifici.js`, `interno.css`).

Per Rimini oggi **nessuna fonte DSM o LAS è attiva** (RER su richiesta, DSM costa 2019 senza licenza scritta, PNRR non
ancora scaricabile): la pipeline parte, scrive «in attesa» nella pagina di stato e si ferma. Il DTM 0,5 m RER è già attivo.
Inoltre la pipeline lavora solo le tessere con i corpi della Fase A: prima va fatto `prepara` su Rimini (sezione Fase A
di `AGGIORNAMENTO_2026-11-03.md`).

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

### FC-A. Sul PC (PowerShell)

**FC-A1.** Se hai già fatto i passi A1–A3 della Fase B con questo zip, sito e server della fase 4 sono già copiati,
tranne questi file. Copiali (un comando alla volta, ognuno deve mostrare `100%`):
```powershell
scp fase4-server\servizio\interno.py fase4-server\servizio\app.py fase4-server\servizio\config.py fase4-server\servizio\protezione.py fase4-server\servizio\report_servizi.py eugenio:~/energia/fase4-server/servizio/
scp fase4-server\Caddyfile fase4-server\docker-compose.yml fase4-server\.env.example eugenio:~/energia/fase4-server/
scp fase4-server\api\requirements.txt eugenio:~/energia/fase4-server/api/
scp -r fase10-edifici3d eugenio:~/energia/
```
Se non hai ancora fatto la Fase B, fai prima i suoi passi A1–A3: il pacchetto del sito comprende già la cartella
`interno/` e i file nuovi della pagina 3D.

### FC-B. Cloudflare Access (dal browser, una volta sola)

**FC-B1.** Apri **one.dash.cloudflare.com** (Zero Trust) con l'account di statocritico.it. In **Settings** →
**Custom Pages** (o **Team name and domain**) leggi il **Team domain**: è del tipo `<nome>.cloudflareaccess.com`.
Annotalo (serve al passo FC-C1; non va scritto altrove).

**FC-B2.** **Access** → **Applications** → **Add an application** → **Self-hosted**. Nome: `EuGEnio interno`.
**Session Duration**: 24 hours.

**FC-B3.** In **Application domain** aggiungi due righe (pulsante **Add domain**):
- Subdomain `eugenio`, Domain `statocritico.it`, Path `interno/*`
- Subdomain `eugenio`, Domain `statocritico.it`, Path `api/interno/*`

**FC-B4.** **Next** → **Add a policy**: nome `solo Paolo`, Action **Allow**, regola **Include** → **Emails** → la tua email
(la stessa della policy di `notizie.statocritico.it/admin`). Metodo di accesso: **One-time PIN** (come per listmonk).
**Next** → **Add application**.

**FC-B5.** Riapri l'applicazione `EuGEnio interno` → scheda **Overview** (o **Basic information**): copia
**Application Audience (AUD) Tag** (una lunga stringa esadecimale).

### FC-C. Sul server (`ssh eugenio`)

**FC-C1.** Righe nuove nel `.env` (scrivi i tuoi valori al posto dei segnaposto, senza virgolette):
```bash
cd ~/energia/fase4-server
grep -q CF_ACCESS_ .env || printf "CF_ACCESS_TEAM_DOMAIN=\nCF_ACCESS_AUD=\nCF_ACCESS_EMAIL=\nEDIFICI_STATO=/dati/edifici_stato\nINTERNO_ORA=300\n" >> .env
nano .env
```
In nano compila `CF_ACCESS_TEAM_DOMAIN=<team>.cloudflareaccess.com`, `CF_ACCESS_AUD=<AUD tag>` e
`CF_ACCESS_EMAIL=<la tua email>`; salva con Ctrl+O, Invio, Ctrl+X. Controllo (deve stampare 5):
```bash
grep -c -E "^(CF_ACCESS_TEAM_DOMAIN|CF_ACCESS_AUD|CF_ACCESS_EMAIL|EDIFICI_STATO|INTERNO_ORA)=" .env
```

**FC-C2.** Cartella dello stato, scrivibile dall'utente 1000 dei container (come le altre):
```bash
mkdir -p /srv/energia/dati/edifici_stato /srv/energia/dati/edifici
setfacl -R -m u:1000:rwx -m d:u:1000:rwx /srv/energia/dati/edifici_stato /srv/energia/dati/edifici
```

**FC-C3.** Api (PyJWT nuovo), caddy e immagine della pipeline:
```bash
cd ~/energia/fase4-server && docker compose up -d --build api && docker compose up -d --force-recreate caddy
docker compose --profile edifici build edifici-lidar
```
L'ultima riga dura qualche minuto (GDAL, laspy, IfcOpenShell per ARM) e finisce con `Built` (o `naming to … energia-edifici`).

**FC-C4.** Prove (una alla volta):
```bash
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/salute').read()[-60:])"
docker compose --profile edifici run --rm edifici-lidar lidar-fonti --zona rimini --prova
docker compose --profile edifici run --rm edifici-lidar lidar --zona rimini --archivio /dati/edifici --stato /dati/edifici_stato --subito
```
Attesi: un testo che finisce con `"previsioni_in_corso": 0}`; l'elenco delle fonti (quattro «in attesa», `rer_dtm05` e
`rer_dtm5` «attiva») con le righe della prova dal vivo (quadro di unione «coperta 32_…», `HTTP 200 image/tiff` per i DTM);
un JSON con `"esito": "in attesa"` e `"motivo": "nessuna fonte DSM o LAS attiva …"`.

**FC-C5.** Cron dell'host per la notte (3:30, dopo i mercati; la pipeline si ferma da sola alle 7:00):
```bash
(crontab -l 2>/dev/null; echo "30 3 * * * cd ~/energia/fase4-server && docker compose --profile edifici run --rm edifici-lidar >> ~/edifici.log 2>&1") | crontab -
crontab -l | grep edifici
```
Deve comparire la riga appena aggiunta.

### FC-D. Prove nel browser

**FC-D1.** Apri `https://eugenio.statocritico.it/interno/edifici.html`: compare la pagina di Cloudflare Access; chiedi
il codice, scrivilo: si apre «Stato della pipeline degli edifici» con Rimini (fonti in attesa, una notte «in attesa»)
e lo spazio su disco.

**FC-D2.** In una finestra anonima apri `https://eugenio.statocritico.it/api/interno/edifici/stato`: deve comparire il
login di Cloudflare, mai i dati.

**FC-D3.** Menu › Patrimonio › **Modelli 3D** (Ctrl+F5): sulla demo sintetica il corpo a capanna dell'edificio E-DEMO ha
le falde a gradini; nel passo «Corpi» la tabella «Falde dei tetti» con l'avviso del rilievo sintetico. «Aggiungi un'area»
e clic sulla falda sud: inclinazione 23°, orientamento 180°.

### FC-E. Quando arrivano i dati (a mano)

- **Risposta della Regione** su DSM e LAS RER 2023-24 (e sulla licenza del DSM della costa 2019): in
  `fase10-edifici3d/zone/rimini.toml`, per la fonte giusta, scrivi `url` (link per tessera con `{tavola}`, oppure
  `"file:/srv/energia/dati/consegne/rer_dsm/{tavola}.tif"` se consegnano su disco), `licenza_confermata = true`,
  `attiva = true`; poi ricopia la cartella `fase10-edifici3d` e ricostruisci l'immagine (FC-C3, ultima riga). La notte
  dopo la pagina di stato mostra le tessere fatte; misura spazio e tempi (righe «Restano (kB)» e «Secondi»).
- **LiDAR PNRR** (dopo il 7/11/2026, app PST): se c'è un modo di scaricare per tessera con licenza scritta, compila
  `pnrr_dsm` allo stesso modo (priorità 1: vince sulle altre).
- **Modelli DXF/IFC di un edificio**: sul PC `pip install ezdxf ifcopenshell` nell'ambiente della fase 10, poi
  `python -m edifici3d importa-modello file.ifc --uscita modello.geojson` (DXF non georeferenziati: `--posa` con due
  punti noti) e nella pagina 3D «Usa il tuo modello».

### Se qualcosa va storto (Fase C)

- **La pagina interna dà 503** «non configurata»: mancano `CF_ACCESS_TEAM_DOMAIN` o `CF_ACCESS_AUD` nel `.env` (FC-C1),
  poi `docker compose up -d api`.
- **Dà 403 anche dopo il login**: il team domain o l'AUD non coincidono con quelli dell'applicazione; `docker compose
  logs --tail 20 api | grep interno` e mandami le righe (senza il gettone).
- **La pipeline non parte**: `tail -30 ~/edifici.log`; «fuori dalla finestra» vuol dire che è stata lanciata a mano senza
  `--subito`; «già in corso» che un'altra esecuzione tiene il blocco.

## Fase D – EuGEnio Visure: lettore delle visure, importazione in Patrimonio, avviatore .exe, Docker (§ 15)

Cosa c'è (dettagli in `fase11-visure/README.md`):
- **fase 11**: lettore locale delle visure catastali in PDF (`fase11-visure/visure`, solo pypdf): per immobile e per
  soggetto, fabbricati e terreni; comune, codice, sezione, foglio, particella, subalterno, zona, categoria, classe,
  consistenza, superficie, rendita, indirizzo, piani; uscite `indice.csv`, `edifici_visure.csv` o
  `patrimonio_con_visure.csv`, `visure.json`, `registro.txt`, PDF ordinati. **Nessuna credenziale, nessun accesso a
  SISTER**; intestatari e codici fiscali tolti prima della lettura (a parte solo con `--includi-intestatari`); comando
  `controlla` per verificare che una visura sia anonimizzata. Pagina locale su `http://127.0.0.1:8770`. Avviatore
  `EuGEnioVisure.exe` con versioni approvate (impronte SHA-256 in `avviatore/versioni_approvate.json`), workflow
  `.github/workflows/visure-windows.yml` (test, .exe, firma SignPath se configurata, release sul tag `visure-v…`),
  immagine Docker, proposte upstream in `UPSTREAM.md`, verifica delle condizioni d'uso nel README;
- **sito** (stessa versione `?v=20261104a`, nessun rebuild dell'api): passo «Visure catastali» in Patrimonio (file
  nuovi `visure_abbina.js` e `visure_patrimonio.js`; cambiati `patrimonio.js`, `patrimonio.html`, `stile.css`,
  `visure.html`, `sitografia.html`). L'abbinamento si fa nel browser: al server vanno solo comune, sezione, foglio e
  particella; le colonne delle visure non entrano nel report.

Provato su **visure sintetiche** (dati inventati): le visure vere anonimizzate servono per adattare `regole.toml`.
Lo scaricamento automatico con `visura-api` resta spento finché l'Agenzia non risponde (README fase 11, «Condizioni
d'uso»).

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

### FD-A. Sul PC: prova del lettore (PowerShell)

**FD-A1.** Se non l'hai già fatto per le sezioni di sopra, estrai `eugenio_2026-11-04.zip` sopra la cartella del progetto
(sovrascrivi). Poi crea l'ambiente della fase 11 (una volta sola):
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase11-visure
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```
L'ultima riga finisce con `Successfully installed …`.

**FD-A2.** Test (sei in `fase11-visure`):
```powershell
.\.venv\Scripts\python -m pytest -q tests
```
Deve finire senza `failed`: `67 passed` dove ci sono node, Playwright con Chromium e le librerie della fase 7;
altrimenti alcune prove risultano `skipped` (per esempio `59 passed, 4 skipped`), va bene.

**FD-A3.** Visure sintetiche e lettura:
```powershell
.\.venv\Scripts\python -m visure esempi --uscita ..\..\visure_prova
.\.venv\Scripts\python -m visure leggi ..\..\visure_prova --patrimonio ..\..\visure_prova\patrimonio_esempio_visure.csv --uscita ..\..\visure_prova\risultati --ordina
```
La seconda riga elenca i 6 PDF (4 «letta», uno «non_riconosciuta», uno «senza_testo») e finisce con
`9 unità, 6 edifici`. In `visure_prova\risultati` trovi `patrimonio_con_visure.csv` (si apre con Excel) e `registro.txt`.

**FD-A4.** Pagina locale:
```powershell
.\.venv\Scripts\python -m visure web
```
Si apre il browser su `http://127.0.0.1:8770`: scegli i PDF di `visure_prova`, premi «Leggi le visure», scarica lo zip.
Chiudi con Ctrl+C nella finestra di PowerShell.

### FD-B. Sito

**FD-B1.** Se hai già pubblicato il sito con i passi A2, A3 e B2 della Fase B usando **questo** zip, i file della Fase D
sono già sul server: passa a FD-C. Altrimenti rifai solo quei tre passi (pacchetto del sito, `scp ..\sito.tar.gz`,
`tar -xzmf` sul server); per la Fase D non serve ricostruire l'api.

### FD-C. Prove nel browser (Ctrl+F5)

**FD-C1.** Menu › Patrimonio › **Patrimonio**: carica `visure_prova\patrimonio_esempio_visure.csv` e premi «Trova gli
edifici» (le particelle sono inventate: Zornade può non trovarle o trovarne altre, va bene). Al passo **«Visure
catastali»** carica `visure_prova\risultati\indice.csv`: compaiono i conteggi e, nelle schede, le righe «Visura (…)».

**FD-C2.** Premi «Scarica il risultato con le visure (CSV)»: il file ha le colonne `visura_…`.

**FD-C3.** Menu › Patrimonio › **Visure**: la pagina descrive il programma e le condizioni d'uso.

### FD-D. L'.exe per Windows (GitHub Actions)

**FD-D1.** Dopo il commit e il push (passo FD-F), apri github.com/statocritico/eugenio → **Actions** → **visure-windows**
→ **Run workflow** → **Run workflow**. Dopo 5–10 minuti i job `test-linux` ed `exe` sono verdi (il job `firma` è
«skipped» finché SignPath non è configurato, la release non parte senza tag).

**FD-D2.** Apri l'esecuzione → in fondo, **Artifacts** → scarica `eugenio-visure-non-firmato`, estrai
`EuGEnioVisure.exe` in una cartella di prova e fai doppio clic. Windows mostra «PC protetto da Windows» (l'.exe non è
ancora firmato): **Ulteriori informazioni** → **Esegui comunque**. Si apre una finestra di testo con «in uso la versione
0.1.0» e poi il browser sulla pagina locale.

**FD-D3.** Solo dopo la prova con le visure vere: tag della release (pubblica l'.exe e lo zip del lettore):
```powershell
git tag visure-v0.1.0
git push origin visure-v0.1.0
```

### FD-E. Firma (quando vuoi distribuire l'.exe)

Procedura in `fase11-visure/README.md`, «Firma dell'.exe»: domanda a SignPath Foundation, progetto su app.signpath.io,
segreto `SIGNPATH_API_TOKEN` e variabili `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_POLICY_SLUG` su
GitHub. Token e certificati non vanno mai scritti nei file del progetto.

### FD-F. Repository (sul PC)

```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git status
git add -A
git commit -m "Fase D: EuGEnio Visure (lettore locale delle visure, importazione in Patrimonio, avviatore con versioni approvate, Docker)"
git push
```
Prima del push `git status` non deve mostrare `fase2-gradi-giorno`, file `.env`, cartelle `Visure_…`,
`intestatari_DATI_PERSONALI.csv` né visure vere (il `.gitignore` le esclude). `visure_prova` sta fuori dalla cartella
`eugenio`, quindi non compare.

### Da fare a mano (Fase D)

- Visure vere anonimizzate: prima `.\.venv\Scripts\python -m visure controlla visura.pdf` (deve dire «nessun dato
  personale»), poi mandamele; con quelle adatto `regole.toml` e i test.
- Richiesta di chiarimento all'Agenzia delle Entrate (`fase11-visure/UPSTREAM.md`, § 2) e copia datata delle condizioni
  generali che accetti nell'area riservata; proposte a Zornade (§ 1) insieme alla risposta del § 14.2 della proposta.

### Se qualcosa va storto (Fase D)

- **`pytest` mostra `failed`**: mandami le ultime 20 righe.
- **Una visura vera dà «non_riconosciuta» o «manca: …»** nel `registro.txt`: mandami solo le righe del registro (non
  la visura, se non è anonimizzata).
- **L'.exe si chiude subito**: aprilo da PowerShell (`.\EuGEnioVisure.exe --stato`) e mandami le righe che stampa;
  il registro è in `%LOCALAPPDATA%\EuGEnio\Visure\avviatore.log`.

## Fase E – fonti regione per regione, altezze di Zornade, modulo UNI privato, articolo (§ 15)

Cosa c'è (dettagli in `fase10-edifici3d/README.md`, § «Fase E – come si usa»):
- **fonti per regione**: `fase10-edifici3d/fonti/regioni.toml`, 21 voci (19 regioni e 2 province autonome) × 4 temi
  (edifici con altezze, DTM, DSM/LiDAR, ortofoto) più le fonti nazionali, con licenza, stato, scheda, prova dal vivo e
  data; comando `python -m edifici3d regioni [--prova] [--markdown]`. Esito al 04/11/2026: **17 attive, 48 in attesa, 19
  non disponibili** su 84. Accese davvero: le ortofoto di **Bolzano 2023** e **Trento 2015** (`ortofoto/bolzano.toml`,
  `ortofoto/trento.toml`, CC BY 4.0, GetMap provato). Le altre attive (DBGT Lombardia, edifici FVG con altezza, CTR 3D
  Liguria, Edifici P.A.T. 3D, DTM/DSM di Bolzano e Trento, DTM di Lombardia e Liguria, sagome del Veneto) aspettano gli
  adattatori del formato o una zona in `zone/`. Molti portali del Centro-Sud (e il Piemonte) chiudono le connessioni dal
  container: da riprovare dal server (passo FE-C3);
- **Emilia-Romagna**: le schede RNDT ora dicono CC BY 4.0 anche per il DSM 2023-24 (23/10/2026; download ancora su
  richiesta, WCS 401) e per il **DSM della costa 2019**: in `zone/rimini.toml` la sua licenza è confermata, ma la fonte
  resta **spenta** perché copre solo la costa e la pipeline non sa ancora limitarla alla sua copertura. Nella prova
  FC-C4 l'esito resta «in attesa»;
- **altezze di Zornade** (ODbL): `edifici3d/zornade.py` legge un estratto consegnato da Zornade (mai l'API: il blocco
  `buildings` non ha altezze), scarta le altezze GlobalBuildingAtlas o non commerciali, scrive solo in
  `odbl/<zona>/prodotti/zornade/` con `LEGGIMI_ODbL.txt` e confronta le altezze con quelle CC BY; provato su un **campione
  sintetico** (comandi `zornade-campione`, `zornade-altezze`);
- **analisi 5 e 7–13**: aggancio pubblico `edifici3d/analisi.py`, rotte `GET /api/analisi/stato` e `POST /api/analisi/{id}`
  (`servizio/analisi.py`), script `analisi_uni.js` nelle pagine Fabbisogno, Comunità energetiche, Facciate e tetti, Pompe
  di calore e solare termico, Clima che cambia, Prefattibilità LEED: senza il modulo privato scrivono «analisi non
  disponibile in questa installazione»;
- **modulo privato** `fase10-edifici3d/uni_privato/`: solo struttura (passi a parole, 16 tabelle vuote, test che saltano),
  **nessun testo o coefficiente UNI**; fuori da git (`.gitignore`), dallo zip pubblico e dalle immagini Docker
  (`.dockerignore` nuovo nella cartella principale); consegnato nello zip a parte `eugenio_uni_privato_2026-11-04.zip`;
- **articolo**: bozza in `documenti/ARTICOLO_EDIFICI_3D_bozza.md` (con le cose da controllare prima di pubblicarla);
- **sito** (stessa versione `?v=20261104a`): `analisi_uni.js` (nuovo), le 6 pagine delle analisi, `ortofoto.html` e
  `sitografia.html` (fonti di Bolzano e Trento); **server**: `servizio/analisi.py` (nuovo), `app.py`, `api/Dockerfile`.

Prove: fase 4 **150** test, fase 5 **13**, fase 6 **40**, fase 7 **13**, fase 8 **23**, fase 9 **6**, fase 10 **56**, fase 11
**67**, tutti passano (fase 3 non ha test); `uni_privato` 6 passano e 8 saltano (tabelle da compilare). Chromium headless
(Playwright) con le rotte vere `analisi` e `ortofoto` e il sito statico: le 6 pagine dicono «non disponibile» senza
modulo e «installato» per l'analisi di un modulo finto; pagina Ortofoto su Bolzano e Trento con tessere 200 dal proxy e
licenza sotto la mappa; nessun errore JavaScript.

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

### FE-A. Sul PC (PowerShell)

**FE-A1.** Se non l'hai già fatto per le sezioni di sopra, estrai `eugenio_2026-11-04.zip` sopra la cartella del progetto
(sovrascrivi). Poi estrai **anche** `eugenio_uni_privato_2026-11-04.zip` nella stessa cartella `eugenio`: crea
`fase10-edifici3d\uni_privato\`. Controllo:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
dir fase10-edifici3d\uni_privato
git check-ignore -v fase10-edifici3d/uni_privato/__init__.py
```
Il primo comando elenca `__init__.py`, `LEGGIMI.md`, `analisi`, `tabelle`, `tests`; il secondo stampa la riga
`.gitignore:…:fase10-edifici3d/uni_privato/` (il modulo resta fuori da git).

**FE-A2.** Test della fase 10 (nell'ambiente della fase 10, se l'hai; altrimenti salta):
```powershell
cd fase10-edifici3d
python -m pytest -q tests
python -m pytest -q uni_privato\tests
python -m edifici3d regioni
cd ..
```
Attesi: `56 passed`; `6 passed, 8 skipped`; il riepilogo per regione che finisce con
`conteggi: {'attiva': 17, 'in attesa': 48, 'non disponibile': 19}`.

**FE-A3.** Copia sul server (un comando alla volta, ognuno deve mostrare `100%`). Se hai già rifatto il pacchetto del sito
con i passi A2–A3 della Fase B usando **questo** zip, salta la prima riga:
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
scp ..\sito.tar.gz eugenio:~/
scp fase4-server\servizio\analisi.py fase4-server\servizio\app.py eugenio:~/energia/fase4-server/servizio/
scp fase4-server\api\Dockerfile eugenio:~/energia/fase4-server/api/
scp .dockerignore eugenio:~/energia/
scp -r fase10-edifici3d eugenio:~/energia/
scp -r fase10-edifici3d\uni_privato eugenio:/srv/energia/dati/
```
(L'ultima riga mette il modulo privato dove lo cerca l'api; la penultima lo copia anche in `~/energia`, che è privato: il
`.dockerignore` lo tiene fuori dalle immagini.)

### FE-B. Sul server (`ssh eugenio`)

**FE-B1.** Permessi del modulo privato per l'utente 1000 dei container:
```bash
setfacl -R -m u:1000:rX /srv/energia/dati/uni_privato && ls /srv/energia/dati/uni_privato
```
Deve elencare `LEGGIMI.md  __init__.py  analisi  tabelle  tests`.

**FE-B2.** Sito, api e immagine della pipeline:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c analisi_uni /srv/energia/sito/edificio-fabbisogno.html
cd ~/energia/fase4-server && docker compose up -d --build api
docker compose --profile edifici build edifici-lidar
```
La prima riga stampa `1`. Le ricostruzioni durano qualche minuto.

**FE-B3.** Controlli (uno alla volta):
```bash
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/analisi/stato').read()[:300])"
docker compose exec -T api ls /app/ortofoto_fonti
docker compose exec -T api ls /app/edifici3d
docker compose --profile edifici run --rm --entrypoint sh edifici-lidar -c "test -d /app/uni_privato && echo NELL_IMMAGINE || echo fuori"
```
Attesi: `b'{"interfaccia":1,"modulo":true,"analisi":[{"id":"5",…"disponibile":false,…` (`modulo` è `true` perché il
modulo c'è, ma le analisi restano non disponibili finché le tabelle sono vuote); `bolzano.toml  emilia_romagna.toml
italia.toml  toscana.toml  trento.toml`; `__init__.py  analisi.py`; `fuori` (l'immagine della pipeline, che copia tutta
la fase 10, non contiene il modulo privato).

**FE-B4.** Verifica dal vivo delle fonti dal server (molti portali chiudono le connessioni che arrivano da fuori Italia):
```bash
docker compose --profile edifici run --rm edifici-lidar regioni --prova > ~/regioni_prova.txt; tail -40 ~/regioni_prova.txt
```
Mandami il file `~/regioni_prova.txt` (o le righe con `errore` e quelle di Piemonte e Basilicata): con quelle aggiorno
gli stati in `regioni.toml`.

**FE-B5.** Pulizia: `rm ~/sito.tar.gz`, poi `exit`.

### FE-C. Prove nel browser (Ctrl+F5)

**FE-C1.** Menu › Edificio › **Pompe di calore e solare termico**: sotto il riquadro grigio compaiono due righe «… (analisi
10): analisi non disponibile in questa installazione.» e «… (analisi 11): …». Lo stesso in Fabbisogno, Comunità
energetiche, Facciate e tetti, Clima che cambia e Fotovoltaico › Prefattibilità LEED.

**FE-C2.** Apri `https://eugenio.statocritico.it/ortofoto.html?lat=46.4983&lon=11.3548&z=17`: si apre Bolzano con
l'ortofoto 2023; a destra la fonte «Ortofoto Provincia di Bolzano 2023 (20 cm)» con «licenza verificata»; sotto la mappa
«Ortofoto: Provincia autonoma di Bolzano – Ortofoto 2023, 20 cm (CC BY 4.0)». Con `lat=46.0679&lon=11.1211` Trento 2015.

### FE-D. Repository (sul PC)

```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git status
git add -A
git commit -m "Fase E: fonti regione per regione, ortofoto di Bolzano e Trento, altezze di Zornade in ODbL, aggancio facoltativo alle analisi 5 e 7-13"
git push
```
Prima del push `git status` non deve mostrare `fase10-edifici3d/uni_privato`, `fase2-gradi-giorno` né file `.env`.

### Da fare a mano (Fase E)

- **Modulo privato**: compilare le tabelle di `uni_privato/tabelle/` e scrivere i passi in `uni_privato/analisi/`
  leggendo le norme (istruzioni in `uni_privato/LEGGIMI.md`); poi ricopiare la cartella in `/srv/energia/dati/uni_privato`
  e `docker compose restart api`. Le pagine di calcolo delle analisi sono ancora da fare.
- **Fonti in attesa**: mandarmi l'esito di FE-B4; email alla Regione FVG per la licenza del LiDAR 2017-2020 (Eagle.fvg);
  per l'ER il DSM della costa 2019 non va più chiesto per la licenza (scheda RNDT in CC BY 4.0), resta da chiedere
  l'accesso al DSM 2023-24.
- **Zornade**: la risposta del § 14.2 la mandi tu; quando arriva un estratto con le altezze LiDAR:
  `python -m edifici3d zornade-altezze --file <estratto> --archivio /srv/energia/dati/edifici --confronta-con
  /srv/energia/dati/edifici/cc-by/er/prodotti/contesto` (nell'ambiente della fase 10 o nel container `edifici-lidar`).
- **Articolo**: rileggere `documenti/ARTICOLO_EDIFICI_3D_bozza.md`, togliere la nota iniziale e pubblicarlo su Substack
  dopo aver pubblicato il sito.

### Se qualcosa va storto (Fase E)

- **L'api non riparte** dopo FE-B2: `docker compose logs --tail 40 api`; una riga «modulo privato … non caricato» vuol dire
  che il modulo ha un errore: l'api funziona comunque e le analisi restano «non disponibili».
- **FE-B3 stampa `NELL_IMMAGINE`**: il `.dockerignore` non è arrivato in `~/energia` (passo FE-A3): ricopialo e rifai FE-B2.
- **FE-C1 non mostra le righe**: la pagina è ancora quella vecchia (Ctrl+F5) o il pacchetto del sito non è stato estratto.

## Importa DXF/IFC – disegni e modelli BIM letti nel browser, file pesanti convertiti sul PC (04/11/2026 notte)

Decisioni del 04/11/2026 (in `RIEPILOGO.md`, «Decisioni di Paolo del 04/11/2026»): ortofoto RER accese con «uso da
confermare»; costi dell'energia della classifica inseriti dall'utente; `--includi-intestatari` delle visure mantenuta e
spenta di default; DXF e IFC letti nel browser in una pagina separata, con la conversione sul PC per i file pesanti.

Cosa c'è:
- **sito** (versione **`?v=20261104b`**, nessun rebuild dell'api): pagina nuova **Patrimonio › Importa DXF/IFC**
  (`importa-dxf-ifc.html`, `importa_modello.js`, `modelli_import.js`, `modelli_worker.js`); librerie nuove in `sito/lib/`
  con le licenze: `dxf-parser/` 1.1.2 (MIT), `web-ifc/` 0.0.77 (MPL-2.0, `web-ifc.wasm` da 1,3 MB e 5,9 MB di JavaScript),
  `clipper-lib/` 6.4.2 (Boost), `proj4/` 2.22.0 (MIT). Si caricano **solo** in questa pagina, dentro il Web Worker, e
  web-ifc solo quando arriva un IFC. La pagina 3D apre il risultato con `modelli3d.html?modello=locale` (memoria della
  scheda, mai il server); il testo «Usa il tuo modello» delle 9 pagine 3D rimanda alla pagina nuova. Cambiati anche il
  menu, `edificio3d.js`, `stile.css`, `sitografia.html`, `lib/README.md`;
- **fase 10**: `importa.py` corretto (punti della posa nelle unità del disegno, `IfcMapConversion` con il progetto in
  millimetri, orientamento delle falde riferito al nord vero, plugin di IfcOpenShell trovati anche nell'.exe, primo errore
  di IfcOpenShell nel messaggio), opzione `--grande` (fino a 500 MB, 8 GB di memoria, 30 minuti, solo sul PC), processo
  figlio anche con «spawn» (Windows) con tetto di memoria; file di prova sintetici `tests/modelli_sintetici.py`;
- **fase 11**: comando `EuGEnioVisure.exe modello …`, `prova --modelli`, scheda «Modelli DXF/IFC» della pagina locale
  (`visure/modelli.py`); il pacchetto approvato contiene anche `edifici3d/importa.py` (impronta nuova nell'elenco); spec,
  `costruisci_windows.ps1`, workflow e Docker con ezdxf, IfcOpenShell, shapely, pyproj e numpy
  (`requirements-modelli.txt`).

Limiti nel browser: DXF di testo (non binari), IFC STEP (non `.ifczip` né ifcXML), fino a **50 MB** (oltre 30 MB la pagina
avvisa), 180 secondi, 200.000 entità, 2 milioni di triangoli, 1 GB di memoria per web-ifc; solidi ACIS (3DSOLID) non letti
(avviso), blocchi con estrusione diversa da +Z letti in pianta (avviso). Oltre, si converte sul PC.

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

### IM-A. Sul PC (PowerShell)

**IM-A1.** Estrai `eugenio_2026-11-04.zip` sopra la cartella del progetto (sovrascrivi), poi:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase5-sito
python costruisci_pagine.py --controlla
```
Deve comparire `versione 20261104b: 0 file da rigenerare`.

**IM-A2.** Pacchetto del sito (sei in `fase5-sito`), come al passo A2 della Fase B:
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
```

**IM-A3.** Copia sul server (ognuno deve mostrare `100%`):
```powershell
scp ..\sito.tar.gz eugenio:~/
scp fase10-edifici3d\edifici3d\importa.py fase10-edifici3d\edifici3d\__main__.py eugenio:~/energia/fase10-edifici3d/edifici3d/
```
Se pubblichi insieme alle sezioni di sopra, basta il pacchetto del sito di questo passo (contiene tutto).

### IM-B. Sul server (`ssh eugenio`)

**IM-B1.** Estrai il sito e controlla la versione (deve stampare un numero maggiore di 0):
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261104b /srv/energia/sito/importa-dxf-ifc.html
```

**IM-B2.** Il WebAssembly deve arrivare con il suo tipo (deve stampare `content-type: application/wasm`):
```bash
curl -sI https://eugenio.statocritico.it/lib/web-ifc/web-ifc.wasm | grep -i content-type
```

### IM-C. Prove nel browser (Ctrl+F5)

**IM-C1.** Sul PC prepara i file di prova sintetici (nell'ambiente della fase 10, con ezdxf e IfcOpenShell):
```powershell
cd fase10-edifici3d
.\.venv\Scripts\python tests\modelli_sintetici.py ..\..\prove_modelli
cd ..
```
Compaiono cinque file in `C:\Users\ingpa\Documents\claude\pj\statocritico\prove_modelli`.

**IM-C2.** Menu › Patrimonio › **Importa DXF/IFC**. Premi F12 e apri la scheda **Rete** (Network).

**IM-C3.** Passo 1: scegli `casa_sito.ifc`. Dopo qualche secondo: «File letto», al passo 2 la pianta con due corpi, al
passo 3 «come indicato nel file (IfcSite)»; il modello compare sulla mappa vicino a Rimini e la tabella del passo 4 dice
capanna (gronda 7, colmo 10) e piano (4). Nella scheda Rete compaiono `web-ifc.wasm` e le tessere dell'ortofoto, **nessuna
richiesta POST**.

**IM-C4.** Premi **Apri nella pagina Modelli 3D**: si apre la pagina 3D con «Modello «casa_sito»: 2 corpi (letto solo in
questo browser)».

**IM-C5.** Torna a Importa DXF/IFC, scegli `casa_metri.dxf`. Al passo 3 resta scelto «due punti noti»: scrivi nella riga 1
`0`, `0`, `12,5665`, `44,06` e nella riga 2 `10`, `0`, `12,566625`, `44,06`, poi **Posiziona il modello**: sei corpi
(capanna, padiglione, monofalda, tre piani) e l'avviso dei 3DSOLID. Prova anche il clic: clic sulla pianta vicino a uno
spigolo, poi clic sulla mappa sul punto vero.

**IM-C6.** In un'altra pagina (es. Patrimonio › Modelli 3D) la scheda Rete **non** deve mostrare `web-ifc`, `dxf-parser`,
`clipper` né `proj4`.

### IM-D. L'.exe con la conversione dei modelli (GitHub Actions)

**IM-D1.** Dopo il push (IM-E) apri su GitHub **Actions** → `visure-windows` → **Run workflow**. Il passo «Prova
dell'.exe» converte un IFC e un DXF sintetici; alla fine scarica l'artefatto `eugenio-visure-non-firmato`.

**IM-D2.** Sul PC, nella cartella dell'.exe (PowerShell):
```powershell
.\EuGEnioVisure.exe --non-aggiornare prova --modelli
.\EuGEnioVisure.exe --non-aggiornare modello ..\prove_modelli\casa_sito.ifc --uscita casa_sito.geojson
```
Attesi: due righe `OK:` (lettore e conversione dei modelli), poi `2 corpi → casa_sito.geojson`. Il file si apre al passo 1
della pagina Importa DXF/IFC («Modello già convertito: 2 corpi»). Doppio clic sull'.exe: nella pagina locale c'è la scheda
**Modelli DXF/IFC**.

### IM-E. Repository (sul PC)

```powershell
git status
git add -A
git commit -m "Importa DXF/IFC: DXF e IFC letti nel browser, conversione dei file pesanti con EuGEnio Visure"
git push
```
Prima del push `git status` non deve mostrare `fase10-edifici3d/uni_privato`, `fase2-gradi-giorno` né file `.env`.

### Da fare a mano (Importa DXF/IFC)

- Provare la pagina con un **DXF vero** (da CAD) e un **IFC vero** (da Revit, ArchiCAD o simili) e mandarmi l'esito (numero
  di corpi, tetti, avvisi): i file di prova sono sintetici.
- Dopo la prima build su Actions: dimensione e tempo di avvio dell'.exe (la prova Linux pesa 137 MB e parte in ~2,5 s) e
  una conversione con `--grande` di un file grande.

### Se qualcosa va storto (Importa DXF/IFC)

- **«Lettura interrotta dopo 180 secondi»** o **«memoria del browser esaurita»**: il modello è troppo complesso per il
  browser; convertilo sul PC (passo 5 della pagina) e apri il `.geojson`.
- **IM-B2 non stampa `application/wasm`**: la pagina funziona lo stesso (web-ifc ripiega su un caricamento più lento); se
  l'IFC non si apre, mandami le righe rosse della console (F12 → Console).
- **«nessuna geometria leggibile negli elementi dell'IFC (primo errore: …)»** dall'.exe: mandami la riga intera.
- **Il modello cade fuori dall'Italia**: unità del disegno sbagliate (scegli l'unità al passo 1) o punti scambiati.

