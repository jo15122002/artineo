from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# --------------------------
# Endpoints REST
# --------------------------

@app.get("/config")
async def get_config():
    """
    Endpoint pour récupérer la configuration du système.
    Par exemple, retour d’un dictionnaire avec des paramètres.
    """
    config = {
        "module_kinect": {"activation": True, "seuil": 0.5},
        "module_rfid": {"activation": True},
        "joysticks": {"sensibilite": 1.0}
    }
    return config

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
