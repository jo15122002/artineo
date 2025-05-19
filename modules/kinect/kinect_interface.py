import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2
from config import Config
import logging


class KinectInterface:
    """
    Interface to the Kinect sensor for depth frame acquisition.

    Responsibilities:
    - Initialize and close the Kinect runtime.
    - Fetch raw depth frames and apply preprocessing (median blur).
    - Crop to configured ROI and flip horizontally.
    """

    def __init__(self, config: Config, blur_ksize: int = 5, logger=None):
        self.config = config
        self.blur_ksize = blur_ksize
        self._kinect = None
        self.logger = logger or logging.getLogger(__name__)

    def open(self) -> None:
        """
        Initialize the Kinect runtime for depth frames.
        Raises an exception on failure.
        """
        try:
            self._kinect = PyKinectRuntime.PyKinectRuntime(
                PyKinectV2.FrameSourceTypes_Depth
            )
            self.logger.info("Kinect sensor initialized.")
        except Exception as e:
            self.logger.error("Failed to initialize Kinect: %s", e)
            raise

    def close(self) -> None:
        """
        Safely close the Kinect runtime and release resources.
        """
        if self._kinect is not None:
            try:
                self._kinect.close()
                self.logger.info("Kinect sensor closed.")
            except Exception as e:
                self.logger.warning("Error closing Kinect: %s", e)
            finally:
                self._kinect = None

    def _get_raw_depth(self) -> np.ndarray:
        """
        Retrieve the latest raw depth frame from the sensor.
        Raises if no new frame is available.
        """
        if not self._kinect:
            raise RuntimeError("No Kinect connected.")
        if not self._kinect.has_new_depth_frame():
            raise RuntimeError("No new depth frame available.")
        frame = self._kinect.get_last_depth_frame()
        # Kinect depth frames come as a flat array of uint16
        depth = frame.reshape((424, 512))
        return depth

    def has_new_depth_frame(self) -> bool:
        """
        Check if a new depth frame is available.
        Returns:
            bool: True if a new depth frame is available, False otherwise.
        """
        return self._kinect.has_new_depth_frame()

    def get_depth_frame(self) -> np.ndarray:
        """
        Get a preprocessed depth frame:
        - median blur
        - crop to ROI
        - horizontal flip

        Returns:
            np.ndarray of shape (roi_height, roi_width) with dtype uint16
        """
        raw = self._get_raw_depth().astype(np.uint16)
        blurred = cv2.medianBlur(raw, self.blur_ksize)

        # Crop to ROI
        y0, x0 = self.config.roi_y0, self.config.roi_x0
        h, w = self.config.roi_height, self.config.roi_width
        cropped = blurred[y0 : y0 + h, x0 : x0 + w]

        # Flip horizontally for mirror view
        flipped = cv2.flip(cropped, 1)
        return flipped
