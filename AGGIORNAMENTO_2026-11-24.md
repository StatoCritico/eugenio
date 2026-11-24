# Aggiornamento del 24/11/2026 – CER – Sviluppo impianti FV (prima fase, fino alle uscite A e B)

Ramo `claude/2026-11-24-cer-fv`, **non ancora in una release** (regola del 20/11: release solo al via di Paolo; versione
del sito ancora `20261123b`, nessuna voce di Novità). Richiesta di Paolo del 24/11 (01:04): «fai la prima fase della
procedura intera (fino ad A+B), in una nuova pagina "CER - Sviluppo impianti FV" dentro fotovoltaico. usa i dati delle
colture per valutare i terreni pubblici: non li cediamo, pubblichiamo solo un indicatore di "probabilità di coltura DOP"».

Fatto:

- **Pagina** `fv-cer.html` (Fotovoltaico, dopo Cabine primarie, sperimentale): edifici (formato di Patrimonio) e curve di
  carico (tre formati) letti nel browser → area del GSE di ogni edificio (dal browser) → per area curve sommate, clima del
  comune della cabina, **potenza FV + accumulo** più alta con la quota condivisa minima (bisezione), impianti da 1 MW al
  massimo, superficie → **A** terreni pubblici adatti con la probabilità di coltura DOP o certificata, punteggio e verifica
  dell'area del GSE → **B** cabine per la manifestazione di interesse, avviso tipo in PDF e modulo CSV → file con i soli
  codici del GSE. Esempi sintetici `esempi/cer_fv_sedi_esempio.csv` e `cer_fv_curve_esempio.csv`.
- **Fase 17** `fase17-cer-fv/`: `python -m cer_fv terreni` costruisce `terreni_pubblici_<anno>.sqlite` dagli immobili
  delle PA (solo terreni in proprietà) con l'indicatore calcolato sui **piani colturali grafici di AGREA**, che restano sul
  server e non si cedono. Regole in `cer_fv/regole_colture.toml`.
- **Server**: rotte `/api/cer-fv/info` e `/api/cer-fv/terreni` (`servizio/cer_fv.py`, limite `cer_fv` 600 all'ora);
  `aggiorna_da_github.sh` copia anche `fase17-cer-fv`.

Prove: `fase5-sito/tests/test_fv_cer.py` (file, calcolo con Node, pagina in Chromium con `?prova=1`), suite della fase 5,
`fase17-cer-fv/tests` (4), `fase4-server/tests/test_cer_fv.py`, `test_protezione.py`, `test_aggiorna_da_github.py`.

## Passi (dopo il via di Paolo: pull request, Merge e release come sempre)

Senza il file dei terreni la pagina funziona fino alla potenza per cabina e alla parte B; la parte A dice «i terreni
pubblici non sono ancora sul server».

**CF1 – Browser (PC)**: apri https://agrea.regione.emilia-romagna.it/servizi/documentazione/open-data-sullutilizzo-del-suolo-1
e scarica i **piani colturali grafici** delle 9 province per le **ultime tre campagne concluse** (es. 2023, 2024, 2025).
Deve comparire uno zip per provincia e anno.

**CF2 – PC**: metti gli zip in tre cartelle con il nome dell'anno, per esempio `C:\Users\ingpa\Documents\claude\agrea\2024\`.
Non aprirli: il costruttore legge gli zip (anche zip dentro zip).

**CF3 – PC (PowerShell)**: copia le cartelle sul server (stesso comando che usi per gli altri file, cambiando l'utente o
l'indirizzo se diversi):

```powershell
scp -r C:\Users\ingpa\Documents\claude\agrea ubuntu@<server>:/tmp/agrea
```

**CF4 – Server**: sposta i file nella cartella dei dati (non è servita dal sito e non va nel repository):

```bash
sudo mkdir -p /srv/energia/dati/agrea /srv/energia/dati/cer_fv
sudo cp -r /tmp/agrea/* /srv/energia/dati/agrea/ && ls /srv/energia/dati/agrea
```

Deve comparire l'elenco degli anni (`2023 2024 2025`).

**CF5 – Server**: aggiungi `pyshp` al venv della fase 7:

```bash
~/energia/fase7-territorio/.venv/bin/pip install -r ~/energia/fase17-cer-fv/requirements.txt
```

**CF6 – Server**: costruisci i terreni (qualche minuto; alla fine un riepilogo JSON con `particelle`, `con_indicatore` e
`campagne_agrea`):

```bash
cd ~/energia/fase17-cer-fv && PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv terreni \
    --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /tmp/cer_fv
```

Se scrive «nessun campo della coltura (DESC_COLT/DESC_USO)» per un file, mandami le prime righe del suo `.dbf` (i nomi
dei campi potrebbero essere diversi da quelli del tracciato del 2018).

**CF7 – Server**: copia il file per l'api:

```bash
sudo cp /tmp/cer_fv/terreni_pubblici_*.sqlite /srv/energia/dati/cer_fv/ && sudo chown -R 1000:1000 /srv/energia/dati/cer_fv
```

**CF8 – Browser**: apri https://eugenio.statocritico.it/api/cer-fv/info: deve comparire `"disponibile": true` con l'anno e
le campagne AGREA.

**CF9 – Browser**: apri https://eugenio.statocritico.it/fv-cer.html, premi «Prova con l'esempio», poi «Calcola» e «Cerca i
terreni pubblici». Devono comparire la tabella delle cabine, i terreni (con la colonna «Coltura DOP o certificata») e
l'elenco B.

**CF10 – Server**: cancella le copie temporanee con `rm -r /tmp/agrea /tmp/cer_fv` (gli zip sul PC puoi tenerli).
