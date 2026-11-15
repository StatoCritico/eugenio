#!/usr/bin/env bash
# Aggiornamento del server di EuGEnio da una release di GitHub (decisione di Paolo del 12/11/2026, strada «2a»).
#
# Il repository è pubblico: il server lo legge in HTTPS, senza chiavi. Si pubblica solo ciò che ha una release (tag
# vAAAA.MM.GG, vAAAA.MM.GGb …), creata dopo che Paolo ha approvato la pull request.
#
#   ~/energia/fase4-server/aggiorna_da_github.sh --prova            dice cosa farebbe con l'ultima release, senza toccare nulla
#   ~/energia/fase4-server/aggiorna_da_github.sh                    aggiorna all'ultima release (se è più nuova di quella installata)
#   ~/energia/fase4-server/aggiorna_da_github.sh v2026.11.13        aggiorna a quella release
#   ~/energia/fase4-server/aggiorna_da_github.sh --forza v2026.11.13   anche se è già installata
#   ~/energia/fase4-server/aggiorna_da_github.sh --notte            dal crontab: solo se c'è una release nuova, email con l'esito
#
# Passi (gli stessi delle procedure AGGIORNAMENTO_*.md):
#   1. copia di sicurezza di ~/energia (si tengono le ultime 3) e delle convenzioni del server;
#   2. codice delle fasi 3, 4, 6, 7, 8, 9, 10 e fase5-sito/novita.toml in ~/energia (rsync senza cancellare: restano
#      .env, fase 2, uni_privato, mercati_energia/dati e tutto ciò che non è nel repository);
#   3. convenzioni (*.toml e fonti/) in /srv/energia/dati/mercati/convenzioni, con l'elenco di quelle cambiate;
#   4. docker compose build api, up -d --force-recreate api worker, attesa dell'api «healthy»; se non lo diventa entro
#      3 minuti si torna da soli alla copia di sicurezza e si esce con errore;
#   5. sito in /srv/energia/sito (rsync senza cancellare; dati/indicatori e dati/prezzi non si toccano), controllo della
#      versione ?v= di index.html;
#   6. file degli indici dei prezzi (worker «prezzi»);
#   7. Purge Everything su Cloudflare, se nel .env ci sono CF_ZONE_ID e CF_PURGE_TOKEN (token con il solo permesso
#      «Zone › Cache Purge»);
#   8. versione installata in ~/.eugenio_versione; elenco dei file AGGIORNAMENTO_*.md cambiati: i loro «passi a mano»
#      (archivi, righe nuove del .env, crontab…) lo script NON li fa, li scrive alla fine e nell'email.
# I segreti restano nel .env del server: lo script li legge solo per il Purge e non li stampa mai.
set -euo pipefail

# bash legge lo script mentre lo esegue: passando a un'altra release il file può cambiare sotto i piedi. Si riparte da una
# copia temporanea, una volta sola.
if [ -z "${EUGENIO_AGG_COPIA:-}" ]; then
  COPIA_SCRIPT=$(mktemp "${TMPDIR:-/tmp}/aggiorna_da_github.XXXXXX.sh")
  cp "$0" "$COPIA_SCRIPT"
  EUGENIO_AGG_COPIA="$COPIA_SCRIPT" exec bash "$COPIA_SCRIPT" "$@"
fi
trap 'rm -f "$EUGENIO_AGG_COPIA"' EXIT

REPO="${EUGENIO_REPO:-https://github.com/statocritico/eugenio.git}"
CLONE="${EUGENIO_CLONE:-$HOME/eugenio-git}"
ENERGIA="${EUGENIO_ENERGIA:-$HOME/energia}"
SITO="${EUGENIO_SITO:-/srv/energia/sito}"
CONV="${EUGENIO_CONVENZIONI:-/srv/energia/dati/mercati/convenzioni}"
STATO="${EUGENIO_STATO:-$HOME/.eugenio_versione}"
REGISTRO="${EUGENIO_REGISTRO:-$HOME/aggiorna_da_github.log}"
CARTELLE=(fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d)
ESCLUSI=(--exclude=.env --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=uni_privato
         --exclude=fase2-gradi-giorno --exclude=mercati_energia/dati/ --exclude=node_modules)

PROVA=0; FORZA=0; NOTTE=0; TAG=""
for a in "$@"; do
  case "$a" in
    --prova) PROVA=1 ;;
    --forza) FORZA=1 ;;
    --notte) NOTTE=1 ;;
    -h|--help) sed -n 2,31p "$0"; exit 0 ;;
    v*) TAG="$a" ;;
    *) echo "Argomento sconosciuto: $a" >&2; exit 2 ;;
  esac
done

registra() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$REGISTRO"; }
fai() {                          # esegue, o in prova scrive soltanto
  if [ "$PROVA" = 1 ]; then echo "  [prova] $*"; else "$@"; fi
}
avviso() {                       # email all'amministratore con l'avviso del server (servizio/avvisi.py), se possibile
  [ "$PROVA" = 1 ] && return 0
  (cd "$ENERGIA/fase4-server" && docker compose run --rm --no-deps -T api python -c \
    "import sys; from servizio import avvisi; avvisi.invia(sys.argv[1], sys.argv[2])" "$1" "$2") >/dev/null 2>&1 || true
}

for c in git rsync flock curl docker; do
  command -v "$c" >/dev/null || { echo "Manca il comando $c (sudo apt-get install -y $c)." >&2; [ "$c" = docker ] && [ "$PROVA" = 1 ] || exit 1; }
done

exec 9>"$HOME/.aggiorna_da_github.lock"
flock -n 9 || { echo "Un altro aggiornamento è in corso." >&2; exit 1; }

# ------------------------------------------------------------------ 0. release da installare
if [ -d "$CLONE/.git" ]; then
  git -C "$CLONE" fetch -q --tags --force origin
else
  git clone -q "$REPO" "$CLONE"
fi
if [ -z "$TAG" ]; then
  TAG=$(git -C "$CLONE" tag -l 'v20*' --sort=-v:refname | grep -v '^visure' | head -1)
fi
[ -n "$TAG" ] || { echo "Nessuna release vAAAA.MM.GG su GitHub." >&2; exit 1; }
git -C "$CLONE" rev-parse -q --verify "refs/tags/$TAG" >/dev/null || { echo "La release $TAG non esiste." >&2; exit 1; }
PRIMA=$(cat "$STATO" 2>/dev/null || echo "")
if [ "$TAG" = "$PRIMA" ] && [ "$FORZA" = 0 ]; then
  [ "$NOTTE" = 1 ] || echo "La release $TAG è già installata (--forza per rifarla)."
  exit 0
fi
registra "Aggiornamento da ${PRIMA:-sconosciuta} a $TAG$( [ "$PROVA" = 1 ] && echo ' (prova)')"
git -C "$CLONE" -c advice.detachedHead=false checkout -q --force "$TAG"
SORG="$CLONE"
VERSIONE=$(sed -n 's/.*?v=\([0-9]\{8\}[a-z]\?\).*/\1/p' "$SORG/fase5-sito/sito/index.html" | head -1)
registra "Sito della release: ?v=$VERSIONE"

# passi a mano annunciati dalle procedure cambiate tra le due release
MANO=""
if [ -n "$PRIMA" ] && git -C "$CLONE" rev-parse -q --verify "refs/tags/$PRIMA" >/dev/null; then
  MANO=$(git -C "$CLONE" diff --name-only "$PRIMA" "$TAG" -- 'AGGIORNAMENTO_*.md' | tr '\n' ' ')
fi

# ------------------------------------------------------------------ 1. copie di sicurezza
COPIA="$ENERGIA"_prima_"$TAG"
fai cp -a "$ENERGIA" "$COPIA"
fai cp -a "$CONV" "$HOME/convenzioni_prima_$TAG"
if [ "$PROVA" = 0 ]; then         # si tengono le ultime 3 copie del codice
  ls -1dt "$ENERGIA"_prima_* 2>/dev/null | tail -n +4 | xargs -r rm -rf
fi

# ------------------------------------------------------------------ 2. codice
ELENCO=$(mktemp)
R=(rsync -a -i "${ESCLUSI[@]}")
[ "$PROVA" = 1 ] && R+=(-n)
for d in "${CARTELLE[@]}"; do
  "${R[@]}" "$SORG/$d" "$ENERGIA/" >>"$ELENCO"
done
"${R[@]}" "$SORG/.dockerignore" "$ENERGIA/" >>"$ELENCO"
fai mkdir -p "$ENERGIA/fase5-sito"
"${R[@]}" "$SORG/fase5-sito/novita.toml" "$ENERGIA/fase5-sito/" >>"$ELENCO"
registra "Codice: $(grep -c '^>f' "$ELENCO" || true) file nuovi o cambiati in $ENERGIA"

# ------------------------------------------------------------------ 3. convenzioni
CAMBIATE=$(cd "$SORG/fase6-mercati/convenzioni" && for f in *.toml fonti/*.toml; do
  cmp -s "$f" "$CONV/$f" 2>/dev/null || echo "$f"; done | tr '\n' ' ')
registra "Convenzioni cambiate: ${CAMBIATE:-nessuna}"
fai cp "$SORG"/fase6-mercati/convenzioni/*.toml "$CONV/"
fai cp "$SORG"/fase6-mercati/convenzioni/fonti/*.toml "$CONV/fonti/"

# ------------------------------------------------------------------ 4. immagine e container
torna_indietro() {
  registra "ERRORE: $1. Torno alla copia di sicurezza $COPIA."
  rm -rf "$ENERGIA" && cp -a "$COPIA" "$ENERGIA"
  cp "$HOME/convenzioni_prima_$TAG"/*.toml "$CONV/" 2>/dev/null || true
  (cd "$ENERGIA/fase4-server" && docker compose build api && docker compose up -d --force-recreate api worker) || true
  avviso "aggiornamento a $TAG fallito" "$1. Il server è tornato alla versione ${PRIMA:-precedente}. Registro: $REGISTRO"
  exit 1
}
if [ "$PROVA" = 0 ]; then
  cd "$ENERGIA/fase4-server"
  docker compose build api >>"$REGISTRO" 2>&1 || torna_indietro "build dell'immagine non riuscita"
  docker compose up -d --force-recreate api worker >>"$REGISTRO" 2>&1 || torna_indietro "avvio dei container non riuscito"
  for _ in $(seq 1 36); do
    sleep 5
    if docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/salute')" \
        >/dev/null 2>&1; then OK=1; break; fi
  done
  [ "${OK:-0}" = 1 ] || torna_indietro "l'api non risponde dopo 3 minuti"
  registra "api e worker aggiornati e funzionanti"
else
  echo "  [prova] docker compose build api; up -d --force-recreate api worker; attesa di /api/salute"
fi

# ------------------------------------------------------------------ 5. sito
S=(rsync -a -i --exclude=dati/indicatori/ --exclude=dati/prezzi/)
[ "$PROVA" = 1 ] && S+=(-n)
"${S[@]}" "$SORG/fase5-sito/sito/" "$SITO/" >"$ELENCO"
registra "Sito: $(grep -c '^>f' "$ELENCO" || true) file nuovi o cambiati in $SITO"
if [ "$PROVA" = 0 ]; then
  grep -q "?v=$VERSIONE" "$SITO/index.html" || torna_indietro "il sito non ha la versione ?v=$VERSIONE"
  registra "Sito aggiornato a ?v=$VERSIONE"
fi

# ------------------------------------------------------------------ 6. indici dei prezzi
if [ "$PROVA" = 0 ]; then
  (cd "$ENERGIA/fase4-server" && docker compose run --rm -T worker python -m servizio.worker prezzi >>"$REGISTRO" 2>&1) \
    && registra "Indici dei prezzi rifatti" \
    || registra "Avviso: file degli indici dei prezzi non rifatto (si rifà stanotte con i mercati)"
fi

# ------------------------------------------------------------------ 7. Purge di Cloudflare
ZONA=$(sed -n 's/^CF_ZONE_ID=//p' "$ENERGIA/fase4-server/.env" 2>/dev/null | head -1)
TOKEN=$(sed -n 's/^CF_PURGE_TOKEN=//p' "$ENERGIA/fase4-server/.env" 2>/dev/null | head -1)
PURGE="non fatto (CF_ZONE_ID o CF_PURGE_TOKEN mancanti nel .env): fallo a mano"
if [ -n "$ZONA" ] && [ -n "$TOKEN" ]; then
  if [ "$PROVA" = 1 ]; then
    PURGE="[prova] Purge Everything della zona"
  elif curl -fsS -X POST "https://api.cloudflare.com/client/v4/zones/$ZONA/purge_cache" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      --data '{"purge_everything":true}' | grep -q '"success":true'; then
    PURGE="fatto"
  else
    PURGE="NON riuscito: fallo a mano"
  fi
fi
registra "Purge di Cloudflare: $PURGE"

# ------------------------------------------------------------------ 8. fine
[ "$PROVA" = 0 ] && echo "$TAG" > "$STATO"
FINE="Release $TAG $( [ "$PROVA" = 1 ] && echo 'da installare' || echo installata ) (sito ?v=$VERSIONE). Convenzioni cambiate: ${CAMBIATE:-nessuna}. Purge: $PURGE."
[ -n "$MANO" ] && FINE="$FINE Procedure cambiate, controlla i loro passi a mano: $MANO"
registra "$FINE"
rm -f "$ELENCO"
[ "$PROVA" = 1 ] && echo "Prova finita: niente è stato cambiato."
[ "$NOTTE" = 1 ] && avviso "server aggiornato a $TAG" "$FINE"
echo "Controlla: docker compose ps (in $ENERGIA/fase4-server), crontab -l (1 riga, edifici-lidar)."
