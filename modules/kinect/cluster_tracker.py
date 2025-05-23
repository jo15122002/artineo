from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ClusterPoint:
    """Represents a single detection point in a cluster."""
    shape: str
    cx: float
    cy: float
    area: float
    angle: float
    width: float
    height: float


@dataclass
class Cluster:
    """Holds temporal accumulation of detection points for one object shape."""
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
        # average angle, taking simple mean
        return sum(p.angle for p in self.points) / len(self.points)

    @property
    def confirmation_count(self) -> int:
        """Number of consecutive frames this cluster has been observed."""
        return len(self.points)


class ClusterTracker:
    """
    Tracks clusters of detected shapes over time.
    Handles matching new detections to existing clusters based on spatial proximity
    and shape identity, keeps a sliding history of points, and prunes old clusters.
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
        Update clusters with a list of detections.
        Each detection is a tuple: (shape, cx, cy, area, angle, width, height).
        """
        self.frame_idx += 1
        for det in detections:
            shape, cx, cy, area, angle, width, height = det
            point = ClusterPoint(shape, cx, cy, area, angle if area <= self.area_threshold else 0.0, width, height)

            matched = False
            for cluster in self.clusters:
                if self._matches(cluster, point):
                    cluster.points.append(point)
                    cluster.last_seen = self.frame_idx
                    if len(cluster.points) > self.max_history:
                        cluster.points.pop(0)
                    matched = True
                    break

            if not matched:
                new_cluster = Cluster(shape=shape, points=[point], last_seen=self.frame_idx)
                self.clusters.append(new_cluster)

        # prune clusters not seen recently
        self.clusters = [c for c in self.clusters if self.frame_idx - c.last_seen <= self.max_history]

    def _matches(self, cluster: Cluster, point: ClusterPoint) -> bool:
        """
        Determine if a new point belongs to an existing cluster
        based on shape equality and spatial proximity.
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
        Return clusters with at least `min_confirmations` accumulated points.
        Useful for downstream object detection.
        """
        return [c for c in self.clusters if c.confirmation_count >= min_confirmations]

    def reset(self) -> None:
        """Clear all tracked clusters and reset frame index."""
        self.clusters.clear()
        self.frame_idx = 0
