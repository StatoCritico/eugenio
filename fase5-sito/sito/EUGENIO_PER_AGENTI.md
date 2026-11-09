# EuGEnio per agenti AI

> **Ultimo aggiornamento: 07/11/2026 (sera, dopo le prime prove: tetti stimati dal colmo, ricerca nella colonna destra e per solo comune, ortofoto RER trasparente dove non ha dati, camera 3D sopra il terreno; 08/11: frecce per spostare l'ortofoto di 1 m, parametri `de`/`dn` delle tessere; tetti ipotizzati 22°/32° e «Forma dei tetti»; sagome regionali del Veneto con le altezze OSM; terreno da più DTM, anche il Veneto; menu dell'08/11: gruppo Edifici, pagine dei gruppi Edifici, Cogenerazione e Fotovoltaico «in lavorazione» e non accessibili dal menu, «Cambiamento climatico» in Clima e meteo, mappe che si aprono su Cesena; edifici dei DB topografici anche per 15 città fuori dall'Emilia-Romagna (Napoli con le classi di altezza Copernicus) e sagome regionali al volo anche in Sardegna e Campania; 09/11: Roma, Bari e Bologna per il comune intero, 69 archivi di edifici (54 DBTR dell'Emilia-Romagna); colore degli edifici e alberi in Modelli 3D, ricerca con Comune prima dell'Indirizzo e «Reset», tutti i comuni italiani nella ricerca per comune, clic sulla mappa che non sposta la vista, limiti per IP solo sulle tessere chieste alla fonte e 429 con `Retry-After`, Previsioni non più sperimentale; 09/11 b: ricerca con **un solo Comune** in cima, Indirizzo, Foglio e Particella e un solo «Reset», risultati in un altro comune scartati; «Colore» e «Alberi» sotto la mappa accanto ad «Azzera»; celle LiDAR chieste solo se esistono; quote del terreno Copernicus anche per gli edifici OSM e le sagome regionali; tessere segnaposto delle ortofoto trattate come vuote) – versione del sito `?v=20261109b`.**
> Regola di manutenzione: dopo ogni modifica alle funzioni, alle pagine o alle API di EuGEnio questo file si aggiorna
> (nella radice del repository e in `fase5-sito/sito/`, le due copie sono identiche) insieme a `fase5-sito/sito/llms.txt`,
> con data e versione del sito. Un test (`fase4-server/tests/test_agenti.py`) confronta i percorsi `/api/…` citati qui con
> le rotte reali dell'API, in tutti e due i sensi, e fallisce finché il file non è allineato.

*In English, briefly: EuGEnio (eugenio.statocritico.it) is a free, open source (AGPL-3.0) Italian web service for energy
managers: energy consumption forecasts with TiRex-2 and municipal weather, climate data for the Italian "Legge 10"
building energy reports, building portfolio geolocation, 3D buildings, solar and shading tools, health-sector energy cost
statistics. This file, written in Italian, tells an AI agent what each page and public API does, what it may and may not
automate, and how to cite the data. Free-to-use JSON APIs are listed in § 4; some routes require a human browser check
(Cloudflare Turnstile).*

Questo file serve a un agente AI (Claude, ChatGPT, Gemini, Copilot…) che deve usare EuGEnio **per conto di una persona**:
cosa c'è, come si usa, cosa può fare da solo con le API, cosa deve lasciare fare alla persona nel browser, come citare le
fonti e cosa non deve fare. È ricavato dal codice; se trovi una differenza tra questo file e il comportamento reale del sito,
vale il sito: segnalala (§ 10).

Indice: 1. Cos'è · 2. Licenze e come citare · 3. Mappa del sito, pagina per pagina · 4. API pubbliche · 5. Limiti e
protezioni · 6. Flussi tipici · 7. Cosa EuGEnio non fa · 8. Privacy, funzione per funzione · 9. File statici utili ·
10. Contatti e segnalazioni · 11. Da dove è ricavato questo file.

---

## 1. Cos'è

- **EuGEnio** («Eu» di Europa + «EGE», Esperto in Gestione dell'Energia) è il primo servizio online di **Stato Critico**,
  progetto personale e senza scopo di lucro di un energy manager del settore sanitario pubblico (titolare: Paolo Bianco).
- Indirizzo: `https://eugenio.statocritico.it` (sito statico + API sotto `/api/`). Codice: `https://github.com/statocritico/eugenio`.
- Gira su un server gratuito (Oracle Cloud, 2 CPU ARM, **senza GPU**): le risorse sono poche, usale con parsimonia.
- Lingua del sito e delle risposte dell'API: **italiano**. Numeri nell'API con il punto decimale; nei CSV scaricati
  separatore `;` e virgola decimale (per Excel in italiano).
- Copertura: i comuni italiani (codici ISTAT a 6 cifre, per esempio `099014` Rimini, `037006` Bologna). Più dati e più
  funzioni per l'**Emilia-Romagna** (regione `08`) e per la **sanità**. Il meteo di un comune può non essere ancora sul server:
  in quel caso le rotte rispondono 503 o 404 con un messaggio chiaro, non è un tuo errore.
- Stato: **servizio sperimentale**, risultati non ancora validati in modo sistematico (validate: Costi energetici Sanità e, dal 07/11/2026, Dati climatici e Legge 10). Non sostituisce i valori
  normativi, le visure ufficiali né il giudizio di un professionista. Dillo alla persona quando le dai i risultati.

## 2. Licenze e come citare

- **Codice**: AGPL-3.0. Chi offre online una versione modificata deve pubblicarne il codice.
- **Dati elaborati e report di EuGEnio**: CC BY 4.0. Formula obbligatoria nel documento che li usa:
  **«Fonte: EuGEnio – eugenio.statocritico.it»**, più le fonti originali indicate nel file o nella risposta (campi `fonte`,
  `licenza`, `citazione`, foglio «Info» degli Excel/ODS, ultime righe dei CSV, «Fonti e attribuzioni» dei PDF).
- **Nome e logo** («EuGEnio», «Stato Critico», logo e simbolo) non sono in licenza: si citano per dire la provenienza
  («basato su EuGEnio»), ma un servizio derivato deve avere nome e logo propri.
- **Attribuzioni delle fonti** (riportale quando usi i relativi dati):

| Dato | Attribuzione |
|---|---|
| Meteo e clima (previsioni, storico, Legge 10, gradi giorno) | Weather data by Open-Meteo.com (CC BY 4.0); ERA5: Copernicus Climate Change Service (C3S), ECMWF; ICON: Deutscher Wetterdienst (DWD); correzione ed elaborazioni: EuGEnio |
| Clima dal 1940 | ERA5 / ERA5-Land, Copernicus (C3S), tramite Open-Meteo (CC BY 4.0); elaborazione EuGEnio |
| Comuni, codici, confini | ISTAT (CC BY 4.0), confini tramite Gramscii |
| Indirizzi (civici) | ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0) |
| Particelle e geocodifica via Zornade | collegamento **«Dati elaborati da Zornade»** a `https://zornade.com` (obbligatorio, non basta la scritta) + fonti originali (Agenzia delle Entrate – catasto, ISTAT, OpenStreetMap ODbL) |
| Cartografia catastale (strato delle particelle) | Agenzia delle Entrate – Cartografia catastale, CC BY 4.0 (servizio WMS INSPIRE; linee ricolorate da EuGEnio) |
| Edifici Emilia-Romagna | «Regione Emilia-Romagna – DBTR, CC BY 4.0» (unità volumetriche ed edifici); terreno «Regione Emilia-Romagna – DTM 5×5 m (CC BY 4.0)» (quote dei corpi e tessere di `/api/terreno/{z}/{x}/{y}.png`; fuori dall'ER le tessere vengono dal Copernicus DEM GLO-90, © DLR e Airbus); altezze del DBTR non plausibili portate alla stima e dichiarate (`h_dbtr_scartata`, «altezza stimata (dato DBTR non plausibile)») |
| Edifici OpenStreetMap | © contributori OpenStreetMap (ODbL 1.0); archivio separato da quelli CC BY; anche gli edifici del ripiego di Modelli 3D fuori dal DBTR (`GET /api/edifici/osm`): ogni edificio porta la licenza della sua sagoma |
| Edifici del Veneto (sagome regionali al volo, 08/11/2026) | «Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0» per le sagome; altezze prese da OpenStreetMap (ODbL 1.0) dove un edificio OSM si sovrappone; licenza per corpo `IODL 2.0; altezza ODbL 1.0` o `IODL 2.0` (altezza stimata) |
| Terreno del Veneto | «Regione del Veneto – DTM 5 m da voli LiDAR, IODL 2.0» (tessere di `/api/terreno/{z}/{x}/{y}.png` e quote dei corpi in Veneto, dove il DTM è sul server; intestazione `X-Terreno-Nome`) |
| Edifici delle città fuori dall'ER (08/11/2026) | l'`attribuzione` dell'archivio in `/edifici3d/archivi.json` e nel suo `indice.json` (per esempio «Comune di Venezia – DBGT, Unità volumetriche (IODL 2.0)», «Regione Piemonte – BDTRE, Unità volumetriche (altezze ARPA Piemonte), CC BY 2.5», «Provincia autonoma di Bolzano – INSPIRE Edifici (CC0 1.0); altezze da DSM − DTM …», «Regione Campania – DBT 2020 … (CC BY 4.0); altezze: © European Union, Copernicus Land Monitoring Service 2012, European Environment Agency (EEA) …»); `licenza` per corpo; il file `LICENZE.txt` accanto a ogni archivio |
| Sagome regionali al volo di Sardegna e Campania (08/11/2026) | «Regione Autonoma della Sardegna – DBGT 10k 2022, Edificio (CC BY 4.0)», «Regione Campania – CTR 2020, Geoportale Regione Campania (CC BY 4.0)»; altezze OSM (ODbL 1.0) o stimate, come in Veneto |
| Terreno e LiDAR ER | Regione Emilia-Romagna, DTM e prodotti LiDAR (CC BY 4.0) |
| Orizzonte lontano | Copernicus DEM GLO-90 (© DLR e Airbus, licenza Copernicus DEM), dai file di Open-Meteo.com (CC BY 4.0) |
| Ortofoto | la citazione della fonte scelta, restituita da `/api/ortofoto/fonti` (per esempio «Regione Emilia-Romagna – Ortofoto RER 2023-24 (CC BY 4.0)», «Sentinel-2 cloudless – https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) (CC BY 4.0)»); il Geoportale Nazionale è solo consultazione dal vivo e non va nei report |
| PVGIS | PVGIS © Unione europea, Joint Research Centre (JRC); riuso con citazione (decisione 2011/833/UE) |
| Fattori di emissione | ISPRA (CC BY 4.0) |
| Sanità | Ragioneria Generale dello Stato – OpenBDAP; Regione Emilia-Romagna – ReportER; ISTAT (CC BY 4.0) |
| Prezzi PMI | Eurostat (nrg_pc_205, nrg_pc_203), riuso con citazione |
| Gradi giorno e zone di legge | DPR 412/93, Allegato A (atto normativo, libero); abbinamento ai codici ISTAT: EuGEnio |
| Valori ricavati dagli anni tipo CTI (pagina Legge 10) | si possono **solo citare** (EuGEnio e CTI): non sono CC BY |

- I dati catastali (Zornade, visure) **non sostituiscono visure ed estratti ufficiali** dell'Agenzia delle Entrate.

## 3. Mappa del sito, pagina per pagina

Tutte le pagine stanno in `https://eugenio.statocritico.it/<pagina>`. Le pagine funzionano **in un browser con
JavaScript** (mappe con MapLibre/WebGL, calcoli nel browser). Un agente che non controlla un browser usa le API del § 4,
quando ci sono, oppure guida la persona passo passo.

Etichette di stato del menu: **S** = sperimentale (funziona, risultati da controllare); **triangolo giallo** = in sviluppo
(LiDAR e Visure: pagina descrittiva, nessun dato) oppure, se la voce **non è cliccabile** (suggerimento «In lavorazione:
disponibile prossimamente»), **in lavorazione**: pagina non accessibile dal menu né da altri collegamenti del sito,
raggiungibile solo con l'indirizzo diretto, con in cima l'avviso «Pagina in lavorazione, non ancora verificata»; **GME** =
in attesa di autorizzazione dal GME (voce non cliccabile, pagina segnaposto). Dall'08/11/2026 sono **in lavorazione tutte
le pagine dei gruppi Edifici, Cogenerazione e Fotovoltaico** (tranne le voci GME): un agente non le propone alla persona
come servizi disponibili. Accessibili: Clima e meteo, Patrimonio, Statistiche.

Parametri dell'indirizzo comuni: `?regione=RR` (codice regione ISTAT a 2 cifre, predefinito `08`) sceglie la regione della
mappa in Previsioni, Patrimonio, Legge 10, Dati climatici, Ortofoto; `?vista=italia` apre la mappa grande su tutta Italia.

### Clima e meteo

| Pagina | URL e parametri | A cosa serve | Ingressi | Uscite | Stato |
|---|---|---|---|---|---|
| **Previsioni** | `/` (`index.html`), `?regione=RR` | Previsione dei consumi di un edificio con TiRex-2 dal suo storico, dal meteo previsto del comune e dal calendario; oppure **«Solo clima»**: le variabili meteo previste del comune, senza file | comune (mappa, elenco o indirizzo); file dei consumi; «energia per intervallo» (si somma) o «potenza o media» (si media); orizzonte «prossimi giorni, ora per ora» (fino a 15 giorni) o «prossimi mesi, giorno per giorno» (fino a 365); modo «prevedi il futuro» o «mettila alla prova sull'ultimo periodo»; variabili meteo | grafico con fasce di probabilità (quantili 10–90 %), schede delle variabili meteo, avvisi; report PDF, dati in Excel/ODS | sperimentale |
| **Legge 10** | `legge10.html`, `?comune=ISTAT`, `?regione=RR` | Dati climatici del comune dal clima reale delle ultime stagioni (5, 10 o 30): gradi giorno sul periodo della zona e sull'anno, zona risultante, tendenza per decennio, temperature di progetto, dati mensili come nella UNI 10349, confronto con l'Allegato A del DPR 412/93; clima dal 1940 | comune | grafici, tabelle; CSV/JSON; report PDF/Excel/ODS; CSV nazionali `dati/clima_sintesi.csv` e `dati/clima_stagioni.csv` | attiva |
| **Cambiamento climatico** | `edificio-clima.html`, `?istat=ISTAT` (indirizzo invariato; fino al 07/11/2026 «Clima che cambia» nel gruppo Edificio) | Tendenza dei gradi giorno dal 1940 nel comune e consumi attesi con la firma energetica dell'edificio (analisi 13); estrapolazioni della tendenza, non scenari climatici ufficiali | comune, stagione di partenza, carico di base e pendenza (facoltativi) | grafico, tabella | sperimentale |
| **Dati climatici** | `dati.html`, `?dataset=ID` (`meteo_orario`, `meteo_giornaliero`, `gradi_giorno`, `legge10`, `dpr412`, `comuni`, `eurostat_pmi`) | Scaricare dati ridistribuibili per comune, provincia, regione o Italia | dataset, grandezze, periodo, frequenza (oraria, giornaliera, mensile, annuale, per stagione), copertura minima, area | CSV, Excel (.xlsx), OpenDocument (.ods), con fonti e licenze | attiva (il download chiede la verifica anti-robot) |

Per la relazione tecnica ex Legge 10 restano **obbligatori i valori normativi** (UNI 10349, DPR 412/93): EuGEnio dà il clima
osservato come confronto. I prospetti UNI non sono pubblicati.

Formato del file dei consumi (Previsioni): CSV, `.xlsx` o `.ods` (primo foglio), **due colonne**: data/ora e valore,
separatore `;`, `,` o tabulazione, decimali col punto o con la virgola, date `AAAA-MM-GG hh:mm` o `GG/MM/AAAA hh:mm`
(ora italiana se senza fuso), almeno 30 valori, al massimo 200.000 righe e 5 MB. Dati quartorari o orari per la modalità
oraria (si riportano all'ora), giornalieri per quella giornaliera. Esempi: `esempi/esempio_orario_sintetico.csv`
(`data;kWh` / `27/06/2026 01:00;20,69`), `esempi/esempio_giornaliero_sintetico.csv` (`giorno,consumo` / `2024-01-23,1074.1`).

### Patrimonio

| Pagina | URL e parametri | A cosa serve | Ingressi | Uscite | Stato |
|---|---|---|---|---|---|
| **Patrimonio** | `patrimonio.html`, `?regione=RR`, `#valori` (scheda «Valori per sede») | Geolocalizzare un elenco di edifici: punto, particella catastale, comune; mappa 3D con i valori di ogni sede (consumi, costi) come barre; abbinare le visure lette da EuGEnio Visure; aprire una sede in Modelli 3D | file degli edifici (sotto) | mappa, esiti `ok` / `verificare` / `non_trovato`; CSV (`;`, BOM), GeoJSON con attribuzione; report PDF/Excel/ODS | attiva |
| **Ortofoto** | `ortofoto.html`, `?lat=…&lon=…&z=…` (predefinito, dall'08/11/2026: Cesena, ospedale Bufalini, viale Ghirotti 286, 44,1326 N 12,2597 E, zoom 15,6), `&fonte=ID`, `?regione=RR` | Foto aeree come sfondo, con strati delle particelle catastali e dei contorni degli edifici; ricerca per indirizzo o per foglio e particella (dal 09/11/2026 b un solo modulo con un solo Comune, come Modelli 3D) | luogo | mappa; immagine JPG/PNG/PDF con le attribuzioni | sperimentale |
| **LiDAR** | `lidar.html` | Descrive la ricostruzione di altezze e falde dai rilievi laser | — | — | in sviluppo |
| **Modelli 3D** | `modelli3d.html`, `?edificio=ID`, `?archivio=demo` (demo sintetica, edifici inventati), `?archivio=<percorso>` (altro archivio sotto `/edifici3d/`), `?sede=locale` (sede passata da Patrimonio nella memoria della scheda), `?modello=locale` (modello passato da Importa DXF/IFC), `?dbtr=locale` (edifici del DB topografico letto in Aggiungi edifici, dalla memoria del browser) | Mappa 2D con ricerca e clic sull'edificio, poi «Genera il 3D»: corpi, edifici vicini, terreno, piani e superfici stimati | edificio scelto | vista 3D; immagine PNG/PDF; report dell'edificio | sperimentale: dal 07/11/2026 sagome e altezze delle **unità volumetriche del DBTR** dell'Emilia-Romagna (CC BY 4.0, con i cortili, foglio e numero dell'edificio, destinazione d'uso) per i comuni già preparati, uno per archivio (all'inizio Rimini; poi gli altri comuni della Romagna; dal 09/11/2026 54 archivi: Bologna e Castel Bolognese interi, Ravenna con parte del forese, i centri di altri comuni della Romagna e della cintura di Bologna, con nome «… (centro e frazioni principali)» o «… (zona verso Bologna)» e zona coperta vicino ai corpi); **dall'08/11/2026 anche 15 città fuori dall'Emilia-Romagna**, con i DB topografici di Regioni, Province e Comuni: Milano, Torino, Genova (parte del centro, San Martino e Lanterna), Venezia, Trieste, Trento, Bolzano, Firenze, Ancona, Roma (comune intero dal 09/11/2026, 7 fogli del DBGT 2014), Bari (comune intero dal 09/11/2026, CTR 2006), Potenza, Napoli, Palermo e Cagliari (Castello e Brotzu), ognuna con la sua licenza (CC BY 4.0, CC BY 2.5 a Torino, IODL 2.0 a Venezia, Bari e Potenza, CC0 1.0 a Bolzano) e altezze dal DB o dal rilievo laser (Trento, Bolzano, Cagliari, Genova); a Napoli (DBT 2020 della Regione Campania, CC BY 4.0) le altezze vengono dalle **classi** del Copernicus Urban Atlas Building Height 2012 («© European Union, Copernicus Land Monitoring Service 2012, European Environment Agency (EEA)»: centro della classe, per esempio 25 m per la classe 20–30 m), poi dalla mediana dei vicini, poi dalla stima dall'uso, sempre dichiarate per corpo; le Regioni che pubblicano le sagome senza altezze (Veneto, Sardegna, Campania) danno le sagome al volo con le altezze OSM; `/edifici3d/archivi.json` elenca gli archivi con il loro riquadro e, per un comune intero, il codice `istat` (zona coperta = confine ISTAT del comune); **fuori dal DBTR** (fuori dall'Emilia-Romagna e nei comuni ER non ancora preparati) la pagina usa come **ripiego gli edifici OpenStreetMap** intorno al punto (`GET /api/edifici/osm`, ODbL 1.0, qualità inferiore, altezze in parte stimate, dichiarate in pagina, nell'immagine e nel report); se OpenStreetMap non risponde lo dice e il 3D non si genera; dove c'è il DBTR OSM non si usa; con `?dbtr=locale` gli edifici del file caricato dalla persona valgono per primi (zona coperta per la sessione: confine del comune se il file è il comune intero, altrimenti il riquadro dei corpi); senza parametri nell'indirizzo (e con la regione scelta Emilia-Romagna) la mappa si apre su **Cesena, ospedale Bufalini** (zoom 15,6, l'ospedale e la collina; con una regione scelta diversa, su quella regione); la ricerca (primo passo della colonna destra, esempio «viale Ghirotti 286», «Cesena») porta la mappa a zoom 17; **con il solo comune** (o un indirizzo senza coordinate) al centro del comune a zoom 14, senza chiamare il server; un punto vicino al confine (generalizzato) di un comune coperto è coperto se l'archivio ha un corpo entro 150 m; **forma dei tetti in cascata** per ogni corpo (08/11/2026): falde misurate dal LiDAR → **tetto stimato dal colmo DBTR** (a capanna sul lato lungo, a padiglione se quasi quadrato) → **tetto ipotizzato a falde, 22° in pianura e 32° in montagna** (montagna = quota del terreno sotto il corpo da 600 m al Nord, da 700 m al Centro-Sud; stessa forma, colmo = gronda + semiluce × tan(inclinazione)) → **piano** per capannoni, commerciali, palestre, tettoie, corpi oltre 1.500 m² o con il lato corto oltre 25 m, gronda sotto 3 m, cortili, forme poco rettangolari; nota sotto la mappa «Tetti: N misurati dal LiDAR, M stimati dal colmo DBTR, K ipotizzati (22° pianura / 32° montagna), P piani», anche in legenda, immagine e report; edifici OSM in marrone; nella vista 3D rilievo ombreggiato, esagerazione ×1/×1,5/×2 dichiarata nell'immagine e la fonte del terreno in legenda; nuova ricerca o mappa portata a oltre 2 km durante il 3D → mappa 2D; dal 09/11/2026: **colore degli edifici** a scelta (grigio, giallo, rosso, indaco, violetto; l'edificio scelto resta arancio, OSM marrone) e casella **«Alberi»** (chiome dal LiDAR, spenta in partenza), ricordati nel browser e scritti nell'immagine; dal 09/11/2026 b la ricerca è **un solo modulo**: **Comune** una volta sola in cima, **Indirizzo**, **Foglio** e **Particella** affiancati, poi «Cerca l'indirizzo» (usa solo Comune e Indirizzo), «Cerca la particella» (solo Comune, Foglio e Particella) e un solo «Reset» che svuota tutto; con il solo Comune tutti e due vanno al centro del comune; un risultato in un altro comune (comune catastale diverso da quello scritto) non sposta la mappa lì ma al centro del comune scritto, con l'avviso; «Colore» degli edifici e «Alberi» stanno **sotto la mappa**, nella riga di «Genera il 3D» dopo le frecce dell'ortofoto e «Azzera»; la ricerca per solo comune trova tutti i comuni italiani; **un clic sulla mappa non sposta mai la vista** (regione e comune si evidenziano); dove la fonte di ortofoto scelta da sola non ha immagini la pagina passa alla successiva e lo dice; se una fonte della mappa supera il limite orario, nota sotto la mappa con il tempo di ripresa |
| **Aggiungi edifici (DB topografico)** | `aggiungi-dbtr.html`, `?regione=er\|lom\|fvg\|lig` | Caricare il **database topografico** scaricato dal portale della Regione (zip, GeoPackage o Shapefile, fino a 300 MB): corpi con le altezze ricavati **nel browser** (Web Worker, stesse regole del server: convenzione delle altezze del comune, cortili, foglio, numero, destinazione) e usati in Modelli 3D solo da chi li ha caricati; **facoltativo**, con una casella di consenso non spuntata di partenza: proposta dello stesso file all'**archivio comune** (coda sul server, controlli automatici, approvazione di Stato Critico) | regione, comune, «comune intero» sì/no, file | edifici in Modelli 3D (`modelli3d.html?dbtr=locale`); stato delle proprie proposte | sperimentale; Emilia-Romagna (DBTR) provata su più comuni; Lombardia (DBGT), Friuli Venezia Giulia (CTRN) e Liguria (CTR 3D, solo proposta al server: serve il DTM) sperimentali |
| **Scaricare i DB topografici** | `dbtr-istruzioni.html` | Istruzioni passo passo per scaricare gli edifici dai portali di Emilia-Romagna, Lombardia, Friuli Venezia Giulia, Liguria, Trento e Veneto (pagina, strati, formato, sistema di riferimento, licenza, limiti) e stato delle altre regioni | — | — | pagina di testo |
| **Importa DXF/IFC** | `importa-dxf-ifc.html`, `?lat=…&lon=…&z=…` | Aprire un disegno DXF o un modello BIM IFC: corpi, altezze e falde ricavati **nel browser**, posa dal file, da un sistema di riferimento o con due punti; il risultato si apre in Modelli 3D | file DXF/IFC (oltre ~30 MB si converte sul PC) | modello in Modelli 3D; `.geojson` | sperimentale |
| **Visure** | `visure.html` | Descrive **EuGEnio Visure**, programma che gira sul PC (Windows `.exe`, Docker, `python -m visure`) e legge le visure catastali in PDF che la persona ha già | — | — | in sviluppo (lettore pronto, provato su visure sintetiche; programma per Windows da pubblicare) |

Formato del file del Patrimonio: CSV (`;` o `,`, UTF-8 o codifica di Windows), `.xlsx` o `.ods`; una riga per edificio,
al massimo 500 righe per caricamento (la pagina manda i file grandi a blocchi di 40 righe). Serve **almeno una** di
queste informazioni, in ordine di affidabilità: `lat` e `lon`; `comune`, `foglio`, `particella` (o `mappale`) [, `sezione`];
`indirizzo` [, `civico`], `comune`. Facoltative: `id`, `denominazione` (e qualunque altra colonna, riportata in uscita);
per le pagine dell'edificio anche `piani_fuori_terra`, `piani_interrati`, `superficie_lorda`, `superficie_netta`,
`superficie_catastale`, `anno_costruzione`. Nomi alternativi riconosciuti (per esempio `latitudine`, `via`, `mappale`,
`fg`, `nome`, `codice`, `SLP`). Esempio (`esempi/patrimonio_esempio.csv`):

```
id;denominazione;indirizzo;civico;comune;foglio;particella;lat;lon
H01;Ospedale Santa Maria delle Croci;Viale Vincenzo Randi;5;Ravenna;;;;
H06;Ospedale Marconi;;;Cesenatico;22;111;;
H08;Ospedale Nefetti;;;;;;43.942496;11.901527
```

Scheda «Valori per sede»: le colonne in più del file (per esempio `Energia elettrica 2025`, `Costo gas 2025`) diventano
valori da disegnare; una **seconda riga facoltativa con le unità** (`kWh`, `Smc`, `€`…). Esempio:
`esempi/valori_sedi_esempio.csv` (valori inventati). Colonne in uscita principali: `lat`, `lon`, `fonte_punto` (`ANNCSU`,
`Zornade`, `coordinate`, `catasto`), `indirizzo_trovato`, `istat`, `belfiore`, `foglio_catasto`, `mappale`, `esito`, `nota`.

### Edifici e Fotovoltaico (in lavorazione: non accessibili dal menu; pagine 3D, stessi parametri di Modelli 3D: `?edificio=ID&lon=…&lat=…`, `?archivio=…`, `?sede=locale`, `?dbtr=locale`)

**Stato dall'08/11/2026 (decisione di Paolo)**: tutte le pagine di questi due gruppi sono **in lavorazione, non
accessibili**: nel menu la voce ha il triangolo giallo e non è cliccabile, nessuna pagina del sito le collega, si aprono
solo con l'indirizzo diretto e mostrano in cima «Pagina in lavorazione, non ancora verificata». I risultati non sono
verificati: un agente non le usa per conto di una persona né le indica come servizi disponibili (per edificio, ombre e
fotovoltaico si usa Modelli 3D, gruppo Patrimonio). Il gruppo si chiama **Edifici** (prima «Edificio»); gli indirizzi delle
pagine non cambiano. Descrizione tecnica (per quando saranno aperte):

Dal 07/11/2026 sera queste pagine funzionano **come Modelli 3D**: mappa 2D con la ricerca (indirizzo o foglio e particella)
e il clic sull'edificio, poi «Genera il 3D»; stessi archivi DBTR per comune, stesso ripiego OpenStreetMap fuori dal DBTR,
stessi edifici del DB topografico caricato nel browser (nella stessa scheda), terreno dal server. Cambia solo il passo in
evidenza nel pannello di destra. `?edificio=ID` va insieme a `lon` e `lat` del punto (senza, si cerca vicino al primo
archivio). La demo sintetica solo con `?archivio=demo`.

**Forma dei tetti a scelta** (08/11/2026): nel passo «Corpi › Falde dei tetti» il selettore «Forma dei tetti» (`#forma-tetti`)
con «Misurata (LiDAR) dove c'è», «Stimata dal colmo DBTR dove c'è», «Ipotesi automatica (22°/32°)», «Tutti piani»; le scelte
che per l'edificio non ci sono restano spente con il motivo; predefinita la più affidabile disponibile. Le prime due
scendono la cascata dove manca la fonte (LiDAR → colmo → ipotesi). Cambiando scelta si ricalcolano tetti, aree FV (salvo
inclinazione e orientamento corretti a mano), ombre, producibilità e sole sulle facciate; la scelta è scritta nei risultati
e nel report (`tetti: {scelta, testo, conteggi}`). In Modelli 3D non c'è selettore: vale la cascata.

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
Gruppo **Edifici** (in quest'ordine nel menu):

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
| `edificio-obblighi.html` – Obblighi di legge | potenza minima di rinnovabili (D.Lgs. 199/2021), S/V, zona, limite di H'T del DM requisiti minimi | edificio | in lavorazione, non accessibile |
| `edificio-geometria.html` – Geometria e luce naturale | volume, superfici, S/V, pareti esposte e in comune, cielo visto | edificio | in lavorazione, non accessibile |
| `edificio-consumi.html` – Consumi, firma energetica e priorità | consumi al m² e al m³, firma energetica con i gradi giorno reali del comune, classifica delle sedi | consumi mensili, una riga per mese: `AAAA-MM;valore` | in lavorazione, non accessibile |
| `edificio-fabbisogno.html`, `edificio-involucro.html`, `edificio-impianti.html` | fabbisogno con le metodiche UNI, facciate e tetti, pompe di calore e solare termico (segnaposto: «analisi non disponibile in questa installazione», modulo UNI non pubblico) | — | in lavorazione, non accessibile |
| `edificio-ecobonus.html` – Ecobonus | segnaposto: prima verifica degli interventi con la detrazione Ecobonus | — | in lavorazione, non accessibile |
| `edificio-conto-termico.html` – Conto Termico | segnaposto: prima verifica degli interventi con l'incentivo del Conto Termico (GSE) | — | in lavorazione, non accessibile |

Gruppo **Fotovoltaico**:

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
| `fv-ombre.html` – Ombre e percorso del sole | ombre degli edifici vicini, ora per ora | edificio, giorno, ora | in lavorazione, non accessibile |
| `fv-irradiazione.html` – Sole e irradiazione su tetti e facciate | irradiazione annua e stagionale con ombre e orizzonte fino a 25 km | edificio | in lavorazione, non accessibile |
| `fv-producibilita.html` – Producibilità con le ombre | producibilità FV dei tetti con il clima orario del comune | aree FV disegnate o proposte, kWp, inclinazione, orientamento | in lavorazione, non accessibile |
| `fv-pvgis.html` – Confronto con PVGIS | producibilità di EuGEnio accanto a PVGIS con lo stesso orizzonte | come sopra | in lavorazione, non accessibile |
| `fv-dlgs199.html` – D.Lgs. 199/2021, Allegato III | potenza minima da rinnovabili per nuove costruzioni e ristrutturazioni, confrontata col FV possibile | edificio | in lavorazione, non accessibile |
| `fv-leed.html` – Prefattibilità LEED | quali informazioni utili a LEED dà EuGEnio, tema per tema (descrittiva, nessun testo LEED) | — | in lavorazione, non accessibile |
| `edificio-cer.html` – Comunità energetiche (indirizzo invariato; fino al 07/11/2026 nel gruppo Edificio) | energia condivisa ora per ora per cabina primaria (solo energia, niente prezzi né incentivi) | CSV lungo `ora;sede;cabina;prelievo;immissione` in kWh (esempio `esempi/cer_esempio_sintetico.csv`); il codice della cabina lo scrive la persona | in lavorazione, non accessibile |
| `fv-mercato.html` | analisi di mercato su prezzi GME | — | **GME**: segnaposto |

Le altezze dell'archivio sono approssimate (circa ±3 m): piani, superfici, ombre e producibilità sono stime.

### Cogenerazione

| Pagina | A cosa serve | Stato |
|---|---|---|
| `cog-emissioni.html` – Emissioni | CO₂ evitata o aggiunta dal cogeneratore rispetto a rete elettrica e caldaia, con i fattori ISPRA; calcolo nel browser; ingressi: dati misurati di un anno (MWh elettrici, MWh termici, gas in MWh PCI o Sm³) oppure taglia, ore e rendimenti | in lavorazione, non accessibile (dall'08/11/2026) |
| `cog-spark-spread.html`, `cog-simulazione.html`, `cog-confronto.html`, `cog-rischio.html`, `cog-car.html` | analisi economiche su prezzi di mercato | **GME**: segnaposto |

### Statistiche

| Pagina | URL e parametri | A cosa serve | Stato |
|---|---|---|---|
| **Costi energetici Sanità** | `indicatori.html`, `?regione=RR`, `&ente=CE-COD` (per esempio `?regione=08&ente=080-101`, Azienda USL Piacenza; `080-999` = consolidato regionale) | spesa per energia degli enti del Servizio Sanitario Nazionale dal 2015, a confronto con regione e Italia, per giornata di degenza, posto letto, cittadino | attiva |

### Altre pagine

`metodo.html` (Come funziona: modello, fonti meteo, correzione ERA5, limiti; `#fonti`), `faq.html` (F.A.Q.; questo file è
spiegato in `#agenti-ai`), `sitografia.html` (progetti e dati usati), `mirror.html` (come installare una copia),
`licenza.html` (`#dati` per la CC BY), `privacy.html`, `contatti.html`, **`novita.html`** (Novità: cosa cambia a ogni
pubblicazione, dalla più recente; ancora per data, `#d<aaaammgg>`, per esempio `#d20261107`, e `#d20261107-2` per la seconda voce dello stesso giorno) con il feed Atom **`novita.xml`**
(per sapere se il servizio è cambiato dall'ultima volta basta leggere la prima `entry`). Newsletter mensile dei dati:
`https://notizie.statocritico.it/subscription/form` (l'iscrizione la fa la persona, non l'agente).

## 4. API pubbliche

Base: `https://eugenio.statocritico.it`. Tutte le risposte sono JSON (salvo i file). Errori: JSON `{"detail": "messaggio
in italiano"}`. Schema OpenAPI completo: **`/api/openapi.json`**, pagina interattiva **`/api/docs`**.

Nelle prove con curl usa sempre un **User-Agent identificabile** con un contatto, per esempio:

```bash
UA='MioAgente/1.0 (per conto di un utente; contatto: nome@esempio.it)'
curl -sS -A "$UA" https://eugenio.statocritico.it/api/salute
```

Legenda: **libera** = un agente può chiamarla direttamente; **Turnstile** = serve il gettone di sessione ottenuto da una
verifica anti-robot fatta in un browser vero (§ 5): un agente senza browser **non può** usarla in automatico.

### 4.1 Servizio e comuni

| Metodo e percorso | Accesso | Cosa restituisce |
|---|---|---|
| `GET /api/salute` | libera | `{"stato": "ok", "previsioni": {…ultimo aggiornamento…} \| null, "modello_caricato": bool, "previsioni_in_corso": n}` |
| `GET /api/protezione` | libera | `{"turnstile": chiave pubblica \| null, "intestazione": "X-EuGEnio-Sessione", "minuti": 30, "rotte": ["previsione", "patrimonio", "geocodifica", "particella", "estrazione"]}` |
| `POST /api/sessione` | solo browser | corpo `{"token": "<gettone Turnstile>"}` → `{"sessione": "…", "scade": epoch}` |
| `GET /api/comuni` | libera | elenco dei comuni con meteo: `[{"istat": "099014", "nome": "Rimini", "belfiore": "H294", "provincia": …, "lat": …, "lon": …, "svg_x": …, "svg_y": …}, …]` |
| `GET /api/mappa?giorni=7` | libera | gradi giorno previsti (base 20 °C), gradi giorno estivi (base 24 °C) e temperatura media dei prossimi `giorni` (1–15) per comune: `{"giorni": 7, "comuni": {"099014": {"t": 9.8, "gg": 71.4, "gc": 0.0}, …}}` |
| `GET /api/metodologia` | libera | metriche della correzione ERA5 → ICON e dei modelli meteo |

### 4.2 Meteo, clima e Legge 10

| Metodo e percorso | Accesso | Parametri | Risposta (estratto) |
|---|---|---|---|
| `GET /api/meteo/{istat}` | libera | `modalita=breve` (orario: ultimi `giorni` ≤ 90 osservati + previsione) o `modalita=lungo` (giornaliero, ultimi `giorni` ≤ 3650) | `{"storico": {"t": [...], "temperature_2m": [...], …}, "previsione": {…}}` (orari in Europe/Rome, ISO 8601) |
| `GET /api/clima-previsto/{istat}` | libera | `modalita=breve\|lungo`, `orizzonte` (ore 1–360 o giorni 1–365), `covariate` separate da virgola: orarie `temperatura, umidita, radiazione, diffusa, vento, nuvolosita, pioggia, neve`; giornaliere anche `gradi_giorno, gradi_raffrescamento` | `{"solo_clima": true, "passo": "ora", "storico": {"t": [...]}, "previsione": {"t": [...], "fonte_meteo": ["ICON-2I", …]}, "clima": {"temperatura": {"unita": "°C", "storico": [...], "previsione": [...]}}, "avvisi": [...]}` |
| `GET /api/clima-legge10/{istat}` | libera | `anni` = stagioni complete da usare (3–30, predefinito 10) | `{"istat", "comune", "stagioni": [...], "mensili": [...], "gradi_giorno": {"zona_di_riferimento", "gg_periodo_zona", "gg_anno_intero", "zona_risultante", "per_stagione": {...}, "tendenza_gg_per_decennio", …}, "temperatura_progetto": {"invernale", "estiva", "metodo"}, "avvertenza", "fonte"}` |
| `GET /api/edifici/gradi-giorno/{istat}` | libera | `dal=AAAA-MM`, `al=AAAA-MM` | `{"mesi": [{"mese": "2025-01", "gg20": 512.3, "gc24": 0.0, "t_media": 4.1, "giorni": 31}, …], "fonte", "nota"}` (clima reale, **non** i valori di legge) |
| `GET /api/edifici/clima-orario/{istat}` | libera | `anno=AAAA` (se manca, l'ultimo completo) | un anno orario UTC: `{"anno", "inizio", "passo_ore": 1, "ghi": [...], "dhi": [...], "t": [...], "vento": [...], "fonte"}` (W/m², °C, km/h) |

Esempi:

```bash
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-legge10/099014?anni=10"
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-previsto/099014?modalita=lungo&orizzonte=30&covariate=temperatura,gradi_giorno"
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/edifici/gradi-giorno/099014?dal=2024-07&al=2025-06"
```

### 4.3 Previsione dei consumi

| Metodo e percorso | Accesso | Parametri (multipart/form-data) |
|---|---|---|
| `POST /api/previsione` | **Turnstile** | `file` (CSV/xlsx/ods, formato del § 3), `istat`, `modalita=breve\|lungo`, `orizzonte` (ore ≤ 360 o giorni ≤ 365), `tipo=energia\|potenza`, `covariate` (come sopra), `verifica=true\|false` |

Risposta: `{"modalita", "passo", "istat", "covariate": [...], "storico": {"t": [...], "v": [...]}, "previsione": {"t": [...],
"0.1": [...], …, "0.5": [...], …, "0.9": [...], "fonte_meteo": [...]}, "avvisi": [...], "clima": {…}}`; con `verifica=true`
anche `"verifica": {"reale", "mae", "wape", "bias", "copertura_80"}`. La mediana è il quantile `0.5`; tra `0.1` e `0.9` c'è
l'80 % di probabilità. Oltre 72 ore il meteo viene dal modello globale IFS; oltre 15 giorni dalla climatologia (scenario
«anno tipo»). **Un agente senza browser non può chiamarla**: prepara il file e fai caricare il file alla persona nella pagina.

### 4.4 Dati climatici scaricabili

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/storici/catalogo` | libera | dataset presenti, grandezze, frequenze, periodi, fonti, licenze, limiti, elenco dei dati **non** scaricabili |
| `POST /api/storici/stima?formato=csv\|xlsx\|ods` | libera | righe e dimensione stimate per una selezione, `consentito` sì/no e suggerimenti per ridurla |
| `POST /api/storici/estrai?formato=csv\|xlsx\|ods` | **Turnstile** | il file (CSV in streaming; Excel e ODS con il foglio «Info») |

Corpo JSON di stima ed estrazione:

```json
{"dataset": "gradi_giorno", "variabili": ["gg20", "gc24"], "dal": "2024-07-01", "al": "2025-06-30",
 "frequenza": "mensile", "copertura": 90,
 "area": {"tipo": "comuni", "comuni": ["099014", "037006"]}}
```

`area.tipo`: `tutti`, `regione` (con `"regione": "08"`), `provincia` (con `"provincia"`: codice ISTAT a 3 cifre),
`comuni` (con l'elenco), `solo_capoluoghi`: true/false. Per `legge10`: `stagioni` (3–30) e `tipologia` (`mensili`,
`riepilogo`, `stagioni`). Per `eurostat_pmi`: `tassazione` (`X_TAX`, `X_VAT`, `I_TAX`). Le grandezze valide di ogni dataset
sono nel catalogo. Qualsiasi nome che richiami dati di mercato, Zornade o ANNCSU risponde **403**.

```bash
curl -sS -A "$UA" -H "Content-Type: application/json" -X POST \
  "https://eugenio.statocritico.it/api/storici/stima?formato=csv" \
  -d '{"dataset":"gradi_giorno","variabili":["gg20"],"frequenza":"mensile","dal":"2024-07-01","al":"2025-06-30","area":{"tipo":"comuni","comuni":["099014"]}}'
```

### 4.5 Patrimonio, geocodifica, catasto

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `POST /api/converti` | libera | `file` (.xlsx o .ods) → `{"formato", "fogli": [...], "foglio_usato", "csv": "…"}` (primo foglio, separatore `;`); i CSV tornano come sono |
| `POST /api/patrimonio` | **Turnstile** | `file` (formato del § 3, ≤ 500 righe) → `{"riepilogo", "geojson", "righe": [...], "fonte", "fonte_url", "fonti"}` |
| `GET /api/geocodifica?q=…&comune=…` | **Turnstile** | `{"risultati": [{"etichetta", "lat", "lon"}], "fonte": "Dati elaborati da Zornade", "fonte_url"}` |
| `GET /api/particella?lat=…&lon=…` | **Turnstile** | `{"particella": {"id", "etichetta", "area_m2", "lat", "lon"}, "comune": {"belfiore", "nome", "istat", "disponibile"}, "fonte", "fonte_url"}` |

Queste rotte consumano la quota gratuita di Zornade condivisa da tutti gli utenti: **mai** usarle per estrazioni massive.

### 4.5 bis Edifici OpenStreetMap al volo (ripiego di Modelli 3D, 07/11/2026)

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/edifici/osm?lon=…&lat=…` | **Turnstile** | edifici OSM entro ~400 m dal centro della cella di 0,002° (~200 m) che contiene il punto, dall'API Overpass (istanza principale overpass-api.de, riserva europea Overpass API Europa): FeatureCollection WGS84 con le proprietà delle celle di contesto (`id`, `edificio`, `gronda`, `altezza`, `fonte_sagoma`, `fonte_altezza`, `licenza: "ODbL 1.0"`, `qualita`: `"stima"` dove l'altezza è stimata, `origine_altezza`: `osm_height` (tag height), `osm_piani` (building:levels × 3 m), `dbtr_vicini` (mediana dei corpi DBTR entro 200 m, almeno 3) o `fissa` (9 m)) e `licenza`, `attribuzione`, `scheda`, `nota`, `centro`, `raggio`, `altezze` (conteggi per origine), `altezze_stimate`, `altezze_osm`, `data`; solo Italia (400 fuori); 404 se il ripiego è spento sul server; 502/503 se Overpass non risponde o è sovraccarico |

**Sagome regionali al volo** (08/11/2026): dove la Regione pubblica le sagome aperte e senza altezze con un WFS (oggi il
**Veneto**, «Edifici del Veneto (feb. 2022)», IODL 2.0) la stessa rotta risponde con le sagome della Regione e, per ognuna,
l'altezza dell'edificio OSM che le si sovrappone di più (height, poi piani × 3 m), altrimenti la mediana dei corpi DBTR
vicini (`dbtr_vicini`) o dei vicini con l'altezza OSM (`osm_vicini`), altrimenti 9 m (`fissa`); in più `sagome` (regione,
nome, licenza, attribuzione, scheda, corpi, `con_altezza_osm`, `osm_aggiunti`), `quote_dtm` (corpi con `quota_terreno`
dal DTM del server; dal 09/11/2026 b, dove non c'è un DTM regionale, dal Copernicus DEM 90 m, anche per gli edifici OSM senza sagome regionali; `quote_fonte`: `dtm`, `copernicus` o `dtm+copernicus`) e, se il WFS non risponde, `avviso_sagome` con i soli edifici OSM. Proprietà per corpo in più:
`regione_sagoma`, `uso`, `codice_uso`, `codice_tipo`, `osm_id`. Intestazione `X-Licenza: IODL 2.0; ODbL 1.0`.

Serve alle pagine 3D **solo fuori dal DBTR**; le altezze stimate sono sempre dichiarate per corpo, in una nota sotto la
mappa, nell'immagine e nel report; consuma le quote di Overpass del server (una chiamata alla volta per
tutto il sito, tetto orario, copia per cella di 30 giorni): **mai** usarla per scaricare zone. Per dati OSM in quantità
si usano gli estratti di OpenStreetMap (Geofabrik) o Overpass direttamente, con le loro regole d'uso.

### 4.6 Ortofoto, strati, terreno, orizzonte, PVGIS

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/ortofoto/fonti` | libera | fonti accese con `id`, nome, licenza, citazione, stato, zoom, riquadro, `tessere`, `spostabile` e `spostamento_max` (m) |
| `GET /api/ortofoto/{fonte}/{z}/{x}/{y}.{ext}` | libera, con limite | tessera 256×256 in EPSG:3857 (XYZ); `ext` = estensione della fonte (`jpg`); 404 fuori zona o fuori zoom; per la RER 2023-24 (dal 07/11/2026 sera) JPEG se la tessera è piena, **PNG con trasparenza** dove la fonte non ha dati (l'indirizzo pubblicato in `tessere` ha `?t=1`); dal 09/11/2026 `X-Ortofoto-Vuota: 1` se la tessera è tutta trasparente (la RER 2023-24 non ha immagini a Bologna, Modena, Parma, Imola, Ferrara, Faenza, Bagno di Romagna, Comacchio: usa un'altra fonte); le fonti solo dal vivo (AGEA 2012) hanno `Cache-Control: private, max-age=86400`; dal 09/11/2026 b le fonti con tessere **segnaposto** fuori dalla loro regione (la Toscana risponde con un'immagine bianca e la scritta «Fonte dei dati: Regione Toscana…», per esempio a Bagno di Romagna o a Bologna) danno al loro posto un PNG trasparente con `X-Ortofoto-Vuota: 1` (indirizzo pubblicato in `tessere` con `?s=1`). **`?de=<m>&dn=<m>`** (dall'08/11/2026, interi da −20 a 20, solo fonti con `spostabile: true` in `/fonti`, cioè WMS): ortofoto spostata di `de` m verso est e `dn` m verso nord rispetto alla cartografia (il proxy chiede alla fonte il riquadro spostato in EPSG:3857, nessuna copia su disco, intestazione `X-Ortofoto-Spostamento`); 422 fuori dai limiti, 400 per le fonti a tessere già pronte (Sentinel-2). Serve alle frecce sotto la mappa: non per scaricare zone |
| `GET /api/ortofoto/strati` | libera | strati accesi: `catasto` (particelle AdE), `dbtr_edifici`, `osm_edifici` |
| `GET /api/ortofoto/strati/{sid}/{z}/{x}/{y}.{ext}` | libera, con limite | PNG trasparente (zoom 16–20) o, per `osm_edifici`, GeoJSON delle sagome a zoom 16 (`.json`) |
| `GET /api/terreno/fonti` | libera | DTM del server per il terreno 3D (riquadro, licenza, attribuzione), zoom e ripiego (Copernicus DEM 90 m) |
| `GET /api/terreno/{z}/{x}/{y}.png` | libera, con limite | tessera 256×256 del terreno in codifica Terrarium (quota = R·256 + G + B/256 − 32768 m), EPSG:3857 (XYZ), zoom 8–15; DTM regionale 5 m dove c'è (dall'08/11/2026 **più DTM insieme**, il più dettagliato prima: Emilia-Romagna, Veneto dove è sul server), altrimenti Copernicus DEM (intestazioni `X-Terreno-Fonte` e `X-Terreno-Nome` con il nome del DTM); 404 fuori dall'Italia. Serve alla vista 3D: le quote dei corpi degli edifici sono già nei corpi |
| `GET /api/edifici/orizzonte?lat=…&lon=…&h=…&direzioni=72` | libera, con limite | orizzonte del terreno fino a ~25 km dal Copernicus DEM: `{"angoli": [...], "distanze_km": [...], "quota_dem", "raggio_km", "fonte"}`; `direzioni` ∈ 36, 72, 120, 360; solo Italia |
| `POST /api/edifici/pvgis` | libera, con limite | confronto con PVGIS (JRC) per 1–12 aree; corpo sotto |

```json
{"lat": 44.0594, "lon": 12.5683,
 "aree": [{"id": "tetto-sud", "kwp": 20, "inclinazione": 15, "orientamento": 180, "perdite": 14,
           "orizzonte": [2.1, 3.0, 4.5, 5.0, 3.2, 1.0]}]}
```

`orientamento` in gradi da nord (180 = sud); `orizzonte` = angoli in gradi da nord in senso orario, passo costante.
Risposta: per area `con_orizzonte` e `senza_orizzonte_utente` con `kwh_anno`, `kwh_mensili`, `irradiazione_piano`,
`banca_dati`, `anni`. Le tessere sono pensate per la mappa del sito: **non scaricare intere zone** di ortofoto, strati o
terreno.

### 4.7 Report e analisi

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/report/schema` | libera | schema JSON del documento generico |
| `POST /api/report?formato=pdf\|xlsx\|ods` | libera | documento generico (JSON secondo lo schema) → file |
| `POST /api/report/{tipo}?formato=pdf\|xlsx\|ods` | libera | report di un servizio dalla **risposta JSON già ottenuta**: `tipo` = `previsione`, `legge10`, `patrimonio` (`{"righe": [...], "fonti": [...]}`), `indicatori`, `valori_sedi`, `edificio` |
| `GET /api/analisi/stato` | libera | analisi avanzate disponibili su questo server (oggi tutte «analisi non disponibile in questa installazione») |
| `POST /api/analisi/{id}` | libera | esegue un'analisi se disponibile; altrimenti 503 |

Word (docx) e ODT rispondono **410**. Corpo ≤ 5 MB. Esempio, PDF della Legge 10:

```bash
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-legge10/099014" -o l10.json
curl -sS -A "$UA" -H "Content-Type: application/json" -X POST --data @l10.json \
  "https://eugenio.statocritico.it/api/report/legge10?formato=pdf" -o legge10_rimini.pdf
```

### 4.8 Codici di risposta

| Codice | Significato |
|---|---|
| 200 / 304 | ok (le tessere usano ETag) |
| 400 | richiesta malformata (formato o tipo di report sconosciuto, corpo vuoto) |
| 401 | manca la sessione anti-robot (intestazione `X-EuGEnio-Verifica: 1`): serve il browser |
| 403 | dato non scaricabile (mercato, Zornade, ANNCSU) o verifica non superata |
| 404 | comune non disponibile, tessera fuori zona, analisi sconosciuta |
| 410 | formato spento (docx, odt) |
| 413 | file o richiesta troppo grandi (riduci periodo, area o righe: la stima dice come) |
| 422 | dati non validi (messaggio in italiano: leggilo e correggi) |
| 429 | limite orario superato per la tua rete: **aspetta** i secondi di `Retry-After` (dal 09/11/2026; `X-EuGEnio-Limite` dice quale limite), non ritentare a raffica |
| 502 | la fonte esterna (ortofoto, PVGIS, Zornade) non risponde |
| 503 | dati non ancora sul server, server occupato (previsioni, file), quota di Zornade dell'ora esaurita, fonte molto richiesta (con `Retry-After`) |

### 4.5 ter Proposte di DB topografici all'archivio comune («Aggiungi DBTR», 07/11/2026)

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `POST /api/dbtr/inizia` | **Turnstile**; 3 file al giorno per rete | JSON `regione` (`er`, `lom`, `fvg`, `lig`), `comune` (nome), `istat` (6 cifre, facoltativo), `intero` (comune intero), `formato` (`zip` o `gpkg`), `dimensione` (byte, al massimo 300 MB), `consenso: true` (obbligatorio), `impronta` (SHA-256 del file, facoltativa) → `id`, `gettone`, `pezzo_byte`, `pezzi`; 503 se la coda è piena |
| `PUT /api/dbtr/{rid}/pezzo/{n}` | gettone in `X-EuGEnio-Dbtr` | pezzo `n` del file nel corpo della richiesta (32 MB, l'ultimo più corto) |
| `POST /api/dbtr/{rid}/fine` | gettone | chiude il caricamento: impronta, controllo leggero (zip senza percorsi «..», link simbolici, bombe di compressione; o GeoPackage) → `stato: "ricevuto"`; 422 e file cancellato se rifiutato |
| `GET /api/dbtr/{rid}` | gettone (intestazione o `?g=`) | stato della proposta: `ricevuto`, `in preparazione`, `in attesa di approvazione`, `controlli non superati`, `approvato`, `installato`, `rifiutato`, con un messaggio |
| `DELETE /api/dbtr/{rid}` | gettone | ritira la proposta prima dell'approvazione (file cancellati) |

Il caricamento è un'azione **della persona**, con il suo consenso esplicito: un agente non la fa da solo né la ripete in
serie. Il server prepara una proposta alla volta, a bassa priorità; l'archivio comune cambia **solo dopo l'approvazione**
nella pagina interna di Stato Critico (non pubblica). Nessun dato personale richiesto. La lettura
nel browser (senza server) resta sempre possibile.

## 5. Limiti e protezioni (cosa un agente può e non può fare)

- **Limiti per rete in finestra mobile di un'ora** (IPv4 per indirizzo, IPv6 per rete /64), valori predefiniti: rotte dei
  dati (comuni, mappa, meteo, clima, Legge 10, gradi giorno, catalogo delle ortofoto e degli strati, analisi) **600**
  richieste; previsioni **20**; conversioni **200**; report **60**; stime di Dati climatici **600**; download di Dati
  climatici **30**; edifici geolocalizzati **2.000**; ricerche Zornade **120**; dal 09/11/2026 tessere di ortofoto
  **12.000** e di particelle e contorni **12.000** chieste alla fonte, tessere del terreno da generare **6.000**, tessere già
  in copia sul server **60.000** (tetto comune); confronti PVGIS **60**; profili d'orizzonte **120**; edifici OpenStreetMap al
  volo **300** richieste che chiamano Overpass (comprese le tessere OSM dei contorni) e **3.000** dalla copia; verifiche anti-robot **60**;
  proposte di DB topografici **3 al giorno** (finestra di 24 ore) e **60 pezzi all'ora**.
  Oltre: **429** con `Retry-After` (secondi finché si libera il 10 % del limite) e `X-EuGEnio-Limite` (il tipo).
- **Cloudflare** ferma le raffiche su `/api/` (circa 60 richieste in 10 secondi per IP, blocco breve; le ortofoto escluse).
- **Tetti per tutto il sito**: due previsioni alla volta (le altre aspettano fino a 30 s, poi 503); due report e due file di
  Dati climatici alla volta; quota oraria di Zornade condivisa (oltre: 503); ritmo verso le fonti di ortofoto e verso PVGIS;
  edifici OpenStreetMap: una chiamata a Overpass alla volta e al massimo 300 all'ora per tutto il sito (oltre: 503).
- **Verifica anti-robot (Cloudflare Turnstile)** sulle rotte che costano o consumano quote: `previsione`, `patrimonio`,
  `geocodifica`, `particella`, `estrazione`, `edifici_osm`, `dbtr` (cioè `POST /api/previsione`, `POST /api/patrimonio`,
  `GET /api/geocodifica`, `GET /api/particella`, `POST /api/storici/estrai`, `GET /api/edifici/osm`, `POST /api/dbtr/inizia`). La pagina ottiene un gettone Turnstile nel browser, lo scambia con
  `POST /api/sessione` e manda la sessione (30 minuti, legata alla rete) nell'intestazione `X-EuGEnio-Sessione`.
  **Un agente non deve aggirarla** (niente risolutori di captcha, niente riuso di gettoni altrui): o guida la persona a
  usare la pagina, o lavora in un browser che la persona controlla e vede, oppure usa un proprio **mirror** (§ 7), dove
  la verifica è spenta.
- **Pagine che richiedono un browser**: Previsioni (caricamento), Patrimonio, Modelli 3D e tutte le pagine 3D (WebGL),
  Ortofoto, Importa DXF/IFC, Aggiungi edifici (DB topografico), Cambiamento climatico, Costi energetici Sanità e le pagine in lavorazione (calcoli nel
  browser). Le rotte libere del § 4 bastano per meteo, clima, Legge 10, gradi giorno, stime, orizzonte, PVGIS e report.
- **Cache**: le tessere di ortofoto e strati hanno `Cache-Control: public` e `ETag` (usa `If-None-Match`); orizzonte e
  PVGIS sono tenuti in copia dal server (stesso punto, nessuna nuova chiamata). Le previsioni meteo cambiano più volte
  al giorno; lo storico una volta al giorno (per i comuni delle regioni che il server aggiorna ogni giorno; per gli altri
  comuni serviti lo storico può fermarsi a una data precedente e la previsione usa la climatologia: le date nella risposta
  lo dicono). **Tieni tu una copia** delle risposte che riusi, invece di richiederle.
- **Uso cortese**: User-Agent identificabile con un contatto; richieste in serie, non in parallelo; pause di almeno un
  secondo tra le chiamate pesanti; niente scraping massivo di pagine, tessere o comuni (per molti comuni usa
  `POST /api/storici/stima` ed `estrai` con un'area, o i CSV nazionali del § 9); rispetta 429 e `Retry-After`; non usare EuGEnio come
  intermediario gratuito verso Zornade, PVGIS o le fonti di ortofoto.

## 6. Flussi tipici, passo passo

**A. Previsione dei consumi di un edificio a Rimini da un CSV orario**
1. Controlla che il comune ci sia: `GET /api/comuni` → Rimini `099014`.
2. Prepara il file: due colonne, `data;kWh`, una riga per ora (o per quarto d'ora), almeno qualche settimana di storia
   (fino a 90 giorni usati), date `GG/MM/AAAA hh:mm` o ISO, ora italiana.
3. La persona apre `https://eugenio.statocritico.it/`, sceglie Rimini sulla mappa, carica il file, sceglie «energia per
   intervallo», «Prossimi giorni, ora per ora», l'orizzonte (per esempio 72 ore) e «Calcola la previsione» (la verifica
   anti-robot è di solito invisibile).
4. Per giudicare l'affidabilità: modo «Mettila alla prova sull'ultimo periodo» (`verifica`), che dà MAE, WAPE, bias e
   copertura dell'intervallo 80 %.
5. Scarica il report (PDF) o i dati (Excel/ODS) dalla pagina; cita «Fonte: EuGEnio – eugenio.statocritico.it» e Open-Meteo.

**B. Dati climatici per la Legge 10 di un comune**
1. Trova il codice ISTAT (`GET /api/comuni`).
2. `GET /api/clima-legge10/{istat}?anni=10` (o 5, 30).
3. Confronta con i valori di legge in `dati/dpr412.json` (gradi giorno, zona, altitudine dell'Allegato A del DPR 412/93).
4. PDF: `POST /api/report/legge10?formato=pdf` con la risposta del passo 2. Link per la persona:
   `https://eugenio.statocritico.it/legge10.html?comune=<istat>`.
5. Ricorda alla persona che nella relazione tecnica restano obbligatori i valori normativi (UNI 10349, DPR 412/93).

**C. Solo clima (nessun file)**: `GET /api/clima-previsto/{istat}?modalita=breve&orizzonte=72&covariate=temperatura,radiazione,umidita`
(prossime ore) o `modalita=lungo&orizzonte=90` (prossimi giorni, con la climatologia oltre il 15° giorno). Nella pagina:
Previsioni → «Solo il clima, senza consumi».

**D. Gradi giorno**: mensili reali di un comune con `GET /api/edifici/gradi-giorno/{istat}?dal=…&al=…`; per più comuni o
frequenze diverse `POST /api/storici/stima` con il dataset `gradi_giorno` e poi la pagina `dati.html?dataset=gradi_giorno`
(il download chiede la verifica); serie dal 1940 per stagione: `dati/clima_stagioni.csv`. Sono gradi giorno dal clima reale
(base 20 °C su tutto l'anno; estivi base 24 °C); quelli **di legge** sono in `dati/dpr412.json` e nel dataset `dpr412`.

**E. Patrimonio con geolocalizzazione**
1. Prepara il CSV del § 3 (coordinate, oppure foglio e particella, oppure indirizzo e comune; meglio un `id` stabile).
2. Se è un Excel, va bene così: la pagina lo converte (`/api/converti`).
3. La persona lo carica in `patrimonio.html`: la pagina lo manda a blocchi, mostra gli esiti, permette di scaricare CSV e
   GeoJSON. Le righe `verificare` e `non_trovato` vanno controllate a mano (la colonna `nota` dice il motivo).
4. Per i valori di ogni sede (consumi, costi) usa la scheda «Valori per sede» (`patrimonio.html#valori`).
5. Cita ANNCSU e, per le particelle, «Dati elaborati da Zornade» con il collegamento.

**F. Modello 3D e producibilità FV di un edificio** (dall'08/11/2026 i passi 2–4 usano pagine **in lavorazione, non
accessibili**: per ora si resta in Modelli 3D, che ha anch'essa ombre, fotovoltaico, confronto con PVGIS e obblighi)
1. `modelli3d.html`: cerca l'indirizzo (esempio «viale Ghirotti 286», «Cesena»), fai clic sull'edificio, «Genera il 3D» (solo dove c'è un archivio di sagome:
   i comuni della Romagna preparati dal DBTR, elencati con il riquadro in `/edifici3d/archivi.json`; fuori zona la pagina
   lo dice). Un punto dentro un cortile non sceglie l'edificio da solo: trascina il punto sul corpo o fai clic. Per vedere il funzionamento:
   `modelli3d.html?archivio=demo` (edifici inventati: non usarli come risultati).
2. Correggi gronda, colmo, piani; poi `fv-producibilita.html` (stesso edificio): aree FV, kWp, inclinazione, orientamento.
3. Confronto: `fv-pvgis.html`, o direttamente `GET /api/edifici/orizzonte` + `POST /api/edifici/pvgis`.
4. Obblighi: `fv-dlgs199.html` ed `edificio-obblighi.html`. Ricorda che altezze e superfici sono stime.

**G. Importare un DXF/IFC**: `importa-dxf-ifc.html?lat=…&lon=…&z=…`; il file resta nel browser; posa dal file, da un sistema
di riferimento (EPSG) o con due punti noti; «Apri in Modelli 3D» (passa per `modelli3d.html?modello=locale`) o scarica il
`.geojson`. File oltre ~30 MB: sul PC con `EuGEnioVisure.exe modello` o con `python -m edifici3d importa-modello` (fase 10).

**H. Visure catastali con EuGEnio Visure, in locale**
1. La persona scarica da sé le visure in PDF (area riservata dell'Agenzia delle Entrate o SISTER): EuGEnio non lo fa e
   non chiede credenziali.
2. Sul PC: `EuGEnioVisure.exe` (quando pubblicato) oppure, dal codice, `python -m visure leggi CARTELLA_VISURE
   --patrimonio patrimonio.csv --ordina` (cartella `fase11-visure`) o la pagina locale `python -m visure web`
   (`http://127.0.0.1:8770`, solo sul computer).
3. Risultati in `Visure_AAAA-MM-GG/`: `indice.csv`, `edifici_visure.csv` o `patrimonio_con_visure.csv` (colonne `visura_…`:
   piani, superficie catastale, categorie). Intestatari e codici fiscali **non** entrano nei file.
4. Caricarli in `patrimonio.html`, passo «Visure catastali»: l'abbinamento si fa nel browser.

**I. Costi energetici della sanità**: `indicatori.html?regione=08&ente=080-101`, oppure i file `dati/indicatori/indice.json`
(anni, voci di conto economico, fonti, citazione) e `dati/indicatori/RR.json` (enti della regione con le serie). Cita
OpenBDAP (RGS), ReportER e ISTAT, più EuGEnio.

## 7. Cosa EuGEnio non fa e non deve fare

- **Dati di mercato (GME, EEX)**: PUN, prezzi zonali, PSV, IGI, TTF, future, PFOR **non sono mai esposti** né scaricabili:
  sono solo per uso interno. Non cercarli nelle API, non provare nomi alternativi (risposta 403), non chiederli.
  Le pagine «GME» restano segnaposto finché non c'è una licenza scritta del GME.
- **Visure e persone**: è vietato usare i dati catastali per **re-identificare persone**. EuGEnio Visure toglie intestatari
  e codici fiscali; non chiedere né ricostruire chi possiede un immobile. Il sito non usa mai lo SPID della persona.
- **Norme UNI**: il modulo con le metodiche UNI non è pubblico; le analisi che lo richiedono dicono «analisi non
  disponibile in questa installazione». EuGEnio non pubblica prospetti o estratti di norme UNI, né testi LEED, né contenuti
  GSE (licenza incompatibile).
- **Zornade**: niente estrazioni massive tramite EuGEnio (la quota è condivisa e un abuso fa sospendere la chiave del
  servizio); i dati catastali non sostituiscono visure ed estratti ufficiali; il collegamento «Dati elaborati da Zornade»
  è obbligatorio.
- **Valori normativi**: EuGEnio non sostituisce UNI 10349, DPR 412/93, APE, progetti o diagnosi firmate.
- **Garanzie**: nessuna; servizio gratuito e sperimentale.
- **Uso intensivo**: per lavori grandi o ripetuti la strada giusta è un **mirror** (codice AGPL-3.0, istruzioni in
  `mirror.html` e nel repository): sul proprio server la verifica anti-robot è spenta e i limiti si scelgono.

## 8. Privacy, funzione per funzione

| Funzione | Cosa va al server di EuGEnio | Cosa resta nel browser o sul PC |
|---|---|---|
| Previsioni con file | il file dei consumi (elaborato in memoria e scartato) e il comune | — |
| Solo clima, Legge 10, gradi giorno, Dati climatici | solo comune e filtri | — |
| Patrimonio | il file degli edifici, a blocchi (indirizzi cercati nell'ANNCSU sul server, il resto e le particelle a Zornade, che riceve solo il testo dell'indirizzo, i dati catastali o le coordinate); scartato a fine elaborazione; le risposte di Zornade in una cache tecnica senza legame con chi ha cercato, cancellata dopo 12 mesi | colonne `visura_…` e valori per sede |
| Excel/ODS in qualunque pagina | il file, per la conversione in CSV (non salvato) | — |
| Ricerca di un luogo (Ortofoto, Modelli 3D) | indirizzo o foglio e particella, come Patrimonio | — |
| Ortofoto e strati | le coordinate delle tessere viste | — |
| Modelli 3D, Edificio, Fotovoltaico | comune (clima), punto (orizzonte), aree FV e punto (PVGIS, inoltrati al JRC); fuori dal DBTR il punto per gli edifici OpenStreetMap (all'API Overpass va solo il centro della cella di ~200 m, non il punto esatto; risposta in copia sul server per 30 giorni, senza legame con chi l'ha chiesta) e, in Veneto, il riquadro di ~800 m attorno allo stesso centro al servizio WFS della Regione del Veneto; per la firma energetica solo il periodo, non i consumi | consumi mensili, correzioni, modello importato |
| Importa DXF/IFC | nulla (solo le tessere della mappa) | il file DXF/IFC |
| Aggiungi edifici (DB topografico) | nulla, se la persona non spunta il consenso; con il consenso il file del DB topografico (nessun dato personale chiesto: solo comune e regione; conservato fino all'approvazione, poi parte dell'archivio pubblico CC BY, o cancellato al rifiuto o al ritiro) | il file e gli edifici ricavati (IndexedDB del sito, finché la persona non li toglie) |
| EuGEnio Visure | nulla: gira sul PC o sul server dell'ente | visure in PDF, risultati |
| Cambiamento climatico, Costi energetici Sanità (e le pagine in lavorazione Comunità energetiche ed Emissioni) | nulla dei dati della persona (si leggono file pubblici e l'elenco dei comuni) | curve orarie, firma, dati del cogeneratore |
| Report | i risultati da impaginare (generati in memoria, non salvati) | — |
| Contattaci | nulla: prepara l'email nel programma di posta | — |

Sempre: indirizzo IP e richieste nei registri del server per 14 giorni; contatori dei limiti in memoria. Dettagli:
`privacy.html`. Prima di caricare dati di altri (per esempio consumi di un'abitazione), l'agente ricorda alla persona che
deve avere il diritto di usarli.

## 9. File statici utili (si leggono senza API)

| File | Contenuto |
|---|---|
| `/dati/dpr412.json`, `/dati/dpr412.csv` | Allegato A del DPR 412/93 per codice ISTAT attuale: gradi giorno, zona, altitudine, note su fusioni |
| `/dati/clima_sintesi.csv` | clima dal 1940, una riga per comune (≈1 MB) |
| `/dati/clima_stagioni.csv` | gradi giorno e zona per comune e stagione dal 1940 (≈31 MB: scaricalo una volta sola) |
| `/dati/clima/regioni.json`, `/dati/clima/RR/ISTAT.json`, `/dati/clima/RR/ISTAT_mensili.json` | clima dal 1940 del comune (sintesi e mensili) |
| `/dati/indicatori/indice.json`, `/dati/indicatori/RR.json` | indicatori di spesa energetica della sanità |
| `/dati/ispra_fattori_emissione.json` | fattori di emissione ISPRA usati nella pagina Emissioni |
| `/esempi/*.csv` | file di esempio **inventati** (consumi, patrimonio, valori per sede, CER) |
| `/edifici3d/archivi.json` | archivi di edifici 3D presenti sul server, in ordine di affidabilità, con nome, licenza, attribuzione e riquadro (un archivio DBTR per comune in `/edifici3d/cc-by/er/<comune>/prodotti/`; PMTiles e celle di contesto letti dalla pagina); `lidar` indica l'archivio delle falde LiDAR (solo quando la pipeline ne ha scritto l'indice; dal 09/11/2026 b `lidar/indice.json` ha l'elenco `celle.falde` e `celle.alberi` delle celle di 0,01° che esistono, e la pagina chiede solo quelle: le altre darebbero 404); `archivi.json` e gli `indice.json` si riconvalidano sempre (`Cache-Control: no-cache` con ETag), i PMTiles restano in copia un giorno |
| `/llms.txt` | rimando breve a questo file |
| `/novita.html`, `/novita.xml` | registro delle versioni del sito (pagina e feed Atom, la voce più recente per prima) |

## 10. Contatti e segnalazioni

- Pagina **Contattaci**: `https://eugenio.statocritico.it/contatti.html` (prepara un'email per `eugenio@statocritico.it`).
- Privacy: `privacy@statocritico.it`.
- Errori nel codice o in questo file: **issue su GitHub** `https://github.com/statocritico/eugenio/issues`, con pagina o
  rotta, parametri, risposta ricevuta e data. Un agente può preparare il testo; l'invio lo fa la persona.

## 11. Da dove è ricavato questo file

Per aggiornarlo, rileggi: `fase4-server/servizio/app.py` e i router `storici.py`, `edifici.py`, `edifici_osm.py`, `ortofoto.py`, `strati.py`,
`pvgis.py`, `orizzonte.py`, `analisi.py` (rotte e parametri; `interno.py` è riservato e non va citato);
`fase4-server/servizio/protezione.py` e `config.py` (limiti, Turnstile); `modello.py` (CSV e risposta delle previsioni);
`report_servizi.py` (tipi di report); `fase7-territorio/territorio/patrimonio.py` (colonne del Patrimonio);
`fase5-sito/parti/testata.html` (menu e stati); `fase5-sito/sito/*.js` (parametri dell'indirizzo: `URLSearchParams`);
`fase5-sito/sito/privacy.html` e `licenza.html`; `fase10-edifici3d/ortofoto/*.toml` (fonti e citazioni); README delle
fasi 4, 5, 7, 10, 11, 12, 13. Il test `fase4-server/tests/test_agenti.py` controlla che le due copie siano identiche, che la
versione in testa sia quella del sito e che i percorsi `/api/…` citati qui e le rotte pubbliche dell'app coincidano.
