#!/usr/bin/env bash
# Crea l'istanza `eugenio` (Ampere A1, 2 OCPU / 12 GB, Ubuntu 24.04, disco 100 GB) e, se Oracle
# risponde "Out of host capacity", riprova da solo finché non ci riesce.
#
# Funziona dove c'è la OCI CLI già configurata:
#   - Cloud Shell della console Oracle (nessuna installazione, ma la sessione si chiude dopo
#     60 minuti di inattività e comunque dopo 24 ore: adatto a qualche ora di tentativi);
#   - WSL2 sul PC (consigliato per giorni di tentativi): vedi il README della fase 1, punto 6 ter.
#
# Uso:
#   bash 02_crea_istanza.sh --chiave ~/oracle_energia.pub            # riprova ogni 5 minuti
#   bash 02_crea_istanza.sh --chiave ~/oracle_energia.pub --ogni 120 --piccola
#
# Opzioni:
#   --chiave FILE   chiave SSH pubblica (la riga di oracle_energia.pub)           [obbligatoria]
#   --ogni SECONDI  pausa fra un tentativo e l'altro (predefinita 300, minimo 60)
#   --piccola       chiede 1 OCPU / 6 GB (più facile da trovare; si ingrandisce dopo da console)
#   --prova         controlla rete, immagine e chiave senza creare nulla
#
# Non crea nulla di a pagamento: shape, OCPU, RAM e disco sono quelli Always Free e la quota
# `solo-always-free` blocca comunque qualsiasi eccesso. Nessun segreto in questo file.
set -euo pipefail

REGIONE="eu-milan-1"
NOME="eugenio"
SUBNET_NOME="public subnet-eugenio-vcn"
OCPU=2; RAM=12; DISCO=100
OGNI=300; CHIAVE=""; PROVA=0

while [ $# -gt 0 ]; do
  case "$1" in
    --chiave) CHIAVE="$2"; shift 2 ;;
    --ogni) OGNI="$2"; shift 2 ;;
    --piccola) OCPU=1; RAM=6; shift ;;
    --prova) PROVA=1; shift ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "Opzione sconosciuta: $1" >&2; exit 2 ;;
  esac
done

registro() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$HOME/crea_istanza.log"; }
fermati() { registro "ERRORE: $*"; exit 1; }

command -v oci >/dev/null || fermati "OCI CLI non trovata (in Cloud Shell c'è già; in WSL vedi il README, punto 6 ter)"
[ -n "$CHIAVE" ] || fermati "manca --chiave FILE con la chiave SSH pubblica"
[ -f "$CHIAVE" ] || fermati "chiave non trovata: $CHIAVE"
grep -q '^ssh-' "$CHIAVE" || fermati "$CHIAVE non sembra una chiave pubblica (deve iniziare con ssh-ed25519 o ssh-rsa)"
[ "$OGNI" -ge 60 ] 2>/dev/null || OGNI=60

# Tenancy (= compartment root): in Cloud Shell c'è la variabile OCI_TENANCY, altrimenti il file di config
TENANCY="${OCI_TENANCY:-}"
if [ -z "$TENANCY" ] && [ -f "$HOME/.oci/config" ]; then
  TENANCY=$(awk -F= '/^tenancy/{gsub(/ /,"",$2); print $2; exit}' "$HOME/.oci/config")
fi
[ -n "$TENANCY" ] || fermati "OCID della tenancy non trovato (manca ~/.oci/config: eseguire 'oci setup config')"

O="--region $REGIONE"

# OCID dell'istanza `eugenio` non terminata, se esiste
esistente() {
  local id
  id=$(oci compute instance list $O -c "$TENANCY" --display-name "$NOME" --all \
    --query 'data[?"lifecycle-state"!=`TERMINATED` && "lifecycle-state"!=`TERMINATING`] | [0].id' \
    --raw-output 2>/dev/null || true)
  [ -n "$id" ] && [ "$id" != "null" ] && echo "$id"
  return 0
}

concluso() {
  local ip
  ip=$(oci compute instance list-vnics $O --instance-id "$1" --query 'data[0]."public-ip"' --raw-output 2>/dev/null || echo "?")
  registro "Istanza $NOME: $1"
  registro "IP pubblico: $ip  →  ssh -i \$HOME\\.ssh\\oracle_energia ubuntu@$ip"
  printf '\a'
  exit 0
}

ESISTE=$(esistente)
if [ -n "$ESISTE" ]; then
  registro "L'istanza $NOME esiste già: niente da creare."
  concluso "$ESISTE"
fi

AD=$(oci iam availability-domain list $O -c "$TENANCY" --query 'data[0].name' --raw-output)
SUBNET=$(oci network subnet list $O -c "$TENANCY" --all \
  --query "data[?\"display-name\"=='$SUBNET_NOME'] | [0].id" --raw-output)
[ -n "$SUBNET" ] && [ "$SUBNET" != "null" ] || fermati "subnet '$SUBNET_NOME' non trovata: creare prima la rete (README, punto 6)"
IMMAGINE=$(oci compute image list $O -c "$TENANCY" --operating-system "Canonical Ubuntu" \
  --operating-system-version "24.04" --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC --all \
  --query 'data[?!contains("display-name", `Minimal`)] | [0].id' --raw-output)
[ -n "$IMMAGINE" ] && [ "$IMMAGINE" != "null" ] || fermati "immagine Ubuntu 24.04 per A1 non trovata"

registro "Regione $REGIONE, AD $AD, shape A1 $OCPU OCPU / $RAM GB, disco $DISCO GB"
registro "Subnet $SUBNET"
registro "Immagine $IMMAGINE"
if [ "$PROVA" = 1 ]; then registro "Prova riuscita: tutto pronto per la creazione."; exit 0; fi

tentativo=0
while true; do
  tentativo=$((tentativo + 1))
  # se un tentativo precedente è andato a buon fine ma l'attesa è scaduta, non se ne crea una seconda
  ESISTE=$(esistente)
  [ -n "$ESISTE" ] && concluso "$ESISTE"
  set +e
  USCITA=$(oci compute instance launch $O \
    --availability-domain "$AD" -c "$TENANCY" --display-name "$NOME" \
    --shape VM.Standard.A1.Flex --shape-config "{\"ocpus\": $OCPU, \"memoryInGBs\": $RAM}" \
    --image-id "$IMMAGINE" --boot-volume-size-in-gbs "$DISCO" \
    --subnet-id "$SUBNET" --assign-public-ip true --vnic-display-name "$NOME-vnic" \
    --ssh-authorized-keys-file "$CHIAVE" \
    --wait-for-state RUNNING --max-wait-seconds 900 2>&1)
  ESITO=$?
  set -e
  if [ $ESITO -eq 0 ]; then
    registro "CREATA al tentativo $tentativo."
    concluso "$(echo "$USCITA" | grep -o 'ocid1.instance[^"]*' | head -1)"
  fi
  case "$USCITA" in
    *"Out of host capacity"*|*"OutOfCapacity"*|*"out of capacity"*)
      attesa=$OGNI; motivo="nessuna A1 libera" ;;
    *"LimitExceeded"*|*"QuotaExceeded"*|*"quotas were exceeded"*)
      fermati "quota o limite superato: controllare la quota solo-always-free (README, punto 3). Dettagli: $(echo "$USCITA" | grep -m1 -i message)" ;;
    *"TooManyRequests"*|*'"status": 429'*)
      attesa=$((OGNI * 2)); motivo="troppe richieste, rallento" ;;
    *"InternalError"*|*"ServiceUnavailable"*|*"timed out"*|*"Connection"*)
      attesa=$OGNI; motivo="errore temporaneo di Oracle" ;;
    *)
      fermati "errore inatteso, mi fermo. Dettagli: $(echo "$USCITA" | tail -5 | tr '\n' ' ')" ;;
  esac
  # un po' di variazione casuale per non bussare sempre allo stesso secondo
  attesa=$((attesa + RANDOM % 60))
  registro "Tentativo $tentativo: $motivo. Riprovo fra $attesa s."
  sleep "$attesa"
done
