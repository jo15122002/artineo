# backend/payload_sender.py
import logging
from typing import Any, Dict, List
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

from ArtineoClient import ArtineoAction, ArtineoClient

class PayloadSender:
    """
    Enqueue les messages JSON sur le ArtineoClient WS et gère
    proprement le démarrage/arrêt de la connexion.
    """
    def __init__(
        self,
        client: ArtineoClient,
        logger: logging.Logger = None,
    ):
        self.client = client
        self.logger = logger or logging.getLogger(__name__)
        self._lock = asyncio.Lock()

    def start(self) -> None:
        """Démarre la tâche WebSocket en arrière-plan."""
        self.client.start()
        self.logger.info("ArtineoClient WS handler started.")

    async def stop(self) -> None:
        """Arrête proprement le WebSocket."""
        await self.client.stop()
        self.logger.info("ArtineoClient WS handler stopped.")

    async def send_update(
        self,
        new_strokes: List[Dict[str, Any]],
        remove_strokes: List[str],
        new_objects: List[Dict[str, Any]],
        remove_objects: List[str],
    ) -> None:
        """
        Construit le message SET et l'enqueue pour envoi.
        """
        payload = {
            "module": self.client.module_id,
            "action": ArtineoAction.SET,
            "data": {
                "newStrokes":    new_strokes,
                "removeStrokes": remove_strokes,
                "newObjects":    new_objects,
                "removeObjects": remove_objects,
            }
        }
        msg = json.dumps(payload, ensure_ascii=False)
        # On protège l'enqueue au cas où plusieurs coroutines appellent en même temps
        async with self._lock:
            try:
                self.client.send_ws(msg)
                self.logger.debug("Enqueued WS message: %s", payload)
            except Exception as e:
                self.logger.error("Failed to enqueue WS message: %s", e)
