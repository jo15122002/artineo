from machine import SPI, Pin
from utime import sleep

import mfrc522


def main():
    # Configuration SPI pour ESP32 :
    # Vous pouvez adapter les pins en fonction de votre câblage.
    # Ici on utilise SPI(1) avec une vitesse de 2.5MHz.
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0, sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation du lecteur RFID.
    # Dans cet exemple, gpioRst est connecté à GPIO0 et gpioCs à GPIO2.
    rdr = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    
    print("Placez une carte RFID près du lecteur...")
    
    while True:
        # Envoyer une requête pour détecter une carte (REQIDL)
        stat, tag_type = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            # Exécute la procédure d'anticollision pour récupérer l'UID
            stat, raw_uid = rdr.anticoll()
            if stat == rdr.OK:
                print("Carte détectée!")
                print("Type: 0x%02x" % tag_type)
                print("UID: 0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]))
                print("")
                # Attendre 2 secondes pour éviter des lectures multiples consécutives
                sleep(2)
        sleep(0.1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
