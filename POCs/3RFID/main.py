from machine import SPI, Pin
from utime import sleep

import mfrc522


def main():
    # Configuration SPI pour ESP32
    spi = SPI(2, baudrate=2500000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    
    # Initialisation des trois lecteurs RFID
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4, gpioCs=5)    # Lecteur 1
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)   # Lecteur 2
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)   # Lecteur 3
    
    print("Placez une carte RFID près d'un des lecteurs...")
    
    while True:
        # Vérification du Lecteur 1
        stat1, tag_type1 = rdr1.request(rdr1.REQIDL)
        if stat1 == rdr1.OK:
            stat1, raw_uid1 = rdr1.anticoll()
            if stat1 == rdr1.OK:
                print("Lecteur 1 : Carte détectée !")
                print("Type : 0x%02x" % tag_type1)
                print("UID  : 0x%02x%02x%02x%02x" % (raw_uid1[0], raw_uid1[1], raw_uid1[2], raw_uid1[3]))
                print("")
                sleep(2)
                
        # Vérification du Lecteur 2
        stat2, tag_type2 = rdr2.request(rdr2.REQIDL)
        if stat2 == rdr2.OK:
            stat2, raw_uid2 = rdr2.anticoll()
            if stat2 == rdr2.OK:
                print("Lecteur 2 : Carte détectée !")
                print("Type : 0x%02x" % tag_type2)
                print("UID  : 0x%02x%02x%02x%02x" % (raw_uid2[0], raw_uid2[1], raw_uid2[2], raw_uid2[3]))
                print("")
                sleep(2)
                
        # Vérification du Lecteur 3
        stat3, tag_type3 = rdr3.request(rdr3.REQIDL)
        if stat3 == rdr3.OK:
            stat3, raw_uid3 = rdr3.anticoll()
            if stat3 == rdr3.OK:
                print("Lecteur 3 : Carte détectée !")
                print("Type : 0x%02x" % tag_type3)
                print("UID  : 0x%02x%02x%02x%02x" % (raw_uid3[0], raw_uid3[1], raw_uid3[2], raw_uid3[3]))
                print("")
                sleep(2)
        
        sleep(0.05)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt du programme")
