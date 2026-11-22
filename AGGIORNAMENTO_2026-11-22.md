# Aggiornamento del 22/11/2026 – Suolo e aree agricole, ricerca per ente, periodo nell'elettricità e `aggiorna_da_github.sh` sicuro

Release `v2026.11.22`, versione del sito `20261122a` (la `v2026.11.21b` non è mai stata pubblicata: il suo contenuto è
dentro questa). Quattro cose:
- **Statistiche › Suolo e aree agricole** (`suolo.html`, nuova, sperimentale, fase 16): suolo consumato, nuovo consumo di
  suolo per causa (con la parte su suolo agricolo, stima EuGEnio) e superfici coltivate per regione, provincia e comune,
  con il periodo a due indicatori. Dati ISPRA/SNPA e ISTAT preparati dal worker (lavoro `suolo`). Dettagli:
  `fase16-suolo/README.md`, `fase4-server/README.md` § «Suolo e aree agricole», `fase5-sito/README.md`;
- **Territorio › Edifici pubblici, ricerca per ente** (`edifici-pubblici.html?modo=enti`): autocompletamento sui 9.294
  enti, fino a 8 enti con un colore ciascuno, totali e tabella; rotte `/api/immobili-pa/ente/…`. Servono le tessere e
  l'indice rifatti (passo AT5). Dettagli: `fase7-territorio/README.md`, `fase4-server/README.md`, `fase5-sito/README.md`;
- **Statistiche › Produzione e consumi di elettricità**: la scelta **«Emissioni»** (`elettricita.html?modo=emissioni`,
  anelli della produzione per fonte, fattori di emissione ed energia primaria per regione, zona e Italia dal 2000,
  confronto con ISPRA e 0,187 tep/MWh) e il **periodo a due indicatori** (flussi sommati, fattori come rapporto delle
  somme, capacità e burden sharing all'anno finale con la variazione dall'iniziale; collegamento con `inizio` e `fine`);
  più le correzioni del burden sharing e di Carichi elettrici della voce delle novità. Dettagli:
  `fase15-elettricita/README.md`, `fase5-sito/README.md`;
- **server**: `fase4-server/aggiorna_da_github.sh` sicuro, corretto dopo l'aggiornamento fallito del 21/11 mattina
  (sezione «Correzioni dello script» in fondo).

## Cosa è successo il 21/11 mattina e ripristino fatto a mano

### Cosa è successo

- Lo script della `v2026.11.20d` (quello installato in `~/energia`) non copiava `fase15-elettricita`: la build
  dell'immagine della `v2026.11.21` è fallita perché il Dockerfile copia quella cartella.
- La copia di sicurezza appena fatta (`~/energia_prima_…`) era stata cancellata dalla pulizia delle copie vecchie: `cp -a`
  conserva la data dei file, quindi la copia nuova sembrava la più vecchia.
- `torna_indietro` ha quindi cancellato `~/energia` senza avere una copia da rimettere, compreso il `.env`.
- I container sono rimasti accesi (con l'immagine e le variabili di prima): il servizio non si è fermato.

### Ripristino, passi R1–R8

Promemoria di cosa è stato fatto a mano; **non va rifatto**.

- **R1** – `~/energia` ricopiata da `~/energia_prima_v2026.11.16c`, l'ultima copia di sicurezza rimasta.
- **R2** – `.env` ricostruito dalle variabili d'ambiente del container `api` (in `~/energia/fase4-server/.env.nuovo`);
  cambiate solo `SMTP_UTENTE` e `SMTP_PASSWORD`.
- **R3** – `.env` nuovo al suo posto e copia in `~/.eugenio_env_backup/env_2026-11-21`:
  ```bash
  cd ~/energia/fase4-server; cp .env ~/env_2026-11-15_vecchio; mv .env.nuovo .env; chmod 600 .env; mkdir -p ~/.eugenio_env_backup; cp .env ~/.eugenio_env_backup/env_2026-11-21
  ```
- **R4** – codice della `v2026.11.21` dal clone `~/eugenio-git` con `rsync`:
  ```bash
  cd ~/eugenio-git; for d in fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d fase15-elettricita; do rsync -a --exclude=.env --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=uni_privato --exclude=fase2-gradi-giorno --exclude=mercati_energia/dati/ --exclude=node_modules "$d" ~/energia/; done; rsync -a .dockerignore ~/energia/; rsync -a fase5-sito/novita.toml ~/energia/fase5-sito/
  ```
- **R5** – cartella dei dati di Terna:
  ```bash
  sudo mkdir -p /srv/energia/dati/terna; sudo chown 1000:1000 …; sudo setfacl …
  ```
- **R6** – build e riavvio:
  ```bash
  cd ~/energia/fase4-server; docker compose build api; docker compose up -d --force-recreate api worker
  ```
- **R7** – sito:
  ```bash
  rsync -a --exclude=dati/indicatori/ --exclude=dati/prezzi/ --exclude=dati/elettricita/ --exclude=dati/carichi/ ~/eugenio-git/fase5-sito/sito/ /srv/energia/sito/
  ```
- **R8** – Purge di Cloudflare con `CF_ZONE_ID` e `CF_PURGE_TOKEN` letti dal `.env`, poi:
  ```bash
  echo v2026.11.21 > ~/.eugenio_versione
  ```

## Passi per questa release (v2026.11.22)

- **AT1** – Merge della [pull request #17](https://github.com/StatoCritico/eugenio/pull/17) su GitHub.
- **AT2** – Release `v2026.11.22` ([collegamento della release](https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.22&target=main&title=v2026.11.22+%E2%80%93+Suolo+e+aree+agricole%2C+ricerca+per+ente+negli+edifici+pubblici%2C+emissioni+dell%27elettricit%C3%A0&body=%2A%2ASuolo+e+aree+agricole%2C+ricerca+per+ente+negli+edifici+pubblici%2C+emissioni+dell%27elettricit%C3%A0%2A%2A+%2822%2F11%2F2026%2C+versione+20261122a%29%0A%0ANuovo%0A-+Statistiche+%E2%80%BA+Suolo+e+aree+agricole+%28sperimentale%29%3A+per+regione+e+provincia+il+suolo+consumato%2C+il+nuovo+consumo+di+suolo+per+causa+%28con+la+parte+su+suolo+agricolo%29+e+le+superfici+coltivate%2C+con+una+mappa+a+istogrammi+e+un+periodo+da+scegliere.+Scelta+una+provincia%2C+i+comuni+si+colorano+per+percentuale+di+suolo+consumato.+Dati+ISPRA%2FSNPA+e+ISTAT%3B+si+scarica+solo+l%27immagine.%0A-+Territorio+%E2%80%BA+Edifici+pubblici%2C+nuova+scheda+%C2%ABPer+ente%C2%BB%3A+scrivi+il+nome+di+un+ente+%28un+Comune%2C+un%27azienda+sanitaria%2C+un%27universit%C3%A0%E2%80%A6%29+e+vedi+sulla+mappa+tutti+i+suoi+immobili%2C+con+i+totali+e+una+tabella.+Puoi+mettere+a+confronto+fino+a+8+enti%2C+ognuno+con+il+suo+colore.%0A%0AMigliorato%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+nuova+scelta+%C2%ABEmissioni%C2%BB%3A+anelli+con+la+produzione+per+fonte+in+ogni+regione+e+provincia.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+scelta+%C2%ABEmissioni%C2%BB%3A+il+fattore+di+emissione+medio+e+quello+del+termoelettrico%2C+e+l%27energia+primaria+del+termoelettrico%2C+per+regione%2C+per+zona+di+mercato+e+per+l%27Italia%2C+anno+per+anno+dal+2000.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+scelta+%C2%ABEmissioni%C2%BB%3A+il+confronto+con+i+valori+di+ISPRA+e+con+il+coefficiente+di+0%2C187+tep%2FMWh.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%3A+gli+istogrammi+sulla+mappa+sono+pi%C3%B9+grandi%3B+con+%C2%ABEmissioni%C2%BB+gli+anelli+sono+pi%C3%B9+piccoli+e+non+si+coprono+pi%C3%B9+fra+regioni+vicine.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+scelta+%C2%ABBurden+sharing%C2%BB%3A+colonne+verticali+come+nelle+altre+scelte%2C+con+la+linea+di+base%3B+passando+sopra+una+regione+%28sul+telefono%2C+al+primo+tocco%29+compaiono+il+rettangolo+arancione+dell%27obiettivo+2030+con+la+linea+dell%27obiettivo+dell%27anno+e+un+riquadretto+con+l%27obiettivo+2030+della+regione%2C+la+percentuale+raggiunta+e+i+MW+che+mancano.+Gli+stessi+valori+sono+nel+grafico+e+nella+tabella.%0A-+Statistiche+%E2%80%BA+Carichi+elettrici%3A+si+apre+sull%27ultimo+anno+con+i+dati%2C+a+quarti+d%27ora%2C+con+le+date+gi%C3%A0+scritte%3B+se+i+dati+non+ci+sono+ancora%2C+compare+solo+il+messaggio%2C+senza+sezioni+vuote.%0A-+Novit%C3%A0%3A+accanto+alla+data+di+ogni+voce+c%27%C3%A8+il+numero+di+versione+del+sito.%0A-+Territorio+%E2%80%BA+Edifici+pubblici%3A+i+filtri+%C2%ABProvince+e+Citt%C3%A0+metropolitane%C2%BB+e+%C2%ABUniversit%C3%A0%C2%BB+ora+mostrano+i+loro+immobili+%28prima+erano+vuoti+e+finivano+in+%C2%ABAltri+enti%C2%BB%29%2C+e+c%27%C3%A8+una+voce+nuova+%C2%ABUnioni+di+Comuni+e+Comunit%C3%A0+montane%C2%BB%2C+anche+nel+filtro+della+ricerca.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%3A+si+sceglie+un+periodo+con+due+indicatori%2C+come+in+Suolo+e+aree+agricole.+Produzione%2C+carichi%2C+consumi+ed+emissioni+sono+la+somma+degli+anni+del+periodo+e+i+fattori+di+emissione+sono+ricalcolati+sul+periodo%3B+per+capacit%C3%A0+e+burden+sharing+si+vede+l%27ultimo+anno+con+la+variazione+dal+primo.+Il+collegamento+ricorda+il+periodo.%0A%0APagine%3A+https%3A%2F%2Feugenio.statocritico.it%2Fsuolo.html+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fedifici-pubblici.html%3Fmodo%3Denti+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Felettricita.html%3Fmodo%3Demissioni+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fcarichi.html)), con il testo della prima voce delle novità
  (22/11/2026, versione 20261122a).
- **AT3** – Installazione con lo **script nuovo preso dal clone** (lo script installato in `~/energia` è ancora quello
  vecchio; vedi la sezione «Quando questa correzione sarà in una release» più sotto):
  ```bash
  ssh eugenio
  git -C ~/eugenio-git fetch -q --tags --force origin
  git -C ~/eugenio-git -c advice.detachedHead=false checkout -q --force v2026.11.22
  ~/eugenio-git/fase4-server/aggiorna_da_github.sh --prova
  ~/eugenio-git/fase4-server/aggiorna_da_github.sh --forza
  ```
  Cosa deve comparire: con `--prova` nessuna riga «ATTENZIONE: il Dockerfile copia percorsi che non ci sarebbero» (il
  Dockerfile ora copia anche `fase16-suolo`) e alla fine «Prova finita: niente è stato cambiato.»; con `--forza`, in
  `tail -n 30 ~/aggiorna_da_github.log`, «Copia del .env: …», «Copia di sicurezza: ~/energia_prima_v2026.11.22»,
  «Dockerfile: tutti i percorsi dei COPY ci sono», «api e worker aggiornati e funzionanti» e la riga finale «Release …
  installata»; `cat ~/.eugenio_versione` deve dire `v2026.11.22`.

  Poi i file di «Produzione e consumi di elettricità» vanno ricostruiti con la grandezza Emissioni: il worker li rifà
  solo una volta al mese, quindi lancialo a mano (l'archivio di Terna c'è già, e `GrossVsCO2Emissions` era già
  scaricato: pochi minuti):
  ```bash
  cd ~/energia/fase4-server
  docker compose run --rm worker python -m servizio.worker elettricita 2>&1 | tail -5
  grep -c '"emissioni"' /srv/energia/sito/dati/elettricita/italia.json
  ```
  Cosa deve comparire: `Statistiche di Terna: N file pubblicati in /sito/dati/elettricita` e un numero maggiore di 0.
  Finché `italia.json` non ha la parte `emissioni` il pulsante «Emissioni» resta nascosto. Il periodo a due indicatori
  non ha bisogno di file nuovi.
- **AT4** – [Server] Primo giro del worker **`suolo`** (il lavoro mensile parte da solo il 6 del mese alle 05:30, e subito se
  `/sito/dati/suolo/italia.json` manca; farlo a mano adesso evita di aspettare):
  ```bash
  df -h /srv/energia                     # servono ~1 GB liberi (carte ~800 MB + Excel 87 MB + CSV)
  cd ~/energia/fase4-server
  docker compose run --rm worker python -m servizio.worker suolo 2>&1 | tail -8
  ls -la /srv/energia/dati/suolo /srv/energia/sito/dati/suolo | head -40
  ```
  Durata: circa **5 minuti** (scarico di ~900 MB dal groupware ISPRA e da ISTAT, lettura dell'Excel, incrocio agricolo
  di ~2 minuti). Spazio: ~900 MB in `/srv/energia/dati/suolo/` (`ispra_indicatori.xlsx`, `istat_coltivazioni.csv`,
  `istat_censimento2020.csv`, `stato_scarico.json`, `agricolo_<anno>.json`, `carte/` con due GeoTIFF, `lavoro_stato.json`)
  e ~2 MB in `/srv/energia/sito/dati/suolo/` (`italia.json` e un `RR.json` per regione). Cosa deve comparire: nessun errore e
  i file della pagina in `/srv/energia/sito/dati/suolo/`; se un controllo del costruttore non passa non si pubblica niente
  e arriva un'email all'amministratore. Variabili facoltative nel `.env` (non servono: i predefiniti vanno bene):
  `SUOLO_DATI` (archivio, predefinito `/dati/suolo`), `SUOLO_GIORNO` (6), `SUOLO_ORA` (05:30), `SUOLO_CARTE` (1 = scarica
  anche le carte raster e fa l'incrocio agricolo; 0 per saltarlo: la pagina si costruisce senza la parte «di cui su suolo
  agricolo»).
- **AT5** – [Server] **Un solo** rifacimento di tessere e indice degli Edifici pubblici con `immobili-pa-sito`: insieme i
  gruppi corretti (Province, Università, Unioni di Comuni) e gli enti per la ricerca per ente (tabelle `enti` ed
  `ente_particelle`, elenco `enti_2023_<versione>.json`, proprietà `e` nelle tessere). Circa **15–20 minuti**, **il sito
  resta acceso**: indice, PMTiles ed elenco degli enti si scrivono a parte e si sostituiscono alla fine. Va fatto **dopo**
  AT3 (che ha copiato in `~/energia/fase7-territorio` il codice nuovo).
  1. `tmux new -s immobili` (o `tmux attach -t immobili` se c'è già).
  2. `df -h /srv/energia`: servono almeno **9 GB** liberi (file di lavoro di tippecanoe ~4 GB, PMTiles nuovo ~780 MB
     accanto al vecchio, indice nuovo ~2,8 GB accanto al vecchio).
  3. Lancia, sull'host, con il venv della fase 7 e tippecanoe:
     ```bash
     cd ~/energia/fase7-territorio && . .venv/bin/activate
     python -m territorio immobili-pa-sito --dest /srv/energia/dati/immobili_pa \
         --tessere /srv/energia/dati/edifici/immobili_pa --indice /srv/energia/dati/immobili_pa
     ls -la /srv/energia/dati/edifici/immobili_pa /srv/energia/dati/immobili_pa/*.sqlite
     ```
     Alla fine un dizionario con `'pmtiles': '/edifici3d/immobili_pa/immobili_pa_2023_AAAAMMGGhhmm.pmtiles'`, `'enti':
     '/edifici3d/immobili_pa/enti_2023_AAAAMMGGhhmm.json'` e, nei `'gruppi'`, `'I': 'Unioni di Comuni e Comunità montane'`;
     nella cartella delle tessere il PMTiles nuovo, il precedente (resta fino al prossimo rifacimento), l'elenco degli enti
     e `indice.json`; nessun file `….nuovo` rimasto.
  4. Controlli dell'indice:
     ```bash
     DB=/srv/energia/dati/immobili_pa/immobili_pa_2023.sqlite
     sqlite3 $DB "SELECT gruppo, COUNT(*) FROM beni GROUP BY gruppo"
     sqlite3 $DB "SELECT COUNT(*) FROM enti"
     sqlite3 $DB "SELECT chiave, nome, n_beni FROM enti WHERE chiave IN ('3e2f550eee','5bccda1c4d','dfd3f91cd8')"
     grep -o '"enti": *"[^"]*"' /srv/energia/dati/edifici/immobili_pa/indice.json
     ```
     Atteso: gruppi A 125.061 · C 2.182.550 · E 458.139 · **I 73.157** · M 53.964 · N 28.288 · **P 64.324** · R 215.908 ·
     S 43.217 · **U 12.436** (totale 3.257.044; se mancano P, U e I il codice nuovo non è stato preso); **9294** enti;
     `3e2f550eee` Comune di Cesena **4638**, `5bccda1c4d` Azienda USL della Romagna **898**, `dfd3f91cd8` Università di
     Bologna **1134**; in `indice.json` la chiave `enti` con il nome del file nuovo.
  5. Controllo della rotta:
     ```bash
     curl -s https://eugenio.statocritico.it/api/immobili-pa/ente/3e2f550eee | head -c 600; echo
     curl -s https://eugenio.statocritico.it/api/immobili-pa/ente/3e2f550eee | grep -c 'amm_cf\|cedente'
     ```
     Atteso: `"disponibile": true` e il Comune di Cesena con i suoi totali; il secondo comando deve dire **0** (mai codici
     fiscali né soggetto cedente).
  6. Niente riavvio dell'API e niente Purge: l'indice si sostituisce con un nome fisso letto a ogni richiesta, il PMTiles e
     l'elenco degli enti hanno un nome nuovo e `indice.json` si riconvalida sempre.
- **AT6** – Controlli nel browser (se serve, ricarica forzata con Ctrl+F5):
  - https://eugenio.statocritico.it/novita.html: sotto il titolo della prima voce, in piccolo, «22/11/2026 · versione
    20261122a»;
  - https://eugenio.statocritico.it/suolo.html (dopo AT4): istogrammi per regione; le tre scelte **Suolo** (con
    l'interruttore ha / % del territorio / m² per abitante), **Consumi** (colonne per causa con la barra verde scura «di cui
    su suolo agricolo») e **Colture**; scelta una regione le province, scelta una provincia i comuni colorati; spostando
    l'indicatore iniziale per avere un periodo (per esempio 2015–2025): con Suolo e Colture il trattino nero al valore
    iniziale e la variazione nel riquadretto e nella tabella, con Consumi i valori sommati sul periodo;
  - https://eugenio.statocritico.it/edifici-pubblici.html?modo=enti&sel=3e2f550eee (dopo AT5): scheda «Per ente» aperta
    con il Comune di Cesena, 4.638 beni nei totali, pallini nel suo colore (contorni e retino ingrandendo oltre lo zoom 13),
    tabella ordinabile; scrivendo «ausl romagna» o «unibo» nel campo compaiono gli enti giusti; in «Cerca un immobile» le
    caselle degli enti con «Unioni di Comuni e Comunità montane»; spegnendo tutto tranne «Province e Città metropolitane»
    (poi «Università») compaiono degli immobili;
  - https://eugenio.statocritico.it/elettricita.html: sotto la mappa «Periodo 2025» con i due indicatori sull'ultimo
    anno; portando l'indicatore iniziale al 2015 (anche con la tastiera: Tab sull'indicatore, frecce o Inizio/Fine) il
    periodo diventa 2015–2025: con «Capacità» trattini neri sugli istogrammi e, nella tabella, la variazione in piccolo
    sotto ogni valore e la colonna «Variazione del totale dal 2015»; con «Produzione» i valori della tabella sono la somma
    degli anni («Valori del periodo 2015–2025: somma degli anni»); nel grafico a destra gli anni 2015–2025 riquadrati;
    l'indirizzo e il collegamento in fondo hanno `inizio=2015&fine=2025`; un vecchio collegamento con `anno=2020` apre il
    periodo 2020;
  - https://eugenio.statocritico.it/elettricita.html?modo=emissioni: pulsante «Emissioni» acceso, anelli per fonte sulle
    regioni (e sulle province ingrandendo) più piccoli e che non si coprono fra regioni vicine (Puglia e Basilicata
    comprese), riquadri con il fattore di emissione medio, quello del termoelettrico e l'energia primaria, confronto con
    ISPRA e con 0,187 tep/MWh; con un periodo i riquadri dicono «Valori nazionali – 2015–2025» e il confronto ISPRA «media
    pesata»;
  - in https://eugenio.statocritico.it/elettricita.html, scelta «Capacità» con un anno solo: istogrammi più grandi di prima
    (1,4 volte: barre alte al più circa 100 px nella vista dell'Italia), con la linea di base sotto ogni gruppo; la
    Lombardia non esce dal bordo alto della mappa;
  - scelta «Burden sharing»: in ogni regione solo la colonna delle rinnovabili in più dal 2020, impilata per fonte, con
    la linea di base e nessun pezzo sotto la base. Passando il mouse su una regione compaiono, solo su quella, il
    rettangolo arancione vuoto dell'obiettivo 2030 con la linea nera dell'obiettivo dell'anno e il riquadretto con
    «Obiettivo 2030: … MW», «Raggiunto: … %» e «Mancano: … MW» (anche nella parte vuota del rettangolo); togliendo il
    mouse il rettangolo sparisce. Sul telefono: primo tocco = obiettivo e riquadretto, secondo tocco = province. Le
    stesse righe nel grafico a destra e la colonna «Mancano al 2030 (MW)» nella tabella;
  - https://eugenio.statocritico.it/carichi.html: caselle Dal/al già compilate con gli ultimi 12 mesi fino all'ultimo
    giorno con i dati, «Quarti d'ora» spuntato, nell'indirizzo niente `passo=`; se i dati di Terna non ci sono ancora,
    solo il messaggio, senza titoli di sezioni vuote.
- **AT7** – Da qui in poi l'aggiornamento automatico notturno funziona con lo script nuovo (installato in `~/energia` dal
  passo AT3). Controlla che la riga ci sia ancora:
  ```bash
  crontab -l | grep aggiorna_da_github
  ```
  Deve comparire la riga delle 4:40, `40 4 * * * $HOME/energia/fase4-server/aggiorna_da_github.sh --notte …`.

## Correzioni dello script `aggiorna_da_github.sh`

Correzioni dello script di aggiornamento dopo l'aggiornamento a `v2026.11.21` fallito il 21/11 mattina (9:22): rilancio
dello script della release, ritorno indietro che non cancella mai `~/energia`, pulizia delle copie che non cancella la
copia appena fatta, controllo dei `COPY` del Dockerfile prima della build, copia del `.env` in
`~/.eugenio_env_backup/env_<data>`. Dettagli: `fase4-server/README.md`, sezione «Correzioni del 21/11/2026». Lo script
non cambia il sito.

### Quando questa correzione sarà in una release: lancia lo script nuovo direttamente dal clone

Lo script installato in `~/energia` e quello rimasto nel clone `~/eugenio-git` (al tag `v2026.11.21`) sono ancora quelli
vecchi, che non sanno rilanciare lo script della release: la prima volta lo script nuovo va preso dal clone, portato
prima sulla release che contiene la correzione. Prima di cominciare `~/energia` deve esserci, con
`fase4-server/docker-compose.yml` e `fase4-server/.env` (altrimenti lo script si ferma senza toccare niente).

```bash
ssh eugenio
git -C ~/eugenio-git fetch -q --tags --force origin
git -C ~/eugenio-git -c advice.detachedHead=false checkout -q --force <release con la correzione>
~/eugenio-git/fase4-server/aggiorna_da_github.sh --prova
~/eugenio-git/fase4-server/aggiorna_da_github.sh --forza
```

Al posto di `<release con la correzione>` metti il tag della release che contiene questa correzione (per esempio
`v2026.11.22`). Cosa deve comparire:
- con `--prova`: nessuna riga «ATTENZIONE: il Dockerfile copia percorsi che non ci sarebbero» e alla fine «Prova finita:
  niente è stato cambiato.»;
- con `--forza`: nel registro (`tail -n 30 ~/aggiorna_da_github.log`) «Copia del .env: …», «Copia di sicurezza:
  ~/energia_prima_<release>», «Dockerfile: tutti i percorsi dei COPY ci sono», «api e worker aggiornati e funzionanti» e la
  riga finale «Release … installata»;
- `ls -l ~/.eugenio_env_backup/`: i file `env_…` con permessi `-rw-------` (la copia `env_2026-11-21` fatta a mano resta
  com'è);
- `ls -ld ~/energia_prima_*`: al massimo 3 copie, compresa quella appena fatta.

Da quel momento lo script installato in `~/energia` conosce il rilancio: gli aggiornamenti successivi (anche quello
notturno delle 4:40) tornano a partire da `~/energia/fase4-server/aggiorna_da_github.sh` come prima.
