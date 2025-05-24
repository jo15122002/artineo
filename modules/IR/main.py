import asyncio
import json
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

# On ajoute ../../serveur au path pour importer ArtineoClient
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


def preprocess(gray):
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.morphologyEx(blur, cv2.MORPH_OPEN, kernel)


def find_brightest_circle(gray, clean):
    circles = cv2.HoughCircles(
        clean,
        cv2.HOUGH_GRADIENT,
        dp=2.0,
        minDist=80,
        param1=100,
        param2=30,
        minRadius=15,
        maxRadius=80
    )
    if circles is None:
        return None

    candidates = np.round(circles[0]).astype(int)
    best = None
    best_mean = -1.0

    for x, y, r in candidates:
        mask = np.zeros_like(gray, dtype=np.uint8)
        cv2.circle(mask, (x, y), r, 255, thickness=-1)
        mean_val = cv2.mean(gray, mask=mask)[0]
        if mean_val > best_mean:
            best_mean = mean_val
            best = (int(x), int(y), int(r))

    return best


def main():
    width, height = 320, 240
    frame_size = width * height * 3  # bgr24

    # 1) Initialisation du client WS
    client = ArtineoClient(module_id=1)

    # 2) Démarrage du handler WS dans un thread avec sa propre boucle
    def _ws_loop():
        asyncio.run(client._ws_handler())
    threading.Thread(target=_ws_loop, daemon=True).start()
    print("WebSocket handler démarré dans un thread dédié.")

    # 3) (facultatif) callback sur messages reçus
    client.on_message = lambda msg: print("Message reçu :", msg)

    # 4) Fonction d'envoi + mesure de latence
    def safe_send(action, data):
        # 4a) Préparation du message
        ts = time.time() * 1000
        payload = {
            "module": client.module_id,
            "action": action,
            "data": data,
            "_ts_client": ts
        }
        msg = json.dumps(payload)
        client.send_ws(msg)

        # 4b) Mesure de la latence en parallèle
        def _measure():
            try:
                lat = asyncio.run(client.measure_latency())
                print(f"⏱ latence WS RTT ~ {lat:.1f} ms")
            except Exception as e:
                print(f"[WARN] échec mesure latence : {e}")
        threading.Thread(target=_measure, daemon=True).start()

    # 5) Préparation de la fenêtre d'affichage
    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)

    # 6) Boucle de lecture du flux caméra
    while True:
        raw = sys.stdin.buffer.read(frame_size)
        if len(raw) < frame_size:
            break  # fin du flux
        frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clean = preprocess(gray)

        best = find_brightest_circle(gray, clean)
        if best:
            x, y, r = best
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            safe_send(ArtineoAction.SET, {
                "x": x,
                "y": y,
                "diameter": r * 2
            })

        cv2.imshow("Flux de la caméra", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    print("Fin du module 1, le thread WebSocket sera tué automatiquement.")


if __name__ == "__main__":
    main()