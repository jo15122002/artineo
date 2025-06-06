# modules/2rotation/main.py -- ESP32 WROOM32 avec 3 KY-023 → Artineo rotation

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
HOST      = "artineo.local"    # Remplacez par l’adresse correcte de votre serveur
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

# ——— Filtrage bruit (moyenne glissante) ———
USE_SIMPLE_AVG = True
prev_x = 0.0
prev_y = 0.0
prev_z = 0.0
ALPHA = 0.2   # Coefficient de la moyenne glissante

# ——— Accumulateur de rotation (logique incrémentation) ———
rotX_acc = 0.0
rotY_acc = 0.0
rotZ_acc = 0.0

# ————————————————
# 3) Tâche principale asynchrone
# ————————————————
async def async_main():
    global prev_x, prev_y, prev_z
    global rotX_acc, rotY_acc, rotZ_acc

    print("Démarrage module KY-023 → Artineo rotation…")

    # a) Connexion Wi-Fi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(SSID, PASSWORD)
        t0 = ticks_ms()
        while not sta.isconnected() and ticks_diff(ticks_ms(), t0) < 15_000:
            await asyncio.sleep_ms(500)
    if not sta.isconnected():
        raise OSError("Impossible de se connecter au Wi-Fi")
    print("[WiFi] Connecté :", sta.ifconfig())

    # b) Initialisation du client Artineo (tâche WS en arrière-plan)
    client = ArtineoClient(
        module_id=MODULE_ID,
        host=HOST,
        port=PORT,
        ssid=SSID,
        password=PASSWORD
    )
    print("[Artineo] Tâche WS lancée en arrière-plan")

    # c) On fixe un FPS = 15
    fps = 15
    interval_ms = int(1000 / fps)
    print(f"[Config] FPS = {fps}, interval = {interval_ms} ms")

    # d) Tâche périodique lecture KY-023 → filtre bruit → incrémente rotation → envoi
    async def joystick_task():
        global prev_x, prev_y, prev_z
        global rotX_acc, rotY_acc, rotZ_acc

        while True:
            # 1) Lecture brute
            raw_x = adcX.read()
            raw_y = adcY.read()
            raw_z = adcZ.read()

            vx = normalize(raw_x)
            vy = normalize(raw_y)
            vz = normalize(raw_z)

            # 2) Filtrage bruit par moyenne glissante
            if USE_SIMPLE_AVG:
                vx = ALPHA * vx + (1 - ALPHA) * prev_x
                vy = ALPHA * vy + (1 - ALPHA) * prev_y
                vz = ALPHA * vz + (1 - ALPHA) * prev_z
                prev_x, prev_y, prev_z = vx, vy, vz

            # 3) Incrémentation de la rotation
            #    On considère vx,vy,vz comme des vitesses angulaires normalisées [-1..+1] rad/s
            #    dt en secondes = interval_ms / 1000
            dt = interval_ms / 1000.0
            rotX_acc += vx * dt
            rotY_acc += vy * dt
            rotZ_acc += vz * dt

            # 4) Envoi via ArtineoClient
            buf = {
                "rotX": rotX_acc,
                "rotY": rotY_acc,
                "rotZ": rotZ_acc
            }
            await client.send_buffer(buf)

            # 5) Pause jusqu’à la prochaine itération
            await asyncio.sleep_ms(interval_ms)

    asyncio.create_task(joystick_task())

    # e) Boucle principale qui reste active
    while True:
        await asyncio.sleep(1)

# ————————————————
# 4) Démarrage uasyncio
# ————————————————
try:
    asyncio.run(async_main())
except KeyboardInterrupt:
    print("Arrêt manuel")
