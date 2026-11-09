# Fase 4 – Server di EuGEnio: eugenio.statocritico.it

**EuGEnio** (Europa + EGE) è il primo pezzo online di **Stato Critico**: gira sul server Oracle della
fase 1 ed è pubblicato tramite Cloudflare su
- `eugenio.statocritico.it` – il servizio (sito e API);
- `notizie.statocritico.it` – la **newsletter mensile automatica dei dati** (iscrizione, conferma, cancellazione).

La newsletter Substack (`statocritico.substack.com`) resta per gli articoli scritti a mano: è un'altra
cosa. Il sito principale `statocritico.it` (landing page, poi Astro su Cloudflare Pages) è nell'elenco
`DA_FARE.md`.

Container:

| Container | Cosa fa |
|---|---|
| `api` | FastAPI: riceve il CSV dei consumi, costruisce le covariate meteo e di calendario, chiama **TiRex-2** e restituisce la previsione probabilistica (quantili 10–90 %). Fa anche da proxy verso **Zornade** (la chiave resta sul server) e geolocalizza i patrimoni edilizi (ANNCSU + Zornade) |
| `worker` | previsioni meteo ogni 6 ore e storico meteo ogni giorno per i comuni delle `REGIONI_AGGIORNATE` (vuoto = tutte le `REGIONI` servite; giornaliero aggiornato a blocchi di comuni, vedi «Meteo nazionale a blocchi»); **dati di mercato ogni notte alle 02:30** (fase 6), seguiti dalla **sorveglianza delle fonti delle convenzioni** (pagine di Intercent-ER, Consip, CET; email solo quando cambia qualcosa); **newsletter mensile** il 12 del mese (dopo l'aggiornamento del 10 dei dati di e-distribuzione); verifica comuni/confini il 2 del mese; **indirizzario ANNCSU** il 12 del mese (fase 7); avvisi per email |
| `caddy` | sito statico della fase 5 e instradamento verso l'API, solo dentro la rete Docker |
| `cloudflared` | **Cloudflare Tunnel**: collega il server a Cloudflare senza aprire porte; l'HTTPS lo fa Cloudflare |
| `listmonk` + `postgres` | newsletter automatica dei dati: liste, doppia conferma, cancellazione, invii |

Un quarto container, `open-meteo`, è facoltativo (istanza Open-Meteo propria, vedi fase 3).

## Correzioni del 09/11/2026 b (`?v=20261109b`, procedura P1–P10 di `AGGIORNAMENTO_2026-11-09b.md`)

- **Ortofoto, tessere segnaposto** (`servizio/ortofoto.py`): campo `segnaposto` delle fonti (TOML della fase 10, oggi
  solo `toscana2023`). Una tessera piccola (≤ 4.000 byte) e quasi tutta bianca (≥ 95 % dei pixel sopra 235), come quella
  che la WMS della Toscana dà fuori dalla regione con la scritta «Fonte dei dati: Regione Toscana…», diventa un **PNG
  trasparente con `X-Ortofoto-Vuota: 1`**, anche se era già nella copia su disco (la copia si corregge da sola); la pagina
  passa alla fonte successiva come per la RER senza immagini. L'indirizzo pubblicato delle tessere di queste fonti ha
  `?s=1` (browser e Cloudflare non riusano le tessere bianche di prima). Test `test_segnaposto_della_toscana_diventa_vuoto`.
- **Quote dei corpi fuori dai DTM regionali** (`servizio/terreno.py`, `servizio/edifici_osm.py`): `quote_punti(...,
  ripiego=True)` dà ai punti fuori dai DTM regionali la quota del **Copernicus DEM 90 m** (`quote_copernicus`: una finestra
  sola attorno ai punti, bilineare, le stesse quote delle tessere `/api/terreno`); `con_quote` la usa per le sagome
  regionali **e per gli edifici OSM** (prima solo il DTM regionale e solo le sagome regionali). Risposta con `quote_dtm` e
  `quote_fonte` (`dtm`, `copernicus`, `dtm+copernicus`). Prima a Susegana, senza il DTM del Veneto sul server (J5 bis),
  i corpi restavano senza quota e la pagina spegneva il terreno: «c'è ma è piatta». Con `TERRENO_ATTIVO=false` niente
  quote. Test `test_quote_dei_punti_con_il_ripiego_copernicus`, `test_quote_da_copernicus_senza_il_dtm_veneto` e la
  quota nel test dei corpi OSM (Copernicus simulato, nessuna rete).

## Aggiunte dell'08/11/2026 (stessa versione `?v=20261107b`)

- **Sagome regionali al volo** (`servizio/edifici_osm.py`, `edifici3d/sagome_regionali.py` e `fonti/sagome_regionali.toml`
  copiati nell'immagine): `GET /api/edifici/osm` in **Veneto** chiede anche al WFS della Regione (`rv:edifici_veneto_feb2022`,
  bbox di 800 m attorno al centro della cella, in **EPSG:6876**) le sagome e dà a ognuna l'altezza dell'edificio OSM
  sovrapposto (poi mediana dei vicini, poi 9 m), con `sagome`, `quote_dtm`, `X-Licenza: IODL 2.0; ODbL 1.0`. Stessa
  verifica anti-robot e stessi limiti per IP del ripiego OSM; una chiamata ai WFS alla volta, almeno 1 s tra due, tetto
  `EDIFICI_REGIONALI_TETTO_ORA` (300) all'ora, timeout `EDIFICI_REGIONALI_TIMEOUT_S` (30 s); copia delle sagome per cella
  in `/dati/edifici_regionali/<regione>/` per `EDIFICI_OSM_GIORNI` giorni; WFS giù → soli edifici OSM con `avviso_sagome`;
  `EDIFICI_REGIONALI=false` spegne. Quote dei corpi dal DTM del server (`terreno.quote_punti`). Prova dal vivo dal
  container (08/11): Susegana via San Salvatore 200 in 6,7 s (396 sagome, 4 con l'altezza OSM, 449 quote dal DTM 73–110 m),
  castello di San Salvatore 52 sagome (quote 85–162 m), Conegliano centro 1.153 sagome. Test `tests/test_edifici_regionali.py`.
  Dall'08/11/2026 notte anche **Sardegna** (WFS del DBGT 10k, CC BY 4.0) e **Campania** (CTR 2020, ArcGIS REST, CC BY 4.0) da
  `fase10-edifici3d/fonti/sagome_regionali.d/` (nell'immagine dell'api): la copia tiene anche il campo dell'uso della fonte
  (`sagome_regionali.campi_tenuti`: `uso` per la Sardegna, `tipo` per la Campania) e la fonte dice «servizio ArcGIS» o «WFS».
- **Terreno da più DTM** (`servizio/terreno.py`): le schede di `CARTELLA_TERRENO` si ordinano dal passo più fine; per ogni
  tessera il primo DTM che la copre, poi gli altri per i vuoti, poi Copernicus, poi piatta; intestazione nuova
  `X-Terreno-Nome` (nome del DTM, anche dalla copia). DTM del Veneto: `dtm-server --regione veneto --crs EPSG:6876 --file
  <cartella delle tavole> --uscita /dati/terreno/dtm5_veneto_tv.tif` (passo J5 bis). Test
  `test_piu_dtm_veneto_in_6876_il_piu_dettagliato_prima` (tavole ASCII Grid sintetiche senza `.prj`).
- **Report dell'edificio**: sezione «Forma dei tetti» (scelta e corpi per fonte) dal campo `tetti`.

- **`/api/geocodifica` senza 0,0** (08/11/2026 sera, menu e ricerca): le risposte di Zornade senza coordinate vere (vuote,
  non numeriche o 0,0) si scartano; la pagina Previsioni propone il comune scritto («Comune di X») senza chiamare il server.
  Test `test_geocodifica_scarta_le_coordinate_zero` (`tests/test_protezione.py`). Serve il rebuild dell'api (già in J5).

## Correzioni del 07/11/2026 sera (`?v=20261107b`)

- **Ortofoto RER** (`servizio/ortofoto.py`, `trasparente = true` nel TOML): chiesta in PNG con `TRANSPARENT=TRUE`; tessere
  piene restituite in JPEG, con buchi in PNG trasparente (prima nere e opache dove la RER non ha dati, per esempio sulle
  colline di Brisighella agli zoom 12–14); copia in `ortofoto/rer2023_t/`, indirizzo pubblicato con `?t=1`. La cartella
  vecchia `ortofoto/rer2023/` si cancella (passo J7).
- **Caddyfile**: `archivi.json` e `*/indice.json` sotto `/edifici3d/` con `Cache-Control: no-cache` (riconvalida con ETag);
  prima un giorno di copia nel browser mostrava l'elenco vecchio degli archivi.
- **`/api/comuni`**: valori vuoti (NaN) e colonne mancanti non danno più 500.
- **Ricerca** (fase 7, `territorio/zornade.py` e `patrimonio.py`): 0,0 non è mai un punto (civico senza coordinate).
- Misura dello sfasamento (proxy degli strati): nessuno scarto introdotto dal server; test `test_colonne_e_datum_senza_scarti`.

## Come funziona la previsione

**Meteo previsto per ogni comune** (riportato al "clima" di riferimento ICON con i parametri della fase 3):

| Ore | Fonte |
|---|---|
| 0–48 | **ICON-2I** di Arpae (2,2 km) |
| 48–72 | transizione lineare ICON-2I → IFS |
| 72 h – 15 giorni | **ECMWF IFS** 0,25° – con avviso all'utente: l'incertezza cresce |

**Due modalità**:
- **breve** – passo orario, ultimi 90 giorni di consumi, orizzonte fino a 15 giorni.
  Covariate predefinite: temperatura, radiazione, umidità + festivi, sabato, ponti, ora e stagione.
- **lungo** – passo giornaliero, ultimi 3 anni, orizzonte fino a 1 anno. Covariate: temperatura media,
  gradi giorno di riscaldamento (base 20 °C) e raffrescamento (base 24 °C), radiazione + calendario.
  Oltre i 15 giorni si usa la **climatologia** (media degli stessi giorni negli anni precedenti):
  il risultato è uno scenario "anno tipo", e l'utente viene avvisato.

**Verifica**: con l'opzione `verifica` l'API nasconde l'ultimo tratto dei dati, lo prevede usando il
meteo osservato e restituisce errore medio, WAPE e copertura dell'intervallo 10–90 %.

Prove con consumi sintetici di un edificio a Bologna (CPU, 2 core):

| | WAPE | copertura 80 % | tempo |
|---|---|---|---|
| breve, 120 ore | 14 % | 58 % | ~5 s |
| lungo, 60 giorni | 6 % | 87 % | ~5 s |

Il primo avvio scarica i pesi di TiRex-2 da Hugging Face (in `dati/hf`).

**Privacy** (vedi `fase5-sito/sito/privacy.html`):
- i file caricati sono elaborati in memoria e non vengono salvati né registrati;
- l'API non scrive registri di accesso (`--no-access-log`);
- gli IP stanno solo nel registro di Caddy, `/data/log/accessi.log` nel volume `caddy-dati`, a rotazione e cancellato dopo 14 giorni (`roll_keep_for 336h`);
- il worker, una volta al mese insieme all'indirizzario ANNCSU, cancella dalla cache Zornade le risposte più vecchie di 12 mesi.

**Limiti d'uso per IP** (IPv6 contati per rete /64; dettagli e verifica anti-robot in "Protezione dell'API"):
- 20 previsioni all'ora;
- 120 ricerche Zornade all'ora;
- 2.000 edifici all'ora per il patrimonio, contati in edifici e non in richieste.
- 60 report scaricabili (pdf, xlsx, ods) all'ora;
- 600 richieste all'ora alle rotte dei dati (meteo, Legge 10, mappa, comuni, metodologia).

Il sito invia i file del patrimonio a blocchi di 40 righe, perché il tunnel Cloudflare chiude le richieste che durano più di 100 secondi.

## Installazione

Prerequisiti: fase 1 completata (Docker installato), pacchetto dati della fase 3 copiato in
`/srv/energia/dati`, sito della fase 5 in `/srv/energia/sito`.

### 1. Dominio: statocritico.it su Cloudflare, sottodomini eugenio e notizie

Il dominio è su Aruba e il piano di Stato Critico prevede già di affidarne il DNS a Cloudflare:
questo è il momento di farlo.

1. **Cloudflare** → *Add a domain* → `statocritico.it` → piano **Free**. Cloudflare importa i record
   esistenti e indica due nameserver (`xxx.ns.cloudflare.com`).
2. **Aruba** → pannello del dominio → *Gestione DNS / Nameserver* → sostituisci i nameserver di Aruba
   con i due di Cloudflare. La propagazione richiede da qualche minuto a 24 ore; Cloudflare manda
   un'email quando il dominio è attivo. (Se su Aruba ci sono caselle email del dominio, verifica che
   i record MX siano stati importati.)
3. **Cloudflare** → *Zero Trust* (gratuito fino a 50 utenti) → *Networks → Tunnels → Create a tunnel* →
   tipo **Cloudflared** → nome `eugenio` → copia il **token** (la lunga stringa dopo `--token`) nel `.env`
   come `CLOUDFLARE_TUNNEL_TOKEN`.
4. Nello stesso tunnel → *Public Hostname*, due voci (Cloudflare crea da solo i record DNS):
   - `eugenio` . `statocritico.it` → servizio **HTTP** `caddy:80`;
   - `notizie` . `statocritico.it` → servizio **HTTP** `listmonk:9000`.
5. *SSL/TLS → Edge Certificates* del dominio → **Always Use HTTPS** attivo.

Fatto il 26/10/2026: tunnel `eugenio`, route `eugenio` → `http://caddy:80` e `notizie` → `http://listmonk:9000`,
Access (applicazione `notizie`, destinazione `notizie.statocritico.it/admin`, policy riutilizzabile "solo Paolo"
con One-time PIN). Email Routing: `privacy@statocritico.it` → Gmail di Paolo, catch-all disattivato.
Il token del tunnel si mette nel `.env` senza mostrarlo: copiare tutto il comando `docker run` dalla pagina del
tunnel (pulsante di copia), poi sul server, in `fase4-server`:
```bash
read -rs -p "Incolla il comando e premi Invio: " CMD; echo
T="${CMD##*--token }"; sed -i "s|^CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=$T|" .env; unset CMD T
docker compose up -d --no-deps cloudflared
```
Attenzione: l'ID del tunnel (36 caratteri) non è il token (oltre 150 caratteri, inizia con `eyJ`). Le password di
listmonk si generano sul server: `sed -i "s|^LISTMONK_DB_PASSWORD=.*|LISTMONK_DB_PASSWORD=$(openssl rand -hex 24)|" .env`
(idem per `LISTMONK_ADMIN_PASSWORD`). Il worker resta spento finché non c'è il pacchetto meteo della fase 3:
`docker compose up -d api caddy postgres listmonk`.

Vantaggi rispetto a un record `A` verso il server: nessuna porta aperta su Oracle (anche 80 e 443
possono restare chiuse, vedi fase 1), IP del server nascosto, protezione DDoS e certificati gestiti
da Cloudflare. Quando nascerà il sito Astro su Cloudflare Pages, starà sullo stesso account e dominio.

6. *Zero Trust → Access → Applications → Add → Self-hosted*: proteggi `notizie.statocritico.it/admin`
   con un accesso tramite codice via email riservato al tuo indirizzo. Il pannello di listmonk resta
   così invisibile al pubblico; iscrizione, conferma e cancellazione restano aperte. (Le API di
   listmonk richiedono comunque il token; il worker le chiama dall'interno, senza passare da Cloudflare.)

### 2. Chiave Zornade

Registrati su <https://app.zornade.com/api> e crea una chiave gratuita (10.000 richieste/ora).
Va **solo** nel file `.env` del server.

### 3. Avvio

Permessi: i container `api` e `worker` girano come utente 1000, mentre sulle immagini Ubuntu di Oracle `ubuntu` è
l'utente 1001. Senza questo comando il worker non può scrivere in `/srv/energia/dati` (PermissionError):
```bash
sudo apt-get install -y acl
sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX /srv/energia/dati
```
La pagina del patrimonio richiede anche `comuni.parquet` nella cartella dati (viene dal pacchetto della fase 3; si può
copiare prima dall'archivio meteo del PC insieme a `comuni.json`).

Prima, i file di configurazione delle fasi 6 e 7 nella cartella dati:
```bash
mkdir -p /srv/energia/dati/mercati/convenzioni
cp ~/energia/fase6-mercati/config.example.toml /srv/energia/dati/mercati/config.toml
cp ~/energia/fase6-mercati/convenzioni/*.toml /srv/energia/dati/mercati/convenzioni/      # convenzioni compilate
cp -r ~/energia/fase6-mercati/convenzioni/fonti /srv/energia/dati/mercati/convenzioni/     # pagine sorvegliate
sed -i 's|^cartella = "archivio_mercati"|cartella = "/dati/mercati"|; s|^cartella = "convenzioni"|cartella = "/dati/mercati/convenzioni"|' /srv/energia/dati/mercati/config.toml
```

```bash
cd ~/energia/fase4-server
cp .env.example .env
nano .env                 # CLOUDFLARE_TUNNEL_TOKEN, ZORNADE_API_KEY, GME_*, SMTP_*, REGIONI, REGIONI_AGGIORNATE
chmod 600 .env
docker compose up -d --build      # la prima build richiede ~10 minuti
docker compose logs -f worker     # prime previsioni meteo (qualche minuto), poi l'indirizzario ANNCSU
```

Al primo avvio il worker scarica anche l'indirizzario ANNCSU in `/srv/energia/dati/anncsu/`
(~270 MB da scaricare, ~0,3 GB su disco, pochi minuti); per rifarlo a mano:
`docker compose exec worker python -m servizio.worker anncsu`.

Controllo: `https://eugenio.statocritico.it/api/salute` e la documentazione interattiva
`https://eugenio.statocritico.it/api/docs`.

### Meteo nazionale a blocchi e regioni aggiornate (07/11/2026)

**Regioni servite e regioni aggiornate.** `REGIONI` (`.env`) dice quali comuni il sito serve (meteo, previsioni,
Legge 10, Dati climatici, patrimonio): codici ISTAT separati da virgola, **vuoto = tutta Italia**.
`REGIONI_AGGIORNATE` dice di quali comuni il worker aggiorna **ogni giorno** previsioni (ogni `ORE_PREVISIONI` ore) e
storico (dopo `ORA_STORICO_UTC`) con l'API gratuita di Open-Meteo: **vuoto = tutte quelle servite**, cioè il
comportamento di prima (predefinito: nessun cambiamento sul server). Vale solo dentro le servite
(`meteo.comuni(aggiornati=True)`). Esempio: con l'archivio nazionale della fase 3 si può servire tutta Italia e
aggiornare ogni giorno solo l'Emilia-Romagna (`REGIONI=` e `REGIONI_AGGIORNATE=08`): gli altri comuni restano
consultabili con l'archivio com'è, senza le previsioni del giorno (la previsione dei consumi usa allora la
climatologia, come quando il meteo manca). Il worker scrive all'avvio «Meteo: regioni servite …, aggiornate ogni giorno …».

**Giornaliero a blocchi.** `giornaliero.parquet` nazionale (7.896 comuni × ~4.300 giorni ≈ 34 milioni di righe) è
**un solo file ordinato per comune e data, con un row group ogni `COMUNI_PER_BLOCCO` comuni** (100,
`meteo_storico/aggrega.py`; un comune non è mai diviso tra due row group; metadato `eugenio_formato =
giornaliero_a_blocchi_v1`). Così:
- `meteo.storico_giornaliero(istat)` legge solo il row group del comune (estremi dalle statistiche, in cache finché il
  file non cambia): ~0,1 s e pochi MB, mai il file intero; `servizio/storici.py` (Dati climatici) legge con i filtri
  per comune e data, `notiziario.py` solo i capoluoghi;
- `meteo.aggiorna_giornaliero(p, nuovi)` (usato dallo storico del worker) riscrive il file **un pezzo alla volta**:
  le righe nuove vincono su quelle con la stessa chiave `istat`+`data`, i comuni nuovi entrano al loro posto; scrive in
  `giornaliero.parquet.nuovo` e sostituisce il file solo alla fine (l'api legge sempre un file intero). Misurato sul
  container: ~650 MB di picco e ~16 s per 8,6 milioni di righe; la memoria non cresce con il file (worker: `mem_limit` 3 GB);
- **compatibilità con i file di prima** (scritti in un colpo da `esporta` o dall'aggiornamento di prima del 07/11): si
  leggono così come sono; il primo aggiornamento li converte da solo. Se il file è ordinato per comune basta una
  passata; se non lo è (`esporta` di prima seguiva l'ordine di `comuni.parquet`) la conversione legge il file una volta
  per blocco di comuni e salva i blocchi in `giornaliero.parziale/` accanto al file: se si interrompe, rilanciandola
  rifà solo i blocchi mancanti. Per farla una volta sola e sotto controllo, con il worker fermo:
  ```bash
  docker compose run --rm --no-deps worker python -m meteo_storico giornaliero-blocchi --file /dati/giornaliero.parquet --solo-verifica
  docker compose run --rm --no-deps worker python -m meteo_storico giornaliero-blocchi --file /dati/giornaliero.parquet
  ```
  (procedura con copia di sicurezza e verifica in `AGGIORNAMENTO_2026-11-07.md`, passo F12). Prove:
  `tests/test_meteo_nazionale.py` (esportazione a blocchi, lettura per comune, aggiornamento, regioni servite e
  aggiornate), `tests/test_giornaliero_blocchi.py` (file di prima ordinati e non ordinati, conversione interrotta e
  ripresa, comando) e `tests/test_scarica_risposte.py` (risposta troncata di Open-Meteo).

**Risposte troncate di Open-Meteo.** Una risposta 200 con il JSON interrotto a metà (capitato il 04/11/2026) o con meno
punti di quelli chiesti non ferma più l'aggiornamento: `meteo_storico.scarica.richiesta` la registra nel log
(«risposta troncata o incompleta … riprovo (n/4)»), aspetta 5, 10, 20, 40 s e riprova, sempre passando dal limitatore
dell'API; dopo 4 risposte troncate di fila (`MAX_TRONCATE`) o 8 tentativi in tutto (`TENTATIVI`) si arrende con un
errore (email all'amministratore dal worker).

### 4. Aggiornare

```bash
cd ~/energia && git pull
cd fase4-server && docker compose up -d --build
```

## Lavori periodici sui file del sito (fasi 8 e 9)

Il worker rifà da sé due gruppi di file statici del sito, montando in scrittura **solo**
`/srv/energia/sito/dati` (`/sito/dati` nel container; Caddy continua a leggere il sito in sola lettura):

| lavoro | quando | cosa fa | risorse |
|---|---|---|---|
| `indicatori` (fase 8) | il **5 di ogni mese** dalle 6 (`INDICATORI_GIORNO`) | riscarica CE OpenBDAP, ReportER e ISTAT e riscrive `dati/indicatori/` | ~3 minuti, pochi MB, ~70 file scaricati |
| `clima` (fase 9) | il **10 gennaio** e il **10 luglio** dalle 3 (`CLIMA_DATE`) | aggiorna la cache ERA5/ERA5-Land con l'anno in corso dai file `.om` di Open-Meteo su AWS, ricalcola tutti i comuni e riscrive `dati/clima/`, `dati/clima_stagioni.csv`, `dati/clima_sintesi.csv` | ~10 minuti; ~1,5 GB di RAM durante il calcolo; cache 630 MB in `/srv/energia/dati/clima_lavoro/` |

Perché quelle date: la stagione di riscaldamento va dal 1/7 al 30/6 (la zona F non ha limiti) e ERA5T arriva con
~5 giorni di ritardo, quindi **il 10 luglio** entrano i gradi giorno della stagione appena finita; **il 10 gennaio**
è finito l'anno solare ed entrano i mensili, le temperature di progetto e la tendenza della temperatura media.

I file nuovi si scrivono in una cartella accanto (`dati/.indicatori_nuova`, `dati/.clima_nuova`), si controllano
(indice presente, almeno il 90 % / 99 % dei file di prima) e solo allora si scambiano con quelli pubblicati con due
`rename` sullo stesso disco. Se una fonte non risponde o il controllo fallisce, restano i file di prima e
l'amministratore riceve l'email. Il calcolo del clima gira in processi separati (`scarica.py`, `calcola.py` della
fase 9 in `/app/clima_storico`), così la memoria torna libera alla fine; per questo il worker ha `mem_limit: 3g`.

**Prima installazione** (una volta, sul server):

```bash
sudo mkdir -p /srv/energia/dati/clima_lavoro
sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX -m u:ubuntu:rwX -m d:u:ubuntu:rwX /srv/energia/sito/dati /srv/energia/dati/clima_lavoro
cp ~/clima_comuni.parquet /srv/energia/dati/clima_lavoro/comuni.parquet     # dal PC (pacchetti)
cd ~/energia/fase4-server
docker compose run --rm worker python -m servizio.worker indicatori        # ~3 minuti
nohup docker compose run --rm worker python -m servizio.worker clima > ~/clima_primo.log 2>&1 &   # ~1 ora la prima volta
```

La prima esecuzione di `clima` scarica tutta la serie dal 1940 (27 GB letti da S3 in ~1 ora, gratuiti: AWS Open
Data; 630 MB su disco); le successive solo l'anno in corso. **Finché il worker è spento**, gli stessi comandi vanno
nel cron dell'host (`crontab -e`), da togliere quando si accende il worker:

```
0 6 5 * *    cd /home/ubuntu/energia/fase4-server && docker compose run --rm worker python -m servizio.worker indicatori >> /home/ubuntu/lavori.log 2>&1
0 3 10 1,7 * cd /home/ubuntu/energia/fase4-server && docker compose run --rm worker python -m servizio.worker clima >> /home/ubuntu/lavori.log 2>&1
```

Siccome il server riscrive `dati/indicatori/`, `dati/clima/` e i due CSV, **il sito non va più copiato con
`scp -r sito/*`** (riporterebbe gli indicatori del PC, più vecchi): si copia con un archivio che li esclude
(comandi nel README della fase 5).

## API

Le rotte pubbliche sono descritte per gli agenti AI in [`../EUGENIO_PER_AGENTI.md`](../EUGENIO_PER_AGENTI.md) (06/11/2026;
copia identica nel sito): **una rotta nuova, cambiata o tolta va scritta anche lì**, altrimenti `tests/test_agenti.py`
fallisce (confronta i percorsi citati con `app.openapi()` in tutti e due i sensi, escluse le rotte `/api/interno/…`).
Il Caddyfile serve dal 06/11/2026 i file `.md` del sito come `text/markdown; charset=utf-8` e `/llms.txt` come
`text/plain; charset=utf-8` (dopo la modifica: `docker compose up -d --force-recreate caddy`).

| Metodo | Percorso | Descrizione |
|---|---|---|
| GET | `/api/salute` | stato e ultimo aggiornamento delle previsioni |
| GET | `/api/protezione` | chiave pubblica di Turnstile (`null` = verifica spenta) e rotte che chiedono il gettone di sessione |
| POST | `/api/sessione` | JSON `{"token": "…"}` con il gettone Turnstile → gettone di sessione da mandare in `X-EuGEnio-Sessione` |
| GET | `/api/comuni` | comuni disponibili (ISTAT, catastale, coordinate, posizione sulla mappa) |
| GET | `/api/meteo/{istat}?modalita=breve\|lungo&giorni=N` | meteo storico e previsto del comune |
| POST | `/api/previsione` | multipart: `file` (CSV), `istat`, `modalita`, `orizzonte` (ore o giorni), `tipo` (`energia` = somma, `potenza` = media), `covariate` (es. `temperatura,radiazione`; vuoto = solo calendario), `verifica`. Dal 04/11/2026 la risposta ha anche `clima` = `{variabile: {unita, storico, previsione}}`: le variabili meteo usate dal modello negli stessi passi di `storico` e `previsione`, nell'ordine delle covariate richieste (schede della pagina e report) |
| GET | `/api/clima-previsto/{istat}?modalita=breve\|lungo&orizzonte=N&covariate=…` | (04/11/2026) «Solo clima» della pagina Previsioni: le variabili meteo scelte (stessi nomi delle covariate), ultimi passi osservati (48 ore o 30 giorni) e poi previsti, con la stessa catena di fonti della previsione (ICON-2I → IFS; previsione → climatologia), senza file né TiRex-2. Stessa forma della risposta di `/api/previsione` senza consumi (`solo_clima: true`, `storico.t`, `previsione.t`, `previsione.fonte_meteo`, `fonte_storico`, `clima`); 404 se il comune non ha meteo sul server. Limite «dati», senza verifica anti-robot (`modello.solo_clima`) |
| GET | `/api/geocodifica?q=indirizzo` | ricerca indirizzi (Zornade) |
| GET | `/api/particella?lat=&lon=` | particella catastale e comune nel punto (Zornade) |
| GET | `/api/metodologia` | metriche della correzione ERA5 per la pagina del sito |
| GET | `/api/clima-legge10/{istat}?anni=10` | dati climatici aggiornati per la Legge 10 dal clima reale del comune |
| POST | `/api/patrimonio` | CSV di edifici → particella catastale, comune, punto (max 500 righe per richiesta, 2.000 edifici l'ora per IP; il sito manda blocchi di 40); indirizzi prima con ANNCSU, poi con Zornade; CSV in UTF-8 o nella codifica di Windows; la risposta porta `fonti` da citare |
| POST | `/api/report?formato=pdf\|xlsx\|ods` | documento generico in JSON (schema in `/api/report/schema`) → file PDF, Excel o ODS; `docx` e `odt` rispondono 410 (spenti dal 28/10/2026); vedi "Report" |
| POST | `/api/report/{tipo}?formato=pdf\|xlsx\|ods` | `tipo` = `previsione`, `legge10`, `patrimonio`, `indicatori`, `valori_sedi`, `edificio` (dal 04/11/2026: pagina 3D, vedi `report_servizi.report_edificio`): il corpo è la risposta già ricevuta dal servizio → file del report |
| GET | `/api/edifici/gradi-giorno/{istat}?dal=AAAA-MM&al=AAAA-MM` | (04/11/2026, fase 10) gradi giorno mensili reali (base 20 °C e 24 °C) e temperatura media dall'archivio giornaliero, per la firma energetica; 503 finché manca l'archivio |
| GET | `/api/edifici/clima-orario/{istat}?anno=AAAA` | (04/11/2026, fase 10) un anno orario di radiazione globale e diffusa, temperatura e vento dall'archivio orario del comune, per la producibilità FV nel browser; 503 finché manca l'archivio |
| GET | `/api/ortofoto/fonti` | (04/11/2026, Fase B) fonti delle ortofoto accese, con licenza, citazione, stato («confermata», «da confermare»), zoom, riquadro e modello d'indirizzo delle tessere |
| GET | `/api/ortofoto/{fonte}/{z}/{x}/{y}.jpg` | (Fase B) tessera 256×256 in web mercator dal proxy con copia su disco (`servizio/ortofoto.py`); 404 fuori zona o per una fonte spenta, 502 se la fonte risponde con un errore, 503 se il ritmo verso la fonte è esaurito; **`?de=<m>&dn=<m>`** (08/11/2026, interi ±20, solo fonti WMS: `spostabile` in `/fonti`): ortofoto spostata di de m a est e dn m a nord rispetto alla cartografia, per le frecce sotto la mappa. Il proxy chiede alla fonte il BBOX della tessera spostato di (−de, −dn) m sul terreno in EPSG:3857 (scala locale dell'ellissoide WGS84 al centro della tessera, `bbox_spostato`; scarto < 1 cm, nessuna riproiezione); **nessuna copia su disco** (ogni passo da 1 m è un'altra serie di tessere usata da una sola persona: con la copia `ORTOFOTO_MAX_GB` si riempirebbe e la pulizia toglierebbe le tessere normali), `Cache-Control` di un giorno, `X-Ortofoto-Copia: no`, `X-Ortofoto-Spostamento`; contano ritmo e limite per IP come le altre; 422 fuori dai limiti, 400 per le fonti XYZ (Sentinel-2) |
| GET | `/api/ortofoto/strati` | (05/11/2026, seconda pubblicazione) strati sopra le ortofoto accesi (`servizio/strati.py`): tema (`particelle`, `edifici`), regioni, licenza, citazione, colore, legenda, zoom, riquadro e modello d'indirizzo delle tessere |
| GET | `/api/ortofoto/strati/{id}/{z}/{x}/{y}.png` | tessera **trasparente** 256×256 in web mercator: particelle catastali dell'Agenzia delle Entrate (WMS in EPSG:4258 riproiettato), contorni degli edifici del DBTR; solo linee, ricolorate; copia su disco, ritmo e limite come le ortofoto; 404 fuori zona o zoom, 502 se la fonte sbaglia, 503 col ritmo esaurito |
| GET | `/api/ortofoto/strati/osm_edifici/16/{x}/{y}.json` | sagome degli edifici di OpenStreetMap (ODbL) della tessera z16, in GeoJSON, dall'API Overpass, con copia su disco |
| GET | `/api/terreno/{z}/{x}/{y}.png` | (07/11/2026) **terreno della pagina 3D su richiesta** (`servizio/terreno.py`): tessera Terrarium 256×256 (zoom 8–15) letta a finestra dal COG del DTM 5 m in `/dati/terreno` (comando `dtm-server` della fase 10), altrove Copernicus DEM 90 m, se nemmeno quello tessera piatta dichiarata; copia su disco, `X-Terreno-Fonte`, Cache-Control 30 giorni; limite `terreno` solo sulle tessere da generare; 404 fuori dall'Italia o con `TERRENO_ATTIVO=false` |
| GET | `/api/terreno/fonti` | (07/11/2026) DTM disponibili sul server (riquadro, licenza, attribuzione), zoom e ripiego |
| GET | `/api/edifici/osm?lon=&lat=` | (07/11/2026) **ripiego OpenStreetMap di Modelli 3D** fuori dal DBTR (`servizio/edifici_osm.py`): edifici OSM entro 400 m dal centro della cella di 0,002° del punto, da Overpass, letti con le regole di `osm_campione` (multipoligoni con i cortili, altezza `height` → `building:levels` × 3 m → stima di 9 m), in GeoJSON WGS84 con licenza ODbL 1.0; Turnstile, limite `edifici_osm`, tetto orario per tutto il sito, copia di 30 giorni; 400 fuori dall'Italia, 404 se spento, 502/503 se Overpass non risponde |
| GET | `/api/edifici/orizzonte?lat=&lon=&h=&direzioni=72` | (Fase B) orizzonte del terreno fino a 25 km dal Copernicus DEM 90 m (file `.om` di Open-Meteo su S3, come la fase 3), angoli per direzione; copia su disco per punto (~100 m) |
| POST | `/api/edifici/pvgis` | (Fase B) `{lat, lon, aree: [{id, kwp, inclinazione, orientamento, montaggio, perdite, orizzonte}]}` → PVGIS `PVcalc` chiamato dal server con `userhorizon` e senza, per area; massimo 12 aree; risposte copiate su disco |
| GET | `/api/interno/edifici/stato` | (Fase C, **interna**) stato della pipeline notturna degli edifici (zone, tessere, ultime 30 notti, qualità, errori, disco, fonti); solo con il JWT di Cloudflare Access verificato (`servizio/interno.py`); 403 senza o con gettone non valido, 503 se `CF_ACCESS_TEAM_DOMAIN`/`CF_ACCESS_AUD` mancano nel `.env`; `X-Robots-Tag: noindex`, `no-store` |
| GET | `/api/interno/verifica` | (Fase C, interna) 204 con un JWT valido: la usa Caddy (`forward_auth`) per la pagina `/interno/edifici.html` |
| GET | `/api/analisi/stato` | (Fase E) per le analisi 5 e 7–13 del § 9 solo «disponibile» o «analisi non disponibile in questa installazione»; nulla sul contenuto o sul percorso del modulo privato (`servizio/analisi.py`) |
| POST | `/api/analisi/{id}` | (Fase E) `{edificio: {corpi: […]}, clima, ipotesi, opzioni}` → risultato del modulo privato (solo `valori`, `tabelle`, `avvisi`, `fonti`, `stima`); 503 «analisi non disponibile in questa installazione» se il modulo manca o l'analisi non è pronta, 404 per un'analisi sconosciuta, 422 per una richiesta malformata; niente viene salvato |
| GET | `/api/report/schema` | schema JSON del documento accettato da `/api/report` |
| GET | `/api/storici/catalogo` | dataset scaricabili presenti sul server (grandezze, frequenze, periodo, fonte, licenza, limiti) |
| POST | `/api/storici/stima?formato=csv\|xlsx\|ods` | JSON con i filtri → righe, colonne e dimensione stimate; se la richiesta è troppo grande, motivo e suggerimenti |
| POST | `/api/storici/estrai?formato=csv\|xlsx\|ods` | stesso JSON → file CSV (in streaming), Excel o OpenDocument (.ods) con foglio "Info" |

## Dati storici scaricabili (pagina "Dati storici")

Modulo `servizio/storici.py` (router FastAPI incluso in `app.py`). Dataset, mostrati solo se i file ci sono:

| Dataset | File letti | Frequenze |
|---|---|---|
| meteo orario ICON storico (dal 14/11/2022) | `orario/<istat>.parquet`, solo i comuni scelti | oraria, giornaliera, mensile, annuale, stagione |
| meteo giornaliero ERA5 corretto (dal 2015) | `giornaliero.parquet`, filtri per comune e data | giornaliera, mensile, annuale, stagione |
| gradi giorno (GG20, GC24) | `giornaliero.parquet` | giornaliera, mensile, annuale, stagione |
| dati climatici per la Legge 10 (mensili UNI 10349, riepilogo, GG per stagione) | `giornaliero.parquet` + `meteo_storico.legge10` | ultime N stagioni |
| elenco dei comuni con il punto meteo | `comuni.parquet` | – |
| gradi giorno, zona e altitudine del DPR 412/93 (Allegato A, valori di legge) | `dpr412.json` (copia di `fase5-sito/sito/dati/dpr412.json`, generato da `fase5-sito/costruisci_dpr412.py`) | – |
| prezzi Eurostat per le PMI | `mercati/eurostat/*.parquet` | semestrale |

Aggregazioni per giorno civile italiano: medie per temperatura, umidità, vento e nuvolosità; somme per radiazione
(kWh/m²), pioggia, neve e gradi giorno; minimo e massimo per t_min e t_max. Il periodo si allarga a mesi, anni o
stagioni (1 luglio – 30 giugno) interi; un periodo con meno della copertura scelta (predefinita 90%) resta vuoto e
il file riporta `dati_validi` e `dati_attesi`. Area: regione, provincia, elenco di comuni, tutti; facoltativo solo
capoluoghi. CSV con `;`, decimali con la virgola, UTF-8 con BOM, unità nelle intestazioni e fonti in righe `#` in
fondo; Excel e OpenDocument (.ods, dal 28/10/2026) con fogli "Dati" e "Info" (filtri, fonti, licenze, data di
estrazione, significato delle colonne). L'ODS ha lo stesso contenuto dell'Excel: numeri come numeri, date come date,
riga di intestazione ripetuta in stampa, intestazione e piè di stampa con la citazione; lo scrive `storici.py`
direttamente in XML e in streaming nello zip (senza odfpy e senza tenere il foglio in memoria). In tutti ci sono anche le voci "Licenza EuGEnio" (elaborazioni e raccolte di EuGEnio con licenza CC BY 4.0:
riuso libero, anche con modifiche, citando EuGEnio come fonte e mantenendo le fonti originali) e "Come citare"
(«Fonte: EuGEnio – eugenio.statocritico.it (dati estratti il gg/mm/aaaa)»); i testi sono `RIUSO` in `storici.py` e
`CITAZIONE` in `report.py`.

**Mai scaricabili** (le rotte rispondono 403 a qualunque richiesta che li nomini): prezzi GME (PUN, zonali, PSV,
IGI), EEX/TTF e future, PFOR, PSV ARERA, dati Zornade, indirizzario ANNCSU. Nessun dato degli utenti viene salvato.

Limiti (variabili d'ambiente): `STORICI_MAX_RIGHE_CSV` 500.000, `STORICI_MAX_RIGHE_XLSX` 300.000,
`STORICI_MAX_CELLE_XLSX` 3.000.000 (~40 s di scrittura), `STORICI_MAX_RIGHE_ODS` 300.000,
`STORICI_MAX_CELLE_ODS` 3.000.000 (~9 s per 300.000 righe × 10 colonne, ~5 MB), `STORICI_MAX_COMUNI` 2.000 comuni elencati,
`STORICI_MAX_COMUNI_LEGGE10` 400, `STORICI_COPERTURA` 90, `STORICI_ESTRAZIONI_ORA` 30 e `STORICI_STIME_ORA` 600 per
IP, `STORICI_PARALLELE` 2 estrazioni contemporanee. Tempi misurati: CSV da 500.000 righe ~8–10 s, Excel da 300.000
righe × 13 colonne ~40 s. Prove: `python -m pytest tests/test_storici.py`.

I dati di mercato (GME, TTF, PFOR) non hanno rotte pubbliche: si usano solo dentro simulazioni e
analisi (fase 6), non si possono scaricare dal sito.

Formato CSV: due colonne, data/ora e valore; separatore `;` `,` o tab; decimali con virgola o punto;
date `GG/MM/AAAA hh:mm` o `AAAA-MM-GG hh:mm`, in ora italiana.

Limiti per indirizzo IP: 20 previsioni/ora, 120 ricerche/ora, 60 report/ora, 30 download di dati storici/ora, 600
richieste/ora alle rotte dei dati. File fino a 5 MB / 200.000 righe. Previsione, patrimonio, geocodifica, particella ed
estrazione dei dati storici chiedono anche il gettone di sessione (vedi "Protezione dell'API").

## Report

**Formati offerti (decisione del 28/10/2026 sera)**: il servizio gratuito genera i report solo in **PDF** e i dati
grezzi in **Excel (.xlsx)** e **ODS** (foglio di calcolo OpenDocument); il CSV lo produce già il sito da sé. I generatori
**Word (.docx)** e **ODT** restano nel codice ma sono **spenti**: le rotte rispondono **410** con il messaggio «Il formato
… non è più disponibile: il servizio gratuito genera i report solo in PDF e i dati grezzi in Excel o ODS». L'elenco
dei formati accesi è la variabile `REPORT_FORMATI` (predefinita `pdf,xlsx,ods`; per riaccendere Word e ODT:
`REPORT_FORMATI=pdf,xlsx,ods,docx,odt` nel `.env` e `docker compose up -d api`); `report.formati_attivi()` la legge.
Le descrizioni di Word e ODT qui sotto valgono per quando si riaccendono. Il codice è in `servizio/report.py` (modello del documento e cinque generatori) e
`servizio/report_servizi.py` (report dei servizi esistenti). Le usano i pulsanti "Scarica il report" di previsione, patrimonio, Legge 10 e indicatori (`sito/report.js`).

**Report della previsione (dal 04/11/2026)**: `report_servizi.report_previsione` riceve anche il formato
(`CON_FORMATO`). Le tabelle mettono consumi (P10, P50, P90, valore reale) e **tutte le variabili meteo attive in colonne
affiancate**, nell'ordine delle opzioni della pagina (quello di `richiesta.covariate`); nel **PDF** una sezione «Grafici»
con i grafici in sequenza, prima i consumi e poi una variabile per grafico (SVG piatti disegnati dal server,
`_svg_serie`, colori fissi senza trasparenze). Con `solo_clima: true` (risposta di `/api/clima-previsto`) il documento si
chiama «Previsione del clima», file `clima_previsto_<istat>_<modalita>`, senza TiRex-2 tra le fonti. Prove:
`tests/test_solo_clima.py` (10 test: funzione, rotta, colonne affiancate in Excel, ordine dei grafici nel PDF).

**Modello del documento** (indipendente dal formato): `titolo`, `sottotitolo`, `data` (vuota = oggi),
`nome_file` (facoltativo, senza estensione), `sezioni` con `titolo` e `blocchi`, `fonti` (`testo`, `url`).
Blocchi (campo `tipo`):

| tipo | campi |
|---|---|
| `paragrafo` | `testo` |
| `elenco` | `voci`, `numerato` |
| `tabella` | `titolo`, `intestazioni`, `righe` (celle: numero, testo, sì/no, vuoto), `decimali` per colonna, `nota` |
| `chiave_valore` | `titolo`, `voci` (`chiave`, `valore`, `unita`, `decimali`) |
| `immagine` | `formato` `png` o `svg`, `dati` in base64, `didascalia`, `larghezza_cm` |
| `avvertenza` | `testo`, `livello` (`attenzione` o `info`) |

Ogni file porta l'**intestazione** "Prodotto da EuGEnio – eugenio.statocritico.it" (in Word e PDF nell'intestazione
di ogni pagina, con il collegamento al sito; in Excel nella prima riga del foglio Info e nell'intestazione di stampa di
ogni foglio) e chiude con le **fonti e attribuzioni** e le **avvertenze** complete (una volta, in fondo; in Excel nel
foglio Info). Il **piè di pagina** di ogni pagina (Word e PDF) e di stampa di ogni foglio (Excel) riporta, in carattere
piccolo, un'avvertenza breve coerente con la FAQ "I dati sono garantiti?" (`faq.html#garanzia`): servizio gratuito e
senza garanzia, dati calcolati o reperiti con sistemi automatici e verificati a campione, nessuna responsabilità per
errori nei dati, nelle previsioni o nell'uso del report; sviluppato anche con l'intelligenza artificiale, calcoli
deterministici; la licenza dei dati e dei report (CC BY 4.0, riuso citando «Fonte: EuGEnio –
eugenio.statocritico.it»); dove segnalare gli errori (`contatti.html`); più il numero di pagina ("Pagina 2 di 5").
Le avvertenze complete in fondo al report comprendono il testo della licenza (`TESTO_LICENZA`): CC BY 4.0 per il
report e i dati elaborati, obbligo di citare EuGEnio come fonte con la data del report, attribuzioni delle fonti
originali da mantenere, dati di origine soggetti alle loro licenze (Zornade: link e fonti originali, niente
rivendita dei dati grezzi), testi normativi come atti pubblici, codice AGPL-3.0, rimando a `licenza.html#dati`. I testi sono
costanti in `report.py` (`INTESTAZIONE`, `CITAZIONE`, `LICENZA_DATI`, `PIE_AVVERTENZA`, `PIE_AVVERTENZA_XLSX` – più
corta perché in Excel intestazione e piè di stampa, codici di formato compresi, non superano 255 caratteri –,
`TESTO_LICENZA`, `AVVERTENZE`). **Logo**: per ora nessuno; per aggiungerlo basta assegnare i byte di un PNG a
`LOGO_PNG` (altezza `LOGO_ALTEZZA_CM`): va a sinistra nell'intestazione di Word e PDF e in cima al foglio Info.

- **Formati italiani**: in Word e PDF 1.234,56 e 27/10/2026; le stringhe ISO di data o data/ora nelle tabelle sono
  riconosciute (quelle con fuso riportate all'ora italiana). In Excel i numeri restano numeri, con formato di
  cella, e le date diventano date; c'è un foglio per tabella più il foglio **Info** (titolo, data, testi,
  coppie chiave/valore, avvertenze, fonti). Il testo che inizia con `=` non diventa mai una formula.
- **Immagini**: PNG in Word e PDF; SVG solo nel PDF (in Word resta una nota, in Excel le immagini non entrano).
  SVG con immagini, script o riferimenti esterni sono rifiutati.
- **ODT e ODS**: [odfpy](https://github.com/eea/odfpy) 1.4.1 (Python puro, licenza Apache 2.0 o GPL 2+, dipende solo
  da defusedxml), versione fissata in `api/requirements.txt`. L'**ODT** ha le stesse sezioni del Word: A4
  verticale, bordi neri sottili, niente fondi, collegamenti #1A3F8F sottolineati; intestazione con logo (E alta
  `ALTEZZA_E_MM`, base sulla linea di base) a sinistra, titolo al centro e linea sotto; piè «Prodotto da EuGEnio –
  eugenio.statocritico.it.» + `PIE_AVVERTENZA` e «Pagina N di M»; fonti, avvertenze complete e licenza in fondo.
  L'**ODS** ha gli stessi fogli dell'Excel (Info con logo, fonti e licenza, poi un foglio per tabella), numeri come
  numeri con formato italiano, date come date, nessuna formula, intestazione e piè di stampa come l'Excel. Il
  `mimetype` è il primo elemento dello zip, non compresso, come vuole lo standard. Controllati con LibreOffice
  headless (conversione in PDF) e riletti con pandas (`engine="odf"`).
- **PDF**: [fpdf2](https://py-pdf.github.io/fpdf2/) (Python puro, nessuna libreria di sistema) con il font
  **DejaVu Sans** del pacchetto Debian `fonts-dejavu-core`, installato nel `Dockerfile` durante la build.
  Senza il font si ripiega su Helvetica e i simboli fuori dal latin-1 diventano testo (`≥` → `>=`, `€` → `EUR`).
  In alternativa al pacchetto: copiare `DejaVuSans.ttf` e `DejaVuSans-Bold.ttf` (licenza libera) in una
  cartella dell'immagine e indicarla con `REPORT_FONT_DIR`. Con tabelle di più di 8 colonne il PDF è orizzontale.
- **Limiti** (variabili d'ambiente in `config.py`): corpo fino a 5 MB (`REPORT_MAX_MB`), 50 sezioni,
  100 blocchi per sezione, 30 colonne, 5.000 righe per tabella e 10.000 in tutto, 20.000 caratteri per testo,
  10 immagini da 1,5 MB. 60 report all'ora per IP, al massimo due generati alla volta
  (5.000 righe: ~5 s in Word o PDF, meno di 1 s in Excel).
- **Privacy**: tutto in memoria, nulla scritto su disco né registrato; risposta con `Cache-Control: no-store`.
- **Errori**: 410 (formato spento: docx, odt), 400 (formato sconosciuto, tipo sconosciuto, JSON non valido), 422 (documento non valido, con il motivo in
  italiano in `detail`), 413 (troppo grande), 429 (limite d'uso).
- **Immagini SVG nel PDF** (29/10/2026): prima di `pdf.image` gli SVG passano da `_svg_per_pdf` (il `font-family`
  diventa quello registrato nel PDF, DejaVu o Helvetica; via il `<title>`; `7px, 4px` → `7 4` in tratteggi, spessori e
  corpi; con Helvetica `€` → `EUR`); un'immagine che fpdf2 non riesce a leggere diventa la scritta «[Immagine non
  riproducibile nel PDF]» invece di far fallire il report. Verificato con le mappe 3D e i diagrammi di Pareto del sito:
  300 sedi × 6 colonne in Lombardia (1.812 comuni, due mappe + 6 Pareto) = corpo di circa 3,3 MB, PDF in circa 7 s,
  dentro i limiti attuali (5 MB di corpo, 1,5 MB per immagine): non è servito alzarli. Il sito manda le mappe del
  report «leggere» (coordinate intere, punti a meno di un pixel tolti, attributi comuni sul gruppo).
- **Mai dati di mercato**: i report non contengono prezzi GME/EEX (PUN, PSV, IGI, TTF, PFOR); le funzioni
  dei servizi leggono solo campi noti e scartano comunque le colonne con quei nomi.

**Report dei servizi** (`POST /api/report/{tipo}?formato=…`; il corpo è la risposta JSON già ricevuta):

| tipo | corpo | nome del file |
|---|---|---|
| `previsione` | risposta di `/api/previsione` più `richiesta` facoltativa (`comune`, `modalita`, `orizzonte`, `covariate`, `tipo`, `unita`) | `previsione_037006_breve.pdf` |
| `legge10` | risposta di `/api/clima-legge10/{istat}`, più il campo facoltativo `dpr412` {gg, zona, alt, nome, nota, origini} aggiunto dal sito (sezione "Confronto con il DPR 412/93"; differenza e zona ricalcolate dal server) | `clima_legge10_037006.pdf` |
| `patrimonio` | `{"righe": [...], "fonti": [...]}` con le righe unite di tutti i blocchi | `patrimonio_geolocalizzato.pdf` |
| `valori_sedi` (29/10/2026) | composto da `sito/valori_sedi.js` (Patrimonio, «Valori per sede»): `titolo`, `sottotitolo`, `totali` [{colonna, tipo: consumo\|costo, totale, unita, sedi}], `prezzi` [{consumo, costo, valore, unita, sedi}] (costo unitario medio = Σ costi / Σ consumi, colonne abbinate per posizione), `mappe` e `pareto` [{titolo, tipo, svg}] con gli **SVG piatti in base64** (colori di stampa già risolti nel browser), `tabelle` [{titolo, tipo, intestazioni, righe, decimali}], `note`, `fonti`, `avviso` {titolo, testo} facoltativo (file d'esempio, in cima). Ordine: totali, costi unitari medi, mappe, Pareto dei consumi, Pareto dei costi, tabella dei consumi, tabella dei costi. Le immagini solo nel PDF (la rotta passa `formato` ai tipi in `CON_FORMATO`); Excel e ODS hanno solo totali e tabelle. Immagini non valide saltate, al massimo `REPORT_MAX_IMMAGINI` (le altre segnalate in «Note») | `valori_per_sede.pdf` |
| `indicatori` | valori già calcolati da `sito/indicatori.js` (fase 8): `ente`, `regione`, `italia` {nome, codice, regione_ce, fonte_residenti, anni [{anno, provvisorio, spesa, leva, incidenza, peso, per_giornata, per_posto, per_cittadino, AZ9999, BZ9999, …}]}, `componente`, `anno_confronto`, `avvertenze`, `fonti`, `elaborazione`; il server impagina soltanto | `indicatori_energia_080_114.pdf` |

Attribuzioni sempre incluse: "Weather data by Open-Meteo.com (CC BY 4.0)" e ISTAT (CC BY 4.0) per previsione e
Legge 10, TiRex-2 per la previsione, "Dati elaborati da Zornade" con link a https://zornade.com e "ANNCSU –
Agenzia delle Entrate e ISTAT (CC BY 4.0)" per il patrimonio, OpenBDAP della Ragioneria Generale dello Stato
(CC BY 4.0) per gli indicatori; Zornade, ANNCSU e ISTAT per i valori per sede. Il report Legge 10 apre con l'avvertenza che i
dati non sostituiscono i valori normativi (UNI 10349, DPR 412/93).

**Nuovo tipo di report**: in `servizio/report_servizi.py` scrivere `def report_xxx(d: dict, **kw) -> Documento`
che costruisce sezioni e fonti dalla risposta del servizio, aggiungerlo a `TIPI` e una prova in
`tests/test_report.py`; la rotta `POST /api/report/xxx` esiste da sola. In alternativa il sito può comporre il
documento e inviarlo a `POST /api/report`.

Prove: dalla cartella `fase4-server`, `python -m pytest tests` (non servono TiRex-2 né i dati meteo).

Senza l'archivio meteo della fase 3 (`giornaliero.parquet`) `/api/clima-legge10/{istat}` risponde **503** con il
messaggio "i dati meteo delle ultime stagioni non sono ancora sul server", che la pagina Legge 10 mostra così com'è.
La zona risultante di `/api/clima-legge10` e dei Dati storici «Legge 10» usa la zona del DPR 412/93 del comune
(`storici.zona_dpr`, da `DATI/dpr412.json`) quando più zone sono coerenti (regola del 27/10/2026, README della
fase 3).

**Stile dei report (decisione del 27/10/2026)**: stile professionale e sobrio, adatto alla stampa in bianco e nero.
Testo nero; nessun fondo colorato (né nelle intestazioni delle tabelle né nei riquadri: solo bordi neri sottili);
collegamenti in blu scuro (`COLORE_LINK` = #1A3F8F) sottolineati. Logo Corallo a colori (`servizio/logo_eugenio.png`,
uguale per tutti i vestiti del sito). I grafici, quando verranno aggiunti, usano `SERIE_STAMPA`: sei serie con colore,
tratto e retino propri, adatte a chi confonde rosso e verde e leggibili anche stampate in bianco e nero.

**Intestazione e piè di pagina** (27/10/2026):
- logo: la base del simbolo è allineata alla linea di base della scritta EuGEnio e il tetto sporge un po' sopra la E;
  la E è alta `ALTEZZA_E_MM` = 4 mm; il PNG è tagliato sulla linea di base (`LOGO_MAIUSCOLA`, `LOGO_CIMA_MAIUSCOLA`
  dicono dove sta la E), così in Word poggia sulla stessa riga del titolo;
- PDF orizzontale: su una riga logo a sinistra, titolo al centro (rimpicciolito fino a 7 pt e poi accorciato se
  troppo lungo), "Prodotto da EuGEnio – eugenio.statocritico.it" a destra; la linea è sotto il testo;
- PDF verticale e Word (A4 verticale): logo e titolo; il piè comincia con "Prodotto da EuGEnio –
  eugenio.statocritico.it." e prosegue con l'avvertenza, sulla stessa riga;
- Excel e ODS (intestazione di stampa): "EuGEnio" a sinistra e titolo al centro; il piè comincia con "Prodotto da EuGEnio".
- ODT: come il Word (logo e titolo al centro con la linea sotto; piè con avvertenza e «Pagina N di M»).

## Newsletter automatica dei dati

Separata da Substack, che resta per gli articoli. Gira tutta sul server: [listmonk](https://listmonk.app)
(open source, AGPL-3.0) con PostgreSQL. Una lista **mensile**, con **doppia conferma** e cancellazione
con un clic in ogni email: il 12 del mese arrivano i gradi giorno osservati nel mese appena concluso nei
capoluoghi, rispetto agli anni precedenti, e gli ultimi prezzi Eurostat dell'energia per le PMI.

Le campagne partono da sole (`NOTIZIARIO_INVIO_AUTOMATICO=true`); con `false` restano in bozza e arriva un avviso.
I dati GME e TTF non compaiono. Iscrizione: `https://notizie.statocritico.it/subscription/form`
(collegata dal menu del sito, "Dati per email").

**Invio: OCI Email Delivery** (stesso account Oracle, dati in UE). Limiti dell'account a consumo: **50.000 email ogni
24 ore**, 18.000 al minuto, messaggi fino a 2 MB (ogni destinatario conta come un'email); l'account solo Always Free
non può inviare (limite 0). Il listino separa le prime 3.100 email del mese dalle successive, che costano pochi
centesimi ogni mille. listmonk distribuisce gli invii con una finestra mobile di **3.000 messaggi ogni 24 ore**: una
newsletter fino a 3.000 iscritti parte in un giorno; oltre, alzare la finestra (costo trascurabile).

Configurazione (una volta):
1. Console Oracle → *Developer Services → Email Delivery*:
   - *Email Domains* → `statocritico.it` → **DKIM**: aggiungi su Cloudflare il record CNAME indicato;
   - **SPF**: su Cloudflare esiste già il record TXT di Email Routing
     `v=spf1 include:_spf.mx.cloudflare.net ~all` (26/10/2026). **Non crearne un secondo**: modifica quello e
     aggiungi l'`include:` indicato dalla console Oracle prima di `~all` (due record SPF si annullano a vicenda);
   - *Approved Senders*: `eugenio@statocritico.it`.
2. Profilo utente → *Tokens and keys* → *SMTP credentials* → genera utente e password: nel `.env` (`SMTP_UTENTE`,
   `SMTP_PASSWORD`). Server `smtp.email.eu-milan-1.oci.oraclecloud.com`, porta 587. Se la sezione non c'è:
   *Identity → Domains → Default → Users →* il proprio utente *→ Edit user capabilities → SMTP credentials*.
   Per non mostrare le credenziali, sul server: `read -rs U`, `read -rs P`, poi
   `U="$U" P="$P" python3 -c '...re.sub("^SMTP_UTENTE=.*"...)'` con i valori tra apici singoli, e `unset U P`.
   Prova: `docker compose run --rm --no-deps api python -c "from servizio import avvisi; print(avvisi.invia('prova', 'prova'))"`
   (fatto il 26/10/2026: SPF, DKIM e DMARC in PASS su Gmail).
3. Nel `.env`: `LISTMONK_DB_PASSWORD`, `LISTMONK_ADMIN_PASSWORD` (lunghe), poi `docker compose up -d`.
4. `https://notizie.statocritico.it/admin` → *Impostazioni*:
   - *Generali*: URL radice `https://notizie.statocritico.it`, mittente `EuGEnio <eugenio@statocritico.it>`;
   - *SMTP*: dati del punto 2, **Auth protocol PLAIN** (con LOGIN Oracle risponde "504 authentication mechanism not
     supported"), TLS STARTTLS, HELO vuoto; **eliminare il blocco d'esempio `smtp.yoursite.com`**, altrimenti
     listmonk alterna i due server; *Performance*: **finestra mobile: 3.000 messaggi ogni 24 ore**;
   - *Privacy*: cancellazione con un clic, esportazione dei dati, collegamento all'informativa
     (`https://eugenio.statocritico.it/privacy.html`);
   - *Liste*: cancella le liste, gli iscritti e la campagna d'esempio; crea **EuGEnio mensile**, pubblica, **doppio
     opt-in**; il suo numero va in `LISTA_MENSILE` (l'interfaccia mostra solo l'UUID: il numero si legge con
     `docker compose exec postgres psql -U listmonk -d listmonk -tAc "select id, name from lists"`; oggi è 3);
   - *Utenti*: un utente **API** → `LISTMONK_API_UTENTE` / `LISTMONK_API_TOKEN`.
5. `docker compose up -d` per rileggere il `.env`. Prova: `docker compose exec worker python -m servizio.worker mensile` (con `NOTIZIARIO_INVIO_AUTOMATICO=false` resta in bozza).

Le stesse credenziali SMTP servono agli avvisi all'amministratore (errori notturni, password GME
scaduta, nuovi comuni ISTAT, campagne in bozza, download ANNCSU non riuscito, novità delle convenzioni
trovate dalla sorveglianza notturna).

## Consumo dell'API Open-Meteo gratuita

Emilia-Romagna (330 comuni): previsioni ogni 6 ore ~2.200 chiamate/giorno, storico ~550/giorno:
**~2.800 su 10.000 al giorno**. Il conteggio è in `dati/stato_api.json`. Se si eseguono anche i
download della fase 3 sullo stesso server, conviene sospendere quelli o usare l'istanza locale.
Per tutta Italia serve l'istanza Open-Meteo propria (`--profile open-meteo`).

## File in Excel e OpenDocument (dal 29/10/2026)

Chi carica i dati può usare anche **.xlsx** (Excel) e **.ods** (OpenDocument), oltre a CSV: `servizio/tabelle.py`
riconosce il formato dal contenuto, legge il **primo foglio** con pandas (openpyxl e odfpy, già nell'immagine) e lo
trasforma nel CSV che il resto del codice già capisce (punto e virgola, punto decimale, date AAAA-MM-GG[ hh:mm:ss]).
`/api/previsione` e `/api/patrimonio` lo fanno da sé; le pagine che leggono il file nel browser chiamano
`POST /api/converti` (risponde `{formato, fogli, foglio_usato, csv}`, 200 conversioni l'ora per IP). Il vecchio
.xls risponde 422 con l'invito a salvarlo in .xlsx. Tutto in memoria, niente su disco. Test: `tests/test_tabelle.py`.

## Risorse

TiRex-2 su CPU: ~1,2 GB di RAM (misurati) per il processo API. `torch.compile` è spento (`TORCHDYNAMO_DISABLE=1` in `modello.py`): l'immagine non ha `g++`. Se il meteo del comune non è sul server la previsione usa il solo calendario e lo dice in un avviso. Totale stimato con tutti i servizi:
~3,5 GB su 12. Disco: vedi la tabella "Spazio" nel README principale (~15 GB, ~35 GB con Open-Meteo).
Una previsione alla volta (`modello.py`) per non saturare i 2 core; dal 29/10/2026 ne entrano al massimo due
(una in calcolo, una in fila) e le altre ricevono 503 dopo 30 secondi (`protezione.py`). La conversione mensile
dell'indirizzario ANNCSU usa ~400 MB di memoria per un paio di minuti; il ricalcolo del clima dal 1940
(gennaio e luglio) ~1,5 GB per ~5 minuti.

## Protezione dell'API

Codice in `servizio/protezione.py` (decisione del 29/10/2026), prove in `tests/test_protezione.py`.

**Primo filtro: Cloudflare.** Il server non ha porte aperte (tunnel) e Cloudflare blocca gli attacchi di massa. Una
regola gratuita di rate limiting (il piano Free ne ha una: finestra di 10 secondi, conteggio per IP, blocco) ferma
le raffiche su `/api/`: Security → WAF → Rate limiting rules, `URI Path` inizia con `/api/`, 60 richieste in
10 secondi, azione Block per 10 secondi. Bot Fight Mode resta **spento**: sul piano Free non ammette eccezioni e
bloccherebbe anche chi usa le API dei dati aperti con uno script.

**Limiti per indirizzo** (finestra mobile di un'ora, in memoria, azzerati a ogni riavvio):

| Tipo | Rotte | Limite per IP all'ora |
|---|---|---|
| `previsione` | `/api/previsione` | 20 |
| `zornade` | `/api/geocodifica`, `/api/particella` | 120 |
| `patrimonio` | `/api/patrimonio` | 2.000 edifici |
| `report` | `/api/report`, `/api/report/{tipo}` | 60 |
| `converti` | `/api/converti` | 200 |
| `dati` | `/api/meteo`, `/api/clima-legge10`, `/api/mappa`, `/api/comuni`, `/api/metodologia` | `LIMITE_DATI_ORA` (600) |
| `stima`, `estrazione` | `/api/storici/stima`, `/api/storici/estrai` | `STORICI_STIME_ORA` (600), `STORICI_ESTRAZIONI_ORA` (30) |
| `sessione` | `/api/sessione` | `SESSIONI_ORA` (60) |
| `edifici_osm` | `/api/edifici/osm` e tessere OSM dei «Contorni degli edifici» che chiamano davvero Overpass o il WFS regionale (09/11/2026: prima anche la copia) | `EDIFICI_OSM_ORA` (300) |
| `edifici_osm_copia` | `/api/edifici/osm` con la cella già in copia (09/11/2026) | `EDIFICI_OSM_COPIA_ORA` (3.000) |
| `ortofoto` | tessere di `/api/ortofoto/{fonte}/…` chieste alla fonte (09/11/2026: solo queste) | `ORTOFOTO_ORA` (12.000) |
| `strati` | tessere di particelle e contorni regionali chieste alla fonte (09/11/2026; prima contavano come ortofoto) | `STRATI_ORA` (12.000) |
| `terreno` | tessere di `/api/terreno/…` da generare | `TERRENO_ORA` (6.000) |
| `tessere_copia` | tessere di ortofoto, strati e terreno servite dalla copia su disco (09/11/2026, tetto anti-abuso) | `TESSERE_COPIA_ORA` (60.000) |

**429 con `Retry-After` (09/11/2026, prove J10: migliaia di 429 in Modelli 3D)**: ogni 429 dei limiti per IP porta
`Retry-After` (secondi finché si libera il 10 % del limite, `Limitatore.attesa`) e `X-EuGEnio-Limite` (il tipo). Nella
pagina `protezione.js` ferma per quel tempo (da 30 s a 20 minuti) le richieste di quella fonte della mappa (ortofoto,
strati, edifici OSM, terreno), risponde da sé senza rete, scrive la nota sotto la mappa (prima di «Genera il 3D» o dei
comandi di Ortofoto: fonte, «limite orario», tra quanto riprova) e alla fine ricarica le tessere; la nota sparisce alla
prima risposta buona. Un 429 senza `X-EuGEnio-Limite` viene da Cloudflare (regola di rate limiting su `/api/`). I limiti
contano solo quello che costa alle fonti esterne o alla CPU: le tessere e le celle già in copia hanno solo i tetti alti
anti-abuso.

L'indirizzo è quello che Caddy mette in `X-Forwarded-For` (il `CF-Connecting-IP` di Cloudflare, non falsificabile
perché il server si raggiunge solo dal tunnel). Gli IPv4 contano uno per uno, gli **IPv6 per rete /64**: chi ha IPv6
ha miliardi di indirizzi e potrebbe cambiarli a ogni richiesta. Le code vuote si cancellano ogni 10 minuti.

**Tetti per tutto il sito**:
- **Zornade**: al massimo `ZORNADE_TETTO_ORA` (6.000) chiamate all'ora per tutti gli utenti insieme, contate davvero
  (la cache non consuma quota); il patrimonio controlla prima il caso peggiore (2 chiamate per edificio). Oltre il
  tetto: 503 «quota di quest'ora esaurita». La chiave gratuita ne ha 10.000 e per i termini del 18/09/2026 l'estrazione
  massiva e i carichi eccessivi fanno sospendere il token: il margine resta per le prove sul PC. Email all'amministratore, una volta al giorno, quando l'ora supera
  il 70 % del tetto (`ZORNADE_AVVISO_QUOTA`).
- **Previsioni**: `modello.py` ne calcola una alla volta; ne entrano al massimo `PREVISIONI_PARALLELE` (2: una in
  calcolo e una in fila), chi aspetta più di `PREVISIONI_ATTESA_S` (30 s; il tunnel chiude dopo 100 s) riceve 503
  «riprova tra un minuto» invece di restare appeso.
- Report: 2 alla volta (già prima); estrazioni dei dati storici: `STORICI_PARALLELE` (2).

**Verifica anti-robot (Cloudflare Turnstile)** su previsione, patrimonio, geocodifica, particella ed estrazione dei
dati storici:
1. `protezione.js` (nel `<head>` di tutte le pagine, da `parti/testa.html`) avvolge `fetch`: alla prima richiesta
   protetta legge `/api/protezione`, carica Turnstile e ottiene un gettone (di solito senza chiedere nulla; se
   Cloudflare vuole un clic compare un riquadro in basso a destra);
2. `POST /api/sessione` verifica il gettone con Cloudflare (`siteverify`, con l'IP del visitatore; il nome del sito
   deve essere tra `TURNSTILE_HOSTNAME`) e restituisce un **gettone di sessione** firmato con HMAC
   (`SESSIONE_CHIAVE`), valido `SESSIONE_MINUTI` (30) e legato alla rete di chi l'ha chiesto (IPv4 o /64);
3. le rotte protette vogliono il gettone nell'intestazione `X-EuGEnio-Sessione`, altrimenti 401 con
   `X-EuGEnio-Verifica: 1`; il sito allora rifà la verifica una volta e ripete la richiesta.

Senza `TURNSTILE_SITEKEY` e `TURNSTILE_SECRET` nel `.env` la verifica è spenta (prove, mirror): restano i limiti.
Le rotte dei dati aperti (meteo, Legge 10, catalogo e stime dei dati storici, report) restano usabili da script, con
i loro limiti. Configurazione: Cloudflare → Turnstile → Add widget, nome `eugenio`, dominio
`eugenio.statocritico.it`, modalità *Managed*; la Site Key va in `TURNSTILE_SITEKEY`, la Secret Key in
`TURNSTILE_SECRET`; `SESSIONE_CHIAVE` si genera con `openssl rand -hex 32` (se manca, a ogni riavvio dell'api le
sessioni aperte si rinnovano da sole con una nuova verifica).

**Avviso per i 429 ripetuti**: ogni rifiuto per limite si conta per giorno e per rete in
`/dati/protezione/429.json` (scritto al massimo ogni minuto). L'email all'amministratore parte **solo** quando la
stessa rete supera i limiti almeno `AVVISO_429_SOGLIA` (20) volte al giorno per `AVVISO_429_GIORNI` (3) giorni
consecutivi, una volta per serie di giorni, con i conteggi e la strada per bloccarla in Cloudflare (Security → WAF →
Tools → IP Access Rules). I conteggi si cancellano dopo `AVVISO_429_CONSERVA_GIORNI` (7) giorni, come dice
l'informativa privacy.

## Edifici 3D (fase 10, dal 04/11/2026)

- `servizio/edifici.py`: le due rotte `/api/edifici/…` qui sopra (limite delle rotte dei dati, nessun dato di mercato,
  mai i gradi giorno Arpae della fase 2). 5 test in `tests/test_edifici.py`.
- Report `edificio` (PDF, Excel, ODS) in `report_servizi.py`: edificio, piani e superfici con la fonte, indicatori
  geometrici, corpi con fonte e licenza della sagoma, consumi normalizzati, firma energetica, FV; avviso in cima se i
  dati sono sintetici.
- **Caddy** serve i prodotti della fase 10 come file statici da `/edifici3d/` (`handle_path`, Range, `Content-Type`
  per `.pmtiles` e COG, cache di un giorno): cartella `CARTELLA_EDIFICI` del `.env` (predefinita
  `/srv/energia/dati/edifici`, con le sottocartelle `cc-by/` e `odbl/`), montata in sola lettura nel servizio `caddy`.
  Dopo l'aggiornamento: `docker compose up -d caddy` (la cartella può essere vuota: la pagina apre la demo sintetica).

## Ortofoto, orizzonte lontano e PVGIS (fase 10, Fase B, dal 04/11/2026)

- **`servizio/ortofoto.py`** – proxy delle ortofoto. Le fonti stanno nei TOML di `fase10-edifici3d/ortofoto/` (uno per
  regione; nell'immagine in `/app/ortofoto_fonti`): RER 2023-24 (WMS `rer2023_24_rgb`, strato `RER2023_24_RGB`, stato
  «da confermare» finché la Regione non risponde), Toscana 2023 (CC BY 4.0, confermata), Sentinel-2 cloudless 2016 (EOX,
  CC BY 4.0) e WMS del Geoportale Nazionale (AGEA 2012, **solo dal vivo**, `cache = false`, mai nei report). Il proxy
  rifiuta all'avvio le fonti con indirizzi esclusi (Google, Esri, Bing, EOX 2018+, WMS AGEA). Copia su disco in
  `/dati/ortofoto/<fonte>/<z>/<x>/<y>.jpg` (`ORTOFOTO_GIORNI`, `ORTOFOTO_MAX_GB`, pulizia delle più vecchie), ritmo verso
  la fonte dal TOML (`ritmo.al_secondo`, `ritmo.all_ora`, attesa del turno fino a `ORTOFOTO_ATTESA_S`), limite per IP
  `ORTOFOTO_ORA` (dal 09/11/2026 solo per le tessere chieste alla fonte; dalla copia `TESSERE_COPIA_ORA`), intestazioni
  `Cache-Control: public, max-age=ORTOFOTO_CACHE_S` (così anche Cloudflare tiene la copia; per le fonti solo dal vivo
  `private, max-age=86400`, solo il browser, dal 09/11/2026: prima `no-store`), `ETag` e 304, `X-Ortofoto-Fonte`,
  `X-Ortofoto-Licenza`, `X-Ortofoto-Vuota: 1` per le tessere tutte trasparenti delle fonti `trasparente` (09/11/2026: la RER
  2023-24 non ha immagini a Bologna, Modena, Parma, Imola, Ferrara, Faenza, Bagno di Romagna, Comacchio; le pagine passano
  da sole alla fonte successiva). Ritmo dal 09/11/2026: RER 8/s, AGEA 2012 4/s e 4.000/h, attesa `ORTOFOTO_ATTESA_S` 8 s.
  **Spegnere una fonte** senza toccare i TOML: `ORTOFOTO_SPENTE=rer2023` nel `.env` e riavvio dell'api; oppure
  `ORTOFOTO_SOLO_CONFERMATE=true` (servite solo le fonti «confermata»); oppure `attiva = false`/`stato = "spenta"` nel TOML.
- **`servizio/orizzonte.py`** – orizzonte lontano: finestra di ±25 km del Copernicus DEM GLO-90 dai file
  `data/copernicus_dem90/static/lat_<grado>.om` di Open-Meteo (gli stessi che la fase 3 usa per la quota dei comuni,
  letti con `meteo_storico.s3.FSBlocchi`), angolo massimo per direzione con curvatura e rifrazione (k = 0,13), da 250 m
  in là (più vicino lavora la pagina con gli edifici). Copia in `/dati/orizzonte/`. ~1–4 s per punto la prima volta.
- **`servizio/terreno.py`** (07/11/2026, decisione di Paolo: il DTM non va più negli archivi dei comuni) – tessere del
  terreno 3D generate su richiesta dal COG unico per quadrante in `CARTELLA_TERRENO` (`/dati/terreno`, scritto una volta
  con `edifici-lidar dtm-server`), aprendo la panoramica adatta allo zoom (una tessera legge al più ~1 MB); vuoti e zone
  fuori dai DTM dal Copernicus DEM dei file `.om` dell'orizzonte; copia in `CARTELLA_TERRENO_TESSERE/<versione>/` (la
  versione cambia quando cambiano i DTM) con tetto `TERRENO_MAX_GB` (5) e pulizia delle più vecchie; limite per IP
  `TERRENO_ORA` (6.000 tessere nuove all'ora dal 09/11/2026; quelle in copia nel tetto `TESSERE_COPIA_ORA`), `TERRENO_PARALLELE` (2) generazioni insieme. `rasterio` (GDAL nella ruota)
  è nell'immagine dell'api. Prove: `tests/test_terreno.py` (8, DTM sintetico e Copernicus simulato).
- **`servizio/pvgis.py`** – confronto PVGIS: `PVcalc` della v5.3 chiamato dal server (PVGIS non ha CORS), con
  `userhorizon` (36 direzioni, massimo dei gruppi) e senza; ritmo per tutto il sito sotto le 30 chiamate al secondo del JRC
  (`PVGIS_AL_SECONDO=20`), limite per IP `PVGIS_ORA`, copia delle risposte in `/dati/pvgis/` per `PVGIS_CACHE_GIORNI`.
- **Caddy**: `/api/ortofoto/*` e (dal 07/11/2026) `/api/terreno/*` hanno un blocco loro (senza compressione, timeout di
  30 s); le intestazioni di cache le scrive l'api. **Cloudflare**: la regola di rate limiting su `/api/` (60 richieste in
  10 s) va ristretta per non bloccare le tessere: `URI Path starts with "/api/" and not URI Path starts with
  "/api/ortofoto/" and not URI Path starts with "/api/terreno/"` (passo manuale in `AGGIORNAMENTO_2026-11-04.md`, aggiunta
  del terreno in F20 di `AGGIORNAMENTO_2026-11-07.md`).
- **Report `edificio`**: sezioni nuove Obblighi di legge, Sole sulle facciate, Orizzonte lontano, Confronto con PVGIS,
  Classifica di priorità; figura con l'ortofoto (PNG) **solo** se porta licenza e citazione, che vanno nella didascalia e
  tra le fonti; le fonti «solo dal vivo» non entrano mai.
- Prove: `tests/test_ortofoto.py` (9, risposte simulate) e `tests/test_pvgis_orizzonte.py` (5, DEM sintetico e risposte
  simulate); `tests/test_edifici.py` con il report della Fase B. Dal vivo, dal container di sviluppo il 04/11/2026: WMS RER
  2023-24, WMS Toscana, EOX 2016, WMS del Geoportale Nazionale, PVGIS (con e senza `userhorizon`) e DEM su S3 rispondono.

## Strati sopra le ortofoto (05/11/2026, seconda pubblicazione)

- **`servizio/strati.py`** – stesso schema del proxy delle ortofoto (copia in `CARTELLA_ORTOFOTO/strati/`, ritmo verso la
  fonte per tutti gli utenti, limite per indirizzo «strati» dal 09/11/2026 (prima «ortofoto»; le tessere OSM consumano
  «edifici_osm» e il tetto di Overpass del sito; dalla copia «tessere_copia»), `Cache-Control` di 30 giorni), per
  immagini **trasparenti**:
  - **particelle catastali** (`catasto`): WMS INSPIRE dell'Agenzia delle Entrate, CC BY 4.0, senza EPSG:3857 né CORS. Si
    chiede il riquadro in EPSG:4258 (WMS 1.3.0, assi lat,lon) e si **riproiettano le righe** in web mercator (la longitudine
    è lineare in tutte e due: basta spostare le righe secondo la latitudine, esatto al pixel); con `metatessera = 2` si
    chiede un blocco 2×2 e si tiene la tessera in alto a destra (la scritta del servizio in basso a sinistra cade fuori);
    `contorni = true` toglie il riempimento e lascia linee e numeri nel colore del TOML;
  - **contorni degli edifici**: DBTR dell'Emilia-Romagna (`dbtr_edifici`, strato `EDI_Edificio`, EPSG:3857) e, per le altre
    regioni, OpenStreetMap (`osm_edifici`, Overpass, GeoJSON a tessere z16, archivio ODbL separato).
- Rotte sotto `/api/ortofoto/` apposta: il **Caddyfile non cambia** (nessuna compressione, timeout di 30 s) e la regola di
  rate limiting di Cloudflare, che esclude `/api/ortofoto/`, vale anche qui. Spegnimento senza toccare i TOML:
  `STRATI_SPENTI=id1,id2` nel `.env`, poi `docker compose up -d api`.
- TOML in `fase10-edifici3d/ortofoto/strati/` (copiati nell'immagine con la riga già esistente del Dockerfile).
- Prove: `tests/test_strati.py` (8, risposte simulate: riproiezione esatta, contorni senza griglia ai bordi, blocco 2×2,
  Overpass → GeoJSON, rotte, copia, spegnimento, coerenza con `fonti/regioni.toml`). Dal vivo dal container il 05/11/2026:
  WMS AdE e WMS DBTR rispondono (Rimini, zoom 17 e 18, allineati all'ortofoto RER); Overpass no (da provare dal server).
- Pubblicazione: rebuild dell'api e poi `docker compose up -d worker` (procedura D di `AGGIORNAMENTO_2026-11-05.md`).

## Ripiego OpenStreetMap degli edifici per Modelli 3D (07/11/2026)

Decisione di Paolo del 07/11/2026: OpenStreetMap resta come **ripiego** dove il punto cade fuori da ogni archivio di
qualità (DBTR: fuori dall'Emilia-Romagna e nei comuni ER non ancora preparati); dove c'è il DBTR vale il DBTR e OSM non si
mescola (lo decide la pagina, README della fase 5).

- **`servizio/edifici_osm.py`** – `GET /api/edifici/osm?lon=&lat=`: il punto si arrotonda alla **cella di 0,002°**
  (~200 m); una sola query Overpass piccola (`around:400` dal centro della cella, XML con i membri delle relazioni) serve
  tutti i punti della cella e resta **in copia** in `/dati/edifici_osm/<j>_<i>.json` per `EDIFICI_OSM_GIORNI` (30;
  oltre 500 MB si tolgono le più vecchie). A Overpass va il centro della cella, non il punto dell'utente.
- **Riuso**: lettore e regole di `fase10-edifici3d/edifici3d/osm_campione.py` (`query_punto`, `corpi_al_volo`: way chiuse,
  multipoligoni con i cortili e way aperte, i pezzi dello stesso multipoligono = un edificio, altezza `height` →
  `building:levels` × 3 m → **stima** di 9 m dichiarata in `fonte_altezza` e `qualita = "stima"`), copiato nell'immagine
  con `modello.py`, `osm.py` e `tessere.py` (Dockerfile); `shapely` e `pyproj` in `api/requirements.txt`. Client Overpass
  di `strati.py` (`chiedi_overpass`, istanza principale e di riserva dello strato `osm_edifici`, User-Agent del servizio);
  `EDIFICI_OSM_URL` nel `.env` per altre istanze.
- **Regole d'uso di Overpass**: **una chiamata alla volta** per tutto il sito e almeno un secondo tra due chiamate; turno
  atteso al massimo `EDIFICI_OSM_ATTESA_S` (15 s), poi 503; timeout `EDIFICI_OSM_TIMEOUT_S` (30 s) per istanza (due istanze +
  attesa restano sotto i 100 s di Cloudflare; Caddy ha 180 s su `/api/`); tetto `EDIFICI_OSM_TETTO_ORA` (300) chiamate
  all'ora per tutto il sito (`protezione.tetto_globale`), poi 503. Risposte di Overpass con `<remark> runtime error` = 502.
- **Protezione**: Turnstile (gettone di sessione, `edifici_osm` in `TIPI_PROTETTI`, `protezione.js` del sito) come
  patrimonio e geocodifica, perché la rotta consuma le quote di Overpass del server; limite per IP `edifici_osm`.
- **Spegnimento**: `EDIFICI_OSM=false` nel `.env` e `docker compose up -d api` (la rotta risponde 404, la pagina dice che il
  ripiego non è disponibile).
- **Licenza**: `licenza: "ODbL 1.0"`, `attribuzione: "© OpenStreetMap contributors (ODbL 1.0)"` nella risposta e in ogni
  corpo, intestazione `X-Licenza`; la copia su disco è un database derivato ODbL, separato dagli archivi CC BY.
- **Caddyfile**: nessuna regola nuova (`/api/*` con 180 s e compressione bastano).
- Prove: `tests/test_edifici_osm.py` (7, Overpass simulato: licenza e cortili, istanza di riserva, copia per cella e
  scadenza, limiti per IP, tetto, fuori Italia, spegnimento, Overpass giù o in timeout, turno occupato, Turnstile). Dal vivo
  dal container il 07/11/2026 (stesso codice della rotta): Pesaro, ospedale San Salvatore (43,904 N 12,906 E), **390 corpi
  in 24,9 s** (10 con altezza da OSM, 380 stimati, un multipoligono con cortile); Cesena, ospedale Bufalini (44,1405 N
  12,2405 E), **746 corpi in 20,2 s** (19 pezzi di multipoligoni, 18 con cortile, 745 stimati); seconda richiesta nella
  stessa cella dalla copia in 0,01 s. `overpass-api.de` dal container: connessione chiusa o 502; la riserva di allora,
  `maps.mail.ru`, ha risposto (a tratti 504): sostituita il 07/11 pomeriggio (sotto).
- Pubblicazione: rebuild dell'api e `docker compose up -d --force-recreate api worker` (IMAGE `energia-api` per tutti e
  due), procedura F di `AGGIORNAMENTO_2026-11-07.md`.

### Altezze, istanza di riserva e Turnstile (decisioni di Paolo del 07/11/2026 pomeriggio)

- **Altezze**: ai corpi senza `height` né `building:levels` la rotta dà la **mediana delle gronde dei corpi DBTR vicini**
  (entro 200 m, almeno 3, altezze del DB topografico non stimate) letti da `archivi.json` e dalle celle di contesto degli
  archivi in `CARTELLA_EDIFICI_INTERNA` (`/dati/edifici`; al più 64 celle in memoria, `archivi.json` riletto quando cambia);
  altrove la stima fissa di 9 m. Calcolo **a ogni risposta** (`con_altezze_vicine`), non nella copia su disco. Ogni corpo
  porta `origine_altezza` (`osm_height`, `osm_piani`, `dbtr_vicini`, `fissa`) e la fonte («stima: mediana dei corpi DBTR
  vicini (11 entro 200 m: 5 m)»); la risposta ha i conteggi in `altezze` (più `altezze_stimate`, `altezze_osm`). Regola in
  `fase10-edifici3d/edifici3d/osm_campione.py` (`altezze_da_vicini`), uguale nella pagina per il DB topografico caricato
  nel browser. Prova su dati veri: al confine Rimini–Coriano 27 corpi su 28 dai vicini DBTR; Pesaro 380 a 9 m.
- **Istanza di riserva** (al posto di `maps.mail.ru`, VK): **Overpass API Europa** `https://ovp.dresel.systems/api/interpreter`
  (Christian Dresel, Fürth, Germania; dati Europa da Geofabrik aggiornati ogni giorno; libera, senza chiave; 4 richieste
  parallele per IP; registri di 14 giorni con informativa GDPR; nessuna garanzia di disponibilità). Dal container il
  07/11: 200 in 1,0–2,5 s su Pesaro, Cesena, Milano, Napoli, Palermo. Alternative valutate: `overpass.private.coffee` (ex
  kumi.systems, Austria: API senza risposta in 60 s, anche dal server il 06/11), `overpass.openstreetmap.fr` (solo usi
  autorizzati, dati di luglio 2026), `overpass.osm.ch` (solo Svizzera). `servizio/strati.py`: `OVERPASS_PRINCIPALE`,
  `OVERPASS_RISERVA`, `riserva_overpass()` comune allo strato `osm_edifici` e al ripiego; nel `.env` `OVERPASS_RISERVA`
  (riga assente = riserva del TOML; **vuota = nessuna riserva**, da usare se dal server non risponde: F13 della
  procedura; più istanze separate da virgola). La principale resta `overpass-api.de` (FOSSGIS e.V.).
- **Turnstile** resta sul ripiego (confermato da Paolo).
- Prove: `tests/test_edifici_osm.py` (+2: mediana dei vicini DBTR e corpi stimati esclusi, copia su disco senza le altezze
  calcolate; pochi vicini → 9 m), `tests/test_strati.py` (riserva europea, `OVERPASS_RISERVA` dal `.env`, vuota = nessuna).

## Newsletter: sezione «Novità di EuGEnio» (07/11/2026)

`servizio/notiziario.py` (`novita_del_mese`): nella newsletter mensile, dopo i prezzi Eurostat, le voci del mese concluso
del registro delle versioni `fase5-sito/novita.toml` (README della fase 5), con il rimando a `novita.html`. Il file è
copiato nell'immagine (`COPY fase5-sito/novita.toml /app/novita.toml`, `NOVITA_TOML` in `config.py`): il pacchetto del
codice (F5) lo deve comprendere. Nessun dato di mercato. Prova: `tests/test_notiziario_novita.py` (2). Caddy serve
`/novita.xml` come `application/atom+xml; charset=utf-8`.

## «Aggiungi DBTR»: proposte di DB topografici e approvazione interna (07/11/2026)

Decisione di Paolo del 07/11/2026 (pagina Patrimonio › Aggiungi edifici (DB topografico), README della fase 5): il DB
topografico si legge nel browser; **solo con il consenso** dell'utente lo stesso file arriva qui, in una coda, e diventa
parte dell'archivio comune dopo l'approvazione nella pagina interna.

- **`servizio/dbtr_coda.py`** – `POST /api/dbtr/inizia` (Turnstile, tipo `dbtr` in `TIPI_PROTETTI`; JSON con regione
  `er|lom|fvg|lig`, comune, `istat`, `intero`, `formato` `zip|gpkg`, `dimensione`, `consenso: true`, `impronta` SHA-256;
  nessun dato personale) → `id`, `gettone` (HMAC con la chiave delle sessioni), `pezzo_byte`, `pezzi`;
  `PUT /api/dbtr/{rid}/pezzo/{n}` (corpo = pezzo, gettone in `X-EuGEnio-Dbtr`, scritto in posizione nel file
  preallocato `caricato.part`); `POST /api/dbtr/{rid}/fine` (pezzi tutti presenti, impronta, `edifici3d.coda.controlla_file`:
  zip senza percorsi «..»/assoluti/con unità, senza link simbolici né cifratura, rapporto ≤ 200:1 sulle voci oltre 50 MB,
  ≤ 3 GB estratti, con almeno un GeoPackage o Shapefile; oppure un GeoPackage) → `ricevuto`, altrimenti 422 e cartella
  cancellata; `GET /api/dbtr/{rid}` (stato e messaggio, anche dopo installazione o rifiuto per 30 giorni) e
  `DELETE /api/dbtr/{rid}` (ritiro prima dell'approvazione).
- **Rotte interne** (stessa verifica di `interno.py` più l'intestazione `X-EuGEnio-Interno: 1` e `Sec-Fetch-Site` non
  `cross-site` sulle POST): `GET /api/interno/dbtr/coda` (richieste, ultime 30 decisioni, limiti, spazio),
  `GET /api/interno/dbtr/{rid}/anteprima` (GeoJSON dei corpi preparati), `GET …/registro` (uscita di `prepara`),
  `POST …/approva` (solo da «in attesa di approvazione»: stato «approvato», l'installazione la fa `edifici-coda`) e
  `POST …/rifiuta` (cartella cancellata, esito e riga di storico).
- **Limiti** (`.env`): `DBTR_MAX_MB=300`, `DBTR_PEZZO_MB=32` (Cloudflare accetta al più 100 MB per richiesta; Caddy 40 MB su
  `/api/dbtr/*`), `DBTR_CARICAMENTI_GIORNO=3` (per rete, finestra di 24 ore: nuovo tipo giornaliero in `protezione.py`),
  `DBTR_PEZZI_ORA=60`, `DBTR_CODA_MAX=20` richieste aperte, `DBTR_CODA_MAX_GB=4`, `DBTR_LIBERO_MIN_GB=10`;
  `DBTR_CODA=false` spegne le rotte pubbliche (404; la lettura nel browser resta). Cartella `CARTELLA_CODA_DBTR`
  (`/dati/edifici_coda`, scrivibile dall'utente 1000, mai servita da Caddy).
- **Servizio `edifici-coda`** (`docker-compose.yml`, profilo `edifici`, immagine `energia-edifici`, `restart:
  unless-stopped`, 1 CPU, `cpu_shares: 128`, 4 GB): `python -m edifici3d coda --ciclo` (README della fase 10). Si accende
  con `docker compose --profile edifici up -d edifici-coda`; non va nel crontab.
- L'immagine dell'api copia `fase10-edifici3d/edifici3d/coda.py` (in testa solo libreria standard).
- Test: `tests/test_dbtr_coda.py` (16: caricamento a più pezzi, consenso, regione, nomi, dimensione, sette zip malevoli,
  impronta, limite giornaliero, coda piena, spegnimento, ritiro, rotte interne con JWT finto, Caddyfile/compose/.env).

## Pipeline LiDAR e pagina di stato interna (fase 10, Fase C, dal 04/11/2026)

- **Container `edifici-lidar`** (profilo `edifici` del compose, immagine `energia-edifici` da `fase10-edifici3d/Dockerfile`,
  1 CPU, 4 GB): non resta acceso, lo lancia il cron dell'host alle 3:30 con `docker compose --profile edifici run --rm
  edifici-lidar` e si ferma da solo alle 7:00 (finestra nel TOML della zona). Monta `/dati` (stato in
  `/dati/edifici_stato`) e `CARTELLA_EDIFICI` (prodotti in `/dati/edifici`, serviti da Caddy in `/edifici3d/`).
- **`/api/salute`** dà anche `previsioni_in_corso` (previsioni in calcolo o in fila): la pipeline aspetta finché è > 0.
- **`servizio/interno.py`**: rotte `/api/interno/…` (tabella dell'API). Il JWT dell'intestazione `Cf-Access-Jwt-Assertion`
  si verifica con PyJWT: firma RS256 con le chiavi del team (`https://<team>/cdn-cgi/access/certs`, in memoria un'ora),
  `aud` = `CF_ACCESS_AUD`, `iss` = `https://<team>`, scadenza; `CF_ACCESS_EMAIL` facoltativo. Team e audience **solo nel
  `.env`**; senza, 503 (chiuso anche nei mirror). Limite «interno»: `INTERNO_ORA` richieste per IP all'ora.
- **Caddy**: `/api/interno/*` e `/interno/*` rispondono 403 senza l'intestazione di Access, mandano `X-Robots-Tag:
  noindex, nofollow` e `Cache-Control: no-store`; la pagina statica passa da `forward_auth` verso `/api/interno/verifica`
  (così anche l'HTML richiede un JWT valido); `/interno` porta a `/interno/edifici.html`. Provato con caddy 2.10 e
  un'api simulata: 403 senza intestazione o con gettone falso, 200 con gettone valido.
- **Report `edificio`**: sezione «Falde dei tetti» (falde dal LiDAR o dal modello dell'utente).
- Prove: `tests/test_interno.py` (13: gettone valido, firma di un'altra chiave, audience, emittente, scaduto, HS256,
  email ammesse, chiusura senza configurazione, Caddyfile, `.env.example`, report con le falde).

- **Stato della zona** (05/11/2026): ogni zona della risposta ha `situazione` = `{stato, testo}` coerente con l'esito
  dell'ultima notte: `in attesa` (nessuna fonte DSM/LAS attiva e/o 0 corpi della Fase A: «manca prepara»), `non
  avviata`, `fermata`, `completata`, `in corso`. Prima la pagina diceva «Zona in corso» anche con 0 tessere su 0. Test in
  `tests/test_interno.py` (7 nuovi).

## Analisi avanzate con il modulo privato (fase 10, Fase E, dal 04/11/2026)

- **`servizio/analisi.py`**: rotte `/api/analisi/…` (tabella dell'API), limite «dati». Usa l'aggancio pubblico
  `edifici3d/analisi.py` della fase 10 (copiato nell'immagine con il suo `__init__.py`, riga nuova di `api/Dockerfile`).
- **Modulo privato** delle metodiche UNI (decisione del 03/11/2026): **mai nell'immagine né nel repository**. Sul server sta
  in `/srv/energia/dati/uni_privato` e il container lo vede come `/dati/uni_privato` (o dove dice `UNI_PRIVATO` nel `.env`).
  Senza modulo, o con le sue tabelle ancora da compilare, ogni analisi risponde «analisi non disponibile in questa
  installazione» e il resto del servizio funziona come prima. Un modulo rotto o con un'altra versione dell'interfaccia
  non fa cadere l'api (avviso nel registro, analisi spente).
- **`.dockerignore`** nella cartella principale (nuovo): `fase2-gradi-giorno/`, `fase10-edifici3d/uni_privato/`, `.env`,
  ambienti e cache non entrano mai nel contesto di build delle immagini (anche quella della pipeline, che copia tutta la
  fase 10).
- Ortofoto: due TOML nuovi copiati nell'immagine con gli altri, `bolzano.toml` (Ortofoto 2023) e `trento.toml` (PAT 2015).
- Prove: `tests/test_analisi.py` (2: senza modulo tutto «non disponibile», con un modulo finto scritto nel test la sola
  analisi pronta risponde e le chiavi interne non escono).

## Licenze e attribuzioni (da mostrare sul sito)

- Codice di EuGEnio: AGPL-3.0. Dati elaborati e report prodotti da EuGEnio: CC BY 4.0, riuso citando
  «Fonte: EuGEnio – eugenio.statocritico.it» (con la data di estrazione) e mantenendo le fonti originali.

- TiRex-2: NX-AI, Apache 2.0.
- Meteo: "Weather data by Open-Meteo.com" (CC BY 4.0) – modelli Arpae ICON-2I, DWD ICON, ECMWF IFS, ERA5 Copernicus.
- "Dati elaborati da Zornade" (link a https://zornade.com) – catasto Agenzia delle Entrate, ISTAT, OpenStreetMap (ODbL).
- Civici: ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0).
- Confini comunali: ISTAT (CC BY 4.0) via Gramscii.
- Ortofoto (Fase B): la citazione e la licenza di ogni fonte stanno nel suo TOML e sotto la mappa; PVGIS © Unione europea
  (riuso con citazione); Copernicus DEM GLO-90 © DLR e Airbus (licenza Copernicus DEM) dai file di Open-Meteo (CC BY 4.0).
- Report: python-docx (MIT), fpdf2 (LGPL-3.0), openpyxl (MIT), odfpy (Apache 2.0 / GPL 2+), font DejaVu Sans (licenza libera Bitstream Vera/DejaVu).
