import os

import cv2
from picamera2 import Picamera2

# Si besoin, forcer le mode offscreen (pour éviter l'ouverture d'une fenêtre système en environnement headless)
# os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    picam2 = Picamera2()
    # Crée une configuration de prévisualisation en 640x480 avec le format XRGB8888
    config = picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (640, 480)})
    picam2.configure(config)
    picam2.start()

    # Créer explicitement la fenêtre (cela garantit qu'une seule fenêtre est utilisée)
    cv2.namedWindow("Flux Video", cv2.WINDOW_NORMAL)

    while True:
        frame = picam2.capture_array()
        cv2.imshow("Flux Video", frame)
        # Quitter en appuyant sur 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    picam2.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
