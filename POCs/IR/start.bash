#!/bin/bash
# Corriger l'état de dpkg
echo "Configuration de dpkg..."
sudo dpkg --configure -a

# Suppression des anciens paquets libcamera et nettoyage
echo "Suppression des anciennes installations de libcamera..."
sudo apt-get purge -y libcamera0 libcamera-apps libcamera-ipa
sudo apt-get autoremove -y

# Débloquer les paquets éventuellement mis en hold
echo "Déblocage des paquets libcamera..."
sudo apt-mark unhold libcamera0 libcamera-apps libcamera-ipa

# Mise à jour du système
echo "Mise à jour du système..."
sudo apt-get update && sudo apt-get upgrade -y

# Installation des paquets système requis
echo "Installation des paquets système..."
sudo apt-get install -y python3 python3-pip python3-opencv gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good

# Installation de libcamera et ses dépendances via aptitude
echo "Installation de libcamera via aptitude..."
sudo aptitude install -y libcamera0 libcamera-apps libcamera-ipa

# Installation des packages Python
echo "Installation des packages Python..."
pip3 install --upgrade pip
pip3 install opencv-python numpy --break-system-packages

# Test de la caméra avec libcamera-vid
echo "Test de la caméra via libcamera-vid (5 secondes sans prévisualisation)..."
libcamera-vid -t 5000 --nopreview --inline -o /dev/null
if [ $? -ne 0 ]; then
    echo "Erreur : La caméra ne fonctionne pas. Vérifiez votre installation de libcamera."
    exit 1
fi
echo "La caméra fonctionne correctement."

# Lancement du script principal
echo "Lancement du script principal..."
python3 main.py
