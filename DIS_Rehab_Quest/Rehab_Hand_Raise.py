import cv2
import mediapipe as mp
import numpy as np
import time
import os
import socket, struct, math, collections

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════════
#  MEDIAPIPE SETUP
# ══════════════════════════════════════════════════════════════════
mp_pose = mp.solutions.pose
pose    = mp_pose.Pose(
    model_complexity         = 1,
    min_detection_confidence = 0.6,
    min_tracking_confidence  = 0.6,
    smooth_landmarks         = True,
)
PL = mp_pose.PoseLandmark

# ══════════════════════════════════════════════════════════════════
#  WEBCAM
# ══════════════════════════════════════════════════════════════════
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS,          30)

demo_mp4 = os.path.join(BASE_DIR, 'Hand_Raise.mp4')
demo_cap = cv2.VideoCapture(demo_mp4)

W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[INFO] Webcam: {W}×{H}")

# ══════════════════════════════════════════════════════════════════
#  UDP → UNITY
# ══════════════════════════════════════════════════════════════════
UNITY_IP   = "127.0.0.1"
FRAME_PORT = 5006
sock       = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)

# ══════════════════════════════════════════════════════════════════
#  SMOOTHING — exponential moving average on all 33 landmarks
# ══════════════════════════════════════════════════════════════════
SMOOTH_ALPHA = 0.35
smoothed_lm  = {}

def smooth_landmarks(raw_landmarks):
    global smoothed_lm
    out = {}
    for i, lm in enumerate(raw_landmarks.landmark):
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

# ══════════════════════════════════════════════════════════════════
#  MIRROR-AWARE LANDMARK HELPERS
#
#  Because we flip the frame horizontally, what the user sees as
#  their "right hand" is MediaPipe's LEFT_WRIST (and vice-versa).
#  Use these helpers everywhere instead of PL.RIGHT_WRIST / LEFT_WRIST.
# ══════════════════════════════════════════════════════════════════
# "Screen right" = user's right in the mirror = MP's LEFT landmark
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

# ══════════════════════════════════════════════════════════════════
#  SKELETON — colour-coded, mirror-corrected
# ══════════════════════════════════════════════════════════════════
# Each entry: (landmark_a_value, landmark_b_value, BGR_color, thickness)
SKELETON_SEGMENTS = [
    # Torso
    (SCREEN_LEFT_SHOULDER,  SCREEN_RIGHT_SHOULDER, (220,220,220), 3),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_HIP,       (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_LEFT_HIP,       SCREEN_RIGHT_HIP,      (220,220,220), 3),

    # Screen-right arm (cyan, brighter)
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_ELBOW,    (0,230,230),   4),
    (SCREEN_RIGHT_ELBOW,    SCREEN_RIGHT_WRIST,    (0,255,200),   4),

    # Screen-left arm (lighter cyan)
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_ELBOW,     (0,200,200),   3),
    (SCREEN_LEFT_ELBOW,     SCREEN_LEFT_WRIST,     (0,220,180),   3),

    # Screen-right leg (orange-blue)
    (SCREEN_RIGHT_HIP,   SCREEN_RIGHT_KNEE,  (0,140,255), 4),
    (SCREEN_RIGHT_KNEE,  SCREEN_RIGHT_ANKLE, (0,170,255), 4),
    (SCREEN_RIGHT_ANKLE, SCREEN_RIGHT_HEEL,  (0,190,255), 3),
    (SCREEN_RIGHT_HEEL,  SCREEN_RIGHT_FOOT,  (0,200,255), 3),

    # Screen-left leg (lighter)
    (SCREEN_LEFT_HIP,   SCREEN_LEFT_KNEE,  (0,120,220), 3),
    (SCREEN_LEFT_KNEE,  SCREEN_LEFT_ANKLE, (0,150,220), 3),
    (SCREEN_LEFT_ANKLE, SCREEN_LEFT_HEEL,  (0,170,220), 3),
    (SCREEN_LEFT_HEEL,  SCREEN_LEFT_FOOT,  (0,180,220), 3),
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

def draw_skeleton(frame, lm_dict):
    for (a, b, color, thick) in SKELETON_SEGMENTS:
        if a not in lm_dict or b not in lm_dict: continue
        ax, ay = int(lm_dict[a][0]*W), int(lm_dict[a][1]*H)
        bx, by = int(lm_dict[b][0]*W), int(lm_dict[b][1]*H)
        if not (0<ax<W and 0<ay<H and 0<bx<W and 0<by<H): continue
        cv2.line(frame, (ax,ay), (bx,by), (0,0,0),    thick+3, cv2.LINE_AA)
        cv2.line(frame, (ax,ay), (bx,by), color,       thick,   cv2.LINE_AA)
    for (jid, color, r) in KEY_JOINTS:
        if jid not in lm_dict: continue
        jx = int(lm_dict[jid][0]*W)
        jy = int(lm_dict[jid][1]*H)
        if not (0<jx<W and 0<jy<H): continue
        cv2.circle(frame, (jx,jy), r+2, (0,0,0),    -1, cv2.LINE_AA)
        cv2.circle(frame, (jx,jy), r,   color,       -1, cv2.LINE_AA)
        cv2.circle(frame, (jx,jy), r,   (255,255,255), 1, cv2.LINE_AA)

# ══════════════════════════════════════════════════════════════════
#  WRIST TRAIL
# ══════════════════════════════════════════════════════════════════
TRAIL_LEN   = 20
wrist_trail = collections.deque(maxlen=TRAIL_LEN)

def draw_wrist_trail(frame):
    pts = list(wrist_trail)
    for i in range(1, len(pts)):
        alpha  = i / len(pts)
        radius = max(2, int(alpha * 8))
        color  = (int(alpha*0), int(alpha*255), int(alpha*200))
        cv2.circle(frame, pts[i], radius, (0,0,0), -1, cv2.LINE_AA)
        cv2.circle(frame, pts[i], radius, color,   -1, cv2.LINE_AA)
        if i > 1:
            t2 = (i-1)/len(pts)
            c2 = (0, int(t2*255), int(t2*200))
            cv2.line(frame, pts[i-1], pts[i], c2, radius, cv2.LINE_AA)

# ══════════════════════════════════════════════════════════════════
#  APPLE
# ══════════════════════════════════════════════════════════════════
APPLE_RADIUS = 42
APPLE_CX     = W // 2
APPLE_CY     = int(H * 0.20)
PICK_DIST    = 85

apple_img = None
try:
    raw = cv2.imread("apple.png", cv2.IMREAD_UNCHANGED)
    if raw is not None:
        sz        = APPLE_RADIUS * 2
        apple_img = cv2.resize(raw, (sz, sz))
        print("[INFO] apple.png loaded")
except Exception:
    pass

def draw_apple_sprite(frame, cx, cy, scale=1.0):
    r = int(APPLE_RADIUS * scale)
    if apple_img is not None:
        half = r
        x1, y1 = cx-half, cy-half
        x2, y2 = cx+half, cy+half
        if x1<0 or y1<0 or x2>W or y2>H: return
        resized = cv2.resize(apple_img,(r*2,r*2)) if scale!=1.0 else apple_img
        roi = frame[y1:y2, x1:x2]
        if resized.shape[2] == 4:
            a = resized[:,:,3]/255.0
            for c in range(3):
                roi[:,:,c] = (a*resized[:,:,c]+(1-a)*roi[:,:,c]).astype(np.uint8)
        else:
            frame[y1:y2,x1:x2] = resized
    else:
        cv2.circle(frame,(cx,cy), r,   (20, 20,200),-1, cv2.LINE_AA)
        cv2.circle(frame,(cx,cy), r,   (0,  0, 120), 2, cv2.LINE_AA)
        hx, hy = int(cx-r*0.28), int(cy-r*0.28)
        cv2.ellipse(frame,(hx,hy),(int(r*0.35),int(r*0.2)),
                    -30,0,360,(180,180,255),-1,cv2.LINE_AA)
        cv2.line(frame,(cx,cy-r),(cx+7,cy-r-15),(0,100,0),3,cv2.LINE_AA)
        cv2.ellipse(frame,(cx+12,cy-r-14),(7,4),
                    20,0,200,(0,150,0),-1,cv2.LINE_AA)

def draw_apple_ring(frame, cx, cy, proximity, t):
    r     = APPLE_RADIUS + 22
    color = (0,255,80) if proximity > 0.7 else (0,200,255)
    dashes  = 12
    offset  = int(t * 40) % 30
    for i in range(dashes):
        a1 = (360//dashes*i + offset) % 360
        a2 = a1 + 14
        cv2.ellipse(frame,(cx,cy),(r,r),0,a1,a2,color,3,cv2.LINE_AA)
    if proximity > 0.05:
        sweep = int(360 * proximity)
        cv2.ellipse(frame,(cx,cy),(r+8,r+8),-90,0,sweep,(0,255,120),4,cv2.LINE_AA)

# ══════════════════════════════════════════════════════════════════
#  FLOATING SCORE PARTICLES
# ══════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════
#  HUD HELPERS
# ══════════════════════════════════════════════════════════════════
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

def send_frame(img):
    _, buf  = cv2.imencode(".jpg",img,[cv2.IMWRITE_JPEG_QUALITY,75])
    data    = buf.tobytes()
    header  = struct.pack(">I",len(data))
    try: sock.sendto(header+data,(UNITY_IP,FRAME_PORT))
    except Exception: pass

# ══════════════════════════════════════════════════════════════════
#  SMOOTH FEEDBACK
# ══════════════════════════════════════════════════════════════════
fb_text        = "Raise your RIGHT hand to grab the apple!"
fb_target_col  = np.array([255,255,255], dtype=float)
fb_current_col = np.array([255,255,255], dtype=float)

def set_feedback(text, color_bgr):
    global fb_text, fb_target_col
    fb_text       = text
    fb_target_col = np.array(color_bgr, dtype=float)

def update_feedback_color():
    global fb_current_col
    fb_current_col += (fb_target_col - fb_current_col) * 0.12

# ══════════════════════════════════════════════════════════════════
#  GAME STATE
# ══════════════════════════════════════════════════════════════════
score         = 0
combo         = 0
apple_visible = True
respawn_at    = 0.0
RESPAWN_DELAY = 2.0

pick_burst_at = -99.0
BURST_DURATION = 0.4

last_send  = 0.0
last_write = 0.0

print("[INFO] Rehab_Hand Raise running :press Q to quit")

# ══════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)   # mirror so user sees themselves naturally
    now   = time.time()

    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)

    state     = 0
    wrist_pos = None
    hand_near = False
    proximity = 0.0
    detected  = False
    lm_dict   = {}

    if results.pose_landmarks:
        detected = True
        lm_dict  = smooth_landmarks(results.pose_landmarks)

        # ── MIRROR FIX: use LEFT_WRIST landmark for the screen-right hand ──
        # After cv2.flip, the user's right hand appears on the right of the
        # screen, but MediaPipe labeled it LEFT_WRIST before the flip.
        rw = lm_dict[SCREEN_RIGHT_WRIST]    # screen right = MP LEFT
        rs = lm_dict[SCREEN_RIGHT_SHOULDER] # screen right shoulder

        wrist_pos = (int(rw[0]*W), int(rw[1]*H))
        wrist_trail.append(wrist_pos)

        # Hand is "up" when wrist is above shoulder (smaller y = higher)
        state = 1 if rw[1] < rs[1] else 0

        dist      = math.hypot(wrist_pos[0]-APPLE_CX, wrist_pos[1]-APPLE_CY)
        max_dist  = 250
        proximity = max(0.0, 1.0 - dist/max_dist)
        hand_near = dist < PICK_DIST

    # ── GAME LOGIC ────────────────────────────────────────────────
    if not apple_visible:
        if now >= respawn_at:
            apple_visible = True
            combo         = 0
            set_feedback("New apple! Raise your hands!", (200,255,200))
    else:
        if state == 1 and hand_near:
            apple_visible = False
            respawn_at    = now + RESPAWN_DELAY
            combo        += 1
            pts           = 10 * combo
            score        += pts
            pick_burst_at = now
            label = f"+{pts}!" if combo == 1 else f"+{pts}  x{combo} COMBO!"
            spawn_particle(APPLE_CX-60, APPLE_CY-60, label, (80,255,80))
            set_feedback(
                f"Amazing! +{pts} points!" + (" COMBO!" if combo > 1 else ""),
                (80,255,80)
            )
        elif state == 1 and not hand_near:
            set_feedback("Almost there! Reach toward the apple!", (100,220,255))
        else:
            set_feedback("Raise your hands higher!", (80,100,255))

    if now - last_write > 0.1:
        try:
            with open("output.txt","w") as f: f.write(str(state))
        except Exception: pass
        last_write = now

    # ── DRAW ─────────────────────────────────────────────────────
    if detected:
        draw_wrist_trail(frame)
    if detected and lm_dict:
        draw_skeleton(frame, lm_dict)

    burst_progress = min(1.0,(now-pick_burst_at)/BURST_DURATION)

    if apple_visible:
        draw_apple_ring(frame, APPLE_CX, APPLE_CY, proximity, now)
        draw_apple_sprite(frame, APPLE_CX, APPLE_CY)
    else:
        if burst_progress < 1.0:
            r   = int(APPLE_RADIUS * (1 + burst_progress*3))
            overlay2 = frame.copy()
            cv2.circle(overlay2,(APPLE_CX,APPLE_CY),r,(80,255,80),-1,cv2.LINE_AA)
            cv2.addWeighted(overlay2,(1-burst_progress)*0.5,
                            frame,   1-(1-burst_progress)*0.5, 0, frame)
        secs = max(0, respawn_at - now)
        cv2.circle(frame,(APPLE_CX,APPLE_CY),APPLE_RADIUS+10,(80,80,80),2,cv2.LINE_AA)
        text_center(frame,f"{secs:.1f}s",APPLE_CX,APPLE_CY+8,0.7,(180,180,180),1)

    update_draw_particles(frame, now)

    # ── HUD ───────────────────────────────────────────────────────
    rounded_rect(frame, 0, 0, W, 72, 0, (12,12,18), alpha=0.72)
    cv2.line(frame,(0,72),(W,72),(0,180,180),1)

    put_text(frame, f"Score: {score}", 18, 48, 1.0, (80,255,130), 2)

    if combo > 1:
        rounded_rect(frame,140,8,290,60,8,(0,80,0),alpha=0.8)
        put_text(frame, f"x{combo} COMBO", 148, 44, 0.75, (80,255,80), 2)

    text_center(frame, "Exercise: Raise Hands to Pick Apple", W//2, 46, 0.6, (180,210,255), 1)

    if not detected:
        stxt, scol = "No person detected", (130,130,130)
    elif state == 1:
        stxt, scol = "Hand UP!", (80,255,80)
    else:
        stxt, scol = "Hand DOWN!", (80,100,255)
    (tw,_),_ = cv2.getTextSize(stxt,cv2.FONT_HERSHEY_DUPLEX,0.85,2)
    put_text(frame, stxt, W-tw-18, 48, 0.85, scol, 2)

    if detected and apple_visible:
        bx, by, bh = W-28, 90, 200
        rounded_rect(frame,bx-4,by-4,bx+18,by+bh+4,4,(20,20,20),alpha=0.7)
        fill_h = int(bh * proximity)
        if fill_h > 0:
            bar_col = (0,255,80) if proximity > 0.7 else (0,200,255)
            cv2.rectangle(frame,(bx,by+bh-fill_h),(bx+14,by+bh),bar_col,-1)
        cv2.rectangle(frame,(bx,by),(bx+14,by+bh),(80,80,80),1)
        text_center(frame,"▲",bx+7,by-10,0.4,(150,150,150),1)

    update_feedback_color()
    rounded_rect(frame, 0, H-72, W, H, 0, (12,12,18), alpha=0.72)
    cv2.line(frame,(0,H-72),(W,H-72),(0,180,180),1)
    col = tuple(int(c) for c in fb_current_col)
    text_center(frame, fb_text, W//2, H-22, 0.88, col, 2)

    if wrist_pos and hand_near and apple_visible:
        cx, cy = wrist_pos
        cv2.line(frame,(cx-20,cy),(cx+20,cy),(0,255,80),2,cv2.LINE_AA)
        cv2.line(frame,(cx,cy-20),(cx,cy+20),(0,255,80),2,cv2.LINE_AA)
        cv2.circle(frame,wrist_pos,22,(0,255,80),2,cv2.LINE_AA)

    # ── SEND TO UNITY ─────────────────────────────────────────────
    if now - last_send >= 1/30:
        send_frame(frame)
        last_send = now

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
                cv2.putText(frame, "DEMO: Hand Raise", (dx+2, dy-5), cv2.FONT_HERSHEY_DUPLEX, 0.45, (0,0,0), 1)
            except Exception as e:
                pass

    preview = cv2.resize(frame,(640,360))
    cv2.imshow("Rehab: Hand Raise", preview)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
sock.close()
print(f"[INFO] Session ended. Final score: {score}")
