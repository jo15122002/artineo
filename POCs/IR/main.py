import cv2
from picamera2 import Picamera2


def main():
    # Crée une instance Picamera2
    picam2 = Picamera2()
    # Crée une configuration de prévisualisation en 640x480
    config = picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (640, 480)})
    # Configure la caméra avec cette configuration
    picam2.configure(config)
    # Démarre la capture
    picam2.start()

    while True:
        # Capture une image sous forme de tableau NumPy (compatible avec OpenCV)
        frame = picam2.capture_array()
        # cv2.imshow("Flux Video", frame)
        # Quitte la boucle quand on appuie sur 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    picam2.stop()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
