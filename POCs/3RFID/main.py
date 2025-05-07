# main.py

import neopixel
import uasyncio as asyncio
import ujson
from machine import SPI, Pin
from utime import ticks_diff, ticks_ms

import mfrc522
from ArtineoClient import ArtineoClient

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────
INTENSITY     = 0.1      # LED brightness (0…1)
COOLDOWN      = 2        # seconds between validations
MAX_ATTEMPTS  = 3        # max tries per set
READ_TRIES    = 15       # RFID read retries per cycle
READ_DELAY_MS = 50       # ms between retries
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# Globals (hardware + state)
# ──────────────────────────────────────────────────────────────────────────────
rdr1 = rdr2 = rdr3 = None
led1 = led2 = led3 = None
button = None

button_pressed = False
current_set    = 1
attempt_count  = 0

client = None
config = {}

def scale_color(col):
    return (
        int(col[0] * INTENSITY),
        int(col[1] * INTENSITY),
        int(col[2] * INTENSITY),
    )

def button_irq(pin):
    global button_pressed
    button_pressed = True

def setup_hardware():
    """Initialise SPI, les 3 lecteurs RFID, LEDs et bouton (une fois)."""
    global rdr1, rdr2, rdr3, led1, led2, led3, button

    spi = SPI(2, baudrate=2_500_000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4,  gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    for rdr in (rdr1, rdr2, rdr3):
        rdr.init()
        rdr.antenna_on()
        rdr.set_gain(rdr.MAX_GAIN)

    led1 = neopixel.NeoPixel(Pin(15), 1)
    led2 = neopixel.NeoPixel(Pin(18), 1)
    led3 = neopixel.NeoPixel(Pin(19), 1)
    for led in (led1, led2, led3):
        led[0] = (0, 0, 0)
        led.write()

    button = Pin(14, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq)

    print("✅ Hardware initialized.")

async def read_uid(reader,
                   attempts: int = READ_TRIES,
                   delay_ms: int = READ_DELAY_MS) -> str:
    """
    Essaie jusqu'à 'attempts' fois :
      - reader.init() + antenna_on()
      - reader.request(REQLDL) (on ignore son statut)
      - reader.anticoll(); si statut OK et raw len>=4, on lève l'uid
      - sinon on attend delay_ms et on recommence
    """
    uid = None
    for i in range(attempts):
        reader.init()
        reader.antenna_on()

        # On lance la requête mais on ne dépend plus de bits==16
        _stat_req, _bits = reader.request(reader.REQIDL)
        # On fait l'anticollision quoi qu'il arrive
        stat_ac, raw = reader.anticoll()
        print(f"[RFID] try {i+1}/{attempts} anticoll status={stat_ac} raw={bytes(raw)}")
        # raw est un bytearray de longueur 5 : UID[0..3] + bcc
        if stat_ac == reader.OK and len(raw) >= 4:
            uid = "".join("{:02x}".format(x) for x in raw[:4])
            print(f"[RFID] → UID read: {uid}")
            break

        # On laisse un petit temps
        await asyncio.sleep_ms(delay_ms)

    return uid

def get_answers() -> dict:
    arr = config.get("answers", [])
    if not arr:
        return {}
    return arr[(current_set - 1) % len(arr)]

def check_answers(u1, u2, u3) -> bool:
    correct = get_answers()
    ok = True

    # lieu
    if u1 is None:
        led1[0] = scale_color((255,165,0)); ok = False
    elif u1 == correct.get("lieu"):
        led1[0] = scale_color((0,255,0))
    else:
        led1[0] = scale_color((255,0,0)); ok = False
    led1.write()

    # couleur
    if u2 is None:
        led2[0] = scale_color((255,165,0)); ok = False
    elif u2 == correct.get("couleur"):
        led2[0] = scale_color((0,255,0))
    else:
        led2[0] = scale_color((255,0,0)); ok = False
    led2.write()

    # emotion
    if u3 is None:
        led3[0] = scale_color((255,165,0)); ok = False
    elif u3 == correct.get("emotion"):
        led3[0] = scale_color((0,255,0))
    else:
        led3[0] = scale_color((255,0,0)); ok = False
    led3.write()

    return ok

async def async_main():
    global client, config, current_set, attempt_count, button_pressed

    setup_hardware()

    # 2) Create ArtineoClient & WebSocket
    client = ArtineoClient(
        module_id=3,
        host="192.168.0.180", port=8000,
        ssid="Bob_bricolo", password="bobbricolo"
    )
    ws = await client.connect_ws()
    if ws:
        try:
            config = client.fetch_config()
        except Exception as e:
            print("⚠️ fetch_config failed:", e)
            config = {}
    else:
        print("⚠️ No WS, fallback to local config.")
        config = {}

    # Buffer initial
    await client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set, "button_pressed": False
    })

    # Éteindre LEDs, petit délai
    for led in (led1, led2, led3):
        led[0] = (0,0,0); led.write()
    await asyncio.sleep(1)

    print("▶️ Entering main loop.")
    while True:
        u1 = await read_uid(rdr1)
        u2 = await read_uid(rdr2)
        u3 = await read_uid(rdr3)
        print("Read UIDs:", u1, u2, u3)

        # Envoi systématique
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
            correct = check_answers(u1, u2, u3)
            attempt_count += 1

            if correct or attempt_count >= MAX_ATTEMPTS:
                current_set += 1
                attempt_count = 0
                print("→ Moving to set", current_set)

            await asyncio.sleep(COOLDOWN)
            await client.set_buffer({
                "uid1": u1,
                "uid2": u2,
                "uid3": u3,
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
