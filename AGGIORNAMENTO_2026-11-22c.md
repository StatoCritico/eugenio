# Aggiornamento del 22/11/2026 c – Torna la pagina iniziale con le previsioni

Release `v2026.11.22c`, versione del sito `20261122c`. Paolo, 22:56: la pagina iniziale nuova della `v2026.11.22b` è
lentissima e non funziona (niente scritte a rotazione, niente descrizioni al passaggio del mouse, pagine aperte «sotto»
l'immagine): si ritira e `/` torna a essere Previsioni, come prima della `22b`. Tutto il resto della `22b` resta (dati
pluviometrici, carichi elettrici, colori del suolo, schede degli enti). Nessun passo sul server oltre all'installazione.

## Passi

- **PC1** – Merge della pull request su GitHub (collegamento nella risposta di Claude).
- **PC2** – Release `v2026.11.22c` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.22c&target=main&title=v2026.11.22c+%E2%80%93+Torna+la+pagina+iniziale+con+le+previsioni&body=%2A%2ATorna+la+pagina+iniziale+con+le+previsioni%2A%2A+%2822%2F11%2F2026%2C+versione+20261122c%29%0A%0AMigliorato%0A-+La+pagina+iniziale+torna+a+essere+Previsioni%2C+come+prima%3A+la+nuova+pagina+con+il+disegno+animato+era+troppo+lenta+e+la+ritiriamo+per+rifarla.%0A%0APagina%3A+https%3A%2F%2Feugenio.statocritico.it%2F
- **PC3** – Niente da fare: l'aggiornamento automatico delle 4:40 la installa da solo. Per averla subito, sul server:
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  cat ~/.eugenio_versione
  ```
  Deve dire `v2026.11.22c`.
- **PC4** – [Browser, Ctrl+F5] https://eugenio.statocritico.it/ apre Previsioni (mappa dei comuni con i gradi giorno);
  nel menu Clima e meteo › Previsioni è evidenziata; https://eugenio.statocritico.it/novita.html ha in cima «22/11/2026 ·
  versione 20261122c».

Sul server restano `previsioni.html`, `home.js` e `home_*.webp` della `22b` (lo script non cancella file del sito): non
danno fastidio; si possono togliere con `rm /srv/energia/sito/{previsioni.html,home.js,home_*.webp}`.
