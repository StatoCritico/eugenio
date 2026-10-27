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

### Istanza Open-Meteo propria (consigliata per tutta Italia)

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

## Cosa produce

```
archivio/
  comuni.parquet, comuni.json        comuni, punti meteo, codici ISTAT e catastali, coordinate mappa
  sorgenti/                          file scaricati da ISTAT e Gramscii
  grezzi/<fonte>/<istat>/<anno>.parquet
  orario/era5|icon|era5_corretto/<istat>.parquet
  correzione/parametri/<istat>.parquet, metriche.json, metriche_comuni.json
  stato_api.json                     consumo dell'API gratuita
pacchetto_server/                    da copiare sul server (fase 4)
  comuni.json, giornaliero.parquet, orario/<istat>.parquet, parametri_correzione.parquet, metriche.json
```

Spazio: ~6 MB per comune con ERA5 dal 2015 (ER ≈ 2 GB, Italia ≈ 50 GB; circa metà sono i pezzi annuali in `grezzi/`, che servono per riprendere e aggiornare). Il pacchetto per il server dell'ER è ~170 MB.

Copia sul server:
```powershell
scp -i $HOME\.ssh\oracle_energia -r E:\meteo\pacchetto_server ubuntu@IP:/srv/energia/dati
```

## Licenze e attribuzioni

- Dati meteo: **Open-Meteo.com**, CC BY 4.0 (ERA5/ERA5-Land: Copernicus Climate Change Service;
  ICON: Deutscher Wetterdienst). Attribuzione obbligatoria: "Weather data by Open-Meteo.com".
- Confini comunali, codici, sezioni di censimento: **ISTAT**, CC BY 4.0, via il repository
  Gramscii *european-territory-boundaries*.
- L'API gratuita di Open-Meteo è per uso non commerciale: va bene per un progetto hobbistico open source.
