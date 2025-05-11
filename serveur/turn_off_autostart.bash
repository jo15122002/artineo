#!/usr/bin/env bash
set -e

if [[ $EUID -ne 0 ]]; then
  echo "⚠️  Ce script doit être exécuté en root (sudo)."
  exit 1
fi

PLIST_PATH="/Library/LaunchDaemons/com.artineo.servers.plist"
LOG_DIR="/var/log/artineo"

echo "🛠️  Désinstallation du LaunchDaemon com.artineo.servers…"

# 1) Décharger le daemon s'il est chargé
if launchctl list | grep -q "com.artineo.servers"; then
  echo "→ Déchargement du daemon…"
  launchctl unload -w "$PLIST_PATH" 2>/dev/null || true
else
  echo "→ Daemon non chargé."
fi

# 2) Supprimer le plist
if [ -f "$PLIST_PATH" ]; then
  echo "→ Suppression de $PLIST_PATH"
  rm -f "$PLIST_PATH"
else
  echo "→ Aucun plist trouvé à $PLIST_PATH"
fi

# 3) Supprimer les logs
if [ -d "$LOG_DIR" ]; then
  echo "→ Suppression du dossier de logs $LOG_DIR"
  rm -rf "$LOG_DIR"
else
  echo "→ Aucun dossier de logs trouvé à $LOG_DIR"
fi

echo "✅ Le comportement d’auto-démarrage a été désactivé et tous les fichiers associés ont été supprimés."
