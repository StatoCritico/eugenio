# Aggiornamento del 23/11/2026 – Nuova pagina iniziale (versione statica)

Release `v2026.11.23`, versione del sito `20261123a`. Paolo, 22/11 alle 23:42: la pagina iniziale rifatta con Claude Design
(zip `eugenio_home_statica_2026-11-23.zip`) va provata, corretta se serve e messa nella prossima release.

Cosa cambia rispetto alla `v2026.11.22c`:

- `/` torna a essere la **pagina iniziale**, ma con un **disegno fermo** (un'immagine WebP per tema, 120 e 190 KB) al posto
  della scena animata della `22b` che era lentissima: gli unici elementi attivi sono **16 bersagli** con i titoli a turno, la
  descrizione al passaggio e, al clic, una **scheda flottante** sopra l'immagine con le pagine della parte. Sotto restano le
  schede dei gruppi del menu e le ultime novità.
- **Previsioni** torna in `previsioni.html`; gli indirizzi vecchi con parametri (`/?comune=…`, `/#…`) ci passano da soli.
- Tolti da `stile.css` gli stili della scena animata (~1.000 righe) e i fondali «inverno», non più usati.
- Correzioni fatte nella prova: tolta la cornice del vecchio contenitore (era più larga del disegno e spostata a sinistra);
  sul telefono il disegno sbordava di 1 px a destra (calcolo della posizione in `home.js`).

Prove: `fase5-sito/tests/test_home_browser.py` (6 prove in Chromium) passate; pagina guardata a 1440, 1920 e 375 px, tema
scuro e chiaro, senza errori JavaScript.

## Passi

- **PH1** – [Browser] Merge della pull request su GitHub (collegamento nella risposta di Claude).
- **PH2** – [Browser] Release `v2026.11.23` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.23&target=main&title=v2026.11.23+%E2%80%93+Nuova+pagina+iniziale&body=%2A%2ANuova+pagina+iniziale%2A%2A+%2823%2F11%2F2026%2C+versione+20261123a%29%0A%0ANuovo%0A-+Nuova+pagina+iniziale%3A+un+disegno+con+l%27edificio%2C+i+suoi+impianti%2C+le+reti+che+lo+alimentano%2C+il+territorio+intorno+e+il+meteo%2C+in+due+stili+%28futuristico+con+il+tema+scuro%2C+tecnico+con+il+tema+chiaro%29.+I+mirini+sul+disegno+mostrano+a+turno+il+loro+nome%3B+passandoci+sopra+vedi+a+cosa+servono+e+con+un+clic+%28o+un+tocco%29+si+apre+una+scheda+con+le+pagine+di+quella+parte.+Le+parti+ancora+in+preparazione+dicono+%C2%ABProssimamente%C2%BB.+Il+disegno+%C3%A8+un%27immagine+ferma%3A+la+pagina+si+apre+subito.%0A-+Previsioni+ora+si+apre+da+previsioni.html%3B+i+vecchi+collegamenti+continuano+a+funzionare.%0A%0APagina%3A+https%3A%2F%2Feugenio.statocritico.it%2F
- **PH3** – Niente da fare: l'aggiornamento automatico delle 4:40 la installa da solo. Per averla subito, sul server:
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  cat ~/.eugenio_versione
  ```
  Deve dire `v2026.11.23`.
- **PH4** – [Browser, Ctrl+F5] https://eugenio.statocritico.it/ apre la pagina iniziale con il disegno, che compare subito;
  i nomi dei mirini si accendono uno alla volta; passando sopra un mirino compare la descrizione; con un clic si apre la
  scheda con le pagine, e un clic su una pagina la apre con il menu del suo gruppo in vista. Con ◐ il disegno passa alla
  versione tecnica chiara.
- **PH5** – [Browser] https://eugenio.statocritico.it/?regione=08 apre Previsioni (`previsioni.html?regione=08`);
  https://eugenio.statocritico.it/novita.html ha in cima «23/11/2026 · versione 20261123a».
- **PH6** – [Server, facoltativo] Togliere i fondali «inverno» della `22b`, non più usati:
  ```bash
  rm -f /srv/energia/sito/home_scuro_inverno.webp /srv/energia/sito/home_chiaro_inverno.webp
  ```

Se anche questa versione online si comporta in modo diverso dalla prova (lenta, senza scritte), annotare browser e
dimensione della finestra: il disegno non ha più animazioni, quindi la lentezza verrebbe da altro (cache di Cloudflare: un
Purge risolve).
