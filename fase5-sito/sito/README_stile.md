# Stile del sito: vestiti, temi e variabili

Nota tecnica sullo stile grafico di EuGEnio (27/10/2026). Il progetto è di Claude Design, adattato al sito esistente.

## Temi e vestiti

- Il **tema** può essere scuro (predefinito) o chiaro. Il tema chiaro si attiva con `data-theme="light"` su `<html>`.
- Il **vestito** è la tavolozza dei colori del sito. Corallo è il predefinito e vale quando su `<html>` non c'è
  `data-vestito`. Gli altri sono `ambra`, `indaco`, `lime` e `verde`.
- Il tema e il vestito sono indipendenti tra loro.
- Ogni pagina ha nel `<head>`, **prima** del CSS, uno script breve che legge `localStorage` e imposta i due attributi
  sui valori `tema` e `vestito`. Così al caricamento non si vedono lampi di colori sbagliati. Lo stesso script definisce
  `eugenioLoghi()`, che sceglie i file dei loghi.
- `aspetto.js` collega i pulsanti:
  - **◐ (`.tema`)** cambia il tema. Ce n'è uno nella riga del menu e uno, per il telefono, nella riga del marchio.
  - **asterisco (`.vestito-pulsante`)** è disegnato nel colore `--primario` del vestito attivo. Apre un elenco
    (`role="listbox"`) con un asterisco per vestito, ciascuno nel proprio colore principale. Sul telefono lo stesso
    elenco è sempre aperto nel menu, alla voce «Aspetto».
  - **Tastiera:** frecce, Inizio e Fine per muoversi, Invio o Spazio per scegliere, Esc per chiudere. Un clic fuori
    dall'elenco lo chiude.
- Dopo la scelta di un tema o di un vestito **la pagina non si ricarica** (dal 27/10/2026): mappe e grafici scrivono i
  colori come `var(--…)` nello stile degli elementi SVG e cambiano da soli; i colori calcolati (fondo dei comuni,
  scala dei gradi giorno, striscia delle zone) li rifanno gli script all'evento `eugenio:aspetto` che `aspetto.js`
  emette dopo il cambio. Chi aggiunge un disegno: colori come `"var(--nome)"` (la funzione `el()` degli script li mette
  nello stile), oppure ascoltare `eugenio:aspetto`. Se il browser non salva le scelte, il cambio vale per la pagina
  aperta.

## Grafici (regole dal 28/10/2026)

Valgono per **tutti** i grafici del sito, anche quelli futuri. Il modulo comune è `grafici.js` (oggetto
`window.EUGENIO_GRAFICI`), incluso nelle cinque pagine dei servizi dopo `aspetto.js`; il divisore delle colonne è in
`divisore.js`. Nessuna libreria esterna: SVG scritto a mano, colori come `"var(--…)"`.

1. **Pulsante con la freccina e riquadro flottante.** Ogni grafico ha in alto a destra un piccolo pulsante
   (`.grafico-apri`, aria-label «Apri il grafico in un riquadro») che apre il grafico in un riquadro sopra la pagina
   (`<dialog>` modale, sfondo scurito). Nel riquadro:
   - il grafico è ridisegnato con le misure del riquadro (le scritte restano di 12 px) e si rifà se la finestra cambia;
   - zoom con la rotella del mouse o con due dita, trascinamento col mouse o col dito, doppio clic o «Vista iniziale»
     per tornare all'inizio; da tastiera `+`, `-` e `0`;
   - ci sono **✱** e **◐**, che fanno esattamente quello che fanno nella testata (sono gli stessi comandi di
     `aspetto.js`, esposti in `window.EUGENIO_ASPETTO`): cambiano vestito e tema di tutta la pagina e il grafico nel
     riquadro si aggiorna mantenendo lo zoom;
   - si chiude con ×, con Esc (se l'elenco dei vestiti è aperto, Esc chiude prima quello) o con un clic fuori.
2. **Grafici osservabili.** I grafici a barre o a linee con dati mensili, annuali o per stagione (e anche la
   previsione oraria) mostrano i valori: passando il mouse vicino a una barra o a un punto, la barra si evidenzia
   (classe `.evidenziata`), i punti delle curve prendono un cerchio, compare una linea guida verticale e un
   suggerimento con l'etichetta (mese, anno, stagione) e i valori **formattati all'italiana** (virgola decimale,
   punto per le migliaia, unità: `toLocaleString("it-IT")`). Funziona nella pagina e nel riquadro, col tocco (si
   tocca il grafico; un tocco fuori lo spegne) e con la tastiera (l'SVG prende il fuoco; frecce, Inizio e Fine; il
   valore è letto anche dai lettori di schermo). Non usare `<title>` sulle barre: il suggerimento lo sostituisce.
3. **Pannelli ridimensionabili.** Nelle pagine dei servizi il confine tra la colonna di sinistra (`.mappa-area`) e il
   pannello di destra (`.pannello`) ha una maniglia (`.divisore`, `role="separator"`, cursore col-resize): si
   trascina col mouse o col dito, oppure con le frecce quando ha il fuoco (Maiuscolo per passi grandi, Inizio e Fine
   per i limiti, Canc o doppio clic per la larghezza predefinita). Limiti: pannello almeno 340 px, sinistra almeno
   300 px. La larghezza si ricorda per pagina nel browser (`localStorage`, chiave `larghezza-pannello:<pagina>`, come
   frazione della larghezza). Sotto gli 861 px la colonna è una sola e la maniglia sparisce. A ogni cambio
   `divisore.js` emette `eugenio:ridimensiona` su `document`; mappe e grafici con viewBox si adattano da soli, quelli
   registrati con `adatta: true` si ridisegnano col loro ResizeObserver.

### Come aggiungere un grafico

La funzione di disegno riceve **dove** disegnare e **le misure**: nella pagina `misure.riquadro` è `false` e il grafico
usa le sue misure solite (o `misure.larghezza`, la larghezza del box); nel riquadro usa `misure.larghezza` e
`misure.altezza` come viewBox. La legenda (HTML) va nella stessa destinazione, sotto l'SVG: il riquadro la misura e
dà al grafico l'altezza che resta.

```js
const G = window.EUGENIO_GRAFICI;
function disegnaConsumi(dest, misure, dati) {          // dati: [{ mese: "gen", kwh: 1234.5 }, …]
  const W = misure && misure.riquadro ? misure.larghezza : 640, H = misure && misure.riquadro ? misure.altezza : 240;
  const sx = 48, dx = 8, su = 12, gi = 26;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Consumi mensili" }, dest);
  const max = Math.max(...dati.map((d) => d.kwh)), passo = (W - sx - dx) / dati.length;
  const Y = (v) => su + (H - su - gi) * (1 - v / max);
  const punti = dati.map((d, i) => {
    const x = sx + passo * (i + .5);
    const barra = el("rect", { x: x - passo * .3, y: Y(d.kwh), width: passo * .6, height: Y(0) - Y(d.kwh), fill: "var(--primario)" }, svg);
    return { x, titolo: d.mese, elementi: [barra],
      righe: [["var(--primario)", `consumo: ${d.kwh.toLocaleString("it-IT", { maximumFractionDigits: 1 })} kWh`]] };
  });
  G.osserva(svg, punti, { area: [sx, su, W - dx, H - gi], guida: false });   // guida: false per le sole barre
  // legenda, se serve: dest.appendChild(…)
}
G.registra(document.getElementById("grafico-consumi"), (dest, misure) => disegnaConsumi(dest, misure, dati),
  { titolo: "Consumi mensili", adatta: false });
```

- `registra(box, disegna, { titolo, adatta })` svuota il box, disegna, aggiunge il pulsante con la freccina; si
  richiama ogni volta che i dati cambiano (sostituisce il disegno precedente). `adatta: true` se il disegno nella
  pagina usa `misure.larghezza` (come gli Indicatori).
- `osserva(svg, punti, { area, guida })`: un elemento di `punti` per ogni mese/anno, con `x` in coordinate SVG,
  `titolo`, `righe` (`[colore, testo]`, colore `null` per una riga senza campione), `segni` (`[x, y, colore]`, i
  cerchi sulle curve) ed `elementi` (le barre da evidenziare). Si chiama alla fine del disegno.
- I colori calcolati (non `var(--…)`) vanno rifatti all'evento `eugenio:aspetto`, come già scritto sopra: il riquadro
  aperto ridisegna comunque il suo grafico a ogni cambio di tema o di vestito.

## Loghi

I loghi sono in `logo/<vestito>/`, in versione `_scuro` e `_chiaro`:

- `logo_orizzontale`;
- `scritta`;
- `simbolo`;
- `icona_64`, `icona_32` e `icona_16`.

Tutte le `<img data-logo="NOME">` prendono il file `logo/<vestito>/NOME_<tema>.svg`. Lo fanno così:

- nella testata, `<script>eugenioLoghi()</script>` subito dopo il marchio;
- nel piè di pagina, il simbolo viene aggiornato da `aspetto.js`.

Il `logo_orizzontale` (27/10/2026 sera) ha la stessa geometria del logo dei report: la E di «EuGEnio» è alta quanto
l'edificio, la base del simbolo è sulla linea di base della scritta e il tetto sporge un po' sopra la E
(simbolo `scale(0.85)` traslato, scritta spostata a sinistra di 34,4 unità, `viewBox="0 30 333 61"`). In testata è
alto 28 px sul computer (153 px di larghezza, circa +40 % rispetto a prima) e `min(30px, 7.7vw)` sul telefono.

L'icona del browser è sempre Corallo chiaro (`icona_32_chiaro.svg`, `icona_16_chiaro.svg`).

## Variabili principali (`stile.css`)

| Variabile | Uso |
|---|---|
| `--carta`, `--foglio`, `--rialzo`, `--tinta`, `--linea`, `--bordo` | fondi, riquadri, bordi |
| `--inchiostro`, `--tenue` | testo e testo secondario |
| `--primario`, `--primario-forte`, `--su-primario`, `--profondo` | colore del vestito: link, pulsanti, barre, titoli dei grafici |
| `--segno` | valore di legge e comune scelto |
| `--successo`, `--attenzione`, `--errore` (e i `-fondo`) | stati e messaggi |
| `--serie-1` … `--serie-6` | serie dei grafici, una per tratto: continua, `7 4`, `2 3`, `10 3 2 3`, `12 5`, `1 4` |
| `--scala-da`, `--scala-a` | mappa della Previsione e striscia delle zone climatiche, dal chiaro allo scuro |
| `--reg-01` … `--reg-20` | colori delle regioni (codice ISTAT), letti da `minimappa.js`; cambiano con il tema e sono uguali in tutti i vestiti. Nel tema scuro (27/10/2026 sera): regioni vicine al 50 %, piccola mappa all'80 %, e i comuni della regione scelta riempiti con il colore della regione schiarito del 18 % (`EUGENIO.fondoComuni`), così la regione scelta è la più luminosa e i confini comunali scuri si vedono; nel tema chiaro tutto come prima (comuni in `--linea`) |
| `--freddo`, `--gelo`, `--avviso`, `--fuoco` | vecchi nomi, rimasti come alias di `--primario`, `--profondo`, `--segno`, `--tinta` |
| `--ind-ente`, `--ind-regione`, `--ind-italia`, `--ind-risc`, `--ind-ele`, `--ind-altre` | alias delle serie per `indicatori.js` |

Ogni vestito ridefinisce solo:

- fondi e testo;
- `--primario`, `--primario-forte`, `--su-primario`, `--profondo`, `--curva`;
- `--segno`;
- `--scala-da` e `--scala-a`.

Serie, regioni e stati restano quelli di Corallo.

I caratteri sono in `font/`. Hanken Grotesk, variabile, è usato per il testo. Barlow 500, 600 e 700, da
`@fontsource/barlow` 5.3.0 con licenza OFL, è usato per i titoli.

## Come aggiungere un vestito (per esempio in un mirror)

1. **In `stile.css`**, copia i due blocchi di un vestito esistente:
   - `:root[data-vestito="…"]:not([data-theme="light"])`;
   - `:root[data-vestito="…"][data-theme="light"]`.

   Cambia il nome e i colori. Controlla il contrasto: almeno 4,5:1 per testo e link su `--carta` e `--foglio`, e per
   `--su-primario` su `--primario`.
2. **Sempre in `stile.css`**, aggiungi i due colori del campione dell'elenco:
   - `.vestito-elenco li[data-vestito="…"] .asterisco`;
   - la stessa regola preceduta da `[data-theme="light"]`.
3. **Loghi:** crea `logo/<nome>/` con gli stessi 12 file SVG. I quattro colori da sostituire sono nelle note di
   Claude Design: E-G-E, palazzo e lettere, curva, punto.
4. **Nell'HTML di ogni pagina:**
   - aggiungi il nome all'espressione `/^(ambra|indaco|lime|verde)$/` dello script nel `<head>`;
   - aggiungi una voce `<li role="option" …>` nei due elenchi `#vestiti-elenco` e `#vestiti-telefono`.
5. **In `aspetto.js`**, aggiungi il nome in `VESTITI`.
6. **Versione nella cache:** aumenta il numero `?v=` in tutte le pagine.

I report (PDF, Excel e ODS) non cambiano con il vestito. Usano:

- testo nero;
- link in blu scuro #1A3F8F;
- il logo Corallo chiaro;
- `SERIE_STAMPA` in `report.py` per i grafici.
