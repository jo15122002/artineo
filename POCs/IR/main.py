import cv2
import numpy as np

def main():
    # Définition de la pipeline GStreamer utilisant libcamera
    pipeline = (
        "libcamerasrc ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "video/x-raw,format=BGR ! "
        "appsink"
    )
    
    # Ouverture du flux vidéo via la pipeline
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Erreur lors de l'ouverture de la caméra via libcamera.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur lors de la capture d'image")
            break

        # Conversion de l'image en niveaux de gris pour la détection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (15, 15), 0)

        # Détection des cercles avec la transformation de Hough
        circles = cv2.HoughCircles(gray_blurred,
                                   cv2.HOUGH_GRADIENT,
                                   dp=1.2,
                                   minDist=100,
                                   param1=50,
                                   param2=30,
                                   minRadius=10,
                                   maxRadius=100)
        
        # Si des cercles sont détectés, on les dessine sur l'image
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                cv2.circle(frame, (x, y), r, (0, 255, 0), 4)
                cv2.rectangle(frame, (x - 2, y - 2), (x + 2, y + 2), (0, 128, 255), -1)
                print("Sphère détectée à: x =", x, "y =", y, "rayon =", r)

        # Affichage du flux vidéo avec les détections
        cv2.imshow("Détection de Sphère", frame)

        # Quitter en appuyant sur "q"
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
