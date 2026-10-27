# Fase 8 – Indicatori della spesa energetica degli enti del SSN

Raccoglie e calcola i dati della pagina **Indicatori** del sito (`fase5-sito/sito/indicatori.html`): la spesa per
energia e utenze di ogni ente del Servizio Sanitario Nazionale, anno per anno dal 2015 al 2025, accanto al
consolidato della sua regione e all'Italia, con leva, incidenza, peso e spesa per giornata di degenza, per posto
letto e per cittadino. Il risultato sono file JSON statici, che il sito legge da `dati/indicatori/`.

Pacchetto Python `indicatori_ssn`, dipende solo da `httpx`. Codice AGPL come il resto di EuGEnio; nessun segreto,
tutte le fonti sono pubbliche e senza chiavi.

```
python -m indicatori_ssn aggiorna --out <cartella> [--cache cache] [--pausa 2] [--rinnova] [--parziale]
python -m indicatori_ssn verifica --out <cartella> [--anno 2024]
```

`aggiorna` scarica ciò che manca nella cache (una richiesta ogni `--pausa` secondi), calcola e scrive
`<cartella>/indice.json` e un file per regione (`01.json` … `20.json`, codici ISTAT della mappa del sito), poi stampa
le dimensioni e i valori di controllo del 2024. Se una fonte non risponde e la sua copia in cache manca, **i file
del sito non vengono toccati** (codice di uscita 2); `--parziale` li scrive lo stesso con gli anni mancanti vuoti.
`--rinnova` riscarica anche ciò che è già in cache (da usare nell'aggiornamento mensile).

## Fonti

| Dato | Fonte | Come si scarica | Licenza |
|---|---|---|---|
| Voci del conto economico per ente, 2015–2025 | **OpenBDAP**, Ragioneria Generale dello Stato (MEF): «Modello di rilevazione del Conto Economico degli enti del SSN» | API CKAN `datastore/dump/<ID>.csv` (≈ 15 MB per anno, separatore `;`), filtrato mentre si legge; in cache resta `cache/bdap/ce_<anno>.csv` con le sole voci utili (≈ 1.600 righe), il file completo si cancella. `datastore_search` non esiste su questo catalogo (404) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.it), titolare Ragioneria Generale dello Stato (metadati dei dataset su [dati.gov.it](https://www.dati.gov.it/opendata/api/3/action/package_show?id=spd_ssn_cce_elb_voccn_01_2024): `license_type` A21_CCBY40, `rightsHolder` RGS) |
| Giornate di degenza, posti letto, residenti per azienda (Emilia-Romagna) | **ReportER**, SISEPS Regione Emilia-Romagna | `POST …/ReportERHomeService/methods/stats/report/TABLE` con il corpo del portale (vedi sotto) | CC BY 4.0: ReportER non indica una licenza propria e valgono le [note legali della Regione](https://www.regione.emilia-romagna.it/note-legali) («gli altri contenuti, salvo diversamente specificato, sono rilasciati sotto licenza Creative Commons Attribution 4.0») |
| Popolazione al 1° gennaio di Italia, regioni e province autonome | **ISTAT** | ZIP di [demo.istat.it](https://demo.istat.it/): `data/posas/POSAS_<anno>_it_Regioni.zip` e `_Province.zip` (dal 1/1/2020), `data/ricostruzione/PopolazioneEta-Territorio-Regioni.zip` e `-Province.zip` (1/1/2016–2019); di riserva il servizio SDMX | [CC BY 4.0](https://www.istat.it/note-legali/) |

Attribuzioni (in pagina, nei JSON `indice.json → fonti`, nei CSV scaricabili e nei report): «Ragioneria Generale
dello Stato – OpenBDAP», «Regione Emilia-Romagna – ReportER (SISEPS)», «ISTAT», ciascuna con la licenza e il link,
più la nota «Elaborazione di EuGEnio (Stato Critico) sui dati originali: somme, rapporti e abbinamento dei codici»
(la CC BY chiede di indicare le modifiche). Si pubblicano solo le voci usate e i denominatori: nulla che le licenze
non consentano.

### OpenBDAP

Dataset per anno (ID della risorsa CKAN in `costanti.DATASET_CE`): consuntivi 2015–2024, 2025 IV trimestre
(provvisorio). Voci: **BA1610** riscaldamento, **BA1660** utenze elettricità, **BA1670** altre utenze (gas, acqua)
→ numeratore; **BA0340** combustibili, carburanti e lubrificanti → riportata a parte, esclusa (comprende il
carburante degli automezzi); **BA1650** telefonia → esclusa e non pubblicata; **AZ9999** valore della produzione e
**BZ9999** costi della produzione → denominatori. Codici ente: `999` consolidato regionale (unità «regione»),
`000` GSA (esclusa: è la contabilità dei fondi gestiti dalla regione, già compresa nel consolidato).
L'Italia è la somma dei 21 consolidati di regioni e province autonome (`n_regioni` per anno nel JSON: se ne manca
qualcuno l'anno è segnalato in `anni_incompleti_italia`).

Il 27/10/2026, fino alle 11 circa, il catalogo (`bdap-opendata.rgs.mef.gov.it`, comprese le API) rispondeva con
la pagina «non è disponibile per attività di manutenzione straordinaria»: il programma lo riconosce (risposta HTML
al posto del CSV), non insiste e non sovrascrive i file del sito. Licenza letta anche da `package_show`
(`license_id` `cc-by`, autore Ragioneria Generale dello Stato).

**Calabria 2021**: nel CE 2021 manca il consolidato (`999`) della Calabria (c'è solo la GSA e le aziende). Per quel
anno l'Italia è la somma di 20 consolidati e la sua popolazione è quella delle 20 regioni comprese, così i rapporti
restano coerenti; il JSON lo dice in `italia.regioni_mancanti` e la pagina lo scrive sotto il confronto e la tabella.

### ReportER

| Misura | Report | Coordinate | Filtri |
|---|---|---|---|
| giornate di degenza ordinaria | SDO – Giornate (STATS-10-2-1-2) | flusso 10, ambito 2, sottoambito 1, scheda 2 | anno di dimissione; regime `001` (degenza ordinaria); tipo presidio `PUB` |
| accessi in day hospital (solo in nota) | idem | idem | regime `002` |
| posti letto | Posti letto per bilancio annuale (STATS-13-1-1-1) | 13, 1, 1, 1 | data di rilevazione 31/12 dell'anno; tipo presidio `1 ` (strutture pubbliche, con lo spazio); colonna TOTALE |
| residenti | Popolazione (STATS-23-1-1-1) | 23, 1, 1, 1 | anno (31/12); colonna Residenti |

Corpo: `{"macroareaId":1,"flowId":…,"macroScopeId":…,"scopeId":…,"tabId":…,"representationType":"TABLE",
"activeFilterList":[{"id":"<ID filtro>","values":[{"value":"<valore>"}]}],"saved":false}` (gli ID dei filtri
sono in `costanti.py`). Nota: il report delle giornate non ha più il regime come variabile di colonna; si usa il
filtro di regime. La riga TOTALE vale per il consolidato regionale (`999`). Aziende → codice ente:
PIACENZA 101, PARMA 102, REGGIO EMILIA 103, MODENA 104, BOLOGNA 105, IMOLA 106, FERRARA 109, ROMAGNA 114,
AOSPU PARMA 902, AOSP REGGIO EMILIA 903 (fino al 2016), AOSPU MODENA 904, AOSPU BOLOGNA / IRCCS S. ORSOLA 908,
AOSPU FERRARA 909, I.O.R. 960. Un nome nuovo non abbinato finisce nel registro come avviso.

### ISTAT e la discontinuità 2018/2019

La popolazione al 1° gennaio dell'anno T vale per il 31/12 dell'anno T−1. Fino all'anno di riferimento 2018 si
usa la **ricostruzione intercensuaria 2002–2019**, dal 2019 il **censimento permanente** (POSAS); per il 2025 il
dato al 1/1/2026 è una **stima** ISTAT. Tra le due serie c'è un salto (le serie non sono state riallineate):
`indice.json → serie_popolazione` dice per ogni anno quale serie è stata usata, e la pagina lo scrive accanto
al grafico. Bolzano e Trento vengono dai file per provincia (021, 022); l'Italia è la somma delle regioni.

Il servizio SDMX (`esploradati.istat.it`, dataflow `22_289` e `164_164_DF_DCIS_RICPOPRES2011_1`, chiave
`A.<area>.JAN.9.TOTAL.99`) dà gli stessi numeri ma il 27/10/2026 rispondeva solo ai metadati (dati: errore 500
«Error during writing responce» o nessuna risposta dopo 5 minuti), quindi è rimasto come riserva.

Per l'Emilia-Romagna (AUSL e consolidato) si usano i residenti **SISEPS**, come nell'analisi di partenza
(2024: 4.482.977 contro ISTAT 4.461.998, −0,5 %); il valore ISTAT del consolidato resta nel JSON (`pop_istat`).

## Indicatori

Spesa = BA1610 + BA1660 + BA1670 (oppure una sola componente). Leva = AZ9999 / spesa; incidenza = spesa / AZ9999;
peso = spesa / BZ9999; € per giornata = spesa / giornate di degenza ordinaria (ospedali pubblici); € per posto letto =
spesa / posti letto pubblici al 31/12; € per cittadino = spesa / residenti al 31/12. Le formule sono in
`calcolo.py` e, identiche, in `sito/indicatori.js` (i JSON portano i valori grezzi, il sito fa le divisioni). Dove
manca un denominatore il valore è `null` («n.d.» in pagina).

Avvertenze (in pagina, in `metodo.html#indicatori` e nei report): valori monetari (prezzi oltre ai consumi, 2022);
classificazione contabile diversa tra aziende (servizio energia, global service, voci a zero); valore della
produzione legato al riparto regionale; perimetro (sedi territoriali nella spesa, solo ospedali nei denominatori;
la spesa per cittadino della regione comprende AOU e IRCCS); denominatori (degenza ordinaria, posti letto al 31/12,
popolazioni SISEPS e ISTAT diverse); discontinuità (AOSP Reggio Emilia nell'AUSL dal 2017, riorganizzazioni in altre
regioni, popolazione 2018/2019, 2025 provvisorio).

### Valori di controllo 2024 (totale energia e utenze)

| | AUSL della Romagna | Emilia-Romagna (consolidato) | Italia |
|---|---|---|---|
| Spesa | 39.455.736 € | 187.362.060 € | 2.267.333.735 € |
| Leva | 75,8x | 64,5x | 66,2x |
| Incidenza | 1,32 % | 1,55 % | 1,51 % |
| Peso | 1,33 % | 1,56 % | 1,52 % |
| € per giornata di degenza | 45,82 € (861.172 giornate) | 52,01 € (3.602.183) | n.d. |
| € per posto letto | 13.439 € (2.936 posti) | 14.273 € (13.127) | n.d. |
| € per cittadino | 35,09 € (1.124.403 SISEPS) | 41,79 € (4.482.977 SISEPS) | 38,47 € (58.943.464 ISTAT al 1/1/2025) |

`python -m indicatori_ssn verifica --out <cartella>` li ricalcola dai file prodotti. I denominatori tra parentesi
sono stati verificati su ReportER e ISTAT il 27/10/2026; con i CE scaricati lo stesso giorno **tutti i valori
tornano** con l'analisi di partenza.

## File prodotti

- `indice.json`: anni, anni provvisori, voci, componenti, fonti e licenze, serie della popolazione, date di
  aggiornamento di ReportER, elenco delle regioni, unità `italia` e `consolidati` (uno per regione o provincia
  autonoma).
- In `indice.json` e in ogni `RR.json` anche `licenza` (elaborazioni di EuGEnio con licenza CC BY 4.0: riuso,
  anche con modifiche, citando EuGEnio come fonte e mantenendo le fonti originali) e `citazione`
  («Fonte: EuGEnio – eugenio.statocritico.it (dati aggiornati il gg/mm/aaaa)»); testi in `costanti.py`
  (`LICENZA`, `CITAZIONE`, `citazione()`). Le stesse due righe, `Licenza;…` e `Come citare;…`, chiudono i CSV
  scaricati dalla pagina (`indicatori.js`).
- `RR.json`: per ogni ambito della regione (due per il Trentino-Alto Adige: Bolzano 041 e Trento 042) gli enti
  con i valori per anno.

Ogni unità: `{"cod","reg","nome","v":{"BA1610":[…11 anni],"BA1660":…,"BA1670":…,"BA0340":…,"AZ9999":…,"BZ9999":…},
"gg","dh","pl","pop"` (solo se ci sono), `"fonte_pop"` (`siseps`|`istat`), `"nomi"` (solo se il nome è cambiato:
`[[da, a, nome], …]`), `"anni_presenti"`}. Importi in euro con al più due decimali, `null` dove manca il dato.
JSON compatti, senza spazi.

**Dimensioni** (27/10/2026): **270 kB in tutto** per 21 file; `indice.json` 26 kB, il file più grande
`03.json` (Lombardia, 88 enti tra vecchie ASL e nuove ATS/ASST) 55 kB (14 kB con gzip), Emilia-Romagna 17 kB, Valle
d'Aosta 1 kB. Circa 600 byte per ente. La pagina scarica `indice.json` e il file di una regione alla volta.

## Prove

```
cd fase8-indicatori && python -m pytest          # dati piccoli in tests/dati, nessuna richiesta in rete
cd fase5-sito/sito && python3 -m http.server 8765 &
node fase8-indicatori/tests/pagina.js http://localhost:8765 fase8-indicatori/screenshot   # Playwright, chromium
```

`tests/pagina.js` apre `indicatori.html` a 1280 e 390 px (errori JS, scorrimento orizzontale, cambio di regione
dall'elenco e dalla piccola mappa, componenti, screenshot) e controlla in tutte le pagine che la voce «Indicatori»
segua «Dati storici», che i CSS e JS condivisi siano alla versione `?v=20261027g` e che l'indice laterale di
metodo, faq e sitografia ci sia ancora.

## Aggiornamento mensile sul server

I dati cambiano poche volte l'anno (consuntivo CE in primavera, IV trimestre a febbraio, ReportER in
ottobre–novembre, ISTAT a giugno e a marzo), quindi basta **una volta al mese**: il worker della fase 4 lo fa il
**5 di ogni mese dalle 6** (`INDICATORI_GIORNO` nel `.env`), dal 27/10/2026. Come è collegato:

- `fase4-server/api/Dockerfile`: `COPY fase8-indicatori/indicatori_ssn /app/indicatori_ssn` (nessuna dipendenza
  nuova: `httpx` c'è già);
- `docker-compose.yml`, servizio `worker`: `/srv/energia/sito/dati` montata in scrittura su `/sito/dati`; la cache
  resta in `/dati/indicatori_cache` (fuori dal sito);
- `servizio/worker.py`, lavoro `indicatori`: `cli.aggiorna(…, rinnova=True, pausa=2.0)` scrive in
  `dati/.indicatori_nuova/`; se c'è `indice.json` e almeno il 90 % dei file di prima, la cartella prende il posto di
  `dati/indicatori/` (due `rename`), altrimenti restano i file del mese prima.

Se OpenBDAP o un'altra fonte non risponde, `cli.aggiorna` solleva `FonteNonDisponibile`: il worker manda l'email
all'amministratore e i file pubblicati restano quelli del mese prima. Con `rinnova=True` si riscaricano circa
11 + 44 + 16 file (≈ 3 minuti con le pause). Quando esce un nuovo anno (CE 2026) si aggiunge il suo ID in
`costanti.DATASET_CE` e si sposta `PROVVISORI`.

A mano (anche finché il worker è spento, o da cron dell'host):
`cd ~/energia/fase4-server && docker compose run --rm worker python -m servizio.worker indicatori`.
Istruzioni di prima installazione (permessi della cartella, cron provvisorio) nel README della fase 4, sezione
«Lavori periodici sui file del sito».

## Proposte per le prossime versioni

- **Spesa per cittadino delle AUSL fuori dall'Emilia-Romagna**: le ASL coincidono quasi sempre con una o più
  province (o con la regione intera: Marche, Molise, Valle d'Aosta, Bolzano, Trento). Una tabella ASL → province
  (o comuni) a mano, con la popolazione POSAS per provincia già scaricata, darebbe il pro capite per la maggior
  parte d'Italia; per le regioni con ASL sub-provinciali (Lombardia, Lazio, Campania, Piemonte) servirebbe
  l'elenco comuni per ASL del Ministero della Salute.
- **Giornate e posti letto per le altre regioni**: dataset del Ministero della Salute «Dati di struttura e di
  attività dei reparti» (HSP, fino al 2022) su dati.salute.gov.it, da abbinare ai codici ente del CE.
- Indicatori fisici (kWh, Smc) quando ci saranno fonti pubbliche per ente.

## Stato

27/10/2026: prima versione; aggiornamento mensile automatico dal worker (il 5 del mese). Dati 2015–2025 scaricati (CE OpenBDAP, ReportER, ISTAT), JSON scritti in
`fase5-sito/sito/dati/indicatori/`, valori di controllo 2024 verificati, prove Python e Playwright superate.
