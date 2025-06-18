import uuid
from typing import List, Dict, Any, Tuple

class StrokeConfirmTracker:
    """
    Retourne les strokes confirmées uniquement après un minimum de frames consécutives.
    """
    def __init__(
        self,
        proximity_threshold: float = 5.0,
        min_confirm: int = 3
    ):
        self.proximity_threshold = proximity_threshold
        self.min_confirm = min_confirm
        # candidates: id -> {'centroid':(x,y), 'count':n, 'event':dict}
        self.candidates: Dict[str, Dict[str, Any]] = {}

    def update(self, raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        confirmed: List[Dict[str, Any]] = []
        new_cands: Dict[str, Dict[str, Any]] = {}

        # pour chaque event cru, trouver un candidat existant ou créer un nouveau
        for ev in raw_events:
            x, y = ev['x'], ev['y']
            match_id = None
            # recherche d'un candidat proche
            for cid, cand in self.candidates.items():
                cx, cy = cand['centroid']
                if abs(x-cx) <= self.proximity_threshold and abs(y-cy) <= self.proximity_threshold:
                    match_id = cid
                    break

            if match_id:
                # mise à jour du candidat existant
                count_prev = self.candidates[match_id]['count']
                new_count = count_prev + 1
                new_cands[match_id] = {
                    'centroid': (x, y),
                    'count': new_count,
                    'event': ev,
                }
            else:
                # nouveau candidat
                cid = str(x) + '_' + str(y)
                new_cands[cid] = {
                    'centroid': (x, y),
                    'count': 1,
                    'event': ev,
                }

        # collecter les confirmées
        for cid, cand in new_cands.items():
            if cand['count'] >= self.min_confirm:
                confirmed.append(cand['event'])

        # remplacer les candidats
        self.candidates = new_cands
        return confirmed