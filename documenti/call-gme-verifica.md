# Call di verifica con GME – Scaletta

*Oggetto: licenza d'uso dei dati quartorari GME in EuGEnio*

## 1. Presentazione (2 minuti)
- **Che cos'è EuGEnio**: un servizio di calcolo energetico per edifici e impianti, con mappa delle zone di mercato, dati climatici storici e (in arrivo) modellazione 3D degli edifici.
- **Natura del progetto**: EuGEnio è **open source e non commerciale**, senza fini di lucro né ricavi dai dati.
- **Cosa chiediamo**: di usare i dati GME **solo come input di calcolo**. Gli utenti non ricevono mai la serie grezza e vedono solo indicatori derivati.
- **Codice e dati separati**: il codice è pubblico; i dati GME e le credenziali restano solo sul server e non entrano mai nel repository.

## 2. Dati richiesti
| Dato | Granularità | Profondità storica |
|---|---|---|
| PUN Index GME (MGP) | 15 minuti | da definire (almeno l'ultimo anno, meglio dall'avvio dell'MTU a 15') |
| Prezzi zonali MGP (tutte le zone in mappa) | 15 minuti | come sopra |
| MTE: prezzi di controllo dei prodotti mensili, trimestrali e annuali, baseload e peakload | giornaliera | per le stime del mese corrente e di fine anno |
| Gas: prezzi MGP-gas e IG Index GME | giornaliera | come per l'elettricità (cogenerazione) |
| MT-Gas: prezzi dei prodotti a termine del gas | giornaliera | per le stime di fine anno (cogenerazione) |
| TEE: prezzi del mercato dei Titoli di Efficienza Energetica | per sessione | per valorizzare i certificati bianchi CAR |

## 3. Impegni che offriamo
- La serie grezza non viene mai ridistribuita né resa scaricabile, né tramite interfaccia né tramite API.
- Si pubblicano solo aggregati e indicatori calcolati.
- In ogni output compare "Fonte: Gestore dei Mercati Energetici S.p.A.".
- Il marchio "PUN INDEX GME" si usa solo per indicare il dato, senza suggerire affiliazione.
- L'accesso avviene solo tramite il canale ufficiale (API o FTP), nel rispetto delle quote, senza scraping.

## 4. Report previsti (da mostrare come esempio)
1. PUN e prezzi zonali aggregati mensili e per fasce, con stima del mese corrente e di fine anno.
2. Prezzo catturato FV e FV+BESS (autoconsumo diretto, a distanza, immissione totale).
3. Confronto tra calcolo a 15 minuti e calcolo orario (giustifica la richiesta dei dati quartorari).
4. Arbitraggio BESS standalone.
5. Cannibalizzazione solare e profilo medio giornaliero.
6. Stima dell'incentivo CER e confronto RID/mercato.
7. Confronto tra offerta indicizzata e offerta a fasce per un profilo di consumo.
8. Valore della flessibilità dei carichi.
9. Correlazione tra clima e prezzo.
10. Differenziali zonali e separazione dei mercati.
11. Volatilità e indicatori di rischio.
12. Costo totale dell'energia per POD (insieme alle tariffe ARERA e alle formule delle convenzioni Consip e Intercent-ER).

**Cogenerazione in autoconsumo sull'edificio (con o senza FV)**

13. Spark spread di autoconsumo e ore convenienti.
14. Simulazione del cogeneratore con diverse strategie di funzionamento (termica, elettrica, economica a 15').
15. Cogeneratore + FV (+ BESS): complementarità e combinazione ottimale delle taglie.
16. Confronto con caldaia, pompa di calore e sistemi ibridi.
17. Trigenerazione.
18. Emissioni evitate.
19. Rischio prezzo elettricità/gas.
20. Budget di dissipazione termica fino a fine anno nel rispetto dei requisiti CAR, da spendere nei quarti d'ora a prezzo più alto.

## 5. Domande da verificare con GME

### Licenza
- [ ] **Tipo di licenza**: serve una licenza "commerciale" anche per un servizio gratuito? Qual è la loro qualificazione dell'uso su un servizio pubblico?
- [ ] **Uso non commerciale**: per un progetto open source e non commerciale esiste una licenza specifica, eventualmente gratuita, diversa da quella commerciale?
- [ ] **Software pubblico**: il codice che legge e calcola sui dati GME (client API, formule) si può pubblicare con licenza open source, a condizione che non contenga dati né credenziali?
- [ ] **Self-hosting**: chi installa EuGEnio sul proprio server deve chiedere una licenza GME propria (ognuno con le sue credenziali e la sua autorizzazione)?
- [ ] **Costi** ed eventuali canoni.
- [ ] **Durata, rinnovo e revoca** (le condizioni standard permettono a GME di revocare in qualsiasi momento): si può avere un preavviso minimo?
- [ ] **Forma**: lettera di autorizzazione o contratto? Chi firma, e a chi va intestata?

### Output consentiti
- [ ] **Livello minimo di aggregazione** da pubblicare: si possono mostrare medie mensili e per fascia, profili medi giornalieri, percentili?
- [ ] **Grafici**: sono ammessi grafici con valori puntuali (per esempio un giorno a 15 minuti) o solo grafici aggregati?
- [ ] **Risultati personalizzati**: un calcolo fatto su richiesta dell'utente (per esempio il suo prezzo catturato) è considerato un "estratto"?
- [ ] **Ritardo**: va rispettato un ritardo minimo di pubblicazione rispetto agli esiti?
- [ ] **Formato della citazione** e posizione (in ogni report, nel piè di pagina, nella pagina delle fonti).

### Accesso tecnico
- [ ] **Canale**: API o FTP? Si possono avere quote API adeguate a un uso automatizzato periodico?
- [ ] **Automazione (art. 6 bis)**: un download automatico programmato tramite l'API ufficiale è coperto dalla licenza?
- [ ] **Archiviazione**: si può conservare lo storico in locale, non accessibile agli utenti?

### Combinazione con altri dati
- [ ] **Dati ARERA**: le tariffe ARERA sono in CC BY-SA 4.0, con obbligo di condivisione allo stesso modo. Un report di costo totale combina quei dati con i dati GME. La licenza GME può coprire esplicitamente questa combinazione, ferma restando la non ridistribuibilità della serie GME?
- [ ] **Future EEX**: si possono affiancare ai dati MTE per le stime?

### Dati gas e TEE (cogenerazione)
- [ ] I dati del mercato del gas (MGP-gas, IG Index GME, MT-Gas) e del mercato TEE possono rientrare nella stessa licenza dei dati elettrici?
- [ ] Ci sono condizioni diverse per l'indice IG Index GME, che è un marchio GME?
- [ ] I prezzi dei TEE si possono usare per valorizzare i certificati bianchi nelle simulazioni e mostrare solo il valore stimato all'utente?
- [ ] Per il report sul budget di dissipazione CAR, si possono mostrare all'utente il prezzo soglia e i quarti d'ora consigliati (che derivano dai prezzi GME)?

### Eccezione per la ricerca
- [ ] Se EuGEnio è collegato a un organismo di ricerca, si applica l'eccezione dell'art. 6 bis (art. 3 Direttiva UE 2019/790)? Fino a dove arriva (ricerca sì, servizio pubblico no?)

## 6. Dopo la call
- [ ] Farsi inviare per iscritto le risposte o una bozza di licenza.
- [ ] Far rivedere la bozza da un legale.
- [ ] Adattare l'interfaccia di EuGEnio ai livelli di aggregazione concordati.

## Riferimenti
- [GME – Condizioni generali di utilizzo del sito](https://www.mercatoelettrico.org/Home/CondizioniUtilizzo)
- [GME – Condizioni generali API (EN)](https://www.mercatoelettrico.org/Portals/0/Documents/en-US/20251015CONDIZIONI_GENERALI_API_En.pdf)
- [ARERA – Termini e condizioni d'uso](https://arera.it/termini-e-condizioni-uso-del-sito)
- **Contatto GME**: Viale Maresciallo Pilsudski 122/124, 00197 Roma, tel. +39 06 8012 1, PEC gme@pec.mercatoelettrico.org
