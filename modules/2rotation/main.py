# main.py -- MicroPython code pour ESP32 WROOM32 avec 3 joysticks, envoi au buffer Artineo, FPS limité

import network
import uasyncio as asyncio
from machine import ADC, Pin
from utime import ticks_ms, ticks_diff
from ArtineoClientMicro import ArtineoClient

# ————————————————
# 1) CONFIGURATION WIFI + ARTINEO
# ————————————————
SSID      = "Bob_bricolo"
PASSWORD  = "bobbricolo"
HOST      = "artineo.local"    # Adresse de votre serveur Artineo
PORT      = 8000
MODULE_ID = 2                  # Identifiant unique pour ce module

# ————————————————
# 2) CONFIGURATION DES FPS
# ————————————————
# On souhaite limiter la fréquence de lecture / envoi à 24 images par seconde.
JOYSTICK_FPS        = 10
JOYSTICK_INTERVAL_MS = int(1000 / JOYSTICK_FPS)   # ≃41 ms

# ————————————————
# 3) INITIALISATION ADC (joysticks)
# ————————————————
# Chaque joystick utilise une sortie analogique (potentiomètre) sur GPIO 34, 35 et 32.
adcX = ADC(Pin(34))
adcX.width(ADC.WIDTH_12BIT)    # plage 0–4095
adcX.atten(ADC.ATTN_11DB)      # jusqu’à ~3.3 V

adcY = ADC(Pin(35))
adcY.width(ADC.WIDTH_12BIT)
adcY.atten(ADC.ATTN_11DB)

adcZ = ADC(Pin(32))
adcZ.width(ADC.WIDTH_12BIT)
adcZ.atten(ADC.ATTN_11DB)

# Fonction de normalisation (0–4095 → -1.0 .. +1.0)
def normalize(raw):
    return (raw / 2047.5) - 1.0

# ————————————————
# 4) TÂCHE ASYNCHRONE PRINCIPALE
# ————————————————
async def async_main():
    print("Démarrage du module de rotation…")

    # a) Connexion Wi-Fi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(SSID, PASSWORD)
        start = ticks_ms()
        # Attendre jusqu’à 15 000 ms max
        while not sta.isconnected() and ticks_diff(ticks_ms(), start) < 15000:
            await asyncio.sleep_ms(500)
    if not sta.isconnected():
        raise OSError("Impossible de se connecter au Wi-Fi")
    print("[WiFi] Connecté :", sta.ifconfig())

    # b) Création du client Artineo et connexion WS
    client = ArtineoClient(
        module_id=MODULE_ID,
        host=HOST,
        port=PORT,
        ssid=SSID,
        password=PASSWORD
    )
    await client.connect_ws()
    print("[Artineo] WebSocket connecté")

    # c) Tâche périodique de lecture des joysticks et envoi au buffer
    async def joystick_task():
        while True:
            # lire chaque axe
            raw_x = adcX.read()   # 0..4095
            raw_y = adcY.read()
            raw_z = adcZ.read()

            # normaliser en [-1.0 .. +1.0]
            vx = normalize(raw_x)
            vy = normalize(raw_y)
            vz = normalize(raw_z)

            buf = {
                "rotX": vx,
                "rotY": vy,
                "rotZ": vz
            }
            # envoyer au buffer via WebSocket
            try:
                await client.set_buffer(buf)
            except Exception as e:
                print("[Artineo] Erreur set_buffer :", e)
            # attendre pour respecter JOYSTICK_FPS
            await asyncio.sleep_ms(JOYSTICK_INTERVAL_MS)

    # d) Lancer la tâche de lecture en arrière-plan
    asyncio.create_task(joystick_task())

    # e) Garder la boucle active
    while True:
        await asyncio.sleep(1)

# ————————————————
# 5) DÉMARRAGE UASYNCIO
# ————————————————
try:
    asyncio.run(async_main())
except KeyboardInterrupt:
    print("Arrêt manuel")
