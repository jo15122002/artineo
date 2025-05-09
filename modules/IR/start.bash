#!/usr/bin/env bash
set -e

# --- Fonction de nettoyage ---
cleanup() {
  echo "Arrêt de la pipeline vidéo..."
  # Tuer les processus enfants lancés par ce script
  pkill -P $$ libcamera-vid  2>/dev/null || true
  pkill -P $$ ffmpeg         2>/dev/null || true
  pkill -P $$ python3        2>/dev/null || true
  exit 0
}

# On piège INT (Ctrl-C) et TERM (shutdown), mais PAS EXIT pour éviter la récursion
trap cleanup SIGINT SIGTERM

# Mise à jour et installations (si besoin)
echo "Récupération du code et mise à jour du système..."
git pull
sudo apt update && sudo apt upgrade -y

echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps ffmpeg \
    python3-requests python3-websockets python3-dotenv

# Test rapide de la caméra
echo "Test de la caméra (2s)..."
libcamera-hello -t 2000 --nopreview

# Lancement de la pipeline :
# libcamera-vid → ffmpeg (scale 320×240 @15FPS) → main.py
echo "Démarrage du pipeline vidéo..."
libcamera-vid -t 0 --nopreview --width 640 --height 480 --inline --codec yuv420 --output - | \
ffmpeg -loglevel error \
       -f rawvideo -pix_fmt yuv420p -s 640x480 -r 30 -i - \
       -f rawvideo -vf "scale=320:240" -pix_fmt bgr24 -r 15 - | \
python3 main.py

echo "Pipeline terminée normalement."