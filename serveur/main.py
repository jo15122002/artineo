import asyncio
import json
import os
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# --------------------------------------------------
# Configuration des endpoints REST existants
# --------------------------------------------------

CONFIG_DIR = "configs"

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
    # pas de module spécifié : retourne toutes les config
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

@app.get("/history")
async def get_history(): #TODO later on fera de l'historisation
    # stub pour l’historique
    return {"historique": []}

# --------------------------------------------------
# Gestion des connexions WebSocket
# --------------------------------------------------

class ConnectionManager:
    def __init__(self):
        # map module_id -> websocket
        self.active: Dict[int, WebSocket] = {}
        # map module_id -> last pong reçu (bool)
        self._last_pong: Dict[int, bool] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()

    def register(self, module_id: int, ws: WebSocket):
        # enregistre / met à jour le ws pour ce module
        self.active[module_id] = ws

    def disconnect(self, ws: WebSocket):
        # supprime toute entrée pointant vers ce ws
        to_remove = [mid for mid, socket in self.active.items()
                     if socket is ws]
        for mid in to_remove:
            del self.active[mid]

    def clear_pongs(self):
        # initialise à False pour tous les modules connus
        for mid in self.active.keys():
            self._last_pong[mid] = False

    def record_pong(self, module_id: int):
        self._last_pong[module_id] = True

    async def broadcast_ping(self):
        # envoie "ping" à tous les ws
        for ws in list(self.active.values()):
            try:
                await ws.send_text("ping")
            except:
                # ignore les erreurs d’envoi
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()

            # essaie de parser du JSON pour identifier le module
            try:
                msg = json.loads(raw)
                module_id = msg.get("module")
                if isinstance(module_id, int):
                    manager.register(module_id, ws)
                # acknowledgement JSON
                await ws.send_text(f"ACK:{json.dumps(msg)}")
                continue
            except json.JSONDecodeError:
                pass

            # message brut
            if raw == "ping":
                # si client envoie un ping, on répond pong
                await ws.send_text("pong")
            elif raw == "pong":
                # enregistre le pong pour ce module
                # on identifie le module via le mapping actif
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
    """
    Envoie 'ping' à tous les modules connectés et
    attend 1 seconde, puis renvoie pour chacun un statut alive/dead.
    """
    manager.clear_pongs()
    # envoi des pings
    await manager.broadcast_ping()
    # temps pour laisser les clients répondre
    await asyncio.sleep(1)

    # construit le résultat
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
    <head>
        <title>Test WebSocket</title>
    </head>
    <body>
        <h1>Test de connexion WebSocket</h1>
        <input id="messageInput" type="text" placeholder="Tapez un message..."/>
        <button onclick="sendMessage()">Envoyer</button>
        <ul id="messages">
        </ul>
        <script>
            const ws = new WebSocket("ws://192.168.0.180:8000/ws");
            ws.onmessage = function(event) {
                const messages = document.getElementById('messages');
                let message = document.createElement('li');
                message.textContent = event.data;
                messages.appendChild(message);
            };
            function sendMessage() {
                const input = document.getElementById("messageInput");
                ws.send(input.value);
                input.value = "";
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)