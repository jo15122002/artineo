from os import uname

from machine import SPI, Pin

emptyRecv = b""

class MFRC522:
    """
    Classe pour accéder au module RFID MFRC522 en MicroPython.
    
    Permet de lire/écrire des données sur des tags RFID compatibles ISO/IEC 14443A.
    """
    GAIN_REG = 0x26
    MAX_GAIN = 0x07

    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    def __init__(self, spi=None, gpioRst=None, gpioCs=None):
        """
        Initialise le module MFRC522.
        
        :param spi: Instance SPI à utiliser (si None, crée une instance par défaut selon la plateforme)
        :param gpioRst: Numéro de la broche pour le Reset (RST)
        :param gpioCs: Numéro de la broche pour Chip Select (CS)
        """
        if gpioRst is not None:
            self.rst = Pin(gpioRst, Pin.OUT)
        else:
            self.rst = None
        assert(gpioCs is not None, "Needs gpioCs")
        if gpioCs is not None:
            self.cs = Pin(gpioCs, Pin.OUT)
        else:
            self.cs = None

        # Buffers pour les opérations SPI et les registres
        self.regBuf = bytearray(4)
        self.blockWriteBuf = bytearray(18)
        self.authBuf = bytearray(12)
        self.wregBuf = bytearray(2)
        self.rregBuf = bytearray(1)
        self.recvBuf = bytearray(16)
        self.recvMv = memoryview(self.recvBuf)

        if self.rst is not None:
            self.rst.value(0)
        if self.cs is not None:
            self.cs.value(1)

        if spi is not None:
            self.spi = spi
        else:
            sck = Pin(14, Pin.OUT)
            mosi = Pin(13, Pin.OUT)
            miso = Pin(12, Pin.IN)
            if uname()[0] == 'WiPy':
                self.spi = SPI(0)
                self.spi.init(SPI.MASTER, baudrate=1000000, pins=(sck, mosi, miso))
            elif uname()[0] == 'esp8266':
                self.spi = SPI(baudrate=100000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)
                self.spi.init()
            else:
                raise RuntimeError("Unsupported platform")

        if self.rst is not None:
            self.rst.value(1)
        self.init()

    def _wreg(self, reg, val):
        """
        Écrit une valeur dans le registre spécifié du MFRC522.
        
        :param reg: Adresse du registre (7 bits)
        :param val: Valeur à écrire dans le registre
        """
        if self.cs is not None:
            self.cs.value(0)
        buf = self.wregBuf
        buf[0] = 0xff & ((reg << 1) & 0x7e)
        buf[1] = 0xff & val
        self.spi.write(buf)
        if self.cs is not None:
            self.cs.value(1)

    def _rreg(self, reg):
        """
        Lit et renvoie la valeur d'un registre spécifié.
        
        :param reg: Adresse du registre
        :return: Valeur lue (entier)
        """
        if self.cs is not None:
            self.cs.value(0)
        buf = self.rregBuf
        buf[0] = 0xff & (((reg << 1) & 0x7e) | 0x80)
        self.spi.write(buf)
        val = self.spi.read(1)
        if self.cs is not None:
            self.cs.value(1)
        return val[0]

    def _sflags(self, reg, mask):
        """
        Met à 1 les bits correspondant au masque dans le registre spécifié.
        
        :param reg: Adresse du registre
        :param mask: Masque des bits à mettre à 1
        """
        self._wreg(reg, self._rreg(reg) | mask)

    def _cflags(self, reg, mask):
        """
        Met à 0 les bits correspondant au masque dans le registre spécifié.
        
        :param reg: Adresse du registre
        :param mask: Masque des bits à effacer
        """
        self._wreg(reg, self._rreg(reg) & (~mask))

    def _tocard(self, cmd, send, into=None):
        """
        Effectue la communication avec la carte en envoyant une commande.
        
        :param cmd: Commande à envoyer (ex: 0x0C pour Transceive, 0x0E pour CRC)
        :param send: Liste des octets à envoyer
        :param into: Buffer optionnel pour lire la réponse
        :return: Tuple (stat, recv, bits)
                 stat : code de retour (OK, NOTAGERR, ERR)
                 recv : données lues (bytearray ou memoryview)
                 bits : nombre de bits reçus
        """
        recv = emptyRecv
        bits = irq_en = wait_irq = n = 0
        stat = self.ERR

        if cmd == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30

        self._wreg(0x02, irq_en | 0x80)
        self._cflags(0x04, 0x80)
        self._sflags(0x0A, 0x80)
        self._wreg(0x01, 0x00)

        for c in send:
            self._wreg(0x09, c)
        self._wreg(0x01, cmd)

        if cmd == 0x0C:
            self._sflags(0x0D, 0x80)

        i = 2000
        while True:
            n = self._rreg(0x04)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break

        self._cflags(0x0D, 0x80)

        if i:
            if (self._rreg(0x06) & 0x1B) == 0x00:
                stat = self.OK
                if n & irq_en & 0x01:
                    stat = self.NOTAGERR
                elif cmd == 0x0C:
                    n = self._rreg(0x0A)
                    lbits = self._rreg(0x0C) & 0x07
                    if lbits != 0:
                        bits = (n - 1) * 8 + lbits
                    else:
                        bits = n * 8

                    if n == 0:
                        n = 1
                    elif n > 16:
                        n = 16

                    if into is None:
                        recv = self.recvBuf
                    else:
                        recv = into
                    pos = 0
                    while pos < n:
                        recv[pos] = self._rreg(0x09)
                        pos += 1
                    if into is None:
                        recv = self.recvMv[:n]
                    else:
                        recv = into
            else:
                stat = self.ERR

        return stat, recv, bits

    def _assign_crc(self, data, count):
        """
        Calcule et assigne la CRC aux données (en modifiant le buffer 'data').
        
        :param data: Buffer contenant les données
        :param count: Nombre d'octets avant d'ajouter la CRC (la CRC sera écrite à data[count] et data[count+1])
        """
        self._cflags(0x05, 0x04)
        self._sflags(0x0A, 0x80)
        dataPos = 0
        while dataPos < count:
            self._wreg(0x09, data[dataPos])
            dataPos += 1

        self._wreg(0x01, 0x03)

        i = 0xFF
        while True:
            n = self._rreg(0x05)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break

        data[count] = self._rreg(0x22)
        data[count + 1] = self._rreg(0x21)

    def init(self):
        """
        Initialise le module MFRC522 : réinitialisation, configuration des registres et activation de l'antenne.
        """
        self.reset()
        self._wreg(0x2A, 0x8D)
        self._wreg(0x2B, 0x3E)
        self._wreg(0x2D, 30)
        self._wreg(0x2C, 0)
        self._wreg(0x15, 0x40)
        self._wreg(0x11, 0x3D)
        self.set_gain(self.MAX_GAIN)
        self.antenna_on()

    def reset(self):
        """
        Effectue une réinitialisation logicielle du module en écrivant 0x0F dans le registre Command.
        """
        self._wreg(0x01, 0x0F)

    def antenna_on(self, on=True):
        """
        Active ou désactive l'antenne en modifiant le registre approprié.
        
        :param on: True pour activer, False pour désactiver
        """
        if on and ~(self._rreg(0x14) & 0x03):
            self._sflags(0x14, 0x03)
        else:
            self._cflags(0x14, 0x03)

    def request(self, mode):
        """
        Envoie une commande REQ pour détecter une carte RFID.
        
        :param mode: Mode de requête (ex : REQIDL ou REQALL)
        :return: Tuple (stat, bits) où 'stat' est le code de retour et 'bits' le nombre de bits reçus.
        """
        self._wreg(0x0D, 0x07)
        (stat, recv, bits) = self._tocard(0x0C, [mode])
        if (stat != self.OK) | (bits != 0x10):
            stat = self.ERR
        return stat, bits

    def anticoll(self):
        """
        Exécute la procédure d'anticollision pour récupérer l'UID d'une carte.
        
        :return: Tuple (stat, uid) où 'stat' est le code de retour et 'uid' est un bytearray contenant l'UID.
        """
        ser_chk = 0
        ser = [0x93, 0x20]
        self._wreg(0x0D, 0x00)
        (stat, recv, bits) = self._tocard(0x0C, ser)
        if stat == self.OK:
            if len(recv) == 5:
                for i in range(4):
                    ser_chk ^= recv[i]
                if ser_chk != recv[4]:
                    stat = self.ERR
            else:
                stat = self.ERR
        return stat, bytearray(recv)

    def select_tag(self, ser):
        """
        Sélectionne un tag RFID à partir de son UID.
        
        :param ser: UID du tag (liste ou bytearray de 4 octets)
        :return: OK si la sélection est réussie, sinon ERR.
        """
        buf = bytearray(9)
        buf[0] = 0x93
        buf[1] = 0x70
        buf[2:7] = ser
        self._assign_crc(buf, 7)
        (stat, recv, bits) = self._tocard(0x0C, buf)
        return self.OK if (stat == self.OK) and (bits == 0x18) else self.ERR

    def auth(self, mode, addr, sect, ser):
        """
        Effectue l'authentification sur un bloc du tag à l'aide d'une clé.
        
        :param mode: Mode d'authentification (AUTHENT1A ou AUTHENT1B)
        :param addr: Adresse du bloc à authentifier
        :param sect: Clé (6 octets) pour l'authentification
        :param ser: UID du tag (utilise les 4 premiers octets)
        :return: Code de retour de la commande d'authentification.
        """
        buf = self.authBuf
        buf[0] = mode  # Mode d'authentification
        buf[1] = addr  # Bloc
        buf[2:8] = sect  # Clé
        buf[8:12] = ser[:4]  # UID (4 octets)
        return self._tocard(0x0E, buf)[0]

    def halt_a(self):
        """
        Implémente la commande HALT_A.
        Conformément à la datasheet, envoie la commande 0x50, 0x00 suivie du CRC.
        """
        buf = bytearray(4)  # Allocation d'un buffer de 4 octets
        buf[0] = 0x50
        buf[1] = 0x00
        self._assign_crc(buf, 2)
        self._tocard(0x0C, buf)


    def stop_crypto1(self):
        """
        Désactive le chiffrement (crypto1) utilisé pour l'authentification avec le tag.
        """
        self._cflags(0x08, 0x08)

    def set_gain(self, gain):
        """
        Configure le gain du récepteur.
        
        :param gain: Valeur de gain, jusqu'à MAX_GAIN.
        """
        assert gain <= self.MAX_GAIN
        self._cflags(self.GAIN_REG, 0x07 << 4)
        self._sflags(self.GAIN_REG, gain << 4)

    def read(self, addr, into=None):
        """
        Lit 16 octets à partir d'un bloc spécifié sur le tag.
        
        :param addr: Adresse du bloc à lire.
        :param into: Buffer optionnel dans lequel copier les données.
        :return: Les données lues (bytearray) si OK, sinon None.
        """
        buf = self.regBuf
        buf[0] = 0x30
        buf[1] = addr
        self._assign_crc(buf, 2)
        (stat, recv, _) = self._tocard(0x0C, buf, into=into)
        if into is None:
            recv = bytearray(recv)
        return recv if stat == self.OK else None

    def write(self, addr, data):
        """
        Écrit 16 octets dans un bloc spécifié sur le tag.
        
        :param addr: Adresse du bloc à écrire.
        :param data: Bytearray de 16 octets à écrire.
        :return: OK si l'écriture est réussie, sinon ERR.
        """
        buf = self.regBuf
        buf[0] = 0xA0
        buf[1] = addr
        self._assign_crc(buf, 2)
        (stat, recv, bits) = self._tocard(0x0C, buf)
        if not (stat == self.OK) or not (bits == 4) or not ((recv[0] & 0x0F) == 0x0A):
            stat = self.ERR
        else:
            buf = self.blockWriteBuf
            i = 0
            while i < 16:
                buf[i] = data[i]
                i += 1
            self._assign_crc(buf, 16)
            (stat, recv, bits) = self._tocard(0x0C, buf)
            if not (stat == self.OK) or not (bits == 4) or not ((recv[0] & 0x0F) == 0x0A):
                stat = self.ERR
        return stat