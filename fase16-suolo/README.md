# Fase 16 – Suolo e aree agricole (ISPRA/SNPA, ISTAT, Copernicus)

Modulo `suolo` per la pagina sperimentale **Statistiche › «Suolo e aree agricole»** (`fase5-sito/sito/suolo.html`,
`suolo.js`), sul modello della fase 15 (elettricità). Stato al 22/11/2026: scaricatore, incrocio agricolo, costruttore,
lavoro del worker e pagina pronti e provati sul ramo `claude/2026-11-22-suolo`; **non ancora pubblicati** (release solo
al via di Paolo).

| File | Che cosa fa |
|---|---|
| `suolo/scarica.py` | scarica gli indicatori ISPRA (file con anno e versione più alti, niente indirizzi fissi), le superfici coltivate e il censimento ISTAT (SDMX) e, a richiesta, le due carte raster per l'incrocio |
| `suolo/agricolo.py` | **suolo agricolo consumato** (stima EuGEnio): carta dei cambiamenti ISPRA × Carta di uso del suolo ISPRA, pixel per pixel, per comune |
| `suolo/colture.py` | superfici coltivate per famiglia, senza doppi conteggi (voci ISTAT gerarchiche e cambiate nel 2020) |
| `suolo/censimento.py` | SAU e superficie agricola non utilizzata del censimento 2020 per provincia e regione |
| `suolo/costruisci.py` | file della pagina `italia.json` e `RR.json`, con i controlli prima della pubblicazione |
| `suolo/classi.py` | classi della carta del consumo di suolo e gruppi della pagina; usi agricoli della carta d'uso |
| `suolo/mappa.py` | regioni, province e comuni delle mappe del sito (posizioni, abbinamento dei codici, poligoni per l'incrocio) |
| `suolo/istat_territori.json` | codici territoriali ISTAT (NUTS) → regioni e province della mappa (generata il 22/11/2026 dalla codelist CL_ITTER107) |

Licenze: ISPRA/SNPA e ISTAT **CC BY 4.0** (citazione e indicazione delle modifiche); la carta di uso del suolo ISPRA integra
dati del Copernicus Land Monitoring Service (© European Union, dati liberi con attribuzione). Citazione nella pagina e
nell'immagine: «Elaborazione EuGEnio su dati ISPRA/SNPA, ISTAT e Copernicus». I dati costruiti e scaricati **non vanno nel
repository** (`.gitignore`: `fase5-sito/sito/dati/suolo/`, `fase16-suolo/raw/`, `fase16-suolo/carte/`), come per l'elettricità;
la pagina fa scaricare solo l'immagine.

## Uso

```sh
cd fase16-suolo
python -m suolo.scarica /percorso/raw [--carte]                 # ~1 minuto; con --carte ~800 MB in più (una volta l'anno)
python -m suolo.agricolo raw/carte/consumo_suolo_2024-2025.tif raw/carte/Uso_del_suolo_2023.tif \
       ../fase5-sito/sito/dati/mappa raw/agricolo_2025.json [--regioni 08,03]      # ~70 s per l'Italia, ~0,9 GB di RAM
python -m suolo.costruisci raw /tmp/suolo ../fase5-sito/sito/dati/mappa [--precedente italia.json] [--forza]
rm -rf ../fase5-sito/sito/dati/suolo && cp -r /tmp/suolo ../fase5-sito/sito/dati/suolo     # per guardare la pagina in locale
python -m pytest -q                                              # prove, niente rete
```

Servono `openpyxl` (o, più veloce, `python-calamine`, che il costruttore usa se c'è) e, solo per `agricolo.py`, `numpy`,
`rasterio`, `pyproj`, `shapely`: tutti già nell'immagine del server (fase 4). Sul server il lavoro `suolo` del worker fa
tutto da solo una volta al mese (README della fase 4, § «Suolo e aree agricole»).

## Fonti

- **ISPRA/SNPA, indicatori del consumo di suolo** `consumo_suolo_<anno>_Com_Prov_Reg_Naz_v<versione>.xlsx` (edizione 2026,
  v1.1 del 27/10/2026, 87 MB) nella cartella https://groupware.sinanet.isprambiente.it/uso-copertura-e-consumo-di-suolo/library/consumo-di-suolo/indicatori:
  un foglio per livello (Comuni, Province, Regioni, Nazionale) e anno (2006, 2012, 2015–2025) più gli anni rivisti
  (`2023_rev`, `2024_rev`). Campi usati: `csuolo1` suolo consumato, `csuolo8` netto, `csuolo10` lordo, `csuolo13`
  ripristini, `csuolox111…126` incrementi per classe, `pidrau4` pericolosità idraulica media P2, `pfrane3` + `pfrane4` frane
  P3 + P4, `ccoste4` 0–300 m dalla costa, `careep2` aree protette EUAP, `clammi3` superficie, `clammi4` popolazione.
  Report: Munafò M. (a cura di), 2026, *Consumo di suolo, ecosistemi urbani e stato del territorio. Edizione 2026*, Report
  ambientali SNPA 50/2026.
- **Carta dei cambiamenti** del consumo di suolo (`…/carta-nazionale-consumo-suolo-<anno>/cambiamenti-<a>-<b>/consumo_suolo_<a>-<b>.tif`,
  10 m, EPSG:7794, uint32, 155 MB): codici `2111…2126` = nuovo consumo (da suolo non consumato alla classe), `22xx`
  coperture non conteggiate, codici a 6 cifre = passaggi fra classi consumate (`122111` cantiere → edificio) o ripristini.
- **Carta nazionale di uso del suolo ISPRA** (`…/copertura-del-suolo/carta-di-copertura-del-suolo/uso-del-suolo-<anno>/Uso_del_suolo_<anno>.tif`,
  10 m, EPSG:3035, int16, 630 MB; ultima: 2023, integra Copernicus 2018 e la carta del consumo di suolo 2023): usi agricoli
  11 seminativi, 12 foraggere, 13 colture permanenti, 14 aree agroforestali, 16 altri usi agricoli; non agricoli 2 forestale,
  3 cave e miniere, 4 urbano e aree assimilate, 5 acque, 61 zone umide, 62 altri usi non economici.
- **ISTAT, stime congiunturali** «Coltivazioni: superfici e produzione» per provincia, SDMX `101_1015_DF_DCSP_COLTIVAZIONI_2`,
  `DATA_TYPE = ART` (superficie totale, ha), dal 2006 (18 MB in CSV, ~1 minuto).
- **ISTAT, 7° Censimento dell'agricoltura** (2020), SDMX `DF_DCAT_CENSAGRIC2020_SURF_ALL`, `ARU` (SAU) e `AA_UNUT`
  (superficie agricola non utilizzata) per comune.

Il groupware risponde senza login; il nome del file ISPRA contiene anno e versione e cambia a ogni edizione (v1.0 → v1.1 in
pochi giorni): `scarica.file_indicatori()` sceglie quello con l'anno e poi la versione più alti (confronto numerico: 1.10 >
1.9); `carte_recenti()` sceglie la cartella `carta-nazionale-consumo-suolo-<anno>` più recente, la sua cartella dei
cambiamenti e il file a 10 m (non quello a 2,5 m), e la carta d'uso più recente.

## File della pagina (uscita di `costruisci`)

`italia.json`:
- `voci`: `suolo` (sau, nonut, cons, idr, frane, coste, protette), `consumi` (edifici, strade, piazzali, cantieri, cave, fv,
  altro, nc = non attribuito), `colture` (cereali, industriali, ortive, avvicendate, prati, vite, olivo, frutta), con nome e
  colore; `censimento_voci` = 2 (le prime due voci di `suolo` vengono dal censimento 2020).
- `anni`: `suolo` (2006, 2012, 2015…2025), `consumi` (2012, 2015…2025), `colture` (2006…2025), `agricolo` (2025);
  `periodi`: anno del flusso → [carta iniziale, carta finale] (`"2012": [2006, 2012]`, `"2015": [2012, 2015]`, poi annuali);
  `rev`: anni con il valore rivisto (`["2023", "2024"]`).
- `italia` e `regioni` (codice, nome, posizione dell'istogramma): `sup` (ha), `pop` {anno}, `suolo` {anno: [7 voci]},
  `consumi` {anno: [8 voci]}, `bilancio` {anno: [lordo, ripristini, netto]}, `agricolo` {anno: [7 gruppi]}, `colture`
  {anno: [8 famiglie]}, `rev` {anno: suolo consumato rivisto}.
- `riferimenti` (ISPRA con titolo, edizione, versione, data, file, indirizzo, licenza e citazione; ISTAT; incrocio agricolo
  con metodo, usi e confronto ISMEA), `fonte`, `note` (avvisi del costruttore).

`RR.json`: `province` (stesse grandezze, con `sigla`; colture assenti in Sardegna) e `comuni` = {`anni`, `campi`, `dati`:
[codice della mappa, nome, provincia 2026, superficie, [suolo consumato per anno], [incremento netto per anno]]}.
Dimensioni con i dati veri: `italia.json` 83 kB, `RR.json` da 17 kB (Valle d'Aosta) a 320 kB (Lombardia), 2 MB in tutto.

## Scelte

- **Serie come le pubblica ISPRA** (decisione di Paolo): superfici dei fogli di ogni anno, anche il 2023 e il 2024 che
  l'edizione successiva ha rivisto; i valori rivisti vanno in `rev` e la pagina li segnala («rev» nel grafico e nel
  riquadretto). Italia: 2023 2.152.721 ha pubblicati, 2.149.607 rivisti; 2024 2.157.457 e 2.154.864.
- **Periodi**: il flusso dell'anno *t* è il periodo che finisce in *t*. I periodi lunghi 2006–2012 e 2012–2015 restano interi
  (nella pagina: somma nei periodi scelti, barra larga alta quanto la media annua nel grafico), non si spalmano sugli anni.
- **Pericolosità**: le aree idrauliche P1 ⊃ P2 ⊃ P3 sono annidate (Italia 2025: 474.221, 282.649, 104.369 ha consumati): si
  usa P2, lo scenario medio di riferimento; le frane P3 e P4 sono classi distinte e si sommano.
- **Non attribuito**: nel 2006–2012 la somma delle classi (39.376 ha) è minore del consumo lordo (63.598 ha): la differenza
  è la voce «non attribuito a una classe», così la colonna impilata è sempre il consumo lordo. Negli altri periodi la somma
  delle classi coincide con il lordo.
- **Comuni sardi**: ISPRA usa i codici nuovi (province 112–119), le mappe del sito quelli vecchi (090, 091, 092, 095, 111) e
  le sigle delle province vecchie: i 377 comuni si abbinano per nome nella regione; la tabella comune della mappa →
  provincia 2026 viene dall'elenco ISPRA e serve anche al censimento e all'incrocio agricolo.
- **Colture senza doppi conteggi**: ogni famiglia è fatta di concetti con alternative in ordine di preferenza (per esempio
  PGRAPM dal 2024, prima PERMGRASSE + POORINGS + OTHEZINGS + PGPNP; OLIVTAB_OIL e non anche OLIVO/OHROIE; WINEES e non le
  uve DOP/IGP); in ogni anno si usa la prima alternativa con dati. Verifiche: PGRAPM 2024 = somma esatta dei figli; somma
  delle famiglie 12,43 milioni di ha nel 2024 contro 12,54 di SAU del censimento 2020; regioni = Italia. Escluso un anno con
  molte meno voci del precedente (il 2026 provvisorio: 125 contro 189). Sardegna solo regionale (le province delle stime
  mescolano le vecchie e le nuove e non sommano al dato regionale). Voci nuove non assegnate → nota, non sommate.
- **Censimento**: SAU 12.431.808 ha, superficie non utilizzata 315.911 ha (Italia 2020), tutti i comuni assegnati.

## Suolo agricolo consumato (incrocio fatto da EuGEnio)

Decisione di Paolo: «facciamo noi i dati incrociando». `agricolo.py`:
1. legge la carta dei cambiamenti a strisce di 512 righe e tiene i pixel `2111…2126` (circa 1 milione su 12,5 miliardi);
2. porta il centro di ogni pixel da EPSG:7794 a EPSG:3035 e legge l'uso del suolo in quel punto (strisce di 1024 righe
   della carta d'uso, solo dove ci sono punti);
3. porta il centro in UTM 32N e lo assegna al comune delle mappe del sito (shapely, `STRtree`; fuori da ogni comune →
   il più vicino entro 500 m);
4. somma per comune nuovo consumo e parte agricola per gruppo di classi e per uso agricolo, poi regioni e Italia (le
   province le somma `costruisci` con la tabella comune → provincia 2026). Un pixel = 0,01 ha.

**Risultato per il 2024–2025** (carta `consumo_suolo_2024-2025.tif` × `Uso_del_suolo_2023.tif`, 22/11/2026, 70 secondi per
l'Italia intera): nuovo consumo 10.226 ha (Excel ISPRA: 10.243, −0,2 %, differenze di bordo), **di cui su suolo agricolo
6.904 ha (67 %)**: seminativi 5.130, colture permanenti 739, altri usi agricoli 553, foraggere 475, aree agroforestali 6.
Per gruppo: fotovoltaico a terra 2.575 su 2.797 (92 %, «quasi tutto» per ISPRA), cantieri 3.172 su 5.374, edifici 405 su
725, piazzali 324 su 616, cave e discariche 209 su 413, strade 195 su 269. Il resto del nuovo consumo era, nella carta
d'uso, urbano e aree assimilate 2.235 ha, altri usi non economici 587, forestale 400, cave 71, acque e zone umide 30.

**Confronto con ISMEA** (Rapporto SNPA 2026, consumo di suolo agricolo 2024–2025: 8.208 ha, l'80 %): la stima di EuGEnio è
l'84 % di quella ISMEA in Italia; per regione Lazio 1.232 contro 1.289 (96 %), Sicilia 1.285 contro 1.444 (89 %), Puglia 791
contro 878 (90 %), Lombardia 671 contro 832 (81 %), Piemonte 606 contro 694 (87 %). Lo scarto viene soprattutto dai 2.235 ha
che la carta d'uso classifica «urbano e aree assimilate» (lotti liberi, verde e aree di margine dentro le aree urbane di
Copernicus, che ISMEA conta in parte come agricoli) e dagli incolti («altri usi non economici»). La nostra è quindi una
stima prudente, con un metodo pubblico e ripetibile.

**Prototipo su poche regioni**: `--regioni 08,03` tiene solo i comuni di quelle regioni (la lettura della carta dei
cambiamenti resta intera: è la parte che costa, ~45 s).

**Ogni anno**: con la carta dei cambiamenti di una nuova edizione il worker rifà l'incrocio (`agricolo_<anno>.json` resta
nell'archivio) e `costruisci` unisce tutti i file: la serie cresce di un anno a ogni edizione. Finché ISPRA non pubblica una
carta d'uso più recente si usa la 2023 (per i cambiamenti successivi dice com'era usato il suolo prima del consumo).
Per gli anni passati servirebbero le carte dei cambiamenti delle edizioni precedenti, ma ogni edizione rivede l'anno prima:
non mescolarle senza un controllo (problema aperto).

## Controlli prima della pubblicazione (`costruisci`)

ValueError, e il worker lascia i file di prima e manda un'email: somme comuni = province = regioni = Italia per ogni foglio
(suolo consumato e consumo lordo, tolleranza 1 ha o un milionesimo; con i dati veri passano tutte); tutti i comuni ISPRA
abbinati alla mappa e tutte le province e regioni nella mappa; ultimo anno = anno dell'edizione − 1; con `precedente`
nessuna regione che cambi il suolo consumato di più del 2 % in un anno già pubblicato (salvo `forza`). Avvisi nelle `note`:
scarto oltre il 2 % fra il nuovo consumo dei pixel e quello dell'Excel, anni o voci ISTAT esclusi, codici sconosciuti.
Numeri di controllo con i dati veri (22/11/2026): Italia 2025 2.164.360,82 ha consumati, 7,19 % del territorio, 367 m² per
abitante; consumo 2024–2025 lordo 10.242,55 ha, ripristini 745,6, netto 9.496,95; fotovoltaico a terra +2.798 ha.

## Prove (`tests/`, niente rete)

- `campioni.py`: Excel nello stesso formato di ISPRA (Bologna, Imola, Aggius con il codice nuovo; anni 2006, 2012, 2015 e
  `2012_rev`), CSV SDMX delle colture e del censimento, un incrocio agricolo inventato.
- `test_costruisci.py`: valori, periodi, rev, non attribuito, SAU dei comuni sardi nelle province nuove, comuni, colture con
  le alternative, controlli (somme, edizione, comune non abbinato, scarto con i file pubblicati e `forza`), serie agricola
  su più anni, stesso risultato con openpyxl e con calamine.
- `test_scarica.py`: file con anno e versione più alti, scarico e «cambiati» con `httpx.MockTransport`, risposte sbagliate,
  carte più recenti.
- `test_agricolo.py`: due raster minuscoli costruiti nella prova (EPSG:7794 e EPSG:3035) a Bologna: nuovo consumo, parte
  agricola, codici esclusi, filtro per regione.

## Problemi aperti

1. Serie del suolo agricolo consumato solo per il 2024–2025: gli anni prima richiedono le carte dei cambiamenti delle
   edizioni precedenti (con le loro revisioni) o la carta di uso del suolo di altri anni (2012, 2018, 2022 sul groupware).
2. Scarto con ISMEA (84 %): chiedere a ISMEA o ISPRA (consumosuolo@isprambiente.it) quale strato agricolo usano.
3. Aree a pericolosità: ISPRA probabilmente usa le perimetrazioni attuali per tutti gli anni (la crescita misura il
   consumo, non il cambio delle mappe): da confermare con ISPRA.
4. SAU per comune: ISTAT attribuisce la superficie al comune del centro aziendale; per questo la pagina mostra SAU e
   superficie non utilizzata solo per provincia e regione.
5. Colture in Sardegna solo regionali; Monza, Fermo e Barletta-Andria-Trani hanno dati dal 2010 (prima nelle province
   d'origine).
6. Lettura dell'Excel sul server con openpyxl: 41 s per l'edizione 2026 (provato il 22/11/2026, file identici a quelli
   costruiti con `python-calamine`, che ci mette un secondo e si potrebbe aggiungere all'immagine).
