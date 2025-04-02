import RPi.GPIO as GPIO
import spidev
import time

class MFRC522:
    # Constantes du module RC522
    CommandReg = 0x01
    CommIEnReg = 0x02
    CommIrqReg = 0x04
    FIFOLevelReg = 0x0A
    FIFODataReg = 0x09
    BitFramingReg = 0x0D
    ModeReg = 0x11
    TxControlReg = 0x14
    ErrorReg = 0x06

    PCD_IDLE = 0x00
    PCD_TRANSCEIVE = 0x0C
    PICC_REQIDL = 0x26
    PICC_ANTICOLL = 0x93

    OK = 0
    ERROR = 1

    def __init__(self, cs_pin=8, rst_pin=22, spi_bus=0, spi_dev=0):
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

        self.init()

    def _write(self, addr, val):
        GPIO.output(self.cs_pin, GPIO.LOW)
        self.spi.xfer2([(addr << 1) & 0x7E, val])
        GPIO.output(self.cs_pin, GPIO.HIGH)

    def _read(self, addr):
        GPIO.output(self.cs_pin, GPIO.LOW)
        val = self.spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])
        GPIO.output(self.cs_pin, GPIO.HIGH)
        return val[1]

    def init(self):
        self.reset()
        self._write(self.TModeReg(), 0x8D)
        self._write(self.TPrescalerReg(), 0x3E)
        self._write(self.TReloadRegL(), 30)
        self._write(self.TReloadRegH(), 0)
        self._write(self.TxAutoReg(), 0x40)
        self._write(self.ModeReg, 0x3D)
        self.antenna_on()

    def reset(self):
        self._write(self.CommandReg, self.PCD_IDLE)

    def antenna_on(self):
        temp = self._read(self.TxControlReg)
        if ~(temp & 0x03):
            self._write(self.TxControlReg, temp | 0x03)

    def TModeReg(self):
        return 0x2A

    def TPrescalerReg(self):
        return 0x2B

    def TReloadRegH(self):
        return 0x2C

    def TReloadRegL(self):
        return 0x2D

    def TxAutoReg(self):
        return 0x15

    def request(self):
        self._write(self.BitFramingReg, 0x07)
        (status, back_data, back_bits) = self._to_card(self.PCD_TRANSCEIVE, [self.PICC_REQIDL])
        if (status != self.OK) or (back_bits != 0x10):
            return (self.ERROR, None)
        return (self.OK, back_data)

    def anticoll(self):
        ser_num = []
        self._write(self.BitFramingReg, 0x00)
        (status, back_data, back_bits) = self._to_card(self.PCD_TRANSCEIVE, [self.PICC_ANTICOLL, 0x20])
        if status == self.OK:
            if len(back_data) == 5:
                checksum = 0
                for i in range(4):
                    checksum ^= back_data[i]
                if checksum != back_data[4]:
                    return (self.ERROR, None)
                ser_num = back_data
            else:
                return (self.ERROR, None)
        return (status, ser_num)

    def _to_card(self, command, send_data):
        back_data = []
        back_bits = 0
        error = 0

        self._write(self.CommandReg, self.PCD_IDLE)
        self._write(self.CommIEnReg, 0x77)
        self._write(self.CommIrqReg, 0x7F)
        self._write(self.FIFOLevelReg, 0x80)

        for data in send_data:
            self._write(self.FIFODataReg, data)

        self._write(self.CommandReg, command)

        if command == self.PCD_TRANSCEIVE:
            self._write(self.BitFramingReg, 0x80)

        i = 2000
        while True:
            n = self._read(self.CommIrqReg)
            i -= 1
            if (n & 0x01) or (n & 0x30):
                break
            if i == 0:
                return (self.ERROR, None, None)

        error = self._read(self.ErrorReg)
        if error & 0x1B:
            return (self.ERROR, None, None)

        n = self._read(self.FIFOLevelReg)
        last_bits = self._read(self.ControlReg()) & 0x07
        if last_bits != 0:
            back_bits = (n - 1) * 8 + last_bits
        else:
            back_bits = n * 8

        for _ in range(n):
            back_data.append(self._read(self.FIFODataReg))

        return (self.OK, back_data, back_bits)

    def ControlReg(self):
        return 0x0C

    def read_uid(self):
        (status, TagType) = self.request()
        if status != self.OK:
            return None
        (status, uid) = self.anticoll()
        if status == self.OK:
            return uid
        return None
