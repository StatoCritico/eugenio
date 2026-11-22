# EuGEnio per agenti AI

> **Ultimo aggiornamento: 22/11/2026 (nuova pagina sperimentale **Statistiche › Suolo e aree agricole** (`suolo.html`: suolo consumato, nuovo consumo per causa con la parte su suolo agricolo e superfici coltivate per regione, provincia e comune, dati ISPRA/SNPA e ISTAT); in **Territorio › Edifici pubblici** la scheda **«Per ente»** (`edifici-pubblici.html?modo=enti`, fino a 8 enti con un colore ciascuno, rotte `/api/immobili-pa/ente/{chiavi}`); in **Produzione e consumi di elettricità** il **periodo** a due indicatori (`&inizio=AAAA&fine=AAAA`: flussi sommati sul periodo, fattori come rapporto delle somme, capacità e burden sharing all'anno finale con la variazione dall'iniziale) – versione del sito `?v=20261122a`; 21/11/2026 b: in **Statistiche › Produzione e consumi di elettricità** la scelta **Emissioni** (`elettricita.html?modo=emissioni`): anelli della produzione per fonte in ogni regione e provincia, fattore di emissione medio e del termoelettrico ed energia primaria del termoelettrico per regione, zona di mercato e Italia dal 2000, confronto con ISPRA e con 0,187 tep/MWh – versione del sito `?v=20261121b`; 21/11/2026 mattina: pagine sperimentali **Statistiche › Produzione e consumi di elettricità** (`elettricita.html`) e **Statistiche › Carichi elettrici** (`carichi.html`) con i dati di Terna, usati per le elaborazioni e **non scaricabili**; **collegamento a questa simulazione** in fondo alle pagine a scelte; numeri col punto delle migliaia in tutte le pagine; Comunità energetiche con le aree del GSE accese in partenza – versione del sito `?v=20261121a`; 20/11/2026 (mattina: «Annulla iscrizione» dei programmi di posta su ogni email di EuGEnio porta a EuGEnio e non blocca più l'indirizzo, rotte `/api/email/via-tutto` e `/api/email/servizio`, messaggio chiaro se l'indirizzo è bloccato dal servizio di posta; 19/11 sera: foglio psicro_UTA.xlsx v2.3 con la grafica originale dei diagrammi; ortofoto AGEA solo fino allo zoom 18, niente più scacchiere nella vista 3D; Cabine primarie con una sola mappa, «Sposta» / «Scegli punti», cabine di tutta Italia e confini sommati per ogni punto; 07/11 sera, dopo le prime prove: tetti stimati dal colmo, ricerca nella colonna destra e per solo comune, ortofoto RER trasparente dove non ha dati, camera 3D sopra il terreno; 08/11: frecce per spostare l'ortofoto di 1 m, parametri `de`/`dn` delle tessere; tetti ipotizzati 22°/32° e «Forma dei tetti»; sagome regionali del Veneto con le altezze OSM; terreno da più DTM, anche il Veneto; menu dell'08/11: gruppo Edifici, pagine dei gruppi Edifici, Cogenerazione e Fotovoltaico «in lavorazione» e non accessibili dal menu, «Cambiamento climatico» in Clima e meteo, mappe che si aprono su Cesena; edifici dei DB topografici anche per 15 città fuori dall'Emilia-Romagna (Napoli con le classi di altezza Copernicus) e sagome regionali al volo anche in Sardegna e Campania; 09/11: Roma, Bari e Bologna per il comune intero, 69 archivi di edifici (54 DBTR dell'Emilia-Romagna); colore degli edifici e alberi in Modelli 3D, ricerca con Comune prima dell'Indirizzo e «Reset», tutti i comuni italiani nella ricerca per comune, clic sulla mappa che non sposta la vista, limiti per IP solo sulle tessere chieste alla fonte e 429 con `Retry-After`, Previsioni non più sperimentale; 09/11 b: ricerca con **un solo Comune** in cima, Indirizzo, Foglio e Particella e un solo «Reset», risultati in un altro comune scartati; «Colore» e «Alberi» sotto la mappa accanto ad «Azzera»; celle LiDAR chieste solo se esistono; quote del terreno Copernicus anche per gli edifici OSM e le sagome regionali; tessere segnaposto delle ortofoto trattate come vuote; 09/11 c: **tutti i tetti partono piani**, sezione «Coperture» con la tegola per scegliere i tetti a falde (inclinazione, «Reset piani», esporta e importa, scelte nel browser), niente più ipotesi automatica 22°/32° né falde LiDAR o dal colmo nella vista; fonte dell'ortofoto scelta da sola tra quelle applicabili nel punto (regione e riquadro); tessere d'errore delle fonti pulite (`X-Ortofoto-Errore`) e nota quando una fonte non risponde; zoom massimi reali delle fonti (AGEA 2012 18, regionali 19); alberi anche nella mappa 2D; tolta l'esagerazione del rilievo; 09/11 d: tetto a falde anche per i corpi con cortile, tegola spenta dalla ricerca, maniglia per l'altezza della mappa, clic nella vista 3D sul volume più vicino, alberi indicativi da OpenStreetMap dove manca il LiDAR (`/api/alberi/osm/{nome}.json`), particelle e terreno con le tessere d'errore pulite; 09/11 e: indicatore di caricamento a clessidra, gettone della verifica anti-robot valido un'ora, legato a rete e browser e comune alle schede; 09/11 f: **Obblighi di legge, Geometria e luce naturale, Consumi** di nuovo accessibili come sperimentali; 11/11: pagina **Statistiche › Indici dei prezzi** (`indici-prezzi.html`): prezzi dell'energia elettrica delle convenzioni Intercent-ER e Consip, prezzi del gas Intercent-ER, PSV day-ahead ARERA e PFOR,t ricostruito, con il confronto delle convenzioni sui consumi mensili per fascia caricati dalla persona, file statico `dati/prezzi/indici.json`; 14/11: pagina **Clima e meteo › Newsletter e avvisi** (`dati-per-email.html`): newsletter mensile per regione, previsioni settimanali per fino a 5 comuni e avvisi meteo del giorno dopo (non allerte), scelti con un collegamento personale, rotte `/api/email/opzioni`, `/api/email/link` e seguenti; 14/11 b: nuovo gruppo **Trattamento aria › Psicrometria** con quattro pagine sperimentali (`aria-trasformazioni.html`, `aria-ore.html`, `aria-latenti.html`, `aria-freecooling.html`) e le rotte `/api/psicro/disponibilita/{istat}` e `/api/psicro/serie/{istat}` (serie oraria di temperatura e umidità, dal 1940 quando l'archivio è sul server); scelta degli anni «ultimo anno · 5 · 10 · 20 · tutta la serie» in Legge 10, Dati climatici e Cambiamento climatico, `anni=0` (tutte) e `anni=1` in `/api/clima-legge10/{istat}`; 15/11: pagine **Esempi** (`esempi.html`) e **Contributi** (`contributi.html`), tutte e due tra le «Altre pagine»; 16/11: pagine di Trattamento aria divise in due metà, ognuna con la sua barra di scorrimento; foglio `psicro_UTA.xlsx` v2.2 con la citazione «Fonte: EuGEnio – eugenio.statocritico.it» in ogni foglio, sotto ogni grafico e nel piè di stampa; la stessa citazione in riga 1 di ogni foglio e nel piè di stampa degli Excel/ODS dei report e di Dati climatici, intestazioni dei fogli di dati in riga 2; 16/11 g: **Perugia** in Modelli 3D e nelle pagine 3D, centro, Fontivegge e Sant'Andrea delle Fratte, con sagome OpenStreetMap e altezze dal LiDAR PST 2014 del MASE, terreno dal DTM 1 m dello stesso rilievo; 70 archivi di edifici; 16/11 h: ripiego OpenStreetMap anche per gli edifici vicini fuori da un archivio parziale, quando l'edificio scelto è dentro; 17/11: il gruppo del menu **Patrimonio si chiama Territorio**, nuova pagina **Territorio › Edifici pubblici** (`edifici-pubblici.html`) con gli immobili delle Pubbliche Amministrazioni del censimento MEF 2023 sulle particelle catastali, ricerca e schede da `/api/immobili-pa/info` e seguenti (§ 4.5 quater), edifici pubblici retinati in Modelli 3D); 18/11: pagine **Statistiche › Stato della rete elettrica** (`rete-elettrica.html`: criticità dei comuni dalle cabine primarie di e-distribuzione, cabine, comuni di altri distributori, interruzioni in corso e loro statistiche) e **Fotovoltaico › Cabine primarie** (`fv-cabine.html`: cabine primarie e aree convenzionali del GSE dei punti cercati o di un elenco di sedi), sperimentali, con le rotte della rete elettrica del § 4.10; 19/11: **righello** (pulsante sotto le mappe con l'ortofoto: clic = punto, clic sul primo punto = area, clic o tocco su un punto per prenderlo e clic o tocco successivo per posarlo, clic destro = azzera, Esc = spento; lunghezza, perimetro e area nel riquadretto, distanze orizzontali sull'ellissoide), in Modelli 3D **«Genera il 3D» anche senza edificio scelto** (3D della vista, da zoom 15) e **Maiuscolo + clic** per più edifici insieme con i valori sommati, in Stato della rete elettrica ortofoto sotto gli strati (casella «Ortofoto») e cabine grandi come le interruzioni, in Cabine primarie confini dell'area del punto e delle aree confinanti letti da soli al clic; 19/11 b: **terreno 3D a 5 m in tutta Italia** dal DTM nazionale HR-DTM-5m del CNR-IRPI, letto dal server da Zenodo, tra i DTM regionali e il Copernicus; 19/11 d: **Cabine primarie con una sola mappa** con l'ortofoto e le cabine di tutta Italia, «Sposta» / «Scegli punti» sotto la mappa, confini per ogni punto; 19/11 e: Cabine primarie si apre su tutta Italia; 19/11 f: foglio `strumenti/psicro_UTA.xlsx` v2.3 con i fogli «psicro» e «Mollier» nella grafica del diagramma originale – A3 orizzontale, curve nere, estate rossa e inverno blu, nel T–x isoentalpiche in kcal e kJ, isocore e goniometro a due semicerchi, tutte le scritte dell'originale, nel Mollier le stesse curve e scritte; celle di ingresso e risultato invariate); 20/11: «Annulla iscrizione» del programma di posta su qualunque email di EuGEnio arriva a EuGEnio (niente più blocco dell'indirizzo nel servizio di posta); 20/11 b: Comunità energetiche (in lavorazione): l'area convenzionale delle sedi e lo strato delle aree sono letti dal browser dal servizio pubblico del GSE al momento, mai dal server né salvati; nei file c'è solo il codice COD_AC con la nota «area convenzionale proposta dalla mappa del GSE; verifica ufficiale: GSE»; LiDAR PNRR: app https://sim.mase.gov.it/pst/, non ancora pubblicato (verifica del 16/11); 20/11 c: Comunità energetiche con la struttura delle altre pagine (mappa con ortofoto, particelle, edifici, aree del GSE, righello e «Aggiungi sedi» a sinistra; ricerca, sedi ed esiti a destra) ; 20/11 d: Comunità energetiche, confini dell'area di ogni sede (bordo spesso) e delle confinanti a qualsiasi zoom, letti dal browser come in Cabine primarie, area sotto il mouse in azzurro chiaro – versione `?v=20261120d`.**
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
- Stato: **servizio sperimentale**, risultati non ancora validati in modo sistematico (validate: Costi energetici Sanità e, dal 07/11/2026, Dati climatici e Legge 10). Non sostituisce i valori
  normativi, le visure ufficiali né il giudizio di un professionista. Dillo alla persona quando le dai i risultati.

## 2. Licenze e come citare

- **Codice**: AGPL-3.0 con i termini aggiuntivi della sezione 7 (`TERMINI_AGGIUNTIVI.md`). Chi offre online una versione
  modificata deve pubblicarne il codice; chi distribuisce EuGEnio o lo fa usare in rete conserva l'attribuzione
  «EuGEnio © 2026 Paolo Bianco – Stato Critico – https://eugenio.statocritico.it» (piede o pagina Licenza).
- **Dati elaborati e report di EuGEnio**: CC BY 4.0. Formula obbligatoria nel documento che li usa:
  **«Fonte: EuGEnio – eugenio.statocritico.it»**, più le fonti originali indicate nel file o nella risposta (campi `fonte`,
  `licenza`, `citazione`, foglio «Info» degli Excel/ODS, riga 1 di ogni foglio e piè di pagina di stampa degli Excel/ODS (dal 16/11/2026), ultime righe dei CSV, «Fonti e attribuzioni» dei PDF).
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
| Edifici Emilia-Romagna | «Regione Emilia-Romagna – DBTR, CC BY 4.0» (unità volumetriche ed edifici); terreno «Regione Emilia-Romagna – DTM 5×5 m (CC BY 4.0)» (quote dei corpi e tessere di `/api/terreno/{z}/{x}/{y}.png`; fuori dall'ER le tessere vengono dal Copernicus DEM GLO-90, © DLR e Airbus); altezze del DBTR non plausibili portate alla stima e dichiarate (`h_dbtr_scartata`, «altezza stimata (dato DBTR non plausibile)») |
| Edifici OpenStreetMap | © contributori OpenStreetMap (ODbL 1.0); archivio separato da quelli CC BY; anche gli edifici del ripiego di Modelli 3D fuori dal DBTR (`GET /api/edifici/osm`): ogni edificio porta la licenza della sua sagoma |
| Edifici del Veneto (sagome regionali al volo, 08/11/2026) | «Regione del Veneto – Edifici del Veneto (feb. 2022), IODL 2.0» per le sagome; altezze prese da OpenStreetMap (ODbL 1.0) dove un edificio OSM si sovrappone; licenza per corpo `IODL 2.0; altezza ODbL 1.0` o `IODL 2.0` (altezza stimata) |
| Terreno del Veneto | «Regione del Veneto – DTM 5 m da voli LiDAR, IODL 2.0» (tessere di `/api/terreno/{z}/{x}/{y}.png` e quote dei corpi in Veneto, dove il DTM è sul server; intestazione `X-Terreno-Nome`) |
| Terreno nel resto d'Italia | dal 19/11/2026 «HR-DTM-5m – M. Panza, M. Muto, I. Marchesini, M. Rossi, M. Alvioli, G. Iovine – CNR-IRPI (GEO-CNR), versione 1.3, CC BY 4.0, https://doi.org/10.5281/zenodo.24009736» (tessere di `/api/terreno/{z}/{x}/{y}.png` e quote fuori dai DTM regionali; `X-Terreno-Nome` dice anche il rilievo d'origine: LiDAR con nome e anno, o TINITALY 1.1 a 10 m) |
| Edifici delle città fuori dall'ER (08/11/2026) | l'`attribuzione` dell'archivio in `/edifici3d/archivi.json` e nel suo `indice.json` (per esempio «Comune di Venezia – DBGT, Unità volumetriche (IODL 2.0)», «Regione Piemonte – BDTRE, Unità volumetriche (altezze ARPA Piemonte), CC BY 2.5», «Provincia autonoma di Bolzano – INSPIRE Edifici (CC0 1.0); altezze da DSM − DTM …», «Regione Campania – DBT 2020 … (CC BY 4.0); altezze: © European Union, Copernicus Land Monitoring Service 2012, European Environment Agency (EEA) …», a Perugia «© OpenStreetMap contributors (ODbL 1.0); altezze da DSM − DTM 1 m: Ministero dell'Ambiente e della Sicurezza Energetica – Geoportale Nazionale, Banca dati PST (CC BY 4.0)»); `licenza` per corpo; il file `LICENZE.txt` accanto a ogni archivio |
| Sagome regionali al volo di Sardegna e Campania (08/11/2026) | «Regione Autonoma della Sardegna – DBGT 10k 2022, Edificio (CC BY 4.0)», «Regione Campania – CTR 2020, Geoportale Regione Campania (CC BY 4.0)»; altezze OSM (ODbL 1.0) o stimate, come in Veneto |
| Terreno e LiDAR ER | Regione Emilia-Romagna, DTM e prodotti LiDAR (CC BY 4.0) |
| Orizzonte lontano | Copernicus DEM GLO-90 (© DLR e Airbus, licenza Copernicus DEM), dai file di Open-Meteo.com (CC BY 4.0) |
| Ortofoto | la citazione della fonte scelta, restituita da `/api/ortofoto/fonti` (per esempio «Regione Emilia-Romagna – Ortofoto RER 2023-24 (CC BY 4.0)», «Sentinel-2 cloudless – https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016) (CC BY 4.0)»); per AGEA 2022-2024 con l'anno vero della zona (`X-Ortofoto-Anno`), per esempio «AGEA – Agenzia per le Erogazioni in Agricoltura, ortofoto RGB 2023 (CC BY 4.0)»; il Geoportale Nazionale è solo consultazione dal vivo e non va nei report |
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
(LiDAR e Visure: pagina descrittiva, nessun dato) oppure, se la voce **non è cliccabile** (suggerimento «In lavorazione:
disponibile prossimamente»), **in lavorazione**: pagina non accessibile dal menu né da altri collegamenti del sito,
raggiungibile solo con l'indirizzo diretto, con in cima l'avviso «Pagina in lavorazione, non ancora verificata»; **GME** =
in attesa di autorizzazione dal GME (voce non cliccabile, pagina segnaposto). Dall'08/11/2026 sono **in lavorazione tutte
le pagine dei gruppi Edifici, Cogenerazione e Fotovoltaico** (tranne le voci GME): un agente non le propone alla persona
come servizi disponibili. Accessibili: Clima e meteo, Patrimonio, Trattamento aria (dal 14/11/2026, sperimentale),
Statistiche, più le prime tre pagine di Edifici (sperimentali) e, dal 17/11/2026, Fotovoltaico › Cabine primarie
(`fv-cabine.html`, sperimentale).

Parametri dell'indirizzo comuni: `?regione=RR` (codice regione ISTAT a 2 cifre, predefinito `08`) sceglie la regione della
mappa in Previsioni, Patrimonio, Legge 10, Dati climatici, Ortofoto; `?vista=italia` apre la mappa grande su tutta Italia.
**Collegamento a questa simulazione** (dal 20/11/2026, `collegamento.js`): nelle pagine che funzionano a scelte tutte le
scelte stanno nella query string, con nomi brevi in italiano (per esempio `legge10.html?regione=08&comune=037006&anni=5`,
`dati.html?dataset=meteo_giornaliero&var=t_media,pioggia&freq=mensile&dal=2020-03-01&area=comuni&comuni=037006`,
`ortofoto.html?lat=44.4949&lon=11.3426&z=15.5&fonte=pcn2012&particelle=1`); il riquadro in fondo alla pagina mostra
l'indirizzo completo (si aggiorna da solo a ogni scelta, pulsante per copiarlo) e aprirlo rimette le stesse scelte; anche `elettricita.html` e `carichi.html` (21/11/2026; in `elettricita.html` dal 22/11/2026 `inizio` e `fine` al posto di `anno`, che funziona ancora) e `suolo.html` (22/11/2026: `modo`, `inizio`, `fine`, `unita`, `provincia`). Mai file caricati, nomi o dati personali; tutto nel browser.

### Clima e meteo

| Pagina | URL e parametri | A cosa serve | Ingressi | Uscite | Stato |
|---|---|---|---|---|---|
| **Previsioni** | `/` (`index.html`), `?regione=RR` | Previsione dei consumi di un edificio con TiRex-2 dal suo storico, dal meteo previsto del comune e dal calendario; oppure **«Solo clima»**: le variabili meteo previste del comune, senza file | comune (mappa, elenco o indirizzo); file dei consumi; «energia per intervallo» (si somma) o «potenza o media» (si media); orizzonte «prossimi giorni, ora per ora» (fino a 15 giorni) o «prossimi mesi, giorno per giorno» (fino a 365); modo «prevedi il futuro» o «mettila alla prova sull'ultimo periodo»; variabili meteo | grafico con fasce di probabilità (quantili 10–90 %), schede delle variabili meteo, avvisi; report PDF, dati in Excel/ODS | sperimentale |
| **Legge 10** | `legge10.html`, `?comune=ISTAT`, `?regione=RR` | Dati climatici del comune dal clima reale delle ultime stagioni (ultima, 5, 10, 20 o tutte): gradi giorno sul periodo della zona e sull'anno, zona risultante, tendenza per decennio, temperature di progetto, dati mensili come nella UNI 10349, confronto con l'Allegato A del DPR 412/93; clima dal 1940 | comune | grafici, tabelle; CSV/JSON; report PDF/Excel/ODS; CSV nazionali `dati/clima_sintesi.csv` e `dati/clima_stagioni.csv` | attiva |
| **Cambiamento climatico** | `edificio-clima.html`, `?istat=ISTAT` (indirizzo invariato; fino al 07/11/2026 «Clima che cambia» nel gruppo Edificio) | Tendenza dei gradi giorno dal 1940 nel comune e consumi attesi con la firma energetica dell'edificio (analisi 13); estrapolazioni della tendenza, non scenari climatici ufficiali | comune, stagioni della tendenza (ultime 5, 10 o 20, dal 1991/92, 1981/82, 1961/62 o tutta la serie dal 1940/41), carico di base e pendenza (facoltativi) | grafico, tabella | sperimentale |
| **Dati climatici** | `dati.html`, `?dataset=ID` (`meteo_orario`, `meteo_giornaliero`, `gradi_giorno`, `legge10`, `dpr412`, `comuni`, `eurostat_pmi`) | Scaricare dati ridistribuibili per comune, provincia, regione o Italia | dataset, grandezze, periodo (scelte rapide «ultimo anno · 5 · 10 · 20 anni · tutta la serie»; per `legge10` stagioni «ultima · 5 · 10 · 20 · tutta la serie»), frequenza (oraria, giornaliera, mensile, annuale, per stagione), copertura minima, area | CSV, Excel (.xlsx), OpenDocument (.ods), con fonti e licenze | attiva (il download chiede la verifica anti-robot) |

Per la relazione tecnica ex Legge 10 restano **obbligatori i valori normativi** (UNI 10349, DPR 412/93): EuGEnio dà il clima
osservato come confronto. I prospetti UNI non sono pubblicati.

Formato del file dei consumi (Previsioni): CSV, `.xlsx` o `.ods` (primo foglio), **due colonne**: data/ora e valore,
separatore `;`, `,` o tabulazione, decimali col punto o con la virgola, date `AAAA-MM-GG hh:mm` o `GG/MM/AAAA hh:mm`
(ora italiana se senza fuso), almeno 30 valori, al massimo 200.000 righe e 5 MB. Dati quartorari o orari per la modalità
oraria (si riportano all'ora), giornalieri per quella giornaliera. Esempi: `esempi/esempio_orario_sintetico.csv`
(`data;kWh` / `27/06/2026 01:00;20,69`), `esempi/esempio_giornaliero_sintetico.csv` (`giorno,consumo` / `2024-01-23,1074.1`).

### Territorio (fino al 16/11/2026 il gruppo si chiamava «Patrimonio»)

| Pagina | URL e parametri | A cosa serve | Ingressi | Uscite | Stato |
|---|---|---|---|---|---|
| **Patrimonio** | `patrimonio.html`, `?regione=RR`, `#valori` (scheda «Valori per sede») | Geolocalizzare un elenco di edifici: punto, particella catastale, comune; mappa 3D con i valori di ogni sede (consumi, costi) come barre; abbinare le visure lette da EuGEnio Visure; aprire una sede in Modelli 3D | file degli edifici (sotto) | mappa, esiti `ok` / `verificare` / `non_trovato`; CSV (`;`, BOM), GeoJSON con attribuzione; report PDF/Excel/ODS | attiva |
| **Edifici pubblici** | `edifici-pubblici.html`, `?lat=…&lon=…&z=…`, `?ref=<particella AdE>` (es. `A045_000100.1`), `?bene=<id bene MEF>`, `?regione=RR`; ricerca per ente (dal 22/11/2026): `?modo=enti&sel=<chiave>,<chiave>…` (chiavi di 10 caratteri dall'elenco degli enti, al massimo 8, i colori seguono l'ordine), `&ruolo=proprieta,uso` (predefinito solo `proprieta`), `&natura=E,T` (predefinito solo `E`), `&ordina=<colonna>:asc|desc`, `&tipo_ente=<gruppo>`, `&regione_ente=<indice>` | Immobili delle Pubbliche Amministrazioni (censimento MEF «Patrimonio della PA», dati al 31/12/2023, CC BY 4.0) sulla mappa con la **particella catastale** dell'Agenzia delle Entrate (CC BY 4.0) e l'ortofoto sotto: particelle con edifici retinate a righe oblique, terreni in verde, edifici e terreni insieme in viola, beni senza particella come punti arancio; livelli accendibili (Edifici, Terreni, Beni senza particella, gruppi di enti: Comuni, Unioni di Comuni e Comunità montane, Province e Città metropolitane, Regioni, Sanità, Università, Edilizia residenziale pubblica, Stato, Previdenza, Altri); ricerca a parole (ente, comune, indirizzo, tipologia, dati catastali) e per indirizzo o foglio e particella; clic → scheda dei beni (tipologia, superficie, epoca, titolo, utilizzo, vincolo, aggancio) con «Apri in Modelli 3D», «Apri in Ortofoto» e «Mostra tutti i beni di questo ente»; scheda **«Per ente»** (dal 22/11/2026): autocompletamento su tutti gli enti dichiaranti (con filtri per tipologia e regione dove l'ente ha beni), fino a 8 enti insieme ognuno con un colore, caselle «in proprietà» (accesa) / «in uso» (detenzione, spenta) e fabbricati (accesi) / terreni (spenti), pallini fino allo zoom 13 e poi contorni e retino nel colore dell'ente, totali per ente (e insieme, sui beni distinti) e tabella ordinabile con una riga per particella | luogo o parole | mappa; scheda; immagine JPG/PNG/PDF con le attribuzioni | sperimentale: 3,26 milioni di beni, 95 % di quelli con identificativo agganciati a una particella (1,8 milioni di particelle); manca il Trentino-Alto Adige (catasto tavolare); da lontano un punto per particella, dallo zoom 13 i confini; nella scheda mai il soggetto cedente né codici fiscali |
| **Ortofoto** | `ortofoto.html`, `?lat=…&lon=…&z=…` (predefinito, dall'08/11/2026: Cesena, ospedale Bufalini, viale Ghirotti 286, 44,1326 N 12,2597 E, zoom 15,6), `&fonte=ID`, `?regione=RR` | Foto aeree come sfondo, con strati delle particelle catastali e dei contorni degli edifici; ricerca per indirizzo o per foglio e particella (dal 09/11/2026 b un solo modulo con un solo Comune, come Modelli 3D) | luogo | mappa; immagine JPG/PNG/PDF con le attribuzioni | sperimentale |
| **LiDAR** | `lidar.html` | Descrive la ricostruzione di altezze e falde dai rilievi laser | — | — | in sviluppo |
| **Modelli 3D** | `modelli3d.html`, `?edificio=ID`, `?archivio=demo` (demo sintetica, edifici inventati), `?archivio=<percorso>` (altro archivio sotto `/edifici3d/`), `?sede=locale` (sede passata da Patrimonio nella memoria della scheda), `?modello=locale` (modello passato da Importa DXF/IFC), `?dbtr=locale` (edifici del DB topografico letto in Aggiungi edifici, dalla memoria del browser) | Mappa 2D con ricerca e clic sull'edificio, poi «Genera il 3D»: corpi, edifici vicini, terreno, piani e superfici stimati; dal 19/11/2026 **Maiuscolo + clic** sceglie più edifici insieme (in 2D e nella vista 3D; corpi, volume, superfici e indicatori sommati, pareti in comune tra loro comprese; Maiuscolo + trascinamento non fa più lo zoom a riquadro; «Torna alla mappa 2D» lascia attiva la scelta) e, senza edificio scelto, **«Genera il 3D»** (da zoom 15) fa l'alzato della zona sullo schermo, poi un clic su un volume lo sceglie; righello sotto la mappa | edificio scelto | vista 3D; immagine PNG/PDF; report dell'edificio | sperimentale: dal 07/11/2026 sagome e altezze delle **unità volumetriche del DBTR** dell'Emilia-Romagna (CC BY 4.0, con i cortili, foglio e numero dell'edificio, destinazione d'uso) per i comuni già preparati, uno per archivio (all'inizio Rimini; poi gli altri comuni della Romagna; dal 09/11/2026 54 archivi: Bologna e Castel Bolognese interi, Ravenna con parte del forese, i centri di altri comuni della Romagna e della cintura di Bologna, con nome «… (centro e frazioni principali)» o «… (zona verso Bologna)» e zona coperta vicino ai corpi); **dall'08/11/2026 anche 15 città fuori dall'Emilia-Romagna**, con i DB topografici di Regioni, Province e Comuni: Milano, Torino, Genova (parte del centro, San Martino e Lanterna), Venezia, Trieste, Trento, Bolzano, Firenze, Ancona, Roma (comune intero dal 09/11/2026, 7 fogli del DBGT 2014), Bari (comune intero dal 09/11/2026, CTR 2006), Potenza, Napoli, Palermo e Cagliari (Castello e Brotzu) e, **dal 16/11/2026, Perugia** (centro, Fontivegge e Sant'Andrea delle Fratte: sagome OpenStreetMap, ODbL 1.0, archivio `odbl/umb/perugia`, con le altezze da DSM − DTM 1 m del LiDAR PST 2014 del MASE, CC BY 4.0, rilievo «non collaudato» nel quadro di unione; edifici costruiti dopo il 2014 con l'altezza OSM o stimata, dichiarata per corpo), ognuna con la sua licenza (CC BY 4.0, CC BY 2.5 a Torino, IODL 2.0 a Venezia, Bari e Potenza, CC0 1.0 a Bolzano) e altezze dal DB o dal rilievo laser (Trento, Bolzano, Cagliari, Genova); a Napoli (DBT 2020 della Regione Campania, CC BY 4.0) le altezze vengono dalle **classi** del Copernicus Urban Atlas Building Height 2012 («© European Union, Copernicus Land Monitoring Service 2012, European Environment Agency (EEA)»: centro della classe, per esempio 25 m per la classe 20–30 m), poi dalla mediana dei vicini, poi dalla stima dall'uso, sempre dichiarate per corpo; le Regioni che pubblicano le sagome senza altezze (Veneto, Sardegna, Campania) danno le sagome al volo con le altezze OSM; `/edifici3d/archivi.json` elenca gli archivi con il loro riquadro e, per un comune intero, il codice `istat` (zona coperta = confine ISTAT del comune); **fuori dal DBTR** (fuori dall'Emilia-Romagna e nei comuni ER non ancora preparati) la pagina usa come **ripiego gli edifici OpenStreetMap** intorno al punto (`GET /api/edifici/osm`, ODbL 1.0, qualità inferiore, altezze in parte stimate, dichiarate in pagina, nell'immagine e nel report); se OpenStreetMap non risponde lo dice e il 3D non si genera; dove c'è il DBTR OSM non si usa; con `?dbtr=locale` gli edifici del file caricato dalla persona valgono per primi (zona coperta per la sessione: confine del comune se il file è il comune intero, altrimenti il riquadro dei corpi); senza parametri nell'indirizzo (e con la regione scelta Emilia-Romagna) la mappa si apre su **Cesena, ospedale Bufalini** (zoom 15,6, l'ospedale e la collina; con una regione scelta diversa, su quella regione); la ricerca (primo passo della colonna destra, esempio «viale Ghirotti 286», «Cesena») porta la mappa a zoom 17; **con il solo comune** (o un indirizzo senza coordinate) al centro del comune a zoom 14, senza chiamare il server; un punto vicino al confine (generalizzato) di un comune coperto è coperto se l'archivio ha un corpo entro 150 m; **tetti** (decisione del 09/11/2026 c, sostituisce la cascata automatica dell'08/11): **tutti piani in partenza** (all'altezza di gronda); nella sezione **«Coperture»** (passo 4 della colonna destra, tra «Edificio» e «Corpi») la persona accende la **tegola** e con un clic su un edificio (anche vicino, DBTR, OSM o sagome regionali, in 2D o in 3D) gli dà un tetto a falde con l'**inclinazione** scritta (22° all'inizio, da 5 a 60°), a capanna sul lato lungo o a padiglione; un secondo clic lo riporta piano; con la tegola accesa il clic non sceglie l'edificio; «Reset piani» (con conferma nella pagina) li riporta tutti piani; le scelte stanno nel browser (`localStorage`, chiave `eugenio-tetti-v1`: `archivio|id del corpo` → inclinazione) e si portano su un altro PC con «Esporta tetti» / «Importa tetti» (JSON `{"tipo": "eugenio-tetti", "versione": 1, "tetti": {...}}`); nota sotto la mappa «Tetti: N a falde scelti dall'utente (22°), P piani», anche in legenda, immagine, tabella dei corpi («tetto a falde scelto dall'utente (22°)») e report; le falde misurate dal LiDAR, la stima dal colmo DBTR e l'ipotesi 22°/32° sono **sospese** (restano nel codice, non nella vista); edifici OSM in marrone; nella vista 3D rilievo ombreggiato (sempre con il rilievo vero: tolta il 09/11/2026 c la riga «Rilievo ×1 ×1,5 ×2») e la fonte del terreno in legenda; nuova ricerca o mappa portata a oltre 2 km durante il 3D → mappa 2D; dal 09/11/2026: **colore degli edifici** a scelta (grigio, giallo, rosso, indaco, violetto; l'edificio scelto resta arancio, OSM marrone) e casella **«Alberi»** (chiome dal LiDAR, spenta in partenza), ricordati nel browser e scritti nell'immagine; dal 09/11/2026 b la ricerca è **un solo modulo**: **Comune** una volta sola in cima, **Indirizzo**, **Foglio** e **Particella** affiancati, poi «Cerca l'indirizzo» (usa solo Comune e Indirizzo), «Cerca la particella» (solo Comune, Foglio e Particella) e un solo «Reset» che svuota tutto; con il solo Comune tutti e due vanno al centro del comune; un risultato in un altro comune (comune catastale diverso da quello scritto) non sposta la mappa lì ma al centro del comune scritto, con l'avviso; «Colore» degli edifici e «Alberi» stanno **sotto la mappa**, nella riga di «Genera il 3D» dopo le frecce dell'ortofoto e «Azzera»; la ricerca per solo comune trova tutti i comuni italiani; **un clic sulla mappa non sposta mai la vista** (regione e comune si evidenziano); dove la fonte di ortofoto scelta da sola non ha immagini la pagina passa alla successiva e lo dice; se una fonte della mappa supera il limite orario, nota sotto la mappa con il tempo di ripresa; dal 09/11/2026 c la casella della **fonte dell'ortofoto** mostra solo le fonti applicabili nel punto (regione dai confini ISTAT e riquadro: a Firenze la Toscana e non la RER, in Veneto AGEA 2012 e Sentinel-2) e sceglie da sola la migliore (regionale a 20 cm dove ha immagini, poi AGEA 2012, poi Sentinel-2); una scelta a mano resta finché la fonte è applicabile, poi si torna all'automatico con una nota; se una fonte **non risponde** (tessere con `X-Ortofoto-Errore`, 5xx, rete) la pagina la ferma qualche minuto e lo scrive sotto la mappa («Ortofoto «…»: la fonte non risponde … riprovo da solo tra N minuti»); «Alberi» mostra le chiome anche nella mappa 2D e dice se lì non ce ne sono (per ora solo la fascia costiera della zona di Rimini); dal 09/11/2026 d dove manca il LiDAR, con «Alberi» acceso, **chiome indicative da OpenStreetMap** (`natural=tree` e `tree_row`, ODbL 1.0, altezza dai dati OSM o 8 m, verde chiaro, dichiarate in nota, legenda, immagine e report; nelle ombre come stima; dove c'è il LiDAR vince il LiDAR); i corpi **con cortile** e le piante complesse prendono le falde «a distanza dal bordo» (scendono verso la strada e verso il cortile); la **tegola** si spegne con la ricerca; una **maniglia** sotto la mappa ne cambia l'altezza (trascinamento, dito, frecce; ricordata nel browser); nella vista 3D il clic sceglie il **volume più vicino** alla camera (pareti e tetti), anche con la tegola; una piccola clessidra sulla mappa (`.carico-mappa`, `role="status"`) dice «Carico le tessere… (N)», la fonte lenta dopo 3 s e «Genero il 3D…»: un agente che usa il browser aspetti che sparisca; dal 17/11/2026 gli **edifici pubblici** (corpo in una particella con edifici del censimento MEF) sono **retinati a righe oblique** in 2D e nella vista 3D (casella «Edifici pubblici» tra i livelli, accesa in partenza) e, scelto un edificio pubblico, sotto il messaggio compaiono l'ente e il collegamento alla scheda di Edifici pubblici; `?lat=…&lon=…` senza `edificio` apre la mappa 2D sul punto |
| **Aggiungi edifici (DB topografico)** | `aggiungi-dbtr.html`, `?regione=er\|lom\|fvg\|lig` | Caricare il **database topografico** scaricato dal portale della Regione (zip, GeoPackage o Shapefile, fino a 300 MB): corpi con le altezze ricavati **nel browser** (Web Worker, stesse regole del server: convenzione delle altezze del comune, cortili, foglio, numero, destinazione) e usati in Modelli 3D solo da chi li ha caricati; **facoltativo**, con una casella di consenso non spuntata di partenza: proposta dello stesso file all'**archivio comune** (coda sul server, controlli automatici, approvazione di Stato Critico) | regione, comune, «comune intero» sì/no, file | edifici in Modelli 3D (`modelli3d.html?dbtr=locale`); stato delle proprie proposte | sperimentale; Emilia-Romagna (DBTR) provata su più comuni; Lombardia (DBGT), Friuli Venezia Giulia (CTRN) e Liguria (CTR 3D, solo proposta al server: serve il DTM) sperimentali |
| **Scaricare i DB topografici** | `dbtr-istruzioni.html` | Istruzioni passo passo per scaricare gli edifici dai portali di Emilia-Romagna, Lombardia, Friuli Venezia Giulia, Liguria, Trento e Veneto (pagina, strati, formato, sistema di riferimento, licenza, limiti) e stato delle altre regioni | — | — | pagina di testo |
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

### Edifici e Fotovoltaico (in lavorazione: non accessibili dal menu, tranne le prime tre di Edifici, sperimentali dal 09/11/2026 f; pagine 3D, stessi parametri di Modelli 3D: `?edificio=ID&lon=…&lat=…`, `?archivio=…`, `?sede=locale`, `?dbtr=locale`)

**Dal 09/11/2026 f (decisione di Paolo)**: `edificio-obblighi.html`, `edificio-geometria.html` e `edificio-consumi.html`
sono **accessibili e sperimentali** («S»): un agente può indicarle, dicendo che i risultati sono sperimentali e non
verificati. **Stato dall'08/11/2026 (decisione di Paolo)**: tutte le altre pagine di questi due gruppi sono **in lavorazione, non
accessibili**: nel menu la voce ha il triangolo giallo e non è cliccabile, nessuna pagina del sito le collega, si aprono
solo con l'indirizzo diretto e mostrano in cima «Pagina in lavorazione, non ancora verificata». I risultati non sono
verificati: un agente non le usa per conto di una persona né le indica come servizi disponibili (per edificio, ombre e
fotovoltaico si usa Modelli 3D, gruppo Patrimonio). Il gruppo si chiama **Edifici** (prima «Edificio»); gli indirizzi delle
pagine non cambiano. Descrizione tecnica (per quando saranno aperte):

Dal 07/11/2026 sera queste pagine funzionano **come Modelli 3D**: mappa 2D con la ricerca (indirizzo o foglio e particella)
e il clic sull'edificio, poi «Genera il 3D»; stessi archivi DBTR per comune, stesso ripiego OpenStreetMap fuori dal DBTR (dal 16/11 anche per i vicini fuori da un archivio parziale),
stessi edifici del DB topografico caricato nel browser (nella stessa scheda), terreno dal server. Cambia solo il passo in
evidenza nel pannello di destra. `?edificio=ID` va insieme a `lon` e `lat` del punto (senza, si cerca vicino al primo
archivio). La demo sintetica solo con `?archivio=demo`.

**Forma dei tetti** (dal 09/11/2026 c): nel passo «Corpi › Falde dei tetti» il selettore «Forma dei tetti» (`#forma-tetti`) ha due scelte: «Scelti dall'utente (tegola in «Coperture»)» (predefinita: i tetti a falde scelti con la tegola, gli altri piani) e «Tutti piani». Cambiando scelta, o un tetto con la tegola, si ricalcolano tetti, aree FV (salvo inclinazione e orientamento corretti a mano), ombre, producibilità e sole sulle facciate; la scelta è scritta nei risultati e nel report (`tetti: {scelta, testo, conteggi, scelti}`). In Modelli 3D non c'è selettore.

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
Gruppo **Edifici** (in quest'ordine nel menu):

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
| `edificio-obblighi.html` – Obblighi di legge | potenza minima di rinnovabili (D.Lgs. 199/2021), S/V, zona, limite di H'T del DM requisiti minimi | edificio | sperimentale (S), accessibile dal 09/11/2026 f |
| `edificio-geometria.html` – Geometria e luce naturale | volume, superfici, S/V, pareti esposte e in comune, cielo visto | edificio | sperimentale (S), accessibile dal 09/11/2026 f |
| `edificio-consumi.html` – Consumi, firma energetica e priorità | consumi al m² e al m³, firma energetica con i gradi giorno reali del comune, classifica delle sedi | consumi mensili, una riga per mese: `AAAA-MM;valore` | sperimentale (S), accessibile dal 09/11/2026 f |
| `edificio-fabbisogno.html`, `edificio-involucro.html`, `edificio-impianti.html` | fabbisogno con le metodiche UNI, facciate e tetti, pompe di calore e solare termico (segnaposto: «analisi non disponibile in questa installazione», modulo UNI non pubblico) | — | in lavorazione, non accessibile |
| `edificio-ecobonus.html` – Ecobonus | segnaposto: prima verifica degli interventi con la detrazione Ecobonus | — | in lavorazione, non accessibile |
| `edificio-conto-termico.html` – Conto Termico | segnaposto: prima verifica degli interventi con l'incentivo del Conto Termico (GSE) | — | in lavorazione, non accessibile |

Gruppo **Fotovoltaico**:

| Pagina | A cosa serve | Ingressi | Stato |
|---|---|---|---|
| `fv-ombre.html` – Ombre e percorso del sole | ombre degli edifici vicini, ora per ora | edificio, giorno, ora | in lavorazione, non accessibile |
| `fv-irradiazione.html` – Sole e irradiazione su tetti e facciate | irradiazione annua e stagionale con ombre e orizzonte fino a 25 km | edificio | in lavorazione, non accessibile |
| `fv-producibilita.html` – Producibilità con le ombre | producibilità FV dei tetti con il clima orario del comune | aree FV disegnate o proposte, kWp, inclinazione, orientamento | in lavorazione, non accessibile |
| `fv-pvgis.html` – Confronto con PVGIS | producibilità di EuGEnio accanto a PVGIS con lo stesso orizzonte | come sopra | in lavorazione, non accessibile |
| `fv-dlgs199.html` – D.Lgs. 199/2021, Allegato III | potenza minima da rinnovabili per nuove costruzioni e ristrutturazioni, confrontata col FV possibile | edificio | in lavorazione, non accessibile |
| `fv-leed.html` – Prefattibilità LEED | quali informazioni utili a LEED dà EuGEnio, tema per tema (descrittiva, nessun testo LEED) | — | in lavorazione, non accessibile |
| `edificio-cer.html` – Comunità energetiche (indirizzo invariato; fino al 07/11/2026 nel gruppo Edificio) | energia condivisa ora per ora per cabina primaria (solo energia, niente prezzi né incentivi) | CSV lungo `ora;sede;cabina;prelievo;immissione` in kWh (esempio `esempi/cer_esempio_sintetico.csv`); il codice della cabina lo scrive la persona | in lavorazione, non accessibile |
| `fv-mercato.html` | analisi di mercato su prezzi GME | — | **GME**: segnaposto |

Le altezze dell'archivio sono approssimate (circa ±3 m): piani, superfici, ombre e producibilità sono stime.

### Trattamento aria (dal 14/11/2026, sperimentale)

Gruppo **Trattamento aria**, sottotitolo **Psicrometria**, tra Edifici e Cogenerazione. Le quattro pagine hanno lo stesso
passo 1: comune sulla mappa e serie meteo oraria con il cursore «ultimo anno · 2 · 5 · 10 · 20 · tutta la serie»
(`GET /api/psicro/serie/{istat}?anni=`, § 4.2); la scelta è ricordata nel browser e vale per tutte e quattro. Le condizioni
di progetto sono **statistiche della serie scelta** (predefinito 99 % in inverno e 1 % in estate; scelte 99,6 · 99 · 95 % e
0,4 · 1 · 5 % o un valore libero), **non valori di norma**, e si correggono a mano. Formule dell'aria umida ASHRAE
Fundamentals 2017 (come psychrolib). Diagramma «Psicrometrico» (predefinito) o «Mollier», con immagine PNG/SVG
scaricabile (legenda e fonti). Tutti i calcoli nel browser. `?prova=1` usa una serie **sintetica** generata nel browser
(«dati sintetici di prova»): serve solo a provare la pagina, non dà risultati veri.

| Pagina | URL | A cosa serve | Ingressi | Uscite |
|---|---|---|---|---|
| **Trasformazioni (UTA)** | `aria-trasformazioni.html` | sequenza dell'unità di trattamento aria d'estate e d'inverno come il foglio `psicro_UTA.xlsx` (stesse formule e risultati): punto di immissione, miscela, recuperatore, batterie (fattore di bypass e ADP, parametro AUTO), umidificazione adiabatica o a vapore, post-riscaldamento, ventilatore; potenze, acqua, verifiche; stima stagionale indicativa con i gradi giorno del DPR 412/93 | portata, quota di aria esterna, riferimento della portata, ambiente, carichi, fino a 10 righe per stagione; condizioni esterne dalla serie (modificabili) | tabelle, diagramma; `strumenti/psicro_UTA.xlsx` (vuoto o compilato nel browser con i dati della pagina, prime 6 righe), CSV e JSON |
| **Ore di funzionamento** | `aria-ore.html` | tutte le ore della serie sul diagramma, in 4 gruppi (predefiniti: estate 5 anni, inverno 5 anni, estate 20 anni, inverno 20 anni); per gruppo ore l'anno, T min/media/max, percentili di x e h, condizioni di progetto, ore per classe di T (2 K) e x (1 g/kg), ore dentro e fuori da una zona di comfort | gruppi di ore (anni, date gg/mm anche a cavallo d'anno, ore locali «dalle» compresa e «alle» esclusa: 8–18 = 8:00–17:59, giorni tutti o feriali), zona di comfort | tabelle, diagramma, CSV |
| **Carichi latenti** | `aria-latenti.html` | ore, energia e potenza latente per deumidificare l'aria esterna d'estate (UR interna = massimo) e umidificarla a vapore d'inverno (UR interna = minimo), anche per 1.000 m³/h; curva di durata; parte sensibile e SHR per contesto | condizione interna (predefinite 26 °C/50 % e 20 °C/40 %, 10 anni), ore, portata e suo riferimento, livello di progetto | cifre, tabelle, curva di durata, diagramma, CSV |
| **Free cooling e recupero** | `aria-freecooling.html` | ore ed energia di free cooling (economizzatore a temperatura o entalpico), calore e freddo recuperati, ore a rischio di brina e sbrinamento, elettricità in più dei ventilatori; anno medio, per gruppo di ore e mese per mese; stima del potenziale del clima, non simulazione dell'edificio | UTA (portata, aria esterna minima, ambiente estate/inverno, mandata, T di bilancio, efficienze), gruppi di ore | tabelle, diagramma, CSV |

### Cogenerazione

| Pagina | A cosa serve | Stato |
|---|---|---|
| `cog-emissioni.html` – Emissioni | CO₂ evitata o aggiunta dal cogeneratore rispetto a rete elettrica e caldaia, con i fattori ISPRA; calcolo nel browser; ingressi: dati misurati di un anno (MWh elettrici, MWh termici, gas in MWh PCI o Sm³) oppure taglia, ore e rendimenti | in lavorazione, non accessibile (dall'08/11/2026) |
| `cog-spark-spread.html`, `cog-simulazione.html`, `cog-confronto.html`, `cog-rischio.html`, `cog-car.html` | analisi economiche su prezzi di mercato | **GME**: segnaposto |

### Statistiche

| Pagina | URL e parametri | A cosa serve | Stato |
|---|---|---|---|
| **Indici dei prezzi** | `indici-prezzi.html`, ancore `#<id dell'indice>` (per esempio `#consip-ee22`, `#psv-da-arera`) e `#confronto-consumi` | prezzi dell'energia elettrica delle convenzioni Intercent-ER (lotti 1 e 2) e Consip (17 lotti, si sceglie dalla casella), prezzi del gas Intercent-ER (€/Smc, per lotto e uso), PSV day-ahead pubblicato da ARERA e PFOR,t ricostruito da EuGEnio (stesso valore nei tre mesi del trimestre), anno in corso e anno prima, gennaio–dicembre, con la variazione; **confronto sui consumi**: un file CSV, Excel o ODS con «mese», «F1», «F2», «F3» in kWh, letto nel browser, dà il costo dell'energia con Intercent-ER lotto 1 e 2 e Consip (lotto a scelta) nei due anni, sugli stessi mesi | attiva |
| **Costi energetici Sanità** | `indicatori.html`, `?regione=RR`, `&ente=CE-COD` (per esempio `?regione=08&ente=080-101`, Azienda USL Piacenza; `080-999` = consolidato regionale) | spesa per energia degli enti del Servizio Sanitario Nazionale dal 2015, a confronto con regione e Italia, per giornata di degenza, posto letto, cittadino | attiva |
| **Stato della rete elettrica** (dal 17/11/2026) | `rete-elettrica.html`, `?regione=RR`, `&comune=<ISTAT a 6 cifre>`; `?prova=1` dati sintetici | mappa della regione con quattro strati spegnibili: **criticità dei comuni** (classificazione di EuGEnio dai dati mensili per trasformatore di e-distribuzione: L = livello più alto tra verde, giallo, arancione, rosso dei trasformatori delle cabine che servono il comune, q = quota a quel livello; L verde nessun colore, q > 0,5 pieno di L, altrimenti strisce tra il livello precedente e L), **comuni con un altro distributore** (retino), **cabine primarie** (punti colorati bordati di nero, dal 19/11/2026 grandi come quelli delle interruzioni: livello peggiore dei trasformatori, verde disegnato bianco, grigio per altri gestori o senza dato; dettagli: nome, codice e-distribuzione, `COD_AC` del GSE, gestore, trasformatori per livello, data) e **interruzioni in corso**; dal 19/11/2026 sotto tutti gli strati l'**ortofoto** (casella «Ortofoto», accesa in partenza: contesto Sentinel-2 da lontano, da vicino la fonte migliore della zona come in Ortofoto, citazione sotto la mappa e nell'immagine scaricata) e il **righello** accanto alle caselle; scelto un comune: criticità, cabine, interruzioni in corso e statistiche dal giorno d'inizio della raccolta (ogni 15 minuti; durata **stimata** = ultima lettura in cui compare − inizio dichiarato); per un comune di un altro distributore il rimando alla mappa del GSE; province senza dato (oggi Torino) segnalate. Download: immagine (JPG, PNG, PDF) e dati CSV, Excel, PDF con le fonti; le posizioni delle cabine sono di OpenStreetMap (**ODbL**, da citare) | sperimentale |
| **Produzione e consumi di elettricità** (dal 21/11/2026) | `elettricita.html`, `?regione=RR` o `?vista=italia`, `&modo=…`, `&inizio=AAAA&fine=AAAA` (periodo, dal 22/11/2026; uguali = un anno; il vecchio `&anno=AAAA` vale come un anno solo), `&barre=…`, `&fondo=…`, `&ortofoto=0|1` | istogrammi per regione e per provincia di potenza installata, produzione, carichi e consumi per settore, con gli obiettivi regionali 2030 di potenza rinnovabile (burden sharing); dati statistici annuali di Terna dal 2000, elaborati da EuGEnio; con `?modo=emissioni` (dal 21/11/2026 b) anelli della produzione per fonte in ogni regione e provincia, fattore di emissione medio e del termoelettrico (g CO₂/kWh) ed energia primaria del termoelettrico per regione, zona di mercato e Italia, anno per anno dal 2000, confronto con i valori ISPRA e con il coefficiente 0,187 tep/MWh; con un periodo (dal 22/11/2026) produzione, carichi, consumi ed emissioni sono sommati sugli anni, i fattori sono il rapporto delle somme, capacità e burden sharing sono dell'anno finale con la variazione dall'iniziale | sperimentale; i dati di Terna si usano solo per le elaborazioni e **non si scaricano** (nessun CSV, Excel o JSON: si scarica solo l'immagine della mappa); file sul server, non nel repository |
| **Carichi elettrici** (dal 21/11/2026) | `carichi.html`, `?zona=NORD|CNOR|CSUD|SUD|CALA|SICI|SARD` (senza `zona` = Italia), `&da=AAAA-MM-GG&a=AAAA-MM-GG`, `&passo=15|60`, dal 22/11/2026 `&finestra=AAAA-MM-GG_AAAA-MM-GG` (finestra dei grafici delle fonti, anche con l'ora `AAAA-MM-GGTHHMM`; senza = tutto il periodo) e `&spente=termo,bio,idro,geo,eol,fv,saldo` (fonti spente; senza = tutte accese) | carico elettrico di una zona di mercato (dal 2021: Nord, Centro-Nord, Centro-Sud, Sud, Calabria, Sicilia, Sardegna) o di tutta Italia nel periodo scelto, a quarti d'ora o a ore: valori del periodo (energia, potenza massima e minima, media), profilo giornaliero con fascia minimo–massimo, curva di durata, potenza per fonte in MW (aree impilate, energia della finestra in GWh per fonte, caselle per accendere e spegnere le fonti; dal 22/11/2026) e mix di produzione per fonte al 100 % con la stessa finestra (pulsanti «Ieri» … «Ultimo anno» dall'ultimo giorno con i dati, cursore di un mese a scatto), solo Italia | sperimentale; dati di Terna usati per le elaborazioni e **non scaricabili** (nessun file di dati; il server li aggiorna da solo) |
| **Suolo e aree agricole** (sperimentale, dal 22/11/2026) | `suolo.html`, `?regione=RR` o `?vista=italia`, `&provincia=<ISTAT a 3 cifre>`, `&modo=suolo|consumi|colture`, `&inizio=AAAA&fine=AAAA` (periodo; uguali = un anno), `&unita=pct|m2ab` (solo con `suolo`), `&barre=…`, `&fondo=…`, `&ortofoto=0|1` | istogrammi per regione e provincia: **Suolo** (SAU e superficie agricola non utilizzata del censimento ISTAT 2020, suolo consumato, consumato in aree a pericolosità idraulica P2 e da frana P3+P4, entro 300 m dalla costa, in aree protette EUAP; ha, % del territorio o m² per abitante; con una provincia i comuni colorati per % consumato), **Consumi** (nuovo consumo di suolo per causa: edifici, strade e infrastrutture, piazzali, cantieri, cave e discariche, fotovoltaico a terra, altro; ripristini e netto; «di cui su suolo agricolo», stima EuGEnio per il 2024–2025), **Colture** (superfici coltivate ISTAT per famiglia, 2006–2025). Dati ISPRA/SNPA (edizione 2026: anni 2006, 2012, 2015–2025, serie come pubblicata, 2023 e 2024 segnati «rev»), ISTAT e Copernicus, CC BY 4.0, elaborati da EuGEnio | sperimentale; si scarica solo l'immagine della mappa; file sul server (`/dati/suolo/`), non nel repository |

### Fotovoltaico › Cabine primarie (dal 17/11/2026, sperimentale)

| Pagina | URL e parametri | A cosa serve | Stato |
|---|---|---|---|
| **Cabine primarie** | `fv-cabine.html`, `?lat=…&lon=…` (aggiunge un punto all'apertura e apre la mappa lì; senza, la mappa si apre su tutta Italia); `?prova=1` dati sintetici | dal 19/11/2026 sera **una sola mappa** con l'ortofoto (fonte migliore nel punto o scelta dal menu), particelle catastali, contorni degli edifici, righello e le **cabine primarie di tutta Italia** (`/api/rete/cabine`, colorate con il livello di saturazione come nello Stato della rete elettrica; quelle dei punti con un anello); sotto la mappa, a sinistra, **«Sposta»** (il mouse trascina la mappa, il clic non mette punti) e **«Scegli punti»** (ogni clic segna un punto, a qualsiasi zoom), **«Cancella tutti»** (punti e confini) e il colore dei punti; il punto scelto si trascina. A destra la ricerca per indirizzo o foglio e particella e il caricamento di un elenco nello **stesso formato di Patrimonio** (`id;denominazione;indirizzo;civico;comune;foglio;particella;lat;lon`, al massimo 200 righe; le righe con `lat`/`lon` restano nel browser, le altre passano da `POST /api/patrimonio` con la verifica anti-robot). Per ogni punto compaiono le **cabine primarie interessate**: quella dell'area convenzionale del GSE che contiene il punto (il browser chiede al servizio pubblico del GSE solo il `COD_AC`, senza geometria, e prende la cabina con quel codice da `/api/rete/cabine`) e quelle di e-distribuzione che servono il comune. Per **ogni punto** (segnato, cercato o dell'elenco) i **confini arrivano da soli**: il perimetro dell'area che contiene il punto (bordo spesso) e quelli di **tutte le aree confinanti** (bordo sottile): punto → `COD_AC` senza geometria, poligono semplificato con `where=COD_AC IN (…)`, codici delle aree che lo toccano con una domanda `POST` (geometria = quel poligono, 30 m di margine, risposta senza geometria), poi i poligoni con `where=COD_AC IN (…)`; i confini dei vari punti si sommano e un'area sotto il mouse si colora di azzurro chiaro. «**Aggiorna confini**» aggiunge, **dal browser**, i perimetri semplificati delle aree spuntate (al massimo 100), con l'attribuzione «Aree convenzionali: © GSE S.p.A. – CC BY-NC-SA 3.0 IT»; i perimetri non passano dal server di EuGEnio, non si salvano e non entrano nelle immagini né nei file CSV/Excel/PDF (solo i codici). Il pulsante distinto «Scarica i confini delle aree (GSE, CC BY-NC-SA)» prepara nel browser `aree_convenzionali_GSE_<aaaa-mm-gg>.geojson` (licenza, fonte, servizio, data di lettura e avviso nel file; proprietà `COD_AC`, `gestore`, `COD_CONSEG`, `sedi`). La cabina che conta per gli incentivi è quella dell'area del **punto di connessione** (POD): la verifica ufficiale è la ricerca per POD del GSE | sperimentale |

### Altre pagine

`metodo.html` (Come funziona: modello, fonti meteo, correzione ERA5, limiti; `#fonti`), `faq.html` (F.A.Q.; questo file è
spiegato in `#agenti-ai`), `sitografia.html` (progetti e dati usati), `mirror.html` (come installare una copia),
`licenza.html` (`#dati` per la CC BY), `privacy.html`, `contatti.html`, **`contributi.html`** (Contributi, dal 15/11/2026, tra le «Altre pagine» prima di Contattaci: come contribuire, con la discussione generale sul forum di Edilclima `https://forum.edilclima.it/viewtopic.php?t=38424` e la pagina Contattaci; sezione `#ringraziamenti`: «In questa pagina verranno ringraziati coloro che hanno contribuito allo sviluppo del sito.», per ora senza nomi), **`esempi.html`** (Esempi, dal 15/11/2026, tra le «Altre pagine» dopo Novità e prima di Contributi: casi d'uso concreti pagina per pagina, nell'ordine dei gruppi del menu, ancore `#clima`, `#patrimonio`, `#edifici`, `#aria`, `#cogenerazione`, `#fotovoltaico`, `#statistiche`; le pagine in lavorazione e quelle GME sono solo citate come «in arrivo»; utile per capire a cosa serve ogni pagina), **`novita.html`** (Novità: cosa cambia a ogni
pubblicazione, dalla più recente; ancora per data, `#d<aaaammgg>`, per esempio `#d20261107`, e `#d20261107-2` per la seconda voce dello stesso giorno) con il feed Atom **`novita.xml`**
(per sapere se il servizio è cambiato dall'ultima volta basta leggere la prima `entry`). **`dati-per-email.html`** (dal
14/11/2026, menu Clima e meteo › «Newsletter e avvisi»): tre servizi email gratuiti e separati, newsletter mensile (il 12: prezzi, freddo regione
per regione, capoluoghi di fino a 3 regioni scelte), previsioni settimanali (domenica pomeriggio, da lunedì a domenica, fino
a 5 comuni in tutta Italia) e avvisi meteo del giorno dopo (pioggia forte: almeno 40 mm in 24 ore o 15 mm in un'ora; neve:
almeno 2 cm; vento: raffiche di almeno 75 km/h). Gli avvisi **non sono allerte**: il servizio è gratuito, non fornisce
garanzie e non sostituisce le allerte della Protezione Civile e degli enti pubblici. L'iscrizione la fa la persona, non
l'agente: serve il collegamento personale che arriva nella sua casella (§ 4.9). Modulo di listmonk della sola newsletter
mensile: `https://notizie.statocritico.it/subscription/form`.

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
| `GET /api/protezione` | libera | `{"turnstile": chiave pubblica \| null, "intestazione": "X-EuGEnio-Sessione", "minuti": 60, "rotte": ["previsione", "patrimonio", "geocodifica", "particella", "estrazione"]}` |
| `POST /api/sessione` | solo browser | corpo `{"token": "<gettone Turnstile>"}` → `{"sessione": "…", "scade": epoch}`; dal 09/11/2026 e il gettone vale 60 minuti ed è legato alla rete **e al browser** (User-Agent): va usato dallo stesso browser che ha fatto la verifica |
| `GET /api/comuni` | libera | elenco dei comuni con meteo: `[{"istat": "099014", "nome": "Rimini", "belfiore": "H294", "provincia": …, "lat": …, "lon": …, "svg_x": …, "svg_y": …}, …]` |
| `GET /api/mappa?giorni=7` | libera | gradi giorno previsti (base 20 °C), gradi giorno estivi (base 24 °C) e temperatura media dei prossimi `giorni` (1–15) per comune: `{"giorni": 7, "comuni": {"099014": {"t": 9.8, "gg": 71.4, "gc": 0.0}, …}}` |
| `GET /api/metodologia` | libera | metriche della correzione ERA5 → ICON e dei modelli meteo |

### 4.2 Meteo, clima e Legge 10

| Metodo e percorso | Accesso | Parametri | Risposta (estratto) |
|---|---|---|---|
| `GET /api/meteo/{istat}` | libera | `modalita=breve` (orario: ultimi `giorni` ≤ 90 osservati + previsione) o `modalita=lungo` (giornaliero, ultimi `giorni` ≤ 3650) | `{"storico": {"t": [...], "temperature_2m": [...], …}, "previsione": {…}}` (orari in Europe/Rome, ISO 8601) |
| `GET /api/clima-previsto/{istat}` | libera | `modalita=breve\|lungo`, `orizzonte` (ore 1–360 o giorni 1–365), `covariate` separate da virgola: orarie `temperatura, umidita, radiazione, diffusa, vento, nuvolosita, pioggia, neve`; giornaliere anche `gradi_giorno, gradi_raffrescamento` | `{"solo_clima": true, "passo": "ora", "storico": {"t": [...]}, "previsione": {"t": [...], "fonte_meteo": ["ICON-2I", …]}, "clima": {"temperatura": {"unita": "°C", "storico": [...], "previsione": [...]}}, "avvisi": [...]}` |
| `GET /api/clima-legge10/{istat}` | libera | `anni` = ultime stagioni complete da usare (1–30, predefinito 10; **0 = tutte** quelle dell'archivio giornaliero, che parte dal 2015; dal 14/11/2026 anche 1 sola: valori indicativi) | `{"istat", "comune", "stagioni": [...], "stagioni_richieste", "stagioni_disponibili", "prima_stagione_disponibile", "note": [...], "mensili": [...], "gradi_giorno": {"zona_di_riferimento", "gg_periodo_zona", "gg_anno_intero", "zona_risultante", "per_stagione": {...}, "tendenza_gg_per_decennio", …}, "temperatura_progetto": {"invernale", "estiva", "metodo"}, "avvertenza", "fonte"}` |
| `GET /api/psicro/disponibilita/{istat}` | libera | — | dal 14/11/2026, per le pagine «Trattamento aria»: `{"istat", "comune", "quota_m", "pressione_pa", "dal", "al", "anni_completi", "anni_scelte", "archivio": "psicro"\|"orario_icon", "fonte", "licenza", "note"}` (ore UTC `AAAA-MM-GGTHH:00Z`; pressione dall'atmosfera standard alla quota del punto meteo) |
| `GET /api/psicro/serie/{istat}` | libera, con limite (120 serie per IP all'ora) | `anni` = 1, 2, 5, 10, 20 oppure 0 (tutta la serie, dal 1940): ultimi anni×12 mesi fino all'ultima ora disponibile; 422 per altri valori | serie oraria continua in UTC: `{"istat", "comune", "quota_m", "pressione_pa", "inizio": "1940-01-01T00:00Z", "passo_h": 1, "n", "t": [decimi di °C interi o null], "ur": [% interi o null], "dal", "al", "anni_richiesti", "anni_dati", "fonte", "licenza", "note": [...]}`; ERA5/ERA5-Land (Copernicus) riportato alla quota del comune e, dove il server le ha, la serie ERA5 corretta verso ICON (dal 2015) e ICON per le ore recenti: le fonti usate davvero, periodo per periodo, sono in `fonte` e `note`; finché l'archivio dal 1940 di un comune non è sul server, la serie oraria ICON dal 14/11/2022 (lo dice `note`); 503 se non c'è nessuna delle due. Una serie dal 1940 sono ~760.000 ore (~1,5 MB compressa): scaricala una volta e tienila |
| `GET /api/edifici/gradi-giorno/{istat}` | libera | `dal=AAAA-MM`, `al=AAAA-MM` | `{"mesi": [{"mese": "2025-01", "gg20": 512.3, "gc24": 0.0, "t_media": 4.1, "giorni": 31}, …], "fonte", "nota"}` (clima reale, **non** i valori di legge) |
| `GET /api/edifici/clima-orario/{istat}` | libera | `anno=AAAA` (se manca, l'ultimo completo) | un anno orario UTC: `{"anno", "inizio", "passo_ore": 1, "ghi": [...], "dhi": [...], "t": [...], "vento": [...], "fonte"}` (W/m², °C, km/h) |

Esempi:

```bash
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/clima-legge10/099014?anni=10"
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/psicro/disponibilita/099014"
curl -sS -A "$UA" "https://eugenio.statocritico.it/api/psicro/serie/099014?anni=1"
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
| `POST /api/storici/estrai?formato=csv\|xlsx\|ods` | **Turnstile** | il file (CSV in streaming; Excel e ODS con il foglio «Info»; dal 16/11/2026 in ogni foglio la riga 1 è la citazione «Fonte: EuGEnio – eugenio.statocritico.it» e nel foglio «Dati» le intestazioni stanno in riga 2 – con pandas `header=1`; la citazione è anche nel piè di pagina di stampa) |

Corpo JSON di stima ed estrazione:

```json
{"dataset": "gradi_giorno", "variabili": ["gg20", "gc24"], "dal": "2024-07-01", "al": "2025-06-30",
 "frequenza": "mensile", "copertura": 90,
 "area": {"tipo": "comuni", "comuni": ["099014", "037006"]}}
```

`area.tipo`: `tutti`, `regione` (con `"regione": "08"`), `provincia` (con `"provincia"`: codice ISTAT a 3 cifre),
`comuni` (con l'elenco), `solo_capoluoghi`: true/false. Per `legge10`: `stagioni` (1–30, 0 = tutte) e `tipologia` (`mensili`,
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
| `POST /api/converti` | libera | `file` (.xlsx o .ods) → `{"formato", "fogli": [...], "foglio_usato", "csv": "…"}` (primo foglio, separatore `;`; una prima riga con la sola citazione «Fonte: EuGEnio…», come nei file scaricati da EuGEnio, viene saltata); i CSV tornano come sono |
| `POST /api/patrimonio` | **Turnstile** | `file` (formato del § 3, ≤ 500 righe) → `{"riepilogo", "geojson", "righe": [...], "fonte", "fonte_url", "fonti"}` |
| `POST /api/patrimonio` con `luogo=1` | **Turnstile** | (dal 17/11/2026, ricerca delle pagine di mappa) con **una** riga, campi in più nella riga: `luogo_tipo` (`particella`, `via`, `località` o null), `luogo_lat`, `luogo_lon` (segnaposto: punto interno della particella catastale del civico, Agenzia delle Entrate – Cartografia catastale CC BY 4.0, o metà della via, OpenStreetMap ODbL), `luogo_riquadro` ([ovest, sud, est, nord] da inquadrare), `luogo_fonte`, `luogo_avviso`, `particella_ade`, `vie_candidate` (con `etichetta`), `scegli_via` (true = più vie possibili: far scegliere), `via_scelta`; limite `luogo` (300 all'ora per IP) |
| `GET /api/geocodifica?q=…&comune=…` | **Turnstile** | `{"risultati": [{"etichetta", "lat", "lon"}], "fonte": "Dati elaborati da Zornade", "fonte_url"}` |
| `GET /api/particella?lat=…&lon=…` | **Turnstile** | `{"particella": {"id", "etichetta", "area_m2", "lat", "lon"}, "comune": {"belfiore", "nome", "istat", "disponibile"}, "fonte", "fonte_url"}` |

Queste rotte consumano la quota gratuita di Zornade condivisa da tutti gli utenti: **mai** usarle per estrazioni massive.

### 4.5 quater Immobili delle Pubbliche Amministrazioni (17/11/2026)

Dati: censimento MEF «Patrimonio della PA», dati al 31/12/2023 (CC BY 4.0), con le particelle della cartografia catastale
dell'Agenzia delle Entrate (CC BY 4.0); aggancio di EuGEnio. Citare: «Fonti: MEF – Dipartimento dell'Economia, «Patrimonio
della PA», dati beni immobili al 31/12/2023 (CC BY 4.0); Agenzia delle Entrate, cartografia catastale (CC BY 4.0).
Elaborazione: EuGEnio – eugenio.statocritico.it». Limite per IP: 1.200 richieste all'ora (`immobili_pa`).

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/immobili-pa/info` | libera | `{"disponibile", "anno", "pmtiles", "attribuzione", "beni", "particelle", "gruppi", …}`; `{"disponibile": false}` se i dati non sono sul server |
| `GET /api/immobili-pa/cerca?q=…&gruppo=C&limite=20` | libera | ricerca a parole (tutte obbligatorie, anche iniziate, almeno 2 lettere; al massimo 50 risultati): `{"risultati": [{"id_bene", "ref_ade", "amministrazione", "tipologia", "comune", "indirizzo", "punto": [lon, lat], …}], "altri"}`; `gruppo` = codice di `gruppi` |
| `GET /api/immobili-pa/particella/{ref}` | libera | `{"particella": {"ref_ade", "punto", "riquadro", "area_m2", "n_beni"}, "beni": [...]}` (al massimo 500 beni); 404 se la particella non ha beni pubblici |
| `GET /api/immobili-pa/bene/{id_bene}` | libera | `{"bene": {...}, "dichiarazioni": [...]}`, anche per i beni senza particella; `dichiarazioni` (dal 22/11/2026) sono tutte le righe dello stesso bene, di solito proprietario e chi lo ha in uso; ogni bene ha `ente_chiave` |
| `GET /api/immobili-pa/ente/{chiavi}?ruolo=proprieta,uso&natura=E,T` | libera, limite `immobili_pa_ente` | dal 22/11/2026: uno o più enti (chiavi separate da virgole, al massimo 8): `{"disponibile", "enti": [{"chiave", "id", "nome", "tipologia_amm", "gruppo", "sede", "totali_dichiarati", "totali", "riquadro", "comuni": [...]}], "insieme"}`; `totali` con i filtri, `insieme` (con più enti) calcolato sui beni distinti; 404 se una chiave non c'è; `{"disponibile": false}` con un indice preparato prima del 22/11/2026 |
| `GET /api/immobili-pa/ente/{chiave}/punti` | libera, limite `immobili_pa_ente` (pesa 3) | centri delle particelle dell'ente e dei beni senza particella con un punto affidabile: `{"campi": ["lon", "lat", "n", "natura", "ruolo", "ref"], "righe": [...]}` (una riga per particella, ruolo P/U e natura E/T); ETag e copia di un giorno |
| `GET /api/immobili-pa/ente/{chiave}/beni?ruolo=&natura=&regione=&provincia=&comune=<cod. catastale>&ordina=sup_mq&verso=desc&pagina=1&per_pagina=100` | libera, limite `immobili_pa_ente` | elenco per particella (beni senza particella: una riga per bene) con `ref`, `lon`, `lat`, `n_beni`, `sup_mq`, `area_m2`, `comune`, `indirizzo`, `tipologie`, `epoca`, `utilizzo`, `titolo`, `ruoli`; al massimo 200 righe per pagina; `ordina` tra `regione, provincia, comune, indirizzo, tipologie, n_beni, sup_mq, area_m2, epoca, utilizzo, titolo, ruoli` |

Gli enti si trovano nell'elenco statico indicato da `indice.json` (`enti`, § 9): non cercarli chiamando le rotte una per una.
Limiti della ricerca per ente: 600 richieste all'ora per IP (`immobili_pa_ente`) e un tetto orario per tutto il sito.

I beni non contengono mai il soggetto che cede l'immobile all'ente né codici fiscali (neanche quello dell'ente: la
chiave è derivata e non reversibile). Per vedere molti immobili insieme usa le tessere (`/edifici3d/immobili_pa/`, § 9),
non migliaia di richieste alla ricerca; l'elenco per ente non si scarica e non va copiato in blocco.

### 4.5 bis Edifici OpenStreetMap al volo (ripiego di Modelli 3D, 07/11/2026)

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/edifici/osm?lon=…&lat=…` | **Turnstile** | edifici OSM entro ~400 m dal centro della cella di 0,002° (~200 m) che contiene il punto, dall'API Overpass (istanza principale overpass-api.de, riserva europea Overpass API Europa): FeatureCollection WGS84 con le proprietà delle celle di contesto (`id`, `edificio`, `gronda`, `altezza`, `fonte_sagoma`, `fonte_altezza`, `licenza: "ODbL 1.0"`, `qualita`: `"stima"` dove l'altezza è stimata, `origine_altezza`: `osm_height` (tag height), `osm_piani` (building:levels × 3 m), `dbtr_vicini` (mediana dei corpi DBTR entro 200 m, almeno 3) o `fissa` (9 m)) e `licenza`, `attribuzione`, `scheda`, `nota`, `centro`, `raggio`, `altezze` (conteggi per origine), `altezze_stimate`, `altezze_osm`, `data`; solo Italia (400 fuori); 404 se il ripiego è spento sul server; 502/503 se Overpass non risponde o è sovraccarico |

**Sagome regionali al volo** (08/11/2026): dove la Regione pubblica le sagome aperte e senza altezze con un WFS (oggi il
**Veneto**, «Edifici del Veneto (feb. 2022)», IODL 2.0) la stessa rotta risponde con le sagome della Regione e, per ognuna,
l'altezza dell'edificio OSM che le si sovrappone di più (height, poi piani × 3 m), altrimenti la mediana dei corpi DBTR
vicini (`dbtr_vicini`) o dei vicini con l'altezza OSM (`osm_vicini`), altrimenti 9 m (`fissa`); in più `sagome` (regione,
nome, licenza, attribuzione, scheda, corpi, `con_altezza_osm`, `osm_aggiunti`), `quote_dtm` (corpi con `quota_terreno`
dal DTM del server; dal 09/11/2026 b, dove non c'è un DTM regionale, dal Copernicus DEM 90 m, anche per gli edifici OSM senza sagome regionali; `quote_fonte`: `dtm`, `copernicus` o `dtm+copernicus`) e, se il WFS non risponde, `avviso_sagome` con i soli edifici OSM. Proprietà per corpo in più:
`regione_sagoma`, `uso`, `codice_uso`, `codice_tipo`, `osm_id`. Intestazione `X-Licenza: IODL 2.0; ODbL 1.0`.

Serve alle pagine 3D **solo fuori dal DBTR**; le altezze stimate sono sempre dichiarate per corpo, in una nota sotto la
mappa, nell'immagine e nel report; consuma le quote di Overpass del server (una chiamata alla volta per
tutto il sito, tetto orario, copia per cella di 30 giorni): **mai** usarla per scaricare zone. Per dati OSM in quantità
si usano gli estratti di OpenStreetMap (Geofabrik) o Overpass direttamente, con le loro regole d'uso.

### 4.6 Ortofoto, strati, terreno, orizzonte, PVGIS

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/ortofoto/fonti` | libera | fonti accese con `id`, nome, licenza, citazione, stato, zoom, riquadro, `tessere`, `spostabile` e `spostamento_max` (m) |
| `GET /api/ortofoto/{fonte}/{z}/{x}/{y}.{ext}` | libera, con limite | tessera 256×256 in EPSG:3857 (XYZ); `ext` = estensione della fonte (`jpg`); 404 fuori zona o fuori zoom; per la RER 2023-24 (dal 07/11/2026 sera) JPEG se la tessera è piena, **PNG con trasparenza** dove la fonte non ha dati (l'indirizzo pubblicato in `tessere` ha `?t=1`); dal 09/11/2026 `X-Ortofoto-Vuota: 1` se la tessera è tutta trasparente (la RER 2023-24 non ha immagini a Bologna, Modena, Parma, Imola, Ferrara, Faenza, Bagno di Romagna, Comacchio: usa un'altra fonte); le fonti solo dal vivo (AGEA 2012) hanno `Cache-Control: private, max-age=86400`; dal 09/11/2026 b le fonti con tessere **segnaposto** fuori dalla loro regione (la Toscana risponde con un'immagine bianca e la scritta «Fonte dei dati: Regione Toscana…», per esempio a Bagno di Romagna o a Bologna) danno al loro posto un PNG trasparente con `X-Ortofoto-Vuota: 1` (indirizzo pubblicato in `tessere` con `?s=1`). Dal 09/11/2026 c un **errore della fonte** (timeout, rete, 5xx, XML d'errore) o il turno verso la fonte non arrivato in tempo danno una tessera vuota «pulita»: 200, PNG trasparente, `Cache-Control: no-store`, `X-Ortofoto-Errore: fonte|occupata|ferma` e `Retry-After` (dopo 6 errori di fila in 60 s la fonte è ferma 60 s, poi 120, fino a 5 minuti: le tessere rispondono subito vuote senza chiamarla); zoom massimi in `/fonti` (`zoom`): regionali a 20 cm 19, AGEA 2012 18, Sentinel-2 15; oltre, la mappa ingrandisce le tessere. Dal 09/11/2026 d la chiamata alla fonte dura al più 18 s e anche le **particelle e i contorni** (`/api/ortofoto/strati/{sid}/{z}/{x}/{y}.{ext}`) danno la tessera vuota pulita (`X-Ortofoto-Errore`, per lo strato OSM una FeatureCollection vuota) invece di 502 e 503; particelle fino allo zoom 19. **`?de=<m>&dn=<m>`** (dall'08/11/2026, interi da −20 a 20, solo fonti con `spostabile: true` in `/fonti`, cioè WMS): ortofoto spostata di `de` m verso est e `dn` m verso nord rispetto alla cartografia (il proxy chiede alla fonte il riquadro spostato in EPSG:3857, nessuna copia su disco, intestazione `X-Ortofoto-Spostamento`); 422 fuori dai limiti, 400 per le fonti a tessere già pronte (Sentinel-2). Serve alle frecce sotto la mappa: non per scaricare zone |
| `GET /api/ortofoto/agea/{z}/{x}/{y}.jpg` | libera, con limite | (dal 17/11/2026) ortofoto **AGEA 2022-2024 RGB, CC BY 4.0** del Geoportale AGEA per tutta Italia (volo a 20 cm; zoom 10–18, dal 19/11/2026: l'`exportImage` del Geoportale per lo zoom 19 dà scacchiere bianche e nere, che il proxy ora scarta; con copia sul server, entra nei report): per ogni tessera il volo più recente che copre il punto (2024 Piemonte, Valle d'Aosta, Lombardia, Veneto, Molise, Calabria; 2023 Trentino-Alto Adige, Friuli-Venezia Giulia, Emilia-Romagna, Umbria, Lazio, Campania, Basilicata; 2022 le altre regioni), sui confini unito al precedente; l'anno usato è in **`X-Ortofoto-Anno`** (`2023` o `2023,2022`) e va nella citazione: in `/fonti` la fonte ha `anni` e `citazione_anni` («AGEA – Agenzia per le Erogazioni in Agricoltura, ortofoto RGB {anni} (CC BY 4.0)», con gli anni in ordine e «e»: «2022 e 2023»); JPEG se piena, PNG trasparente con `X-Ortofoto-Vuota: 1` dove nessun anno copre (mare). Priorità: dopo le regionali RER 2023-24, Toscana 2023, Bolzano 2023; prima di Trento 2015, AGEA 2012 (solo ripiego) e Sentinel-2. Non scaricare zone |
| `GET /api/alberi/osm/{nome}.json` | libera, con limite (`edifici_osm`, tetto di Overpass) | dal 09/11/2026 d: alberi indicativi da OpenStreetMap nella cella di 0,01° `nome` = `i_j` (i = floor(lon/0,01), j = floor(lat/0,01)), stesso formato delle celle `lidar/alberi/`: `{"campi": ["lon", "lat", "h", "quota", "lato"], "alberi": [...], "stima": true, "licenza": "ODbL 1.0"}`; `natural=tree` (altezza da `height`/`est_height` o 8 m, chioma da `diameter_crown` o 5 m) e `natural=tree_row` (una chioma ogni 6 m); citare «© contributori OpenStreetMap (ODbL 1.0)» e dire che sono stime; con `X-Ortofoto-Errore` la cella è vuota perché Overpass non ha risposto: riprova dopo `Retry-After` |
| `GET /api/ortofoto/strati` | libera | strati accesi: `catasto` (particelle AdE), `dbtr_edifici`, `osm_edifici` |
| `GET /api/ortofoto/strati/{sid}/{z}/{x}/{y}.{ext}` | libera, con limite | PNG trasparente (zoom 16–20) o, per `osm_edifici`, GeoJSON delle sagome a zoom 16 (`.json`) |
| `GET /api/terreno/fonti` | libera | DTM del server per il terreno 3D (riquadro, licenza, attribuzione; il DTM nazionale con `remoto`, `doi`, `versione`), zoom e ripiego (Copernicus DEM 90 m) |
| `GET /api/terreno/{z}/{x}/{y}.png` | libera, con limite | tessera 256×256 del terreno in codifica Terrarium (quota = R·256 + G + B/256 − 32768 m), EPSG:3857 (XYZ), zoom 8–15; DTM regionale 5 m dove c'è (dall'08/11/2026 **più DTM insieme**, il più dettagliato prima: Emilia-Romagna, Veneto dove è sul server), poi dal 19/11/2026 il DTM nazionale HR-DTM-5m del CNR-IRPI (5 m, CC BY 4.0, letto dal server da Zenodo), in mare e se le fonti non rispondono Copernicus DEM (intestazioni `X-Terreno-Fonte` e `X-Terreno-Nome` con il nome del DTM); 404 fuori dall'Italia. Serve alla vista 3D: le quote dei corpi degli edifici sono già nei corpi |
| `GET /api/edifici/orizzonte?lat=…&lon=…&h=…&direzioni=72` | libera, con limite | orizzonte del terreno fino a ~25 km dal Copernicus DEM: `{"angoli": [...], "distanze_km": [...], "quota_dem", "raggio_km", "fonte"}`; `direzioni` ∈ 36, 72, 120, 360; solo Italia |
| `POST /api/edifici/pvgis` | libera, con limite | confronto con PVGIS (JRC) per 1–12 aree; corpo sotto |

```json
{"lat": 44.0594, "lon": 12.5683,
 "aree": [{"id": "tetto-sud", "kwp": 20, "inclinazione": 15, "orientamento": 180, "perdite": 14,
           "orizzonte": [2.1, 3.0, 4.5, 5.0, 3.2, 1.0]}]}
```

`orientamento` in gradi da nord (180 = sud); `orizzonte` = angoli in gradi da nord in senso orario, passo costante.
Risposta: per area `con_orizzonte` e `senza_orizzonte_utente` con `kwh_anno`, `kwh_mensili`, `irradiazione_piano`,
`banca_dati`, `anni`. Le tessere sono pensate per la mappa del sito: **non scaricare intere zone** di ortofoto, strati o
terreno.

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

### 4.9 Newsletter e avvisi (14/11/2026)

Le scelte della pagina `dati-per-email.html`. Solo la persona può iscriversi: il gettone `t` arriva nella sua casella.

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `GET /api/email/opzioni` | libera | `{"attivo": bool, "max_regioni": 3, "max_comuni": 5, "regioni": [{"cod", "nome"}], "avvisi": [{"id": "pioggia"\|"neve"\|"vento", "nome", "soglia"}], "avvertenza", "giorno_mensile", "settimanale": {"giorno", "ora"}, "ora_avvisi"}` |
| `GET /api/email/comuni` | libera | elenco nazionale dei comuni per la ricerca: `[{"istat", "nome", "provincia", "regione_cod"}]` |
| `POST /api/email/link` | **Turnstile** | corpo `{"email": "…"}`: spedisce il collegamento personale (valido 7 giorni); risponde sempre `{"inviato": true}`; al massimo 10 richieste all'ora per IP e 3 email al giorno allo stesso indirizzo |
| `POST /api/email/leggi` | gettone | corpo `{"t": "<gettone>"}` → `{"email", "mensile", "settimanale", "avvisi": [...], "regioni": [...], "comuni": [{"istat", "nome", "provincia"}]}` |
| `POST /api/email/salva` | gettone | corpo `{"t", "mensile": bool, "regioni": [...], "settimanale": bool, "comuni": ["040007", …], "avvisi": ["pioggia", …]}` (422 oltre i limiti o senza comuni per settimanale e avvisi) |
| `POST /api/email/via` | gettone | `?t=<gettone>` (cancellazione con un clic dei programmi di posta, RFC 8058) o corpo `{"t"}`: cancella da quel servizio → `{"cancellato": "mensile"\|"settimanale"\|"avvisi", "preferenze"}` |
| `POST /api/email/via-tutto` | gettone | `?t=<gettone>` (dal 20/11/2026: «Annulla iscrizione» con un clic del programma di posta sull'email del collegamento personale, RFC 8058): toglie l'iscritto da **tutti** i servizi → `{"cancellato": "tutti"}`; il gettone contiene il numero dell'iscritto, mai l'indirizzo |
| `POST /api/email/servizio` | — | dal 20/11/2026: «Annulla iscrizione» con un clic sulle email del servizio per l'amministratore e sul collegamento per chi non è ancora iscritto: non cancella niente → `{"cancellato": null}`. Esiste perché ogni email di EuGEnio porti la propria intestazione `List-Unsubscribe` HTTPS: senza, il servizio di posta (OCI Email Delivery) mette la sua, che blocca l'indirizzo per sempre |

### 4.10 Stato della rete elettrica e cabine primarie (17/11/2026)

Dati di e-distribuzione S.p.A. (mappa delle Aree critiche e mappa delle interruzioni) raccolti dal server in un database:
**interruzioni ogni 15 minuti**, **saturazione dei trasformatori ogni notte** (dato mensile del distributore). Posizioni
delle cabine primarie dalle sottostazioni OpenStreetMap (**ODbL**, «© contributori OpenStreetMap»), con il codice
dell'area convenzionale del GSE (`COD_AC`, solo il codice: i perimetri del GSE non passano dal server). Uso non
commerciale, fonte citata: «Fonte: e-distribuzione S.p.A., mappa delle Aree critiche e mappa delle interruzioni».
Regioni: codice ISTAT a 2 cifre (`08`); comuni: ISTAT a 6 cifre.

| Metodo e percorso | Accesso | Cosa restituisce |
|---|---|---|
| `GET /api/rete/stato` | libera | `{"saturazione_aggiornata", "interruzioni_aggiornate", "attive", "province_mancanti": ["001"], "province_non_aggiornate", "raccolta_dal", "raccordo", "regola", "nota_durata", "fonti", "licenze"}` (cache 1 minuto) |
| `GET /api/rete/cabine?regione=08` | libera | GeoJSON di punti delle cabine primarie con posizione: `cod_ac`, `gestore`, `cod_cp_ed`, `nome_cp_ed`, `comuni_serviti`, `esito` del raccordo, `livello` (peggiore tra i trasformatori: VERDE, GIALLO, ARANCIONE, ROSSO; `null` = altro gestore o senza dato), `trasf` (trasformatori per livello), `data_saturazione`; `senza_posizione` = cabine non ancora collocate; licenza ODbL nella collezione (cache 30 minuti) |
| `GET /api/rete/comuni?regione=08` | libera | `[{"istat", "nome", "concessionario", "servito_in_parte", "pieno", "strisce", "livello", "quota", "trasf", "cabine", "data", "dato_disponibile"}]`: criticità del comune (classificazione di EuGEnio: L = livello più alto tra i trasformatori, q = quota con livello L; q > 0,5 colore pieno, altrimenti strisce tra il livello precedente e L; VERDE nessun riempimento); `concessionario: false` = il distributore è un altro; `servito_in_parte: true` = comune con trasformatori e-distribuzione servito in parte da un altro distributore (colorato con la sua criticità) (cache 30 minuti) |
| `GET /api/rete/cabine/comune/{istat}` | libera | cabine che servono il comune con i loro trasformatori e livelli, criticità del comune, data del dato |
| `GET /api/rete/interruzioni/attive?regione=08` (oppure `bbox=lon_min,lat_min,lon_max,lat_max`) | libera | GeoJSON di punti delle interruzioni in corso: `id`, `comune`, `comuni`, `causa` (Guasto, Lavoro Programmato), `codice_causa`, `clienti`, `inizio`, `ripristino_previsto`, `durata_finora_min` (cache 2 minuti) |
| `GET /api/rete/interruzioni/comune/{istat}?da=aaaa-mm&a=aaaa-mm` | libera | statistiche delle interruzioni del comune da quando il server le raccoglie (`dal`): `totale`, `per_mese` (`n`, `guasti`, `programmati`, `clienti`, `durata_media_min`, `durata_max_min`), `per_causa`, `attive`, `ultime` (al più 50). Durata stimata = ultima lettura in cui l'interruzione compare − inizio dichiarato (errore fino a 15 minuti); medie e massimi solo sulle interruzioni chiuse (cache 5 minuti) |

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
| 429 | limite orario superato per la tua rete: **aspetta** i secondi di `Retry-After` (dal 09/11/2026; `X-EuGEnio-Limite` dice quale limite), non ritentare a raffica |
| 502 | la fonte esterna (ortofoto, PVGIS, Zornade) non risponde |
| 503 | dati non ancora sul server, server occupato (previsioni, file), quota di Zornade dell'ora esaurita, fonte molto richiesta (con `Retry-After`) |

### 4.5 ter Proposte di DB topografici all'archivio comune («Aggiungi DBTR», 07/11/2026)

| Metodo e percorso | Accesso | Cosa fa |
|---|---|---|
| `POST /api/dbtr/inizia` | **Turnstile**; 3 file al giorno per rete | JSON `regione` (`er`, `lom`, `fvg`, `lig`), `comune` (nome), `istat` (6 cifre, facoltativo), `intero` (comune intero), `formato` (`zip` o `gpkg`), `dimensione` (byte, al massimo 300 MB), `consenso: true` (obbligatorio), `impronta` (SHA-256 del file, facoltativa) → `id`, `gettone`, `pezzo_byte`, `pezzi`; 503 se la coda è piena |
| `PUT /api/dbtr/{rid}/pezzo/{n}` | gettone in `X-EuGEnio-Dbtr` | pezzo `n` del file nel corpo della richiesta (32 MB, l'ultimo più corto) |
| `POST /api/dbtr/{rid}/fine` | gettone | chiude il caricamento: impronta, controllo leggero (zip senza percorsi «..», link simbolici, bombe di compressione; o GeoPackage) → `stato: "ricevuto"`; 422 e file cancellato se rifiutato |
| `GET /api/dbtr/{rid}` | gettone (intestazione o `?g=`) | stato della proposta: `ricevuto`, `in preparazione`, `in attesa di approvazione`, `controlli non superati`, `approvato`, `installato`, `rifiutato`, con un messaggio |
| `DELETE /api/dbtr/{rid}` | gettone | ritira la proposta prima dell'approvazione (file cancellati) |

Il caricamento è un'azione **della persona**, con il suo consenso esplicito: un agente non la fa da solo né la ripete in
serie. Il server prepara una proposta alla volta, a bassa priorità; l'archivio comune cambia **solo dopo l'approvazione**
nella pagina interna di Stato Critico (non pubblica). Nessun dato personale richiesto. La lettura
nel browser (senza server) resta sempre possibile.

## 5. Limiti e protezioni (cosa un agente può e non può fare)

- **Limiti per rete in finestra mobile di un'ora** (IPv4 per indirizzo, IPv6 per rete /64), valori predefiniti: rotte dei
  dati (comuni, mappa, meteo, clima, Legge 10, gradi giorno, catalogo delle ortofoto e degli strati, analisi) **600**
  richieste; previsioni **20**; conversioni **200**; report **60**; stime di Dati climatici **600**; download di Dati
  climatici **30**; edifici geolocalizzati **2.000**; ricerche Zornade **120**; dal 09/11/2026 tessere di ortofoto
  **12.000** e di particelle e contorni **12.000** chieste alla fonte, tessere del terreno da generare **6.000**, tessere già
  in copia sul server **60.000** (tetto comune); confronti PVGIS **60**; profili d'orizzonte **120**; edifici OpenStreetMap al
  volo **300** richieste che chiamano Overpass (comprese le tessere OSM dei contorni) e **3.000** dalla copia; verifiche anti-robot **60**;
  proposte di DB topografici **3 al giorno** (finestra di 24 ore) e **60 pezzi all'ora**; stato della rete elettrica
  (rotte del § 4.10, dal 17/11/2026) **1.200** richieste.
  Oltre: **429** con `Retry-After` (secondi finché si libera il 10 % del limite) e `X-EuGEnio-Limite` (il tipo).
- **Cloudflare** ferma le raffiche su `/api/` (circa 60 richieste in 10 secondi per IP, blocco breve; le ortofoto escluse).
- **Tetti per tutto il sito**: due previsioni alla volta (le altre aspettano fino a 30 s, poi 503); due report e due file di
  Dati climatici alla volta; quota oraria di Zornade condivisa (oltre: 503); ritmo verso le fonti di ortofoto e verso PVGIS;
  edifici OpenStreetMap: una chiamata a Overpass alla volta e al massimo 300 all'ora per tutto il sito (oltre: 503).
- **Verifica anti-robot (Cloudflare Turnstile)** sulle rotte che costano o consumano quote: `previsione`, `patrimonio`,
  `geocodifica`, `particella`, `estrazione`, `edifici_osm`, `dbtr` (cioè `POST /api/previsione`, `POST /api/patrimonio`,
  `GET /api/geocodifica`, `GET /api/particella`, `POST /api/storici/estrai`, `GET /api/edifici/osm`, `POST /api/dbtr/inizia`). La pagina ottiene un gettone Turnstile nel browser, lo scambia con
  `POST /api/sessione` e manda la sessione (30 minuti, legata alla rete) nell'intestazione `X-EuGEnio-Sessione`.
  **Un agente non deve aggirarla** (niente risolutori di captcha, niente riuso di gettoni altrui): o guida la persona a
  usare la pagina, o lavora in un browser che la persona controlla e vede, oppure usa un proprio **mirror** (§ 7), dove
  la verifica è spenta.
- **Pagine che richiedono un browser**: Previsioni (caricamento), Patrimonio, Modelli 3D e tutte le pagine 3D (WebGL),
  Ortofoto, Importa DXF/IFC, Aggiungi edifici (DB topografico), Cambiamento climatico, Costi energetici Sanità e le pagine in lavorazione (calcoli nel
  browser). Le rotte libere del § 4 bastano per meteo, clima, Legge 10, gradi giorno, stime, orizzonte, PVGIS e report.
- **Cache**: le tessere di ortofoto e strati hanno `Cache-Control: public` e `ETag` (usa `If-None-Match`); orizzonte e
  PVGIS sono tenuti in copia dal server (stesso punto, nessuna nuova chiamata). Le previsioni meteo cambiano più volte
  al giorno; lo storico una volta al giorno (per i comuni delle regioni che il server aggiorna ogni giorno; per gli altri
  comuni serviti lo storico può fermarsi a una data precedente e la previsione usa la climatologia: le date nella risposta
  lo dicono). **Tieni tu una copia** delle risposte che riusi, invece di richiederle.
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

**F. Modello 3D e producibilità FV di un edificio** (dall'08/11/2026 i passi 2–4 usano pagine **in lavorazione, non
accessibili**: per ora si resta in Modelli 3D, che ha anch'essa ombre, fotovoltaico, confronto con PVGIS e obblighi)
1. `modelli3d.html`: cerca l'indirizzo (esempio «viale Ghirotti 286», «Cesena»), fai clic sull'edificio, «Genera il 3D» (solo dove c'è un archivio di sagome:
   i comuni della Romagna preparati dal DBTR, elencati con il riquadro in `/edifici3d/archivi.json`; fuori zona la pagina
   lo dice). Un punto dentro un cortile non sceglie l'edificio da solo: trascina il punto sul corpo o fai clic. Per vedere il funzionamento:
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

- **Dati di mercato (GME, EEX)**: PUN, prezzi zonali, PSV del GME, IGI, TTF e future **non sono mai esposti** né
  scaricabili: sono solo per uso interno. Non cercarli nelle API, non provare nomi alternativi (risposta 403), non
  chiederli. Dall'11/11/2026 si pubblicano invece, nella pagina Indici dei prezzi e in `dati/prezzi/indici.json`: i prezzi
  che le centrali pubblicano nei listini delle convenzioni (Intercent-ER, Consip), il **PSV day-ahead pubblicato da ARERA**
  (CC BY-SA 4.0) e il **PFOR,t ricostruito da EuGEnio** (elaborazione nostra con il metodo ARERA; nessun valore TTF).
  Le pagine «GME» restano segnaposto finché non c'è una licenza scritta del GME.
- **Visure e persone**: è vietato usare i dati catastali per **re-identificare persone**. EuGEnio Visure toglie intestatari
  e codici fiscali; non chiedere né ricostruire chi possiede un immobile. Il sito non usa mai lo SPID della persona.
- **Norme UNI**: il modulo con le metodiche UNI non è pubblico; le analisi che lo richiedono dicono «analisi non
  disponibile in questa installazione». EuGEnio non pubblica prospetti o estratti di norme UNI, né testi LEED. Dei dati del GSE
  (CC BY-NC-SA 3.0 IT) EuGEnio pubblica solo i codici `COD_AC` delle aree convenzionali; i perimetri si leggono dal vivo
  dal browser con l'attribuzione e non entrano mai in report, immagini o file scaricabili (salvo il GeoJSON separato di
  Cabine primarie, con la licenza del GSE dichiarata).
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
| Trattamento aria (4 pagine) | solo il comune e gli anni della serie | tutti i dati dell'UTA, i gruppi di ore e i risultati; il foglio Excel compilato si prepara nel browser |
| Patrimonio | il file degli edifici, a blocchi (indirizzi cercati nell'ANNCSU sul server, il resto e le particelle a Zornade, che riceve solo il testo dell'indirizzo, i dati catastali o le coordinate); scartato a fine elaborazione; le risposte di Zornade in una cache tecnica senza legame con chi ha cercato, cancellata dopo 12 mesi | colonne `visura_…` e valori per sede |
| Excel/ODS in qualunque pagina | il file, per la conversione in CSV (non salvato) | — |
| Ricerca di un luogo (Ortofoto, Modelli 3D) | indirizzo o foglio e particella, come Patrimonio | — |
| Ortofoto e strati | le coordinate delle tessere viste | — |
| Modelli 3D, Edificio, Fotovoltaico | comune (clima), punto (orizzonte), aree FV e punto (PVGIS, inoltrati al JRC); fuori dal DBTR il punto per gli edifici OpenStreetMap (all'API Overpass va solo il centro della cella di ~200 m, non il punto esatto; risposta in copia sul server per 30 giorni, senza legame con chi l'ha chiesta) e, in Veneto, il riquadro di ~800 m attorno allo stesso centro al servizio WFS della Regione del Veneto; per la firma energetica solo il periodo, non i consumi | consumi mensili, correzioni, modello importato |
| Importa DXF/IFC | nulla (solo le tessere della mappa) | il file DXF/IFC |
| Aggiungi edifici (DB topografico) | nulla, se la persona non spunta il consenso; con il consenso il file del DB topografico (nessun dato personale chiesto: solo comune e regione; conservato fino all'approvazione, poi parte dell'archivio pubblico CC BY, o cancellato al rifiuto o al ritiro) | il file e gli edifici ricavati (IndexedDB del sito, finché la persona non li toglie) |
| EuGEnio Visure | nulla: gira sul PC o sul server dell'ente | visure in PDF, risultati |
| Cambiamento climatico, Costi energetici Sanità (e le pagine in lavorazione Comunità energetiche ed Emissioni) | nulla dei dati della persona (si leggono file pubblici e l'elenco dei comuni) | curve orarie, firma, dati del cogeneratore |
| Report | i risultati da impaginare (generati in memoria, non salvati) | — |
| Contattaci | nulla: prepara l'email nel programma di posta | — |
| Newsletter e avvisi | email, servizi scelti, regioni (fino a 3) e comuni (fino a 5), in listmonk sul server di EuGEnio finché la persona resta iscritta; nessun tracciamento di aperture e clic | — |

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
| `/dati/prezzi/indici.json` | indici dei prezzi (11/11/2026), rifatto ogni notte: `anni` [anno prima, anno in corso], `sezioni` (`elettricita`, `gas`) con gli `indici`: `id`, `centrale`, `titolo`, `unita` (€/MWh o €/Smc), `fonte`, `licenza`, `nota`, `lotti` {lotto: {`nome`, `varianti` {fascia o uso: {anno: 12 valori o null}}}}, `lotto_predefinito`, `dettagli` (per il PFOR: trimestre, metodo, provvisorio). Citare le fonti indicate (Intercent-ER, Consip, ARERA CC BY-SA 4.0, EuGEnio) |
| `/dati/indicatori/indice.json`, `/dati/indicatori/RR.json` | indicatori di spesa energetica della sanità |
| `/dati/suolo/italia.json`, `/dati/suolo/RR.json` | «Suolo e aree agricole» (22/11/2026, fase 16, costruiti dal worker): `voci` (suolo, consumi, colture), `anni`, `periodi` (anno del flusso → [carta iniziale, carta finale]), `rev`, `riferimenti` (ISPRA, ISTAT, incrocio agricolo e confronto ISMEA), `italia` e `regioni` con `sup`, `pop`, `suolo`, `consumi`, `bilancio` [lordo, ripristini, netto], `agricolo`, `colture` per anno (ha); `RR.json` con le `province` e i `comuni` (codice delle mappe, superficie, suolo consumato e incremento netto per anno). Citare «Elaborazione EuGEnio su dati ISPRA/SNPA, ISTAT e Copernicus» (CC BY 4.0) |
| `/dati/ispra_fattori_emissione.json` | fattori di emissione ISPRA usati nella pagina Emissioni |
| `/esempi/*.csv` | file di esempio **inventati** (consumi, patrimonio, valori per sede, CER, consumi mensili per fascia del confronto delle convenzioni) |
| `/edifici3d/archivi.json` | archivi di edifici 3D presenti sul server, in ordine di affidabilità, con nome, licenza, attribuzione e riquadro (un archivio DBTR per comune in `/edifici3d/cc-by/er/<comune>/prodotti/`; PMTiles e celle di contesto letti dalla pagina); `lidar` indica l'archivio delle falde LiDAR (solo quando la pipeline ne ha scritto l'indice; dal 09/11/2026 b `lidar/indice.json` ha l'elenco `celle.falde` e `celle.alberi` delle celle di 0,01° che esistono, e la pagina chiede solo quelle: le altre darebbero 404); `archivi.json` e gli `indice.json` si riconvalidano sempre (`Cache-Control: no-cache` con ETag), i PMTiles restano in copia un giorno |
| `/edifici3d/immobili_pa/indice.json`, `/edifici3d/immobili_pa/immobili_pa_2023_<versione>.pmtiles`, `/edifici3d/immobili_pa/enti_2023_<versione>.json` | immobili delle PA (17/11/2026): indice (anno, nomi dei file `pmtiles` ed `enti`, conteggi, attribuzione, `gruppi` di enti) e tessere vettoriali PMTiles con gli strati `particelle` (poligoni dallo zoom 13) e `punti` (un punto per particella fino allo zoom 12 e i beni senza particella); proprietà `r` (riferimento AdE o `b<id bene>`), `t` (E edifici, T terreni, M entrambi), `n` (beni), `g` (gruppo di enti), `a` (primo ente), `tp` (tipologie), `s` (1 = senza particella), `e` (dal 22/11/2026: enti della particella, `",<id><p|u>,…,"`, p = in proprietà, u = in uso); `enti_…json`: `{"campi": ["id", "chiave", "nome", "gruppo", "sede", "beni", "fabbricati", "terreni", "particelle", "regioni"], "regioni": [...], "enti": [[...], …]}` (nessun codice fiscale). I nomi dei file cambiano a ogni rifacimento: leggili da `indice.json` |
| `/strumenti/psicro_UTA.xlsx` | foglio di calcolo delle trasformazioni dell'aria (UTA), stesse formule della pagina Trasformazioni (UTA) (14/11/2026) |
| `/llms.txt` | rimando breve a questo file |
| `/novita.html`, `/novita.xml` | registro delle versioni del sito (pagina e feed Atom, la voce più recente per prima) |

## 10. Contatti e segnalazioni

- Pagina **Contattaci**: `https://eugenio.statocritico.it/contatti.html` (prepara un'email per `eugenio@statocritico.it`).
- Privacy: `privacy@statocritico.it`.
- Errori nel codice o in questo file: **issue su GitHub** `https://github.com/statocritico/eugenio/issues`, con pagina o
  rotta, parametri, risposta ricevuta e data. Un agente può preparare il testo; l'invio lo fa la persona.

## 11. Da dove è ricavato questo file

Per aggiornarlo, rileggi: `fase4-server/servizio/app.py` e i router `storici.py`, `psicro.py`, `edifici.py`, `edifici_osm.py`, `ortofoto.py`, `strati.py`,
`pvgis.py`, `orizzonte.py`, `analisi.py` (rotte e parametri; `interno.py` è riservato e non va citato);
`fase4-server/servizio/protezione.py` e `config.py` (limiti, Turnstile); `modello.py` (CSV e risposta delle previsioni);
`report_servizi.py` (tipi di report); `fase7-territorio/territorio/patrimonio.py` (colonne del Patrimonio);
`fase5-sito/parti/testata.html` (menu e stati); `fase5-sito/sito/*.js` (parametri dell'indirizzo: `URLSearchParams`);
`fase5-sito/sito/privacy.html` e `licenza.html`; `fase10-edifici3d/ortofoto/*.toml` (fonti e citazioni); README delle
fasi 4, 5, 7, 10, 11, 12, 13. Il test `fase4-server/tests/test_agenti.py` controlla che le due copie siano identiche, che la
versione in testa sia quella del sito e che i percorsi `/api/…` citati qui e le rotte pubbliche dell'app coincidano.
