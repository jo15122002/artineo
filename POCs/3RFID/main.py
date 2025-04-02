#!/usr/bin/env python3
import sys
import os
import time

# Ajouter le dossier dependencies au path pour importer la lib custom_rc522.py
current_dir = os.path.dirname(os.path.realpath(__file__))
dependencies_dir = os.path.join(current_dir, "dependencies")
if dependencies_dir not in sys.path:
    sys.path.append(dependencies_dir)

from custom_rc522 import RC522Reader

def main():
    # Instanciation de plusieurs lecteurs avec des broches CS et RST différentes
    # Adaptez ces numéros de broches selon votre câblage :
    try:
        reader1 = RC522Reader(cs=24, rst=22)
        # reader2 = RC522Reader(cs=23, rst=27)
        # reader3 = RC522Reader(cs=18, rst=25)

        # Regrouper les lecteurs dans une liste avec un identifiant pour chaque lecteur
        readers = [(1, reader1)]  # Ajoutez d'autres lecteurs si nécessaire
        print("Démarrage de la détection sur les lecteurs RFID...")
        
        while True:
            for reader_id, reader in readers:
                print(f"Lecteur {reader_id} : Attente de tag...")
                detected, _ = reader.request()
                if detected:
                    error, uid = reader.anticoll()
                    if error == 0:
                        print(f"Lecteur {reader_id} - Tag détecté : UID = {uid}")
                    else:
                        print(f"Lecteur {reader_id} - Erreur dans la procédure anticollision.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nArrêt du programme par l'utilisateur.")
    finally:
        # Nettoyage de chaque lecteur
        print("Nettoyage des ressources...")
        for _, reader in readers:
            reader.cleanup()

if __name__ == "__main__":
    main()
