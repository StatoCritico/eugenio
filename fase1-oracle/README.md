# Fase 1 – Oracle Cloud: account PAYG, protezioni di spesa, server

Obiettivo: un server Ubuntu ARM con **2 OCPU, 12 GB di RAM e 100 GB di disco**, gratuito
(risorse *Always Free*), protetto da quote e avvisi di spesa, pronto per Docker.

Tempo stimato: 1–2 ore. Serve una carta di credito/debito (solo verifica e pre-autorizzazione).

> **Aggiornato con la prova del 25/10/2026.** La console Oracle è cambiata rispetto alle prime
> istruzioni: i passi qui sotto seguono le schermate attuali. I limiti Always Free di Ampere A1 sono
> **2 OCPU e 12 GB** (ridotti nel 2026 da 4/24): la console li mostra come "0 of 2" e "0 of 12".

---

## 1. Registrazione

1. Vai su <https://signup.cloud.oracle.com> e crea l'account *Free Tier*.
2. **Home region: Italy Northwest (Milan) – `eu-milan-1`**. Non si cambia più: le risorse gratuite
   esistono solo nella home region. In alternativa Germany Central (Frankfurt).
3. Completa la verifica con la carta e attiva l'autenticazione a due fattori (Oracle Mobile Authenticator
   o un'app TOTP) quando richiesta.

## 2. Passaggio a Pay As You Go (PAYG)

Perché: con l'account solo Always Free le istanze "inattive" possono essere recuperate da Oracle;
con PAYG no, e **le risorse Always Free restano gratuite**.

### Always Free o PAYG? (rivalutazione, ottobre 2026)

Una precisazione prima: il server **non usa una GPU**. Le istanze Always Free (Ampere A1 ARM ed
E2.1.Micro) non hanno GPU; TiRex-2 gira sul processore. Quindi la scelta non dipende dalla GPU,
ma dalla regola sulle istanze inattive. Oracle recupera un'istanza Always Free se, su 7 giorni:
- l'uso della CPU al 95° percentile è sotto il 20 %, **e**
- l'uso della rete è sotto il 20 %, **e**
- (solo per A1) l'uso della memoria è sotto il 20 %.

Il nostro carico tipico: previsioni meteo ogni 6 ore e dati di mercato di notte (qualche minuto),
qualche previsione TiRex-2 al giorno (~5 secondi ciascuna), memoria ~3–4 GB su 12 (25–35 %).
La CPU resta quasi sempre ferma; la memoria è appena sopra la soglia e scenderebbe sotto se si
riavviasse l'API senza previsioni in corso (il modello si carica alla prima richiesta). È un margine
troppo sottile per un servizio che deve restare acceso.

| | Solo Always Free | PAYG con quote e budget (consigliato) |
|---|---|---|
| Costo | 0 € | 0 € finché si resta nei limiti Always Free; le quote impediscono di uscirne |
| Recupero per inattività | possibile: si perdono istanza e disco | no |
| Disponibilità di macchine A1 | spesso "Out of host capacity" | di norma migliore |
| Carta di credito | richiesta comunque all'iscrizione | idem; avviso al primo centesimo |
| Rischio | perdere il server senza preavviso | addebito solo per errore di configurazione, bloccato dalle quote |

Restare solo Always Free è possibile, ma bisognerebbe tenere occupata la macchina apposta
(carichi fittizi) e fare backup regolari: non ne vale la pena. **Consiglio: PAYG con le quote del
punto 3 e il budget del punto 4.** Se si preferisce non fare il passaggio, saltare questo punto
e attivare comunque i backup del punto 9.

1. Console → menu ☰ → **Billing & Cost Management → Upgrade and Manage Payment**.
2. **Upgrade to Pay As You Go**, conferma i dati di pagamento.
3. Attendi l'email di conferma (da pochi minuti ad alcune ore). Oracle può fare una pre-autorizzazione
   temporanea sulla carta, poi annullata.

**Account appena creato:** finché Oracle non ha finito di attivare la tenancy (può volerci da qualche ora
a un giorno, arriva un'email) il pulsante di upgrade resta disattivato. Nel frattempo si possono fare i
punti 3–6 (quote, budget, chiave SSH, rete); l'istanza conviene crearla dopo l'upgrade (vedi punto 6 bis,
"Out of capacity").

## 3. Quote: impedire di creare risorse a pagamento

Le quote bloccano *a monte* la creazione di risorse oltre i limiti gratuiti (gli avvisi di spesa
arrivano solo dopo).

Console → ☰ → **Governance & Administration → Tenancy Management → Quota Policies → Create Quota Policy**
- Nome: `solo-always-free`
- Compartment: la root (tenancy)
- Description: una frase qualsiasi (es. "Blocca la creazione di risorse oltre i limiti Always Free")
- Dichiarazioni (copiale da [`quote.txt`](quote.txt)):

```
zero compute-core quotas in tenancy
set compute-core quota standard-a1-core-count to 2 in tenancy
set compute-core quota standard-a1-core-regional-count to 2 in tenancy
set compute-core quota standard-e2-micro-core-count to 2 in tenancy
zero compute-memory quotas in tenancy
set compute-memory quota standard-a1-memory-count to 12 in tenancy
set compute-memory quota standard-a1-memory-regional-count to 12 in tenancy
set block-storage quota total-storage-gb to 200 in tenancy
set block-storage quota backup-count to 5 in tenancy
```

Attenzione:
- **Nessuna riga vuota in fondo** (né in cima o in mezzo): Oracle la legge come una dichiarazione vuota
  e risponde `Syntax error starting with '' at statement N char 0`.
- Oracle conta le A1 con i nomi **regionali** (`standard-a1-core-regional-count`,
  `standard-a1-memory-regional-count`). Senza quelle due righe le `zero` le azzerano e la creazione
  dell'istanza fallisce con *"The following compartment quotas were exceeded:
  standard-a1-core-regional-count … by 2"*. I nomi vecchi restano per sicurezza: se la console ne
  rifiuta uno perché non esiste più, cancellalo.
- Per modificare la policy: aprila → **Manage quota policy** → aggiorna le dichiarazioni. I due tag
  `Oracle-Tags` (CreatedBy, CreatedOn) li aggiunge Oracle da solo.
- In caso di dubbio sui nomi: **Governance & Administration → Limits, Quotas and Usage** (servizio
  *Compute*, voce *Ampere A1*).

## 4. Budget e avvisi di spesa

Console → ☰ → **Billing & Cost Management → Budgets → Create Budget**
- Nome: `allarme-spesa`, compartment target: root, **importo mensile 1 €**, giorno di reset 1.
- **Alert rule 1**: *Threshold metric* = **Actual Spend**, *Threshold type* = **Absolute amount**,
  valore **0,01** → email al tuo indirizzo. Ti avvisa al primo centesimo addebitato.
- **Alert rule 2**: **Forecast Spend**, **Percentage of budget**, **100** → email.

Note: gli avvisi sono solo email (non bloccano nulla), sono valutati circa una volta al giorno e la
previsione si attiva dopo almeno 3 giorni di consumi. Nei primi giorni controlla anche
**Billing & Cost Management → Cost Analysis**.

## 5. Chiave SSH (sul tuo PC Windows)

In PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.ssh      # su Windows la cartella può non esistere
ssh-keygen -t ed25519 -C "oracle-energia" -f $HOME\.ssh\oracle_energia
Get-Content $HOME\.ssh\oracle_energia.pub   # questa riga va incollata in Oracle
```

Senza la cartella `.ssh` il comando risponde `Saving key ... failed: No such file or directory`.
La passphrase è consigliata (va digitata a ogni accesso). Il file senza `.pub` è la chiave privata:
non si condivide mai.

## 6. Rete (prima dell'istanza)

Se la rete viene creata dentro il modulo dell'istanza, l'interruttore dell'IP pubblico resta bloccato
("You must select a public subnet to assign a public IPv4 address"). Si crea quindi prima, con la
procedura guidata, che prepara anche internet gateway e regola per la porta 22:

1. Barra di ricerca → **Virtual cloud networks** (regione Milan, compartment root).
2. **Actions → Start VCN Wizard** (non *Create VCN*, che crea una rete senza accesso a internet).
3. **Create VCN with Internet Connectivity** → nome `eugenio-vcn`, blocchi di indirizzi proposti
   (`10.0.0.0/16`, subnet pubblica `10.0.0.0/24`, privata `10.0.1.0/24`), IPv6 spento → **Create**.

Subnet privata e NAT gateway creati dal wizard sono gratuiti e possono restare.

## 6 bis. Creazione dell'istanza

Console → ☰ → **Compute → Instances → Create instance**. Oracle propone Oracle Linux su
VM.Standard.E2.1.Micro (1 GB): vanno cambiati entrambi.

**1 Basic information**
- Nome: `eugenio`; compartment root; availability domain AD-1 (Milano ne ha uno solo).
- **Change shape** *prima* dell'immagine: *Virtual machine* → serie **Ampere** → **VM.Standard.A1.Flex**,
  aperta con la freccetta: **2 OCPU, 12 GB** → *Select shape*.
  L'avviso *"Service limits status: some resource limit is critical"* è normale: elenca le due voci A1
  ("0 of 2", "0 of 12") perché l'istanza le userà al 100 %.
- **Change image** → Ubuntu → **Canonical Ubuntu 24.04** (non *Minimal*, non 26.04). La voce non porta
  "aarch64" nel nome: contiene sia la build x86 sia quella ARM e Oracle sceglie quella adatta alla shape.
- Advanced options: lasciare tutto (metadata service attivo, nessuno script cloud-init, nessun tag,
  live migration scelta da Oracle, *Restore instance lifecycle state* attivo, plugin predefiniti).
- *Estimated cost* (es. 1,85 €/mese per il boot volume) è il prezzo di listino: la nota *"does not
  reflect any tier unit pricing"* significa che non toglie le risorse Always Free.

**2 Security**: Shielded instance spento; Confidential computing non disponibile su A1 (avviso
normale); nessun security attribute.

**3 Networking**
- VNIC name `eugenio-vnic`; **Select existing virtual cloud network** → `eugenio-vcn`;
  **Select existing subnet** → `public subnet-eugenio-vcn`.
- **Automatically assign public IPv4 address**: attivo. Serve per l'SSH da casa (il sito passa dal tunnel).
- IPv6 spento.
- **Add SSH keys** → **Paste public key** (non "Generate a key pair for me") → la riga del punto 5.

**4 Storage**: **Specify a custom boot volume size** attivo → **100 GB**, prestazioni **Balanced
(10 VPU/GB)** (le prestazioni più alte si pagano); in-transit encryption attiva; chiave gestita da
Oracle; nessun block volume. L'uso previsto è ~15 GB (~35 GB con l'istanza Open-Meteo propria): restano
100 GB dei 200 gratuiti per un volume di backup.

**Review** → controllare shape, immagine, *Public IPv4 address: Yes*, chiave SSH, 100 GB → **Create**.

**"Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1"**: a Milano non ci
sono macchine A1 libere (il 25/10/2026 nemmeno da 1 OCPU/6 GB). Milano ha un solo availability domain e
la home region non si cambia, quindi:
1. passare a PAYG (punto 2): gli account a consumo hanno la precedenza sulle A1;
2. riprovare *Create* in altri momenti (mattina presto, sera tardi);
3. lasciare che ci riprovi lo script [`02_crea_istanza.sh`](02_crea_istanza.sh) (punto 6 ter).
Partire con 1 OCPU/6 GB e ingrandire dopo (*Edit → Shape*, con riavvio) è possibile, ma richiede
comunque capacità libera.

La home region **non si può cambiare** (FAQ Oracle: "Oracle assigns your home region and you can't change
it") e le istanze Always Free si creano solo lì: un'istanza A1 a Francoforte sarebbe a pagamento. In
Austria Oracle non ha regioni. Rifare l'account con un'altra home region è sconsigliato: Oracle ammette
un solo account gratuito per persona e anche Francoforte è spesso senza A1 libere.

## 6 ter. Creazione automatica con ritentativi (`02_crea_istanza.sh`)

Lo script crea la stessa istanza del punto 6 bis (A1 2 OCPU/12 GB, Ubuntu 24.04, 100 GB, subnet
pubblica di `eugenio-vcn`, IP pubblico, chiave SSH `oracle_energia.pub`) e, finché Oracle risponde
"Out of host capacity", riprova ogni 5 minuti (con qualche secondo casuale in più). Si ferma da solo
quando l'istanza esiste, scrive IP e comando SSH ed emette un segnale acustico. Si ferma anche su
errori di quota (punto 3) o inattesi, invece di insistere. Prima di ogni tentativo controlla se
l'istanza c'è già, così non ne crea mai due. Registro in `~/crea_istanza.log`. Funziona anche prima
del passaggio a PAYG.

Opzioni: `--prova` (controlla rete, immagine e chiave senza creare nulla), `--ogni SECONDI` (minimo 60),
`--piccola` (1 OCPU/6 GB, da ingrandire poi da console).

### Dal PC, in WSL (consigliato: può girare per giorni)

Una volta sola, nel terminale Ubuntu di WSL:

```bash
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)" -s --accept-all-defaults
exec -l $SHELL          # ricarica il PATH
oci setup config
```

`oci setup config` chiede:
- **user OCID**: console → icona del profilo in alto a destra → *My profile* → OCID (*Copy*);
- **tenancy OCID**: icona del profilo → *Tenancy: …* → OCID;
- **region**: `eu-milan-1`;
- genera una nuova coppia di chiavi API (Y), percorso proposto, passphrase facoltativa.

Poi in console: icona del profilo → *My profile* → **API keys → Add API key → Paste a public key** e
incollare il contenuto di `~/.oci/oci_api_key_public.pem` (`cat ~/.oci/oci_api_key_public.pem`). La
chiave privata resta in `~/.oci` e non va mai copiata altrove. Verifica: `oci iam region list`.

Avvio (in `tmux`, così si può chiudere la finestra del comando senza fermarlo):

```bash
sudo apt install -y tmux
tmux new -s oracle
cd /mnt/c/Users/ingpa/Documents/claude/pj/statocritico/eugenio/fase1-oracle
bash 02_crea_istanza.sh --chiave /mnt/c/Users/ingpa/.ssh/oracle_energia.pub --prova
bash 02_crea_istanza.sh --chiave /mnt/c/Users/ingpa/.ssh/oracle_energia.pub
# Ctrl+B poi D per staccarsi; `tmux attach -t oracle` per rivederlo; `tail ~/crea_istanza.log`
```

WSL resta acceso finché c'è un terminale Ubuntu aperto (anche ridotto a icona) o un container Docker in
esecuzione; il PC non deve andare in sospensione.

### Da Cloud Shell (senza installare nulla, per qualche ora)

Console → icona **Cloud Shell** (>_) in alto → menu ⚙ → **Upload**: caricare `02_crea_istanza.sh` e
`oracle_energia.pub`. Poi:

```bash
bash 02_crea_istanza.sh --chiave oracle_energia.pub --prova
bash 02_crea_istanza.sh --chiave oracle_energia.pub
```

Cloud Shell chiude la sessione dopo 60 minuti di inattività e comunque dopo 24 ore (documentazione Oracle), e
con lei lo script: va bene per una sera di tentativi, non per giorni.

Annota l'**indirizzo IP pubblico** dell'istanza.

## 7. Porte di rete (firewall Oracle)

Il sito è pubblicato con **Cloudflare Tunnel** (fase 4): il server apre lui la connessione verso
Cloudflare, quindi **non serve aprire nessuna porta** oltre a SSH (22), già aperta. Se il tuo IP di
casa è fisso, restringi anche la 22 a quell'indirizzo (*Security List → regola della porta 22 →
Source CIDR* `tuo.ip/32`).

(Solo se un giorno si volesse pubblicare senza Cloudflare: aprire 80 e 443 nella Security List e
lanciare `sudo bash 01_setup_server.sh --apri-web`.)

## 8. Primo accesso e preparazione del server

```powershell
ssh -i $HOME\.ssh\oracle_energia ubuntu@IP_PUBBLICO
```

Sul server:

```bash
git clone https://github.com/statocritico/eugenio.git energia   # oppure copia la cartella con scp
# la fase 2 (daemon personale) non è nel repository pubblico: copiarla a parte con scp
cd energia/fase1-oracle
sudo bash 01_setup_server.sh
```

Lo script ([`01_setup_server.sh`](01_setup_server.sh)):
- aggiorna il sistema e attiva gli aggiornamenti di sicurezza automatici;
- imposta il fuso orario Europe/Rome e 4 GB di swap;
- installa **fail2ban** (protezione SSH) e **Docker** (serve alla fase 4);
- lascia chiuse le porte web (con `--apri-web` le apre anche nel firewall interno di Ubuntu);
- disattiva l'accesso SSH con password.

Al termine riavvia (`sudo reboot`) e ricollegati.

## 9. Backup

Console → Block Storage → Boot Volumes → il volume dell'istanza → *Boot Volume Backups*: una policy
"Bronze" (backup mensile) resta nei 5 backup gratuiti. In più, i dati che contano (archivio meteo,
dati di mercato, database della mailing list) sono piccoli: conviene copiarli anche sul PC ogni tanto
(`scp -r ubuntu@IP:/srv/energia/dati ./backup-energia`).

## 10. Verifica finale

- [ ] Account in stato **Pay As You Go** (Billing → Subscriptions)
- [ ] Quota policy `solo-always-free` attiva
- [ ] Budget con i due avvisi
- [ ] Rete `eugenio-vcn` creata con il wizard (subnet pubblica)
- [ ] Istanza `eugenio` A1 2 OCPU/12 GB in esecuzione, IP pubblico, boot volume 100 GB
- [ ] `docker run --rm hello-world` funziona
- [ ] Dopo 2–3 giorni, **Cost Analysis** mostra 0,00 €

## Costi

Tutto quanto sopra rientra nelle risorse Always Free (A1 fino a 2 OCPU/12 GB, 200 GB di block volume,
10 TB/mese di traffico in uscita). Fonte: <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm>
