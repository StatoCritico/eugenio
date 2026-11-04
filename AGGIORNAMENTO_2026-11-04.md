# Meteo di tutta Italia sul server – 4/11/2026

Situazione di partenza (verificata il 4/11/2026 alle 0:05):
- download da S3 **finito il 30/10/2026 alle 11:35**: ERA5 e ICON per tutti i 7.896 comuni (`/srv/lavoro/archivio`, 45 GB);
- correzione ERA5 → ICON **già fatta** (`era5_corretto` 7.896/7.896; temperatura: errore da 1,72 a 1,41 °C);
- esportazione **mai completata**: in `/srv/lavoro/pacchetto` c'è solo la cartella `orario`.

Cosa cambia nel codice (sul PC dal 4/11/2026, 3 test nuovi in `fase4-server/tests/test_meteo_nazionale.py`):
- `esporta` scrive `giornaliero.parquet` a blocchi di 25 comuni: per tutta Italia sono ~34 milioni di righe, che
  scritte in una volta sola avrebbero esaurito la memoria;
- l'api legge **solo il blocco del comune richiesto** (0,04 s) invece di caricare tutto il file;
- l'aggiornamento giornaliero del worker riscrive il file un blocco alla volta (~300 MB di memoria al massimo);
- due impostazioni nel `.env`: `REGIONI` = regioni **servite** (vuoto = tutta Italia) e `REGIONI_AGGIORNATE` = regioni il
  cui meteo recente e le cui previsioni si aggiornano ogni giorno con l'API gratuita (resta `08`: per tutta Italia
  servirebbero più delle 10.000 chiamate al giorno concesse).

Risultato: **Legge 10, Dati climatici e storico meteo per tutti i comuni d'Italia**; meteo recente e previsioni
aggiornati ogni giorno per l'Emilia-Romagna. Per gli altri comuni la previsione dei consumi usa lo storico fino a fine
ottobre e poi la climatologia (lo dice la colonna «fonte» dei risultati).

Tempo: ~15 minuti di comandi, più ~30–60 minuti di esportazione che va da sola.

---

## A. Sul PC: pacchetto del codice

**1. Apri PowerShell** e vai nella cartella del codice:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```

**2. Prepara il pacchetto del codice** (senza fase 2, `.venv` e `.env`):
```powershell
tar -czf ..\codice.tar.gz --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico
dir ..\codice.tar.gz
```
Il file deve essere di **meno di 1 MB**. Se è molto più grande, è entrata una `.venv`: fermati e dimmelo.

**3. Copialo sul server:**
```powershell
scp ..\codice.tar.gz eugenio:~/
```
Compare una riga con `100%`.

## B. Sul server: codice nuovo

**4. Entra nel server:** `ssh eugenio`.

**5. Copia di sicurezza del codice di oggi:**
```bash
cp -a ~/energia ~/energia_prima_20261104
```

**6. Codice nuovo** (il `.env` resta quello del server):
```bash
tar -xzmf ~/codice.tar.gz -C ~/energia && ls -l ~/energia/fase4-server/.env
```
L'ultima riga deve mostrare `-rw-------` e `.env`.

**7. Ricostruisci l'immagine** (api e worker usano la stessa; ~3–5 minuti):
```bash
cd ~/energia/fase4-server && docker compose build api
docker compose run --rm --no-deps -T worker grep -c COMUNI_PER_BLOCCO /app/meteo_storico/aggrega.py
```
L'ultimo comando deve stampare un numero maggiore di 0.

## C. Sul server: esportazione del meteo (va da sola, ~30–60 minuti)

**8. Prepara la cartella del pacchetto** (quella vecchia è incompleta):
```bash
sudo rm -rf /srv/lavoro/pacchetto && sudo mkdir /srv/lavoro/pacchetto && sudo chown 1000:1000 /srv/lavoro/pacchetto
```
Nessun messaggio = tutto bene.

**9. Lancia l'esportazione nella sessione `tmux`** (così continua anche se la connessione cade):
```bash
tmux new -s esporta
```
e dentro:
```bash
cd ~/energia/fase4-server
docker compose run --rm --no-deps -T -v /srv/lavoro/archivio:/archivio -v /srv/lavoro/pacchetto:/pacchetto worker \
  python -m meteo_storico esporta --archivio /archivio --regioni tutte --dest /pacchetto 2>&1 | tee ~/esporta.log
```
Ogni pochi minuti compare una riga `esportazione: 500/7896 comuni`, poi 1000, 1500… Staccati con **Ctrl+B** e poi **D**.
Per rientrare: `tmux attach -t esporta`.

**10. Quando ha finito**, l'ultima riga del registro dice `Esportati 7896 comuni (… righe giornaliere) in /pacchetto`:
```bash
tail -3 ~/esporta.log
ls /srv/lavoro/pacchetto
ls /srv/lavoro/pacchetto/orario | wc -l
du -sh /srv/lavoro/pacchetto
```
Devono comparire `comuni.json`, `comuni.parquet`, `giornaliero.parquet`, `metriche.json`, `parametri_correzione.parquet`,
`orario`, `LEGGIMI.txt`; il conteggio della cartella `orario` deve essere **7896**. Chiudi la sessione `tmux` con
`tmux kill-session -t esporta`.

## D. Sul server: dati al loro posto e impostazioni

**11. Copia di sicurezza dei comuni di oggi**, poi copia del pacchetto nella cartella dati (qualche minuto, ~4–5 GB):
```bash
cp /srv/energia/dati/comuni.json /srv/energia/dati/comuni_prima_20261104.json
cp /srv/energia/dati/comuni.parquet /srv/energia/dati/comuni_prima_20261104.parquet
cp -r /srv/lavoro/pacchetto/. /srv/energia/dati/
sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX /srv/energia/dati/orario /srv/energia/dati/giornaliero.parquet /srv/energia/dati/parametri_correzione.parquet
ls -l /srv/energia/dati/giornaliero.parquet
```
L'ultimo comando mostra il file (qualche centinaio di MB).

**12. Regioni servite e aggiornate.** Tutta Italia servita, aggiornamenti quotidiani per la sola Emilia-Romagna:
```bash
sed -i 's/^REGIONI=.*/REGIONI=/' ~/energia/fase4-server/.env
grep -q "^REGIONI_AGGIORNATE=" ~/energia/fase4-server/.env || echo "REGIONI_AGGIORNATE=08" >> ~/energia/fase4-server/.env
grep -E "^REGIONI" ~/energia/fase4-server/.env
```
Devono comparire esattamente due righe: `REGIONI=` (vuoto) e `REGIONI_AGGIORNATE=08`.

**13. Riavvia l'api** con il codice e le impostazioni nuove:
```bash
cd ~/energia/fase4-server && docker compose up -d --force-recreate api && sleep 40 && docker compose ps api
```
Deve risultare `Up` (anche `health: starting` va bene per un minuto).

## E. Prove

**14. Dal server**, Legge 10 per Bologna (Emilia-Romagna) e per Roma (Lazio):
```bash
curl -s https://eugenio.statocritico.it/api/clima-legge10/037006 | head -c 200; echo
curl -s https://eugenio.statocritico.it/api/clima-legge10/058091 | head -c 200; echo
docker stats --no-stream fase4-server-api-1
```
Le prime due righe devono iniziare con `{"` e contenere dei numeri, **non** «non sono ancora sul server». Nell'ultima la
memoria dell'api (`MEM USAGE`) deve restare ben sotto i 6 GB.

**15. Nel browser** (Ctrl+F5):
- **Legge 10**: un comune dell'Emilia-Romagna e uno di un'altra regione (freccia ↓ della piccola mappa, poi la regione):
  la parte calcolata dal server compare in entrambi;
- **Dati climatici**: scarica qualche mese del meteo giornaliero di un comune fuori dall'Emilia-Romagna;
- **Previsioni**: il file d'esempio su un comune dell'Emilia-Romagna.

## F. Sul server: worker acceso, cron svuotato

**16. Togli i lavori dal cron dell'host** (da ora li fa il worker: mercati ogni notte, indicatori il 5, clima il 10/1 e
il 10/7). Prima guarda cosa c'è:
```bash
crontab -l
```
Se ci sono solo le tre righe di mercati, indicatori e clima, cancellale tutte:
```bash
crontab -r; crontab -l
```
Deve rispondere `no crontab for ubuntu`.

**17. Accendi il worker:**
```bash
cd ~/energia/fase4-server && docker compose up -d worker && docker compose ps
```
`worker` deve risultare `Up`. Segui il registro per qualche minuto (Ctrl+C per uscire, il worker continua):
```bash
docker compose logs -f worker
```
Dopo qualche minuto deve comparire `Previsioni aggiornate: 330 comuni, fino a …` (i comuni dell'Emilia-Romagna).

**18. Pulizia:** `rm ~/codice.tar.gz`, poi `exit`. Tieni per qualche giorno `~/energia_prima_20261104` e i file
`comuni_prima_20261104.*`; poi cancellali.

## Se qualcosa va storto

- **L'esportazione si ferma con un errore**: `tail -30 ~/esporta.log` e mandami le righe.
- **L'api non riparte** o la Legge 10 risponde 500: `docker compose logs --tail 60 api`. Per tornare indietro:
  `cd ~ && rm -rf ~/energia && mv ~/energia_prima_20261104 ~/energia && cd ~/energia/fase4-server && docker compose up -d --build api`
  e, nel `.env`, `REGIONI=08`.
- **Il worker non parte**: `docker compose logs --tail 60 worker`; per spegnerlo `docker compose stop worker` e rimettere
  le righe del cron (README della fase 4).

## Dopo

- Il disco di lavoro `/srv/lavoro` (100 GB, archivio di 45 GB) non serve più al sito: tenerlo finché tutto è verificato,
  poi decidere se staccarlo (si perde l'archivio orario, ricostruibile da S3 in ~2 giorni) o tenerlo per ricalcoli.
- Aggiornamento quotidiano da S3 anche per le altre regioni (storico recente e previsioni), al posto dell'API gratuita.
