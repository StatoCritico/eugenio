# Città di riferimento: Napoli, Palermo, Cagliari, Catanzaro – fonti, licenze e istruzioni di download

Verifica dell'08/11/2026, fatta dal container di sviluppo senza login, account o captcha e senza aggirare blocchi.
Nessun file di `/home/claude/eu` è stato modificato: le prove sono in `/home/claude/citta_rif2/` (`sud/`, `script/`).
Legenda: **[V]** verificato con una prova dal vivo o letto su una pagina ufficiale; **[D]** dedotto o da confermare.

Scopo: completare le città di riferimento (dopo Milano, Firenze e Roma) con quattro città del Sud e delle Isole, per
controllare **sagome e altezze dei DB topografici** contro **DSM − DTM** e per provare i formati delle Regioni
Campania, Sicilia, Sardegna e Calabria.
Cartella dei download di Paolo: `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\<città>\`.

## 1. In breve

| Città | Edifici con altezze | DTM | DSM | Valore come riferimento |
|---|---|---|---|---|
| **Palermo** | **Comune di Palermo, «Carta tecnica comunale – Unità volumetriche»** 1:2.000 (100.432 volumi con `QUOTA_GRON`, `QUOTA_PIED`, `ALTEZZA`, `VOLUME`), CC BY 4.0, SHP EPSG:7792, 16 MB | Regione Siciliana, MDT 2013 2 m (ImageServer, **licenza non chiara**: il DTM in file è a pagamento); `QUOTA_PIED` del Comune | **nessun DSM aperto** (SITR: DTM/DSM 2 m a 150 € per sezione); PST da verificare dopo il 10/11 | **Il migliore del Sud per le altezze**: due fonti quasi indipendenti (CTR regionale 2012-13 con le z di gronda e UN_VOL comunale) d'accordo: mediana +0,1 m all'Ospedale Civico. Manca un DSM per il controllo indipendente |
| **Cagliari** | Regione Sardegna, DBGT 10k 2022 (v05) – Edificio: **solo sagome** (z = 0), CC BY 4.0, **WFS provato** (499.171 edifici, anche in SHAPE-ZIP) | Regione Sardegna, **DTM LiDAR 2008, 1 m**, fascia costiera (tutta Cagliari), CC BY 4.0 | Regione Sardegna, **DSM LiDAR 2008, 1 m** + **DSM «buildings»** (solo edifici), CC BY 4.0, URL diretti per tessera | **Il migliore per DSM − DTM** (LiDAR completo e scaricabile in automatico), ma vecchio (2008) e senza altezze nel DB: le altezze vanno ricavate. Prova: Torre dell'Elefante 33,4 m (≈ 31 m), Torre di San Pancrazio 39,9 m (≈ 36 m) |
| **Napoli** | Regione Campania, **DBT 2020** (volo AGEA 2020, 1:5.000), CC BY 4.0: **sagome senza altezza** (la z dei vertici è la quota al piede, verificato contro il DTM: +0,3 m) | Regione Campania, **DTM 2020, 5 m**, CC BY 4.0, **ImageServer provato** (`exportImage`) e ASCII per comune | **nessun DSM aperto** (regionale o comunale); PST da verificare dopo il 10/11 | Utile per provare il **formato GeoUML/DBGT nazionale** (EDIFC + CR_EDF_IS PolygonZ) e il DTM; per le altezze servono LiDAR (PST, PNRR) o Zornade |
| **Catanzaro** | **non verificabile da qui**: geoportale regionale chiuso al container (connessione chiusa, robots.txt vieta WebFetch); scheda RNDT della CTR 1:5.000 sparita (errore 500); Comune: nessun dato cartografico aperto | [D] DTM 5×5 m regionale (FTP del geoportale, con credenziali: non usabile) | solo PST (aste fluviali e costa, da verificare dopo il 10/11) | **Debole**: da riprovare dal server o dal browser di Paolo; per ora solo PST e OSM/Zornade |

Novità rispetto a `fonti/regioni.toml` e a `LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
- **Palermo**: il Comune pubblica le **unità volumetriche 1:2.000 con le altezze** (`ALTEZZA`, `QUOTA_GRON`, `QUOTA_PIED`) in
  CC BY 4.0, scaricabili senza login (zip di 16,4 MB, EPSG:7792). [V]
- **Sicilia, CTR 2012-13**: lo strato «Edificato» ha **le z dei vertici alla quota di gronda** (verificato: z − `QUOTA_GRON`
  comunale, mediana +0,1/+0,8 m): l'altezza si ricava come z − DTM, come in Liguria. Interrogabile via ArcGIS REST
  (`ctr_2013_dbtrs/MapServer/35`) o scaricabile in blocco (164 MB). La maggior parte dei volumi è del rilievo **2003**
  (`ANNORILEV`). [V]
- **Sicilia, CART 2000 (1:2.000)**: strato `B_Edificato_B1_A` con **`quotaterra`, `quotagrond`, `volume`** su 2.728
  fogli dei centri minori (non Palermo, Catania, Messina), CC BY 4.0. [V]
- **Sicilia, DTM/DSM ATA 2 m**: in file sono **a pagamento** (150 € per sezione, pagina «Costi di cessione»), quindi
  fuori dalla CC BY del SITR; l'ImageServer `mdt_2013` risponde ma la licenza del servizio non è scritta. [V]
- **Sardegna**: DTM, DSM e **DSM degli edifici** LiDAR 2008 a 1 m con **URL diretti per tessera** nel WFS
  `dbu:QU2k_fasciacostiera2008_DTM_DSM1m` (lo stesso per i centri urbani interni 2013): il download è
  automatizzabile, al contrario di quanto scritto in `regioni.toml`. Il DBGT 10k 2022 si scarica per riquadro dal WFS
  (anche in SHAPE-ZIP) ma **non ha altezze**. [V]
- **Campania**: il DBT 2020 **non ha unità volumetriche né quote di gronda** (verificato su tutto il comune di Napoli:
  31.112 edifici); il DTM 2020 5 m è un ImageServer pubblico (EPSG:7792). I file sono su SharePoint con link anonimi
  per comune. [V]

## 2. Napoli

### 2.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Campania – DBT 2020**, file `DBT_5K.zip` del comune di Napoli: `EDIFC` (31.112 edifici, attributi `EDIFC_TY`, `EDIFC_STAT`, `EDIFC_SOT`), `EDIFC_CR_EDF_IS` (ingombro al suolo, **PolygonZ**), `EDIFC_CR_EDF_ME` (massimo estradosso, 2D), `EDIFC_CR_EDF_ME_SR` (porzioni), `EDIFC_EDIFC_USO`, `EDIFC_EDIFC_NOME`, `EDI_MIN`, `CS_EDI`, `PT_QUO`; progetto QGIS e domini | volo AGEA 2020 (campi `DATA_CRE`/`DATA_MOD` vuoti) | 1:5.000 | Shapefile, `.prj` «ETRS_1989_UTM_Zone_33N» (EPSG:25833; i servizi della Regione usano RDN2008/UTM 33N, EPSG:7792: differenza di centimetri) | pagina «Carta Tecnica Regionale»: «possono essere scaricati liberamente, con licenza d'uso CC-BY 4.0»; note legali: «messi a disposizione del pubblico con licenza Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)… indicazione della fonte (Geoportale Regione Campania)» | download per comune da SharePoint con **link anonimo** (cartella del comune) | **153.786.015 byte**; `EDIFC_CR_EDF_IS.shp` 18 MB | [V] **nessuna altezza**: z dei vertici di `CR_EDF_IS` = quota al piede (Centro Direzionale, 136 sagome: z − DTM mediana **+0,32 m**, p10/p90 −1,0/+3,4 m); `CR_EDF_ME` è 2D; nessuna classe `UN_VOL` |
| Edifici (servizio) | Regione Campania – MapServer `Amministrativo/CTR2020`, strato 4 «Poligoni» (CTR numerica con `tipo`/`descr`, es. 31110000 «Edificio civile», 3111000O «edificio ospedale») | 2020 | 1:5.000 | ArcGIS REST, `hasZ`, nativo EPSG:3857 (si interroga in 7792) | come sopra | **automatico** (`Query`, 2.000 oggetti) | — | [V] 508 poligoni nel riquadro del Centro Direzionale; z dei poligoni «Edificio civile» = terreno (CTR SHP dell'elemento 447123: z − DTM ≈ 0–4 m) |
| Edifici (CTR 3D) | Regione Campania – CTR 2020 `CTR_5k/DWG_3D.zip`, `SHP.zip` (rar per elemento: `POL`, `LIN`, `POI` PolygonZ) | 2020 | 1:5.000 | DWG / SHP | CC BY 4.0 | SharePoint | 130 MB (DWG 3D), 80 MB (SHP) | [V] SHP dell'elemento 447123 letto: edifici alla quota del terreno, «quota al suolo» come punti; nessuna quota di gronda. DWG 3D non aperto [D] |
| DTM | **Regione Campania – DTM 2020 (DTM5K)** | 2020 | **5 m** | ImageServer `Amministrativo/CTR_DTM5m` (F32, **EPSG:7792**); ASCII Grid per elemento 5k nel file `DTM_5k.zip` del comune | descrizione dell'elemento: «DTM della Carta tecnica regionale… aggiornato all'anno 2020»; licenza della pagina CTR (CC BY 4.0) | **automatico** con `exportImage` (nessun token) o zip per comune | ritaglio 1,5 × 1,5 km: 591 kB; `DTM_5k.zip` di Napoli **21.179.847 byte** (25 tessere `.asc`, ~3 MB l'una) | [V] `exportImage` 300×300 sul Centro Direzionale: quote 1,9–74,7 m; zip scaricato e letto (celle 5 m, `nodata` −9999, bordo a 0) |
| DTM (WCS) | `DG5009/CTR2020_DTM5K_tif/ImageServer/WCSServer` (indicato nel portale) | — | — | — | — | — | — | [V] 404: usare l'ImageServer |
| DSM | **Nessun DSM aperto** della Regione o del Comune | — | — | — | — | — | — | [V] portale ArcGIS regionale: 0 risultati per «DSM» e «LiDAR»; open data del Comune (CKAN): 0 dataset cartografici |
| DSM (nazionale) | PST MASE – «DSM FIRST LiDAR 1 m – Regione Campania» (`m_amte:299FN3:2a5efec9-…`), aste fluviali I–IV ordine (+ costa, scheda «AMP») | 2008-2013 [D] | 1 m (anche 2 m) | GeoTIFF | scheda RNDT: «distribuito con licenza CC BY 4.0» | a mano dall'app PST (offline fino al 10/11/2026) | ~ 2–5 MB a cella [D] | [V] WMS `LIDAR_CAMPANIA.map` risponde (6 strati), GetMap su Napoli vuoto come ovunque: **copertura da verificare** |

### 2.2 Area di prova

Riquadri in EPSG:7792 (RDN2008/UTM 33N; valgono anche per i file in EPSG:25833):

| Edificio | E, N | Elemento 5k (DTM/CTR) |
|---|---|---|
| **Ospedale Antonio Cardarelli** (35 edifici con uso 030102 nel DBT) | 434615, 4524087 | 447112 |
| **Centro Direzionale** (torri ENEL, Palazzo di Giustizia, Consiglio regionale) | 439455, 4523249 | 447123 |
| Maschio Angioino (centro) | 436997, 4521087 | 447164 |

Riquadri consigliati: Cardarelli **434100–434900 E, 4523800–4524500 N**; Centro Direzionale **439000–440000 E,
4522800–4523800 N**. PST: celle 0,01° tra **14,20–14,30 E, 40,83–40,88 N**.

### 2.3 Istruzioni per Paolo

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
6. **Dopo il 10/11/2026**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona
   area» su 14,20–14,30 E / 40,83–40,88 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Campania» e «DTM LiDAR 1 m»,
   aggiungili al carrello, «Scarica tutto» e salva in `…\citta_rif\napoli\pst\`.

### 2.4 Cosa può fare il server da solo

- **DTM**: `https://geomaps.regione.campania.it/server/rest/services/Amministrativo/CTR_DTM5m/ImageServer/exportImage?bbox=<x0,y0,x1,y1>&bboxSR=7792&imageSR=7792&size=<w,h>&format=tiff&pixelType=F32&f=image`
  (provato, nessun token).
- **Sagome**: query sul MapServer `federated/rest/services/Amministrativo/CTR2020/MapServer/4` (poligoni CTR con
  `tipo`), oppure lo zip per comune. I link per comune sono nello strato
  `…/Mappa_CTR2020___Link_Download_Comuni_MIL1/MapServer/0` (campi `dbt_5k`, `dtm`, `ctr_shp`, `ctr_3d`…; query per
  `COMUNE='Napoli'` provata).
- **Zip del DBT**: i link SharePoint sono anonimi: la prima richiesta al link imposta un cookie `FedAuth` «anonimo» (come
  in un browser), con cui il file risponde a richieste Range (fatto qui per leggere l'indice e i soli file degli
  edifici). Nessun blocco aggirato, ma è un percorso non documentato: se la Regione cambia le impostazioni di
  condivisione, si torna al download a mano.
- Formato: è il **DBGT nazionale (GeoUML) esportato in Shapefile**, con le geometrie in file separati
  (`EDIFC_CR_EDF_IS`, `_ME`, `_ME_SR`) legati da `CLASSREF` = `CLASSID` di `EDIFC`. Serve un adattatore `campania_dbt`
  (sagome e usi); l'altezza resta da LiDAR/Zornade/OSM.

## 3. Palermo

### 3.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Comune di Palermo – «Carta tecnica comunale – Unità volumetriche»** (dataset 1294): `VOLUMETRIE_7792` con `ID_UN_VOL`, **`QUOTA_GRON`**, **`QUOTA_PIED`**, **`ALTEZZA`**, `AREA`, `VOLUME` | copertura temporale dichiarata 2013 (pubbl. 07/06/2021); anno del volo non scritto [D] | 1:2.000 | Shapefile **PolygonZ**, **RDN2008/UTM 33N (EPSG:7792)** | scheda: «Quest'opera è distribuita con Licenza CC BY 4.0 IT»; catalogo DCAT: `creativecommons.org/licenses/by/4.0` | download diretto senza login | **16.428.234 byte** (zip); shp 39 MB + dbf 17 MB | [V] **100.432 volumi**, altezza mediana 7,6 m, p99 39,1 m, 70 con altezza 0; Ospedale Civico (938 volumi in 900×800 m) fino a 42,3 m; torre di Piazzale Ungheria **71,1 m**; ciminiera di Isola delle Femmine 127,5 m |
| Edifici (vecchia versione) | Comune di Palermo – dataset 269, `UNITA_VOLUMETRICA` | 2013 | 1:2.000 | Shapefile 2D, Monte Mario / Italy 2 (EPSG:3004) | CC BY 4.0 | download diretto | 9.980.595 byte | [V] 100.347 volumi, solo `TIPO_DI_PO` («AL SUOLO», «SOFFITTO DI PORTICO»…): **nessuna altezza**, superata dalla 1294 |
| Edifici (regionale) | **Regione Siciliana – CTR 1:10.000 ed. ATA 2012-2013**, strato «Edificato» (`CODICE` B001 «Edificio civile…», `ANNORILEV`) | `ANNORILEV`: in gran parte **2003**, aggiornamenti 2007 e 2012 | 1:10.000 | Shapefile PolygonZ ETRS89/UTM 33N (EPSG:25833) o ArcGIS REST `ctr_10000/ctr_2013_dbtrs/MapServer/35` (`hasZ`, 1.000 oggetti) | SITR, area download: «distribuiti secondo la Licenza Pubblica Creative Commons Attribuzione 4.0 Internazionale» (nota 1752 del 02/02/2021 per i dati «non sottoposti a costi di cessione») | **automatico** (query REST) o zip regionale `CTR_ATA_2012_2013_B_Edificato.zip` | **164.136.249 byte** (1.645.430 poligoni, shp 527 MB) | [V] **le z dei vertici sono alla quota di gronda**: contro `QUOTA_GRON` comunale mediana **+0,09 m** (Civico, 170 edifici) e +0,76 m (centro, 412) |
| Edifici (centri minori) | Regione Siciliana – **CART 2000 1:2.000**, `B_Edificato_B1_A` con `quotaterra`, `quotagrond`, `superficie`, `volume` | 2003 (volo CART 2000) | 1:2.000 | ArcGIS REST `ctn_2000/cart2000_dbtrs/MapServer/30` (EPSG:3004) e SHP | CC BY 4.0 (area download SITR) | automatico | — | [V] 2.728 fogli; **Palermo città non coperta** (solo Monreale, Isola delle Femmine, Villabate ai bordi) |
| DTM | Regione Siciliana – **MDT 2013** (ATA 2012-13) e MDT 2008 (ATA 2007-08) | 2013 / 2008 | **2 m** | ImageServer `modelli_digitali/mdt_2013` (F32, EPSG:25833, quote ortometriche) | **non scritta per il servizio**; in file (ASCII per sezione) sono **a pagamento**: «Modello digitale del terreno/ di superficie in formato Ascii (a sezione) Passo 2X2 Euro 150» | `exportImage` funziona senza token | ritaglio 900×800 m: 1,1 MB | [V] `QUOTA_PIED` − MDT 2013 mediana −0,22 m (Civico, 97 % entro 2 m) e −0,10 m (centro). **Da usare solo per prove interne finché il SITR non chiarisce la licenza** [D] |
| DTM (alternativa) | `QUOTA_PIED` delle unità volumetriche comunali; punti quotati CTR (strato H003) | 2013 | 1:2.000 | come sopra | CC BY 4.0 | come sopra | — | [V] |
| DSM | **Nessun DSM aperto**: il DSM ATA 2 m del SITR è a pagamento (stesso prezzo del DTM) | — | 2 m | ASCII | costi di cessione (esclusi dalla CC BY) | richiesta al SITR | — | [V] cartella `modelli_digitali` dell'ArcGIS del SITR: solo `mdt_2008`, `mdt_2013`, `mdt_40m_it2000` e pendenze |
| DSM (nazionale) | PST MASE – «DSM FIRST LiDAR 1 m – Regione Sicilia» (`m_amte:299FN3:5cebe64c-…`), aste fluviali I–IV ordine (+ costa, «AMP») | 2008-2013 [D] | 1 m | GeoTIFF | CC BY 4.0 (scheda RNDT) | app PST (offline fino al 10/11) | ~ 2–5 MB a cella [D] | [V] WMS `LIDAR_SICILIA.map` attivo, immagini vuote: **copertura di Palermo da verificare** (Oreto, costa) |

**Prova di coerenza (08/11/2026)** [V] (`script/pa_prova.py`):

| Riquadro (EPSG:7792) | Volumi comunali | `QUOTA_PIED` − MDT 2013 | z CTR 2012-13 − `QUOTA_GRON` |
|---|---|---|---|
| Ospedale Civico, 355600–356500 E, 4218150–4218950 N | 938 (altezza mediana 12,4 m, max 42,3) | mediana −0,22 m, MAE 0,52 m, 97 % entro 2 m | 170 edifici: mediana +0,09 m, MAE 2,18 m, 71 % entro 2 m, 11 % oltre 5 m |
| Centro (Teatro Massimo, Cattedrale, Piazzale Ungheria), 355500–356500 E, 4219500–4220700 N | 3.165 (mediana 13,6 m, max 71,1) | mediana −0,10 m, MAE 1,23 m, 80 % entro 2 m | 412 edifici: mediana +0,76 m, MAE 2,51 m, 65 % entro 2 m, 13 % oltre 5 m |

Le due fonti di edifici sono diverse (CTR regionale 1:10.000, quasi tutta del 2003, contro carta comunale 1:2.000) ma
non del tutto indipendenti (entrambe fotogrammetriche, forse con voli vicini) [D]: è un controllo di coerenza, non di
verità. Edifici noti nel dato comunale: Teatro Massimo fino a 46,6 m (gronda 65,9, piede 19,3), Cattedrale fino a 37,1 m,
torre di Piazzale Ungheria 71,1 m; le altezze reali non sono state trovate su fonti verificabili [D].

### 3.2 Area di prova

- **Ospedale Civico e Benefratelli** (38,1033 N, 13,3583 E): EPSG:7792 **355600–356500 E, 4218150–4218950 N**.
- **Centro storico** (Teatro Massimo 355998/4220426, Cattedrale 355890/4219773, torre di Piazzale Ungheria
  355804/4220566): **355500–356500 E, 4219500–4220700 N**.
- PST: celle 0,01° tra **13,33–13,38 E, 38,09–38,13 N**.

### 3.3 Istruzioni per Paolo

1. Apri <https://opendata.comune.palermo.it/opendata-dataset.php?dataset=1294> («CARTA TECNICA COMUNALE – UNITA'
   VOLUMETRICHE», licenza CC BY 4.0) e premi **Scarica il file SHP** (link diretto
   <https://opendata.comune.palermo.it/js/server/uploads/dataset/shp/_09062021064719.zip>).
2. Salva in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\palermo\unita_volumetriche_7792.zip`
   (**16 MB**; dentro `VOLUMETRIE_7792.shp/.dbf/.shx/.prj`).
3. Facoltativo (CTR regionale con le gronde, tutta la Sicilia): apri
   <https://www.sitr.regione.sicilia.it/download/download-carta-tecnica-regionale-10000/ata1213-shape/> e scarica
   **«B_Edificato [157 MB]»** (<https://www.sitr.regione.sicilia.it/wp-content/uploads/CTR_ATA_2012_2013_B_Edificato.zip>,
   164 MB) in `…\citta_rif\palermo\CTR_ATA_2012_2013_B_Edificato.zip`. Non serve per il server, che interroga il servizio.
4. **Non** comprare né chiedere ancora il DTM/DSM ATA 2 m: aspettare la risposta alla lettera al SITR (§ 7).
5. **Dopo il 10/11/2026**: nell'app PST «Seleziona area» su 13,33–13,38 E / 38,09–38,13 N; se compaiono «DSM FIRST
   LiDAR 1 m – Regione Sicilia» e «DTM LiDAR 1 m», scarica DSM FIRST e DTM in `…\citta_rif\palermo\pst\`.

### 3.4 Cosa può fare il server da solo

- **UN_VOL comunale**: download diretto dello zip (URL fisso, nessun login), poi un **adattatore nuovo** `palermo_uv`
  semplice: `ALTEZZA` → altezza, `QUOTA_GRON` gronda, `QUOTA_PIED` terreno, `ID_UN_VOL` → volume, nessun edificio padre
  (i volumi sono già separati). Sistema EPSG:7792.
- **CTR 2012-13 regionale** (tutta la Sicilia): query REST per riquadro su
  `https://map.sitr.regione.sicilia.it/gis/rest/services/ctr_10000/ctr_2013_dbtrs/MapServer/35/query` con
  `returnZ=true`, `outSR=25833`, pagine da 1.000; altezza = mediana delle z dei vertici − DTM. Stesso schema per i
  centri minori con la CART 2000 (`ctn_2000/cart2000_dbtrs/MapServer/30`, campi `quotagrond − quotaterra`).
- **DTM**: `exportImage` di `mdt_2013` funziona, ma va acceso solo dopo che il SITR conferma la licenza del servizio.

## 4. Cagliari

### 4.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Sardegna – DBGT 10k 2022 v05**, `dbu:dbgt_10k_22_v05_02_edificio_ingombro_suolo` e `…_edificio_massima_estensione` (campi `classid`, `stato`, `tipologia`, `uso`, `nome`, `monumental`, `porzione`) | DBGT10k «semplificato prodotto nel 2019… sulla base del volo aereo realizzato nel 2013»; edizione 2022 v05 [D sull'anno di aggiornamento] | 1:10.000 | WFS GeoServer 2.0.0, **EPSG:7791**, GeoJSON, GML o **SHAPE-ZIP** | scheda RNDT `R_SARDEG:2c842f2a-…`: `creativecommons.org/licenses/by/4.0`, «no limitations to public access»; WFS: Fees e AccessConstraints «NONE» | **automatico** (CountDefault 1.000.000) | SHAPE-ZIP del riquadro Brotzu (207 edifici): 41 kB | [V] **499.171 edifici** in regione, 17.935 nel riquadro di Cagliari; **z = 0 in tutti i vertici**: nessuna altezza |
| Edifici (2k comunali) | Regione Sardegna – «Database geotopografico scala 1:2.000… dei centri urbani», `DBGT2k_<mappa>.zip` | 2019 (mosaici) | 1:2.000 | **solo raster** TIFF | CC BY 4.0 (`R_SARDEG:969d4bc9-…`) | URL nel WFS `dbu:qu_dbgt2k_cu` | ~1,7 MB per mappa | [V] zip `DBGT2k_55714002.zip` letto: solo `.tif` e `.tfw`: non serve |
| DTM | **Regione Sardegna – DTM 1 m fascia costiera 2008** (LiDAR) | 2008 | **1 m**, tessere 1:2.000 (≈ 1.466 × 1.141 m) | ASCII Grid, **WGS84/UTM 32N** (nomi `*_WGS.ASC`, coordinate coincidenti con EPSG:7791 al metro) | scheda RNDT `R_SARDEG:BFPNM`: `creativecommons.org/licenses/by/4.0`, «no limitations to public access» | **URL diretti** dal WFS `dbu:QU2k_fasciacostiera2008_DTM_DSM1m` (campo `dtm`) | ~3,0 MB per tessera (10–12 MB estratti) | [V] 5 tessere scaricate; **103 tessere** nell'area di Cagliari |
| DSM | **Regione Sardegna – DSM 1 m fascia costiera 2008** (primo impulso) e **DSM «BUILDINGS»** (DSM sugli edifici, terreno altrove) e «VEGETATION» | 2008 | 1 m | come il DTM | come il DTM | URL diretti (campi `dsm`, `dsm_buildi`, `dsm_vegeta`) | ~3,3–3,5 MB per tessera e prodotto | [V] torri di Castello e Brotzu (sotto) |
| DTM/DSM (interno) | Regione Sardegna – DTM e DSM 1 m dei centri urbani interni, volo 2013 (`dbu:QU2k_DTM_DSM1m_centri_urbani_2013`) | 2013 | 1 m | ASCII | CC BY 4.0 (`R_SARDEG:7f606501-…`) | URL diretti | — | [V] non copre Cagliari (è costiera) |
| DSM (nazionale) | PST MASE – Sardegna 1 m | 2008 | 1 m | GeoTIFF | CC BY 4.0 | app PST | — | non serve: il LiDAR regionale 2008 copre già la città |

**Prova di plausibilità (08/11/2026, DSM 2008 − DTM 2008)** [V] (`script/ca_prova.py`):

| Edificio | Tessera | DSM max − DTM sotto | Altezza nota |
|---|---|---|---|
| Torre dell'Elefante (39,21796 N, 9,11490 E) | 557140_17 | **33,4 m** (36,8 m dal punto più basso intorno) | circa 31 m [D] |
| Torre di San Pancrazio (39,22151 N, 9,11700 E) | 557140_13 | **39,9 m** | circa 36 m [D] |
| Ospedale Brotzu, sagoma DBGT principale (17.455 m²) | 557100_22 | p99 **43,5 m**, mediana 5,0 m (corpo basso esteso) | da confermare [D] |
| 200 sagome DBGT ≥ 50 m² nel riquadro Brotzu | 557100_22 | mediana 9,0 m, p90 20,2 m; 8 sagome sotto 2 m (demolite, nuove o tettoie) | — |

Le torri risultano 2–4 m più alte del valore noto: il DSM prende il punto più alto (merli, antenne) e il DTM sotto le
torri è interpolato sul ciglio dei bastioni. È il comportamento atteso: Cagliari va usata come riferimento per il
**metodo DSM − DTM su sagome DB**, non come verità al metro sulle singole torri.

### 4.2 Area di prova

- **Ospedale Brotzu** (39,2510 N, 9,1075 E): EPSG:7791 **508800–509800 E, 4344300–4345200 N**; tessera LiDAR
  **557100_22**.
- **Castello – Via Roma** (Torre dell'Elefante 509919/4340971, Torre di San Pancrazio 510099/4341365): **509300–510600 E,
  4340300–4341800 N**; tessere **557140_12, 557140_13, 557140_17, 557140_18**.
- Sezione 10k 557140 «CAGLIARI» e 557100 «MONSERRATO».

### 4.3 Istruzioni per Paolo

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

### 4.4 Cosa può fare il server da solo

- **Tutto**: elenco delle tessere dal WFS `dbu:QU2k_fasciacostiera2008_DTM_DSM1m` (filtro per riquadro in EPSG:3003,
  campi `dtm`, `dsm`, `dsm_buildi` con gli URL), download degli zip, lettura degli ASCII; sagome dal WFS DBGT 10k per
  riquadro (GeoJSON in EPSG:7791). Altezza per sagoma = mediana o p90 di (DSM − DTM) dentro la sagoma ristretta di 1 m.
- Il WFS DBGT 10k è un candidato naturale per `sagome_regionali.toml` (sagome senza altezze, CC BY 4.0, WFS provato).
- Attenzione: i raster 2008 hanno 18 anni; gli edifici costruiti dopo risultano a quota terreno (8 su 200 al Brotzu).

## 5. Catanzaro

### 5.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | Regione Calabria – CTR 1:5.000 (scheda RNDT «Regione Calabria – Carta Tecnica Regionale 1:5000 CTR…», `r_calabr:00010:20140912:104758`) | 2008 [D] | 1:5.000 | [D] | **non letta** | geoportale regionale | — | [V] la scheda RNDT risponde con errore 500 (sparita); `geoportale.regione.calabria.it` chiude la connessione in HTTPS e dà 503 in HTTP; WebFetch rifiutato da robots.txt; il catalogo RNDT ha solo 4 schede `r_calabr` (uso del suolo) |
| Edifici (comunale) | Comune di Catanzaro | — | — | — | — | CKAN `opendata.comune.catanzaro.it` (16 dataset) | — | [V] 0 dataset cartografici; `sit.comune.catanzaro.it` non raggiungibile |
| DTM | [D] Regione Calabria – DTM 5×5 m («DTM5X5» sul geoportale) | [D] | 5 m | `.img` per elemento [D] | non trovata | FTP del geoportale **con credenziali** (lette in uno script di terzi: non usate) | — | non usabile finché la Regione non lo pubblica in modo anonimo |
| DSM | **nessuno** regionale o comunale trovato | — | — | — | — | — | — | — |
| DTM/DSM (nazionale) | PST MASE – «DSM FIRST LiDAR 1 m – Regione Calabria» (`m_amte:299FN3:1c04aa0a-…`), aste fluviali I–IV ordine (+ costa, «AMP») | 2008-2013 [D] | 1 m | GeoTIFF | CC BY 4.0 (scheda RNDT) | app PST (offline fino al 10/11) | — | [V] WMS `LIDAR_CALABRIA.map` attivo, immagini vuote: **copertura da verificare** (Fiumarella, Corace, Catanzaro Lido) |

### 5.2 Area di prova

Coordinate EPSG:7792 (RDN2008/UTM 33N):
- **Azienda ospedaliera Pugliese-Ciaccio** (38,9206 N, 16,5824 E): 637176, 4309156 → riquadro **636700–637700 E,
  4308700–4309600 N**.
- **Cittadella regionale** (Germaneto, 38,8623 N, 16,5701 E; edificio grande e noto) e AOU Mater Domini (Germaneto):
  636225, 4302664 → riquadro **635500–637000 E, 4302000–4303500 N** [D per il Mater Domini].
- Centro (Duomo, 38,9053 N, 16,5920 E): 638041, 4307470.
- PST: celle 0,01° tra **16,56–16,60 E, 38,86–38,93 N** (più la costa di Catanzaro Lido, 16,60–16,64 E, 38,81–38,84 N).

### 5.3 Istruzioni per Paolo

1. Dal tuo browser apri <https://geoportale.regione.calabria.it/opendata> («Repertorio cartografico»): annota se la CTR
   1:5.000 (2008) e il DTM 5×5 m si scaricano senza registrazione, in che formato e con quale licenza; se sì, scarica gli
   elementi che coprono i due riquadri del § 5.2 in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\catanzaro\`.
   Se chiede login o registrazione, fermati e annotalo.
2. **Dopo il 10/11/2026**: nell'app PST «Seleziona area» su 16,56–16,60 E / 38,86–38,93 N; se compaiono «DSM FIRST LiDAR
   1 m – Regione Calabria» e «DTM LiDAR 1 m», scarica DSM FIRST e DTM in `…\citta_rif\catanzaro\pst\`.

### 5.4 Cosa può fare il server da solo

- Oggi niente di regionale: riprovare dal server di Milano `geoportale.regione.calabria.it` (porta 443) con
  `python -m edifici3d regioni --prova`. Per gli edifici restano OSM e, quando arriva, l'estratto Zornade.

## 6. Cosa non è disponibile o non è compatibile

| Città | Dato | Motivo |
|---|---|---|
| Napoli | altezze nel DB topografico | DBT 2020 senza unità volumetriche né quote di gronda (z = quota al piede) |
| Napoli | DSM regionale o comunale | non pubblicato |
| Palermo | DTM e DSM ATA 2 m in file | a pagamento (150 € per sezione): esclusi dalla CC BY del SITR |
| Palermo | ImageServer MDT 2013 | licenza del servizio non scritta: solo prove interne finché il SITR non risponde |
| Palermo | CART 2000 1:2.000 | non copre la città |
| Cagliari | altezze nel DB topografico | DBGT 10k senza altezze (z = 0); DBGT comunali 2k solo raster |
| Cagliari | LiDAR recente | solo 2008 (fascia costiera); centri urbani 2013 solo nell'interno |
| Catanzaro | tutto il regionale | geoportale non raggiungibile né leggibile dal container; scheda RNDT della CTR sparita; DTM 5 m solo via FTP con credenziali |
| tutte | PST MASE | app offline fino al 10/11/2026, WMS con immagini vuote: copertura non verificabile oggi |
| tutte | LiDAR PNRR 25 cm | non ancora pubblicato (verifica in `LIDAR_MASE_VERIFICA_2026-11-08.md`) |

Nessuna fonte proposta ha licenza incompatibile (NC, SA, «tutti i diritti riservati»): sono tutte CC BY 4.0, salvo il
DTM/DSM siciliano a pagamento (escluso) e i dati calabresi (licenza non letta).

## 7. Ordine consigliato e spazio

| Ordine | Cosa | Dove | Dimensione |
|---|---|---|---|
| 1 | Palermo, unità volumetriche comunali (EPSG:7792) | `citta_rif\palermo\` | 0,016 GB |
| 2 | Cagliari, LiDAR 2008 DTM + DSM + DSM edifici, 5 tessere | `citta_rif\cagliari\` | 0,05 GB |
| 3 | Napoli, DBT 2020 + DTM 2020 del comune | `citta_rif\napoli\` | 0,154 + 0,021 GB |
| 4 | (dopo il 10/11) PST Napoli, Palermo, Catanzaro, se coprono | `citta_rif\<città>\pst\` | qualche decina di MB [D] |
| 5 | Catanzaro: controllo del geoportale regionale dal browser | `citta_rif\catanzaro\` | da vedere |
| — | facoltativi: CTR Sicilia «B_Edificato» (tutta la regione), SHAPE-ZIP DBGT Cagliari, CTR 2020 Napoli SHP | | 0,164 + ~0,004 + 0,080 GB |

Totale essenziale: **circa 0,25 GB** (0,50 GB con i facoltativi).

## 8. Da aggiornare nel progetto (non fatto qui: `/home/claude/eu` è in modifica da un altro lavoro)

- `fase10-edifici3d/fonti/regioni.toml`:
  - **Campania / edifici**: nome «DBT 2020 (CTR 2020, volo AGEA 2020)», licenza **CC BY 4.0** (pagina CTR e note
    legali del geoportale), `altezza = "no (EDIFC_CR_EDF_IS PolygonZ con z = quota al piede; nessuna UN_VOL)"`, servizio
    MapServer `Amministrativo/CTR2020/MapServer/4` e strato dei link per comune; stato «in attesa» solo per
    l'adattatore `campania_dbt` (sagome e usi), poi candidato a `sagome_regionali` (ma è ArcGIS REST, non WFS).
  - **Campania / dtm**: «DTM 2020 5 m», CC BY 4.0, servizio `server/rest/services/Amministrativo/CTR_DTM5m/ImageServer`
    (EPSG:7792, `exportImage` provato l'08/11/2026) → **attiva**.
  - **Campania / dsm**: resta «non disponibile» (aggiungere: verificato l'08/11/2026 sul portale ArcGIS regionale).
  - **Sicilia / edifici**: aggiungere tre fonti: (1) CTR 2012-13 «Edificato», `altezza = "z dei vertici = quota di
    gronda (altezza = z − DTM)"`, servizio `ctr_10000/ctr_2013_dbtrs/MapServer/35`, anno prevalente 2003; (2) CART 2000
    1:2.000 (`quotagrond`, `quotaterra`, `volume`; centri minori); (3) **Comune di Palermo, unità volumetriche 1:2.000**
    (`ALTEZZA`, CC BY 4.0, URL dello zip) → candidata ad «attiva» come archivio comunale con un adattatore `palermo_uv`.
  - **Sicilia / dtm e dsm**: motivo aggiornato: «MDT 2008 e 2013 2 m consultabili in ImageServer
    (`modelli_digitali/mdt_2013`), ma i modelli in file sono a pagamento (150 € per sezione, pagina Costi di cessione):
    licenza del servizio da chiarire»; stato «in attesa».
  - **Sardegna / edifici**: servizio WFS `https://webgis.regione.sardegna.it/geoserver/ows`, strati
    `dbu:dbgt_10k_22_v05_02_edificio_ingombro_suolo` e `…_massima_estensione` (499.171 edifici, EPSG:7791, SHAPE-ZIP),
    `altezza = "no (z = 0)"`, prova dell'08/11/2026 → **attiva come sagome** e da aggiungere a `sagome_regionali.toml`
    (riquadro_wgs84 circa [8.1, 38.8, 9.9, 41.3], crs EPSG:7791).
  - **Sardegna / dtm e dsm**: il download **non** passa solo dalla mappa: gli URL sono nei campi `dtm`, `dsm`,
    `dsm_buildi` dei WFS `dbu:QU2k_fasciacostiera2008_DTM_DSM1m` e `dbu:QU2k_DTM_DSM1m_centri_urbani_2013` (prova:
    5 tessere di Cagliari scaricate) → **attiva**; aggiungere il prodotto «DSM buildings».
  - **Calabria**: nota aggiornata: «08/11/2026: geoportale ancora chiuso al container (HTTPS) e 503 in HTTP, robots.txt
    vieta la lettura automatica; scheda RNDT della CTR 1:5.000 `r_calabr:00010:20140912:104758` in errore 500; DTM 5×5 m
    solo via FTP con credenziali».
  - **[nazionale] PST**: aggiungere le schede DSM FIRST 1 m di Campania, Sicilia, Sardegna e Calabria (identificativi al
    § 10) e «copertura di Napoli, Palermo, Catanzaro da verificare dopo il 10/11».
- `fase10-edifici3d/fonti/sagome_regionali.toml`: aggiungere **Sardegna** (WFS DBGT 10k, CC BY 4.0, prova dell'08/11/2026:
  207 sagome intorno al Brotzu, z = 0); valutare la Sicilia (CTR 2012-13 via ArcGIS REST, con z di gronda: andrebbe però
  trattata come archivio con altezze, non come sagome).
- `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
  - **Campania**: cambiare le domande: il DBT 2020 si scarica e **non** ha unità volumetriche né quote di gronda
    (verificato su Napoli). Chiedere se esistono le **quote di gronda/estradosso o le UN_VOL** della restituzione 2020
    non pubblicate, se c'è un **DSM** (fotogrammetrico 2020 o LiDAR), un file unico regionale e se possiamo scaricare in
    automatico dai link SharePoint; la CC BY 4.0 è già scritta (non serve chiederla).
  - **Sicilia**: tenere la richiesta degli edifici con altezze ma citare che la CTR 2012-13 ha già le z di gronda (anno
    2003 per gran parte) e chiedere **la licenza dell'ImageServer `mdt_2013`** e la cessione **gratuita** del DTM/DSM
    ATA 2 m per un progetto senza scopo di lucro (oggi 150 € per sezione).
  - **Sardegna**: ridurre: gli edifici DBGT 10k si scaricano dal WFS e il LiDAR 2008 ha URL diretti. Chiedere solo se
    esistono **altezze** (DBGT comunali 1k-2k vettoriali con quote, o un aggiornamento LiDAR di Cagliari e della costa
    dopo il 2008) e confermare la dicitura di attribuzione.
  - **Calabria**: aggiungere la richiesta di **accesso anonimo** al DTM 5×5 m (oggi FTP con credenziali) e di una scheda
    di metadati aggiornata della CTR 1:5.000 (quella nel RNDT non risponde), con la licenza.
- `DA_FARE.md`: «Città di riferimento Sud e Isole» con i passi del § 7; dopo il 10/11 la copertura PST di Napoli, Palermo e
  Catanzaro; Catanzaro dal browser di Paolo; adattatori `palermo_uv` e `campania_dbt`; prova Sicilia «z gronda − DTM».
- Comune di Palermo: possibile esempio per il comando `prepara-regione` con un archivio comunale (come Milano).

## 9. Prove dal vivo (08/11/2026)

| Prova | Esito |
|---|---|
| Raggiungibilità dal container | sit.regione.campania.it, geomaps.regione.campania.it, regionecampania.sharepoint.com, sitr.regione.sicilia.it, map.sitr.regione.sicilia.it, opendata.comune.palermo.it, webgis.regione.sardegna.it, dati.comune.napoli.it, opendata.comune.catanzaro.it: **sì**; geoportale.comune.napoli.it, geoportale.regione.calabria.it (HTTPS), sit.comune.catanzaro.it, overpass-api.de: **no** |
| Portale ArcGIS Campania (`sharing/rest/search`, MapServer, ImageServer) | elenco dei servizi; `exportImage` DTM 5 m 200 image/tiff; MapServer `DG5009` richiede token (non usato) |
| Strato dei link per comune e SharePoint (cookie anonimo, API `GetFolderByServerRelativeUrl`, Range) | cartella di Napoli: `DBT_5K.zip`, `DTM_5k.zip`, `CTR_5k/` (6 zip); indice del DBT (1.018 voci) e file degli edifici letti; altre cartelle: «Accesso negato» |
| DBT Napoli: z di `EDIFC_CR_EDF_IS` contro DTM 5 m | mediana +0,32 m: quota al piede |
| CTR 2020 SHP (rar per elemento, `bsdtar`) | edifici alla quota del terreno |
| SITR: pagine download, «Licenza d'uso», «Costi di cessione»; indice di `B_Edificato.zip`; servizi ArcGIS `ctr_2013_dbtrs`, `cart2000_dbtrs`, `mdt_2013` | CC BY 4.0 per i dati senza costi; DTM/DSM 2 m a pagamento; query e `exportImage` riuscite |
| Catalogo DCAT del Comune di Palermo e zip delle unità volumetriche (dataset 1294 e 269) | 2 zip scaricati e letti (100.432 e 100.347 volumi) |
| Prova di coerenza Palermo (`script/pa_prova.py`) | tabella al § 3.1 |
| WFS Sardegna (GetCapabilities, DescribeFeatureType, GetFeature GeoJSON e SHAPE-ZIP, `resultType=hits`) | 358 strati; DBGT 10k e quadri d'unione con URL; 499.171 edifici |
| LiDAR Sardegna 2008: 5 tessere × DTM/DSM (+2 × BUILDINGS) | scaricate e confrontate (`script/ca_prova.py`) |
| PST: WMS `LIDAR_{CAMPANIA,SICILIA,SARDEGNA,CALABRIA}.map` | GetCapabilities 200, GetMap vuoto sulle quattro città |
| CSW RNDT `geodati.gov.it/RNDT/csw` | schede PST delle quattro regioni, schede sarde (LiDAR, DBGT), schede SITR (pendenze), 4 schede `r_calabr`; la scheda della CTR Calabria dà errore 500 |
| CKAN Comune di Napoli e di Catanzaro | 0 dataset cartografici |

Script: `script/zipindice.py` e `script/zipparziale.py` (come in `citta_rif`, con il supporto del cookie `COOKIE`),
`script/spcookie.sh` (cookie anonimo di un link SharePoint), `script/dtmasc.py` (lettura di tessere ASCII),
`script/pa_prova.py`, `script/ca_prova.py` (gli altri script della cartella appartengono a un lavoro parallelo su
altre città, cartelle `nord/` e `centro/`). I file grezzi scaricati per le prove (DBT e DTM di Napoli, CTR, unità
volumetriche di Palermo, LiDAR di Cagliari: circa 450 MB) sono stati cancellati; in `sud/` restano indici, risposte JSON
e i piccoli ritagli GeoTIFF.

## 10. Fonti

Napoli / Campania
- Geoportale, CTR, DBT e DTM 2020 (CC BY 4.0): <https://sit.regione.campania.it/carta-tecnica-regionale>; note legali
  <https://sit.regione.campania.it/note-legali>
- Cartella SharePoint del comune di Napoli: <https://regionecampania.sharepoint.com/:f:/s/50-09-92-CTR2020/EoXurF7CRjZIt-QGFwPwDtUBr_zC71u6aA_c4IjjI-4eYA>
- Link di download per comune (ArcGIS): <https://geomaps.regione.campania.it/federated/rest/services/Amministrativo/Mappa_CTR2020___Link_Download_Comuni_MIL1/MapServer/0>
- CTR 2020 MapServer: <https://geomaps.regione.campania.it/federated/rest/services/Amministrativo/CTR2020/MapServer>
- DTM 2020 5 m: <https://geomaps.regione.campania.it/server/rest/services/Amministrativo/CTR_DTM5m/ImageServer>
- Specifica DBGT Campania v4.0 (CC BY 4.0): <https://geomaps.regione.campania.it/portal/sharing/rest/content/items/e07b1f4b43944c8aa8a31d9074e6b76c>
- Open data del Comune di Napoli: <https://dati.comune.napoli.it/>

Palermo / Sicilia
- Unità volumetriche 1:2.000 (CC BY 4.0): <https://opendata.comune.palermo.it/opendata-dataset.php?dataset=1294>, file
  <https://opendata.comune.palermo.it/js/server/uploads/dataset/shp/_09062021064719.zip>; versione 2013:
  <https://opendata.comune.palermo.it/opendata-dataset.php?dataset=269>; catalogo DCAT <https://opendata.comune.palermo.it/dcat/dcat.php>
- SITR, CTR ATA 2012-13 in shapefile: <https://www.sitr.regione.sicilia.it/download/download-carta-tecnica-regionale-10000/ata1213-shape/>
- SITR, licenza d'uso: <https://www.sitr.regione.sicilia.it/licenza-duso/>; costi di cessione: <https://www.sitr.regione.sicilia.it/costi-di-cessione/>
- Servizi ArcGIS del SITR: <https://map.sitr.regione.sicilia.it/gis/rest/services> (`ctr_10000/ctr_2013_dbtrs`,
  `ctn_2000/cart2000_dbtrs`, `modelli_digitali/mdt_2013`)
- Carta tecnica 1:2.000 CART 2000: <https://www.sitr.regione.sicilia.it/download/download-carta-tecnica-2000/>
- Discussione OSM sull'import degli edifici di Palermo (CC BY): <https://lists.openstreetmap.org/pipermail/imports/2014-April/003120.html>

Cagliari / Sardegna
- WFS regionale: <https://webgis.regione.sardegna.it/geoserver/ows?service=WFS&request=GetCapabilities>
- LiDAR fascia costiera 2008 (CC BY 4.0): <https://geodati.gov.it/resource/id/R_SARDEG:BFPNM>; mappa di download
  <https://www.sardegnageoportale.it/webgis2/sardegnamappe/?map=download_raster>
- DBGT 10k (CC BY 4.0): <https://geodati.gov.it/resource/id/R_SARDEG:2c842f2a-d268-45e4-a68c-6cff2070bd28>
- DBGT 2k dei centri urbani (raster): <https://geodati.gov.it/resource/id/R_SARDEG:969d4bc9-f591-4f26-aaef-4d1c8d63a033>
- DTM/DSM centri urbani 2013: <https://geodati.gov.it/resource/id/R_SARDEG:7f606501-8ef8-4fa0-99ad-54811f370308>

Catanzaro / Calabria
- Geoportale (non leggibile da qui): <https://geoportale.regione.calabria.it/opendata>
- Scheda RNDT della CTR 1:5.000 (in errore): <https://geodati.gov.it/resource/id/r_calabr:00010:20140912:104758>
- Open data del Comune di Catanzaro: <https://opendata.comune.catanzaro.it/>
- Repertorio ICA delle banche dati calabresi: <https://ica.cultura.gov.it/geoportale/repertorio-preliminare-delle-banche-dati-territoriali-reperibili-on-line/calabria/>

Nazionali
- PST MASE, distribuzione e licenza: <https://gn.mase.gov.it/portale/distribuzione-dati-pst>; app
  <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>; schede DSM FIRST 1 m: Campania
  <https://geodati.gov.it/resource/id/m_amte:299FN3:2a5efec9-3014-4f11-865d-db93d48c5065>, Sicilia
  <https://geodati.gov.it/resource/id/m_amte:299FN3:5cebe64c-71fc-4a61-86bc-61e2cfc5f1bf>, Sardegna
  <https://geodati.gov.it/resource/id/m_amte:299FN3:294f00a5-86ab-403c-86c3-05ad3ebbe585>, Calabria
  <https://geodati.gov.it/resource/id/m_amte:299FN3:1c04aa0a-5c79-466c-a266-b15428703449>
