import cv2
import numpy as np
from dataclasses import dataclass
from typing import List

from config import Config


@dataclass(frozen=True)
class DepthResult:
    """
    Container for the result of depth processing.
    """
    mapped: np.ndarray            # 8-bit depth-to-color mapped image
    contours: List[np.ndarray]    # contours of detected objects


class DepthProcessor:
    """
    Processes depth frames against a baseline to produce a normalized depth map
    and extract object contours.
    """

    def __init__(self, config: Config, mask_threshold: int = 80, morph_kernel: int = 3):
        """
        Args:
            config: Config object with mapping scale.
            mask_threshold: intensity threshold for binary mask (0-255).
            morph_kernel: size of square kernel for morphological filtering.
        """
        self._scale = config.scale
        self._mask_threshold = mask_threshold
        # kernel for opening/closing
        self._kernel = np.ones((morph_kernel, morph_kernel), dtype=np.uint8)

    def process(self, frame: np.ndarray, baseline: np.ndarray) -> DepthResult:
        """
        Compute a mapped depth image and detect objects by contour extraction.

        Args:
            frame: current median-averaged depth frame (uint16 array).
            baseline: baseline depth frame (uint16 array).

        Returns:
            DepthResult with:
              - mapped: uint8 image where 128 is baseline and differences scaled
              - contours: list of contours found in the binary mask
        """
        # compute signed difference and map to 0-255
        diff = frame.astype(int) - baseline.astype(int)
        mapped = np.clip(128 + diff * self._scale, 0, 255).astype(np.uint8)
        
        # min_val, max_val, _, _ = cv2.minMaxLoc(mapped)
        # print(f"[DEBUG DepthProc4] mapped_blur   min={min_val:.1f}, max={max_val:.1f}")

        # binary mask: objects appear darker than background
        _, mask = cv2.threshold(mapped, self._mask_threshold, 255, cv2.THRESH_BINARY_INV)
        # clean up noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)
        
        cv2.imshow("Depth Mask", mask)
        cv2.waitKey(1)

        # find external contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return DepthResult(mapped=mapped, contours=contours)

# Example usage:
# from config import Config
# raw_conf = client.fetch_config()\# config = Config(**raw_conf)
# depth_processor = DepthProcessor(config)
# result = depth_processor.process(current_frame, baseline_frame)
# img = result.mapped; contours = result.contours
