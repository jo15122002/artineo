# backend/payload_sender.py
import logging
from typing import Any, Dict, List, Optional
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
        logger: Optional[logging.Logger] = None,
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
        new_strokes: Optional[List[Dict[str, Any]]] = None,
        remove_strokes: Optional[List[str]] = None,
        new_objects: Optional[List[Dict[str, Any]]] = None,
        remove_objects: Optional[List[str]] = None,
        new_backgrounds: Optional[List[Dict[str, Any]]] = None,
        remove_backgrounds: Optional[List[str]] = None,
        button: Optional[int] = None,
    ) -> None:
        """
        Construit le message SET et l'enqueue pour envoi.
        Les arguments new_backgrounds, remove_backgrounds et button sont facultatifs.
        """
        # éviter les None
        new_strokes = new_strokes or []
        remove_strokes = remove_strokes or []
        new_objects = new_objects or []
        remove_objects = remove_objects or []

        data: Dict[str, Any] = {
            "newStrokes":    new_strokes,
            "removeStrokes": remove_strokes,
            "newObjects":    new_objects,
            "removeObjects": remove_objects,
        }

        if new_backgrounds is not None:
            data["newBackgrounds"] = new_backgrounds
        if remove_backgrounds is not None:
            data["removeBackgrounds"] = remove_backgrounds
        if button is not None:
            data["button"] = button

        payload = {
            "module": self.client.module_id,
            "action": ArtineoAction.SET,
            "data": data
        }

        msg = json.dumps(payload, ensure_ascii=False)
        # on protège l'enqueue si plusieurs coroutines appellent en même temps
        async with self._lock:
            try:
                self.client.send_ws(msg)
                # self.logger.debug("Enqueued WS message: %s", payload)
            except Exception as e:
                self.logger.error("Failed to enqueue WS message: %s", e)
