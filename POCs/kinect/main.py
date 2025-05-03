import asyncio
import glob
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from dependencies.pykinect2 import PyKinectRuntime, PyKinectV2

sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parent
        .joinpath("..", "..", "serveur")
        .resolve()
    )
)
from ArtineoClient import ArtineoAction, ArtineoClient  # type: ignore

client = ArtineoClient(module_id=4, host="192.168.0.180", port=8000)
config = client.fetch_config()
print("Configuration récupérée : ", config)

latest_payload = None
strokes_events = []
objects_events = []

# --- Paramètres de la Région d'Intérêt (ROI) ---
ROI_X0, ROI_Y0 = 160, 130
ROI_X1, ROI_Y1 = 410, 300
ROI_WIDTH = ROI_X1 - ROI_X0   # 250 pixels
ROI_HEIGHT = ROI_Y1 - ROI_Y0  # 170 pixels

TEMPLATE_DIR = "images/templates/"

# Méthode de comparaison choisie :
USE_MATCHSHAPES = True
AREA_THRESHOLD = 2000
SMALL_AREA_THRESHOLD = 300

N_PROFILE = 100
background_profiles = {}

frame_idx = 0

template_contours = {}
template_sizes = {}
overlays = {}
clusters = []

# Chargement des templates
for filepath in glob.glob(os.path.join(TEMPLATE_DIR, "*.png")):
    name = os.path.splitext(os.path.basename(filepath))[0]
    img_gray = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        raise FileNotFoundError(f"Image introuvable : {filepath}")
    _, thresh_inv = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(cnts, key=cv2.contourArea)
    template_contours[name] = cnt
    x, y, w_t, h_t = cv2.boundingRect(cnt)
    template_sizes[name] = (w_t, h_t)

forme_templates = {n: c for n, c in template_contours.items() if n.startswith("Forme_")}
fond_templates  = {n: c for n, c in template_contours.items() if n.startswith("Fond_")}
small_templates = {n: c for n, c in template_contours.items() if n.startswith("Small_")}

def compute_profile(mask, name=None, n=N_PROFILE):
    h, w = mask.shape
    xs = np.linspace(0, w-1, n, dtype=int)
    prof = np.zeros(n, dtype=float)
    for i, x in enumerate(xs):
        ys = np.where(mask[:, x] > 0)[0]
        prof[i] = float(ys.min())/h if ys.size else 0.0

    if name:
        plot_h, plot_w = 200, n
        img_plot = np.ones((plot_h, plot_w, 3), dtype=np.uint8)*255
        pts = [(i, int((1 - prof[i])*(plot_h-1))) for i in range(n)]
        for i in range(1, n):
            cv2.line(img_plot, pts[i-1], pts[i], (0,0,0), 1)
        cv2.namedWindow(f"profile_{name}", cv2.WINDOW_NORMAL)
        cv2.imshow(f"profile_{name}", img_plot)

    return prof.tolist()

# Pré-calc des profils et overlays
for name, cnt in template_contours.items():
    path = os.path.join(TEMPLATE_DIR, f"{name}.png")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Overlay introuvable : {path}")

    if name.startswith("Forme_") or name.startswith("Small_"):
        # Sprite recadré + alpha
        alpha = img[...,3] if img.shape[2]==4 else None
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if alpha is None else None
        mask  = (alpha>0) if alpha is not None else (gray<255)
        ys, xs = np.where(mask)
        y0, y1 = ys.min(), ys.max()
        x0, x1 = xs.min(), xs.max()
        sprite = img[y0:y1+1, x0:x1+1].copy()
        if sprite.shape[2]==3:
            gray = cv2.cvtColor(sprite, cv2.COLOR_BGR2GRAY)
            _, a = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY_INV)
            sprite = np.dstack([sprite, a])
        # ferme trous alpha
        kern = np.ones((3,3),np.uint8)
        sprite[:,:,3] = cv2.morphologyEx(sprite[:,:,3], cv2.MORPH_CLOSE, kern, iterations=2)
        overlays[name] = sprite
    else:
        bgr = img[:,:,:3] if img.shape[2]==4 else img
        gray_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_full, 128, 255, cv2.THRESH_BINARY)
        prof = compute_profile(mask, name)
        background_profiles[name] = prof
        overlays[name] = img

for name, prof in background_profiles.items():
    prof_arr = np.array(prof)
    print(name, prof_arr[:5], float(prof_arr.mean()))

def classify_background_by_profile(cnt):
    x,y,w_d,h_d = cv2.boundingRect(cnt)
    mask = np.zeros((h_d, w_d), dtype=np.uint8)
    cnt_s = cnt - [x,y]
    cv2.drawContours(mask, [cnt_s], -1, 255, cv2.FILLED)
    prof = np.array(compute_profile(mask))
    best_name, best_d = None, float("inf")
    for n,tprof in background_profiles.items():
        d = np.linalg.norm(prof - np.array(tprof))
        if d<best_d:
            best_d, best_name = d, n
    print(f"Profil classifié : {best_name} (d={best_d:.2f})")
    return best_name

def classify_contour(cnt):
    area = cv2.contourArea(cnt)
    if area < SMALL_AREA_THRESHOLD:
        candidates = small_templates
    elif area < AREA_THRESHOLD:
        candidates = forme_templates
    else:
        return classify_background_by_profile(cnt)

    best_score, best_name = float("inf"), None
    if USE_MATCHSHAPES:
        for n,tc in candidates.items():
            s = cv2.matchShapes(cnt, tc, cv2.CONTOURS_MATCH_I1, 0.0)
            print(f"Score {n}: {s:.2f}")
            if s<best_score:
                best_score, best_name = s, n
    else:
        hu1 = cv2.HuMoments(cv2.moments(cnt)).flatten()
        for n,tc in candidates.items():
            hu2 = cv2.HuMoments(cv2.moments(tc)).flatten()
            s = np.linalg.norm(hu1-hu2)
            print(f"Score {n}: {s:.2f}")
            if s<best_score:
                best_score, best_name = s, n
    print(f"Contour classifié : {best_name} (s={best_score:.2f})")
    return best_name

def overlay_png(canvas, overlay, cx, cy, scale=1.0):
    h0,w0 = overlay.shape[:2]
    if scale!=1.0:
        overlay = cv2.resize(overlay,(int(w0*scale),int(h0*scale)),interpolation=cv2.INTER_AREA)
    h,w = overlay.shape[:2]
    x0 = cx - w//2; y0 = cy - h//2
    x1,y1 = x0+w, y0+h
    ox0,oy0 = max(0,-x0), max(0,-y0)
    x0_,y0_ = max(0,x0), max(0,y0)
    x1_,y1_ = min(canvas.shape[1],x1), min(canvas.shape[0],y1)
    ov = overlay[oy0:oy0+(y1_-y0_), ox0:ox0+(x1_-x0_)]
    if ov.ndim==2:
        bgr = cv2.cvtColor(ov, cv2.COLOR_GRAY2BGR).astype(float)
        _,a = cv2.threshold(ov,254,255,cv2.THRESH_BINARY_INV)
        alpha = (a/255.0)[...,None]
    elif ov.shape[2]==2:
        bgr = cv2.cvtColor(ov[:,:,0],cv2.COLOR_GRAY2BGR).astype(float)
        alpha = (ov[:,:,1]/255.0)[...,None]
    elif ov.shape[2]==3:
        bgr = ov.astype(float)
        gray = cv2.cvtColor(ov, cv2.COLOR_BGR2GRAY)
        _,a = cv2.threshold(gray,254,255,cv2.THRESH_BINARY_INV)
        alpha = (a/255.0)[...,None]
    else:
        bgr = ov[:,:,:3].astype(float)
        alpha = (ov[:,:,3]/255.0)[...,None]
    inv = 1-alpha
    roi = canvas[y0_:y1_, x0_:x1_].astype(float)
    canvas[y0_:y1_, x0_:x1_] = (roi*inv + bgr*alpha).astype(np.uint8)

def update_clusters(dets, max_h=10, tol=3):
    global clusters, frame_idx
    for shape,cx,cy,area,ang,w,h in dets:
        matched=False
        if area>AREA_THRESHOLD:
            ang=0.0
        for cl in clusters:
            if cl['shape']==shape and abs(cx-cl['centroid'][0])<=tol and abs(cy-cl['centroid'][1])<=tol:
                cl['points'].append((cx,cy,area,ang,w,h))
                if len(cl['points'])>max_h:
                    cl['points'].pop(0)
                cl['last_seen']=frame_idx
                matched=True
                break
        if not matched:
            clusters.append({
                'shape':shape,
                'points':[(cx,cy,area,ang,w,h)],
                'centroid':(cx,cy),
                'avg_w':w,'avg_h':h,'avg_angle':ang,
                'sprite':None,'sprite_params':(0.0,0.0),
                'last_seen':frame_idx
            })
    clusters[:] = [cl for cl in clusters if frame_idx-cl['last_seen']<=10]

display_scale = 2
def crop_to_roi(img): return img[ROI_Y0:ROI_Y1, ROI_X0:ROI_X1]
def show_image(name, img):
    rz = cv2.resize(img, (img.shape[1]*display_scale, img.shape[0]*display_scale))
    cv2.imshow(name, rz)

mouse_x=mouse_y=0
def mouse_cb(evt,x,y,_,__):
    global mouse_x,mouse_y
    if evt==cv2.EVENT_MOUSEMOVE:
        mouse_x,mouse_y = x//display_scale, y//display_scale

tool_color = {'1':0,'2':2,'3':1,'4':3}

# Init Kinect
try:
    kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
    print("Kinect initialisée.")
except Exception as e:
    print("Erreur Kinect:", e); exit(1)

# Globals for drawing
tool_base_frames = {}
frames = []
cropped_frames = []
base_frame = None
final_drawings = {t: np.zeros((ROI_HEIGHT,ROI_WIDTH,3), dtype=float) for t in ['1','2','3']}
current_tool = '1'
delta = 30; scale=738.0/delta; alpha=0.3; brush_scale=1.2

brush = cv2.imread("images/brushes/brush3.png", cv2.IMREAD_GRAYSCALE)
if brush is None:
    print("Brush introuvable"); exit(1)
brush = brush.astype(float)/255.0
def resize_brush(b,s): return cv2.resize(b,(max(3,min(1000,int(s))),)*2)

win_names = ["Mapped Depth","Depth frame","Binary Mask Debug","Distance Map Debug","Mask Objects"]
for w in win_names:
    cv2.namedWindow(w, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(w, ROI_WIDTH*display_scale, ROI_HEIGHT*display_scale)
cv2.setMouseCallback("Mapped Depth", mouse_cb)
cv2.setMouseCallback("Depth frame", mouse_cb)
cv2.setMouseCallback("Distance Map Debug", mouse_cb)

def detect_objects(frame):
    _,mask = cv2.threshold(frame,80,255,cv2.THRESH_BINARY_INV)
    kern=np.ones((2,2),np.uint8)
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,kern)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kern)
    cv2.imshow("Mask Objects",mask)
    dets=[]
    for cnt in cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]:
        a=cv2.contourArea(cnt)
        if a<200: continue
        M=cv2.moments(cnt)
        if M['m00']==0: continue
        cx,cy = M['m10']/M['m00'], M['m01']/M['m00']
        hull=cv2.convexHull(cv2.approxPolyDP(cnt,1.0,True))
        pts=hull.reshape(-1,2)
        dists = np.hypot(*(pts - [cx,cy]).T)
        med = np.median(dists)
        mask_filt = pts[np.where(dists>med+5)] if np.any(dists>med+5) else pts
        idx = np.argmax(np.hypot(mask_filt[:,0]-cx,mask_filt[:,1]-cy))
        tip = mask_filt[idx]
        ang = math.degrees(math.atan2(tip[1]-cy, tip[0]-cx))
        ang = ang if ang>=0 else ang+360
        x,y,w_d,h_d = cv2.boundingRect(cnt)
        shape = classify_contour(cnt)
        dets.append((shape, int(cx), int(cy), float(a), float(ang), float(w_d), float(h_d)))
    update_clusters(dets)

def process_depth_frame(cf):
    global base_frame, final_drawings
    diff = cf.astype(int)-base_frame.astype(int)
    mapped = np.clip(128 + diff*scale, 0,255).astype(np.uint8)
    show_image("Mapped Depth", mapped)
    if current_tool=='4':
        detect_objects(mapped); return
    ch = tool_color[current_tool]
    col = np.zeros((ROI_HEIGHT,ROI_WIDTH,3),dtype=np.uint8)
    col[:,:,ch]=mapped
    cur_diff = (mapped.astype(int)-128).clip(min=0).astype(float)
    fd = final_drawings[current_tool][:,:,ch]
    fd[:] = (1-alpha)*fd + alpha*cur_diff
    fd[fd<0.7]=0
    fd*=0.95

def render_final_drawings():
    for t in ['1']:
        fd = cv2.convertScaleAbs(final_drawings[t])
        white = np.full(fd.shape,255,dtype=np.uint8)
        ch = tool_color[t]
        m = (fd[:,:,ch].astype(float)/255.0)[...,None]
        color = np.array([255,0,0],dtype=float)
        res = (1-m)*white + m*color
        show_image(f"Final Drawing {t}", np.clip(res,0,255).astype(np.uint8))

def composite_colored_drawing():
    comp = np.zeros((ROI_HEIGHT,ROI_WIDTH,3),dtype=float)
    for t,d in final_drawings.items():
        ch=tool_color[t]
        layer = np.zeros_like(d); layer[:,:,ch]=d[:,:,ch]
        comp = cv2.add(comp, layer)
    return cv2.convertScaleAbs(comp)

def process_brush_strokes():
    global frame_idx, strokes_events
    strokes_events.clear()
    frame_idx += 1
    comp = composite_colored_drawing()
    gray = cv2.GaussianBlur(cv2.cvtColor(comp,cv2.COLOR_BGR2GRAY),(3,3),0)
    show_image("Depth frame", comp)
    _,bin_img = cv2.threshold(gray,3,255,cv2.THRESH_BINARY)
    kern=np.ones((3,3),np.uint8)
    bin_img=cv2.morphologyEx(bin_img,cv2.MORPH_OPEN,kern,iterations=3)
    bin_img=cv2.morphologyEx(bin_img,cv2.MORPH_CLOSE,kern,iterations=3)
    dist_map = cv2.distanceTransform(bin_img,cv2.DIST_L2,5)
    disp = cv2.normalize(dist_map,None,0,255,cv2.NORM_MINMAX).astype(np.uint8)
    contours,_ = cv2.findContours(bin_img,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    brushed = np.full((ROI_HEIGHT,ROI_WIDTH,3),255,dtype=np.uint8)
    for cnt in contours:
        if cv2.contourArea(cnt)<100: continue
        mask_c = np.zeros(bin_img.shape, dtype=np.uint8)
        cv2.drawContours(mask_c,[cnt],-1,255,cv2.FILLED)
        region = dist_map.copy()
        region[mask_c==0]=0
        rm = region.max()
        if rm<1: continue
        dil = cv2.dilate(dist_map,kern)
        local_max = (dist_map==dil)&(mask_c==255)&(dist_map>=rm-7)
        ys,xs = np.where(local_max)
        for y,x in zip(ys,xs):
            val = dist_map[y,x]
            if val<1 or val>150: continue
            b = resize_brush(brush, val*brush_scale)
            color = {'1':(0,0,255),'2':(255,0,0),'3':(0,255,0),'4':(0,0,0)}[current_tool]
            bh,bw = b.shape
            y0,x0 = max(0,y-bh//2), max(0,x-bw//2)
            y1,x1 = min(ROI_HEIGHT,y0+bh), min(ROI_WIDTH,x0+bw)
            r = b[:y1-y0,:x1-x0,None]
            dst = brushed[y0:y1,x0:x1].astype(float)
            blended = dst*(1-r)+np.array(color,dtype=float)*r
            brushed[y0:y1,x0:x1] = blended.astype(np.uint8)
            strokes_events.append({
                'tool': current_tool,
                'x': int(x), 'y': int(y),
                'size': float(val),
                'color': list(color)
            })
    brushed = cv2.medianBlur(brushed,5)
    if 0<=mouse_x<ROI_WIDTH and 0<=mouse_y<ROI_HEIGHT:
        d=dist_map[mouse_y,mouse_x]
        cv2.putText(disp, f"Distance:{d:.2f}@({mouse_x},{mouse_y})",
                    (10,30),cv2.FONT_HERSHEY_SIMPLEX,0.3,(255,255,0),1)
    show_image("Brushed Result Debug", brushed)
    show_image("Binary Mask Debug", bin_img)
    show_image("Distance Map Debug", disp)

def process_objects():
    global objects_events
    objects_events.clear()
    brushed = np.full((ROI_HEIGHT,ROI_WIDTH,3),255,dtype=np.uint8)
    for cl in clusters:
        if len(cl['points'])<10 or cl['avg_w']*cl['avg_h']>ROI_WIDTH*ROI_HEIGHT*0.5:
            continue
        name = cl['shape']; cx,cy = map(int,cl['centroid'])
        w_t,h_t = template_sizes[name]
        scale_x,scale_y = cl['avg_w']/w_t, cl['avg_h']/h_t
        sc = max(0.1,min(3.0,(scale_x+scale_y)/2*0.6))
        prev_sc,prev_ang = cl['sprite_params']
        if cl['sprite'] is None or abs(sc-prev_sc)>0.1 or abs(cl['avg_angle']-prev_ang)>5:
            base = overlays[name]
            h0,w0 = base.shape[:2]
            M = cv2.getRotationMatrix2D((w0/2,h0/2), cl['avg_angle'], sc)
            abs_c,abs_s = abs(M[0,0]),abs(M[0,1])
            nw = int(h0*abs_s + w0*abs_c)
            nh = int(h0*abs_c + w0*abs_s)
            M[0,2]+=(nw-w0)/2; M[1,2]+=(nh-h0)/2
            rot = cv2.warpAffine(base,M,(nw,nh),flags=cv2.INTER_AREA,
                                 borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
            a = rot[:,:,3]
            ys,xs = np.where(a>0)
            y0,y1 = ys.min(), ys.max(); x0,x1 = xs.min(), xs.max()
            cl['sprite'] = rot[y0:y1+1, x0:x1+1]
            cl['sprite_params'] = (sc, cl['avg_angle'])
        spr = cl['sprite']
        h,w = spr.shape[:2]
        x0,y0 = cx-w//2, cy-h//2
        ox,oy = max(0,-x0), max(0,-y0)
        x0_,y0_ = max(0,x0), max(0,y0)
        x1_,y1_ = min(brushed.shape[1],x0+w), min(brushed.shape[0],y0+h)
        roi = spr[oy:oy+(y1_-y0_), ox:ox+(x1_-x0_)]
        mask = roi[:,:,3]>0
        dst = brushed[y0_:y1_, x0_:x1_]
        dst[mask] = roi[mask][:,:3]
        objects_events.append({
            'tool': current_tool,
            'shape': name,
            'cx': cx, 'cy': cy,
            'w': float(cl['avg_w']), 'h': float(cl['avg_h']),
            'angle': float(cl['avg_angle']),
            'scale': float(sc)
        })

async def main():
    global frame_idx, current_tool, base_frame, frames, cropped_frames
    await client.connect_ws()
    print("WebSocket connecté.")
    client.start_listening()

    while True:
        frame_idx += 1
        if kinect.has_new_depth_frame():
            df = kinect.get_last_depth_frame().reshape((424,512)).astype(np.uint16)
            df = cv2.medianBlur(df,5)
            cf = crop_to_roi(df)
            cf = cv2.flip(cf,1)
            if base_frame is None:
                frames.append(cf)
                if len(frames)>=10:
                    base_frame = np.mean(frames,axis=0).astype(np.uint16)
                    print(f"Baseline calculée pour l'outil {current_tool}.")
            else:
                cropped_frames.append(cf)
                if len(cropped_frames)>10: cropped_frames.pop(0)
                mean_cf = np.mean(cropped_frames,axis=0).astype(np.uint16)
                process_depth_frame(mean_cf)

        render_final_drawings()
        process_brush_strokes()
        if current_tool=='4':
            process_objects()

        latest_payload = {
            "tool": current_tool,
            "strokes": strokes_events,
            "objects": objects_events
        }
        await client.set_buffer(latest_payload)

        key = cv2.waitKey(1)&0xFF
        if key==ord('q'): break
        if key in [ord('1'),ord('2'),ord('3'),ord('4')]:
            nt = chr(key)
            if nt!=current_tool:
                if base_frame is not None:
                    frames.clear()
                    cropped_frames.clear()
                base_frame = None
                current_tool = nt
                print(f"Outil changé : {current_tool}")
        if key==ord(' '):
            USE_MATCHSHAPES = not USE_MATCHSHAPES
            print(f"matchShapes : {USE_MATCHSHAPES}")

        await asyncio.sleep(0)

    kinect.close()
    cv2.destroyAllWindows()
    await client.close_ws()

if __name__ == "__main__":
    asyncio.run(main())