# stroke_lifetimer.py
from typing import List

class StrokeLifeTimer:
    """
    Gère la durée de vie des strokes : on décrémente chaque frame,
    on remet à max_age celles qu'on redétecte et on retire celles arrivées à 0.
    """
    def __init__(self, max_age: int = 5):
        self.max_age = max_age
        self.ages: dict[str, int] = {}

    def update(self, active_ids: List[str]) -> List[str]:
        """
        - active_ids : liste des IDs de strokes redétectées cette frame.
        Retourne la liste des IDs à retirer (celle dont l'âge est <= 0).
        """
        # 1) Reset age des strokes actives
        for sid in active_ids:
            self.ages[sid] = self.max_age

        # 2) Décrémente les autres
        to_remove = []
        for sid in list(self.ages):
            if sid not in active_ids:
                self.ages[sid] -= 1
                if self.ages[sid] <= 0:
                    to_remove.append(sid)
                    del self.ages[sid]
        return to_remove
