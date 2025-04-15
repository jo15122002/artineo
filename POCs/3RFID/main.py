import neopixel
import ujson
from machine import SPI, Pin
from utime import sleep, ticks_diff, ticks_ms

import mfrc522

# Flag global pour l'appui du bouton
button_pressed = False

def button_irq_handler(pin):
    global button_pressed
    # Dès que le bouton est appuyé (front descendant), définir le flag.
    button_pressed = True

def setup():
    global rdr1, rdr2, rdr3, led1, led2, led3, button
    global last_uid1, last_uid2, last_uid3
    global expected_uid1, expected_uid2, expected_uid3

    print("Setup...")
    # Configuration SPI pour l'ESP32 (adaptation possible selon votre câblage)
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation des trois lecteurs RFID
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    
    # Facultatif : ajuster le gain (par exemple ici à 0x02)
    rdr1.set_gain(0x02)
    rdr2.set_gain(0x02)
    rdr3.set_gain(0x02)
    
    # Initialisation des LED WS2812b pour chaque lecteur RFID
    led1 = neopixel.NeoPixel(Pin(15), 1)
    led2 = neopixel.NeoPixel(Pin(18), 1)
    led3 = neopixel.NeoPixel(Pin(19), 1)
    for led in (led1, led2, led3):
        led[0] = (0, 0, 0)
        led.write()
    
    # Configuration du bouton sur le GPIO14 en mode pull-up.
    button = Pin(14, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq_handler)
    
    # Variables pour stocker les UID lus par chaque lecteur (sous forme de string)
    last_uid1 = None
    last_uid2 = None
    last_uid3 = None
    
    # UID attendus (exemple, en minuscules, sans séparateurs)
    expected_uid1 = "e7f000a9be"
    expected_uid2 = "ea1f11b054"
    expected_uid3 = "b66640c151"
    
    print("Placez une carte RFID et appuyez sur le bouton pour lancer la lecture ou l'assignation.")

def read_uid(reader, timeout=200):
    """
    Tente de lire un UID depuis 'reader' avec un timeout (en ms) pour éviter une attente excessive.
    Après la lecture, le tag est désactivé (halt et stop_crypto1) pour libérer le lecteur.
    """
    start = ticks_ms()
    uid = None
    while ticks_diff(ticks_ms(), start) < timeout:
        stat, tag_type = reader.request(reader.REQIDL)
        if stat == reader.OK:
            stat, raw_uid = reader.anticoll()
            if stat == reader.OK:
                uid = "".join("{:02x}".format(x) for x in raw_uid)
                break
        sleep(0.01)
    reader.halt_a()
    reader.stop_crypto1()
    return uid

def assign_cards(reader):
    """
    Fonction d'assignation des cartes aux mots-clés.
    Pour chaque mot dans chaque catégorie ("lieux", "couleurs", "émotions"),
    le programme attend que l'utilisateur place une carte RFID pour récupérer son UID,
    puis stocke l'association dans le fichier JSON "assignments.json".
    """
    assignments = {"lieux": {}, "couleurs": {}, "émotions": {}}
    
    # Charger les assignations existantes si le fichier existe
    try:
        with open("assignments.json", "r") as f:
            assignments = ujson.load(f)
            print(assignments)
        print("Assignations existantes chargées.")
    except Exception as e:
        print("Aucun fichier d'assignation existant, création d'un nouveau.")
    
    # Listes de mots-clés à assigner par catégorie
    lieux = ["Ville", "Campagne", "Jardin", "Rivière", "Restaurant", "Marché", "Océan", "Montagne", "Maison", "Atelier"]
    couleurs = ["Bleu", "Vert", "Gris", "Jaune", "Rouge", "Rose", "Orange", "Marron", "Violet", "Beige"]
    emotions = ["Curiosité", "Calme", "Monotonie", "joie", "tristesse", "colère", "amour", "fatigue", "Motivation", "Dégoût"]
    
    def assign_keyword(category, word):
        print("----")
        print("Pour la catégorie '{}', assignez le mot '{}'".format(category, word))
        uid = None
        # Attente active jusqu'à la détection d'une carte
        print("Placez une carte RFID sur le lecteur {} pour assigner '{}'".format(reader, word))
        while uid is None:
            uid = read_uid(reader, timeout=500)
            sleep(0.1)
        assignments[category][word] = uid
        # Sauvegarder immédiatement l'assignation
        with open("assignments.json", "w") as f:
            ujson.dump(assignments, f)
        print("Assignation enregistrée: {} -> {}".format(word, uid))
        sleep(1)
    
    print("Début de l'assignation des cartes aux mots-clés")
    for word in lieux:
        assign_keyword("lieux", word)
    for word in couleurs:
        assign_keyword("couleurs", word)
    for word in emotions:
        assign_keyword("émotions", word)
    print("Fin de l'assignation.")

def main():
    global last_uid1, last_uid2, last_uid3, button_pressed
    global expected_uid1, expected_uid2, expected_uid3
    setup()
    
    # Option : Demander à l'utilisateur s'il souhaite effectuer une assignation
    mode = input("Tapez 'a' pour assigner les cartes aux mots-clés ou 'r' pour simplement lire les tags : ")
    if mode.lower() == 'a':
        print("Mode assignation activé. Utilisation de rdr1 pour l'assignation...")
        assign_cards(rdr1)
        print("Assignation terminée. Redémarrage du programme...")
    
    while True:
        if button_pressed:
            button_pressed = False
            # Mesurer le temps d'exécution depuis l'appui
            start_time = ticks_ms()
            
            # Lire rapidement chaque lecteur avec un timeout court
            last_uid1 = read_uid(rdr1, timeout=200)
            last_uid2 = read_uid(rdr2, timeout=200)
            last_uid3 = read_uid(rdr3, timeout=200)
            
            print("Bouton appuyé, vérification des UID...")
            
            # Vérifier Lecteur 1
            if last_uid1 is None:
                led1[0] = (255, 165, 0)  # Orange
                print("Lecteur 1 : Aucune carte détectée")
            elif last_uid1 == expected_uid1:
                led1[0] = (0, 255, 0)    # Vert
                print("Lecteur 1 : UID correct")
            else:
                led1[0] = (255, 0, 0)    # Rouge
                print("Lecteur 1 : UID incorrect")
            led1.write()
            
            # Vérifier Lecteur 2
            if last_uid2 is None:
                led2[0] = (255, 165, 0)  # Orange
                print("Lecteur 2 : Aucune carte détectée")
            elif last_uid2 == expected_uid2:
                led2[0] = (0, 255, 0)    # Vert
                print("Lecteur 2 : UID correct")
            else:
                led2[0] = (255, 0, 0)    # Rouge
                print("Lecteur 2 : UID incorrect")
            led2.write()
            
            # Vérifier Lecteur 3
            if last_uid3 is None:
                led3[0] = (255, 165, 0)  # Orange
                print("Lecteur 3 : Aucune carte détectée")
            elif last_uid3 == expected_uid3:
                led3[0] = (0, 255, 0)    # Vert
                print("Lecteur 3 : UID correct")
            else:
                led3[0] = (255, 0, 0)    # Rouge
                print("Lecteur 3 : UID incorrect")
            led3.write()
            
            # Attendre le relâchement complet du bouton
            while button.value() == 0:
                sleep(0.01)
            
            # Optionnel : éteindre les LED après 2 secondes
            sleep(2)
            for led in (led1, led2, led3):
                led[0] = (0, 0, 0)
                led.write()
            
            # Afficher le temps écoulé depuis l'appui
            elapsed = ticks_diff(ticks_ms(), start_time)
            print("Temps écoulé depuis l'appui du bouton : {} ms".format(elapsed))
        
        sleep(0.05)

if __name__ == "__main__":
    print("Démarrage du programme...")
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
