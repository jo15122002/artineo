#!/bin/bash

# Se positionner dans le répertoire du script
cd "$(dirname "$0")"

# Vérifier et activer l'interface SPI dans /boot/config.txt
echo "Vérification de l'activation de SPI dans /boot/config.txt..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "SPI non activé, modification de /boot/config.txt..."
    # Décommente la ligne si elle est présente en commentaire
    sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/config.txt
    # Si la ligne n'est toujours pas présente, on l'ajoute à la fin du fichier
    if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
        echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    fi
    echo "SPI a été activé dans /boot/config.txt."
    echo "Pour appliquer ces changements, un redémarrage est nécessaire."
    read -p "Voulez-vous redémarrer maintenant ? [O/n] " response
    if [[ "$response" =~ ^[Oo] ]]; then
       sudo reboot
       exit 0
    else
       echo "N'oubliez pas de redémarrer votre Raspberry Pi plus tard."
    fi
else
    echo "SPI est déjà activé."
fi

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
python3 rfid_reader.py
