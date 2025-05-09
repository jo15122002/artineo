#!/usr/bin/env bash
#
# teardown_kiosk_autostart.bash — Désactive le démarrage en mode Kiosk
# sur Raspberry Pi en supprimant la configuration autostart de Chromium.
#
# Usage (non-root):
#   chmod +x teardown_kiosk_autostart.bash
#   ./teardown_kiosk_autostart.bash
#

set -e

# Détecte l'utilisateur propriétaire (celui ayant lancé sudo ou $USER)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
  OWNER="$SUDO_USER"
else
  OWNER="$USER"
fi
HOME_DIR=$(eval echo "~${OWNER}")

# Chemin du fichier autostart LXDE-pi
AUTOSTART_FILE="${HOME_DIR}/.config/lxsession/LXDE-pi/autostart"

if [ -f "${AUTOSTART_FILE}" ]; then
  echo "Suppression du fichier autostart : ${AUTOSTART_FILE}"
  rm -f "${AUTOSTART_FILE}"
  echo "Configuration kiosk désactivée."
else
  echo "Aucun fichier autostart trouvé à l'emplacement :"
  echo "  ${AUTOSTART_FILE}"
  echo "Rien à faire."
fi

# (Optionnel) restauration des valeurs par défaut d'économie d'écran
echo "Restauration des paramètres d'écran par défaut..."
sudo -u "${OWNER}" bash -c "xset s on; xset +dpms; xset s blank"

echo "✅ Démarrage automatique en mode kiosk désactivé pour ${OWNER}."
echo "→ Au prochain démarrage, Chromium ne s'ouvrira plus automatiquement."