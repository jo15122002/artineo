# debug_loop_lecteur1.py

import time
from machine import Pin, SPI
import pn532 as nfc   # votre pn532.py basé sur NFC_PN532_SPI

# ─────── 1) Configuration SPI ───────
# Ici on reprend VSPI / SPI(2) : SCK=12, MOSI=23, MISO=13
spi = SPI(2,
          baudrate=400_000,
          polarity=0,
          phase=0,
          sck=Pin(12),
          mosi=Pin(23),
          miso=Pin(13))
spi.init()

# ─────── 2) CS et RESET ───────
cs  = Pin(5, Pin.OUT)
rst = Pin(4, Pin.OUT)
cs.on()

print("▶️ DEBUG_LOOP Lecteur 1 (bring your NFC card within the white coil)")

# ─────── 3) Init PN532 en debug ───────
pn = nfc.PN532(spi, cs, irq=None, reset=rst, debug=True)

# ─────── 4) Vérif fw+SAM ───────
try:
    ic, ver, rev, support = pn.get_firmware_version()
    print("✅ FW v{}.{} (IC=0x{:02x}, sup=0x{:02x})".format(ver, rev, ic, support))
    pn.SAM_configuration()
    print("✅ SAM_configuration OK\n")
except Exception as e:
    print("❌ Erreur init PN532:", e)

# ─────── 5) Boucle de lecture ───────
print("⏳ Attente de la carte… (timeout 1000 ms par essai)")

while True:
    print("\n→ Nouvelle tentative de lecture")
    uid = pn.read_passive_target(timeout=1000)
    if uid:
        # on a lu un tag !
        hex_list = [hex(b) for b in uid]
        hex_str  = "-".join("{:02x}".format(b) for b in uid)
        print("🎉 Carte détectée ! raw:", hex_list)
        print("🎉 UID string:", hex_str)
        break
    else:
        print("— pas de carte (None), réessaie dans 500 ms")
        time.sleep(0.5)
