# Aggiornamento del 16/11/2026 (b) – Trattamento aria divisa in due metà

Seconda pubblicazione del 16/11, sopra la `v2026.11.16`. Sito **`?v=20261116b`**, release **`v2026.11.16b`**.

## Cosa cambia

**Segnalazione di Paolo del 16/11, 11:12**: la correzione della mattina (`?v=20261116a`) non bastava. Le pagine di
Trattamento aria devono essere **divise in due metà, ognuna con la sua barra di scorrimento**, e quella di sinistra deve
avere la barra **sul lato sinistro**, per non sovrapporsi al controllo che sposta la divisione.

- Le quattro pagine (`aria-trasformazioni.html`, `aria-ore.html`, `aria-latenti.html`, `aria-freecooling.html`) ora
  funzionano come **Patrimonio**. Sul computer (oltre 861 px) la pagina sotto la testata è alta quanto la finestra e non
  scorre. A sinistra ci sono titolo, mappa e diagramma; a destra i passi; ognuna delle due metà scorre da sola. La barra di
  sinistra sta sul lato sinistro (`direction: rtl`, come in tutte le pagine a due colonne).
- Il **piè di pagina** (fonti e collegamenti) è in fondo alla colonna sinistra, come in Patrimonio
  (`footer.piede.piede-colonna`). Prima era sotto le due colonne e non si sarebbe più visto.
- Sul telefono, con una sola colonna, non cambia nulla: la pagina scorre tutta insieme.
- Novità: la voce del 16/11 ha il testo nuovo e la versione `20261116b`.

## File toccati (rispetto alla `v2026.11.16`)

- fase 5:
  - `sito/stile.css` (regole `main.pagina-aria`);
  - le quattro pagine `aria-*.html` (piè nella colonna sinistra);
  - `novita.toml`, `novita.html` e `novita.xml`;
  - tutte le pagine portate a `?v=20261116b`;
  - `sito/EUGENIO_PER_AGENTI.md`, `sito/llms.txt` e README.
- `EUGENIO_PER_AGENTI.md` nella radice e questo file.

## Test (16/11/2026, container)

- **Fase 5**: costruzione delle pagine, menu, Esempi e Contributi, file per gli agenti, pagine di Trattamento aria e scelta
  della serie danno 114 test passati e 1 saltato.
- **Browser** (Chromium, 1400×850), nelle quattro pagine come in Patrimonio:
  - il `main` è alto 767 px e la pagina non scorre;
  - la metà sinistra ha `overflow-y: auto` e `direction: rtl`, con 1.650–1.820 px di contenuto;
  - la metà destra ha `overflow-y: auto`, con 6.400–9.100 px di contenuto;
  - il piè di pagina è nella colonna sinistra.
- **Telefono** (400 px): una sola colonna che scorre con la pagina.

## Procedura AB1–AB3

### AB1. [PC] Script
Lo script `pubblica_2026-11-16b.ps1` e la patch `eugenio_2026-11-16b.patch` sono già nel clone (li ha messi Claude).
```powershell
cd C:\Users\ingpa\Documents\claude\pj\statocritico\eugenio
```
```powershell
powershell -ExecutionPolicy Bypass -File .\pubblica_2026-11-16b.ps1
```
Lo script fa questi passi:
1. sposta lo script e la patch fuori dal clone;
2. esegue `git pull`;
3. applica la patch;
4. controlla `?v=20261116b` e che nel commit non ci siano file privati;
5. fa commit e push;
6. crea la release `v2026.11.16b` con le note della prima voce delle Novità.

Cosa aspettarsi: alla fine la riga verde `FATTO`. Se lo script si ferma, scrive in rosso una riga che comincia con
`FERMO:` e dice dove: mandamela.

### AB2. [Server] Aggiornamento da GitHub
```bash
ssh eugenio
```
```bash
tmux ls; ls /srv/energia/dati/psicro/.scarica_in_corso 2>/dev/null; tail -3 ~/scarica_psicro.log
```
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Prima di lanciare lo script, controlla che lo scarico sia finito: non deve esserci il file `.scarica_in_corso` e in fondo al
log ci deve essere il JSON finale. Se lo scarico gira ancora, aspetta.

Cosa aspettarsi dallo script:
- `Aggiornamento da v2026.11.16 a v2026.11.16b` (oppure `da v2026.11.14b`, se AA3 non era ancora fatto: va bene, porta
  dentro anche la `v2026.11.16`);
- `Sito della release: ?v=20261116b`;
- `Release v2026.11.16b installata`.

### AB3. [Browser] Le due metà
1. Apri `https://eugenio.statocritico.it/aria-ore.html` con Ctrl+F5, su un computer.
2. La pagina sotto il menu non scorre. Con la rotella sulla metà destra scorrono solo i passi; sulla metà sinistra scorrono
   solo titolo, mappa e diagramma.
3. La barra della metà sinistra sta sul **bordo sinistro** della finestra; quella della metà destra sul bordo destro.
4. Il divisore al centro si trascina come prima.
5. In fondo alla metà sinistra ci sono le fonti e il piè di pagina.
6. Controlla lo stesso nelle altre tre pagine.
7. Sul telefono non cambia nulla.

## Da riportare in RIEPILOGO.md e DA_FARE.md

- RIEPILOGO, riga di stato: «**16/11/2026 (b)**: sito `?v=20261116b`, release `v2026.11.16b` (AB1–AB3). Trattamento aria
  divisa in due metà come Patrimonio, ognuna con la sua barra di scorrimento (quella di sinistra sul lato sinistro), piè
  nella colonna sinistra.»
- RIEPILOGO, decisioni di Paolo del 16/11: le pagine di Trattamento aria sono divise in due metà, ognuna con la sua barra di
  scorrimento; la barra di sinistra sta a sinistra per non coprire il divisore.
- DA_FARE: [ ] **Paolo**: AB1 subito, AB2 e AB3 a scarico finito; poi Z12, Z13 e Z15 di `AGGIORNAMENTO_2026-11-14b.md`.
