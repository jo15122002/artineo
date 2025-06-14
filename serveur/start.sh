#!/usr/bin/env bash
# serveur/start.sh

set -e

### ─── GESTION DU FLAG --debug ───────────────────────────────────────────────
DEBUG_FLAG=false
# Parcourt les arguments pour détecter "--debug"
for arg in "$@"; do
  if [ "$arg" = "--debug" ]; then
    DEBUG_FLAG=true
  fi
done
# Retire tous les "--debug" de la liste des arguments passés au frontend si besoin
# (ici, on ne passe pas d’args au frontend, donc on ne les transmet pas).
### ─────────────────────────────────────────────────────────────────────────────

# 1) Ajout des répertoires usuels à PATH pour npm/Homebrew
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Si le flag --debug est présent, on exporte BACK_DEBUG pour le backend
if [ "$DEBUG_FLAG" = true ]; then
  echo "🔧 Mode DEBUG activé pour le backend"
  export BACK_DEBUG=true
fi

# fonction pour trouver un port libre à partir d’une base
find_free_port(){
  local port=$1
  while lsof -iTCP -sTCP:LISTEN -Pn | grep -q ":${port} "; do
    port=$((port+1))
  done
  echo $port
}

# Au signal SIGINT, SIGTERM ou à la sortie du script, on tue les child processes
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
  # Assurez-vous que uvicorn est installé dans l'environnement virtuel
  if ! command -v uvicorn &> /dev/null; then
    echo "Uvicorn n'est pas installé dans l'environnement virtuel. Installation en cours..."
    pip install uvicorn
  fi

  # Si BACK_DEBUG est actif, lance uvicorn en mode debug (log-level=debug). Sinon, mode info.
  if [ "$DEBUG_FLAG" = true ]; then
    exec uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
  else
    exec uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
  fi
) &
backendPID=$!

### 2) Frontend Nuxt
FRONT_START_PORT=3000
PORT=$(find_free_port $FRONT_START_PORT)

(
  cd "$BASE_DIR/front"
  npm install
  # npm devrait maintenant être trouvé
  NUXT_TELEMETRY_DISABLED=1 exec npm run dev -- --host 0.0.0.0 --port $PORT
) &
frontendPID=$!

### 3) Affichage des URLs
sleep 1
IP=$(hostname -I 2>/dev/null | awk '{print $1}' \
     || ipconfig getifaddr en0 2>/dev/null \
     || echo "localhost")

echo
echo "✅ Backend accessible sur : http://${IP}:8000 (log-level=$( [ "$DEBUG_FLAG" = true ] && echo "debug" || echo "info" ))"
echo "✅ Frontend accessible sur : http://${IP}:${PORT}"
echo

### 4) On attend la fin (CTRL+C déclenchera cleanup)
wait
echo "✅ Tous les services sont arrêtés."
