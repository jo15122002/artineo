# ArtineoClient.py

import sys

# JSON unifié
if sys.implementation.name == "micropython":
    import ujson as json
else:
    import json

# Actions
class ArtineoAction:
    SET = "set"
    GET = "get"

# Plateforme
MICROPY = sys.implementation.name == "micropython"

if MICROPY:
    # --- MicroPython π---
    import network
    import uasyncio as asyncio
    import urequests as requests
    from utime import sleep, ticks_diff, ticks_ms

    # Essaie d'uwebsockets, sinon fallback synchrone
    try:
        import uwebsockets.client as ws_client
        ASYNC_WS = True
    except ImportError:
        import websocket_client as ws_client
        ASYNC_WS = False

    class ArtineoClient:
        def __init__(self, module_id=None, host=None, port=None,
                     ssid=None, password=None):
            self.module_id = module_id
            self.host      = host or "192.168.0.180"
            self.port      = port or 8000
            self.base_url  = f"http://{self.host}:{self.port}"
            self.ws_url    = f"ws://{self.host}:{self.port}/ws"
            self.ws        = None
            self._handler  = None
            # connexion Wi‑Fi si cred fournies
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
                raise OSError("Impossible de se connecter au Wi‑Fi")
            print("Wi‑Fi OK:", sta.ifconfig())

        def fetch_config(self):
            url = f"{self.base_url}/config"
            if self.module_id is not None:
                url += f"?module={self.module_id}"
            resp = requests.get(url)
            data = resp.json()
            return data.get("config") or data.get("configurations")

        def set_config(self, new_config: dict):
            url = f"{self.base_url}/config?module={self.module_id}"
            resp = requests.post(url, json=new_config)
            return resp.json()

        async def connect_ws(self, max_retries=3, delay=1):
            # si ws déjà ouverte et utilisable
            if self.ws:
                try:
                    if ASYNC_WS:
                        if self.ws.open: return self.ws
                    else:
                        if self.ws.open: return self.ws
                except AttributeError:
                    pass
            # sinon on (re)connecte
            for i in range(max_retries):
                try:
                    conn = ws_client.connect(self.ws_url)
                    self.ws = await conn if ASYNC_WS else conn
                    print(f"[ArtineoClient] WS connectée (essai {i+1})")
                    return self.ws
                except OSError as e:
                    print(f"[ArtineoClient] échec WS {i+1}/{max_retries}: {e}")
                    await asyncio.sleep(delay)
                    delay *= 2
            print("[ArtineoClient] abandon WS")
            self.ws = None
            return None

        async def send_ws_json(self, message: dict):
            ws = await self.connect_ws()
            if not ws:
                return {}
            payload = json.dumps(message)
            # on protège contre ws fermé en vol
            try:
                if ASYNC_WS:
                    await ws.send(payload)
                    raw = await ws.recv()
                else:
                    ws.send(payload)
                    raw = ws.recv()
            except AssertionError:
                # tentative de recréation
                ws = await self.connect_ws()
                if not ws: return {}
                if ASYNC_WS:
                    await ws.send(payload)
                    raw = await ws.recv()
                else:
                    ws.send(payload)
                    raw = ws.recv()
            try:
                return json.loads(raw)
            except:
                return {"raw": raw}

        async def send_ws(self, action, data):
            msg = {"module": self.module_id, "action": action, "data": data}
            return await self.send_ws_json(msg)

        async def get_buffer(self):
            return await self.send_ws(ArtineoAction.GET, None)

        async def set_buffer(self, buffer_data):
            return await self.send_ws(ArtineoAction.SET, buffer_data)

        def on_message(self, handler):
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            if not ws: return
            while True:
                raw = await ws.recv() if ASYNC_WS else ws.recv()
                if raw == "ping":
                    if ASYNC_WS:
                        await ws.send("pong")
                    else:
                        ws.send("pong")
                    continue
                try:
                    msg = json.loads(raw)
                except:
                    msg = raw
                if self._handler:
                    self._handler(msg)

        def start_listening(self):
            try:
                asyncio.create_task(self._listen_loop())
            except Exception as e:
                print("start_listening:", e)

        async def close_ws(self):
            if not self.ws: return
            if ASYNC_WS:
                await self.ws.close()
            else:
                self.ws.close()
            self.ws = None

else:
    # --- CPython / Raspberry Pi ---
    import asyncio
    import os

    import requests
    import websockets
    from dotenv import load_dotenv

    load_dotenv()

    class ArtineoClient:
        def __init__(self, module_id=None, host=None, port=None):
            host = host or os.getenv("ARTINEO_HOST","127.0.0.1")
            port = port or os.getenv("ARTINEO_PORT","8000")
            self.module_id = module_id
            self.base_url  = f"http://{host}:{port}"
            self.ws_url    = f"ws://{host}:{port}/ws"
            self.ws        = None
            self._handler  = None
            self._task     = None

        def fetch_config(self):
            params = {}
            if self.module_id is not None:
                params["module"] = self.module_id
            r = requests.get(f"{self.base_url}/config", params=params)
            r.raise_for_status()
            payload = r.json()
            return payload.get("config") or payload.get("configurations")

        def set_config(self, new_config: dict):
            r = requests.post(f"{self.base_url}/config", params={"module":self.module_id}, json=new_config)
            r.raise_for_status()
            return r.json()

        async def connect_ws(self):
            if self.ws is None or self.ws.closed:
                self.ws = await websockets.connect(self.ws_url)
            return self.ws

        async def send_ws_json(self, message: dict):
            ws = await self.connect_ws()
            await ws.send(json.dumps(message))
            raw = await ws.recv()
            try:
                return json.loads(raw)
            except:
                return {"raw": raw}

        async def send_ws(self, action, data):
            return await self.send_ws_json({"module":self.module_id, "action":action, "data":data})

        async def get_buffer(self):
            return await self.send_ws(ArtineoAction.GET, None)

        async def set_buffer(self, buffer_data):
            return await self.send_ws(ArtineoAction.SET, buffer_data)

        def on_message(self, handler):
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            async for raw in ws:
                if raw.strip('"') == "ping":
                    await ws.send("pong")
                    continue
                try:
                    msg = json.loads(raw)
                except:
                    msg = raw
                if self._handler:
                    self._handler(msg)

        def start_listening(self):
            if not self._task:
                self._task = asyncio.create_task(self._listen_loop())

        async def close_ws(self):
            if self.ws and not self.ws.closed:
                await self.ws.close()
            if self._task:
                self._task.cancel()
                self._task = None
