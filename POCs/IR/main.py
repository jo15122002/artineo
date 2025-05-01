import asyncio
import sys
from pathlib import Path

import cv2
import numpy as np

# On ajoute ../../serveur au path pour pouvoir y importer ArtineoClient
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


def preprocess(gray):
    """Égalisation d'histogramme + ouverture/fermeture pour nettoyer l'image."""
    eq = cv2.equalizeHist(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(eq, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


def find_best_circle(img):
    """Détecte le plus grand cercle via HoughCircles ou retourne None."""
    circles = cv2.HoughCircles(
        img,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=100,
        param1=100,
        param2=30,
        minRadius=20,
        maxRadius=150
    )
    if circles is None:
        return None
    circles = np.uint16(np.around(circles[0]))
    x, y, r = max(circles, key=lambda c: c[2])
    return int(x), int(y), int(r)


def main():
    width, height = 640, 480
    frame_size = width * height * 3  # bgr24 = 3 octets/pixel

    # Création du client et récupération de la config
    client = ArtineoClient(module_id=1)
    config = client.fetch_config()
    print("Config reçue :", config)

    # Préparer la boucle asyncio pour la WS
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.connect_ws())
    print("WebSocket connectée.")

    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)

    try:
        while True:
            buf = sys.stdin.buffer.read(frame_size)
            if len(buf) < frame_size:
                break

            frame = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 3))

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            clean = preprocess(blurred)

            circ = find_best_circle(clean)
            if circ:
                x, y, r = circ
                diameter = 2 * r

                # Dessin
                cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
                cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)

                # Envoi au serveur
                data = {"x": x, "y": y, "diameter": diameter}
                loop.run_until_complete(
                    client.send_ws(ArtineoAction.SET, data)
                )

            cv2.imshow("Flux de la caméra", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        # Fermeture propre
        loop.run_until_complete(client.close_ws())
        loop.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
