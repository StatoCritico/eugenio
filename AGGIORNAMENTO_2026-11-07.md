# Aggiornamento del 07/11/2026 – Modelli 3D corretti, DBTR vero dei comuni, ripiego OpenStreetMap, «Aggiungi DBTR», pagine 3D unificate, Novità e meteo nazionale a blocchi (sito `?v=20261107a`; correzioni dalle prove: `?v=20261107b`, sezione I)

Otto lavori (E è il terreno 3D dal server con la plausibilità delle altezze; F le pagine 3D unificate, le altezze OSM e la
riserva Overpass europea; G la pagina «Novità» con il feed Atom; H il giornaliero meteo nazionale a blocchi,
`REGIONI_AGGIORNATE` e il nuovo tentativo sulle risposte troncate di Open-Meteo, con i test della fase 4 tutti verdi),
pubblicati insieme con la **procedura F1–F23** in fondo (rigenerata il 07/11 sera), un solo zip (`eugenio_2026-11-07.zip`, il progetto intero senza fase 2, `uni_privato`, `.env` e dati DBTR)
e gli archivi degli edifici da copiare sul server (**19 tar, uno per comune**, in
`C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\`, **mai** nel clone né nel repository):

- **A – correzioni di Modelli 3D e Ortofoto** dopo le prove D16 del 06/11 sera (menu, Costi Sanità, Ortofoto e demo ok;
  Modelli 3D con cinque problemi, ora corretti);
- **B – archivio vero del DBTR del comune di Rimini** (estrazione del 05/11), più il codice per gli altri comuni
  scaricati il 06/11 (19 in tutto) e il DTM 5 m dai quadranti preconfezionati della Regione;
- **C – ripiego OpenStreetMap al volo** (decisione di Paolo del 07/11 mattina): fuori dal DBTR Modelli 3D usa gli edifici
  OSM intorno al punto, chiesti dal server all'API Overpass; **serve il rebuild dell'api** (rotta nuova `GET
  /api/edifici/osm`, `shapely` e `pyproj` nell'immagine);
- **D – «Aggiungi DBTR»** (decisione di Paolo del 07/11): pagina Patrimonio › **Aggiungi edifici (DB topografico)** che
  legge nel browser il DB topografico scaricato dal portale della Regione e lo usa in Modelli 3D solo per chi lo carica;
  con il consenso esplicito lo stesso file va in una **coda sul server**, preparata dal nuovo servizio `edifici-coda` e
  approvata (o rifiutata) nella pagina interna; pagina di istruzioni **Scaricare i DB topografici**. Serve: rebuild di
  api ed `energia-edifici`, Caddy ricreato (limite di 40 MB su `/api/dbtr/*`), cartella della coda, servizio acceso.

Online c'è `?v=20261106a` (o `?v=20261105b` se la procedura E del 06/11 non è stata fatta: in quel caso fai prima E1–E10 di
`AGGIORNAMENTO_2026-11-06.md`, poi questa).

## Cosa cambia

### A – Modelli 3D e Ortofoto

1. **Multipoligoni OSM con i cortili** (`fase10-edifici3d/edifici3d/osm_campione.py`): le relazioni `multipolygon`
   `building` si ricompongono anche con way `outer` aperte (polygonize), i fori `inner` restano, un pezzo per poligono
   (`r<id>_<k>`). Opzione `--dtm` di `osm-campione` per riusare `grezzi/dtm5.tif` (o un quadrante) senza chiamare il WCS.
2. **Cortili nella pagina** (`edificio3d.js`, `edifici_calcoli.js`): i corpi portano i fori (`buchi`); GeoJSON dell'edificio
   scelto e 3D con i cortili; un punto nel cortile non è «dentro» (distanza anche dai lati del cortile); area, volume,
   S/V, superfici e pareti del cortile uguali in JS e in Python (test di parità).
3. **Fuori zona**: «Il punto è fuori dalla zona coperta dall'archivio degli edifici («DBTR Emilia-Romagna – Rimini»): qui
   il 3D non si può ancora generare. Le zone coperte sono tratteggiate sulla mappa.» nei tre punti dove prima usciva
   «nessun edificio dell'archivio lo contiene (né entro 30 m)»; riquadri coperti tratteggiati, discreti, sulla mappa 2D.
4. **Zoom 17** dopo la ricerca, costante comune `EUGENIO_CERCA.ZOOM` in `cerca_luogo.js`, usata da Ortofoto e Modelli 3D.
5. **Livelli della mappa** nella colonna destra di Modelli 3D, primo passo, come «Strati sopra la foto» in Ortofoto;
   legenda e attribuzioni sotto la mappa.
6. In più: la fonte del 3D dei corpi DBTR ora è «DB topografico regionale» (la parola «DSM» nella fonte «da DTM DSM 2008»
   faceva scrivere «corpi dal LiDAR»); la scheda dell'edificio mostra nome, foglio e numero e destinazione del DBTR.

### B – DBTR dei comuni, DTM dai quadranti

- **Lettura del DBTR vero** (`edifici3d/uvl.py`): strati e colonne reali (`V_UVL_GPG`, `V_EDI_GPG`, `V_EDI_CT_USO_AVM`;
  ID_E, EDI_ID_E, H_UVL, B_UVL, H_GRONDA, H_COLMO…), GeoPackage **o** cartella Shapefile (Faenza, Novafeltria), senza
  pyarrow (prima `read_arrow` falliva: correzione anche in `regionali.py` e `zornade.py`), corpi legati all'edificio,
  foglio/numero/nome/destinazione nelle proprietà, cortili tenuti.
- **Regole delle altezze verificate** sul DTM 5 m 2025 e sul DSM LiDAR 2019 della costa (1.930 corpi di Rimini), poi su
  Faenza e Lugo (tabella nel README della fase 10): H_UVL intero = altezza (≈ gronda); H_UVL decimale **sopra** la base =
  **quota assoluta** del tetto (altezza = H_UVL − B_UVL; 7.861 corpi a Rimini); H_COLMO = quota assoluta a Rimini (colmo =
  H_COLMO − B_UVL, 4.313 tetti a capanna) e altezza a Faenza; **H_GRONDA non si usa** (spesso vicina al terreno). La
  Fase A del 04/11, scritta sul WMS, avrebbe dato a 7.861 corpi di Rimini altezze di 10–80 m sbagliate.
- **Un archivio CC BY per comune**: `prepara --comune rimini …` scrive `cc-by/er/rimini/prodotti/` (autonomo, più comuni in
  parallelo); `archivi-json` rigenera `archivi.json` dalla cartella degli archivi (DBTR dei comuni prima, prove OSM dopo o
  tolte con `--senza-prova`, chiave `lidar` per le falde della pipeline); `controlla-archivio` per i controlli di qualità.
  La pipeline LiDAR legge i corpi di tutti i comuni; la pagina legge solo gli archivi vicini al punto.
- **DTM 5 m dai quadranti** (`edifici3d/dtm_locale.py`, `fonti/emilia_romagna.toml`): quattro URL con dimensione, licenza
  **CC BY 4.0** verificata (scheda RNDT `r_emiro:2016-08-08T155835` e PDF nello zip), edizione 2025; letto **a finestra**
  anche dentro lo zip (`/vsizip/`), mai tutto in memoria; `prepara --dtm <zip>` ritaglia da sé; `dtm-ritaglia` e
  `scarica --fonte dtm5 --quadrante SE`. Il WCS (`dtm-wcs`) resta come riserva.
- **Attribuzione** «Regione Emilia-Romagna – DBTR, CC BY 4.0» in `indice.json`, `LICENZE.txt`, PMTiles, pagina, immagine e
  report. La scheda RNDT delle UVL dice CC BY 4.0; i metadati XML dentro l'estrazione dicono ancora CC BY 3.0 (scheda
  vecchia, compatibile).

### Prove sul DBTR vero (container)

- Rimini, `controlla-uvl`: 42.804 UVL di 35.702 edifici, 4,3 s, 392 MB. `prepara --comune rimini` col quadrante SE (zip non
  estratto): **40.518 corpi**, **301 s**, **700 MB** di memoria, **106 MB** di prodotti (tar di 81 MB).
- Gronda: mediana 7 m, 95° percentile 15 m, massimo 83 m; 219 corpi con cortile; 37.528 con foglio e numero.
- **Biblioteca Gambalunga** (via Gambalunga 27): edificio «Palazzo Gambalunga – Biblioteca», foglio 74 numero 1100, 2 corpi
  di 13 e 14 m, **cortile** presente, scelto col punto e generato in 3D. **Ospedale Infermi** (viale Settembrini 2, nel
  comune di Rimini): «sede di ospedale», foglio 99 numero 1, 14 corpi da 7 a 30 m; il punto ANNCSU può cadere
  sull'Istituto «Leonardo da Vinci» accanto: si trascina sul corpo dell'ospedale.
- Faenza (Shapefile) e Lugo: `controlla-uvl` ok (29.627 e 19.907 corpi con altezza).
- Pipeline LiDAR su una tessera della costa con l'archivio vero: 586 corpi, falde trovate.
- Stima sul server (ARM, 2 OCPU, 12 GB; container `edifici-lidar` 1 CPU e 4 GB): 5–10 minuti per Rimini, ~1 h per i 19 comuni.

### Archivio di prova OSM: tolto da `archivi.json` (definitivo, decisione di Paolo del 07/11)

Rigenerato con i cortili (530 corpi), accanto al DBTR aggiungerebbe 91 sagome non coperte, quasi tutte minuscole o
doppie, con altezze stimate a 9 m: **tolto da `archivi.json`**, file lasciati sul server come riserva. `archivi-json` ora
**non** elenca le prove di predefinito (`--senza-prova` resta accettato; `--con-prova` per rimetterle, per ultime). Fuori dal
DBTR serve il ripiego al volo (C), non un archivio OSM fisso.

### C – Ripiego OpenStreetMap al volo (decisione di Paolo del 07/11 mattina)

OpenStreetMap resta come **ripiego** per Modelli 3D quando il punto o l'edificio cade fuori da ogni archivio di qualità
(fuori dall'Emilia-Romagna e nei comuni ER il cui DBTR non è ancora preparato: oggi solo Rimini, Faenza e Lugo). Dove c'è
il DBTR vale il DBTR e OSM non si mescola.

1. **Rotta nuova `GET /api/edifici/osm?lon=&lat=`** (`fase4-server/servizio/edifici_osm.py`): punto arrotondato alla cella
   di 0,002° (~200 m), una query Overpass piccola (`around:400` dal centro della cella) per cella, **copia su disco** di 30
   giorni (`/dati/edifici_osm/`, tetto 500 MB); a Overpass va il centro della cella, non il punto. Lettore e regole di
   `osm_campione.py` (multipoligoni con i cortili e way aperte, `height` → `building:levels` × 3 → **stima** di 9 m
   dichiarata), client Overpass di `strati.py` (principale + riserva, User-Agent del servizio). **Una chiamata alla volta**
   per tutto il sito, almeno 1 s tra due, attesa del turno 15 s, timeout 30 s per istanza, tetto 300 chiamate/ora per il
   sito; limite per IP `edifici_osm` 60/ora; **Turnstile** come patrimonio e geocodifica (consuma le quote di Overpass).
   Spegnimento: `EDIFICI_OSM=false` nel `.env` (404). Valori nel `.env.example`; nessuno è obbligatorio.
2. **Pagina** (`edificio3d.js`): archivio «virtuale» OSM in fondo agli archivi, sorgente GeoJSON (sagome 2D tratteggiate);
   ricerca, punto trascinato, clic e sede dal Patrimonio fuori dal DBTR → corpi OSM; scelta, Genera il 3D, ombre, tabelle,
   immagine e report come con l'archivio; terreno piano (nessun DTM).
3. **Zona coperta = confine ISTAT del comune** per gli archivi di un comune intero (`istat` in `archivi.json`, tabella
   `uvl.COMUNI_ISTAT` dei 18 comuni scaricati, `prepara --istat`), riquadro dei corpi per gli altri (`prepara --parziale`,
   es. Ravenna, solo l'ospedale; Ravenna è fuori dalla tabella apposta). Il riquadro di Rimini sborda su Riccione,
   Coriano e Santarcangelo: con il confine, un punto di Riccione usa OSM e non «nessun edificio». I corpi OSM che cadono in
   un comune coperto si scartano. Le zone tratteggiate sono ora i confini dei comuni.
4. **Licenze**: «© OpenStreetMap contributors, ODbL 1.0» in ogni corpo (tabella, scheda), nel piè, nell'immagine scaricata
   e nel report (con l'attribuzione degli archivi davvero usati: prima il report metteva sempre quella del primo archivio);
   mai mescolati con l'archivio CC BY; altezze stimate dichiarate («stima: altezza non presente in OSM (9 m)»).
5. **Messaggi**: «Qui non c'è ancora il DBTR: si usa OpenStreetMap come ripiego (© OpenStreetMap contributors, ODbL 1.0),
   con qualità inferiore e altezze in parte stimate (9 m dove OSM non ha né altezza né piani).»; Overpass giù: «… il punto è
   fuori dalla zona coperta … e OpenStreetMap, il ripiego per queste zone, non ha risposto (…): qui il 3D non si può
   generare ora. Riprova tra qualche minuto.», nessun edificio scelto.
6. `archivi.json`: solo gli archivi DBTR (sopra). Privacy (riga del trattamento e API Overpass tra chi tratta i dati),
   F.A.Q. `#ripiego-osm`, piè di Modelli 3D, `EUGENIO_PER_AGENTI.md` (§ 4.5 bis, limiti, Turnstile, privacy) e `llms.txt`.
   Stessa versione `?v=20261107a` (non ancora pubblicata).

**Prova dal vivo** dal container (stesso codice della rotta, Overpass vero): **Pesaro**, ospedale San Salvatore (43,904 N
12,906 E): 200 in 24,9 s, **390 corpi**, 10 con altezza da OSM e 380 stimati, un multipoligono con cortile, due corpi
`building=hospital` ~400 m a nord del punto (stimati 9 m); **Cesena**, ospedale Bufalini (44,1405 N 12,2405 E): 200 in
20,2 s, **746 corpi**, 745 stimati, 19 pezzi di multipoligoni (18 con cortile); seconda richiesta nella stessa cella dalla
copia in 0,01 s. Pagina in Chromium con queste due risposte: scelta e Genera il 3D in ~2 s, 87 e 507 corpi vicini, nessun
errore. `overpass-api.de` dal container chiude la connessione o dà 502; ha risposto la riserva `maps.mail.ru` (a tratti 504
anche lei): dal server, il 06/11, `overpass-api.de` rispondeva.

### File toccati

Fase 10: `edifici3d/uvl.py`, `edifici3d/dtm_locale.py` (nuovo), `edifici3d/__main__.py` (`prepara --comune`, `--gpkg` più
file, `dtm-ritaglia`, `archivi-json`, `controlla-archivio`, `scarica --quadrante`, `osm-campione --dtm`),
`edifici3d/osm_campione.py`, `edifici3d/tessere.py`, `edifici3d/modello.py` (verso dei fori), `edifici3d/pipeline.py`
(contesti dei comuni), `edifici3d/fonti.py` (quadranti), `edifici3d/regionali.py`, `edifici3d/zornade.py` (lettore senza
pyarrow), `edifici3d/sintetico.py`, `fonti/emilia_romagna.toml`, `tests/test_edifici3d.py`, `tests/test_osm_campione.py`,
`README.md`. Fase 5: `sito/edificio3d.js`, `sito/edifici_calcoli.js`, `sito/cerca_luogo.js`, `sito/ortofoto.js`,
`sito/modelli3d.html`, `sito/stile.css`, `sito/EUGENIO_PER_AGENTI.md`, `sito/llms.txt`, tutte le pagine (versione),
`sito/interno/edifici.html` (a mano), `tests/test_mappe_browser.py`, `README.md`. Radice: `EUGENIO_PER_AGENTI.md`,
`RIEPILOGO.md`, `DA_FARE.md`, questo file.
Ripiego OSM (C): fase 4 `servizio/edifici_osm.py` (nuovo), `servizio/strati.py` (client Overpass riusabile
`chiedi_overpass`, `istanze_overpass`), `servizio/protezione.py` (`edifici_osm`, `tetto_globale`), `servizio/config.py`,
`servizio/app.py`, `api/Dockerfile` (copia `modello.py`, `osm.py`, `osm_campione.py`, `tessere.py`), `api/requirements.txt`
(`shapely==2.2.0`, `pyproj==3.8.0`), `.env.example`, `tests/test_edifici_osm.py` (nuovo), `README.md`; fase 10
`edifici3d/osm_campione.py` (`query_punto`, `crs_metrico`, `errore_overpass`, `corpi_al_volo`), `edifici3d/osm.py` (pezzi
di un multipoligono = un edificio), `edifici3d/uvl.py` (`COMUNI_ISTAT`), `edifici3d/__main__.py` (`archivi-json` senza prove
di predefinito, `--con-prova`, `istat`; `prepara --istat`, `--parziale`), test, `README.md`; fase 5 `sito/edificio3d.js`,
`sito/confini_gl.js` (`geometriaComune`), `sito/protezione.js`, `sito/privacy.html`, `sito/faq.html`, `sito/modelli3d.html`,
`sito/EUGENIO_PER_AGENTI.md`, `sito/llms.txt`, `tests/test_mappe_browser.py`, `README.md`.
**Non toccati**: Caddyfile (bastano `/api/*` con 180 s e la compressione), `fase11-visure/`, `edifici3d/importa.py` e
`__init__.py`, `edifici3d/analisi.py`.

### Test (container)

Fase 10: **106 passed**. Fase 5: **45 passed, 1 skipped** (pvlib). Fase 4 (con `PYTHONPATH=.:../fase3-storico:../fase6-mercati:../fase7-territorio:../fase8-indicatori:../fase9-clima-storico:../fase10-edifici3d`):
**179 passed, 4 failed** (7 nuovi in `test_edifici_osm.py`): i 4 rossi sono **già rossi sul commit 60d8a7c**, senza nessuna modifica di oggi
(`tests/test_meteo_nazionale.py` 3 e `tests/test_scarica_risposte.py` 1, file nel repository ma non negli zip: provano
`COMUNI_PER_BLOCCO`, `REGIONI_AGGIORNATE` e un nuovo tentativo sui JSON troncati, non ancora scritti; in DA_FARE).
`test_agenti.py` (versione e copie del file per gli agenti) passa.

### Limiti

- Altezze del DBTR «qualitative» (±3 m); le regole sono verificate su Rimini, Faenza e Lugo: per ogni nuovo comune
  `controlla-uvl` e `controlla-archivio` (sotto) prima di metterlo in `archivi.json`.
- Le ombre dei corpi a corte usano la sagoma esterna (il cortile risulta in ombra).
- Ravenna è solo l'area dell'ospedale (estrazione parziale); il Geoportale non estrae per provincia né per regione.
- Un corpo diviso a mano con una linea che taglia il cortile: il cortile resta nella parte che contiene il suo centro.

### D – «Aggiungi DBTR» (decisione di Paolo del 07/11/2026)

**Due destinazioni insieme.**

1. **Nel browser, subito** (`fase5-sito/sito/aggiungi-dbtr.html`, `aggiungi_dbtr.js`, `dbtr_worker.js`, `dbtr_lettore.js`,
   `dbtr_locale.js`): l'utente sceglie regione e comune (elenco ISTAT dei comuni della regione, casella «comune intero»)
   e carica lo zip del portale, il GeoPackage o le parti di uno Shapefile (anche una cartella), fino a **300 MB**. Il Web
   Worker legge zip (**fflate 0.8.2**, MIT), GeoPackage (**sql.js 1.14.2**, MIT, SQLite in WebAssembly, caricato solo quando
   serve) e Shapefile/DBF (lettore scritto qui: poligoni con fori, PolygonZ, codifica dal `.cpg` o dal codice di lingua),
   con proj4js per i sistemi di riferimento. **Stessa logica del Python**: `uvl.convenzione`, `uvl.altezze`, `uvl.corpo_da`
   (corpo–edificio, foglio, numero, nome, destinazione, cortili), adattatori DBGT Lombardia e CTRN FVG di `regionali.py`;
   proprietà e coordinate come `tessere.feature_da_corpi` (area con le coordinate spostate come GEOS, arrotondamenti come
   `round()` di Python). Terreno: piano, alla quota della base del DB topografico (dichiarato). «Apri in Modelli 3D» salva i
   corpi in IndexedDB e apre `modelli3d.html?dbtr=locale`: l'archivio «locale» vale per primo (dove si sovrappone a un
   archivio del server vince il file dell'utente) ed è **zona coperta per la sessione** (confine ISTAT del comune se è il
   comune intero, altrimenti il riquadro dei corpi); fuori resta il ripiego OSM. Mai al server. Liguria: la CTR 3D richiede
   il DTM regionale, che il browser non scarica → solo proposta al server. Segnalati (non corretti) i corpi sotto 30 m² e
   oltre 40 m (anomalia di Bagno di Romagna, sotto).
2. **Nell'archivio comune, dopo l'approvazione** (consenso esplicito, casella **non spuntata**): `POST /api/dbtr/inizia`
   (Turnstile; regione, comune, ISTAT, comune intero, formato, dimensione, SHA-256; **nessun dato personale**), pezzi da
   **32 MB** con `PUT /api/dbtr/{id}/pezzo/{n}` (Cloudflare accetta al più 100 MB per richiesta: un file da 300 MB passa
   in 10 pezzi), `POST /api/dbtr/{id}/fine` (impronta, controllo leggero dello zip: percorsi «..», assoluti o con l'unità,
   link simbolici, zip cifrati, bombe oltre 200:1 su voci di 50 MB, oltre 3 GB estratti, nessun dato → 422 e file
   cancellato). Stato e ritiro con `GET`/`DELETE /api/dbtr/{id}` (gettone firmato). Soglie: **300 MB** per file, **3 file
   al giorno per rete** (finestra di 24 ore), 60 pezzi all'ora, **20 proposte aperte**, 4 GB di coda, 10 GB liberi sul disco
   (tutte nel `.env`); caricamenti a metà cancellati dopo 6 ore. File in `/dati/edifici_coda/<id>/` (fuori da
   `/edifici3d/`, mai servita da Caddy).
3. **Preparazione** (`fase10-edifici3d/edifici3d/coda.py`, servizio `edifici-coda` con l'immagine `energia-edifici`, una
   richiesta alla volta): estrazione sicura (solo i file attesi, dimensione reale ricontrollata, uno zip annidato al massimo),
   controlli (strati e colonne, EPSG:7791 per l'ER, riquadro dentro la regione dichiarata, metadati XML della Regione letti
   come testo, comuni catastali, **dati personali**: nomi di colonna da intestatari, codici fiscali, email e valori che
   sembrano codici fiscali o email → la proposta non supera i controlli), `prepara --comune` (o `prepara-regione --comune`,
   nuovo) in un processo figlio con `nice` e tetto di memoria di 3,5 GB, DTM del server se c'è (quadranti ER in
   `cc-by/er/grezzi/dtm5/`; se non copre il comune si rifà con B_UVL), `controlla-archivio`, anteprima GeoJSON (al più
   15.000 corpi). Bassa priorità: peso CPU 128 contro 1024 dell'api, pausa se `/api/salute` dice `previsioni_in_corso > 0`,
   nessuna preparazione dalle 3:15 alle 7:00 (pipeline LiDAR).
4. **Approvazione** nella pagina interna `/interno/edifici.html` (Cloudflare Access, JWT verificato dall'api, più
   l'intestazione `X-EuGEnio-Interno` contro le richieste da altri siti): coda con comune, regione, formato, data, dimensione,
   esito (corpi, gronda mediana/p95/max, convenzione, scartati, anomalie, corpi sospetti), anteprima dei corpi colorati per
   altezza sull'ortofoto, registro; **Approva** → entro un minuto `edifici-coda` sposta l'archivio in
   `cc-by/<er|lom|fvg|lig>/<comune>/` (il precedente in `_precedenti/`, due copie al massimo, ignorate da `archivi-json`;
   ritorno con `coda-ripristina --zona er --comune <c>`) e rigenera `archivi.json`; **Rifiuta** → file cancellati subito.
   Nessuna email. Restano una riga in `storico.jsonl` (comune, regione, formato, data, esito) e l'esito per 30 giorni.
5. **Licenza e attribuzione**: quelle della fonte, CC BY 4.0 per le quattro regioni (`fonti/regioni.toml`: ER RNDT
   `r_emiro:2017-11-24T135040`; Lombardia `r_lombar:3493af32-…`; FVG CC BY 4.0 nella scheda del servizio di download,
   «Non indicato» sugli strati, IODL 2.0 come regola generale della Regione: in attesa di chiarimento; Liguria
   `r_liguri:D.2237`).
6. **Pagina di istruzioni** `dbtr-istruzioni.html` (scelta: pagina separata, perché le istruzioni sono lunghe e per
   regione, si leggono una volta mentre si aspetta l'email del portale, e la pagina dello strumento resta corta; è collegata
   in alto alla pagina dello strumento, in Modelli 3D e nella F.A.Q. `#aggiungi-dbtr`): Emilia-Romagna, Lombardia, Friuli
   Venezia Giulia, Liguria, Trento, Veneto (pagina, strati, formato, sistema, licenza, limiti, cosa caricare), con «verifica
   sul portale» dove un passaggio non è confermato (il Geoportale ER e le schede INSPIRE non erano leggibili dal container:
   i passi ER vengono dai download fatti da Paolo il 05–06/11); le altre regioni «in attesa di chiarimento dalla Regione»
   (Campania, Abruzzo, Puglia, Umbria «da verificare», note aggiunte in `fonti/regioni.toml` senza accendere fonti).
7. Menu (gruppo Patrimonio, «S»): «Aggiungi edifici (DB topografico)» e «Scaricare i DB topografici»; privacy (`#dbtr`),
   F.A.Q., Sitografia (sql.js, fflate), `lib/README.md`, `EUGENIO_PER_AGENTI.md` (§ 3, § 4.5 ter, § 5, § 8) e `llms.txt`.

**Prove (container)**: parità Python–JS (node) sui sintetici (GeoPackage e Shapefile, convenzioni «quote» e «altezze»,
DBGT con le z, CTRN con i nomi troncati del DBF) **identica**; sulle estrazioni vere: Lugo 19.906 corpi (1 diverso), Faenza
29.630 (3), Rimini 40.518 (6 diversi, 1 in meno nel browser: geometrie non valide che il Python ripara con make_valid);
Rimini letta in node in ~3 s. Chromium: lettura di GeoPackage e Shapefile, nessuna richiesta senza consenso, invio a pezzi
con impronta, apertura in Modelli 3D (scelta di un edificio con cortile e corpi del file), pagina interna con una coda
finta (anteprima, Approva). Coda in Python: zip malevoli, quattro regioni, installazione, `_precedenti/`, `archivi.json`,
ritorno all'archivio precedente, finestra oraria.

**Correzione emersa**: gli adattatori di Lombardia, FVG e Liguria cercavano i nomi completi delle colonne
(`QUOTA_GRONDA`…), ma negli Shapefile il DBF li tronca a 10 caratteri (`QUOTA_GRON`): ora `regionali.nomi_completi` li
riconosce (anche il lettore del sito).

**File toccati (D)**: fase 10 `edifici3d/coda.py` e `edifici3d/archivi.py` (nuovi; `scrivi_archivi_json` spostato qui,
`__main__` lo importa, cartelle «_…» ignorate), `edifici3d/__main__.py` (`coda`, `coda-ripristina`, `prepara-regione
--comune/--nome/--istat/--parziale`), `edifici3d/regionali.py` (nomi troncati), `fonti/regioni.toml` (note), test
`dbtr_sintetici.py`, `dbtr_node.js`, `test_coda.py`, `test_dbtr_parita.py`, `test_dbtr_browser.py`, `README.md`; fase 4
`servizio/dbtr_coda.py` (nuovo), `servizio/app.py`, `config.py`, `protezione.py` (`dbtr` al giorno, `dbtr_pezzi`),
`api/Dockerfile` (copia `coda.py`), `Caddyfile` (`/api/dbtr/*` a 40 MB), `docker-compose.yml` (`edifici-coda`),
`.env.example`, `tests/test_dbtr_coda.py`, `README.md`; fase 5 `sito/aggiungi-dbtr.html`, `dbtr-istruzioni.html`,
`aggiungi_dbtr.js`, `dbtr_worker.js`, `dbtr_lettore.js`, `dbtr_locale.js`, `lib/sql.js/`, `lib/fflate/` (nuovi),
`edificio3d.js`, `modelli3d.html`, `protezione.js`, `privacy.html`, `faq.html`, `sitografia.html`, `lib/README.md`,
`interno/edifici.html`, `interno/edifici.js`, `interno/interno.css`, `EUGENIO_PER_AGENTI.md`, `llms.txt`,
`parti/testata.html` (tutte le pagine rigenerate), test, `README.md`; radice `EUGENIO_PER_AGENTI.md`, `RIEPILOGO.md`,
`DA_FARE.md`, questo file; `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md` (copiato così com'è dal lavoro sulle lettere).

**Test (container, 07/11 dopo D)**: fase 10 **122 passed**; fase 5 **46 passed, 1 skipped**; fase 4 **195 passed, 4 failed**
(gli stessi 4 già rossi sul commit 60d8a7c).

### Archivi dei 19 comuni (preparazione del 07/11/2026 mattina)

Preparati con il codice del 07/11 (ripiego OSM compreso): **19 archivi**, tutti con `"problemi": []` in
`controlla-archivio`, ognuno con il codice ISTAT nell'indice (Ravenna `--parziale`, solo l'area dell'ospedale). Corpi:
Forlì 56.163, Cesena 46.226, Rimini 40.518, Faenza 29.630, Lugo 19.906, Cervia 14.534, Ravenna 12.979 (parziale), Riccione
11.985, Santarcangelo 9.028, Russi 7.826, Savignano 6.643, Cattolica 6.170, Forlimpopoli 5.775, Brisighella 5.698, Bagno di
Romagna 5.019, Mercato Saraceno 3.932, Montescudo-Monte Colombo 3.500, Novafeltria 3.397, Santa Sofia 3.324 (~293.000 corpi);
da 30 s a 7,5 minuti per comune. Sul PC in `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\`: **19
tar.gz** (1,2 GB) con `SHA256SUMS.txt`; la sottocartella `parti\` si può cancellare. **Anomalia**: a Bagno di Romagna un
corpo di 8,3 m² «abitativa» con H_UVL 114 m (foglio 54, numero 216, ~43,8892 N 11,9914 E), errore del dato (DA_FARE:
regola di plausibilità). Gli archivi dei comuni montani sono grandi per le tessere del terreno (Brisighella 171 MB, Bagno
138 MB, Santa Sofia 120 MB: DA_FARE).

### E – Terreno 3D dal server e altezze non plausibili (decisioni di Paolo del 07/11/2026)

**Terreno** (decisione delle 11:37, al posto della riduzione dello zoom fuori dai centri abitati): il DTM **non va più negli
archivi dei comuni**. Prima pesava quasi tutto l'archivio dei comuni montani (Brisighella: 98 MB di `terreno.pmtiles` e
71 MB di `dtm_cog.tif` su 169 MB). Ora:

- il server tiene il DTM 5 m come **COG unico** per quadrante in `/srv/energia/dati/terreno/`, convertito una volta dallo
  zip con il comando nuovo `dtm-server` della fase 10 (quadrante SE: 1,30 GB, ~14 minuti; F17);
- la rotta nuova **`GET /api/terreno/{z}/{x}/{y}.png`** (`fase4-server/servizio/terreno.py`, elenco in
  `GET /api/terreno/fonti`) genera le tessere Terrarium solo dove qualcuno apre il 3D: letture a finestra con la
  panoramica giusta (0,03–0,13 s per tessera), copia su disco (`/dati/terreno_tessere`, 5 GB al massimo, pulizia delle
  più vecchie), Cache-Control di 30 giorni, limite per IP solo sulle tessere nuove (`TERRENO_ORA`), fuori dal DTM il
  Copernicus DEM 90 m dell'orizzonte lontano, se nemmeno quello una tessera piatta dichiarata. Nell'immagine dell'api
  entra `rasterio` (rebuild in F11); Caddy ha il blocco `/api/terreno/*` (F11); **Cloudflare**: la regola di rate limiting
  su `/api/` deve escludere anche `/api/terreno/` (F20);
- la pagina 3D (`edificio3d.js`) usa questa sorgente `raster-dem` per tutti gli archivi e anche per il DB topografico letto
  nel browser, se `/api/terreno/fonti` risponde (altrimenti mappa piatta: così la pagina funziona anche prima del rebuild
  dell'api); le tessere dell'archivio solo se l'indice ha ancora `tessere_terreno` (demo sintetica). Una tessera che
  manca non dà errori (prova in Chromium);
- `prepara` calcola ancora dal DTM la **quota di ogni corpo**: ombre, orizzonte vicino e report non cambiano. `dtm_cog.tif`
  e `terreno.pmtiles` solo con `--terreno-archivio`; la pipeline LiDAR ripiega sul DTM del server (`/dati/terreno`).

Confronto vicino agli edifici (Brisighella e Rimini, 40 corpi a caso, tessere che li contengono): a zoom 15 tessere
**identiche** (scarto 0,000 m), a zoom 14 al più 0,23 m, a zoom 13 al più 1,5–3,1 m (panoramiche del COG, solo lontano
dalla vista); quote dei corpi identiche.

**Altezze non plausibili** (decisione di Paolo, richiesta del coordinatore): il corpo resta, la gronda del DBTR si porta
alla stima (mediana dei vicini entro 100 m, o dall'uso, 6–9 m), il valore originale va in `h_dbtr_scartata`, la fonte
dice «stima: altezza DBTR non plausibile (X m)» e pagina e report «altezza stimata (dato DBTR non plausibile: X m)».
Regola in `fase10-edifici3d/edifici3d/plausibilita.py` (spiegazione e prove nel README della fase 10), identica nel
lettore del sito (`dbtr_lettore.js`) e quindi nella coda; i corpi piccoli e altissimi rimasti (campanili, ciminiere) sono
ancora solo segnalati. Corpi portati alla stima nei 19 comuni: 7 corpi (Bagno di Romagna 1, Forlì 3, Lugo 1, Ravenna 1, Rimini 1).

**19 archivi rigenerati** con il codice nuovo (tutti `"problemi": []`):

| Comune | Corpi | tar prima (MB) | tar dopo (MB) | Altezze stimate |
|---|---:|---:|---:|---|
| Brisighella | 5.698 | 171,5 | 3,7 | 0 |
| Cesena | 46.226 | 160,3 | 26,0 | 0 |
| Forlì | 56.163 | 160,2 | 29,1 | 3 – 41,0 → 3,5 m (f. 83 n. 49); 40,8 → 3,5 m (f. 188 n. 431); 41,0 → 12,0 m (f. 147 n. 1285) |
| Bagno di Romagna | 5.019 | 138,4 | 3,1 | 1 – 114,0 → 4,0 m (f. 54 n. 216) |
| Santa Sofia | 3.324 | 120,1 | 2,1 | 0 |
| Faenza | 29.630 | 116,6 | 16,0 | 0 |
| Mercato Saraceno | 3.932 | 82,1 | 2,5 | 0 |
| Rimini | 40.518 | 81,4 | 22,5 | 1 – 47,94 → 5,0 m (f. 145 n. 690) |
| Novafeltria | 3.397 | 46,4 | 2,1 | 0 |
| Cervia | 14.534 | 46,1 | 8,2 | 0 |
| Santarcangelo | 9.028 | 31,3 | 4,9 | 0 |
| Russi | 7.826 | 25,2 | 4,2 | 0 |
| Savignano | 6.643 | 24,5 | 3,5 | 0 |
| Montescudo-Monte Colombo | 3.500 | 19,2 | 2,0 | 0 |
| Lugo | 19.906 | 19,0 | 10,2 | 1 – 40,0 → 6,0 m (f. 104 n. 1126) |
| Riccione | 11.985 | 15,8 | 6,5 | 0 |
| Forlimpopoli | 5.775 | 14,3 | 3,3 | 0 |
| Ravenna (parziale) | 12.979 | 8,6 | 6,8 | 1 – 35,0 → 12,0 m (f. 77 n. I) |
| Cattolica | 6.170 | 7,2 | 3,3 | 0 |
| **Totale** | 292.253 | **1.288,4** | **160,0** | 7 |

File nuovi: `fase10-edifici3d/edifici3d/plausibilita.py`, `fase10-edifici3d/tests/test_plausibilita.py`,
`fase4-server/servizio/terreno.py`, `fase4-server/tests/test_terreno.py`. Toccati: `edifici3d/__main__.py` (opzione
`--terreno-archivio`, comando `dtm-server`, `controlla-archivio`), `dtm_locale.py` (`cog_server`), `pipeline.py`,
`coda.py`, `tessere.py`; `fase4-server/servizio/app.py`, `config.py`, `protezione.py`, `api/requirements.txt`,
`Caddyfile`, `.env.example`; `fase5-sito/sito/edificio3d.js`, `dbtr_lettore.js`, `interno/edifici.js`, `llms.txt`,
`EUGENIO_PER_AGENTI.md` (radice e sito); test `test_edifici3d.py`, `test_osm_campione.py`, `test_mappe_browser.py`.
Il sito resta `?v=20261107a` (non ancora pubblicato).

Test (container): fase 10 **125** (+3: `test_plausibilita.py`), fase 5 **47 + 1 saltato** (+1: terreno dal server e
altezza stimata in Chromium, anche con la rotta assente), fase 4 **203** (+8: `test_terreno.py`) e i 4 rossi già noti.

### F – Pagine 3D, altezze OSM, Overpass (decisioni di Paolo del 07/11/2026 pomeriggio)

1. **Altezze del ripiego OSM.** Ai corpi OSM senza `height` né `building:levels` si dà la **mediana delle gronde dei corpi
   DBTR vicini** (entro 200 m dal centro del corpo, almeno 3 corpi, solo altezze del DB topografico: esclusi i corpi già
   portati alla stima e quelli fuori da 2–80 m), arrotondata al mezzo metro; dove non ci sono, **9 m fissi** come prima.
   - Server (`fase4-server/servizio/edifici_osm.py`): legge `archivi.json` e le celle di contesto degli archivi in
     `CARTELLA_EDIFICI_INTERNA` (`/dati/edifici` nell'api), al più 64 celle in memoria; il calcolo si fa **a ogni
     risposta** e non nella copia su disco, così un comune preparato dopo vale subito anche per le celle già copiate.
   - Browser (`edificio3d.js`): stessa regola sui corpi del DB topografico caricato con «Aggiungi DBTR» («mediana dei
     corpi del DB topografico del tuo file vicini»).
   - Regola comune in `fase10-edifici3d/edifici3d/osm_campione.py`: `altezze_da_vicini`, `origine_altezza`,
     `conta_altezze`, `altezza_dbtr_valida`. Ogni corpo porta `origine_altezza` (`osm_height`, `osm_piani`,
     `dbtr_vicini`, `fissa`) e la fonte, per esempio «stima: mediana dei corpi DBTR vicini (11 entro 200 m: 5 m)»; la
     risposta ha i conteggi in `altezze` (`altezze_stimate` e `altezze_osm` restano).
   - **Nota sotto la mappa** (`#nota-altezze-osm`, creata dalla pagina sotto «Fonte del 3D per corpo»): «Edifici
     OpenStreetMap nella vista: 85, di cui 3 con l'altezza dal dato OSM (height o piani × 3 m), 0 stimati dalla mediana
     dei corpi DBTR vicini (entro 200 m), 82 a 9 m fissi (stima).» In 2D conta le sagome OSM nella vista, in 3D l'edificio
     e i vicini; la stessa riga va nell'immagine scaricata e nelle note del report. F.A.Q. `#ripiego-osm` aggiornata.
   - Prova su dati veri (container, archivi dei 18 comuni del server più l'istanza europea): al confine Rimini–Coriano 27
     corpi su 28 stimati dai vicini DBTR (es. «11 entro 200 m: 5 m»), 1 a 9 m; Pesaro 380 a 9 m, 10 dal dato OSM.
2. **Istanza Overpass di riserva**: **Overpass API Europa** (`https://ovp.dresel.systems/api/interpreter`) al posto di
   `maps.mail.ru` (VK), per lo strato «Contorni degli edifici – OpenStreetMap» e per il ripiego. Scelta:
   | Istanza | Esito dal container (07/11) | Regole pubblicate | Scelta |
   |---|---|---|---|
   | Overpass API Europa, ovp.dresel.systems (Christian Dresel, Fürth, Germania) | 200 in 1,0–2,5 s a Pesaro, Cesena, Milano, Napoli, Palermo; dati del 05/11 | libera, senza chiave né registrazione; 4 richieste parallele per IP; uso corretto, niente cicli continui; nessuna garanzia; registri (IP, testo della query) 14 giorni, GDPR, server in Germania (IPv4 da un proxy tedesco che non decifra) | **riserva** |
   | overpass.private.coffee (ex overpass.kumi.systems, Austria) | API senza risposta in 60 s (la pagina risponde); anche dal server il 06/11 | nessun limite, avvisare per progetti grandi | alternativa se torna a rispondere |
   | overpass.openstreetmap.fr | 200, ma `/api/status`: «only available to white-listed usages»; dati del 27/07/2026 | solo usi autorizzati | no |
   | overpass.osm.ch | 200 senza edifici fuori dalla Svizzera | solo Svizzera, chiedere prima | no |
   | maps.mail.ru (VK, Russia) | 504 | nessun limite | tolta |
   La principale resta `overpass-api.de` (FOSSGIS e.V.; dal container connessione chiusa, dal server rispondeva).
   `servizio/strati.py`: costanti `OVERPASS_PRINCIPALE` e `OVERPASS_RISERVA`, funzione `riserva_overpass()` comune allo
   strato e al ripiego; `OVERPASS_RISERVA` nel `.env` (riga assente = riserva del TOML; **riga vuota = nessuna riserva**,
   più istanze separate da virgola; i servizi esclusi delle ortofoto sono scartati). TOML `fonti/…/ortofoto/strati/
   edifici.toml` con la scelta e le alternative; informativa privacy (servizi esterni) e Sitografia (voce OpenStreetMap).
3. **Turnstile resta** sul ripiego OSM: nessuna modifica (confermato nei documenti).
4. **Pagine 3D unificate.** Le 8 pagine Edificio › Geometria, Consumi, Obblighi e Fotovoltaico › Ombre, Producibilità,
   Sole e irradiazione, Confronto PVGIS, D.Lgs. 199/2021 aprivano un solo archivio (`/edifici3d/cc-by/er/prodotti/`, che
   con gli archivi per comune non esiste più) e finivano sulla demo. Il modo più semplice: **la stessa mappa di Modelli 3D**.
   - HTML: la parte della mappa (ricerca, mappa 2D, «Genera il 3D», «Torna alla mappa 2D», demo, immagine, legenda dei
     livelli, fonti), il passo «Livelli della mappa», il rimando ad «Aggiungi edifici» e gli script (`minimappa.js`,
     `confini_gl.js`, `esporta_mappa.js`, `cerca_luogo.js`, `strati_gl.js`, `dbtr_locale.js`) copiati da `modelli3d.html`
     (le 8 pagine avevano già lo stesso pannello); titolo, sottotitolo e `data-vista` restano quelli della pagina, con una
     frase sul modo di scegliere l'edificio; «Prova la demo» ed «Esci dalla demo» restano sulla pagina stessa.
   - JS (`edificio3d.js`): `DUE_TEMPI` vale per ogni pagina con `#genera-3d`; `data-vista` sceglie solo il passo in
     evidenza (le ombre partono da sole in Fotovoltaico › Ombre); titolo dell'immagine dal titolo della pagina; demo di
     ripiego (da `?sede=locale` o `?edificio=`) solo se la rotta OSM risponde 404 (nessun archivio e nessun ripiego);
     `?edificio=<id>&lon=&lat=` (senza punto, il centro del primo archivio) con il messaggio se l'edificio non c'è.
   - Il DB topografico caricato nel browser vale in tutte le pagine della stessa scheda (segnale di sessione di
     `dbtr_locale.js`).
5. **Prove in Chromium su dati veri** (script nel container, non nel repository): tutte le 9 pagine 3D, con i 18 archivi
   DBTR veri serviti come sul server (`archivi.json` con 18 voci, Lugo escluso apposta) e il ripiego OSM:
   - **Rimini**, Biblioteca Gambalunga: «Palazzo Gambalunga – Biblioteca», foglio 74, numero 1100, 2 corpi (13 e 14 m),
     1.131 corpi vicini, archivio `cc-by/er/rimini`, mai la demo;
   - **Pesaro** (Overpass simulato con la risposta vera dell'istanza europea): edificio OSM scelto e generato, 84 vicini,
     nota «85, di cui 3 con l'altezza dal dato OSM, 0 stimati dai corpi DBTR vicini, 82 a 9 m fissi»;
   - **Lugo** (GeoPackage vero letto in «Aggiungi edifici», 19.906 corpi in 2 s, «Apri in Modelli 3D», poi ogni pagina
     nella stessa scheda): foglio 107, numero 564, 2 corpi, 798 vicini, archivio «locale»;
   - nessun errore JavaScript; in console solo i 404 delle rotte `/api` che nel container non ci sono (`ortofoto/fonti`,
     `terreno/fonti`, `ortofoto/strati`, `protezione`).

**File toccati (F)**: fase 4 `servizio/strati.py`, `servizio/edifici_osm.py`, `servizio/config.py`, `.env.example`,
`tests/test_strati.py`, `tests/test_edifici_osm.py`, `README.md`; fase 10 `edifici3d/osm_campione.py`,
`ortofoto/strati/edifici.toml`, `tests/test_osm_campione.py`, `README.md`; fase 5 `sito/edificio3d.js`, le 8 pagine 3D,
`sito/privacy.html`, `sito/sitografia.html`, `sito/faq.html`, `sito/stile.css`, `tests/test_mappe_browser.py`
(`test_altre_pagine_3d_come_modelli3d`, `test_pagine_3d_unificate_dbtr_osm_e_file_locale`),
`tests/test_costruisci_pagine.py`, `README.md`; radice `EUGENIO_PER_AGENTI.md` (anche in `sito/`), `sito/llms.txt`,
`RIEPILOGO.md`, `DA_FARE.md`, questo file.

### G – Pagina «Novità» e feed Atom (decisione di Paolo del 07/11/2026, ore 12:32)

- **Fonte unica** `fase5-sito/novita.toml` (accanto a `costruisci_pagine.py` e a `parti/`, perché è materia della
  costruzione delle pagine e non un dato servito): una voce `[[voce]]` per pubblicazione, la più recente in cima, con
  `data`, `versione`, `titolo`, righe `nuovo`, `cambiato`, `corretto` (facoltative) e `collegamenti` facoltativi.
  Voci iniziali ricostruite dagli AGGIORNAMENTO e dalla PUBBLICAZIONE: `?v=20261027m`, `20261028d`, `20261029b`,
  `20261104c`, `20261105a`, `20261105b`, `20261106a` e in cima `20261107a` (tutto il pacchetto di oggi).
- `costruisci_pagine.py` genera **`sito/novita.html`** (pagina di testo, indice laterale per versione con `indice.js`) e
  il feed **`sito/novita.xml`** (Atom, indirizzi assoluti, una `entry` per voce); `--controlla` li confronta come le altre
  pagine. Testata: «Novità» tra Mirror e Contattaci (computer e telefono) con `data-ultima`; nella testa comune
  `<link rel="alternate" type="application/atom+xml" …>`; **pallino** discreto se la versione è più nuova dell'ultima vista
  (`aspetto.js`, solo `localStorage` con try/catch, nessun cookie; la prima visita non lo mostra; aprire la pagina lo
  toglie). Caddy: `application/atom+xml; charset=utf-8` per `/novita.xml` (serve `--force-recreate caddy`, già in F11).
- **Newsletter mensile** (`servizio/notiziario.py`): sezione «Novità di EuGEnio» con le voci del mese concluso, da
  `novita.toml` copiato nell'immagine dell'api (`COPY fase5-sito/novita.toml /app/novita.toml`: per questo il pacchetto del
  codice di F5 comprende quel file). Prima uscita con la sezione: 12/12/2026 (voci di novembre).
- **Niente «Blog»** per ora (DA_FARE). **Regola permanente** (RIEPILOGO, README generale e della fase 5): a ogni
  pubblicazione una voce in `novita.toml` con AGGIORNAMENTO, `EUGENIO_PER_AGENTI.md` e `llms.txt`, poi la release su
  GitHub con lo stesso testo (F23).
- Test: `test_novita_versione_feed_e_menu` (prima voce = versione di `index.html`, feed Atom valido, ordine del menu, nessun
  dato di mercato), `test_novita_telefono_e_pallino` (375 px senza scorrimento orizzontale, pallino),
  `fase4-server/tests/test_notiziario_novita.py` (2).

**File toccati (G)**: fase 5 `novita.toml` (nuovo), `costruisci_pagine.py`, `parti/testata.html`, `parti/testa.html`,
`sito/novita.html` e `sito/novita.xml` (nuovi, generati), `sito/aspetto.js`, `sito/stile.css`, tutte le pagine
(testata e testa), test; fase 4 `servizio/notiziario.py`, `servizio/config.py` (`NOVITA_TOML`), `api/Dockerfile`,
`Caddyfile`, `tests/test_notiziario_novita.py` (nuovo).

**Test (container, 07/11 sera, dopo F e G)**: fase 10 **126**; fase 5 **50 passed, 1 skipped**; fase 4 **208 passed,
4 failed** (gli stessi 4 rossi del commit 60d8a7c, **verdi dopo la sezione H**).

### H – Meteo nazionale a blocchi e test della fase 4 tutti verdi (07/11/2026 sera)

Quattro test della fase 4 erano rossi già sul commit `60d8a7c` (`tests/test_meteo_nazionale.py`, 3, e
`tests/test_scarica_risposte.py`, 1, scritti il 04/11): descrivevano funzioni mai scritte, nemmeno sul server (verificato da
Paolo). I test sono stati presi come specifica e **non sono stati cambiati**; ora il codice c'è.

- **Giornaliero nazionale a blocchi** (`fase3-storico/meteo_storico/aggrega.py`): `giornaliero.parquet` (per tutta Italia
  ~34 milioni di righe) è **un solo file ordinato per comune e data, con un row group ogni `COMUNI_PER_BLOCCO` comuni**
  (100; un comune mai diviso tra due row group; metadato `eugenio_formato = giornaliero_a_blocchi_v1`). Scelta: row group
  nello stesso file e non un file per blocco, perché è quello che chiedono i test (`num_row_groups`) e perché resta lo
  stesso percorso `/srv/energia/dati/giornaliero.parquet` che usano api, worker, Dati climatici e newsletter.
  - `esporta` elabora i comuni a blocchi in `giornaliero.parziale/` (riprendibile) e alla fine li unisce;
  - `leggi_comune` legge solo il row group del comune (statistiche min/max di `istat`): `meteo.storico_giornaliero` ~0,1 s,
    in cache per comune finché il file non cambia (`meteo._giornaliero_comune`);
  - `aggiorna_a_blocchi` (usato da `meteo.aggiorna_giornaliero`, cioè dallo storico del worker) riscrive il file un pezzo
    di 500.000 righe alla volta, le righe nuove vincono, i comuni nuovi entrano al loro posto, scrittura in
    `giornaliero.parquet.nuovo` e sostituzione atomica. Misura nel container: 8,6 milioni di righe in ~16 s con ~650 MB di
    picco, che non crescono con il file (worker a 3 GB);
  - **compatibilità**: i file di prima si leggono così come sono; il primo aggiornamento li converte da solo (file
    ordinato: una passata; file non ordinato, come quelli di `esporta` di prima che seguiva l'ordine di `comuni.parquet`:
    una lettura per blocco, riprendibile in `giornaliero.parziale/`). Per non lasciarlo al worker c'è il comando nuovo
    `python -m meteo_storico giornaliero-blocchi --file … [--solo-verifica]`, eseguito **una volta** in F12 con il worker
    fermo, una copia di sicurezza e la verifica prima e dopo;
  - `notiziario.py` legge dal giornaliero solo i capoluoghi (prima caricava le quattro colonne di tutto il file).
- **Regioni servite e aggiornate** (`servizio/config.py`, `.env`): `REGIONI` = regioni servite (vuoto = tutta Italia,
  invariato); **`REGIONI_AGGIORNATE`** = regioni di cui il worker aggiorna ogni giorno previsioni e storico, **vuoto = tutte
  quelle servite** (predefinito: il server si comporta come prima, qualunque sia il suo `REGIONI`); valgono solo dentro le
  servite. `meteo.comuni(aggiornati=True)` in `aggiorna_previsioni` e `aggiorna_storico`; il worker scrive all'avvio
  «Meteo: regioni servite …, aggiornate ogni giorno …». Per servire tutta Italia aggiornando solo l'ER (quando l'archivio
  nazionale sarà in `/srv/energia/dati`): `REGIONI=` e `REGIONI_AGGIORNATE=08` (decisione da prendere, non fatta oggi).
- **Risposte troncate di Open-Meteo** (`fase3-storico/meteo_storico/scarica.py`): una risposta 200 con il JSON interrotto o
  con meno punti di quelli chiesti si **riprova** (log «risposta troncata o incompleta … riprovo (n/4)», pause 5–40 s,
  sempre col limitatore) invece di fermare l'aggiornamento; dopo 4 di fila (`MAX_TRONCATE`) o 8 tentativi (`TENTATIVI`)
  errore ed email all'amministratore.
- Per chi usa il sito non cambia nulla di visibile, tranne che l'aggiornamento del meteo non si ferma più per una
  risposta interrotta: una riga in «Corretto» della voce `?v=20261107a` di `novita.toml` e una frase in
  `EUGENIO_PER_AGENTI.md` (storico aggiornato ogni giorno per le regioni aggiornate).

**File toccati (H)**: fase 3 `meteo_storico/aggrega.py`, `scarica.py`, `__main__.py` (comando `giornaliero-blocchi`),
`README.md`; fase 4 `servizio/meteo.py`, `config.py`, `worker.py`, `notiziario.py`, `.env.example`, `README.md`,
`tests/test_giornaliero_blocchi.py` (nuovo, 3: file di prima ordinati e non ordinati, conversione interrotta e ripresa,
comando); fase 5 `novita.toml`, `sito/novita.html`, `sito/novita.xml`, `sito/EUGENIO_PER_AGENTI.md`, `sito/llms.txt`;
radice `EUGENIO_PER_AGENTI.md`, `RIEPILOGO.md`, `DA_FARE.md`, questo file. Servono il rebuild dell'api (immagine unica di
api e worker: già in F11) e la conversione del giornaliero (F12).

**Test (container, 07/11 sera, dopo H)**: fase 4 **215 passed, 0 failed** (208 + i 4 di prima, ora verdi, + 3 nuovi);
fase 5 **50 passed, 1 skipped**; fase 10 **126 passed**; la fase 3 non ha test propri (le sue funzioni si provano dalla
fase 4).

## Procedura F1–F23 (tutto il pacchetto del 07/11: sezioni A–H)

Rigenerata il 07/11/2026 sera con la sezione H: numerazione continua **F1–F23** in ordine di esecuzione (la vecchia
F1–F17 con F11 bis/ter/quater, F13 bis e F17 bis non vale più). Corrispondenza per chi avesse già cominciato: F1–F11
uguali; **F12 nuovo** (giornaliero a blocchi); F11 bis → **F13**; F11 ter → **F14**; F12 → **F15**; F13 → **F16**;
F13 bis → **F17**; F14 → **F18**; F15 → **F19**; F11 quater → **F20**; F16 → **F21**; F17 → **F22**; F17 bis → **F23**.

Etichette: **[PC]** PowerShell sul PC, **[Server]** terminale sul server (`ssh eugenio`: la chiave ha la passphrase),
**[Cloudflare]** pannello di Cloudflare nel browser, **[Browser]** il sito. **Da casa o da rete mobile**: la rete
aziendale blocca statocritico.it e il pannello di Cloudflare. Comandi PowerShell **una riga alla volta** (un riquadro per
riga); sul server un comando per riga, si possono incollare insieme. Nessun valore segreto in questi comandi.

Punto di partenza: clone `C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio` al commit `60d8a7c` (online
`?v=20261106a`), zip `C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio_2026-11-07.zip`, archivi in
`C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\` (19 `.tar.gz` + `SHA256SUMS.txt`; la sottocartella
`parti\` **non** si copia).

### Procedura breve

1. **[PC]** F1–F4: clone pulito a `60d8a7c`, zip estratto sopra, controlli dei file, `costruisci_pagine.py --controlla`
   e test della fase 5, segreti esclusi.
2. **[PC]** F5–F9: pacchetti del codice e del sito, impronte dei 19 archivi, copia sul server.
3. **[Server]** F10–F11: copie di sicurezza, codice nuovo, rebuild di `energia-api` e `energia-edifici`, api, worker e
   Caddy ricreati; `docker compose ps` con IMAGE `energia-api` per api e worker.
4. **[Server]** F12: giornaliero meteo a blocchi (worker fermo, copia, verifica, conversione una volta sola, verifica).
5. **[Server]** F13–F14: ripiego OSM e prova dell'istanza Overpass europea; coda «Aggiungi DBTR» (`edifici-coda`).
6. **[Server]** F15–F18: 19 archivi DBTR con `sha256sum -c` e `archivi.json`; DTM quadrante SE e `dtm-server`; facoltativi.
7. **[Server]** F19: sito, `crontab -l` = 1 riga, pulizia. **[Cloudflare]** F20: rate limiting senza `/api/ortofoto/` e
   `/api/terreno/`.
8. **[Browser]** F21: prove (Modelli 3D, Edificio, Fotovoltaico, Aggiungi edifici, pagina interna, terreno, Novità, meteo).
9. **[PC]** F22–F23: commit, push e release GitHub `v2026.11.07`.

### Tempi indicativi

| Parte | Passi | Tempo |
|---|---|---|
| PC: controlli, test della fase 5 | F1–F4 | 15–20 min |
| PC: pacchetti e copia (160 MB di archivi) | F5–F9 | 10 min |
| Server: copie e rebuild delle immagini | F10–F11 | 10–15 min |
| Server: giornaliero a blocchi | F12 | 2–5 min (fino a 30 min se il file è nazionale e non ordinato) |
| Server: OSM, coda, archivi | F13–F15 | 15 min |
| Server: DTM SE (download e `dtm-server`) | F16–F17 | 20–30 min (si lavora ad altro intanto) |
| Server: sito, crontab; Cloudflare | F19–F20 | 10 min |
| Browser: prove | F21 | 30–45 min |
| PC: commit e release | F22–F23 | 10 min |
| **Totale** | | **circa 2 ore e mezza** (F18 facoltativo escluso) |

### Parte 1 – PC: zip, controlli e test

**F1. [PC]** Stato del clone:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git fetch
```
```powershell
git status -sb | Select-Object -First 1
```
```powershell
git log --oneline -1
```
```powershell
git status --short | Measure-Object
```
Cosa aspettarsi: `## main...origin/main` senza `[behind …]`; `60d8a7c …`; `Count : 0`.

Cosa fare se va male: `[behind N]` o un commit diverso da `60d8a7c` → fermati e mandami `git log --oneline origin/main -3`;
`Count` diverso da 0 → mandami `git status --short`.

**F2. [PC]** Estrai lo zip sopra il clone e controlla:
```powershell
dir ..\eugenio_2026-11-07.zip
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-07.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261107a" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
```powershell
git status --short fase11-visure
```
```powershell
git status --short fase3-storico
```
```powershell
git status --short fase4-server
```
Cosa aspettarsi: lo zip è il progetto intero (circa 6 MB); `Count : 1`; i file nuovi (`??`) sono
`AGGIORNAMENTO_2026-11-07.md`, `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md`, in `fase10-edifici3d` `edifici3d/dtm_locale.py`,
`edifici3d/coda.py`, `edifici3d/archivi.py`, `edifici3d/plausibilita.py` e i test `dbtr_sintetici.py`, `dbtr_node.js`,
`test_coda.py`, `test_dbtr_parita.py`, `test_dbtr_browser.py`, `test_plausibilita.py`; in `fase4-server`
`servizio/edifici_osm.py`, `servizio/dbtr_coda.py`, `servizio/terreno.py`, `tests/test_edifici_osm.py`,
`tests/test_dbtr_coda.py`, `tests/test_terreno.py`, `tests/test_notiziario_novita.py`, `tests/test_giornaliero_blocchi.py`;
in `fase5-sito/sito` `aggiungi-dbtr.html`, `dbtr-istruzioni.html`, `aggiungi_dbtr.js`, `dbtr_worker.js`, `dbtr_lettore.js`,
`dbtr_locale.js`, `novita.html`, `novita.xml`, le cartelle `lib/sql.js/` e `lib/fflate/`; `fase5-sito/novita.toml`.
`fase11-visure` **non stampa nulla**. `fase3-storico` stampa ` M` per `README.md`, `meteo_storico/__main__.py`,
`meteo_storico/aggrega.py`, `meteo_storico/scarica.py`. `fase4-server` stampa le righe ` M` di `.env.example`,
`Caddyfile`, `docker-compose.yml`, `README.md`, `api/Dockerfile`, `api/requirements.txt`, `servizio/app.py`, `config.py`,
`meteo.py`, `notiziario.py`, `protezione.py`, `strati.py`, `worker.py`, `tests/test_strati.py` e le `??` sopra;
**non** compaiono `tests/test_meteo_nazionale.py` né `tests/test_scarica_risposte.py` (sono già nel repository e non
sono cambiati).

Cosa fare se va male: `Count : 0` = zip vecchio (riscaricalo); righe di `fase11-visure`, altri file di `fase4-server` o i
due test sopra con ` M`: fermati e mandami le righe.

**F3. [PC]** Pagine e test della fase 5:
```powershell
cd fase5-sito
```
```powershell
python costruisci_pagine.py --controlla
```
```powershell
python -m pytest -q tests
```
```powershell
cd ..
```
Cosa aspettarsi: `versione 20261107a: 0 file da rigenerare`; `50 passed, 1 skipped` (senza Playwright e Chromium sul PC
molti si saltano: va bene). Gli altri test li ho eseguiti io nel container: **fase 4 215 passed, 0 failed** (i 4 rossi del
commit `60d8a7c` ora passano), fase 10 126 passed.

Cosa fare se va male: `file da rigenerare` → `python costruisci_pagine.py` e di nuovo `--controlla`, poi dimmelo; test
rossi → mandami le ultime 30 righe.

**F4. [PC]** Segreti, file privati e copie identiche:
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x
```
```powershell
git ls-files fase2-gradi-giorno fase10-edifici3d/uni_privato
```
```powershell
fc.exe /b EUGENIO_PER_AGENTI.md fase5-sito\sito\EUGENIO_PER_AGENTI.md
```
Cosa aspettarsi: quattro righe `.gitignore:…`; nessuna riga; `FC: nessuna differenza riscontrata`.

Cosa fare se va male: meno di quattro righe o file elencati dal secondo comando → fermati e mandameli (niente commit).

### Parte 2 – PC: pacchetti e copia sul server

**F5. [PC]** Pacchetto del codice (fasi 3, 4, 6–10 e `novita.toml`, che serve alla build dell'api):
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=.venv-build --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude=uni_privato --exclude=node_modules .dockerignore fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d fase5-sito/novita.toml
```
```powershell
tar -tzf ..\codice.tar.gz | Select-String -Pattern "uni_privato|dtm_locale|edifici_osm|dbtr_coda|coda\.py|terreno\.py|plausibilita|novita|aggrega|giornaliero_blocchi|meteo_nazionale|scarica_risposte|\.env$"
```
Cosa aspettarsi: **17 righe**: `fase3-storico/meteo_storico/aggrega.py`; in `fase4-server` `servizio/terreno.py`,
`dbtr_coda.py`, `edifici_osm.py` e i test `test_giornaliero_blocchi.py`, `test_meteo_nazionale.py`,
`test_notiziario_novita.py`, `test_dbtr_coda.py`, `test_scarica_risposte.py`, `test_edifici_osm.py`, `test_terreno.py`; in
`fase10-edifici3d` `tests/test_coda.py`, `tests/test_plausibilita.py`, `edifici3d/dtm_locale.py`, `coda.py`,
`plausibilita.py`; `fase5-sito/novita.toml`. Nessun `uni_privato`, nessun `.env` (`.env.example` non compare perché
finisce con `.example`).

Cosa fare se va male: compare `uni_privato` o una riga che finisce con `.env` → cancella `..\codice.tar.gz` e mandami le
righe; manca `novita.toml` → la build dell'api in F11 si fermerebbe: rifai il primo comando dalla cartella del clone.

**F6. [PC]** Pacchetto del sito:
```powershell
cd fase5-sito
```
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
```
```powershell
cd ..
```
Cosa aspettarsi: nessun messaggio; `..\sito.tar.gz` accanto a `..\codice.tar.gz`.

**F7. [PC]** Archivi degli edifici dei 19 comuni (rigenerati il 07/11 senza DTM e con le altezze non plausibili portate
alla stima; un tar per comune, 160 MB in tutto), con le impronte:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici
```
```powershell
(Get-ChildItem *.tar.gz).Count
```
```powershell
Get-ChildItem *.tar.gz | ForEach-Object { (Get-FileHash $_ -Algorithm SHA256).Hash.ToLower() + "  " + $_.Name } | Compare-Object (Get-Content SHA256SUMS.txt) | Measure-Object
```
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
Cosa aspettarsi: `19`; poi `Count : 0` (impronte uguali a `SHA256SUMS.txt`).

Cosa fare se va male: il confronto stampa righe → mandamele (se `SHA256SUMS.txt` ha un solo spazio tra impronta e nome,
confronta a occhio con `Get-Content SHA256SUMS.txt`; il controllo vero si rifà sul server in F15 con `sha256sum -c`).
La sottocartella `parti\` non si copia (si può cancellare).

**F8. [PC]** Copia sul server (ogni comando chiede la passphrase della chiave; prima la cartella, poi i file):
```powershell
ssh eugenio "mkdir -p ~/archivi_edifici"
```
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
```powershell
scp C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\*.tar.gz C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\SHA256SUMS.txt eugenio:~/archivi_edifici/
```
Cosa aspettarsi: righe con `100%` (gli archivi, 160 MB: un paio di minuti).

Cosa fare se va male: `Connection timed out` → sei sulla rete aziendale: passa a casa o alla rete del telefono;
`Permission denied (publickey)` → passphrase sbagliata, riprova.

**F9. [PC]** Facoltativo: il GeoPackage di Rimini sul server (serve solo per rifare l'archivio là in F18.1):
```powershell
scp C:\Users\ingpa\Documents\claude\pj\statocritico\dbtr\rimini_2026-11-05\estraz_procons.gpkg eugenio:~/rimini_estraz_procons.gpkg
```

### Parte 3 – Server: codice, immagini e meteo

**F10. [Server]** Entra (`ssh eugenio`), poi copie di sicurezza, spazio libero, codice nuovo:
```bash
cp -a ~/energia ~/energia_prima_20261107a
crontab -l > ~/crontab_prima_20261107a.txt; wc -l ~/crontab_prima_20261107a.txt
df -h /srv
tar -xzmf ~/codice.tar.gz -C ~/energia && ls ~/energia/fase10-edifici3d/edifici3d/dtm_locale.py ~/energia/fase4-server/servizio/edifici_osm.py ~/energia/fase4-server/tests/test_giornaliero_blocchi.py
grep -c "def aggiorna_a_blocchi" ~/energia/fase3-storico/meteo_storico/aggrega.py
test -d ~/energia/fase10-edifici3d/uni_privato && echo PRESENTE || echo assente
grep -E "^(REGIONI|REGIONI_AGGIORNATE|EDIFICI_OSM|CARTELLA_DATI)=" ~/energia/fase4-server/.env
```
Cosa aspettarsi: `1 …crontab_prima_20261107a.txt`; `df` con almeno 5 GB liberi; i tre file; `1`; `assente` (oppure
`PRESENTE` se il modulo privato è già sul server: va bene, il tar non lo tocca); dal `.env` la riga `REGIONI=…` (di solito
`08`) e `CARTELLA_DATI=/srv/energia/dati`, **nessuna** riga `REGIONI_AGGIORNATE` né `EDIFICI_OSM`: va bene, valgono i
predefiniti (`REGIONI_AGGIORNATE` vuoto = il worker aggiorna tutte le regioni servite, **come prima**; ripiego OSM acceso).
Il `.env` non si tocca.

Cosa fare se va male: `cp` dice che la cartella esiste → usa `~/energia_prima_20261107b`; `CARTELLA_DATI` diversa →
usa quella cartella al posto di `/srv/energia/dati` in tutti i passi seguenti.

**F11. [Server]** Rebuild dell'immagine unica di api e worker (ripiego OSM, coda, terreno, meteo a blocchi), api e worker
ricreati sulla stessa immagine, immagine della pipeline degli edifici, Caddy ricreato:
```bash
cd ~/energia/fase4-server && docker compose build api
docker compose up -d --force-recreate api worker
docker compose --profile edifici build edifici-lidar
docker compose --profile edifici run --rm edifici-lidar --help | head -3
docker compose up -d --force-recreate caddy
sleep 60; docker compose ps api worker caddy
```
(il Caddyfile ha i blocchi nuovi `/api/dbtr/*`, con il limite di 40 MB per richiesta, e `/api/terreno/*`, e il tipo di
`/novita.xml`: per questo Caddy si ricrea)

Cosa aspettarsi: la build dell'api finisce con `Built` (qualche minuto: ruote di shapely, pyproj e rasterio per ARM); poi
`Started`; la build di `energia-edifici` con `Built`; l'aiuto di `edifici3d`; in `docker compose ps` `api` `Up …
(healthy)`, `worker` `Up`, `caddy` `Up`, **api e worker con IMAGE `energia-api`**.

Cosa fare se va male: IMAGE `sha256:…` per api o worker → `docker compose up -d --force-recreate api worker` e di nuovo
`docker compose ps api worker`; api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe.
Per tornare indietro: `rm -rf ~/energia && mv ~/energia_prima_20261107a ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker caddy`.

**F12. [Server]** Giornaliero meteo a blocchi (sezione H): worker fermo, copia di sicurezza, verifica, conversione **una
volta sola**, verifica, prova di lettura, worker di nuovo acceso. Il primo comando dice se il file c'è:
```bash
ls -l /srv/energia/dati/giornaliero.parquet
docker compose stop worker
cp -a /srv/energia/dati/giornaliero.parquet /srv/energia/dati/giornaliero_prima_20261107a.parquet
docker compose run --rm --no-deps worker python -m meteo_storico giornaliero-blocchi --file /dati/giornaliero.parquet --solo-verifica
docker compose run --rm --no-deps worker python -m meteo_storico giornaliero-blocchi --file /dati/giornaliero.parquet
docker compose run --rm --no-deps worker python -c "from servizio import meteo; s = meteo.storico_giornaliero('099014'); print(len(s), s.data.min(), s.data.max())"
docker compose up -d worker
sleep 15; docker compose logs --tail 30 worker | grep -i "regioni"
docker compose ps api worker
```
Cosa aspettarsi:
- `ls` mostra il file (decine o centinaia di MB per l'ER, oltre 1 GB se è già nazionale);
- la verifica stampa `righe: N  row group: M  comuni: K` e `ordinato per comune: sì|no  a blocchi: no  formato: (prima
  del 07/11/2026)`;
- la conversione stampa `Convertito: N righe scritte.` (**stesso N** della verifica; di poco meno solo se c'erano righe
  doppie) e poi `a blocchi: sì  formato: giornaliero_a_blocchi_v1  comuni per blocco: 100`, con `row group` = K/100
  arrotondato in su (4 per i 330 comuni dell'ER, 79 per tutta Italia). Tempo: pochi secondi per l'ER; per il file
  nazionale 2–5 minuti se era ordinato, fino a circa 30 se non lo era (righe «blocco i di n convertito»);
- la prova di Rimini stampa circa 4.000 giorni, dal 2015 a pochi giorni fa;
- il worker scrive «Meteo: regioni servite 08, aggiornate ogni giorno tutte quelle servite» (o le regioni del tuo `.env`);
- `docker compose ps`: api e worker `Up` con IMAGE `energia-api`.

Cosa fare se va male:
- `ls` dice «No such file or directory» → l'archivio meteo non c'è e non c'è niente da convertire: salta il `cp` e i tre
  `docker compose run`, esegui `docker compose up -d worker` e le ultime due righe, poi continua con F13;
- la conversione si interrompe (connessione caduta, errore) → rilancia **lo stesso comando**: riprende dai blocchi già
  fatti in `/srv/energia/dati/giornaliero.parziale/`; il file originale resta valido fino alla fine;
- `MemoryError` o `Killed` → mandami le ultime righe; intanto `docker compose up -d worker` (il file vecchio funziona
  ancora: il worker lo convertirà da solo al primo aggiornamento dello storico, con la stessa memoria limitata);
- per tornare al file di prima: `docker compose stop worker`, poi
  `cp -a /srv/energia/dati/giornaliero_prima_20261107a.parquet /srv/energia/dati/giornaliero.parquet`, poi
  `rm -rf /srv/energia/dati/giornaliero.parziale /srv/energia/dati/giornaliero.parquet.nuovo`, poi `docker compose up -d worker`.
La copia `giornaliero_prima_20261107a.parquet` si tiene finché il worker non ha aggiornato lo storico almeno una volta
(domani dopo le 6, `docker compose logs worker | grep "Storico aggiornato"`), poi si cancella.

**F13. [Server]** Ripiego OSM dal vivo, dentro l'api (senza Turnstile la rotta risponde; con Turnstile acceso risponde 401,
ed è giusto: la si prova dal browser in F21), poi la **prova dell'istanza di riserva di Overpass dal server** (Overpass
API Europa al posto di maps.mail.ru), una sola volta per istanza:
```bash
docker compose exec -T api python -c "import edifici3d.osm_campione as o, shapely, pyproj; print('lettore ok', shapely.__version__, pyproj.__version__)"
docker compose exec -T api python -c "import urllib.request as u, json; r=u.urlopen('http://localhost:8000/api/protezione'); print(json.load(r)['rotte'])"
docker compose exec -T api python -c "from servizio import strati as S; print(S.istanze_overpass())"
docker compose exec -T api python -c "import time, httpx; from servizio import strati as S; from edifici3d import osm_campione as O
for u in S.istanze_overpass():
    t = time.time()
    try:
        r = S._scarica(u, O.query_punto(12.906, 43.904), 40); print(u, r.status_code, round(time.time() - t, 1), 's', r.content.count(b'<way'), 'way')
    except Exception as e: print(u, 'NON RISPONDE', type(e).__name__)"
```
Cosa aspettarsi: `lettore ok 2.2.0 3.8.0`; l'elenco delle rotte protette con `edifici_osm` e `dbtr` in fondo;
`['https://overpass-api.de/api/interpreter', 'https://ovp.dresel.systems/api/interpreter']` (nessun `mail.ru`); due righe
`… 200 … s 300–400 way` (Pesaro), una per istanza; va bene anche se la principale dice `502`/`504` (sovraccarica a tratti).

Cosa fare se va male: se `ovp.dresel.systems` dice `NON RISPONDE` o un codice diverso da 200 (ripeti una volta dopo un
minuto): niente riserva, così il ripiego dice chiaramente che OpenStreetMap non risponde quando la principale è giù:
`echo "OVERPASS_RISERVA=" >> ~/energia/fase4-server/.env && docker compose up -d --force-recreate api worker`, poi rifai il
terzo comando (deve stampare solo `overpass-api.de`) e scrivimelo (lo annoto in DA_FARE). Il Turnstile del ripiego resta
acceso (confermato da Paolo).

**F14. [Server]** Coda «Aggiungi DBTR»: cartella con i permessi per l'utente 1000, servizio `edifici-coda`, rotte:
```bash
sudo mkdir -p /srv/energia/dati/edifici_coda && sudo chown 1000:1000 /srv/energia/dati/edifici_coda && sudo chmod 750 /srv/energia/dati/edifici_coda
ls -ld /srv/energia/dati/edifici_coda
docker compose --profile edifici up -d edifici-coda
sleep 20; docker compose --profile edifici logs --tail 5 edifici-coda
docker compose exec -T caddy wget -qO- --post-data='{}' --header='Content-Type: application/json' http://localhost/api/dbtr/inizia 2>&1 | head -c 200; echo
```
Cosa aspettarsi: `drwxr-x--- … 1000 1000 … edifici_coda`; il registro dice «coda «Aggiungi DBTR» avviata: /dati/edifici_coda
→ /dati/edifici»; l'ultimo comando risponde con un errore 401 (verifica anti-robot) o 422 (campi mancanti): va bene, la
rotta c'è. Con le ACL già messe sulla cartella dei dati il `chown` è comunque innocuo.

Cosa fare se va male: il servizio si ferma con «Permission denied» → rifai il `chown`; per spegnere le proposte senza
toccare il resto: `DBTR_CODA=false` nel `.env` e `docker compose up -d --force-recreate api` (la lettura nel browser resta).

**F15. [Server]** Archivi DBTR dei 19 comuni (impronte controllate con `sha256sum -c`) e `archivi.json` (archivio di prova
OSM tolto dall'elenco, file lasciati):
```bash
grep CARTELLA_EDIFICI ~/energia/fase4-server/.env || echo "predefinita: /srv/energia/dati/edifici"
cp /srv/energia/dati/edifici/archivi.json ~/archivi_prima_20261107a.json
cd ~/archivi_edifici && sha256sum -c SHA256SUMS.txt | grep -vc ': OK$'; cd ~/energia/fase4-server
rm -f /srv/energia/dati/edifici/cc-by/er/*/prodotti/terreno.pmtiles /srv/energia/dati/edifici/cc-by/er/*/prodotti/dtm_cog.tif
for f in ~/archivi_edifici/*.tar.gz; do tar -xzf "$f" -C /srv/energia/dati/edifici || echo "ERRORE $f"; done
ls /srv/energia/dati/edifici/cc-by/er/ | wc -l; ls /srv/energia/dati/edifici/cc-by/er/rimini/prodotti
docker compose --profile edifici run --rm edifici-lidar archivi-json --archivio /dati/edifici
docker compose exec -T api python -c "import urllib.request as u, json; d=json.load(u.urlopen('http://caddy/edifici3d/archivi.json')); print(len(d['archivi']), [a['base'] for a in d['archivi']], d.get('lidar'))"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://caddy/edifici3d/cc-by/er/rimini/prodotti/indice.json'); print(r.status, r.headers['Content-Type'])"
```
(se il primo comando stampa una cartella diversa, usala al posto di `/srv/energia/dati/edifici`)

Cosa aspettarsi: `0` (tutte le impronte `OK`); nessuna riga «ERRORE»; `19` o `20` cartelle in `cc-by/er/` (i 19 comuni, più
`grezzi` se c'è); `contesto  corpi.pmtiles  indice.json` (il terreno non è più negli archivi: F17); `archivi-json` stampa
il JSON con **19 archivi** `/edifici3d/cc-by/er/<comune>/prodotti/`, ognuno con `"istat"` tranne Ravenna (parziale), e
`"lidar": "/edifici3d/cc-by/er/prodotti/"`; dall'api `19`, l'elenco delle basi e `/edifici3d/cc-by/er/prodotti/`, poi
`200 application/json`. Alla fine: `rm -r ~/archivi_edifici`.

Cosa fare se va male: il primo numero non è `0` → `cd ~/archivi_edifici && sha256sum -c SHA256SUMS.txt | grep -v ': OK$'`
e mandami le righe (ricopia quei tar con F8); `Permission denied` scrivendo `archivi.json` → `sudo chown -R 1000:1000
/srv/energia/dati/edifici` e rifai il comando; per tornare all'elenco di prima:
`cp ~/archivi_prima_20261107a.json /srv/energia/dati/edifici/archivi.json`.

**F16. [Server]** DTM 5 m, quadrante SE (Romagna), scaricato direttamente sul server (serve a `dtm-server` in F17 e per
preparare altri comuni sul server):
```bash
mkdir -p /srv/energia/dati/edifici/cc-by/er/grezzi/dtm5 && cd /srv/energia/dati/edifici/cc-by/er/grezzi/dtm5
wget -c https://mappegis.regione.emilia-romagna.it/archiviogis/DTM/DTM5x5_ed2025_SE_7791.zip
stat -c %s DTM5x5_ed2025_SE_7791.zip
unzip -l DTM5x5_ed2025_SE_7791.zip
cd ~/energia/fase4-server
```
Cosa aspettarsi: lo scaricamento (1,4 GB, qualche minuto); `1459636279` esatti; `unzip -l` con `DTM5x5_ed2025_SE_7791.tif`
(1.873.783.580 byte), `licenza/…_licenza.pdf` e `metadati/…`. **Non estrarlo**: il codice lo legge dentro lo zip.

Cosa fare se va male: dimensione diversa → rilancia lo stesso `wget -c` (riprende); `404` → l'indirizzo pubblico è
`https://servizimoka.regione.emilia-romagna.it/download/api/packs?p=2806`; alternativa:
`docker compose --profile edifici run --rm edifici-lidar scarica --fonte dtm5 --quadrante SE --archivio /dati/edifici`.

**Nota del 07/11 sera (pubblicazione in corso)**: le immagini `python:3.12-slim` non hanno più `libexpat1`, che serve a
`rasterio` («ImportError: libexpat.so.1»). Aggiunto `libexpat1` all'`apt-get install` di `fase10-edifici3d/Dockerfile` e
`fase4-server/api/Dockerfile`: dopo averli copiati, rifare la build di `energia-edifici` (e dell'api, se `import rasterio`
fallisce anche lì) prima di F17.

**F17. [Server]** DTM per il terreno 3D (sezione E): il quadrante SE convertito **una volta** in un COG nella cartella della
rotta `/api/terreno` (comando `dtm-server`), poi una prova della rotta:
```bash
sudo mkdir -p /srv/energia/dati/terreno && sudo chown 1000:1000 /srv/energia/dati/terreno
docker compose --profile edifici run --rm edifici-lidar dtm-server --file /dati/edifici/cc-by/er/grezzi/dtm5/DTM5x5_ed2025_SE_7791.zip --uscita /dati/terreno/dtm5_er_se.tif
ls -l /srv/energia/dati/terreno
docker compose exec -T api python -c "import urllib.request as u, json; print(json.load(u.urlopen('http://localhost:8000/api/terreno/fonti'))['dtm'])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/terreno/15/17432/11870.png'); print(r.status, r.headers['X-Terreno-Fonte'], len(r.read()))"
```
Cosa aspettarsi: il comando lavora 10–20 minuti (una CPU) e stampa un JSON con `"byte": 1304050538` circa e
`"crs": "EPSG:7791"`; `ls` mostra `dtm5_er_se.tif` (~1,3 GB) e `dtm5_er_se.json`; la rotta elenca il DTM con «Regione
Emilia-Romagna – DTM 5×5 m (edizione 2025), CC BY 4.0»; la tessera di prova (Brisighella) `200 dtm` e ~100.000 byte. Lo
zip in `grezzi/dtm5/` resta (serve a `prepara`).

Cosa fare se va male: `Permission denied` su `/dati/terreno` → rifai il `chown`; la rotta risponde 404 → l'api non è stata
ricostruita (F11) o `TERRENO_ATTIVO=false` nel `.env`; la tessera dice `copernicus` invece di `dtm` → manca la scheda
`.json` accanto al `.tif` (rifai il comando).

**F18. [Server]** Facoltativi:
1. Rifare Rimini sul server dal GeoPackage di F9 (prova che il codice gira là; 5–10 minuti, ~1 GB di memoria):
   ```bash
   mkdir -p /srv/energia/dati/edifici/cc-by/er/grezzi/dbtr/rimini && mv ~/rimini_estraz_procons.gpkg /srv/energia/dati/edifici/cc-by/er/grezzi/dbtr/rimini/estraz_procons.gpkg
   docker compose --profile edifici run --rm edifici-lidar controlla-uvl --gpkg /dati/edifici/cc-by/er/grezzi/dbtr/rimini/estraz_procons.gpkg
   docker compose --profile edifici run --rm edifici-lidar prepara --comune rimini --gpkg /dati/edifici/cc-by/er/grezzi/dbtr/rimini/estraz_procons.gpkg --dtm /dati/edifici/cc-by/er/grezzi/dtm5/DTM5x5_ed2025_SE_7791.zip --archivio /dati/edifici
   docker compose --profile edifici run --rm edifici-lidar controlla-archivio /dati/edifici/cc-by/er/rimini/prodotti --punto 12.567964 44.061369 Biblioteca --punto 12.587865 44.046762 Ospedale
   ```
   Cosa aspettarsi: `controlla-uvl` con 42804 corpi; `prepara` con `"corpi": 40518`; `controlla-archivio` con `"problemi": []`.
2. Rigenerare l'archivio di prova OSM con i cortili (senza rete), solo se vuoi tenerlo:
   ```bash
   docker compose --profile edifici run --rm edifici-lidar osm-campione --riquadro 12.5600 44.0555 12.5735 44.0640 --nome rimini-prova --archivio /dati/edifici --osm /dati/edifici/odbl/rimini-prova/grezzi/mappa.osm --dtm /dati/edifici/odbl/rimini-prova/grezzi/dtm5.tif
   ```
   (se `grezzi/` non c'è – il tar del 05/11 aveva solo i prodotti – lascialo com'è).

**F19. [Server]** Sito, crontab, pulizia:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261107a /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/interno/edifici.html
grep -c 'id="livelli-mappa"' /srv/energia/sito/modelli3d.html
ls /srv/energia/sito/aggiungi-dbtr.html /srv/energia/sito/dbtr-istruzioni.html /srv/energia/sito/lib/sql.js/sql-wasm.wasm /srv/energia/sito/lib/fflate/fflate.js /srv/energia/sito/novita.html /srv/energia/sito/novita.xml
grep -c 'id="genera-3d"' /srv/energia/sito/edificio-geometria.html /srv/energia/sito/fv-producibilita.html
grep -c "risposta interrotta" /srv/energia/sito/novita.html
docker compose exec -T caddy wget -qS -O /dev/null http://localhost/novita.xml 2>&1 | grep -i content-type
crontab -l
crontab -l | wc -l
rm ~/codice.tar.gz ~/sito.tar.gz
exit
```
Cosa aspettarsi: tre righe con N > 0; `1`; i sei file; `1` per le due pagine 3D; `1`;
`Content-Type: application/atom+xml; charset=utf-8`; il crontab con **una sola riga**, `edifici-lidar` alle 3:30, e poi
`1` (il worker fa mercati, previsioni, storico, indicatori e clima; la coda «Aggiungi DBTR» è un servizio sempre acceso:
nessuno dei due va nel crontab). La notte la pipeline LiDAR comincia le tessere della costa (pagina interna: da «In
attesa» a «Zona in corso»).

Cosa fare se va male: `crontab -l | wc -l` diverso da 1 → mandami `crontab -l` (righe `servizio.worker …` sono doppioni
del worker e vanno tolte con `crontab -e`; la copia di prima è in `~/crontab_prima_20261107a.txt`); pagina vecchia →
controlla di essere nella cartella giusta e rifai il `tar`.

### Parte 4 – Cloudflare

**F20. [Cloudflare]** Regola di rate limiting su `/api/` (quella del 04/11, 60 richieste in 10 s): il 3D chiede 30–80
tessere del terreno insieme, quindi la regola deve escludere `/api/ortofoto/` **e** `/api/terreno/`. Cloudflare →
`statocritico.it` → Security → WAF → **Rate limiting rules** → la regola su `/api/` → **Edit expression** e incolla:
```
(starts_with(http.request.uri.path, "/api/") and not starts_with(http.request.uri.path, "/api/ortofoto/") and not starts_with(http.request.uri.path, "/api/terreno/"))
```
→ **Save**. Cosa aspettarsi: la regola salvata con l'espressione nuova, sempre 60 richieste in 10 s per IP.

Cosa fare se va male: non trovi la regola o ha un'altra forma → mandami uno screenshot dell'espressione (senza toccarla);
il pannello non si apre → sei sulla rete aziendale.

### Parte 5 – Prove nel browser (Ctrl+F5; F12 → Console)

**F21. [Browser]** Su `https://eugenio.statocritico.it`:
1. **Modelli 3D**: «via Gambalunga 27», «Rimini» → la mappa va sul punto a **zoom 17**; si colora l'edificio del punto (se
   cade sull'edificio accanto, trascinalo sulla Biblioteca) → «Edificio … scelto (sagome: Regione Emilia-Romagna – DBTR,
   CC BY 4.0)», sagome con i **cortili**. **Genera il 3D**: «Fonte del 3D per corpo: DB topografico regionale»; a destra
   «Palazzo Gambalunga – Biblioteca», foglio 74, numero 1100; tabella dei corpi (2 corpi, 13 e 14 m). PNG o PDF: in fondo
   «Regione Emilia-Romagna – DBTR, CC BY 4.0».
2. **Livelli della mappa**: sono il passo **1** della colonna destra (sopra «Edificio»), con Ortofoto, fonte, particelle e
   contorni; legenda e attribuzioni sotto la mappa.
3. **viale Settembrini 2, Rimini**: l'ospedale è **coperto**; se il punto cade sull'istituto «Leonardo da Vinci» accanto,
   trascinalo sul padiglione; Genera il 3D (14 corpi, «sede di ospedale», foglio 99 numero 1).
4. **Fuori dal DBTR, ripiego OSM** (i tratteggi sono il **confine del comune**):
   - «piazzale Cinelli 4», «Pesaro»: dopo qualche secondo («chiedo gli edifici a OpenStreetMap…») sagome **tratteggiate**
     OSM e il messaggio «Qui non c'è ancora il DBTR: si usa OpenStreetMap come ripiego (© OpenStreetMap contributors, ODbL
     1.0)…»; **Genera il 3D**: tabella dei corpi con l'origine dell'altezza e «OpenStreetMap · ODbL 1.0», scheda con
     «Licenza delle sagome: ODbL 1.0»; PDF e report con la riga «© OpenStreetMap contributors…»;
   - per provare il ripiego in Emilia-Romagna serve un comune **non** scaricato, per esempio «via Emilia 1», «Imola»: stesso
     comportamento (Cesena e Riccione sono tra i 19 comuni del DBTR: lì sagome DBTR, nessun OSM; testo corretto il 07/11 sera);
   - di nuovo «via Gambalunga 27», «Rimini»: sagome DBTR, nessuna chiamata `edifici/osm` (F12 → Rete);
   - se Overpass non risponde: «… OpenStreetMap, il ripiego per queste zone, non ha risposto (…)» e «Genera il 3D» spento.
5. **Ortofoto**: ricerca → zoom 17; «mostra i contorni degli edifici dell'archivio 3D» disegna le sagome DBTR.
6. **Aggiungi edifici (DB topografico)** (menu Patrimonio, «S»): regione Emilia-Romagna, comune «Lugo», carica lo zip (o il
   `.gpkg`) di `dbtr\lugo_2026-11-06`: «File letto…: 19.906 corpi» (o quasi), gli edifici colorati sulla mappa; **Apri in
   Modelli 3D**: Lugo con «Edifici del tuo file…», clic su un edificio, «Genera il 3D»; F12 → Rete: **nessuna** richiesta
   `/api/dbtr/`; «Togli gli edifici del file» torna agli archivi del server. Solo se vuoi provare la coda: spunta il
   consenso, **Invia il file** (avanzamento a pezzi, poi «Grazie! File ricevuto…»).
7. **Pagina interna** `/interno/edifici.html` (Cloudflare Access): in cima «DB topografici proposti» con la proposta di Lugo
   («ricevuto», poi «in attesa di approvazione»); clic: esito, anteprima, «SOSTITUISCE l'archivio attuale»; **Rifiuta** (è
   una prova) e la riga passa in «Ultime decisioni».
8. **Scaricare i DB topografici** (menu Patrimonio): sei sezioni regionali e la tabella delle altre regioni; F.A.Q.
   «Posso aggiungere io gli edifici del mio comune?»; Privacy, riga «Database topografico».
9. **Terreno dal server**: Modelli 3D a Brisighella (centro del paese, clic su un edificio), Genera il 3D: colline sotto
   gli edifici; F12 → Rete, filtro `terreno`: `/api/terreno/15/…png` con `200` e `X-Terreno-Fonte: dtm`, **nessun 429**
   (F20), nessun `terreno.pmtiles`. A Pesaro la mappa resta piatta. Bagno di Romagna, foglio 54 numero 216: «altezza
   stimata (dato DBTR non plausibile: 114 m)».
10. **Edificio e Fotovoltaico**: **Edificio › Geometria e luce naturale** apre la mappa 2D con la ricerca (non la demo);
   «via Gambalunga 27», «Rimini» → Genera il 3D → foglio 74, numero 1100, passo «Indicatori geometrici» in evidenza.
   **Fotovoltaico › Producibilità con le ombre**: stessa cosa, «Aggiungi un'area», clic sul tetto, «Calcola la
   producibilità». A Pesaro, sotto la mappa, la nota «Edifici OpenStreetMap nella vista: …». Con la prova 6 fatta, nella
   stessa scheda, Fotovoltaico › Ombre usa gli edifici del file.
11. **Novità**: in alto a destra «Come funziona · F.A.Q. · Sitografia · Mirror · **Novità** · Contattaci»; la pagina mostra
   il 7 novembre 2026 in cima, con in «Corretto» la riga sull'aggiornamento del meteo; dal telefono nessuno scorrimento di
   lato e «Novità» nel menu; `https://eugenio.statocritico.it/novita.xml` si apre come feed.
12. **Meteo** (sezione H): Clima e meteo › **Legge 10**, comune Rimini: i dati climatici compaiono come prima (o il
   messaggio «i dati meteo delle ultime stagioni non sono ancora sul server» se in F12 il file mancava); **Dati
   climatici**: stima e scarico di «Meteo giornaliero» per Rimini, un anno: il CSV si scarica; **Previsioni** › «Solo
   clima» su Rimini: le schede delle variabili meteo.
13. Console: nessuna riga rossa (a parte i 404 delle falde `lidar/` finché la pipeline non ha lavorato). Rete: la prima
   `edifici/osm` di una cella impiega 10–30 s, la seconda è immediata (copia sul server).

Cosa fare se va male: pagina vecchia → Ctrl+F5 o Cloudflare → Caching → Purge Everything; nessun edificio → F12 → Rete,
filtra `edifici3d` e mandami i codici; ripiego OSM sempre «non ha risposto» → sul server `docker compose logs --tail 40 api
| grep -i "edifici osm"` e mandami le righe; tessere del terreno con 429 → controlla l'espressione di F20; Legge 10 o Dati
climatici con un errore 500 → sul server `docker compose logs --tail 40 api` e mandami le righe (per tornare al file
meteo di prima: «Cosa fare se va male» di F12).

### Parte 6 – Commit, push e release

**F22. [PC]** Nel clone (gli archivi degli edifici **non** sono nel clone):
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_dbtr|estraz_procons|\.gpkg$|DTM5x5|archivi_edifici|giornaliero.*\.parquet"
```
```powershell
git commit -m "07/11/2026: Modelli 3D con i cortili, messaggio fuori zona, zoom 17, Livelli nella colonna destra; multipoligoni OSM coi fori; DBTR vero dei comuni (un archivio per comune, regole delle altezze verificate sul LiDAR, archivi-json, controlla-archivio); DTM 5 m dai quadranti; ripiego OpenStreetMap al volo fuori dal DBTR (GET /api/edifici/osm); Aggiungi edifici (DB topografico) con lettura nel browser, coda sul server con consenso, servizio edifici-coda e approvazione interna; terreno 3D dal server (/api/terreno, dtm-server); pagine 3D unificate; altezze OSM dai corpi DBTR vicini; riserva Overpass europea; pagina Novità con feed Atom; giornaliero meteo nazionale a blocchi (comando giornaliero-blocchi), REGIONI_AGGIORNATE, nuovo tentativo sulle risposte troncate di Open-Meteo, test della fase 4 tutti verdi; sito ?v=20261107a"
```
```powershell
git push
```
```powershell
git log --oneline -2
```
Cosa aspettarsi: il secondo comando **non stampa nulla**; il push finisce con `… main -> main`; in cima il commit nuovo,
sotto `60d8a7c`.

Cosa fare se va male: il secondo comando stampa righe → `git restore --staged <percorso>` per ognuna e dimmelo; push
rifiutato → `git pull --rebase` e di nuovo `git push`.

**F23. [PC o Browser]** Release su GitHub con il testo della voce in cima a `novita.toml` (regola permanente; tag **senza**
il prefisso `visure-`, che resta per EuGEnio Visure). Da PowerShell, se `gh auth status` dice «Logged in», prima il testo
(file temporaneo fuori dal clone), poi la release:
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.07 --target main --title "EuGEnio 7 novembre 2026 – Edifici veri di 19 comuni della Romagna e pagine 3D tutte uguali" --notes-file ..\note_release.md
```
```powershell
gh release view v2026.11.07 --web
```
Cosa aspettarsi: l'indirizzo `https://github.com/statocritico/eugenio/releases/tag/v2026.11.07` e la pagina aperta con le
sezioni Nuovo, Cambiato, Corretto (in «Corretto» anche la riga sul meteo).

Senza `gh`, dal browser: 1) `https://github.com/statocritico/eugenio/releases/new`; 2) «Choose a tag» → `v2026.11.07` →
«Create new tag: v2026.11.07 on publish»; 3) «Target»: `main`; 4) titolo `EuGEnio 7 novembre 2026 – Edifici veri di 19
comuni della Romagna e pagine 3D tutte uguali`; 5) nel testo la voce del 7 novembre di
`https://eugenio.statocritico.it/novita.html` (titoli Nuovo, Cambiato, Corretto e le righe); 6) **non** spuntare
«Set as a pre-release»; 7) «Publish release».

Cosa fare se va male: `gh: command not found` → usa il browser; «tag already exists» → la release c'è già: aprila con
`gh release view v2026.11.07 --web` e controlla il testo; non creare tag `visure-…` qui.

### Per gli altri comuni (dopo il 07/11: i 19 comuni sono già in F7–F15)

Gli archivi dei comuni nuovi arrivano come tar (uno per comune, con `cc-by/er/<comune>/…`, e il loro `SHA256SUMS.txt`). Si
ripetono **F8** (solo quei tar), **F15** (`sha256sum -c`, estrazione, `archivi-json`, controllo dall'api: ogni comune intero
con il suo `istat`; un comune non nella tabella `uvl.COMUNI_ISTAT` si prepara con `--istat`, un'estrazione parziale con
`--parziale`) e **F21** su un indirizzo di ogni comune nuovo (dove prima c'era il ripiego OSM ora ci sono le sagome DBTR).
In alternativa si preparano sul server, un comune alla volta (GeoPackage o cartella Shapefile copiati con `scp` in
`/srv/energia/dati/edifici/cc-by/er/grezzi/dbtr/<comune>/`, poi i comandi di F18.1 con `--comune <comune>` e il percorso
giusto); per gli Shapefile si passa la **cartella**, non il file `.shp`. Alla fine sempre `archivi-json`.

## I – Correzioni dopo le prove (?v=20261107b)

Prove di Paolo sul sito pubblicato `?v=20261107a` (F21, 07/11 sera). Cosa è cambiato, punto per punto:

1. **Dati climatici e Legge 10 validate**: tolto l'avviso «Attenzione! Servizio sperimentale non ancora verificato» (il menu
   non le segnava già con «S»). Restano sperimentali le altre pagine.
2. **Barra di scorrimento della colonna della mappa** (Modelli 3D, Ortofoto): era a destra, attaccata al divisore
   trascinabile. Ora è **a sinistra** (`direction: rtl` sul contenitore, contenuto `ltr`), solo sul computer; le altre pagine
   con il divisore non hanno una colonna che scorre accanto al divisore (scorre la pagina, barra sul bordo destro).
3. **Vista isometrica**: l'inquadratura è circa **il doppio dell'edificio** (lato maggiore della pianta o altezza),
   centrata sull'edificio; prima zoom fisso, troppo vicino.
4. **Colori**: invariati; gli edifici **OpenStreetMap** (qualsiasi origine dell'altezza: dato OSM, piani, vicini DBTR o 9 m)
   in **marrone** `#9a6440`, nella mappa 2D e 3D, in legenda (voce visibile solo se ce ne sono) e nell'immagine scaricata
   (riga «Colori: …»).
5. **Nuova ricerca o mappa portata lontano durante il 3D**: si torna alla mappa 2D **dritta** (inclinazione 0, subito, senza
   animazione) e il 3D dell'edificio di prima si toglie. Causa del «3D piatto»: l'animazione di ritorno veniva interrotta dal
   volo verso il punto nuovo e la mappa restava inclinata con la rotazione spenta. Lontano = oltre 2 km dall'edificio.
6. **Tetti a falde stimati dal colmo DBTR**: dove il DBTR dà il colmo (`colmo` > gronda + 0,3 m, già nelle proprietà dei
   corpi degli archivi: **nessuna rigenerazione**) e non ci sono falde LiDAR, la pagina disegna un tetto **a capanna sul lato
   lungo** del rettangolo minimo del corpo o **a padiglione** se il corpo è quasi quadrato (lato lungo/lato corto < 1,3);
   niente stima per i corpi con cortile o poco rettangolari (< 70 % del rettangolo). Precedenza: falde LiDAR → colmo DBTR →
   piano. Dichiarato «tetto stimato dal colmo DBTR» in tabella dei corpi e delle falde, nel riquadro delle fonti,
   nell'immagine e nel report. Corpi con il tetto stimato: **6.946** (Rimini 4.103, Faenza 2.839, Santarcangelo 4); gli
   altri 16 comuni **non hanno H_COLMO** nel DBTR scaricato (Cesena, Forlì, Lugo: 0). **Ospedale di Rimini** (foglio 99 n.
   1, 14 corpi): H_COLMO vuoto o 0 per tutti → resta piatto finché non arrivano le falde LiDAR. Se l'utente cambia colmo o
   tipo di tetto, le falde si ristimano («tetto stimato dai valori inseriti»).
7. **Ricerca nella colonna destra**: passo **1 «Cerca l'edificio»** prima di «Livelli della mappa» (ora 2) in tutte le 9
   pagine 3D; in Ortofoto passo 1 «Cerca il luogo» prima di «Fonte». Con il **solo comune** (senza indirizzo o senza
   particella) la mappa va al **centro del comune** (baricentro del confine ISTAT dei file del sito, zoom 14), senza
   chiamare il server.
8. **Sfasamento** (misurato, otto zone: Rimini centro, ospedale e marina, Faenza, Lugo, Cesena, Brisighella, Forlì; zoom
   19, 0,21 m per pixel): **nessun errore nel nostro proxy**. WMS DBTR della Regione rispetto ai nostri archivi: **0,0 m**
   ovunque; particelle AdE dal proxy (righe riproiettate da EPSG:4258) rispetto a una riproiezione esatta pixel per pixel
   con pyproj da EPSG:25833, 6706 e 4258: **≤ 0,2 m** (un pixel); RDN2008/ETRS89 → WGS 84 in PROJ è la trasformazione nulla
   per tutte le fonti, quindi nessuno scarto di datum tra di loro. Le differenze viste da Paolo sono **dei dati**: fabbricati
   e particelle AdE rispetto al DBTR **0–5 m**, diversi da zona a zona (0 m Rimini centro, Faenza, Lugo, Forlì; ~1,5 m
   Rimini marina e Brisighella; ~5 m vicino al Bufalini di Cesena; l'ospedale di Rimini 1–4 m); ortofoto non «true ortho»:
   tetti degli edifici alti spostati di **2–5 m** rispetto alla base, edifici bassi entro ~1 m. Confini ISTAT generalizzati
   (~100 m). Dichiarato in una F.A.Q. nuova («Perché particelle, sagome e ortofoto non coincidono al metro?», `#sfasamento`)
   e nella legenda delle particelle. Test numerico: `test_colonne_e_datum_senza_scarti` (fase 4).
9. **Pulsanti che bloccavano Chrome**: le immagini (JPG, PNG, PDF) aprivano **sempre** la finestra di sistema «Salva con
   nome» (`showSaveFilePicker`); in «Aggiungi edifici» i pulsanti di scelta del file e della cartella aprono la finestra
   «Apri» (`<input type=file>`; la cartella con un'ulteriore conferma di Chrome). Se la finestra si apre fuori dallo schermo,
   Chrome è bloccato (suono a ogni clic). Ora: **download diretto** di predefinito, «Salva con nome…» solo spuntando «chiedi
   dove salvarlo»; in «Aggiungi edifici» si **trascina** il file o la cartella nella zona «Trascina qui» (il pulsante «scegli
   i file…» resta, la scelta della cartella con la finestra di sistema è tolta: le cartelle si trascinano). F.A.Q. nuova
   «Ho premuto un pulsante e Chrome non risponde più» (`#finestra-bloccata`) con i modi per sbloccare.
   «**Apri in Modelli 3D**» e «**Togli**»: in Chromium (anche sul sito pubblicato, con il GeoPackage vero di Lugo) funzionano;
   l'esito però finiva nel messaggio del passo 3, fuori vista: «comune non scelto», errori di memoria del browser e
   «tolti» non si vedevano. Ora l'esito è **accanto ai pulsanti**, i pulsanti si spengono mentre lavorano e la memoria del
   browser ha un tempo massimo (30 s).
10. **Archivi**: nessuna rigenerazione (il colmo c'è già). Cambia solo `archivi.json`: `lidar` compare solo quando la
   pipeline ha scritto `lidar/indice.json` (prima la pagina lo chiedeva e riceveva 404); la pipeline aggiorna `archivi.json`
   quando scrive il primo indice delle falde.

Altre correzioni chieste nella serata:

- **`archivi.json` vecchio nel browser** (Paolo vedeva l'archivio di prova OSM e `terreno.pmtiles`: era la copia di un
  giorno, `max-age=86400`): Caddy dà `Cache-Control: no-cache` (riconvalida con ETag) ad `archivi.json` e agli `indice.json`
  sotto `/edifici3d/`; la pagina lo chiede con `?v=<versione>` e `cache: "no-cache"`. Le celle di contesto si chiedono solo se
  l'archivio le ha (`indice.nomi_celle`: niente più 404 dei comuni vicini).
- **Bagno di Romagna «senza DBTR»**: causa principale la copia vecchia di `archivi.json`; in più, con i confini ISTAT
  generalizzati il **5 %** dei corpi DBTR dei 19 comuni (Cattolica 13 %) cadeva «fuori» e prendeva OpenStreetMap. Ora un
  punto è coperto anche se l'archivio del comune ha un corpo entro 150 m; un edificio OSM entro 30 m da un corpo DBTR si
  scarta. Verifica su 1.159 corpi veri (61 per comune): tutti coperti. Test sui 19 comuni.
- **Ortofoto nera a Brisighella**: è la RER 2023-24 che, in JPEG, dà **nero opaco** dove non ha dati (88 % della tessera
  allo zoom 13, 53 % allo zoom 14, 4 % al 15). Il proxy chiede la RER in **PNG con `TRANSPARENT=TRUE`** (`trasparente =
  true` nel TOML) e restituisce JPEG le tessere piene, PNG con la trasparenza quelle con buchi (sotto si vede il
  contesto). Copia nuova in `ortofoto/rer2023_t/`; l'indirizzo delle tessere ha `?t=1` (browser e Cloudflare non usano le
  copie nere di 30 giorni).
- **Novafeltria (0,00000, 0,00000)**: la risposta senza coordinate (`lat` vuoto diventava 0 nella pagina) non è mai un
  punto: «Indirizzo senza coordinate in ANNCSU né da Zornade … Ti porto al centro del comune». Lato server
  `zornade.coordinate()` scarta 0,0 e `_anncsu` i civici senza coordinate.
- **3D nero in collina e «salto» cambiando la fonte**: con il terreno acceso MapLibre teneva la quota del centro a **0 m**
  finché non aveva le tessere; a Bagno di Romagna (550–780 m) la camera finiva **dentro la collina** (nessuna tessera chiesta,
  tutto nero); quando poi la quota arrivava la camera saltava. Ora la quota del centro è subito quella del terreno sotto
  l'edificio (dal DTM, già nei corpi) per l'esagerazione scelta; cambiare la fonte dell'ortofoto non muove la camera.
- **Rilievo nella vista 3D**: ombreggiatura (`hillshade`, stessa sorgente di `/api/terreno`) più marcata senza ortofoto,
  colori dal tema; «Rilievo ×1 / ×1,5 / ×2» nella barra della vista 3D, dichiarato nell'immagine se diverso da ×1; in
  legenda «Terreno: DTM 5 m Regione Emilia-Romagna / Copernicus / piatto» secondo `X-Terreno-Fonte` della tessera al centro.
- **Sentinel-2 cloudless** anche nel selettore delle pagine 3D (stesso elenco e ordine di Ortofoto).
- **Pagina interna**: con la coda vuota «Nessuna proposta in coda…» al posto della tabella vuota (Paolo non aveva premuto
  «Invia il file» con il consenso: nulla era arrivato).
- **`/api/comuni` rispondeva 500** sul server (visto dal container): valori vuoti (NaN) e colonne mancanti non fermano più
  la risposta. Se dopo J5 risponde ancora 500, servono le righe del registro (J5, «cosa fare se va male»).
- **«Novità» blu**: era la copia vecchia del browser (dopo Purge e Ctrl+F5 il colore è giusto); test nuovo che confronta il
  colore di «Novità» con «F.A.Q.» in tutti i vestiti e temi.

**Aggiunte dell'08/11/2026 (stessa versione `b`, decisioni di Paolo):**

- **Ortofoto spostabile di 1 m**: quattro frecce a croce sotto la mappa (Modelli 3D e le 9 pagine 3D accanto a «Genera il
  3D»; Ortofoto accanto a «Scarica l'immagine»), stato «Ortofoto spostata: 2 m E, 1 m S» e «Azzera». Si sposta **solo la
  foto**: particelle, contorni e sagome restano dove sono. Tecnica: il proxy accetta `?de=<m>&dn=<m>` (interi ±20, solo
  fonti WMS) e chiede alla fonte il BBOX della tessera spostato di quei metri sul terreno in EPSG:3857 (la proiezione già
  usata per le richieste: scala locale dell'ellissoide, scarto < 1 cm, nessuna riproiezione dell'immagine); **nessuna
  copia su disco** delle tessere spostate (riempirebbero `ORTOFOTO_MAX_GB` scacciando le tessere normali), copia del
  browser di un giorno. Nella pagina cambia solo l'indirizzo delle tessere (`setTiles`): la camera non si muove, in 2D e
  in 3D. Fonti: RER, Toscana, Bolzano, Trento, Geoportale Nazionale (dal vivo). Sentinel-2 cloudless e ortofoto dei siti
  in PMTiles: frecce spente con il motivo (tessere già pronte; MapLibre non sposta uno strato raster). Frecce **attive
  solo con un'ortofoto spostabile e almeno uno strato vettoriale accesi** (nelle pagine 3D le sagome degli edifici ci sono
  sempre), altrimenti spente con il motivo nel tooltip. Spostamento ricordato per la sessione, azzerato cambiando fonte;
  riga «Ortofoto spostata manualmente di X m E, Y m N rispetto alla cartografia» nell'immagine scaricata e nella
  didascalia del report. F.A.Q. `#sfasamento`, `novita.toml`, `EUGENIO_PER_AGENTI.md`, `llms.txt`, README di fase 4 e 5.
- **Novità**: in fondo la voce «Meet EuGEnio» del 26/10/2026 (messa online), testo «Siamo online», senza versione.
  Poi (Paolo, 08/11 ore 09:52) **tutte le voci riscritte** per raccontare solo le funzioni per gli utenti, con i gruppi
  **Nuovo / Migliorato / Verificato** (al posto di Nuovo / Cambiato / Corretto): via protezione e verifica anti-robot,
  menu, file per gli agenti AI, copie, server; la voce `20261106a` (solo file per gli agenti) è tolta; verificati Costi
  energetici Sanità (05/11) e Dati climatici e Legge 10 (`20261107b`). `costruisci_pagine.py` rifiuta i campi sconosciuti
  (i vecchi `cambiato`/`corretto`), la newsletter usa gli stessi gruppi, J12 legge i gruppi nuovi.
  Infine (Paolo, 09:55) la **versione del sito non compare più** né in `novita.html` né in `novita.xml` né nella
  newsletter né nel testo della release (J12: la versione resta nel nome del tag): resta solo in `novita.toml` (test con
  `index.html`). Ancore e identificativi del feed per data, stabili: `#d20261107`, `#d20261107-2` per la seconda voce
  dello stesso giorno (gli identificativi del feed cambiano una volta rispetto a `?v=20261107a`: un lettore di feed può
  mostrare di nuovo le voci come nuove). Il collegamento «Novità» della testata tiene `data-ultima` (attributo
  nascosto, serve al pallino di `aspetto.js`).

**Aggiunte dell'08/11/2026, seconda parte (stessa versione `b`, decisioni di Paolo: «tutto in un'unica pubblicazione»):**

- **Tetti a falda, tre fonti.** Per la forma del tetto di ogni corpo: 1. **falde misurate dal LiDAR** (pipeline notturna,
  `lidar/indice.json`); 2. **tetto stimato dal colmo DBTR** (già nella sezione 6 qui sopra); 3. **ipotesi automatica**: tetto
  a falde a **22° in pianura, 32° in montagna**, a capanna sul lato lungo o a padiglione se il corpo è quasi quadrato (stessa
  regola del colmo), colmo = gronda + semiluce × tan(inclinazione). **Criterio pianura/montagna (scelta)**: la zona
  altimetrica ISTAT dei comuni non è nei dati del sito e ISTAT oggi pubblica in formato aperto solo l'altimetria e le
  fasce altimetriche dei comuni (al 31/12/2021), non la classificazione per zona; quindi vale la **quota del terreno sotto
  l'edificio** (DTM, già nei corpi) con le soglie ISTAT della montagna: **≥ 600 m nei comuni del Nord, ≥ 700 m al Centro, al
  Sud e nelle isole**; collina = pianura (22°). Senza la quota del corpo (edifici OSM) l'altitudine del comune del DPR
  412/93; senza nessuna, pianura. Effetto: il paese di fondovalle di un comune montano (Bagno di Romagna, ~490 m) resta a
  22°, le frazioni sopra i 600 m vanno a 32°. **Restano piani** (soglie): uso capannone, commerciale, palestra, industriale
  (DBTR o OSM) e tipi DBTR industriali, tettoie, hangar, serre, cabine, tribune, palazzi dello sport; corpi **oltre 1.500
  m²** o con il **lato corto oltre 25 m**; **gronda sotto 3 m** (accessori); corpi con cortile; forma poco rettangolare
  (**meno del 70 %** del rettangolo minimo: più robusto del numero di lati, perché il DBTR ha molti vertici allineati) o
  più stretta di 2 m. Regola uguale in `edifici_calcoli.js` e `fase10-edifici3d/edifici3d/tetti.py` (test di parità).
  - **Modelli 3D**: le tre fonti in cascata per ogni corpo; **nota sotto la mappa** («Tetti: 0 misurati dal LiDAR, 1
    stimato dal colmo DBTR, 1 ipotizzato (22° pianura / 32° montagna: 1 a 22°), 1 piano»), conteggi in legenda, riga
    nell'immagine, sezione «Forma dei tetti» nel report; il motivo del tetto piano nella tabella dei corpi.
  - **Edificio e Fotovoltaico**: selettore **«Forma dei tetti»** nel passo «Corpi › Falde dei tetti»: «Misurata (LiDAR) dove
    c'è», «Stimata dal colmo DBTR dove c'è», «Ipotesi automatica (22°/32°)», «Tutti piani»; quelle non disponibili spente
    con il motivo; predefinita la più affidabile; ombre, aree FV, producibilità e sole sulle facciate ricalcolati al
    cambio; inclinazione e orientamento corretti a mano restano; scelta scritta nei risultati e nel report.
  - Numeri (tutti i corpi degli archivi, nessuna falda LiDAR ancora): **Rimini** 40.518 corpi = 0 LiDAR, **4.103** dal
    colmo DBTR, **28.107 ipotizzati** (tutti a 22°), **8.308 piani** (2.432 bassi, 1.744 poco rettangolari, 1.677
    commerciali – gli alberghi –, 1.494 capannoni, 302 tipi industriali/tettoie, 202 stretti, 162 con cortile, 129
    palestre, 85 con il lato corto oltre 25 m, 81 oltre 1.500 m²); **Bagno di Romagna** 5.019 corpi = 0 LiDAR, 0 colmo,
    **4.211 ipotizzati (2.843 a 22°, 1.368 a 32°)**, **808 piani** (346 capannoni).
- **Sagome regionali con le altezze OSM** (nuovo livello della cascata delle fonti delle pagine 3D, tra il DBTR e OSM). Dove
  non c'è un archivio DBTR e la Regione ha in `regioni.toml` uno strato edifici **attivo**, aperto, **senza altezze** e con
  un WFS che risponde, il server chiede le sagome intorno al punto (stessa rotta `/api/edifici/osm`, celle di 0,002°, copia
  su disco, limiti, Turnstile; `EDIFICI_REGIONALI=false` le spegne) e dà a ognuna l'altezza dell'edificio OSM che le si
  sovrappone di più (height, poi piani × 3 m), altrimenti la mediana dei vicini (DBTR o OSM con l'altezza) o 9 m, sempre
  dichiarata per corpo; tetto con la cascata (ipotesi 22°/32°); quote dal DTM del server. Accesa solo il **Veneto**
  («Edifici del Veneto (feb. 2022)», IODL 2.0, WFS `idt2-geoserver.regione.veneto.it/geoserver/wfs`, `rv:edifici_veneto_feb2022`,
  bbox nel sistema nativo **EPSG:6876**). Valutate e non accese: Valle d'Aosta, Umbria, Sicilia (in attesa, nessun WFS aperto
  provato), Piemonte e Toscana (servizi non raggiungibili dal container), aggregati strutturali della Protezione Civile
  (CC BY 4.0, solo file per regione: nessun servizio interrogabile per riquadro). In pagina: «Sagome dalla Regione del
  Veneto (IODL 2.0), altezze da OpenStreetMap dove ci sono, altrimenti stimate», stesso marrone degli edifici OSM (legenda
  «edifici OpenStreetMap o sagome regionali»), attribuzioni IODL 2.0 + ODbL in pagina, immagine e report; privacy: il
  riquadro di ~800 m attorno al centro della cella va anche al WFS della Regione. **Prova dal vivo dal container
  (08/11)**, rotta del server con il WFS vero, Overpass vero (riserva europea: la principale chiudeva la connessione) e il
  DTM veneto vero: castello di San Salvatore **52 sagome** (+7 OSM, nessuna con l'altezza OSM, quote 85–162 m); Susegana via
  San Salvatore **396 sagome** (+53 OSM; **4 con l'altezza OSM**, 60 dalla mediana dei vicini OSM, il resto 9 m; quote 73–110
  m) in 6,7 s; Conegliano centro **1.153 sagome** (+98 OSM; 1 con l'altezza OSM). OSM in zona ha pochissime altezze: quasi
  tutte le sagome restano a 9 m stimati (dichiarato). Pagina provata in Chromium con la risposta vera di Susegana: edificio
  `veneto_1458202`, gronda 6 m dall'OSM sovrapposto, quota 77 m, tetto ipotizzato a 22°, terreno acceso, nessun errore.
- **Terreno da più file.** `dtm-server` accetta più file (zip, TIFF o **ESRI ASCII Grid**, anche una cartella), li mosaica in
  un COG unico per zona e scrive la scheda (`--regione veneto`: «Regione del Veneto – DTM 5 m da voli LiDAR, IODL 2.0»,
  nome per la legenda, data dei file); `--crs` per i file senza sistema. Le **40 tavole** di Susegana e Conegliano (ASCII
  Grid 400×400 da 5 m, senza `.prj`, 2024-06-03) sono in **EPSG:6876** (verificato: castello di San Salvatore 157 m, via San
  Salvatore 78 m, Conegliano 73 m; il Copernicus sulle stesse tessere dà 72–127 m): COG di 12,5 MB in 2,5 s. La rotta
  `/api/terreno` usa **più DTM insieme**, il più dettagliato prima, poi Copernicus, poi piatto; intestazione nuova
  `X-Terreno-Nome` (legenda «Terreno: DTM 5 m da voli LiDAR Regione del Veneto (IODL 2.0)»). Prova della rotta con ER e
  Veneto insieme: Susegana e Conegliano `dtm` dal Veneto, Brisighella `dtm` dall'ER, Treviso `copernicus`. Altre tavole:
  pagina IDT del Veneto (https://idt2.regione.veneto.it/idt/downloader/download → «Modelli digitali» → «DTM 5 m da voli
  LiDAR» → provincia e comune → ZIP); nessun download automatico pubblico trovato.

**Aggiunte dell'08/11/2026, terza parte (stessa versione `b`, decisioni di Paolo delle 12:19: il sito va online per la
newsletter del 12/11):**

- **Menu.** Sei gruppi; «Edificio» diventa **«Edifici»** (`data-gruppo` resta `edificio`, gli indirizzi delle pagine non
  cambiano). **Clima e meteo**: Dati climatici, Legge 10, Previsioni, **Cambiamento climatico** (ultima voce, S, accessibile:
  è l'analisi 13 «Clima che cambia», `edificio-clima.html`, rinominata in titolo, menu, «Nello stesso gruppo», Novità e file
  per agenti). **Patrimonio** invariato (LiDAR e Visure col triangolo come prima). **Edifici**: Obblighi di legge (prima
  voce), Geometria, Consumi, Fabbisogno UNI, Facciate e tetti, Pompe di calore, **Ecobonus**, **Conto Termico** (due
  segnaposto nuovi, `edificio-ecobonus.html` e `edificio-conto-termico.html`), tutte **in lavorazione**. **Cogenerazione**:
  Emissioni in lavorazione, le 5 GME come prima. **Fotovoltaico**: le 6 pagine e **Comunità energetiche** (`edificio-cer.html`,
  spostata qui) in lavorazione, Prezzo catturato GME. **Statistiche** invariato.
- **Pagine in lavorazione** (16): voce `span.voce-gme.voce-corso` col triangolo giallo, non cliccabile, attenuata, tooltip
  «In lavorazione: disponibile prossimamente» (menu del computer, del telefono e riga fissata); nessun collegamento nel sito
  (tolti in Sitografia, Cambiamento climatico, LEED, CER, Facciate e tetti, Novità; Patrimonio e Modelli 3D non ne avevano);
  restano raggiungibili con l'indirizzo diretto, con in cima «Pagina in lavorazione, non ancora verificata».
  `costruisci_pagine.py` genera dal menu l'avviso, gli elenchi «Nello stesso gruppo» e l'etichetta del gruppo; scelta mia,
  da confermare: sono «in lavorazione» anche le tre pagine Edifici che erano già «in sviluppo» (Fabbisogno, Facciate e tetti,
  Pompe di calore), perché il gruppo Edifici è tutto non accessibile.
- **Tendine** larghe quanto la voce più lunga (prima 17rem fissi, 11 voci andavano a capo); **barra di scorrimento a sinistra**
  nella colonna della mappa di tutte le pagine a due colonne (anche Previsioni, Legge 10, Dati climatici, Patrimonio, Importa,
  Aggiungi edifici, Costi Sanità e le pagine 3D); telefono invariato.
- **Ricerca**: esempio **«viale Ghirotti 286», «Cesena»** (e foglio 149, particella 387) al posto di «via Gambalunga 27»,
  «Rimini»; il solo comune porta al centro del comune in tutte e 10 le pagine con «Cerca l'indirizzo» e «Cerca la
  particella» (Modelli 3D, Ortofoto, 8 pagine 3D), provato in Chromium pagina per pagina; **Previsioni**: il solo nome del
  comune propone «Comune di Cesena (FC)» e lo sceglie senza server, le risposte 0,0 non compaiono (anche `/api/geocodifica`
  le scarta: **serve il rebuild dell'api**, già in J5). Legge 10 e Dati climatici cercano solo comuni.
- **Apertura su Cesena**: Ortofoto, Modelli 3D e pagine 3D si aprono sull'**ospedale Bufalini** e la collina (44,1326 N
  12,2597 E, zoom 15,6) se l'indirizzo non porta un punto, una sede, un edificio, un modello o un file e la regione scelta è
  l'Emilia-Romagna. Centro verificato sul DBTR di Cesena: l'ospedale è la particella **foglio 149 n. 387** (59 corpi, quote
  38–59 m, baricentro 44,1338 N 12,2597 E); il punto della richiesta (44,1405 N 12,2405 E) cade ~2 km più a nord-ovest, in
  una zona residenziale, quindi non l'ho usato. Patrimonio parte sempre dalla mappa della regione.
- **Novità** (voce `20261107b`): un paragrafo sulle pagine in lavorazione, «Clima e meteo › Cambiamento climatico» tra i
  miglioramenti, l'apertura su Cesena; tolte le righe delle voci precedenti che presentavano come disponibili pagine ora in
  lavorazione (Emissioni, pagine Edificio e Fotovoltaico) e il collegamento a Emissioni. F.A.Q. nuova `#in-lavorazione`
  («Perché alcune voci del menu non si aprono?»); `EUGENIO_PER_AGENTI.md` e `llms.txt` con lo stato «in lavorazione, non
  accessibile».

Test (container, 08/11 sera, dopo il menu, in sequenza): fase 4 **232 passed**, fase 5 **80 passed, 1 saltato** (Chromium: menu a sei gruppi, voci in lavorazione non cliccabili con il tooltip, tendine su una riga a 900, 1000 e 1366 px, tastiera; ricerca col solo comune e apertura su Cesena nelle 10 pagine con la ricerca; Previsioni col solo comune; barra a sinistra in 10 pagine a due colonne con le barre vere; 375 px senza scorrimento di lato), fase 10 **133 passed** (`test_blocco2_browser.py` può andare in timeout se gira insieme a un’altra suite in Chromium: da solo passa).

Test (container, 08/11, dopo tetti, sagome venete e terreno da più file): fase 4 **231 passed**, fase 5 **62 passed, 1 saltato** (Chromium: tetti in cascata, «Forma dei tetti» in Fotovoltaico con il ricalcolo e 375 px, sagome venete), fase 10 **133 passed**.

Test (container, 08/11 mattina): fase 4 **224 passed** (con `PYTHONPATH` delle fasi 3, 6–10); fase 5 **58 passed, 1 saltato**
(Chromium: frecce in Ortofoto, Modelli 3D e Ombre FV, 375 px); fase 10 **128 passed**.

Test (container, 07/11 sera): fase 4 **218 passed**; fase 5 **55 passed, 1 saltato** (Chromium: 19 comuni coperti, prove di
Paolo nel 3D, ricerca per comune e 0,0, telefono a 375 px senza scorrimento di lato, «Novità»); fase 10 **128 passed**
(trascina, «Apri» e «Togli» con l'esito accanto, coda vuota); fase 7 **14 passed**.

File toccati: `fase5-sito/sito/` (`edificio3d.js`, `edifici_calcoli.js` con `faldeStimate`, `cerca_luogo.js`,
`ortofoto.js`, `esporta_mappa.js`, `aggiungi_dbtr.js`, `interno/edifici.js`, `stile.css`, le 9 pagine 3D, `ortofoto.html`,
`aggiungi-dbtr.html`, `dati.html`, `legge10.html`, `faq.html`, tutte le pagine per la versione), `fase5-sito/novita.toml`,
`fase4-server/Caddyfile`, `servizio/ortofoto.py`, `servizio/app.py`, `fase7-territorio/territorio/{zornade,patrimonio}.py`,
`fase10-edifici3d/edifici3d/{archivi,pipeline}.py`, `fase10-edifici3d/ortofoto/emilia_romagna.toml` e `strati/catasto.toml`,
test. Dall'08/11 anche: `sposta_ortofoto.js` (nuovo), `ortofoto.js`, `strati_gl.js`, `stile.css`, le 9 pagine 3D e
`ortofoto.html` (contenitore e script delle frecce), `faq.html`, `novita.html`, `novita.xml`, `EUGENIO_PER_AGENTI.md`,
`llms.txt`, `fase5-sito/costruisci_pagine.py` (voce senza versione), `fase4-server/servizio/{ortofoto,report_servizi,notiziario}.py`.
Dall'08/11, seconda parte: `edificio3d.js`, `edifici_calcoli.js`, `stile.css`, le 9 pagine 3D (nota dei tetti, legenda,
selettore nelle 8 pagine Edificio e Fotovoltaico), `privacy.html`, `novita.*`, `EUGENIO_PER_AGENTI.md`, `llms.txt`;
`fase4-server/servizio/{edifici_osm,terreno,report_servizi,config}.py`, `.env.example`, `api/Dockerfile`;
`fase10-edifici3d/edifici3d/{tetti,sagome_regionali}.py` (nuovi), `dtm_locale.py`, `osm_campione.py`, `__main__.py`,
`fonti/sagome_regionali.toml` (nuovo); test nuovi `fase10-edifici3d/tests/test_tetti.py`, `fase4-server/tests/test_edifici_regionali.py`.

## K – Lettori regionali e 15 città di riferimento (08/11/2026 sera tardi, stessa versione `?v=20261107b`)

Decisione di Paolo: **tutti i lettori regionali** e gli archivi delle città entrano nella stessa pubblicazione J. Tre
lavori in parallelo (gruppi A, B, C: `lettori/{a,b,c}/MODIFICHE_CONDIVISE.md`) integrati in un solo albero:

- **Adattatori nuovi** in `fase10-edifici3d/edifici3d/adattatori/` (17 adattatori registrati in tutto): Lazio, Basilicata,
  Piemonte (A); Toscana, Puglia, Marche, Palermo e CTR Sicilia, FVG edizione 2 (B); Trento, Bolzano, Sardegna, Campania
  (C); **Venezia** (`venezia_dbgt`, DBGT del Comune, IODL 2.0, scaricato da Paolo l'08/11). Fonti in `fonti/<zona>.toml`.
- **15 archivi delle città** (tabella nel README della fase 10, «Lettori regionali e città di riferimento»): Milano,
  Torino, Genova (parte), Venezia, Trieste, Trento, Bolzano, Firenze, Ancona, Roma (foglio 374), Bari (5 elementi),
  Potenza, Napoli, Palermo, Cagliari (parte). **Torino** rifatto con il file di Paolo con la fascia nord (68.768 corpi).
  **Napoli** (decisione di Paolo delle 15:22: si pubblica) con le altezze del **Copernicus Urban Atlas Building Height
  2012** (il servizio dà classi di altezza, non metri: altezza centrale della classe, dichiarata per corpo), poi la
  mediana dei vicini, poi la stima dall'uso; altezze OSM **non** usate (ODbL in un archivio CC BY: vietato dalla regola
  delle cartelle). Attribuzione «© European Union, Copernicus Land Monitoring Service 2012, European Environment Agency
  (EEA)» nell'archivio.
- **Cartelle per licenza** (regola unica): `cc-by/` per CC BY 4.0, CC BY 2.5, CC0 1.0 (e i dati Copernicus), `iodl/` per
  IODL 2.0 (Potenza, Bari, Venezia), `odbl/` per OSM. Caddy serve già tutto `/edifici3d/*` e la pagina legge le `base` di
  `archivi.json`: **nessuna modifica alle pagine pubbliche né al Caddyfile**.
- **Codice condiviso**: `archivi.py` (IODL e CC0 con i DB topografici, prima di ODbL), `__main__.py` (`LICENZE.txt`
  secondo la licenza con il DTM delle quote, `controlla-archivio` con CC BY 2.5, IODL 2.0, CC0 1.0 e soglia 25 m per i
  parziali, comando `confronta-dsm`, `--attribuzione-dtm`), `regionali.py` (`coerenza()` degli adattatori esterni,
  `scegli_adattatore` con `alternativi`: FVG ED2 predefinita, ED1 per i file della coda), `uvl.py` (proprietà a lista dei
  GeoJSON di GeoServer), `altezze_dsm.py` (fonte Copernicus UA), `altezze_ua.py` (nuovo), `fonti/regioni.toml` (stati,
  licenze e prove dell'08/11: 90 fonti), `fonti/{friuli_venezia_giulia,liguria,lombardia}.toml`;
  `fase4-server/servizio/edifici_osm.py` (campo dell'uso della fonte per Sardegna e Campania; testo della fonte ArcGIS);
  commenti di `fase4-server/api/Dockerfile` e `fase10-edifici3d/Dockerfile` (i file nuovi c'erano già: l'api copia
  `sagome_regionali.py` e `fonti/sagome_regionali.d/`, `energia-edifici` tutta la fase 10).
- **Documenti**: `documenti/LETTERE_DA_INVIARE_2026-11-08.md` (nuovo: 14 lettere brevi pronte da copiare, con tabella
  di destinatari, richieste e priorità e indirizzi verificati l'08/11 su pagine o schede ufficiali; Emilia-Romagna con
  UVL/EDI per provincia o regione, DSM/LAS RER 2023-24 e deroga per le altezze in OpenStreetMap; Calabria al Settore 8 via
  PEC del Dipartimento; FVG a irdat@regione.fvg.it), `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md` (Basilicata tolta; Lazio solo licenza 2020; Toscana solo
  versione 2023; Piemonte CC BY 2.5 e WCS del DTM; FVG scarico in blocco del LiDAR; Sicilia licenza del DTM 2013; Campania
  quote e DSM; Sardegna, Puglia, Marche ridotte; Umbria e Abruzzo precisate; Bolzano riscritta; Calabria con la licenza
  del DTM 5 m; nessuna lettera ai Comuni di Venezia e Genova), `novita.toml` (voce utente nella `20261107b`),
  `EUGENIO_PER_AGENTI.md` e `llms.txt` (città coperte).

Test (container, 08/11 sera tardi, alle 16:10, dopo gli archivi finali): fase 10 **171 passed** (senza
`test_blocco2_browser.py`); fase 4 **232 passed** (con `PYTHONPATH` delle fasi 3, 6–8 e 10); fase 5 senza Chromium **41
passed, 1 saltato** (`test_mappe_browser.py` e `test_menu_browser.py` non lanciati).

Archivi finali (08/11, 16:10): **Venezia** preparato (175.501 corpi di 74.542 edifici, gronda fino a 77,95 m, quota da
`UN_VOL_QB`); **Napoli** rifatto con le classi Copernicus (29.698 corpi: circa 25.600 con la classe UA, 3.540 dalla
mediana dei vicini, 560 stimati dall'uso; 20 corpi oltre 60 m, torri del Centro Direzionale nella classe 100–368 m);
**Torino** già rifatto alle 15:05 dal file con la fascia nord (143.566 volumi nel file, 70.873 nel confine, 68.768 corpi).
`controlla-archivio` su tutti e 15: `"problemi": []` (avvisi solo a Milano e Genova: corpi oltre 60 m veri).
`archivi-json` su una cartella di prova con i 28 indici ER (07/11 e 08/11) e i 15 delle città: **43 voci**, ordine e
licenze come in J6. Trieste: confronto LiDAR 2017-2020 chiuso su 7.327 edifici (elemento 110103 intero e tavole 05, 08,
09, 11, 12 del 110141): scarto mediano +0,05 m, MAE 1,33 m, 82 % entro 2 m, 3,6 % oltre 5 m; torri di Cattinara DSM − DTM
58,7–60,6 m contro gronda 54,8 m nell'archivio (coerente). Lettere: `documenti/LETTERE_DA_INVIARE_2026-11-08.md` (14,
con indirizzi verificati l'08/11).

Archivi sul PC: `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_citta\` (15 tar e
`SHA256SUMS_citta_2026-11-08.txt`), **mai** nel clone né nel repository. Sul server con **J4 quater e J5 quater**.

## Procedura J1–J12 (da `?v=20261107a` pubblicato a `?v=20261107b`)

Punto di partenza: sito `?v=20261107a` online e procedura F fatta fino a F22–F23 (commit e release `v2026.11.07`). Se F22
non è stato fatto, fallo prima (il commit del 07a), poi questa. **Archivi degli edifici: nessuna copia** (non sono stati
rigenerati) **tranne i 9 archivi nuovi e Ravenna dell'08/11** (J4 ter, J5 ter) **e i 15 archivi delle città** (J4 quater, J5 quater). Serve: pacchetto del sito, rebuild di **api** (ortofoto, `/api/comuni`, ricerca) ed **energia-edifici**
(`archivi-json`, pipeline), **Caddy** ricreato (Caddyfile), `archivi.json` rigenerato, vecchia copia nera della RER tolta,
**Purge Everything** su Cloudflare. Release: **nuova**, `v2026.11.07b` (è una seconda pubblicazione dello stesso giorno,
con la sua voce in `novita.toml`; la release `v2026.11.07` resta com'è, così ogni release corrisponde a una versione del sito).
Tempo: circa 1 ora (prove comprese), più 5 minuti per il DTM del Veneto (J4 bis e J5 bis, facoltativi), più circa 30
minuti per gli archivi dell'08/11 e il quadrante NE del DTM (J4 ter e J5 ter: quasi tutto attesa del server), più circa 20
minuti per i 15 archivi delle città (J4 quater e J5 quater, 0,4 GB).

### J1. [PC] Zip sopra il clone
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Measure-Object
```
```powershell
Expand-Archive -Path ..\eugenio_2026-11-07.zip -DestinationPath . -Force
```
```powershell
Select-String -Path fase5-sito\sito\index.html -Pattern "20261107b" -List | Measure-Object
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
```powershell
git status --short -uall | Select-String -Pattern "^\?\?" | Measure-Object
```
Cosa aspettarsi: `Count : 0` prima (clone pulito dopo F22); poi `Count : 1`; nove righe nuove:
`?? fase10-edifici3d/edifici3d/sagome_regionali.py`, `?? fase10-edifici3d/edifici3d/tetti.py`,
`?? fase10-edifici3d/fonti/sagome_regionali.toml`, `?? fase10-edifici3d/tests/test_tetti.py`,
`?? fase4-server/tests/test_edifici_regionali.py`, `?? fase5-sito/tests/punti_19_comuni.json`; dall'08/11 sera anche
`?? fase5-sito/sito/edificio-conto-termico.html` e `?? fase5-sito/sito/edificio-ecobonus.html` (otto righe in tutto), più
`?? documenti/CITTA_RIFERIMENTO_MILANO_FIRENZE_ROMA.md` (documento dell'08/11 sulle città di riferimento: nove righe);
dall'08/11 sera anche `?? documenti/CITTA_RIFERIMENTO_NORD.md`, `?? documenti/CITTA_RIFERIMENTO_CENTRO.md` e
`?? documenti/CITTA_RIFERIMENTO_SUD_ISOLE.md` (i 15 capoluoghi): **dodici righe**; dall'08/11 sera tardi (sezione K) in più
**67 file nuovi** dei lettori regionali, che il quarto comando mostra in **51 righe** (le cartelle nuove `adattatori/` e
`sagome_regionali.d/` contano una riga ciascuna):
- `documenti/`: `CITTA_RIFERIMENTO_DOWNLOAD.md`, `LETTERE_DA_INVIARE_2026-11-08.md` (2 righe);
- `fase10-edifici3d/edifici3d/`: `a_comuni.py`, `altezze_dsm.py`, `altezze_ua.py`, `b_regioni.py` e la cartella `adattatori/`
  (15 file: `__init__.py`, `a_dbgt.py`, `basilicata.py`, `bolzano.py`, `campania.py`, `friuli_venezia_giulia.py`, `lazio.py`,
  `marche.py`, `piemonte.py`, `puglia.py`, `sardegna.py`, `sicilia.py`, `toscana.py`, `trento.py`, `venezia.py`) (5 righe);
- `fase10-edifici3d/fonti/`: 15 TOML (`basilicata`, `bolzano`, `campania`, `campania_napoli`, `lazio`, `lombardia_milano`,
  `marche`, `piemonte`, `puglia`, `sardegna`, `sicilia`, `sicilia_ctr`, `toscana`, `trento`, `venezia`) e la cartella
  `sagome_regionali.d/` (3 file: `LEGGIMI.md`, `campania.toml`, `sardegna.toml`) (16 righe);
- `fase10-edifici3d/tests/`: `test_adattatori_a.py`, `_b.py`, `_c.py`, `_integra.py` (4 righe) e 24 campioni in `tests/dati/`
  (`basilicata_dbgt_campione.geojson`, `bolzano_inspire_edifici_campione.geojson`, `bolzano_inspire_parti_campione.geojson`,
  `campania_ctr2020_campione.geojson`, `fvg_ctrn_ed2_campione.geojson`, `lazio_dbgt_campione.geojson`, i 6 file
  `lombardia_milano_un_vol.{cpg,dbf,prj,shp,shx}` e `lombardia_milano_un_vol_LEGGIMI.txt`, `marche_edificio_campione.geojson`,
  `marche_punto_quotato_campione.geojson`, `palermo_uv_campione.geojson`, `piemonte_bdtre_campione.geojson`,
  `puglia_ctr_438074_campione.zip`, `sardegna_dbgt_campione.geojson`, `sardegna_lidar2008_dsm_campione.tif`,
  `sardegna_lidar2008_dtm_campione.tif`, `sardegna_wfs_campione.geojson`, `sicilia_ctr_campione.geojson`,
  `toscana_uv_campione.geojson`, `trento_pat3d_campione.geojson`) (24 righe).

In tutto il quarto comando mostra **63 righe** (12 + 51); il quinto, che conta un file per riga, `Count : 79` (12 + 67).

Cosa fare se va male: il primo `Count` non è 0 → F22 non è stato fatto: mandami `git status --short` (niente zip finché
non è chiaro); `Count : 0` dopo l'estrazione → zip vecchio, riscaricalo; l'ultimo `Count` diverso da 79 → mandami
l'elenco del quarto comando (nessun commit finché non torna).

### J2. [PC] Pagine e test della fase 5, segreti
```powershell
cd fase5-sito
```
```powershell
python costruisci_pagine.py --controlla
```
```powershell
python -m pytest -q tests
```
```powershell
cd ..
```
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x
```
Cosa aspettarsi: `versione 20261107b: 0 file da rigenerare`; test verdi (senza Chromium sul PC molti saltano: va bene);
quattro righe `.gitignore:…`.

Cosa fare se va male: test rossi → mandami le ultime 30 righe; meno di quattro righe → fermati e mandamele.

### J3. [PC] Pacchetti del codice e del sito
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=.venv-build --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude=uni_privato --exclude=node_modules .dockerignore fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d fase5-sito/novita.toml
```
```powershell
tar -tzf ..\codice.tar.gz | Select-String -Pattern "uni_privato|\.env$" | Measure-Object
```
```powershell
cd fase5-sito
```
```powershell
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
```
```powershell
cd ..
```
Cosa aspettarsi: `Count : 0` (nessun modulo privato, nessun `.env`).

Cosa fare se va male: `Count` diverso da 0 → cancella `..\codice.tar.gz` e mandami le righe.

### J4. [PC] Copia sul server
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Cosa aspettarsi: due righe con `100%`.

Cosa fare se va male: `Connection timed out` → rete aziendale: passa a casa o al telefono.

### J4 bis. [PC] Facoltativo: tavole del DTM del Veneto sul server
Solo se la cartella `C:\Users\ingpa\Documents\claude\pj\statocritico\dtm_veneto\susegana_conegliano` c'è (40 zip, 7 MB):
```powershell
scp -r ..\dtm_veneto\susegana_conegliano eugenio:~/dtm_veneto_tv
```
Cosa aspettarsi: 40 righe `12_2K_….asc.zip 100%`. Se la cartella non c'è, salta J4 bis e J5 bis: in Veneto la rotta del
terreno usa il Copernicus.

### J4 ter. [PC] Archivi dei comuni dell'08/11
In `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\` ci sono 10 archivi con la data **2026-11-08**:
Bologna (281 fogli su 305), Cesenatico, Bellaria-Igea Marina, Bagnacavallo, Conselice, Modigliana, Alfonsine, Cotignola
(interi), **Misano Adriatico** (estrazione raggruppata: Misano e Morciano interi, parte di Coriano) e **Ravenna (città)**, che sostituisce quello del 07/11 (ospedale più 84 fogli intorno al centro), con
`SHA256SUMS_2026-11-08.txt`. Bologna è già ricomposto: la cartella `parti\` si può cancellare.
```powershell
ssh eugenio "mkdir -p ~/archivi_0811"
```
```powershell
scp C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\*_2026-11-08.tar.gz C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_edifici\SHA256SUMS_2026-11-08.txt eugenio:~/archivi_0811/
```
Cosa aspettarsi: undici righe con `100%` (Bologna 38 MB, Ravenna 15 MB, gli altri 2–7 MB).

Cosa fare se va male: `Connection timed out` → rete aziendale. Se nel frattempo ti ho dato altri archivi con la stessa data,
l'asterisco li prende tutti: va bene, purché ci sia anche il loro `SHA256SUMS` aggiornato.

### J4 quater. [PC] Archivi delle 15 città
In `C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_citta\` (già riempita l'08/11: archivi ricomposti e impronte verificate sul PC; la sottocartella `parti\` si può cancellare) ci
sono 15 tar `edifici_<zona>_<comune>_2026-11-08.tar.gz` (Milano, Torino, Genova, Venezia, Trieste, Trento, Bolzano,
Firenze, Ancona, Roma, Bari, Potenza, Napoli, Palermo, Cagliari) e `SHA256SUMS_citta_2026-11-08.txt`.
```powershell
(Get-ChildItem C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_citta\*_2026-11-08.tar.gz).Count
```
```powershell
ssh eugenio "mkdir -p ~/archivi_citta"
```
```powershell
scp C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_citta\*_2026-11-08.tar.gz C:\Users\ingpa\Documents\claude\pj\statocritico\archivi_citta\SHA256SUMS_citta_2026-11-08.txt eugenio:~/archivi_citta/
```
Cosa aspettarsi: `15`; poi sedici righe con `100%`: Roma 92 MB, Milano 75 MB, Venezia 47 MB, Firenze 35 MB, Torino 29 MB,
Palermo 26 MB, Potenza 17 MB, Napoli 14 MB, Trento 13 MB, Trieste e Bari 11 MB, Bolzano 8 MB, Ancona 5 MB, Cagliari 2 MB,
Genova 0,6 MB (383 MB in tutto) e lo `SHA256SUMS` di 15 righe.

Cosa fare se va male: un numero diverso da 15 → manca un file nello scaricamento: riscarica la cartella; `Connection
timed out` → rete aziendale.

### J5. [Server] Copia di sicurezza, codice, rebuild di api ed edifici, api, worker e Caddy ricreati
Entra con `ssh eugenio`, poi:
```bash
cp -a ~/energia ~/energia_prima_20261107b
tar -xzmf ~/codice.tar.gz -C ~/energia && grep -c "def senza_buchi" ~/energia/fase4-server/servizio/ortofoto.py
cd ~/energia/fase4-server && docker compose build api
docker compose up -d --force-recreate api worker caddy
docker compose --profile edifici build edifici-lidar
docker compose --profile edifici up -d --force-recreate edifici-coda
sleep 60; docker compose ps api worker caddy
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/comuni'); print(r.status, len(r.read()))"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/rer2023/13/4363/2971.jpg'); print(r.status, r.headers['Content-Type'], r.headers['X-Ortofoto-Copia'])"
docker compose exec -T api python -c "import urllib.request as u, json; print([f['tessere'] for f in json.load(u.urlopen('http://localhost:8000/api/ortofoto/fonti'))['fonti'] if f['id']=='rer2023'])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/rer2023/17/70114/47547.jpg?t=1&de=2&dn=-1'); print(r.status, r.headers['X-Ortofoto-Copia'], r.headers['X-Ortofoto-Spostamento'])"
docker compose exec -T api python -c "from edifici3d import sagome_regionali as SR; print([f['id'] for f in SR.carica()])"
docker compose --profile edifici run --rm --entrypoint python edifici-lidar -c "import edifici3d.regionali as R, edifici3d.altezze_ua, edifici3d.altezze_dsm, edifici3d.a_comuni, edifici3d.b_regioni, edifici3d.fonti as F; print(len(R.ADATTATORI), 'venezia_dbgt' in R.ADATTATORI, F.carica_zona('campania_napoli')['zona']['codice'], F.carica_zona('venezia')['zona']['codice'])"
```
Cosa aspettarsi: `1`; le build finiscono con `Built`; api `Up … (healthy)`, worker e caddy `Up`, api e worker con IMAGE
`energia-api`; `/api/comuni` → `200` e qualche centinaio di migliaia di byte; la tessera di Brisighella allo zoom 13 →
`200 image/png nuova` (PNG con la trasparenza: era nera); `['/api/ortofoto/rer2023/{z}/{x}/{y}.jpg?t=1']`;
`200 no de=2; dn=-1` (tessera spostata, senza copia); `['veneto', 'campania', 'sardegna']` (sagome al volo, i file di
`fonti/sagome_regionali.d/` sono nell'immagine dell'api); `17 True cam ven` (i 17 adattatori, con i 14 nuovi di
`edifici3d/adattatori/`, i moduli `altezze_*`, `a_comuni`, `b_regioni` e i TOML nuovi delle zone sono nell'immagine
`energia-edifici`).

Cosa fare se va male: api non `healthy` dopo 2 minuti → `docker compose logs --tail 40 api` e mandami le righe;
`['veneto']` soltanto o `ModuleNotFoundError`/un numero minore di 17 → il codice estratto non è quello dello zip nuovo
(J1 e J3 di nuovo, poi le due build); `/api/comuni` ancora `500` → `docker compose logs --tail 30 api | grep -i -A5 comuni` e mandami le righe (il resto
funziona); per tornare indietro: `rm -rf ~/energia && mv ~/energia_prima_20261107b ~/energia && cd ~/energia/fase4-server && docker compose build api && docker compose up -d --force-recreate api worker caddy`.

### J5 bis. [Server] Facoltativo: DTM del Veneto per il terreno 3D (solo se hai fatto J4 bis)
```bash
mkdir -p /srv/energia/dati/terreno/grezzi && mv ~/dtm_veneto_tv /srv/energia/dati/terreno/grezzi/veneto_tv && ls /srv/energia/dati/terreno/grezzi/veneto_tv | wc -l
cd ~/energia/fase4-server && docker compose --profile edifici run --rm edifici-lidar dtm-server --regione veneto --crs EPSG:6876 --file /dati/terreno/grezzi/veneto_tv --uscita /dati/terreno/dtm5_veneto_tv.tif | grep -E '"(crs|tavole|licenza|riquadro_wgs84)"' -A0
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/terreno/15/17497/11677.png'); print(r.status, r.headers['X-Terreno-Fonte'], r.headers['X-Terreno-Nome'])"
docker compose exec -T api python -c "import urllib.request as u, json; print([d['file'] for d in json.load(u.urlopen('http://localhost:8000/api/terreno/fonti'))['dtm']])"
```
Cosa aspettarsi: `40`; `"crs": "EPSG:6876"`, `"tavole": 40`, `"licenza": "IODL 2.0"` e il riquadro 12,15–12,34 E, 45,80–45,96 N;
`200 dtm DTM 5 m da voli LiDAR Regione del Veneto (IODL 2.0)` (castello di San Salvatore); `['dtm5_er_se.tif',
'dtm5_veneto_tv.tif']` (l'api rilegge le schede ogni 5 minuti: se manca il Veneto, aspetta e ripeti).

Cosa fare se va male: `copernicus` invece di `dtm` → la tessera era già in copia da prima: va bene così (la copia
cambia versione con il DTM nuovo dopo 5 minuti); errore di `dtm-server` → mandami le ultime 20 righe.

### J5 ter. [Server] Archivi dell'08/11 e DTM quadrante NE (Bologna e bassa Romagna)
Ancora in `~/energia/fase4-server`. Prima gli archivi (Ravenna vecchio tolto, poi i 10 nuovi), poi il quadrante NE del
DTM: serve alla rotta del terreno per Bologna e per la parte nord di Ravenna, Bagnacavallo, Conselice e Alfonsine.
```bash
cd ~/archivi_0811 && sha256sum -c SHA256SUMS_2026-11-08.txt | grep -vc ': OK$'; cd ~/energia/fase4-server
cp /srv/energia/dati/edifici/archivi.json ~/archivi_prima_20261108.json
mv /srv/energia/dati/edifici/cc-by/er/ravenna ~/ravenna_07nov
for f in ~/archivi_0811/*.tar.gz; do tar -xzf "$f" -C /srv/energia/dati/edifici || echo "ERRORE $f"; done
ls /srv/energia/dati/edifici/cc-by/er/ | wc -l; ls /srv/energia/dati/edifici/cc-by/er/bologna/prodotti
cd /srv/energia/dati/edifici/cc-by/er/grezzi/dtm5 && wget -c https://mappegis.regione.emilia-romagna.it/archiviogis/DTM/DTM5x5_ed2025_NE_7791.zip && stat -c %s DTM5x5_ed2025_NE_7791.zip; cd ~/energia/fase4-server
docker compose --profile edifici run --rm edifici-lidar dtm-server --file /dati/edifici/cc-by/er/grezzi/dtm5/DTM5x5_ed2025_NE_7791.zip --uscita /dati/terreno/dtm5_er_ne.tif | grep -E '"(crs|byte)"'
docker compose exec -T api python -c "import urllib.request as u, json; print([d['file'] for d in json.load(u.urlopen('http://localhost:8000/api/terreno/fonti'))['dtm']])"
```
Cosa aspettarsi: `0` (impronte tutte `OK`); nessuna riga «ERRORE»; **29** o **30** cartelle in `cc-by/er/` (28 archivi più
`grezzi`, più `prodotti` se la pipeline delle falde l'ha già scritta); `contesto  corpi.pmtiles  indice.json`; lo
scaricamento del DTM (1,1 GB) e `1153456683` esatti; `dtm-server` lavora 10–20 minuti e stampa `"crs": "EPSG:7791"` e
`"byte"` intorno a 1,3 miliardi; l'elenco dei DTM con `dtm5_er_ne.tif` accanto a `dtm5_er_se.tif` (e al Veneto se hai
fatto J5 bis). L'api rilegge le schede ogni 5 minuti: se `dtm5_er_ne.tif` manca, aspetta e ripeti l'ultima riga. Alla fine
`rm -r ~/archivi_0811` e, dopo le prove di J10, `rm -r ~/ravenna_07nov`.

Cosa fare se va male: il primo numero non è `0` → `cd ~/archivi_0811 && sha256sum -c SHA256SUMS_2026-11-08.txt | grep -v ': OK$'`
e mandami le righe (ricopia quei file con J4 ter); dimensione del DTM diversa → rilancia la stessa riga `wget -c`; per
tornare a Ravenna di prima: `rm -rf /srv/energia/dati/edifici/cc-by/er/ravenna && mv ~/ravenna_07nov /srv/energia/dati/edifici/cc-by/er/ravenna`
e `cp ~/archivi_prima_20261108.json /srv/energia/dati/edifici/archivi.json`.

### J5 quater. [Server] Archivi delle 15 città
Ancora in `~/energia/fase4-server`, dopo J5 ter. Le cartelle nuove sono `cc-by/<zona>/<comune>` e, per la IODL 2.0,
`iodl/<zona>/<comune>` (Potenza, Bari, Venezia): Caddy le serve già (tutto `/edifici3d/*`), nessuna modifica.
```bash
cd ~/archivi_citta && sha256sum -c SHA256SUMS_citta_2026-11-08.txt | grep -vc ': OK$'; cd ~/energia/fase4-server
cp /srv/energia/dati/edifici/archivi.json ~/archivi_prima_citta_20261108.json
for f in ~/archivi_citta/*.tar.gz; do tar -xzf "$f" -C /srv/energia/dati/edifici || echo "ERRORE $f"; done
ls -d /srv/energia/dati/edifici/cc-by/*/* /srv/energia/dati/edifici/iodl/*/* | grep -v "/cc-by/er/" | wc -l
for d in $(ls -d /srv/energia/dati/edifici/cc-by/*/*/prodotti /srv/energia/dati/edifici/iodl/*/*/prodotti | grep -v "/cc-by/er/"); do echo "$d $(docker compose --profile edifici run --rm edifici-lidar controlla-archivio ${d#/srv/energia} | grep -c '"problemi": \[\]')"; done
```
Cosa aspettarsi: `0` (impronte tutte `OK`); nessuna riga «ERRORE»; `15`; quindici righe che finiscono con ` 1` (archivio
senza problemi; Milano e Genova hanno solo avvisi sui corpi oltre 60 m, veri: grattacieli e Matitone). Alla fine
`rm -r ~/archivi_citta`.

Cosa fare se va male: il primo numero non è `0` → `cd ~/archivi_citta && sha256sum -c SHA256SUMS_citta_2026-11-08.txt | grep -v ': OK$'`
e ricopia quei file con J4 quater; una riga con ` 0` → mandami l'uscita di `controlla-archivio` di quella cartella (gli
altri archivi restano validi); per togliere tutti gli archivi delle città: `cd /srv/energia/dati/edifici && rm -rf
cc-by/lom cc-by/pie cc-by/lig cc-by/fvg cc-by/tn cc-by/bz cc-by/tos cc-by/mar cc-by/laz cc-by/cam cc-by/sic cc-by/sar iodl`
e `cp ~/archivi_prima_citta_20261108.json /srv/energia/dati/edifici/archivi.json`.

### J6. [Server] `archivi.json` rigenerato e intestazioni di copia
```bash
docker compose --profile edifici run --rm edifici-lidar archivi-json --archivio /dati/edifici
docker compose exec -T api python -c "import urllib.request as u, json; d=json.load(u.urlopen('http://caddy/edifici3d/archivi.json')); print(len(d['archivi']), d.get('lidar'))"
docker compose exec -T caddy wget -qS -O /dev/null http://localhost/edifici3d/archivi.json 2>&1 | grep -i cache-control
docker compose exec -T caddy wget -qS -O /dev/null http://localhost/edifici3d/cc-by/er/rimini/prodotti/indice.json 2>&1 | grep -i cache-control
```
Cosa aspettarsi: il JSON dei **43 archivi**: i 28 dell'ER (i 19 di prima più i 9 dell'08/11; Ravenna ora si chiama
«DBTR Emilia-Romagna – Ravenna (città)» e, con «Misano Adriatico, Morciano e parte di Coriano», è senza `"istat"`: zona
coperta = riquadro dei corpi) e le **15 città** (J5 quater), in ordine di percorso: prima tutti i `cc-by/` (Bolzano CC0 1.0,
Napoli, i 28 dell'ER, Trieste, Roma, Genova, Milano, Ancona, Torino CC BY 2.5, Cagliari, Palermo, Trento, Firenze), poi
gli `iodl/` (Potenza, Bari, Venezia), ognuno con la sua `licenza` e `attribuzione`; Roma, Genova, Bari e Cagliari senza
`"istat"` (parziali); `43 None` (niente `lidar` finché la pipeline notturna non ha scritto il primo indice delle falde; poi
lo aggiunge da sola); due volte `Cache-Control: no-cache`.

Cosa fare se va male: `43 /edifici3d/cc-by/er/prodotti/` → la pipeline ha già scritto le falde: va bene; `28` → J5 quater
non fatto o tar estratti altrove: rifallo; `max-age=86400` →
Caddy non è stato ricreato: `docker compose up -d --force-recreate caddy` e ripeti le ultime due righe.

### J7. [Server] Via la copia vecchia (nera) della RER
Solo la cartella della fonte `rer2023` (la nuova è `rer2023_t`); prima guarda quanto pesa:
```bash
du -sh /srv/energia/dati/ortofoto/rer2023 /srv/energia/dati/ortofoto/rer2023_t 2>/dev/null
rm -rf /srv/energia/dati/ortofoto/rer2023
ls /srv/energia/dati/ortofoto
```
Cosa aspettarsi: le dimensioni (la vecchia anche qualche centinaio di MB, la nuova piccola); dopo il `rm`, nell'elenco
`rer2023_t`, `s2cloudless2016` e le altre fonti, **non** `rer2023`.

Cosa fare se va male: `No such file or directory` per `rer2023` → nessuna copia vecchia: va bene. Non cancellare altre
cartelle.

### J8. [Server] Sito e pulizia
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261107b /srv/energia/sito/index.html /srv/energia/sito/modelli3d.html /srv/energia/sito/interno/edifici.html
grep -c 'id="passo-cerca"' /srv/energia/sito/modelli3d.html /srv/energia/sito/ortofoto.html
grep -c "Servizio sperimentale non ancora verificato" /srv/energia/sito/dati.html /srv/energia/sito/legge10.html
rm ~/codice.tar.gz ~/sito.tar.gz
exit
```
Cosa aspettarsi: tre righe con N > 0; `1` e `1`; `0` e `0`.

### J9. [Cloudflare] Purge Everything
Cloudflare → `statocritico.it` → **Caching** → **Configuration** → **Purge Everything** → conferma. Serve per le pagine,
`stile.css` e le tessere vecchie che Cloudflare tiene in copia.

Cosa aspettarsi: «Purge request successful» (o simile). Cosa fare se va male: il pannello non si apre → rete aziendale.

### J10. [Browser] Prove (Ctrl+F5; F12 → Console)
1. **Dati climatici** e **Legge 10**: niente avviso giallo «Servizio sperimentale».
2. **Modelli 3D**: a destra il passo **1 «Cerca l'edificio»**, poi «2 Livelli della mappa»; la barra per scorrere la colonna
   della mappa è sul **bordo sinistro** della colonna. Scrivi solo «Bagno di Romagna» nel campo Comune e premi «Cerca
   l'indirizzo»: la mappa va al centro del comune, senza chiedere l'indirizzo.
3. «viale Ghirotti 286», «Cesena» → Genera il 3D → **Isometrica**: l'edificio occupa circa metà dell'inquadratura. Ora, con
   il 3D aperto, cerca «viale Settembrini 2», «Rimini»: la mappa torna **2D dritta**, il 3D di prima sparisce.
4. Faenza, «corso Mazzini 50» (o un edificio del centro con il tetto a falde): Genera il 3D → falde colorate sul tetto;
   tabella «Falde dei tetti» con «tetto stimato dal colmo DBTR»; scarica il PNG: in fondo la riga «Colori: …» e «Tetto a falde
   stimato dal colmo DBTR per N corpi». L'ospedale di Rimini resta piatto (il DBTR non ha il colmo dei suoi corpi).
5. **Bagno di Romagna**, foglio 54 particella 216 → Genera il 3D: la vista **non diventa nera**, le colline si vedono
   ombreggiate; barra della vista 3D «Rilievo ×1 ×1,5 ×2»: ×2 esagera le colline; in legenda «Terreno: DTM 5 m Regione
   Emilia-Romagna…»; nel selettore della fonte c'è anche **Sentinel-2 cloudless**; scegliere «Geoportale Nazionale – AGEA
   2012» **non** sposta la vista. Il riquadro dice «Edificio … Comune: Bagno di Romagna» **senza** «Qui non c'è ancora il
   DBTR».
6. **Ortofoto**: «via Fratelli Cardinali Cicognani 74», «Brisighella» e poi rimpicciolisci: **niente zone nere**, dove la RER
   non ha dati si vede il contesto Sentinel-2. Passo 1 «Cerca il luogo» a destra. Strato delle particelle: la legenda dice
   degli scarti di 1–5 m.
7. «via XXIV Maggio 10», «Novafeltria»: messaggio «Indirizzo senza coordinate … Ti porto al centro del comune», la mappa sul
   paese (mai tutta nera).
8. **Immagine**: in Modelli 3D clic su **PNG**: il file va **subito nei download**, nessuna finestra; spunta «chiedi dove
   salvarlo» e riprova: si apre «Salva con nome».
9. **Aggiungi edifici**: trascina lo zip o il `.gpkg` di Lugo nella zona «Trascina qui» (nessuna finestra); senza comune
   «Apri in Modelli 3D» scrive **accanto** «Scegli prima il comune…»; scelto «Lugo», apre Modelli 3D; tornando indietro,
   «Togli gli edifici del file…» scrive accanto cosa ha tolto.
10. **Pagina interna** `/interno/edifici.html`: con la coda vuota «Nessuna proposta in coda…».
11. Pesaro (fuori dal DBTR): gli edifici OpenStreetMap sono **marroni**, in legenda «edifici OpenStreetMap».
12. **Frecce dell'ortofoto** (08/11). In **Modelli 3D**, Rimini, zoom alto con la RER: sotto la mappa, accanto a «Genera il
    3D», la croce di frecce è attiva; tre clic su → e uno su ↓: la foto scorre di ~1 m a clic (sagome e particelle ferme),
    accanto «Ortofoto spostata: 3 m E, 1 m S»; la vista non salta, anche dopo «Genera il 3D»; PNG: in fondo «Ortofoto
    spostata manualmente di 3 m E, 1 m S rispetto alla cartografia»; «Azzera» la rimette a posto; con la fonte
    «Sentinel-2 cloudless» o la casella «Ortofoto» spenta le frecce sono grigie e il tooltip dice perché. In **Ortofoto**,
    accanto a «Scarica l'immagine»: grigie finché non accendi «Confini delle particelle» o i contorni (tooltip «Accendi
    un'ortofoto e almeno uno strato vettoriale…»), poi attive come sopra. **Novità**: gruppi «Nuovo», «Migliorato»,
    «Verificato», nessuna «Versione del sito»; in fondo «26 ottobre 2026 – Meet EuGEnio», «Siamo online».
13. **Tetti** (08/11). In **Modelli 3D**, Faenza «corso Mazzini 50» → Genera il 3D: sotto la mappa la nota «Tetti: 0
    misurati dal LiDAR, N stimati dal colmo DBTR, K ipotizzati (22° pianura / 32° montagna: …), P piani»; la stessa riga in
    legenda (voce delle falde), nel PNG e nel report. Rimini, un albergo sul lungomare: tetto piano, nella tabella dei corpi
    «tetto piano (uso commerciale (commerciale))». Bagno di Romagna, foglio 54 particella 216: tetti ipotizzati a 22°
    (paese a ~490 m), una casa sopra i 600 m (es. una frazione in collina) a 32°.
14. **Forma dei tetti** (08/11). In **Fotovoltaico › Producibilità con le ombre** (pagina in lavorazione: non è nel menu, aprila con l'indirizzo diretto `/fv-producibilita.html`), stesso edificio di Faenza: nel passo
    «Corpi › Falde dei tetti» il selettore «Forma dei tetti» con «Misurata (LiDAR) dove c'è – non disponibile: …» grigia,
    scelta «Stimata dal colmo DBTR dove c'è» (o «Ipotesi automatica» se il DBTR non ha il colmo); disegna un'area FV sulla
    falda a sud, «Calcola», poi scegli «Tutti piani»: l'area diventa «su telai» a 10°, la producibilità si ricalcola da sola
    e il messaggio dice «Forma dei tetti: «Tutti piani»»; «Ipotesi automatica (22°/32°)»: falde a 22°. Sul telefono (o con
    la finestra stretta a 375 px) niente scorrimento di lato.
15. **Veneto** (08/11). Modelli 3D: cerca «via San Salvatore», «Susegana» (o clic vicino a 45,850 N 12,246 E) → messaggio
    «Sagome dalla Regione del Veneto (IODL 2.0), altezze da OpenStreetMap dove ci sono, altrimenti stimate»; sagome in
    marrone; sotto la mappa la nota «Edifici fuori dal DBTR nella vista: … (… con la sagoma della Regione, … da
    OpenStreetMap) …»; Genera il 3D: con J5 bis fatto il terreno è in rilievo («Quote dei corpi dal DTM del server»,
    legenda «Terreno: DTM 5 m da voli LiDAR Regione del Veneto (IODL 2.0)»), altrimenti piatto; tetto ipotizzato a 22°;
    PNG: righe «Sagome degli edifici fuori dal DBTR: Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0» e ODbL.
    Castello di San Salvatore (45,8507 N 12,2349 E): sagome sulla collina, quote fino a ~160 m.
16. **Menu** (08/11 sera). Sei gruppi: Clima e meteo, Patrimonio, **Edifici**, Cogenerazione, Fotovoltaico, Statistiche;
    nessuna voce delle tendine va a capo. Clima e meteo: ultima voce **«Cambiamento climatico S»**, si apre. Edifici:
    «Obblighi di legge» in cima, «Ecobonus» e «Conto Termico» in fondo, tutte col **triangolo giallo**, grigie, non
    cliccabili, tooltip «In lavorazione: disponibile prossimamente»; lo stesso per Emissioni, le pagine del Fotovoltaico e
    **Comunità energetiche** (ora in Fotovoltaico). Clic su «Fotovoltaico» (riga nera fissata): stesse voci, non
    cliccabili. Indirizzo diretto `/fv-ombre.html`: in cima l'avviso giallo «Pagina in lavorazione, non ancora
    verificata». Sul telefono (375 px) il menu fa lo stesso, un tocco mostra la nota.
17. **Ricerca e Cesena** (08/11 sera). **Ortofoto** e **Modelli 3D** aperti senza nulla nell'indirizzo: la mappa è già
    su Cesena, ospedale Bufalini con la collina dietro; nei campi l'esempio «viale Ghirotti 286», «Cesena». Scrivi solo
    «Cesena» nel Comune della particella e premi «Cerca la particella»: la mappa va al centro del comune. **Previsioni**:
    scrivi «Cesena» nell'indirizzo → compare «Comune di Cesena (FC)», cliccalo: il comune è scelto. Nella colonna della
    mappa di Previsioni e Patrimonio, con la finestra bassa, la barra per scorrere è a **sinistra**.
18. **Comuni dell'08/11**. Modelli 3D: «via dell'Indipendenza 1», «Bologna» → sagome DBTR (non marroni), Genera il 3D
    con il terreno in rilievo (colli a sud); le Due Torri (piazza di Porta Ravegnana) svettano sulle altre (la Garisenda
    più bassa). Poi «viale Abba 102», «Cesenatico» (ospedale) e «via Corridoni 31», «Modigliana»: sagome DBTR, niente «Qui
    non c'è ancora il DBTR». Ravenna, «via Randi 5» (ospedale) e la stazione: entrambe coperte. Misano Adriatico, piazza della Repubblica, e Morciano: sagome DBTR. Conselice, «via Selice 101»:
    terreno dal DTM (non piatto per un errore: la bassa è davvero piana, la legenda dice «DTM 5 m Regione Emilia-Romagna»).
19. **Città dell'08/11** (sezione K). Modelli 3D, una prova per città: scrivi indirizzo e comune → sagome del DB
    topografico (non marroni, niente «Qui non c'è ancora il DBTR»); Genera il 3D; clic sull'edificio indicato: la gronda
    nella tabella dei corpi deve essere quella scritta (±1 m; a Napoli il centro della classe) e in fondo al PNG c'è
    l'attribuzione dell'archivio. Se una città mostra sagome marroni → F12 → Rete, filtro `archivi.json` (vedi sotto).
    - **Milano**, «piazza del Duomo 1»: Duomo **65,8 m**; poi «piazza Tre Torri», Torre Allianz **200,7 m**. PNG: «Comune di
      Milano – Database Topografico 2020 … (CC BY 4.0)».
    - **Torino**, «corso Inghilterra 3»: grattacielo Intesa Sanpaolo **166 m**; «via Montebello 20», Mole **55 m** (corpo
      murario, la guglia non è un volume). Licenza «CC BY 2.5»; terreno piatto o Copernicus (BDTRE senza quote).
    - **Genova**, «via di Francia 1»: Matitone **101,2 m**. Fuori dalle 4 tavole (es. Nervi) sagome OSM marroni: è giusto.
    - **Venezia**, «piazza San Marco»: campanile gronda **73,7 m**, colmo **93,5 m** (tetto a capanna stimato; la cuspide
      vera arriva a 98,6 m); «via Paccagnella 11» (Mestre), Ospedale dell'Angelo: corpo più alto **28,0 m**; «Castello
      6777» (Ospedale Civile ai Santi Giovanni e Paolo): edificio principale **17,8 m**. Licenza «IODL 2.0», PNG «Comune
      di Venezia – DBGT, Unità volumetriche (IODL 2.0)».
    - **Trieste**, «piazza dell'Unità d'Italia 4»: Municipio **24,1 m**; «strada di Fiume 447» (Cattinara): torri **54,8 m**.
    - **Trento**, «piazza Duomo»: Duomo **22,6 m**.
    - **Bolzano**, «piazza Duomo»: campanile **53,9 m** (navata 14,4 m); licenza «CC0 1.0».
    - **Firenze**, «piazza del Duomo»: cupola **112,6 m**; «piazza della Signoria», Palazzo Vecchio **40,5 m**.
    - **Ancona**, «piazzale del Duomo»: San Ciriaco **10,4 m** (una sola gronda per edificio: dato regionale 1:10.000).
    - **Roma**, «piazza San Pietro»: basilica **45,6 m**; «piazza Venezia», Vittoriano **63,3 m**. Fuori dal foglio 374
      sagome OSM marroni: è giusto.
    - **Bari**, «corso Cavour 12»: Teatro Petruzzelli **25,1 m**; licenza «IODL 2.0».
    - **Potenza**, «via Potito Petrone» (Ospedale San Carlo): corpo più alto **38,6 m**; licenza «IODL 2.0».
    - **Napoli**, «via Antonio Cardarelli 9» (Ospedale Cardarelli, DEA): **25 m**, fonte «Copernicus UA Building Height
      2012 (10 m): classe 20–30 m, 25 m»; Centro Direzionale (Palazzo di Giustizia): **100 m**, classe 100–368 m. PNG:
      «© European Union, Copernicus Land Monitoring Service 2012, European Environment Agency (EEA)».
    - **Palermo**, «piazza Verdi»: Teatro Massimo **39,3 m**.
    - **Cagliari**, «piazzale Ricchi 1» (Ospedale Brotzu): corpo più alto **26,4 m**; Castello, Cattedrale **17,9 m**.
20. Console: nessuna riga rossa a parte, eventualmente, le tessere fuori zona; Rete: nessuna richiesta `lidar/indice.json`
    né `terreno.pmtiles`, nessun 404 su `contesto/…json`.

Cosa fare se va male: pagina vecchia → J9 di nuovo e Ctrl+F5; ortofoto ancora nera → J5 (seconda riga di prova) e J7;
3D nero → mandami lo screenshot e la Console; «Qui non c'è ancora il DBTR» in uno dei 28 archivi o in una delle 15 città → F12 → Rete, filtro
`archivi.json`: mandami il contenuto della risposta.

### J11. [PC] Commit e push
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_dbtr|estraz_procons|\.gpkg$|DTM5x5|archivi_edifici|archivi_citta|\.tar\.gz$|giornaliero.*\.parquet"
```
```powershell
git commit -m "07/11/2026 sera: correzioni dalle prove di Paolo - Dati climatici e Legge 10 non sperimentali; ricerca nella colonna destra e per solo comune; barra della colonna a sinistra; isometrica al doppio dell'edificio; edifici OSM in marrone; 3D azzerato con nuova ricerca; tetti a falde stimati dal colmo DBTR; camera 3D sopra il terreno, rilievo ombreggiato ed esagerazione; ortofoto RER trasparente dove non ha dati; coordinate 0,0 mai un punto; download senza finestre e Aggiungi edifici con trascina; archivi.json senza copia lunga; copertura vicino ai confini; sito ?v=20261107b; frecce per spostare l'ortofoto di 1 m; Novita: Meet EuGEnio; tetti ipotizzati 22/32 gradi in cascata e Forma dei tetti nelle pagine Edificio e FV; sagome del Veneto con le altezze OSM; terreno da piu DTM (Veneto); menu dell'08/11: gruppo Edifici, pagine di Edifici, Cogenerazione e Fotovoltaico in lavorazione e non accessibili, Cambiamento climatico in Clima e meteo, Comunita energetiche in Fotovoltaico, Ecobonus e Conto Termico segnaposto; tendine larghe, barra a sinistra in tutte le pagine a due colonne; ricerca col solo comune anche in Previsioni; mappe aperte su Cesena (ospedale Bufalini); 8 comuni DBTR nuovi (Bologna, Cesenatico, Bellaria-Igea Marina, Bagnacavallo, Conselice, Modigliana, Alfonsine, Cotignola, Misano Adriatico con Morciano) e Ravenna citta, quadrante NE del DTM; lettori regionali (14 adattatori nuovi, 17 in tutto: Lazio, Basilicata, Piemonte, Toscana, Puglia, Marche, Palermo e CTR Sicilia, FVG ed. 2, Trento, Bolzano, Sardegna, Campania, Comune di Venezia) e 15 citta (Milano, Torino, Genova, Venezia, Trieste, Trento, Bolzano, Firenze, Ancona, Roma, Bari, Potenza, Napoli con altezze Copernicus Urban Atlas, Palermo, Cagliari); cartelle per licenza cc-by e iodl; confronta-dsm e altezze_ua; sagome al volo di Sardegna e Campania; regioni.toml aggiornato; lettere alle Regioni da inviare (LETTERE_DA_INVIARE_2026-11-08)"
```
```powershell
git push
```
Cosa aspettarsi: il terzo comando **non stampa nulla**; il push finisce con `… main -> main`.

Cosa fare se va male: righe dal terzo comando → `git restore --staged <percorso>` per ognuna e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`.

### J12. [PC o Browser] Release `v2026.11.07b`
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.07b --target main --title "EuGEnio 7 novembre 2026 (sera) – Tetti a falde, 3D in collina e ortofoto da allineare" --notes-file ..\note_release.md
```
Cosa aspettarsi: l'indirizzo `https://github.com/statocritico/eugenio/releases/tag/v2026.11.07b`.

Senza `gh`: come F23 dal browser, con tag `v2026.11.07b` e il testo della prima voce di `novita.html`.
