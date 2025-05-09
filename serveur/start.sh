#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

### 1) Lancer le back
echo "🚀 Démarrage du backend…"
(
  cd "$BASE_DIR/back"

  # 1.a) venv Python (créé à la première exécution)
  [ ! -d env ] && python3 -m venv env

  # 1.b) activation
  source env/bin/activate

  # 1.c) installation rapide si besoin
  pip install --upgrade pip
  pip install "uvicorn[standard]" fastapi

  # 1.d) lancement
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
) &

### 2) Lancer le front
echo "🌐 Démarrage du frontend (Nuxt)…"
(
  cd "$BASE_DIR/front"

  # 2.a) node_modules (installé une fois)
  [ ! -d node_modules ] && npm install

  # 2.b) lancement en mode dev, host 0.0.0.0 pour être accessible sur le réseau
  npm run dev -- --hostname 0.0.0.0 --port 3000
) &

### 3) Attendre les deux
wait
echo "✅ Backend et frontend démarrés avec succès !"
echo "🔗 Accédez à l'application via http://localhost:3000 ou http://artineo.local:3000"