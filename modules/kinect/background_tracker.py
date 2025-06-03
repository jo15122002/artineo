import uuid

class BackgroundTracker:
    """
    Gère l'UUID et le shape du fond actuellement posé,  
    en s'assurant qu'un même shape soit vu N frames de suite avant de l'émettre,  
    et qu'il soit absent M frames de suite avant de le supprimer.
    """

    def __init__(self, min_confirm_frames: int = 3, min_remove_frames: int = 3):
        # Les paramètres de robustesse :
        # - min_confirm_frames : nombre minimum de frames où l'on voit le même shape
        #   avant de considérer qu'il y a vraiment un nouveau fond.
        # - min_remove_frames  : nombre minimum de frames successives sans fond
        #   avant de considérer que l'ancien fond a disparu.
        self.min_confirm_frames = min_confirm_frames
        self.min_remove_frames  = min_remove_frames

        # Variables internes :
        self.current_shape: str | None = None
        self.current_id:    str | None = None

        # Pour suivre la forme candidate au changement :
        self.candidate_shape: str | None = None
        self.candidate_count: int       = 0  # nb. de frames consécutives où l'on a vu candidate_shape

        # Pour suivre la disparition :
        self.no_shape_count: int = 0  # nb. de frames consécutives sans aucun bg détecté

    def update(self, detected_shapes: list[str]) -> tuple[list[dict], list[str]]:
        """
        Appelé à chaque frame (ou détection).  
        - Si detected_shapes est vide pendant >= min_remove_frames, on supprime l'ancien fond.  
        - Sinon, si detected_shapes[0] change, on incrémente un compteur de stabilité ;  
          dès qu'il atteint min_confirm_frames, on confirme le nouveau fond.  
        Retourne (new_backgrounds, removed_background_ids).
        """
        new_backgrounds = []
        removed_ids = []

        # --- 1) Cas où il n'y a **pas** de shape détecté du tout cette frame ---
        if not detected_shapes:
            # On incrémente le compteur “pas de fond” :
            self.no_shape_count += 1

            # Tant qu’on n’atteint pas min_remove_frames, on ne fait rien.
            if self.current_id is not None and self.no_shape_count >= self.min_remove_frames:
                # Après assez de frames sans fond détecté, on lève la suppression
                removed_ids.append(self.current_id)
                self.current_shape = None
                self.current_id = None

                # On réinitialise les variables de choix :
                self.candidate_shape = None
                self.candidate_count = 0
                self.no_shape_count = 0

            # Si on n'avait pas de fond (current_id=None), on ne fait rien non plus.
            return new_backgrounds, removed_ids

        # Si on est ici, il y a au moins un detected_shapes[0]
        shape = detected_shapes[0]
        # ... donc on “reset” le compteur “pas de fond”
        self.no_shape_count = 0

        # --- 2) Cas où on n'a **pas de fond actuel** (current_shape=None) ---
        if self.current_shape is None:
            # Si la forme candidate n'a pas encore été initialisée, on démarre la phase d'accumulation :
            if self.candidate_shape is None:
                self.candidate_shape = shape
                self.candidate_count = 1
                return new_backgrounds, removed_ids

            # Si on voit à nouveau la même candidate → on incrémente
            if shape == self.candidate_shape:
                self.candidate_count += 1
                # Si on atteint le seuil, on confirme le nouveau fond :
                if self.candidate_count >= self.min_confirm_frames:
                    new_id = str(uuid.uuid4())
                    self.current_shape = shape
                    self.current_id    = new_id
                    new_backgrounds.append({
                        "id":    new_id,
                        "shape": shape,
                        # on pourra remplir “type”, “cx” etc. à l’extérieur
                    })
                    # On remet à zéro le candidat
                    self.candidate_shape = None
                    self.candidate_count = 0
            else:
                # On a vu une forme différente avant d'atteindre le seuil : on repart à zéro
                self.candidate_shape = shape
                self.candidate_count = 1

            return new_backgrounds, removed_ids

        # --- 3) Cas où on a déjà un fond confirmé (current_shape != None) ---
        if shape == self.current_shape:
            # Tant que c'est le même shape, on ne fait rien de plus
            return new_backgrounds, removed_ids

        # Si on arrive ici, detected_shapes[0] != current_shape : 
        # on a potentiellement un nouveau fond (shape différent).
        # on démarre / incrémente le compteur de ce nouveau candidat
        if self.candidate_shape is None or shape != self.candidate_shape:
            # soit on n'avait pas de candidat, soit c'est un candidat différent : on replace
            self.candidate_shape = shape
            self.candidate_count = 1
        else:
            # c'est la même candidate qu'à la frame précédente
            self.candidate_count += 1

        # Si on atteint le seuil de confirmation pour ce shape différent :
        if self.candidate_count >= self.min_confirm_frames:
            # On signale la suppression de l'ancien fond (car shape a clairement changé)
            if self.current_id is not None:
                removed_ids.append(self.current_id)

            new_id = str(uuid.uuid4())
            self.current_shape = shape
            self.current_id    = new_id
            new_backgrounds.append({
                "id":    new_id,
                "shape": shape,
                # on pourra compléter “type”, “cx” etc. à l’extérieur
            })
            # On remet le candidat à zéro pour la phase suivante
            self.candidate_shape = None
            self.candidate_count = 0

        return new_backgrounds, removed_ids
