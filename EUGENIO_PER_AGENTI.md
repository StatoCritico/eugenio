# EuGEnio per agenti AI

> **Ultimo aggiornamento: 06/11/2026 – versione del sito `?v=20261106a`.**
> Regola di manutenzione: dopo ogni modifica alle funzioni, alle pagine o alle API di EuGEnio questo file si aggiorna
> (nella radice del repository e in `fase5-sito/sito/`, le due copie sono identiche) insieme a `fase5-sito/sito/llms.txt`,
> con data e versione del sito. Un test (`fase4-server/tests/test_agenti.py`) confronta i percorsi `/api/…` citati qui con
> le rotte reali dell'API, in tutti e due i sensi, e fallisce finché il file non è allineato.

*In English, briefly: EuGEnio (eugenio.statocritico.it) is a free, open source (AGPL-3.0) Italian web service for energy
managers: energy consumption forecasts with TiRex-2 and municipal weather, climate data for the Italian "Legge 10"
building energy reports, building portfolio geolocation, 3D buildings, solar and shading tools, health-sector energy cost
statistics. This file, written in Italian, tells an AI agent what each page and public API does, what it may and may not
automate, and how to cite the data. Free-to-use JSON APIs are listed in § 4; some routes require a human browser check
(Cloudflare Turnstile).*

Questo file serve a un agente AI (Claude, ChatGPT, Gemini, Copilot…) che deve usare EuGEnio **per conto di una persona**:
cosa c'è, come si usa, cosa può fare da solo con le API, cosa deve lasciare fare alla persona nel browser, come citare le
fonti e cosa non deve fare. È ricavato dal codice; se trovi una differenza tra questo file e il comportamento reale del sito,
vale il sito: segnalala (§ 10).

Indice: 1. Cos'è · 2. Licenze e come citare · 3. Mappa del sito, pagina per pagina · 4. API pubbliche · 5. Limiti e
protezioni · 6. Flussi tipici · 7. Cosa EuGEnio non fa · 8. Privacy, funzione per funzione · 9. File statici utili ·
10. Contatti e segnalazioni · 11. Da dove è ricavato questo file.

---

## 1. Cos'è

- **EuGEnio** («Eu» di Europa + «EGE», Esperto in Gestione dell'Energia) è il primo servizio online di **Stato Critico**,
  progetto personale e senza scopo di lucro di un energy manager del settore sanitario pubblico (titolare: Paolo Bianco).
- Indirizzo: `https://eugenio.statocritico.it` (sito statico + API sotto `/api/`). Codice: `https://github.com/statocritico/eugenio`.
- Gira su un server gratuito (Oracle Cloud, 2 CPU ARM, **senza GPU**): le risorse sono poche, usale con parsimonia.
- Lingua del sito e delle risposte dell'API: **italiano**. Numeri nell'API con il punto decimale; nei CSV scaricati
  separatore `;` e virgola decimale (per Excel in italiano).
- Copertura: i comuni italiani (codici ISTAT a 6 cifre, per esempio `099014` Rimini, `037006` Bologna). Più dati e più
  funzioni per l'**Emilia-Romagna** (regione `08`) e per la **sanità**. Il meteo di un comune può non essere ancora sul server:
  in quel caso le rotte rispondono 503 o 404 con un messaggio chiaro, non è un tuo errore.
- Stato: **servizio sperimentale**, risultati non ancora validati in modo sistematico. Non sostituisce i valori
  normativi, le visure ufficiali né il giudizio di un professionista. Dillo alla persona quando le dai i risultati.

## 2. Licenze e come citare

- **Codice**: AGPL-3.0. Chi offre online una versione modificata deve pubblicarne il codice.
- **Dati elaborati e report di EuGEnio**: CC BY 4.0. Formula obbligatoria nel documento che li usa:
  **«Fonte: EuGEnio – eugenio.statocritico.it»**, più le fonti originali indicate nel file o nella risposta (campi `fonte`,
  `licenza`, `citazione`, foglio «Info» degli Excel/ODS, ultime righe dei CSV, «Fonti e attribuzioni» dei PDF).
- **Nome e logo** («EuGEnio», «Stato Critico», logo e simbolo) non sono in licenza: si citano per dire la provenienza
  («basato su EuGEnio»), ma un servizio derivato deve avere nome e logo propri.
- **Attribuzioni delle fonti** (riportale quando usi i relativi dati):

| Dato | Attribuzione |
|---|---|
| Meteo e clima (previsioni, storico, Legge 10, gradi giorno) | Weather data by Open-Meteo.com (CC BY 4.0); ERA5: Copernicus Climate Change Service (C3S), ECMWF; ICON: Deutscher Wetterdienst (DWD); correzione ed elaborazioni: EuGEnio |
| Clima dal 1940 | ERA5 / ERA5-Land, Copernicus (C3S), tramite Open-Meteo (CC BY 4.0); elaborazione EuGEnio |
| Comuni, codici, confini | ISTAT (CC BY 4.0), confini tramite Gramscii |
| Indirizzi (civici) | ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0) |
| Particelle e geocodifica via Zornade | collegamento **«Dati elaborati da Zornade»** a `https://zornade.com` (obbligatorio, non basta la scritta) + fonti originali (Agenzia delle Entrate – catasto, ISTAT, OpenStreetMap ODbL) |
| Cartografia catastale (strato delle particelle) | Agenzia delle Entrate – Cartografia catastale, CC BY 4.0 (servizio WMS INSPIRE; linee ricolorate da EuGEnio) |
| Edifici Emilia-Romagna | Regione Emilia-Romagna – Database topografico regionale (DBTR), CC BY 4.0 |
| Edifici OpenStreetMap | © contributori OpenStreetMap (ODbL 1.0); archivio separato da quelli CC BY |
| Terreno e LiDAR ER | Regione Emilia-Romagna, DTM e prodotti LiDAR (CC BY 4.0) |
| Orizzonte lontano | Copernicus DEM GLO-90 (© DLR e Airbus, licenza Copernicus DEM), dai file di Open-Meteo.com (CC BY 4.0) |
| Ortofoto | la citazione della fonte scelta, restituita da `/api/ortofoto/fonti` (per esempio «Regione Emilia-Romagna – Ortofoto RER 2023-24 (CC BY 4.0)», «Sentinel-2 cloudless – https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) (CC BY 4.0)»); il Geoportale Nazionale è solo consultazione dal vivo e non va nei report |
| PVGIS | PVGIS © Unione europea, Joint Research Centre (JRC); riuso con citazione (decisione 2011/833/UE) |
| Fattori di emissione | ISPRA (CC BY 4.0) |
| Sanità | Ragioneria Generale dello Stato – OpenBDAP; Regione Emilia-Romagna – ReportER; ISTAT (CC BY 4.0) |
| Prezzi PMI | Eurostat (nrg_pc_205, nrg_pc_203), riuso con citazione |
| Gradi giorno e zone di legge | DPR 412/93, Allegato A (atto normativo, libero); abbinamento ai codici ISTAT: EuGEnio |
| Valori ricavati dagli anni tipo CTI (pagina Legge 10) | si possono **solo citare** (EuGEnio e CTI): non sono CC BY |

- I dati catastali (Zornade, visure) **non sostituiscono visure ed estratti ufficiali** dell'Agenzia delle Entrate.

## 3. Mappa del sito, pagina per pagina

Tutte le pagine stanno in `https://eugenio.statocritico.it/<pagina>`. Le pagine funzionano **in un browser con
JavaScript** (mappe con MapLibre/WebGL, calcoli nel browser). Un agente che non controlla un browser usa le API del § 4,
quando ci sono, oppure guida la persona passo passo.

Etichette di stato del menu: **S** = sperimentale (funziona, risultati da controllare); **triangolo giallo** = in sviluppo
(pagina descrittiva, nessun dato); **GME** = in attesa di autorizzazione dal GME (voce non cliccabile, pagina segnaposto).

Parametri dell'indirizzo comuni: `?regione=RR` (codice regione ISTAT a 2 cifre, predefinito `08`) sceglie la regione della
mappa in Previsioni, Patrimonio, Legge 10, Dati climatici, Ortofoto; `?vista=italia` apre la mappa grande su tutta Italia.

### Clima e meteo

| Pagina | URL e parametri | A cosa serve | Ingressi | Uscite | Stato |
|---|---|---|---|---|---|
| **Previsioni** | `/` (`index.html`), `?regione=RR` | Previsione dei consumi di un edificio con TiRex-2 dal suo storico, dal meteo previsto del comune e dal calendario; oppure **«Solo clima»**: le variabili meteo previste del comune, senza file | comune (mappa, elenco o indirizzo); file dei consumi; «energia per intervallo» (si somma) o «potenza o media» (si media); orizzonte «prossimi giorni, ora per ora» (fino a 15 giorni) o «prossimi mesi, giorno per giorno» (fino a 365); modo «prevedi il futuro» o «mettila alla prova sull'ultimo periodo»; variabili meteo | grafico con fasce di probabilità (quantili 10–90 %), schede delle variabili meteo, avvisi; report PDF, dati in Excel/ODS | sperimentale |
| **Legge 10** | `legge10.html`, `?comune=ISTAT`, `?regione=RR` | Dati climatici del comune dal clima reale delle ultime stagioni (5, 10 o 30): gradi giorno sul periodo della zona e sull'anno, zona risultante, tendenza per decennio, temperature di progetto, dati mensili come nella UNI 10349, confronto con l'Allegato A del DPR 412/93; clima dal 1940 | comune | grafici, tabelle; CSV/JSON; report PDF/Excel/ODS; CSV nazionali `dati/clima_sintesi.csv` e `dati/clima_stagioni.csv` | attiva |
| **Dati climatici** | `dati.html`, `?dataset=ID` (`meteo_orario`, `meteo_giornaliero`, `gradi_giorno`, `legge10`, `dpr412`, `comuni`, `eurostat_pmi`) | Scaricare dati ridistribuibili per comune, provincia, regione o Italia | dataset, grandezze, periodo, frequenza (oraria, giornaliera, mensile, annuale, per stagione), copertura minima, area | CSV, Excel (.xlsx), OpenDocument (.ods), con fonti e licenze | attiva (il download chiede la verifica anti-robot) |

Per la relazione tecnica ex Legge 10 restano **obbligatori i valori normativi** (UNI 10349, DPR 412/93): EuGEnio dà il clima
osservato come confronto. I prospetti UNI non sono pubblicati.

Formato del file dei consumi (Previsioni): CSV, `.xlsx` o `.ods` (primo foglio), **due colonne**: data/ora e valore,
separatore `;`, `,` o tabulazione, decimali col punto o con la virgola, date `AAAA-MM-GG hh:mm` o `GG/MM/AAAA hh:mm`
(ora italiana se senza fuso), almeno 30 valori, al massimo 200.000 righe e 5 MB. Dati quartorari o orari per la modalità
oraria (si riportano all'ora), giornalieri per quella giornaliera. Esempi: `esempi/esempio_orario_sintetico.csv`
(`data;kWh` / `27/06/2026 01:00;20,69`), `esempi/esempio_giornaliero_sintetico.csv` (`giorno,consumo` / `2024-01-23,1074.1`).

### Patrimonio

| Pagina | URL e parametri | A cosa serve | Ingressi | Uscite | Stato |
|---|---|---|---|---|---|
| **Patrimonio** | `patrimonio.html`, `?regione=RR`, `#valori` (scheda «Valori per sede») | Geolocalizzare un elenco di edifici: punto, particella catastale, comune; mappa 3D con i valori di ogni sede (consumi, costi) come barre; abbinare le visure lette da EuGEnio Visure; aprire una sede in Modelli 3D | file degli edifici (sotto) | mappa, esiti `ok` / `verificare` / `non_trovato`; CSV (`;`, BOM), GeoJSON con attribuzione; report PDF/Excel/ODS | attiva |
| **Ortofoto** | `ortofoto.html`, `?lat=…&lon=…&z=…` (predefinito Rimini, zoom 16), `&fonte=ID`, `?regione=RR` | Foto aeree come sfondo, con strati delle particelle catastali e dei contorni degli edifici; ricerca per indirizzo o per foglio e particella | luogo | mappa; immagine JPG/PNG/PDF con le attribuzioni | sperimentale |
| **LiDAR** | `lidar.html` | Descrive la ricostruzione di altezze e falde dai rilievi laser | — | — | in sviluppo |
| **Modelli 3D** | `modelli3d.html`, `?edificio=ID`, `?archivio=demo` (demo sintetica, edifici inventati), `?archivio=<percorso>` (altro archivio sotto `/edifici3d/`), `?sede=locale` (sede passata da Patrimonio nella memoria della scheda), `?modello=locale` (modello passato da Importa DXF/IFC) | Mappa 2D con ricerca e clic sull'edificio, poi «Genera il 3D»: corpi, edifici vicini, terreno, piani e superfici stimati | edificio scelto | vista 3D; immagine PNG/PDF; report dell'edificio | sperimentale: **oggi sul server c'è solo un archivio di prova** (OpenStreetMap, centro di Rimini); il DBTR dell'ER è in arrivo; altrove il 3D si genera solo dove ci sono le sagome |
| **Importa DXF/IFC** | `importa-dxf-ifc.html`, `?lat=…&lon=…&z=…` | Aprire un disegno DXF o un modello BIM IFC: corpi, altezze e falde ricavati **nel browser**, posa dal file, da un sistema di riferimento o con due punti; il risultato si apre in Modelli 3D | file DXF/IFC (oltre ~30 MB si converte sul PC) | modello in Modelli 3D; `.geojson` | sperimentale |
| **Visure** | `visure.html` | Descrive **EuGEnio Visure**, programma che gira sul PC (Windows `.exe`, Docker, `python -m visure`) e legge le visure catastali in PDF che la persona ha già | — | — | in sviluppo (lettore pronto, provato su visure sintetiche; programma per Windows da pubblicare) |

Formato del file del Patrimonio: CSV (`;` o `,`, UTF-8 o codifica di Windows), `.xlsx` o `.ods`; una riga per edificio,
al massimo 500 righe per caricamento (la pagina manda i file grandi a blocchi di 40 righe). Serve **almeno una** di
queste informazioni, in ordine di affidabilità: `lat` e `lon`; `comune`, `foglio`, `particella` (o `mappale`) [, `sezione`];
`indirizzo` [, `civico`], `comune`. Facoltative: `id`, `denominazione` (e qualunque altra colonna, riportata in uscita);
per le pagine dell'edificio anche `piani_fuori_terra`, `piani_interrati`, `superficie_lorda`, `superficie_netta`,
`superficie_catastale`, `anno_costruzione`. Nomi alternativi riconosciuti (per esempio `latitudine`, `via`, `mappale`,
`fg`, `nome`, `codice`, `SLP`). Esempio (`esempi/patrimonio_esempio.csv`):

```
id;denominazione;indirizzo;civico;comune;foglio;particella;lat;lon
H01;Ospedale Santa Maria delle Croci;Viale Vincenzo Randi;5;Ravenna;;;;
H06;Ospedale Marconi;;;Cesenatico;22;111;;
H08;Ospedale Nefetti;;;;;;43.942496;11.901527
```

Scheda «Valori per sede»: le colonne in più del file (per esempio `Energia elettrica 2025`, `Costo gas 2025`) diventano
valori da disegnare; una **seconda riga facoltativa con le unità** (`kWh`, `Smc`, `€`…). Esempio:
`esempi/valori_sedi_esempio.csv` (valori inventati). Colonne in uscita principali: `lat`, `lon`, `fonte_punto` (`ANNCSU`,
`Zornade`, `coordinate`, `catasto`), `indirizzo_trovato`, `istat`, `belfiore`, `foglio_catasto`, `mappale`, `esito`, `nota`.

### Edificio e Fotovoltaico (pagine 3D, stessi parametri di Modelli 3D: `?edificio=ID`, `?archivio=…`, `?sede=locale`)

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
| `edificio-geometria.html` – Geometria e luce naturale | volume, superfici, S/V, pareti esposte e in comune, cielo visto | edificio | sperimentale |
| `edificio-consumi.html` – Consumi, firma energetica e priorità | consumi al m² e al m³, firma energetica con i gradi giorno reali del comune, classifica delle sedi | consumi mensili, una riga per mese: `AAAA-MM;valore` | sperimentale |
| `edificio-fabbisogno.html`, `edificio-involucro.html`, `edificio-impianti.html` | fabbisogno con le metodiche UNI, facciate e tetti, pompe di calore e solare termico | — | in sviluppo: «analisi non disponibile in questa installazione» (modulo UNI non pubblico) |
| `edificio-cer.html` – Comunità energetiche | energia condivisa ora per ora per cabina primaria (solo energia, niente prezzi né incentivi) | CSV lungo `ora;sede;cabina;prelievo;immissione` in kWh (esempio `esempi/cer_esempio_sintetico.csv`); il codice della cabina lo scrive la persona | sperimentale |
| `edificio-clima.html` – Clima che cambia, `?istat=ISTAT` | tendenza dei gradi giorno dal 1940 e consumi attesi con la firma energetica | comune, stagione di partenza, carico di base e pendenza (facoltativi) | sperimentale |
| `edificio-obblighi.html` – Obblighi di legge | potenza minima di rinnovabili (D.Lgs. 199/2021), S/V, zona, limite di H'T del DM requisiti minimi | edificio | sperimentale |
| `fv-ombre.html` – Ombre e percorso del sole | ombre degli edifici vicini, ora per ora | edificio, giorno, ora | sperimentale |
| `fv-irradiazione.html` – Sole e irradiazione su tetti e facciate | irradiazione annua e stagionale con ombre e orizzonte fino a 25 km | edificio | sperimentale |
| `fv-producibilita.html` – Producibilità con le ombre | producibilità FV dei tetti con il clima orario del comune | aree FV disegnate o proposte, kWp, inclinazione, orientamento | sperimentale |
| `fv-pvgis.html` – Confronto con PVGIS | producibilità di EuGEnio accanto a PVGIS con lo stesso orizzonte | come sopra | sperimentale |
| `fv-dlgs199.html` – D.Lgs. 199/2021, Allegato III | potenza minima da rinnovabili per nuove costruzioni e ristrutturazioni, confrontata col FV possibile | edificio | sperimentale |
| `fv-leed.html` – Prefattibilità LEED | quali informazioni utili a LEED dà EuGEnio, tema per tema (descrittiva, nessun testo LEED) | — | sperimentale |
| `fv-mercato.html` | analisi di mercato su prezzi GME | — | **GME**: segnaposto |

Le altezze dell'archivio sono approssimate (circa ±3 m): piani, superfici, ombre e producibilità sono stime.

### Cogenerazione

| Pagina | A cosa serve | Stato |
|---|---|---|
| `cog-emissioni.html` – Emissioni | CO₂ evitata o aggiunta dal cogeneratore rispetto a rete elettrica e caldaia, con i fattori ISPRA; calcolo nel browser; ingressi: dati misurati di un anno (MWh elettrici, MWh termici, gas in MWh PCI o Sm³) oppure taglia, ore e rendimenti | sperimentale |
| `cog-spark-spread.html`, `cog-simulazione.html`, `cog-confronto.html`, `cog-rischio.html`, `cog-car.html` | analisi economiche su prezzi di mercato | **GME**: segnaposto |

### Statistiche

| Pagina | URL e parametri | A cosa serve | Stato |
|---|---|---|---|
| **Costi energetici Sanità** | `indicatori.html`, `?regione=RR`, `&ente=CE-COD` (per esempio `?regione=08&ente=080-101`, Azienda USL Piacenza; `080-999` = consolidato regionale) | spesa per energia degli enti del Servizio Sanitario Nazionale dal 2015, a confronto con regione e Italia, per giornata di degenza, posto letto, cittadino | attiva |

### Altre pagine

`metodo.html` (Come funziona: modello, fonti meteo, correzione ERA5, limiti; `#fonti`), `faq.html` (F.A.Q.; questo file è
spiegato in `#agenti-ai`), `sitografia.html` (progetti e dati usati), `mirror.html` (come installare una copia),
`licenza.html` (`#dati` per la CC BY), `privacy.html`, `contatti.html`. Newsletter mensile dei dati:
`https://notizie.statocritico.it/subscription/form` (l'iscrizione la fa la persona, non l'agente).

## 4. API pubbliche

Base: `https://eugenio.statocritico.it`. Tutte le risposte sono JSON (salvo i file). Errori: JSON `{"detail": "messaggio
in italiano"}`. Schema OpenAPI completo: **`/api/openapi.json`**, pagina interattiva **`/api/docs`**.

Nelle prove con curl usa sempre un **User-Agent identificabile** con un contatto, per esempio:

```bash
UA='MioAgente/1.0 (per conto di un utente; contatto: nome@esempio.it)'
curl -sS -A "$UA" https://eugenio.statocritico.it/api/salute
```

Legenda: **libera** = un agente può chiamarla direttamente; **Turnstile** = serve il gettone di sessione ottenuto da una
verifica anti-robot fatta in un browser vero (§ 5): un agente senza browser **non può** usarla in automatico.

### 4.1 Servizio e comuni

| Metodo e percorso | Accesso | Cosa restituisce |
|---|---|---|
| `GET /api/salute` | libera | `{"stato": "ok", "previsioni": {…ultimo aggiornamento…} \| null, "modello_caricato": bool, "previsioni_in_corso": n}` |
| `GET /api/protezione` | libera | `{"turnstile": chiave pubblica \| null, "intestazione": "X-EuGEnio-Sessione", "minuti": 30, "rotte": ["previsione", "patrimonio", "geocodifica", "particella", "estrazione"]}` |
| `POST /api/sessione` | solo browser | corpo `{"token": "<gettone Turnstile>"}` → `{"sessione": "…", "scade": epoch}` |
| `GET /api/comuni` | libera | elenco dei comuni con meteo: `[{"istat": "099014", "nome": "Rimini", "belfiore": "H294", "provincia": …, "lat": …, "lon": …, "svg_x": …, "svg_y": …}, …]` |
| `GET /api/mappa?giorni=7` | libera | gradi giorno previsti (base 20 °C), gradi giorno estivi (base 24 °C) e temperatura media dei prossimi `giorni` (1–15) per comune: `{"giorni": 7, "comuni": {"099014": {"t": 9.8, "gg": 71.4, "gc": 0.0}, …}}` |
| `GET /api/metodologia` | libera | metriche della correzione ERA5 → ICON e dei modelli meteo |

### 4.2 Meteo, clima e Legge 10

| Metodo e percorso | Accesso | Parametri | Risposta (estratto) |
|---|---|---|---|
| `GET /api/meteo/{istat}` | libera | `modalita=breve` (orario: ultimi `giorni` ≤ 90 osservati + previsione) o `modalita=lungo` (giornaliero, ultimi `giorni` ≤ 3650) | `{"storico": {"t": [...], "temperature_2m": [...], …}, "previsione": {…}}` (orari in Europe/Rome, ISO 8601) |
| `GET /api/clima-previsto/{istat}` | libera | `modalita=breve\|lungo`, `orizzonte` (ore 1–360 o giorni 1–365), `covariate` separate da virgola: orarie `temperatura, umidita, radiazione, diffusa, vento, nuvolosita, pioggia, neve`; giornaliere anche `gradi_giorno, gradi_raffrescamento` | `{"solo_clima": true, "passo": "ora", "storico": {"t": [...]}, "previsione": {"t": [...], "fonte_meteo": ["ICON-2I", …]}, "clima": {"temperatura": {"unita": "°C", "storico": [...], "previsione": [...]}}, "avvisi": [...]}` |
| `GET /api/clima-legge10/{istat}` | libera | `anni` = stagioni complete da usare (3–30, predefinito 10) | `{"istat", "comune", "stagioni": [...], "mensili": [...], "gradi_giorno": {"zona_di_riferimento", "gg_periodo_zona", "gg_anno_intero", "zona_risultante", "per_stagione": {...}, "tendenza_gg_per_decennio", …}, "temperatura_progetto": {"invernale", "estiva", "metodo"}, "avvertenza", "fonte"}` |
| `GET /api/edifici/gradi-giorno/{istat}` | libera | `dal=AAAA-MM`, `al=AAAA-MM` | `{"mesi": [{"mese": "2025-01", "gg20": 512.3, "gc24": 0.0, "t_media": 4.1, "giorni": 31}, …], "fonte", "nota"}` (clima reale, **non** i valori di legge) |
| `GET /api/edifici/clima-orario/{istat}` | libera | `anno=AAAA` (se manca, l'ultimo completo) | un anno orario UTC: `{"anno", "inizio", "passo_ore": 1, "ghi": [...], "dhi": [...], "t": [...], "vento": [...], "fonte"}` (W/m², °C, km/h) |

Esempi:

```bash
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-legge10/099014?anni=10"
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-previsto/099014?modalita=lungo&orizzonte=30&covariate=temperatura,gradi_giorno"
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/edifici/gradi-giorno/099014?dal=2024-07&al=2025-06"
```

### 4.3 Previsione dei consumi

| Metodo e percorso | Accesso | Parametri (multipart/form-data) |
|---|---|---|
| `POST /api/previsione` | **Turnstile** | `file` (CSV/xlsx/ods, formato del § 3), `istat`, `modalita=breve\|lungo`, `orizzonte` (ore ≤ 360 o giorni ≤ 365), `tipo=energia\|potenza`, `covariate` (come sopra), `verifica=true\|false` |

Risposta: `{"modalita", "passo", "istat", "covariate": [...], "storico": {"t": [...], "v": [...]}, "previsione": {"t": [...],
"0.1": [...], …, "0.5": [...], …, "0.9": [...], "fonte_meteo": [...]}, "avvisi": [...], "clima": {…}}`; con `verifica=true`
anche `"verifica": {"reale", "mae", "wape", "bias", "copertura_80"}`. La mediana è il quantile `0.5`; tra `0.1` e `0.9` c'è
l'80 % di probabilità. Oltre 72 ore il meteo viene dal modello globale IFS; oltre 15 giorni dalla climatologia (scenario
«anno tipo»). **Un agente senza browser non può chiamarla**: prepara il file e fai caricare il file alla persona nella pagina.

### 4.4 Dati climatici scaricabili

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/storici/catalogo` | libera | dataset presenti, grandezze, frequenze, periodi, fonti, licenze, limiti, elenco dei dati **non** scaricabili |
| `POST /api/storici/stima?formato=csv\|xlsx\|ods` | libera | righe e dimensione stimate per una selezione, `consentito` sì/no e suggerimenti per ridurla |
| `POST /api/storici/estrai?formato=csv\|xlsx\|ods` | **Turnstile** | il file (CSV in streaming; Excel e ODS con il foglio «Info») |

Corpo JSON di stima ed estrazione:

```json
{"dataset": "gradi_giorno", "variabili": ["gg20", "gc24"], "dal": "2024-07-01", "al": "2025-06-30",
 "frequenza": "mensile", "copertura": 90,
 "area": {"tipo": "comuni", "comuni": ["099014", "037006"]}}
```

`area.tipo`: `tutti`, `regione` (con `"regione": "08"`), `provincia` (con `"provincia"`: codice ISTAT a 3 cifre),
`comuni` (con l'elenco), `solo_capoluoghi`: true/false. Per `legge10`: `stagioni` (3–30) e `tipologia` (`mensili`,
`riepilogo`, `stagioni`). Per `eurostat_pmi`: `tassazione` (`X_TAX`, `X_VAT`, `I_TAX`). Le grandezze valide di ogni dataset
sono nel catalogo. Qualsiasi nome che richiami dati di mercato, Zornade o ANNCSU risponde **403**.

```bash
curl -sS -A "$UA" -H "Content-Type: application/json" -X POST \
  "https://eugenio.statocritico.it/api/storici/stima?formato=csv" \
  -d '{"dataset":"gradi_giorno","variabili":["gg20"],"frequenza":"mensile","dal":"2024-07-01","al":"2025-06-30","area":{"tipo":"comuni","comuni":["099014"]}}'
```

### 4.5 Patrimonio, geocodifica, catasto

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `POST /api/converti` | libera | `file` (.xlsx o .ods) → `{"formato", "fogli": [...], "foglio_usato", "csv": "…"}` (primo foglio, separatore `;`); i CSV tornano come sono |
| `POST /api/patrimonio` | **Turnstile** | `file` (formato del § 3, ≤ 500 righe) → `{"riepilogo", "geojson", "righe": [...], "fonte", "fonte_url", "fonti"}` |
| `GET /api/geocodifica?q=…&comune=…` | **Turnstile** | `{"risultati": [{"etichetta", "lat", "lon"}], "fonte": "Dati elaborati da Zornade", "fonte_url"}` |
| `GET /api/particella?lat=…&lon=…` | **Turnstile** | `{"particella": {"id", "etichetta", "area_m2", "lat", "lon"}, "comune": {"belfiore", "nome", "istat", "disponibile"}, "fonte", "fonte_url"}` |

Queste rotte consumano la quota gratuita di Zornade condivisa da tutti gli utenti: **mai** usarle per estrazioni massive.

### 4.6 Ortofoto, strati, orizzonte, PVGIS

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/ortofoto/fonti` | libera | fonti accese con `id`, nome, licenza, citazione, stato, zoom, riquadro |
| `GET /api/ortofoto/{fonte}/{z}/{x}/{y}.{ext}` | libera, con limite | tessera 256×256 in EPSG:3857 (XYZ); `ext` = estensione della fonte (`jpg`); 404 fuori zona o fuori zoom |
| `GET /api/ortofoto/strati` | libera | strati accesi: `catasto` (particelle AdE), `dbtr_edifici`, `osm_edifici` |
| `GET /api/ortofoto/strati/{sid}/{z}/{x}/{y}.{ext}` | libera, con limite | PNG trasparente (zoom 16–20) o, per `osm_edifici`, GeoJSON delle sagome a zoom 16 (`.json`) |
| `GET /api/edifici/orizzonte?lat=…&lon=…&h=…&direzioni=72` | libera, con limite | orizzonte del terreno fino a ~25 km dal Copernicus DEM: `{"angoli": [...], "distanze_km": [...], "quota_dem", "raggio_km", "fonte"}`; `direzioni` ∈ 36, 72, 120, 360; solo Italia |
| `POST /api/edifici/pvgis` | libera, con limite | confronto con PVGIS (JRC) per 1–12 aree; corpo sotto |

```json
{"lat": 44.0594, "lon": 12.5683,
 "aree": [{"id": "tetto-sud", "kwp": 20, "inclinazione": 15, "orientamento": 180, "perdite": 14,
           "orizzonte": [2.1, 3.0, 4.5, 5.0, 3.2, 1.0]}]}
```

`orientamento` in gradi da nord (180 = sud); `orizzonte` = angoli in gradi da nord in senso orario, passo costante.
Risposta: per area `con_orizzonte` e `senza_orizzonte_utente` con `kwh_anno`, `kwh_mensili`, `irradiazione_piano`,
`banca_dati`, `anni`. Le tessere sono pensate per la mappa del sito: **non scaricare intere zone** di ortofoto o strati.

### 4.7 Report e analisi

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/report/schema` | libera | schema JSON del documento generico |
| `POST /api/report?formato=pdf\|xlsx\|ods` | libera | documento generico (JSON secondo lo schema) → file |
| `POST /api/report/{tipo}?formato=pdf\|xlsx\|ods` | libera | report di un servizio dalla **risposta JSON già ottenuta**: `tipo` = `previsione`, `legge10`, `patrimonio` (`{"righe": [...], "fonti": [...]}`), `indicatori`, `valori_sedi`, `edificio` |
| `GET /api/analisi/stato` | libera | analisi avanzate disponibili su questo server (oggi tutte «analisi non disponibile in questa installazione») |
| `POST /api/analisi/{id}` | libera | esegue un'analisi se disponibile; altrimenti 503 |

Word (docx) e ODT rispondono **410**. Corpo ≤ 5 MB. Esempio, PDF della Legge 10:

```bash
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-legge10/099014" -o l10.json
curl -sS -A "$UA" -H "Content-Type: application/json" -X POST --data @l10.json \
  "https://eugenio.statocritico.it/api/report/legge10?formato=pdf" -o legge10_rimini.pdf
```

### 4.8 Codici di risposta

| Codice | Significato |
|---|---|
| 200 / 304 | ok (le tessere usano ETag) |
| 400 | richiesta malformata (formato o tipo di report sconosciuto, corpo vuoto) |
| 401 | manca la sessione anti-robot (intestazione `X-EuGEnio-Verifica: 1`): serve il browser |
| 403 | dato non scaricabile (mercato, Zornade, ANNCSU) o verifica non superata |
| 404 | comune non disponibile, tessera fuori zona, analisi sconosciuta |
| 410 | formato spento (docx, odt) |
| 413 | file o richiesta troppo grandi (riduci periodo, area o righe: la stima dice come) |
| 422 | dati non validi (messaggio in italiano: leggilo e correggi) |
| 429 | limite orario superato per la tua rete: **aspetta**, non ritentare a raffica |
| 502 | la fonte esterna (ortofoto, PVGIS, Zornade) non risponde |
| 503 | dati non ancora sul server, server occupato (previsioni, file), quota di Zornade dell'ora esaurita, fonte molto richiesta (con `Retry-After`) |

## 5. Limiti e protezioni (cosa un agente può e non può fare)

- **Limiti per rete in finestra mobile di un'ora** (IPv4 per indirizzo, IPv6 per rete /64), valori predefiniti: rotte dei
  dati (comuni, mappa, meteo, clima, Legge 10, gradi giorno, catalogo delle ortofoto e degli strati, analisi) **600**
  richieste; previsioni **20**; conversioni **200**; report **60**; stime di Dati climatici **600**; download di Dati
  climatici **30**; edifici geolocalizzati **2.000**; ricerche Zornade **120**; tessere di ortofoto e strati **3.000**;
  confronti PVGIS **60**; profili d'orizzonte **120**; verifiche anti-robot **60**. Oltre: **429**.
- **Cloudflare** ferma le raffiche su `/api/` (circa 60 richieste in 10 secondi per IP, blocco breve; le ortofoto escluse).
- **Tetti per tutto il sito**: due previsioni alla volta (le altre aspettano fino a 30 s, poi 503); due report e due file di
  Dati climatici alla volta; quota oraria di Zornade condivisa (oltre: 503); ritmo verso le fonti di ortofoto e verso PVGIS.
- **Verifica anti-robot (Cloudflare Turnstile)** sulle rotte che costano o consumano quote: `previsione`, `patrimonio`,
  `geocodifica`, `particella`, `estrazione` (cioè `POST /api/previsione`, `POST /api/patrimonio`, `GET /api/geocodifica`,
  `GET /api/particella`, `POST /api/storici/estrai`). La pagina ottiene un gettone Turnstile nel browser, lo scambia con
  `POST /api/sessione` e manda la sessione (30 minuti, legata alla rete) nell'intestazione `X-EuGEnio-Sessione`.
  **Un agente non deve aggirarla** (niente risolutori di captcha, niente riuso di gettoni altrui): o guida la persona a
  usare la pagina, o lavora in un browser che la persona controlla e vede, oppure usa un proprio **mirror** (§ 7), dove
  la verifica è spenta.
- **Pagine che richiedono un browser**: Previsioni (caricamento), Patrimonio, Modelli 3D e tutte le pagine 3D (WebGL),
  Ortofoto, Importa DXF/IFC, Comunità energetiche, Clima che cambia, Emissioni, Costi energetici Sanità (calcoli nel
  browser). Le rotte libere del § 4 bastano per meteo, clima, Legge 10, gradi giorno, stime, orizzonte, PVGIS e report.
- **Cache**: le tessere di ortofoto e strati hanno `Cache-Control: public` e `ETag` (usa `If-None-Match`); orizzonte e
  PVGIS sono tenuti in copia dal server (stesso punto, nessuna nuova chiamata). Le previsioni meteo cambiano più volte
  al giorno; lo storico una volta al giorno. **Tieni tu una copia** delle risposte che riusi, invece di richiederle.
- **Uso cortese**: User-Agent identificabile con un contatto; richieste in serie, non in parallelo; pause di almeno un
  secondo tra le chiamate pesanti; niente scraping massivo di pagine, tessere o comuni (per molti comuni usa
  `POST /api/storici/stima` ed `estrai` con un'area, o i CSV nazionali del § 9); rispetta 429 e `Retry-After`; non usare EuGEnio come
  intermediario gratuito verso Zornade, PVGIS o le fonti di ortofoto.

## 6. Flussi tipici, passo passo

**A. Previsione dei consumi di un edificio a Rimini da un CSV orario**
1. Controlla che il comune ci sia: `GET /api/comuni` → Rimini `099014`.
2. Prepara il file: due colonne, `data;kWh`, una riga per ora (o per quarto d'ora), almeno qualche settimana di storia
   (fino a 90 giorni usati), date `GG/MM/AAAA hh:mm` o ISO, ora italiana.
3. La persona apre `https://eugenio.statocritico.it/`, sceglie Rimini sulla mappa, carica il file, sceglie «energia per
   intervallo», «Prossimi giorni, ora per ora», l'orizzonte (per esempio 72 ore) e «Calcola la previsione» (la verifica
   anti-robot è di solito invisibile).
4. Per giudicare l'affidabilità: modo «Mettila alla prova sull'ultimo periodo» (`verifica`), che dà MAE, WAPE, bias e
   copertura dell'intervallo 80 %.
5. Scarica il report (PDF) o i dati (Excel/ODS) dalla pagina; cita «Fonte: EuGEnio – eugenio.statocritico.it» e Open-Meteo.

**B. Dati climatici per la Legge 10 di un comune**
1. Trova il codice ISTAT (`GET /api/comuni`).
2. `GET /api/clima-legge10/{istat}?anni=10` (o 5, 30).
3. Confronta con i valori di legge in `dati/dpr412.json` (gradi giorno, zona, altitudine dell'Allegato A del DPR 412/93).
4. PDF: `POST /api/report/legge10?formato=pdf` con la risposta del passo 2. Link per la persona:
   `https://eugenio.statocritico.it/legge10.html?comune=<istat>`.
5. Ricorda alla persona che nella relazione tecnica restano obbligatori i valori normativi (UNI 10349, DPR 412/93).

**C. Solo clima (nessun file)**: `GET /api/clima-previsto/{istat}?modalita=breve&orizzonte=72&covariate=temperatura,radiazione,umidita`
(prossime ore) o `modalita=lungo&orizzonte=90` (prossimi giorni, con la climatologia oltre il 15° giorno). Nella pagina:
Previsioni → «Solo il clima, senza consumi».

**D. Gradi giorno**: mensili reali di un comune con `GET /api/edifici/gradi-giorno/{istat}?dal=…&al=…`; per più comuni o
frequenze diverse `POST /api/storici/stima` con il dataset `gradi_giorno` e poi la pagina `dati.html?dataset=gradi_giorno`
(il download chiede la verifica); serie dal 1940 per stagione: `dati/clima_stagioni.csv`. Sono gradi giorno dal clima reale
(base 20 °C su tutto l'anno; estivi base 24 °C); quelli **di legge** sono in `dati/dpr412.json` e nel dataset `dpr412`.

**E. Patrimonio con geolocalizzazione**
1. Prepara il CSV del § 3 (coordinate, oppure foglio e particella, oppure indirizzo e comune; meglio un `id` stabile).
2. Se è un Excel, va bene così: la pagina lo converte (`/api/converti`).
3. La persona lo carica in `patrimonio.html`: la pagina lo manda a blocchi, mostra gli esiti, permette di scaricare CSV e
   GeoJSON. Le righe `verificare` e `non_trovato` vanno controllate a mano (la colonna `nota` dice il motivo).
4. Per i valori di ogni sede (consumi, costi) usa la scheda «Valori per sede» (`patrimonio.html#valori`).
5. Cita ANNCSU e, per le particelle, «Dati elaborati da Zornade» con il collegamento.

**F. Modello 3D e producibilità FV di un edificio**
1. `modelli3d.html`: cerca l'indirizzo, fai clic sull'edificio, «Genera il 3D» (oggi solo dove c'è un archivio di
   sagome: archivio di prova del centro di Rimini; altrove compare un messaggio). Per vedere il funzionamento:
   `modelli3d.html?archivio=demo` (edifici inventati: non usarli come risultati).
2. Correggi gronda, colmo, piani; poi `fv-producibilita.html` (stesso edificio): aree FV, kWp, inclinazione, orientamento.
3. Confronto: `fv-pvgis.html`, o direttamente `GET /api/edifici/orizzonte` + `POST /api/edifici/pvgis`.
4. Obblighi: `fv-dlgs199.html` ed `edificio-obblighi.html`. Ricorda che altezze e superfici sono stime.

**G. Importare un DXF/IFC**: `importa-dxf-ifc.html?lat=…&lon=…&z=…`; il file resta nel browser; posa dal file, da un sistema
di riferimento (EPSG) o con due punti noti; «Apri in Modelli 3D» (passa per `modelli3d.html?modello=locale`) o scarica il
`.geojson`. File oltre ~30 MB: sul PC con `EuGEnioVisure.exe modello` o con `python -m edifici3d importa-modello` (fase 10).

**H. Visure catastali con EuGEnio Visure, in locale**
1. La persona scarica da sé le visure in PDF (area riservata dell'Agenzia delle Entrate o SISTER): EuGEnio non lo fa e
   non chiede credenziali.
2. Sul PC: `EuGEnioVisure.exe` (quando pubblicato) oppure, dal codice, `python -m visure leggi CARTELLA_VISURE
   --patrimonio patrimonio.csv --ordina` (cartella `fase11-visure`) o la pagina locale `python -m visure web`
   (`http://127.0.0.1:8770`, solo sul computer).
3. Risultati in `Visure_AAAA-MM-GG/`: `indice.csv`, `edifici_visure.csv` o `patrimonio_con_visure.csv` (colonne `visura_…`:
   piani, superficie catastale, categorie). Intestatari e codici fiscali **non** entrano nei file.
4. Caricarli in `patrimonio.html`, passo «Visure catastali»: l'abbinamento si fa nel browser.

**I. Costi energetici della sanità**: `indicatori.html?regione=08&ente=080-101`, oppure i file `dati/indicatori/indice.json`
(anni, voci di conto economico, fonti, citazione) e `dati/indicatori/RR.json` (enti della regione con le serie). Cita
OpenBDAP (RGS), ReportER e ISTAT, più EuGEnio.

## 7. Cosa EuGEnio non fa e non deve fare

- **Dati di mercato (GME, EEX)**: PUN, prezzi zonali, PSV, IGI, TTF, future, PFOR **non sono mai esposti** né scaricabili:
  sono solo per uso interno. Non cercarli nelle API, non provare nomi alternativi (risposta 403), non chiederli.
  Le pagine «GME» restano segnaposto finché non c'è una licenza scritta del GME.
- **Visure e persone**: è vietato usare i dati catastali per **re-identificare persone**. EuGEnio Visure toglie intestatari
  e codici fiscali; non chiedere né ricostruire chi possiede un immobile. Il sito non usa mai lo SPID della persona.
- **Norme UNI**: il modulo con le metodiche UNI non è pubblico; le analisi che lo richiedono dicono «analisi non
  disponibile in questa installazione». EuGEnio non pubblica prospetti o estratti di norme UNI, né testi LEED, né contenuti
  GSE (licenza incompatibile).
- **Zornade**: niente estrazioni massive tramite EuGEnio (la quota è condivisa e un abuso fa sospendere la chiave del
  servizio); i dati catastali non sostituiscono visure ed estratti ufficiali; il collegamento «Dati elaborati da Zornade»
  è obbligatorio.
- **Valori normativi**: EuGEnio non sostituisce UNI 10349, DPR 412/93, APE, progetti o diagnosi firmate.
- **Garanzie**: nessuna; servizio gratuito e sperimentale.
- **Uso intensivo**: per lavori grandi o ripetuti la strada giusta è un **mirror** (codice AGPL-3.0, istruzioni in
  `mirror.html` e nel repository): sul proprio server la verifica anti-robot è spenta e i limiti si scelgono.

## 8. Privacy, funzione per funzione

| Funzione | Cosa va al server di EuGEnio | Cosa resta nel browser o sul PC |
|---|---|---|
| Previsioni con file | il file dei consumi (elaborato in memoria e scartato) e il comune | — |
| Solo clima, Legge 10, gradi giorno, Dati climatici | solo comune e filtri | — |
| Patrimonio | il file degli edifici, a blocchi (indirizzi cercati nell'ANNCSU sul server, il resto e le particelle a Zornade, che riceve solo il testo dell'indirizzo, i dati catastali o le coordinate); scartato a fine elaborazione; le risposte di Zornade in una cache tecnica senza legame con chi ha cercato, cancellata dopo 12 mesi | colonne `visura_…` e valori per sede |
| Excel/ODS in qualunque pagina | il file, per la conversione in CSV (non salvato) | — |
| Ricerca di un luogo (Ortofoto, Modelli 3D) | indirizzo o foglio e particella, come Patrimonio | — |
| Ortofoto e strati | le coordinate delle tessere viste | — |
| Modelli 3D, Edificio, Fotovoltaico | comune (clima), punto (orizzonte), aree FV e punto (PVGIS, inoltrati al JRC); per la firma energetica solo il periodo, non i consumi | consumi mensili, correzioni, modello importato |
| Importa DXF/IFC | nulla (solo le tessere della mappa) | il file DXF/IFC |
| EuGEnio Visure | nulla: gira sul PC o sul server dell'ente | visure in PDF, risultati |
| Comunità energetiche, Clima che cambia, Emissioni, Costi energetici Sanità | nulla dei dati della persona (si leggono file pubblici e l'elenco dei comuni) | curve orarie, firma, dati del cogeneratore |
| Report | i risultati da impaginare (generati in memoria, non salvati) | — |
| Contattaci | nulla: prepara l'email nel programma di posta | — |

Sempre: indirizzo IP e richieste nei registri del server per 14 giorni; contatori dei limiti in memoria. Dettagli:
`privacy.html`. Prima di caricare dati di altri (per esempio consumi di un'abitazione), l'agente ricorda alla persona che
deve avere il diritto di usarli.

## 9. File statici utili (si leggono senza API)

| File | Contenuto |
|---|---|
| `/dati/dpr412.json`, `/dati/dpr412.csv` | Allegato A del DPR 412/93 per codice ISTAT attuale: gradi giorno, zona, altitudine, note su fusioni |
| `/dati/clima_sintesi.csv` | clima dal 1940, una riga per comune (≈1 MB) |
| `/dati/clima_stagioni.csv` | gradi giorno e zona per comune e stagione dal 1940 (≈31 MB: scaricalo una volta sola) |
| `/dati/clima/regioni.json`, `/dati/clima/RR/ISTAT.json`, `/dati/clima/RR/ISTAT_mensili.json` | clima dal 1940 del comune (sintesi e mensili) |
| `/dati/indicatori/indice.json`, `/dati/indicatori/RR.json` | indicatori di spesa energetica della sanità |
| `/dati/ispra_fattori_emissione.json` | fattori di emissione ISPRA usati nella pagina Emissioni |
| `/esempi/*.csv` | file di esempio **inventati** (consumi, patrimonio, valori per sede, CER) |
| `/edifici3d/archivi.json` | archivi di edifici 3D presenti sul server (PMTiles letti dalla pagina) |
| `/llms.txt` | rimando breve a questo file |

## 10. Contatti e segnalazioni

- Pagina **Contattaci**: `https://eugenio.statocritico.it/contatti.html` (prepara un'email per `eugenio@statocritico.it`).
- Privacy: `privacy@statocritico.it`.
- Errori nel codice o in questo file: **issue su GitHub** `https://github.com/statocritico/eugenio/issues`, con pagina o
  rotta, parametri, risposta ricevuta e data. Un agente può preparare il testo; l'invio lo fa la persona.

## 11. Da dove è ricavato questo file

Per aggiornarlo, rileggi: `fase4-server/servizio/app.py` e i router `storici.py`, `edifici.py`, `ortofoto.py`, `strati.py`,
`pvgis.py`, `orizzonte.py`, `analisi.py` (rotte e parametri; `interno.py` è riservato e non va citato);
`fase4-server/servizio/protezione.py` e `config.py` (limiti, Turnstile); `modello.py` (CSV e risposta delle previsioni);
`report_servizi.py` (tipi di report); `fase7-territorio/territorio/patrimonio.py` (colonne del Patrimonio);
`fase5-sito/parti/testata.html` (menu e stati); `fase5-sito/sito/*.js` (parametri dell'indirizzo: `URLSearchParams`);
`fase5-sito/sito/privacy.html` e `licenza.html`; `fase10-edifici3d/ortofoto/*.toml` (fonti e citazioni); README delle
fasi 4, 5, 7, 10, 11, 12, 13. Il test `fase4-server/tests/test_agenti.py` controlla che le due copie siano identiche, che la
versione in testa sia quella del sito e che i percorsi `/api/…` citati qui e le rotte pubbliche dell'app coincidano.
