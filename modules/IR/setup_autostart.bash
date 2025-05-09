#!/usr/bin/env bash
set -euo pipefail

# ================================================================
# setup_autostart.bash
# Configure automatiquement :
#  • le service systemd pour lancer start.bash (pipeline IR)
#  • le kiosk mode Chromium sur module1 au démarrage graphique
# Usage (exécuter en non-root avec sudo) :
#   chmod +x setup_autostart.bash
#   ./setup_autostart.bash
# ================================================================

# 1️⃣ Détection de l’utilisateur « propriétaire »
if [ -n "${SUDO_USER-}" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~$OWNER")

# 2️⃣ Chemins et noms
WORKDIR="$HOME_DIR/Desktop/artineo/modules/IR"
START_SCRIPT="$WORKDIR/start.bash"
SERVICE_NAME="artineo-ir"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
AUTOSTART_GLOBAL="/etc/xdg/lxsession/LXDE-pi/autostart"

# 3️⃣ Vérification de start.bash
if [ ! -f "$START_SCRIPT" ]; then
  echo "❌ Erreur : $START_SCRIPT introuvable."
  exit 1
fi
if [ ! -x "$START_SCRIPT" ]; then
  echo "⚙️  Rendre $START_SCRIPT exécutable..."
  chmod +x "$START_SCRIPT"
fi

# 4️⃣ Installation des paquets système requis
echo "📦 Mise à jour et installation des paquets requis…"
sudo apt update
sudo apt install -y \
  python3 python3-opencv libcamera-apps ffmpeg \
  chromium-browser raspi-config \
  python3-requests python3-websockets python3-dotenv

# 5️⃣ Activer l’autologin sur LXDE-pi
echo "🔧 Activation de l’autologin sur le bureau LXDE-pi…"
sudo raspi-config nonint do_boot_behaviour B4

# 6️⃣ Création du service systemd pour la pipeline IR
echo "🔧 Création du service systemd : ${SERVICE_NAME}"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Artineo IR Module Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${OWNER}
WorkingDirectory=${WORKDIR}
ExecStart=${START_SCRIPT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "♻️  Reload systemd et activation du service..."
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl start  "${SERVICE_NAME}.service"

# 7️⃣ Configuration du mode kiosk Chromium (global pour LXDE-pi)
echo "🖥️  Configuration du mode kiosk pour Chromium…"
sudo mkdir -p "$(dirname "$AUTOSTART_GLOBAL")"
sudo tee "$AUTOSTART_GLOBAL" > /dev/null <<EOF
@xset s off
@xset -dpms
@xset s noblank
@/usr/bin/chromium-browser --noerrdialogs --disable-infobars --kiosk http://artineo.local:3000/modules/module1
EOF

sudo chown root:root "$AUTOSTART_GLOBAL"
sudo chmod 644        "$AUTOSTART_GLOBAL"

# 8️⃣ Ajuste les droits sur le dossier .config de l’utilisateur
sudo chown -R "${OWNER}":"${OWNER}" "$HOME_DIR/.config"

echo "✅ Installation terminée !"
echo "  • Service IR démarré : sudo systemctl status ${SERVICE_NAME}.service"
echo "  • Chromium démarrera en kiosk sur module1 au prochain login graphique."
