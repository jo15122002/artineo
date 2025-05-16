import numpy as np
import cv2

class StrokeAccumulator:
    """
    Exponential smoothing des variations de profondeur pour chaque outil.
    Si `abs_mode=True`, on suit bosses & creux. Sinon, on peut capter uniquement creux.
    """
    def __init__(self, tools, height, width, alpha, abs_mode=True):
        # Mappe outil → canal (0,1,2)
        self.tool_color = {t:i for i,t in enumerate(tools)}
        # Stocke un buffer float par outil, 3 canaux
        self.buffers = {
            t: np.zeros((height, width, 3), dtype=np.float32)
            for t in tools
        }
        self.alpha = alpha
        self.abs_mode = abs_mode

    def update(self, mapped: np.ndarray, tool: str) -> np.ndarray:
        """
        - mapped: uint8 (0-255), 128 = baseline
        - tool: str (ex. '1')
        Retourne image composite uint8 en 3 canaux pour détection.
        """
        # 1) calculer la variation signée
        diff = mapped.astype(int) - 128

        # 2) selon le mode, ne garder que les creux ou abs
        if self.abs_mode:
            diff = np.abs(diff)
        else:
            diff = (128 - mapped.astype(int)).clip(min=0)

        # 3) lissage exponentiel sur le canal dédié
        ch = self.tool_color[tool]
        buf = self.buffers[tool][:,:,ch]
        buf[:] = (1 - self.alpha) * buf + self.alpha * diff.astype(float)

        # 4) passage en uint8
        composite = cv2.convertScaleAbs(self.buffers[tool])
        return composite
