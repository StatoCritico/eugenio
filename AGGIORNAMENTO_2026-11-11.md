# Aggiornamento dell'11/11/2026 – Indici dei prezzi e primo numero della newsletter

Da fare **stasera, 11/11**: il 12 dalle 9 il worker crea da solo la bozza del primo numero sulla lista vera con il codice
e i file che trova sul server. Sito **`?v=20261111a`**, release **`v2026.11.11`**.

## Cosa cambia

**Decisioni di Paolo dell'11/11/2026**
1. PUN: niente, finché il GME non autorizza.
2. Si pubblicano i **prezzi che Intercent-ER e Consip pubblicano** nei listini delle convenzioni (PUN + spread), così come
   sono, e mai il PUN da solo.
3. Il **PFOR,t ricostruito** si pubblica (è un'elaborazione di EuGEnio); i valori TTF e dei future no.
4. Il **PSV day-ahead pubblicato da ARERA** si pubblica.
5. Nuova pagina **Statistiche › Indici dei prezzi**, prima di Costi energetici Sanità: anno in corso e anno prima,
   gennaio–dicembre, barre affiancate e tabella con la variazione; prima l'energia elettrica (Intercent-ER, Consip), poi
   il gas (listini Intercent-ER, PSV, PFOR ripetuto nei tre mesi del trimestre); il lotto si sceglie da una casella a
   discesa; gli indici anche in cima alla newsletter (Consip con il lotto dell'Emilia-Romagna) con il collegamento.
6. Nella pagina, **confronto sui consumi**: un file CSV/Excel con i consumi mensili in F1, F2, F3 dà il costo con Consip e
   i due lotti Intercent-ER, anno prima e anno in corso, in un solo grafico a 6 barre.
7. Consip gas: non trovato, non si mette.

**Newsletter** (anteprima di stasera): frase di sintesi e scarto in °C, periodo di confronto dichiarato, scarto dal
1991–2020 dal clima dal 1940, gradi giorno di tutti i giorni del mese detto nel testo, «Il tuo comune non c'è?» con il
collegamento ai Dati climatici, Novità dal numero precedente al giorno dell'invio (nel primo tutte), benvenuto nel primo
numero, Cesena tra i capoluoghi, niente Eurostat; ora in cima **gli indici dei prezzi di ottobre**. Oggetto «EuGEnio –
prezzi e freddo di ottobre 2026».

**Fonti dei listini** (lette ogni notte, solo la colonna del prezzo):
- Intercent-ER Energia elettrica 19 (2026) e 18 (2025): `listini.zip` delle pagine delle convenzioni;
- Intercent-ER Gas naturale 22: `listini_lotti_1_2_gn_22_….zip` (€/Smc, usi termici, non termici, cogenerazione);
- Consip Energia Elettrica 22: «EE22 - Corrispettivi - 1026.xlsx» da acquistinretepa.it (17 lotti). **L'indirizzo
  cambia ogni mese**: va aggiornato in `fase6-mercati/convenzioni/fonti/listini.toml` (DA_FARE).

## File toccati

- fase 6: `mercati_energia/listini.py` (nuovo), `mercati_energia/prezzi_pubblici.py` (nuovo), `notturno.py` (passo dei
  listini), `convenzioni/intercenter_ee19_2026.toml` (sezione `[listino]`), `convenzioni/fonti/listini.toml` (nuovo),
  `tests/test_prezzi_pubblici.py` (nuovo), README;
- fase 4: `servizio/worker.py` (comando `prezzi`, dopo i mercati), `servizio/notiziario.py`, `servizio/config.py`,
  `.env.example`, `tests/test_notiziario_freddo.py` (nuovo), `tests/test_notiziario_novita.py`, README;
- fase 5: `sito/indici-prezzi.html` e `sito/indici_prezzi.js` (nuovi), `sito/esempi/consumi_fasce_esempio.csv` (nuovo),
  `parti/testata.html`, `sito/stile.css`, `sito/faq.html` (`#dati-mercato`, `#indici-prezzi`), `novita.toml`, tutte le
  pagine a `?v=20261111a`, `EUGENIO_PER_AGENTI.md` e `llms.txt`, prove (`test_indici_prezzi_browser.py` nuovo,
  `test_costruisci_pagine.py`, `test_menu_browser.py` allineato anche al 09/11 f), README;
- `.gitignore` (`fase5-sito/sito/dati/prezzi/`), `EUGENIO_PER_AGENTI.md` nella radice, questo file.

## Test (11/11/2026, container)

Fase 4 **254 passed**; fase 5 con Chrome **122 passed, 1 saltato**; fase 6 **45 passed** (più 1 che fallisce anche prima:
`test_tabella_arera_2022_23_e_storico` cerca `mercati_energia/dati/psv_da_arera_2022_2023.csv`, che nel repository
pubblico non c'è; sul server c'è).

## Procedura V1–V12 (V1–V9 fatti da Paolo l'11/11 sera; da V10 in poi vale la procedura W1–W9 in fondo)

Tempo: circa 40 minuti. Ordine: PC → server → Cloudflare → browser → listmonk → PC. Da casa o dal telefono.

### V1. [PC] Zip sopra il clone
Scarica `eugenio_2026-11-11.zip` in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Measure-Object
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-11.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261111a" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: `Count : 0` prima; `Count : 1` dopo; righe `??` solo per: `AGGIORNAMENTO_2026-11-11.md`,
`fase4-server/tests/test_notiziario_freddo.py`, `fase5-sito/sito/esempi/consumi_fasce_esempio.csv`,
`fase5-sito/sito/indici-prezzi.html`, `fase5-sito/sito/indici_prezzi.js`, `fase5-sito/tests/test_indici_prezzi_browser.py`,
`fase6-mercati/convenzioni/fonti/listini.toml`, `fase6-mercati/mercati_energia/listini.py`,
`fase6-mercati/mercati_energia/prezzi_pubblici.py`, `fase6-mercati/tests/test_prezzi_pubblici.py`.

Cosa fare se va male: `Count` diverso da 0 prima → `git status --short` e mandami l'uscita; altre righe `??` → mandamele.

### V2. [PC] Pacchetti del codice e del sito
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
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori --exclude=dati/prezzi --exclude=./dati/prezzi -C sito .
```
```powershell
cd ..
```
Cosa aspettarsi: `Count : 0`.

### V3. [PC] Copia sul server
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: due righe con `100%`.

### V4. [Server] Copia di sicurezza, codice, convenzioni, rebuild
```bash
ssh eugenio
```
```bash
cd ~/energia/fase4-server
```
```bash
cp -a ~/energia ~/energia_prima_20261111
cp -a /srv/energia/dati/mercati/convenzioni ~/convenzioni_prima_20261111
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "def novita_tra\|def _tabella_prezzi" ~/energia/fase4-server/servizio/notiziario.py && ls ~/energia/fase6-mercati/mercati_energia/listini.py ~/energia/fase6-mercati/mercati_energia/prezzi_pubblici.py
cp ~/energia/fase6-mercati/convenzioni/intercenter_ee19_2026.toml /srv/energia/dati/mercati/convenzioni/
cp ~/energia/fase6-mercati/convenzioni/fonti/listini.toml /srv/energia/dati/mercati/convenzioni/fonti/
docker compose build api
docker compose up -d --force-recreate api worker
sleep 60; docker compose ps api worker
```
Cosa aspettarsi: il `grep` stampa `2`; i due `ls` mostrano i file; build senza errori; `api` e `worker` `Up` (api
`healthy`) con IMAGE `energia-api` tutti e due.

Cosa fare se va male: api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe; per
tornare indietro: `rm -rf ~/energia && mv ~/energia_prima_20261111 ~/energia && cp ~/convenzioni_prima_20261111/*.toml /srv/energia/dati/mercati/convenzioni/ && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker`.

### V5. [Server] Primi listini e file degli indici (senza aspettare la notte)
```bash
docker compose run --rm worker python -c "from servizio import config as C; from mercati_energia import listini; from mercati_energia.config import carica; c = carica(C.MERCATI_CONFIG); print(listini.aggiorna(c.cartella, c.convenzioni))"
docker compose run --rm worker python -m servizio.worker prezzi
ls -l /srv/energia/sito/dati/prezzi/indici.json
python3 -c "import json; d = json.load(open('/srv/energia/sito/dati/prezzi/indici.json')); [print(s['id'], [(i['id'], len(i['lotti'])) for i in s['indici']]) for s in d['sezioni']]"
```
Cosa aspettarsi: la prima riga stampa
`{'intercenter-ee19-2026': 60, 'intercenter-ee18-2025': 72, 'consip-ee22': 1632, 'intercenter-gn22': 34}` (numeri di
righe; più alti se i listini sono stati aggiornati); il file esiste; l'ultima riga stampa
`elettricita [('intercenter-ee19-2026', 2), ('consip-ee22', 17)]` e `gas [('intercenter-gn22', 2), ('psv-da-arera', 1), ('pfor', 1)]`.

Cosa fare se va male: una fonte con `errore: …` → mandami la riga (per Consip: copia a mano il file in
`/srv/energia/dati/mercati/listini_manuali/consip-ee22/` con un `listino.toml` che contiene `centrale = "Consip"`,
`formato = "consip"`, `titolo = "Energia Elettrica 22"`, `serie = "consip-ee22"`, e rifai V5); `Permission denied` sul
file → `sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX /srv/energia/sito/dati` e rifai la seconda riga; niente `pfor` →
mandami l'uscita di `docker compose run --rm worker python -c "from mercati_energia import pfor; from pathlib import Path; print(pfor.calcola(Path('/dati/mercati')).tail())"`.

### V6. [Server] Anteprima della newsletter senza invio
```bash
docker compose run --rm --no-deps worker python -c "import datetime as d; from servizio import notiziario as n; o,c=n.testo_mensile(2026,10,d.date(2026,11,12)); print(o); print(); print(c)"
```
Cosa aspettarsi: oggetto «EuGEnio – prezzi e freddo di ottobre 2026»; in testa «Benvenuto!», poi **Indici dei prezzi di
ottobre 2026** (Intercent-ER lotto 1 e 2 e Consip lotto 6 con F1, F2, F3; gas, PSV e PFOR) con il collegamento alla
pagina, poi «Il freddo di ottobre 2026» (10 capoluoghi con Cesena, colonna «Scarto dal 1991–2020», «Il tuo comune non
c'è?»), le Novità dal 26 ottobre all'11 novembre. Incollamela qui.

### V7. [Server] Sito e pulizia
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261111a /srv/energia/sito/index.html /srv/energia/sito/indici-prezzi.html
grep -c "confronto-consumi" /srv/energia/sito/indici_prezzi.js; ls /srv/energia/sito/esempi/consumi_fasce_esempio.csv /srv/energia/sito/dati/prezzi/indici.json
grep -c "20261111a" /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt
rm -f ~/codice.tar.gz ~/sito.tar.gz
exit
```
Cosa aspettarsi: due righe con N > 0; N > 0 e i due file (il file degli indici **non** è stato toccato dal pacchetto
del sito); due righe con N > 0.

### V8. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma.

### V9. [Browser] Prove (Ctrl+F5; F12 → Console, con «Errors» acceso)
1. Menu **Statistiche**: «Indici dei prezzi» prima di «Costi energetici Sanità».
2. `https://eugenio.statocritico.it/indici-prezzi.html`: Intercent-ER (lotto 1, fasce F1–F3, 2025 e 2026 con la
   variazione), Consip (casella con 17 lotti, «Lotto 6: Emilia Romagna» scelto), gas Intercent-ER in €/Smc, PSV e PFOR
   (nella tabella del PFOR il trimestre e «provvisorio» dove serve). Il riquadro ↗ dei grafici si apre.
3. Confronto: «file di esempio» → scaricalo e caricalo nel campo del file: «Letti 12 mesi.», un grafico con 6 barre e la
   tabella con le tre offerte; cambia il lotto Consip e la terza riga cambia. Prova anche un tuo file Excel.
4. F.A.Q. `#indici-prezzi` e `#dati-mercato`; Novità con la voce dell'11/11.
5. Console senza righe rosse nostre (quelle di `challenges.cloudflare.com` e `passkeys-inject.js` si ignorano).

### V10. [Server, poi listmonk] Bozza sulla lista Prove e invio
```bash
ssh eugenio
cd ~/energia/fase4-server
docker compose exec postgres psql -U listmonk -d listmonk -tAc "select id, name from lists"
```
Al posto di `N` metti il numero della riga «Prove»:
```bash
docker compose run --rm --no-deps -e LISTA_MENSILE=N -e NOTIZIARIO_INVIO_AUTOMATICO=false worker python -c "from servizio import notiziario as n; print(n.mensile(2026,10))"
exit
```
**[listmonk]** `https://notizie.statocritico.it/admin` → **Campagne** → l'ultima «Mensile 2026-10» → in **Liste** solo
**Prove** → **Avvia**. Rileggi l'email (PC e telefono): tabelle dei prezzi e del freddo, collegamenti.

### V11. [PC] Commit, push e release `v2026.11.11`
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|\.tar\.gz$|giornaliero.*\.parquet|dati/prezzi"
```
```powershell
git commit -m "11/11/2026: pagina Statistiche Indici dei prezzi (listini Intercent-ER e Consip, gas Intercent-ER, PSV ARERA, PFOR ricostruito, confronto sui consumi per fascia); newsletter con gli indici in cima, scarti in gradi e dal 1991-2020, novita dal numero precedente, benvenuto, Cesena, senza Eurostat; sito ?v=20261111a; procedura AGGIORNAMENTO_2026-11-11"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_1111.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.11 --target main --title "EuGEnio 11 novembre 2026 – Indici dei prezzi" --notes-file ..\note_release_1111.md
```
Cosa aspettarsi: il terzo comando **non stampa nulla**; il push finisce con `… main -> main`; la release stampa
l'indirizzo `…/releases/tag/v2026.11.11`. Se tutto è a posto:
`ssh eugenio "rm -rf ~/energia_prima_20261111 ~/convenzioni_prima_20261111"`.

### V12. Il 12/11 dopo le 9
1. Arriva l'avviso «newsletter in bozza: EuGEnio – prezzi e freddo di ottobre 2026».
2. **[listmonk]** **Campagne** → la nuova «Mensile 2026-10» sulla lista **EuGEnio mensile** → rileggila → **Invia prova**
   ai tuoi indirizzi (devono essere iscritti in listmonk) → se va bene, **Avvia**.
3. Dopo l'invio, sul server: `NOTIZIARIO_INVIO_AUTOMATICO=true` nel `.env`, poi
   `cd ~/energia/fase4-server && docker compose up -d --force-recreate worker`.


## Correzione delle 23:30 (dopo le prove V9): gas 2025, PFOR, quattro decimali – sito `?v=20261111b`

**Cosa si vedeva**: nel grafico del gas Intercent-ER il 2025 aveva solo ottobre–dicembre; il PFOR solo il IV trimestre 2026.

- **Gas**: la GN22 segue l'anno termico (da ottobre 2025); gennaio–settembre 2025 stanno nei listini della **GN21**
  (`listini_gn_21.zip`, pagina della convenzione scaduta). Aggiunta come `precedenti` della GN22 in
  `convenzioni/fonti/listini.toml` (`listini.py` ora legge i `precedenti` anche lì). Ora il 2025 è completo in tutti e due
  i lotti.
- **PFOR**: per ogni trimestre servono le quotazioni TTF del secondo mese prima del trimestre, e l'archivio del server
  le ha solo da fine agosto 2026. **Paolo ha fornito i valori trimestrali dal 2015 al IV/2026** (23:36), in €/Smc
  (verificato: III/2020 0,062715 €/Smc = 5,8612 €/MWh, il valore ARERA della delibera 241/2020): file
  `fase6-mercati/mercati_energia/dati/pfor_storico.csv` (cartella fuori da git, come gli altri dati di terzi: arriva sul
  server col pacchetto del codice dal PC), convertiti in €/MWh con il PCS 0,03852 GJ/Smc e usati **prima** del calcolo,
  che resta per i trimestri mancanti (dal I/2027). Nota della pagina e F.A.Q. `#indici-prezzi` riscritte.
- **PSV e PFOR con quattro decimali** (Paolo, 23:36): campo `decimali` per indice nel file degli indici, usato dalla pagina e
  dalla newsletter. Cambia `indici_prezzi.js`: sito **`?v=20261111b`** (la voce delle Novità dell'11/11 passa alla `b`).

Test: fase 4 **254**, fase 5 (pagine, agenti, Indici dei prezzi e menu nel browser) **49 passed, 1 saltato**, fase 6
**47** (+1 che fallisce anche prima).

## Procedura W1–W9 (da eseguire dopo V1–V9: sostituisce V10–V12)

Sul server c'è già quello di V1–V9 (codice, convenzioni, file degli indici, sito `?v=20261111a`). Questi passi
aggiungono la correzione delle 23:30 (gas 2025, PFOR storico, quattro decimali, sito `?v=20261111b`), poi la bozza di
prova, il commit unico e la release. Tempo: circa 25 minuti.

### W1. [PC] Zip sopra il clone
Lo zip `eugenio_2026-11-11b.zip` è già in `C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-11b.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261111b" -List | Measure-Object
```
```powershell
Test-Path fase6-mercati\mercati_energia\dati\pfor_storico.csv
```
Cosa aspettarsi: `Count : 1` e `True`.

Cosa fare se va male: `Count : 0` → lo zip è quello vecchio: riscaricalo dalla chat e rifai il secondo comando.

### W2. [PC] Pacchetti e copia sul server
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
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori --exclude=dati/prezzi --exclude=./dati/prezzi -C sito .
```
```powershell
cd ..
```
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: `Count : 0`; due righe con `100%`.

### W3. [Server] Codice, listini, rebuild, file degli indici, sito
```bash
ssh eugenio
```
```bash
cd ~/energia/fase4-server
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "precedenti" ~/energia/fase6-mercati/mercati_energia/listini.py && grep -c "DEC_GAS" ~/energia/fase6-mercati/mercati_energia/prezzi_pubblici.py
cp ~/energia/fase6-mercati/convenzioni/fonti/listini.toml /srv/energia/dati/mercati/convenzioni/fonti/
docker compose build api
docker compose up -d --force-recreate api worker
sleep 60; docker compose ps api worker
docker compose run --rm worker python -c "from mercati_energia import prezzi_pubblici as P; print(len(P.pfor_storico()))"
docker compose run --rm worker python -c "from servizio import config as C; from mercati_energia import listini; from mercati_energia.config import carica; c = carica(C.MERCATI_CONFIG); print(listini.aggiorna(c.cartella, c.convenzioni))"
docker compose run --rm worker python -m servizio.worker prezzi
python3 -c "import json; d = json.load(open('/srv/energia/sito/dati/prezzi/indici.json')); g = {i['id']: i for i in d['sezioni'][1]['indici']}; print(g['intercenter-gn22']['lotti']['1']['varianti']['Usi termici']['2025']); print(g['psv-da-arera']['decimali'], g['psv-da-arera']['lotti']['']['varianti']['']['2026'][9]); print(g['pfor']['lotti']['']['varianti']['']['2025'][0], g['pfor']['lotti']['']['varianti']['']['2026'][11])"
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261111b /srv/energia/sito/index.html /srv/energia/sito/indici-prezzi.html
rm -f ~/codice.tar.gz ~/sito.tar.gz
```
Cosa aspettarsi, riga per riga:
- i due `grep` stampano numeri > 0;
- `api` e `worker` `Up` (api `healthy`) con IMAGE `energia-api`;
- `48` (valori storici del PFOR);
- la riga dei listini con anche `'intercenter-gn21': 36`;
- 12 valori da `0.5613` a `0.3452`, nessun `None`;
- `4 88.3585` (decimali del PSV e valore di ottobre 2026);
- `44.8636 61.6355` (PFOR di gennaio 2025 e di dicembre 2026);
- due righe con N > 0.

Cosa fare se va male: `0` al posto di `48` → `pfor_storico.csv` non è nel pacchetto: controlla W1 (`True`) e rifai W2–W3;
api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe; per tornare a com'era dopo V9:
`rm -rf ~/energia && mv ~/energia_prima_20261111 ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker`
(la copia `~/energia_prima_20261111` è quella di prima di V4).

### W4. [Server] Anteprima della newsletter senza invio
Ancora in `~/energia/fase4-server`:
```bash
docker compose run --rm --no-deps worker python -c "import datetime as d; from servizio import notiziario as n; o,c=n.testo_mensile(2026,10,d.date(2026,11,12)); print(o); print(); print(c)"
```
Cosa aspettarsi: oggetto «EuGEnio – prezzi e freddo di ottobre 2026»; «Benvenuto!»; **Indici dei prezzi di ottobre 2026**
(Intercent-ER lotto 1 e 2 e Consip lotto 6 con F1, F2, F3; gas Intercent-ER, PSV e PFOR con quattro decimali e la
variazione su ottobre 2025); «Il freddo di ottobre 2026» con 10 capoluoghi; Novità dal 26 ottobre all'11 novembre.
Incollamela qui.

### W5. [Server, poi listmonk] Bozza sulla lista Prove e invio
```bash
docker compose exec postgres psql -U listmonk -d listmonk -tAc "select id, name from lists"
```
Al posto di `N` metti il numero della riga «Prove»:
```bash
docker compose run --rm --no-deps -e LISTA_MENSILE=N -e NOTIZIARIO_INVIO_AUTOMATICO=false worker python -c "from servizio import notiziario as n; print(n.mensile(2026,10))"
exit
```
**[listmonk]** `https://notizie.statocritico.it/admin` → **Campagne** → l'ultima «Mensile 2026-10» → in **Liste** solo
**Prove** → **Avvia**. Rileggi l'email (PC e telefono): tabelle dei prezzi e del freddo, collegamenti.

### W6. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma.

### W7. [Browser] Prove (Ctrl+F5; F12 → Console, con «Errors» acceso)
`https://eugenio.statocritico.it/indici-prezzi.html`:
1. Gas Intercent-ER: il 2025 è completo da gennaio, in tutti e due i lotti.
2. PSV e PFOR con quattro decimali; il PFOR ha il 2025 e il 2026 completi (gennaio 2025 44,8636, ottobre–dicembre 2026
   61,6355), con il trimestre sotto il mese.
3. Confronto sui consumi con il file di esempio: 6 barre e la tabella.
4. Console senza righe rosse nostre.

### W8. [PC] Commit unico, push e release `v2026.11.11`
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|\.tar\.gz$|giornaliero.*\.parquet|dati/prezzi|mercati_energia/dati"
```
```powershell
git commit -m "11/11/2026: pagina Statistiche Indici dei prezzi (listini Intercent-ER e Consip, gas Intercent-ER, PSV ARERA, PFOR, confronto sui consumi per fascia); newsletter con gli indici in cima, scarti in gradi e dal 1991-2020, novita dal numero precedente, benvenuto, Cesena, senza Eurostat; sito ?v=20261111b; procedura AGGIORNAMENTO_2026-11-11"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_1111.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.11 --target main --title "EuGEnio 11 novembre 2026 – Indici dei prezzi" --notes-file ..\note_release_1111.md
```
Cosa aspettarsi: il terzo comando **non stampa nulla** (in particolare niente `mercati_energia/dati`: `pfor_storico.csv`
resta fuori da git); il push finisce con `… main -> main`; la release stampa l'indirizzo `…/releases/tag/v2026.11.11`.
Se tutto è a posto: `ssh eugenio "rm -rf ~/energia_prima_20261111 ~/convenzioni_prima_20261111"`.

Cosa fare se va male: righe dal terzo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`.

### W9. Il 12/11 dopo le 9
1. Arriva l'avviso «newsletter in bozza: EuGEnio – prezzi e freddo di ottobre 2026».
2. **[listmonk]** **Campagne** → la nuova «Mensile 2026-10» sulla lista **EuGEnio mensile** → rileggila → **Invia prova**
   ai tuoi indirizzi (devono essere iscritti in listmonk) → se va bene, **Avvia**.
3. Dopo l'invio, sul server: `NOTIZIARIO_INVIO_AUTOMATICO=true` nel `.env`, poi
   `cd ~/energia/fase4-server && docker compose up -d --force-recreate worker`.
