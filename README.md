# EuGEnio – consumi, meteo e mercati dell'energia

**EuGEnio** (Europa + EGE, l'Esperto in Gestione dell'Energia) è il primo servizio online di
**Stato Critico** (energy management, sanità, IA e altre cose serie):
- `eugenio.statocritico.it` – il servizio, pubblicato tramite Cloudflare Tunnel;
- `notizie.statocritico.it` – la newsletter mensile automatica dei dati;
- `statocritico.substack.com` – la newsletter degli articoli, scritta a mano (resta su Substack);
- `statocritico.it` – il sito di Stato Critico (in costruzione);
- codice su `github.com/statocritico/eugenio`.

È un **servizio open source** di previsione dei consumi energetici con TiRex-2, meteo per comune, dati
climatici per la Legge 10 (con i valori del DPR 412/93 e il clima dal 1940), patrimonio edilizio,
indicatori di spesa energetica degli enti sanitari, dati di mercato per simulazioni interne e convenzioni
regionali; in progetto (dal 03/11/2026) edifici 3D, fotovoltaico con le ombre, visure, analisi di mercato e
cogenerazione. Gira su un server gratuito Oracle Cloud (fase 1). Le cartelle sono numerate per fase; la
numerazione ha un buco (la 2) perché quella fase non fa parte del servizio pubblico.

| Fase | Cartella | Cosa contiene | Dove si esegue |
|---|---|---|---|
| 1 | `fase1-oracle/` | account Oracle, Always Free o PAYG (analisi), quote, budget, istanza ARM, preparazione, backup | console Oracle + server |
| 3 | `fase3-storico/` | storico meteo Open-Meteo per comune, correzione ERA5, **dati climatici per la Legge 10**, verifica comuni/confini | PC o server |
| 4 | `fase4-server/` | docker compose: API + TiRex-2, worker (meteo, mercati, newsletter, ANNCSU, avvisi), **Cloudflare Tunnel**, **newsletter automatica** (listmonk) | server |
| 5 | `fase5-sito/` | sito statico: previsione dei consumi (mappa, CSV, grafico), patrimonio edilizio sul catasto, dati climatici per la Legge 10, metodo, FAQ, informativa privacy | server |
| 6 | `fase6-mercati/` | **MGP/PUN quartorario, PSV (MGP-GAS), IGI, TTF** ogni notte, solo uso interno; **PSV day-ahead ARERA** dal 10/2022; **PFOR,t** ricostruito; **ISTAT (FOI…) ed Eurostat PMI** su richiesta; **convenzioni regionali** (Intercent-ER, CET, …) con **sorveglianza notturna** delle fonti (Intercent-ER, Consip, CET) | server (anche PC) |
| 8 | `fase8-indicatori/` | **indicatori di spesa energetica degli enti SSN** (OpenBDAP, ReportER, ISTAT) per la pagina «Costi energetici Sanità» (menu Statistiche; fino al 05/11/2026 «Indicatori») | server (mensile) |
| 9 | `fase9-clima-storico/` | **clima dal 1940** per tutti i comuni (ERA5/ERA5-Land), indicatori alla UNI 10349 e al DPR 412/93 | cloud o PC, una volta l'anno |
| 7 | `fase7-territorio/` | **patrimonio edilizio diffuso**: geolocalizzazione in blocco con **ANNCSU** (civici ufficiali) e Zornade (catasto); scelta su come usare i confini Gramscii | server o PC |
| 10 | `fase10-edifici3d/` | **edifici 3D** (DBTR, aggregati, OSM), ortofoto, LiDAR, pipeline notturna a tessere, pagina di stato nascosta, ombre, fotovoltaico e analisi energetiche; **Fase A e Fase B in codice dal 04/11/2026** (pacchetto `edifici3d`, PMTiles/COG, pagina 3D su demo sintetica; ortofoto con proxy e copia, facciate, orizzonte lontano, PVGIS, obblighi D.Lgs. 199/2021 e classifica di priorità; **Fase C** dal 04/11/2026 sera: pipeline LiDAR notturna a tessere con TOML per zona, falde per corpo, pagina di stato nascosta con Cloudflare Access, import DXF/IFC; **Fase E** dal 04/11/2026 notte: fonti verificate regione per regione in `fonti/regioni.toml`, ortofoto di Bolzano e Trento, altezze di Zornade nell'archivio ODbL, aggancio facoltativo al modulo privato delle analisi 5 e 7–13; **Importa DXF/IFC** dal 04/11/2026 notte: DXF e IFC letti nel browser in una pagina separata con dxf-parser e web-ifc, stessa logica di `importa-modello`, file pesanti convertiti sul PC; **05/11/2026**: adattatori di Lombardia, FVG e Liguria, zone LiDAR di Bolzano e Trento, copertura delle fonti, Tabella 11, Perez, Patrimonio → Modelli 3D, posa sulla sagoma, corpi dal solo LiDAR, alberi, analisi 7, 9 e 13 nel codice pubblico; **07/11/2026**: DBTR vero dei comuni (GeoPackage o Shapefile, un archivio per comune, regole delle altezze verificate sul LiDAR, cortili), DTM 5 m dai quadranti letti a finestra, primo archivio vero: Rimini; **08/11/2026**: 28 comuni della Romagna, lettori regionali di 13 regioni e province e del Comune di Venezia, archivi di 15 città italiane, cartelle per licenza `cc-by/` e `iodl/`), fonti DSM/LAS RER 2023-24 in attesa | sito + server |
| 11 | `fase11-visure/` | **EuGEnio Visure**: programma a parte (.exe personale e Docker per enti) per le visure catastali e il CSV arricchito; **Fase D in codice dal 04/11/2026**: lettore locale delle visure in PDF (nessuna credenziale, nessun accesso a SISTER, dati personali esclusi), importazione nella pagina Patrimonio solo nel browser, avviatore `EuGEnioVisure.exe` con versioni approvate (impronte SHA-256) e workflow `.github/workflows/visure-windows.yml` con firma SignPath predisposta, immagine Docker; dal 04/11/2026 notte anche la **conversione dei modelli DXF/IFC** pesanti (`EuGEnioVisure.exe modello`, scheda «Modelli DXF/IFC»); scaricamento con `visura-api` non attivo finché l'Agenzia non chiarisce i termini | PC dell'utente o server dell'ente |
| 12 | `fase12-gme-fotovoltaico/` | analisi sui **dati GME quartorari** (FV, BESS, CER, offerte, flessibilità, zone, rischio, costo per POD): **uso interno finché non c'è la licenza GME**; registro della call `DOMANDE_CALL_GME.md` | server |
| 13 | `fase13-cogenerazione/` | **cogenerazione** in autoconsumo, report 13–20 con il budget di dissipazione CAR: **uso interno finché non c'è la licenza GME**; regole CAR dagli atti normativi, niente contenuti GSE; **report 18 Emissioni nel sito dal 05/11/2026** con i fattori ISPRA (`dati_terzi/`), senza dati GME | server + sito |
| — | `documenti/` | documenti di progetto: proposta 3D e visure, riepilogo GME, scaletta della call GME, bozza dell'articolo per Stato Critico sugli edifici 3D (Fase E), valutazione dei dati di Zornade (05/11/2026, per il § 14.2) | — |

## Per gli agenti AI

[`EUGENIO_PER_AGENTI.md`](EUGENIO_PER_AGENTI.md) (dal 06/11/2026) spiega tutte le funzioni di EuGEnio a un agente AI
(Claude, ChatGPT…) che le usa per conto di una persona: pagine e parametri dell'indirizzo, formati dei file, API libere e
protette da Turnstile, limiti, flussi passo passo, cosa non fare, privacy, attribuzioni. La stessa copia è nel sito
(`https://eugenio.statocritico.it/EUGENIO_PER_AGENTI.md`, collegata dalla F.A.Q. `#agenti-ai` e dalla Sitografia `#claude`),
con il rimando breve `https://eugenio.statocritico.it/llms.txt`.

**Da aggiornare dopo ogni modifica** (oltre ai README delle fasi, `DA_FARE.md` e `RIEPILOGO.md`): se cambiano funzioni,
pagine o API, anche `EUGENIO_PER_AGENTI.md` (radice e `fase5-sito/sito/`, identici) e `fase5-sito/sito/llms.txt`, con data e
versione del sito in testa. Il test `fase4-server/tests/test_agenti.py` fallisce se le due copie differiscono, se la versione
non è quella del sito o se le rotte `/api/…` dell'app e quelle citate nel file non coincidono.

## Novità e release

Il registro delle versioni del sito è `fase5-sito/novita.toml` (dal 07/11/2026): `fase5-sito/costruisci_pagine.py` ne fa
la pagina `novita.html` (collegamento «Novità» in alto a destra) e il feed Atom `novita.xml`; la newsletter mensile ne
prende le voci del mese. **A ogni pubblicazione** si aggiunge una voce (data, versione `?v=…`, titolo, righe Nuovo,
Cambiato, Corretto in italiano semplice) insieme ad `AGGIORNAMENTO_<data>.md`, `EUGENIO_PER_AGENTI.md` e `llms.txt`, e dopo
il commit si crea la **release su GitHub** con lo stesso testo (tag `vAAAA.MM.GG`; i tag `visure-…` restano per EuGEnio
Visure). `fase5-sito/tests/test_costruisci_pagine.py` controlla che la prima voce abbia la versione di `index.html`.

## Ordine consigliato

1. Fase 1 (1–2 ore).
2. Fase 3: avviare il download meteo (circa 12 giorni con l'API gratuita per l'Emilia-Romagna).
   Nel frattempo: chiedere le eventuali credenziali (API del GME per la fase 6, chiave Zornade per la
   fase 7) e preparare il dominio su Cloudflare (fase 4).
3. Fasi 4, 5, 6, 7 quando il pacchetto meteo è pronto; fasi 8 e 9 quando servono.
4. Fasi 10–13 (dal 03/11/2026, progetti): 10 e 11 secondo il programma A–E della proposta; 12 e 13 solo dopo la
   licenza scritta del GME.

## Spazio su disco e memoria

Stime per l'Emilia-Romagna (330 comuni); misurate dove indicato.

| Componente | Spazio iniziale | Crescita annua |
|---|---|---|
| Sistema operativo, pacchetti | ~6 GB | — |
| Immagini Docker (API con PyTorch, Caddy, cloudflared, listmonk, PostgreSQL) | ~4 GB | — |
| Pesi di TiRex-2 (misurato) | 0,3 GB | — |
| Meteo sul server (pacchetto fase 3, misurato su 2 comuni) | 0,2 GB | ~0,05 GB |
| Dati di mercato: storico completo (PUN dal 2004, PSV dal 2010) | < 50 MB | ~5 MB |
| Confini e sezioni di censimento, tutta Italia (cache) | 0,73 GB | — |
| Indirizzario ANNCSU, civici georeferenziati di tutta Italia (sostituito ogni mese) | ~0,3 GB | cresce con la georeferenziazione dei Comuni |
| ISTAT, Eurostat, indici importati | < 10 MB | trascurabile |
| Sorveglianza delle convenzioni (copie delle pagine, documenti scaricati) | < 50 MB | ~20 MB |
| Cache Zornade (1.000 edifici) | ~5 MB | — |
| Newsletter (10.000 iscritti, campagne) | < 0,2 GB | piccola |
| **Totale** | **~12–16 GB** | **< 0,5 GB** |
| Istanza Open-Meteo propria (facoltativa, cache) | +20 GB (configurabile) | — |
| Tutta Italia invece della sola ER (meteo sul server) | +4 GB | +1 GB |

Il disco gratuito è 200 GB in tutto: un volume di avvio da **100 GB** basta con ampio margine e lascia
spazio ai backup. Sul PC, l'archivio meteo completo dell'ER occupa ~2 GB (Italia ~50 GB).
Memoria: ~3,5 GB in uso su 12 (API con TiRex-2 1,2 GB misurati, worker, PostgreSQL, listmonk, Caddy, cloudflared).

## Credenziali

Nessuna credenziale è nel repository. Il server le legge dal file `fase4-server/.env`, da creare
copiando `fase4-server/.env.example` (che elenca le variabili, tutte vuote); il file `.env` è escluso
da `.gitignore`.

## Licenze e condizioni dei dati

- Codice: AGPL-3.0 (file `LICENSE`). Dati elaborati e report di EuGEnio: CC BY 4.0, riuso citando
  «Fonte: EuGEnio – eugenio.statocritico.it»; i valori ricavati dagli anni tipo CTI si possono solo citare.
- **Nome e logo** non sono concessi in licenza: i nomi «EuGEnio» e «Stato Critico», il logo, il simbolo e la
  scritta (file in `fase5-sito/sito/logo/` e `fase4-server/servizio/logo_eugenio.png`) restano esclusi dall'AGPL
  e dalla CC BY e servono solo al funzionamento di questo sito. Si possono citare per indicare la provenienza
  («basato su EuGEnio»), ma un mirror o un servizio derivato deve avere nome e logo propri e non deve presentarsi
  come il sito ufficiale né come approvato da Stato Critico. Dettagli: pagina Licenza del sito, sezione «Nome e logo».
- Liberi con attribuzione: Open-Meteo (CC BY 4.0), ISTAT e confini Gramscii (CC BY 4.0), Arpae
  (CC BY 4.0), ANNCSU (Agenzia delle Entrate e ISTAT, CC BY 4.0), Eurostat, Zornade (piano gratuito:
  link "Dati elaborati da Zornade" + fonti; OSM ODbL).
- **Solo uso interno**: GME (licenza personale non commerciale) e TTF/EEX, compreso il PFOR
  ricostruito: servono a simulazioni e analisi, non si pubblicano e non si scaricano dal sito.
  I future trimestrali TTF si leggono dal sito EEX, che li mostra a scopo informativo, solo per
  calcolare il PFOR.
- **Licenza GME per le analisi delle fasi 12 e 13**: serve una licenza scritta; fino ad allora le pagine restano
  segnaposto. Tariffe ARERA in CC BY-SA 4.0, fattori ISPRA in CC BY 4.0 (in una cartella separata con la loro
  licenza, se entrano nel repository); nessun contenuto GSE (CC BY-NC-SA 3.0 IT) e nessun estratto di norme UNI.
- **Norme UNI**: coefficienti e prospetti in un modulo privato fuori dal repository (`fase10-edifici3d/uni_privato/`,
  in `.gitignore`, fuori dallo zip pubblico e, con il `.dockerignore`, dalle immagini Docker; consegnato a parte). Senza
  il modulo le analisi 5 e 7–13 dicono «analisi non disponibile in questa installazione».
- **Fonti delle altre regioni**: licenza, stato e data della verifica di ogni fonte in `fase10-edifici3d/fonti/regioni.toml`;
  si accendono solo quelle con licenza compatibile scritta e provate dal vivo.
- **Zornade** (termini del 18/09/2026): uso libero anche commerciale con attribuzione e link; ridistribuzione non
  vietata in generale (vietata la rivendita dei dati grezzi contro le licenze), vietate la re-identificazione di
  persone e i carichi eccessivi (l'estrazione massiva fa sospendere il token). I dati catastali non sostituiscono
  visure ed estratti ufficiali.
- Modello TiRex-2: Apache 2.0. listmonk: AGPL-3.0.
