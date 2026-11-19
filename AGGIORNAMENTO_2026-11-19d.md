# Aggiornamento del 19/11/2026 d – Cabine primarie con una sola mappa

Pubblicazione sopra la `v2026.11.19c`. Sito **`?v=20261119d`**, release **`v2026.11.19d`**, voce nelle Novità. Cambiano solo
il sito (`fv-cabine.html`, `fv_cabine.js`, `stile.css`, versione di tutte le pagine), i testi per gli agenti e le prove:
niente da fare a mano sul server oltre all'aggiornamento.

## Segnalazione e richiesta di Paolo (19/11/2026, 19:29)

«La pagina cabine primarie non funziona. Elimina la mappa grande in alto (quella senza ortofoto) e tutti i controlli e lascia
solo quella in basso (con ortofoto). Aggiungi il righello. I pulsanti del punto (3) Punti spostali sotto la mappa a
sinistra. Invece di "nuovo punto al centro del dettaglio" un pulsante che passa da Sposta a Scegli punti […]. I punti si
devono aggiungere con qualsiasi livello di zoom. Sull'ortofoto si devono vedere tutte le cabine primarie di tutta Italia
(colori della criticità come nello stato della rete). Per ogni punto cliccato (o selezionato con le voci 1 e 2) i confini
della cabina del punto e di tutte le confinanti. Al posto di "Togli tutti i punti" "Cancella tutti" (spegne anche i confini).
Il mouse dentro un'area la retina di un colore leggero e trasparente.»

## Causa del «non funziona» (verificata dal browser sul sito vero)

Nessun errore JavaScript, il GSE rispondeva (anche la domanda `POST` delle aree confinanti, finora provata solo col servizio
simulato: 8 aree a Cesena). Ma la colonna di sinistra era alta quanto la finestra: la mappa con l'ortofoto restava
schiacciata (~300 px) sotto la mappa grande e i comandi sotto di lei, righello compreso, erano fuori vista.

## Cosa cambia

- Una sola mappa, con l'ortofoto, alta `min(72vh, 720px)`; colonna di sinistra alta quanto il contenuto. Tolte la mappa di
  regioni e comuni, le caselle degli strati, la sua immagine e il titolo «Dettaglio».
- Righello sotto la mappa, subito (prima arrivava dopo confini e strati).
- Sotto la mappa a sinistra: **Sposta** / **Scegli punti**, **Cancella tutti**, colore. Con «Scegli punti» ogni clic segna un
  punto a qualsiasi zoom e parte la ricerca di area GSE, cabina e confini.
- Cabine primarie di tutta Italia sull'ortofoto (`/api/rete/cabine`), colori e grandezza come nello Stato della rete
  elettrica; anello sulle cabine dei punti.
- Confini per **ogni** punto (anche quelli caricati dall'elenco), **sommati** sulla mappa; area sotto il mouse in azzurro
  chiaro trasparente. Restano letti **dal browser** (decisione del 17/11 sulle aree del GSE: mai dal server), solo a video,
  spenti nelle immagini.
- Prove: fase 5 tutta, 221 passate + le 60 rifatte dopo il cambio di versione (2 saltate).

## Procedura AL1–AL3

### AL1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/cabine-una-mappa` (collegamento di Claude), scheda **Files changed**, poi **Merge
   pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.19d`) e premi **Publish release**.

### AL2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.19c a v2026.11.19d`, `Release v2026.11.19d installata` e il Purge di Cloudflare
fatto. (Se AK1–AK4 della `v2026.11.19c` non sono ancora stati fatti, questo aggiornamento li comprende: basta fare AK3 se
si vuole liberare spazio.)

### AL3. [Browser] Prova
1. Apri https://eugenio.statocritico.it/fv-cabine.html con **Ctrl+F5**: una sola mappa con la foto aerea e i pallini colorati
   delle cabine; sotto, a sinistra, «Sposta» (acceso), «Scegli punti», «Cancella tutti», «Colore»; più sotto ortofoto,
   caselle e il pulsante del righello.
2. Con «Sposta» trascina la mappa: nessun punto nuovo.
3. Premi «Scegli punti», avvicinati molto e fai clic: compare il punto, a destra l'area GSE e la cabina, sulla mappa il
   confine spesso dell'area e quelli sottili delle confinanti. Allontanati e fai clic in un'altra zona: i confini si sommano.
4. Passa col mouse dentro un'area: si colora di azzurro chiaro.
5. «Cancella tutti»: spariscono punti e confini.
