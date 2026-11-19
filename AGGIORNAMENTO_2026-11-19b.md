# Aggiornamento del 19/11/2026 b – terreno 3D a 5 m in tutta Italia (HR-DTM-5m del CNR-IRPI)

Pubblicazione **insieme** a quella del mattino (`AGGIORNAMENTO_2026-11-19.md`: righello, 3D della vista, più edifici,
ortofoto nella rete, confini automatici delle cabine, ricerca di Venezia): il ramo `claude/terreno-hrdtm5m` parte da
`claude/righello-vista3d-cabine` e li contiene tutti e due. **Una sola pull request e una sola release `v2026.11.19`**
(la procedura AI1 del mattino è sostituita da AJ1 qui sotto). Sito **`?v=20261119b`**, voce nelle Novità.

Nessun passo a mano sul server: niente file da copiare (il DTM nazionale si legge da Zenodo), niente righe nuove nel
`.env` (i valori predefiniti vanno bene), l'immagine `api` la ricostruisce l'aggiornamento dalla release.

## Richiesta di Paolo (19/11/2026)

| Richiesta | Cosa è stato fatto |
|---|---|
| Valutare il DTM 5 m d'Italia su Zenodo (record 24009736) e provarlo «con un servizio simulato» | Prova sul file vero (Zenodo accetta le letture a pezzi) e simulazione di `/api/terreno` su 8 località; Paolo ha verificato dal server che Zenodo risponde `206 16384`. Poi la fonte è entrata nel servizio. |

## Cosa cambia

- **Terreno della vista 3D** (`fase4-server/servizio/terreno.py`): ordine **DTM regionali → HR-DTM-5m → Copernicus DEM
  90 m → piatta**. L'HR-DTM-5m (M. Panza, M. Muto, I. Marchesini, M. Rossi, M. Alvioli, G. Iovine – CNR-IRPI/GEO-CNR,
  versione 1.3, **CC BY 4.0**, https://doi.org/10.5281/zenodo.24009736) è un COG di 34,3 GB: **non si copia**, si legge a
  distanza (`/vsicurl/`), ~1 MB per tessera nuova. Il file resta aperto (uno per thread): 0,3–0,9 s per tessera dopo la
  prima. Se Zenodo non risponde la fonte si salta per 10 minuti e si usa il Copernicus.
- **Legenda e intestazione `X-Terreno-Nome`**: «DTM 5 m nazionale HR-DTM-5m del CNR-IRPI (CC BY 4.0), qui da LiDAR
  <nome> (<anno>)» oppure «… qui da TINITALY 1.1 a 10 m» (file `servizio/hrdtm5m_fonti_250m.tif`, 357 kB, dal GeoPackage
  delle fonti della stessa pubblicazione). Il LiDAR copre il 52 % del territorio, TINITALY il 48 % (Roma, Susegana, Bagno di
  Romagna, Cagliari sono TINITALY).
- **Quote dei punti** (`quote_punti`, sagome regionali e ripiego OSM): fuori dai DTM regionali dal nazionale invece che dal
  Copernicus.
- **Copia delle tessere**: la versione cambia (c'è un DTM in più), quindi le tessere si rifanno; da ora `pulisci()` toglie
  subito le cartelle delle versioni vecchie in `/srv/energia/dati/terreno_tessere`.
- **Sito**: attribuzione del terreno in `edificio3d.js`, piè di pagina delle 9 pagine con il 3D, voce nella Sitografia,
  Novità, `EUGENIO_PER_AGENTI.md` (due copie) e `llms.txt`.
- **Configurazione** (facoltativa, nel `.env`): `TERRENO_NAZIONALE_URL` (`""` spegne la fonte),
  `TERRENO_NAZIONALE_PAUSA_S` (600), `TERRENO_NAZIONALE_TIMEOUT_S` (10).

## Misure (19/11/2026)

| Località | Quota del punto | Rilievo d'origine | Tessera z15 nuova |
|---|---|---|---|
| Susegana | 70,2 m (Copernicus 70,9) | TINITALY 1.1 | 0,3–0,4 s |
| Bagno di Romagna | 509,3 m (DTM ER ~510) | TINITALY 1.1 (in ER resta il DTM regionale) | – |
| Palermo | 13,2 m | LiDAR ATA 2012-2013 | 0,5 s |
| Aosta | 582,1 m | LiDAR NOPRS 2008-2015 | 0,9 s (z14) |
| Roma (Colosseo) | 26,8 m | TINITALY 1.1 | 0,5 s |

Prima tessera dopo l'avvio dell'api ~3,6 s (apertura del file remoto); tessere col mare (es. Palermo a zoom 10) ~4 s per il
Copernicus, come prima.

## Test (19/11/2026, workspace di Claude)

| Prove | Esito |
|---|---|
| `fase4-server/tests` (tutte; nuove in `test_terreno.py`: nazionale letto da un servizio HTTP simulato che risponde a pezzi come Zenodo, pausa se non risponde, rilievo d'origine, pulizia delle versioni vecchie) | 345 passate |
| `fase5-sito`: `test_costruisci_pagine`, `test_agenti_sito`, `test_esempi_contributi`, `test_aria`, `test_aria_latenti` | 58 passate, 1 saltata |
| `fase5-sito`, nel browser: `test_mappe_browser`, `test_prove_1911_browser`, `test_prove_0911b/c/d_browser` | 72 passate |

`fase4-server/tests/conftest.py` (nuovo) spegne la fonte vera in tutte le prove: nessuna prova va su Zenodo.

## Procedura AJ1–AJ3

### AJ1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/terreno-hrdtm5m` (collegamento di Claude), scheda **Files changed**, poi **Merge
   pull request** → **Confirm merge**. Contiene anche il lavoro del mattino: **non** serve un'altra pull request per
   `claude/righello-vista3d-cabine`.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.19`) e premi **Publish release**.

### AJ2. [Server] Aggiornamento
Niente da fare a mano: alle 4:40 l'aggiornamento notturno installa la `v2026.11.19`. Per averla subito (`ssh eugenio`):
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.18 a v2026.11.19`, `Release v2026.11.19 installata`. Poi, sempre sul server:
```bash
cd ~/energia/fase4-server && docker compose exec -T api python -c "import urllib.request as u; r = u.urlopen('http://localhost:8000/api/terreno/15/17497/11677.png'); print(r.status, r.headers['X-Terreno-Fonte'], r.headers['X-Terreno-Nome'])"
```
Cosa aspettarsi (Susegana, dopo qualche secondo): `200 dtm DTM 5 m nazionale HR-DTM-5m del CNR-IRPI (CC BY 4.0), qui da
TINITALY 1.1 a 10 m`. Se c'è il DTM del Veneto sul server, invece, `200 dtm DTM 5 m da voli LiDAR Regione del Veneto …`:
va bene anche così (il regionale viene prima).

Cosa fare se va male: `copernicus` invece di `dtm` → `docker compose logs --tail 40 api | grep -i "terreno"` e mandami
le righe (probabile: Zenodo non raggiunto dal container; la ruota ARM di rasterio 1.5.2 legge ZSTD, controllato); per spegnere la fonte nel frattempo
aggiungi `TERRENO_NAZIONALE_URL=` nel `.env` e `docker compose up -d --force-recreate api worker`.

### AJ3. [Browser] Prove (Ctrl+F5)
1. Le prove AI3 di `AGGIORNAMENTO_2026-11-19.md` (righello, 3D della vista, più edifici, rete, cabine, Venezia «piazza San Marco»).
2. https://eugenio.statocritico.it/modelli3d.html: vai su una zona collinare fuori dall'Emilia-Romagna (per esempio
   Conegliano o Assisi), avvicinati e premi «Genera il 3D». Il terreno ha colline e scarpate nitide (prima era morbido,
   a 90 m); la legenda sotto la mappa dice «HR-DTM-5m … qui da …». Se una zona già vista prima mostra il terreno vecchio,
   è la copia del browser (30 giorni): svuota la cache del sito.
