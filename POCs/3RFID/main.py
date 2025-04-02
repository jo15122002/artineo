import RPi.GPIO as GPIO
import time
import requests
from mfrc522 import SimpleMFRC522

# Configuration des pins (mode BCM)
BUTTON_PIN = 18  # Bouton de confirmation (avec résistance pull-up)
LED_PIN = 23     # LED de feedback

# Configuration du serveur
SERVER_URL = "http://votre-serveur.com/api/rfid"  # Remplacez par l'URL de votre serveur

# Initialisation des GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

# Initialisation du lecteur RFID RC522
reader = SimpleMFRC522()

def send_rfid_data(tag):
    """Envoie l'ID RFID au serveur via une requête HTTP POST."""
    data = {"rfid": tag}
    try:
        response = requests.post(SERVER_URL, json=data)
        print("Réponse du serveur :", response.status_code, response.text)
    except Exception as e:
        print("Erreur lors de l'envoi :", e)

try:
    while True:
        print("Veuillez scanner votre tag RFID...")
        try:
            id, text = reader.read()  # Attend la détection d'un tag RFID
        except Exception as e:
            print("Erreur de lecture RFID :", e)
            time.sleep(1)
            continue

        # Conversion de l'ID en chaîne hexadécimale en majuscules
        tag_hex = hex(id)[2:].upper()
        print("Tag RFID détecté :", tag_hex)

        # Attente de la confirmation via le bouton
        print("Appuyez sur le bouton pour confirmer...")
        while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            time.sleep(0.1)
        print("Bouton appuyé, envoi des données...")

        # Envoi des données RFID au serveur
        send_rfid_data(tag_hex)

        # Feedback visuel via clignotement de la LED
        for _ in range(2):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.2)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.2)

        # Petite pause pour éviter une relecture immédiate
        time.sleep(1)

except KeyboardInterrupt:
    print("Arrêt du programme par l'utilisateur.")

finally:
    print("Nettoyage des GPIO.")
    GPIO.cleanup()