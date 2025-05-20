import asyncio
import json
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

# On ajoute ../../serveur/back au path pour importer ArtineoClient
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

    # 1) Initialisation du client WS + fetch de la config
    client = ArtineoClient(module_id=1)
    try:
        cfg = client.fetch_config() or {}
        fps = float(cfg.get("fps", 10))  # default 10 fps si absent
    except Exception as e:
        print(f"[WARN] Impossible de récupérer la config, on prend fps=10 : {e}")
        fps = 10.0

    interval = 1.0 / fps
    print(f"[INFO] FPS configuré = {fps}  → intervalle minimal = {interval:.3f}s")

    # 2) Lancement du handler WebSocket dans un thread séparé
    def run_ws_loop():
        asyncio.run(client._ws_handler())

    ws_thread = threading.Thread(target=run_ws_loop, daemon=True)
    ws_thread.start()
    print("WebSocket handler démarré dans un thread dédié.")

    # 3) Prépare le safe_send et le throttle
    last_send = 0.0

    def safe_send(action, data):
        nonlocal last_send
        now = time.time()
        if now - last_send < interval:
            return  # trop tôt, on skip
        last_send = now
        try:
            msg = json.dumps({
                "module": client.module_id,
                "action": action,
                "data": data
            })
            client.send_ws(msg)
        except Exception as e:
            print(f"[WARN] Échec envoi WS : {e}")

    # 4) Prépare la fenêtre d’affichage
    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)

    # 5) Boucle de lecture du flux caméra
    while True:
        raw = sys.stdin.buffer.read(frame_size)
        if len(raw) < frame_size:
            break
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
            print(f"[SEND] x={x}, y={y}, diameter={r*2}")
        else:
            # print("[INFO] Aucun cercle détecté.")

        cv2.imshow("Flux de la caméra", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    print("Fin du module 1, le thread WebSocket sera tué automatiquement.")


if __name__ == "__main__":
    main()
