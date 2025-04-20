# ArtineoClient.py

import sys

import ujson as json


# Remplace enum.Enum par une simple classe de constantes
class ArtineoAction:
    SET = "set"
    GET = "get"

# Détection MicroPython
MICROPY = sys.implementation.name == "micropython"

if MICROPY:
    import network
    import uasyncio as asyncio
    import urequests as requests
    from utime import sleep, ticks_diff, ticks_ms

    # Essaie d'importer le WebSocket asynchrone, sinon fallback synchrone
    try:
        import uwebsockets.client as ws_client
        ASYNC_WS = True
    except ImportError:
        import websocket_client as ws_client
        ASYNC_WS = False

    class ArtineoClient:
        def __init__(self, module_id: int=None, host: str=None, port: int=None,
                     ssid: str=None, password: str=None):
            self.host      = host or "127.0.0.1"
            self.port      = port or 8000
            self.module_id = module_id
            self.base_url  = f"http://{self.host}:{self.port}"
            self.ws_url    = f"ws://{self.host}:{self.port}/ws"
            self.ws        = None
            self._handler  = None
            # connect Wi‑Fi immédiatement
            if ssid and password:
                self.connect_wifi(ssid, password)

        def connect_wifi(self, ssid: str, password: str, timeout: int=15):
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

        def fetch_config(self) -> dict:
            url = self.base_url + "/config"
            if self.module_id is not None:
                url += f"?module={self.module_id}"
            r = requests.get(url)
            data = r.json()
            return data.get("config") or data.get("configurations")

        async def connect_ws(self, max_retries=5, base_delay=1):
            """
            Initialise la connexion WebSocket.
            En cas d'EHOSTUNREACH ou autre OSError, on réessaie
            avec un back‑off exponentiel jusqu'à max_retries tentatives.
            Retourne l'objet ws connecté ou None si échec.
            """
            
            print(f"[ArtineoClient] Connexion WS à {self.ws_url}...")
            
            if self.ws is not None:
                return self.ws

            delay = base_delay
            for attempt in range(1, max_retries + 1):
                try:
                    conn = ws_client.connect(self.ws_url)
                    if ASYNC_WS:
                        self.ws = await conn
                    else:
                        self.ws = conn
                    print(f"[ArtineoClient] WS connectée (tentative {attempt})")
                    return self.ws

                except OSError as e:
                    print(f"[ArtineoClient] Echec WS (tentative {attempt}/{max_retries}) : {e}")
                    # si on est à la dernière tentative, on abandonne
                    if attempt == max_retries:
                        print("[ArtineoClient] Impossible de se connecter au WS, on passe sans WS.")
                        return None
                    # sinon on attend un peu puis on réessaye
                    await asyncio.sleep(delay)
                    delay *= 2  # back‑off exponentiel

            return None


        async def send_ws_json(self, message: dict) -> dict:
            """
            Envoie un JSON sur la WS et attend la réponse.
            Gère les deux APIs (async uwebsockets et sync websocket_client).
            """
            if self.ws is None:
                # pas de WS ouverte, on renvoie un écho minimal
                print("[ArtineoClient] send_ws_json : pas de WS, message ignoré")
                return {}
            
            ws = await self.connect_ws()
            payload = json.dumps(message)
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

        async def send_ws(self, action: str, data) -> dict:
            msg = {
                "module": self.module_id,
                "action": action,
                "data": data
            }
            return await self.send_ws_json(msg)

        def on_message(self, handler):
            """
            Enregistre un callback pour les messages entrants.
            """
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            while True:
                if ASYNC_WS:
                    raw = await ws.recv()
                else:
                    raw = ws.recv()
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
                    # appel synchrone possible
                    self._handler(msg)

        def start_listening(self):
            """
            Lance la boucle d'écoute en tâche de fond.
            """
            try:
                asyncio.create_task(self._listen_loop())
            except Exception as e:
                print("Impossible de démarrer _listen_loop:", e)

        async def set_buffer(self, buffer_data) -> dict:
            """
            Envoie le buffer au serveur via WS.
            """
            return await self.send_ws(ArtineoAction.SET, buffer_data)

        async def get_buffer(self) -> dict:
            """
            Lit le buffer depuis le serveur via WS.
            """
            # action GET ne nécessite pas de champ "request"
            return await self.send_ws(ArtineoAction.GET, None)

        async def close_ws(self):
            if self.ws:
                if ASYNC_WS:
                    await self.ws.close()
                else:
                    self.ws.close()
                self.ws = None

else:
    # CPython / Raspberry Pi
    import asyncio
    import os

    import requests
    import websockets
    from dotenv import load_dotenv

    load_dotenv()

    class ArtineoClient:
        def __init__(self, module_id:int=None, host:str=None, port:str=None):
            host = host or os.getenv("ARTINEO_HOST","127.0.0.1")
            port = port or os.getenv("ARTINEO_PORT","8000")
            self.base_url  = f"http://{host}:{port}"
            self.ws_url    = f"ws://{host}:{port}/ws"
            self.module_id = module_id
            self.ws        = None
            self._handler  = None
            self._listen_task = None

        def fetch_config(self)->dict:
            params={}
            if self.module_id is not None:
                params["module"]=self.module_id
            r = requests.get(f"{self.base_url}/config", params=params)
            r.raise_for_status()
            payload = r.json()
            return payload.get("config") or payload.get("configurations")

        async def connect_ws(self):
            if self.ws is None or self.ws.closed:
                self.ws = await websockets.connect(self.ws_url)
            return self.ws

        async def send_ws_json(self, message:dict)->dict:
            ws = await self.connect_ws()
            await ws.send(json.dumps(message))
            raw = await ws.recv()
            try:
                return json.loads(raw)
            except:
                return {"raw": raw}

        async def send_ws(self, action:str, data)->dict:
            msg = {"module":self.module_id, "action":action, "data":data}
            return await self.send_ws_json(msg)

        def on_message(self, handler):
            self._handler = handler

        async def _listen_loop(self):
            ws = await self.connect_ws()
            async for raw in ws:
                if raw.strip('"')=="ping":
                    await ws.send("pong")
                    continue
                try:
                    msg=json.loads(raw)
                except:
                    msg=raw
                if self._handler:
                    self._handler(msg)

        def start_listening(self):
            if not self._listen_task:
                self._listen_task = asyncio.create_task(self._listen_loop())

        async def set_buffer(self, buffer_data) -> dict:
            return await self.send_ws(ArtineoAction.SET, buffer_data)

        async def get_buffer(self)->dict:
            return await self.send_ws(ArtineoAction.GET, None)

        async def close_ws(self):
            if self.ws and not self.ws.closed:
                await self.ws.close()
            if self._listen_task:
                self._listen_task.cancel()
                self._listen_task = None
