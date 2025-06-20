#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

# Zoom numérique : facteur >1 pour agrandir (ex: 2.0 pour zoom ×2)
ZOOM_FACTOR = 2.0

# On ajoute ../../serveur au path pour importer ArtineoClient
sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parent
        .joinpath("..", "..", "serveur", "back")
        .resolve()
    )
)
from ArtineoClient import ArtineoAction, ArtineoClient


def preprocess(gray):
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.morphologyEx(blur, cv2.MORPH_OPEN, kernel)


def find_brightest_circle(gray, clean):
    circles = cv2.HoughCircles(
        clean,
        cv2.HOUGH_GRADIENT,
        dp=2.0,
        minDist=80,
        param1=100,
        param2=30,
        minRadius=10,
        maxRadius=80
    )
    if circles is None:
        return None

    candidates = np.round(circles[0]).astype(int)
    best = None
    best_mean = -1.0

    for x, y, r in candidates:
        mask = np.zeros_like(gray, dtype=np.uint8)
        cv2.circle(mask, (x, y), r, 255, thickness=-1)
        mean_val = cv2.mean(gray, mask=mask)[0]
        if mean_val > best_mean:
            best_mean = mean_val
            best = (int(x), int(y), int(r))

    return best


def main():
    # --- parsing des arguments ---
    parser = argparse.ArgumentParser(description="Module IR")
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Active le mode debug (affiche les logs détaillés et la fenêtre vidéo)"
    )
    args = parser.parse_args()
    debug = args.debug

    if debug:
        print("Mode debug activé. Affichage des logs et de la fenêtre vidéo.")
    else:
        print("Mode debug désactivé. Aucune fenêtre vidéo ne sera affichée.")

    def log(msg: str):
        """Affiche msg uniquement si debug est True."""
        if debug:
            print(msg)

    # résolution d’entrée après redimensionnement ffmpeg
    width, height = 320, 240
    frame_size = width * height * 3  # bgr24

    # 1) Initialisation du client WS
    client = ArtineoClient(module_id=1)

    # 2) Démarrage du handler WS dans un thread dédié
    def run_ws():
        asyncio.run(client._ws_handler())
    threading.Thread(target=run_ws, daemon=True).start()
    log("WebSocket handler démarré dans un thread dédié.")

    # 3) (Optionnel) callback de réception
    client.on_message = lambda msg: log(f"Message reçu : {msg}")

    # 4) Envoi + mesure RTT
    def safe_send(action, data):
        ts = time.time() * 1000
        payload = {
            "module": client.module_id,
            "action": action,
            "data": data,
            "_ts_client": ts
        }
        msg = json.dumps(payload)
        client.send_ws(msg)
        log(f"[DEBUG] Envoi WS à {ts:.0f} → {msg}")

        # → ici, juste après l'envoi, on récupère le RTT
        try:
            latency = client.get_latency(timeout=2.0)
            log(f"⏱ RTT WS ~ {latency:.1f} ms")
        except Exception as e:
            log(f"[WARN] Impossible de mesurer le RTT : {e}")

    # 4b) Préparation de la fenêtre d'affichage si debug
    if debug:
        cv2.namedWindow("Flux de la caméra", cv2.WINDOW_NORMAL)

    # 5) Boucle de lecture du flux caméra
    while True:
        raw = sys.stdin.buffer.read(frame_size)
        if len(raw) < frame_size:
            break  # fin du flux
        frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))

        # --- Zoom numérique via crop + resize ---
        if ZOOM_FACTOR > 1.0:
            h, w = frame.shape[:2]
            new_w = int(w / ZOOM_FACTOR)
            new_h = int(h / ZOOM_FACTOR)
            x0 = (w - new_w) // 2
            y0 = (h - new_h) // 2
            cropped = frame[y0:y0+new_h, x0:x0+new_w]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clean = preprocess(gray)

        best = find_brightest_circle(gray, clean)
        if best:
            x, y, r = best
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            safe_send(ArtineoAction.SET, {
                "x": x,
                "y": y,
                "diameter": r * 2
            })

        # Affichage seulement si debug
        if debug:
            cv2.imshow("Flux de la caméra", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    # 6) Nettoyage fenêtre si debug
    if debug:
        cv2.destroyAllWindows()
        log("Fin du module, le thread WS s'arrêtera automatiquement.")


if __name__ == "__main__":
    main()
