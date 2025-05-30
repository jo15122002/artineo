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

        logger.info("MainController initialized.")

    async def run(self) -> None:
        # --- init Kinect & WS ---
        self.kinect.open()
        if not self.config.bypass_ws:
            self.payload_sender.start()

        alfa_decay = 0.1
        prox = self.stroke_tracker.proximity_threshold

        try:
            while True:
                # prepare diff lists
                new_strokes = []
                removed_strokes = []
                new_backgrounds = []
                removed_backgrounds = []
                new_objects = []
                removed_objects = []

                # 1) channel switch?
                next_tool = await self.channel_selector.get_next_channel()
                if next_tool and next_tool != self.current_tool:
                    old = self.current_tool
                    self.current_tool = next_tool
                    logger.info(f"Tool switched → {self.current_tool}")

                    # make old tool's dynamic strokes persistent
                    old_slots = self.strokes_by_tool[old]
                    for sid, ev in old_slots.items():
                        ev['persistent'] = True
                        self.stroke_lifetimers[old].ages.pop(sid, None)

                    # reset baseline & drawing buffers
                    self.baseline_calc.reset()
                    for buf in self.final_drawings.values():
                        buf.fill(0)

                    # re-send all persistent strokes of new tool
                    new_slots = self.strokes_by_tool[self.current_tool]
                    persistent = [
                        ev for ev in new_slots.values() if ev.get('persistent')
                    ]
                    if persistent and not self.config.bypass_ws:
                        await self.payload_sender.send_update(
                            new_strokes=persistent,
                            remove_strokes=[],
                            new_backgrounds=[],
                            remove_backgrounds=[],
                            new_objects=[],
                            remove_objects=[]
                        )

                # 2) get depth frame
                if not self.kinect.has_new_depth_frame():
                    await asyncio.sleep(0.01)
                    continue
                frame = self.kinect.get_depth_frame()

                # ROI calibration
                if self.config.calibrate_roi:
                    rx, ry = self.roi_calibrator.run()
                    logger.info(f"ROI calibrated → x={rx}, y={ry}")
                    self.config.calibrate_roi = False

                if self.display:
                    self.display.show('depth', frame)
                    if self.display.process_events() == ord('q'):
                        break

                # 3) baseline
                try:
                    baseline = self.baseline_calc.baseline
                except RuntimeError:
                    self.baseline_calc.update(frame)
                    continue

                # 4) depth → mapped + contours
                result = self.depth_processor.process(frame, baseline)

                # 5) composite for tools 1–3
                if self.current_tool in ('1','2','3'):
                    ch = self.tool_channel[self.current_tool]
                    diff = (result.mapped.astype(int) - 128).clip(min=0).astype(float)
                    mask = diff > self.config.stroke_intensity_thresh
                    buf = self.final_drawings[self.current_tool][:,:,ch]
                    buf[mask] = (1-self.config.alpha)*buf[mask] + self.config.alpha*diff[mask]
                    buf[~mask] *= (1-alfa_decay)
                    composite = cv2.convertScaleAbs(self.final_drawings[self.current_tool])
                    alfa_decay = alfa_decay * 0.9 + 0.11
                else:
                    composite = None

                # 6) stroke vs object/background detection
                if self.current_tool != '4':
                    # strokes branch
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

                    # lifetimer purge
                    dynamic_slots = {
                        sid: ev
                        for sid, ev in slots.items()
                        if not ev.get('persistent', False)
                    }
                    active_ids = []
                    for sid, ev in dynamic_slots.items():
                        for r in raw:
                            if abs(r['x']-ev['x'])<=prox and abs(r['y']-ev['y'])<=prox:
                                active_ids.append(sid)
                                break
                    lifetimer = self.stroke_lifetimers[self.current_tool]
                    stale = lifetimer.update(active_ids)
                    for sid in stale:
                        del slots[sid]
                        removed_strokes.append(sid)

                else:
                    # clustering + object/background
                    dets = []
                    for cnt in result.contours:
                        shape = self.shape_classifier.classify(cnt)
                        M = cv2.moments(cnt)
                        if M['m00'] == 0:
                            continue
                        cx = M['m10']/M['m00']
                        cy = M['m01']/M['m00']
                        area = float(cv2.contourArea(cnt))
                        x, y, w, h = cv2.boundingRect(cnt)
                        dets.append((shape, cx, cy, area, 0.0, float(w), float(h)))
                    self.cluster_tracker.update(dets)

                    valid = self.object_detector.detect()
                    for ev in valid:
                        # background event?
                        if ev['type'] == 'background':
                            # remove previous backgrounds
                            for bid in list(self.backgrounds_by_id):
                                removed_backgrounds.append(bid)
                                del self.backgrounds_by_id[bid]
                            # register new background
                            bid = str(uuid.uuid4())
                            ev['id'] = bid
                            self.backgrounds_by_id[bid] = ev
                            new_backgrounds.append(ev)
                            # reset baseline with this new landscape
                            self.baseline_calc.reset()
                        else:
                            # object event
                            oid = str(uuid.uuid4())
                            ev['id'] = oid
                            self.all_objects[oid] = ev
                            new_objects.append(ev)

                # 7) send WS diffs
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

                # yield
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down.")
        finally:
            # cleanup
            self.kinect.close()
            if not self.config.bypass_ws:
                # collect all remaining ids
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
