# ArtineoClientMicro.py

import random

import network
import uasyncio as asyncio
import ujson as json
import urequests as requests
from utime import sleep, ticks_diff, ticks_ms

# essaie uwebsockets, sinon fallback synchrone
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
        module_id=None,
        host="artineo.local",
        port=8000,
        ssid="Bob_bricolo",
        password="bobbricolo",
        http_retries=3,
        http_backoff=0.5,
        ws_retries=5,
        ws_backoff=1.0,
        ws_ping_interval=20.0,
    ):
        self.module_id        = module_id
        self.base_url         = f"http://{host}:{port}"
        self.ws_url           = f"ws://{host}:{port}/ws"
        self.http_retries     = http_retries
        self.http_backoff     = http_backoff
        self.ws_retries       = ws_retries
        self.ws_backoff       = ws_backoff
        self.ws_ping_interval = ws_ping_interval

        self._handler    = None
        self._stop       = False
        # nouvelle file FIFO + event
        self._send_q     = []
        self._send_event = asyncio.Event()
        self.ws          = None

        if ssid and password:
            self.connect_wifi(ssid, password)

    def connect_wifi(self, ssid, password, timeout=15):
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        if not sta.isconnected():
            sta.connect(ssid, password)
            start = ticks_ms()
            while not sta.isconnected() and ticks_diff(ticks_ms(), start) < timeout*1000:
                sleep(0.5)
        if not sta.isconnected():
            raise OSError("Impossible de se connecter au Wi-Fi")
        print("Wi-Fi OK:", sta.ifconfig())

    async def _http_request(self, method, path, json_payload=None):
        url = f"{self.base_url}{path}"
        if self.module_id:
            sep = "&" if "?" in url else "?"
            url += f"{sep}module={self.module_id}"
        delay = self.http_backoff
        for attempt in range(1, self.http_retries+1):
            try:
                resp = requests.get(url) if method=="GET" else requests.post(url, json=json_payload)
                return resp.json()
            except Exception as e:
                if attempt < self.http_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise RuntimeError(f"HTTP {method} {url} échoué après {attempt} tentatives") from e

    async def fetch_config(self):
        data = await self._http_request("GET", "/config")
        return data.get("config") or data.get("configurations")

    async def set_config(self, new_config):
        return await self._http_request("POST", "/config", json_payload=new_config)

    async def _ws_handler(self):
        attempt, backoff = 0, self.ws_backoff
        while not self._stop:
            try:
                conn = ws_client.connect(self.ws_url)
                self.ws = await conn if ASYNC_WS else conn
                attempt, backoff = 0, self.ws_backoff

                sender = asyncio.create_task(self._ws_sender())
                pinger = asyncio.create_task(self._ws_heartbeat())

                async for raw in self.ws:
                    if raw == "ping":
                        if ASYNC_WS: await self.ws.send("pong")
                        else:           self.ws.send("pong")
                        continue
                    try:
                        msg = json.loads(raw)
                    except:
                        msg = raw
                    if self._handler:
                        self._handler(msg)

                sender.cancel()
                pinger.cancel()

            except Exception as e:
                print(f"[ArtineoClient] WS erreur: {e}")
                attempt += 1
                if attempt > self.ws_retries:
                    print("[ArtineoClient] Abandon WS")
                    break
                await asyncio.sleep(backoff)
                backoff *= 2

        print("[ArtineoClient] WS stopped")

    async def _ws_sender(self):
        while not self._stop:
            # si rien à envoyer, on attend l'événement
            while not self._send_q:
                await self._send_event.wait()
                self._send_event.clear()
            payload = self._send_q.pop(0)
            try:
                if ASYNC_WS: await self.ws.send(payload)
                else:         self.ws.send(payload)
            except Exception:
                # remet en tête de file pour réessayer
                self._send_q.insert(0, payload)
                raise

    async def _ws_heartbeat(self):
        while not self._stop:
            try:
                if ASYNC_WS: await self.ws.ping()
                else:         self.ws.send("ping")
            except:
                raise
            await asyncio.sleep(self.ws_ping_interval)

    def on_message(self, handler):
        """Enregistre le handler(msg) appelé à chaque message."""
        self._handler = handler

    async def send_ws(self, action, data):
        """Met en file un WS JSON et déclenche l’envoi."""
        msg = {"module": self.module_id, "action": action, "data": data}
        payload = json.dumps(msg)
        self._send_q.append(payload)
        self._send_event.set()

    async def get_buffer(self):
        return await self.send_ws(ArtineoAction.GET, None)

    async def set_buffer(self, buf):
        return await self.send_ws(ArtineoAction.SET, buf)

    def start(self):
        """Démarre la boucle WS en tâche de fond."""
        self._stop = False
        asyncio.create_task(self._ws_handler())

    async def stop(self):
        """Arrête proprement WS."""
        self._stop = True
        if self.ws:
            if ASYNC_WS: await self.ws.close()
            else:         self.ws.close()
        await asyncio.sleep(0)
