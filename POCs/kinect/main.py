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
brush = cv2.imread("brush2.png", cv2.IMREAD_GRAYSCALE)
if brush is None:
    print("Erreur : Fichier brush introuvable à l'emplacement 'brush2.png'")
    exit(1)
brush = brush.astype(np.float32) / 255.0  # Normalisation

def resize_brush(base_brush, size):
    """Redimensionne le brush selon la taille calculée."""
    size = max(3, int(size))
    resized = cv2.resize(base_brush, (size, size), interpolation=cv2.INTER_LINEAR)
    return resized.astype(np.float32) / 255.0

# --- Création des fenêtres d'affichage ---
window_names = ["Mapped Depth", "Depth frame", "Colored Drawing", 
                "Final Drawing 1", "Final Drawing 2", "Final Drawing 3", 
                "Binary Mask Debug", "Brushed Result Debug", "Composite Drawing", "Gray Composite Debug", "Inverted Composite Debug", "Distance Map Debug"]
for name in window_names:
    cv2.namedWindow(name)
cv2.setMouseCallback("Mapped Depth", mouse_callback)
cv2.setMouseCallback("Depth frame", mouse_callback)

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
    """Applique l'effet brush sur le dessin composite final."""
    composite_img = composite_colored_drawing()
    cv2.imshow("Composite Drawing", composite_img)
    
    gray = cv2.cvtColor(composite_img, cv2.COLOR_BGR2GRAY)
    cv2.imshow("Gray Composite Debug", gray)
    
    inverted = 255 - gray
    cv2.imshow("Inverted Composite Debug", inverted)
    
    _, binary = cv2.threshold(inverted, 245, 255, cv2.THRESH_BINARY)
    cv2.imshow("Binary Mask Debug", binary)
    
    dist_map = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    dist_map = cv2.normalize(dist_map, None, 5, 30, cv2.NORM_MINMAX)
    cv2.imshow("Distance Map Debug", dist_map.astype(np.uint8))
    
    brushed = np.full(composite_img.shape, 255, dtype=np.uint8)
    
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        for pt in cnt[::2]:
            x, y = pt[0]
            brush_size = dist_map[y, x]
            custom_brush = resize_brush(brush, brush_size)
            bh, bw = custom_brush.shape
            top = y - bh // 2
            left = x - bw // 2
            t0 = max(0, top)
            l0 = max(0, left)
            t1 = min(brushed.shape[0], top + bh)
            l1 = min(brushed.shape[1], left + bw)
            brush_y0 = 0 if top >= 0 else -top
            brush_x0 = 0 if left >= 0 else -left
            region_brush = custom_brush[brush_y0:brush_y0 + (t1-t0), brush_x0:brush_x0 + (l1-l0)]
            if current_tool == '1':
                stroke_color = np.array([255, 0, 0], dtype=np.float32)
            elif current_tool == '2':
                stroke_color = np.array([0, 0, 255], dtype=np.float32)
            else:
                stroke_color = np.array([0, 255, 0], dtype=np.float32)
            region = brushed[t0:t1, l0:l1].astype(np.float32)
            alpha_mask = region_brush[..., None]
            blended = region * (1 - alpha_mask) + stroke_color * alpha_mask
            brushed[t0:t1, l0:l1] = np.clip(blended, 0, 255).astype(np.uint8)
    
    cv2.imshow("Brushed Result Debug", brushed)
    
    zoom_factor = 3
    cropped = brushed[125:315, 160:410]
    resized = cv2.resize(cropped, (cropped.shape[1]*zoom_factor, cropped.shape[0]*zoom_factor), interpolation=cv2.INTER_LINEAR)
    # cv2.imshow("Colored Drawing", resized)

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
