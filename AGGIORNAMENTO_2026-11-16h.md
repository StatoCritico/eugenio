# Aggiornamento del 16/11/2026 (h) – Modelli 3D: i vicini fuori da un archivio parziale

Ottava pubblicazione del 16/11, sopra la `v2026.11.16g`. Sito **`?v=20261116h`**, release **`v2026.11.16h`**, voce nelle
Novità. Metodo nuovo: pull request, Merge di Paolo, release pubblicata da Paolo dal collegamento già compilato.

## Il problema (prova AG6 di Paolo, 16/11, 18:48)

A Perugia, scelto il CREO (dentro il riquadro dell'archivio LiDAR PST), il resto del polo ospedaliero S. Maria della
Misericordia (fuori dal riquadro) restava **senza edifici**: niente sagome marroni del ripiego OpenStreetMap.

Causa: in `edificio3d.js` il ripiego OSM si chiedeva **solo se il punto scelto** era fuori da ogni archivio. Con un archivio
**parziale** (senza `istat`: Perugia, Ravenna città, i comuni «centro e frazioni principali») un edificio vicino al bordo
del riquadro lasciava vuoti i vicini di fuori.

## La correzione

- `contestoCoperto` (nuova, in `fase5-sito/sito/edificio3d.js`): se il punto è dentro il riquadro di un archivio di un
  **comune intero** (`istat`) vale il punto, come prima. Così niente richieste in più a Overpass vicino ai confini dei comuni
  interi: la prova dei 19 comuni resta senza chiamate OSM. Se invece il punto è coperto solo da un archivio **parziale**,
  devono essere coperti anche otto punti attorno a ~250 m, cioè i lati e gli angoli del contesto. Altrimenti si chiede
  il ripiego.
- I corpi OSM che cadono nelle zone coperte li scarta `fuoriDalDbtr`, come prima: dove c'è il DB topografico OSM non si
  mescola.
- Messaggio durante la richiesta: «Attorno a questo punto manca il DB topografico: chiedo gli edifici al server…» (prima
  «Qui non c'è ancora il DBTR», sbagliato quando il punto è dentro l'archivio).
- Novità (voce `20261116h`), versione `?v=20261116h` in tutte le pagine, `EUGENIO_PER_AGENTI.md` (le due copie),
  `llms.txt`, README della fase 5.
- Prova nuova `test_vicini_fuori_da_un_archivio_parziale_dal_ripiego_osm` (`fase5-sito/tests/test_mappe_browser.py`).
  Con l'archivio parziale: richiesta OSM, il corpo OSM dentro il riquadro scartato, quello fuori tenuto. Con lo stesso
  archivio come comune intero: nessuna richiesta. Senza la correzione la prova fallisce.

## Test (16/11/2026, container, Chromium)

| Prove | Passate | Saltate |
|---|---|---|
| `test_mappe_browser.py`, `test_costruisci_pagine.py`, `test_prove_0911b/c/e_browser.py` | 96 | 1 |
| `test_agenti.py` (fase 4) | 5 | – |

`costruisci_pagine.py --controlla`: 0 file da rigenerare.

## Procedura AH1–AH3

### AH1. [Browser] Merge e release
1. Apri la pull request (collegamento di Claude; elenco su https://github.com/StatoCritico/eugenio/pulls), scheda **Files
   changed**, poi **Merge pull request** → **Confirm merge**.
2. Scrivi a Claude «merge fatto»: ti manda il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già
   compilato. Aprilo e premi **Publish release**.

### AH2. [Server] Aggiornamento
Niente da fare a mano: alle 4:40 l'aggiornamento notturno installa la `v2026.11.16h` (email solo se qualcosa va storto).
Per averla subito:
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.16g a v2026.11.16h`, `Release v2026.11.16h installata`. Cambiano solo file
statici (sito): nessuna immagine da ricostruire, nessun archivio.

### AH3. [Browser] Prova
1. Apri https://eugenio.statocritico.it/modelli3d.html (Ctrl+F5), Comune «Perugia», Indirizzo «piazzale Giorgio Menghini».
2. Fai clic sul CREO (dentro il riquadro tratteggiato). Cosa aspettarsi: dopo qualche secondo, a sud del riquadro, i corpi
   del polo ospedaliero in marrone (OpenStreetMap). Dentro il riquadro restano solo i corpi grigi del LiDAR, senza doppioni.
3. «Genera il 3D»: il CREO con le altezze del LiDAR, l'ospedale accanto con le altezze di OpenStreetMap o stimate.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, stato: `?v=20261116h`, release `v2026.11.16h`: ripiego OSM anche per i vicini fuori da un archivio parziale.
- DA_FARE: [ ] **Paolo**: AH1 (Merge e release), AH3 dopo l'aggiornamento; [ ] ricerca della sola via senza civico che
  finisce lontano senza avviso («via Sant'Andrea delle Fratte», Perugia): guardare cosa dà l'ANNCSU e avvisare quando ci
  sono più vie con nomi simili.
