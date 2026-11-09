# Aggiornamento del 09/11/2026 f – tre pagine di Edifici sperimentali (sito `?v=20261109f`, release `v2026.11.09f`)

Punto di partenza: **`?v=20261109e` online** (procedura T1–T10 di `AGGIORNAMENTO_2026-11-09e.md` fatta, release
`v2026.11.09e`). Se T non è ancora fatta, falla prima tutta e poi questa. Cambia **solo il sito**: niente rebuild, niente
`.env`, niente Caddyfile.

## Cosa cambia
Richiesta di Paolo delle 22:15: le prime tre voci del gruppo **Edifici** tornano accessibili, con la **S** di sperimentale:
- **Obblighi di legge** (`edificio-obblighi.html`)
- **Geometria e luce naturale** (`edificio-geometria.html`)
- **Consumi, firma energetica e priorità** (`edificio-consumi.html`)

Nelle tendine compare la «S» (testo intero «sperimentale» nel title e per i lettori di schermo), nel menu del telefono la
parola «sperimentale». Le tre pagine non hanno più l'avviso «Pagina in lavorazione, non ancora verificata». Le altre voci
di Edifici (Fabbisogno UNI, Facciate e tetti, Pompe di calore, Ecobonus, Conto Termico), Cogenerazione › Emissioni e il
Fotovoltaico restano in lavorazione. Voce `20261109f` nelle Novità.

## File toccati
`fase5-sito/parti/testata.html` (le tre voci, nelle tendine e nel menu del telefono); tutte le pagine del sito
rigenerate con `costruisci_pagine.py --versione 20261109f`; `fase5-sito/novita.toml` (voce nuova), `novita.html`,
`novita.xml`; `fase5-sito/tests/test_costruisci_pagine.py` (`EDIFICI_SPERIMENTALI`, 8 «S», 13 voci in lavorazione);
`RIEPILOGO.md`, `DA_FARE.md`, `fase5-sito/README.md`, `EUGENIO_PER_AGENTI.md` (radice e sito, identici), `llms.txt`.

## Test (container, 09/11/2026)
`tests/test_costruisci_pagine.py` e `tests/test_agenti_sito.py`: 42 passed, 1 saltato. Prove delle mappe 3D nel browser
(`tests/test_mappe_browser.py`, comprese le tre pagine): 14 passed.

## Procedura U1–U8

Tempo: circa 15 minuti. Ordine: PC → server → Cloudflare → browser → PC.

### U1. [PC] Zip sopra il clone
Lo zip `eugenio_2026-11-09f.zip` è già in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Measure-Object
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-09f.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261109f" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: `Count : 0` prima; `Count : 1` dopo; una riga nuova: `?? AGGIORNAMENTO_2026-11-09f.md`.

Cosa fare se va male: `Count` diverso da 0 prima → `git status --short` e mandami l'uscita (forse T10 non è stato fatto);
`Count : 0` dopo → zip sbagliato; altre righe `??` → mandamele.

### U2. [PC] Pagine e test della fase 5
```powershell
cd fase5-sito
```
```powershell
python costruisci_pagine.py --controlla
```
```powershell
python -m pytest -q tests/test_costruisci_pagine.py tests/test_agenti_sito.py
```
Cosa aspettarsi: `versione 20261109f: 0 file da rigenerare`; `42 passed, 1 skipped`.

Cosa fare se va male: test rossi → mandami le ultime 30 righe.

### U3. [PC] Pacchetto del sito
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
```
```powershell
cd ..
```
Cosa aspettarsi: nessun messaggio.

### U4. [PC] Copia sul server
```powershell
scp ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: una riga con `100%`.

Cosa fare se va male: `Connection timed out` → rete aziendale: passa a casa o al telefono.

### U5. [Server] Sito e pulizia
Entra con `ssh eugenio`, poi:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261109f /srv/energia/sito/index.html /srv/energia/sito/edificio-obblighi.html /srv/energia/sito/edificio-geometria.html /srv/energia/sito/edificio-consumi.html
grep -c 'href="edificio-geometria.html"' /srv/energia/sito/index.html; grep -c "in-lavorazione" /srv/energia/sito/edificio-geometria.html /srv/energia/sito/edificio-fabbisogno.html
grep -c "20261109f" /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt; grep -c "Tre pagine di Edifici" /srv/energia/sito/novita.xml
rm -f ~/sito.tar.gz
exit
```
Cosa aspettarsi: quattro righe con N > 0; poi `2`, poi `edificio-geometria.html:0` e `edificio-fabbisogno.html:2`; poi due
righe con N > 0 e `1`.

Cosa fare se va male: `20261109f` a 0 → `sito.tar.gz` vecchio: rifai U3 e U4 e la prima riga.

### U6. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma.

Cosa aspettarsi: «Purge request successful» (o simile).

### U7. [Browser] Prove (Ctrl+F5)
1. Menu **Edifici**: le prime tre voci hanno la **S** (al passaggio del mouse: «sperimentale») e sono cliccabili; le altre
   hanno ancora il triangolo giallo e non si cliccano.
2. Apri **Geometria e luce naturale**: nessun avviso «Pagina in lavorazione» in cima; «Nello stesso gruppo» ha le tre
   voci come collegamenti. Stessa cosa per **Obblighi di legge** e **Consumi**.
3. Menu del telefono (finestra stretta, icona del menu): le tre voci con la parola «sperimentale».
4. **Novità**: in cima «Tre pagine di Edifici, sperimentali».

Cosa fare se va male: menu vecchio → U6 di nuovo e Ctrl+F5; altro → screenshot.

### U8. [PC] Commit, push e release `v2026.11.09f`
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
git commit -m "09/11/2026 f: Obblighi di legge, Geometria e luce naturale e Consumi di nuovo accessibili come sperimentali; sito ?v=20261109f; procedura AGGIORNAMENTO_2026-11-09f"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_f.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.09f --target main --title "EuGEnio 9 novembre 2026 (f) – tre pagine di Edifici sperimentali" --notes-file ..\note_release_f.md
```
Cosa aspettarsi: il terzo comando **non stampa nulla**; il push finisce con `… main -> main`; la release stampa
`https://github.com/StatoCritico/eugenio/releases/tag/v2026.11.09f`.

Cosa fare se va male: righe dal terzo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`; senza `gh`: GitHub → Releases → Draft a new release, tag `v2026.11.09f`,
titolo come sopra, testo di `..\note_release_f.md`.
