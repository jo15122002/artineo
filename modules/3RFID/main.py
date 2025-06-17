# modules/3RFID/main.py

import neopixel
import uasyncio as asyncio
from machine import SPI, Pin
from utime import ticks_diff, ticks_ms

import pn532  # driver PN532 SPI
from ArtineoClientMicro import ArtineoClient

# —————————————————————————————————————————————————————————————————————————————
# Brochages & constantes
# —————————————————————————————————————————————————————————————————————————————
SPI_ID, SPI_BAUD    = 2, 1_000_000
CS_PINS             = [5, 17, 26]
RST_PINS            = [4, 16, 25]
LED_PINS            = [15, 18, 19]
BUTTON_PIN          = 14

TIMER_LED_PIN       = 21
TIMER_LED_COUNT     = 22
TIMER_COLOR         = (0, 0, 255)
TIMER_DURATION      = 60  # en secondes

PROGRESS_COLOR      = (0, 255, 0)
INTENSITY           = 0.1
COOLDOWN            = 2

MAX_ATTEMPTS        = 2
READ_TRIES          = 2
READ_DELAY_MS       = 50

DEBUG_LOGS          = True
# —————————————————————————————————————————————————————————————————————————————

# —————————————————————————————————————————————————————————————————————————————
# État global
# —————————————————————————————————————————————————————————————————————————————
rdrs           = []
leds           = []
timer_strip    = None
button_pressed = False
current_set    = 1
attempt_count  = 0
total_sets     = 1       # sera initialisé avec len(config["answers"])
config         = {}
_client        = None
_timer_task    = None
_timer_start   = 0       # timestamp du début du timer
# —————————————————————————————————————————————————————————————————————————————

def log(*args, **kwargs):
    if DEBUG_LOGS:
        print(*args, **kwargs)

def scale_color(c):
    return (
        int(c[0] * INTENSITY),
        int(c[1] * INTENSITY),
        int(c[2] * INTENSITY),
    )

def button_irq(pin):
    global button_pressed
    button_pressed = True
    log("[main] button pressed")

async def read_uid(reader):
    for _ in range(READ_TRIES):
        uid = reader.read_passive_target(timeout=READ_DELAY_MS)
        if uid:
            val = "".join("{:02x}".format(b) for b in uid)
            log(f"[main] read_uid → {val}")
            return val
        await asyncio.sleep_ms(READ_DELAY_MS)
    log("[main] read_uid → None")
    return None

def get_answers():
    answers = config.get("answers", [])
    idx = (current_set - 1) % len(answers) if answers else 0
    return answers[idx] if answers else {}

def check_answers(uids):
    correct = get_answers()
    keys = ("lieu", "couleur", "emotion")
    ok = True
    for i, uid in enumerate(uids):
        if uid is None:
            color = (255,165,0); ok = False
        elif uid.lower() == correct.get(keys[i], "").lower():
            color = (0,255,0)
        else:
            color = (255,0,0); ok = False
        leds[i][0] = scale_color(color)
        leds[i].write()
        log(f"[main] led {i+1} → {color}")
    return ok

def setup_hardware():
    global timer_strip
    log("[main] setup_hardware()")
    # strip
    timer_strip = neopixel.NeoPixel(Pin(TIMER_LED_PIN), TIMER_LED_COUNT)
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = (0,0,0)
    timer_strip.write()
    # SPI et PN532
    spi = SPI(SPI_ID, baudrate=SPI_BAUD, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()
    for cs_pin, rst_pin, led_pin in zip(CS_PINS, RST_PINS, LED_PINS):
        cs = Pin(cs_pin, Pin.OUT); cs.on()
        rst = Pin(rst_pin, Pin.OUT)
        rdr = pn532.PN532(spi, cs, irq=None, reset=rst, debug=False)
        rdr.SAM_configuration()
        rdrs.append(rdr)
        led = neopixel.NeoPixel(Pin(led_pin), 1)
        led[0] = scale_color((0,255,0))
        led.write()
        leds.append(led)
    btn = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    btn.irq(handler=button_irq, trigger=Pin.IRQ_FALLING)
    log("[main] hardware initialized")

def setProgressBar(percentage):
    pct = max(0, min(percentage, 100))
    lit = int((pct / 100) * TIMER_LED_COUNT)
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = scale_color(PROGRESS_COLOR) if i < lit else (0,0,0)
    timer_strip.write()
    log(f"[main] progress {pct}%")

def endStartAnimation():
    for led in leds:
        led[0] = (0,0,0); led.write()
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = (0,0,0)
    timer_strip.write()
    log("[main] start animation ended")

def format_timer():
    """
    Retourne le timer restant sous la forme "M:SS".
    """
    elapsed = ticks_diff(ticks_ms(), _timer_start)
    rem_ms = max(0, TIMER_DURATION * 1000 - elapsed)
    total_sec = rem_ms // 1000
    m = total_sec // 60
    s = total_sec % 60
    return "{}:{:02d}".format(m, s)

async def timer_coroutine():
    log("[main] timer start")
    step = TIMER_DURATION / TIMER_LED_COUNT
    # allume tout
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = scale_color(TIMER_COLOR)
    timer_strip.write()
    # éteint un à un
    for j in range(TIMER_LED_COUNT):
        idx = TIMER_LED_COUNT - 1 - j
        timer_strip[idx] = (0,0,0)
        timer_strip.write()
        await asyncio.sleep(step)
    log("[main] timer expired")
    await next_set(timeout=True)

def reset_timer():
    """
    Annule l'ancienne tâche, mémorise l'heure de départ,
    et relance le compte à rebours.
    """
    global _timer_task, _timer_start
    if _timer_task:
        try:
            _timer_task.cancel()
        except:
            pass
    _timer_start = ticks_ms()
    _timer_task = asyncio.create_task(timer_coroutine())
    log("[main] timer reset")

async def next_set(timeout=False):
    global current_set, attempt_count, button_pressed
    attempt_count = 0
    button_pressed = False
    current_set = current_set + 1 if current_set < total_sets else 1
    log(f"[main] next_set → {current_set} (by {'timeout' if timeout else 'manual'})")
    await _client.send_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set,
        "button_pressed": False,
        "timer": format_timer()
    })
    reset_timer()

async def async_main():
    global config, total_sets, _client, current_set, attempt_count, button_pressed

    log("[main] async_main start")
    setup_hardware()

    # startup animation
    setProgressBar(25)

    # —————— WebSocket Artineo ——————
    _client = ArtineoClient(
        module_id=3,
        host="artineo.local",
        port=8000,
        ssid="Bob_bricolo",
        password="bobbricolo"
    )
    # on lance les boucles WS
    await asyncio.sleep(0)
    asyncio.create_task(_client._ws_loop())
    asyncio.create_task(_client._ws_receiver())
    setProgressBar(50)

    # fetch config
    config = await _client.fetch_config()
    total_sets = len(config.get("answers", [])) or 1
    log(f"[main] total_sets = {total_sets}")
    setProgressBar(75)

    # initial buffer (timer démarré ensuite)
    await _client.send_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set,
        "button_pressed": False,
        "timer": "{}:{:02d}".format(TIMER_DURATION//60, TIMER_DURATION%60)
    })
    setProgressBar(100)
    await asyncio.sleep(1)

    endStartAnimation()
    reset_timer()

    log("[main] entering loop")
    
    while _client.varStart is False:
        log("[main] waiting for varStart to be True")
        await asyncio.sleep(1)
    
    while True:
        u1 = await read_uid(rdrs[0])
        u2 = await read_uid(rdrs[1])
        u3 = await read_uid(rdrs[2])
        log(f"[main] UIDs: {u1}, {u2}, {u3}")

        # envoi régulier du buffer AVEC le timer
        await _client.send_buffer({
            "uid1": u1,
            "uid2": u2,
            "uid3": u3,
            "current_set": current_set,
            "button_pressed": button_pressed,
            "timer": format_timer()
        })

        if button_pressed:
            button_pressed = False
            correct = check_answers([u1, u2, u3])
            attempt_count += 1
            await asyncio.sleep(COOLDOWN)

        await asyncio.sleep_ms(50)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("stopped by user")
