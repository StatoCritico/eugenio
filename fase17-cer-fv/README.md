# Fase 17 – CER – Sviluppo impianti FV (24/11/2026)

Parte del server della pagina **Fotovoltaico › CER – Sviluppo impianti FV** (`fase5-sito/sito/fv-cer.html`, sperimentale).
Richiesta di Paolo del 24/11/2026; proposta completa in `documenti/PROPOSTA_TERRENI_CER_2026-11-24.md` (Project).

La pagina fa quasi tutto nel browser (curve di carico, aree del GSE, potenza FV + accumulo: `cer_fv_calcolo.js`); qui si
prepara una sola cosa: l'elenco dei **terreni pubblici in proprietà** con la **probabilità di coltura DOP o
certificata**, letto dalla rotta `GET /api/cer-fv/terreni` della fase 4 (`servizio/cer_fv.py`).

## Cosa fa

```bash
python -m cer_fv terreni --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /srv/energia/dati/cer_fv
```

1. Dall'indice degli immobili delle PA della fase 7 (`immobili_pa_<anno>.sqlite`, tabella `ente_particelle`) prende le
   particelle dei terreni (`natura = 'T'`) **in proprietà** (`ruolo = 'P'`) di enti pubblici, con superficie della particella,
   comune, ente (nome, settore, sede), tipologie e utilizzo; più enti nella stessa particella → `n_enti` e `enti`.
2. Dal parquet delle particelle della fase 7 prende foglio, particella e poligono.
3. Dove ci sono i **piani colturali grafici di AGREA** (Emilia-Romagna) calcola per ogni particella la **probabilità di
   coltura DOP o certificata** (`colture.py`, regole in `cer_fv/regole_colture.toml`):
   - peso dell'appezzamento 1 se biologico (`FLAG_BIO`), in produzione integrata (`FLAG_INTE`) o con qualità DOP/IGP/DOC;
     altrimenti peso della categoria di coltura (vite, frutteti, foraggere, olivo, castagno, orticole, seminativi) per il
     fattore della provincia (zone dei disciplinari approssimate per provincia, es. foraggere 1 a Parma, Reggio Emilia e
     Modena per il Parmigiano Reggiano);
   - per campagna: somma di (quota della particella coperta dall'appezzamento × peso), al massimo 1;
   - indicatore = massimo delle **ultime 3 campagne**, 0-100, classe alta (≥ 60), media (≥ 30), bassa; «non dichiarata»
     se la particella è nella zona coperta da AGREA ma nessun appezzamento la tocca; vuoto fuori dalla zona.
4. Scrive `terreni_pubblici_<anno>.sqlite` (tabella `terreni`, indice R*Tree `terreni_rt`, tabella `info`) con scrittura
   sicura (file temporaneo e rinomina).

## Dati AGREA: non si cedono (decisione di Paolo, 24/11/2026)

I piani colturali grafici si scaricano da
https://agrea.regione.emilia-romagna.it/servizi/documentazione/open-data-sullutilizzo-del-suolo-1 (per provincia, dal
2018) e si mettono **sul server** in `/srv/energia/dati/agrea/<campagna>/` (zip o shapefile come scaricati; anche zip dentro
zip). La pagina non dichiara una licenza e la descrizione della fornitura del 2018 dice «non cedibili a terzi»: per questo
i file **non entrano nel repository, non sono serviti e nessuna rotta li restituisce**. Esce solo l'indicatore per
particella. Sistema di riferimento letto dal `.prj`; senza `.prj` si deduce dalle coordinate (Gauss-Boaga fuso Ovest
EPSG:3003, UTM 32N, gradi). Campi cercati: `DESC_COLT`, `DESC_USO`, `DESC_QUAL`, `FLAG_BIO`, `FLAG_INTE` (anche con i nomi
troncati dei DBF).

L'indicatore **non è una certificazione**: per la L.R. Emilia-Romagna 5/2026 (art. 10) serve l'attestazione di un
agronomo; la pagina lo scrive accanto al valore.

## Installazione sul server

Con il venv della fase 7 (stesse librerie più `pyshp`):

```bash
cd ~/energia/fase17-cer-fv
~/energia/fase7-territorio/.venv/bin/pip install -r requirements.txt
sudo mkdir -p /srv/energia/dati/agrea /srv/energia/dati/cer_fv
PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv terreni \
    --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /tmp/cer_fv
sudo cp /tmp/cer_fv/terreni_pubblici_*.sqlite /srv/energia/dati/cer_fv/ && sudo chown -R 1000:1000 /srv/energia/dati/cer_fv
```

Si rifà quando cambiano gli immobili delle PA (una volta l'anno) o arriva una nuova campagna AGREA.

## Prove

```bash
python -m pytest -q tests     # indice, parquet e piani colturali sintetici (shapefile in 3003 senza .prj); nessuna rete
```
