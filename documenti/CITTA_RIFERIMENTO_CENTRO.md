# Città di riferimento: Perugia, Ancona, L'Aquila, Bari, Potenza – fonti, licenze e istruzioni di download

Verifica dell'08/11/2026, fatta dal container di sviluppo senza login, account o captcha e senza aggirare blocchi.
Nessun file di `/home/claude/eu` è stato modificato: le prove sono in `/home/claude/citta_rif2/` (`centro/`, `script/`).
Legenda: **[V]** verificato con una prova dal vivo o letto su una pagina ufficiale; **[D]** dedotto o da confermare.

Scopo: cinque città del Centro-Sud con edifici noti dove confrontare **sagome e altezze dei DB topografici** con
**DSM − DTM**, per provare gli adattatori regionali fuori da Lombardia, Toscana e Lazio (modello:
`CITTA_RIFERIMENTO_MILANO_FIRENZE_ROMA.md`).
Cartella dei download di Paolo: `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\<città>\`.

Raggiungibilità dal container (08/11/2026): RSDI Basilicata **ora risponde** (il 04/11 dava 503); SIT Puglia e
`cartografia.sit.puglia.it` rispondono; Regione Marche risponde (niente captcha oggi), ma `static.regione.marche.it`
(dove rimandano i PDF e gli zip della pagina Repertorio) ha una catena di certificati incompleta e fallisce la verifica
TLS; Cartanet Abruzzo risponde (a tratti 503); **tutti i siti della Regione Umbria** (`umbriageo`, `siat`,
`dati.umbria.it`, `geo.umbriaterritorio.it`) chiudono la connessione («connection reset») e non sono nella lista di
WebFetch; `opendata.regione.abruzzo.it` e `www.regione.abruzzo.it` non rispondono. Il portale PST del MASE è offline
fino al 10/11/2026: le sue WMS LiDAR (Marche, Abruzzo, Puglia, Basilicata) rispondono ma con immagini vuote, quella
dell'Umbria dà 500.

## 1. In breve

| Città | Edifici con altezze | DTM | DSM | Valore come riferimento |
|---|---|---|---|---|
| **Potenza** | Regione Basilicata, **DBGT 1:5.000, `UN_VOL` con `un_vol_av`** (volo 2013 [D]), IODL 2.0, **WFS provato** + zip per comune (89,5 MB) e regionale (71,5 MB) | Regione Basilicata **DTM 5 m da LiDAR 2013**, IODL 2.0, **WCS provato** | Regione Basilicata **DSM 5 m da LiDAR 2013**, IODL 2.0, **WCS provato** | **Il migliore del gruppo**: tutto aperto, tutto automatico, nessun adattatore nuovo per i campi. Prova su ospedale San Carlo e centro: (DSM p90 − DTM) − `un_vol_av` mediana 0,0 / −0,7 m, 63–71 % entro 2 m; DSM − (quota base + altezza) mediana +0,1 m, 94 % entro 2 m |
| **Bari** | Regione Puglia, **CTR 1:5.000 (volo 2006)** in SHP per elemento: poligoni degli edifici + **punti «quota gronda» e «quota piede»**, IODL 2.0, download diretto provato | Regione Puglia **DTM 8 m** (2006), IODL 2.0, ASCII per elemento, provato | **nessun DSM aperto** regionale o comunale: solo PST MASE (costa, da verificare dopo il 10/11) | Buono per le **sagome e le quote** (1:5.000, quote assolute di gronda e piede); vecchio (2006) e senza DSM per il controllo. Piede contro DTM: mediana +0,18 m, 90 % entro 1 m (14.893 punti) |
| **Ancona** | Regione Marche, **DBGT 2019 (CTR 1:10.000)**: `edificio` con **`edifc_qm` = quota di gronda** + `punto_quotato` «al piede», CC BY 4.0, zip regionali provati | Regione Marche **DTM 10 m 2019** (CC BY 4.0, download da browser: TLS del server statico non valido dal container) | **nessun DSM aperto**: solo PST MASE (costa, da verificare) | Discreto: copertura regionale recente (2019-2020) con un'altezza per edificio (gronda − piede); scala 1:10.000, edifici complessi appiattiti (Duomo 10,4 m) |
| **Perugia** | Regione Umbria: **CTR 1:2.000 del centro storico (volo 2000)**, CTR 10k Tevere-Trasimeno (volo 2013), Fabbricati 2005-10 senza altezze; CC BY 3.0 (schede RNDT) / CC BY 4.0 (dati.gov.it) | nessun DTM regionale trovato (solo PST) | solo PST MASE Umbria (aste fluviali: copertura di Perugia dubbia) | **Non verificabile oggi**: tutti i portali umbri sono irraggiungibili dal container. Da scaricare a mano e controllare se le CTR hanno quote di gronda |
| **L'Aquila** | Regione Abruzzo: CTR/DBTI 2007 1:5.000 in SHP e DTM 10 m 2007 «disponibili presso la Regione» (**solo su richiesta**), licenza non indicata | DTM 10 m 2007 (su richiesta) | solo PST MASE Abruzzo (asta dell'Aterno: da verificare) | **Debole**: niente edifici con altezze scaricabili; resta OSM finché la Regione non risponde alla lettera |

Novità rispetto a `fonti/regioni.toml` e a `LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
- **Basilicata**: RSDI raggiungibile; **WFS `dbgt_0201:un_vol`** (EPSG:25833, `un_vol_av`, geometria con Z = quota della
  base), **WCS `rsdi_wcs`** con DTM e DSM 5 m (valori in float32, non solo immagini), zip delle unità volumetriche di
  tutta la regione (`webGis/shape-zip/unita_volumetrica.zip`, 71,5 MB) e del DBGT per comune
  (`downloadProd/dbgt_ctr_comune_download/<codice>.zip`). Licenza **IODL 2.0** nelle schede e nel PDF dentro lo zip.
  Edifici, DTM e DSM possono passare ad «attiva»; la lettera alla Basilicata non serve più. [V]
- **Puglia**: la CTR 1:5.000 2006 si scarica per elemento in SHP (`cartografia.sit.puglia.it/download/CTR/SHP/<foglio>/<elemento>_ctr.zip`)
  con i punti quotati di gronda e di piede degli edifici; il DTM 8 m per elemento in ASCII (virgola decimale). Licenza
  IODL 2.0 nelle schede RNDT di CTR e DTM. [V]
- **Marche**: il DBGT 2019 si scarica per classe su tutta la regione (`giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/<classe>.zip`);
  `edificio` ha la quota di gronda (`edifc_qm`), `punto_quotato` la quota al piede di ogni edificio; c'è anche il
  derivato «Edificato 2019» con `QUOTA1` (piede) e `QUOTA2` (gronda). Licenza CC BY 4.0 dichiarata nella pagina
  OpenData (D.G.R. 783/2017). Niente captcha oggi. [V]
- **Umbria**: esistono CTR 1:2.000 del centro di Perugia (2000) e CTR 10k Tevere-Trasimeno (2013), ma non sono
  raggiungibili dal container; la WMS dello strato 02 del DBGT Tevere-Trasimeno ha condizioni «non commerciali». [V]
- **Abruzzo**: Cartanet risponde; DTM 10 m e CTR/DBTI 2007 risultano solo «disponibili presso la Regione». [V]

## 2. Potenza

### 2.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici (servizio) | **Regione Basilicata – DBGT, classe 020101 «Unità volumetrica»**, WFS `dbgt_0201:un_vol` (campi `un_vol_por`, `un_vol_av`, `cediuv`, `scril`) | DBGT presentato il 21/07/2014; scheda 15/09/2015; volo 2013 [D] (ortofoto e LiDAR regionali 2013) | 1:5.000 | WFS 2.0 GeoServer, GeoJSON, **EPSG:25833**; geometria **PolygonZ: Z = quota della base** del volume | scheda RNDT `r_basili:26e21af8:14ff44204d8:214c`: «Licenza IODL 2.0 – link: https://www.dati.gov.it/content/italian-open-data-license-v20»; WFS: Fees e AccessConstraints «NONE» | **automatico**, nessun limite di oggetti dichiarato (5.000 oggetti in 2 s) | — | [V] San Carlo: 50 volumi in 600×400 m, padiglione principale 38,6 m; centro: 674 volumi; comune: 38.552 volumi nel riquadro 15×20 km |
| Edifici (comune) | DBGT per comune, **`17076063.zip`** (Potenza): `unita_volumetrica_17076063.shp` (`ALTEZZA_VO`, `PORZIONE`, `TIPO_PORZ`, `CEDIUV`), `edifici_is_*` (uso, tipologia, stato), `edifici_min_is_*`, `edifici_max_estens_*` | come sopra | 1:5.000 | Shapefile **Polygon 2D**, EPSG:25833 | `informazioni_e_precisazioni.pdf` nello zip: «Licenza: Italian Open Data License 2.0» | download diretto, link dal WFS `confini:limiti_comunali_download_dbgt` (campo `download`) | **89.543.379 byte** | [V] 27.330 volumi; stessi `CEDIUV` e altezze del WFS |
| Edifici (regione) | `unita_volumetrica.zip` (tutta la Basilicata) | file del 08/10/2015 | 1:5.000 | Shapefile **PolygonZ**, ETRS89/UTM 33N | come sopra | download diretto (link nella scheda RNDT) | **71.544.070 byte** (326 MB estratti) | [V] 477.261 volumi (`altezza_vo`, `porzione`: 01 al suolo 99 %, 08 sotterranea, 03/04 portici e sottopassaggi) |
| DTM | **Regione Basilicata – DTM 5 m** («Anno di rilievo: 2013»; punti LiDAR Ground + Model Keypoint) | 2013 | 5 m, tavole 1000×1000 celle | **WCS 2.0.1** `rsdi_wcs__dtm_5m`, GeoTIFF float32, EPSG:25833 (anche ASCII Grid per tavola dal viewer) | scheda `r_basili:9EE9C09A-…`: «Licenza IODL 2.0» | **automatico** (WCS); a mano dal viewer «Modello Digitale del Terreno» | 1,2×1 km: 200 kB; 10×9 km: 16,8 MB | [V] ritagli a San Carlo (685–822 m) e nel centro |
| DSM | **Regione Basilicata – DSM 5 m** (punti Ground, Low/Medium/High Vegetation, Building, Model Keypoint: **LiDAR**) | 2013 [D] (stesso rilievo del DTM) | 5 m | WCS `rsdi_wcs__dsm_5m`, GeoTIFF float32 | scheda `r_basili:28FFB196-…`: «Licenza IODL 2.0» | **automatico** (WCS) | come il DTM | [V] ritagli a San Carlo (685–832 m) e nel centro. La WMS `maps_dsm` dà solo immagini colorate; il WCS generale è spento («Service WCS is disabled»): usare lo spazio `rsdi_wcs` |
| DSM/DTM PST | PST MASE Basilicata 1 m (aste fluviali) | 2008-13 [D] | 1 m | GeoTIFF | CC BY 4.0 (PST) | app PST (offline fino al 10/11) | — | non serve: c'è il LiDAR regionale (5 m); a 1 m solo se il PST copre il Basento a Potenza |

**Prova di coerenza (08/11/2026, volumi ≥ 100 m², sagoma ristretta di 2,5 m, DTM e DSM 5 m dal WCS)** [V]:

| Area | Volumi | (DSM p90 − DTM) − `un_vol_av` | \|d\| < 2 m | \|d\| > 5 m | DSM p90 − (Z base + `un_vol_av`) | \|d\| < 2 m |
|---|---|---|---|---|---|---|
| Ospedale San Carlo | 34 | mediana 0,00 m, MAE 1,85 m | 71 % | 6 % | mediana +0,55 m, MAE 1,35 m | 88 % |
| Centro storico (Cattedrale, Torre Guevara) | 674 | mediana −0,74 m, MAE 2,28 m | 63 % | 11 % | mediana +0,13 m, MAE 0,81 m | 94 % |

La Z delle sagome è la **quota più bassa della base** (in pendenza il DTM medio sotto la sagoma è +0,8 m più alto):
per questo «Z + altezza» coincide con il DSM meglio di «DTM + altezza». Il DBGT e il LiDAR sono dello stesso periodo
(2013) ma sono prodotti diversi (restituzione fotogrammetrica contro punti laser): il confronto prova la pipeline e la
coerenza delle quote, non la data. Valori notevoli: padiglione principale del San Carlo 38,6 m (19.833 m²); campanile
della Cattedrale di San Gerardo, volume di 39 m² alto 38,6 m; volume di 48,2 m accanto alla Torre Guevara (sulla scarpata:
altezza misurata dal piede più basso) [V sui dati, altezza reale non verificata].

### 2.2 Area di prova

- **Centro storico – Cattedrale – Torre Guevara**: EPSG:25833 **567400–568800 E, 4498500–4499500 N** (Cattedrale
  568191/4499147, Torre Guevara 568499/4499135).
- **Ospedale San Carlo**: **567500–568700 E, 4500000–4501000 N** (centro 568129/4500441).
- Riquadro di tutta la città per i raster: 563000–573000 E, 4495000–4504000 N.

### 2.3 Istruzioni per Paolo

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
4. Non serve altro: il server può rifare tutto da solo (§ 2.4).

### 2.4 Cosa può fare il server da solo

- **Edifici**: WFS `https://rsdi.regione.basilicata.it/rbgeoserver2016/ows`, `service=WFS&version=2.0.0&request=GetFeature&typeNames=dbgt_0201:un_vol&outputFormat=application/json&srsName=EPSG:25833&bbox=<x0,y0,x1,y1>,EPSG:25833`
  (paginazione con `count`/`startIndex`). Campi come il DBGT lombardo in minuscolo (`un_vol_av`, `un_vol_por`,
  `cediuv`); manca `un_vol_qe`, ma la Z della geometria dà la quota della base: **quota di gronda = Z + `un_vol_av`**.
  Basta una zona `basilicata` nell'adattatore `lombardia_dbgt` (EPSG:25833, campi minuscoli) [D]. Nello SHP per comune
  il campo si chiama `ALTEZZA_VO`, nello zip regionale `altezza_vo`.
- **DTM/DSM**: WCS `https://rsdi.regione.basilicata.it/rbgeoserver2016/rsdi_wcs/ows`, `GetCoverage` con
  `coverageId=rsdi_wcs__dtm_5m` / `rsdi_wcs__dsm_5m`, `subset=E(...)&subset=N(...)` in EPSG:25833, GeoTIFF float32
  (nodata −9999). Un riquadro di 10×9 km in 3 s.
- Elenco dei comuni con il link dello zip: WFS `confini:limiti_comunali_download_dbgt` (campi `comune_ist`, `download`).

## 3. Bari

### 3.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Puglia – Carta Tecnica Regionale 1:5.000**, SHP per elemento: `CTR_<el>_pol` (poligoni, `LAYER`, `DESCR`: «edificio civile», «capannone», «chiesa», «campanile», «tettoia», «baracca»…), `CTR_<el>_poi` (punti **«quota gronda edificio»**, **«quota piede fabbricato»**, «quota colmo edificio», «quota al suolo»), `CTR_<el>_lin` («dividente edificio civile», «limite colmo») | volo ago.–nov. 2006 (piccole aree marzo 2007); file del 15/04/2009 | 1:5.000 | Shapefile **PolygonZ/PointZ** senza `.prj`: **WGS84/UTM 33N (EPSG:32633)** (scheda RNDT; verificato: la Basilica di San Nicola coincide con OSM al 94 %, scarto del baricentro 0,3 m); c'è anche il DWG | scheda RNDT `r_puglia:e5fdf473-…` «Cartografia Tecnica Regionale – CTR»: «Italian Open Data License (IODL 2.0)» | download diretto per elemento: `http://cartografia.sit.puglia.it/download/CTR/SHP/<foglio>/<elemento>_ctr.zip` (anche https); elenco dalla pagina «Download – Cartografie», foglio **438 «Bari»** | 3–7,4 MB per elemento (438073: 7.442.059 byte) | [V] 438073 (Policlinico, Murat): 2.061 edifici, 15.294 punti di gronda, 14.505 di piede; 438074 (Bari Vecchia): 871 edifici, 6.687 gronde |
| Edifici (DBT) | Regione Puglia – **DBT Multiscala 2006** (copertura topologica, 1:5.000/1:2.000) | 2006 | 1:5.000 | solo consultazione web (`webapps.sit.puglia.it/freewebapps/DBTICoperturaTopologica`) | scheda `r_puglia:63d5dd1e-…`: «Nessuno», «Dato pubblico» (**nessuna licenza**) | non scaricabile | — | [V] |
| DTM | **Regione Puglia – DTM** (livello 3 Intesa GIS, dalle stesse riprese del 2006) | 2006 | **8 m** | ASCII Grid per elemento 5k (`g_<el>.asc`, **virgola decimale**, nodata −9999), EPSG:32633 | scheda `r_puglia:85898eba-…`: «Italian Open Data License (IODL 2.0)» | download diretto: `http://cartografia.sit.puglia.it/download/DTM/ASC/<foglio>/<elemento>_asc.zip` | 0,2–0,55 MB per elemento | [V] 438061–438074 scaricati; piede degli edifici contro DTM: mediana +0,18 m, MAE 0,50 m, 90 % entro 1 m |
| DSM | **Nessun DSM aperto** della Regione o del Comune | — | — | — | open data del Comune di Bari (CKAN): nessun dato cartografico (solo «Edifici sensibili», «Civilario») | — | — | [V] dati.puglia.it: 0 risultati per DTM/lidar |
| DSM (nazionale) | PST MASE – «DSM FIRST/LAST LiDAR 1 m – Regione Puglia» (`m_amte:299FN3:05e815e5-…`, costa e aste fluviali) | 2008-13 [D] | 1 m | GeoTIFF | CC BY 4.0 (PST) | app PST (offline fino al 10/11) | — | [V] WMS `LIDAR_PUGLIA.map` risponde ma vuota; **copertura del lungomare di Bari probabile [D]**, da verificare |

Attenzione: nel centro di Bari i poligoni degli edifici sono **isolati interi** (i corpi sono separati da linee
«dividente edificio civile» nello strato `_lin`), con più punti di gronda per poligono: l'altezza «mediana gronda −
piede minimo» per poligono è una media dell'isolato. Per corpi singoli servono la poligonizzazione con le linee divisorie
o l'assegnazione dei punti di gronda ai sotto-poligoni [D]. Altezze ricavate (gronda − piede, 438073): mediana 8,2 m,
massimo 49,4 m; intorno al Policlinico fino a 30,8 m; campanile vicino alla Cattedrale 37,1 m [V sui dati].

### 3.2 Area di prova

Foglio 438 «Bari», elementi 1:5.000 (numerazione: 1 = NE, 2 = SE, 3 = SO, 4 = NO della sezione) [V]:

| Edificio | WGS84/UTM 33N (E, N) | Elemento 5k |
|---|---|---|
| Bari Vecchia, Basilica di San Nicola, Cattedrale | 656980, 4554930 / 656905, 4554701 | 438074 |
| Murattiano | 656983, 4553985 | 438074 / 438073 |
| Policlinico | 656338, 4552942 | 438073 |
| Madonnella, Japigia | > 657330 E | 438071 (quasi vuoto: costa), 438072 |
| San Paolo, Stanic (ovest) | 650300–653840 E | 438061, 438062 |

Riquadro consigliato: **655500–657400 E, 4552300–4555200 N** (Policlinico – Murattiano – Bari Vecchia).
PST: celle 0,01° tra **16,84–16,89 E, 41,10–41,14 N**.

### 3.3 Istruzioni per Paolo

1. Apri <http://www.sit.puglia.it/portal/portale_cartografie_tecniche_tematiche/Download/Cartografie>, scegli il foglio
   **«438 – Bari»** e, alla riga «Carta Tecnica Regionale formato Shape», **Vai al dettaglio**.
2. Scarica `438073_ctr.zip`, `438074_ctr.zip`, `438072_ctr.zip`, `438061_ctr.zip`, `438062_ctr.zip` (link diretti
   `http://cartografia.sit.puglia.it/download/CTR/SHP/438/4380xx_ctr.zip`; **23,5 MB** in tutto) in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\bari\ctr\`.
3. Torna al foglio 438, riga «Digital Terrain Model» → **Vai al dettaglio**, e scarica gli stessi elementi
   (`4380xx_asc.zip`, **2,0 MB** in tutto) in `…\citta_rif\bari\dtm8\`.
4. **Dopo il 10/11/2026**: nell'app PST (<https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>) «Seleziona
   area» su 16,84–16,89 E / 41,10–41,14 N; se compaiono «DSM FIRST LiDAR 1 m – Regione Puglia» e «DTM LiDAR 1 m»,
   aggiungili al carrello, «Scarica tutto» e salva in `…\citta_rif\bari\pst\`. Senza copertura, Bari resta senza DSM.

### 3.4 Cosa può fare il server da solo

- Scaricare CTR e DTM per elemento dagli URL fissi (nessun login, risposta 200 anche in https).
- Serve un **adattatore nuovo `puglia_ctr`**: poligoni `_pol` con `DESCR` di edificio; punti `_poi` «quota gronda
  edificio» dentro il poligono → gronda (mediana o per sotto-poligono), «quota piede fabbricato» entro 3 m → piede
  (minimo); altezza = gronda − piede; EPSG:32633 → 25833 (differenza centimetrica). Script di prova:
  `script/ctr_puglia_altezze.py` (2.001 altezze su 2.061 edifici nel 438073; 1 sola ≤ 0).
- DTM: leggere l'ASCII sostituendo la virgola decimale.
- Elenco elementi per foglio: la pagina del portale (POST `select_idfoglio`, poi `azionelink=dettaglioCTR&idF=<id>`)
  oppure i nomi standard `<foglio><sezione><elemento>`.

## 4. Ancona

### 4.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Marche – DBGT 2019 (CTR 1:10.000)**, classe **`edificio`**: `edifc_qm` (**quota di gronda**, uguale al punto di gronda nel 97,6 % dei casi), `edifc_uso`/`uso_name`, `edifc_ty`, `cr_edf_por`, `origine` (CTR / aggiornamento), `data_ini` 01/01/2020, `data_dbt` 30/06/2025 | aggiornamento 2019-2020 | 1:10.000 | Shapefile PolygonZ (Z = 0), **RDN2008/UTM 33N (EPSG:7792)** | pagina «Cartografia e informazioni territoriali – Elenco Opendata»: «Con la D.G.R. 783 del 10/07/2017 la Giunta ha reso fruibili, con licenza di tipo aperto (Open Data), i dati cartografici/geodatabase … Elenco degli Opendata disponibili con licenza Creative Commons Attribuzione 4.0 Internazionale», con «CARTA TECNICA REGIONALE 1:10.000 (DBGT 2019)» ed «EDIFICATO 1:10.000» | download diretto, tutta la regione: `https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/edificio.zip` | **51.153.447 byte** (dbf 695 MB, shp 122 MB) | [V] 453.585 edifici; ad Ancona 4.211 |
| Edifici (quote al piede) | DBGT 2019, classe **`punto_quotato`**: per ogni edificio un punto «su manufatto / edificio – al piede» e uno «in gronda o su copertura» (`pt_quo_q`) | 2019-2020 | 1:10.000 | Shapefile MultiPointZ, EPSG:7792 | come sopra | `…/CTR2019/DBT/punto_quotato.zip` | **56.134.010 byte** (dbf 1,26 GB) | [V] 578.201 + 578.201 punti; ad Ancona 4.182 edifici con piede e gronda, altezza mediana 11,1 m, nessuna ≤ 0 |
| Edifici (derivato) | «**Edificato 2019**» (`EDIFICATO_RM.shp`: `QUOTA1` = quota al piede, `QUOTA2` = quota in gronda, `CLASSE` EDIFC/EDI_MIN/ELE_CP) | 2019 | 1:10.000 | Shapefile 2D, EPSG:7792 | pagina OpenData (CC BY 4.0); la specifica non cita la licenza | download da `www.regione.marche.it/Portals/0/…/Banche_dati/Edificato-2019.zip` (rimanda a `static.regione.marche.it`) | non letta [D] | [V] specifica letta con WebFetch; zip non scaricabile dal container (catena TLS incompleta di `static.regione.marche.it`): **da browser** |
| DTM | Regione Marche – **DTM 10 m (2019)** («Orografia 2019»: DTM, curve, punti quotati) | 2019 | 10 m | GeoTIFF / zip | CC BY 4.0 (pagina OpenData) | da browser: `…/Banche_dati/Orografia-2019-DTM.zip` o `.tif` | non letta [D] | [V] link nella pagina Repertorio; download non provato (TLS) |
| DSM | **Nessun DSM aperto** della Regione | — | — | — | servizi ArcGIS `BasiRaster/DEM`: «Token Required» | — | — | [V] |
| DSM (nazionale) | PST MASE – «DSM FIRST LiDAR 1 m – Regione Marche» (`m_amte:299FN3:e7d3bc78-…`, costa e aste fluviali) | 2008-13 [D] | 1 m | GeoTIFF | CC BY 4.0 (PST) | app PST (offline fino al 10/11) | — | [V] WMS `LIDAR_MARCHE.map` vuota; **copertura del porto e del centro probabile [D]**, da verificare |

Valori di controllo (ad Ancona, gronda − piede) [V sui dati]: Ospedale di Torrette, padiglione principale **33,3 m**
(20.236 m²), altri padiglioni 18,5 e 13,8 m; **Mole Vanvitelliana 13,4 m** (8.210 m², plausibile per il corpo
pentagonale); **Duomo di San Ciriaco 10,4 m** (implausibile per la cupola: un solo punto di gronda per edificio alla
scala 1:10.000, quindi le architetture complesse vengono appiattite). Senza DSM aperto il controllo indipendente si
potrà fare solo con il PST.

### 4.2 Area di prova

- **Centro – Porto – Duomo – Mole**: EPSG:7792 (≈ 25833) **378500–380500 E, 4829500–4831800 N** (Mole 379319/4830129,
  Duomo 379809/4831339).
- **Ospedale di Torrette**: **374800–375800 E, 4828400–4829300 N** (padiglione principale 375262/4828862).
- PST: celle 0,01° tra **13,45–13,53 E, 43,59–43,63 N**.

### 4.3 Istruzioni per Paolo

1. Scarica <https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/edificio.zip> (**51 MB**) e
   <https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/punto_quotato.zip> (**56 MB**) in
   `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\ancona\dbgt2019\`. Sono di tutta la regione.
2. Apri <https://www.regione.marche.it/Regione-Utile/Ambiente/Cartografia-e-informazioni-territoriali/Repertorio>,
   sezione «Banche dati» → «Edificato 1:10.000»: scarica **Edificato-2019.zip** e **Edificato-2019-Specifiche.pdf** in
   `…\citta_rif\ancona\edificato2019\` (annota la dimensione: dal container non si è potuta leggere).
3. Nella stessa pagina, sezione «DTM» → «DTM 10m (2019)»: scarica **Orografia-2019-DTM.zip** (o `.tif`) e
   **Orografia-2019-Specifiche.pdf** in `…\citta_rif\ancona\dtm10\`.
4. **Dopo il 10/11/2026**: PST su 13,45–13,53 E / 43,59–43,63 N, DSM FIRST e DTM 1 m in `…\citta_rif\ancona\pst\`.

### 4.4 Cosa può fare il server da solo

- Scaricare `edificio.zip` e `punto_quotato.zip` da `giscartografia.regione.marche.it` (certificato valido, nessun
  login). Il dominio `static.regione.marche.it` (Edificato 2019, DTM) fallisce la verifica TLS dal container: riprovare
  dal server di Milano; se fallisce anche lì, download a mano.
- Serve un **adattatore `marche_dbgt`**: `edificio` (EPSG:7792) + punto «al piede» dentro la sagoma (entro 1 m) →
  altezza = `edifc_qm` − piede (oppure, con l'Edificato 2019, `QUOTA2` − `QUOTA1` senza join).
- I servizi ArcGIS della Regione chiedono un token: non usarli.

## 5. Perugia

### 5.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Umbria – CTR 1:2.000 vettoriale**: «Centro di Perugia. Anno di volo 2000, edizione cartografia anno 2002» (più agglomerati produttivi 2007) | 2000 | 1:2.000 | 7Z [D] (`dati.gov.it`: formato «7Z») | scheda RNDT `r_umbria:00000:20191217:131000`: «Licenza d'uso CC BY 3.0 (D.G.R. n.1389/2014)»; `dati.gov.it`: «CC BY 4.0» | da browser: <http://www.umbriageo.regione.umbria.it/pagina/distribuzione-carta-tecnica-regionale-vettoriale-1-001> | [D] | scheda letta [V]; **portale irraggiungibile dal container** («connection reset»); se ha le quote di gronda: da verificare |
| Edifici | Regione Umbria – **CTR 1:10.000 vettoriale «esito grafico» del DBGT Tevere-Trasimeno** (volo giugno-luglio 2013) | 2013 | 1:10.000 | [D] | scheda `r_umbria:00009:20191202:162000`: «CC BY 3.0 (D.G.R. n.1389/2014)» | da browser: `…/pagina/distribuzione-carta-tecnica-regionale-10k-esito-gr` | [D] | scheda letta [V]; il DBGT stesso (strato 02 Immobili) è solo **WMS «non commerciale»** (`siat.regione.umbria.it/arcgis/…/DBT_02_Immobili`): non utilizzabile |
| Edifici | Regione Umbria – CTR 1:5.000 / 1:10.000 vettoriale (1985-2006) e **Fabbricati – Ecografico catastale 2005-2010** (senza altezze) | 1985-2010 | 1:5.000 | [D] | CC BY 3.0 / 4.0 (schede) | da browser | [D] | già in `regioni.toml` |
| DTM | **Nessun DTM regionale** nel RNDT né su dati.gov.it | — | — | — | — | — | — | [V] |
| DSM/DTM | PST MASE – «DSM FIRST/LAST, DTM LiDAR 1 m – Regione Umbria» (`m_amte:299FN3:ef03e653-…`, solo aste fluviali di I e II ordine) | 2008-13 [D] | 1 m | GeoTIFF | CC BY 4.0 (PST) | app PST (offline) | — | [V] WMS `LIDAR_UMBRIA.map` risponde **500**; il Tevere passa a 3–5 km dal centro: **copertura di Perugia dubbia** |

### 5.2 Area di prova

- **Centro storico – Cattedrale di San Lorenzo – Torre degli Sciri (≈ 46 m)**: ETRS89/UTM 33N **286800–288070 E,
  4775800–4777000 N** (Torre degli Sciri 287219/4776644, Cattedrale 287553/4776621).
- **Ospedale Santa Maria della Misericordia** (Sant'Andrea delle Fratte): **284300–285200 E, 4772600–4773400 N**.
- PST: celle 0,01° tra 12,35–12,40 E / 43,07–43,12 N (e la valle del Tevere a Ponte San Giovanni, 12,43–12,45 E).

### 5.3 Istruzioni per Paolo

1. Dal browser (in Italia), apri <http://www.umbriageo.regione.umbria.it/pagina/distribuzione-carta-tecnica-regionale-vettoriale-1-001>
   e scarica la **CTR 1:2.000 del centro di Perugia** in `C:\Users\ingpa\Documents\claude\pj\statocritico\citta_rif\perugia\ctr2k\`;
   copia anche la licenza o la pagina delle condizioni.
2. Apri `…/pagina/distribuzione-carta-tecnica-regionale-10k-esito-gr` e scarica le sezioni 10k che coprono Perugia
   (CTR 10k Tevere-Trasimeno 2013) in `…\citta_rif\perugia\ctr10k_2013\`.
3. Annota per ognuno: formato, dimensione, sistema di riferimento e se gli edifici hanno **quote di gronda/piede o
   altezze** (è l'informazione che manca per decidere se Perugia è utilizzabile).
4. **Dopo il 10/11/2026**: PST su 12,35–12,45 E / 43,07–43,12 N; se copre il centro o l'ospedale, DSM FIRST e DTM 1 m
   in `…\citta_rif\perugia\pst\`.

### 5.4 Cosa può fare il server da solo

Niente, oggi: i portali umbri chiudono le connessioni dall'estero; riprovare dal server di Milano con
`python -m edifici3d regioni --prova`. Se rispondono, valutare la WMS della CTR 10k e i download di UmbriaGeo.

## 6. L'Aquila

### 6.1 Fonti

| Tema | Fonte e prodotto | Anno | Risoluzione / scala | Formato e sistema | Licenza (citazione) | Accesso | Dimensione | Verifica 08/11/2026 |
|---|---|---|---|---|---|---|---|---|
| Edifici | **Regione Abruzzo – CTR digitale / DBTI multiscala 1:5.000 – aggiornamento 2007** (Intesa GIS; da cui CTR 10k e 25k) | volo 2007 | 1:5.000 | SHP, raster ECW/TIFF | **non indicata** | «I materiali sono disponibili presso Regione Abruzzo – Servizio per l'Informazione Territoriale e la Telematica» (**su richiesta**); in rete solo WMS raster «DBT multiscala» | — | [V] pagina Cartanet letta |
| Edifici | Regione Abruzzo – DB Prior Topografico 1:10.000 (2003) | 2003 | 1:10.000 | SHP | non indicata | su richiesta | — | [V] |
| DTM | **Regione Abruzzo – DTM 10 m (ed. 2007)**, dalla CTR 5k (precisione < 0,9 m sui punti quotati) | 2007 | 10 m | TIFF, «UTM WGS84» | non indicata | **su richiesta** (scheda e quadro d'unione scaricabili) | — | [V] |
| DSM | **Nessun DSM aperto** della Regione o del Comune; i rilievi 3D del centro storico dopo il sisma 2009 sono lavori di ricerca senza dati aperti | — | — | — | — | — | — | [V] Cartanet: nessun risultato per «lidar», «DTM» nel catalogo |
| DSM/DTM | PST MASE – «DSM FIRST LiDAR 1 m – Regione Abruzzo» (`m_amte:299FN3:7d24e563-…`, aste fluviali e costa) | 2008-13 [D] | 1 m | GeoTIFF | CC BY 4.0 (PST) | app PST (offline) | — | [V] WMS `LIDAR_ABRUZZO.map` vuota; **asta dell'Aterno sotto il centro: copertura probabile ma da verificare** [D] |

### 6.2 Area di prova

- **Centro storico – Forte Spagnolo – Collemaggio**: ETRS89/UTM 33N **367370–369070 E, 4688780–4690970 N** (Forte
  368523/4690282, Basilica di Collemaggio 368599/4689065).
- **Ospedale San Salvatore** (Coppito): **363900–364900 E, 4691200–4692100 N** (364395/4691663).
- PST: celle 0,01° tra **13,33–13,42 E, 42,33–42,38 N**.

### 6.3 Istruzioni per Paolo

1. Niente da scaricare in modo aperto oggi. Scarica solo la scheda del DTM 10 m e il quadro d'unione da
   <http://geoportale.regione.abruzzo.it/Cartanet/pages4home/modello_digitale_terreno/modello-digitale-terreno-10-m>
   (link «Apri scheda Metadati» e «quadro d'unione») in `…\citta_rif\laquila\documenti\`.
2. **Dopo il 10/11/2026**: PST su 13,33–13,42 E / 42,33–42,38 N; se copre il centro, DSM FIRST e DTM 1 m in
   `…\citta_rif\laquila\pst\`. Con il PST L'Aquila avrebbe almeno il controllo DSM − DTM con le altezze di OSM.
3. La lettera alla Regione Abruzzo (già pronta) va integrata con la richiesta del DBTI 2007 e del DTM 10 m (§ 9).

### 6.4 Cosa può fare il server da solo

Nulla di nuovo: niente servizi di edifici scaricabili; la WMS raster `geocatalogo.regione.abruzzo.it/erdas-iws/ogc/wms`
dà solo immagini.

## 7. Cosa non è disponibile o non è compatibile

| Città | Dato | Motivo |
|---|---|---|
| Potenza | DSM/DTM a 1 m | il LiDAR regionale è pubblicato a 5 m (sufficiente per gli edifici medi e grandi) |
| Bari | DSM regionale o comunale | non esiste in open data; solo PST (da verificare) |
| Bari | DBT Multiscala 2006 | solo consultazione, «Dato pubblico» senza licenza: si usa la CTR (IODL 2.0) |
| Bari | corpi di fabbrica nel centro | i poligoni CTR sono isolati: servono le linee divisorie |
| Ancona | DSM regionale | non pubblicato; servizi ArcGIS con token |
| Ancona | Edificato 2019 e DTM 10 m | link su `static.regione.marche.it` con catena TLS incompleta: solo da browser |
| Perugia | tutto | portali umbri irraggiungibili dal container; DBGT Tevere-Trasimeno solo WMS «non commerciale» |
| L'Aquila | edifici, DTM | CTR/DBTI 2007 e DTM 10 m solo su richiesta, senza licenza scritta |
| tutte | PST MASE | app offline fino al 10/11/2026, WMS vuote (Umbria 500): copertura da verificare |
| tutte | LiDAR PNRR 25 cm | non ancora pubblicato |

Licenze incompatibili trovate: solo la **WMS del DBGT Tevere-Trasimeno (Umbria)**, «uso locale di studio e di ricerca,
non per attività commerciali» (da non usare). Le altre fonti proposte sono IODL 2.0 (Basilicata, Puglia), CC BY 4.0
(Marche) e CC BY 3.0 / 4.0 (Umbria: le schede RNDT dicono 3.0, dati.gov.it 4.0, da chiarire); Abruzzo senza licenza.

## 8. Ordine consigliato e spazio

| Ordine | Cosa | Dove | Dimensione |
|---|---|---|---|
| 1 | Potenza: DBGT del Comune + DSM e DTM 5 m (WCS) | `citta_rif\potenza\` | 89,5 + 2 × 17 MB |
| 2 | Bari: CTR 5 elementi + DTM 8 m | `citta_rif\bari\` | 23,5 + 2,0 MB |
| 3 | Ancona: DBGT 2019 `edificio` + `punto_quotato` | `citta_rif\ancona\dbgt2019\` | 51 + 56 MB |
| 4 | Ancona: Edificato 2019 e DTM 10 m (da browser) | `citta_rif\ancona\` | da annotare [D] |
| 5 | Perugia: CTR 2k centro e CTR 10k 2013 (da browser in Italia) | `citta_rif\perugia\` | da annotare [D] |
| 6 | (dopo il 10/11) PST per Bari, Ancona, L'Aquila, Perugia (ed eventualmente Potenza) | `citta_rif\<città>\pst\` | qualche decina di MB [D] |
| — | facoltativo: unità volumetriche di tutta la Basilicata (con Z) | `citta_rif\potenza\` | 71,5 MB |

Totale essenziale (passi 1–3): **circa 255 MB**; con il facoltativo della Basilicata circa 330 MB.

## 9. Da aggiornare nel progetto (non fatto qui: `/home/claude/eu` non va toccato)

- `fase10-edifici3d/fonti/regioni.toml`:
  - **Basilicata / nota**: togliere «rsdi … 503»: RSDI risponde (08/11/2026).
  - **Basilicata / edifici** → **«attiva»**: servizio `https://rsdi.regione.basilicata.it/rbgeoserver2016/ows`
    (`typeNames=dbgt_0201:un_vol`, EPSG:25833), altezza `un_vol_av`, Z della geometria = quota della base; download
    `webGis/shape-zip/unita_volumetrica.zip` (71,5 MB) e per comune `downloadProd/dbgt_ctr_comune_download/<17+ISTAT>.zip`;
    `url_prova` = GetFeature con `resultType=hits` su Potenza; `prova` = «08/11/2026: 50 volumi al San Carlo, confronto
    con DSM−DTM 5 m mediana 0,0 m». Adattatore: zona `basilicata` in `lombardia_dbgt` (campi minuscoli) [D].
  - **Basilicata / dtm e dsm** → **«attiva»**: WCS `…/rbgeoserver2016/rsdi_wcs/ows`, coverage `rsdi_wcs__dtm_5m` e
    `rsdi_wcs__dsm_5m` (GeoTIFF float32, 5 m, LiDAR 2013); togliere «a 5 m serve solo per edifici grandi» o precisare
    che a Potenza basta per i volumi ≥ 100 m².
  - **Basilicata / ortofoto**: riprovare la WMS 2013 (il server ora risponde).
  - **Puglia / edifici**: nome «CTR 1:5.000 (volo 2006), SHP per elemento con punti di gronda e piede», licenza
    IODL 2.0 (scheda `r_puglia:e5fdf473-4457-420a-9cef-3ad20f31a9b9`), servizio
    `http://cartografia.sit.puglia.it/download/CTR/SHP/<foglio>/<elemento>_ctr.zip`, altezza «quota gronda − quota
    piede (punti)», stato «in attesa» solo per l'adattatore `puglia_ctr`; annotare che il DBT Multiscala 2006 è «Dato
    pubblico» senza licenza.
  - **Puglia / dtm** → **«attiva»**: download `…/download/DTM/ASC/<foglio>/<elemento>_asc.zip` provato (8 m, EPSG:32633,
    virgola decimale).
  - **Marche / nota**: niente captcha l'08/11/2026; `static.regione.marche.it` con certificato non verificabile.
  - **Marche / edifici**: «DBGT 2019 (CTR 10k) – edificio + punto_quotato», CC BY 4.0 (pagina OpenData, D.G.R.
    783/2017), servizio `https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/edificio.zip`, altezza
    «`edifc_qm` (gronda) − punto al piede», stato «in attesa» per l'adattatore; in alternativa «Edificato 2019»
    (`QUOTA2` − `QUOTA1`).
  - **Marche / dtm**: «DTM 10 m (2019)», CC BY 4.0, download da browser (TLS).
  - **Umbria**: aggiungere CTR 1:2.000 del centro di Perugia (volo 2000) e CTR 10k Tevere-Trasimeno (2013), CC BY 3.0;
    il DBGT Tevere-Trasimeno strato 02 come «non disponibile» (WMS non commerciale); nota: connessione chiusa anche
    l'08/11, WMS PST Umbria 500.
  - **Abruzzo / edifici e dtm**: CTR/DBTI 2007 1:5.000 SHP e DTM 10 m 2007 «disponibili presso la Regione» (su
    richiesta, licenza non indicata); Cartanet risponde (pagine in `Cartanet/pages4home/…`).
- `documenti/LETTERE_REGIONI_DB_TOPOGRAFICI.md`:
  - **Basilicata**: **lettera da togliere** (dati scaricabili e servizi provati, IODL 2.0); spostare la Regione tra
    quelle «attive»; eventualmente solo una richiesta di DTM/DSM a risoluzione più fine del LiDAR 2013.
  - **Puglia**: ridurre la lettera: la CTR 2006 con le quote si scarica in IODL 2.0; chiedere solo se esiste un
    aggiornamento più recente (volo 2015?) e un DSM/LiDAR regionale, e la licenza del DBT Multiscala.
  - **Marche**: ridurre la lettera: il DBGT 2019 si scarica in CC BY 4.0; chiedere se esistono unità volumetriche con
    altezze per corpo (non solo una gronda per edificio), un DSM, e segnalare il certificato di
    `static.regione.marche.it`.
  - **Umbria**: la lettera resta valida; aggiungere la CTR 1:2.000 di Perugia (quote di gronda?), il chiarimento
    CC BY 3.0 / 4.0 e la richiesta di poter usare il DBGT Tevere-Trasimeno 2013 (oggi WMS «non commerciale»).
  - **Abruzzo**: la lettera resta valida; precisare la richiesta: **DBTI 2007 1:5.000 in SHP** (edifici con quote) e
    **DTM 10 m 2007**, con una licenza aperta scritta.
- `DA_FARE.md`: «Città di riferimento – Centro-Sud» con i passi del § 8 e, dopo il 10/11, la verifica PST per Bari,
  Ancona, L'Aquila e Perugia.

## 10. Prove dal vivo (08/11/2026)

| Prova | Esito |
|---|---|
| RSDI Basilicata: pagina «DBGT & CTR», WFS GetCapabilities (`rbgeoserver2016`, 553 strati), DescribeFeatureType `dbgt_0201:un_vol` | 200; campi `un_vol_por`, `un_vol_av`, `cediuv`, `scril`; Fees/AccessConstraints NONE |
| WFS GetFeature `un_vol` (San Carlo, centro, `resultType=hits`, `count=5000`) | 50 / 674 volumi; 38.552 nel riquadro di 15×20 km; 5.000 oggetti in 2 s |
| WCS `rsdi_wcs` GetCapabilities, DescribeCoverage, GetCoverage DTM e DSM (3 ritagli) | GeoTIFF float32 EPSG:25833, 5 m; WCS globale e `maps_dtm` disabilitati |
| Zip `unita_volumetrica.zip` (regione) e `17076063.zip` (Potenza) scaricati, letti e cancellati | 477.261 e 27.330 volumi; IODL 2.0 nel PDF; stessi `CEDIUV` e altezze del WFS |
| Schede ISO dal CSW della RSDI (UN_VOL, DTM, DSM) | IODL 2.0; «Anno di rilievo: 2013»; DSM da classi LiDAR |
| SIT Puglia: pagina «Download – Cartografie», foglio 438, dettaglio CTR e DTM | 51 elementi CTR, 64 DTM; URL diretti |
| CTR 438073, 438074, 438072, 438061, 438062, 438071, 438083 e DTM degli stessi elementi | 200; SHP PolygonZ/PointZ; DTM ASCII 8 m con virgola decimale |
| Allineamento CTR Puglia con OSM (Basilica di San Nicola) | sovrapposizione 94 %, scarto 0,3 m → EPSG:32633 |
| Schede RNDT Puglia (CTR, DTM, DBT Multiscala) | IODL 2.0 per CTR e DTM; DBT «Dato pubblico» |
| Regione Marche: pagine OpenData e Repertorio; `giscartografia` `edificio.zip`, `punto_quotato.zip` (scaricati, letti, cancellati) | CC BY 4.0 dichiarata; 453.585 edifici, 1.321.718 punti; `static.regione.marche.it`: errore TLS (catena incompleta), `http`: 503 |
| Specifica «Edificato 2019» (WebFetch) | `QUOTA1` piede, `QUOTA2` gronda, EPSG:7792 |
| Servizi ArcGIS Marche (`BasiRaster/DEM`, `MarcheCTR`) | «Token Required»: non usati |
| Umbria: `umbriageo`, `siat`, `dati.umbria.it`, `geo.umbriadigitale.it`; WebFetch | connection reset / DNS; WebFetch non ammesso; schede RNDT e pacchetti dati.gov.it letti |
| Cartanet Abruzzo (`pages4home`: area download, DTM, cartografia numerica, WMS); catalogo | DTM 10 m e CTR 2007 «disponibili presso la Regione»; nessun download |
| `dati.gov.it`, `dati.puglia.it`, `opendata.comune.bari.it` (CKAN) | nessun DSM/LiDAR regionale per le cinque città |
| CSW RNDT (`geodati.gov.it`) | schede PST LiDAR per Umbria, Marche, Abruzzo, Puglia; schede Umbria CTR 2k/5k/10k |
| WMS PST `LIDAR_{UMBRIA,MARCHE,ABRUZZO,PUGLIA,BASILICATA}.map` GetCapabilities e GetMap sulle 4 città | Umbria 500; le altre immagini vuote (0 pixel) |
| Nominatim (OSM) | coordinate degli ospedali e dei monumenti delle aree di prova |

Script: `script/wfsq.py` (WFS su riquadro in WGS84), `script/confronta.py` (altezze DB contro DSM − DTM),
`script/ctr_puglia_altezze.py` (altezze dalla CTR pugliese), `script/ckan.py` (ricerca CKAN), più `zipindice.py`,
`zipparziale.py`, `csw.py`, `cswrec.py` copiati dal lavoro precedente. Prove rimaste in `centro/` (circa 52 MB:
ritagli GeoJSON e GeoTIFF, due elementi CTR di Bari estratti senza le linee, DTM per elemento, pagine e schede); gli zip regionali (Basilicata,
Marche) sono stati cancellati dopo la lettura.

## 11. Fonti

Potenza (Basilicata)
- RSDI, pagina DBGT & CTR: <https://rsdi.regione.basilicata.it/dbgt-ctr/>
- Scheda UN_VOL: <https://geodati.gov.it/resource/id/r_basili:26e21af8:14ff44204d8:214c>; zip regionale
  <https://rsdi.regione.basilicata.it/webGis/shape-zip/unita_volumetrica.zip>
- WFS: <https://rsdi.regione.basilicata.it/rbgeoserver2016/ows?service=WFS&request=GetCapabilities>
- DBGT di Potenza: <https://rsdi.regione.basilicata.it/downloadProd/dbgt_ctr_comune_download/17076063.zip>
- DTM 5 m: <https://geodati.gov.it/resource/id/r_basili:9EE9C09A-7091-D8A2-A41D-F28191B86C4F>; DSM 5 m:
  <https://geodati.gov.it/resource/id/r_basili:28FFB196-1EAA-49B4-769D-78C030B75042>
- WCS: <https://rsdi.regione.basilicata.it/rbgeoserver2016/rsdi_wcs/ows?service=WCS&version=2.0.1&request=GetCapabilities>

Bari (Puglia)
- Download per foglio: <http://www.sit.puglia.it/portal/portale_cartografie_tecniche_tematiche/Download/Cartografie>
- Esempi: <http://cartografia.sit.puglia.it/download/CTR/SHP/438/438073_ctr.zip>,
  <http://cartografia.sit.puglia.it/download/DTM/ASC/438/438073_asc.zip>
- Schede: CTR <https://geodati.gov.it/resource/id/r_puglia:e5fdf473-4457-420a-9cef-3ad20f31a9b9>, DTM
  <https://geodati.gov.it/resource/id/r_puglia:85898eba-d4b0-4c3b-a2c7-6ea666522591>, DBT Multiscala
  <https://geodati.gov.it/resource/id/r_puglia:63d5dd1e-6e66-4607-85e6-36688f4be6ab>
- Servizi WMS/WFS del SIT: <http://cartografia.sit.puglia.it/doc/Servizi_WMS-WFS_SIT_Puglia.pdf>
- Open data del Comune di Bari: <https://opendata.comune.bari.it/>

Ancona (Marche)
- Elenco Opendata (CC BY 4.0): <https://www.regione.marche.it/Regione-Utile/Ambiente/Cartografia-e-informazioni-territoriali/OpenData>
- Repertorio (link a DBGT 2019, Edificato, DTM): <https://www.regione.marche.it/Regione-Utile/Ambiente/Cartografia-e-informazioni-territoriali/Repertorio>
- DBGT 2019: <https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/edificio.zip>,
  <https://giscartografia.regione.marche.it/Cartografia/CTR2019/DBT/punto_quotato.zip>
- Specifiche: <https://www.regione.marche.it/Portals/0/Paesaggio_Territorio_Urbanistica/Cartografia/Banche_dati/Edificato-2019-Specifiche.pdf>,
  <https://www.regione.marche.it/Portals/0/Paesaggio_Territorio_Urbanistica/Cartografia/Banche_dati/Orografia-2019-Specifiche.pdf>
- D.G.R. 783/2017: <https://www.norme.marche.it/Delibere/2017/DGR0783_17.pdf>

Perugia (Umbria)
- CTR 1:2.000: <https://geodati.gov.it/resource/id/r_umbria:00000:20191217:131000>; CTR 10k Tevere-Trasimeno:
  <https://geodati.gov.it/resource/id/r_umbria:00009:20191202:162000>; DBGT strato 02 (WMS non commerciale):
  <https://geodati.gov.it/resource/id/r_umbria:00000:20160209:130800>
- Pacchetti su dati.gov.it: <https://www.dati.gov.it/opendata/dataset/carta-tecnica-regionale-vettoriale-a-scala-1-2-000>
- UmbriaGeo (da browser): <http://www.umbriageo.regione.umbria.it>

L'Aquila (Abruzzo)
- Cartanet: <http://geoportale.regione.abruzzo.it/Cartanet/>; DTM 10 m:
  <http://geoportale.regione.abruzzo.it/Cartanet/pages4home/modello_digitale_terreno/modello-digitale-terreno-10-m>;
  CTR 2007: <http://geoportale.regione.abruzzo.it/Cartanet/pages4home/cartografia_numerica/carta-tecnica-regionale-digitale-1-5.000-1-10.000-1-25.000-aggiornamento-2007>

Nazionali
- PST MASE, distribuzione e licenza: <https://gn.mase.gov.it/portale/distribuzione-dati-pst>; app
  <https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new>; schede «Prodotti LiDAR»: Umbria
  <https://geodati.gov.it/resource/id/m_amte:299FN3:af606d12-5a15-4427-961f-4f2542f680b9>, Abruzzo
  <https://geodati.gov.it/resource/id/m_amte:299FN3:2add20b5-d1fb-4475-b5a6-6d01dd61297c>, Marche
  <https://geodati.gov.it/resource/id/m_amte:299FN3:8b69cd21-a598-4b37-acce-0f488cc9ee81>, Puglia
  <https://geodati.gov.it/resource/id/m_amte:299FN3:a666a1c3-51d5-498b-bd43-0b5a2ad90f72>
