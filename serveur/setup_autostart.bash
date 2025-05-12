#!/usr/bin/env bash
set -e

# Vérifie qu’on exécute en root
if [[ $EUID -ne 0 ]]; then
  echo "❌ Ce script doit être lancé en root (sudo)."
  exit 1
fi

PROJECT_DIR="/usr/local/artineo/serveur"
BACK_DIR="$PROJECT_DIR/back"
FRONT_DIR="$PROJECT_DIR/front"
START_SCRIPT="$PROJECT_DIR/start.sh"
LOG_DIR="/var/log/artineo"
PLIST_PATH="/Library/LaunchDaemons/com.artineo.servers.plist"

echo "🔧 Configuration auto-start dans $PROJECT_DIR…"

# 1) Assure-toi que start.sh est exécutable
if [ ! -x "$START_SCRIPT" ]; then
  chmod +x "$START_SCRIPT"
  echo "✔ Rendu $START_SCRIPT exécutable."
fi

# 2) Crée l’environnement Python dans back/env et installe FastAPI/Uvicorn
PYTHON_BIN="/usr/bin/python3"
VENV_DIR="$BACK_DIR/env"
if [ ! -d "$VENV_DIR" ]; then
  echo "🐍 Création du venv dans $VENV_DIR"
  $PYTHON_BIN -m venv "$VENV_DIR"
fi
echo "⚡ Activation du venv et installation des dépendances Python…"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install fastapi "uvicorn[standard]"
deactivate

# 3) Installe les dépendances npm dans front/
NPM_BIN="$(which npm || echo /usr/local/bin/npm)"
if [ -x "$NPM_BIN" ]; then
  echo "📦 Installation des dépendances NPM dans $FRONT_DIR"
  ( cd "$FRONT_DIR" && "$NPM_BIN" install )
else
  echo "⚠️ npm non trouvé. Installez Node.js/npm pour le frontend."
fi

# 4) Crée le dossier de logs
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# 5) Génère le LaunchDaemon plist
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

# 6) Permissions du plist
chown root:wheel "$PLIST_PATH"
chmod 644 "$PLIST_PATH"
echo "✔ Plist généré : $PLIST_PATH"

# 7) (Re)charge le daemon
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"
echo "✔ LaunchDaemon chargé et activé."

echo
echo "✅ Installation terminée. Redémarrez votre Mac pour que le back et le front démarrent automatiquement avant le login."