# Aggiornamento del 19/11/2026 c – scacchiere al posto della foto aerea (AGEA)

Pubblicazione sopra la `v2026.11.19`. Sito **`?v=20261119c`**, release **`v2026.11.19c`**, voce nelle Novità. Cambiano la
fonte `agea` (`fase10-edifici3d/ortofoto/italia.toml`), il proxy delle ortofoto (`fase4-server/servizio/ortofoto.py`) e
qualche testo del sito: l'aggiornamento ricostruisce da solo l'immagine dell'api e fa il Purge di Cloudflare.

## Segnalazione di Paolo (19/11/2026, 19:11)

«Funziona e funziona anche il righello, ma appaiono scacchiere al posto dell'ortofoto (se muovo la vista torna a posto,
poi ricomincia).» Immagine: vista 3D fuori dall'Emilia-Romagna (edifici OpenStreetMap), scacchiere bianche e nere sul
terreno vicino alla camera, foto normale più lontano.

## Causa (verificata dal browser dell'app, 19/11 sera)

- La tessera `https://eugenio.statocritico.it/api/ortofoto/agea/19/280519/192508.jpg` (Assisi) è un JPEG di 11 kB con una
  **scacchiera bianca e nera**, anno 2023, in copia sul server e su Cloudflare.
- La fonte `agea` chiedeva le tessere fino allo zoom 18 al servizio delle tessere già pronte (`/tile/…`, foto giusta) e
  allo **zoom 19** l'`exportImage` dell'ImageServer. **L'`exportImage` del Geoportale AGEA risponde sempre con la
  scacchiera**: provato a Cesena, Roma, Milano, Napoli, Torino, Assisi e Bari, per gli anni 2022, 2023 e 2024, anche agli
  zoom 16 e 17. Le tessere già pronte dello zoom 18 sono giuste dappertutto. Il servizio dichiara `maxScale` 2256,99
  (= zoom 18) e `minPixelSize` 0,597 m.
- Nella vista 3D MapLibre usa lo zoom 19 solo vicino alla camera: per questo le scacchiere comparivano davanti e, muovendo
  la vista, sparivano (altre tessere, a zoom 18) per poi tornare.

## Correzione

- `italia.toml`: fonte `agea` da zoom **10 a 18** (prima 19). Oltre il 18 la mappa ingrandisce le tessere del 18 (~0,43 m a
  terra a 44° N invece di ~0,21: il volo è a 20 cm, ma il servizio non dà di più). Allo zoom 19 il proxy risponde 404 senza
  chiamare AGEA. Nome della fonte senza «20 cm».
- `ortofoto.py`: `scacchiera()` riconosce un'immagine quasi tutta bianca e nera a quadri; una tessera così, da qualunque
  fonte, vale come **errore della fonte** (tessera vuota con `no-store`, mai in copia); una copia già fatta a scacchiera
  oltre `zoom_tessere` non vale.
- Testi: Ortofoto (nota sulle fonti), `EUGENIO_PER_AGENTI.md` (due copie), `llms.txt`, README della fase 4 e della fase 10,
  Novità.
- Prove: `fase4-server/tests/test_ortofoto.py` (zoom 19 → 404 senza chiamate, scacchiera riconosciuta e foto no, tessera a
  scacchiera scartata e non copiata). Fase 4: 347 passate. Fase 5: `test_costruisci_pagine`, `test_agenti_sito`,
  `test_ortofoto_agea_browser`, `test_prove_1911_browser`: 56 passate, 1 saltata.

## Procedura AK1–AK4

### AK1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/scacchiere` (collegamento di Claude), scheda **Files changed**, poi **Merge pull
   request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.19c`) e premi **Publish release**.

### AK2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.19 a v2026.11.19c`, `Release v2026.11.19c installata` e il Purge di
Cloudflare fatto (toglie anche le scacchiere dalla copia di Cloudflare).

### AK3. [Server] Le copie dello zoom 19 (facoltativo, libera spazio)
Non si useranno più. Prima guarda quante sono:
```bash
du -sh /srv/energia/dati/ortofoto/agea/19 2>/dev/null
```
Poi cancellale:
```bash
sudo rm -rf /srv/energia/dati/ortofoto/agea/19
```
Cosa aspettarsi: nessun messaggio. Se la prima riga non stampa niente, la cartella non c'è (dati altrove): mandami l'uscita
di `ls /srv/energia/dati/ortofoto`.

### AK4. [Browser] Prova
1. Apri https://eugenio.statocritico.it/modelli3d.html con **Ctrl+F5**, torna sulla zona della segnalazione e genera il 3D.
2. Avvicinati e ruota la vista: niente scacchiere; vicinissimo la foto è un po' più sfocata (tessere del 18 ingrandite).
3. Se una scacchiera resta, è la copia del browser: svuota la cache del sito (Ctrl+Shift+Canc, «Immagini e file nella
   cache») e ricarica.
