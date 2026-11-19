# Aggiornamento del 19/11/2026 e – Cabine primarie: apertura su tutta Italia e due metà scorrevoli

Pubblicazione sopra la `v2026.11.19d`. Sito **`?v=20261119e`**, release **`v2026.11.19e`**, voce nelle Novità. Cambiano solo
il sito (`fv_cabine.js`, `stile.css`, versione di tutte le pagine), i testi per gli agenti e le prove: niente da fare a mano
sul server oltre all'aggiornamento.

## Richiesta di Paolo (19/11/2026, 21:29)

«Imposta la pagina delle cabine primarie per aprirsi con la mappa allargata a tutta Italia. Inoltre ripristina la divisione
in due parti con le barre di scorrimento sinistra e destra come tutte le altre pagine.»

## Cosa cambia

- La mappa si apre su tutta Italia con le cabine di tutto il Paese, a zoom 5 (non meno: da lì parte lo sfondo Sentinel-2;
  alla prima prova l'inquadratura veniva a 4,8 e lo sfondo restava nero, perché la mappa la calcolava prima di avere
  l'altezza finale). Con `?lat=…&lon=…` si apre sul punto come prima.
- Tornate le due metà come in Stato della rete elettrica, Ortofoto e Modelli 3D: la colonna di sinistra resta ferma sotto il
  menu e scorre con la sua barra, la colonna di destra scorre con la pagina. La mappa non si schiaccia più (era il motivo del
  «non funziona»): gli elementi della colonna non si restringono e la colonna scorre.
- Prove: fase 5, 63 + 52 passate (pagine, agenti, rete, prove del 19/11 nel browser); provata con l'API vera.

## Procedura AM1–AM3

### AM1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/cabine-italia-colonne` (collegamento di Claude), scheda **Files changed**, poi
   **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.19e`) e premi **Publish release**.

### AM2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.19d a v2026.11.19e` (o da una versione precedente: comprende anche la `c` e la
`d`), `Release v2026.11.19e installata` e il Purge di Cloudflare fatto.

### AM3. [Browser] Prova
1. Apri https://eugenio.statocritico.it/fv-cabine.html con **Ctrl+F5**: la mappa mostra tutta Italia sullo sfondo satellitare
   con i pallini colorati delle cabine.
2. Con la rotella fuori dalla mappa, a sinistra scorre solo la colonna della mappa (barra sottile a sinistra), a destra la
   pagina con la ricerca e i punti.
3. Scorrendo la colonna di sinistra si arriva a «Sposta» / «Scegli punti», «Cancella tutti», ortofoto e righello; la mappa
   resta alta.
