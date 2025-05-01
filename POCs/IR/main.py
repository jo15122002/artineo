import asyncio
import queue
import sys
import threading
from pathlib import Path

import cv2
import numpy as np

# importer ArtineoClient
sys.path.insert(0, str(Path(__file__).resolve().parent.joinpath("..","..","serveur")))
from ArtineoClient import ArtineoAction, ArtineoClient

# Thread WS qui lit dans ws_queue
ws_queue = queue.Queue()
def ws_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = ArtineoClient(module_id=1)
    loop.run_until_complete(client.connect_ws())
    while True:
        data = ws_queue.get()
        if data is None: break
        loop.run_until_complete(client.send_ws(ArtineoAction.SET, data))
    loop.run_until_complete(client.close_ws())

threading.Thread(target=ws_thread, daemon=True).start()

def preprocess(gray):
    # blur plus petit + ouverture simple
    blur = cv2.GaussianBlur(gray, (5,5), 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
    return cv2.morphologyEx(blur, cv2.MORPH_OPEN, kernel)

def find_circle(img):
    circles = cv2.HoughCircles(
        img, cv2.HOUGH_GRADIENT,
        dp=2.0, minDist=80,
        param1=100, param2=30,
        minRadius=15, maxRadius=80
    )
    if circles is None: return None
    c = max(np.round(circles[0]).astype(int), key=lambda x: x[2])
    return tuple(c)  # (x,y,r)

def main():
    W, H = 320, 240
    frame_sz = W*H*3

    cv2.namedWindow("Cam", cv2.WINDOW_NORMAL)
    frame_idx = 0

    while True:
        buf = sys.stdin.buffer.read(frame_sz)
        if len(buf) < frame_sz:
            break
        frame = np.frombuffer(buf, np.uint8).reshape((H, W, 3))

        frame_idx += 1
        # Ne traiter que 1 frame sur 3
        if frame_idx % 3 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clean = preprocess(gray)
            circ = find_circle(clean)
            if circ:
                x, y, r = circ
                cv2.circle(frame, (x, y), r, (0,255,0), 2)
                diameter = 2*r
                # push asynchrone
                ws_queue.put({"x":x, "y":y, "diameter": diameter})

        cv2.imshow("Cam", frame)
        if cv2.waitKey(1)&0xFF == ord('q'):
            break

    # signaler au thread de s'arrêter
    ws_queue.put(None)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()