# Fase 11 – EuGEnio Visure

Stato al 04/11/2026 sera: **Fase D in codice** – lettore locale delle visure in PDF (`visure/`), importazione in
Patrimonio nel browser, avviatore per Windows con versioni approvate, versione Docker, proposte upstream
([`UPSTREAM.md`](UPSTREAM.md)), verifica delle condizioni d'uso (sotto). Provato su **visure sintetiche** (dati inventati):
le visure vere anonimizzate non sono ancora arrivate. Lo scaricamento automatico delle visure con `visura-api` resta
**non attivo** finché non sono chiariti i termini dell'Agenzia. Prima, 03/11/2026: progetto approvato, nessun codice.
Documento di riferimento: [`../documenti/PROPOSTA_3D_EDIFICI_E_VISURE.md`](../documenti/PROPOSTA_3D_EDIFICI_E_VISURE.md),
§ 13 e § 15 «Fase D».

## Scopo

Dal CSV geolocalizzato di Patrimonio (comune catastale, sezione, foglio, particella) ottenere tutte le visure in PDF
ordinate e il CSV arricchito con piani, superfici e categorie: i piani servono alla stima delle superfici della
[fase 10](../fase10-edifici3d/README.md) (§ 8: valore del CSV → visura → stima dall'altezza).

Dal 04/11/2026 la prima parte che funziona è la **lettura**: le visure le scarica l'utente come fa già (area riservata o
SISTER), EuGEnio Visure le legge sul suo computer e prepara i file per Patrimonio.

## Decisioni

- Programma separato **EuGEnio Visure**, in due versioni: personale (.exe) e per enti (Docker), basato su
  [`visura-api`](https://github.com/zornade/visura-api) di Zornade (AGPL), chiamato tramite la sua interfaccia REST,
  **senza fork**. (04/11/2026: il componente `visura-api` è previsto nell'elenco delle versioni approvate ma **non
  attivo**, vedi «Condizioni d'uso»; il lettore non lo usa.)
- Il sito pubblico **non usa mai lo SPID** dell'utente: le credenziali restano sul PC dell'utente o sul server dell'ente.
  Al server di EuGEnio non arriva niente.
- **Intestatari e codici fiscali non entrano nel CSV**: restano solo nei PDF, sul PC o sul server dell'ente.
- **`--includi-intestatari`** (decisione del 04/11/2026): l'opzione resta, **spenta di default** (casella non spuntata
  nella pagina locale); il file `intestatari_DATI_PERSONALI.csv` è solo per uso proprio, mai caricato su EuGEnio.
- **Modelli DXF/IFC pesanti** (decisione del 04/11/2026): l'avviatore li converte sul PC con il codice della fase 10
  (sezione «Conversione dei modelli DXF/IFC»); i file leggeri si aprono direttamente nella pagina Importa DXF/IFC del sito.
- Planimetrie catastali escluse (solo titolari o delegati, dati personali).
- I dati catastali non sostituiscono visure ed estratti ufficiali; vietato usarli per re-identificare persone (vale
  per tutto EuGEnio, vedi fase 7).

## Cosa c'è (04/11/2026, Fase D)

```
fase11-visure/
  visure/                    lettore (Python puro + pypdf), riga di comando e pagina locale
    lettore.py               visure per immobile e per soggetto, fabbricati e terreni, formato «etichette» e «tabella»
    regole.toml              TUTTE le espressioni regolari: si adattano qui alle visure vere, senza toccare il codice
    regole.py                caricamento delle regole (anche da zip) e file dell'utente che sostituisce singole voci
    piani.py                 «T-1-2», «S1-T», «PT», «da 1 a 3», ammezzato, sottotetto → livelli, fuori terra, interrati
    arricchisci.py           abbinamento delle unità agli edifici e colonne visura_… (stessa logica di visure_abbina.js)
    uscite.py                indice.csv, edifici_visure.csv, patrimonio_con_visure.csv, visure.json, registro.txt, PDF ordinati
    privacy.py               controllo di anonimato (comando `controlla`)
    web.py                   pagina locale su http://127.0.0.1:8770 (solo libreria standard)
    autotest.py              controllo di avvio con una visura sintetica incorporata (lo usa l'avviatore)
    sintetici.py             visure sintetiche in PDF per i test (reportlab, solo sviluppo)
  avviatore/                 EuGEnioVisure.exe: versioni approvate, aggiornamenti, firma
    avviatore.py, versioni_approvate.json, costruisci_pacchetto.py, eugenio_visure.spec, costruisci_windows.ps1,
    versione_windows.txt, requirements-build.txt, signpath-artifact-configuration.xml
  docker/                    Dockerfile e docker-compose.yml
  tests/                     67 test (lettore, abbinamento, parità con JavaScript, pagina locale, avviatore, browser)
  UPSTREAM.md                proposte a Zornade, all'Agenzia delle Entrate e alle librerie (bozze, non inviate)
../fase5-sito/sito/visure_abbina.js, visure_patrimonio.js   importazione nella pagina Patrimonio
../.github/workflows/visure-windows.yml                     test, .exe per Windows, firma SignPath, release
```

### Uso con Python (PC o server)

```bash
cd fase11-visure
python -m pip install -r requirements.txt            # solo pypdf
python -m visure leggi CARTELLA_DELLE_VISURE --patrimonio patrimonio.csv --ordina
python -m visure web                                 # pagina locale nel browser
python -m visure controlla visura.pdf                # dati personali ancora presenti? (prima di condividere)
python -m visure esempi --uscita prova               # visure sintetiche (serve reportlab: requirements-dev.txt)
```

`--patrimonio` accetta il file caricato in Patrimonio o il risultato scaricato dalla pagina (`patrimonio_geolocalizzato.csv`,
con `belfiore`, `foglio_catasto` e `mappale`: abbinamento più sicuro). `--regole mie.toml` sostituisce singole voci di
`regole.toml`. `--includi-intestatari` salva a parte, in `intestatari_DATI_PERSONALI.csv`, le righe degli intestatari:
solo per uso proprio.

Risultati (cartella `Visure_AAAA-MM-GG/`):

```
Visure_AAAA-MM-GG/
  indice.csv                  una riga per unità (fabbricati e terreni): file, pagina, tipo, data, comune, codice,
                              sezione, foglio, particella, subalterno, zona, microzona, categoria, classe, consistenza e
                              unità (vani, m², m³), superficie catastale (totale ed escluse aree scoperte), rendita,
                              indirizzo, piano, piani, piani fuori terra e interrati, piano più alto; per i terreni
                              qualità, porzione, superficie in m², redditi; esito (ok/parziale) e nota
  edifici_visure.csv          senza --patrimonio: una riga per particella con le colonne visura_…
  patrimonio_con_visure.csv   con --patrimonio: il file di partenza con le colonne visura_… (stesse righe e colonne)
  visure.json                 unità ed edifici insieme (lo legge anche la pagina Patrimonio)
  registro.txt                esito di ogni PDF, campi mancanti, unità non abbinate, righe personali tolte
  pdf/<Comune>_<Belfiore>/F<foglio>_P<particella>/sub_<n>.pdf   con --ordina (per soggetto: pdf/per_soggetto/)
```

Colonne `visura_…` per edificio: `visura_unita`, `visura_subalterni`, `visura_categorie` («A/10 ×2; C/6»),
`visura_uso_prevalente` (categoria con la superficie maggiore; le pertinenze C/2, C/6, C/7 contano solo se non c'è altro)
e `visura_uso` (residenziale, uffici, scuola, ospedale… come `usoDa` della fase 10), `visura_piani`,
`visura_piani_fuori_terra`, `visura_piani_interrati`, `visura_piano_piu_alto`, `visura_superficie_catastale` (somma
delle unità A, B, C), `visura_consistenza_m3` (somma delle B), `visura_rendita_euro`, `visura_terreni_m2`,
`visura_data`, `visura_indirizzo`, `visura_esito` (ok, verificare, nessuna_visura), `visura_nota`. Il prefisso evita di
confonderle con le colonne facoltative scritte dall'utente (`piani_fuori_terra`…), che hanno la precedenza.

**Abbinamento** (`arricchisci.py` e `visure_abbina.js`, provati uguali da un test): chiave «forte» dal risultato di
Patrimonio (Belfiore + foglio + mappale), poi «dichiarata» dal file dell'utente (comune per nome o codice Belfiore,
sezione, foglio, particella), senza zeri iniziali; comuni confrontati senza accenti né apostrofi (Forlì = FORLI'). Esito
«ok» se il comune coincide per codice e la sezione è certa, altrimenti «verificare».

### Importazione in Patrimonio (sito)

Pagina Patrimonio, passo **«Visure catastali (facoltativo)»**: si carica `indice.csv`, `edifici_visure.csv`,
`patrimonio_con_visure.csv` o `visure.json`; l'abbinamento si fa **nel browser** (`visure_abbina.js`, stessa logica
del Python) e ogni scheda mostra la riga «Visura»; CSV e GeoJSON scaricati contengono le colonne `visura_…`. I file di
EuGEnio Visure si possono caricare anche al passo 1: al server vanno solo `id;comune;sezione;foglio;particella` (o il
file di Patrimonio senza le colonne delle visure), le colonne delle visure restano nel browser e si riattaccano. Il
report PDF/Excel/ODS si genera sul server e quindi **non** contiene le colonne delle visure. Le colonne con dati
personali (intestatari, codici fiscali, nascite, diritti, quote) si scartano appena lette. Accetta solo CSV e JSON (un
foglio di calcolo andrebbe convertito dal server).

### Adattare il lettore alle visure vere

1. Con una visura anonimizzata: `python -m visure controlla visura.pdf` deve dire «nessun dato personale»; poi
   `python -m visure leggi visura.pdf --uscita prova` e guardare `registro.txt` e `indice.csv`.
2. Se un campo manca («manca: piano»…), copiare in un file `mie.toml` solo la voce di `regole.toml` da cambiare (per
   esempio `[campi]` → `piano = [...]`) e riprovare con `--regole mie.toml`; quando funziona, portare la voce in
   `regole.toml`, aggiungere la visura (anonimizzata) o un suo estratto sintetico ai test e ricostruire il pacchetto
   (`python avviatore/costruisci_pacchetto.py --aggiorna-elenco`).
3. Le tabelle si leggono per posizione: ogni cella va alla colonna con il titolo più vicino (`[tabella.colonne]` dice
   quali parole del titolo valgono per quale colonna).

### Dati personali

Le righe con intestatari, codici fiscali e partite IVA, date e luoghi di nascita, diritti e quote si tolgono dal testo
**prima** di cercare i dati dell'immobile, quindi non possono finire in `indice.csv` né nelle altre uscite (un test lo
controlla su tutti i PDF sintetici). Con `--includi-intestatari` (o la casella nella pagina locale) si salvano a parte in
`intestatari_DATI_PERSONALI.csv`, mai nei CSV per Patrimonio; la pagina Patrimonio scarta comunque queste colonne.
Niente va al server di EuGEnio. Le visure di esempio vere restano fuori dal repository.

### Versione personale: `EuGEnioVisure.exe` (avviatore)

L'.exe contiene Python, pypdf, l'elenco delle versioni approvate e il pacchetto del lettore della versione corrente. A
ogni avvio:
1. legge `versioni_approvate.json` (incorporato e, con la rete, quello del repository su `raw.githubusercontent.com`;
   solo HTTPS e host di GitHub, anche nei reindirizzamenti; le revoche dei due elenchi si sommano);
2. sceglie la versione approvata più recente compatibile (`minimo_avviatore`), non revocata e non fallita su quel PC;
3. prende il pacchetto (incorporato, già scaricato o dall'`url` della release) e ne controlla l'impronta **SHA-256**,
   che deve coincidere con l'elenco: un file diverso si cancella;
4. lo carica ed esegue il **controllo di avvio** (`visure.autotest`): se fallisce, segna la versione come fallita
   (`stato.json`) e torna alla precedente;
5. apre la pagina locale (o esegue i comandi: `EuGEnioVisure.exe leggi cartella`). Opzioni: `--non-aggiornare`,
   `--stato`. Dati in `%LOCALAPPDATA%\EuGEnio\Visure` (versioni, stato, `avviatore.log`).

**Approvare una versione**: test verdi, prova con visure vere anonimizzate, `python avviatore/costruisci_pacchetto.py
--aggiorna-elenco` (zip riproducibile: stesse sorgenti → stessa impronta), commit, tag `visure-v<versione>`: il workflow
pubblica la release con l'.exe e lo zip, e gli avviatori già installati la ricevono da soli. Dopo la pubblicazione ogni
cambiamento richiede un numero di versione nuovo (con `--revoca` si revoca l'impronta precedente della stessa versione).
Un test controlla che l'impronta nell'elenco sia quella delle sorgenti attuali.

**Costruzione**: su Windows `powershell -ExecutionPolicy Bypass -File avviatore\costruisci_windows.ps1` (venv, test,
pacchetto, controllo dell'impronta, PyInstaller, prova dell'.exe, impronte); oppure GitHub Actions
(`.github/workflows/visure-windows.yml`: test su Linux, .exe su `windows-2022`, firma SignPath se configurata, release sul
tag). Il 04/11/2026 lo spec è stato provato costruendo l'eseguibile **Linux** con PyInstaller 6.16.0 (stesso meccanismo:
pacchetto caricato dallo zip, controllo di avvio, lettura dei PDF sintetici); l'.exe Windows va costruito da Actions o
sul PC.

### Conversione dei modelli DXF/IFC (04/11/2026 notte)

Decisione del 04/11/2026: i disegni DXF e i modelli IFC si leggono nel browser (pagina **Patrimonio › Importa DXF/IFC**
del sito), ma i file pesanti (oltre 30–50 MB o molto complessi) si convertono sul PC. L'avviatore contiene quindi anche il
convertitore della fase 10:
- **comando** `EuGEnioVisure.exe modello edificio.ifc --uscita modello.geojson` (con Python: `python -m visure modello …`),
  con le stesse opzioni di `python -m edifici3d importa-modello`: `--crs EPSG:7791`, `--posa X1,Y1=LON1,LAT1 X2,Y2=LON2,LAT2`
  (X e Y nelle unità del disegno), `--rotazione`, `--unita`, `--edificio`, `--grande` (fino a 500 MB, 8 GB, 30 minuti);
- **pagina locale**: scheda «Modelli DXF/IFC» (`/modelli`) con file, sistema di riferimento o due punti, unità e «file molto
  grande»; il risultato si scarica come `.geojson` (stesso gettone e stessi controlli dell'Host della scheda delle visure);
- **controllo di avvio** `prova --modelli`: crea al momento un DXF e un IFC minimi e li converte nel processo separato;
- **codice**: `visure/modelli.py` chiama `edifici3d/importa.py`, che `costruisci_pacchetto.py` copia dalla fase 10 nel
  pacchetto approvato accanto a `visure/` (l'impronta SHA-256 dell'elenco copre anche lui: dopo ogni modifica di
  `importa.py` serve `costruisci_pacchetto.py --aggiorna-elenco`, controllato dal test dell'elenco); le librerie compilate
  (numpy, shapely, pyproj, ezdxf, IfcOpenShell, `requirements-modelli.txt`) sono nell'.exe: lo spec le raccoglie con
  `collect_all` e lascia fuori scipy e i plugin di IfcOpenShell che non servono (esportazioni, OpenCOLLADA);
- **processo separato**: nell'.exe e su Windows «spawn» (l'avviatore chiama `multiprocessing.freeze_support()`), con tetto
  di memoria via Job Object di Windows e tempo massimo; su Linux «fork» con `RLIMIT_AS` e `RLIMIT_CPU`;
- il pacchetto resta alla versione **0.1.0** (mai pubblicata): l'impronta nell'elenco è quella nuova.

Provato il 04/11/2026 dal container: eseguibile **Linux** costruito con lo stesso spec (PyInstaller 6.16.0, 137 MB, avvio
~2,5 s), `prova --modelli`, conversioni di DXF e IFC sintetici anche con `EUGENIO_MP=spawn`, risultati identici al Python;
immagine Docker con `--network none`, `--read-only`, `--cap-drop ALL`. L'.exe Windows va costruito da Actions o con
`costruisci_windows.ps1`, che ora provano anche la conversione dei modelli.

### Firma dell'.exe

Prima SignPath Foundation (gratis per open source, costruzione da GitHub Actions); in alternativa Certum Open Source
(cloud da 49 €, kit 69 €). Dal 1/3/2026 un certificato vale al massimo 460 giorni (rinnovo ogni ~15 mesi); marcatura
temporale sempre. SmartScreen può avvisare nelle prime settimane. **Certificati, chiavi e password mai nel repository**.

Passi con **SignPath Foundation** (da fare a mano, dopo la prima build riuscita su Actions):
1. domanda sul sito signpath.org per `statocritico/eugenio` (licenza AGPL-3.0, build pubbliche su GitHub Actions);
2. accettata la domanda, su app.signpath.io: progetto (slug, es. `eugenio-visure`), configurazione dell'artefatto
   copiata da `avviatore/signpath-artifact-configuration.xml`, criterio di firma `release-signing`, GitHub come sistema
   di build fidato, un utente CI con il suo token;
3. su GitHub, Settings → Secrets and variables → Actions: segreto `SIGNPATH_API_TOKEN`; variabili
   `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_POLICY_SLUG`;
4. tag `visure-v0.1.0` → il job `firma` manda l'.exe a SignPath e la release usa quello firmato (senza variabili il job si
   salta e la release contiene l'.exe non firmato).

Con **Certum Open Source** (certificato nel cloud SimplySign o su chiavetta, mai esportato): installare SimplySign Desktop
e Windows SDK, leggere l'impronta SHA-1 del certificato nel magazzino di Windows, poi `$env:EUGENIO_FIRMA_SHA1 = "<impronta>"`
e `costruisci_windows.ps1 -Firma` (signtool con marca temporale `http://time.certum.pl`, poi `signtool verify`).

### Versione Docker

```bash
cd fase11-visure
docker build --build-context fase10=../fase10-edifici3d -f docker/Dockerfile -t eugenio-visure:0.1.0 .
# lettura in blocco, senza alcuna rete:
docker run --rm --network none -v "$PWD/lavoro:/lavoro" eugenio-visure:0.1.0 leggi /lavoro/visure --uscita /lavoro/risultati
# modello DXF/IFC → GeoJSON per la pagina Modelli 3D, senza rete (dal 04/11/2026):
docker run --rm --network none -v "$PWD/lavoro:/lavoro" eugenio-visure:0.1.0 modello /lavoro/edificio.ifc --uscita /lavoro/modello.geojson
# pagina locale su http://127.0.0.1:8770 (porta pubblicata solo sul PC; container in sola lettura, senza privilegi):
docker compose -f docker/docker-compose.yml up --build
```

Dietro un proxy aziendale che ispeziona HTTPS: `docker build --secret id=ca_proxy,src=certificato.crt …` (il certificato
non resta nell'immagine). Il controllo di avvio gira già nella costruzione. Provata il 04/11/2026: costruzione, lettura
con `--network none`, pagina con `--read-only` e `--cap-drop ALL`.

### Test

```bash
cd fase11-visure
python -m pip install -r requirements-dev.txt
python -m pytest -q tests        # 71 test (67 + 4 della conversione dei modelli); con node e Playwright/Chromium anche
                                 # parità JS e prova nel browser
```

## Architettura

```
eugenio-visure/
  motore/       chiamate a visura-api, salvataggio PDF, lettura di piani e superfici, CSV arricchito, ripresa
  connettori/   SISTER · area riservata (SPID/CIE, anche come incaricato dell'ente) · in futuro PDND
  desktop/      avviatore .exe
  server/       servizio Docker (pagina web, pianificazione, archivio)
```

(04/11/2026: in codice ci sono la lettura, piani e superfici, CSV arricchito (`visure/`), l'avviatore (`avviatore/`) e
il servizio Docker del solo lettore (`docker/`); chiamate a visura-api, connettori, pianificazione e archivio aspettano
la verifica dei termini.)

**Versione personale (.exe)**: avviatore leggero e firmato che installa o aggiorna `visura-api` in una cartella locale
(Python + Chromium), lo avvia su localhost e lo usa; un utente, login interattivo con qualunque accesso (SPID per i
propri immobili, SISTER per un professionista, incaricato per un ente); riepilogo prima di partire (visure stimate,
costo, tempo), conferma, 3–5 s tra le richieste, ripresa dopo interruzione, nuovo login se la sessione scade.

**Versione per enti (Docker)**: `docker-compose` con `visura-api` e il servizio EuGEnio Visure; pagina web interna
(elenco immobili, stato, download PDF e CSV, aggiornamento su richiesta); pianificazione (es. trimestrale) a
rotazione e ritmo lento; archivio storico con **segnalazione delle variazioni** (subalterni nuovi o soppressi,
cambi di categoria o consistenza); registro degli accessi; autenticazione dell'ente (proxy con SSO/LDAP) e ruoli;
login predefinito **assistito** (l'operatore approva dal telefono), opzione esplicita **SISTER diretto** con
credenziali tra i segreti dell'ente; tetto di costo per lavoro.

**Risultati**

```
Visure_AAAA-MM-GG/
  <Comune>_<Belfiore>/F<foglio>_P<particella>/sub_<n>.pdf
  indice.csv                  tutte le visure con percorso, categoria, piano
  patrimonio_con_visure.csv   CSV di partenza + colonne nuove
  registro.txt                esiti e motivi
```

Colonne aggiunte: numero di subalterni, categorie e uso prevalente (B/2 e D/4 case di cura e ospedali, B/5 scuole,
A/10 uffici…); piani trovati, fuori terra, interrati, piano più alto (T, PT, S1, S2, R, ammezzato, sottotetto,
intervalli «T-1-2»); superficie catastale (categorie A, B, C); consistenza in m³ per le categorie B; data della
visura ed esito.

**In EuGEnio**: la pagina Patrimonio riconoscerà le colonne nuove (anche il formato di `visura-api` e i PDF delle
visure, letti solo nel browser). (04/11/2026: riconosce i file del lettore; il formato di `visura-api` è accettato in
forma generica – elenco JSON di unità con foglio, particella, sub… – da verificare su un esempio vero; la lettura dei
PDF direttamente nel browser non c'è: servirebbe pdf.js, oggi si usa il lettore locale.)

**Aggiornamenti di visura-api**: solo **versioni approvate** (elenco pubblicato da EuGEnio con l'impronta di ogni
versione); ritorno alla precedente se la nuova fallisce i controlli di avvio; in Docker immagine fissata alla
versione approvata. (04/11/2026: lo stesso meccanismo è in codice per il lettore; per `visura-api` la sezione
`visura_api` dell'elenco è vuota e «non attivo».)

**Contributi da proporre a Zornade (upstream)**: login manuale in una finestra visibile (credenziali mai nel
programma); salvataggio dei PDF delle visure; lettura di piano, superficie catastale e consistenza in m³. Bozze in
[`UPSTREAM.md`](UPSTREAM.md), con due proposte nuove (release con impronte, registri senza dati personali).

## Condizioni d'uso dei dati catastali (verifica del 04/11/2026)

Ricerca sulle fonti pubbliche; **non è una consulenza legale**: le conclusioni vanno confermate dall'Agenzia (bozza della
richiesta in `UPSTREAM.md`, § 2) e, per gli enti, dal loro ufficio legale o dal DPO.

**Cosa dicono le fonti**
- **Provvedimento dell'Agenzia delle Entrate prot. 460187 del 30/12/2024** (in vigore dal 1/1/2025): la consultazione
  telematica delle banche dati catastale e ipotecaria è aperta a chiunque, nell'area riservata (SPID, CIE, CNS o, nei casi
  previsti, credenziali Entratel, Fisconline o SISTER) ed è **gratuita** dal 1/1/2025; serve l'**accettazione preventiva
  delle condizioni generali** pubblicate sul sito (p. 3.2); chi consulta tratta i dati «sotto la propria responsabilità,
  quali titolari autonomi del trattamento» (p. 9.1); per gli incaricati che operano per conto di PA o di deleganti «i
  dati acquisiti non possono essere ceduti a terzi» (p. 6.3); l'Agenzia traccia gli accessi (p. 11.5) e può **limitare o
  sospendere l'accesso fino a 30 giorni** per attività anomale o interrogazioni eccessive rispetto ai limiti delle
  condizioni generali (p. 11.6); per le PA ci sono SMIDT, il Portale per i Comuni e la **PDND** (p. 6.1, 6.4, 6.6).
- **L. 311/2004, art. 1, commi 367–373** (spiegati dalla circolare dell'Agenzia del Territorio n. 5 del 20/04/2005):
  **divieto generale di riutilizzazione commerciale** dei dati catastali e ipotecari, cioè della loro cessione o fornitura
  a terzi, anche in copia, parziale o dopo elaborazione, salvo convenzioni con l'Agenzia; non è riutilizzazione la
  fornitura al solo committente su incarico scritto; sanzioni amministrative. Da ricontrollare su Normattiva la vigenza
  dopo il riordino dei tributi catastali (D.Lgs. 139/2024).
- **Decreto del Direttore dell'Agenzia del Territorio del 4/5/2007** (accesso telematico): i dati «possono essere
  utilizzati esclusivamente per i fini consentiti dalla legge» (art. 14), la titolarità resta all'Amministrazione
  (art. 13), le violazioni portano all'inibizione dell'accesso (art. 4 e 10).
- **Testo delle condizioni generali in vigore**: non trovato in una pagina pubblica; si legge nell'area riservata al
  momento dell'accettazione (attività manuale: salvarne una copia con la data).

**Conclusioni per EuGEnio**
1. **Lettore locale (questa fase)**: legge PDF che l'utente ha già ottenuto; non accede ai servizi dell'Agenzia, quindi
   non usa credenziali né rischia le sospensioni del p. 11.6. Resta il trattamento dei dati personali, di cui l'utente è
   titolare autonomo: per questo intestatari e codici fiscali sono esclusi dalle uscite e dal sito. **Rischio basso.**
2. **Colonne `visura_…`**: sono dati catastali elaborati. Restano dell'utente: non vanno al server di EuGEnio, non
   entrano nei report CC BY né nel repository, e la pagina lo dice. Se un ente le **pubblica o le cede a terzi** può
   ricadere nel divieto dei commi 367–373 o nel p. 6.3: la scelta è sua, con il suo ufficio legale. **Rischio medio, a
   carico dell'utente; avviso in pagina.**
3. **Scaricamento automatico con `visura-api`** (versione personale ed enti del § 13): le condizioni generali potrebbero
   vietare strumenti automatici e il p. 11.6 prevede la sospensione per interrogazioni eccessive. **Rischio alto finché
   l'Agenzia non risponde**: il componente resta spento (`visura_api.stato = "non attivo"`), si chiede per iscritto
   (`UPSTREAM.md`, § 2) e la responsabilità andrà scritta chiaramente nel programma. Per le PA la via a lungo termine
   resta la **PDND**.

Fonti: [provvedimento 460187/2024](https://informazionefiscale.it/IMG/pdf/provv_consultazione_banche_dati_30.12.24.pdf),
[circolare Agenzia del Territorio 5/2005](https://www.geototus.altervista.org/normativa/2005/Circ-5-20-04-2005.pdf),
[decreto Agenzia del Territorio 4/5/2007](https://assistenzaipocat.agenziaentrate.gov.it/KnowledgeBases/New_sister_tp/attach/decreto_accesso_telematico_04_05_07.pdf),
[provvedimento 152840/2025 (registri di partita)](https://www.dirittobancario.it/wp-content/uploads/2025/03/Provvedimento-Agnzia-Entrate-27-marzo-2025-n.-152840.pdf).

## Avvertenze

Termini di SISTER e dell'area riservata (l'automazione potrebbe violarli: chiedere all'Agenzia o a Zornade prima di
distribuire, responsabilità scritta chiaramente nel programma); costi delle visure (dal 1/1/2025 la consultazione
telematica è gratuita); manutenzione quando l'Agenzia cambia le pagine o il formato delle visure (regole in
`regole.toml`); per le PA la via ufficiale a lungo termine è la PDND. Il README di `visura-api` avverte che i
registri contengono dati personali e che piano e superficie non sono tra i campi restituiti.

## Piano di lavoro (§ 15, Fase D)

- [x] Lettura dei PDF delle visure e CSV arricchito (04/11/2026, su visure sintetiche; **da provare sulle visure vere
      anonimizzate**).
- [x] Importatore in Patrimonio (04/11/2026: file del lettore e JSON generico, abbinamento solo nel browser; PDF letti
      nel browser non previsti per ora).
- [ ] Proporre a Zornade i tre contributi a `visura-api` (bozza in `UPSTREAM.md`, da inviare).
- [x] Versione personale: avviatore .exe con versioni approvate (04/11/2026, spec provato su Linux); [ ] .exe costruito
      su Windows; [ ] firma con SignPath (o Certum Open Source).
- [x] Versione per enti, primo passo: Docker del lettore (04/11/2026). [ ] Pagina web dell'ente, pianificazione con
      login assistito, archivio e variazioni (dopo la verifica dei termini).
- [x] Verifica dei termini di SISTER (04/11/2026, ricerca sulle fonti pubbliche: sopra). [ ] Risposta scritta
      dell'Agenzia; in futuro connettore PDND.

Attività manuale di Paolo, prima di cominciare: preparare due o tre **visure vere anonimizzate** (una B/2 o B/5, una
A, una D) e indicare quale accesso usa l'ente (SISTER con convenzione o profilo di incaricato). Le visure di esempio
restano fuori dal repository finché non sono anonimizzate del tutto (controllo: `python -m visure controlla`).

## Fonti

- visura-api: https://github.com/zornade/visura-api
- pypdf: https://github.com/py-pdf/pypdf (BSD-3-Clause)
- PyInstaller: https://pyinstaller.org (GPL-2.0 con eccezione per i programmi costruiti)
- Validità certificati di firma: https://sslinsights.com/code-signing-certificate-validity-reduced-460-days/
- Certum Code Signing: https://shop.certum.eu/code-signing.html
- SignPath Foundation: https://signpath.org/
- Condizioni d'uso: vedi la sezione «Condizioni d'uso dei dati catastali».
