# Aggiornamento del 14–15/11/2026 – Newsletter e avvisi: mensile per regione, previsioni settimanali, avvisi meteo

Sito **`?v=20261114a`**, release **`v2026.11.14`**. Contiene anche i file del 12/11 (`aggiorna_da_github.sh`), se il
loro commit (X3) non è ancora stato fatto: un solo commit per tutti e due.

## Cosa cambia

**Decisioni di Paolo del 14/11/2026**
1. Tre servizi **separati**, ognuno con la sua iscrizione:
   - **newsletter mensile** (il 12): indicatori **per regione** e valori nazionali degli indicatori economici;
   - **previsioni settimanali**: il tempo della settimana dopo per **fino a 5 comuni** scelti da ogni utente;
   - **avvisi meteo** (non allerte): domani **pioggia forte**, **neve** o **vento molto forte** sopra soglie ragionevoli.
2. Soglie scelte da Claude (si cambiano nel `.env`): pioggia forte **≥ 40 mm in 24 ore o ≥ 15 mm in un'ora**; neve
   **≥ 2 cm** di neve fresca; vento molto forte **raffiche ≥ 75 km/h** (burrasca forte).
3. Ovunque (pagina, email, F.A.Q.): «Il servizio di avvisi meteo è gratuito, non fornisce garanzie e non sostituisce le
   allerte della Protezione Civile e degli enti pubblici».

**Decisione di Paolo del 15/11/2026**: «Iscriviti» si sposta dentro **Clima e meteo** e si chiama **«Newsletter e
avvisi»** (ultima voce del gruppo, dopo Cambiamento climatico); tolto il pulsante della testata e la voce del menu del
telefono. La pagina resta `dati-per-email.html` (gli indirizzi già spediti funzionano).

**Sitografia (Paolo, 15/11/2026)**: in «Energia» accanto a FIRE e SECEM anche **ANIT**, **AiCARR** e **SIAIS**; in «Dati
sanitari e sugli enti pubblici» anche **AGENAS** e **ANCI**.

**Scelte fatte da Claude** (dette a Paolo il 14/11, si cambiano nel `.env` o con una richiesta):
- mensile: fino a **3 regioni**; tabella di tutte le regioni (media dei capoluoghi di provincia) per tutti, capoluoghi uno
  per uno per le regioni scelte, Consip con i **lotti delle regioni scelte**; senza regioni scelte la sola tabella;
- settimanale: la **domenica dalle 17**, da lunedì a domenica; avvisi: **ogni giorno dalle 15** per domani;
- previsioni dei servizi email da Open-Meteo con la scelta automatica del modello per ogni punto (servono raffiche e
  neve), solo per i comuni scelti, anche fuori dall'Emilia-Romagna;
- niente password: **collegamento personale** per email, valido 7 giorni; le liste nuove sono private (si gestiscono
  solo dalla pagina) e si creano da sole in listmonk;
- un messaggio per iscritto (API transazionale di listmonk), con «Cambia servizi, regioni e comuni» e «Cancellati con un
  clic» in fondo; il mensile del 12/12 sarà il primo così, anche per gli iscritti di oggi.

**File**: fase 4 `servizio/preferenze_email.py`, `servizio/listmonk.py`, `servizio/meteo_email.py` (nuovi),
`servizio/notiziario.py`, `servizio/worker.py`, `servizio/meteo.py` (storico anche dei capoluoghi di tutte le regioni),
`servizio/config.py`, `servizio/avvisi.py`, `servizio/protezione.py`, `servizio/app.py`, `api/requirements.txt`
(`markdown`), `.env.example`, `tests/test_email_personali.py`, README; fase 5 `sito/dati-per-email.html`,
`sito/dati_per_email.js` (nuovi), `parti/testata.html` (15/11: voce «Newsletter e avvisi» in Clima e meteo, tolto «Iscriviti»), `sito/protezione.js`, `stile.css`,
`faq.html`, `privacy.html`, `novita.toml`, tutte le pagine a `?v=20261114a`, `tests/test_dati_per_email_browser.py`,
README; `EUGENIO_PER_AGENTI.md` (due copie), `llms.txt`. Test: fase 4 **248 passati** (2 saltati); fase 5 con Chrome
**126 passati** (1 saltato).

## Procedura Y (circa 40 minuti, da fare quando le altre chat hanno finito)

Altre chat stanno lavorando sugli stessi file. Questa procedura parte **dopo**: un solo commit e una sola release con
tutto quello che c'è nella cartella, poi il server si aggiorna da GitHub con lo script.

### Y0. [Claude] Controllo d'insieme prima del commit
Scrivimi «le altre chat hanno finito». Controllo io nella cartella del PC, senza cambiare il lavoro degli altri:
- che i miei file siano ancora quelli provati (impronte in `..\md5_1114.txt`, aggiornate il 15/11);
- che ci sia **una sola versione del sito** (`?v=`): se un'altra chat ne ha messa una, rigenero le pagine con la più
  recente e unisco le voci di `fase5-sito/novita.toml` (la prima voce deve avere quella versione);
- `costruisci_pagine.py --controlla`, i test delle fasi 4 e 5 e `EUGENIO_PER_AGENTI.md` uguale nelle due copie;
- l'elenco dei file del commit e il messaggio, da incollare in Y2.

Cosa aspettarsi: un mio messaggio «pronto per Y1» con il messaggio del commit e il titolo della release.

### Y1. [PC] Controllo dei file
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
git status --short | Select-String -Pattern "^\?\?"
```
Cosa aspettarsi: tra le righe `??` almeno `AGGIORNAMENTO_2026-11-12.md`, `AGGIORNAMENTO_2026-11-14.md`,
`fase4-server/aggiorna_da_github.sh`, `fase4-server/servizio/listmonk.py`, `fase4-server/servizio/meteo_email.py`,
`fase4-server/servizio/preferenze_email.py`, `fase4-server/tests/test_email_personali.py`,
`fase5-sito/sito/dati-per-email.html`, `fase5-sito/sito/dati_per_email.js`,
`fase5-sito/tests/test_dati_per_email_browser.py`, più i file nuovi delle altre chat che ti ho elencato in Y0. Righe
che non conosci → mandamele.

### Y2. [PC] Commit, push e release `v2026.11.14`
```powershell
git add -A
```
```powershell
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|\.tar\.gz$|giornaliero.*\.parquet|dati/prezzi|mercati_energia/dati|invii_email|caso_RN|piano_CHP_v5"
```
```powershell
git update-index --chmod=+x fase4-server/aggiorna_da_github.sh
```
```powershell
git commit -m "<messaggio che ti mando in Y0>"
```
```powershell
git push
```
```powershell
python -c "import tomllib; v=tomllib.load(open('fase5-sito/novita.toml','rb'))['voce'][0]; g={'nuovo':'Nuovo','migliorato':'Migliorato','verificato':'Verificato'}; t=[v['titolo'],'','https://eugenio.statocritico.it/novita.html','']; [t.extend(['### '+g[k]]+['- '+x for x in v[k]]+['']) for k in g if v.get(k)]; open('../note_release_1114.md','w',encoding='utf-8').write(chr(10).join(t))"
```
```powershell
gh release create v2026.11.14 --target main --title "EuGEnio – Newsletter e avvisi" --notes-file ..\note_release_1114.md
```
Cosa aspettarsi: il secondo comando **non stampa nulla** (dati personali o di terzi fuori da git); il push finisce con
`… main -> main`; la release stampa `…/releases/tag/v2026.11.14`. Righe dal secondo comando → `git restore --staged
<percorso>` per ognuna e dimmelo. Se la release dell'altra chat ha già preso `v2026.11.14`, usa `v2026.11.14b` qui e
nei passi dopo.

### Y3. [server] Script di aggiornamento (solo la prima volta)
Se X4–X6 di `AGGIORNAMENTO_2026-11-12.md` non sono fatti, falli adesso: strumenti (`which git rsync flock curl docker`),
clone e installazione dello script, token di Cloudflare per il Purge (si può rimandare: lo script dirà «Purge: fallo a
mano»).

### Y4. [server] Chiave dei collegamenti personali
```bash
cd ~/energia/fase4-server
```
```bash
grep -q '^NOTIZIE_CHIAVE=.' .env || { sed -i '/^NOTIZIE_CHIAVE=/d' .env; echo "NOTIZIE_CHIAVE=$(openssl rand -hex 32)" >> .env; }
```
```bash
grep -c '^NOTIZIE_CHIAVE=.' .env
```
Cosa aspettarsi: `1`. La chiave non si stampa e **non va mai cambiata** (i collegamenti già spediti smetterebbero di
funzionare). Le altre impostazioni hanno già i valori giusti senza scriverle.

### Y5. [server] Aggiornamento da GitHub
```bash
~/energia/fase4-server/aggiorna_da_github.sh --prova
```
Cosa aspettarsi: `Release v2026.11.14 da installare (sito ?v=…)` con la versione detta in Y0, l'elenco delle procedure
con passi a mano (questa e quelle delle altre chat) e `Prova finita: niente è stato cambiato.`
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi (la build dura qualche minuto in più per il pacchetto nuovo): `api e worker aggiornati e funzionanti`,
`Sito aggiornato a ?v=…`, `Indici dei prezzi rifatti`, `Purge di Cloudflare: fatto` (o «fallo a mano») e
`Release v2026.11.14 installata`. Se c'è `ERRORE: … Torno alla copia di sicurezza` → mandami le ultime 30 righe di
`~/aggiorna_da_github.log`: il server è già tornato com'era. Poi fai i passi a mano delle procedure delle altre chat che
lo script ha elencato.

### Y6. [server] Prova di listmonk dal server
Scrivi il tuo indirizzo al posto di `TUA@EMAIL` (resta sul server, non mandarmelo):
```bash
docker compose exec api python -c "from servizio import listmonk as L; print(L.liste_servizi()); print(L.iscritto('TUA@EMAIL') is not None); print(L.modello_tx())"
```
Cosa aspettarsi: `{'mensile': 3, 'settimanale': <n>, 'avvisi': <m>}` (le due liste nuove create adesso), `True`, un numero
(il modello «EuGEnio – messaggio personale»). In listmonk, Liste: «EuGEnio settimanale» e «EuGEnio avvisi meteo»,
private. Un errore → mandami le ultime righe (senza il tuo indirizzo).

### Y7. [browser, finestra anonima] La pagina
1. Su `https://eugenio.statocritico.it` apri il menu **Clima e meteo**: l'ultima voce è **«Newsletter e avvisi»**; in
   alto a destra non c'è più «Iscriviti». Clic sulla voce.
2. Scrivi il tuo indirizzo → «Mandami il collegamento» → «Fatto. Se l'indirizzo è giusto…».
3. Nella posta (guarda anche lo spam) l'email «EuGEnio – il tuo collegamento per newsletter e avvisi»: apri il
   collegamento.
4. «Scelte per …»: la newsletter mensile è già spuntata (sei nella lista 3). Spunta **Emilia-Romagna**, aggiungi
   **Cesena** e altri comuni, spunta le **previsioni settimanali** e i tre **avvisi**; sotto c'è l'avvertenza.
5. «Salva le scelte» → «Salvato. Riceverai la newsletter mensile, le previsioni settimanali e gli avvisi meteo.»

In listmonk, Iscritti → il tuo indirizzo: liste «EuGEnio mensile», «EuGEnio settimanale», «EuGEnio avvisi meteo»
confermate; in Attributi `"eugenio": {"regioni": ["08"], "comuni": [...], "avvisi": [...]}`.

### Y8. [server] Prima prova degli invii (solo a te, se sei l'unico iscritto ai servizi nuovi)
```bash
docker compose run --rm worker python -m servizio.worker settimanale
```
Cosa aspettarsi: nei log `Email settimanale-<lunedì prossimo>: {'inviati': 1, …}` e nella posta «EuGEnio – previsioni
dal … al …: …» con una tabella per comune; in fondo i collegamenti per cambiare le scelte e per cancellarti. La domenica
alle 17 il worker non te la rimanda (registro degli invii).
```bash
docker compose run --rm worker python -m servizio.worker avvisi
```
Cosa aspettarsi: `Email avvisi-<domani>: {'inviati': 0, 'saltati': 1, …}` se domani non c'è niente oltre le soglie (è
normale), altrimenti l'email «EuGEnio – avviso meteo per domani: …» con «Non è un'allerta.» in cima.

### Y9. [server] Anteprima del mensile per l'Emilia-Romagna (nessun invio)
```bash
docker compose run --rm --no-deps worker python -c "import datetime as d; from servizio import notiziario as n; c=n._capoluoghi_italia(); v=n._voci_freddo(c,2026,10); print(n.testo_mensile_regioni(2026,10,d.date(2026,11,12),['08'],v,n._nomi_regioni(c))[1])"
```
Cosa aspettarsi: prezzi, «Il freddo di ottobre 2026, regione per regione» con una riga per regione e «Emilia-Romagna: i
capoluoghi». Regioni mancanti nella tabella sono normali nei primi giorni: lo storico dei capoluoghi fuori
dall'Emilia-Romagna si aggiorna ogni giorno da adesso; dal 12/12 ci saranno tutte quelle con il mese completo.

### Y10. [browser] Controlli finali
1. `https://eugenio.statocritico.it/faq.html#avvisi-meteo`: le soglie e «non sono allerte».
2. Novità mostra «Newsletter e avvisi: scegli servizi e zona».
3. Nell'email delle previsioni clicca «Cancellati con un clic»: la pagina dice «Fatto: non riceverai più le previsioni
   settimanali» con «Cambia gli altri servizi»; poi ripristinale dalla pagina, se vuoi.

## Da sapere

- Il 12/12 il mensile parte come messaggi personali a tutti gli iscritti della lista 3: chi non ha scelto regioni riceve
  la tabella delle regioni e l'invito a sceglierle. Per tornare alla campagna unica di prima: `NOTIZIE_PERSONALI=false`
  nel `.env` e `docker compose up -d --force-recreate worker` (si fermano anche settimanale e avvisi).
- Le soglie degli avvisi si cambiano nel `.env` (`AVVISO_PIOGGIA_24H_MM`, `AVVISO_PIOGGIA_1H_MM`, `AVVISO_NEVE_CM`,
  `AVVISO_VENTO_KMH`) e si applicano dopo `--force-recreate api worker`; la pagina e le email le scrivono da sole, le
  F.A.Q. vanno corrette a mano.
- Da verificare alla prima occasione: che i programmi di posta mostrino «Annulla iscrizione» (intestazione
  List-Unsubscribe dei messaggi transazionali).
