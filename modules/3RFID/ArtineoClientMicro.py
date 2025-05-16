# modules/3RFID/ArtineoClientMicro.py

import network
import uasyncio as asyncio
import ujson
import urequests
from utime import sleep, ticks_diff, ticks_ms

# Essaie uwebsockets, sinon fallback synchrone
try:
    import uwebsockets.client as ws_client
    ASYNC_WS = True
except ImportError:
    import websocket_client as ws_client
    ASYNC_WS = False

# Affiche les logs seulement si DEBUG_LOGS = True
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
        host="192.168.0.50",
        port=8000,
        ssid=None,
        password=None,
        http_retries=3,
        http_backoff=0.5,
        http_timeout=5,
        ws_ping_interval=20.0,
    ):
        log("[ArtineoClient] __init__")
        self.module_id        = module_id
        self.base_url         = f"http://{host}:{port}"
        self.ws_url           = f"ws://{host}:{port}/ws"
        self.http_retries     = http_retries
        self.http_backoff     = http_backoff
        self.http_timeout     = http_timeout
        self.ws_ping_interval = ws_ping_interval
        self.ssid             = ssid
        self.password         = password

        self.ws = None

        if self.ssid and self.password:
            log(f"[ArtineoClient] connect_wifi to: {self.ssid}")
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

    async def connect_ws(self):
        """Ouvre la connexion WebSocket une seule fois."""
        log("[ArtineoClient] connecting to WS…")
        conn = ws_client.connect(self.ws_url)
        self.ws = await conn if ASYNC_WS else conn
        log("[ArtineoClient] WS connected")

        # lance un ping périodique
        asyncio.create_task(self._ws_heartbeat())

    async def _ws_heartbeat(self):
        """Ping régulier pour maintenir la connexion."""
        while True:
            try:
                if ASYNC_WS:
                    await self.ws.ping()
                else:
                    self.ws.send("ping")
            except Exception as e:
                log("[ArtineoClient] WS heartbeat error:", e)
                break
            await asyncio.sleep(self.ws_ping_interval)

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

    async def set_buffer(self, buf):
        """Envoie directement le buffer via WS."""
        if not self.ws:
            log("[ArtineoClient] set_buffer: WS non connecté, skip")
            return
        msg = ujson.dumps({
            "module": self.module_id,
            "action": ArtineoAction.SET,
            "data": buf
        })
        log("[ArtineoClient] set_buffer:", msg)
        try:
            if ASYNC_WS:
                await self.ws.send(msg)
            else:
                self.ws.send(msg)
        except Exception as e:
            log("[ArtineoClient] set_buffer error:", e)
            # tente une reconnexion Wi-Fi/WS si besoin
            try:
                self.connect_wifi()
                await self.connect_ws()
            except Exception as reconnect_err:
                log("[ArtineoClient] reconnect failed:", reconnect_err)
