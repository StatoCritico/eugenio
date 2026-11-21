# Aggiornamento del 21/11/2026 b – scelta «Emissioni» e `aggiorna_da_github.sh` sicuro

Release `v2026.11.21b`, versione del sito `20261121b`. Due cose:
- **sito**: in Statistiche › Produzione e consumi di elettricità la nuova scelta **«Emissioni»**
  (`elettricita.html?modo=emissioni`): anelli con la produzione per fonte in ogni regione e provincia; fattore di emissione
  medio e del termoelettrico ed energia primaria del termoelettrico per regione, zona di mercato e Italia, anno per anno dal
  2000; confronto con i valori ISPRA e con il coefficiente 0,187 tep/MWh. Dettagli: `fase15-elettricita/README.md` e
  `fase5-sito/README.md`;
- **server**: `fase4-server/aggiorna_da_github.sh` corretto dopo l'aggiornamento fallito di stamattina (sezione «Correzioni
  dello script» più sotto).

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

## Passi per questa release (v2026.11.21b)

- **AS1** – Merge della [pull request #17](https://github.com/StatoCritico/eugenio/pull/17) su GitHub.
- **AS2** – Release `v2026.11.21b` ([collegamento della release](https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.21b&target=main&title=v2026.11.21b+%E2%80%93+Elettricit%C3%A0%3A+emissioni+ed+energia+primaria+per+regione&body=%2A%2AElettricit%C3%A0%3A+emissioni+ed+energia+primaria+per+regione%2A%2A+%2821%2F11%2F2026%2C+versione+20261121b%29%0A%0AMigliorato%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+nuova+scelta+%C2%ABEmissioni%C2%BB%3A+anelli+con+la+produzione+per+fonte+in+ogni+regione+e+provincia.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+scelta+%C2%ABEmissioni%C2%BB%3A+il+fattore+di+emissione+medio+e+quello+del+termoelettrico%2C+e+l%27energia+primaria+del+termoelettrico%2C+per+regione%2C+per+zona+di+mercato+e+per+l%27Italia%2C+anno+per+anno+dal+2000.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+scelta+%C2%ABEmissioni%C2%BB%3A+il+confronto+con+i+valori+di+ISPRA+e+con+il+coefficiente+di+0%2C187+tep%2FMWh.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%3A+gli+istogrammi+e+gli+anelli+sulla+mappa+sono+grandi+il+doppio.%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0%2C+scelta+%C2%ABBurden+sharing%C2%BB%3A+colonne+verticali+come+nelle+altre+scelte%2C+con+il+rettangolo+arancione+dell%27obiettivo+2030%2C+la+linea+dell%27obiettivo+dell%27anno+e+la+linea+di+base%3B+passando+sopra+il+rettangolo%2C+anche+dove+%C3%A8+vuoto%2C+compaiono+l%27obiettivo+2030+della+regione%2C+la+percentuale+raggiunta+e+i+MW+che+mancano.+Gli+stessi+valori+sono+nel+grafico+e+nella+tabella.%0A-+Statistiche+%E2%80%BA+Carichi+elettrici%3A+si+apre+sull%27ultimo+anno+con+i+dati%2C+a+quarti+d%27ora%2C+con+le+date+gi%C3%A0+scritte%3B+se+i+dati+non+ci+sono+ancora%2C+compare+solo+il+messaggio%2C+senza+sezioni+vuote.%0A-+Novit%C3%A0%3A+accanto+alla+data+di+ogni+voce+c%27%C3%A8+il+numero+di+versione+del+sito.%0A%0APagine%3A+https%3A%2F%2Feugenio.statocritico.it%2Felettricita.html%3Fmodo%3Demissioni+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fcarichi.html)), con il testo della voce delle novità del 21/11 b.
- **AS3** – Installazione con lo **script nuovo preso dal clone** (lo script installato in `~/energia` è ancora quello
  vecchio; vedi la sezione «Quando questa correzione sarà in una release» più sotto):
  ```bash
  ssh eugenio
  git -C ~/eugenio-git fetch -q --tags --force origin
  git -C ~/eugenio-git -c advice.detachedHead=false checkout -q --force v2026.11.21b
  ~/eugenio-git/fase4-server/aggiorna_da_github.sh --prova
  ~/eugenio-git/fase4-server/aggiorna_da_github.sh --forza
  ```
  Cosa deve comparire: con `--prova` nessuna riga «ATTENZIONE: il Dockerfile copia percorsi che non ci sarebbero» e alla
  fine «Prova finita: niente è stato cambiato.»; con `--forza`, in `tail -n 30 ~/aggiorna_da_github.log`, «Copia del
  .env: …», «Copia di sicurezza: ~/energia_prima_v2026.11.21b» (o il nome della release), «Dockerfile: tutti i percorsi
  dei COPY ci sono», «api e worker aggiornati e funzionanti» e la riga finale «Release … installata»;
  `cat ~/.eugenio_versione` deve dire `v2026.11.21b`.

  Poi i file della pagina vanno ricostruiti con la grandezza Emissioni: il worker rifà i file di «Produzione e consumi di
  elettricità» solo una volta al mese, quindi lancialo a mano (l'archivio di Terna c'è già, e `GrossVsCO2Emissions` era
  già scaricato: pochi minuti):
  ```bash
  cd ~/energia/fase4-server
  docker compose run --rm worker python -m servizio.worker elettricita 2>&1 | tail -5
  grep -c '"emissioni"' /srv/energia/sito/dati/elettricita/italia.json
  ```
  Cosa deve comparire: `Statistiche di Terna: N file pubblicati in /sito/dati/elettricita` e un numero maggiore di 0.
  Finché `italia.json` non ha la parte `emissioni` il pulsante «Emissioni» resta nascosto.
- **AS4** – Controllo nel browser: https://eugenio.statocritico.it/elettricita.html?modo=emissioni (se serve, ricarica
  forzata con Ctrl+F5): pulsante «Emissioni» acceso, anelli per fonte sulle regioni (e sulle province ingrandendo),
  riquadri con il fattore di emissione medio, quello del termoelettrico e l'energia primaria, confronto con ISPRA e con
  0,187 tep/MWh; in fondo alla pagina «Novità» la voce del 21/11 b. Poi (segnalazioni di Paolo del 21–22/11):
  - in https://eugenio.statocritico.it/elettricita.html, scelta «Capacità»: istogrammi grandi il doppio di prima (barre
    alte circa 140 px nella vista dell'Italia), con la linea di base sotto ogni gruppo; anche le altre scelte e gli
    anelli di «Emissioni» sono il doppio;
  - scelta «Burden sharing»: in ogni regione una colonna verticale, rettangolo arancione vuoto = obiettivo 2030, dentro
    le rinnovabili in più dal 2020 impilate per fonte, linea nera = obiettivo dell'anno, linea di base; nessun pezzo
    sotto la base. Passando il mouse nella parte vuota del rettangolo arancione compare il riquadretto con «Obiettivo
    2030: … MW», «Raggiunto: … %» e «Mancano: … MW»; le stesse righe nel grafico a destra e la colonna «Mancano al 2030
    (MW)» nella tabella;
  - https://eugenio.statocritico.it/carichi.html: caselle Dal/al già compilate con gli ultimi 12 mesi fino all'ultimo
    giorno con i dati, «Quarti d'ora» spuntato, nell'indirizzo niente `passo=`; se i dati di Terna non ci sono ancora,
    solo il messaggio, senza titoli di sezioni vuote;
  - https://eugenio.statocritico.it/novita.html: sotto il titolo della prima voce, in piccolo, «21/11/2026 · versione
    20261121b».
- **AS5** – Da qui in poi l'aggiornamento automatico notturno funziona con lo script nuovo (installato in `~/energia` dal
  passo AS3). Controlla che la riga ci sia ancora:
  ```bash
  crontab -l | grep aggiorna_da_github
  ```
  Deve comparire la riga delle 4:40, `40 4 * * * $HOME/energia/fase4-server/aggiorna_da_github.sh --notte …`.

## Correzioni dello script `aggiorna_da_github.sh`

Correzioni dello script di aggiornamento dopo l'aggiornamento a `v2026.11.21` fallito stamattina (21/11, 9:22): rilancio
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
`v2026.11.21b`). Cosa deve comparire:
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
