# Bozza – articolo per Stato Critico (statocritico.substack.com)

> **Nota per Paolo (da togliere prima di pubblicare).** Bozza del 04/11/2026 (Fase E, § 15 della proposta: «Articolo su
> Stato Critico: come EuGEnio ricostruisce gli edifici in 3D», impegno preso con Zornade nel § 14.2). Descrive solo ciò
> che c'è nel codice al 04/11/2026; prima di pubblicarla:
> 1. pubblica il sito `?v=20261104a` e il rebuild dell'api (sezioni Previsioni, Fase B, C, D ed E di
>    `AGGIORNAMENTO_2026-11-04.md`), altrimenti le pagine citate non sono online;
> 2. se nel frattempo sono arrivati i dati veri degli edifici di Rimini (Fase A, `prepara`), togli le frasi sulla demo
>    sintetica nel paragrafo «Edifici in 3D»;
> 3. ricontrolla la riga sulla RER 2023-24 (oggi «uso da confermare» finché l'Archivio Cartografico non risponde);
> 4. la parte su Zornade è scritta in modo da non anticipare la risposta del § 14.2: adattala dopo averla inviata.
> Nessun dato di mercato, nessun valore delle norme UNI, nessun contenuto del GSE.

---

# Come EuGEnio ricostruisce gli edifici in 3D (e le altre novità d'autunno)

*EuGEnio è il servizio gratuito e open source di Stato Critico per chi gestisce l'energia di edifici pubblici e
patrimoni immobiliari: eugenio.statocritico.it. Il codice è su GitHub in AGPL-3.0, i dati elaborati e i report sono in
CC BY 4.0.*

Negli ultimi giorni EuGEnio è cambiato parecchio. Il menu è nuovo, le previsioni hanno una modalità in più e, soprattutto,
è arrivata la prima parte di un progetto a cui pensavo da tempo: ricostruire gli edifici in tre dimensioni, con il
terreno e gli edifici vicini, per capire quanto sole arriva su tetti e facciate. Qui racconto come funziona, da dove
vengono i dati e, con la stessa franchezza, cosa ancora non c'è.

## Un menu a cinque gruppi

Le pagine sono diventate troppe per una sola riga. Ora il menu ha cinque gruppi: **Clima e meteo** (dati climatici,
Legge 10, previsioni), **Patrimonio** (geolocalizzazione, ortofoto, LiDAR, modelli 3D, visure), **Edificio**,
**Cogenerazione** e **Fotovoltaico**. Le funzioni non ancora pronte hanno una pagina che dice cosa faranno, con quali dati
e a che punto siamo, senza numeri finti. Mi sembrava più onesto di una voce che porta a una pagina vuota.

## Previsioni: anche «solo clima»

La pagina Previsioni prevede i consumi con TiRex-2, un modello di previsione delle serie storiche, a partire dal file dei
consumi dell'utente e dal meteo del comune. Ora si può anche scegliere **«Solo clima»**: niente file, solo le grandezze
meteo osservate e previste per il comune, ognuna nella sua scheda con il suo grafico. Cambiare comune, o cliccare di
nuovo su quello scelto, toglie il file caricato: così non si rischia di prevedere i consumi di Rimini con il meteo di
Piacenza.

## Edifici in 3D: da dove vengono

Il punto di partenza, in Emilia-Romagna, è il **Database Topografico Regionale**, che descrive ogni edificio come un
insieme di «unità volumetriche»: corpi di fabbrica con la loro sagoma e la loro altezza. È in CC BY 4.0 e ha un pregio
enorme: un ospedale con una torre e un corpo basso non è un unico parallelepipedo, ma due corpi distinti, ciascuno con
la sua altezza. EuGEnio lavora proprio così: ogni corpo è un prisma con base, altezza e tetto propri, mentre l'edificio
resta un'unica cosa da selezionare, sommare e mettere nel report.

Sotto gli edifici c'è il **terreno**, dal modello digitale del terreno della Regione (a 5 m, e a 0,5 m dove c'è il
rilievo LiDAR 2023-24). Da corpi e terreno la pagina calcola, direttamente nel browser:

- volume, superfici, rapporto S/V e pareti esposte per orientamento (le pareti in comune con un altro corpo non
  disperdono, la parte che sporge sì);
- le **ombre** ora per ora e il percorso del sole;
- il sole su **tetti e facciate**, facciata per facciata, a pezzi di pochi metri;
- la **producibilità fotovoltaica** delle aree disegnate dall'utente sul tetto, con le perdite per ombreggiamento e
  l'orizzonte lontano delle colline e delle montagne (dal modello del terreno europeo Copernicus);
- il **confronto con PVGIS**, il servizio della Commissione europea, a cui passiamo il nostro orizzonte;
- la potenza minima di rinnovabili richiesta dal **D.Lgs. 199/2021** e, per un patrimonio, una classifica di priorità
  degli interventi.

Una precisazione importante: **oggi la pagina gira su un isolato sintetico** vicino a Rimini, inventato per provare
tutti i passaggi e dichiarato come tale sulla pagina e nei report. I dati veri della Regione vanno scaricati e preparati
sul server, una provincia alla volta, partendo da Rimini.

## Ortofoto: solo quelle che si possono usare

Sotto la mappa si può mettere un'**ortofoto**. Sembra banale, ma ogni ortofoto ha la sua licenza e molte di quelle che
si vedono online non si possono riusare. EuGEnio usa solo ortofoto con una licenza aperta scritta nella scheda ufficiale,
e sotto la mappa compaiono sempre licenza e citazione, anche nei PDF. Oggi le fonti sono:

- **Emilia-Romagna**, ortofoto 2023-24 a 20 cm (CC BY 4.0; l'uso tramite la nostra copia sul server è segnalato «da
  confermare» finché la Regione non risponde alla nostra richiesta);
- **Toscana** 2023, **Provincia di Bolzano** 2023 e **Provincia di Trento** 2015, tutte a 20 cm e in CC BY 4.0;
- per il resto d'Italia il mosaico Sentinel-2 2016 di EOX a 10 m, utile solo per orientarsi.

Le ortofoto si scaricano dalla fonte una volta sola e poi si servono da una copia sul server, a ritmo limitato: così non
pesiamo sui servizi delle Regioni.

## LiDAR: i tetti veri

L'altezza di un corpo dice poco sul tetto: piano, a capanna o a padiglione? Per saperlo serve il **LiDAR**, il rilievo
laser dall'aereo che misura la quota di ogni punto. EuGEnio ha una pipeline notturna che lavora a tessere di un
chilometro: scarica il rilievo, ricava per ogni corpo la forma del tetto, la pendenza e l'orientamento delle falde,
salva i risultati e cancella i dati grezzi. Si ferma se c'è una previsione da calcolare e riprende dalla tessera dopo.

Anche qui, con franchezza: **la pipeline è provata su un rilievo sintetico**. Per Rimini il terreno LiDAR della Regione
è già pubblico; le superfici (i DSM) sono in CC BY 4.0 ma si ottengono su richiesta, e la richiesta è partita. Il LiDAR
nazionale finanziato dal PNRR, a 25 cm, è in pubblicazione a blocchi: lo seguiamo.

## E il resto d'Italia?

Ho controllato regione per regione, nel catalogo nazionale dei dati territoriali e sui geoportali, quattro cose:
edifici con altezze, modello del terreno, superfici o LiDAR, ortofoto. Il risultato è nel repository
(`fase10-edifici3d/fonti/regioni.toml`), con licenza, collegamento, stato e data della verifica per ogni voce. In breve:

- le province autonome di **Trento** e **Bolzano** hanno quasi tutto in licenza aperta (Bolzano perfino in pubblico
  dominio per terreno e superfici);
- **Lombardia**, **Liguria** e **Friuli Venezia Giulia** pubblicano edifici con un'altezza o una quota per corpo, in
  CC BY 4.0; il **Veneto** le sagome, senza altezze;
- molte ortofoto recenti sono quelle dell'AGEA concesse alle Regioni, che non si possono riusare;
- diversi portali, soprattutto al Centro-Sud, non erano raggiungibili dal nostro ambiente di prova o non indicano una
  licenza: restano «in attesa» e verranno ricontrollati.

Per ogni nuova regione servirà un piccolo adattatore, perché ogni database topografico chiama le cose a modo suo.

## Due archivi, due licenze

I dati regionali sono quasi sempre in CC BY 4.0. Gli edifici di OpenStreetMap sono invece in ODbL, una licenza che
chiede di condividere allo stesso modo i database derivati. Per non mescolarle, EuGEnio tiene **due archivi separati**:
uno CC BY (DB topografici, terreno, LiDAR, aggregati della Protezione Civile) e uno ODbL (OpenStreetMap). Ogni edificio
porta la licenza della sua sagoma, e un edificio che prende un dato dall'archivio ODbL passa in quello ODbL, mai il
contrario.

Nell'archivio ODbL è pronto anche il posto per le **altezze degli edifici di Zornade**, utili nelle regioni senza un buon
database topografico e come confronto con quelle regionali: un lettore che accetta solo gli estratti consegnati
(nessuno scaricamento dalle loro API), scarta le altezze con licenze non commerciali e confronta le altezze corpo per
corpo. Oggi è provato su un campione sintetico. A Zornade, che ringrazio, EuGEnio deve già la parte catastale: la
geolocalizzazione del patrimonio usa le loro API per trovare la particella di ogni edificio («Dati elaborati da
Zornade», https://zornade.com), insieme all'archivio nazionale dei civici di Agenzia delle Entrate e ISTAT.

## Visure catastali, senza credenziali

Per stimare piani e superfici servono le visure catastali. **EuGEnio Visure** è un programma a parte, da usare sul
proprio PC: legge i PDF delle visure che l'utente ha già, toglie intestatari e codici fiscali prima di leggerle e
restituisce un file con categoria, consistenza, superficie e piani, da importare nella pagina Patrimonio. L'abbinamento
avviene nel browser: al server di EuGEnio arrivano solo comune, foglio e particella. Non chiede credenziali e non si
collega ai servizi dell'Agenzia delle Entrate: lo scaricamento automatico resta spento finché non sono chiari i termini
d'uso.

## Cosa non c'è (ancora)

- Le analisi che richiedono le **norme tecniche** (fabbisogno, pompe di calore, solare termico…) hanno solo la struttura
  del codice: le pagine dicono «analisi non disponibile in questa installazione». Le norme UNI sono protette e i loro
  contenuti non finiranno né nel sito né nel repository.
- Le analisi basate sui **prezzi dei mercati dell'energia** restano fuori dal sito finché non ci sono le licenze dei dati.
- I dati veri degli edifici e del LiDAR vanno ancora caricati, a partire da Rimini.

Il codice è aperto e le segnalazioni sono benvenute: github.com/statocritico/eugenio, oppure la pagina Contattaci del
sito.

---

**Fonti e attribuzioni** – Regione Emilia-Romagna, Database Topografico Regionale, DTM e ortofoto RER 2023-24 (CC BY
4.0); Regione Toscana, ortofoto 2023 (CC BY 4.0); Provincia autonoma di Bolzano, ortofoto 2023 (CC BY 4.0) e modelli
digitali (CC0); Provincia autonoma di Trento, ortofoto PAT 2015 (CC BY 4.0); Sentinel-2 cloudless 2016 by EOX IT Services
GmbH (CC BY 4.0, contiene dati Copernicus Sentinel modificati); Copernicus DEM; PVGIS © Unione europea; Open-Meteo (CC BY
4.0); © OpenStreetMap contributors (ODbL 1.0); Dati elaborati da Zornade (https://zornade.com); ANNCSU – Agenzia delle
Entrate e ISTAT (CC BY 4.0); Dipartimento della Protezione Civile, aggregati strutturali (CC BY 4.0).
