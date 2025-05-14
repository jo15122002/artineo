# modules/3RFID/main.py

import neopixel
import pn532  # ton pn532.py basé sur NFC_PN532_SPI
import uasyncio as asyncio
import ujson
from ArtineoClientMicro import ArtineoClient
from machine import SPI, Pin
from utime import ticks_diff, ticks_ms

# ──────────────────────────────────────────────────────────────────────────────
# Configuration matériel
# ──────────────────────────────────────────────────────────────────────────────
# Broches SPI(2) (VSPI) : SCK=12, MOSI=23, MISO=13
SPI_ID     = 2
SPI_BAUD   = 1_000_000  # passe à 400_000 ou 100_000 si besoin de stabilité
CS_PINS    = [5, 17, 26]  # CS pour rdr1, rdr2, rdr3
RST_PINS   = [4, 16, 25]  # RST pour rdr1, rdr2, rdr3
LED_PINS   = [15, 18, 19] # NeoPixel X1 par lecteur
BUTTON_PIN = 14           # bouton en pull-up

# Paramètres de l’application
INTENSITY     = 0.1      # luminosité des LEDs (0…1)
COOLDOWN      = 2        # secondes entre validations
MAX_ATTEMPTS  = 3        # essais max par set
READ_TRIES    = 15       # tentatives de lecture par cycle
READ_DELAY_MS = 50       # délai entre tentatives (ms)


# ──────────────────────────────────────────────────────────────────────────────
# Variables globales
# ──────────────────────────────────────────────────────────────────────────────
rdrs           = []      # liste des 3 lecteurs PN532
leds           = []      # liste des 3 NeoPixel
button_pressed = False
current_set    = 1
attempt_count  = 0

client = None
config = {}


# ──────────────────────────────────────────────────────────────────────────────
# Fonctions utilitaires
# ──────────────────────────────────────────────────────────────────────────────
def scale_color(col):
    return (
        int(col[0] * INTENSITY),
        int(col[1] * INTENSITY),
        int(col[2] * INTENSITY),
    )

def button_irq(pin):
    global button_pressed
    button_pressed = True

async def read_uid(reader, attempts=READ_TRIES, delay_ms=READ_DELAY_MS) -> str:
    """
    Essaie jusqu’à 'attempts' fois de lire un UID via reader.read_passive_target().
    Renvoie l’UID en hex string (4 octets) ou None.
    """
    for _ in range(attempts):
        card = reader.read_passive_target(timeout=delay_ms)
        if card:
            return "".join("{:02x}".format(b) for b in card)
        await asyncio.sleep_ms(delay_ms)
    return None

def get_answers() -> dict:
    arr = config.get("answers", [])
    if not arr:
        return {}
    return arr[(current_set - 1) % len(arr)]

def check_answers(uids):
    """
    uids : liste de 3 hex strings ou None
    Met à jour les LEDs et renvoie True si tous corrects.
    """
    correct = get_answers()
    ok = True
    for i, uid in enumerate(uids):
        if uid is None:
            color = (255,165,0)    # orange
            ok = False
        elif uid == correct.get(("lieu","couleur","emotion")[i]):
            color = (0,255,0)      # vert
        else:
            color = (255,0,0)      # rouge
            ok = False
        leds[i][0] = scale_color(color)
        leds[i].write()
    return ok


# ──────────────────────────────────────────────────────────────────────────────
# Initialisation hardware
# ──────────────────────────────────────────────────────────────────────────────
def setup_hardware():
    global rdrs, leds, button

    # 1) SPI
    spi = SPI(SPI_ID, baudrate=SPI_BAUD, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    # 2) PN532 ×3
    for cs_pin, rst_pin in zip(CS_PINS, RST_PINS):
        cs  = Pin(cs_pin, Pin.OUT)
        rst = Pin(rst_pin, Pin.OUT)
        cs.on()
        rdr = pn532.PN532(spi, cs, irq=None, reset=rst, debug=False)
        rdr.SAM_configuration()
        rdrs.append(rdr)

    # 3) NeoPixels ×3
    for p in LED_PINS:
        led = neopixel.NeoPixel(Pin(p), 1)
        led[0] = (0,0,0)
        led.write()
        leds.append(led)

    # 4) Bouton
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq)

    print("✅ Hardware initialized.")


# ──────────────────────────────────────────────────────────────────────────────
# Boucle principale async
# ──────────────────────────────────────────────────────────────────────────────
async def async_main():
    global client, config, current_set, attempt_count, button_pressed

    setup_hardware()

    # Connexion Artineo
    client = ArtineoClient(module_id=3)
    client.start()
    try:
        config = await client.fetch_config()
    except Exception as e:
        print("⚠️ fetch_config failed:", e)
        config = {}

    # Buffer initial
    await client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set, "button_pressed": False
    })

    # Allume / éteint initial
    await asyncio.sleep(1)

    print("▶️ Entering main loop.")
    while True:
        # Lecture séquentielle sur les 3 lecteurs
        u1 = await read_uid(rdrs[0])
        u2 = await read_uid(rdrs[1])
        u3 = await read_uid(rdrs[2])
        print("Read UIDs:", u1, u2, u3)

        # Mise à jour buffer Artineo
        await client.set_buffer({
            "uid1": u1, "uid2": u2, "uid3": u3,
            "current_set": current_set,
            "button_pressed": button_pressed
        })

        if button_pressed:
            button_pressed = False
            start = ticks_ms()
            correct = check_answers([u1,u2,u3])
            attempt_count += 1

            if correct or attempt_count >= MAX_ATTEMPTS:
                current_set += 1
                attempt_count = 0

            await asyncio.sleep(COOLDOWN)
            # Mise à jour buffer post-validation
            await client.set_buffer({
                "uid1": u1, "uid2": u2, "uid3": u3,
                "current_set": current_set,
                "button_pressed": False
            })
            print("⏱ Validation took", ticks_diff(ticks_ms(), start), "ms")

        await asyncio.sleep_ms(50)


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("🛑 Program stopped by user")
