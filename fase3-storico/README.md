# Fase 3 – Archivio meteo storico per comune (Open-Meteo) e correzione ERA5

Costruisce, per ogni comune, le serie orarie delle 8 variabili meteo usate dal progetto e le
prepara per il server. Si può eseguire **sul PC** (con l'archivio su disco esterno) o sul server.

| Variabile | Unità | Perché conta per l'energia |
|---|---|---|
| `temperature_2m` | °C | riscaldamento/raffrescamento, gradi giorno |
| `relative_humidity_2m` | % | carico latente, comfort, pompe di calore |
| `shortwave_radiation` | W/m² | apporti solari, fotovoltaico |
| `diffuse_radiation` | W/m² | fotovoltaico e apporti su facciate non esposte |
| `wind_speed_10m` | km/h | dispersioni per infiltrazione |
| `cloud_cover` | % | proxy di illuminazione e radiazione |
| `precipitation` | mm | umidità delle murature, comportamento utenti |
| `snowfall` | cm | eventi estremi, carichi di picco |

## Le due serie

| | ERA5-Seamless | ICON storico |
|---|---|---|
| Cos'è | rianalisi ECMWF/Copernicus (ERA5 0,25° + ERA5-Land 0,1° per temperatura e umidità) | previsioni archiviate dei modelli DWD ICON (D2 2 km, EU 7 km, globale) |
| API | `archive-api.open-meteo.com`, `models=era5_seamless` | `historical-forecast-api.open-meteo.com`, `models=icon_seamless` |
| Periodo | dal 1950 (qui dal 2015), ritardo ~5 giorni | **dal 14/11/2022** |
| Uso | modalità di **lungo periodo** (giornaliera, 5–10 anni) | modalità di **breve periodo** (oraria) e riferimento per la correzione |

Verifica fatta sull'API (ottobre 2026): ICON-2I di Arpae è archiviato solo dal 14/04/2025 ed
ECMWF IFS dal 04/02/2024; *ICON seamless* è l'unica serie ad alta risoluzione che copre il periodo
"2022–oggi". Per questo la correzione parte da **novembre 2022** e non da gennaio.

## La correzione ERA5 (da spiegare sul sito)

**Problema.** Il modello impara il legame consumi↔meteo su anni di ERA5, ma in esercizio riceve
previsioni ICON. Le due fonti hanno differenze sistematiche (risoluzione, orografia, costa): senza
correzione il modello vedrebbe un "salto di clima" fra passato e previsione.

**Metodo**, per ogni comune, variabile, mese e ora del giorno, sul periodo comune:
- temperatura, umidità, nuvolosità → si aggiunge la differenza media ICON − ERA5;
- radiazione globale e diffusa, vento → si moltiplica per il rapporto Σ ICON / Σ ERA5
  (limitato fra 0,5 e 2; radiazione solo nelle ore di luce; diffusa mai superiore alla globale);
- pioggia e neve → fattore mensile (limitato fra 0,3 e 3);
- ogni mese usa anche il precedente e il successivo (pesi ¼ ½ ¼) per stime stabili.

**Validazione.** I parametri vengono stimati sui dati fino a 12 mesi fa e verificati sugli ultimi 12
mesi, che il metodo non ha visto. **Una variabile viene corretta solo se l'errore diminuisce**:
altrimenti resta come in ERA5 (succede spesso per pioggia e neve). Le metriche finiscono in
`correzione/metriche.json`, che il sito mostra.

Prova su Bologna e Ravenna (verifica ottobre 2025–ottobre 2026):

| Grandezza | Errore (RMSE) prima | dopo |
|---|---|---|
| Temperatura oraria | 1,58 °C | 1,31 °C |
| Temperatura media giornaliera | 1,01 °C | 0,81 °C |
| **Gradi giorno mensili (base 20)** | **16,7 GG** | **7,0 GG** |
| Umidità relativa | 9,6 % | 8,4 % |
| Vento | 3,5 km/h | 3,2 km/h |
| Pioggia (totali mensili) | 19,0 mm | non corretta (peggiorava) |

Sui gradi giorno, la grandezza che conta di più per i consumi termici, l'errore si riduce di oltre la metà.

## Installazione sul PC Windows

1. Installa **Python 3.12** da <https://www.python.org/downloads/> (spunta *Add python.exe to PATH*).
2. In PowerShell, nella cartella `fase3-storico`:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   (se PowerShell blocca lo script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)

Su Linux/server: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.

## Uso

```powershell
# archivio FUORI dalla cartella del codice (sul PC di Paolo: ...\statocritico\meteo\archivio;
# va bene anche un disco esterno, es. E:\meteo\archivio). Solo Emilia-Romagna (predefinito).
$A = "C:\Users\ingpa\Documents\claude\pj\statocritico\meteo\archivio"
New-Item -ItemType Directory -Force $A
python -m meteo_storico comuni   --archivio $A                # una volta: 7.896 comuni, punti, codici (scarica ~730 MB di sezioni)
python -m meteo_storico scarica  --archivio $A --dal 2015-01-01   # giorni (vedi sotto); si può interrompere e riprendere
python -m meteo_storico correggi --archivio $A                # pochi minuti
python -m meteo_storico esporta  --archivio $A --dest E:\meteo\pacchetto_server
python -m meteo_storico stato    --archivio $A
```

Per provare prima su due comuni: `--comuni "037006,039014"` (Bologna, Ravenna). **In PowerShell le
virgolette servono**: senza, `037006,039014` diventa una coppia di numeri e perde gli zeri iniziali
(dal 25/10/2026 il programma li rimette comunque da solo).

Per riprendere dopo un'interruzione (Ctrl+C, riavvio): `cd` nella cartella `fase3-storico`,
`.\.venv\Scripts\Activate.ps1`, reimpostare `$A` e rilanciare lo stesso `scarica`. Per farlo correre
senza pause: Impostazioni → Sistema → Alimentazione → *Sospensione: Mai* con l'alimentatore collegato.
Per altre regioni: `--regioni 08,09,11` o `--regioni tutte`.

**Il punto di ogni comune** è il baricentro degli edifici delle sezioni di censimento ISTAT 2021
(pesato col numero di edifici): rappresenta dove si consuma energia ed evita, per i comuni montani,
il clima di una cima disabitata. Per i pochi comuni senza sezioni (fusioni dopo il 2021) si usa il
baricentro geometrico.

### Quanto ci vuole con l'API gratuita

L'API gratuita consente 10.000 "chiamate" al giorno e 300.000 al mese, dove un comune × un anno con
8 variabili vale ~21–26 chiamate. Misurato il 25/10/2026 su Bologna e Ravenna: **411 chiamate per
comune** (ERA5 2015–2026 ~308, ICON 11/2022–2026 ~103). Lo script rispetta da solo i limiti (tiene il conto su file e si mette
in pausa) e **riprende da dove si era fermato**:

| Ambito | Volume | Tempo |
|---|---|---|
| Emilia-Romagna (330 comuni), ERA5 2015→oggi + ICON 2022→oggi | ~135.000 chiamate | **~14 giorni** di esecuzione (anche a più riprese) |
| solo ICON per l'Emilia-Romagna (se ERA5 arriva da un'istanza propria) | ~34.000 chiamate | ~3,5 giorni |
| Tutta Italia | ~2,6 milioni | non praticabile: serve un'istanza propria |

Si può lasciare il PC acceso, oppure eseguirlo sul server Oracle in una sessione `tmux`.
Download dell'Emilia-Romagna avviato sul PC il 25/10/2026 (prova su Bologna e Ravenna riuscita).

### Tutta Italia: lettura diretta dei file su AWS (`scarica-s3`, dal 29/10/2026)

Per tutta Italia (7.896 comuni) l'API gratuita non basta (~2,6 milioni di chiamate) e un'istanza Open-Meteo propria è
troppo lenta (prova del 28/10/2026 sul server: ERA5 ~12 s per anno e per richiesta fino al 2021, ~2,5 min dal 2022,
ICON storico in timeout, perché ogni punto apre centinaia di file). `scarica-s3` legge invece **direttamente i file
`.om` di Open-Meteo sul bucket pubblico AWS** (`s3://openmeteo`, accesso anonimo, nessuna quota), per righe di griglia e
per gruppi di comuni vicini, come la fase 9. Scrive gli stessi file di `scarica` (`grezzi/` e `orario/`), quindi
`correggi` ed `esporta` non cambiano.

```bash
python -m meteo_storico scarica-s3 --archivio /srv/lavoro/archivio --regioni tutte --dal 2015-01-01 --per-gruppo 800
python -m meteo_storico correggi   --archivio /srv/lavoro/archivio --regioni tutte
python -m meteo_storico esporta    --archivio /srv/lavoro/archivio --regioni tutte --dest /srv/lavoro/pacchetto
```

Stesse regole dell'API (modulo `meteo_storico/s3.py`), verificate il 28–29/10/2026 su Trento, Bologna, Firenze, Roma,
Bari e Palermo contro l'API:
- **ERA5-Seamless**: temperatura e punto di rugiada da ERA5-Land (0,1°), il resto da ERA5 (0,25°), cella più vicina;
  temperatura e punto di rugiada riportati alla quota del comune con 6,5 °C/km (quota dal Copernicus DEM 90 m di
  Open-Meteo, `data/copernicus_dem90`); umidità da temperatura e punto di rugiada; diffusa = globale − diretta; vento
  da u e v; neve = acqua equivalente × 0,7. Scarto dall'API: solo arrotondamenti.
- **ICON seamless**: ICON-D2 (2 km) dove copre, altrimenti ICON-EU (7 km), ora per ora; tra le 3×3 celle vicine quella
  con la quota più simile al comune; temperatura riportata alla quota del comune; globale = diretta + diffusa. Su S3
  c'è **dal 24/05/2023** (con l'API dal 14/11/2022). Confronto su 1.251 giorni per 6 comuni
  (`statocritico\pacchetti\confronta_icon.py`): ICON-EU uguale all'API, ICON-D2 uguale tranne il file del
  13–15/01/2024 (chunk 3914), lasciato vuoto.
- Riprendibile: un pezzo comune × anno completo non si rifà. `--per-gruppo` regola la memoria (800 comuni ≈ 2 GB).
- File di lavoro: `celle_s3.parquet` (quota e celle di ogni comune). Dipendenze in più: `omfiles`, `fsspec`, `s3fs`
  (già nell'immagine del server per la fase 9).

### Archivio psicrometrico dal 1940 (`scarica-psicro`, 14/11/2026)

Per il menu **«Trattamento aria»** del sito (diagramma psicrometrico, ore di funzionamento, carichi latenti, free
cooling) serve, per ogni comune, la serie **oraria** di temperatura e umidità relativa il più lunga possibile. Decisione di
Paolo: un archivio leggero con **solo temperatura e punto di rugiada → T e UR, ora per ora, per tutti i comuni, dal
1940**. Modulo `meteo_storico/psicro.py`; il server lo legge con le rotte `/api/psicro/…` (README della fase 4).

```bash
python -m meteo_storico scarica-psicro --archivio /srv/lavoro/archivio --regioni tutte --dal 1940-01-01 --blocco 400 \
  --cartella-psicro /dati/psicro
python -m meteo_storico aggiorna-psicro --cartella-psicro /dati/psicro --orario /dati/orario   # come il worker ogni notte
python -m meteo_storico stato --archivio /srv/lavoro/archivio --regioni tutte                  # riga «psicro»
```
Opzioni: `--dal` (predefinito 1940-01-01), `--al` (predefinito l'ultima ora di ERA5 su S3, ~5 giorni fa), `--comuni` o
`--regioni`/`--regione`, `--blocco N` (= `--per-gruppo`, comuni letti insieme), `--cartella-psicro` (predefinita
`<archivio>/psicro`), `--tieni-lavoro` (non cancella i pezzi annuali).

**Formato** (`<cartella>/<istat>.parquet`, una riga per ora con dati; le ore senza dati non ci sono e nell'API diventano
`null`):

| Colonna | Tipo | Contenuto |
|---|---|---|
| `ora` | int32 | ore dal 1970-01-01T00:00Z (UTC; prima del 1970 negative) |
| `t` | int16 | temperatura a 2 m in **decimi di °C**, riportata alla quota del comune |
| `ur` | uint8 | umidità relativa in % (vuota se manca il punto di rugiada) |
| `fonte` | uint8 | 1 = ERA5/ERA5-Land grezzo riportato in quota come `s3.py`; 2 = serie oraria ERA5 corretta verso ICON (`orario/era5_corretto`, dal 2015); 3 = ICON storico (`orario/icon` dell'archivio o `/dati/orario` del server) |

Metadati del file: `eugenio_formato` (`psicro_v1`), `istat`, `quota_m` (quota del punto meteo dal Copernicus DEM 90 m),
`dal`, `al`. Ora per ora vince la fonte 2, poi la 3, poi la 1. Codifica delta su tutte le colonne e zstd 6 (row group di
~10 anni, statistiche su `ora`: le finestre brevi leggono solo l'ultimo pezzo). Nella stessa cartella `celle.parquet`:
quota e celle ERA5/ERA5-Land di ogni comune (pressione nell'API, aggiornamento notturno da S3 senza l'archivio intero).

**Da dove arrivano i dati.** Stessi file e stesse regole di `scarica-s3`, ma solo `temperature_2m` e `dew_point_2m`:
ERA5-Land (0,1°) **dal 1950** dove ha la cella di terra, ERA5 (0,25°) per il **1940–1949** e, ora per ora, dove ERA5-Land
manca (mare, isole piccole; ERA5 si legge solo per i comuni che ne hanno bisogno); temperatura e punto di rugiada
riportati alla quota del comune con 6,5 °C/km (quota e celle da `celle_s3.parquet`, già pronto se `scarica-s3` è stato
fatto); UR = `s3.umidita(t, td)`. Disponibilità sul bucket verificata il 14/11/2026: `copernicus_era5/*/year_1940.om`
c'è (`year_1939` no), `copernicus_era5_land/*/year_1950.om` c'è (`year_1949` no); file annuali fino al 2021, poi
`chunk_*.om` di 21 giorni. Poi, per le ore dal 2015, la serie corretta dell'archivio (`orario/era5_corretto/<istat>.parquet`)
e, dopo la sua fine, ICON (`orario/icon/<istat>.parquet`).

**Come lavora (riprendibile, memoria limitata).** Comuni in ordine di latitudine e longitudine, a gruppi di `--blocco`;
per ogni gruppo un anno alla volta in `<cartella>/.lavoro/<gruppo>/<anno>.parquet` (un row group per comune: un anno già
scritto non si rifà). Finiti gli anni del gruppo, ogni comune diventa un file solo (pezzi annuali + file già presente +
serie corretta + ICON) con scrittura atomica, e il lavoro del gruppo si cancella: i file finali compaiono un gruppo alla
volta e il server li usa subito. Un comune con il file già completo per il periodo chiesto si salta; dal 16/11 conta
come completo anche se gli mancano al più **30 giorni** in fondo (`MARGINE_FINE`): la fine di ERA5 avanza ogni notte e prima
un rilancio il giorno dopo rifaceva tutti i comuni (le ore mancanti le aggiunge l'aggiornamento notturno, fino a 45 giorni).
**Letture riprovate** (16/11): se un file `.om` risulta illeggibile («Not an OM file», Open-Meteo lo sta riscrivendo di notte)
`s3.leggi` dimentica dimensione e blocchi in cache di quel file e riprova fino a 3 volte (dopo 30, 60, 90 s). Memoria: un gruppo ×
un anno (400 comuni ≈ 150 MB, 800 ≈ 300 MB) più un comune alla volta nell'unione. Mentre lavora c'è il file
`<cartella>/.scarica_in_corso` (aggiornato a ogni anno): l'aggiornamento notturno del worker in quel tempo non tocca la
cartella.

**Spazio e tempo per tutta Italia (misure del 14/11/2026 in questo ambiente, dati veri da S3).**
- Spazio: **1,5 byte per ora** (Bologna 1949–1950 e 400 punti a caso nel Nord, dati veri; 2,1 senza la codifica delta).
  Dal 1/1/1940 a novembre 2026 sono ~762.600 ore → **~1,15 MB per comune**, **~9 GB per 7.896 comuni** (8,5–10 GB secondo
  i comuni; la stima di Paolo di ~8 GB era giusta come ordine di grandezza). Durante lo scarico in più i pezzi annuali di
  un gruppo (~0,5 GB con 400 comuni).
- Sul server (15–16/11/2026): il gruppo 1 ha fatto gli anni in 14 minuti, ~1,4 byte per ora come qui; lo scarico si è
  fermato una volta alle 00:10 con «Not an OM file» (anno 2026 del gruppo 9, file riscritto da Open-Meteo) e il rilancio
  del mattino ripartiva da capo per la fine avanzata di un giorno (rimedio: `--al` fisso; ora corretto, vedi sopra).
- Tempo: un gruppo di 400 comuni legge un anno dei file annuali in **~5 s** (~0,02 GB da S3) e un anno dei file a chunk
  (2022 →) in **~30 s** (~0,06 GB); l'unione costa ~0,15 s per comune. Per 7.896 comuni (20 gruppi): 82 anni × 20 × 5 s
  + 5 anni × 20 × 30 s + 20 minuti di unione ≈ **3,5 ore**, ~40 GB letti da S3 (nessun costo, nessuna quota). Sul server
  ARM con la rete di Oracle contare **4–8 ore**: si può lasciare in `tmux` e riprendere.
- Prova reale fatta qui: 5 capoluoghi 1949–1950 e 400 punti nel Nord per il 1945, il 1950 e il 2024; confronto dei valori
  con l'API non ripetuto (limite giornaliero dell'API pubblica esaurito dall'ambiente di prova): `t_td` replica riga per
  riga `s3.era5`, già verificato contro l'API il 28–29/10/2026.

**Aggiornamento ogni notte** (worker della fase 4, `psicro.aggiorna`): aggiunge solo ore nuove, prima da ICON del server
(fonte 3), poi da ERA5 su S3 per i comuni rimasti indietro (fonte 1). Un buco lasciato da una notte saltata non si riempie
da solo: per riempirlo rilanciare `scarica-psicro` sui comuni interessati (rifà il file intero con tutte le fonti).

**Legge 10 e archivio psicrometrico.** La pagina Legge 10 offre ora ultima stagione · 5 · 10 · 20 · tutte, ma le stagioni
oltre l'archivio giornaliero (dal 2015) **non** si prendono da qui: `legge10.calcola` usa anche irradiazione globale e
diffusa e vento (tabella mensile UNI 10349-1), che questo archivio non ha, e mescolare ERA5 corretto e non corretto nella
stessa media darebbe valori non confrontabili. Per i gradi giorno stagione per stagione dal 1940 c'è già la sezione
«Clima dal 1940» (fase 9). `legge10.calcola` accetta `anni=0` (tutte) e `anni=1` (con la nota «valori indicativi») e
restituisce `stagioni_richieste`, `stagioni_disponibili`, `prima_stagione_disponibile` e `note`.

### Istanza Open-Meteo propria (superata da `scarica-s3`)


Open-Meteo è open source (AGPL-3.0): un container Docker legge i dati direttamente dall'archivio
pubblico su AWS S3 e li tiene in cache, **senza limiti di chiamate**. Sul server Oracle (Docker è già
installato dalla fase 1):

```bash
docker volume create open-meteo-data
docker run -d --rm --name open-meteo -v open-meteo-data:/app/data \
  -e REMOTE_DATA_DIRECTORY=https://openmeteo.s3.amazonaws.com/data/ -e CACHE_SIZE=40GB \
  -p 127.0.0.1:8080:8080 ghcr.io/open-meteo/open-meteo

# prova: deve restituire dati orari
curl "http://127.0.0.1:8080/v1/archive?latitude=44.5&longitude=11.34&start_date=2020-01-01&end_date=2020-01-02&hourly=temperature_2m&models=era5_seamless"
curl "http://127.0.0.1:8080/v1/forecast?latitude=44.5&longitude=11.34&start_date=2023-01-01&end_date=2023-01-02&hourly=temperature_2m&models=icon_seamless"

python -m meteo_storico scarica --archivio /srv/energia/archivio --regioni tutte --locale http://127.0.0.1:8080
docker stop open-meteo     # a fine download
```

Se la seconda prova (ICON storico) non restituisce dati, l'istanza locale non ha l'archivio delle
previsioni: usare `--locale` solo per ERA5 (`--fonte era5`) e l'API pubblica per ICON
(`--fonte icon`, ~3 settimane per tutta Italia). Su PC Windows lo stesso container gira in WSL2
con Docker Engine (gratuito), senza Docker Desktop.

## Dati climatici per la Legge 10 e aggiornamento dei comuni

```powershell
python -m meteo_storico legge10 --archivio $A --comuni 037006 --anni 10 [--ufficiali valori_norma.csv]
python -m meteo_storico territorio-verifica --archivio $A
python -m meteo_storico territorio-blocca
```
Il primo produce per ogni comune un JSON e un CSV mensile (UNI 10349-1, gradi giorno DPR 412/93,
zona climatica risultante, tendenza, temperature di progetto stimate); dettagli nel README della
fase 7. Gli altri due controllano nuovi comuni ISTAT e nuove versioni dei confini Gramscii.

**Zona climatica risultante** (`legge10.zona_risultante`, decisione del 27/10/2026, uguale nella fase 9 e
negli indicatori CTI): una zona è *coerente* se i suoi gradi giorno, calcolati sul suo stesso periodo di
accensione, cadono nella sua fascia dell'art. 2; a cavallo di due zone possono esserlo entrambe (es. 2.050 GG
sul periodo D e 2.250 sul periodo E). Si prende la zona del DPR 412/93 del comune se è tra le coerenti
(`calcola(..., zona_dpr=...)`; sul server la passa `servizio.storici.zona_dpr` leggendo `dpr412.json`);
altrimenti, o senza zona DPR, la coerente più lontana dai bordi della propria fascia; se nessuna è coerente,
la zona dei GG sull'anno intero.

## Cosa produce

```
archivio/
  comuni.parquet, comuni.json        comuni, punti meteo, codici ISTAT e catastali, coordinate mappa
  sorgenti/                          file scaricati da ISTAT e Gramscii
  grezzi/<fonte>/<istat>/<anno>.parquet
  orario/era5|icon|era5_corretto/<istat>.parquet
  psicro/<istat>.parquet, celle.parquet   archivio psicrometrico dal 1940 (scarica-psicro; sul server /srv/energia/dati/psicro)
  correzione/parametri/<istat>.parquet, metriche.json, metriche_comuni.json
  stato_api.json                     consumo dell'API gratuita
pacchetto_server/                    da copiare sul server (fase 4)
  comuni.json, giornaliero.parquet, orario/<istat>.parquet, parametri_correzione.parquet, metriche.json
  giornaliero.parziale/              solo durante `esporta` (blocchi già fatti: si riprende da lì)
```

**Giornaliero a blocchi (07/11/2026).** Per tutta Italia `giornaliero.parquet` ha ~34 milioni di righe: `esporta` non
lo costruisce più in memoria. Elabora i comuni in ordine di codice ISTAT a blocchi di `COMUNI_PER_BLOCCO` (100, in
`meteo_storico/aggrega.py`; `--comuni-per-blocco` per cambiarlo), scrive ogni blocco in `giornaliero.parziale/` e alla
fine li unisce in un solo file **ordinato per comune e data, un row group per blocco** (un comune mai diviso tra due
row group), poi cancella la cartella. Se `esporta` si interrompe, rilanciato con le stesse opzioni rifà solo i blocchi
mancanti. Il server legge un comune alla volta (solo il suo row group) e aggiorna il file un pezzo alla volta
(README della fase 4, «Meteo nazionale a blocchi»). Un giornaliero scritto prima si controlla o si converte una volta
con:
```bash
python -m meteo_storico giornaliero-blocchi --file pacchetto_server/giornaliero.parquet --solo-verifica
python -m meteo_storico giornaliero-blocchi --file pacchetto_server/giornaliero.parquet
```
(file ordinato: una passata; non ordinato: una lettura per blocco, riprendibile in `giornaliero.parziale/`; il file
originale resta valido finché quello nuovo non è pronto). Funzioni: `aggrega.aggiorna_a_blocchi`,
`aggrega.leggi_comune`, `aggrega.info_giornaliero`.

**Risposte troncate dell'API (07/11/2026).** `scarica.richiesta` riprova una risposta 200 con il JSON interrotto o con
meno punti di quelli chiesti (fino a 4 volte di fila, pause di 5–40 s, sempre col limitatore; poi errore), invece di
fermare `scarica` o l'aggiornamento del server. Prova: `fase4-server/tests/test_scarica_risposte.py` (la fase 3 non ha
una cartella di test propria: le sue funzioni si provano dalla fase 4).

Spazio: ~6 MB per comune con ERA5 dal 2015 (ER ≈ 2 GB, Italia ≈ 50 GB; circa metà sono i pezzi annuali in `grezzi/`, che servono per riprendere e aggiornare). Il pacchetto per il server dell'ER è ~170 MB.

Copia sul server (corretta il 28/10/2026: con `scp -r pacchetto_server ...:/srv/energia/dati` i file finivano in
`/srv/energia/dati/pacchetto_server/` invece che nella cartella dati):
```powershell
tar -czf meteo_pacchetto.tar.gz -C pacchetto_server .
scp meteo_pacchetto.tar.gz eugenio:~/
# sul server:
tar -xzmf ~/meteo_pacchetto.tar.gz -C /srv/energia/dati
```
Procedura completa, con l'accensione del worker: `AGGIORNAMENTO_meteo_fase3.md` nella cartella principale.

## Licenze e attribuzioni

- Dati meteo: **Open-Meteo.com**, CC BY 4.0 (ERA5/ERA5-Land: Copernicus Climate Change Service;
  ICON: Deutscher Wetterdienst). Attribuzione obbligatoria: "Weather data by Open-Meteo.com".
- Confini comunali, codici, sezioni di censimento: **ISTAT**, CC BY 4.0, via il repository
  Gramscii *european-territory-boundaries*.
- L'API gratuita di Open-Meteo è per uso non commerciale: va bene per un progetto hobbistico open source.
