import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import threading
import time

# Configuration des Chip Select et RST pour les 3 lecteurs
READERS_CONFIG = [
    {"cs": 8, "rst": 25, "name": "Lecteur 1"},
    {"cs": 7, "rst": 24, "name": "Lecteur 2"},
    {"cs": 12, "rst": 23, "name": "Lecteur 3"},
]

# Désactivation des warnings GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Fonction pour lire un lecteur RFID
def read_rfid(reader_config):
    reader = SimpleMFRC522(spi_bus=0, spi_device=0, gpio_cs=reader_config["cs"], gpio_rst=reader_config["rst"])
    print(f"[{reader_config['name']}] Prêt à scanner...")

    try:
        while True:
            id, text = reader.read_no_block()
            if id:
                print(f"[{reader_config['name']}] Tag détecté : {id} | Message : {text.strip()}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print(f"\n[{reader_config['name']}] Arrêté.")

# Démarrage des threads pour chaque lecteur
threads = []
for config in READERS_CONFIG:
    t = threading.Thread(target=read_rfid, args=(config,), daemon=True)
    threads.append(t)
    t.start()

# Boucle principale
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nArrêt du programme...")
    GPIO.cleanup()
 