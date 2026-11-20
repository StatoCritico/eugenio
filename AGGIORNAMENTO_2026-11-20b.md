# Aggiornamento del 20/11/2026 b – Comunità energetiche con le aree del GSE, verifica MASE, terreno sul server

Pubblicazione sopra la `v2026.11.20`. Sito **`?v=20261120b`**, release **`v2026.11.20b`**. Nelle Novità solo il collegamento LiDAR: la
pagina Comunità energetiche resta «in lavorazione». Tre lavori fatti in parallelo e riuniti in una sola pull request
(richiesta di Paolo del 20/11, 07:45). L'aggiornamento automatico ricrea già api e worker: niente da fare a mano oltre
alla prova facoltativa.

## 1. Comunità energetiche (`edificio-cer.html`, ancora in lavorazione)

- **Sedi**: a mano (nome, latitudine, longitudine) o da un elenco CSV/Excel/ODS (colonne `sede`, `lat`, `lon`, facoltative
  `cabina` e `istat`, al più 200 righe). Per ogni sede il browser chiede al servizio pubblico del GSE l'area
  convenzionale e **precompila il `COD_AC`** nel campo «Cabina» (modificabile), con l'avviso «proposta dalla mappa del GSE
  dalle coordinate; in caso di dubbio vale la ricerca per POD». A meno di 50 m dal confine mostra le due aree; fuori da
  ogni area (isole minori, SDC, mare) un avviso. Elenchi: al più 4 domande al GSE alla volta; risposte tenute solo in
  memoria finché la pagina è aperta; una cabina scritta nel file non si sostituisce.
- **Cabine del comune**: menu delle cabine e-distribuzione del comune della sede (nome, `COD_AC`, saturazione) dalla rotta
  esistente `/api/rete/cabine/comune/{istat}`; comuni di un altro distributore: avviso e rimando alla mappa del GSE;
  con trasformatori e-distribuzione «servito in parte da un altro distributore», mai «non concessionario».
- **Strato «Aree convenzionali (GSE)»** sulla mappa: spento in partenza, da zoom 10, contorni con il codice, riquadro al
  clic (codice, gestore, data di consegna, collegamento al GSE), attribuzione «© GSE S.p.A. – CC BY-NC-SA 3.0 IT» fissa
  quando è acceso; spento nelle immagini scaricate.
- **Calcolo e file**: la colonna `cabina` del file orario è facoltativa (vale quella della sede); nei CSV, Excel, ODS e PDF
  solo il codice con la nota «area convenzionale proposta dalla mappa del GSE; verifica ufficiale: GSE».
- **Server**: nessuna rotta nuova; `/api/rete/stato` dice anche l'indirizzo del servizio del GSE (`URL_GSE_AREE` in
  `rete.py`, uguale a quello di `rete.js`, controllato da una prova). **Lavoro nuovo del worker `gse-aree`**: il **3 di
  ogni mese alle 7** (ora italiana; `GSE_CONTROLLO_GIORNO`, `GSE_CONTROLLO_ORA`), una sola domanda `?f=json`, nessun dato
  salvato, email solo se il servizio non risponde (accorgersi del cambio a `AC_Comuni_2027`).

## 2. Verifica MASE (16/11) nei file

`zone/rimini.toml`, voce `[fonti.pnrr_dsm]`: verifica del 16/11 (app https://sim.mase.gov.it/pst/ online, nessun livello
PNRR, nessuna scheda nel RNDT, licenza PNRR non scritta), scheda con il nuovo indirizzo, fonte sempre spenta «in attesa».
Nuovo indirizzo anche nel README della fase 10 e nella pagina LiDAR (`lidar.html`).

## 3. Terreno sul server

Paragrafo «Come si aggiunge un DTM sul server» nel README della fase 4 (rimando da quello della fase 10): COG generato nel
container con `dtm-server` oppure copiato con `sudo cp` + `sudo chown 1000:1000`, rilettura ogni 5 minuti, verifica con
`/api/terreno/fonti` e `X-Terreno-Nome`. Regola nel README generale per le procedure.

## Prove

Fase 5 completa sul ramo della pagina: 227 passate, 2 saltate; fase 4 `test_rete.py` e `test_worker.py`: 43 passate (9
nuove); fase 10 (zone, fonti, edifici): 53 passate; dopo l'unione dei tre rami: fase 5 completa 227 passate e 2 saltate (con la voce di Novità), fase 4 43
passate, fase 10 25 passate.

## Procedura AO1–AO3

### AO1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/2026-11-20-cer-mase-terreno` (collegamento di Claude), scheda **Files changed**,
   poi **Merge pull request** → **Confirm merge**.
2. Apri il collegamento `https://github.com/StatoCritico/eugenio/releases/new?…` già compilato da Claude (tag
   `v2026.11.20b`) e premi **Publish release**. (Se la `v2026.11.20` non è ancora pubblicata, prima quella: AN2.)

### AO2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Release v2026.11.20b installata` e il Purge di Cloudflare fatto (api e worker ricreati dallo script).

Facoltativo, prova del controllo mensile del GSE:
```bash
cd ~/energia/fase4-server && docker compose run --rm worker python -m servizio.worker gse-aree
```
Cosa aspettarsi: una riga che dice che il servizio del GSE risponde; nessuna email.

### AO3. [Browser] Prova (pagina in lavorazione: si apre dall'indirizzo, non dal menu)
1. Apri https://eugenio.statocritico.it/edificio-cer.html con **Ctrl+F5**.
2. Aggiungi una sede a mano, per esempio «Prova», 44.4949, 11.3426 (Bologna): nel campo «Cabina» deve comparire
   `AC001E00693` con la nota del GSE, e il menu delle cabine del comune.
3. Accendi «Aree convenzionali (GSE)» e avvicinati (zoom 10 o più): contorni con i codici e, sotto la mappa, l'attribuzione
   del GSE; clic su un'area → codice, gestore, data, collegamento.
4. https://eugenio.statocritico.it/lidar.html: il collegamento «Banca dati PST e LiDAR PNRR» porta a
   https://sim.mase.gov.it/pst/.
