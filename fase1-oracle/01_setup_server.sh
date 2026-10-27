#!/usr/bin/env bash
# Preparazione del server Oracle (Ubuntu 24.04 ARM). Eseguire una sola volta:  sudo bash 01_setup_server.sh
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Eseguire con sudo"; exit 1; fi
export DEBIAN_FRONTEND=noninteractive

echo ">> Aggiornamento del sistema"
apt-get update -qq
apt-get -y -qq upgrade
apt-get -y -qq install ca-certificates curl gnupg git unattended-upgrades fail2ban \
  netfilter-persistent iptables-persistent python3-venv sqlite3 htop

echo ">> Aggiornamenti di sicurezza automatici"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo ">> Fuso orario"
timedatectl set-timezone Europe/Rome

echo ">> Swap 4 GB"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
sysctl -w vm.swappiness=10 >/dev/null
grep -q 'vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf

APRI_WEB=0
[[ "${1:-}" == "--apri-web" ]] && APRI_WEB=1
if [[ $APRI_WEB -eq 1 ]]; then
echo ">> Firewall interno: apertura porte 80 e 443"
# Le immagini Ubuntu di Oracle hanno regole iptables che rifiutano tutto tranne SSH:
# inseriamo le nuove regole prima della regola REJECT finale.
for p in 80 443; do
  if ! iptables -C INPUT -p tcp -m state --state NEW --dport $p -j ACCEPT 2>/dev/null; then
    pos=$(iptables -L INPUT --line-numbers | awk '/REJECT/ {print $1; exit}')
    if [[ -n "${pos:-}" ]]; then
      iptables -I INPUT "$pos" -p tcp -m state --state NEW --dport $p -j ACCEPT
    else
      iptables -A INPUT -p tcp -m state --state NEW --dport $p -j ACCEPT
    fi
  fi
done
netfilter-persistent save >/dev/null
else
  echo ">> Porte web chiuse: il sito passa da Cloudflare Tunnel (fase 4)"
fi

echo ">> SSH solo con chiave"
cat > /etc/ssh/sshd_config.d/99-energia.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
systemctl reload ssh || systemctl reload sshd || true

echo ">> fail2ban"
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
bantime = 1h
EOF
systemctl enable --now fail2ban >/dev/null

echo ">> Docker (repository ufficiale)"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get -y -qq install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
usermod -aG docker "${SUDO_USER:-ubuntu}"
# rotazione dei log dei container
cat > /etc/docker/daemon.json <<'EOF'
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "3" } }
EOF
systemctl restart docker

mkdir -p /srv/energia
chown "${SUDO_USER:-ubuntu}:${SUDO_USER:-ubuntu}" /srv/energia

echo
echo "Fatto. Riavvia con 'sudo reboot' e ricollegati: dopo il riavvio 'docker run --rm hello-world'"
echo "deve funzionare senza sudo."
