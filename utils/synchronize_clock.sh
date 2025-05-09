#!/bin/bash

SCRIPT_PATH="/usr/local/bin/smart_time_sync.sh"
LOG_FILE="/var/log/smart_time_sync.log"

echo "📦 Installation du script de synchronisation intelligente..."

# Création du script principal
sudo bash -c "cat > $SCRIPT_PATH" <<'EOF'
#!/bin/bash

echo "⏱️ Tentative de synchronisation de l'heure (NTP via Chrony)..."

if ! command -v chronyc &> /dev/null; then
    echo "📦 Installation de chrony..."
    apt update -y
    apt install -y chrony
fi

echo "🛠️ Configuration de chrony avec time.google.com..."
cat > /etc/chrony/chrony.conf <<EOC
server time.google.com iburst
driftfile /var/lib/chrony/chrony.drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
EOC

echo "🔁 Redémarrage du service chrony..."
systemctl restart chrony
sleep 3
chronyc -a makestep
sleep 2

sync_status=$(chronyc tracking | grep "Leap status" | awk '{print $3}')

if [[ "$sync_status" == "Normal" ]]; then
    echo "✅ Synchronisation NTP réussie 🎉"
else
    echo "❌ Échec de la synchronisation NTP, tentative via HTTPS..."
    http_date=$(curl -sI https://cloudflare.com | grep '^Date:' | cut -d' ' -f2-)
    if [ -z "$http_date" ]; then
        echo "⚠️ Impossible de récupérer l'heure via HTTPS."
        exit 1
    fi
    date_cmd=$(date -d "$http_date" "+%Y-%m-%d %H:%M:%S")
    echo "📅 Mise à jour manuelle de l'heure avec : $date_cmd"
    date -s "$date_cmd"
fi

echo "🔍 État final de la synchronisation :"
timedatectl status
EOF

# Rendre exécutable
sudo chmod +x "$SCRIPT_PATH"

# Ajouter à la crontab root au démarrage si absent
if ! sudo crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "🛠️ Ajout à la crontab pour exécution au démarrage..."
    (sudo crontab -l 2>/dev/null; echo "@reboot $SCRIPT_PATH >> $LOG_FILE 2>&1") | sudo crontab -
else
    echo "✅ Entrée crontab déjà présente."
fi

echo "✅ Installation terminée. Lancement du script de synchronisation..."
sudo "$SCRIPT_PATH"