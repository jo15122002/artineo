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
echo "Compilation de l'application Nuxt..."
npm run build

# Démarrage du serveur Nuxt en production (écoute par défaut sur le port 3000)
echo "Démarrage du serveur Nuxt..."
npm run start &
NUXT_PID=$!

# Laisser le temps au serveur de démarrer
sleep 5

# Lancement de Chromium en mode kiosque pointant vers l'application Nuxt
echo "Lancement de Chromium en mode kiosque..."
chromium-browser --noerrdialogs --disable-infobars --incognito --kiosk http://localhost:3000

# À la fermeture du navigateur, arrêt du serveur Nuxt
echo "Arrêt du serveur Nuxt..."
kill $NUXT_PID

exit 0
