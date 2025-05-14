import asyncio
import json
import mimetypes
import os
from typing import Dict

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
        print(f"[ping] Envoi de ping à {len(self.active)} modules")
        print(f"[ping] Modules actifs: {list(self.active)}")
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
            print(f"Message reçu : {raw}")

            try:
                msg = json.loads(raw)
                module_id = msg.get("module")
                action = msg.get("action")
                if isinstance(module_id, int):
                    manager.register(module_id, ws)

                if action == "set" and "data" in msg:
                    buffer[module_id] = msg["data"]
                    resp = {"status": "ok", "action": "set_buffer", "module": module_id}
                    await ws.send_text(json.dumps(resp, ensure_ascii=False))
                    continue

                if action == "get":
                    buf = buffer[module_id]
                    resp = {"action": "get_buffer", "module": module_id, "buffer": buf}
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
    manager.clear_pongs()
    await manager.broadcast_ping()
    await asyncio.sleep(1)
    statuses = {
        mid: ("alive" if manager._last_pong.get(mid) else "dead")
        for mid in manager.active.keys()
    }
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