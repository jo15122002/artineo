#!/bin/bash
set -e
set -m   # active le contrôle de job
# À la sortie du script ou sur interruption, on tue tout le groupe de processus
trap 'echo "Arrêt de la pipeline vidéo..."; kill 0' EXIT INT TERM

# Mettre à jour et installer (idem avant)
echo "Récupération du code et mise à jour du système..."
git pull
sudo apt update && sudo apt upgrade -y

echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps ffmpeg \
    python3-requests python3-websockets python3-dotenv

echo "Test de la caméra (2 s)..."
libcamera-hello -t 2000 --nopreview

echo "Démarrage du pipeline (640×480 → 320×240 @15FPS) etc."
libcamera-vid -t 0 --nopreview --width 640 --height 480 --inline --codec yuv420 --output - | \
ffmpeg -loglevel error \
       -f rawvideo -pix_fmt yuv420p -s 640x480 -r 30 -i - \
       -f rawvideo -vf "scale=320:240" -pix_fmt bgr24 -r 15 - | \
python3 main.py

echo "Script terminé."