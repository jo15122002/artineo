#!/usr/bin/env python3
"""
test_multiple_readers_mfrc522.py

Ce script teste successivement plusieurs lecteurs RFID RC522 en utilisant la bibliothèque MFRC522-python.
Pour chaque test, le script attend la détection d'une carte RFID et affiche l'UID lu.
Pour tester un autre lecteur, débranchez celui testé et reconfigurez le branchement (par exemple, en passant
le module sur CE1 pour le lecteur 2) puis appuyez sur Entrée pour continuer.

Prérequis :
    - Installation de la bibliothèque MFRC522-python (par exemple via : sudo python3 Read.py pour tester l'exemple)
    - Les librairies RPi.GPIO et spidev doivent être installées
    - Exécution avec sudo (les accès GPIO nécessitent souvent des droits administrateur)
"""

import MFRC522
import RPi.GPIO as GPIO
import time

def test_reader(reader, reader_name="Lecteur"):
    print(f"{reader_name} : Placez une carte RFID près du lecteur.")
    while True:
        # Demande la présence d'une carte (commande PICC_REQIDL)
        (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
        if status == reader.MI_OK:
            print(f"{reader_name} : Carte détectée!")
            # Récupère l'UID via la procédure d'anticollision
            (status, uid) = reader.MFRC522_Anticoll()
            if status == reader.MI_OK:
                print(f"{reader_name} : UID = {uid}")
                break
            else:
                print(f"{reader_name} : Erreur lors de l'anticollision.")
        time.sleep(0.1)

def main():
    try:
        # Test Lecteur 1 : configuration par défaut (par exemple SDA branché sur CE0)
        print("=== Test du Lecteur 1 ===")
        reader1 = MFRC522.MFRC522()
        test_reader(reader1, "Lecteur 1")
        reader1.cleanup()
        
        input("Appuyez sur Entrée pour tester le Lecteur 2 (rebranchez le module sur une configuration différente, par exemple SDA sur CE1)...")
        
        # Test Lecteur 2 :
        # Pour tester un deuxième lecteur, vous devrez brancher le module sur une autre configuration SPI
        # (par exemple, SDA sur CE1) et adapter, si nécessaire, la configuration dans le code de la bibliothèque.
        # Ici, on réinstancie l'objet MFRC522 pour tester ce deuxième lecteur.
        print("=== Test du Lecteur 2 ===")
        reader2 = MFRC522.MFRC522()
        test_reader(reader2, "Lecteur 2")
        reader2.cleanup()
        
        input("Appuyez sur Entrée pour tester le Lecteur 3 (rebranchez le module sur une troisième configuration)...")
        
        # Test Lecteur 3 :
        print("=== Test du Lecteur 3 ===")
        reader3 = MFRC522.MFRC522()
        test_reader(reader3, "Lecteur 3")
        reader3.cleanup()
        
    except KeyboardInterrupt:
        print("\nArrêt du programme par l'utilisateur.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()