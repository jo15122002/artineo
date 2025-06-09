# modules/2rotation/main.py

import network
import uasyncio as asyncio
import gc
from machine import ADC, Pin
from utime import ticks_ms, ticks_diff

from ArtineoClientMicro import ArtineoClient

# —————— 1) Wi-Fi et Artineo ——————
SSID      = "Bob_bricolo"
PASSWORD  = "bobbricolo"
HOST      = "artineo.local"
PORT      = 8000
MODULE_ID = 2

# —————— 2) ADC pour KY-023 (VRx) ——————
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

# —————— 3) Paramètres du filtre + zone morte ——————
ALPHA      = 0.1     # coeff passe-bas
DEADZONE   = 0.05    # zone morte ±0.05
SENSITIVITY = 0.02   # incrément par itération

# Valeurs filtrées initiales
filtered_x = 0.0
filtered_y = 0.0
filtered_z = 0.0

# Rotation cumulée
rotX = 0.0
rotY = 0.0
rotZ = 0.0

# On crée dès maintenant un buffer dict que l’on réutilisera
_shared_buf = {
    "module": MODULE_ID,
    "action": "set",
    "data": {
        "rotX": 0.0,
        "rotY": 0.0,
        "rotZ": 0.0
    }
}

# —————— 4) Tâche asynchrone principale ——————
async def async_main():
    print("Démarrage module KY-023 → Artineo rotation…")

    # a) Connexion Wi-Fi
    # (tu peux laisser cette partie ou bien laisser ArtineoClient s’en charger,
    #  peu importe)
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

    # b) Client Artineo
    client = ArtineoClient(
        module_id=MODULE_ID,
        host=HOST,
        port=PORT,
        ssid=SSID,
        password=PASSWORD,
    )
    # on insère un petit yield pour garantir qu’on est bien dans la boucle asyncio
    await asyncio.sleep(0)
    # on crée la tâche WS
    asyncio.create_task(client._ws_loop())
    print("[Artineo] Tâche WS démarrée")

    # c) Tâche joystick
    async def joystick_task():
        global filtered_x, filtered_y, filtered_z
        global rotX, rotY, rotZ, _shared_buf

        while True:
            # 1) Lecture brute
            raw_x = adcX.read()
            raw_y = adcY.read()
            raw_z = adcZ.read()

            vx = normalize(raw_x)
            vy = normalize(raw_y)
            vz = normalize(raw_z)

            # 2) Filtre passe-bas
            filtered_x = ALPHA * vx + (1 - ALPHA) * filtered_x
            filtered_y = ALPHA * vy + (1 - ALPHA) * filtered_y
            filtered_z = ALPHA * vz + (1 - ALPHA) * filtered_z

            # 3) Zone morte
            if abs(filtered_x) < DEADZONE:
                filtered_x = 0.0
            if abs(filtered_y) < DEADZONE:
                filtered_y = 0.0
            if abs(filtered_z) < DEADZONE:
                filtered_z = 0.0

            # 4) Incrémentation rotation cumulée
            rotX += filtered_x * SENSITIVITY
            rotY += filtered_y * SENSITIVITY
            rotZ += filtered_z * SENSITIVITY

            # 5) Mets à jour le buffer partagé (sans recréer de dict)
            _shared_buf["data"]["rotX"] = rotX
            _shared_buf["data"]["rotY"] = rotY
            _shared_buf["data"]["rotZ"] = rotZ

            # 6) Sérialisation + envoi WS
            try:
                # ujson.dumps fait toujours une nouvelle chaîne, 
                # MAIS on n’a pas à construire un nouveau dict à chaque fois
                await client.send_buffer(_shared_buf["data"])
            except Exception as e:
                print("[Artineo] Erreur send_buffer :", e)

            # 7) Forcer le GC pour libérer immédiatement les temporaires
            gc.collect()
            await asyncio.sleep(0)

            # 8) Affiche la mémoire libre pour debug
            print("[joystick_task] mem_free =", gc.mem_free())

            # 9) Pause ~50 ms (≈20 FPS)
            await asyncio.sleep_ms(50)

    asyncio.create_task(joystick_task())

    # Boucle vide pour maintenir le programme actif
    while True:
        await asyncio.sleep(1)

# —————— 5) Démarrage uasyncio ——————
try:
    asyncio.run(async_main())
except KeyboardInterrupt:
    print("Arrêt manuel")
