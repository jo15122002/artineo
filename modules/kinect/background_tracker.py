import uuid


class BackgroundTracker:
    """
    Gère l'UUID et le shape du fond actuellement posé,
    en décidant s'il faut émettre un nouvel ID quand le shape change,
    ou signaler une suppression quand le fond disparaît.
    """

    def __init__(self):
        self.current_shape: str | None = None
        self.current_id:    str | None = None

    def update(self, detected_shapes: list[str]) -> tuple[list[dict], list[str]]:
        """
        Appelé à chaque frame (ou à chaque détection) avec la liste des shapes
        décelés dans bg_events (typiquement, 0 ou 1 élément).
        - Si detected_shapes est vide et qu'on avait déjà un fond, c'est une suppression.
        - Si detected_shapes[0] != self.current_shape, on crée un nouvel UUID.
        - Sinon, on ne fait rien.
        Retourne (new_backgrounds, removed_background_ids).
        """
        new_backgrounds = []
        removed_ids = []

        if not detected_shapes:
            # Il n'y a plus de fond détecté
            if self.current_id is not None:
                removed_ids.append(self.current_id)
                self.current_shape = None
                self.current_id = None
            return new_backgrounds, removed_ids

        # Il y a au moins un shape détecté
        shape = detected_shapes[0]
        if shape != self.current_shape:
            # Le fond a changé
            if self.current_id is not None:
                removed_ids.append(self.current_id)
            new_id = str(uuid.uuid4())
            self.current_shape = shape
            self.current_id = new_id
            new_backgrounds.append({
                "id":    new_id,
                "shape": shape,
                # on peut aussi remplir "type","cx","cy","w","h","angle","scale"
                # ou les recevoir en argument si besoin
            })
        # Sinon, shape == self.current_shape, on ne fait rien de plus
        return new_backgrounds, removed_ids
