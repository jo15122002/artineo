#!/usr/bin/env bash
set -e

# Désactive la mise en veille et l'écran de veille
xset s off
xset -dpms
xset s noblank

# Répertoire du projet Nuxt (script placé dans le répertoire racine du projet)
FRONTEND_DIR="$(dirname "$0")"
cd "$FRONTEND_DIR"

# Vérification et installation de Node.js & npm sur le Raspberry si nécessaire
if ! command -v npm >/dev/null 2>&1; then
  echo "npm non trouvé, installation de Node.js et npm via apt..."
  sudo apt-get update
  sudo apt-get install -y nodejs npm
fi

# Installation des dépendances du projet (package.json doit contenir nuxt)
echo "Installation des dépendances..."
npm install

# Build de l'application Nuxt
# Utilisation de npx nuxi pour Nuxt 3 ou npx nuxt pour Nuxt 2
echo "Compilation de l'application Nuxt..."
if command -v npx >/dev/null 2>&1; then
  npx nuxi build || npx nuxt build
else
  echo "npx introuvable, installation..."
  npm install -g npx
  npx nuxi build || npx nuxt build
fi

# Lancement du serveur Nuxt en mode preview (production)
echo "Démarrage du serveur Nuxt en preview..."
if command -v npx >/dev/null 2>&1; then
  npx nuxi preview --hostname 0.0.0.0 --port 3000 &
  NUXT_PID=$!
else
  npm install -g npx
  npx nuxi preview --hostname 0.0.0.0 --port 3000 &
  NUXT_PID=$!
fi

# Laisser le temps au serveur de démarrer
sleep 5

# Lancement de Chromium en mode kiosque pointant vers l'application Nuxt
echo "Lancement de Chromium en mode kiosque..."
chromium-browser \
  --noerrdialogs \
  --disable-infobars \
  --incognito \
  --kiosk \
  http://localhost:3000

# À la fermeture du navigateur, arrêt du serveur Nuxt
echo "Arrêt du serveur Nuxt..."
kill $NUXT_PID

exit 0