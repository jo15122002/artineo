#!/usr/bin/env bash
#
# setup_autostart.sh — Configure un service systemd pour lancer start.bash au démarrage
#
# Usage : sudo ./setup_autostart.sh
#

# Variables
SERVICE_NAME="artineo-ir"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
WORKDIR="${HOME}/Desktop/artineo/POCs/IR"
SCRIPT="${WORKDIR}/start.bash"

# Vérifie que le script start.bash existe
if [ ! -x "${SCRIPT}" ]; then
  echo "Erreur : ${SCRIPT} introuvable ou non exécutable."
  exit 1
fi

# Crée le fichier de service systemd
cat <<EOF | sudo tee "${SERVICE_PATH}" > /dev/null
[Unit]
Description=Artineo Module 1 Auto-Start
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${WORKDIR}
ExecStart=${SCRIPT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Recharge systemd et active le service
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl start "${SERVICE_NAME}.service"

echo "Service ${SERVICE_NAME}.service créé et démarré."
echo "Pour vérifier : sudo systemctl status ${SERVICE_NAME}.service"