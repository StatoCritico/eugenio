# Pubblicazione del 04/11/2026: procedura unica

## Aggiornamento menu (?v=20261104c)

Dopo questa procedura è cambiato il **menu dei servizi** (sezione «Menu fissabile e voci GME non cliccabili» di
`AGGIORNAMENTO_2026-11-04.md`): mouse sopra un gruppo → tendina; clic sul titolo → riga nera fissata sotto la barra;
secondo clic → la riga sparisce; voci «licenza GME» non cliccabili. Il sito passa da `?v=20261104b` a **`?v=20261104c`**.
Cambiano **solo file statici del sito** (`fase5-sito`) e i documenti: **nessun rebuild** dell'api e nessun riavvio di
Caddy, che legge `fase5-sito/sito` montato in sola lettura (`docker-compose.yml`: `…/fase5-sito/sito:/srv/sito:ro`).

Prima di tutto capisci in quale caso sei. **[PC]** nel clone:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git log --oneline -5
```
- Se tra le righe **non** c'è il commit «Pubblicazione del 03-04/11/2026: …», la procedura completa non è ancora fatta:
  **caso A**.
- Se c'è (e hai già fatto le Parti 5 e 6, cioè il sito sul server è `?v=20261104b`): **caso B**.
- Se c'è il commit ma ti sei fermato prima della Parte 5: estrai lo zip nuovo (passo 3), rifai i passi 4, 9, 10 (con il
  messaggio di M8 qui sotto) e 11, poi continua la procedura completa dalla Parte 3 dove ti eri fermato.

In dubbio, guarda il server (`ssh eugenio`): `grep -c 20261104b /srv/energia/sito/index.html`. Un numero maggiore di 0
vuol dire che il sito della procedura completa è già online (caso B); `0` vuol dire che online c'è ancora una versione
più vecchia (caso A).

### Caso A – la procedura completa non è ancora fatta

Esegui **tutta** la procedura qui sotto, dalla Parte 1, con lo zip nuovo `eugenio_2026-11-04.zip` (quello con questa
sezione). La procedura dice già ovunque **`20261104c`** al posto di `20261104b`: nei controlli, nel `grep` del passo 27
e nel messaggio di commit. Il passo 4 ora si aspetta **`19 passed`** e il passo 38 prova anche il menu nuovo. Non serve
nient'altro di questa sezione.

### Caso B – la procedura completa è già fatta: solo il menu

**M1. [PC]** Entra nel clone e controlla che non ci siano modifiche non salvate:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git status
```
Deve dire `nothing to commit, working tree clean`. Se elenca dei file, fermati: lo zip li sovrascrive.

**M2. [PC]** Estrai lo zip nuovo nel clone (come al passo 3). `.git`, `.env`, `fase2-gradi-giorno` e `iscrizioni` non
sono nello zip e restano come sono:
```powershell
dir ..\eugenio_2026-11-04.zip
Expand-Archive -Path ..\eugenio_2026-11-04.zip -DestinationPath . -Force
git status --short
```
Cosa aspettarsi:
- lo zip ha la data di oggi e un'ora successiva a quella dello zip usato per la procedura completa;
- `git status --short` elenca **solo** file sotto `fase5-sito/` e i documenti in cima (`RIEPILOGO.md`, `DA_FARE.md`,
  `AGGIORNAMENTO_2026-11-04.md`, `PUBBLICAZIONE_2026-11-04.md`). In `fase5-sito/` cambiano:
  - `costruisci_pagine.py`, `README.md`, `parti/testa.html`, `parti/testata.html`;
  - `sito/aspetto.js`, `sito/stile.css`, `sito/README_stile.md`;
  - tutte le pagine `sito/*.html` (testata e versione), `sito/interno/edifici.html`;
  - `sito/cti_legge10.js`, `sito/edificio3d.js`, `sito/legge10.js`, `sito/ombre_worker.js` (solo il numero di versione);
  - `tests/test_costruisci_pagine.py` e, nuovo (`??`), `tests/test_menu_browser.py`.

Se compaiono file di altre fasi (per esempio `fase4-server/…`), fermati e dimmelo: vuol dire che il clone non era
allineato all'ultima pubblicazione.

**M3. [PC]** Controlli (il primo non scrive nulla):
```powershell
cd fase5-sito
python costruisci_pagine.py --controlla
python -m pytest -q tests
cd ..
```
Cosa aspettarsi: `versione 20261104c: 0 file da rigenerare` e `19 passed` (oppure `17 passed, 2 skipped` se sul PC
manca Playwright).

**M4. [PC]** Pacchetto del **solo sito**, lo stesso comando del passo 21:
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
dir ..\sito.tar.gz
```
Il file ha l'ora di adesso e pesa circa 5 MB. Il pacchetto del codice (`codice.tar.gz`) **non** serve.

**M5. [PC]** Copia sul server:
```powershell
scp ..\sito.tar.gz eugenio:~/
```
Compare una riga con `100%`.

**M6. [Server]** Entra con `ssh eugenio` e pubblica il sito, come al passo 27:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261104c /srv/energia/sito/index.html /srv/energia/sito/cog-car.html /srv/energia/sito/interno/edifici.html
grep -c "riga-fissata" /srv/energia/sito/index.html /srv/energia/sito/stile.css
grep -c 'href="cog-car.html"' /srv/energia/sito/index.html
```
Cosa aspettarsi:
- tre righe `…:N`, tutte con N maggiore di 0;
- due righe con N maggiore di 0 (la riga fissata c'è nella pagina e nel foglio di stile);
- `0`: la home non ha più collegamenti alla pagina CAR.

**Non** serve `docker compose up --build`, né riavviare Caddy o l'api: Caddy serve subito i file nuovi. Puoi cancellare
il pacchetto con `rm ~/sito.tar.gz`.

**M7. [Browser]** Apri `https://eugenio.statocritico.it/lidar.html` e premi **Ctrl+F5**. Poi:
1. Mouse sopra **Edificio**, senza cliccare: si apre la tendina verticale. Sposta il mouse in basso: si chiude.
2. Fermo con il mouse sul titolo **Patrimonio**: compare «Clicca qui per fissare il menu Patrimonio sotto la barra».
3. Clic su **Patrimonio**: sotto la barra compare la riga **nera** con le 6 voci in orizzontale, **LiDAR** sottolineata;
   il titolo Patrimonio diventa una linguetta nera. Mouse sopra Patrimonio: la tendina non si apre.
4. Clic su **Edificio**: la riga passa alle 8 voci di Edificio (su due righe).
5. Clic su una voce della riga, per esempio **Obblighi di legge**: nella pagina nuova la riga c'è ancora.
6. Clic di nuovo su **Edificio**: la riga sparisce; con il mouse ancora sopra si riapre la tendina.
7. Mouse sopra **Cogenerazione**: cinque voci grigie con «licenza GME» tratteggiata; fermo su una compare «In attesa di
   autorizzazione dal GME»; il clic non apre nulla. Lo stesso per **Fotovoltaico › Prezzo catturato, accumuli e mercato**.
8. Prova un altro vestito con ✱ e il tema con ◐, con un gruppo fissato: la riga resta nera.
9. F12 → Console: nessuna riga rossa.
10. Dal telefono: **Menu** funziona come prima; se un gruppo era stato fissato dal computer non lo vedi (la memoria è del
    singolo browser). Sul telefono, in Cogenerazione, un tocco su una voce «licenza GME» mostra la nota e non apre nulla.

Se il menu sembra quello vecchio, il browser usa ancora la copia di prima: Ctrl+F5 di nuovo, oppure in Cloudflare
**Caching → Configuration → Purge Everything**.

**M8. [PC]** Commit e push, nel clone:
```powershell
git add -A
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni"
git commit -m "Menu dei servizi: tendina al passaggio del mouse, clic che fissa il gruppo in una riga nera sotto la barra, voci in attesa della licenza GME non cliccabili; sito ?v=20261104c"
git push
```
Cosa aspettarsi: il secondo comando non stampa **nulla**; l'ultima riga del push è del tipo `abc1234..def5678  main ->
main`. Se il push viene rifiutato, `git pull --rebase` e di nuovo `git push`.

---


Questa procedura pubblica in una volta sola **tutto quello che è in codice dal 03/11 al 04/11/2026 e non è ancora
online**:
- `AGGIORNAMENTO_2026-11-03.md`: menu a cinque gruppi, pagine segnaposto, Fase A degli edifici 3D;
- `AGGIORNAMENTO_2026-11-04.md`: Previsioni (schede, «Solo clima», comune deselezionabile), Fasi B, C, D ed E, Importa
  DXF/IFC.

Per la pubblicazione **sostituisce** i passi di quei due file, che restano come descrizione di cosa è cambiato. Il sito si
pubblica in una sola versione, **`?v=20261104c`**: comprende anche tutto quello che quei file chiamano `20261103a` e
`20261104a`.

Comprende tre attività: commit e push dal PC, pubblicazione su server, Cloudflare e browser, costruzione e controllo di
`EuGEnioVisure.exe`. Il modulo UNI privato e le prove con DXF/IFC veri sono rinviati (sezione «Rinviato», in fondo).

Dove si esegue ogni passo:

| Etichetta | Dove |
|---|---|
| **[PC]** | PowerShell sul PC, nella cartella indicata |
| **[Server]** | terminale del server, dopo `ssh eugenio` (il prompt è `ubuntu@eugenio:~$`) |
| **[Cloudflare]** | dashboard di Cloudflare nel browser |
| **[GitHub]** | github.com/statocritico/eugenio nel browser |
| **[Browser]** | il sito, `https://eugenio.statocritico.it` (premi Ctrl+F5 sulla prima pagina che apri) |

Un'azione per passo. Nessun valore segreto va scritto in questo file, nei documenti o nei messaggi: token, AUD ed email
vanno solo nel `.env` del server.

## Ordine e perché

1. **Parte 1, PC**: estrai lo zip nel clone e fai i controlli (pagine, test, file da tenere fuori da git). Prepara anche
   i file di prova sintetici che servono più avanti.
2. **Parte 2, commit e push**. Si fa prima della pubblicazione per due motivi:
   - il pulsante **Run workflow** di `visure-windows` compare in GitHub solo quando il file del workflow è sul ramo
     principale, e oggi non c'è;
   - il push **non avvia** il workflow: il workflow parte con un tag `visure-v…`, con una pull request o a mano.
   
   Il push non tocca il sito: online non cambia nulla finché non fai la Parte 5.
3. **Parte 3, GitHub Actions**: avvia la costruzione dell'.exe. Dura 5–10 minuti e intanto vai avanti.
4. **Parte 4, Cloudflare**: la regola di rate limiting e Cloudflare Access. Va fatta prima del server, perché l'AUD di
   Access serve per il `.env`.
5. **Parte 5, PC → server**: i due pacchetti, quello del codice e quello del sito, e la copia sul server.
6. **Parte 6, server**: `.env`, cartelle, codice, sito, rebuild, controlli e cron.
7. **Parte 7, browser**: prove delle pagine.
8. **Parte 8, .exe**: scaricamento dell'artefatto (o costruzione in locale) e controlli.

---

## Parte 1 – PC: zip nel clone e controlli

**1. [PC]** Apri PowerShell ed entra nel clone:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git status
git branch --show-current
```
Cosa aspettarsi:
- `git status` non deve mostrare modifiche tue non ancora salvate in un commit. Se ce ne sono e ti servono, fermati: lo
  zip le sovrascrive.
- Il secondo comando stampa il nome del ramo, di solito `main`. Annotalo.

**2. [PC]** Controlla lo zip e guarda quali file `.env` hai sul PC. Lo zip non contiene nessun `.env`, quindi non li
tocca, ma è meglio saperlo:
```powershell
dir ..\eugenio_2026-11-04.zip
Get-ChildItem -Recurse -Force -Filter .env | Select-Object FullName
```
Lo zip deve avere data e ora di oggi, 04/11/2026. Se è più vecchio, non è quello giusto: chiedi lo zip nuovo. Il secondo
comando elenca gli eventuali `.env`. Va bene anche se non ne elenca nessuno.

**3. [PC]** Estrai lo zip dentro il clone, sovrascrivendo i file. Le cartelle `.git` e `.env`, la `fase2-gradi-giorno` e
`iscrizioni` non sono nello zip e restano come sono:
```powershell
Expand-Archive -Path ..\eugenio_2026-11-04.zip -DestinationPath . -Force
Test-Path .git
dir .github\workflows
Select-String -Path .gitignore -Pattern "uni_privato"
```
Cosa aspettarsi:
- `True`;
- il file `visure-windows.yml`;
- la riga `fase10-edifici3d/uni_privato/` del `.gitignore`.

Se `Expand-Archive` dà errore, usa «Estrai tutto» di Esplora file: come destinazione indica la cartella `eugenio` e
scegli «Sostituisci i file».

**4. [PC]** Controlla che le pagine siano già rigenerate (il comando non scrive nulla). Il secondo comando, facoltativo,
esegue i test della fase 5:
```powershell
cd fase5-sito
python costruisci_pagine.py --controlla
python -m pytest -q tests
cd ..
```
Cosa aspettarsi:
- `versione 20261104c: 0 file da rigenerare`;
- `19 passed`. Se sul PC manca Playwright, i 2 test nel browser vengono saltati: `17 passed, 2 skipped` va bene.

Se il primo comando elenca dei file da rigenerare, lo zip non è stato estratto del tutto: rifai il passo 3.

**5. [PC]** Ambiente della fase 11. Serve per tre cose: i test di EuGEnio Visure, le visure sintetiche e i modelli
DXF/IFC sintetici. Il passo vale anche se `.venv` esiste già: `requirements-modelli.txt` è nuovo e va installato.
```powershell
cd fase11-visure
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q tests
```
Cosa aspettarsi:
- il comando `pip` finisce con `Successfully installed …` (oppure `Requirement already satisfied`);
- i test finiscono senza `failed`, con **`71 passed`**. Se sul PC manca qualcosa (node, Chromium), compare qualche
  `skipped`: va bene.

Se `py -3.13` dice che la versione non c'è, installa Python 3.13 a 64 bit da python.org, con «py launcher», e ripeti. Se
`.venv` esiste già, il primo comando non fa danni.

**6. [PC]** Visure sintetiche e lettura (sei sempre in `fase11-visure`):
```powershell
.\.venv\Scripts\python -m visure esempi --uscita ..\..\visure_prova
.\.venv\Scripts\python -m visure leggi ..\..\visure_prova --patrimonio ..\..\visure_prova\patrimonio_esempio_visure.csv --uscita ..\..\visure_prova\risultati --ordina
```
Il secondo comando elenca 6 PDF: 4 «letta», uno «non_riconosciuta» e uno «senza_testo». Finisce con `9 unità, 6 edifici`.

**7. [PC]** Modelli DXF/IFC sintetici, che servono alla Parte 7 e alla Parte 8. Usano ezdxf e IfcOpenShell dell'ambiente
della fase 11:
```powershell
.\.venv\Scripts\python ..\fase10-edifici3d\tests\modelli_sintetici.py ..\..\prove_modelli
cd ..
dir ..\prove_modelli
```
Devono comparire cinque file: `casa_metri.dxf`, `casa_utm.dxf`, `casa_mm.dxf`, `casa_sito.ifc` e `casa_mappa_mm.ifc`. Le
cartelle `visure_prova` e `prove_modelli` stanno fuori da `eugenio`, quindi git non le vede.

**8. [PC]** Controlla che la fase 2, il modulo UNI privato e i segreti restino fuori da git (sei in `eugenio`):
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x fase11-visure/.venv/x
git ls-files fase2-gradi-giorno fase10-edifici3d/uni_privato
```
Cosa aspettarsi:
- cinque righe, una per percorso, del tipo `.gitignore:12:fase2-gradi-giorno/	fase2-gradi-giorno/README.md`. Il
  numero di riga può essere diverso;
- dal secondo comando, **nessuna riga**.

Se il secondo comando stampa dei file, quei file sono già in git da prima. Toglili dall'indice: i file restano sul disco.
Poi dimmelo, perché restano nella storia del repository:
```powershell
git rm -r --cached fase2-gradi-giorno
```
(oppure `fase10-edifici3d/uni_privato`).

## Parte 2 – Commit e push

**9. [PC]** Aggiungi i file e controlla la lista prima del commit:
```powershell
git add -A
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|Visure_|intestatari_DATI_PERSONALI|visure_vere"
git status --short | Measure-Object
```
Cosa aspettarsi:
- il primo controllo non stampa **nulla**;
- il secondo stampa un `Count` di qualche centinaio. Le novità del 03/11 e del 04/11 sono tante: va bene.

Se il primo controllo stampa qualcosa, togli quei file dall'indice prima del commit, con
`git restore --staged <percorso>` (o `git rm -r --cached <percorso>`), e dimmelo.

**10. [PC]** Commit, con il messaggio suggerito:
```powershell
git commit -m "Pubblicazione del 03-04/11/2026: menu a cinque gruppi e fasi 10-13; edifici 3D (fasi A, B, C, E), Previsioni a schede con Solo clima, ortofoto, pipeline LiDAR e pagina interna, EuGEnio Visure, Importa DXF/IFC, menu fissabile e voci GME non cliccabili; sito ?v=20261104c" -m "Modulo UNI privato, fase 2 e .env fuori dal repository."
```
L'ultima riga dice quanti file sono cambiati (`… files changed`).

**11. [PC]** Push:
```powershell
git push
```
L'ultima riga deve essere del tipo `abc1234..def5678  main -> main`.

Se il push viene rifiutato (`rejected`, `fetch first`), su GitHub c'è un commit che il PC non ha. Fai
`git pull --rebase`, poi di nuovo `git push`. Se `git pull` segnala conflitti, fermati e mandami le righe.

**12. [GitHub]** Controlla che il workflow ci sia. Apri **github.com/statocritico/eugenio** → scheda **Actions**: nella
colonna di sinistra deve comparire **visure-windows**.
- Il push **non** avvia il workflow. È normale che non ci sia nessuna esecuzione: si avvia al passo 13.
- Se in **Actions** compare «Workflows aren't being run on this repository», premi il pulsante verde per attivarli.

## Parte 3 – Avvio della costruzione dell'.exe (GitHub Actions)

**13. [GitHub]** **Actions** → **visure-windows** (a sinistra) → a destra **Run workflow** → **Branch**: il ramo del
passo 1 (es. `main`) → **Run workflow**.

Dopo qualche secondo compare un'esecuzione con il pallino giallo. Non aspettarla: vai avanti con la Parte 4. La riprendi
alla Parte 8.

## Parte 4 – Cloudflare (dal browser)

**14. [Cloudflare] Rate limiting.** La regola «API EuGEnio» blocca a 60 richieste in 10 s su `/api/`. Bloccherebbe le
tessere delle ortofoto, perché una mappa ne chiede 20–40 insieme.

Apri **dash.cloudflare.com** → **statocritico.it** → **Security** → **Security rules** (oppure **WAF** → **Rate limiting
rules**) → **API EuGEnio** → **Edit** → **Edit expression**. Scrivi:
```
(starts_with(http.request.uri.path, "/api/") and not starts_with(http.request.uri.path, "/api/ortofoto/"))
```
Premi **Save**.
- Se l'editor rifiuta `starts_with` (sul piano gratuito alcune funzioni possono mancare), usa questa forma equivalente:
  ```
  (http.request.uri.path contains "/api/" and not http.request.uri.path contains "/api/ortofoto/")
  ```
- Le tessere restano comunque limitate dal server (3.000 all'ora per indirizzo) e dalla cache di Cloudflare.

**15. [Cloudflare] Team domain di Access.** Apri **one.dash.cloudflare.com** (Zero Trust) con l'account di
statocritico.it → **Settings** → **Custom Pages** (o **Team name and domain**). Leggi il **Team domain**: è del tipo
`<nome>.cloudflareaccess.com`. Tienilo a portata di mano per il passo 24, senza scriverlo in nessun file del progetto.

**16. [Cloudflare] Applicazione Access.** **Access** (nella dashboard nuova **Access controls**) → **Applications** →
**Add an application** → **Self-hosted**.
- Nome: `EuGEnio interno`.
- **Session Duration**: `24 hours`.

**17. [Cloudflare]** In **Application domain** metti due righe (la seconda con **Add domain**):
- Subdomain `eugenio`, Domain `statocritico.it`, Path `interno/*`;
- Subdomain `eugenio`, Domain `statocritico.it`, Path `api/interno/*`.

**18. [Cloudflare]** **Next** → **Add a policy**:
- nome `solo Paolo`, Action **Allow**;
- **Include** → **Emails** → la tua email, la stessa della policy di `notizie.statocritico.it/admin`. Puoi anche
  riusare la policy «solo Paolo» che esiste già;
- metodo di accesso **One-time PIN**.

Poi **Next** → **Add application**.

**19. [Cloudflare]** Riapri `EuGEnio interno` → **Overview** (o **Basic information**) e copia l'**Application Audience
(AUD) Tag**, una lunga stringa esadecimale. Ti serve al passo 24, poi non lasciarlo in giro (note, chat).

## Parte 5 – Pacchetti e copia sul server (PC)

**20. [PC]** Pacchetto del **codice del server**, come nella pubblicazione del 28/10/2026. Contiene le fasi 3, 4, 6, 7,
8, 9 e 10 e il `.dockerignore`. Restano fuori la fase 2, il modulo UNI privato, gli ambienti e i `.env`. Sei in
`eugenio`:
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=.venv-build --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env --exclude=uni_privato --exclude=node_modules .dockerignore fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d
dir ..\codice.tar.gz
tar -tzf ..\codice.tar.gz | Select-String -Pattern "uni_privato|fase2|(^|/)\.env$|\.venv"
```
Cosa aspettarsi:
- un file di **meno di 3 MB**;
- l'ultimo comando non stampa **nulla**.

Se il file è molto più grande, o se l'ultimo comando stampa qualcosa, fermati e dimmelo.

**21. [PC]** Pacchetto del **sito**, senza `dati/indicatori`, che il server rifà da sé:
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
dir ..\sito.tar.gz
```
Il file deve avere l'ora di adesso e pesare qualche MB (circa 5 MB compressi: dentro ci sono anche web-ifc e MapLibre).

**22. [PC]** Copia i due pacchetti sul server:
```powershell
scp ..\codice.tar.gz ..\sito.tar.gz eugenio:~/
```
Per ognuno dei due file compare una riga con `100%`.

## Parte 6 – Server

**23. [Server]** Entra nel server, fai una copia di sicurezza del codice di oggi e sostituiscilo con quello nuovo. Il
`.env` del server non è nel pacchetto e resta com'è:
```bash
cp -a ~/energia ~/energia_prima_20261104
tar -xzmf ~/codice.tar.gz -C ~/energia && ls ~/energia
ls -l ~/energia/fase4-server/.env
test -d ~/energia/fase10-edifici3d/uni_privato && echo PRESENTE || echo assente
```
Prima di questi comandi dai `ssh eugenio`.

Cosa aspettarsi:
- `ls` elenca anche `fase10-edifici3d`;
- il `.env` ha i permessi `-rw-------`;
- l'ultimo comando stampa `assente`.

**24. [Server] Righe nuove del `.env`.** Ogni riga si aggiunge solo se manca; i valori segreti si scrivono dopo, con
nano:
```bash
cd ~/energia/fase4-server
grep -q '^CARTELLA_EDIFICI=' .env || echo "CARTELLA_EDIFICI=/srv/energia/dati/edifici" >> .env
grep -q '^ORTOFOTO_SPENTE=' .env || printf "ORTOFOTO_SPENTE=\nORTOFOTO_MAX_GB=15\n" >> .env
grep -q '^CF_ACCESS_TEAM_DOMAIN=' .env || printf "CF_ACCESS_TEAM_DOMAIN=\nCF_ACCESS_AUD=\nCF_ACCESS_EMAIL=\nEDIFICI_STATO=/dati/edifici_stato\nINTERNO_ORA=300\n" >> .env
nano .env
```
In nano, in fondo al file, completa tre righe, senza virgolette e senza spazi:
- `CF_ACCESS_TEAM_DOMAIN=` seguito dal team domain del passo 15;
- `CF_ACCESS_AUD=` seguito dall'AUD del passo 19;
- `CF_ACCESS_EMAIL=` seguito dalla tua email.

Salva con Ctrl+O, Invio, Ctrl+X.

`ORTOFOTO_SPENTE` resta **vuota**: per la decisione del 04/11/2026 la RER si pubblica accesa con «uso da confermare».
Le altre variabili nuove del `.env.example` (`ORTOFOTO_GIORNI`, `PVGIS_*`, `ORIZZONTE_*`, …) hanno già nel codice gli
stessi valori predefiniti: non serve aggiungerle.

**25. [Server]** Controlla il `.env`. I comandi stampano solo conteggi, mai i valori:
```bash
grep -c -E "^(CARTELLA_EDIFICI|ORTOFOTO_SPENTE|ORTOFOTO_MAX_GB|CF_ACCESS_TEAM_DOMAIN|CF_ACCESS_AUD|CF_ACCESS_EMAIL|EDIFICI_STATO|INTERNO_ORA)=" .env
grep -c -E "^CF_ACCESS_(TEAM_DOMAIN|AUD|EMAIL)=.+" .env
grep -c -E "^CF_ACCESS_TEAM_DOMAIN=[a-z0-9-]+\.cloudflareaccess\.com$" .env
ls -l .env
```
Cosa aspettarsi:
- `8`, poi `3`, poi `1`;
- i permessi `-rw-------`.

Se il secondo o il terzo conteggio non torna, riapri `nano .env`: di solito c'è uno spazio, o `https://` davanti al team
domain. Se i permessi sono cambiati, rimettili con `chmod 600 .env`.

**26. [Server] Cartelle dei dati** per edifici, stato della pipeline, ortofoto, orizzonte e PVGIS, scrivibili
dall'utente 1000 dei container:
```bash
mkdir -p /srv/energia/dati/edifici/cc-by /srv/energia/dati/edifici/odbl /srv/energia/dati/edifici_stato /srv/energia/dati/ortofoto /srv/energia/dati/orizzonte /srv/energia/dati/pvgis
sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX /srv/energia/dati/edifici /srv/energia/dati/edifici_stato /srv/energia/dati/ortofoto /srv/energia/dati/orizzonte /srv/energia/dati/pvgis
getfacl -n -p /srv/energia/dati/edifici_stato | grep 1000
```
Cosa aspettarsi: le righe `user:1000:rwx` e `default:user:1000:rwx`.

Se `mkdir` dice `Permission denied`, ripetilo con `sudo` davanti.

**27. [Server] Sito.** Il primo comando pubblica il sito e controlla la versione:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261104c /srv/energia/sito/index.html /srv/energia/sito/importa-dxf-ifc.html /srv/energia/sito/interno/edifici.html
ls -l /srv/energia/sito/lib/web-ifc/web-ifc.wasm /srv/energia/sito/cog-car.html
```
Cosa aspettarsi:
- tre righe `…:N`, tutte con N maggiore di 0;
- `web-ifc.wasm` di 1303940 byte e la pagina `cog-car.html`.

Caddy serve subito i file statici, ma le parti nuove (`/interno/`, `/edifici3d/`) funzionano solo dopo il passo 29.

**28. [Server] Rebuild dell'api.** Una volta sola: comprende Previsioni, Fasi A, B, C ed E e PyJWT. Dura qualche minuto:
```bash
cd ~/energia/fase4-server && docker compose up -d --build api
docker compose ps api
```
Dopo circa un minuto `docker compose ps api` deve mostrare `Up … (healthy)`.

Se non diventa `healthy`, guarda `docker compose logs --tail 40 api` e mandami le ultime righe. Una riga «modulo privato
… non caricato» non è un errore: il modulo è rinviato.

**29. [Server] Caddy.** Il Caddyfile è cambiato e anche i volumi nel `docker-compose.yml`: il container va ricreato,
non solo riavviato:
```bash
docker compose up -d --force-recreate caddy
docker compose ps caddy
docker compose logs --tail 10 caddy
```
Cosa aspettarsi: `Up`, e nel registro nessuna riga con `"level":"error"`.

Se caddy non resta acceso, nel registro c'è la riga del Caddyfile sbagliata: mandamela.

**30. [Server] Immagine della pipeline degli edifici.** Dura qualche minuto: compila GDAL, laspy e IfcOpenShell per ARM.
```bash
docker compose --profile edifici build edifici-lidar
```
Finisce con `Built`, oppure con `naming to … energia-edifici`.

**31. [Server] Controlli dentro l'api.** Dai i comandi uno alla volta:
```bash
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/salute').read()[-60:])"
docker compose exec -T api grep -c "re-identificare" /app/servizio/report.py
docker compose exec -T api python -c "import servizio.edifici; print('ok')"
docker compose exec -T api python -c "import urllib.request as u, urllib.error as e
try: print(u.urlopen('http://localhost:8000/api/edifici/gradi-giorno/099014').status)
except e.HTTPError as x: print(x.code)"
docker compose exec -T api python -c "import urllib.request as u, urllib.error as e
try: print(u.urlopen('http://localhost:8000/api/clima-previsto/099014').read()[:120])
except e.HTTPError as x: print(x.code)"
docker compose exec -T api ls /app/ortofoto_fonti
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/ortofoto/fonti').read()[:200])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://localhost:8000/api/ortofoto/s2cloudless2016/12/2190/1478.jpg'); print(r.status, r.headers['Content-Type'])"
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/edifici/orizzonte?lat=44.06&lon=12.567&h=10').read()[:150])"
docker compose exec -T api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/analisi/stato').read()[:300])"
docker compose exec -T api ls /app/edifici3d
docker compose exec -T api python -c "import urllib.request as u, urllib.error as e
try: print(u.urlopen('http://caddy/api/interno/edifici/stato').status)
except e.HTTPError as x: print(x.code)"
```
Risultati attesi, nell'ordine:

| # | Atteso |
|---|---|
| 1 | un testo che finisce con `"previsioni_in_corso": 0}` |
| 2 | `1` |
| 3 | `ok` |
| 4 | `200`, oppure `503` finché il pacchetto meteo della fase 3 non è sul server: vanno bene tutti e due |
| 5 | `b'{…` con le variabili del clima, oppure `404` («dati meteo non ancora sul server»): vanno bene tutti e due, annota quale |
| 6 | `bolzano.toml  emilia_romagna.toml  italia.toml  toscana.toml  trento.toml` |
| 7 | `b'{"fonti":[{"id":"rer2023"…` |
| 8 | `200 image/jpeg` |
| 9 | un testo con `"angoli"`; `HTTP Error 503` vuol dire che il server non raggiunge S3 o manca `omfiles`: mandami la riga |
| 10 | `b'{"interfaccia":1,"modulo":false,…` con tutte le analisi `"disponibile":false`: è giusto, il modulo UNI è rinviato |
| 11 | `__init__.py  analisi.py` |
| 12 | `403`: Caddy rifiuta le pagine interne senza l'intestazione di Cloudflare Access |

**32. [Server] Il WebAssembly deve arrivare con il suo tipo.** Il comando passa da Cloudflare:
```bash
curl -sI https://eugenio.statocritico.it/lib/web-ifc/web-ifc.wasm | grep -i -E "^(HTTP|content-type|content-length)"
```
Cosa aspettarsi:
- `HTTP/2 200`;
- **`content-type: application/wasm`**;
- se compare, `content-length: 1303940`.

Lo stesso controllo si fa anche dal PC. In PowerShell scrivi `curl.exe`, non `curl`, che lì è un'altra cosa:
`curl.exe -sI https://eugenio.statocritico.it/lib/web-ifc/web-ifc.wasm`.

Cosa fare se va male:
- `404`: il passo 27 non è andato a buon fine;
- un altro tipo (es. `application/octet-stream`): la pagina funziona lo stesso, perché web-ifc ripiega su un caricamento
  più lento. Mandami la riga.

**33. [Server] Pagine interne chiuse dall'esterno.** Senza login Cloudflare Access deve fermare la richiesta:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://eugenio.statocritico.it/api/interno/edifici/stato
curl -s -o /dev/null -w "%{http_code}\n" https://eugenio.statocritico.it/interno/edifici.html
```
Cosa aspettarsi: `302` (il rinvio al login di Access) oppure `401` o `403`. **Mai `200`**.

Se compare `200`, Access non copre quel percorso: ricontrolla il passo 17.

**34. [Server] Prove della pipeline.** Dai i comandi uno alla volta:
```bash
docker compose --profile edifici run --rm edifici-lidar lidar-fonti --zona rimini --prova
docker compose --profile edifici run --rm edifici-lidar lidar --zona rimini --archivio /dati/edifici --stato /dati/edifici_stato --subito
docker compose --profile edifici run --rm --entrypoint sh edifici-lidar -c "test -d /app/uni_privato && echo NELL_IMMAGINE || echo fuori"
```
Cosa aspettarsi:
- dal primo, l'elenco delle fonti: quattro «in attesa» (il DSM della costa 2019 resta spento), `rer_dtm05` e `rer_dtm5`
  «attiva», con le righe della prova dal vivo (quadro di unione «coperta 32_…», `HTTP 200 image/tiff` per i DTM);
- dal secondo, un JSON con `"esito": "in attesa"` e `"motivo": "nessuna fonte DSM o LAS attiva …"`;
- dal terzo, `fuori`.

Cosa fare se va male:
- se l'ultimo stampa `NELL_IMMAGINE`, il `.dockerignore` non è arrivato in `~/energia`: rifai i passi 20, 22, 23 e 30;
- se il secondo dà `PermissionError`, rifai il passo 26.

**35. [Server] Facoltativo: verifica dal vivo delle fonti regionali dal server.** Molti portali del Centro-Sud chiudono
le connessioni che arrivano da fuori Italia, e il server è a Milano:
```bash
docker compose --profile edifici run --rm edifici-lidar regioni --prova > ~/regioni_prova.txt; tail -40 ~/regioni_prova.txt
```
Mandami le righe con `errore` e quelle di Piemonte e Basilicata: con quelle aggiorno `regioni.toml`.

**36. [Server] Cron della pipeline notturna** alle 3:30, dopo i mercati delle 02:30. La pipeline si ferma da sola alle
7:00.
```bash
crontab -l | grep -c edifici-lidar
(crontab -l 2>/dev/null; echo "30 3 * * * cd /home/ubuntu/energia/fase4-server && docker compose --profile edifici run --rm -T edifici-lidar >> /home/ubuntu/edifici.log 2>&1") | crontab -
crontab -l
```
Cosa aspettarsi:
- il primo comando stampa `0`. Se stampa `1`, la riga c'è già: **non** dare il secondo comando;
- `crontab -l` mostra la riga nuova e anche quella dei mercati delle 02:30, che deve restare.

**Regola (05/11/2026)**: il crontab dell'host si cambia **solo** partendo da `crontab -l` (come qui sopra, o con
`crontab -e`), **mai** con un `… | crontab -` che non parte da `crontab -l`: sostituisce tutto il crontab. Il 05/11/2026 il
crontab era vuoto (righe di mercati, indicatori e clima sparite tra il 03/11 e il 04/11, notte dei mercati del 04/11
saltata). Prima di cambiarlo salva una copia: `crontab -l > ~/crontab_prima_$(date +%Y%m%d).txt`. Dopo **ogni**
pubblicazione dai `crontab -l` e controlla che ci siano le 4 righe (sezione «Controllo del crontab» di
`AGGIORNAMENTO_2026-11-05.md`).

La mattina dopo, `tail -30 ~/edifici.log` deve mostrare l'esito «in attesa», come al passo 34.

**37. [Server] Pulizia:**
```bash
rm ~/codice.tar.gz ~/sito.tar.gz
exit
```
La copia `~/energia_prima_20261104` tienila qualche giorno. Quando tutto funziona, cancellala con
`rm -rf ~/energia_prima_20261104`.

## Parte 7 – Prove nel browser

Usa il PC (Ctrl+F5 sulla prima pagina) e, dove indicato, il telefono. Per le pagine 3D apri la console con F12: alla
fine **non** devono esserci righe rosse né `429`.

**38. [Browser] Menu (03/11).**
- La seconda riga della testata mostra **Clima e meteo, Patrimonio, Edificio, Cogenerazione, Fotovoltaico** con le
  freccine.
- Mouse sopra **Edificio** (senza cliccare): si apre la tendina con 8 voci. Sposta il mouse in basso: si chiude.
- Clic su **Patrimonio**: sotto la barra compare una riga **nera** con le 6 voci affiancate; tenendo fermo il mouse sul
  titolo compare «Clicca qui per richiudere la barra di Patrimonio e tornare al menu a tendina». Clic su **Edificio**:
  la riga passa a Edificio (8 voci, su due righe). Apri una voce della riga: nella pagina nuova la riga c'è ancora, con la
  voce sottolineata. Clic di nuovo su **Edificio**: la riga sparisce e torna la tendina.
- Da tastiera: Tab fino a **Clima e meteo** (la tendina si apre), freccia giù, freccia destra (Patrimonio), Esc.
- In alto a destra ci sono Indicatori, Come funziona, F.A.Q., Sitografia, Mirror e Contattaci.
- Mouse sopra **Cogenerazione**: 5 voci su 6 sono grigie con l'etichetta «licenza GME» tratteggiata; fermo sopra una di
  queste compare «In attesa di autorizzazione dal GME» e il clic non apre nessuna pagina. Solo **Emissioni** si apre.
- Scrivendo l'indirizzo `cog-car.html`, la pagina dice «In attesa della licenza GME» e non mostra nessun numero di
  prezzo.
- `faq.html#zornade` apre la domanda su particelle e indirizzi trovati con Zornade.
- Dal telefono: **Menu** mostra «Servizi» con i cinque gruppi, poi «Altre pagine» e «Aspetto»; in Cogenerazione le voci
  «licenza GME» non si aprono (un tocco mostra «In attesa di autorizzazione dal GME»).

**39. [Browser] Previsioni con le schede** (Clima e meteo › Previsioni).
1. Scarica l'esempio dalla pagina: link «esempio orario» al passo 2.
2. Scegli Rimini sulla mappa, lascia «I consumi, con il meteo», carica il file e lancia la previsione.
3. Il risultato è diviso in schede: **Consumo** e una scheda per ogni parametro climatico attivo. Ogni scheda ha il suo
   grafico, la freccina ↗ del riquadro e «Scarica la previsione».
4. Scarica il **CSV**: ha tutte le colonne, comprese le righe del passato. Scarica il **PDF**: nella sezione «Grafici»
   ci sono prima i consumi, poi i parametri. Scarica l'**Excel**: colonne affiancate.
5. Clicca un altro comune: il file si toglie, con un messaggio. Ricarica il file, poi fai un **secondo clic sul comune
   scelto**: il comune si toglie insieme al file.

**40. [Browser] Previsioni, «Solo clima».**
- Scegli «Solo il clima, senza consumi»: il riquadro del file sparisce.
- Scegli Rimini e lancia: compaiono solo le schede dei parametri, con il report «Previsione del clima».
- Se compare «I dati meteo di questo comune non sono ancora sul server», è il caso `404` del passo 31 (riga 5): va
  bene finché il pacchetto meteo non è sul server.
- In **Legge 10**, il secondo clic sul comune scelto lo toglie, risultati compresi. Anche nella ricerca dei **Dati
  climatici**, un comune già scelto si toglie.

**41. [Browser] Ortofoto** (Patrimonio › Ortofoto).
- Si apre Rimini con l'ortofoto RER. Sotto la mappa c'è la riga «Ortofoto: … – licenza CC BY 4.0…» con «uso da
  confermare».
- A destra cambia fonte: la riga sotto la mappa cambia con lei.
- Apri `https://eugenio.statocritico.it/ortofoto.html?lat=46.4983&lon=11.3548&z=17`: Bolzano, con l'ortofoto 2023 e
  «licenza verificata».
- Con `lat=46.0679&lon=11.1211` invece: Trento 2015.
- Nella console nessun `429`. Se ci sono, il passo 14 non è salvato.

**42. [Browser] Modelli 3D** (Patrimonio › Modelli 3D).
1. Compaiono l'avviso «Dati sintetici di esempio» e la mappa 3D dell'isolato.
2. Clic sull'edificio arancione: a destra compaiono corpi, superfici e indicatori.
3. Il corpo a capanna di E-DEMO ha le falde a gradini. Al passo «Corpi» c'è la tabella «Falde dei tetti» con l'avviso
   del rilievo sintetico.
4. «Aggiungi un'area», poi clic sulla falda sud: inclinazione 23°, orientamento 180°.
5. Scegli «Sfondo della mappa: Ortofoto RER…» e premi **PDF**. Si scarica `edificio.pdf`:
   - in cima l'avviso sui dati sintetici;
   - nella sezione «Figure» la vista con l'ortofoto, con licenza e citazione nella didascalia.

**43. [Browser] Fotovoltaico ed Edificio.**
- **Fotovoltaico › Producibilità con le ombre**: «Aggiungi un'area», clic su un tetto, «Calcola la producibilità».
  Compaiono il totale, con l'avviso sul clima sintetico finché il meteo non è sul server, e il grafico mensile.
- **Fotovoltaico › Sole e irradiazione su tetti e facciate**: «Calcola il sole sulle facciate». Dopo qualche secondo
  compaiono la tabella per orientamento e le facciate colorate.
- **Fotovoltaico › Confronto con PVGIS**: area, «Calcola la producibilità», poi «Confronta con PVGIS». Compaiono la
  tabella EuGEnio / PVGIS e il grafico mensile.
- **Edificio › Obblighi di legge**: la tabella con P = k · S, la zona climatica e H'T massimo. Se cambi «Intervento» o
  «edificio pubblico», i valori cambiano.
- **Edificio › Pompe di calore e solare termico**: sotto il riquadro grigio compaiono due righe «… (analisi 10): analisi
  non disponibile in questa installazione.» e «… (analisi 11): …». Lo stesso in Fabbisogno, Comunità energetiche,
  Facciate e tetti, Clima che cambia e Fotovoltaico › Prefattibilità LEED.

**44. [Browser] Importa DXF/IFC** (Patrimonio › Importa DXF/IFC), con i file sintetici del passo 7.
1. Premi F12 e apri la scheda **Rete** (Network).
2. Al passo 1 scegli `C:\Users\ingpa\Documents\claude\pj\statocritico\prove_modelli\casa_sito.ifc`. Dopo qualche
   secondo:
   - compare «File letto»;
   - al passo 2 la pianta mostra due corpi;
   - al passo 3 compare «come indicato nel file (IfcSite)»;
   - il modello compare sulla mappa vicino a Rimini;
   - la tabella del passo 4 dice capanna (gronda 7, colmo 10) e piano (4).
   
   Nella scheda Rete compaiono `web-ifc.wasm` e le tessere dell'ortofoto, e **nessuna richiesta POST**.
3. Premi **Apri nella pagina Modelli 3D**: compare «Modello «casa_sito»: 2 corpi (letto solo in questo browser)».
4. Torna a Importa DXF/IFC e scegli `casa_metri.dxf`. Al passo 3 resta scelto «due punti noti». Scrivi:
   - nella riga 1: `0`, `0`, `12,5665`, `44,06`;
   - nella riga 2: `10`, `0`, `12,566625`, `44,06`.
   
   Poi premi **Posiziona il modello**: compaiono sei corpi (capanna, padiglione, monofalda, tre piani) e l'avviso dei
   3DSOLID. Prova anche col clic: un clic sulla pianta vicino a uno spigolo, poi un clic sulla mappa sul punto vero.
5. In un'altra pagina (es. Modelli 3D), la scheda Rete **non** deve mostrare `web-ifc`, `dxf-parser`, `clipper` né
   `proj4`.

**45. [Browser] Patrimonio con le visure** (Patrimonio › Patrimonio), con i file del passo 6.
1. Carica `C:\Users\ingpa\Documents\claude\pj\statocritico\visure_prova\patrimonio_esempio_visure.csv` e premi «Trova
   gli edifici». Le particelle sono inventate: Zornade può non trovarle, va bene.
2. Al passo «Visure catastali» carica `visure_prova\risultati\indice.csv`: compaiono i conteggi e, nelle schede, le
   righe «Visura (…)».
3. Premi «Scarica il risultato con le visure (CSV)»: il file ha le colonne `visura_…`.
4. **Patrimonio › Visure**: la pagina descrive il programma e le condizioni d'uso.

**46. [Browser] Pagina interna.**
1. Apri `https://eugenio.statocritico.it/interno/edifici.html`: compare la pagina di Cloudflare Access.
2. Chiedi il codice e scrivilo: si apre «Stato della pipeline degli edifici», con Rimini (fonti in attesa, una notte «in
   attesa», quella del passo 34) e lo spazio su disco.
3. In una **finestra anonima** apri `https://eugenio.statocritico.it/api/interno/edifici/stato`: deve comparire il
   login di Cloudflare, **mai** i dati.

Cosa fare se va male:
- **503 «non configurata»**: mancano `CF_ACCESS_TEAM_DOMAIN` o `CF_ACCESS_AUD` (passi 24 e 25). Poi, sul server,
  `cd ~/energia/fase4-server && docker compose up -d api`;
- **403 dopo il login**: il team domain o l'AUD non coincidono con l'applicazione. Dai
  `docker compose logs --tail 20 api | grep interno` e mandami le righe, senza il gettone.

## Parte 8 – EuGEnioVisure.exe

### 8A. Da GitHub Actions (consigliato)

**47. [GitHub]** **Actions** → l'esecuzione del passo 13. I job `test-linux` ed `exe` devono essere verdi. Il job `firma`
è «skipped» (SignPath non è configurato) e anche `release` (non c'è un tag): va bene.

Se `exe` è rosso al passo «Pacchetto del lettore e controllo dell'impronta», vedi il passo 54. Se è rosso altrove, apri
il passo rosso e mandami le ultime 20 righe.

**48. [GitHub]** Nella pagina dell'esecuzione, in fondo, in **Artifacts**, scarica:
- `eugenio-visure-non-firmato` (l'.exe);
- `eugenio-visure-pacchetto` (lo zip del lettore).

**49. [PC]** Estrai i due artefatti in una cartella di prova fuori dal repository. Il primo comando crea la cartella;
gli artefatti scaricati sono zip, di solito nella cartella `Download`:
```powershell
New-Item -ItemType Directory -Force C:\Users\ingpa\Documents\claude\pj\statocritico\visure_exe
cd C:\Users\ingpa\Documents\claude\pj\statocritico\visure_exe
Expand-Archive -Force $env:USERPROFILE\Downloads\eugenio-visure-non-firmato.zip .
Expand-Archive -Force $env:USERPROFILE\Downloads\eugenio-visure-pacchetto.zip .
Unblock-File .\EuGEnioVisure.exe
dir
```
Devono comparire `EuGEnioVisure.exe` e `visure-0.1.0.zip`.

Poi vai ai controlli del passo 52.

### 8B. In alternativa: costruzione in locale

**50. [PC] Prerequisiti:**
- Windows 10/11 a 64 bit;
- **Python 3.13** a 64 bit da python.org, con il «py launcher»;
- il clone aggiornato (Parte 1);
- la rete, per `pip`;
- circa 3 GB liberi.

Controllo:
```powershell
py -3.13 --version
```
Deve stampare `Python 3.13.x`.

**51. [PC]** Costruzione. Lo script crea l'ambiente `.venv-build`, esegue i test, costruisce il pacchetto, ne controlla
l'impronta, lancia PyInstaller e prova l'.exe:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase11-visure
powershell -ExecutionPolicy Bypass -File avviatore\costruisci_windows.ps1
```
La prima volta dura 10–20 minuti. Compaiono, in ordine:
- `1. Test`;
- `2. Pacchetto del lettore e impronta`;
- `3. PyInstaller`;
- `5. Prova dell'.exe`. Il passo 4, la firma, si salta;
- alla fine, in verde, `Fatto: dist\EuGEnioVisure.exe (SHA-256 …)`.

I file sono in `fase11-visure\dist\`, che git ignora: `EuGEnioVisure.exe`, `EuGEnioVisure.exe.sha256`,
`visure-0.1.0.zip` e `visure-0.1.0.zip.sha256`. Per i controlli del passo 52 entra in quella cartella (`cd dist`).

Cosa fare se va male:
- se si ferma con «test non superati», mandami le ultime 20 righe;
- se si ferma con «L'impronta … non e' quella dell'elenco», vedi il passo 54.

### 8C. Controlli dell'.exe (in tutti e due i casi)

**52. [PC]** Nella cartella dell'.exe, `visure_exe` oppure `fase11-visure\dist`, dai i comandi uno alla volta:
```powershell
"{0:N1} MB" -f ((Get-Item .\EuGEnioVisure.exe).Length / 1MB)
(Get-FileHash .\EuGEnioVisure.exe -Algorithm SHA256).Hash.ToLower()
Measure-Command { .\EuGEnioVisure.exe --non-aggiornare prova --modelli | Out-Host }
.\EuGEnioVisure.exe --non-aggiornare modello C:\Users\ingpa\Documents\claude\pj\statocritico\prove_modelli\casa_sito.ifc --uscita casa_sito.geojson
.\EuGEnioVisure.exe --non-aggiornare modello C:\Users\ingpa\Documents\claude\pj\statocritico\prove_modelli\casa_utm.dxf --crs EPSG:7791 --uscita casa_utm.geojson
```
Cosa aspettarsi, comando per comando:

| Comando | Atteso |
|---|---|
| dimensione | **circa 90 MB** (88,3 MB la build di Actions del 05/11/2026; la prova Linux, con altre librerie, pesava 137 MB). Annotala |
| impronta dell'.exe | una stringa di 64 caratteri. Annotala: non è nell'elenco delle versioni approvate, che contiene l'impronta del **pacchetto del lettore**; quella dell'.exe va nel `SHA256SUMS.txt` della release |
| avvio | le righe dell'avviatore, `· in uso la versione 0.1.0 (SHA-256 3fc84c6ae60536a1…)`, poi **due righe `OK:`** (lettore e conversione dei modelli). `Measure-Command` stampa il tempo (`TotalSeconds`): **circa 8 s alla prima esecuzione** (7,9 s il 05/11/2026: estrazione del file unico e controllo dell'antivirus; Linux 2,5 s), meno alle successive. Con `\| Out-Host` i caratteri accentati possono apparire come «ÔÇô», «├®», «┬À»: è solo la decodifica di PowerShell (codepage 850); prima del comando dai `[Console]::OutputEncoding = [Text.Encoding]::UTF8` |
| IFC | `2 corpi → casa_sito.geojson` |
| DXF | una riga `… corpi → casa_utm.geojson`, senza errori |

Poi apri `casa_sito.geojson` al passo 1 della pagina **Importa DXF/IFC**: deve dire «Modello già convertito: 2 corpi».

Fai anche doppio clic sull'.exe:
- Windows mostra «PC protetto da Windows», perché l'.exe non è firmato: **Ulteriori informazioni** → **Esegui
  comunque**;
- si apre una finestra con «in uso la versione 0.1.0», poi il browser sulla pagina locale (`http://127.0.0.1:8770`),
  con la scheda **Modelli DXF/IFC**;
- chiudi la finestra nera per fermarlo.

**53. [PC] Verifica dell'impronta rispetto a `versioni_approvate.json`.** Per il caso Actions, nella cartella
`visure_exe`; per la costruzione locale, in `fase11-visure\dist`, con il percorso dell'elenco `..\avviatore\…`:
```powershell
(Get-FileHash .\visure-0.1.0.zip -Algorithm SHA256).Hash.ToLower()
(Get-Content C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase11-visure\avviatore\versioni_approvate.json -Raw | ConvertFrom-Json).versioni | Format-Table versione, sha256
.\EuGEnioVisure.exe --non-aggiornare --stato
```
Le tre impronte devono coincidere con `3fc84c6ae60536a1554ef6af225cd0ff57eea3c4cbda83171a296f5410a80851`:
- quella del pacchetto, per intero;
- quella dell'elenco, per intero;
- quella che `--stato` mostra, per i primi 16 caratteri.

Il workflow e lo script fanno lo stesso controllo e si fermano se non torna.

**54. Se l'impronta cambia.** Il pacchetto è riproducibile: stessi file, stesso zip, byte per byte, anche con gli «a
capo» di Windows. Se l'impronta cambia, sono cambiati i file di `fase11-visure\visure\` (`.py`, `.toml`) o
`fase10-edifici3d\edifici3d\importa.py` o `__init__.py`.
1. **[PC]** Guarda cosa è cambiato rispetto al commit:
   ```powershell
   cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
   git status fase11-visure fase10-edifici3d/edifici3d
   git diff --stat HEAD -- fase11-visure/visure fase10-edifici3d/edifici3d
   ```
   Se ci sono modifiche che non volevi (estrazione incompleta, un file aperto e salvato), ripristina con
   `git checkout -- <file>` e ricostruisci.
2. Se il cambiamento è voluto e la 0.1.0 **non è mai stata pubblicata** (nessun tag `visure-v0.1.0`, ed è il caso di
   oggi), aggiorna l'elenco:
   ```powershell
   cd fase11-visure
   .\.venv\Scripts\python avviatore\costruisci_pacchetto.py --aggiorna-elenco
   cd ..
   git add fase11-visure/avviatore/versioni_approvate.json
   git commit -m "EuGEnio Visure: impronta del pacchetto 0.1.0 aggiornata"
   git push
   ```
   Poi rifai il passo 13, oppure il 51, e i controlli. L'.exe va ricostruito: contiene l'elenco incorporato.
3. Se la versione è **già stata pubblicata** con un tag, non riusare lo stesso numero. Alza `VERSIONE` in
   `fase11-visure\visure\__init__.py` (es. `0.1.1`), poi `--aggiorna-elenco`, commit, push e un tag nuovo. `--revoca`
   serve solo se proprio devi tenere lo stesso numero.
4. Un `.exe` il cui `--stato` mostra un'impronta diversa dall'elenco **non va distribuito**.

Cosa fare se va male:
- **L'.exe si chiude subito**: da PowerShell lancia `.\EuGEnioVisure.exe --stato` e mandami le righe. Il registro è in
  `%LOCALAPPDATA%\EuGEnio\Visure\avviatore.log`;
- **«nessuna geometria leggibile negli elementi dell'IFC (primo errore: …)»**: mandami la riga intera.

---

## Rinviato

- **Modulo UNI privato sul server**:
  - estrazione di `eugenio_uni_privato_2026-11-04.zip` sul PC;
  - `scp -r fase10-edifici3d\uni_privato eugenio:/srv/energia/dati/`;
  - `sudo setfacl -R -m u:1000:rX /srv/energia/dati/uni_privato`;
  - `docker compose restart api`.
  
  Dopo, `/api/analisi/stato` dirà `"modulo":true` (le analisi restano non disponibili finché le tabelle sono vuote).
  Prima vanno compilate le tabelle (`AGGIORNAMENTO_2026-11-04.md`, Fase E, FE-A1, FE-A3 ultima riga, FE-B1).
- **Prove con DXF e IFC veri**, da CAD e da Revit/ArchiCAD: nella pagina Importa DXF/IFC e con
  `EuGEnioVisure.exe modello … --grande` per un file grande. Mandami il numero di corpi, i tetti e gli avvisi.
- **Release dell'.exe**, dopo le visure vere anonimizzate: `git tag visure-v0.1.0` e
  `git push origin visure-v0.1.0`. Firma con SignPath: `fase11-visure/README.md`, «Firma dell'.exe».
- **Dati veri della Fase A**: UVL e DTM 5 m dal Geoportale ER, URL in `fonti/emilia_romagna.toml`, `prepara` su Rimini
  (`AGGIORNAMENTO_2026-11-03.md`, «Dati veri»). Finché manca, la pipeline resta «in attesa».
- **Risposta a Zornade (§ 14.2)**: resta aperta per decisione di Paolo del 04/11/2026. Prima si valuta se i dati di
  Zornade servono davvero.
- **Articolo** su Substack, dopo questa pubblicazione (`documenti/ARTICOLO_EDIFICI_3D_bozza.md`).

## Incoerenze trovate nei due AGGIORNAMENTO e come sono state risolte qui

1. **Versione del sito.** Le sezioni dicono `20261103a` (03/11), `20261104a` (Previsioni, B, C, D, E), `20261104b`
   (Importa DXF/IFC) e `20261104c` (menu fissabile e la nota in cima).
   - Qui una sola versione, **`20261104c`**, verificata con `costruisci_pagine.py --controlla`.
   - I `grep` dei controlli cercano `20261104c`.
2. **Copia dei file sul server.** Gli elenchi di `scp` sono parziali e si ripetono:
   - `app.py`, `protezione.py` e `report_servizi.py` compaiono in tre o quattro sezioni;
   - alla Fase B mancano `docker-compose.yml` e `api/requirements.txt`, che aggiunge FC-A1;
   - `scp -r fase10-edifici3d` compare quattro volte e copierebbe anche un eventuale `.venv` o `uni_privato` del PC.
   
   Qui c'è **un solo pacchetto del codice**, come il 28/10, con le esclusioni e un controllo.
3. **Rebuild ripetuti.** L'api si ricostruiva quattro volte (03/11 passo 8, B2, FC-C3, FE-B2) e `edifici-lidar` due
   volte. Caddy si riavviava con `up -d` (03/11) o con `--force-recreate` (04/11).
   - Qui un solo rebuild dell'api, dopo tutto il codice, e una sola build della pipeline.
   - Caddy sempre con `--force-recreate`, perché il Caddyfile è un singolo file montato.
4. **`.env`.** Le righe erano sparse in tre passi (03/11 B1, B1, FC-C1). Qui c'è un solo passo, con un controllo che
   stampa solo conteggi. `ORTOFOTO_SPENTE` resta vuota per la decisione del 04/11 (la Fase B la presentava ancora come
   scelta).
5. **Cartelle dei dati.** Erano in tre passi diversi, e FC-C2 usava `setfacl` senza `sudo` e `rwx`, mentre il README
   della fase 4 usa `sudo` e `rwX`. Qui c'è un solo passo, con `sudo setfacl … rwX` come nel README.
6. **TOML delle ortofoto attesi.** B3 ne elencava 3, FE-B3 ne elenca 5. Qui sono 5: si aggiungono Bolzano e Trento.
7. **Stato delle analisi.** FE-B3 si aspettava `"modulo":true`. Con il modulo UNI rinviato è `"modulo":false`.
8. **Numero dei test, verificati il 04/11/2026.**

   | Fase | Scritto nelle sezioni | Corretto |
   |---|---|---|
   | 11 | 67 (FD-A2) | 71 |
   | 5 | 9 (03/11), 13 (Fase E) | 14 |
   | 10 | 56 (FE-A2) | 68 |
   | 4 | 150 | 150 |
9. **File di prova DXF/IFC.** IM-C1 usa `fase10-edifici3d\.venv`, che sul PC può non esistere. Qui si usa l'ambiente
   della fase 11, che ha ezdxf e IfcOpenShell (`requirements-dev.txt` include `requirements-modelli.txt`). Il `pip
   install` va rifatto anche se l'ambiente esiste.
10. **Commit.** C'erano cinque commit e cinque push (03/11 D, Fase B E, FD-F, FE-D, IM-E), e IM-E non aveva il `cd`.
    Qui c'è un solo commit, prima della pubblicazione.
11. **Avvio del workflow.** FD-D1 e IM-D1 dicevano «dopo il push» come se il push lo avviasse. Il workflow parte solo
    con un tag `visure-v…`, con una pull request o con **Run workflow**. Qui si avvia a mano (passo 13).
12. **Cron.** FC-C5 usava `~` e non aveva `-T`. Qui ci sono il percorso assoluto `/home/ubuntu/…`, come le altre righe
    del README della fase 4, e `-T`, per sicurezza, perché nel cron non c'è un terminale. C'è anche un controllo per
    non aggiungere la riga due volte.
13. **Controllo del WebAssembly.** Si aggiungono `HTTP` e `content-length` e la variante `curl.exe` per PowerShell (lì
    `curl` è un alias di `Invoke-WebRequest`).
14. **Controlli in più**, che non erano nelle sezioni:
    - Caddy rifiuta `/api/interno/` senza l'intestazione di Access (passo 31, riga 12);
    - Access copre i due percorsi visti dall'esterno (passo 33);
    - verifica dell'impronta con `--stato` (passo 53).
