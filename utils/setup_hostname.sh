#!/usr/bin/env bash
set -e

# Vérifie qu'on est root
if [[ $EUID -ne 0 ]]; then
  echo "❗️ Merci de lancer ce script avec sudo : sudo $0" >&2
  exit 1
fi

# Nom d’hôte voulu
HOST="artineo"

# Chemins
SCRIPT_PATH="/usr/local/artineo/utils/set-hostname.sh"
DAEMON_LABEL="com.artineo.sethostname"
PLIST_PATH="/Library/LaunchDaemons/${DAEMON_LABEL}.plist"

echo "⚙️  Configuration du nom de l’hôte en '${HOST}'…"

# Applique immédiatement le renommage
scutil --set ComputerName  "${HOST}"
scutil --set HostName      "${HOST}"
scutil --set LocalHostName "${HOST}"
killall -HUP mDNSResponder 2>/dev/null || true

echo "✅ Hostname appliqué."

# Crée le LaunchDaemon pour appliquer à chaque démarrage
echo "🔧 Installation du LaunchDaemon…"
cat <<EOF > "${PLIST_PATH}"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
    <string>${DAEMON_LABEL}</string>
  <key>ProgramArguments</key>
    <array>
      <string>${SCRIPT_PATH}</string>
    </array>
  <key>RunAtLoad</key>
    <true/>
  <key>StandardOutPath</key>
    <string>/var/log/${DAEMON_LABEL}.out</string>
  <key>StandardErrorPath</key>
    <string>/var/log/${DAEMON_LABEL}.err</string>
</dict>
</plist>
EOF

chown root:wheel "${PLIST_PATH}"
chmod 644    "${PLIST_PATH}"

# Charge (ou recharge) le daemon
if launchctl list | grep -q "${DAEMON_LABEL}"; then
  launchctl unload -w "${PLIST_PATH}" 2>/dev/null || true
fi
launchctl load -w "${PLIST_PATH}"

echo "✅ LaunchDaemon installé et chargé. Le hostname sera appliqué à chaque démarrage."
