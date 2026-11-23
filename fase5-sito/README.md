# Fase 5 – Sito: mappa, previsione, patrimonio, Legge 10, metodo

Sito statico (HTML, CSS e JavaScript senza librerie esterne), servito da Caddy nella fase 4.

```
sito/
  index.html        pagina iniziale (dal 23/11/2026): disegno fermo di Claude Design, uno per tema (parti/scena_home.html,
                    home_*_estate.webp, home.js) con 16 bersagli, schede dei gruppi del menu (parti/home.toml), ultime novità; i
                    vecchi indirizzi con le scelte (/?comune=…, #…) passano a previsioni.html
  previsioni.html   (fino al 22/11/2026 era index.html) mappa dei comuni colorata con i gradi giorno previsti a 7 giorni,
                    ricerca indirizzo, caricamento CSV, scelta della modalità, grafico con le fasce di probabilità
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
  aria-*.html       Trattamento aria › Psicrometria (14/11/2026, sperimentali): aria-trasformazioni, aria-ore, aria-latenti,
                    aria-freecooling, con aria_*.js (logica della pagina) e i moduli comuni psicro.js, diagramma_aria.js,
                    scelta_aria.js, gruppi_ore.js (sezione «Trattamento aria» qui sotto)
  strumenti/psicro_UTA.xlsx  foglio psicrometrico UTA scaricabile (generato da fase14-trattamento-aria/foglio)
  esempi/           CSV di consumi SINTETICI e patrimonio_esempio.csv (tre edifici, uno per tipo di dato)
  rete-elettrica.html  Statistiche › Stato della rete elettrica (17/11/2026, sperimentale): rete_elettrica.js
  fv-cabine.html    Fotovoltaico › Cabine primarie (17/11/2026, sperimentale): fv_cabine.js
  pluviometria.html Clima e meteo › Dati pluviometrici (22/11/2026, sperimentale): pluviometria.js e pioggia_gl.js
                    (indice, immagini e legenda della pioggia, usato anche da rete_elettrica.js)
  rete.js           parte comune delle pagine della rete (e di Comunità energetiche): API /api/rete/…, dati sintetici
                    con ?prova=1, colori e regola della criticità, strisce e retino, cabine, riquadretti, GSE dal browser
                    (unico indirizzo del servizio nel sito), CSV/PDF/Excel/ODS (sezione «Rete elettrica» qui sotto)
  edificio-cer.html Fotovoltaico › Comunità energetiche (in lavorazione): cer_sedi.js (sedi, aree convenzionali del GSE
                    dal vivo, cabine del comune, mappa) e analisi_pubbliche.js (energia condivisa)
  collegamento.js   «Collegamento a questa simulazione» (20/11/2026): scelte della pagina nella query string, riquadro con
                    l'indirizzo e «Copia» in fondo al pannello; inventario delle pagine qui sotto, regole in README_stile.md
costruisci_dpr412.py  rigenera dati/dpr412.* (Normattiva + elenchi ISTAT di comuni, soppressi e variazioni)
abbinamento_dpr412.md scelte e casi dell'abbinamento al codice ISTAT attuale (refusi, fusioni, cambi di nome)
costruisci_mappa.py  genera dati/mappa/ dai confini Gramscii (versione bloccata) e da comuni.parquet nazionale
scarica_font.py      scarica i caratteri usati (Hanken Grotesk, Barlow; OFL) e scrive font/font.css: i visitatori
                     non chiamano Google Fonts; --solo-css riscrive solo font.css dai file presenti
costruisci_pagine.py rimette in tutte le pagine testata, piè e parte comune del <head> da parti/, e il numero di
                     versione (--versione); test in tests/test_costruisci_pagine.py
parti/               testa.html, testata.html, piede.html: le parti comuni delle pagine, da modificare solo qui
```

Menu di tutte le pagine (il gruppo Patrimonio si chiama Territorio dal 17/11/2026): Previsioni, Patrimonio, Legge 10, Dati storici, Come funziona, F.A.Q., Sitografia, Mirror, Contattaci, Iscriviti (modulo
di listmonk). Piede: Contattaci · Licenza. Le pagine di testo (`.articolo`) occupano tutta la larghezza dello schermo
(27/10/2026). ANNCSU (anncsu.open.agenziaentrate.gov.it), Agenzia delle Entrate, ISTAT e Zornade sono sempre
collegati nel testo delle pagine (non nei titoli delle F.A.Q., dove il clic apre la risposta).

## Numeri col punto delle migliaia ovunque (20/11/2026, richiesta di Paolo; `?v=20261121a`)

Modulo comune `sito/numeri.js` (`window.EUGENIO_NUMERI.formato(v, decimali, minimi, vuoto)` e `raggruppa(testo)`), nella
testa di ogni pagina (`parti/testa.html`, subito dopo `protezione.js`), nel worker del DB topografico (`dbtr_worker.js`,
`importScripts`) e nella pagina interna degli edifici; in node lo caricano con `require("./numeri.js")` i moduli provati
anche lì (`analisi_pubbliche.js`, `emissioni_cog.js`, `dbtr_lettore.js`, `aria_trasformazioni.js`). Usa
`Intl.NumberFormat("it-IT", { useGrouping: "always" })` dove c'è, altrimenti il ripiego col punto messo a mano che avevano
`carichi.js` ed `elettricita.js` (che ora usano il modulo). Lo usano al posto di `toLocaleString`/`toFixed` tutti gli
script che mostrano numeri: `aggiungi_dbtr.js`, `analisi_pubbliche.js`, `app.js` (anche la scala dei gradi giorno e i kB
del file), `cerca_luogo.js`, `clima_storico.js`, `cti_legge10.js`, `dati.js`, `dbtr_lettore.js`, `edifici_pubblici.js`,
`edificio3d.js`, `emissioni_cog.js`, `esporta_mappa.js`, `importa_modello.js`, `indicatori.js`, `indici_prezzi.js`,
`legge10.js`, `patrimonio.js`, `pubblici_enti.js`, `rete.js` (numeri, non le date), `righello.js`, `valori_sedi.js`, `visure_patrimonio.js`, i
moduli del Trattamento aria, `carichi.js`, `elettricita.js`; anche i conteggi lunghi nei messaggi (righe, ore, corpi,
sedi). Restano senza punto date, anni, codici, coordinate, indirizzi, campi modificabili e i numeri dei file CSV/Excel/ODS.
Regola in `README_stile.md` («Numeri»); prova `test_costruisci_pagine.py::test_numeri_col_punto_delle_migliaia` (nessun
`toLocaleString`/`Intl.NumberFormat` per i numeri negli script, modulo in ogni pagina, casi in node).

## Collegamento a questa simulazione (20/11/2026, richiesta di Paolo; `?v=20261121a`)

«Per tutte le pagine che non richiedono il caricamento di un file CSV ma funzionano tramite selezioni, si generi un
collegamento che l'utente può salvare e reincollare nel browser per ripartire con la stessa simulazione, cioè con la stessa
selezione, senza rifarla. In fondo alla pagina deve apparire il collegamento, con un pulsante per copiarlo negli appunti, che
si aggiorna automaticamente a ogni modifica; reincollandolo si riparte esattamente dallo stesso punto.»

- Modulo comune `sito/collegamento.js` (`window.EUGENIO_COLLEGAMENTO`: `registra`, `aggiorna`, `quando`, `indirizzo`) e stile
  `.collegamento-simulazione` in `stile.css`; regole e istruzioni per le pagine nuove in `sito/README_stile.md` § «Collegamento
  a questa simulazione». Il riquadro sta in fondo al pannello di destra (in fondo all'articolo nelle pagine a una colonna;
  in tutte e due prima di «Nello stesso gruppo», se c'è); lo script è incluso pagina per pagina, subito dopo `aspetto.js` (non nella testa comune:
  le pagine di testo non lo caricano).
- Lo stato è nella query string con nomi brevi in italiano, riscritto con `history.replaceState` a ogni modifica (350 ms di
  ritardo); i parametri che le pagine usavano già restano quelli. All'apertura il modulo rimette i controlli
  `data-collegamento` nell'ordine della pagina (aspettando i menu caricati dopo) e poi chiama `applica` delle registrazioni;
  la regione nell'indirizzo vale più di quella ricordata dalla piccola mappa. Oltre 2.000 caratteri restano le scelte
  principali, con un avviso. Mai file caricati, nomi o dati personali, segreti; niente al server.
- Inventario delle pagine (`sito/*.html`). Classe **a** = a sole scelte, collegamento completo; **b** = con il caricamento
  di un file: collegamento per le sole scelte che non dipendono dal file; **c** = pagina di testo, modulo o segnaposto:
  niente collegamento.

| Pagina | Script | Classe | Cosa va nell'indirizzo |
|---|---|---|---|
| `legge10.html` | legge10.js | a | regione, comune (già della pagina), anni |
| `dati.html` | dati.js | a | regione, dataset (già), var, tip, tass, freq, dal, al, stagioni, fino, cop, area, prov, comuni (codici ISTAT, anche di altre regioni), capoluoghi, formato |
| `indicatori.html` | indicatori.js | a | regione, ente (già), comp, componenti, anno |
| `elettricita.html` | elettricita.js | a | regione o vista=italia, modo (già; dal 21/11/2026 anche `emissioni`), inizio e fine (dal 22/11/2026; `anno` dei collegamenti vecchi = un anno solo), barre, fondo, ortofoto |
| `rete-elettrica.html` | rete_elettrica.js | a | regione, comune (già), criticita, altri, cabine, interruzioni, ortofoto; prova=1 resta |
| `pluviometria.html` | pluviometria.js | a | durata, passo, secondi, fine (null = ultimo dato), lat, lon, pioggia, interruzioni, ortofoto (22/11/2026) |
| `ortofoto.html` | ortofoto.js | a | lat, lon, z, fonte (già), archivio, particelle, contorni (lo spostamento manuale della foto resta nella scheda) |
| `edifici-pubblici.html` | edifici_pubblici.js, pubblici_enti.js | a | lat, lon, z, ref o bene (già), tipi, enti, ortofoto, fonte, particelle, contorni; dal 22/11/2026 modo (`enti`), sel (chiavi degli enti nell'ordine dei colori), ruolo, natura, ordina (`colonna:asc|desc`), tipo_ente, regione_ente (secondari) |
| `aria-trasformazioni.html` | aria_trasformazioni.js | a | comune (già), anni, inverno, estate, diagramma, uta (dati e sequenze diversi dai predefiniti, JSON compatto) |
| `aria-ore.html` | aria_ore.js | a | comune, anni, inverno, estate, diagramma, gruppi, nuvola, raggio, trasp, comfort, vedi_comfort, vedi_progetto, tabella (non le condizioni di progetto corrette a mano) |
| `aria-latenti.html` | aria_latenti.js | a | comune, anni, inverno, estate, diagramma, obiettivo_estate, obiettivo_inverno, portata, riferimento, gruppi-estate, gruppi-inverno |
| `aria-freecooling.html` | aria_freecooling.js | a | comune, anni, inverno, estate, diagramma, gruppi, tutti i campi dell'UTA (V, riferimento, quotaMinima, estateT…, epsS, epsL…), gruppo_diagramma (non le condizioni di progetto corrette a mano) |
| `cog-emissioni.html` | emissioni_cog.js | a | modo, elettrica, calore, gas, unita_gas, potenza, ore, eta_e, eta_t, anno, rete, eta_caldaia, calcolato (il calcolo si rifà da solo) |
| `edificio-clima.html` | analisi_pubbliche.js | a | istat (già), dal, base, pendenza |
| `previsioni.html` (Previsioni; fino al 22/11/2026 `index.html`) | app.js | b | regione, comune, cosa, tipo, modalita, orizzonte, verifica, cov, calcolato (solo «Solo il clima»); il file dei consumi va ricaricato |
| `indici-prezzi.html` | indici_prezzi.js | b | scelte (lotto e fascia di ogni indice), lotto_consip; il file dei consumi per fascia va ricaricato |
| `fv-cabine.html` | fv_cabine.js | b | centro, punti (solo coordinate dei punti segnati o cercati), fonte scelta a mano, particelle, contorni; non i punti dell'elenco caricato |
| `edificio-cer.html` | cer_sedi.js, analisi_pubbliche.js | b | centro, sedi (coordinate e cabina scelta a mano, non i nomi), fonte, aree_gse, particelle, contorni; non le sedi del file né il file orario |
| `modelli3d.html`, `edificio-geometria.html`, `edificio-consumi.html`, `edificio-obblighi.html`, `fv-dlgs199.html`, `fv-irradiazione.html`, `fv-ombre.html`, `fv-producibilita.html`, `fv-pvgis.html` | edificio3d.js | b | edificio, lat, lon (edificio in 3D, altrimenti il punto in 2D; già letti all'apertura), archivio=demo resta, ortofoto, fonte, particelle, contorni, inclinazione, tetti, uso, dati dell'edificio (piani, superfici, anno), intervento, pubblico, giorno, ora, modulo_w, modulo_lati, fascia, vettore, unita, consumi (secondario), costo; niente con un modello importato, il DB topografico letto nel browser o una sede del Patrimonio |
| `patrimonio.html` | patrimonio.js e altri | c (b senza scelte utili) | niente: tutto dipende dal file degli edifici (e dai file delle visure e dei valori); la regione è già in `?regione=` |
| `importa-dxf-ifc.html`, `aggiungi-dbtr.html` | importa_modello.js, aggiungi_dbtr.js | c (solo file) | niente: senza il file non c'è niente da ripetere |
| `dati-per-email.html`, `contatti.html` | dati_per_email.js, contatti.js | c (moduli) | niente: moduli con email e dati personali, non simulazioni |
| `faq.html`, `metodo.html`, `licenza.html`, `privacy.html`, `sitografia.html`, `mirror.html`, `novita.html`, `esempi.html`, `contributi.html`, `dbtr-istruzioni.html`, `fv-leed.html`, `link.html` | – | c (testo) | niente |
| `cog-car.html`, `cog-confronto.html`, `cog-rischio.html`, `cog-simulazione.html`, `cog-spark-spread.html`, `edificio-conto-termico.html`, `edificio-ecobonus.html`, `edificio-fabbisogno.html`, `edificio-impianti.html`, `edificio-involucro.html`, `fv-mercato.html`, `lidar.html`, `visure.html` | – | c (segnaposto) | niente (da aggiungere quando diventano pagine con scelte) |
| `carichi.html` | carichi.js | a | zona, da, a, passo (già della pagina, 20/11/2026; dal 21/11/2026 `passo` solo con le ore, `passo=60`); dal 22/11/2026 finestra (`finestra=AAAA-MM-GG_AAAA-MM-GG`, solo se non è tutto il periodo) e spente (`spente=fv,eol`, solo con fonti spente); dal 22/11/2026 b gli stessi sei con «2» per la metà destra (`zona2`, `da2`, `a2`, `passo2`, `finestra2`, `spente2`) |
| `suolo.html` | suolo.js | a | regione o vista=italia, provincia, modo (scritti dalla pagina), inizio, fine, unita (solo se non ha), barre, fondo, ortofoto (22/11/2026) |

- Moduli comuni toccati: `strati_gl.js` (caselle particelle e contorni con `data-collegamento`), `scelta_aria.js` (anni e
  livello dall'indirizzo, più forti della memoria del browser), `gruppi_ore.js` (gruppi dall'indirizzo), `diagramma_aria.js`
  (`diagramma=mollier`). In Ore di funzionamento gli anni del collegamento valgono come scelti a mano (non si alzano da soli).
- Trovati con le prove a 375 px e corretti: in Emissioni la tabella dei totali e quella di sensibilità, in Cambiamento
  climatico la tabella dei risultati allargavano la pagina sul telefono (ora scorrono dentro di sé).
- Prove: `tests/test_collegamento_browser.py` (una per pagina delle classi a e b, più le nove pagine 3D sulla demo
  sintetica in Modelli 3D e Ombre): scelte, collegamento letto dal riquadro, pagina nuova con quell'indirizzo in un contesto
  nuovo (senza memoria del browser), stesse scelte, campo uguale all'indirizzo, 375 px senza scorrimento orizzontale,
  nessun errore JavaScript; screenshot (1400 e 375 px) se esiste `/home/claude/wt_collegamento_prove/`.

## Comunità energetiche: strato delle aree acceso in partenza (20/11/2026, 18:40, richiesta di Paolo; `?v=20261121a`)

«Modifica la pagina per iniziare con il layer aree convenzionali attivo; anche se è spento, quando l'utente aggiunge un punto
della mappa si accende.» La casella «Aree convenzionali (GSE)» è `checked` nell'HTML e `strato()` la legge alla fine di
`creaMappa()`; `aggiungi()` chiama `accendiStrato()` per ogni sede con le coordinate (clic, ricerca, coordinate, elenco), che
la riaccende se l'utente l'aveva spenta (ma non quando le sedi tornano da un collegamento con `aree_gse=0`: `applica`
la rispegne). Le domande al GSE per lo strato partono sempre e solo da zoom 10 (all'apertura la
mappa è sull'Italia, nessuna domanda). I messaggi dei confini delle sedi vanno nel passo 1 a destra (`messaggio-sedi`),
quelli dello strato restano sotto la mappa. Prove: `test_cer_browser.py`.

## Pagina iniziale (22/11/2026, richieste di Paolo delle 11:38 e delle 12:13; versione statica dal 23/11/2026)

Paolo: «ci vuole una home page che aiuti l'utente a capire cosa fa eugenio senza rimanere disorientato»; poi: «uno schema
grafico che mostra un edificio 3d e le reti che lo alimentano, il territorio che lo circonda e il meteo che gli sta sopra,
animato per stagione (d'estate sole e pioggia, d'inverno sole e neve) e che posizionando il mouse faccia vedere le funzioni
(raggruppate per gruppi, con titolo e descrizione di gruppo). Cliccando sulle parti grafiche si aprono le schede e cliccando
sulla voce si apre la pagina, aprendo anche il relativo menu in alto in orizzontale».

- `index.html` non è più Previsioni: titolo e una riga su cosa fa EuGEnio, poi il **disegno** e sotto le **schede dei
  gruppi** («Da dove cominciare» con un pulsante per gruppo), poi «Come lavora EuGEnio» e le ultime tre novità.
- **Storia**: la prima versione animata (scena a strati con le stagioni, `v2026.11.22b`) era lentissima sul sito vero e
  non mostrava titoli e descrizioni; è stata ritirata la sera del 22/11 (`v2026.11.22c`, `/` di nuovo Previsioni). Dal
  **23/11/2026** (`v2026.11.23`, versione 20261123a) torna con la **versione statica** rifatta da Paolo con Claude Design
  (zip `eugenio_home_statica_2026-11-23.zip`).
- **Disegno** (`parti/scena_home.html`, blocco `<!-- scena-home -->` messo da `costruisci_pagine.py`, con il suo `<style>`):
  un'**immagine ferma per tema**, `sito/home_scuro_estate.webp` (variante futuristica) e `home_chiaro_estate.webp`
  (variante tecnica), 1920 × 1080 dal 23/11 b (prima 1920 × 1400), scambiate con `[data-theme="light"]`; **nessuna animazione**. Gli unici elementi
  attivi sono i **16 bersagli** `button.sh-punto data-parte data-gruppo` (mirini; tratteggiati e grigi/arancio, classe
  `sh-poi`, le parti «prossimamente»), posizionati in percentuale; testi e bersagli scalano con la scena (`cqw`). Legenda del
  consumo di suolo **con dati d'esempio**. Gli stili della vecchia scena animata sono stati tolti da `stile.css`; il blocco
  annulla anche cornice e proporzioni di `.scena-contenitore`.
- **16:9** (23/11/2026 b): fondali nuovi di Claude Design 1920 × 1080 (scuro 81 KB, chiaro 118 KB) per tutti gli schermi,
  `.sh-quadro` con `aspect-ratio: 16/9`, bersagli riposizionati da Design; sotto i 560 px di scena la scheda flottante è
  fissata in fondo allo schermo (`position: fixed`, al più 70 % dell'altezza).
- **Dimensione** (`home.js`): larga quanto la pagina (esce dalla colonna, centrata) ma mai più alta dello spazio che resta
  **dal bordo alto del disegno** (sotto testata, titolo e testo, a pagina non scorsa) al fondo della finestra (23/11 b:
  prima contava solo la testata e bisognava scorrere); rapporto letto dall'`aspect-ratio` del CSS; ricalcolo anche a font
  caricati. Il testo di presentazione (`.home-sotto`) va su tutta la larghezza. Lo spostamento `--sh-x` si calcola dalla posizione reale della scena, per difetto, così non
  sborda mai a destra (23/11: col bordo del contenitore sborda di 1 px sul telefono).
- **Parti** (`parti/home.toml`, `[parti.…]`): titolo, descrizione, gruppo e pagine collegate (anche di altri gruppi e in
  lavorazione). `costruisci_pagine.py` (`parti_home`, blocco `<!-- parti-home -->`, JSON) aggiunge nome e stato dal menu e
  segna «prossimamente» le parti senza pagine accessibili (oggi solare termico, pompa di calore, centrale termica, frigo,
  cogeneratore, cabina del gas). La parte «cabina primaria» non c'è nel disegno: le sue pagine (Stato della rete elettrica,
  Cabine primarie) sono nel **traliccio**.
- **Comportamento** (`home.js`): i **titoli** dei bersagli (23/11 b: 30 % più grandi, `clamp(14px, 1,43cqw, 19,5px)`)
  compaiono a turno, uno alla volta (1 s acceso, **0,5 s** spento), e si fermano mentre si usa la scena; stanno a sinistra
  del bersaglio nella parte destra del disegno e, se non ci stanno da nessuna parte (telefoni), scorrono dentro il bordo
  (`--dx`). **Titoli = argomenti del menu**, non oggetti del disegno (23/11 b, Paolo: niente «sul tetto», «sulla torre»),
  uguali in `home.toml` e nei bottoni di `scena_home.html`; **sostando** ~0,35 s su un bersaglio (o col fuoco da tastiera) compare la descrizione breve
  («Clic per le pagine» o «Prossimamente»); il **clic** (Invio, tocco) apre sopra l'immagine, accanto al bersaglio, la
  **scheda flottante** con le pagine della parte (quelle non disponibili spente, con lo stato) e «Tutte le pagine di …», che
  apre la scheda del gruppo sotto il disegno; si chiude con ×, Esc o un clic fuori. Sotto i 560 px di scena la scheda sta in
  basso e la legenda sparisce. **Clic su una pagina**: `localStorage` «menu-fissato» = gruppo della pagina nel menu (preso
  dalle schede dei gruppi), così la pagina si apre con le voci del gruppo in orizzontale sotto il menu (`aspetto.js`).
- **Schede**: le scrive `costruisci_pagine.py` (`schede_home`, blocco `<!-- schede-home -->`) dal menu (`parti/testata.html`:
  ordine, nomi, stato sperimentale / in sviluppo / in lavorazione / licenza GME) e da `parti/home.toml` (parte del disegno,
  descrizione del gruppo, una riga per pagina). Una pagina nuova del menu entra da sola nella scheda; la riga va aggiunta in
  `home.toml` (la prova `test_pagina_iniziale` lo controlla). Le ultime tre novità: `ultime_novita`, blocco
  `<!-- ultime-novita -->`.
- Previsioni sta in `previsioni.html` (menu e collegamenti aggiornati). Uno script in testa a `index.html` manda a
  `previsioni.html` ogni indirizzo con parametri (tranne `utm_…`) o con un'ancora: i collegamenti salvati e quelli delle
  email continuano a funzionare.
- Prove: `test_costruisci_pagine.py::test_pagina_iniziale` (parti, schede, righe, voci, redirect, novità) e
  `test_home_browser.py` (23/11: scena nella finestra e solo bersagli attivi, titoli a turno, descrizione, scheda
  flottante e menu fissato, pagina di un altro gruppo, tema chiaro e vecchi indirizzi, telefono a 375 px senza sbordare).

## Clima e meteo › Dati pluviometrici (22/11/2026, richiesta di Paolo; sperimentale, release `v2026.11.22b`, versione 20261122b)

Pagina `pluviometria.html` + `pluviometria.js` + `pioggia_gl.js`, voce «Dati pluviometrici» (sperimentale) nel gruppo
Clima e meteo **prima di Previsioni**. Decisioni di Paolo: solo il «Merging» del DPC ogni 30 minuti (niente radar puro),
fini statistici e non di allerta, licenza CC BY-SA 4.0 scritta accanto ai dati.
- Mappa MapLibre con l'immagine della pioggia (sorgente `image`, `updateImage`; nessuna `attribution` nella sorgente: la
  citazione sta nell'`AttributionControl` con `customAttribution`), strati «Pioggia», «Interruzioni» (del periodo, da
  `/api/rete/interruzioni/periodo`) e «Ortofoto» come in Stato della rete elettrica, righello.
- Animazione: `#durata` 3/6/12/24/168 ore (predefinito 24), `#passo` 3/6/12/24 ore automatico (durata ≤ 24 ore → 3 ore,
  7 giorni → 24 ore; i passi più lunghi della durata sono disabilitati; l'utente lo può cambiare), `#secondi` (0,7), «Play»
  e cursore `#fine` sulla fine del periodo; ogni immagine = pioggia caduta nel passo che finisce a quell'ora (CUM3, CUM6,
  CUM12 o CUM24); immagini precaricate; indice in `dati/radar/indice.json` scritto dal worker.
- Clic: `/api/radar/punto` (ultimi 3/6/12/24 ore) e comune (`C.comuneNelPunto`) → `/api/radar/comune/{istat}`: grafico
  SVG (`EUGENIO_GRAFICI`) dei 30 giorni misurati con la prevista, tabella, file CSV/PDF/Excel con `licenza: "CC BY-SA 4.0"`.
  «–» = nessuna misura, mai zero.
- In `rete-elettrica.html` la casella `#strato-pioggia` «Pioggia misurata (ultime 3 ore)», spenta in partenza: ultimo
  CUM3 sotto le cabine, legenda, aggiornata ogni 5 minuti.
- Stile: blocco «dati pluviometrici» in `stile.css`; 375 px senza scorrimento orizzontale. Prove:
  `test_pluviometria_browser.py` (con `page.route` sulle rotte e immagini finte), `test_rete_browser.py`,
  `test_costruisci_pagine.py`.

## Statistiche › Suolo e aree agricole (22/11/2026, richiesta di Paolo; sperimentale, release `v2026.11.22`, versione 20261122a)

Pagina `suolo.html` + `suolo.js`, voce «Suolo e aree agricole» (sperimentale, «S») nel gruppo Statistiche dopo «Carichi
elettrici». Stessa struttura e stile di «Produzione e consumi di elettricità» (`main.pagina-elettricita.pagina-suolo`, classi
`comandi-elettricita`, `grafico-elettricita`, `tabella-elettricita` riusate): mappa MapLibre con le regioni bianche e un
istogramma per regione (immagini della mappa, `DOPPIO = 2`), clic → province, secondo clic → Italia, piccola mappa,
caselle Istogrammi / Regioni bianche / Ortofoto, righello, a destra grafico «anno per anno», province, tabella con il
totale, «Come leggere i dati», collegamento salvabile, solo «Scarica l'immagine», avviso sperimentale.
- **Tre scelte** (decisione di Paolo): **Suolo** (barre affiancate: SAU e superficie non utilizzata del censimento 2020,
  suolo consumato, in aree a pericolosità idraulica P2 e da frana P3+P4, entro 300 m dalla costa, in aree protette;
  interruttore **ha / % del territorio / m² per abitante**), **Consumi** (colonna impilata per causa: edifici, strade e
  infrastrutture, piazzali e aree produttive, cantieri, cave e discariche, fotovoltaico a terra, altro, non attribuito; accanto
  la colonna verde «di cui su suolo agricolo», stima EuGEnio), **Colture** (colonna impilata per famiglia).
- **Colori** (Paolo, 22/11/2026: nel tema scuro i grafici non si leggevano): `TAVOLOZZA` in `suolo.js`, per id della voce,
  `[scuro, chiaro]` come le serie di `stile.css`: nel tema scuro colori chiari come nella pagina dell'elettricità (contrasto
  ≥ 4,5:1 sui riquadri `--foglio`), nel tema chiaro più scuri (≥ 3:1 sul bianco); fra le voci dello stesso gruppo ΔE2000 ≥ 7,8
  anche con deuteranopia, protanopia e tritanopia simulate (Machado 2009). Valgono per mappa, grafici, legende e immagine
  scaricata; il colore nei dati della fase 16 resta solo per voci nuove senza tavolozza. «Di cui su suolo agricolo»
  `#77f69e` (scuro) / `#2a9a50` (chiaro), al posto di `#1b5e20`. Comuni per % consumato: nel tema scuro la scala va dal
  giallo chiaro al viola chiaro (`#fff3b8 → #a35ee6`, tutte ≥ 4,5:1 sul fondo), nel tema chiaro resta `#fff5d6 → #6b0f1a`.
  Al cambio di tema (`eugenio:aspetto`) si ridisegnano anche gli istogrammi della mappa. Il trattino del valore iniziale
  resta nero (in legenda con il bordo).
- **Periodo a due indicatori** (Paolo, 22/11/2026 01:00): due `input type=range` sovrapposti in `.cursore-doppio` (guida
  colorata fra i due con `--da` e `--a`; ognuno si muove con mouse, dito e tastiera, `aria-label` «Anno iniziale/finale del
  periodo», `aria-valuetext` con l'anno); all'apertura tutti e due sull'ultimo anno. Flussi (Consumi) = somma dei periodi
  fra le due carte (`flussiDelPeriodo`: con un anno solo il periodo che finisce lì, anche 2006–2012 o 2012–2015); stati
  (Suolo, Colture) = anno finale, con la variazione nel riquadretto e in tabella e un **trattino nero** sull'istogramma al
  valore dell'anno iniziale. Grafico «anno per anno» su anni di calendario: anni senza carta vuoti, periodi lunghi come barre
  larghe alte quanto la media annua (scritta «media annua»), periodo scelto riquadrato, «rev» sopra il 2023 e il 2024.
- **Scala** degli istogrammi: valore più alto fra tutte le unità (regioni o province della regione) e tutti gli anni; per i
  consumi i periodi di un anno e il periodo scelto (i periodi lunghi schiaccerebbero le barre annuali).
- **Provincia e comuni**: con una regione scelta il menu «Provincia» (o un clic sulla barra della provincia nel grafico delle
  province) apre la provincia: con «Suolo» i comuni si colorano per % di suolo consumato all'anno finale (6 classi, da
  `#fff5d6` a `#6b0f1a`, riquadretto con ha, %, variazione o incremento netto), l'istogramma della provincia sparisce per non
  coprirli e la tabella passa ai comuni. Il clic sulla mappa resta quello dell'elettricità (secondo clic sulla regione =
  Italia). In Sardegna le colture sono solo regionali (nota sotto il grafico).
- **Dati**: `dati/suolo/italia.json` e `dati/suolo/RR.json`, costruiti dal worker con `fase16-suolo` (formato nel README della
  fase 16), in `.gitignore` come quelli dell'elettricità; senza i file la pagina lo dice sotto la mappa.
- Fonti nel piè, metodo in `metodo.html#suolo`, caso d'uso in `esempi.html`, righe in `EUGENIO_PER_AGENTI.md` (due copie) e
  `llms.txt`. Prove: `tests/test_suolo_browser.py` (dati inventati della fase 16: istogrammi, regione → province, provincia →
  comuni, cambio di scelta, periodo da tastiera, collegamento, 375 px, nessun errore).

## Statistiche › Carichi elettrici (20/11/2026, richiesta di Paolo; sperimentale, `?v=20261121a`)

Pagina `carichi.html` + `carichi.js`, voce «Carichi elettrici» (sperimentale) nel gruppo Statistiche dopo «Produzione e
consumi di elettricità». **Pagina unica a tutta larghezza** (`main.articolo.pagina-carichi`), senza mappa grande e senza
divisione in due metà.

- **Zona**: solo dalla piccola mappa accanto al titolo, grande come nelle altre pagine ma con le **zone di mercato**
  (`dati/mappa/zone.json`, costruito da `costruisci_zone.py` unendo le regioni di `italia.json` con shapely; colori
  `--reg-RR` di una regione della zona; zoom `+ − ⟲` con `EUGENIO.zoomabile` di `minimappa.js`, che qui non disegna
  la sua mappa delle regioni perché manca `.mappa-area`). Clic = zona; secondo clic o «Tutta Italia» = Italia.
  Zone dal 1° gennaio 2021 (ARERA 103/2019; GME, «Zone geografiche», 18/10/2023), le stesse dei dati di Terna del
  2026: Nord, Centro-Nord (Toscana, Marche), Centro-Sud (Umbria, Lazio, Abruzzo, Campania), Sud (Molise, Puglia,
  Basilicata), Calabria, Sicilia, Sardegna.
- **Periodo**: due date modificabili, predefinito gli ultimi 12 mesi fino all'ultimo dato; pulsante «Ultimi 12 mesi».
  **Passo**: casella «Quarti d'ora» (predefinita); senza, ore = media dei quarti d'ora dell'ora.
- **Indirizzo**: `?zona=NORD&da=AAAA-MM-GG&a=AAAA-MM-GG&passo=60` (`history.replaceState` a ogni scelta; senza
  `zona` = Italia, senza `passo` = quarti d'ora; i collegamenti vecchi con `passo=15` valgono ancora). Dopo l'unione (20/11/2026) la pagina carica `collegamento.js` e si registra con queste quattro chiavi
  (`regione: false`, `pronto` alla fine dell'avvio): riquadro «Collegamento a questa simulazione» in fondo alla pagina;
  prova in `test_collegamento_browser.py::test_carichi`.
- **Grafici** (tutti con la freccina del riquadro): valori del periodo (energia, potenza massima e minima con l'istante,
  media, quota rinnovabile per l'Italia, quarti d'ora senza dati); profilo giornaliero (fascia minimo–massimo e media
  per quarto d'ora o ora del giorno, ora italiana); curva di durata (potenze in ordine decrescente, ascissa in ore);
  potenza per fonte in MW (dal 22/11/2026, vedi sotto) e fonti (barre al 100 % per quarto d'ora o ora, colori di
  `fase15-elettricita/elettricita/costruisci.py`, solo Italia: con una zona scelta compare la nota «Terna pubblica la
  produzione per fonte solo per tutta l'Italia»).
- **Zoom proprio**: rotella = zoom dell'asse orizzontale attorno al puntatore, trascinamento = spostamento, due dita =
  zoom, doppio clic = vista iniziale, tastiera (frecce, `+ − 0`). Il grafico si **ridisegna con i dati della vista**
  (percorsi aggregati per pixel: le barre delle fonti sono una colonna per pixel che somma i quarti d'ora coperti, o una
  barra per quarto d'ora quando c'è posto; la curva di durata un punto per pixel). Con il grafico ingrandito l'asse
  verticale si adatta ai valori visibili. La vista è comune alla pagina e al riquadro. `grafici.js` passa all'SVG
  con `svg.__zoomProprio = { zoom(fattore, clientX), vistaIniziale() }` i tasti `+ − 0` e «Vista iniziale» del
  riquadro e gli lascia rotella, trascinamento e doppio clic (regola in `README_stile.md`, «Grafici»).
- **Dati**: `dati/carichi/indice.json`, `carico_AAAA-MM.json`, `fonti_AAAA-MM.json`, costruiti dal worker con
  `fase15-elettricita/elettricita/carichi.py` (formato nel README della fase 15); si caricano solo i mesi del periodo.
  Fuori dal repository (`.gitignore`) e **non scaricabili** (decisione di Paolo): nessun CSV né JSON da scaricare.
  Senza `indice.json` (o senza mesi) la pagina dice che i dati non ci sono ancora e nasconde comandi, piccola mappa e
  sezioni (dal 21/11/2026: niente titoli di sezioni vuote, resta solo il messaggio).
- Fonti e licenze nel piè, sezione `metodo.html#carichi`, «Come leggere i grafici» in fondo alla pagina.
- Prove: `tests/test_carichi_browser.py` (Playwright, dati inventati dalla fase 15).

### Potenza per fonte, finestra comune e fonti spente (22/11/2026, richiesta di Paolo delle 09:42)

- **Grafico «Potenza per fonte»** (`#grafico-assoluti`, `cfgAssoluti()`) prima delle barre al 100 % (`#grafico-fonti`):
  stessa scomposizione e stessi colori (`indice.json`, `voci`), aree impilate in **MW medi** del quarto d'ora o dell'ora
  (una colonna per quarto d'ora, o per pixel con la **media** dei quarti d'ora coperti, `colonneFonti()`, comune ai due
  grafici; il saldo entra solo quando è positivo, come nelle barre al 100 %). Asse verticale da 0 al massimo della pila
  visibile. L'energia (**GWh**) di ogni fonte nella finestra visibile sta accanto alla sua casella (`scriviEnergie()`).
  La nota «Terna pubblica la produzione per fonte solo per tutta l'Italia» è passata in questa sezione e vale per i due.
- **Stessa vista**: i due grafici delle fonti stanno in un gruppo (`cfg.gruppo = st.finestra`, `grafico()`): rotella,
  trascinamento, dita, tasti `+ − 0`, doppio clic e riquadro grande in uno spostano anche l'altro. Col cambio di zona o
  di passo la finestra resta; col cambio di periodo torna a tutto il periodo.
- **Pulsanti** sopra il grafico (`#carichi-finestre`, `.filtro` con `aria-pressed`): «Ieri», «Ultima settimana»,
  «Ultimo mese», «Ultimi 3 mesi», «Ultimo anno» contano all'indietro dall'**ultimo giorno con i dati di tutte le
  fonti** nel periodo (`ultimoGiornoFonti()`, `finestraDi()`: settimana = 7 giorni, mese = stesso giorno del mese prima
  + 1, tagliati all'inizio del periodo); «Tutto il periodo» torna alla vista intera. Acceso il pulsante della finestra
  di adesso (tolleranza un minuto).
- **Cursore «Sposta di un mese»** (`#carichi-scorri`, input range): con la finestra più corta del periodo, ogni scatto la
  porta un mese avanti o indietro **con la stessa larghezza** (`posizioni()`: finestre che finiscono alla fine del
  periodo e poi un mese prima a ogni scatto, l'ultima che comincia all'inizio del periodo). Con tutto il periodo è
  spento. Frecce, Pagina su/giù, Inizio e Fine come ogni input range; `aria-valuetext` e `<output>` con la finestra.
- **Caselle per fonte** sotto il grafico in MW (anche nel riquadro grande; tutte le copie restano allineate,
  `accendiFonti()`), «Accendi tutte», «Spegni tutte». Il grafico in MW si ridisegna con le sole fonti accese («Nessuna
  fonte accesa» se sono tutte spente); in quello al 100 % le spente restano al loro posto col **colore dello sfondo**
  (`fill: var(--sfondo-grafico, var(--carta))`, `--sfondo-grafico: var(--foglio)` nel riquadro grande) e sono barrate
  nella legenda. Riquadretto: «(spenta)» accanto alla fonte, «fonti accese, in tutto».
- **Indirizzo e collegamento**: `finestra=AAAA-MM-GG_AAAA-MM-GG` (giorni interi, fine compresa) oppure con l'ora,
  `AAAA-MM-GGTHHMM` (istante esatto, ora italiana, dopo zoom e trascinamento), e `spente=termo,saldo` (identificativi
  di `voci`, ignorati quelli che non ci sono). I predefiniti (tutto il periodo, tutte accese) non si scrivono. Scritti
  300 ms dopo l'ultimo cambio (`scriviPresto()`, poi `EUGENIO_COLLEGAMENTO.aggiorna()`).
- Correzioni: «Tutta Italia» davvero nascosto quando la zona è l'Italia (`.carichi-zona .bottone[hidden]`); tacche
  dell'asse dei tempi ogni 64 px (prima 80), così una settimana a 375 px ha le date.
- Prove: `test_carichi_browser.py::test_potenza_per_fonte_e_finestra`, `::test_fonti_spente` (colore dello sfondo nel
  tema scuro, nel chiaro e nel riquadro), `::test_telefono_fonti`; `test_collegamento_browser.py::test_carichi_finestra_e_fonti`.

### Due metà, zona a discesa, anni, Italia = somma delle zone, dati mancanti (22/11/2026 b, richiesta di Paolo delle 09:54)

- **Due metà** sotto il titolo e l'avviso: `div.strumento.carichi-meta[data-divisore]` con `section.carichi-lato`
  `data-lato="0"` (`data-divisore-sinistra`, identificativi di sempre) e `data-lato="1"` (`data-divisore-destra`). La
  destra la riempie `copiaMeta()` copiando la sinistra e aggiungendo «-2» a `id`, `for`, `aria-labelledby`,
  `aria-describedby`, `aria-controls`. `divisore.js` ora accetta anche `.strumento[data-divisore]` dentro la pagina con le
  due metà segnate da `data-divisore-sinistra` / `data-divisore-destra` (stesso comportamento: trascinamento, frecce,
  doppio clic, larghezza ricordata). Dagli 861 px ogni metà è alta quanto la finestra sotto la testata e scorre da sola
  (la barra della sinistra a sinistra, `direction: rtl`); col telefono una sotto l'altra. Il JavaScript ha lo stato di
  ogni metà in `creaLato(k)` (zona, periodo, passo, grafici, finestra, fonti spente) e i dati comuni in `D` (indice,
  mesi, file letti una volta sola per le due metà). `window.EUGENIO_CARICHI.stato` è la metà sinistra, `.destra` la destra.
- **Zona**: casella a discesa `#carichi-zona` (e `-2`) con «Italia (tutte le zone)» e le sette zone, al posto di «Zona
  Italia / Tutta Italia». La **piccola mappa** resta una sola, sopra: il clic su una zona la sceglie in **tutte e due**
  le metà; se è già in tutte e due, torna all'Italia. Evidenza (`evidenzia()`): le zone non scelte più chiare, zona della
  sinistra `.meta-sx` (bordo pieno scuro, spesso), della destra `.meta-dx` (bordo tratteggiato color primario), la stessa
  in tutte e due `.meta-tutte` (bordo pieno color primario); spiegazione in `#minimappa-legenda` sotto la mappa
  («Sinistra: Nord», «Destra: Sicilia» o «Tutte e due le metà: …»).
- **Anni e archivio**: menu `#carichi-anno` (anni dell'archivio) e «‹ ›» (`#anno-prima`, `#anno-dopo`: anno precedente e
  successivo; con un periodo che non è un anno intero «‹» va all'anno prima di quello della data finale e «›» a
  quello della data finale) che scrivono Dal/al (anno tagliato ai limiti dell'archivio). Pulsanti della finestra e
  cursore «Sposta di un mese» ora vanno su **tutto l'archivio** (`posizioni()` dalla fine dell'archivio indietro di un
  mese per scatto, `finestraDi()` dall'ultimo giorno con le fonti dell'archivio): se la finestra esce dal periodo Dal/al
  (`vaiA()`), il periodo si sposta con la stessa lunghezza in giorni (più lungo se la finestra non ci sta), si ricalcola
  e la finestra si rimette dopo il calcolo. Con tutto il periodo visibile il cursore sposta il periodo intero, un mese a
  scatto.
- **Italia = somma delle zone** (fase 15, `carichi.py`): l'Italia scritta è la somma degli interi delle zone, quarto
  d'ora per quarto d'ora (dove manca una zona resta «Italy» di Terna); `scarto_italia_mw` nell'indice di ogni mese.
  Scarto misurato su nov 2025 – nov 2026 tra «Italy» e la somma: 7·10⁻¹² MW (cioè nessuno); 1–3 MW solo per gli
  arrotondamenti delle singole zone, ora spariti. La produzione per fonte è solo nazionale.
- **Dati mancanti**: `scriviMancanti()` elenca sotto lo stato di ogni metà (`#carichi-mancanti`, nascosto se non ce ne
  sono) i tratti senza potenza richiesta della zona e senza produzione per fonte; `tratteggia()` disegna nei due grafici
  delle fonti un rettangolo tratteggiato (`rect.carichi-mancanti-area`, motivo SVG) con «dati mancanti» se è largo almeno
  96 px; il riquadretto lo dice. Il worker riprova i giorni mancanti (fase 4, § «Dati di Terna», «Giorni mancanti»).
- Prove: `test_carichi_browser.py::test_due_meta_zone_e_mappa`, `::test_anni_e_archivio`, `::test_dati_mancanti` (dati
  scritti a mano: dicembre 2025 e gennaio 2026 col buco del 14–15 gennaio); `test_collegamento_browser.py::test_carichi_due_meta`;
  fase 15 `test_carichi.py::test_italia_somma_delle_zone`; fase 4 `test_terna.py::test_giorni_mancanti_*`.

### «Riallinea le due metà» ed energia rinnovabile (22/11/2026 c, richiesta di Paolo delle 10:20)

- Pulsante **«Riallinea le due metà»** (`#carichi-riallinea`, sotto la legenda della piccola mappa, in alto e comune):
  `riallinea()` prende il pezzo della metà sinistra (scelte o sezione `.carichi-sezione`) che è in cima alla sua area
  visibile e fa scorrere la metà destra fino allo stesso pezzo, alla stessa distanza dal bordo (`scrollBy` istantaneo),
  anche se sopra i grafici le due metà sono alte in modo diverso (nota delle zone, dati mancanti…). Col telefono (una
  metà sotto l'altra) la pagina salta dal pezzo in alto allo stesso pezzo dell'altra metà (dalla sinistra alla destra e
  viceversa). Annuncio per i lettori di schermo; si usa anche da tastiera (è un pulsante). Corretto anche il telefono:
  sotto gli 861 px le due metà sono davvero una sotto l'altra (`.strumento.carichi-meta { display: block }`; prima
  restavano due colonne strette).
- **Sesto riquadro** di «Valori del periodo» (al posto di «Produzione rinnovabile», che c'era solo per l'Italia):
  «Energia da fonti rinnovabili (Italia)» in GWh o TWh e, sotto, la quota sulla **produzione nazionale** (rinnovabili +
  termoelettrico negli stessi quarti d'ora) e quella sulla potenza richiesta dell'Italia. Rinnovabili: bioenergie,
  idroelettrico (come lo pubblica Terna nella produzione rinnovabile, pompaggi compresi: Terna non li separa),
  geotermico, eolico, fotovoltaico; esclusi termoelettrico tradizionale e saldo (estero, pompaggi, accumuli). Sempre
  dell'Italia, anche con una zona scelta (le fonti esistono solo per l'Italia), e per tutte le fonti: le caselle
  accese/spente non contano. Contano solo i quarti d'ora con tutte le fonti. Spiegazione in `#nota-rinnovabili` sotto i
  riquadri.
- Prove: `test_carichi_browser.py::test_riallinea` (due colonne, tastiera, telefono), `::test_energia_rinnovabile`
  (valore e quota ricalcolati dai file, uguali con una fonte spenta e con una zona).

## Segnalazioni di Paolo sulla v2026.11.21 (21–22/11/2026, nella versione 20261121b, pull request #17)

- **Elettricità, istogrammi più grandi**: in `elettricita.js` `INGRANDISCI = 1.4` ingrandisce la tela di tutti i
  disegni sulla mappa (barre di capacità, produzione, carichi, consumi; colonne del burden sharing): prima il doppio,
  ridotto del 30 % il 22/11 (00:59, Paolo: «troppo grandi»). Si disegna con le misure di prima e la tela ha
  `PR × INGRANDISCI` pixel per unità (gli anelli `ANELLI = 2`, con i raggi in pixel di `RAGGI`), quindi resta nitida (non è `icon-size`). Inquadratura con un **margine in
  alto** pari alle colonne più alte (`margini()`, al più il 40 % della mappa), così la Lombardia non esce dal bordo.
- **Anelli delle emissioni più piccoli** (22/11, 00:18): raggio sulla mappa da 8 a 21 px per le regioni e da 7 a 20 per
  le province (`RAGGI`, in pixel sulla mappa, indipendenti da `INGRANDISCI`); nella vista dell'Italia scala con lo zoom dell'inquadratura
  (`scalaAnelli()`, riferimento zoom 4,5 per una mappa di 800 × 640 px, mai sopra 1, mai sotto 0,5), così non si
  sovrappongono neppure con la mappa piccola. Il fattore medio nel buco solo se il buco è largo almeno 18 px (altrimenti
  è nel riquadretto). Controllo: `EUGENIO_ELETTRICITA.cerchi()` (centri e raggi in pixel) nelle prove.
- **Burden sharing verticale** (00:05 del 22/11): come gli altri istogrammi, ancorato in basso sul punto della regione:
  colonna delle rinnovabili in più dal 2020 impilata per fonte (**solo le parti positive**: i negativi, per esempio le
  bioenergie dismesse, stanno solo nel riquadretto) e **linea di base** (lo zero). Il rettangolo **arancione vuoto**
  (`#f08a24`) alto quanto l'obiettivo 2030 della Tabella A e la linea nera dell'obiettivo dell'anno scelto sono
  un'immagine a parte (`el-RR-ob`, stessa misura) nello strato `el-obiettivi`, filtrato sul codice della regione **sotto
  il mouse** (00:18 del 22/11; `mostraObiettivo()`, `stato.obiettivoSu`); col dito il primo tocco mostra l'obiettivo e
  il riquadretto, il secondo apre le province (tipo del puntatore letto da `pointerdown`/`pointermove`, perché dopo un
  tocco il browser manda anche mousemove e click di compatibilità). Scala comune che comprende gli obiettivi 2030: quando
  il rettangolo compare la colonna non cambia. Province: solo la colonna (non hanno obiettivi).
- **Riquadretto dell'obiettivo**: sulla mappa (tutta l'immagine del simbolo, quindi anche la parte vuota del rettangolo)
  le prime righe sono «Obiettivo 2030», «Raggiunto: x % (y MW in più dal 2020)» e «Mancano: z MW» (0 se raggiunto);
  per una provincia sono quelli della sua regione (`verso2030()`). Le stesse righe nel riquadretto del grafico «anno per
  anno» (anche sul riquadro arancione dell'anno scelto) e la colonna «Mancano al 2030 (MW)» nella tabella. Unità: MW,
  come nel resto della pagina.
- **Carichi elettrici**: «Quarti d'ora» acceso già nell'HTML; all'apertura le caselle Dal/al hanno gli ultimi 12 mesi
  che finiscono all'ultimo giorno con i dati; il passo predefinito non va nell'indirizzo; senza dati solo il messaggio.
- **Novità**: sotto il titolo di ogni voce, in piccolo, «21/11/2026 · versione 20261121b» (`p.novita-versione`,
  `costruisci_pagine.py`). Cambia la decisione dell'08/11/2026 solo per la pagina: le ancore e il feed restano senza
  versione (richiesta di Paolo: la procedura di pubblicazione dice di controllare la versione nelle Novità).
- Prove: `test_elettricita_browser.py::test_istogrammi_ingranditi` (misure × 1,4; anelli senza sovrapposizioni),
  `::test_burden_suggerimento_obiettivo` (rettangolo solo sulla regione sotto il mouse), `::test_burden_tocco`;
  `test_carichi_browser.py` (predefiniti, `passo=15` dei collegamenti vecchi, senza dati);
  `test_collegamento_browser.py::test_carichi_predefiniti`; `test_costruisci_pagine.py::test_novita_versione_feed_e_menu`.

## Produzione e consumi di elettricità: periodo a due indicatori (22/11/2026, 02:08, richiesta di Paolo; versione 20261122a)

- **Componente comune** `sito/cursore_periodo.js` (`window.EUGENIO_PERIODO.crea({inizio, fine, doppio, min, max, etichetta,
  testo, cambia})` → `imposta(anni, a, b)`, `scrivi()`): i due `input type=range` sovrapposti in `.cursore-doppio` di
  «Suolo e aree agricole» (stile in `stile.css`), con la spinta dell'altro indicatore (inizio ≤ fine), `--da`/`--a`,
  `aria-valuetext` e l'etichetta del periodo. Lo usano `suolo.js` (che prima aveva il codice dentro) ed `elettricita.js`;
  nelle due pagine `cursore_periodo.js` si carica subito prima dello script della pagina. Tastiera: quella degli input
  range (frecce, Pagina su/giù, Inizio, Fine).
- **`elettricita.js`**: `st.inizio`, `st.fine` (e `st.anno` = anno finale, per gli obiettivi del burden sharing); all'apertura
  tutti e due sull'ultimo anno; cambiando grandezza il periodo resta, avvicinato agli anni della grandezza (`imposta`).
  **Flussi** (produzione, carichi, consumi, emissioni: `flusso()`) = somma degli anni del periodo (`valoriP`); **fattori**
  delle emissioni = rapporto delle somme (`indicatoriP`: CO₂/produzione lorda, CO₂/termoelettrico, tep/termoelettrico/1000;
  con un anno solo i valori del costruttore così come sono); nei riquadri ISPRA come media dei fattori annuali pesata sulla
  produzione lorda (sul termoelettrico per i fattori del termoelettrico), solo se ISPRA ha tutti gli anni. **Stati**
  (capacità, burden sharing) all'anno finale con la variazione dall'iniziale nel riquadretto (per fonte e totale), nella
  tabella (in piccolo sotto ogni valore, classe `small.variazione`, e colonna «Variazione del totale dal …» o «Variazione dal
  …» del burden sharing), nel suggerimento del grafico per provincia e, sull'istogramma, **trattino nero** al valore iniziale
  (per barra; per il burden sharing all'altezza della colonna). Scala degli istogrammi e degli anelli: anni singoli e, con
  un periodo, anche le somme del periodo. Grafico a destra: riquadro `rect.periodo-scelto` dal primo all'ultimo anno del
  periodo (colorato appena con un periodo), anni iniziale e finale in grassetto.
- **Collegamento**: `inizio` e `fine` (sempre tutti e due); `anno=AAAA` dei collegamenti di prima vale come `inizio=fine=AAAA`
  e sparisce dall'indirizzo riscritto.
- Prove: `test_elettricita_browser.py::test_periodo` (apertura sull'ultimo anno, Inizio/Fine da tastiera, variazioni e
  trattino nella legenda della capacità, riquadro del grafico, somma della produzione nella tabella, fattore medio
  dell'Italia come rapporto delle somme, collegamento), `test_collegamento_browser.py::test_elettricita` (periodo nel
  collegamento e `anno=` vecchio), `test_suolo_browser.py` (componente comune).

## Produzione e consumi di elettricità: grandezza «Emissioni» (21/11/2026, richiesta di Paolo; pubblicata con la versione 20261122a)

Pubblicata nella release `v2026.11.22` (voce delle novità del 22/11, versione 20261122a, che comprende quella del 21/11 b mai pubblicata; procedura in `AGGIORNAMENTO_2026-11-22.md`).
- **Selettore**: pulsante «Emissioni» (`data-modo="emissioni"`, `?modo=emissioni` nell'indirizzo e nel collegamento
  salvabile). Si nasconde se `italia.json` non ha la parte `emissioni` (file costruiti prima del 21/11/2026). Anni: quelli
  di GrossVsCO2Emissions con la produzione (2000–2025).
- **Mappa**: in ogni regione (o provincia della regione scelta) un **anello** con la produzione lorda per fonte, colori di
  `VOCI["produzione"]`, disegnato su canvas e aggiunto con `addImage` allo strato di simboli `el-barre` (finisce
  nell'immagine scaricata). Area = area minima + parte proporzionale alla produzione (raggio
  `sqrt(r0² + (r1² − r0²)·P/Pmax)`, dal 22/11/2026 r0–r1 8–21 px per le regioni e 7–20 per le province (vedi sopra); Pmax su tutte le unità e tutti gli
  anni): proporzionale alla produzione, ma le regioni piccole restano leggibili. Nel buco il fattore medio della regione;
  per le province nessun testo (i fattori sono solo regionali).
- **Pannello**: tre riquadri `.cifra` (`#riquadri-emissioni`, `data-cifra` tep/medio/termo) con i valori nazionali
  dell'anno, il confronto con MEF/MASE 0,187 tep/MWh e con ISPRA (fattore della produzione lorda, dei consumi, del
  termoelettrico con e senza bioenergie, consumo di energia del parco termoelettrico) e lo scarto percentuale; con una
  regione scelta anche il valore della regione. Grafico «anno per anno»: le tre serie (Italia o regione) con la linea
  tratteggiata MEF e i cerchi vuoti ISPRA (solo Italia). Tabella: regioni raggruppate per zona di mercato con la riga di
  zona (`tr.riga-zona`, `data-zona`; per Calabria, Sicilia e Sardegna una sola riga «regione e zona»), totale Italia nel
  piede, riga della regione scelta `tr.scelta`.
- **Numeri**: tutti con `EUGENIO_NUMERI.formato`; l'asse verticale dei grafici della pagina ora mette i decimali quando
  il passo è sotto 1. Indicatori e riferimenti vengono da `italia.json` (fase 15, `indicatori()` e
  `riferimenti_emissioni.json`): nel JavaScript non ci sono valori di riferimento scritti a mano.
- Metodo in `metodo.html#elettricita-emissioni`; prove in `tests/test_elettricita_browser.py::test_emissioni` e
  `test_emissioni_telefono`.

## Comunità energetiche: confini delle aree delle sedi a qualsiasi zoom (20/11/2026, 14:08, `?v=20261120d`, richiesta di Paolo)

«Le aree delle cabine primarie una volta che si sceglie un punto si devono vedere a qualsiasi zoom, inoltre va evidenziata
quella su cui si trova il mouse come era nella versione precedente.» Come in Cabine primarie: per ogni sede con un'area del
GSE, `confiniSede()` chiede i codici delle confinanti (`R.gse.areeVicine`, una volta per area) e i poligoni semplificati
(`R.gse.aree`, `where=COD_AC IN (…)`); `ricomponiConfini()` li somma fra le sedi nella sorgente `cer-confini`
(`promoteId: COD_AC`): bordo spesso l'area di una sede, sottile le confinanti, **nessuno zoom minimo** e nessuna casella;
togliendo le sedi spariscono. Area sotto il mouse in azzurro chiaro (`feature-state` «sopra», `#bfe3ff`, opacità 0,38) sia
nei confini delle sedi sia nello strato «Aree convenzionali (GSE)» della casella (che resta da zoom 10). Al più 600 aree a
video; mai nelle immagini né nei file. Prova: `test_confini_delle_sedi_a_ogni_zoom_e_area_sotto_il_mouse`.

## Comunità energetiche con la struttura delle altre pagine (20/11/2026, 08:49, `?v=20261120c`, richiesta di Paolo)

Segnalazione: «la pagina si è scombinata» (era un articolo a colonna unica con la mappa in mezzo). Ora segue le regole
generali delle pagine con mappa (come Cabine primarie, Ortofoto, Modelli 3D):

- `main.strumento.pagina-cer` con **due metà e barre di scorrimento distinte**: a sinistra (`.mappa-area`, colonna `sticky`
  che scorre da sola, barra a sinistra) titolo, minimappa, **mappa con l'ortofoto** (`.mappa-dettaglio`, `min(72vh, 720px)`)
  e i **comandi**: «Sposta» / «Aggiungi sedi» (ogni clic aggiunge una sede), «Togli tutte le sedi», menu dell'ortofoto
  (fonte scelta da sola nel punto, contesto Sentinel-2, anni AGEA nella citazione), **caselle dei livelli** (aree
  convenzionali del GSE, particelle catastali, contorni degli edifici: `strati_gl.js`), **righello** (`righello.js`),
  frecce per spostare l'ortofoto (`sposta_ortofoto.js`), legenda, attribuzioni, immagine e fonti nel piè della colonna;
  a destra (`.pannello`) avviso sperimentale, **istruzioni ed esiti**: ricerca (indirizzo, foglio e particella, comune:
  `cerca_luogo.js`), sede con le coordinate, elenco, tabella delle sedi con cabina e menu del comune, dati orari, energia
  condivisa, scarica, come si calcola, stesso gruppo.
- Il modo di prova (`?prova=1`) mette il suo avviso nel pannello (prima in testa a `main`, che spostava le colonne).
- Prove: `test_cer_browser.py` (la mappa si porta in vista prima del clic: la colonna di sinistra scorre da sola; niente
  scorrimento orizzontale a 375 px).

## Comunità energetiche: aree convenzionali del GSE dal vivo (20/11/2026, `?v=20261120b`)

Pagina `edificio-cer.html` (resta **in lavorazione** nel menu), nuovo `cer_sedi.js`; riferimento tecnico
`documenti/CABINE_PRIMARIE_GSE_SERVIZIO_2026-11-17.md` (punti A-D). Principio: il browser chiede al GSE solo ciò che serve,
lo mostra e lo dimentica (nessun proxy, nessun file, nessun localStorage; cache in memoria finché la pagina è aperta) e
solo su azione dell'utente (sede aggiunta o strato acceso).

- **Passo 1, sedi**: una sede a mano (nome, latitudine, longitudine) o un elenco CSV/Excel/ODS (`sede`, `lat`, `lon`,
  facoltativi `cabina` e `istat`; al massimo 200). Per ogni sede con coordinate `R.gse.areeAccanto` (rete.js) chiede lo
  strato 0 del GSE con `distance=50` m e senza geometria; se tornano più aree, una seconda richiesta senza margine dice
  quale contiene il punto. Il COD_AC **precompila** il campo «Cabina» (modificabile) con la nota «proposta dalla mappa del
  GSE dalle coordinate; in caso di dubbio vale la ricerca per POD…»; confine (< 50 m, due aree): tutte e due con avviso;
  nessuna area (isola minore, SDC, mare): avviso. Elenchi: al massimo 4 richieste al GSE alla volta (`GSE.INSIEME`); una
  cabina presa dal file non viene sostituita.
- **Menu delle cabine del comune**: comune dai confini ISTAT del sito (`C.comuneNelPunto`), cabine da
  `GET /api/rete/cabine/comune/<istat>` (rotta esistente, una richiesta per comune): nome, COD_AC del raccordo, saturazione;
  la scelta riempie il campo. `R.statoComune`: comune di un altro distributore → avviso e rimando alla mappa del GSE;
  `servitoed = 0` con trasformatori di e-distribuzione → «servito in parte da un altro distributore» (mai «non
  concessionario», regola in vigore).
- **Mappa** (confini ISTAT, sedi, cabine dei comuni delle sedi col colore della saturazione) con la casella **«Aree
  convenzionali (GSE)»**, spenta all'apertura: da zoom 10 (sotto: «avvicinati…»), ~400 ms dopo la fine di ogni
  spostamento una richiesta per il riquadro visibile (`R.gse.areeNelRiquadro`: riquadro allargato alla griglia delle
  tessere dello zoom, così i piccoli spostamenti ritrovano la risposta in memoria; `maxAllowableOffset` ≈ un pixel; con
  `exceededTransferLimit` un avviso, niente paginazione), contorni con l'etichetta COD_AC (segnaposto HTML: le mappe del
  sito non hanno font), al clic codice, gestore, data di consegna e collegamento alla mappa del GSE; attribuzione fissa
  sotto la mappa quando è acceso. Immagini scaricate (JPG/PNG/PDF): strato ed etichette spenti, riaccesi dopo.
- **Energia condivisa**: la colonna `cabina` del file orario è ora facoltativa; per le sedi dell'elenco (stesso nome) vale
  il campo «Cabina»; ricalcolo a ogni modifica (evento `eugenio:cer-sedi`).
- **File** CSV, Excel, ODS, PDF (`R.pulsantiDati` con il nuovo parametro dei formati): sedi con il solo codice della
  cabina e la nota «area convenzionale proposta dalla mappa del GSE; verifica ufficiale: GSE», più l'energia condivisa;
  mai i perimetri.
- **Indirizzo del servizio**: solo in `rete.js` (`GSE_FS`, `GSE.FEATURESERVER`, `GSE.SERVIZIO` = strato 0) e, lato server,
  in `servizio/rete.py` (`URL_GSE_AREE`, controllo mensile del worker); una prova della fase 4 controlla che coincidano.
- Prove: `tests/test_cer_browser.py` (GSE e `/api/rete/…` simulati: richieste, confine, mare, menu, regola del comune,
  4 alla volta, strato, riquadro al clic, immagine, file, telefono, `?prova=1`).

## Cabine primarie: apertura su tutta Italia e due metà scorrevoli (19/11/2026, 21:29, `?v=20261119e`, richiesta di Paolo)

- La mappa si apre su **tutta Italia** (`C.ITALIA`), mai sotto lo zoom 5 (da lì parte lo sfondo Sentinel-2): alla creazione
  il riquadro non ha ancora l'altezza finale, quindi dopo `load` `resize()` e `vediItalia()` (`cameraForBounds`, zoom ≥ 5;
  usata anche dal pulsante «Italia» della minimappa). Con `?lat=…&lon=…` si apre sul punto a zoom 16 come prima.
- Tornate le **due metà con la loro barra di scorrimento** come nelle altre pagine (colonna di sinistra `sticky` alta
  quanto la finestra con `overflow-y: auto`, pannello che scorre con la pagina): tolto `position: static; height: auto`
  della `v2026.11.19d`; al suo posto `.pagina-cabine .mappa-area > * { flex-shrink: 0 }` (come Ortofoto e Modelli 3D), così
  la mappa resta a `min(72vh, 720px)` e la colonna scorre.
- Prove: `test_cabine_confini_automatici_al_clic_prova` controlla zoom e riquadro d'apertura, colonna scorrevole e altezza
  della mappa.

## Cabine primarie con una sola mappa (19/11/2026 sera, `?v=20261119d`, richiesta di Paolo)

Segnalazione: «la pagina cabine primarie non funziona». La colonna di sinistra era alta quanto la finestra (`.mappa-area`
sticky): la mappa di dettaglio con l'ortofoto restava schiacciata in fondo e i comandi sotto (righello compreso) fuori vista.
- **Una sola mappa** (`#mappa-dettaglio`, con l'ortofoto): tolte la mappa grande di regioni e comuni (`#mappa-cabine`), le
  sue caselle degli strati, la sua immagine e il titolo «Dettaglio». In questa pagina la colonna di sinistra è alta quanto
  il contenuto (`.pagina-cabine .mappa-area { position: static; height: auto }`), mappa a `min(72vh, 720px)`.
- **Righello** in un posto suo sotto la mappa (`#posto-righello`), creato subito al caricamento della mappa (prima arrivava
  solo dopo confini e strati, anche 8 s).
- **Sotto la mappa a sinistra** i comandi dei punti (`#comandi-punti`): «Sposta» / «Scegli punti» (`#modo-sposta`,
  `#modo-scegli`, `aria-pressed`, `st.modo`), «Cancella tutti» (`#svuota-punti`: punti, confini e aree aggiunte) e il colore.
  Con «Sposta» il mouse trascina la mappa e il clic non mette punti (sceglie un punto o spunta una cabina dei punti); con
  «Scegli punti» ogni clic segna un punto nuovo, **a qualsiasi zoom** (tolto il limite dello zoom 13), cursore a croce
  (`.modo-scegli`). Tolto «Nuovo punto al centro del dettaglio».
- **Cabine di tutta Italia** sull'ortofoto: `/api/rete/cabine` (una richiesta, ~2.000 punti) nello strato `fv-tutte-punti`,
  colorate con la saturazione e grandi come nella rete (`RAGGIO_CABINE`); le cabine dei punti hanno un anello
  (`fv-cabine-punti`, spesso se spuntate). La tabella nazionale serve anche alle cabine dei punti (niente più richieste per
  regione).
- **Confini per ogni punto** (anche quelli dell'elenco): area del punto e confinanti come prima (`R.gse.areeVicine`, poi
  `R.gse.aree` con `where=COD_AC IN (…)`), ma **sommati** fra i punti: poligoni in memoria per `COD_AC` (`st.poligoni`),
  codici delle vicine chiesti una volta per area (`st.vicine`), «Aggiorna confini» aggiunge (`st.extra`); `ricomponiAree()`
  rifà lo strato (aree dei punti col bordo spesso). Al massimo 600 aree a video. Togliendo un punto spariscono le sue aree.
- **Area sotto il mouse** retinata di azzurro chiaro trasparente: sorgente `fv-aree` con `promoteId: "COD_AC"`,
  `feature-state` `sopra` (`st.sopra`).
- Niente più caselle degli strati: le aree del GSE si vedono quando ci sono (con l'attribuzione), sempre spente nelle
  immagini scaricate. La minimappa dell'Italia accanto al titolo porta la mappa sulla regione.
- Prove: `tests/test_prove_1911_browser.py::test_cabine_confini_automatici_al_clic_prova` (niente mappa in alto, comandi
  sotto la mappa, «Sposta» senza punti, «Scegli punti» a zoom 20,5, aree sommate, evidenza sotto il mouse, «Cancella
  tutti»), `tests/test_rete_browser.py` (confini anche per i punti dell'elenco). Provata anche con l'API e il GSE veri: la
  domanda `POST` delle confinanti al GSE funziona (8 aree a Cesena).

## Righello, 3D della vista e più edifici, ortofoto nella rete, confini automatici delle cabine (19/11/2026, `?v=20261119a`, richiesta di Paolo)

- **Righello** (`sito/righello.js`, nuovo, in tutte le pagine con l'ortofoto: Modelli 3D e le pagine 3D, Ortofoto, Edifici
  pubblici, Aggiungi edifici, Cabine primarie, Stato della rete elettrica). `EUGENIO_RIGHELLO.aggiungi(mappa,
  { dove })` mette un piccolo pulsante (icona del righello, `aria-pressed`) nell'elemento indicato – riga dei comandi sotto la
  mappa in Modelli 3D, caselle dei livelli in Cabine primarie e nella rete – o in una riga subito sotto la mappa (dopo la
  maniglia dell'altezza). Acceso: clic sinistro = punto; clic sul primo punto (con almeno 3 punti) = forma chiusa con l'area;
  un clic (o un tocco) su un punto lo prende – col mouse segue il puntatore – e il clic o tocco successivo lo posa (seconda
  richiesta del 19/11: niente trascinamento tenendo premuto, così va anche col dito; tocchi brevi gestiti da `touchend`, zoom
  col doppio clic/tocco sospeso mentre il righello è acceso); clic destro = annulla lo spostamento o azzera (dopo una
  rotazione col tasto destro i punti restano); Esc = annulla lo spostamento o spegne.
  Passando sopra la linea o dentro l'area, riquadretto con lunghezza o perimetro e area (mentre si disegna anche l'ultimo
  tratto fino al puntatore). Distanze orizzontali con la formula dell'emisenoverso (raggio medio 6.371.008,8 m), area nella
  proiezione cilindrica equivalente attorno alla latitudine media. Gli eventi del mouse si fermano sul contenitore della
  mappa (fase di cattura) prima di MapLibre: con il righello acceso la pagina non riceve i clic (niente scelta di edifici o di
  comuni, niente punti spostati); spostamento e zoom restano. Strati `righello-*` sempre in cima; riquadretti della pagina
  nascosti mentre è acceso.
- **Modelli 3D** (`edificio3d.js`): «Genera il 3D» senza edificio scelto fa il 3D della vista (da zoom 15; la scritta resta la stessa per tenere la riga sotto la mappa su una sola riga, lo dice il suggerimento del pulsante):
  `vista3d()` carica il contesto di 250 m attorno al centro (ripiego OSM, quote, tetti scelti, alberi), mette tutti i corpi
  tra i vicini, nasconde i pannelli dell'edificio ed entra nel 3D; gli edifici delle tessere sono tutti quelli sullo schermo.
  **Maiuscolo + clic** aggiunge o toglie un edificio: in 2D (`scegliLista2d`, `daGenerare.scelti`) e nella vista 3D (`clic`);
  `scegli()` accetta un elenco di codici, carica il contesto attorno a ciascuno (`stato.puntiScelti`), tiene i vicini entro
  250 m da uno qualsiasi e calcola corpi, superfici e indicatori (`E.indicatori`) sugli edifici scelti insieme. `stato.edifici`
  è l'elenco, `stato.edificio` il codice o «A + B». Lo zoom a riquadro di MapLibre (Maiuscolo + trascinamento) è spento.
  «Torna alla mappa 2D» chiama `esci3d()` senza argomenti e lascia attiva la scelta (prima l'evento del clic valeva «azzera»).
- **Stato della rete elettrica** (`rete_elettrica.js`, `rete.js`): casella «Ortofoto» (accesa): contesto Sentinel-2 sempre
  sotto e, sopra, la fonte migliore applicabile al centro (`/api/ortofoto/fonti` e `fontiNelPunto`, come in Cabine primarie),
  citazione sotto la mappa (con «si vede dallo zoom N») e nell'immagine scaricata (rifiutata con una fonte solo dal vivo).
  Cabine con lo stesso raggio delle interruzioni (`stratoCabine(m, id, { raggio, bordo })`).
- **Cabine primarie** (`fv_cabine.js`, `rete.js`): confini automatici. Un punto nuovo o spostato con un clic, la ricerca, il
  trascinamento e il clic su un punto chiedono `R.gse.areeVicine(lon, lat, area)` (codici dell'area e delle confinanti: il
  poligono dell'area con `where=COD_AC IN (…)`, poi una domanda `POST` con quel poligono, 30 m di margine e `returnGeometry=false`)
  e `R.gse.aree(codici)`; area del punto con il bordo spesso (`_centrale`), confinanti sottili; stesse regole di «Aggiorna
  confini» (dal browser, solo a video, spente nelle immagini). Non per i punti di un elenco finché non se ne sceglie uno.
- Prove: `tests/test_prove_1911_browser.py` (misure con valori noti, righello nella rete e in tutte le pagine con l'ortofoto,
  ortofoto e cabine della rete, confini automatici in prova e con il GSE simulato, vista 3D e più edifici in 2D e in 3D).

## Territorio › Edifici pubblici e retino in Modelli 3D (17/11/2026, `?v=20261117a`, richiesta di Paolo)

- **Menu**: il gruppo «Patrimonio» si chiama **«Territorio»** (solo l'etichetta: `data-gruppo="patrimonio"`, gli id e i
  file restano gli stessi; `costruisci_pagine.py` rimette l'etichetta sopra il titolo delle pagine). Nuova voce
  **«Edifici pubblici»** (sperimentale, «S») dopo Patrimonio.
- **`edifici-pubblici.html`** (`edifici_pubblici.js`, `main.strumento.pagina-ortofoto.pagina-pubblici`): mappa MapLibre con
  le tessere `/edifici3d/immobili_pa/immobili_pa_<anno>_<versione>.pmtiles` (nome scritto in `indice.json`, fase 7
  `immobili-pa-sito`): particelle con edifici retinate a righe oblique, terreni in verde, edifici e terreni insieme in viola,
  beni senza particella come punti arancio; da lontano un punto per particella, dallo zoom 13 i confini. Livelli: Edifici,
  Terreni, Beni senza particella, gruppi di enti (caselle, «Tutti», «Nessuno»; costruite da `indice.json` «gruppi»: dal
  22/11/2026 anche «Unioni di Comuni e Comunità montane», codice `I`, e Province e Università non più vuote), ortofoto con la fonte migliore della zona
  scelta da sola (`EUGENIO_CONFINI.fontiNelPunto`) o a mano, contesto Sentinel-2 sotto, strati comuni (`strati_gl.js`).
  Ricerca a parole nell'indice (`/api/immobili-pa/cerca`, filtro per gruppo) e per indirizzo o foglio e particella
  (`cerca_luogo.js`); clic su punto o particella → scheda (`/api/immobili-pa/particella/{ref}` o `/bene/{id}`) con
  «Apri in Modelli 3D», «Apri in Ortofoto» e (dal 22/11/2026) «Mostra tutti i beni di questo ente»; un bene senza particella
  mostra tutte le sue dichiarazioni (proprietario e chi lo ha in uso). Indirizzo: `?lat=&lon=&z=`, `?ref=`, `?bene=`.
  Immagine scaricabile con le attribuzioni (`esporta_mappa.js`).
- **Ricerca per ente** (22/11/2026, `pubblici_enti.js`; decisioni di Paolo e studio
  `documenti/EDIFICI_PUBBLICI_RICERCA_ENTE_2026-11-22.md`): nel passo 1 due schede (`role="tablist"`, frecce, Inizio e
  Fine) «Cerca un immobile» e **«Per ente»** (`?modo=enti`). Nella seconda:
  - menu **tipologia** (gruppi di `indice.json`) e **«con beni in»** (regioni dove l'ente ha beni);
  - **combobox ARIA** (`role="combobox"`, `aria-expanded`, `aria-activedescendant`, elenco `role="listbox"`; frecce, Invio,
    Esc) con l'autocompletamento **tutto nel browser** sull'elenco statico `enti_<anno>_<versione>.json` (indicato da
    `indice.json` → `enti`): ogni parola deve iniziare una parola del nome o della sede, sigle comuni (AUSL, ASL, ACER, ATER,
    IACP, «unibo») come sinonimi, prima il nome esatto («cesena» → Comune di Cesena prima di Cesenatico), poi i più grandi;
    proposte con nome leggibile (i nomi MEF sono in maiuscolo), tipologia, sede e beni (`EUGENIO_NUMERI.formato`);
  - **enti scelti** (al massimo 8) con il colore (tavolozza Okabe–Ito senza arancio e porpora: blu, vermiglione, verde
    acqua, giallo, celeste, nero, ocra, grigio-blu; un ente nuovo prende il primo colore libero), totali brevi, «Inquadra»,
    «×» e «Togli tutti»;
  - caselle **ruolo** («in proprietà» accesa, «in uso» = detenzione spenta) e **natura** (fabbricati accesi, terreni
    spenti), decisioni di Paolo del 22/11/2026; avvisi del § 5.5 dello studio (beni dichiarati, superfici, cedente non
    mostrato, Trentino-Alto Adige solo a pallini).
  - **Mappa**: per ogni ente una sorgente GeoJSON dai punti di `/api/immobili-pa/ente/{chiave}/punti` (filtrati nel browser
    per ruolo e natura, una feature per particella con `n` beni), pallini fino allo zoom delle particelle (13) con raggio
    che cresce con √n, raggruppati (`cluster`, senza numeri: la mappa non ha glifi) oltre 3.000 punti; dallo zoom 13 restano
    i pallini dei soli beni senza particella e compaiono i livelli dei contorni sulla sorgente `pa` delle tessere, filtrati
    con la proprietà `e` (`["in", ",<id>p,", ["get", "e"]]`); se una particella è di più enti scelti vale il colore del
    primo. I livelli
    normali si **attenuano** (opacità ~0,1) e la loro legenda si schiarisce; sotto la mappa la legenda degli enti.
    Clic e passaggio del mouse passano prima da `EUGENIO_PUBBLICI_ENTI.suClic/suMovimento` (nomi degli enti scelti nella
    particella; clic su un gruppo di pallini → zoom).
  - **Stili proprietà / uso / terreni** (22/11/2026 sera, richiesta di Paolo), sempre nel colore dell'ente:
    - **in proprietà**: colore pieno e acceso (pallino pieno con bordo bianco; particella piena, opacità 0,72, con
      contorno continuo: livelli `pa-enti-edifici`, `pa-enti-terreni`, `pa-enti-linea`);
    - **in uso** (detenzione): stesso colore trasparente (pallino ad anello, interno a opacità 0,22 e bordo nel colore;
      particella a opacità 0,22 con contorno tratteggiato: `pa-enti-uso-edifici`, `pa-enti-uso-terreni`,
      `pa-enti-uso-linea`, sotto quelli della proprietà, filtrati con `,<id>u,` e senza `,<id>p,` degli enti scelti);
    - **terreni**: righe oblique «\» chiare e scure nel colore dell'ente (immagini `terreno-ente-<n>` per il riempimento e
      `pallino-terreno-<n>-p|u` per i pallini, livelli `symbol` `pe-<chiave>-righe` e `-senza-righe` con `icon-size`
      proporzionale al raggio); **fabbricati senza righe** (il retino magenta resta il segno degli immobili pubblici nella
      vista normale).
    Un pallino o una particella con beni in proprietà e in uso prende lo stile della proprietà; con fabbricati e terreni
    quello dei fabbricati. La legenda sotto la mappa spiega i tre stili con campioni disegnati come sulla mappa (pallino e
    riquadro nel colore del primo ente, `campioneStile`); le righe dell'immagine scaricata li descrivono a parole e la mappa
    nell'immagine è la stessa.
  - **Scheda in sovraimpressione** (22/11/2026 sera): nella modalità per ente un clic su un pallino, una particella o una
    riga della tabella apre la scheda completa in un riquadro **sopra la mappa** (`#scheda-sopra`, `role="dialog"` non
    modale, in alto a sinistra: la posizione la scrive `edifici_pubblici.js` dal contenitore della mappa, lasciando liberi
    i pulsanti di zoom a destra e attribuzione, righello e livelli sotto), chiusa con **×**, **Esc** o un **clic fuori**
    (non con uno spostamento della mappa); sotto i 860 px è a **tutta larghezza in basso** (al massimo 62 % dell'altezza).
    Contiene tutti i campi pubblicabili restituiti da `/particella/{ref}` e `/bene/{id}`, per **ogni dichiarazione**
    (proprietario e chi lo ha in uso), con prima i beni degli enti scelti e il campione del loro colore e ruolo: ente,
    tipo, settore e macrocategoria, sede dell'ente, ruolo, titolo e quota, detenzione dell'intera unità, natura,
    indirizzo, comune con codice catastale, regione, identificativo e sistema catastale, superficie dichiarata e di
    riferimento, cubatura, pertinenze, epoca, canone, utilizzo e finalità, dati a terzi, vincolo, natura giuridica,
    compendio, punto del censimento con la sua fonte, aggancio, identificativo del bene. Mai soggetto cedente né codici
    fiscali. La stessa scheda resta anche nel passo «Scheda» del pannello; passando a «Cerca un immobile» il riquadro si
    chiude.
  - **Passo «Edifici degli enti selezionati»** (numeri dei passi rifatti): per ogni ente i totali (`/api/immobili-pa/ente/
    {chiavi}`, una richiesta per tutti) con superficie dichiarata dei fabbricati in m², dei terreni in ettari, percentuali
    con un decimale; con più enti la riga «Insieme» sui beni distinti. Elenco con `tabella_ordinabile.js` (una riga per
    particella con il numero di unità; colonne Comune, Regione solo se l'ente ha beni in più regioni, Indirizzo,
    Tipologia, Unità, Superficie dichiarata, Area del lotto, Epoca, Utilizzo, Titolo; le ultime quattro nascoste sotto i
    600 px): fino a 200 righe tutte insieme e ordinate nel browser, oltre si parte dai **comuni** (tabella ordinabile dei
    comuni, clic → particelle del comune) o, con un solo comune, dalle **pagine da 100 righe ordinate dal server**.
    L'ordinamento scelto vale per tutti gli enti e va nel collegamento. Clic (o Invio) su una riga → la mappa vola sulla
    particella, la riga e il contorno si evidenziano e si apre la scheda sopra la mappa (con Invio il fuoco va al
    riquadro e torna alla riga quando si chiude). Nessuna esportazione della tabella.
  - **Immagine** (`opzioniImmagine`): nella fascia sotto la mappa una riga per ente con il colore scritto («blu: Comune di
    Cesena (FC) – 2.718 beni, 551 particelle»), i filtri e la spiegazione dei segni.
  - Con un `indice.json` senza `enti` (dati preparati prima del 22/11/2026) la scheda dice che la ricerca per ente non è
    ancora disponibile; con l'indice vecchio le rotte rispondono `{"disponibile": false}`.
- **`tabella_ordinabile.js`**: componente riusabile delle tabelle ordinabili (regole in `sito/README_stile.md`, «Tabelle
  ordinabili»).
- **`retino.js`**: il motivo a righe oblique (magenta `#c2185b`) registrato come immagine MapLibre, uguale in tutte e due
  le pagine; `campione()` per le legende.
- **`pubblici_mappa.js`** (Modelli 3D): un edificio è pubblico se il punto interno di uno dei suoi corpi cade in una
  particella con edifici (t = E o M) delle tessere già caricate (`querySourceFeatures`, nessuna richiesta in più); gli
  edifici pubblici vanno nella sorgente `corpi-pubblici` e si disegnano con `fill-pattern` (2D, `pubblici-2d` e bordo) e
  `fill-extrusion-pattern` (3D, `pubblici-3d`), togliendoli con un filtro dalle estrusioni normali. Casella «Edifici
  pubblici (retinati…)» tra i livelli, accesa in partenza; voce di legenda col retino. Scelto un edificio pubblico, sotto il
  messaggio (`#nota-pubblico`) l'ente, le tipologie e il collegamento alla scheda. `?lat=&lon=` senza `edificio` apre la
  mappa 2D sul punto (collegamento da Edifici pubblici).
- Test: `test_costruisci_pagine.py` (gruppo «Territorio», voce nuova, 13 «S»), `test_esempi_contributi.py` (esempio
  della pagina), `test_mappe_browser.py` (pagina a due colonne), `test_pubblici_enti_browser.py` (22/11/2026: file e testi,
  schede, combobox da tastiera, colori, limite di 8, totali, ordinamento con `aria-sort`, ente grande per comune e
  pagine, clic su una riga, collegamento riaperto, 375 px, indice vecchio; rotte simulate).

## Rete elettrica (17/11/2026, richiesta di Paolo; contratto in CONTRATTO_RETE, sintesi qui)

- **Statistiche › Stato della rete elettrica** (`rete-elettrica.html`, `rete_elettrica.js`): mappa MapLibre della regione
  scelta (piccola mappa, `?regione=RR`; clic su un'altra regione = la sceglie senza spostare la vista), con quattro strati
  spegnibili e la loro legenda: criticità dei comuni (riempimento pieno o a strisce: regola `classeComune` in `rete.js`,
  uguale a quella del servizio; legenda «classificazione di EuGEnio dai dati mensili per trasformatore di
  e-distribuzione»; province senza dato a righe grigie), comuni con un altro distributore (retino), cabine primarie
  (punti grandi, livello peggiore: bianco = verde, giallo, arancione, rosso; grigio = altri gestori o senza dato; riquadretto
  con nome, codice e-distribuzione, `COD_AC`, gestore, trasformatori per livello, data) e interruzioni in corso (punti blu,
  rilette ogni 5 minuti). A destra date di aggiornamento (`/api/rete/stato`), avviso per le province senza dato e, scelto
  un comune (clic, casella con i nomi o `&comune=ISTAT`): criticità, cabine (`/api/rete/cabine/comune/<istat>`, ripiego sul
  campo `comuni_serviti`), interruzioni in corso, statistiche dal giorno d'inizio della raccolta con la durata stimata
  (`/api/rete/interruzioni/comune/<istat>`, grafico mensile con `grafici.js`); per un comune non concessionario il
  rimando alla mappa del GSE. Download: immagine (`esporta_mappa.js`, fonti nella fascia) e dati CSV (nel browser,
  citazione in riga 1) ed Excel/PDF (documento generico `POST /api/report`), con l'attribuzione ODbL delle posizioni.
- **Comuni serviti in parte da un altro distributore** (17/11/2026 sera, decisione di Paolo): i comuni segnati
  `servitoed = 0` ma con trasformatori e-distribuzione (35, soprattutto milanesi; `servito_in_parte: true` con
  `concessionario: true` in `/api/rete/comuni`) hanno il colore della criticità, niente retino, bordo tratteggiato (strato
  della criticità, voce di legenda) e la nota «servito in parte da un altro distributore» (`nota_servito_in_parte` di
  `/api/rete/stato`) nel riquadretto, nella scheda del comune e nei file (colonna «Servito in parte da un altro
  distributore»). Nei dati di prova un comune ogni 41 circa.
- **Fotovoltaico › Cabine primarie** (`fv-cabine.html`, `fv_cabine.js`): dal 19/11/2026 sera **una sola mappa** con
  ortofoto (fonte automatica nel punto o scelta dal menu, contesto Sentinel-2), particelle ed edifici (`strati_gl.js`),
  frecce dell'ortofoto (`sposta_ortofoto.js`), righello, cabine di tutta Italia colorate con la saturazione e i punti; sotto,
  a sinistra, «Sposta» / «Scegli punti», «Cancella tutti» e il colore (sezione sopra). Il punto scelto si trascina. A destra
  ricerca (`cerca_luogo.js`), elenco nel formato di Patrimonio (max 200 righe; con `lat`/`lon` restano nel browser, le
  altre a `POST /api/patrimonio` a blocchi di 40), punti con colore dal menu come quello degli edifici di Modelli 3D
  (`localStorage` `eugenio-colore-punti-cabine`). Per ogni punto: area GSE (`COD_AC`, richiesta dal browser senza
  geometria, al massimo 4 insieme) → cabina da `/api/rete/cabine`, più le cabine e-distribuzione del comune, e i confini
  dell'area e delle confinanti (sommati fra i punti). «Aggiorna confini» (cabine spuntate, max 100): poligoni dal GSE con
  `where=COD_AC IN (…)`, `maxAllowableOffset=0.0002`, solo a video con l'attribuzione del GSE, spenti nelle immagini
  scaricate (`opz.dopo` di `esporta_mappa.js` li riaccende). «Scarica i confini delle aree (GSE, CC BY-NC-SA)»: GeoJSON del
  contratto fatto nel browser. Dati CSV, Excel, PDF con i soli codici. `?lat=…&lon=…` aggiunge un punto all'apertura.
- **Servizio del GSE**: indirizzo solo in `rete.js` (`GSE.SERVIZIO`, test); CORS aperto (`Access-Control-Allow-Origin: *`).
  Il Caddyfile non ha `connect-src` (CSP solo `frame-ancestors`): nessuna modifica necessaria.
- **Modo di prova** `?prova=1`: dati sintetici generati in `rete.js` dai confini ISTAT del sito (cabine ogni 7 comuni,
  Torino senza dato, aree GSE inventate), con l'avviso in pagina e nei file; nessuna richiesta al server né al GSE.
- Test: `tests/test_rete_browser.py` (menu, file, regola della criticità, le due pagine in Chromium con dati sintetici e
  con API e GSE simulati, GeoJSON separato, telefono).

## Ortofoto AGEA 2022-2024 con l'anno vero nella citazione (17/11/2026, segnalazione di Paolo)

- Nuova fonte nazionale `agea` (fase 4 e `fase10-edifici3d/ortofoto/italia.toml`): ortofoto AGEA RGB 20 cm, CC BY 4.0,
  per ogni tessera il volo più recente (2022, 2023 o 2024), con copia sul server; scelta da sola dove non c'è un'ortofoto
  regionale più recente o dello stesso anno (Emilia-Romagna, Toscana, Bolzano). Prima fuori da queste regioni c'era solo
  AGEA 2012 del Geoportale Nazionale, lenta e spesso «non risponde o è occupata»; ora resta come ripiego da scegliere a mano.
- **Anno nella citazione**: `protezione.js` (già in tutte le pagine, avvolge `fetch`) legge `X-Ortofoto-Anno` delle tessere
  e lo ricorda per fonte e tessera (`window.EUGENIO_ORTOFOTO_ANNI`: `citazione(f, mappa)`, `anniDellaVista`,
  `anniNelRiquadro`, `testoAnni`, `segui(mappa, sorgente, fn)`). Le fonti con `anni` e `citazione_anni` hanno la citazione
  con gli anni delle tessere dentro la vista, allo zoom in uso («ortofoto RGB 2023», «2022 e 2023» sul confine); senza
  tessere note quella generica «2022-2024». Usata sotto la mappa (si aggiorna all'arrivo delle tessere e a ogni
  spostamento: l'evento «idle» di MapLibre non arriva sempre), nelle immagini scaricate e nella figura dei report di
  Modelli 3D (`ortofoto.js`, `edificio3d.js`, `fv_cabine.js`, `importa_modello.js`, `aggiungi_dbtr.js`).
- Testi: `ortofoto.html` (fonti nel piede e «Licenze e regole»), `sitografia.html` (Geoportale AGEA), voce «Migliorato»
  del 17/11 in `novita.toml`, `EUGENIO_PER_AGENTI.md`, `llms.txt`. Versione del sito invariata.
- Test: `tests/test_ortofoto_agea_browser.py` (Milano → AGEA con «2024» sotto la mappa e nel PDF; confine con «2022 e
  2023»; in Emilia-Romagna resta la RER davanti ad AGEA).

## Ricerca di un luogo: particella del civico e metà della via (17/11/2026, segnalazione di Paolo; versione da fissare alla pubblicazione)

- **Problema**: cercando un indirizzo in Ortofoto e Modelli 3D la mappa andava sul punto della riga a zoom 17: con il civico
  sull'accesso ANNCSU (Rimini, viale Settembrini 2: l'ospedale Infermi restava fuori dalla vista), senza civico su un civico
  qualsiasi della via (Rimini, via Coriano, 8,7 km), con una via che non esiste lontano senza avviso (Perugia, «via
  Sant'Andrea delle Fratte», frazione).
- **`cerca_luogo.js`**: la richiesta porta `luogo=1`; il server aggiunge alla riga segnaposto e riquadro (fase 4, § «Ricerca
  di un luogo»). Civico (o foglio e particella) → segnaposto in un punto interno della **particella catastale** (Agenzia delle
  Entrate – Cartografia catastale, CC BY 4.0) e particella **tutta nella vista** (zoom al più `ZOOM_PARTICELLA` = 19); con
  più accessi dello stesso civico, la particella più grande fra le loro (scelta B di Paolo: l'ospedale di viale
  Settembrini 2), scritto nel messaggio. Sola via → mappa **centrata a metà della via**, zoom che la fa vedere tutta (o, se la
  metà è molto fuori centro, buona parte: non oltre un livello sotto quello del riquadro). Più vie compatibili o via non
  riconosciuta → **elenco di pulsanti** nella riga dei messaggi (vie e località di OpenStreetMap e dell'ANNCSU, più il punto
  trovato da Zornade), la mappa resta ferma finché non si sceglie; con una via riconosciuta le altre simili sono pulsanti
  «Altre vie simili». Località scelta: zoom `ZOOM_LOCALITA` (15). Avviso discreto (`.cerca-avviso`) se una fonte non risponde.
  Il messaggio cita le fonti (ANNCSU o Zornade con il collegamento; particella: Agenzia delle Entrate; via: OpenStreetMap).
- **Interfaccia compatibile**: `crea`, `cerca`, `ZOOM` come prima; nuovi `inquadra(mappa, lon, lat, riga, extra)` (usata da
  `ortofoto.js` ed `edificio3d.js` al posto di `flyTo`), `ZOOM_PARTICELLA`, `ZOOM_LOCALITA`; la riga passata a `suTrovato` ha in
  più `riquadro`, `luogo_tipo` e `fonte_testo` (attribuzione completa, usata per il punto in Modelli 3D e per le immagini e i
  report di Ortofoto). Risposta senza i campi nuovi (server di prima, `LUOGO=false`): tutto come prima. `cerca(campi,
  suScelta)`: con l'elenco restituisce `{ scelta, riga }` senza punto.
- `stile.css`: `.cerca-corpo`, `.cerca-scelte`, `.cerca-avviso` dentro `.cerca-edificio`. `metodo.html` (fonti) e
  `privacy.html` (fornitori: WFS catastale dell'Agenzia, cosa riceve Overpass) citano le fonti nuove.
- **Da fare alla pubblicazione**: nuova versione (`python costruisci_pagine.py --versione …`, la voce del 17/11/2026 di
  `novita.toml` porta `20261117`, da allineare): finché la versione non cambia `test_novita_versione_feed_e_menu` fallisce e
  i browser tengono il vecchio `cerca_luogo.js`.
- Test: `tests/test_ricerca_luogo_browser.py` (Ortofoto: ospedale nella vista, via Coriano centrata a metà e tutta visibile,
  scelta di una via simile senza richiamare il server; Modelli 3D: elenco di Perugia e mappa ferma, località scelta; risposta
  senza campi nuovi = zoom 17 come prima).

## Esempi e Contributi (15/11/2026, richiesta di Paolo; versione da fissare alla pubblicazione)

- **Contributi** (`sito/contributi.html`, pagina di testo `main.articolo.contributi`): nella riga «Altre pagine» in alto e
  nel menu del telefono, **prima di Contattaci**. Dice che chi contribuisce sul forum e sui dati climatici sarà
  ringraziato qui; invita alla discussione generale sul forum di Edilclima («meet EuGEnio (ovvero a cosa serve l'AI per i
  tecnici? Parte #1)», `https://forum.edilclima.it/viewtopic.php?t=38424`) e a Contattaci. Sezione `#ringraziamenti` con
  la frase «In questa pagina verranno ringraziati coloro che hanno contribuito allo sviluppo del sito.» (15/11 sera),
  **nessun nome** finché Paolo non li dà.
- **Esempi** (`sito/esempi.html`, `main.articolo.esempi`): tra le **«Altre pagine»** (riga in alto e menu del
  telefono), **dopo Novità e prima di Contributi**: Come funziona · F.A.Q. · Sitografia · Mirror · Novità · Esempi ·
  Contributi · Contattaci (15/11 sera; prima era l'ultima voce del menu dei servizi, `a.voce-diretta`, tolta con il suo
  CSS). Contenuto: indice in cima (`nav.indice`) e
  un `h2` per gruppo del menu nello stesso ordine (`#clima`, `#patrimonio`, `#edifici`, `#aria`, `#cogenerazione`,
  `#fotovoltaico`, `#statistiche`), una riga d'introduzione (`.esempi-gruppo`), un `h3` per pagina accessibile con 1–3
  casi raccontati (`ul.esempi-casi`) e il collegamento alla pagina; le pagine in lavorazione e GME solo per nome in
  `p.esempi-arrivo` («In arrivo: …», senza collegamento); LiDAR e Visure (voci «in sviluppo» ma collegate) in una riga
  «In sviluppo». Quando una pagina passa da «in lavorazione» a disponibile, va tolta da «In arrivo» e le va scritto un
  esempio (il test lo pretende). Dal 15/11 in Clima e meteo c'è anche «Newsletter e avvisi» (`dati-per-email.html`).
- **Barra dei servizi su due righe** (`stile.css`, approvata da Paolo il 15/11): con sette gruppi la riga non stava più
  sotto ~1.170 px (la pagina scorreva in orizzontale). Da 861 px `.menu-gruppi` va a capo (`flex-wrap: wrap`) e tra
  1.061 e 1.340 px i titoli sono un po' più stretti (come già tra 861 e 1.060): senza «Iscriviti» ed «Esempi» la riga
  resta una fino a ~1.005 px (prova del 15/11 sera), sotto va su due; ✱ e ◐ restano a destra, `--alto-testata` si misura
  da sé. Le tendine si aprono verso sinistra per gli ultimi tre gruppi (`li:nth-last-child(-n+3)`), ma `aspetto.js` (al
  `toggle`) le gira dall'altra parte se uscirebbero dalla finestra (`.tendina.a-sinistra` / `.a-destra`): a 1.000 px
  Statistiche va sulla seconda riga, a sinistra. La riga «Altre pagine» in alto, con otto voci, sta su una riga da 861 px
  in su (prova a 1366, 1100, 1000, 900 e 861 px); sotto gli 861 px le voci sono nel pulsante Menu.
- Test: `tests/test_esempi_contributi.py` (ordine delle «Altre pagine» nella riga in alto e nel telefono, Esempi non più
  nel menu dei servizi né nel CSS, forum, Contattaci e frase dei ringraziamenti, gruppi e indice di Esempi nell'ordine
  del menu, ogni collegamento interno a un file che esiste e mai a una pagina in lavorazione o GME, ogni pagina
  accessibile con un esempio e ogni pagina non accessibile «in arrivo», nessun dato di mercato; in Chromium nessuno
  scorrimento orizzontale a 1366, 1100, 1000, 900 e 375 px, riga in alto su una riga e dentro la finestra, voce Esempi
  che porta alla pagina senza fissare la riga, a 375 px Esempi e Contributi tra le «Altre pagine» del pulsante Menu);
  `test_costruisci_pagine.py` (Altre pagine con Esempi e Contributi, voce attiva delle due pagine);
  `test_menu_browser.py` (tendine dentro la finestra anche a 1100 px).

## Trattamento aria: moduli comuni e pagine (14/11/2026, `?v=20261114b`, pubblicato il 15/11 con la seconda pubblicazione del giorno)

Nuovo gruppo di menu **«Trattamento aria»** (`data-gruppo="aria"`) tra Edifici e Cogenerazione, con il sottotitolo non
cliccabile **«Psicrometria»** (`<li class="voce-sottotitolo">`, anche nella riga fissata e nel telefono) e 4 voci
sperimentali («S»): Trasformazioni (UTA), Ore di funzionamento, Carichi latenti, Free cooling e recupero. Con sette gruppi
gli **ultimi tre** si aprono verso sinistra (a 900 px Cogenerazione usciva dalla finestra). `costruisci_pagine.py` non è
cambiato: gruppo, «Nello stesso gruppo» ed etichetta del gruppo vengono già dal menu della testata; `parti/testa.html`
accetta `aria` nel menu fissato.

**Pagine** (`main.strumento.pagina-aria`): a sinistra titolo e piccola mappa, mappa della regione (`#mappa`, altezza
`clamp(240px, 38vh, 440px)`; dal 16/11 la pagina è divisa in due metà alte quanto la finestra, ognuna con la sua barra di
scorrimento – quella di sinistra sul lato sinistro – e il piè di pagina in fondo alla colonna sinistra, come Patrimonio) e sotto il diagramma (`#diagramma-aria`); a destra i passi: 1 «Comune e
serie meteo» (`#scelta-aria`), 2 dati della pagina (`#aria-gruppi` nelle tre pagine con i gruppi, `#aria-livello` in
Trasformazioni, `#aria-pagina`), 3 «Risultati» (`#passo-risultati`, nascosto), poi «Nello stesso gruppo». Le pagine possono aggiungere
passi (`.passo` con `h2 > span.n`). Ogni pagina ha il suo `aria_<pagina>.js` (calcolo nel browser, CSV dei risultati) e un
gemello Python del calcolo in `fase14-trattamento-aria/aria/` con prove di parità:

| Pagina | Script | Cosa fa | Predefiniti |
|---|---|---|---|
| `aria-trasformazioni.html` | `aria_trasformazioni.js` | sequenza UTA del foglio `psicro_UTA.xlsx` (estate e inverno, fino a 10 righe), condizioni esterne dalla serie modificabili («ripristina dal clima»), stima stagionale, foglio Excel compilato nel browser (prime 6 righe), CSV e JSON | dati del foglio (5000 m³/h, 120 m…; ambiente invernale 20 °C/40 %, dal 15/11/2026 anche nel foglio) |
| `aria-ore.html` | `aria_ore.js` | nuvola di tutte le ore per 4 gruppi, statistiche, condizioni di progetto, classi di T e x, zona di comfort; Punti/Densità | G1 estate 5 anni, G2 inverno 5 anni, G3 estate 20 anni, G4 inverno 20 anni |
| `aria-latenti.html` | `aria_latenti.js` | deumidificazione estiva e umidificazione invernale a vapore dell'aria esterna: ore, energia, potenze anche per 1.000 m³/h, curva di durata | 26 °C/50 % (UR massima), 20 °C/40 % (UR minima), 10 anni |
| `aria-freecooling.html` | `aria_freecooling.js` | regimi ora per ora, free cooling (economizzatore a temperatura o entalpico), recupero, brina, mese per mese | G1 ore d'ufficio tutto l'anno, G2 tutte le ore |

Colori delle stagioni: ESTATE blu, INVERNO rosso, linee spesse (come il foglio). Le API complete dei moduli comuni sono in
`API_MODULI_ARIA.md` (documento di lavoro fuori dal repository) e in breve qui:

- **`psicro.js`** (`window.EUGENIO_PSICRO`, anche `require` in node): formule del foglio `psicro_UTA.xlsx` e di psychrolib
  SI, gemello Python in `fase14-trattamento-aria/aria/psicro.py` con test di parità. `stato(t, dato, p)` (dato: UR % o
  `{ur}|{x}|{xg}|{twb}|{tdew}|{h}`), `statoTX`, `statoHX`, inverse (`tRugiada`, `tBulboUmido`, `tSatDaH`,
  `tIsoentalpicaUR`, `adpRetta`, `adpDaBF`), `mollierY`/`tDaMollier`, `trasforma(tipo, ingresso, [P1,P2,P3], ctx)` con i
  tipi e gli avvisi del foglio, `sequenza(opz)` (una stagione del foglio UTA), `portataMassica`, `puntoImmissione`,
  `vettori(t, ur, p)` (x, h, bulbo umido di una serie oraria, una volta per serie: ~0,4 s per 750.000 ore) e
  `condizioniProgetto(t, ur, p, { inverno: 99, estate: 1, indici })` (percentili della serie, predefiniti 99 % / 1 %).
- **`diagramma_aria.js`** (`EUGENIO_DIAGRAMMA_ARIA.crea(box, opz)`): diagramma su canvas con «Psicrometrico» /
  «Mollier», stesse curve e scale del foglio, strati `nuvola` (100.000 punti in ~0,1 s), `spezzata`, `punto`, `zona`,
  `retta`, legenda con «mostra», suggerimento T/UR/x/h, ↗ col riquadro di `grafici.js` (sotto il diagramma la legenda
  della pagina), PNG e SVG con i colori di stampa e la fascia con la **legenda degli strati visibili** (nome, colore,
  nota, per esempio le ore l'anno), le fonti della pagina e «Fonte: EuGEnio».
- **`scelta_aria.js`** (`EUGENIO_SCELTA_ARIA.crea(opz)`): passo 1 con mappa ed elenco dei comuni, cursore «ultimo anno · 2
  · 5 · 10 · 20 · tutta la serie», `GET /api/psicro/serie/{istat}?anni=` con copia in memoria, disponibilità, errori
  503/429 in italiano, evento `eugenio:aria-serie`; scelta in `localStorage` `eugenio-aria-v1` comune alle 4 pagine.
  **Modo di prova** `?prova=1`: serie oraria sintetica generata nel browser, scritta come «dati sintetici di prova».
  Sotto la riga della disponibilità e della fonte, le **note del server** (`note` della risposta: archivio dal 1940 non
  ancora sul server, anni chiesti e disponibili, fonti periodo per periodo, ore senza dati; la prima in grassetto) in
  `ul.aria-note-serie`. I testi delle pagine non danno per certa la fonte: rimandano al passo 1.
  `EUGENIO_SCELTA_ARIA.livelloProgetto(box)`: livello delle condizioni di progetto (99,6 · 99 · 95 % in inverno, 0,4 · 1 ·
  5 % in estate, più «altro»; predefiniti 99 % / 1 %), ricordato in `eugenio-aria-v1`, evento `eugenio:aria-livello`.
- **`gruppi_ore.js`** (`EUGENIO_GRUPPI_ORE.crea(box, opz)`, parte pura anche in node): fino a 4 gruppi di ore con nome,
  «Mostra», anni, date, ore locali (ora legale italiana: storica fino al 1995, europea dal 1996), feriali e i preset Estate · Inverno · Tutto l'anno · Ore d'ufficio ·
  Tutto il giorno; Inverno secondo la zona climatica del DPR 412 se nota; evento `eugenio:aria-gruppi`. Ore: «dalle»
  compresa, «alle» esclusa; sotto i campi la pagina scrive l'intervallo in chiaro («dalle 8 alle 18, cioè ore
  8:00–17:59», 10 ore). Nelle pagine aria `[hidden]` vince su `.bottone` (regola in `stile.css`: prima il «Togli» del
  gruppo unico restava visibile).

Prove: `tests/test_aria.py` (menu, pagine, node) e `tests/test_aria_browser.py` (Chromium: 4 pagine × 2 temi con
`?prova=1`, viste, nuvola di 100.000 punti sotto 1 s, esportazioni, ↗, gruppi, livello, scelta condivisa, menu a 1366,
1000 e 900 px); per pagina `test_aria_trasformazioni_browser.py`, `test_aria_ore_browser.py`, `test_aria_latenti.py`
(Python e node) e `test_aria_latenti_browser.py`, `test_aria_freecooling_browser.py` (temi, 1366 e 375 px, nessun errore
JS, controlli che cambiano i risultati). `test_scelte_serie_browser.py`: le scelte degli anni nelle pagine del clima.

**Scelta degli anni nelle pagine del clima** (stessa decisione): Legge 10 «ultima stagione · 5 · 10 · 20 · tutta la serie»
(`anni=1|5|10|20|0` di `/api/clima-legge10/{istat}`; le stagioni vengono dall'archivio giornaliero dal 2015, la risposta
dice quante ce ne sono; con meno di 5 i valori sono indicativi), Dati climatici (periodo «ultimo anno · 5 · 10 · 20 anni ·
tutta la serie»; per `legge10` le stesse stagioni), Cambiamento climatico (tendenza sulle ultime 5, 10 o 20 stagioni,
dal 1991/92, 1981/82, 1961/62 o su tutta la serie dal 1940/41). Foglio Excel scaricabile in `strumenti/psicro_UTA.xlsx` (eccezione nel `.gitignore`, che esclude gli xlsx).

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
- `python costruisci_pagine.py` genera `sito/novita.html` (pagina di testo con l'indice laterale per versione; dal
  21/11/2026 sotto ogni titolo, in piccolo, «gg/mm/aaaa · versione …») e
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
- **Vicini fuori da un archivio parziale (16/11/2026)**: il ripiego OSM si chiede quando il contesto di ~250 m attorno
  al punto non è tutto coperto (`contestoCoperto` in `edificio3d.js`: il punto e otto punti attorno), non solo quando il punto
  è fuori; i corpi OSM che cadono nelle zone coperte li scarta `fuoriDalDbtr`. Caso: Perugia (archivio parziale), CREO
  dentro il riquadro e polo ospedaliero fuori.
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

## Newsletter e avvisi (14/11/2026, `?v=20261114a`)

Pagina **`dati-per-email.html`** (`dati_per_email.js`), voce **«Newsletter e avvisi»** del gruppo Clima e meteo (decisione di Paolo del 15/11/2026: il pulsante
«Iscriviti» della testata e del menu del telefono è tolto; prima portava al modulo di listmonk). Tre servizi separati (decisione di Paolo del 14/11/2026): newsletter mensile con le regioni (fino a 3),
previsioni settimanali e avvisi meteo con i comuni (fino a 5, tutta Italia), gli avvisi per pioggia forte, neve e vento
molto forte con l'avvertenza «Il servizio di avvisi meteo è gratuito, non fornisce garanzie e non sostituisce le allerte
della Protezione Civile e degli enti pubblici».

Stati della pagina: senza nulla dopo `#` il modulo dell'email (`POST /api/email/link`, verifica anti-robot in
`protezione.js`); con `#t=<gettone>` le scelte (`/api/email/leggi` e `/salva`); con `#via=<gettone>` la cancellazione da un
servizio (`/api/email/via`). Il gettone si toglie dalla barra appena letto. Se l'API risponde `"attivo": false` la pagina
rimanda al modulo di listmonk. Server: sezione «Newsletter e avvisi» del README della fase 4.

Aggiornati anche F.A.Q. (`#dati-per-email`, `#avvisi-meteo`), informativa privacy (riga `#newsletter`), Novità, file per
gli agenti (§ 3 Altre pagine, § 4.9, § 8) e `llms.txt`. Stile: `.dati-email`, `.dpe-*` in `stile.css`. Prova nel
browser: `tests/test_dati_per_email_browser.py` (API finta).

## Attribuzione obbligatoria, termini aggiuntivi della AGPL (16/11/2026)

Decisione di Paolo del 16/11/2026. Il codice resta AGPL-3.0, con tre termini aggiuntivi della sezione 7 scritti in
`TERMINI_AGGIUNTIVI.md` nella radice del repository:

- (b) chi distribuisce EuGEnio o lo fa usare in rete, anche modificato, conserva la riga «EuGEnio © 2026 Paolo Bianco –
  Stato Critico – https://eugenio.statocritico.it» nel piè o in una pagina raggiungibile da ogni pagina;
- (c) le versioni modificate si distinguono dall'originale;
- (e) nessun diritto su nomi e logo.

Nel sito la riga sta nel piè di tutte le pagine (`parti/piede.html`, `<span class="piede-attribuzione">`), insieme al
collegamento `licenza.html#attribuzione`. La sezione nuova «Attribuzione obbligatoria» della pagina Licenza spiega i
termini e dice che l'uso interno non ha obblighi. Anche la pagina Mirror, nelle «Regole da rispettare», ha una riga
nuova. Il test `test_attribuzione_agpl_in_tutte_le_pagine` controlla il piè di ogni pagina, la sezione della Licenza e
il file dei termini. Nessuna voce di Novità, perché non cambia nessuna funzione per gli utenti. La versione del sito
non cambia.
