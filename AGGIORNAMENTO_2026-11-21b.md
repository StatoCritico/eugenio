# Aggiornamento del 21/11/2026 b – `aggiorna_da_github.sh` sicuro

Correzioni dello script di aggiornamento dopo l'aggiornamento a `v2026.11.21` fallito stamattina (21/11, 9:22): rilancio
dello script della release, ritorno indietro che non cancella mai `~/energia`, pulizia delle copie che non cancella la
copia appena fatta, controllo dei `COPY` del Dockerfile prima della build, copia del `.env` in
`~/.eugenio_env_backup/env_<data>`. Dettagli: `fase4-server/README.md`, sezione «Correzioni del 21/11/2026». Nessun
cambiamento al sito.

## Quando questa correzione sarà in una release: lancia lo script nuovo direttamente dal clone

Lo script installato in `~/energia` e quello rimasto nel clone `~/eugenio-git` (al tag `v2026.11.21`) sono ancora quelli
vecchi, che non sanno rilanciare lo script della release: la prima volta lo script nuovo va preso dal clone, portato
prima sulla release che contiene la correzione. Prima di cominciare `~/energia` deve esserci, con
`fase4-server/docker-compose.yml` e `fase4-server/.env` (altrimenti lo script si ferma senza toccare niente).

```bash
ssh eugenio
git -C ~/eugenio-git fetch -q --tags --force origin
git -C ~/eugenio-git -c advice.detachedHead=false checkout -q --force <release con la correzione>
~/eugenio-git/fase4-server/aggiorna_da_github.sh --prova
~/eugenio-git/fase4-server/aggiorna_da_github.sh --forza
```

Al posto di `<release con la correzione>` metti il tag della release che contiene questa correzione (per esempio
`v2026.11.21b`). Cosa deve comparire:
- con `--prova`: nessuna riga «ATTENZIONE: il Dockerfile copia percorsi che non ci sarebbero» e alla fine «Prova finita:
  niente è stato cambiato.»;
- con `--forza`: nel registro (`tail -n 30 ~/aggiorna_da_github.log`) «Copia del .env: …», «Copia di sicurezza:
  ~/energia_prima_<release>», «Dockerfile: tutti i percorsi dei COPY ci sono», «api e worker aggiornati e funzionanti» e la
  riga finale «Release … installata»;
- `ls -l ~/.eugenio_env_backup/`: i file `env_…` con permessi `-rw-------` (la copia `env_2026-11-21` fatta a mano resta
  com'è);
- `ls -ld ~/energia_prima_*`: al massimo 3 copie, compresa quella appena fatta.

Da quel momento lo script installato in `~/energia` conosce il rilancio: gli aggiornamenti successivi (anche quello
notturno delle 4:40) tornano a partire da `~/energia/fase4-server/aggiorna_da_github.sh` come prima.
