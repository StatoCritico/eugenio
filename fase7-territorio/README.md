# Fase 7 – Territorio: comuni, confini, catasto e patrimonio edilizio diffuso

## Fonti e ruoli

| Fonte | Cosa dà | Come la usiamo |
|---|---|---|
| **ISTAT** – elenco dei comuni | codici ISTAT e catastali (Belfiore), province, capoluoghi, variazioni | scaricato al bisogno (aggiornato ogni 30 giorni) |
| **Gramscii** – confini comunali (ISTAT 1/1/2026, CC BY 4.0) e sezioni di censimento 2021 | mappa SVG dei comuni, baricentro degli edifici | **versione bloccata** e verificata (vedi sotto) |
| **ANNCSU** – Archivio Nazionale dei Numeri Civici delle Strade Urbane (Agenzia delle Entrate e ISTAT, CC BY 4.0, mensile) | civici ufficiali con coordinate dell'accesso | **prima fonte per gli indirizzi**: file nazionale scaricato una volta al mese e interrogato in locale (nessuna chiave, nessuna quota) |
| **MEF** – censimento «Patrimonio della PA» (dati al 31/12/2023, CC BY 4.0) e **Agenzia delle Entrate** – download massivo della cartografia catastale (CC BY 4.0) | immobili delle Pubbliche Amministrazioni con la particella catastale disegnata | `immobili-pa`: file nazionali in cache, una volta l'anno (vedi «Immobili delle PA») |
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
- `immobili_pa_2023.pmtiles` e `indice.json` nella cartella degli archivi edifici (servita da Caddy in
  `/edifici3d/immobili_pa/`): strato `particelle` (dallo zoom 13) e strato `punti` (un punto per particella fino allo
  zoom 12, più i beni con un punto affidabile ma senza particella). Proprietà corte: `r` riferimento, `t` tipo (E, T, M),
  `n` beni, `g` gruppo di enti (`GRUPPI_ENTI` in `immobili_pa_sito.py`), `a` primo ente, `tp` tipologie, `s` = 1 per i
  punti senza particella;
- `immobili_pa_2023.sqlite` per l'API (`/api/immobili-pa/…`, fase 4): beni con ricerca a parole (FTS5) e particelle con
  centro e riquadro. **Senza** soggetto cedente e suo codice fiscale (per gli immobili in affitto possono essere persone
  fisiche) e senza il codice fiscale dell'ente.

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
del sito ~12 minuti (PMTiles ~180 MB, indice SQLite 2,3 GB).

La lettura dei GML è fatta «a flusso» sui byte e costruisce il poligono solo per le particelle del censimento
(~0,06 s per comune contro ~1,2 s con GDAL); servono solo pandas, pyarrow e shapely. Composizione in due passate
con le colonne di testo a dizionario: sul file nazionale sta in ~4 GB di memoria.

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
python -m pytest tests -q      # 20 test, nessuna chiamata di rete (Zornade simulato, ZIP ANNCSU costruito nel test)
```
