# Fase 17 – CER – Sviluppo impianti FV (24/11/2026)

Parte del server della pagina **Fotovoltaico › CER – Sviluppo impianti FV** (`fase5-sito/sito/fv-cer.html`, sperimentale).
Richiesta di Paolo del 24/11/2026; proposta completa in `documenti/PROPOSTA_TERRENI_CER_2026-11-24.md` (Project).

La pagina fa quasi tutto nel browser (curve di carico, aree del GSE, potenza FV + accumulo: `cer_fv_calcolo.js`); qui si
prepara una sola cosa: l'elenco dei **terreni pubblici in proprietà** con la **probabilità di coltura DOP o
certificata**, letto dalla rotta `GET /api/cer-fv/terreni` della fase 4 (`servizio/cer_fv.py`).

## Cosa fa

```bash
python -m cer_fv scarica-agrea      # piani colturali AGREA in /srv/energia/dati/agrea/<anno>/ (ultime 3 campagne chiuse)
python -m cer_fv scarica-vincoli    # vincoli paesaggistici della Regione in /srv/energia/dati/vincoli/ + vincoli_er.sqlite
python -m cer_fv terreni --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /srv/energia/dati/cer_fv
```

0. `scarica-agrea` (24/11/2026, `agrea.py`): scarica dal server stesso i file **«UtilizziGrafici»** di AGREA delle ultime
   tre campagne **chiuse** (quella dell'anno in corso è ancora aperta), uno zip per provincia (non il `_XX` fuori regione),
   solo quelli nuovi o di dimensione diversa, scrivendo prima in `.part`; `--togli-vecchie` cancella le campagne non più
   usate; `--anni 2023 2024 2025` per anni precisi. Tutto in **`/srv/energia/dati/agrea/`** (`DATI/agrea`), nessuna copia
   altrove (Paolo, 24/11: «non sparpagliarli dappertutto»). ~1,3 GB di zip per campagna.
1. Dall'indice degli immobili delle PA della fase 7 (`immobili_pa_<anno>.sqlite`, tabella `ente_particelle`) prende le
   particelle dei terreni (`natura = 'T'`) **in proprietà** (`ruolo = 'P'`) di enti pubblici, con superficie della particella,
   comune, ente (nome, settore, sede), tipologie e utilizzo; più enti nella stessa particella → `n_enti` e `enti`.
2. Dal parquet delle particelle della fase 7 prende foglio e particella (e il poligono solo per i file AGREA vecchi).
   Con la sezione presa dal riferimento AdE (`A944A_…`) forma la **chiave catastale** (codice del comune, sezione, foglio e
   particella senza zeri iniziali).
3. Dove ci sono i **piani colturali grafici di AGREA** (Emilia-Romagna) calcola per ogni particella la **probabilità di
   coltura DOP o certificata** (`colture.py`, regole in `cer_fv/regole_colture.toml`):
   - abbinamento: i file «UtilizziGrafici» (dal 2021) hanno già comune ISTAT, sezione, foglio, particella e superficie
     (`SUP_UTI`, ettari); il `.dbf` si legge **a pezzi dallo zip** con un lettore dBASE proprio (`agrea.righe_dbf`), senza
     estrarlo né caricarlo in memoria, e si tengono solo le righe delle particelle pubbliche (prova sul file vero di Rimini
     2025: 1,5 GB di `.dbf`, 244.000 righe, 2 secondi e 43 MB di memoria). Codice ISTAT → codice catastale da
     `DATI/clima_lavoro/comuni.parquet` (fase 3) o, se manca, dall'elenco dei comuni dell'ISTAT salvato una volta in
     `DATI/agrea/comuni_istat.csv` (`--comuni` per un altro file). Per i file senza foglio e particella (fino al 2020)
     resta l'abbinamento geometrico con i poligoni;
   - peso dell'appezzamento 1 se biologico o in conversione (`DESC_BIO`; nei file vecchi `FLAG_BIO`), in produzione
     integrata (`FLAG_INTE`, solo nei file vecchi) o con una menzione DOP/IGP/DOC (`DESC_QUAL`, `DESC_MENZ` come «COLLINE
     DI ROMAGNA - DOP», `DESC_CE_OL` per l'olio);
     altrimenti peso della categoria di coltura (vite, frutteti, foraggere, olivo, castagno, orticole, seminativi) per il
     fattore della provincia (zone dei disciplinari approssimate per provincia, es. foraggere 1 a Parma, Reggio Emilia e
     Modena per il Parmigiano Reggiano);
   - per campagna: somma di (quota della particella coperta dall'appezzamento × peso), al massimo 1 (quota = `SUP_UTI` /
     superficie della particella AdE, o intersezione dei poligoni nei file vecchi);
   - indicatore = massimo delle **ultime 3 campagne**, 0-100, classe alta (≥ 60), media (≥ 30), bassa; «non dichiarata»
     se la particella è nella zona coperta da AGREA ma nessun appezzamento la tocca; vuoto fuori dalla zona.
4. Scrive `terreni_pubblici_<anno>.sqlite` (tabella `terreni`, indice R*Tree `terreni_rt`, tabella `info`) con scrittura
   sicura (file temporaneo e rinomina).

## Vincoli paesaggistici (24/11/2026 sera, `vincoli.py`)

Richiesta di Paolo (24/11, 20:54–20:56): escludere i vincoli del gruppo «Vincoli paesaggistici» del catalogo della Regione
(https://datacatalog.regione.emilia-romagna.it/catalogCTA/dataset?groups=vincoli-paesaggistici, CC BY 4.0).

- **Escludono** la parte della particella che coprono: foreste e boschi (art. 142 c. 1 g), corsi d'acqua con le fasce di
  150 m (c; tratti con `escluso = E` saltati), territori costieri (a), contermini ai laghi (b), zone di interesse
  archeologico (m), beni dell'art. 136, beni archeologici tutelati e zone umide (i) (questi due dal WFS del Patrimonio
  culturale dell'Emilia-Romagna, GML in EPSG:4326; le zone umide non sono nel gruppo del catalogo ma sono un vincolo dello
  stesso articolo). **Segnalati** soltanto: usi civici e università agrarie (h).
- Non usati: art. 142 c. 2 (zone escluse dai vincoli: nel catalogo il dataset non ha file, 24/11/2026), montagne oltre i
  1.200 m (d) e circhi glaciali (e) (non toccano i terreni agricoli), il dataset dei decreti (solo pagina web).
- `scarica-vincoli`: zip degli shapefile (indirizzi letti dall'API CKAN del catalogo, `package_show`) e GML del WFS, tutto in
  **`/srv/energia/dati/vincoli/`** (~230 MB, quasi tutto boschi); poi `vincoli_er.sqlite` (~230 MB: perimetri semplificati a
  2 m, in gradi con precisione 1e-5, indice R*Tree) per la rotta `/api/cer-fv/vincoli` della fase 4. `--solo-mappa` rifà
  il file senza scaricare. Shapefile in RDN2008 / UTM 32N (EPSG:7791); anelli costruiti a mano (pyshp si ferma sugli
  anelli degeneri dei boschi).
- In `terreni` (se la cartella c'è, o `--vincoli`): per ogni particella pubblica dell'Emilia-Romagna, col poligono del
  parquet in UTM 32N, `quota_vincolata` (0-1, unione dei vincoli che escludono, sovrapposizioni contate una volta),
  `vincoli` (testo con la quota di ognuno) e `vincoli_segnalati`; sotto l'1 % non si conta. Prova sul PC con i file veri:
  141.629 poligoni, 20 s per caricarli e 1,3 GB di memoria.
- Nella pagina: conta solo la superficie libera; escluso se vincolato per metà o più; livello viola dallo zoom 13.

## Dati AGREA: non si cedono (decisione di Paolo, 24/11/2026)

I piani colturali grafici sono pubblicati da AGREA
(https://agrea.regione.emilia-romagna.it/servizi/documentazione/open-data-sullutilizzo-del-suolo-1; file in
https://agreagestione.regione.emilia-romagna.it/agrea-file/: `UtilizziGrafici` dal 2021 per provincia della particella,
`AppezzAziendaGrafici` per provincia della sede dell'azienda, `PianiColturaliGraficiFinoAl2020`). Li scarica il server con
`scarica-agrea` in `/srv/energia/dati/agrea/<campagna>/` (vanno bene anche zip o shapefile messi a mano, anche zip dentro
zip). Il codice dell'azienda nei file è già cifrato da AGREA. Altre regioni (verifica del 24/11): nessun piano colturale
grafico aperto equivalente; la Lombardia pubblica solo una griglia a 20 m 2012–2020 (SIARL), che non basta. La pagina non dichiara una licenza e la descrizione della fornitura del 2018 dice «non cedibili a terzi»: per questo
i file **non entrano nel repository, non sono serviti e nessuna rotta li restituisce**. Esce solo l'indicatore per
particella. File vecchi: sistema di riferimento letto dal `.prj`; senza `.prj` si deduce dalle coordinate (Gauss-Boaga fuso
Ovest EPSG:3003, UTM 32N, gradi). Campi cercati: `DESC_COLT`, `DESC_USO`, `DESC_QUAL`, `DESC_BIO`, `DESC_MENZ`,
`DESC_CE_OL`, `FLAG_BIO`, `FLAG_INTE` (anche con i nomi troncati dei DBF).

L'indicatore **non è una certificazione**: per la L.R. Emilia-Romagna 5/2026 (art. 10) serve l'attestazione di un
agronomo; la pagina lo scrive accanto al valore.

## Installazione sul server

Con il venv della fase 7 (stesse librerie più `pyshp`, che serve solo per i file AGREA vecchi), tutto dentro
`/srv/energia/dati` (niente `/tmp`, niente copie sul PC):

```bash
cd ~/energia/fase17-cer-fv
~/energia/fase7-territorio/.venv/bin/pip install -r requirements.txt
sudo mkdir -p /srv/energia/dati/agrea /srv/energia/dati/cer_fv && sudo chown -R "$USER" /srv/energia/dati/agrea /srv/energia/dati/cer_fv
PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv scarica-agrea --togli-vecchie
sudo mkdir -p /srv/energia/dati/vincoli && sudo chown -R "$USER" /srv/energia/dati/vincoli
PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv scarica-vincoli
PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv terreni \
    --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /srv/energia/dati/cer_fv
```

Il file si scrive accanto con un nome temporaneo e poi si rinomina: l'api lo legge in sola lettura. Si rifà una volta
l'anno, dopo il 31/12 (nuova campagna chiusa) o quando cambiano gli immobili delle PA.

## Prove

```bash
python -m pytest -q tests     # indice, parquet e piani colturali sintetici: shapefile in 3003 senza .prj (file vecchi) e
                              # zip col tracciato «UtilizziGrafici» (chiavi catastali, DESC_BIO, DESC_MENZ); scaricamento
                              # con le risposte finte di AGREA; nessuna rete
```
