# Proposte «upstream» della fase 11 (EuGEnio Visure)

Stato al 04/11/2026: **bozze, nessuna inviata**. Correzioni e contributi che EuGEnio potrebbe proporre ai progetti e alle
fonti usate, nati dal lavoro sulla Fase D. Le invia Paolo, quando e se lo ritiene utile; dopo l'invio annotare qui data e
risposta.

| # | Destinatario | Tipo | Priorità | Stato |
|---|---|---|---|---|
| 1 | Zornade – `visura-api` | tre contributi del § 13 e due nuovi | media | bozza |
| 2 | Agenzia delle Entrate | richiesta di chiarimento sulle condizioni d'uso (automazione, riuso dei dati letti) | **alta**, prima di attivare `visura-api` | bozza |
| 3 | Agenzia delle Entrate | proposta di dati aperti e di visure leggibili dalle macchine | bassa | bozza |
| 4 | pypdf | nessuna correzione necessaria per ora; segnalazione solo se le visure vere mostrano problemi | — | da rivalutare |
| 5 | PyInstaller, SignPath Foundation | nessun contributo; adesione a SignPath per la firma (non è un contributo) | — | da fare con la prima release |

---

## 1. Zornade – `visura-api` (issue o email a hello@zornade.com)

Si può unire alla risposta a Zornade del § 14.2 della proposta (punto «Da valutare se aggiungere»).

> **Oggetto:** visura-api – tre proposte di contributo da EuGEnio
>
> Ciao [nome],
>
> stiamo preparando EuGEnio Visure, un programma open source (AGPL-3.0) che legge sul PC dell'utente le visure
> catastali in PDF e le abbina agli edifici di un patrimonio (piani, superfici, categorie per le analisi energetiche).
> Per ora lavora solo sui PDF che l'utente ha già: non usiamo visura-api finché non abbiamo chiarito con l'Agenzia le
> condizioni d'uso dell'area riservata e di SISTER. Se in futuro lo useremo, sarà senza fork, tramite la sua interfaccia
> REST, e ci farebbe piacere contribuire con:
>
> 1. **login manuale in una finestra visibile** del browser, così le credenziali non passano mai dal programma
>    (l'utente entra con SPID o CIE e il programma prosegue nella stessa sessione);
> 2. **salvataggio del PDF** di ogni visura accanto ai dati restituiti, con un nome prevedibile
>    (`<Belfiore>/F<foglio>_P<particella>/sub_<n>.pdf`);
> 3. **lettura di piano, superficie catastale e consistenza in m³** (categorie B): abbiamo un lettore con regole in un file
>    TOML, provato su visure sintetiche, che possiamo adattare al vostro formato
>    (github.com/statocritico/eugenio, cartella `fase11-visure`);
> 4. *(nuovo)* **release con tag e impronte SHA-256** pubblicate: il nostro avviatore usa solo versioni approvate
>    elencate con l'impronta, e un tag stabile per release lo semplificherebbe;
> 5. *(nuovo)* un'**opzione per non scrivere dati personali nei registri** (intestatari e codici fiscali), visto che il
>    vostro README avverte che i log li contengono.
>
> Prima di scrivere codice aspettiamo di sapere se le proposte vi interessano e come preferite riceverle.
>
> Grazie, Paolo – EuGEnio, un servizio di Stato Critico

## 2. Agenzia delle Entrate – richiesta di chiarimento (prima di attivare lo scaricamento automatico)

Canale: area riservata → assistenza, oppure PEC della Direzione Centrale Servizi Catastali, Cartografici e di Pubblicità
Immobiliare (indirizzo da verificare sul sito dell'Agenzia). È il passo che manca per decidere se `visura-api` si attiva
(vedi README, «Condizioni d'uso»).

> **Oggetto:** Consultazione telematica delle banche dati catastali – richiesta di chiarimenti su strumenti di supporto
> all'utente e uso dei dati per la gestione energetica di un patrimonio pubblico
>
> Gentili,
>
> sono Paolo Bianco e curo EuGEnio (eugenio.statocritico.it), un servizio gratuito e open source per l'analisi
> energetica degli edifici, usato anche per il patrimonio di enti pubblici. Vi chiedo alcuni chiarimenti sul
> provvedimento prot. 460187 del 30/12/2024 e sulle condizioni generali dei servizi di consultazione.
>
> 1. **Lettura delle visure già ottenute.** Un programma che gira sul computer dell'utente legge le visure in PDF che
>    l'utente ha ottenuto dai vostri servizi e ne estrae categoria, consistenza, superficie e piano, per stimare le
>    superfici degli edifici. Non accede ai vostri servizi e non conserva né trasmette intestatari e codici fiscali.
>    Confermate che questo uso, interno all'utente o all'ente che ha consultato i dati, è compatibile con le condizioni
>    generali e con l'art. 1, commi 367–373, della L. 311/2004?
> 2. **Strumenti di supporto alla consultazione.** È ammesso che un utente autenticato (SPID o CIE, oppure un incaricato
>    dell'ente) usi un programma sul proprio computer per richiedere in sequenza le visure dei propri immobili, con un
>    ritmo lento (una richiesta ogni pochi secondi) e un tetto giornaliero? Esistono limiti quantitativi pubblicati che
>    non vanno superati (punto 11.6 del provvedimento)?
> 3. **Enti pubblici.** Per un ente che vuole tenere aggiornati i dati catastali del proprio patrimonio, la via indicata
>    è la PDND o il servizio SMIDT (punti 6.1 e 6.6)? Esiste un e-service PDND con i dati di classamento e superficie per
>    gli immobili dell'ente?
> 4. **Dati derivati.** Indicatori aggregati per edificio ricavati dalle visure (ad esempio «superficie catastale totale» o
>    «categoria prevalente»), senza dati personali, possono essere mostrati in report interni dell'ente o pubblicati?
>
> Ringrazio per l'attenzione. Cordiali saluti,
> Paolo Bianco – EuGEnio, un servizio di Stato Critico

## 3. Agenzia delle Entrate – proposte di dati aperti (facoltativa, dopo la 2)

- **Visure leggibili dalle macchine:** accanto al PDF, la stessa visura in un formato strutturato (XML o JSON) per il
  titolare che la richiede; in alternativa PDF accessibili (PDF/UA, testo marcato), che aiutano anche chi usa lettori di
  schermo.
- **Condizioni generali in una pagina pubblica e stabile:** oggi si leggono al momento dell'accettazione nell'area
  riservata; un indirizzo pubblico, con data di versione, aiuterebbe chi sviluppa strumenti a rispettarle.
- **Dati aperti aggregati per particella** (numero di unità, categoria prevalente, superficie catastale totale), senza
  dati personali e in CC BY 4.0 come la cartografia catastale e l'ANNCSU: servirebbero alle analisi energetiche e
  urbanistiche senza scaricare visure una per una.

## 4. pypdf

La modalità `extraction_mode="layout"` (pypdf 6.17.0) ricostruisce bene le colonne delle tabelle delle visure sintetiche:
nessun difetto trovato. Se le visure vere anonimizzate mostrano problemi (colonne spostate, caratteri persi, pagine
ruotate), aprire una issue su github.com/py-pdf/pypdf con un **PDF minimo senza dati personali** che riproduce il caso
(mai una visura vera, anche se anonimizzata, senza averla controllata con `python -m visure controlla`).

## 5. Firma del codice

Non è un contributo ma un'adesione: domanda a **SignPath Foundation** (signpath.org) per il progetto
`statocritico/eugenio`, con il workflow `.github/workflows/visure-windows.yml` già predisposto (README, «Firma»).
