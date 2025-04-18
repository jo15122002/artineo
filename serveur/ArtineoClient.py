# artineo_client.py

import asyncio
import os

import requests
import websockets
from dotenv import load_dotenv

# Charge les variables du .env
load_dotenv()

class ArtineoClient:
    def __init__(self, module_id: int = None):
        """
        Lit ARTINEO_HOST et ARTINEO_PORT depuis l'env,
        puis construit les URLs HTTP et WS.
        """
        host = os.getenv("ARTINEO_HOST", "127.0.0.1")
        port = os.getenv("ARTINEO_PORT", "8000")

        self.base_url = f"http://{host}:{port}"
        self.ws_url   = f"ws://{host}:{port}/ws"
        self.module_id = module_id
        self.ws = None

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

    async def send_ws(self, message: str) -> str:
        ws = await self.connect_ws()
        await ws.send(message)
        return await ws.recv()

    async def close_ws(self):
        if self.ws:
            await self.ws.close()
            self.ws = None


# Exemple d'utilisation
if __name__ == "__main__":
    client = ArtineoClient(module_id=1)
    config = client.fetch_config()
    print("Config reçue :", config)

    async def run():
        réponse = await client.send_ws("Salut module 1 !")
        print("Réponse WS :", réponse)
        await client.close_ws()

    asyncio.run(run())
