# serveur/back/ArtineoClient.py

import asyncio
import json
import os
import random
import time
from contextlib import suppress
from typing import Any, Callable

import requests
import websockets
from dotenv import load_dotenv
from websockets.exceptions import InvalidMessage  # <— ajouté

load_dotenv()

class ArtineoAction:
    SET = "set"
    GET = "get"

class ArtineoClient:
    def __init__(
        self,
        module_id: str = None,
        host: str = None,
        port: str = None,
        http_retries: int = 3,
        http_backoff: float = 0.5,
        http_timeout: float = 5,
        ws_retries: int = 5,
        ws_backoff: float = 1.0,
        ws_ping_interval: float = 20.0,
    ):
        # --- HTTP setup ---
        host = host or "artineo.local"
        port = port or "8000"
        self.module_id     = module_id
        self.base_url      = f"http://{host}:{port}"
        self.ws_url        = f"ws://{host}:{port}/ws"
        self.http_retries  = http_retries
        self.http_backoff  = http_backoff
        self.http_timeout  = http_timeout

        # --- WebSocket resilience parameters ---
        self.ws_retries       = ws_retries
        self.ws_backoff       = ws_backoff
        self.ws_ping_interval = ws_ping_interval

        # queue pour messages sortants
        self._send_queue = asyncio.Queue()
        # gestion des tâches asyncio
        self._ws_task    = None
        self._stop_event = asyncio.Event()
        # callback user à chaque message reçu
        self.on_message: Callable[[Any], None] = lambda msg: None

    # ----- HTTP layer -----
    def _http_request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        last_exc = None
        delay = self.http_backoff

        for attempt in range(1, self.http_retries + 1):
            try:
                resp = requests.request(method, url, timeout=self.http_timeout, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as e:
                last_exc = e
                if attempt < self.http_retries:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise RuntimeError(
                        f"HTTP {method} {url} échoué après {attempt} tentatives"
                    ) from last_exc

    def fetch_config(self):
        params = {}
        if self.module_id is not None:
            params["module"] = self.module_id
        data = self._http_request("GET", "/config", params=params)
        return data.get("config") or data.get("configurations")

    def set_config(self, new_config: dict):
        params = {"module": self.module_id}
        return self._http_request("POST", "/config", params=params, json=new_config)

    # ----- WebSocket layer -----
    async def _ws_handler(self):
        """Loop principal : connecte, relaie, reconnecte."""
        attempt = 0
        backoff = self.ws_backoff

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url, ping_interval=None) as ws:
                    attempt = 0
                    backoff = self.ws_backoff

                    sender_task = asyncio.create_task(self._ws_sender(ws))
                    ping_task   = asyncio.create_task(self._ws_heartbeat(ws))

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            msg = raw
                        self.on_message(msg)

                    sender_task.cancel()
                    ping_task.cancel()

            except (websockets.ConnectionClosed, OSError, InvalidMessage) as exc:
                attempt += 1
                print(f"[ArtineoClient] WS déconnecté ({exc}), essai {attempt}/{self.ws_retries}")
                if attempt > self.ws_retries:
                    raise RuntimeError("Impossible de reconnecter le WebSocket") from exc
                # backoff exponentiel + jitter
                jitter = 1 + 0.1 * (2 * random.random() - 1)
                await asyncio.sleep(backoff * jitter)
                backoff *= 2

            except asyncio.CancelledError:
                break

    async def _ws_sender(self, ws):
        """Envoie tous les messages mis en file."""
        while True:
            msg = await self._send_queue.get()
            try:
                await ws.send(msg)
            except Exception:
                print(f"[ArtineoClient] Erreur d'envoi WS : {msg}")
                await self._send_queue.put(msg)
                raise

    async def _ws_heartbeat(self, ws):
        """Ping périodique pour maintenir la connexion."""
        while True:
            try:
                await ws.ping()
            except Exception:
                raise
            await asyncio.sleep(self.ws_ping_interval)

    def start(self):
        """Démarre la supervision WebSocket."""
        if self._ws_task is None or self._ws_task.done():
            self._stop_event.clear()
            self._ws_task = asyncio.create_task(self._ws_handler())

    async def stop(self):
        """Arrête proprement WebSocket et tâches associées."""
        self._stop_event.set()
        if self._ws_task:
            self._ws_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ws_task

    def send_ws(self, message: str):
        """Queue un message pour envoi via le WS (même si hors-ligne)."""
        print(f"[ArtineoClient] Envoi WS : {message}")
        self._send_queue.put_nowait(message)