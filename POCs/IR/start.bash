#!/bin/bash
# Correction éventuelle de dpkg
sudo dpkg --configure -a

# Mise à jour du système
sudo apt-get update && sudo apt-get upgrade -y

# Installation des paquets essentiels
sudo apt-get install -y python3 python3-pip python3-opencv gstreamer1.0-tools

# Installation des packages Python
pip3 install opencv-python numpy picamera --break-system-packages


# Test rapide de la caméra via libcamera-vid (5 secondes sans prévisualisation)
echo "Test de la caméra (libcamera-vid)..."
libcamera-vid -t 5000 --nopreview --inline -o /dev/null
if [ $? -ne 0 ]; then
    echo "Erreur lors du test de la caméra. Vérifiez votre installation de libcamera."
    exit 1
fi

# Vérification que le device /dev/video0 existe (pour v4l2src)
if [ -e /dev/video0 ]; then
    echo "Appareil /dev/video0 trouvé."
else
    echo "Appareil /dev/video0 non trouvé. Vérifiez que la caméra est correctement exposée."
    exit 1
fi

# Lancement de l'application principale
echo "Lancement de main.py..."
python3 main.py