import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ClusterPoint:
    """Représente un point de détection unique dans un cluster."""
    shape: str
    cx: float
    cy: float
    area: float
    angle: float
    width: float
    height: float


@dataclass
class Cluster:
    """
    Cumul temporel de points de détection pour une même forme.
    Contient un uuid stable, des points accumulés et le dernier indice de frame.
    """
    id: str
    shape: str
    points: List[ClusterPoint] = field(default_factory=list)
    last_seen: int = 0

    @property
    def centroid(self) -> Tuple[float, float]:
        xs = [p.cx for p in self.points]
        ys = [p.cy for p in self.points]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    @property
    def avg_width(self) -> float:
        return sum(p.width for p in self.points) / len(self.points)

    @property
    def avg_height(self) -> float:
        return sum(p.height for p in self.points) / len(self.points)

    @property
    def avg_angle(self) -> float:
        # moyenne simple des angles
        return sum(p.angle for p in self.points) / len(self.points)

    @property
    def confirmation_count(self) -> int:
        """Nombre de frames consécutives où ce cluster a été vu."""
        return len(self.points)


class ClusterTracker:
    """
    Suit dans le temps les clusters de formes détectées. 
    - Associe un UUID fixe à chaque cluster ("objet") créé.
    - Match des nouvelles détections à un cluster existant si : 
        * même 'shape', 
        * centroid à moins de `tol` pixels de l’ancien centroid.
    - Garde au maximum `max_history` points par cluster, et supprime un cluster 
      s’il n’a pas été mis à jour depuis plus de `max_history` frames.
    """

    def __init__(
        self,
        max_history: int = 10,
        tol: float = 3.0,
        area_threshold: float = 2000.0
    ):
        self.max_history = max_history
        self.tol = tol
        self.area_threshold = area_threshold
        self.frame_idx: int = 0
        self.clusters: List[Cluster] = []

    def update(self, detections: List[Tuple[str, float, float, float, float, float, float]]) -> None:
        """
        Met à jour les clusters existants avec une liste de nouvelles détections.
        Chaque `detection` est un tuple :
            (shape, cx, cy, area, angle, width, height).
        """
        self.frame_idx += 1

        for det in detections:
            shape, cx, cy, area, angle, width, height = det

            # Si area > area_threshold, on force angle à 0.0
            pt_angle = angle if area <= self.area_threshold else 0.0
            point = ClusterPoint(shape, cx, cy, area, pt_angle, width, height)

            matched = False
            for cluster in self.clusters:
                if self._matches(cluster, point):
                    # Ajoute ce point à l’historique du cluster
                    cluster.points.append(point)
                    cluster.last_seen = self.frame_idx
                    # Conserve au plus `max_history` points
                    if len(cluster.points) > self.max_history:
                        cluster.points.pop(0)
                    matched = True
                    break

            if not matched:
                # Création d’un nouveau cluster avec un UUID tout frais
                new_cluster = Cluster(
                    id=str(uuid.uuid4()),
                    shape=shape,
                    points=[point],
                    last_seen=self.frame_idx
                )
                self.clusters.append(new_cluster)

        # 2) Purge des clusters trop anciens (pas vus depuis > max_history)
        self.clusters = [
            c for c in self.clusters
            if self.frame_idx - c.last_seen <= self.max_history
        ]

    def _matches(self, cluster: Cluster, point: ClusterPoint) -> bool:
        """
        Vérifie si le `point` doit appartenir au même `cluster` existant :
         - même shape,
         - centroid(ancien cluster) ≈ centroid(nouveau point) à ± tol pixels.
        """
        if cluster.shape != point.shape:
            return False
        cx_prev, cy_prev = cluster.centroid
        return (
            abs(point.cx - cx_prev) <= self.tol
            and abs(point.cy - cy_prev) <= self.tol
        )

    def get_valid_clusters(self, min_confirmations: int = 1) -> List[Cluster]:
        """
        Renvoie les clusters ayant accumulé au moins `min_confirmations` points.
        Utile pour l’ObjectDetector ou la détection finale.
        """
        return [c for c in self.clusters if c.confirmation_count >= min_confirmations]

    def reset(self) -> None:
        """Vide tous les clusters et remet l’index de frame à zéro."""
        self.clusters.clear()
        self.frame_idx = 0
