import asyncio
import json
import mimetypes
import os
import time
from contextlib import suppress
from typing import Dict
from collections import deque

from fastapi import (Body, FastAPI, HTTPException, Query, WebSocket,
                     WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Autoriser CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.mount(
    "/assets",
    StaticFiles(directory="assets"),
    name="assets"
)

# --------------------------------------------------
# Configuration des endpoints REST
# --------------------------------------------------

CONFIG_DIR = "configs"
DEFAULT_BUFFER_FILE = "assets/default_buffer.json"

# buffer global (un dict par module_id)
buffer: Dict[int, dict] = {1: {}, 2: {}, 3: {}, 4: {}}


@app.on_event("startup")
async def load_default_buffer():
    """
    Charge au démarrage le default_buffer.json dans la variable `buffer`.
    Si le fichier n'existe pas ou est invalide, on conserve le buffer vide par défaut.
    """
    global buffer
    if os.path.exists(DEFAULT_BUFFER_FILE):
        try:
            with open(DEFAULT_BUFFER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # convertir les clés en int si besoin
            buffer = {int(k): v for k, v in data.items()}
            print(f"[startup] default buffer chargé pour modules: {list(buffer.keys())}")
        except Exception as e:
            print(f"[startup] Erreur en chargeant {DEFAULT_BUFFER_FILE}: {e}")
    else:
        print(f"[startup] Aucun default buffer ({DEFAULT_BUFFER_FILE}) trouvé, buffer vide.")


@app.get("/config")
async def get_config(module: int = None):
    if module is not None:
        file_path = os.path.join(CONFIG_DIR, f"module{module}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Fichier de config introuvable")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return JSONResponse(
                content={"config": cfg},
                media_type="application/json; charset=utf-8"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lecture fichier: {e}")
    all_configs = {}
    try:
        for name in os.listdir(CONFIG_DIR):
            if name.endswith(".json"):
                with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
                    all_configs[name] = json.load(f)
        return JSONResponse(
            content={"configurations": all_configs},
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture configurations: {e}")


@app.post("/config")
async def update_config(
    module: int = Query(..., description="ID du module à configurer"),
    payload: dict = Body(..., description="Clés à mettre à jour dans la config")
):
    file_path = os.path.join(CONFIG_DIR, f"module{module}.json")
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lecture config: {e}")
    else:
        config = {}

    config.update(payload)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur écriture config: {e}")

    return JSONResponse(
        status_code=200,
        content={"config": config},
        media_type="application/json; charset=utf-8"
    )


@app.get("/history")
async def get_history():
    return JSONResponse(
        content={"historique": []},
        media_type="application/json; charset=utf-8"
    )
    
@app.get("/buffer")
async def get_buffer(module: int = Query(..., description="ID du module")):
    """
    Renvoie la dernière donnée du buffer pour le module donné.
    """
    if module not in buffer:
        raise HTTPException(status_code=404, detail=f"Module {module} introuvable")
    return JSONResponse(
        content={"buffer": buffer[module]},
        media_type="application/json; charset=utf-8"
    )
    
@app.get("/getAsset")
async def get_asset(
    module: int = Query(..., description="Numéro du module"),
    path: str  = Query(..., description="Chemin relatif vers l'asset dans le dossier du module")
):
    """
    Renvoie le fichier situé dans assets/module{module}/{path}
    Exemples d'appel :
      GET /getAsset?module=3&path=1.png
      GET /getAsset?module=3&path=blob1.svg
    """
    base_dir = os.path.abspath(os.path.join("assets", f"module{module}"))
    normalized = os.path.normpath(path)
    full_path = os.path.abspath(os.path.join(base_dir, normalized))

    if not full_path.startswith(base_dir + os.sep):
        raise HTTPException(400, "Chemin invalide")
    if not os.path.isfile(full_path):
        raise HTTPException(404, "Asset non trouvé")

    media_type, _ = mimetypes.guess_type(full_path)
    return FileResponse(full_path, media_type=media_type)


# --------------------------------------------------
# Gestion des connexions WebSocket
# --------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, WebSocket] = {}
        # on stocke pour chaque module le timestamp du dernier 'pong'
        self._last_pong_time: Dict[int, float] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()

    def register(self, module_id: int, ws: WebSocket):
        self.active[module_id] = ws
        # initialiser le timestamp dès la connexion
        self._last_pong_time[module_id] = time.time()

    def disconnect(self, ws: WebSocket):
        to_remove = [mid for mid, socket in self.active.items() if socket is ws]
        for mid in to_remove:
            del self.active[mid]
            del self._last_pong_time[mid]

    async def broadcast_ping(self):
        """Envoie un 'ping' à tous les clients enregistrés."""
        for ws in list(self.active.values()):
            with suppress(Exception):
                await ws.send_text("ping")

    def record_pong(self, module_id: int):
        """Appelé sur réception d'un 'pong' pour mettre à jour le timestamp."""
        self._last_pong_time[module_id] = time.time()

manager = ConnectionManager()

diff_queues: Dict[int, deque] = {
    1: deque(), 2: deque(), 3: deque(), 4: deque()
}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            print(f"Message reçu : {raw}")

            try:
                msg = json.loads(raw)
                recv_ts = int(time.time() * 1000)
                sent_ts = msg.get("_ts_client")
                if sent_ts is not None:
                    print(f"⏱ latence réseau ~ {recv_ts - sent_ts} ms", flush=True)
                module_id = msg.get("module")
                action = msg.get("action")
                if isinstance(module_id, int):
                    manager.register(module_id, ws)

                if action == "set" and "data" in msg:
                    # stocke le diff reçu
                    diff_queues[module_id].append(msg["data"])
                    # conserve l'ancien buffer complet si besoin ailleurs
                    resp = {"status": "ok", "action": "set_buffer", "module": module_id}
                    await ws.send_text(json.dumps(resp, ensure_ascii=False))
                    continue

                if action == "get":
                    # si on a des diffs en attente, on envoie le plus ancien
                    if diff_queues[module_id]:
                        payload = diff_queues[module_id].popleft()
                    else:
                        # aucune mise à jour : payload vide
                        payload = {}
                    resp = {
                        "action": "get_buffer",
                        "module": module_id,
                        "buffer": payload
                    }
                    await ws.send_text(json.dumps(resp, ensure_ascii=False))
                    continue

                ack = {"action": "ack", "data": msg}
                await ws.send_text(json.dumps(ack, ensure_ascii=False))
                continue

            except json.JSONDecodeError:
                pass

            if raw == "ping":
                await ws.send_text("pong")
            elif raw == "pong":
                entries = [(mid, sock) for mid, sock in manager.active.items() if sock is ws]
                if entries:
                    mid, _ = entries[0]
                    manager.record_pong(mid)
            else:
                await ws.send_text(f"ECHO:{raw}")

    except WebSocketDisconnect:
        manager.disconnect(ws)

# --------------------------------------------------
# Health check étendu
# --------------------------------------------------

@app.get("/hc")
async def health_check():
    """
    Renvoie pour chaque module un statut 'alive' ou 'dead'
    selon la fraîcheur du dernier 'pong' reçu (<5s).
    """
    THRESHOLD = 9.0  # secondes
    now = time.time()
    statuses: Dict[int, str] = {}

    # Inspecter chaque module encore connecté
    for module_id in manager.active.keys():
        last = manager._last_pong_time.get(module_id, 0)
        delta = now - last
        statuses[module_id] = "alive" if delta <= THRESHOLD else "dead"

    return JSONResponse(
        content={"modules": statuses},
        media_type="application/json; charset=utf-8"
    )

# --------------------------------------------------
# Page de test WebSocket + UTF-8
# --------------------------------------------------

html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Test WebSocket</title>
</head>
<body>
  <h1>WebSocket Test</h1>
  <div>
    <h2>Envoyer un message brut</h2>
    <input id="inp" type="text" placeholder="message…"/>
    <button onclick="send()">Envoyer</button>
  </div>
  <div>
    <h2>Récupérer un buffer</h2>
    <label>Module ID :</label>
    <input id="moduleInput" type="number" value="1" min="1"/>
    <button onclick="getBuffer()">Get Buffer</button>
  </div>
  <h2>Logs</h2>
  <ul id="out"></ul>
  <h2>Buffers reçus</h2>
  <ul id="bufferList"></ul>
  <script>
    const ws = new WebSocket("ws://artineo.local:8000/ws");
    ws.onmessage = e => {
      const data = e.data;
      try {
        const obj = JSON.parse(data);
        if (obj.action === "get_buffer") {
          const bufList = document.getElementById("bufferList");
          const li = document.createElement("li");
          li.textContent = `Module ${obj.module} buffer : ${JSON.stringify(obj.buffer)}`;
          bufList.appendChild(li);
          return;
        }
      } catch(_) {}
      const li = document.createElement("li");
      li.textContent = data;
      document.getElementById("out").append(li);
    };
    function send() {
      const v = document.getElementById("inp").value;
      ws.send(v);
      document.getElementById("inp").value = "";
    }
    function getBuffer() {
      const moduleId = parseInt(document.getElementById("moduleInput").value) || 0;
      const msg = JSON.stringify({module: moduleId, action: "get", request: "buffer"});
      ws.send(msg);
    }
  </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html, media_type="text/html; charset=utf-8")