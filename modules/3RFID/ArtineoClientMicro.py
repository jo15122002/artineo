# modules/3RFID/ArtineoClientMicro.py

import network
import uasyncio as asyncio
import ujson
import urequests
from utime import sleep, ticks_ms, ticks_diff

# Essaie uwebsockets, sinon fallback synchrone
try:
    import uwebsockets.client as ws_client
    ASYNC_WS = True
except ImportError:
    import websocket_client as ws_client
    ASYNC_WS = False

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
        print("[ArtineoClient] __init__")
        self.module_id        = module_id
        self.base_url         = f"http://{host}:{port}"
        self.ws_url           = f"ws://{host}:{port}/ws"
        self.http_retries     = http_retries
        self.http_backoff     = http_backoff
        self.http_timeout     = http_timeout
        self.ws_ping_interval = ws_ping_interval

        self.ws = None

        if ssid and password:
            print(f"[ArtineoClient] connect_wifi to: {ssid}")
            self.connect_wifi(ssid, password)

    def connect_wifi(self, ssid, password, timeout=15):
        print("[ArtineoClient] connect_wifi()")
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        if not sta.isconnected():
            sta.connect(ssid, password)
            start = ticks_ms()
            while not sta.isconnected() and ticks_diff(ticks_ms(), start) < timeout * 1000:
                sleep(0.5)
        if not sta.isconnected():
            raise OSError("Impossible de se connecter au Wi-Fi")
        print("[ArtineoClient] Wi-Fi OK:", sta.ifconfig())

    async def connect_ws(self):
        """Ouvre la connexion WebSocket une seule fois."""
        print("[ArtineoClient] connecting to WS…")
        conn = ws_client.connect(self.ws_url)
        self.ws = await conn if ASYNC_WS else conn
        print("[ArtineoClient] WS connected")

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
                print("[ArtineoClient] WS heartbeat error:", e)
                break
            await asyncio.sleep(self.ws_ping_interval)

    async def fetch_config(self):
        """Charge la config via HTTP GET /config?module=…"""
        print("[ArtineoClient] fetch_config()")
        url = f"{self.base_url}/config?module={self.module_id}"
        delay = self.http_backoff
        for attempt in range(1, self.http_retries + 1):
            try:
                resp = urequests.get(url, timeout=self.http_timeout)
                data = resp.json()
                cfg = data.get("config") or data.get("configurations") or {}
                print("[ArtineoClient] fetch_config OK")
                return cfg
            except Exception as e:
                print(f"[ArtineoClient] fetch_config attempt {attempt} failed:", e)
                if attempt < self.http_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
        print("[ArtineoClient] fetch_config giving up, returning {{}}")
        return {}

    async def set_buffer(self, buf):
        """Envoie directement le buffer via WS."""
        if not self.ws:
            print("[ArtineoClient] set_buffer: WS non connecté, skip")
            return
        msg = ujson.dumps({"module": self.module_id, "action": ArtineoAction.SET, "data": buf})
        print("[ArtineoClient] set_buffer:", msg)
        try:
            if ASYNC_WS:
                await self.ws.send(msg)
            else:
                self.ws.send(msg)
        except Exception as e:
            print("[ArtineoClient] set_buffer error:", e)
