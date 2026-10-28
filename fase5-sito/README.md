# Fase 5 – Sito: mappa, previsione, patrimonio, Legge 10, metodo

Sito statico (HTML, CSS e JavaScript senza librerie esterne), servito da Caddy nella fase 4.

```
sito/
  index.html        mappa dei comuni colorata con i gradi giorno previsti a 7 giorni, ricerca indirizzo
                    (Zornade), caricamento CSV, scelta della modalità, grafico con le fasce di probabilità
  patrimonio.html   elenco di edifici (CSV) → punto e particella catastale, mappa dei punti, esiti, download
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
python costruisci_pagine.py --versione 20261028d   # aaaammgg + lettera: nuova versione in pagine e script
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
(`?v=20261028d`): quando si cambiano stile o script, si aumenta con `costruisci_pagine.py --versione …`, così i
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
- Versione cache: `?v=20261028d`. Provato con Playwright: pulsanti a 1440 e 390 px (tema scuro e chiaro), nessun
  errore né scorrimento orizzontale, clic su ODS → `formato=ods`; F.A.Q. aperta da `#formati-report`.
