# Città di riferimento: Milano, Firenze, Roma – fonti, licenze e istruzioni di download

Verifica dell'08/11/2026, fatta dal container di sviluppo senza login, account o captcha e senza aggirare blocchi.
Nessun file di `/home/claude/eu` è stato modificato: le prove sono in `/home/claude/citta_rif/` (`prove/`, `script/`).
Legenda: **[V]** verificato con una prova dal vivo o letto su una pagina ufficiale; **[D]** dedotto o da confermare.

Scopo: tre città con edifici noti dove confrontare **sagome e altezze dei DB topografici** con **DSM − DTM** (LiDAR o
fotogrammetria), per controllare che gli adattatori regionali funzionino e per dare a tutti dei riferimenti noti.
Cartella dei download di Paolo: `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\<città>\`.

## 1. In breve

| Città | Edifici con altezze | DTM | DSM | Valore come riferimento |
|---|---|---|---|---|
| **Firenze** | Regione Toscana, unità volumetriche «multiscala» (CTR 1:2.000 del 2011 in città), CC BY 4.0, **WFS provato** e zip regionale | Comune di Firenze, **LiDAR 27/06/2023, 0,5 m**, CC BY 4.0 | Comune di Firenze, **LiDAR 2023, 0,5 m**, CC BY 4.0 (anche DSM regionale 2021, 1 m) | **Il migliore**: due fonti indipendenti e recenti. Prova sul Duomo: DSM − quota di gronda, mediana +0,8 m, scarto < 2 m nell'86 % dei volumi |
| **Milano** | DBT 2020 del Comune (1:1.000, volo marzo-aprile 2020), CC BY 4.0, SHP con **UN_VOL** identico al DBGT regionale | Regione Lombardia DTM 5 m (servizio provato); punti quotati del DBT 2020 | **nessun DSM aperto**: solo PST MASE 1 m (2008-13, copertura da verificare dopo il 10/11) e, in futuro, LiDAR PNRR | Buono per le **sagome e le altezze** (1:1.000), debole per il controllo indipendente: il DBGT regionale di Milano **è** il DBT comunale (stessi identificativi e valori) |
| **Roma** | Regione Lazio **DBGT 2014** (SHP per foglio 1:50.000, CC BY 4.0) e DBGT 2020 per comune (licenza da confermare); UN_VOL con altezze | Regione Lazio DTM 5 m 2002-03 (DXF per elemento); punti quotati e curve del DBGT | **nessun DSM aperto** regionale o comunale: solo PST MASE (Tevere, da verificare) e LiDAR PNRR in futuro | Utile per provare un **terzo formato** di DB topografico; contenuto vecchio (80 % dei volumi dal volo 2002-03, 20 % aggiornati 2014, < 1 % 2023) |

Novità rispetto a `fonti/regioni.toml` e a `LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
- **Lazio**: il DBGT 2014 **con le unità volumetriche e le altezze** (`UN_VOL_AV`, `UN_VOL_QE`) è già scaricabile in
  Shapefile da `geoportale.regione.lazio.it/cartografia` (licenza `cc-by4` su dati.lazio.it), e c'è anche un **DBGT
  2020** per comune (Roma.zip, 1,19 GB). La lettera alla Regione Lazio va ridotta alla conferma della licenza
  dell'edizione 2020 e della versione della CC BY. [V]
- **Toscana**: le unità volumetriche «multiscala» (CTR 2k/10k, 1988-2013) sono scaricabili in blocco (zip SpatiaLite
  di 531 MB con `licenza_ccby_40.pdf`) e interrogabili via **WFS** (`ms:rt_edif.unitavolumetriche`); solo la nuova
  versione «al 2023» è consultabile ma non scaricabile (WMS `rt_edificato`). La lettera alla Toscana resta valida
  solo per la versione 2023. [V]
- **Toscana DSM 2021**: download diretto per elemento 1:5.000 con URL fisso
  `…/geoscopio/download/altimetria/DSM_autocorrelazione_2021/DSM_<elemento>.zip` (≈ 22 MB, ASCII 1 m, EPSG:7791,
  con `licenza_CCBY40_7791.pdf` nello zip): il server può scaricarlo da solo. [V]
- **Comune di Milano**: DBT 2020 in SHP (597 MB) e FeatureServer ArcGIS pubblico (`DBGT/Milano_2020_DBGT`, strato 30
  «Unità volumetrica»), stessi campi dell'adattatore `lombardia_dbgt`. [V]
- **Comune di Firenze**: DSM e DTM LiDAR 2023 a 0,5 m (zip di 1,04 e 0,92 GB, 484 tessere ASCII di 500 m). [V]

## 2. Milano

### 2.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Comune di Milano – Database Topografico (DBT) 2020**, strato 02 Immobili: `UN_VOL` (237.743 unità volumetriche), `EDIFC`, `EDI_MIN`, `PT_QUO` | volo marzo/aprile 2020 | 1:1.000 | Shapefile, **RDN2008/UTM 32N (EPSG:7791)** (c'è anche la versione Gauss-Boaga, EPSG:3003, 435 MB) | dataset: «Creative Commons Attribution» (`cc-by`); piè di pagina del portale: «i contenuti del sito sono soggetti alla licenza Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)» | download diretto (zip unico) | **596.533.009 byte** (zip); `UN_VOL.shp` 96 MB + `.dbf` 100 MB | [V] zip letto a distanza (indice e intestazioni): campi `UN_VOL_QE, UN_VOL_POR, CLASSID, UN_VOL_AV, UN_VOL_EX, CEDIUV, SCRIL`, `.prj` EPSG:7791 |
| Edifici (servizio) | Comune di Milano – FeatureServer `DBGT/Milano_2020_DBGT`, strato **30** «020101 – Unità volumetrica (fino a 1:2000)» | 2020 | 1:1.000 | ArcGIS REST, EPSG:7791, `hasZ` | come sopra | **automatico**, `maxRecordCount` 2000, solo `Query` | — | [V] Porta Nuova (515500–516000 E, 5036600–5037100 N): 635 volumi; Pirellone `un_vol_av` 125,5 m (alto 127 m); Torre Galfa 105,8 m; Niguarda fino a 34,6 m |
| Edifici (regionale) | Regione Lombardia – DBGT, classe 020101 Unità volumetrica (già nel progetto, adattatore `lombardia_dbgt`) | consegna 10/03/2023 (`COD_CONS`) | come il comunale | ArcGIS REST | CC BY 4.0 (scheda RNDT `r_lombar:3493af32-…`) | automatico | — | [V] stesso riquadro: **635 volumi, stessi `CLASSID`, `CEDIUV`, `UN_VOL_AV`, `UN_VOL_QE`** del comunale → a Milano il DBGT regionale è il DBT 2020 del Comune |
| DTM | Regione Lombardia – **DTM 5×5 m (ed. 2015)** | 2015 | 5 m | ImageServer `arcgis2/…/BaseMap/DTM5_RL_img` (F32, EPSG:32632) o zip regionale | CC BY 4.0 (scheda RNDT `r_lombar:dfc98d60-…`) | **automatico** con `exportImage` (o zip `DTM5_RL.zip`, 3.085.490.651 byte) | ritaglio 1,5×1,5 km: 591 kB | [V] `exportImage` 300×300 in EPSG:7791 su Porta Nuova: 200 image/tiff, quote 105,5–140,0 m |
| DTM (alternativa) | DBT 2020 – `PT_QUO` (punti quotati) | 2020 | 1:1.000 | Shapefile EPSG:7791 | come il DBT | nello zip del DBT | 231 MB dbf + 31 MB shp | [V] presente nell'indice dello zip |
| DSM | **Nessun DSM aperto** del Comune o della Regione | — | — | — | Regione: «Copertura rilievi LiDAR» con copyright (già in `regioni.toml`); rilievo LiDAR del gemello digitale di Milano (Leica CityMapper-2, articolo Remote Sensing 2023): nessuna pubblicazione né licenza | — | — | [V] CKAN del Comune: 0 risultati per DSM, DTM, LiDAR |
| DSM (nazionale) | PST MASE – «DSM FIRST/LAST LiDAR 1 m – Regione Lombardia» (`m_amte:299FN3:84a24090-…`) | 2008-2013 | 1 m | GeoTIFF, EPSG:4326, celle 0,01° | CC BY 4.0 (pagina «Distribuzione dati PST» e note legali del Geoportale) | a mano dall'app PST (offline fino al 10/11/2026) | ~ 2–5 MB a cella [D] | [V] WMS `LIDAR_LOMBARDIA.map` risponde ma GetMap vuoto ovunque (manutenzione); **copertura di Milano da verificare** (il PST copre aste fluviali e coste: forse Lambro/Seveso/Olona) |

### 2.2 Area di prova

- **Porta Nuova – Pirellone – Palazzo Lombardia**: riquadro EPSG:7791 **514600–516000 E, 5036400–5037300 N**
  (Pirellone 515716/5036816, Torre UniCredit 514872/5036770, Bosco Verticale 514864/5036914, Palazzo Lombardia
  515285/5037038).
- **Ospedale di Niguarda**: 514200–514900 E, 5039300–5040000 N.
- PST (se copre): celle 0,01° tra **9,18–9,21 E, 45,48–45,52 N**.

### 2.3 Istruzioni per Paolo

1. Apri <https://dati.comune.milano.it/dataset/ds2889_database-topografico-dbt-2020-shp>.
2. Nella sezione «Dati e risorse» scegli **DS2889_DBT_2020.zip** (RDN2008 / UTM 32N, EPSG:7791; non la versione
   Gauss-Boaga) e premi **Scarica** (link diretto:
   <https://gisportal.comune.milano.it/download/area_download/SIT/DBT2020/DBT_2020.zip>).
3. Salva in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\milano\DBT_2020.zip` (**597 MB**).
4. Non serve estrarre tutto: per EuGEnio bastano, dalla cartella `DBT 2020 - SHAPE/`, i file `UN_VOL.*`,
   `EDIFC*.*`, `EDI_MIN*.*` e (per il terreno) `PT_QUO.*`, più i due PDF `Catalogo_Dati_Territoriali_*.pdf` (specifiche).
5. **Dopo il 10/11/2026** (app PST di nuovo online): apri <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>,
   «Seleziona area» sul riquadro 9,18–9,21 E / 45,48–45,52 N, guarda se tra i livelli c'è «DSM FIRST LiDAR 1 m –
   Regione Lombardia»; se sì, aggiungi al carrello **DSM FIRST** e **DTM** 1 m, «Scarica tutto» e salva gli ZIP in
   `…\citta_rif\milano\pst\`. Se l'area non è coperta, annotalo: Milano resta senza DSM aperto.

### 2.4 Cosa può fare il server da solo

- Sagome e altezze: `python -m edifici3d --zona lombardia regionale-campione --riquadro 514600 5036400 516000 5037300
  --max 5000 --uscita milano_pn.geojson` (servizio regionale già nel progetto) oppure lo stesso dal FeatureServer
  comunale (`…/DBGT/Milano_2020_DBGT/FeatureServer/30/query`, `outFields=*`, `returnZ=true`, pagine da 2000).
- Lo SHP del Comune entra con il comando già documentato
  `python -m edifici3d --zona lombardia prepara-regione --file UN_VOL.shp --archivio … --comune milano --istat 015146`
  (stessi campi del DBGT: nessun adattatore nuovo).
- DTM: `exportImage` del DTM 5 m Lombardia sul riquadro (provato), senza scaricare lo zip regionale da 3,1 GB.

## 3. Firenze

### 3.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Toscana – Edificato multiscala, unità volumetriche** (`uv_av` altezza del volume, `uv_qe` quota di estrusione, `uv_qs` quota al suolo, tipologia e uso) | a Firenze **volo 08/03/2011** (`dtvolo` 20110308, `scala` 02 = CTR 1:2.000) | 1:2.000 in città, 1:10.000 altrove | WFS MapServer (GML 3.1.1, **EPSG:3003**; GeoJSON non ammesso) o zip SpatiaLite EPSG:3003 | scheda RNDT `r_toscan:c3e27a3a-…`: «La risorsa è liberamente accessibile e usabile con licenza CC BY»; nello zip `licenza_ccby_40.pdf`; WFS: Fees e AccessConstraints «none» | **automatico** (WFS, 3.000 oggetti per richiesta) o zip regionale | zip **530.630.969 byte** (SpatiaLite 2,05 GB, tutta la Toscana) | [V] Duomo: 154 volumi in 200×200 m; cupola `uv_av` 112,57 m (`uv_qe` 161,03), campanile 84,96 m (reale 84,7); Careggi: 316 volumi, «Sede di ospedale» fino a 37,7 m |
| Edifici (2023) | Regione Toscana – «Edificato – unità volumetriche al 2023» (v. 1.0, ott. 2026) | 2023 | 1:10.000 | solo WMS `ows_ricomposizione_ctr` strato `rt_edificato` | CC BY (scheda `r_toscan:294be9db-…`) | **non scaricabile** (WFS 400): già chiesto con la lettera alla Regione | — | [V] |
| DTM | **Comune di Firenze – DTM 2023** (LiDAR del 27/06/2023) | 2023 | **0,5 m**, tessere 500×500 m | ASCII Grid (`.ASC`), nomi `32_<E>_<N>`; **sistema reale RDN2008/UTM 32N (EPSG:7791)**: la scheda dice «ROMA40/OVEST», ma le coordinate coincidono con EPSG:7791 (lanterna del Duomo trovata a 11,25695 E, 43,77312 N) | dati.toscana.it, dataset `dtm-lidar-2023` del Comune di Firenze: `license_id` **cc-by-4.0** | download diretto (zip unico) | **922.675.701 byte**, 484 tessere da ~7 MB (≈ 3,4 GB estratti) | [V] intestazione letta: NCOLS 1000, CELLSIZE 0,500; zip in **Deflate64** (si apre con Esplora risorse di Windows, 7-Zip o `unzip`; non con `zipfile` di Python) |
| DSM | **Comune di Firenze – DSM 2023** (stesso rilievo LiDAR) | 2023 | **0,5 m** | come il DTM | `dsm-lidar-2023`: **cc-by-4.0** | download diretto | **1.038.346.174 byte** | [V] tessera `32_681500_4849000`: massimo 162,47 m sulla lanterna, DTM 48,46 m → **114,0 m** (cupola 114,5 m) |
| DSM (2ª fonte) | Regione Toscana – **DSM 2021** (autocorrelazione di immagini, IRS, voli 20/07–21/08/2021) | 2021 | 1 m, per elemento 1:5.000 | ASCII, EPSG:7791 | scheda RNDT `r_toscan:c5c907bf-…`: «liberamente accessibile e usabile con licenza CC BY»; nello zip `licenza_CCBY40_7791.pdf` | download diretto per elemento: `https://www502.regione.toscana.it/geoscopio/download/altimetria/DSM_autocorrelazione_2021/DSM_<elemento>.zip`; quadro d'unione WFS `rt_cartoteca.lidar2k_DSM_autocorrelazione_2021` (mappa `wmscartoteca`) | ~ 22 MB per elemento (69 MB estratti) | [V] elementi 275031, 275032, 275043, 275044 (centro), 263152, 263163 (Careggi); 3 zip provati (21,4–22,4 MB) |
| DTM/DSM regionali LiDAR | Regione Toscana – LiDAR 1:2.000 (centro di Firenze: rilievo **2007**, 1 m, EPSG:3003) | 2007 | 1 m | ASCII | CC BY (cartoteca) | download per tavola dalla cartoteca | — | [V] link dal GetFeatureInfo (`…/altimetria/lidar/dsm/19k53_1x1_dsm_011_2007_3003_….zip`): **troppo vecchio**, non serve |
| DSM/DTM PST | PST MASE Toscana 1 m (2008-2015) | — | 1 m | GeoTIFF | CC BY 4.0 | app PST | — | non serve a Firenze (c'è il LiDAR 2023) |

**Prova di coerenza (08/11/2026, tessera del Duomo, 94 volumi ≥ 30 m² con sagoma ristretta di 1 m)** [V]:

| Misura | Mediana | MAE | \|d\| < 2 m | \|d\| > 5 m |
|---|---|---|---|---|
| DSM 2023 mediana − `uv_qe` (quota di estrusione 2011) | +0,79 m | 1,59 m | 86 % | 7 % |
| DSM 2023 p90 − `uv_qe` | +1,62 m | 2,63 m | 60 % | 10 % |
| DTM 2023 mediana − `uv_qs` (quota al suolo) | +0,23 m | 0,33 m | 100 % | 0 % |

Le due fonti sono indipendenti (CTR 2011 contro LiDAR 2023), nello stesso sistema dopo la conversione 3003 → 7791, e
d'accordo come in Romagna (DBTR contro DSM 2019): Firenze è la città di riferimento più solida. Gli scarti grandi sono i
volumi delle cupole (DSM sopra la gronda) e un volume di 58,8 m con DSM a 127–137 m (sagoma che tocca la cupola).

### 3.2 Area di prova

- **Centro storico – Duomo – Palazzo Vecchio**: EPSG:7791 **680500–682500 E, 4848000–4850000 N** (Duomo 681638/4849150,
  Palazzo Vecchio 681583/4848739); in EPSG:3003 circa 1680530–1682530 E, 4848015–4850015 N.
- **Ospedale di Careggi** (in collina): EPSG:7791 **680500–681200 E, 4852200–4852900 N**.
- Tessere LiDAR comunali (500 m, nome = angolo sud-ovest): centro `32_680500…682000_4848000…4849500` (16 tessere),
  Careggi `32_680500_4852000`, `32_680500_4852500`, `32_681000_4852000`, `32_681000_4852500`.

### 3.3 Istruzioni per Paolo

1. Apri <https://dati.toscana.it/dataset/dsm-lidar-2023> («DSM 2023», Comune di Firenze, licenza cc-by-4.0), risorsa
   «MDS LIDAR 2023 ASCII» → **Vai alla risorsa** (porta a
   <https://datigis.comune.fi.it/grid/MDS_LIDAR_2023_ASCII.zip>). Salva in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\firenze\MDS_LIDAR_2023_ASCII.zip` (**1,04 GB**).
2. Apri <https://dati.toscana.it/dataset/dtm-lidar-2023>, risorsa «MDT LIDAR 2023 ASCII» (link diretto
   <https://datigis.comune.fi.it/grid/MDT_LIDAR_2023_ASCII.zip>). Salva in `…\citta_rif\firenze\MDT_LIDAR_2023_ASCII.zip`
   (**0,92 GB**).
3. Se vuoi estrarre solo l'area di prova, apri lo zip con Esplora risorse o 7-Zip (è in Deflate64) e copia le 20 tessere
   elencate al § 3.2 in `…\citta_rif\firenze\dsm\` e `…\dtm\`; altrimenti lascia gli zip interi.
4. Edifici: scarica lo zip regionale
   <https://www502.regione.toscana.it/geoscopio/download/dbtopografico/edificato/edificato_2k_10k_1988_2013.zip>
   (dalla Cartoteca di Geoscopio, voce dell'edificato) in `…\citta_rif\firenze\edificato_2k_10k_1988_2013.zip`
   (**531 MB**, tutta la Toscana, SpatiaLite in EPSG:3003; dentro `_leggimi.txt` con i campi e `licenza_ccby_40.pdf`).
   È facoltativo: il server può prendere Firenze dal WFS.
5. Facoltativo (seconda fonte di DSM, fotogrammetrica 2021): apri <https://www502.regione.toscana.it/geoscopio/cartoteca.html>,
   in «Morfologia» accendi «DSM (da autocorrelazione di immagini) anno 2021», clicca sull'elemento e poi su **[ DSM ]**;
   oppure usa direttamente i link `…/DSM_autocorrelazione_2021/DSM_275031.zip`, `DSM_275032.zip`, `DSM_275043.zip`,
   `DSM_275044.zip`, `DSM_263152.zip`, `DSM_263163.zip` (6 × ~22 MB) e salvali in `…\citta_rif\firenze\dsm2021\`.

### 3.4 Cosa può fare il server da solo

- **Edifici**: WFS `https://www502.regione.toscana.it/ows2/com.rt.wms.RTmap/wms?map=owsedificato`,
  `service=WFS&version=1.1.0&request=GetFeature&typeName=ms:rt_edif.unitavolumetriche&bbox=<x0,y0,x1,y1>,EPSG:3003`
  (GML, 3.000 oggetti per richiesta: riquadri da 500 m nel centro). Serve un **adattatore nuovo** `toscana_uv` (mappa
  semplice: `uv_av` → altezza, `uv_qe` gronda, `uv_qs` terreno, `edifc_id`/`edi_min_id` → edificio, `uv_por` porzione,
  `edifc_duso` uso; EPSG:3003 → 7791).
- **DSM/DTM 2023**: scaricare i due zip dagli URL diretti (nessun login; risposta 206 alle richieste Range, quindi si
  possono anche leggere solo le tessere servite, come ho fatto qui) ed estrarre con `7z` o `unzip` (Deflate64).
- **DSM 2021**: elenco degli elementi dal WFS del quadro d'unione (`map=wmscartoteca`, `typename=rt_cartoteca.lidar2k_DSM_autocorrelazione_2021`,
  campo `elemento`), poi `DSM_<elemento>.zip`.

## 4. Roma

### 4.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Lazio – DBGT 2014** («2014 Carta Tecnica Regionale Numerica scala 1:5.000 – Provincia di Roma», risorsa «DBGT 5K formato SHP»), file per foglio 1:50.000: **`DBT_Lazio_RM374.zip`** (foglio 374 «Roma») | contenuto: volo 2002-03 aggiornato al 2014 (`DATA_AGG`: 223.903 volumi 2003, 56.994 2014) | 1:5.000 | Shapefile **PolygonZ**, `.prj` «ETRS_1989_UTM_Zone_33N» (EPSG:25833; la Regione dichiara RDN2008/UTM 33N, EPSG:7792: differenza di centimetri) | dati.lazio.it: `license_id` **cc-by4**; schede RNDT delle classi DBGT v. 2014: «Unico vincolo: nominare la fonte del dato» | download diretto per foglio dal «File Browser» pubblico della Regione | **581.835.243 byte** (RM374); `UN_VOL.shp` 125 MB + `.dbf` 134 MB | [V] `UN_VOL`: 280.897 volumi, campi `CLASSID, COD_ISTAT, DATA_AGG, FONTE, LIVELLO, UN_VOL_AV, UN_VOL_POR, UN_VOL_QE, CEDIUV, SCALA`; nessuna altezza ≤ 0; mediana 7,95 m; Torre Europarco 111,3 m (alta 120 m) |
| Edifici (2020) | Regione Lazio – **DBGT 2020**, Shapefile per comune: **`Roma.zip`** | aggiornamenti 2023 su pochi oggetti (2.901 volumi su 386.769) | 1:5.000 | come sopra (PolygonZ, UTM 33N) | **non scritta** per l'edizione 2020 (nessun pacchetto su dati.lazio.it, nessun file di licenza nello zip): per analogia CC BY 4.0 [D], **da confermare** | download diretto | **1.190.275.164 byte**; `UN_VOL` 166 + 199 MB | [V] 386.769 volumi in tutto il comune; Gemelli fino a 46,0 m, Umberto I 35,2 m, Palazzo della Civiltà 60,2 m (alto 68 m) |
| DTM | Regione Lazio – **DTM 5 m da CTRN 2002-03**, per elemento 1:5.000 | 2002-03 | 5 m | DXF (punti, ~50 MB per elemento) | dati.lazio.it «Creative Commons Attribution» (`cc-by`, versione non indicata) | download diretto per elemento | ~4 MB per zip; foglio 374 intero: 64 zip, 258 MB | [V] `374101_dtm.zip` → `374101_dtm.dxf` (AutoCAD R14); vecchio e scomodo: solo ripiego |
| DTM (alternativa) | DBGT 2014/2020 – `PT_QUO` (punti quotati) e curve di livello (`DBT_Contours_RM374.zip`, 77 MB) | 2003/2014 | 1:5.000 | Shapefile | come il DBGT | nello zip / cartella `curve-di-livello` | `PT_QUO.dbf` 356 MB (RM374) | [V] |
| DSM | **Nessun DSM aperto** della Regione Lazio o di Roma Capitale | — | — | — | Roma Capitale: «Atlante» e gemello digitale (voli 2022-2025, 5–7,5 cm) senza dati aperti né licenza; open data del Comune (365 dataset): nessun dato cartografico | — | — | [V] RNDT, GeoNode e CKAN regionali, CKAN di Roma Capitale |
| DSM (nazionale) | PST MASE – «DSM FIRST/LAST LiDAR 1 m – Regione Lazio» (`m_amte:299FN3:d53d84c9-…`) | 2008-2012 [D] | 1 m | GeoTIFF EPSG:4326 | CC BY 4.0 (PST) | a mano dall'app PST (offline fino al 10/11/2026) | ~ 2–5 MB a cella [D] | [V] WMS `LIDAR_LAZIO.map` attivo ma immagini vuote; quadro d'unione con errore PostGIS: **copertura del Tevere a Roma da verificare** |

Attenzione: **San Pietro e la Città del Vaticano non sono nel DBGT** (Stato estero): non usarli come riferimento.

### 4.2 Area di prova

Tutto nel **foglio 374** (estensione di `UN_VOL`: 12,333–12,665 E, 41,792–42,006 N) [V]. Elementi 1:5.000 dal WFS
regionale `geonode:qu_5k` [V]:

| Edificio | ETRS89/UTM 33N (E, N) | Elemento 5k | Sezione 10k |
|---|---|---|---|
| Colosseo, Fori | 291946, 4640627 | 374101 | 374100 «Roma Sud Ovest» |
| Pantheon (centro) | — | 374062 / 374101 | 374060 «Roma Nord Ovest» |
| Policlinico Umberto I | 293725, 4642408 | 374073 | 374070 «Roma Nord Est» |
| Policlinico Gemelli | 286840, 4645379 | 374064 | 374060 |
| EUR: Palazzo della Civiltà Italiana | 289671, 4634737 | 374141 | 374140 «E.U.R.» |
| EUR: Torre Eurosky, Torre Europarco | 289858, 4633175 | 374142, 374143 | 374140 |

Riquadri consigliati (EPSG:25833): centro **290500–294500 E, 4639500–4643500 N**; Gemelli **286300–287400 E,
4644800–4645900 N**; EUR **288800–290600 E, 4632600–4635300 N**. PST: celle 0,01° tra **12,42–12,52 E, 41,81–41,94 N**.

### 4.3 Istruzioni per Paolo

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
6. **Dopo il 10/11/2026**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona
   area» su 12,42–12,52 E / 41,81–41,94 N; se compaiono i livelli «DSM FIRST LiDAR 1 m – Regione Lazio» e «DTM LiDAR
   1 m», aggiungi al carrello DSM FIRST e DTM, «Scarica tutto» e salva in `…\citta_rif\roma\pst\`. Senza copertura, Roma
   resta senza DSM aperto fino al LiDAR PNRR.

### 4.4 Cosa può fare il server da solo

- Il File Browser della Regione è in modalità **senza autenticazione** («NoAuth»: il browser stesso riceve un gettone
  anonimo da `POST /cartografia/api/login` e scarica da `/cartografia/api/raw/<percorso>` con l'intestazione
  `X-Auth`). Con lo stesso meccanismo il server può scaricare `DBT_Lazio_RM374.zip` o leggerne solo i file `UN_VOL.*`
  con richieste Range (fatto qui: `UN_VOL.shp` 30,7 MB compressi, `.dbf` 4,8 MB). Nessun blocco aggirato, ma è un
  percorso non documentato: se la Regione aggiunge un login, si torna al download a mano.
- Quadri d'unione: WFS anonimo `https://geoportale.regione.lazio.it/geoserver/ows`, strati `geonode:qu_5k`,
  `geonode:qu_10k`, `geonode:qu_50k` (JSON, EPSG:4326), Fees e AccessConstraints «NONE».
- Il DBGT Lazio ha **gli stessi nomi di campo** del DBGT Lombardia (`UN_VOL_AV`, `UN_VOL_QE`, `UN_VOL_POR`, `CEDIUV`)
  più `COD_ISTAT` e `DATA_AGG`: l'adattatore `lombardia_dbgt` va quasi bene, serve una zona `lazio` (EPSG:25833/7792,
  porzione `08` da decodificare con il catalogo, `DATA_AGG` come anno del dato) [D].
- Non c'è un servizio WFS degli edifici: il GeoServer regionale pubblica solo `geonode:wms_edi_min_a` (edifici minori).

## 5. Cosa non è disponibile o non è compatibile

| Città | Dato | Motivo |
|---|---|---|
| Milano | DSM del Comune o della Regione | non pubblicato (Regione: copyright; gemello digitale del Comune: nessuna licenza) |
| Milano | edifici «indipendenti» dal DBGT | il DBGT regionale coincide con il DBT 2020 comunale (verificato su 635 volumi): il confronto prova la pipeline, non il dato |
| Firenze | Edificato al 2023 | solo WMS: download non previsto (lettera alla Regione già pronta) |
| Firenze | LiDAR regionale del centro | rilievo 2007: superato dal LiDAR comunale 2023 |
| Roma | DSM regionale o comunale | non esiste in open data; Atlante di Roma Capitale senza dati aperti |
| Roma | DBGT 2020 | licenza non scritta per l'edizione 2020 (da confermare; la 2014 è cc-by4) |
| Roma | San Pietro, Vaticano | fuori dal DBGT (Stato estero) |
| tutte | PST MASE | app offline fino al 10/11/2026, WMS con immagini vuote, quadro d'unione con errore del database: copertura non verificabile oggi |
| tutte | LiDAR PNRR 25 cm | non ancora pubblicato (verifica del 08/11/2026 in `LIDAR_MASE_VERIFICA_2026-11-08.md`) |

Nessuna fonte trovata ha licenza incompatibile (NC, SA o «tutti i diritti riservati») tra quelle proposte; le licenze sono
tutte CC BY 4.0, salvo il DBGT Lazio 2020 (non scritta) e il DTM Lazio 2002-03 (`cc-by` senza versione).

## 6. Ordine consigliato e spazio

| Ordine | Cosa | Dove | Dimensione |
|---|---|---|---|
| 1 | Firenze DSM 2023 + DTM 2023 | `citta_rif\firenze\` | 1,04 + 0,92 GB |
| 2 | Firenze edificato regionale (facoltativo: c'è il WFS) | `citta_rif\firenze\` | 0,53 GB |
| 3 | Milano DBT 2020 (EPSG:7791) | `citta_rif\milano\` | 0,60 GB |
| 4 | Roma DBGT 2014 foglio 374 | `citta_rif\roma\` | 0,58 GB |
| 5 | (dopo il 10/11) PST Milano e Roma, se coprono | `citta_rif\<città>\pst\` | qualche decina di MB [D] |
| — | facoltativi: DSM Toscana 2021 (6 elementi), DTM Lazio 5 m (7 elementi), DBGT Lazio 2020 Roma | | 0,13 + 0,03 + 1,19 GB |

Totale essenziale: **circa 3,7 GB** (2,1 GB senza l'edificato toscano e con Roma solo il foglio 374).

## 7. Da aggiornare nel progetto (non fatto qui: `/home/claude/eu` è in modifica da un altro lavoro)

- `fase10-edifici3d/fonti/regioni.toml`:
  - **Lazio / edifici**: da «CTRN 2002-2003 DXF; DBGT 2014» a **DBGT 2014 SHP per foglio, UN_VOL con `UN_VOL_AV`,
    `UN_VOL_QE`**, licenza cc-by4 (dati.lazio.it), `prova` = indice e `UN_VOL.dbf` del foglio RM374 letti l'08/11/2026;
    stato «in attesa» solo per la zona e l'adattatore.
  - **Toscana / edifici**: aggiungere «Edificato multiscala» con WFS `owsedificato` (`ms:rt_edif.unitavolumetriche`,
    `uv_av`, `uv_qe`, `uv_qs`) e zip regionale; licenza CC BY 4.0 (pdf nello zip); stato «in attesa» per l'adattatore.
  - **Toscana / dsm**: DSM 2021 con URL per elemento (download provato) → può passare ad «attiva»; aggiungere la fonte
    comunale **Firenze LiDAR 2023** (DSM e DTM 0,5 m, CC BY 4.0).
  - **Lombardia / edifici**: annotare che a Milano il DBGT coincide con il DBT 2020 del Comune (SHP e FeatureServer).
  - **Lombardia / dtm**: aggiungere l'ImageServer `DTM5_RL_img` (`exportImage` provato).
- `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md`: lettera **Lazio** da ridurre (il DBGT 2014 si scarica; chiedere solo la
  licenza scritta dell'edizione 2020 e la versione della CC BY del DTM 2002-03); lettera **Toscana** solo per la
  versione 2023.
- `DA_FARE.md`: «Città di riferimento» con i passi del § 6 e, dopo il 10/11, la verifica della copertura PST a Milano e
  Roma.

## 8. Prove dal vivo (08/11/2026)

| Prova | Esito |
|---|---|
| CKAN `dati.comune.milano.it` (`package_search`, `package_show`) | 200; DBT 2020 SHP, licenza `cc-by`; pagine HTML del portale 403 senza User-Agent di un browser, 200 con |
| Indice a distanza di `DBT_2020.zip` (Range sulla directory centrale) e lettura di `UN_VOL.prj`/`.dbf` | 1.754 voci; EPSG:7791; 237.743 volumi |
| FeatureServer `DBGT/Milano_2020_DBGT/30/query` e DBGT regionale sullo stesso riquadro | 635 volumi in entrambi, attributi identici |
| `DTM5_RL_img/ImageServer/exportImage` (TIFF F32, EPSG:7791) | 200 image/tiff, 591 kB |
| `sim.mase.gov.it`, WMS `LIDAR_{LOMBARDIA,TOSCANA,LAZIO}.map` GetMap, `QU_Lidar.map` GetFeatureInfo | GetCapabilities 200, immagini vuote, errore PostGIS |
| CKAN `dati.toscana.it` e redirect `data.comune.fi.it` → `datigis.comune.fi.it/grid/*.zip` | 302 → 206; zip in Deflate64; tessera del Duomo letta e confrontata |
| WFS `owsedificato` (`DescribeFeatureType`, `GetFeature` GML in EPSG:3003) | 200; 154 volumi al Duomo, 316 a Careggi |
| WFS `ows_ricomposizione_ctr` (Edificato 2023) | 400 (solo WMS) |
| Cartoteca: preset Geoscopio, WFS del quadro DSM 2021, GetFeatureInfo HTML, zip `DSM_2750xx.zip` | link di download trovato e provato (206) |
| CKAN `dati.lazio.it`, File Browser `geoportale.regione.lazio.it/cartografia` (API in modalità NoAuth), WFS `geonode:qu_5k` | DBGT 2014/2020 elencati; `UN_VOL` di RM374 e di Roma 2020 letti per intero con Range; elementi 5k trovati |
| CKAN `dati.comune.roma.it` (365 dataset) | nessun dato cartografico |
| CSW RNDT `geodati.gov.it/RNDT/csw` | schede PST per Lombardia, Toscana, Lazio; DSM 2021 Toscana; DBGT 2014 Lazio |

Script delle prove: `script/zipindice.py` (indice di uno zip remoto), `script/zipparziale.py` (una voce di uno zip remoto,
anche Deflate64 con il pacchetto `inflate64`; i file grezzi scaricati per le prove sono stati cancellati), `script/csw.py` e `script/cswrec.py` (ricerca e schede RNDT).

## 9. Fonti

Milano
- DBT 2020 SHP: <https://dati.comune.milano.it/dataset/ds2889_database-topografico-dbt-2020-shp> – file
  <https://gisportal.comune.milano.it/download/area_download/SIT/DBT2020/DBT_2020.zip>
- Pagina del portale con la licenza CC BY 4.0: <https://dati.comune.milano.it/about>
- FeatureServer del DBT: <https://gisportal.comune.milano.it/federated/rest/services/DBGT/Milano_2020_DBGT/FeatureServer/30>
- DBGT regionale: <https://geodati.gov.it/resource/id/r_lombar:3493af32-587c-4bca-92a4-ea717ea1a617>,
  <https://www.cartografia.servizirl.it/arcgis5/rest/services/BaseMap/DBGT_Tema0201_Edificato/MapServer/0>
- DTM 5 m: <https://geodati.gov.it/resource/id/r_lombar:dfc98d60-5f02-4a2b-8113-5ad24cc53a9c>,
  <https://www.cartografia.servizirl.it/arcgis2/rest/services/BaseMap/DTM5_RL_img/ImageServer>
- Gemello digitale (LiDAR CityMapper-2, non aperto): <https://doi.org/10.3390/rs15215263>

Firenze
- DSM 2023: <https://dati.toscana.it/dataset/dsm-lidar-2023>; DTM 2023: <https://dati.toscana.it/dataset/dtm-lidar-2023>
- File: <https://datigis.comune.fi.it/grid/MDS_LIDAR_2023_ASCII.zip>, <https://datigis.comune.fi.it/grid/MDT_LIDAR_2023_ASCII.zip>
- Edificato multiscala: <https://geodati.gov.it/resource/id/r_toscan:c3e27a3a-c62d-48f3-9cd7-738b6e96b6c9>, zip
  <https://www502.regione.toscana.it/geoscopio/download/dbtopografico/edificato/edificato_2k_10k_1988_2013.zip>, WFS
  <https://www502.regione.toscana.it/ows2/com.rt.wms.RTmap/wms?map=owsedificato&service=WFS&request=GetCapabilities>
- Edificato al 2023: <https://www502.regione.toscana.it/geonetwork/srv/api/records/r_toscan:294be9db-ba10-4e2d-a890-89f87d00f30a>
- DSM 2021: <https://geodati.gov.it/resource/id/r_toscan:c5c907bf-50cc-4a76-8787-abc547509c8d>, quadro
  <https://geodati.gov.it/resource/id/r_toscan:11200544-5d90-4027-8624-d06802a95ffa>, cartoteca
  <https://www502.regione.toscana.it/geoscopio/cartoteca.html>

Roma
- DBGT 2014 provincia di Roma: <https://dati.lazio.it/catalog/it/dataset/2014-carta-tecnica-regionale-numerica-scala-1-5-000-provincia-di-roma>
- File Browser della Regione: <https://geoportale.regione.lazio.it/cartografia/2014_DBGT_5K_SHP/strati-informativi/Roma/>,
  <https://geoportale.regione.lazio.it/cartografia/2020_DBGT_5K_SHP/>
- CTRN e DTM 2002-03: <https://dati.lazio.it/catalog/it/dataset/carta-tecnica-regionale-2002-2003-5k-roma>
- Scheda RNDT di una classe DBGT 2014 («Unico vincolo: nominare la fonte del dato»):
  <https://geodati.gov.it/resource/id/r_lazio:8c4741fa-7bb4-4fee-beca-484b>
- Quadri d'unione WFS: <https://geoportale.regione.lazio.it/geoserver/ows?service=WFS&request=GetCapabilities>
- Open data di Roma Capitale: <https://dati.comune.roma.it/catalog>
- Atlante di Roma Capitale: <https://turismoroma.it/it/node/173226>; GEOmedia, «dal webGIS al Digital Twin»:
  <https://ojs.mediageo.it/index.php/GEOmedia/article/view/2169>

Nazionali
- PST MASE, distribuzione e licenza: <https://gn.mase.gov.it/portale/distribuzione-dati-pst>; app
  <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>; schede PST DSM 1 m: Lombardia
  <https://geodati.gov.it/resource/id/m_amte:299FN3:84a24090-2239-4e54-8764-8fa0a2e239a5>, Toscana
  <https://geodati.gov.it/resource/id/m_amte:299FN3:bbd58eb9-354c-4e0a-af2b-ff57e548f787>, Lazio
  <https://geodati.gov.it/resource/id/m_amte:299FN3:d53d84c9-75c5-44fb-9d7e-88f4b22db95f>
