import asyncio
import logging
import cv2

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

logger = logging.getLogger(__name__)

class DisplayManager:
    def __init__(self, windows: list[str]):
        for w in windows:
            cv2.namedWindow(w, cv2.WINDOW_NORMAL)
    def show(self, name: str, img):
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
        self.baseline_calc = BaselineCalculator(self.config)
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
        self.payload_sender = PayloadSender(self.client, logger=logger)

        self.current_tool: str = '1'  # default tool

        if self.config.debug_mode:
            self.display = DisplayManager(["Depth frame", "Mapped depth"])
        else:
            self.display = None

        logger.info("MainController initialized.")

    async def run(self) -> None:
        """
        Main async loop:
          - Connect WS
          - Continuously capture depth frames
          - Update baseline, map depth, detect strokes/objects
          - Send payloads
        """
        # Open Kinect sensor
        self.kinect.open()
        # Connect and start heartbeat
        await self.payload_sender.connect()

        try:
            while True:
                # 1. Acquire frame
                if not self.kinect.has_new_depth_frame():
                    await asyncio.sleep(0.01)
                    continue
                frame = self.kinect.get_depth_frame()

                # 2. Update baseline if needed
                try:
                    baseline = self.baseline_calc.baseline
                except RuntimeError:
                    logger.warning("Baseline not available, skipping frame.")
                    self.baseline_calc.update(frame)
                    continue

                # 3. Process depth
                result = self.depth_processor.process(frame, baseline)

                if self.display:
                    self.display.show("Depth frame", result.mapped)
                    key = self.display.process_events()
                    if key == ord('q'):
                        break

                # 4. Detection phase
                if self.current_tool != '4':
                    strokes = self.brush_detector.detect(result.mapped, self.current_tool)
                    objects = []
                else:
                    # Prepare detections for clustering
                    detections = []
                    for cnt in result.contours:
                        shape = self.shape_classifier.classify(cnt)
                        M = cv2.moments(cnt)
                        if M['m00'] == 0:
                            continue
                        cx = M['m10'] / M['m00']
                        cy = M['m01'] / M['m00']
                        area = float(cv2.contourArea(cnt))
                        x, y, w, h = cv2.boundingRect(cnt)
                        angle = 0.0  # placeholder for future angle logic
                        detections.append((shape, cx, cy, area, angle, float(w), float(h)))
                    self.cluster_tracker.update(detections)
                    strokes = []
                    objects = self.object_detector.detect()

                # 5. Send JSON payload
                await self.payload_sender.send(
                    tool=self.current_tool,
                    strokes=strokes,
                    objects=objects,
                )

                # 6. Throttle loop (simulate Kinect frame rate)
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down.")
        finally:
            self.kinect.close()
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
    client = ArtineoClient(module_id=4, host="artineo.local", port=8000)
    raw_conf = client.fetch_config()

    controller = MainController(
        raw_config=raw_conf
    )
    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
