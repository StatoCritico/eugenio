# Stile del sito: vestiti, temi e variabili

Nota tecnica sullo stile grafico di EuGEnio (27/10/2026, aggiornata il 29/10/2026: mappe e barre a mattoncini). Il progetto è di Claude Design, adattato al sito esistente.

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

## Testata e colonne (29/10/2026, terza versione)

- **Testata** (`parti/testata.html`): riga 1 = marchio e «un servizio per uno Stato Critico» a sinistra, voci
  informative (Come funziona … Contattaci) a destra sulla stessa riga; riga 2 = voci dei servizi (Dati climatici,
  Legge 10, Previsioni, Patrimonio, Indicatori) alte `--alto-comando` (36 px) come il pulsante Iscriviti, poi Iscriviti,
  ✱ e ◐ con i cerchi della stessa altezza e sulla stessa linea. Tra 861 e 1060 px frase e voci informative sono più
  piccole; sotto gli 861 px resta il menu del telefono (Iscriviti è nel menu). L'altezza resta in `--alto-testata`.
- **Colonne con scorrimento indipendente** (solo Patrimonio, `main.pagina-patrimonio`, da 861 px; quarta versione):
  `main` è alto quanto la finestra meno la testata e le due colonne scorrono ciascuna per conto suo, **senza barre di
  scorrimento visibili** (`scrollbar-width: none` e `::-webkit-scrollbar`; rotella, tastiera e dito funzionano); la
  maniglia del divisore resta. Il piè di pagina di Patrimonio (`<footer id="piede" class="piede piede-colonna">`, con
  le parti comuni tra i marcatori `<!-- piede -->` come nelle altre pagine) sta in fondo alla colonna sinistra; sul
  telefono `patrimonio.js` lo riporta in fondo alla pagina. Nelle altre pagine dei servizi tutto come prima: mappa a
  sinistra fissa (sticky) che occupa lo spazio disponibile, pagina che scorre, piè a tutta larghezza in fondo.
- **Titoli senza articolo**: «Elenco degli edifici», «Risultato», «Sedi e valori», «Totali», «Comune», «Consumi»…
  (vale per i titoli dei passi e delle sezioni; le domande delle F.A.Q. restano frasi).

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

4. **Anche le tabelle hanno la freccina** (29/10/2026, vale per le tabelle future): ogni contenitore `.tabella-scorre` e
   ogni elemento con `data-riquadro-tabella` (anche creati dopo dagli script: li trova un `MutationObserver`) riceve in
   alto a destra il pulsante `.grafico-apri` («Apri la tabella in un riquadro»). Il riquadro è lo stesso dei grafici
   (classe `con-tabella`): larghezza naturale della tabella se sta nella finestra, altrimenti il 95 % con scorrimento
   interno; altezza al massimo il 95 % della finestra; ✱ e ◐; niente zoom. La tabella vera si sposta nel riquadro e torna
   al suo posto alla chiusura, così caselle e pulsanti funzionano anche lì. Titolo: `data-titolo`, `<caption>` o il
   titolo h2/h3 che la precede. A mano: `EUGENIO_GRAFICI.registraTabella(elemento)`.

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

## Mappe (regole dal 29/10/2026)

1. **Riquadretti.** Tutte le mappe grandi (Previsioni, Patrimonio, Legge 10, Dati climatici) usano un solo meccanismo,
   `EUGENIO.suggerimenti(svg, opz)` in `minimappa.js`, che `mappaGrande()` e `sfondoItalia()` attivano da sole. Passando
   col mouse sopra una **regione non selezionata** compare il suo nome (con «clic per aprirla»); sopra un **comune della
   regione scelta** il nome con la sigla della provincia, e le righe che la pagina mette in `data-dettaglio` (nella
   Previsione i gradi giorno e la temperatura dei prossimi 7 giorni). La piccola mappa accanto al titolo resta com'era.
   - Gli elementi si descrivono con gli attributi `data-nome`, `data-prov` e `data-dettaglio` (righe separate da `\n`);
     niente `<title>` sui percorsi, che farebbe un secondo suggerimento del browser.
   - Il riquadretto è il `<div class="etichetta-mappa">` dentro `.mappa` (creato se manca), con lo stesso aspetto dei
     riquadretti dei grafici: titolo in grassetto, righe in `--tenue`, campione di colore facoltativo.
   - Chi vuole un contenuto diverso passa `{ contenuto(elemento, tocco) }` che restituisce `{ titolo, righe: [[colore,
     testo]] }`, `null` (niente riquadretto) o `undefined` (vale quello predefinito): così fa la mappa 3D per le barre.
   - **Tocco:** il riquadretto compare dove si tocca e sparisce dopo 3,5 secondi o al tocco successivo; il tocco su un
     comune lo sceglie come prima (Legge 10, Previsioni, Dati climatici). Su una **regione vicina** il primo tocco mostra
     solo il nome («tocca di nuovo per aprirla») e il secondo, entro 4 secondi, la apre: sul telefono non si cambia
     regione per sbaglio. Durante il trascinamento e lo zoom il riquadretto si spegne.
2. **Patrimonio: solo la regione scelta, in tre dimensioni** (`mappa3d.js`, `EUGENIO_MAPPA3D.crea(box)`). La mappa
   grande mostra i comuni della regione scelta (stesso fondo delle altre pagine, `EUGENIO.fondoComuni`) e il contorno
   della regione, senza le regioni vicine; la regione cambia solo dalla piccola mappa (la freccia ↓ lì è nascosta).
   - I percorsi di `dati/mappa/RR.json` (solo `M`, `L`, `Z`) diventano poligoni; ogni punto passa per una matrice di
     rotazione (imbardata attorno alla verticale, inclinazione da 0° = dall'alto a 80°, rollio dell'immagine) e una
     prospettiva leggera (distanza 2,6 volte la regione). A ogni fotogramma (`requestAnimationFrame`) si riscrivono i
     percorsi; durante il movimento i poligoni lunghi usano un punto su due e le barre sono senza linee dei mattoncini.
   - Comandi (dal 29/10/2026, terza versione): **trascinamento = spostamento** (come nelle altre mappe);
     Ctrl (o ⌘, o tasto destro)+trascinamento = imbardata e inclinazione; Ctrl+Maiuscolo+trascinamento = rollio;
     Alt+trascinamento = vista delle barre; tasto centrale = spostamento; rotella = zoom attorno al puntatore; doppio
     clic = vista iniziale. Dito: uno sposta, due ingrandiscono, ruotano e spostano. Tastiera sulla mappa: frecce =
     spostamento, Ctrl+frecce = rotazione e inclinazione, Ctrl+Maiuscolo+frecce = rollio, Alt+frecce = barre, `+`, `-`, `0` (dall'alto),
     `3` (vista 3D), `I` (isometrica). Sotto la mappa ci sono i pulsanti (zoom, «Dall'alto», «3D», «Isometrica»,
     ruota, inclina, rollio e, con due mappe, «Copia la vista sull'altra mappa»).
   - Vista «Dall'alto» = come le altre pagine; vista «3D» predefinita = imbardata −20°, inclinazione 55°, con lo
     zoccolo della regione (spessore costante di circa 12 pixel). La pagina si apre dall'alto e passa alla vista 3D
     quando si caricano i valori per sede. **Inquadratura delle viste predefinite** (`adatta()`, all'apertura con i valori,
     «Dall'alto», «3D», «Isometrica», doppio clic): zoom e centro calcolati sulle proiezioni sullo schermo di mappa
     visibile, zoccolo, punti e cime delle barre, con un bordo del 5 % della finestra su ogni lato (qualche passaggio,
     perché le barre crescono un po' con lo zoom). Vista «Isometrica» (da videogioco, 29/10/2026): proiezione **ortografica**
     (`prospettiva: false`), imbardata −45° (il **nord in alto a destra**), inclinazione 60° cioè mappa vista 30° sopra l'orizzonte, così un quadrato
     della mappa diventa un rombo largo il doppio dell'alto (il 2:1 dei videogiochi; l'isometria «vera» a 35,26° darebbe
     1,73:1); barre allineate agli assi della mappa (rotazione 0 che segue l'imbardata) e viste anche loro a 30°. Il
     resto della grafica non cambia.
   - **Colori delle regioni** (quarta versione, richiesta di Paolo): le regioni restano colorate come nelle altre mappe
     (`fondoRegione`: nel tema scuro `EUGENIO.fondoComuni`, il colore della regione schiarito; nel chiaro il colore della
     regione mescolato al 55 % col bianco). Con **più di 10 regioni visibili** tutte grigie (`fondoNeutro()`: `--bordo`
     mescolato con `--carta`, circa rgb(92,88,100) nel tema scuro e rgb(201,197,206) nel chiaro). `coloriVisibili()`
     dice alle barre quali colori di fondo evitare.
   - **Riquadretto sulle aree senza comuni**: le sagome delle regioni hanno `data-nome` (con «regione» o «regione
     scelta»), quindi nelle province senza comuni disegnati compare il nome della regione; nelle altre pagine la regione
     scelta mostra il suo nome dove non ci sono comuni sopra (vuoti lungo i confini).
   - **Più regioni** (`scena({ sagome, comuni })`, 29/10/2026): con i valori per sede la mappa mostra le regioni intere
     che contengono sedi (sagome col loro fondo, contorno e zoccolo comuni) e, sopra, i comuni delle sole province con
     sedi con dati; inquadratura automatica sul loro insieme. La piccola mappa allora cambia solo la regione ricordata e
     i collegamenti (`EUGENIO_PATRIMONIO.territorioAutomatico`). `regione(dati)` resta il caso di una sola regione.
   - L'esportazione (`esporta()`) copia l'SVG e scrive come attributi i colori e gli spessori calcolati dal CSS: fuori
     dal sito `var(--…)` non vale. La copia piatta è `EUGENIO_MAPPA3D.appiattisci(svg, leggero)` (anche per i Pareto):
     toglie classi, dati e strati di servizio, scrive i numeri senza «px» (fpdf2 non li legge); `leggero` (report)
     porta gli attributi comuni sul gruppo e `esporta({ leggero: true })` scrive coordinate intere senza i punti a meno
     di un pixel dal precedente.

### Barre a mattoncini (Patrimonio, «Valori per sede», `valori_sedi.js`)

- **Barre di fronte** (terza versione): la fila di barre di ogni sede è frontale sullo schermo (`rotazione` 0) e ogni
  barra è girata di 30° su se stessa (`torsione`), così si vedono due facce. Con «Le barre ruotano insieme alla mappa»
  **spenta (predefinito)** girando la mappa le barre «controruotano»: ogni gruppo resta con lo stesso orientamento e la
  stessa spaziatura sullo schermo, attorno al punto della sede; accesa, la fila gira con la mappa. Il pulsante «Barre di
  fronte» azzera la rotazione propria delle barre (`barreDiFronte()`). Nella vista isometrica la fila va lungo gli assi
  della mappa, senza torsione.
- **Colori delle barre** (quarta versione): famiglie di tinte per tipo di consumo: **elettricità = verdi**, **gas ed
  energia termica = gialli, arancioni e rossi**, **acqua = azzurri**, **rifiuti, combustibili ed emissioni =
  marroni**, le altre colonne colori liberi. Il tipo si riconosce prima dal nome, nell'ordine: marrone (rifiuti,
  combustibil…, gasolio, olio, pellet, legna, emissioni, CO2/CO₂, anidride carbonica), elettricità (elettric, luce,
  EE, energia attiva), termica (gas, metano, Smc, termic, calore, riscaldamento, vapore, GPL, servizio energia, «S.E.»
  o «SE» come parola a sé), acqua (acqua, idric); se il nome non basta, dall'unità (kg, t, ton, tonnellate, tCO2,
  kgCO2 → marrone; kWh → elettricità; MWh e Smc → termica; m³ e litri → acqua). Dentro la famiglia si sceglie la
  tonalità più lontana (ΔE CIE76) dai colori delle regioni visibili e diversa da quelle già date (due colonne
  elettriche = due verdi distinti); i costi ereditano il colore del consumo abbinato. Il menu del colore offre le
  tonalità delle quattro famiglie e poi gli altri colori.
- **Grattacieli.** La base di ogni sede si proietta con la camera della mappa; la barra si disegna sempre in piedi
  (dal basso verso l'alto dello schermo) come un parallelepipedo con una vista sua: rotazione delle barre (che segue
  l'imbardata della mappa se è spuntato «Le barre ruotano insieme alla mappa») e inclinazione delle barre, regolabili
  dai cursori o con Alt+trascinamento. Facce in tre toni dello stesso colore (tetto schiarito del 30 %, un fianco pieno,
  l'altro scurito del 30 %), linee dei mattoncini più scure, ordine dal fondo al davanti (algoritmo del pittore: prima
  le sedi più in alto sullo schermo, nel gruppo prima le barre più lontane). Più colonne della stessa sede = barre
  affiancate in fila, centrate sulla sede. La prospettiva rimpicciolisce le barre lontane.
- **Unità.** Riga delle unità: se la riga subito sotto i titoli ha solo testo non numerico nelle colonne dei valori, è
  quella delle unità; altrimenti l'unità si cerca nel titolo tra parentesi. Le unità con multipli (Wh…TWh, W…GW,
  J…TJ, g/kg/t, litri e m³, € e k€) si portano all'unità base: kWh e MWh sono la «stessa unità». Senza unità ogni
  colonna ha la sua scala.
- **Scale.** Stessa unità = stessa scala e stesso mattoncino. Unità diverse = una scala per unità: il valore più alto
  di ciascuna arriva all'altezza massima (circa il 28 % del lato corto della mappa, cursore «Altezza delle barre»).
- **Mattoncino.** Vale il più piccolo numero tondo 1, 2, 2,5 o 5 × 10^k (nell'unità più comoda: 2 GWh, non 2.000 MWh;
  litri e m³ restano come nel file) tale che il valore più alto stia in **20 mattoncini al massimo**. I mattoncini sono
  cubi (altezza = lato della base). **Tutte le barre di una mappa hanno la stessa base** (decisione di Paolo, 29/10/2026):
  il lato è l'altezza massima divisa per i mattoncini della scala che ne ha di più; le scale con meno mattoncini arrivano
  più in basso, quindi barre di unità diverse hanno altezze massime diverse. L'ultimo mattoncino in cima è
  parziale.
- **Colori.** All'inizio i sei colori `--serie-1…6` del vestito, prima quelli che si staccano di più dal fondo dei
  comuni; ogni colonna di costo prende il colore del consumo abbinato (stessa posizione). Per ogni colonna si può
  scegliere un altro colore (anche fissi: blu, turchese, verde, viola, arancio, rosso, grigio) e spegnere le barre,
  dalla legenda sotto la sua mappa o dalla casella nel titolo della colonna in tabella. I toni delle facce si rifanno
  all'evento `eugenio:aspetto`.
- **Sedi nello stesso punto** (centro del comune, o coordinate entro circa 100 m): in fila lungo la profondità della
  vista delle barre, la più grande in fondo e la più piccola davanti (`pila: { rango, n }` del gruppo), così si
  vedono tutte.
- **Disegno SVG.** «Scarica il disegno (SVG)» salva la vista così com'è, piatta: titolo, legenda dei colori, valore del
  mattoncino, «Fonte: EuGEnio – eugenio.statocritico.it» con la data e l'attribuzione di Zornade, ANNCSU e ISTAT.
  Con due mappe ci sono due pulsanti (consumi, costi).

### Valori per sede (seconda versione, 29/10/2026)

- **Passi** (terza versione): Elenco degli edifici, Risultato, Sedi e valori, Totali, Costi unitari medi, Consumi per
  sede, Costi per sede, Vista tridimensionale, Generazione del report. Le legende sotto le mappe hanno una riga per
  colonna (casella, colore, nome, «1 mattoncino = …»); «Consumi» e «Costi» sopra le mappe hanno lo stile dei titoli dei
  passi; i pulsanti Accendi/Spegni/Ripristina sono piccoli e sotto le tabelle; le schede dei Pareto vanno a capo
  (nessuna barra di scorrimento).
- **Un solo flusso nella colonna destra**, senza schede: passi numerati di seguito (`EUGENIO_PATRIMONIO.numeraPassi()`
  numera i passi visibili): l'elenco degli edifici, il risultato, le sedi con i valori (`#valori`), i totali, i costi
  unitari medi, i consumi per sede (tabella + Pareto), i costi per sede (tabella + Pareto), la vista delle barre e il
  report. Il colore e la casella «mostra» di ogni colonna stanno nella legenda sotto la sua mappa (vicino a ciò che
  cambiano); la casella «mostra» c'è anche nel titolo della colonna in tabella, e le due restano allineate.
- **Valute** = costi: unità con un simbolo o un codice di valuta (€, EUR, euro, €/anno, k€, migliaia di euro, $, USD,
  £, GBP, CHF, ¥, JPY, CNY, ₹, zł…), anche tra parentesi nel titolo, oppure simboli accanto ai numeri in almeno metà
  delle celle («€ 1.234,56»). Le altre colonne sono consumi. Con entrambi: due mappe nella colonna sinistra (sopra i
  consumi, sotto i costi, `.mappa-area.due-mappe`, non più fissa), due tabelle, due riquadri di Pareto; con un solo
  tipo una sola mappa.
- **Abbinamento per posizione**: la i-esima colonna di consumo (da sinistra) va con la i-esima di costo; costo unitario
  medio = Σ costi / Σ consumi sulle sole sedi con entrambi i valori, in unità composta (valuta/unità del consumo: €/MWh,
  €/Smc, €/m³); per l'energia sempre **€/MWh con 2 decimali**, anche se i consumi sono in kWh (decisione di Paolo, 29/10/2026: il
  file d'esempio mostra 302,38 €/MWh); gli altri prezzi con 3 decimali sotto 10; `k€` si porta in €. Nella tabella dei costi, a richiesta, anche il costo unitario di ogni sede.
- **Territorio**: regione di ogni sede con le coordinate (punto nel poligono della regione, altrimenti la più vicina);
  sedi senza coordinate col comune riconosciuto → **centro del comune** (`x`, `y` di `RR.json`, cercato prima nelle
  regioni delle altre sedi, poi nelle altre), segnalato in tabella («posizione: centro del comune»); comune e provincia
  di ogni sede col punto nel poligono del comune.
- **Sedi accese**: casella sull'intestazione di riga (tutte e due le tabelle, allineate) e pulsanti «Accendi tutte»,
  «Spegni tutte», «Ripristina» per le sedi e per le colonne di ogni tabella. Scelta automatica (e «Ripristina»): in un
  comune con più di tre sedi con dati sono accese le **tre col valore più alto nella prima colonna di consumo** (se
  manca, nella prima colonna con un valore; scelta documentata: sommare colonne di unità diverse non ha senso); le
  altre restano in tabella, spente. **Totali e Pareto usano sempre tutte le sedi del file**; le mappe solo le accese.
- **Totali** (`table.totali`, cifre grandi): somma di ogni colonna, prima i consumi e poi i costi, con il numero di
  sedi che hanno il dato.
- **Pareto**: un riquadro a schede (una per colonna) per i consumi e uno per i costi; ogni scheda è un grafico di
  `grafici.js` (`registra` con il pulsante ↗, `osserva` col riquadretto): sedi in ordine decrescente a barre, curva
  cumulata in % sull'asse destro, linea dell'80 % (`--segno`, tratteggio `7 4`), frase «le prime k sedi su n fanno
  l'80 %».
- **Report** `valori_sedi` (PDF, Excel, ODS con `report.js`): totali e costi unitari medi, mappe, Pareto dei consumi e
  dei costi, tabelle dei consumi e dei costi. Mappe e Pareto vanno al server come SVG piatti in base64 disegnati coi
  **colori di stampa** (tema chiaro, vestito Corallo, applicati e tolti nello stesso istante con le transizioni spente:
  l'utente non vede nulla). In Excel e ODS solo totali e tabelle.
- **File d'esempio** (`esempi/valori_sedi_esempio.csv`, generato con seme fisso): 13 ospedali con energia elettrica
  (kWh, da 500.000 a 14.000.000), gas (Smc), acqua (m³) e i tre costi (€) nello stesso ordine; il prezzo
  dell'elettricità va da 280 a 320 €/MWh (costo = kWh / 1000 × prezzo). La prima riga è una nota che comincia con `#`
  (ignorata da valori e geolocalizzazione) e fa riconoscere il file: allora l'avviso «Dati di esempio non reali»
  compare in fondo alla colonna sinistra (subito prima delle fonti «Particelle catastali…»), sotto i titoli di
  totali e tabelle e in cima al report. Titolo «Dati di esempio non reali» (senza virgola).

## File caricati (`tabelle.js`, dal 29/10/2026)

Tutti i campi di caricamento accettano CSV e TXT, Excel (`.xlsx`) e OpenDocument (`.ods`). `EUGENIO_TABELLE.leggi(file)`
riconosce il tipo dall'estensione e dai primi byte (`PK` = archivio zip, cioè xlsx o ods; `D0 CF 11 E0` = vecchio `.xls`):
i CSV si leggono nel browser (UTF-8, altrimenti Windows-1252), i fogli di calcolo vanno a `/api/converti`, che restituisce
il primo foglio come CSV col punto decimale; se i fogli sono più di uno la pagina lo dice («è stato letto il primo,
«X»»). Il `.xls` si ferma con un messaggio che chiede di salvarlo come `.xlsx`, `.ods` o `.csv`. La Previsione manda il
file al server così com'è (anche `/api/previsione` legge xlsx e ods) e controlla solo il `.xls`.

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
