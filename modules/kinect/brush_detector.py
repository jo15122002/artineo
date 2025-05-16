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
        self.config = config
        self.brush_scale = config.brush_scale
        self.stroke_area_thresh = stroke_area_thresh
        self.kern = np.ones((3, 3), np.uint8)

        # position du curseur dans la fenêtre dist (en pixels de carte)
        self.mouse_x = 0
        self.mouse_y = 0
        # initialisation de la fenêtre dist en DEBUG
        cv2.namedWindow('dist', cv2.WINDOW_NORMAL)
        cv2.setMouseCallback('dist', self._mouse_cb)

    def _mouse_cb(self, event, x, y, flags, param):
        # callback pour capturer la position du curseur
        if event == cv2.EVENT_MOUSEMOVE:
            # dividé par 3 pour obtenir coords sur carte originale
            self.mouse_x = x // 3
            self.mouse_y = y // 3

    def _resize_brush(self, size: float) -> np.ndarray:
        """Redimensionne le brush selon la taille détectée et le facteur brush_scale"""
        s = max(3, min(1000, int(size * self.brush_scale)))
        return cv2.resize(self.brush, (s, s), interpolation=cv2.INTER_AREA)

    def detect(self, composite: np.ndarray, tool: str) -> List[Dict]:
        strokes = []
        # on travaille sur la composite déjà colorée
        gray = (
            cv2.cvtColor(composite, cv2.COLOR_BGR2GRAY)
            if composite.ndim == 3 else composite
        )

        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kern, iterations=3)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kern, iterations=3)

        raw_dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        dist_map = cv2.normalize(raw_dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        disp_big = cv2.resize(dist_map, (dist_map.shape[1]*3, dist_map.shape[0]*3),
                      interpolation=cv2.INTER_NEAREST)

        h, w = dist_map.shape
        if 0 <= self.mouse_x < w and 0 <= self.mouse_y < h:
            dist_val = dist_map[self.mouse_y, self.mouse_x]
            text = f"Dist: {dist_val:.2f}@({self.mouse_x},{self.mouse_y})"
            cv2.putText(disp_big, text, (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
        cv2.resizeWindow('dist', dist_map.shape[1] * 3, dist_map.shape[0] * 3)
        cv2.imshow('mask', mask)
        cv2.imshow('dist', disp_big)

        tol = self.config.stroke_radius_tol

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            if cv2.contourArea(cnt) < self.stroke_area_thresh:
                continue

            # Masque du contour
            region = np.zeros(mask.shape, dtype=np.uint8)
            cv2.drawContours(region, [cnt], -1, 255, cv2.FILLED)

            # Distance map restreinte au contour
            local = dist_map.copy()
            local[region==0]=0

            level = int(local.max())

            dil = cv2.dilate(dist_map, self.kern)

            peaks = (
                (dist_map == dil) &
                (region == 255) &
                (dist_map.astype(int) >= int(level - tol))
            )

            ys, xs = np.where(peaks)
            for y, x in zip(ys, xs):
                radius = float(raw_dist[y, x])
                diameter = radius * 2.0
                strokes.append({
                    'tool_id': tool,
                    'x': int(x),
                    'y': int(y),
                    'size': diameter
                })

            # if rm < 1: continue
            # dil = cv2.dilate(dist_map, self.kern)
            # peaks = np.logical_and(dist_map==dil, dist_map>=rm-7)
            # ys, xs = np.where(peaks)
            # for y, x in zip(ys, xs):
            #     x_py = int(x)
            #     y_py = int(y)
            #     v    = int(dist_map[y, x])
            #     if not (1 <= v <= 150):
            #         continue
            #     strokes.append({
            #         'tool_id': tool,   # au lieu de color
            #         'x': x_py,
            #         'y': y_py,
            #         'size': v
            #     })
        return strokes
