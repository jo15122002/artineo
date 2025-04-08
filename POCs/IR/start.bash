#!/bin/bash
# --- Mise à jour du système et installation des paquets ---
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

# --- Test de la caméra avec libcamera-hello ---
echo "Test de la caméra avec libcamera-hello (5 secondes sans prévisualisation)..."
libcamera-hello -t 5000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : libcamera-hello a échoué."
    exit 1
fi

# --- Liste des périphériques vidéo ---
echo "Liste des périphériques vidéo :"
v4l2-ctl --list-devices

# --- Rechargement du module v4l2loopback ---
echo "Rechargement du module v4l2loopback pour créer /dev/video2..."
sudo modprobe -r v4l2loopback
# On omet l'option exclusive_caps pour faciliter l'accès en lecture et écriture
sudo modprobe v4l2loopback video_nr=2 card_label="CameraLoop" max_buffers=16

if [ ! -e /dev/video2 ]; then
    echo "Erreur : /dev/video2 n'a pas été créé."
    exit 1
fi

# --- Lancement de libcamera-vid en mode H264 ---
# Ici, nous utilisons 640x480 car c'est le mode de capture privilégié (score élevé) et nous omettons --inline.
echo "Lancement de libcamera-vid en mode H264 (640x480) vers /dev/video2..."
libcamera-vid -t 0 --nopreview --codec h264 --width 640 --height 480 --output /dev/video2 &
# Attendre quelques secondes pour que le flux se stabilise
sleep 5

# --- Test du flux via GStreamer ---
echo "Test du flux depuis /dev/video2 avec GStreamer (décodage H264)..."
gst-launch-1.0 v4l2src device=/dev/video2 ! h264parse ! avdec_h264 ! videoconvert ! videoscale ! "video/x-raw,width=320,height=240" ! autovideosink

echo "Script terminé."
