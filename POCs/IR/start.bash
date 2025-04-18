#!/bin/bash
# Mise à jour du système
echo "Mise à jour du système..."
git pull
sudo apt update && sudo apt upgrade -y

# Installation des paquets essentiels
echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps ffmpeg

# Installation des dépendances Python supplémentaires
echo "Installation des bibliothèques Python requests, websockets et python-dotenv..."
pip3 install --upgrade pip
pip3 install --user requests websockets python-dotenv

# Test de la caméra avec libcamera-hello (5 secondes sans preview)
echo "Test de la caméra avec libcamera-hello..."
libcamera-hello -t 5000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-hello a échoué. Vérifiez votre installation."
    exit 1
fi

# Lancement de libcamera-vid et conversion du flux pour main.py
echo "Lancement de libcamera-vid et envoi du flux à main.py..."
libcamera-vid -t 0 --nopreview --width 640 --height 480 --inline --codec yuv420 --output - | \
ffmpeg -loglevel error -f rawvideo -pix_fmt yuv420p -s 640x480 -i - -f rawvideo -pix_fmt bgr24 - | \
python3 main.py

echo "Script terminé."
# End of script