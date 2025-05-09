#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Fonction pour trouver le premier port libre à partir d'une base
find_free_port(){
  local port=$1
  while lsof -iTCP -sTCP:LISTEN -Pn | grep -q ":${port} "; do
    port=$((port+1))
  done
  echo $port
}

### 1) Backend FastAPI
(
  echo "🚀 Démarrage du backend (FastAPI) sur le port 8000…"
  cd "$BASE_DIR/back"
  source env/bin/activate
  exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
) &

### 2) Frontend Nuxt
FRONT_START_PORT=3000
PORT=$(find_free_port $FRONT_START_PORT)

(
  echo "🌐 Démarrage du frontend (Nuxt) sur le port ${PORT}…"
  cd "$BASE_DIR/front"
  # la commande nuxt (v3) utilise --host et --port
  exec npm run dev -- --host 0.0.0.0 --port $PORT
) &

### 3) Affichage des URLs d’accès réseau
# on attend un court instant pour que les serveurs démarrent et que l'IP soit connue
sleep 1
IP=$(hostname -I | awk '{print $1}')
echo
echo "✅ Backend accessible sur : http://${IP}:8000"
echo "✅ Frontend accessible sur : http://${IP}:${PORT}"
echo

wait
echo "🚀 Tous les serveurs sont en cours d'exécution."