import cv2, numpy as np, queue, threading, sys
from ArtineoClient import ArtineoClient, ArtineoAction

# 1. Thread WS
ws_queue = queue.Queue()
def ws_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = ArtineoClient(module_id=1)
    loop.run_until_complete(client.connect_ws())
    while True:
        data = ws_queue.get()
        if data is None: break
        loop.run_until_complete(client.send_ws(ArtineoAction.SET, data))
    loop.run_until_complete(client.close_ws())

threading.Thread(target=ws_loop, daemon=True).start()

# 2. Capture direct
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_FPS, 30)

def detect_circle(gray):
    blur = cv2.GaussianBlur(gray, (5,5), 1)
    clean = cv2.morphologyEx(blur, cv2.MORPH_OPEN,
               cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    circles = cv2.HoughCircles(clean, cv2.HOUGH_GRADIENT,
            dp=2.0, minDist=100, param1=100, param2=40,
            minRadius=30, maxRadius=80)
    if circles is None: return None
    x,y,r = max(np.round(circles[0]).astype(int), key=lambda c: c[2])
    return x,y,r

frame_idx=0
cv2.namedWindow("Cam", cv2.WINDOW_NORMAL)
while True:
    ret, frame = cap.read()
    if not ret: break
    frame_idx += 1

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if frame_idx % 3 == 0:
        res = detect_circle(gray)
        if res:
            x,y,r = res
            cv2.circle(frame,(x,y),r,(0,255,0),2)
            ws_queue.put({"x":x,"y":y,"diameter":2*r})

    cv2.imshow("Cam", frame)
    if cv2.waitKey(1)&0xFF==ord('q'): break

# propre arrêt
ws_queue.put(None)
cap.release()
cv2.destroyAllWindows()