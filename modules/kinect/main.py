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
            mask_threshold=2,
            morph_kernel=5
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

        logger.info("MainController initialized.")

    async def run(self) -> None:
        # --- 1) Démarrage Kinect & WebSocket ---
        self.kinect.open()
        if not self.config.bypass_ws:
            self.payload_sender.start()

        # IDs des zones fraîchement ajoutées à ignorer pour la détection de retrait
        self.skip_removal_ids: set[str] = set()

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

                    # 2.d) Réinitialiser le contexte “fond” en canal 4
                    self.current_background_shape = None
                    self.current_background_id = None
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
                    buf[~mask] *= (1 - 0.1)
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
                    if not self.baseline_ready:
                        try:
                            baseline_dessin = self.baseline_calc.ensure_baseline_ready(frame)
                            self.baseline_manager.baseline = baseline_dessin.copy()
                            self.baseline_ready = True
                            logger.info("Baseline dessin injectée dans BaselineManager.")
                        except RuntimeError:
                            if self.config.debug_mode:
                                disp = cv2.convertScaleAbs(frame, alpha=255.0 / (frame.max() or 1))
                                cv2.imshow("Attente baseline", disp)
                                cv2.waitKey(1)
                            continue

                    baseline_for_bg = self.baseline_manager.get_baseline()

                    removal_bg_ids: List[str] = []
                    removal_obj_ids: List[str] = []

                    def _mark_removal(evt: dict):
                        shape_name = evt["shape"]
                        shape_id = evt["id"]
                        # Ignorer si dans skip_removal_ids
                        if shape_id in self.skip_removal_ids:
                            return
                        logger.debug(f"Detected removal: {shape_name} (id={shape_id})")
                        if shape_name.startswith("landscape_"):
                            removal_bg_ids.append(shape_id)
                            if shape_id == self.current_background_id:
                                self.current_background_shape = None
                                self.current_background_id = None
                        else:
                            removal_obj_ids.append(shape_id)

                    self.baseline_manager.detect_and_handle_removals(
                        frame,
                        send_event_fn=_mark_removal
                    )

                    logger.debug(f"Removed backgrounds: {removal_bg_ids}, Removed objects: {removal_obj_ids}")
                    removed_backgrounds.extend(removal_bg_ids)
                    removed_objects.extend(removal_obj_ids)

                    bg_events, obj_events, _cnts = self.channel4_detector.detect(
                        frame,
                        baseline_for_bg
                    )

                    # 7.e) Suivi du fond unique avec BackgroundTracker
                    shapes = [ev["shape"] for ev in bg_events]
                    new_bg_entries, removed_bg_entries = self.bg_tracker.update(shapes)

                    if new_bg_entries:
                        new_shape = new_bg_entries[0]["shape"]
                        cx = bg_events[0]["cx"]
                        cy = bg_events[0]["cy"]
                        w_box = bg_events[0]["w"]
                        h_box = bg_events[0]["h"]
                        new_id = self.baseline_manager.place_zone(new_shape, cx, cy, w_box, h_box)
                        self.current_background_shape = new_shape
                        self.current_background_id = new_id
                        self.skip_removal_ids.add(new_id)
                        new_backgrounds.append({
                            "id":    new_id,
                            "type":  "background",
                            "shape": new_shape,
                            "cx":    cx,
                            "cy":    cy,
                            "w":     w_box,
                            "h":     h_box,
                            "angle": bg_events[0].get("angle", 0.0),
                            "scale": bg_events[0].get("scale", 1.0),
                        })

                    for rid in removed_bg_entries:
                        if rid not in removed_backgrounds:
                            removed_backgrounds.append(rid)
                        if rid == self.current_background_id:
                            self.current_background_shape = None
                            self.current_background_id = None

                    # 7.f) Traitement des objets
                    if obj_events:
                        for ev in obj_events:
                            if ev["type"] == "background":
                                continue
                            name = ev["shape"]
                            cx, cy = ev["cx"], ev["cy"]
                            w_box, h_box = ev["w"], ev["h"]
                            new_id = self.baseline_manager.place_zone(name, cx, cy, w_box, h_box)
                            new_objects.append({
                                "id":    new_id,
                                "type":  "object",
                                "shape": name,
                                "cx":    cx,
                                "cy":    cy,
                                "w":     w_box,
                                "h":     h_box,
                                "angle": ev.get("angle", 0.0),
                                "scale": ev.get("scale", 1.0),
                            })

                    # On supprime la skip list **après** cette frame
                    self.skip_removal_ids.clear()

                # --- 8) Envoi WS des diffs (strokes, backgrounds, objets) ---
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
                for (name, x0, y0, w, h, unique_id, _orig_patch) in self.baseline_manager.placed_zones:
                    if name.startswith("landscape_"):
                        remaining_bg_ids.append(unique_id)
                    else:
                        remaining_obj_ids.append(unique_id)

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

    
    def _process_channel4(
        self,
        raw_frame: np.ndarray
    ) -> tuple[
        list[dict],  # new_backgrounds
        list[str],   # removed_backgrounds
        list[dict],  # new_objects
        list[str]    # removed_objects
    ]:
        new_backgrounds: list[dict] = []
        removed_backgrounds: list[str] = []
        new_objects: list[dict] = []
        removed_objects: list[str] = []

        # --- 1) Récupérer ou accumuler la baseline-fond ---
        try:
            baseline_for_bg = self.baseline_calc.ensure_baseline_ready(raw_frame)
        except RuntimeError:
            # on retourne vide : la baseline n'est pas encore prête
            return [], [], [], []

        # --- 2) Déléguer toute la détection à Channel4Detector ---
        bg_events, obj_events, cnts_raw = self.channel4_detector.detect(
            raw_frame,
            baseline_for_bg
        )

        # --- 4) Gestion des événements “fond” ---
        if not self.background_detected and bg_events:
            bg = bg_events[0]
            self.current_background_id = bg["id"]
            self.background_detected = True

            logger.info(
                "Fond initial détecté (3D) : %s (id=%s). Construction de la baseline-objets…",
                bg["shape"], bg["id"]
            )

            # Création de la baseline-objets
            self.obj_baseline_calc.reset()
            try:
                self.obj_baseline_calc.update(raw_frame)
                self.obj_baseline_ready = True
                logger.info("obj_baseline initialisée sur le fond détecté.")
            except RuntimeError as e:
                logger.warning("Impossible de calculer obj_baseline en une frame : %s", e)
                self.obj_baseline_ready = False

            new_backgrounds.append({
                "id":    bg["id"],
                "type":  "background",
                "shape": bg["shape"],
                "cx":    bg["cx"],
                "cy":    bg["cy"],
                "w":     bg["w"],
                "h":     bg["h"],
                "angle": bg["angle"],
                "scale": bg["scale"],
            })

        elif self.background_detected and bg_events:
            # Remplacement de fond
            rem = [ev for ev in bg_events if ev["id"] != self.current_background_id]
            if rem:
                bg_new = rem[0]
                old_id = self.current_background_id
                self.current_background_id = bg_new["id"]

                logger.info(
                    "Remplacement du fond : ancien id=%s → nouveau id=%s (shape=%s)",
                    old_id, bg_new["id"], bg_new["shape"]
                )
                removed_backgrounds.append(old_id)

                self.obj_baseline_calc.reset()
                try:
                    self.obj_baseline_calc.update(raw_frame)
                    self.obj_baseline_ready = True
                    logger.info("obj_baseline recalculée sur le nouveau fond.")
                except RuntimeError as e:
                    logger.warning("Impossible de recalculer obj_baseline : %s", e)
                    self.obj_baseline_ready = False

                new_backgrounds.append({
                    "id":    bg_new["id"],
                    "type":  "background",
                    "shape": bg_new["shape"],
                    "cx":    bg_new["cx"],
                    "cy":    bg_new["cy"],
                    "w":     bg_new["w"],
                    "h":     bg_new["h"],
                    "angle": bg_new["angle"],
                    "scale": bg_new["scale"],
                })

        # 4.1) Disparition effective du fond
        if self.background_detected and not bg_events:
            logger.info("Le fond (id=%s) a été retiré.", self.current_background_id)
            removed_backgrounds.append(self.current_background_id)
            self.background_detected = False
            self.obj_baseline_ready = False
            self.current_background_id = None
            self.obj_baseline_calc.reset()

        # --- 5) Gestion des objets (après validation du fond et baseline-objets prête) ---
        if self.background_detected and self.obj_baseline_ready:
            try:
                baseline_obj = self.obj_baseline_calc.baseline
                result_obj = self.depth_processor_4.process(raw_frame, baseline_obj)
            except RuntimeError:
                result_obj = None

            if result_obj is not None:
                cnts_obj = result_obj.contours
                dets_for_obj: list[tuple] = []
                for cnt in cnts_obj:
                    area = float(cv2.contourArea(cnt))
                    if area < self.config.small_area_threshold:
                        continue

                    shape = self.shape_classifier.classify_3d(
                        cnt,
                        result_obj.mapped
                    )
                    if shape is None:
                        continue

                    M = cv2.moments(cnt)
                    if M.get("m00", 0) == 0:
                        continue
                    cx = float(M["m10"] / M["m00"])
                    cy = float(M["m01"] / M["m00"])
                    x, y, w, h = cv2.boundingRect(cnt)
                    dets_for_obj.append((shape, cx, cy, area, 0.0, float(w), float(h)))

                self.cluster_tracker.update(dets_for_obj)

                evs_obj, removed_ids_obj = self.object_detector.detect()
                for ev in evs_obj:
                    if ev["type"] != "background":
                        new_objects.append(ev)
                for rid in removed_ids_obj:
                    if rid not in (self.current_background_id or []):
                        removed_objects.append(rid)

        return new_backgrounds, removed_backgrounds, new_objects, removed_objects

if __name__ == '__main__':

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

    logger.info("Starting Artineo Kinect module...")

    # Fetch config from remote
    client = ArtineoClient(module_id=4, host="localhost", port=8000)
    raw_conf = client.fetch_config()

    controller = MainController(
        raw_config=raw_conf,
        client=client,
    )

    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
