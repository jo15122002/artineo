import cv2
import numpy as np
from typing import List, Dict

from config import Config


class BrushStrokeDetector:
    """
    Détection des brush strokes à partir d'une image composite colorée.
    Seul l'événement (tool, x, y, size, color) est renvoyé sous forme de liste de dicts.

    Usage:
        detector = BrushStrokeDetector(brush_image, config)
        strokes = detector.detect(composite_image, current_tool)
    """

    def __init__(self, brush: np.ndarray, config: Config,
                 stroke_area_thresh: float = 100.0):
        # brush: image grayscale float [0,1]
        self.brush = brush.astype(np.float32) / 255.0
        self.tool_channel = {'1': 0, '2': 1, '3': 2}
        self.config = config
        self.brush_scale = config.brush_scale
        self.stroke_area_thresh = stroke_area_thresh
        self.kern = np.ones((3, 3), np.uint8)

        # position du curseur dans la fenêtre dist (en pixels de carte)
        self.mouse_x = 0
        self.mouse_y = 0
        # initialisation de la fenêtre dist en DEBUG
        # cv2.namedWindow('dist', cv2.WINDOW_NORMAL)
        # cv2.setMouseCallback('dist', self._mouse_cb)

    def _mouse_cb(self, event, x, y, flags, param):
        # callback pour capturer la position du curseur
        if event == cv2.EVENT_MOUSEMOVE:
            # dividé par 3 pour obtenir coords sur carte originale
            self.mouse_x = x // 3
            self.mouse_y = y // 3

    def detect(self, composite: np.ndarray, tool: str) -> List[Dict]:
        strokes = []
        # on travaille sur la composite déjà colorée
        if composite.ndim == 3:
            ch = self.tool_channel.get(tool, 0)
            gray = composite[:, :, ch]
        else:
            gray = composite

        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, mask = cv2.threshold(gray, self.config.stroke_intensity_thresh, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kern, iterations=3)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kern, iterations=3)

        raw_dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

        skel = cv2.ximgproc.thinning(mask)

        if self.config.debug_mode:
            for name, img in (("mask", mask), ("skel", skel)):
                big = cv2.resize(img,
                                 (img.shape[1], img.shape[0]),
                                 interpolation=cv2.INTER_NEAREST)
                cv2.imshow(name, big)
            cv2.waitKey(1)

        ys, xs = np.where(skel > 0)
        for y, x in zip(ys, xs):
            # ignore les très petits traits
            if raw_dist[y, x] < self.config.stroke_radius_min or raw_dist[y, x] > self.config.stroke_size_max:
                continue
            radius   = raw_dist[y, x]        # vrai rayon en pixels
            diameter = float(radius * 2.0)   # diamètre local

            strokes.append({
                'tool_id': tool,
                'x':        int(x),
                'y':        int(y),
                'size':     diameter
            })
        
        return strokes
