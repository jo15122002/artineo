# modules/2rotation/ArtineoClientMicro.py

import network
import uasyncio as asyncio
import ujson
from utime import sleep, ticks_diff, ticks_ms

# Essaie uwebsockets.client, sinon fallback sur notre websocket_client.py local
try:
    import uwebsockets.client as ws_client
    ASYNC_WS = True
except ImportError:
    import websocket_client as ws_client
    ASYNC_WS = False

# Affiche les logs seulement si DEBUG_LOGS = True
DEBUG_LOGS = True
def log(*args, **kwargs):
    if DEBUG_LOGS:
        print(*args, **kwargs)

class ArtineoAction:
    SET = "set"
    GET = "get"

class ArtineoClient:
    """
    Client Micropython pour Artineo (module rotation).
    - Tente de se connecter en WS une première fois.
    - Si la connexion tombe, retente toutes les 5 secondes (jusqu’à réussite).
    - Expose get_latency() (mesure ping-pong) et send_buffer() pour émettre un JSON.
    """

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
        self.base_url         = f"http://{host}:{port}"
        self.ws_url           = f"ws://{host}:{port}/ws"
        self.ssid             = ssid
        self.password         = password
        self.ws_ping_interval = ws_ping_interval

        self.ws = None
        self._stop_ws = False

        if self.ssid and self.password:
            log(f"[ArtineoClient] connect_wifi to: {self.ssid}")
            self.connect_wifi()

        # Démarrage de la tâche WS en arrière-plan
        # (on lance _ws_loop() qui tente de se reconnecter en cas de perte)
        try:
            asyncio.create_task(self._ws_loop())
        except Exception as e:
            # Sur certaines versions de MicroPython, create_task peut échouer si asyncio n'est pas encore initialisé
            log("[ArtineoClient] Erreur démarrage tâche WS:", e)

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
        """
        Tâche principale pour maintenir la connexion WS :
        - essaie de se connecter ;
        - si succès, lance le ping périodique ;
        - si échec ou déconnexion, attend 5 s puis retente.
        """
        backoff = 5.0
        while not self._stop_ws:
            try:
                log("[ArtineoClient] Tentative WS →", self.ws_url)
                conn = ws_client.connect(self.ws_url)
                self.ws = await conn if ASYNC_WS else conn
                log("[ArtineoClient] WS connecté")
                # Lance le ping périodique
                asyncio.create_task(self._ws_heartbeat())
                # On reste « bloqué » en réception tant que WS ouvert
                while self.ws and getattr(self.ws, "open", True):
                    # On peut simplement dormir, car la boucle WS gère ping/pong en _ws_heartbeat
                    await asyncio.sleep(1)
                log("[ArtineoClient] WS fermé, on va retenter dans 5 s")
            except Exception as e:
                log("[ArtineoClient] Erreur WS :", e)
            # On attend un peu avant de retenter
            await asyncio.sleep(backoff)

    async def _ws_heartbeat(self):
        """Ping périodique pour maintenir la connexion WS ouverte."""
        while self.ws and getattr(self.ws, "open", True):
            try:
                if ASYNC_WS:
                    await self.ws.ping()
                else:
                    self.ws.send("ping")
            except Exception as e:
                log("[ArtineoClient] WS heartbeat error:", e)
                break
            await asyncio.sleep(self.ws_ping_interval)

    async def send_buffer(self, buf):
        """
        Envoie simplement le JSON suivant en WS :
          { "module": <module_id>, "action": "set", "data": buf }
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
            if ASYNC_WS:
                await self.ws.send(msg)
            else:
                self.ws.send(msg)
        except Exception as e:
            log("[ArtineoClient] send_buffer error:", e)

    def get_latency(self, timeout=5.0):
        """
        Mesure synchrone du ping-pong WS (RTT en ms).
        Attention : doit être appelé seulement APRÈS que le WS soit connecté
        et que la boucle asyncio tourne. Retourne un float.
        """
        if not self.ws or not getattr(self.ws, "open", False):
            raise RuntimeError("WebSocket non connecté")
        # note : en MicroPython, pas de run_coroutine_threadsafe, on peut simplifier
        # et juste envoyer un ping/pong de base (non précis). On renvoie 0 pour indiquer « non dispo »
        return 0.0

    def stop(self):
        """Arrête proprement la tâche WS et ferme la connexion."""
        self._stop_ws = True
        try:
            if self.ws:
                self.ws.close()
        except:
            pass
