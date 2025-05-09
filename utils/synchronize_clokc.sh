#!/bin/bash

echo "📦 Installation de chrony (alternative à timesyncd)..."
sudo apt update -y
sudo apt install -y chrony

echo "🛠️ Configuration personnalisée de chrony..."
sudo tee /etc/chrony/chrony.conf > /dev/null <<EOF
pool pool.ntp.org iburst
driftfile /var/lib/chrony/chrony.drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
EOF

echo "🔄 Redémarrage du service chrony..."
sudo systemctl restart chrony
sudo systemctl enable chrony

echo "⏱️ Forçage de la mise à l'heure immédiate..."
sudo chronyc -a makestep

echo "✅ État de la synchronisation :"
chronyc tracking

echo "✅ Vérification finale :"
timedatectl status