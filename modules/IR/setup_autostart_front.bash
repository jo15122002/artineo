#!/usr/bin/env bash
#
# setup_autostart.bash — Configure le lancement automatique en mode Kiosk
# sur Raspberry Pi pour ouvrir Chromium en plein écran sur
# http://artineo.local:3000/modules/module1 au démarrage.
#
# Usage (non-root) : 
#   chmod +x setup_autostart.bash
#   ./setup_autostart.bash
#

set -e

# Détecte l'utilisateur qui a lancé sudo (ou tomme USER sinon)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~${OWNER}")

# 1️⃣ Installe Chromium si nécessaire
echo "Installation de Chromium-browser..."
sudo apt-get update
sudo apt-get install -y chromium-browser

# 2️⃣ Crée le dossier autostart pour LXDE-pi
AUTOSTART_DIR="${HOME_DIR}/.config/lxsession/LXDE-pi"
mkdir -p "${AUTOSTART_DIR}"

# 3️⃣ Écrit le fichier autostart
AUTOSTART_FILE="${AUTOSTART_DIR}/autostart"
cat > "${AUTOSTART_FILE}" <<EOF
@xset s off
@xset -dpms
@xset s noblank
@chromium-browser --noerrdialogs --disable-infobars --kiosk http://artineo.local:3000/modules/module1
EOF

chown -R "${OWNER}":"${OWNER}" "${HOME_DIR}/.config"
chmod 644 "${AUTOSTART_FILE}"

echo "✅ Autostart configuré pour l’utilisateur ${OWNER}."
echo "→ Au prochain démarrage, Chromium s’ouvrira en plein écran sur artineo.local/module1."
