#!/usr/bin/env bash
set -euo pipefail

# ====================================================
# start.bash — lance la pipeline IR (1296×972 → crop×2 → 320×240)
# ====================================================

# Usage
usage() {
  echo "Usage: $0 [--debug|-d]"
  exit 1
}

# Parse options
DEBUG_FLAG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--debug)
      DEBUG_FLAG="--debug"
      shift
      ;;
    -*)
      echo "Unknown option: $1"
      usage
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      ;;
  esac
done

# Variables
WORKDIR="${HOME}/Desktop/artineo/modules/IR"
FIFO="/tmp/ir_video_fifo"
VID_PID=""

cleanup() {
  echo "Arrêt de la pipeline vidéo…"
  [[ -n "$VID_PID" ]] && kill "$VID_PID" 2>/dev/null || true
  rm -f "$FIFO"
  exit 0
}

# Trap Ctrl-C / SIGTERM
trap cleanup SIGINT SIGTERM
# Ignore SIGPIPE
trap '' PIPE

# 1️⃣ Prépare le FIFO
rm -f "$FIFO"
mkfifo "$FIFO"

# 2️⃣ Mise à jour & installation des dépendances
echo "🔄 Mise à jour APT…"
sudo apt update
sudo apt upgrade -y || echo "⚠️  apt upgrade a échoué, on continue…"

echo "📦 Installation des paquets requis…"
sudo apt install -y --no-install-recommends \
    python3 python3-opencv libcamera-apps ffmpeg \
    python3-requests python3-websockets python3-dotenv \
  || echo "⚠️  apt install a échoué, on continue…"

# 3️⃣ Récupère le code & test caméra
if [[ -d "$WORKDIR/.git" ]]; then
  echo "🔄 Git pull…"
  cd "$WORKDIR" && git pull || true
fi

echo "🎥 Test caméra (libcamera-hello)…"
libcamera-hello -t 2000 --nopreview || echo "⚠️  libcamera-hello a échoué"

# 4️⃣ Lance libcamera-vid → FIFO (full-res 1296×972)
echo "🚀 Démarrage de libcamera-vid (1296×972) → FIFO"
libcamera-vid \
  -t 0 --nopreview \
  --width 1296 --height 972 \
  --inline --codec yuv420 --output - \
  > "$FIFO" 2>/dev/null &
VID_PID=$!

# 5️⃣ Lance FFmpeg → crop centré (648×486) → scale 320×240 → main.py
echo "🔄 Démarrage de ffmpeg → main.py${DEBUG_FLAG:+ (mode debug)}"
ffmpeg -hide_banner -loglevel error \
  -f rawvideo -pix_fmt yuv420p -s 1296x972 -r 30 -i "$FIFO" \
  -vf "crop=648:486:324:243,scale=320:240" \
  -f rawvideo -pix_fmt bgr24 -r 15 - \
| python3 "$WORKDIR/main.py" $DEBUG_FLAG

# 6️⃣ Cleanup si main.py termine
cleanup