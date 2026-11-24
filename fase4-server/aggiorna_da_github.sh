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
#   ~/energia/fase4-server/aggiorna_da_github.sh --notte            dal crontab: solo se c'è una release nuova, email solo se qualcosa va storto
#
# Passi (gli stessi delle procedure AGGIORNAMENTO_*.md):
#   0. rilancio dello script della release (21/11/2026, vedi sotto «Script vecchio contro release nuova»);
#   1. copia del .env in ~/.eugenio_env_backup/env_<data> (permessi 600, si tengono gli ultimi 10), copia di sicurezza di
#      ~/energia (controllata: deve avere fase4-server/docker-compose.yml e il .env; si tengono le ultime 3, ordinate con il
#      file .eugenio_copia scritto dentro ogni copia, mai la data della cartella) e delle convenzioni del server;
#   2. codice delle fasi 3, 4, 6, 7, 8, 9, 10, 15 e fase5-sito/novita.toml in ~/energia (rsync senza cancellare: restano
#      .env, fase 2, uni_privato, mercati_energia/dati e tutto ciò che non è nel repository);
#   3. convenzioni (*.toml e fonti/) in /srv/energia/dati/mercati/convenzioni, con l'elenco di quelle cambiate;
#   4. controllo dei COPY di api/Dockerfile (ogni percorso deve esistere in ~/energia: se manca qualcosa si rimette il codice
#      di prima e ci si ferma SENZA toccare i container); docker compose build api, up -d --force-recreate api worker,
#      attesa dell'api «healthy»; se non lo diventa entro 3 minuti si torna da soli alla copia di sicurezza;
#   5. sito in /srv/energia/sito (rsync senza cancellare; dati/indicatori, dati/prezzi, dati/elettricita, dati/carichi,
#      dati/suolo e (22/11/2026) dati/radar, scritti dal worker, non si toccano), controllo della
#      versione ?v= di index.html;
#   6. file degli indici dei prezzi (worker «prezzi»);
#   7. Purge Everything su Cloudflare, se nel .env ci sono CF_ZONE_ID e CF_PURGE_TOKEN (token con il solo permesso
#      «Zone › Cache Purge»);
#   8. versione installata in ~/.eugenio_versione; elenco dei file AGGIORNAMENTO_*.md cambiati: i loro «passi a mano»
#      (archivi, righe nuove del .env, crontab…) lo script NON li fa, li scrive alla fine e nel registro.
# Email all'amministratore (decisione di Paolo del 16/11/2026): solo se qualcosa va storto (aggiornamento fallito e ritorno
# alla versione di prima, errore imprevisto con --notte, Purge o indici dei prezzi non riusciti); se va tutto bene, niente.
# I segreti restano nel .env del server: lo script li legge solo per il Purge e non li stampa mai.
#
# Correzioni del 21/11/2026 (aggiornamento a v2026.11.21 fallito e ~/energia cancellata, AGGIORNAMENTO_2026-11-22.md):
# - Script vecchio contro release nuova. Prima girava lo script della versione INSTALLATA, che non conosce le cartelle e i
#   passi della release nuova (v2026.11.20d non copiava fase15-elettricita, che il Dockerfile di v2026.11.21 usa). Ora,
#   subito dopo il checkout del tag nel clone, se $CLONE/fase4-server/aggiorna_da_github.sh è diverso da quello in
#   esecuzione, si rilancia (exec) quello del tag con gli stessi argomenti e la release già scelta, con
#   EUGENIO_RILANCIATO=1 che impedisce un secondo rilancio. Scelto al posto di «leggere le CARTELLE da un file del tag»
#   perché copre ogni cambiamento della procedura (cartelle, esclusioni, controlli, passi nuovi), non solo l'elenco delle
#   cartelle: ogni release si installa con lo script provato insieme a lei. Il rilancio avviene prima di qualunque copia o
#   modifica; il controllo dei COPY (passo 4) resta come rete di sicurezza.
# - torna_indietro non cancella mai ~/energia: controlla che la copia esista e abbia docker-compose.yml e il .env, la copia
#   in ~/energia.ripristino_<data>, sposta ~/energia in ~/energia.fallita_<data> e mette la copia al suo posto. Se la copia
#   non va bene non tocca niente (i container di prima restano accesi), registra l'errore e manda l'avviso.
# - Pulizia delle copie: cp -a conserva la data della cartella di origine, quindi «ls -t» cancellava proprio la copia
#   appena fatta. Ora l'ordine viene dal file .eugenio_copia (secondi, versione contenuta, release); la copia appena fatta e
#   quelle della versione installata non si cancellano mai. Con --forza su una release già provata la copia esistente
#   non si sovrascrive: la nuova prende un suffisso _<data>.
# Variabili per le prove (fase4-server/tests/test_aggiorna_da_github.py): EUGENIO_ENV_BACKUP (~/.eugenio_env_backup),
# EUGENIO_ATTESA (5 secondi tra un controllo di /api/salute e l'altro).
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
ENV_BACKUP="${EUGENIO_ENV_BACKUP:-$HOME/.eugenio_env_backup}"
ATTESA="${EUGENIO_ATTESA:-5}"
ADESSO=$(date '+%Y%m%d-%H%M%S')
CARTELLE=(fase3-storico fase4-server fase6-mercati fase7-territorio fase8-indicatori fase9-clima-storico fase10-edifici3d
          fase15-elettricita fase16-suolo fase17-cer-fv)
ESCLUSI=(--exclude=.env --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=uni_privato
         --exclude=fase2-gradi-giorno --exclude=mercati_energia/dati/ --exclude=node_modules)

PROVA=0; FORZA=0; NOTTE=0; TAG=""
for a in "$@"; do
  case "$a" in
    --prova) PROVA=1 ;;
    --forza) FORZA=1 ;;
    --notte) NOTTE=1 ;;
    -h|--help) sed -n 2,30p "$0"; exit 0 ;;
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

PROBLEMI=""                      # cose andate storte ma non gravi: finiscono nell'email di fine (solo con --notte)
problema() { PROBLEMI="${PROBLEMI:+$PROBLEMI }$*"; }
if [ "$NOTTE" = 1 ]; then         # errore imprevisto di notte (rete, git, rsync…): email, poi set -e chiude lo script
  trap 'avviso "aggiornamento notturno interrotto" "Errore imprevisto alla riga $LINENO di aggiorna_da_github.sh (release ${TAG:-?}). Registro: $REGISTRO"' ERR
fi

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
git -C "$CLONE" -c advice.detachedHead=false checkout -q --force "$TAG"
SORG="$CLONE"

# rilancio dello script della release (21/11/2026): la release si installa con la propria procedura
NUOVO="$SORG/fase4-server/aggiorna_da_github.sh"
if [ -z "${EUGENIO_RILANCIATO:-}" ] && [ -f "$NUOVO" ] && ! cmp -s "$NUOVO" "$EUGENIO_AGG_COPIA"; then
  registra "Lo script della release $TAG è diverso da quello in esecuzione: rilancio quello della release"
  ARG=()
  for a in "$@"; do case "$a" in v*) ;; *) ARG+=("$a") ;; esac; done
  ARG+=("$TAG")
  trap - ERR EXIT
  rm -f "$EUGENIO_AGG_COPIA"
  exec env EUGENIO_RILANCIATO=1 EUGENIO_AGG_COPIA= bash "$NUOVO" "${ARG[@]}"
fi
registra "Aggiornamento da ${PRIMA:-sconosciuta} a $TAG$( [ "$PROVA" = 1 ] && echo ' (prova)')$( [ -n "${EUGENIO_RILANCIATO:-}" ] && echo ', script della release')"
VERSIONE=$(sed -n 's/.*?v=\([0-9]\{8\}[a-z]\?\).*/\1/p' "$SORG/fase5-sito/sito/index.html" | head -1)
registra "Sito della release: ?v=$VERSIONE"

# passi a mano annunciati dalle procedure cambiate tra le due release
MANO=""
if [ -n "$PRIMA" ] && git -C "$CLONE" rev-parse -q --verify "refs/tags/$PRIMA" >/dev/null; then
  MANO=$(git -C "$CLONE" diff --name-only "$PRIMA" "$TAG" -- 'AGGIORNAMENTO_*.md' | tr '\n' ' ')
fi

# ------------------------------------------------------------------ 1. copie di sicurezza
# ~/energia deve esserci e avere il .env: senza, non si tocca niente (dopo il 21/11: ripristino a mano dalla copia del .env)
if [ ! -f "$ENERGIA/fase4-server/docker-compose.yml" ] || [ ! -f "$ENERGIA/fase4-server/.env" ]; then
  registra "ERRORE: $ENERGIA non ha fase4-server/docker-compose.yml o fase4-server/.env: non tocco niente." \
           "Rimetti il .env (copie in $ENV_BACKUP) e rilancia."
  trap - ERR
  avviso "aggiornamento a $TAG non iniziato" "$ENERGIA non ha docker-compose.yml o il .env. Registro: $REGISTRO"
  exit 1
fi

copia_env() {                    # il .env non si perde mai: copia datata, 600, ultime 10
  ( umask 077
    mkdir -p "$ENV_BACKUP"; chmod 700 "$ENV_BACKUP"
    local giorno dest ultimo
    giorno=$(date '+%Y-%m-%d')
    ultimo=$(ls -1 "$ENV_BACKUP" 2>/dev/null | grep '^env_' | sort | tail -1 || true)
    if [ -n "$ultimo" ] && cmp -s "$ENERGIA/fase4-server/.env" "$ENV_BACKUP/$ultimo"; then
      registra "Copia del .env: uguale a $ENV_BACKUP/$ultimo"
    else
      dest="$ENV_BACKUP/env_$giorno"
      [ -e "$dest" ] && dest="$ENV_BACKUP/env_${giorno}_$(date '+%H%M%S')"
      cp "$ENERGIA/fase4-server/.env" "$dest"; chmod 600 "$dest"
      registra "Copia del .env: $dest"
    fi
    ls -1 "$ENV_BACKUP" | grep '^env_' | sort | head -n -10 | while read -r f; do rm -f "$ENV_BACKUP/$f"; done
  )
}

pulisci_copie() {                # ultime 3 copie, in ordine di .eugenio_copia (le copie senza file sono le più vecchie)
  local d t v r elenco tieni
  elenco=$(for d in "$ENERGIA"_prima_*; do
      [ -d "$d" ] || continue
      t=0; v=""; r=""
      [ -f "$d/.eugenio_copia" ] && read -r t v r < "$d/.eugenio_copia" || true
      [[ "$t" =~ ^[0-9]+$ ]] || t=0
      [ -n "$v" ] || v=-                                      # read con IFS di tabulazione fonderebbe i campi vuoti
      printf '%s\t%s\t%s\n' "$t" "$v" "$d"
    done | sort -t $'\t' -k1,1n -k3,3V)
  tieni=$(printf '%s\n' "$elenco" | tail -n 3 | cut -f3)
  printf '%s\n' "$elenco" | while IFS=$'\t' read -r t v d; do
    [ -n "$d" ] || continue
    [ "$d" = "$COPIA" ] && continue                          # mai la copia appena fatta
    [ -n "$PRIMA" ] && [ "$v" = "$PRIMA" ] && continue        # mai una copia della versione installata
    printf '%s\n' "$tieni" | grep -qxF "$d" && continue
    registra "Cancello la copia vecchia $d"
    rm -rf "$d"
  done
}

COPIA="$ENERGIA"_prima_"$TAG"
[ -e "$COPIA" ] && COPIA="${COPIA}_$ADESSO"     # --forza: la copia già fatta (forse l'unica buona) non si tocca
if [ "$PROVA" = 0 ]; then
  copia_env
  cp -a "$ENERGIA" "$COPIA"
  touch "$COPIA"
  printf '%s %s %s\n' "$(date +%s)" "${PRIMA:-sconosciuta}" "$TAG" > "$COPIA/.eugenio_copia"
  if [ ! -f "$COPIA/fase4-server/docker-compose.yml" ] || [ ! -f "$COPIA/fase4-server/.env" ]; then
    registra "ERRORE: la copia di sicurezza $COPIA è incompleta: mi fermo senza toccare niente."
    trap - ERR
    avviso "aggiornamento a $TAG non iniziato" "Copia di sicurezza $COPIA incompleta. Registro: $REGISTRO"
    exit 1
  fi
  registra "Copia di sicurezza: $COPIA"
  cp -a "$CONV" "$HOME/convenzioni_prima_$TAG"
  pulisci_copie
else
  echo "  [prova] copia del .env in $ENV_BACKUP; cp -a $ENERGIA $COPIA; cp -a $CONV $HOME/convenzioni_prima_$TAG"
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
torna_indietro() {               # $1 motivo; $2 = «codice» per rimettere solo i file, senza toccare i container
  trap - ERR
  registra "ERRORE: $1. Torno alla copia di sicurezza $COPIA."
  cd "$HOME"
  if [ ! -f "$COPIA/fase4-server/docker-compose.yml" ] || [ ! -f "$COPIA/fase4-server/.env" ]; then
    registra "ERRORE GRAVE: la copia $COPIA manca o è incompleta (docker-compose.yml o .env): NON tocco $ENERGIA." \
             "I container di prima restano accesi; sistema a mano."
    avviso "aggiornamento a $TAG fallito, ritorno indietro NON fatto" \
      "$1. La copia di sicurezza $COPIA manca o è incompleta: $ENERGIA è rimasta con il codice nuovo, i container di prima sono accesi. Registro: $REGISTRO"
    exit 1
  fi
  local RIPR="$ENERGIA.ripristino_$ADESSO" FALL="$ENERGIA.fallita_$ADESSO"
  if ! cp -a "$COPIA" "$RIPR" || [ ! -f "$RIPR/fase4-server/.env" ]; then
    rm -rf "$RIPR"
    registra "ERRORE GRAVE: copia di $COPIA non riuscita: NON tocco $ENERGIA."
    avviso "aggiornamento a $TAG fallito, ritorno indietro NON fatto" "$1. Copia di $COPIA non riuscita. Registro: $REGISTRO"
    exit 1
  fi
  rm -f "$RIPR/.eugenio_copia"
  mv "$ENERGIA" "$FALL" && mv "$RIPR" "$ENERGIA"
  registra "$ENERGIA rimessa dalla copia; il codice della release fallita è in $FALL"
  ls -1d "$ENERGIA".fallita_* 2>/dev/null | sort | head -n -3 | while read -r f; do rm -rf "$f"; done
  cp "$HOME/convenzioni_prima_$TAG"/*.toml "$CONV/" 2>/dev/null || true
  if [ "${2:-}" != codice ]; then
    (cd "$ENERGIA/fase4-server" && docker compose build api && docker compose up -d --force-recreate api worker) \
      >>"$REGISTRO" 2>&1 || true
    avviso "aggiornamento a $TAG fallito" "$1. Il server è tornato alla versione ${PRIMA:-precedente}. Registro: $REGISTRO"
  else
    avviso "aggiornamento a $TAG fermato" "$1. Container non toccati, codice di ${PRIMA:-prima} rimesso. Registro: $REGISTRO"
  fi
  exit 1
}

controlla_copy() {               # ogni COPY di api/Dockerfile deve trovare il suo percorso; scrive quelli che mancano
  local df="$1" p prima
  awk '                          # righe unite dove finiscono con «\», poi gli argomenti dei COPY tranne la destinazione
    { riga = riga $0 }
    /\\$/ { sub(/\\$/, "", riga); next }
    { n = split(riga, x, /[ \t]+/); riga = ""
      k = 0; for (i = 1; i <= n; i++) if (x[i] != "") y[++k] = x[i]
      if (k < 3 || toupper(y[1]) != "COPY") next
      da = 0; for (i = 2; i <= k; i++) if (y[i] ~ /^--from/) da = 1
      if (da) next
      for (i = 2; i < k; i++) if (y[i] !~ /^--/) print y[i] }' "$df" | while IFS= read -r p; do
    if [ "$PROVA" = 1 ]; then      # in prova ~/energia non cambia: vale anche ciò che la release vi copierebbe
      prima=${p%%/*}
      compgen -G "$ENERGIA/$p" >/dev/null && continue
      if [ "$p" = fase5-sito/novita.toml ] || printf '%s\n' "${CARTELLE[@]}" | grep -qxF "$prima"; then
        compgen -G "$SORG/$p" >/dev/null && continue
      fi
    else
      compgen -G "$ENERGIA/$p" >/dev/null && continue
    fi
    echo "$p"
  done
}

DOCKERFILE="$ENERGIA/fase4-server/api/Dockerfile"
[ "$PROVA" = 1 ] && DOCKERFILE="$SORG/fase4-server/api/Dockerfile"
MANCANO=$(controlla_copy "$DOCKERFILE" | tr '\n' ' ')
if [ -n "$MANCANO" ]; then
  if [ "$PROVA" = 1 ]; then
    echo "  [prova] ATTENZIONE: il Dockerfile copia percorsi che non ci sarebbero in $ENERGIA: $MANCANO"
  else
    torna_indietro "il Dockerfile copia percorsi che mancano in $ENERGIA ($MANCANO): build non lanciata" codice
  fi
else
  registra "Dockerfile: tutti i percorsi dei COPY ci sono"
fi
if [ "$PROVA" = 0 ]; then
  cd "$ENERGIA/fase4-server"
  docker compose build api >>"$REGISTRO" 2>&1 || torna_indietro "build dell'immagine non riuscita"
  docker compose up -d --force-recreate api worker >>"$REGISTRO" 2>&1 || torna_indietro "avvio dei container non riuscito"
  for _ in $(seq 1 36); do
    sleep "$ATTESA"
    if docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/salute')" \
        >/dev/null 2>&1; then OK=1; break; fi
  done
  [ "${OK:-0}" = 1 ] || torna_indietro "l'api non risponde dopo 3 minuti"
  registra "api e worker aggiornati e funzionanti"
else
  echo "  [prova] docker compose build api; up -d --force-recreate api worker; attesa di /api/salute"
fi

# ------------------------------------------------------------------ 5. sito
S=(rsync -a -i --exclude=dati/indicatori/ --exclude=dati/prezzi/ --exclude=dati/elettricita/ --exclude=dati/carichi/
   --exclude=dati/suolo/ --exclude=dati/radar/)
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
    || { registra "Avviso: file degli indici dei prezzi non rifatto (si rifà stanotte con i mercati)"
         problema "File degli indici dei prezzi non rifatto (si rifà la notte dopo con i mercati)."; }
fi

# ------------------------------------------------------------------ 7. Purge di Cloudflare
ZONA=$(sed -n 's/^CF_ZONE_ID=//p' "$ENERGIA/fase4-server/.env" 2>/dev/null | head -1 || true)
TOKEN=$(sed -n 's/^CF_PURGE_TOKEN=//p' "$ENERGIA/fase4-server/.env" 2>/dev/null | head -1 || true)
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
    problema "Purge di Cloudflare non riuscito: fallo a mano da https://dash.cloudflare.com/ (statocritico.it › Caching › Configuration › Purge Everything)."
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
if [ "$NOTTE" = 1 ] && [ -n "$PROBLEMI" ]; then   # di notte, email solo se qualcosa non è andato
  avviso "server aggiornato a $TAG, ma con problemi" "$PROBLEMI $FINE"
fi
[ "$NOTTE" = 1 ] || echo "Controlla: docker compose ps (in $ENERGIA/fase4-server) e crontab -l (edifici-lidar alle 3:30, aggiorna_da_github.sh --notte alle 4:40)."
exit 0
