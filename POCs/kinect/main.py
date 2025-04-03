import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

# Variables globales pour la position du curseur
mouse_x, mouse_y = 0, 0
def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

# Mapping outil → canal couleur (OpenCV BGR)
# '1' → bleu (canal 0), '2' → rouge (canal 2), '3' → vert (canal 1)
tool_color_channel = {'1': 0, '2': 2, '3': 1}

# Initialisation de la Kinect v2
kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
print("Kinect initialized")
print(kinect)

# Pour chaque outil, nous stockerons la dernière image (depth) utilisée comme base_frame
tool_base_frames = {}

# Variables pour accumuler des frames et calculer la base_frame courante
frames = []
base_frame = None  # Base de référence pour la session en cours (en uint16)
last_depth_frame = None  # Dernière image de profondeur capturée (en uint16)

# Stockage des dessins finaux en float32 (pour permettre la moyenne mobile)
final_drawings = {
    '1': np.zeros((424, 512, 3), dtype=np.float32),
    '2': np.zeros((424, 512, 3), dtype=np.float32),
    '3': np.zeros((424, 512, 3), dtype=np.float32)
}

# Outil sélectionné par défaut
current_tool = '1'

# Paramètres pour le mapping de la profondeur
delta = 45             # Plage en mm autour de la base
scale = 128.0 / delta  # Ainsi, aucune modification donne 128
alpha = 0.1            # Coefficient pour la moyenne mobile exponentielle

# Chargement du brush personnalisé (PNG en niveaux de gris)
# brush = cv2.imread("POCs/kinect/brush2.png", cv2.IMREAD_GRAYSCALE)
# if brush is None:
#     print("Erreur : Le fichier 'brush2.png' est introuvable.")
#     exit(1)
# # Normalisation entre 0 et 1 pour une convolution propre
# brush = brush.astype(np.float32) / 255.0


# Création des fenêtres (les fenêtres de dessin final sont ouvertes dès le départ)
cv2.namedWindow("Mapped Depth")
cv2.namedWindow("Depth frame")
cv2.namedWindow("Colored Drawing")
cv2.namedWindow("Final Drawing 1")
cv2.namedWindow("Final Drawing 2")
cv2.namedWindow("Final Drawing 3")
cv2.setMouseCallback("Mapped Depth", mouse_callback)
cv2.setMouseCallback("Depth frame", mouse_callback)

# Chargement du brush impressionniste
brush = cv2.imread("POCs/kinect/brush2.png", cv2.IMREAD_GRAYSCALE)
if brush is None:
    print("Erreur : Fichier brush introuvable à l'emplacement 'POCs/kinect/brush.png'")
    exit(1)
brush = brush.astype(np.float32) / 255.0  # Normalisation


while True:
    if kinect.has_new_depth_frame():
        depth_frame = kinect.get_last_depth_frame()
        # Conversion en image 424x512 (en mm, uint16)
        current_frame = depth_frame.reshape((424, 512)).astype(np.uint16)
        # Mise à jour de la dernière image de profondeur capturée
        last_depth_frame = current_frame.copy()
        
        # Si aucune base n'est établie pour la session en cours, accumuler des frames
        if base_frame is None:
            frames.append(current_frame)
            if len(frames) >= 10:
                base_frame = np.mean(frames, axis=0).astype(np.uint16)
                print(f"Base frame computed for tool {current_tool}.")
        else:
            # Calcul de la différence par rapport à la base
            diff = current_frame.astype(np.int32) - base_frame.astype(np.int32)
            mapped = 128 + (diff * scale)
            mapped = np.clip(mapped, 0, 255).astype(np.uint8)
            
            # Création de l'image "Mapped Depth" pour l'outil actif
            color_channel = tool_color_channel[current_tool]
            colored_frame = np.zeros((424, 512, 3), dtype=np.uint8)
            colored_frame[:, :, color_channel] = mapped
            
            # Affichage d'infos en temps réel (profondeur, diff, etc.)
            if 0 <= mouse_y < 424 and 0 <= mouse_x < 512:
                depth_val = current_frame[mouse_y, mouse_x]
                diff_val = diff[mouse_y, mouse_x]
                mapped_val = mapped[mouse_y, mouse_x]
                text = f"Depth: {depth_val}mm, Diff: {diff_val}mm, Val: {mapped_val} | Pos: ({mouse_x},{mouse_y})"
                cv2.putText(colored_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            
            cv2.imshow("Mapped Depth", colored_frame)
            cv2.imshow("Depth frame", mapped)
            
            # Calcul de la modification par rapport à la base (seules les valeurs positives)
            current_diff = mapped.astype(np.int16) - 128
            current_diff[current_diff < 0] = 0
            current_diff = current_diff.astype(np.float32)
            
            # Mise à jour par moyenne mobile pour le canal de l'outil courant
            final_channel = final_drawings[current_tool][:, :, color_channel]
            updated_channel = (1 - alpha) * final_channel + alpha * current_diff
            final_drawings[current_tool][:, :, color_channel] = updated_channel

            # Appliquer le brush via convolution sur le canal actif uniquement
            # Cela ajoute une texture impressionniste (comme un filtre de peinture)
            # smoothed = cv2.filter2D(final_drawings[current_tool][:, :, color_channel], -1, brush)
            # final_drawings[current_tool][:, :, color_channel] = smoothed

    
    # Affichage continu des fenêtres de dessin final
    fd1 = cv2.convertScaleAbs(final_drawings['1'])
    fd2 = cv2.convertScaleAbs(final_drawings['2'])
    fd3 = cv2.convertScaleAbs(final_drawings['3'])
    cv2.imshow("Final Drawing 1", fd1)
    cv2.imshow("Final Drawing 2", fd2)
    cv2.imshow("Final Drawing 3", fd3)
    
    # Création de l'image composite pour "Colored Drawing"
    composite = np.zeros((424, 512, 3), dtype=np.float32)
    for tool_key, drawing in final_drawings.items():
        ch = tool_color_channel[tool_key]
        layer = np.zeros_like(drawing)
        layer[:, :, ch] = drawing[:, :, ch]
        composite = cv2.add(composite, layer)
    composite_uint8 = cv2.convertScaleAbs(composite)
    cropped_composite = composite_uint8[125:315, 160:410]

    # Créer un fond blanc
    white_bg = np.ones_like(composite_uint8) * 255

    # Masque : zones où il y a du dessin (au moins un canal > 0)
    mask = np.any(composite_uint8 > 10, axis=2).astype(np.uint8)

    # Brush appliqué uniquement aux zones avec dessin
    brushed = np.zeros_like(composite_uint8)
    for c in range(3):
        channel = composite_uint8[:, :, c].astype(np.float32)
        filtered = cv2.filter2D(channel, -1, brush)
        filtered_masked = np.where(mask == 1, filtered, 255)  # 255 = blanc sinon
        brushed[:, :, c] = np.clip(filtered_masked, 0, 255).astype(np.uint8)

    # Recadrage + zoom
    zoom_factor = 3
    cropped = brushed[125:315, 160:410]
    resized_colored = cv2.resize(cropped,
                                (cropped.shape[1] * zoom_factor, cropped.shape[0] * zoom_factor),
                                interpolation=cv2.INTER_LINEAR)

    cv2.imshow("Colored Drawing", resized_colored)



    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in [ord('1'), ord('2'), ord('3')]:
        new_tool = chr(key)
        if new_tool != current_tool:
            # Sauvegarder la dernière image de profondeur (last_depth_frame) pour l'outil en cours
            if last_depth_frame is not None:
                tool_base_frames[current_tool] = last_depth_frame.copy()
            # Lors de la sélection d'un nouvel outil, utiliser la base sauvegardée pour cet outil, si elle existe
            if new_tool in tool_base_frames:
                base_frame = tool_base_frames[new_tool].copy()
                print(f"Using saved base frame for tool {new_tool}.")
            else:
                base_frame = None
                frames = []
            current_tool = new_tool
            print(f"Tool changed to: {current_tool}")

kinect.close()
cv2.destroyAllWindows()
