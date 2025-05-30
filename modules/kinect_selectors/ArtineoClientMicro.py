import network
import uasyncio as asyncio
import ujson
import urequests
from utime import sleep, ticks_diff, ticks_ms

# Fallback synchrone websocket
import websocket_client as ws_client
ASYNC_WS = False

DEBUG_LOGS = True
def log(*args):
    if DEBUG_LOGS:
        print("[ArtineoClient]", *args)

class ArtineoAction:
    SET = "set"
    GET = "get"

class ArtineoClient:
    def __init__(
        self,
        module_id,
        host="192.168.1.142",
        port=8000,
        ssid=None,
        password=None,
        http_retries=3,
        http_backoff=0.5,
        http_timeout=5,
        ws_ping_interval=20.0,
    ):
        self.module_id        = module_id
        self.base_url         = f"http://{host}:{port}"
        self.ws_url           = f"ws://{host}:{port}/ws"
        self.http_retries     = http_retries
        self.http_backoff     = http_backoff
        self.http_timeout     = http_timeout
        self.ws_ping_interval = ws_ping_interval
        self.ssid             = ssid
        self.password         = password
        self.ws               = None

        if self.ssid and self.password:
            self.connect_wifi()

    def connect_wifi(self, timeout=15):
        log("connect_wifi()")
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        if not sta.isconnected():
            sta.connect(self.ssid, self.password)
            start = ticks_ms()
            while not sta.isconnected() and ticks_diff(ticks_ms(), start) < timeout * 1000:
                sleep(0.5)
        if not sta.isconnected():
            raise OSError("Impossible de se connecter au Wi-Fi")
        log("Wi-Fi OK:", sta.ifconfig())

    async def connect_ws(self):
        """Connexion WS synchrone + démarrage du heartbeat et du receiver."""
        log("connecting WS to", self.ws_url)
        # sync connect
        self.ws = ws_client.connect(self.ws_url)
        log("WS connected (fallback)")
        # ping/pong texte
        asyncio.create_task(self._ws_heartbeat())
        # receiver loop
        asyncio.create_task(self._ws_receiver())

    async def _ws_heartbeat(self):
        """Ping texte périodique."""
        log("heartbeat started")
        while True:
            if not self.ws:
                log("heartbeat: no ws, exiting")
                break
            try:
                self.ws.send("ping")
                # pas de recv ici, serveur répondra "pong" dans _ws_receiver
            except Exception as e:
                log("heartbeat send error:", e)
                try: self.ws.close()
                except: pass
                self.ws = None
                break
            await asyncio.sleep(self.ws_ping_interval)
        log("heartbeat exiting")

    async def _ws_receiver(self):
        """Boucle qui lit tout ce qui vient du serveur."""
        log("receiver started")
        while True:
            if not self.ws:
                log("receiver: ws is None, exiting")
                break
            try:
                msg = self.ws.recv()  # blocking recv
                log("Received WS message:", msg)
            except Exception as e:
                log("receiver error (connection closed?):", e)
                try: self.ws.close()
                except: pass
                self.ws = None
                break
        log("receiver exiting")

    async def set_buffer(self, buf):
        """Envoie buf, reconnecte si nécessaire."""
        # reconnect if needed
        if not self.ws:
            log("set_buffer: ws down, reconnecting…")
            if self.ssid and self.password:
                self.connect_wifi()
            await self.connect_ws()

        # build message
        msg = ujson.dumps({
            "module": self.module_id,
            "action": ArtineoAction.SET,
            "data": buf
        })
        log("send_buffer:", msg)
        # try send
        try:
            self.ws.send(msg)
        except Exception as e:
            log("send error:", e)
            try: self.ws.close()
            except: pass
            self.ws = None

    async def fetch_config(self):
        """Charge la config via HTTP GET /config?module=…"""
        log("[ArtineoClient] fetch_config()")
        url = f"{self.base_url}/config?module={self.module_id}"
        delay = self.http_backoff
        for attempt in range(1, self.http_retries + 1):
            try:
                resp = urequests.get(url, timeout=self.http_timeout)
                data = resp.json()
                cfg = data.get("config") or data.get("configurations") or {}
                log("[ArtineoClient] fetch_config OK")
                return cfg
            except Exception as e:
                log(f"[ArtineoClient] fetch_config attempt {attempt} failed:", e)
                if attempt < self.http_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
        log("[ArtineoClient] fetch_config giving up, returning {}")
        return {}