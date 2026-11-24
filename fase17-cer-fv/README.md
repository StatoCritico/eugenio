# Fase 17 – CER – Sviluppo impianti FV (24/11/2026)

Parte del server della pagina **Fotovoltaico › CER – Sviluppo impianti FV** (`fase5-sito/sito/fv-cer.html`, sperimentale).
Richiesta di Paolo del 24/11/2026; proposta completa in `documenti/PROPOSTA_TERRENI_CER_2026-11-24.md` (Project).

La pagina fa quasi tutto nel browser (curve di carico, aree del GSE, potenza FV + accumulo: `cer_fv_calcolo.js`); qui si
prepara una sola cosa: l'elenco dei **terreni pubblici in proprietà** con la **probabilità di coltura DOP o
certificata**, letto dalla rotta `GET /api/cer-fv/terreni` della fase 4 (`servizio/cer_fv.py`).

## Cosa fa

```bash
python -m cer_fv scarica-agrea      # piani colturali AGREA in /srv/energia/dati/agrea/<anno>/ (ultime 3 campagne chiuse)
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
