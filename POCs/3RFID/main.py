# main.py

import neopixel
import uasyncio as asyncio
import ujson
from machine import SPI, Pin
from utime import ticks_diff, ticks_ms

import mfrc522
from ArtineoClient import ArtineoClient

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
INTENSITY      = 0.1      # LED brightness (0…1)
COOLDOWN       = 2        # seconds between validations
MAX_ATTEMPTS   = 3        # max tries per set
READ_TRIES     = 10       # RFID read retries per cycle
READ_DELAY_MS  = 50       # ms between retries
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

# will hold the last successfully read UIDs
last_good_uids = [None, None, None]

client = None
config = {}

def scale_color(col):
    """Scale an (r,g,b) tuple by INTENSITY."""
    return (int(col[0]*INTENSITY),
            int(col[1]*INTENSITY),
            int(col[2]*INTENSITY))

def button_irq(pin):
    """IRQ handler for the button."""
    global button_pressed
    button_pressed = True

def setup_hardware():
    """Initialize SPI, RFID readers, WS2812 LEDs, and button—only once."""
    global rdr1, rdr2, rdr3, led1, led2, led3, button

    # SPI bus
    spi = SPI(2, baudrate=2_500_000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    # Three MFRC522 readers
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4,  gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    for rdr in (rdr1, rdr2, rdr3):
        rdr.init()
        rdr.antenna_on()
        rdr.set_gain(rdr.MAX_GAIN)

    # Three WS2812 LEDs (1 pixel each)
    led1 = neopixel.NeoPixel(Pin(15), 1)
    led2 = neopixel.NeoPixel(Pin(18), 1)
    led3 = neopixel.NeoPixel(Pin(19), 1)
    for led in (led1, led2, led3):
        led[0] = (0,0,0)
        led.write()

    # Button on GPIO14, pull-up, falling-edge IRQ
    button = Pin(14, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq)

    print("✅ Hardware initialized.")

async def read_uid(reader,
                   attempts: int = READ_TRIES,
                   delay_ms: int = READ_DELAY_MS) -> str:
    """
    Try to read an UID up to 'attempts' times, waiting 'delay_ms' between.
    Uses REQIDL so card remains in field, without halting.
    """
    reader.antenna_on()
    uid = None
    for _ in range(attempts):
        stat, _ = reader.request(reader.REQIDL)
        if stat == reader.OK:
            stat, raw = reader.anticoll()
            if stat == reader.OK:
                uid = "".join("{:02x}".format(x) for x in raw)
                break
        await asyncio.sleep_ms(delay_ms)
    return uid

def get_answers() -> dict:
    """Return the correct-answer dict for current_set."""
    arr = config.get("answers", [])
    if not arr:
        return {}
    idx = (current_set - 1) % len(arr)
    return arr[idx]

def check_answers(u1, u2, u3) -> bool:
    """Compare UIDs to answers, update LEDs, return True if all correct."""
    correct = get_answers()
    ok = True

    # Reader1 → 'lieu'
    if u1 is None:
        led1[0] = scale_color((255,165,0))
        ok = False
    elif u1 == correct.get("lieu"):
        led1[0] = scale_color((0,255,0))
    else:
        led1[0] = scale_color((255,0,0))
        ok = False
    led1.write()

    # Reader2 → 'couleur'
    if u2 is None:
        led2[0] = scale_color((255,165,0))
        ok = False
    elif u2 == correct.get("couleur"):
        led2[0] = scale_color((0,255,0))
    else:
        led2[0] = scale_color((255,0,0))
        ok = False
    led2.write()

    # Reader3 → 'emotion'
    if u3 is None:
        led3[0] = scale_color((255,165,0))
        ok = False
    elif u3 == correct.get("emotion"):
        led3[0] = scale_color((0,255,0))
    else:
        led3[0] = scale_color((255,0,0))
        ok = False
    led3.write()

    return ok

async def async_main():
    global client, config, current_set, attempt_count, button_pressed, last_good_uids

    # 1) Hardware init (once)
    setup_hardware()

    # 2) Connect WebSocket & fetch config
    client = ArtineoClient(module_id=3,
                           host="192.168.0.180", port=8000,
                           ssid="Bob_bricolo", password="bobbricolo")
    ws = await client.connect_ws()
    if ws:
        try:
            config = client.fetch_config()
        except Exception as e:
            print("⚠️ fetch_config failed:", e)
            config = {}
    else:
        print("⚠️ No WS, using local config fallback.")
        config = {}

    # 3) Initial empty buffer
    await client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set, "button_pressed": False
    })

    # 4) Turn off LEDs & pause briefly
    for led in (led1, led2, led3):
        led[0] = (0,0,0); led.write()
    await asyncio.sleep(1)

    print("▶️ Entering main loop.")
    while True:
        # 5a) Read each tag with persistence
        u1 = await read_uid(rdr1)
        u2 = await read_uid(rdr2)
        u3 = await read_uid(rdr3)
        
        print("⏱ Read UIDs:", u1, u2, u3)

        # If we got a new UID, update stored; else keep last
        last_good_uids[0] = u1 or last_good_uids[0]
        last_good_uids[1] = u2 or last_good_uids[1]
        last_good_uids[2] = u3 or last_good_uids[2]

        # Use persistent UIDs
        pu1, pu2, pu3 = last_good_uids

        # 5b) Send buffer on any change
        if (pu1,pu2,pu3,button_pressed) != (last_good_uids[0], last_good_uids[1], last_good_uids[2], False):
            await client.set_buffer({
                "uid1": pu1, "uid2": pu2, "uid3": pu3,
                "current_set": current_set,
                "button_pressed": button_pressed
            })

        # 5c) On button press → validate
        if button_pressed:
            button_pressed = False
            start = ticks_ms()
            correct = check_answers(pu1, pu2, pu3)
            attempt_count += 1

            if correct or attempt_count >= MAX_ATTEMPTS:
                current_set += 1
                attempt_count = 0
                # reset persistence for next set
                last_good_uids = [None, None, None]
                print("→ Moving to set", current_set)

            # cooldown and reset button flag in buffer
            await asyncio.sleep(COOLDOWN)
            await client.set_buffer({
                "uid1": pu1, "uid2": pu2, "uid3": pu3,
                "current_set": current_set,
                "button_pressed": False
            })
            print("⏱ Validation took", ticks_diff(ticks_ms(), start), "ms")

        # 5d) Yield to event loop
        await asyncio.sleep_ms(50)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("🛑 Program stopped by user")
