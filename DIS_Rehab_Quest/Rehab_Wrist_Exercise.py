import cv2
import mediapipe as mp
import numpy as np
import time
import math
import os
from collections import deque

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── MediaPipe ────────────────────────────────────────────────────
mp_pose = mp.solutions.pose
PL      = mp_pose.PoseLandmark

pose = mp_pose.Pose(
    static_image_mode       = False,
    model_complexity        = 1,
    smooth_landmarks        = True,
    min_detection_confidence= 0.6,
    min_tracking_confidence = 0.6
)

# ── Exponential smoothing on all 33 landmarks ────────────────────
SMOOTH_ALPHA = 0.35
smoothed_lm  = {}

def smooth_landmarks(raw):
    global smoothed_lm
    out = {}
    for i, lm in enumerate(raw.landmark):
        if i not in smoothed_lm:
            smoothed_lm[i] = [lm.x, lm.y, lm.z]
        else:
            sx, sy, sz = smoothed_lm[i]
            smoothed_lm[i] = [
                SMOOTH_ALPHA * lm.x + (1 - SMOOTH_ALPHA) * sx,
                SMOOTH_ALPHA * lm.y + (1 - SMOOTH_ALPHA) * sy,
                SMOOTH_ALPHA * lm.z + (1 - SMOOTH_ALPHA) * sz,
            ]
        out[i] = smoothed_lm[i]
    return out


SCREEN_RIGHT_WRIST    = PL.LEFT_WRIST.value
SCREEN_LEFT_WRIST     = PL.RIGHT_WRIST.value
SCREEN_RIGHT_SHOULDER = PL.LEFT_SHOULDER.value
SCREEN_LEFT_SHOULDER  = PL.RIGHT_SHOULDER.value
SCREEN_RIGHT_ELBOW    = PL.LEFT_ELBOW.value
SCREEN_LEFT_ELBOW     = PL.RIGHT_ELBOW.value
SCREEN_RIGHT_HIP      = PL.LEFT_HIP.value
SCREEN_LEFT_HIP       = PL.RIGHT_HIP.value
SCREEN_RIGHT_KNEE     = PL.LEFT_KNEE.value
SCREEN_LEFT_KNEE      = PL.RIGHT_KNEE.value
SCREEN_RIGHT_ANKLE    = PL.LEFT_ANKLE.value
SCREEN_LEFT_ANKLE     = PL.RIGHT_ANKLE.value
SCREEN_RIGHT_HEEL     = PL.LEFT_HEEL.value
SCREEN_LEFT_HEEL      = PL.RIGHT_HEEL.value
SCREEN_RIGHT_FOOT     = PL.LEFT_FOOT_INDEX.value
SCREEN_LEFT_FOOT      = PL.RIGHT_FOOT_INDEX.value

# ── Colour-coded skeleton ────────────────────────────────────────
SKELETON_SEGMENTS = [
    (SCREEN_LEFT_SHOULDER,  SCREEN_RIGHT_SHOULDER, (220,220,220), 3),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_HIP,       (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_LEFT_HIP,       SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_ELBOW,    (0,230,230),   4),
    (SCREEN_RIGHT_ELBOW,    SCREEN_RIGHT_WRIST,    (0,255,200),   4),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_ELBOW,     (0,200,200),   3),
    (SCREEN_LEFT_ELBOW,     SCREEN_LEFT_WRIST,     (0,220,180),   3),
    (SCREEN_RIGHT_HIP,   SCREEN_RIGHT_KNEE,  (0,140,255), 4),
    (SCREEN_RIGHT_KNEE,  SCREEN_RIGHT_ANKLE, (0,170,255), 4),
    (SCREEN_RIGHT_ANKLE, SCREEN_RIGHT_HEEL,  (0,190,255), 3),
    (SCREEN_RIGHT_HEEL,  SCREEN_RIGHT_FOOT,  (0,200,255), 3),
    (SCREEN_LEFT_HIP,   SCREEN_LEFT_KNEE,   (0,120,220), 3),
    (SCREEN_LEFT_KNEE,  SCREEN_LEFT_ANKLE,  (0,150,220), 3),
    (SCREEN_LEFT_ANKLE, SCREEN_LEFT_HEEL,   (0,170,220), 3),
    (SCREEN_LEFT_HEEL,  SCREEN_LEFT_FOOT,   (0,180,220), 3),
]

KEY_JOINTS = [
    (SCREEN_RIGHT_WRIST,    (0,255,200), 10),
    (SCREEN_LEFT_WRIST,     (0,220,180),  8),
    (SCREEN_RIGHT_ELBOW,    (0,230,230),  8),
    (SCREEN_LEFT_ELBOW,     (0,200,200),  7),
    (SCREEN_RIGHT_SHOULDER, (200,200,255), 9),
    (SCREEN_LEFT_SHOULDER,  (180,180,255), 8),
    (SCREEN_RIGHT_HIP,      (200,200,200), 8),
    (SCREEN_LEFT_HIP,       (200,200,200), 8),
    (SCREEN_RIGHT_KNEE,     (0,170,255),  8),
    (SCREEN_LEFT_KNEE,      (0,150,220),  7),
    (SCREEN_RIGHT_ANKLE,    (0,190,255),  8),
    (SCREEN_LEFT_ANKLE,     (0,170,220),  7),
]

def draw_skeleton(frame, lm_dict, W, H):
    for (a, b, color, thick) in SKELETON_SEGMENTS:
        if a not in lm_dict or b not in lm_dict: continue
        ax, ay = int(lm_dict[a][0]*W), int(lm_dict[a][1]*H)
        bx, by = int(lm_dict[b][0]*W), int(lm_dict[b][1]*H)
        if not (0<ax<W and 0<ay<H and 0<bx<W and 0<by<H): continue
        cv2.line(frame, (ax,ay), (bx,by), (0,0,0), thick+3, cv2.LINE_AA)
        cv2.line(frame, (ax,ay), (bx,by), color,   thick,   cv2.LINE_AA)
    for (jid, color, r) in KEY_JOINTS:
        if jid not in lm_dict: continue
        jx = int(lm_dict[jid][0]*W)
        jy = int(lm_dict[jid][1]*H)
        if not (0<jx<W and 0<jy<H): continue
        cv2.circle(frame, (jx,jy), r+2, (0,0,0),    -1, cv2.LINE_AA)
        cv2.circle(frame, (jx,jy), r,   color,       -1, cv2.LINE_AA)
        cv2.circle(frame, (jx,jy), r,   (255,255,255), 1, cv2.LINE_AA)

# ── Webcam ───────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS,          30)

demo_mp4 = os.path.join(BASE_DIR, 'Wrist.mp4')
demo_cap = cv2.VideoCapture(demo_mp4)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[INFO] Camera: {W}×{H}")

# ── Guide circle ──────────────────────────────────────────────────
GUIDE_R  = 90
GUIDE_CX = W // 2
GUIDE_CY = H // 2

# ── Wrist trail ───────────────────────────────────────────────────
TRAIL_LEN = 80
trail     = deque(maxlen=TRAIL_LEN)

def draw_wrist_trail(img, trail):
    pts = list(trail)
    for i in range(1, len(pts)):
        t = i / len(pts)
        col = (0, int(255*t), 200)
        cv2.line(img, pts[i-1], pts[i], col, int(2+t*3), cv2.LINE_AA)

# ── Floating particles ────────────────────────────────────────────
particles = []

def spawn_particle(x, y, text, color):
    particles.append({
        'x':x,'y':y,'vy':-2.5,'text':text,
        'color':color,'alpha':1.0,'birth':time.time()
    })

def update_draw_particles(frame, now):
    alive = []
    for p in particles:
        age = now - p['birth']
        if age > 1.5: continue
        p['y']    += p['vy']
        p['alpha'] = max(0, 1.0 - age/1.2)
        a   = p['alpha']
        col = tuple(int(c*a) for c in p['color'])
        cv2.putText(frame, p['text'], (int(p['x'])+2, int(p['y'])+2),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (0,0,0), 4, cv2.LINE_AA)
        cv2.putText(frame, p['text'], (int(p['x']), int(p['y'])),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, col, 2, cv2.LINE_AA)
        alive.append(p)
    particles[:] = alive

# ── HUD helpers ───────────────────────────────────────────────────
def rounded_rect(img, x1, y1, x2, y2, r, bgr, alpha=0.65):
    overlay = img.copy()
    cv2.rectangle(overlay,(x1+r,y1),(x2-r,y2),bgr,-1)
    cv2.rectangle(overlay,(x1,y1+r),(x2,y2-r),bgr,-1)
    for cx,cy in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
        cv2.circle(overlay,(cx,cy),r,bgr,-1)
    cv2.addWeighted(overlay,alpha,img,1-alpha,0,img)

def put_text(img, text, x, y, scale=0.8, color=(255,255,255), thickness=2):
    cv2.putText(img,text,(x+2,y+2),cv2.FONT_HERSHEY_DUPLEX,
                scale,(0,0,0),thickness+2,cv2.LINE_AA)
    cv2.putText(img,text,(x,y),cv2.FONT_HERSHEY_DUPLEX,
                scale,color,thickness,cv2.LINE_AA)

def text_center(img, text, cx, y, scale, color, thickness=2):
    (tw,_),_ = cv2.getTextSize(text,cv2.FONT_HERSHEY_DUPLEX,scale,thickness)
    put_text(img,text,cx-tw//2,y,scale,color,thickness)

# ── Animated guide ring ───────────────────────────────────────────
def draw_guide_ring(frame, cx, cy, radius, proximity, t):
    # Static background ring
    cv2.circle(frame, (cx,cy), radius, (40,40,70), 2, cv2.LINE_AA)
    # Rotating dashed ring
    color   = (0,255,80) if proximity > 0.7 else (0,200,255)
    dashes  = 12
    offset  = int(t * 40) % 30
    for i in range(dashes):
        a1 = (360//dashes*i + offset) % 360
        a2 = a1 + 14
        cv2.ellipse(frame,(cx,cy),(radius,radius),0,a1,a2,color,3,cv2.LINE_AA)
    # Proximity fill arc
    if proximity > 0.05:
        sweep = int(360 * proximity)
        cv2.ellipse(frame,(cx,cy),(radius+10,radius+10),
                    -90,0,sweep,(0,255,120),4,cv2.LINE_AA)

# ── Rotation progress arc (side panel) ───────────────────────────
def draw_rotation_arc(frame, cx, cy, radius, angle_sum, color=(0,200,255)):
    max_deg = 300
    cv2.circle(frame,(cx,cy),radius,(40,40,60),8)
    pct = min(1.0, abs(angle_sum)/max_deg)
    if pct > 0:
        sweep = int(360 * pct)
        arc_col = (0,255,80) if pct > 0.8 else color
        cv2.ellipse(frame,(cx,cy),(radius,radius),-90,0,sweep,arc_col,8,cv2.LINE_AA)

# ── Smooth feedback ───────────────────────────────────────────────
fb_text        = "Move your RIGHT wrist along the circle!"
fb_target_col  = np.array([255,255,200], dtype=float)
fb_current_col = np.array([255,255,200], dtype=float)

def set_feedback(text, color_bgr):
    global fb_text, fb_target_col
    fb_text       = text
    fb_target_col = np.array(color_bgr, dtype=float)

def update_feedback_color():
    global fb_current_col
    fb_current_col += (fb_target_col - fb_current_col) * 0.12

# ── Game state ────────────────────────────────────────────────────
score        = 0
reps         = 0
# "active_wrist" = what the user SEES (screen perspective)
# "RIGHT" → screen right → MP LEFT_WRIST
active_wrist = "RIGHT"

prev_angle  = None
angle_sum   = 0.0

def reset_circle():
    global trail, prev_angle, angle_sum
    trail.clear()
    prev_angle = None
    angle_sum  = 0.0

def get_active_landmark_id():
    """Return the correct MP landmark id for the currently active screen wrist."""
    if active_wrist == "RIGHT":
        return SCREEN_RIGHT_WRIST   # = PL.LEFT_WRIST.value
    else:
        return SCREEN_LEFT_WRIST    # = PL.RIGHT_WRIST.value

print("[INFO] Wrist Circle: Q=quit  R=reset  SPACE=toggle hand")


# ── Main loop ─────────────────────────────────────────────────────
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    now   = time.time()

    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)

    wrist_px  = None
    detected  = False
    lm_dict   = {}
    proximity = 0.0

    if results.pose_landmarks:
        detected = True
        lm_dict  = smooth_landmarks(results.pose_landmarks)

        draw_skeleton(frame, lm_dict, W, H)

        lid = get_active_landmark_id()
        rw  = lm_dict[lid]
        wrist_px = (int(rw[0]*W), int(rw[1]*H))
        trail.append(wrist_px)

        # Proximity to guide circle centre
        dist_to_centre = math.hypot(wrist_px[0]-GUIDE_CX, wrist_px[1]-GUIDE_CY)
        proximity = max(0.0, 1.0 - dist_to_centre / (GUIDE_R * 2.5))

        # Rotation angle tracking
        rel_x = wrist_px[0] - GUIDE_CX
        rel_y = wrist_px[1] - GUIDE_CY
        angle = (math.degrees(math.atan2(rel_y, rel_x)) + 90) % 360

        if prev_angle is not None:
            delta = angle - prev_angle
            if delta > 180: delta -= 360
            if delta < -180: delta += 360
            angle_sum += delta

        prev_angle = angle

        # Full rotation detected
        if abs(angle_sum) > 300:
            score += 20
            reps  += 1
            dir_label = "CW" if angle_sum > 0 else "CCW"
            spawn_particle(GUIDE_CX-40, GUIDE_CY-60,
                        f"{dir_label} +20  +Rep {reps}", (80,255,120))
            set_feedback(f"Full Circle! Rep {reps}  +20 pts", (80,255,120))
            angle_sum = 0.0
            trail.clear()  # fresh trail for next rep — cleaner look

        # Feedback when rotating
        elif abs(angle_sum) > 60:
            pct = min(100, int(abs(angle_sum)/300*100))
            set_feedback(f"Keep going! {pct}% complete", (100,220,255))
        else:
            set_feedback(f"Move your {active_wrist} wrist along the circle!", (255,255,200))

        # Active wrist highlight
        cv2.circle(frame, wrist_px, 18, (0,255,180), 2, cv2.LINE_AA)
        cv2.circle(frame, wrist_px, 10, (0,255,180), -1, cv2.LINE_AA)

        # Crosshair when wrist is on/near guide ring
        ring_dist = abs(dist_to_centre - GUIDE_R)
        if ring_dist < 30:
            cx2, cy2 = wrist_px
            cv2.line(frame,(cx2-20,cy2),(cx2+20,cy2),(0,255,80),2,cv2.LINE_AA)
            cv2.line(frame,(cx2,cy2-20),(cx2,cy2+20),(0,255,80),2,cv2.LINE_AA)
            cv2.circle(frame,wrist_px,22,(0,255,80),2,cv2.LINE_AA)

    if not detected:
        set_feedback("No person detected, step back so body is visible", (150,150,150))

    # ── Draw trail + guide ring ───────────────────────────────────
    draw_wrist_trail(frame, trail)
    draw_guide_ring(frame, GUIDE_CX, GUIDE_CY, GUIDE_R, proximity, now)

    # Guide crosshairs (subtle)
    cv2.line(frame,(GUIDE_CX,GUIDE_CY-GUIDE_R-15),
             (GUIDE_CX,GUIDE_CY+GUIDE_R+15),(40,40,70),1,cv2.LINE_AA)
    cv2.line(frame,(GUIDE_CX-GUIDE_R-15,GUIDE_CY),
             (GUIDE_CX+GUIDE_R+15,GUIDE_CY),(40,40,70),1,cv2.LINE_AA)

    # Floating particles
    update_draw_particles(frame, now)

    # Rotation progress arc (right side panel)
    draw_rotation_arc(frame, W-55, 160, 38, angle_sum)
    put_text(frame, "%" , W-68, 200, 0.45, (150,150,200), 1)

    # ── TOP HUD ──────────────────────────────────────────────────
    rounded_rect(frame, 0, 0, W, 72, 0, (12,12,18), alpha=0.72)
    cv2.line(frame,(0,72),(W,72),(0,180,180),1)

    put_text(frame, f"Score: {score}", 18, 48, 1.0, (80,255,130), 2)
    put_text(frame, f"Reps: {reps}",  200, 48, 0.9, (200,210,80), 2)

    text_center(frame, "Exercise: Wrist 360 deg Circle", W//2, 46, 0.65, (180,210,255), 1)

    wrist_tag = f"Wrist: {active_wrist}  [SPACE]"
    (ww,_),_ = cv2.getTextSize(wrist_tag, cv2.FONT_HERSHEY_DUPLEX, 0.65, 1)
    put_text(frame, wrist_tag, W-ww-18, 48, 0.65, (120,200,255), 1)

    # ── BOTTOM HUD ───────────────────────────────────────────────
    update_feedback_color()
    rounded_rect(frame, 0, H-72, W, H, 0, (12,12,18), alpha=0.72)
    cv2.line(frame,(0,H-72),(W,H-72),(0,180,180),1)
    col = tuple(int(c) for c in fb_current_col)
    text_center(frame, fb_text, W//2, H-22, 0.88, col, 2)

    # Controls hint (bottom left corner)
    rounded_rect(frame, 0, H-72-90, 230, H-72, 6, (8,8,18), alpha=0.55)
    for i, line in enumerate(["Q=Quit", "R=Reset circle", "SPACE=Toggle hand"]):
        put_text(frame, line, 10, H-72-70+i*22, 0.45, (140,150,200), 1)

    # ── PIP DEMO VIDEO ───────────────────────────────────────────
    if demo_cap.isOpened():
        ret_demo, demo_frame = demo_cap.read()
        if not ret_demo:
            demo_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret_demo, demo_frame = demo_cap.read()
        if ret_demo:
            try:
                demo_frame = cv2.resize(demo_frame, (240, 135))
                dx, dy = 10, 80
                frame[dy:dy+135, dx:dx+240] = demo_frame
                cv2.rectangle(frame, (dx-2, dy-18), (dx+240+2, dy+135+2), (0, 210, 210), 2)
                cv2.rectangle(frame, (dx-2, dy-18), (dx+240+2, dy), (0, 210, 210), -1)
                cv2.putText(frame, "DEMO: Wrist Circle", (dx+2, dy-5), cv2.FONT_HERSHEY_DUPLEX, 0.45, (0,0,0), 1)
            except Exception as e:
                pass

    cv2.imshow("Rehab Quest: Wrist Circle", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        reset_circle()
    elif key == ord(' '):
        active_wrist = "LEFT" if active_wrist == "RIGHT" else "RIGHT"
        reset_circle()
        set_feedback(f"Switched to {active_wrist} wrist to make a circle!", (200,200,255))

cap.release()
cv2.destroyAllWindows()
print(f"[DONE] Wrist Circle Score: {score}    Reps: {reps}")
