#!/bin/bash

echo "🔧 Mise à jour des paquets..."
sudo apt update -y

echo "📦 Installation des services NTP si nécessaires..."
sudo apt install -y systemd-timesyncd ntp

echo "🕓 Activation de la synchronisation automatique de l'heure..."
sudo timedatectl set-ntp true

echo "🔄 Redémarrage du service de synchronisation..."
sudo systemctl restart systemd-timesyncd.service

echo "🧪 Forçage de la synchronisation initiale..."
sudo ntpd -gq || echo "⚠️ Échec avec ntpd, essaie avec ntpdate"
sudo apt install -y ntpdate
sudo ntpdate pool.ntp.org

echo "✅ État actuel de l'heure système :"
timedatectl status

echo "✅ Synchronisation terminée. Vérifie que 'System clock synchronized' est sur 'yes'."
