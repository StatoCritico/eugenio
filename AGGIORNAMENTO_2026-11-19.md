# Aggiornamento del 19/11/2026 – righello, 3D della vista e più edifici, ortofoto nella rete, confini automatici delle cabine

Pubblicazione sopra la `v2026.11.18`. Sito **`?v=20261119a`**, release **`v2026.11.19`**, voce nelle Novità. Cambiano i file
statici del sito e, per la ricerca degli indirizzi, `fase7-territorio/territorio/luogo.py`: l'aggiornamento ricostruisce
l'immagine dell'api da solo; nessun archivio, nessun passo a mano sul server.

## Richieste di Paolo (19/11/2026, mattina)

| Richiesta | Cosa è stato fatto |
|---|---|
| Modelli 3D: fare l'alzato **senza selezionare un edificio**, secondo la vista sullo schermo | Senza edificio scelto **«Genera il 3D»** fa il 3D della vista (da zoom 15; la scritta del pulsante resta uguale, lo dice il suo suggerimento): 3D della zona sullo schermo con tutti gli edifici delle tessere; il contesto di 250 m attorno al centro dà ripiego OpenStreetMap, quote, tetti scelti e alberi. Nessun edificio in evidenza e nessun calcolo finché non si fa clic su un volume. |
| Modelli 3D: **selezione multipla con Maiuscolo** e valori aggregati di volume e superficie | **Maiuscolo + clic** aggiunge o toglie un edificio, nella mappa 2D e nella vista 3D. Tabella dei corpi, superfici, volume lordo, superficie disperdente, S/V e gli altri indicatori sono calcolati sugli edifici scelti insieme (stesse funzioni di prima; le pareti in comune tra gli edifici scelti contano come «tra corpi»). Nella scheda «Edifici scelti insieme: N (valori sommati)». Maiuscolo + trascinamento non fa più lo zoom a riquadro, in questa pagina. |
| Rete elettrica: **ortofoto sotto**, accendibile e spegnibile | Casella **«Ortofoto»** tra gli strati (accesa): da lontano il contesto satellitare Sentinel-2, da vicino (zoom 10 e oltre) la fonte migliore della zona (AGEA 2022-2024 o la regionale), scelta da sola come in Cabine primarie. Citazione sotto la mappa e nell'immagine scaricata. Per vedere bene la foto conviene spegnere «Criticità dei comuni». |
| Rete elettrica: cabine **più piccole**, come i pallini blu delle interruzioni | Stesso raggio delle interruzioni (4 px a zoom 5, 6 a zoom 10, 8 a zoom 14; prima 4,5–12). Solo in questa pagina: in Cabine primarie restano come prima. |
| **Righello** in tutte le pagine con l'ortofoto | Pulsante piccolo col righello sotto la mappa, accanto ai livelli: Modelli 3D e le pagine 3D (nella riga di «Genera il 3D»), Ortofoto, Edifici pubblici, Aggiungi edifici (sotto la mappa), Cabine primarie (accanto alle caselle della mappa di dettaglio), Stato della rete elettrica (accanto alle caselle). Clic sinistro = punto; clic sul primo punto = forma chiusa con l'area; un clic (o un tocco) su un punto lo prende e quello successivo lo posa, anche col dito; clic destro = azzera (o annulla lo spostamento); Esc = spento. Passando sopra la misura: lunghezza, oppure area e perimetro. Con il righello acceso i clic non scelgono edifici o comuni. |
| Cabine primarie: **confini richiesti al clic** sulla mappa, con le **aree confinanti** | Un clic sulla mappa di dettaglio che mette o sposta il punto, la ricerca, il trascinamento o il clic su un punto (mappa o elenco) chiedono da soli al GSE il perimetro dell'area che contiene il punto (bordo spesso) e quelli di tutte le aree che la toccano (bordo sottile). Il pulsante «Aggiorna confini» resta per le cabine spuntate. Non per i punti caricati da un elenco, finché non se ne sceglie uno. |

## Seconda richiesta di Paolo (19/11/2026, 11:03)

- **«Torna alla mappa 2D» lascia la scelta attiva**: gli edifici generati restano in evidenza e in `daGenerare`; «Genera il
  3D» li rigenera, Maiuscolo + clic ne aggiunge o ne toglie, un clic su un altro edificio cambia la scelta. (Prima il
  pulsante passava l'evento a `esci3d`, che lo prendeva per «azzera».)
- **Righello**: un punto non si trascina più tenendo premuto. Un clic o un tocco sul punto lo prende (arancione, più
  grande; col mouse segue il puntatore), il clic o tocco successivo lo posa; clic destro o Esc annullano lo spostamento. I
  tocchi brevi col dito valgono come clic; mentre il righello è acceso il doppio clic/tocco non ingrandisce la mappa.

## Ricerca «piazza San Marco» a Venezia ferma (segnalazione di Paolo, 19/11/2026, 13:38)

Il difetto è già nella versione online (`v2026.11.18`, ricerca di un luogo del 17–18/11). Con la sola via, il server
raggruppa i civici ANNCSU della via per trovare i tratti lontani tra loro (frazioni); lo faceva confrontando **tutte le
coppie** di civici. A Venezia l'odonimo ANNCSU di «San Marco» è il **sestiere**, con migliaia di civici: migliaia al quadrato
di confronti (circa 4 s ogni 6.000 civici nel container, di più sul server ARM, per ognuna delle vie simili) e la pagina resta
su «Cerco…». Ora i soli civici si raggruppano con una griglia (stesso risultato, 20.000 civici in 0,04 s); prova nuova in
`fase7-territorio/tests/test_luogo.py`. Da confermare dopo l'aggiornamento (AI3, punto 6): dal browser non ho potuto vedere la
risposta vera del server (riquadro del browser nascosto).

## Note sulle regole già decise

- **GSE**: valgono le regole del 17/11. I poligoni si chiedono sempre e solo con `where=COD_AC IN (…)`; le confinanti si
  trovano con una domanda che manda il poligono dell'area del punto e riceve **solo i codici** (`returnGeometry=false`). La
  domanda col poligono è un `POST` (il poligono non sta nell'indirizzo), dal browser come le altre: niente server di
  EuGEnio, niente copie; strato spento nelle immagini; attribuzione CC BY-NC-SA 3.0 IT.
- **Misure del righello**: distanze orizzontali sull'ellissoide, area nella proiezione equivalente locale; indicative (le
  ortofoto hanno uno scarto di qualche metro), non sostituiscono un rilievo.

## Test (19/11/2026, container, Chromium headless)

| Prove | Esito |
|---|---|
| `tests/test_prove_1911_browser.py` (nuovo, 11 prove) | passate |
| tutte le prove della fase 5 (`python -m pytest tests`) | 222 passate, 2 saltate (11 minuti) |
| `fase4-server/tests/test_agenti.py` | passate |

Modifiche alle prove esistenti: in `test_mappe_browser.py` il pulsante senza edificio scelto resta acceso
(prima era spento); in `test_prove_0911b_browser.py` nella riga sotto la mappa c'è anche il righello; in
`test_rete_browser.py` si aspettano i confini automatici prima di «Aggiorna confini».

## Procedura AI1–AI3

### AI1. [Browser] Merge e release
1. Apri la pull request (collegamento di Claude; elenco su https://github.com/StatoCritico/eugenio/pulls), scheda **Files
   changed**, poi **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude e premi
   **Publish release**.

### AI2. [Server] Aggiornamento
Niente da fare a mano: alle 4:40 l'aggiornamento notturno installa la `v2026.11.19` (email solo se qualcosa va storto). Per
averla subito:
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.18 a v2026.11.19`, `Release v2026.11.19 installata`.

### AI3. [Browser] Prove (Ctrl+F5 su ogni pagina)
1. https://eugenio.statocritico.it/rete-elettrica.html: le cabine sono punti piccoli come quelli blu; sotto i comuni la
   foto satellitare; avvicinandoti (zoom 10 e oltre) la foto aerea, con la citazione sotto la mappa. Togli la spunta
   «Ortofoto»: la foto sparisce.
2. Sulla stessa pagina premi il righello accanto alle caselle, fai tre clic sulla mappa e poi clic sul primo punto: compare
   l'area gialla; passa sopra col mouse: area e perimetro. Clic su un punto: diventa arancione e segue il mouse; clic dove
   posarlo. Prova lo stesso col dito dal telefono. Clic destro: tutto azzerato. Esc: righello
   spento (il clic su un comune torna ad aprirlo).
3. https://eugenio.statocritico.it/modelli3d.html: senza scegliere edifici, avvicinati (zoom 15 o più) e premi «Genera il 3D»:
   il 3D della zona. Clic su un edificio: i suoi dati a destra. Maiuscolo + clic su un altro: la tabella dei
   corpi li ha tutti e due, volume e superfici sono sommati. Maiuscolo + clic di nuovo sul secondo: torna al primo da solo.
4. «Torna alla mappa 2D»: gli edifici scelti restano in evidenza. Clic su un altro edificio, Maiuscolo + clic su un terzo,
   «Genera il 3D»: tutti e due in arancio.
5. https://eugenio.statocritico.it/fv-cabine.html: avvicinati sulla mappa di dettaglio e fai clic: compare il punto e, dopo
   qualche secondo, il confine dell'area del GSE (bordo spesso) con le aree confinanti (bordo sottile), anche nella mappa in
   alto. Se il GSE non risponde lo dice il messaggio sopra l'elenco delle cabine.
6. https://eugenio.statocritico.it/modelli3d.html: Comune «Venezia», Indirizzo «piazza San Marco», «Cerca l'indirizzo»:
   entro qualche secondo la mappa va sulla piazza (o compare l'elenco delle vie fra cui scegliere).

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, stato: `?v=20261119a`, release `v2026.11.19`: righello, 3D della vista e più edifici, ortofoto nella rete,
  cabine piccole, confini automatici delle cabine.
- DA_FARE: [ ] **Paolo**: AI1 (Merge e release), AI3 dopo l'aggiornamento.
