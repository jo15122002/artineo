#!/bin/bash
# Correction de dpkg en cas de besoin
sudo dpkg --configure -a

# Mise à jour du système
sudo apt-get update && sudo apt-get upgrade -y

# Installation des paquets essentiels
sudo apt-get install -y python3 python3-pip python3-opencv gstreamer1.0-tools

# Installation des packages Python (ici dans l'espace utilisateur)
pip3 install opencv-python numpy --break-system-packages

# Lancement de l'application principale
echo "Lancement de main.py..."
python3 main.py