from machine import SPI, Pin
from utime import sleep
import mfrc522

def main():
    # Configuration SPI pour ESP32
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation du Lecteur 1 (RST: GPIO4, CS: GPIO5)
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)
    # Initialisation du Lecteur 2 (RST: GPIO16, CS: GPIO17)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    
    print("Placez une carte RFID près de l'un des lecteurs...")
    
    while True:
        # Vérifier le Lecteur 1
        stat1, tag_type1 = rdr1.request(rdr1.REQIDL)
        if stat1 == rdr1.OK:
            stat1, raw_uid1 = rdr1.anticoll()
            if stat1 == rdr1.OK:
                print("Lecteur 1 : Carte détectée !")
                print("Type: 0x%02x" % tag_type1)
                print("UID: 0x%02x%02x%02x%02x" % (raw_uid1[0], raw_uid1[1], raw_uid1[2], raw_uid1[3]))
                print("")
                sleep(2)  # Attendre pour éviter des lectures multiples consécutives

        # Vérifier le Lecteur 2
        stat2, tag_type2 = rdr2.request(rdr2.REQIDL)
        if stat2 == rdr2.OK:
            stat2, raw_uid2 = rdr2.anticoll()
            if stat2 == rdr2.OK:
                print("Lecteur 2 : Carte détectée !")
                print("Type: 0x%02x" % tag_type2)
                print("UID: 0x%02x%02x%02x%02x" % (raw_uid2[0], raw_uid2[1], raw_uid2[2], raw_uid2[3]))
                print("")
                sleep(2)  # Attendre pour éviter des lectures multiples consécutives
        
        sleep(0.1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
