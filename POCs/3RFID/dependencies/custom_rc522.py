#!/usr/bin/env python3
"""
custom_rc522.py
----------------
Bibliothèque personnalisée pour utiliser les modules RFID RC522 sur Raspberry Pi.

Basée sur la datasheet du RC522 (cf. RC522.pdf :contentReference[oaicite:2]{index=2}&#8203;:contentReference[oaicite:3]{index=3}) et les exemples Arduino,
cette bibliothèque utilise spidev et RPi.GPIO pour communiquer avec le module via SPI,
en contrôlant manuellement les broches CS et RST.

Fonctionnalités principales :
  - Réinitialisation du module via la broche RST.
  - Initialisation du RC522 avec des valeurs recommandées.
  - Lecture et écriture de registres (avec adressage selon la datasheet).
  - Méthode request() pour envoyer une commande REQA (détection simplifiée d'un tag).
  - Méthode anticoll() pour récupérer l'UID d'une carte (implémentation rudimentaire).
  - Nettoyage des ressources SPI et GPIO.

Exemple d'utilisation :
    from custom_rc522 import RC522Reader
    reader = RC522Reader(cs=24, rst=22)  # Exemple : CS sur GPIO24, RST sur GPIO22
    detected, tag_info = reader.request()
    if detected:
        error, uid = reader.anticoll()
        if error == 0:
            print("UID du tag :", uid)
    reader.cleanup()
"""

import RPi.GPIO as GPIO
import spidev
import time

class RC522Reader:
    def __init__(self, cs, rst, spi_bus=0, spi_device=0):
        """
        Initialise le lecteur RC522 avec les broches CS et RST spécifiées.
        
        :param cs: Numéro de la broche GPIO utilisée pour CS (Chip Select)
        :param rst: Numéro de la broche GPIO utilisée pour RST (Reset)
        :param spi_bus: Numéro du bus SPI (par défaut 0)
        :param spi_device: Numéro du périphérique SPI (par défaut 0)
        """
        self.cs = cs
        self.rst = rst

        # Configuration des GPIO en mode BCM
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs, GPIO.OUT)
        GPIO.setup(self.rst, GPIO.OUT)
        # CS désactivé par défaut (niveau haut) et RST activé (niveau haut)
        GPIO.output(self.cs, GPIO.HIGH)
        GPIO.output(self.rst, GPIO.HIGH)
        
        # Initialisation de l'interface SPI
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 1000000  # 1 MHz (peut être ajusté)
        
        # Réinitialiser et initialiser le module
        self.reset()
        self.init_rc522()
    
    def reset(self):
        """Réinitialise le module RC522 via la broche RST et une commande soft-reset."""
        GPIO.output(self.rst, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.05)
        # Envoi d'une commande soft-reset (commande 0x0F dans CommandReg, adresse 0x01)
        self.write_register(0x01, 0x0F)
        time.sleep(0.05)
    
    def init_rc522(self):
        """
        Configure les registres du RC522 avec des valeurs courantes recommandées.
        Ces valeurs (ex. TModeReg, TPrescalerReg, etc.) sont tirées d'exemples Arduino et 
        de la datasheet.
        """
        self.write_register(0x2A, 0x8D)  # TModeReg : mode timer
        self.write_register(0x2B, 0x3E)  # TPrescalerReg : prescaler timer
        self.write_register(0x2C, 30)    # TReloadRegH
        self.write_register(0x2D, 0)     # TReloadRegL
        self.write_register(0x15, 0x40)  # TxASKReg : modulation 100% ASK
        self.write_register(0x11, 0x3D)  # ModeReg : mode opérationnel
    
    def write_register(self, reg, value):
        """
        Écrit une valeur dans un registre du RC522.
        
        Selon la datasheet, pour écrire, le premier octet envoyé est (reg << 1) & 0x7E.
        
        :param reg: Adresse du registre (en valeur décimale ou hexadécimale)
        :param value: Valeur à écrire dans le registre
        """
        address = ((reg << 1) & 0x7E)
        GPIO.output(self.cs, GPIO.LOW)
        self.spi.xfer2([address, value])
        GPIO.output(self.cs, GPIO.HIGH)
    
    def read_register(self, reg):
        """
        Lit une valeur dans un registre du RC522.
        
        Selon la datasheet, pour lire, le premier octet envoyé est ((reg << 1) & 0x7E) | 0x80.
        
        :param reg: Adresse du registre
        :return: Valeur lue dans le registre
        """
        address = (((reg << 1) & 0x7E) | 0x80)
        GPIO.output(self.cs, GPIO.LOW)
        response = self.spi.xfer2([address, 0])
        GPIO.output(self.cs, GPIO.HIGH)
        return response[1]
    
    def request(self, req_mode=0x26):
        """
        Envoie une commande REQA (par défaut 0x26) pour détecter la présence d'une carte.
        
        Cette méthode efface le FIFO, configure le BitFramingReg, envoie la commande 
        Transceive (0x0C) et place la commande REQA dans le FIFO. Elle attend ensuite un court délai
        pour récupérer une réponse simplifiée.
        
        :param req_mode: Mode de requête (0x26 pour toutes les cartes ISO/IEC 14443A)
        :return: (True, data) si une réponse est reçue, sinon (False, [])
        """
        # Flush FIFO
        self.write_register(0x0A, 0x80)
        # Configuration du BitFramingReg (valeur typique)
        self.write_register(0x0D, 0x07)
        # Envoi de la commande Transceive
        self.write_register(0x01, 0x0C)
        # Mettre la commande REQA dans le FIFO
        self.write_register(0x09, req_mode)
        # Démarrer la transmission en réglant certains bits (cette valeur est indicative)
        self.write_register(0x0D, 0x87)
        time.sleep(0.05)
        fifo_level = self.read_register(0x0A)
        if fifo_level:
            data = []
            for _ in range(fifo_level):
                data.append(self.read_register(0x09))
            return True, data
        return False, []
    
    def anticoll(self):
        """
        Exécute la procédure d'anticollision pour récupérer l'UID d'une carte.
        
        Envoie la commande anticollision (0x93, puis 0x20) et lit les données du FIFO.
        La réponse typique contient 5 octets : le premier est le code de cascade, suivi de 4 octets
        dont le dernier correspond à la somme de contrôle (BCC). Pour simplifier, cette méthode renvoie
        les 3 premiers octets de l'UID (dans cet exemple rudimentaire).
        
        :return: (error, uid) où error vaut 0 en cas de succès et uid est une liste d'octets.
        """
        # Flush FIFO
        self.write_register(0x0A, 0x80)
        # Écrire la commande anticollision dans le FIFO : 0x93 puis 0x20
        self.write_register(0x09, 0x93)
        self.write_register(0x09, 0x20)
        # Démarrer la transmission
        self.write_register(0x01, 0x0C)
        time.sleep(0.05)
        fifo_level = self.read_register(0x0A)
        if fifo_level >= 5:
            uid_full = []
            for _ in range(5):
                uid_full.append(self.read_register(0x09))
            # Ici, on extrait une partie de l'UID (par exemple, les 3 octets centraux) pour simplifier
            return 0, uid_full[1:4]
        return 1, []
    
    def cleanup(self):
        """
        Libère les ressources SPI et nettoie les broches GPIO utilisées par ce lecteur.
        """
        self.spi.close()
        GPIO.cleanup([self.cs, self.rst])

# Exemple de test si exécuté directement (pour débogage)
if __name__ == "__main__":
    try:
        reader = RC522Reader(cs=24, rst=22)
        print("Placez une carte RFID près du lecteur...")
        detected, info = reader.request()
        if detected:
            error, uid = reader.anticoll()
            if error == 0:
                print("UID détecté :", uid)
            else:
                print("Erreur dans l'anticollision.")
        else:
            print("Aucune carte détectée.")
    except KeyboardInterrupt:
        print("Interruption par l'utilisateur.")
    finally:
        reader.cleanup()
