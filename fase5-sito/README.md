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
| Edificio | Geometria e luce naturale; Consumi, firma energetica e priorità; Fabbisogno con le metodiche UNI; Facciate e tetti (sole, tetti freddi e verdi); Pompe di calore e solare termico; Comunità energetiche; Clima che cambia; Obblighi di legge |
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
