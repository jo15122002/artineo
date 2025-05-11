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

# 1) Rendre start.sh exécutable si besoin
if [ ! -x "$START_SCRIPT" ]; then
  chmod +x "$START_SCRIPT"
  echo "✅ Rendu $START_SCRIPT exécutable."
fi

# 2) Créer le dossier de logs
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# 3) Génération du LaunchDaemon plist
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

# 4) Appliquer les permissions
chown root:wheel "$PLIST_PATH"
chmod 644 "$PLIST_PATH"

# 5) (Re)charger le daemon
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"
echo "✅ LaunchDaemon chargé : $PLIST_PATH"

# 6) Ouvrir le panneau Sécurité pour que vous naviguiez vers Full Disk Access
# echo "🔐 Ouverture du panneau Sécurité dans les Préférences Système…"
# open "/System/Library/PreferencePanes/Security.prefPane"

cat <<EOF

👉 Dans la barre latérale de "Privacy & Security", sélectionnez "Full Disk Access",  
puis ajoutez le processus "launchd" (généralement situé dans /usr/libexec/launchd).

🚨 Note : sur macOS Ventura+, le panneau System Settings n'accepte pas les URL AppleScript.  
Vous devrez naviguer manuellement dans la liste.

🛑 Redémarrez ensuite votre Mac pour que le daemon démarre avant toute connexion.

EOF
