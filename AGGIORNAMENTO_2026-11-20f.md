# Aggiornamento del 20/11/2026 f – Mercato del giorno prima del GME: offerte pubbliche, curve, liquidità, transiti

Ramo `claude/2026-11-20-mercato-mgp`. Cambiano la fase 6 (`mercati_energia/mgp.py`, `mgp_notturno.py`, configurazione,
archivio, comandi) e il worker della fase 4 (lavoro nuovo `mercato-mgp`). **Il sito non cambia**: nessuna versione nuova
`?v=`, nessuna voce nelle Novità.

> **SOLO USO INTERNO.** Offerte pubbliche, curve di domanda e offerta, liquidità, transiti e fabbisogno del GME restano in
> `/srv/energia/dati/mercati` sul server (cartella non servita da Caddy): mai sul sito, mai esportati, mai nella newsletter,
> nessuna rotta API, finché non c'è una licenza scritta del GME.

## Cosa cambia

- Prezzi (PUN Index GME e zonali) e quantità acquistate e vendute per zona c'erano già (lavoro `mercati` delle 02:30).
- Lavoro nuovo **`mercato-mgp`**, ogni notte alle **04:15** (ora italiana; `ORA_MERCATO_MGP` nel `.env` per cambiarla),
  al massimo 45 minuti, con le stesse credenziali GME del lavoro `mercati` (`GME_UTENTE`, `GME_PASSWORD`, già nel `.env`):
  - **liquidità, transiti, fabbisogno** (archivio annuale), con lo storico all'indietro fino al 2004;
  - **curve aggregate di domanda e offerta** per zona e livello di prezzo (un file al giorno) e **offerta e domanda
    totali** per zona e periodo, dal 1/10/2025;
  - **offerte pubbliche** MGP, tutte (accettate e no), una riga per offerta, un Parquet al giorno in
    `/srv/energia/dati/mercati/mgp_offerte/AAAA/AAAA-MM-GG.parquet`: ogni notte il giorno nuovo (oggi − 8, il GME le
    pubblica dopo 7 giorni) e **3 giorni di storico**, con 20 secondi di pausa fra le richieste, fino al 1/10/2025.
- Funzione interna delle **curve ordinate** di offerta e domanda (giorno, periodo, zona o Italia): restituisce i dati per
  le analisi, non li mostra da nessuna parte.
- **Email** all'amministratore solo per: credenziali GME rifiutate, una serie ferma da più di 4 giorni, disco sotto gli 8 GB
  liberi, lavoro fallito 3 notti di fila; una volta per episodio.
- **Spazio stimato**: 4–20 MB al giorno di offerte, ~1,5–7 GB all'anno; con lo storico dal 1/10/2025 ~2–8 GB in tutto. Lo
  storico si ferma da solo oltre 12 GB di offerte o sotto gli 8 GB liberi.
- Prove: fase 6 68 passate (1 fallita anche prima di questo ramo: `test_tabella_arera_2022_23_e_storico`, manca il file
  `mercati_energia/dati/psv_da_arera_2022_2023.csv`, escluso da `.gitignore`); fase 4 359 passate (con `PYTHONPATH` sulle
  fasi 3, 4, 6, 7, 8, 10).

## Procedura MGP1–MGP6

### MGP1. [Browser] Merge e release
1. Apri la pull request del ramo `claude/2026-11-20-mercato-mgp` su https://github.com/StatoCritico/eugenio/pulls, scheda
   **Files changed**, poi **Merge pull request** → **Confirm merge**.
2. Pubblica la release successiva su https://github.com/StatoCritico/eugenio/releases/new (tag del giorno, per esempio
   `v2026.11.20f` se è libero) e premi **Publish release**.

### MGP2. [Server] Aggiornamento
```bash
~/energia/fase4-server/aggiorna_da_github.sh
```
Cosa aspettarsi: `Release v2026.11.20… installata`, api «healthy», worker ricreato. Niente da copiare a mano: la
sezione `[mgp]` del `config.toml` è facoltativa (valori predefiniti in `fase6-mercati/config.example.toml`).

### MGP3. [Server] Credenziali e spazio
```bash
grep -c '^GME_UTENTE=' ~/energia/fase4-server/.env
grep -c '^GME_PASSWORD=' ~/energia/fase4-server/.env
df -h /srv/energia/dati
```
Cosa aspettarsi: `1` e `1` (le righe ci sono; il comando non stampa i valori) e, nella colonna `Avail`, almeno 15–20 GB.
Se mancano le righe, il lavoro non fa nulla e non manda email.

### MGP4. [Server] Prima esecuzione (facoltativa, altrimenti parte da sola alle 04:15)
```bash
cd ~/energia/fase4-server
docker compose run --rm worker python -m servizio.worker mercato-mgp
```
Dura fino a 45 minuti (il limitatore dell'API aspetta fra una richiesta e l'altra). Cosa aspettarsi alla fine, nel
registro: una riga `MGP: righe {'mgp_liquidita': …, 'mgp_transiti': …, 'mgp_fabbisogno': …, 'mgp_domanda_offerta': …,
'mgp_offerte': …}, errori N, da segnalare 0`. Righe `GME: limite di … raggiunto in locale, attendo …` sono normali.

### MGP5. [Server] Stato dell'archivio (il mattino dopo)
```bash
cd ~/energia/fase4-server
docker compose run --rm worker python -m mercati_energia -c /dati/mercati/config.toml mgp-stato
```
Cosa aspettarsi: una riga per serie con il primo e l'ultimo giorno e i MB occupati, per esempio
`mgp_offerte  dal 2025-11-0… al 2025-11-12  4 giorni  …  MB`, e in fondo lo spazio libero. Il comando stampa solo date e
dimensioni, nessun valore dei dati. **Segnare a Claude la dimensione di un giorno di offerte** (MB ÷ giorni): serve a
confermare la stima dello spazio.

### MGP6. [Server] Se le offerte non arrivano
Se dopo due notti `mgp_offerte` ha `0 giorni` o compare `non scaricati: …`, guardare gli errori dell'ultima notte:
```bash
sudo python3 -c "import json; e=json.load(open('/srv/energia/dati/mercati/mgp_ultima_esecuzione.json')); print('\n'.join(e['errori'][-10:]))"
```
Un errore con «quot» o «limit» vuol dire che il GME respinge un giorno intero di offerte per le quote dell'API: riferirlo a
Claude (l'alternativa è il server FTPS del GME, `ftps://download.ipex.it`, con credenziali da chiedere al GME).

## Da verificare con le credenziali vere (non provato dal vivo)
- che una richiesta `Offers_PublicDomain` di un giorno rientri nelle quote dell'API;
- i valori del campo `Type` delle curve aggregate (`ME_DemandAndSupply`) e il separatore decimale degli XML delle offerte;
- quanto storico restituisce l'API per le offerte e le curve.
