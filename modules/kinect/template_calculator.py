import os
import cv2
import numpy as np
from pathlib import Path

from kinect_interface import KinectInterface
from config import Config

# Configuration (vous pouvez aussi la sortir vers votre config.py)
TEMPLATE_NAMES    = ["landscape_sea", "landscape_fields",
                     "medium_lighthouse", "medium_mill", "small_boat"]
OUT_DIR           = "templates"
BASELINE_FRAMES   = 30
DEPTH_THRESHOLD   = 5  # mm

os.makedirs(OUT_DIR, exist_ok=True)

def main():
    cfg = Config()  # ou Config(**raw_config) si besoin
    kin = KinectInterface(cfg)
    kin.open()
    print("✅ Kinect via KinectInterface initialisée.")

    baseline = None
    next_idx = 0

    print("b = capture baseline  │  c = capture template  │  q = quitter")

    while True:
        if not kin.has_new_depth_frame():
            key = cv2.waitKey(1) & 0xFF
        else:
            frame = kin.get_depth_frame()  # ndarray uint16 déjà à la bonne forme
            # Affichage ×2 pour le visuel
            disp = cv2.convertScaleAbs(frame, alpha=255.0/(frame.max() or 1))
            disp = cv2.resize(disp, None, fx=2, fy=2,
                              interpolation=cv2.INTER_NEAREST)
            cv2.imshow("Depth", disp)
            key = cv2.waitKey(1) & 0xFF

        if key == ord('b'):
            # calcul du baseline
            print("→ Capturing baseline…")
            buffer = []
            for _ in range(BASELINE_FRAMES):
                while not kin.has_new_depth_frame():
                    pass
                buffer.append(kin.get_depth_frame())
            baseline = np.median(np.stack(buffer), axis=0).astype(np.uint16)
            print("✔ Baseline OK.")

        elif key == ord('c'):
            if baseline is None:
                print("‼️ Faites d’abord ‘b’ pour capturer le baseline.")
                continue
            if next_idx >= len(TEMPLATE_NAMES):
                print("✅ Tous les templates faits.")
                continue

            depth = frame  # dernière frame lue
            diff = np.abs(depth.astype(int) - baseline.astype(int))
            mask = diff > DEPTH_THRESHOLD

            ys, xs = np.where(mask)
            if xs.size == 0:
                print("⚠️ Aucun objet détecté.")
                continue

            x1, x2 = xs.min(), xs.max()
            y1, y2 = ys.min(), ys.max()
            tpl = depth[y1:y2+1, x1:x2+1]

            name = TEMPLATE_NAMES[next_idx]
            path = Path(OUT_DIR)/f"{name}.npy"
            np.save(str(path), tpl)
            print(f"✔ {name}.npy ({tpl.shape})")

            # affichage du template
            disp_t = cv2.convertScaleAbs(tpl, alpha=255.0/(tpl.max() or 1))
            disp_t = cv2.resize(disp_t, None, fx=2, fy=2,
                                interpolation=cv2.INTER_NEAREST)
            cv2.imshow("Template", disp_t)

            next_idx += 1

        elif key == ord('q'):
            break

    kin.close()
    cv2.destroyAllWindows()
    print("Templates enregistrés dans", OUT_DIR)

if __name__ == "__main__":
    main()
