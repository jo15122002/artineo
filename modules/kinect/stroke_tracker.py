from typing import List, Dict

class StrokeTracker:
    """
    Tracker de strokes pour éviter les duplications dans all_strokes.
    Compare raw et all_strokes et ne renvoie que les nouveaux points.
    """
    def __init__(self, proximity_threshold: float = 5.0):
        """
        Args:
            proximity_threshold: distance max (en pixels) pour considérer deux points identiques.
        """
        self.proximity_threshold = proximity_threshold

    def update(self, raw: List[Dict], all_strokes: List[Dict]) -> List[Dict]:
        """
        Filtre raw pour ne garder que les events n'existant pas déjà dans all_strokes.

        Args:
            raw: liste de nouveaux events [{'tool_id', 'x', 'y', 'size'}].
            all_strokes: historique complet des events déjà envoyés.

        Returns:
            List de nouveaux events à ajouter.
        """
        new_events: List[Dict] = []
        for event in raw:
            exists = any(
                prev['tool_id'] == event['tool_id'] and
                abs(prev['x'] - event['x']) <= self.proximity_threshold and
                abs(prev['y'] - event['y']) <= self.proximity_threshold
                for prev in all_strokes
            )
            if not exists:
                new_events.append(event)
        return new_events
