import asyncio
import sys
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
    width, height = 640, 480
    frame_size = width * height * 3  # bgr24

    # Initialisation WebSocket
    client = ArtineoClient(module_id=1)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.connect_ws())
    print("WebSocket connectée.")

    # Envoi non-bloquant/résilient
    async def safe_send(action, data):
        try:
            await client.send_ws(action, data)
        except Exception as e:
            print(f"[WARN] Échec envoi WS : {e}")

    # Capture et traitement
    while True:
        raw = sys.stdin.buffer.read(frame_size)
        if len(raw) < frame_size:
            break
        frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))

        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=50,
            param1=50, param2=30, minRadius=10, maxRadius=100
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))[0]
            # Trier par intensité (au lieu de taille), puis prendre le premier
            # On calcule la « luminosité » moyenne du pourtour
            best = None; bestScore = -1
            for (x, y, r) in circles:
                mask = np.zeros_like(gray)
                cv2.circle(mask, (x, y), r, 255, 2)
                score = cv2.mean(gray, mask=mask)[0]
                if score > bestScore:
                    bestScore = score
                    best = (x, y, r)
            if best:
                x, y, r = best
                cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
                # Envoi des coordonnées
                loop.run_until_complete(
                    safe_send(ArtineoAction.SET, {
                        "x": int(x), "y": int(y), "diameter": int(r * 2)
                    })
                )

        # cv2.imshow("Flux caméra", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()