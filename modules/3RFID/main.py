# modules/3RFID/main.py

import uasyncio as asyncio
from machine import SPI, Pin
import neopixel
from utime import ticks_ms, ticks_diff

from ArtineoClientMicro import ArtineoClient
import pn532   # votre driver PN532 basé sur NFC_PN532_SPI

# —————————————————————————————————————————————————————————————————————————————
# Brochages & constantes
# —————————————————————————————————————————————————————————————————————————————
SPI_ID, SPI_BAUD = 2, 1_000_000
CS_PINS  = [5, 17, 26]
RST_PINS = [4, 16, 25]
LED_PINS = [15, 18, 19]
BUTTON_PIN = 14

INTENSITY     = 0.1
COOLDOWN      = 2
MAX_ATTEMPTS  = 3
READ_TRIES    = 15
READ_DELAY_MS = 50

# —————————————————————————————————————————————————————————————————————————————
# État global
# —————————————————————————————————————————————————————————————————————————————
rdrs           = []
leds           = []
button_pressed = False
current_set    = 1
attempt_count  = 0
config         = {}

def scale_color(c):
    return (int(c[0]*INTENSITY), int(c[1]*INTENSITY), int(c[2]*INTENSITY))

def button_irq(pin):
    global button_pressed
    button_pressed = True

async def read_uid(reader):
    """Lis l’UID en READ_TRIES essais."""
    for _ in range(READ_TRIES):
        uid = reader.read_passive_target(timeout=READ_DELAY_MS)
        if uid:
            return "".join("{:02x}".format(b) for b in uid)
        await asyncio.sleep_ms(READ_DELAY_MS)
    return None

def get_answers():
    arr = config.get("answers", [])
    return arr[(current_set-1) % len(arr)] if arr else {}

def check_answers(uids):
    correct = get_answers()
    keys = ("lieu", "couleur", "emotion")
    ok = True
    for i, uid in enumerate(uids):
        if uid is None:
            color = (255,165,0); ok = False
        elif uid == correct.get(keys[i]):
            color = (0,255,0)
        else:
            color = (255,0,0); ok = False
        leds[i][0] = scale_color(color)
        leds[i].write()
    return ok

def setup_hardware():
    print("[main] setup_hardware()")
    spi = SPI(SPI_ID, baudrate=SPI_BAUD, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    for cs_pin, rst_pin in zip(CS_PINS, RST_PINS):
        cs  = Pin(cs_pin, Pin.OUT); cs.on()
        rst = Pin(rst_pin, Pin.OUT)
        rdr = pn532.PN532(spi, cs, irq=None, reset=rst, debug=False)
        rdr.SAM_configuration()
        rdrs.append(rdr)

    for p in LED_PINS:
        led = neopixel.NeoPixel(Pin(p), 1)
        led[0] = (0,0,0); led.write()
        leds.append(led)

    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    # => Correction ici : handler et trigger en mots-clés,
    #    sinon on inverse handler/trigger et on passe un function comme int !
    button.irq(handler=button_irq, trigger=Pin.IRQ_FALLING)

    print("[main] Hardware initialized.")

async def async_main():
    global config, current_set, attempt_count, button_pressed

    print("[main] Starting async_main")
    setup_hardware()

    # 1) Wi-Fi & WS
    print("[main] Init ArtineoClient")
    client = ArtineoClient(
        module_id=3,
        host="192.168.0.166",   # ← IP de votre serveur
        port=8000,
        ssid="Bob_bricolo",
        password="bobbricolo"
    )
    await client.connect_ws()

    # 2) fetch_config()
    print("[main] fetch_config()…")
    config = await client.fetch_config()
    print("[main] Config loaded:", config)

    # 3) buffer initial
    print("[main] send initial buffer…")
    await client.set_buffer({
        "uid1": None,
        "uid2": None,
        "uid3": None,
        "current_set": current_set,
        "button_pressed": False
    })

    print("[main] Entering main loop.")
    while True:
        u1 = await read_uid(rdrs[0])
        u2 = await read_uid(rdrs[1])
        u3 = await read_uid(rdrs[2])
        print("[main] UIDs:", u1, u2, u3)

        # met à jour le buffer à chaque cycle
        await client.set_buffer({
            "uid1": u1,
            "uid2": u2,
            "uid3": u3,
            "current_set": current_set,
            "button_pressed": button_pressed
        })

        if button_pressed:
            button_pressed = False
            start = ticks_ms()
            correct = check_answers([u1, u2, u3])
            attempt_count += 1
            if correct or attempt_count >= MAX_ATTEMPTS:
                current_set += 1
                attempt_count = 0
            await asyncio.sleep(COOLDOWN)

        await asyncio.sleep_ms(50)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("[main] Stopped by user")
