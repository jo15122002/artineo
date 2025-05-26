import cv2
import numpy as np
import time
import sys
from kinect_interface import KinectInterface
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

class RoiCalibrator:
    """
    Affiche un flux depth (ou binarisé) agrandi par 'scale' et
    montre la position du curseur. Appuyez sur [espace] pour valider,
    [q] pour quitter.
    """
    def __init__(self, kinect_interface: KinectInterface, scale: int = 2):
        self.kinect = kinect_interface
        self.scale = scale
        self.selected = (0, 0)
        self.window = "RoiCalibrator"
        cv2.namedWindow(self.window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self.selected = (x, y)

    def run(self):
        while True:
            if not self.kinect.has_new_depth_frame():
                time.sleep(0.01)
                continue

            frame = self.kinect._get_raw_depth().astype(np.uint16)
            # Normalisation + conversion en 8-bits
            disp = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            # Agrandissement
            h, w = disp.shape
            disp = cv2.resize(disp, (w * self.scale, h * self.scale))

            # Affichage de la position (remise à l’échelle)
            x_s, y_s = self.selected
            x0, y0 = x_s // self.scale, y_s // self.scale
            cv2.putText(
                disp,
                f"Cursor: ({x0}, {y0})",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
            )

            cv2.imshow(self.window, disp)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):      # [espace] pour valider
                print(f"Selected ROI: ({x0}, {y0})")
                break
            elif key == ord("q"):    # [q] pour quitter
                sys.exit(0)

        cv2.destroyWindow(self.window)
        return (x0, y0)