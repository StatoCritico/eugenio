# Città di riferimento: istruzioni di download (tutte insieme)

Data: 08/11/2026. Unisce le sezioni «Istruzioni per Paolo» dei quattro documenti `documenti/CITTA_RIFERIMENTO_*.md`
(Milano-Firenze-Roma, Nord, Centro, Sud e isole), dove ci sono fonti, licenze, prove e aree di prova.

**Cartella di destinazione**: `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\<città>\` (una sottocartella per
città, in minuscolo: `firenze`, `genova`, `laquila`…). Le sottocartelle indicate nei passi (`dsm\`, `dtm\`, `ctr\`…) vanno create.
Niente login, registrazioni o captcha: se un sito li chiede, fermati e annotalo. Quando hai finito scrivimi «città
scaricate»: preparo gli archivi e li metto nella stessa pubblicazione con i lettori regionali.

**Spazio**: circa 4,5 GB in tutto (Firenze da sola ~2 GB). **Ordine**: A, poi B, poi C; D solo se vuoi i file sul PC.
**Dopo il 10/11** (portale PST del MASE di nuovo online): la sezione E in fondo.

## Sommario

| Gruppo | Città | Dimensione | Cosa si prende |
|---|---|---|---|
| A | Firenze | ~2 GB | DSM e DTM LiDAR 2023 a 0,5 m del Comune: il riferimento migliore d'Italia |
| A | Genova | ~140 MB | LiDAR comunale 2018 a 0,5 m e carta tecnica DXF |
| A | Trento | ~230 MB | Edifici P.A.T. 3D e LiDAR 2014/2018 |
| A | Potenza | ~125 MB | DBGT con altezze, DSM e DTM 5 m |
| A | Palermo | 16 MB | unità volumetriche con gronda |
| A | Milano | 597 MB | DBT 2020 con le altezze |
| A | Cagliari | ~55 MB | LiDAR 2008 a 1 m |
| A | Bari | ~26 MB | CTR 2006 con quote di gronda e DTM 8 m |
| A | Ancona | ~110 MB + Repertorio | DBT 2019 con quote di gronda |
| B | Roma | 582 MB | DBGT 2014 Lazio con altezze, dal File Browser regionale |
| B | Napoli | 175 MB | DBT e DTM 2020 dalla cartella SharePoint della Regione |
| B | Torino | da annotare | BDTRE del comune dal geoportale regionale |
| B | Trieste | da annotare | LiDAR 2017-2020 da Eagle.fvg come ospite |
| C | Venezia | — | portale del Comune |
| C | Perugia | — | UmbriaGeo |
| C | Catanzaro | — | geoportale della Calabria |
| C | L'Aquila | pochi kB | solo schede e quadro d'unione |
| D | Bolzano | 4 × 9,4 MB | il server prende tutto da solo dai servizi della Provincia |

## A. Download diretti (link fissi, nessun login): i più utili

### Firenze
_DSM e DTM LiDAR 2023 a 0,5 m del Comune: il riferimento migliore d'Italia; ~2 GB. Dettagli: `documenti/CITTA_RIFERIMENTO_MILANO_FIRENZE_ROMA.md`._

1. Apri <https://dati.toscana.it/dataset/dsm-lidar-2023> («DSM 2023», Comune di Firenze, licenza cc-by-4.0), risorsa
   «MDS LIDAR 2023 ASCII» → **Vai alla risorsa** (porta a
   <https://datigis.comune.fi.it/grid/MDS_LIDAR_2023_ASCII.zip>). Salva in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\firenze\MDS_LIDAR_2023_ASCII.zip` (**1,04 GB**).
2. Apri <https://dati.toscana.it/dataset/dtm-lidar-2023>, risorsa «MDT LIDAR 2023 ASCII» (link diretto
   <https://datigis.comune.fi.it/grid/MDT_LIDAR_2023_ASCII.zip>). Salva in `…\citta_rif\firenze\MDT_LIDAR_2023_ASCII.zip`
   (**0,92 GB**).
3. Se vuoi estrarre solo l'area di prova, apri lo zip con Esplora risorse o 7-Zip (è in Deflate64) e copia le 20 tessere
   elencate nel documento di Firenze (§ 3.2) in `…\citta_rif\firenze\dsm\` e `…\dtm\`; altrimenti lascia gli zip interi.
4. Edifici: scarica lo zip regionale
   <https://www502.regione.toscana.it/geoscopio/download/dbtopografico/edificato/edificato_2k_10k_1988_2013.zip>
   (dalla Cartoteca di Geoscopio, voce dell'edificato) in `…\citta_rif\firenze\edificato_2k_10k_1988_2013.zip`
   (**531 MB**, tutta la Toscana, SpatiaLite in EPSG:3003; dentro `_leggimi.txt` con i campi e `licenza_ccby_40.pdf`).
   È facoltativo: il server può prendere Firenze dal WFS.
5. Facoltativo (seconda fonte di DSM, fotogrammetrica 2021): apri <https://www502.regione.toscana.it/geoscopio/cartoteca.html>,
   in «Morfologia» accendi «DSM (da autocorrelazione di immagini) anno 2021», clicca sull'elemento e poi su **[ DSM ]**;
   oppure usa direttamente i link `…/DSM_autocorrelazione_2021/DSM_275031.zip`, `DSM_275032.zip`, `DSM_275043.zip`,
   `DSM_275044.zip`, `DSM_263152.zip`, `DSM_263163.zip` (6 × ~22 MB) e salvali in `…\citta_rif\firenze\dsm2021\`.

### Genova
_LiDAR comunale 2018 a 0,5 m e carta tecnica DXF; ~140 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_NORD.md`._

1. Scarica DSM e DTM a 0,5 m delle tavole **3931, 3831, 3723, 3721** (link diretti, nessun login):
   `https://mappe.comune.genova.it/gis/rilievo/01_DSM_50CM_REV/DSM3931.asc` e
   `https://mappe.comune.genova.it/gis/rilievo/02_DTM_50CM_REV/DTM3931.asc`, e lo stesso con 3831, 3723, 3721. Salva in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\genova\dsm\` e `…\genova\dtm\` (**8 file, ~110 MB**).
   In alternativa apri la mappa <https://mappe.comune.genova.it/MapStore2/#/viewer/1000003072>, accendi «2018-20 – 50 CM
   quadro unione», clicca sulla tavola e usa i link del riquadro informativo.
2. Scarica la Carta Tecnica Comunale 2018 in DXF delle tavole 1:2.000 **3930** e **3830** (e 3720 per Lanterna e
   Matitone): `https://mappe.comune.genova.it/gis/rilievo/CAD/DXF/2000/3930.zip`, `…/3830.zip`, `…/3720.zip` in
   `…\genova\ctc_dxf\` (**28 MB**; 3930 si espande a 159 MB).
3. Non scaricare i LAS (quasi 1 GB a tavola): non servono.

### Trento
_Edifici P.A.T. 3D e LiDAR 2014/2018; ~230 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_NORD.md`._

1. Scarica <https://siatservices.provincia.tn.it/idt/vector/p_TN_6a7806d8-63fa-4445-b009-9412c99d8fd2.zip> (Edifici
   P.A.T. 3D, **108 MB**, nessun login) in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\trento\edifici_pat_3d.zip`.
2. Per le 8 tessere `5h664551020`, `5h664551025`, `5h665051020`, `5h665051025` (ospedale S. Chiara) e `5h663551030`,
   `5h663551035`, `5h664051030`, `5h664051035` (centro, Duomo, MUSE) scarica DTM e DSM First, per esempio
   <https://siatservices.provincia.tn.it/stemdata/2014_lidar_dtm_asc/5h665051025_DTM.asc> e
   <https://siatservices.provincia.tn.it/stemdata/2014_lidar_dsmfirst_asc/5h665051025_DSMFirst.asc> (cambia il nome
   della tessera). Salva in `…\trento\dtm\` e `…\trento\dsm\` (**16 file, ~120 MB**). Le cartelle si aprono anche nel
   browser come elenco di file.
3. Facoltativo: le stesse 8 tessere del DBM (`…/2014_lidar_dbm_asc/<tessera>_DBM.asc`, ~60 MB) in `…\trento\dbm\`.

### Potenza
_DBGT con altezze, DSM e DTM 5 m; ~125 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_CENTRO.md`._

1. Edifici: scarica <https://rsdi.regione.basilicata.it/downloadProd/dbgt_ctr_comune_download/17076063.zip> (DBGT del
   Comune di Potenza, **89,5 MB**, nessun login) e salvalo in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\potenza\17076063.zip`. Per EuGEnio bastano
   `unita_volumetrica_17076063.*`, `edifici_is_17076063.*` e `informazioni_e_precisazioni.pdf` (licenza).
2. Facoltativo (unità volumetriche **con la Z** della base, tutta la regione): <https://rsdi.regione.basilicata.it/webGis/shape-zip/unita_volumetrica.zip>
   (**71,5 MB**) in `…\citta_rif\potenza\unita_volumetrica_regione.zip`.
3. DSM e DTM 5 m della città: incolla nel browser questi due indirizzi (ognuno scarica un GeoTIFF di **~17 MB**) e salva
   come `…\citta_rif\potenza\dsm5_potenza.tif` e `dtm5_potenza.tif`:
   - `https://rsdi.regione.basilicata.it/rbgeoserver2016/rsdi_wcs/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageId=rsdi_wcs__dsm_5m&format=image/tiff&subset=E(563000,573000)&subset=N(4495000,4504000)`
   - lo stesso con `coverageId=rsdi_wcs__dtm_5m`.
4. Non serve altro: il server può rifare tutto da solo (vedi il documento della città).

### Palermo
_unità volumetriche con gronda; 16 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_SUD_ISOLE.md`._

1. Apri <https://opendata.comune.palermo.it/opendata-dataset.php?dataset=1294> («CARTA TECNICA COMUNALE – UNITA'
   VOLUMETRICHE», licenza CC BY 4.0) e premi **Scarica il file SHP** (link diretto
   <https://opendata.comune.palermo.it/js/server/uploads/dataset/shp/_09062021064719.zip>).
2. Salva in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\palermo\unita_volumetriche_7792.zip`
   (**16 MB**; dentro `VOLUMETRIE_7792.shp/.dbf/.shx/.prj`).
3. Facoltativo (CTR regionale con le gronde, tutta la Sicilia): apri
   <https://www.sitr.regione.sicilia.it/download/download-carta-tecnica-regionale-10000/ata1213-shape/> e scarica
   **«B_Edificato [157 MB]»** (<https://www.sitr.regione.sicilia.it/wp-content/uploads/CTR_ATA_2012_2013_B_Edificato.zip>,
   164 MB) in `…\citta_rif\palermo\CTR_ATA_2012_2013_B_Edificato.zip`. Non serve per il server, che interroga il servizio.
4. **Non** comprare né chiedere ancora il DTM/DSM ATA 2 m: aspettare la risposta alla lettera al SITR (vedi il documento della città).

### Milano
_DBT 2020 con le altezze; 597 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_MILANO_FIRENZE_ROMA.md`._

1. Apri <https://dati.comune.milano.it/dataset/ds2889_database-topografico-dbt-2020-shp>.
2. Nella sezione «Dati e risorse» scegli **DS2889_DBT_2020.zip** (RDN2008 / UTM 32N, EPSG:7791; non la versione
   Gauss-Boaga) e premi **Scarica** (link diretto:
   <https://gisportal.comune.milano.it/download/area_download/SIT/DBT2020/DBT_2020.zip>).
3. Salva in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\milano\DBT_2020.zip` (**597 MB**).
4. Non serve estrarre tutto: per EuGEnio bastano, dalla cartella `DBT 2020 - SHAPE/`, i file `UN_VOL.*`,
   `EDIFC*.*`, `EDI_MIN*.*` e (per il terreno) `PT_QUO.*`, più i due PDF `Catalogo_Dati_Territoriali_*.pdf` (specifiche).

### Cagliari
_LiDAR 2008 a 1 m; ~55 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_SUD_ISOLE.md`._

1. Scarica le tessere LiDAR 2008 (nessun login; ogni link scarica uno zip con un `.ASC`), in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\cagliari\dtm\`, `…\dsm\` e `…\dsm_edifici\`:
   - DTM: `https://webgis.regione.sardegna.it/scaricocartografiaETL/modelliDigitali/Fascia_costiera_2008_DTM1m/<tessera>.ZIP`
   - DSM: `https://webgis.regione.sardegna.it/scaricocartografiaETL/modelliDigitali/Fascia_costiera_2008_DSM1m/<tessera>.ZIP`
   - DSM edifici: `https://webgis.regione.sardegna.it/scaricocartografiaETL/modelliDigitali/Fascia_costiera_2008_DSM1m/<tessera>_BUILDINGS.ZIP`

   con `<tessera>` = **557100_22, 557140_12, 557140_13, 557140_17, 557140_18** (15 file, circa **50 MB** in tutto).
   In alternativa, dalla mappa <https://www.sardegnageoportale.it/webgis2/sardegnamappe/?map=download_raster>, livello
   «modello digitale passo 1 m fascia costiera 2008», clic sulla tessera.
2. Edifici del riquadro di Cagliari in Shapefile (un solo link, ~3–4 MB [D]):
   `https://webgis.regione.sardegna.it/geoserver/dbu/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=dbu:dbgt_10k_22_v05_02_edificio_massima_estensione&outputFormat=SHAPE-ZIP&srsName=EPSG:7791&bbox=504000,4335000,516000,4350000,EPSG:7791`
   → salva come `…\citta_rif\cagliari\dbgt10k_edifici_cagliari.zip`. È facoltativo: il server lo prende da solo.

### Bari
_CTR 2006 con quote di gronda e DTM 8 m; ~26 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_CENTRO.md`._

1. Apri <http://www.sit.puglia.it/portal/portale_cartografie_tecniche_tematiche/Download/Cartografie>, scegli il foglio
   **«438 – Bari»** e, alla riga «Carta Tecnica Regionale formato Shape», **Vai al dettaglio**.
2. Scarica `438073_ctr.zip`, `438074_ctr.zip`, `438072_ctr.zip`, `438061_ctr.zip`, `438062_ctr.zip` (link diretti
   `http://cartografia.sit.puglia.it/download/CTR/SHP/438/4380xx_ctr.zip`; **23,5 MB** in tutto) in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\bari\ctr\`.
3. Torna al foglio 438, riga «Digital Terrain Model» → **Vai al dettaglio**, e scarica gli stessi elementi
   (`4380xx_asc.zip`, **2,0 MB** in tutto) in `…\citta_rif\bari\dtm8\`.

### Ancona
_DBT 2019 con quote di gronda; ~110 MB + Repertorio. Dettagli: `documenti/CITTA_RIFERIMENTO_CENTRO.md`._

1. Scarica <https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/edificio.zip> (**51 MB**) e
   <https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/punto_quotato.zip> (**56 MB**) in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\ancona\dbgt2019\`. Sono di tutta la regione.
2. Apri <https://www.regione.marche.it/Regione-Utile/Ambiente/Cartografia-e-informazioni-territoriali/Repertorio>,
   sezione «Banche dati» → «Edificato 1:10.000»: scarica **Edificato-2019.zip** e **Edificato-2019-Specifiche.pdf** in
   `…\citta_rif\ancona\edificato2019\` (annota la dimensione: dal container non si è potuta leggere).
3. Nella stessa pagina, sezione «DTM» → «DTM 10m (2019)»: scarica **Orografia-2019-DTM.zip** (o `.tif`) e
   **Orografia-2019-Specifiche.pdf** in `…\citta_rif\ancona\dtm10\`.

## B. Portali da aprire nel browser (qualche clic in più)

### Roma
_DBGT 2014 Lazio con altezze, dal File Browser regionale; 582 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_MILANO_FIRENZE_ROMA.md`._

1. Apri <https://dati.lazio.it/catalog/it/dataset/2014-carta-tecnica-regionale-numerica-scala-1-5-000-provincia-di-roma>
   (licenza cc-by4) e clicca la risorsa **«DBGT 5K formato SHP»**: si apre il «File Browser» della Regione
   (<https://geoportale.regione.lazio.it/cartografia/2014_DBGT_5K_SHP/strati-informativi/Roma/>, nessun login).
2. Seleziona **`DBT_Lazio_RM374.zip`** (foglio 374 «Roma», **582 MB**) e premi l'icona **Scarica** (freccia verso il
   basso in alto a destra). Salva in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\roma\DBT_Lazio_RM374.zip`.
3. Per EuGEnio bastano, dalla cartella `DBT_Lazio_RM374/`, `UN_VOL.*`, `EDIFC*.*`, `EDI_MIN*.*` (e `PT_QUO.*` per il
   terreno).
4. Facoltativo, solo se la Regione conferma la licenza dell'edizione 2020: nella stessa pagina del File Browser risali
   a `/cartografia/2020_DBGT_5K_SHP/` e scarica **`Roma.zip`** (**1,19 GB**, tutto il comune) in
   `…\citta_rif\roma\2020\Roma.zip`.
5. Facoltativo (terreno vecchio, 5 m): da `/cartografia/2002_2003_DTM_5MT_DXF/Roma/` scarica `374062_dtm.zip`,
   `374064_dtm.zip`, `374073_dtm.zip`, `374101_dtm.zip`, `374141_dtm.zip`, `374142_dtm.zip`, `374143_dtm.zip`
   (7 × ~4 MB) in `…\citta_rif\roma\dtm5\`.

### Napoli
_DBT e DTM 2020 dalla cartella SharePoint della Regione; 175 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_SUD_ISOLE.md`._

1. Apri <https://sit.regione.campania.it/carta-tecnica-regionale> e clicca la **mappa interattiva per il download**
   (oppure direttamente la cartella del comune di Napoli:
   <https://regionecampania.sharepoint.com/:f:/s/50-09-92-CTR2020/EoXurF7CRjZIt-QGFwPwDtUBr_zC71u6aA_c4IjjI-4eYA>;
   SharePoint si apre senza login).
2. Nella cartella «Napoli» seleziona **`DBT_5K.zip`** (**154 MB**) e premi **Scarica**. Salva in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\napoli\DBT_5K.zip`.
3. Nella stessa cartella scarica **`DTM_5k.zip`** (**21 MB**) in `…\citta_rif\napoli\DTM_5k.zip`.
4. Per EuGEnio bastano, dalla cartella `DBT/` dello zip, `EDIFC.*`, `EDIFC_CR_EDF_IS.*`, `EDIFC_CR_EDF_ME*.*`,
   `EDIFC_EDIFC_USO.dbf`, `EDIFC_EDIFC_NOME.dbf`, `EDI_MIN*.*`, `PT_QUO.*` e la cartella `domini/`.
5. Facoltativo: nella sottocartella `CTR_5k` c'è la CTR 2020 (`SHP.zip` 80 MB, `DWG_3D.zip` 130 MB): non serve per le
   altezze.

### Torino
_BDTRE del comune dal geoportale regionale; da annotare. Dettagli: `documenti/CITTA_RIFERIMENTO_NORD.md`._

1. Apri <https://www.geoportale.piemonte.it> e cerca «BDTRE»; nella scheda della BDTRE scegli lo **scarico per comune**,
   comune **Torino (001272)**, formato SHP, sistema **EPSG:32632**. Salva lo zip in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\torino\bdtre\` (dimensione [D]: annotala). Se il nome del
   file segue il modello del 2015 (`…GAIMSDWL-001272-EPSG32632-SHP.zip`), annota anche l'URL: il server lo potrà
   riscaricare da solo.
2. Dentro lo zip controlla che ci sia `UN_VOL` (o il tema 0201 «Edificato») e annota i nomi dei campi d'altezza
   (`UN_VOL_AV`, `UN_VOL_QE` come in Lombardia e Lazio?) e la licenza indicata nel pacchetto.
3. Apri <https://geoportale.comune.torino.it>, sezione «Dati di base» / «Carta Tecnica»: se lo zip
   `carta_tecnica.zip` si scarica **senza login**, salvalo in `…\citta_rif\torino\comune\` e annota la dimensione; se
   chiede credenziali, fermati (non è un dato aperto scaricabile) e annotalo.
4. Dal geoportale regionale, «Scarico – Ripresa Aerea ICE 2009-2011 – DTM5» e «DSM»: scarica le tavole che coprono le Molinette (EPSG:32632 395100–396100 E,
   4987600–4988800 N) e Mole e grattacieli (394400–397500 E, 4991000–4992000 N) in `…\citta_rif\torino\ice\` (facoltativo: sono a 5 m).

### Trieste
_LiDAR 2017-2020 da Eagle.fvg come ospite; da annotare. Dettagli: `documenti/CITTA_RIFERIMENTO_NORD.md`._

1. Apri <https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest> (accesso ospite, nessuna registrazione),
   funzione di scarico delle basi cartografiche, rilievo **LiDAR RAFVG 2017-2020**: scarica **DTM 0,5 m** e **DSM primo
   ritorno 0,5 m** (quote **ortometriche**) delle tavole che coprono Cattinara (EPSG:6708 408300–408900 E, 5053700–5054300 N) e il
   centro (404700–405300 E, 5055500–5056100 N). Salva in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\trieste\lidar\` e annota nomi e dimensioni delle tavole.
   Se l'applicazione chiede una registrazione, fermati e annotalo.
2. Nessun download per gli edifici: il server li prende dal WFS.

## C. Solo verifiche (annotare cosa c'è, scaricare solo se è aperto)

### Venezia
_portale del Comune; —. Dettagli: `documenti/CITTA_RIFERIMENTO_NORD.md`._

1. Dal browser apri <https://dati.venezia.it> e <https://geoportale.comune.venezia.it> (dal container sono bloccati):
   cerca «carta tecnica», «DBT», «edifici», «LiDAR», «DSM». Se c'è un DBT con unità volumetriche o altezze, o un DSM,
   **senza login**, annota pagina, licenza e dimensione e salva il file in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\venezia\comune\`.
2. Se non trovi altezze aperte, Venezia resta solo per le sagome: nessun altro download.

### Perugia
_UmbriaGeo; —. Dettagli: `documenti/CITTA_RIFERIMENTO_CENTRO.md`._

1. Dal browser (in Italia), apri <http://www.umbriageo.regione.umbria.it/pagina/distribuzione-carta-tecnica-regionale-vettoriale-1-001>
   e scarica la **CTR 1:2.000 del centro di Perugia** in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\perugia\ctr2k\`;
   copia anche la licenza o la pagina delle condizioni.
2. Apri `…/pagina/distribuzione-carta-tecnica-regionale-10k-esito-gr` e scarica le sezioni 10k che coprono Perugia
   (CTR 10k Tevere-Trasimeno 2013) in `…\citta_rif\perugia\ctr10k_2013\`.
3. Annota per ognuno: formato, dimensione, sistema di riferimento e se gli edifici hanno **quote di gronda/piede o
   altezze** (è l'informazione che manca per decidere se Perugia è utilizzabile).

### Catanzaro
_geoportale della Calabria; —. Dettagli: `documenti/CITTA_RIFERIMENTO_SUD_ISOLE.md`._

1. Dal tuo browser apri <https://geoportale.regione.calabria.it/opendata> («Repertorio cartografico»): annota se la CTR
   1:5.000 (2008) e il DTM 5×5 m si scaricano senza registrazione, in che formato e con quale licenza; se sì, scarica gli
   elementi che coprono l'ospedale Pugliese-Ciaccio (EPSG:7792 636700–637700 E, 4308700–4309600 N) e Germaneto
   (635500–637000 E, 4302000–4303500 N) in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\catanzaro\`.
   Se chiede login o registrazione, fermati e annotalo.

### L'Aquila
_solo schede e quadro d'unione; pochi kB. Dettagli: `documenti/CITTA_RIFERIMENTO_CENTRO.md`._

1. Niente da scaricare in modo aperto oggi. Scarica solo la scheda del DTM 10 m e il quadro d'unione da
   <http://geoportale.regione.abruzzo.it/Cartanet/pages4home/modello_digitale_terreno/modello-digitale-terreno-10-m>
   (link «Apri scheda Metadati» e «quadro d'unione») in `…\citta_rif\laquila\documenti\`.
2. La lettera alla Regione Abruzzo (già pronta) va integrata con la richiesta del DBTI 2007 e del DTM 10 m (vedi il documento della città).

## D. Facoltativo

### Bolzano
_il server prende tutto da solo dai servizi della Provincia; 4 × 9,4 MB. Dettagli: `documenti/CITTA_RIFERIMENTO_NORD.md`._

Nessun download necessario: tutto è nei servizi. Facoltativo, per avere i file sul PC, apri nel browser e salva in
`C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\bolzano\` (4 file da 9,4 MB):
`https://geoservices9.civis.bz.it/geoserver/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageId=p_bz-Elevation__DigitalElevationModel-0.5m&format=image/tiff&subset=E(677000,677600)&subset=N(5151700,5152300)`
e lo stesso con `DigitalTerrainModel-0.5m` e con il riquadro del Duomo (`E(680300,680900)`).

## E. Dopo il 10/11/2026: PST del MASE (LiDAR nazionale)

App: <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new> → «Seleziona area» sul riquadro indicato → se compaiono «DSM
FIRST LiDAR 1 m» e «DTM LiDAR 1 m» della regione, aggiungili al carrello e «Scarica tutto» in `…\citta_rif\<città>\pst\`.

- **Palermo**: nell'app PST «Seleziona area» su 13,33–13,38 E / 38,09–38,13 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Sicilia» e «DTM LiDAR 1 m», scarica DSM FIRST e DTM in `…\citta_rif\palermo\pst\`.
- **Milano**: apri <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>, «Seleziona area» sul riquadro 9,18–9,21 E / 45,48–45,52 N, guarda se tra i livelli c'è «DSM FIRST LiDAR 1 m – Regione Lombardia»; se sì, aggiungi al carrello **DSM FIRST** e **DTM** 1 m, «Scarica tutto» e salva gli ZIP in `…\citta_rif\milano\pst\`. Se l'area non è coperta, annotalo: Milano resta senza DSM aperto.
- **Bari**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona area» su 16,84–16,89 E / 41,10–41,14 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Puglia» e «DTM LiDAR 1 m», aggiungili al carrello, «Scarica tutto» e salva in `…\citta_rif\bari\pst\`. Senza copertura, Bari resta senza DSM.
- **Ancona**: PST su 13,45–13,53 E / 43,59–43,63 N, DSM FIRST e DTM 1 m in `…\citta_rif\ancona\pst\`.
- **Roma**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona area» su 12,42–12,52 E / 41,81–41,94 N; se compaiono i livelli «DSM FIRST LiDAR 1 m – Regione Lazio» e «DTM LiDAR 1 m», aggiungi al carrello DSM FIRST e DTM, «Scarica tutto» e salva in `…\citta_rif\roma\pst\`. Senza copertura, Roma resta senza DSM aperto fino al LiDAR PNRR.
- **Napoli**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona area» su 14,20–14,30 E / 40,83–40,88 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Campania» e «DTM LiDAR 1 m», aggiungili al carrello, «Scarica tutto» e salva in `…\citta_rif\napoli\pst\`.
- **Torino**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona area» su 7,66–7,72 E / 45,03–45,08 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Piemonte» e «DTM 1 m», scarica le celle in `…\citta_rif\torino\pst\`.
- **Trieste**: PST, celle 13,74–13,84 E / 45,62–45,68 N, DSM FIRST 2 m e DTM, in `…\trieste\pst\` (solo se Eagle non va).
- **Venezia**: nell'app PST «Seleziona area» su 12,30–12,36 E / 45,42–45,45 N (centro storico) e 12,21–12,24 E / 45,50–45,52 N
  (Ospedale dell'Angelo); se c'è un DSM FIRST 1 m o 2 m, scaricalo in `…\citta_rif\venezia\pst\`.
- **Perugia**: PST su 12,35–12,45 E / 43,07–43,12 N; se copre il centro o l'ospedale, DSM FIRST e DTM 1 m in `…\citta_rif\perugia\pst\`.
- **Catanzaro**: nell'app PST «Seleziona area» su 16,56–16,60 E / 38,86–38,93 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Calabria» e «DTM LiDAR 1 m», scarica DSM FIRST e DTM in `…\citta_rif\catanzaro\pst\`.
- **L'Aquila**: PST su 13,33–13,42 E / 42,33–42,38 N; se copre il centro, DSM FIRST e DTM 1 m in `…\citta_rif\laquila\pst\`. Con il PST L'Aquila avrebbe almeno il controllo DSM − DTM con le altezze di OSM.
