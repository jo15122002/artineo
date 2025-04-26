import asyncio
import json
import os
from typing import Dict

from fastapi import (Body, FastAPI, HTTPException, Query, WebSocket,
                     WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# Autoriser les requêtes CORS (Cross-Origin Resource Sharing)
# pour permettre aux clients d'accéder à l'API depuis d'autres origines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------------------------------------
# Configuration des endpoints REST existants
# --------------------------------------------------

CONFIG_DIR = "configs"

# buffer global (un dict par module_id)
buffer: Dict[int, dict] = {1: {}, 2: {}, 3: {}, 4: {}}

@app.get("/config")
async def get_config(module: int = None):
    if module is not None:
        file_path = os.path.join(CONFIG_DIR, f"module{module}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    return {"config": json.load(f)}
            except Exception as e:
                raise HTTPException(status_code=500,
                                    detail=f"Erreur lecture fichier: {e}")
        else:
            raise HTTPException(status_code=404,
                                detail="Fichier de config introuvable")
    all_configs = {}
    try:
        for name in os.listdir(CONFIG_DIR):
            if name.endswith(".json"):
                with open(os.path.join(CONFIG_DIR, name), "r") as f:
                    all_configs[name] = json.load(f)
        return {"configurations": all_configs}
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Erreur lecture configurations: {e}")


@app.post("/config")
async def update_config(
    module: int = Query(..., description="ID du module à configurer"),
    payload: dict = Body(..., description="Clés à mettre à jour dans la config")
):
    """
    Met à jour partiellement le fichier de config module{module}.json
    en écrasant uniquement les clés présentes dans `payload`.
    """
    file_path = os.path.join(CONFIG_DIR, f"module{module}.json")
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Charger la config existante (ou créer un dict vide)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lecture config: {e}")
    else:
        config = {}

    # Fusionner : n'écrase que les clés fournies
    config.update(payload)

    # Sauvegarder
    try:
        with open(file_path, "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur écriture config: {e}")

    return JSONResponse(status_code=200, content={"config": config})

@app.get("/history")
async def get_history():  # TODO historisation future
    return {"historique": []}


# --------------------------------------------------
# Gestion des connexions WebSocket
# --------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, WebSocket] = {}
        self._last_pong: Dict[int, bool] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()

    def register(self, module_id: int, ws: WebSocket):
        self.active[module_id] = ws

    def disconnect(self, ws: WebSocket):
        to_remove = [mid for mid, socket in self.active.items() if socket is ws]
        for mid in to_remove:
            del self.active[mid]

    def clear_pongs(self):
        for mid in self.active.keys():
            self._last_pong[mid] = False

    def record_pong(self, module_id: int):
        self._last_pong[module_id] = True

    async def broadcast_ping(self):
        for ws in list(self.active.values()):
            try:
                await ws.send_text("ping")
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()

            # Tentative de parsing JSON
            try:
                msg = json.loads(raw)
                module_id = msg.get("module")
                action = msg.get("action")
                # Enregistrement de la connexion si module_id valide
                if isinstance(module_id, int):
                    manager.register(module_id, ws)

                # --- traitement du buffer ---
                # set_buffer
                if action == "set" and "buffer" in msg:
                    buffer[module_id] = msg["buffer"]
                    await ws.send_text(json.dumps({
                        "status": "ok",
                        "action": "set_buffer",
                        "module": module_id
                    }))
                    continue

                # get_buffer
                if action == "get":
                    buf = buffer.get(module_id, {})
                    # Envoi du buffer au client
                    await ws.send_text(json.dumps({
                        "action": "get_buffer",
                        "module": module_id,
                        "buffer": buf
                    }))
                    continue

                # Ack pour tout autre JSON
                await ws.send_text(f"ACK:{json.dumps(msg)}")
                continue

            except json.JSONDecodeError:
                pass

            # message brut
            if raw == "ping":
                await ws.send_text("pong")
            elif raw == "pong":
                entry = [(mid, socket) for mid, socket in manager.active.items()
                         if socket is ws]
                if entry:
                    mid, _ = entry[0]
                    manager.record_pong(mid)
            else:
                # echo pour tout autre texte
                await ws.send_text(f"ECHO:{raw}")

    except WebSocketDisconnect:
        manager.disconnect(ws)

# --------------------------------------------------
# Health check étendu
# --------------------------------------------------

@app.get("/hc")
async def health_check():
    manager.clear_pongs()
    await manager.broadcast_ping()
    await asyncio.sleep(1)

    statuses = {
        module_id: ("alive" if manager._last_pong.get(module_id) else "dead")
        for module_id in manager.active.keys()
    }
    return JSONResponse(content={"modules": statuses})


# --------------------------------------------------
# Page de test WebSocket (ne pas modifier)
# --------------------------------------------------

html = """
<!DOCTYPE html>
<html>
    <head><title>Test WebSocket</title></head>
    <body>
        <h1>WebSocket Test</h1>
        <div>
            <h2>Envoyer un message brut</h2>
            <input id="inp" type="text" placeholder="message..."/>
            <button onclick="send()">Envoyer</button>
        </div>
        <div>
            <h2>Récupérer un buffer</h2>
            <label for="moduleInput">Module ID : </label>
            <input id="moduleInput" type="number" value="1" min="1"/>
            <button onclick="getBuffer()">Get Buffer</button>
        </div>
        <h2>Logs</h2>
        <ul id="out"></ul>
        <h2>Buffers reçus</h2>
        <ul id="bufferList"></ul>
        <script>
            const ws = new WebSocket("ws://192.168.0.180:8000/ws");
            ws.onmessage = e => {
                const data = e.data;
                // Essaie de parser en JSON
                try {
                    const obj = JSON.parse(data);
                    // Si c'est la réponse à get_buffer
                    if (obj.action === "get_buffer") {
                        const bufList = document.getElementById("bufferList");
                        const li = document.createElement("li");
                        li.textContent = `Module ${obj.module} buffer : ${JSON.stringify(obj.buffer)}`;
                        bufList.appendChild(li);
                        return;
                    }
                } catch(_) {
                    // not JSON or autre action
                }
                // Log normal
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
                const msg = JSON.stringify({
                    module: moduleId,
                    action: "get",
                    request: "buffer"
                });
                ws.send(msg);
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)