# Fase 10 – Edifici 3D, ortofoto, LiDAR e analisi energetiche

Stato al 09/11/2026 c (sito `?v=20261109c`, procedura Q di `AGGIORNAMENTO_2026-11-09c.md`, dopo le prove P9):
- **Tetti (decisione di Paolo del 09/11/2026)**: le pagine 3D partono con **tutti i tetti piani** e l'utente sceglie i tetti
  a falde con la tegola della sezione «Coperture» (fase 5). `edifici3d/tetti.py` (stima dal colmo e ipotesi 22°/32°) e le
  falde per corpo del LiDAR (`lidar.py`, `lidar/falde/`) restano nel codice e nella pipeline ma sono **sospesi nella
  vista**: la pagina non li usa e non chiede più le celle `lidar/falde/`. Le chiome (`lidar/alberi/`) restano.
- **Zoom massimi reali delle ortofoto** (`ortofoto/*.toml`, campo `zoom`): 20 cm a terra = zoom 19 (0,21 m/pixel a
  44° N) per RER 2023-24, Toscana 2023, Trento 2015 e Bolzano 2023 (prima 20); AGEA 2012, 50 cm = zoom 18 (prima 19);
  Sentinel-2 10 m = zoom 14, servito fino al 15 (EOX ha tessere fino al 17, solo ingrandite). Oltre lo zoom massimo la
  mappa ingrandisce le tessere disponibili. Il campo `regione` dei TOML («00» nazionale) serve ora anche alla pagina per
  mostrare solo le fonti applicabili nel punto.

Stato al 09/11/2026 b (sito `?v=20261109b`, procedura P1–P10 di `AGGIORNAMENTO_2026-11-09b.md`, dopo le prove N10):
- **Celle LiDAR**: `lidar/indice.json` ha ora l'elenco `celle` (`falde`, `alberi`: i nomi `<i>_<j>` delle celle di 0,01°
  che esistono), scritto dalla pipeline a ogni tessera (`Pipeline._indice` → `celle_presenti`) e, per gli indici di prima,
  dal comando nuovo **`python -m edifici3d lidar-celle --archivio <archivio>`** (`aggiorna_celle_archivio`: tutti i
  `**/lidar/indice.json`, salta le cartelle con «_»). La pagina 3D chiede solo quelle celle: prima chiedeva ogni cella
  attorno al punto, anche a Roma o in Veneto, con decine di 404 in Console. Test `test_lidar_celle_aggiorna_gli_indici_vecchi`
  e controllo dell'elenco in `test_pipeline_campione_completa_e_idempotente`; la demo del sito (`fase5-sito/sito/dati/edifici3d/lidar/indice.json`) ha l'elenco.
- **Ortofoto della Toscana**: fuori dalla regione, ma dentro il suo riquadro (Bagno di Romagna, Cesena, Bologna, La Spezia,
  Perugia, provate il 09/11), la WMS risponde 200 con un JPEG bianco di ~1,7 kB e la scritta «Fonte dei dati: Regione
  Toscana – Base informativa territoriale…» («strane scritte sul terreno bianco» nelle prove di Paolo). Campo nuovo
  `segnaposto = true` in `ortofoto/toscana.toml` (documentato in `emilia_romagna.toml`): il proxy rende queste tessere vuote
  (fase 4).

Stato al 09/11/2026 (sito `?v=20261109a`, procedura N1–N12 di `AGGIORNAMENTO_2026-11-09.md`):
- **Roma** e **Bari** per il comune intero (archivi del 09/11; comando `b_regioni dbgt-fogli`).
- **Archivi DBTR del 09/11** (estrazioni 354181–354187): **Bologna intera** (mancano solo 7 fogli rurali), Castel
  Bolognese intero, Ravenna con parte del forese, Misano rifatto con quasi tutto Coriano, 17 comuni della Romagna e 8
  comuni vicini a Bologna parziali: 29 archivi (`archivi_er_0911/`), **69 voci** in `archivi.json`. Le estrazioni
  raggruppate si dividono per comune con il nuovo comando `dividi` (`edifici3d/dividi.py`, test `test_dividi.py`);
  sezione «Comuni dell'08/11 e del 09/11/2026». La pagina legge ora fino a **150 archivi** (prima 60).
- **Tetti ipotizzati**: cortile solo se il buco è di almeno 25 m² o del 10 % della pianta (`tetti.cortili`,
  `CORTILE_MIN_M2`, `CORTILE_MIN_QUOTA`; uguale a `cortiliDi` della pagina): a Bagno di Romagna (foglio 54 particella 216)
  il corpo di 178 m² con un buco di 8 m² occupato da un corpo interno restava piano, ora capanna a 22°. Soglia di montagna
  600 m invariata. Test `test_cavedio_non_e_un_cortile` e casi di parità `cavedio`, `cortile_quota`.
- **Ortofoto**: ritmo verso la fonte RER 8/s (misurate 0,3–0,5 s a tessera) e AGEA 2012 4/s e 4.000/h; la RER 2023-24 **non
  ha immagini** a Bologna, Modena, Parma, Imola, Ferrara, Faenza, Bagno di Romagna, Comacchio (tessere vuote a ogni scala,
  prove del 09/11): il proxy le dichiara (`X-Ortofoto-Vuota`) e le pagine passano da sole alla fonte successiva. I WMS AGEA
  della Regione (`agea2011_rgb`, `agea2020_rgb`, `agea2023_rgb`) esistono ma restano esclusi (§ 6).
- **Alberi** della pagina 3D: vengono dalla pipeline LiDAR (`lidar_corpi.alberi`: celle di 2 m del DSM − DTM alte e
  fuori dalle sagome, entro 50 m dagli edifici, `lidar/alberi/<cella>.json`), non da OSM; nella pagina ora sono chiome
  (ottagoni che si fondono), accese dalla casella «Alberi» (spenta in partenza); restano ostacoli per le ombre.
- **Due Torri di Bologna**: nel DBTR un solo volume (UVL 47888, 157,8 m², edificio «Altro», foglio 0) **senza altezza**
  (`H_UVL` 0, `H_GRONDA` e `H_COLMO` vuoti), scartato dalla preparazione; la Garisenda non ha un volume suo. Per vederle
  serve una correzione dell'archivio (`DA_FARE.md`).

Stato all'08/11/2026 (stessa versione `?v=20261107b`, decisioni di Paolo):
- **Lettori regionali e 15 città** (08/11/2026 notte): 17 adattatori (`edifici3d/adattatori/`), archivi di Milano,
  Torino, Genova, Venezia, Trieste, Trento, Bolzano, Firenze, Ancona, Roma, Bari, Potenza, Napoli, Palermo e Cagliari;
  cartelle per licenza `cc-by/` e `iodl/`; sezione «Lettori regionali e città di riferimento (08/11/2026)».
- **Tetti a falda, tre fonti** (`edifici3d/tetti.py`, gemello di `edifici_calcoli.js`: `faldeStimate`, `tettoIpotizzato`,
  `zonaAltimetrica`, `motivoTettoPiano`; test di parità in node `tests/test_tetti.py`): 1. falde misurate dal LiDAR;
  2. tetto stimato dal colmo DBTR; 3. **tetto ipotizzato a falde, 22° in pianura e 32° in montagna**, stessa forma (capanna
  sul lato lungo del rettangolo minimo, padiglione se lato lungo/lato corto < 1,3), colmo = gronda + semiluce ×
  tan(inclinazione). **Pianura o montagna** (scelta documentata): la classificazione ISTAT dei comuni per zona altimetrica
  non è nei dati del sito e non è tra i file aperti che ISTAT pubblica oggi (altimetria e fasce altimetriche dei comuni
  al 31/12/2021, senza la zona), quindi vale la **quota del terreno sotto il corpo** (DTM, `quota_terreno`) con le soglie
  della definizione ISTAT di montagna: **≥ 600 m nei comuni del Nord, ≥ 700 m al Centro, al Sud e nelle isole** (provincia
  dal codice ISTAT del comune); senza la quota del corpo (OSM) l'altitudine del comune del DPR 412/93; senza nessuna,
  pianura. Collina = pianura (22°). **Piani** i corpi plausibilmente piani: uso `capannone`, `commerciale`, `palestra`,
  `industriale` (DBTR o OSM), tipi DBTR industriali/tettoie/hangar/serre/cabine/tribune/palazzi dello sport, cortili,
  **oltre 1.500 m²**, **lato corto oltre 25 m**, **gronda sotto 3 m**, forma poco rettangolare (< 70 % del rettangolo minimo:
  più robusto del numero di lati) o più stretta di 2 m. Conteggi per archivio con `tetti.conta_tetti`: **Rimini** 40.518
  corpi = 0 LiDAR, 4.103 colmo DBTR, 28.107 ipotizzati (tutti a 22°), 8.308 piani (2.432 bassi, 1.677 commerciali, 1.494
  capannoni, 1.744 poco rettangolari, …); **Bagno di Romagna** 5.019 = 0 LiDAR, 0 colmo, 4.211 ipotizzati (2.843 a 22°,
  1.368 a 32°), 808 piani (346 capannoni). Nella pagina: cascata in Modelli 3D, selettore «Forma dei tetti» nelle pagine
  Edificio e Fotovoltaico (README della fase 5).
- **Sagome regionali al volo con le altezze OSM** (`edifici3d/sagome_regionali.py`, `fonti/sagome_regionali.toml`): livello
  della catena delle sagome tra il DBTR del comune e OpenStreetMap. Fonti accese: solo quelle «attiva» in `regioni.toml`,
  **senza altezze** e con un WFS che risponde: oggi il **Veneto** («Edifici del Veneto (feb. 2022)», IODL 2.0, WFS
  `idt2-geoserver.regione.veneto.it`, `rv:edifici_veneto_feb2022`, **bbox nel sistema nativo EPSG:6876**: in EPSG:4326
  restituisce 0). Altezza di ogni sagoma dall'edificio OSM che le si sovrappone di più (≥ 10 % della sagoma; height, poi
  piani × 3 m), poi mediana dei corpi DBTR vicini o dei vicini con l'altezza OSM (`osm_vicini`, entro 200 m, almeno 3),
  poi 9 m; gli edifici OSM senza sagoma regionale (sovrapposti per meno del 20 %) restano OSM. Codici `edi_uso` letti con
  il catalogo nazionale dei DB topografici (01 residenziale, 07 commerciale, 08–09 produttivo/agricolo, …): legenda veneta
  da confermare. Valutate e non accese: Valle d'Aosta, Umbria, Sicilia (in attesa, nessun WFS aperto provato), Piemonte e
  Toscana (servizi non raggiungibili dal container), aggregati strutturali della Protezione Civile (solo file per regione,
  nessun servizio interrogabile per riquadro). Prova dal vivo dell'08/11 (rotta del server, README della fase 4):
  castello di San Salvatore 52 sagome (0 con altezza OSM), Susegana via San Salvatore 396 (4 con altezza OSM, 60 dalla
  mediana dei vicini OSM), Conegliano centro 1.153 (1).
- **`dtm-server` con più file** (`dtm_locale.cog_server`): uno o più zip, TIFF o **ESRI ASCII Grid** (anche una cartella),
  mosaicati in un COG unico per zona; `--crs` per i file senza sistema (le tavole del Veneto non hanno il `.prj`:
  **EPSG:6876**, verificato con le quote di Susegana), `--regione er|veneto` per la scheda (licenza, attribuzione, nome in
  legenda), data dei dati dallo zip. Prova con le **40 tavole** 2 km × 2 km del DTM 5 m da voli LiDAR (Susegana e
  Conegliano, 2024-06-03): COG di 12,5 MB in 2,5 s; castello di San Salvatore 157 m, via San Salvatore 78 m, Conegliano
  73 m (Copernicus sulla stessa tessera: 72–127 m). La rotta `/api/terreno` usa più DTM insieme (README della fase 4).
  Altre tavole venete: https://idt2.regione.veneto.it/idt/downloader/download → «Modelli digitali» → «DTM 5 m da voli
  LiDAR» → provincia e comune → scarica gli ZIP delle tavole (`12_2K_NNNN.asc.zip`; nessun download automatico pubblico
  trovato: la pagina è un'applicazione con la scelta a mano).
- 133 test (fase 10).

Stato al 07/11/2026 sera (sito `?v=20261107b`, correzioni dalle prove di Paolo, sezione I di `AGGIORNAMENTO_2026-11-07.md`):
**tetti a falde stimati dal colmo DBTR** nella pagina (`edifici_calcoli.js`, `faldeStimate`: capanna sul lato lungo del
rettangolo minimo, padiglione se lato lungo/lato corto < 1,3; precedenza falde LiDAR → colmo DBTR → piano; il colmo è già
nelle proprietà dei corpi degli archivi, nessuna rigenerazione: 6.946 corpi a Rimini, Faenza e Santarcangelo; gli altri 16
comuni non hanno H_COLMO); `archivi.json` con `lidar` solo se `cc-by/er/prodotti/lidar/indice.json` c'è e la pipeline lo
rigenera quando scrive il primo indice delle falde; ortofoto RER in PNG trasparente (`trasparente = true` in
`ortofoto/emilia_romagna.toml`); legenda delle particelle con gli scarti normali del catasto (1–5 m, misurati: il proxy non
sposta nulla); 128 test.

Stato al 07/11/2026 (sito `?v=20261107a`): **DBTR vero dei comuni** (estrazioni dal Geoportale, GeoPackage o Shapefile)
letto con i nomi reali degli strati e delle colonne, regole delle altezze verificate sul LiDAR, un **archivio CC BY per
comune** (`prepara --comune`), `archivi.json` rigenerato dalla cartella degli archivi, **DTM 5 m dai quadranti** della
Regione (letto a finestra anche dentro lo zip), **cortili** (fori) dei corpi dal DBTR e dai multipoligoni OSM, lettura dei
file senza pyarrow (sezione «DBTR dei comuni, DTM dai quadranti e cortili»); 104 test.

Stato al 05/11/2026, seconda pubblicazione (`?v=20261105b`): **strati sopra le ortofoto** (particelle catastali
dell'Agenzia delle Entrate riproiettate dal proxy, contorni degli edifici DBTR/OSM), **archivio di prova OSM** del centro di
Rimini (`osm-campione`), **DTM dal WCS a blocchi** (`dtm-wcs`) e la tabella **«Cosa manca per passare dalla demo al servizio
vero»** (sezione «Strati sopra le ortofoto, archivio di prova e strumenti per il servizio vero»); 96 test.

Prima, **affinamenti Edificio** (sezione «Affinamenti Edificio – blocco 2»: Tabella 11 del DM requisiti
minimi, trasposizione di Perez confrontata con PVGIS, colonne `visura_…`, Patrimonio → Modelli 3D, posa sulla sagoma
dell'archivio, corpi dal solo LiDAR, ombre degli alberi); prima, lo stesso giorno, **edifici fuori dall'Emilia-Romagna** (sezione «Edifici fuori dall'Emilia-Romagna – come si usa»):
adattatori dei DB topografici di Lombardia, FVG e Liguria → corpi, provati su piccoli campioni scaricati dal vivo; zone
LiDAR di Bolzano e Trento in `zone/`; copertura delle fonti nella pipeline (maschera o riquadri) e fonti a più file con
indice; DSM della costa 2019 acceso in `zone/rimini.toml` solo sulle tessere coperte.

Stato precedente, 04/11/2026 (notte): **Fase E in codice** (sezione «Fase E – come si usa» qui sotto): verifica delle fonti
regione per regione in `fonti/regioni.toml` (17 fonti attive, 48 in attesa, 19 non disponibili su 84; ortofoto nuove di
Bolzano 2023 e Trento 2015), altezze di Zornade nell'archivio ODbL (`edifici3d/zornade.py`, provate su un campione
sintetico), aggancio facoltativo al modulo privato delle analisi 5 e 7–13 (`edifici3d/analisi.py`; il modulo
`uni_privato/` contiene solo la struttura ed è fuori da repository e zip pubblico); 56 test in tutto.

Stato precedente, 04/11/2026 (sera): **Fase C in codice** (pipeline LiDAR notturna a tessere con TOML per zona, falde per corpo,
pagina di stato nascosta, import DXF/IFC; 40 test in tutto; sezione «Fase C – come si usa» qui sotto): provata sul
**campione sintetico**; per Rimini le fonti DSM/LAS sono **in attesa** (Regione, PNRR), il DTM 0,5 m è già attivo.

Stato precedente, 04/11/2026: **Fase A e Fase B in codice** (pacchetto `edifici3d/`, 21 test; pagina 3D nel sito; rotte del clima,
delle ortofoto, dell'orizzonte e di PVGIS e report nel server), provate su **dati sintetici** per gli edifici e **dal vivo**
per ortofoto, DEM e PVGIS: i dati veri degli edifici (GeoPackage UVL, DTM 5 m, aggregati, OSM) non sono ancora stati
scaricati (sezione «Fase A – come si usa» qui sotto). Fase B: sezione «Fase B – come si usa». Restano segnaposto nei
gruppi Patrimonio (LiDAR, Visure), Edificio (Fabbisogno, Facciate e tetti, Impianti, CER, Clima) e Fotovoltaico (LEED, mercato).

Documento di riferimento: [`../documenti/PROPOSTA_3D_EDIFICI_E_VISURE.md`](../documenti/PROPOSTA_3D_EDIFICI_E_VISURE.md)
(discussione del 30/10–01/11/2026, §§ 1–12 e 15). Le visure catastali sono nella [fase 11](../fase11-visure/README.md).

## Obiettivo

L'utente sceglie un edificio sulla mappa (o carica un proprio modello DXF/IFC/DWG) ed EuGEnio ricostruisce in 3D
l'edificio, gli edifici vicini e il terreno, poi calcola:
- ombre e percorso del sole nel ciclo diurno;
- ore di sole e irradiazione su tetti e facciate (annua, mensile, giorno tipo);
- producibilità fotovoltaica con le perdite per ombreggiamento, con il clima orario già archiviato (ERA5 corretto
  verso ICON, radiazione globale e diffusa per comune);
- confronto con PVGIS;
- analisi energetiche del patrimonio (§ 9, tabella sotto);
- supporto al D.Lgs. 199/2021 (Allegato III) e prefattibilità LEED.

Sopra la mappa: ortofoto come livello d'immagine, con confini ed edifici sovrapposti.

## Decisioni (§ 2 della proposta)

| Tema | Decisione |
|---|---|
| Edifici da Zornade | **niente scaricamento via API** (lo scraping massivo fa sospendere il token); l'estratto ER offerto da Zornade è OpenStreetMap e **in ER non serve**; si resta in contatto per le altezze LiDAR (da novembre) e per le regioni senza buon DB topografico |
| Base edifici in ER | **DBTR – Unità volumetrica (UVL)**, CC BY 4.0, con altezza per corpo di fabbrica |
| Licenze | archivio **CC BY** (DBTR, aggregati, LiDAR) separato dall'archivio **ODbL** (OSM); ogni edificio porta la licenza della sua sagoma |
| Tetti | inclinazione stimata dal DSM; se le altezze sono irregolari il tetto è piano; l'utente disegna i rettangoli FV e corregge inclinazione e orientamento |
| Edifici a più corpi | ogni corpo è un prisma con quota di base, altezza e tetto propri; l'edificio resta un'unità per selezione, totali e report |
| Metodiche UNI | si implementano anche senza risposta di UNI; testi, prospetti e formule in un **modulo privato** fuori dal repository (§ 10, vedi sotto) |
| Pipeline | notturna e automatica, una zona alla volta (Rimini → Forlì-Cesena → Ravenna → resto ER), aggiornamento annuale a rotazione |
| Avvisi | **nessuna email**: pagina di stato nascosta protetta da Cloudflare Access |
| Ortofoto | RER 2023-24 in ER; ortofoto regionali in CC BY altrove; AGEA 2022–24 RGB per siti puntuali |
| Piani | stimati dall'altezza; per il patrimonio dell'utente presi dalle visure catastali (fase 11) |
| SPID | il sito pubblico non usa mai lo SPID dell'utente |

### Metodiche UNI (§ 10) – nuova decisione del 03/11/2026

- Si implementano UNI/TS 11300, EN ISO 52016, UNI 10349 anche senza risposta di UNI.
- 07/11/2026 (Paolo): con lo stesso criterio anche **UNI EN 17463:2021** (VALERI, valutazione degli investimenti
  energetici) e **UNI EN 15459-1:2018** (valutazione economica dei sistemi energetici degli edifici), per le valutazioni di
  convenienza economica: solo calcoli interni, nel modulo privato; sul sito solo risultati e citazione.
- Non si ridistribuiscono testi, prospetti, estratti o formule. Paolo legge le formule.
- Coefficienti, prospetti e passaggi presi dalle norme stanno in un **modulo o file di dati privato**, sul server ma
  fuori dal repository (come la fase 2): `fase10-edifici3d/uni_privato/` (in `.gitignore`, fuori dallo zip pubblico).
  Il codice pubblico contiene solo la struttura del calcolo e legge il modulo privato se c'è; senza, le analisi UNI
  restano spente (mirror compresi).
- Sostituisce la decisione del 27/10/2026 «i prospetti UNI 10349 non si elaborano con strumenti di IA». Resta valido
  che i prospetti UNI 10349 **non si pubblicano**.

## Catena di ripiego delle fonti (§ 4)

| Dato | Ordine |
|---|---|
| Sagoma | modello dell'utente → DBT regionale con unità volumetriche (ER: UVL) → aggregati Protezione Civile divisi con le particelle → OSM (costruzioni recenti, archivio ODbL separato) |
| Altezza | modello dell'utente → LiDAR più recente che copre l'edificio (PNRR → RER → PST), DSM − DTM → DBT → OSM `height` o `building:levels`×3 → GHSL 100 m → valore dell'utente (stima) |
| Terreno | DTM regionale (ER 0,5 m o 5 m; Veneto DTM 5 m da voli LiDAR dall'08/11/2026, il più dettagliato prima) → LiDAR PNRR/PST → Copernicus DEM 90 m (tessere 3D) |
| Tetto | falde LiDAR → stima dal colmo DBTR → ipotesi 22° pianura / 32° montagna (o piano per capannoni e corpi grandi) |
| Orizzonte lontano | Copernicus DEM 90 m, raggio 20–30 km (già usato in fase 3) |
| Ombre di alberi ed edifici | DSM primo impulso dove disponibile |

Per ogni dato si salvano **fonte** e **qualità**. Fuori dall'ER la scelta tra aggregati (CC BY) e OSM (ODbL) si fa
regione per regione.

**Decisione di Paolo del 07/11/2026 – OSM come ripiego al volo in Modelli 3D.** Dove il punto cade fuori da ogni
archivio di qualità (DBTR: fuori dall'Emilia-Romagna e nei comuni ER non ancora preparati) la pagina usa gli edifici OSM
intorno al punto, chiesti al server (`GET /api/edifici/osm`, Overpass, README della fase 4) e letti con le regole di
`osm_campione` (`query_punto`, `corpi_al_volo`); **dove c'è il DBTR vale il DBTR e OSM non si mescola**. Zona coperta da un
archivio di un comune intero = **confine ISTAT del comune** (`istat` in `archivi.json`, tabella `uvl.COMUNI_ISTAT` o
`prepara --istat`); per gli archivi parziali (`prepara --parziale`, es. Ravenna, solo l'ospedale) e quelli senza codice, il
riquadro dei corpi. L'archivio «di prova» OSM del centro di Rimini (`odbl/rimini-prova/`) non si elenca più in
`archivi.json` (i file restano sul server come riserva; `archivi-json --con-prova` per rimetterlo).

**Altezze dei corpi OSM (decisione di Paolo del 07/11/2026 pomeriggio).** `osm_campione.altezze_da_vicini`: i corpi senza
`height` né `building:levels` (prima tutti a 9 m) prendono la **mediana delle gronde dei corpi DBTR vicini** (entro
`RAGGIO_VICINI` = 200 m dal centro, almeno `MINIMO_VICINI` = 3; `altezza_dbtr_valida` esclude i corpi già portati alla
stima e quelli fuori da 2–80 m), arrotondata al mezzo metro; altrove restano i 9 m. Sempre «stima»: `origine_altezza`
(`osm_height`, `osm_piani`, `dbtr_vicini`, `fissa`) e `fonte_altezza` per corpo, `conta_altezze` per i conteggi. La usa la
rotta del server con gli archivi che ha e, con lo stesso algoritmo in JS, la pagina con il DB topografico caricato nel
browser. Test: `test_origine_e_conteggi_delle_altezze_al_volo`. Istanza di riserva di Overpass del TOML
`ortofoto/strati/edifici.toml`: **Overpass API Europa** (ovp.dresel.systems) al posto di maps.mail.ru, con le alternative
valutate (README della fase 4). Dal 07/11 sera tutte le pagine 3D (Edificio e Fotovoltaico) usano gli archivi come Modelli
3D (README della fase 5).

Catena delle fonti delle sagome in Modelli 3D (dall'08/11/2026): modello dell'utente → DBTR del comune (CC BY 4.0) → **sagome regionali al volo con le altezze OSM** (Veneto, IODL 2.0 + ODbL) → OpenStreetMap al volo
(ODbL 1.0, ripiego; altezza `height` → `building:levels` × 3 m → stima di 9 m dichiarata) → nessun 3D (Overpass giù o
ripiego spento).

Verifiche fatte (§ 3): il catasto AdE in blocco non ha i fabbricati; aggregati Protezione Civile nazionali senza
altezze; DBTR UVL con altezze ±3 m (da verificare se gronda o colmo, e se c'è il numero di piani); DTM ER 5×5 m
(dicembre 2025); LiDAR RER2023/24 e RER2025/26 (DSM e LAS solo su richiesta); PST MASE non automatizzabile, portale
offline fino al 7/11/2026; LiDAR PNRR a 25 cm in arrivo; strato edifici Zornade = OSM (ODbL); GlobalBuildingAtlas
CC BY-NC (escluso); PVGIS 30 chiamate/s, niente CORS, `userhorizon`.

## Ortofoto (§ 6)

| Ordine | Fonte | Uso |
|---|---|---|
| 1 | ER: RER 2023-24, 20 cm, CC BY 4.0, WMS `RER2023_24_RGB` | proxy con cache sul server (**fatto**; stato «da confermare» con la Regione, spegnibile) |
| 2 | ortofoto regionali in CC BY verificate una per una, un TOML per regione | proxy con cache (**fatto**: Toscana 2023; Fase E: Bolzano 2023, Trento 2015) |
| 3 | AGEA 2022–2024 RGB (CC BY 4.0, Reg. UE 2023/138) | a mano per siti puntuali, ridotte a 50 cm, fuori pipeline (**comando `ortofoto-sito`**) |
| 4 | Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) | contesto di zona (**fatto**, con copia) |
| 5 | WMS Geoportale Nazionale (AGEA 2012) | solo dal vivo, senza cache (**fatto**, mai nei report) |

Esclusi: AGEA infrarosso e foto originali; WMS regionali AGEA «Utilizzo ristretto» finché la Regione non conferma;
Google, Esri, Bing; EOX 2018+ (CC BY-NC-SA). Nei report ogni figura con ortofoto porta licenza e citazione.

## Architettura (§§ 5, 7, 8)

**Sito**
- WebGL: MapLibre GL (edifici estrusi per corpo, terreno, WMS) e three.js (ombre), ospitati sul sito, non da CDN.
  `mappa3d.js` resta per le barre di Patrimonio.
- Ombre nel browser (Web Worker): profilo d'orizzonte per punto (36–72 direzioni); clima orario dall'archivio,
  componente diretta ricavata, trasposizione di Perez, modello FV tipo PVWatts (pvlib come riferimento).
- Modelli importati (DXF, IFC con ezdxf e IfcOpenShell; DWG con LibreDWG o convertitore ODA; glTF/OBJ, CityJSON,
  GeoJSON) elaborati solo nel browser, con passaggio di posa.
- Aree FV: rettangoli agganciati ai lati del corpo, aderenti o su telai (ombra tra le file), fasce di rispetto,
  conteggio moduli e potenza; confronto PVGIS.

**Server**
- Edifici in PMTiles e DTM/DSM in COG, serviti da Caddy come file statici; PVGIS chiamato dal server.

**Tetti dal DSM, per corpo**: punti dentro il corpo meno ~1 m di bordo; altezza = mediana (DSM − DTM); si prova piano,
capanna, padiglione e si sceglie il più semplice che riduce davvero l'errore; RMSE > 0,3–0,5 m o pendenza < ~5° →
piano; edificio non presente nel rilievo → fonte successiva.

**Corpi di altezza diversa (§ 7)**: UVL già divise; LiDAR senza UVL → raggruppamento per altezza simile (1–1,5 m),
scarto sotto 20–25 m²; UVL + LiDAR → confini UVL, altezza LiDAR; nessuno → una sola altezza, divisibile dall'utente.
Pareti in comune non disperdono (tranne la parte che sporge).

**Piani e superfici (§ 8)**: piani ≈ (gronda − sovralzo) ÷ interpiano (residenziale ~3,0 m, uffici e scuole
3,3–3,6, ospedali 3,8–4,5, capannoni un piano); lorda = Σ area × piani; netta ≈ 0,80–0,85 × lorda. Precedenza:
valore del CSV → visura → stima. Colonne facoltative nuove nel CSV di Patrimonio: piani fuori terra, piani interrati,
superficie lorda, netta, catastale, anno di costruzione.

## Analisi energetiche (§ 9)

| # | Analisi | Pagina del sito |
|---|---|---|
| 1 | indicatori geometrici, S/V, pareti per orientamento e in comune | Edificio › Geometria e luce naturale |
| 2 | consumi normalizzati (kWh/m², kWh/m³, €/m²) | Edificio › Consumi, firma energetica e priorità |
| 3 | firma energetica (consumi ↔ gradi giorno reali) | idem |
| 4 | classifica di priorità del patrimonio | idem |
| 5 | fabbisogno con le metodiche UNI | Edificio › Fabbisogno con le metodiche UNI |
| 6 | FV sui tetti con le ombre, autoconsumo | Fotovoltaico › Producibilità con le ombre |
| 7 | comunità energetiche per cabina primaria | Edificio › Comunità energetiche |
| 8 | apporti solari sulle facciate | Edificio › Facciate e tetti |
| 9 | sky view factor, luce naturale | Edificio › Geometria e luce naturale; Fotovoltaico › Prefattibilità LEED |
| 10 | pompe di calore, COP/SCOP orari | Edificio › Pompe di calore e solare termico |
| 11 | solare termico per l'ACS | idem |
| 12 | tetti freddi e tetti verdi | Edificio › Facciate e tetti |
| 13 | clima che cambia (gradi giorno dal 1940) | Edificio › Clima che cambia |
| 14 | obblighi di legge (D.Lgs. 199/2021, S/V, zona) | Edificio › Obblighi di legge; Fotovoltaico › D.Lgs. 199/2021 |

Primo pacchetto: 1, 2, 3, 6; poi 4 e 14; poi il resto. Prezzi GME/EEX solo per uso interno: nelle analisi economiche
pubbliche solo convenzioni o prezzi pubblici (ARERA). Le analisi di mercato per FV, BESS e CER sono nella
[fase 12](../fase12-gme-fotovoltaico/README.md).

## Pipeline notturna degli edifici (§ 11)

- Unità: tessera LiDAR 1×1 km. Scarica → elabora → salva risultati → cancella i grezzi.
- Finestra 3:30–7:00 (dopo i mercati), container separato (1 CPU, 4 GB), pausa se c'è una previsione in coda.
- Coda: Rimini → Forlì-Cesena → Ravenna → resto ER → altre regioni; solo tessere con edifici; ripresa dalla tessera
  successiva; zone grandi divise per comune.
- Per tessera: corpi, altezze, falde, qualità; DSM ridotto a 1 m (int16, decimetri) per le aree urbane.
- Salvaguardie: stop sotto 20 GB liberi; quota di download per notte; tessere che falliscono più volte saltate e
  segnalate; registro delle attribuzioni per zona.
- Aggiornamento annuale: ogni giorno la zona più vecchia, solo le tessere con fonte cambiata. Altre regioni: un TOML
  per zona con fonti e licenze.
- Stime per la Romagna (da misurare): Rimini ~300 tessere, ~20 GB scaricati, 1–3 h, ~0,35 GB che restano;
  Forlì-Cesena ~800, ~50 GB, 2–7 h, ~0,7 GB; Ravenna ~650, ~40 GB, 2–6 h, ~0,6 GB.
- Automatizzabile oggi: DTM 0,5 m RER (WCS), DTM 5 m, DBTR UVL, aggregati, OSM. Dipende dalla Regione: DSM e LAS RER.
  Non automatizzabili: PST/PNRR MASE, ortofoto AGEA.

## Pagina di stato nascosta (§ 12)

- `eugenio.statocritico.it/interno/edifici.html`, fuori da menu e mappa del sito, `X-Robots-Tag: noindex` (non nel
  `robots.txt`); dati da `GET /api/interno/edifici/stato` (`stato.json` riscritto a ogni tessera).
- Cloudflare Access su `/interno/*` e `/api/interno/*`, solo l'email di Paolo; Caddy rifiuta le richieste senza
  intestazione di Access.
- Contenuto in sola lettura: zona e avanzamento, coda e date, ultime 30 notti, esiti per qualità, errori, spazio su
  disco, versioni delle fonti. Comandi solo via ssh.

## Fase A – come si usa (04/11/2026)

### Contenuto

| File | Cosa fa |
|---|---|
| `fonti/emilia_romagna.toml` | fonti della zona con URL, licenza e attribuzione; archivi per licenza (`cc-by`, `odbl`); coda Rimini → … |
| `edifici3d/fonti.py` | lettura del TOML, scaricamento con ripresa (Range, file `.parziale`), registro `fonti.json` con SHA256 |
| `edifici3d/uvl.py` | UVL → corpo; controllo automatico degli attributi con rapporto; lettura del GeoPackage (pyogrio) |
| `edifici3d/osm.py` | edifici OSM non coperti dalle UVL (archivio ODbL), altezza da `height` o `building:levels` × 3 m |
| `edifici3d/modello.py` | corpo ed edificio (§ 7), piani e superfici con precedenza file → visura → stima (§ 8), indicatori geometrici (§ 9, analisi 1) |
| `edifici3d/dtm.py` | quota del terreno per corpo (minimo e mediana); COG e tessere Terrarium in PMTiles solo con `--terreno-archivio` (dal 07/11/2026 il terreno 3D viene dalla rotta `/api/terreno` del server) |
| `edifici3d/dtm_locale.py` | DTM 5 m dai quadranti: ritaglio a finestra per `prepara` e `dtm-server` (quadrante → COG unico per la rotta del server) |
| `edifici3d/plausibilita.py` | altezze del DBTR non plausibili portate alla stima (07/11/2026), stessa regola in `dbtr_lettore.js` |
| `edifici3d/tessere.py` | PMTiles vettoriali dei corpi (uno per licenza, rifiuta licenze mescolate) e celle GeoJSON di 0,01° per i calcoli |
| `edifici3d/sintetico.py` | isolato e DTM **sintetici** (vicino a Rimini) e consumi di prova, dichiarati come tali |
| `tests/uvl_wms_campione.json` | 5 UVL vere di Rimini dal GetFeatureInfo del WMS (solo attributi, senza geometria), per il test del controllo |

### Comandi (dalla cartella `fase10-edifici3d`)

```
pip install -r requirements.txt
python -m edifici3d controlla-uvl --wms-punto 44.0600 12.5665          # rapporto su pochi corpi dal WMS pubblico
python -m edifici3d controlla-uvl --gpkg UVL.gpkg                       # rapporto sul GeoPackage regionale
python -m edifici3d scarica --fonte dbtr_uvl --archivio /srv/energia/dati/edifici   # dopo aver scritto l'URL nel TOML
python -m edifici3d prepara --gpkg …/cc-by/er/grezzi/UVL.gpkg --dtm …/dtm5.tif --archivio /srv/energia/dati/edifici \
       [--riquadro x0 y0 x1 y1]                                         # EPSG:7791; una zona alla volta
python -m edifici3d demo --uscita ../fase5-sito/sito/dati/edifici3d     # rifà la demo sintetica del sito
python -m pytest tests
```

`prepara` scrive in `<archivio>/cc-by/er/prodotti/`: `corpi.pmtiles` (strato `corpi`, zoom 13–16), `contesto/<i>_<j>.json`
e `indice.json` (centro, riquadro, licenza, attribuzione); il DTM serve per la quota di ogni corpo. Fino al 07/11/2026
scriveva anche `dtm_cog.tif` e `terreno.pmtiles` (Terrarium, zoom 10–15): ora solo con `--terreno-archivio` (sezione
«Terreno dal server»). Caddy
li serve da `/edifici3d/cc-by/er/prodotti/` (`CARTELLA_EDIFICI` nel `.env`, Caddyfile della fase 4), la pagina li cerca
lì e, se non ci sono, apre la demo sintetica con l'avviso.

### Verifiche del 03–04/11/2026 dal container di sviluppo

- **WMS DBTR** (`servizigis.regione.emilia-romagna.it/wms/dbtr`, strato `UVL_Unita_volumetrica`): raggiungibile;
  GetFeatureInfo in `application/geojson` restituisce tutti gli attributi ma **senza geometria**.
- **Attributi UVL** su 13 corpi (Rimini, Bologna, Ravenna, Parma): `H_uvl` (altezza, m, anche decimale), `B_uvl` (quota
  della base), `Id_e`/`Edi_id_e` (corpo/edificio), `Tipo_fonte` («DTM DSM 2008», «SIT»), `Qualita`, `D_tetto` («Non
  assegnato»); **`H_GRONDA` e `H_COLMO` sempre vuoti, nessun campo con il numero di piani**. Quindi: H_uvl si usa come
  gronda e la fonte lo dice («gronda o colmo da verificare»); i piani si stimano. Da chiedere all'Archivio Cartografico
  o da confrontare col LiDAR (fase C). Il controllo si rifà in automatico sul GeoPackage completo.
- **WFS DBTR** e **WCS DTM**: 401; il link al GeoPackage UVL non compare nella scheda del catalogo (download dalla
  pagina «download-dbtopografico»): URL da completare nel TOML dopo il primo download a mano.
- **Aggregati**: la scheda della Protezione Civile rimanda a cinque repository GitHub `pcm-dpc/DPC-Aggregati-Strutturali-*`
  (ER in `ITH-NordEst`), molto grandi: si scarica solo il file della regione.
- **Overpass** non raggiungibile dal container; per OSM si usa l'estratto Geofabrik (PBF) sul server.

### Scelte tecniche

- Sistema dei dati: EPSG:7791 (RDN2008/UTM 32N); tessere e celle in WGS84; calcoli della pagina in metri locali attorno
  all'edificio (proiezione equirettangolare, errore trascurabile entro 250 m).
- Terreno in MapLibre: il COG non si legge direttamente, quindi servono tessere Terrarium (PNG); dal 07/11/2026 le genera
  il server su richiesta (`/api/terreno/{z}/{x}/{y}.png`) invece di metterle in PMTiles in ogni archivio.
- MapLibre GL **5.24** (UMD, un solo file): la 6 è solo a moduli ES con il worker separato.
- Sole: algoritmo NOAA in JS; ombre al suolo come inviluppo della base e della base proiettata (prismi); orizzonte di
  ogni punto delle aree FV su 72 direzioni nel Web Worker; producibilità oraria con trasposizione **isotropa** (dal
  05/11/2026 **Perez**, sezione «Affinamenti Edificio – blocco 2»), perdite di sistema 14 %, temperatura delle celle con NOCT 45 °C, coefficiente −0,37 %/°C; diretta
  ricavata come (GHI − DHI)/cos z. Telai su tetto piano a 10° verso sud con passo tra le file per il sole a 22,5°.
- Firma energetica: minimi quadrati tra consumo mensile e gradi giorno reali del comune (base 20 °C) dalla rotta
  `/api/edifici/gradi-giorno/{istat}` (archivio meteo ERA5 corretto, **non** i dati Arpae personali della fase 2).
- Nessun coefficiente UNI: solo geometria e modelli solari di letteratura aperta.

## Fase B – come si usa (04/11/2026)

### Contenuto

| File | Cosa fa |
|---|---|
| `ortofoto/emilia_romagna.toml`, `toscana.toml`, `italia.toml` | fonti delle ortofoto per il proxy del server: URL, strato, licenza, citazione, scheda, **stato** («confermata», «da confermare», «spenta»), `attiva`, `cache` (copia sì/no), `nei_report`, zoom, riquadro, ritmo. Letti da `fase4-server/servizio/ortofoto.py` (copiati nell'immagine dell'api) |
| `edifici3d/ortofoto_sito.py` | ortofoto AGEA scaricate a mano per un sito → mosaico RGB (l'infrarosso si scarta), web mercator a 50 cm, COG JPEG, PMTiles di tessere JPEG (zoom 14–18), scheda `indice.json` con licenza, citazione e SHA256 delle tessere di partenza |
| server: `servizio/ortofoto.py`, `servizio/orizzonte.py`, `servizio/pvgis.py` | proxy con copia, orizzonte lontano dal Copernicus DEM 90 m, confronto PVGIS (README della fase 4) |
| sito: `ortofoto.html` + `ortofoto.js` | pagina Patrimonio › Ortofoto: mappa, selettore delle fonti che coprono la zona, licenza e citazione sempre sotto la mappa, contorni degli edifici se l'archivio 3D c'è |
| sito: `edifici_calcoli.js` | `partiFacciate`, `irraggiamentoFacciate`, `riepilogoFacciate` (§ 7), `uniscio` (orizzonte vicino + lontano), `obbligoFer` e `htMassimo` (analisi 14), `priorita` (analisi 4) |
| sito: `edificio3d.js` + 9 pagine 3D | passi nuovi Obblighi di legge, Facciate al sole, Confronto con PVGIS, Classifica di priorità; sfondo con le ortofoto; pagine nuove Fotovoltaico › Sole e irradiazione (facciate), › Confronto con PVGIS, › D.Lgs. 199/2021 ed Edificio › Obblighi di legge |

### Ortofoto AGEA per un sito (procedura a mano)

1. Dal GeoPortale AGEA scaricare le tessere **RGB** 2022, 2023 o 2024 del sito (al massimo 20 per richiesta, codice via
   email). Mai l'infrarosso né le foto originali.
2. Sul server, nell'ambiente della fase 10:
   `python -m edifici3d ortofoto-sito --sito ospedale-rimini --anno 2023 --archivio /srv/energia/dati/edifici t1.tif t2.tif …`
3. Il comando scrive `cc-by/ortofoto_siti/<sito>/` (COG, PMTiles, `indice.json`) e aggiorna `cc-by/ortofoto_siti/indice.json`;
   Caddy li serve da `/edifici3d/…` e la pagina Ortofoto li mostra come fonti in più con «AGEA – Ortofoto <anno> RGB,
   ridotta a 50 cm da EuGEnio (CC BY 4.0)».
4. Cancellare le tessere originali scaricate: resta solo la versione a 50 cm.

### Facciate (§ 7)

Ogni lato di ogni corpo si divide in segmenti di al più 4 m e in fasce di al più 3 m; si tolgono le fasce coperte da un
corpo confinante (stesso edificio o vicino) fino alla sua altezza, così la parte che sporge sopra il corpo più basso resta
esposta. Per il centro di ogni pezzo: orizzonte su 72 direzioni (edifici entro 250 m, nel Web Worker) unito all'orizzonte
del terreno (server); poi sole ora per ora sul piano verticale (modello isotropo, cielo visto ridotto dagli ostacoli). Totale
per orientamento: m² esposti, kWh/m² e kWh all'anno, estate (giu–ago), inverno (dic–feb), perdita per ombre. Sulla mappa i
pezzi sono lastre colorate per kWh/m². La somma delle aree esposte coincide con le «pareti esposte» degli indicatori (test).

### Orizzonte lontano

Riuso della fase 3: stessi file `.om` del Copernicus DEM 90 m di Open-Meteo su S3 e stessa lettura a blocchi
(`meteo_storico.s3.FSBlocchi`). Raggio 25 km (`ORIZZONTE_RAGGIO_KM`), passo 90 m, da 250 m in là, curvatura con
rifrazione k = 0,13. Nella pagina il profilo del terreno si unisce a quello dei corpi direzione per direzione (massimo)
per FV, facciate e PVGIS. Prova del 04/11/2026: sotto il Cimone (1.537 m) l'orizzonte arriva a 8,2°; a Rimini 2,1° (verso
i colli a sud-ovest).

### PVGIS

`POST /api/edifici/pvgis` con le aree FV della pagina: per ogni area l'orizzonte medio dei suoi punti (vicino + lontano),
ridotto a 36 direzioni. Due chiamate per area (con `userhorizon` e senza). Prova del 04/11/2026 su Rimini, 10 kWp a 10°
sud: 12.382 kWh/anno senza orizzonte dell'utente; con un orizzonte di 30° in ogni direzione 10.296 (il parametro funziona).

### Obblighi di legge (analisi 14) – formule dalla norma

- **D.Lgs. 8 novembre 2021, n. 199, art. 26 e Allegato III** (testo vigente su Normattiva, letto il 04/11/2026):
  sezione B, punto 3: P = k · S [kW], k = 0,025 per gli edifici esistenti e 0,05 per quelli di nuova costruzione, S =
  superficie in pianta al livello del terreno (proiezione al suolo della sagoma, senza pertinenze): nella pagina S è la
  somma delle aree dei corpi; punto 5: edifici pubblici +10 % sulla potenza e +5 punti sulle quote; punto 1: quote di
  copertura dei consumi previsti (60/60 % nuovi, 40/40 % primo livello, 15 % secondo livello e impianto termico),
  mostrate come promemoria perché servono i consumi di progetto; sezione C, punto 3 (moduli su tetti piani entro la
  balaustra o 30 cm) e punto 2 (impianti a terra esclusi) come avvisi.
- **DPR 412/93, Allegato A**: zona climatica e gradi giorno del comune (`dati/dpr412.json`, già nel sito).
- **DM 26/6/2015 come modificato dal DM 28/10/2025** (GU n. 283 del 5/12/2025, in vigore 180 giorni dopo): Allegato 1,
  Appendice A, § 2.1, **Tabella 10** (H'T massimo per nuova costruzione e demolizione e ricostruzione, per zona e S/V).
  La Tabella 11 (ristrutturazioni di primo livello) dipende dal rapporto tra superfici vetrate e totali: **calcolata dal
  05/11/2026** con la quota scritta dall'utente o stimata (sezione «Affinamenti Edificio – blocco 2»).

### Classifica di priorità (analisi 4)

Per ogni sede (edifici analizzati nella pagina, aggiunti con un clic, o file con una riga per sede) cinque criteri:
consumo per m² (analisi 2), sensibilità al clima per m² e quota del carico di base (analisi 3, firma), costo per m², FV
possibile per m² (analisi 6). Ogni criterio diventa un punteggio 0–100 col rango percentile tra le sedi, poi media pesata
dei criteri disponibili (pesi modificabili; predefiniti 0,35/0,20/0,10/0,20/0,15). Il gas si porta in kWh col PCS
convenzionale 0,03852 GJ/Smc. **Costi**: li inserisce l'utente (bollette o prezzo della sua convenzione); EuGEnio non li
calcola dalle convenzioni perché le formule delle convenzioni elettriche usano il PUN del GME (solo uso interno). La lista
resta nel browser (`localStorage`).

## Fase C – come si usa (04/11/2026)

### Contenuto

| File | Cosa fa |
|---|---|
| `zone/rimini.toml` | prima zona della coda: riquadro (EPSG:7791), tessere di 1 km con il nome delle tavole RER (`32_78504884`), limiti della notte, fonti DSM/LAS/DTM con licenza, stato, motivo e ultima verifica dal vivo |
| `zone/campione.toml` | zona di **prova** sul campione sintetico (tessere di 50 m; `prova = true`, mai nella coda notturna) |
| `edifici3d/lidar.py` | griglie da DSM o LAS (laspy), DSM e DTM ridotti a 1 m in int16 decimetri (COG), falde per corpo: piano, una falda, capanna, padiglione ai minimi quadrati, scelta del più semplice che riduce davvero l'errore, RMSE > 0,5 m o pendenza < 5° → piano, «non presente nel rilievo», salto di altezza segnalato |
| `edifici3d/pipeline.py` | pipeline notturna: tessere con edifici (dai corpi della Fase A), fonte per priorità, versione per tessera (quadro di unione WMS, file, intestazioni HTTP), scaricamento con ripresa, prodotti, cancellazione dei grezzi, stato atomico, limiti, blocco di una sola esecuzione, scelta automatica della zona |
| `edifici3d/campione.py` | rilievo LiDAR **sintetico** (DSM, DTM, un LAS) sull'isolato sintetico, con tetti di forma nota |
| `edifici3d/importa.py` | DXF (ezdxf) e IFC (IfcOpenShell) dell'utente → GeoJSON «eugenio-modello-1» con corpi, altezze e falde |
| `Dockerfile` | container della pipeline (1 CPU, 4 GB; servizio `edifici-lidar` del compose della fase 4, profilo `edifici`) |
| server: `servizio/interno.py` | `GET /api/interno/edifici/stato` e `/api/interno/verifica` con il JWT di Cloudflare Access verificato (README della fase 4) |
| sito: `interno/edifici.html` + `edifici.js` + `interno.css` | pagina di stato nascosta (fuori da menu e mappa del sito, noindex) |
| sito: `edificio3d.js` + 9 pagine 3D | falde LiDAR (tabella, falde a gradini sulla mappa, aree FV sulla falda, report), modello dell'utente aperto solo nel browser |

### Comandi (dalla cartella `fase10-edifici3d`)

```
python -m edifici3d lidar-fonti --zona rimini [--prova]      # fonti, stato e motivo; --prova controlla dal vivo
python -m edifici3d lidar --zona rimini --archivio /srv/energia/dati/edifici --stato /srv/energia/dati/edifici_stato
python -m edifici3d lidar --zona auto …                      # cron delle 3:30: prima zona della coda con tessere da fare
python -m edifici3d lidar … --subito --max-minuti 20 --tessere 32_78504884   # prova fuori finestra
python -m edifici3d lidar … --aggiorna                       # aggiornamento annuale (solo fonti cambiate)
python -m edifici3d lidar-stato --stato /srv/energia/dati/edifici_stato
python -m edifici3d campione --uscita /tmp/campione          # campione sintetico + prodotti della Fase A
python -m edifici3d lidar --zona campione --archivio /tmp/a --stato /tmp/s --radice /tmp/campione --subito
python -m edifici3d importa-modello edificio.ifc --uscita modello.geojson
python -m edifici3d importa-modello pianta.dxf --uscita modello.geojson --posa 0,0=12.5665,44.0600 25,0=12.5668,44.0600
python -m edifici3d importa-modello grande.ifc --uscita modello.geojson --grande     # file molto grandi, solo sul PC
python tests/modelli_sintetici.py prove_modelli                                      # DXF e IFC sintetici di prova
python -m edifici3d demo --uscita ../fase5-sito/sito/dati/edifici3d   # demo del sito, ora con lidar/ dal campione
```

Sul server la pipeline gira nel suo container: `docker compose --profile edifici run --rm edifici-lidar` (comando
predefinito `lidar --zona auto --archivio /dati/edifici --stato /dati/edifici_stato`).

### Regole della pipeline

- **Unità**: tessera della zona (1×1 km a Rimini, angolo in basso a sinistra a km interi in EPSG:7791, stesso nome
  delle tavole RER). Si lavorano solo le tessere toccate da almeno un corpo della Fase A (`prodotti/contesto/`): senza
  i corpi della Fase A la zona ha 0 tessere.
- **Fonti**: una fonte si usa solo con `attiva = true`, un `url` e `licenza_confermata = true`; tra le DSM/LAS attive
  vince la `priorita` più bassa che copre la tessera (§ 4: PNRR → RER → altro). DTM: la prima fonte `dtm` attiva, poi
  i punti di terreno del LAS, poi il DTM della Fase A.
- **Riprendibile e idempotente**: stato riscritto a ogni tessera (file temporaneo e rename); una tessera rimasta «in
  corso» conta come tentativo; una tessera fatta si salta finché la versione della sua fonte non cambia (`--aggiorna`
  dopo `aggiorna_giorni`). Rielaborare scrive sugli stessi file.
- **Limiti** (`[limiti]` del TOML): finestra 03:30–07:00 (fuori non parte, salvo `--subito`), `max_minuti`,
  `min_gb_liberi` (20), `max_gb_notte` (25), `max_mb_tessera`, `max_tentativi` (3, poi «saltata» e segnalata),
  `pausa_url` (la pipeline aspetta finché `/api/salute` dice `previsioni_in_corso` > 0, al più `pausa_max_minuti`).
- **Corpi a cavallo** di due tessere: rielaborati quando arriva la vicina, dai DSM e DTM ridotti già salvati.
- **Prodotti** (archivio della licenza della fonte, serviti da Caddy in `/edifici3d/`): `lidar/dsm/<t>.tif` e
  `lidar/dtm/<t>.tif` (int16 decimetri, solo entro `maschera_m` dagli edifici), `lidar/corpi/<t>.json` (sistema della
  zona), `lidar/falde/<i>_<j>.json` (celle 0,01° in WGS84, lette dalla pagina 3D), `lidar/indice.json` (fonti,
  licenze, attribuzioni e tessere per fonte). Lo **stato** va in `edifici_stato/<zona>.json`, fuori dalla cartella
  pubblica.
- **Grezzi** cancellati a fine tessera (`tieni_grezzi = false`).

### Falde per corpo (§ 5)

Punti del DSM ridotto dentro la sagoma meno 1 m di bordo; altezza mediana = mediana(DSM − DTM); camini e rami tolti con
mediana ± 4 MAD; i modelli si adattano alle quote assolute del DSM (la pendenza del terreno non entra); capanna col
colmo lungo i due assi del rettangolo minimo con cinque posizioni del colmo; padiglione con le quattro falde dello
scheletro del rettangolo. Un modello più complesso vince solo se riduce l'RMSE del 30 % e di 5 cm. Gronda e colmo:
estremi delle falde estrapolati al bordo. Qualità: buona (RMSE ≤ 0,2 m, copertura ≥ 80 %), media (≤ 0,35 m, ≥ 60 %),
bassa. Sul campione: C1 capanna 23,2° sud/nord, C6 capanna 31° est/ovest, C7 padiglione 20,5°, C4 una falda 6° sud,
gli altri piani, C10 «non presente nel rilievo».

### Pagina 3D (sito)

Se c'è `lidar/indice.json` nell'archivio, la pagina legge le celle `lidar/falde/` insieme a quelle del contesto: gronda,
colmo e tetto dei corpi diventano quelli del LiDAR (fonte «LiDAR – …» con la qualità), le falde inclinate si vedono a
gradini (dall'arancio, verso sud, al blu, verso nord), la tabella «Falde dei tetti» dà pendenza, orientamento e
superficie, un'area FV disegnata su una falda ne prende inclinazione e orientamento, il report ha la sezione «Falde dei
tetti». Correggere un corpo fa cadere le sue falde misurate.

### Modelli DXF e IFC dell'utente (§ 5)

Secondo il § 5 della proposta il modello si elabora **solo nel browser, senza salvarlo sul server**: il comando
`importa-modello` gira sul PC dell'utente (o sul server dell'ente) e produce un GeoJSON che la pagina 3D apre con
«Usa il tuo modello» senza inviarlo al server. Le librerie Python (ezdxf, IfcOpenShell) non girano nel browser: dal
04/11/2026 notte c'è anche la lettura nel browser con librerie JavaScript (sotto).
- **DXF**: polilinee chiuse con spessore (base = elevazione), oppure altezza nel nome del layer (`TORRE_H_12.5`);
  facce 3D (3DFACE, MESH, POLYFACE, anche nei blocchi); i solidi ACIS non si leggono (avviso). Unità da `$INSUNITS`
  (o `--unita`). Posa: `--crs EPSG:…` se georeferenziato, oppure `--posa` con due punti noti (controllo della scala), o
  uno più `--rotazione` (azimut dell'asse +Y dal nord vero; la convergenza del meridiano si aggiunge da sola).
- **IFC** (STEP; niente ifcZIP né ifcXML): geometria di tutti gli elementi costruttivi; posa da IfcMapConversion o da
  IfcSite (latitudine, longitudine, nord vero, origine del sito).
- Tetti = facce rivolte in alto che sono la superficie più alta nel loro punto, raggruppate per piano (5°, 0,3 m);
  falde a contatto con la stessa gronda → un corpo; tetti piani a quote diverse → corpi diversi.
- **Dati non fidati**: dimensione ≤ 50 MB, firma del formato, niente collegamenti simbolici, lettura in un processo
  figlio con 2 GB di memoria e 120 s di CPU, tetti su entità (200.000), blocchi annidati (8), triangoli (2 milioni),
  corpi (500), coordinate e altezze fuori scala scartate, testi ripuliti. Nel browser: ≤ 10 MB, formato, coordinate
  in Italia, altezze 0–300 m.

**Lettura nel browser (04/11/2026 notte, decisione di Paolo)**: la pagina del sito **Patrimonio › Importa DXF/IFC**
(`fase5-sito/sito/importa-dxf-ifc.html`) fa lo stesso lavoro senza installare niente e senza mandare il file al server:
`modelli_import.js` è la traduzione in JavaScript di `importa.py` (stessi controlli, stessi tetti, stessa regola dei tetti
e dei corpi, stesso GeoJSON «eugenio-modello-1»), con dxf-parser (DXF), web-ifc (IFC, WebAssembly), Clipper (unioni e
margini dei poligoni, al posto di shapely; giunti ad angolo, così margine +d e −d restituisce gli spigoli come GEOS) e
proj4js (al posto di pyproj). Differenze: nel browser solo DXF di testo e un massimo di 50 MB; MESH letti con un gestore
proprio aggiunto a dxf-parser; web-ifc dà coordinate «Y in alto» già in metri e si riportano a Z in alto. La posa si
sceglie in pagina: dal file (IfcMapConversion, IfcSite), con un sistema di riferimento (RDN2008/ETRS89/WGS84 UTM 32 e 33,
RDN2008 Italia, IGM95, Gauss-Boaga fuso Ovest e Est), con due punti noti (clic sulla pianta e sulla mappa) o un punto e la
rotazione. Oltre 30 MB la pagina consiglia la conversione sul PC (`EuGEnioVisure.exe modello`, Python, Docker).

Correzioni del 04/11/2026 notte a `importa.py`, trovate con i test di parità: i punti di `--posa` si scrivono **nelle
unità del disegno** (prima un DXF in millimetri si posava come se fossero metri); `IfcMapConversion.Scale` con il progetto
in millimetri non si applica due volte (IfcOpenShell dà già metri), e così l'origine di IfcSite; **l'orientamento delle
falde è riferito al nord vero** (prima era sugli assi del disegno: sbagliato con TrueNorth, IfcMapConversion ruotata o
coordinate UTM, dove la convergenza a Rimini è ~2,5°); nell'.exe di PyInstaller si aggiunge la cartella dei plugin di
IfcOpenShell («No geometry mapping registered»). Nuova opzione **`--grande`** (solo sul PC: 500 MB, 2 milioni di entità,
20 milioni di triangoli, 8 GB, 30 minuti); il processo figlio parte con «fork» o, su Windows e nell'.exe, con «spawn»
(`EUGENIO_MP=spawn` per provarlo), con tetto di memoria via Job Object di Windows.

File di prova sintetici: `python tests/modelli_sintetici.py CARTELLA` scrive cinque modelli inventati (DXF in metri con
3DFACE, blocco ruotato, POLYFACE, MESH, polilinee e un 3DSOLID; DXF in EPSG:7791; DXF in millimetri; IFC con IfcSite e
TrueNorth; IFC in millimetri con IfcMapConversion, arredo e spazio da escludere). Test: `tests/test_importa_parita.py`
(Python e node, 7) e `tests/test_importa_browser.py` (Chromium con Playwright, 5).

### Verifiche dal vivo del 04/11/2026 (dal container di sviluppo, senza aggirare blocchi)

- **Quadro di unione LiDAR RER 2023-24** (WMS `metadati_raster`, strato `QU_LiDAR_RER2023_2024`): raggiungibile;
  GetFeatureInfo dà la tavola (`32_78504884`) e le date di volo (Rimini 25–27/03/2023). Scheda: CC BY 4.0, «No
  download»: DSM e LAS **solo su richiesta** → fonti `rer_dsm` e `rer_las` in attesa. RER2025/26 e RER2022: nessuna
  tavola sui punti provati in Romagna.
- **DTM 0,5 m RER 2023-24**: WCS 1.0.0 pubblico (`wcs/dtmrer2023_24`, copertura `1`), GeoTIFF float32 EPSG:7791, CC BY
  4.0 dalla scheda → fonte `rer_dtm05` **attiva** (chiesta a 1 m).
- **DTM 5 m**: il WCS pubblico è `wcs/dtm5x5` (copertura `DTM5X5_RDN32_RMD`); quello del TOML della Fase A (`wcs/dtm5`)
  dava 401: TOML della Fase A corretto, `fonti.url_wcs` passa al WCS 1.0.0 (il 2.0.1 dell'ArcGIS regionale risponde in
  multipart). Prova dal vivo: 200 image/tiff.
- **DSM della costa da LiDAR 2019** (ImageServer pubblico `DSMCosta_Lidar2019`, 1 m): copre Rimini e la costa e
  risponde, ma il servizio non indica la licenza e la scheda INSPIRE non si apre (certificato scaduto): fonte
  `rer_dsm_costa_2019` in attesa, da chiedere all'Archivio Cartografico insieme a DSM e LAS.
- **LiDAR PNRR (portale PST/SIM del MASE)**: HTTP 500/503 (offline fino al 7/11/2026), nessuna interfaccia automatica:
  fonte `pnrr_dsm` in attesa.

## Fase E – come si usa (04/11/2026)

### Contenuto

| File | Cosa fa |
|---|---|
| `fonti/regioni.toml` | fonti per regione e provincia autonoma (edifici con altezze, DTM, DSM/LiDAR, ortofoto) e nazionali: licenza, stato («attiva», «in attesa», «non disponibile»), scheda, servizio, esito della prova dal vivo, data della verifica, motivo, file di EuGEnio che la usano |
| `edifici3d/regioni.py` | lettura e controllo del file (regola: «attiva» solo con licenza compatibile scritta in una scheda ufficiale e prova dal vivo), riepilogo, tabella, prova dal vivo degli `url_prova` |
| `ortofoto/bolzano.toml`, `ortofoto/trento.toml` | ortofoto nuove per il proxy del server: Bolzano 2023 e Trento 2015 (20 cm, CC BY 4.0, GetMap provato) |
| `edifici3d/zornade.py` | altezze di Zornade (estratto consegnato, mai l'API) → corpi ODbL, confronto con le altezze CC BY, prodotti solo in `odbl/<zona>/prodotti/zornade/` con `LEGGIMI_ODbL.txt`; campione sintetico |
| `edifici3d/analisi.py` | aggancio pubblico alle analisi 5 e 7–13: elenco, forma di richiesta e risultato, caricamento facoltativo del modulo privato, stato; server: `servizio/analisi.py` (`/api/analisi/…`); sito: `analisi_uni.js` |
| `uni_privato/` | **modulo privato** (in `.gitignore`, fuori dallo zip pubblico e dalle immagini Docker): solo struttura, tabelle vuote da compilare a mano, test che saltano finché i dati non ci sono; si consegna nello zip a parte `eugenio_uni_privato_<data>.zip` |

### Comandi (dalla cartella `fase10-edifici3d`)

```
python -m edifici3d regioni                     # riepilogo per regione (esce con 1 se il file viola le regole)
python -m edifici3d regioni --prova             # ricontrolla dal vivo gli url_prova (dal server di Milano)
python -m edifici3d regioni --markdown          # tabella per questo README
python -m edifici3d zornade-campione --uscita /tmp/z.geojson
python -m edifici3d zornade-altezze --file estratto.gpkg --archivio /srv/energia/dati/edifici \
       [--confronta-con /srv/energia/dati/edifici/cc-by/er/prodotti/contesto] [--mappa altezza=<colonna>]
python -m pytest tests                          # test pubblici
python -m pytest uni_privato/tests              # test del modulo privato (solo dove c'è)
```

### Fonti per regione (verifica del 04/11/2026)

Metodo: catalogo nazionale RNDT (CSW di geodati.gov.it, schede ISO lette per licenza e collegamenti), siti delle
Regioni e prove dal vivo dal container di sviluppo (GetCapabilities, GetMap in EPSG:3857, DescribeFeatureType, query
ArcGIS, primo kB dei download), **senza aggirare blocchi**: dove un portale chiude la connessione, risponde 502/503 o
chiede un captcha (Marche), la voce resta «in attesa» con il motivo e va riprovata dal server con `regioni --prova`.
Licenze considerate compatibili con la CC BY 4.0 di EuGEnio: CC BY 4.0, CC0, IODL 2.0, CC BY 3.0/2.5. Escluse:
non commerciali, condivisione allo stesso modo, «tutti i diritti riservati», ortofoto AGEA concesse alle Regioni, «dato
pubblico» senza licenza.

| Regione | Edifici (altezze) | DTM | DSM / LiDAR | Ortofoto |
|---|---|---|---|---|
| Piemonte | in attesa | in attesa | in attesa | in attesa |
| Valle d'Aosta | in attesa | in attesa | in attesa | — |
| Lombardia | **attiva** | **attiva** | — | — |
| Provincia autonoma di Bolzano | — | **attiva** | **attiva** | **attiva** |
| Provincia autonoma di Trento | **attiva** | **attiva** | **attiva** | **attiva** |
| Veneto | **attiva** | in attesa | — | — |
| Friuli Venezia Giulia | **attiva** | in attesa | in attesa | in attesa |
| Liguria | **attiva** | **attiva** | — | — |
| Emilia-Romagna | **attiva** | **attiva** | in attesa | **attiva** |
| Toscana | in attesa | in attesa | in attesa | **attiva** |
| Umbria | in attesa | in attesa | — | — |
| Marche | in attesa | in attesa | — | in attesa |
| Lazio | in attesa | in attesa | — | — |
| Abruzzo | in attesa | in attesa | — | in attesa |
| Molise | in attesa | in attesa | — | in attesa |
| Campania | in attesa | in attesa | — | in attesa |
| Puglia | in attesa | in attesa | — | in attesa |
| Basilicata | in attesa | in attesa | in attesa | in attesa |
| Calabria | in attesa | in attesa | — | in attesa |
| Sicilia | in attesa | in attesa | in attesa | in attesa |
| Sardegna | in attesa | in attesa | in attesa | — |

Note principali:
- **Accese davvero** in EuGEnio con questa fase: le ortofoto di **Bolzano 2023** e **Trento 2015** (`ortofoto/`). Le altre
  fonti «attive» (DBGT Lombardia, edifici FVG con `ALTEZZA` e `QUOTA_GRONDA`, CTR 3D Liguria, Edifici P.A.T. 3D, DTM e
  DSM di Bolzano e Trento, DTM Lombardia e Liguria, sagome del Veneto) hanno licenza e servizio verificati ma aspettano
  l'**adattatore del formato** (oggi c'è solo quello delle UVL dell'ER) o il TOML di una zona in `zone/`.
- **Emilia-Romagna**: nel RNDT sono comparse le schede «DSM First/Last 0,5 m RER 2023-24» (23/10/2026, CC BY 4.0), ma il
  WCS `dsmfirst2023_24` risponde 401: `rer_dsm` resta in attesa. La scheda del **DSM della costa 2019** ora riporta CC BY
  4.0 (`r_emiro:2022-02-08T110323`): in `zone/rimini.toml` la licenza è confermata ma la fonte resta **spenta**, perché
  copre solo la costa e la pipeline non sa ancora limitare una fonte alla sua copertura (con `versione = "fissa"` ogni
  tessera dell'entroterra risulterebbe coperta).
- **Friuli Venezia Giulia**: LiDAR 2017-2020 (DSM, DTM 0,5 m, LAS) scaricabile da Eagle.fvg ma senza licenza scritta:
  da chiedere. **Sicilia**: il SITR dichiara CC BY 4.0 per i dati scaricabili senza costi di cessione (dal 2021).
  **Marche**: «dove non diversamente specificato» CC BY 4.0, servizi dietro captcha.
- Fonti nazionali nel blocco `[nazionale]`: PST e LiDAR PNRR (in attesa), aggregati della Protezione Civile (CC BY),
  OpenStreetMap e Zornade (ODbL, archivio separato), GlobalBuildingAtlas (escluso), Sentinel-2 e AGEA 2022-24.

### Altezze di Zornade (archivio ODbL)

- Il blocco `buildings` dell'API di Zornade non ha altezze (solo conteggi e impronte OSM) e le altezze LiDAR annunciate per
  novembre non sono ancora uscite: il lettore lavora su un **estratto consegnato** (GeoPackage, GeoJSON, Shapefile,
  FlatGeobuf, Parquet). Colonne riconosciute per sinonimi (`height_lidar`, `height`, `altezza`, `eave_height`,
  `height_source`, `survey_date`…), sovrascrivibili con `--mappa`.
- Scarti: geometria assente o sotto 10 m², altezza assente o fuori 2–300 m, **altezze da GlobalBuildingAtlas o con
  licenza non commerciale** (Zornade ha spiegato che i 20,5 milioni del suo sito sono un residuo di GBA, CC BY-NC).
- **Licenze** (decisione del § 2 e termini Zornade allineati in fase 4 e 7): tutto ciò che contiene dati di Zornade va
  solo in `odbl/<zona>/prodotti/zornade/` (`prepara` rifiuta altre cartelle e corpi con un'altra licenza); un corpo CC BY
  che prende l'altezza da Zornade (catena del § 4, solo per altezze deboli o assenti) diventa ODbL e porta in `extra` la
  licenza della sagoma originale. Accanto ai prodotti `LEGGIMI_ODbL.txt`: attribuzioni («© OpenStreetMap contributors
  (ODbL 1.0)», «Dati elaborati da Zornade» con link), condivisione allo stesso modo, divieto di re-identificazione.
- **Confronto** con le altezze CC BY (corpi della Fase A): abbinamento per sovrapposizione (IoU ≥ 0,5), `confronto.csv`
  per corpo (database derivato: ODbL) e `confronto.json` con le statistiche (differenza media e mediana, scarto medio,
  RMSE, quota entro 1 e 3 m: opera prodotta, citabile con le due attribuzioni). Sul campione sintetico: 8 corpi
  abbinati su 10, scarto medio 0,5 m, RMSE 0,6 m.
- Nessuna chiamata all'API di Zornade in questo modulo (controllato da un test).

### Analisi 5 e 7–13 e modulo privato

- Codice pubblico: `edifici3d/analisi.py` con l'elenco delle analisi (pagina del sito, dati, uscite, avvertenze), la forma
  della richiesta (`edificio.corpi`, `clima`, `ipotesi`, `opzioni`) e del risultato (`valori`, `tabelle`, `avvisi`,
  `fonti`: le altre chiavi si scartano) e il caricamento facoltativo del modulo privato (variabile `UNI_PRIVATO`, poi
  `/dati/uni_privato`, poi `fase10-edifici3d/uni_privato`), con controllo della versione dell'interfaccia (1).
- **Senza modulo**, o con le tabelle ancora da compilare, le pagine Fabbisogno, Comunità energetiche, Facciate e tetti,
  Pompe di calore e solare termico, Clima che cambia e Prefattibilità LEED scrivono «analisi non disponibile in questa
  installazione» (anche senza JavaScript e sui mirror).
- **Modulo privato** `uni_privato/` (fuori da git, dallo zip pubblico e dalle immagini Docker, grazie al `.dockerignore`
  nuovo): un file per analisi con i passi descritti a parole e segnaposto `da_scrivere(...)`, 16 tabelle TOML **vuote**
  (`compilata = false`) da riempire a mano, `PRONTA = False`, test di struttura e test di calcolo che saltano. Nessun
  testo, prospetto, coefficiente o formula di norme vi è stato scritto. Istruzioni in `uni_privato/LEGGIMI.md`.
- Le analisi 7, 9 e 13 non richiedono coefficienti UNI: **dal 05/11/2026 sono nel codice pubblico** (`pubblica = True` in
  `edifici3d/analisi.py`, sempre disponibili, anche sui mirror; tolte dal modulo privato con le loro tabelle vuote):
  - **13, Clima che cambia** (`edificio-clima.html`, `analisi_pubbliche.js`): gradi giorno per stagione dal clima dal 1940
    (fase 9), tendenza ai minimi quadrati, Theil–Sen e Mann–Kendall, estrapolazione al 2030/2040/2050 con l'intervallo al
    95 % della previsione, consumo atteso con la firma energetica (12 × base + pendenza × GG);
  - **7, Comunità energetiche** (`edificio-cer.html`): CSV orario per sede con la cabina primaria scritta dall'utente;
    energia condivisa = minimo orario tra immissioni e prelievi per cabina (D.Lgs. 199/2021 artt. 31–32, DM MASE 414/2023),
    ripartizione di esempio per sede; nessun prezzo né incentivo (dipendono dai prezzi GME). **Perimetri delle cabine
    primarie**: nessuna fonte con licenza compatibile trovata il 05/11/2026 (solo quelli del GSE, CC BY-NC-SA 3.0 IT, non
    usati): il codice della cabina lo scrive l'utente;
  - **9, Cielo visibile** (colonna «Cielo visibile» della tabella delle facciate, `riepilogoFacciate`) e pagina
    **Prefattibilità LEED** (`fv-leed.html`): temi del sistema LEED descritti con parole nostre e collegati alle pagine di
    EuGEnio che danno i dati; **nessun testo, tabella o soglia LEED riprodotti** (protetti dall'USGBC), nessun punteggio.

## Edifici fuori dall'Emilia-Romagna – come si usa (05/11/2026)

### Contenuto

| File | Cosa fa |
|---|---|
| `edifici3d/regionali.py` | adattatori dei DB topografici → corpi (stesso `modello.Corpo` della Fase A): **Lombardia** DBGT 020101 (`UN_VOL_AV`, `UN_VOL_QE`, z della base, `CEDIUV` come edificio), **FVG** Edificato CTRN (`ALTEZZA`, `QUOTA_PIEDE`, `QUOTA_GRONDA`), **Liguria** CTR 3D (z di gronda − DTM); controllo degli attributi e della coerenza delle quote; campione dal vivo a pagine (ArcGIS REST o WFS 2.0.0) |
| `fonti/lombardia.toml`, `fonti/friuli_venezia_giulia.toml`, `fonti/liguria.toml` | fonti delle tre zone (servizio, strato, sistema, licenza, attribuzione), come `emilia_romagna.toml` |
| `edifici3d/coperture.py` | maschera della copertura di una fonte da una sola immagine a passo grosso (`lidar-copertura`) e indice dei file di una fonte divisa in file irregolari, dalle sole intestazioni (`lidar-indice`) |
| `zone/bolzano.toml`, `zone/trento.toml` | zone LiDAR fuori ER: Bolzano DSM/DTM 0,5 m (WCS, CC0, chiesti a 1 m) con il DTM 2,5 m per i vuoti; Trento DSM/DTM 1 m 2006-09 (1410 file per modello, indice in `zone/coperture/`) |
| `zone/coperture/` | `rimini_rer_dsm_costa_2019.geojson` (fascia costiera coperta dal DSM 2019, 27,8 km²), `trento_pat_lidar_2009.json` (riquadri dei file del LiDAR PAT) |
| `tests/dati/*_campione.geojson` | 8 volumi DBGT di Milano, 6 elementi CTRN del foglio 110, 5 edifici CTR della Liguria, scaricati dal vivo il 05/11/2026 (CC BY 4.0, fonte nel file) |

### Comandi (dalla cartella `fase10-edifici3d`; `--zona` va prima del comando)

```
python -m edifici3d --zona lombardia regionale-campione --riquadro 514600 5034400 514900 5034700 --max 500 --uscita lom.geojson
python -m edifici3d --zona friuli_venezia_giulia regionale-campione --strato EDIFICI:EDIFICATO_CTRN_ED1_110 --riquadro … --uscita fvg.geojson
python -m edifici3d --zona liguria regionale-campione --riquadro 1388500 4858000 1388800 4858300 --uscita lig.geojson
python -m edifici3d --zona lombardia controlla-regione --file lom.geojson          # campi, riempimento, coerenza delle quote
python -m edifici3d --zona lombardia prepara-regione --file lom.geojson --archivio /srv/energia/dati/edifici [--dtm dtm.tif]
python -m edifici3d --zona liguria prepara-regione --file lig.geojson --dtm dtm_7791.tif --archivio …   # il DTM serve
python -m edifici3d lidar-copertura --zona rimini --fonte rer_dsm_costa_2019 --passo 50   # rifà la maschera (una richiesta)
python -m edifici3d lidar-indice --zona trento --fonte pat_dsm_2009 [--max 200]          # indice dei file (riprende da dove era)
```

`prepara-regione` scrive in `<archivio>/cc-by/<lom|fvg|lig>/prodotti/` gli stessi prodotti di `prepara` (corpi.pmtiles,
contesto/, indice.json con il sistema della zona e il resoconto dell'adattatore; con `--dtm` anche dtm_cog.tif e
terreno.pmtiles). Il campione serve per le prove e per una prima zona piccola; per una provincia intera si scarica il file
ufficiale della Regione (GeoPackage o Shapefile, URL da scrivere nel TOML) o il servizio a pezzi dal server.

### Formati verificati dal vivo (05/11/2026, piccoli campioni, nessun blocco aggirato)

- **Lombardia**: GeoJSON dell'ArcGIS sempre in WGS84 con le z (EPSG:4979); 60 volumi a Milano: `UN_VOL_QE − z =
  UN_VOL_AV` in 51, nei 9 con porzione «03» la base sta 3,5 m sotto terra → terreno = `UN_VOL_QE − UN_VOL_AV` (o DTM).
  `UN_VOL_AV` è alla sommità del volume: usata come gronda, «gronda o colmo da verificare» come le UVL dell'ER.
- **FVG**: 44 strati WFS, uno per foglio CTRN; EPSG:6708 (asse nord prima: il riquadro della richiesta si scrive in forma
  breve `x0,y0,x1,y1,EPSG:6708`); `QUOTA_GRONDA − QUOTA_PIEDE = ALTEZZA` in 22 su 22; nessun codice d'edificio.
- **Liguria**: nessun campo d'altezza, z costante per poligono (399 su 400) = quota di gronda; DTM 2023 via WCS
  (`M2056__L6952`, 5 m, EPSG:3003; `riproietta_dtm` lo porta nel sistema della zona). Scartati sotterranei, aggetti, ruderi.
- **Edifici P.A.T. 3D (Trento)**: zip di 108 MB, non letto a distanza: adattatore **ancora da scrivere** dopo un download.

### Copertura delle fonti nella pipeline

`[fonti.<id>.copertura]` nel TOML della zona: `riquadri` (sistema della zona), `maschera` (GeoJSON in `zone/coperture/`),
`minima` (quota dell'area degli edifici della tessera che deve cadere dentro, 0,95 se non detto). Fuori copertura la fonte
«non copre» la tessera (come una tavola assente dal quadro di unione) e vince la successiva. Le fonti con `indice` danno
la copertura dai riquadri dei file. **DSM della costa 2019** (Rimini): acceso, con `minima = 0.10` perché la fascia larga
1–1,5 km taglia le tessere in diagonale: i corpi della tessera fuori dalla fascia risultano «non presente nel rilievo»;
priorità più bassa delle fonti RER 2023-24, che vinceranno quando arrivano (con `--aggiorna`). Il DTM si compone: se la
prima fonte lascia vuoti (Bolzano 0,5 m solo nelle aree insediative) si riempiono con le successive (2,5 m), poi DTM della
Fase A. Una zona senza i corpi della Fase A resta «in attesa» e la scelta automatica (`--zona auto`) la salta.

## Affinamenti Edificio – blocco 2 (05/11/2026)

| Tema | Dove | Cosa fa |
|---|---|---|
| Tabella 11 del DM requisiti minimi | `edifici_calcoli.js` (`HT_TAB11`, `htMassimoPrimoLivello`, `quotaVetrataStimata`), pagine 3D › Obblighi di legge | H'T massimo per le ristrutturazioni importanti di primo livello, per zona e quota EX ANTE di superfici vetrate sul totale dei componenti dell'involucro (DM 26/6/2015, All. 1, App. A, § 2.1, Tab. 11, nel testo del DM 28/10/2025, GU n. 283 del 5/12/2025, pp. 39–40, letta il 05/11/2026). La norma dà 20 colonne (9 %…100 %): tra due colonne EuGEnio interpola in modo lineare (scelta dichiarata), sotto il 9 % vale la prima. Quota scritta dall'utente o **stimata** (finestre/pareti tipiche per uso, valori assunti da EuGEnio, × pareti esposte ÷ superficie disperdente), segnata come stima |
| Trasposizione di Perez | `edifici_calcoli.js` (`perez`, `trasponi` con `modello: "perez"` predefinito) | Perez et al. 1990, coefficienti «allsitescomposite1990» come pvlib, massa d'aria di Kasten e Young; circumsolare persa quando il sole è dietro l'orizzonte del punto, isotropa e fascia dell'orizzonte ridotte dal fattore di vista del cielo; FV e facciate; il report dice «trasposizione di Perez (1990)» |
| Colonne `visura_…` | `edifici_calcoli.js` (`daVisura`, `mappaVisura`, `leggiVisura`), `edificio3d.js`, `valori_sedi.js` | precedenza file → visura → stima nelle pagine dell'edificio (piani fuori terra e interrati, superficie catastale, uso); in «Valori per sede» le colonne `visura_…` non diventano valori da disegnare e la superficie catastale della visura (segnata «v») è una base dei consumi al m² se il file non ha la sua |
| Patrimonio → Modelli 3D | `patrimonio.js` (pulsante «Apri in Modelli 3D»), `edificio3d.js` (`?sede=locale`) | la sede passa nella memoria della scheda (sessionStorage, mai al server): la pagina 3D apre l'edificio dell'archivio che contiene il punto (o il più vicino entro 30 m), mette le colonne facoltative nei campi e le visure nella precedenza |
| Posa sulla sagoma | `edifici_calcoli.js` (`posaDaSagoma`), `importa_modello.js`, `importa-dxf-ifc.html` | quinta posa: clic sulla sagoma di un edificio dell'archivio; rotazione dai rettangoli minimi (quattro candidati a 90°), baricentri, scelta per sovrapposizione (IoU su griglia 80×80); nessuna scala, rapporto delle aree come controllo; la pagina usa poi la posa «due punti» |
| Corpi dal solo LiDAR | `edifici3d/lidar_corpi.py`, `Pipeline.corpi_lidar`, comando `lidar-corpi` | per le zone senza sagome (§ 7): h = DSM − DTM ≥ 2,5 m, chiome tolte con la ruvidezza 3×3 (> 0,8 m), celle vicine unite se |Δh| < 1,25 m, corpi sotto 20 m² scartati, buchi sotto 25 m² chiusi, corpi che si toccano = un edificio; scrive i prodotti della Fase A, poi la pipeline stima le falde |
| Ombre degli alberi | `lidar_corpi.alberi`, `Pipeline._alberi`, `edificio3d.js` | chiome del DSM entro 50 m dagli edifici → quadrati di 2 m in `lidar/alberi/<cella>.json` (per tessera); nella pagina 3D sono ostacoli dell'orizzonte (FV e facciate), fanno ombra al suolo e si vedono in verde |

**Confronto con PVGIS (05/11/2026, dal vivo)**: PVGIS 5.3 `seriescalc`, SARAH3, anno 2020, Rimini (44,06; 12,57), sud;
irradiazione sul piano dai GHI e DHI orizzontali di PVGIS con la trasposizione di EuGEnio, contro il piano inclinato di
PVGIS (con il suo orizzonte del terreno, trascurabile a Rimini):

| Piano | Isotropa | Perez | PVGIS | Scarto isotropa | Scarto Perez |
|---|---|---|---|---|---|
| 30° sud | 1.725 kWh/m² | 1.810 kWh/m² | 1.795 kWh/m² | −3,9 % | +0,8 % |
| 90° sud (facciata) | 1.150 kWh/m² | 1.249 kWh/m² | 1.242 kWh/m² | −7,4 % | +0,5 % |

Mese per mese la Perez resta entro pochi kWh/m² da PVGIS. Il test `test_perez_contro_pvgis` (fase 5) rifà il confronto
sul giorno 15 di ogni mese (estratto in `fase5-sito/tests/pvgis_rimini_2020_giorno15.json`, © Unione europea, riuso
con citazione) e `test_perez_uguale_a_pvlib` controlla che il codice JS dia gli stessi valori di pvlib (scarto < 1e-6
W/m²; si salta se pvlib non c'è).

**Corpi dal solo LiDAR sul campione sintetico**: 7 corpi in 5 edifici; C3, C6, C7, C9 ritrovati con IoU ≥ 0,97; C1, C2
e C8 (10–13 m, a contatto) diventano un corpo solo perché le altezze ai confini differiscono meno di 1,25 m (limite del
metodo: si dividono a mano nella pagina 3D); C10, demolito, non compare; nessun corpo sugli alberi.

## Modelli 3D in due tempi e allineamento con le ortofoto (05/11/2026)

- La pagina Modelli 3D si apre in 2D (ricerca, clic sull'edificio) e genera il 3D a richiesta; per ogni corpo usa la fonte
  più affidabile tra gli archivi elencati in **`/edifici3d/archivi.json`** (servito da Caddy dalla cartella degli edifici):
  ```json
  {"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"},
               {"base": "/edifici3d/cc-by/bz/prodotti/", "nome": "Corpi dal LiDAR di Bolzano"},
               {"base": "/edifici3d/odbl/er/prodotti/", "nome": "OpenStreetMap"}]}
  ```
  in ordine di affidabilità (se il file manca vale solo il DBTR dell'ER). I corpi di un archivio meno affidabile che cadono
  dentro quelli di uno migliore non si usano; le falde LiDAR del primo archivio sostituiscono le altezze del DB. Il file si
  scrive a mano quando c'è più di un archivio (da far scrivere a `prepara`/`prepara-regione`: in DA_FARE).
- **Edifici «storti»**: la demo sintetica (`sintetico.py`) ha rettangoli allineati alla griglia UTM 32N posati vicino a
  Rimini, senza legame con edifici veri: sopra l'ortofoto sembravano ruotati (convergenza della griglia ~2,5° e strade vere a
  ~45°). La catena dei dati veri è corretta: le UVL del WMS DBTR e le sagome OSM vere (4326 → 7791 → `feature_da_corpi` →
  PMTiles → pagina) coincidono con l'ortofoto RER 2023-24 entro circa 1 m. Ora la demo non va mai sopra una foto vera.
- Il WMS della cartografia catastale dell'Agenzia delle Entrate (CC BY 4.0) non offre EPSG:3857 né CORS: **fatto nella
  seconda pubblicazione del 05/11** (sezione qui sotto), con la riproiezione nel proxy del server.

## Strati sopra le ortofoto, archivio di prova e strumenti per il servizio vero (05/11/2026, seconda pubblicazione)

- **Strati** (`ortofoto/strati/*.toml`, letti da `fase4-server/servizio/strati.py`, rotte `/api/ortofoto/strati…`; nelle
  pagine con `fase5-sito/sito/strati_gl.js`):
  - `catasto.toml`: **particelle catastali** dell'Agenzia delle Entrate (WMS INSPIRE, CC BY 4.0). Il servizio offre solo
    sistemi geografici e UTM: il proxy chiede il riquadro in EPSG:4258 (assi lat,lon) e **riproietta riga per riga** in
    web mercator (esatto al pixel); chiede un blocco di 2×2 tessere e tiene quella in alto a destra (la scritta del servizio
    cade fuori), toglie il riempimento beige e lascia linee e numeri in giallo. Provato dal vivo il 05/11 sul centro di
    Rimini (zoom 17 e 18): confini allineati all'ortofoto RER e al DBTR. Non copre Trento, Bolzano e il catasto tavolare;
  - `edifici.toml`: **contorni degli edifici**, per regione: Emilia-Romagna dal WMS DBTR (strato `EDI_Edificio`, che si
    vede da 1:14.174 = zoom 16; l'UVL solo da zoom 19), fuori ER **OpenStreetMap** via Overpass (ODbL, tessere z16 in
    GeoJSON). Un test controlla che ogni strato regionale corrisponda a una fonte «edifici» **attiva** in
    `fonti/regioni.toml`. Overpass **non risponde dal container** (connessione chiusa): codice provato con risposte
    simulate, da provare dal server. Lombardia (ArcGIS `export` del DBGT) provata: immagine vuota alle scale utili, non
    accesa.
- **`osm-campione`** (`edifici3d/osm_campione.py`): archivio di prova **ODbL** di un quartiere con **una sola** chiamata
  all'API di OpenStreetMap (riquadro al più ~2×2 km) e un GetCoverage del DTM 5 m; altezze da `height` o
  `building:levels` × 3 m, altrimenti **stima dichiarata** (9 m). Il 05/11 per il centro di Rimini (12,5600–12,5735 E,
  44,0555–44,0640 N): 532 edifici, 528 corpi, 27 tessere, 1,3 MB di prodotti, 12 s. Pacchetto da mettere sul server:
  `edifici_rimini_prova_2026-11-05.tar.gz` (con `archivi.json`, `LICENZE.txt`, `LEGGIMI_ARCHIVIO_PROVA.txt`).
- **`dtm-wcs`** (`edifici3d/dtm_wcs.py`): DTM 5×5 m dal WCS pubblico `dtm5x5` a blocchi di 10 km (ripresa, mosaico in un
  GeoTIFF deflate); provato il 05/11: un blocco di 10×10 km = 2000×2000 celle, 15 MB, 35 s.

### Cosa manca per passare dalla demo al servizio vero

**Aggiornamento del 07/11/2026**: passi 1–6 pronti per Rimini (estrazione arrivata il 05/11, archivio provato nel
container, DTM dal quadrante SE, comandi nella procedura F di `AGGIORNAMENTO_2026-11-07.md`); restano la copia sul server
(Paolo), le prove del passo 8 e gli altri comuni (19 scaricati il 06/11, un archivio per comune). Testo originale:

Oggi sul server non c'è nessun archivio di edifici: Modelli 3D cerca il punto e mostra ortofoto e strati, ma il 3D si genera
solo sulla demo sintetica. Con l'**archivio di prova OSM** del centro di Rimini (passo D13 di `AGGIORNAMENTO_2026-11-05.md`)
il flusso vero funziona già lì (ricerca, punto trascinabile, «Genera il 3D», immagine e report), con altezze stimate. Il
servizio vero in Emilia-Romagna usa le **unità volumetriche del DBTR** (altezza per corpo, CC BY 4.0) e il **DTM 5 m**.

| # | Passo | Chi | Tempo e spazio (stime) |
|---|---|---|---|
| 1 | **Prenotare l'estrazione del DBTR** dal Geoportale: pagina «Download DB Topografico» (`https://geoportale.regione.emilia-romagna.it/download-data/download-dbtopografico`), area = comune o provincia di Rimini (o tutta la regione), classe **Unità volumetrica (UVL)** (facoltativo: Edificio), formato **GeoPackage**, sistema **RDN2008 / UTM 32N (EPSG:7791)**. Il modulo ha il reCAPTCHA e la consegna è per email: l'agente non può farlo (e non deve aggirarlo). Il WFS del DBTR non è un'alternativa (401 il 03/11, 404 il 05/11/2026). | **Paolo** | **fatto** (05–06/11: Rimini e altri 18 comuni; Geoportale solo per comune). 5 minuti + attesa dell'email; GeoPackage stimato 50–150 MB per la provincia di Rimini, 1–3 GB per la regione (da verificare sul file) |
| 2 | Copiare il GeoPackage sul server: `scp UVL_rimini.gpkg eugenio:/srv/energia/dati/edifici/cc-by/er/grezzi/` (creare prima la cartella con `mkdir -p`). In alternativa metterlo in `C:\Users\ingpa\Documents\claude\pj\statocritico\edifici\`: l'agente lo legge dal PC, prepara l'archivio nel suo ambiente e ti restituisce un tar come quello di prova. | **Paolo** (o agente dal PC) | **fatto nel container** (07/11); sul server con F (copia del tar degli archivi o del GeoPackage). minuti |
| 3 | **DTM 5 m** della zona dal WCS pubblico, sul server: `docker compose --profile edifici run --rm edifici-lidar dtm-wcs --riquadro 770000 4860000 800000 4895000 --uscita /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif` (comune di Rimini e dintorni, 30×35 km, 12 blocchi). Per tutta la regione: i quattro quadranti TIFF della scheda del DTM (~4,9 GB) in `cc-by/er/grezzi/`. | **Paolo** (comando pronto) | **fatto** (07/11): quadrante SE in zip (`wget -c`, F), letto a finestra; il WCS resta come riserva. ~7 minuti e ~180 MB per 30×35 km; ~1 h per i quadranti |
| 4 | **Controllo degli attributi**: `docker compose --profile edifici run --rm edifici-lidar controlla-uvl --gpkg /dati/edifici/cc-by/er/grezzi/UVL_rimini.gpkg` (rapporto su H_uvl, B_uvl, gronda/colmo, piani). | Paolo; l'agente legge il rapporto | **fatto** (07/11, rapporto nel README: H_UVL, quote, colmi). 1–2 minuti |
| 5 | **`prepara`**: `docker compose --profile edifici run --rm edifici-lidar prepara --gpkg /dati/edifici/cc-by/er/grezzi/UVL_rimini.gpkg --dtm /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif --archivio /dati/edifici --riquadro 770000 4860000 800000 4895000`. Scrive `cc-by/er/prodotti/` (corpi.pmtiles, contesto/, indice.json; dal 07/11/2026 niente dtm_cog.tif e terreno.pmtiles: terreno dal server). | Paolo | **fatto** (07/11, `prepara --comune rimini`: 40.518 corpi, 301 s, 106 MB). provincia di Rimini: 5–20 minuti, 50–200 MB; regione intera a zone (una provincia per volta), qualche ora e 1–3 GB |
| 6 | **`archivi.json`** in `/srv/energia/dati/edifici/`: il DBTR **prima** dell'archivio di prova OSM (o l'archivio di prova tolto): `{"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}, {"base": "/edifici3d/odbl/rimini-prova/prodotti/", "nome": "OpenStreetMap – rimini-prova (archivio di prova)"}]}`. | Paolo (testo pronto) | **fatto** (07/11, comando `archivi-json`, archivio di prova tolto con `--senza-prova`). 1 minuto |
| 7 | **Caddy**: niente da fare. `/edifici3d/` è già servito dalla cartella `CARTELLA_EDIFICI` (sola lettura, Range, CORS, cache di un giorno); nessun riavvio. | — | — |
| 8 | **Prove**: Modelli 3D → «via Gambalunga 27, Rimini» → l'edificio UVL del punto (trascinare il punto se serve) → «Genera il 3D» (fonte «DB topografico regionale»); Ortofoto → «contorni dell'archivio 3D» accesi. | Paolo; l'agente corregge quello che non va | 10 minuti |
| 9 | **Dopo, da sola, la pipeline LiDAR** (cron delle 3:30, `edifici-lidar`, zona Rimini): trovati i corpi della Fase A, lavora le tessere coperte dal **DSM della costa 2019** (falde per corpo dal LiDAR, CC BY 4.0, fascia costiera); per il resto resta «in attesa» finché non arrivano DSM/LAS RER 2023-24 (email all'Archivio Cartografico) o il LiDAR PNRR. La pagina interna `/interno/edifici.html` passa da «In attesa: … 0 corpi della Fase A» a «Zona in corso». | automatico; l'agente legge lo stato | notti successive |

L'agente (Claude) ha già fatto: proxy di particelle e contorni, comandi `osm-campione` e `dtm-wcs`, archivio di prova OSM
del centro di Rimini, prove dal vivo di WMS AdE, WMS DBTR, WCS DTM e API OSM; può fare: leggere il GeoPackage dal PC e
preparare l'archivio (passo 2, alternativa), scrivere `archivi.json` da `prepara`, controllare i rapporti dei passi 4–5 e
le prove del passo 8. Resta a Paolo: la prenotazione del DBTR (reCAPTCHA ed email), i comandi sul server, l'email
all'Archivio Cartografico per DSM/LAS 2023-24.

## DBTR dei comuni, DTM dai quadranti e cortili (07/11/2026)

### Il DBTR vero

L'estrazione del Geoportale («Download DB Topografico», un comune alla volta: il Geoportale non permette la provincia né
la regione per EDI e UVL) arriva come `estraz_procons.gpkg` **o** come Shapefile (`V_UVL_GPG.shp` …) con gli stessi nomi:

| Strato | Cosa | Usato per |
|---|---|---|
| `V_UVL_GPG` | unità volumetriche (corpi): ID_E, EDI_ID_E, H_UVL, B_UVL, H_GRONDA, H_COLMO, TIPO_FONTE, QUALITA, DATA_AGG… | sagoma (con i cortili), altezza, colmo, legame con l'edificio |
| `V_EDI_GPG` | edifici: ID_E, FOGLIO, NUMERO, NOME, D_TY_EDI, D_STAT_E, COD_COM | nome, foglio e numero, tipo, nelle proprietà di ogni corpo |
| `V_EDI_CT_USO_AVM` | destinazione d'uso CT_USO/D_CT_USO per ID_E (senza geometria) | destinazione nelle proprietà; uso per la stima dei piani (`uvl.USI`) |
| `V_EDI_GPGSA` | ingombro al suolo degli edifici | non usato |

`edifici3d/uvl.py` legge GeoPackage e cartelle Shapefile (strato `V_UVL_GPG`, o il vecchio nome del WMS) con pyogrio
**senza pyarrow** (prima `read_arrow` falliva senza pyarrow, che non è nei requisiti: anche `regionali.py` e `zornade.py`
ora usano lo stesso lettore). I corpi si legano all'edificio con `EDI_ID_E → V_EDI_GPG.ID_E`: la pagina sceglie
l'edificio con tutti i suoi corpi.

**Altezze** (verifica del 07/11/2026 su 42.804 UVL di Rimini contro il DTM 5 m 2025 e il DSM LiDAR 2019 della costa su
1.930 corpi; poi Faenza e Lugo; i metadati dicono solo «altezza qualitativa ±3 m, normalizzata a 3, 6 e 9 m»):

| Caso | Cosa è | Regola |
|---|---|---|
| H_UVL intero (Rimini 80 %, Lugo e Faenza quasi tutti) | altezza del corpo; rispetto al LiDAR −1,2 m dalla mediana del tetto, ~gronda | gronda = H_UVL |
| H_UVL decimale **sopra** B_UVL (Rimini 7.816 corpi, aggiornati 2025-26) | **quota assoluta** del tetto: H_UVL − B_UVL = mediana LiDAR (−0,1 m) | gronda = H_UVL − B_UVL |
| H_UVL decimale **sotto** B_UVL (Faenza, base ~33 m) | altezza | gronda = H_UVL |
| H_UVL ≈ B_UVL in collina, o H_UVL ≤ 0 (tettoie, baracche, cabine) | nessuna altezza | corpo scartato (Rimini 2.286, Faenza 513, Lugo 173) |
| H_COLMO sopra B_UVL (Rimini) | quota assoluta del colmo: H_COLMO − DTM = 95° percentile LiDAR (−0,2 m) | colmo = H_COLMO − B_UVL (4.313 corpi a capanna) |
| H_COLMO sotto B_UVL (Faenza) | altezza del colmo (H_COLMO − H_UVL ≈ 0,8 m) | colmo = H_COLMO (3.262 corpi) |
| H_GRONDA | quota, ma spesso vicina al terreno (mediana 3,6 m sotto il LiDAR) | **non usata** come gronda; resta in `quota_gronda_dbtr` |

**Convenzione per comune** (correzione del 07/11/2026 notte, dopo la preparazione di Faenza): le regole «quota» si
applicano solo se l'estrazione usa le quote. `uvl.convenzione()` guarda gli H_UVL con i decimali: se almeno il 5 % (e
almeno 5) sta **sotto** la base di oltre 1 m – impossibile per una quota del tetto – l'estrazione usa le **altezze** e
tutti gli H_UVL sono altezze (Faenza: prima la soglia fissa `BASE_COLLINA` di 15 m e la regola dei decimali scambiavano per
quote un campanile di 44,5 m e una chiesa di 43,5 m, ridotti a 7 e 10,5 m). Rimini resta «quote» (7.861 corpi assoluti,
invariato), Lugo «quote» con 3 corpi assoluti. Il comando `prepara` scrive la convenzione nel registro.

La fonte dell'altezza di ogni corpo lo dice («DBTR H_UVL (altezza del corpo, ±3 m, da DTM DSM 2008)», «DBTR H_UVL −
B_UVL …», «; colmo da H_COLMO − B_UVL»); la pagina mostra «DB topografico regionale» come fonte del 3D (prima «DTM DSM 2008»
nella fonte faceva scrivere «corpi dal LiDAR»: corretto in `edificio3d.js`). Licenza: **CC BY 4.0** nella scheda RNDT
`r_emiro:2017-11-24T135040` (i metadati XML dentro l'estrazione dicono ancora CC BY 3.0, scheda vecchia; compatibili);
attribuzione «Regione Emilia-Romagna – DBTR, CC BY 4.0» in archivio, `LICENZE.txt`, pagina, immagini e report.

### Comandi

```
# controllo degli attributi (GeoPackage o cartella Shapefile)
python -m edifici3d controlla-uvl --gpkg /dati/edifici/cc-by/er/grezzi/dbtr/rimini/estraz_procons.gpkg
# un archivio CC BY per comune: cc-by/er/<comune>/prodotti/ (autonomo; più comuni in parallelo, cartelle diverse)
python -m edifici3d prepara --comune rimini --gpkg …/dbtr/rimini/estraz_procons.gpkg \
       --dtm …/grezzi/dtm5/DTM5x5_ed2025_SE_7791.zip --archivio /dati/edifici
python -m edifici3d prepara --comune faenza --gpkg …/dbtr/faenza --dtm …/DTM5x5_ed2025_SE_7791.zip --archivio /dati/edifici
# archivi.json dalla cartella degli archivi: solo DBTR e archivi veri (dal 07/11/2026; --con-prova rimette le prove OSM)
python -m edifici3d archivi-json --archivio /dati/edifici
# comune non nella tabella uvl.COMUNI_ISTAT: --istat 040007; estrazione di una parte del comune: --parziale
python -m edifici3d prepara --comune ravenna --parziale --gpkg …/dbtr/ravenna/estraz_procons.gpkg --dtm … --archivio /dati/edifici
# DTM: un quadrante (solo SE per la Romagna) e, se serve, un ritaglio
python -m edifici3d scarica --fonte dtm5 --quadrante SE --archivio /dati/edifici          # o wget -c (procedura F)
python -m edifici3d dtm-ritaglia --file …/DTM5x5_ed2025_SE_7791.zip --riquadro 775300 4874100 791400 4891000 --uscita dtm5_rimini.tif
# archivio di prova OSM rigenerato con i cortili, senza rete
python -m edifici3d osm-campione --riquadro 12.5600 44.0555 12.5735 44.0640 --nome rimini-prova --archivio /dati/edifici \
       --osm /dati/edifici/odbl/rimini-prova/grezzi/mappa.osm --dtm /dati/edifici/odbl/rimini-prova/grezzi/dtm5.tif
```

`prepara` (senza `--comune` scrive come prima in `cc-by/er/prodotti/`; accetta anche più `--gpkg` insieme, deduplicando
gli ID_E) scrive `corpi.pmtiles`, `contesto/` (quote dei corpi dal DTM ritagliato sul riquadro dei corpi più 300 m, poi
cancellato; `dtm_cog.tif` e `terreno.pmtiles` solo con `--terreno-archivio`), `indice.json` (nome «DBTR Emilia-Romagna – Rimini», riquadro, comuni catastali, file letti,
attribuzioni per file, secondi) e `LICENZE.txt`. Le proprietà di ogni corpo comprendono `foglio`, `numero`, `nome`,
`destinazione`, `tipo_edificio`, `altezza_dbtr` (relativa/assoluta) e, per le altezze non plausibili portate alla stima,
`h_dbtr_scartata` e `stima_altezza` («vicini» o «uso»). Le celle di contesto si riscrivono da capo a ogni
preparazione.

`archivi-json` elenca gli indici di `*/*/prodotti/` e `*/*/*/prodotti/` (CC BY prima, ODbL dopo; le prove OSM solo con
`--con-prova`, per ultime; `--senza-prova` resta accettato ed è il predefinito dal 07/11/2026), con nome, licenza,
attribuzione, riquadro, numero di corpi e, per gli archivi di un comune intero, `istat` (dall'indice, scritto da `prepara`
dal 07/11/2026, o dalla tabella `uvl.COMUNI_ISTAT` per gli archivi preparati prima, come Rimini; mai per i `parziale`), più `"lidar": "/edifici3d/cc-by/er/prodotti/"` (le falde della
pipeline notturna restano nell'archivio regionale); copia il file precedente in `archivi.json.prima`. La pagina legge fino
a 150 archivi (60 fino al 09/11/2026, quando sono diventati 69) e interroga solo quelli il cui riquadro tocca il punto (più 300 m); i corpi di archivi con la **stessa
licenza** (due comuni vicini) non si escludono a vicenda; il terreno 3D viene dalla rotta del server (uno solo per tutti
gli archivi; le tessere dell'archivio solo se l'indice ha ancora `tessere_terreno`: demo sintetica e archivi vecchi).
La pipeline LiDAR (`lidar`) legge i corpi di `cc-by/er/prodotti/contesto` **e** di tutti i `cc-by/er/<comune>/prodotti/contesto`.

### Prova sul DBTR vero di Rimini (container, 2 CPU Xeon 2,1 GHz)

- `controlla-uvl`: 42.804 UVL di 35.702 edifici (32.459 con foglio e numero, 34.088 con destinazione), 4,3 s, 392 MB.
  Altezza usata per 40.518 corpi: mediana 7 m, 95° percentile 15 m, massimo 83 m (zona mare); 4.313 tetti a capanna.
- `prepara --comune rimini` con il quadrante SE (zip, senza estrarlo): **40.518 corpi**, 1.048 tessere vettoriali, 193 celle,
  448 tessere del terreno, **301 s**, **700 MB** di memoria al massimo, **106 MB** di prodotti (corpi.pmtiles 16 MB,
  contesto 34 MB, terreno.pmtiles 28 MB, dtm_cog.tif 29 MB). Sul server (ARM, 2 OCPU, 12 GB; container `edifici-lidar` con
  1 CPU e 4 GB) si stimano 5–10 minuti per un comune come Rimini; i 19 comuni scaricati (~300.000 UVL) ~1 h e ~0,8 GB.
- Biblioteca Gambalunga (EDI 5bcfc664, «Palazzo Gambalunga – Biblioteca», foglio 74 numero 1100): 2 corpi, 13 e 14 m,
  **cortile** presente; Ospedale Infermi (EDI a707d3a4, destinazione «sede di ospedale», foglio 99 numero 1): 14 corpi da 7 a
  30 m, un cortile. Tutti e due scelti col punto e generati in 3D in Chromium (fonte «DB topografico regionale», nessun
  errore). Il punto di viale Settembrini 2 dell'ANNCSU può cadere sull'Istituto «Leonardo da Vinci» accanto: si trascina.
- Pipeline LiDAR su una tessera della costa (32_78404886) con l'archivio vero: 586 corpi, falde trovate (capanna,
  padiglione, piano), 23 s.
- Archivio di prova OSM rigenerato coi cortili dal `mappa.osm` e dal DTM del quadrante: 534 edifici, 530 corpi. Accanto
  al DBTR aggiungerebbe 91 sagome non coperte, quasi tutte minuscole o duplicati: **si toglie da `archivi.json`**
  (`--senza-prova`); i file restano sul server come riserva (scelta prudente, decisione finale a Paolo).

### DTM 5 m dai quadranti

«DTM 5×5 – ultima edizione», edizione 2025, quattro quadranti GeoTIFF zippati (NO 1.562.380.811, NE 1.153.456.683, SO
1.035.399.357, **SE 1.459.636.279 byte**: Romagna, 655.500–802.800 E, 4.843.000–4.922.500 N), licenza **CC BY 4.0**
(scheda RNDT `r_emiro:2016-08-08T155835`, revisione 18/12/2025, e PDF della licenza nello zip). Indirizzi in
`fonti/emilia_romagna.toml` (`quadranti`, con dimensione attesa). Il TIFF dentro (1,87 GB, float32 non a tessere) si legge
**solo nella finestra** che serve, anche dentro lo zip (`/vsizip/`, `edifici3d/dtm_locale.py`): un comune in ~5 s.
Il WCS (`dtm-wcs`) resta come riserva.

### Cortili (fori)

- UVL con fori (215 a Rimini) e multipoligoni OSM (`osm_campione.edifici_da_xml`: way `outer`/`inner` anche aperte,
  ricomposte con polygonize, fori tenuti, una parte per poligono `r<id>_<k>`) arrivano con i fori in PMTiles e celle.
- Sito: `aCorpo()` porta `buchi`; il GeoJSON dell'edificio scelto e del 3D li ha; un punto in un cortile non è «dentro»
  (la distanza conta anche dai lati del cortile); `edifici_calcoli.js` ha `areaCorpo`, `dentroCorpo`, `latiCorpo`: area,
  volume, superfici e pareti (quelle sul cortile comprese) come `modello.indicatori` in Python (test di parità
  `test_indicatori_con_cortile_python_e_sito_uguali`). Le ombre usano la sagoma esterna (il cortile resta in ombra:
  approssimazione dichiarata qui).

### Ripiego OSM al volo (07/11/2026)

- `osm_campione.query_punto(lon, lat, 400)`: query Overpass in XML (`way` e `relation` `building` `around`, con i membri
  `(._;>;)`), stesso formato dell'API di OSM; `crs_metrico(lon)`: fuso UTM 32/33/34 N per aree corrette in tutta Italia;
  `errore_overpass()`: Overpass risponde 200 anche con la query in timeout (`<remark> runtime error`);
  `corpi_al_volo(xml, lon, lat)`: `edifici_da_xml` + `corpi_con_stima` (9 m) + `tessere.feature_da_corpi` → GeoJSON WGS84
  con le proprietà delle celle di contesto.
- `osm.corpi_da_osm`: i pezzi di un multipoligono (`r<id>_<k>`) hanno `edificio = r<id>` (un edificio solo per scelta,
  totali e report); vale anche per l'archivio di prova.
- Prove: `tests/test_osm_campione.py::test_ripiego_al_volo_corpi_e_query` (way outer aperte saldate, cortile, due pezzi
  dello stesso edificio, stima, coordinate WGS84); `test_edifici3d.py::test_archivio_per_comune_archivi_json_e_controllo`
  (predefinito senza prove, `--con-prova`, `istat` dall'indice e dalla tabella, `parziale`).
- Dal vivo (07/11/2026, rotta del server dal container): Pesaro 390 corpi (380 con altezza stimata), Cesena 746 corpi (745
  stimati, 18 con cortile): in OSM le altezze mancano quasi sempre, anche sugli ospedali.

## «Aggiungi DBTR»: DB topografici caricati dagli utenti (07/11/2026)

Decisione di Paolo del 07/11/2026: la pagina Patrimonio › Aggiungi edifici (DB topografico) legge nel browser il DB
topografico scaricato dal portale della Regione (`fase5-sito/sito/dbtr_lettore.js`, **stessa logica** di `uvl.py` e
`regionali.py`) e, con il consenso esplicito, lo manda alla coda del server, che lo prepara qui e lo installa dopo
l'approvazione nella pagina interna.

| File | Cosa fa |
|---|---|
| `edifici3d/coda.py` | stati e richiesta (`richiesta.json`), nomi dei comuni, controllo leggero dello zip (anche per l'api), estrazione sicura, controlli (strati e colonne, EPSG, riquadro nella regione, metadati XML come testo, comuni catastali, dati personali), `prepara`/`prepara-regione --comune` in un processo figlio (`nice`, 3,5 GB), `controlla-archivio`, anteprima, corpi sospetti (sotto 30 m² e oltre 40 m, solo segnalati), installazione con `_precedenti/`, ritorno, pulizia, finestra oraria, pausa con le previsioni |
| `edifici3d/archivi.py` | `scrivi_archivi_json` (spostato da `__main__`, che lo importa): leggero, cartelle «_…» ignorate, scrittura atomica |
| `edifici3d/__main__.py` | `coda [--ciclo]`, `coda-ripristina --zona --comune`; `prepara-regione --comune --nome --istat --parziale` (un archivio per comune anche in Lombardia, FVG e Liguria: `cc-by/<lom|fvg|lig>/<comune>/prodotti/`) |
| `edifici3d/regionali.py` | `nomi_completi`: i nomi troncati a 10 caratteri dei DBF (`QUOTA_GRON`, `def_tipo_e`…) tornano quelli completi |

Comandi (servizio `edifici-coda`, `docker-compose.yml` della fase 4):

```
python -m edifici3d coda --cartella /dati/edifici_coda --archivio /dati/edifici --ciclo   # un giro al minuto
python -m edifici3d coda --cartella /dati/edifici_coda --archivio /dati/edifici           # un giro solo (prove)
python -m edifici3d coda-ripristina --archivio /dati/edifici --zona er --comune lugo        # torna all'archivio precedente
python -m edifici3d --zona lombardia prepara-regione --file un_vol.shp --archivio … --comune milano --istat 015146
```

Opzioni del ciclo: `--pausa-url` (predefinita `http://api:8000/api/salute`: non si comincia se `previsioni_in_corso > 0`),
`--finestra` (predefinita `03:15-07:00`, la pipeline LiDAR). Variabili: `CODA_MEMORIA_GB` (3,5), `CODA_MINUTI` (120),
`CODA_DTM_ER`, `CODA_DTM_LIG` (DTM da usare; predefiniti i quadranti in `cc-by/er/grezzi/dtm5/` e i GeoTIFF in
`cc-by/lig/grezzi/dtm/`). Senza DTM le quote dei corpi vengono dalla base del DB topografico (il terreno 3D è comunque
quello della rotta del server). La Liguria senza DTM sul server non supera i controlli.

**Parità Python–JavaScript** (`tests/test_dbtr_parita.py`, node; `tests/test_dbtr_browser.py`, Chromium): sui DB sintetici
di `tests/dbtr_sintetici.py` identica (corpi, proprietà, coordinate entro 2·10⁻⁷ gradi); sulle estrazioni vere (se c'è
`DBTR_VERI`, predefinita `/home/claude/dbtr2`) Lugo 1 corpo diverso su 19.906, Faenza 3 su 29.630, Rimini 6 su 40.518:
geometrie non valide che il Python ripara con `make_valid` e il browser no. Per arrivarci: area con le coordinate spostate
sul primo vertice (come GEOS; prima ~45 corpi per comune differivano di 0,1 m²) e arrotondamenti come `round()` di Python.
Test della coda: `tests/test_coda.py`.

## Terreno dal server e altezze non plausibili (07/11/2026)

### Terreno: niente più DTM negli archivi dei comuni (decisione di Paolo, 07/11 ore 11:37)

Gli archivi dei comuni montani erano pesanti per il terreno, non per gli edifici: Brisighella 169 MB di prodotti, di cui
**98 MB** `terreno.pmtiles` (770 tessere a zoom 15 da ~92 kB l'una) e **71 MB** `dtm_cog.tif`, contro 2,9 MB di
`corpi.pmtiles` e 5 MB di celle. La prima idea (zoom pieno solo entro 300 m dai corpi, zoom 13 altrove) avrebbe ridotto
Brisighella a ~70 MB; la decisione è stata più netta:

- **il server tiene il DTM** 5 m come **COG unico per quadrante** in `/srv/energia/dati/terreno/` (`/dati/terreno` nei
  container), convertito **una volta** dallo zip della Regione con `dtm-server` (`dtm_locale.cog_server`: DEFLATE con
  predittore, tessere 512, panoramiche; accanto `<nome>.json` con sistema, riquadro in WGS84, licenza e attribuzione).
  Quadrante SE: 1.459.636.279 byte di zip → **1,30 GB** di COG (il TIFF dentro è 1,87 GB), 815 s nel container con altri
  due processi in corso;
- **la rotta `/api/terreno/{z}/{x}/{y}.png`** (`fase4-server/servizio/terreno.py`) genera le tessere Terrarium **solo dove
  qualcuno apre il 3D** (lettura a finestra, panoramica adatta allo zoom: 0,03–0,13 s per tessera; 40–120 kB), con copia
  su disco (5 GB al massimo), Cache-Control di 30 giorni e limite per IP; fuori dal DTM regionale e nei suoi vuoti il
  **Copernicus DEM 90 m** (gli stessi file `.om` dell'orizzonte lontano, ~4 s la prima volta), se nemmeno quello
  risponde una tessera piatta dichiarata (`X-Terreno-Fonte: piatta`, non copiata);
- **la pagina 3D** usa quella sorgente `raster-dem` (`tiles`, zoom 8–15; sopra il 15 MapLibre ingrandisce) se
  `/api/terreno/fonti` risponde con `"attivo": true` (prova prima di creare la mappa: se **tutte** le tessere danno 404
  MapLibre non finisce di caricare la mappa; senza rotta la mappa resta piatta, come senza DTM); le
  tessere dell'archivio solo se l'indice ha ancora `tessere_terreno` (demo sintetica, archivi preparati prima). Una
  tessera che manca (404) non dà errori: MapLibre usa quella di livello più basso (prova in Chromium,
  `test_modelli3d_terreno_dal_server_e_altezza_stimata`). Vale anche per il DB topografico letto nel browser;
- **`prepara`** continua a calcolare dal DTM la **quota di ogni corpo** (minimo e mediana dentro la sagoma, un numero per
  corpo nelle celle e nelle tessere): ombre, orizzonte vicino (Web Worker: solo corpi, gronde e quote) e report non
  dipendono dalle tessere. `dtm_cog.tif` e `terreno.pmtiles` si scrivono solo con `--terreno-archivio` (prove sul PC
  senza server); `controlla-archivio` non li chiede più e dice da dove viene il terreno;
- **pipeline LiDAR**: il ripiego «DTM della Fase A» (il `dtm_cog.tif` dell'archivio) ora è seguito dal DTM del server
  (`DTM_SERVER`, predefinita `/dati/terreno`, solo se nel sistema della zona).

Confronto prima/dopo vicino agli edifici (40 corpi a caso per comune, tessere che li contengono; tessere dell'archivio del
07/11 mattina contro quelle generate dalla rotta sul COG del server):

| Comune | Zoom 15 | Zoom 14 | Zoom 13 | Quote dei corpi |
|---|---|---|---|---|
| Brisighella | 33 tessere, scarto massimo **0,000 m** | 24, 0,000 m | 14, max 3,1 m (media 0,14 m) | identiche (5.698 corpi) |
| Rimini | 30 tessere, **0,000 m** | 19, max 0,23 m | 11, max 1,5 m (media 0,02 m) | identiche (40.518 corpi) |

Allo zoom 15 (quello della vista 3D attorno all'edificio) le tessere sono identiche; agli zoom 13–14 la rotta legge le
panoramiche del COG (10–20 m) invece di ricampionare i 5 m, con scarti di qualche metro solo in montagna e solo lontano
dalla vista. Le quote dei corpi non cambiano; ombre e orizzonte vicino cambiano solo per i corpi con l'altezza portata
alla stima (sotto).

### Altezze del DBTR non plausibili → stima (decisione di Paolo, 07/11/2026)

`plausibilita.py`, chiamata da `_corpi_uvl` (quindi da `prepara` e dalla coda), e la stessa funzione `plausibilita` in
`dbtr_lettore.js` (parità in `tests/test_plausibilita.py`). Il corpo resta; la gronda del DBTR si sostituisce con la
**mediana dei corpi vicini** (centro entro 100 m, gronda plausibile ≤ 40 m, al mezzo metro) o, senza vicini, con una stima
dall'uso (due piani più il sovralzo, tra 6 e 9 m; capannoni 8 m); colmo tolto, `h_dbtr_scartata` (valore originale),
`stima_altezza`, `fonte_altezza` = «stima: altezza DBTR non plausibile (114 m)», `qualita` = «altezza stimata (dato DBTR
non plausibile)». Pagina e report mostrano «altezza stimata (dato DBTR non plausibile: 114 m)».

Regola (analisi dei 502 corpi oltre 25 m dei 19 comuni): **candidato** un corpo non verticale (luogo di culto, campanile,
torre, ciminiera, industriale/capannone, impianto, serbatoio, antenna, faro, inceneritore, silo) con gronda oltre 150 m,
oppure oltre 30 m con **snellezza** (gronda / larghezza minima dell'inviluppo convesso) oltre 8; **non plausibile** se
oltre 150 m, o se non tocca un corpo alto (riquadro entro 3 m, almeno 60 m², gronda ≥ la sua − 8 m: torrini sopra un
palazzo) e ha area sotto 30 m² o gronda oltre 3 volte la mediana dei vicini. La sola regola «sotto 30 m² e oltre 40 m»
avrebbe preso anche la ciminiera di Forlì (60 m su 14 m²) e un pezzo di chiesa di Ravenna (44 m su 9 m²); una regola solo
relativa (4× la mediana) il Grattacielo di Rimini (83 m su 17 × 47 m, vicini a 7 m: snellezza 4,8).

Corpi portati alla stima (stessi conteggi nella rigenerazione): 7 corpi (Bagno di Romagna 1, Forlì 3, Lugo 1, Ravenna 1, Rimini 1), gli stessi previsti dall'analisi sulle celle:

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

Tempi di preparazione invariati (da 24 s a 9,4 minuti per Forlì, due comuni alla volta).

Restano (non toccati, da guardare con l'ortofoto se serve): a Mercato Saraceno ~15 corpi «abitativa» del foglio 94 a
32–40 m con vicini simili (probabile convenzione delle quote diversa in quella zona); a Lugo il secondo corpo dello stesso
edificio a 39 m (57 m², snellezza 5).

## Comuni dell'08/11 e del 09/11/2026: 54 archivi DBTR e quadrante NE del DTM

Estrazioni scaricate da Paolo l'08/11 (`downloadDBTR_354162`–`354171`) e il 09/11 (`354181`–`354187`), riconosciute dal
codice catastale `COD_COM` di `V_EDI_GPG` e preparate con `prepara --comune` sui **due quadranti** SE e NE del DTM 5 m
(`--dtm` accetta più quadranti). Dal 09/11 le estrazioni **raggruppate** (più comuni in un solo GeoPackage: 354184, 354185,
354168, 354187) si dividono prima con `dividi` (sotto); i pezzi dei comuni che hanno già un archivio (Cesena, Rimini,
Riccione, Faenza, Lugo, Forlì, Forlimpopoli, Bagnacavallo, Cotignola, Brisighella, Conselice, Russi, Imola…) restano fuori.

| Comune | ISTAT | Fogli | Corpi | Gronda max | Note |
|---|---|---|---|---|---|
| **Bologna** (09/11) | 037006 | tutti tranne 63, 64, 65, 66, 89, 133, 250 (354168 + 354187) | 61.813 | 103,7 m (52 oltre 60 m) | comune intero; prima 66.283 corpi con i pezzi dei comuni vicini, ora solo Bologna (i vicini hanno archivi loro); tar 35 MB |
| Cesenatico | 040008 | 54 su 54 | 11.659 (1.659 senza altezza, scartati) | | tar 6,3 MB |
| Bellaria-Igea Marina | 099001 | 25 su 27 | 7.479 | | |
| Bagnacavallo | 039002 | 94 su 95 | 11.467 | | Shapefile |
| Conselice | 039008 | 62 su 65 | 6.722 | | Shapefile, tutto nel quadrante NE |
| Modigliana | 040022 | 95 su 96 | 2.814 | | |
| Alfonsine | 039001 | 111 su 113 | 6.978 | | |
| Cotignola | 039009 | 38 su 38 | 4.958 | 15 m | |
| **Castel Bolognese** (09/11) | 039006 | 36 su 36 (354181, Shapefile, + 1 corpo da 354184) | 2.815 | 24 m | comune intero |
| **Misano Adriatico, Morciano e Coriano** (09/11) | — (`--parziale`) | Misano 24 su 26, Morciano 7 su 8, **Coriano 39 su 46** (354171 + Coriano e Misano di 354184) | 14.347 | 30 m | rifatto il 09/11 (prima 11.964 corpi, Coriano 18 fogli); nome «… Misano Adriatico, Morciano e Coriano (centro e frazioni principali)» |
| **Ravenna** (09/11) | — (`--parziale`) | 186 fogli: ospedale del 06/11 + 354163 + 354183 (altri fogli del forese) | 42.574 | 55 m | prima 27.525 corpi (città); nome «… Ravenna (città e parte del forese)»; corpi uniti per `ID_E`; tar 23 MB |
| Gambettola (09/11) | — (`--parziale`) | 10 su 14 | 2.691 | 23 m | i 18 comuni sotto: «… <Comune> (centro e frazioni principali)» |
| Predappio | — | 30 su 98 | 1.620 | 40 m | 354184 + 15 corpi di 354185 |
| Riolo Terme | — | 22 su 47 | 1.612 | 21 m | 354184 + 8 corpi di 354181 |
| Longiano | — | 10 su 29 | 659 | 21 m | |
| Gatteo | — | 5 su 15 | 119 | 9 m | solo i fogli verso Gambettola e Savignano |
| Massa Lombarda | — | 34 su 47 | 3.422 | 21 m | |
| Fusignano | — | 22 su 28 | 3.991 | 28 m | mancano 3, 10, 11, 12, 13, 18 (con edifici: sotto) |
| Meldola | — | 29 su 60 | 2.782 | 27 m | 354185 + 9 corpi di 354184 |
| Verucchio | — | 20 su 21 | 3.096 | 36 m | manca il foglio 2 (con edifici: sotto) |
| Castrocaro Terme e Terra del Sole | — | 33 su 39 | 2.408 | 31 m | |
| Bertinoro | — | 30 su 65 | 1.805 | 37 m | |
| Solarolo | — | 16 su 25 | 1.715 | 19 m | |
| Sant'Agata sul Santerno | — | 8 su 12 | 1.118 | 19 m | |
| Sarsina | — | 14 su 55 | 914 | 27 m | |
| Dovadola | — | 21 su 33 | 662 | 37 m | |
| Premilcuore | — | 11 su 47 | 441 | 30 m | |
| Sant'Agata Feltria | — | 8 su 13 | 249 | 12,5 m | |
| Casalecchio di Reno (09/11) | — (`--parziale`) | 26 fogli (354168 + 354187) | 3.950 | 37 m | gli 8 comuni vicini a Bologna con almeno ~1.000 volumi: «… <Comune> (zona verso Bologna)» |
| San Lazzaro di Savena | — | 33 fogli | 3.723 | 30 m | |
| Zola Predosa | — | 18 fogli | 2.361 | 30 m | |
| Calderara di Reno | — | 24 fogli | 2.357 | 33 m | |
| Castel Maggiore | — | 26 fogli | 1.770 | 26 m | |
| Granarolo dell'Emilia | — | 23 fogli (354187) | 1.290 | 36 m | |
| Sasso Marconi | — | 16 fogli (354187) | 1.129 | 20 m | |
| Pianoro | — | 14 fogli (354187) | 1.016 | 29 m | |

Tutti con `"problemi": []` e `"avvisi": []` (`controlla-archivio`, 09/11/2026). In `uvl.COMUNI_ISTAT` dal 09/11 anche
`castel-bolognese`; Ravenna (186 fogli, il forese non è completo), Misano e i 26 comuni parziali restano fuori apposta (zona
coperta = vicinanza ai corpi, sicura). Fuori dagli archivi: Anzola dell'Emilia (539 volumi) e Castenaso (229) nelle
estrazioni di Bologna, e i pezzi di poche decine di edifici di Imola, Mordano, San Clemente, Civitella, Sogliano, Portico,
Poggio Torriana, Santarcangelo. Archivi del 09/11 in `archivi_er_0911/` (29 tar, 91 MB, `SHA256SUMS_er_2026-11-09.txt`):
con i 28 dell'08/11 (Bologna, Ravenna e Misano sostituiti), le 15 città e Roma e Bari intere `archivi-json` dà **69 voci**.

**Fogli mancanti, confronto con OpenStreetMap** (09/11/2026; edifici OSM con il centro nel confine ISTAT generalizzato, a
più di 30 m da ogni corpo del DBTR; riferimento: Castel Bolognese, che ha tutti i fogli, 105 su 2.185 = **4,8 %**, sparsi,
per lo più tettoie e baracche che il DBTR non ha e i bordi del confine generalizzato):
- **Bologna**: 1.897 su 51.655 = **3,7 %**, sotto il riferimento, nessun gruppo oltre 75 edifici in una cella di 500 m (il
  più grande al bordo est, verso Villanova di Castenaso, dove il confine generalizzato entra nel comune vicino): i fogli
  63, 64, 65, 66, 89, 133 e 250 sono **rurali o con pochi edifici**. Bologna è preparata come comune intero.
- **Verucchio**: 434 su 2.413 = **18 %**, con gruppi di 20–50 edifici a ovest del capoluogo: il foglio 2 ha edifici →
  archivio parziale.
- **Fusignano**: 629 su 2.486 = **25 %**, un gruppo di 93 edifici a nord-ovest del centro: i 6 fogli mancanti hanno edifici
  → archivio parziale.

**Coriano** (scelta del 09/11/2026): rifatto l'archivio `misano-adriatico` con il nuovo Coriano, invece di un archivio
Coriano separato. Delle 34 tavole di Coriano in 354184, 13 sono già in 354171 (6–9, 17–20, 31, 32, 38, 40, 46) e 5 tavole
sono solo in 354171 (28–30, 39, 47): un archivio separato senza i volumi di Misano avrebbe diviso Coriano in due archivi,
con le tavole di confine metà qui e metà là; rifacendo `misano-adriatico` la deduplica per `ID_E` di `prepara` basta
(2.393 corpi nuovi su 4.203), Coriano sta in un archivio solo (39 fogli su 46) e si sostituisce una cartella che c'è già.

### Estrazioni raggruppate: `dividi` (09/11/2026)

`prepara` non filtra per comune: `python -m edifici3d dividi` (modulo `edifici3d/dividi.py`) scrive per ogni estrazione un
GeoPackage ridotto con i quattro strati filtrati in modo coerente (`V_EDI_GPG` del comune, `V_UVL_GPG` con `EDI_ID_E`
tenuto, `V_EDI_GPGSA` e `V_EDI_CT_USO_AVM` con `ID_E` tenuto). Un edificio è del comune se il suo `COD_COM` è uno dei codici
dati, oppure se `COD_COM` è vuoto (circa il 10 % degli edifici) e il suo punto interno cade nel **confine ISTAT** del comune
(`b_regioni.confine_comune`, senza margine; per le province dell'ER ora la ricerca va diretta al file `08.json`). Il codice
vince sul confine (il confine è generalizzato a circa 100 m). `--elenco` dice, per ogni `COD_COM` delle estrazioni, il
comune ISTAT che contiene la maggior parte dei suoi edifici (Bologna 0,997; Castel Maggiore C204 0,954; Calderara B399
0,89): così si riconoscono i comuni.

```
python -m edifici3d dividi --gpkg …/354168/estraz_procons.gpkg …/354187/estraz_procons.gpkg --elenco
python -m edifici3d dividi --gpkg …/354168/estraz_procons.gpkg …/354187/estraz_procons.gpkg --codici A944 --istat 037006 --uscita divisi/bologna
python -m edifici3d prepara --comune bologna --gpkg divisi/bologna/354168/estraz_procons.gpkg divisi/bologna/354187/estraz_procons.gpkg \
       --dtm …/DTM5x5_ed2025_SE_7791.zip …/DTM5x5_ed2025_NE_7791.zip --archivio …
python -m edifici3d prepara --comune pianoro --parziale --nome "DBTR Emilia-Romagna – Pianoro (zona verso Bologna)" --gpkg divisi/pianoro/354187/estraz_procons.gpkg --dtm … --archivio …
```

Il quadrante **NE** (`DTM5x5_ed2025_NE_7791.zip`, 1.153.456.683 byte, riquadro 655500–802800 E, 4922500–5002000 N, nel
TOML) serve a Bologna e ai suoi vicini, al nord di Ravenna, Bagnacavallo, Conselice, Alfonsine, Fusignano e Massa
Lombarda; sul server è `dtm5_er_ne.tif` per la rotta `/api/terreno` (passo J5 ter di `AGGIORNAMENTO_2026-11-07.md`). Il
comando di preparazione usato nel container (`prep.sh`, fuori dal repository) è `prepara --comune <c> --gpkg <file
divisi> --dtm <SE.zip> <NE.zip> --archivio <cartella> [--parziale --nome "…"]`, poi `controlla-archivio` e `tar czf
edifici_dbtr_<c>_2026-11-09.tar.gz cc-by/er/<c>`.

## Lettori regionali e città di riferimento (08/11/2026)

Tre lavori in parallelo (gruppi A, B, C) e l'integrazione dell'08/11/2026 sera: un adattatore per ogni DB topografico
delle città di riferimento, provato dal vivo su dati reali, e **15 archivi delle città** pronti per la procedura J
(`AGGIORNAMENTO_2026-11-07.md`, J4 quater e J5 quater). Gli adattatori nuovi stanno in `edifici3d/adattatori/` (uno per
regione, registrati da soli da `regionali.py`), le fonti in `fonti/<zona>.toml` (URL solo lì), le sagome al volo nuove in
`fonti/sagome_regionali.d/`. `python -m edifici3d --zona <zona> controlla-regione | prepara-regione` vale per tutte.

### Cartelle degli archivi per licenza (regola unica, 08/11/2026)

La cartella dice gli obblighi della licenza, secondo la mappa `[archivi]` del TOML della zona:
- **`cc-by/`**: licenze di sola attribuzione Creative Commons o con meno obblighi: **CC BY 4.0**, **CC BY 2.5** (Torino),
  **CC0 1.0** (Bolzano: nessun obbligo, attribuzione di cortesia) e la politica dei dati **Copernicus** (Reg. UE
  1159/2013: citazione e dichiarazione delle modifiche; altezze di Napoli);
- **`iodl/`**: **IODL 2.0** (Potenza, Bari, Venezia): attribuzione con il suo testo, tenuta a parte perché non è una
  licenza Creative Commons;
- **`odbl/`**: **ODbL 1.0** (OpenStreetMap, condivisione allo stesso modo): mai insieme alle altre.
Caddy serve tutto `/edifici3d/*` e la pagina accetta qualsiasi `base` di `archivi.json` sotto `/edifici3d/`: **nessuna
modifica alle pagine pubbliche né al Caddyfile** per `iodl/`. `archivi-json` mette gli archivi CC BY, IODL e CC0 insieme
(DB topografici, in ordine di percorso) prima di ODbL; `controlla-archivio` accetta CC BY 4.0, CC BY 2.5, IODL 2.0 e CC0
1.0 (con la licenza scritta anche nell'attribuzione) e, per gli archivi parziali, una mediana della gronda fino a 25 m
(centri storici: Genova 21,4 m); `prepara-regione --comune` scrive `LICENZE.txt` con il testo della licenza giusta e
l'attribuzione del DTM delle quote (`--attribuzione-dtm` se diverso da quello del TOML). Le altezze OSM (ODbL) non
entrano mai negli archivi CC BY o IODL: restano nelle sagome al volo e nel ripiego OSM.

### Città (archivi in `archivi_citta/edifici_<zona>_<comune>_2026-11-08.tar.gz`, tutti con `"problemi": []`)

Stato finale delle 16:10 dell'08/11/2026: 15 archivi (383 MB), `SHA256SUMS_citta_2026-11-08.txt`; con i 28 dell'ER
`archivi.json` ha **43 voci** (prima `cc-by/` in ordine di percorso, poi `iodl/`); pubblicati con `v2026.11.07b`
(08/11, 22:42). **09/11/2026**: **Roma** e **Bari** rifatti per il **comune intero** (`--istat`, non più `--parziale`) in
`archivi_bari_roma/` (`edifici_laz_roma_2026-11-09.tar.gz`, `edifici_pug_bari_2026-11-09.tar.gz`,
`SHA256SUMS_bari_roma_2026-11-09.txt`), da mettere sul server con `AGGIORNAMENTO_2026-11-09.md` al posto delle cartelle
dell'08/11; le voci di `archivi.json` restano 43.

| Città | Zona / adattatore | Copertura | Corpi | Controlli di altezza | Licenza | Cartella |
|---|---|---|---|---|---|---|
| Milano | `lombardia_milano` (zona lom) / `lombardia_dbgt` | comune intero 015146 (DBT 2020 del Comune) | 237.402 | Duomo 65,8 m; Torre Allianz (CityLife) 200,7 m; Torre Generali 165,5 m; DTM 5 m regionale | CC BY 4.0 | `cc-by/lom/milano` |
| Torino | `piemonte` / `piemonte_bdtre` | comune intero 001272 (con la fascia nord riscaricata, 143.566 volumi nel file) | 68.768 | grattacielo Intesa Sanpaolo 166 m; Mole 55 m (corpo murario; la guglia non è un volume); nessuna quota (`un_vol_qe` vuoto) | CC BY 2.5 (da confermare) | `cc-by/pie/torino` |
| Genova | `liguria` / `liguria_ctr3d` | 4 tavole (San Martino, centro, Lanterna), parziale | 1.501 | Matitone 101,2 m; DSM − DTM comunale 2018 contro z − DTM: mediana −0,71 m, 77 % entro 2 m | CC BY 4.0 | `cc-by/lig/genova` |
| Venezia | `venezia` (zona ven) / `venezia_dbgt` | comune intero 027042 (DBGT comunale, aggiornato al 10/09/2026) | 175.501 (74.542 edifici) | campanile di San Marco gronda 73,7 m, colmo 93,5 m (alto 98,6 m: la cuspide non è nel DB); basilica 25,4 m (colmo 39,1 m); Ospedale dell'Angelo fino a 28,0 m; Ospedale Civile ai Santi Giovanni e Paolo 17,8 m (padiglioni vicini fino a 27,9 m); massimo 77,95 m (Porto Marghera); quota = `UN_VOL_QB` (nessun DTM) | IODL 2.0 | `iodl/ven/venezia` |
| Trieste | `friuli_venezia_giulia` / `fvg_ctrn_ed2` | comune intero 032006 (CTRN ed. 2, volo 2003) | 38.819 | Municipio di piazza Unità 24,1 m; LiDAR 2017-2020 su 7.327 edifici (elemento 110103 e 5 tavole del 110141): scarto mediano +0,05 m, MAE 1,33 m, 82 % entro 2 m, 3,6 % oltre 5 m; torri di Cattinara 54,8 m contro DSM − DTM 58,7–60,6 m (coerente) | CC BY 4.0 | `cc-by/fvg/trieste` |
| Trento | `trento` / `trento_pat3d` | comune intero 022205 | 13.281 | Duomo 22,6 m; DSM First − DTM contro `MED_ALT` mediana +0,19 m, 94 % entro 2 m | CC BY 4.0 | `cc-by/tn/trento` |
| Bolzano | `bolzano` / `bolzano_inspire` | comune intero 021008 | 20.377 | campanile del Duomo 53,9 m (navata 14,4 m); altezze da DSM − DTM 0,5 m | CC0 1.0 | `cc-by/bz/bolzano` |
| Firenze | `toscana` / `toscana_uv` | comune intero 048017 | 104.475 | cupola del Duomo 112,6 m; Palazzo Vecchio 40,5 m; DSM LiDAR 2023 p90 − `uv_qe` +1,5 m; DTM LiDAR 2023 del Comune | CC BY 4.0 | `cc-by/tos/firenze` |
| Ancona | `marche` / `marche_dbgt` | comune intero 042002 | 11.289 | San Ciriaco 10,4 m (una gronda per edificio, 1:10.000); massimo 69,4 m | CC BY 4.0 | `cc-by/mar/ancona` |
| Roma | `lazio` / `lazio_dbgt` | comune intero 058091 (fogli 1:50.000 364, 365, 373, 374, 375, 386, 387 del DBGT 2014; `COD_ISTAT` del DB) | 384.621 (250.170 edifici) | Torre Europarco 111,3 m (massimo); Vittoriano fino a 63,3 m; Basilica di San Pietro 45,6 m; Palazzo della Civiltà Italiana fino a 60,2 m; Gemelli fino a 46,0 m; Umberto I fino a 29,5 m; Ostia 3.334 corpi entro 1 km (fino a 24,3 m); Fiumicino (058120) escluso; quota da `UN_VOL_QE − UN_VOL_AV`; archivio 390 MB (tar 126 MB): corpi.pmtiles 88,5 MB contro 64,2 MB, 1.462 celle contro 705, cella più grande invariata (1,57 MB, centro) | CC BY 4.0 | `cc-by/laz/roma` |
| Bari | `puglia` / `puglia_ctr` | comune intero 072006 (31 elementi CTR dei fogli 438 e 439, Palese, Santo Spirito, Carbonara, Torre a Mare compresi) | 73.205 (30.778 edifici) | Cattedrale fino a 37,2 m (corpo colpito 31,8 m); San Nicola fino a 26,1 m; Policlinico fino a 37,7 m entro 120 m; Petruzzelli 23,4 m; Palese 4.902 corpi entro 1 km, Torre a Mare 2.522; massimo 65,2 m; DTM 8 m (33 elementi) | IODL 2.0 | `iodl/pug/bari` |
| Potenza | `basilicata` / `basilicata_dbgt` | comune intero 076063 | 27.286 | Ospedale San Carlo 38,6 m (gruppo A); massimo 50,3 m; DTM 5 m dal WCS | IODL 2.0 | `iodl/bas/potenza` |
| Napoli | `campania_napoli` (zona cam) / `campania_dbt` | comune intero 063049 (DBT 2020) | 29.698 | altezze: classe Copernicus UA Building Height 2012 in circa 25.600 corpi (86 %), mediana dei vicini in circa 3.540, stima dall'uso in circa 560; Ospedale Cardarelli (DEA) classe 20–30 m → 25 m; torri del Centro Direzionale classe 100–368 m → 100 m (20 corpi oltre 60 m); DTM 2020 5 m | CC BY 4.0 (+ Copernicus) | `cc-by/cam/napoli` |
| Palermo | `sicilia` / `palermo_uv` | comune intero 082053 (unità volumetriche del Comune) | 99.023 | Teatro Massimo 39,3 m; massimo 204,1 m nell'area del porto (da controllare: probabile errore di quota) | CC BY 4.0 | `cc-by/sic/palermo` |
| Cagliari | `sardegna` / `sardegna_dbgt_lidar` | 6 tessere LiDAR (Castello e Brotzu), parziale | 3.034 | Ospedale Brotzu 26,4 m; Cattedrale 17,9 m; DSM buildings − DTM LiDAR 2008 1 m | CC BY 4.0 | `cc-by/sar/cagliari` |

Comandi di Venezia e Napoli (08/11/2026, dalla cartella della fase 10; `ARCH` = cartella degli archivi; gli altri 13 nei
`MODIFICHE_CONDIVISE.md` dei gruppi e in `COMANDI.md` del gruppo C):

```
# Venezia (scarico di Paolo dalla Carta Tecnica di dati.venezia.it; EPSG:3004 senza .prj)
python -m edifici3d.adattatori.venezia unisci --un-vol UN_VOL.shp --edifc EDIFC.shp --uscita venezia_uv.geojson
python -m edifici3d --zona venezia prepara-regione --file venezia_uv.geojson --archivio ARCH --comune venezia \
    --istat 027042 --nome "Venezia – DBGT del Comune (unità volumetriche)"                    # ~8 min, 175.501 corpi
# Napoli (DBT_5K.zip e DTM_5k.zip di Paolo; classi Copernicus dall'ImageServer EEA, senza account)
python -m edifici3d.adattatori.campania dbt-zip --zip DBT_5K.zip --uscita napoli_dbt.geojson
python -m edifici3d.altezze_dsm mosaico --file DTM_5k.zip --crs EPSG:25833 --zero-vuoto --uscita dtm5_napoli.tif
python -m edifici3d.altezze_ua --zona campania_napoli scarica --file napoli_dbt.geojson --crs-file EPSG:25833 --uscita ua_napoli.tif
python -m edifici3d.altezze_ua annota --file napoli_dbt.geojson --crs-file EPSG:25833 --raster ua_napoli.tif --uscita napoli_ua.geojson
python -m edifici3d --zona campania_napoli prepara-regione --file napoli_ua.geojson --dtm dtm5_napoli.tif --archivio ARCH \
    --comune napoli --istat 063049 --nome "Campania – Napoli (DBT 2020, altezze Copernicus UA 2012)"   # ~12 min
python -m edifici3d archivi-json --archivio ARCH
```

Comandi di **Bari** e **Roma per il comune intero** (09/11/2026, dalla cartella della fase 10; `G` = cartella dei file
grezzi, cancellabile alla fine):

```
# Bari: elementi 1:5.000 che toccano il confine ISTAT (+700 m), elenco in fonti/puglia.toml (elementi_bari); 438033 e
# 438082 sono solo mare (CTR 404, DTM sì). Quadro d'unione calcolato: foglio 20'×12', sezione 5'×3' (01–16 da NO per
# righe), elemento 2'30"×1'30" (1 NE, 2 SE, 3 SO, 4 NO).
for e in $(python -c "import tomllib;print(' '.join(tomllib.load(open('fonti/puglia.toml','rb'))['fonti']['edifici']['elementi_bari']))"); do
  curl -fsS -o $G/ctr/${e}_ctr.zip https://cartografia.sit.puglia.it/download/CTR/SHP/${e:0:3}/${e}_ctr.zip
  curl -fsS -o $G/dtm/${e}_asc.zip https://cartografia.sit.puglia.it/download/DTM/ASC/${e:0:3}/${e}_asc.zip; done
python -m edifici3d.b_regioni puglia-ctr --ctr $G/ctr/*_ctr.zip --istat 072006 --uscita $G/bari_ctr.geojson   # 74.817 corpi
python -m edifici3d.b_regioni puglia-dtm --asc $G/dtm/*_asc.zip --crs EPSG:7792 --uscita $G/dtm_bari_8m_7792.tif
python -m edifici3d --zona puglia prepara-regione --file $G/bari_ctr.geojson --dtm $G/dtm_bari_8m_7792.tif --archivio ARCH \
    --comune bari --istat 072006 --nome "Bari – CTR 2006 Regione Puglia"                               # ~6 min
# LICENZE.txt: stesso testo dell'archivio dell'08/11 (con la scheda RNDT del DTM 8 m)

# Roma: fogli 1:50.000 che toccano il confine (WFS geonode:qu_50k): 364, 365, 373, 374, 375, 386, 387 (fonti/lazio.toml,
# fogli_roma). Solo UN_VOL.* di ogni zip, con richieste Range e il gettone anonimo del File Browser (come il browser).
python -m edifici3d.b_regioni dbgt-fogli --shp $G/rm3{64,65,73,74,75,86,87}/UN_VOL.shp --istat 058091 \
    --uscita $G/roma_un_vol.gpkg                       # 742.377 letti → 388.033 (COD_ISTAT 058091), 0 doppioni, 0 id ripetuti
python -m edifici3d --zona lazio prepara-regione --file $G/roma_un_vol.gpkg --archivio ARCH --comune roma \
    --istat 058091 --nome "DB topografico Regione Lazio 2014 – Roma"                           # ~33 min, 384.621 corpi
python -m edifici3d controlla-archivio ARCH/cc-by/laz/roma/prodotti; python -m edifici3d controlla-archivio ARCH/iodl/pug/bari/prodotti
```
I volumi del foglio 374 fuori dal comune (18.806 di altri comuni: Fiumicino, Ciampino, …) non sono più nell'archivio;
i 142 con codice «058000» sono tenuti perché il punto interno cade nel confine ISTAT, i 44 fuori sono scartati; 819
volumi con `COD_ISTAT` 058091 cadono fuori dal confine generalizzato +150 m (bordi del confine ISTAT a ~100 m): tenuti.

Altre fonti provate ma senza archivio: CTR 2012-13 della Sicilia (`sicilia_ctr`: serve un DTM con licenza aperta),
sagome al volo di **Sardegna** (WFS) e **Campania** (ArcGIS REST) in `fonti/sagome_regionali.d/`; Bolzano e Trento non
sono nelle sagome al volo (il riquadro del Veneto li contiene: `fonte_nel_punto` prende la prima fonte; vale l'archivio
del comune). **Perugia** chiusa senza dati (portali dell'Umbria non raggiungibili; PST da riverificare dopo il 10/11).
**Catanzaro**: il DTM 5 m della Regione Calabria **non è aperto** («la cessione diretta ad Enti terzi dei dati non è
consentita salvo concessioni/autorizzazioni specifiche»): decisione di Paolo dell'08/11, da usare **solo per le quote a
terra degli edifici** (mai come terreno 3D né in `/api/terreno`) quando il ripiego OSM avrà le quote dal DTM; nessun
archivio per ora (nessun DB con gli edifici).

### File

| File | Cosa fa |
|---|---|
| `edifici3d/adattatori/a_dbgt.py` | base dei DBGT del catalogo nazionale (UN_VOL): nomi dei campi senza maiuscole, porzione 08 scartata, `coerenza()` |
| `edifici3d/adattatori/lazio.py`, `basilicata.py`, `piemonte.py` | `lazio_dbgt`, `basilicata_dbgt` (WFS e WCS RSDI), `piemonte_bdtre` (gruppo A) |
| `edifici3d/adattatori/toscana.py`, `puglia.py`, `marche.py`, `sicilia.py`, `friuli_venezia_giulia.py` | `toscana_uv`, `puglia_ctr`, `marche_dbgt`, `palermo_uv`, `sicilia_ctr`, `fvg_ctrn_ed2` (gruppo B) |
| `edifici3d/adattatori/trento.py`, `bolzano.py`, `sardegna.py`, `campania.py` | `trento_pat3d`, `bolzano_inspire`, `sardegna_dbgt_lidar`, `campania_dbt` (gruppo C) |
| `edifici3d/adattatori/venezia.py` | `venezia_dbgt`: DBGT del Comune di Venezia (EPSG:3004 senza `.prj`, gronda `UN_VOL_AV` = `UN_VOL_QG − UN_VOL_QB`, quota `UN_VOL_QB`, colmo `UN_VOL_QE − UN_VOL_QB`, sotto 0,5 m scartati); passo `unisci` con lo strato `EDIFC` (edificio di appartenenza e destinazione) |
| `edifici3d/a_comuni.py`, `edifici3d/b_regioni.py` | comune intero dai servizi o dai file, ritaglio sul confine ISTAT, DTM a blocchi (A); passi `toscana-wfs`, `puglia-ctr`, `marche-dbgt`, `palermo-uv`, `fvg-wfs`… (B); `dbgt-fogli` (09/11/2026: UN_VOL di più fogli DBGT del Lazio per un comune, senza doppioni) |
| `edifici3d/altezze_dsm.py` | altezze da DSM − DTM per sagoma (`annota`, `confronta`, `mosaico`); comando `confronta-dsm` (C) |
| `edifici3d/altezze_ua.py` | altezze dal **Copernicus Urban Atlas Building Height 2012** (Napoli): il servizio dà **classi** (1 = 2–4 m … 10 = 100–368 m), non metri; 90° percentile delle classi dei pixel nella sagoma, altezza centrale della classe, poi mediana dei vicini |
| `edifici3d/regionali.py` | `scegli_adattatore`: l'adattatore del TOML o uno di `alternativi` se al file mancano i campi (FVG: ED2 predefinita, ED1 per i file della coda); `controlla` usa la `coerenza()` degli adattatori esterni |
| `fonti/<zona>.toml` | lazio, basilicata, piemonte, lombardia_milano, toscana, puglia, marche, sicilia, sicilia_ctr, trento, bolzano, sardegna, campania, campania_napoli, venezia; aggiornati friuli_venezia_giulia (ED2), liguria (`[fonti.lidar]` di Genova), lombardia (`[fonti.dtm5]`) |

Immagini: `energia-edifici` copia tutta la fase 10 (adattatori, fonti, `altezze_*.py`); l'api copia solo
`sagome_regionali.py` (importa `osm_campione`, `pyproj`, `shapely`) e `fonti/sagome_regionali.d/` per le sagome al volo di
Sardegna e Campania; `servizio/edifici_osm.py` tiene anche il campo dell'uso della fonte (`SR.campi_tenuti`).

## Piano di lavoro (§ 15)

### Fase A – Edificio e contesto in ER (dati già disponibili)
- [x] Script di scaricamento parametrizzati (TOML) e controllo automatico degli attributi UVL; attributi verificati sul
      WMS (gronda/colmo vuoti, niente piani). [ ] **Scaricare davvero** GeoPackage UVL e DTM 5 m (URL da completare).
- [x] Archivi separati CC BY / ODbL nel codice (cartelle, registro, PMTiles che rifiutano licenze mescolate).
      [ ] Scaricare aggregati e OSM.
- [x] PMTiles degli edifici, COG e Terrarium del DTM; Caddy configurato. [ ] Produrli sui dati veri sul server.
- [x] Pagina 3D: selezione dell'edificio, contesto 250 m, corpi estrusi, terreno, ombre animate (demo sintetica).
- [x] Tetti piani correggibili, divisione manuale dei corpi, rettangoli FV, ombre e producibilità, report PDF/Excel/ODS.
      [ ] Producibilità col clima orario vero (serve l'archivio della fase 3 sul server).
- [x] Stima dei piani e superfici; colonne facoltative nel CSV di Patrimonio (fase 7 e sito).
- [x] Analisi 1 (geometria), 2 (consumi per m² e m³, Patrimonio e pagina Consumi), 3 (firma), 6 (FV con ombre).

### Fase B – Ortofoto e affinamenti
- [x] Proxy con cache per il WMS RER 2023-24 (stato «da confermare», spegnibile per fonte) e per le regionali in CC BY
      (Toscana 2023); Sentinel-2 cloudless 2016; Geoportale Nazionale solo dal vivo; procedura AGEA (`ortofoto-sito`);
      pagina Ortofoto. [ ] Conferma della Regione → `stato = "confermata"` nel TOML.
- [x] Facciate segmento per segmento, orizzonte lontano (Copernicus DEM, riuso della fase 3), confronto PVGIS con
      `userhorizon` (server, cache, sotto 30 chiamate/s).
- [x] Analisi 4 (classifica di priorità) e 14 (obblighi D.Lgs. 199/2021, S/V e zona).
- [x] Altre regioni in CC BY nei TOML delle ortofoto: Bolzano 2023 e Trento 2015 (Fase E, 04/11/2026). [ ] Piemonte ICE
      2009-11 e Basilicata 2013 da provare dal server (`fonti/regioni.toml`).

### Fase C – LiDAR e pipeline
- [x] Pipeline notturna a tessere con TOML per zona, DSM ridotto, falde per corpo (04/11/2026, campione sintetico).
- [x] Pagina di stato nascosta con Cloudflare Access (codice; [ ] configurare Access nel pannello di Cloudflare).
- [x] Prima zona: Rimini configurata (`zone/rimini.toml`). [ ] Misurare spazio e tempi reali (servono i corpi della Fase A
      e una fonte DSM/LAS attiva).
- [x] DSM/LAS RER, DSM costa 2019 e LiDAR PNRR predisposti come fonti «in attesa». [ ] Attivarli con URL e licenza
      confermata (risposta della Regione; app PST dopo il 7/11/2026).
- [x] Import DXF/IFC (comando sul PC, modello aperto solo nel browser). [x] Lettura diretta dei DXF/IFC nel browser
      (04/11/2026 notte: pagina Importa DXF/IFC con dxf-parser e web-ifc; file pesanti convertiti sul PC con EuGEnio Visure).
- [x] Corpi dal solo LiDAR (raggruppamento per altezza, § 7) per le zone senza UVL; ombre degli alberi dal DSM
      (05/11/2026, campione sintetico). [ ] Prova su una tessera vera (Bolzano, dal server).

### Fase E – Resto d'Italia e analisi avanzate
- [x] Verifica regione per regione di DB topografici con altezze, DTM, DSM/LiDAR e ortofoto (04/11/2026,
      `fonti/regioni.toml`); ortofoto di Bolzano 2023 e Trento 2015 accese. [ ] Riprovare dal server le voci «in attesa»
      per portale irraggiungibile.
- [x] Adattatori DBGT Lombardia, CTRN FVG e CTR 3D Liguria → corpi; zone LiDAR di Bolzano e Trento; copertura delle fonti
      e DSM della costa 2019 acceso solo dove copre (05/11/2026). [ ] Adattatori Edifici P.A.T. 3D e BDTRE Piemonte;
      `prepara-regione` sulla prima zona vera di ogni regione; sagome per Bolzano.
- [x] Altezze di Zornade (ODbL) in archivio separato, confronto e catena del § 4 (campione sintetico). [ ] Estratto vero
      di Zornade con le altezze LiDAR.
- [x] Struttura del modulo privato delle metodiche UNI e aggancio facoltativo delle analisi 5, 7–13. [ ] Tabelle e passi
      da compilare a mano (Paolo); pagine di calcolo.
- [x] Bozza dell'articolo su Stato Critico (`documenti/ARTICOLO_EDIFICI_3D_bozza.md`). [ ] Pubblicarlo dopo il sito.

(La fase D del programma è EuGEnio Visure, nella fase 11.)

### Attività manuali di Paolo collegate
- [x] Email all'Archivio Cartografico della Regione Emilia-Romagna (§ 14.1): inviata.
- [ ] Risposta a Zornade (§ 14.2), eventualmente con la domanda su `visura-api`.
- [ ] Dopo il 7/11/2026: controllare nell'app «Download Banca Dati PST» se ci sono livelli PNRR (25 cm, 2025–26,
      «SIM») e se coprono la Romagna; scaricare una tessera di prova.

## Fonti principali (§ 16)

- Zornade – llms.txt: https://zornade.com/llms.txt
- RNDT – catalogo nazionale dei dati territoriali (CSW): https://geodati.gov.it/RNDT/csw (Fase E; schede citate in `fonti/regioni.toml`)
- Aggregati strutturali: https://rischi.protezionecivile.gov.it/en/approfondimento/national-dataset-italian-structural-aggregates/
- Catasto senza fabbricati: https://www.rivistageomedia.it/survey-and-positioning/cartografia-catastale-italia-disponibile-per-il-download-ma-mancano-i-fabbricati
- DBTR UVL: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/database-topografico-regionale/immobili-e-antropizzazioni/edificato/layer-6
- DTM ER, novità 2025: https://geoportale.regione.emilia-romagna.it/notizie/servizi-e-applicazioni/dtm-novita-2025
- DTM 0,5 m RER: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/altimetria/layer-60
- Prodotti LiDAR RER2023-24: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/quadri-di-unione/layer-16
- RER2025/26: https://geoportale.regione.emilia-romagna.it/in-primo-piano/rer25-26-aggiornamento-set-26
- Ortofoto RER 2023-24: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/immagini/layer-14
- Ortofoto AGEA 2023 ER: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/immagini/layer-16
- GeoPortale AGEA, note legali: https://geoportale.agea.gov.it/legal-notes
- Ortofoto Toscana 2023: https://geodati.gov.it/resource/id/r_toscan:66ca3807-815a-4bd1-b626-98ca240d72a2
- EOX Sentinel-2 cloudless: https://cloudless.eox.at/pricing
- App PST: https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new
- LiDAR PNRR, stato aprile 2026: https://www.gisinfrastrutture.it/2026/04/ottime-notizie-per-il-dtm-ad-alta-precisione-di-tutta-litalia/
- PVGIS API: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
- OSM, completezza in Italia: https://iris.uniroma1.it/retrieve/32c1587a-0b38-4b80-bb32-3b3490acdff8/Salvati_Official-Statistics_2022.pdf

Elenco completo nel § 16 della proposta.
