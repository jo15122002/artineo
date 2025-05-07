#!/bin/bash

# Pull dernier code
echo "Récupération des dernières modifications..."
git pull

# Mise à jour du système
echo "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation des paquets essentiels
echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps ffmpeg \
    python3-requests python3-websockets python3-dotenv

# Test de la caméra (2 secondes sans preview)
echo "Test de la caméra avec libcamera-hello..."
libcamera-hello -t 2000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-hello a échoué. Vérifiez votre installation."
    exit 1
fi

# Lancement du pipeline : capture 640×480 → ffmpeg scale 320×240@15FPS → main.py
echo "Lancement du pipeline (320×240 @15FPS)..."
libcamera-vid -t 0 --nopreview --width 640 --height 480 --inline --codec yuv420 --output - | \
ffmpeg -loglevel error \
       -f rawvideo -pix_fmt yuv420p -s 640x480 -r 30 -i - \
       -f rawvideo -vf "scale=320:240" -pix_fmt bgr24 -r 15 - | \
python3 main.py

echo "Script terminé."