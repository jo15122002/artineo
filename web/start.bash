#!/usr/bin/env bash
set -e

# Désactive la mise en veille et l'écran de veille X11
xset s off           # Désactive l'écran de veille
xset -dpms           # Désactive DPMS (gestion de l'alimentation)
xset s noblank       # Empêche l'écran de se mettre en veille

# Vérification et installation de Node.js si nécessaire
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js non trouvé, installation via NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs build-essential
fi

# Définition du répertoire racine du projet (ce script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📦 Installation des dépendances..."
npm install

echo "🔨 Build de l'application Nuxt..."
npm run build

# Lancement du serveur Nuxt en mode preview (production)
HOST=0.0.0.0
PORT=3000

echo "🚀 Démarrage du serveur Nuxt --hostname $HOST --port $PORT"
npx nuxi preview --hostname $HOST --port $PORT &
NUXT_PID=$!

# Pause pour laisser le serveur se monter
sleep 5

echo "🌐 Lancement de Chromium en mode kiosque sur http://localhost:$PORT"
chromium-browser \
  --noerrdialogs \
  --disable-infobars \
  --incognito \
  --kiosk \
  http://localhost:$PORT

# À la fermeture de Chromium, on arrête Nuxt
echo "🛑 Arrêt du serveur Nuxt (PID=$NUXT_PID)"
kill "$NUXT_PID"

exit 0