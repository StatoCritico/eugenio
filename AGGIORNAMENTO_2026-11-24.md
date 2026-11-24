# Aggiornamento del 24/11/2026 – CER – Sviluppo impianti FV (prima fase, fino alle uscite A e B)

Release **`v2026.11.24`**, versione del sito **`20261124a`** (via di Paolo del 24/11 alle 14:23: «pubblichiamo»), ramo
`claude/2026-11-24-cer-fv`. Richiesta di Paolo del 24/11 (01:04): «fai la prima fase della
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

Aggiunte sullo stesso ramo (24/11, ore 09:24–09:27, richieste di Paolo):

- **Riquadro evidenziato** (`.riquadro-llm` in `stile.css`) in cima a **Novità** e **Come funziona** con i collegamenti a
  `llms.txt` ed `EUGENIO_PER_AGENTI.md`.
- **Bersaglio verde** nella pagina iniziale, in cima al fascio di luce dietro la torre (17°, `a.sh-punto.sh-file`): porta
  dritto a `EUGENIO_PER_AGENTI.md`, con la descrizione al passaggio e senza scheda. Verde (non azzurro) per attirare
  l'attenzione, in tutti e due i temi.
- **Fotovoltaico › Curve di carico** (`fv-curve.html`, prima voce del gruppo, **in lavorazione**): skill `load-curve` per
  e-distribuzione scaricabile da `strumenti/load-curve.zip` (zip di Paolo delle 09:55, con un POD e percorsi d'esempio al
  posto di quelli veri) e skill per il Portale Consumi dell'Acquirente Unico;
  si attiva quando ci sarà l'accesso come persona giuridica.

Prove: `fase5-sito/tests/test_fv_cer.py` (file, calcolo con Node, pagina in Chromium con `?prova=1`), suite della fase 5,
`fase17-cer-fv/tests` (4), `fase4-server/tests/test_cer_fv.py`, `test_protezione.py`, `test_aggiorna_da_github.py`.

## Pubblicazione

- **PU1** – [Browser] Merge della pull request su GitHub (collegamento nella risposta di Claude).
- **PU2** – [Browser] Release `v2026.11.24` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.24&target=main&title=v2026.11.24%20%E2%80%93%20CER%20%E2%80%93%20Sviluppo%20impianti%20FV&body=%2A%2ACER%20%E2%80%93%20Sviluppo%20impianti%20FV%2A%2A%20%2824%2F11%2F2026%2C%20versione%2020261124a%29%0A%0ANuovo%0A-%20Fotovoltaico%20%E2%80%BA%20CER%20%E2%80%93%20Sviluppo%20impianti%20FV%20%28sperimentale%29%3A%20carichi%20l%27elenco%20degli%20edifici%20e%20le%20loro%20curve%20di%20carico%20%28restano%20nel%20tuo%20browser%29%3B%20EuGEnio%20trova%20l%27area%20della%20cabina%20primaria%20di%20ogni%20edificio%2C%20somma%20i%20consumi%20e%20calcola%2C%20con%20il%20clima%20del%20posto%2C%20la%20potenza%20fotovoltaica%20e%20l%27accumulo%20pi%C3%B9%20grandi%20che%20rispettano%20la%20quota%20minima%20di%20energia%20condivisa%20che%20scegli.%20Poi%20propone%20i%20terreni%20pubblici%20vicini%20alla%20cabina%2C%20con%20l%27ente%20proprietario%20e%20la%20probabilit%C3%A0%20che%20ci%20sia%20una%20coltura%20DOP%20o%20certificata%20%28solo%20in%20Emilia-Romagna%2C%20dai%20piani%20colturali%20di%20AGREA%3A%20un%27indicazione%2C%20non%20una%20certificazione%29%2C%20oppure%20prepara%20l%27elenco%20delle%20cabine%20e%20un%20avviso%20tipo%20per%20raccogliere%20le%20manifestazioni%20di%20interesse%20dei%20proprietari.%0A%0APagina%3A%20https%3A%2F%2Feugenio.statocritico.it%2Ffv-cer.html
- **PU3** – [Server] per averla subito (altrimenti la installa l'aggiornamento automatico delle 4:40):
  ```bash
  ~/energia/fase4-server/aggiorna_da_github.sh --forza
  cat ~/.eugenio_versione
  ```
  Deve dire `v2026.11.24`. Da qui c'è `~/energia/fase17-cer-fv` e si possono fare i passi CF2–CF7.
- **PU4** – [Browser del PC, Ctrl+F5] https://eugenio.statocritico.it/ – mirino verde in cima al fascio di luce dietro la
  torre, «File per gli assistenti AI», che apre `EUGENIO_PER_AGENTI.md`; https://eugenio.statocritico.it/novita.html con il
  riquadro in cima e la voce del 24/11; nel menu Fotovoltaico «Curve di carico» (triangolo giallo, non cliccabile) e «CER –
  Sviluppo impianti FV» (con la «S»).

## Passi dei terreni pubblici (dopo PU3)

Senza il file dei terreni la pagina funziona fino alla potenza per cabina e alla parte B; la parte A dice «i terreni
pubblici non sono ancora sul server».

**Dal 24/11 alle 10:29 (Paolo: «usa la cartella del progetto eugenio per scaricare i file, non sparpagliarli
dappertutto»)**: i file li scarica il server stesso in `/srv/energia/dati/agrea/` (la cartella dei dati di EuGEnio); niente
PC, niente `/tmp`. Si usano i file **«UtilizziGrafici»** (campi già ritagliati sulle particelle, con foglio e particella),
letti a pezzi senza estrarli.

**CF1 – Server** (✓ fatto da Paolo il 24/11 alle 14:23): crea le due cartelle dei dati e rendile tue (l'api le legge soltanto):

```bash
sudo mkdir -p /srv/energia/dati/agrea /srv/energia/dati/cer_fv && sudo chown -R "$USER" /srv/energia/dati/agrea /srv/energia/dati/cer_fv
```

Non deve comparire niente.

**CF2 – Server**: aggiungi `pyshp` al venv della fase 7:

```bash
~/energia/fase7-territorio/.venv/bin/pip install -r ~/energia/fase17-cer-fv/requirements.txt
```

Deve finire con «Successfully installed pyshp…» o «Requirement already satisfied».

**CF3 – Server**: scarica le ultime tre campagne chiuse (2023, 2024, 2025: ~3,9 GB, qualche minuto):

```bash
cd ~/energia/fase17-cer-fv && PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv scarica-agrea
```

Alla fine un riepilogo con `"campagne": [2023, 2024, 2025]` e 27 file in `"scaricati"`. Se si interrompe, rilancia lo stesso
comando: riprende dai file mancanti.

**CF4 – Server**: controlla lo spazio: `du -sh /srv/energia/dati/agrea && df -h /srv/energia` (circa 3,9 GB usati).

**CF5 – Server**: costruisci i terreni (qualche minuto; alla fine un riepilogo con `particelle`, `con_indicatore` e
`campagne_agrea`):

```bash
cd ~/energia/fase17-cer-fv && PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv terreni \
    --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /srv/energia/dati/cer_fv
```

`con_indicatore` deve essere di qualche migliaio (i terreni pubblici dell'Emilia-Romagna dichiarati ad AGREA). Se compare
«codici ISTAT senza codice catastale», mandami la riga.

**CF6 – Browser**: apri https://eugenio.statocritico.it/api/cer-fv/info: deve comparire `"disponibile": true` con l'anno e
le campagne AGREA.

**CF7 – Browser**: apri https://eugenio.statocritico.it/fv-cer.html, premi «Prova con l'esempio», poi «Calcola» e «Cerca i
terreni pubblici». Devono comparire la tabella delle cabine, i terreni (con la colonna «Coltura DOP o certificata») e
l'elenco B.

**Ogni anno, dopo il 31/12** (nuova campagna chiusa): CF3 con `--togli-vecchie` (cancella la campagna più vecchia), poi CF5.
