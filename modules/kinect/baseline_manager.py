# baseline_manager.py

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
        self.placed_zones: List[Tuple[str,int,int,int,int]] = []

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
        Parcourt self.placed_zones, détecte si un élément a été retiré, et met à jour la baseline.
        Si send_event_fn est fourni, on appelle send_event_fn(removal_event_dict) pour chaque zone retirée.
        """
        to_remove_indices: List[int] = []

        for idx, (name, x0, y0, w, h) in enumerate(self.placed_zones):
            x1 = x0 + w
            y1 = y0 + h

            # S’assurer de ne pas sortir des bords
            y0c, y1c = max(0, y0), min(self.baseline.shape[0], y1)
            x0c, x1c = max(0, x0), min(self.baseline.shape[1], x1)
            if y0c >= y1c or x0c >= x1c:
                # Zone invalide (à l’extérieur), on marque à supprimer
                to_remove_indices.append(idx)
                continue

            patch_depth = raw_frame[y0c:y1c, x0c:x1c].astype(float)
            patch_base  = self.baseline[y0c:y1c, x0c:x1c].astype(float)

            # Si l’objet est toujours là, patch_base - patch_depth >= petit nombre (hauteur ≥ 0).
            # Si l’objet a été retiré, patch_depth - patch_base sera (> 0) en majorité.
            delta = patch_depth - patch_base
            nb_pixels = delta.size
            if nb_pixels == 0:
                to_remove_indices.append(idx)
                continue

            # Nombre de pixels où (delta > removal_threshold)
            nb_retired = int((delta > self.removal_threshold).sum())

            # Si la proportion de tels pixels dépasse removal_ratio, on considère retrait
            if (nb_retired / float(nb_pixels)) > self.removal_ratio:
                # 1) Mettre à jour la baseline : remplacer la zone par la profondeur actuelle
                self.baseline[y0c:y1c, x0c:x1c] = raw_frame[y0c:y1c, x0c:x1c]

                # 2) Préparer l’event de suppression
                if send_event_fn is not None:
                    removal_event = {
                        "type":    "removal",
                        "shape":   name,
                        "x":       x0c,
                        "y":       y0c,
                        "w":       x1c - x0c,
                        "h":       y1c - y0c
                    }
                    send_event_fn(removal_event)

                # 3) Enregistrer l’indice à supprimer plus tard
                to_remove_indices.append(idx)

        # On supprime de placed_zones par indices du plus grand au plus petit
        for idx in sorted(to_remove_indices, reverse=True):
            del self.placed_zones[idx]

    def place_zone(
        self,
        name: str,
        cx: float,
        cy: float,
        w: float,
        h: float
    ):
        """
        « Colle » immédiatement le template_rel (hauteur du carton) correspondant à `name`
        dans self.baseline, centré en (cx, cy) avec largeur w, hauteur h. Puis mémorise la zone.

        :param name: nom du template (clé dans template_manager.depth_templates)
        :param cx: coordonnée x du centroïde (en pixels) retournée par le détecteur
        :param cy: coordonnée y du centroïde
        :param w: largeur (en pixels) du bounding box
        :param h: hauteur (en pixels)
        """
        # Calculer la bounding box (x0,y0) en haut à gauche
        x0 = int(cx - w/2)
        y0 = int(cy - h/2)
        x1 = x0 + int(w)
        y1 = y0 + int(h)

        # Clamp sur les bords de l’image
        y0c, y1c = max(0, y0), min(self.baseline.shape[0], y1)
        x0c, x1c = max(0, x0), min(self.baseline.shape[1], x1)

        # Charger le template_rel 2D (hauteur du carton)
        tmpl_rel = self.template_manager.depth_templates.get(name, None)
        if tmpl_rel is None:
            # Template inconnu → on ne fait rien
            return

        # Redimensionner le template_rel à la taille du bounding box
        try:
            tmpl_resized = cv2.resize(
                tmpl_rel.astype(float),
                (x1c - x0c, y1c - y0c),
                interpolation=cv2.INTER_AREA
            )
        except Exception:
            # En cas d’erreur de resize (dimensions nulles ou autres), on abandonne
            return

        # Extraire la portion courante de la baseline
        patch_base = self.baseline[y0c:y1c, x0c:x1c].astype(float)

        # Coller le template : nouvelle profondeur = ancienne_base - hauteur_carton
        new_patch = (patch_base - tmpl_resized)

        # Mettre à jour la baseline (on caste en dtype d’origine, généralement uint16)
        self.baseline[y0c:y1c, x0c:x1c] = new_patch.astype(self.baseline.dtype)

        # Mémoriser la zone collée (on stocke x0c,y0c, largeur, hauteur)
        self.placed_zones.append((name, x0c, y0c, x1c - x0c, y1c - y0c))

    def get_baseline(self) -> np.ndarray:
        """
        Pour récupérer la baseline actuelle (par exemple pour la passer à Channel4Detector).
        """
        return self.baseline
