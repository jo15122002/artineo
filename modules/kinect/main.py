import asyncio
import logging
from typing import Dict, List
import uuid
import cv2
import numpy as np
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parent
        .joinpath("..", "..", "serveur", "back")
        .resolve()
    )
)
from ArtineoClient import ArtineoClient
from background_tracker import BackgroundTracker
from baseline_calculator import BaselineCalculator
from baseline_manager import BaselineManager
from brush_detector import BrushStrokeDetector
from channel_selector import ChannelSelector
from channel4_detector import Channel4Detector
from cluster_tracker import ClusterTracker
from config import Config
from depth_processor import DepthProcessor
from keyboard_selector import KeyboardChannelSelector
from kinect_interface import KinectInterface
from object_detector import ObjectDetector
from payload_sender import PayloadSender
from roi_calibrator import RoiCalibrator
from shape_classifier import ShapeClassifier
from stroke_confirm_tracker import StrokeConfirmTracker
from stroke_lifetimer import StrokeLifeTimer
from stroke_tracker import StrokeTracker
from template_manager import TemplateManager

logger = logging.getLogger(__name__)

class DisplayManager:
    def __init__(self, windows: List[str]):
        self.windows = windows
        for w in self.windows:
            cv2.namedWindow(w, cv2.WINDOW_NORMAL)

    def show(self, name: str, img):
        if name not in self.windows:
            cv2.namedWindow(name, cv2.WINDOW_NORMAL)
            self.windows.append(name)
        cv2.imshow(name, img)

    def process_events(self):
        return cv2.waitKey(1) & 0xFF


class MainController:
    """
    Orchestrates the Artineo Kinect pipeline :
      1. Phase dessin (outils 1−3) → calcul de baseline « sable + dessin »
      2. Passage en canal 4 → on instancie BaselineManager avec cette baseline
      3. Boucle canal 4 :
         - détecter suppressions → mise à jour de la baseline
         - détecter ajouts (fonds + objets) via Channel4Detector → collages successifs dans la baseline
      4. Envoi des événements (add / remove) vers NuxtJS via WebSocket.
    """

    def __init__(
        self,
        raw_config: dict,
        channel_selector: ChannelSelector = KeyboardChannelSelector(),
        client: ArtineoClient = None,
    ):
        logger.info("Initializing MainController...")

        # 1. Charger la config
        self.config = Config(**(raw_config or {}))

        # 2. ArtineoClient (pour envoyer les events au serveur)
        self.client = client

        # 3. Initialisation Kinect et BaselineCalculator (phase dessin)
        self.kinect = KinectInterface(self.config, logger=logger)
        self.baseline_calc = BaselineCalculator(self.config, logger=logger)

        # 4. Charger les templates relatifs via TemplateManager
        self.template_manager = TemplateManager(
            template_dir=self.config.template_dir,
            n_profile=self.config.n_profile,
            area_threshold=self.config.area_threshold,
            small_area_threshold=self.config.small_area_threshold,
        )

        # 5. ShapeClassifier (matching 3D sur patch_rel)
        self.shape_classifier = ShapeClassifier(
            depth_templates=self.template_manager.depth_templates,
            small_area_threshold=self.config.small_area_threshold,
            match_threshold=self.config.match_threshold
        )

        # 6. ClusterTracker + ObjectDetector (inchangés)
        self.cluster_tracker = ClusterTracker(
            max_history=self.config.n_profile,
            tol=self.config.display_scale,
            area_threshold=self.config.area_threshold,
        )
        self.object_detector = ObjectDetector(
            cluster_tracker=self.cluster_tracker,
            template_sizes=self.template_manager.template_sizes,
            roi_width=self.config.roi_width,
            roi_height=self.config.roi_height,
        )

        # 7. DepthProcessors
        self.depth_processor = DepthProcessor(
            self.config,
            mask_threshold=2,
            morph_kernel=3
        )
        self.depth_processor_4 = DepthProcessor(
            self.config,
            mask_threshold=1,
            morph_kernel=3
        )

        # 8. Channel4Detector (ne fait que détecter)
        self.channel4_detector = Channel4Detector(
            depth_processor=self.depth_processor_4,
            shape_classifier=self.shape_classifier,
            cluster_tracker=self.cluster_tracker,
            object_detector=self.object_detector,
            small_area_threshold=self.config.small_area_threshold,
            display=self.config.debug_mode
        )
        self.bg_tracker = BackgroundTracker()

        # 9. Gestion des outils 1–3 (brush, strokes, etc.)
        self.current_tool: str = '1'
        self.tool_channel = {'1': 0, '2': 1, '3': 2, '4': 3}
        self.channel_selector: ChannelSelector = channel_selector

        self.stroke_tracker = StrokeTracker(proximity_threshold=5.0)
        self.stroke_lifetimers = {
            tool: StrokeLifeTimer(max_age=5)
            for tool in self.tool_channel
        }
        self.stroke_confirm = StrokeConfirmTracker(
            proximity_threshold=5.0,
            min_confirm=self.config.stroke_confirmation_frames
        )
        self.strokes_by_tool: Dict[str, Dict[str, dict]] = {
            '1': {}, '2': {}, '3': {}, '4': {}
        }

        brush_path = Path(self.config.template_dir).parent.joinpath(
            "images", "brushes", "brush3.png"
        )
        brush_img = cv2.imread(str(brush_path), cv2.IMREAD_GRAYSCALE)
        if brush_img is None:
            raise FileNotFoundError(f"Brush image not found: {brush_path}")
        self.brush_detector = BrushStrokeDetector(
            brush=brush_img,
            config=self.config,
        )

        # 10. WS payload sender
        if not self.config.bypass_ws:
            self.payload_sender = PayloadSender(self.client, logger=logger)

        # 11. Buffers pour le dessin (outils 1–3)
        h, w = self.config.roi_height, self.config.roi_width
        self.final_drawings = {
            t: np.zeros((h, w, 3), dtype=float)
            for t in self.tool_channel
        }

        # 12. ROI calibrator
        self.roi_calibrator = RoiCalibrator(self.kinect, scale=1)

        # 13. BaselineManager (initialisée avec une baseline factice)
        dummy_baseline = np.zeros(
            (self.config.roi_height, self.config.roi_width),
            dtype=np.uint16
        )
        self.baseline_manager = BaselineManager(
            initial_baseline=dummy_baseline,
            template_manager=self.template_manager,
            removal_threshold=self.config.removal_threshold,
            removal_ratio=self.config.removal_ratio
        )
        self.baseline_ready = False  # passera à True lorsque la baseline « sable+dessin » sera calculée

        # Pour suivre l’état du fond / objets en canal 4
        # (inutile si vous n’avez pas de structure dédiée)
        self.backgrounds_in_baseline: List[str] = []
        self.objects_in_baseline: List[str] = []
        
        self.baseline_sand: np.ndarray | None = None
        self.baseline_objects: np.ndarray | None = None

        self.active_background: dict | None = None       # Contiendra l’événement complet du fond posé (ou None)
        self.active_objects: Dict[str, dict] = {}        # Clé = object_id, Valeur = event dict correspondant à l’objet.

        # ID des zones fraîchement ajoutées à ignorer pour la détection de retrait
        self.skip_removal_ids: set[str] = set()
        
        self.bg_detect_count    = 0
        self.bg_candidate_id    = None
        self.bg_candidate_shape = None
        self.bg_missing_count   = 0
        self.BG_FRAMES_TO_ADD   = 10    # ou  nombre que vous voulez
        self.BG_FRAMES_TO_REMOVE= 10
        
        self.obj_detect_counts   = {}
        self.obj_missing_counts  = {}
        self.OBJ_FRAMES_TO_ADD   = 10
        self.OBJ_FRAMES_TO_REMOVE= 10

        logger.info("MainController initialized.")

    async def run(self) -> None:
        # --- 1) Démarrage Kinect & WebSocket ---
        self.kinect.open()
        if not self.config.bypass_ws:
            self.payload_sender.start()

        try:
            while True:
                # Listes temporaires d’événements à envoyer
                new_strokes: List[dict] = []
                removed_strokes: List[str] = []
                new_backgrounds: List[dict] = []
                removed_backgrounds: List[str] = []
                new_objects: List[dict] = []
                removed_objects: List[str] = []

                # --- 2) Changement d’outil éventuel ---
                next_tool = await self.channel_selector.get_next_channel()
                if next_tool and next_tool != self.current_tool:
                    # (identique à votre version : réinitialiser tout le contexte)
                    old = self.current_tool
                    self.current_tool = next_tool
                    logger.info(f"Tool switched → {self.current_tool}")

                    # 2.a) Transformer anciens strokes en persistents
                    old_slots = self.strokes_by_tool[old]
                    for sid, ev in old_slots.items():
                        ev['persistent'] = True
                        self.stroke_lifetimers[old].ages.pop(sid, None)

                    # 2.b) Reset du BaselineCalculator pour la phase dessin
                    self.baseline_calc.reset()
                    self.baseline_ready = False

                    # 2.c) Réinitialiser les buffers de dessin
                    for buf in self.final_drawings.values():
                        buf.fill(0)

                    # 2.d) Réinitialiser le contexte “fond” et “objets” en canal 4
                    self.active_background = None
                    self.active_objects.clear()
                    self.baseline_sand = None
                    self.baseline_objects = None
                    self.skip_removal_ids.clear()

                    # 2.e) Ré-émission des strokes persistents du nouvel outil
                    new_slots = self.strokes_by_tool[self.current_tool]
                    persistent = [ev for ev in new_slots.values() if ev.get('persistent')]
                    if persistent and not self.config.bypass_ws:
                        await self.payload_sender.send_update(
                            new_strokes=persistent,
                            remove_strokes=[],
                            new_backgrounds=[],
                            remove_backgrounds=[],
                            new_objects=[],
                            remove_objects=[]
                        )

                # --- 3) Lecture d’une frame Kinect ---
                if not self.kinect.has_new_depth_frame():
                    await asyncio.sleep(0.01)
                    continue
                frame = self.kinect.get_depth_frame()

                # --- 4) Calibration ROI si demandé ---
                if self.config.calibrate_roi:
                    rx, ry = self.roi_calibrator.run()
                    logger.info(f"ROI calibrated → x={rx}, y={ry}")
                    self.config.calibrate_roi = False

                # --- 5) Affichage brut (debug) si activé ---
                if self.config.debug_mode:
                    disp_dbg = cv2.convertScaleAbs(frame, alpha=255.0 / (frame.max() or 1))
                    cv2.imshow("Depth (debug)", disp_dbg)
                    if cv2.waitKey(1) == ord('q'):
                        break

                # --- 6) OUTILS 1–3 (pinceaux) ---
                if self.current_tool in ('1', '2', '3'):
                    # (votre code inchangé pour la phase dessin)
                    try:
                        baseline_dessin = self.baseline_calc.ensure_baseline_ready(frame)
                        self.baseline_ready = True
                    except RuntimeError:
                        continue

                    result = self.depth_processor.process(frame, baseline_dessin)
                    ch = self.tool_channel[self.current_tool]
                    diff = (result.mapped.astype(int) - 128).clip(min=0).astype(float)
                    mask = diff > self.config.stroke_intensity_thresh
                    buf = self.final_drawings[self.current_tool][:, :, ch]
                    buf[mask] = (1 - self.config.alpha) * buf[mask] + self.config.alpha * diff[mask]
                    buf[~mask] *= (1 - 0.15)
                    composite = cv2.convertScaleAbs(self.final_drawings[self.current_tool])

                    raw = self.brush_detector.detect(composite, self.current_tool)
                    existing = list(self.strokes_by_tool[self.current_tool].values())
                    unique = self.stroke_tracker.update(raw, existing)
                    confirmed = self.stroke_confirm.update(unique)

                    slots = self.strokes_by_tool[self.current_tool]
                    for ev in confirmed:
                        if ev['size'] > self.config.stroke_size_max:
                            continue
                        ev['persistent'] = False
                        sid = str(uuid.uuid4())
                        ev['id'] = sid
                        slots[sid] = ev
                        new_strokes.append(ev)

                    dynamic_slots = {
                        sid: ev
                        for sid, ev in slots.items()
                        if not ev.get('persistent', False)
                    }
                    active_ids = []
                    for sid, ev in dynamic_slots.items():
                        for r in raw:
                            if abs(r['x'] - ev['x']) <= self.stroke_tracker.proximity_threshold \
                            and abs(r['y'] - ev['y']) <= self.stroke_tracker.proximity_threshold:
                                active_ids.append(sid)
                                break
                    lifetimer = self.stroke_lifetimers[self.current_tool]
                    stale = lifetimer.update(active_ids)
                    for sid in stale:
                        del slots[sid]
                        removed_strokes.append(sid)

                # --- 7) OUTIL 4 (canal fond + objets) ---
                else:
                    # 7.a) Initialiser baseline_sand dès qu’on entre en canal 4 pour la première fois
                    if self.baseline_sand is None:
                        try:
                            self._initialize_baseline_for_channel4(frame)
                        except RuntimeError:
                            # si ensure_baseline_ready échoue, on attend la frame suivante
                            continue

                    # 7.b) Détection des fonds (par rapport à la baseline_sand)
                    bg_events, obj_events_unused, _cnts_unused = self.channel4_detector.detect(
                        frame,
                        self.baseline_sand
                    )
                    logger.debug(f"[run] bg_events reçus : {bg_events}")

                    # 7.c) Traitement des événements “fond” en utilisant BackgroundTracker
                    _new_bgs, _rem_bgs = self._handle_background_events(bg_events, frame)
                    logger.info(f"[run] _handle_background_events → nouveaux fonds : {_new_bgs}, fonds supprimés : {_rem_bgs}")
                    for ev in _new_bgs:
                        new_backgrounds.append(ev)
                    for rid in _rem_bgs:
                        removed_backgrounds.append(rid)

                    # 7.d) Si on a maintenant un fond confirmé, on fait la détection d’objets sur baseline_objects
                    if self.active_background is not None:
                        _new_objs, _rem_objs = self._handle_object_events(frame)
                        logger.info(f"[run] _handle_object_events → nouveaux objets : {_new_objs}, objets supprimés : {_rem_objs}")
                        for ev in _new_objs:
                            new_objects.append(ev)
                        for oid in _rem_objs:
                            removed_objects.append(oid)

                    # 7.e) Après avoir confirmé ou retiré, on peut vider skip_removal_ids si besoin
                    #      (vous pouvez adapter cette logique pour ne pas vider immédiatement
                    #       si vous voulez conserver l’ID du fond deux frames de plus, etc.)
                    self.skip_removal_ids.clear()

                # --- 8) Envoi WS des diffs (strokes, backgrounds, objects) ---
                if not self.config.bypass_ws and (
                    new_strokes or removed_strokes or
                    new_backgrounds or removed_backgrounds or
                    new_objects or removed_objects
                ):
                    await self.payload_sender.send_update(
                        new_strokes=new_strokes,
                        remove_strokes=removed_strokes,
                        new_backgrounds=new_backgrounds,
                        remove_backgrounds=removed_backgrounds,
                        new_objects=new_objects,
                        remove_objects=removed_objects,
                    )
                    
                if self.baseline_sand is not None:
                    # On normalise la baseline_sand (uint16) en 8 bits pour affichage
                    sand_norm = cv2.convertScaleAbs(
                        self.baseline_sand,
                        alpha=255.0 / (self.baseline_sand.max() or 1)
                    )
                    cv2.imshow("Baseline Sand (sable)", sand_norm)

                if self.baseline_objects is not None:
                    # Même traitement pour sable+fond+objets
                    obj_norm = cv2.convertScaleAbs(
                        self.baseline_objects,
                        alpha=255.0 / (self.baseline_objects.max() or 1)
                    )
                    cv2.imshow("Baseline Objects (sable+fond+objets)", obj_norm)

                # pour que les fenêtres se mettent à jour
                cv2.waitKey(1)

                # --- 9) Petite pause non bloquante pour la boucle asyncio ---
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down.")
        finally:
            # --- Cleanup final ---
            self.kinect.close()

            if not self.config.bypass_ws:
                all_stroke_ids = []
                for slots in self.strokes_by_tool.values():
                    all_stroke_ids.extend(slots.keys())

                remaining_bg_ids = []
                remaining_obj_ids = []
                if self.active_background is not None:
                    remaining_bg_ids.append(self.active_background["id"])
                for obj_id in self.active_objects.keys():
                    remaining_obj_ids.append(obj_id)

                await self.payload_sender.send_update(
                    new_strokes=[],
                    remove_strokes=all_stroke_ids,
                    new_backgrounds=[],
                    remove_backgrounds=remaining_bg_ids,
                    new_objects=[],
                    remove_objects=remaining_obj_ids,
                )
                await self.payload_sender.stop()

            if self.config.debug_mode:
                cv2.destroyAllWindows()
            logger.info("Shutdown complete.")

    
    def _blit_zone_on_baseline(
        self,
        baseline: np.ndarray,
        event: dict
    ) -> np.ndarray:
        """
        Colle la silhouette 3D d’un fond ou d’un objet (event) sur la baseline fournie.
        - `baseline` : np.ndarray 2D de type uint16 (ex. self.baseline_objects)
        - `event`    : dictionnaire qui contient au moins les clefs :
              'shape'  → nom de template (p.ex. 'landscape_sea' ou 'medium_lighthouse')
              'cx','cy'→ coordonnées du centre de la zone dans l’image depth
              'w','h'  → largeur et hauteur de la bounding box (en pixels dans la depth frame)
              'angle'  → rotation (en degrés) à appliquer au template
              'scale'  → facteur d’échelle (1.0 = taille native du template)
              'id'     → identifiant unique (uuid) de la zone

        Retourne une NOUVELLE array (copie de baseline) sur laquelle on a « blitté » la forme 3D.
        """
        
        # 1) Récupérer le template de profondeur 3D brut (uint16)
        shape_name = event["shape"]
        if shape_name not in self.template_manager.depth_templates:
            logger.warning(f"Template {shape_name} introuvable dans depth_templates.")
            return baseline

        template_depth = self.template_manager.depth_templates[shape_name]
        # template_depth est un np.ndarray 2D dtype=uint16

        # 2) Appliquer l’échelle + rotation
        #    - On part de la taille native du template (H_t, W_t)
        H_t, W_t = template_depth.shape

        #    - On calcule la nouvelle taille « wxh » à appliquer, en fonction de event['scale'] et event['w'], event['h']
        #      Pour être sûr d’avoir exactement la bounding box détectée, on peut forcer :
        new_w = int(event["w"])
        new_h = int(event["h"])
        if new_w <= 0 or new_h <= 0:
            # pas de zone, on retourne baseline inchangée
            return baseline

        # 2.a) Resize du template (sans rotation) pour coller à la bbox w×h
        resized = cv2.resize(
            template_depth,
            (new_w, new_h),
            interpolation=cv2.INTER_NEAREST  # on préserve la quantification profondeur
        )

        # 2.b) Rotation autour du centre (cx_template, cy_template) = (new_w/2, new_h/2)
        angle = float(event.get("angle", 0.0))
        M = cv2.getRotationMatrix2D(
            center=(new_w / 2, new_h / 2),
            angle=angle,
            scale=1.0
        )
        # Calculer bounding box de la rotation pour qu’on ne coupe pas
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        bound_w = int((new_h * sin) + (new_w * cos))
        bound_h = int((new_h * cos) + (new_w * sin))

        # Ajuster la matrice de translation pour centrer
        M[0, 2] += (bound_w / 2) - (new_w / 2)
        M[1, 2] += (bound_h / 2) - (new_h / 2)

        rotated = cv2.warpAffine(
            resized,
            M,
            (bound_w, bound_h),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0  # on considère que le reste est « loin » (valeur grande)
        )

        # 3) Positionner le centre (cx, cy) → on veut que (cx, cy) corresponde au centre de rotated
        H_b, W_b = baseline.shape
        cx = int(event["cx"])
        cy = int(event["cy"])
        # calculer coin supérieur gauche de la zone où coller `rotated`
        x0 = cx - (bound_w // 2)
        y0 = cy - (bound_h // 2)
        x1 = x0 + bound_w
        y1 = y0 + bound_h

        # 4) Faire la découpe « ROI » dans la baseline (pénaliser les débordements)
        x0_clip = max(0, x0)
        y0_clip = max(0, y0)
        x1_clip = min(W_b, x1)
        y1_clip = min(H_b, y1)

        # coordonnées dans le template tourné/resizé à prendre
        tx0 = x0_clip - x0
        ty0 = y0_clip - y0
        tx1 = tx0 + (x1_clip - x0_clip)
        ty1 = ty0 + (y1_clip - y0_clip)

        # Extraire la zone de baseline sur laquelle on va coller
        baseline_roi = baseline[y0_clip:y1_clip, x0_clip:x1_clip]
        template_roi = rotated[ty0:ty1, tx0:tx1]

        # 5) Combinaison des profondeurs :  
        #    On veut que la zone la plus proche (smallest depth) gagne. Typiquement, le template
        #    est plus proche (valeur plus petite) que la baseline existante (sable ou ancien objet).
        #    On prend donc l’opération np.minimum à chaque pixel.
        merged = np.minimum(baseline_roi, template_roi.astype(baseline_roi.dtype))

        # 6) Réinsérer la zone merge dans la baseline
        new_baseline = baseline.copy()
        new_baseline[y0_clip:y1_clip, x0_clip:x1_clip] = merged
        return new_baseline        
    
    
    def _handle_background_events(
        self,
        bg_events: List[dict],
        frame: np.ndarray,
    ) -> tuple[list[dict], list[str]]:
        """
        Gère l’ajout/suppression du fond après N frames pour éviter le clignotement.
        On se base sur `shape` (et non `id`) pour suivre la stabilité.
        """

        new_bgs:     list[dict] = []
        removed_bgs: list[str] = []

        # --- CAS 1 : aucun fond actif pour le moment ---
        if self.active_background is None:
            if not bg_events:
                # Pas de fond détecté → rien à valider
                logger.debug("_handle_background_events (CAS 1) : aucun bg_event et pas de active_background")
                # On remet à zéro le candidat précédent
                self.bg_candidate_shape = None
                self.bg_detect_count = 0
                return new_bgs, removed_bgs

            # Il y a au moins un bg_events
            cand = bg_events[0]
            cand_shape = cand["shape"]

            if self.bg_candidate_shape != cand_shape:
                # Nouveau shape candidat (différent du précédent)
                self.bg_candidate_shape = cand_shape
                self.bg_detect_count = 1
                logger.debug(
                    f"_handle_background_events (CAS 1) : nouveau candidat de fond '{cand_shape}' "
                    f"(id temporaire = {cand['id']}). reset bg_detect_count=1."
                )
            else:
                # Même shape que la frame précédente → incrémenter le compteur
                self.bg_detect_count += 1
                logger.debug(
                    f"_handle_background_events (CAS 1) : fond '{cand_shape}' détecté "
                    f"{self.bg_detect_count} frames de suite."
                )

            # Si on a vu ce même shape au moins BG_FRAMES_TO_ADD fois de suite => on le valide
            if self.bg_detect_count >= self.BG_FRAMES_TO_ADD:
                logger.info(
                    f"_handle_background_events (CAS 1) : fond '{cand_shape}' confirmé "
                    f"après {self.bg_detect_count} frames. Ajout du fond."
                )
                # 1) on devient actif
                self.active_background = cand.copy()
                # 2) on colle la forme du fond dans baseline_objects
                self.baseline_objects = self._blit_zone_on_baseline(self.baseline_objects, cand)
                # 3) on empêche une suppression immédiate
                self.skip_removal_ids.add(cand["id"])
                # 4) on envoie l’événement vers le front
                new_bgs.append({
                    "id":    cand["id"],
                    "type":  "background",
                    "shape": cand_shape,
                    "cx":    cand["cx"],
                    "cy":    cand["cy"],
                    "w":     cand["w"],
                    "h":     cand["h"],
                    "angle": cand.get("angle", 0.0),
                    "scale": cand.get("scale", 1.0),
                })
                # Réinitialiser les compteurs pour la suite
                self.bg_candidate_shape = None
                self.bg_detect_count = 0
                self.bg_missing_count = 0  # on n’a pas encore besoin de compter les absences
            return new_bgs, removed_bgs

        # --- CAS 2 : il existe déjà un fond actif ---
        # 2.a) si on détecte au moins un bg_event
        if bg_events:
            # On cherche dans bg_events un event dont le shape == self.active_background["shape"]
            shapes_detectes = [ev["shape"] for ev in bg_events]
            if self.active_background["shape"] in shapes_detectes:
                # Le même fond est toujours présent → on remet à zéro le compteur d’absence
                self.bg_missing_count = 0
                logger.debug(
                    f"_handle_background_events (CAS 2) : fond actif '{self.active_background['shape']}' "
                    "toujours détecté, reset missing_count."
                )
                return new_bgs, removed_bgs

            # Sinon, on a un « nouveau » shape dans bg_events (remplacement potentiel)
            cand = bg_events[0]
            cand_shape = cand["shape"]

            if self.bg_candidate_shape != cand_shape:
                # On change de candidat
                self.bg_candidate_shape = cand_shape
                self.bg_detect_count = 1
                logger.debug(
                    f"_handle_background_events (CAS 2) : nouveau candidat de remplacement "
                    f"'{cand_shape}', reset bg_detect_count=1."
                )
            else:
                # Même candidat que la frame précédente → on incrémente
                self.bg_detect_count += 1
                logger.debug(
                    f"_handle_background_events (CAS 2) : remplacement candidat '{cand_shape}' "
                    f"détecté {self.bg_detect_count} frames de suite."
                )

            if self.bg_detect_count >= self.BG_FRAMES_TO_ADD:
                # On valide le remplacement
                old_shape = self.active_background["shape"]
                old_id    = self.active_background["id"]
                logger.info(
                    f"_handle_background_events (CAS 2) : remplacement du fond "
                    f"'{old_shape}' (id={old_id}) → nouveau '{cand_shape}'."
                )
                # 1) on enregistre la suppression de l’ancien
                removed_bgs.append(old_id)
                # 2) on reconstruit baseline_objects sans l’ancien fond
                self._rebuild_baseline_objects()
                # 3) on colle le nouveau fond
                self.active_background = cand.copy()
                self.baseline_objects = self._blit_zone_on_baseline(self.baseline_objects, cand)
                self.skip_removal_ids.add(cand["id"])
                # 4) on émet l’événement d’ajout du nouveau fond
                new_bgs.append({
                    "id":    cand["id"],
                    "type":  "background",
                    "shape": cand_shape,
                    "cx":    cand["cx"],
                    "cy":    cand["cy"],
                    "w":     cand["w"],
                    "h":     cand["h"],
                    "angle": cand.get("angle", 0.0),
                    "scale": cand.get("scale", 1.0),
                })
                # Reset des compteurs
                self.bg_candidate_shape = None
                self.bg_detect_count = 0
                self.bg_missing_count = 0
            return new_bgs, removed_bgs

        # 2.b) il y avait un fond actif, mais plus aucun bg_events → peut-être une suppression
        if not bg_events:
            self.bg_missing_count += 1
            logger.debug(
                f"_handle_background_events (CAS 2) : plus aucun bg_events, "
                f"missing_count pour '{self.active_background['shape']}' = {self.bg_missing_count}"
            )
            # On vérifie s’il a effectivement disparu
            if self.bg_missing_count >= self.BG_FRAMES_TO_REMOVE:
                # On considère que le fond est parti
                old_id = self.active_background["id"]
                logger.info(
                    f"_handle_background_events (CAS 2) : fond '{self.active_background['shape']}' "
                    f"(id={old_id}) supprimé après {self.bg_missing_count} frames d’absence."
                )
                removed_bgs.append(old_id)
                self.active_background = None
                # On reconstruit baseline_objects sans ce fond
                self._rebuild_baseline_objects()
                # Reset des compteurs
                self.bg_missing_count = 0
                self.bg_candidate_shape = None
                self.bg_detect_count = 0
            return new_bgs, removed_bgs

        # 2.c) cas par défaut (improbable, déjà couvert ci-dessus)
        logger.debug("_handle_background_events : aucun changement détecté (cas par défaut).")
        return new_bgs, removed_bgs

    def _handle_object_events(
        self,
        frame: np.ndarray
    ) -> tuple[list[dict], list[str]]:
        new_objs: list[dict]     = []
        removed_objs: list[str]  = []

        # 1) Si baseline_objects n'est pas encore prête, on sort
        if self.baseline_objects is None:
            logger.debug("_handle_object_events : baseline_objects non initialisée, on quitte.")
            return new_objs, removed_objs

        # 2) Exécuter DepthProcessor pour détecter des contours “autres que le fond”
        try:
            frame_smooth = cv2.medianBlur(frame, 3)
            result_obj = self.depth_processor_4.process(frame_smooth, self.baseline_objects)
        except RuntimeError:
            logger.debug("_handle_object_events : DepthProcessor a échoué cette frame.")
            return new_objs, removed_objs

        if result_obj is None:
            logger.debug("_handle_object_events : result_obj est None, rien à faire.")
            return new_objs, removed_objs

        cnts_obj = result_obj.contours
        logger.debug(f"_handle_object_events : {len(cnts_obj)} contours extraits du DepthMask.")
        dets_for_obj: list[tuple] = []
        for cnt in cnts_obj:
            area = float(cv2.contourArea(cnt))
            if area < self.config.small_area_threshold:
                continue

            shape = self.shape_classifier.classify_3d(cnt, result_obj.mapped, self.baseline_objects)
            if shape is None:
                continue

            M = cv2.moments(cnt)
            if M.get("m00", 0) == 0:
                continue
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
            x, y, w, h = cv2.boundingRect(cnt)
            dets_for_obj.append((shape, cx, cy, area, 0.0, float(w), float(h)))
            logger.debug(f"  → candidat objet '{shape}' à ({cx:.1f},{cy:.1f}), area={area:.1f}")

        # 3) Mettre à jour le cluster_tracker pour avoir les IDs stables
        self.cluster_tracker.update(dets_for_obj)
        evs_obj, removed_ids_obj = self.object_detector.detect()
        logger.debug(f"_handle_object_events : object_detector renvoie {len(evs_obj)} évènements, {len(removed_ids_obj)} suppressions potentielles")

        # 4) Parcourir les événements « arrivés »
        for ev in evs_obj:
            if ev["type"] == "object":
                oid = ev["id"]
                if oid not in self.obj_detect_counts:
                    self.obj_detect_counts[oid]  = 1
                    self.obj_missing_counts[oid] = 0
                    logger.debug(f"Object candidat (nouveau) → id={oid}, shape={ev['shape']} (compteur détecté=1)")
                else:
                    self.obj_detect_counts[oid] += 1
                    self.obj_missing_counts[oid] = 0
                    logger.debug(f"Object '{ev['shape']}' (id={oid}) déjà vu, compteur détecté={self.obj_detect_counts[oid]}")

                if oid not in self.active_objects and self.obj_detect_counts[oid] >= self.OBJ_FRAMES_TO_ADD:
                    # valider l’objet, le blitter, l’envoyer au front
                    self.active_objects[oid] = ev.copy()
                    self.baseline_objects   = self._blit_zone_on_baseline(self.baseline_objects, ev)
                    new_objs.append({
                        "id":    ev["id"],
                        "type":  "object",
                        "shape": ev["shape"],
                        "cx":    ev["cx"],
                        "cy":    ev["cy"],
                        "w":     ev["w"],
                        "h":     ev["h"],
                        "angle": ev.get("angle", 0.0),
                        "scale": ev.get("scale", 1.0),
                    })
                    logger.info(f"_handle_object_events : objet validé → {ev['shape']} (id={oid}) ajouté à baseline_objects")
                    # Réinitialiser
                    self.obj_detect_counts[oid]  = 0
                    self.obj_missing_counts[oid] = 0

        #  Suppressions potentielles :
        all_ids = set(self.obj_detect_counts.keys()) | set(self.active_objects.keys())
        for oid in all_ids:
            if oid not in [e["id"] for e in evs_obj]:
                self.obj_missing_counts[oid] = self.obj_missing_counts.get(oid, 0) + 1
                logger.debug(f"_handle_object_events : objet id={oid} non détecté cette frame (missing_count={self.obj_missing_counts[oid]})")
            else:
                self.obj_missing_counts[oid] = 0

            if oid in self.active_objects and self.obj_missing_counts[oid] >= self.OBJ_FRAMES_TO_REMOVE:
                logger.info(f"_handle_object_events : objet '{self.active_objects[oid]['shape']}' (id={oid}) supprimé après {self.OBJ_FRAMES_TO_REMOVE} frames manquées")
                del self.active_objects[oid]
                removed_objs.append(oid)
                self._rebuild_baseline_objects()
                del self.obj_detect_counts[oid]
                del self.obj_missing_counts[oid]

        return new_objs, removed_objs

    def _rebuild_baseline_objects(self) -> None:
        """
        Reconstruit self.baseline_objects **à partir de** self.baseline_sand, puis en
        « blittant » :  1) le fond actif (s’il existe),  2) chaque objet actif.  
        On écrit le résultat dans self.baseline_objects.
        """
        if self.baseline_sand is None:
            # pas encore initialisé → on ne fait rien
            return

        # 1) repartir du sable pur
        base = self.baseline_sand.copy()

        # 2) si un fond est actif, on le colle en premier
        if self.active_background is not None:
            base = self._blit_zone_on_baseline(base, self.active_background)

        # 3) pour chaque objet encore actif, on colle son masque
        for obj_id, event in self.active_objects.items():
            base = self._blit_zone_on_baseline(base, event)

        # 4) on met à jour l’attribut
        self.baseline_objects = base
    
    def _check_background_presence(
        self,
        frame: np.ndarray
    ) -> bool:
        """
        Compare la zone (bounding box) du fond actif entre `frame` et `self.baseline_sand`.
        Si trop de pixels ont des valeurs très proches → le fond est toujours là.
        Si tous (ou trop) les pixels tombent sous un seuil → le fond a disparu.
        Retourne True si le fond est encore présent, False sinon.
        """

        if self.active_background is None or self.baseline_sand is None:
            return False

        # 1) On extrait la bounding box du fond
        ev = self.active_background
        cx, cy = int(ev["cx"]), int(ev["cy"])
        w_box, h_box = int(ev["w"]), int(ev["h"])

        # définir les coins de la bbox
        x0 = max(0, cx - w_box // 2)
        y0 = max(0, cy - h_box // 2)
        x1 = min(self.baseline_sand.shape[1], x0 + w_box)
        y1 = min(self.baseline_sand.shape[0], y0 + h_box)

        # 2) Extraire le patch du frame courant et le patch de la baseline_sand
        patch_frame = frame[y0:y1, x0:x1].astype(int)
        patch_sand  = self.baseline_sand[y0:y1, x0:x1].astype(int)

        # 3) Calculer la différence absolue
        diff = np.abs(patch_frame - patch_sand)

        # 4) Seuil de présence : si trop de pixels ont diff > removal_threshold,
        #    on déduit que le fond est toujours là. Sinon, il a disparu.
        mask_present = diff > self.config.removal_threshold
        # ratio de pixels « toujours présents »
        taux_present = float(mask_present.sum()) / float(mask_present.size)

        # Si le pourcentage de pixels « proches de la baseline sand » est trop grand,
        # on estime que le fond a disparu. Sinon, on le considère encore là.
        if taux_present < self.config.removal_ratio:
            # La plupart des pixels sont presque identiques à la baseline_sand → fond disparu
            return False
        else:
            return True
    
    def _initialize_baseline_for_channel4(self, frame: np.ndarray) -> None:
        """
        Appeler cette méthode **une seule fois** dès que l’on détecte le tout premier passage
        en outil '4' (canal fond+objets). On calcule baseline_sand (sable seul) et on
        initialise baseline_objects à la même valeur. Ensuite, on remet à zéro tout ce qui
        concerne le fond/objets actifs.
        """
        # 1) calculer baseline “sable seul”
        baseline_sand = self.baseline_calc.ensure_baseline_ready(frame)
        self.baseline_sand = baseline_sand.copy()

        # 2) la baseline “sable+fond+objets” de départ est strictement égale à “sable seul”
        self.baseline_objects = self.baseline_sand.copy()

        # 3) pas encore de fond ni d’objet visible
        self.active_background = None
        self.active_objects = {}

        # 4) on autorise immédiatement l’ajout d’un nouveau fond
        #    (skip_removal_ids vide ou mis à jour plus bas)
        self.skip_removal_ids.clear()

        # 5) on indique que la baseline de base (sable) est maintenant prête
        self.baseline_ready = True
        logger.info("Baseline sand (sable) initialisée pour canal 4.")

    
if __name__ == '__main__':

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

    logger.info("Starting Artineo Kinect module...")

    # Fetch config from remote
    client = ArtineoClient(module_id=4, host="artineo.local", port=8000)
    raw_conf = client.fetch_config()

    controller = MainController(
        raw_config=raw_conf,
        client=client,
    )

    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
