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
| `worker` | (22/11/2026) **suolo e aree agricole** il 6 del mese dalle 05:30 (`suolo`: indicatori ISPRA, colture e censimento ISTAT, incrocio del suolo agricolo una volta per carta; ricostruisce solo se qualcosa è cambiato), vedi § «Suolo e aree agricole»; (20/11/2026) **dati di Terna**: ogni giorno alle 06:30 il giorno prima dall'API ufficiale e qualche mese di storico dal Download Center (`terna-api`, archivio `/dati/terna/serie`), poi i file di «Carichi elettrici» (`carichi`); il 5 del mese alle 05:00 le statistiche annuali per «Produzione e consumi di elettricità» (`elettricita`), vedi § «Dati di Terna»; (20/11/2026) **controllo mensile del servizio del GSE delle aree convenzionali** il 3 del mese dalle 7 (`gse-aree`, una richiesta `?f=json`, email solo se non risponde); (17/11/2026) **interruzioni della rete elettrica ogni 15 minuti** (thread a parte) e **saturazione dei trasformatori ogni notte alle 01:15** (`rete-interruzioni`, `rete-saturazione`, database `/dati/rete/rete.sqlite`); (14/11/2026) ogni giorno dopo lo storico le ore nuove dell'**archivio psicrometrico** (`psicro`, se `CARTELLA_PSICRO` c'è); (11/11/2026) dopo i mercati di ogni notte anche gli **indici dei prezzi** per il sito (`prezzi`, `/sito/dati/prezzi/indici.json`); previsioni meteo ogni 6 ore e storico meteo ogni giorno per i comuni delle `REGIONI_AGGIORNATE` (vuoto = tutte le `REGIONI` servite; giornaliero aggiornato a blocchi di comuni, vedi «Meteo nazionale a blocchi»); **dati di mercato ogni notte alle 02:30** (fase 6), seguiti dalla **sorveglianza delle fonti delle convenzioni** (pagine di Intercent-ER, Consip, CET; email solo quando cambia qualcosa); **newsletter mensile** il 12 del mese (dopo l'aggiornamento del 10 dei dati di e-distribuzione); verifica comuni/confini il 2 del mese; **indirizzario ANNCSU** il 12 del mese (fase 7); avvisi per email |
| `caddy` | sito statico della fase 5 e instradamento verso l'API, solo dentro la rete Docker |
| `cloudflared` | **Cloudflare Tunnel**: collega il server a Cloudflare senza aprire porte; l'HTTPS lo fa Cloudflare |
| `listmonk` + `postgres` | newsletter automatica dei dati: liste, doppia conferma, cancellazione, invii |

Un quarto container, `open-meteo`, è facoltativo (istanza Open-Meteo propria, vedi fase 3).

## Aggiunte del 17/11/2026 (stato della rete elettrica e cabine primarie)

- Modulo `servizio/rete.py`: database SQLite `/srv/energia/dati/rete/rete.sqlite` (nel container `/dati/rete/`), raccolta
  delle **interruzioni ogni 15 minuti** e **saturazione dei trasformatori ogni notte alle 01:15** nel worker, sei rotte
  `/api/rete/…` per le pagine «Statistiche › Stato della rete elettrica» e «Fotovoltaico › Cabine primarie». Dettagli:
  § «Stato della rete elettrica». Messa in servizio: `../AGGIORNAMENTO_2026-11-18_rete.md`.
- Nessuna variabile obbligatoria nel `.env` (valori predefiniti in `.env.example`), nessuna modifica al Caddyfile né al
  compose: il database sta nella cartella dei dati già montata.

## Aggiunte del 20/11/2026 (aree convenzionali del GSE per Comunità energetiche)

- `servizio/rete.py`: costante `URL_GSE_AREE` (FeatureServer `AC_Comuni_2025` del GSE, unico indirizzo lato server; quello
  del browser è in `fase5-sito/sito/rete.js` e una prova controlla che coincidano) e `controlla_servizio_gse()`: una sola
  richiesta `URL_GSE_AREE?f=json`, nessun dato salvato; errore se non risponde, se risponde con un errore ArcGIS o se manca
  lo strato 0. I perimetri delle aree **non passano mai dal server**: li legge il browser.
- `servizio/worker.py`: lavoro `gse-aree` **una volta al mese**, il giorno `GSE_CONTROLLO_GIORNO` (3) dalle
  `GSE_CONTROLLO_ORA` (7, ora italiana), registrato in `worker_stato.json` (una volta anche se fallisce); **email
  all'amministratore solo se il servizio non risponde** (oggetto «servizio del GSE delle aree convenzionali non risponde»,
  con le istruzioni per AC_Comuni_2027). A mano: `docker compose run --rm worker python -m servizio.worker gse-aree`.
- `/api/rete/stato`: in `fonti` anche `aree_convenzionali_gse` e `pagina_aree_convenzionali_gse` (solo indirizzi).
- Nessuna rotta nuova: la pagina usa `/api/rete/cabine/comune/{istat}`. Nessuna variabile obbligatoria. Per attivare il
  controllo basta ricreare il worker con il codice nuovo (`docker compose up -d --force-recreate worker`); l'API va
  ricreata solo per il campo nuovo di `/api/rete/stato`.
- Prove: `tests/test_rete.py` (risposta valida, HTTP 503, non JSON, errore ArcGIS, strato 0 mancante, rete assente, stesso
  indirizzo in rete.py e rete.js) e `tests/test_worker.py` (email solo se non risponde, una volta al mese nel ciclo).

## Aggiunte del 20/11/2026 e (dati di Terna nel worker)

- Modulo `servizio/terna.py` e tre lavori nuovi del worker: `terna-api` (serie quartorarie e IMCEI), `elettricita`
  (statistiche annuali, fase 15) e `carichi` (file di «Carichi elettrici», fase 15). Dettagli: § «Dati di Terna».
- Immagine: `fase15-elettricita/elettricita` copiata in `/app/elettricita` (`api/Dockerfile`, come la fase 8);
  `aggiorna_da_github.sh` copia anche `fase15-elettricita` e non tocca `dati/elettricita/` e `dati/carichi/` del sito.
- Variabili nuove nel `.env`: `TERNA_CLIENT_ID`, `TERNA_CLIENT_SECRET` (facoltative: senza, l'API non parte; le altre hanno
  valori predefiniti). Nessuna modifica al Caddyfile né ai volumi: le pagine leggono `dati/elettricita/` e `dati/carichi/`
  nella cartella del sito, già montata nel worker come `/sito/dati`. Messa in servizio: `../AGGIORNAMENTO_2026-11-20e.md`.

## Aggiunte del 22/11/2026 (suolo e aree agricole nel worker; non ancora in una release)

- Lavoro nuovo del worker `suolo` (e `suolo-forza`), fase 16: dettagli nel § «Suolo e aree agricole».
- Immagine: `fase16-suolo/suolo` copiata in `/app/suolo` (`api/Dockerfile`); usa openpyxl, numpy, rasterio, pyproj e
  shapely, già nell'immagine. `aggiorna_da_github.sh` copia anche `fase16-suolo` (e lo controlla con i COPY del Dockerfile)
  e non tocca `dati/suolo/` del sito.
- Variabili nuove nel `.env`, tutte facoltative: `SUOLO_DATI` (archivio, predefinito `/dati/suolo`), `SUOLO_GIORNO` (6),
  `SUOLO_ORA` (05:30), `SUOLO_CARTE` (1: scarica anche le carte raster, ~800 MB, e fa l'incrocio agricolo; 0 per saltarlo).
  Nessuna modifica al Caddyfile né ai volumi: la pagina legge `dati/suolo/` nella cartella del sito, già montata nel worker.

## Aggiunte del 22/11/2026 b (dati pluviometrici; release `v2026.11.22b`, versione 20261122b)

- Modulo nuovo `servizio/radar.py`: lavoro del worker in un thread a parte (`radar`, ogni 30 minuti) e rotte
  `/api/radar/stato`, `/api/radar/punto`, `/api/radar/comune/{istat}` (limite `RADAR_ORA`); dettagli nel § «Dati
  pluviometrici». Solo il «Merging» del DPC (CUM3/6/12/24), fini statistici, niente allerta (decisioni di Paolo).
- Dipendenza nuova `dpc-radar==0.3.0` (Apache-2.0) in `api/requirements.txt`: richiede solo httpx, numpy e rasterio, già
  nell'immagine. Nessun COPY nuovo nel Dockerfile (il modulo sta in `servizio/`).
- `rete.py`: rotta nuova `/api/rete/interruzioni/periodo?da=…&a=…` (al più 8 giorni) per l'animazione della pagina.
- `report.py`: campo `licenza` del documento (`"CC BY 4.0"` predefinito, `"CC BY-SA 4.0"` per i file con i dati del DPC),
  che adatta i testi della licenza nelle avvertenze e nei piè di pagina (`_lic`).
- `notiziario.py`: sezione «La pioggia di <mese>» nel mensile per regione e «Pioggia misurata» nel settimanale (con la
  previsione di una settimana prima, salvata da `settimanale()`); nessun avviso.
- Caddyfile: `dati/radar/indice.json` senza cache, immagini dei frame in cache una settimana.
- Variabili nuove nel `.env`, tutte facoltative: `RADAR_ATTIVO`, `RADAR_DATI` (`/dati/radar`), `RADAR_SITO`
  (`/sito/dati/radar`), `RADAR_MIN` (30), `RADAR_GIORNI_MAPPA` (7), `RADAR_ARCHIVIO_ANNI` (10), `RADAR_RECUPERO_GIORNI` (150),
  `RADAR_SCARICHI` (60), `RADAR_SPAZIO_MIN_GB` (5), `RADAR_AVVISO_ORE` (12), `RADAR_ORA` (1200). Nessun volume nuovo: il
  worker scrive in `/dati/radar` e `/sito/dati/radar`, già montate.

## Ortofoto AGEA 2022-2024 per tutta Italia (17/11/2026, segnalazione di Paolo)

> **19/11/2026 sera (segnalazione di Paolo, scacchiere nella vista 3D)**: l'`exportImage` del Geoportale AGEA risponde 200
> con una scacchiera bianca e nera al posto della foto (provato in sette città, tutti e tre gli anni; il servizio ha
> maxScale = zoom 18). Le tessere dello zoom 19 venivano da lì e andavano in copia. Ora la fonte `agea` va da zoom 10 a 18
> (`italia.toml`; oltre la mappa ingrandisce il 18) e `scacchiera()` in `servizio/ortofoto.py` scarta una tessera a
> scacchiera di qualunque fonte come errore (mai in copia). Le copie dello zoom 19 sul server si possono cancellare
> (`AGGIORNAMENTO_2026-11-19c.md`).

- **Causa**: fuori da Emilia-Romagna, Toscana e Trentino-Alto Adige l'unica foto aerea era `pcn2012`, il WMS del
  Geoportale Nazionale (MASE) con il volo AGEA 2012 a 50 cm: solo dal vivo, lento e spesso in errore (502), da cui «non
  risponde o è occupata» in Ortofoto, Modelli 3D e Fotovoltaico › Cabine primarie.
- **Fonte nuova `agea`** (`fase10-edifici3d/ortofoto/italia.toml`, `tipo = "arcgis"`): servizi ImageServer del Geoportale
  AGEA `AgEA/Ortofoto_AgEA_2024`, `_2023`, `_2022` (RGB, 20 cm, CC BY 4.0 dalle note legali, Reg. UE 2023/138), tessere
  già pronte `/tile/{z}/{y}/{x}` fino allo zoom 18 (`zoom_tessere`) e `exportImage` sul riquadro della tessera allo zoom
  19; con copia sul server, nei report, zoom 10–19, ritmo 10/s e 8.000/h, priorità 2 (dopo RER 2023-24, Toscana 2023,
  Bolzano 2023; Trento 2015 passa a 3, dietro AGEA 2023; `pcn2012` resta a 8 come ripiego da scegliere a mano).
- **Anno più recente per tessera** (`ortofoto.py`, `tessera_anni`, `componi`): ogni anno AGEA vola circa un terzo d'Italia
  per regioni intere (2024 Piemonte, Valle d'Aosta, Lombardia, Veneto, Molise, Calabria; 2023 Trentino-Alto Adige,
  Friuli-Venezia Giulia, Emilia-Romagna, Umbria, Lazio, Campania, Basilicata; 2022 le altre) e dove non ha volato il
  servizio dà un PNG trasparente. Il proxy chiede prima l'anno più recente; se non riempie la tessera chiede insieme gli
  altri e compone (il più recente sopra, i precedenti nei buchi: confini tra regioni). Un anno con una tessera tutta
  trasparente a zoom ≥ 10 non si chiede più per le tessere figlie fino a 4 livelli sotto (`_vuote_anno`, in memoria):
  dopo i primi zoom ogni tessera nuova costa **una** chiamata. Anni usati in `X-Ortofoto-Anno` (`2023` o `2023,2022`) e
  nel file `<y>.jpg.anno` accanto alla copia (senza quel file la copia non vale e si richiede). In `/api/ortofoto/fonti`
  la fonte ha `anni` e `citazione_anni` (con `{anni}`); `citazione` è quella generica «… ortofoto RGB 2022-2024 …». La
  pagina mette nella citazione gli anni delle tessere della vista (fase 5, `protezione.js`).
- **Tempi dal container** (17/11/2026, prima volta / dalla copia): Rimini e Roma 2023, Milano 2024, Palermo e Bari 2022,
  Trento 2023: 0,16–0,35 s a tessera agli zoom 16–19 (0,3–1,6 s allo zoom 12, quando il primo anno chiesto è vuoto);
  dalla copia 3–6 ms. Confine Gabicce (Emilia-Romagna 2023, Marche 2022) allo zoom 12: «2023,2022».
- **Sul server**: nessuna variabile nuova, nessuna modifica a Caddy o al compose; i TOML vanno nell'immagine come sempre
  (`/app/ortofoto_fonti`). La copia di `pcn2012` non esiste (era solo dal vivo); niente da svuotare.
- Test: `test_ortofoto.py` (TOML e priorità, URL `/tile` e `exportImage`, anno più recente con una sola chiamata e copia
  con il file degli anni, anno precedente e memoria delle zone vuote, 404 come «non ha volato», confine composto, mare
  vuoto, errori, componi).

## Ricerca di un luogo: particella del civico e metà della via (17/11/2026)

Segnalazione di Paolo: cercando un indirizzo nelle mappe la posizione era spesso lontana da quella vera. **Prima** la ricerca
(`cerca_luogo.js` → `POST /api/patrimonio`) andava sul punto della riga a zoom fisso 17: con il civico sull'**accesso**
ANNCSU (il portone; Rimini, viale Settembrini 2: l'accesso «2» è all'angolo sud dell'ospedale Infermi, l'ospedale 300–500 m
più a nord, fuori dalla vista), senza civico sul **civico di numero mediano** o sul punto della via dato da Zornade (Rimini,
via Coriano: 8,7 km di strada, a zoom 17 se ne vedono ~800 m), con una via inesistente sul punto di Zornade anche lontano
(Perugia, «via Sant'Andrea delle Fratte», che è una frazione: 2,5 km a nord, senza avviso).

**Ora** la pagina manda anche il campo `luogo=1`; con una sola riga e `LUOGO=true` la rotta, dopo la geolocalizzazione di
sempre, chiama `servizio/luogo.py` (logica in `fase7-territorio/territorio/luogo.py`) e aggiunge alla riga (nessun campo
tolto o cambiato): `luogo_regola`, `luogo_tipo` (`particella`, `via`, `località` o null), `luogo_lat`, `luogo_lon` (segnaposto),
`luogo_riquadro` ([ovest, sud, est, nord] da inquadrare), `luogo_fonte`, `luogo_avviso` (testo breve se una fonte non
risponde), `particella_ade` (riferimento, foglio, mappale, superficie, riquadro, distanza), `vie_candidate` (vie e località
fra cui scegliere, con `etichetta`), `scegli_via`, `via_scelta`; `fonti` della risposta comprende le fonti nuove.
- **Civico, foglio e particella**: particella che contiene il punto dalla **cartografia catastale dell'Agenzia delle Entrate,
  servizio WFS INSPIRE** (`CATASTO_WFS_URL`, CC BY 4.0, nessuna chiave: stesso ente e licenza del WMS dello strato
  «Particelle»): una GetFeature su un quadrato di 30 m attorno al punto; particelle «STRADA…» e «ACQUA…» escluse; punto
  sulla strada → la particella più vicina entro 15 m, preferendo quella scelta da Zornade. Segnaposto su un **punto interno
  garantito** (baricentro, o centro del tratto interno più largo per le particelle a L); riquadro della particella (la pagina
  aggiunge il margine). **Civico con più accessi** ANNCSU (2, 2/B … 2/O entro 600 m) cercato senza esponente: fra le
  particelle che contengono gli accessi **la più grande** (decisione di Paolo del 17/11/2026, «scelta B»: a Rimini, viale
  Settembrini 2, la particella n. 1 dell'ospedale Infermi, 10,6 ettari, non quella dell'accesso «2» all'angolo sud); **una
  sola** GetFeature sul riquadro degli accessi più 20 m (COUNT 500), accessi assegnati alle particelle in locale; se il
  riquadro supera 640 m di lato, o il WFS lo rifiuta due volte («Richiesta non valida», capita a tratti) o lo tronca, una
  richiesta per accesso, al più 4 insieme (al più 16 accessi). `particella_ade` porta `accessi` e `richiesta_wfs`
  (`riquadro` o `per_accesso`). Prova dal vivo del 17/11/2026: 0,8–5,4 s (1–2 richieste) contro 11,7–14,5 s (15 richieste in
  fila) della prima versione; il ripiego per accesso 4,8–7,9 s. Un solo accesso, o
  l'esponente scritto («2/B»): la particella di quell'accesso. Campo `luogo_regola`: `particella_piu_grande_del_civico`,
  `particella_del_civico`, `particella_dell_accesso`, `particella_del_punto` (foglio e particella, coordinate, punto di
  Zornade), `meta_della_via`, `località`.
- **Via senza civico**: strade di OpenStreetMap con quel nome nel comune da **Overpass** (filtro su `ref:ISTAT` e sulle
  parole del nome, solo `highway` stradali: niente sentieri e ciclabili; con le località `place`) più i civici ANNCSU della
  via; **metà della lunghezza** lungo la via (catena dei tratti, o il punto che lascia metà della lunghezza da ciascuna parte
  lungo l'asse principale se ci sono diramazioni), riquadro della via; tratti a più di 1 km sono vie diverse (frazioni).
- **Più vie compatibili** (stesso nome in frazioni diverse; via non riconosciuta, anche con il civico, ma vie simili o una
  località con quel nome): `scegli_via = true` e l'elenco; la pagina non sposta la mappa e fa scegliere.
- Protezioni: limite per IP `luogo` (`LUOGO_ORA`, 300 ricerche all'ora, controllato prima di geolocalizzare), tetto per tutto
  il sito `CATASTO_WFS_TETTO_ORA` (3.000 chiamate all'ora al WFS) e, per Overpass, il contatore `overpass` comune al ripiego
  OSM (`EDIFICI_OSM_TETTO_ORA`); una chiamata alla volta per fonte (attesa al più `LUOGO_ATTESA_S`, 10 s), ciascuna al più
  `LUOGO_TIMEOUT_S` (20 s); copia in memoria delle risposte per `LUOGO_COPIA_ORE` (24) ore. A Overpass vanno solo il codice
  ISTAT e le parole del nome della via, al WFS un quadrato di 30 m: mai chi cerca. Fonte giù o tetto pieno: la riga resta
  com'era, con `luogo_avviso`. `LUOGO=false` nel `.env` spegne tutto (comportamento di prima).
- Prove: `tests/test_luogo.py` (fonti simulate, rotta con Zornade finto); logica in `fase7-territorio/tests/test_luogo.py`;
  pagine in `fase5-sito/tests/test_ricerca_luogo_browser.py`. Prove dal vivo del 17/11/2026 nel README della fase 7.

## Regola dei file Excel (16/11/2026)

Excel e ODS dei report (`servizio/report.py`) e di Dati climatici (`servizio/storici.py`) rispettano la regola di Paolo
(obbligo della licenza CC BY 4.0): la citazione «Fonte: EuGEnio – eugenio.statocritico.it» (nei report con «, report
del gg/mm/aaaa») sta **in riga 1 di ogni foglio**, **sotto ogni grafico** (oggi nessun grafico negli Excel: i grafici
sono solo nel PDF, un test lo controlla) e **nel piè di pagina di stampa** di ogni pagina (`oddFooter.left` in openpyxl,
piè dello stile di pagina «Default» negli ODS). Nei fogli di dati le intestazioni stanno in **riga 2**, righe 1–2 ripetute
in stampa, riquadro bloccato in A3 (solo Excel). `tabelle.in_csv` (`/api/converti`, Previsioni, Patrimonio) salta una
prima riga che contiene solo «Fonte: EuGEnio…», così un file di EuGEnio ricaricato funziona come prima. Prove:
`test_report.py` (`test_regola_file_excel_xlsx/ods`), `test_storici.py` (`test_regola_excel_xlsx/ods`),
`test_tabelle.py`. La fixture di `test_protezione.py` ha anche il segnaposto `meteo_storico.psicro`.

## Aggiunte del 14/11/2026 (archivio psicrometrico e scelte di serie)

- Rotte `/api/psicro/disponibilita/{istat}` e `/api/psicro/serie/{istat}?anni=1|2|5|10|20|0` per il menu «Trattamento
  aria» (`servizio/psicro.py`), limite proprio `PSICRO_ORA`, ripiego sulla serie oraria ICON finché l'archivio dal 1940
  non è sul server; lavoro notturno `psicro` nel worker dopo lo storico. Dettagli: § «Archivio psicrometrico».
- `/api/clima-legge10` accetta `anni` da 1 a 30 e 0 (tutte le stagioni); i Dati storici «Legge 10» `stagioni` da 0 a 30.
- Variabili nuove nel `.env`: `CARTELLA_PSICRO`, `PSICRO_ORA`, `PSICRO_S3`, `PSICRO_GIORNI_MAX`. Caddy comprime già le
  risposte JSON di `/api/*` (`encode zstd gzip`): nessuna modifica al Caddyfile.

## Correzioni del 09/11/2026 e (`?v=20261109e`, procedura T di `AGGIORNAMENTO_2026-11-09e.md`)

- **Gettone di sessione della verifica anti-robot** (`servizio/protezione.py`, `rete_sessione`): legato a rete (IPv4, IPv6
  /64) **e browser** (User-Agent, solo come impronta firmata), `SESSIONE_MINUTI` predefinito **60** (prima 30). Con
  `SESSIONE_CHIAVE` nel `.env` (passo T5) i gettoni restano validi dopo un riavvio dell'api; senza, la chiave casuale cambia a
  ogni avvio e ogni rebuild rifaceva la verifica a tutti. La pagina tiene il gettone in `localStorage` (fase 5): Turnstile al
  più una volta all'ora per browser. La protezione non si indebolisce: stesso Turnstile, stessa firma HMAC, legame più
  stretto (anche il browser). Alternativa non fatta: la «pre-clearance» di Turnstile (cookie `cf_clearance` di Cloudflare),
  che richiede regole WAF e cambia il modo di proteggere le rotte.
- Test: `test_edifici_osm.py` (gettone di un altro browser rifiutato).

## Correzioni del 09/11/2026 d (`?v=20261109d`, procedura S di `AGGIORNAMENTO_2026-11-09d.md`)

- **Strati, origine dei 503** (prove Q8: «errori console piovono», decine di `GET …/api/ortofoto/strati/catasto/18|19/… 503`):
  erano **nostri**, non dell'Agenzia delle Entrate né del limite per IP: la rotta degli strati era ancora sincrona e, dopo
  `ORTOFOTO_ATTESA_S` secondi di attesa del turno (catasto: 2 chiamate al secondo per tutto il sito), rispondeva 503 «Fonte
  dello strato molto richiesta»; i 502 erano errori o lentezze della fonte. Ora `servizio/strati.py` fa come le ortofoto della
  c: rotta asincrona, chiamata alla fonte al più `ORTOFOTO_TIMEOUT_S`, semaforo per strato, **tessera vuota pulita** (200,
  `no-store`, `X-Ortofoto-Errore: fonte|occupata|ferma`, `Retry-After`; per lo strato OSM una FeatureCollection vuota),
  strato fermo dopo errori ripetuti (`strati.guasti`). In più **tutte le tessere del blocco 2×2** chiesto all'Agenzia vanno in
  copia (prima solo quella chiesta: le altre tre si richiedevano una per una, quattro volte le chiamate). Particelle fino
  allo zoom 19 (prima 20).
- **Terreno**: attesa del turno asincrona fino a 20 s (prima un thread fermo e 503 dopo `TERRENO_ATTESA_S`), generazione in
  un thread; il 503 resta solo per un server sommerso (una tessera del terreno vuota sarebbe una quota sbagliata).
- **Ortofoto**: `ORTOFOTO_TIMEOUT_S` predefinito **18 s** (prima 12; in Q5 AGEA 2012 dal server dava 32 tessere «fonte» su
  40); nel registro il tempo di ogni errore («ReadTimeout dopo 18,0 s» = lenta, pochi decimi = rifiuto o rete).
- **Alberi indicativi da OpenStreetMap** (`servizio/alberi_osm.py`, nuovo): `GET /api/alberi/osm/{i}_{j}.json`, cella di
  0,01° come `lidar/alberi/`; `natural=tree` (altezza da `height`/`est_height` o 8 m, chioma da `diameter_crown` o 5 m) e
  `natural=tree_row` (una chioma ogni 6 m); boschi non usati; ODbL 1.0, `"stima": true`; limite `edifici_osm` e tetto di
  Overpass, copia su disco (`CARTELLA_ORTOFOTO/alberi_osm/`), cella vuota pulita se Overpass non risponde. La pagina la
  chiede solo per le celle senza LiDAR e solo con «Alberi» acceso.
- Test: `test_strati.py` (errore pulito, blocco intero in copia, turno mancato, strato fermo), `test_alberi_osm.py` (nuovo).

## Correzioni del 09/11/2026 c (`?v=20261109c`, procedura Q di `AGGIORNAMENTO_2026-11-09c.md`)

- **Ortofoto, errori della fonte** (`servizio/ortofoto.py`, prove P9: «502 Bad Gateway» a raffica di AGEA 2012 e ortofoto
  «a pezzi»): la rotta delle tessere è **asincrona** (`async def tessera`, `asyncio.sleep` per il turno, `httpx.AsyncClient`;
  prima ogni tessera in attesa del turno teneva un thread: con 40 thread fermi le richieste in coda superavano i 30 s di
  `read_timeout` di Caddy, che rispondeva 502); chiamata alla fonte al più `ORTOFOTO_TIMEOUT_S` (12 s, nuovo, facoltativo nel
  `.env`); al più `2 × ritmo.al_secondo` chiamate in volo per fonte. Un errore della fonte (timeout, rete, 5xx, XML
  d'errore, immagine illeggibile) o il turno non arrivato in tempo danno una **tessera vuota pulita**: 200, PNG trasparente,
  `Cache-Control: no-store`, `X-Ortofoto-Errore: fonte|occupata|ferma`, `Retry-After` (prima 502 e 503). Dopo 6 errori di fila
  in 60 s la fonte è **ferma** 60 s (poi 120, fino a 5 minuti; una risposta buona azzera): tessere vuote subito, senza
  chiamarla e senza contarle nel limite. La pagina conta gli errori e scrive la nota sotto la mappa (fase 5, `protezione.js`).
- **Zoom massimi reali** (TOML della fase 10): regionali a 20 cm 19 (prima 20), AGEA 2012 18 (prima 19), Sentinel-2 15.
- Test: `test_ortofoto.py` (errore pulito e turno mancato, fonte ferma dopo errori ripetuti e timeout, fermo che raddoppia).

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
  <cartella delle tavole> --uscita /dati/terreno/dtm5_veneto_tv.tif` (passo J5 bis; procedura completa e permessi in
  «Come si aggiunge un DTM sul server», più sotto). Test
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
| GET | `/api/clima-legge10/{istat}?anni=10` | dati climatici aggiornati per la Legge 10 dal clima reale del comune. `anni` = ultime stagioni complete, da 1 a 30 (predefinito 10), **0 = tutte** quelle dell'archivio giornaliero (14/11/2026; prima 3–30). La risposta dice `stagioni_richieste`, `stagioni_disponibili`, `prima_stagione_disponibile` e in `note` se le stagioni usate sono meno di quelle chieste o meno di 5 (valori indicativi, tendenza vuota) |
| GET | `/api/psicro/disponibilita/{istat}` | (14/11/2026, menu «Trattamento aria») periodo coperto (`dal`, `al` in UTC), `anni_completi`, `anni_scelte`, quota del punto meteo e `pressione_pa` (atmosfera standard), `archivio` (`psicro` o `orario_icon`), fonte, licenza, note; limite «dati» |
| GET | `/api/psicro/serie/{istat}?anni=1\|2\|5\|10\|20\|0` | (14/11/2026) serie oraria **continua in UTC** degli ultimi anni×12 mesi fino all'ultima ora (0 = tutta la serie dal 1940): `inizio`, `passo_h`: 1, `n`, `t` (decimi di °C interi o `null`), `ur` (% interi o `null`), `dal`, `al`, `anni_richiesti`, `anni_dati`, `fonte`, `licenza`, `note`. Archivio `CARTELLA_PSICRO/<istat>.parquet` (fase 3, `scarica-psicro`); finché manca, la serie oraria ICON del server (`/dati/orario`, dal 14/11/2022) con la nota; senza nessuna delle due 503; 422 per altri `anni`. Limiti «dati» e `psicro` (`PSICRO_ORA`, 120 serie per IP all'ora); copia in memoria delle ultime 16 risposte (rinnovata quando il file cambia). Una serie dal 1940 è ~5,5 MB di JSON, ~1,2–1,5 MB compressa da Caddy (`encode zstd gzip`, già attivo su `/api/*`) |
| GET | `/api/rete/stato` | (17/11/2026) ultimi aggiornamenti di saturazione e interruzioni, interruzioni attive, province senza dato (`province_mancanti`, es. Torino) o non aggiornate, inizio della raccolta, tabella di raccordo, regola della criticità, fonti e licenze; `Cache-Control` 60 s |
| GET | `/api/rete/cabine?regione=RR` | (17/11/2026) GeoJSON di punti delle cabine primarie con posizione (tabella di raccordo, ODbL): campi del raccordo più `livello` (peggiore tra i trasformatori, `null` = altro gestore o senza dato), `trasf`, `data_saturazione`; `senza_posizione`, `attribuzione`, `licenza`, `licenze`; 30 minuti |
| GET | `/api/rete/comuni?regione=RR` | (17/11/2026) elenco dei comuni (tutta Italia senza `regione`) con `concessionario`, `servito_in_parte`, `pieno`, `strisce`, `livello`, `quota`, `trasf`, `cabine`, `data`, `dato_disponibile` (regola del contratto, `rete.classe_comune`); 30 minuti |
| GET | `/api/rete/cabine/comune/{istat}` | (17/11/2026) cabine che servono il comune (anche quelle di altri gestori dal raccordo), trasformatori del comune con livello, montanti e sezioni, criticità; 30 minuti |
| GET | `/api/rete/interruzioni/attive?regione=RR\|bbox=…` | (17/11/2026) GeoJSON di punti delle interruzioni in corso (punto della cabina secondaria con più clienti), `durata_finora_min`; 2 minuti |
| GET | `/api/rete/interruzioni/comune/{istat}?da=aaaa-mm&a=aaaa-mm` | (17/11/2026) statistiche del comune: `dal`, `totale`, `per_mese`, `per_causa`, `per_codice_causa`, `attive`, `ultime` (50); 5 minuti |
| POST | `/api/patrimonio` | CSV di edifici → particella catastale, comune, punto (max 500 righe per richiesta, 2.000 edifici l'ora per IP; il sito manda blocchi di 40); indirizzi prima con ANNCSU, poi con Zornade; CSV in UTF-8 o nella codifica di Windows; la risposta porta `fonti` da citare |

| POST | `/api/patrimonio` | CSV di edifici → particella catastale, comune, punto (max 500 righe per richiesta, 2.000 edifici l'ora per IP; il sito manda blocchi di 40); indirizzi prima con ANNCSU, poi con Zornade; CSV in UTF-8 o nella codifica di Windows; la risposta porta `fonti` da citare. Con `luogo=1` e una riga (ricerca delle pagine di mappa, 17/11/2026) campi in più: particella del civico, metà della via, vie fra cui scegliere (§ «Ricerca di un luogo») |
| POST | `/api/report?formato=pdf\|xlsx\|ods` | documento generico in JSON (schema in `/api/report/schema`) → file PDF, Excel o ODS; `docx` e `odt` rispondono 410 (spenti dal 28/10/2026); vedi "Report" |
| POST | `/api/report/{tipo}?formato=pdf\|xlsx\|ods` | `tipo` = `previsione`, `legge10`, `patrimonio`, `indicatori`, `valori_sedi`, `edificio` (dal 04/11/2026: pagina 3D, vedi `report_servizi.report_edificio`): il corpo è la risposta già ricevuta dal servizio → file del report |
| GET | `/api/edifici/gradi-giorno/{istat}?dal=AAAA-MM&al=AAAA-MM` | (04/11/2026, fase 10) gradi giorno mensili reali (base 20 °C e 24 °C) e temperatura media dall'archivio giornaliero, per la firma energetica; 503 finché manca l'archivio |
| GET | `/api/edifici/clima-orario/{istat}?anno=AAAA` | (04/11/2026, fase 10) un anno orario di radiazione globale e diffusa, temperatura e vento dall'archivio orario del comune, per la producibilità FV nel browser; 503 finché manca l'archivio |
| GET | `/api/ortofoto/fonti` | (04/11/2026, Fase B) fonti delle ortofoto accese, con licenza, citazione, stato («confermata», «da confermare»), zoom, riquadro e modello d'indirizzo delle tessere |
| GET | `/api/ortofoto/{fonte}/{z}/{x}/{y}.jpg` | (Fase B) tessera 256×256 in web mercator dal proxy con copia su disco (`servizio/ortofoto.py`); 404 fuori zona o per una fonte spenta, 502 se la fonte risponde con un errore, 503 se il ritmo verso la fonte è esaurito; **`?de=<m>&dn=<m>`** (08/11/2026, interi ±20, solo fonti WMS: `spostabile` in `/fonti`): ortofoto spostata di de m a est e dn m a nord rispetto alla cartografia, per le frecce sotto la mappa. Il proxy chiede alla fonte il BBOX della tessera spostato di (−de, −dn) m sul terreno in EPSG:3857 (scala locale dell'ellissoide WGS84 al centro della tessera, `bbox_spostato`; scarto < 1 cm, nessuna riproiezione); **nessuna copia su disco** (ogni passo da 1 m è un'altra serie di tessere usata da una sola persona: con la copia `ORTOFOTO_MAX_GB` si riempirebbe e la pulizia toglierebbe le tessere normali), `Cache-Control` di un giorno, `X-Ortofoto-Copia: no`, `X-Ortofoto-Spostamento`; contano ritmo e limite per IP come le altre; 422 fuori dai limiti, 400 per le fonti XYZ (Sentinel-2) |
| GET | `/api/ortofoto/strati` | (05/11/2026, seconda pubblicazione) strati sopra le ortofoto accesi (`servizio/strati.py`): tema (`particelle`, `edifici`), regioni, licenza, citazione, colore, legenda, zoom, riquadro e modello d'indirizzo delle tessere |
| GET | `/api/ortofoto/strati/{id}/{z}/{x}/{y}.png` | tessera **trasparente** 256×256 in web mercator: particelle catastali dell'Agenzia delle Entrate (WMS in EPSG:4258 riproiettato), contorni degli edifici del DBTR; solo linee, ricolorate; copia su disco, ritmo e limite come le ortofoto; 404 fuori zona o zoom, 502 se la fonte sbaglia, 503 col ritmo esaurito |
| GET | `/api/ortofoto/strati/osm_edifici/16/{x}/{y}.json` | sagome degli edifici di OpenStreetMap (ODbL) della tessera z16, in GeoJSON, dall'API Overpass, con copia su disco |
| GET | `/api/terreno/{z}/{x}/{y}.png` | (07/11/2026) **terreno della pagina 3D su richiesta** (`servizio/terreno.py`): tessera Terrarium 256×256 (zoom 8–15) letta a finestra dal COG del DTM 5 m in `/dati/terreno` (comando `dtm-server` della fase 10), poi (19/11/2026) il DTM nazionale **HR-DTM-5m** del CNR-IRPI letto a distanza da Zenodo, in mare e senza rete Copernicus DEM 90 m, se nemmeno quello tessera piatta dichiarata; copia su disco, `X-Terreno-Fonte`, Cache-Control 30 giorni; limite `terreno` solo sulle tessere da generare; 404 fuori dall'Italia o con `TERRENO_ATTIVO=false` |
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
| POST | `/api/storici/estrai?formato=csv\|xlsx\|ods` | stesso JSON → file CSV (in streaming), Excel o OpenDocument (.ods) con foglio "Info" (dal 16/11/2026 citazione in riga 1 di ogni foglio, intestazioni in riga 2) |

## Stato della rete elettrica (17/11/2026)

Modulo `servizio/rete.py` (contratto comune dei tre agenti, decisioni di Paolo del 17/11/2026). Il **worker** scrive, le
**rotte** leggono; le pagine sono «Statistiche › Stato della rete elettrica» e «Fotovoltaico › Cabine primarie».

**Database** `RETE_DB` (predefinito `/dati/rete/rete.sqlite` = `/srv/energia/dati/rete/rete.sqlite` sul server; cartella
dell'utente 1000). Schema versionato con `PRAGMA user_version` (oggi 1), creato dal worker al primo lavoro; giornale WAL
(il worker scrive mentre l'api legge); le rotte aprono in sola lettura (`query_only`) e rispondono 503 finché il file non
c'è (non lo creano mai).

| tabella | contenuto |
|---|---|
| `meta` | `saturazione_aggiornata`, `interruzioni_aggiornate`, `raccolta_dal`, `comuni_ed_aggiornati`, `saturazione_ultimo_giro` (esito della notte), `avviso_province` |
| `province` | `ProvinceCritiche_View`: codice ISTAT a 3 cifre, nome, regione (codice ISTAT a 2 cifre da `f1`), livelli di criticità della provincia |
| `comuni_ed` | `View_ComuniGestitiED2021Is`: ISTAT 2021, ISTAT attuale (uguale se esiste ancora, altrimenti per nome nella stessa regione, `NULL` se non si trova), nome, `servitoed` (0 = il distributore è un altro) |
| `saturazione` | `comuniServiti`: una riga per mese, comune, cabina primaria, trasformatore, montante e sezione, con il livello. **Una fotografia per mese e provincia**: l'ultima lettura riuscita del mese sostituisce quella di prima, i mesi passati restano (storico mensile) |
| `saturazione_province` | mese, provincia, ora della lettura, comuni e righe lette |
| `tentativi_province` | ultimo tentativo per provincia, esito, errore (mai il gettone), ultima lettura riuscita, `in_errore_dal` (primo errore dopo l'ultima lettura riuscita) |
| `interruzioni` | una riga per `id_interruzione`: cause (`causa_disalimentazione`, codice `causa_interruzione`), inizio e ripristino previsto in ISO (ora italiana) o il testo («In corso di definizione»), comune principale (cabina secondaria con più clienti) e tutti i comuni, punto, **clienti = massimo visto** della somma sulle cabine secondarie, `prima_lettura`, `ultima_lettura`, `chiusa_il` (prima lettura completa in cui non compare più; si riapre se ricompare) |
| `interruzioni_cs` | una riga per interruzione e cabina secondaria (`cod_cs`): comune, punto, clienti massimi |
| `letture` | una riga per lettura delle interruzioni: esito (`ok`, `sospetta`, `errore`), righe, nuove, chiuse, durata (tenute 400 giorni) |

**Interruzioni** (`rete-interruzioni`, thread a parte nel worker, così i lavori lunghi della notte non le fermano): ai
minuti 3, 18, 33, 48 di ogni ora (la mappa di e-distribuzione si aggiorna al minuto 1) tutte le righe dello strato
`ITA_power_cut_map_layer_View/FeatureServer/0` a pagine di 1.000. Un `id_interruzione` può avere più righe (una per
cabina secondaria, anche in comuni diversi). Una lettura senza righe mentre ne erano aperte almeno 10 è «sospetta» e
non chiude nulla. **Durata stimata** = ultima lettura in cui compare − `data_interruzione` (dichiarata nelle risposte,
errore fino a una lettura).

**Saturazione** (`rete-saturazione`, ogni notte alle `RETE_SATURAZIONE_ORA` = 01:15, prima dei mercati delle 2:30, del
LiDAR delle 3:30 e dell'aggiornamento da GitHub delle 4:40; subito alla prima accensione se il database non ne ha):
pagina delle Aree critiche (biscotti), elenco delle province, comuni gestiti, poi per ogni provincia gettone nuovo
(`tokenservice`) e `comuniServiti`, con le intestazioni `Origin` e `Referer` della pagina e una pausa di `RETE_PAUSA_S`
(mai meno di 4 s); le province fallite si ritentano alla fine due volte (pausa 15 s) e di nuovo la notte dopo (Torino
oggi risponde 500: `province_mancanti`, la pagina dice «dato non disponibile»). **Il gettone non viene mai scritto**:
né nei log (httpx registra solo l'indirizzo), né negli errori (solo codici e stati HTTP), né nel database. ~110 province
in ~10 minuti. Se il giro si ferma prima delle province (elenco non letto), tutte le province note contano come fallite.

**Criticità** (`rete.classe_comune`, copia identica di `fase7-territorio/territorio/cabine.py` del ramo dei dati, **da
unificare**): trasformatori distinti (cabina, trasformatore) che servono il comune, L = livello più alto, q = quota con L;
L = VERDE nessun riempimento, q > 0,5 colore pieno, altrimenti strisce `[livello precedente, L]` (dettagli nel contratto).
Livello della cabina = peggiore tra i suoi trasformatori (VERDE si disegna bianco; `null` = grigio). Fotografia attuale =
ultimo mese riuscito di ogni provincia; calcolo tenuto in memoria finché database, raccordo o elenco dei comuni non
cambiano.

**Tabella di raccordo** `RETE_RACCORDO` (predefinita accanto al database, `raccordo_cp.csv` dell'agente dati: `cod_ac,
gestore, cod_cp_ed, nome_cp_ed, comuni_serviti, osm_id, osm_nome, lat, lon, punteggio_nome, distanza_m, esito,
data_raccordo, versione_ac`): dà posizione (OSM, **ODbL**), `COD_AC` e gestore. Le cabine e-distribuzione senza riga
restano senza posizione (contate in `senza_posizione`, presenti in `/cabine/comune/…` con `lat` nullo); le righe senza
codice e-distribuzione (`solo_gse`, altri gestori) compaiono grigie. Riletta da sola quando il file cambia. Regione di un
comune: `DATI/comuni.parquet` (fase 3), altrimenti la provincia da `ProvinceCritiche`.

**Comuni serviti in parte** (decisione di Paolo del 17/11/2026): un comune con trasformatori e-distribuzione nel dato
mensile non è mai «non concessionario». I 35 comuni (soprattutto milanesi) che `View_ComuniGestitiED2021Is` segna
`servitoed = 0` ma che compaiono in `comuniServiti` hanno `concessionario: true` e `servito_in_parte: true`: la pagina li
colora con la loro criticità (niente retino) e scrive «servito in parte da un altro distributore» (`nota` in
`/cabine/comune/…`, `nota_servito_in_parte` in `/stato`). Non concessionari (retino) = `servitoed = 0` senza trasformatori.

**Licenze nelle risposte**: «Fonte: e-distribuzione S.p.A., mappa delle Aree critiche e mappa delle interruzioni» (uso non
commerciale, rimozione su richiesta); posizioni «© contributori OpenStreetMap», ODbL 1.0; codici `COD_AC` del GSE senza
geometrie (i perimetri si leggono solo dal browser); criticità «classificazione di EuGEnio». `/api/rete/comuni` è un
elenco (forma del contratto): fonti e licenze stanno in `/api/rete/stato`.

**Email all'amministratore** (decisione di Paolo del 17/11/2026) **solo** in due casi, una volta per episodio (si
riarmano quando la condizione cessa): (a) le interruzioni **non si leggono da più di 72 ore consecutive** (dall'ultima
lettura riuscita, `meta.interruzioni_aggiornate`); (b) **più di 5 province** non sono aggiornate con successo da più di
72 ore consecutive (`tentativi_province.in_errore_dal`, primo errore dopo l'ultima lettura riuscita; controllo dopo ogni
giro notturno, stato dell'avviso in `meta.avviso_province`). Nessun'altra email: né per letture fallite più brevi, né
quando riparte, né per Torino da sola, né per un giro notturno fallito (solo nel registro; la saturazione non passa da
`_sicuro`). Soglie: `RETE_AVVISO_ORE` (72) e `RETE_AVVISO_PROVINCE` (5).

**Protezione**: letture leggere, senza Turnstile; limite proprio `rete` (`RETE_ORA`, 1.200 richieste per IP all'ora);
`Cache-Control: public` da 1 minuto (stato) a 30 minuti (cabine, comuni).

**Variabili** (tutte facoltative): `RETE_DB`, `RETE_RACCORDO`, `RETE_ATTIVA` (false spegne i due lavori), `RETE_INTERRUZIONI_MIN`
(15, minimo 5), `RETE_SATURAZIONE_ORA` (01:15), `RETE_PAUSA_S` (4, minimo 4), `RETE_ORA` (1200), `RETE_AVVISO_ORE` (72), `RETE_AVVISO_PROVINCE` (5);
(20/11/2026) `GSE_CONTROLLO_GIORNO` (3) e `GSE_CONTROLLO_ORA` (7) per il controllo mensile del servizio del GSE.

**A mano**: `docker compose run --rm worker python -m servizio.worker rete-interruzioni` (o `rete-saturazione`, ~10
minuti). **Prove**: `tests/test_rete.py` (regola, interruzioni a pagine con chiusura, riapertura e lettura sospetta,
saturazione con Torino in errore, ritentativi, pause, gettone mai registrato, fotografia mensile, rotte e 503/422/429) e
`tests/test_worker.py` (orari delle letture, email solo oltre le 72 ore, più di 5 province ferme, una per episodio).

## Dati di Terna (20/11/2026)

Dati di Terna per le pagine «Produzione e consumi di elettricità» (statistiche annuali) e «Carichi elettrici» (serie
quartorarie) e per le analisi future. **Decisione di Paolo**: si caricano sul server per le elaborazioni del sito ma
**non si scaricano** dal sito e **mai nel repository** (`.gitignore`: `fase5-sito/sito/dati/elettricita/`,
`fase5-sito/sito/dati/carichi/`). **Niente dati di prezzo o di mercato di Terna** (cataloghi Market e Fees: prezzi,
corrispettivi, MSD): restano esclusi come GME ed EEX; una prova controlla che il modulo non li chiami.

### Lavori

| lavoro | quando | cosa fa | richieste |
|---|---|---|---|
| `terna-api` | ogni giorno dalle **06:30** (`TERNA_API_ORA`, ora italiana) | 1) **API ufficiale** (se ci sono le chiavi): il giorno prima (e quelli rimasti indietro, al più `TERNA_API_GIORNI_MAX` = 7) per `load/v2.0/total-load`, `load/v2.0/market-load`, `load/v2.0/peak-valley-load`, `generation/v2.0/actual-generation`, `generation/v2.0/renewable-generation`, `generation/v2.0/energy-balance` (`dateFrom`=`dateTo`=gg/mm/aaaa, carico di tutte le zone senza filtro); l'**IMCEI** (`load/v2.0/monthly-index-industrial-electrical-consumption`, `year`, `month`) dal 2021 fino al primo mese recente non ancora pubblicato (i mesi vecchi senza dati si saltano), poi una prova al giorno dal 20 del mese (`TERNA_IMCEI_GIORNO`). 2) **Storico dal Download Center** (senza chiave, non consuma la quota): `TERNA_STORICO_MESI` (6) mesi per serie al giorno dal `TERNA_STORICO_INIZIO` (2021-01), ripreso da dove era rimasto, solo mesi finiti (un mese entra appena finisce). 3) **Riserva**: se un mese dello storico non arriva dal Download Center lo si chiede all'API (una richiesta per serie e mese, se c'è quota); se l'API non è configurata o non ha risposto, il mese in corso si legge dal Download Center. 4) Se l'archivio è cambiato, il lavoro `carichi` | API: 6 al giorno + 1 token (~7; il primo giorno ~55 con gli ultimi 7 giorni e 12 mesi di IMCEI; recupero dell'IMCEI ≤ 12 al giorno per ~6 giorni); Download Center: ~36 nei giorni dello storico (~12 giorni per 2021→oggi), poi 6 il primo giorno del mese |
| `carichi` | subito dopo `terna-api`, se l'archivio è cambiato | se la fase 15 ha `costruisci_carichi(archivio, uscita)` (import protetto: `elettricita.carichi`, poi `elettricita.costruisci`; dal 20/11/2026 c'è e legge direttamente l'archivio Parquet `carico_totale`, `produzione`, `rinnovabili`), la chiama con `/dati/terna/serie` e `/sito/dati/.carichi_nuova` e pubblica in `/sito/dati/carichi` con `_pubblica` se il controllo passa (almeno un JSON, non meno del 90 % di prima); se non c'è o solleva `NotImplementedError`, riga nel registro e niente pubblicato | nessuna |
| `elettricita` | il **5 del mese dalle 05:00** (`ELETTRICITA_GIORNO`, `ELETTRICITA_ORA`); **subito** se `/dati/terna/statistiche` è vuota | `terna_dc.scarica(/dati/terna/statistiche, ultimi=2)` (fase 15: anni mancanti più gli ultimi due, provvisori → consolidati) e `costruisci(raw, /sito/dati/.elettricita_nuova)`; pubblica in `/sito/dati/elettricita` con `_pubblica` solo se c'è `italia.json` e i JSON non sono meno del 90 % di prima. `NotImplementedError` (costruttore non ancora pronto): avviso nel registro, niente pubblicato, nessuna email | Download Center, ~10–20 richieste al mese |

Tutti e tre si lanciano anche a mano: `docker compose run --rm worker python -m servizio.worker terna-api` (o
`elettricita`, `carichi`). Un solo `terna-api` alla volta (lucchetto `/dati/terna/.aggiorna.lock`): se il ciclo del worker
sta già lavorando, il lancio a mano scrive «un altro aggiornamento è in corso» e termina. Nel `worker_stato.json` le voci `terna_api` ed `elettricita` (una volta al giorno). Dopo un
**429 o un 5xx** di Terna il lavoro si ferma subito (nessuna ripetizione immediata, la quota non si brucia), lo stato non
avanza e il ciclo riprova dopo `TERNA_RIPROVA_MIN` (60) minuti, al più `TERNA_RIPROVA_MAX` (4) volte al giorno.

**Giorni mancanti** (22/11/2026, Paolo: nel Download Center mancavano il 14 e il 15 gennaio 2026 per carico e
produzione, e un mese con dei giorni vuoti entrava lo stesso senza più riprove). Dopo lo storico, `terna-api` controlla
una volta i mesi già archiviati di `carico_totale`, `produzione` e `rinnovabili` (`giorni_mancanti()`: giorni con meno
della metà degli istanti del giorno tipico del mese, vale per i dati orari e per quelli a 15 minuti). I mesi completi
vanno in `stato.json` → `buchi_controllati` e non si ricontrollano; quelli con dei giorni vuoti vanno in `buchi`
(`giorni`, `prove`, `ultima`) e si **riprovano una volta al giorno**, al più `TERNA_BUCHI_MESI` (3) mesi per giro: dall'API
giorno per giorno se è configurata e c'è quota (una richiesta per giorno), altrimenti il mese intero dal Download Center
(una richiesta). Recuperati: «giorni mancanti recuperati» nel registro e il mese passa tra i controllati (poi `carichi`
ricostruisce i file). Dopo `TERNA_BUCHI_PROVE` (14) prove il buco è `definitivo` (Terna non ha i dati: riga nel registro,
nessuna email) e la pagina lo mostra come «dati mancanti». `TERNA_BUCHI_MESI=0` spegne il controllo.

### API ufficiale: chiavi, limiti, errori

- Applicazione creata da Paolo su https://developer.terna.it (procedura in `../AGGIORNAMENTO_2026-11-20e.md`); **una
  sola**: mai altre chiavi per aggirare i limiti. `TERNA_CLIENT_ID` e `TERNA_CLIENT_SECRET` stanno **solo** nel `.env` del
  server (permessi 600), mai nel codice, nei documenti, nei registri. Senza le due chiavi la parte dell'API non parte
  (riga «TERNA_CLIENT_ID o TERNA_CLIENT_SECRET mancanti» nel registro, **nessuna email**); lo storico dal Download Center
  continua.
- Token: `POST https://api.terna.it/public-api/access-token` (`grant_type=client_credentials`, `client_id`,
  `client_secret`, form-urlencoded), valido 300 s, rinnovato 30 s prima della scadenza; poi
  `Authorization: Bearer <token>`. **401** → token nuovo e una sola ripetizione.
- Limiti di Terna: **1 richiesta al secondo, 300 al giorno**. Pausa minima `TERNA_PAUSA_S` (1,1 s, mai sotto 1, vale anche
  per il Download Center); contatore persistente `/dati/terna/quota_api.json` (`{"giorno": "AAAA-MM-GG", "richieste":
  n}`, giorno italiano, scritto **prima** di ogni richiesta, anche del token) con tetto `TERNA_API_TETTO` (250, mai sopra
  300); un giorno si scarica solo se restano almeno 7 richieste.
- Corpo vuoto (Terna risponde così ai parametri non riconosciuti, senza errore): riga nel registro, giorno considerato
  senza dati.

### Email all'amministratore

Solo per errori veri: (a) l'archivio non si aggiorna da più di `TERNA_AVVISO_GIORNI` (3) giorni — con le chiavi conta
l'API (chiavi scadute o revocate), senza conta il Download Center — una volta per episodio; (b) `elettricita`: il
Download Center non risponde in **due mesi diversi di fila**, oppure i file costruiti sono incompleti; (c) `carichi`: file
incompleti o errore del costruttore; (d) errore imprevisto del codice. Mai per le chiavi mancanti, per un 429 isolato, né
per i costruttori non ancora pronti.

### Cartelle

| sul server | nel container | cosa |
|---|---|---|
| `/srv/energia/dati/terna/serie/<serie>/<AAAA-MM>.parquet` | `/dati/terna/serie/…` | archivio delle serie (sotto) |
| `/srv/energia/dati/terna/statistiche/<Dataset>_<anno>.json` | `/dati/terna/statistiche/` | risposte del Download Center per le statistiche annuali (fase 15, `terna_dc`) |
| `/srv/energia/dati/terna/stato.json` | `/dati/terna/stato.json` | stato: mese successivo dello storico per serie (`dc`), ultimo giorno dall'API (`api_giorno`), IMCEI (`imcei`), ultimi aggiornamenti riusciti, avvisi |
| `/srv/energia/dati/terna/quota_api.json` | `/dati/terna/quota_api.json` | contatore delle richieste all'API di oggi |
| `/srv/energia/dati/terna/elettricita_stato.json` | idem | mesi in cui il Download Center non ha risposto (email al secondo) |
| `/srv/energia/sito/dati/elettricita/`, `/srv/energia/sito/dati/carichi/` | `/sito/dati/elettricita/`, `/sito/dati/carichi/` | file statici delle due pagine, scritti solo dal worker |

`/dati/terna` non è mai servita da Caddy.

## Suolo e aree agricole (22/11/2026)

Dati della pagina «Suolo e aree agricole» (Statistiche, sperimentale; fase 16, README in `../fase16-suolo/README.md`):
indicatori del consumo di suolo ISPRA/SNPA, stime delle superfici coltivate e censimento ISTAT, carte raster ISPRA per il
suolo agricolo consumato. Licenze CC BY 4.0 (dati Copernicus con attribuzione dentro la carta d'uso ISPRA): si possono
mostrare e rielaborare citando le fonti; per scelta di Paolo la pagina fa scaricare solo l'immagine. I file costruiti non
vanno nel repository (`.gitignore`: `fase5-sito/sito/dati/suolo/`).

| lavoro | quando | cosa fa | richieste |
|---|---|---|---|
| `suolo` | il **6 del mese dalle 05:30** (`SUOLO_GIORNO`, `SUOLO_ORA`); **subito** se `/sito/dati/suolo/italia.json` manca | `scarica.scarica(SUOLO_DATI, carte=SUOLO_CARTE)`: elenco della cartella «indicatori» del groupware SINAnet e file `consumo_suolo_<anno>_Com_Prov_Reg_Naz_v<x>.xlsx` con anno e versione più alti (riscaricato solo se il nome cambia), CSV SDMX ISTAT delle coltivazioni (dal 2006) e del censimento 2020 (impronta SHA-256), con `SUOLO_CARTE` la carta dei cambiamenti più recente e la carta di uso del suolo più recente; se la carta dei cambiamenti è nuova (o manca il suo `agricolo_<anno>.json`) l'incrocio `agricolo.agricolo` (~2 minuti, il file resta nell'archivio e la serie cresce di un anno a ogni edizione); poi, solo se qualcosa è cambiato, `costruisci(SUOLO_DATI, /sito/dati/.suolo_nuova, /sito/dati/mappa, /sito/dati/suolo/italia.json)` e `_pubblica` in `/sito/dati/suolo` se i controlli passano | groupware ISPRA: 1 pagina al mese, l'Excel (87 MB) a ogni nuova versione, le carte (~800 MB) una volta l'anno; ISTAT: 2 richieste SDMX al mese |

Controlli del costruttore (se uno non passa: niente pubblicato, restano i file di prima, email all'amministratore): somme
dei comuni = province = regioni = Italia (suolo consumato e consumo lordo, tolleranza 1 ha); tutti i comuni ISPRA abbinati
alle mappe del sito (i sardi per nome); ultimo anno = anno dell'edizione − 1; nessuna regione che cambi di più del 2 % in un
anno già pubblicato (nuova edizione con revisioni grandi: dopo un controllo, `python -m servizio.worker suolo-forza`). In
più `_controlla_cartella`: `italia.json` presente e non meno del 90 % dei JSON di prima. Email anche se le fonti non
rispondono in due mesi diversi di fila (`SUOLO_DATI/lavoro_stato.json`) e se l'incrocio agricolo fallisce (la pagina si
costruisce lo stesso, senza la parte nuova). Nel `worker_stato.json` la voce `suolo` (una volta al giorno).

| sul server | nel container | cosa |
|---|---|---|
| `/srv/energia/dati/suolo/` | `/dati/suolo/` (`SUOLO_DATI`) | `ispra_indicatori.xlsx`, `istat_coltivazioni.csv`, `istat_censimento2020.csv`, `stato_scarico.json`, `agricolo_<anno>.json`, `carte/` (due GeoTIFF, ~800 MB), `lavoro_stato.json` |
| `/srv/energia/sito/dati/suolo/` | `/sito/dati/suolo/` | `italia.json` e `RR.json` della pagina (~2 MB in tutto), scritti solo dal worker |

Prima messa in servizio (dopo la release che contiene questa parte): `docker compose run --rm worker python -m
servizio.worker suolo` (circa 5 minuti con le carte: scarico ~900 MB, lettura dell'Excel con openpyxl, incrocio), poi
controllare `https://eugenio.statocritico.it/suolo.html`.

### Formato dell'archivio (`/dati/terna/serie`)

Un file **Parquet per serie e mese** (`<AAAA-MM>.parquet`, mese **italiano** dell'istante), scritto in un file temporaneo
e poi rinominato; **deduplicato sulla chiave**, vince l'ultima riga scritta (il Download Center di fine mese sostituisce
le righe dell'API dello stesso istante). Righe ordinate per chiave.

| serie | fonte (API / Download Center) | chiave | colonne |
|---|---|---|---|
| `carico_totale` | `total-load` / `TotalLoad` | `istante`, `zona` | `carico_mw`, `previsione_mw` |
| `carico_mercato` | `market-load` / `MarketLoad` | `istante`, `zona` | `carico_mw`, `previsione_mw` |
| `picco_valle` | `peak-valley-load` / `PeakValleyLoad` | `istante`, `fonte` | `picco_gw`, `valle_gw`, `fonte_gw` |
| `produzione` | `actual-generation` / `ActualGeneration` | `istante`, `fonte` | `energia_gwh` |
| `rinnovabili` | `renewable-generation` / `RenewableGeneration` | `istante`, `fonte` | `energia_gwh` |
| `bilancio` | `energy-balance` / `EnergyBalance` | `istante`, `fonte` | `energia_gwh` |
| `imcei` | `monthly-index-industrial-electrical-consumption` (solo API) | `mese`, `regione`, `settore`, `tensione` | `indice`, `consumo_gwh` |

- `istante`: `timestamp[us, UTC]` (per l'ora italiana: `df.istante.dt.tz_convert("Europe/Rome")`); passo di 15 minuti
  (carichi, produzione, bilancio), un'ora per picco e valle del giorno. Dall'API: `date` + `date_offset` (esatto). Dal
  Download Center la data è l'ora locale senza fuso (millisecondi dall'1/1/0001): nell'**ora ripetuta di fine ottobre**
  Terna dà due righe con la stessa ora e in ordine qualsiasi; per ogni zona o fonte la riga più vicina al quarto d'ora
  precedente è l'ora legale (continuità), l'altra l'ora solare.
- `zona`: nomi inglesi di Terna — `Italy`, `North`, `Centre-North`, `Centre-South`, `South`, `Calabria`, `Sicily`,
  `Sardinia` (`Italy` è il totale: non sommarla alle zone).
- `fonte`: nomi inglesi di Terna — produzione: `Thermal`, `Hydro`, `Wind`, `Photovoltaic`, `Geothermal`,
  `Self-consumption`; rinnovabili: `Hydro`, `Wind`, `Photovoltaic`, `Geothermal`, `Biomass`; bilancio e picco/valle anche
  `Net Foreign Exchange`, `Pumping-consumption`. In `picco_valle` la riga con `fonte` vuota è il totale (picco o valle del
  giorno in GW, l'altro vuoto); le righe per fonte (solo Download Center) hanno la copertura in `fonte_gw`. Nel Download
  Center le colonne si chiamano «Peak Load [MW]» e «Valley Load [MW]» ma i valori sono GW (42,3 il 31/10/2025), come
  nell'API.
- `energia_gwh`: il valore come lo chiama Terna («GWh»); al passo di 15 minuti i valori corrispondono alla potenza media
  in GW (Thermal ~14 di notte): controllare l'unità prima di sommare.
- `imcei`: `mese` testo `AAAA-MM`; `regione`, `settore` (ALIMENTARE, ALTRI, CARTARIA, …), `tensione` (AT, MT).
- `origine`: `api` o `dc`. Numeri `float64` (i formati misti di Terna — `" 13"`, `"1.234,5"` — sono già convertiti),
  testi `string`. Leggere un anno: `pd.concat(pd.read_parquet(f) for f in sorted(Path(archivio, "carico_totale").glob("2025-*.parquet")))`.

### Prove

`tests/test_terna.py` (nessuna rete): quota con tetto e azzeramento il giorno dopo, tetto mai sopra 300, token nuovo dopo
un 401 e alla scadenza, 429/5xx senza ripetizioni, corpo vuoto, chiavi mai nel registro, quota esaurita, numeri misti,
date del Download Center, ora ripetuta di ottobre, picco/valle, deduplicazione, mese italiano, IMCEI, pagine del Download
Center, storico che riprende dallo stato, Download Center fermo, email dopo 3 giorni, aggiornamento giornaliero dall'API,
429 con riserva, primo avvio con 7 giorni, riserva dello storico dall'API, `elettricita` che non pubblica se `costruisci`
non è pronto o i file sono pochi (o manca `italia.json`), email dopo due mesi senza risposta, `carichi` assente/non
pronto/pubblicato, lavori nel ciclo e nei comandi, nessun catalogo di mercato, un aggiornamento alla volta, mesi vecchi dell'IMCEI senza dati saltati.

## Dati pluviometrici (22/11/2026)

Dati della pagina Clima e meteo › «Dati pluviometrici» (`pluviometria.html`, sperimentale), della casella «Pioggia
misurata» di «Stato della rete elettrica» e delle sezioni di pioggia della newsletter. Decisioni di Paolo del 22/11/2026:
**solo il «Merging»** del Dipartimento della Protezione Civile (radar corretto con i pluviometri: il radar da solo è poco
affidabile), **un dato ogni 30 minuti**, **fini statistici e non di allerta** (niente intensità istantanea, niente
bollettini di criticità, niente avvisi per email), libreria `dpc-radar`, archivio delle mappe per **10 anni** e valori per
comune **per sempre**, licenza **CC BY-SA 4.0** scritta accanto ai dati (pagina, immagini, file, email).

Fonte: API aperta `https://radar-api.protezionecivile.it` (senza account; sono le chiamate del visualizzatore del DPC, non
documentate: se cambiano, il worker manda un'email dopo `RADAR_AVVISO_ORE` ore senza giri riusciti e si aggiorna la
libreria). Il DPC tiene i frame circa 5 mesi: per questo EuGEnio si fa l'archivio.

| prodotto | cosa | griglia | usato per |
|---|---|---|---|
| `CUM3`, `CUM6`, `CUM12`, `CUM24` | pioggia delle 3/6/12/24 ore precedenti, mm | 0,01° (EPSG:4326) | ultimo dato (ogni 30 minuti), immagini della mappa, archivio (CUM3 e CUM24), valori per comune (CUM3 e CUM24) |

Giro del worker (`radar.giro`, ogni `RADAR_MIN` minuti, 4 minuti dopo il :00 e il :30):
1. ultimo frame di ogni prodotto: controllo di qualità della libreria (`RainGrid.quality`) contro il frame di 30 minuti
   prima (salti impossibili; tra il 9/10 e il 3/11/2026 il DPC ha pubblicato CUM24 alle :30 con valori fino a 20.584 mm),
   valori oltre i record italiani e pixel isolati; un frame scartato non sostituisce il precedente (`ultimi/ultimi.json`
   tiene il verdetto);
2. immagini PNG mancanti degli ultimi `RADAR_GIORNI_MAPPA` giorni, alle ore locali multiple del passo (CUM3 ogni 3 ore,
   CUM6 ogni 6, CUM12 a mezzanotte e mezzogiorno, CUM24 a mezzanotte), riproiettate su una griglia fissa in Web Mercator
   (1 km, Italia lon 5,5–19,5, lat 35–48); scala in mm con 14 classi, tratteggio grigio dove non c'è misura;
3. archivio CUM3 (ogni 3 ore) e CUM24 (mezzanotte) come GeoTIFF compressi in decimi di mm (30–110 KB l'uno, ~250 MB
   l'anno), e valori per comune (mediana 3×3 al punto di `comuni.parquet`, NaN = nessuna misura) in Parquet mensili;
   recupero all'indietro fino a `RADAR_RECUPERO_GIORNI` giorni, al più `RADAR_SCARICHI` frame per giro (prima messa in
   servizio: ~1.350 frame, circa un giorno); i frame che il DPC non ha più vanno in `assenti.json`;
4. pulizia (immagini oltre la finestra, mappe oltre `RADAR_ARCHIVIO_ANNI` anni), `indice.json` per la pagina e una copia
   per l'api; a inizio giornata la pioggia prevista dal sito (`previsioni/ultima.parquet`) in `previsto/<anno>.parquet`.

Sotto `RADAR_SPAZIO_MIN_GB` GB liberi l'archivio delle mappe si ferma (un'email); immagini e valori continuano.

| sul server | nel container | cosa |
|---|---|---|
| `/srv/energia/dati/radar/` | `/dati/radar/` (`RADAR_DATI`) | `archivio/<prodotto>/<anno>/*.tif`, `valori/<prodotto>/<AAAA-MM>.parquet`, `ultimi/`, `previsto/`, `previsto_email.parquet`, `indice.json`, `stato.json`, `assenti.json` |
| `/srv/energia/sito/dati/radar/` | `/sito/dati/radar/` (`RADAR_SITO`) | `indice.json` e `<prodotto>/<AAAAMMGGTHHMMZ>.png` (7 giorni, pochi MB), scritti solo dal worker |

Rotte: `/api/radar/stato`; `/api/radar/punto?lat=…&lon=…` (ultimi valori CUM3/6/12/24 nel punto e comune più vicino);
`/api/radar/comune/<istat>?giorni=30` (pioggia di ogni giorno italiano dal CUM24 della mezzanotte dopo, previsione del sito
registrata a inizio giornata, CUM3 degli ultimi 7 giorni). Newsletter: `notiziario.tabella_pioggia_regioni` (mensile per
regione: per provincia la media dei comuni misurati tutti i giorni e il comune più piovoso, i cinque comuni più piovosi) e
`notiziario.righe_pioggia_settimana` (settimanale: gli ultimi 7 giorni interi, misurata e prevista). Prove:
`tests/test_radar.py` (nessuna chiamata al DPC: frame sintetici e client finto).

Prima messa in servizio (dopo la release che contiene questa parte): `docker compose run --rm worker python -m
servizio.worker radar` (un giro di prova, ~1 minuto), poi il thread del worker continua da solo; controllare
`https://eugenio.statocritico.it/pluviometria.html`.

## Archivio psicrometrico per «Trattamento aria» (14/11/2026)

Temperatura e umidità relativa **orarie dal 1940** per ogni comune (`servizio/psicro.py`; formato e scarico nella fase 3,
`meteo_storico/psicro.py`, README della fase 3 § «Archivio psicrometrico»). Un file per comune in `CARTELLA_PSICRO`
(nel container `/dati/psicro`, sul server `/srv/energia/dati/psicro`; ~9 GB per tutta Italia) più `celle.parquet`
(quota del punto meteo e celle ERA5 di ogni comune: serve alla pressione e all'aggiornamento notturno).

- **Rotte**: `/api/psicro/disponibilita/{istat}` e `/api/psicro/serie/{istat}?anni=` (tabella delle API). Ore in UTC; la
  pagina converte in ora italiana. Pressione = 101325·(1 − 2,25577·10⁻⁵·z)^5,2559 con z la quota del punto meteo (la
  stessa a cui è riportata la temperatura); se `celle.parquet` non c'è, l'altitudine della casa comunale del DPR 412/93.
- **Ripiego**: senza il file di un comune si serve la serie oraria ICON del server (`/dati/orario/<istat>.parquet`, dal
  14/11/2022, aggiornata ogni giorno per le `REGIONI_AGGIORNATE`), con `archivio: "orario_icon"` e la nota: le pagine
  funzionano già prima che lo scarico dal 1940 sia finito, con al più 4 anni.
- **Aggiornamento notturno** (worker, comando `psicro`, subito dopo lo storico, una volta al giorno): aggiunge le ore nuove,
  mai quelle vecchie: prima le ore ICON appena scritte in `/dati/orario` (fonte 3), poi, per i comuni rimasti indietro
  (fuori dalle `REGIONI_AGGIORNATE`), ERA5/ERA5-Land dai file `.om` su S3 (fonte 1, ~5 giorni di ritardo, al più
  `PSICRO_GIORNI_MAX` giorni; `PSICRO_S3=false` lo spegne). Senza la cartella non fa nulla; mentre `scarica-psicro` ci
  scrive (file `.scarica_in_corso` aggiornato da meno di 6 ore) aspetta. Riscrive solo i file con ore nuove (~0,1 s per
  comune: ~15–30 minuti per tutta Italia sul server ARM). A mano: `docker compose run --rm worker python -m servizio.worker psicro`.
- **Variabili** (`.env`): `CARTELLA_PSICRO` (predefinita `/dati/psicro`), `PSICRO_ORA` (120), `PSICRO_S3` (true),
  `PSICRO_GIORNI_MAX` (45).
- **Prove**: `tests/test_psicro.py` (archivio sintetico: forme, null e buchi, finestre 1/2/5/10/20/0, limiti, 503,
  ripiego ICON, quota dalle celle, copia in memoria; fase 3 con S3 finto: unione delle fonti, riprendibilità, notte).

**Scelte di serie nelle altre pagine (14/11/2026).** Legge 10 (`select#anni`) e Dati climatici (stagioni della Legge 10 e
periodi rapidi delle serie a date) offrono **ultimo anno · 5 · 10 · 20 · tutta la serie**; Cambiamento climatico la
tendenza sulle ultime 5, 10, 20 stagioni o dal 1991, 1981, 1961, 1940. Lato server `/api/clima-legge10` accetta 1–30 e
0 (tutte) e i Dati storici «Legge 10» `stagioni` 0–30 (catalogo: `scelte` [1, 5, 10, 20, 0]); quando l'archivio
giornaliero (dal 2015) è più corto la risposta, la stima e la pagina dicono quante stagioni si usano e da quale.
Le stagioni più vecchie della Legge 10 **non** si prendono dall'archivio psicrometrico: `legge10.calcola` usa anche
irradiazione globale e diffusa e vento (tabella mensile UNI 10349-1), che quell'archivio non ha; mescolare nella stessa
tabella mesi con e senza queste grandezze, o ERA5 corretto e non corretto, darebbe medie non confrontabili. I gradi giorno
stagione per stagione dal 1940 ci sono già nella sezione «Clima dal 1940» della stessa pagina (fase 9).

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
con un clic in ogni email: il 12 del mese arrivano la temperatura e i gradi giorno del mese appena concluso nei
capoluoghi, confrontati con lo stesso mese degli anni precedenti e con il 1991–2020, e le Novità di EuGEnio (contenuto
dell'11/11/2026 nella sezione «Newsletter: contenuto del primo numero»).

Le campagne partono da sole (`NOTIZIARIO_INVIO_AUTOMATICO=true`); con `false` restano in bozza e arriva un avviso.
Dal 14/11/2026 il mensile parte come **un messaggio per iscritto** con le sue regioni (sezione «Newsletter e avvisi» più sotto).
I dati GME e TTF non compaiono. Iscrizione: `https://notizie.statocritico.it/subscription/form`
(dal 14/11/2026 il menu del sito porta a Clima e meteo › «Newsletter e avvisi», `dati-per-email.html`).

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
| `luogo` | `/api/patrimonio` con `luogo=1` (ricerca di un luogo, 17/11/2026, oltre a «patrimonio») | `LUOGO_ORA` (300) |
| `immobili_pa` | `/api/immobili-pa/cerca`, `/particella/{ref}`, `/bene/{id}` (17/11/2026) | 1.200 |
| `cer_fv` | `/api/cer-fv/terreni` (24/11/2026), `/api/cer-fv/vincoli` (24/11/2026 sera: vincoli paesaggistici della Regione nel riquadro `bbox`, al massimo 0,25 gradi² e 6.000 poligoni, da `DATI/vincoli/vincoli_er.sqlite`) | 600 |
| `immobili_pa_ente` | `/api/immobili-pa/ente/{chiavi}`, `/ente/{chiave}/beni` (peso 1) e `/ente/{chiave}/punti` (peso 3), 22/11/2026; più il tetto orario di tutto il sito `IMMOBILI_PA_ENTE_TETTO_ORA` (30.000, oltre: 503) | 600 |
| `report` | `/api/report`, `/api/report/{tipo}` | 60 |
| `converti` | `/api/converti` | 200 |
| `dati` | `/api/meteo`, `/api/clima-legge10`, `/api/mappa`, `/api/comuni`, `/api/metodologia`, `/api/psicro/…` | `LIMITE_DATI_ORA` (600) |
| `psicro` | `/api/psicro/serie/{istat}` (14/11/2026, oltre a «dati») | `PSICRO_ORA` (120) |
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

## CER – Sviluppo impianti FV (24/11/2026)

Rotte di `servizio/cer_fv.py` per **Fotovoltaico › CER – Sviluppo impianti FV** (fase 5). Leggono in sola lettura
`DATI/cer_fv/terreni_pubblici_<anno>.sqlite` (il più recente; `CARTELLA_CER_FV` lo sposta), preparato sull'host dalla
fase 17 (`python -m cer_fv terreni`): terreni in proprietà di enti pubblici con la probabilità di coltura DOP o certificata.

| Rotta | Cosa dà |
|---|---|
| `GET /api/cer-fv/info` | anno, conteggi, campagne AGREA usate, attribuzione; `{"disponibile": false}` se il file manca |
| `GET /api/cer-fv/terreni?lon=…&lat=…&raggio_km=5&min_m2=0&limite=100` | terreni entro il raggio (al massimo 15 km, 300 risultati), dal più vicino, con `distanza_m`; 503 se il file manca |

Campi: riferimento, centro, area, comune, foglio e particella, ente (nome, settore, sede, chiave derivata), numero di enti,
tipologie, utilizzo, `prob_coltura` (0-100), `classe_coltura`, `campagne`, `quota_dichiarata`. Nessun dato AGREA oltre
all'indicatore, nessun codice fiscale né soggetto cedente (prove in `tests/test_cer_fv.py`).

## Immobili delle Pubbliche Amministrazioni (17/11/2026, `?v=20261117a`)

Rotte di `servizio/immobili_pa.py` per **Territorio › Edifici pubblici** (fase 5) e per la nota degli edifici pubblici in
Modelli 3D. Leggono in sola lettura l'indice SQLite `DATI/immobili_pa/immobili_pa_<anno>.sqlite` (il più recente),
preparato dalla fase 7 (`python -m territorio immobili-pa-sito`): nessun dato in memoria, una connessione per richiesta.

| Rotta | Cosa dà |
|---|---|
| `GET /api/immobili-pa/info` | anno, conteggi, attribuzione, PMTiles, gruppi di enti; `{"disponibile": false}` se l'indice manca |
| `GET /api/immobili-pa/cerca?q=…&gruppo=…&limite=…` | ricerca a parole (FTS5, ogni parola come prefisso, tutte obbligatorie, al massimo 50 risultati) |
| `GET /api/immobili-pa/particella/{ref}` | particella (centro, riquadro, area) e beni (al massimo 500) |
| `GET /api/immobili-pa/bene/{id_bene}` | un bene, anche senza particella: `bene` (la prima dichiarazione) e, dal 22/11/2026, `dichiarazioni` (tutte: lo stesso `id_bene` può essere dichiarato dal proprietario e da chi lo ha in uso; prima si vedeva solo una riga) |

Ogni bene (in `/cerca`, `/particella` e `/bene`) ha i campi pubblicabili dell'indice elencati in `CAMPI_BENE`. Dal
22/11/2026 sera (scheda in sovraimpressione della ricerca per ente) anche `sup_riferimento_mq`, `detenzione_intera`,
`sistema_catastale` e `ruolo` (P proprietà, U uso), già nell'indice rifatto il 22/11; con l'indice per ente `/particella` e
`/bene` aggiungono `ente_chiave`, `ente_settore`, `ente_macrocategoria` ed `ente_sede` (`comune`, `provincia`, `regione`)
dell'ente dichiarante, letti dalla tabella `enti`. Non serve rifare l'indice. Mai `amm_cf`, `cedente`, `cedente_cf`
(`ESCLUSE`, controllato nei test).
| `GET /api/immobili-pa/ente/{chiavi}?ruolo=proprieta,uso&natura=E,T` | (22/11/2026) uno o più enti, chiavi separate da virgole (al massimo 8): dati dell'ente, `totali_dichiarati` (tabella `enti`), `totali` con i filtri (dai beni), `riquadro`, `comuni` (particelle, righe, beni e superficie per comune); con più enti `insieme`, calcolato sui **beni distinti** (un bene dichiarato da due enti scelti conta una volta, «in uso» solo se nessuno degli enti scelti lo ha in proprietà) |
| `GET /api/immobili-pa/ente/{chiave}/punti` | (22/11/2026) centri delle particelle e dei beni senza particella con punto affidabile, compatti: `{"campi": ["lon","lat","n","natura","ruolo","ref"], "righe": […]}` (5 decimali); `ETag` legato al file dell'indice, `Cache-Control: public, max-age=86400`, 304 con `If-None-Match` |
| `GET /api/immobili-pa/ente/{chiave}/beni?ruolo=&natura=&regione=&provincia=&comune=&ordina=&verso=&pagina=&per_pagina=` | (22/11/2026) elenco per particella (righe di `ente_particelle` raggruppate per `ref`), al massimo **200 righe per pagina**, ordinamento solo sulle colonne di `ORDINAMENTI` (vuoti in fondo; senza `ordina`: regione, comune, indirizzo), `totale` e `pagine` |

Limite per IP `immobili_pa`: 1.200 richieste all'ora (`protezione.LIMITI`); per le rotte degli enti `immobili_pa_ente`:
600 all'ora (i punti pesano 3) più il tetto `IMMOBILI_PA_ENTE_TETTO_ORA` per tutto il sito (30.000 all'ora, oltre: 503),
pensati contro la copia sistematica (decisione «non scaricabile»: con 200 righe per pagina servono decine di migliaia di
richieste per copiare tutto). L'ente si indica con la **chiave** (10 caratteri esadecimali derivati dal codice fiscale
nella fase 7; il CF non è nell'indice); 404 per una chiave sconosciuta, 400 per chiavi, ruoli, nature, ordinamenti o comuni
non validi. Con un indice di prima del 22/11/2026 (senza tabella `enti`) le tre rotte rispondono `{"disponibile": false}`:
l'ordine fra rilascio del sito e rifacimento dell'indice non conta.

Le tessere della mappa non passano dall'API: sono il PMTiles statico `immobili_pa_<anno>_<versione>.pmtiles` nella cartella
degli archivi edifici (`CARTELLA_EDIFICI/immobili_pa/`, servita da Caddy in `/edifici3d/immobili_pa/`, con `indice.json`
riconvalidato sempre); accanto c'è `enti_<anno>_<versione>.json`, l'elenco degli enti per l'autocompletamento (in copia
per un giorno come il PMTiles: il nome cambia a ogni rifacimento). Nessuna rotta restituisce soggetto cedente o codici
fiscali (`ESCLUSE`). Test: `tests/test_immobili_pa.py` (indice costruito con la fase 7: niente CF né cedente in nessuna
risposta, paginazione, ordinamento su lista chiusa, filtri, 404, indice vecchio, limite e tetto, `bene` con due
dichiarazioni).

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

**Come si aggiunge un DTM sul server** (20/11/2026). `/srv/energia/dati/terreno` (`/dati/terreno` nei container) e le
altre cartelle scritte dai container (`psicro`, `rete`, …) sono dell'utente 1000: un `cp` dell'utente `ubuntu` fallisce
con «permission denied» (successo il 16/11/2026 con il DTM di Perugia). Due strade, dalla cartella `~/energia/fase4-server`:

1. **Generare il COG nel container** (`edifici-lidar` gira come utente 1000 e scrive `<nome>.tif` e la scheda
   `<nome>.json`). I file d'origine devono stare sotto `/srv/energia/dati` (il container vede solo `/dati`), copiati con
   `sudo`:
   ```bash
   sudo mkdir -p /srv/energia/dati/terreno/grezzi/<zona>
   sudo cp ~/<tavole>/* /srv/energia/dati/terreno/grezzi/<zona>/ && sudo chown -R 1000:1000 /srv/energia/dati/terreno/grezzi
   docker compose --profile edifici run --rm edifici-lidar dtm-server --regione veneto --crs EPSG:6876 \
       --file /dati/terreno/grezzi/<zona> --uscita /dati/terreno/dtm5_<zona>.tif
   ```
   `--file` accetta uno o più zip, TIFF, ESRI ASCII Grid o cartelle (mosaicati); `--regione er|veneto|pst_umbria` sceglie
   la scheda (licenza, attribuzione, nome in legenda; altrimenti `--licenza`, `--attribuzione`, `--nome`); `--crs` solo
   per i file senza sistema. Le sottocartelle (`grezzi/`) non sono lette dalla rotta.
2. **Copiare un COG già pronto** (fatto sul PC con `python -m edifici3d dtm-server …`), sempre `.tif` **e** `.json` con lo
   stesso nome:
   ```bash
   sudo cp ~/perugia_1611/dtm1_pst_perugia.tif ~/perugia_1611/dtm1_pst_perugia.json /srv/energia/dati/terreno/ \
     && sudo chown 1000:1000 /srv/energia/dati/terreno/dtm1_pst_perugia.tif /srv/energia/dati/terreno/dtm1_pst_perugia.json
   ```
   (per una cartella `sudo cp -r` o `sudo mv`, poi `sudo chown -R 1000:1000`).

L'api rilegge le schede ogni **5 minuti** (`dtm_disponibili()`), senza riavvio; la copia delle tessere cambia versione da
sola. Verifica dopo 5 minuti: `curl -s https://eugenio.statocritico.it/api/terreno/fonti` deve elencare il file nuovo in
`dtm` (`file`, `riquadro_wgs84`, `licenza`, `nome`); poi le intestazioni di una tessera dentro il riquadro (il parametro in
coda evita la copia di Cloudflare, che tiene le tessere 30 giorni), ad es. Perugia centro:
`curl -sI "https://eugenio.statocritico.it/api/terreno/15/17511/12026.png?prova=$(date +%s)" | grep -i x-terreno` →
`X-Terreno-Fonte: dtm` e `X-Terreno-Nome` con il nome del DTM nuovo (non «DTM 5 m nazionale HR-DTM-5m …»).

**DTM nazionale HR-DTM-5m (19/11/2026)**. Tra i DTM regionali e il Copernicus `terreno.py` usa il DTM a 5 m di tutta
Italia del CNR-IRPI (M. Panza, M. Muto, I. Marchesini, M. Rossi, M. Alvioli, G. Iovine; Zenodo,
https://doi.org/10.5281/zenodo.24009736, versione 1.3 del 06/11/2026, **CC BY 4.0**): LiDAR regionali a 1–2 m ricampionati
dove ci sono (52 % del territorio), TINITALY 1.1 a 10 m altrove, mare senza dato (lì resta il Copernicus). È un COG di
34,3 GB (EPSG:6875, float32, ZSTD con predittore 3, tessere 512, panoramiche fino a 1:513) e **non si copia sul server**
(spazio libero ~24 GB): si legge con `/vsicurl/` dall'indirizzo `TERRENO_NAZIONALE_URL` (predefinito il file della
versione 1.3; `""` spegne la fonte). Zenodo risponde 206 alle letture a pezzi, provato dal server il 19/11/2026.

- **Ordine**: DTM regionali (il più dettagliato prima), poi il nazionale, poi Copernicus, poi piatta. Il nazionale è una
  scheda fissa (`NAZIONALE`) aggiunta in coda a `dtm_disponibili()`: la versione della copia cambia e le tessere vecchie
  si tolgono da sole (da questa pubblicazione `pulisci()` toglie subito le cartelle delle versioni che non ci sono più).
- **File tenuto aperto**: riaprire il COG remoto costa ~1 s (HEAD e intestazione), due volte per tessera; `apri()` tiene
  aperto un dataset per thread e per panoramica. Opzioni di GDAL per `/vsicurl/` (`opzioni_gdal()`): niente elenco della
  cartella, letture a pezzi unite, 2 tentativi, `TERRENO_NAZIONALE_TIMEOUT_S` (10 s), cache HTTP di 64 MB, User-Agent di
  EuGEnio.
- **Pausa**: dopo un errore di rete il nazionale si salta per `TERRENO_NAZIONALE_PAUSA_S` (600 s) e si usa il Copernicus,
  così una caduta di Zenodo non rallenta ogni tessera.
- **Rilievo d'origine**: `X-Terreno-Nome` è «DTM 5 m nazionale HR-DTM-5m del CNR-IRPI (CC BY 4.0), qui da LiDAR <nome>
  (<anno>)» o «… qui da TINITALY 1.1 a 10 m», dal file `servizio/hrdtm5m_fonti_250m.tif` (357 kB): il GeoPackage
  `HRDTM5m_Mask_20mres.gpkg` della stessa pubblicazione (CC BY 4.0) rasterizzato una volta su una griglia di 250 m in
  EPSG:6875, codici in `tags()["fonti"]` (14 rilievi; per rifarlo con una versione nuova: `rasterize` di rasterio sul
  livello `simplified`, prima TINITALY e sopra i LiDAR). Si sceglie il rilievo più esteso tra 81 punti della tessera.
- **Misure (19/11/2026)**: dal workspace di Claude e con il codice di questa pubblicazione, prima tessera ~3,6 s (apertura),
  poi 0,3–0,9 s per tessera nuova, ~1 MB scaricato ciascuna; quote dei punti 0,5 s. Quote coerenti con quelle note: Bagno
  di Romagna 509,3 m (DTM ER ~510), Susegana 70,2 m (Copernicus 70,9), Bologna (Due Torri) 59,5 m, Roma (Colosseo) 26,8 m.
- **Prove**: `tests/test_terreno.py` con un DTM nazionale simulato (COG ZSTD in EPSG:6875 con una striscia di mare) servito
  da un piccolo servizio HTTP che risponde a pezzi come Zenodo; `tests/conftest.py` spegne la fonte vera in tutte le prove.


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

`servizio/notiziario.py` (`novita_tra`): nella newsletter mensile le voci del registro delle versioni
`fase5-sito/novita.toml` (README della fase 5), con il rimando a `novita.html`. Il file è copiato nell'immagine
(`COPY fase5-sito/novita.toml /app/novita.toml`, `NOVITA_TOML` in `config.py`): il pacchetto del codice (F5) lo deve
comprendere. Nessun dato di mercato. Caddy serve `/novita.xml` come `application/atom+xml; charset=utf-8`.

## Newsletter: contenuto del primo numero (11/11/2026, decisioni di Paolo)

Dopo l'anteprima del 12/11/2026 (dati di ottobre), `servizio/notiziario.py`:

| Parte | Regola |
|---|---|
| Indici dei prezzi (in cima) | dal file del sito `/sito/dati/prezzi/indici.json` (scritto dal worker dopo i mercati, `prezzi`): energia elettrica Intercent-ER lotti 1 e 2 e Consip lotto predefinito (6, Emilia-Romagna) con F1, F2, F3 in colonna; gas: listino Intercent-ER (primo lotto con il valore del mese), PSV ARERA, PFOR; tra parentesi la variazione sullo stesso mese dell'anno prima; collegamento a `indici-prezzi.html`. Oggetto «EuGEnio – prezzi e freddo di <mese>», titolo «EuGEnio, <mese>». |
| Capoluoghi | quelli segnati in `comuni.parquet` più i secondi capoluoghi di `CO_CAPOLUOGHI` (Cesena accanto a Forlì; Urbino, Carrara, Andria, Trani se serviti). Senza capoluoghi la sezione si salta con un avviso nel registro e **il giornaliero non si legge** (prima, senza filtro, si sarebbe letto tutto l'archivio nazionale). |
| Frase di sintesi | «Ottobre 2026 è stato più caldo della media 2015–2025 in N capoluoghi su M: in media +X °C con il Y % di gradi giorno in meno. Rispetto al clima del 1991–2020 lo scarto medio è di +Z °C.» |
| Tabella | temperatura media, scarto in °C dalla media dello stesso mese nell'archivio (periodo **dichiarato**: anni precedenti con almeno 25 giorni del mese), scarto dal 1991–2020, gradi giorno base 20 °C di **tutti i giorni del mese** (detto nel testo: anche fuori dal periodo di accensione), media e scarto in %. Segno meno tipografico (−). |
| Scarto dal 1991–2020 | scarto dalla media dell'archivio + (media del mese negli stessi anni − normale 1991–2020) nella serie del **clima dal 1940** (fase 9, `/sito/dati/clima/<RR>/<istat>.json` e `_mensili.json`): i due termini vengono ciascuno da una sola fonte, così ERA5 corretto/ICON e ERA5-Land non si confrontano direttamente. Se manca un anno o un file, la colonna resta «—» (o sparisce se manca per tutti). |
| Novità | voci di `novita.toml` con data **dopo il numero precedente e fino al giorno dell'invio** (`novita_tra`); nel **primo numero** (`NOTIZIARIO_PRIMO_NUMERO`, predefinito `2026-11`) tutte dall'inizio. |
| Altri comuni | subito sotto la tabella, «Il tuo comune non c'è?» con il collegamento a Clima e meteo › Dati climatici (`dati.html`). |
| Benvenuto | due righe solo nel primo numero. |
| Eurostat | **tolto** (dato semestrale: per ora non dice niente). I file e i Dati storici restano. |

Anteprima senza invio, dal server: `cd ~/energia/fase4-server`, poi
`docker compose run --rm --no-deps worker python -c "import datetime as d; from servizio import notiziario as n; o,c=n.testo_mensile(2026,10,d.date(2026,11,12)); print(o); print(); print(c)"`.
Bozza sulla lista **Prove** (ID 4 in listmonk, privata, opt-in singolo): `docker compose run --rm --no-deps -e LISTA_MENSILE=4 -e NOTIZIARIO_INVIO_AUTOMATICO=false worker python -c "from servizio import notiziario as n; print(n.mensile(2026,10))"`.
Prove: `tests/test_notiziario_novita.py` (3), `tests/test_notiziario_freddo.py` (7).

## Newsletter e avvisi: mensile per regione, previsioni settimanali, avvisi meteo (dal 14/11/2026)

Decisione di Paolo del 14/11/2026: tre servizi **separati**, ognuno con la sua lista in listmonk, e la zona scelta da chi
si iscrive nella pagina del sito **`dati-per-email.html`** (menu Clima e meteo › «Newsletter e avvisi», dal 15/11/2026; prima «Iscriviti»).

| Servizio | Lista | Quando | Contenuto |
|---|---|---|---|
| Newsletter mensile | «EuGEnio mensile» (`LISTA_MENSILE`, 3) | il 12, dalle 9 | prezzi nazionali (Consip con i **lotti delle regioni scelte**), freddo e gradi giorno del mese **regione per regione** (media dei capoluoghi), i **capoluoghi** delle regioni scelte (fino a `EMAIL_MAX_REGIONI` = 3), novità |
| Previsioni settimanali | «EuGEnio settimanale» (`LISTA_SETTIMANALE`, 0 = creata) | domenica dalle 17 | da lunedì a domenica per fino a `EMAIL_MAX_COMUNI` = 5 comuni: min e max, pioggia, neve, raffica, gradi giorno, giorni oltre le soglie degli avvisi; gradi giorno della settimana contro gli stessi giorni degli anni dell'archivio |
| Avvisi meteo | «EuGEnio avvisi meteo» (`LISTA_AVVISI`, 0 = creata) | ogni giorno dalle 15 | domani nei comuni scelti, solo per i fenomeni scelti: **pioggia forte** ≥ 40 mm/24 h o ≥ 15 mm/1 h, **neve** ≥ 2 cm, **vento molto forte** raffiche ≥ 75 km/h (`AVVISO_*` nel `.env`) |

Gli avvisi **non sono allerte**: in ogni avviso, nella pagina e nelle F.A.Q. c'è scritto che il servizio è gratuito, non
fornisce garanzie e non sostituisce le allerte della Protezione Civile e degli enti pubblici, con il collegamento al
bollettino nazionale di criticità.

**Come funziona**
- `servizio/preferenze_email.py` (rotte `/api/email/…`): `opzioni`, `comuni` (elenco nazionale), `link` (collegamento
  personale per email, con la verifica anti-robot, 10 all'ora per IP e 3 al giorno per indirizzo; l'indirizzo non entra
  in listmonk finché non si salva), `leggi`, `salva` (liste già confermate: il collegamento conferma l'indirizzo), `via`
  (cancellazione da un servizio, anche con un clic dal programma di posta, RFC 8058). Gettoni firmati con
  `NOTIZIE_CHIAVE` (o `SESSIONE_CHIAVE`): senza chiave la pagina dice «non ancora attivo».
- `servizio/listmonk.py`: liste (create la prima volta, private e a doppia conferma), iscritti con le scelte negli
  attributi `eugenio` (`regioni`, `comuni`, `avvisi`), **messaggi personali** con l'API transazionale e il modello
  «EuGEnio – messaggio personale» (creato da solo).
- `servizio/notiziario.py`: testi Markdown → HTML (pacchetto `markdown`), un messaggio per iscritto, piè con
  «Cambia servizi, regioni e comuni» e «Cancellati con un clic»; registro degli invii in `/dati/invii_email/` (niente
  doppioni se il worker riparte; cancellato dopo 120 giorni). `NOTIZIE_PERSONALI=false` riporta il mensile alla campagna
  unica di prima (settimanale e avvisi fermi).
- `servizio/meteo_email.py`: previsioni Open-Meteo (`best_match`, con raffiche e neve) per i soli comuni scelti, a blocchi
  di 50 con il limitatore del server; vale anche fuori dalle `REGIONI_AGGIORNATE`.
- Worker: `settimanale` e `avvisi` nel ciclo (`SETTIMANALE_GIORNO`, `SETTIMANALE_ORA`, `AVVISI_ORA`) e a mano
  (`python -m servizio.worker settimanale|avvisi`). Lo storico di ogni giorno comprende i **capoluoghi di tutte le
  regioni** (`STORICO_CAPOLUOGHI_ITALIA=true`, ~110 punti in più) per gli indicatori regionali del mensile.

Anteprima del mensile per una regione, dal server (`cd ~/energia/fase4-server`):
`docker compose run --rm --no-deps worker python -c "import datetime as d; from servizio import notiziario as n; c=n._capoluoghi_italia(); v=n._voci_freddo(c,2026,10); print(n.testo_mensile_regioni(2026,10,d.date(2026,11,12),['08'],v,n._nomi_regioni(c))[1])"`.
Prove: `tests/test_email_personali.py` (15) e, nel sito, `tests/test_dati_per_email_browser.py` (4).

**«Annulla iscrizione» dei programmi di posta e lista di soppressione di OCI (20/11/2026)**. OCI Email Delivery aggiunge
una sua intestazione `List-Unsubscribe` a ogni email che non ne ha già una HTTPS; con quella, «Annulla iscrizione» di
Gmail mette l'indirizzo nella **lista di soppressione** di OCI e da lì OCI rifiuta ogni email per lui (errore SMTP 254
«… is suppressed for sender …»), anche il collegamento per reiscriversi. Successo a Paolo il 19–20/11 (prova voluta di
«Annulla iscrizione»). Ora:
- i messaggi dei tre servizi avevano già la nostra intestazione (`/api/email/via`, cancella solo da quel servizio) e il
  collegamento «Cancellati con un clic» nel piè;
- **tutte le email spedite direttamente** (`avvisi.invia_a`: collegamento personale, email del servizio per
  l'amministratore) hanno ora la nostra intestazione HTTPS con `List-Unsubscribe-Post`: il collegamento personale punta a
  `/api/email/via-tutto?t=…` (gettone `tutto` con il **numero** dell'iscritto, mai l'indirizzo; toglie da tutti i servizi;
  per chi non è iscritto la rotta `/api/email/servizio`, che non fa niente), le email del servizio a
  `/api/email/servizio` e portano in fondo «Non usare "Annulla iscrizione"…: si spengono togliendo EMAIL_AMMINISTRATORE»;
- un destinatario nella lista di soppressione è riconosciuto (`avvisi.IndirizzoBloccato`): la pagina dice che l'indirizzo
  è bloccato dal servizio di posta e rimanda a Contatti (risposta 409), l'amministratore riceve un'email con l'indirizzo e
  il percorso per sbloccarlo; nel registro solo «lista di soppressione di OCI», senza l'indirizzo.
- **Per sbloccare un indirizzo**: https://cloud.oracle.com (regione Milano) › Developer Services › Email Delivery ›
  Suppression List, compartimento **radice**, riga dell'indirizzo › Delete.
- Restano senza la nostra intestazione solo le email di sistema di listmonk (conferme della doppia conferma, se mai
  usate: il sito iscrive con liste già confermate); le campagne di listmonk usano la sua intestazione (Impostazioni ›
  Privacy › «Includi l'intestazione List-Unsubscribe», da tenere accesa).

## Aggiornamento del server da GitHub (`aggiorna_da_github.sh`, dal 12/11/2026)

Decisione di Paolo del 12/11/2026 (strade «1» e «2a»): Claude lavora sul repository con **pull request** che Paolo
approva; dopo l'approvazione si crea la **release** (`vAAAA.MM.GG`, `vAAAA.MM.GGb` …) e il server si aggiorna da solo da
quella release con `aggiorna_da_github.sh`. Il repository è pubblico: il server lo legge in HTTPS, **senza chiavi**.
Niente pacchetti `codice.tar.gz`/`sito.tar.gz` da copiare con scp.

| Comando (sul server) | Cosa fa |
|---|---|
| `~/energia/fase4-server/aggiorna_da_github.sh --prova` | dice cosa farebbe con l'ultima release (file, convenzioni cambiate, procedure con passi a mano), senza toccare nulla |
| `~/energia/fase4-server/aggiorna_da_github.sh` | installa l'ultima release, se è più nuova di quella in `~/.eugenio_versione` |
| `~/energia/fase4-server/aggiorna_da_github.sh v2026.11.13` | installa quella release (anche per tornare indietro: `--forza v…`) |
| `~/energia/fase4-server/aggiorna_da_github.sh --notte` | dal crontab alle 4:40: solo se c'è una release nuova; **email solo se qualcosa va storto** (16/11/2026) |

Passi: copia di sicurezza di `~/energia` (`~/energia_prima_<release>`, si tengono le ultime 3) e delle convenzioni (`~/convenzioni_prima_<release>`); codice delle fasi 3, 4,
6, 7, 8, 9, 10, (20/11/2026) 15 e (22/11/2026) 16 in `~/energia` con rsync **senza cancellare** (restano `.env`, fase 2, `uni_privato`,
`mercati_energia/dati/` e tutto ciò che non è nel repository); convenzioni `*.toml` e `fonti/*.toml` in
`/srv/energia/dati/mercati/convenzioni`; `docker compose build api` e `up -d --force-recreate api worker` con attesa di
`/api/salute` (3 minuti: se l'api non risponde si torna **da soli** alla copia e si esce con errore, email
all'amministratore); sito in `/srv/energia/sito` (senza cancellare; `dati/indicatori/`, `dati/prezzi/` e, dal 20/11/2026, `dati/elettricita/` e
`dati/carichi/`, dal 22/11/2026 `dati/suolo/` non si toccano) con il controllo della versione `?v=`; `worker prezzi`; **Purge Everything** su Cloudflare se nel `.env` ci sono `CF_ZONE_ID` e
`CF_PURGE_TOKEN` (token con il **solo** permesso «Zone › Cache Purge» sulla zona; lo script non li stampa mai). Registro in
`~/aggiorna_da_github.log`; un solo aggiornamento alla volta (`flock`). Lo script si riavvia da una copia temporanea, così
può aggiornare anche se stesso.

### Correzioni del 21/11/2026 (aggiornamento a v2026.11.21 fallito, `../AGGIORNAMENTO_2026-11-22.md`)

Il 21/11 alle 9:22 lo script di v2026.11.20d ha installato v2026.11.21 senza copiare `fase15-elettricita` (non la
conosceva) e la build è fallita; il ritorno indietro ha poi fatto `rm -rf ~/energia` verso una copia che la pulizia aveva
appena cancellato (`cp -a` conserva la data della cartella, e `ls -t` la vedeva come la più vecchia). Ora:

| Punto | Comportamento |
|---|---|
| **Script della release** | dopo il checkout del tag nel clone, se `~/eugenio-git/fase4-server/aggiorna_da_github.sh` è diverso da quello in esecuzione, lo script **rilancia quello della release** (`exec`) con gli stessi argomenti e la release già scelta; `EUGENIO_RILANCIATO=1` impedisce un secondo rilancio. Ogni release si installa con la procedura provata insieme a lei (cartelle, esclusioni, controlli, passi nuovi), non solo con l'elenco delle cartelle aggiornato. Il rilancio avviene prima di qualunque copia o modifica. |
| **Copia del `.env`** | prima di tutto, `~/energia/fase4-server/.env` va in `~/.eugenio_env_backup/env_AAAA-MM-GG` (cartella 700, file 600; se il file del giorno c'è già e il `.env` è diverso, `env_AAAA-MM-GG_HHMMSS`; se è uguale all'ultima copia, niente). Si tengono le ultime 10, in ordine di nome. Le copie fatte a mano con lo stesso nome (es. `env_2026-11-21` di Paolo) non si sovrascrivono mai. |
| **Controlli iniziali** | se `~/energia` non ha `fase4-server/docker-compose.yml` o il `.env`, lo script si ferma senza toccare niente (avviso). La copia di sicurezza appena fatta deve avere gli stessi due file, altrimenti ci si ferma. |
| **Copie di sicurezza** | dentro ogni copia `~/energia_prima_<release>` c'è il file `.eugenio_copia` (secondi, versione contenuta, release); la pulizia ordina su quello (le copie senza file, quelle di prima del 21/11, sono le più vecchie, in ordine di release) e tiene le ultime 3. **Mai** cancellate: la copia appena fatta e quelle della versione installata. Con `--forza` su una release che ha già la sua copia, quella non si sovrascrive: la nuova si chiama `~/energia_prima_<release>_<AAAAMMGG-HHMMSS>`. |
| **Controllo dei `COPY`** | dopo la copia del codice e prima della build, ogni percorso dei `COPY` di `api/Dockerfile` (anche su più righe e con `*`) deve esistere in `~/energia`. Se manca qualcosa: messaggio con l'elenco, codice di prima rimesso dalla copia, **container non toccati**, avviso. Con `--prova` lo stesso controllo si fa sul codice della release e scrive solo «ATTENZIONE». |
| **Ritorno indietro** | non fa mai `rm -rf ~/energia`. Controlla che la copia esista e abbia `docker-compose.yml` e il `.env`; la copia in `~/energia.ripristino_<data>`, sposta `~/energia` in `~/energia.fallita_<data>` (se ne tengono 3) e mette la copia al suo posto, poi rifà build e avvio. Se la copia manca o è incompleta **non tocca niente**: `~/energia` resta con il codice nuovo, i container di prima restano accesi, errore nel registro («ERRORE GRAVE») ed email. |

Variabili in più per le prove: `EUGENIO_ENV_BACKUP` (`~/.eugenio_env_backup`), `EUGENIO_ATTESA` (5 secondi tra i
controlli di `/api/salute`). Prove: `tests/test_aggiorna_da_github.py` (repository «origin» locale, `~/energia` finta,
`docker` finto nel PATH; servono `bash`, `git`, `rsync`, `flock`).

**Attenzione**: il rilancio lo fa solo uno script che lo conosce. Le release fino a v2026.11.21 hanno lo script vecchio:
la prima volta lo script nuovo va lanciato **dal clone** (procedura in `../AGGIORNAMENTO_2026-11-22.md`).

**Cosa non fa**: i «passi a mano» delle procedure `AGGIORNAMENTO_*.md` cambiate tra le due release (righe nuove del
`.env`, archivi grandi, crontab, servizi nuovi come `edifici`) li **elenca** alla fine e nel registro, non li esegue; i
dati di terzi fuori da git (`mercati_energia/dati/`, `uni_privato`, fase 2) arrivano ancora dal PC. Le procedure nuove
avranno quindi un passo unico «`aggiorna_da_github.sh`» più gli eventuali passi a mano.

Tutte le cartelle si possono cambiare con le variabili `EUGENIO_REPO`, `EUGENIO_CLONE` (`~/eugenio-git`),
`EUGENIO_ENERGIA`, `EUGENIO_SITO`, `EUGENIO_CONVENZIONI`, `EUGENIO_STATO`, `EUGENIO_REGISTRO` (le usa la prova a vuoto).
Installazione e prima prova: procedura X di `AGGIORNAMENTO_2026-11-12.md`.

**Email (decisione di Paolo del 16/11/2026)**: l'email all'amministratore parte **solo se qualcosa va storto**, mai per
dire che è andato tutto bene:
- aggiornamento fallito, con il ritorno da solo alla versione di prima (anche a mano);
- con `--notte`, errore imprevisto (GitHub irraggiungibile, rsync, disco pieno…): oggetto «aggiornamento notturno
  interrotto»;
- con `--notte`, release installata ma Purge di Cloudflare o indici dei prezzi non riusciti: oggetto «server aggiornato a
  …, ma con problemi».

Se va tutto bene, l'esito resta solo in `~/aggiorna_da_github.log`, insieme all'elenco delle procedure con i passi a mano.
Riga del crontab (procedura X9): `40 4 * * * $HOME/energia/fase4-server/aggiorna_da_github.sh --notte >/dev/null 2>&1`.

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
- Rete elettrica (17/11/2026): «Fonte: e-distribuzione S.p.A., mappa delle Aree critiche e mappa delle interruzioni» (uso
  non commerciale, rimozione su richiesta); posizioni delle cabine primarie «© contributori OpenStreetMap», ODbL 1.0; codici
  delle aree convenzionali GSE S.p.A. (solo i codici).
- Confini comunali: ISTAT (CC BY 4.0) via Gramscii.
- Ortofoto (Fase B): la citazione e la licenza di ogni fonte stanno nel suo TOML e sotto la mappa; PVGIS © Unione europea
  (riuso con citazione); Copernicus DEM GLO-90 © DLR e Airbus (licenza Copernicus DEM) dai file di Open-Meteo (CC BY 4.0).
- Report: python-docx (MIT), fpdf2 (LGPL-3.0), openpyxl (MIT), odfpy (Apache 2.0 / GPL 2+), font DejaVu Sans (licenza libera Bitstream Vera/DejaVu).

## Come si lanciano tutte le prove della fase 4 (24/11/2026)

```bash
cd fase4-server && python -m pytest -q tests
```

(24/11/2026 sera) `tests/conftest.py` mette nei percorsi di Python le altre fasi come il container (fase 10 prima,
poi 3, 6, 7, 8, 15, 16, 17 in coda): non serve più il PYTHONPATH a mano. Servono le librerie di `api/requirements.txt`
(anche `fpdf2`, `rasterio`, `dpc-radar`). Il 24/11/2026: 439 passate.
