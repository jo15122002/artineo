#!/usr/bin/env bash
set -e

if [[ $EUID -ne 0 ]]; then
  echo "⚠️  Ce script doit être exécuté en root (sudo)."
  exit 1
fi

# 1) Variables
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_PATH="/Library/LaunchDaemons/com.artineo.servers.plist"
LOG_DIR="/var/log/artineo"
START_SCRIPT="$BASE_DIR/start.sh"

# 2) Vérifications
if [ ! -x "$START_SCRIPT" ]; then
  echo "❌ start.sh introuvable ou non exécutable dans $BASE_DIR."
  exit 1
fi

# 3) Crée le dossier de logs
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# 4) Génère le plist
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

# 5) Fixe les permissions du plist
chown root:wheel "$PLIST_PATH"
chmod 644 "$PLIST_PATH"

# 6) (Re)charge le daemon
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"

echo "✅ LaunchDaemon installé et chargé."
echo "   • Plist : $PLIST_PATH"
echo "   • Logs  : $LOG_DIR/servers.{out,err}.log"
echo "   • Le script start.sh sera exécuté au démarrage du Mac, avant déverrouillage de session."
