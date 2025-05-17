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

# Ruban timer (et barre de progression)
TIMER_LED_PIN       = 21          # broche data du ruban
TIMER_LED_COUNT     = 10          # nombre de LEDs sur le ruban
TIMER_COLOR         = (0, 0, 255) # couleur RGB pour le timer
TIMER_DURATION      = 20          # durée limite en secondes du timer
PROGRESS_COLOR      = (0, 255, 0) # couleur RGB pour la barre de progression

# Intensité des LEDs
INTENSITY           = 0.1         # (0.0–1.0)

# Pause après validation (indépendante du timer)
COOLDOWN            = 2           # en secondes

MAX_ATTEMPTS        = 2
READ_TRIES          = 2
READ_DELAY_MS       = 50

# Active les logs de debug
DEBUG_LOGS          = False
# —————————————————————————————————————————————————————————————————————————————

# —————————————————————————————————————————————————————————————————————————————
# État global
# —————————————————————————————————————————————————————————————————————————————
rdrs           = []        # lecteurs PN532
leds           = []        # LEDs de validation
timer_strip    = None      # ruban LEDs pour minuteur/progress
button_pressed = False
current_set    = 1
attempt_count  = 0
config         = {}
_client        = None      # instance ArtineoClient
_timer_task    = None      # tâche uasyncio du timer
# —————————————————————————————————————————————————————————————————————————————

def log(*args, **kwargs):
    if DEBUG_LOGS:
        print(*args, **kwargs)

def scale_color(c):
    """Retourne la couleur c multipliée par INTENSITY."""
    return (
        int(c[0] * INTENSITY),
        int(c[1] * INTENSITY),
        int(c[2] * INTENSITY),
    )

def button_irq(pin):
    global button_pressed
    button_pressed = True
    log("[main] Button pressed")

async def read_uid(reader):
    """Tente READ_TRIES lectures passives, retourne l'UID hex ou None."""
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
    """Colorie les LEDs de validation selon la validité des UIDs."""
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
        log(f"[main] LED {i+1} → {color} (uid={uid})")
    return ok

def setup_hardware():
    """Initialise SPI, PN532, LEDs de validation, strip timer et bouton."""
    global timer_strip

    log("[main] setup_hardware()")
    
    # Ruban timer/progress bar
    timer_strip = neopixel.NeoPixel(Pin(TIMER_LED_PIN), TIMER_LED_COUNT)
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = (0,0,0)
    timer_strip.write()
    log(f"[main] Timer strip init: pin={TIMER_LED_PIN}, count={TIMER_LED_COUNT}")
    setProgressBar(10)
    
    # SPI
    spi = SPI(SPI_ID, baudrate=SPI_BAUD, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    # Lecteurs PN532 + LEDs de validation allumées au vert
    for idx, (cs_pin, rst_pin, led_pin) in enumerate(zip(CS_PINS, RST_PINS, LED_PINS)):
        cs  = Pin(cs_pin, Pin.OUT); cs.on()
        rst = Pin(rst_pin, Pin.OUT)
        rdr = pn532.PN532(spi, cs, irq=None, reset=rst, debug=False)
        rdr.SAM_configuration()
        rdrs.append(rdr)
        # init et allume la LED de validation associée
        led = neopixel.NeoPixel(Pin(led_pin), 1)
        led[0] = scale_color((0,255,0))
        led.write()
        leds.append(led)
        log(f"[main] Reader #{idx+1} init → LED on pin {led_pin} lit")

    setProgressBar(30)

    # Bouton avec IRQ
    btn = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    btn.irq(handler=button_irq, trigger=Pin.IRQ_FALLING)
    log(f"[main] Button IRQ set on pin {BUTTON_PIN}")

    setProgressBar(40)

    log("[main] Hardware initialized.")

def setProgressBar(percentage):
    """
    Allume la barre de progression en fonction de percentage (0–100).
    """
    pct = max(0, min(percentage, 100))
    lit = int((pct / 100) * TIMER_LED_COUNT)
    for i in range(TIMER_LED_COUNT):
        if i < lit:
            timer_strip[i] = scale_color(PROGRESS_COLOR)
        else:
            timer_strip[i] = (0,0,0)
    timer_strip.write()
    log(f"[main] ProgressBar set to {pct}% ({lit}/{TIMER_LED_COUNT})")

def endStartAnimation():
    """
    Éteint toutes les LEDs de validation et la barre de progression.
    À appeler juste avant la boucle principale de lecture.
    """
    # LEDs validation off
    for i, led in enumerate(leds):
        led[0] = (0,0,0)
        led.write()
        log(f"[main] LED {i+1} off")
    # timer strip off
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = (0,0,0)
    timer_strip.write()
    log("[main] Timer strip cleared")

async def timer_coroutine():
    """
    Efface progressivement le ruban sur TIMER_DURATION secondes,
    puis passe au set suivant.
    """
    log("[main] timer_coroutine start")
    step = TIMER_DURATION / TIMER_LED_COUNT
    # allumé complet
    for i in range(TIMER_LED_COUNT):
        timer_strip[i] = scale_color(TIMER_COLOR)
    timer_strip.write()
    # extinction progressive
    for j in range(TIMER_LED_COUNT):
        idx = TIMER_LED_COUNT - 1 - j
        timer_strip[idx] = (0,0,0)
        timer_strip.write()
        await asyncio.sleep(step)
    log("[main] timer expired → next_set(timeout=True)")
    await next_set(timeout=True)

def reset_timer():
    """Réinitialise la tâche timer."""
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
    Passe au set suivant, reset attempts, met à jour le serveur,
    relance le timer.
    """
    global current_set, attempt_count, button_pressed
    attempt_count = 0
    button_pressed = False
    current_set += 1
    log(f"[main] Next set #{current_set}, by {'timeout' if timeout else 'manual'}")
    await _client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set,
        "button_pressed": False
    })
    reset_timer()

async def async_main():
    global config, _client, attempt_count, current_set, button_pressed

    log("[main] Starting async_main")
    setup_hardware()
    
    setProgressBar(50)

    # 1) Wi-Fi & WS
    _client = ArtineoClient(
        module_id=3,
        host="artineo.local",
        port=8000,
        ssid="Bob_bricolo",
        password="bobbricolo"
    )
    await _client.connect_ws()
    
    setProgressBar(60)

    # 2) Fetch config
    config = await _client.fetch_config()
    log("[main] Config loaded:", config)
    
    setProgressBar(80)

    # 3) Initial buffer
    await _client.set_buffer({
        "uid1": None, "uid2": None, "uid3": None,
        "current_set": current_set,
        "button_pressed": False
    })
    
    setProgressBar(100)
    
    await asyncio.sleep(1)

    # 4) Fin de l’animation de démarrage puis start timer
    endStartAnimation()
    reset_timer()

    log("[main] Entering main loop.")
    while True:
        u1 = await read_uid(rdrs[0])
        u2 = await read_uid(rdrs[1])
        u3 = await read_uid(rdrs[2])
        log("[main] UIDs:", u1, u2, u3)

        await _client.set_buffer({
            "uid1": u1, "uid2": u2, "uid3": u3,
            "current_set": current_set,
            "button_pressed": button_pressed
        })

        if button_pressed:
            button_pressed = False
            start = ticks_ms()
            log("[main] Manual validation")
            correct = check_answers([u1, u2, u3])
            attempt_count += 1
            log(f"[main] Attempt {attempt_count}, correct={correct}")
            if correct or attempt_count >= MAX_ATTEMPTS:
                await next_set(timeout=False)
            await asyncio.sleep(COOLDOWN)
            log(f"[main] Cooldown {COOLDOWN}s done")

        await asyncio.sleep_ms(50)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("Program stopped by user")
