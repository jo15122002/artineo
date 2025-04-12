import sys
import cv2
import numpy as np

def main():
    width = 640
    height = 480
    frame_size = width * height * 3  # bgr24 = 3 octets par pixel

    # Créer explicitement une fenêtre unique
    cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)

    while True:
        # Lire exactement la taille d'une image
        raw_data = sys.stdin.buffer.read(frame_size)
        if len(raw_data) < frame_size:
            break  # Fin du flux
        frame = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 3))
        cv2.imshow("Flux de la caméra", frame)
        # Quitter si l'utilisateur appuie sur 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
