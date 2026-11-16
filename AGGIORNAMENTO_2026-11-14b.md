# Aggiornamento del 14–15/11/2026 (b) – Trattamento aria, Esempi, Contributi, scelta degli anni

**Seconda pubblicazione del 14/11**, sopra quella di «Newsletter e avvisi» (`AGGIORNAMENTO_2026-11-14.md`, sito
`?v=20261114a`, release `v2026.11.14`). Nuovo gruppo di menu **Trattamento aria › Psicrometria** con quattro pagine
sperimentali e il foglio Excel, scelta degli anni nelle pagine del clima, pagine **Esempi** e **Contributi**, archivio
orario di temperatura e umidità dal 1940 (da scaricare sul server). Sito **`?v=20261114b`**, release **`v2026.11.14b`**.

Il lavoro è nato in parallelo a «Newsletter e avvisi» (tutte e due dal commit `e6d1082` dell'11/11) ed è stato messo
**sopra** quel lavoro: si consegna come patch `eugenio_2026-11-14b.patch` da applicare dopo il commit della
`v2026.11.14`. Nei file in comune ci sono tutte e due le cose: menu (Trattamento aria, Esempi, Contributi **e** «Newsletter
e avvisi» in Clima e meteo, senza più «Iscriviti»), `stile.css`, `app.py` (i due router), `worker.py` (i lavori `psicro`,
`settimanale` e `avvisi`), `protezione.py` (i limiti `email_link`, `email_pref` e `psicro`), `config.py`, `.env.example`,
F.A.Q. (i due gruppi di domande), `novita.toml` (la voce del 14/11 di Newsletter e avvisi resta, sopra c'è la voce nuova
del 15/11 con la versione `20261114b`), `EUGENIO_PER_AGENTI.md` (due copie uguali), `llms.txt`, README.

## Cosa cambia

**Decisioni di Paolo del 14/11/2026 (Trattamento aria)**
1. Nuovo gruppo di menu **«Trattamento aria»** tra Edifici e Cogenerazione, con il sottotitolo **«Psicrometria»** e quattro
   pagine sperimentali (S): **Trasformazioni (UTA)**, **Ore di funzionamento**, **Carichi latenti**, **Free cooling e
   recupero** (la quarta scelta da Paolo).
2. Scelta della serie ovunque: **ultimo anno · (2) · 5 · 10 · 20 · tutta la serie**. Archivio orario leggero, solo
   temperatura e punto di rugiada → UR, **dal 1940** (ERA5 dal 1940, ERA5-Land dal 1950), ~9 GB per tutta Italia.
3. Condizioni di progetto = **statistiche della serie scelta**, livello predefinito **99 % in inverno, 1 % in estate**,
   scelte rapide 99,6 · 99 · 95 % (0,4 · 1 · 5 %) più un campo libero, modificabile dall'utente; i valori di T e UR che ne
   escono si possono correggere a mano.
4. Ore di funzionamento, gruppi predefiniti: **G1 estate 5 anni, G2 inverno 5 anni, G3 estate 20 anni, G4 inverno 20
   anni**; diagramma Psicrometrico come vista predefinita.
5. Carichi latenti, predefiniti: **26 °C/50 % d'estate (UR massima), 20 °C/40 % d'inverno (UR minima, umidificazione a
   vapore), 10 anni**.
6. Colori: **ESTATE blu, INVERNO rosso, linee spesse** (come nel foglio Excel v2.1). Il foglio **psicro_UTA.xlsx** si
   scarica da Trasformazioni (UTA), vuoto o già compilato con i dati della pagina; il generatore è nella fase 14.
7. Legge 10 continua a usare l'**archivio giornaliero corretto** (servono irradiazione e vento): le stagioni più vecchie
   **non** si prendono dall'archivio psicrometrico.

**Decisioni di Paolo del 14–15/11/2026 (pagine e risposte alle domande)**
8. Pagina **Contributi** tra le «Altre pagine», prima di Contattaci: come contribuire (discussione generale sul forum di
   Edilclima, confronti dei dati climatici, Contattaci) e **ringraziamenti** a chi contribuisce, per ora senza nomi, con
   la frase (15/11 sera): «In questa pagina verranno ringraziati coloro che hanno contribuito allo sviluppo del sito.»
9. **Esempi** sta tra le **«Altre pagine»** (riga in alto e menu del telefono), **dopo Novità e prima di Contributi**:
   Come funziona · F.A.Q. · Sitografia · Mirror · Novità · Esempi · Contributi · Contattaci (15/11 sera; prima era
   l'ultima voce del menu dei servizi, senza tendina). Casi d'uso concreti per ogni pagina disponibile, **raggruppati come i gruppi del
   menu**; le pagine in lavorazione e GME solo come «in arrivo». Ha anche gli esempi di Clima e meteo › Newsletter e
   avvisi, arrivata con la release `v2026.11.14`.
10. Foglio Excel `psicro_UTA.xlsx`: ambiente invernale predefinito **20 °C / 40 %** (prima 50 %), come le pagine.
11. Preset invernale di Trasformazioni (UTA) **invariato**.
12. Barra dei servizi su **due righe** quando non ci sta: **approvato da Paolo** (15/11 sera). Con sette gruppi, senza
    «Iscriviti» e senza «Esempi» (passato alle Altre pagine), nelle prove del 15/11 sera la riga resta una fino a
    **~1.005 px** e va a capo sotto, senza scorrimento orizzontale; la riga delle «Altre pagine» in alto sta su una riga
    da 861 px in su (sotto le voci sono nel pulsante Menu).

**Sito**
- Quattro pagine nuove `aria-trasformazioni.html`, `aria-ore.html`, `aria-latenti.html`, `aria-freecooling.html`, con i
  moduli comuni `psicro.js` (formule ASHRAE 2017, come psychrolib), `diagramma_aria.js` (Psicrometrico/Mollier, ↗, PNG e
  SVG con legenda e fonti), `scelta_aria.js` (comune e serie, livello di progetto), `gruppi_ore.js` (gruppi di ore; «8–18»
  è scritto in chiaro: dalle 8:00 alle 17:59). Tutti i calcoli nel browser; al server va solo la richiesta della serie.
- Legge 10: stagioni «ultima · 5 · 10 · 20 · tutta la serie» (l'archivio giornaliero parte dal 2015: la pagina dice quante
  stagioni ha usato; con meno di 5 «valori indicativi»). Dati climatici: periodo «ultimo anno · 5 · 10 · 20 anni · tutta
  la serie». Cambiamento climatico: tendenza sulle ultime 5, 10, 20 stagioni o da una stagione di partenza.
- Pagine di testo nuove `esempi.html` (Esempi) e `contributi.html` (Contributi).
- Come funziona: capitolo **Trattamento aria** (`#trattamento-aria`); F.A.Q.: gruppo **Trattamento aria** (8 domande);
  Sitografia: psychrolib (MIT, solo per le prove), ASHRAE Handbook – Fundamentals 2017 cap. 1, ERA5/ERA5-Land dal 1940.

**Server**
- API: rotte nuove `GET /api/psicro/disponibilita/{istat}` e `GET /api/psicro/serie/{istat}?anni=1|2|5|10|20|0`
  (`servizio/psicro.py`, limite proprio 120 serie per IP all'ora); `/api/clima-legge10/{istat}` accetta `anni=0` (tutte) e
  `anni=1`. Finché l'archivio dal 1940 di un comune non c'è, la serie è quella oraria ICON del server (dal 14/11/2022) e la
  risposta lo dice.
- Worker: lavoro nuovo **`psicro`** ogni giorno dopo lo storico (aggiunge le ore nuove all'archivio, se la cartella c'è).
- Fase 3: comandi nuovi `scarica-psicro` e `aggiorna-psicro` (`meteo_storico/psicro.py`).
- `.env`: nessuna variabile nuova obbligatoria (predefiniti: `CARTELLA_PSICRO=/dati/psicro`, `PSICRO_ORA=120`,
  `PSICRO_S3=true`, `PSICRO_GIORNI_MAX=45`). **Caddy non cambia** (comprime già le risposte di `/api/*`).

## File toccati (rispetto alla `v2026.11.14`)

- fase 3: `meteo_storico/psicro.py` (nuovo), `meteo_storico/__main__.py`, `meteo_storico/legge10.py`, README;
- fase 4: `servizio/psicro.py` (nuovo), `servizio/app.py`, `servizio/config.py`, `servizio/worker.py`,
  `servizio/storici.py`, `servizio/protezione.py`, `.env.example`, `tests/test_psicro.py` e
  `tests/test_legge10_stagioni.py` (nuovi), `tests/test_storici.py`, README;
- fase 5: pagine e script `aria-*.html`, `aria_*.js`, `psicro.js`, `diagramma_aria.js`, `scelta_aria.js`, `gruppi_ore.js`,
  `strumenti/psicro_UTA.xlsx`, `esempi.html`, `contributi.html` (nuovi); `parti/testata.html`, `parti/testa.html`,
  `stile.css`, `aspetto.js`, `README_stile.md`, `legge10.html/js`, `dati.html/js`, `edificio-clima.html`,
  `analisi_pubbliche.js`, `metodo.html`, `faq.html`, `sitografia.html`, `novita.toml` (e `novita.html/xml`), tutte le
  pagine a `?v=20261114b`, `EUGENIO_PER_AGENTI.md` e `llms.txt`; prove nuove `tests/test_aria*.py` (7 file),
  `tests/test_scelte_serie_browser.py`, `tests/test_esempi_contributi.py`, e `test_costruisci_pagine.py`,
  `test_menu_browser.py`; README;
- fase 14 (nuova): `fase14-trattamento-aria/` (gemello Python `aria/psicro.py`, `ore.py`, `latenti.py`,
  `freecooling.py`, `trasformazioni.py`, prove, generatore del foglio con l'ambiente invernale 20 °C / 40 %);
- `README.md`, `.gitignore` (eccezione per `fase5-sito/sito/strumenti/psicro_UTA.xlsx`), `EUGENIO_PER_AGENTI.md` nella
  radice, questo file. `AGGIORNAMENTO_2026-11-14.md` (Newsletter e avvisi) **non cambia**.

## Test (15/11/2026, container, sopra la `v2026.11.14`)

Fase 4 **288 passati**; fase 14 **182 passati**; fase 5 tutta, con Chromium, **193 passati, 1 saltato (manca `pvlib` nel container)** (le prove delle pagine 3D chiedono i
pacchetti `mapbox-vector-tile` e `pmtiles`, installati nel container). Foglio Excel rigenerato: **414/414** controlli
di `check_workbook.py` e **0 errori** di formula su 6.011 (LibreOffice). La fase 3 non ha prove proprie:
`meteo_storico/psicro.py` è provato da `fase4-server/tests/test_psicro.py`.

## Correzioni dopo la verifica indipendente del 14/11 sera (già dentro)

- Giorno della settimana giusto anche prima del 1970 (con «tutta la serie» le ore feriali del 1940–1969 sparivano) e ora
  legale con le **date storiche italiane** prima del 1996 (non più la regola europea di oggi per tutti gli anni).
- Al passo 1 delle pagine si vedono le **note del server** (per esempio «L'archivio dal 1940 di questo comune non è ancora
  sul server…») e le fonti usate davvero; i testi delle pagine, «Come funziona», F.A.Q. e il file per gli agenti non danno
  più per certa la serie corretta dal 2015.
- Bulbo umido vicino a 0 °C uguale a psychrolib (prima fino a 0,68 K di scarto in qualche stato).
- Free cooling: x massima predefinita esatta; Carichi latenti: le ore esattamente all'obiettivo non contano; migliaia sempre
  col punto, «−» tipografico, «nell'1 %»; etichette del diagramma sistemate; «ultimi N anni» col 29/02 come il server;
  messaggio 503 senza elenco dei comuni.

## Procedura Z0–Z16

**Prima** si fa tutta la procedura di `AGGIORNAMENTO_2026-11-14.md` (Newsletter e avvisi): commit, push e release
`v2026.11.14`, server aggiornato con `aggiorna_da_github.sh`, prove nel browser. Questa procedura parte da lì.

Tempo: circa 30 minuti per Z0–Z6; poi l'archivio dal 1940 (Z7–Z12) va da solo per 4–8 ore; Z15 il giorno dopo.
Ordine: PC (patch, commit, release) → server (script) → browser → server (archivio).

### Z0. [PC e server] La `v2026.11.14` è a posto
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git pull
```
```powershell
git status --short
```
```powershell
git tag -l "v2026.11.14*"
```
Cosa aspettarsi: `Already up to date.`; **nessuna riga** da `git status`; il tag `v2026.11.14` (e non ancora
`v2026.11.14b`). Sul server `cat ~/.eugenio_versione` stampa `v2026.11.14`.

Cosa fare se va male: righe in `git status` → fermati e mandamele (la patch va applicata su un clone pulito); manca il
tag o il server ha un'altra versione → finisci prima `AGGIORNAMENTO_2026-11-14.md`. Se in quella procedura la release
ha preso un altro nome (per esempio `v2026.11.14b`, perché `v2026.11.14` era già occupata), usa qui `v2026.11.14c` al
posto di `v2026.11.14b`.

### Z1. [PC] Applicare la patch
Scarica `eugenio_2026-11-14b.patch` (e lo zip, che resta come copia completa) in
`C:\Users\ingpa\Documents\claude\pj\statocritico\`.
```powershell
git apply --3way --whitespace=nowarn ..\eugenio_2026-11-14b.patch
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261114b" -List | Measure-Object
```
```powershell
Select-String -Path fase4-server\servizio\app.py -Pattern "include_router\((psicro|preferenze_email)\.router\)" | Measure-Object
```
```powershell
Select-String -Path fase5-sito\parti\testata.html -Pattern "dati-per-email.html|esempi.html|contributi.html|aria-ore.html" | Measure-Object
```
Cosa aspettarsi: il primo comando non stampa errori (al più righe `Applied patch … cleanly`; la patch è fatta proprio
sopra la `v2026.11.14`, quindi deve andare **pulita**); poi `Count : 1`, `Count : 2` e un numero **maggiore di 5**.

Cosa fare se va male: se `git apply` scrive `with conflicts`, `error:` o `patch does not apply` → **fermati**, mandami
l'uscita e non andare avanti (per tornare indietro: `git reset --hard` e `git clean -fd`, che tolgono solo la patch).

### Z2. [PC] Controllo, commit e push
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|\.tar\.gz$|giornaliero.*\.parquet|dati/prezzi|mercati_energia/dati|psicro/.*\.parquet|__pycache__|invii_email"
```
```powershell
git status --short | Select-String -Pattern "\.xlsx$"
```
```powershell
git commit -m "14-15/11/2026 (b): menu Trattamento aria (Trasformazioni UTA, Ore di funzionamento, Carichi latenti, Free cooling e recupero), foglio psicro_UTA.xlsx (inverno 20 °C/40 %), API /api/psicro e archivio orario dal 1940 (scarica-psicro), scelta degli anni in Legge 10, Dati climatici e Cambiamento climatico, pagine Esempi e Contributi; sito ?v=20261114b; procedura AGGIORNAMENTO_2026-11-14b"
```
```powershell
git push
```
Cosa aspettarsi: il secondo comando **non stampa nulla**; il terzo una sola riga,
`A  fase5-sito/sito/strumenti/psicro_UTA.xlsx`; il push finisce con `… main -> main`.

Cosa fare se va male: righe dal secondo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato
→ `git pull --rebase` e di nuovo `git push`.

### Z3. [PC] Release `v2026.11.14b` (stesso testo della prima voce delle Novità)
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_1114b.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
Select-String -Path ..\note_release_1114b.md -Pattern "Trattamento aria|Esempi|Contributi" | Measure-Object
```
```powershell
gh release create v2026.11.14b --target main --title "EuGEnio 15 novembre 2026 – Trattamento aria, Esempi e Contributi" --notes-file ..\note_release_1114b.md
```
Cosa aspettarsi: `Count` maggiore di 7; la release stampa `…/releases/tag/v2026.11.14b`. La release serve **prima** del
server: lo script installa solo ciò che ha una release.

### Z4. [Server] Aggiornamento da GitHub
```bash
ssh eugenio
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh --prova
```
Cosa aspettarsi, nell'ordine: `Aggiornamento da v2026.11.14 a v2026.11.14b (prova)`, `Sito della release: ?v=20261114b`,
`[prova] cp -a …` (le due copie di sicurezza), `Codice: N file nuovi o cambiati in /home/…/energia` (N circa 16: fasi
3 e 4, `novita.toml`), `Convenzioni cambiate: nessuna`, `[prova] docker compose build api; up -d --force-recreate api
worker; attesa di /api/salute`, `Sito: N file nuovi o cambiati in /srv/energia/sito` (N circa 74: tutte le pagine per
la versione, più le pagine e i moduli nuovi e `strumenti/psicro_UTA.xlsx`), `Purge di Cloudflare: [prova] Purge
Everything della zona` (o «fallo a mano»), poi `Release v2026.11.14b da installare (sito ?v=20261114b). … Procedure
cambiate, controlla i loro passi a mano: AGGIORNAMENTO_2026-11-14b.md` e `Prova finita: niente è stato cambiato.`
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa fa: copia di sicurezza di `~/energia` (in `~/energia_prima_v2026.11.14b`, tiene le ultime 3) e delle convenzioni;
codice delle fasi 3, 4, 6–10 e `novita.toml` in `~/energia` (senza cancellare: `.env` e fase 2 restano); `docker compose
build api` e `up -d --force-recreate api worker`, poi aspetta fino a 3 minuti che `/api/salute` risponda (se no torna da
solo alla copia e si ferma con `ERRORE: … Torno alla copia di sicurezza`); sito in `/srv/energia/sito` (senza toccare
`dati/indicatori` e `dati/prezzi`) con il controllo di `?v=20261114b`; indici dei prezzi rifatti; Purge di Cloudflare;
versione in `~/.eugenio_versione`.

Cosa aspettarsi: le stesse righe della prova senza `[prova]`, più `api e worker aggiornati e funzionanti`, `Sito
aggiornato a ?v=20261114b`, `Indici dei prezzi rifatti`, `Purge di Cloudflare: fatto` (o «fallo a mano»: allora
Cloudflare → `statocritico.it` → Caching → Configuration → Purge Everything), `Release v2026.11.14b installata …` e
`Controlla: docker compose ps …`. La build dura qualche minuto.

Cosa fare se va male: `ERRORE: …` → mandami le ultime 30 righe di `~/aggiorna_da_github.log`: il server è già tornato
alla `v2026.11.14`. Lo script **non** fa i passi a mano di questa procedura: sono Z5–Z15.

### Z5. [Server] Le rotte nuove rispondono
```bash
cd ~/energia/fase4-server
docker compose ps api worker
curl -s https://eugenio.statocritico.it/api/psicro/disponibilita/037006; echo
curl -s "https://eugenio.statocritico.it/api/psicro/serie/037006?anni=1" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['n'], d['dal'], d['al'], d['note'][:1])"
curl -s -o /dev/null -w "%{http_code}\n" "https://eugenio.statocritico.it/api/psicro/serie/037006?anni=3"
curl -s "https://eugenio.statocritico.it/api/clima-legge10/037006?anni=0" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['stagioni_disponibili'], d['prima_stagione_disponibile'], d['note'])"
curl -s https://eugenio.statocritico.it/api/email/opzioni | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['attivo'], d['max_comuni'])"
docker compose run --rm --no-deps -T worker python -m meteo_storico --help | grep -c scarica-psicro
ls -l /srv/energia/sito/strumenti/psicro_UTA.xlsx; grep -c 20261114b /srv/energia/sito/index.html /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt
```
Cosa aspettarsi: `api` e `worker` `Up` (api `healthy`); la riga di disponibilità con `"comune":"Bologna"`,
`"archivio":"orario_icon"`, `"dal":"2022-11-14T…"`, `quota_m` e `pressione_pa`; circa `8760 …` con la nota «L'archivio
dal 1940 di questo comune non è ancora sul server…»; `422`; il numero di stagioni (circa 11), `2015/16` e `[]`;
`True 5` (Newsletter e avvisi risponde ancora; `False 5` solo se era già così dopo la `v2026.11.14`); `1` o più; il foglio di circa 240 KB; tre righe con N > 0.

Cosa fare se va male: 404 sulle rotte `/api/psicro/…` → l'immagine è vecchia: `docker compose build api && docker compose
up -d --force-recreate api worker`; 503 → mandami la risposta (manca la serie oraria ICON del comune).

### Z6. [Browser] Menu e pagine (Ctrl+F5; F12 → Console, con «Errors» acceso)
1. Menu: **Clima e meteo** finisce con «Newsletter e avvisi»; **Trattamento aria** tra Edifici e Cogenerazione, con il
   sottotitolo **PSICROMETRIA** (non cliccabile) e le quattro voci con «S»; l'ultimo gruppo è Statistiche;
   tra le pagine in alto «… Novità · **Esempi** · **Contributi** · Contattaci»; niente «Iscriviti». Anche nel menu del
   telefono (Esempi e Contributi tra le «Altre pagine») e nella riga fissata (📌 sul gruppo Trattamento aria). Restringi
   la finestra: sotto ~1.000 px i gruppi vanno su due righe, la riga in alto resta su una riga e la pagina non scorre
   di lato.
2. `aria-trasformazioni.html`: scegli **Bologna** sulla mappa. Al passo 1, sotto «Dati dal … al …» e la fonte, le note
   del server, la prima in grassetto: «L'archivio dal 1940 di questo comune non è ancora sul server: per ora c'è solo la
   serie oraria ICON dal 14/11/2022 (circa 4 anni).»; il cursore degli anni va da «ultimo anno» a «tutta la serie». Le
   condizioni esterne si riempiono (inverno 99 %, estate 1 %); l'ambiente invernale è **20 °C / 40 %**. Scrivi a mano
   un'altra temperatura estiva: i risultati cambiano; «ripristina dal clima» la riporta. ESTATE blu, INVERNO rosso.
   «Psicrometrico» / «Mollier»; ↗ apre il riquadro; il **PNG** ha la legenda. Scarica il foglio vuoto: in Excel l'ambiente
   invernale (celle D50 e D51 del foglio UTA) è **20 °C / 40 %**; «Foglio Excel con i miei dati» si apre e ricalcola.
3. `aria-ore.html`: quattro gruppi (estate 5 anni, inverno 5 anni, estate 20 anni, inverno 20 anni); con la serie di 4
   anni la pagina avvisa che usa tutta la serie caricata per i gruppi da 5 e 20 anni. **Ore d'ufficio** in un gruppo:
   «Ore: dalle 8 alle 18, cioè ore 8:00–17:59 (10 ore al giorno…)». Zona di comfort: ore dentro e fuori. CSV.
4. `aria-latenti.html`: 26 °C/50 % d'estate, 20 °C/40 % d'inverno, 10 anni; nessun pulsante «Togli»; muovi un cursore
   di umidità: ore ed energia cambiano. CSV.
5. `aria-freecooling.html`: cambia l'economizzatore (temperatura/entalpico): cambiano ore e kWh; il PNG ha la legenda
   dei regimi con le ore l'anno.
6. **Legge 10**, Bologna: stagioni «ultima stagione · ultime 5 · ultime 10 · ultime 20 · tutta la serie»; con «ultima
   stagione» la nota «valori indicativi»; con «tutta la serie» la nota dice quante stagioni ci sono (dal 2015/16).
7. **Dati climatici**: periodo «ultimo mese · ultimo anno · 5 anni · 10 anni · 20 anni · tutta la serie».
8. **Cambiamento climatico**: «Tendenza calcolata su» con ultime 5, 10, 20 stagioni, dal 1991/92, 1981/82, 1961/62 e
   tutta la serie.
9. **Esempi** (dalla riga in alto, tra Novità e Contributi): in cima i gruppi del menu come ancore; in Clima e meteo anche «Newsletter e avvisi»; un gruppo
   «Trattamento aria» con le quattro pagine; le pagine in lavorazione solo in «In arrivo», senza collegamento.
10. **Contributi**: il collegamento alla discussione del forum di Edilclima si apre; sotto «Ringraziamenti» la frase «In
    questa pagina verranno ringraziati coloro che hanno contribuito allo sviluppo del sito.», per ora senza nomi.
11. **Newsletter e avvisi** funziona ancora: «Mandami il collegamento» con il tuo indirizzo → «Fatto…» (come Y7 di
    `AGGIORNAMENTO_2026-11-14.md`; il collegamento ricevuto apre le tue scelte).
12. **Come funziona** → capitolo «Trattamento aria»; **F.A.Q.** → gruppi «Trattamento aria» (8 domande) **e** quello
    della newsletter con gli avvisi meteo; **Sitografia** → psychrolib e ASHRAE, e ANIT, AiCARR, SIAIS, AGENAS, ANCI;
    **Novità** → in cima la voce del 15/11 «Trattamento aria…», sotto quella del 14/11 «Newsletter e avvisi…».
13. Console senza righe rosse nostre (quelle di `challenges.cloudflare.com` e `passkeys-inject.js` si ignorano).

Se tutto è a posto: `ssh eugenio "ls -d ~/energia_prima_*"` mostra le copie di sicurezza (lo script tiene le ultime 3).

### Z7. [Server] Dov'è l'archivio della fase 3? (il disco temporaneo del 28/10 può essere stato staccato)
```bash
ssh eugenio
```
```bash
cd ~/energia/fase4-server
lsblk -o NAME,SIZE,MOUNTPOINT | grep -v loop
ls -d /srv/lavoro/archivio/orario/era5_corretto && ls /srv/lavoro/archivio/orario/era5_corretto | wc -l
ls -la /srv/lavoro/archivio/comuni.parquet /srv/lavoro/archivio/celle_s3.parquet
df -h /srv/energia/dati | tail -1
```
Cosa aspettarsi, due casi:
- **Ramo A, l'archivio c'è**: `ls -d` stampa il percorso e il conteggio è vicino a **7896**; `comuni.parquet` c'è
  (`celle_s3.parquet` può mancare: va bene, lo scarico rifà le celle in ~10 minuti). → vai a **Z8-A**.
- **Ramo B, l'archivio non c'è** (`No such file or directory`, oppure `/srv/lavoro` vuoto e nessun disco da 100G nella
  riga di `lsblk`): → vai a **Z8-B**.

In tutti e due i casi nella riga di `df` servono almeno **15G** liberi (colonna Avail): l'archivio finale è ~9 GB, più
~0,5 GB di lavoro durante lo scarico. Meno di 15 GB → fermati e mandami la riga.

### Z8-A. [Server] Ramo A: prova su due comuni con l'archivio della fase 3
```bash
docker compose run --rm --no-deps -T -v /srv/lavoro/archivio:/archivio worker \
  python -m meteo_storico scarica-psicro --archivio /archivio --comuni 037006,099014 --dal 1949-01-01 --al 1950-12-31 \
  --cartella-psicro /archivio/psicro_prova
ls -la /srv/lavoro/archivio/psicro_prova
sudo rm -rf /srv/lavoro/archivio/psicro_prova
```
Cosa aspettarsi: righe `psicro gruppo 1/1 (2 comuni) anno 1949: … s` e `anno 1950`, poi un JSON con `"scritti": 2`,
`"dal": "1949-01-01T00:00Z"`, `"al": "1950-12-31T23:00Z"`; nella cartella `037006.parquet` e `099014.parquet` di circa
150–200 KB (contengono anche la serie corretta dal 2015 e ICON) e `celle.parquet`. La cartella è dell'utente 1000
(`opc`), per questo la pulizia vuole `sudo`. In questo ramo dal 2015 si usa la serie corretta verso ICON (fonte 2), come scritto in «Come
funziona». → vai a **Z9** e usa in Z10 la riga **A**.

Cosa fare se va male: errori di rete o `Permission denied` → mandami le ultime 20 righe.

### Z8-B. [Server] Ramo B: archivio di lavoro piccolo, senza la serie corretta
Senza l'archivio della fase 3 lo scarico usa l'elenco dei comuni del server e, per le ore dal 14/11/2022, la serie
oraria ICON del server. **Cosa vuol dire**: le ore dal 1940 a ~5 giorni fa sono ERA5/ERA5-Land riportati alla quota del
comune (fonte 1), dal 14/11/2022 vince ICON dove il server ce l'ha (fonte 3); **manca la correzione verso ICON per il
2015–2022** (fonte 2). Le condizioni di progetto di quegli anni possono scostarsi di qualche decimo di grado, fino a
circa 1 °C, da quelle con la serie corretta. I testi del sito lo permettono: «Come funziona» dice che la serie corretta
si usa solo dove il server ce l'ha, e al passo 1 di ogni pagina sono scritte le fonti usate davvero, periodo per periodo
(«ERA5/ERA5-Land …: N ore dal … al …»). Se un giorno l'archivio corretto torna, si può rifare lo scarico (cancellando
`/srv/energia/dati/psicro` e rifacendo Z10 nel ramo A: altre 4–8 ore).
```bash
mkdir -p $HOME/psicro_archivio/orario/icon && cp /srv/energia/dati/comuni.parquet $HOME/psicro_archivio/ && ls -ln $HOME/psicro_archivio
docker compose run --rm --no-deps -T -v $HOME/psicro_archivio:/archivio -v /srv/energia/dati/orario:/archivio/orario/icon:ro worker \
  python -m meteo_storico scarica-psicro --archivio /archivio --comuni 037006,099014 --dal 1949-01-01 --al 1950-12-31 \
  --cartella-psicro /archivio/psicro_prova
ls -la $HOME/psicro_archivio/psicro_prova
rm -rf $HOME/psicro_archivio/psicro_prova
```
Cosa aspettarsi: `ls -ln` mostra `comuni.parquet` e `orario` con `1000 1000` (se c'è un altro numero:
`sudo chown -R 1000:1000 $HOME/psicro_archivio`); poi come in Z8-A (`"scritti": 2`, due file di 25–40 KB e
`celle.parquet`); dopo la prova in `$HOME/psicro_archivio` c'è anche `celle_s3.parquet` (si riusa). → vai a **Z9** e usa
in Z10 la riga **B**.

### Z9. [Server] Cartella vera
```bash
mkdir -p /srv/energia/dati/psicro && ls -ldn /srv/energia/dati/psicro
```
Cosa aspettarsi: una riga con `1000 1000`. Se c'è un altro numero: `sudo chown 1000:1000 /srv/energia/dati/psicro`.

### Z10. [Server] Scarico di tutta Italia dal 1940, in tmux (4–8 ore, ~9 GB)
```bash
tmux new -s psicro
```
e dentro, prima
```bash
cd ~/energia/fase4-server
```
poi **una sola** delle due righe. Riga **A** (ramo A):
```bash
docker compose run --rm --no-deps -T -v /srv/lavoro/archivio:/archivio worker python -m meteo_storico scarica-psicro --archivio /archivio --regioni tutte --dal 1940-01-01 --blocco 400 --cartella-psicro /dati/psicro 2>&1 | tee -a ~/scarica_psicro.log
```
Riga **B** (ramo B):
```bash
docker compose run --rm --no-deps -T -v $HOME/psicro_archivio:/archivio -v /srv/energia/dati/orario:/archivio/orario/icon:ro worker python -m meteo_storico scarica-psicro --archivio /archivio --regioni tutte --dal 1940-01-01 --blocco 400 --cartella-psicro /dati/psicro 2>&1 | tee -a ~/scarica_psicro.log
```
Cosa aspettarsi: dopo pochi secondi `psicro: 7896 comuni, 0 già completi; periodo 1940-01-01T00:00Z → …` (la data finale
è di circa 5 giorni fa), poi una riga per anno: `psicro gruppo 1/20 (400 comuni) anno 1940: 5 s (…)`. Gli anni fino al
2021 durano pochi secondi, dal 2022 qualche decina; alla fine di ogni gruppo `psicro: unione di 400 comuni`. Staccati con
**Ctrl+B** e poi **D**: lo scarico continua da solo.

Cosa fare se va male: se si ferma (errore, riavvio del server, Ctrl+C) rilancia **la stessa riga**: i comuni già finiti e
gli anni già scritti del gruppo in corso non si rifanno. `MemoryError` o container ucciso → stessa riga con `--blocco 200`.

### Z11. [Server] Controllo durante lo scarico (quando vuoi)
```bash
tail -3 ~/scarica_psicro.log
ls /srv/energia/dati/psicro | wc -l
du -sh /srv/energia/dati/psicro
curl -s https://eugenio.statocritico.it/api/psicro/disponibilita/037006; echo
```
Cosa aspettarsi: i file salgono di ~400 per gruppo finito; lo spazio di ~0,45 GB ogni 400 comuni. L'ultima riga mostra
`"archivio":"orario_icon"` finché il gruppo di Bologna non è finito, poi `"archivio":"psicro"`, `"dal":"1940-01-01T00:00Z"`,
`"anni_completi":86`.

### Z12. [Server] Fine dello scarico
```bash
tail -12 ~/scarica_psicro.log
ls /srv/energia/dati/psicro | wc -l
du -sh /srv/energia/dati/psicro
curl -s -H "Accept-Encoding: gzip" -o /dev/null -w "%{size_download}\n" "https://eugenio.statocritico.it/api/psicro/serie/037006?anni=0"
tmux kill-session -t psicro
```
Cosa aspettarsi: in fondo al log un JSON con `"comuni": 7896`, `"scritti"` vicino a 7896 e `"gb_letti"` tra 30 e 50; i
file sono circa **7897** (uno per comune più `celle.parquet`); lo spazio **8,5–10 GB**; l'ultima riga circa
**1000000–1600000** byte (la serie dal 1940 compressa).

Cosa fare se va male: `"scritti"` molto più basso di 7896 o file mancanti → rilancia Z10 (fa solo quelli mancanti) e
mandami le ultime 30 righe del log.

### Z13. [Browser] La serie dal 1940 nelle pagine
`https://eugenio.statocritico.it/aria-ore.html` con Bologna (Ctrl+F5): al passo 1 non c'è più la nota sulla serie ICON;
con «tutta la serie» il periodo parte dal 1940 e i gruppi da 20 anni non avvisano più; nel riquadro delle note le fonti
periodo per periodo (ramo A: ERA5/ERA5-Land, poi ERA5 corretto verso ICON dal 2015, poi ICON; ramo B: ERA5/ERA5-Land, poi
ICON) e «Prima del 1950 i valori vengono da ERA5 a 0,25°…». Con «Ore d'ufficio» su tutta la serie le ore feriali ci sono
anche negli anni 1940–1969. Il diagramma con ~750.000 ore si
disegna in pochi secondi.

### Z14. [Server] Pulizia (solo ramo B)
```bash
rm -rf $HOME/psicro_archivio
exit
```

### Z15. [Server] Il giorno dopo: aggiornamento notturno
```bash
ssh eugenio
cd ~/energia/fase4-server
docker compose logs --since 24h worker | grep -i "psicrometrico" | tail -3
exit
```
Cosa aspettarsi: dopo lo storico del mattino (le 5 UTC) una riga `Archivio psicrometrico: {'comuni': 7896, 'icon': …,
's3': …, 'saltato': None}` (`icon` = comuni aggiornati dalla serie ICON del server, `s3` = gli altri). Prima che la
cartella esista la riga è `cartella /dati/psicro assente, niente da aggiornare` (normale); durante lo scarico
`'saltato': 'scarica-psicro in corso'` (normale). Un errore arriva anche per email («errore in archivio
psicrometrico»): mandami il testo. Per spegnere solo la parte da S3: `PSICRO_S3=false` nel `.env`, poi
`docker compose up -d --force-recreate worker`.

### Z16. Da ricordare
Se una notte il worker salta (server spento, errore), le ore di quella notte restano un buco: si riempie solo rilanciando
`scarica-psicro` sui comuni interessati (rifà il file intero con tutte le fonti).

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, riga di stato: «**15/11/2026 – Trattamento aria, Esempi, Contributi** (seconda pubblicazione del 14/11:
  sito `?v=20261114b`, release `v2026.11.14b`, da fare con Z0–Z16 dopo la `v2026.11.14` di Newsletter e avvisi): nuovo
  gruppo di menu «Trattamento aria › Psicrometria» con 4 pagine sperimentali (Trasformazioni (UTA), Ore di
  funzionamento, Carichi latenti, Free cooling e recupero), foglio `psicro_UTA.xlsx` (ambiente invernale 20 °C / 40 %),
  rotte `/api/psicro/…`, archivio orario T/UR dal 1940 (`scarica-psicro`, ~9 GB, da scaricare sul server), lavoro
  notturno `psicro` nel worker, scelta degli anni «ultimo anno · 5 · 10 · 20 · tutta la serie» in Legge 10, Dati
  climatici e Cambiamento climatico; pagine Esempi e Contributi (tutte e due tra le Altre pagine, prima di Contattaci); nuova fase 14
  (`fase14-trattamento-aria/`). Test (sopra la `v2026.11.14`): fase 4 288 passati, fase 14 182 passati, fase 5 193 passati, 1 saltato (manca `pvlib` nel container).»
- RIEPILOGO, decisioni di Paolo del 14–15/11/2026: le dodici della sezione «Cosa cambia» qui sopra: menu e 4 pagine,
  scelta degli anni e archivio dal 1940, livello di progetto 99 %/1 % con scelte 99,6 · 99 · 95 e campo libero e valori
  correggibili, gruppi di Ore di funzionamento, obiettivi di Carichi latenti, colori estate blu e inverno rosso, Legge 10
  sul giornaliero; pagina **Contributi** tra le Altre pagine (forum di Edilclima e la frase dei ringraziamenti); **Esempi** tra le Altre
  pagine (dopo Novità, prima di Contributi), raggruppati come i gruppi del menu; foglio Excel con ambiente invernale **20 °C / 40 %**;
  preset invernale di Trasformazioni **invariato**; barra dei servizi su due righe quando non ci sta (approvato da Paolo; nelle prove del 15/11 sera sotto ~1.000 px).
- RIEPILOGO, tabella «Struttura e stato»: nuova riga **14** `fase14-trattamento-aria/` (gemello Python delle pagine, foglio
  Excel e generatore, prove di parità con psychrolib 2.5 e con il JS).
- DA_FARE, nuova sezione «Dal 15/11/2026 (Trattamento aria, Esempi, Contributi)»:
  - [ ] **Paolo**: Z0–Z6 dopo la procedura della `v2026.11.14`, poi Z7–Z14 per l'archivio dal 1940, Z15 il giorno dopo.
  - [ ] Prova delle 4 pagine con l'API vera (finora solo con `?prova=1` e le prove dell'API).
  - [ ] Scala Δh/Δx sul bordo del Mollier solo nell'Excel: valutare se portarla nel sito.
  - [ ] Copia in memoria di `/api/psicro/serie` (16 risposte, ~100 MB con le serie dal 1940): controllare con `docker stats`.
  - [ ] Buchi dell'archivio orario dopo una notte saltata: si rilancia `scarica-psicro` sui comuni interessati.
  - [ ] Se il ramo B di Z8: rifare l'archivio con la serie corretta 2015–2022 quando l'archivio della fase 3 torna disponibile.
  - [ ] Contributi: aggiungere i nomi dei primi a cui dire grazie (con il loro consenso).
  - (chiusi il 15/11: ambiente invernale del foglio allineato a 20 °C / 40 %; preset invernale di Trasformazioni
    confermato così com'è; barra dei servizi su due righe approvata; Esempi spostato tra le Altre pagine.)
