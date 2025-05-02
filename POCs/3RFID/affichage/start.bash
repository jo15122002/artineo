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

# Installation des dépendances du projet si manquantes
if [ ! -d "node_modules" ]; then
  echo "Installation des dépendances du projet..."
  npm install
fi

# Build de l'application Nuxt en mode production
# On tente d'abord npm run build, sinon on utilise npx nuxi build (Nuxt 3) ou npx nuxt build (Nuxt 2)
echo "Compilation de l'application Nuxt..."
if npm run build --if-present; then
  echo "Build via npm OK."
else
  echo "Script 'build' manquant, exécution de npx nuxi build..."
  if command -v npx >/dev/null 2>&1; then
    npx nuxi build || npx nuxt build
  else
    echo "npx introuvable, installation temporaire de npx..."
    npm install -g npx
    npx nuxi build || npx nuxt build
  fi
fi

# Démarrage du serveur Nuxt en production
# On tente d'abord npm run start, sinon fallback sur npx nuxi preview (Nuxt 3) ou npx nuxt start (Nuxt 2)
echo "Démarrage du serveur Nuxt..."
if npm run start --if-present & then
  NUXT_PID=$!
else
  echo "Script 'start' manquant, exécution de npx nuxi preview..."
  if command -v npx >/dev/null 2>&1; then
    npx nuxi preview & NUXT_PID=$!
    # fallback
    wait 1 || (npx nuxt start & NUXT_PID=$!)
  else
    echo "npx introuvable, installation temporaire de npx..."
    npm install -g npx
    npx nuxi preview & NUXT_PID=$!
    wait 1 || (npx nuxt start & NUXT_PID=$!)
  fi
fi

# Laisser le temps au serveur de démarrer
sleep 5

# Lancement de Chromium en mode kiosque pointant vers l'application Nuxt
echo "Lancement de Chromium en mode kiosque..."
chromium-browser --noerrdialogs --disable-infobars --incognito --kiosk http://localhost:3000

# À la fermeture du navigateur, arrêt du serveur Nuxt
echo "Arrêt du serveur Nuxt..."
kill $NUXT_PID

exit 0