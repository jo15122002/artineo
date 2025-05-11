#!/usr/bin/env bash
#
# turn_off_autostart.sh — Désactive et supprime le service systemd Artineo Module 3
# Usage : sudo ./turn_off_autostart.sh
#

set -e

SERVICE_NAME="artineo-module4"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "🛑 Arrêt et désactivation du service ${SERVICE_NAME}.service..."

# Stoppe le service s'il tourne
if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
  systemctl stop "${SERVICE_NAME}.service"
  echo "Service arrêté."
else
  echo "Service non en cours d'exécution."
fi

# Désactive le démarrage automatique
if systemctl is-enabled --quiet "${SERVICE_NAME}.service"; then
  systemctl disable "${SERVICE_NAME}.service"
  echo "Démarrage automatique désactivé."
else
  echo "Le service n'était pas activé au démarrage."
fi

# Supprime le fichier de service
if [ -f "${SERVICE_FILE}" ]; then
  rm -f "${SERVICE_FILE}"
  echo "Fichier de service supprimé (${SERVICE_FILE})."
else
  echo "Aucun fichier de service trouvé à ${SERVICE_FILE}."
fi

# Recharge la configuration systemd
systemctl daemon-reload
echo "Configuration systemd rechargée."

echo "✅ Le service ${SERVICE_NAME}.service a été entièrement désactivé et supprimé."