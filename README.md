# EuGEnio – consumi, meteo e mercati dell'energia

**EuGEnio** (Europa + EGE, l'Esperto in Gestione dell'Energia) è il primo servizio online di
**Stato Critico** (energy management, sanità, IA e altre cose serie):
- `eugenio.statocritico.it` – il servizio, pubblicato tramite Cloudflare Tunnel;
- `notizie.statocritico.it` – la newsletter mensile automatica dei dati;
- `statocritico.substack.com` – la newsletter degli articoli, scritta a mano (resta su Substack);
- `statocritico.it` – landing page da preparare (vedi `DA_FARE.md`);
- codice su `github.com/statocritico/eugenio`.

Due cose distinte nello stesso progetto:

1. **Daemon gradi giorno** (uso personale, contratto) – fase 2.
2. **Servizio open source** di previsione dei consumi energetici con TiRex-2, meteo per comune, dati di
   mercato per simulazioni, convenzioni regionali, patrimonio edilizio e dati per la Legge 10 – fasi 3–7.

Tutto gira sullo stesso server gratuito Oracle Cloud (fase 1).

| Fase | Cartella | Cosa contiene | Dove si esegue |
|---|---|---|---|
| 1 | `fase1-oracle/` | account Oracle, Always Free o PAYG (analisi), quote, budget, istanza ARM, preparazione, backup | console Oracle + server |
| 2 | `fase2-gradi-giorno/` | daemon mensile gradi giorno Arpae → file Excel predefinito + email; consolidato su richiesta | server |
| 3 | `fase3-storico/` | storico meteo Open-Meteo per comune, correzione ERA5, **dati climatici per la Legge 10**, verifica comuni/confini | PC o server |
| 4 | `fase4-server/` | docker compose: API + TiRex-2, worker (meteo, mercati, newsletter, ANNCSU, avvisi), **Cloudflare Tunnel**, **newsletter automatica** (listmonk) | server |
| 5 | `fase5-sito/` | sito statico: previsione dei consumi (mappa, CSV, grafico), patrimonio edilizio sul catasto, dati climatici per la Legge 10, metodo, FAQ, informativa privacy | server |
| 6 | `fase6-mercati/` | **MGP/PUN quartorario, PSV (MGP-GAS), IGI, TTF** ogni notte, solo uso interno; **PSV day-ahead ARERA** dal 10/2022; **PFOR,t** ricostruito; **ISTAT (FOI…) ed Eurostat PMI** su richiesta; **convenzioni regionali** (Intercent-ER, CET, …) con **sorveglianza notturna** delle fonti (Intercent-ER, Consip, CET) | server (anche PC) |
| 8 | `fase8-indicatori/` | **indicatori di spesa energetica degli enti SSN** (OpenBDAP, ReportER, ISTAT) per la pagina Indicatori | server (mensile) |
| 9 | `fase9-clima-storico/` | **clima dal 1940** per tutti i comuni (ERA5/ERA5-Land), indicatori alla UNI 10349 e al DPR 412/93 | cloud o PC, una volta l'anno |
| 7 | `fase7-territorio/` | **patrimonio edilizio diffuso**: geolocalizzazione in blocco con **ANNCSU** (civici ufficiali) e Zornade (catasto); scelta su come usare i confini Gramscii | server o PC |

## Ordine consigliato

1. Fase 1 (1–2 ore).
2. Fase 2 (30 minuti): il daemon parte subito, indipendente dal resto.
3. Fase 3: avviare il download meteo (circa 12 giorni con l'API gratuita per l'Emilia-Romagna).
   Nel frattempo: richiedere le credenziali API del GME (fase 6) e la chiave Zornade (fase 7),
   spostare il DNS di statocritico.it su Cloudflare (fase 4).
4. Fasi 4, 5, 6, 7 quando il pacchetto meteo è pronto.
5. Cosa resta da fare dopo il lancio: `DA_FARE.md`.

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
| Fase 2: file Arpae grezzi + archivio | 0,3 GB | ~0,3 GB |
| **Totale** | **~12–16 GB** | **< 0,5 GB** |
| Istanza Open-Meteo propria (facoltativa, cache) | +20 GB (configurabile) | — |
| Tutta Italia invece della sola ER (meteo sul server) | +4 GB | +1 GB |

Il disco gratuito è 200 GB in tutto: un volume di avvio da **100 GB** basta con ampio margine e lascia
spazio ai backup. Sul PC, l'archivio meteo completo dell'ER occupa ~2 GB (Italia ~50 GB).
Memoria: ~3,5 GB in uso su 12 (API con TiRex-2 1,2 GB misurati, worker, PostgreSQL, listmonk, Caddy, cloudflared).

## Segreti (mai nel repository)

- password per le app di Gmail → `/opt/gg-arpae/.smtp_password` (fase 2)
- `.env` del server (fase 4): token del tunnel Cloudflare, chiave Zornade, credenziali GME, SMTP di
  OCI Email Delivery, password di listmonk e del suo database
- chiave SSH privata → solo sul PC

## Licenze e condizioni dei dati

- Codice delle fasi 3–7: AGPL-3.0 (file `LICENSE`). Il daemon della fase 2 è di uso personale:
  tenerlo fuori dal repository pubblico.
- Liberi con attribuzione: Open-Meteo (CC BY 4.0), ISTAT e confini Gramscii (CC BY 4.0), Arpae
  (CC BY 4.0), ANNCSU (Agenzia delle Entrate e ISTAT, CC BY 4.0), Eurostat, Zornade (piano gratuito:
  link "Dati elaborati da Zornade" + fonti; OSM ODbL).
- **Solo uso interno**: GME (licenza personale non commerciale) e TTF/EEX, compreso il PFOR
  ricostruito: servono a simulazioni e analisi, non si pubblicano e non si scaricano dal sito.
  I future trimestrali TTF si leggono dal sito EEX, che li mostra a scopo informativo, solo per
  calcolare il PFOR.
- Modello TiRex-2: Apache 2.0. listmonk: AGPL-3.0.
