# Fase 5 – Sito: mappa, previsione, patrimonio, Legge 10, metodo

Sito statico (HTML, CSS e JavaScript senza librerie esterne), servito da Caddy nella fase 4.

```
sito/
  index.html        mappa dei comuni colorata con i gradi giorno previsti a 7 giorni, ricerca indirizzo
                    (Zornade), caricamento CSV, scelta della modalità, grafico con le fasce di probabilità
  patrimonio.html   elenco di edifici (CSV) → punto e particella catastale, mappa dei punti, esiti, download; dal
                    04/11/2026 passo «Visure catastali» con i file di EuGEnio Visure (visure_abbina.js,
                    visure_patrimonio.js), abbinati solo nel browser
  legge10.html      dati climatici del comune per la Legge 10, con il confronto con l'Allegato A del DPR 412/93
                    (gradi giorno, zona e altitudine di legge, differenza %, linea del DPR nel grafico; per i comuni
                    nati da fusione i valori dei comuni d'origine): gradi giorno, zona, temperature di progetto,
                    dati mensili UNI 10349, grafico dei gradi giorno per stagione, download CSV/JSON
  metodo.html       come funziona, in capitoli, uno per pagina del servizio: In generale ("Ma è legale?", i tuoi
                    dati), Previsione dei consumi (modello, fonti meteo, correzione ERA5 con le metriche reali da
                    /api/metodologia, limiti), Patrimonio, Legge 10, Dati storici, Indicatori (in preparazione), e #fonti con
                    tutte le fonti di dati e i link (meteo, territorio, energia e mercati, convenzioni, modello)
  faq.html          F.A.Q. (voce di menu "F.A.Q."): nome, open source (cinque ragioni), mirror, dati di mercato,
                    limiti, CKAN (con Eurostat e ISTAT), funzioni mancanti, chi c'è dietro; ancore #open-source,
                    #mirror, #mancano, #chi
  sitografia.html   Sitografia (era "Link"; link.html resta come rimando): gruppi comprimibili, tutti aperti all'inizio,
                    con i pulsanti Espandi tutto / Comprimi tutto. Progetti open source e dati aperti usati (con Oracle
                    Cloud come hosting), norme e dati climatici di riferimento (Normattiva, UNI, CTI), siti di riferimento per l'energia (FIRE, SECEM, ENEA, GSE, Energy & Strategy
                    del Politecnico di Milano) e per i dati sanitari (ISTAT IstatData, SISEPS Emilia-Romagna, OpenBDAP,
                    DoveVannoINostriSoldi); "open source" porta a licenza.html; in fondo Claude (ancora #claude)
  dati.html         Dati storici (dati.js): scelta di dataset (meteo orario ICON, giornaliero ERA5 corretto, gradi
                    giorno, dati per la Legge 10, comuni, prezzi Eurostat), periodo, frequenza, copertura minima e
                    zona (regione, provincia, comuni dalla ricerca o dalla mappa); stima delle dimensioni e download
                    CSV, Excel o OpenDocument (.ods) da /api/storici/... Mai dati GME, EEX, PFOR, Zornade o ANNCSU
  contatti.html     Contattaci: modulo (nome, email, ente, ruolo, tipo, oggetto, descrizione) che prepara l'email
                    per eugenio@statocritico.it nel programma di posta di chi scrive (mailto) o la copia negli
                    appunti; il sito non riceve né salva niente (contatti.js)
  licenza.html      la AGPL-3.0 in parole semplici: cos'è, perché, cosa comporta per chi usa il sito e per chi lo
                    installa, condizioni delle fonti di dati
  mirror.html       come fare un mirror: requisiti, codice, dati meteo di un'altra regione, .env, prova in locale
                    (docker-compose.override.yml con la porta 8080), messa online, personalizzazione, regole
  importa-dxf-ifc.html  Patrimonio › Importa DXF/IFC (04/11/2026): DXF e IFC letti nel browser (importa_modello.js nella
                    pagina, modelli_worker.js nel Web Worker, modelli_import.js con la logica di `importa-modello`);
                    librerie in lib/ (dxf-parser, web-ifc, clipper-lib, proj4) caricate solo qui; posa dal file, da un
                    sistema di riferimento o con due punti noti; risultato a modelli3d.html?modello=locale o .geojson
  privacy.html      informativa privacy (titolare: Paolo Bianco; email in arrivo via Cloudflare Email Routing e Gmail)
  EUGENIO_PER_AGENTI.md  tutte le funzioni spiegate agli agenti AI (06/11/2026; copia identica di quello nella radice del
                    repository; servito da Caddy come text/markdown); llms.txt  rimando breve (convenzione llms.txt)
  app.js, patrimonio.js, legge10.js, contatti.js, stile.css
  report.js         pulsanti "Scarica il report" (PDF, Excel, ODS; dal 28/10/2026 niente Word né ODT) su previsione, patrimonio, Legge 10 e
                    indicatori: manda i
                    risultati già mostrati a POST /api/report/{tipo}?formato=… e scarica il file (corpoReport() in
                    ogni script di pagina)
  indice.js         indice laterale di Come funziona, F.A.Q. e Sitografia: a sinistra, fermo mentre il testo scorre,
                    con la voce della sezione visibile evidenziata; un clic apre la sezione e ci porta. In Come
                    funziona su due livelli (capitoli h2 e paragrafi h3). Su telefono diventa un riquadro richiudibile
                    in alto
  minimappa.js      piccola mappa d'Italia accanto al titolo di previsione, patrimonio e Legge 10: nome della regione
                    al passaggio del mouse, zoom con la rotella (+, −, doppio clic per tornare), clic = regione della
                    mappa grande (?regione=RR, ricordata nel browser e portata nei link; predefinita 08); il patrimonio
                    cambia regione senza ricaricare (window.EUGENIO.suRegione). Ogni regione ha il suo colore, ispirato
                    al logo o allo stemma regionale (tabella COLORI in cima al file). La mappa grande mostra tutta
                    l'Italia (regioni colorate in trasparenza), si apre centrata sulla regione scelta, si muove con
                    rotella e trascinamento (doppio clic: torna alla regione; la freccia ↑ accanto alla piccola mappa
                    la porta su tutta l'Italia); spessori fissi in pixel: comuni 0,5,
                    province 1,2, regioni 2,2
  dati/dpr412.json  Allegato A del DPR 412/93 per codice ISTAT attuale (gg, zona, altitudine, nome nel DPR, nota
  dati/dpr412.csv   fusione/incorporazione); il CSV si scarica dalla pagina. Generati da costruisci_dpr412.py dal testo
                    vigente di Normattiva (Akoma Ntoso, aggiornato al 28/04/2022): 8.105 righe su 8.106 abbinate,
                    7.890 comuni attuali su 7.896 coperti (6 nati dopo il 1993 per distacco); scelte in
                    abbinamento_dpr412.md. Una copia va anche nella cartella dati del server (dataset di Dati storici)
  dati/mappa/       confini per il sito, tutta Italia: italia.json (regioni) e RR.json (comuni e province di ogni
                    regione; le province sono disegnate sopra i comuni senza intercettare i clic)
  font/             caratteri ospitati sul sito (Barlow, Hanken Grotesk; licenza OFL)
  logo/             logo, scritta, simbolo e icone per ogni vestito (SVG, scuro e chiaro)
  aspetto.js        pulsanti del tema ◐ e del vestito ✱
  grafici.js        modulo comune dei grafici: pulsante ↗ e riquadro flottante (zoom, trascinamento, ✱ e ◐),
                    riquadretto dei valori sui grafici mensili e annuali (regole in README_stile.md § Grafici)
  divisore.js       maniglia tra le due colonne delle pagine dei servizi: allarga o stringe il pannello di destra
  tabelle.js        file caricati: CSV letti nel browser, Excel (.xlsx) e OpenDocument (.ods) convertiti dal server
                    (/api/converti, primo foglio); numeri all'italiana
  mappa3d.js        mappa 3D di Patrimonio (rotazione su tre assi, zoom, barre a mattoncini, disegno SVG)
  valori_sedi.js    scheda «Valori per sede» di Patrimonio: unità, scale, mattoncini, controlli per colonna, tabella
  esempi/valori_sedi_esempio.csv  13 sedi con valori SINTETICI (riga delle unità: MWh, MWh, litri)
  README_stile.md   vestiti, variabili CSS, colori delle regioni e delle serie
  esempi/           CSV di consumi SINTETICI e patrimonio_esempio.csv (tre edifici, uno per tipo di dato)
costruisci_dpr412.py  rigenera dati/dpr412.* (Normattiva + elenchi ISTAT di comuni, soppressi e variazioni)
abbinamento_dpr412.md scelte e casi dell'abbinamento al codice ISTAT attuale (refusi, fusioni, cambi di nome)
costruisci_mappa.py  genera dati/mappa/ dai confini Gramscii (versione bloccata) e da comuni.parquet nazionale
scarica_font.py      scarica i caratteri usati (Hanken Grotesk, Barlow; OFL) e scrive font/font.css: i visitatori
                     non chiamano Google Fonts; --solo-css riscrive solo font.css dai file presenti
costruisci_pagine.py rimette in tutte le pagine testata, piè e parte comune del <head> da parti/, e il numero di
                     versione (--versione); test in tests/test_costruisci_pagine.py
parti/               testa.html, testata.html, piede.html: le parti comuni delle pagine, da modificare solo qui
```

Menu di tutte le pagine: Previsioni, Patrimonio, Legge 10, Dati storici, Come funziona, F.A.Q., Sitografia, Mirror, Contattaci, Iscriviti (modulo
di listmonk). Piede: Contattaci · Licenza. Le pagine di testo (`.articolo`) occupano tutta la larghezza dello schermo
(27/10/2026). ANNCSU (anncsu.open.agenziaentrate.gov.it), Agenzia delle Entrate, ISTAT e Zornade sono sempre
collegati nel testo delle pagine (non nei titoli delle F.A.Q., dove il clic apre la risposta).

## Tre pagine di Edifici sperimentali (09/11/2026 f, `?v=20261109f`)

Decisione di Paolo delle 22:15: **Obblighi di legge**, **Geometria e luce naturale** e **Consumi, firma energetica e
priorità** tornano voci cliccabili del gruppo Edifici con l'etichetta **sperimentale** (`cantiere prova`: «S» nelle
tendine, parola intera nel menu del telefono). Le pagine non hanno più l'avviso «Pagina in lavorazione»
(`costruisci_pagine.py` lo mette solo alle voci `voce-corso`). Le altre voci di Edifici restano in lavorazione. Test in
`tests/test_costruisci_pagine.py` (`EDIFICI_SPERIMENTALI`, 8 «S», 13 voci in lavorazione).

## Correzioni dalle prove di Paolo delle 21:05 (09/11/2026 e, `?v=20261109e`)

Procedura T di `AGGIORNAMENTO_2026-11-09e.md`; prove nel browser `tests/test_prove_0911e_browser.py` (6).

- **Indicatore di caricamento «impazzito»** (orologio di 600–700 px): causa vera la regola generica `.mappa img, .mappa svg
  { width: 100%; height: auto }` di `stile.css`, che dava all'icona dentro la mappa la larghezza del suo riquadro (fino a
  `calc(100% - 70px)`). Ora **clessidra** (`svg.carico-icona` con `width`/`height`, selettore `.mappa .carico-mappa
  svg.carico-icona` più forte, `clamp(16px, 1,4vw, 26px)`, `flex: none`, `max-width`/`max-height` 26 px; testo
  `clamp(11px, 0,85vw, 14px)`; riquadro al più 40 px di altezza e 34em di larghezza); la clessidra si capovolge piano
  (2,4 s), ferma con `prefers-reduced-motion`. Provato a 375, 1366, 1920 px, con lo zoom del browser al 150 %, con la
  mappa allungata dalla maniglia, in 2D e in 3D, in Modelli 3D e in Ortofoto.
- **Verifica anti-robot meno frequente** (`protezione.js`): il gettone di sessione sta in `localStorage` (comune a tutte le
  schede e alle visite successive finché vale; evento `storage` tra le schede; ripiego su `sessionStorage`); dal server vale
  60 minuti ed è legato a rete e browser. Turnstile (e le righe del suo riquadro in Console) si carica al più una volta
  all'ora per browser, non più a ogni scheda.

## Correzioni dalle prove Q8 di Paolo (09/11/2026 d, `?v=20261109d`)

Procedura S di `AGGIORNAMENTO_2026-11-09d.md`; prove nel browser `tests/test_prove_0911d_browser.py` (7).

- **Indicatore di caricamento** (aggiunta delle 15:49, `protezione.js`, `.carico-mappa`): conta le richieste di tessere in
  volo (ortofoto, strati, terreno, edifici e alberi OSM) e mostra sulla mappa (in basso a sinistra, sopra la scala) un
  orologio con «Carico le tessere… (N)», il nome della fonte se una tessera aspetta più di 3 s («… risposta lenta») e i
  lavori lunghi delle pagine (`EUGENIO_LIMITI.lavoro(testo)` → funzione che lo chiude; «Genero il 3D…»); compare dopo
  400 ms, `aria-live="polite"`, lancetta ferma con `prefers-reduced-motion`; HTML sopra la mappa, fuori dal PNG. Su tutte le
  mappe agganciate con `EUGENIO_LIMITI.collega(m)`.

- **Righe rosse delle particelle** (`protezione.js`): con la fase 4 le tessere d'errore sono risposte 200; «occupata» (turno
  verso la fonte non arrivato in tempo: il nostro ritmo) **non conta più come errore** e non ferma la fonte, fa solo
  ricaricare le tessere poco dopo (era la causa di «Sentinel-2 cloudless 2016 non risponde, ferma per 30 s»); un timer di
  ricarica per famiglia (prima uno solo per tutte).
- **Tegola**: si spegne con «Cerca l'indirizzo», «Cerca la particella», «Reset», Invio nei campi della ricerca e con un
  edificio scelto dalla ricerca (`trovato`).
- **Tetto a falde con il cortile** (`edifici_calcoli.js`, `tettoDistanza`): per i corpi con cortile e le piante complesse
  (L, U, T, sotto il 70 % del rettangolo minimo) ogni punto del tetto è alto gronda + tan(inclinazione) × distanza dal
  bordo più vicino, esterno o del cortile (approssimazione dello straight skeleton: lati quasi allineati uniti, griglia da
  0,3 m al più ~15.000 punti, una falda piana per lato con quota dalla retta del lato); stesse falde di sempre (tabella,
  gradini, aree FV, report). La corte di prova 40 × 30 m con cortile 20 × 10 m dà 8 falde (4 verso la strada, 4 verso il
  cortile) e colmo a gronda + 5 m × tan 22°. I corpi rettangolari restano a capanna o a padiglione.
- **Maniglia dell'altezza della mappa** (`divisore.js`, `.maniglia-mappa`): sotto ogni mappa MapLibre delle pagine con la
  colonna della mappa (Modelli 3D e le pagine 3D, Ortofoto, Aggiungi edifici, Importa DXF/IFC); mouse, dito (pointer
  events) e frecce; da 280 px al 92 % della finestra; ricordata per pagina (`altezza-mappa:<pagina>:<id>`); doppio clic:
  predefinita; `eugenio:ridimensiona` durante e dopo (resize di MapLibre, anche in 3D). Patrimonio ha la mappa SVG e non
  ne ha bisogno. In più `flex-shrink: 0` per tutte le pagine 3D: in fv-producibilita la mappa si restringeva sotto il testo.
- **Clic nella vista 3D** (`piuVicinoAllaCamera`): MapLibre trova già i prismi estrusi sotto il puntatore (pareti e tetti:
  provato, 60 px sopra la pianta di un corpo alto si trova il corpo) ma nell'ordine degli strati; la pagina prende il più
  vicino alla camera (`transform.getCameraLngLat`/`getCameraAltitude`, centro del prisma a metà altezza). Vale per la
  scelta e per la tegola, anche per i vicini; in 2D resta la sagoma.
- **Alberi da OpenStreetMap** dove manca il LiDAR: con «Alberi» acceso la pagina chiede `/api/alberi/osm/<cella>.json`
  per le celle senza LiDAR (dove c'è vince il LiDAR); chiome più chiare (`#a9c98a`), quota del terreno dell'edificio,
  dichiarate nella nota («chiome indicative da OpenStreetMap…, entrano anche nelle ombre, come stima»), in legenda,
  nell'immagine e nel report. **Decisione**: entrano nelle ombre, come stima, solo con la casella «Alberi» accesa (spenta:
  restano solo le chiome LiDAR, che stanno sempre tra gli ostacoli).

## Correzioni dalle prove P9 di Paolo (09/11/2026 c, `?v=20261109c`)

Procedura Q di `AGGIORNAMENTO_2026-11-09c.md`; prove nel browser `tests/test_prove_0911c_browser.py` (9).

- **Tetti (decisione di Paolo del 09/11/2026, sostituisce la cascata automatica dell'08/11)**: **tutti i tetti partono
  piani** (altezza di gronda). Sezione nuova **«(4) Coperture»** nel pannello di destra delle 9 pagine 3D, tra «Edificio» e
  «Corpi» (i passi si rinumerano da soli, `numeraPassi`): pulsante-interruttore **tegola** (`#tegola`, icona SVG isometrica,
  `aria-pressed`, tooltip «Tetto a falde: clic su un edificio per cambiarlo»; cursore della mappa con la tegola; Esc la
  spegne), **Inclinazione** (`#inclinazione-tetti`, 22° all'inizio, 5–60°), **«Reset piani»** con la conferma **nella
  pagina** (`#conferma-reset`: «Sì, riporta tutti piani» / «Annulla»; mai `confirm()`), **«Esporta tetti» / «Importa
  tetti»** (JSON `{"tipo": "eugenio-tetti", "versione": 1, "tetti": {"<archivio>|<id corpo>": {"i": 22, "t": …}}}`, al
  più 2 MB, voci controllate) e la riga di stato `#stato-tetti`. Con la tegola accesa un clic (2D o 3D, `cliccaTegola`)
  trova il corpo sotto il puntatore (edificio scelto, vicini, o dalle celle dell'archivio con `contesto`) e alterna piano ↔
  falde all'inclinazione corrente; il clic non sceglie l'edificio. Forma: `E.tettoScelto` (`edifici_calcoli.js`): capanna
  sul lato lungo, padiglione se quasi quadrato o se la pianta riempie meno del 70 % del rettangolo minimo
  (`faldeStimate(…, {forza: true})`); restano piani solo i corpi con cortile o più stretti di 2 m (lo dice la riga di
  stato). **Dove si registra**: nel browser, `localStorage` chiave `eugenio-tetti-v1` (con try/catch: senza archivio le
  scelte valgono fino alla chiusura); chiave `archivio|id del corpo`, archivio = percorso sul server (`cc-by/er/cesena`),
  `osm`, `reg-<regione>` (sagome regionali), `locale`, `demo`. I vicini con il tetto a falde si disegnano nel layer
  `tetti-vicini` (prisma fino alla gronda) e nelle falde a gradini; la loro versione piatta delle tessere si nasconde; in
  2D bordo color mattone (`corpi*-2d-tetto`). Nota «Tetti: N a falde scelti dall'utente (22°), P piani» sotto la mappa, in
  legenda, nell'immagine, nella tabella dei corpi («tetto a falde scelto dall'utente (22°)») e nel report
  (`tetti.scelti`). Pagine Edificio e Fotovoltaico: «Forma dei tetti» con **«Scelti dall'utente»** e **«Tutti piani»**.
  Le falde LiDAR (le celle `lidar/falde/` non si chiedono più), la stima dal colmo DBTR e l'ipotesi 22°/32°
  (`tettoIpotizzato`) restano nel codice ma sono **sospese**.
- **Rilievo**: tolta la riga «Rilievo ×1 ×1,5 ×2» della barra 3D (modifica di Paolo delle 11:56): terreno sempre ×1.
- **Fonte dell'ortofoto scelta da sola** (`confini_gl.js`, `fontiNelPunto`): le fonti nazionali (regione «00») valgono nel
  riquadro, quelle regionali solo nella loro regione (confini ISTAT; entro ~150 m dal confine anche la regione accanto).
  Modelli 3D e pagine 3D (`opzioni` di `edificio3d.js`), Ortofoto (`elenco`), Aggiungi edifici e Importa DXF/IFC (con
  `confini_gl.js` caricato) mostrano solo le fonti applicabili e scelgono la migliore (regionale a 20 cm dove ha
  immagini, poi AGEA 2012, poi Sentinel-2); scelta a mano tenuta finché applicabile, poi automatico con ««…» non copre
  questo punto: torno alla scelta automatica».
- **Fonti che non rispondono** (`protezione.js`): le tessere d'errore del server (`X-Ortofoto-Errore`), i 5xx e la rete
  caduta si contano per fonte; 4 errori in 60 s, o «ferma» dal server, fermano la fonte per il `Retry-After` (30 s–20
  min) con la nota sotto la mappa «Ortofoto «…»: la fonte non risponde (o è molto richiesta). Mi fermo e riprovo da solo
  tra N minuti.»; un errore isolato fa ricaricare le tessere poco dopo. I nomi delle fonti arrivano da `/api/ortofoto/fonti`.
- **Alberi**: anche nella mappa 2D (layer `alberi-2d`, da zoom 15, chiome attorno al centro) e nota se lì non ce ne sono
  (oggi le chiome esistono solo nella fascia costiera della zona di Rimini, dove la pipeline ha il DSM della costa 2019).
- **Console**: le righe di `challenges.cloudflare.com` (CSP «connect-src … data:», «OTS parsing error», avvisi WebGPU
  «powerPreference … ignored», «No available adapters») vengono dal riquadro di Turnstile, che si carica solo alla prima
  richiesta protetta (ricerca, edifici OSM, Patrimonio…): EuGEnio non usa WebGPU e la sua CSP ha solo `frame-ancestors`.

## Correzioni dalle prove N10 di Paolo (09/11/2026 b, `?v=20261109b`)

Procedura P1–P10 in `AGGIORNAMENTO_2026-11-09b.md`. Prove nel browser in `tests/test_prove_0911b_browser.py` (10).

- **Ricerca unificata** (`cerca_luogo.js`, `stile.css`; Modelli 3D, Ortofoto e le 8 pagine 3D): un solo modulo
  `#cerca-luogo-modulo` con **Comune** una volta sola in cima (`#cerca-comune`), **Indirizzo** (`#cerca-via`), **Foglio** e
  **Particella** affiancati (`#catasto-foglio`, `#catasto-particella`), poi «Cerca l'indirizzo» (`#cerca-indirizzo`: solo
  Comune e Indirizzo), «Cerca la particella» (`#cerca-particella`: solo Comune, Foglio e Particella) e un solo «Reset»
  (`#cerca-reset`). Con il solo Comune tutti e due vanno al centro del comune. Invio in Indirizzo cerca l'indirizzo, in
  Foglio o Particella la particella, nel Comune quello che è scritto. Spariscono `#catasto-comune`, `#reset-indirizzo`,
  `#reset-particella` e i due `<form>`. Prima, con due «Comune» diversi (Bagno di Romagna nella particella, Susegana rimasto
  nell'indirizzo) la ricerca finiva a «via San Salvatore 13, Susegana». In più un risultato in un **altro comune** (il
  server scrive «comune catastale … diverso da quello indicato» e i nomi non hanno nulla in comune) non sposta la mappa lì:
  si va al centro del comune scritto, con l'avviso. Apertura su Cesena e precedenza dei parametri invariate.
- **Colore e Alberi sotto la mappa** (`edificio3d.js`, `controlliAspetto3d`; `stile.css`): la riga `#aspetto-3d` va in
  `#comandi-edificio`, dopo `#sposta-ortofoto` (frecce, stato, «Azzera»), non più nel pannello di destra sotto i livelli;
  etichetta visibile «Colore» (il nome intero «Colore degli edifici» nel tooltip e nell'`aria-label` del pulsante), stato
  dell'ortofoto al più 10rem: a 1366 px Genera il 3D, frecce, stato, Azzera, Colore e Alberi su una riga; con la colonna
  stretta il gruppo va a capo intero, nessuno scorrimento di lato a 375 px. In Ortofoto non ci sono questi comandi.
- **Celle LiDAR** (`edificio3d.js`, `haCellaLidar`): falde e alberi si chiedono solo per le celle dell'elenco `celle` di
  `lidar/indice.json` (fase 10); con un indice senza elenco solo dentro il riquadro di un archivio dell'Emilia-Romagna. Prima
  ogni cella attorno al punto, anche a Roma e a Susegana: decine di 404 in Console. `importa_modello.js` chiede le celle di
  contesto solo se sono in `nomi_celle`. Demo del sito con l'elenco.
- **Terreno fuori dall'Emilia-Romagna**: la pagina accendeva già il terreno ovunque, ma lo spegneva per gli edifici OSM e
  le sagome regionali **senza quota**; il server ora dà la quota Copernicus (fase 4), quindi Susegana è in rilievo anche
  senza il DTM del Veneto ed esagerazione ×1,5/×2 funziona. Messaggio «Quote dei corpi dal terreno del server (DTM regionale
  o, dove manca, Copernicus DEM 90 m).».
- **Ortofoto segnaposto**: con le tessere della Toscana vuote (fase 4) a Bagno di Romagna la pagina passa da RER (vuota) a
  Toscana (vuota) ad AGEA 2012 e lo scrive; prima restava la Toscana con le scritte bianche.
- Novità: voce `20261109b` (ricerca e comandi sotto la mappa).

## Correzioni dalle prove J10 di Paolo (09/11/2026, `?v=20261109a`)

Procedura N1–N12 in `AGGIORNAMENTO_2026-11-09.md` (con Roma e Bari intere). Prove nel browser in
`tests/test_prove_0911_browser.py` (7: limite orario, ricerca e Torino, clic, colore e alberi, frecce su una riga a 360,
375 e 1366 px).

- **Limiti orari delle fonti della mappa** (`protezione.js`, `window.EUGENIO_LIMITI`): un 429 di ortofoto, strati
  (particelle e contorni), edifici OSM o terreno ferma quella fonte per il tempo del `Retry-After` del server (da 30 s a
  20 minuti; senza intestazione 3 minuti); intanto la pagina risponde da sé con un 429 senza rete (niente righe in
  Console, nessun carico). Nota `#nota-limiti` (classe `aiuto nota-limiti`) **sotto la mappa, prima di
  `#comandi-edificio`** (o di `.comandi-ortofoto`): «Ortofoto: raggiunto il limite orario di richieste per il tuo
  indirizzo. Mi fermo e riprovo da solo tra N minuti.»; alla fine della pausa evento `eugenio:limite` (`fermo: false`): le
  mappe collegate con `EUGENIO_LIMITI.collega(m)` (Modelli 3D e pagine 3D, Ortofoto, Aggiungi edifici, Importa DXF/IFC)
  **tolgono e rimettono** sorgente e strati della fonte (`setTiles` e `refreshTiles` su tessere raster in errore fanno
  fallire il disegno in MapLibre 5.24: TypeError «reading 'bind'»), `strati_gl.js` richiede le tessere OSM mancanti (gli
  errori non si ricordano più); la nota sparisce alla prima risposta buona. `collega` toglie anche gli errori delle tessere
  dalla Console. Prova a mano: `EUGENIO_LIMITI.ferma('ortofoto', 120)` nella Console.
- **Previsioni** (`index.html`): tolto l'avviso «Servizio sperimentale» (come Dati climatici e Legge 10).
- **Frecce dell'ortofoto** su una riga (`sposta_ortofoto.js`, `stile.css`): ← ↑ ↓ →, «1 m», stato (accorciato con i
  puntini, intero nel `title`) e «Azzera», anche con la colonna stretta; il contenitore nei comandi si restringe
  (`min-width: 0`), nessuno scorrimento di lato a 360 px.
- **Ricerca** (`cerca_luogo.js`): Comune prima dell'Indirizzo; «Reset» (`#reset-indirizzo`, `#reset-particella`) svuota i
  campi del suo blocco e il messaggio. `dati/mappa/01.json` e `15.json` avevano `NaN` (comune «None» di Torino, sigla
  «NA» di Napoli letti come vuoti): il browser non li leggeva e **Piemonte e Campania** mancavano alla ricerca per comune.
  Corretti i file, `costruisci_mappa.py` (`allow_nan=False`, nome e sigla testuali) e la lettura dell'elenco ISTAT nella
  fase 3; test `test_confini_json_validi_per_il_browser`.
- **Clic sulla mappa** (`edificio3d.js`, `ortofoto.js`): non sposta mai la vista; regione e comune si evidenziano con il
  messaggio (prima `fitBounds` sul comune o sulla regione: a Roma «la mappa impazzisce»). La piccola mappa, la ricerca, la
  rotella e il trascinamento spostano la vista come prima.
- **Colore degli edifici e alberi** (Modelli 3D e pagine 3D, riga `#aspetto-3d` sotto i livelli): menu `#colore-edifici`
  con le classi del menu dell'asterisco (`vestito-pulsante`, `vestito-elenco a-discesa`) e la stessa tastiera; grigio
  (`--serie-6`), giallo `#e0b400`, rosso `#c62828`, indaco `#4757c9`, violetto `#8a4fd0`; scelto in arancio (`--primario`),
  OSM marrone. Casella `#strato-alberi` spenta in partenza; chiome come ottagoni un po' più larghi della cella di 2 m (si
  fondono), verde per altezza, base al 40 %. `localStorage`: `eugenio-colore-edifici`, `eugenio-alberi-3d` (try/catch).
  Legenda (`.pallino.vicini` col colore, `#legenda-alberi`) e riga «Colori: …» del PNG coerenti.
- **Tetti ipotizzati** (`edifici_calcoli.js`, `cortiliDi`): cortile solo se il buco è di almeno 25 m² o del 10 % della
  pianta (Bagno di Romagna, foglio 54 particella 216: un buco di 8 m² occupato da un corpo interno rendeva piano il tetto);
  stessa regola in `fase10-edifici3d/edifici3d/tetti.py`.
- **Fonti vuote** (`edificio3d.js`, `ortofoto.js`): con la fonte scelta da sola, la pagina prova la tessera al centro;
  se il server dice `X-Ortofoto-Vuota: 1` (RER 2023-24 senza immagini, per esempio a Bologna) passa alla fonte successiva
  e lo scrive; zone ricordate a tessere dello zoom 12. Una scelta a mano non si cambia.
- `costruisci_pagine.py` aggiorna anche il `?v=` delle pagine di `sito/interno/` (prima a mano).

## Menu dell'08/11/2026, ricerca col solo comune, apertura su Cesena (decisioni di Paolo, stessa versione `?v=20261107b`)

Per la newsletter del 12/11 il sito mostra come servizi solo quelli usabili.

| Gruppo (`data-gruppo`) | Voci accessibili | Voci in lavorazione (triangolo giallo, non cliccabili) | GME |
|---|---|---|---|
| Clima e meteo (`clima`) | Dati climatici, Legge 10, Previsioni, **Cambiamento climatico** S (`edificio-clima.html`, prima «Clima che cambia» nel gruppo Edificio) | — | — |
| Patrimonio (`patrimonio`) | Patrimonio, Ortofoto S, LiDAR (triangolo, come prima), Modelli 3D S, Importa DXF/IFC S, Aggiungi edifici S, Scaricare i DB topografici, Visure (triangolo, come prima) | — | — |
| **Edifici** (`edificio`, prima «Edificio») | — | **Obblighi di legge** (prima voce), Geometria e luce naturale, Consumi, Fabbisogno UNI, Facciate e tetti, Pompe di calore e solare termico, **Ecobonus** e **Conto Termico** (segnaposto nuovi: `edificio-ecobonus.html`, `edificio-conto-termico.html`) | — |
| Cogenerazione (`cogenerazione`) | — | Emissioni | 5 voci |
| Fotovoltaico (`fotovoltaico`) | — | Ombre, Sole e irradiazione, Producibilità, PVGIS, D.Lgs. 199/2021, LEED, **Comunità energetiche** (`edificio-cer.html`) | Prezzo catturato |
| Statistiche (`statistiche`) | Costi energetici Sanità | — | — |

- **Voci in lavorazione**: `<span class="voce-gme voce-corso" data-pagina=… aria-disabled="true" title="In lavorazione:
  disponibile prossimamente">` con il triangolo giallo, stesso comportamento delle voci GME (non cliccabili, attenuate,
  nota al tocco, `aria-current` sulla propria pagina; nella riga fissata come nella tendina). Indirizzi delle pagine
  invariati; `data-gruppo="edificio"` invariato (la scelta «menu fissato» dei browser resta valida). Le frecce della
  tastiera in un gruppo senza collegamenti non danno più errore (`aspetto.js`).
- **`costruisci_pagine.py`** ricava dal menu della testata (`gruppi_menu`, `pagine_in_corso`): l'elenco **«Nello stesso
  gruppo»** di ogni pagina che lo ha (voci in lavorazione e GME senza collegamento), l'**etichetta del gruppo** sopra il
  titolo (`<p class="gruppo-servizio">`) e, nelle pagine in lavorazione, l'**avviso in cima** «Pagina in lavorazione, non
  ancora verificata» tra `<!-- in-lavorazione -->` e `<!-- /in-lavorazione -->` (tolto da sé se la pagina torna
  accessibile). `--controlla` lo verifica come il resto. Per aprire una pagina basta cambiare la sua voce in
  `parti/testata.html` in un collegamento e rigenerare.
- **Nessun collegamento** del sito alle pagine in lavorazione (test `test_nessun_collegamento_interno_alle_pagine_in_lavorazione`,
  come per le GME): tolti in Sitografia (PVGIS, Obblighi), in Cambiamento climatico (firma dalla pagina Consumi), fra le
  pagine in lavorazione (LEED, CER, Facciate e tetti) e nelle Novità; Patrimonio e Modelli 3D non ne avevano.
- **Tendine** larghe quanto la voce più lunga (`width: max-content`, al massimo 30rem e dentro la finestra): nessuna voce
  va a capo a 900, 1000 e 1366 px (prima 17rem: «Cogeneratore sull'edificio…», «Consumi, firma…» su due righe).
- **Barra di scorrimento a sinistra** nella colonna della mappa di **tutte** le pagine a due colonne (`main.strumento >
  .mappa-area`: `overflow-y: auto`, `direction: rtl`, figli `ltr`), anche in Patrimonio (prima nascosta); telefono invariato.
- **Ricerca**: esempio «viale Ghirotti 286», «Cesena» (foglio 149, particella 387 nel modulo catastale) in `cerca_luogo.js`;
  il solo comune, in tutti e due i moduli, porta al centro del comune in Modelli 3D, Ortofoto e nelle 8 pagine 3D (provato
  pagina per pagina in Chromium). **Previsioni**: il solo nome del comune (o «…, Comune») propone «Comune di X (PR)» che
  sceglie il comune senza chiamare il server; le risposte senza coordinate (0,0) non compaiono (anche il server le scarta in
  `/api/geocodifica`); esempio «Es. viale Ghirotti 286, Cesena, o solo il comune». Legge 10 e Dati climatici cercano solo
  comuni: invariate.
- **Apertura su Cesena** (`EUGENIO_CERCA.PARTENZA`, 44,1326 N 12,2597 E, zoom 15,6): Ortofoto, Modelli 3D e pagine 3D si
  aprono sull'ospedale Bufalini e la collina se l'indirizzo non porta `lat`/`lon`, `sede`, `edificio`, `modello`, `dbtr`,
  `archivio` e la regione scelta è l'Emilia-Romagna (con un'altra regione ricordata, Modelli 3D va su quella). Centro dal
  DBTR di Cesena: i 59 corpi della particella foglio 149 n. 387 (baricentro 44,1338 N 12,2597 E, quote 38–59 m), spostato
  di ~130 m a sud per la collina. Nota: il punto indicato nella richiesta (44,1405 N 12,2405 E) cade ~2 km più a nord-ovest,
  in una zona residenziale. Patrimonio, Previsioni e Legge 10 non cambiano apertura.
- Test: `test_costruisci_pagine.py` (menu, voci in lavorazione, avviso, nessun collegamento, «Nello stesso gruppo»,
  esempio e partenza), `test_menu_browser.py` (sei gruppi, tendine su una riga, voci non cliccabili, tastiera),
  `test_mappe_browser.py` (ricerca col solo comune e apertura su Cesena nelle 10 pagine, precedenza dei parametri,
  Previsioni, barra a sinistra con le barre vere di Chromium); fase 4 `test_geocodifica_scarta_le_coordinate_zero`.

## Tetti a falda, sagome del Veneto e terreno veneto (08/11/2026, stessa versione `?v=20261107b`)

> **Sospeso dal 09/11/2026 c**: la cascata automatica dei tetti descritta qui sotto non è più usata dalle pagine (tutti i tetti partono piani, tetti a falde scelti dall'utente in «Coperture»: vedi la sezione del 09/11/2026 c). Resta come documentazione del codice.

Decisioni di Paolo dell'08/11 (sezione I di `AGGIORNAMENTO_2026-11-07.md`):

- **Forma dei tetti, tre fonti** (`edifici_calcoli.js`: `rettangoloTetto`, `tettoIpotizzato`, `zonaAltimetrica`,
  `motivoTettoPiano`, `IPOTESI_TETTO`; gemello Python `fase10-edifici3d/edifici3d/tetti.py`): falde LiDAR → tetto stimato
  dal colmo DBTR → **tetto ipotizzato a falde, 22° in pianura, 32° in montagna** (quota del terreno sotto il corpo ≥ 600 m
  al Nord, ≥ 700 m al Centro-Sud; senza quota l'altitudine del comune del DPR 412/93) → piano per i corpi plausibilmente
  piani (capannoni, commerciali, palestre, tettoie; oltre 1.500 m² o lato corto oltre 25 m; gronda sotto 3 m; cortili e
  forme poco rettangolari). `edificio3d.js`: `conFalde` ricorda i valori del DBTR (`c.base`) e il record LiDAR,
  `applicaTetto(c, scelta)` sceglie la fonte (`c.fonteTetto`: `lidar`, `colmo`, `ipotesi`, `piano`, `modello`, `utente`);
  il modello DXF/IFC e i corpi corretti a mano non cambiano.
  - **Modelli 3D**: cascata per ogni corpo; **nota sotto la mappa** `#nota-tetti` («Tetti: N misurati dal LiDAR, M stimati
    dal colmo DBTR, K ipotizzati (22° pianura / 32° montagna: …), P piani»), voce di legenda `#legenda-falde` con i
    conteggi, riga nell'immagine scaricata, sezione nel report (`tetti` del corpo del report, `fonte_tetto` per corpo),
    motivo del tetto piano nella tabella dei corpi.
  - **Edificio e Fotovoltaico** (8 pagine): selettore **«Forma dei tetti»** (`#forma-tetti`, nel passo «Corpi › Falde dei
    tetti»): «Misurata (LiDAR) dove c'è», «Stimata dal colmo DBTR dove c'è», «Ipotesi automatica (22°/32°)», «Tutti piani»;
    le scelte non disponibili sono spente con il motivo (nell'opzione e in `#motivi-forma-tetti`); predefinita la più
    affidabile disponibile. Le prime due scendono la cascata dove manca la fonte. Il cambio ricalcola tetti, aree FV (non
    quelle con inclinazione o orientamento corretti a mano), ombre, producibilità e sole sulle facciate (se erano già
    calcolati); la scelta è scritta nei messaggi dei risultati, nella nota e nel report. Orizzonte vicino: stessa logica
    (colmo o gronda dei corpi).
  - Tabelle di obblighi, PVGIS e facciate dentro `.tabella-scorre` (a 375 px la tabella degli obblighi allargava la pagina).
- **Sagome del Veneto con le altezze OSM**: la pagina chiede sempre `/api/edifici/osm`; in Veneto il server risponde con le
  sagome della Regione (`regione_sagoma`, licenza `IODL 2.0; altezza ODbL 1.0`) e `sagome`. Messaggio «Sagome dalla
  Regione del Veneto (IODL 2.0), altezze da OpenStreetMap dove ci sono, altrimenti stimate», stesso colore marrone degli
  edifici OSM (legenda «edifici OpenStreetMap o sagome regionali»), livello «sagome regionali con altezze OSM o stimate»
  nella fonte per corpo, origine `osm_vicini` nelle altezze, attribuzioni IODL 2.0 + ODbL in pagina, immagine e report.
  Se i corpi hanno la quota dal DTM del server (`quota_terreno`), la vista 3D ha il terreno vero e il tetto usa la quota.
  Privacy: voce del WFS della Regione del Veneto.
- **Terreno da più DTM**: legenda dal nome del DTM della tessera (`X-Terreno-Nome`, es. «DTM 5 m da voli LiDAR Regione del
  Veneto (IODL 2.0)»); attribuzione del terreno con ER e Veneto.
- Novità (riga in «Nuovo»), `EUGENIO_PER_AGENTI.md`, `llms.txt`, test `test_tetti_in_cascata_in_modelli3d`,
  `test_forma_dei_tetti_a_scelta_in_fotovoltaico`, `test_sagome_venete_con_altezze_osm_in_modelli3d`,
  `test_tetti_e_sagome_regionali_documentati`.

## Ortofoto spostabile di 1 m (08/11/2026, stessa versione `?v=20261107b`)

Richiesta e decisioni di Paolo dell'08/11: frecce per compensare a occhio gli scarti di 1–5 m tra foto e cartografia
(F.A.Q. `#sfasamento`).

- `sito/sposta_ortofoto.js` (nuovo, `window.EUGENIO_SPOSTA`): quattro frecce (dal 09/11/2026 su una riga ← ↑ ↓ →; prima a croce) (↑ nord, ↓ sud, ← ovest, → est,
  1 m a clic; con il fuoco su una freccia anche i tasti freccia), stato «Ortofoto spostata: 2 m E, 1 m S» e «Azzera».
  Spostamento della **sola ortofoto**: particelle, contorni, sagome degli edifici e contesto Sentinel-2 restano fermi.
  La pagina cambia solo l'indirizzo delle tessere della sorgente `ortofoto` (`setTiles`, con `&de=…&dn=…` e attesa di
  350 ms dopo l'ultimo clic): nessun movimento della camera, uguale in 2D e in 3D. Il resto lo fa il proxy (README della
  fase 4: BBOX WMS spostato, nessuna copia su disco).
- **Attive solo** con un'ortofoto spostabile accesa (`spostabile` in `/api/ortofoto/fonti`: le fonti WMS – RER, Toscana,
  Bolzano, Trento, Geoportale Nazionale) **e** almeno uno strato vettoriale acceso (Ortofoto: contorni dell'archivio,
  particelle o contorni degli edifici dei livelli; pagine 3D: sono sempre disegnate le sagome degli edifici dell'archivio
  o di OpenStreetMap, quindi basta l'ortofoto accesa). Altrimenti spente, con il motivo nel `title` dei pulsanti e del
  gruppo e nel testo di stato (`aria-describedby`): «Accendi un'ortofoto e almeno uno strato vettoriale (particelle o
  contorni) per allineare la foto alla cartografia»; Sentinel-2 cloudless e ortofoto dei siti in PMTiles: «tessere già
  pronte…» (MapLibre non sa spostare uno strato raster). I confini ISTAT non contano (generalizzati, ~100 m).
- Dove: in `#comandi-edificio` accanto a «Genera il 3D» nelle 9 pagine 3D (nascoste nella demo sintetica); in Ortofoto
  sotto la mappa accanto a «Scarica l'immagine» (`.comandi-ortofoto`).
- Sessione: `sessionStorage` (`eugenio-sposta-ortofoto:<pagina>`, con try/catch), ripreso solo per la stessa fonte;
  cambiare fonte azzera.
- Immagine scaricata: riga «Ortofoto spostata manualmente di 2 m E, 1 m S rispetto alla cartografia.»; report: `de` e
  `dn` nella vista con l'ortofoto, la didascalia lo dichiara (`report_servizi.testo_spostamento`).
- F.A.Q. `#sfasamento`: una frase sulle frecce. `novita.toml` riscritto (gruppi Nuovo / Migliorato / Verificato, sezione
  «Novità» sotto): le frecce in «Nuovo» della voce `20261107b`; in fondo la voce
  «Meet EuGEnio» del 26/10/2026 (solo `testo`, senza versione: `costruisci_pagine.py` accetta la versione mancante solo
  per una voce con il solo testo; ancora `#d20261026`).
- Test: `test_ortofoto_frecce_spostano_la_foto_non_i_vettori`, `test_modelli3d_frecce_in_2d_e_3d` (Modelli 3D e
  Ombre FV: stati attivo/spento e tooltip, indirizzi delle tessere, vettori e camera fermi, «Azzera», Sentinel-2, nessun
  errore in console), `test_spostamento_ortofoto_documentato`, «Meet EuGEnio» in `test_novita_versione_feed_e_menu`.

## Correzioni dalle prove di Paolo (07/11/2026 sera, `?v=20261107b`)

Dettagli e procedura J1–J12 nella sezione I di `AGGIORNAMENTO_2026-11-07.md`.

- **Dati climatici e Legge 10** senza l'avviso «Servizio sperimentale» (validate, come Costi energetici Sanità).
- **Pagine 3D e Ortofoto**: la ricerca (`cerca_luogo.js`) è il **passo 1 della colonna destra** (`#passo-cerca`), prima dei
  livelli; con il **solo comune** la mappa va al centro del comune (baricentro del confine ISTAT di `dati/mappa/<regione>.json`,
  zoom 14, nessuna chiamata); una risposta senza coordinate (vuota o 0,0) porta al centro del comune con l'avviso. Barra di
  scorrimento della colonna della mappa **a sinistra** (`direction: rtl` del contenitore, sul computer).
- **Modelli 3D** (`edificio3d.js`): quota del centro della camera = quota del terreno sotto l'edificio (prima 0 m: in collina
  la camera finiva dentro il versante, vista nera); rilievo ombreggiato (`hillshade`) con i colori del tema, esagerazione
  ×1/×1,5/×2 nella barra della vista 3D, legenda del terreno dalla fonte delle tessere (`X-Terreno-Fonte`); isometrica al
  doppio dell'edificio; tetti a falde stimati dal colmo DBTR (`faldeStimate` in `edifici_calcoli.js`); edifici OSM in
  marrone; nuova ricerca o mappa a oltre 2 km durante il 3D → 2D dritta e 3D azzerato; copertura vicino ai confini (corpo
  dell'archivio entro 150 m); celle chieste solo se in `indice.nomi_celle`; `lidar/indice.json` solo se `archivi.json` ha
  `lidar`; `archivi.json?v=<versione>` con `cache: "no-cache"`; Sentinel-2 cloudless anche nel selettore.
- **Immagini** (`esporta_mappa.js`): download diretto; la finestra «Salva con nome» solo con «chiedi dove salvarlo».
- **Aggiungi edifici**: zona «Trascina qui» (file e cartelle, senza finestre di sistema), esito di «Apri in Modelli 3D» e
  «Togli» accanto ai pulsanti (`#messaggio-3d`), tempo massimo per IndexedDB.
- **Pagina interna**: «Nessuna proposta in coda» con la coda vuota.
- **F.A.Q.** nuove: `#sfasamento` (particelle, sagome e ortofoto: scarti dei dati, misurati) e `#finestra-bloccata` (Chrome
  bloccato da una finestra di sistema).
- Test nuovi (Chromium): 19 comuni coperti senza OSM (`punti_19_comuni.json`), prove di Paolo nel 3D, ricerca per comune e
  0,0, telefono a 375 px senza scorrimento di lato, «Novità» con il colore di «F.A.Q.» in tutti i vestiti e temi.

## Preparazione

I file di mappa (tutta Italia) e i caratteri sono già inclusi. Si rigenerano solo quando cambiano
i comuni o la versione dei confini (vedi fase 7):

```bash
python costruisci_mappa.py --comuni <archivio fase 3>/comuni.parquet
python scarica_font.py             # solo se cambiano i caratteri; con --solo-css non usa la rete
```

**Testata, piè e versione (dal 27/10/2026 sera).** Testata, riga finale del piè e parte comune del `<head>` (script del
tema e del vestito, foglio di stile, icone) si modificano **solo** in `parti/`; nelle pagine stanno tra i marcatori
`<!-- testa -->`, `<!-- testata -->`, `<!-- piede -->` (e i loro `<!-- /… -->`) e si rigenerano con lo script, che segna
da sé la voce di menu della pagina (`aria-current="page"`). Le fonti di ogni pagina strumento (`.piede-fonti`) restano
nella pagina, sopra la riga finale. Prima di ogni pubblicazione che cambia stile, script o pagine:
```bash
python costruisci_pagine.py --versione 20261029a   # aaaammgg + lettera: nuova versione in pagine e script
python costruisci_pagine.py --controlla            # 0 = tutto aggiornato (lo usano anche i test)
python -m pytest tests                             # idempotenza, voce attiva, versione
```
La regione mostrata da `index.html` e `legge10.html` si sceglie con `?regione=RR` nell'indirizzo (predefinita 08,
Emilia-Romagna). `legge10.html?comune=037006` apre direttamente un comune (il link si aggiorna a ogni scelta).

Pubblicazione sul server (dal PC, con l'host `eugenio` di `~/.ssh/config`). Dal 27/10/2026 il worker del server
rifà da sé `dati/indicatori/` (ogni mese) e `dati/clima/` con i due CSV (gennaio e luglio): per non riportare sul
server le copie del PC, più vecchie, il sito si copia con un archivio che esclude `dati/indicatori` (il clima non è
nella cartella del PC):
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
scp ..\..\sito.tar.gz eugenio:~/
ssh eugenio "tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && rm ~/sito.tar.gz"
```
Caddy lo serve subito, senza riavvii. Le pagine richiamano `stile.css` e gli script con un numero di versione
(`?v=20261029a`): quando si cambiano stile o script, si aumenta con `costruisci_pagine.py --versione …`, così i
browser e Cloudflare non usano la copia vecchia rimasta in memoria.

Per vedere solo la grafica in locale: `python -m http.server -d sito 8000` (mappe visibili, dati no: servono le API).

## Pagina del patrimonio

Il file non viaggia intero:
- il browser lo legge in UTF-8 o, se non è valido, nella codifica di Windows di Excel;
- lo divide in blocchi di 40 righe e li manda uno dopo l'altro a `/api/patrimonio`, mostrando l'avanzamento,
  così nessuna richiesta supera i 100 secondi del tunnel Cloudflare;
- unisce i risultati;
- se il file non ha una colonna identificativa (`id`, `codice`…), numera le righe prima di dividerle, perché il
  server numererebbe da 1 in ogni blocco.

Se un blocco fallisce dopo il primo, la pagina mostra il risultato parziale e lo dice.

Mappa: regioni d'Italia (`italia.json`) con lo zoom sui punti trovati. Gli edifici trovati sono blu, quelli da
verificare rossi; i non trovati non hanno punto ma restano nell'elenco con la nota che spiega il motivo. Un clic
sul punto evidenzia la scheda e viceversa. Filtri per esito.

Download:
- CSV con `;`, decimali con la virgola e BOM per Excel, con tutte le colonne in uscita e le fonti in fondo;
- GeoJSON con `attribution_html`.

Il link "Dati elaborati da Zornade" è sempre visibile sotto il risultato e nel piè di pagina (obbligatorio con il
piano gratuito). L'ANNCSU è citato quando un punto viene da lì.

Prova del 26/10/2026 in Chromium (desktop, telefono, tema scuro) con API simulate: 95 edifici in tre blocchi,
CSV salvato da Excel con accenti, filtri, clic sui punti, download CSV.

## Pagina della Legge 10

Usa `/api/clima-legge10/{istat}?anni=5|10|30`. Mostra:
- sei cifre chiave: GG sul periodo della zona, zona risultante, GG sull'anno intero, tendenza per decennio,
  temperature di progetto invernale ed estiva con il metodo usato;
- l'avvertenza che i valori normativi restano obbligatori;
- il grafico dei GG per stagione con la media;
- la tabella mensile (T media, minima e massima, irradiazione globale e diffusa in MJ/m² al giorno, pressione
  del vapore, umidità, vento);
- i GG sul periodo di accensione di ogni zona.

Se il comune non ha una stagione completa, la pagina mostra il messaggio dell'API.

## Scelte grafiche

- La mappa è l'elemento principale: comuni dal chiaro al blu profondo secondo i gradi giorno previsti
  nei prossimi 7 giorni (più scuro = più riscaldamento). Tocca un comune per sceglierlo.
- Caratteri: Barlow per i titoli, Hanken Grotesk per il testo (dal 27/10/2026; Bricolage non si usa più).
- Vestiti (27/10/2026): 5 combinazioni di colori (Corallo predefinito, Ambra, Indaco, Lime, Verde), scelte con
  l'asterisco ✱ accanto a ◐ (`aspetto.js`); tema scuro predefinito. Loghi in `logo/<vestito>/`; regole, variabili e
  come aggiungere un vestito nel proprio mirror in `README_stile.md`.
- Nel grafico è evidenziata la zona in cui il meteo viene dal modello globale (oltre 48–72 h) o
  dalla climatologia (oltre 15 giorni), con l'avviso testuale sotto.
- Tema chiaro/scuro automatico, adatto al telefono, navigabile da tastiera. Nel tema scuro i pulsanti
  principali hanno il testo scuro su fondo chiaro.
- Le tre pagine-strumento (previsione, patrimonio, Legge 10) hanno la stessa impaginazione: mappa a sinistra,
  passi numerati a destra.

## Aggiornamento del 27/10/2026 (pomeriggio)

- `indicatori.html` / `indicatori.js` e `dati/indicatori/` (generati da `fase8-indicatori`): spesa energetica degli enti SSN.
- `clima_storico.js` e `dati/clima/` (generati da `fase9-clima-storico`, non nel repository per le dimensioni: si
  pubblicano dal pacchetto `statocritico\pacchetti\clima_dati.tar.gz.part*`): sezione "Il clima dal 1940" della
  Legge 10, che compare anche se l'API non risponde; `dati/clima_sintesi.csv` e `dati/clima_stagioni.csv` scaricabili.
- `cti_legge10.js` e `dati/cti/` (27/10/2026 sera; generati da `statocritico\cti_try\indicatori.py`, **fuori dal
  repository**: si pubblicano dal pacchetto `statocritico\pacchetti\cti_dati.tar.gz`, 2,2 MB, da estrarre in
  `/srv/energia/sito/`): sezione 3 «L'anno tipo del CTI» della Legge 10 (la sezione «Il clima dal 1940» diventa la
  4), anche senza API. Cifre (GG della zona con scarto dal DPR, zona, temperature di progetto), tabella DPR 412/93 /
  clima reale delle ultime 10 stagioni (`dati/clima/`) / anno tipo CTI, frase con località, distanze, pesi e
  correzione di quota, avvisi, mensili in un `<details>`, riquadro «Licenza: solo citazione» e fonte («elaborazione
  EuGEnio su anni tipo climatici CTI – Comitato Termotecnico Italiano», link try.cti2000.it). Metodo: interpolatore
  del CTI (due località della stessa regione, pesi 1/d², 6,5 °C/km). **Non CC BY**: niente CSV e niente report con
  questi valori; mai dati orari. Spiegazione in `metodo.html#anno-tipo-cti` e F.A.Q. `#cti-elaborazioni`.
- `faq.html` a gruppi (`<h2 id>` + domande `<details id>`): l'indice laterale mostra solo i gruppi; i collegamenti
  diretti alle domande (es. `faq.html#garanzia`) aprono la domanda.
- `sitografia.html` in due parti (27/10/2026): **Fonti dei dati** (Territorio e dati aperti, Energia, Norme e dati
  climatici, Dati sanitari e sugli enti pubblici) e **Strumenti di sviluppo** (Previsione e meteo, Server e
  pubblicazione, Dati e documenti, Newsletter, Caratteri, E per finire); voci nuove: Zornade, Open-Meteo su AWS,
  ReportER, python-docx e fpdf2, Playwright, Barlow. L'indice laterale mostra le due parti e, sotto, i gruppi.
- Licenza dei dati e dei report (27/10/2026): **CC BY 4.0, citando EuGEnio** («Fonte: EuGEnio – eugenio.statocritico.it»);
  sezione `licenza.html#dati`, F.A.Q. `#riuso`, piè di tutte le pagine "Licenza (codice AGPL, dati CC BY 4.0)"; licenza e
  formula di citazione in ogni download (CSV: righe finali; JSON e GeoJSON: campi `licenza` e `citazione`) e nei file
  statici (`dpr412.*`, `clima_*.csv` con BOM UTF-8, `dati/indicatori/*.json`).
- Correzioni del 27/10/2026 sera: menu «Previsioni» (era Previsione); marchio in testata più grande, con la E alta
  quanto l'edificio e il tetto che sporge; comandi della piccola mappa a sinistra, in colonna (+, −, ⟲ e per ultima la
  freccia ↓ che mostra tutta l'Italia nella mappa grande), ciascuno con il suggerimento; mappa regionale nel tema scuro
  con colori chiari e la regione scelta più luminosa (dettagli in `sito/README_stile.md`).
- Versione cache: `?v=20261027t`.
- 27/10/2026 notte:
  - testata, piè e `<head>` comuni in `parti/` con `costruisci_pagine.py` (vedi «Preparazione»);
  - **cambio di vestito o di tema senza ricaricare la pagina** (nella Previsione il file caricato resta): `aspetto.js`
    cambia `data-theme`/`data-vestito` e i loghi, poi emette l'evento `eugenio:aspetto`. Mappe e grafici disegnano i
    colori come `var(--…)` nello stile degli elementi SVG, quindi cambiano da soli; i colori calcolati (fondo dei comuni
    della regione, scala dei gradi giorno della Previsione, striscia delle zone del clima dal 1940) li rifanno
    `app.js`, `legge10.js` e `clima_storico.js` all'evento. Per ogni altro colore scritto come valore, `aspetto.js`
    sostituisce il vecchio valore di una variabile con il nuovo (rete di sicurezza). In Dati storici i comuni fuori
    dalla selezione usano `--comune-fuori` (grigio medio nel tema scuro, chiaro nel chiaro);
  - `scarica_font.py` riscritto: solo Hanken Grotesk (variabile) e Barlow 500/600/700, stessi file e stesso `font.css`
    di oggi (verificato byte per byte), niente Bricolage;
  - **vista d'Italia**: la freccia ↓ accanto alla piccola mappa mostra tutta l'Italia nella mappa grande, con le
    regioni colorate; un clic su una regione la sceglie (Previsioni e Legge 10 si ricaricano sulla regione, Patrimonio e
    Dati storici cambiano senza ricaricare). Con `?vista=italia` nell'indirizzo la mappa grande si apre già su tutta
    l'Italia. Alla prima visita si apre ancora l'Emilia-Romagna (unica con il meteo completo); per aprire invece
    l'Italia basta `ITALIA_ALLA_PRIMA_VISITA = true` in `minimappa.js`.

## Aggiornamento del 28/10/2026 – formati aperti OpenDocument (da pubblicare; Word e ODT tolti la sera stessa, vedi sotto)

- `report.js`: due pulsanti in più, «ODT (LibreOffice)» e «ODS (LibreOffice)» (`formato=odt|ods`), con un suggerimento
  al passaggio del mouse; i pulsanti dei report sono ora separati e vanno a capo ordinatamente (`stile.css`), su
  telefono due per riga.
- `dati.html` / `dati.js`: nel passo «Formato e download» la scelta **OpenDocument (.ods)** accanto a CSV ed Excel,
  con il suo testo d'aiuto e il limite di righe del catalogo (`limiti.righe_ods`).
- Testi: nuova F.A.Q. `#formati-report` («In che formati posso scaricare i report e i dati?»), licenza dei report e
  dei file in `faq.html` e `licenza.html`, Dati storici in `metodo.html`, odfpy nella Sitografia («Dati e documenti»).
- Versione cache: `?v=20261028b`. Provato con Playwright: 12 pagine a 1440 e 390 px senza errori né scorrimento
  orizzontale; download ODT/ODS dai pulsanti e scelta ODS in Dati storici (schermate in `vestiti/schermate5`).

## Aggiornamento del 28/10/2026 sera – solo PDF e dati grezzi (da pubblicare)

Decisione di Paolo: **il servizio gratuito genera solo il PDF e i dati grezzi**; niente più report in Word (.docx) né
in ODT. Sul server i due formati sono spenti (rispondono 410, variabile `REPORT_FORMATI`, README della fase 4).
- `report.js`: tre pulsanti, nell'ordine **PDF**, **Excel (.xlsx)**, **ODS (LibreOffice)**, ognuno con un suggerimento
  al passaggio del mouse; sotto, una riga «Il servizio gratuito genera il report in PDF e i dati grezzi in Excel o ODS.
  Perché solo questi formati?» con il collegamento a `faq.html#formati-report` (`.report-nota` in `stile.css`).
- F.A.Q. `#formati-report` riscritta («In che formati posso scaricare i report e i dati? Perché non in Word?»: PDF =
  report impaginato, Excel/ODS = dati grezzi, come costruire una relazione propria citando EuGEnio); `#licenza-report`
  (PDF ed Excel/ODS; vale anche per i Word e ODT scaricati prima); `licenza.html` (`#dati`, `#report`); Sitografia
  (python-docx «spento dal 28/10/2026», odfpy per l'ODS); commenti di `patrimonio.js`, `legge10.js`, `indicatori.js` e
  `README_stile.md`.
- Versione cache: `?v=20261029a` (29/10/2026: riquadretti sulle mappe, Patrimonio 3D con Valori per sede, file
  Excel/ODS). Prima: `?v=20261028e` (28/10/2026 notte: grafici nel riquadro flottante e osservabili, pannelli
  ridimensionabili, freccia ↓ della piccola mappa corretta). Provato con Playwright: pulsanti a 1440 e 390 px (tema scuro e chiaro), nessun
  errore né scorrimento orizzontale, clic su ODS → `formato=ods`; F.A.Q. aperta da `#formati-report`.

## Aggiornamento del 29/10/2026 – verifica anti-robot (da pubblicare con `?v=20261029a`)

- Nuovo `sito/protezione.js`, caricato nel `<head>` di tutte le pagine da `parti/testa.html` (dopo la modifica:
  `python costruisci_pagine.py`, senza cambiare versione). Avvolge `window.fetch`: per previsione, patrimonio,
  geocodifica, particella ed estrazione dei Dati climatici chiede al server `/api/protezione`; se la verifica è
  accesa carica Cloudflare Turnstile da `challenges.cloudflare.com` (solo in quel momento), scambia il gettone con
  `POST /api/sessione` e manda il gettone di sessione nell'intestazione `X-EuGEnio-Sessione`; a una risposta 401 con
  `X-EuGEnio-Verifica` rifà la verifica una volta e ripete la richiesta. Le pagine non sono cambiate.
- Il riquadro della verifica (in basso a destra, colori del vestito) compare solo se Cloudflare vuole un clic; il
  gettone di sessione resta mezz'ora in `sessionStorage`.
- Se Turnstile non si carica (blocco pubblicità) la pagina mostra l'errore come le altre risposte del server: «La
  verifica anti-robot di Cloudflare non si è caricata…».
- Senza le chiavi Turnstile nel `.env` del server (prove in locale, mirror) `protezione.js` non fa nulla.
- Informativa privacy aggiornata (Turnstile tra i servizi di Cloudflare, conteggio dei 429 per 7 giorni, gettone nel
  browser). Provato in Node con browser, Turnstile e server simulati: verifica spenta, una sola verifica per più
  richieste anche contemporanee, rinnovo dopo un 401, errore leggibile se la verifica fallisce.

## Novità: registro delle versioni (07/11/2026, regola permanente)

- **Fonte unica** `novita.toml` (qui, accanto a `costruisci_pagine.py` e `parti/`): una voce `[[voce]]` per pubblicazione
  **con novità per gli utenti**, la più recente in cima, con `data`, `versione` (quella di `?v=`), `titolo`, righe
  `nuovo` (servizi pubblicati), `migliorato` (cosa si può fare di più o meglio), `verificato` (da sperimentale a
  validato) – facoltative, 3–6 in tutto – `testo` e `collegamenti` facoltativi (`{ testo, indirizzo }`). **Regola
  dell'08/11/2026 (Paolo)**: solo le funzioni per gli utenti, niente modifiche interne (protezione, menu, file per gli
  agenti, copie, server, test); linguaggio semplice, nome della pagina con il gruppo del menu («Patrimonio › Modelli
  3D»), niente gergo tecnico; campi sconosciuti (i vecchi `cambiato`, `corretto`) rifiutati. **La versione resta solo
  qui** (test con `index.html`, tag della release): pagina, feed, newsletter e testo della release mostrano solo data,
  titolo e gruppi; ancore e identificativi del feed per data (`#d20261107`, `#d20261107-2` per la seconda voce dello
  stesso giorno). Mai dati GME/EEX, fase 2 o `uni_privato`.
- `python costruisci_pagine.py` genera `sito/novita.html` (pagina di testo con l'indice laterale per versione) e
  `sito/novita.xml` (feed Atom con indirizzi assoluti); `--controlla` li confronta come le altre pagine. La testata ha
  «Novità» tra Mirror e Contattaci (computer e telefono) con `data-ultima` = versione dell'ultima voce; la testa comune ha
  il `<link rel="alternate" type="application/atom+xml">`; `aspetto.js` mette un pallino sul collegamento se l'ultima
  versione vista (`localStorage` «novita-vista», con try/catch, nessun cookie) è più vecchia; la prima visita non lo
  mostra, aprire la pagina lo toglie. Caddy serve `/novita.xml` come `application/atom+xml; charset=utf-8`.
- La newsletter mensile (`fase4-server/servizio/notiziario.py`) mette le voci del mese nella sezione «Novità di EuGEnio»
  (`novita.toml` è copiato nell'immagine dell'api: va nel pacchetto del codice).
- **A ogni pubblicazione**: una voce qui, insieme ad AGGIORNAMENTO, `EUGENIO_PER_AGENTI.md` e `llms.txt`; dopo il commit
  la release su GitHub con lo stesso testo (`gh release create vAAAA.MM.GG --notes-file …`, passo F23 di
  `AGGIORNAMENTO_2026-11-07.md`). Niente «Blog» per ora (DA_FARE).
- Test: `test_novita_versione_feed_e_menu` (prima voce = versione di `index.html`, feed valido, menu, nessun dato di
  mercato) e, in Chromium, `test_novita_telefono_e_pallino` (375 px senza scorrimento orizzontale, pallino).

## Aggiornamento del 07/11/2026 sera – pagine 3D unificate e altezze OSM (stessa versione `?v=20261107a`)

- **Pagine 3D unificate** (decisione di Paolo): Edificio › Geometria, Consumi, Obblighi e Fotovoltaico › Ombre,
  Producibilità, Sole e irradiazione, Confronto PVGIS, D.Lgs. 199/2021 hanno la **stessa mappa di Modelli 3D** (ricerca,
  mappa 2D, «Genera il 3D», livelli, immagine, demo della pagina stessa) e gli stessi script (`minimappa.js`,
  `confini_gl.js`, `esporta_mappa.js`, `cerca_luogo.js`, `strati_gl.js`, `dbtr_locale.js`). In `edificio3d.js` i due
  tempi valgono per ogni pagina con `#genera-3d`; `data-vista` sceglie solo il passo in evidenza; `archivi.json` (archivi
  per comune, confine ISTAT o riquadro), ripiego OSM, DB topografico del browser e terreno da `/api/terreno` ovunque;
  apertura da `?sede=locale`, `?dbtr=locale` (o la stessa scheda) e `?edificio=<id>&lon=&lat=`; la demo solo con
  `?archivio=demo` o se non c'è né archivio né ripiego. Prima queste pagine aprivano `/edifici3d/cc-by/er/prodotti/` (che
  non esiste più) e finivano sulla demo.
- **Altezze OSM**: corpi senza `height` né piani → mediana dei corpi DBTR entro 200 m (il server con i suoi archivi, la
  pagina con il file caricato nel browser), altrove 9 m; `origine_altezza` per corpo, nota `#nota-altezze-osm` sotto la
  mappa, la stessa riga nell'immagine e nel report.
- Overpass di riserva europea in privacy e Sitografia; F.A.Q. `#ripiego-osm` aggiornata.
- Test: `test_altre_pagine_3d_come_modelli3d`, `test_pagine_3d_unificate_dbtr_osm_e_file_locale` (9 pagine con un archivio
  DBTR per comune, Pesaro col ripiego OSM e il file nel browser), controlli dell'HTML in `test_costruisci_pagine.py`.
  Prova su dati veri in AGGIORNAMENTO_2026-11-07.md, sezione F.

## Aggiornamento del 07/11/2026 – «Aggiungi edifici (DB topografico)» e «Scaricare i DB topografici» (stessa versione `?v=20261107a`)

Decisione di Paolo del 07/11/2026. Due pagine nuove nel gruppo **Patrimonio** (menu con «S» per la prima):

- **`aggiungi-dbtr.html`** (`aggiungi_dbtr.js`): regione (`er`, `lom`, `fvg`, `lig`; `?regione=`), comune dall'elenco ISTAT
  di `dati/mappa/<regione>.json`, casella «comune intero» (spuntata), file: zip del portale, GeoPackage o parti di uno
  Shapefile, anche una cartella (fino a 300 MB). Lettura nel **Web Worker** `dbtr_worker.js` con `dbtr_lettore.js` (stessa
  logica di `uvl.py` e `regionali.py`; zip con **fflate 0.8.2**, GeoPackage con **sql.js 1.14.2** caricato solo quando
  serve, Shapefile e DBF letti dal file stesso, proj4js), riepilogo (corpi, scartati per motivo, gronda mediana/p95/max,
  convenzione, cortili, foglio e numero, destinazione, comuni catastali, avvisi: regione sbagliata, corpi oltre 60 m, corpi
  piccoli e altissimi, possibili dati personali), mappa con l'ortofoto e i corpi colorati per gronda. **Apri in Modelli
  3D** salva i corpi con `dbtr_locale.js` (IndexedDB del sito, segnale nella memoria della scheda) e apre
  `modelli3d.html?dbtr=locale`. **Proponi** (casella del consenso non spuntata, pulsante spento finché non c'è): impronta
  SHA-256, `POST /api/dbtr/inizia` (Turnstile: `protezione.js` la conosce), pezzi `PUT …/pezzo/{n}` con tre tentativi,
  `POST …/fine`; le proposte fatte da quel browser restano in `localStorage` (`eugenio-dbtr-proposte`) per vederne lo stato
  e ritirarle. Le parti di uno Shapefile si impacchettano in uno zip nel worker prima dell'invio.
- **`edificio3d.js`**: archivio «locale» (`stato.locale`, `{ locale: true }`, sorgente GeoJSON, celle di 0,01° in memoria)
  dopo gli archivi del server e prima del ripiego OSM; in `contesto()` si legge per primo e i corpi del server che cadono
  dentro i suoi si scartano; zona coperta per la sessione (confine ISTAT con «comune intero», altrimenti riquadro);
  niente terreno dell'archivio (quota della base del DB topografico); righe nelle attribuzioni dell'immagine e nelle note
  del report; «Togli gli edifici del file».
- **`dbtr-istruzioni.html`**: istruzioni per Emilia-Romagna, Lombardia, Friuli Venezia Giulia, Liguria, Trento, Veneto e
  tabella delle altre regioni («in attesa di chiarimento dalla Regione»); scelta di una pagina separata motivata in
  `AGGIORNAMENTO_2026-11-07.md` (D.6).
- **Pagina interna** `interno/edifici.html` + `edifici.js`: sezione «DB topografici proposti» in cima (tabella, dettaglio,
  anteprima con MapLibre e l'ortofoto, Approva/Rifiuta con conferma e `X-EuGEnio-Interno`, registro, ultime decisioni).
- Anche: `privacy.html` (riga `#dbtr`, «In breve» e data), F.A.Q. `#aggiungi-dbtr`, Modelli 3D (rimando), Sitografia
  (sql.js, fflate), `lib/README.md`, `EUGENIO_PER_AGENTI.md` e `llms.txt`.
- Test: `test_costruisci_pagine.py::test_aggiungi_dbtr_e_istruzioni` (nuovo; librerie solo nel worker della pagina,
  consenso spento, istruzioni, privacy), conteggi del menu aggiornati (16 «S», 8 voci in Patrimonio). Le prove nel
  browser (parità, invio, Modelli 3D, pagina interna) sono in `fase10-edifici3d/tests/test_dbtr_browser.py`.

## Aggiornamento del 07/11/2026 – Modelli 3D col DBTR vero, cortili, zona coperta, zoom 17 (`?v=20261107a`, che sostituisce `?v=20261106a`)

- **Cortili** (fori delle sagome): `edificio3d.js` porta gli anelli interni nei corpi (`buchi`), nel GeoJSON dell'edificio
  scelto e del 3D; un punto in un cortile non è «dentro» l'edificio (la distanza di 30 m conta anche dai lati del
  cortile); `edifici_calcoli.js` ha `areaCorpo`, `dentroCorpo`, `latiCorpo`: area, volume, S/V, superfici e pareti sul
  cortile come in Python (test di parità in fase 10). Le ombre usano la sagoma esterna.
- **Fuori zona**: `coperto(lon, lat)` sui riquadri degli archivi; fuori da tutti, ricerca, punto trascinato/clic e sede
  dal Patrimonio scrivono «il punto è fuori dalla zona coperta dall'archivio degli edifici («DBTR Emilia-Romagna –
  Rimini»): qui il 3D non si può ancora generare»; i riquadri coperti sono tratteggiati, discreti, sulla mappa 2D.
- **Più archivi** (un archivio DBTR per comune): `archivi.json` fino a 150 archivi (60 fino al 09/11/2026: con gli archivi del 09/11 sono 69), letti solo quelli il cui riquadro tocca
  il punto; archivi della stessa licenza non si escludono; terreno dell'archivio dell'edificio scelto; falde LiDAR
  dall'archivio indicato da `"lidar"`. Ortofoto: contorni dell'archivio 3D da tutti gli archivi di `archivi.json`.
- **Fonte del 3D**: «DB topografico regionale» per i corpi DBTR (prima la fonte «… da DTM DSM 2008» faceva scrivere «corpi dal
  LiDAR»); scheda dell'edificio con nome, foglio e numero e destinazione d'uso del DBTR.
- **Zoom dopo la ricerca**: costante comune `EUGENIO_CERCA.ZOOM = 17` (`cerca_luogo.js`), usata da Ortofoto e Modelli 3D
  (prima 18, e in Ortofoto `Math.max(18, …)`).
- **Livelli della mappa** di Modelli 3D: dalla colonna della mappa alla colonna destra, primo passo («1 Livelli della
  mappa», come «Strati sopra la foto» in Ortofoto); legenda e attribuzioni restano sotto la mappa.
- Test: `test_mappe_browser.py` con 2 test nuovi (posizione dei Livelli; archivio CC BY sintetico con un edificio a corte:
  punto nel cortile, cortile nel 3D e nell'area, messaggio fuori zona, zoom 17); fase 5 **44 passed, 1 skipped** (pvlib).
- Versione **`?v=20261107a`** (anche `interno/edifici.html`, a mano); `EUGENIO_PER_AGENTI.md` e `llms.txt` aggiornati.

### Stesso giorno, poi: ripiego OpenStreetMap fuori dal DBTR (decisione di Paolo, stessa versione `?v=20261107a`)

- **Ripiego al volo** (`edificio3d.js`): in Modelli 3D, se il punto (ricerca, punto trascinato, clic, sede dal Patrimonio)
  è fuori da ogni archivio DBTR, `contesto()` chiede `GET /api/edifici/osm?lon=&lat=` (una richiesta per cella di 0,002°,
  tenuta in memoria) e usa gli edifici OSM come corpi: scelta, «Genera il 3D», ombre, tabelle, immagine e report come con
  l'archivio. Archivio «virtuale» `{ osm: true }` in fondo a `stato.archivi`, sorgente **GeoJSON** `corpi_<k>` (sagome 2D
  tratteggiate); mai nella demo né con `?archivio=`.
- **Dove c'è il DBTR, OSM non si mescola**: `coperto()` (ora asincrona) usa il **confine ISTAT del comune** per gli
  archivi di un comune intero (`istat` in `archivi.json`; `C.comuneNelPunto` di `confini_gl.js`, confini di tutta Italia)
  e il riquadro dei corpi per gli altri (il riquadro di Rimini sborda su Riccione, Coriano, Santarcangelo); i corpi OSM che
  cadono in un comune coperto si scartano. Zone coperte tratteggiate: il confine del comune (`C.geometriaComune`, nuova).
- **Licenze e messaggi**: ogni corpo OSM porta «ODbL 1.0»; messaggi «Qui non c'è ancora il DBTR: si usa OpenStreetMap come
  ripiego (© OpenStreetMap contributors, ODbL 1.0), con qualità inferiore e altezze in parte stimate…»; riga `#fonti-osm`
  nel piè; immagine con «Edifici fuori dal DBTR: © OpenStreetMap contributors, ODbL 1.0…» (righe degli archivi senza
  doppioni); report con l'attribuzione degli archivi davvero usati (non più sempre quella del primo) e la nota del ripiego.
  Edificio OSM: niente DTM (mappa e quote piatte, anche per i corpi DBTR vicini oltre il confine), comune dai confini
  nazionali. Overpass giù o ripiego spento: «… OpenStreetMap, il ripiego per queste zone, non ha risposto (…): qui il 3D
  non si può generare ora», nessun edificio scelto.
- `protezione.js`: `/api/edifici/osm` tra le rotte con la verifica anti-robot. `privacy.html`: riga del trattamento e API
  Overpass tra chi tratta i dati (solo il centro della cella, dal server). F.A.Q. `#ripiego-osm`; piè di Modelli 3D.
- Test: `test_mappe_browser.py::test_modelli3d_ripiego_osm_fuori_dal_dbtr` (Pesaro con il lettore vero della fase 10:
  scelta del multipoligono, Genera il 3D con il cortile, licenza ODbL in pagina, report e PDF, nessuna richiesta nella
  stessa cella; Riccione non coperta dentro il riquadro di Rimini; corpo OSM nel comune di Rimini scartato; Cesena con
  Overpass giù; Rimini senza richieste a OSM) e il test del cortile aggiornato (archivio virtuale, messaggio con OSM non
  disponibile). Fase 5 **45 passed, 1 skipped**. Prova con i dati veri di Pesaro e Cesena (copia della rotta): scelta e 3D
  in ~2 s, 87 e 507 corpi vicini, nessun errore in console.

## Aggiornamento del 06/11/2026 – file per gli agenti AI (`?v=20261106a`, che sostituisce `?v=20261105b`)

Richiesta di Paolo: un file che spiega tutte le funzioni di EuGEnio agli agenti AI, perché lo possano usare da soli.
- **`sito/EUGENIO_PER_AGENTI.md`** (copia identica di `../EUGENIO_PER_AGENTI.md`, nella radice del repository per GitHub):
  cos'è, licenze e attribuzioni, mappa del menu pagina per pagina con i parametri dell'indirizzo (`?comune=`, `?regione=`,
  `?dataset=`, `?archivio=`, `?edificio=`, `?sede=locale`, `?modello=locale`, `?lat=&lon=&z=`, `?fonte=`, `?istat=`,
  `?ente=`), formati dei file, API libere e protette da Turnstile con esempi curl, limiti, flussi passo passo, cosa EuGEnio
  non fa, privacy funzione per funzione, file statici, contatti, fonti nel repository da cui è ricavato.
- **`sito/llms.txt`** (convenzione llms.txt): descrizione breve e rimando al file.
- **F.A.Q.** nuova voce `#agenti-ai` («Posso far usare EuGEnio al mio assistente di intelligenza artificiale?») con il
  collegamento che scarica il file (`download`).
- **Sitografia** `#claude`, dopo «No, scherzavamo: non è open source…»: «E lo puoi usare anche tu: per fargli imparare cosa
  può fare EuGEnio, scarica e fagli leggere [questo file].» (collegamento con `download`).
- `stile.css`: `.articolo p code` va a capo anche dentro le parole (l'indirizzo lungo nella F.A.Q. non fa più scorrere la
  pagina in orizzontale sul telefono).
- Caddy: tipo `text/markdown; charset=utf-8` per i `.md` e `text/plain; charset=utf-8` per `/llms.txt` (fase 4, Caddyfile).
- Versione **`?v=20261106a`** (anche `interno/edifici.html`, a mano); **43 test** (5 nuovi in `tests/test_agenti_sito.py`,
  2 nel browser: ancora `#agenti-ai`, download dalla F.A.Q. e dalla Sitografia a 1366 e 375 px, nessuno scorrimento
  orizzontale, nessun errore).

**Dopo ogni modifica a funzioni, pagine o API del sito** aggiornare anche `EUGENIO_PER_AGENTI.md` (radice e `sito/`,
identici) e `sito/llms.txt`, con data e versione del sito in testa (`?v=…` uguale a quella di `index.html`: i test lo
controllano).

## Aggiornamento del 05/11/2026 – seconda pubblicazione (`?v=20261105b`, che sostituisce `?v=20261105a`)

Dopo le prove di Paolo su `?v=20261105a` (dettagli e procedura D1–D17 in `../AGGIORNAMENTO_2026-11-05.md`, blocco 6):
- **`esporta_mappa.js`**: il messaggio di successo compare solo a file davvero scritto. In Chrome/Edge sul computer la
  finestra «Salva con nome» (`showSaveFilePicker`) si apre **nel clic**, la pagina scrive il file e dice «Immagine salvata:
  nome (dimensione)»; «Annulla» = «Salvataggio annullato». Altrove «Download avviato…» con il collegamento «Salva …» da
  cliccare a mano. Controllo della copia della mappa (vuota o non leggibile per CORS) prima di creare il file. `pulsanti()`
  accetta ora l'elemento dei messaggi (per il collegamento).
- **`cerca_luogo.js`** (nuovo): ricerca per indirizzo o per comune, foglio e particella (una riga a `POST /api/patrimonio`,
  nessuna dipendenza nuova da Zornade), comune a Ortofoto (nuova casella sopra la mappa, pallino sul punto) e Modelli 3D.
- **`strati_gl.js`** (nuovo): caselle «Confini delle particelle catastali» e «Contorni degli edifici» sopra la foto, dal
  proxy del server (`/api/ortofoto/strati`), con il DB regionale dove c'è e OpenStreetMap altrove; legenda e fonti sotto la
  mappa (`#legenda-strati`) e nelle righe dell'immagine scaricata.
- **Modelli 3D** (`edificio3d.js`, `modelli3d.html`): punto trascinabile (mouse e dito) e clic che lo sposta da zoom 15;
  l'edificio scelto è quello del punto corretto; **«Esci dalla demo»** (`#esci-demo`) sempre visibile nella demo; riquadro
  «Livelli della mappa» con Ortofoto (casella + fonte), particelle e contorni (spenti nella demo).
- **Menu** (`parti/testata.html`, `parti/testa.html`, `stile.css`): nelle tendine e nella riga fissata «S», «GME» e il
  triangolo giallo per «in sviluppo» (testo intero nel `title` e per i lettori di schermo; parole intere nel menu del
  telefono); sesto gruppo **Statistiche** con **Costi energetici Sanità** (`indicatori.html`, senza etichetta e senza
  l'avviso sperimentale); «Indicatori» tolto dalle «Altre pagine»; `menu-fissato` accetta `statistiche`.
- Corretti: scorrimento orizzontale sul telefono con la riga fissata (testi nascosti assoluti fuori dalla riga che scorre:
  `.riga-voci > li` ora `position: relative`); l'avviso «Dati sintetici di esempio» visibile senza demo (`.messaggio[hidden]`).
- Versione **`?v=20261105b`** (anche `interno/edifici.html`, a mano); **38 test** (5 nuovi; 9 nel browser).

## Aggiornamento del 05/11/2026 – Ortofoto e Modelli 3D dopo le prove sul sito pubblicato (blocco 5, stessa versione `?v=20261105a`)

- **Ortofoto** (`ortofoto.html`, `ortofoto.js`): contesto Sentinel-2 sempre sotto la fonte scelta, sovracampionamento
  oltre lo zoom massimo (mappa fino a 21), `bounds` per sorgente, avviso sulla mappa (sotto lo zoom minimo, fuori dal
  riquadro, oltre lo zoom massimo), confini di regioni, province (zoom ≥ 7) e comuni (zoom ≥ 9), piccola mappa d'Italia
  (clic = va lì, secondo clic = torna all'Italia), clic su regione o comune sulla mappa grande, «Scarica l'immagine» in JPG,
  PNG e PDF con le attribuzioni dentro l'immagine (rifiutato per le fonti «solo dal vivo»), colonna della mappa che scorre.
  Prima, sotto lo zoom 12 delle ortofoto regionali la mappa restava nera: era il «sparisce tutto».
- **Modelli 3D in due tempi** (`modelli3d.html`, `edificio3d.js` con `data-vista="modelli"`): mappa 2D con piccola mappa,
  confini e ortofoto; ricerca per indirizzo o per comune, foglio e particella (una riga a `POST /api/patrimonio`, come la
  pagina Patrimonio); clic sull'edificio (secondo clic lo toglie); «Genera il 3D» con la fonte più affidabile per corpo
  (falde LiDAR → DB topografico → modello DXF/IFC → OSM → stima) scritta in pagina, nell'immagine e nelle note del report;
  comandi della vista come `mappa3d.js` (barra Zoom · Vista · Ruota · Inclina · Rollio, tastiera, doppio clic); «Scarica
  l'immagine»; «Torna alla mappa 2D». Senza archivio: «Prova la demo sintetica» (`?archivio=demo`); con `?sede=locale` o
  `?edificio=` senza archivio vero si ripiega sulla demo dichiarata, come prima. Le altre 8 pagine 3D non cambiano.
- La **demo sintetica non va mai sopra un'ortofoto vera** (selettore dello sfondo spento con il motivo): le sue sagome sono
  inventate e allineate alla griglia UTM, ed erano gli edifici «storti» rispetto alla foto.
- Moduli nuovi: `confini_gl.js` (confini ISTAT di `dati/mappa/` per MapLibre, inversa di Gauss–Krüger, clic su regione e
  comune), `esporta_mappa.js` (vista della mappa + fascia delle attribuzioni → JPG, PNG, PDF scritto nel browser);
  `minimappa.js` ha due agganci nuovi (`EUGENIO.suStessaRegione`, `EUGENIO.evidenziaPiccola`), usati solo da queste pagine.
- `visure.html`: sezioni «Disinstallare» e «Code signing policy» (per SignPath Foundation); `interno/edifici.js`: frase
  dello stato della zona dal server (`situazione`), «In attesa: …» invece di «Zona in corso».
- Test: `tests/test_mappe_browser.py` (4 in Chromium: Ortofoto, Modelli 3D senza archivio, demo in due tempi, altre pagine
  in un tempo) e 2 in `test_costruisci_pagine.py` (pagine, moduli senza servizi esterni, inversa UTM con node): 33 in tutto.

## Aggiornamento del 05/11/2026 – analisi senza GME e senza UNI (blocco 3, stessa versione `?v=20261105a`)

- `cog-emissioni.html` + `emissioni_cog.js`: Cogenerazione › Emissioni (report 18) con i fattori ISPRA in
  `dati/ispra_fattori_emissione.json` (copia di `fase13-cogenerazione/dati_terzi/`), tutto nel browser, nessun dato GME;
- `edificio-clima.html` e `edificio-cer.html` con `analisi_pubbliche.js` (analisi 13 e 7), esempio
  `esempi/cer_esempio_sintetico.csv` (dati inventati); colonna «Cielo visibile» delle facciate (analisi 9);
- `fv-leed.html`: prefattibilità LEED descrittiva, nessun contenuto del sistema LEED riprodotto;
- menu: Emissioni, Comunità energetiche, Clima che cambia e Prefattibilità LEED passano da «in sviluppo» a «sperimentale»;
  le loro pagine non usano più `analisi_uni.js`; 2 test nuovi, 2 nel browser in `fase10-edifici3d/tests/test_blocco2_browser.py`.

## Aggiornamento del 05/11/2026 – affinamenti Edificio (versione `?v=20261105a`, che sostituisce `?v=20261104c`)

Blocco 2 di `AGGIORNAMENTO_2026-11-05.md` (dettagli nel README della fase 10, «Affinamenti Edificio – blocco 2»):
- `edifici_calcoli.js`: Tabella 11 del DM requisiti minimi (`htMassimoPrimoLivello`) con la quota vetrata scritta o stimata
  (`quotaVetrataStimata`); trasposizione di **Perez** al posto dell'isotropa (FV e facciate, `modello: "isotropo"` per il
  calcolo di prima); colonne `visura_…` (`daVisura`, `mappaVisura`, `leggiVisura`); posa sulla sagoma (`posaDaSagoma`);
- 9 pagine 3D: campo «Superfici vetrate» nel passo Obblighi di legge, nota della sede aperta dal Patrimonio, alberi del
  LiDAR come ostacoli e in verde sulla mappa (`lidar/alberi/` dell'archivio), apertura con `?sede=locale`;
- `patrimonio.js`: pulsante «Apri in Modelli 3D» in ogni sede con le coordinate (dati nella memoria della scheda);
- `valori_sedi.js`: colonne `visura_…` lette a parte (non diventano valori da disegnare), superficie catastale della
  visura come base dei consumi al m² (segnata «v»);
- `importa-dxf-ifc.html` e `importa_modello.js`: posa «agganciato alla sagoma di un edificio dell'archivio» (legge in GET
  le celle statiche di `/edifici3d/…` o della demo; il modello non lascia il browser);
- demo sintetica `dati/edifici3d/` rifatta (con `lidar/alberi/`); `tests/pvgis_rimini_2020_giorno15.json` (estratto PVGIS
  per il confronto); 6 test nuovi in `tests/test_costruisci_pagine.py`, 3 nel browser in
  `fase10-edifici3d/tests/test_blocco2_browser.py`.

## Aggiornamento del 04/11/2026 notte – menu fissabile e voci GME non cliccabili (`?v=20261104c`, che sostituisce `?v=20261104b`)

Richiesta di Paolo del 04/11/2026; regole grafiche in `sito/README_stile.md` § «Menu a gruppi».
- **Cinque gruppi principali** (Clima e meteo, Patrimonio, Edificio, Cogenerazione, Fotovoltaico): il mouse o il fuoco da
  tastiera sul titolo apre la tendina verticale a scomparsa; il **clic sul titolo fissa il gruppo**: le voci compaiono in
  orizzontale nella riga nera `nav.riga-fissata` sotto la barra dei menu. Clic su un altro gruppo: la riga cambia; secondo
  clic sullo stesso: la riga sparisce e torna la tendina. Suggerimento «Clicca qui per …» che cambia con lo stato. La
  scelta resta al cambio di pagina (`localStorage` «menu-fissato»). «Altre pagine» (Indicatori, Come funziona, F.A.Q. …)
  e il piè restano come prima.
- **Voci «licenza GME»** (5 di Cogenerazione, 1 di Fotovoltaico): non più collegamenti ma `span.voce-gme` con
  «In attesa di autorizzazione dal GME», nella tendina, nella riga, nel menu del telefono e negli elenchi «Nello stesso
  gruppo» delle pagine segnaposto (7 pagine toccate). Le pagine restano (raggiungibili solo scrivendo l'indirizzo); nessun
  altro collegamento interno porta lì, salvo quello di ogni pagina a sé stessa (test).
- File: `parti/testata.html` (span delle voci GME, `nav.riga-fissata`), `parti/testa.html` (`data-menu-fissato` prima del
  CSS), `costruisci_pagine.py` (`aria-current` anche sugli span GME, così il gruppo resta segnato sulla loro pagina),
  `sito/aspetto.js` (comportamento del menu), `sito/stile.css` (sezioni «menu fissato» e «voci in attesa della licenza
  GME»), le pagine `cog-*.html` e `fv-leed.html` (elenchi «Nello stesso gruppo»), tutte le pagine rigenerate e
  `interno/edifici.html` (versione a mano: la pagina interna non passa da `costruisci_pagine.py`).
- Test: 3 nuovi in `tests/test_costruisci_pagine.py` (voci GME non collegate, nessun collegamento interno alle pagine GME,
  riga e script del `<head>`) e 2 in `tests/test_menu_browser.py` (Chromium headless a 1366 e 375 px: tendina al
  passaggio del mouse, fissaggio, cambio di gruppo, secondo clic, persistenza, voci GME, tastiera, ×, nessun errore JS;
  si salta senza Playwright); **19 test** in tutto.
- Solo file statici: nessun rebuild dell'api né riavvio di Caddy (il sito è montato in sola lettura in `/srv/sito`).

## Aggiornamento del 04/11/2026 notte – Importa DXF/IFC (da pubblicare con `?v=20261104b`, che sostituisce `?v=20261104a`)

Decisione del 04/11/2026: disegni DXF e modelli IFC letti **direttamente nel browser**, in una pagina separata.
- `importa-dxf-ifc.html` (menu Patrimonio, accanto a Modelli 3D): file → pianta dei corpi → posa → risultato sulla mappa
  → «Apri nella pagina Modelli 3D» (passaggio nella `sessionStorage` della scheda, `modelli3d.html?modello=locale`) o
  «Scarica il modello (.geojson)»; si riapre anche un `.geojson` già convertito. Passo 5: istruzioni per i file pesanti
  (oltre 30 MB) con `EuGEnioVisure.exe`, Python o Docker.
- `modelli_import.js`: la stessa logica di `fase10-edifici3d/edifici3d/importa.py` (controlli, tetti sul file, tetti e
  corpi dai triangoli, posa, GeoJSON «eugenio-modello-1»), con dxf-parser, web-ifc, Clipper (al posto di shapely) e
  proj4js (al posto di pyproj; sistemi italiani definiti nel file). Gira nel Web Worker `modelli_worker.js` e in node per
  i test di parità; web-ifc (7 MB) si carica solo quando arriva un IFC, con un solo thread.
- Limiti: 50 MB (avviso oltre 30), 180 s (poi il worker si chiude), 200.000 entità, 2 milioni di triangoli, 1 GB di
  memoria per web-ifc; DXF solo di testo, IFC solo STEP; 3DSOLID non letti (avviso).
- La pagina non manda niente al server: le sue sole richieste sono le librerie e le tessere dell'ortofoto di sfondo
  (`/api/ortofoto/…`). Nessun'altra pagina scarica le librerie dei modelli (test in `tests/test_costruisci_pagine.py` e
  prova nel browser in `fase10-edifici3d/tests/test_importa_browser.py`).
- Pagine 3D: «Usa il tuo modello» rimanda alla pagina nuova; `edificio3d.js` apre `?modello=locale`.

## Aggiornamento del 04/11/2026 notte – analisi 5 e 7–13, ortofoto di Bolzano e Trento, Fase E (da pubblicare con `?v=20261104a`)

- `analisi_uni.js` (nuovo): nelle pagine Edificio › Fabbisogno, › Comunità energetiche, › Facciate e tetti, › Pompe di
  calore e solare termico, › Clima che cambia e Fotovoltaico › Prefattibilità LEED, una riga per analisi
  (`[data-analisi="N"]`) che parte da «analisi non disponibile in questa installazione» (vale anche senza JavaScript e sui
  mirror senza la rotta) e chiede `GET /api/analisi/stato`; se il modulo privato del server rende disponibile l'analisi,
  la riga diventa verde e dice che il modulo è installato e la pagina di calcolo non è ancora pubblicata. Le pagine restano
  segnaposto: nessun contenuto delle norme UNI.
- `ortofoto.html` e `sitografia.html`: fonti nuove di Bolzano 2023 e Trento 2015 (il selettore della pagina le prende dal
  server). Prova: `ortofoto.html?lat=46.4983&lon=11.3548&z=17`.
- Test nuovo `test_pagine_fase_e_aggancio_analisi` (13 test in tutto). Provato in Chromium headless con le rotte vere
  `analisi` e `ortofoto` della fase 4: senza modulo, con un modulo finto, pagina Ortofoto su Bolzano e Trento.

## Aggiornamento del 04/11/2026 – Previsioni: schede, «Solo clima», comune deselezionabile (da pubblicare con `?v=20261104a`)

- **Cambio di comune** (`app.js`, `azzeraPerComune`): il file dei consumi caricato, i risultati e una risposta ancora in
  arrivo appartengono al comune di prima e si tolgono, con il messaggio «Comune cambiato: il file dei consumi caricato è
  stato tolto…». Anche un file ancora in lettura (controllo `.xls`) viene scartato.
- **Secondo clic sul comune scelto = lo si toglie** (evidenziazione, elenco su «Scegli…», riquadro del comune; nella
  previsione anche file e risultati; nella Legge 10 anche `?comune=` e i passi dei risultati). Funzione comune
  `EUGENIO.alterna(istat, attuale, scegli, togli)` e `EUGENIO.togliScelto(percorsi)` in `minimappa.js`, usata da
  `app.js` e `legge10.js` (con una copia minima se `minimappa.js` manca). Nella pagina Dati (scelta multipla) la mappa
  alternava già; ora anche un comune già scelto nei risultati della ricerca si toglie. Patrimonio e pagine 3D scelgono
  edifici, non comuni: invariate.
- **«Cosa prevedere»** al passo 2: «I consumi, con il meteo» (come prima) o «Solo il clima, senza consumi»: niente
  file, niente «Modo» (verifica), pulsante «Mostra le previsioni del clima» → `GET /api/clima-previsto/{istat}` con
  modalità, orizzonte e variabili spuntate.
- **Risultato a schede** (`.schede.schede-previsione`): «Consumo» (spenta, con una nota, in Solo clima) e una scheda per
  ogni variabile meteo attiva nell'ordine delle opzioni della pagina (`COV`). Ogni scheda ha il suo grafico (con la
  freccina del riquadro di `grafici.js`, valori al passaggio del mouse, zone del meteo meno affidabile), le cifre della
  verifica (Consumo), gli avvisi e «Scarica la previsione (CSV)»; sotto le schede i pulsanti dei report.
- **CSV con tutti i valori** in colonne affiancate: `data;parte;consumo;q01…q09;[reale];<variabili meteo>;fonte_meteo`,
  con le righe del passato («dati caricati» o «osservato») e quelle della previsione; in Solo clima file
  `clima_previsto_<istat>_<modalita>.csv` senza le colonne dei consumi. Report PDF/Excel/ODS: vedi il README della fase 4
  (colonne affiancate, grafici in sequenza nel PDF).
- Provato in Chromium headless (Playwright) con le rotte simulate dal codice vero della fase 4: schede e riquadro,
  CSV, PDF ed Excel, Solo clima in lungo termine, cambio e deselezione del comune, Legge 10.

## Aggiornamento del 04/11/2026 sera – visure catastali in Patrimonio, Fase D (da pubblicare con `?v=20261104a`)

Importazione dei file di **EuGEnio Visure** (fase 11, lettore delle visure che gira sul PC dell'utente):
- `visure_abbina.js` (nuovo, senza DOM, gira anche in node): lettura di `indice.csv`, `edifici_visure.csv`,
  `patrimonio_con_visure.csv`, `visure.json` (e di un elenco JSON generico di unità), scarto delle colonne con dati
  personali, abbinamento delle unità agli edifici e colonne `visura_…`; **stessa logica** di
  `fase11-visure/visure/arricchisci.py` e `piani.py`, controllata da un test che fa girare il file con node;
- `visure_patrimonio.js` (nuovo): passo «Visure catastali (facoltativo)» in `patrimonio.html` (dopo il Risultato), riga
  «Visura» nelle schede, conteggi, unità senza edificio, «Cerca gli edifici delle visure», «Togli le visure»;
- `patrimonio.js`: funzione `esegui` (geolocalizzazione riutilizzabile), evento `eugenio:patrimonio-risultato`, colonne
  `visura_…` nel CSV e nel GeoJSON scaricati (non nel report, che si fa sul server); i file di EuGEnio Visure caricati
  al passo 1 mandano al server solo `id;comune;sezione;foglio;particella` (o il file senza le colonne delle visure);
- `patrimonio.html` (passo nuovo, testo del passo 1, due script), `stile.css` (`.edificio .visura`, `.non-abbinate`),
  `visure.html` (pagina rifatta: cosa fa, come si usa, condizioni d'uso dei dati catastali, fonti; resta «in sviluppo»
  nel menu finché l'.exe non è pubblicato), `sitografia.html` (pypdf per le visure, PyInstaller).
- Prova in Chromium headless: `fase11-visure/tests/test_patrimonio_browser.py` (5 casi, sito vero e `/api/patrimonio`
  simulata; controlla anche che al server non arrivi nulla delle visure).

## Aggiornamento del 04/11/2026 sera – edifici 3D, Fase C (da pubblicare con `?v=20261104a`)

- **Pagina 3D** (`edificio3d.js` e le 9 pagine 3D): se l'archivio ha `lidar/indice.json`, le falde misurate dal LiDAR
  sostituiscono le stime del DBTR (gronda, colmo, tetto; fonte «LiDAR – …» con la qualità); tabella «Falde dei tetti»
  (pendenza, orientamento, superficie inclinata e in pianta); falde inclinate disegnate a gradini colorati per
  orientamento; un'area FV disegnata su una falda ne prende inclinazione e orientamento; sezione «Falde dei tetti» nel
  report. «Usa il tuo modello (DXF o IFC)»: apre il GeoJSON prodotto sul PC con `importa-modello` (fase 10), **solo nel
  browser**, senza inviarlo al server; gli edifici dell'archivio sotto il modello si nascondono.
- **Demo sintetica** (`dati/edifici3d/lidar/`): falde del campione LiDAR sintetico, dichiarate come inventate.
- **Pagina interna** `interno/edifici.html` (+ `edifici.js`, `interno.css`): stato della pipeline notturna; fuori da
  menu, testata (`costruisci_pagine.py` lavora solo sulle pagine della cartella principale) e robots.txt, `noindex`.
  Protetta da Cloudflare Access (Caddy e api, README della fase 4).
- `stile.css`: legenda delle falde, blocchi «Falde dei tetti» e «Usa il tuo modello».
- Prove: 12 test (uno nuovo, `test_pagine_fase_c`); Chromium headless (Playwright, servito da Caddy per i Range dei
  PMTiles): falde del campione sul corpo C1 (capanna, 2 falde, fonte LiDAR), falde a gradini sulla mappa, area FV sulla falda
  sud (23°, 180°, aderente), report con le falde, modello DXF aperto senza nessuna richiesta POST, pagina interna con
  dati simulati (zone, fonti in attesa, notti, disco) e con 403.

## Aggiornamento del 04/11/2026 – edifici 3D, Fase B (da pubblicare con `?v=20261104a`)

- **Patrimonio › Ortofoto** non è più un segnaposto: `ortofoto.html` + `ortofoto.js`, mappa MapLibre con le ortofoto del
  proxy del server (`/api/ortofoto/fonti`, tessere `/api/ortofoto/<fonte>/<z>/<x>/<y>.jpg`), selettore delle fonti che
  coprono la zona (stato: «licenza verificata», «uso da confermare», «solo consultazione»), **licenza e citazione sempre
  sotto la mappa**, contorni degli edifici se c'è l'archivio 3D (non sulla demo sintetica), ortofoto AGEA dei siti da
  `/edifici3d/cc-by/ortofoto_siti/indice.json`; `?lat=&lon=&z=` e `?fonte=`.
- **Pagina 3D** (`edificio3d.js`, `edifici_calcoli.js`, `ombre_worker.js`), passi nuovi: Obblighi di legge (D.Lgs. 199/2021,
  Allegato III; zona e GG del DPR 412/93; S/V e H'T della Tabella 10 del DM requisiti minimi aggiornato), Facciate al sole
  (pezzi esposti, tabella per orientamento, grafico, lastre colorate sulla mappa da giallo chiaro a blu scuro), Confronto
  con PVGIS (tabella e grafico mensile), Classifica di priorità del patrimonio (edifici aggiunti dalla pagina o file di
  sedi, pesi modificabili, lista nel browser); sfondo «ortofoto» sotto la mappa con l'attribuzione; orizzonte del terreno
  fino a 25 km unito a quello degli edifici (FV, facciate, PVGIS); quote dei corpi relative al terreno dell'edificio
  scelto. Report `edificio` con le sezioni nuove e la vista con l'ortofoto (PNG) con licenza e citazione nella didascalia.
- **Pagine nuove** dello strumento 3D (generate dallo stesso corpo di `modelli3d.html`, `data-vista`): Fotovoltaico ›
  Sole e irradiazione (`facciate`), › Confronto con PVGIS (`pvgis`), › D.Lgs. 199/2021 (`dlgs199`), Edificio › Obblighi
  di legge (`obblighi`); Edificio › Consumi, firma energetica e priorità ha anche la classifica. Nel menu le cinque voci
  passano a «sperimentale». Edificio › Facciate e tetti resta segnaposto con un rimando alla pagina delle facciate.
- Sitografia: ortofoto regionali, EOX 2016, PVGIS, Copernicus DEM, D.Lgs. 199/2021 e DM 28/10/2025.
- Test: 2 nuovi (pagine e menu della Fase B; calcoli di facciate, orizzonte unito, obblighi e classifica con node), 11 in
  tutto. Prova in Chrome headless (Playwright, WebGL software) con il server vero della fase 4 e le fonti dal vivo:
  Ortofoto (RER, EOX, PCN), pagina 3D completa (obblighi, facciate, FV, PVGIS, classifica, sfondo, PDF con la figura).

## Aggiornamento del 04/11/2026 – edifici 3D, Fase A (da pubblicare con `?v=20261103a`)

- **Strumento 3D** in cinque pagine (stessa pagina, apertura diversa con `data-vista`): Patrimonio › Modelli 3D,
  Edificio › Geometria e luce naturale, Edificio › Consumi, firma energetica e priorità, Fotovoltaico › Ombre e
  percorso del sole, Fotovoltaico › Producibilità con le ombre. Nel menu l'etichetta passa da «in sviluppo» a
  «sperimentale». Passi: edificio (clic sulla mappa), corpi (gronda, colmo, tetto, piani correggibili; divisione con una
  linea), piani e superfici (valori dell'utente → stima), indicatori geometrici (con il grafico delle pareti per
  orientamento), ombre (giorno, ora, ciclo animato), aree FV (rettangolo sul tetto con fascia di rispetto, inclinazione,
  orientamento e montaggio precompilati e modificabili, moduli e kWp), consumi e firma energetica, report.
- File: `edificio3d.js` (pagina), `edifici_calcoli.js` (calcoli senza DOM: piani, superfici, indicatori, sole NOAA,
  ombre, orizzonte, FV, firma; usato anche da `valori_sedi.js` e dal worker), `ombre_worker.js` (profilo d'orizzonte),
  `lib/maplibre-gl/` (MapLibre GL JS 5.24.0) e `lib/pmtiles/` (PMTiles 4.4.1), con licenze e `lib/README.md`.
- Dati: da `/edifici3d/cc-by/er/prodotti/` (Caddy) o, se non ci sono, dalla **demo sintetica** `dati/edifici3d/`
  (isolato inventato vicino a Rimini, avviso «Dati sintetici di esempio» in pagina e nel report); `?archivio=demo` la
  forza. Clima dalle rotte `/api/edifici/…`; se mancano, producibilità con un anno di cielo sereno ridotto (dichiarato) e
  firma solo con i consumi d'esempio.
- **Patrimonio**: colonne facoltative `piani_fuori_terra`, `piani_interrati`, `superficie_lorda`, `superficie_netta`,
  `superficie_catastale`, `anno_costruzione` (con nomi alternativi) escluse dai valori da disegnare; nuovo passo
  «Consumi per metro quadro» (e tabella nel report) quando c'è una superficie. I file vecchi non cambiano.
- Sitografia: MapLibre, PMTiles, Shapely, pyproj, rasterio e GDAL. Stile: sezione «edifici 3D» in fondo a `stile.css`.
- Test: 2 nuovi (pagine 3D con librerie locali e licenze, niente CDN; calcoli JS con node), 9 in tutto. Prova in Chrome
  headless (Playwright, WebGL software): selezione, divisione, aree FV, producibilità, firma, report.

## Aggiornamento del 03/11/2026 – menu a cinque gruppi e pagine segnaposto (da pubblicare con `?v=20261103a`)

**Nuovo menu principale** (`parti/testata.html`, regole in `sito/README_stile.md` § «Menu a gruppi»): cinque gruppi
con un sottomenu a tendina ciascuno (`<details class="voce-gruppo">`: si apre con clic, Invio o Spazio anche senza
JavaScript; `aspetto.js` tiene aperto un gruppo alla volta, chiude con Esc o un clic fuori, frecce ↓ ↑ Inizio Fine tra
le voci, ← → tra i gruppi, Tab fuori dal gruppo lo chiude). Sul telefono gli stessi gruppi sono elenchi richiudibili
nel pulsante Menu, con il gruppo della pagina già aperto. `costruisci_pagine.py` segna il gruppo della pagina con
`data-attivo` (tre test nuovi in `tests/test_costruisci_pagine.py`, 7 in tutto).

| Gruppo | Voci |
|---|---|
| Clima e meteo | Dati climatici (`dati.html`), Legge 10 (`legge10.html`), Previsioni (`./`) |
| Patrimonio | Patrimonio (`patrimonio.html`), Ortofoto, LiDAR, Modelli 3D, Visure |
| Edificio (dall'08/11/2026 «Edifici», vedi sopra) | Geometria e luce naturale; Consumi, firma energetica e priorità; Fabbisogno con le metodiche UNI; Facciate e tetti (sole, tetti freddi e verdi); Pompe di calore e solare termico; Comunità energetiche; Clima che cambia; Obblighi di legge |
| Cogenerazione | Spark spread; Cogeneratore sull'edificio con FV e accumulo; Confronto tra alternative e trigenerazione; Emissioni; Rischio prezzo; Budget di dissipazione CAR (report 13–20) |
| Fotovoltaico | Ombre e percorso del sole; Sole e irradiazione su tetti e facciate; Producibilità con le ombre; Confronto con PVGIS; D.Lgs. 199/2021 Allegato III; Prefattibilità LEED; Prezzo catturato, accumuli e mercato (report 1–12, in attesa della licenza GME) |

Le voci che non rientrano nei gruppi sono nella riga in alto a destra («Altre pagine»): **Indicatori** (prima voce),
Come funziona, F.A.Q., Sitografia, Mirror, Contattaci; Iscriviti, ✱ e ◐ restano nella seconda riga; Privacy e Licenza
restano nel piè. Sul telefono le stesse voci sono nel Menu sotto «Altre pagine».

**25 pagine segnaposto** (classe `articolo segnaposto`): gruppo, titolo, stato («in sviluppo» oppure «In attesa della
licenza GME»), cosa farà, come funzionerà, fonti previste con la licenza, collegamenti alle altre pagine del gruppo.
Nessun dato né risultato; le pagine dei gruppi Cogenerazione e del mercato FV hanno l'avviso sul GME (collegato a
`faq.html#dati-mercato`, nuova ancora). File: `ortofoto.html`, `lidar.html`, `modelli3d.html`, `visure.html`,
`edificio-*.html` (8), `cog-*.html` (6), `fv-*.html` (7). Progetti in `fase10-edifici3d`, `fase11-visure`,
`fase12-gme-fotovoltaico`, `fase13-cogenerazione`.

**Allineamento ai termini di Zornade del 18/09/2026**: nuova F.A.Q. `#zornade` (riuso con attribuzione e fonti, niente
rivendita dei dati grezzi, niente re-identificazione, estrazione massiva = sospensione della chiave, cache a 12 mesi come
scelta di privacy, dati catastali non ufficiali), `licenza.html` (fonti e tabella del mirror), `patrimonio.html` (avviso
nelle fonti) e `patrimonio.js` (testo di licenza nei file scaricati).

Provato con Chrome senza interfaccia (Playwright) a 1440, 1000 e 390 px: nessun errore, nessuno scorrimento
orizzontale, tastiera sui gruppi (↓ apre e porta alla prima voce, → passa al gruppo accanto, Esc chiude).
Pubblicazione: `AGGIORNAMENTO_2026-11-03.md`.

## Statistiche › Indici dei prezzi (11/11/2026)

`sito/indici-prezzi.html` e `sito/indici_prezzi.js` (con `grafici.js` e `tabelle.js`), voce di Statistiche prima di
Costi energetici Sanità; non sperimentale (valori pubblicati dalle fonti; il PFOR ha il metodo dichiarato nella F.A.Q.
`#indici-prezzi`). Legge `dati/prezzi/indici.json`, che **non è nel repository** (lo scrive il worker sul server ogni
notte; `.gitignore`); senza il file la pagina dice che i valori tornano dopo l'aggiornamento notturno.
- Per ogni indice: barre affiancate gennaio–dicembre (anno prima tenue, anno in corso pieno; verde elettricità, arancio
  gas: `--prezzi-ele`, `--prezzi-gas` in `stile.css`), tabella con la variazione (vuota dove manca un anno), lotto dalla
  casella a discesa (Intercent-ER, Consip), fascia o uso con i pulsanti; €/Smc con 4 decimali.
- **Confronto sui consumi** (`#confronto-consumi`): file CSV, Excel o ODS con «mese», «F1», «F2», «F3» (kWh; MWh se il
  titolo lo dice), letto nel browser con `tabelle.js`; costo dell'energia con Intercent-ER lotto 1 e 2 e Consip (lotto a
  scelta) nei due anni, **sugli stessi mesi** (quelli con i prezzi di tutte e tre le offerte in entrambi gli anni), un
  grafico con 6 barre e una tabella (€ e €/MWh, sottolineato il più basso). Esempio inventato:
  `sito/esempi/consumi_fasce_esempio.csv`.
- Prova nel browser: `tests/test_indici_prezzi_browser.py` (file dei prezzi servito dalla prova).
