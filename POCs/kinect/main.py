import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

# --- Suivi du curseur ---
mouse_x, mouse_y = 0, 0
def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

# --- Mapping outil → canal couleur (OpenCV BGR) ---
# '1' → bleu (canal 0), '2' → rouge (canal 2), '3' → vert (canal 1)
tool_color_channel = {'1': 0, '2': 2, '3': 1}

# --- Initialisation de la Kinect v2 ---
kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
print("Kinect initialized")
print(kinect)

# --- Gestion des baselines par outil ---
tool_base_frames = {}
frames = []
base_frame = None  # Baseline de la session en cours (en uint16)
last_depth_frame = None  # Dernière image de profondeur capturée (en uint16)

# Buffer global pour le lissage temporel sur 10 frames du canal actif
active_channel_buffer = []

# --- Stockage des dessins finaux ---
final_drawings = {
    '1': np.zeros((424, 512, 3), dtype=np.float32),
    '2': np.zeros((424, 512, 3), dtype=np.float32),
    '3': np.zeros((424, 512, 3), dtype=np.float32)
}

# Outil sélectionné par défaut
current_tool = '1'

# --- Paramètres du mapping ---
delta = 45             # Plage en mm autour de la baseline
scale = 128.0 / delta  # Ainsi, aucune modification donne 128
alpha = 0.1            # Coefficient pour la moyenne mobile exponentielle

# --- Chargement du brush personnalisé ---
brush = cv2.imread("POCs/kinect/brush2.png", cv2.IMREAD_GRAYSCALE)
if brush is None:
    print("Erreur : Fichier brush introuvable à l'emplacement 'POCs/kinect/brush2.png'")
    exit(1)
brush = brush.astype(np.float32) / 255.0  # Normalisation

def resize_brush(base_brush, size):
    size = max(3, int(size))  # éviter trop petit
    resized = cv2.resize(base_brush, (size, size), interpolation=cv2.INTER_LINEAR)
    return resized.astype(np.float32) / 255.0

# --- Création des fenêtres ---
cv2.namedWindow("Mapped Depth")
cv2.namedWindow("Depth frame")
cv2.namedWindow("Colored Drawing")
cv2.namedWindow("Final Drawing 1")
cv2.namedWindow("Final Drawing 2")
cv2.namedWindow("Final Drawing 3")
cv2.setMouseCallback("Mapped Depth", mouse_callback)
cv2.setMouseCallback("Depth frame", mouse_callback)

while True:
    if kinect.has_new_depth_frame():
        depth_frame = kinect.get_last_depth_frame()
        current_frame = depth_frame.reshape((424, 512)).astype(np.uint16)
        last_depth_frame = current_frame.copy()
        
        if base_frame is None:
            frames.append(current_frame)
            if len(frames) >= 10:
                base_frame = np.mean(frames, axis=0).astype(np.uint16)
                print(f"Base frame computed for tool {current_tool}.")
        else:
            # Calcul de la différence par rapport à la baseline
            diff = current_frame.astype(np.int32) - base_frame.astype(np.int32)
            mapped = 128 + (diff * scale)
            mapped = np.clip(mapped, 0, 255).astype(np.uint8)
            
            # Création de l'image "Mapped Depth" pour l'outil actif
            color_channel = tool_color_channel[current_tool]
            colored_frame = np.zeros((424, 512, 3), dtype=np.uint8)
            colored_frame[:, :, color_channel] = mapped
            if 0 <= mouse_y < 424 and 0 <= mouse_x < 512:
                depth_val = current_frame[mouse_y, mouse_x]
                diff_val = diff[mouse_y, mouse_x]
                mapped_val = mapped[mouse_y, mouse_x]
                text = f"Depth: {depth_val}mm, Diff: {diff_val}mm, Val: {mapped_val} | Pos: ({mouse_x},{mouse_y})"
                cv2.putText(colored_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.imshow("Mapped Depth", colored_frame)
            cv2.imshow("Depth frame", mapped)
            
            # Calcul de la modification par rapport à la baseline (valeurs positives uniquement)
            current_diff = mapped.astype(np.int16) - 128
            current_diff[current_diff < 0] = 0
            current_diff = current_diff.astype(np.float32)
            
            final_channel = final_drawings[current_tool][:, :, color_channel]
            updated_channel = (1 - alpha) * final_channel + alpha * current_diff
            final_drawings[current_tool][:, :, color_channel] = updated_channel

    # --- Affichage des fenêtres Final Drawing (zone d'intérêt recadrée et agrandie par 2) ---
    for tool in ['1', '2', '3']:
        fd = cv2.convertScaleAbs(final_drawings[tool])
        fd_cropped = fd[125:315, 160:410]
        fd_resized = cv2.resize(fd_cropped, (fd_cropped.shape[1]*2, fd_cropped.shape[0]*2), interpolation=cv2.INTER_LINEAR)
        cv2.imshow(f"Final Drawing {tool}", fd_resized)
    
    # --- Création du composite pour Colored Drawing ---
    composite = np.zeros((424, 512, 3), dtype=np.float32)
    for tool_key, drawing in final_drawings.items():
        ch = tool_color_channel[tool_key]
        layer = np.zeros_like(drawing)
        layer[:, :, ch] = drawing[:, :, ch]
        composite = cv2.add(composite, layer)
    composite_uint8 = cv2.convertScaleAbs(composite)

        # --- TEMPORAL SMOOTHING SUR LE CANAL ACTIF ---
    channel_index = tool_color_channel[current_tool]
    active_img = cv2.convertScaleAbs(final_drawings[current_tool][:, :, channel_index])
    active_channel_buffer.append(active_img.astype(np.float32))
    if len(active_channel_buffer) > 10:
        active_channel_buffer.pop(0)
    avg_active_img = np.mean(active_channel_buffer, axis=0).astype(np.uint8)
    cv2.imshow("Binary Mask Debug", avg_active_img)  # Pour vérifier le lissage

    # --- BAND-PASS THRESHOLDING sur l'image lissée ---
    # Ici, on utilise directement avg_active_img pour le seuillage
    _, binary = cv2.threshold(avg_active_img, 1, 255, cv2.THRESH_BINARY)
    
    # Calcul de la carte de distance -> estimation de l'épaisseur du trait
    dist_map = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    dist_map = cv2.normalize(dist_map, None, 5, 30, cv2.NORM_MINMAX)
    
    # Trouver les contours dans le masque nettoyé
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Pour test : couleur fixe selon l'outil actif
    if current_tool == '1':
        test_color = np.array([255, 0, 0], dtype=np.float32)  # Bleu
    elif current_tool == '2':
        test_color = np.array([0, 0, 255], dtype=np.float32)  # Rouge
    else:
        test_color = np.array([0, 255, 0], dtype=np.float32)  # Vert
    
    # Fond blanc pour le rendu final
    brushed_color = np.ones_like(composite_uint8) * 255

    # Itérer sur les contours trouvés et appliquer le brush
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        region_dist = dist_map[y:y+h, x:x+w]
        brush_size = np.mean(region_dist)
        custom_brush = resize_brush(brush, brush_size)
        bh, bw = custom_brush.shape

        for pt in cnt:
            j, i = pt[0]  # pt = [[x, y]]
            top = i - bh // 2
            left = j - bw // 2
            t0 = max(0, top)
            l0 = max(0, left)
            t1 = min(424, top + bh)
            l1 = min(512, left + bw)
            brush_top = 0 if top >= 0 else -top
            brush_left = 0 if left >= 0 else -left
            crop_h = t1 - t0
            crop_w = l1 - l0
            if crop_h <= 0 or crop_w <= 0:
                continue
            brush_crop = custom_brush[brush_top:brush_top+crop_h, brush_left:brush_left+crop_w]
            color_region = np.ones((crop_h, crop_w, 3), dtype=np.float32) * test_color
            region = brushed_color[t0:t1, l0:l1].astype(np.float32)
            alpha_f = brush_crop[..., None]
            blended = region * (1 - alpha_f) + color_region * alpha_f
            brushed_color[t0:t1, l0:l1] = np.clip(blended, 0, 255).astype(np.uint8)
    
    cv2.imshow("Brushed Result Debug", brushed_color)
    
    # Recadrer et agrandir Colored Drawing par un facteur de 3
    zoom_factor = 3
    cropped_cd = brushed_color[125:315, 160:410]
    resized_colored = cv2.resize(cropped_cd, (cropped_cd.shape[1]*zoom_factor, cropped_cd.shape[0]*zoom_factor), interpolation=cv2.INTER_LINEAR)
    cv2.imshow("Colored Drawing", resized_colored)

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
                print(f"Using saved base frame for tool {new_tool}.")
            else:
                base_frame = None
                frames = []
            current_tool = new_tool
            print(f"Tool changed to: {current_tool}")

kinect.close()
cv2.destroyAllWindows()
