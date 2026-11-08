# Librerie del sito (ospitate qui, non da CDN)

Scaricate con npm il 04/11/2026 e copiate così come sono (file `dist`), con la loro licenza accanto. Versioni fissate.

| Cartella | Pacchetto npm | Versione | Licenza | Uso |
|---|---|---|---|---|
| `maplibre-gl/` | `maplibre-gl` | 5.24.0 | BSD-3-Clause (`LICENSE.txt`) | mappa 3D degli edifici (`edificio3d.js`) |
| `pmtiles/` | `pmtiles` | 4.4.1 | BSD-3-Clause (`LICENSE`) | lettura dei PMTiles da Caddy con richieste Range |
| `dxf-parser/` | `dxf-parser` | 1.1.2 | MIT (`LICENSE`) | DXF di testo nella pagina Importa DXF/IFC (solo nel Web Worker) |
| `web-ifc/` | `web-ifc` | 0.0.77 | MPL-2.0 (`LICENSE.md`) | IFC nella pagina Importa DXF/IFC: `web-ifc-api-iife.js` e `web-ifc.wasm`, caricati dal worker solo quando arriva un IFC |
| `clipper-lib/` | `clipper-lib` | 6.4.2 | Boost Software License 1.0 (`LICENSE`, con la nota su jsbn) | unioni e margini dei poligoni dei tetti (come shapely nel comando Python) |
| `proj4/` | `proj4` | 2.22.0 | MIT (`LICENSE.md`) | sistemi di riferimento (RDN2008, ETRS89, WGS84 UTM, Gauss-Boaga) nella posa dei modelli; anche nella pagina Aggiungi edifici |
| `sql.js/` | `sql.js` | 1.14.2 (14/08/2026) | MIT (`LICENSE`) | GeoPackage (SQLite) nella pagina Aggiungi edifici (DB topografico): `sql-wasm.js` e `sql-wasm.wasm`, caricati dal suo Web Worker solo quando arriva un GeoPackage o uno zip |
| `fflate/` | `fflate` | 0.8.2 | MIT (`LICENSE`) | zip dei portali regionali nella pagina Aggiungi edifici (lettura nel Web Worker, e zip degli Shapefile da proporre all'archivio comune): `umd/index.js` copiato come `fflate.js` |

Le ultime quattro (04/11/2026) servono **solo** alla pagina `importa-dxf-ifc.html`: le carica il suo Web Worker
(`modelli_worker.js`), nessun'altra pagina le scarica (lo controllano un test della fase 5 e la prova nel browser della
fase 10). Della distribuzione di web-ifc si copiano solo la versione IIFE per il browser e il `.wasm` a un solo thread
(`web-ifc-mt.wasm` richiederebbe l'isolamento cross-origin, `web-ifc-node.wasm` è per node).

Si usa la versione 5 di MapLibre (UMD, un solo file `maplibre-gl.js` con il worker dentro): la 6 si distribuisce solo
come moduli ES (`.mjs`) con il worker in un file separato. Aggiornamento:

```
npm install maplibre-gl@<versione> pmtiles@<versione>
cp node_modules/maplibre-gl/dist/{maplibre-gl.js,maplibre-gl.css} node_modules/maplibre-gl/LICENSE.txt maplibre-gl/
cp node_modules/pmtiles/dist/pmtiles.js pmtiles/
npm install dxf-parser@1.1.2 web-ifc@0.0.77 clipper-lib@6.4.2 proj4@2.22.0
cp node_modules/dxf-parser/dist/dxf-parser.js node_modules/dxf-parser/LICENSE dxf-parser/
cp node_modules/web-ifc/{web-ifc-api-iife.js,web-ifc.wasm,LICENSE.md} web-ifc/
cp node_modules/clipper-lib/clipper.js clipper-lib/          # LICENSE scritto a mano: il pacchetto non lo contiene
cp node_modules/proj4/dist/proj4.js node_modules/proj4/LICENSE.md proj4/
npm install sql.js@1.14.2 fflate@0.8.2                      # 07/11/2026, pagina Aggiungi edifici (DB topografico)
cp node_modules/sql.js/dist/{sql-wasm.js,sql-wasm.wasm} node_modules/sql.js/LICENSE sql.js/
cp node_modules/fflate/umd/index.js fflate/fflate.js && cp node_modules/fflate/LICENSE fflate/
```
Impronte SHA-256 dei file copiati il 07/11/2026: `sql-wasm.js` f1c84000…, `sql-wasm.wasm` 38c14f6e…, `fflate.js` c3b34f2e….
sql.js 1.15 (ottobre 2026) era troppo recente: si è scelta l'ultima della serie 1.14. Dopo un aggiornamento rilanciare
anche i test di parità di «Aggiungi DBTR» (`tests/test_dbtr_parita.py` e `tests/test_dbtr_browser.py` della fase 10).
Dopo un aggiornamento dei lettori dei modelli rilanciare i test di parità della fase 10 (`tests/test_importa_parita.py`
e `tests/test_importa_browser.py`).
poi aggiornare questa tabella e la pagina Link (progetti open source usati).
