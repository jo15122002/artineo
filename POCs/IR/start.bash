#!/bin/bash
# Désinstallation des dépendances précédemment installées (pip et apt-get) en une seule ligne
echo "Suppression des dépendances existantes..."
pip3 uninstall -y opencv-python numpy && sudo apt-get remove --purge -y python3-pip python3-opencv gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly && sudo apt-get autoremove -y

# Mise à jour du système et installation des dépendances nécessaires
echo "Mise à jour du système..."
sudo apt-get update

echo "Installation des paquets requis..."
sudo apt-get install -y python3 python3-pip python3-opencv gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly

echo "Installation des packages Python..."
pip3 install opencv-python numpy --break-system-packages

# Test de la caméra avec libcamera-vid
echo "Test de la caméra via libcamera-vid (5 secondes de capture sans prévisualisation)..."
libcamera-vid -t 5000 --nopreview --inline -o /dev/null
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-vid n'a pas pu démarrer. Vérifiez votre configuration de caméra."
    exit 1
fi
echo "La caméra fonctionne correctement."

# Lancer le script principal
echo "Lancement du script principal..."
python3 main.py
