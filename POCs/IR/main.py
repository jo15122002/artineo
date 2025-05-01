import asyncio
import queue
import sys
import threading
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
        .joinpath("..", "..", "serveur")
        .resolve()
    )
)
from ArtineoClient import ArtineoAction, ArtineoClient

# --- Thread et queue pour envoi WS non bloquant ---
ws_queue = queue.Queue()

def ws_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = ArtineoClient(module_id=1)
    loop.run_until_complete(client.connect_ws())
    while True:
        data = ws_queue.get()
        if data is None:
            break
        # envoi asynchrone en synchrone pour le thread
        loop.run_until_complete(client.send_ws(ArtineoAction.SET, data))
    loop.run_until_complete(client.close_ws())

threading.Thread(target=ws_thread, daemon=True).start()


def preprocess(gray):
    """Flou léger + ouverture morphologique pour stabiliser HoughCircles."""
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.morphologyEx(blur, cv2.MORPH_OPEN, kernel)


def find_brightest_circle(gray, clean):
    """Détection Hough puis sélection du cercle le plus lumineux."""
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
    W, H = 320, 240
    frame_size = W * H * 3  # BGR24

    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)
    frame_idx = 0

    while True:
        raw = sys.stdin.buffer.read(frame_size)
        if len(raw) < frame_size:
            break
        frame = np.frombuffer(raw, dtype=np.uint8).reshape((H, W, 3))

        frame_idx += 1
        if frame_idx % 3 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clean = preprocess(gray)
            circ = find_brightest_circle(gray, clean)
            if circ:
                x, y, r = circ
                diameter = 2 * r
                # Dessin
                cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
                cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)
                # queue non bloquante
                ws_queue.put({"x": x, "y": y, "diameter": int(diameter)})

        cv2.imshow("Flux de la caméra", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # signal pour arrêter proprement le thread WS
    ws_queue.put(None)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()