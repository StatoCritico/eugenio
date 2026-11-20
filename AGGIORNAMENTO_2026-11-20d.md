# Aggiornamento del 20/11/2026 d – Comunità energetiche: confini delle aree delle sedi a qualsiasi zoom

Pubblicazione sopra la `v2026.11.20c`. Sito **`?v=20261120d`**, release **`v2026.11.20d`**, voce nelle Novità. Cambiano
solo il sito (`cer_sedi.js`, versione di tutte le pagine), i testi per gli agenti e le prove: niente da fare a mano sul
server oltre all'aggiornamento.

## Richiesta di Paolo (20/11/2026, 14:08)

«Le aree delle cabine primarie una volta che si sceglie un punto si devono vedere a qualsiasi zoom, inoltre va evidenziata
quella su cui si trova il mouse come era nella versione precedente.»

## Cosa cambia

- Per ogni sede (aggiunta con un clic, cercata, scritta a mano o da un elenco) il browser chiede al GSE l'area che la contiene
  e tutte le confinanti, come in Cabine primarie: **bordo spesso** l'area della sede, **sottile** le confinanti, sommate fra le
  sedi, **a qualsiasi ingrandimento** e senza accendere nessuna casella. Togliendo le sedi spariscono.
- **Area sotto il mouse in azzurro chiaro** trasparente, sia nei confini delle sedi sia nello strato «Aree convenzionali
  (GSE)» della casella (che resta da zoom 10, per esplorare la zona).
- Al passaggio del mouse: codice, gestore, «area di una sede» o «area confinante»; al clic il riquadro con il collegamento
  al GSE.
- Restano le regole del GSE: lette dal browser, solo a video, mai nelle immagini né nei file (solo il codice); al più 600
  aree a video.
- Prove: fase 5 completa 228 passate, 2 saltate (con la prova nuova sui confini a zoom 5 e sull'area sotto il mouse).

## Procedura AQ1–AQ3

### AQ1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/2026-11-20-cer-confini` (collegamento di Claude), scheda **Files changed**, poi
   **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.20d`) e premi **Publish release**.

### AQ2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.20c a v2026.11.20d`, `Release v2026.11.20d installata` e il Purge di Cloudflare
fatto.

### AQ3. [Browser] Prova
1. Apri https://eugenio.statocritico.it/edificio-cer.html con **Ctrl+F5**.
2. Premi «Aggiungi sedi» e fai clic su un punto (o cerca un indirizzo): compaiono l'area della sede con il bordo spesso e le
   confinanti con il bordo sottile.
3. Allontanati fino all'Italia intera: i confini restano.
4. Passa col mouse sopra le aree: quella sotto il mouse si colora di azzurro chiaro.
