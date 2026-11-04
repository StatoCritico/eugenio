# Fase 13 – Cogenerazione (CHP) in autoconsumo sull'edificio

> **Uso interno finché non c'è la licenza GME.** I report usano prezzi elettrici quartorari, prezzi del gas (MGP-gas,
> IG Index GME, MT-Gas) e del mercato dei TEE: nessuno di questi dati, né valori derivati, va nel repository, nel sito,
> nei report o nella newsletter prima della licenza scritta. Le pagine del gruppo Cogenerazione del sito sono
> segnaposto; solo «Emissioni» (fattori ISPRA) potrà partire prima, per la parte che non dipende dai prezzi.

Stato al 03/11/2026: **progetto, nessun codice**. Fa parte della stessa richiesta di licenza della
[fase 12](../fase12-gme-fotovoltaico/README.md) (domande in [`DOMANDE_CALL_GME.md`](../fase12-gme-fotovoltaico/DOMANDE_CALL_GME.md)).
Documento di riferimento: [`../documenti/eugenio-gme-riepilogo.md`](../documenti/eugenio-gme-riepilogo.md) (§ 2,
report 13–20; § 4; § 5).

## Report (13–20)

| # | Report | Pagina del sito |
|---|---|---|
| 13 | **Spark spread di autoconsumo**: per zona, mese, fascia e quarto d'ora, costo evitato dell'elettricità prelevata rispetto al costo del gas per produrla, al netto del calore recuperato; ore convenienti all'anno | Cogenerazione › Spark spread di autoconsumo |
| 14 | **Simulazione del cogeneratore sull'edificio**: fabbisogno termico ed elettrico da clima e modello 3D (fase 10); inseguimento termico, elettrico, ottimizzazione economica a 15'; taglia ed eventuale accumulo termico | Cogenerazione › Cogeneratore sull'edificio, con FV e accumulo |
| 15 | **Cogeneratore + FV (ed eventuale BESS)**: complementarità (FV a mezzogiorno d'estate, CHP sere e inverno), ore di CHP perse per il FV, combinazione ottimale delle taglie | idem |
| 16 | **Confronto tra alternative** a parità di fabbisogno: caldaia + rete, cogeneratore, pompa di calore (anche da FV), ibrido CHP + PdC | Cogenerazione › Confronto tra alternative e trigenerazione |
| 17 | **Trigenerazione** (facoltativa): assorbimento con il calore recuperato | idem |
| 18 | **Emissioni**: CO₂ evitata o aggiunta rispetto alla rete, fattori medi o orari | Cogenerazione › Emissioni |
| 19 | **Rischio prezzo**: sensibilità del risparmio alla variazione congiunta di elettricità e gas, con MTE e MT-Gas | Cogenerazione › Rischio prezzo elettricità e gas |
| 20 | **Budget di dissipazione CAR** fino a fine anno (dettaglio sotto) | Cogenerazione › Budget di dissipazione CAR |

### Report 20 – Dissipazione gestibile fino a fine anno nel rispetto dei requisiti CAR

**A cosa serve.** La qualifica CAR si verifica sull'anno solare. Il calore dissipato non è calore utile: abbassa il
rendimento globale e il PES. Il report dice al gestore quanto calore può ancora dissipare da oggi al 31 dicembre (per
esempio in inseguimento elettrico quando il prezzo è alto) senza scendere sotto le soglie CAR.

**Dati di ingresso**
- Consuntivo da inizio anno: energia elettrica prodotta, calore utile, calore dissipato, combustibile (misure o
  contatori).
- Previsione da oggi a fine anno: fabbisogno termico ed elettrico da clima e modello 3D, con scenari di inverno mite,
  medio e rigido dall'archivio climatico storico; piano di funzionamento previsto; prezzi attesi di elettricità e gas
  (consuntivi più MTE e MT-Gas).
- Parametri CAR: formula del PES; rendimenti di riferimento armonizzati con le correzioni per clima, livello di
  tensione e quota autoconsumata o immessa; soglia del rendimento globale oltre la quale tutta l'elettricità conta come
  cogenerativa; soglia PES per classe di taglia (indicativamente > 0 sotto 1 MWe e ≥ 10 % sopra). **Tutti da
  verificare sugli atti normativi in vigore.**

**Come si calcola**
1. Rendimento globale e PES progressivi da inizio anno.
2. Proiezione a fine anno nello scenario «senza ulteriore dissipazione».
3. Ricerca della massima dissipazione (MWh termici) che mantiene il PES annuo, calcolato sulla quota cogenerativa,
   sopra la soglia; sotto la soglia di rendimento globale l'unità si divide in parte cogenerativa e non cogenerativa,
   e l'energia qualificabile come CAR si riduce.
4. Distribuzione ottimale del budget sui quarti d'ora con lo spark spread più alto, rispettando avviamenti, potenza
   minima e manutenzione.

**Indicatori**
- Rendimento globale progressivo e proiettato, margine rispetto alla soglia.
- PES progressivo e proiettato, margine rispetto alla soglia CAR.
- **Budget di dissipazione residuo** (MWh termici) per scenario: prudente, medio, ottimistico.
- Ore aggiuntive in dissipazione consentite e **prezzo soglia** dell'elettricità oltre il quale conviene spenderle.
- Margine economico aggiuntivo confrontato con il valore dei benefici CAR (TEE ed eventuali altre agevolazioni da
  verificare): quanto costerebbe superare il limite.
- Energia elettrica qualificabile come CAR (E_CHP) stimata a fine anno.
- Avvisi: 80 % del budget superato, scenario rigido che azzera il margine, scostamento consuntivo–previsione oltre una
  tolleranza.

**Aggiornamento**: almeno mensile, settimanale negli ultimi mesi dell'anno.

## Indicatori per la cogenerazione

- **Energetici**: PES e verifica dei requisiti CAR; rendimento elettrico, termico e globale; ore equivalenti e numero
  di avviamenti; calore dissipato; quote del fabbisogno coperte da cogeneratore, FV e rete; quota autoconsumata e
  immessa.
- **Economici**: spark spread medio catturato; costo della produzione elettrica (€/MWh) con gas al netto del calore
  valorizzato; risparmio rispetto al riferimento; ricavi da TEE e da energia immessa (RID o mercato); beneficio
  dell'accisa ridotta sul gas; costo di manutenzione per ora; VAN, tempo di ritorno, TIR.
- **Effetto della granularità**: differenza tra simulazione a 15' e oraria (avviamenti, modulazione, interazione con
  il FV).

## Componenti di costo in più rispetto al costo per POD (§ 4)

| Componente | Fonte |
|---|---|
| Gas (formula della convenzione gas: PSV o indice + spread) | Convenzione Consip / Intercent-ER + GME (MGP-gas, IG Index) |
| Trasporto e distribuzione del gas | ARERA (CC BY-SA 4.0) |
| Accise sul gas, con l'aliquota ridotta per la quota usata nella produzione elettrica | D.Lgs. 504/1995 (dalla norma, non dalle pagine ADM) |
| Regole CAR, PES, rendimenti di riferimento, TEE | normativa UE e nazionale (sotto) |
| Prezzi dei TEE | GME (mercato TEE) |
| Fattori di emissione | ISPRA (CC BY 4.0) |

## Fonti normative e regola sui contenuti GSE

I contenuti del sito GSE (linee guida, testi, tabelle, esempi) sono in **CC BY-NC-SA 3.0 IT**: «condividi allo stesso
modo» è incompatibile con la CC BY-SA 4.0 di ARERA nelle opere derivate che li combinano. Quindi:
- **non si riproducono** testi, tabelle o esempi delle linee guida GSE, né nel repository né nel sito né nei report;
- formula del PES, soglie CAR e rendimenti di riferimento si implementano **direttamente dagli atti normativi**, liberi:
  - [D.Lgs. 8 febbraio 2007, n. 20](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2007-02-08;20)
    (cogenerazione ad alto rendimento);
  - [DM 4 agosto 2011](https://www.gazzettaufficiale.it/eli/id/2011/09/19/11A12046/sg) (integrazione del D.Lgs. 20/2007,
    calcolo del PES e della quota CHP);
  - [Regolamento delegato (UE) 2015/2402](https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32015R2402)
    (valori di rendimento di riferimento armonizzati);
- le linee guida GSE si usano solo per capire il metodo (metodi e idee non sono protetti), citandole come riferimento.

EuGEnio è open source e non commerciale, quindi il vincolo «non commerciale» del GSE sarebbe rispettato; restano
l'obbligo di condividere allo stesso modo e l'incompatibilità con ARERA.

## Punti aperti

- [ ] Licenza GME anche per MGP-gas, IG Index GME, MT-Gas e TEE (domande della call, sezione «Dati gas e TEE»).
- [ ] Verificare sugli atti in vigore: formula e soglie del PES, rendimenti di riferimento e fattori di correzione,
      soglie di rendimento globale, metodo di calcolo della quota cogenerativa (base del report 20).
- [ ] Verificare il regime attuale dell'accisa ridotta sul gas per cogenerazione e degli oneri di sistema
      sull'energia autoconsumata.
- [ ] Fabbisogno termico ed elettrico dell'edificio dalla fase 10 (dipende dal modello 3D e dal modulo UNI privato).
