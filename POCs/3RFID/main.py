import machine
import mfrc522
import time

# Configuration SPI (adaptez les numéros de broches selon votre câblage)
# Exemple avec ESP32 Wroom-32 :
#   SCK  -> GPIO18
#   MOSI -> GPIO23
#   MISO -> GPIO19
spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0,
                  sck=machine.Pin(18), mosi=machine.Pin(23), miso=machine.Pin(19))

# Configuration des broches pour le module RFID :
#   CS (SDA) -> par exemple GPIO5
#   RST      -> par exemple GPIO22
cs = machine.Pin(5, machine.Pin.OUT)
rst = machine.Pin(22, machine.Pin.OUT)

# Initialisation du lecteur RFID
rdr = mfrc522.MFRC522(spi=spi, cs=cs, rst=rst)

print("Placez une carte RFID près du lecteur...")

while True:
    # La commande request() permet de détecter une carte
    (status, tag_type) = rdr.request()
    if status == rdr.OK:
        print("Carte détectée")
        # Procédure d'anticollision pour récupérer l'UID
        (status, raw_uid) = rdr.anticoll()
        if status == rdr.OK:
            print("UID de la carte :", raw_uid)
            # Petite pause pour éviter une lecture multiple immédiate
            time.sleep(2)
    time.sleep(0.1)
