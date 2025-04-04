from machine import SPI, Pin
from utime import sleep
import mfrc522
import neopixel

def main():
    # Configuration SPI pour l'ESP32
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation des trois lecteurs RFID
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    
    # Initialisation des LED pour chaque lecteur RFID
    led1 = neopixel.NeoPixel(Pin(15), 1)
    led2 = neopixel.NeoPixel(Pin(18), 1)
    led3 = neopixel.NeoPixel(Pin(19), 1)
    # Éteindre les LED initialement
    for led in (led1, led2, led3):
        led[0] = (0, 0, 0)
        led.write()
    
    # # Initialisation du bouton sur le pin 21 avec résistance pull-down
    button = Pin(14, Pin.IN)
    
    # Variables pour stocker le dernier UID lu pour chaque lecteur (sous forme de string)
    last_uid1 = None
    last_uid2 = None
    last_uid3 = None
    
    # UID attendus sous forme de chaîne (sans séparateurs, en minuscules)
    expected_uid1 = "e7f000a9be"
    expected_uid2 = "ea1f11b054"
    expected_uid3 = "b66640c151"
    
    print("Placez une carte RFID près d'un des lecteurs...")
    
    while True:
        # print(button.value())

        # Vérification continue du lecteur 1
        stat1, tag_type1 = rdr1.request(rdr1.REQIDL)
        if stat1 == rdr1.OK:
            stat1, raw_uid1 = rdr1.anticoll()
            if stat1 == rdr1.OK:
                # Conversion de la liste d'octets en string hexadécimal
                last_uid1 = "".join("{:02x}".format(x) for x in raw_uid1)
                print("Lecteur 1 : Carte détectée, UID :", last_uid1)
                sleep(0.5)
                
        # Vérification continue du lecteur 2
        stat2, tag_type2 = rdr2.request(rdr2.REQIDL)
        if stat2 == rdr2.OK:
            stat2, raw_uid2 = rdr2.anticoll()
            if stat2 == rdr2.OK:
                last_uid2 = "".join("{:02x}".format(x) for x in raw_uid2)
                print("Lecteur 2 : Carte détectée, UID :", last_uid2)
                # sleep(0.5)
                
        # Vérification continue du lecteur 3
        stat3, tag_type3 = rdr3.request(rdr3.REQIDL)
        if stat3 == rdr3.OK:
            stat3, raw_uid3 = rdr3.anticoll()
            if stat3 == rdr3.OK:
                last_uid3 = "".join("{:02x}".format(x) for x in raw_uid3)
                print("Lecteur 3 : Carte détectée, UID :", last_uid3)
                # sleep(0.5)
        
        # Vérification à l'appui du bouton
        if button.value() == 0:
            print("Bouton appuyé, vérification des UID...")
            # Lecteur 1
            if last_uid1 is None:
                led1[0] = (255, 165, 0)  # Orange
                print("Lecteur 1 : Aucune carte détectée, LED orange")
            elif last_uid1 == expected_uid1:
                led1[0] = (0, 255, 0)    # Vert
                print("Lecteur 1 : UID correct, LED verte")
            else:
                led1[0] = (255, 0, 0)    # Rouge
                print("Lecteur 1 : UID incorrect, LED rouge")
            led1.write()
            
            # Lecteur 2
            if last_uid2 is None:
                led2[0] = (255, 165, 0)  # Orange
                print("Lecteur 2 : Aucune carte détectée, LED orange")
            elif last_uid2 == expected_uid2:
                led2[0] = (0, 255, 0)    # Vert
                print("Lecteur 2 : UID correct, LED verte")
            else:
                led2[0] = (255, 0, 0)    # Rouge
                print("Lecteur 2 : UID incorrect, LED rouge")
            led2.write()
            
            # Lecteur 3
            if last_uid3 is None:
                led3[0] = (255, 165, 0)  # Orange
                print("Lecteur 3 : Aucune carte détectée, LED orange")
            elif last_uid3 == expected_uid3:
                led3[0] = (0, 255, 0)    # Vert
                print("Lecteur 3 : UID correct, LED verte")
            else:
                led3[0] = (255, 0, 0)    # Rouge
                print("Lecteur 3 : UID incorrect, LED rouge")
            led3.write()
            
            # Attente que le bouton soit relâché pour éviter les déclenchements multiples
            while button.value() == 0:
                sleep(0.1)
            
            # Optionnel : remettre les LED à l'état éteint après quelques secondes
            # sleep(2)
            for led in (led1, led2, led3):
                led[0] = (0, 0, 0)
                led.write()
                
        sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
