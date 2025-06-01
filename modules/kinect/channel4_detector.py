import cv2
import numpy as np
from typing import List, Dict
from depth_processor import DepthProcessor
from shape_classifier import ShapeClassifier
from cluster_tracker import ClusterTracker
from object_detector import ObjectDetector

class Channel4Detector:
    def __init__(
        self,
        depth_processor: DepthProcessor,
        shape_classifier: ShapeClassifier,
        cluster_tracker: ClusterTracker,
        object_detector: ObjectDetector,
        small_area_threshold: float,
        display: bool = True
    ):
        """
        :param depth_processor: instance de DepthProcessor pour extraire mapped + contours
        :param shape_classifier: instance de ShapeClassifier (modifié pour prendre baseline)
        :param cluster_tracker: instance de ClusterTracker
        :param object_detector: instance d’ObjectDetector
        :param small_area_threshold: aire min d’un contour pour tenter classification
        :param display: si True, on ouvre des fenêtres OpenCV pour visualiser le processus
        """
        self.depth_processor      = depth_processor
        self.shape_classifier     = shape_classifier
        self.cluster_tracker      = cluster_tracker
        self.object_detector      = object_detector
        self.small_area_threshold = small_area_threshold
        self.display              = display

        # Si on veut, on peut définir des couleurs pour chaque type de template
        # Exemple : landscapes en bleu, mediums en vert, small en jaune
        self.color_landscape = (255, 200, 0)  # BGR
        self.color_medium    = (0, 255, 0)
        self.color_small     = (0, 200, 255)

        # Noms des templates pour savoir quel type de couleur utiliser
        # (on suppose que les noms commencent par "landscape_", "medium_" ou "small_")
        # Sinon, adaptez la logique pour vos propres noms.
        self.prefix_landscape = "landscape_"
        self.prefix_medium    = "medium_"
        self.prefix_small     = "small_"

    def detect(
        self,
        raw_frame: np.ndarray,
        baseline_for_bg: np.ndarray
    ) -> tuple[List[Dict], List[Dict], List[np.ndarray]]:
        """
        1) Traite 'raw_frame' (depth brute) avec DepthProcessor → mapped + contours
        2) Pour chaque contour > small_area_threshold, on appelle classify_3d(cnt, raw_frame, baseline_for_bg)
        3) On collecte dets_brut = [(shape, cx, cy, area, 0.0, w, h), …]
        4) On update le ClusterTracker, puis appel à ObjectDetector.detect()
        5) Si display=True, on affiche en direct :
           - La depth map 8 bits (mapped) avec contours et annotations
           - Pour chaque contour classifié : patch_rel et tmpl_resized correspondants
        """

        # 1) Soustraction baseline + affichage / extraction de contours
        result   = self.depth_processor.process(raw_frame, baseline_for_bg)
        mapped   = result.mapped       # image 8 bits (0..255) pour debug/affichage
        cnts_raw = result.contours     # contours filtrés après clean

        dets_brut: List[tuple] = []

        # Copie de mapped pour dessiner les contours en superposition
        if self.display:
            display_img = cv2.cvtColor(mapped, cv2.COLOR_GRAY2BGR)  # passer en BGR pour couleur
        else:
            display_img = None

        # 2) Pour chaque contour, classification 3D
        for cnt in cnts_raw:
            area = float(cv2.contourArea(cnt))
            print()
            if area < self.small_area_threshold:
                continue

            # Classifier en comparant delta = baseline_for_bg - raw_frame
            shape = self.shape_classifier.classify_3d(
                cnt,
                raw_frame,
                baseline_for_bg
            )
            if shape is None:
                # Si aucun template ne matche, on peut dessiner le contour en rouge (optionnel)
                if self.display:
                    cv2.drawContours(display_img, [cnt], -1, (0, 0, 255), 2)
                continue

            # Calculer centroïde
            M = cv2.moments(cnt)
            if M.get("m00", 0) == 0:
                continue
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
            x, y, w, h = cv2.boundingRect(cnt)

            dets_brut.append((shape, cx, cy, area, 0.0, float(w), float(h)))

            # Si display activé, dessiner le contour et annoter le nom du template
            if self.display:
                # Choisir la couleur selon le préfixe du nom
                if shape.startswith(self.prefix_landscape):
                    color = self.color_landscape
                elif shape.startswith(self.prefix_medium):
                    color = self.color_medium
                elif shape.startswith(self.prefix_small):
                    color = self.color_small
                else:
                    color = (255, 255, 255)

                # Dessiner le contour en surimpression
                cv2.drawContours(display_img, [cnt], -1, color, 2)
                # Dessiner un rectangle autour
                cv2.rectangle(display_img, (x, y), (x + w, y + h), color, 1)
                # Annoter le nom du template et le score (si vous l’avez retourné)
                # Ici on n’a pas retourné le score, mais on peut afficher shape uniquement
                cv2.putText(
                    display_img,
                    shape,
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                    cv2.LINE_AA
                )

                # → A titre de debug avancé, on peut aussi afficher patch_rel et tmpl_resized :
                #    Récupérer patch_rel et tmpl_resized en dupliquant la logique de ShapeClassifier (ou faire remonter ces arrays).
                #    Mais pour rester simple, on se contente ici d’afficher le contour sur mapped.

        # 3) Mettre à jour le tracker de clusters
        self.cluster_tracker.update(dets_brut)

        # 4) Détection des events (background vs objet) via ObjectDetector
        events_all, removed_ids_all = self.object_detector.detect()

        # 5) Séparer en deux listes
        candidate_backgrounds = [ev for ev in events_all if ev["type"] == "background"]
        candidate_objects     = [ev for ev in events_all if ev["type"] != "background"]

        # 6) Afficher le résultat global si display=True
        if self.display:
            # Fenêtre principale « Vue 3D » ou « Vue Depth + contours »
            cv2.imshow("Channel4 View", display_img)

            # Attendre 1 ms pour la rafraîchir (ou 10 ms si trop rapide)
            cv2.waitKey(1)

        return candidate_backgrounds, candidate_objects, cnts_raw
