# Valutazione: servono i dati di Zornade per gli edifici 3D? (per decidere il § 14.2)

Documento del 05/11/2026, chiesto da Paolo con la decisione del 04/11/2026 (RIEPILOGO, «Risposta a Zornade (§ 14.2 della
proposta): resta aperta; prima si valuta se i dati di Zornade servono davvero»). **Il § 14.2 resta aperto**: questo
documento serve a decidere. Nessuna email è stata mandata a Zornade.

Fonti usate: `documenti/PROPOSTA_3D_EDIFICI_E_VISURE.md` (§§ 2–4, 9, 14.2), termini di Zornade del 18/09/2026 come
allineati nelle fasi 4 e 7 (`fase7-territorio/README.md`, `fase4-server/servizio/protezione.py`), verifica delle fonti per
regione del 04–05/11/2026 (`fase10-edifici3d/fonti/regioni.toml`), lettore delle altezze Zornade
(`fase10-edifici3d/edifici3d/zornade.py`) e lavori del 05/11/2026 (adattatori regionali, corpi dal solo LiDAR).

## 1. Cosa offre Zornade (oggi e annunciato)

| Prodotto | Cosa contiene | Licenza | Come si ottiene | Stato per EuGEnio |
|---|---|---|---|---|
| API catastale (`parcels/locate`, `parcels/search`, `geocode/search`) | particella, foglio, mappale, superficie, comune catastale | dati catastali AdE (CC BY 4.0) elaborati da Zornade, attribuzione «Dati elaborati da Zornade» con link | API gratuita, 10.000 richieste/ora per token | **già in uso** nella fase 7 (Patrimonio), dopo ANNCSU; tetto di sito a 6.000/ora |
| Blocco `buildings` dell'API | conteggi e impronte degli edifici | OSM, **ODbL 1.0** | API (ma lo scaricamento massivo fa sospendere il token) | non usato: niente altezze; in ER non serve |
| Strato edifici (estratto) | 16,3 milioni di sagome **tutte da OSM**; altezze nel 10,1 % in ER e nel 10,3 % in Italia (5,4 m di media) | ODbL 1.0 | estratto consegnato (offerto per l'ER) | non serve dove c'è un DB topografico; le altezze sono poche |
| **Altezze LiDAR** (annunciate «da novembre») | altezza per edificio dal LiDAR del MASE (PNRR), su sagome OSM | ODbL 1.0 (sagome OSM; per le altezze da confermare) | estratto consegnato (non via API) | **non ancora uscite**; lettore pronto (`zornade.py`), provato su un campione sintetico |
| `visura-api` | servizio REST per le visure su SISTER | AGPL | codice su GitHub | previsto in fase 11, **non attivo** finché l'Agenzia non chiarisce i termini |

Costi: API catastale gratuita con attribuzione; i piani a pagamento e il costo di un eventuale estratto delle altezze
**non sono documentati** nei file del progetto e non sono stati chiesti.

## 2. Cosa abbiamo senza Zornade (dopo il 05/11/2026)

| Dato | Fonte aperta | Copertura | Licenza |
|---|---|---|---|
| Sagome con altezza per corpo | DBTR UVL (ER), DBGT 020101 (Lombardia), CTRN (FVG), CTR 3D (Liguria), Edifici P.A.T. 3D (Trento) | 6 territori; adattatori pronti per ER, Lombardia, FVG, Liguria (05/11/2026); Trento da scrivere | CC BY 4.0 |
| Sagome senza altezza | Edifici del Veneto (IODL 2.0), aggregati della Protezione Civile (nazionali, senza altezze) | Veneto; tutta Italia | IODL 2.0, CC BY |
| Altezze e falde dal LiDAR | DTM RER 0,5 m (attivo), DSM costa 2019 (attivo dove copre), DSM/LAS RER 2023-24 (su richiesta), DSM/DTM Bolzano 0,5 m (CC0, attivi), DSM/DTM Trento 1 m 2006-09 (attivi), LiDAR PNRR del MASE (in arrivo, licenza da verificare dopo il 7/11) | ER, Alto Adige, Trentino; PNRR per tutta Italia | CC BY 4.0, CC0; PNRR da verificare |
| Corpi dal solo LiDAR | raggruppamento per altezza (§ 7, `lidar-corpi`, 05/11/2026) | dove c'è un DSM aperto | quella del DSM |
| Sagome di ripiego | OpenStreetMap (Geofabrik) | ~54 % degli edifici italiani, molto variabile | ODbL (archivio separato) |
| Altezza di quartiere | GHSL GHS-BUILT-H (100 m) | Italia | CC BY 4.0 |

Regioni **senza** sagome con altezza aperte né DSM aperto (verifica del 04/11/2026, molte voci «in attesa» per portali
irraggiungibili dal container): Piemonte, Valle d'Aosta, Toscana (edifici), Umbria, Marche, Lazio, Abruzzo, Molise,
Campania, Puglia, Basilicata, Calabria, Sicilia, Sardegna; Veneto ha le sagome ma non le altezze.

## 3. Analisi per analisi: cosa aggiungerebbe Zornade

| # | Analisi (menu) | Dati che servono | In ER e nei 5 territori con DB e/o LiDAR | Altrove oggi | Con le altezze LiDAR di Zornade |
|---|---|---|---|---|---|
| 1 | Geometria e luce naturale | sagome, altezze | UVL/DBGT/CTR + LiDAR | OSM senza altezze (10 % ha l'altezza) o GHSL a 100 m | **sì**: altezza per edificio dove non c'è altro |
| 2–4 | Consumi, firma, priorità | superfici (piani) | piani stimati da UVL/LiDAR o dal file/visure | stima grossolana | sì, indirettamente (piani dalle altezze) |
| 5, 10, 11 | Fabbisogno, pompe di calore, solare termico | geometria + modulo UNI | come 1 | come 1 | come 1 |
| 6 | FV con le ombre | falde dei tetti, ostacoli | DSM (falde) dove c'è; tetti piani con UVL | tetti piani su sagome OSM, ombre approssimate | **parziale**: un'altezza per edificio migliora le ombre, **non dà le falde** (servono DSM o LAS) |
| 7 | Comunità energetiche | produzione FV, consumi | come 6 | come 6 | come 6 |
| 8, 12 | Facciate e tetti | facciate esposte, ombre | come 1 e 6 | approssimato | sì per le ombre tra edifici |
| 9 | Cielo visibile e LEED | scena 3D | come 1 | approssimato | sì |
| 13 | Clima che cambia | clima dal 1940 | indipendente dagli edifici | indipendente | no |
| 14 | Obblighi di legge | superficie in pianta, S/V | sagome + altezze | S/V incerto | sì per S/V |
| — | Patrimonio (particelle) | catasto | **API catastale di Zornade** (già in uso) | idem | — |
| — | Ortofoto, Visure | — | — | — | no (visura-api a parte, fase 11) |

In sintesi: Zornade aggiunge valore **solo per le altezze degli edifici fuori dai territori con un DB topografico con
altezze o un DSM aperto**, e lo aggiunge su sagome OSM (copertura variabile). Non sostituisce il DSM per le falde e il FV
dettagliato. Nei territori coperti (ER, Lombardia, FVG, Liguria, Trento, Bolzano) **non aggiunge nulla** di essenziale:
lì le fonti aperte hanno sagome migliori (per corpo) e licenza più semplice (CC BY/CC0 invece di ODbL).

## 4. Licenza, condizioni e rischi

- **ODbL**: tutto ciò che contiene altezze di Zornade va nell'archivio `odbl/`, con «© OpenStreetMap contributors (ODbL
  1.0)» e «Dati elaborati da Zornade» con link; i database derivati si ridistribuiscono **alla stessa licenza** (share-
  alike). Un corpo CC BY che prende l'altezza da Zornade diventa ODbL (`zornade.py` lo fa già). Per i report (opere
  prodotte) basta l'attribuzione. Conseguenza: due archivi e due attribuzioni dove si mescolano le fonti.
- **Termini del 18/09/2026** (allineati in fase 4 e 7): uso libero anche commerciale; conservazione consentita per il
  servizio; vietati GDPR violato, re-identificazione, rivendita dei dati grezzi senza attribuzione, carichi eccessivi;
  l'estrazione massiva via API **fa sospendere il token** → le altezze vanno prese **solo da un estratto consegnato**, mai
  dall'API (lo fa già il lettore). Il token resta essenziale per Patrimonio: non va messo a rischio.
- **Dipendenze**: un fornitore privato e piccolo per un dato che EuGEnio potrebbe ricavare da sé dalla fonte pubblica
  (LiDAR PNRR del MASE); aggiornamenti e continuità non garantiti; formato e colonne dell'estratto non ancora noti
  (il lettore li riconosce per sinonimi). Le altezze annunciate per novembre non sono ancora uscite.
- **Qualità**: sagome OSM (incomplete in molte regioni, nessuna divisione per corpo), un'altezza per edificio; residuo
  GlobalBuildingAtlas (CC BY-NC) da escludere (il lettore lo scarta).
- **Rischio di licenza sulle altezze**: se Zornade le ricava dal LiDAR PNRR, la licenza del dato di partenza (ancora da
  verificare) vale anche per loro.

## 5. Alternative

1. **LiDAR PNRR direttamente** (dopo il 7/11/2026, se la licenza è compatibile): stessa fonte delle altezze di Zornade,
   con DSM e falde, in CC BY o simile, senza ODbL. Ostacolo: il portale PST non si automatizza (blocchi a mano, per
   tessera); la pipeline a tessere della fase C e `lidar-corpi` sono pronti a riceverlo.
2. **Altre regioni con DB topografico**: riprovare dal server le voci «in attesa» (Piemonte BDTRE, Toscana, Marche,
   Sicilia, …) e scrivere gli adattatori (Trento, Piemonte); ogni regione attiva riduce lo spazio di Zornade.
3. **OSM + GHSL** come ripiego dichiarato («altezza di quartiere»), già nella catena del § 4.
4. **Altezza inserita dall'utente** per le sedi del suo patrimonio (modello DXF/IFC, visure, piani).

## 6. Raccomandazione

**Servono solo per le altezze degli edifici nelle regioni senza DB topografico con altezze né DSM aperto, e solo finché
il LiDAR PNRR non è usabile direttamente.** Non servono in Emilia-Romagna, Lombardia, FVG, Liguria, Trento e Bolzano, né
per falde, FV dettagliato e ortofoto; l'API catastale resta com'è (fase 7).

Quindi, per il § 14.2: rispondere a Zornade **senza impegni sull'estratto dell'Emilia-Romagna** (non serve), chiedendo
di essere avvisati quando escono le altezze LiDAR e con quali **licenza, colonne, copertura, data del rilievo e costo**;
decidere sull'estratto solo dopo aver visto, dopo il 7/11, se il LiDAR PNRR si può usare direttamente. Se sì, Zornade per
le altezze non serve; se no, un estratto per le regioni scoperte, nell'archivio ODbL, come fonte temporanea.

## 7. Cosa resta da decidere (Paolo)

- [ ] Rispondere a Zornade (§ 14.2) nel senso del § 6, o aspettare il controllo del PST dopo il 7/11/2026.
- [ ] Dopo il 7/11: licenza e scaricabilità del LiDAR PNRR (DA_FARE, «Attività manuali»).
- [ ] Se si prende l'estratto: regioni da chiedere (§ 2) e verifica della licenza delle altezze.
