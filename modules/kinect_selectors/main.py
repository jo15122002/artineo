import uasyncio as asyncio
from machine import Pin
from ArtineoClientMicro import ArtineoClient
from utime import sleep_ms

# ————————————————————————————————————————————————————————————————
# CONFIGURATION réseau & module
# ————————————————————————————————————————————————————————————————
MODULE_ID = 41
HOST      = "192.168.1.142"
PORT      = 8000

# ————————————————————————————————————————————————————————————————
# ÉTAT GLOBAL pour la détection d'appuis
# ————————————————————————————————————————————————————————————————
button1_pressed = False
button2_pressed = False

def button_irq(pin):
    """
    IRQ handler : on tombe ici sur front descendant (appui).
    On ne fait QUE lever un drapeau, pas d'envoi direct.
    """
    global button1_pressed, button2_pressed
    if pin.value() == 1:
        sleep_ms(50)  # anti-rebond
        if pin is button1:
            button1_pressed = True
        elif pin is button2:
            button2_pressed = True

async def ws_connect_with_retry(client, retries=5, base_delay=2):
    """
    Tente plusieurs fois de se connecter au WS,
    en réessayant Wifi+WS avec back-off exponentiel.
    """
    delay = base_delay
    for attempt in range(1, retries + 1):
        try:
            print(f"WS connect, tentative #{attempt}…")
            await client.connect_ws()
            print("→ WebSocket OK")
            return True
        except OSError as e:
            print(f"!!! WS connexion échouée ({e}), retry dans {delay}s")
            # on tente de reconnecter le Wi-Fi avant de réessayer
            try:
                client.connect_wifi()
                print("→ Wi-Fi re-connecté")
            except Exception as wifi_e:
                print(f"⚠️ échec reconnection Wi-Fi : {wifi_e}")
            await asyncio.sleep(delay)
            delay *= 2
    return False

async def async_main():
    global button1, button2, button1_pressed, button2_pressed

    # 1) Instanciation du client
    client = ArtineoClient(
        module_id = MODULE_ID,
        host      = HOST,
        port      = PORT,
        ssid      = SSID,
        password  = PASSWORD,
    )

    # 2) Connexion Wi-Fi (blocante)
    try:
        client.connect_wifi()
        print("✅ Wi-Fi connecté :", SSID)
    except Exception as e:
        print("❌ Impossible de se connecter au Wi-Fi :", e)
        return

    # 3) Connexion WebSocket avec retry
    ok = await ws_connect_with_retry(client, retries=4, base_delay=1)
    if not ok:
        print("❌ Échec de la connexion WS après plusieurs tentatives")
        return

    # 4) (Optionnel) récupération de la config distante
    try:
        cfg = await client.fetch_config()
        print("✅ Config reçue :", cfg)
    except Exception as e:
        print("⚠️ fetch_config a échoué :", e)

    # 5) Envoi d'un buffer initial pour « annoncer » l'état au serveur
    await client.set_buffer({"button1": False, "button2": False})

    # 6) Setup des GPIO
    button1 = Pin(25, Pin.IN, Pin.PULL_UP)
    button2 = Pin(26, Pin.IN, Pin.PULL_UP)
    # IRQ front descendant = appui
    button1.irq(trigger=Pin.IRQ_RISING, handler=button_irq)
    button2.irq(trigger=Pin.IRQ_RISING, handler=button_irq)
    print("✅ Boutons initialisés")

    # 7) Boucle principale : envoi des événements de bouton hors IRQ
    while True:
        if button1_pressed or button2_pressed:
            payload = {}
            if button1_pressed:
                print("🔘 Bouton 1 appuyé → envoi WS")
                payload = {"button": 1}
            if button2_pressed:
                print("🔘 Bouton 2 appuyé → envoi WS")
                payload = {"button": 2}
            # remise à zéro des drapeaux
            button1_pressed = False
            button2_pressed = False

            # envoi et gestion d'éventuelle reconnexion
            try:
                await client.set_buffer(payload)
            except Exception as e:
                print("⚠️ Envoi set_buffer a échoué :", e)
                # on retentera naturellement au prochain cycle
        
        # on ne bouffe pas trop de CPU
        await asyncio.sleep_ms(100)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except Exception as e:
        print("🔥 Erreur fatale dans async_main :", e)
