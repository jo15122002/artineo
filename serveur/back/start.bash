#!/usr/bin/env bash
set -e

# 1) Crée l'envvirtual si nécessaire
[ ! -d env ] && python3 -m venv env

# 2) Active-le
source env/bin/activate

# 3) Installe (ou met à jour) les dépendances
pip install --upgrade pip
pip install "uvicorn[standard]" fastapi

# 4) Démarre le serveur
exec uvicorn main:app --reload --host 0.0.0.0 --port 8000