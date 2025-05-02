import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2
import os
import glob
import math
from pathlib import Path
import sys
import asyncio

sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parent
        .joinpath("..", "..", "serveur")
        .resolve()
    )
)
from ArtineoClient import ArtineoAction, ArtineoClient # type: ignore

client = ArtineoClient(module_id=4, host="192.168.0.180", port=8000)
config = client.fetch_config()
print("Configuration récupérée : ", config)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(client.connect_ws())
print("WebSocket connecté.")

latest_payload = None
strokes_events = []
objects_events = []

# --- Paramètres de la Région d'Intérêt (ROI) ---
ROI_X0, ROI_Y0 = 160, 130
ROI_X1, ROI_Y1 = 410, 300
ROI_WIDTH = ROI_X1 - ROI_X0   # 250 pixels
ROI_HEIGHT = ROI_Y1 - ROI_Y0  # 170 pixels

TEMPLATE_DIR = "images/templates/"

# Méthode de comparaison choisie :
# - pour matchShapes : utilisez cv2.matchShapes
# - pour Hu moments + KNN : on construira un simple KNN
USE_MATCHSHAPES = True
AREA_THRESHOLD = 2000
SMALL_AREA_THRESHOLD = 300 

N_PROFILE = 100 
background_profiles = {} 

frame_idx = 0

template_contours = {}
template_sizes = {}
overlays = {}
clusters = []

for filepath in glob.glob(os.path.join(TEMPLATE_DIR, "*.png")):
    name = os.path.splitext(os.path.basename(filepath))[0]
    img_gray = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        raise FileNotFoundError(f"Image introuvable : {filepath}")
    _, thresh_inv = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(cnts, key=cv2.contourArea)
    template_contours[name] = cnt
    x, y, w_t, h_t = cv2.boundingRect(cnt)
    template_sizes[name] = (w_t, h_t)

forme_templates = {name:cnt for name, cnt in template_contours.items() if name.startswith("Forme_")}
fond_templates = {name:cnt for name, cnt in template_contours.items() if name.startswith("Fond_")}
small_templates = {name:cnt for name, cnt in template_contours.items() if name.startswith("Small_")}

async def send_latest_payload():
    global latest_payload
    if latest_payload is None:
        return
    # envoie via WebSocket
    await client.set_buffer(latest_payload)

def compute_profile(mask, name=None, n=N_PROFILE):
    """
    mask : image binaire (0/255) de la silhouette
    name : nom pour la fenêtre d'affichage (ex. 'Fond_mer2' ou 'Kinect')
    renvoie un vecteur de longueur n, normalisé [0,1]
    """
    h, w = mask.shape
    xs = np.linspace(0, w-1, n).astype(int)
    prof = np.zeros(n, dtype=np.float32)
    for i, x in enumerate(xs):
        ys = np.where(mask[:, x] == 255)[0]
        if ys.size:
            prof[i] = ys.min() / float(h)
        else:
            prof[i] = 0.0

    if name is not None:
        # Crée une image blanche de 200px de haut pour dessiner le profil
        plot_h, plot_w = 200, n
        img_plot = np.ones((plot_h, plot_w, 3), dtype=np.uint8) * 255
        # Prépare les points (i, y) inversé pour que y=0 soit en haut
        pts = [(i, int((1 - prof[i]) * (plot_h - 1))) for i in range(n)]
        for i in range(1, n):
            cv2.line(img_plot, pts[i-1], pts[i], (0, 0, 0), 1)
        cv2.namedWindow(f"profile_{name}", cv2.WINDOW_NORMAL)
        cv2.imshow(f"profile_{name}", img_plot)

    return prof



for name, cnt in template_contours.items():
    path = os.path.join(TEMPLATE_DIR, f"{name}.png")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Overlay introuvable : {path}")

    if name.startswith("Forme_") or name.startswith("Small_"):
        # ——— Création du sprite recadré avec canal alpha ———
        if img.shape[2] == 4:
            mask = img[...,3] > 0
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, m = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY_INV)
            mask = m.astype(bool)

        ys, xs = np.where(mask)
        y0, y1 = ys.min(), ys.max()
        x0, x1 = xs.min(), xs.max()
        sprite = img[y0:y1+1, x0:x1+1].copy()

        # Ajout du canal alpha si besoin
        if sprite.shape[2] == 3:
            gray = cv2.cvtColor(sprite, cv2.COLOR_BGR2GRAY)
            _, a = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY_INV)
            sprite = np.dstack([sprite, a])

        # Fermer les trous de l’alpha
        kernel = np.ones((3,3), np.uint8)
        alpha = cv2.morphologyEx(sprite[...,3], cv2.MORPH_CLOSE, kernel, iterations=2)
        sprite[...,3] = alpha

        overlays[name] = sprite

    else:
        # 1) Extraire le canal BGR
        if img.shape[2] == 4:
            bgr = img[..., :3]
        else:
            bgr = img
        gray_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # 2) Binarisation directe : intérieur de la forme = 255, extérieur = 0
        _, mask = cv2.threshold(gray_full, 128, 255, cv2.THRESH_BINARY)

        # 3) Calcul et stockage du profil
        background_profiles[name] = compute_profile(mask, name)

        # 4) Stockage de l’overlay brut pour éviter le KeyError
        overlays[name] = img

for name, prof in background_profiles.items():
    print(name, np.unique(prof)[:5], prof.mean())

def classify_background_by_profile(cnt):
    # 1) reconstruire un mask binaire du contour
    x,y,w_d,h_d = cv2.boundingRect(cnt)
    mask = np.zeros((h_d, w_d), dtype=np.uint8)
    cnt_shifted = cnt - [x,y]            # déplacer le contour à l’origine du mask
    cv2.drawContours(mask, [cnt_shifted], -1, 255, thickness=cv2.FILLED)

    # 2) calculer son profil
    prof = compute_profile(mask, name='Kinect')

    # 3) comparer aux profils stockés et choisir le plus proche
    best_name, best_dist = None, float("inf")
    for name, tpl_prof in background_profiles.items():
        # distance euclidienne
        d = np.linalg.norm(prof - tpl_prof)
        # print(f"Distance {name} : {d:.2f}")
        if d < best_dist:
            best_dist, best_name = d, name
    print(f"Profil classifié : {best_name} (distance={best_dist:.2f})")
    return best_name

def classify_contour(cnt):
    """
    Retourne le nom du template le plus proche de cnt.
    """
    best_score = float("inf")
    best_name  = None

    area = cv2.contourArea(cnt)

    if area < SMALL_AREA_THRESHOLD:
        candidates = small_templates
    elif area < AREA_THRESHOLD:
        candidates = forme_templates
    else:
        return classify_background_by_profile(cnt)

    if USE_MATCHSHAPES:
        # Méthode cv2.matchShapes
        for name, template_cnt in candidates.items():
            score = cv2.matchShapes(cnt, template_cnt,
                                    cv2.CONTOURS_MATCH_I1, 0.0)
            print(f"Score {name} : {score:.2f}")
            if score < best_score:
                best_score, best_name = score, name
    else:
        # Méthode Hu moments + KNN (ici, un 1-Nearest-Neighbor très basique)
        hu_cnt = cv2.HuMoments(cv2.moments(cnt)).flatten()
        for name, template_cnt in candidates.items():
            hu_temp = cv2.HuMoments(cv2.moments(template_cnt)).flatten()
            score = np.linalg.norm(hu_cnt - hu_temp)
            print(f"Score {name} : {score:.2f}")
            if score < best_score:
                best_score, best_name = score, name

    print(f"Contour classifié : {best_name} (score={best_score:.2f})")
    return best_name

def overlay_png(canvas, overlay, center_x, center_y, scale=1.0):
    """
    Superpose `overlay` sur `canvas`. Gère :
      - overlay en niveau de gris (2D)
      - overlay Gray+Alpha (2 canaux)
      - overlay BGR (3 canaux)
      - overlay BGRA (4 canaux)
    Le blanc pur (255) est considéré transparent si pas de canal alpha.
    """
    # 1) Redimension si besoin
    h0, w0 = overlay.shape[:2]
    if scale != 1.0:
        new_w = int(w0 * scale)
        new_h = int(h0 * scale)
        overlay = cv2.resize(overlay, (new_w, new_h), interpolation=cv2.INTER_AREA)
    h, w = overlay.shape[:2]

    # 2) Détermination du ROI sur canvas
    x0 = int(center_x - w//2);   y0 = int(center_y - h//2)
    x1, y1 = x0 + w, y0 + h

    # 3) Recadrage si hors-limites
    ox0 = max(0, -x0); oy0 = max(0, -y0)
    x0_clamped = max(0, x0);    y0_clamped = max(0, y0)
    x1_clamped = min(canvas.shape[1], x1)
    y1_clamped = min(canvas.shape[0], y1)
    overlay = overlay[oy0 : oy0 + (y1_clamped - y0_clamped),
                      ox0 : ox0 + (x1_clamped - x0_clamped)]
    h, w = overlay.shape[:2]

    # 4) Préparer bgr et alpha selon le nombre de canaux
    if overlay.ndim == 2:
        # Grayscale seul
        bgr   = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR).astype(float)
        # tout ce qui est blanc (255) -> alpha=0, sinon alpha=1
        _, a = cv2.threshold(overlay, 254, 255, cv2.THRESH_BINARY_INV)
        alpha = (a.astype(float) / 255.0)[..., None]

    elif overlay.ndim == 3 and overlay.shape[2] == 2:
        # Gray + Alpha
        gray  = overlay[..., 0]
        a     = overlay[..., 1]
        bgr   = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR).astype(float)
        alpha = (a.astype(float) / 255.0)[..., None]

    elif overlay.ndim == 3 and overlay.shape[2] == 3:
        # BGR sans alpha
        bgr   = overlay.astype(float)
        # blanc => transparent
        gray  = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
        _, a = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY_INV)
        alpha = (a.astype(float) / 255.0)[..., None]

    elif overlay.ndim == 3 and overlay.shape[2] == 4:
        # BGRA
        bgr   = overlay[..., :3].astype(float)
        alpha = (overlay[..., 3].astype(float) / 255.0)[..., None]

    else:
        raise ValueError(f"Overlay de forme inattendue : {overlay.shape}")

    # 5) Blending
    inv_a = 1.0 - alpha
    roi   = canvas[y0_clamped:y0_clamped+h, x0_clamped:x0_clamped+w].astype(float)
    blended = roi * inv_a + bgr * alpha
    canvas[y0_clamped:y0_clamped+h, x0_clamped:x0_clamped+w] = blended.astype(np.uint8)


def update_clusters(detections, max_history=10, tol=3):
    global clusters, frame_idx
    for shape, cx, cy, area, angle, w, h in detections:
        matched = False
        if area > AREA_THRESHOLD:
            angle = 0.0
        for cl in clusters:
            if cl['shape']==shape \
               and abs(cx - cl['centroid'][0]) <= tol \
               and abs(cy - cl['centroid'][1]) <= tol:
                # on met à jour le cluster existant…
                cl['points'].append((cx, cy, area, angle, w, h))
                # on garde max_history
                if len(cl['points']) > max_history:
                    cl['points'].pop(0)
                # recalculs (centroid, avg_area, avg_angle, avg_w, avg_h) comme avant…
                cl['last_seen'] = frame_idx    # <-- on note quand on l’a vu
                matched = True
                break
        if not matched:
            # création d’un nouveau cluster
            clusters.append({
                'shape': shape,
                'points': [(cx, cy, area, angle, w, h)],
                'centroid': (cx, cy),
                'avg_area': area,
                'avg_angle': 0.0,
                'avg_w': w,
                'avg_h': h,
                'sprite': None,
                'sprite_params': (0.0, 0.0),
                'last_seen': frame_idx       # <-- initialisé à la frame courante
            })
    # **Après** avoir mis à jour tous les clusters, on supprime les stale :
    # on ne conserve que ceux vus dans les 10 dernières frames
    clusters[:] = [cl for cl in clusters if frame_idx - cl['last_seen'] <= 10]

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
tool_color_channel = {'1': 0, '2': 2, '3': 1, '4': 3}

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
    '3': np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.float32),
    # '4': np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.float32)
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

def detect_objects(frame):
    _, mask_objects = cv2.threshold(frame, 80, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((2,2), np.uint8)
    mask_objects = cv2.morphologyEx(mask_objects, cv2.MORPH_OPEN, kernel, iterations=1)
    mask_objects = cv2.morphologyEx(mask_objects, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours_objs, _ = cv2.findContours(mask_objects, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cv2.imshow("Mask Objects", mask_objects)

    detections = []
    min_area_obj = 200

    for cnt in contours_objs:
        area = cv2.contourArea(cnt)
        if area < min_area_obj:
            continue

        # Calcul du centroïde
        M = cv2.moments(cnt)
        if M['m00'] == 0:
            continue
        cx = M['m10']/M['m00']
        cy = M['m01']/M['m00']

        cnt_small = cv2.approxPolyDP(cnt, epsilon=1.0, closed=True)

        hull = cv2.convexHull(cnt_small)
        pts = hull.reshape(-1, 2)

        diffs = pts - np.array([cx, cy])
        dists = np.hypot(diffs[:,0], diffs[:,1])
        med = np.median(dists)
        mask = dists > med + 5   # adaptez le +5 selon votre bruit
        if not np.any(mask):
            mask = dists >= med   # tomber back si tout est trop serré
        pts_filt = pts[mask]

        idx = np.argmax(np.hypot(pts_filt[:,0]-cx, pts_filt[:,1]-cy))
        tip_x, tip_y = pts_filt[idx]

        # 3) Angle 0–360°
        raw_ang = math.degrees(math.atan2(tip_y-cy, tip_x-cx))
        ang360  = raw_ang if raw_ang>=0 else raw_ang+360
        # ang360 -= 90

        # 4) Taille de la boîte si besoin (ici boundingRect)
        x,y,w_d,h_d = cv2.boundingRect(cnt)

        # 5) Classification
        shape_name = classify_contour(cnt)
        detections.append((shape_name,
                   int(cx), int(cy),
                   area, ang360, w_d, h_d))
    
    update_clusters(detections)

# --- Traitement de la depth frame ---
def process_depth_frame(current_frame):
    global base_frame, final_drawings
    # Calcul de la différence par rapport à la baseline
    diff = current_frame.astype(np.int32) - base_frame.astype(np.int32)
    mapped = 128 + (diff * scale)
    mapped = np.clip(mapped, 0, 255).astype(np.uint8)
    show_image("Mapped Depth", mapped)

    # detect_objects(mapped)

    if current_tool == '4':
        detect_objects(mapped)
        return

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
        elif tool == '3':
            stroke_color = np.array([0, 255, 0], dtype=np.float32)
        mask_3 = np.repeat(mask_norm[:, :, np.newaxis], 3, axis=2)
        result = (1 - mask_3) * white_bg.astype(np.float32) + mask_3 * stroke_color
        result = np.clip(result, 0, 255).astype(np.uint8)
        show_image(f"Final Drawing {tool}", result)

def render_classification():
    canvas = np.zeros((ROI_HEIGHT, ROI_WIDTH, 3), dtype=np.uint8)
    for cl in clusters:
        if len(cl['points']) < 10:
            continue
        name = cl['shape']
        cx, cy = map(int, cl['centroid'])
        w_t, h_t = template_sizes[name]
        avg_w, avg_h = cl['avg_w'], cl['avg_h']
        scale = max(0.1, min(3.0, ((avg_w/w_t + avg_h/h_t)/2)*0.6))
        overlay_png(canvas, overlays[name], cx, cy, scale=scale)
    show_image("Classification", canvas)

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
    """Applique le pipeline de rendu avec brush strokes sur la ROI et superpose les sprites."""
    global frame_idx, strokes_events
    strokes_events.clear()

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # 1) Mise à jour du frame counter
    frame_idx += 1

    # 2) Composition du dessin courant et conversion en niveaux de gris
    composite_img = composite_colored_drawing()
    if composite_img is None:
        return
    gray = cv2.cvtColor(composite_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    cv2.imshow("Depth frame", composite_img)

    # 3) Binarisation + morpho
    _, binary = cv2.threshold(gray, 3, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel, iterations=3)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)

    # 4) Distance transform pour debug
    dist_map     = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    dist_display = cv2.normalize(dist_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # 5) Extraction des contours pour le brush
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 6) Application des brush strokes
    brushed = np.full((ROI_HEIGHT, ROI_WIDTH, 3), 255, dtype=np.uint8)
    min_brush_size    = 1
    max_brush_size    = 150
    dilate_kernel     = np.ones((3, 3), np.uint8)
    region_max_diff   = 7

    for cnt in contours:
        if cv2.contourArea(cnt) < 100:
            continue
        # masque intérieur du contour
        mask_contour = np.zeros(binary.shape, dtype=np.uint8)
        cv2.drawContours(mask_contour, [cnt], -1, 255, thickness=cv2.FILLED)

        region = dist_map.copy()
        region[mask_contour == 0] = 0
        region_max = region.max()
        if region_max < min_brush_size:
            continue

        dilated = cv2.dilate(dist_map, dilate_kernel)
        local_max_mask = (
            (dist_map == dilated) &
            (mask_contour == 255) &
            (dist_map >= region_max - region_max_diff)
        )
        ys, xs = np.where(local_max_mask)
        for py, px in zip(ys, xs):
            val = dist_map[py, px]
            if val < min_brush_size or val > max_brush_size:
                continue
            custom_brush = resize_brush(brush, int(val * brush_scale_factor))
            color = { '1': (0,0,255), '2': (255,0,0), '3': (0,255,0), '4': (0,0,0) }[current_tool]
            bh, bw = custom_brush.shape
            y0 = max(0, py - bh//2); x0 = max(0, px - bw//2)
            y1 = min(ROI_HEIGHT, y0 + bh);    x1 = min(ROI_WIDTH,  x0 + bw)
            roi_brush = custom_brush[:y1-y0, :x1-x0][..., None]
            region = brushed[y0:y1, x0:x1].astype(float)
            blended = region * (1-roi_brush) + np.array(color, float) * roi_brush
            brushed[y0:y1, x0:x1] = blended.astype(np.uint8)
            strokes_events.append({
                'tool': current_tool,
                'x': px, 'y': py, 'size': val,
                'color': color, 'brush': custom_brush
            })

    brushed = cv2.medianBlur(brushed, 5)

    # 7) Extraction des contours Objet depuis Mapped Depth pour clusters
    #    (idem process_depth_frame mais on veut contours_objs ici)
    #    On assume que mask_objects et contours_objs ont déjà été calculés
    #    dans process_depth_frame() et update_clusters y est appelé.

    # 8) Annotation des clusters : superposition des sprites
    # Purge des clusters stale est géré dans update_clusters()

    # 9) Affichage des widgets de debug
    if 0 <= mouse_y < ROI_HEIGHT and 0 <= mouse_x < ROI_WIDTH:
        d = dist_map[mouse_y, mouse_x]
        cv2.putText(dist_display, f"Distance: {d:.2f} @({mouse_x},{mouse_y})",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255,255,0), 1)
    show_image("Brushed Result Debug", brushed)
    show_image("Binary Mask Debug", binary)
    show_image("Distance Map Debug", dist_display)

def process_objects():
    global objects_events

    objects_events.clear()

    brushed = np.full((ROI_HEIGHT, ROI_WIDTH, 3), 255, dtype=np.uint8)
    for cl in clusters:
        if len(cl['points']) < 10:
            continue

        # Si cluster trop gros (main), on skip
        if cl['avg_area'] > ROI_WIDTH*ROI_HEIGHT*0.5:
            continue

        name      = cl['shape']
        cx, cy    = map(int, cl['centroid'])
        avg_w, avg_h, avg_angle = cl['avg_w'], cl['avg_h'], cl['avg_angle']

        # 8a) calcul scale linéaire
        w_t, h_t = template_sizes[name]
        scale_x = avg_w / w_t
        scale_y = avg_h / h_t
        scale   = (scale_x + scale_y) / 2.0
        scale   = max(0.1, min(3.0, scale)) * 0.6

        # 8b) Préparation du sprite (scale + rotate)
        prev_scale, prev_angle = cl['sprite_params']
        if cl['sprite'] is None \
           or abs(scale - prev_scale) > 0.1 \
           or abs(avg_angle - prev_angle) > 5:

            base = overlays[name]  # BGRA
            h0, w0 = base.shape[:2]

            # M = [cos*s  -sin*s  tx]
            #     [sin*s   cos*s  ty]
            M = cv2.getRotationMatrix2D((w0/2, h0/2), avg_angle, scale)
            # taille boîte englobante
            abs_cos = abs(M[0,0]); abs_sin = abs(M[0,1])
            new_w = int(h0*abs_sin + w0*abs_cos)
            new_h = int(h0*abs_cos + w0*abs_sin)
            # recentrage
            M[0,2] += (new_w - w0)/2
            M[1,2] += (new_h - h0)/2

            rotated = cv2.warpAffine(
                base, M, (new_w, new_h),
                flags=cv2.INTER_AREA,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0,0,0,0)
            )

            # recadrage ultime sur alpha>0
            a = rotated[...,3]
            ys, xs = np.where(a>0)
            y0, y1 = ys.min(), ys.max()
            x0, x1 = xs.min(), xs.max()
            sprite = rotated[y0:y1+1, x0:x1+1]
            cl['sprite'] = sprite
            cl['sprite_params'] = (scale, avg_angle)

        # 8c) Blitting binaire
        sprite = cl['sprite']
        h, w = sprite.shape[:2]
        x0 = cx - w//2; y0 = cy - h//2
        x1 = x0 + w;   y1 = y0 + h
        ox = max(0, -x0); oy = max(0, -y0)
        x0 = max(0, x0);  y0 = max(0, y0)
        x1 = min(brushed.shape[1], x1)
        y1 = min(brushed.shape[0], y1)
        roi = sprite[oy:oy+(y1-y0), ox:ox+(x1-x0)]
        mask = roi[...,3] > 0
        fg   = roi[...,:3]
        dst  = brushed[y0:y1, x0:x1]
        dst[mask] = fg[mask]

        objects_events.append({
            'tool': current_tool,
            'shape': name,
            'cx': cx, 'cy': cy,
            'w': avg_w, 'h': avg_h,
            'angle': avg_angle,
            'scale': scale,
            'sprite': sprite
        })
async def main():

    client.start_listening()

    while True:
        frame_idx += 1
        if kinect.has_new_depth_frame():
            depth_frame = kinect.get_last_depth_frame()
            full_frame = depth_frame.reshape((424, 512)).astype(np.uint16)
            full_frame = cv2.medianBlur(full_frame, 5)
            
            # Recadrer la frame sur la ROI
            current_frame = crop_to_roi(full_frame)
            current_frame = cv2.flip(current_frame, 1)
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

        if current_tool == '4':
            process_objects()
            render_classification()

        latest_payload = {
            "tool": current_tool,
            "strokes": strokes_events,
            "objects": objects_events
        }

        await client.set_buffer(latest_payload)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key in [ord('1'), ord('2'), ord('3'), ord('4')]:
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
        elif key == ord(' '): 
            USE_MATCHSHAPES = not USE_MATCHSHAPES
            print(f"Utilisation de cv2.matchShapes : {USE_MATCHSHAPES}")
        
        await asyncio.sleep(0)
        
    kinect.close()
    cv2.destroyAllWindows()
    loop.run_until_complete(client.close_ws())
    loop.close()

if __name__ == "__main__":
    asyncio.run(main())