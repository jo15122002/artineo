import os
import cv2
import numpy as np
from pathlib import Path

from kinect_interface import KinectInterface
from config import Config

# NOMS DES TEMPLATES (dans l’ordre où vous les capturez)
TEMPLATE_NAMES    = [
    "landscape_sea",
    "landscape_fields",
    "medium_lighthouse",
    "medium_mill",
    "small_boat"
]
OUT_DIR           = "templates"
BASELINE_FRAMES   = 30
DEPTH_THRESHOLD   = 5  # mm : seuil pour isoler l’objet sur le fond

os.makedirs(OUT_DIR, exist_ok=True)

def main():
    cfg = Config()  # ou Config(**raw_config) selon votre usage
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
            frame = kin.get_depth_frame()  # uint16 (mm)
            # Affichage ×2 pour visualiser la depth map
            disp = cv2.convertScaleAbs(frame, alpha=255.0/(frame.max() or 1))
            disp = cv2.resize(disp, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            cv2.imshow("Depth", disp)
            key = cv2.waitKey(1) & 0xFF

        if key == ord('b'):
            # 1) Calcul de la baseline (médiane de BASELINE_FRAMES frames)
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
                print("‼️ Faites d’abord ‘b’ pour capturer la baseline.")
                continue
            if next_idx >= len(TEMPLATE_NAMES):
                print("✅ Tous les templates ont déjà été capturés.")
                continue

            depth = frame  # dernière frame lue (avec l’objet posé sur le bac)
            # 2) On calcule la différence absolue entre baseline et profondeur courante
            diff = np.abs(depth.astype(int) - baseline.astype(int))
            mask = diff > DEPTH_THRESHOLD  # on ne garde que là où un objet dégage le sable

            ys, xs = np.where(mask)
            if xs.size == 0:
                print("⚠️ Aucun objet détecté (aucune profondeur différente du fond).")
                continue

            # 3) On recadre au rectangle englobant du masque
            x1, x2 = xs.min(), xs.max()
            y1, y2 = ys.min(), ys.max()
            # depth_abs contiendra la profondeur absolue du carton + sable
            depth_abs = depth[y1:y2+1, x1:x2+1].astype(float)
            # baseline_abs est la profondeur du sable seul sous cette zone
            baseline_patch = baseline[y1:y2+1, x1:x2+1].astype(float)
            # 4) On calcule le template RELATIF = (baseline – depth_abs)
            #    Ce qui donne, pour chaque pixel, la « hauteur » du carton (≥ 0)
            template_rel = baseline_patch - depth_abs.astype(float)

            name = TEMPLATE_NAMES[next_idx]
            path = Path(OUT_DIR) / f"{name}.npy"
            np.save(str(path), template_rel.astype(np.float32))
            print(f"✔ {name}.npy (shape {template_rel.shape}) enregistré en mode relatif.")

            # affichage rapide du template_rel (hauteur)
            disp_t = np.zeros_like(template_rel, dtype=np.uint8)
            # On normalise pour voir dans [0..255]
            vmax = np.nanmax(template_rel) or 1.0
            disp_t = cv2.convertScaleAbs(template_rel, alpha=255.0 / vmax)
            disp_t = cv2.resize(disp_t, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            cv2.imshow("Template (hauteur)", disp_t)

            next_idx += 1

        elif key == ord('q'):
            break

    kin.close()
    cv2.destroyAllWindows()
    print("✅ Templates relatifs générés dans", OUT_DIR)


if __name__ == "__main__":
    main()
