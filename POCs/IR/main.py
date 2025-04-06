import cv2
import numpy as np


def map_distance_to_color(distance, max_distance):
    """
    Mappe la distance (de 0 à max_distance) à une couleur.
    Plus la sphère est proche du point de référence, plus la couleur tend vers le rouge lumineux.
    Plus elle est éloignée, plus la couleur tend vers le bleu sombre.
    """
    # Calcul de la luminosité inversée (plus proche = plus lumineux)
    brightness = int(np.clip(255 * (1 - distance/max_distance), 0, 255))
    # Calcul d'un poids pour mixer rouge et bleu
    weight = np.clip(1 - distance/max_distance, 0, 1)
    red = int(brightness * weight)
    blue = int(brightness * (1 - weight))
    green = 0  # pas de vert pour simplifier
    return (blue, green, red)  # format BGR

def main():
    # Définition de la pipeline GStreamer avec libcamera
    pipeline = (
        "libcamerasrc ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "video/x-raw,format=BGR ! "
        "appsink sync=false"
    )

    
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Erreur lors de l'ouverture de la caméra via libcamera.")
        return
    
    # Point de référence pour l'interaction (ici, le centre du cadre)
    ref_point = (320, 240)  # pour un cadre de 640x480
    max_distance = np.sqrt((640/2)**2 + (480/2)**2)  # distance maximale possible depuis le centre
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur lors de la capture d'image.")
            break
        
        # Conversion en niveaux de gris et floutage pour réduire le bruit
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        # Détection des cercles via HoughCircles
        circles = cv2.HoughCircles(gray_blurred, 
                                   cv2.HOUGH_GRADIENT, 
                                   dp=1.2, 
                                   minDist=50, 
                                   param1=50, 
                                   param2=30, 
                                   minRadius=10, 
                                   maxRadius=100)
        
        # Couleur par défaut en cas de non-détection
        overlay_color = (127, 127, 127)  # gris neutre
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            # Utilisation de la première sphère détectée
            x, y, r = circles[0]
            # Dessin du cercle et de son centre
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)
            # Calcul de la distance entre le centre de la sphère et le point de référence
            distance = np.sqrt((x - ref_point[0])**2 + (y - ref_point[1])**2)
            overlay_color = map_distance_to_color(distance, max_distance)
            # Affichage de la distance sur le flux vidéo
            cv2.putText(frame, f"Distance: {int(distance)}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Création d'un panneau de couleur illustrant l'effet interactif
        color_panel = np.zeros((200, 640, 3), dtype=np.uint8)
        color_panel[:] = overlay_color
        
        # Affichage des fenêtres : flux vidéo avec détection et panneau de couleur
        cv2.imshow("Flux Video", frame)
        cv2.imshow("Effet Couleur", color_panel)
        
        # Sortie de la boucle si 'q' est appuyé
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
