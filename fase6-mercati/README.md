# Fase 6 – Dati di mercato, indicatori economici, convenzioni regionali

## Cosa raccoglie

| Dato | Fonte | Dettaglio | Quando | Accesso |
|---|---|---|---|---|
| **PUN** e **prezzi zonali MGP** | GME, API ufficiale | **orari dal 1/4/2004** (avvio della borsa), **quartorari dal 1/10/2025** (PUN Index GME) | ogni notte | credenziali personali gratuite |
| Volumi MGP per zona | GME | idem | ogni notte | idem |
| **MGP: liquidità, transiti, fabbisogno** | GME (`ME_Liquidity`, `ME_Transits`, `ME_Demand`) | orari dal 2004, quartorari dal 1/10/2025 | ogni notte, lavoro `mercato-mgp` (04:15) | idem |
| **MGP: curve aggregate di domanda e offerta** e offerta/domanda totali per zona | GME (`ME_DemandAndSupply`, i file «MGP_DomandaOfferta») | per zona, periodo e livello di prezzo, dal 1/10/2025 (configurabile) | idem | idem |
| **MGP: offerte pubbliche** (tutte, accettate e no) | GME (`Offers_PublicDomain`, XML) | una riga per offerta, pubblicate dopo 7 giorni, dal 1/10/2025 (configurabile) | idem, storico 3 giorni a notte | idem |
| **PSV** dal mercato a pronti del gas MGP-GAS: negoziazione continua (prezzo medio ponderato) e asta | GME | giornaliero, **dall'avvio del mercato** (dicembre 2010) | ogni notte | idem |
| **IGI** – Italian Gas Index | GME | giornaliero, dalla prima pubblicazione (2023) | ogni notte | idem |
| **TTF** Neutral Gas Price | EEX, file pubblico ultimi 60 giorni | giornaliero | ogni notte (si accumula) | libero, uso interno |
| **Future trimestrali TTF** (solo per il PFOR) | sito EEX, Market Data Hub ("for information purposes only") | prezzo di regolamento giornaliero, prossimi 4 trimestri | ogni notte (si accumula) | lettura a scopo informativo, mai mostrati |
| **FOI**, NIC energia, prezzi alla produzione D35 | ISTAT, SDMX | mensile / annuale | **su richiesta** | libero, max 5 richieste/minuto |
| Prezzi elettricità e gas per **PMI** (fasce IB, IC, I2, I3 …) | Eurostat (dati ISTAT/ARERA) | semestrale | **su richiesta** | libero |
| **PSV day-ahead mensile** ufficiale (ARERA CMEM,m, indice `PSV_DA`) | ARERA, pagina pubblica | mensile, **da ottobre 2022**: dal 2024 dalla pagina della vulnerabilità, 10/2022–12/2023 dal file `mercati_energia/dati/psv_da_arera_2022_2023.csv` | ogni notte (nuovo valore nei primi 2 giorni lavorativi del mese) | libero |
| Altri indici (valori di fattura, `PFOR_ARERA`…) | importazione CSV | mensile | quando servono | — |

**Storico completo, recuperato da solo.** Ogni notte, oltre ai giorni recenti, il programma va
all'indietro nel tempo per al massimo un'ora (`max_minuti_storico`), finché arriva all'inizio di
ciascuna serie: PUN e prezzi zonali dal 1° aprile 2004, PSV dall'avvio dell'MGP-GAS, IGI dalla prima
pubblicazione. Le date di inizio non vanno indovinate: quando il GME smette di restituire dati per sei
blocchi di fila, la serie si considera iniziata lì (`storico.json` registra fin dove è arrivato).

**Limiti dell'API GME** (letti con `quote-gme` il 28/10/2026; la guida tecnica non li pubblica): 5 connessioni
contemporanee, **10 al minuto, 100 all'ora**, 2,25 MB di dati al minuto, 350 MB all'ora. Ogni chiamata è una
connessione, comprese `Auth`, `GetMyQuotas` e le richieste respinte con 429. La finestra oraria parte dalla prima
connessione (`lastModifiedHour`): superate le 100, il GME risponde 429 fino alla sua scadenza e ogni tentativo in più
conta. Per questo il client (`gme.ClientGME`) legge le quote **una sola volta** all'avvio, conta in locale ogni
chiamata e **aspetta prima** di superare 8 connessioni al minuto e 90 all'ora (margini in `MARGINE_CONNESSIONI`);
se le quote dicono che la finestra in corso è già piena, aspetta che scada. Dopo un 429 aspetta 65 s, poi
15 minuti a tentativo (o quanto dice `Retry-After`), al massimo 6 tentativi. Primo uso, 28/10/2026: la versione
precedente leggeva le quote prima di ogni richiesta (due connessioni a richiesta) e riprovava ogni 65 s, quindi
ha esaurito le 100 connessioni orarie e ha continuato a ricevere 429. Con ~90 richieste all'ora e un'ora a notte
(`max_minuti_storico`), lo storico completo (~800 blocchi) richiede circa **9–10 notti**; `stato` mostra il primo giorno
disponibile di ogni serie. Da verificare alla prima esecuzione: che lo storico precedente al 2025 del
PUN sia restituito con la zona `PUN` come quello attuale (la guida tecnica descrive solo il PUN Index).

Indici mensili calcolati ogni notte (quelli delle formule contrattuali): `PUN_MENSILE`, `PUN_F1`,
`PUN_F2`, `PUN_F3`, `PUN_F23`, `PZ_<zona>`, `PSV_GME_MENSILE` (continua, o asta dove manca),
`PSV_MGPGAS_CONT_MENSILE`, `PSV_MGPGAS_MENSILE`, `IGI_MENSILE`, `TTF_MENSILE`,
`PFOR`, `PFOR_GJ`, `PFOR_SMC`, più
quelli importati. Le fasce F1/F2/F3 seguono la definizione ARERA con i festivi nazionali; il 4 ottobre
(San Francesco) è incluso dal 2026.

## Mercato del giorno prima: offerte pubbliche, curve e serie aggiuntive (lavoro `mercato-mgp`, 20/11/2026)

> **SOLO USO INTERNO, regola vincolante.** Offerte, curve, liquidità, transiti e fabbisogno del GME restano nell'archivio
> sul server (`/dati/mercati`, cartella `DATI` non servita dal sito): **mai sul sito, mai esportati, mai nella newsletter o
> in file pubblici**, nessuna rotta API, niente in `fase5-sito`, finché non c'è una **licenza scritta del GME**. Il
> repository non contiene dati veri: le prove usano solo dati inventati. La funzione delle curve ordinate restituisce i
> dati a chi la chiama (analisi interne) e non li mostra da nessuna parte; il comando `mgp-stato` stampa solo date e spazio.

Prezzi (PUN Index GME e zonali) e quantità acquistate e vendute per zona c'erano già (lavoro `mercati`, dataset
`mgp_prezzi` e `mgp_volumi`). Il lavoro nuovo `mercato-mgp` (`mercati_energia/mgp.py`, `mgp_notturno.py`) aggiunge:

| Dataset (in `/dati/mercati/`) | Dato del GME (API, comparto MGP) | Righe e colonne | File |
|---|---|---|---|
| `mgp_liquidita/` | `ME_Liquidity` | per periodo: `liquidita` (%), `volumi_borsa`, `volumi_fuori_borsa` | un Parquet per anno |
| `mgp_transiti/` | `ME_Transits` | per periodo e coppia di zone: `da`, `a`, `transito`, `note` | un Parquet per anno |
| `mgp_fabbisogno/` | `ME_Demand` | per periodo e zona: `zona`, `fabbisogno` | un Parquet per anno |
| `mgp_domanda_offerta/` | `ME_DemandAndSupply` (= file «MGP_DomandaOfferta») | per periodo, zona, lato e livello di prezzo: `zona`, `tipo` (testo del GME), `scopo` (BID/OFF, quando riconosciuto), `prezzo`, `quantita`, `quantita_accettata`, `prezzo_zonale`, `note` | un Parquet per giorno, `AAAA/AAAA-MM-GG.parquet` |
| `mgp_offerta_domanda_totali/` | somma delle curve aggregate | per periodo, zona e lato: offerta e domanda totali (`quantita`) e accettate (`quantita_accettata`) | un Parquet per anno |
| `mgp_offerte/` | `Offers_PublicDomain` (`.xml.zip`) | **una riga per offerta**, campi del GME con i loro nomi: `PURPOSE_CD` (BID acquisto / OFF vendita), `STATUS_CD` (ACC, REJ, PREJ, INC, REP, REV, SUB), `TYPE_CD`, `MARKET_CD`, `UNIT_REFERENCE_NO`, `ZONE_CD`, `GRID_SUPPLY_POINT_NO`, `OPERATORE`, `BID_OFFER_DATE_DT`, `TRANSACTION_REFERENCE_NO`, `QUANTITY_NO`, `ENERGY_PRICE_NO`, `AWARDED_QUANTITY_NO`, `AWARDED_PRICE_NO`, `ADJ_QUANTITY_NO`, `ADJ_ENERGY_PRICE_NO`, `MERIT_ORDER_NO`, `PARTIAL_QTY_ACCEPTED_IN`, `BILATERAL_IN`, `SUBMITTED_DT`; dal 1/10/2025 anche `OFFER_TYPE` (S semplice, B a blocchi), `BLOCK_ID`, `PERIOD` (1–96, fino a 100), `GRANULARITY` (PT15, PT30, PT60), `MINIMUM_ACCEPTANCE_RATIO`; prima `INTERVAL_NO` (ora 1–25). Campi nuovi del GME restano, come testo. In più: `data`, `periodo` (PERIOD o INTERVAL_NO), `minuti` (da GRANULARITY; 60 nei file orari) | un Parquet per giorno, `AAAA/AAAA-MM-GG.parquet` |

Tutte le serie hanno `data`, `ora`, `periodo`, `minuti` (15 dal 1/10/2025, 60 prima) e `inizio_utc`, contati dalla
mezzanotte italiana (giorni di 23 e 25 ore compresi). **Unità**: nei file a 15 minuti il GME esprime le quantità in **MW**
e non più in MWh (l'energia di un quarto d'ora è MW × 0,25 h); prima del 1/10/2025 sono MWh orari.

**Curve ordinate.** `mgp.curve(cartella, giorno, periodo, zona=None)` (o `mgp.curve_ordinate(offerte, …)`) ricostruisce
dalle offerte pubbliche la curva di **offerta** (vendite, prezzo crescente, a parità l'ordine di merito) e di **domanda**
(acquisti, prezzo decrescente) di un giorno, un periodo e una zona (`ZONE_CD`, un elenco di zone, o `None` = Italia, cioè
tutte le zone delle offerte): prezzo, quantità, quantità accettata, cumulate, stato, unità, tipo e granularità. Per un
quarto d'ora valgono anche le offerte orarie (PT60) e alla mezz'ora (PT30) che lo contengono. Predefiniti: offerte
accettate e rifiutate (`ACC`, `REJ`, `PREJ`; `stati=None` = tutte, comprese incongrue, sostituite e revocate);
`aggrega=True` somma le offerte allo stesso prezzo (curva a gradini). Nessuna pagina, rotta o file le mostra.

**Ogni notte** (worker, `ORA_MERCATO_MGP` = 04:15, dopo il lavoro `mercati` delle 02:30; al massimo `max_minuti` = 45):
1. liquidità, transiti, fabbisogno: dall'ultimo giorno in archivio meno 7 (rettifiche) a domani, poi lo storico
   all'indietro a blocchi (7 giorni a 15 minuti, 31 orari) fino al 1/4/2004 o a quando il GME smette di rispondere per
   sei blocchi di fila;
2. curve aggregate: i giorni mancanti fino a oggi, poi 7 giorni all'indietro per notte fino a `domanda_offerta_inizio`;
3. offerte pubbliche: i giorni mancanti fino a **oggi − 8** (il GME le pubblica dopo 7 giorni dalla seduta), poi
   **3 giorni all'indietro per notte** fino a `offerte_inizio`, con **20 s di pausa** fra una richiesta e l'altra.
Deduplicazione: le serie annuali si aggiornano per chiave (`inizio_utc`, `minuti` più zona o coppia di zone); i file
giornalieri si riscrivono per intero (file temporaneo e rename) e non hanno righe identiche. Ripresa: `mgp_stato.json`
tiene il punto raggiunto da ogni storico; un giorno che fallisce (rete, quote, XML rotto) si ritenta le notti dopo, al
massimo 3 volte, poi resta fra i `non_scaricati` (visibili con `mgp-stato`). Tutti i file del lavoro stanno nella cartella
dell'archivio: i dataset, `mgp_stato.json`, `mgp_ultima_esecuzione.json`.

**Email all'amministratore, una volta per episodio, solo per**: credenziali GME rifiutate (la password scade ogni 6 mesi;
le stesse del lavoro `mercati`, `GME_UTENTE`/`GME_PASSWORD` nel `.env`), una serie senza dati nuovi da più di
`giorni_ferma` = 4 giorni oltre il ritardo normale, disco con meno di `spazio_minimo_gb` = 8 GB liberi, lavoro fallito 3
notti di fila. Senza credenziali il lavoro non fa nulla e non scrive email.

**Spazio (stima).** Le offerte pubbliche sono il dato grande: con le offerte a 15 minuti si stimano **150 000–500 000
righe al giorno**; in Parquet zstd, con righe ordinate per lato, zona, unità e periodo, 25–45 byte a riga, cioè
**4–20 MB al giorno, ~1,5–7 GB all'anno** (prova su dati inventati della stessa forma: 400 000 righe = 18 MB, il caso
peggiore perché i dati veri si comprimono meglio). Le curve aggregate ~0,3–1 GB all'anno, le serie piccole pochi MB.
Sul server (~24 GB liberi su 96) l'impostazione predefinita, storico dal **1/10/2025**, occupa ~2–8 GB. Per andare più
indietro (`offerte_inizio`; quanto storico dia l'API è da verificare) controllare prima lo spazio con `mgp-stato`: lo
storico delle offerte si ferma comunque da solo oltre `offerte_max_gb` = 12 GB o sotto gli 8 GB liberi (i giorni nuovi
continuano). La prima notte vera dirà la dimensione effettiva di un giorno (`mgp-stato`).

**Limiti dell'API.** Il GME conta i dati come oggetti × campi; il limite al minuto (2,25 milioni) è inferiore a un giorno
di offerte a 15 minuti (~5–10 milioni di campi), quindi **non è verificato che una richiesta di un giorno passi**: se il
GME la respinge per le quote, il giorno finisce fra i falliti (`QuotaGME`) e dopo 3 notti fra i `non_scaricati`. In quel
caso l'alternativa è il server **FTPS del GME** (`ftps://download.ipex.it`, cartella `MGP_OffertePubbliche`, credenziali
diverse da quelle dell'API, da chiedere al GME), non ancora implementato.

Configurazione (`[mgp]` del `config.toml`, tutte facoltative): `abilitato`, `max_minuti`, `inizio_serie`,
`giorni_riverifica`, `domanda_offerta`, `domanda_offerta_inizio`, `domanda_offerta_giorni_per_notte`, `offerte`,
`offerte_inizio`, `offerte_giorni_per_notte`, `offerte_ritardo_giorni`, `pausa_s`, `giorni_ferma`, `offerte_max_gb`,
`spazio_minimo_gb` (spiegate in `config.example.toml`).

```bash
python -m mercati_energia mgp            # il lavoro della notte, subito
python -m mercati_energia mgp-stato      # giorni in archivio, spazio, giorni non scaricati, avvisi aperti
# sul server
docker compose run --rm worker python -m servizio.worker mercato-mgp
docker compose run --rm worker python -m mercati_energia -c /dati/mercati/config.toml mgp-stato
```

Da verificare con le credenziali vere (non provato dal vivo il 20/11/2026): che `Offers_PublicDomain` per un giorno
rientri nelle quote; i valori del campo `Type` di `ME_DemandAndSupply` (riconosciuti BID/OFF se contengono parole come
acquisto/vendita, BID/OFF; il testo originale resta in `tipo`); il separatore decimale degli XML delle offerte (gestiti
punto e virgola); il nome dell'elemento di ogni offerta (si riconosce dal campo `PURPOSE_CD`, qualunque sia); la
profondità dello storico disponibile via API.

Fonti: [Servizio API del GME – Guida tecnica (15/10/2025)](https://gme.mercatoelettrico.org/Portals/0/Documents/it-IT/20251015Manuale_tecnico_API.pdf),
§ 5.25–5.55 (ME_Demand, ME_DemandAndSupply, ME_Liquidity, ME_Transits, ME_ZonalPrices, ME_ZonalVolumes,
Offers_PublicDomain); [Modifica al formato XSD dei file pubblicati dal GME (offerte a blocchi e a 15', 1/10/2025)](https://www.mercatoelettrico.org/Portals/0/Documents/it-IT/20251001_DT_FormatoXSD_15min.pdf)
(campi PERIOD, GRANULARITY, OFFER_TYPE, BLOCK_ID, MINIMUM_ACCEPTANCE_RATIO; nuovo formato di MGP_DomandaOfferta; MW al
posto di MWh; server FTPS); [«SpecificheMTS» (10/06/2025)](https://gme.mercatoelettrico.org/Portals/0/Documents/it-IT/20250610_SpecificheMTSV1.pdf), versione precedente dello stesso documento;
legenda delle offerte pubbliche nella pagina
[Esiti › MGP › Download](https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MGP/Download/Download)
(riserbo di 7 giorni, significato dei campi e degli stati).

## Uso dei dati: solo interno

> **Dall'11/11/2026 (decisioni di Paolo)** si pubblicano, nella pagina Statistiche › Indici dei prezzi e nella newsletter,
> solo: i **prezzi dei listini** pubblicati dalle centrali (Intercent-ER energia elettrica e gas, Consip energia
> elettrica), così come pubblicati; il **PSV day-ahead pubblicato da ARERA** (`PSV_DA`, CC BY-SA 4.0); il **PFOR,t
> ricostruito** (elaborazione di EuGEnio: nessun valore TTF o dei future esce). PUN, prezzi zonali, PSV del GME, IGI, TTF
> e future restano interni. Sezione «Listini e indici dei prezzi pubblicabili» qui sotto.

I dati GME (PUN, prezzi zonali, volumi, PSV MGP-GAS, IGI, e dal 20/11/2026 offerte pubbliche, curve, liquidità,
transiti e fabbisogno MGP) e quelli TTF/EEX **non si pubblicano e non si possono
scaricare dal sito** (il PFOR ricostruito sì, dall'11/11/2026): restano sul server e servono
solo a simulazioni e analisi (prezzi delle convenzioni, scenari di costo). Nessuna rotta dell'API li
espone e la newsletter non li riporta. Motivi:
- **GME**: licenza personale, gratuita, non commerciale; vietato pubblicare, trasmettere o
  ridistribuire i dati o estratti senza permesso scritto. Dove si mostrano risultati di analisi
  basate su questi dati, citare "Fonte: Gestore dei Mercati Energetici S.p.A.". In caso di dubbio
  su cosa sia un'elaborazione ammessa, chiedere conferma a SupportoAPI@mercatoelettrico.org.
- **EEX**: file pubblici, ma gli indici hanno condizioni di licenza proprie.
- **Future trimestrali TTF**: il sito EEX li mostra "for information purposes only" e vieta la
  ripubblicazione sistematica senza permesso. EuGEnio li legge a quello scopo, una richiesta per
  trimestre a notte (4 in tutto, con una pausa), e li usa **soltanto per calcolare il PFOR**: non li
  mostra, non li esporta, non li passa ad altri. Il **PSV day-ahead** citato da
  molte convenzioni (es. CET) invece arriva in automatico: è la media mensile che l'ARERA pubblica
  come CMEM,m per la tutela della vulnerabilità (delibera 374/2022), dal 2024 sulla stessa pagina. I mesi da
  ottobre 2022 a dicembre 2023 stanno su una pagina ARERA che non cambia più (servizio di tutela 22/23): i 15
  valori sono copiati nel file `dati/psv_da_arera_2022_2023.csv` (26/10/2026, controllati sulle tre unità
  della pagina) e vanno in archivio ogni notte insieme agli altri, senza importazioni a mano.
ISTAT ed Eurostat sono dati aperti con citazione della fonte.

## Indice PFOR,t (ARERA, discontinuato) ricostruito

Fino al 30/9/2022 l'ARERA calcolava ogni trimestre il **PFOR,t** (TIVG art. 6.2 c): media aritmetica
delle quotazioni forward trimestrali OTC del gas al TTF **per il trimestre t**, rilevate (ICIS-Heren)
nel **secondo mese solare prima del trimestre**, in €/MWh poi convertite in €/GJ (÷ 3,6). Il valore è
unico per il trimestre: i tre mesi hanno lo stesso PFOR. Dal 1/10/2022 (delibera 374/2022) è stato
sostituito dalla media mensile del PSV day-ahead.

Il modulo `pfor.py` lo ricalcola con lo stesso metodo su dati aggiornati, in €/MWh, €/GJ ed €/Smc
(PCS 0,03852 GJ/Smc), come indici `PFOR`, `PFOR_GJ`, `PFOR_SMC` utilizzabili nelle convenzioni:
- **metodo `forward`** (fedele, automatico ogni notte): media dei prezzi di regolamento giornalieri del
  future EEX *Dutch TTF Natural Gas Quarter* (codice `G3BQ`) per il trimestre t, nelle sedute del mese
  di rilevazione. L'ARERA usava le quotazioni OTC di ICIS-Heren (a pagamento); il prodotto è lo stesso,
  cambia solo la piattaforma su cui è quotato. Il sito EEX tiene **solo i contratti ancora quotati e
  circa sei settimane di sedute**: le quotazioni vanno lette ogni notte e accumulate, e i trimestri
  passati non si possono recuperare. Il primo trimestre ricostruito così è il **I/2027** (rilevazione:
  novembre 2026; valore definitivo da inizio dicembre). Verificato dal vivo il 25/10/2026: 4 trimestri,
  32 sedute ciascuno dal 10/9/2026;
- **metodo `stima_spot`** (per i trimestri precedenti): media del TTF giornaliero EEX nel mese di
  rilevazione. Segue il mercato a pronti invece della curva a termine ed è dichiarato come stima nella
  colonna `metodo`;
- `provvisorio` segnala i valori il cui mese di rilevazione non è ancora finito o ha poche sedute.

Altre fonti delle forward (abbonamento EEX DataSource, ICE, fornitore) si possono aggiungere in
`[pfor.sorgente]` del `config.toml`, o importando un CSV (`data;trimestre;prezzo`, es.
`2026-11-03;2027-Q1;31,20`). Verificato sull'esempio ufficiale ARERA: III trimestre 2020, media di
maggio 5,861184 €/MWh → **1,628107 €/GJ**, identico.

```bash
python -m mercati_energia importa-forward ttf_trimestrali.csv
python -m mercati_energia pfor --dal 2022Q4 --al 2027Q1
```
Il trimestre successivo è calcolabile già dalla fine del suo mese di rilevazione (es. il I trimestre
2027 a fine novembre 2026). Per i trimestri fino al III/2022 si possono importare i valori ufficiali
ARERA come indice `PFOR_ARERA` (comando `importa`) e confrontarli con la ricostruzione.

## Installazione

Sul PC (prove) o sul server, Python 3.11+:
```bash
cd fase6-mercati
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp config.example.toml config.toml
```

**Credenziali GME**: modulo su <https://api.mercatoelettrico.org> (per una persona fisica bastano i dati
anagrafici; per un ente serve la dichiarazione dei poteri di firma via PEC). La password provvisoria
va cambiata nel portale prima dell'uso e **scade ogni 6 mesi**: il server avvisa per email quando
l'accesso fallisce. Mettere utente e password in `config.toml` + `.gme_password` (permessi 600) oppure,
sul server, nel `.env` (`GME_UTENTE`, `GME_PASSWORD`).

Sul server la fase 4 lo esegue da sola ogni notte alle 02:30 (container `worker`): copiare
`config.example.toml` in `/srv/energia/dati/mercati/config.toml` e le convenzioni in
`/srv/energia/dati/mercati/convenzioni/`, **compresa la sottocartella `fonti/`** (sorveglianza).

## Comandi

```bash
python -m mercati_energia notturno                 # aggiornamento (la prima volta scarica dal 1/10/2025)
python -m mercati_energia stato                    # ultimo giorno per dataset e spazio occupato
python -m mercati_energia indici --indice PUN_F1   # indici mensili
python -m mercati_energia importa psv_da.csv       # indici mensili da CSV: indice;mese;valore;unita;fonte
python -m mercati_energia quote-gme                # quote residue dell'API GME
python -m mercati_energia mgp                      # mercato del giorno prima: offerte pubbliche, curve, liquidità…
python -m mercati_energia mgp-stato                # giorni in archivio e spazio delle serie MGP

python -m mercati_energia istat cerca FOI          # trova i dataflow (gli id cambiano quando ISTAT ribasa)
python -m mercati_energia istat struttura 169_748  # dimensioni e codici per costruire la chiave
python -m mercati_energia istat scarica foi_annuale --forza
python -m mercati_energia eurostat scarica elettricita_pmi gas_pmi --csv pmi.csv
```

Verifica fatta il 25/10/2026: EEX (TTF, 60 giorni; future trimestrali), ARERA (PSV day-ahead) ed Eurostat rispondono e sono integrati.

**ISTAT, verifica del 28/10/2026** (SDMX di nuovo raggiungibile): FOI e NIC sono passati alla **base 2025** da gennaio
2026 (dataflow FOI mensile `169_748`, FOI medie annue `169_750`, NIC `167_745`; dimensione `ECOICOP_2` al posto di
`E_COICOP_REV_ISTAT`); i prezzi alla produzione (`145_360`) hanno la dimensione `ECON_ACTIVITY_NACE_2007` e dal 2026 solo
la **base 2021** (`DATA_TYPE = IND_PRIC_2021`). Corretto anche il codice del FOI **senza tabacchi**: `00ST` (`00` è con i
tabacchi). **Decisione di Paolo (28/10/2026): serie unica nella base più recente.** Con `base = {tipo, precedente, anno}`
in configurazione, `istat.raccorda` tiene i valori della base nuova e riporta gli altri dividendo per il coefficiente di
raccordo (media dell'anno di base nella base vecchia / 100: FOI 2025 = 121,4 → 1,214); ogni riga ha `raccordato`,
`coefficiente`, `valore_originale` e `base`. Spiegato nella F.A.Q. `#istat-base`. Il comando `istat struttura` ora legge
la DSD (`references=all` sul dataflow risponde 501); l'elenco completo dei dataflow può richiedere oltre 3 minuti.
La cache delle serie ha l'id del dataflow nel nome, quindi cambiando dataflow si riscarica. 5 test in
`tests/test_istat_raccordo.py`. L'API GME è stata provata
dal vivo il 28/10/2026 (autenticazione, `GetMyQuotas`, prime richieste): limiti nella sezione sullo storico.

Sul server il comando va lanciato con la configurazione della cartella dati, per esempio:
`docker compose run --rm worker python -m mercati_energia -c /dati/mercati/config.toml quote-gme`.

## Convenzioni regionali

Ogni convenzione è un file TOML in `convenzioni/`. I modelli vuoti stanno in `convenzioni/modelli/`. Aggiungere
un'altra centrale (Consip, Aria, SCR Piemonte, …) vuol dire aggiungere un file, senza toccare il codice.

Compilate il 26/10/2026 dai documenti pubblici delle centrali (pagine delle convenzioni, capitolati, listini,
determine di aggiudicazione, avvisi TED, comunicazione CET ai soci) e verificate lo stesso giorno; ogni valore ha
la fonte in un commento:

| File | Convenzione | Periodo | Lotti e spread |
|---|---|---|---|
| `intercenter_ee19_2026.toml` | Intercent-ER Energia elettrica 19 (Nova AEG) | 2026 | 1 sanità MT 1,87 €/MWh; 2 BT/MT 3,25 €/MWh (determina 401/2025) |
| `intercenter_ee20_2027.toml` | Intercent-ER Energia elettrica 20 | 2027 | 1 sanità MT 2,44 €/MWh (Nova AEG); 2 BT/MT 3,47 €/MWh (Alperia) |
| `intercenter_gn23_2026_27.toml` | Intercent-ER Gas Naturale 23, lotto 1 (Energy Wave) | 10/2026–9/2027 | 0,0119 €/Smc, PCS 38,10 MJ/Smc |
| `intercenter_gn23_cogen_2027.toml` | Intercent-ER Gas Naturale 23, lotto 2 cogenerazione (Edison) | 2027 | 0,0067 €/Smc (media giornaliera ponderata approssimata con quella mensile) |
| `cet_ee_2026.toml` | CET / Soggetto Aggregatore Toscana, energia elettrica | 2026 | AT-MT 1,180 (NovaAEG); BT 2,470 (NovaAEG); IP 4,250 €/MWh (A2A) |
| `cet_gas_2025_26.toml` | CET / Soggetto Aggregatore Toscana, gas | 10/2025–9/2026 | Centro 0,0168; Nord-Ovest 0,0156; Sud-Est 0,0136 €/Smc |

Note:
- Intercent-ER: le garanzie d'origine e lo sbilanciamento sono compresi nello spread. Le perdite convenzionali
  ARERA (TIS, tabella 4: MT 3,8 %, BT 10,2 %) si applicano allo stesso prezzo dell'energia, e per questo il
  lotto 2 è diviso in `2-BT` e `2-MT`. Il dispacciamento si paga a parte, come sul mercato libero (EE19 verificata
  sul capitolato il 26/10/2026).
- Il gas usa `PSV_DA`, cioè la CMEM,m dell'ARERA. Coincide con l'indice del capitolato GN23 (ICIS Heren PSV Day
  Ahead "mid", tutti i giorni del mese, weekend con la quotazione Weekend): cambia solo l'arrotondamento finale.
- CET energia 2026: spread dalla comunicazione CET ai soci del 29/10/2025 (quelli della slide ANCI erano del 2025).
  Il fornitore non applica corrispettivi fissi o di potenza propri; perdite TIS al prezzo di fornitura come per
  Intercent-ER. Opzione verde a parte: +1,5 €/MWh (lotti 1 e 2), +3,5 €/MWh (lotto 3).
- Ancora senza file:
  - CET gas 2026/27 ed energia 2027: aggiudicati, spread non pubblici;
  - Intercent-ER GN22 (gas 2025/26).

Regole di prezzo dell'energia supportate, per fascia (F0, F1, F2, F3, F23):

| Regola | Formula | Esempio |
|---|---|---|
| `indice_piu_spread` | coefficiente × indice del mese + spread | CET: PUN medio mensile + spread; gas: PSV day-ahead + spread |
| `base_piu_delta_indice` | P0 + k × (indice − indice di riferimento) | vecchie convenzioni indicizzate a Brent/gasolio |
| `fisso` | P0 | prezzo fisso per l'intera durata |
| `prezzi_pubblicati` | dal CSV `mese;fascia;prezzo` della centrale | listini mensili pubblicati |

In più il calcolo considera:
- le perdite di rete applicate all'energia, se la convenzione lo prevede;
- il corrispettivo fisso in €/POD/anno;
- il corrispettivo di potenza in €/kW/mese;
- la conversione da €/MWh a €/Smc con il PCS, per il gas.

```bash
python -m mercati_energia convenzioni elenco
python -m mercati_energia convenzioni prezzi intercenter-ee19-2026 1 --dal 2026-01 --al 2026-09
python -m mercati_energia convenzioni costo intercenter-ee19-2026 2-BT --consumi consumi.csv --pod 3
```
`consumi.csv`: `mese;fascia;quantita` (MWh per l'elettricità, Smc per il gas). Il costo riguarda
energia, perdite e corrispettivi della convenzione: trasporto, oneri di sistema, accise e IVA no.

## Sorveglianza delle fonti (ogni notte)

I valori delle convenzioni non si aggiornano a mano: ogni notte, dopo i mercati, `sorveglianza.py` controlla le
fonti e manda un'email all'amministratore **solo quando cambia qualcosa** rispetto alla notte prima.

| Cosa | Dove si configura | Cosa succede |
|---|---|---|
| Elenchi delle convenzioni e delle gare (Intercent-ER, CET) | `convenzioni/fonti/centrali.toml`, `tipo = "elenco"` | segnala i collegamenti nuovi su energia elettrica e gas: convenzioni da aggiungere |
| Pagine di gare in corso (Consip EE e gas) | `convenzioni/fonti/centrali.toml`, `tipo = "pagina"` | segnala le modifiche e scarica esiti, aggiudicazioni, listini |
| Pagine di ogni convenzione | sezione `[sorveglianza]` del suo TOML, `pagine = [...]` | scarica i documenti nuovi (listini, guide, determine, capitolati) e ne estrae il testo |
| Valori (spread, corrispettivi, perdite) | `[[sorveglianza.valore]]`: `lotto`, `campo`, `cerca` (regex con un gruppo numerico), `fonti`, `applica` | confronta il valore nei documenti con quello del file: se diverso e `applica = true` aggiorna il TOML (copia di sicurezza in `sorveglianza/copie_toml/`, commento con data e valore precedente), altrimenti lo propone |
| PSV day-ahead ARERA | automatico | avviso se dopo il giorno 7 manca ancora il mese precedente |

Regole pratiche:
- le richieste sono condizionate (ETag/Last-Modified), una per pagina a notte, con un User-Agent che dichiara EuGEnio;
- un documento si scarica se il nome del file o il testo del collegamento corrisponde a `documenti` (predefinito:
  listini, prezzi, guide, esiti, aggiudicazioni, capitolati, convenzioni, accordi, condizioni);
- la prima notte crea solo la base di confronto e scarica i documenti presenti, senza email;
- una regola che trova più valori diversi ("ambiguo") o un valore scritto per fascia (`{ F1 = .. }`) non aggiorna
  mai il file da sola: diventa una proposta da controllare;
- un valore mai trovato non si segnala (documento non ancora uscito); uno trovato e poi sparito sì;
- una pagina che non risponde si segnala alla terza notte di fila, poi una volta a settimana;
- i valori aggiornati sul server vanno ricopiati nel repository (l'email lo ricorda).

Prova dal vivo del 26/10/2026: 11 pagine su 11 rispondono (Intercent-ER, Consip, CET); scaricati 7 documenti
(capitolati, schema di convenzione, determina EE19, esiti Consip EE ID 2880, avviso di aggiudicazione Consip gas
ID 2958); i moduli e la modulistica no. Seconda notte: nessuna segnalazione.

Regole oggi attive: EE19 (spread dei tre lotti dalla determina di aggiudicazione, letti dal PDF vero). Per EE20,
GN23 e i lotti CET si aggiungono quando la sorveglianza avrà scaricato il primo listino: il testo estratto sta in
`<archivio>/sorveglianza/documenti/`, da lì si scrive la regex.

```bash
python -m mercati_energia sorveglianza          # controllo subito (lo stesso della notte), stampa le novità
python -m mercati_energia sorveglianza stato    # pagine controllate, ultima modifica, errori, documenti scaricati
```

## Listini e indici dei prezzi pubblicabili (11/11/2026)

`mercati_energia/listini.py` legge ogni notte (passo di `notturno.esegui`) i listini mensili pubblicati dalle centrali e
ne tiene **solo il prezzo** (le colonne del solo PUN o del solo PSV non si leggono), nel dataset `listini` dell'archivio
(chiave convenzione + lotto + fascia + mese; `prezzo` con `unita`, €/MWh o €/Smc; `serie` e `titolo`). `precedenti =
[{ id, titolo, url }]` (nel TOML della convenzione o in `fonti/listini.toml`) aggiunge le convenzioni precedenti con gli
stessi lotti alla stessa serie, per il confronto con l'anno prima. Il **PFOR** della pagina viene prima da
`mercati_energia/dati/pfor_storico.csv` (anno;trimestre;pfor_eur_smc, dal 2015 al IV/2026, valori di Paolo dell'11/11/2026,
convertiti in €/MWh con il PCS 0,03852 GJ/Smc; cartella fuori da git), poi dal calcolo per i trimestri mancanti:

| Fonte | Dove è scritta | Formato |
|---|---|---|
| Intercent-ER, Energia elettrica 19 (2026) e 18 (2025, `precedenti`) | sezione `[listino]` di `convenzioni/intercenter_ee19_2026.toml` | `listini.zip`, un Excel per lotto, fasce F1–F3, €/kWh → €/MWh |
| Intercent-ER, Gas naturale 22 e 21 (`precedenti`, anno termico 2024/25) | `convenzioni/fonti/listini.toml` | come sopra, in €/Smc (4 decimali), usi (termici, non termici, cogenerazione) al posto delle fasce |
| Consip, Energia Elettrica 22 (17 lotti) | `convenzioni/fonti/listini.toml` | «EE22 - Corrispettivi - MMAA.xlsx» da acquistinretepa.it (accesso con cookie, il client li tiene): un foglio per lotto, prezzo variabile per fascia F0–F3 |
| File copiati a mano | `<archivio>/listini_manuali/<id>/` con `listino.toml` facoltativo (`centrale`, `titolo`, `serie`, `formato`) | come sopra |

**Attenzione (Consip)**: l'`id` di `getDocument` cambia ogni mese. Il file contiene tutti i mesi dal novembre 2024,
quindi basta mettere in `listini.toml` l'indirizzo del file del mese nuovo (DA_FARE).

`mercati_energia/prezzi_pubblici.py` (`costruisci`, `scrivi`) prepara il file del sito `/sito/dati/prezzi/indici.json`
(scritto dal worker dopo i mercati di ogni notte, e con `python -m servizio.worker prezzi`): sezioni `elettricita`
(Intercent-ER, Consip) e `gas` (listini Intercent-ER, `PSV_DA`, PFOR ripetuto nei tre mesi del trimestre, con metodo e
«provvisorio»), anno in corso e anno prima. `INDICI_AMMESSI = {"PSV_DA", "PFOR"}`: nessun altro indice mensile. Prove:
`tests/test_prezzi_pubblici.py` (il file non contiene valori del PUN né del TTF).

## Spazio occupato

Misurato su un anno sintetico con 20 zone a 15 minuti: prezzi 1,8 MB, volumi 3,2 MB, quindi
**~5 MB l'anno** da ora in poi. Lo storico orario 2004–2025 pesa circa un quarto per anno (24 valori
al giorno invece di 96): ~30 MB in tutto. Con gas, TTF e indici l'archivio completo resta **sotto i
50 MB**.

## Test

`python -m pytest tests/` (27 test) – fasce ARERA, festivi, cambio dell'ora (giornate di 23/25 ore), PFOR sull'esempio
ARERA, decodifica delle risposte GME, indici mensili, prezzi e costi delle convenzioni, modelli, tabelle ARERA del
PSV day-ahead (anche quella 2022/23, con le colonne in un altro ordine) e storico 10/2022–12/2023; sorveglianza con
un sito simulato su tre notti (nuove gare, documenti nuovi, valore aggiornato, valore proposto, nessun doppione),
pagine che non rispondono, valori per fascia, PSV in ritardo, testo da PDF e ZIP, file veri delle convenzioni.
