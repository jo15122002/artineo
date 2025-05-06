#!/usr/bin/env bash
#
# setup_autostart_module3.sh — Configure un service systemd pour lancer
# start.bash du module 3 au boot et ouvrir Chromium sur artineo.local/modules/module3
#
# Usage : sudo ./setup_autostart_module3.sh
#

set -e

SERVICE_NAME="artineo-module3"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# 1) Détermine l'utilisateur à qui lancer le service
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~${OWNER}")

# 2) Emplacement du POC 3RFID/affichage et du script de démarrage
WORKDIR="${HOME_DIR}/Desktop/artineo/POCs/3RFID/affichage"
SCRIPT="${WORKDIR}/start.bash"

# Vérifie que le dossier existe
if [ ! -d "${WORKDIR}" ]; then
  echo "Erreur : répertoire ${WORKDIR} introuvable. Vérifiez le chemin !"
  exit 1
fi

# 3) Crée start.bash s’il n’existe pas (ou l’écrase si besoin)
cat > "${SCRIPT}" <<'EOF'
#!/usr/bin/env bash
set -e
# Désactive économiseur d’écran / DPMS
xset s off
xset -dpms
xset s noblank
# Lance Chromium en mode kiosque sur le module 3
chromium-browser --noerrdialogs --disable-infobars --incognito --kiosk http://artineo.local/modules/module3
EOF

chmod +x "${SCRIPT}"
echo "→ start.bash créé/modifié dans ${WORKDIR}"

# 4) Crée (ou remplace) le service systemd
sudo tee "${SERVICE_PATH}" > /dev/null <<EOF
[Unit]
Description=Artineo Module 3 Auto-Start
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${OWNER}
WorkingDirectory=${WORKDIR}
ExecStart=${SCRIPT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 5) Active et démarre le service
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl start  "${SERVICE_NAME}.service"

echo "Service ${SERVICE_NAME}.service créé, activé et démarré."
echo "Vérifiez son statut avec : sudo systemctl status ${SERVICE_NAME}.service"
