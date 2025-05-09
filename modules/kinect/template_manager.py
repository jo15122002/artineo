import logging
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Charge et gère les templates d'images (formes et fonds).
    Extrait et stocke contours, tailles, profils d'arrière-plan et overlays (sprites) prêts à l'emploi.
    """

    def __init__(
        self,
        template_dir: str,
        n_profile: int = 100,
        area_threshold: float = 2000.0,
        small_area_threshold: float = 250.0
    ) -> None:
        self.template_dir = Path(template_dir)
        self.n_profile = n_profile
        self.area_threshold = area_threshold
        self.small_area_threshold = small_area_threshold

        # Données extraites
        self.template_contours: Dict[str, np.ndarray] = {}
        self.template_sizes: Dict[str, Tuple[int, int]] = {}
        self.background_profiles: Dict[str, List[float]] = {}
        self.overlays: Dict[str, np.ndarray] = {}

        # Regroupements par type
        self.forme_templates: Dict[str, np.ndarray] = {}
        self.fond_templates: Dict[str, np.ndarray] = {}
        self.small_templates: Dict[str, np.ndarray] = {}

        self._load_all_templates()
        self._classify_templates()

    def _load_all_templates(self) -> None:
        """
        Parcourt le répertoire de templates, calcule contours et tailles.
        Pré-calcule profils de fond et construit les overlays.
        """
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        for filepath in self.template_dir.glob("*.png"):
            name = filepath.stem
            img = cv2.imread(str(filepath), cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.warning("Impossible de charger le template %s", filepath)
                continue

            # Extraire le plus grand contour
            gray = (
                cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2GRAY)
                if img.shape[2] >= 3
                else img[..., 0]
            )
            _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
            cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                logger.warning("Aucun contour trouvé pour %s", name)
                continue
            cnt = max(cnts, key=cv2.contourArea)
            self.template_contours[name] = cnt

            x, y, w, h = cv2.boundingRect(cnt)
            self.template_sizes[name] = (w, h)

            # Construire overlay (sprite RGBA)
            sprite = self._extract_sprite(img, cnt, x, y, w, h)
            self.overlays[name] = sprite

            # Pour les profils de fond (contours larges)
            if self._is_background(name):
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.drawContours(mask, [cnt - [x, y]], -1, 255, cv2.FILLED)
                profile = self._compute_profile(mask)
                self.background_profiles[name] = profile

        logger.info("%d templates chargés", len(self.template_contours))

    def _classify_templates(self) -> None:
        """
        Remplit les dictionnaires forme_templates, fond_templates et small_templates.
        """
        for name, cnt in self.template_contours.items():
            area = cv2.contourArea(cnt)
            if name.startswith("Fond_") or area >= self.area_threshold:
                self.fond_templates[name] = cnt
            elif name.startswith("Small_") or area <= self.small_area_threshold:
                self.small_templates[name] = cnt
            else:
                self.forme_templates[name] = cnt

        logger.debug(
            "Forme: %d, Fond: %d, Small: %d",
            len(self.forme_templates), len(self.fond_templates), len(self.small_templates),
        )

    def _is_background(self, name: str) -> bool:
        return name in self.fond_templates or name.startswith("Fond_")

    def _extract_sprite(
        self,
        img: np.ndarray,
        contour: np.ndarray,
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> np.ndarray:
        """
        Découpe et ferme les trous d'alpha pour obtenir un overlay RGBA.
        """
        # Extraire roi autour du contour
        roi = img[y : y + h, x : x + w].copy()
        if roi.shape[2] == 4:
            alpha = roi[..., 3]
        else:
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, alpha = cv2.threshold(gray_roi, 254, 255, cv2.THRESH_BINARY_INV)
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2BGRA)

        # Fermer les petits trous
        kernel = np.ones((3, 3), np.uint8)
        alpha_closed = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel, iterations=2)
        roi[..., 3] = alpha_closed
        return roi

    def _compute_profile(self, mask: np.ndarray) -> List[float]:
        """
        Calcule le profil vertical du mask sur n_profile points.
        Renvoie une liste de floats normalisés.
        """
        h, w = mask.shape
        xs = np.linspace(0, w - 1, self.n_profile, dtype=int)
        prof = np.zeros(self.n_profile, dtype=float)
        for i, x in enumerate(xs):
            ys = np.where(mask[:, x] > 0)[0]
            prof[i] = float(ys.min()) / h if ys.size else 0.0
        return prof.tolist()

    def get_contours(self) -> Dict[str, np.ndarray]:
        return self.template_contours

    def get_sizes(self) -> Dict[str, Tuple[int, int]]:
        return self.template_sizes

    def get_profiles(self) -> Dict[str, List[float]]:
        return self.background_profiles

    def get_overlays(self) -> Dict[str, np.ndarray]:
        return self.overlays

    def list_template_names(self) -> List[str]:
        return list(self.template_contours.keys())

    def reload(self) -> None:
        """
        Recharge et recalcule tous les templates.
        """
        self.template_contours.clear()
        self.template_sizes.clear()
        self.background_profiles.clear()
        self.overlays.clear()
        self.forme_templates.clear()
        self.fond_templates.clear()
        self.small_templates.clear()
        self._load_all_templates()
        self._classify_templates()
