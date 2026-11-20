# Fase 15 – Produzione e consumi di elettricità (statistiche annuali di Terna)

Stato al 20/11/2026: scaricatore e costruttore funzionanti; pagina «Produzione e consumi di elettricità»
(`fase5-sito/sito/elettricita.html`, `elettricita.js`) in lavorazione, senza versione pubblicata.

I dati di Terna **non vanno nel repository** e **non si scaricano dal sito** (decisione di Paolo): la cartella
`raw/` e `fase5-sito/sito/dati/elettricita/` sono nel `.gitignore`.

## Uso

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

## Lo scaricatore (`elettricita/terna_dc.py`)

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

## Dataset

Unità: energia in GWh, potenza in MW. Livello territoriale: regione e provincia (107 province, nomi di Terna:
alcuni da riparare, vedi `ripara()` in `costruisci.py`; «Valle D'Aosta» nei consumi, «Valle d'Aosta» nella
produzione). Anni: quelli che restituisce il servizio al 20/11/2026.

### Già usati dalla pagina

| Dataset | Anni | Colonne | Contenuto |
|---|---|---|---|
| GenerationPlants | 2000–2025 | Anno, Tipo capacità (Lorda/Netta), Regione, Provincia, Fonte, Potenza efficiente (MW) | potenza per fonte: Termoelettrico, Idrico, Eolico, Fotovoltaico, Geotermoelettrico, Accumulo stand alone |
| CapacityRenewableSources | 2000–2025 | … Fonti, Potenza efficiente (MW) | rinnovabili con le bioenergie |
| CapacityThermal | 2000–2025 | … Categoria, Sottocategoria, Potenza efficiente (MW) | termoelettrico per categoria e sottocategoria (come ProductionThermal) |
| ElectricityBySource | 2000–2025 | Anno, Tipo produzione (Lorda/Netta), Regione, Provincia, Fonte, Produzione (GWh) | produzione per fonte |
| ProductionRenewableSources | 2000–2025 | … Fonte rinnovabile, Produzione (GWh) | rinnovabili con le bioenergie |
| ElectricalEnergy | 2000–2024 | Anno, Regione, Provincia, Settore, Consumo (GWh) | consumi per settore: Industria, Servizi, Domestico, Agricoltura |
| ConsumptionBySource | 2005–2024 | Anno, Regione, Fonte, Copertura (GWh) | copertura della richiesta per fonte, solo regione |
| ElectricityByType | 2005–2024 | Anno, Regione, Tipologia, Domanda (GWh) | rinnovabili, tradizionali, saldo import/export, solo regione |

### Nuovi (20/11/2026, per analisi future; la pagina non li usa ancora)

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
regione**. Colonne: Anno, Combustibile (Solidi, Gas naturale / «Gas Naturale» dal 2021, Petroliferi, Bioenergie,
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

## Autoconsumo (dataset Market)

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

## Problemi noti nei dati di Terna

- **ElectricalEnergy 2019 e 2020: mancano ~7 e ~5,5 TWh di industria** rispetto a Total, Market e IndustrialSector
  (2019: 121 978 contro 128 940 GWh; 2020: 119 952 contro 125 417), concentrati a Brescia (2019: 4 606 contro 8 535)
  e Taranto (796 contro 3 828), cioè metallurgia e autoconsumo. Gli altri settori e gli altri anni coincidono. La
  pagina usa ElectricalEnergy: per Brescia e Taranto 2019–2020 mostra un calo che non c'è; da valutare se usare Total.
- **ElectricityBySource 2017**: produzione lorda uguale alla netta per tutte le fonti e fotovoltaico Italia 193 GWh
  (contro 22 104 nel 2016 e 22 654 nel 2018). Il costruttore prende già il massimo con ProductionRenewableSources.
- Righe doppie con la stessa chiave in GenerationPlants (2017, +16 GW di termoelettrico), ThermalHeat (tutti gli anni,
  da sommare), ProductionThermal (lorda e netta senza colonna), Market/consumi fino al 2020 (da sommare).
- Nomi non uniformi: «Valle D'Aosta» / «Valle d'Aosta», «Gas naturale» / «Gas Naturale», sottocategorie
  termoelettriche con maiuscole diverse, province con caratteri sbagliati (`ripara()`).
- Anni diversi tra dataset: produzione e potenza fino al 2025, consumi fino al 2024, ServiceSector solo dal 2019.
