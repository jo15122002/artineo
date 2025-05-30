# kinect/object_detector.py

import uuid
from typing import Any, Dict, List, Tuple


class ObjectDetector:
    """
    À partir des clusters fournis par ClusterTracker, génère
    deux listes :
      - new_objects : nouveaux objets détectés, chacun sous forme de dict
        {'id', 'shape', 'cx', 'cy', 'w', 'h', 'angle', 'scale'}
      - remove_objects : liste des IDs d'objets qui ont disparu

    Filtre les clusters trop petits (nombre de points < min_points)
    ou trop grands (surface > max_area_ratio * ROI area),
    et maintient un état interne pour suivre les objets entre les appels.
    """

    def __init__(
        self,
        cluster_tracker: Any,
        template_sizes: Dict[str, Tuple[int, int]],
        roi_width: int,
        roi_height: int,
        min_points: int = 10,
        max_area_ratio: float = 0.5,
    ) -> None:
        self._tracker = cluster_tracker
        self._template_sizes = template_sizes
        self._roi_area = roi_width * roi_height
        self._min_points = min_points
        self._max_area_ratio = max_area_ratio

        # État interne pour le tracking des objets
        # clef = object ID, valeur = dernières propriétés de l'objet
        self._tracked_objects: Dict[str, Dict[str, Any]] = {}

    def detect(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parcourt les clusters validés et compare à l'état précédent pour
        générer :
          - new_objects : liste d'objets fraîchement arrivés
          - remove_objects : liste d'IDs d'objets disparus
        """
        # Récupère les clusters "confirmés" par ClusterTracker
        clusters = self._tracker.get_valid_clusters(
            min_confirmations=self._min_points
        )

        current_objects: Dict[str, Dict[str, Any]] = {}

        for cl in clusters:
            avg_w = cl.avg_width
            avg_h = cl.avg_height

            # filtre par surface
            if (avg_w * avg_h) > (self._roi_area * self._max_area_ratio):
                continue

            name = cl.shape
            cx, cy = cl.centroid
            angle = cl.avg_angle

            # calcul de l'échelle relative au template
            w_t, h_t = self._template_sizes[name]
            scale = (avg_w / w_t + avg_h / h_t) / 2.0

            # génère un ID stable si possible, sinon un nouveau UUID
            # on suppose que ClusterTracker expose un identifiant unique `cl.id`
            cluster_id = getattr(cl, "id", None)
            if cluster_id is not None:
                obj_id = str(cluster_id)
            else:
                obj_id = str(uuid.uuid4())

            obj = {
                "id": obj_id,
                "shape": name,
                "cx": int(cx),
                "cy": int(cy),
                "w": float(avg_w),
                "h": float(avg_h),
                "angle": float(angle),
                "scale": float(scale),
            }

            current_objects[obj_id] = obj

        # Détecte les arrivées et disparitions
        new_objects: List[Dict[str, Any]] = []
        remove_objects: List[str] = []

        # nouveaux IDs
        for oid, props in current_objects.items():
            if oid not in self._tracked_objects:
                new_objects.append(props)

        # IDs disparus
        for oid in list(self._tracked_objects.keys()):
            if oid not in current_objects:
                remove_objects.append(oid)

        # met à jour l'état interne
        self._tracked_objects = current_objects

        return new_objects, remove_objects
