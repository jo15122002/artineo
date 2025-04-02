#!/bin/bash

# Se placer dans le répertoire du script
cd "$(dirname "$0")"

# Vérifier si l'environnement virtuel existe, sinon le créer
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activation de l'environnement virtuel
echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Mise à jour de pip et installation des dépendances
echo "Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Lancement du script de test
echo "Démarrage de test_multiple_readers.py..."
sudo python3 test.py