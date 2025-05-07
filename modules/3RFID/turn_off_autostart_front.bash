#!/usr/bin/env bash
#
# disable_autostart_module3.sh — Désactive et supprime l’autostart du module 3
# Usage : sudo ./disable_autostart_module3.sh
#

set -e

SERVICE_NAME="artineo-module3"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

echo
echo "→ Désactivation du service : ${SERVICE_NAME}"
echo

# 1) Stoppe le service (s’il tourne)
if systemctl is-active --quiet "${SERVICE_NAME}"; then
  echo "Arrêt du service ${SERVICE_NAME}…"
  systemctl stop "${SERVICE_NAME}"
else
  echo "Le service ${SERVICE_NAME} n’est pas en cours d’exécution."
fi

# 2) Désactive le démarrage automatique
if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
  echo "Désactivation du démarrage automatique…"
  systemctl disable "${SERVICE_NAME}"
else
  echo "Le service ${SERVICE_NAME} n’est pas activé au démarrage."
fi

# 3) Supprime le fichier de service
if [ -f "${SERVICE_PATH}" ]; then
  echo "Suppression du fichier de service : ${SERVICE_PATH}"
  rm "${SERVICE_PATH}"
  # Recharge systemd pour prendre en compte la suppression
  echo "Reload de systemd…"
  systemctl daemon-reload
else
  echo "Aucun fichier de service trouvé à : ${SERVICE_PATH}"
fi

echo
echo "✅ Le service ${SERVICE_NAME} a été désactivé et supprimé."
echo