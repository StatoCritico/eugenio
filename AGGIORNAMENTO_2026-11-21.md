# Aggiornamento del 21/11/2026 – Elettricità: produzione, consumi e carichi; collegamento salvabile

Pubblicazione che riunisce il ramo `claude/2026-11-20-insieme` sopra la `v2026.11.20d`. Sito **`?v=20261121a`**, release
**`v2026.11.21`**, voce nelle Novità. Contiene anche il lavoro delle procedure `AGGIORNAMENTO_2026-11-20e.md` (dati di Terna
nel worker) e `AGGIORNAMENTO_2026-11-20f.md` (mercato del giorno prima del GME, solo uso interno): con questa release
arrivano sul server tutte e due.

## Cosa cambia per chi usa il sito

- **Statistiche › Produzione e consumi di elettricità** (sperimentale, `elettricita.html`): istogrammi per regione e per
  provincia di potenza installata, produzione, carichi e consumi per settore, obiettivi regionali 2030 (burden sharing), dati
  di Terna dal 2000. Si scarica solo l'immagine.
- **Statistiche › Carichi elettrici** (sperimentale, `carichi.html`): per zona di mercato o tutta Italia, profilo
  giornaliero minimo–massimo, curva di durata, mix per fonte al 100 %, a ore o quarti d'ora, periodo a scelta.
- **Collegamento a questa simulazione** in fondo alle pagine a scelte: si copia, si salva, si riapre con le stesse scelte.
- Numeri sempre con il punto delle migliaia; Comunità energetiche con le aree del GSE accese in partenza e riaccese quando
  si aggiunge una sede; in Emissioni e Cambiamento climatico le tabelle non allargano più la pagina sul telefono.

**I dati di Terna non sono nel repository e non si scaricano dal sito** (decisione di Paolo del 20/11): li scarica da solo
il worker sul server (`/srv/energia/dati/terna/`) e li elabora in `/srv/energia/sito/dati/elettricita/` e
`/srv/energia/sito/dati/carichi/`, che `aggiorna_da_github.sh` non tocca. Le **chiavi dell'API di Terna sono facoltative**
(decisione di Paolo del 20/11 sera): senza chiavi il worker va avanti con il Download Center di Terna, che dà anche il
mese in corso.

## Procedura AR1–AR7

### AR1. [Browser] Merge della pull request
1. Apri la pull request del ramo `claude/2026-11-20-insieme` su https://github.com/StatoCritico/eugenio/pulls (collegamento
   di Claude), scheda **Files changed**, poi **Merge pull request** → **Confirm merge**.
2. Cosa deve comparire: «Pull request successfully merged and closed».

### AR2. [Browser] Release v2026.11.21
1. Apri il collegamento già compilato da Claude: https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.21&target=main&title=v2026.11.21+%E2%80%93+Elettricit%C3%A0+in+Italia%3A+produzione%2C+consumi+e+carichi&body=%2A%2AElettricit%C3%A0+in+Italia%3A+produzione%2C+consumi+e+carichi%2A%2A+%2821%2F11%2F2026%2C+versione+20261121a%29%0A%0ANuovo%0A-+Statistiche+%E2%80%BA+Produzione+e+consumi+di+elettricit%C3%A0+%28sperimentale%29%3A+istogrammi+per+regione+e+per+provincia+della+potenza+installata%2C+della+produzione%2C+dei+carichi+e+dei+consumi+per+settore%2C+con+gli+obiettivi+regionali+al+2030+%28burden+sharing%29.+Dati+di+Terna+dal+2000.+Si+scarica+solo+l%27immagine.%0A-+Statistiche+%E2%80%BA+Carichi+elettrici+%28sperimentale%29%3A+il+carico+elettrico+di+una+zona+di+mercato+o+di+tutta+Italia+nel+periodo+che+scegli%2C+a+ore+o+a+quarti+d%27ora%3A+profilo+del+giorno+con+minimo+e+massimo%2C+curva+di+durata+e+fonti+di+produzione+al+100+%25.%0A-+Collegamento+a+questa+simulazione%3A+in+fondo+alle+pagine+che+funzionano+con+delle+scelte+c%27%C3%A8+un+collegamento%2C+con+il+pulsante+per+copiarlo%2C+che+si+aggiorna+da+solo.+Salvalo+e+incollalo+nel+browser+per+ripartire+dalle+stesse+scelte.%0A%0AMigliorato%0A-+Tutte+le+pagine%3A+i+numeri+hanno+sempre+il+punto+delle+migliaia+%28per+esempio+12.345%29.%0A-+Fotovoltaico+%E2%80%BA+Comunit%C3%A0+energetiche+%28ancora+in+anteprima%29%3A+le+aree+convenzionali+del+GSE+sono+accese+gi%C3%A0+all%27apertura+e+si+riaccendono+da+sole+quando+aggiungi+una+sede.%0A-+Clima+e+meteo+%E2%80%BA+Cambiamento+climatico%3A+sul+telefono+la+tabella+dei+risultati+non+allarga+pi%C3%B9+la+pagina.%0A%0APagine%3A+https%3A%2F%2Feugenio.statocritico.it%2Felettricita.html+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fcarichi.html.
2. Controlla che il tag sia `v2026.11.21` e che il testo sia quello della voce delle Novità, poi premi **Publish release**.
3. Cosa deve comparire: la pagina della release `v2026.11.21` con l'etichetta **Latest**.

### AR3. [Server] Cartella dei dati di Terna (solo se non l'hai già fatta con la procedura del 20/11 e)
```bash
ssh eugenio
ls -ldn /srv/energia/dati/terna
```
Se compare `No such file or directory`, fai il passo **T4** di `AGGIORNAMENTO_2026-11-20e.md` (quattro comandi: crea la
cartella e dà i permessi al worker). Cosa deve comparire alla fine: una riga che comincia con `drwxrwxr-x+` e contiene
`1000 1000`.

Le chiavi dell'API di Terna (passi **T2–T3** di `AGGIORNAMENTO_2026-11-20e.md`) **si possono saltare**: senza chiavi il
registro del worker scrive una riga che l'API è spenta e lo storico arriva lo stesso dal Download Center.

### AR4. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa deve comparire: `Aggiornamento da v2026.11.20… a v2026.11.21`, poi, perché c'è la fase 15 nuova, la ricostruzione
dell'immagine con `api` e `worker` ricreati (`api e worker aggiornati e funzionanti` nel registro), `Release v2026.11.21
installata` e il Purge di Cloudflare fatto. Poi:
```bash
cd ~/energia/fase4-server
docker compose ps
```
Cosa deve comparire: `api` e `worker` in stato `running` (l'api anche `healthy` dopo un minuto).

### AR5. [Server] Primi dati delle due pagine, subito a mano
Il worker li farebbe da solo (statistiche annuali alla prima accensione e poi il 5 del mese alle 05:00; carichi ogni
giorno dalle 06:30). Per vederli subito:

1. **Statistiche annuali** («Produzione e consumi di elettricità»). Prima guarda se il worker appena ricreato l'ha già
   fatto:
   ```bash
   cd ~/energia/fase4-server
   docker compose logs --since 1h worker | grep -i "statistiche di terna"
   ```
   Se non compare niente, lancialo a mano (alcuni minuti: una richiesta al secondo al Download Center, anni dal 2000):
   ```bash
   docker compose run --rm worker python -m servizio.worker elettricita 2>&1 | tail -5
   ls /srv/energia/sito/dati/elettricita | head
   ```
   Cosa deve comparire: `Statistiche di Terna: N file pubblicati in /sito/dati/elettricita` e, nella cartella, fra gli
   altri `italia.json`.

2. **Carichi** («Carichi elettrici»): storico dal Download Center e file della pagina.
   ```bash
   docker compose run --rm worker python -m servizio.worker terna-api 2>&1 | tee ~/terna_primo.log | tail -5
   ls /srv/energia/sito/dati/carichi | head
   ```
   (Il comando completo è `python -m servizio.worker terna-api`, come in `AGGIORNAMENTO_2026-11-20e.md`, passo T6.) Dura
   2–4 minuti. Cosa deve comparire: l'ultima riga `INFO terna Terna: {...}` con `'mesi_dc': ['carico_totale 2021-01', …]`
   (6 mesi di storico per serie) e, senza chiavi, `'api': 'spenta'`; nella cartella `indice.json`, `carico_AAAA-MM.json` e
   `fonti_AAAA-MM.json`. Se scrive `un altro aggiornamento è in corso, niente da fare`, il worker l'ha già lanciato da
   solo: guarda `docker compose logs --since 1h worker | grep -i terna`.

   Ogni giro aggiunge 6 mesi di storico (da gennaio 2021): da solo il worker arriva al mese scorso in circa 12 giorni.
   Nel frattempo la pagina ha i primi mesi del 2021 e il mese in corso. **Facoltativo**, per avere tutto lo storico
   subito (un giro più lungo, 10–20 minuti, sempre una richiesta al secondo):
   ```bash
   docker compose run --rm -e TERNA_STORICO_MESI=72 worker python -m servizio.worker terna-api 2>&1 | tail -3
   ```

### AR6. [Browser] Prove
1. Apri https://eugenio.statocritico.it/elettricita.html con **Ctrl+F5**: nel menu Statistiche c'è la voce «Produzione e
   consumi di elettricità» con la «S» di sperimentale; la mappa delle regioni si colora e gli istogrammi si riempiono. C'è
   solo il pulsante per l'immagine, nessun CSV o Excel. Se la pagina dice che i dati non ci sono ancora, rifai AR5.1.
2. Apri https://eugenio.statocritico.it/carichi.html con **Ctrl+F5**: valori del periodo, profilo giornaliero, curva di
   durata e fonti. Fai clic sulla zona Nord nella piccola mappa: i grafici cambiano e compare la nota che la produzione per
   fonte c'è solo per tutta l'Italia. Togli «Quarti d'ora»: i grafici passano alle ore. Se la pagina dice che i dati non
   ci sono ancora, rifai AR5.2.
3. **Collegamento**: apri https://eugenio.statocritico.it/legge10.html, scegli un comune e un numero di anni; in fondo alla
   pagina il riquadro «Collegamento a questa simulazione» mostra l'indirizzo, che cambia da solo a ogni scelta. Premi il
   pulsante per copiarlo, aprilo in una finestra anonima: la pagina riparte con lo stesso comune e gli stessi anni.
4. **Numeri col punto**: apri https://eugenio.statocritico.it/indicatori.html: gli importi in euro hanno il punto delle
   migliaia (per esempio `12.345`), anche nei grafici.
5. Apri https://eugenio.statocritico.it/novita.html: in cima la voce del 21/11/2026, versione `20261121a`.

### AR7. [Server] MGP (solo uso interno)
Con questa release arriva anche il lavoro notturno `mercato-mgp` del GME: segui i passi **MGP3–MGP5** di
`AGGIORNAMENTO_2026-11-20f.md` (credenziali e spazio, prima esecuzione facoltativa, stato dell'archivio il mattino dopo).
Quei dati restano sul server, mai sul sito né esportati.

## Prove (21/11/2026)

Vedi il messaggio di Claude con la pull request: prove della fase 5 (costruzione delle pagine, file per gli agenti, menu,
le due pagine nuove, collegamento) e della fase 15.
