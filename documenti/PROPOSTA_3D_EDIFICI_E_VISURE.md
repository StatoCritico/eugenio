# EuGEnio – Ricostruzione 3D degli edifici, analisi energetiche e visure catastali

Esito della discussione del 30/10–01/11/2026. **Nessuna modifica applicata al codice**: questo file raccoglie
decisioni, verifiche, progetto e cose da fare. Sostituisce il file `PROPOSTA_3D_EDIFICI_2026-10-30.txt`.

---

## 1. Obiettivo

Nuova pagina di EuGEnio: l'utente sceglie un edificio sulla mappa (o carica un proprio modello DXF/IFC/DWG) e
EuGEnio ricostruisce in 3D l'edificio, gli edifici vicini e il terreno, poi calcola:

- ombre e percorso del sole nel ciclo diurno;
- ore di sole e irradiazione su tetti e facciate (annua, mensile, giorno tipo);
- producibilità fotovoltaica con le perdite per ombreggiamento, usando il clima orario già archiviato
  (ERA5 corretto verso ICON, radiazione globale e diffusa per comune);
- confronto con PVGIS;
- analisi energetiche del patrimonio (§ 9);
- supporto a D.Lgs. 199/2021 (Allegato III) e prefattibilità LEED.

Sopra la mappa: ortofoto come livello d'immagine, con confini ed edifici sovrapposti.

---

## 2. Decisioni prese

| Tema | Decisione |
|---|---|
| Edifici da Zornade | **Niente scaricamento via API** (lo scraping massivo è motivo di sospensione del token). Zornade ha offerto l'estratto ER, ma è OpenStreetMap: **in ER non serve** (vedi § 4). Si resta in contatto per le altezze LiDAR che caricheranno da novembre e per le regioni senza buon DB topografico. |
| Base edifici in ER | **DBTR – Unità volumetrica (UVL)**, CC BY 4.0, con altezza per corpo di fabbrica. |
| Licenze | Archivio **CC BY** (DBTR, aggregati, LiDAR) separato dall'archivio **ODbL** (OSM). Ogni edificio porta la licenza della sua sagoma. |
| Tetti | Inclinazione stimata dal DSM; se le altezze sono irregolari il tetto è piano. L'utente disegna i rettangoli FV e corregge inclinazione e orientamento. |
| Edifici a più corpi | Ogni corpo è un prisma con quota di base, altezza e tetto propri; l'edificio resta un'unità per selezione, totali e report (§ 7). |
| Metodiche UNI | Si implementano anche senza risposta di UNI; testi, prospetti e formule restano in un **modulo privato** fuori dal repository (§ 10). |
| Pipeline | Notturna e automatica, una zona alla volta (Rimini → Forlì-Cesena → Ravenna → resto ER), aggiornamento annuale a rotazione (§ 11). |
| Avvisi | **Nessuna email**: pagina di stato nascosta protetta da Cloudflare Access (§ 12). |
| Ortofoto | RER 2023-24 in ER; ortofoto regionali in CC BY altrove; AGEA 2022–24 RGB per siti puntuali (§ 6). |
| Piani | Stimati dall'altezza; per il patrimonio dell'utente presi dalle visure catastali (§ 8). |
| Visure | Programma **EuGEnio Visure** in due versioni: personale (.exe) e per enti (Docker), basato su `visura-api` (§ 13). |
| SPID | Il sito pubblico **non** usa mai lo SPID dell'utente: le credenziali restano sul PC dell'utente o sul server dell'ente. |

---

## 3. Verifiche fatte

**Catasto AdE.** Il download in blocco (GML, semestrale, CC BY 4.0) contiene solo particelle e fogli, **niente
fabbricati**. Le particelle servono a dividere gli aggregati e a collegare edificio e particella; le sagome dalle
particelle non si ricavano.

**Aggregati strutturali (Protezione Civile).** Nazionale, CC BY 4.0, shapefile su GitHub, ~17,9 milioni di
poligoni, da DB topografici regionali più fabbricati catastali. Versione 2020–21, senza altezze; edifici adiacenti
spesso uniti. Migliore base nazionale in CC BY.

**DBTR ER – UVL.** CC BY 4.0, GeoPackage. Altezze "qualitative" (DSM con errore di circa ±3 m; valori bassi
arrotondati a 3/6/9 m). Da verificare: se l'altezza è riferita alla gronda o al colmo, e se c'è il numero di piani.

**DTM ER 5x5 m** (dicembre 2025). CC BY 4.0, include i LiDAR RER2022 e RER2023/24; 4 quadranti TIFF (~4,9 GB),
EPSG:7791, anche WCS.

**LiDAR RER2023/24 e RER2025/26.** DTM 0,5 m (WMS/WCS), DSM primo e ultimo impulso, LAS classificati (anche classe
Edifici), CC BY 4.0. DSM e LAS **solo su richiesta** all'Archivio Cartografico. RER2025/26 in corso fino a coprire
tutta la regione.

**Banca dati PST (MASE).** DTM, DSM primo e ultimo impulso a 1 m, GeoTIFF, CC BY 4.0, EPSG:4326; rilievi
2008–2013, circa metà del territorio (coste e fiumi). Download dal visualizzatore sim.mase.gov.it senza
registrazione, **non automatizzabile**. Utile fuori dall'ER, con controllo degli edifici cambiati dopo il rilievo.
Portale offline fino al 7/11/2026.

**LiDAR nazionale PNRR (progetto SIM del MASE).** Tutta Italia (~302.000 km²), **DTM e DSM a 25 cm**, almeno
8 punti/m² in pianura, precisione dichiarata 8 cm in verticale e 15 cm in orizzontale; voli da luglio 2025, dati
pubblicati a blocchi nella stessa app PST. Non verificati: regioni già pubblicate, nuvole di punti, licenza.
Diventerebbe la fonte LiDAR principale per tutta Italia.

**OpenStreetMap.** ~54 % degli edifici italiani (studio 2022), molto variabile tra regioni; altezze rare. ODbL.

**Strato edifici di Zornade** (risposta di Zornade). 16,3 milioni di edifici, **tutti da OSM**, ODbL; altezze nel
10,1 % dei casi in ER e nel 10,3 % in Italia (5,4 m di media). I 20,5 milioni citati nel loro sito sono un residuo
di GlobalBuildingAtlas (CC BY-NC) non usato. Un file per edificio con la sagoma OSM è un database derivato ODbL;
aggregati e mappe sono opere prodotte. Attribuzione: «© OpenStreetMap contributors (ODbL 1.0)» più «Dati elaborati
da Zornade» con link.

**GlobalBuildingAtlas.** Altezze e LoD1 in CC BY-NC: non utilizzabili nei dati di EuGEnio.

**GHSL GHS-BUILT-H.** Altezza media su celle di 100 m, CC BY 4.0: solo valore di quartiere.

**Termini di Zornade** (18/09/2026). Uso libero anche commerciale; dati mostrabili e conservabili per il tempo che
serve al servizio. Vietati: violazioni del GDPR, re-identificazione di persone, rivendita dei dati grezzi senza
attribuzione o contro le licenze, carichi eccessivi. Limite 10.000 richieste/ora per token; attribuzione con link nel
piano gratuito; le attribuzioni delle fonti restano sempre obbligatorie. Differenze rispetto ai testi del progetto
(da allineare): la ridistribuzione non è vietata in generale, l'estrazione massiva è motivo di sospensione e non un
divieto di conservare, la pulizia della cache a 12 mesi resta una scelta di privacy.

**PVGIS.** 30 chiamate/s per IP; niente CORS (si chiama dal server); parametro `userhorizon` per passare il nostro
orizzonte.

**Ortofoto.** Vedi § 6.

**visura-api** (Zornade, AGPL). Servizio REST con Chromium automatico su SISTER. Credenziali personali della
convenzione SISTER (non condivisibili) o SPID con approvazione dal telefono. Restituisce foglio, particella,
subalterno, categoria, classe, consistenza, rendita, indirizzo, partita e intestatari; **piano e superficie non sono
tra i campi elencati** e non risulta il salvataggio dei PDF. Il README avverte che l'automazione potrebbe violare i
termini di SISTER e che i registri contengono dati personali.

**Firma del codice.** Dal 1/3/2026 un certificato vale al massimo **460 giorni**, chiave su hardware dedicato. Un .exe
firmato con marcatura temporale resta valido dopo la scadenza. SignPath Foundation: gratis per progetti open source.
Certum Open Source: cloud da 49 €, kit 69 €. SmartScreen tratta allo stesso modo OV ed EV: l'avviso può comparire
comunque nelle prime settimane.

---

## 4. Catena di ripiego delle fonti

| Dato | Ordine |
|---|---|
| Sagoma | modello dell'utente → DBT regionale con unità volumetriche (ER: UVL) → aggregati Protezione Civile divisi con le particelle → OSM (costruzioni recenti, archivio ODbL separato) |
| Altezza | modello dell'utente → LiDAR più recente che copre l'edificio (PNRR → RER → PST), DSM − DTM → DBT → OSM `height` o `building:levels`×3 → GHSL 100 m → valore dell'utente (segnalato come stima) |
| Terreno | DTM regionale (ER 0,5 m o 5 m) → LiDAR PNRR/PST → TINITALY 10 m (INGV) |
| Orizzonte lontano | Copernicus DEM 90 m, raggio 20–30 km (già usato in fase 3) |
| Ombre di alberi ed edifici | DSM primo impulso dove disponibile |

Per ogni dato si salvano **fonte** e **qualità**, come la colonna "fonte del punto" di Patrimonio. Fuori dall'ER la
scelta tra aggregati (CC BY) e OSM (ODbL) si fa regione per regione, secondo la completezza.

---

## 5. Architettura della pagina 3D

**Sito**
- WebGL: MapLibre GL (edifici estrusi con base e altezza per corpo, terreno, WMS) e three.js (ombre in tempo reale).
  Librerie ospitate sul sito, non da CDN. `mappa3d.js` resta per le barre di Patrimonio.
- Ombre calcolate nel browser (Web Worker): profilo d'orizzonte per punto (36–72 direzioni), poi l'ombra di ogni ora
  è una consultazione. Clima orario dall'archivio, componente diretta ricavata, trasposizione di Perez, modello FV
  tipo PVWatts (pvlib come riferimento).

**Server**
- Edifici in PMTiles e DTM/DSM in COG, file statici serviti da Caddy.
- PVGIS chiamato dal server come controllo.

**Modelli importati**
- DXF e IFC con librerie aperte (ezdxf, IfcOpenShell); DWG con LibreDWG o conversione dell'utente col convertitore
  gratuito di ODA; anche glTF/OBJ, CityJSON, GeoJSON.
- Passaggio di posa (due punti noti o aggancio alla sagoma catastale).
- Elaborati solo nel browser, senza salvarli sul server.

**Tetti dal DSM, per corpo**
1. Punti del DSM dentro il corpo, meno una fascia di bordo di ~1 m (LAS classe Edifici o DSM ultimo impulso).
2. Altezza = mediana di (DSM − DTM).
3. Si prova piano unico, due falde (capanna), quattro (padiglione); si sceglie il più semplice che riduce davvero
   l'errore.
4. Errore alto (indicativamente RMSE > 0,3–0,5 m, da tarare) o pendenza < ~5° → tetto piano.
5. Edificio presente nella sagoma recente ma non nel rilievo → «non presente nel rilievo», fonte successiva.

**Aree FV dell'utente**
- Rettangoli sulla vista dall'alto, agganciati ai lati del corpo, con inclinazione e orientamento precompilati e
  modificabili.
- Montaggio aderente o su telai (tetto piano: inclinazione e passo tra le file, con ombra tra le file).
- Fasce di rispetto, dimensione del modulo, conteggio dei moduli e potenza automatici.
- Ombre su più punti per rettangolo; confronto con PVGIS (`userhorizon`).

---

## 6. Ortofoto

| Ordine | Fonte | Uso |
|---|---|---|
| 1 | **ER: RER 2023-24**, 20 cm, CC BY 4.0, WMS `RER2023_24_RGB` | proxy con cache sul server (da confermare con la Regione) |
| 2 | **Ortofoto regionali in CC BY** verificate una per una (Toscana 2023, Bolzano 2023, …), un TOML per regione; punto di partenza: editor-layer-index di OSM | proxy con cache |
| 3 | **AGEA 2022–2024 RGB** dal GeoPortale AGEA, CC BY 4.0 (note legali, Reg. UE 2023/138) | scaricate a mano per siti puntuali (massimo 20 tessere per richiesta, OTP, limite giornaliero), ridotte a 50 cm, conservate come ortofoto del sito; fuori dalla pipeline |
| 4 | Sentinel-2 cloudless 2016 (EOX, CC BY 4.0, 10 m) | contesto di zona |
| 5 | WMS del Geoportale Nazionale (AGEA 2012, 50 cm; licenza ambigua) | solo dal vivo, senza cache |

**Esclusi:** AGEA infrarosso e foto originali (convenzione per le PA: solo fini istituzionali); WMS regionali AGEA
(ER «Utilizzo ristretto», Veneto «Tutti i diritti riservati») finché la Regione non conferma; Google, Esri, Bing;
EOX 2018+ (CC BY-NC-SA).

Il link «Termini e Condizioni» del download AGEA porta solo all'informativa privacy: nessun limite d'uso aggiuntivo.
Nei report ogni figura con ortofoto porta la sua licenza e la sua citazione.

---

## 7. Edifici con corpi di altezza diversa

**Da dove vengono i corpi**

| Caso | Metodo |
|---|---|
| DBTR UVL (ER) | già pronti, divisi dove cambia l'altezza di gronda; esclusi camini, abbaini, lucernari |
| LiDAR senza UVL | raggruppamento delle celle di (DSM − DTM) con altezza simile (tolleranza ~1–1,5 m), scarto delle aree sotto ~20–25 m², confini allineati alla sagoma |
| UVL + LiDAR | confini UVL, altezza dal LiDAR (mediana per corpo); un salto netto dentro un corpo UVL lo divide e viene segnalato |
| Nessuno dei due | una sola altezza per la sagoma, segnalata come stima; l'utente può dividere il corpo con una linea e dare un'altezza a ciascuna parte |

**Dati per corpo:** sagoma, quota del terreno (minimo o mediana del DTM), altezza di gronda, altezza di colmo e
falde se inclinato, piani, fonte e qualità, edificio di appartenenza (DBTR, aggregato o particella).

**Effetti sui calcoli**
- Ombre: i corpi alti ombreggiano tetti e facciate di quelli bassi (caso importante per il FV).
- Aree FV: disegnate sul tetto di un corpo, con la sua inclinazione e quota.
- Involucro: le pareti in comune non disperdono, ma la parte che sporge sopra il corpo più basso sì; lo stesso per le
  pareti in comune con edifici confinanti; si sommano volumi, superfici disperdenti, tetti e pavimenti a terra.
- Facciate: irraggiamento solo sulle parti esposte, segmento per segmento.

---

## 8. Numero di piani e superfici

**Stima, per corpo:** piani ≈ (altezza di gronda − sovralzo del piano terra) ÷ interpiano, arrotondato.
Interpiano tipico: residenziale ~3,0 m; uffici e scuole 3,3–3,6 m; ospedali 3,8–4,5 m; capannoni e palestre un
piano. Uso da tag OSM, categoria catastale o dichiarazione dell'utente. Taratura sull'interpiano medio della zona
dove OSM ha altezza e piani; controllo con le sezioni di censimento ISTAT (edifici per numero di piani).

**Superfici:** lorda = Σ (area del corpo × piani); netta ≈ 0,80–0,85 × lorda, o il valore dell'utente.

**Precedenza:** valore dichiarato nel CSV → visura catastale → stima dall'altezza. Nel report la fonte di ogni numero.

**Planimetrie catastali:** non accessibili (solo titolari o delegati, dati personali). **Visure:** riportano piano,
categoria, consistenza e superficie catastale, ma vanno ottenute una per una → programma EuGEnio Visure (§ 13).

**Colonne facoltative nel CSV di Patrimonio:** piani fuori terra, piani interrati, superficie lorda, superficie netta,
superficie catastale, anno di costruzione.

---

## 9. Analisi energetiche

| # | Analisi | Dati | Valore |
|---|---|---|---|
| 1 | Indicatori geometrici: volume lordo, superficie lorda e netta, superficie disperdente, **S/V**, pareti esposte per orientamento, pareti in comune | corpi, altezze, piani | base di tutto; S/V è nei limiti di legge (DM 26/6/2015) |
| 2 | Consumi normalizzati: kWh/m², kWh/m³, €/m² per sede | Valori per sede + superfici | confronto fra le sedi di un patrimonio |
| 3 | **Firma energetica**: consumi mensili ↔ gradi giorno reali | consumi + archivio meteo | carico di base, sensibilità al clima, sedi anomale |
| 4 | Classifica di priorità del patrimonio | 1 + 2 + 3 + 6 + convenzioni | dove intervenire prima |
| 5 | Fabbisogno stimato con le metodiche UNI | geometria + ipotesi su involucro ed epoca | consumo reale vs atteso, scenari |
| 6 | FV sui tetti con le ombre, per edificio e per patrimonio, con autoconsumo se ci sono dati orari | tetti, DSM, clima | già nel progetto |
| 7 | Comunità energetiche: FV e consumi per **cabina primaria** | 6 + perimetri GSE (licenza da verificare) | molto attuale per enti e comuni |
| 8 | Apporti solari sulle facciate: surriscaldamento estivo, apporti invernali persi | facciate + ombre | schermature e vetri |
| 9 | Ostruzione del cielo e accesso alla luce (sky view factor) | scena 3D | luce naturale, prefattibilità LEED |
| 10 | Pompe di calore: COP/SCOP con temperature orarie reali | meteo + fabbisogno | sostituzione delle caldaie |
| 11 | Solare termico per l'acqua calda sanitaria | tetti + ombre + clima | ospedali |
| 12 | Tetti freddi e tetti verdi | tetti + ortofoto | LEED Heat Island, CAM |
| 13 | Clima che cambia: tendenza dei gradi giorno dal 1940 | fase 9 | consumi futuri |
| 14 | Obblighi di legge: potenza minima di rinnovabili (D.Lgs. 199/2021), S/V e zona | 1 + 6 | domanda frequente |

**Avvertenze:** i prezzi GME/EEX sono per uso interno; nelle analisi economiche pubbliche solo convenzioni o prezzi
pubblici (ARERA). Superficie netta ed epoca di costruzione sono i dati più incerti: chiederli nel modulo.

**Primo pacchetto:** 1, 2, 3, 6. Poi 4 e 14, poi il resto.

---

## 10. Metodiche UNI

- Si implementano UNI/TS 11300, EN ISO 52016, UNI 10349 anche senza risposta di UNI.
- Non si ridistribuiscono testi, prospetti, estratti o formule. Paolo legge le formule.
- Coefficienti, prospetti e passaggi presi dalle norme stanno in un **modulo o file di dati privato**, sul server ma
  fuori dal repository (come la fase 2); il codice pubblico contiene solo la struttura del calcolo.
- Aggiornare nel RIEPILOGO la decisione del 27/10/2026 («non si elaborano con strumenti di IA»).

---

## 11. Pipeline notturna degli edifici

- **Unità di lavoro:** tessera LiDAR 1×1 km. Scarica → elabora → salva risultati → cancella i grezzi.
- **Finestra:** 3:30–7:00 (dopo i mercati), container separato (1 CPU, 4 GB), pausa se c'è una previsione in coda.
- **Coda:** Rimini → Forlì-Cesena → Ravenna → resto ER → altre regioni; solo tessere con edifici; ripresa dalla
  tessera successiva; zone grandi divise per comune.
- **Per tessera:** corpi, altezze, falde, qualità; DSM ridotto a 1 m (int16, decimetri) per le aree urbane.
- **Salvaguardie:** stop sotto 20 GB liberi; quota di download per notte regolabile; tessere che falliscono più volte
  saltate e segnalate; registro delle attribuzioni per zona.
- **Aggiornamento annuale:** ogni giorno la zona più vecchia; si rielaborano solo le tessere con fonte cambiata.
- **Altre regioni:** un TOML per zona con fonti e licenze; senza LiDAR la zona passa con qualità più bassa.

**Stime per la Romagna** (da misurare sulla prima zona)

| | Rimini | Forlì-Cesena | Ravenna |
|---|---|---|---|
| Superficie | ~865 km² | ~2.380 km² | ~1.860 km² |
| Tessere con edifici | ~300 | ~800 | ~650 |
| Dati scaricati | ~20 GB | ~50 GB | ~40 GB |
| Tempo | 1–3 h | 2–7 h | 2–6 h |
| Spazio che resta | ~0,35 GB | ~0,7 GB | ~0,6 GB |

**Automatizzabile oggi:** DTM 0,5 m RER (WCS), DTM 5 m, DBTR UVL, aggregati Protezione Civile, OSM.
**Dipende dalla Regione:** DSM e LAS RER (link → automatico; disco → elaborazione sul PC e caricamento dei soli
risultati). **Non automatizzabili:** PST/PNRR MASE (finché non c'è un'interfaccia), ortofoto AGEA.

---

## 12. Pagina di stato nascosta

- `eugenio.statocritico.it/interno/edifici.html`, fuori da menu e mappa del sito, `X-Robots-Tag: noindex`
  (non nel `robots.txt`).
- Dati: `GET /api/interno/edifici/stato` (JSON), da `stato.json` riscritto a ogni tessera.
- Protezione: Cloudflare Access su `/interno/*` e `/api/interno/*`, solo l'email di Paolo; Caddy rifiuta le
  richieste senza intestazione di Access.
- Contenuto (sola lettura): zona in corso e avanzamento; coda e date; ultime 30 notti; esiti per qualità; errori;
  spazio su disco; versioni delle fonti. Eventuali comandi via ssh.

---

## 13. EuGEnio Visure

**Scopo:** dal CSV geolocalizzato di Patrimonio (comune catastale, sezione, foglio, particella) ottenere tutte le
visure in PDF ordinate e il CSV arricchito con piani, superfici e categorie.

**Architettura**

```
eugenio-visure/
  motore/       chiamate a visura-api, salvataggio PDF, lettura di piani e superfici, CSV arricchito, ripresa
  connettori/   SISTER · area riservata (SPID/CIE, anche come incaricato dell'ente) · in futuro PDND
  desktop/      avviatore .exe
  server/       servizio Docker (pagina web, pianificazione, archivio)
```

`visura-api` resta un componente separato, chiamato tramite la sua interfaccia REST, **senza fork**.

**Versione personale (.exe)**
- Avviatore leggero e firmato: installa o aggiorna `visura-api` in una cartella locale (Python + Chromium), lo avvia
  su localhost e lo usa.
- Un utente, login interattivo con qualunque accesso (SPID per i propri immobili, SISTER per un professionista,
  incaricato per un ente).
- Riepilogo prima di partire (visure stimate, eventuale costo, tempo), conferma, ritmo di 3–5 s tra le richieste,
  ripresa dopo interruzione, nuovo login se la sessione scade.

**Versione per enti (Docker)**
- `docker-compose` con l'immagine di `visura-api` e il servizio EuGEnio Visure.
- Pagina web interna: elenco immobili, stato, download di PDF e CSV, aggiornamento su richiesta.
- Pianificazione (es. trimestrale) a rotazione e con ritmo lento.
- Archivio storico con **segnalazione delle variazioni** (subalterni nuovi o soppressi, cambi di categoria o
  consistenza).
- Registro degli accessi; autenticazione dell'ente (proxy con SSO/LDAP) e ruoli.
- **Login:** predefinito il **login assistito** (alla data prevista l'operatore riceve un avviso e approva l'accesso
  dal telefono); opzione esplicita **SISTER diretto** con credenziali custodite fra i segreti dell'ente.
- Tetto di costo per ogni lavoro.

**Risultati**

```
Visure_AAAA-MM-GG/
  <Comune>_<Belfiore>/F<foglio>_P<particella>/sub_<n>.pdf
  indice.csv                  tutte le visure con percorso, categoria, piano
  patrimonio_con_visure.csv   CSV di partenza + colonne nuove
  registro.txt                esiti e motivi
```

**Colonne aggiunte:** numero di subalterni, categorie e uso prevalente (B/2 e D/4 case di cura e ospedali, B/5
scuole, A/10 uffici…); piani trovati, fuori terra, interrati, piano più alto (T, PT, S1, S2, R, ammezzato, sottotetto,
intervalli «T-1-2»); superficie catastale (categorie A, B, C); **consistenza in m³ per le categorie B** (volume);
data della visura ed esito. **Intestatari e codici fiscali non entrano nel CSV**: restano solo nei PDF, sul PC o sul
server dell'ente.

**In EuGEnio:** la pagina Patrimonio riconosce le colonne nuove (anche il formato di `visura-api` e i PDF delle visure,
letti solo nel browser). Al server di EuGEnio non arriva niente.

**Aggiornamenti di visura-api**
- Solo **versioni approvate**: elenco pubblicato da EuGEnio con l'impronta di ogni versione; una versione nuova si
  prova, si aggiunge all'elenco e da lì arriva da sola agli utenti.
- Ritorno alla versione precedente se quella nuova fallisce i controlli di avvio.
- Docker: immagine fissata alla versione approvata.

**Contributi da proporre a Zornade (upstream):**
1. login manuale in una finestra visibile (credenziali mai nel programma);
2. salvataggio dei PDF delle visure;
3. lettura di piano, superficie catastale e consistenza in m³.

**Firma dell'.exe:** prima SignPath Foundation (gratis per open source, costruzione da GitHub Actions); in
alternativa Certum Open Source (cloud da 49 €). Rinnovo ogni ~15 mesi; marcatura temporale sempre.

**Avvertenze:** termini di SISTER e dell'area riservata (l'automazione potrebbe violarli: chiedere all'Agenzia o a
Zornade prima di distribuire, responsabilità scritta chiaramente nel programma); costi delle visure; manutenzione
quando l'Agenzia cambia le pagine; per le PA la via ufficiale a lungo termine è la PDND.

---

## 14. Email

### 14.1 Archivio Cartografico – Regione Emilia-Romagna (da inviare)

Indirizzo: pagina «Contatti» del Geoportale ER (non trovato un indirizzo diretto).

> **Oggetto:** Richiesta prodotti LiDAR RER2023/24 e chiarimenti sulle licenze – progetto open source EuGEnio
>
> Gentile Archivio Cartografico,
>
> sono Paolo Bianco e curo **EuGEnio** (eugenio.statocritico.it), un servizio gratuito e senza fini commerciali per
> l'analisi energetica degli edifici. Il codice è open source (AGPL-3.0) e i risultati sono pubblicati in CC BY 4.0.
> Usiamo già il DTM 5x5 m e il DBTR, citando la Regione come fonte.
>
> Stiamo sviluppando una funzione che stima l'ombreggiamento e la producibilità fotovoltaica dei tetti. Vi scrivo per
> alcune richieste.
>
> **1. Prodotti LiDAR RER2023/24** (e, quando collaudati, RER2025/26), rilasciati in CC BY 4.0 secondo il Geoportale:
> **DSM primo e ultimo impulso** (GeoTIFF) e **nuvola LAS/LAZ classificata**, in particolare le classi Terreno ed
> Edifici. Area iniziale: province di **Rimini, Forlì-Cesena e Ravenna**, poi il resto della regione.
>
> **2. Modalità di accesso.** Il nostro server elaborerebbe una tessera da 1 km alla volta, di notte, cancellando i
> dati grezzi dopo l'elaborazione, e ripeterebbe il controllo una volta l'anno per recepire gli aggiornamenti. Chiedo
> se sia possibile:
> - un accesso scaricabile per tessera (elenco di link o servizio WCS), che useremmo con un ritmo limitato da
>   concordare;
> - oppure, in alternativa, una consegna una tantum (link o supporto fisico), con indicazione di eventuali costi.
>
> **3. Prodotti derivati.** Chiedo conferma che possiamo pubblicare in CC BY 4.0 le altezze e le falde dei tetti per
> edificio ricavate da questi dati, citando «Regione Emilia-Romagna – rilievo LiDAR RER2023/24».
>
> **4. Ortofoto RER 2023-24 (CC BY 4.0).** Chiedo conferma che si possano usare dal WMS come sfondo, con una cache sul
> nostro server per non sovraccaricare il vostro servizio.
>
> **5. Ortofoto AGEA 2023.** Il WMS `agea2023_rgb` del Geoportale riporta «Utilizzo ristretto dei dati». Dal 26/08/2026
> le note legali del GeoPortale AGEA dichiarano le ortofoto RGB in GeoTIFF riutilizzabili in CC BY 4.0, ai sensi del
> Regolamento (UE) 2023/138. Chiedo se possiamo considerare in CC BY 4.0 anche la componente RGB servita dal vostro
> WMS, citando «AGEA», e se prevedete di aggiornarne la licenza nel catalogo.
>
> **6. DBTR – Unità volumetrica.** È previsto l'aggiornamento delle altezze con i nuovi rilievi LiDAR?
>
> Resto a disposizione per ogni chiarimento.
> Cordiali saluti,
> Paolo Bianco – EuGEnio, un servizio di Stato Critico

### 14.2 Risposta a Zornade (da inviare a hello@zornade.com o al contatto diretto)

> Ciao [nome],
>
> grazie mille, e grazie per le correzioni: cambiano davvero il progetto.
>
> Ripensandoci con i tuoi numeri, per l'Emilia-Romagna l'estratto non ci serve: la Regione pubblica in CC BY il DBTR
> con le unità volumetriche, che ha già un'altezza per ogni corpo di fabbrica, e stiamo chiedendo DSM e LAS del rilievo
> LiDAR RER2023/24. Così in ER restiamo tutti in CC BY e non mescoliamo licenze.
>
> Mi interessa invece molto il vostro progetto di novembre sul LiDAR del MASE. Quando usciremo dall'ER, le vostre
> altezze da LiDAR, e gli estratti per le regioni senza un buon DB topografico, potrebbero essere la base. Ti chiederei
> di tenermi aggiornato; a quel punto useremo l'ODbL come mi hai spiegato, con «© OpenStreetMap contributors (ODbL
> 1.0)» e «Dati elaborati da Zornade» col link.
>
> Una curiosità sul LiDAR: i 15 cm sono la griglia o la precisione? Negli articoli che ho trovato si parla di DTM e DSM
> a 25 cm, con precisione di 15 cm in orizzontale e 8 cm in verticale.
>
> L'attribuzione resta dove già usiamo la vostra API (geolocalizzazione del patrimonio), e il caso documentato lo
> faccio volentieri: scriverò un articolo su Stato Critico (statocritico.substack.com) su come EuGEnio ricostruisce gli
> edifici in 3D, citando Zornade per la parte catastale e, più avanti, per le altezze. Se vi va, potete riprenderlo o
> linkarlo dal vostro blog.
>
> Grazie ancora,
> Paolo

*Da valutare se aggiungere:* una domanda su `visura-api` (termini di SISTER, disponibilità ad accogliere i tre
contributi del § 13).

---

## 15. Programma delle cose da fare

### Subito
- [ ] Inviare l'email all'Archivio Cartografico ER (§ 14.1).
- [ ] Inviare la risposta a Zornade (§ 14.2), eventualmente con la domanda su `visura-api`.
- [ ] Preparare due o tre visure vere anonimizzate (una B/2 o B/5, una A, una D) e indicare quale accesso usa l'ente
      (SISTER con convenzione o profilo di incaricato).
- [ ] Dopo il 7/11/2026: controllare nell'app «Download Banca Dati PST» se ci sono livelli PNRR (25 cm, 2025–26,
      «SIM») e se coprono la Romagna; scaricare una tessera di prova.

### Allineamenti nel progetto (testi, nessuna funzione nuova)
- [ ] Termini Zornade del 18/09/2026: correggere README fase 7, `zornade.py`, RIEPILOGO, F.A.Q. e pagine del sito
      («ridistribuzione vietata», «estrazione massiva»).
- [ ] Avviso che i dati catastali non sostituiscono visure ed estratti ufficiali; regola di non re-identificare persone.
- [ ] RIEPILOGO: nuova decisione sulle metodiche UNI (§ 10).
- [ ] Copiare in RIEPILOGO e DA_FARE le decisioni di questo file e rigenerare lo zip.

### Fase A – Edificio e contesto in ER (dati già disponibili)
- [ ] Scaricare DBTR UVL e DTM 5 m; verificare attributi UVL (gronda o colmo, piani).
- [ ] Aggregati Protezione Civile e OSM in cache come archivi separati (CC BY / ODbL).
- [ ] PMTiles degli edifici e COG del DTM serviti da Caddy.
- [ ] Pagina 3D: selezione dell'edificio, contesto 250 m, corpi estrusi, terreno, ombre animate.
- [ ] Tetti piani correggibili, divisione manuale dei corpi, rettangoli FV, ombre e producibilità, report PDF/Excel/ODS.
- [ ] Stima dei piani e superfici; colonne facoltative nel CSV di Patrimonio.
- [ ] Analisi 1, 2, 3 e 6 (§ 9).

### Fase B – Ortofoto e affinamenti
- [ ] Proxy con cache per il WMS RER 2023-24 (dopo la conferma della Regione).
- [ ] Facciate, orizzonte lontano (Copernicus DEM), confronto PVGIS con `userhorizon`.
- [ ] Analisi 4 e 14.

### Fase C – LiDAR e pipeline
- [ ] Pipeline notturna a tessere con TOML per zona, DSM ridotto, falde per corpo.
- [ ] Pagina di stato nascosta con Cloudflare Access.
- [ ] Prima zona: Rimini; misurare spazio e tempi reali.
- [ ] Integrare DSM/LAS RER (secondo la risposta della Regione) e, quando disponibile, il LiDAR PNRR.
- [ ] Import DXF/IFC.

### Fase D – EuGEnio Visure
- [ ] Lettura dei PDF delle visure e CSV arricchito (provabile senza credenziali, con le visure di esempio).
- [ ] Importatore in Patrimonio (formato `visura-api` e PDF, lettura solo nel browser).
- [ ] Proporre a Zornade i tre contributi a `visura-api`.
- [ ] Versione personale: avviatore .exe con versioni approvate; firma con SignPath (o Certum Open Source).
- [ ] Versione per enti: Docker, pagina web, pianificazione con login assistito, archivio e variazioni.
- [ ] Verifica dei termini di SISTER prima della distribuzione; in futuro connettore PDND.

### Fase E – Resto d'Italia e analisi avanzate
- [ ] Verifica regione per regione di DB topografici con altezze e ortofoto in CC BY.
- [ ] Altezze LiDAR di Zornade (ODbL) per le regioni senza DBT, quando disponibili.
- [ ] Metodiche UNI (modulo privato), analisi 5, 7–13.
- [ ] Articolo su Stato Critico: come EuGEnio ricostruisce gli edifici in 3D (impegno con Zornade).

---

## 16. Fonti principali

- Zornade – llms.txt: https://zornade.com/llms.txt
- visura-api: https://github.com/zornade/visura-api
- Aggregati strutturali: https://rischi.protezionecivile.gov.it/en/approfondimento/national-dataset-italian-structural-aggregates/
- Catasto senza fabbricati: https://www.rivistageomedia.it/survey-and-positioning/cartografia-catastale-italia-disponibile-per-il-download-ma-mancano-i-fabbricati
- DBTR UVL: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/database-topografico-regionale/immobili-e-antropizzazioni/edificato/layer-6
- DTM ER, novità 2025: https://geoportale.regione.emilia-romagna.it/notizie/servizi-e-applicazioni/dtm-novita-2025
- DTM 0,5 m RER: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/altimetria/layer-60
- Prodotti LiDAR RER2023-24: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/quadri-di-unione/layer-16
- RER2025/26: https://geoportale.regione.emilia-romagna.it/in-primo-piano/rer25-26-aggiornamento-set-26
- Ortofoto RER 2023-24: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/immagini/layer-14
- Ortofoto AGEA 2023 ER: https://geoportale.regione.emilia-romagna.it/catalogo/dati-cartografici/cartografia-di-base/immagini/layer-16
- GeoPortale AGEA, note legali: https://geoportale.agea.gov.it/legal-notes
- Convenzione AGEA PA 2022–2024: https://agea.gov.it/portale-apigw/documents/d/agea/schema-della-convenzione-per-la-concessione-della-licenza-d-uso-dei-prodotti-aerofotogrammetrici-di-agea-2022-2024-pdf
- Ortofoto Veneto: https://www.regione.veneto.it/web/ambiente-e-territorio/ortofoto
- Ortofoto Toscana 2023: https://geodati.gov.it/resource/id/r_toscan:66ca3807-815a-4bd1-b626-98ca240d72a2
- Ortofoto PCN: https://www.alspergis.altervista.org/data/ortofoto_pcn.html
- EOX Sentinel-2 cloudless: https://cloudless.eox.at/pricing
- App PST: https://sim.mase.gov.it/portalediaccesso/mappe/#/viewer/new
- Piattaforma PST: https://www.geocorsi.it/N1604/nuova-piattaforma-online-per-il-download-dei-dati-pst.html
- LiDAR PNRR, stato aprile 2026: https://www.gisinfrastrutture.it/2026/04/ottime-notizie-per-il-dtm-ad-alta-precisione-di-tutta-litalia/
- LiDAR PNRR, avvio: https://www.rivistageomedia.it/survey-and-positioning/al-via-la-realizzazione-del-nuovo-modello-altimetrico-del-territorio-italiano
- PVGIS API: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
- OSM, completezza in Italia: https://iris.uniroma1.it/retrieve/32c1587a-0b38-4b80-bb32-3b3490acdff8/Salvati_Official-Statistics_2022.pdf
- Validità certificati di firma: https://sslinsights.com/code-signing-certificate-validity-reduced-460-days/
- Certum Code Signing: https://shop.certum.eu/code-signing.html
- SignPath Foundation: https://signpath.org/
