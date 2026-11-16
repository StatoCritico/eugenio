# Perugia – LiDAR PST scaricato dal MASE (16/11/2026)

Seguito di `LIDAR_MASE_VERIFICA_2026-11-16.md`. Scaricamento fatto da Claude il 16/11/2026 alle 15:55–16:05 nell'app
`https://sim.mase.gov.it/pst/` (browser integrato dell'app desktop, senza login). Susegana: nessuna tavola PST (WMS del
Veneto e quadro di unione vuoti); decisione di Paolo: si aspetta il LiDAR PNRR.

**Esito (16/11/2026 sera):** archivio di Perugia pronto, `odbl/umb/perugia`, pubblicazione con
`AGGIORNAMENTO_2026-11-16g.md` (release `v2026.11.16g`, sito `?v=20261116g`). Con Perugia ci sono tutti i capoluoghi di
regione.

## Cosa è stato scaricato

| Prodotto | Tavole | File | Dimensione |
|---|---|---|---|
| DTM 1×1 | 20 | `umbria_204_D4308..D4311{1235..1239}_0101_DTM.tiff` | ZIP 80,1 MB |
| DSM First 1×1 | 20 | `umbria_204_..._0101_DSMFirst.tiff` | ZIP 80,1 MB |

- Area: 43,08–43,12 N, 12,35–12,40 E (centro storico, Fontivegge, Sant'Andrea delle Fratte), 4 × 5 tavole da 0,01°.
- **Il polo ospedaliero S. Maria della Misericordia è quasi tutto fuori** (area OSM 43,0775–43,0808 N × 12,3534–12,3572 E):
  serve la tavola **D43071235** (DTM e DSM First). Il tentativo del 16/11 è fallito perché l'app MASE si è bloccata (mappa
  bianca, widget che non si aprono, anche dopo il ricaricamento). Il CREO (43,0805 N) è dentro.
- Rilievo: contratto **204**, «PST Estensione 2014», voli del 13–14/03/2014, **collaudato NO** (nel quadro di unione).
- GeoTIFF float32, **EPSG:4326**, 1000 × 1000 celle da 0,00001° (circa 0,8 × 1,1 m), nodata −9999; valide il 100 % delle
  celle in entrambi i prodotti.
- Nello ZIP: `area_selezionata/tile_selezionate.csv` (sessione, fid, tavola), quadro di unione in shapefile, metadati
  (`LIDAR_DTM_1x1_Umbria.xml` senza licenza; per il DSM «Metadati non disponibili», errore 502 del catalogo).
- Licenza: **CC BY 4.0** dalla pagina «Distribuzione dati PST» (i metadati nello ZIP non la riportano). Attribuzione:
  «Ministero dell'Ambiente e della Sicurezza Energetica – Geoportale Nazionale, Banca dati PST (CC BY 4.0)».

## Primi controlli (container)

- DTM 241–495 m, mediana 315 m: **quote ortometriche** (con quote ellissoidiche sarebbero circa 46 m più alte).
- DSM − DTM: p50 1,1 m, p99 23,8 m; il 40 % delle celle supera 2,5 m; meno dello 0,03 % sotto −1 m.

## Archivio degli edifici

- **Sagome**: OpenStreetMap da Overpass (`https://ovp.dresel.systems/api/interpreter`, dati del 15/11/2026), riquadro
  43,079–43,121 N × 12,349–12,401 E: 6.198 way, 6.137 sagome valide (`umbria.py osm-geojson`, EPSG:7792).
- **Altezze**: `altezze_dsm.annota` (DSM First − DTM, mediana dei pixel nella sagoma ridotta di 1 m). Si tengono le 5.834
  sagome dentro le tavole (campo `dsm_esito` presente). Ordine: DSM − DTM (`ok`, `pochi_pixel`) → tag OSM `height` /
  `building:levels` (edifici costruiti dopo il 2014: «non presente nel rilievo PST 2014») → mediana dei vicini → uso.
- **Archivio**: zona `umbria_perugia`, adattatore `umbria_osm_pst`, licenza **ODbL 1.0** (sagome OSM; mai nello stesso
  archivio dei CC BY), cartella `odbl/umb/perugia/prodotti`, attribuzione «© OpenStreetMap contributors (ODbL 1.0); altezze
  da DSM − DTM 1 m: Ministero dell'Ambiente e della Sicurezza Energetica – Geoportale Nazionale, Banca dati PST (CC BY 4.0)».
- **Numeri**: 5.834 corpi, 5.833 edifici, 38 celle, 6,7 MB (tar.gz 2,1 MB); gronda min / mediana / max 1,91 / 11,05 /
  52,38 m; origine delle altezze (celle-corpo): DSM 6.106, vicini 57, uso 7, piccoli 5, livelli OSM 1.
  `controlla-archivio`: `problemi: []`, `avvisi: []`.
- **Prove**: Palazzo dei Priori 29,06 m (2.837 pixel, 4 tavole DSM), Cattedrale 28,61 m, Fontivegge 16,79 m. Pagina Modelli
  3D provata in locale (Chrome senza schermo): il 3D del Palazzo dei Priori si genera dall'archivio, cortile compreso,
  nessun errore JavaScript.
- **Terreno**: COG `dtm1_pst_perugia.tif` (1 m, 49 MB) e scheda `dtm1_pst_perugia.json` (`dtm-server --regione
  pst_umbria`), per `/api/terreno`: 473,9 m in centro, 302,6 m a Fontivegge.

## Come si scarica dall'app MASE (procedura che funziona)

1. `https://sim.mase.gov.it/pst/` → pulsante **«Cerca prodotti»** (secondo della colonna di destra).
2. «Seleziona geometria» → **Disegno manuale** → strumento **poligono** (non il rettangolo): clic sui quattro vertici in
   senso orario, con una pausa tra i clic, doppio clic sull'ultimo.
3. Spuntare **un prodotto alla volta** (es. «Quadro di unione LiDAR DTM Griglia 1x1») → **«Filtra risultati trovati»**
   → controllare «Elementi in tabella» → **«Aggiungi a carrello»**.
4. Pulsante **Carrello** → casella in testa alla tabella (seleziona tutto) → **«N / 20 Download»** (massimo 20 tavole per
   richiesta) → la richiesta viene preparata sul server (circa 30 s) → «Download file» / «Scarica tutti».
5. Il collegamento `https://sim.mase.gov.it/core/api/esri/api/v1/downloads/<sessione>/file/<id>` si scarica anche senza
   il browser (curl dal container: 200, `application/octet-stream`).

Problemi incontrati: il **rettangolo** e a volte anche il poligono danno **0 elementi** con un errore 500 del server
`gis.platform.sim.mase.gov.it`; rifacendo il poligono in senso orario e con un solo prodotto la ricerca è riuscita. Con
«Limiti amministrativi › comunali › Perugia» la ricerca funziona sempre (511 tavole DTM 1×1 nel comune), ma il carrello non
mostra il nome della tavola e non si possono scegliere le righe prima di caricarle. Il `fid` della nuova app **non**
coincide con l'`objectid` del WMS del quadro di unione (es. D43111235: fid 169275, objectid 169277). Muovere la mappa via
JavaScript con tempi lunghi (45 s) ha bloccato l'app per il resto della sessione.

## Prossimi passi

- Tavola **D43071235** (DTM e DSM First) per il polo ospedaliero; poi OSM sul riquadro allargato, `annota`, `prepara-regione`
  e ripubblicazione dell'archivio (stessa cartella).
- Resto del comune (511 tavole DTM, 26 richieste da 20) solo se serve.
- Quando uscirà il LiDAR PNRR: confronto con il PST 2014 e, se migliore, sostituzione delle altezze.
