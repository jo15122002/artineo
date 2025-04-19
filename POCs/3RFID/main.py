import neopixel
import ujson
from machine import SPI, Pin
from utime import sleep, ticks_diff, ticks_ms

import mfrc522
from ArtineoClient import ArtineoClient

# Variable globale d'intensité (0 = LED éteintes, 1 = intensité maximale)
intensity = 0.1
COOLDOWN_SECONDS = 2  # Cooldown entre deux essais

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
    global client, config

    print("Setup...")
    # Configuration SPI pour l'ESP32 (adaptation selon votre câblage)
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation des trois lecteurs RFID
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    
    # Initialiser et réinitialiser les modules
    rdr1.init()
    rdr2.init()
    rdr3.init()
    print("Lecteurs RFID initialisés.")
    
    # Facultatif : ajuster le gain (ici à 0x07, maximum)
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

    client = ArtineoClient(module_id=3)
    client.connect_ws()
    print("Connecté au serveur WebSocket.")
    config = client.fetch_config()
    print("Configuration récupérée:", config)
    
    # Variables pour stocker les UID lus par chaque lecteur (en string)
    last_uid1 = None
    last_uid2 = None
    last_uid3 = None
    
    # UID attendus par défaut (utilisés ici pour tests initiaux)
    expected_uid1 = "8804eaa5c3"
    expected_uid2 = "8804d091cd"
    expected_uid3 = "8804fa8cfa"
    
    print("Placez une carte RFID et appuyez sur le bouton pour lancer la lecture ou l'assignation.")

def read_uid(reader, attempts=2):
    """
    Tente de lire un UID depuis 'reader' en effectuant un nombre fixe d'essais.
    Après la lecture, le tag est désactivé (reset, halt et stop_crypto1) pour libérer le lecteur.
    
    :param reader: Instance du lecteur RFID.
    :param attempts: Nombre d'essais à effectuer.
    :return: L'UID lu sous forme de chaîne hexadécimale ou None si aucune lecture n'a réussi.
    """
    uid = None
    for _ in range(attempts):
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
    return uid

def get_answers(number):
    """
    Renvoie le dictionnaire des réponses correctes correspondant au numéro donné.
    Permet ainsi de sélectionner différents sets de réponses.
    
    :param number: Numéro du set de réponses.
    :return: Dictionnaire avec les clés "lieu", "couleur" et "emotion".
    """
    answers = {
        1: {"lieu": "8804eaa5c3", "couleur": "8804d091cd", "emotion": "8804fa8cfa"},
        2: {"lieu": "uidset2_lieu", "couleur": "uidset2_couleur", "emotion": "uidset2_emotion"}
    }
    return answers.get(number, answers[1])

def check_answers(uid_lieu, uid_couleur, uid_emotion, answer_set=1):
    """
    Vérifie si les UID fournis correspondent aux réponses correctes pour un set donné.
    Utilise get_answers(answer_set) pour récupérer le dictionnaire des réponses correctes.
    Met à jour les LED (led1, led2, led3) en appliquant l'intensité.
    
    - Si aucune carte n'est détectée → LED orange.
    - Si l'UID est correct → LED verte.
    - Sinon → LED rouge.
    
    Affiche également les messages correspondants.
    
    :param uid_lieu: UID du "lieu" (lecteur 1).
    :param uid_couleur: UID de la "couleur" (lecteur 2).
    :param uid_emotion: UID de l'"emotion" (lecteur 3).
    :param answer_set: Numéro du set de réponses à utiliser.
    :return: True si toutes les réponses sont correctes, sinon False.
    """
    correct = get_answers(answer_set)
    all_correct = True

    # Vérification du lieu via led1
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
    
    # Vérification de la couleur via led2
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
    
    # Vérification de l'émotion via led3
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
        print("Placez une carte RFID sur le lecteur pour assigner '{}'".format(word))
        while uid is None:
            uid = read_uid(reader, attempts=3)
            sleep(0.1)
        assignments[category][word] = uid
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
    global client, config
    setup()
    
    # Gestion du mode : 'a' pour assignation, 'r' pour lecture et vérification
    mode = "r"  # Par défaut, mode lecture. (Décommentez la ligne suivante pour interactivité)
    # mode = input("Tapez 'a' pour assigner les cartes aux mots-clés ou 'r' pour lire les tags et vérifier les réponses : ").strip().lower()
    if mode.lower() == 'a':
        print("Mode assignation activé. Utilisation de rdr1 pour l'assignation...")
        assign_cards(rdr1)
        print("Assignation terminée. Redémarrage du programme...")
    
    # Initialisation de la logique des sets de réponses et du nombre d'essais
    board_index = 1
    attempt_count = 0
    MAX_ATTEMPTS = 3  # 3 essais par set
    
    print("Mode lecture activé. Vous avez {} essais par set de réponses.".format(MAX_ATTEMPTS))
    print("Appuyez sur le bouton pour lancer une tentative.")

    uid1 = None
    uid2 = None
    uid3 = None
    
    while True:

        uid1 = read_uid(rdr1, attempts=3)
        uid2 = read_uid(rdr2, attempts=3)
        uid3 = read_uid(rdr3, attempts=3)

        if (uid1 != last_uid1 or
            uid2 != last_uid2 or
            uid3 != last_uid3):
            last_uid1 = uid1
            last_uid2 = uid2
            last_uid3 = uid3

            client.send_ws(ujson.dumps({
                "moduleNum": 3,
                "action": "set",
                "data" : {
                    "uid1": uid1,
                    "uid2": uid2,
                    "uid3": uid3
                }
            }))
        
        if button_pressed:
            button_pressed = False
            start_time = ticks_ms()
            
            print("Bouton appuyé, tentative {} pour le set {}.".format(attempt_count+1, board_index))
            # Vérification des réponses avec le set correspondant
            correct = check_answers(last_uid1, last_uid2, last_uid3, answer_set=board_index)
            
            attempt_count += 1
            if correct or attempt_count >= MAX_ATTEMPTS:
                if correct:
                    print("Bonne réponse obtenue après {} essai(s).".format(attempt_count))
                else:
                    print("Maximum d'essais atteint. Passage au set suivant.")
                board_index += 1
                attempt_count = 0
                # Vous pouvez ici afficher le nouveau set de réponses attendu pour l'utilisateur
                new_answers = get_answers(board_index)
                print("Nouveau set de réponses sélectionné:", new_answers)
            
            # Cooldown entre essais
            print("Cooldown de {} secondes...".format(COOLDOWN_SECONDS))
            sleep(COOLDOWN_SECONDS)
            
            # Afficher le temps écoulé
            elapsed = ticks_diff(ticks_ms(), start_time)
            print("Temps écoulé pour cet essai : {} ms".format(elapsed))
            
        sleep(0.05)

if __name__ == "__main__":
    print("Démarrage du programme...")
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
