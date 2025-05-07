#!/usr/bin/env bash
#
# teardown_autostart.sh — Désactive et supprime le service systemd Artineo IR
#
# Usage : sudo ./teardown_autostart.sh
#

SERVICE_NAME="artineo-ir"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Arrêt du service ${SERVICE_NAME}.service…"
sudo systemctl stop "${SERVICE_NAME}.service" || true

echo "Désactivation du démarrage automatique…"
sudo systemctl disable "${SERVICE_NAME}.service" || true

if [ -f "${SERVICE_FILE}" ]; then
  echo "Suppression du fichier de service ${SERVICE_FILE}…"
  sudo rm "${SERVICE_FILE}"
else
  echo "Attention : ${SERVICE_FILE} introuvable."
fi

echo "Rechargement des unités systemd…"
sudo systemctl daemon-reload

echo "Vérification de l’état du service (devrait être absent ou inactif) :"
sudo systemctl status "${SERVICE_NAME}.service" || true

echo "Opération terminée."