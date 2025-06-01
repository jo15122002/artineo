import cv2
import numpy as np
from typing import Optional, Dict

class ShapeClassifier:
    """
    Classification 3D pour tous les templates (paysages, objets moyens, petit objet),
    en comparant la carte de hauteur (baseline – depth_frame) à des templates_rel (hauteur).
    """

    def __init__(
        self,
        depth_templates: Dict[str, np.ndarray],
        small_area_threshold: float = 1000.0,
        match_threshold: float = 100.0
    ):
        """
        :param depth_templates: dict mapping nom_template -> np.ndarray 2D float32 (hauteur du carton)
        :param small_area_threshold: aire minimale (en px) d'un contour pour tenter la classification.
        :param match_threshold: seuil maximal de MSE (hauteur²) pour accepter la correspondance.
        """
        self.depth_templates = depth_templates
        self.small_area_threshold = small_area_threshold
        self.match_threshold = match_threshold

    def classify_3d(
        self,
        cnt: np.ndarray,
        depth_frame: np.ndarray,
        baseline_for_bg: np.ndarray
    ) -> Optional[str]:
        """
        Pour un contour 'cnt' sur 'depth_frame', calcule la carte de hauteur réelle
        = (baseline_for_bg - depth_frame) dans la bounding box, puis compare à tous
        les 'depth_templates' (template_rel) en MSE 2D. Retourne le nom du template
        (landscape_*, medium_*, small_*) si MSE_min < match_threshold, ou None.

        :param cnt: contour 2D (ndarray (N_points,1,2)) issu de findContours
        :param depth_frame: depth frame brute (2D, uint16 ou float) de la Kinect
        :param baseline_for_bg: depth frame (2D) correspondant à la baseline (dessin + paysage),
                                utilisée pour calculer la profondeur relative.
        :return: nom du template détecté, ou None
        """
        # 1) Aire minimale (filtres parasites)
        area = float(cv2.contourArea(cnt))
        if area < self.small_area_threshold:
            return None

        # 2) Bounding box (x, y, w, h) autour du contour
        x, y, w, h = cv2.boundingRect(cnt)
        patch_depth = depth_frame[y : y + h, x : x + w].astype(float)
        if patch_depth.size == 0:
            return None

        # 3) Créer un masque binaire du contour dans la petite image (h, w)
        mask = np.zeros((h, w), dtype=np.uint8)
        cnt_shift = cnt - np.array([[x, y]])  # décalage pour centrer le contour
        cv2.drawContours(mask, [cnt_shift], -1, 255, thickness=-1)

        # 4) Calculer la carte de hauteur réelle = (baseline – depth_frame) sous le masque
        baseline_patch = baseline_for_bg[y : y + h, x : x + w].astype(float)
        patch_rel = np.where(mask, baseline_patch - patch_depth, np.nan)

        # 5) Comparer patch_rel à chaque template_rel (depth_templates[name])
        best_name = None
        best_score = float("inf")

        for name, tmpl_rel in self.depth_templates.items():
            # tmpl_rel est une np.ndarray 2D float32 (hauteur du carton)
            try:
                tmpl_resized = cv2.resize(
                    tmpl_rel.astype(float),
                    (w, h),
                    interpolation=cv2.INTER_AREA
                )
            except Exception:
                continue

            # Calcul du MSE uniquement là où mask=255 (les nan ignorent hors contour)
            diff = patch_rel - tmpl_resized
            mse = float(np.nanmean(diff**2))
            if mse < best_score:
                best_score = mse
                best_name = name

        print(f"Best match: {best_name} with MSE {best_score:.2f}")

        # 6) Si le MSE minimal est en dessous du seuil, on retourne le nom du template
        if best_score < self.match_threshold:
            return best_name
        else:
            return None
