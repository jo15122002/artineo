import cv2
import numpy as np


def main():
    # Définir le pipeline GStreamer en utilisant v4l2src
    pipeline = (
        "v4l2src device=/dev/video0 ! "
        "videoconvert ! "
        "video/x-raw,format=BGR ! "
        "appsink"
    )
    
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Erreur lors de l'ouverture de la caméra via pipeline V4L2.")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur lors de la lecture du flux vidéo.")
            break
        
        cv2.imshow("Flux Video", frame)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()