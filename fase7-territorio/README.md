# Fase 7 – Territorio: comuni, confini, catasto e patrimonio edilizio diffuso

## Fonti e ruoli

| Fonte | Cosa dà | Come la usiamo |
|---|---|---|
| **ISTAT** – elenco dei comuni | codici ISTAT e catastali (Belfiore), province, capoluoghi, variazioni | scaricato al bisogno (aggiornato ogni 30 giorni) |
| **Gramscii** – confini comunali (ISTAT 1/1/2026, CC BY 4.0) e sezioni di censimento 2021 | mappa SVG dei comuni, baricentro degli edifici | **versione bloccata** e verificata (vedi sotto) |
| **ANNCSU** – Archivio Nazionale dei Numeri Civici delle Strade Urbane (Agenzia delle Entrate e ISTAT, CC BY 4.0, mensile) | civici ufficiali con coordinate dell'accesso | **prima fonte per gli indirizzi**: file nazionale scaricato una volta al mese e interrogato in locale (nessuna chiave, nessuna quota) |
| **MEF** – censimento «Patrimonio della PA» (dati al 31/12/2023, CC BY 4.0) e **Agenzia delle Entrate** – download massivo della cartografia catastale (CC BY 4.0) | immobili delle Pubbliche Amministrazioni con la particella catastale disegnata | `immobili-pa`: file nazionali in cache, una volta l'anno (vedi «Immobili delle PA») |
| **Zornade** – API catastale gratuita (10.000 richieste/ora, confermato sull'account il 25/10/2026) | particella, foglio, mappale, superficie, comune catastale, edifici, terreno; geocodifica di riserva | chiamata dal server con la chiave tenuta lì; cache locale |

Dal 17/11/2026 la ricerca di un luogo delle pagine di mappa usa anche la **cartografia catastale dell'Agenzia delle
Entrate** (WFS INSPIRE, CC BY 4.0, senza chiave) per la forma della particella del civico, e le strade di **OpenStreetMap**
(Overpass, ODbL) per la metà di una via: § «Ricerca di un luogo» più sotto.

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

**Colonne facoltative dell'edificio** (04/11/2026, fase 10 § 8): `piani_fuori_terra`, `piani_interrati`,
`superficie_lorda`, `superficie_netta`, `superficie_catastale`, `anno_costruzione`; i nomi alternativi («Piani», «SLP»,
«Sup. netta (m²)», «Anno di costruzione»…) si riportano a questi e passano in uscita come le altre colonne. Nelle pagine
dell'edificio hanno la precedenza sulle visure e sulle stime. I CSV senza queste colonne non cambiano (test).

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
interno; prima di pubblicarlo o condividerlo vanno mantenute le attribuzioni (Zornade con link e fonti originali, per
esempio OSM in ODbL) e non va rivenduto come dato grezzo (termini di Zornade del 18/09/2026, vedi sotto).

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
  OpenStreetMap ODbL).
- **Termini di Zornade del 18/09/2026** (sostituiscono quanto scritto qui prima): uso libero anche commerciale; dati
  mostrabili e conservabili per il tempo che serve al servizio; la ridistribuzione **non è vietata in generale** (vietata
  la rivendita dei dati grezzi senza attribuzione o contro le licenze delle fonti); vietati violazioni del GDPR,
  **re-identificazione di persone** e carichi eccessivi. L'**estrazione massiva** (scraping) è motivo di **sospensione del
  token**, non un divieto di conservare i dati. Limite **10.000 richieste/ora** per token; attribuzione con link nel
  piano gratuito; le attribuzioni delle fonti restano sempre obbligatorie. La **pulizia della cache a 12 mesi** resta
  una scelta di privacy di EuGEnio (informativa), non un obbligo di Zornade. Per questo EuGEnio non scarica in blocco
  lo strato edifici di Zornade (fase 10).
- **Altezze degli edifici di Zornade** (fase 10, Fase E, 04/11/2026): solo da un estratto consegnato da Zornade, mai
  dall'API (il blocco `buildings` dell'API non ha altezze); con gli stessi termini: archivio **ODbL** separato da quello
  CC BY, «© OpenStreetMap contributors (ODbL 1.0)» e «Dati elaborati da Zornade» con link, condivisione allo stesso modo
  dei database derivati, nessuna re-identificazione. Dettagli in `fase10-edifici3d/README.md`, § «Altezze di Zornade».
- Test (03/11/2026): le prove usano `tests/dati/patrimonio_prova.csv` (3 edifici: indirizzo, foglio e particella, sole
  coordinate), non il file d'esempio del sito, che è cambiato il 27/10/2026.
- **I dati catastali non sostituiscono visure ed estratti ufficiali** dell'Agenzia delle Entrate: particelle, fogli e
  superfici servono a localizzare gli edifici. Vietato usarli, da soli o incrociati con altri dati, per
  **re-identificare persone** (proprietari, intestatari, occupanti).
- ANNCSU, quando un punto viene da lì: "ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0)".

Il GeoJSON porta `attribution_html` e l'elenco `sources`; le risposte dell'API `fonte_url` e `fonti`.

## Immobili delle Pubbliche Amministrazioni (MEF + catasto AdE)

Dal 17/11/2026. Il MEF (Dipartimento dell'Economia, progetto «Patrimonio della PA», art. 2 c. 222 L. 191/2009)
pubblica ogni anno l'elenco dei beni immobili dichiarati dalle Amministrazioni; l'**ultimo anno pubblicato è il 2023**
(dati al 31/12/2023, rilevazione aprile-dicembre 2024), licenza **CC BY 4.0**:
https://www.de.mef.gov.it/it/attivita_istituzionali/patrimonio_pubblico/censimento_immobili_pubblici/open_data_immobili/dati_immobili_2023.html

Il MEF **non pubblica poligoni**: dà un punto (per il 94 % dei beni accatastati è il centroide della particella fornito
dall'Agenzia delle Entrate) e l'identificativo catastale. I confini si ottengono agganciando l'identificativo alle
particelle del **download massivo della cartografia catastale** dell'Agenzia delle Entrate (CC BY 4.0, 19 ZIP regionali,
14,7 GB, versione del 22-23/09/2026): https://wfs-download.cartografia.agenziaentrate.eu/wfsdownload/UMBRIA.zip (e così
per le altre regioni; Valle d'Aosta = `VALLE-AOSTA`).

```bash
cd fase7-territorio
python -m territorio immobili-pa --dest /srv/energia/dati/immobili_pa            # tutto: ~40 minuti; su disco al massimo uno ZIP regionale (Lombardia ~2,5 GB)
python -m territorio immobili-pa --dest $D --regioni-ade UMBRIA                     # una sola regione, per provare
```

Ogni ZIP regionale si scarica, si legge e si cancella; restano in `--dest`:

| File | Contenuto | Peso (2023) |
|---|---|---|
| `mef_immobili_pa_2023.parquet` | le 3.257.044 righe MEF con i nomi brevi delle colonne (`natura`, `amministrazione`, `tipologia`, `id_catastale`, `lat`, `lon`…) | 77 MB |
| `poligoni/<REGIONE>.parquet` | particelle AdE agganciate (`chiave`, `ref_ade`, `aggancio`, WKB) | 430 MB |
| `immobili_pa_2023_beni.parquet` | GeoParquet di punti: tutte le colonne MEF + `particella_chiave` e `con_poligono` | 113 MB |
| `immobili_pa_2023_particelle.parquet` | GeoParquet di poligoni: una riga per particella con `n_beni`, `n_fabbricati`, `n_terreni`, amministrazioni, tipologie, `area_m2`, `aggancio` | 440 MB |

**Aggancio** (17/11/2026, quattro regole automatiche, in ordine; colonna `aggancio`):
1. `esatto`: comune, sezione, foglio e particella coincidono. Il riferimento AdE è posizionale: `A045_000100.1` =
   comune `A045`, sezione assente (`_`), foglio `0001`, allegato `0`, sviluppo `0`, particella `1`; con la sezione il
   trattino non c'è (`F363A001300.100`). Nel MEF i terreni sono `comune:sezione:foglio:particella:…`, i fabbricati
   `comune:sezione:sez.urbana:foglio:particella:…`; le unità graffate hanno più identificativi separati da `;`; i codici
   comune troncati (`205` per `F205`) si completano con il comune del bene;
2. `senza_sezione`: il MEF non scrive la sezione che l'AdE indica (Roma, Milano…) e con quel foglio e numero c'è una sola
   sezione;
3. `sezione_dal_punto`: le sezioni sono più d'una (molti comuni lombardi nati da fusioni di comuni censuari) e si sceglie
   la particella che contiene il punto del MEF;
4. `punto`: l'identificativo non c'è nella mappa (particella soppressa o rinumerata dopo la dichiarazione, sezione urbana
   del catasto fabbricati diversa da quella della mappa, identificativo scritto male) e si prende la particella che
   contiene il punto del MEF. Solo con un punto affidabile: centroide fornito dall'Agenzia (`IDENTIFICATIVI_CATASTALI`)
   o posizione messa dall'utente (`UTENTE`); mai con il punto da indirizzo.

Le particelle si raggruppano per riferimento AdE (`ref_ade`): più chiavi MEF che portano alla stessa particella danno un
solo poligono. Nei beni la colonna `ref_ade` dice la particella agganciata (vuota se nessuna).

**Attenzione nell'uso**:
- il poligono è la **particella**: per un fabbricato è il lotto dell'edificio, non la sagoma; più unità immobiliari
  (appartamenti, box…) della stessa particella condividono lo stesso poligono;
- il **Trentino-Alto Adige** non c'è (catasto tavolare delle Province autonome, fuori dal download AdE); in Friuli
  Venezia Giulia e in alcuni comuni del Veneto e della Lombardia il tavolare abbassa la copertura;
- le superfici del MEF sono dichiarate dalle Amministrazioni; l'`area_m2` è calcolata sul poligono AdE;
- i dati non sostituiscono visure ed estratti ufficiali.

**Prodotti per il sito** (Territorio › Edifici pubblici e retino in Modelli 3D):

```bash
sudo apt install tippecanoe                         # una volta (2.17 o successivo: scrive i PMTiles)
python -m territorio immobili-pa-sito --dest /srv/energia/dati/immobili_pa \
    --tessere /srv/energia/dati/edifici/immobili_pa --indice /srv/energia/dati/immobili_pa
```
- tessere in **due passate** di tippecanoe (`-r1`: nessuna feature scartata «per frequenza»; particelle dallo zoom 13,
  punti dallo zoom 4 sfoltiti solo se una tessera supera 1 MB) unite con `tile-join`: lo zoom minimo per feature sui
  poligoni, con tippecanoe 2.49, lasciava una sola particella per tessera (prova del 17/11/2026, test che lo controlla);
- `immobili_pa_2023_<AAAAMMGGhhmm>.pmtiles` e `indice.json` nella cartella degli archivi edifici (servita da Caddy in
  `/edifici3d/immobili_pa/`): strato `particelle` (dallo zoom 13) e strato `punti` (un punto per particella fino allo
  zoom 12, più i beni con un punto affidabile ma senza particella). Proprietà corte: `r` riferimento, `t` tipo (E, T, M),
  `n` beni, `g` gruppo di enti (`GRUPPI_ENTI` in `immobili_pa_sito.py`), `a` primo ente, `tp` tipologie, `s` = 1 per i
  punti senza particella;
- `immobili_pa_2023.sqlite` per l'API (`/api/immobili-pa/…`, fase 4): beni con ricerca a parole (FTS5) e particelle con
  centro e riquadro. **Senza** soggetto cedente e suo codice fiscale (per gli immobili in affitto possono essere persone
  fisiche) e senza il codice fiscale dell'ente.

**Gruppi di enti** (`g` nelle tessere, colonna `gruppo` dell'indice, caselle «Enti» della pagina, filtro della ricerca):
C Comuni, I Unioni di Comuni e Comunità montane, P Province e Città metropolitane, R Regioni, S Sanità, U Università,
E Edilizia residenziale pubblica, M Stato (Ministeri e PCM, Organi costituzionali, Agenzie fiscali), N Previdenza, A altri
enti. Le tipologie si confrontano **senza accenti, apostrofi, maiuscole e spazi doppi**: nei CSV MEF sono scritte con
l'apostrofo (`Universita'`, `Citta' Metropolitane e Province`, `Unioni di Comuni e Comunita' Montane`). Fino al
22/11/2026 il confronto era letterale e P e U restavano vuoti (Province, Università e Unioni in «Altri enti»); le Unioni
hanno dal 22/11 un gruppo proprio (I) invece che stare con i Comuni. Conteggi attesi sui dati 2023 (righe di `beni`):
C 2.182.550, I 73.157, P 64.324, R 215.908, S 43.217, U 12.436, E 458.139, M 53.964, N 28.288, A 125.061.
Controllo sul server: `sqlite3 immobili_pa_2023.sqlite "SELECT gruppo, COUNT(*) FROM beni GROUP BY gruppo"`.

**Rifacimento con il sito acceso** (dal 22/11/2026): l'indice si scrive in `.immobili_pa_2023.sqlite.nuovo` e si
sostituisce con `os.replace` (l'API lo apre con `immutable=1`, una connessione per richiesta: le richieste nuove leggono
subito il file nuovo, non serve riavviare); il PMTiles ha un **nome nuovo a ogni rifacimento** e `indice.json` (sempre
riconvalidato, `Cache-Control: no-cache` in Caddy) si sostituisce per ultimo, così Cloudflare e i browser non mescolano
tessere vecchie e nuove e **non serve la Purge**. Si tiene il PMTiles precedente (pagine già aperte) e si cancellano i più
vecchi. Spazio in più durante il lavoro: ~4 GB di file di lavoro di tippecanoe (GeoJSON e due PMTiles parziali), il
PMTiles nuovo (~760 MB) accanto al vecchio e l'indice nuovo (2,3 GB) accanto al vecchio fino alla sostituzione: tenere
liberi almeno **8 GB** (`df -h /srv/energia`); a lavoro finito restano in più solo i ~760 MB del PMTiles precedente.

**Attribuzione** (scritta anche nei metadati dei file): «Fonti: MEF – Dipartimento dell'Economia, «Patrimonio della
PA», dati beni immobili al 31/12/2023 (CC BY 4.0); Agenzia delle Entrate, cartografia catastale (CC BY 4.0).
Elaborazione: EuGEnio – eugenio.statocritico.it».

**Elaborazione del 17/11/2026** (sera, con le quattro regole): 3.257.044 beni (1.515.583 fabbricati, 1.741.461 terreni),
3.141.599 con identificativo catastale, **2.990.318 agganciati (95,2 %; 97,8 % senza il Trentino-Alto Adige)** a 1.814.954
particelle. Agganci: esatto 2.520.826, senza sezione 186.019, sezione dal punto 20.323, punto 263.150. Su 20.000 beni per
regola con il centroide AdE, il punto cade dentro la particella o entro 20 m nel 98 % (esatto), 95 % (senza sezione), 99 %
(sezione dal punto) e 96 % (punto) dei casi. Copertura per regione: 99–99,6 % Emilia-Romagna, Valle d'Aosta, Liguria,
Umbria, Marche, Toscana, Abruzzo; 97–99 % Piemonte, Molise, Lazio, Sicilia, Puglia, Basilicata, Veneto, Lombardia,
Sardegna, Friuli Venezia Giulia; Campania 91,6 %, Calabria 90,7 %; Trentino-Alto Adige 0 %. Prima delle regole 2–4
(pomeriggio) l'aggancio era all'84 % e la Lombardia al 64 %. Durata: ~40 minuti in due code parallele su 2 vCPU; prodotti
del sito ~12 minuti (PMTiles ~760 MB, indice SQLite 2,3 GB).

La lettura dei GML è fatta «a flusso» sui byte e costruisce il poligono solo per le particelle del censimento
(~0,06 s per comune contro ~1,2 s con GDAL); servono solo pandas, pyarrow e shapely. Composizione in due passate
con le colonne di testo a dizionario: sul file nazionale sta in ~4 GB di memoria.

### Ricerca di un luogo: particella del civico e metà della via (17/11/2026)

`territorio/luogo.py` serve solo alla **ricerca di una riga** delle pagine di mappa (`POST /api/patrimonio` con `luogo=1`,
fase 4): non cambia la geolocalizzazione dei file del patrimonio. Aggiunge alla riga dove mettere il segnaposto e cosa
inquadrare (campi nel README della fase 4). Nessuna rete nel modulo: riceve le funzioni che chiamano le fonti.
- **Particella del civico**: cartografia catastale dell'**Agenzia delle Entrate, WFS INSPIRE**
  (`https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php`, CC BY 4.0, nessuna chiave; GML 3.2 in EPSG:6706
  con coppie «lat lon»; il riferimento è lo stesso di Zornade, `H294_009900.2330`). GetFeature su un quadrato di 30 m:
  particella che contiene il punto (strade e acque escluse), altrimenti quella di Zornade o la più vicina entro 15 m. Punto
  interno garantito (baricentro se dentro, altrimenti il centro del tratto interno più largo), superficie, riquadro. Civico
  con più accessi ANNCSU entro 600 m (`Indirizzario.accessi`: 2, 2/B … 2/O) e cercato senza esponente: **la particella più
  grande** fra quelle che contengono gli accessi (decisione di Paolo del 17/11/2026, «scelta B»); un solo accesso o
  esponente scritto: la particella di quell'accesso. Regola in `luogo_regola`. Una sola richiesta al WFS con il riquadro
  degli accessi più 20 m, assegnazione in locale; ripiego per accesso (al più 4 insieme) se il riquadro supera 640 m o il
  WFS lo rifiuta o lo tronca (`particelle_degli_accessi`). Geometria in Python puro (niente shapely).
- **Metà della via**: strade OSM con il nome (query Overpass su `ref:ISTAT` e sulle parole del nome, con accenti; solo strade,
  non sentieri né ciclabili; più le località `place`), confrontate con lo stesso punteggio dell'ANNCSU; tratti uniti in catene,
  metà della catena se è quasi tutta la via, altrimenti il punto che lascia metà della lunghezza da ciascuna parte lungo
  l'asse principale; gruppi a più di 1 km = vie diverse. Senza OSM, i civici ANNCSU (`Indirizzario.vie_simili`) ordinati
  lungo l'asse. Una via ANNCSU e una OSM con lo stesso nome nello stesso posto sono una sola scelta (con il numero dei civici).
  Dal 19/11/2026 i gruppi dei soli civici si fanno con una griglia (lato 1.500 m/√2) invece che confrontando tutte le
  coppie: a Venezia «piazza San Marco» l'odonimo ANNCSU del sestiere ha migliaia di civici e il confronto a coppie (n²)
  teneva ferma la ricerca.
- **Scelte**: una via riconosciuta (punteggio ≥ 0,8) o una nettamente migliore → si va lì, le altre simili sono «altre vie»;
  più vie riconosciute alla pari, o nessuna ma vie simili o una località con quel nome → si fa scegliere. Con il civico
  l'elenco si prepara solo se la via non è stata riconosciuta dall'ANNCSU (punto di Zornade o via interpretata).

Prove dal vivo del 17/11/2026 (ANNCSU del 02/11/2026, WFS dell'Agenzia e Overpass dal vivo; Zornade non chiamato, la chiave
è solo sul server):

| Ricerca | Prima | Dopo |
|---|---|---|
| Rimini, via Settembrini 2 | 44,042903 N 12,589748 E (accesso «2» ANNCSU, all'angolo sud) a zoom 17: l'ospedale (44,0459 N 12,5879 E per OSM, 330 m più a nord; particella foglio 99 n. 1 fino a 44,0489 N) resta fuori da una mappa alta ~500 px | regola `particella_piu_grande_del_civico`: particella **foglio 99 n. 1** (ospedale, 105.819 m²), segnaposto a 44,046563 N 12,587992 E; riquadro 44,044708–44,048895 N × 12,585209–12,590945 E (gli accessi del «2» cadono nelle particelle 2330, 2331, 2545 e, il 2/O, nella n. 1); prima scelta (particella dell'accesso «2») era la 2330, 3.447 m², all'angolo sud |
| Rimini, via Coriano | 44,015966 N 12,595084 E (civico 210/I, numero mediano) a zoom 17 (~800 m di via visibili) | metà della via (OSM, 8,7 km di tratti) 44,017179 N 12,593942 E; riquadro 43,9906–44,0417 N × 12,5758–12,6041 E; «VIA CORCIANO» fra le altre vie simili |
| Perugia, via Sant'Andrea delle Fratte | nessun punto ANNCSU; Zornade (sul server) ~2,5 km più a nord, senza avviso | elenco da scegliere: Sant'Andrea delle Fratte (località, 43,0743 N 12,3382 E), Strada delle Fratte, Strada di Sant'Andrea d'Agliano, Via Sant'Andrea… |

Per via Coriano il civico mediano dell'ANNCSU cade già a ~150 m dalla metà: l'errore che si vedeva era lo zoom fisso 17 (si
vedevano ~800 m di una via di ~6 km in linea d'aria, e gli edifici grandi più a sud-ovest restavano fuori); ora la via si
vede tutta. Tempi: 2–4 s per ricerca senza copia (WFS ~1 s, Overpass 1–3 s); un civico con molti accessi come il 2 di
viale Settembrini 0,8–5,4 s con la richiesta unica sul riquadro (prima versione, una richiesta per accesso: 11,7–14,5 s);
il WFS rifiuta a tratti il riquadro («Richiesta non valida», di solito dopo raffiche di richieste): secondo tentativo,
poi ripiego per accesso (4,8–7,9 s).

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

## Cabine primarie: raccordo e-distribuzione ↔ GSE ↔ OpenStreetMap (17/11/2026)

Modulo `territorio/cabine.py`, comando `python -m territorio cabine-raccordo`. Serve alle pagine «Stato della rete
elettrica» (Statistiche) e «Cabine primarie» (Fotovoltaico) e al servizio notturno della fase 4, che ne riusa le
regole (`classe_comune`, `livello_peggiore`, normalizzazione dei nomi, codici ISTAT).

### Fonti e licenze

| Fonte | Cosa dà | Licenza / condizioni | Dove finisce |
|---|---|---|---|
| e-distribuzione, Aree critiche (`comuniServiti`, una richiesta per provincia) | per ogni comune i trasformatori AT/MT che lo servono: codice e nome della cabina primaria, livello di saturazione mensile | nessuna licenza dichiarata: uso non commerciale, fonte citata, rimozione su richiesta (decisione di Paolo del 17/11/2026) | codici, nomi, livelli nei file pubblici |
| e-distribuzione, `View_ComuniGestitiED2021Is` | comuni ISTAT 2021 serviti (`servitoed` 1/0) | come sopra | elenco dei comuni non concessionari |
| GSE, `AC_Comuni_2025` strato 0 (2.145 aree, 2.143 codici) | poligoni delle aree convenzionali, `COD_AC`, gestore | CC BY-NC-SA 3.0 IT | **solo i codici** e il gestore; i poligoni si scaricano una volta in una cartella di lavoro per il calcolo e **non vanno mai nel repository né sul server** |
| OpenStreetMap (`power=substation`, estratto Italia di openstreetmap.fr) | posizione e nome delle sottostazioni | ODbL 1.0 («© contributori OpenStreetMap, ODbL») | coordinate delle cabine: ogni file che le contiene porta attribuzione e licenza ODbL |
| ISTAT: elenco dei comuni, soppressi, variazioni dal 1991 | codici attuali dei comuni | CC BY 4.0 | codici ISTAT |
| Confini dei comuni del sito (`fase5-sito/sito/dati/mappa`, ISTAT 2026 generalizzati) | unione dei comuni serviti da una cabina | CC BY 4.0 | solo calcolo |

Lo strato 5 del GSE («Aree convenzionali modificate», 245 aree) è un sottoinsieme dello strato 0 con le stesse
geometrie: non serve. Due codici (`AC001E00366`, `AC001E00891`) hanno due poligoni ciascuno: si uniscono.

### Metodo

1. **Sottostazioni OSM**: tutte le `power=substation` (nodi, way, relazioni; centroide delle aree) lette dal PBF in tre
   passate con pyosmium, senza indice di tutti i nodi (~2 minuti, < 1 GB di memoria). Candidate a cabina primaria
   (`candidata_osm`): escluse le ferroviarie, gli utenti AT con gestore dichiarato che non è un distributore, Terna o
   Enel (acciaierie, aziende), `minor_distribution`/`industrial`/`generation` salvo gestore distributore con tensione
   ≥ 40 kV o nome «cabina primaria»/«CP» (ci sono CP così etichettate e CP dentro le stazioni delle centrali Enel:
   Cencenighe, Quero, Canterno), le aree piccole senza attributi (cabine secondarie).
2. **Nomi** (`gettoni`, `punteggio_nome`): maiuscole senza accenti; «S.», «SAN», «SANTA», «SANT'» → S; Z.I./zona
   industriale → ZI; N.E. → nord-est; articoli elisi tolti (D'ADDA = sull'Adda); parole vuote (CP, SE, SC, cabina,
   primaria, e-distribuzione, Enel, kV, tensioni, «TR3», «CS» non iniziale); lettere isolate unite (V. T. → VT);
   troncature (FLUMINIMAGGI = Fluminimaggiore), iniziali (Q.S.ELENA = Quartu Sant'Elena), piccoli errori di battitura;
   nome OSM accorciato (Canosa = CANOSA DI PUGLIA) 0,8; «EBOLI 1» = «Eboli»; sigla di provincia iniziale sciolta col
   capoluogo se è la provincia di un comune servito (ME RIVIERA = Messina Riviera, VI MONTEVIALE). Il nome del comune
   servito vale metà se ci sono altre parole («PADOVA FIERA»). Punteggio = 0,75 × parole e-distribuzione ritrovate +
   0,25 × parole OSM spiegate.
3. **Candidati**: per ogni cabina le sottostazioni dentro l'unione dei comuni serviti più 3 km. Punteggio coppia =
   0,6 nome + 0,15 attributi (gestore e-distribuzione/Enel 1; `distribution` 0,8; Terna o `transmission` 0,15–0,35;
   altro distributore 0,2) + 0,25 vicinanza (1 dentro i comuni, poi cala fino a 0 a 3 km). Per le cabine senza un nome
   ben riconosciuto, seconda ricerca entro 20 km con nome quasi uguale (≥ 0,9) e vicinanza 0 (comuni serviti
   incompleti, come per le cabine torinesi che servono anche comuni di altre province).
4. **Aree GSE e assegnazione globale**: ogni sottostazione cade in un'area GSE. Punteggio cabina ↔ area = 0,7 ×
   migliore coppia nell'area + 0,3 × quota dell'area dentro i comuni serviti (fascia 500 m per i confini
   generalizzati). L'algoritmo ungherese (scipy) dà a ogni area di e-distribuzione al più una cabina. Dopo: le cabine
   rimaste senza sottostazione prendono la migliore libera con nome ≥ 0,75 anche se sta in un'area già assegnata
   (PALAU e PALAU 2) o di un altro gestore; due codici con lo stesso nome a meno di 3 km (LUNI: DY… e DX…) condividono
   la sottostazione. Senza sottostazione, il `COD_AC` è stimato dai comuni serviti e la nota lo dice.
5. **Esito**: `sicuro` se nome ≥ 0,75, sottostazione entro 1,5 km dai comuni serviti, dentro un'area
   e-distribuzione, a più di 100 m dal bordo dell'area, area per almeno metà dentro i comuni serviti e nessuna
   alternativa quasi equivalente (scarto < 0,05) se il nome non è ≥ 0,95. Altrimenti `da_verificare` con la nota.
   `senza_posizione`: nessuna sottostazione OSM riconosciuta. `solo_gse`: aree GSE senza cabina e-distribuzione
   abbinata (altri gestori, Torino, cabine e-distribuzione non presenti in `comuniServiti`), con la sottostazione OSM
   più plausibile che vi ricade (gestore, nome GSE `TXT1/TXT2` quando c'è, superficie).
6. **Criticità dei comuni** (`classe_comune`, regola del contratto, «classificazione di EuGEnio»): L = livello più alto
   tra i trasformatori del comune, q = quota con livello L; L = VERDE nessun riempimento; q > 0,5 colore pieno;
   altrimenti strisce `[precedente, L]` (`["VERDE", "GIALLO"]` si disegna bianco/giallo). Ogni trasformatore conta una
   volta per comune anche se due vecchi comuni ora fusi lo elencano entrambi.
7. **Codici ISTAT** (`codice_attuale`): e-distribuzione usa in parte codici vecchi; si riportano ai codici attuali con
   «(NUOVO=028108)» nella descrizione, poi le tabelle ISTAT (cambi di provincia e comuni confluiti), poi il nome
   (i codici sardi 118xxx non esistono nelle tabelle ISTAT: si riconoscono per nome); tra omonimi decide la provincia
   degli altri comuni della stessa richiesta (SAN TEODORO in Gallura e non in provincia di Messina).

### Secondo passaggio di verifica (`--verifica`, 17/11/2026 sera)

Le righe `da_verificare` e `senza_posizione` si riesaminano con prove indipendenti dal nome (`secondo_passaggio`,
regole in `decidi_verifica`, tutte con test):
- **comuni ↔ area GSE**: quota dell'area dentro i comuni serviti e coerenza F (media armonica con la quota dei comuni
  serviti dentro l'area); per ogni area la cabina più coerente, escluse quelle già collocate con sicurezza altrove;
  area che non tocca i comuni serviti = errore;
- **linee AT OSM** (`power=line/cable` con nome): «A – B» conferma la cabina A se B è una stazione collocata altrove e
  nessun'altra cabina somiglia ad A di più (`parti_linea`, `prova_linee`);
- **località OSM** (`place=*`) omonime entro 1,5 km, escluso il comune che contiene la sottostazione (`prova_luoghi`);
- **documenti**: schede dell'appendice del Piano di Sviluppo e-distribuzione con CP e comune (`schede_piano_sviluppo`,
  testo da `pdftotext -layout`);
- **esclusività e scambi**: per le cabine non confermate, sottostazioni libere in aree e-distribuzione libere con prove
  forti → esito `corretto` (abbinamento cambiato, con la prova nella nota);
- cabine «torinesi»: nome uguale in un'area fatta di comuni serviti da e-distribuzione ma senza dati `comuniServiti`.
Una cabina in un'area GSE di un altro gestore resta `da_verificare` anche con la posizione confermata. Risultato del
17/11: da 1.574 / 114 / 29 (sicuro / da_verificare / senza_posizione) a 1.647 sicuro, 4 corretto, 41 da_verificare, 25
senza_posizione (con la scelta A per le aree di altri gestori: 1.654 / 4 / 34 / 25); nessuna riga già sicura cambiata.

Aree GSE di altri gestori (scelta A di Paolo, 17/11/2026): una cabina e-distribuzione che cade nell'area di un altro
distributore tiene il `COD_AC` di quell'area col suo gestore; è `sicuro` se la posizione è confermata, altrimenti resta
`da_verificare`; nota «area GSE di un altro gestore».

Comuni serviti in parte (decisione di Paolo, 17/11/2026): un comune con trasformatori e-distribuzione nel dato mensile
non è mai «non concessionario» anche se lo strato `View_ComuniGestitiED2021Is` dice `servitoed = 0`. Esce
nell'elenco `serviti_in_parte` di `comuni_non_concessionari.json` (fuori da `comuni`) e in `comuni_criticita.json` con
`servito_in_parte: true` (`separa_serviti_in_parte`). Il 17/11: 550 non concessionari, 35 serviti in parte.

### Eccezioni verificate a mano (`cabine_eccezioni.csv`)

Le verifiche fatte a mano (cartelli sui cancelli, Street View, dataadl, documenti) si scrivono in
`fase7-territorio/cabine_eccezioni.csv`; `cabine-raccordo` lo legge da solo (oppure `--eccezioni FILE`) e lo applica
**per ultimo**, sopra il calcolo e il secondo passaggio. CSV UTF-8, virgola, righe che cominciano con `#` = commenti:

```
cod_cp_ed,osm_id,lat,lon,cod_ac,esito,nota,fonte,data
DW001385043,way/146602758,,,,sicuro,cartello «CP Vaccaro» sul cancello,Street View (Paolo),2026-11-18
DV001381250,,45.4170,11.8890,,corretto,cabina vista su dataadl,dataadl.it (Paolo),2026-11-18
```

- `cod_cp_ed` (obbligatorio): codice e-distribuzione della cabina; una riga per cabina.
- `osm_id`: sottostazione OSM da usare (`way/…`, `node/…`, `relation/…`, anche non tra le candidate); oppure `lat` e
  `lon` (WGS84, gradi decimali) per una posizione non OSM. Vuoti = posizione invariata.
- `cod_ac`: area GSE da imporre; vuoto = area che contiene la nuova posizione (se la posizione cambia), altrimenti
  invariata. Una riga `solo_gse` con lo stesso codice si toglie.
- `esito`: `sicuro`, `corretto`, `da_verificare`, `senza_posizione` (vuoto = invariato).
- `nota`, `fonte`, `data`: finiscono nella nota come «verifica a mano: <nota> (<fonte>, <data>) [prima: …]».
Errori bloccanti: riga senza `cod_cp_ed`, esito non ammesso, solo `lat` o solo `lon`. Avvisi (stampati): codice non
presente nei dati, `osm_id` non trovato, `cod_ac` sconosciuto, sottostazione usata da due cabine. Test in
`tests/test_cabine.py::test_eccezioni`.

### Uso

```bash
# una volta: poligoni GSE nella cartella di lavoro (mai nel repository), tabelle ISTAT, PBF dell'Italia
python -m territorio cabine-raccordo --dati-cp <dati_cp> --osm <italy.osm.pbf> --aree-gse <lavoro>/tmp_gse --scarica-gse \
    --istat <lavoro>/istat --dest <uscite>
# le volte successive, con l'estratto OSM già fatto e i comuni e-distribuzione salvati:
python -m territorio cabine-raccordo --dati-cp <dati_cp> --osm <lavoro>/osm_substation_tutte.json \
    --aree-gse <lavoro>/tmp_gse --istat <lavoro>/istat --comuni-ed <lavoro>/comuni_gestiti.json --dest <uscite>
# con il secondo passaggio: linee e località OSM (dal PBF, oppure JSON {linee, luoghi} già estratto) e appendice PdS
python -m territorio cabine-raccordo … --verifica --linee-luoghi <lavoro>/osm_linee_luoghi.json \
    --documenti <lavoro>/doc/PdS2025_appendice.txt
```
`<dati_cp>` è la cartella prodotta dallo script di raccolta delle Aree critiche (`grezzi/PPP.json` per provincia).
Le tabelle ISTAT si scaricano da https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
(`Elenco-comuni-italiani.csv`, `Elenco-comuni-soppressi.zip`, `Variazioni-amministrative-e-territoriali-dal-1991.zip`,
scompattati). Servono `shapely`, `scipy` e, per leggere il PBF, `osmium` (pyosmium).

Escono in `<uscite>`: `raccordo_cp.csv` (colonne del contratto più `nota` in fondo), `cabine_primarie.geojson` (punti
con livello peggiore e trasformatori per livello), `comuni_criticita.json`, `comuni_non_concessionari.json`,
`osm_sottostazioni.geojson` (le candidate, ODbL). Risultati del 17/11/2026: 1.717 cabine e-distribuzione (manca
Torino, il servizio risponde 500), 1.574 `sicuro`, 114 `da_verificare`, 29 `senza_posizione`, 450 aree `solo_gse` (dopo il secondo passaggio e la scelta A 1.654 / 4 `corretto` / 34 / 25, 446 `solo_gse`);
prove note confermate (PADOVA FIERA `DV001382982` ↔ OSM way/97839983 «Padova San Lazzaro SC» ↔ `AC001E00909`; Padova
Centro → `AC001E00906`, Bassanello → `AC001E00886`, Camin → `AC001E00887`).

## Test

```powershell
python -m pytest tests -q      # nessuna chiamata di rete (Zornade, WFS catastale e Overpass simulati, ZIP ANNCSU
                               # costruito nel test, cabine primarie su una «Padova» finta, immobili delle PA su dati finti)
```
