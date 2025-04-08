#!/bin/bash
#
# Ce script met à jour le système, installe les paquets nécessaires,
# teste la caméra avec libcamera-hello, configure un périphérique virtuel (/dev/video2)
# via v4l2loopback et lance libcamera-vid en mode H264 à 640x480.
# Ensuite, il teste le flux via GStreamer.
#
# Lancez ce script avec sudo (ex.: sudo ./start.bash).

# --- 1. Mise à jour du système et installation des paquets ---
echo "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    v4l2loopback-dkms

# --- 2. Test de la caméra avec libcamera-hello ---
echo "Test de la caméra avec libcamera-hello (5 secondes sans prévisualisation)..."
libcamera-hello -t 5000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-hello a échoué. Vérifiez votre installation de libcamera."
    exit 1
fi

# --- 3. Affichage des périphériques vidéo ---
echo "Liste des périphériques vidéo actuels :"
v4l2-ctl --list-devices

# --- 4. Configuration du périphérique virtuel via v4l2loopback ---
echo "Configuration de v4l2loopback pour créer /dev/video2..."
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback video_nr=2 card_label="CameraLoop" exclusive_caps=1 max_buffers=16

if [ ! -e /dev/video2 ]; then
    echo "Erreur : /dev/video2 n'a pas été créé."
    exit 1
fi

# --- 5. Lancement de libcamera-vid en mode H264 ---
# Nous utilisons ici 640x480 car ce mode semble être privilégié (score le plus élevé) 
# et présente moins de contraintes mémoire que 1296x972.
echo "Lancement de libcamera-vid en mode H264 (640x480) vers /dev/video2..."
# Remarque : on retire l'option --inline pour éviter certains problèmes d'écriture.
libcamera-vid -t 0 --nopreview --codec h264 --width 640 --height 480 --output /dev/video2 &
# Attendre quelques secondes pour permettre au flux de démarrer
sleep 5

# --- 6. Test du flux depuis le périphérique virtuel ---
echo "Test du flux depuis /dev/video2 avec GStreamer..."
gst-launch-1.0 v4l2src device=/dev/video2 ! h264parse ! avdec_h264 ! videoconvert ! autovideosink

echo "Script terminé."
