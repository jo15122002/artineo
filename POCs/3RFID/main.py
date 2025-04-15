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
    # Configuration SPI pour l'ESP32 : ajustez les pins selon votre câblage
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation des trois lecteurs RFID
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    
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
    # Le bouton doit relier la broche à 0 quand il est appuyé.
    button = Pin(14, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq_handler)
    
    # Variables pour stocker les UID lus par chaque lecteur (en string)
    last_uid1 = None
    last_uid2 = None
    last_uid3 = None
    
    # UID attendus (en minuscules, sans séparateurs)
    expected_uid1 = "e7f000a9be"
    expected_uid2 = "ea1f11b054"
    expected_uid3 = "b66640c151"
    
    print("Placez une carte RFID et appuyez sur le bouton pour lancer la lecture.")

def read_uid(reader, timeout=300):
    """
    Tente de lire un UID depuis 'reader' avec un timeout (en ms) ajusté.
    Effectue jusqu'à deux tentatives de lecture avant de renvoyer None.
    Après chaque tentative, le tag est désactivé pour libérer le lecteur.
    """
    uid = None
    attempts = 2  # Nombre de tentatives de lecture
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
        # Libère le lecteur
        reader.halt_a()
        reader.stop_crypto1()
        if uid is not None:
            break
        # Si l'UID n'a pas été lu, tenter une seconde fois
        attempts -= 1
        # Réinitialiser le timer pour la nouvelle tentative
        start = ticks_ms()
    return uid


def main():
    global last_uid1, last_uid2, last_uid3, button_pressed
    global expected_uid1, expected_uid2, expected_uid3
    setup()
    while True:
        if button_pressed:
            button_pressed = False
            # Démarrer la mesure du temps au moment de l'appui du bouton
            start_time = ticks_ms()
            
            # Lire rapidement chaque lecteur avec un timeout court
            last_uid1 = read_uid(rdr1, timeout=100)
            last_uid2 = read_uid(rdr2, timeout=100)
            last_uid3 = read_uid(rdr3, timeout=100)
            
            print("Bouton appuyé, vérification des UID...")
            # Vérifier Lecteur 1 et allumer la LED correspondante
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
                led2[0] = (255, 165, 0)
                print("Lecteur 2 : Aucune carte détectée")
            elif last_uid2 == expected_uid2:
                led2[0] = (0, 255, 0)
                print("Lecteur 2 : UID correct")
            else:
                led2[0] = (255, 0, 0)
                print("Lecteur 2 : UID incorrect")
            led2.write()
            
            # Vérifier Lecteur 3
            if last_uid3 is None:
                led3[0] = (255, 165, 0)
                print("Lecteur 3 : Aucune carte détectée")
            elif last_uid3 == expected_uid3:
                led3[0] = (0, 255, 0)
                print("Lecteur 3 : UID correct")
            else:
                led3[0] = (255, 0, 0)
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
            
            # Afficher le temps écoulé
            elapsed = ticks_diff(ticks_ms(), start_time)
            print("Temps écoulé depuis l'appui du bouton : {} ms".format(elapsed))
        
        sleep(0.05)

if __name__ == "__main__":
    print("Démarrage du programme...")
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
