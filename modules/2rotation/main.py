# main.py -- MicroPython code for ESP32 WROOM32 with 3 joysticks sending to Artineo buffer
# Ajout d’une notion de FPS pour limiter la fréquence de lecture des joysticks et d’envoi WS

import network
import uasyncio as asyncio
from machine import ADC, Pin
from ArtineoClientMicro import ArtineoClient, ArtineoAction

# ————————————————
# 1) CONFIGURATION WIFI + ARTINEO
# ————————————————
SSID = "Xiaomi_2FAE"
PASSWORD = "jodjoy2002"
HOST = "artineo.local"    # Adresse de votre serveur Artineo
PORT = 8000
MODULE_ID = 2            # Identifiant unique pour ce module

# ————————————————
# 2) CONFIGURATION DES FPS
# ————————————————
# On souhaite limiter la fréquence de lecture / envoi à 20 images par seconde, par exemple.
JOYSTICK_FPS = 24
JOYSTICK_INTERVAL_MS = int(1000 / JOYSTICK_FPS)   # ex. 1000/20 = 50 ms

# ————————————————
# 3) INITIALISATION ADC (joysticks)
# ————————————————
# Chaque joystick utilise une sortie analogique (potentiomètre) connectée aux broches ADC 34, 35 et 32.
adcX = ADC(Pin(34))
adcX.width(ADC.WIDTH_12BIT)    # plage 0-4095
adcX.atten(ADC.ATTN_11DB)      # plage d'entrée jusqu'à ~3.3V

adcY = ADC(Pin(35))
adcY.width(ADC.WIDTH_12BIT)
adcY.atten(ADC.ATTN_11DB)

adcZ = ADC(Pin(32))
adcZ.width(ADC.WIDTH_12BIT)
adcZ.atten(ADC.ATTN_11DB)

# Fonction de normalisation (0-4095 → -1.0 à +1.0)
def normalize(raw):
    # raw ∈ [0..4095] → on ramène en [-1.0 .. +1.0]
    return (raw / 2047.5) - 1.0

# ————————————————
# 4) TASK ASYNCHRONE PRINCIPALE
# ————————————————
async def async_main():
    # a) Connexion Wi-Fi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(SSID, PASSWORD)
        t_start = asyncio.get_event_loop().time()
        while not sta.isconnected() and (asyncio.get_event_loop().time() - t_start) < 15:
            await asyncio.sleep_ms(500)
    if not sta.isconnected():
        raise OSError("Impossible de se connecter au Wi-Fi")
    print("[WiFi] Connecté:", sta.ifconfig())

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
            # lecture brute
            raw_x = adcX.read()   # 0..4095
            raw_y = adcY.read()
            raw_z = adcZ.read()
            # normalisation en [-1.0..+1.0]
            vx = normalize(raw_x)
            vy = normalize(raw_y)
            vz = normalize(raw_z)
            # Construction du buffer à envoyer
            buf = {
                "rotX": vx,
                "rotY": vy,
                "rotZ": vz
            }
            # Envoi via WebSocket (ArtineoAction.SET)
            try:
                await client.set_buffer(buf)
            except Exception as e:
                print("[Artineo] Erreur set_buffer:", e)
                # On continue malgré l’erreur
            # Pause pour respecter la fréquence JOYSTICK_FPS
            await asyncio.sleep_ms(JOYSTICK_INTERVAL_MS)

    # d) Lancement de la tâche de lecture en parallèle
    asyncio.create_task(joystick_task())

    # e) Garder le programme en vie
    while True:
        await asyncio.sleep(1)

# ————————————————
# 5) DÉMARRAGE UASYNCIO
# ————————————————
try:
    asyncio.run(async_main())
except KeyboardInterrupt:
    print("Arrêt manuel")
