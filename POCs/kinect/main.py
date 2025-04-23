import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2
import os
import glob

# --- Paramètres de la Région d'Intérêt (ROI) ---
ROI_X0, ROI_Y0 = 160, 130
ROI_X1, ROI_Y1 = 410, 300
ROI_WIDTH = ROI_X1 - ROI_X0   # 250 pixels
ROI_HEIGHT = ROI_Y1 - ROI_Y0  # 170 pixels

TEMPLATE_DIR = "images/templates/"

# Méthode de comparaison choisie :
# - pour matchShapes : utilisez cv2.matchShapes
# - pour Hu moments + KNN : on construira un simple KNN
USE_MATCHSHAPES = False

template_contours = {}
overlays = {}

for filepath in glob.glob(os.path.join(TEMPLATE_DIR, "*.png")):
    name = os.path.splitext(os.path.basename(filepath))[0]  # e.g. "moulin"
    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    # Binarisation : noir (0) = contour, blanc (255) = fond
    _, thresh = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY_INV)
    # Extraction des contours
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # On prend le plus grand contour (en aire)
    cnt = max(cnts, key=cv2.contourArea)
    template_contours[name] = cnt

for name, cnt in template_contours.items():
    path = os.path.join(TEMPLATE_DIR, f"{name}.png")
    # IMREAD_UNCHANGED pour charger le canal alpha si présent
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Overlay introuvable : {path}")
    overlays[name] = img  # img.shape = (h, w, 4)

def classify_contour(cnt):
    """
    Retourne le nom du template le plus proche de cnt.
    """
    best_score = float("inf")
    best_name  = None

    if USE_MATCHSHAPES:
        # Méthode cv2.matchShapes
        for name, template_cnt in template_contours.items():
            score = cv2.matchShapes(cnt, template_cnt,
                                    cv2.CONTOURS_MATCH_I1, 0.0)
            if score < best_score:
                best_score, best_name = score, name
    else:
        # Méthode Hu moments + KNN (ici, un 1-Nearest-Neighbor très basique)
        hu_cnt = cv2.HuMoments(cv2.moments(cnt)).flatten()
        for name, template_cnt in template_contours.items():
            hu_temp = cv2.HuMoments(cv2.moments(template_cnt)).flatten()
            score = np.linalg.norm(hu_cnt - hu_temp)
            if score < best_score:
                best_score, best_name = score, name

    return best_name

def overlay_png(canvas, overlay, center_x, center_y, scale=1.0):
    """
    Superpose `overlay` (RGBA) sur `canvas` (BGR) centré en (center_x, center_y).
    scale permet d'agrandir/réduire l'overlay.
    """
    # 1) Redimensionner l'overlay si besoin
    h0, w0 = overlay.shape[:2]
    if scale != 1.0:
        overlay = cv2.resize(overlay, (int(w0*scale), int(h0*scale)), interpolation=cv2.INTER_AREA)
    h, w = overlay.shape[:2]

    # 2) Calculer les coordonnées du ROI sur le canvas
    x0 = int(center_x - w//2)
    y0 = int(center_y - h//2)
    x1, y1 = x0 + w, y0 + h

    # 3) Vérifier limites
    if x0 < 0 or y0 < 0 or x1 > canvas.shape[1] or y1 > canvas.shape[0]:
        # découper l'overlay et ajuster le ROI
        x0_c = max(0, -x0);   y0_c = max(0, -y0)
        x1_c = min(w, canvas.shape[1] - x0)
        y1_c = min(h, canvas.shape[0] - y0)
        overlay = overlay[y0_c:y1_c, x0_c:x1_c]
        x0, y0 = max(0, x0), max(0, y0)
        h, w = overlay.shape[:2]

    # 4) Séparer BGR et Alpha
    bgr    = overlay[..., :3].astype(float)
    alpha  = overlay[..., 3:] / 255.0  # normalisé [0,1]
    inv_a  = 1.0 - alpha

    # 5) Mélanger sur le canvas
    roi = canvas[y0:y0+h, x0:x0+w].astype(float)
    blended = roi * inv_a + bgr * alpha
    canvas[y0:y0+h, x0:x0+w] = blended.astype(np.uint8)

# Facteur de mise à l'échelle pour l'affichage dans les fenêtres
display_scale = 2  # vous pourrez ainsi voir une image agrandie (250x170 devient 500x340)

# --- Fonction utilitaire pour recadrer une image sur la ROI ---
def crop_to_roi(image):
    return image[ROI_Y0:ROI_Y1, ROI_X0:ROI_X1]

# --- Affichage redimensionné tout en gardant le même ratio ---
def show_image(window_name, image):
    # Redimensionnement de l'image selon le facteur display_scale
    resized = cv2.resize(image, (image.shape[1] * display_scale, image.shape[0] * display_scale),
                         interpolation=cv2.INTER_LINEAR)
    cv2.imshow(window_name, resized)

# --- Global Mouse Coordinates (en coordonnées de la ROI) ---
mouse_x, mouse_y = 0, 0
def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    # x,y sont les coordonnées dans la fenêtre redimensionnée,
    # on les convertit en coordonnées dans l'image originale (de la ROI).
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = int(x / display_scale), int(y / display_scale)

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
tool_base_frames = {}    # Baselines sauvegardées pour chaque outil
frames = []              # Accumulation de frames pour calculer la baseline
base_frame = None        # Baseline actuelle (en uint16) sur la ROI
last_depth_frame = None  # Dernière frame (croppée) de profondeur
cropped_frames = []      # Liste pour stocker les frames recadrées

active_channel_buffer = []  # Buffer pour le lissage temporel du canal actif

# Stockage des dessins finaux pour chaque outil (dimensions de la ROI)
final_drawings = {
    '1': np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.float32),
    '2': np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.float32),
    '3': np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.float32)
}

# Outil actif par défaut
current_tool = '1'

# --- Paramètres de mapping ---
delta = 30              # Plage en mm autour de la baseline
scale = 738.0 / delta   # Facteur de mapping pour amplifier la sensibilité
alpha = 0.3             # Coefficient de lissage pour la mise à jour des dessins
brush_scale_factor = 1.2

# --- Chargement du brush personnalisé ---
brush = cv2.imread("images/brushes/brush3.png", cv2.IMREAD_GRAYSCALE)
if brush is None:
    print("Erreur : Fichier brush introuvable à l'emplacement 'images/brushes/brush3.png'")
    exit(1)
brush = brush.astype(np.float32) / 255.0  # Normalisation

def resize_brush(base_brush, size):
    """Gère les tailles extrêmes du brush"""
    size = max(3, min(1000, int(size)))
    return cv2.resize(base_brush, (size, size))

# --- Création des fenêtres d'affichage en mode recadrable ---
window_names = [
    "Mapped Depth", 
    "Depth frame", 
    # "Colored Drawing", 
    "Binary Mask Debug", 
    # "Brushed Result Debug", 
    "Distance Map Debug",
    "Mask Objects"
]
for name in window_names:
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    # Optionnel : on peut fixer une taille initiale en gardant le ratio de la ROI
    cv2.resizeWindow(name, ROI_WIDTH * display_scale, ROI_HEIGHT * display_scale)

# Attribution de la callback souris sur quelques fenêtres
cv2.setMouseCallback("Mapped Depth", mouse_callback)
cv2.setMouseCallback("Depth frame", mouse_callback)
cv2.setMouseCallback("Distance Map Debug", mouse_callback)

# --- Traitement de la depth frame ---
def process_depth_frame(current_frame):
    global base_frame, final_drawings
    # Calcul de la différence par rapport à la baseline
    diff = current_frame.astype(np.int32) - base_frame.astype(np.int32)
    mapped = 128 + (diff * scale)
    mapped = np.clip(mapped, 0, 255).astype(np.uint8)
    show_image("Mapped Depth", mapped)

    _, mask_objects = cv2.threshold(mapped, 95, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5), np.uint8)
    mask_objects = cv2.morphologyEx(mask_objects, cv2.MORPH_OPEN, kernel, iterations=2)
    mask_objects = cv2.morphologyEx(mask_objects, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours_objs, _ = cv2.findContours(mask_objects, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cv2.imshow("Mask Objects", mask_objects)

    detections = []
    min_area_obj = 500

    for cnt in contours_objs:
        area = cv2.contourArea(cnt)
        if area < min_area_obj:
            continue

        # Calcul du centroïde
        M = cv2.moments(cnt)
        if M["m00"] == 0: 
            continue
        cx = int(M["m10"]/M["m00"])
        cy = int(M["m01"]/M["m00"])

        # Classification de la forme (fonction classify_contour déjà définie)
        shape_name = classify_contour(cnt)
        print(f"Objet détecté : {shape_name} à ({cx}, {cy})")
        detections.append((shape_name, cx, cy))

    
    # Création d'une image colorée pour l'outil actif
    color_channel = tool_color_channel[current_tool]
    colored_frame = np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.uint8)
    colored_frame[:, :, color_channel] = mapped
    
    # Mise à jour du dessin final sur la ROI en ne gardant que les différences positives
    current_diff = mapped.astype(np.int16) - 128
    current_diff[current_diff < 0] = 0
    current_diff = current_diff.astype(np.float32)
    
    channel = tool_color_channel[current_tool]
    final_channel = final_drawings[current_tool][:, :, channel]
    updated_channel = (1 - alpha) * final_channel + alpha * current_diff
    final_drawings[current_tool][:, :, channel] = updated_channel

    # Nettoyage immédiat du dessin pour limiter l'accumulation de bruit
    epsilon = 0.7  # Valeur seuil à ajuster selon le niveau de bruit observé
    final_drawings[current_tool][:, :, channel][final_drawings[current_tool][:, :, channel] < epsilon] = 0
    final_drawings[current_tool][:, :, channel] *= 0.95


# --- Rendu des dessins finaux ---
def render_final_drawings():
    """Affiche pour chaque outil son dessin final sur fond blanc."""
    # for tool in ['1', '2', '3']:
    for tool in ['1']:
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
        show_image(f"Final Drawing {tool}", result)

# --- Composition des dessins finaux ---
def composite_colored_drawing():
    """Compose une image colorée à partir des dessins finaux de tous les outils (dimension ROI)."""
    composite = np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.float32)
    for tool_key, drawing in final_drawings.items():
        ch = tool_color_channel[tool_key]
        layer = np.zeros_like(drawing)
        layer[:, :, ch] = drawing[:, :, ch]
        composite = cv2.add(composite, layer)
    return cv2.convertScaleAbs(composite)

# --- Traitement des brush strokes ---
def process_brush_strokes():
    """Applique le pipeline de rendu avec brush strokes sur la ROI."""
    composite_img = composite_colored_drawing()
    if composite_img is None:
        return

    gray = cv2.cvtColor(composite_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    cv2.imshow("Depth frame", composite_img )

    # Seuillage et nettoyage morphologique
    _, binary = cv2.threshold(gray, 3, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=3)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    # Calcul de la distance transform et normalisation pour le debug
    dist_map = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    dist_display = cv2.normalize(dist_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Détection des contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Canvas blanc pour l'application des brushes (dimensions ROI)
    brushed = np.full((ROI_HEIGHT, ROI_WIDTH, 3), 255, dtype=np.uint8)
    
    min_brush_size = 1
    max_brush_size = 150
    dilate_kernel = np.ones((3, 3), np.uint8)
    region_max_diff = 7
    
    for cnt in contours:
        if cv2.contourArea(cnt) < 100:
            continue

        # Créer le masque rempli du contour
        mask_contour = np.zeros(binary.shape, dtype=np.uint8)
        cv2.drawContours(mask_contour, [cnt], -1, 255, thickness=cv2.FILLED)
        
        contour_region = dist_map.copy()
        contour_region[mask_contour == 0] = 0
        
        region_max = contour_region.max()
        if region_max < min_brush_size:
            continue
        
        dilated = cv2.dilate(dist_map, dilate_kernel)
        # On recherche les maxima locaux dans la région
        local_max_mask = ((dist_map == dilated) &
                          (mask_contour == 255) &
                          (dist_map >= (region_max - region_max_diff)))
        ys, xs = np.where(local_max_mask)
        
        for (py, px) in zip(ys, xs):
            local_value = dist_map[py, px]
            if local_value < min_brush_size or local_value > max_brush_size:
                continue
            try:
                custom_brush = resize_brush(brush, int(local_value * brush_scale_factor))
                color = {
                    '1': (0, 0, 255),
                    '2': (255, 0, 0),
                    '3': (0, 255, 0)
                }[current_tool]
                bh, bw = custom_brush.shape
                y_start = max(0, py - bh // 2)
                x_start = max(0, px - bw // 2)
                y_end = min(ROI_HEIGHT, y_start + bh)
                x_end = min(ROI_WIDTH, x_start + bw)
                
                brush_roi = custom_brush[:y_end - y_start, :x_end - x_start]
                alpha_channel = brush_roi[..., None]
                region = brushed[y_start:y_end, x_start:x_end].astype(float)
                blended = region * (1 - alpha_channel) + np.array(color, dtype=float) * alpha_channel
                brushed[y_start:y_end, x_start:x_end] = blended.astype(np.uint8)
            except Exception as e:
                print(f"Erreur brush : {str(e)}")

    brushed = cv2.medianBlur(brushed, 5)
    if 0 <= mouse_y < ROI_HEIGHT and 0 <= mouse_x < ROI_WIDTH:
        dist_val = dist_map[mouse_y, mouse_x]
        text = f"Distance: {dist_val:.2f}mm | Pos: ({mouse_x},{mouse_y})"
        cv2.putText(dist_display, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255,255,0), 2)

    # upscale_factor = 2
    # upscaled_brushed = cv2.resize(brushed, (brushed.shape[1] * upscale_factor, brushed.shape[0] * upscale_factor), interpolation=cv2.INTER_CUBIC)
    # cv2.imshow("Brushed Result Upscaled", upscaled_brushed)
    show_image("Brushed Result Debug", brushed)
    show_image("Binary Mask Debug", binary)
    show_image("Distance Map Debug", dist_display)
    # show_image("Composite Drawing", composite_img)

# --- Boucle principale ---
while True:
    if kinect.has_new_depth_frame():
        depth_frame = kinect.get_last_depth_frame()
        full_frame = depth_frame.reshape((424, 512)).astype(np.uint16)
        full_frame = cv2.medianBlur(full_frame, 5)
        
        # Recadrer la frame sur la ROI
        current_frame = crop_to_roi(full_frame)
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