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
        self.brush_scale = config.brush_scale
        self.stroke_area_thresh = stroke_area_thresh

    def _resize_brush(self, size: float) -> np.ndarray:
        """Redimensionne le brush selon la taille détectée et le facteur brush_scale"""
        s = max(3, min(1000, int(size * self.brush_scale)))
        return cv2.resize(self.brush, (s, s), interpolation=cv2.INTER_AREA)

    def detect(self, composite: np.ndarray, tool: str) -> List[Dict]:
        """
        Extrait les événements de brush strokes depuis l'image composite.

        Args:
            composite: image BGR uint8 (H x W x 3) représentant l'accumulation couleur.
            tool: identifiant de l'outil courant (string).

        Returns:
            List de dicts: {'tool': tool, 'x': int, 'y': int, 'size': float, 'color': [B,G,R]}
        """

        if composite.ndim == 2 or composite.shape[2] == 1:
            composite = cv2.cvtColor(composite, cv2.COLOR_GRAY2BGR)

        strokes_events: List[Dict] = []
        # Passage en niveaux de gris et lissage
        gray = cv2.GaussianBlur(
            cv2.cvtColor(composite, cv2.COLOR_BGR2GRAY), (3, 3), 0
        )
        # Seuil binaire
        _, bin_img = cv2.threshold(gray, 3, 255, cv2.THRESH_BINARY)
        # Ouverture/Fermeture pour nettoyer le masque
        kern = np.ones((3, 3), np.uint8)
        bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, kern, iterations=3)
        bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kern, iterations=3)
        # Transformée de distance
        dist_map = cv2.distanceTransform(bin_img, cv2.DIST_L2, 5)

        # Extraction des contours de régions valides
        contours, _ = cv2.findContours(
            bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for cnt in contours:
            # Filtre par aire minimale
            if cv2.contourArea(cnt) < self.stroke_area_thresh:
                continue
            # Moment pour extraire le centre
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            # Recherche du maximum local sur la distance transform
            mask_region = np.zeros_like(bin_img)
            cv2.drawContours(mask_region, [cnt], -1, 255, cv2.FILLED)
            region = dist_map.copy()
            region[mask_region == 0] = 0
            rm = region.max()
            if rm < 1:
                continue
            # Localisation des pics (dist >= rm - tol)
            dilated = cv2.dilate(dist_map, kern)
            local_max = (dist_map == dilated) & (mask_region == 255) & (dist_map >= rm - 7)
            ys, xs = np.where(local_max)
            for y, x in zip(ys, xs):
                val = dist_map[y, x]
                if val < 1 or val > 150:
                    continue
                # Redimensionnement du brush
                b = self._resize_brush(val)
                bh, bw = b.shape
                # Couleur en fonction de l'outil (BGR)
                color_map = {
                    '1': [0, 0, 255],
                    '2': [255, 0, 0],
                    '3': [0, 255, 0],
                    '4': [0, 0, 0],
                }
                color = color_map.get(tool, [0, 0, 0])
                # Enregistrement de l'événement
                strokes_events.append({
                    'tool': tool,
                    'x': int(x),
                    'y': int(y),
                    'size': float(val),
                    'color': color,
                })
        return strokes_events
