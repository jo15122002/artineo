import asyncio
import logging
from typing import Dict
import uuid
import cv2
import numpy as np

from config import Config
from kinect_interface import KinectInterface
from baseline_calculator import BaselineCalculator
from template_manager import TemplateManager
from shape_classifier import ShapeClassifier
from cluster_tracker import ClusterTracker
from depth_processor import DepthProcessor
from brush_detector import BrushStrokeDetector
from object_detector import ObjectDetector
from payload_sender import PayloadSender
from frame_smoother import FrameSmoother
from stroke_accumulator import StrokeAccumulator
from stroke_tracker import StrokeTracker
from channel_selector import ChannelSelector
from keyboard_selector import KeyboardChannelSelector
from stroke_lifetimer import StrokeLifeTimer
from stroke_confirm_tracker import StrokeConfirmTracker

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
    ):
        
        logger.info("Initializing MainController...")

        # 1. Load and validate configuration
        self.config = Config(**(raw_config or {}))

        # 2. ArtineoClient setup
        self.client = ArtineoClient(
            module_id=self.config.module_id,
            host=self.config.host,
            port=self.config.port,
        )

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
            small_templates=self.template_manager.small_templates,
            shape_templates=self.template_manager.forme_templates,
            background_profiles=self.template_manager.background_profiles,
            use_matchshapes=self.config.use_matchshapes,
            small_area_threshold=self.config.small_area_threshold,
            area_threshold=self.config.area_threshold,
        )
        self.cluster_tracker = ClusterTracker(
            max_history=self.config.n_profile,
            tol=self.config.display_scale,
            area_threshold=self.config.area_threshold,
        )
        self.depth_processor = DepthProcessor(self.config)
        self.smoother = FrameSmoother(window_size=10)
        h, w = self.config.roi_height, self.config.roi_width
        self.acc = StrokeAccumulator(
            tools=['1','2','3','4'],
            height=h, width=w,
            alpha=self.config.alpha,
            abs_mode=True   # True = bosses & creux
        )
        
        self.current_tool: str = '1'  # default tool
        self.tool_channel = {'1':0, '2':1, '3':2, '4':3}
        self.channel_selector: ChannelSelector = channel_selector
        
        self.stroke_tracker = StrokeTracker(proximity_threshold=5.0)
        self.stroke_lifetimers = {
            tool: StrokeLifeTimer(max_age=5)
            for tool in self.tool_channel
        }
        self.stroke_confirm = StrokeConfirmTracker(
            proximity_threshold=5.0,
            min_confirm= self.config.stroke_confirmation_frames
        )
        self.strokes_by_tool: Dict[str, Dict[str, dict]] = {
            '1': {},
            '2': {},
            '3': {},
            '4': {}
        }

        # Load brush image for stroke detection
        brush_path = Path(self.config.template_dir).parent.joinpath(
            "brushes", "brush3.png"
        )
        brush_img = cv2.imread(str(brush_path), cv2.IMREAD_GRAYSCALE)
        if brush_img is None:
            raise FileNotFoundError(f"Brush image not found: {brush_path}")
        self.brush_detector = BrushStrokeDetector(
            brush=brush_img,
            config=self.config,
        )

        self.object_detector = ObjectDetector(
            cluster_tracker=self.cluster_tracker,
            template_sizes=self.template_manager.template_sizes,
            roi_width=self.config.roi_width,
            roi_height=self.config.roi_height,
        )

        if not self.config.bypass_ws:
            self.payload_sender = PayloadSender(self.client, logger=logger)

        h, w = self.config.roi_height, self.config.roi_width

        self.final_drawings = {
            t: np.zeros((h, w, 3), dtype=float)
            for t in self.tool_channel
        }

        self.all_strokes: Dict[str, Dict] = {}
        self.all_objects: Dict[str, Dict] = {}

        if self.config.debug_mode:
            self.display = DisplayManager([])
        else:
            self.display = None

        logger.info("MainController initialized.")

    async def run(self) -> None:
        # --- init Kinect & WS ---
        self.kinect.open()
        if not self.config.bypass_ws:
            await self.payload_sender.connect()

        alfa_decay = 0.05
        prox = self.stroke_tracker.proximity_threshold

        try:
            while True:
                # Préparation des diffs pour CE cycle
                new_strokes = []
                removed_ids = []
                new_objects = []
                remove_objects = []

                # --- 1) Changement de canal ? ---
                next_tool = await self.channel_selector.get_next_channel()
                if next_tool and next_tool != self.current_tool:
                    old = self.current_tool
                    self.current_tool = next_tool
                    logger.info(f"Tool switched → {self.current_tool}")

                    # a) marque tous les strokes dynamiques de l'ancien canal en persistent
                    old_slots = self.strokes_by_tool[old]
                    for sid, ev in old_slots.items():
                        ev['persistent'] = True
                        # on retire du lifetimer pour qu'ils ne soient plus purgés
                        self.stroke_lifetimers[old].ages.pop(sid, None)

                    # b) réinit baseline & buffers
                    self.baseline_calc.reset()
                    for buf in self.final_drawings.values():
                        buf.fill(0)

                    # c) ré-émet TOUS les strokes persistants du nouveau canal
                    new_slots = self.strokes_by_tool[self.current_tool]
                    persistent_batch = [ev for ev in new_slots.values() if ev.get('persistent')]
                    if persistent_batch:
                        await self.payload_sender.send_update(
                            new_strokes=persistent_batch,
                            remove_strokes=[],
                            new_objects=[],
                            remove_objects=[]
                        )

                # --- 2) Acquire & skip si pas de frame ---
                if not self.kinect.has_new_depth_frame():
                    await asyncio.sleep(0.01)
                    continue
                frame = self.kinect.get_depth_frame()

                # --- 3) Baseline ---
                try:
                    baseline = self.baseline_calc.baseline
                except RuntimeError:
                    self.baseline_calc.update(frame)
                    continue

                # --- 4) Depth → mapped + contours ---
                result = self.depth_processor.process(frame, baseline)

                # --- 5) Accumulation composite pour outils 1–3 ---
                if self.current_tool in ('1','2','3'):
                    ch   = self.tool_channel[self.current_tool]
                    diff = (result.mapped.astype(int) - 128).clip(min=0).astype(float)
                    mask = diff > self.config.stroke_intensity_thresh
                    buf  = self.final_drawings[self.current_tool][:,:,ch]
                    buf[mask]   = (1-self.config.alpha)*buf[mask] + self.config.alpha*diff[mask]
                    buf[~mask] *= (1-alfa_decay)
                    composite = cv2.convertScaleAbs(self.final_drawings[self.current_tool])
                else:
                    composite = None

                # --- 6) Détection strokes OU objets ---
                if self.current_tool != '4':
                    # a) raw, unique, confirmed
                    raw       = self.brush_detector.detect(composite, self.current_tool)
                    dynamic_values = list(self.strokes_by_tool[self.current_tool].values())
                    unique    = self.stroke_tracker.update(raw, dynamic_values)
                    confirmed = self.stroke_confirm.update(unique)

                    # b) ajoute uniquement les strokes dynamiques validées
                    slots = self.strokes_by_tool[self.current_tool]
                    for ev in confirmed:
                        if ev['size'] > self.config.stroke_size_max:
                            continue
                        ev['persistent'] = False
                        sid = str(uuid.uuid4())
                        ev['id'] = sid
                        slots[sid] = ev
                        new_strokes.append(ev)

                    # c) lifetimer sur dynamiques seulement
                    #    - ne prend pas en compte les persistantes
                    dynamic_slots = {
                        sid: ev
                        for sid, ev in slots.items()
                        if not ev.get('persistent', False)
                    }

                    # d) compute active_ids parmi ces dynamiques
                    active_ids = []
                    for sid, ev in dynamic_slots.items():
                        for r in raw:
                            if abs(r['x'] - ev['x']) <= prox and abs(r['y'] - ev['y']) <= prox:
                                active_ids.append(sid)
                                break

                    # e) purge via StrokeLifeTimer
                    lifetimer = self.stroke_lifetimers[self.current_tool]
                    stale = lifetimer.update(active_ids)
                    for sid in stale:
                        del slots[sid]
                        removed_ids.append(sid)

                else:
                    # clustering + objets
                    dets = []
                    for cnt in result.contours:
                        shape = self.shape_classifier.classify(cnt)
                        M = cv2.moments(cnt)
                        if M['m00'] == 0:
                            continue
                        cx = M['m10']/M['m00']; cy = M['m01']/M['m00']
                        area = float(cv2.contourArea(cnt))
                        x,y,w,h = cv2.boundingRect(cnt)
                        dets.append((shape,cx,cy,area,0.0,float(w),float(h)))

                    self.cluster_tracker.update(dets)
                    valid = self.object_detector.detect()
                    for obj in valid:
                        oid = str(uuid.uuid4())
                        obj['id'] = oid
                        self.all_objects[oid] = obj
                        new_objects.append(obj)

                # --- 7) Envoi WS des diffs dynamiques ---
                if not self.config.bypass_ws and (
                    new_strokes or removed_ids or new_objects or remove_objects
                ):
                    await self.payload_sender.send_update(
                        new_strokes=new_strokes,
                        remove_strokes=removed_ids,
                        new_objects=new_objects,
                        remove_objects=remove_objects,
                    )

                # petit yield
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down.")
        finally:
            # cleanup final
            self.kinect.close()
            if not self.config.bypass_ws:
                # 1) Collecte de TOUS les IDs de strokes, sur tous les outils
                all_ids = []
                for slots in self.strokes_by_tool.values():
                    all_ids.extend(slots.keys())

                # 2) On envoie un remove_strokes massif pour tout supprimer
                await self.payload_sender.send_update(
                    new_strokes=[],
                    remove_strokes=all_ids,
                    new_objects=[],
                    remove_objects=list(self.all_objects.keys()),
                )
                await self.payload_sender.close()

            if self.display:
                cv2.destroyAllWindows()
            logger.info("Shutdown complete.")



if __name__ == '__main__':
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

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

    logger.info("Starting Artineo Kinect module...")

    # Fetch config from remote
    client = ArtineoClient(module_id=4, host="localhost", port=8000)
    raw_conf = client.fetch_config()
    # raw_conf = {}

    controller = MainController(
        raw_config=raw_conf
    )

    del client

    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
