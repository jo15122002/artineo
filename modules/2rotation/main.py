# main.py -- ESP32 WROOM32 avec 3 KY-023, FPS récupéré depuis la config Artineo

import network
import uasyncio as asyncio
from machine import ADC, Pin
from utime import ticks_ms, ticks_diff
from ArtineoClientMicro import ArtineoClient

# ————————————————
# 1) Wi-Fi et Artineo
# ————————————————
SSID      = "Bob_bricolo"
PASSWORD  = "bobbricolo"
HOST      = "artineo.local"
PORT      = 8000
MODULE_ID = 2

# ————————————————
# 2) ADC pour chaque KY-023 (VRx)
# ————————————————
adcX = ADC(Pin(34))
adcX.width(ADC.WIDTH_12BIT)
adcX.atten(ADC.ATTN_11DB)

adcY = ADC(Pin(35))
adcY.width(ADC.WIDTH_12BIT)
adcY.atten(ADC.ATTN_11DB)

adcZ = ADC(Pin(32))
adcZ.width(ADC.WIDTH_12BIT)
adcZ.atten(ADC.ATTN_11DB)

def normalize(raw):
    # raw ∈ [0..4095] → [-1.0 .. +1.0]
    return (raw / 2047.5) - 1.0

# ————————————————
# 3) Tâche principale asynchrone
# ————————————————
async def async_main():
    print("Démarrage module KY-023 → Artineo rotation…")

    # a) Connexion Wi-Fi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(SSID, PASSWORD)
        t0 = ticks_ms()
        while not sta.isconnected() and ticks_diff(ticks_ms(), t0) < 15000:
            await asyncio.sleep_ms(500)
    if not sta.isconnected():
        raise OSError("Impossible de se connecter au Wi-Fi")
    print("[WiFi] Connecté :", sta.ifconfig())

    # b) Initialisation du client Artineo et WS
    client = ArtineoClient(
        module_id=MODULE_ID,
        host=HOST,
        port=PORT,
        ssid=SSID,
        password=PASSWORD
    )
    await client.connect_ws()
    print("[Artineo] WebSocket connecté")

    # c) Récupérer la config distante pour obtenir 'fps'
    #    Si 'fps' n’existe pas, on prend 24 par défaut.
    try:
        cfg = await client.fetch_config()  # retourne un dict ou {}
    except Exception as e:
        print("[Artineo] Erreur fetch_config :", e)
        cfg = {}
    raw_fps = cfg.get("fps")
    if isinstance(raw_fps, (int, float)) and raw_fps > 0:
        fps = int(raw_fps)
    else:
        fps = 15
    interval_ms = int(1000 / fps)
    print(f"[Config] FPS = {fps}, interval = {interval_ms} ms")

    # d) Tâche périodique lecture KY-023 + envoi buffer
    async def joystick_task():
        while True:
            raw_x = adcX.read()
            raw_y = adcY.read()
            raw_z = adcZ.read()

            vx = normalize(raw_x)
            vy = normalize(raw_y)
            vz = normalize(raw_z)

            buf = {"rotX": vx, "rotY": vy, "rotZ": vz}
            try:
                await client.set_buffer(buf)
            except Exception as e:
                print("[Artineo] Erreur set_buffer :", e)
            await asyncio.sleep_ms(interval_ms)

    asyncio.create_task(joystick_task())

    # e) Boucle vide pour garder le programme actif
    while True:
        await asyncio.sleep(1)

# ————————————————
# 4) Démarrage uasyncio
# ————————————————
try:
    asyncio.run(async_main())
except KeyboardInterrupt:
    print("Arrêt manuel")
