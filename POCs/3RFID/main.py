import RPi.GPIO as GPIO
from dependencies.mfrc522_multi.rfid_reader import MFRC522
import time

# Configuration des lecteurs RFID
READERS = [
    {"name": "Lecteur 1", "cs": 8},   # GPIO8 (CE0)
    # {"name": "Lecteur 2", "cs": 7},   # GPIO7 (CE1)
    # {"name": "Lecteur 3", "cs": 25},  # GPIO25 (GPIO libre)
]

# Initialisation des lecteurs
readers = []
for reader in READERS:
    mfrc = MFRC522(cs_pin=reader["cs"])
    readers.append({"device": mfrc, "name": reader["name"]})

print("🟢 Lecture RFID multi-lecteurs démarrée (Ctrl+C pour arrêter)")

try:
    while True:
        for reader in readers:
            uid = reader["device"].read_uid()
            if uid:
                uid_str = "-".join(map(str, uid))
                print(f"[{reader['name']}] ✅ Carte détectée : {uid_str}")
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n🛑 Arrêt du programme.")
finally:
    GPIO.cleanup()