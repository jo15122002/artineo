#!/usr/bin/env bash
set -e

# ----------------------------------------------------------------
# start.bash — Démarrage de l'application Nuxt avec PM2 en kiosque
# Placez ce script à la racine de votre projet
# ----------------------------------------------------------------

# 1️⃣ Désactive la mise en veille et l'économiseur d’écran X11
xset s off        # Désactive l'écran de veille
xset -dpms        # Désactive DPMS (gestion d'alimentation)
xset s noblank    # Empêche l'écran de se mettre en veille

# 2️⃣ Vérifie/installe Node.js et npm
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js ou npm non trouvé, installation via NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs npm build-essential
fi

# 3️⃣ Vérifie/installe PM2
if ! command -v pm2 >/dev/null 2>&1; then
  echo "PM2 non trouvé, installation globale via npm..."
  sudo npm install -g pm2
fi

# 4️⃣ Se place dans le dossier du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 5️⃣ Installe les dépendances et build Nuxt
echo "📦 Installation des dépendances..."
npm install

echo "🔨 Build de l'application Nuxt..."
npm run build

# 6️⃣ Démarre Nuxt en arrière-plan via PM2
APP_NAME="nuxt-artineo"
echo "🚀 Démarrage de Nuxt avec PM2 (nom: $APP_NAME)..."
pm2 start --name "$APP_NAME" -- npx nuxi preview --hostname 0.0.0.0 --port 3000

# 7️⃣ Laisse le temps au serveur de démarrer
sleep 5

# 8️⃣ Lance Chromium en mode kiosque sur l'application
echo "🌐 Lancement de Chromium en mode kiosque..."
chromium-browser \
  --noerrdialogs \
  --disable-infobars \
  --incognito \
  --kiosk http://localhost:3000

# 9️⃣ À la fermeture de Chromium, on arrête Nuxt via PM2
echo "🛑 Chromium fermé, arrêt de Nuxt ($APP_NAME) via PM2..."
pm2 stop "$APP_NAME"
pm2 delete "$APP_NAME"

exit 0