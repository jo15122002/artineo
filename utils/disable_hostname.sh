#!/usr/bin/env bash
set -e

# Vérifie qu'on est root
if [[ $EUID -ne 0 ]]; then
  echo "❗️ Merci de lancer ce script avec sudo : sudo $0" >&2
  exit 1
fi

DAEMON_LABEL="com.artineo.sethostname"
PLIST_PATH="/Library/LaunchDaemons/${DAEMON_LABEL}.plist"

echo "🗑️  Suppression du LaunchDaemon ${DAEMON_LABEL}…"

# Décharge le daemon s'il est chargé
launchctl unload -w "${PLIST_PATH}" 2>/dev/null || true

# Supprime le fichier plist
rm -f "${PLIST_PATH}"

echo "✅ LaunchDaemon ${DAEMON_LABEL} supprimé."
