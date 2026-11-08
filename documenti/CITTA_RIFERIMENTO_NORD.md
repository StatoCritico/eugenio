# Città di riferimento del Nord: Torino, Genova, Venezia, Trieste, Trento, Bolzano – fonti, licenze e istruzioni di download

Verifica dell'08/11/2026, fatta dal container di sviluppo senza login, account o captcha e senza aggirare blocchi.
Nessun file di `/home/claude/eu` è stato modificato: le prove sono in `/home/claude/citta_rif2/` (`nord/`, `script/`).
Legenda: **[V]** verificato con una prova dal vivo o letto su una pagina o scheda ufficiale; **[D]** dedotto o da confermare.

Scopo: come per Milano, Firenze e Roma (`CITTA_RIFERIMENTO_MILANO_FIRENZE_ROMA.md`), sei città del Nord con edifici noti
dove confrontare **sagome e altezze dei DB topografici** con **DSM − DTM**, per controllare gli adattatori regionali
(`liguria_ctr3d`, `fvg_ctrn`, Edifici P.A.T. 3D, zone LiDAR di Trento e Bolzano) e avere riferimenti noti.
Cartella dei download di Paolo: `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\<città>\`.

Limiti di rete di questa verifica: dal container **tutti i siti del Piemonte** (geoportale.piemonte.it,
geomap.reteunitaria.piemonte.it, geoservices.csi.it, datigeo-piem-download.it, webgis.arpa.piemonte.it,
geoportale.comune.torino.it, aperto.comune.torino.it) chiudono la connessione o rispondono 503, e WebFetch li rifiuta
(non in lista); **dati.venezia.it** e **geoportale.comune.venezia.it** sono protetti da Incapsula (403 o pagina di
controllo). Per Torino e per il Comune di Venezia le fonti sono quindi lette solo dalle schede del catalogo nazionale
RNDT (CSW di geodati.gov.it, raggiungibile) e vanno provate dal server di Milano o dal browser di Paolo.
Il **portale PST del MASE** è offline fino al 10/11/2026: i WMS `LIDAR_{PIEMONTE,LIGURIA,VENETO,FRIULI_VENEZIA_GIULIA}.map`
rispondono al GetCapabilities ma il GetMap è vuoto (PNG trasparente di 334 byte) su tutte e quattro le città [V]:
**copertura PST da riverificare dopo il 10/11**.

## 1. In breve

| Città | Edifici con altezze | DTM | DSM | Valore come riferimento |
|---|---|---|---|---|
| **Genova** | Regione Liguria, CTR 1:5000 3D (z = quota di gronda, CC BY 4.0, **WFS provato**); Comune, **Carta Tecnica Comunale 2018** in DXF con `UN_VOL` 3D e punti di quota di gronda (CC BY 4.0) | **Comune, LiDAR 3-4/10/2018, 0,5 m** (area urbanizzata) e 1 m (comune), CC BY 4.0 | **Comune, LiDAR 2018, 0,5 m** e 1 m, più nuvole LAS, CC BY 4.0 | **Il migliore del Nord**, come Firenze. San Martino: DSM − z di gronda regionale mediana −0,11 m, scarto < 2 m nell'**88 %** di 354 volumi; Lanterna DSM − DTM 75,3 m (alta 77 m [D]) |
| **Trento** | Provincia, **Edifici P.A.T. 3D** (2014, `MIN_ALT`, `MED_ALT`, `MAS_ALT`, `quota_DTM`; CC BY 4.0; zip 108 MB) | **Provincia, LiDAR 2014/2018, 0,5 m**, CC BY 4.0 (nuovo per il progetto) | **Provincia, LiDAR 2014/2018, 0,5 m**: DSM First, DSM Last e **DBM** (solo edificato), CC BY 4.0 | **Ottimo e automatico**. S. Chiara: DSM − DTM contro `MED_ALT` mediana +0,20 m, **96 %** entro 2 m (555 edifici); ma il 21 % degli edifici ha altezza 0 (55 % nel centro storico) |
| **Bolzano** | **sagome sì, altezze no**: Provincia, INSPIRE `BU.Building` e `BU.BuildingPart` (CC0, WFS, aggiornati 08/07/2026) | Provincia, DTM 0,5 m (CC0, WCS, già nel progetto) | Provincia, DSM 0,5 m (CC0, WCS, ~2013 [D]); corridoio dell'Adige 0,2 m 2024 | **Buono per DSM − DTM su sagome ufficiali**: Duomo, campanile DSM − DTM 60 m al p90, 67 m alla punta (alto 65 m [D]). Il DSM è vecchio: il nuovo corpo dell'ospedale (3.336 m²) risulta alto 0 m |
| **Trieste** | Regione FVG, **CTRN ed. 2** foglio 110 (`ALTEZZA`, `QUOTA_PIEDE`, `QUOTA_GRONDA`, `DATA_VOLO` **2003**); DBTsped 2017-20 (`ALTEZZA_M`, ma blocchi accorpati) | Regione, LiDAR 2017-2020 0,5 m (solo da Eagle.fvg a mano; licenza: IODL 2.0 dalla pagina regionale, «non indicata» nella scheda) | come il DTM; PST 2 m costiero (CC BY 4.0, da verificare) | **Utile per l'adattatore FVG**, debole per il controllo: nessun DSM scaricabile in automatico. Cattinara: torri 54,8 m alla gronda (CTRN) |
| **Torino** | Comune, **Edificato del DBGT** 1:1.000 (CC BY 4.0, aggiornato 31/12/2025, WFS); Regione, **BDTRE UN_VOL**; Arpa Piemonte **Edifici 3D 2017** (`ELEV`, a Torino «da carta tecnica comunale») | Regione, DTM 5 m ICE 2009-2011 (CC BY 4.0) | Regione, DSM 5 m ICE 2009-2011 (CC BY 4.0); PST 1 m sul Po (da verificare) | **Da provare dal server**: tutte le fonti sono solo lette dalle schede RNDT. DSM troppo vecchio e grosso (5 m) per un controllo sugli edifici; i grattacieli Intesa Sanpaolo (2015) e Piemonte (2022) non ci sono |
| **Venezia** | **sagome sì, altezze no**: Regione Veneto `rv:edifici_veneto_feb2022` (a Venezia = DBGT del Comune 2010, IODL 2.0) | Regione Veneto, DTM 5 m da LiDAR (già usato) | **nessun DSM aperto** trovato (PST Veneto 1 m sulle aste fluviali, copertura della laguna da verificare) | **Debole**: solo sagome. Il DBGT 2010 del Comune (lotto regionale) dovrebbe avere le unità volumetriche, ma non è pubblicato |

Novità rispetto a `fonti/regioni.toml` e a `LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
- **Trento – LiDAR PAT 2014/2018 a 0,5 m** (DTM, DSM First, DSM Last, DBM), CC BY 4.0, cartelle pubbliche
  `siatservices.provincia.tn.it/stemdata/2014_lidar_*_asc/` (25.201 tessere ASCII di 500 m per prodotto, ~194 GB) e
  quadro d'unione WFS `stem:inqlid2014_*` con il nome della tessera: sostituisce il 2006-2009 a 1 m. [V]
- **Trento – Edifici P.A.T. 3D**: il campo dell'altezza c'è (`MIN_ALT`, `MED_ALT`, `MAS_ALT`, più `quota_DTM`),
  147.481 edifici, shapefile PolygonZ in ETRS89/UTM 32N; 31.153 (21 %) con altezza 0. [V]
- **Bolzano – edifici**: non è vero che manchino. Ci sono gli strati INSPIRE `BU.Building` / `BU.BuildingPart` (CC0,
  WFS 2.0, `BEGIN_LIFESPAN_VERSION` 2026-07-08), ma in 2D, senza altezze. La lettera alla Provincia va riscritta. [V]
- **Genova – LiDAR comunale 2018** (DSM e DTM 0,5 m e 1 m, LAS) e **Carta Tecnica Comunale 2018** in DXF, tutto CC BY
  4.0 con URL fissi per tavola e quadri d'unione WFS: il tema «dsm» della Liguria non è più «non disponibile». [V]
- **FVG – DBTsped (`EDIFICI:DBS_EDIFICATO`)**: nuovo strato regionale da true ortofoto 2017-2020 con `ALTEZZA_M`, già
  presente a Trieste (la scheda parla solo della provincia di Gorizia). [V]
- **FVG – licenza del LiDAR 2017-2020**: la pagina regionale «Conoscere l'ambiente e il territorio» dice che i dati sono
  rilasciati con la licenza standard della Regione, la **IODL 2.0**; la scheda IRDAT resta senza licenza. [V]
- **Torino**: oltre alla BDTRE regionale c'è l'**Edificato del DBGT del Comune** (1:1.000, CC BY 4.0) e lo strato Arpa
  **Edifici 3D 2017** con l'altezza (`ELEV`) per tutto il Piemonte. [V solo sulle schede RNDT]
- **Veneto**: a Venezia le sagome regionali vengono tutte dal «Lotto Comune di Venezia» del DBGT (volo **2010**); c'è
  anche un «Lotto Laguna di Venezia 2006» (strato `rv:c0101101_lotti_dbgt`). Il WFS in EPSG:6876 vuole il riquadro in
  ordine **Nord, Est** con `urn:ogc:def:crs:EPSG::6876` (in ordine E, N risponde 0 elementi). [V]

## 2. Torino

### 2.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Comune di Torino – Edificato del DBGT** (edifici principali e minori «corredati di informazioni dettagliate», `c_l219:78dc5b8a-…`) | creazione 30/09/2023, revisione **31/12/2025**, aggiornamento trimestrale | 1:1.000 (accuratezza 0,4 m) | WFS `wfs_sicc140_edificato_dbgt`; sistema della scheda: Monte Mario / Italy 1 (EPSG:3003) | scheda RNDT: «no limitations to public access», `https://creativecommons.org/licenses/by/4.0/deed.it` | WFS `https://geomap.reteunitaria.piemonte.it/ws/siccms/coto-01/wfsg01/wfs_sicc140_edificato_dbgt` | — | [V] scheda; servizio **non raggiungibile** dal container; campi delle altezze [D] (non letti) |
| Edifici (zip) | Comune di Torino – «Dati di base – Carta Tecnica» (tutti gli strati, `c_l219:092bd977-…`; strato 02 «Immobili ed antropizzazioni», specifica `geodati/pdf/Strato02.pdf`) | rev. 31/12/2025 | 1:1.000 | zip (formato [D]) | CC BY 4.0 (scheda) | `http://geoportale.comune.torino.it/sec/zip/carta_tecnica.zip` (la cartella `sec` fa pensare a un accesso riservato [D]) | — | [V] scheda; 503 dal container |
| Edifici (regionale) | **Regione Piemonte – BDTRE, Unità volumetrica (UN_VOL)** (`r_piemon:6dacd512-…`) | aggiornamento continuo (edizioni annuali) | 1:10.000 (in città dalle carte comunali [D]) | WFS `bdtre_imm`; zip per comune in EPSG:32632 (modello `…/BDTRE2015_VECTOR/BDTRE_DATABASE_GEOTOPOGRAFICO_2015-LIMI_COMUNI_10_GAIMSDWL-001272-EPSG32632-SHP.zip` per Torino, edizione 2015) | BDTRE generale: CC BY 4.0; scheda UN_VOL: «Condizioni sconosciute» | WFS `geoservices.csi.it/…/bdtre_imm`; zip da `datigeo-piem-download.it` | [D] | [V] schede; WFS e download **chiudono la connessione** dal container |
| Edifici (3D) | **Arpa Piemonte – Edifici 3D 2017**: unità volumetriche BDTRE con `ELEV` (altezza in m) e `DES` (procedura; **«To: quota derivata dalla carta tecnica del comune di Torino»**) | 2017 | 1:10.000 | ArcGIS MapServer `topografia_dati_di_base/Edifici_3D_2017` | scheda: dataset scaricato dal portale ISPRA con **IODL 2.0**; servizio con licenza Arpa (`Licenza_map_service.pdf`); obbligo di citare la fonte | MapServer `webgis.arpa.piemonte.it`; download ISPRA [D] | — | [V] scheda `arlpa_to:EDIF_2017-12-21-11:00`; MapServer non raggiungibile |
| DTM | **Regione Piemonte – Ripresa aerea ICE 2009-2011, DTM 5 m** (LiDAR, ±0,30 m, ±0,60 m in aree urbane dense) | 2009-2011 | 5 m | WCS `wcs_ice_2009_2011_dtm`, scarico dal geoportale (strato `scDTM5ICE`) | scheda `r_piemon:224de2ac-…`: `creativecommons.org/licenses/by/4.0` | WCS / download a mano | [D] | [V] scheda; servizi non raggiungibili |
| DSM | **Regione Piemonte – ICE 2009-2011 DSM** (LiDAR, 5 m, ±0,30 m) | 2009-2011 | 5 m | [D] | scheda `r_piemon:12a0bdd2-…`: CC BY 4.0 | download a mano dal geoportale [D] | [D] | [V] scheda; **5 m e 2009-11: inadatto** a misurare edifici singoli |
| DSM (nazionale) | PST MASE – DSM FIRST/LAST LiDAR 1 m – Piemonte (aste fluviali di I e II ordine: il **Po** attraversa Torino) | 2008-2013 [D] | 1 m | GeoTIFF EPSG:4326 | CC BY 4.0 (scheda `m_amte:299FN3:26f1c7e3-…`) | app PST, offline fino al 10/11 | — | [V] scheda; WMS vuoto; **copertura da verificare** |

### 2.2 Area di prova

- **Ospedale Molinette (Città della Salute)**: EPSG:32632 **395100–396100 E, 4987600–4988800 N** (centro 395595/4988189).
- **Mole Antonelliana** (167,5 m) e grattacieli **Intesa Sanpaolo** (166 m, 2015) e **Piemonte** (205 m, 2022): riquadro
  **394400–397500 E, 4991000–4992000 N** (Mole 397127/4991445; Intesa 394740/4991555; Piemonte 394896/4991474).
  I due grattacieli sono un buon controllo della **data** delle fonti (assenti nel DSM 2009-11, forse anche in Edifici
  3D 2017 per il grattacielo Piemonte).
- PST: celle 0,01° tra **7,66–7,72 E, 45,03–45,08 N** (Po dal Valentino alle Molinette).

### 2.3 Istruzioni per Paolo

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
4. Dal geoportale regionale, «Scarico – Ripresa Aerea ICE 2009-2011 – DTM5» e «DSM»: scarica le tavole che coprono i due
   riquadri del § 2.2 in `…\citta_rif\torino\ice\` (facoltativo: sono a 5 m).
5. **Dopo il 10/11/2026**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona
   area» su 7,66–7,72 E / 45,03–45,08 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Piemonte» e «DTM 1 m», scarica le
   celle in `…\citta_rif\torino\pst\`.

### 2.4 Cosa può fare il server da solo

- Da provare **dal server di Milano** (il container è bloccato): `GetCapabilities` e un `GetFeature` sul riquadro delle
  Molinette di `wfs_sicc140_edificato_dbgt` (Comune) e di `bdtre_imm` (Regione), e `?f=json` del MapServer Arpa
  `Edifici_3D_2017`. Se rispondono, Torino si prende per riquadro come la Liguria, senza download a mano.
- Lo zip BDTRE per comune, se l'URL è fisso, si scarica in automatico; i campi DBGT nazionali sono quelli già letti da
  `lombardia_dbgt` [D].

## 3. Genova

### 3.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Liguria – CTR 1:5000 2007/2013 II ed. 3D / DB topografico, strato Edificato `M2237:L8178`** (già nel progetto, adattatore `liguria_ctr3d`): z dei vertici = quota di gronda | 2007-2013 | 1:5.000 | WFS GeoJSON, EPSG:3003 | scheda `r_liguri:D.2237`: CC BY 4.0 | **automatico** (WFS, `count` 3000) | — | [V] riquadro di San Martino: 479 elementi; **DSM 2018 − z = −0,11 m in mediana, MAE 0,93 m, 88 % entro 2 m** (354 volumi) |
| Edifici (comunale) | **Comune di Genova – Carta Tecnica Comunale (CTC) rilievo 2018**, tavole 1:2.000 in **DXF**: livelli `clip_UN_VOL` (polilinee 3D al piede), `clip_PT_QUO_GRONDA`, `clip_PT_QUO_PIEDE`, `clip_PT_QUO_SUOLO`, `clip_EDIFC_*`, `clip_EDI_MIN_*` | volo 3-4/10/2018 (DXF del 16/05/2022) | 1:1.000/2.000 | DXF in zip per tavola, **EPSG:7791** (coordinate RDN2008/UTM 32N) | schede del Comune (`c_d969:fcdefdd4-…` «Download – Scarico», `c_d969:e7478020-…` CTC 2018): «Creative Commons Attribution 4.0» | download diretto per tavola: `https://mappe.comune.genova.it/gis/rilievo/CAD/DXF/2000/<tavola>.zip` | 3930.zip 15,7 MB (DXF 159 MB), 3830.zip 8,7 MB, 3720.zip 3,8 MB | [V] tavola 3930: 5.229 `UN_VOL`, 4.911 quote di gronda; nella tessera 3931 **DSM 2018 − quota di gronda: mediana −0,05 m, MAE 2,30 m, 72 % entro 2 m** (697 volumi) |
| Edifici (storico) | Comune – «Corpi edilizi del centro storico» (Banca dati Città Vecchia 1995-98) | 1995-98 | 1:5.000 | WFS `SITGEO:V_CORPI_MAPP_CIVIS` | CC BY 4.0 | WFS | — | [V] scheda; non serve (vecchio) |
| DTM | **Comune di Genova – DTM 50 cm** (area urbanizzata) e **DTM 1 m** (intero comune), da LiDAR | volo 3-4/10/2018 | 0,5 m e 1 m; tavole 1:1.000 (850×715 m) e 1:2.000 | ASCII Grid, EPSG:7791 | scheda `c_d969:44d9a724-…`: «Creative Commons Attribution 4.0» | **automatico**: `https://mappe.comune.genova.it/gis/rilievo/02_DTM_50CM_REV/DTM<tavola>.asc` e `…/04_DTM_1M/DTM<tavola>.asc`; quadri WFS `MEDIATORE:V_QU_DSM_DTM_50CM_BUFFER10M` (296 tavole) e `…_LAS_DSM_DTM_1M_BUFFER10M` (157) | 12,7–14,6 MB per tavola 0,5 m | [V] DTM3931 e DTM3723 scaricati (200), intestazione 1700×1429, cella 0,5 |
| DSM | **Comune di Genova – DSM 50 cm** (area urbanizzata, punti Ground, Vegetation, Building, Bridge, Generic) e **DSM 1 m** (comune) | 2018 | 0,5 m e 1 m | ASCII Grid, EPSG:7791 | scheda `c_d969:c39859c3-…`: «Creative Commons Attribution 4.0» | **automatico**: `…/01_DSM_50CM_REV/DSM<tavola>.asc`, `…/03_DSM_1M/DSM<tavola>.asc` (risposta 206 alle richieste Range) | 12,4–16,4 MB per tavola 0,5 m | [V] tessera 3723: **Lanterna** DSM 122,15 m, DTM 46,82 m → **75,3 m** (alta 77 m [D]) |
| Nuvole | Comune – LAS aereo 2018 (e LAS terrestre 2019-2021) | 2018 | — | LAS per tavola 1:2.000 | CC BY 4.0 | `…/LAS/LAS<tavola>.las` | **893 MB** (LAS3930) | [V] dimensione letta; non serve |
| DTM (regionale) | Regione Liguria – DTM ed. 2023 (`r_liguri:D.2056`) | 2023 | [D] | WMS/WCS `M2056` | CC BY 4.0 | WCS (già nel progetto) | — | non riprovato: a Genova c'è il DTM comunale a 0,5 m |
| DSM (nazionale) | PST MASE – DSM FIRST/LAST 1 m – Liguria (`m_amte:299FN3:f0194c98-…`) | 2008-2013 [D] | 1 m | GeoTIFF | CC BY 4.0 | app PST | — | non serve a Genova |

### 3.2 Area di prova

- **Ospedale Policlinico San Martino**: tavola 0,5 m **3931** (EPSG:7791 497420–498270 E, 4916877–4917592 N; centro
  497857/4917354), più 3942 a nord; DXF CTC **3930** (1:2.000).
- **Centro – Cattedrale di San Lorenzo** (494539/4917151): tavola 0,5 m **3831**, DXF **3830**.
- **Lanterna** (492407/4916812): tavola **3723**; **Matitone** (492573/4917555): tavola **3721**; DXF **3720** per entrambi.
- **Ospedale Galliera** (495348/4916250): tavola **3823**, DXF **3820**.

### 3.3 Istruzioni per Paolo

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

### 3.4 Cosa può fare il server da solo

- **Tutto**. Edifici: WFS regionale `M2237:L8178` (adattatore `liguria_ctr3d` già pronto). DSM e DTM: elenco delle
  tavole dal WFS `https://mappe.comune.genova.it/geoserver/ows?service=WFS&typeName=MEDIATORE:V_QU_DSM_DTM_50CM_BUFFER10M`
  (campi `TAVOLA`, `LINK_DSM`, `LINK_DTM`; EPSG:7791) e poi gli `.asc` per tavola. Lo stesso per il 1 m
  (`V_QU_LAS_DSM_DTM_1M_BUFFER10M`) fuori dall'area urbanizzata.
- Per la Liguria l'adattatore usa altezza = z di gronda − DTM: a Genova conviene il **DTM comunale 2018 a 0,5 m** al
  posto del DTM regionale (prova: (z − DTM 2018) − (DSM − DTM) mediana +0,11 m).
- La CTC in DXF è una seconda fonte comunale (unità volumetriche al piede + punti di quota di gronda da associare per
  contenimento, come in `script/prova_ge.py`): servirebbe un adattatore `genova_ctc_dxf` [D]; non è prioritario perché
  la CTR regionale è già migliore sul DSM 2018 (88 % contro 72 % entro 2 m).

## 4. Venezia

### 4.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici (sagome) | **Regione del Veneto – Edifici del Veneto (feb. 2022)** `rv:edifici_veneto_feb2022` (già nel progetto, `sagome_regionali.toml`) | a Venezia **`anno_agg` 2010**, `ente_prod` «ven» (Comune di Venezia), `scril` 5k | 1:5.000 | WFS 2.0, EPSG:6876, **riquadro in ordine N, E** | IODL 2.0 (scheda `r_veneto:edifici_veneto`) | **automatico** | — | [V] San Marco (600×600 m): 758 sagome, tutte 2010; Ospedale dell'Angelo: 26 sagome (la più grande 28.239 m²). **Nessuna altezza** (z = 0) |
| Edifici (fonte del dato) | Regione Veneto – lotti DBGT `rv:c0101101_lotti_dbgt`: «**LOTTO COMUNE DI VENEZIA**» volo **2010** e «LOTTO LAGUNA DI VENEZIA» **2006** (GEO_DB) | 2006, 2010 | 1:1.000/2.000 [D] | — | — | **non pubblicato** come DBGT completo (unità volumetriche) | — | [V] quadro dei lotti letto dal WFS (20 lotti) |
| Edifici (provincia) | Regione Veneto – «Unione dell'edificato della provincia di Venezia» `rv:edi_ve` (CTRN e DBGT di vari anni) | 2019 | 1:5.000 | SHAPE-ZIP dal WFS | IODL 2.0 | WFS | — | [V] scheda; `DescribeFeatureType` vuoto (strato non più pubblicato) |
| Edifici (comunale) | Comune di Venezia – cartografia di base e DBT su dati.venezia.it / geoportale.comune.venezia.it | — | — | — | nel 2013 il SIT annunciava la CC BY [D] | **non raggiungibile** (Incapsula) | — | da verificare dal browser |
| DTM | Regione Veneto – DTM 5 m da voli LiDAR (quadro `rv:c0101071_lidar5m`, tessere `12_2K_3367`, `12_2K_3368` a San Marco) | [D] | 5 m | [D] | IODL 2.0 | già usato nel progetto | — | [V] quadro: 2 tessere su San Marco |
| DSM | **Nessun DSM aperto** regionale o comunale trovato | — | — | — | — | — | — | [V] RNDT: per il Veneto solo PST |
| DSM (nazionale) | PST MASE – DSM FIRST/LAST 1 m e 2 m – Veneto («aste fluviali di I e II ordine») | 2008-2013 [D] | 1–2 m | GeoTIFF | CC BY 4.0 | app PST | — | [V] scheda `m_amte:299FN3:f451a878-…`; **copertura di laguna e Mestre da verificare** |

### 4.2 Area di prova

- **San Marco – Campanile** (98,6 m [D]): WGS84 45,4340 N, 12,3390 E; EPSG:6876 (E, N) 3026530/5033237; EPSG:25833
  291866/5034613. Riquadro WFS: `bbox=5032937,3026230,5033537,3026830,urn:ogc:def:crs:EPSG::6876`.
- **Ospedale dell'Angelo (Mestre)**: 45,5132 N, 12,2227 E; EPSG:6876 3017402/5042005.
- PST: celle 0,01° tra **12,30–12,36 E, 45,42–45,45 N** (centro storico) e **12,21–12,24 E, 45,50–45,52 N** (Angelo).

### 4.3 Istruzioni per Paolo

1. Dal browser apri <https://dati.venezia.it> e <https://geoportale.comune.venezia.it> (dal container sono bloccati):
   cerca «carta tecnica», «DBT», «edifici», «LiDAR», «DSM». Se c'è un DBT con unità volumetriche o altezze, o un DSM,
   **senza login**, annota pagina, licenza e dimensione e salva il file in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\venezia\comune\`.
2. **Dopo il 10/11/2026**: nell'app PST «Seleziona area» sulle due celle del § 4.2; se c'è un DSM FIRST 1 m o 2 m,
   scaricalo in `…\citta_rif\venezia\pst\`.
3. Se non trovi altezze aperte, Venezia resta solo per le sagome: nessun altro download.

### 4.4 Cosa può fare il server da solo

- Sagome dal WFS regionale (già attivo, con l'ordine N, E del riquadro). Altezze: solo OSM o Zornade (cascata già
  decisa).

## 5. Trieste

### 5.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione FVG – IRDAT, Edificato CTRN, foglio 110**: `EDIFICI:EDIFICATO_CTRN_ED2_110` (ed. 2: `ALTEZZA`, `QUOTA_PIEDE`, `QUOTA_GRONDA`, `VOLUME`, `TIPO` confermato/modificato, `ELEMENTO_CTRN`, **`DATA_VOLO`**) ed `…_ED1_110` (ed. 1, senza data) | **volo 22-23/05/2003** a Trieste | 1:5.000 | WFS 2.0 GeoJSON, **EPSG:6708** | scheda del servizio di download: CC BY 4.0; schede degli strati («Edificato 110», `r_friuve:m6528-cc-i9796`): «Dato pubblico», «Non indicato»; pagina regionale: IODL 2.0 | **automatico** (adattatore `fvg_ctrn`, strato da scegliere con `--strato`: usare **ED2**) | — | [V] Cattinara: 151 edifici (ED2), torri **ALTEZZA 54,8 e 54,1 m** (gronda 306,5 m); Faro della Vittoria: torre 57,1 m alla gronda (alto 68 m con la statua [D]) |
| Edifici (2) | **Regione FVG – DBTsped, `EDIFICI:DBS_EDIFICATO`** («Database Territoriale Speditivo», vettorializzazione automatica della true ortofoto 2017-2020; `ALTEZZA_M`, `VOLUME`, `AREA_MQ`) | 2017-2020 | [D] | WFS, EPSG:6708 | schede `r_friuve:m10910-cc-i11780`: «Dato pubblico», «Non indicato» | WFS | — | [V] presente a Trieste (208 poligoni a Cattinara, 235 in centro) benché la scheda citi solo la provincia di Gorizia; **blocchi accorpati** (torri di Cattinara dentro un poligono di 10.153 m² alto 23,8 m): contro la CTRN mediana +0,34 m ma solo 65 % entro 2 m (35 % in centro). Non adatto a corpi singoli |
| DTM | **Regione FVG – Modelli altimetrici rilievo LiDAR RAFVG 2017-2020**: DTM 0,5 m (anche 1 m e 10 m), quote ellissoidiche e ortometriche | 2017-2020 | 0,5 m | ASCII Grid, RDN2008 / TM33 | scheda IRDAT 11826: vincoli vuoti («Use constraints: -»); pagina regionale «Conoscere l'ambiente e il territorio»: dati rilasciati con «la licenza standard attualmente in uso dall'Amministrazione regionale», **Italian Open Data Licence v2.0** | **solo a mano** da Eagle.fvg (`main.aspx?configuration=guest`, funzione «scarico basi cartografiche»); nessun WCS (`serviziogc` e `irdat-ortofoto` hanno solo l'ombreggiatura) | [D] | [V] pagine e servizi; download non provato (applicazione con gettone ospite) |
| DSM | Regione FVG – DSM primo e ultimo ritorno 0,5 m e DBM 0,5 m (stesso rilievo) | 2017-2020 | 0,5 m | come il DTM | come il DTM | Eagle.fvg a mano | [D] | [V] scheda `r_friuve:m10856-cc-i11826` |
| DSM (nazionale) | PST MASE – DSM FIRST/LAST 2 m – FVG («l'intera fascia costiera», riquadro 13,06–13,86 E: comprende Trieste) | volo 2008 [D] (scheda: 2008-06-01) | 2 m | GeoTIFF | CC BY 4.0 (scheda `m_amte:299FN3:fd1f9385-…`) | app PST | — | [V] scheda; WMS vuoto oggi |

### 5.2 Area di prova

- **Ospedale di Cattinara** (torri alte): EPSG:6708 **408300–408900 E, 5053700–5054300 N** (centro 408615/5054004).
- **Ospedale Maggiore – centro**: **404700–405300 E, 5055500–5056100 N** (Ospedale Maggiore 405100/5055835; Piazza
  Unità 403981/5055911).
- **Faro della Vittoria**: 403190/5058760.
- PST: celle 0,01° tra **13,74–13,84 E, 45,62–45,68 N**.

### 5.3 Istruzioni per Paolo

1. Apri <https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest> (accesso ospite, nessuna registrazione),
   funzione di scarico delle basi cartografiche, rilievo **LiDAR RAFVG 2017-2020**: scarica **DTM 0,5 m** e **DSM primo
   ritorno 0,5 m** (quote **ortometriche**) delle tavole che coprono Cattinara e il centro (§ 5.2). Salva in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\trieste\lidar\` e annota nomi e dimensioni delle tavole.
   Se l'applicazione chiede una registrazione, fermati e annotalo.
2. Nessun download per gli edifici: il server li prende dal WFS.
3. **Dopo il 10/11/2026**: PST, celle del § 5.2, DSM FIRST 2 m e DTM, in `…\trieste\pst\` (solo se Eagle non va).

### 5.4 Cosa può fare il server da solo

- Edifici: `fvg_ctrn` con `--strato EDIFICI:EDIFICATO_CTRN_ED2_110` (l'ED2 ha anche `DATA_VOLO`, utile come anno del
  dato). Campi diversi dall'ED1: `ID1` al posto di `ID`, niente `X`/`Y`, geometria `GEOMETRY` [V] (l'adattatore va
  controllato su questi nomi [D]).
- LiDAR: nessun accesso automatico (Eagle è un'applicazione con gettone ospite, nessun servizio documentato). Il
  controllo DSM − DTM a Trieste dipende dai file scaricati a mano da Paolo.

## 6. Trento

### 6.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Provincia autonoma di Trento – Edifici P.A.T. 3D** (`ctp14_edificato_04072014`: proiezione al suolo della gronda; `MIN_ALT`, `MED_ALT`, `MAS_ALT` altezze minima, media e massima; `quota_DTM`; `TIPO`; `TAVOLA` = tessera del LiDAR 2006-09 da cui vengono le altezze; specifica `S158-EDI.pdf`) | file del **04/07/2014** (CTP 2014); altezze dal LiDAR 2006-2009 | CTP 1:10.000 [D] | Shapefile **PolygonZ**, `.prj` «ETRF_1989_UTM_Zone_32N» (≈ EPSG:25832) | scheda `p_TN:6a7806d8-…`: «Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)» | download diretto (zip unico) | **107.676.038 byte** (shp 335 MB, dbf 62 MB estratti) | [V] 147.481 edifici; **31.153 (21 %) con `MED_ALT` = 0**; ospedale S. Chiara corpo principale `MAS_ALT` 51,1 m; campanile del Duomo `MED_ALT` 41,8 m |
| DTM | **PAT – LiDAR DTM PAT 2014/2018** (voli 2013-2015, aggiornati 2018; PST-A) | 2013-2015, 2018 | **0,5 m**, tessere 500×500 m (`5h<E/100><N/100>`) | ASCII Grid (`.asc`, anche `.xyz`), EPSG:25832 | scheda `p_TN:79c6cdf0-…`: CC BY 4.0 | **automatico**: `https://siatservices.provincia.tn.it/stemdata/2014_lidar_dtm_asc/<tessera>_DTM.asc`; quadro WFS `https://siat.provincia.tn.it/geoserver/wfs`, strato `stem:inqlid2014_new` (o `…_dtm_asc`, con `n_tavola`, `x_min`, `y_min`) | ~7–8 MB a tessera; 25.201 tessere, **194 GB** | [V] 5 tessere scaricate; intestazione 1000×1000, cella 0,50 |
| DSM | **PAT – LiDAR DSM First** e **DSM Last 2014/2018**; **DBM** (modello digitale dell'edificato: terreno + edifici, senza vegetazione) | come il DTM | 0,5 m | come il DTM | schede `p_TN:9bb00ab2-…` (First), `p_TN:4966f8b8-…` (Last), `p_TN:ee78298d-…` (DBM): CC BY 4.0 | `…/stemdata/2014_lidar_dsmfirst_asc/<tessera>_DSMFirst.asc`, `…_dsmlast_asc/…_DSMLast.asc`, `…_dbm_asc/…_DBM.asc` | ~7–8 MB a tessera; ~194–198 GB per prodotto | [V] confronto sotto |
| DTM/DSM (vecchio) | PAT – LiDAR 2006/2009 1 m (già in `zone/trento.toml`) | 2006-2009 | 1 m | GeoTIFF 2×2 km | CC BY 4.0 | automatico | 3,8 MB a file | superato dal 2014/2018 |

**Prova di coerenza (08/11/2026)** [V] (edifici interi nel riquadro, sagoma ristretta di 1 m, area ≥ 30 m²,
`MED_ALT` > 0):

| Misura | Area | n | Mediana | MAE | \|d\| < 2 m | \|d\| > 5 m |
|---|---|---|---|---|---|---|
| DSM First mediana − DTM contro `MED_ALT` | S. Chiara (1×1 km) | 555 | +0,20 m | 0,51 m | 96 % | 1 % |
| DSM First p90 − DTM contro `MAS_ALT` | S. Chiara | 555 | −0,77 m | 1,27 m | 85 % | 3 % |
| DTM 2014 mediana − `quota_DTM` | S. Chiara | 555 | +0,04 m | 0,18 m | — | — |
| DSM First mediana − DTM contro `MED_ALT` | Duomo (500 m) | 42 su 93 | +0,19 m | 1,64 m | 76 % | 7 % |

Le altezze del DB vengono dal LiDAR 2006-09 e il controllo usa il LiDAR 2014/18: due rilievi diversi ma non due metodi
indipendenti (come Milano, prova soprattutto la pipeline). Il punto debole è il **centro storico**: nel riquadro del
Duomo 51 edifici su 93 hanno altezza 0 (anche blocchi di 4.000–8.500 m² alti 16–17 m nel DSM). Lì le altezze vanno
prese da DSM − DTM (DBM o DSM First).

### 6.2 Area di prova

- **Ospedale S. Chiara**: EPSG:25832 **664500–665500 E, 5102000–5103000 N** (centro 665016/5102517); tessere
  `5h664551020`, `5h664551025`, `5h665051020`, `5h665051025`.
- **Centro – Duomo – MUSE** (Duomo 664078/5103668; MUSE 663563/5103178): **663500–664500 E, 5103000–5104000 N**;
  tessere `5h663551030`, `5h663551035`, `5h664051030`, `5h664051035`.

### 6.3 Istruzioni per Paolo

1. Scarica <https://siatservices.provincia.tn.it/idt/vector/p_TN_6a7806d8-63fa-4445-b009-9412c99d8fd2.zip> (Edifici
   P.A.T. 3D, **108 MB**, nessun login) in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\trento\edifici_pat_3d.zip`.
2. Per le 8 tessere del § 6.2 scarica DTM e DSM First, per esempio
   <https://siatservices.provincia.tn.it/stemdata/2014_lidar_dtm_asc/5h665051025_DTM.asc> e
   <https://siatservices.provincia.tn.it/stemdata/2014_lidar_dsmfirst_asc/5h665051025_DSMFirst.asc> (cambia il nome
   della tessera). Salva in `…\trento\dtm\` e `…\trento\dsm\` (**16 file, ~120 MB**). Le cartelle si aprono anche nel
   browser come elenco di file.
3. Facoltativo: le stesse 8 tessere del DBM (`…/2014_lidar_dbm_asc/<tessera>_DBM.asc`, ~60 MB) in `…\trento\dbm\`.

### 6.4 Cosa può fare il server da solo

- **Tutto**: elenco delle tessere dal WFS `stem:inqlid2014_new` (riquadro in EPSG:25832) e download diretto dei `.asc`;
  edifici dallo zip provinciale (URL fisso). In `zone/trento.toml` le fonti 2014/2018 possono sostituire quelle
  2006-2009 (tessere di 500 m al posto di 2 km: `lato_tessera` e `nome_tessera` da adattare) [D].
- Adattatore «Edifici P.A.T. 3D → corpi» (ancora da scrivere): `MAS_ALT` o `MED_ALT` → altezza, `quota_DTM` → base;
  gli edifici con altezza 0 vanno misurati con DSM − DTM.

## 7. Bolzano

### 7.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici (sagome) | **Provincia autonoma di Bolzano – INSPIRE «Edifici» `p_bz-Inspire:BU.Building`** (`CURRENT_USE`, `ELEVATION_REF` «topOfConstruction», `HORIZONTAL_GEOM_REF`) e **«Parti di un edificio» `BU.BuildingPart`** (`BUILDING_ID`) | pubblicazione 15/03/2024, aggiornamento biennale; `BEGIN_LIFESPAN_VERSION` **2026-07-08** | [D] | WFS 2.0, GeoJSON, EPSG:25832, **geometrie 2D** (`srsDimension="2"`) | data.civis.bz.it: `cc-zero`; `access_constraints` `https://creativecommons.org/publicdomain/zero/1.0/deed.it` | **automatico**: `https://geoservices8.civis.bz.it/geoserver/p_bz-Inspire/ows` | — | [V] ospedale: 135 parti nel riquadro di 600 m; Duomo: 1.674 parti. **Nessuna altezza** (l'abstract parla di LoD4, ma il servizio è 2D) |
| DTM | Provincia – DTM 0,5 m (aree insediative) e 2,5 m (già in `zone/bolzano.toml`) | 2013 [D] | 0,5 m | WCS 2.0.1 GeoTIFF float32, EPSG:25832 | CC0 1.0 | automatico | ritaglio 600×600 m: 9,4 MB | [V] `GetCoverage` 200 sui due riquadri |
| DSM | Provincia – DSM 0,5 m (aree insediative; scheda: creazione **30/11/2013**, probabilmente volo Solar Tirol 2013 [D]) | ~2013 | 0,5 m | come il DTM | CC0 1.0 | automatico | 9,4 MB a ritaglio | [V] Duomo: DSM − DTM 60,0 m al p90 del campanile, 67 m alla punta |
| DSM/DTM (nuovo) | Provincia – DSM e DTM «EtschAdige» 0,2 m **2024** (corridoio dell'Adige, 659857–678104 E) | 2024 | 0,2 m | WCS | CC0 [D] (stessa serie) | automatico | — | [V] coperture presenti, ma **vuote (nodata) sull'ospedale** e fuori dal Duomo: non coprono la città |

**Prova (08/11/2026)** [V]: senza altezze nel DB, si misura DSM − DTM sulle parti INSPIRE (sagoma ristretta di 1 m,
area ≥ 30 m²). Ospedale: 79 parti misurate, corpi alti fino a 37–38 m; **una parte di 3.336 m² (edificio 1199541,
677489/5152181) risulta alta 0,0 m**: è costruita dopo il DSM (~2013). Duomo: 968 parti misurate, mediana 17,3 m,
campanile 53,3 m in mediana e 60,0 m al p90 (alto 65 m [D]). Le sagome sono aggiornate, il DSM no: Bolzano prova bene il
caso «sagoma ufficiale recente + LiDAR vecchio» (edifici nuovi da segnare «non presenti nel rilievo»).

### 7.2 Area di prova

- **Ospedale di Bolzano** (via Böhler): EPSG:25832 **677000–677600 E, 5151700–5152300 N** (centro 677308/5152008).
- **Duomo – centro storico**: **680300–680900 E, 5151700–5152300 N** (Duomo 680630/5152021).

### 7.3 Istruzioni per Paolo

Nessun download necessario: tutto è nei servizi. Facoltativo, per avere i file sul PC, apri nel browser e salva in
`C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\bolzano\` (4 file da 9,4 MB):
`https://geoservices9.civis.bz.it/geoserver/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageId=p_bz-Elevation__DigitalElevationModel-0.5m&format=image/tiff&subset=E(677000,677600)&subset=N(5151700,5152300)`
e lo stesso con `DigitalTerrainModel-0.5m` e con il riquadro del Duomo (`E(680300,680900)`).

### 7.4 Cosa può fare il server da solo

- Sagome: WFS `BU.BuildingPart` (o `BU.Building`) per riquadro, CC0, come le sagome regionali del Veneto
  (`sagome_regionali.toml`), ma con altezze da **DSM − DTM** (zona LiDAR `bolzano` già pronta) invece che da OSM.
- DSM e DTM: WCS già configurati in `zone/bolzano.toml`.

## 8. Cosa non è disponibile o non è compatibile

| Città | Dato | Motivo |
|---|---|---|
| Torino | tutti i servizi piemontesi e del Comune | non raggiungibili dal container (connessione chiusa o 503): da provare dal server |
| Torino | DSM recente ad alta risoluzione | solo ICE 2009-11 a 5 m (CC BY 4.0) e PST 1 m sul Po (da verificare) |
| Torino | Carta tecnica comunale in zip | URL in cartella `sec`: possibile accesso riservato [D] |
| Genova | nessun limite | — |
| Venezia | altezze degli edifici | DBGT 2010 del Comune non pubblicato con le unità volumetriche; sagome regionali senza altezze |
| Venezia | DSM | nessun DSM aperto regionale o comunale; PST solo aste fluviali (laguna da verificare) |
| Venezia | portale del Comune | protetto da Incapsula: da controllare dal browser |
| Trieste | DSM/DTM in automatico | solo da Eagle.fvg a mano; licenza IODL 2.0 dalla pagina regionale ma «non indicata» nella scheda |
| Trieste | edifici recenti | CTRN ed. 2 del 2003; DBTsped 2017-20 con blocchi accorpati |
| Trento | altezze nel centro storico | 21 % degli edifici provinciali (55 % nel riquadro del Duomo) con altezza 0 |
| Bolzano | altezze degli edifici | sagome INSPIRE in 2D; altezze solo da DSM − DTM (DSM ~2013) |
| tutte | PST MASE | app offline fino al 10/11/2026, WMS con immagini vuote: copertura non verificabile oggi |
| tutte | LiDAR PNRR | non ancora pubblicato |

Nessuna fonte proposta ha licenza incompatibile: CC BY 4.0 (Genova, Liguria, Trento, Torino, Piemonte), CC0 (Bolzano),
IODL 2.0 (Veneto, LiDAR FVG secondo la pagina regionale, Edifici 3D Arpa dal portale ISPRA). Da chiarire: strati FVG
(«Non indicato» nelle schede), BDTRE UN_VOL («Condizioni sconosciute»), licenza del servizio Arpa.

## 9. Ordine consigliato e spazio

| Ordine | Cosa | Dove | Dimensione |
|---|---|---|---|
| 1 | Genova DSM + DTM 0,5 m, tavole 3931, 3831, 3723, 3721 | `citta_rif\genova\` | ~110 MB |
| 2 | Trento Edifici P.A.T. 3D | `citta_rif\trento\` | 108 MB |
| 3 | Trento DTM + DSM First 2014/18, 8 tessere | `citta_rif\trento\` | ~120 MB |
| 4 | Genova CTC 2018 DXF, tavole 3930, 3830, 3720 | `citta_rif\genova\ctc_dxf\` | 28 MB (190 MB estratti) |
| 5 | Torino BDTRE comune di Torino (e, se libera, carta tecnica comunale) | `citta_rif\torino\` | [D] (qualche centinaio di MB) |
| 6 | Trieste LiDAR 2017-20 da Eagle.fvg (DTM + DSM 0,5 m, 2 aree) | `citta_rif\trieste\lidar\` | [D] |
| 7 | Venezia: controllo del portale del Comune (nessun download se non c'è nulla) | `citta_rif\venezia\` | — |
| 8 | (dopo il 10/11) PST Torino, Venezia, Trieste, se coprono | `citta_rif\<città>\pst\` | qualche decina di MB [D] |
| — | facoltativi: Trento DBM (8 tessere), Bolzano 4 ritagli WCS, Torino ICE 5 m | | 60 + 38 MB + [D] |

Totale essenziale noto: **circa 0,37 GB** (Genova 0,14 + Trento 0,23), più Torino e Trieste da misurare. Molto meno di
Milano-Firenze-Roma, perché Genova, Trento e Bolzano danno tessere piccole con URL fissi.

## 10. Da aggiornare nel progetto (non fatto qui: `/home/claude/eu` non va toccato)

`fase10-edifici3d/fonti/regioni.toml`:
- **Provincia autonoma di Trento**
  - *dtm* e *dsm*: aggiungere «LiDAR PAT 2014/2018, 0,5 m» (DTM `p_TN:79c6cdf0-…`; DSM First `p_TN:9bb00ab2-…`;
    DSM Last `p_TN:4966f8b8-…`; DBM `p_TN:ee78298d-…`), CC BY 4.0, servizio
    `https://siatservices.provincia.tn.it/stemdata/2014_lidar_{dtm,dsmfirst,dsmlast,dbm}_asc/`, quadro WFS
    `stem:inqlid2014_new`, stato **«attiva»**, prova «08/11/2026: 5+5 tessere scaricate, DSM − DTM contro MED_ALT
    mediana +0,20 m su 555 edifici». La 2006/2009 resta come ripiego.
  - *edifici*: `altezza = "MIN_ALT, MED_ALT, MAS_ALT (m), quota_DTM; 21 % con 0"`; prova «zip letto: 147.481 edifici,
    PolygonZ, ETRF89/UTM 32N».
- **Provincia autonoma di Bolzano**
  - *edifici*: da «non disponibile» a **«attiva» (solo sagome)**: «INSPIRE BU.Building / BU.BuildingPart», CC0 1.0,
    servizio `https://geoservices8.civis.bz.it/geoserver/p_bz-Inspire/ows`, `altezza = "no (2D): da DSM − DTM"`; poi
    una voce in `sagome_regionali.toml` (con `crs = "EPSG:25832"`) ma con altezze dal LiDAR invece che da OSM.
  - *dsm*/*dtm*: annotare le coperture «EtschAdige 0,2 m 2024» (corridoio dell'Adige, non coprono Bolzano città).
- **Liguria**
  - *dsm*: da «non disponibile» ad **«attiva» (comunale)**: «Comune di Genova – DSM 50 cm e 1 m, LiDAR 2018»
    (`c_d969:c39859c3-…`, `c_d969:ca077ad3-…`), CC BY 4.0, URL per tavola e quadri WFS `MEDIATORE:V_QU_*`.
  - *dtm*: aggiungere «Comune di Genova – DTM 50 cm e 1 m 2018» (`c_d969:44d9a724-…`).
  - *edifici*: nella prova, «08/11/2026: San Martino, DSM 2018 comunale − z di gronda mediana −0,11 m, 88 % entro
    2 m»; fonte comunale aggiuntiva «CTC 2018 DXF» in stato «in attesa» (adattatore DXF).
- **Friuli Venezia Giulia**
  - *edifici*: indicare di usare gli strati **ED2** (`DATA_VOLO`; a Trieste 2003) e aggiungere **DBTsped**
    (`EDIFICI:DBS_EDIFICATO`, `ALTEZZA_M`, blocchi accorpati) come «in attesa» (licenza «Non indicato»).
  - *dtm*/*dsm*: motivo aggiornato: «pagina regionale: IODL 2.0 come licenza standard; scheda IRDAT senza licenza;
    download solo da Eagle.fvg (ospite), nessun WCS». Resta «in attesa» (download non provato).
- **Piemonte**
  - *edifici*: aggiungere «Comune di Torino – Edificato del DBGT» (`c_l219:78dc5b8a-…`, CC BY 4.0, 1:1.000, WFS
    `wfs_sicc140_edificato_dbgt`) e «Arpa Piemonte – Edifici 3D 2017» (`arlpa_to:EDIF_2017-12-21-11:00`, `ELEV`,
    IODL 2.0 dal portale ISPRA), entrambe «in attesa» (non raggiungibili dal container); annotare il modello di URL
    BDTRE per comune.
  - *dtm*: il servizio è il WCS `wcs_ice_2009_2011_dtm`.
- **Veneto**
  - *edifici*: annotare che a Venezia le sagome sono del DBGT del Comune 2010 (lotti in `rv:c0101101_lotti_dbgt`) e che
    il riquadro WFS in EPSG:6876 va in ordine N, E (`urn:ogc:def:crs:EPSG::6876`).
- **[nazionale] PST**: 08/11/2026 GetMap ancora vuoto anche per Piemonte, Liguria, Veneto e FVG.

`documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
- **Bolzano**: riscrivere. Le sagome ci sono (INSPIRE, CC0): chiedere solo se esiste una versione **con altezze** o
  3D (l'abstract dice LoD4, il WFS è 2D), e se il DSM 0,5 m verrà aggiornato (il nuovo corpo dell'ospedale manca).
- **Piemonte**: aggiungere che i servizi WFS, il geoportale e il download BDTRE non rispondono dal nostro ambiente, e
  chiedere la licenza di UN_VOL insieme a quella del servizio Arpa «Edifici 3D 2017».
- **Friuli Venezia Giulia** (sezione «fonte attiva»): nel chiarimento sulla licenza aggiungere il DBTsped (copertura
  reale e origine di `ALTEZZA_M`) e chiedere un download in blocco o un WCS del LiDAR 2017-2020; citare la pagina
  regionale con la IODL 2.0.
- **Veneto** (sezione «fonte attiva»): possibile richiesta facoltativa alla Regione o al Comune di Venezia del DBGT
  «Lotto Comune di Venezia 2010» con le unità volumetriche (quote di gronda).
- **Trento**: nessuna lettera; annotare il LiDAR 2014/2018 e i campi d'altezza trovati.
- **Liguria**: nessuna lettera; annotare le fonti comunali di Genova.

`DA_FARE.md`: «Città di riferimento del Nord» con i passi del § 9; dal server: prove dei servizi di Torino; dopo il
10/11: PST per Torino, Venezia e Trieste.

## 11. Prove dal vivo (08/11/2026)

| Prova | Esito |
|---|---|
| CSW RNDT `geodati.gov.it/RNDT/csw` (ricerche per Torino `c_l219`, Piemonte, Genova `c_d969`, Liguria, Veneto, FVG, PAT, Bolzano) | 200; schede lette con licenza e collegamenti |
| `siatservices.provincia.tn.it/idt/vector/` e indice a distanza dello zip Edifici P.A.T. 3D; download completo (108 MB) e lettura con pyshp | 147.481 edifici, campi e `.prj` letti; zip poi cancellato |
| `siatservices.provincia.tn.it/stemdata/2014_lidar_*_asc/` (elenchi) e 5 tessere DTM, 5 DSM First, 2 DBM | 200; 25.201 tessere per prodotto; confronto con gli edifici |
| WFS `siat.provincia.tn.it/geoserver/wfs` `stem:inqlid2014*` | 200, tessere e percorsi dei file sul riquadro dell'ospedale |
| CKAN `data.civis.bz.it` (edifici, LiDAR, DSM) | 200; INSPIRE BU CC0 |
| WFS `geoservices8.civis.bz.it/…/p_bz-Inspire` (GetCapabilities, DescribeFeatureType, GetFeature GeoJSON e GML) | 200; 2D; 135 e 1.674 parti |
| WCS `geoservices9.civis.bz.it` (DescribeCoverage, 6 GetCoverage) | 200 image/tiff; EtschAdige 2024 vuoto sull'ospedale |
| WFS `geoservices1.civis.bz.it/…/p_bz-GeographicalGrids` (coperture LiDAR) | Solar Tirol 2013 copre ospedale e Duomo |
| WFS FVG `serviziogc.regione.fvg.it/geoserver/EDIFICI` (GetCapabilities 46 strati, DescribeFeatureType, GetFeature ED1/ED2/DBS) | 200; Cattinara, centro, Faro |
| WCS `serviziogc` e `irdat-ortofoto` | nessun DTM/DSM (solo ombreggiatura) |
| `irdat.regione.fvg.it/Distributore/download` (specifiche DBTsped, PDF) | 200; zip dello shape: 404 |
| Eagle.fvg (pagina ospite) | 200; applicazione con gettone ospite, nessun servizio di download documentato |
| WFS Liguria `M2237:L8178` su San Martino | 200, 479 elementi |
| Genova: geoserver WFS (253 strati), MapStore (`geostore/data/1000003072`), GetFeatureInfo HTML dei quadri, download DSM/DTM 3931 e 3723, DXF 3930 (letto con ezdxf), dimensioni con HEAD | 200; link per tavola trovati e provati; DXF `CAD/DXF/1000/3931.zip`: 404 (le CTC in DXF ci sono solo per le tavole 1:2.000) |
| WFS Veneto `idt2-geoserver` (GetCapabilities 1.071 strati, DescribeFeatureType, GetFeature su San Marco e Angelo, lotti DBGT, quadro DTM 5 m) | 200; ordine N, E del riquadro |
| `dati.venezia.it`, `geoportale.comune.venezia.it` | Incapsula / 403 |
| Portali piemontesi e del Comune di Torino, `webgis.arpa.piemonte.it`, `datigeo-piem-download.it` | connessione chiusa, 000 o 503 (proxy); WebFetch: non in lista |
| WMS PST `LIDAR_{PIEMONTE,LIGURIA,VENETO,FRIULI_VENEZIA_GIULIA}.map` | GetCapabilities 200; GetMap PNG vuoto |
| Nominatim (OpenStreetMap) | coordinate degli edifici noti |

Script delle prove in `/home/claude/citta_rif2/script/`: `confronto.py` (statistiche DSM − DTM sulle sagome),
`prova_tn.py`, `prova_bz.py`, `prova_ts.py`, `prova_ge.py`, `prova_ge_reg.py`, più `csw.py`, `cswrec.py`,
`zipindice.py`, `zipparziale.py` copiati dalla verifica precedente. Esiti in `nord/prova_*.txt`; i raster e gli zip
scaricati per le prove sono stati cancellati.

## 12. Fonti

Torino e Piemonte
- Edificato del DBGT del Comune: <https://geodati.gov.it/resource/id/c_l219:78dc5b8a-6c9d-4b1d-8257-5d27dfbc5378>, WFS
  <https://geomap.reteunitaria.piemonte.it/ws/siccms/coto-01/wfsg01/wfs_sicc140_edificato_dbgt?service=WFS&request=getCapabilities>
- Carta Tecnica del Comune: <https://geodati.gov.it/resource/id/c_l219:092bd977-cc13-48ab-8282-ef9434862ad5>,
  <https://geodati.gov.it/resource/id/c_l219:fc407e9b-74d9-4749-9a56-271913a1dca9>
- BDTRE: <https://geodati.gov.it/resource/id/r_piemon:903f1ad3-6821-4d87-b500-0c8028fd303b>; UN_VOL
  <https://geodati.gov.it/resource/id/r_piemon:6dacd512-8862-491a-a37b-c032cd54d081>; download per comune (2015):
  <https://wiki.openstreetmap.org/wiki/Piemonte/BDTRE-2015>
- Arpa Piemonte, Edifici 3D 2017: <https://geodati.gov.it/resource/id/arlpa_to:EDIF_2017-12-21-11:00>
- ICE 2009-2011 DTM 5 m e DSM: <https://geodati.gov.it/resource/id/r_piemon:224de2ac-023e-441c-9ae0-ea493b217a8e>,
  <https://geodati.gov.it/resource/id/r_piemon:12a0bdd2-166a-4825-8645-1a4605b70f48>
- PST Piemonte DSM FIRST 1 m: <https://geodati.gov.it/resource/id/m_amte:299FN3:26f1c7e3-4380-49de-873c-9e43d30804e4>

Genova e Liguria
- DSM 50 cm: <https://geodati.gov.it/resource/id/c_d969:c39859c3-3aad-45b5-a474-0bfaa854bddf>; DSM 1 m
  <https://geodati.gov.it/resource/id/c_d969:ca077ad3-6751-4d4e-93c7-13ff09c0aa7a>; DTM 50 cm
  <https://geodati.gov.it/resource/id/c_d969:44d9a724-e5ac-42ad-9c10-d4ffcaab4ebf>; LAS 2018
  <https://geodati.gov.it/resource/id/c_d969:0942a35c-da52-4604-83e8-853a93bd28cb>
- Mappa di scarico: <https://mappe.comune.genova.it/MapStore2/#/viewer/1000003072>; scheda
  <https://geodati.gov.it/resource/id/c_d969:fcdefdd4-1728-4429-a54b-f9f596f30773>
- CTC 2018: <https://geodati.gov.it/resource/id/c_d969:e7478020-a77e-45bf-aae2-f2da2ac686c3>
- Cartografia del Comune: <https://www.comune.genova.it/tutti-gli-argomenti/cartografia>
- CTR 3D regionale: <https://geodati.gov.it/resource/id/r_liguri:D.2237>, WFS
  <https://geoservizi.regione.liguria.it/geoserver/M2237/wfs?version=2.0.0&request=getcapabilities>

Venezia e Veneto
- Edifici del Veneto: <https://geodati.gov.it/resource/id/r_veneto:edifici_veneto>; edificato della provincia
  <https://geodati.gov.it/resource/id/r_veneto:edi_ve>; WFS
  <https://idt2-geoserver.regione.veneto.it/geoserver/wfs?service=WFS&request=GetCapabilities&version=1.1.0>
- DTM 5 m LiDAR: <https://geodati.gov.it/resource/id/r_veneto:c0101071_Lidar5m>
- PST Veneto DSM FIRST 1 m: <https://geodati.gov.it/resource/id/m_amte:299FN3:f451a878-27b3-43be-bc19-6eeb1362392a>
- Regione Veneto, CTR e DB topografico: <https://www.regione.veneto.it/web/ambiente-e-territorio/carta-tecnica-regionale>,
  <https://www.regione.veneto.it/web/ambiente-e-territorio/db-topografico>
- Comune di Venezia, cartografia aperta annunciata nel 2013: <https://lists.openstreetmap.org/pipermail/talk-it/2013-February/033154.html>

Trieste e FVG
- Edificato 110: <https://geodati.gov.it/resource/id/r_friuve:m6528-cc-i9796>; WFS
  <https://serviziogc.regione.fvg.it/geoserver/EDIFICI/wfs?request=GetCapabilities&version=2.0.0>
- DBTsped: <https://geodati.gov.it/resource/id/r_friuve:m10910-cc-i11780>
- LiDAR 2017-2020: <https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826>,
  <https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11647>; Eagle.fvg
  <https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest>
- Licenza standard IODL 2.0: <https://www.regione.fvg.it/rafvg/cms/RAFVG/ambiente-territorio/conoscere-ambiente-territorio/FOGLIA4/>
- PST FVG DSM FIRST 2 m: <https://geodati.gov.it/resource/id/m_amte:299FN3:fd1f9385-5d3f-4d68-e57f-a223502f1b84>

Trento
- Edifici P.A.T. 3D: <https://geodati.gov.it/resource/id/p_TN:6a7806d8-63fa-4445-b009-9412c99d8fd2>, file
  <https://siatservices.provincia.tn.it/idt/vector/p_TN_6a7806d8-63fa-4445-b009-9412c99d8fd2.zip>
- LiDAR PAT 2014/2018: DTM <https://geodati.gov.it/resource/id/p_TN:79c6cdf0-c73a-46ba-870c-704bf4e27ac3>, DSM First
  <https://geodati.gov.it/resource/id/p_TN:9bb00ab2-8c9e-4afd-aac4-8b6caef3edc9>, DBM
  <https://geodati.gov.it/resource/id/p_TN:ee78298d-818c-492b-bdeb-07a2ef173716>, quadro
  <https://geodati.gov.it/resource/id/p_TN:9f2cc32d-1030-430d-be85-7f95c9cc24ea>; cartelle
  <https://siatservices.provincia.tn.it/stemdata/2014_lidar_dtm_asc/>
- Pagina della Provincia sul rilievo: <https://www.provincia.tn.it/News/Approfondimenti/Rilievo-Lidar-del-territorio-della-Provincia-di-Trento>

Bolzano
- INSPIRE Edifici e Parti: <https://data.civis.bz.it/dataset/inspire-edifici-buildings>,
  <https://data.civis.bz.it/dataset/inspire-parti-di-un-edificio-building-parts>; WFS
  <https://geoservices8.civis.bz.it/geoserver/p_bz-Inspire/ows?service=WFS&version=2.0.0&request=GetCapabilities>
- DSM 0,5 m: <https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Elevation:DigitalElevationModel-0.5m>;
  DTM 0,5 m <https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Elevation:DigitalTerrainModel-0.5m>;
  WCS <https://geoservices9.civis.bz.it/geoserver/ows?service=WCS&version=2.0.1&request=GetCapabilities>

Nazionali
- PST MASE: <https://gn.mase.gov.it/portale/distribuzione-dati-pst>; app
  <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>
