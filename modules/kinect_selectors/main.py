import uasyncio as asyncio
from machine import Pin
from ArtineoClientMicro import ArtineoClient
from utime import sleep_ms

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────

MODULE_ID = "4" 
HOST      = "192.168.1.142"
PORT      = 8000

# ─── INITIALISATION DU CLIENT Artineo ────────────────────────────────────────────
client = ArtineoClient(
    module_id = MODULE_ID,
    host      = HOST,
    port      = PORT,
    ssid      = SSID,
    password  = PASSWORD,
)

# ─── HANDLER POUR L’APPUI SUR BOUTON ─────────────────────────────────────────────
def handle_press(pin):
    # front descendant -> pin.value() passe de 1→0 à l’appui
    if pin.value() == 0:
        name = "button1" if pin is button1 else "button2"
        print(f"🔘 {name} appuyé")
        # envoi asynchrone (créé une tâche uasyncio)
        try:
            asyncio.create_task(client.set_buffer({"button": name}))
        except Exception as e:
            print("Erreur scheduling send:", e)
        # anti-rebond logiciel
        sleep_ms(50)

# ─── PROGRAMME PRINCIPAL ASYNCHRONE ───────────────────────────────────────────────
async def main():
    # 1) connexion Wi-Fi
    client.connect_wifi()
    print("Wi-Fi connecté ▶", client.ssid)

    try:
        # Test rapide du GET /config
        cfg = await client.fetch_config()
        print("✅ HTTP OK, config reçue:", cfg)
    except Exception as e:
        print("❌ Échec HTTP :", e)

    # 2) ouverture du WebSocket
    await client.connect_ws()
    print("WebSocket open ▶", client.ws_url)

    # 3) configuration des GPIO
    global button1, button2
    button1 = Pin(25, Pin.IN, Pin.PULL_UP)
    button2 = Pin(26, Pin.IN, Pin.PULL_UP)

    # 4) attacher les IRQ front descendant (appui)
    button1.irq(trigger=Pin.IRQ_FALLING, handler=handle_press)
    button2.irq(trigger=Pin.IRQ_FALLING, handler=handle_press)

    # 5) boucle infinie pour garder l’event-loop actif
    while True:
        await asyncio.sleep(1)

# ─── DÉMARRAGE DE L’APPLICATION ─────────────────────────────────────────────────
asyncio.run(main())
