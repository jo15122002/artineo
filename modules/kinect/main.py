import asyncio
import logging
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
        self.stroke_tracker = StrokeTracker(proximity_threshold=5.0)

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

        self.current_tool: str = '1'  # default tool
        self.tool_channel = {'1':0, '2':1, '3':2, '4':3}
        h, w = self.config.roi_height, self.config.roi_width

        self.final_drawings = {
            t: np.zeros((h, w, 3), dtype=float)
            for t in self.tool_channel
        }

        self.all_strokes: list = []  # all strokes detected

        if self.config.debug_mode:
            self.display = DisplayManager([])
        else:
            self.display = None

        logger.info("MainController initialized.")

    async def run(self) -> None:
        """
        Main async loop:
        - Connect WS
        - Continuously capture depth frames
        - Update baseline, map depth, accumulate composite
        - Detect strokes (ou objects) et filtrer temporellement
        - Send payload
        """
        # 1) Initialisation
        self.kinect.open()
        if not self.config.bypass_ws:
            await self.payload_sender.connect()

        alfa_decay = 0.05

        try:
            while True:
                # 2) Acquire & check new frame
                if not self.kinect.has_new_depth_frame():
                    await asyncio.sleep(0.01)
                    continue
                frame = self.kinect.get_depth_frame()

                # 3) Baseline
                try:
                    baseline = self.baseline_calc.baseline
                except RuntimeError:
                    self.baseline_calc.update(frame)
                    continue

                # 4) Depth → mapped
                result = self.depth_processor.process(frame, baseline)

                # 5) Mise à jour du composite (bosses)
                ch        = self.tool_channel[self.current_tool]
                diff_raw = (result.mapped.astype(int) - 128).clip(min=0).astype(float)

                mask_sig = diff_raw > self.config.stroke_intensity_thresh
                buf = self.final_drawings[self.current_tool][:,:,ch]
                buf[mask_sig] = (1 - self.config.alpha) * buf[mask_sig] + self.config.alpha * diff_raw[mask_sig]
                buf[~mask_sig] *= (1 - alfa_decay)

                composite = cv2.convertScaleAbs(self.final_drawings[self.current_tool])

                # 6) Debug display
                if self.display:
                    self.display.show("Composite", composite)
                    if self.display.process_events() == ord('q'):
                        break

                # 7) Détection
                if self.current_tool != '4':
                    # strokes + filtrage temporel
                    raw     = self.brush_detector.detect(composite, self.current_tool)
                    new     = self.stroke_tracker.update(raw, self.all_strokes)
                    self.all_strokes.extend(new)
                    strokes = self.all_strokes
                    objects = []
                else:
                    # clustering + objets
                    detections = []
                    for cnt in result.contours:
                        shape = self.shape_classifier.classify(cnt)
                        M = cv2.moments(cnt)
                        if M['m00'] == 0:
                            continue
                        cx = M['m10'] / M['m00']
                        cy = M['m01'] / M['m00']
                        area = float(cv2.contourArea(cnt))
                        x,y,w,h = cv2.boundingRect(cnt)
                        detections.append((shape, cx, cy, area, 0.0, float(w), float(h)))
                    self.cluster_tracker.update(detections)
                    strokes = []
                    objects = self.object_detector.detect()

                # 8) Envoi WS
                if not self.config.bypass_ws:
                    await self.payload_sender.send(
                        tool_id=self.current_tool,
                        strokes=strokes,
                        objects=objects,
                    )

                # 9) Lâcher le thread
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down.")
        finally:
            self.kinect.close()
            if not self.config.bypass_ws:
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
