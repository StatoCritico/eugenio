# Aggiornamento del 03/11/2026

Cosa si pubblica:
- **sito `?v=20261103a`**:
  - menu principale a cinque gruppi con sottomenu a tendina: Clima e meteo, Patrimonio, Edificio, Cogenerazione,
    Fotovoltaico (tastiera e telefono compresi);
  - Indicatori, Come funziona, F.A.Q., Sitografia, Mirror e Contattaci nella riga in alto a destra («Altre pagine»);
  - 25 pagine nuove «in sviluppo» o «in attesa della licenza GME», senza dati;
  - F.A.Q. nuove ancore `#zornade` e `#dati-mercato`; testi su Zornade aggiornati ai termini del 18/09/2026 (F.A.Q.,
    Licenza, Patrimonio);
- **server**: solo `servizio/report.py` (testo della licenza nei report: Zornade e dati catastali) e
  `servizio/protezione.py` (commento); nessuna rotta nuova.

Nel repository: cartelle nuove `documenti/`, `fase10-edifici3d/`, `fase11-visure/`, `fase12-gme-fotovoltaico/`,
`fase13-cogenerazione/` (solo README e il registro della call GME), `.gitignore` con `fase10-edifici3d/uni_privato/`.

Un'azione per passo. In PowerShell i comandi partono dalla cartella `eugenio` del PC.

## A. Sul PC (PowerShell)

**1.** Estrai lo zip `eugenio_2026-11-03.zip` sopra la cartella del progetto (sovrascrivi i file), poi entra nella
cartella:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```

**2.** Controlla che le pagine siano già rigenerate (non scrive nulla):
```powershell
cd fase5-sito
python costruisci_pagine.py --controlla
```
Deve comparire `versione 20261103a: 0 file da rigenerare`.

**3.** Facoltativo: `python -m pytest tests` deve dire `9 passed` (7 prima della Fase A).

**4.** Prepara il pacchetto del sito (sei ancora in `fase5-sito`):
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
```
Controllo: `dir ..\sito.tar.gz` mostra l'ora di adesso.

**5.** Copia sul server il sito e i due file del server, un comando alla volta:
```powershell
scp ..\sito.tar.gz eugenio:~/
scp fase4-server\servizio\report.py fase4-server\servizio\protezione.py eugenio:~/energia/fase4-server/servizio/
```
Per ogni file deve comparire una riga con `100%`.

## B. Sul server

**6.** Entra nel server con `ssh eugenio`.

**7.** Pubblica il sito:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261103a /srv/energia/sito/index.html
ls /srv/energia/sito/cog-car.html
```
La prima riga stampa un numero maggiore di 0, la seconda il nome del file.

**8.** Ricostruisci l'api con il nuovo `report.py`:
```bash
cd ~/energia/fase4-server && docker compose up -d --build api
docker compose exec -T api grep -c "re-identificare" /app/servizio/report.py
```
Deve stampare **1**.

**9.** Pulizia: `rm ~/sito.tar.gz`, poi esci con `exit`.

## C. Prove nel browser (Ctrl+F5 sulla prima pagina)

**10.** Sul computer: la seconda riga della testata mostra **Clima e meteo, Patrimonio, Edificio, Cogenerazione,
Fotovoltaico** con una freccina. Clic su **Edificio**: si apre la tendina con 8 voci «in sviluppo». Clic fuori: si chiude.

**11.** Da tastiera: premi Tab fino a **Clima e meteo**, poi **freccia giù** (si apre e il fuoco va su Dati climatici),
**freccia destra** (passa a Patrimonio), **Esc** (si chiude).

**12.** Apri **Legge 10**: il gruppo Clima e meteo è sottolineato nel colore del vestito. In alto a destra ci sono
Indicatori, Come funziona, F.A.Q., Sitografia, Mirror, Contattaci.

**13.** Apri **Cogenerazione › Budget di dissipazione CAR**: stato «In attesa della licenza GME», avviso giallo sul GME,
nessun numero di prezzo.

**14.** Dal telefono: **Menu** mostra «Servizi» con i cinque gruppi richiudibili (quello della pagina già aperto), poi
«Altre pagine» e «Aspetto».

**15.** Apri `faq.html#zornade`: si apre la domanda «Cosa posso fare con le particelle e gli indirizzi trovati con
Zornade?».

## D. Repository e zip (sul PC)

**16.**
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git add -A
git commit -m "Menu a cinque gruppi con pagine segnaposto, fasi 10-13 (edifici 3D, visure, GME, cogenerazione), termini Zornade del 18/09/2026, decisione sulle metodiche UNI"
git push
```
Lo zip `eugenio_2026-11-03.zip` è già pronto (lo ha fatto Claude con le stesse esclusioni di sempre: niente `.venv`,
`.git`, `.env`, `iscrizioni`, cache e modulo UNI privato). Prima del push, controlla con `git status` che non compaia
`fase2-gradi-giorno` (è in `.gitignore`).

## Altre cose da fare (manuali)

- Inviare la risposta a Zornade (§ 14.2 di `documenti/PROPOSTA_3D_EDIFICI_E_VISURE.md`).
- Dopo il 7/11/2026: controllo del PST (livelli PNRR sulla Romagna).
- Preparare le visure anonimizzate di esempio.
- Call con il GME: compilare `fase12-gme-fotovoltaico/DOMANDE_CALL_GME.md`.

## Se qualcosa va storto

- **Il menu non si apre**: premi Ctrl+F5; se la testata è ancora quella vecchia, il passo 7 non ha stampato un numero
  maggiore di 0: rifai i passi 4, 5 e 7.
- **L'api non riparte dopo il passo 8**: `docker compose logs --tail 40 api` e mandami le ultime righe.

## Fase A – edifici 3D (aggiunta del 04/11/2026)

Cosa cambia in più rispetto ai passi A–D qui sopra (che restano validi e si fanno insieme):
- **sito**: pagine Modelli 3D, Edificio › Geometria, Edificio › Consumi, Fotovoltaico › Ombre e Fotovoltaico ›
  Producibilità non sono più segnaposto (strumento 3D con MapLibre, etichetta «sperimentale» nel menu); file nuovi
  `edificio3d.js`, `edifici_calcoli.js`, `ombre_worker.js`, cartella `lib/` (MapLibre e PMTiles con le licenze), demo
  sintetica in `dati/edifici3d/`; Patrimonio legge le colonne facoltative di piani e superfici e mostra i consumi per
  metro quadro; Sitografia con le librerie nuove. Al passo 3 i test sono **9**.
- **server**: `servizio/edifici.py` (nuovo), `servizio/app.py`, `servizio/report_servizi.py` (report `edificio`),
  `Caddyfile`, `docker-compose.yml` e `.env.example` (`CARTELLA_EDIFICI`).
- **fase 7**: `territorio/patrimonio.py` (nomi delle colonne facoltative), nell'immagine dell'api.
- **fase 10**: pacchetto `edifici3d` (si usa a mano o, più avanti, nella pipeline: non va nell'immagine dell'api).

**A1.** Al passo 5, al posto del secondo `scp`, copia tutti i file del server (un comando alla volta):
```powershell
scp fase4-server\servizio\report.py fase4-server\servizio\protezione.py fase4-server\servizio\edifici.py fase4-server\servizio\app.py fase4-server\servizio\report_servizi.py eugenio:~/energia/fase4-server/servizio/
scp fase4-server\Caddyfile fase4-server\docker-compose.yml fase4-server\.env.example eugenio:~/energia/fase4-server/
scp fase7-territorio\territorio\patrimonio.py eugenio:~/energia/fase7-territorio/territorio/
scp -r fase10-edifici3d eugenio:~/energia/
```
Ogni file deve mostrare `100%`.

**B1.** Sul server, prima del passo 8, crea la cartella degli edifici e aggiungi la riga al `.env`:
```bash
mkdir -p /srv/energia/dati/edifici/cc-by /srv/energia/dati/edifici/odbl
grep -q CARTELLA_EDIFICI ~/energia/fase4-server/.env || echo "CARTELLA_EDIFICI=/srv/energia/dati/edifici" >> ~/energia/fase4-server/.env
grep CARTELLA_EDIFICI ~/energia/fase4-server/.env
```
Deve stampare `CARTELLA_EDIFICI=/srv/energia/dati/edifici`.

**B2.** Al passo 8 il controllo diventa:
```bash
cd ~/energia/fase4-server && docker compose up -d --build api && docker compose up -d caddy
docker compose exec -T api python -c "import servizio.edifici; print('ok')"
docker compose exec -T api python -c "import urllib.request as u, urllib.error as e
try: print(u.urlopen('http://localhost:8000/api/edifici/gradi-giorno/099014').status)
except e.HTTPError as x: print(x.code)"
```
La seconda riga stampa `ok`; la terza `200`, oppure `503` finché il pacchetto meteo della fase 3 non è sul server (va
bene in entrambi i casi).

**C1.** Prove nel browser (Ctrl+F5):
1. Menu › Patrimonio › **Modelli 3D**: compare l'avviso «Dati sintetici di esempio» e la mappa 3D di un isolato; clic
   sull'edificio arancione: a destra compaiono corpi, superfici e indicatori.
2. Menu › Fotovoltaico › **Producibilità con le ombre**: «Aggiungi un'area», clic su un tetto, «Calcola la producibilità»:
   compare il totale con l'avviso sul clima sintetico (finché il meteo non è sul server) e il grafico mensile.
3. Pulsante **PDF** in fondo: si scarica `edificio.pdf` con l'avviso sui dati sintetici in cima.
4. Patrimonio: con un file senza colonne nuove tutto funziona come prima.

**Dati veri (dopo la pubblicazione, a mano; poi li automatizza la pipeline della fase C):**
1. Dal PC, pagina https://geoportale.regione.emilia-romagna.it/download-data/download-dbtopografico : scarica il
   GeoPackage delle **Unità volumetriche** (UVL) e annota l'indirizzo del file; dalla scheda del **DTM 5×5 m** gli
   indirizzi dei 4 quadranti TIFF.
2. Scrivi gli indirizzi in `fase10-edifici3d/fonti/emilia_romagna.toml` (`[fonti.dbtr_uvl] url`, `[fonti.dtm5] quadranti`).
3. Sul server, in un ambiente con `pip install -r ~/energia/fase10-edifici3d/requirements.txt`:
   `cd ~/energia/fase10-edifici3d && python -m edifici3d scarica --fonte dbtr_uvl --archivio /srv/energia/dati/edifici`,
   poi `python -m edifici3d controlla-uvl --gpkg /srv/energia/dati/edifici/cc-by/er/grezzi/<file>.gpkg` (rapporto su
   gronda/colmo e piani: mandamelo), poi `prepara` con `--riquadro` su Rimini.
4. Con i file in `/srv/energia/dati/edifici/cc-by/er/prodotti/` la pagina usa da sola i dati veri al posto della demo.
