import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

# --- Callback pour le suivi du curseur ---
mouse_x, mouse_y = 0, 0
def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

# --- Mapping outil → canal couleur (BGR) ---
tool_color_channel = {'1': 0, '2': 2, '3': 1}

# --- Initialisation de la Kinect v2 ---
try:
    kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
    print("Kinect initialisée.")
except Exception as e:
    print("Erreur lors de l'initialisation de la Kinect:", e)
    exit(1)

# --- Variables globales ---
tool_base_frames = {}   # Baselines sauvegardées pour chaque outil
frames = []             # Accumulation de frames pour calculer la baseline
base_frame = None       # Baseline actuelle (en uint16)
last_depth_frame = None # Dernière frame de profondeur capturée
cropped_frames = []     # Liste pour stocker les frames recadrées

active_channel_buffer = []  # Buffer pour le lissage temporel du canal actif

# Stockage des dessins finaux pour chaque outil (accumulation en float32)
final_drawings = {
    '1': np.zeros((424, 512, 3), dtype=np.float32),
    '2': np.zeros((424, 512, 3), dtype=np.float32),
    '3': np.zeros((424, 512, 3), dtype=np.float32)
}

# Outil actif par défaut
current_tool = '1'

# --- Paramètres de mapping ---
delta = 30              # Plage en mm autour de la baseline
scale = 738.0 / delta   # Facteur de mapping pour amplifier la sensibilité
alpha = 0.3             # Coefficient de lissage pour une mise à jour plus réactive

# --- Chargement du brush personnalisé ---
brush = cv2.imread("brush3.png", cv2.IMREAD_GRAYSCALE)
if brush is None:
    print("Erreur : Fichier brush introuvable à l'emplacement 'brush2.png'")
    exit(1)
brush = brush.astype(np.float32) / 255.0  # Normalisation

def resize_brush(base_brush, size):
    """Gestion des tailles extrêmes"""
    size = max(3, min(1000, int(size)))  # Plage [3, 1000]
    return cv2.resize(base_brush, (size, size))

# --- Création des fenêtres d'affichage ---
window_names = [
    "Mapped Depth", 
    "Depth frame", 
    "Colored Drawing", 
    # "Final Drawing 1", "Final Drawing 2", "Final Drawing 3", 
    "Binary Mask Debug", 
    "Brushed Result Debug", 
    # "Composite Drawing", 
    # "Gray Composite Debug", 
    # "Inverted Composite Debug", 
    "Distance Map Debug"
]

for name in window_names:
    cv2.namedWindow(name)
cv2.setMouseCallback("Mapped Depth", mouse_callback)
cv2.setMouseCallback("Depth frame", mouse_callback)
cv2.setMouseCallback("Distance Map Debug", mouse_callback)


def process_depth_frame(current_frame):
    """Calcule la différence par rapport à la baseline et met à jour le dessin final."""
    global base_frame, final_drawings
    diff = current_frame.astype(np.int32) - base_frame.astype(np.int32)
    mapped = 128 + (diff * scale)
    mapped = np.clip(mapped, 0, 255).astype(np.uint8)
    
    # Création de l'image colorée pour l'outil actif
    color_channel = tool_color_channel[current_tool]
    colored_frame = np.zeros((424, 512, 3), dtype=np.uint8)
    colored_frame[:, :, color_channel] = mapped
    
    if 0 <= mouse_y < 424 and 0 <= mouse_x < 512:
        depth_val = current_frame[mouse_y, mouse_x]
        diff_val = diff[mouse_y, mouse_x]
        mapped_val = mapped[mouse_y, mouse_x]
        text = f"Depth: {depth_val}mm, Diff: {diff_val}mm, Val: {mapped_val} | Pos: ({mouse_x},{mouse_y})"
        cv2.putText(colored_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    # cv2.imshow("Mapped Depth", colored_frame)
    # cv2.imshow("Depth frame", mapped)
    
    # Mise à jour du dessin final (uniquement pour les différences positives)
    current_diff = mapped.astype(np.int16) - 128
    current_diff[current_diff < 0] = 0
    current_diff = current_diff.astype(np.float32)
    channel = tool_color_channel[current_tool]
    final_channel = final_drawings[current_tool][:, :, channel]
    updated_channel = (1 - alpha) * final_channel + alpha * current_diff
    final_drawings[current_tool][:, :, channel] = updated_channel

def render_final_drawings():
    """Affiche les dessins finaux avec un fond blanc pour chaque outil."""
    for tool in ['1', '2', '3']:
        fd = cv2.convertScaleAbs(final_drawings[tool])
        white_bg = np.full(fd.shape, 255, dtype=np.uint8)
        channel = tool_color_channel[tool]
        mask = fd[:, :, channel]
        mask_norm = mask.astype(np.float32) / 255.0
        if tool == '1':
            stroke_color = np.array([255, 0, 0], dtype=np.float32)
        elif tool == '2':
            stroke_color = np.array([0, 0, 255], dtype=np.float32)
        else:
            stroke_color = np.array([0, 255, 0], dtype=np.float32)
        mask_3 = np.repeat(mask_norm[:, :, np.newaxis], 3, axis=2)
        result = (1 - mask_3) * white_bg.astype(np.float32) + mask_3 * stroke_color
        result = np.clip(result, 0, 255).astype(np.uint8)
        fd_cropped = result[125:315, 160:410]
        fd_resized = cv2.resize(fd_cropped, (fd_cropped.shape[1]*2, fd_cropped.shape[0]*2), interpolation=cv2.INTER_LINEAR)
        # cv2.imshow(f"Final Drawing {tool}", fd_resized)

def composite_colored_drawing():
    """Compose une image colorée à partir des dessins finaux des différents outils."""
    composite = np.zeros((424, 512, 3), dtype=np.float32)
    for tool_key, drawing in final_drawings.items():
        ch = tool_color_channel[tool_key]
        layer = np.zeros_like(drawing)
        layer[:, :, ch] = drawing[:, :, ch]
        composite = cv2.add(composite, layer)
    return cv2.convertScaleAbs(composite)

def process_brush_strokes():
    # Récupération de l'image composite
    composite_img = composite_colored_drawing()
    if composite_img is None:
        return

    # Prétraitement : conversion en niveaux de gris et flou
    gray = cv2.cvtColor(composite_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Seuillage et nettoyage morphologique
    _, binary = cv2.threshold(gray, 4, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # Calcul de la distance transform et normalisation pour le debug
    dist_map = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    dist_display = cv2.normalize(dist_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Détection des contours du dessin
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Initialisation d'un canvas blanc pour les brushes
    brushed = np.full((424, 512, 3), 255, dtype=np.uint8)
    
    # Réglages sur la taille minimale et maximale pour l'application du brush
    min_brush_size = 1
    max_brush_size = 150
    
    # Paramétrage de la dilatation pour repérer les maxima locaux
    dilate_kernel = np.ones((3, 3), np.uint8)
    
    for cnt in contours:
        # On filtre les petits contours si nécessaire
        if cv2.contourArea(cnt) < 100:
            continue

        # 1. Créer un masque rempli (mask_contour) pour ce contour
        mask_contour = np.zeros(binary.shape, dtype=np.uint8)
        cv2.drawContours(mask_contour, [cnt], -1, 255, thickness=cv2.FILLED)
        
        # Restriction du dist_map à la zone du contour
        contour_region = dist_map.copy()
        contour_region[mask_contour == 0] = 0
        
        # Calcul du maximum de la distance dans le contour
        region_max = contour_region.max()
        if region_max < min_brush_size:
            # On ne considère pas la forme si la distance maximale est trop faible
            continue
        
        # 2. Identifier les maxima locaux dans ce contour
        # La dilatation fait en sorte que chaque pixel vaut le maximum de son voisinage
        dilated = cv2.dilate(dist_map, dilate_kernel)
        # On considère comme maximum local les points qui:
        # - sont dans le contour (mask_contour==255)
        # - valent exactement la valeur dilatée (donc sont des pics locaux)
        # - ont une valeur >= (region_max - 2)
        local_max_mask = ((dist_map == dilated) &
                          (mask_contour == 255) &
                          (dist_map >= (region_max - 7)))
                          
        # Récupérer les coordonnées des maxima locaux
        ys, xs = np.where(local_max_mask)
        
        # Pour chaque maximum local identifié, appliquer le brush
        for (py, px) in zip(ys, xs):
            local_value = dist_map[py, px]
            # On s'assure que la taille calculée est dans les bornes définies
            if local_value < min_brush_size or local_value > max_brush_size:
                continue

            try:
                # Redimensionnement du brush en fonction de la valeur du maximum local
                custom_brush = resize_brush(brush, int(local_value))
                # Sélection de la couleur en fonction de l'outil actif
                color = {
                    '1': (0, 0, 255),   # Rouge
                    '2': (255, 0, 0),   # Bleu
                    '3': (0, 255, 0)    # Vert
                }[current_tool]
                
                # Positionnement du brush centré sur le point
                bh, bw = custom_brush.shape
                y_start = max(0, py - bh // 2)
                x_start = max(0, px - bw // 2)
                y_end = min(424, y_start + bh)
                x_end = min(512, x_start + bw)
                
                brush_roi = custom_brush[:y_end - y_start, :x_end - x_start]
                # Alpha sous forme de canal (converti de [0,1])
                alpha_channel = brush_roi[..., None]
                
                region = brushed[y_start:y_end, x_start:x_end].astype(float)
                blended = region * (1 - alpha_channel) + np.array(color, dtype=float) * alpha_channel
                brushed[y_start:y_end, x_start:x_end] = blended.astype(np.uint8)
            except Exception as e:
                print(f"Erreur brush : {str(e)}")
    
    # Application d'un léger flou pour adoucir le rendu final
    brushed = cv2.medianBlur(brushed, 5)

    # Affichage de la valeur de la distance sous le curseur
    if 0 <= mouse_y < 424 and 0 <= mouse_x < 512:
        dist_val = dist_map[mouse_y, mouse_x]
        text = f"Distance: {dist_val:.2f}mm | Pos: ({mouse_x},{mouse_y})"
        cv2.putText(dist_display, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
    
    # Affichage des fenêtres de debug
    cv2.imshow("Brushed Result Debug", brushed)
    cv2.imshow("Binary Mask Debug", binary)
    cv2.imshow("Distance Map Debug", dist_display)
    cv2.imshow("Composite Drawing", composite_img)


# --- Boucle principale ---
while True:
    
    if kinect.has_new_depth_frame():
        depth_frame = kinect.get_last_depth_frame()
        current_frame = depth_frame.reshape((424, 512)).astype(np.uint16)
        
        # Application du filtre médian pour réduire le bruit
        current_frame = cv2.medianBlur(current_frame, 5)
        
        last_depth_frame = current_frame.copy()
        
        if base_frame is None:
            frames.append(current_frame)
            if len(frames) >= 10:
                base_frame = np.mean(frames, axis=0).astype(np.uint16)
                print(f"Baseline calculée pour l'outil {current_tool}.")
        else:
            cropped_frames.append(current_frame)
            if len(cropped_frames) > 10:
                cropped_frames.pop(0)
            mean_cropped_frame = np.mean(cropped_frames, axis=0).astype(np.uint16)
            process_depth_frame(mean_cropped_frame)
    
    render_final_drawings()
    process_brush_strokes()
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in [ord('1'), ord('2'), ord('3')]:
        new_tool = chr(key)
        if new_tool != current_tool:
            if last_depth_frame is not None:
                tool_base_frames[current_tool] = last_depth_frame.copy()
            if new_tool in tool_base_frames:
                base_frame = tool_base_frames[new_tool].copy()
                print(f"Utilisation de la baseline sauvegardée pour l'outil {new_tool}.")
            else:
                base_frame = None
                frames = []
                active_channel_buffer = []
            current_tool = new_tool
            print(f"Outil changé: {current_tool}")
    
kinect.close()
cv2.destroyAllWindows()
