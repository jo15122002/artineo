# ArtineoClient.py

import sys
from os import uname


# Remplace enum.Enum par une simple classe de constantes
class ArtineoAction:
    SET = "set"
    GET = "get"

# Détection de MicroPython
MICROPY = sys.implementation.name == "micropython"

if MICROPY:
    import network
    import uasyncio as asyncio
    import ujson as json
    import urequests as requests
    from utime import sleep

    # Fallback si uwebsockets manque
    try:
        import uwebsockets.client as ws_client
    except ImportError:
        import websocket_client as ws_client

    class ArtineoClient:
        def __init__(self, module_id: int = None, host: str = None, port: int = None):
            self.host = host or "192.168.0.180"
            self.port = port or 8000
            self.base_url = f"http://{self.host}:{self.port}"
            self.ws_url   = f"ws://{self.host}:{self.port}/ws"
            self.module_id = module_id
            self.ws = None
            self._handler = None
            self.connect_wifi("Bob_bricolo", "bobbricolo")
            try:
                asyncio.create_task(self._listen_loop())
            except:
                pass

        def connect_wifi(ssid: str, password: str, timeout: int = 15):
            """
            Connecte l'ESP32 à un réseau Wi-Fi.
            Attente bloquante (timeout en secondes).
            """
            sta = network.WLAN(network.STA_IF)
            if not sta.active():
                sta.active(True)
            if not sta.isconnected():
                print("Connexion au Wi‑Fi…")
                sta.connect(ssid, password)
                start = ticks_ms()
                while not sta.isconnected() and ticks_diff(ticks_ms(), start) < timeout * 1000:
                    sleep(0.5)
            if sta.isconnected():
                print("Wi‑Fi connecté, config réseau =", sta.ifconfig())
            else:
                raise OSError("Impossible de se connecter au Wi‑Fi")


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

        async def send_ws(self, action, data: str) -> dict:
            # Accepte action en str ou via ArtineoAction
            act = action if isinstance(action, str) else action
            msg = {
                "module": self.module_id,
                "action": act,
                "data": data
            }
            return await self.send_ws_json(msg)

        def on_message(self, handler):
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            while True:
                raw = await ws.recv()
                if raw == "ping":
                    await ws.send("pong")
                    continue
                try:
                    msg = json.loads(raw)
                except:
                    msg = raw
                if self._handler:
                    self._handler(msg)
                    
        async def set_buffer(self, buffer_data):
            """
            Envoie le buffer (quel que soit son format JSON-serializable)
            au serveur pour mise à jour.
            """
            msg = {
                "module": self.module_id,
                "action": ArtineoAction.SET.value,
                "buffer": buffer_data
            }
            return await self.send_ws_json(msg)

        async def get_buffer(self):
            """
            Demande au serveur le buffer associé à ce module.
            """
            msg = {
                "module": self.module_id,
                "action": ArtineoAction.GET.value,
                "request": "buffer"
            }
            return await self.send_ws_json(msg)

        async def close_ws(self):
            if self.ws:
                await self.ws.close()
                self.ws = None

else:
    import asyncio
    import os

    import requests
    import websockets
    from dotenv import load_dotenv

    load_dotenv()

    class ArtineoClient:
        def __init__(self, module_id: int = None, host: str = None, port: int = None):
            host = host or os.getenv("ARTINEO_HOST", "127.0.0.1")
            port = port or os.getenv("ARTINEO_PORT", "8000")
            self.base_url = f"http://{host}:{port}"
            self.ws_url   = f"ws://{host}:{port}/ws"
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
            except:
                return {"raw": raw}

        async def send_ws(self, action, data: str) -> dict:
            act = action if isinstance(action, str) else action
            msg = {"module": self.module_id, "action": act, "data": data}
            return await self.send_ws_json(msg)

        def on_message(self, handler):
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
                    except:
                        msg = raw
                    if self._handler:
                        self._handler(msg)
            except websockets.ConnectionClosed:
                pass

        def start_listening(self):
            if not self._listen_task:
                self._listen_task = asyncio.create_task(self._listen_loop())

        async def set_buffer(self, buffer_data) -> dict:
            """
            Envoie le buffer au serveur pour mise à jour.
            buffer_data peut être n'importe quel objet JSON-serializable.
            Retourne la réponse du serveur sous forme de dict.
            """
            msg = {
                "module": self.module_id,
                "action": ArtineoAction.SET.value,
                "buffer": buffer_data
            }
            return await self.send_ws_json(msg)

        async def get_buffer(self) -> dict:
            """
            Récupère le buffer sur le serveur pour ce module.
            Retourne le buffer sous forme de dict (ou autre format défini).
            """
            msg = {
                "module": self.module_id,
                "action": ArtineoAction.GET.value
            }
            return await self.send_ws_json(msg)

        async def close_ws(self):
            if self.ws and not self.ws.closed:
                await self.ws.close()
            if self._listen_task:
                self._listen_task.cancel()
                self._listen_task = None
