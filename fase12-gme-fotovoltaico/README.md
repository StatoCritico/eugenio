# Fase 12 – Analisi sui dati GME quartorari: fotovoltaico, accumuli, CER, offerte, costo per POD

> **Uso interno finché non c'è la licenza GME.** Nessun dato GME o EEX (serie, cache, archivi, esempi), nessuna
> credenziale e nessun valore derivato entra nel repository, nel sito, nei report o nella newsletter. Le pagine
> pubbliche collegate (Fotovoltaico › Prezzo catturato, accumuli e mercato; gruppo Cogenerazione) restano segnaposto
> «in attesa della licenza GME» finché la licenza scritta non arriva.

Stato al 03/11/2026: **progetto, nessun codice**. Richiesta di licenza da fare nella call con il GME (registro delle
domande: [`DOMANDE_CALL_GME.md`](DOMANDE_CALL_GME.md)). La cogenerazione (report 13–20) è nella
[fase 13](../fase13-cogenerazione/README.md). Il client GME e lo storico notturno restano nella fase 6.

Documenti di riferimento:
- [`../documenti/eugenio-gme-riepilogo.md`](../documenti/eugenio-gme-riepilogo.md) – discussione del 01/11/2026;
- [`../documenti/call-gme-verifica.md`](../documenti/call-gme-verifica.md) – scaletta della call di verifica.

## Obiettivo

Chiedere al GME l'autorizzazione a usare i dati quartorari (MGP, PUN Index GME, prezzi zonali di tutte le zone di
mercato in mappa) **solo come input di calcolo**: la serie grezza non si rende mai scaricabile, si pubblicano solo
indicatori derivati. Stesso principio adottato per le norme UNI.

## Decisioni

- **Serve una licenza scritta del GME** (art. 5, 6 e 6 bis delle condizioni): un servizio pubblico va oltre l'uso
  personale e informativo; senza consenso scritto sono vietati pubblicazione, memorizzazione, estratti e riassunti per
  fini economici, e l'estrazione automatizzata. Fino alla licenza vale la decisione del 28/10/2026 (fase 6): lo
  storico si scarica entro le quote per il solo uso interno.
- **MTE nella richiesta** (§ 3): prezzi di controllo dei prodotti mensili (3 mesi), trimestrali (4) e annuali,
  baseload e peakload, come stima di mercato per mese corrente e fine anno. Limiti: liquidità scarsa (registrazioni
  OTC), solo PUN e solo baseload/peakload (zone e fasce si ricostruiscono con i rapporti storici zona/PUN e
  fascia/baseload sui quartorari), a novembre la stima di fine anno = consuntivi + prodotto di dicembre. Alternativa:
  future EEX sull'Italia, con altra licenza e citazione separata.
- Per la cogenerazione si chiedono anche MGP-gas, IG Index GME, MT-Gas e mercato dei TEE (fase 13).
- Impegni offerti: serie mai ridistribuita né scaricabile (né interfaccia né API); solo aggregati e indicatori;
  «Fonte: Gestore dei Mercati Energetici S.p.A.» in ogni output; marchio PUN INDEX GME solo per indicare il dato;
  accesso solo dal canale ufficiale (API o FTP) entro le quote, senza scraping.

## Report (1–12)

1. **PUN e PZM**: aggregati mensili e per fasce del mese precedente, stima del mese corrente e di fine anno.
2. **Prezzo catturato** FV standalone o FV+BESS (FV fisso, varie taglie di BESS): autoconsumo diretto, autoconsumo a
   distanza su un edificio o un gruppo, immissione totale; periodo a scelta (predefinito l'ultimo anno).
3. **Effetto della granularità 15' rispetto all'orario** su prezzo catturato, ricavi BESS e costi di consumo
   (l'argomento più diretto per chiedere i quartorari).
4. **Arbitraggio BESS merchant** (senza FV): spread giornaliero massimo-minimo per zona, ricavo teorico a 1 e 2 cicli
   al giorno, durate 1, 2 e 4 ore, saturazione al crescere della taglia.
5. **Cannibalizzazione solare**: capture rate del FV per zona nel tempo, quarti d'ora a prezzo nullo o basso, profilo
   medio giornaliero per mese («duck curve»).
6. **Incentivo CER**: stima della tariffa premio sull'energia condivisa (parte variabile legata al prezzo zonale
   orario), confronto tra RID e vendita a mercato.
7. **Offerta indicizzata o a fasce**: costo di un profilo di consumo dell'utente (curva quartoraria del distributore)
   con prezzo indicizzato rispetto a mono, bi o F1-F3, spread di pareggio.
8. **Valore della flessibilità dei carichi**: spostamento di ricarica dei veicoli, pompa di calore, accumulo termico;
   finestre ottimali per zona e stagione.
9. **Clima e prezzi**: correlazione con temperatura e irraggiamento (dati climatici di EuGEnio) e costo orario della
   climatizzazione di un edificio (collegato alla fase 10).
10. **Differenziali zonali**: spread zona–PUN, frequenza della separazione zonale, zone favorevoli per FV e BESS.
11. **Volatilità e rischio**: distribuzione dei prezzi, percentili per fascia, indicatori per contratti indicizzati.
12. **Costo totale dell'energia per POD**: previsione di spesa per la PA e verifica delle fatture del fornitore in
    convenzione (componenti sotto).

## Costo totale per POD (§ 4)

| Componente | Fonte |
|---|---|
| Energia (formula della convenzione: PUN o prezzo per fascia + spread di lotto) | Convenzione Consip / Intercent-ER (fase 6) + GME |
| Perdite di rete, dispacciamento | ARERA / Terna |
| Trasporto, gestione del contatore, oneri di sistema | ARERA (aggiornamento trimestrale) |
| Accise | Legge (D.Lgs. 504/1995) – non le pagine ADM |
| IVA | Legge |

## Condizioni di riuso verificate (§ 5)

| Fonte | Condizioni | Conseguenza per EuGEnio |
|---|---|---|
| **GME** | licenza personale, gratuita, non cedibile, uso informativo e privato (art. 5); vietati senza consenso scritto pubblicazione, memorizzazione, riassunti ed estratti per fini economici (art. 6) e TDM/bot/scraper per qualsiasi finalità (art. 6 bis, eccezione per organismi di ricerca, art. 3 Dir. UE 2019/790); API: niente condivisione delle credenziali né superamento delle quote; citazione «Fonte: Gestore dei Mercati Energetici S.p.A.»; PUN INDEX GME, IGI e IG Index GME sono marchi | **licenza scritta** prima di qualsiasi output pubblico |
| **ARERA** | riuso in **CC BY-SA 4.0** (d.lgs. 36/2006, condizioni del 27/03/2025); vietato riprodurre il sito; logo non utilizzabile | tabelle tariffarie pubblicate in CC BY-SA con «Fonte: ARERA»; nei report combinati con GME: ARERA come componente separata e dichiarata, solo il totale calcolato, uso coperto dalla licenza GME; delibere linkate, non ripubblicate; la BY-SA riguarda i dati, non il codice |
| **Consip** | consip.it CC BY 3.0 (pagina datata, da ricontrollare); dati.consip.it CC BY 4.0 anche commerciale; marchi senza suggerire affiliazione | riuso con citazione |
| **Intercent-ER** | documenti di gara liberi, licenza di riuso non trovata | da verificare |
| **ADM** | contenuti del sito non riproducibili senza consenso; vietato il deep linking non trasparente | aliquote prese dalla norma (Normattiva/GU) citando la norma |
| **ISPRA** | CC BY 4.0, anche commerciale, senza share-alike | fattori di emissione utilizzabili nei report |
| **GSE** | CC BY-NC-SA 3.0 IT; incompatibile con la BY-SA 4.0 di ARERA nelle opere derivate | nessun contenuto GSE riprodotto (vedi fase 13) |

## Regole per il repository

- Nessun dato GME (serie, cache, archivi) e nessuna credenziale API nel codice pubblico.
- I dati di terzi eventualmente inclusi (tariffe ARERA in CC BY-SA 4.0, fattori ISPRA in CC BY 4.0) in una cartella
  separata con la licenza e la fonte di ciascuno.
- Nessun contenuto GSE e nessun estratto di norme UNI.

## Punti aperti

- [ ] Call con il GME: domande e risposte in [`DOMANDE_CALL_GME.md`](DOMANDE_CALL_GME.md); poi risposte scritte o bozza
      di licenza, revisione di un legale, adattamento dell'interfaccia ai livelli di aggregazione concordati.
- [ ] Verificare le note legali di Intercent-ER; ricontrollare quelle di consip.it.
- [ ] Verificare se EuGEnio rientra nell'eccezione per la ricerca scientifica (art. 6 bis GME).
- [ ] Far rivedere da un legale la richiesta al GME e la questione BY-SA nei report combinati.
- [ ] Definire il metodo di stima a fine anno (MTE più rapporti storici) e la licenza di eventuali fonti esterne (EEX).
- [ ] Verificare il regime degli oneri di sistema sull'energia autoconsumata.

## Fonti

- GME – Condizioni di utilizzo del sito: https://www.mercatoelettrico.org/Home/CondizioniUtilizzo
- GME – Condizioni generali API (EN): https://www.mercatoelettrico.org/Portals/0/Documents/en-US/20251015CONDIZIONI_GENERALI_API_En.pdf
- ARERA – Termini e condizioni d'uso: https://arera.it/termini-e-condizioni-uso-del-sito
- consip.it – Note legali: https://www.consip.it/note-legali-e-privacy
- dati.consip.it – Note legali: https://dati.consip.it/note-legali
- ISPRA – Note legali: https://www.isprambiente.gov.it/it/note-legali
- ADM – Legal notice: https://www.adm.gov.it/portale/ee/legal-notice
- Contatto GME: Viale Maresciallo Pilsudski 122/124, 00197 Roma, tel. +39 06 8012 1, PEC gme@pec.mercatoelettrico.org
