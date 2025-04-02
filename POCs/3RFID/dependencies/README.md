# Custom RC522 Library for Raspberry Pi

Cette bibliothèque personnalisée offre une interface simplifiée pour utiliser le module RFID RC522 sur un Raspberry Pi. Elle gère la communication SPI et le contrôle des GPIO afin de faciliter la lecture des tags RFID.

## Caractéristiques

- **Initialisation et Configuration** : Réinitialisation du module via la broche RST et configuration des registres essentiels du RC522.
- **Accès aux Registres** : Fonctions de lecture et écriture sur les registres du RC522 selon la datasheet.
- **Détection et Anti-collision** : Méthodes simplifiées pour détecter la présence d'un tag (commande REQA) et récupérer son UID via une procédure anti-collision rudimentaire.
- **Nettoyage** : Libération propre des ressources SPI et GPIO.

## Prérequis

- Raspberry Pi fonctionnant sous Raspbian avec l'interface SPI activée (via `sudo raspi-config`).
- Python 3.11 (ou version ultérieure).
- Les packages Python listés dans le fichier `requirements.txt` (RPi.GPIO et spidev).

## Installation

1. **Activer l'interface SPI**  
   Ouvrez un terminal et lancez :
   ```bash
   sudo raspi-config
   ```
   Ensuite, dans le menu **Interfacing Options**, activez l'option **SPI**. Redémarrez votre Raspberry Pi si nécessaire.

2. **Installation des dépendances**  
   Dans le répertoire du projet, exécutez :
   ```bash
   pip install -r requirements.txt
   ```

3. **Organisation des fichiers**  
   La bibliothèque personnalisée se trouve dans le dossier `dependencies/` sous le nom `custom_rc522.py`.  
   Un exemple d'utilisation est fourni dans le fichier `main.py`.

## Câblage sur Raspberry Pi 4B

Pour connecter le module RC522 à un Raspberry Pi 4B, utilisez l'interface SPI. Voici la correspondance recommandée (cf. manuel d'utilisation) :

- **VCC** : Connecter à la broche 1 (3.3V)
- **GND** : Connecter à la broche 6 (GND)
- **MISO** : Connecter à la broche 21 (SPI_MISO)
- **MOSI** : Connecter à la broche 19 (SPI_MOSI)
- **SCK** : Connecter à la broche 23 (SPI_CLK)
- **NSS (CS)** : Connecter à la broche 24 (SPI_CE0_N)
- **RST** : Connecter à la broche 22 (GPIO 18)  
- **IRQ** : Non connecté

Assurez-vous que l'interface SPI est activée sur votre Raspberry Pi.

## Utilisation

Voici un exemple d'utilisation simple de la bibliothèque :

```python
from dependencies.custom_rc522 import RC522Reader

# Instanciation du lecteur avec les broches CS et RST souhaitées
reader = RC522Reader(cs=24, rst=22)

# Détection d'un tag
detected, info = reader.request()
if detected:
    error, uid = reader.anticoll()
    if error == 0:
        print("UID du tag :", uid)
    else:
        print("Erreur lors de la procédure anti-collision.")
else:
    print("Aucun tag détecté.")

# Libération des ressources
reader.cleanup()
```

Pour gérer plusieurs lecteurs, vous pouvez créer plusieurs instances de `RC522Reader` avec différentes broches CS et RST, et les utiliser simultanément dans votre application.

## Fichiers du projet

- `dependencies/custom_rc522.py` : La bibliothèque personnalisée pour le module RC522.
- `main.py` : Exemple de script qui utilise la bibliothèque pour gérer plusieurs lecteurs.
- `requirements.txt` : Liste des dépendances Python.
- `README.md` : Ce document de présentation.

## License

Ce projet est distribué sous licence MIT.

## Remerciements

- La bibliothèque s'inspire de la datasheet du module RC522 et des exemples fournis par HandsOn Technology.
- Utilise les bibliothèques [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) et [spidev](https://pypi.org/project/spidev/) pour l'interfaçage matériel sur Raspberry Pi.