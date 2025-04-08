#!/bin/bash
# Mise à jour du système
echo "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation des paquets essentiels
echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps \
    python3-picamera2 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

# Test de la caméra avec libcamera-hello pour s'assurer qu'elle est fonctionnelle
echo "Test de la caméra avec libcamera-hello (5 secondes sans prévisualisation)..."
libcamera-hello -t 5000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-hello a échoué. Vérifiez l'installation de la caméra."
    exit 1
fi

# Affichage des périphériques vidéo disponibles (optionnel)
echo "Liste des périphériques vidéo actuels :"
v4l2-ctl --list-devices

# Lancement de l'application Python utilisant Picamera2
echo "Lancement de main.py (utilisant Picamera2)..."
python3 main.py

echo "Script terminé."
