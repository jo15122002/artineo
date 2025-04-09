#!/bin/bash
# Mise à jour du système
echo "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation des paquets essentiels
echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps ffmpeg

# Test de la caméra avec libcamera-hello (5 secondes)
echo "Test de la caméra avec libcamera-hello..."
libcamera-hello -t 5000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-hello a échoué. Vérifiez votre installation."
    exit 1
fi

# Lancement de libcamera-vid et conversion du flux
echo "Lancement de libcamera-vid et envoi du flux à cam_debug.py..."
libcamera-vid -t 0 --width 640 --height 480 --inline --codec yuv420 --output - | \
ffmpeg -loglevel error -f rawvideo -pix_fmt yuv420p -s 640x480 -i - -f rawvideo -pix_fmt bgr24 - | \
python3 cam_debug.py

echo "Script terminé."
