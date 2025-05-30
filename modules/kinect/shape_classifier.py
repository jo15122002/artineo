import logging
from typing import Dict, Any, List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ShapeClassifier:
    """
    Classifier for contours based on shape templates and background profiles.
    Inject all templates and parameters via constructor for testability.
    """

    def __init__(
        self,
        small_templates: Dict[str, np.ndarray],
        shape_templates: Dict[str, np.ndarray],
        background_profiles: Dict[str, List[float]],
        use_matchshapes: bool = True,
        small_area_threshold: float = 250.0,
        area_threshold: float = 2000.0,
    ) -> None:
        self.small_templates = small_templates
        self.shape_templates = shape_templates
        self.background_profiles = background_profiles
        self.use_matchshapes = use_matchshapes
        self.small_area_threshold = small_area_threshold
        self.area_threshold = area_threshold

    def _compute_profile(self, mask: np.ndarray) -> np.ndarray:
        """
        Compute vertical profile of a binary mask.
        Returns a 1D numpy array of floats.
        """
        h, w = mask.shape
        # evenly sample columns across width
        # length of profile == length of any background_profiles entry
        prof_len = len(next(iter(self.background_profiles.values())))
        xs = np.linspace(0, w - 1, num=prof_len, dtype=int)
        prof = np.zeros(prof_len, dtype=float)
        for i, x in enumerate(xs):
            ys = np.where(mask[:, x] > 0)[0]
            prof[i] = float(ys.min()) / h if ys.size else 0.0
        return prof

    def _classify_background_by_profile(self, cnt: np.ndarray) -> str:
        """
        Classify a contour by comparing its vertical profile to background templates.
        Returns the best matching template name.
        """
        x, y, w_d, h_d = cv2.boundingRect(cnt)
        mask = np.zeros((h_d, w_d), dtype=np.uint8)
        cnt_shifted = cnt - [x, y]  # translate contour into mask coords
        cv2.drawContours(mask, [cnt_shifted], -1, 255, cv2.FILLED)
        prof = self._compute_profile(mask)

        best_name = None
        best_dist = float('inf')
        for name, tprof in self.background_profiles.items():
            dist = np.linalg.norm(prof - np.array(tprof, dtype=float))
            if dist < best_dist:
                best_dist = dist
                best_name = name

        logger.debug("Background classified: %s (dist=%.3f)", best_name, best_dist)
        return best_name  # type: ignore

    def _classify_contour(self, cnt: np.ndarray) -> str:
        """
        Classify a contour among small and shape templates using matchShapes or Hu moments.
        Returns the best matching template name.
        """
        area = cv2.contourArea(cnt)
        # select template pool
        if area < self.small_area_threshold:
            candidates = self.small_templates
        elif area < self.area_threshold:
            candidates = self.shape_templates
        else:
            # too large → treat as background form
            return self._classify_background_by_profile(cnt)

        best_score = float('inf')
        best_name = None

        if self.use_matchshapes:
            # use cv2.matchShapes on contour geometry
            for name, template_cnt in candidates.items():
                score = cv2.matchShapes(cnt, template_cnt, cv2.CONTOURS_MATCH_I1, 0.0)
                if score < best_score:
                    best_score = score
                    best_name = name
        else:
            # fallback: compare Hu moments
            hu1 = cv2.HuMoments(cv2.moments(cnt)).flatten()
            for name, template_cnt in candidates.items():
                hu2 = cv2.HuMoments(cv2.moments(template_cnt)).flatten()
                score = float(np.linalg.norm(hu1 - hu2))
                if score < best_score:
                    best_score = score
                    best_name = name

        logger.debug("Contour classified: %s (score=%.3f)", best_name, best_score)
        return best_name  # type: ignore

    def classify(self, cnt: np.ndarray) -> str:
        """
        Public API: classify a single contour and return its template name.
        """
        return self._classify_contour(cnt)
