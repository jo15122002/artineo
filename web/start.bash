#!/usr/bin/env bash
set -e

# ----------------------------------------------------------------
# start_mac.bash — Démarrage et gestion de l'application Nuxt sur Mac
# Placez ce script à la racine de votre projet Nuxt
# Usage: ./start_mac.bash
# ----------------------------------------------------------------

# 1️⃣ Vérifie la présence de Homebrew
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew non trouvé. Veuillez installer Homebrew depuis https://brew.sh"
  exit 1
fi

# 2️⃣ Vérifie/installe Node.js et npm via Homebrew
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js/npm non trouvés. Installation via Homebrew..."
  brew update
  brew install node
fi

# 3️⃣ Vérifie/installe PM2
if ! command -v pm2 >/dev/null 2>&1; then
  echo "PM2 non trouvé, installation globale via npm..."
  npm install -g pm2
fi

# 4️⃣ Se place dans le dossier du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📦 Installation des dépendances..."
npm install

echo "🔨 Build de l'application Nuxt..."
npm run build

# 5️⃣ Démarre l'application en production avec PM2
APP_NAME="nuxt-artineo"
echo "🚀 Démarrage de Nuxt (production) via PM2 (nom: $APP_NAME)..."
pm2 start npm --name "$APP_NAME" -- start

# 6️⃣ Enregistre la configuration PM2 pour redémarrage automatique au boot
echo "🔄 Sauvegarde de la configuration PM2 et activation au démarrage du système..."
pm2 save
pm2 startup launchd -u $(whoami) --hp $HOME

echo "✅ L'application Nuxt est lancée et gérée par PM2."  
echo "   Pour voir les logs: pm2 logs $APP_NAME"  
echo "   Pour arrêter: pm2 stop $APP_NAME"  
echo "   Pour redémarrer: pm2 restart $APP_NAME"

exit 0