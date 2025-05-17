# backend/payload_sender.py
import json
import asyncio
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parent
        .joinpath("..", "..", "serveur", "back")
        .resolve()
    )
)

from ArtineoClient import ArtineoAction

class PayloadSender:
    def __init__(self, client, reconnect_interval=5.0, logger=None):
        self.client = client
        self.reconnect_interval = reconnect_interval
        self._lock = asyncio.Lock()
        self.logger = logger or __import__('logging').getLogger(__name__)
        self._ws = None

    async def connect(self):
        """ Ouvre et conserve la connexion WS. """
        while True:
            try:
                await self.client.connect_ws()
                self.client.start_listening()
                self._ws = await self.client.connect_ws()
                self.logger.info("WebSocket connected.")
                return
            except Exception as e:
                self.logger.error("WS connect failed: %s. Retry in %.1fs", e, self.reconnect_interval)
                await asyncio.sleep(self.reconnect_interval)

    async def close(self):
        try:
            await self.client.close_ws()
            self.logger.info("WebSocket closed.")
        except Exception as e:
            self.logger.error("Error closing WebSocket: %s", e)

    async def send_update(self, *, new_strokes, remove_strokes, new_objects, remove_objects):
        """
        Envoie uniquement les diffs au front.
        """
        payload = {
            "module": self.client.module_id,
            "action": ArtineoAction.SET,
            "data": {
                "newStrokes":  new_strokes,
                "removeStrokes": remove_strokes,
                "newObjects":  new_objects,
                "removeObjects": remove_objects,
            }
        }
        async with self._lock:
            try:
                ws = await self.client.connect_ws()
                await ws.send(json.dumps(payload))
                self.logger.debug("Payload sent (no recv): %s", payload)
            except Exception as e:
                self.logger.warning("Send failed (%s), reconnecting...", e)
                await self.connect()
                try:
                    ws = await self.client.connect_ws()
                    await ws.send(json.dumps(payload))
                    self.logger.debug("Payload resent: %s", payload)
                except Exception as e2:
                    self.logger.error("Payload resend failed: %s", e2)
