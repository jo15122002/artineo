import RPi.GPIO as GPIO
import time
import requests
from pirc522 import RFID

SERVER_URL = "http://votre-serveur.com/api/rfid"  # Remplacez par votre URL de serveur

def send_rfid_data(reader_id, uid):
    """Envoie l'UID du tag et l'identifiant du lecteur au serveur."""
    data = {"reader": reader_id, "rfid": uid}
    try:
        response = requests.post(SERVER_URL, json=data)
        print(f"Réponse du serveur pour le lecteur {reader_id} :", response.status_code, response.text)
    except Exception as e:
        print("Erreur lors de l'envoi :", e)

# Instanciation des lecteurs avec des broches CS et RST différentes
# Les numéros de broches sont en mode BCM.
rdr1 = RFID(cs=8, rst=25)   # Premier lecteur : CS sur GPIO8, RST sur GPIO25
rdr2 = RFID(cs=7, rst=24)   # Deuxième lecteur : CS sur GPIO7, RST sur GPIO24
rdr3 = RFID(cs=12, rst=23)  # Troisième lecteur : CS sur GPIO12, RST sur GPIO23

# Regrouper les lecteurs avec un identifiant pour faciliter le suivi
readers = [(1, rdr1), (2, rdr2), (3, rdr3)]

try:
    while True:
        # Parcours de chaque lecteur pour vérifier la présence d'un tag
        for reader_id, rdr in readers:
            print(f"Lecteur {reader_id} : en attente de tag...")
            rdr.wait_for_tag()  # Attend qu'un tag soit présenté
            (error, tag_type) = rdr.request()
            if not error:
                (error, uid) = rdr.anticoll()  # Récupère l'UID du tag
                if not error:
                    # Formatage de l'UID en chaîne de chiffres séparés par des tirets
                    uid_str = "-".join([str(i) for i in uid])
                    print(f"Lecteur {reader_id} - Tag détecté, UID : {uid_str}")
                    send_rfid_data(reader_id, uid_str)
                    # Petite pause pour éviter la lecture multiple du même tag
                    time.sleep(2)
            # Optionnel : nettoyer l'état du lecteur avant la prochaine boucle
            rdr.cleanup()
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Arrêt du programme.")
