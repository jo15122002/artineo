#!/usr/bin/env bash
set -euo pipefail

# teardown_autostart.bash
# Désactive :
#  • le service systemd artineo-ir
#  • l’autostart de Chromium en kiosk via ~/.config/autostart
# Usage (exécuter en non-root, avec sudo si nécessaire) :
#   chmod +x teardown_autostart.bash
#   ./teardown_autostart.bash

# 1️⃣ Détection de l’utilisateur « propriétaire »
if [ -n "${SUDO_USER-}" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~$OWNER")

# 2️⃣ Variables
SERVICE_NAME="artineo-ir"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WRAPPER_SCRIPT="$HOME_DIR/kiosk_chromium.sh"
AUTOSTART_FILE="$HOME_DIR/.config/autostart/kiosk_chromium.desktop"
LOGFILE="$HOME_DIR/chromium-kiosk.log"

echo "🛑 Arrêt et désactivation du service systemd ${SERVICE_NAME}…"
sudo systemctl stop  "${SERVICE_NAME}.service" 2>/dev/null || true
sudo systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true

echo "🗑️  Suppression du fichier de service : ${SERVICE_FILE}"
sudo rm -f "${SERVICE_FILE}"

echo "♻️  Rechargement de systemd…"
sudo systemctl daemon-reload

echo "🛑 Suppression du script wrapper : ${WRAPPER_SCRIPT}"
if [ -f "${WRAPPER_SCRIPT}" ]; then
  rm -f "${WRAPPER_SCRIPT}"
  echo "→ ${WRAPPER_SCRIPT} supprimé."
else
  echo "→ ${WRAPPER_SCRIPT} non trouvé."
fi

echo "🛑 Suppression du .desktop d’autostart : ${AUTOSTART_FILE}"
if [ -f "${AUTOSTART_FILE}" ]; then
  rm -f "${AUTOSTART_FILE}"
  echo "→ ${AUTOSTART_FILE} supprimé."
else
  echo "→ ${AUTOSTART_FILE} non trouvé."
fi

echo "ℹ️  Le fichier de log Chromium (${LOGFILE}) n’a pas été supprimé, vous pouvez le conserver ou le supprimer manuellement."

echo "✅ Teardown terminé. Redémarrez ou reconnectez-vous pour prendre effet."