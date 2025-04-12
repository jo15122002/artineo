import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

# --- Callback pour le suivi du curseur ---
mouse_x, mouse_y = 0, 0
def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

dm_mouse_x, dm_mouse_y = 0, 0
def dm_mouse_callback(event, x, y, flags, param):
    global dm_mouse_x, dm_mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        dm_mouse_x, dm_mouse_y = x, y

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
brush = cv2.imread("brush2.png", cv2.IMREAD_GRAYSCALE)
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
cv2.setMouseCallback("Distance Map Debug", dm_mouse_callback)


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
    """Applique l'effet brush avec gestion robuste du bruit et de la distance map."""
    composite_img = composite_colored_drawing()
    
    # Étape 1: Conversion en gris avec pré-traitement
    gray = cv2.cvtColor(composite_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    cv2.imshow("Gray Composite Debug", gray)
    
    # Étape 2: Seuillage adaptatif (ajuster ces valeurs)
    _, binary = cv2.threshold(gray, 
                            4,   # Seuil bas (début de détection)
                            255, 
                            cv2.THRESH_BINARY)  # Inversion ici
    
    # Étape 3: Nettoyage morphologique
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
    
    # Debug du masque
    cv2.imshow("Binary Mask Debug", binary)
    
    # Étape 4: Distance Transform
    dist_map = cv2.distanceTransform(binary, cv2.DIST_L2, 5)  # Plus besoin d'inversion
    dist_map = np.nan_to_num(dist_map, posinf=0, neginf=0)
    
    # Filtrage des petites distances
    dist_map[dist_map < 2.0] = 0
    
    # Normalisation pour visualisation
    dist_display = cv2.normalize(dist_map, None, 0, 255, cv2.NORM_MINMAX)
    if 0 <= dm_mouse_x < dist_display.shape[1] and 0 <= dm_mouse_y < dist_display.shape[0]:
        val = dist_map[dm_mouse_y, dm_mouse_x]
        text = f"{val:.1f}px"
        cv2.putText(dist_display, text, 
                    (10, 20),  # Décalage pour lisibilité
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                    (255, 255, 255), 1, cv2.LINE_AA)
    
    cv2.imshow("Distance Map Debug", dist_display.astype(np.uint8))
    
    # Étape 5: Application du brush
    brushed = np.full_like(composite_img, 255)
    
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        for pt in cnt[::5]:
            x, y = pt[0]
            
            # Calcul de la taille avec vérification des valeurs
            y_roi = slice(max(0,y-2), min(y+3, dist_map.shape[0]))
            x_roi = slice(max(0,x-2), min(x+3, dist_map.shape[1]))
            
            roi = dist_map[y_roi, x_roi]
            roi_clean = roi[np.isfinite(roi)]  # Filtre les valeurs non-finies
            
            if len(roi_clean) == 0:
                continue  # Aucune donnée valide
                
            brush_size = np.mean(roi_clean) * 1.5
            
            # Vérification finale avant conversion
            if brush_size > 2 and brush_size < 1000:  # Plage de sécurité
                custom_brush = resize_brush(brush, int(brush_size))
                bh, bw = custom_brush.shape
                
                # Positionnement sécurisé
                y_start = max(0, y - bh//2)
                x_start = max(0, x - bw//2)
                y_end = min(brushed.shape[0], y_start + bh)
                x_end = min(brushed.shape[1], x_start + bw)
                
                # Extraction de la région valide
                valid_brush = custom_brush[:y_end-y_start, :x_end-x_start]
                alpha = valid_brush[..., None]
                
                # Couleur selon l'outil
                color = {
                    '1': (0, 0, 255),  # Rouge
                    '2': (255, 0, 0),  # Bleu
                    '3': (0, 255, 0)   # Vert
                }[current_tool]
                
                # Application
                region = brushed[y_start:y_end, x_start:x_end]
                brushed[y_start:y_end, x_start:x_end] = (region * (1 - alpha) + color * alpha).astype(np.uint8)
    
    # Post-traitement final
    brushed = cv2.medianBlur(brushed, 3)
    cv2.imshow("Brushed Result Debug", brushed)


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
