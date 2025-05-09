#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

### 1) (Optionnel) libère le port 8000 si un ancien uvicorn y tourne
if lsof -ti:8000 >/dev/null; then
  echo "⚠ Port 8000 occupé, arrêt de l’ancienne instance UVicorn…"
  lsof -ti:8000 | xargs kill -9
fi

### 2) Démarre le backend FastAPI
(
  echo "🚀 Backend…"
  cd "$BASE_DIR/back"
  source env/bin/activate
  exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
) &

### 3) Démarre le frontend Nuxt
(
  echo "🌐 Frontend…"
  cd "$BASE_DIR/front"
  exec npm run dev -- --host 0.0.0.0 --port 3000
) &

### 4) Attend que tout tourne
wait
echo "✅ Serveurs démarrés !"
echo "   - Frontend: http://artineo.local:3000"
echo "   - Backend: http://artineo.local:8000"