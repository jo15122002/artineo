from collections import deque
import numpy as np

class FrameSmoother:
    """
    Maintient une fenêtre glissante de frames et renvoie la moyenne.
    """
    def __init__(self, window_size: int):
        self.window_size = window_size
        self._buffer = deque(maxlen=window_size)

    def add(self, frame: np.ndarray) -> None:
        # On stocke en float64 pour ne pas perdre en précision
        self._buffer.append(frame.astype(np.float64))

    def mean(self) -> np.ndarray:
        if not self._buffer:
            raise RuntimeError("Aucune frame à lisser")
        # Moyenne et reconversion au dtype original
        avg = np.mean(np.stack(self._buffer, axis=0), axis=0)
        return avg.astype(self._buffer[0].dtype)
