# Fase 15 – Statistiche dell'elettricità (Terna)

Modulo `elettricita` per due pagine della sezione Statistiche del sito (sperimentali):

| Modulo | Pagina | Dati di Terna |
|---|---|---|
| `terna_dc.py`, `costruisci.py` | «Produzione e consumi di elettricità» (`elettricita.html`) | statistiche annuali per regione e provincia |
| `carichi.py` | «Carichi elettrici» (`carichi.html`, 20/11/2026) | fabbisogno ogni 15 minuti per zona di mercato, produzione per fonte (Italia) |

**Decisione di Paolo (20/11/2026):** i dati di Terna si caricano sul sito per le elaborazioni ma **non si scaricano**
(nessun CSV, Excel o JSON da scaricare; al più immagini delle elaborazioni). I file costruiti stanno solo sul server:
`fase5-sito/sito/dati/elettricita/` e `fase5-sito/sito/dati/carichi/` sono in `.gitignore`.

Prove: `cd fase15-elettricita && python -m pytest -q` (solo dati inventati, niente rete).

## Produzione e consumi di elettricità (`terna_dc.py`, `costruisci.py`)

Stato al 21/11/2026: scaricatore e costruttore funzionanti (grandezza «Emissioni» pubblicata con la versione del sito 20261122a, release `v2026.11.22`; periodo a due indicatori nella pagina dal 22/11/2026; dal 22/11/2026 controllo degli anni copiati da un altro anno e ricostruzione della produzione 2006, 2007, 2017 e della capacità 2006, 2017, vedi «Problemi noti nei dati di Terna»); pagina «Produzione e consumi di elettricità»
(`fase5-sito/sito/elettricita.html`, `elettricita.js`) pubblicata il 21/11/2026 (`?v=20261121a`, sperimentale), come «Carichi elettrici».

I dati di Terna **non vanno nel repository** e **non si scaricano dal sito** (decisione di Paolo): la cartella
`raw/` e `fase5-sito/sito/dati/elettricita/` sono nel `.gitignore`.

### Uso

```sh
# scarico (una richiesta al secondo; salta gli anni già presenti, --ultimi N riscarica gli ultimi N anni)
cd /home/claude/terna
PYTHONPATH=/home/claude/eugenio/fase15-elettricita python3 -m elettricita.terna_dc raw [--dataset A,B] [--ultimi N]

# file della pagina
cd fase15-elettricita
python3 -m elettricita.costruisci /home/claude/terna/raw /tmp/el ../fase5-sito/sito/dati/mappa
rm -rf ../fase5-sito/sito/dati/elettricita && cp -r /tmp/el ../fase5-sito/sito/dati/elettricita

python3 -m pytest -q      # prove (niente rete)
```

### Grandezza «Emissioni» (21/11/2026, richiesta di Paolo; pubblicata con la versione 20261122a, release `v2026.11.22`)

`costruisci.py` legge `GrossVsCO2Emissions` (`leggi_emissioni`) e scrive in `italia.json`:
- per regione `emissioni[anno] = [[GWh × 5], [kt CO2 × 5], [tep × 5]]` per combustibile (`EMISSIONI_VOCI`: gas, solidi,
  petroliferi, altri, bio) e `indicatori[anno]` = `[termoelettrico GWh, rinnovabili GWh, totale GWh senza pompaggi e
  accumuli, CO2 kt, tep, fattore medio tCO2/MWh, fattore del termoelettrico tCO2/MWh, tep/MWh]` (`indicatori()`);
- `zone` (zone di mercato dal 2021, `ZONE`, controllate con `sito/dati/mappa/zone.json`: errore se diverse) con gli
  indicatori sommati prima dei rapporti; `emissioni.italia` per l'Italia;
- `emissioni.riferimenti`: copia di `elettricita/riferimenti_emissioni.json` (MEF, ISPRA, metodo dell'energia primaria,
  data di lettura). Il file è nei `package-data` del pacchetto.

**Cosa c'è nei dati.** Ci sono i dati regionali di tutti gli anni 2000–2025 per tutte e 20 le regioni: non serve
ripiegare sulle zone di mercato (Terna non pubblica le emissioni per zona né per provincia). Nei file l'ordine vero delle
colonne è Anno, Combustibile, Produzione, Regione, Emissioni. «Gas naturale» diventa «Gas Naturale» dal 2021. La voce
**Bioenergie** ha emissioni non nulle (7,5 Mt nel 2023): è la voce «altri combustibili» di Terna, con la parte fossile dei
rifiuti, i gas di sintesi e i gas residui (Sardegna, Sarroch: ~4 TWh e 1,8 Mt nel 2023); la CO2 biogenica è contata zero
come nell'inventario. **Altri** sono soprattutto i gas siderurgici (Puglia) e recuperi senza emissioni (Lombardia,
Toscana, Sardegna). Il totale nazionale coincide con ISPRA (Rapporto 430/2026, Tabella 1.16, solo elettricità) nel 2005
(−2 %), 2010 e 2021–2025 (sotto l'1 %), ma è più alto dell'8–12 % nel 2015–2020 (p. es. 2020: 82,5 contro 73,5 Mt):
Terna non ha ricalcolato quegli anni come l'inventario; i fattori di quegli anni sono quindi più alti di quelli ISPRA.

**Fattori.** Medio = CO2 / produzione lorda totale senza pompaggi e accumuli; del termoelettrico = CO2 / produzione
termoelettrica lorda con le bioenergie (stessa definizione di ISPRA, Tabella 1.7, colonna 1: nel 2022–2024 coincidono
alla quarta cifra).

**Energia primaria** (`energia_primaria()`). Il Download Center (i 15 dataset scaricati da `terna_dc.py`) non ha i
consumi di combustibile; ISPRA li pubblica solo per l'Italia (Excel del Rapporto 430/2026, foglio «23», «Consumo di
energia per la produzione elettrica», dati di Terna). Stima per regione: gas naturale, solidi, petroliferi = emissioni /
fattore tCO2/tep (ISPRA 430/2026, Tabella 1.4: gas naturale, carbone da vapore, olio combustibile; 2022–2024, fuori
intervallo l'anno più vicino); bioenergie e altri (e combustibili con produzione ma senza emissioni) = GWh × 1000 ×
0,086 / 0,35 (rendimento convenzionale dal Reg. delegato (UE) 2023/2104, Allegato I). Controllo con ISPRA (somma delle
regioni / consumo ISPRA): 2005 +0,5 %, 2010 −0,7 %, 2015 +2,2 %, 2020 +0,9 %, 2022 +3,2 %, 2023 +3,1 %, 2024 +3,5 %,
2025 +1,2 %. Il petroliferi con l'olio combustibile è l'approssimazione più debole (dentro ci sono anche gas di raffineria
e coke di petrolio), ma pesa poco (1–2 % della produzione termoelettrica).

**Riferimenti** (`riferimenti_emissioni.json`, letti il 21/11/2026):
- MEF/MASE **0,187 tep/MWh**: delibera AEEG EEN 3/08 del 28/3/2008, art. 2.1, usata nei certificati bianchi (Guida
  operativa GSE). Non abbiamo trovato atti che la sostituiscano: il DM MASE 21/7/2025 (GU n. 211 dell'11/9/2025) non indica
  un altro fattore nel testo. Non è un dato annuale ma una previsione del 2008.
- **ISPRA, Rapporto 430/2026** «Settore elettrico: emissioni di CO2 e altri impatti. Edizione 2026» (giugno 2026; sostituisce
  i rapporti «Fattori di emissione atmosferica di gas a effetto serra nel settore elettrico nazionale e nei principali Paesi
  europei» e «Le emissioni di CO2 nel settore elettrico nazionale e regionale») e il suo Excel
  `FE_energia_elettrica_2025-V2.xlsx` (7/7/2026): foglio «9» = Tabella 1.7 per tutti gli anni 1990–2025 (termoelettrico
  solo fossili, termoelettrico con bioenergie, produzione lorda, consumi; 2025 preliminare; convertiti da gCO2/kWh a
  tCO2/MWh), foglio «23» = consumo di energia per la produzione elettrica (ktep) e rendimento equivalente 2005–2025;
  Tabella 2.2 = fattori regionali 2024. Licenza CC BY 4.0 con citazione.
- Ultimo anno (2025, Italia): fattore medio 0,213 tCO2/MWh (ISPRA 0,214), termoelettrico 0,368 (ISPRA 0,367; solo fossili
  0,413), energia primaria 0,166 tep/MWh (ISPRA 0,164; MEF 0,187, −11 %).

Per aggiornare i riferimenti ogni anno (ISPRA pubblica entro il 30 giugno, DM 224/2023): nuove righe in
`riferimenti_emissioni.json` (serie, Tabella 1.4, foglio «23») e nuova data in `letto`.

### Lo scaricatore (`elettricita/terna_dc.py`)

Usa l'interfaccia della pagina https://dati.terna.it/download-center (POST JSON su
`/api/sitecore/dati/downloadcenter/recordsv2`, nessuna chiave, non consuma la quota dell'API ufficiale). Ogni anno
di ogni dataset va in `raw/<dataset>_<anno>.json` = `{"Columns": {...}, "Count": n, "Data": [[...], ...]}`.

**Paginazione** (20/11/2026): il servizio restituisce al massimo 50 000 righe per richiesta. Gli anni più grandi
(Market, ElectricalEnergy, Total, IndustrialSector, ServiceSector del 2019 e del 2020: 46 000–114 000 righe) si
leggono a pagine (`pageIndex` 0, 1, 2… con `pageSize` 50000, una richiesta al secondo) finché le righe arrivano a
`Count`; alla fine si controlla che siano esattamente `Count`, altrimenti `RuntimeError`. Verificato sul 2019 che
l'ordine crescente e quello decrescente danno le stesse righe (le pagine non si sovrappongono e non saltano righe
anche con valori uguali). Prove in `tests/test_terna_dc.py`.

Attenzione: `ElectricalEnergy` 2019 e 2020 erano stati scaricati prima di questo controllo con le sole prime 50 000
righe (metà dei consumi); riscaricati il 20/11/2026. Per controllare una cartella `raw` vecchia: ogni file deve avere
`Count == len(Data)`.

### Dataset

Unità: energia in GWh, potenza in MW. Livello territoriale: regione e provincia (107 province, nomi di Terna:
alcuni da riparare, vedi `ripara()` in `costruisci.py`; «Valle D'Aosta» nei consumi, «Valle d'Aosta» nella
produzione). Anni: quelli che restituisce il servizio al 20/11/2026.

#### Già usati dalla pagina

| Dataset | Anni | Colonne | Contenuto |
|---|---|---|---|
| GenerationPlants | 2000–2025 | Anno, Tipo capacità (Lorda/Netta), Regione, Provincia, Fonte, Potenza efficiente (MW) | potenza per fonte: Termoelettrico, Idrico, Eolico, Fotovoltaico, Geotermoelettrico, Accumulo stand alone |
| CapacityRenewableSources | 2000–2025 | … Fonti, Potenza efficiente (MW) | rinnovabili con le bioenergie |
| CapacityThermal | 2000–2025 | … Categoria, Sottocategoria, Potenza efficiente (MW) | termoelettrico per categoria e sottocategoria (come ProductionThermal) |
| ElectricityBySource | 2000–2025 | Anno, Tipo produzione (Lorda/Netta), Regione, Provincia, Fonte, Produzione (GWh) | produzione per fonte |
| ProductionRenewableSources | 2000–2025 | … Fonte rinnovabile, Produzione (GWh) | rinnovabili con le bioenergie |
| Total | 2000–2024 | Anno, Regione, Provincia, Settore, Attività, Classe, Consumo (GWh) | consumi per settore (Industria, Servizi, Domestico, Agricoltura), sommando attività e classi |
| ElectricalEnergy | 2000–2024 | Anno, Regione, Provincia, Settore, Consumo (GWh) | solo riserva per gli anni senza Total e per il confronto (vedi «Problemi noti») |
| ConsumptionBySource | 2005–2024 | Anno, Regione, Fonte, Copertura (GWh) | copertura della richiesta per fonte, solo regione |
| ElectricityByType | 2005–2024 | Anno, Regione, Tipologia, Domanda (GWh) | rinnovabili, tradizionali, saldo import/export, solo regione |

#### Nuovi (20/11/2026, per analisi future; la pagina non li usa ancora)

**ThermalHeat** – calore prodotto dagli impianti cogenerativi. 2000–2025, regione e provincia.
Colonne: Anno, Regione, Provincia, Impianto cogenerativo, Calore prodotto (GWh). Tipi di impianto:
Ciclo combinato con cogenerazione (CCC), Combustione interna con cogenerazione (CIC), Condensazione e spillamento
(CSC), Contropressione (CPC), Turbine a gas con cogenerazione (TGC), Celle combustibili con cogenerazione (CEC).
La stessa chiave (provincia, tipo) compare più volte con valori diversi (una dimensione nascosta, probabilmente
l'impianto o la sezione; nel 2025 le righe raddoppiano, 993 contro ~530): **si sommano**. Totale Italia:
54,3 TWh (2005), 61,1 (2017), 51,7 (2024), 53,1 (2025); nel 2024 CCC 20,1, CIC 14,2, TGC 8,5, CSC 5,5, CPC 3,4 TWh.

**ProductionThermal** – produzione termoelettrica per categoria e sottocategoria. 2000–2025, regione e provincia.
Colonne: Anno, Regione, Provincia, Categoria (Cogenerative / Non cogenerative), Sottocategoria, Produzione (GWh).
Sottocategorie cogenerative: Ciclo Combinato Con Produzione Di Calore, Combustione Interna Con Produzione Di Calore,
Turbine A Gas Con Produzione Di Calore, Condensazione e spillamento, Contropressione, Celle combustibili con
cogenerazione; non cogenerative: Ciclo combinato, Combustione interna, Turbine a gas, Condensazione, Turbo
espansione, Celle combustibili / Celle A Combustibile, Combustione Esterna, Altro genere (nomi non uniformi negli
anni). **Manca la colonna Lorda/Netta**: ogni chiave compare due volte, il valore maggiore è la produzione lorda,
il minore la netta (somma dei maggiori = Termoelettrico lordo di ElectricityBySource: 162 588 GWh nel 2023; somma
dei minori = netto, 156 156). Sommare tutto conta la produzione due volte. Cogenerativa lorda: 94 TWh (2005),
110 (2017), 96 (2023), 91 (2024), 95 (2025).

**GrossVsCO2Emissions** – produzione termoelettrica lorda ed emissioni di CO2 per combustibile. 2000–2025, **solo
regione** (dal 21/11/2026 lo usa la grandezza «Emissioni», vedi sotto). Colonne: Anno, Combustibile (Solidi, Gas naturale / «Gas Naturale» dal 2021, Petroliferi, Bioenergie,
Altri), Produzione (GWh, lorda: il totale coincide con il termoelettrico lordo), Regione, Emissioni (milioni di
tonnellate di CO2, comprese quelle delle bioenergie). Alcuni valori sono vuoti (`null`). Italia: 141,5 Mt (2005),
67,5 (2023), 56,4 (2024), 58,3 (2025).

**Market** – consumi per mercato. 2000–2024, regione e provincia. Colonne: Anno, Regione, Provincia, Mercato
(Autoconsumo, Mercato libero, Mercato tutelato), Consumo (GWh). Dal 2021 una riga per provincia e mercato; fino al
2020 più righe per chiave (dimensione nascosta, nel 2019–2020 fino a ~650 righe per provincia e mercato): si
sommano. Vedi sotto il significato dell'autoconsumo.

**IndustrialSector**, **ServiceSector**, **Total** – consumi per attività economica e classe, regione e provincia.
Colonne: Anno, Regione, Provincia, [Settore, solo Total], Attività, Classe, Consumo (GWh). IndustrialSector e Total
2000–2024, ServiceSector solo 2019–2024 (il servizio non ha anni precedenti; i servizi 2000–2018 per classe sono in
Total). **La classificazione cambia nel 2019**: 2000–2018 classi merceologiche di Terna (industria 17 classi, p.es.
«Energia ed acqua / Elettricità e gas», «Manifatturiera di base / Cartaria»; servizi 9 classi, p.es. «Commercio»,
«Trasporti», «Illuminazione pubblica»; agricoltura una sola voce); dal 2019 divisioni Ateco (industria 38 classi in 6
attività, servizi 50 classi in 18 attività, agricoltura 13 classi). Righe ripetute per chiave fino al 2020: si
sommano. In IndustrialSector c'è un'attività vuota con classe vuota (107 righe, sempre 0 GWh). La somma di Total per
settore coincide con ElectricalEnergy (salvo 2019–2020, vedi sotto) e con IndustrialSector / ServiceSector.
Dal 20/11/2026 la pagina prende i consumi per settore da Total (vedi la tabella sopra).

### Autoconsumo (dataset Market)

Che cosa comprende, verificato sui dati scaricati il 20/11/2026:

- **Fa parte dei consumi**: Autoconsumo + Mercato libero + Mercato tutelato = consumi totali di ElectricalEnergy e di
  Total in ogni anno (per esempio 2024: 34 310 + 244 097 + 8 518 = 286 925 GWh). È quindi l'energia consumata dagli
  autoproduttori con la propria produzione, senza prelievo dalla rete, ed è già dentro i consumi per settore; il
  mercato libero e il tutelato sono i prelievi dalla rete secondo il contratto di fornitura.
- **È soprattutto industriale e termoelettrico**: valeva già 21–24 TWh nel 2000–2007, quando il fotovoltaico non
  c'era (4–7 GWh). Le province con più autoconsumo nel 2023 sono quelle dei grandi autoproduttori industriali:
  Taranto 2 939 GWh (acciaieria, quasi il 90 % dei consumi industriali della provincia), Cuneo 1 303, Bergamo 1 200,
  Lucca 1 096 (cartiere), Siracusa 1 055 (raffinerie e petrolchimico), Milano 1 039, Modena 953. In nessuna
  provincia supera i consumi dell'industria. Tra le province (2023) è più legato al calore cogenerativo (ThermalHeat,
  correlazione 0,65) e ai consumi industriali (0,64) che alla produzione cogenerativa (0,42) o fotovoltaica (0,37).
- **È una parte della produzione degli autoproduttori, non tutta**: 30,9 TWh nel 2023 contro 96 TWh di produzione
  termoelettrica cogenerativa lorda (che comprende però anche le centrali di produttori non autoproduttori) e 30,7 TWh
  di fotovoltaico lordo. L'energia prodotta dagli autoproduttori e immessa in rete non è autoconsumo. Terna non
  pubblica nel Download Center la produzione degli autoproduttori per provincia, quindi il confronto diretto non è
  possibile con questi dati.
- **Comprende anche l'autoconsumo fotovoltaico**, almeno in parte: dal 2023 al 2024 cresce di 3,4 TWh (30,9 → 34,3),
  in 100 province su 107, con gli aumenti maggiori dove cresce anche il fotovoltaico (Brescia +230, Udine +207,
  Bergamo +129, Milano +127 GWh), mentre cala nei poli industriali termoelettrici (Taranto −363, Chieti −53, Siracusa
  −50). La correlazione tra le variazioni provinciali di autoconsumo e di fotovoltaico è però debole (0,16): il dato
  non permette di separare la quota fotovoltaica da quella termoelettrica.
- Serie Italia (GWh): 23 819 (2000), 20 169 (2006), 17 530 (2009), 21 103 (2010), 24 995 (2014), 29 125 (2018),
  28 468 (2020), 30 745 (2021), 30 866 (2023), 34 310 (2024).

### Problemi noti nei dati di Terna

- **ElectricalEnergy 2019 e 2020: mancano ~7 e ~5,5 TWh di industria** rispetto a Total, Market e IndustrialSector
  (2019: 121 978 contro 128 940 GWh; 2020: 119 952 contro 125 417), concentrati a Brescia (2019: 4 606 contro 8 535)
  e Taranto (796 contro 3 828), cioè metallurgia e autoconsumo. Gli altri settori e gli altri anni coincidono.
  **Risolto il 20/11/2026**: il costruttore prende i consumi da Total (somma per anno, provincia e settore) e usa
  ElectricalEnergy solo per gli anni in cui Total manca. `confronta_consumi()` confronta i due per provincia e anno e
  scrive nel log (stderr) e nel campo `note` di `italia.json` (non usato da `elettricita.js`) le differenze sopra il
  5 %: con i dati del 20/11/2026 sono solo Brescia 2019 (12 738 contro 8 809 GWh, −31 %) e 2020 (11 727 contro
  8 804, −25 %), Taranto 2019 (5 199 contro 2 167, −58 %) e 2020 (4 617 contro 2 076, −55 %). Totale Italia dei
  consumi: 2019 296 254 GWh (prima 289 290), 2020 279 171 (prima 273 705); 2015 +41 GWh (servizi di alcune grandi
  province, sotto la soglia); gli altri anni invariati.
- **Anni copiati da un altro anno** (trovato il 22/11/2026; segnalazione a Terna preparata). Alcuni file del Download
  Center sono la copia di un altro anno con l'anno cambiato. Con i dati scaricati al 22/11/2026 (`trova_copie()` su
  tutti i 354 file di `raw/`):

  | Dataset | Anno | Copia di | Tipo |
  |---|---|---|---|
  | ElectricityBySource | 2017 | 2008 | stesse 684 righe (Italia 319 130 GWh, il dato 2008, invece di ~295 800) |
  | ElectricityBySource | 2006 | 2004 | stesse righe (più 59 righe ripetute) |
  | ElectricityBySource | 2007 | 2005 | stessi valori (96 %) su province e fonti diverse; stessi totali per fonte |
  | GenerationPlants | 2005 | 2002 | stesse righe |
  | GenerationPlants | 2006 | 2004 | stesse righe |
  | GenerationPlants | 2017 | 2012 | contiene tutte le 800 righe del 2012 più 113 righe diverse (930 righe con le ripetute): erano questi i «+16 GW di termoelettrico» che prima si correggevano col minore tra GenerationPlants e CapacityThermal |
  | CapacityRenewableSources | 2005 | 2004 | stesse righe |

  Nessuna copia in ProductionRenewableSources, ProductionThermal, CapacityThermal, ElectricityByType,
  GrossVsCO2Emissions, ConsumptionBySource, Total, ElectricalEnergy, Market, IndustrialSector, ServiceSector,
  ThermalHeat. Regole (`trova_copie`, solo file con almeno 20 righe con un valore): «identico» = stesse righe tolto
  l'anno; «contiene» = ha tutte le righe dell'altro anno, che sono almeno l'80 % delle sue; «valori» = almeno il 95 %
  dei valori diversi da zero sono quelli dell'altro anno. Negli identici e nei «valori» la copia è l'anno più recente
  (in tutti i casi l'anno più vecchio coincide con le altre tabelle del suo anno). **Gli anni copiati non si leggono**
  (`_righe(..., salta)`), per ogni dataset; nota in `italia.json` → `note`, su stderr e in `esito["controlli"]["copie"]`.
  - **Produzione** (`ricostruisci_produzione`): termoelettrico lordo = ProductionThermal (per ogni chiave il valore
    maggiore = lordo; somma = termoelettrico lordo di ElectricityBySource negli anni buoni, p. es. 199 430 GWh nel 2016,
    192 730 nel 2018), idrico rinnovabile, geotermico, eolico, fotovoltaico = ProductionRenewableSources, pompaggi =
    ConsumptionBySource «Idrico tradizionale» per regione (negli anni buoni circa il 2 % sotto il lordo) divisi tra le
    province come la media dell'anno valido prima e dopo. Italia: 2017 **295 787 GWh** (prima 360 854; dato Terna
    295 832), 2006 314 000 (prima 305 248), 2007 313 948 (prima 307 452). Se manca ProductionThermal o
    ProductionRenewableSources dell'anno, l'anno resta vuoto con la nota «dato di Terna non disponibile».
  - **Capacità** (`ricostruisci_capacita`): termoelettrico = CapacityThermal meno il geotermico (CapacityThermal lo
    comprende fino al 2022: si decide confrontando con GenerationPlants nell'anno valido più vicino), rinnovabili =
    CapacityRenewableSources, pompaggio puro = media per provincia dell'anno valido prima e dopo. Italia: 2017
    117 178 MW (prima 117 816), 2006 92 098 (prima 83 556). **2005 vuoto** (anche CapacityRenewableSources 2005 è una
    copia): dato di Terna non disponibile.
  - **Controllo anti-salto** (`controlla_salti`): nota se il totale nazionale di capacità, produzione, richiesta,
    consumi, produzione termoelettrica o CO2 di un anno si scosta di più del 15 % dalla media dell'anno prima e dopo.
    Con i dati del 22/11/2026 resta solo «emissioni di CO2 2022, 86 689 kt contro 72 984 (+19 %)» (dato di Terna, da
    verificare).
  - **Da verificare** (non corretto): la capacità 2005–2009 sembra in parte spostata di un anno (GenerationPlants 2009
    ha 7 MW di fotovoltaico e il termoelettrico di CapacityThermal 2006; CapacityRenewableSources 2006 e 2007 hanno
    l'eolico che Terna dà per il 2005 e il 2006). Non sono copie esatte e il controllo non le riconosce.
- **ElectricityBySource 2017**: era la copia del 2008 (sopra); la «produzione lorda uguale alla netta» e il fotovoltaico
  di 193 GWh venivano da lì. Prima del 22/11/2026 il costruttore prendeva il massimo con ProductionRenewableSources e
  l'Italia 2017 risultava 360 854 GWh.
- Righe doppie con la stessa chiave in CapacityRenewableSources (2017–2018, valori vicini: si tiene il maggiore),
  ThermalHeat (tutti gli anni, da sommare), ProductionThermal (lorda e netta senza colonna), Market/consumi fino al 2020
  (da sommare).
- Nomi non uniformi: «Valle D'Aosta» / «Valle d'Aosta», «Gas naturale» / «Gas Naturale», sottocategorie
  termoelettriche con maiuscole diverse, province con caratteri sbagliati (`ripara()`).
- Anni diversi tra dataset: produzione e potenza fino al 2025, consumi fino al 2024, ServiceSector solo dal 2019.

## Carichi elettrici (`elettricita/carichi.py`)

### Fonte: Terna e non il GME

Paolo aveva chiesto la «potenza richiesta ricalcolata dall'energia scambiata in borsa». I dati del **GME** sono però
solo per uso interno e non si mostrano sul sito: la pagina usa il **fabbisogno di Terna** («Fabbisogno Italia»,
dataset `TotalLoad` del Download Center: carico effettivo in MW medi ogni 15 minuti, per zona di mercato e Italia;
comprende perdite e autoconsumi). Il punto unico per cambiare fonte è `FONTE_CARICO` in `carichi.py` (dataset
dell'archivio, colonne, scala, testo della fonte): se arrivasse la licenza del GME basta scrivere nell'archivio un
dataset con le stesse colonne e cambiare lì.

La produzione per fonte di Terna (`ActualGeneration`, `RenewableGeneration`) è **solo nazionale**: il grafico delle
fonti è sempre dell'Italia; con una zona scelta la pagina lo dice (nessuna ripartizione per zona inventata).

### Archivio (ingresso)

Due formati (vedi anche «Aggancio al worker» sotto per il Parquet del server). Sul PC: una cartella con un file per
dataset e mese: `<archivio>/<Dataset>_<AAAA>-<MM>.json` =
`{"Columns": {nome: tipo, …}, "Data": [[…], …]}`, cioè la risposta del Download Center così com'è.

| Dataset | Colonne usate | Unità |
|---|---|---|
| `TotalLoad` (obbligatorio) | `Date`, `Total Load [MW]`, `Bidding Zone` (Italy, North, Centre-North, Centre-South, South, Calabria, Sicily, Sardinia) | MW |
| `ActualGeneration` | `Date`, `Actual Generation`, `Primary Source` (Thermal, Hydro, Wind, Geothermal, Photovoltaic, Self-consumption) | GW medi |
| `RenewableGeneration` | `Date`, `Renewable Generation`, `Energy Source` (Biomass, Hydro, Wind, Geothermal, Photovoltaic) | GW medi |

`Date`: millisecondi dal 1/1/0001 in ora locale italiana (come il Download Center), oppure ISO `AAAA-MM-GGTHH:MM[:SS]`
in ora locale, oppure ISO con il fuso. Nel giorno del ritorno all'ora solare le 02:00–02:45 compaiono due volte senza
indicazione: la prima occorrenza vale come ora legale, la seconda come solare, e per ogni zona si sceglie poi l'ordine
che fa tornare la somma delle zone con l'Italia (`_ora_doppia`). I dati orari (la generazione fino al 2024) valgono per
i quattro quarti d'ora dell'ora. Una zona sconosciuta ferma la costruzione (configurazione zonale cambiata: aggiornare
`ZONE` e `fase5-sito/costruisci_zone.py`).

Scaricamento (una richiesta al secondo, pagine da 50.000 righe con `pageIndex` se `Count` le supera):

```
python -m elettricita.carichi scarica <archivio> --da 2025-11 [--a 2026-11] [--rifai-ultimo]
```

### File della pagina (uscita)

```
python -m elettricita.carichi costruisci <archivio> <uscita>      # costruisci_carichi(archivio, uscita)
```

- `indice.json`: fonti, data di costruzione, zone (`ITA`, `NORD`, `CNOR`, `CSUD`, `SUD`, `CALA`, `SICI`, `SARD`),
  voci con i colori (gli stessi di `costruisci.py`: termo #8a8f99, bio #f0912a, idro #7cc7e0, geo #d4561c,
  eol #a9c641, fv #f7cb15, saldo #c7a0c0) e i mesi: `inizio` (primo quarto d'ora, UTC = mezzanotte italiana del
  primo del mese), `n` (quarti d'ora con dati: il mese in corso è tagliato all'ultimo), `ora_legale` (`[[indice,
  minuti dall'UTC], …]` a ogni cambio), `passo_carico`, `fonti`, `passo_fonti` (15 o 60), `rinnovabili`.
- `carico_AAAA-MM.json`: `{"mese", "zone": {ITA: [MW interi o null] × n, …}}` (≈ 120 kB al mese).
- `fonti_AAAA-MM.json`: `{"mese", "voci": {termo, bio, idro, geo, eol, fv, saldo: [MW interi o null] × n}}`
  (≈ 100 kB al mese): fv, eol, geo, idro (con i pompaggi), bio dalla produzione rinnovabile (autoconsumi compresi);
  termo = produzione totale con gli autoconsumi meno le rinnovabili (senza `RenewableGeneration`: le rinnovabili di
  `ActualGeneration` e bio = 0); saldo = potenza richiesta dell'Italia − produzione (estero meno pompaggi e accumuli,
  può essere negativo).

La pagina scarica solo i mesi del periodo scelto (12 mesi ≈ 2,6 MB non compressi, molto meno con la compressione del
server).

### Aggancio al worker (fase 4, unito il 20/11/2026)

Il lavoro `carichi` del worker (`fase4-server/servizio/worker.py`, README della fase 4 § «Dati di Terna») gira subito
dopo `terna-api` se l'archivio è cambiato: chiama `costruisci_carichi(TERNA_DATI/serie, sito/dati/.carichi_nuova)` e
pubblica la cartella in `sito/dati/carichi/` con `_pubblica` se il controllo passa. Il worker **non** usa `scarica` di
questo modulo: l'archivio lo tiene `servizio/terna.py` (API ufficiale per il giorno prima, Download Center per lo
storico dal 2021), in **Parquet**, una cartella per serie e un file per mese:

| Dataset di questo modulo | Serie dell'archivio del worker | Colonne lette |
|---|---|---|
| `TotalLoad` | `carico_totale/AAAA-MM.parquet` | `istante` (UTC), `zona`, `carico_mw` |
| `ActualGeneration` | `produzione/AAAA-MM.parquet` | `istante`, `fonte`, `energia_gwh` (GW medi al passo di 15 minuti) |
| `RenewableGeneration` | `rinnovabili/AAAA-MM.parquet` | `istante`, `fonte`, `energia_gwh` |

`costruisci_carichi` riconosce da sé i due formati (cartella `carico_totale/` con dei `.parquet` = archivio del worker,
altrimenti i JSON del Download Center sopra); i file della pagina sono identici (prova `test_archivio_parquet_del_worker`).
L'ora ripetuta di ottobre nel Parquet è già risolta da `terna.py`; `_ora_doppia` la ricontrolla con la somma delle zone.
`scarica` e `python -m elettricita.carichi scarica` restano per le prove sul PC. Il server deve comprimere i `.json`
(gzip/brotli) e può tenerli in cache per un giorno.

Prova con i dati veri (20/11/2026): 13 mesi (novembre 2025 – 19 novembre 2026), 39 richieste in circa 2 minuti,
costruzione in 5 secondi, nessun quarto d'ora mancante tranne il 14–15 gennaio 2026 (192, assenti anche nei dati di
Terna); somma delle zone = Italia (scarto massimo 2 MW, arrotondamenti).
