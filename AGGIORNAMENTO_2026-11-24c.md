# Aggiornamento del 24/11/2026 (notte) – CER: vincoli paesaggistici

Ramo `claude/2026-11-24-cer-vincoli`, **non ancora in una release** (release solo al via di Paolo; sito ancora
`20261124b`, nessuna voce di Novità).

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

Prove: fase 17 (14), fase 4 `test_cer_fv.py` (4), fase 5 `test_fv_cer.py` e `test_costruisci_pagine.py`.

## Passi (dopo il via di Paolo: pull request, Merge, release e installazione come sempre)

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
