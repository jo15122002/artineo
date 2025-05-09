#!/usr/bin/env bash
set -euo pipefail

# ——————————————————————————————————————————————————————————————
# setup_autostart.bash
# Configure l’autostart du module IR (backend + frontend) sur RPi4
# Usage (en non-root user):
#   chmod +x setup_autostart.bash
#   ./setup_autostart.bash
# ——————————————————————————————————————————————————————————————

# 1️⃣ Détecte le propriétaire (pour HOME et User du service)
if [ -n "${SUDO_USER-}" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~$OWNER")

# 2️⃣ Chemins
WORKDIR="$HOME_DIR/Desktop/artineo/POCs/IR"
START_SCRIPT="$WORKDIR/start.bash"
SERVICE_NAME="artineo-ir"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
AUTOSTART_DIR="$HOME_DIR/.config/lxsession/LXDE-pi"
AUTOSTART_FILE="$AUTOSTART_DIR/autostart"

# 3️⃣ Vérifie l’existence et le bit exécutable du start.bash
if [ ! -f "$START_SCRIPT" ]; then
  echo "❌ Erreur : $START_SCRIPT introuvable."
  exit 1
fi
if [ ! -x "$START_SCRIPT" ]; then
  echo "⚙️  Rendre $START_SCRIPT exécutable..."
  chmod +x "$START_SCRIPT"
fi

# 4️⃣ Installer les dépendances système si nécessaire
echo "📦 Mise à jour et installation des paquets requis..."
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-opencv libcamera-apps ffmpeg chromium-browser \
  python3-requests python3-websockets python3-dotenv

# 5️⃣ Création du service systemd pour le pipeline Python
echo "🔧 Création du service systemd : $SERVICE_NAME"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Artineo IR Module Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$OWNER
WorkingDirectory=$WORKDIR
ExecStart=$START_SCRIPT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "♻️  Reload systemd et activation du service..."
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl start  "${SERVICE_NAME}.service"

# 6️⃣ Configuration du kiosk autostart pour Chromium (session LXDE)
echo "🖥️  Configuration du mode kiosk pour Chromium"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_FILE" <<EOF
@xset s off
@xset -dpms
@xset s noblank
@chromium-browser --noerrdialogs --disable-infobars --kiosk http://artineo.local:3000/modules/module1
EOF

# Assure les bons droits sur .config
chown -R "$OWNER":"$OWNER" "$HOME_DIR/.config"

echo "✅ Installation terminée !"
echo "  • Service Python en marche : sudo systemctl status ${SERVICE_NAME}.service"
echo "  • Chromium démarrera en kiosk sur module1 au prochain login graphique."
