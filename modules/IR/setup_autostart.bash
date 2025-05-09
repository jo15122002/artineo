#!/usr/bin/env bash
#
# setup_autostart.sh — Configure un service systemd pour lancer start.bash au démarrage
#
# Usage : sudo ./setup_autostart.sh
#

set -e

SERVICE_NAME="artineo-ir"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# Détecte l'utilisateur propriétaire (pour trouver correctement son HOME)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~${OWNER}")

WORKDIR="${HOME_DIR}/Desktop/artineo/modules/IR"
SCRIPT="${WORKDIR}/start.bash"

# Vérifie que start.bash existe
if [ ! -f "${SCRIPT}" ]; then
  echo "Erreur : ${SCRIPT} introuvable."
  exit 1
fi

# S'il n'est pas exécutable, on le rend exécutable
if [ ! -x "${SCRIPT}" ]; then
  echo "Le script ${SCRIPT} n'est pas exécutable. Ajout du bit exécutable..."
  chmod +x "${SCRIPT}"
fi

# Crée (ou remplace) le service systemd
sudo tee "${SERVICE_PATH}" > /dev/null <<EOF
[Unit]
Description=Artineo Module 1 Auto-Start
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

# Recharge systemd et active le service
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl start  "${SERVICE_NAME}.service"

echo "Service ${SERVICE_NAME}.service créé, activé et démarré."
echo "Pour vérifier : sudo systemctl status ${SERVICE_NAME}.service"