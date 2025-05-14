# artineo_client_micropy.py
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
        ssid=None,
        password=None,
        http_retries=3,
        http_backoff=0.5,
        ws_retries=5,
        ws_backoff=1.0,
        ws_ping_interval=20.0,
    ):
        self.module_id      = module_id
        self.host           = host
        self.port           = port
        self.base_url       = f"http://{host}:{port}"
        self.ws_url         = f"ws://{host}:{port}/ws"
        self.ssid           = ssid
        self.password       = password
        self.http_retries   = http_retries
        self.http_backoff   = http_backoff
        self.ws_retries     = ws_retries
        self.ws_backoff     = ws_backoff
        self.ws_ping_interval = ws_ping_interval

        self._handler  = None
        self._stop     = False
        self._send_q   = asyncio.Queue()
        self.ws        = None

        if ssid and password:
            self.connect_wifi(ssid, password)

    def connect_wifi(self, ssid, password, timeout=15):
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        if not sta.isconnected():
            sta.connect(ssid, password)
            start = ticks_ms()
            while (
                not sta.isconnected()
                and ticks_diff(ticks_ms(), start) < timeout * 1000
            ):
                sleep(0.5)
        if not sta.isconnected():
            raise OSError("Impossible de se connecter au Wi-Fi")
        print("Wi-Fi OK:", sta.ifconfig())

    async def _http_request(self, method, path, json_payload=None):
        url = f"{self.base_url}{path}"
        if self.module_id:
            sep = "&" if "?" in url else "?"
            url += f"{sep}module={self.module_id}"
        last_exc = None
        delay = self.http_backoff
        for attempt in range(1, self.http_retries + 1):
            try:
                if method == "GET":
                    resp = requests.get(url)
                else:
                    resp = requests.post(url, json=json_payload)
                return resp.json()
            except Exception as e:
                last_exc = e
                if attempt < self.http_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise RuntimeError(
                        f"HTTP {method} {url} échoué après {attempt} tentatives"
                    ) from last_exc

    async def fetch_config(self):
        data = await self._http_request("GET", "/config")
        return data.get("config") or data.get("configurations")

    async def set_config(self, new_config):
        return await self._http_request("POST", "/config", json_payload=new_config)

    async def _ws_handler(self):
        attempt = 0
        backoff = self.ws_backoff
        while not self._stop:
            try:
                conn = ws_client.connect(self.ws_url)
                self.ws = await conn if ASYNC_WS else conn
                # on a réussi à se connecter
                attempt = 0
                backoff = self.ws_backoff

                sender = asyncio.create_task(self._ws_sender())
                pinger = asyncio.create_task(self._ws_heartbeat())

                async for raw in self.ws:
                    if raw == "ping":
                        if ASYNC_WS:
                            await self.ws.send("pong")
                        else:
                            self.ws.send("pong")
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
            payload = await self._send_q.get()
            try:
                if ASYNC_WS:
                    await self.ws.send(payload)
                else:
                    self.ws.send(payload)
            except Exception:
                # remettre en queue pour réessayer plus tard
                await self._send_q.put(payload)
                raise

    async def _ws_heartbeat(self):
        while not self._stop:
            try:
                if ASYNC_WS:
                    await self.ws.ping()
                else:
                    # certains clients sync ne supportent pas ping(), on envoie juste un "ping"
                    self.ws.send("ping")
            except Exception:
                raise
            await asyncio.sleep(self.ws_ping_interval)

    def on_message(self, handler):
        """
        handler(msg) => appelé à chaque message reçu (dict ou raw)
        """
        self._handler = handler

    async def send_ws(self, action, data):
        """
        Envoie un message JSON via WebSocket (même si hors-ligne, on le queue).
        """
        msg = {"module": self.module_id, "action": action, "data": data}
        payload = json.dumps(msg)
        await self._send_q.put(payload)

    async def get_buffer(self):
        return await self.send_ws("get", None)

    async def set_buffer(self, buf):
        return await self.send_ws("set", buf)

    def start(self):
        """
        Lancer la supervision WS en tâche de fond.
        Appeler ensuite asyncio.run_forever() ou similar.
        """
        self._stop = False
        asyncio.create_task(self._ws_handler())

    async def stop(self):
        """
        Arrêter proprement la connexion WS.
        """
        self._stop = True
        if self.ws:
            if ASYNC_WS:
                await self.ws.close()
            else:
                self.ws.close()
        # laisser le temps aux coroutines de se terminer
        await asyncio.sleep(0)
