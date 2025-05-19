#!/usr/bin/env bash
set -e

# 1) Setup du nom d'hôte
echo "🔧 Configuration du LocalHostName en 'artineo'..."
sudo scutil --set LocalHostName "artineo"

# 2) Vérification du service mDNSResponder
echo "🔍 Vérification de mDNSResponder..."
sudo launchctl list | grep mDNSResponder || echo "mDNSResponder non trouvé (OK s'il tourne par défaut)."

# 3) Activation de SSH si nécessaire
echo "🔐 Vérification et activation de Remote Login (SSH)..."
# systemsetup -getremotelogin renvoie "Remote Login: On" ou "Remote Login: Off"
if ! sudo systemsetup -getremotelogin | grep -q "On"; then
  echo "→ SSH est désactivé. Activation en cours..."
  sudo systemsetup -setremotelogin on
  echo "✅ SSH activé."
else
  echo "✅ SSH déjà activé."
fi

# 4) Création et activation de l'environnement virtuel
echo "🐍 Création de l'environnement virtuel 'env'..."
python3 -m venv env

echo "⚡ Activation de l'environnement virtuel..."
# macOS/Linux
source env/bin/activate

# 5) Installation des dépendances
echo "📦 Mise à jour de pip et installation des packages..."
python -m pip install --upgrade pip
python -m pip install "uvicorn[standard]" fastapi

# 6) Lancement du serveur
echo "🚀 Démarrage du serveur FastAPI avec Uvicorn..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
