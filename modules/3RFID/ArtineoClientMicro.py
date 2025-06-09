# modules/2rotation/ArtineoClientMicro.py

import sys
sys.path.insert(0, '/lib')

import network
import uasyncio as asyncio
import ujson
from utime import sleep, ticks_diff, ticks_ms

# on importe les constantes de protocole
from uwebsockets.protocol import OP_PING, OP_PONG

# Essaie notre client uwebsockets
try:
    import uwebsockets.client as ws_client
    print("[ArtineoClient] Using uwebsockets.client for WebSocket")
except ImportError:
    import websocket_client as ws_client  # fallback
    print("[ArtineoClient] Using websocket_client fallback")

DEBUG_LOGS = False
def log(*args, **kwargs):
    if DEBUG_LOGS:
        print(*args, **kwargs)

class ArtineoAction:
    SET = "set"
    GET = "get"

class ArtineoClient:
    def __init__(
        self,
        module_id,
        host="artineo.local",
        port=8000,
        ssid=None,
        password=None,
        ws_ping_interval=20.0,
    ):
        log("[ArtineoClient] __init__")
        self.module_id        = module_id
        self.ws_url           = f"ws://{host}:{port}/ws"
        self.ssid             = ssid
        self.password         = password
        self.ws_ping_interval = ws_ping_interval

        self.ws = None
        self._stop_ws = False

        if self.ssid and self.password:
            self.connect_wifi()

    def connect_wifi(self, timeout=15):
        log("[ArtineoClient] connect_wifi()")
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        if not sta.isconnected():
            sta.connect(self.ssid, self.password)
            start = ticks_ms()
            while not sta.isconnected() and ticks_diff(ticks_ms(), start) < timeout * 1000:
                sleep(0.5)
        if not sta.isconnected():
            raise OSError("Impossible de se connecter au Wi-Fi")
        log("[ArtineoClient] Wi-Fi OK:", sta.ifconfig())

    async def _ws_loop(self):
        backoff = 5.0
        while not self._stop_ws:
            try:
                log("[ArtineoClient] Tentative WS →", self.ws_url)
                # uwebsockets.client.connect n'est pas un coroutine
                self.ws = ws_client.connect(self.ws_url)
                log("[ArtineoClient] WS connecté")

                # lance heartbeat et réception
                asyncio.create_task(self._ws_heartbeat())
                asyncio.create_task(self._ws_receiver())

                # on reste bloqué tant que c'est ouvert
                while self.ws.open:
                    await asyncio.sleep(1)

                log("[ArtineoClient] WS fermée, on retente dans 5 s")
            except Exception as e:
                log("[ArtineoClient] Exception dans _ws_loop :", e)
            await asyncio.sleep(backoff)

    async def _ws_heartbeat(self):
        """Envoie périodiquement un frame PING pour tenir la connexion."""
        while self.ws and getattr(self.ws, "open", False):
            try:
                # write_frame(OP_PING) envoie un vrai ping
                self.ws.write_frame(OP_PING)
                log("[ArtineoClient] Heartbeat → PING")
            except Exception as e:
                log("[ArtineoClient] WS heartbeat error :", e)
                break
            await asyncio.sleep(self.ws_ping_interval)

    async def _ws_receiver(self):
        """
        Tâche non-bloquante pour lire les frames WS sans bloquer uasyncio.
        """
        while self.ws and getattr(self.ws, "open", False):
            try:
                # passe en mode timeout court pour ne pas bloquer indéfiniment
                self.ws.settimeout(0.01)            
                msg = self.ws.recv()             
                if msg:
                    log("[ArtineoClient] reçu :", msg)
            except OSError:
                # pas de frame dispo → on rend la main
                pass
            except Exception as e:
                log("[ArtineoClient] _ws_receiver error :", e)
                break
            # on laisse tourner les autres tâches
            await asyncio.sleep_ms(50)


    async def send_buffer(self, buf):
        """
        Envoie un JSON { module, action:set, data } si la WS est ouverte.
        """
        if not self.ws or not getattr(self.ws, "open", False):
            log("[ArtineoClient] send_buffer : WS non connecté, skip.")
            return
        msg = ujson.dumps({
            "module": self.module_id,
            "action": ArtineoAction.SET,
            "data": buf
        })
        log("[ArtineoClient] send :", msg)
        try:
            self.ws.send(msg)
        except Exception as e:
            log("[ArtineoClient] send_buffer error :", e)

    def stop(self):
        """Arrête la tâche WS et ferme la connexion."""
        self._stop_ws = True
        try:
            if self.ws:
                self.ws.close()
        except:
            pass
