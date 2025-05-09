#!/bin/bash

echo "🔧 Mise à jour des paquets..."
sudo apt update -y

echo "📦 Installation de ntpdate si besoin..."
sudo apt install -y ntpdate systemd-timesyncd

echo "🛠️ Configuration manuelle des serveurs NTP..."
sudo sed -i 's|^#NTP=.*|NTP=0.debian.pool.ntp.org 1.debian.pool.ntp.org|' /etc/systemd/timesyncd.conf
sudo sed -i 's|^#FallbackNTP=.*|FallbackNTP=ntp.ubuntu.com|' /etc/systemd/timesyncd.conf

echo "🔄 Redémarrage du service de synchronisation..."
sudo timedatectl set-ntp false
sudo systemctl restart systemd-timesyncd.service
sudo timedatectl set-ntp true

echo "🌐 Test de connectivité NTP..."
if ping -c 2 pool.ntp.org > /dev/null; then
  echo "✅ Connectivité OK, tentative de synchronisation avec ntpdate..."
  sudo ntpdate -u pool.ntp.org
else
  echo "❌ Impossible de joindre les serveurs NTP (pool.ntp.org). Vérifie ta connexion réseau ou ton DNS."
fi

echo "🕒 État actuel de l'heure système :"
timedatectl status

echo "🔁 Redémarrage complet du service timesyncd pour finaliser..."
sudo systemctl restart systemd-timesyncd.service

echo "✅ Script terminé. Vérifie que 'System clock synchronized' est sur 'yes'."