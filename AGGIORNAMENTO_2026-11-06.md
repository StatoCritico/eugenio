# Aggiornamento del 06/11/2026 – file per gli agenti AI

Richiesta di Paolo: «aggiungi un file md che spiega tutte le funzioni di eugenio per gli agenti AI, perché lo possano usare
automaticamente, aggiungilo alla cartella del progetto, al sito e al repo github. Nel sito linkalo nella pagina FAQ e nel
paragrafo che parla di Claude che non è open source aggiungi la frase…». Poi: il file va tenuto aggiornato con ogni novità
(regola permanente).

## Cosa cambia

- **`EUGENIO_PER_AGENTI.md`** nella radice del repository (GitHub) e, identico, in `fase5-sito/sito/` (sito). Ricavato dal
  codice (rotte FastAPI, pagine, parametri dell'indirizzo, protezione, privacy, fonti): cos'è, licenze e attribuzioni,
  mappa del menu pagina per pagina con parametri, ingressi, uscite e stato, API libere e protette da Turnstile con esempi
  curl, codici d'errore, limiti, uso cortese, flussi tipici, cosa EuGEnio non fa, privacy funzione per funzione, file statici,
  contatti, fonti nel repository da cui è ricavato. In testa «Ultimo aggiornamento» con data e versione e la regola di
  manutenzione. Niente segreti, dati GME/EEX, contenuti UNI o GSE; la fase 2 non è nominata.
- **`fase5-sito/sito/llms.txt`** (convenzione llms.txt): descrizione breve e rimando al file.
- **F.A.Q.**: voce nuova `#agenti-ai` «Posso far usare EuGEnio al mio assistente di intelligenza artificiale?», con il
  collegamento che scarica il file (`download`), l'indirizzo da dare all'assistente e il rimando a `llms.txt`.
- **Sitografia** `#claude`, nel paragrafo «No, scherzavamo: non è open source…», la frase di Paolo: «E lo puoi usare anche
  tu: per fargli imparare cosa può fare EuGEnio, scarica e fagli leggere **questo file**.» (collegamento su «questo file»,
  con `download`).
- **Caddyfile** (fase 4): i `.md` del sito escono come `text/markdown; charset=utf-8`, `/llms.txt` come
  `text/plain; charset=utf-8` (provato con Caddy 2.10.2 sul Caddyfile vero). Caddy va **ricreato** (`--force-recreate`).
- `stile.css`: `.articolo p code` va a capo dentro le parole (indirizzo lungo nella F.A.Q. sul telefono).
- **Test**: `fase4-server/tests/test_agenti.py` (5: copie identiche, versione e regola in testa, niente segreti, ogni
  percorso `/api/…` citato esiste nell'app, ogni rotta pubblica dell'app è citata; escluse `/api/interno/…`);
  `fase5-sito/tests/test_agenti_sito.py` (5, di cui 2 in Chromium: ancora `#agenti-ai`, download dalla F.A.Q. e dalla
  Sitografia a 1366 e 375 px, file scaricato identico, niente scorrimento orizzontale, nessun errore). Fase 5: **43 passed**;
  fase 4: **172 passed** (eseguiti nel container).
- Sito **`?v=20261106a`**, che sostituisce `?v=20261105b` (anche `interno/edifici.html`, a mano).
- **Regola permanente** (RIEPILOGO, README generale e della fase 5): dopo ogni modifica alle funzioni, alle pagine o alle
  API, aggiornare anche `EUGENIO_PER_AGENTI.md` (radice e sito) e `llms.txt`, con data e versione del sito.

Non toccati: `fase11-visure/visure/`, `fase10-edifici3d/edifici3d/__init__.py` e `importa.py`; nessun rebuild dell'api o
del worker.

## Procedura breve (online c'è `?v=20261105b`, commit del 05/11 già spinto)

1. **[PC]** Clone pulito e allineato; estrai `eugenio_2026-11-06.zip` sopra il clone; controlli (E1–E2).
2. **[PC]** Pagine e test della fase 5; segreti fuori da git; le due copie del file identiche (E3–E4).
3. **[PC]** Pacchetto del sito e copia sul server di sito e Caddyfile (E5).
4. **[Server]** Copia di sicurezza del Caddyfile, Caddyfile nuovo, sito nuovo, `docker compose up -d --force-recreate caddy`,
   controllo dei tipi (E6–E8).
5. **[Browser]** F.A.Q., Sitografia, file `.md` e `llms.txt` (E9).
6. **[PC]** Commit e push (E10).

## Procedura dettagliata E1–E10

Etichette: **[PC]** PowerShell sul PC, **[Server]** terminale sul server (`ssh eugenio`), **[Browser]**. Da casa o da rete
mobile (la rete aziendale blocca statocritico.it). Comandi da incollare così come sono; nessun valore segreto.

### Parte 1 – PC: zip e controlli

**E1. [PC]** Entra nel clone e guarda lo stato:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
git fetch
git status -sb | Select-Object -First 1
git status --short | Measure-Object
```
Cosa aspettarsi: `## main...origin/main` **senza** `[behind …]`; `Count : 0` (il commit D17 del 05/11 è già fatto).

Cosa fare se va male: con `[behind N]` fermati e mandami `git log --oneline origin/main -3`; con `Count` maggiore di 0
mandami `git status --short`.

**E2. [PC]** Estrai lo zip sopra il clone e controlla:
```powershell
dir ..\eugenio_2026-11-06.zip
Expand-Archive -Path ..\eugenio_2026-11-06.zip -DestinationPath . -Force
Select-String -Path fase5-sito\sito\index.html -Pattern "20261106a" -List | Measure-Object
git status --short | Select-String -Pattern "^\?\?"
git status --short fase11-visure fase10-edifici3d
```
Cosa aspettarsi: lo zip ha l'ora di stasera; `Count : 1`; i file nuovi (`??`) sono sei: `AGGIORNAMENTO_2026-11-06.md`,
`EUGENIO_PER_AGENTI.md`, `fase4-server/tests/test_agenti.py`, `fase5-sito/sito/EUGENIO_PER_AGENTI.md`,
`fase5-sito/sito/llms.txt`, `fase5-sito/tests/test_agenti_sito.py`; l'ultimo comando **non stampa nulla**.

Cosa fare se va male: `Count : 0` = zip vecchio (rifai `dir`); righe di `fase11-visure` o `fase10-edifici3d`: fermati e
mandamele.

**E3. [PC]** Pagine e test della fase 5:
```powershell
cd fase5-sito
python costruisci_pagine.py --controlla
python -m pytest -q tests
cd ..
```
Cosa aspettarsi: `versione 20261106a: 0 file da rigenerare`; poi `43 passed` (senza Playwright e Chromium sul PC `32 passed,
11 skipped` va bene). I 172 test della fase 4 li ho eseguiti io.

**E4. [PC]** Segreti fuori da git e copie identiche:
```powershell
git check-ignore -v fase2-gradi-giorno/README.md fase10-edifici3d/uni_privato/__init__.py fase4-server/.env iscrizioni/x
git ls-files fase2-gradi-giorno fase10-edifici3d/uni_privato
fc.exe /b EUGENIO_PER_AGENTI.md fase5-sito\sito\EUGENIO_PER_AGENTI.md
Select-String -Path EUGENIO_PER_AGENTI.md -Pattern "TURNSTILE_SECRET|ZORNADE_API_KEY|TUNNEL_TOKEN|fase2|uni_privato" | Measure-Object
```
Cosa aspettarsi: quattro righe `.gitignore:…`; dal secondo comando nessuna riga; `FC: nessuna differenza riscontrata`;
`Count : 0`.

### Parte 2 – PC: pacchetto e copia

**E5. [PC]** Pacchetto del sito `?v=20261106a` e copia sul server insieme al Caddyfile:
```powershell
cd fase5-sito
tar -czf ..\..\sito.tar.gz --exclude=dati/indicatori --exclude=./dati/indicatori -C sito .
cd ..
tar -tzf ..\sito.tar.gz | Select-String -Pattern "EUGENIO_PER_AGENTI|llms"
scp ..\sito.tar.gz fase4-server\Caddyfile eugenio:~/
```
Cosa aspettarsi: due righe (`./EUGENIO_PER_AGENTI.md`, `./llms.txt`); poi due righe con `100%`.

### Parte 3 – Server

**E6. [Server]** Copia di sicurezza e Caddyfile nuovo, controllato prima di usarlo:
```bash
cd ~/energia/fase4-server
cp Caddyfile ~/Caddyfile_prima_20261106a
docker run --rm -v ~/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -1
cp ~/Caddyfile Caddyfile && grep -c "text/markdown" Caddyfile
```
Cosa aspettarsi: `Valid configuration`; poi `1`.

Cosa fare se va male: se non dice `Valid configuration` **non** fare il `cp` e mandami l'uscita.

**E7. [Server]** Sito nuovo:
```bash
tar -xzmf ~/sito.tar.gz --no-overwrite-dir -C /srv/energia/sito && grep -c 20261106a /srv/energia/sito/index.html /srv/energia/sito/faq.html /srv/energia/sito/interno/edifici.html
ls -l /srv/energia/sito/EUGENIO_PER_AGENTI.md /srv/energia/sito/llms.txt
grep -c 'id="agenti-ai"' /srv/energia/sito/faq.html
```
Cosa aspettarsi: tre righe `…:N` con N maggiore di 0; i due file (circa 43 kB e 2 kB); `1`.

**E8. [Server]** Caddy ricreato (legge il Caddyfile nuovo) e tipi dei file:
```bash
docker compose up -d --force-recreate caddy
docker compose ps caddy
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://caddy/EUGENIO_PER_AGENTI.md'); print(r.status, r.headers['Content-Type'])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://caddy/llms.txt'); print(r.status, r.headers['Content-Type'])"
docker compose exec -T api python -c "import urllib.request as u; r=u.urlopen('http://caddy/faq.html'); print(r.status, r.headers['Content-Type'])"
rm ~/sito.tar.gz ~/Caddyfile
exit
```
Cosa aspettarsi: `caddy` `Up` da pochi secondi; poi `200 text/markdown; charset=utf-8`, `200 text/plain; charset=utf-8`,
`200 text/html; charset=utf-8`.

Cosa fare se va male: caddy non parte o il sito non risponde → torna indietro con
`cd ~/energia/fase4-server && cp ~/Caddyfile_prima_20261106a Caddyfile && docker compose up -d --force-recreate caddy` e
mandami `docker compose logs --tail 30 caddy`. Tieni `~/Caddyfile_prima_20261106a` qualche giorno.

### Parte 4 – Prove nel browser (Ctrl+F5)

**E9. [Browser]**
1. `https://eugenio.statocritico.it/faq.html#agenti-ai`: la voce «Posso far usare EuGEnio al mio assistente di
   intelligenza artificiale?» è aperta; il clic su `EUGENIO_PER_AGENTI.md` **scarica** il file (circa 43 kB). Aprilo con
   il Blocco note: lettere accentate giuste, in testa «Ultimo aggiornamento: 06/11/2026 – versione del sito `?v=20261106a`».
2. `https://eugenio.statocritico.it/sitografia.html#claude`: sotto «Claude, di Anthropic» c'è «… E lo puoi usare anche tu:
   per fargli imparare cosa può fare EuGEnio, scarica e fagli leggere questo file.»; il clic su «questo file» lo scarica.
3. `https://eugenio.statocritico.it/EUGENIO_PER_AGENTI.md` scritto nella barra: il testo si vede (o si scarica, secondo il
   browser) con gli accenti giusti; F12 → Rete → la richiesta ha `Content-Type: text/markdown; charset=utf-8`.
4. `https://eugenio.statocritico.it/llms.txt`: testo leggibile con il rimando al file.
5. Sul telefono: la voce della F.A.Q. non fa scorrere la pagina in orizzontale.
6. Facoltativo: chiedi a Claude «leggi https://eugenio.statocritico.it/llms.txt e dimmi come scaricare i gradi giorno di
   Rimini da EuGEnio».

Cosa fare se va male: pagina vecchia = Ctrl+F5 o Cloudflare **Caching → Configuration → Purge Everything** (Cloudflare tiene
in copia i `.txt`; i `.md` non li mette in copia).

### Parte 5 – Commit e push

**E10. [PC]** Nel clone:
```powershell
git add -A
git status --short | Select-String -Pattern "fase2-gradi-giorno|uni_privato|(^|/)\.env$|iscrizioni|visure_vere|intestatari_DATI_PERSONALI|edifici_rimini_prova"
git commit -m "06/11/2026: EUGENIO_PER_AGENTI.md per gli agenti AI (radice e sito) e llms.txt; F.A.Q. #agenti-ai; frase in Sitografia #claude; Caddy con text/markdown per i .md; test delle rotte citate; sito ?v=20261106a"
git push
git log --oneline -2
```
Cosa aspettarsi: il secondo comando **non stampa nulla**; il push finisce con `… main -> main`; su GitHub il file
`EUGENIO_PER_AGENTI.md` compare nella pagina principale del repository, tra i file della radice.

Cosa fare se va male: file da escludere nell'elenco → `git restore --staged <percorso>` e dimmelo; push rifiutato →
`git pull --rebase` e di nuovo `git push`.
