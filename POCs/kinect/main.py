import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

# Variables globales pour la position de la souris
mouse_x, mouse_y = 0, 0

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

# Initialisation de la Kinect v2 pour récupérer la profondeur
kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
print("Kinect initialized")
print(kinect)

frames = []
base_frame = None      # Frame de référence pour la session courante
# Dictionnaire pour stocker le dessin final par outil (clé: '1', '2', '3')
final_drawings = {}

# On commence avec l'outil "1" par défaut
current_tool = '1'

# Paramètres pour le mapping de la profondeur
delta = 45             # Plage en mm autour de la base
scale = 128.0 / delta  # Pour mapper une différence de ±delta mm à ±128 (0 correspond à 0, 128 à la base, 255 au max)

cv2.namedWindow("Mapped Depth")
cv2.namedWindow("Depth frame")
cv2.setMouseCallback("Mapped Depth", mouse_callback)
cv2.setMouseCallback("Depth frame", mouse_callback)

while True:
    if kinect.has_new_depth_frame():
        depth_frame = kinect.get_last_depth_frame()
        # Reshape en 424x512 et conversion en uint16 (valeurs en mm)
        current_frame = depth_frame.reshape((424, 512)).astype(np.uint16)
        
        # Si aucune base n'est établie pour la session courante, accumuler des frames pour la calculer
        if base_frame is None:
            frames.append(current_frame)
            if len(frames) >= 10:
                base_frame = np.mean(frames, axis=0).astype(np.uint16)
                print(f"Base frame computed for tool {current_tool}.")
        else:
            # Calcul de la différence par rapport à la base
            diff = current_frame.astype(np.int32) - base_frame.astype(np.int32)
            # Mapper la différence pour que 0 (aucune différence) corresponde à 128
            mapped = 128 + (diff * scale)
            mapped = np.clip(mapped, 0, 255).astype(np.uint8)
            
            # Création d'une image couleur en utilisant uniquement le canal bleu
            blue_frame = np.zeros((current_frame.shape[0], current_frame.shape[1], 3), dtype=np.uint8)
            blue_frame[:, :, 0] = mapped
            
            # Affichage des informations à la position de la souris
            if 0 <= mouse_y < current_frame.shape[0] and 0 <= mouse_x < current_frame.shape[1]:
                depth_val = current_frame[mouse_y, mouse_x]
                diff_val = diff[mouse_y, mouse_x]
                blue_val = mapped[mouse_y, mouse_x]
                text = f"Depth: {depth_val}mm, Diff: {diff_val}mm, Blue: {blue_val}"
                cv2.putText(blue_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            
            cv2.imshow("Mapped Depth", blue_frame)
            cv2.imshow("Depth frame", mapped)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in [ord('1'), ord('2'), ord('3')]:
        new_tool = chr(key)
        # Lors du changement d'outil, si une base a été établie, on enregistre l'image finale
        if base_frame is not None:
            # Supprimer la baseframe : on soustrait 128 du canal bleu afin de n'avoir que ce que l'utilisateur a dessiné
            drawing_only = blue_frame[:, :, 0].astype(np.int16) - 128
            drawing_only = np.clip(drawing_only, 0, 255).astype(np.uint8)
            # Créer une image couleur où seul le canal bleu contient le dessin (les autres canaux restent à 0)
            final_drawing = np.zeros_like(blue_frame)
            final_drawing[:, :, 0] = drawing_only
            
            # Si l'outil a déjà un dessin, on l'additionne au nouveau dessin avec une pondération (pour cumuler)
            if new_tool in final_drawings:
                final_drawings[new_tool] = cv2.addWeighted(final_drawings[new_tool], 0.7, final_drawing, 0.3, 0)
            else:
                final_drawings[new_tool] = final_drawing.copy()
            
            # Afficher la fenêtre du dessin final pour l'outil courant
            window_name = f"Final Drawing {new_tool}"
            cv2.imshow(window_name, final_drawings[new_tool])
        
        # Si on revient sur un outil déjà sélectionné, son dessin final est affiché, sinon on initialise une fenêtre vide
        current_tool = new_tool
        if current_tool not in final_drawings:
            final_drawings[current_tool] = np.zeros((424, 512, 3), dtype=np.uint8)
            cv2.imshow(f"Final Drawing {current_tool}", final_drawings[current_tool])
        
        # Réinitialiser la base et vider les frames pour démarrer un nouveau dessin pour cet outil
        base_frame = None
        frames = []
        print(f"Tool changed to: {current_tool}")

    # Mise à jour en continu des fenêtres Final Drawing existantes
    for tool_key, drawing in final_drawings.items():
        window_name = f"Final Drawing {tool_key}"
        cv2.imshow(window_name, drawing)

kinect.close()
cv2.destroyAllWindows()
