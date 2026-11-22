# Aggiornamento del 22/11/2026 (pluviometria) – Clima e meteo › Dati pluviometrici

**Pronto sul ramo `claude/2026-11-22-radar`, non ancora in una release.** Non si installa finché Paolo non dà il via: il
numero di release, la versione del sito `?v=` e la voce delle Novità si scelgono in quel momento (al posto di
`<release>` qui sotto).

Cosa contiene:
- **Clima e meteo › Dati pluviometrici** (`pluviometria.html`, nuova, sperimentale, nel menu prima di Previsioni): pioggia
  misurata in Italia dal «Merging» del Dipartimento della Protezione Civile (radar corretto con i pluviometri, un dato
  ogni 30 minuti; niente radar puro), mappa animata fino a 7 giorni indietro con durata (3, 6, 12, 24 ore, 7 giorni),
  passo (3, 6, 12, 24 ore, automatico e modificabile) e secondi per passo (0,7), interruzioni della rete elettrica del
  periodo accendibili con una casella, ortofoto, valori nel punto e pioggia di ogni giorno nel comune con quella prevista
  dal sito, file CSV, Excel e PDF in **CC BY-SA 4.0**. A fini statistici, non di allerta: niente avvisi;
- **Stato della rete elettrica**: casella «Pioggia misurata (ultime 3 ore)», spenta in partenza;
- **newsletter**: «La pioggia di <mese>» nel mensile per regione e «Pioggia misurata» nel settimanale;
- **server**: lavoro `radar` del worker (thread ogni 30 minuti), rotte `/api/radar/…` e `/api/rete/interruzioni/periodo`,
  dipendenza `dpc-radar==0.3.0`, due regole di cache nel Caddyfile. Dettagli: `fase4-server/README.md` § «Dati
  pluviometrici».

## Passi (dopo il via di Paolo e la release)

- **PL1** – Cartelle (il worker gira come utente 1000):
  ```bash
  ssh eugenio
  sudo mkdir -p /srv/energia/dati/radar /srv/energia/sito/dati/radar
  sudo chown 1000:1000 /srv/energia/dati/radar /srv/energia/sito/dati/radar
  df -h /srv/energia      # servono ~3 GB liberi nei 10 anni (~250 MB l'anno di mappe + valori)
  ```
- **PL2** – Installazione della release (lo script rifà l'immagine, che ora contiene `dpc-radar`, e non tocca
  `dati/radar` del sito):
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --prova
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  docker compose -f ~/energia/fase4-server/docker-compose.yml exec api python -c "import dpc_radar; print(dpc_radar.__version__)"
  ```
  Cosa deve comparire: «Release <release> installata» e `0.3.0`.
- **PL3** – Caddyfile nuovo (cache di `indice.json` e delle immagini):
  ```bash
  cd ~/energia/fase4-server && docker compose up -d --force-recreate caddy
  ```
- **PL4** – Primo giro a mano (circa un minuto; poi il thread del worker continua ogni 30 minuti e recupera all'indietro
  fino a ~5 mesi, 60 frame per giro, circa un giorno in tutto):
  ```bash
  docker compose run --rm worker python -m servizio.worker radar 2>&1 | tail -8
  ls /srv/energia/sito/dati/radar/ /srv/energia/dati/radar/
  curl -s https://eugenio.statocritico.it/api/radar/stato | head -c 800; echo
  curl -s "https://eugenio.statocritico.it/api/radar/punto?lat=44.14&lon=12.24" | head -c 600; echo
  ```
  Atteso: `indice.json` e le cartelle `CUM3 CUM6 CUM12 CUM24` nel sito; `archivio valori ultimi stato.json` nei dati; nelle
  rotte `licenza` CC BY-SA 4.0 e i valori di Cesena (`null` = nessuna misura, non zero). Se il DPC non risponde, il giro lo
  scrive nel registro; dopo 12 ore senza giri riusciti arriva un'email all'amministratore.
- **PL5** – Controlli nel browser (Ctrl+F5):
  - https://eugenio.statocritico.it/pluviometria.html: mappa della pioggia delle ultime 24 ore, legenda in mm, tratteggio
    grigio dove non c'è misura; «Play» con durata 24 ore e passo 3 ore (automatico), con 7 giorni il passo passa a 1 giorno;
    clic su un punto: valori 3/6/12/24 ore, comune, grafico dei 30 giorni con la prevista (la prevista compare dal giorno
    dopo l'installazione); casella «Interruzioni» con le interruzioni del periodo; citazione del DPC e CC BY-SA sotto la
    mappa e nei file;
  - https://eugenio.statocritico.it/rete-elettrica.html: casella «Pioggia misurata (ultime 3 ore)» spenta; accesa, la
    pioggia sotto le cabine con la sua legenda;
  - menu Clima e meteo: «Dati pluviometrici» prima di Previsioni.
- **PL6** – Newsletter: la sezione di pioggia del settimanale compare dal primo invio dopo 7 giorni di raccolta (la
  prevista dal secondo invio); quella del mensile dal primo mese intero raccolto.

Per spegnere il lavoro senza togliere la pagina: `RADAR_ATTIVO=false` nel `.env` e `docker compose up -d worker`.
