# EuGEnio – Dati GME quartorari: riepilogo della discussione

*Data: 1 novembre 2026*

## 1. Obiettivo

Chiedere a GME l'autorizzazione a usare i dati quartorari (MGP, PUN Index GME, prezzi zonali) in EuGEnio. I dati servono **solo come input di calcolo**: non vengono mai resi scaricabili e si pubblicano solo indicatori derivati. Lo stesso principio vale per tutte le zone di mercato mostrate sulla mappa di EuGEnio (PZM). È lo stesso approccio già adottato per le norme UNI.

## 2. Report proposti

### Report già previsti
1. **PUN e PZM**: valori aggregati mensili e per fasce del mese precedente, stima del mese corrente e stima a fine anno.
2. **Prezzo catturato** da un impianto FV standalone o FV+BESS (FV fisso, varie taglie di BESS). Gli scenari sono:
   - autoconsumo diretto;
   - autoconsumo a distanza su un edificio o un gruppo di edifici;
   - immissione totale in rete.

   Il periodo di analisi è a scelta, con l'ultimo anno come impostazione predefinita.

### Report aggiuntivi proposti
3. **Effetto della granularità 15' rispetto all'orario**: differenze su prezzo catturato, ricavi BESS e costi di consumo. È l'argomento più diretto per giustificare la richiesta dei dati quartorari.
4. **Arbitraggio BESS merchant (senza FV)**: spread giornaliero massimo-minimo per zona, ricavo teorico a 1 e 2 cicli al giorno, durate di 1, 2 e 4 ore e saturazione del valore al crescere della taglia.
5. **Cannibalizzazione solare**: capture rate del FV per zona nel tempo, quarti d'ora a prezzo nullo o basso, profilo medio giornaliero per mese ("duck curve").
6. **Incentivo CER**: stima della tariffa premio sull'energia condivisa (la parte variabile dipende dal prezzo zonale orario) e confronto tra RID e vendita a mercato per l'energia immessa.
7. **Offerta indicizzata o a fasce**: costo di un profilo di consumo dell'utente (curva quartoraria del distributore) con prezzo indicizzato rispetto a mono, bi o F1-F3, e spread di pareggio.
8. **Valore della flessibilità dei carichi**: risparmio ottenibile spostando la ricarica dei veicoli elettrici, la pompa di calore o l'accumulo termico, con le finestre ottimali per zona e stagione.
9. **Clima e prezzi**: correlazione del prezzo con temperatura e irraggiamento usando i dati climatici storici di EuGEnio, e costo orario della climatizzazione di un edificio. Si collega alla pagina 3D degli edifici.
10. **Differenziali zonali**: spread tra prezzo zonale e PUN, frequenza della separazione zonale, zone favorevoli per FV e BESS.
11. **Volatilità e rischio**: distribuzione dei prezzi, percentili per fascia, indicatori di rischio per chi valuta contratti indicizzati.
12. **Costo totale dell'energia per POD** (vedi §4), con due usi: previsione di spesa per la PA e verifica delle fatture del fornitore in convenzione.

### Report per la cogenerazione (CHP) in autoconsumo sull'edificio, con o senza FV
13. **Spark spread di autoconsumo**: confronta, per zona, mese, fascia e quarto d'ora, il costo evitato dell'elettricità prelevata dalla rete con il costo del gas necessario a produrla, al netto del calore recuperato. Ne deriva il numero di ore convenienti all'anno.
14. **Simulazione del cogeneratore sull'edificio**:
    - il fabbisogno termico ed elettrico viene dai dati climatici e dal modello 3D di EuGEnio;
    - le strategie di funzionamento confrontate sono tre: inseguimento termico, inseguimento elettrico, ottimizzazione economica sui prezzi a 15';
    - comprende il dimensionamento della taglia e dell'eventuale accumulo termico.
15. **Cogeneratore + FV (ed eventuale BESS)**:
    - complementarità tra le fonti: il FV copre il mezzogiorno estivo a prezzi bassi, il cogeneratore copre sere e inverno;
    - riduzione delle ore di funzionamento del cogeneratore dovuta al FV;
    - combinazione ottimale delle taglie.
16. **Confronto tra alternative a parità di fabbisogno**: caldaia + rete, cogeneratore, pompa di calore (anche alimentata da FV), ibrido cogeneratore + pompa di calore.
17. **Trigenerazione** (opzionale): raffrescamento ad assorbimento alimentato dal calore recuperato, che aumenta le ore utili in estate.
18. **Emissioni**: CO₂ evitata o aggiunta rispetto alla rete, con fattori di emissione medi o orari.
19. **Rischio prezzo**: sensibilità del risparmio alla variazione congiunta di prezzo elettrico e gas, con stime basate su MTE e MT-Gas.
20. **Dissipazione termica gestibile fino a fine anno senza perdere la qualifica CAR** (dettaglio nella sezione dedicata più avanti).

#### Report 20 – Dissipazione gestibile fino a fine anno nel rispetto dei requisiti CAR

**A cosa serve.** La qualifica CAR si verifica su base annua (anno solare). Il calore dissipato non conta come calore utile, quindi abbassa il rendimento globale e il PES. Il report dice al gestore quanto calore può ancora dissipare da oggi al 31 dicembre, per esempio funzionando in inseguimento elettrico quando il prezzo dell'energia è alto, senza scendere sotto le soglie CAR.

**Dati di ingresso:**
- Consuntivo da inizio anno: energia elettrica prodotta, calore utile, calore dissipato, combustibile consumato (da misure o contatori).
- Previsione da oggi a fine anno:
  - fabbisogno termico ed elettrico dell'edificio da clima e modello 3D, con scenari di inverno mite, medio e rigido tratti dall'archivio climatico storico;
  - piano di funzionamento previsto;
  - prezzi attesi di elettricità e gas (consuntivi più MTE e MT-Gas).
- Parametri CAR:
  - formula del PES;
  - valori di rendimento di riferimento armonizzati, con le correzioni per clima, livello di tensione e quota autoconsumata o immessa;
  - soglia del rendimento globale oltre la quale tutta l'energia elettrica conta come cogenerativa;
  - soglia PES per la classe di taglia (indicativamente > 0 sotto 1 MWe e ≥ 10% sopra).

  Tutti i parametri vanno verificati sulle regole e linee guida GSE in vigore.

**Come si calcola:**
1. Calcolo del rendimento globale e del PES progressivi da inizio anno.
2. Proiezione a fine anno nello scenario "senza ulteriore dissipazione".
3. Ricerca della massima quantità di calore dissipabile (MWh termici) che mantiene il PES annuo, calcolato sulla quota cogenerativa, sopra la soglia. Il calcolo tiene conto che, sotto la soglia di rendimento globale, l'unità si divide in una parte cogenerativa e una non cogenerativa, con conseguente riduzione dell'energia qualificabile come CAR.
4. Distribuzione ottimale del "budget di dissipazione" sui quarti d'ora con lo spark spread più alto, rispettando i vincoli di avviamento, potenza minima e manutenzione.

**Indicatori:**
- Rendimento globale progressivo e proiettato, e margine rispetto alla soglia.
- PES progressivo e proiettato, e margine rispetto alla soglia CAR.
- **Budget di dissipazione residuo** (MWh termici) per scenario climatico: prudente, medio, ottimistico.
- Ore aggiuntive di funzionamento in dissipazione consentite, con il **prezzo soglia** dell'energia elettrica oltre il quale conviene spenderle.
- Margine economico aggiuntivo ottenuto spendendo il budget, confrontato con il valore dei benefici legati alla CAR (TEE ed eventuali altre agevolazioni da verificare): mostra quanto costerebbe superare il limite.
- Energia elettrica qualificabile come CAR ("E_CHP") stimata a fine anno.
- Avvisi: superamento dell'80% del budget, scenario rigido che azzera il margine, scostamento tra consuntivo e previsione oltre una tolleranza.

**Aggiornamento:** almeno mensile, settimanale negli ultimi mesi dell'anno, quando il margine si restringe.

### Indicatori per la cogenerazione
- **Energetici**:
  - PES e verifica dei requisiti CAR;
  - rendimento elettrico, termico e globale;
  - ore equivalenti e numero di avviamenti;
  - calore dissipato;
  - quote del fabbisogno coperte da cogeneratore, FV e rete;
  - quota autoconsumata e quota immessa.
- **Economici**:
  - spark spread medio catturato;
  - costo della produzione elettrica (€/MWh) con gas al netto del calore valorizzato;
  - risparmio rispetto allo scenario di riferimento;
  - ricavi da TEE e da energia immessa (RID o mercato);
  - beneficio dell'accisa ridotta sul gas;
  - costo di manutenzione per ora;
  - VAN, tempo di ritorno, TIR.
- **Effetto della granularità**: differenza tra simulazione a 15' e oraria (vincoli di avviamento, modulazione, interazione con il FV).

## 3. Stime di fine anno: il Mercato a Termine (MTE)

GME non pubblica stime proprie, ma gestisce il **Mercato a Termine dell'energia elettrica (MTE)**. Sull'MTE sono quotati prodotti baseload e peakload mensili (i 3 mesi successivi), trimestrali (i 4 trimestri successivi) e annuali (l'anno successivo). I relativi **prezzi di controllo** rappresentano l'aspettativa del mercato e GME li pubblica anche nella newsletter mensile.

I limiti da tenere presenti:
- **Liquidità scarsa**: i volumi sono soprattutto registrazioni OTC fatte a fini di clearing, quindi il prezzo è indicativo.
- **Solo PUN e solo profili baseload e peakload**: le stime zonali e per fascia vanno ricostruite applicando ai prodotti MTE i rapporti storici zona/PUN e fascia/baseload calcolati sui dati quartorari.
- **Stima a fine anno a novembre**: si ottiene dai consuntivi più il prodotto mensile di dicembre.
- **Alternativa**: i future EEX sull'Italia, che hanno però un'altra licenza e richiedono una citazione separata.

**Decisione:** includere i prezzi MTE nella richiesta a GME. Per la cogenerazione si aggiungono i prezzi del mercato del gas (MGP-gas, IG Index GME), del mercato a termine del gas (MT-Gas) e del mercato dei TEE.

## 4. Costo totale dell'energia

Le componenti, calcolate per POD a partire dalla curva di prelievo, sono:

| Componente | Fonte |
|---|---|
| Energia (formula della convenzione: PUN o prezzo per fascia + spread di lotto) | Convenzione Consip / Intercent-ER + GME |
| Perdite di rete, dispacciamento | ARERA / Terna |
| Trasporto, gestione del contatore, oneri di sistema | ARERA (aggiornamento trimestrale) |
| Accise | Legge / Agenzia delle Dogane e dei Monopoli |
| IVA | Legge |

Per la cogenerazione servono in più:

| Componente | Fonte |
|---|---|
| Gas (formula della convenzione gas: PSV o indice + spread) | Convenzione Consip / Intercent-ER + GME (MGP-gas, IG Index) |
| Trasporto e distribuzione del gas | ARERA |
| Accise sul gas, compresa l'aliquota ridotta per la quota usata nella produzione elettrica | Agenzia delle Dogane e dei Monopoli |
| Regole CAR, PES, rendimenti di riferimento, TEE | GSE / normativa UE e nazionale |
| Prezzi dei TEE | GME (mercato TEE) |
| Fattori di emissione | ISPRA |

## 5. Condizioni di riuso verificate

### GME: serve una licenza scritta
- **Condizioni del sito** (art. 5): la licenza è personale, gratuita, non cedibile e limitata all'uso informativo e privato. Sono vietate le finalità economiche o commerciali, anche indirette. Un servizio pubblico come EuGEnio va oltre l'uso privato.
- **Art. 6**: senza consenso scritto è vietato pubblicare, memorizzare, trasmettere, creare riassunti o estratti e distribuire i contenuti per fini economici o lucrativi.
- **Art. 6 bis**: estrazione e analisi automatizzata (text and data mining, crawler, bot, scraper) sono vietate senza autorizzazione scritta, per qualsiasi finalità. Fanno eccezione gli organismi di ricerca e gli istituti di tutela del patrimonio culturale che operano per ricerca scientifica (art. 3 della Direttiva UE 2019/790).
- **API**: valgono condizioni analoghe (uso informativo e personale), più il divieto di condividere le credenziali e di superare le quote.
- **Citazione obbligatoria**: "Fonte: Gestore dei Mercati Energetici S.p.A."
- **Marchi**: PUN INDEX GME, IGI e IG Index GME sono marchi di GME.
- **Contatto per licenze commerciali**: GME S.p.A., Viale Maresciallo Pilsudski 122/124, 00197 Roma, tel. +39 06 8012 1.
- Fonti: [Condizioni di utilizzo del sito](https://www.mercatoelettrico.org/Home/CondizioniUtilizzo), [Condizioni API (EN)](https://www.mercatoelettrico.org/Portals/0/Documents/en-US/20251015CONDIZIONI_GENERALI_API_En.pdf)

### ARERA: riuso consentito in CC BY-SA 4.0
- Il riuso di dati e documenti è consentito in base al d.lgs. 36/2006 con licenza **CC BY-SA 4.0**: va indicata la fonte e ciò che ne deriva deve restare riutilizzabile alle stesse condizioni.
- È vietato riprodurre il sito o parti di esso su altri siti o sistemi informativi senza autorizzazione scritta. Per le delibere e le pagine conviene quindi linkare la fonte invece di ripubblicarle.
- Il logo non si può usare senza autorizzazione.
- Versione delle condizioni: ultima modifica 27 marzo 2025.
- Fonte: [Termini e condizioni d'uso del sito ARERA](https://arera.it/termini-e-condizioni-uso-del-sito)

**Conseguenze per EuGEnio:**
- Le tabelle tariffarie ARERA, se pubblicate anche rielaborate, vanno rilasciate in CC BY-SA 4.0 con "Fonte: ARERA".
- Nei report che combinano dati ARERA (licenza con obbligo di condivisione) e dati GME (non ridistribuibili) conviene:
  - tenere ARERA come componente separata e dichiarata;
  - mostrare solo il totale calcolato, senza esporre la serie GME;
  - far coprire esplicitamente questo uso dalla licenza GME.
- Non è chiaro se un risultato numerico calcolato sia "materiale derivato" ai sensi della BY-SA: il punto è discutibile.
- La BY-SA riguarda i dati, non il codice di EuGEnio.

### Consip: riuso consentito, anche commerciale
- **consip.it**: contenuti in CC BY 3.0 salvo diversa indicazione (la pagina trovata è datata, va ricontrollata).
- **dati.consip.it**: dati in CC BY 4.0, utilizzabili anche per scopi commerciali citando fonte e autori.
- **Marchi**: è vietato usarli in modo da suggerire un'affiliazione o una sponsorizzazione di MEF o Consip.
- Fonti: [consip.it – Note legali](https://www.consip.it/note-legali-e-privacy), [dati.consip.it – Note legali](https://dati.consip.it/note-legali)

### Intercent-ER: da verificare
- Il sito ha una pagina "Note legali e copyright" che non sono riuscito a leggere.
- I documenti di gara sono ad accesso libero e gratuito, ma non è stata trovata una licenza di riuso esplicita.

### Accise e IVA
- Sono fissate per legge e i testi degli atti ufficiali non sono coperti dal diritto d'autore. Non si prevedono problemi.

### ISPRA: riuso consentito, anche commerciale (CC BY 4.0)
- Salvo diversa indicazione, i dati sono in CC BY 4.0: liberamente distribuibili e riutilizzabili citando la fonte e, dove possibile, l'URL della pagina originale.
- Non c'è obbligo di condivisione allo stesso modo, quindi i fattori di emissione si usano nei report senza vincoli sui risultati.
- Fonte: [ISPRA – Note legali](https://www.isprambiente.gov.it/it/note-legali)

### Agenzia delle Dogane e dei Monopoli: condizioni restrittive
- È vietato copiare, riprodurre, pubblicare o distribuire i contenuti del sito senza consenso scritto, salvo estratti per uso personale. È vietato anche il deep linking non trasparente.
- **Soluzione**: le aliquote di accisa sono fissate per legge (Testo Unico Accise, D.Lgs. 504/1995 e successive modifiche). Si prendono dalla norma (Normattiva o Gazzetta Ufficiale) citando la norma, senza riprodurre pagine o circolari ADM.
- Fonte: [ADM – Legal notice (EN)](https://www.adm.gov.it/portale/ee/legal-notice). Da controllare anche la versione italiana.

### GSE: CC BY-NC-SA 3.0 IT
- I contenuti del sito sono rilasciati con licenza **Attribuzione – Non commerciale – Condividi allo stesso modo 3.0 Italia** (badge "Licenza Creative Commons" nel piè di pagina di gse.it).
- **Non commerciale**: vietato l'uso per scopi prevalentemente orientati a vantaggio commerciale o compenso economico. Se EuGEnio ha componenti commerciali, per riprodurre contenuti GSE serve un'autorizzazione.
- **Condividi allo stesso modo**: le rielaborazioni vanno distribuite con la stessa licenza.
- **Incompatibilità con ARERA**: un'opera derivata che combina contenuti GSE (BY-NC-SA 3.0) e ARERA (BY-SA 4.0) non può rispettare entrambe le clausole "stessa licenza", perché una impone il vincolo non commerciale e l'altra vieta restrizioni aggiuntive.
- **Soluzione**:
  - non riprodurre testi, tabelle o esempi delle linee guida GSE;
  - implementare formula del PES, soglie CAR e rendimenti di riferimento direttamente dagli atti normativi (D.Lgs. 20/2007, DM 4 agosto 2011, Reg. UE 2015/2402), che sono liberi;
  - usare le linee guida GSE solo per capire il metodo (metodi e idee non sono protetti dal diritto d'autore), citandole come riferimento.
- Licenza: [CC BY-NC-SA 3.0 IT](https://creativecommons.org/licenses/by-nc-sa/3.0/it/)

## 6. Punti aperti
- [ ] Preparare e inviare la richiesta di licenza a GME (vedi file della call).
- [ ] Verificare le note legali di Intercent-ER.
- [ ] Ricontrollare la versione attuale delle note legali di consip.it.
- [ ] Verificare se EuGEnio rientra nell'eccezione per la ricerca scientifica (art. 6 bis GME).
- [ ] Far rivedere da un legale la richiesta a GME e la questione BY-SA nei report combinati.
- [ ] Definire il metodo di stima a fine anno (MTE più rapporti storici) e la licenza di eventuali fonti esterne (EEX).
- [x] Verificate le condizioni di riuso di GSE (CC BY-NC-SA 3.0 IT), ISPRA (CC BY 4.0) e Agenzia delle Dogane (restrittiva, usare la norma). Per ARERA gas valgono le condizioni ARERA (CC BY-SA 4.0).
- [x] EuGEnio è open source e non commerciale: il vincolo "non commerciale" del GSE è rispettato. Restano l'obbligo di condividere allo stesso modo e l'incompatibilità con ARERA nei contenuti derivati che li combinano.
- [ ] Repository open source:
  - nessun dato GME (serie, cache, archivi) e nessuna credenziale API nel codice pubblico;
  - i dati di terzi eventualmente inclusi (tariffe ARERA in CC BY-SA 4.0, fattori ISPRA in CC BY 4.0) vanno in una cartella separata con la licenza e la fonte di ciascuno;
  - nessun contenuto GSE e nessun estratto di norme UNI.
- [ ] Verificare sulle regole GSE in vigore: formula e soglie del PES, rendimenti di riferimento e fattori di correzione, soglie di rendimento globale, metodo di calcolo della quota cogenerativa (base del report 20).
- [ ] Verificare il regime attuale dell'accisa ridotta sul gas per cogenerazione e degli oneri di sistema sull'energia autoconsumata.
