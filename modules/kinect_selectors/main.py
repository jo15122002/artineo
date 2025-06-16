import uasyncio as asyncio
from machine import Pin
from ArtineoClientMicro import ArtineoClient
from utime import sleep_ms

# ————————————————————————————————————————————————————————————————
# CONFIGURATION réseau & module
# ————————————————————————————————————————————————————————————————
MODULE_ID = 41
HOST      = "192.168.2.1"
PORT      = 8000

# ————————————————————————————————————————————————————————————————
# ÉTAT GLOBAL pour la détection d'appuis
# ————————————————————————————————————————————————————————————————
button1_pressed = False
button2_pressed = False
button3_pressed = False

def button_irq(pin):
    """
    IRQ handler : on tombe ici sur front descendant (appui).
    On ne fait QUE lever un drapeau, pas d'envoi direct.
    """
    global button1_pressed, button2_pressed, button3_pressed, button1, button2, button3
    if pin.value() == 1:
        # print(f"⚠️ {pin} : appui détecté mais déjà relâché")
        # print(button3)
        sleep_ms(50)  # anti-rebond
        if pin is button1:
            button1_pressed = True
        elif pin is button2:
            button2_pressed = True
        elif pin is button3:
            button3_pressed = True
        else:
            print(f"⚠️ IRQ inconnu pour {pin}")

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
    global button1, button2, button3
    global button1_pressed, button2_pressed, button3_pressed

    # 1) Instanciation du client
    client = ArtineoClient(
        module_id = MODULE_ID,
        host      = HOST,
        port      = PORT,
        ssid      = "Bob_bricolo",
        password  = "bobbricolo",
    )

    # 2) Connexion Wi-Fi (blocante)
    try:
        client.connect_wifi()
        print("✅ Wi-Fi connecté :", client.ssid)
    except Exception as e:
        print("❌ Impossible de se connecter au Wi-Fi :", e)
        return
    
    asyncio.create_task(client._ws_loop())
    asyncio.create_task(client._ws_receiver())

    # On laisse un petit laps de temps pour établir la WS
    await asyncio.sleep(1)

    # # 3) Connexion WebSocket avec retry
    # ok = await ws_connect_with_retry(client, retries=4, base_delay=1)
    # if not ok:
    #     print("❌ Échec de la connexion WS après plusieurs tentatives")
    #     return

    # 4) (Optionnel) récupération de la config distante
    try:
        cfg = await client.fetch_config()
        print("✅ Config reçue :", cfg)
    except Exception as e:
        print("⚠️ fetch_config a échoué :", e)

    # 5) Envoi d'un buffer initial pour « annoncer » l'état au serveur
    await client.send_buffer({"button1": False, "button2": False, "button3": False})

    # 6) Setup des GPIO
    button1 = Pin(25, Pin.IN, Pin.PULL_UP)
    button2 = Pin(26, Pin.IN, Pin.PULL_UP)
    button3 = Pin(32, Pin.IN, Pin.PULL_UP)
    
    # IRQ front descendant = appui
    button1.irq(trigger=Pin.IRQ_RISING, handler=button_irq)
    button2.irq(trigger=Pin.IRQ_RISING, handler=button_irq)
    button3.irq(trigger=Pin.IRQ_RISING, handler=button_irq)
    print("✅ Boutons initialisés")

    # 7) Boucle principale : envoi des événements de bouton hors IRQ
    while True:
        if button1_pressed or button2_pressed or button3_pressed:
            payload = {}
            if button1_pressed:
                print("🔘 Bouton 1 appuyé → envoi WS")
                payload = {"button": 1}
            elif button2_pressed:
                print("🔘 Bouton 2 appuyé → envoi WS")
                payload = {"button": 2}
            elif button3_pressed:
                print("🔘 Bouton 3 appuyé → envoi WS")
                payload = {"button": 3}
                
            # remise à zéro des drapeaux
            button1_pressed = False
            button2_pressed = False
            button3_pressed = False

            # envoi et gestion d'éventuelle reconnexion
            try:
                await client.send_buffer(payload)
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
