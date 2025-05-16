import json
import sys
from pathlib import Path
import asyncio
import logging
from typing import Any, Dict, List

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
from ArtineoClient import ArtineoClient, ArtineoAction


class PayloadSender:
    """
    Manages WebSocket connection and sends payloads via ArtineoClient.
    Simplified: handles reconnection and sending only.
    """
    def __init__(
        self,
        client: ArtineoClient,
        reconnect_interval: float = 5.0,
        logger: logging.Logger = None,
    ):
        self.client = client
        self.reconnect_interval = reconnect_interval
        self._lock = asyncio.Lock()
        self.logger = logger or logging.getLogger(__name__)

    async def connect(self) -> None:
        """
        Ensure WebSocket connection is open.
        """
        try:
            await self.client.connect_ws()
            self.client.start_listening()
            self.logger.info("WebSocket connected.")
        except Exception as e:
            self.logger.error("WebSocket connect failed: %s", e)
            await asyncio.sleep(self.reconnect_interval)
            await self.connect()

    async def send(
        self,
        tool_id: str,
        strokes: List[Dict[str, Any]],
        objects: List[Dict[str, Any]],
    ) -> None:
        """
        Send the payload, reconnecting on failure.
        """
        payload = {"module": self.client.module_id, "action": ArtineoAction.SET, "data": {"tool": tool_id, "strokes": strokes, "objects": objects}}
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

    async def close(self) -> None:
        """
        Close WebSocket connection.
        """
        try:
            await self.client.close_ws()
            self.logger.info("WebSocket closed.")
        except Exception as e:
            self.logger.error("Error closing WebSocket: %s", e)
