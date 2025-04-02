#!/usr/bin/env python3
"""
test_multiple_readers.py

Ce script teste plusieurs lecteurs RFID RC522 un par un à l'aide de la bibliothèque pi-rc522.
Chaque lecteur est configuré avec des paramètres spécifiques (bus, device, pin_rst, etc.) pour
permettre l'utilisation de plusieurs modules sur un même Raspberry Pi.

Prérequis :
    pip install pi-rc522 spidev RPi.GPIO

Utilisation :
    sudo python3 test_multiple_readers.py
"""

import time
import RPi.GPIO as GPIO
from pirc522 import RFID

def test_reader(reader, name="Reader"):
    print(f"{name} : En attente d'une carte RFID...")
    # Attente active jusqu'à ce qu'une carte soit détectée
    reader.wait_for_tag()
    error, tag_type = reader.request()
    if error:
        print(f"{name} : Erreur lors de la requête (aucun tag détecté).")
        return
    error, uid = reader.anticoll()
    if error:
        print(f"{name} : Erreur lors de l'anticollision.")
    else:
        print(f"{name} : Tag détecté, UID = {uid}")
    time.sleep(1)

def main():
    # Reader 1 : configuration par défaut (SDA sur CE0, pin_rst par défaut)
    # reader1 = RFID(pin_mode=GPIO.BCM)  # utilise bus=0, device=0, pin_rst=15, pin_irq=18, pin_mode=GPIO.BOARD par défaut
    
    # Reader 2 : utilisation de CE1 (SDA branché sur CE1, par ex. GPIO7, pin physique 26)
    # Ici, on spécifie bus=0, device=1 et on désactive IRQ en passant pin_irq=None
    # reader2 = RFID(bus=0, device=1, pin_rst=15, pin_irq=None, pin_mode=GPIO.BOARD)
    
    # Reader 3 : utilisation d'une broche CE personnalisée via le paramètre pin_ce
    # Par exemple, on peut connecter SDA sur une broche libre et définir pin_ce manuellement.
    # Ici, on choisit pin_ce=26 (qui correspond à GPIO7 en BOARD, mais adaptez selon votre câblage)
    # reader3 = RFID(pin_ce=24, pin_rst=22, pin_irq=27, pin_mode=GPIO.BCM)
    # convert to GPIO.BOARD
    reader3 = RFID(pin_ce=24, pin_rst=22, pin_irq=27, pin_mode=GPIO.BOARD)
    
    # Regrouper les lecteurs avec un identifiant pour faciliter le test
    readers = [("Reader 1", reader3)]
    
    try:
        for name, rdr in readers:
            print(f"--- Test de {name} ---")
            test_reader(rdr, name)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nArrêt du test par l'utilisateur.")
    finally:
        for name, rdr in readers:
            rdr.cleanup()
            print(f"{name} : Ressources nettoyées.")

if __name__ == "__main__":
    main()
