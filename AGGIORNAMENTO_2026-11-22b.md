# Aggiornamento del 22/11/2026 b – Pagina iniziale, Dati pluviometrici, Carichi elettrici a confronto, schede degli enti pubblici

Release `v2026.11.22b`, versione del sito `20261122b`: un'unica pubblicazione con i lavori di due conversazioni (via di
Paolo delle 10:36 e 10:45), sopra la `v2026.11.22`.

**Prima di cominciare**: devono essere fatti i passi AT3–AT7 di `AGGIORNAMENTO_2026-11-22.md` (installazione della
`v2026.11.22` con lo script nuovo, worker `elettricita` e `suolo`, rifacimento di tessere e indice degli Edifici pubblici
AT5: la scheda completa della ricerca per ente usa i campi di quell'indice). Se la `v2026.11.22` non è ancora installata,
al passo PB4 lancia lo script dal clone come in AT3, ma con il tag `v2026.11.22b`, poi fai AT3 (worker `elettricita`),
AT4, AT5 e AT7 di quella procedura.

Cosa contiene:
- **Pagina iniziale nuova** (`/`, ramo `claude/2026-11-22-home` unito il 22/11 alle 14:05 su richiesta di Paolo): disegno
  animato per stagione di un edificio a piastra e torre aperto in spaccato, con impianti, ombre, reti, territorio, radar e
  stazione meteo; 17 parti con le loro pagine (o «Prossimamente») e le schede dei gruppi del menu. **Previsioni passa a
  `previsioni.html`**: i vecchi indirizzi `/?…` e `/#…` ci arrivano da soli. Dettagli: `fase5-sito/README.md` § «Pagina
  iniziale».
- **Clima e meteo › Dati pluviometrici** (`pluviometria.html`, nuova, sperimentale, nel menu prima di Previsioni): pioggia
  misurata in Italia dal «Merging» del Dipartimento della Protezione Civile (radar corretto con i pluviometri, un dato
  ogni 30 minuti; niente radar puro), mappa animata fino a 7 giorni con durata, passo e secondi per passo, interruzioni
  della rete del periodo, ortofoto, valori nel punto e pioggia giornaliera del comune con la prevista, file in
  **CC BY-SA 4.0**; a fini statistici, non di allerta. Casella «Pioggia misurata (ultime 3 ore)» in **Stato della rete
  elettrica**; pioggia nel mensile per regione e nel settimanale della **newsletter**. Server: lavoro `radar` del worker,
  rotte `/api/radar/…` e `/api/rete/interruzioni/periodo`, dipendenza `dpc-radar==0.3.0`, due regole nel Caddyfile.
  Dettagli: `fase4-server/README.md` § «Dati pluviometrici».
- **Statistiche › Carichi elettrici** (ramo `claude/2026-11-22-carichi-suolo-enti`): due metà da confrontare, zona a
  discesa, anni e finestra su tutto l'archivio, potenza per fonte in MW, caselle per fonte, «Riallinea le due metà»,
  riquadro «Energia da fonti rinnovabili (Italia)», dati mancanti tratteggiati, Italia = somma delle zone. Worker di
  Terna: giorni mancanti nei mesi archiviati cercati e riprovati una volta al giorno (`TERNA_BUCHI_MESI` 3,
  `TERNA_BUCHI_PROVE` 14, facoltative).
- **Statistiche › Suolo e aree agricole**: tavolozza per il tema scuro e per il chiaro (contrasto e daltonismo).
- **Territorio › Edifici pubblici, «Per ente»**: scheda completa sopra la mappa, stili proprietà / uso / terreni; l'API dà
  campi in più dall'indice già rifatto il 22/11 (nessun rifacimento di tessere o indice).

## Passi

- **PB1** – Merge della pull request (collegamento nella risposta di Claude) su GitHub.
- **PB2** – Release `v2026.11.22b` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.22b&target=main&title=v2026.11.22b+%E2%80%93+Nuova+pagina+iniziale%2C+dati+pluviometrici%2C+carichi+elettrici+a+confronto%2C+schede+degli+enti+pubblici&body=%2A%2ANuova+pagina+iniziale%2C+dati+pluviometrici%2C+carichi+elettrici+a+confronto%2C+schede+degli+enti+pubblici%2A%2A+%2822%2F11%2F2026%2C+versione+20261122b%29%0A%0ANuovo%0A-+Nuova+pagina+iniziale%3A+un+disegno+animato+con+le+stagioni+mostra+un+edificio+aperto+in+spaccato+con+i+suoi+impianti%2C+le+reti+che+lo+alimentano%2C+il+territorio+intorno+e+il+meteo+sopra.+Passando+con+il+mouse+su+ogni+parte+vedi+a+cosa+serve+e+quali+pagine+ci+sono%3B+con+un+clic+si+apre+la+scheda+del+gruppo%2C+e+da+l%C3%AC+la+pagina+con+le+voci+del+suo+gruppo+gi%C3%A0+in+vista.+Le+parti+ancora+in+preparazione+dicono+%C2%ABProssimamente%C2%BB.%0A-+Previsioni+ora+si+apre+da+previsioni.html%3B+i+vecchi+collegamenti+continuano+a+funzionare.%0A-+Clima+e+meteo+%E2%80%BA+Dati+pluviometrici+%28sperimentale%29%3A+la+pioggia+misurata+in+Italia+dalla+Protezione+Civile+%28radar+corretti+con+i+pluviometri%2C+un+dato+ogni+mezz%27ora%29%2C+su+una+mappa+che+si+anima+fino+a+7+giorni+indietro%3A+scegli+la+durata%2C+il+passo+e+la+velocit%C3%A0.+Un+clic+su+un+punto+mostra+la+pioggia+delle+ultime+3%2C+6%2C+12+e+24+ore+e+quella+di+ogni+giorno+degli+ultimi+30+nel+comune%2C+accanto+a+quella+prevista+da+EuGEnio.+Si+possono+accendere+le+interruzioni+della+rete+elettrica+dello+stesso+periodo.+Dati+a+fini+statistici%2C+non+di+allerta%2C+con+licenza+CC+BY-SA+4.0.%0A%0AMigliorato%0A-+Statistiche+%E2%80%BA+Stato+della+rete+elettrica%3A+nuova+casella+%C2%ABPioggia+misurata+%28ultime+3+ore%29%C2%BB+per+vedere+la+pioggia+sotto+le+cabine.%0A-+Newsletter%3A+nel+mensile+per+regione+la+pioggia+del+mese+per+provincia+e+i+comuni+pi%C3%B9+piovosi%3B+nel+settimanale+la+pioggia+caduta+nei+tuoi+comuni%2C+confrontata+con+quella+prevista.%0A-+Statistiche+%E2%80%BA+Carichi+elettrici%3A+la+pagina+%C3%A8+divisa+in+due+met%C3%A0%2C+ognuna+con+le+sue+scelte%2C+per+confrontare+due+zone+o+due+periodi%3B+la+zona+si+sceglie+anche+da+una+casella+a+discesa%2C+l%27anno+con+le+frecce%2C+e+la+finestra+si+sposta+su+tutto+l%27archivio.+Il+pulsante+%C2%ABRiallinea+le+due+met%C3%A0%C2%BB+porta+l%27altra+met%C3%A0+allo+stesso+punto.%0A-+Statistiche+%E2%80%BA+Carichi+elettrici%3A+nuovo+grafico+%C2%ABPotenza+per+fonte%C2%BB+in+MW%2C+che+si+ingrandisce+e+si+sposta+insieme+a+quello+in+percentuale%3B+pulsanti+per+ieri%2C+l%27ultima+settimana%2C+mese%2C+tre+mesi+o+anno%3B+caselle+per+accendere+e+spegnere+le+fonti%2C+con+l%27energia+di+ciascuna.%0A-+Statistiche+%E2%80%BA+Carichi+elettrici%3A+nuovo+riquadro+%C2%ABEnergia+da+fonti+rinnovabili+%28Italia%29%C2%BB+con+la+quota+sulla+produzione+e+sulla+richiesta%3B+i+tratti+senza+dati+di+Terna+sono+segnati+con+un+tratteggio.%0A-+Statistiche+%E2%80%BA+Suolo+e+aree+agricole%3A+colori+leggibili+anche+nel+tema+scuro+e+distinguibili+anche+con+il+daltonismo.%0A-+Territorio+%E2%80%BA+Edifici+pubblici%2C+scheda+%C2%ABPer+ente%C2%BB%3A+un+clic+su+un+immobile+apre+la+scheda+completa+sopra+la+mappa%3B+gli+immobili+in+propriet%C3%A0+sono+a+colore+pieno%2C+quelli+in+uso+trasparenti+con+il+bordo%2C+i+terreni+a+righe.%0A%0APagine%3A+https%3A%2F%2Feugenio.statocritico.it%2F+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fpluviometria.html+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fcarichi.html+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fedifici-pubblici.html%3Fmodo%3Denti+%C2%B7+https%3A%2F%2Feugenio.statocritico.it%2Fsuolo.html

- **PB3** – Cartelle (il worker gira come utente 1000):
  ```bash
  ssh eugenio
  sudo mkdir -p /srv/energia/dati/radar /srv/energia/sito/dati/radar
  sudo chown 1000:1000 /srv/energia/dati/radar /srv/energia/sito/dati/radar
  df -h /srv/energia      # servono ~3 GB liberi nei 10 anni (~250 MB l'anno di mappe + valori)
  ```
- **PB4** – Installazione della release (lo script rifà l'immagine, che ora contiene `dpc-radar`, e non tocca
  `dati/radar` del sito):
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --prova
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  docker compose -f ~/energia/fase4-server/docker-compose.yml exec api python -c "import dpc_radar; print(dpc_radar.__version__)"
  ```
  Cosa deve comparire: «Release v2026.11.22b installata» (`cat ~/.eugenio_versione` = `v2026.11.22b`) e `0.3.0`.
- **PB5** – Caddyfile nuovo (cache di `indice.json` e delle immagini):
  ```bash
  cd ~/energia/fase4-server && docker compose up -d --force-recreate caddy
  ```
- **PB6** – Primo giro a mano (circa un minuto; poi il thread del worker continua ogni 30 minuti e recupera all'indietro
  fino a ~5 mesi, 60 frame per giro, circa un giorno in tutto):
  ```bash
  docker compose run --rm worker python -m servizio.worker radar 2>&1 | tail -8
  ls /srv/energia/sito/dati/radar/ /srv/energia/dati/radar/
  curl -s https://eugenio.statocritico.it/api/radar/stato | head -c 800; echo
  curl -s "https://eugenio.statocritico.it/api/radar/punto?lat=44.14&lon=12.24" | head -c 600; echo
  ```
  Atteso: `indice.json` e le cartelle `CUM3 CUM6 CUM12 CUM24` nel sito; `archivio valori ultimi stato.json` nei dati; nelle
  rotte `licenza` CC BY-SA 4.0 e i valori di Cesena (`null` = nessuna misura, non zero). Se il DPC non risponde, il giro lo
  scrive nel registro; dopo 12 ore senza giri riusciti arriva un'email all'amministratore.
- **PB7** – Controlli nel browser (Ctrl+F5):
  - https://eugenio.statocritico.it/pluviometria.html: mappa della pioggia delle ultime 24 ore, legenda in mm, tratteggio
    grigio dove non c'è misura; «Play» con durata 24 ore e passo 3 ore (automatico), con 7 giorni il passo passa a 1 giorno;
    clic su un punto: valori 3/6/12/24 ore, comune, grafico dei 30 giorni con la prevista (la prevista compare dal giorno
    dopo l'installazione); casella «Interruzioni» con le interruzioni del periodo; citazione del DPC e CC BY-SA sotto la
    mappa e nei file;
  - https://eugenio.statocritico.it/rete-elettrica.html: casella «Pioggia misurata (ultime 3 ore)» spenta; accesa, la
    pioggia sotto le cabine con la sua legenda;
  - menu Clima e meteo: «Dati pluviometrici» prima di Previsioni;
  - https://eugenio.statocritico.it/carichi.html: due metà affiancate con le loro scelte; nella piccola mappa la zona di
    sinistra con bordo pieno scuro e quella di destra tratteggiata; «Riallinea le due metà» porta la destra alla stessa
    sezione; grafico «Potenza per fonte» che si sposta insieme a quello al 100 %; caselle per fonte con i GWh; sesto
    riquadro «Energia da fonti rinnovabili (Italia)»; sul telefono le due metà una sotto l'altra;
  - https://eugenio.statocritico.it/suolo.html nel tema scuro: grafici e istogrammi leggibili, «di cui su suolo agricolo»
    verde chiaro;
  - https://eugenio.statocritico.it/edifici-pubblici.html?modo=enti&sel=3e2f550eee: clic su un pallino → scheda completa
    in alto a sinistra sopra la mappa (chiusa con ×, Esc o clic fuori); in legenda i tre campioni proprietà / uso /
    terreni; nessun codice fiscale né soggetto cedente nella scheda;
  - https://eugenio.statocritico.it/: disegno con le stagioni che cambiano da sole; mouse sull'UTA nello spaccato →
    riquadretto con le pagine di Trattamento aria; mouse sul cogeneratore → «Prossimamente»; clic sul traliccio →
    scheda Statistiche con «Produzione e consumi di elettricità» e «Carichi elettrici» in evidenza; clic su una pagina →
    si apre con le voci del gruppo in orizzontale sotto il menu; menu Clima e meteo › Previsioni → `previsioni.html`;
    un vecchio collegamento `https://eugenio.statocritico.it/?regione=08` apre Previsioni;
  - https://eugenio.statocritico.it/novita.html: prima voce «22/11/2026 · versione 20261122b».
- **PB8** – Newsletter: la sezione di pioggia del settimanale compare dal primo invio dopo 7 giorni di raccolta (la
  prevista dal secondo invio); quella del mensile dal primo mese intero raccolto.

Per spegnere il lavoro senza togliere la pagina: `RADAR_ATTIVO=false` nel `.env` e `docker compose up -d worker`.
