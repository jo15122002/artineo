#!/usr/bin/env bash
set -e

# Désactive la mise en veille et l'écran de veille
xset s off
xset -dpms
xset s noblank

# Répertoire du projet Nuxt (script placé dans le répertoire racine du projet)
FRONTEND_DIR="$(dirname "$0")"
cd "$FRONTEND_DIR"

# Installation des dépendances si nécessaire
if [ ! -d "node_modules" ]; then
  echo "Installation des dépendances..."
  npm install
fi

# Build de l'application Nuxt en mode production
echo "Compilation de l'application Nuxt..."
npm run build

# Démarre Nuxt en production (écoute sur le port 3000)
echo "Démarrage du serveur Nuxt..."
npm run start &
NUXT_PID=$!

# Donne le temps au serveur de démarrer
sleep 5

# Lance Chromium en mode kiosque pointant sur l'application Nuxt
echo "Lancement de Chromium en mode kiosque..."
chromium-browser --noerrdialogs --disable-infobars --incognito --kiosk http://localhost:3000

# À la fermeture du navigateur, arrête le serveur Nuxt
echo "Arrêt du serveur Nuxt..."
kill $NUXT_PID

exit 0