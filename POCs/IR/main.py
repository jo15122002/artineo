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


def main():
    width = 640
    height = 480
    frame_size = width * height * 3  # bgr24 = 3 octets par pixel
    
    client = ArtineoClient(module_id=1)
    client.connect_ws()
    print("Connecté au serveur WebSocket.")
    client.fetch_config()
    print("Config reçue :", client.fetch_config())

    # Crée explicitement une fenêtre pour l'affichage
    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)
    # cv2.namedWindow("niveaux de gris", cv2.WINDOW_NORMAL)

    while True:
        # Lecture de la taille d'un frame
        raw_data = sys.stdin.buffer.read(frame_size)
        if len(raw_data) < frame_size:
            break  # Fin du flux
        frame = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 3))
        
        # Convertir en niveaux de gris pour la détection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Appliquer un flou pour réduire le bruit et améliorer la détection
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # Détection de cercles avec la méthode HoughCircles
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,           # Inverse du rapport de résolution
            minDist=50,       # Distance minimale entre les cercles détectés
            param1=50,        # Seuil pour la détection des contours (pour Canny)
            param2=30,        # Seuil d'accumulateur (plus petit = plus de fausses détections)
            minRadius=10,     # Rayon minimum du cercle à détecter
            maxRadius=100     # Rayon maximum du cercle à détecter
        )

        if circles is not None:
            # Arrondir et convertir en type entier
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                # Dessiner le cercle extérieur en vert
                cv2.circle(frame, (i[0], i[1]), i[2], (0, 255, 0), 2)
                # Dessiner le centre du cercle en rouge
                cv2.circle(frame, (i[0], i[1]), 2, (0, 0, 255), 3)

        # Affichage de l'image avec détection de sphère (cercles)
        cv2.imshow("Flux de la caméra", frame)
        # # Affichage de l'image en niveaux de gris
        # cv2.imshow("niveaux de gris", blurred)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
