# Archivio meteo della fase 3: dal PC al server e accensione del worker

Da fare **quando il download di ICON è finito** (stato al 28/10/2026 sera: anni 2022–2025 scaricati per tutti i 330
comuni dell'Emilia-Romagna, 2026 per circa 200; il programma lavora a una raffica al giorno per il limite dell'API
gratuita, l'ultima alle 19:40 del 28/10: la fine è prevista con la raffica del 29/10 sera).

Tempo: ~30 minuti di comandi più il calcolo della correzione (qualche minuto) e la copia (~170 MB).

---

## A. Sul PC: controllare che ICON sia finito

**1. Guardare la finestra di PowerShell dove gira lo scaricamento** (`python -m meteo_storico scarica … --fonte icon`).
È finito quando è tornato il prompt (`PS C:\...>`). Alla fine il programma unisce i pezzi annuali in
`archivio\orario\icon\<istat>.parquet`. Se il prompt non è tornato, aspettare: **non** chiudere la finestra.

**2. Aprire una nuova finestra di PowerShell sul PC** e preparare l'ambiente della fase 3:
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio\fase3-storico
.\.venv\Scripts\Activate.ps1
$A = "C:\Users\ingpa\Documents\claude\pj\statocritico\meteo\archivio"
```
All'inizio del prompt compare `(.venv)`.

**3. Controllare lo stato:**
```powershell
python -m meteo_storico stato --archivio $A
```
ERA5 e ICON devono risultare completi per i 330 comuni. Se ICON non lo è, rilanciare lo scaricamento (riprende da
dove si era fermato) e tornare qui il giorno dopo:
```powershell
python -m meteo_storico scarica --archivio $A --fonte icon
```

## B. Sul PC: correzione ed esportazione

**4. Correzione ERA5 → ICON** (qualche minuto; stampa le metriche alla fine):
```powershell
python -m meteo_storico correggi --archivio $A
```
Alla fine compare un riepilogo JSON delle metriche. Mandarlo a Claude per un controllo.

**5. Pacchetto per il server:**
```powershell
python -m meteo_storico esporta --archivio $A --dest C:\Users\ingpa\Documents\claude\pj\statocritico\meteo\pacchetto_server
```
Nella cartella compaiono `giornaliero.parquet`, `parametri_correzione.parquet`, `metriche.json`, `comuni.json`,
`comuni.parquet`, la cartella `orario` con 330 file e `LEGGIMI.txt`.

**6. Archivio da copiare:**
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\meteo
tar -czf meteo_pacchetto.tar.gz -C pacchetto_server .
dir meteo_pacchetto.tar.gz
```
Il file è di circa 150–200 MB.

**7. Copia sul server:**
```powershell
scp meteo_pacchetto.tar.gz eugenio:~/
```

## C. Sul server: dati e worker

**8. Entrare nel server:** `ssh eugenio`.

**9. Estrarre il pacchetto nella cartella dati** (sovrascrive `comuni.json` e `comuni.parquet` con gli stessi file
nazionali del PC):
```bash
tar -xzmf ~/meteo_pacchetto.tar.gz -C /srv/energia/dati && ls /srv/energia/dati
```
Devono comparire anche `giornaliero.parquet`, `parametri_correzione.parquet` e `orario`.

**10. Permessi per l'utente dei container:**
```bash
sudo setfacl -R -m u:1000:rwX -m d:u:1000:rwX /srv/energia/dati/orario /srv/energia/dati/giornaliero.parquet /srv/energia/dati/parametri_correzione.parquet
```

**11. Togliere i lavori dal cron dell'host** (da ora li fa il worker: mercati ogni notte, indicatori il 5, clima il
10/1 e il 10/7). Prima guardare cosa c'è:
```bash
crontab -l
```
Se ci sono solo le tre righe di mercati, indicatori e clima, cancellarle tutte:
```bash
crontab -r && crontab -l
```
L'ultimo comando deve rispondere `no crontab for ubuntu`.

**12. Accendere il worker:**
```bash
cd ~/energia/fase4-server && docker compose up -d worker && docker compose ps
```
`worker` deve risultare `Up`. Poi seguire il registro per qualche minuto (Ctrl+C per uscire, il worker continua):
```bash
docker compose logs -f worker
```
Si vedono le prime previsioni meteo e l'aggiornamento dello storico degli ultimi giorni.

## D. Controlli

**13. Nel browser**, `https://eugenio.statocritico.it/legge10.html` con **Ctrl+F5**, scegliere un comune
dell'Emilia-Romagna: la parte che usa l'API non deve più dire che i dati meteo non sono sul server.

**14. Previsione:** nella pagina Previsione caricare il file d'esempio e lanciare una previsione.

**15. Pulizia** (solo se tutto va bene): sul server `rm ~/meteo_pacchetto.tar.gz`; sul PC il file
`meteo\meteo_pacchetto.tar.gz` si può tenere come copia di sicurezza.

## Se qualcosa va storto

- **Il worker si ferma** o il registro mostra errori: `docker compose logs --tail 80 worker` e mandare le righe a
  Claude. Per spegnerlo: `docker compose stop worker` (e rimettere le righe del cron, comandi nel README della fase 4).
- **La Legge 10 risponde ancora 503**: controllare che `/srv/energia/dati/giornaliero.parquet` esista e riavviare l'api
  con `docker compose restart api`.
