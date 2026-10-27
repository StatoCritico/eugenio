# Fase 7 – Territorio: comuni, confini, catasto e patrimonio edilizio diffuso

## Quattro fonti, quattro ruoli

| Fonte | Cosa dà | Come la usiamo |
|---|---|---|
| **ISTAT** – elenco dei comuni | codici ISTAT e catastali (Belfiore), province, capoluoghi, variazioni | scaricato al bisogno (aggiornato ogni 30 giorni) |
| **Gramscii** – confini comunali (ISTAT 1/1/2026, CC BY 4.0) e sezioni di censimento 2021 | mappa SVG dei comuni, baricentro degli edifici | **versione bloccata** e verificata (vedi sotto) |
| **ANNCSU** – Archivio Nazionale dei Numeri Civici delle Strade Urbane (Agenzia delle Entrate e ISTAT, CC BY 4.0, mensile) | civici ufficiali con coordinate dell'accesso | **prima fonte per gli indirizzi**: file nazionale scaricato una volta al mese e interrogato in locale (nessuna chiave, nessuna quota) |
| **Zornade** – API catastale gratuita (10.000 richieste/ora, confermato sull'account il 25/10/2026) | particella, foglio, mappale, superficie, comune catastale, edifici, terreno; geocodifica di riserva | chiamata dal server con la chiave tenuta lì; cache locale |

## Confini: cosa teniamo, dove, e perché

Tre posti diversi, da non confondere:
- **repository** = il codice su GitHub (`statocritico/eugenio`): quello che si versiona e si condivide;
- **cache** = il disco del server (e del PC per la fase 3): file scaricati e conservati, non nel repository;
- **sito** = i file che il browser del visitatore scarica quando apre la pagina.

| Dato | Peso | Dove sta | Perché |
|---|---|---|---|
| Confini di **tutti i 7.896 comuni** (Gramscii, ISTAT 1/1/2026) | 1,5 MB | **cache, tutto il territorio nazionale** | base di tutto: mappa, punti meteo, controlli |
| Confini delle **20 regioni** | 0,13 MB | cache | vista d'insieme |
| Confini delle **province** (110 forme, ISTAT 1/1/2026, con le nuove province sarde) | 0,26 MB | cache; nel sito dentro i file delle regioni | linee provinciali sulle mappe (dal 27/10/2026) |
| **Sezioni di censimento** 2021, tutte le regioni | 730 MB | cache, scaricate una volta | servono solo a calcolare il baricentro degli edifici di ogni comune; il risultato resta in `comuni.parquet` |
| **Elenco comuni** con punti meteo, codici ISTAT e catastali | ~0,5 MB | cache, nazionale | usato da server e sito |
| **Civici ANNCSU georeferenziati**, tutta Italia | ~0,3 GB (20,6 milioni di civici, settembre 2026) | cache (`anncsu/anncsu_civici.parquet`), riscaricato ogni mese | geolocalizzazione degli indirizzi |
| File di mappa per il sito: `italia.json` + uno per regione | 1,9 MB in tutto | **repository e sito** | derivati piccoli, rigenerabili con un comando |
| Revisione del dataset Gramscii in uso | 200 byte | repository (`territorio.lock.json`) | dice quale versione scaricare e verificare |

Quindi sì: in cache teniamo **tutti i confini nazionali** (e solo quelli: niente Europa né Francia,
che il dataset Gramscii contiene). Il servizio funziona così su tutto il territorio; il meteo invece
si scarica regione per regione (fase 3, `--regioni`), perché è la parte pesante.

Perché i dati grezzi non vanno nel repository: 730 MB di sezioni non stanno bene su GitHub, e
copiarli fisserebbe una versione senza dire quale. Perché non leggerli "dal vivo" da Gramscii: il
sito dipenderebbe da un servizio esterno, i browser dei visitatori contatterebbero un altro sito
(privacy) e il dataset potrebbe cambiare senza preavviso. Con la **revisione bloccata** i file si
scaricano da una versione precisa, si verificano con le impronte SHA-256 pubblicate da Gramscii
(`SHA256SUMS`, `census-sections-2021/manifest.json`) e restano in cache; il 2 di ogni mese il server
controlla se ci sono nuovi comuni ISTAT o una nuova versione dei confini e lo segnala.

Perché il sito usa file per regione: l'Italia intera in un solo file sono 1,7 MB (500 kB compressi)
da scaricare a ogni visita, anche da telefono. Con `italia.json` (le regioni, 44 kB compressi) e un
file per regione (da 4 a 75 kB compressi, l'Emilia-Romagna 27 kB) il visitatore scarica solo la
regione che guarda. Oggi il sito mostra la regione scelta con `?regione=09` nell'indirizzo; il
passaggio da una regione all'altra sulla mappa arriverà con la nuova interfaccia.

Aggiornamento dei confini (il server lo segnala da solo):
```bash
python -m meteo_storico territorio-verifica --archivio <archivio>   # nuovi comuni, fusioni, nomi; nuova versione Gramscii
python -m meteo_storico territorio-blocca                            # adotta l'ultima versione dei confini
python -m meteo_storico comuni --archivio <archivio>                 # ricostruisce l'elenco nazionale e i punti meteo
python ../fase5-sito/costruisci_mappa.py --comuni <archivio>/comuni.parquet   # rigenera i file di mappa
```
Un comune nuovo (fusione) richiede poi di scaricarne il meteo (fase 3 `scarica --comuni <codice>`).

## Patrimonio edilizio diffuso

Geolocalizza in blocco gli edifici di un ente (ASL, Comune, Università, …) a partire da un CSV.
Per ogni riga usa, in ordine di affidabilità: coordinate → dati catastali (comune, foglio,
particella, sezione) → indirizzo. Gli indirizzi si cercano **prima nell'ANNCSU**, poi con la
geocodifica di Zornade; il punto si porta sempre sulla particella con Zornade. Restituisce particella
(FID Zornade), foglio, mappale, superficie, comune ISTAT e catastale, punto, **fonte del punto**
(`coordinate`, `catasto`, `ANNCSU`, `Zornade`), indirizzo trovato e un esito (`ok`, `verificare`,
`non_trovato`) con la spiegazione: ad esempio se il comune catastale non coincide con quello indicato,
se più particelle corrispondono, se il civico non c'era e si è usato il più vicino.

```powershell
cd fase7-territorio
py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$A = "C:\Users\ingpa\Documents\claude\pj\statocritico\meteo\archivio"
$P = "C:\Users\ingpa\Documents\claude\pj\statocritico\prove-zornade"   # risultati e cache fuori dal repository
$N = "C:\Users\ingpa\Documents\claude\pj\statocritico\anncsu"          # indirizzario ANNCSU, fuori dal repository

# una volta al mese: indirizzario ANNCSU (~270 MB da scaricare, ~1-2 minuti di conversione)
python -m territorio anncsu-scarica --dest $N
#   solo una regione: --comuni $A\comuni.parquet --regioni 08 ; da uno ZIP già scaricato: --zip file.zip

# la chiave non va mai scritta nel comando né in un file del progetto: così resta nascosta
$s = Read-Host "Chiave Zornade" -AsSecureString
$env:ZORNADE_API_KEY = [System.Net.NetworkCredential]::new("", $s).Password
python -m territorio patrimonio esempi\patrimonio_esempio.csv --comuni $A\comuni.parquet --anncsu $N\anncsu_civici.parquet --dettagli --uscita $P\esempio --cache $P\cache_zornade.sqlite
```
(Su Linux: `read -rs ZORNADE_API_KEY && export ZORNADE_API_KEY`.) Un semplice `Read-Host` senza
`-AsSecureString` mostra la chiave a schermo: se finisce in un messaggio o in uno screenshot va revocata
e rigenerata su app.zornade.com. Senza `--anncsu` gli indirizzi passano solo da Zornade, come prima.

Escono `..._geolocalizzato.csv` e `..._punti.geojson` (da aprire in QGIS o sulla mappa del sito).
La colonna `dettaglio` (con `--dettagli`) contiene la risposta grezza di Zornade: va bene per uso
interno, ma il CSV non va pubblicato né condiviso (la licenza vieta la ridistribuzione dei dati grezzi).

Il CSV può essere in UTF-8 o nella codifica di Windows (quella di Excel "CSV separato da punto e virgola"):
la lettura prova la prima e ripiega sulla seconda. La cache delle risposte Zornade (`cache_zornade.sqlite`) si
svuota delle voci più vecchie di 12 mesi con `territorio.zornade.pulisci_cache` (sul server lo fa il worker
ogni mese, come promette l'informativa privacy).

### ANNCSU: come funziona la ricerca degli indirizzi

Il file nazionale si scarica da
`https://anncsu.open.agenziaentrate.gov.it/age-inspire/opendata/anncsu/getds.php?INDIR_ITA` (ZIP con
`INDIR_ITA_AAAAMMGG.csv`; il portale tiene solo l'ultima versione mensile). `anncsu-scarica` lo legge a
blocchi (~400 MB di memoria), tiene solo i civici con coordinate valide in Italia (scarta le coordinate
`0,0` e quelle metriche finite nei campi in gradi) e scrive `anncsu_civici.parquet` (comune, odonimo,
civico, esponente, lat, lon, metodo di rilevazione) più `anncsu_civici.info` con la data della versione.
Primo download dal portale il 25/10/2026 (versione del 15/09/2026): 27,4 milioni di civici, di cui
**20,6 milioni georeferenziati (75 %)**, convertiti in pochi minuti. Un anno e mezzo prima (gennaio 2025)
erano solo 1,1 milioni: i Comuni li stanno georeferenziando con i fondi PNRR e la copertura cresce di mese
in mese, per questo il file si riscarica ogni mese.

Gli odonimi ANNCSU sono scritti per esteso (`VIA LUIGI ZAMBONI`, `VIA DELL'INDIPENDENZA`, `VIALE GIOSUE'
CARDUCCI`), mentre gli elenchi degli enti usano la forma breve: la ricerca confronta le **parole
significative** (senza tipo di strada, articoli e "San"), riconosce le abbreviazioni (`V.le`, `P.zza`,
`C.so`, `Str.`, `F.lli`, `Circonvall.ne`, `Occ.le`, `Prov.le`, `Mons.`, …) e tollera piccoli errori di
battitura. Il civico può stare nella sua colonna o in fondo all'indirizzo (`Via Zamboni, 33/A`,
`Via Zamboni n. 33`). Inoltre:
- **numeri** in cifre, lettere o romani sono la stessa cosa (`XXIV Maggio` = `VENTIQUATTRO MAGGIO`,
  `Umberto I` = `UMBERTO PRIMO`, `XXIII Settembre` = `23 SETTEMBRE 1845`: l'anno dopo il mese si ignora);
- **nome parziale o invertito**: `Via Mazzini` → `VIALE GIUSEPPE MAZZINI`, `Zancanaro Tono` → `TONO ZANCANARO`;
- **iniziali**: `Via E. Benini` sceglie `ETTORE BENINI` e non `CORRADO BENINI`;
- **tipo di strada per famiglie**: Via/Viale/Strada, Piazza/Piazzale/Largo, Vicolo/Vico, Località/Frazione/Borgo.
  Via scritta per Viale non è un dubbio; Via contro Piazza o Mura sì;
- prefisso di frazione (`LOCALITA' ALFERO VIA GIACOMO LEOPARDI`) ignorato.

Alcune note spiegano cosa è stato fatto senza mettere in dubbio il punto, quindi l'esito resta `ok`:
"foglio con allegato" (catasto), "accesso sulla strada", "esponente A non presente: usato 6",
"usato il civico vicino 29" (il civico cercato non è georeferenziato ma c'è quello accanto, entro ±2) e
"via riconosciuta come …" (nome interpretato, ma il civico esiste tal quale su quella via: `Via Ovidio 99`
→ `VIA PUBLIO OVIDIO NASONE 99`). Restano `verificare` il civico lontano, il civico non indicato, le
vie ambigue e le vie interpretate senza la conferma del civico.

Gli indirizzi d'angolo (`Via Barocci e Martiri d'Ungheria`) si provano una via alla volta. Se una via
non si trova, la nota distingue "via non presente in ANNCSU" da "VIA … è in ANNCSU (N civici) ma il
Comune non ne ha ancora georeferenziato nessuno": per questo `anncsu-scarica` scrive anche
`anncsu_vie.parquet` (civici totali e georeferenziati per via, pochi MB) accanto ai civici.

| Caso | Cosa fa | Esito |
|---|---|---|
| via e civico trovati (anche con esponente: `33/A`) | punto dell'accesso | `ok` |
| civico non georeferenziato | usa il civico più vicino **sullo stesso lato** (stessa parità) e lo scrive nella nota | `verificare` |
| civico non indicato | usa un civico centrale della via | `verificare` |
| via trovata solo con un errore di battitura, o via con lo stesso nome e tipo diverso (`Piazza Santo Stefano` → `VIA SANTO STEFANO` esiste) | lo scrive nella nota | `verificare` |
| via non in ANNCSU, o comune non riconosciuto | passa a Zornade | come prima |

Il punto ANNCSU è l'**accesso** (il portone): spesso cade sulla particella della strada. In quel caso
il codice prova 8 punti a 8 e 16 m (nord, est, sud, ovest) e usa la prima particella che non sia una
strada, scrivendo "accesso sulla strada: usata la particella edificata a ~8 m" (esito `ok`, è normale).
Costa fino a 8 richieste Zornade in più per edificio, solo in quei casi, e restano in cache.

Prova sugli odonimi reali di Bologna (file di gennaio 2025): Via Zamboni 33, Via Indipendenza 10,
Piazza Maggiore 6, Via Rizzoli 1, Strada Maggiore 45, Viale Carducci 12, V.le Filopanti 4 e altri
trovati esattamente, in ~50 ms ciascuno (il comune si carica una volta). Le stesse "Via Zamboni 33" e
"Via Indipendenza 10" non le trova la geocodifica di Zornade. Prova dal vivo del 25/10/2026 sul file di
esempio con il file di settembre 2026: "Via Zamboni 33" → VIA LUIGI ZAMBONI 33, particella 170 del
foglio 190 (immobile), esito `ok`.

Prova su un patrimonio vero (312 sedi AUSL Romagna, 25/10/2026, prima delle migliorie qui sopra):
167 `ok`, 115 `verificare`, 30 non trovati; 282 indirizzi da ANNCSU, 0 da Zornade. Dei 115 da
verificare, 38 lo erano solo per il foglio con allegato e 22 per Via/Viale; dei 30 non trovati, 22
risultano risolvibili con numeri, abbreviazioni e nomi parziali (simulazione sugli odonimi reali della
Romagna). Restano non trovate le vie assenti dall'ANNCSU o senza civici georeferenziati.
Seconda prova, con le migliorie: **232 `ok`, 64 `verificare`, 16 non trovati** (296 da ANNCSU). Dei 15
non trovati con indirizzo, 10 hanno la via in ANNCSU ma senza civici georeferenziati (Savignano sul
Rubicone e Novafeltria, 4 ciascuno, e le 2 sedi di Viale San Miniato a Riccione), 1 è d'angolo
(Sarsina) e 4 non hanno la via nell'archivio (La Pioppa, Via Paoluzza, Via Longiano a Poggio Torriana,
Via delle Messi). Terza prova, con note informative e indirizzario rigenerato: **252 `ok`, 45
`verificare`, 15 non trovati**, come previsto.

### Come risponde davvero l'API Zornade (prove del 25/10/2026)

| Rotta | Comportamento | Cosa fa il codice |
|---|---|---|
| `/parcels/locate?lat=&lng=` | funziona; `foglio` arriva **vuoto**, ma c'è `cadastral_reference` (es. `A944_019000.170`) e `kind` (`immobile`, `strada`, …) | ricava foglio (190), allegato e sviluppo dal riferimento; una particella `strada` o `acque` dà esito `verificare` (per gli indirizzi prima cerca la particella edificata vicina) |
| `/parcels/search?comune=&foglio=&label=` | vuole il **nome** del comune (`Bologna`), non il codice catastale (`A944`), e il foglio **senza zeri** (`190`, non `0190`) | passa il nome del comune e toglie gli zeri iniziali |
| `/geocode/search?q=` | lavora sul solo `q`; il parametro `city` non aiuta. Copertura ~18,7 milioni di civici (OpenAddresses e feed di alcuni grandi comuni): "Piazza Maggiore Bologna" trovata, "Via Zamboni 33 Bologna" e "Via Indipendenza 10 Bologna" no | usata dopo ANNCSU: prova "via civico comune", poi "via comune" (esito `verificare`, nota "civico non trovato"); se manca anche la via, la nota lo dice |

I nomi di colonna sono riconosciuti anche in forme comuni (`mappale`, `fg`, `via`, `latitudine`, …).

Sul server lo stesso servizio è all'indirizzo `POST /api/patrimonio` (massimo 500 edifici per
caricamento, 6 caricamenti l'ora per IP); l'indirizzario ANNCSU sta in `/dati/anncsu/` e il worker lo
riscarica ogni mese (il 12, `ANNCSU_GIORNO`; al primo avvio subito). Consumo Zornade: ~1–2 richieste
per edificio (fino a 8 in più se l'accesso cade sulla strada), +1 con `--dettagli`; 1.000 edifici stanno
in un'ora di quota gratuita. Le ricerche restano in cache (`cache_zornade.sqlite`, ~2–5 kB per edificio)
e non si ripagano.

Attribuzioni obbligatorie dove si mostrano i risultati:
- Zornade, piano gratuito: un **link cliccabile** a https://zornade.com,
  `<a href="https://zornade.com">Dati elaborati da Zornade</a>` (la sola scritta, o il dominio senza
  link, non soddisfa la licenza), più le fonti (catasto Agenzia delle Entrate CC BY 4.0, ISTAT,
  OpenStreetMap ODbL). Vietate la ridistribuzione dei dati grezzi e l'estrazione massiva.
- ANNCSU, quando un punto viene da lì: "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)".

Il GeoJSON porta `attribution_html` e l'elenco `sources`; le risposte dell'API `fonte_url` e `fonti`.

## Dati climatici per la Legge 10

Il modulo `meteo_storico/legge10.py` (fase 3) calcola dal clima reale del comune, sugli ultimi N anni
di ERA5 corretto: dati mensili in impostazione UNI 10349-1 (temperature, irradiazione globale e
diffusa in MJ/m², pressione di vapore, vento), gradi giorno sul periodo della zona (DPR 412/93) e
sull'anno intero, zona climatica risultante, gradi giorno per stagione con tendenza, temperature di
progetto stimate (quantili 0,4 % / 99,6 % delle ore) e il confronto con i valori ufficiali se forniti.

```bash
python -m meteo_storico legge10 --archivio <archivio> --comuni 037006 --anni 10 --ufficiali ufficiali.csv
```
Sul server: `GET /api/clima-legge10/{istat}?anni=10`. Per la relazione tecnica restano obbligatori i
valori normativi (UNI 10349, DPR 412/93): questi servono per diagnosi, verifiche dei consumi reali e scenari.

Prova su Bologna con le sole 3 stagioni 2023/24–2025/26 dell'archivio di prova: 1.837 GG sul
periodo della zona D (1.898 sul periodo della zona E), contro i 2.259 GG ufficiali del DPR 412 e la
zona E. Con 10 stagioni il confronto sarà più solido, ma la direzione (inverni più miti dei valori
di norma, che risalgono a serie storiche molto più vecchie) è attesa.

## Test

```powershell
python -m pytest tests -q      # 12 test, nessuna chiamata di rete (Zornade simulato, ZIP ANNCSU costruito nel test)
```
