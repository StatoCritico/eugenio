# Aggiornamento del 17/11/2026 – Territorio › Edifici pubblici

Prima pubblicazione del 17/11, sopra la `v2026.11.16h`. Sito **`?v=20261117a`**, release **`v2026.11.17`**, voce nelle
Novità. Pull request #4 (ramo `claude/2026-11-17-immobili-pa`), Merge di Paolo, release pubblicata da Paolo dal collegamento
già compilato.

## Cosa cambia

- **Dati nuovi (fase 7)**: censimento MEF «Patrimonio della PA», dati al 31/12/2023 (CC BY 4.0; 3.257.044 beni), agganciato
  alle particelle del download massivo della cartografia catastale dell'Agenzia delle Entrate (CC BY 4.0, versione del
  22–23/09/2026). Comandi `python -m territorio immobili-pa` (scarica e aggancia) e `immobili-pa-sito` (tessere PMTiles con
  tippecanoe e indice SQLite per l'API). Aggancio automatico con quattro regole (esatto; senza sezione se unica; sezione
  scelta col punto MEF; particella che contiene il punto MEF): **95,2 %** dei beni con identificativo (97,8 % senza il
  Trentino-Alto Adige, che ha il catasto tavolare e non è nei dati dell'Agenzia); 1.814.954 particelle.
- **API (fase 4)**: rotte `/api/immobili-pa/info`, `/cerca`, `/particella/{ref}`, `/bene/{id_bene}` (sola lettura
  sull'indice SQLite, limite per IP 1.200 all'ora). Nell'indice non ci sono il soggetto cedente né codici fiscali.
- **Sito (fase 5)**: gruppo del menu **Patrimonio → Territorio**; pagina nuova **Territorio › Edifici pubblici**
  (`edifici-pubblici.html`); in **Modelli 3D** gli edifici pubblici sono retinati a righe oblique in 2D e in 3D (casella
  tra i livelli) e, scelto un edificio pubblico, compaiono ente e collegamento alla scheda. Novità, Esempi, file per gli
  agenti, `llms.txt`.
- **Caddy**: nessuna modifica. Le tessere stanno nella cartella degli archivi edifici, già servita in `/edifici3d/`.

## Test (17/11/2026, container, Chromium)

| Prove | Passate |
|---|---|
| fase 7 (`tests/`, con tippecanoe vero e controllo del contenuto delle tessere) | 22 |
| fase 4 `test_immobili_pa.py`, `test_agenti.py`, `test_protezione.py` | 23 |
| fase 5 senza browser | 58 (1 saltata) |
| fase 5 `test_menu_browser.py`, `test_esempi_contributi.py`, `test_mappe_browser.py` | 46 |

Prove a mano con i dati nazionali (tessere da 760 MB, indice da 2,3 GB, server locale): Edifici pubblici a Cesena (ospedale
Bufalini retinato, ricerca «bufalini cesena», scheda), vista della Romagna a zoom 8; Modelli 3D con un archivio di prova:
retino in 2D, nota sull'edificio pubblico scelto, retino dei vicini nella vista 3D.

## Procedura AI1–AI6

Server: Oracle Cloud, utente `ubuntu`, clone in `~/energia`. Tempi misurati nel container di Claude (2 vCPU, 8 GB): AI4
circa 40 minuti, AI5 circa 25 minuti; sul server possono essere simili o un po' più lunghi (gira anche il resto). Dati in `/srv/energia/dati`, archivi edifici in
`/srv/energia/dati/edifici` (la `CARTELLA_EDIFICI` del `.env`; se nel tuo `.env` è un'altra, usa quella al passo AI4).

### AI1. [Browser] Merge e release
1. Apri https://github.com/StatoCritico/eugenio/pull/4, scheda **Files changed**, poi **Merge pull request** →
   **Confirm merge**.
2. Scrivi a Claude «merge fatto»: ti manda il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già
   compilato. Aprilo e premi **Publish release**.

### AI2. [Server] Aggiornamento del codice
Alle 4:40 lo fa da solo. Per averlo subito:
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Release v2026.11.17 installata`. L'immagine dell'api si ricostruisce (rotte nuove); il worker si ricrea
come sempre dopo l'api. La pagina Edifici pubblici si apre già, ma dice «Gli immobili delle PA non sono ancora sul server»
finché non fai AI3–AI5.

### AI3. [Server] Programmi per preparare i dati (una volta sola)
```bash
sudo apt update && sudo apt install -y tippecanoe python3-venv
tippecanoe --version
cd ~/energia/fase7-territorio && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```
Cosa aspettarsi: `tippecanoe v2.…` (serve la 2.17 o successiva) e l'installazione di pandas, pyarrow, shapely, httpx.

### AI4. [Server] Scaricare e agganciare (circa un'ora; lascialo andare in tmux)
1. `tmux new -s immobili`
2. Controlla lo spazio: `df -h /srv/energia` (servono almeno **6 GB** liberi: uno ZIP regionale alla volta, il più grande
   ~2,5 GB, più ~1,5 GB di risultati) e la memoria: `free -g` (la composizione usa fino a ~4 GB).
3. Lancia:
```bash
cd ~/energia/fase7-territorio && . .venv/bin/activate
sudo mkdir -p /srv/energia/dati/immobili_pa && sudo chown ubuntu: /srv/energia/dati/immobili_pa
python -m territorio immobili-pa --dest /srv/energia/dati/immobili_pa
```
Cosa aspettarsi: righe `MEF …: N righe` (31 file), poi una riga `AdE <REGIONE>: {...}` per regione (19), infine
`{'beni': 3257044, 'beni_con_identificativo': 3141599, 'beni_con_poligono': 2990318, 'particelle': 1814954}` (numeri
uguali o vicinissimi se l'Agenzia ha aggiornato la cartografia). Puoi staccarti con Ctrl+B poi D e rientrare con
`tmux attach -t immobili`. Se si interrompe, rilancia lo stesso comando: le regioni già fatte (`poligoni/<REGIONE>.parquet`)
non si rifanno.

### AI5. [Server] Tessere e indice per il sito (circa 30–60 minuti; qui 25 minuti su 2 vCPU)
Nella stessa finestra tmux:
```bash
sudo mkdir -p /srv/energia/dati/edifici/immobili_pa && sudo chown ubuntu: /srv/energia/dati/edifici/immobili_pa
python -m territorio immobili-pa-sito --dest /srv/energia/dati/immobili_pa \
    --tessere /srv/energia/dati/edifici/immobili_pa --indice /srv/energia/dati/immobili_pa
ls -la /srv/energia/dati/edifici/immobili_pa /srv/energia/dati/immobili_pa/*.sqlite
```
Cosa aspettarsi: alla fine un dizionario con `'pmtiles': '/edifici3d/immobili_pa/immobili_pa_2023.pmtiles'`; nella cartella
`immobili_pa_2023.pmtiles` (~760 MB) e `indice.json`; l'indice `immobili_pa_2023.sqlite` (~2,3 GB). Durante il lavoro
servono altri ~4 GB temporanei accanto alle tessere (GeoJSON e due PMTiles parziali, cancellati alla fine): controlla
prima con `df -h /srv/energia` che ci siano almeno **8 GB** liberi.
I file sono leggibili da tutti: il container dell'api (utente 1000) li legge senza `chown`.

Facoltativo, per liberare spazio: `rm -r /srv/energia/dati/immobili_pa/mef_2023` (ZIP del MEF, 91 MB; si riscaricano).
**Non** cancellare i parquet in `/srv/energia/dati/immobili_pa`: servono per rifare tessere e indice senza riscaricare.

### AI6. [Browser] Prova
1. https://eugenio.statocritico.it/api/immobili-pa/info → `"disponibile": true`, `"anno": 2023`.
2. https://eugenio.statocritico.it/edifici-pubblici.html (Ctrl+F5): punti in tutta Italia tranne il Trentino-Alto Adige.
   Cerca «ospedale bufalini cesena»: il risultato porta la mappa sul polo ospedaliero; le particelle con edifici sono
   retinate a righe oblique magenta, la scheda a destra mostra l'ente (AUSL della Romagna) e la tipologia.
3. Spegni «Terreni» e «Comuni»: restano solo gli edifici degli altri enti. «Tutti» li riaccende.
4. https://eugenio.statocritico.it/modelli3d.html (Ctrl+F5), a Cesena vicino al Bufalini: gli edifici dell'ospedale sono
   retinati nella mappa 2D; scelto un edificio, sotto il messaggio compare «Edificio pubblico (censimento MEF …)»; dopo
   «Genera il 3D» i volumi pubblici sono retinati anche in 3D. La casella «Edifici pubblici» tra i livelli li spegne.
5. Il menu dei servizi mostra **Territorio** al posto di Patrimonio, con «Edifici pubblici» come seconda voce.

## Ogni anno

Quando il MEF pubblica i dati 2024 (di solito l'anno dopo la rilevazione): AI4 e AI5 con `--anno 2024`. Il sito usa da
solo l'indice più recente; le tessere sono descritte da `indice.json`, che il comando riscrive.
