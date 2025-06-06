#!/usr/bin/env bash
# serveur/back/start.bash

set -e

# Usage
usage() {
  echo "Usage: $0 [--debug]"
  exit 1
}

### ─── PARSING DES OPTIONS ───────────────────────────────────────────────────
DEBUG_FLAG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --debug)
      DEBUG_FLAG="--debug"
      shift
      ;;
    -*)
      echo "Unknown option: $1"
      usage
      ;;
    *)
      # Pas d’autres arguments attendus
      usage
      ;;
  esac
done
### ────────────────────────────────────────────────────────────────────────────

# Si --debug, on exporte la variable BACK_DEBUG
if [ -n "$DEBUG_FLAG" ]; then
  echo "🔧 Mode DEBUG activé"
  export BACK_DEBUG=true
else
  export BACK_DEBUG=false
fi

# 1) Crée l'envvirtual si nécessaire
[ ! -d env ] && python3 -m venv env

# 2) Active-le
source env/bin/activate

# 3) Installe (ou met à jour) les dépendances
pip install --upgrade pip
pip install "uvicorn[standard]" fastapi

# 4) Démarre le serveur
# Si BACK_DEBUG=true, on passe le log-level debug à Uvicorn
if [ "$BACK_DEBUG" = "true" ]; then
  exec uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
else
  exec uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
fi
