#!/usr/bin/env python3
"""
test_multiple_readers_mfrc522.py

Ce script permet de tester successivement plusieurs lecteurs RFID RC522 en utilisant
la librairie mfrc522 (SimpleMFRC522). Pour chaque test, vous devez brancher le lecteur sur
votre Raspberry Pi selon la configuration souhaitée (par exemple, sur CE0 pour le Lecteur 1,
puis sur CE1 pour le Lecteur 2, etc.). Le script lit une carte RFID et affiche son UID et son texte.

Installation préalable :
    - Installez la librairie mfrc522 (voir README du dépôt)
    - Exécutez le script avec les droits administrateur (sudo) : sudo python3 test_multiple_readers_mfrc522.py

Appuyez sur Entrée après chaque test pour passer au lecteur suivant.
"""

from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
import time

def test_reader(reader, name="Lecteur"):
    print(f"{name} : Approchez une carte RFID du lecteur...")
    try:
        # La méthode read() attend qu'une carte soit détectée et renvoie son ID et un texte éventuel.
        id, text = reader.read()
        print(f"{name} : ID: {id}\nTexte: {text}")
    except Exception as e:
        print(f"{name} : Erreur lors de la lecture -> {e}")
    finally:
        # Nettoyage pour libérer les ressources GPIO
        GPIO.cleanup()
    # Pause pour laisser le temps de voir le résultat
    time.sleep(2)

def main():
    # Test du Lecteur 1 (branchez-le selon la configuration souhaitée)
    print("=== Test du Lecteur 1 ===")
    reader1 = SimpleMFRC522()
    test_reader(reader1, "Lecteur 1")
    
    input("Appuyez sur Entrée pour tester le Lecteur 2 (reconfigurez le branchement du module...)")
    
    # Test du Lecteur 2 (rebranchez le module sur une autre configuration, par exemple sur CE1)
    print("=== Test du Lecteur 2 ===")
    reader2 = SimpleMFRC522()
    test_reader(reader2, "Lecteur 2")
    
    input("Appuyez sur Entrée pour tester le Lecteur 3 (reconfigurez le branchement du module...)")
    
    # Test du Lecteur 3
    print("=== Test du Lecteur 3 ===")
    reader3 = SimpleMFRC522()
    test_reader(reader3, "Lecteur 3")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur.")
        GPIO.cleanup()
