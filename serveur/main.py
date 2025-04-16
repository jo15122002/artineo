import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# --------------------------
# Endpoints REST
# --------------------------

# Dossier contenant les fichiers de configuration
CONFIG_DIR = "configs"

@app.get("/config")
async def get_config(module: int = None):
    if module is not None:
        file_path = os.path.join(CONFIG_DIR, f"module{module}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    config_data = json.load(f)
                return JSONResponse(content={"config": config_data})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture du fichier: {e}")
        else:
            raise HTTPException(status_code=404, detail="Fichier de configuration du module introuvable")
    else:
        # Si aucun module n'est spécifié, parcourir tous les fichiers JSON du dossier
        all_configs = {}
        try:
            for file_name in os.listdir(CONFIG_DIR):
                if file_name.endswith(".json"):
                    full_path = os.path.join(CONFIG_DIR, file_name)
                    with open(full_path, "r") as f:
                        config_data = json.load(f)
                    # Par convention, le nom de fichier est utilisé comme clé (par ex. "module1.json")
                    all_configs[file_name] = config_data
            return JSONResponse(content={"configurations": all_configs})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture des configurations: {e}")


@app.get("/history")
async def get_history():
    """
    Endpoint pour récupérer l’historique des données.
    Dans un premier temps, cela peut renvoyer une liste vide ou fictive.
    """
    # Ici, vous pourriez connecter à une base de données ou lire un fichier JSON
    history_data = []
    return {"historique": history_data}

# --------------------------
# Gestion des connexions WebSocket
# --------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Route websocket pour gérer les connexions en temps réel.
    Ce endpoint reçoit les données des modules (Kinect, RFID, joysticks, etc.)
    et peut renvoyer des accusés de réception.
    """
    await websocket.accept()
    print("Client connecté via WebSocket.")
    
    try:
        while True:
            data = await websocket.receive_text()
            # Traitement des données reçues
            print(f"Message reçu : {data}")

            # Ici, vous pouvez appeler vos algorithmes de traitement (OpenCV, logique RFID, etc.)
            # Pour l’instant, on renvoie simplement une confirmation.
            response = f"Message '{data}' reçu avec succès."
            await websocket.send_text(response)
    except WebSocketDisconnect:
        print("Client déconnecté.")

# --------------------------
# Optionnel: Page de test pour WebSocket
# --------------------------

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
            const ws = new WebSocket("ws://localhost:8000/ws");
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