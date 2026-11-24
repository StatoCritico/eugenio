# Aggiornamento del 24/11/2026 (notte) – CER: vincoli paesaggistici

Release **`v2026.11.24c`**, sito **`?v=20261124c`** (via di Paolo del 24/11 alle 21:53: «correggiamo e pubblichiamo»),
ramo `claude/2026-11-24-cer-vincoli`. Con la correzione delle prove della fase 4 (`tests/conftest.py` mette nei percorsi
di Python le altre fasi come fa il container: prima serviva il PYTHONPATH a mano) e della prova di `aggiorna_da_github.sh`
che non contava la fase 17.

Richiesta di Paolo del 24/11 alle 20:54 («verifica se tra le aree non idonee abbiamo escluso questi vincoli»: il gruppo
«Vincoli paesaggistici» del catalogo della Regione) e via alla proposta alle 20:56 («fallo così»).

Verifica: non c'erano. La pagina escludeva solo zone A, B, C dei parchi, riserve e Rete Natura 2000.

Fatto:

- **Fase 17, `vincoli.py`**: `python -m cer_fv scarica-vincoli` scarica in `/srv/energia/dati/vincoli/` (~230 MB) gli
  shapefile della Regione (boschi, corsi d'acqua con le fasce di 150 m, coste, laghi, zone di interesse archeologico,
  beni dell'art. 136, usi civici) e dal WFS del Patrimonio culturale i beni archeologici tutelati e le zone umide (art. 142
  i, aggiunte: stesso articolo, non nel gruppo del catalogo); poi costruisce `vincoli_er.sqlite` per la mappa. Nella
  costruzione dei terreni ogni particella pubblica dell'Emilia-Romagna ha la quota vincolata e l'elenco dei vincoli.
- **Escludono** boschi, corsi d'acqua e fasce di 150 m, coste, laghi, zone umide, zone e beni archeologici, art. 136:
  la parte vincolata non conta e il terreno è escluso se è vincolato per metà o più. **Usi civici** solo segnalati.
- **Non usati**: le zone escluse dai vincoli dell'art. 142 c. 2 (nel catalogo il dataset non ha file); montagne oltre i
  1.200 m e circhi glaciali (non toccano i terreni agricoli).
- **Server**: rotta `/api/cer-fv/vincoli?bbox=` (perimetri semplificati, al massimo 0,25 gradi² e 6.000 poligoni); i file
  dei terreni vecchi, senza le colonne dei vincoli, continuano a funzionare.
- **Pagina**: livello viola dei vincoli paesaggistici dallo zoom 13, sotto «Aree non idonee e vincoli paesaggistici»;
  scheda del terreno con i vincoli e la superficie libera; colonne nel file.

Prove: fase 17 (14), fase 4 completa (439 passate), fase 5 `test_fv_cer.py` e `test_costruisci_pagine.py`.

## Pubblicazione

- **PC1** – [Browser] Merge della pull request su GitHub (collegamento nella risposta di Claude).
- **PC2** – [Browser] Release `v2026.11.24c` da questo collegamento già compilato, con **Publish release**:
  https://github.com/StatoCritico/eugenio/releases/new?tag=v2026.11.24c&target=main&title=v2026.11.24c%20%E2%80%93%20CER%20%E2%80%93%20Sviluppo%20impianti%20FV%3A%20vincoli%20paesaggistici&body=%2A%2ACER%20%E2%80%93%20Sviluppo%20impianti%20FV%3A%20vincoli%20paesaggistici%2A%2A%20%2824%2F11%2F2026%2C%20versione%2020261124c%29%0A%0AMigliorato%0A-%20Fotovoltaico%20%E2%80%BA%20CER%20%E2%80%93%20Sviluppo%20impianti%20FV%3A%20i%20terreni%20pubblici%20dell%27Emilia-Romagna%20tengono%20conto%20dei%20vincoli%20paesaggistici%20della%20Regione%20%28boschi%2C%20corsi%20d%27acqua%20con%20le%20fasce%20di%20150%20m%2C%20coste%2C%20laghi%2C%20zone%20umide%2C%20zone%20e%20beni%20archeologici%2C%20beni%20dichiarati%20di%20notevole%20interesse%20pubblico%29%3A%20conta%20solo%20la%20parte%20libera%20della%20particella%20e%20il%20terreno%20%C3%A8%20escluso%20se%20%C3%A8%20vincolato%20per%20met%C3%A0%20o%20pi%C3%B9.%20Gli%20usi%20civici%20sono%20segnalati%20nella%20scheda.%20Avvicinandosi%2C%20i%20vincoli%20si%20vedono%20in%20viola%20sulla%20mappa.%0A%0APagina%3A%20https%3A%2F%2Feugenio.statocritico.it%2Ffv-cer.html%0A%0ADopo%20l%27installazione%3A%20passi%20VP1%E2%80%93VP4%20di%20AGGIORNAMENTO_2026-11-24c.md%20%28vincoli%20sul%20server%29.
- **PC3** – [Server] `~/energia/fase4-server/aggiorna_da_github.sh --forza` e poi `cat ~/.eugenio_versione`: deve dire
  `v2026.11.24c`.

## Passi dei vincoli (dopo PC3)

**VP1 – Server**: crea la cartella dei vincoli e rendila tua:

```bash
sudo mkdir -p /srv/energia/dati/vincoli && sudo chown -R "$USER" /srv/energia/dati/vincoli
```

**VP2 – Server**: scarica i vincoli e costruisci il file per la mappa (qualche minuto):

```bash
cd ~/energia/fase17-cer-fv && PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv scarica-vincoli
```

Alla fine un riepilogo con `"poligoni": 141629` circa e `per_fonte` con nove voci.

**VP3 – Server**: ricostruisci i terreni con i vincoli (qualche minuto in più di prima; usa ~1,5 GB di memoria in più):

```bash
cd ~/energia/fase17-cer-fv && PYTHONPATH=. ~/energia/fase7-territorio/.venv/bin/python -m cer_fv terreni \
    --immobili /srv/energia/dati/immobili_pa --agrea /srv/energia/dati/agrea --dest /srv/energia/dati/cer_fv
```

Nel riepilogo `con_vincoli` deve essere un numero (le particelle pubbliche dell'Emilia-Romagna).

**VP4 – Browser**: https://eugenio.statocritico.it/api/cer-fv/vincoli?bbox=12.50,44.00,12.60,44.08 deve rispondere con
`"disponibile": true` e un centinaio di poligoni; in https://eugenio.statocritico.it/fv-cer.html, avvicinandosi oltre lo
zoom 13, compaiono le aree viola e nella scheda dei terreni i vincoli.
