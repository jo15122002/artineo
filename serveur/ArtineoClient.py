# artineo_client.py

import asyncio
import json
import os
from enum import Enum

import requests
import websockets
from dotenv import load_dotenv

# Charge les variables du .env
load_dotenv()

class ArtineoAction(Enum):
    SET = "set"
    GET = "get"
    def __str__(self):
        return self.value

class ArtineoClient:
    def __init__(self, module_id: int = None):
        host = os.getenv("ARTINEO_HOST", "127.0.0.1")
        port = os.getenv("ARTINEO_PORT", "8000")
        self.base_url     = f"http://{host}:{port}"
        self.ws_url       = f"ws://{host}:{port}/ws"
        self.module_id    = module_id
        self.ws           = None
        self._handler     = None
        self._listen_task = None
        
        self.start_listening()

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

    async def send_ws(self, action:ArtineoAction, data:str) -> dict:
        msg = {
            "module": self.module_id,
            "action": action.value,
            "data": data
        }
        return await self.send_ws_json(msg)

    def on_message(self, handler):
        """
        Enregistre une fonction handler(message) -> None
        appelée pour chaque message non-ping reçu.
        """
        self._handler = handler

    async def _listen_loop(self):
        ws = await self.connect_ws()
        try:
            async for raw in ws:
                # Si on reçoit un "ping" brut ou encodé, répondre "pong"
                if raw.strip('"') == "ping":
                    await ws.send("pong")
                    continue

                # Sinon on tente de parser le JSON et on appelle le handler
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
        Lance la boucle d'écoute en tâche de fond.
        """
        if not self._listen_task:
            self._listen_task = asyncio.create_task(self._listen_loop())

    async def close_ws(self):
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None


# Exemple d'utilisation
# if __name__ == "__main__":
#     import asyncio

#     def handle(msg):
#         print("Handler a reçu :", msg)

#     async def main():
#         client = ArtineoClient(module_id=1)
#         print("Config :", client.fetch_config())
#         client.on_message(handle)
#         client.start_listening()

#         # Envoie un ping pour tester
#         await client.send_ws("ping", ArtineoAction.GET)
#         # Attend quelques instants pour voir le "pong"
#         await asyncio.sleep(2)
#         await client.close_ws()

#     asyncio.run(main())
