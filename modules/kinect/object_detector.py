from typing import Any, Dict, List, Tuple


class ObjectDetector:
    """
    À partir des clusters fournis par ClusterTracker, génère les événements d'objets
    sous forme de dictionnaires {shape, cx, cy, w, h, angle, scale}.

    - Filtre les clusters trop petits (nombre de points < min_points)
      ou trop grands (surface > max_area_ratio * ROI area).
    - Calcule l'échelle moyenne par rapport à la taille du template.
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

    def detect(self) -> List[Dict[str, Any]]:
        """
        Parcourt les clusters validés et renvoie la liste des objets détectés.
        """
        events: List[Dict[str, Any]] = []
        # get_valid_clusters() renvoie des instances de Cluster
        clusters = self._tracker.get_valid_clusters(min_confirmations=self._min_points)

        for cl in clusters:
            # Filtre par surface moyenne
            avg_w = cl.avg_width
            avg_h = cl.avg_height
            if (avg_w * avg_h) > (self._roi_area * self._max_area_ratio):
                continue

            name = cl.shape
            cx, cy = cl.centroid
            angle = cl.avg_angle

            print(name)

            # Taille du template de référence
            w_t, h_t = self._template_sizes[name]
            scale_w = avg_w / w_t
            scale_h = avg_h / h_t
            scale = (scale_w + scale_h) / 2.0

            events.append({
                'shape': name,
                'cx': int(cx),
                'cy': int(cy),
                'w': float(avg_w),
                'h': float(avg_h),
                'angle': float(angle),
                'scale': float(scale)
            })

        return events
