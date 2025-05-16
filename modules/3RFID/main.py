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

# Ruban timer
TIMER_LED_PIN       = 21          # broche data du ruban
TIMER_LED_COUNT     = 5          # nombre de LEDs sur le ruban
TIMER_COLOR         = (0, 0, 255) # couleur RGB pour le timer
TIMER_DURATION      = 20          # durée limite en secondes du timer

# Intensité des LEDs
INTENSITY           = 0.1         # intensité pour tous les LEDs (0–1)

# Temps de pause après validation (si besoin)
COOLDOWN            = 2           # en secondes

MAX_ATTEMPTS        = 2
READ_TRIES          = 2
READ_DELAY_MS       = 50

# Activation des logs de debug
DEBUG_LOGS          = False
# —————————————————————————————————————————————————————————————————————————————

# —————————————————————————————————————————————————————————————————————————————
# État global
# —————————————————————————————————————————————————————————————————————————————
rdrs           = []        # lecteurs PN532
leds           = []        # LEDs de validation
timer_strip    = None      # ruban LEDs pour minuteur
button_pressed = False
current_set    = 1
attempt_count  = 0
config         = {}
_client        = None      # ArtineoClient instance
_timer_task    = None      # uasyncio.Task for timer
# —————————————————————————————————————————————————————————————————————————————

def log(*args, **kwargs):
    """Affiche des messages si DEBUG_LOGS est activé."""
    if DEBUG_LOGS:
        print(*args, **kwargs)

def scale_color(c):
    """Applique l'intensité globale (0.0–1.0)."""
    return (
        int(c[0] * INTENSITY),
        int(c[1] * INTENSITY),
        int(c[2] * INTENSITY),
    )

def button_irq(pin):
    global button_pressed
    button_pressed = True
    log("[main] Button pressed IRQ")

async def read_uid(reader):
    """Lit l’UID en READ_TRIES essais (passif)."""
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
    arr = config.get("answers", [])
    return arr[(current_set-1) % len(arr)] if arr else {}

def check_answers(uids):
    """Colorie leds 1/2/3 selon la validité des UIDs."""
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
        log(f"[main] LED {i+1} set to {color} (uid={uid})")
    return ok

def setup_hardware():
    """Initialise SPI, lecteurs PN532, LEDs, ruban timer et bouton."""
    global timer_strip

    log("[main] setup_hardware()")
    # SPI bus
    spi = SPI(SPI_ID, baudrate=SPI_BAUD, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    # Lecteurs PN532
    for cs_pin, rst_pin in zip(CS_PINS, RST_PINS):
        cs  = Pin(cs_pin, Pin.OUT); cs.on()
        rst = Pin(rst_pin, Pin.OUT)
        rdr = pn532.PN532(spi, cs, irq=None, reset=rst, debug=False)
        rdr.SAM_configuration()
        rdrs.append(rdr)
        log(f"[main] PN532 init on CS={cs_pin}, RST={rst_pin}")

    # LEDs de validation (1 pixel chacune)
    for p in LED_PINS:
        led = neopixel.NeoPixel(Pin(p), 1)
        led[0] = (0,0,0); led.write()
        leds.append(led)
        log(f"[main] Validation LED init on pin {p}")

    # Ruban timer
    timer_strip = neopixel.NeoPixel(Pin(TIMER_LED_PIN), TIMER_LED_COUNT)
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = (0,0,0)
    timer_strip.write()
    log(f"[main] Timer strip init: pin={TIMER_LED_PIN}, count={TIMER_LED_COUNT}")

    # Bouton avec IRQ
    btn = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    btn.irq(handler=button_irq, trigger=Pin.IRQ_FALLING)
    log(f"[main] Button IRQ on pin {BUTTON_PIN}")

    log("[main] Hardware initialized.")

async def timer_coroutine():
    """
    Minuteur visuel : efface progressivement le ruban sur TIMER_DURATION secondes,
    puis passe au set suivant.
    """
    log("[main] timer_coroutine started")
    step = TIMER_DURATION / TIMER_LED_COUNT
    # allumer tout le ruban
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = scale_color(TIMER_COLOR)
    timer_strip.write()
    log("[main] Timer strip all on")
    # extinction progressive
    for j in range(TIMER_LED_COUNT):
        idx = TIMER_LED_COUNT - 1 - j
        timer_strip[idx] = (0,0,0)
        timer_strip.write()
        await asyncio.sleep(step)
    log("[main] Timer expired, triggering next_set(timeout=True)")
    # temps écoulé → on passe au set suivant
    await next_set(timeout=True)

def reset_timer():
    """Annule l’ancien timer (si possible) et relance la coroutine du timer."""
    global _timer_task
    if _timer_task:
        try:
            _timer_task.cancel()
            log("[main] Previous timer task canceled")
        except:
            pass
    _timer_task = asyncio.create_task(timer_coroutine())
    log("[main] New timer task created")

async def next_set(timeout=False):
    """
    Passe au set suivant, reset attempts, met à jour le serveur
    et relance le timer.
    """
    global current_set, attempt_count, button_pressed
    attempt_count = 0
    button_pressed = False
    current_set += 1
    log(f"[main] Next set (#{current_set}), triggered by {'timeout' if timeout else 'manual'}")
    # update server buffer
    await _client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set,
        "button_pressed": False
    })
    log(f"[main] Buffer updated for set #{current_set}")
    # restart timer
    reset_timer()

async def async_main():
    global config, current_set, attempt_count, button_pressed, _client

    log("[main] Starting async_main")
    setup_hardware()

    # 1) Wi-Fi & WS
    _client = ArtineoClient(
        module_id=3,
        host="artineo.local",
        port=8000,
        ssid="Bob_bricolo",
        password="bobbricolo"
    )
    await _client.connect_ws()
    log("[main] WebSocket connected")

    # 2) Récupère la config
    config = await _client.fetch_config()
    log("[main] Config loaded:", config)

    # 3) Buffer initial
    await _client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set,
        "button_pressed": False
    })
    log(f"[main] Initial buffer sent for set #{current_set}")

    # 4) Démarre le timer pour le premier set
    reset_timer()

    log("[main] Entering main loop.")
    while True:
        # Lecture des 3 lecteurs
        u1 = await read_uid(rdrs[0])
        u2 = await read_uid(rdrs[1])
        u3 = await read_uid(rdrs[2])
        log("[main] UIDs:", u1, u2, u3)

        # Mise à jour du buffer
        await _client.set_buffer({
            "uid1": u1,
            "uid2": u2,
            "uid3": u3,
            "current_set": current_set,
            "button_pressed": button_pressed
        })

        if button_pressed:
            button_pressed = False
            start = ticks_ms()
            log("[main] Validation triggered manually")
            correct = check_answers([u1, u2, u3])
            attempt_count += 1
            log(f"[main] Attempt {attempt_count}, correct={correct}")
            if correct or attempt_count >= MAX_ATTEMPTS:
                # passage manuel
                await next_set(timeout=False)
            # Pause éventuelle indépendante du timer
            await asyncio.sleep(COOLDOWN)
            log(f"[main] Cooldown of {COOLDOWN}s completed")

        await asyncio.sleep_ms(50)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("Program stopped by user")
