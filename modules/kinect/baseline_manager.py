# baseline_manager.py

import uuid
import cv2
import numpy as np
from typing import List, Tuple, Optional
from template_manager import TemplateManager

class BaselineManager:
    """
    Gère une baseline (depth map) sur laquelle on 'colle' chaque template (paysage ou objet),
    et détecte automatiquement quand un élément est retiré pour remettre la baseline à jour.
    """

    def __init__(
        self,
        initial_baseline: np.ndarray,
        template_manager: TemplateManager,
        removal_threshold: float = 20.0,
        removal_ratio: float = 0.5
    ):
        """
        :param initial_baseline: depth map (2D np.ndarray) du bac vide + dessin (en uint16 ou float)
        :param template_manager: instance de TemplateManager (pour accéder aux templates_rel)
        :param removal_threshold: seuil en mm ; si depth_current - baseline > threshold, on considère un retrait
        :param removal_ratio: proportion de pixels au-dessus de threshold pour déclencher le retrait
        """
        # baseline est toujours un np.ndarray 2D (uint16 ou float)
        self.baseline: np.ndarray = initial_baseline.copy()
        # TemplateManager nous fournit les templates_rel (hauteurs de carton)
        self.template_manager = template_manager

        # Liste des zones « collées » : chaque entrée est un tuple
        #   (shape_name: str, x0: int, y0: int, width: int, height: int)
        self.placed_zones: List[Tuple[str, str, int, int, int, int]] = []

        # Pour détecter la disparition : si (current_depth - baseline) > removal_threshold
        # sur plus de removal_ratio de la zone, on considère que l’objet a disparu
        self.removal_threshold = removal_threshold
        self.removal_ratio     = removal_ratio

    def detect_and_handle_removals(
        self,
        raw_frame: np.ndarray,
        send_event_fn: Optional[callable] = None
    ):
        """
        Pour chaque zone placée (obj_id, shape, x0, y0, w, h),
        on regarde si la zone a disparu. Si oui, on met à jour
        la baseline et on émet un event contenant l’obj_id.
        """
        to_remove_indices: List[int] = []

        for idx, (obj_id, name, x0, y0, w, h) in enumerate(self.placed_zones):
            x1 = x0 + w
            y1 = y0 + h

            # Clamp
            y0c, y1c = max(0, y0), min(self.baseline.shape[0], y1)
            x0c, x1c = max(0, x0), min(self.baseline.shape[1], x1)
            if y0c >= y1c or x0c >= x1c:
                to_remove_indices.append(idx)
                continue

            patch_depth = raw_frame[y0c:y1c, x0c:x1c].astype(float)
            patch_base  = self.baseline[y0c:y1c, x0c:x1c].astype(float)
            delta = patch_depth - patch_base
            nb_pixels = delta.size
            if nb_pixels == 0:
                to_remove_indices.append(idx)
                continue

            nb_retired = int((delta > self.removal_threshold).sum())
            if (nb_retired / float(nb_pixels)) > self.removal_ratio:
                # 1) maj baseline
                self.baseline[y0c:y1c, x0c:x1c] = raw_frame[y0c:y1c, x0c:x1c]

                # 2) event de suppression AVEC obj_id
                if send_event_fn is not None:
                    removal_event = {
                        "type":  "removal",
                        "id":    obj_id,     # <-- on envoie l’UUID
                        "shape": name,
                        "x":     x0c,
                        "y":     y0c,
                        "w":     x1c - x0c,
                        "h":     y1c - y0c
                    }
                    send_event_fn(removal_event)

                to_remove_indices.append(idx)

        # suppression des zones
        for idx in sorted(to_remove_indices, reverse=True):
            del self.placed_zones[idx]

    def place_zone(
        self,
        obj_id: str,
        name: str,
        cx: float,
        cy: float,
        w: float,
        h: float
    ):
        """
        obj_id  : UUID de l’objet (correspond à ev["id"] dans ObjectDetector)
        name    : nom du template (ex. 'landscape_sea', 'medium_lighthouse', 'small_boat', etc.)
        cx, cy  : coordonnées du centroïde en pixels
        w, h    : largeur et hauteur (pixels) du bounding box
        """
        # 1) calcul du bounding box comme avant :
        x0 = int(cx - w/2)
        y0 = int(cy - h/2)
        x1 = x0 + int(w)
        y1 = y0 + int(h)
        y0c, y1c = max(0, y0), min(self.baseline.shape[0], y1)
        x0c, x1c = max(0, x0), min(self.baseline.shape[1], x1)

        # 2) charger le template_rel
        tmpl_rel = self.template_manager.depth_templates.get(name)
        if tmpl_rel is None:
            return

        # 3) redimensionner + collage comme avant...
        try:
            tmpl_resized = cv2.resize(
                tmpl_rel.astype(float),
                (x1c - x0c, y1c - y0c),
                interpolation=cv2.INTER_AREA
            )
        except Exception:
            return

        patch_base = self.baseline[y0c:y1c, x0c:x1c].astype(float)
        new_patch = (patch_base - tmpl_resized)
        self.baseline[y0c:y1c, x0c:x1c] = new_patch.astype(self.baseline.dtype)

        # 4) mémoriser la zone collée AVEC l’obj_id
        self.placed_zones.append((obj_id, name, x0c, y0c, x1c - x0c, y1c - y0c))

    def get_baseline(self) -> np.ndarray:
        """
        Pour récupérer la baseline actuelle (par exemple pour la passer à Channel4Detector).
        """
        return self.baseline
