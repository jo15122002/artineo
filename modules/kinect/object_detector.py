# kinect/object_detector.py

import uuid
from typing import Any, Dict, List, Tuple
from cluster_tracker import ClusterTracker

class ObjectDetector:
    """
    À partir des clusters fournis par ClusterTracker, génère
    deux listes :
      - new_events : nouveaux événements détectés (objets ou fonds),
        chacun sous forme de dict {'id','type','shape','cx','cy','w','h','angle','scale'}
      - remove_ids : liste des IDs d'objets/fonds qui ont disparu
    """
    def __init__(
        self,
        cluster_tracker: ClusterTracker,
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

        # État interne pour le tracking
        # clef = object/fond ID, valeur = dernières propriétés
        self._tracked_objects: Dict[str, Dict[str, Any]] = {}

    def detect(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parcourt les clusters validés et compare à l'état précédent pour
        générer :
          - new_events : liste d'événements récents, sous forme de dicts
          - remove_ids  : liste d'IDs disparus
        """
        # 1) Récupère les clusters « confirmés »
        clusters = self._tracker.get_valid_clusters(
            min_confirmations=self._min_points
        )

        # On identifie dynamiquement les templates de fond
        bg_names = {
            name for name in self._template_sizes.keys()
            if name.startswith("landscape_")
        }

        current: Dict[str, Dict[str, Any]] = {}

        # 2) Parcours et filtre
        for cl in clusters:
            avg_w, avg_h = cl.avg_width, cl.avg_height

            # rejet des très gros clusters
            if avg_w * avg_h > self._roi_area * self._max_area_ratio:
                continue

            name = cl.shape
            cx, cy = cl.centroid
            angle = cl.avg_angle

            # échelle relative au template
            w_t, h_t = self._template_sizes.get(name, (avg_w, avg_h))
            scale = (avg_w / w_t + avg_h / h_t) / 2.0

            # ID stable si possible
            cluster_id = getattr(cl, "id", None)
            obj_id = str(cluster_id) if cluster_id is not None else str(uuid.uuid4())

            # type « background » vs « object »
            ev_type = "background" if name in bg_names else "object"

            # construction de l'événement
            ev = {
                "id":    obj_id,
                "type":  ev_type,
                "shape": name,
                "cx":    int(cx),
                "cy":    int(cy),
                "w":     float(avg_w),
                "h":     float(avg_h),
                "angle": float(angle),
                "scale": float(scale),
            }

            current[obj_id] = ev

        # 3) Différence avec l'état précédent
        new_events: List[Dict[str, Any]] = []
        remove_ids: List[str]   = []

        # arrivées
        for oid, ev in current.items():
            if oid not in self._tracked_objects:
                new_events.append(ev)

        # disparitions
        for oid in list(self._tracked_objects.keys()):
            if oid not in current:
                remove_ids.append(oid)

        # 4) MàJ de l'état interne
        self._tracked_objects = current
        
        return new_events, remove_ids
