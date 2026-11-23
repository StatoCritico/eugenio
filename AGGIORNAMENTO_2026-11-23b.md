# Aggiornamento del 23/11/2026 b – Pagina iniziale 16:9 e dodici pagine verificate

Release `v2026.11.23b`, versione del sito `20261123b`. Paolo, 23/11 alle 08:45, dopo la `v2026.11.23` («funziona, ma»):

1. titoli dei mirini più grandi del 30 % e 0,5 s di pausa tra uno e l'altro (prima 1 s);
2. il disegno deve stare tutto nella finestra contando anche titolo e testo in alto (prima si doveva scorrere);
3. titoli con gli argomenti del menu, non gli oggetti del disegno (via «sul tetto», «sulla torre», «sulla piastra»;
   trattamento aria, recupero, cogeneratore, fotovoltaico restano);
4. testo «EuGEnio prende dati pubblici…» su tutta la larghezza; disegno in 16:9 sui PC (sui telefoni resta com'è): alle
   08:55 Paolo: «il 16:9 lo fa design e te lo do, tu fai il resto» → alle 08:57 il pacchetto
   `eugenio_home_statica_16x9_2026-11-23.zip`, unito a questi ritocchi.

**Aggiunta delle 11:11 (Paolo)**: tolto «sperimentale» da Clima e meteo › Dati pluviometrici e Cambiamento climatico;
Territorio › Edifici pubblici, Ortofoto, Modelli 3D; Trattamento aria › Trasformazioni (UTA), Ore di funzionamento, Carichi
latenti (tutte tranne Free cooling e recupero); Fotovoltaico › Cabine primarie; Statistiche › Stato della rete elettrica,
Produzione e consumi di elettricità, Carichi elettrici (tutte tranne Suolo e aree agricole). Tolti tutti e tre i segni
(11:15): l'etichetta nel menu in alto e in quello del telefono, quella nelle schede della pagina iniziale (viene dal
menu) e l'avviso «Attenzione! Servizio sperimentale» in cima alla pagina (le tre di Trattamento aria non lo avevano).
Restano sperimentali le pagine di Edifici, Free cooling e recupero, Suolo e aree agricole. Voce «Verificato» nelle Novità.

Fatto:

- **16:9 di Claude Design**: fondali 1920 × 1080 (scuro 81 KB, chiaro 118 KB), quadro 16:9 per tutti gli schermi,
  bersagli riposizionati; sul telefono la scheda flottante è fissata in fondo allo schermo. Del pacchetto di Design si
  sono presi fondali, rapporto, posizioni e scheda del telefono; `home.js` resta quello con i ritocchi sotto (quello del
  pacchetto era ancora a 1 s / 1 s e contava solo la testata).
- `parti/scena_home.html`: titoli 30 % più grandi e con gli argomenti del menu.
- `sito/home.js`: altezza dal bordo alto del disegno al fondo della finestra; rapporto letto dall'`aspect-ratio` del CSS ; 1 s acceso e 0,5 s
  spento; titolo a sinistra dei bersagli nella parte destra e, sul telefono, spostato dentro il bordo se non ci sta.
- Titoli nuovi: Previsioni e dati climatici, Dati pluviometrici, Territorio ed edifici pubblici, Edifici e modelli 3D,
  Geometria e luce naturale, Indici dei prezzi e costi energetici, Fotovoltaico, Solare termico, Pompe di calore,
  Fabbisogno e Conto Termico, Raffrescamento, Elettricità e rete elettrica, Consumi di gas naturale (invariati: Unità di
  trattamento aria, Recupero di calore e free cooling, Cogeneratore).
- `stile.css`: testo di presentazione a tutta larghezza, margini del titolo un po' più stretti.

Prove: `test_home_browser.py` (anche: disegno tutto nella finestra a 1366 × 800, testo a tutta larghezza, titoli senza
«sul»/«sulla») e la suite della fase 5. Guardata a 1920 × 960, 1440 × 800, 1366 × 650 e 375 × 740.

## Passi

- **PI1** – [Browser] Merge della pull request su GitHub (collegamento nella risposta di Claude).
- **PI2** – [Browser] Release `v2026.11.23b` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.23b&target=main&title=v2026.11.23b%20%E2%80%93%20Pagina%20iniziale%2016%3A9%20e%20dodici%20pagine%20verificate&body=%2A%2APagina%20iniziale%2016%3A9%20e%20dodici%20pagine%20verificate%2A%2A%20%2823%2F11%2F2026%2C%20versione%2020261123b%29%0A%0AMigliorato%0A-%20Pagina%20iniziale%3A%20il%20disegno%20%C3%A8%20ora%20in%20formato%2016%3A9%2C%20pi%C3%B9%20adatto%20agli%20schermi%20dei%20computer%2C%20e%20si%20vede%20tutto%20senza%20scorrere%2C%20sotto%20il%20titolo%20e%20il%20testo%20di%20presentazione%2C%20che%20ora%20occupa%20tutta%20la%20larghezza.%0A-%20I%20nomi%20sui%20mirini%20sono%20pi%C3%B9%20grandi%2C%20si%20alternano%20pi%C3%B9%20in%20fretta%20e%20indicano%20gli%20argomenti%20delle%20pagine%20%28per%20esempio%20%C2%ABPompe%20di%20calore%C2%BB%2C%20%C2%ABDati%20pluviometrici%C2%BB%2C%20%C2%ABElettricit%C3%A0%20e%20rete%20elettrica%C2%BB%29.%0A%0AVerificato%0A-%20Non%20pi%C3%B9%20sperimentali%3A%20Clima%20e%20meteo%20%E2%80%BA%20Dati%20pluviometrici%20e%20Cambiamento%20climatico%3B%20Territorio%20%E2%80%BA%20Edifici%20pubblici%2C%20Ortofoto%20e%20Modelli%203D%3B%20Trattamento%20aria%20%E2%80%BA%20Trasformazioni%20%28UTA%29%2C%20Ore%20di%20funzionamento%20e%20Carichi%20latenti%3B%20Fotovoltaico%20%E2%80%BA%20Cabine%20primarie%3B%20Statistiche%20%E2%80%BA%20Stato%20della%20rete%20elettrica%2C%20Produzione%20e%20consumi%20di%20elettricit%C3%A0%20e%20Carichi%20elettrici.%0A%0APagina%3A%20https%3A%2F%2Feugenio.statocritico.it%2F
- **PI3** – Niente da fare: l'aggiornamento automatico delle 4:40 la installa da solo. Per averla subito, sul server:
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  cat ~/.eugenio_versione
  ```
  Deve dire `v2026.11.23b`.
- **PI4** – [Browser del PC, Ctrl+F5] https://eugenio.statocritico.it/ – il disegno è in 16:9 e si vede tutto senza scorrere; il testo sotto il titolo va da un bordo all'altro; i nomi dei mirini sono più grandi e si
  alternano più in fretta, con gli argomenti del menu.
- **PI4b** – [Browser] https://eugenio.statocritico.it/carichi.html, `pluviometria.html`, `fv-cabine.html`: nessun avviso
  «Servizio sperimentale» in cima e nessuna «S» accanto alle voci nel menu; `suolo.html` lo ha ancora.
- **PI5** – [Telefono] il disegno è in 16:9, i nomi dei mirini non escono dai bordi e la scheda di un mirino sale dal
  fondo dello schermo.
