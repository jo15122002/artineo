#!/bin/bash

# Se positionner dans le répertoire du script
cd "$(dirname "$0")"

# Vérifier si l'environnement virtuel existe, sinon le créer
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
    echo "Activation de l'environnement virtuel..."
    source venv/bin/activate
    echo "Installation des dépendances..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

echo "Lancement du programme RFID..."
python3 main.py
