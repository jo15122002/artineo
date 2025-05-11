#!/usr/bin/env bash
#
# setup_autostart.bash — Configure un service systemd pour lancer Chromium au démarrage
# Usage : sudo ./setup_autostart.bash
#

set -e

SERVICE_NAME="artineo-module3"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# Détecte l'utilisateur propriétaire (pour trouver correctement son HOME)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~${OWNER}")

# Crée (ou remplace) le service systemd
tee "${SERVICE_PATH}" > /dev/null <<EOF
[Unit]
Description=Artineo Module 3 Auto-Start
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${OWNER}
Environment=DISPLAY=:0
WorkingDirectory=${HOME_DIR}
ExecStart=/usr/bin/chromium-browser \\
    --noerrdialogs \\
    --disable-infobars \\
    --incognito \\
    --kiosk http://artineo.local/modules/module3
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Recharge systemd et active le service
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl start  "${SERVICE_NAME}.service"

echo "Service ${SERVICE_NAME}.service créé, activé et démarré."
echo "Vérifiez son statut avec : systemctl status ${SERVICE_NAME}.service"