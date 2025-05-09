#!/usr/bin/env bash
#
# teardown_autostart.bash — Désactive le service Artineo IR et le mode kiosk Chromium
# Usage (non-root):
#   chmod +x teardown_autostart.bash
#   ./teardown_autostart.bash
#

set -e

# Détecte l'utilisateur propriétaire
if [ -n "${SUDO_USER-}" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~$OWNER")

SERVICE_NAME="artineo-ir"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
AUTOSTART_FILE="$HOME_DIR/.config/lxsession/LXDE-pi/autostart"

echo "🛑 Arrêt et suppression du service ${SERVICE_NAME}.service..."
sudo systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
sudo systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true

echo "🗑️  Suppression du fichier de service : ${SERVICE_FILE}"
sudo rm -f "${SERVICE_FILE}"

echo "♻️  Rechargement de systemd..."
sudo systemctl daemon-reload

echo "🛑 Suppression du fichier autostart Chromium (kiosk)..."
if [ -f "${AUTOSTART_FILE}" ]; then
  rm -f "${AUTOSTART_FILE}"
  echo "→ ${AUTOSTART_FILE} supprimé."
else
  echo "→ Aucun fichier ${AUTOSTART_FILE} trouvé."
fi

echo "✅ Comportement auto-start annulé."
echo "🔄 Reboot recommandé pour appliquer les changements."