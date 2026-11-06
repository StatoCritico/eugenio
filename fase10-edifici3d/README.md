# Fase 10 – Edifici 3D, ortofoto, LiDAR e analisi energetiche

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
| Terreno | DTM regionale (ER 0,5 m o 5 m) → LiDAR PNRR/PST → TINITALY 10 m (INGV) |
| Orizzonte lontano | Copernicus DEM 90 m, raggio 20–30 km (già usato in fase 3) |
| Ombre di alberi ed edifici | DSM primo impulso dove disponibile |

Per ogni dato si salvano **fonte** e **qualità**. Fuori dall'ER la scelta tra aggregati (CC BY) e OSM (ODbL) si fa
regione per regione.

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
| `edifici3d/dtm.py` | COG del DTM, quota del terreno per corpo (minimo e mediana), tessere Terrarium in PMTiles per MapLibre |
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

`prepara` scrive in `<archivio>/cc-by/er/prodotti/`: `corpi.pmtiles` (strato `corpi`, zoom 13–16), `contesto/<i>_<j>.json`,
`dtm_cog.tif`, `terreno.pmtiles` (Terrarium, zoom 10–15) e `indice.json` (centro, riquadro, licenza, attribuzione). Caddy
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
- Terreno in MapLibre: il COG non si legge direttamente, quindi si producono anche tessere Terrarium (PNG) in PMTiles.
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

Oggi sul server non c'è nessun archivio di edifici: Modelli 3D cerca il punto e mostra ortofoto e strati, ma il 3D si genera
solo sulla demo sintetica. Con l'**archivio di prova OSM** del centro di Rimini (passo D13 di `AGGIORNAMENTO_2026-11-05.md`)
il flusso vero funziona già lì (ricerca, punto trascinabile, «Genera il 3D», immagine e report), con altezze stimate. Il
servizio vero in Emilia-Romagna usa le **unità volumetriche del DBTR** (altezza per corpo, CC BY 4.0) e il **DTM 5 m**.

| # | Passo | Chi | Tempo e spazio (stime) |
|---|---|---|---|
| 1 | **Prenotare l'estrazione del DBTR** dal Geoportale: pagina «Download DB Topografico» (`https://geoportale.regione.emilia-romagna.it/download-data/download-dbtopografico`), area = comune o provincia di Rimini (o tutta la regione), classe **Unità volumetrica (UVL)** (facoltativo: Edificio), formato **GeoPackage**, sistema **RDN2008 / UTM 32N (EPSG:7791)**. Il modulo ha il reCAPTCHA e la consegna è per email: l'agente non può farlo (e non deve aggirarlo). Il WFS del DBTR non è un'alternativa (401 il 03/11, 404 il 05/11/2026). | **Paolo** | 5 minuti + attesa dell'email; GeoPackage stimato 50–150 MB per la provincia di Rimini, 1–3 GB per la regione (da verificare sul file) |
| 2 | Copiare il GeoPackage sul server: `scp UVL_rimini.gpkg eugenio:/srv/energia/dati/edifici/cc-by/er/grezzi/` (creare prima la cartella con `mkdir -p`). In alternativa metterlo in `C:\Users\ingpa\Documents\claude\pj\statocritico\edifici\`: l'agente lo legge dal PC, prepara l'archivio nel suo ambiente e ti restituisce un tar come quello di prova. | **Paolo** (o agente dal PC) | minuti |
| 3 | **DTM 5 m** della zona dal WCS pubblico, sul server: `docker compose --profile edifici run --rm edifici-lidar dtm-wcs --riquadro 770000 4860000 800000 4895000 --uscita /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif` (comune di Rimini e dintorni, 30×35 km, 12 blocchi). Per tutta la regione: i quattro quadranti TIFF della scheda del DTM (~4,9 GB) in `cc-by/er/grezzi/`. | **Paolo** (comando pronto) | ~7 minuti e ~180 MB per 30×35 km; ~1 h per i quadranti |
| 4 | **Controllo degli attributi**: `docker compose --profile edifici run --rm edifici-lidar controlla-uvl --gpkg /dati/edifici/cc-by/er/grezzi/UVL_rimini.gpkg` (rapporto su H_uvl, B_uvl, gronda/colmo, piani). | Paolo; l'agente legge il rapporto | 1–2 minuti |
| 5 | **`prepara`**: `docker compose --profile edifici run --rm edifici-lidar prepara --gpkg /dati/edifici/cc-by/er/grezzi/UVL_rimini.gpkg --dtm /dati/edifici/cc-by/er/grezzi/dtm5_rimini.tif --archivio /dati/edifici --riquadro 770000 4860000 800000 4895000`. Scrive `cc-by/er/prodotti/` (corpi.pmtiles, contesto/, dtm_cog.tif, terreno.pmtiles, indice.json). | Paolo | provincia di Rimini: 5–20 minuti, 50–200 MB; regione intera a zone (una provincia per volta), qualche ora e 1–3 GB |
| 6 | **`archivi.json`** in `/srv/energia/dati/edifici/`: il DBTR **prima** dell'archivio di prova OSM (o l'archivio di prova tolto): `{"archivi": [{"base": "/edifici3d/cc-by/er/prodotti/", "nome": "DBTR Emilia-Romagna"}, {"base": "/edifici3d/odbl/rimini-prova/prodotti/", "nome": "OpenStreetMap – rimini-prova (archivio di prova)"}]}`. | Paolo (testo pronto) | 1 minuto |
| 7 | **Caddy**: niente da fare. `/edifici3d/` è già servito dalla cartella `CARTELLA_EDIFICI` (sola lettura, Range, CORS, cache di un giorno); nessun riavvio. | — | — |
| 8 | **Prove**: Modelli 3D → «via Gambalunga 27, Rimini» → l'edificio UVL del punto (trascinare il punto se serve) → «Genera il 3D» (fonte «DB topografico regionale»); Ortofoto → «contorni dell'archivio 3D» accesi. | Paolo; l'agente corregge quello che non va | 10 minuti |
| 9 | **Dopo, da sola, la pipeline LiDAR** (cron delle 3:30, `edifici-lidar`, zona Rimini): trovati i corpi della Fase A, lavora le tessere coperte dal **DSM della costa 2019** (falde per corpo dal LiDAR, CC BY 4.0, fascia costiera); per il resto resta «in attesa» finché non arrivano DSM/LAS RER 2023-24 (email all'Archivio Cartografico) o il LiDAR PNRR. La pagina interna `/interno/edifici.html` passa da «In attesa: … 0 corpi della Fase A» a «Zona in corso». | automatico; l'agente legge lo stato | notti successive |

L'agente (Claude) ha già fatto: proxy di particelle e contorni, comandi `osm-campione` e `dtm-wcs`, archivio di prova OSM
del centro di Rimini, prove dal vivo di WMS AdE, WMS DBTR, WCS DTM e API OSM; può fare: leggere il GeoPackage dal PC e
preparare l'archivio (passo 2, alternativa), scrivere `archivi.json` da `prepara`, controllare i rapporti dei passi 4–5 e
le prove del passo 8. Resta a Paolo: la prenotazione del DBTR (reCAPTCHA ed email), i comandi sul server, l'email
all'Archivio Cartografico per DSM/LAS 2023-24.

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
