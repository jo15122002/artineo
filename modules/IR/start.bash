#!/usr/bin/env bash
set -euo pipefail

# ====================================================
# start.bash — pipeline IR (1296×972 → crop×2 → 320×240)
# ====================================================

usage() {
  echo "Usage: $0 [--debug|-d]"
  exit 1
}

DEBUG_FLAG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--debug) DEBUG_FLAG="--debug"; shift ;;
    -*) echo "Unknown option: $1"; usage ;;
    *)  echo "Unknown argument: $1"; usage ;;
  esac
done

WORKDIR="${HOME}/Desktop/artineo/modules/IR"
FIFO="/tmp/ir_video_fifo"
VID_PID=""

cleanup() {
  echo "Arrêt de la pipeline vidéo…"
  [[ -n "$VID_PID" ]] && kill "$VID_PID" 2>/dev/null || true
  rm -f "$FIFO"
  exit 0
}
trap cleanup SIGINT SIGTERM
trap '' PIPE

# 1️⃣ FIFO
rm -f "$FIFO"
mkfifo "$FIFO"

# 2️⃣ Déps
echo "🔄 Mise à jour APT…"
sudo apt update
sudo apt upgrade -y || echo "⚠️  apt upgrade échoué"
echo "📦 Installation des paquets…"
sudo apt install -y --no-install-recommends \
  python3 python3-opencv libcamera-apps ffmpeg \
  python3-requests python3-websockets python3-dotenv \
  || echo "⚠️  apt install échoué"

# 3️⃣ Code & test caméra
if [[ -d "$WORKDIR/.git" ]]; then
  echo "🔄 Git pull…"
  cd "$WORKDIR" && git pull || true
fi
echo "🎥 Test caméra…"
libcamera-hello -t 2000 --nopreview || echo "⚠️  libcamera-hello échoué"

# 4️⃣ libcamera-vid → FIFO
echo "🚀 libcamera-vid (1296×972) → FIFO"
libcamera-vid \
  -t 0 --nopreview \
  --width 1296 --height 972 \
  --inline --codec yuv420 --output - \
  > "$FIFO" 2>/dev/null &
VID_PID=$!

# 5️⃣ FFmpeg → crop+scale → main.py
echo "🔄 ffmpeg → main.py${DEBUG_FLAG:+ (mode debug)}"
ffmpeg -hide_banner -loglevel error \
  -f rawvideo -pix_fmt yuv420p -s 1296x972 -r 30 -i "$FIFO" \
  -vf "crop=648:486:324:243,scale=320:240" \
  -f rawvideo -pix_fmt bgr24 -r 15 - \
| python3 "$WORKDIR/main.py" $DEBUG_FLAG

# 6️⃣ Cleanup
cleanup
