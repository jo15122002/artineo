#!/bin/bash
# --- 1. Mise à jour du système ---
echo "Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# --- 2. Installation des paquets nécessaires ---
echo "Installation des paquets essentiels..."
sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    v4l2loopback-dkms

# --- 3. Test de la caméra avec libcamera-hello ---
echo "Test de la caméra avec libcamera-hello (5 secondes)..."
libcamera-hello -t 5000 --nopreview
if [ $? -ne 0 ]; then
    echo "Erreur : la caméra ne fonctionne pas avec libcamera-hello."
    exit 1
fi

# --- 4. Affichage des périphériques vidéo disponibles ---
echo "Liste des périphériques vidéo :"
v4l2-ctl --list-devices

# --- 5. Configuration du périphérique virtuel (v4l2loopback) ---
echo "Configuration de v4l2loopback pour créer /dev/video2..."
sudo modprobe -r v4l2loopback
# Charger v4l2loopback avec un nombre de buffers augmenté (ici 16)
sudo modprobe v4l2loopback video_nr=2 card_label="CameraLoop" exclusive_caps=1 max_buffers=16

# Vérifier que le périphérique virtuel a été créé
if [ ! -e /dev/video2 ]; then
    echo "Erreur : /dev/video2 n'a pas été créé."
    exit 1
fi

# --- 6. Lancement de libcamera-vid ---
# On force la résolution 1296x972 (résolution native constatée par libcamera-hello)
# Le mode par défaut de libcamera-vid est H264 et devrait être décodable
echo "Lancement de libcamera-vid en mode H264 avec résolution 1296x972..."
libcamera-vid -t 0 --nopreview --inline --width 1296 --height 972 --output /dev/video2 &
# Attendre quelques secondes pour que le flux soit établi
sleep 5

# --- 7. Test du flux via GStreamer ---
# On va lire le flux H264 depuis /dev/video2, le parser et le décoder
echo "Test du flux via /dev/video2 avec GStreamer..."
gst-launch-1.0 v4l2src device=/dev/video2 ! h264parse ! avdec_h264 ! videoconvert ! autovideosink

# Fin du script
echo "Script terminé."
