# Librerie del sito (ospitate qui, non da CDN)

Scaricate con npm il 04/11/2026 e copiate così come sono (file `dist`), con la loro licenza accanto. Versioni fissate.

| Cartella | Pacchetto npm | Versione | Licenza | Uso |
|---|---|---|---|---|
| `maplibre-gl/` | `maplibre-gl` | 5.24.0 | BSD-3-Clause (`LICENSE.txt`) | mappa 3D degli edifici (`edificio3d.js`) |
| `pmtiles/` | `pmtiles` | 4.4.1 | BSD-3-Clause (`LICENSE`) | lettura dei PMTiles da Caddy con richieste Range |
| `dxf-parser/` | `dxf-parser` | 1.1.2 | MIT (`LICENSE`) | DXF di testo nella pagina Importa DXF/IFC (solo nel Web Worker) |
| `web-ifc/` | `web-ifc` | 0.0.77 | MPL-2.0 (`LICENSE.md`) | IFC nella pagina Importa DXF/IFC: `web-ifc-api-iife.js` e `web-ifc.wasm`, caricati dal worker solo quando arriva un IFC |
| `clipper-lib/` | `clipper-lib` | 6.4.2 | Boost Software License 1.0 (`LICENSE`, con la nota su jsbn) | unioni e margini dei poligoni dei tetti (come shapely nel comando Python) |
| `proj4/` | `proj4` | 2.22.0 | MIT (`LICENSE.md`) | sistemi di riferimento (RDN2008, ETRS89, WGS84 UTM, Gauss-Boaga) nella posa dei modelli |

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
```
Dopo un aggiornamento dei lettori dei modelli rilanciare i test di parità della fase 10 (`tests/test_importa_parita.py`
e `tests/test_importa_browser.py`).
poi aggiornare questa tabella e la pagina Link (progetti open source usati).
