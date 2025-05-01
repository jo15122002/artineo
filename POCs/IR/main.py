import os
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
from ArtineoClient import ArtineoClient


def preprocess(gray):
    """
    Applique égalisation d'histogramme et morphologie pour réduire le bruit
    et améliorer les contours circulaires.
    """
    # égalisation pour étirer le contraste
    eq = cv2.equalizeHist(gray)
    # ouverture puis fermeture pour lisser les petits artifacts
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(eq, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


def find_best_circle(img):
    """
    Retourne le cercle de plus grand rayon détecté par HoughCircles,
    ou None si aucun cercle.
    """
    circles = cv2.HoughCircles(
        img,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=100,      # on veut un seul cercle, on augmente minDist
        param1=100,       # seuil Canny plus élevé pour limiter le bruit
        param2=30,        # accumulateur
        minRadius=20,     # ajuster selon la taille de votre sphère
        maxRadius=150
    )
    if circles is None:
        return None
    circles = np.uint16(np.around(circles[0]))
    # choisir le cercle de plus grand rayon
    best = max(circles, key=lambda c: c[2])
    x, y, r = int(best[0]), int(best[1]), int(best[2])
    return (x, y, r)


def main():
    width, height = 640, 480
    frame_size = width * height * 3  # bgr24 = 3 octets/pixel

    # initialisation WebSocket
    client = ArtineoClient(module_id=1)
    client.connect_ws()
    config = client.fetch_config()
    print("Config reçue :", config)

    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)

    while True:
        buf = sys.stdin.buffer.read(frame_size)
        if len(buf) < frame_size:
            break

        frame = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 3))

        # conversion + prétraitement
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        smooth = cv2.GaussianBlur(gray, (9, 9), 2)
        clean = preprocess(smooth)

        # détection du meilleur cercle
        result = find_best_circle(clean)
        if result:
            x, y, r = result
            diameter = 2 * r

            # dessin sur l'image
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)

            # envoi de la position & diameter
            client.send_position(x=x, y=y, diameter=diameter)

        cv2.imshow("Flux de la caméra", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    client.close_ws()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()