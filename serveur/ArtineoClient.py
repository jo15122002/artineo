# artineo_client.py

import sys

# Détection de MicroPython
MICROPY = sys.implementation.name == "micropython"

if MICROPY:
    # MicroPython / ESP32
    import uasyncio as asyncio
    import ujson as json
    import urequests as requests
    import uwebsockets.client as ws_client
else:
    # CPython / Raspberry Pi
    import asyncio
    import json
    import os

    import requests
    import websockets
    from dotenv import load_dotenv

    load_dotenv()


from enum import Enum


class ArtineoAction(Enum):
    SET = "set"
    GET = "get"
    def __str__(self):
        return self.value


# -------------------------------------------------------------------
# Implémentation pour MicroPython (ESP32)
# -------------------------------------------------------------------
if MICROPY:
    class ArtineoClient:
        def __init__(self, module_id: int = None, host: str = None, port: int = None):
            """
            Sur ESP32, on passe souvent host/port en dur,
            ou on peut les fournir ici au démarrage.
            """
            self.host = host or "192.168.0.180"
            self.port = port or 8000
            self.base_url = f"http://{self.host}:{self.port}"
            self.ws_url   = f"ws://{self.host}:{self.port}/ws"
            self.module_id = module_id

            self.ws = None
            self._handler = None
            # démarre le listener
            try:
                asyncio.create_task(self._listen_loop())
            except:
                pass

        def fetch_config(self) -> dict:
            url = self.base_url + "/config"
            if self.module_id is not None:
                url += f"?module={self.module_id}"
            r = requests.get(url)
            data = r.json()
            return data.get("config") or data.get("configurations")

        async def connect_ws(self):
            if self.ws is None:
                self.ws = await ws_client.connect(self.ws_url)
            return self.ws

        async def send_ws_json(self, message: dict) -> dict:
            ws = await self.connect_ws()
            await ws.send(json.dumps(message))
            raw = await ws.recv()
            try:
                return json.loads(raw)
            except:
                return {"raw": raw}

        async def send_ws(self, action: ArtineoAction, data: str) -> dict:
            msg = {
                "module": self.module_id,
                "action": action.value,
                "data": data
            }
            return await self.send_ws_json(msg)

        def on_message(self, handler):
            """
            Enregistre un callback handler(msg) → None
            """
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            while True:
                raw = await ws.recv()
                # si on reçoit un ping
                if raw == "ping":
                    await ws.send("pong")
                    continue
                # sinon on parse et on appelle le handler
                try:
                    msg = json.loads(raw)
                except:
                    msg = raw
                if self._handler:
                    self._handler(msg)

        async def close_ws(self):
            if self.ws:
                await self.ws.close()
                self.ws = None


# -------------------------------------------------------------------
# Implémentation pour CPython (Raspberry Pi)
# -------------------------------------------------------------------
else:
    import os

    class ArtineoClient:
        def __init__(self, module_id: int = None, host: str = None, port: int = None):
            host = host or os.getenv("ARTINEO_HOST", "127.0.0.1")
            port = port or os.getenv("ARTINEO_PORT", "8000")
            self.base_url  = f"http://{host}:{port}"
            self.ws_url    = f"ws://{host}:{port}/ws"
            self.module_id = module_id

            self.ws = None
            self._handler = None
            self._listen_task = None

        def fetch_config(self) -> dict:
            params = {}
            if self.module_id is not None:
                params["module"] = self.module_id
            resp = requests.get(f"{self.base_url}/config", params=params)
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("config") or payload.get("configurations")

        async def connect_ws(self):
            if self.ws is None or self.ws.closed:
                self.ws = await websockets.connect(self.ws_url)
            return self.ws

        async def send_ws_json(self, message: dict) -> dict:
            ws = await self.connect_ws()
            await ws.send(json.dumps(message))
            raw = await ws.recv()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}

        async def send_ws(self, action: ArtineoAction, data: str) -> dict:
            msg = {"module": self.module_id, "action": action.value, "data": data}
            return await self.send_ws_json(msg)

        def on_message(self, handler):
            """
            Enregistre un callback handler(msg) → None
            """
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            try:
                async for raw in ws:
                    if raw.strip('"') == "ping":
                        await ws.send("pong")
                        continue
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        msg = raw
                    if self._handler:
                        self._handler(msg)
            except websockets.ConnectionClosed:
                pass

        def start_listening(self):
            """
            Démarre en tâche de fond la boucle d'écoute
            """
            if not self._listen_task:
                self._listen_task = asyncio.create_task(self._listen_loop())

        async def close_ws(self):
            if self.ws and not self.ws.closed:
                await self.ws.close()
            if self._listen_task:
                self._listen_task.cancel()
                self._listen_task = None
