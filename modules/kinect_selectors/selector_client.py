#!/usr/bin/env python3
"""
selector_client.py

Client de test pour envoyer les ID de boutons via WebSocket
utilisant ArtineoClient.py.
"""

import asyncio
import json
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
from ArtineoClient import ArtineoClient, ArtineoAction

async def main():
    # Identifiant du "module" qui gérera le filtre couleur côté front
    module_id = 4

    # Instancie et démarre le client WebSocket
    client = ArtineoClient(module_id=module_id, host="localhost", port=8000)
    client.start()
    print(f"[Artineo] Client démarré pour le module {module_id}.")
    print("Appuyez sur un chiffre de 1 à 6 pour simuler un bouton, 'q' pour quitter.")

    loop = asyncio.get_event_loop()
    try:
        while True:
            # Lecture non bloquante de l'entrée utilisateur
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            key = line.strip()
            if key.lower() == 'q':
                break

            if key in [str(i) for i in range(1, 3)]:
                button_id = int(key)
                # Prépare le message WS selon votre protocole
                payload = {
                    "module": module_id,
                    "action": ArtineoAction.SET,
                    "data": { "button": button_id }
                }
                client.send_ws(json.dumps(payload))
                print(f"[Artineo] Bouton {button_id} envoyé.")
            else:
                print("[Artineo] Entrée invalide : tapez 1-2 ou 'q'.")
    except KeyboardInterrupt:
        pass

    print("[Artineo] Arrêt du client WebSocket…")
    await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
