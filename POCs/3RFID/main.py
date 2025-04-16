import neopixel
import ujson
from machine import SPI, Pin
from utime import sleep, ticks_diff, ticks_ms

import mfrc522

# Variable globale d'intensité (0 = LED éteintes, 1 = intensité maximale)
intensity = 0.1

def scale_color(color):
    """
    Applique l'intensité à une couleur.
    color est une tuple (r, g, b) avec des valeurs comprises entre 0 et 255.
    Retourne une nouvelle tuple avec chaque composante multipliée par intensity.
    """
    return (int(color[0] * intensity), int(color[1] * intensity), int(color[2] * intensity))

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
    # Configuration SPI pour l'ESP32 (adaptation selon votre câblage)
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation des trois lecteurs RFID
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    
    rdr1.init()
    rdr2.init()
    rdr3.init()
    print("Lecteurs RFID initialisés.")
    
    # Facultatif : ajuster le gain (ici à 0x07, soit le maximum)
    rdr1.set_gain(0x07)
    rdr2.set_gain(0x07)
    rdr3.set_gain(0x07)
    
    print("Gain ajusté.")
    
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
    
    # Variables pour stocker les UID lus par chaque lecteur (en string)
    last_uid1 = None
    last_uid2 = None
    last_uid3 = None
    
    # UID attendus (exemple, en minuscules, sans séparateurs)
    expected_uid1 = "8804eaa5c3"
    expected_uid2 = "8804d091cd"
    expected_uid3 = "8804fa8cfa"
    
    print("Placez une carte RFID et appuyez sur le bouton pour lancer la lecture ou l'assignation.")

def read_uid(reader, timeout=20000):
    """
    Tente de lire un UID depuis 'reader' avec un timeout (en ms).
    Après la lecture, le tag est désactivé (halt et stop_crypto1) pour libérer le lecteur.
    Effectue jusqu'à 2 tentatives de lecture.
    """
    start = ticks_ms()
    uid = None
    attempts = 2  # Nombre de tentatives
    while attempts:
        start = ticks_ms()
        while ticks_diff(ticks_ms(), start) < timeout:
            stat, tag_type = reader.request(reader.REQIDL)
            if stat == reader.OK:
                stat, raw_uid = reader.anticoll()
                if stat == reader.OK:
                    uid = "".join("{:02x}".format(x) for x in raw_uid)
                    break
            sleep(0.01)
        reader.reset()
        reader.halt_a()
        reader.stop_crypto1()
        attempts -= 1
        if uid:
            break
    return uid

def get_answers(number):
    """
    Renvoie le dictionnaire des réponses correctes correspondant au numéro donné.
    Permet ainsi de sélectionner différents jeux de réponses pour la vérification.
    
    :param number: Numéro du set de réponses
    :return: Un dictionnaire avec les clés "lieu", "couleur" et "emotion"
    """
    answers = {
        1: {"lieu": "8804eaa5c3", "couleur": "8804d091cd", "emotion": "8804fa8cfa"},
        2: {"lieu": "uidset2_lieu", "couleur": "uidset2_couleur", "emotion": "uidset2_emotion"},
        3: {"lieu": "uidset2_lieu", "couleur": "uidset2_couleur", "emotion": "uidset2_emotion"}
    }
    return answers.get(number, answers[1])

def check_answers(uid_lieu, uid_couleur, uid_emotion, answer_set=1):
    """
    Vérifie si les UID fournis correspondent aux réponses correctes.
    Utilise get_answers(answer_set) pour récupérer le dictionnaire des bonnes réponses.
    Met à jour les LED (led1, led2, led3) en appliquant l'intensité.
    
    - Aucun UID → LED orange
    - UID correct → LED verte
    - Sinon → LED rouge
    
    Affiche les messages correspondants et renvoie True si toutes les réponses sont correctes.
    
    :param uid_lieu: UID lu par le lecteur associé au "lieu"
    :param uid_couleur: UID lu par le lecteur associé à la "couleur"
    :param uid_emotion: UID lu par le lecteur associé à l'"emotion"
    :param answer_set: Numéro du set de réponses à utiliser (par défaut 1)
    :return: True si toutes les réponses sont correctes, sinon False
    """
    correct = get_answers(answer_set)
    all_correct = True

    # Vérification du lieu via le lecteur 1 et mise à jour de led1
    if uid_lieu is None:
        led1[0] = scale_color((255, 165, 0))  # Orange
        print("Lecteur 1 : Aucune carte détectée")
        all_correct = False
    elif uid_lieu.lower().strip() == correct["lieu"].lower().strip():
        led1[0] = scale_color((0, 255, 0))    # Vert
        print("Lecteur 1 : UID correct")
    else:
        led1[0] = scale_color((255, 0, 0))    # Rouge
        print("Lecteur 1 : UID incorrect (attendu: {}, reçu: {})".format(correct["lieu"], uid_lieu))
        all_correct = False
    led1.write()
    
    # Vérification de la couleur via le lecteur 2 et mise à jour de led2
    if uid_couleur is None:
        led2[0] = scale_color((255, 165, 0))
        print("Lecteur 2 : Aucune carte détectée")
        all_correct = False
    elif uid_couleur.lower().strip() == correct["couleur"].lower().strip():
        led2[0] = scale_color((0, 255, 0))
        print("Lecteur 2 : UID correct")
    else:
        led2[0] = scale_color((255, 0, 0))
        print("Lecteur 2 : UID incorrect (attendu: {}, reçu: {})".format(correct["couleur"], uid_couleur))
        all_correct = False
    led2.write()
    
    # Vérification de l'émotion via le lecteur 3 et mise à jour de led3
    if uid_emotion is None:
        led3[0] = scale_color((255, 165, 0))
        print("Lecteur 3 : Aucune carte détectée")
        all_correct = False
    elif uid_emotion.lower().strip() == correct["emotion"].lower().strip():
        led3[0] = scale_color((0, 255, 0))
        print("Lecteur 3 : UID correct")
    else:
        led3[0] = scale_color((255, 0, 0))
        print("Lecteur 3 : UID incorrect (attendu: {}, reçu: {})".format(correct["emotion"], uid_emotion))
        all_correct = False
    led3.write()
    
    if all_correct:
        print("Toutes les réponses sont correctes!")
    else:
        print("Certaines réponses sont incorrectes.")
    
    return all_correct

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
            print("Assignations existantes chargées :", assignments)
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
        print("Placez une carte RFID sur le lecteur pour assigner '{}'".format(word))
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
    mode = "r"  # Par défaut, mode lecture
    # mode = input("Tapez 'a' pour assigner les cartes aux mots-clés ou 'r' pour simplement lire les tags et vérifier les réponses : ").strip().lower()
    if mode.lower() == 'a':
        print("Mode assignation activé. Utilisation de rdr1 pour l'assignation...")
        assign_cards(rdr1)
        print("Assignation terminée. Redémarrage du programme...")
    
    print("Mode lecture activé. Appuyez sur le bouton pour lire les cartes.")
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
            # Vérification globale avec mise à jour des LED intégrée dans check_answers()
            # Ici, nous utilisons get_answers() avec un numéro donné (par exemple, 1)
            check_answers(last_uid1, last_uid2, last_uid3, answer_set=1)
            
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
            setup()  # Réinitialiser pour la prochaine lecture
        
        sleep(0.05)

if __name__ == "__main__":
    print("Démarrage du programme...")
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
