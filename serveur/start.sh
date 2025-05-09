#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# fonction pour trouver un port libre à partir d’une base
find_free_port(){
  local port=$1
  while lsof -iTCP -sTCP:LISTEN -Pn | grep -q ":${port} "; do
    port=$((port+1))
  done
  echo $port
}

# au signal SIGINT, SIGTERM ou à la sortie du script, on tue les child processes
cleanup(){
  echo
  echo "🛑 Arrêt des services…"
  kill "${backendPID}" "${frontendPID}" 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

### 1) Backend FastAPI
(
  cd "$BASE_DIR/back"
  source env/bin/activate
  exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
) &
backendPID=$!

### 2) Frontend Nuxt
FRONT_START_PORT=3000
PORT=$(find_free_port $FRONT_START_PORT)

(
  cd "$BASE_DIR/front"
  exec npm run dev -- --host 0.0.0.0 --port $PORT
) &
frontendPID=$!

### 3) Affichage des URLs
sleep 1
# récupération de l'IP (Linux ou Mac)
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo "localhost")

echo
echo "✅ Backend accessible sur : http://${IP}:8000"
echo "✅ Frontend accessible sur : http://${IP}:${PORT}"
echo

### 4) On attend la fin (CTRL+C déclenchera cleanup)
wait