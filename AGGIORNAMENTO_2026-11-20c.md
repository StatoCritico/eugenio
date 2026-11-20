# Aggiornamento del 20/11/2026 c – Comunità energetiche con la struttura delle altre pagine

Pubblicazione sopra la `v2026.11.20b`. Sito **`?v=20261120c`**, release **`v2026.11.20c`**, voce nelle Novità. Cambiano
solo il sito (`edificio-cer.html`, `cer_sedi.js`, `stile.css`, versione di tutte le pagine), i testi per gli agenti e le
prove: niente da fare a mano sul server oltre all'aggiornamento.

## Segnalazione di Paolo (20/11/2026, 08:49)

«No, la pagina si è scombinata. Mappa e comandi a sinistra, con ortofoto, istruzioni ed esiti delle selezioni a destra,
layer spegnibili accendibili (ortofoto, edifici, catasto), righello per misure, barre di scorrimento distinte, come le altre
pagine. Segui le regole, sono generali (salvo dove ti dico io di non seguirle).»

La pagina era rimasta un articolo a colonna unica (com'era prima della `v2026.11.20b`), con la mappa in mezzo al testo.

## Cosa cambia

- **Due metà con la loro barra di scorrimento**, come Cabine primarie, Ortofoto e Modelli 3D (`main.strumento`).
- **A sinistra**: titolo e minimappa dell'Italia, **mappa con l'ortofoto** (fonte scelta da sola nel punto, menu per
  cambiarla, contesto Sentinel-2, anni AGEA nella citazione), **comandi** «Sposta» / «Aggiungi sedi» (ogni clic aggiunge una
  sede e cerca la sua area del GSE) e «Togli tutte le sedi», **livelli accendibili**: aree convenzionali del GSE, confini
  delle particelle catastali, contorni degli edifici; **righello**; frecce per allineare l'ortofoto; legenda, attribuzioni,
  immagine della mappa e fonti.
- **A destra**: avviso sperimentale, istruzioni, **ricerca** (indirizzo, foglio e particella, comune), sede con le
  coordinate, elenco delle sedi, **tabella con cabina e menu delle cabine del comune**, dati orari, energia condivisa,
  scarica, come si calcola.
- Il modo di prova (`?prova=1`) mette il suo avviso nel pannello di destra.
- Restano le regole del GSE: aree lette dal browser, mai nelle immagini né nei file (solo il codice).
- Prove: fase 5 completa 227 passate, 2 saltate.

## Procedura AP1–AP3

### AP1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/2026-11-20-cer-struttura` (collegamento di Claude), scheda **Files changed**, poi
   **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.20c`) e premi **Publish release**.

### AP2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Aggiornamento da v2026.11.20b a v2026.11.20c`, `Release v2026.11.20c installata` e il Purge di Cloudflare
fatto.

### AP3. [Browser] Prova
1. Apri https://eugenio.statocritico.it/edificio-cer.html con **Ctrl+F5**: a sinistra la mappa con l'ortofoto e sotto i
   comandi, a destra le istruzioni; le due metà scorrono ognuna per conto suo.
2. Premi «Aggiungi sedi» e fai clic su un edificio a Bologna: nella tabella a destra compare la sede con il codice
   dell'area (es. `AC001E00693`) e il menu delle cabine del comune.
3. Accendi «Aree convenzionali (GSE)», «Confini delle particelle catastali» e «Contorni degli edifici» e avvicinati: contorni
   delle aree con il codice, particelle ed edifici da zoom 16. Prova il righello e il menu dell'ortofoto.
4. Cerca un indirizzo nel passo 1 a destra: la sede si aggiunge e la mappa ci va.
