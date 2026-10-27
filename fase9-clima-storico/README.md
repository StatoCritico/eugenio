# Indicatori climatici storici per comune (UNI 10349-1 / DPR 412/93), dal 1940

Calcolo offline, per **tutti i 7.896 comuni italiani** e per **tutti gli anni disponibili** (ERA5 dal
1940, ERA5-Land dal 1950), degli indicatori climatici che la pagina Legge 10 di EuGEnio mostra oggi solo
sulle ultime stagioni: dati mensili come nella UNI 10349-1, gradi giorno e zona climatica come nel
DPR 412/93, temperature di progetto statistiche, tendenze. I risultati sono file statici per il sito più
CSV/parquet nazionali scaricabili.

> Valori dal clima ricostruito (rianalisi). Per la relazione tecnica ex Legge 10 restano obbligatori i
> valori normativi (UNI 10349, DPR 412/93). Servono a diagnosi, verifiche dei consumi, sensibilità.

## 1. Fonte scelta e perché

**Fonte: i file `.om` di Open-Meteo sul bucket pubblico AWS Open Data `s3://openmeteo`**, letti per
riga di griglia, senza chiavi e senza passare dall'API. Sono gli stessi dati ERA5 / ERA5-Land che l'API
storica di Open-Meteo serve (licenza CC BY 4.0), quindi la fonte del progetto non cambia.

| via | esito della verifica (27/10/2026) |
|---|---|
| **API storica Open-Meteo** (`archive-api.open-meteo.com`) | risponde; ma il piano gratuito vale *< 10.000 chiamate/giorno, 5.000/ora, 600/minuto, solo uso non commerciale* ([termini](https://open-meteo.com/en/terms)); una richiesta "pesa" di più se supera 10 variabili o **2 settimane** per **località** ("4 weeks of data equals 3.0 API calls", [pricing](https://open-meteo.com/en/pricing)). La richiesta multi-coordinata non fa risparmiare: conta ogni località (verificato: le quote di 7.896 punti, in 79 richieste da 100 coordinate all'API *elevation*, hanno fatto scattare `429 Too Many Requests`). |
| **Bucket `s3://openmeteo`** ([registry AWS](https://registry.opendata.aws/open-meteo/)) | raggiungibile anonimamente dal cloud; ERA5 `year_1940.om`…`year_2021.om` + `chunk_904…987.om` (fino a 5-6 giorni fa), ERA5-Land dal 1950; variabili ERA5: temperatura, punto di rugiada, radiazione globale e diretta, vento u/v a 10 m; ERA5-Land su Open-Meteo: solo temperatura e punto di rugiada. Nessuna quota (traffico pagato dal programma AWS Open Data). **Scelta.** |
| Google ARCO-ERA5 (`gs://gcp-public-data-arco-era5`) | raggiungibile, ma Zarr a blocchi di **un'ora × tutto il globo** (`chunks [1, 721, 1440]`): per una serie puntuale di 86 anni si leggerebbero ~750.000 blocchi per variabile (TB). Scartato. |
| AWS `era5-pds` (Planet OS) | non risponde più all'elenco pubblico. Scartato. |
| Copernicus CDS | richiede account e chiave personale (non creati). Funzionerebbe (ERA5 e ERA5-Land completi, anche radiazione e vento ERA5-Land) ma con code di ore per richiesta e ~1.000 richieste mensili per coprire 86 anni × variabili: inutile dato che il bucket Open-Meteo basta. Se un giorno servisse: registrarsi su cds.climate.copernicus.eu, accettare la licenza dei dataset "ERA5 hourly data on single levels" ed "ERA5-Land hourly data", copiare la chiave in `~/.cdsapirc` **sul proprio PC** (mai nel repository), `pip install cdsapi`, chiedere per mese l'area `[47.2, 6.5, 35.4, 18.6]` in NetCDF. |

### Stima delle chiamate con l'API (per confronto)

Periodo 1/1/1940–21/10/2026 = 31.706 giorni → 2.265 "chiamate" per località (≤ 10 variabili);
ERA5-Land dal 1950: 2.004.

| strategia | chiamate | giorni a 10.000/giorno |
|---|---:|---:|
| una richiesta per comune (7.896), un solo modello | 17,9 milioni | ~1.790 (quasi 5 anni) |
| raggruppando per cella: 2.229 celle ERA5-Land + 512 celle ERA5 | 5,6 milioni | ~560 (1,5 anni) |
| **bucket S3 (scelta)** | **0** (167.384 richieste HTTP di blocchi a S3, 27 GB) | **55 minuti** (fatto il 27/10/2026) |

I comuni condividono molto le celle: in media **3,5 comuni per cella ERA5-Land** (0,1°) e **15,4 per
cella ERA5** (0,25°); lo scaricamento è infatti per cella e i valori sono poi assegnati ai comuni.

Le sole chiamate all'API gratuita fatte da questo lavoro: le quote DEM dei punti (`elevation`, una
volta: ~7.900 "chiamate") e la verifica a campione (~40).

## 2. Metodo

### Punto del comune e celle
* Elenco ISTAT aggiornato (`Elenco-comuni-italiani.csv`, 7.896 comuni) e confini Gramscii alla revisione
  bloccata del sito (`8aff37c2…`, SHA256 verificati).
* Punto = **baricentro degli edifici** delle sezioni di censimento ISTAT 2021 (pesi EDI21), come nella
  fase 3; per i comuni nati da fusione dopo il 2021 si sommano le sezioni di tutti i comuni d'origine.
  7.890 comuni con baricentro edifici, 6 con baricentro geometrico.
* Quota del punto: DEM Copernicus GLO-90 dall'API `elevation` di Open-Meteo (la stessa quota che l'API
  meteo usa per la correzione). Rispetto all'altitudine della casa comunale del DPR: differenza mediana
  0 m, scarto tipo 97 m, ma **152 comuni oltre 300 m e 33 oltre 500 m**: dove l'abitato è diviso in nuclei
  lontani (fondovalle + località turistica, es. Strembo con Madonna di Campiglio, Grosio) la media pesata
  dei punti cade su un versante (Strembo 2.053 m invece di 714 m).
* **Quota per la correzione di temperatura: altitudine della casa comunale del DPR** (`--quota dpr`,
  predefinita), DEM del baricentro solo per i 135 comuni senza altitudine nel DPR. È la quota a cui si
  riferiscono i GG di legge e toglie i casi sopra; `--quota dem` usa sempre il DEM del baricentro. Il
  punto (lat/lon) e la cella restano quelli del baricentro edifici, decisione del progetto.
* Cella: come `cell_selection=land` di Open-Meteo, tra le 3×3 celle intorno al punto quella di terra con
  quota più vicina; se nessuna è di terra, la più vicina entro 7×7. Distanza media punto–centro cella:
  10 km (ERA5-Land), 25 km (ERA5).

### Serie giornaliera di ogni comune
* Giorno civile in **ora solare (UTC+1) tutto l'anno**: niente salti dell'ora legale; l'ultima ora UTC
  dell'anno passa all'anno dopo (`carry_<anno>.npz`). Giorno valido con almeno 20 ore.
* **Temperatura** (media, minima, massima delle 24 ore) e **pressione del vapore** (media oraria di
  Magnus–Alduchov-Eskridge sul punto di rugiada, come in `legge10.py`): da **ERA5-Land** dal 1950.
* **Correzione di quota** della temperatura con −6,5 °C/km tra quota della cella (orografia di
  ERA5-Land / ERA5, file `static/HSURF.om`) e quota del comune (sopra):
  `T_comune = T_cella + 0,0065 (z_cella − z_comune)`, come fa l'API di Open-Meteo. La pressione del
  vapore non è corretta.
* **1940–1949** (solo ERA5): temperatura ERA5 corretta di quota + scarto medio mensile ERA5-Land − ERA5
  del comune nel 1950–1979; lo stesso per la pressione del vapore. Codice di fonte `E` (o `M` per la
  stagione 1949/50 a cavallo).
* **Irradiazione** globale e diffusa (globale − diretta) su piano orizzontale e **vento** a 10 m
  (media delle velocità orarie da u, v): da **ERA5** per tutto il periodo (ERA5-Land su Open-Meteo non
  le ha), non corretti.
* Comuni la cui cella ERA5-Land non ha dati (9 isole minori: Ponza, Ventotene, Pantelleria, Ustica,
  Leni, Lipari, Malfa, Santa Marina Salina, Lampedusa e Linosa): tutta la serie da ERA5
  (`solo_era5: true`).
* **Nessuna correzione ERA5 → ICON**: quella del progetto esiste solo dal 2022 e per l'Emilia-Romagna;
  la serie lunga nazionale è ERA5/ERA5-Land "grezza" (vedi § 4).

### Indicatori
* **Mensili per anno solare** (UNI 10349-1): T media, media delle minime e delle massime giornaliere,
  irradiazione giornaliera media globale e diffusa (MJ/m²), pressione del vapore media (Pa), vento medio
  (m/s); mese valido con ≥ 28 giorni.
* **Gradi giorno base 20 °C** per stagione 1/7–30/6 (indicata con l'anno d'inizio), somma di
  (20 − T media) > 0 sul periodo di accensione (A 1/12–15/3, B 1/12–31/3, C 15/11–31/3, D 1/11–15/4,
  E 15/10–15/4, F tutto l'anno), stagione valida solo se il periodo è completo:
  * `gg_zona`: sul periodo della **zona di legge del comune** (Allegato A del DPR, da
    `sito_fin/dati/dpr412.json`); se il comune non è abbinato, zona coerente sulla media 1991–2020;
  * `gg_anno`: GG "convenzionali" su tutta la stagione;
  * zona per stagione: la "zona coerente" di `legge10.py` (la zona i cui GG sul proprio periodo cadono
    nella propria fascia: A ≤ 600, B 601–900, C 901–1400, D 1401–2100, E 2101–3000, F > 3000).
    Se più zone sono coerenti (capita a cavallo D/E: es. 2.050 GG sul periodo D e 2.250 sul periodo E) vince
    la prima in ordine A…F, come in `legge10.py`: è la scelta più "mite" ed è da rivedere (vedi dubbi).
* **Temperature di progetto statistiche** (non la UNI 10349-3): invernale = 1° percentile dei minimi
  giornalieri, estiva = 99° percentile dei massimi (come il ripiego di `legge10.py`), su **finestre
  mobili di 10 anni solari completi** (una per anno finale, dal 1949) e sui periodi fissi. Dieci anni sono
  ~3.650 giorni: l'1 % sono ~37 giorni, abbastanza stabile; su un anno solo sarebbero 3-4 giorni.
* **Periodi fissi**: 1951–1980, 1961–1990, 1971–2000, 1981–2010, 1991–2020: anni solari del periodo per
  mensili e temperature di progetto, stagioni che *finiscono* nel periodo per i GG (1991–2020 = 30
  stagioni 1990/91–2019/20); più ultimi 30 e ultimi 10 (anni solari completi e ultime 30 / 10 stagioni
  complete).
* **Tendenze**: pendenza della regressione lineare dei GG sul periodo di zona, in GG per decennio, su
  tutta la serie, dal 1981/82 e sulle ultime 30 stagioni; pendenza della T media annua (°C/decennio).
* **Confronto con il DPR**: differenza (assoluta e %) delle medie delle ultime 10 e 30 stagioni dai GG
  di legge; zona che ne risulterebbe. In più una **proposta**: "DPR aggiornato" =
  GG_DPR × GG(ultime N) / GG(1961–1990) della stessa serie, cioè il valore di legge spostato della
  variazione relativa osservata. Toglie gran parte dell'errore sistematico della cella (coste, città,
  fondovalle, vedi § 4). Il periodo 1961–1990 è un'ipotesi: il DPR non dichiara su quali anni sono
  calcolati i suoi GG.

## 3. Verifica a campione (26 comuni, tutti gli anni)

Campione: `campione.txt` (capoluoghi di tutte le regioni + Ala di Stura, Sestriere, Livigno,
Lampedusa). Risultati in `campione/`, script `verifica.py`.

**Lettura S3 + correzione di quota contro l'API Open-Meteo** (`models=era5_land`, stesso punto,
`timezone=Etc/GMT-1`), anni 2000 (file annuale) e 2023 (file a blocchi):

| comune, anno | bias T media | MAE T media | MAE T min | MAE T max | GG anno API / nostri |
|---|---:|---:|---:|---:|---:|
| Bologna 2000 | +0,01 | 0,11 | 0,19 | 0,14 | 2.342 / 2.351 |
| Bologna 2023 | +0,01 | 0,10 | 0,22 | 0,11 | 2.176 / 2.178 |
| Sestriere 2000 | 0,00 | 0,02 | 0,14 | 0,04 | 6.860 / 6.858 |
| Sestriere 2023 | 0,00 | 0,03 | 0,16 | 0,03 | 6.042 / 6.042 |

A Sestriere l'API sceglie la stessa cella: coincidenza entro l'arrotondamento a 0,1 °C (la T min
dell'API è ~0,14 °C più alta: l'API calcola i minimi dopo l'interpolazione oraria). A Bologna l'API
prende la cella a ovest (11,3°E) e noi quella a est (11,4°E, quota più vicina): 0,4 % sui GG.

**Contro `legge10.py`** (stesse ultime 10 stagioni 2016/17–2025/26, stessa serie): GG sul periodo di
zona identici (± 1 GG di arrotondamento) e stessa zona in tutti i 25 comuni; temperature di progetto
entro 0,0–0,4 °C (noi su 10 anni solari 2016–2025, `legge10.py` su 10 stagioni).

**Contro il DPR 412/93** (correzione alla quota DPR, predefinita):

| comune | DPR | ultime 30 | ultime 10 | diff. 10 | DPR aggiornato 10 | tendenza GG/decennio (tutta / dal 1981) |
|---|---:|---:|---:|---:|---:|---:|
| Torino | 2.617 E | 2.608 | 2.484 | −5,1 % | 2.241 E | −74 / −96 |
| Milano | 2.404 E | 2.451 | 2.323 | −3,4 % | 2.033 D | −73 / −102 |
| Bologna | 2.259 E | 2.209 | 2.087 | −7,6 % | 1.920 D | −64 / −89 |
| Firenze | 1.821 D | 2.029 | 1.918 | +5,3 % | 1.579 D | −50 / −82 |
| Roma | 1.415 D | 1.607 | 1.498 | +5,8 % | 1.216 C | −39 / −68 |
| Napoli | 1.034 C | 1.423 | 1.343 | +30 % | 906 C | −28 / −52 |
| Bari | 1.185 C | 1.194 | 1.131 | −4,5 % | 1.049 C | −27 / −45 |
| Palermo | 751 B | 918 | 855 | +14 % | 656 B | −24 / −30 |
| Cagliari | 990 C | 1.159 | 1.091 | +10 % | 865 B | −29 / −41 |
| Genova | 1.435 D | 1.815 | 1.713 | +19 % | 1.214 C | −58 / −72 |
| Bolzano | 2.791 E | 2.372 | 2.184 | −22 % | 2.205 E | −90 / −144 |
| Livigno | 4.648 F | 6.387 | 6.150 | +32 % | 4.140 F | −108 / −152 |

(tabella completa: `campione/clima_sintesi.csv` e `campione/verifica_campione.txt`; i "DPR aggiornati"
sono in `clima_sintesi.csv`). L'ordine di grandezza torna ovunque; nelle pianure interne la differenza è
di pochi punti e dice "clima più mite". Le grandi differenze hanno cause note: **coste e città** (Napoli,
Genova, Reggio Calabria, Palermo: la cella da 9 km mescola entroterra e collina e non vede l'isola di
calore), **fondovalle alpini** (Bolzano, Trento: inversioni termiche che la rianalisi non risolve; qui la
rianalisi è più calda del DPR), **alta montagna** (Livigno, Sestriere: i valori DPR in quota sono
presumibilmente estrapolati). Per questo il confronto assoluto col DPR va mostrato con cautela; più
robusti sono la **variazione nel tempo** della serie e il "DPR aggiornato". Sul campione lo scarto medio
assoluto dal DPR (ultime 30 stagioni) è 13,0 % con la quota DEM e 11,4 % con la quota DPR.

**Tutta Italia** (7.761 comuni con GG di legge, `dati/clima_sintesi.csv`):

* differenza delle ultime 30 stagioni dal DPR: mediana **+2,8 %**, scarto assoluto medio 9,5 %, 5°–95°
  percentile da −10,8 % a +26,8 % (massimo +64 %); ultime 10 stagioni: mediana **−2,4 %** (−15,4 … +19,8);
* tendenza dei GG: mediana **−59 GG per decennio** su tutta la serie (5°–95°: −114 … −25), **−87** dal
  1981 (−180 … −40); temperatura media annua **+0,28 °C per decennio** (0,14 … 0,36), dal 1940;
* zona che risulterebbe dalla media delle ultime 10 stagioni uguale a quella di legge nel 90 % dei
  comuni (88 % con le ultime 30); con il "DPR aggiornato" alle ultime 10 stagioni solo nel 65 %: 2.747
  comuni scenderebbero di una zona (1.558 da E a D, 664 da F a E, 354 da D a C, 146 da C a B, 25 da B ad A).

## 4. Limiti

* **Risoluzione**: ERA5-Land 0,1° (~9 km), ERA5 0,25° (~28 km): la cella è una media che non vede
  città, coste strette, fondovalle, pendii esposti. La correzione di quota è un gradiente standard e non
  risolve le inversioni.
* **Quota**: corretta solo la temperatura; pressione del vapore, irradiazione e vento sono della cella.
* **1940–1949** meno affidabili (meno osservazioni assimilate in ERA5, risoluzione 0,25° raccordata
  con uno scarto medio mensile).
* **Ultimi mesi**: ERA5T preliminare; l'anno in corso è parziale (escluso dai mensili e dai periodi;
  le stagioni incomplete non hanno GG).
* **Nessuna correzione verso ICON** (la serie di `legge10.py` sul server, dal 2022 in Emilia-Romagna, è
  corretta): i valori qui possono differire da quelli della pagina attuale per i comuni dell'Emilia-
  Romagna. Il confronto sulle stagioni comuni (2022/23–2025/26) va fatto sul server, dove c'è
  `giornaliero.parquet` corretto: passo successivo (vedi § 7).
* **Punti in mare**: per comuni su più isole il baricentro edifici può cadere in mare (Lampedusa e
  Linosa: quota 0); 9 isole minori non hanno cella ERA5-Land → ERA5.
* **Cella scelta con la quota DEM del baricentro**: nei ~150 comuni dove il baricentro cade in quota
  (vedi § 2) anche la cella è "alta" e lontana; la correzione alla quota DPR rimedia alla temperatura
  ma non al clima della cella (Grosio resta +21 % sul DPR). Rimedio possibile: rifare l'assegnazione delle
  celle con la quota DPR e riscaricare (≈ 1 ora).
* Le **temperature di progetto** sono statistiche (percentili), non il metodo della UNI 10349-3.

## 5. Uso

```bash
pip install omfiles fsspec s3fs pandas pyarrow numpy shapely pyproj requests
python scarica.py comuni                 # elenco, baricentri, quote DEM, celle (dati/comuni.parquet)
python scarica.py meteo --campione campione.txt     # prova: solo le celle del campione (cache_campione/)
python scarica.py meteo                  # tutto; riprendibile: rilanciare lo stesso comando
python scarica.py stato                  # anni in cache e mancanti
python scarica.py meteo --aggiorna       # riscarica l'anno in corso (ERA5T), es. una volta al mese
python calcola.py                        # indicatori -> dati/
python verifica.py --cache cache_campione --uscita campione    # verifiche (dopo calcola sul campione)
python -m pytest tests                   # funzioni di calcolo, anche contro legge10.py
```

`calcola.py --cache cache_campione --uscita campione --istat campione.txt` rifà il campione;
`--dpr` indica `dpr412.json` (predefinito `/home/claude/sito_fin/dati/dpr412.json`, solo letto);
`--quota dem` corregge la temperatura alla quota DEM del baricentro invece che all'altitudine del DPR.

Lo scaricamento completo (fatto il 27/10/2026, dati fino al 21/10/2026) ha letto 27 GB di blocchi da S3 in
55 minuti e tiene su disco solo i giornalieri per cella: `cache/` 627 MB in parquet zstd (ERA5-Land
455 MB, ERA5 199 MB, 164 file anno + `celle.parquet` + `carry_*.npz`). `calcola.py` su tutta Italia:
~5 minuti, ~1,5 GB di RAM. Le sezioni di censimento (729 MB) sono state cancellate dopo l'uso:
`scarica.py comuni` le riscarica e ne verifica lo SHA256.

### Aggiornamento automatico sul server (dal 27/10/2026)

Il worker della fase 4 rifà il calcolo **il 10 gennaio e il 10 luglio dalle 3** (`CLIMA_DATE`): il 10 luglio la
stagione di riscaldamento 1/7–30/6 è finita da dieci giorni (ERA5T arriva con ~5 giorni di ritardo) ed entrano i
suoi gradi giorno; il 10 gennaio è finito l'anno solare ed entrano i mensili, le temperature di progetto e la
tendenza annua. Gli script sono nell'immagine in `/app/clima_storico/` (solo i `.py`; dipendenze in più
`omfiles`, `fsspec`, `s3fs`, ~100 MB); cartella di lavoro `/srv/energia/dati/clima_lavoro/` con `comuni.parquet`
(copiato dal PC: lo produce `scarica.py comuni`, che sul server non serve), `cache/`, `scarica.log` e
`clima_mensili.parquet`. Il lavoro esegue, in processi separati:

```bash
python scarica.py --log …/scarica.log meteo --cache …/cache --comuni …/comuni.parquet --aggiorna
python calcola.py --cache …/cache --comuni …/comuni.parquet --uscita /sito/dati/.clima_nuova --dpr /sito/dati/dpr412.json
```

e, se in `.clima_nuova/clima/` ci sono `indice.json` e almeno il 99 % dei JSON pubblicati, scambia la cartella
con `dati/clima/` (due `rename` sullo stesso disco) e sostituisce i due CSV nazionali; il parquet dei mensili
resta nella cartella di lavoro. A regime `--aggiorna` riscarica solo l'anno in corso (a gennaio anche il
precedente): prova del 27/10/2026 sul campione di 26 comuni, anno 2026, 0,33 GB letti da S3 e 132 s in tutto;
per tutta Italia ~10 minuti. La **prima volta** la cache è vuota e si scarica tutta la serie dal 1940 (~1 ora,
27 GB letti, 630 MB su disco). Il calcolo usa ~1,5 GB di RAM: il worker ha `mem_limit: 3g`. Comandi di
installazione e cron provvisorio (finché il worker è spento) nel README della fase 4, sezione «Lavori periodici
sui file del sito». Opzioni aggiunte per questo uso: `--comuni` (in `scarica.py meteo` e `calcola.py`) e
`--log` (in `scarica.py`, prima del sottocomando).

## 6. Prodotti

```
dati/comuni.parquet                 7.896 comuni: punto, quota DEM, celle ERA5-Land ed ERA5, distanze   0,5 MB
dati/clima/indice.json              periodi, scale dei numeri, unità, attribuzione, avvertenza          1 kB
dati/clima/regioni.json             ISTAT -> codice regione                                           110 kB
dati/clima/<RR>.json (20)           per regione: GG per stagione sul periodo di zona, zone, medie,
                                    tendenze di tutti i comuni (Lombardia 0,9 MB)                  4,8 MB in tutto
dati/clima/<RR>/<istat>.json        sintesi del comune: ~7,5 kB (~3 kB compresso)                   62 MB in tutto
dati/clima/<RR>/<istat>_mensili.json  mensili 1940-2025 interi scalati: ~27 kB (~10 kB compresso)  216 MB in tutto
dati/clima_stagioni.csv             nazionale: comune × stagione (679.056 righe)            31 MB (5,8 MB gzip)
dati/clima_sintesi.csv              nazionale: una riga per comune (DPR, medie, tendenze, θ)  1,0 MB (0,3 MB gzip)
dati/clima_mensili.parquet          nazionale: comune × anno × mese, 7 grandezze                         83 MB
```

I due CSV nazionali finiscono con quattro righe che iniziano con `#` (fonte, avvertenza, licenza CC BY 4.0 delle
elaborazioni di EuGEnio e formula di citazione «Fonte: EuGEnio – eugenio.statocritico.it (dati aggiornati il
gg/mm/aaaa)»), scritte da `aggiungi_piede_csv()` in `calcola.py`; con pandas si leggono con `comment="#"`.

`dati/clima/` in tutto: 15.831 file, 284 MB (98 MB in tar.gz). Il browser scarica solo ciò che serve:
~3 kB compressi alla scelta del comune, ~10 kB in più se si sceglie un anno nella tabella mensile, il
file regionale solo per una eventuale mappa. Se 284 MB sono troppi per il sito si possono tenere solo i
`<istat>.json` e i `<RR>.json` (67 MB) e servire i mensili anno per anno dal server o dal parquet.

Formato di `<istat>.json`: `stagioni.da` (prima stagione), `gg_zona[]`, `gg_anno[]` (uno per stagione),
`zona` (stringa, una lettera per stagione, `-` se incompleta), `fonte` (`L`/`E`/`M` per stagione);
`tendenze`; `confronto_dpr`; `progetto.fine[]`/`inv[]`/`est[]` (finestre di 10 anni); `periodi{}` con
mensili medi, GG, zona, θ. In `<istat>_mensili.json` ogni grandezza è un vettore di 12 × anni interi da
dividere per `scala` (T, irradiazione, vento × 10; pressione del vapore in Pa).

Attribuzione da riportare dove si mostrano: *"Weather data by Open-Meteo.com (CC BY 4.0), da ERA5 ed
ERA5-Land. Contiene informazioni modificate del Copernicus Climate Change Service [anno]. Né la
Commissione europea né l'ECMWF sono responsabili dell'uso di queste informazioni."* — ISTAT (CC BY 4.0)
via Gramscii per comuni e sezioni.

## 7. Proposta per la pagina Legge 10 (`proposta_sito/`)

* `clima_storico.js`: modulo autonomo `EUGENIO_CLIMA.mostra(istat, contenitore, {ggDpr})`; legge solo
  file statici (niente API), funziona anche se `/api/clima-legge10` non risponde. Mostra:
  1. cifre: GG medi ultime 10 e 30 stagioni con la differenza % dal DPR, GG per decennio (tutta la serie e
     dal 1981), °C per decennio, "DPR aggiornato" con la zona;
  2. grafico dei GG **stagione per stagione dal 1940/41**, barre più chiare per il decennio ERA5,
     media mobile su 10 stagioni, retta di tendenza, linea rossa del DPR, soglie di zona, striscia
     colorata con la zona risultante di ogni stagione;
  3. tabella mensile UNI 10349-1 con scelta tra **media di un periodo** (1951–1980 … ultimi 10) e **un
     anno** (il file `_mensili` si carica solo allora);
  4. tabella dei periodi (GG zona, GG anno, zona, θ inv./est.) con la riga del DPR;
  5. grafico delle temperature di progetto su finestre mobili di 10 anni.
* `frammento_legge10.html`: dove inserire il contenitore, lo script e i link ai CSV nazionali, e la riga
  da aggiungere a `mostra()` in `legge10.js`.
* `clima_storico.css`: tre regole che usano le variabili di `stile.css`.
* `prova_jsdom.js`: prova senza browser sui file del campione
  (`node prova_jsdom.js ../dati 037006 <node_modules con jsdom>`; provato su Bologna, Alice
  Superiore-fusione 001317 e Grosio).

Passi successivi: confronto con la serie corretta ERA5→ICON sul server per l'Emilia-Romagna (stagioni
2022/23–2025/26); scegliere se mostrare i GG con quota DEM o DPR; aggiornamento automatico (fatto: gennaio e luglio); eventualmente gradi giorno di raffrescamento.
