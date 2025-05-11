#!/usr/bin/env bash
set -e

# Vérifie qu'on est root
if [[ $EUID -ne 0 ]]; then
  echo "❌ Ce script doit être lancé en root (sudo)."
  exit 1
fi

# Répertoires et fichiers
PROJECT_DIR="/usr/local/artineo"
START_SCRIPT="$PROJECT_DIR/start.sh"
LOG_DIR="/var/log/artineo"
PLIST_PATH="/Library/LaunchDaemons/com.artineo.servers.plist"

echo "🔧 Configuration de l’auto-démarrage pour le projet cloné dans $PROJECT_DIR…"

# 1) Assure-toi que start.sh est exécutable
if [ ! -x "$START_SCRIPT" ]; then
  chmod +x "$START_SCRIPT"
  echo "✔ Rendu $START_SCRIPT exécutable"
fi

# 2) Crée le dossier de logs
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"
echo "✔ Dossier de logs prêt dans $LOG_DIR"

# 3) Génère le LaunchDaemon plist
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?> 
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" \
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

    <key>WorkingDirectory</key>
      <string>${PROJECT_DIR}</string>

    <key>RunAtLoad</key>
      <true/>

    <key>KeepAlive</key>
      <true/>

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
echo "✔ LaunchDaemon plist généré : $PLIST_PATH"

# 5) (Re)charge le LaunchDaemon
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"
echo "✔ LaunchDaemon chargé et activé"

echo
echo "✅ Auto-démarrage configuré. Le script start.sh sera lancé au boot avant déverrouillage de session."
echo "   Logs dans : $LOG_DIR/servers.{out,err}.log"