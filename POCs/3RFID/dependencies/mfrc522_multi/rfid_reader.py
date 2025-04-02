import RPi.GPIO as GPIO
import spidev
import time

class MFRC522:
    def __init__(self, cs_pin=8, rst_pin=25, spi_bus=0, spi_dev=0):
        self.cs_pin = cs_pin
        self.rst_pin = rst_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.output(self.cs_pin, GPIO.HIGH)
        GPIO.setup(self.rst_pin, GPIO.OUT)
        GPIO.output(self.rst_pin, 1)

        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_dev)
        self.spi.max_speed_hz = 1000000

    def _write(self, addr, val):
        GPIO.output(self.cs_pin, GPIO.LOW)
        self.spi.xfer2([((addr << 1) & 0x7E), val])
        GPIO.output(self.cs_pin, GPIO.HIGH)

    def _read(self, addr):
        GPIO.output(self.cs_pin, GPIO.LOW)
        val = self.spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])
        GPIO.output(self.cs_pin, GPIO.HIGH)
        return val[1]

    def read_uid(self):
        # Méthode simplifiée : teste présence d'une carte
        # Si besoin : ajoute ici les étapes d'authentification
        try:
            tag_type = self._read(0x04)  # Register for TagType (simulé ici)
            if tag_type != 0:
                uid = [self._read(0x0A + i) for i in range(4)]
                return uid
        except Exception as e:
            return None
        return None
