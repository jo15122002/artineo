# main.py

import neopixel
import uasyncio as asyncio
import ujson
from machine import SPI, Pin
from utime import sleep, ticks_diff, ticks_ms

import mfrc522
from ArtineoClient import ArtineoClient

# Constants
INTENSITY = 0.1             # 0 = off, 1 = full brightness
COOLDOWN_SECONDS = 2        # seconds between attempts
MAX_ATTEMPTS = 3            # attempts per set

# Globals
rdr1 = rdr2 = rdr3 = None
led1 = led2 = led3 = None
button = None

button_pressed = False
current_set = 1
attempt_count = 0
last_uid1 = last_uid2 = last_uid3 = None

client = None
config = {}

def scale_color(color):
    """
    Scale an (r,g,b) tuple by INTENSITY.
    """
    return (
        int(color[0] * INTENSITY),
        int(color[1] * INTENSITY),
        int(color[2] * INTENSITY),
    )

def button_irq_handler(pin):
    """
    IRQ handler: set the global flag when the button is pressed.
    """
    global button_pressed
    button_pressed = True

def setup_hardware():
    """
    Synchronous hardware initialization:
      - SPI + three MFRC522 readers
      - WS2812 LEDs
      - button with IRQ
    """
    global rdr1, rdr2, rdr3, led1, led2, led3, button

    # SPI bus on VSPI (SPI(2)), pins may be adjusted
    spi = SPI(2, baudrate=2_500_000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(23), miso=Pin(13))
    spi.init()

    # RFID readers
    rdr1 = mfrc522.MFRC522(spi=spi, gpioRst=4,  gpioCs=5)
    rdr2 = mfrc522.MFRC522(spi=spi, gpioRst=16, gpioCs=17)
    rdr3 = mfrc522.MFRC522(spi=spi, gpioRst=25, gpioCs=26)
    for rdr in (rdr1, rdr2, rdr3):
        rdr.init()
        rdr.set_gain(rdr.MAX_GAIN)

    # WS2812 LEDs
    led1 = neopixel.NeoPixel(Pin(15), 1)
    led2 = neopixel.NeoPixel(Pin(18), 1)
    led3 = neopixel.NeoPixel(Pin(19), 1)
    for led in (led1, led2, led3):
        led[0] = (0, 0, 0)
        led.write()

    # Button on GPIO14, pull-up, falling edge IRQ
    button = Pin(14, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq_handler)

    print("Hardware setup complete.")

def read_uid(reader, attempts=2):
    """
    Tente de lire un UID depuis 'reader' en effectuant un nombre fixe d'essais.
    Après la lecture, le tag est désactivé (reset, halt et stop_crypto1) pour libérer le lecteur.
    
    :param reader: Instance du lecteur RFID.
    :param attempts: Nombre d'essais à effectuer.
    :return: L'UID lu sous forme de chaîne hexadécimale ou None si aucune lecture n'a réussi.
    """
    reader.init()
    uid = None
    for _ in range(attempts):
        stat, tag_type = reader.request(reader.REQIDL)
        if stat == reader.OK:
            stat, raw_uid = reader.anticoll()
            if stat == reader.OK:
                uid = "".join("{:02x}".format(x) for x in raw_uid)
                break
        sleep(0.01)
    reader.reset()
    reader.halt_a()
    reader.stop_crypto1()
    return uid

def get_answers():
    """
    Return the correct-answer dict for the current_set from `config`.
    """
    # assume config["answers"] is a list of dicts
    answers = config.get("answers", [])
    # wrap-around or fallback to first set
    idx = (current_set - 1) % len(answers) if answers else 0
    return answers[idx]

def check_answers(uid1, uid2, uid3):
    """
    Compare the three UIDs to the correct answers for current_set,
    update led1/led2/led3 accordingly, and return True iff all correct.
    """
    correct = get_answers()
    print(f"Set #{current_set}:", correct)
    print("UIDs:", uid1, uid2, uid3)
    print("correct:", correct["lieu"], correct["couleur"], correct["emotion"])
    all_ok = True

    # Lieu (reader 1)
    if uid1 is None:
        led1[0] = scale_color((255, 165, 0))
        print("Lecteur 1: aucune carte")
        all_ok = False
    elif uid1 == correct["lieu"]:
        led1[0] = scale_color((0, 255, 0))
        print("Lecteur 1: correct")
    else:
        led1[0] = scale_color((255, 0, 0))
        print(f"Lecteur 1: incorrect (attendu {correct['lieu']}, reçu {uid1})")
        all_ok = False
    led1.write()

    # Couleur (reader 2)
    if uid2 is None:
        led2[0] = scale_color((255, 165, 0))
        print("Lecteur 2: aucune carte")
        all_ok = False
    elif uid2 == correct["couleur"]:
        led2[0] = scale_color((0, 255, 0))
        print("Lecteur 2: correct")
    else:
        led2[0] = scale_color((255, 0, 0))
        print(f"Lecteur 2: incorrect (attendu {correct['couleur']}, reçu {uid2})")
        all_ok = False
    led2.write()

    # Émotion (reader 3)
    if uid3 is None:
        led3[0] = scale_color((255, 165, 0))
        print("Lecteur 3: aucune carte")
        all_ok = False
    elif uid3 == correct["emotion"]:
        led3[0] = scale_color((0, 255, 0))
        print("Lecteur 3: correct")
    else:
        led3[0] = scale_color((255, 0, 0))
        print(f"Lecteur 3: incorrect (attendu {correct['emotion']}, reçu {uid3})")
        all_ok = False
    led3.write()

    if all_ok:
        print("Toutes les réponses sont correctes!")
    else:
        print("Certaines réponses sont incorrectes.")
    return all_ok

async def async_main():
    global client, config, current_set, attempt_count, last_uid1, last_uid2, last_uid3

    # 1) Hardware init
    setup_hardware()

    # 2) Create ArtineoClient & WebSocket
    client = ArtineoClient(module_id=3, host="192.168.0.180", port=8000, ssid="Bob_bricolo", password="bobbricolo")
    ws = await client.connect_ws()
    if ws is None:
        print("⚠️ Aucune WS, on utilisera la configuration locale par défaut.")
        config = {}
    else:
        print("Connecté au serveur WebSocket.")
        try:
            config = client.fetch_config()
        except OSError as e:
            print("⚠️ Impossible de récupérer la config:", e)
            config = {}

    # 4) Push initial empty buffer
    await client.set_buffer({
        "uid1": None,
        "uid2": None,
        "uid3": None,
        "current_set": current_set
    })

    print("Async setup done. Entering main loop.")

    # Main loop: poll RFID constantly, handle button presses
    while True:
        # 4a) Always keep UI updated: read each tag once
        uid1 = read_uid(rdr1, attempts=1)
        uid2 = read_uid(rdr2, attempts=1)
        uid3 = read_uid(rdr3, attempts=1)
        
        print(f"UIDs: {uid1}, {uid2}, {uid3}")

        # If UIDs changed, send update
        if (uid1, uid2, uid3) != (last_uid1, last_uid2, last_uid3):
            last_uid1, last_uid2, last_uid3 = uid1, uid2, uid3
            await client.set_buffer({
                "uid1": uid1,
                "uid2": uid2,
                "uid3": uid3,
                "current_set": current_set
            })
            print("UIDs updated:", uid1, uid2, uid3)

        # 4b) On button press, evaluate answers
        if button_pressed:
            # reset flag
            globals()['button_pressed'] = False

            start = ticks_ms()
            print(f"Tentative {attempt_count+1} pour set #{current_set}")

            correct = check_answers(uid1, uid2, uid3)
            attempt_count += 1

            # advance set if correct or max attempts reached
            if correct or attempt_count >= MAX_ATTEMPTS:
                if correct:
                    print(f"Réussi en {attempt_count} essai(s).")
                else:
                    print("Max essais atteint, passage au set suivant.")
                current_set += 1
                attempt_count = 0
                print("Nouveau set:", get_answers())

            # cooldown
            print(f"Cooldown {COOLDOWN_SECONDS}s…")
            await asyncio.sleep(COOLDOWN_SECONDS)

            elapsed = ticks_diff(ticks_ms(), start)
            print(f"Temps essai: {elapsed} ms")

        # short sleep to yield
        await asyncio.sleep_ms(50)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("Arrêt du programme")
