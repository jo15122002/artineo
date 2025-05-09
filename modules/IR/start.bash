#!/usr/bin/env bash
set -euo pipefail

# Variables
WORKDIR="${HOME}/Desktop/artineo/POCs/IR"
SCRIPT="${WORKDIR}/start.bash"  # (votre propre script)
FIFO="/tmp/ir_video_fifo"

cleanup() {
  echo "Arrêt de la pipeline vidéo…"
  kill "${VID_PID}" 2>/dev/null || true
  rm -f "${FIFO}"
  exit 0
}
trap cleanup SIGINT SIGTERM

# 1. Préparation du FIFO
rm -f "${FIFO}"
mkfifo "${FIFO}"

# 2. Mise à jour système & installation (optionnel, ou passer cette partie si déjà fait)
echo "Récupération du code et mise à jour…"
cd "${WORKDIR}"
git pull
sudo apt update && sudo apt upgrade -y
sudo apt-get install -y python3 python3-opencv libcamera-apps ffmpeg

echo "Test caméra…"
libcamera-hello -t 2000 --nopreview

# 3. Lancement de libcamera-vid vers le FIFO
echo "Démarrage de libcamera-vid → FIFO"
libcamera-vid -t 0 --nopreview --width 640 --height 480 --inline --codec yuv420 --output - > "${FIFO}" &
VID_PID=$!

# 4. Lancement de ffmpeg + python, lecture depuis le FIFO
echo "Démarrage de ffmpeg → python"
ffmpeg -loglevel error \
       -f rawvideo -pix_fmt yuv420p -s 640x480 -r 30 -i "${FIFO}" \
       -f rawvideo -vf "scale=320:240" -pix_fmt bgr24 -r 15 - | \
python3 main.py

# 5. Quand python se termine (q ou fin), on passe ici et on clean
cleanup
