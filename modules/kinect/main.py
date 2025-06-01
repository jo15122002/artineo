import asyncio
import logging
from typing import Dict
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
from baseline_calculator import BaselineCalculator
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
    def __init__(self, windows: list[str]):
        self.windows = windows
        for w in self.windows:
            cv2.namedWindow(w, cv2.WINDOW_NORMAL)

    def show(self, name: str, img):
        if name not in self.windows:
            cv2.namedWindow(name, cv2.WINDOW_NORMAL)
            self.windows.append(name)
        cv2.imshow(name, img)

    def process_events(self):
        # rafraîchit toutes les fenêtres et capte les touches
        return cv2.waitKey(1) & 0xFF

class MainController:
    """
    Orchestrates the Artineo Kinect pipeline:
      1. Initialize services (Kinect, processors, detectors, sender)
      2. Fetch and validate config
      3. Run async loop: capture -> process -> detect -> send
    """
    def __init__(
        self,
        raw_config: dict,
        channel_selector: ChannelSelector = KeyboardChannelSelector(),
        client: ArtineoClient = None,
    ):
        logger.info("Initializing MainController...")

        # 1. Load and validate configuration
        self.config = Config(**(raw_config or {}))

        # 2. ArtineoClient setup
        self.client = client

        # 3. Initialize components
        self.kinect = KinectInterface(self.config, logger=logger)
        self.baseline_calc = BaselineCalculator(self.config, logger=logger)
        self.template_manager = TemplateManager(
            template_dir=self.config.template_dir,
            n_profile=self.config.n_profile,
            area_threshold=self.config.area_threshold,
            small_area_threshold=self.config.small_area_threshold,
        )
        self.shape_classifier = ShapeClassifier(
            depth_templates=self.template_manager.depth_templates,
            small_area_threshold=self.config.small_area_threshold,
            # match_threshold=self.config.area_threshold
        )
        self.cluster_tracker = ClusterTracker(
            max_history=self.config.n_profile,
            tol=self.config.display_scale,
            area_threshold=self.config.area_threshold,
        )
        self.depth_processor = DepthProcessor(self.config)
        self.depth_processor_4 = DepthProcessor(
            self.config,
            mask_threshold=2,
            morph_kernel=5
        )

        # tool / channel mapping
        self.current_tool: str = '1'  # default tool
        self.tool_channel = {'1':0, '2':1, '3':2, '4':3}
        self.channel_selector: ChannelSelector = channel_selector

        # stroke-tracking setup
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

        # brush detector (tools 1–3)
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

        # object (and background) detector (tool 4)
        self.object_detector = ObjectDetector(
            cluster_tracker=self.cluster_tracker,
            template_sizes=self.template_manager.template_sizes,
            roi_width=self.config.roi_width,
            roi_height=self.config.roi_height,
        )

        # WS payload sender
        if not self.config.bypass_ws:
            self.payload_sender = PayloadSender(self.client, logger=logger)

        # buffers for drawing & events
        h, w = self.config.roi_height, self.config.roi_width
        self.final_drawings = {
            t: np.zeros((h, w, 3), dtype=float)
            for t in self.tool_channel
        }
        self.all_objects: Dict[str, Dict] = {}
        self.backgrounds_by_id: Dict[str, Dict] = {}

        # ROI calibrator
        self.roi_calibrator = RoiCalibrator(self.kinect, scale=2)

        # display
        if self.config.debug_mode:
            self.display = DisplayManager([])
        else:
            self.display = None
            
        self.background_detected = False
        self.current_background_id: str | None = None

        # Nouvelle baseline pour la détection DES OBJETS
        self.obj_baseline_calc = BaselineCalculator(self.config, logger=logger)
        self.obj_baseline_ready = False
        
        self.channel4_detector = Channel4Detector(
            depth_processor=self.depth_processor_4,
            shape_classifier=self.shape_classifier,
            cluster_tracker=self.cluster_tracker,
            object_detector=self.object_detector,
            small_area_threshold=self.config.small_area_threshold,
        )

        logger.info("MainController initialized.")

    async def run(self) -> None:
        # --- init Kinect & WS ---
        self.kinect.open()
        if not self.config.bypass_ws:
            self.payload_sender.start()

        try:
            while True:
                new_strokes = []
                removed_strokes = []
                new_backgrounds = []
                removed_backgrounds = []
                new_objects = []
                removed_objects = []

                # 1) Changement d’outil ?
                next_tool = await self.channel_selector.get_next_channel()
                if next_tool and next_tool != self.current_tool:
                    old = self.current_tool
                    self.current_tool = next_tool
                    logger.info(f"Tool switched → {self.current_tool}")

                    # 1.1) Transformer les anciens strokes en “persistents”
                    old_slots = self.strokes_by_tool[old]
                    for sid, ev in old_slots.items():
                        ev['persistent'] = True
                        self.stroke_lifetimers[old].ages.pop(sid, None)

                    # 1.2) **Toujours reset baseline** quand on change d’outil
                    self.baseline_calc.reset()

                    # 1.3) Reset visuels / buffers
                    for buf in self.final_drawings.values():
                        buf.fill(0)

                    # 1.4) Ré-émettre les strokes persistents du nouveau canal
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

                # 2) Récupérer le frame de profondeur
                if not self.kinect.has_new_depth_frame():
                    await asyncio.sleep(0.01)
                    continue
                frame = self.kinect.get_depth_frame()

                # 3) ROI calibrage si demandé
                if self.config.calibrate_roi:
                    rx, ry = self.roi_calibrator.run()
                    logger.info(f"ROI calibrated → x={rx}, y={ry}")
                    self.config.calibrate_roi = False

                # 4) Affichage brut (debug) si activé
                if self.display:
                    self.display.show('depth', frame)
                    if self.display.process_events() == ord('q'):
                        break

                # 5) OUTILS 1–3 (pinceaux) : même logique qu’avant
                if self.current_tool in ('1', '2', '3'):
                    try:
                        baseline = self.baseline_calc.ensure_baseline_ready(frame)
                    except RuntimeError:
                        continue

                    # 5.2) Une fois baseline ready, on fait la soustraction + composite
                    result = self.depth_processor.process(frame, baseline)
                    ch = self.tool_channel[self.current_tool]
                    diff = (result.mapped.astype(int) - 128).clip(min=0).astype(float)
                    mask = diff > self.config.stroke_intensity_thresh
                    buf = self.final_drawings[self.current_tool][:, :, ch]
                    buf[mask] = (1 - self.config.alpha) * buf[mask] + self.config.alpha * diff[mask]
                    buf[~mask] *= (1 - 0.1)
                    composite = cv2.convertScaleAbs(self.final_drawings[self.current_tool])

                    # 5.3) Détection de strokes (inchangée)
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

                # 6) OUTIL 4 (canal fond + objets) : on réutilise exactement la même logique de baseline
                else:  # self.current_tool == '4'
                    try:
                        baseline = self.baseline_calc.ensure_baseline_ready(frame)
                    except RuntimeError:
                        continue

                    # 6.2) Dès que baseline_for_bg est disponible, on passe à la détection
                    nb, rb, no, ro = self._process_channel4(frame)
                    new_backgrounds.extend(nb)
                    removed_backgrounds.extend(rb)
                    new_objects.extend(no)
                    removed_objects.extend(ro)

                # 7) Envoi WS des diffs (strokes, backgrounds, objects)
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

                # 8) Yield
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down.")
        finally:
            # --- cleanup ---
            self.kinect.close()
            if not self.config.bypass_ws:
                # On supprime tout ce qui reste pour éviter d’afficher des résidus
                all_stroke_ids = []
                for slots in self.strokes_by_tool.values():
                    all_stroke_ids.extend(slots.keys())
                all_obj_ids = list(self.all_objects.keys())
                all_bg_ids = list(self.backgrounds_by_id.keys())

                await self.payload_sender.send_update(
                    new_strokes=[],
                    remove_strokes=all_stroke_ids,
                    new_backgrounds=[],
                    remove_backgrounds=all_bg_ids,
                    new_objects=[],
                    remove_objects=all_obj_ids,
                )
                await self.payload_sender.stop()

            if self.display:
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

        # --- 3) Affichage debug (si nécessaire) ---
        if self.display:
            # Pour visualiser la carte 8 bits, on la recalcule ici (map + blur),
            # mais uniquement pour l’affichage. Ça ne re-crée pas de bruit.
            depth_res = self.depth_processor_4.process(raw_frame, baseline_for_bg)
            mapped = depth_res.mapped
            self._display_detection_debug(
                mapped,
                cnts_raw,
                bg_events,
                obj_events
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

    def _display_detection_debug(
        self,
        raw_frame: np.ndarray,
        contours: list[np.ndarray],
        candidate_backgrounds: list[dict],
        candidate_objects: list[dict]
    ):
        """
        Affiche dans la fenêtre 'debug4' le raw_frame (en 8-bit) annoté :
        - tous les contours en BLEU (non classifiés),
        - en ROUGE les contours ayant été classés background (shape returned),
        - en VERT les contours ayant été classés objets.
        - Ajoute un label textuel au-dessus de chaque bounding box.
        `raw_frame` est soit frame, soit result.mapped converti en 8-bit.
        """
        if not self.display:
            return

        # 1) Normalisation en 8-bit pour affichage
        img8 = cv2.convertScaleAbs(raw_frame)
        debug_img = cv2.cvtColor(img8, cv2.COLOR_GRAY2BGR)

        # 2) dessiner tous les contours (BLEU)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (255, 128, 0), 1)
            cv2.drawContours(debug_img, [cnt], -1, (255, 128, 0), 1)

        # 3) dessiner backgrounds validés (ROUGE) et label
        for ev in candidate_backgrounds:
            # on a les coordonnées (cx, cy, w, h) dans ev
            cx, cy, w_, h_ = int(ev['cx']), int(ev['cy']), int(ev['w']), int(ev['h'])
            x = int(cx - w_ / 2); y = int(cy - h_ / 2)
            cv2.rectangle(debug_img, (x, y), (x + int(w_), y + int(h_)), (0, 0, 255), 2)
            cv2.putText(
                debug_img,
                f"BG:{ev['shape']}",
                (x, max(y - 5, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )

        # 4) dessiner objects candidates (VERT) et label
        for ev in candidate_objects:
            cx, cy, w_, h_ = int(ev['cx']), int(ev['cy']), int(ev['w']), int(ev['h'])
            x = int(cx - w_ / 2); y = int(cy - h_ / 2)
            cv2.rectangle(debug_img, (x, y), (x + int(w_), y + int(h_)), (0, 255, 0), 2)
            cv2.putText(
                debug_img,
                f"OBJ:{ev['shape']}",
                (x, max(y - 5, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )

        # 5) afficher le tout
        self.display.show("debug4", debug_img)


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
