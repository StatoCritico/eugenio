# Fase 4 – Server di EuGEnio: eugenio.statocritico.it

**EuGEnio** (Europa + EGE) è il primo pezzo online di **Stato Critico**: gira sul server Oracle della
fase 1 ed è pubblicato tramite Cloudflare su
- `eugenio.statocritico.it` – il servizio (sito e API);
- `notizie.statocritico.it` – la **newsletter mensile automatica dei dati** (iscrizione, conferma, cancellazione).

La newsletter Substack (`statocritico.substack.com`) resta per gli articoli scritti a mano: è un'altra
cosa. Il sito principale `statocritico.it` (landing page, poi Astro su Cloudflare Pages) è nell'elenco
`DA_FARE.md`.

Container:

| Container | Cosa fa |
|---|---|
| `api` | FastAPI: riceve il CSV dei consumi, costruisce le covariate meteo e di calendario, chiama **TiRex-2** e restituisce la previsione probabilistica (quantili 10–90 %). Fa anche da proxy verso **Zornade** (la chiave resta sul server) e geolocalizza i patrimoni edilizi (ANNCSU + Zornade) |
| `worker` | previsioni meteo ogni 6 ore; storico meteo ogni giorno; **dati di mercato ogni notte alle 02:30** (fase 6), seguiti dalla **sorveglianza delle fonti delle convenzioni** (pagine di Intercent-ER, Consip, CET; email solo quando cambia qualcosa); **newsletter mensile** il 12 del mese (dopo l'aggiornamento del 10 dei dati di e-distribuzione); verifica comuni/confini il 2 del mese; **indirizzario ANNCSU** il 12 del mese (fase 7); avvisi per email |
| `caddy` | sito statico della fase 5 e instradamento verso l'API, solo dentro la rete Docker |
| `cloudflared` | **Cloudflare Tunnel**: collega il server a Cloudflare senza aprire porte; l'HTTPS lo fa Cloudflare |
| `listmonk` + `postgres` | newsletter automatica dei dati: liste, doppia conferma, cancellazione, invii |

Un quarto container, `open-meteo`, è facoltativo (istanza Open-Meteo propria, vedi fase 3).

## Come funziona la previsione

**Meteo previsto per ogni comune** (riportato al "clima" di riferimento ICON con i parametri della fase 3):

| Ore | Fonte |
|---|---|
| 0–48 | **ICON-2I** di Arpae (2,2 km) |
| 48–72 | transizione lineare ICON-2I → IFS |
| 72 h – 15 giorni | **ECMWF IFS** 0,25° – con avviso all'utente: l'incertezza cresce |

**Due modalità**:
- **breve** – passo orario, ultimi 90 giorni di consumi, orizzonte fino a 15 giorni.
  Covariate predefinite: temperatura, radiazione, umidità + festivi, sabato, ponti, ora e stagione.
- **lungo** – passo giornaliero, ultimi 3 anni, orizzonte fino a 1 anno. Covariate: temperatura media,
  gradi giorno di riscaldamento (base 20 °C) e raffrescamento (base 24 °C), radiazione + calendario.
  Oltre i 15 giorni si usa la **climatologia** (media degli stessi giorni negli anni precedenti):
  il risultato è uno scenario "anno tipo", e l'utente viene avvisato.

**Verifica**: con l'opzione `verifica` l'API nasconde l'ultimo tratto dei dati, lo prevede usando il
meteo osservato e restituisce errore medio, WAPE e copertura dell'intervallo 10–90 %.

Prove con consumi sintetici di un edificio a Bologna (CPU, 2 core):

| | WAPE | copertura 80 % | tempo |
|---|---|---|---|
| breve, 120 ore | 14 % | 58 % | ~5 s |
| lungo, 60 giorni | 6 % | 87 % | ~5 s |

Il primo avvio scarica i pesi di TiRex-2 da Hugging Face (in `dati/hf`).

**Privacy** (vedi `fase5-sito/sito/privacy.html`):
- i file caricati sono elaborati in memoria e non vengono salvati né registrati;
- l'API non scrive registri di accesso (`--no-access-log`);
- gli IP stanno solo nel registro di Caddy, `/data/log/accessi.log` nel volume `caddy-dati`, a rotazione e cancellato dopo 14 giorni (`roll_keep_for 336h`);
- il worker, una volta al mese insieme all'indirizzario ANNCSU, cancella dalla cache Zornade le risposte più vecchie di 12 mesi.

**Limiti d'uso per IP**:
- 20 previsioni all'ora;
- 120 ricerche Zornade all'ora;
- 2.000 edifici all'ora per il patrimonio, contati in edifici e non in richieste.
- 60 report scaricabili (docx, pdf, xlsx) all'ora.

Il sito invia i file del patrimonio a blocchi di 40 righe, perché il tunnel Cloudflare chiude le richieste che durano più di 100 secondi.

## Installazione

Prerequisiti: fase 1 completata (Docker installato), pacchetto dati della fase 3 copiato in
`/srv/energia/dati`, sito della fase 5 in `/srv/energia/sito`.

### 1. Dominio: statocritico.it su Cloudflare, sottodomini eugenio e notizie

Il dominio è su Aruba e il piano di Stato Critico prevede già di affidarne il DNS a Cloudflare:
questo è il momento di farlo.

1. **Cloudflare** → *Add a domain* → `statocritico.it` → piano **Free**. Cloudflare importa i record
   esistenti e indica due nameserver (`xxx.ns.cloudflare.com`).
2. **Aruba** → pannello del dominio → *Gestione DNS / Nameserver* → sostituisci i nameserver di Aruba
   con i due di Cloudflare. La propagazione richiede da qualche minuto a 24 ore; Cloudflare manda
   un'email quando il dominio è attivo. (Se su Aruba ci sono caselle email del dominio, verifica che
   i record MX siano stati importati.)
3. **Cloudflare** → *Zero Trust* (gratuito fino a 50 utenti) → *Networks → Tunnels → Create a tunnel* →
   tipo **Cloudflared** → nome `eugenio` → copia il **token** (la lunga stringa dopo `--token`) nel `.env`
   come `CLOUDFLARE_TUNNEL_TOKEN`.
4. Nello stesso tunnel → *Public Hostname*, due voci (Cloudflare crea da solo i record DNS):
   - `eugenio` . `statocritico.it` → servizio **HTTP** `caddy:80`;
   - `notizie` . `statocritico.it` → servizio **HTTP** `listmonk:9000`.
5. *SSL/TLS → Edge Certificates* del dominio → **Always Use HTTPS** attivo.

Fatto il 26/10/2026: tunnel `eugenio`, route `eugenio` → `http://caddy:80` e `notizie` → `http://listmonk:9000`,
Access (applicazione `notizie`, destinazione `notizie.statocritico.it/admin`, policy riutilizzabile "solo Paolo"
con One-time PIN). Email Routing: `privacy@statocritico.it` → Gmail di Paolo, catch-all disattivato.
Il token del tunnel si mette nel `.env` senza mostrarlo: copiare tutto il comando `docker run` dalla pagina del
tunnel (pulsante di copia), poi sul server, in `fase4-server`:
```bash
read -rs -p "Incolla il comando e premi Invio: " CMD; echo
T="${CMD##*--token }"; sed -i "s|^CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=$T|" .env; unset CMD T
docker compose up -d --no-deps cloudflared
```
Attenzione: l'ID del tunnel (36 caratteri) non è il token (oltre 150 caratteri, inizia con `eyJ`). Le password di
listmonk si generano sul server: `sed -i "s|^LISTMONK_DB_PASSWORD=.*|LISTMONK_DB_PASSWORD=$(openssl rand -hex 24)|" .env`
(idem per `LISTMONK_ADMIN_PASSWORD`). Il worker resta spento finché non c'è il pacchetto meteo della fase 3:
`docker compose up -d api caddy postgres listmonk`.

Vantaggi rispetto a un record `A` verso il server: nessuna porta aperta su Oracle (anche 80 e 443
possono restare chiuse, vedi fase 1), IP del server nascosto, protezione DDoS e certificati gestiti
da Cloudflare. Quando nascerà il sito Astro su Cloudflare Pages, starà sullo stesso account e dominio.

6. *Zero Trust → Access → Applications → Add → Self-hosted*: proteggi `notizie.statocritico.it/admin`
   con un accesso tramite codice via email riservato al tuo indirizzo. Il pannello di listmonk resta
   così invisibile al pubblico; iscrizione, conferma e cancellazione restano aperte. (Le API di
   listmonk richiedono comunque il token; il worker le chiama dall'interno, senza passare da Cloudflare.)

### 2. Chiave Zornade

Registrati su <https://app.zornade.com/api> e crea una chiave gratuita (10.000 richieste/ora).
Va **solo** nel file `.env` del server.

### 3. Avvio

Permessi: i container `api` e `worker` girano come utente 1000, mentre sulle immagini Ubuntu di Oracle `ubuntu` è
l'utente 1001. Senza questo comando il worker non può scrivere in `/srv/energia/dati` (PermissionError):
```bash
sudo apt-get install -y acl
sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX /srv/energia/dati
```
La pagina del patrimonio richiede anche `comuni.parquet` nella cartella dati (viene dal pacchetto della fase 3; si può
copiare prima dall'archivio meteo del PC insieme a `comuni.json`).

Prima, i file di configurazione delle fasi 6 e 7 nella cartella dati:
```bash
mkdir -p /srv/energia/dati/mercati/convenzioni
cp ~/energia/fase6-mercati/config.example.toml /srv/energia/dati/mercati/config.toml
cp ~/energia/fase6-mercati/convenzioni/*.toml /srv/energia/dati/mercati/convenzioni/      # convenzioni compilate
cp -r ~/energia/fase6-mercati/convenzioni/fonti /srv/energia/dati/mercati/convenzioni/     # pagine sorvegliate
sed -i 's|^cartella = "archivio_mercati"|cartella = "/dati/mercati"|; s|^cartella = "convenzioni"|cartella = "/dati/mercati/convenzioni"|' /srv/energia/dati/mercati/config.toml
```

```bash
cd ~/energia/fase4-server
cp .env.example .env
nano .env                 # CLOUDFLARE_TUNNEL_TOKEN, ZORNADE_API_KEY, GME_*, SMTP_*, REGIONI
chmod 600 .env
docker compose up -d --build      # la prima build richiede ~10 minuti
docker compose logs -f worker     # prime previsioni meteo (qualche minuto), poi l'indirizzario ANNCSU
```

Al primo avvio il worker scarica anche l'indirizzario ANNCSU in `/srv/energia/dati/anncsu/`
(~270 MB da scaricare, ~0,3 GB su disco, pochi minuti); per rifarlo a mano:
`docker compose exec worker python -m servizio.worker anncsu`.

Controllo: `https://eugenio.statocritico.it/api/salute` e la documentazione interattiva
`https://eugenio.statocritico.it/api/docs`.

### 4. Aggiornare

```bash
cd ~/energia && git pull
cd fase4-server && docker compose up -d --build
```

## API

| Metodo | Percorso | Descrizione |
|---|---|---|
| GET | `/api/salute` | stato e ultimo aggiornamento delle previsioni |
| GET | `/api/comuni` | comuni disponibili (ISTAT, catastale, coordinate, posizione sulla mappa) |
| GET | `/api/meteo/{istat}?modalita=breve\|lungo&giorni=N` | meteo storico e previsto del comune |
| POST | `/api/previsione` | multipart: `file` (CSV), `istat`, `modalita`, `orizzonte` (ore o giorni), `tipo` (`energia` = somma, `potenza` = media), `covariate` (es. `temperatura,radiazione`; vuoto = solo calendario), `verifica` |
| GET | `/api/geocodifica?q=indirizzo` | ricerca indirizzi (Zornade) |
| GET | `/api/particella?lat=&lon=` | particella catastale e comune nel punto (Zornade) |
| GET | `/api/metodologia` | metriche della correzione ERA5 per la pagina del sito |
| GET | `/api/clima-legge10/{istat}?anni=10` | dati climatici aggiornati per la Legge 10 dal clima reale del comune |
| POST | `/api/patrimonio` | CSV di edifici → particella catastale, comune, punto (max 500 righe per richiesta, 2.000 edifici l'ora per IP; il sito manda blocchi di 40); indirizzi prima con ANNCSU, poi con Zornade; CSV in UTF-8 o nella codifica di Windows; la risposta porta `fonti` da citare |
| POST | `/api/report?formato=docx\|pdf\|xlsx` | documento generico in JSON (schema in `/api/report/schema`) → file Word, PDF o Excel; vedi "Report" |
| POST | `/api/report/{tipo}?formato=docx\|pdf\|xlsx` | `tipo` = `previsione`, `legge10`, `patrimonio`: il corpo è la risposta già ricevuta dal servizio → file del report |
| GET | `/api/report/schema` | schema JSON del documento accettato da `/api/report` |
| GET | `/api/storici/catalogo` | dataset scaricabili presenti sul server (grandezze, frequenze, periodo, fonte, licenza, limiti) |
| POST | `/api/storici/stima?formato=csv\|xlsx` | JSON con i filtri → righe, colonne e dimensione stimate; se la richiesta è troppo grande, motivo e suggerimenti |
| POST | `/api/storici/estrai?formato=csv\|xlsx` | stesso JSON → file CSV (in streaming) o Excel con foglio "Info" |

## Dati storici scaricabili (pagina "Dati storici")

Modulo `servizio/storici.py` (router FastAPI incluso in `app.py`). Dataset, mostrati solo se i file ci sono:

| Dataset | File letti | Frequenze |
|---|---|---|
| meteo orario ICON storico (dal 14/11/2022) | `orario/<istat>.parquet`, solo i comuni scelti | oraria, giornaliera, mensile, annuale, stagione |
| meteo giornaliero ERA5 corretto (dal 2015) | `giornaliero.parquet`, filtri per comune e data | giornaliera, mensile, annuale, stagione |
| gradi giorno (GG20, GC24) | `giornaliero.parquet` | giornaliera, mensile, annuale, stagione |
| dati climatici per la Legge 10 (mensili UNI 10349, riepilogo, GG per stagione) | `giornaliero.parquet` + `meteo_storico.legge10` | ultime N stagioni |
| elenco dei comuni con il punto meteo | `comuni.parquet` | – |
| gradi giorno, zona e altitudine del DPR 412/93 (Allegato A, valori di legge) | `dpr412.json` (copia di `fase5-sito/sito/dati/dpr412.json`, generato da `fase5-sito/costruisci_dpr412.py`) | – |
| prezzi Eurostat per le PMI | `mercati/eurostat/*.parquet` | semestrale |

Aggregazioni per giorno civile italiano: medie per temperatura, umidità, vento e nuvolosità; somme per radiazione
(kWh/m²), pioggia, neve e gradi giorno; minimo e massimo per t_min e t_max. Il periodo si allarga a mesi, anni o
stagioni (1 luglio – 30 giugno) interi; un periodo con meno della copertura scelta (predefinita 90%) resta vuoto e
il file riporta `dati_validi` e `dati_attesi`. Area: regione, provincia, elenco di comuni, tutti; facoltativo solo
capoluoghi. CSV con `;`, decimali con la virgola, UTF-8 con BOM, unità nelle intestazioni e fonti in righe `#` in
fondo; Excel con fogli "Dati" e "Info" (filtri, fonti, licenze, data di estrazione, significato delle colonne).
In entrambi ci sono anche le voci "Licenza EuGEnio" (elaborazioni e raccolte di EuGEnio con licenza CC BY 4.0:
riuso libero, anche con modifiche, citando EuGEnio come fonte e mantenendo le fonti originali) e "Come citare"
(«Fonte: EuGEnio – eugenio.statocritico.it (dati estratti il gg/mm/aaaa)»); i testi sono `RIUSO` in `storici.py` e
`CITAZIONE` in `report.py`.

**Mai scaricabili** (le rotte rispondono 403 a qualunque richiesta che li nomini): prezzi GME (PUN, zonali, PSV,
IGI), EEX/TTF e future, PFOR, PSV ARERA, dati Zornade, indirizzario ANNCSU. Nessun dato degli utenti viene salvato.

Limiti (variabili d'ambiente): `STORICI_MAX_RIGHE_CSV` 500.000, `STORICI_MAX_RIGHE_XLSX` 300.000,
`STORICI_MAX_CELLE_XLSX` 3.000.000 (~40 s di scrittura), `STORICI_MAX_COMUNI` 2.000 comuni elencati,
`STORICI_MAX_COMUNI_LEGGE10` 400, `STORICI_COPERTURA` 90, `STORICI_ESTRAZIONI_ORA` 30 e `STORICI_STIME_ORA` 600 per
IP, `STORICI_PARALLELE` 2 estrazioni contemporanee. Tempi misurati: CSV da 500.000 righe ~8–10 s, Excel da 300.000
righe × 13 colonne ~40 s. Prove: `python -m pytest tests/test_storici.py`.

I dati di mercato (GME, TTF, PFOR) non hanno rotte pubbliche: si usano solo dentro simulazioni e
analisi (fase 6), non si possono scaricare dal sito.

Formato CSV: due colonne, data/ora e valore; separatore `;` `,` o tab; decimali con virgola o punto;
date `GG/MM/AAAA hh:mm` o `AAAA-MM-GG hh:mm`, in ora italiana.

Limiti per indirizzo IP: 20 previsioni/ora, 120 ricerche/ora, 60 report/ora, 30 download di dati storici/ora. File fino a 5 MB / 200.000 righe.

## Report

Il servizio genera report scaricabili in **Word (.docx)**, **PDF** e **Excel (.xlsx)**; il CSV lo produce
già il sito da sé. Il codice è in `servizio/report.py` (modello del documento e tre generatori) e
`servizio/report_servizi.py` (report dei servizi esistenti). Le usano i pulsanti "Scarica il report" di previsione, patrimonio, Legge 10 e indicatori (`sito/report.js`).

**Modello del documento** (indipendente dal formato): `titolo`, `sottotitolo`, `data` (vuota = oggi),
`nome_file` (facoltativo, senza estensione), `sezioni` con `titolo` e `blocchi`, `fonti` (`testo`, `url`).
Blocchi (campo `tipo`):

| tipo | campi |
|---|---|
| `paragrafo` | `testo` |
| `elenco` | `voci`, `numerato` |
| `tabella` | `titolo`, `intestazioni`, `righe` (celle: numero, testo, sì/no, vuoto), `decimali` per colonna, `nota` |
| `chiave_valore` | `titolo`, `voci` (`chiave`, `valore`, `unita`, `decimali`) |
| `immagine` | `formato` `png` o `svg`, `dati` in base64, `didascalia`, `larghezza_cm` |
| `avvertenza` | `testo`, `livello` (`attenzione` o `info`) |

Ogni file porta l'**intestazione** "Prodotto da EuGEnio – eugenio.statocritico.it" (in Word e PDF nell'intestazione
di ogni pagina, con il collegamento al sito; in Excel nella prima riga del foglio Info e nell'intestazione di stampa di
ogni foglio) e chiude con le **fonti e attribuzioni** e le **avvertenze** complete (una volta, in fondo; in Excel nel
foglio Info). Il **piè di pagina** di ogni pagina (Word e PDF) e di stampa di ogni foglio (Excel) riporta, in carattere
piccolo, un'avvertenza breve coerente con la FAQ "I dati sono garantiti?" (`faq.html#garanzia`): servizio gratuito e
senza garanzia, dati calcolati o reperiti con sistemi automatici e verificati a campione, nessuna responsabilità per
errori nei dati, nelle previsioni o nell'uso del report; sviluppato anche con l'intelligenza artificiale, calcoli
deterministici; la licenza dei dati e dei report (CC BY 4.0, riuso citando «Fonte: EuGEnio –
eugenio.statocritico.it»); dove segnalare gli errori (`contatti.html`); più il numero di pagina ("Pagina 2 di 5").
Le avvertenze complete in fondo al report comprendono il testo della licenza (`TESTO_LICENZA`): CC BY 4.0 per il
report e i dati elaborati, obbligo di citare EuGEnio come fonte con la data del report, attribuzioni delle fonti
originali da mantenere, dati di origine soggetti alle loro licenze (Zornade: link e niente ridistribuzione in
blocco), testi normativi come atti pubblici, codice AGPL-3.0, rimando a `licenza.html#dati`. I testi sono
costanti in `report.py` (`INTESTAZIONE`, `CITAZIONE`, `LICENZA_DATI`, `PIE_AVVERTENZA`, `PIE_AVVERTENZA_XLSX` – più
corta perché in Excel intestazione e piè di stampa, codici di formato compresi, non superano 255 caratteri –,
`TESTO_LICENZA`, `AVVERTENZE`). **Logo**: per ora nessuno; per aggiungerlo basta assegnare i byte di un PNG a
`LOGO_PNG` (altezza `LOGO_ALTEZZA_CM`): va a sinistra nell'intestazione di Word e PDF e in cima al foglio Info.

- **Formati italiani**: in Word e PDF 1.234,56 e 27/10/2026; le stringhe ISO di data o data/ora nelle tabelle sono
  riconosciute (quelle con fuso riportate all'ora italiana). In Excel i numeri restano numeri, con formato di
  cella, e le date diventano date; c'è un foglio per tabella più il foglio **Info** (titolo, data, testi,
  coppie chiave/valore, avvertenze, fonti). Il testo che inizia con `=` non diventa mai una formula.
- **Immagini**: PNG in Word e PDF; SVG solo nel PDF (in Word resta una nota, in Excel le immagini non entrano).
  SVG con immagini, script o riferimenti esterni sono rifiutati.
- **PDF**: [fpdf2](https://py-pdf.github.io/fpdf2/) (Python puro, nessuna libreria di sistema) con il font
  **DejaVu Sans** del pacchetto Debian `fonts-dejavu-core`, installato nel `Dockerfile` durante la build.
  Senza il font si ripiega su Helvetica e i simboli fuori dal latin-1 diventano testo (`≥` → `>=`, `€` → `EUR`).
  In alternativa al pacchetto: copiare `DejaVuSans.ttf` e `DejaVuSans-Bold.ttf` (licenza libera) in una
  cartella dell'immagine e indicarla con `REPORT_FONT_DIR`. Con tabelle di più di 8 colonne il PDF è orizzontale.
- **Limiti** (variabili d'ambiente in `config.py`): corpo fino a 5 MB (`REPORT_MAX_MB`), 50 sezioni,
  100 blocchi per sezione, 30 colonne, 5.000 righe per tabella e 10.000 in tutto, 20.000 caratteri per testo,
  10 immagini da 1,5 MB. 60 report all'ora per IP, al massimo due generati alla volta
  (5.000 righe: ~5 s in Word o PDF, meno di 1 s in Excel).
- **Privacy**: tutto in memoria, nulla scritto su disco né registrato; risposta con `Cache-Control: no-store`.
- **Errori**: 400 (formato o tipo sconosciuto, JSON non valido), 422 (documento non valido, con il motivo in
  italiano in `detail`), 413 (troppo grande), 429 (limite d'uso).
- **Mai dati di mercato**: i report non contengono prezzi GME/EEX (PUN, PSV, IGI, TTF, PFOR); le funzioni
  dei servizi leggono solo campi noti e scartano comunque le colonne con quei nomi.

**Report dei servizi** (`POST /api/report/{tipo}?formato=…`; il corpo è la risposta JSON già ricevuta):

| tipo | corpo | nome del file |
|---|---|---|
| `previsione` | risposta di `/api/previsione` più `richiesta` facoltativa (`comune`, `modalita`, `orizzonte`, `covariate`, `tipo`, `unita`) | `previsione_037006_breve.pdf` |
| `legge10` | risposta di `/api/clima-legge10/{istat}`, più il campo facoltativo `dpr412` {gg, zona, alt, nome, nota, origini} aggiunto dal sito (sezione "Confronto con il DPR 412/93"; differenza e zona ricalcolate dal server) | `clima_legge10_037006.pdf` |
| `patrimonio` | `{"righe": [...], "fonti": [...]}` con le righe unite di tutti i blocchi | `patrimonio_geolocalizzato.pdf` |
| `indicatori` | valori già calcolati da `sito/indicatori.js` (fase 8): `ente`, `regione`, `italia` {nome, codice, regione_ce, fonte_residenti, anni [{anno, provvisorio, spesa, leva, incidenza, peso, per_giornata, per_posto, per_cittadino, AZ9999, BZ9999, …}]}, `componente`, `anno_confronto`, `avvertenze`, `fonti`, `elaborazione`; il server impagina soltanto | `indicatori_energia_080_114.pdf` |

Attribuzioni sempre incluse: "Weather data by Open-Meteo.com (CC BY 4.0)" e ISTAT (CC BY 4.0) per previsione e
Legge 10, TiRex-2 per la previsione, "Dati elaborati da Zornade" con link a https://zornade.com e "ANNCSU –
Agenzia delle Entrate e ISTAT (CC BY 4.0)" per il patrimonio, OpenBDAP della Ragioneria Generale dello Stato
(CC BY 4.0) per gli indicatori. Il report Legge 10 apre con l'avvertenza che i
dati non sostituiscono i valori normativi (UNI 10349, DPR 412/93).

**Nuovo tipo di report**: in `servizio/report_servizi.py` scrivere `def report_xxx(d: dict, **kw) -> Documento`
che costruisce sezioni e fonti dalla risposta del servizio, aggiungerlo a `TIPI` e una prova in
`tests/test_report.py`; la rotta `POST /api/report/xxx` esiste da sola. In alternativa il sito può comporre il
documento e inviarlo a `POST /api/report`.

Prove: dalla cartella `fase4-server`, `python -m pytest tests` (non servono TiRex-2 né i dati meteo).

**Stile dei report (decisione del 27/10/2026)**: stile professionale e sobrio, adatto alla stampa in bianco e nero.
Testo nero; nessun fondo colorato (né nelle intestazioni delle tabelle né nei riquadri: solo bordi neri sottili);
collegamenti in blu scuro (`COLORE_LINK` = #1A3F8F) sottolineati. Logo Corallo a colori (`servizio/logo_eugenio.png`,
uguale per tutti i vestiti del sito). I grafici, quando verranno aggiunti, usano `SERIE_STAMPA`: sei serie con colore,
tratto e retino propri, adatte a chi confonde rosso e verde e leggibili anche stampate in bianco e nero.

**Intestazione e piè di pagina** (27/10/2026):
- logo: la base del simbolo è allineata alla linea di base della scritta EuGEnio e il tetto sporge un po' sopra la E;
  la E è alta `ALTEZZA_E_MM` = 4 mm; il PNG è tagliato sulla linea di base (`LOGO_MAIUSCOLA`, `LOGO_CIMA_MAIUSCOLA`
  dicono dove sta la E), così in Word poggia sulla stessa riga del titolo;
- PDF orizzontale: su una riga logo a sinistra, titolo al centro (rimpicciolito fino a 7 pt e poi accorciato se
  troppo lungo), "Prodotto da EuGEnio – eugenio.statocritico.it" a destra; la linea è sotto il testo;
- PDF verticale e Word (A4 verticale): logo e titolo; il piè comincia con "Prodotto da EuGEnio –
  eugenio.statocritico.it." e prosegue con l'avvertenza, sulla stessa riga;
- Excel (intestazione di stampa): "EuGEnio" a sinistra e titolo al centro; il piè comincia con "Prodotto da EuGEnio".

## Newsletter automatica dei dati

Separata da Substack, che resta per gli articoli. Gira tutta sul server: [listmonk](https://listmonk.app)
(open source, AGPL-3.0) con PostgreSQL. Una lista **mensile**, con **doppia conferma** e cancellazione
con un clic in ogni email: il 12 del mese arrivano i gradi giorno osservati nel mese appena concluso nei
capoluoghi, rispetto agli anni precedenti, e gli ultimi prezzi Eurostat dell'energia per le PMI.

Le campagne partono da sole (`NOTIZIARIO_INVIO_AUTOMATICO=true`); con `false` restano in bozza e arriva un avviso.
I dati GME e TTF non compaiono. Iscrizione: `https://notizie.statocritico.it/subscription/form`
(collegata dal menu del sito, "Dati per email").

**Invio: OCI Email Delivery** (stesso account Oracle, dati in UE). Limiti dell'account a consumo: **50.000 email ogni
24 ore**, 18.000 al minuto, messaggi fino a 2 MB (ogni destinatario conta come un'email); l'account solo Always Free
non può inviare (limite 0). Il listino separa le prime 3.100 email del mese dalle successive, che costano pochi
centesimi ogni mille. listmonk distribuisce gli invii con una finestra mobile di **3.000 messaggi ogni 24 ore**: una
newsletter fino a 3.000 iscritti parte in un giorno; oltre, alzare la finestra (costo trascurabile).

Configurazione (una volta):
1. Console Oracle → *Developer Services → Email Delivery*:
   - *Email Domains* → `statocritico.it` → **DKIM**: aggiungi su Cloudflare il record CNAME indicato;
   - **SPF**: su Cloudflare esiste già il record TXT di Email Routing
     `v=spf1 include:_spf.mx.cloudflare.net ~all` (26/10/2026). **Non crearne un secondo**: modifica quello e
     aggiungi l'`include:` indicato dalla console Oracle prima di `~all` (due record SPF si annullano a vicenda);
   - *Approved Senders*: `eugenio@statocritico.it`.
2. Profilo utente → *Tokens and keys* → *SMTP credentials* → genera utente e password: nel `.env` (`SMTP_UTENTE`,
   `SMTP_PASSWORD`). Server `smtp.email.eu-milan-1.oci.oraclecloud.com`, porta 587. Se la sezione non c'è:
   *Identity → Domains → Default → Users →* il proprio utente *→ Edit user capabilities → SMTP credentials*.
   Per non mostrare le credenziali, sul server: `read -rs U`, `read -rs P`, poi
   `U="$U" P="$P" python3 -c '...re.sub("^SMTP_UTENTE=.*"...)'` con i valori tra apici singoli, e `unset U P`.
   Prova: `docker compose run --rm --no-deps api python -c "from servizio import avvisi; print(avvisi.invia('prova', 'prova'))"`
   (fatto il 26/10/2026: SPF, DKIM e DMARC in PASS su Gmail).
3. Nel `.env`: `LISTMONK_DB_PASSWORD`, `LISTMONK_ADMIN_PASSWORD` (lunghe), poi `docker compose up -d`.
4. `https://notizie.statocritico.it/admin` → *Impostazioni*:
   - *Generali*: URL radice `https://notizie.statocritico.it`, mittente `EuGEnio <eugenio@statocritico.it>`;
   - *SMTP*: dati del punto 2, **Auth protocol PLAIN** (con LOGIN Oracle risponde "504 authentication mechanism not
     supported"), TLS STARTTLS, HELO vuoto; **eliminare il blocco d'esempio `smtp.yoursite.com`**, altrimenti
     listmonk alterna i due server; *Performance*: **finestra mobile: 3.000 messaggi ogni 24 ore**;
   - *Privacy*: cancellazione con un clic, esportazione dei dati, collegamento all'informativa
     (`https://eugenio.statocritico.it/privacy.html`);
   - *Liste*: cancella le liste, gli iscritti e la campagna d'esempio; crea **EuGEnio mensile**, pubblica, **doppio
     opt-in**; il suo numero va in `LISTA_MENSILE` (l'interfaccia mostra solo l'UUID: il numero si legge con
     `docker compose exec postgres psql -U listmonk -d listmonk -tAc "select id, name from lists"`; oggi è 3);
   - *Utenti*: un utente **API** → `LISTMONK_API_UTENTE` / `LISTMONK_API_TOKEN`.
5. `docker compose up -d` per rileggere il `.env`. Prova: `docker compose exec worker python -m servizio.worker mensile` (con `NOTIZIARIO_INVIO_AUTOMATICO=false` resta in bozza).

Le stesse credenziali SMTP servono agli avvisi all'amministratore (errori notturni, password GME
scaduta, nuovi comuni ISTAT, campagne in bozza, download ANNCSU non riuscito, novità delle convenzioni
trovate dalla sorveglianza notturna).

## Consumo dell'API Open-Meteo gratuita

Emilia-Romagna (330 comuni): previsioni ogni 6 ore ~2.200 chiamate/giorno, storico ~550/giorno:
**~2.800 su 10.000 al giorno**. Il conteggio è in `dati/stato_api.json`. Se si eseguono anche i
download della fase 3 sullo stesso server, conviene sospendere quelli o usare l'istanza locale.
Per tutta Italia serve l'istanza Open-Meteo propria (`--profile open-meteo`).

## Risorse

TiRex-2 su CPU: ~1,2 GB di RAM (misurati) per il processo API. Totale stimato con tutti i servizi:
~3,5 GB su 12. Disco: vedi la tabella "Spazio" nel README principale (~15 GB, ~35 GB con Open-Meteo).
Una previsione alla volta (le altre attendono in coda) per non saturare i 2 core. La conversione mensile
dell'indirizzario ANNCSU usa ~400 MB di memoria per un paio di minuti.

## Licenze e attribuzioni (da mostrare sul sito)

- Codice di EuGEnio: AGPL-3.0. Dati elaborati e report prodotti da EuGEnio: CC BY 4.0, riuso citando
  «Fonte: EuGEnio – eugenio.statocritico.it» (con la data di estrazione) e mantenendo le fonti originali.

- TiRex-2: NX-AI, Apache 2.0.
- Meteo: "Weather data by Open-Meteo.com" (CC BY 4.0) – modelli Arpae ICON-2I, DWD ICON, ECMWF IFS, ERA5 Copernicus.
- "Dati elaborati da Zornade" (link a https://zornade.com) – catasto Agenzia delle Entrate, ISTAT, OpenStreetMap (ODbL).
- Civici: ANNCSU – Agenzia delle Entrate e ISTAT (CC BY 4.0).
- Confini comunali: ISTAT (CC BY 4.0) via Gramscii.
- Report: python-docx (MIT), fpdf2 (LGPL-3.0), openpyxl (MIT), font DejaVu Sans (licenza libera Bitstream Vera/DejaVu).
