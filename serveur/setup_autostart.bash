#!/usr/bin/env bash
set -e

if [[ $EUID -ne 0 ]]; then
  echo "⚠️  Ce script doit être exécuté en root (sudo)."
  exit 1
fi

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_SCRIPT="$BASE_DIR/start.sh"
PLIST_PATH="/Library/LaunchDaemons/com.artineo.servers.plist"
LOG_DIR="/var/log/artineo"

echo "🔧 Mise en place de l’auto-démarrage via LaunchDaemon…"

# 1) Rendre start.sh exécutable si nécessaire
if [ ! -x "$START_SCRIPT" ]; then
  chmod +x "$START_SCRIPT"
  echo "✅ Rendu $START_SCRIPT exécutable."
fi

# 2) Crée le dossier de logs
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# 3) Génération du plist
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?> 
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" 
   "http://www.apple.com/DTDs/PropertyList-1.0.dtd"> 
<plist version="1.0"> 
  <dict>
    <key>Label</key>
      <string>com.artineo.servers</string>
    <key>ProgramArguments</key>
      <array>
        <string>/bin/bash</string>
        <string>${START_SCRIPT}</string>
      </array>
    <key>RunAtLoad</key>
      <true/>
    <key>KeepAlive</key>
      <true/>
    <key>WorkingDirectory</key>
      <string>${BASE_DIR}</string>
    <key>StandardOutPath</key>
      <string>${LOG_DIR}/servers.out.log</string>
    <key>StandardErrorPath</key>
      <string>${LOG_DIR}/servers.err.log</string>
  </dict> 
</plist>
EOF

# 4) Permissions du plist
chown root:wheel "$PLIST_PATH"
chmod 644 "$PLIST_PATH"

# 5) (Re)charge le daemon
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"
echo "✅ LaunchDaemon chargé : $PLIST_PATH"

# 6) Ouvre la fenêtre "Accès complet au disque" pour autoriser launchd
echo "🔐 Ouverture des Préférences Système pour accorder l'accès complet au disque à launchd..."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"

echo "✅ Configuration terminée. Redémarrez le Mac pour tester le lancement avant déverrouillage."