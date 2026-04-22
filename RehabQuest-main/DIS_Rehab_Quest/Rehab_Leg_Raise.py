import cv2
import mediapipe as mp
import numpy as np
import time
import math
import os

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

# ── Webcam ───────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS,          30)

demo_mp4 = os.path.join(BASE_DIR, 'Leg_Raise.mp4')
demo_cap = cv2.VideoCapture(demo_mp4)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[INFO] Camera: {W}×{H}")

# ── Exponential smoothing on all 33 landmarks ────────────────────
SMOOTH_ALPHA = 0.30
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

# ── MIRROR-AWARE LANDMARK IDs ─────────────────────────────────────
# cv2.flip() mirrors the image. After flipping, the user's right side
# appears on the right of screen. MediaPipe processes the flipped frame
# so "screen right" = MP LEFT landmark.
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

# ── Colour-coded skeleton ─────────────────────────────────────────
SKELETON_SEGMENTS = [
    (SCREEN_LEFT_SHOULDER,  SCREEN_RIGHT_SHOULDER, (220,220,220), 3),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_HIP,       (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_LEFT_HIP,       SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_ELBOW,    (0,230,230),   3),
    (SCREEN_RIGHT_ELBOW,    SCREEN_RIGHT_WRIST,    (0,255,200),   3),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_ELBOW,     (0,200,200),   3),
    (SCREEN_LEFT_ELBOW,     SCREEN_LEFT_WRIST,     (0,220,180),   3),
    (SCREEN_RIGHT_HIP,   SCREEN_RIGHT_KNEE,  (0,140,255), 5),
    (SCREEN_RIGHT_KNEE,  SCREEN_RIGHT_ANKLE, (0,170,255), 5),
    (SCREEN_RIGHT_ANKLE, SCREEN_RIGHT_HEEL,  (0,190,255), 3),
    (SCREEN_RIGHT_HEEL,  SCREEN_RIGHT_FOOT,  (0,200,255), 3),
    (SCREEN_LEFT_HIP,   SCREEN_LEFT_KNEE,   (0,120,220), 4),
    (SCREEN_LEFT_KNEE,  SCREEN_LEFT_ANKLE,  (0,150,220), 4),
    (SCREEN_LEFT_ANKLE, SCREEN_LEFT_HEEL,   (0,170,220), 3),
    (SCREEN_LEFT_HEEL,  SCREEN_LEFT_FOOT,   (0,180,220), 3),
]

KEY_JOINTS = [
    (SCREEN_RIGHT_WRIST,    (0,255,200),  7),
    (SCREEN_LEFT_WRIST,     (0,220,180),  7),
    (SCREEN_RIGHT_SHOULDER, (200,200,255), 9),
    (SCREEN_LEFT_SHOULDER,  (180,180,255), 8),
    (SCREEN_RIGHT_HIP,      (200,200,200), 9),
    (SCREEN_LEFT_HIP,       (200,200,200), 9),
    (SCREEN_RIGHT_KNEE,     (0,255,160),  12),   # large — key joint
    (SCREEN_LEFT_KNEE,      (0,200,255),  11),
    (SCREEN_RIGHT_ANKLE,    (0,190,255),   8),
    (SCREEN_LEFT_ANKLE,     (0,170,220),   8),
]

def draw_skeleton(frame, lm_dict):
    for (a, b, color, thick) in SKELETON_SEGMENTS:
        if a not in lm_dict or b not in lm_dict: continue
        ax, ay = int(lm_dict[a][0]*W), int(lm_dict[a][1]*H)
        bx, by = int(lm_dict[b][0]*W), int(lm_dict[b][1]*H)
        if not (0<ax<W and 0<ay<H and 0<bx<W and 0<by<H): continue
        cv2.line(frame,(ax,ay),(bx,by),(0,0,0),    thick+3, cv2.LINE_AA)
        cv2.line(frame,(ax,ay),(bx,by), color,      thick,   cv2.LINE_AA)
    for (jid, color, r) in KEY_JOINTS:
        if jid not in lm_dict: continue
        jx = int(lm_dict[jid][0]*W)
        jy = int(lm_dict[jid][1]*H)
        if not (0<jx<W and 0<jy<H): continue
        cv2.circle(frame,(jx,jy), r+2, (0,0,0),    -1, cv2.LINE_AA)
        cv2.circle(frame,(jx,jy), r,   color,       -1, cv2.LINE_AA)
        cv2.circle(frame,(jx,jy), r,   (255,255,255), 1, cv2.LINE_AA)

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

# ── Animated target line ──────────────────────────────────────────
def draw_target_line(img, y, color, label, active=False, flashing=False):
    now = time.time()
    if flashing:
        alpha = 0.5 + 0.5 * math.sin(now * 14)
        color = tuple(int(c * alpha) for c in color)

    # Glow line (wide, semi-transparent)
    if active:
        overlay = img.copy()
        cv2.line(overlay,(0,y),(W,y),color,12,cv2.LINE_AA)
        cv2.addWeighted(overlay,0.25,img,0.75,0,img)

    # Dashed foreground line
    dash, gap, x = 22, 10, 0
    while x < W:
        cv2.line(img,(x,y),(min(x+dash,W),y),color,3,cv2.LINE_AA)
        x += dash + gap

    # Label badge
    bw, bh = 190, 32
    rounded_rect(img, 8, y-bh//2-3, 8+bw, y+bh//2+3, 6, (10,10,22), alpha=0.75)
    put_text(img, label, 16, y+9, 0.55, color, 1)

# ── Per-leg progress arc ──────────────────────────────────────────
def draw_leg_arc(frame, cx, cy, radius, pct, color, label):
    cv2.circle(frame,(cx,cy),radius,(30,30,50),8)
    if pct > 0:
        sweep = int(360 * min(pct, 1.0))
        arc_col = (0,255,80) if pct >= 0.95 else color
        cv2.ellipse(frame,(cx,cy),(radius,radius),-90,0,sweep,arc_col,8,cv2.LINE_AA)
    put_text(frame, label, cx-9, cy+8, 0.65, color, 2)

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

# ── Smooth feedback ───────────────────────────────────────────────
fb_text        = "Stand straight: calibrating..."
fb_target_col  = np.array([255,255,150], dtype=float)
fb_current_col = np.array([255,255,150], dtype=float)

def set_feedback(text, color_bgr):
    global fb_text, fb_target_col
    fb_text       = text
    fb_target_col = np.array(color_bgr, dtype=float)

def update_feedback_color():
    global fb_current_col
    fb_current_col += (fb_target_col - fb_current_col) * 0.12

# ── Calibration ───────────────────────────────────────────────────
CAL_NEEDED  = 50
cal_frame   = 0
cal_buf     = {"rhip":[], "lhip":[], "rankle":[], "lankle":[]}
calibrated  = False
calibrating = True

hip_y   = {"R": H*0.45, "L": H*0.45}
ankle_y = {"R": H*0.85, "L": H*0.85}

TARGET_OFFSET_FRAC = 0.18

def get_target_y(side):
    leg = abs(ankle_y[side] - hip_y[side])
    return int(hip_y[side] + leg * TARGET_OFFSET_FRAC)

def reset_cal():
    global cal_frame, cal_buf, calibrated, calibrating, smoothed_lm
    cal_frame   = 0
    cal_buf     = {"rhip":[], "lhip":[], "rankle":[], "lankle":[]}
    calibrated  = False
    calibrating = True
    smoothed_lm = {}

# ── Game state ────────────────────────────────────────────────────
score       = 0
reps_r      = 0
reps_l      = 0
combo       = 0
mode        = "ALTERNATE"   # ALTERNATE / R / L
active_side = "R"

LEG_DOWN  = "DOWN"
LEG_UP    = "UP"
leg_state  = {"R": LEG_DOWN, "L": LEG_DOWN}

HOLD_NEEDED  = 10
hold_count   = {"R": 0, "L": 0}

smooth_knee  = {"R": None, "L": None}
KNEE_ALPHA   = 0.25

target_flash_end = 0.0
feedback_until   = 0.0

# Success burst animation
burst_side = None
burst_at   = -99.0
BURST_DUR  = 0.5

print("[INFO] Leg Raise Q=Quit  R=Recalibrate  A=Alternate  L=Left  K=Right")


# ── MAIN LOOP ─────────────────────────────────────────────────────
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    now   = time.time()

    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)

    detected = False
    lm_dict  = {}

    if results.pose_landmarks:
        detected = True
        lm_dict  = smooth_landmarks(results.pose_landmarks)

        # Draw skeleton
        draw_skeleton(frame, lm_dict)

        # Read screen-corrected landmarks (pixel coords)
        def lm_px(lid):
            v = lm_dict[lid]
            return (int(v[0]*W), int(v[1]*H)), float(v[1]*H)

        rhip_px,  rhip_y_raw  = lm_px(SCREEN_RIGHT_HIP)
        lhip_px,  lhip_y_raw  = lm_px(SCREEN_LEFT_HIP)
        rknee_px, rknee_y_raw = lm_px(SCREEN_RIGHT_KNEE)
        lknee_px, lknee_y_raw = lm_px(SCREEN_LEFT_KNEE)
        rankle_px,rankle_y_raw= lm_px(SCREEN_RIGHT_ANKLE)
        lankle_px,lankle_y_raw= lm_px(SCREEN_LEFT_ANKLE)

        # ── Calibration ──────────────────────────────────────────
        if calibrating:
            cal_frame += 1
            cal_buf["rhip"].append(rhip_y_raw)
            cal_buf["lhip"].append(lhip_y_raw)
            cal_buf["rankle"].append(rankle_y_raw)
            cal_buf["lankle"].append(lankle_y_raw)

            pct   = cal_frame / CAL_NEEDED
            bar_x = (W - 360) // 2
            bar_y = H // 2 + 10

            rounded_rect(frame, bar_x-24, bar_y-60, bar_x+384, bar_y+54, 10, (10,10,25), 0.82)
            cv2.line(frame,(bar_x-24,bar_y-60),(bar_x+384,bar_y-60),(0,180,180),2)
            text_center(frame,"Calibrating: stand straight, feet on floor",
                        W//2, bar_y-28, 0.7, (200,230,255), 1)
            # Progress bar
            cv2.rectangle(frame,(bar_x,bar_y+5),(bar_x+360,bar_y+28),(30,30,50),-1)
            cv2.rectangle(frame,(bar_x,bar_y+5),(bar_x+int(360*pct),bar_y+28),(0,200,255),-1)
            cv2.rectangle(frame,(bar_x,bar_y+5),(bar_x+360,bar_y+28),(60,80,120),2)
            text_center(frame,f"{int(pct*100)}%",W//2,bar_y+22,0.5,(180,220,255),1)

            if cal_frame >= CAL_NEEDED:
                hip_y["R"]   = float(np.mean(cal_buf["rhip"]))
                hip_y["L"]   = float(np.mean(cal_buf["lhip"]))
                ankle_y["R"] = float(np.mean(cal_buf["rankle"]))
                ankle_y["L"] = float(np.mean(cal_buf["lankle"]))
                calibrated   = True
                calibrating  = False
                smooth_knee  = {"R": None, "L": None}
                print(f"[CAL] hip_R={hip_y['R']:.0f}  hip_L={hip_y['L']:.0f}")
                set_feedback("Ready! Raise your RIGHT knee to the line!", (80,255,120))
                feedback_until = now + 3.0

        # ── Additional knee smoothing ────────────────────────────
        for side, kraw in [("R", rknee_y_raw), ("L", lknee_y_raw)]:
            if smooth_knee[side] is None:
                smooth_knee[side] = kraw
            else:
                smooth_knee[side] = KNEE_ALPHA*kraw + (1-KNEE_ALPHA)*smooth_knee[side]

        # ── Target lines ─────────────────────────────────────────
        if calibrated:
            flashing = now < target_flash_end

            if mode in ("ALTERNATE", "R"):
                tr      = get_target_y("R")
                act_r   = (mode=="R" or (mode=="ALTERNATE" and active_side=="R"))
                col_r   = (0,255,180) if act_r else (40,70,60)
                draw_target_line(frame, tr, col_r,
                                 "TARGET: Right Knee", act_r, flashing and act_r)

            if mode in ("ALTERNATE", "L"):
                tl      = get_target_y("L")
                act_l   = (mode=="L" or (mode=="ALTERNATE" and active_side=="L"))
                col_l   = (0,180,255) if act_l else (40,60,80)
                draw_target_line(frame, tl, col_l,
                                 "TARGET: Left Knee", act_l, flashing and act_l)

        # ── Per-leg progress arcs ─────────────────────────────────
        if calibrated:
            for side, hip, ankle, knee_sm_val, cx_arc, arc_label in [
                ("R", hip_y["R"], ankle_y["R"],
                 smooth_knee["R"] if smooth_knee["R"] else rknee_y_raw,
                 W-65, "R"),
                ("L", hip_y["L"], ankle_y["L"],
                 smooth_knee["L"] if smooth_knee["L"] else lknee_y_raw,
                 W-155, "L"),
            ]:
                process = (mode == side or
                           (mode == "ALTERNATE" and active_side == side))
                if not process: continue
                tgt_y   = get_target_y(side)
                denom   = max(1, hip - tgt_y)
                pct     = max(0, min(1.0, (hip - knee_sm_val) / denom))
                arc_col = (0,255,120) if pct >= 0.95 else (0,200,255)
                draw_leg_arc(frame, cx_arc, 155, 38, pct, arc_col, arc_label)

        # ── Burst animation on successful rep ────────────────────
        if burst_side is not None:
            prog = min(1.0, (now - burst_at) / BURST_DUR)
            if prog < 1.0:
                # Use the knee position for the burst origin
                kpx = rknee_px if burst_side == "R" else lknee_px
                r2  = int(20 + prog * 60)
                alp = 1.0 - prog
                ov  = frame.copy()
                cv2.circle(ov, kpx, r2, (80,255,80), -1, cv2.LINE_AA)
                cv2.addWeighted(ov, alp*0.35, frame, 1-alp*0.35, 0, frame)
            else:
                burst_side = None

        # ── Game logic ────────────────────────────────────────────
        if calibrated:
            for side in ["R", "L"]:
                process = (mode == side or
                           (mode == "ALTERNATE" and active_side == side))
                if not process: continue

                tgt_y   = get_target_y(side)
                knee_sm = (smooth_knee[side]
                           if smooth_knee[side] is not None
                           else (rknee_y_raw if side=="R" else lknee_y_raw))

                above = knee_sm <= tgt_y   # smaller y = higher on screen

                if leg_state[side] == LEG_DOWN:
                    if above:
                        hold_count[side] += 1
                        if hold_count[side] >= HOLD_NEEDED:
                            leg_state[side]   = LEG_UP
                            combo            += 1
                            pts               = 10 * combo
                            score            += pts
                            target_flash_end  = now + 0.8
                            burst_side        = side
                            burst_at          = now

                            side_name = "Right" if side == "R" else "Left"
                            kpx = rknee_px if side == "R" else lknee_px
                            label = f"+{pts}!" if combo == 1 else f"+{pts} x{combo}!"
                            spawn_particle(kpx[0]-30, kpx[1]-50, label, (80,255,80))

                            if side == "R":
                                reps_r += 1
                                set_feedback(
                                    f"Right leg up!  +{pts} pts  (R:{reps_r})"
                                    + (" COMBO!" if combo > 1 else ""),
                                    (80,255,120)
                                )
                            else:
                                reps_l += 1
                                set_feedback(
                                    f"Left leg up!  +{pts} pts  (L:{reps_l})"
                                    + (" COMBO!" if combo > 1 else ""),
                                    (80,255,120)
                                )
                            feedback_until = now + 2.0
                    else:
                        hold_count[side] = 0

                elif leg_state[side] == LEG_UP:
                    if not above:
                        leg_state[side]  = LEG_DOWN
                        hold_count[side] = 0
                        combo = 0   # combo resets on putting leg down
                        if mode == "ALTERNATE":
                            active_side = "L" if side == "R" else "R"
                            side_name   = "LEFT" if active_side == "L" else "RIGHT"
                            set_feedback(f"Good! Now raise your {side_name} knee!",
                                         (100,220,255))
                            feedback_until = now + 2.0

    # ── No person ─────────────────────────────────────────────────
    if not detected:
        set_feedback("No person detected: Step back so full body is visible",
                     (150,150,150))

    # ── Idle feedback ─────────────────────────────────────────────
    if calibrated and detected and now > feedback_until:
        side_name = "RIGHT" if active_side == "R" else "LEFT"
        if mode == "ALTERNATE":
            set_feedback(f"Raise your {side_name} knee to the dashed line!",
                         (200,210,255))
        elif mode == "R":
            set_feedback("Raise your RIGHT knee to the dashed line!", (0,255,200))
        else:
            set_feedback("Raise your LEFT knee to the dashed line!", (0,200,255))

    # ── Floating particles ────────────────────────────────────────
    update_draw_particles(frame, now)

    # ── TOP HUD ──────────────────────────────────────────────────
    rounded_rect(frame, 0, 0, W, 72, 0, (12,12,18), alpha=0.72)
    cv2.line(frame,(0,72),(W,72),(0,180,180),1)

    put_text(frame, f"Score: {score}", 18, 48, 1.0, (80,255,130), 2)
    put_text(frame, f"R:{reps_r}  L:{reps_l}", 200, 48, 0.85, (200,210,80), 2)

    if combo > 1:
        rounded_rect(frame, 360, 8, 510, 60, 8, (0,80,0), alpha=0.8)
        put_text(frame, f"x{combo} COMBO", 368, 44, 0.75, (80,255,80), 2)

    text_center(frame, "Exercise: Leg Raise", W//2, 46, 0.65, (180,210,255), 1)

    mode_label = f"Mode: {mode if mode != 'ALTERNATE' else 'ALT'}"
    (mw,_),_ = cv2.getTextSize(mode_label, cv2.FONT_HERSHEY_DUPLEX, 0.65, 1)
    put_text(frame, mode_label, W-mw-18, 48, 0.65, (120,200,255), 1)

    # Active side indicator
    if calibrated and detected and mode == "ALTERNATE":
        arrow  = ">>> RIGHT <<<" if active_side == "R" else ">>> LEFT <<<"
        acol   = (0,255,200) if active_side == "R" else (0,200,255)
        text_center(frame, arrow, W//2, 92, 0.8, acol, 2)

    # ── BOTTOM HUD ───────────────────────────────────────────────
    update_feedback_color()
    rounded_rect(frame, 0, H-72, W, H, 0, (12,12,18), alpha=0.72)
    cv2.line(frame,(0,H-72),(W,H-72),(0,180,180),1)
    col = tuple(int(c) for c in fb_current_col)
    text_center(frame, fb_text, W//2, H-22, 0.88, col, 2)

    # Controls sidebar
    rounded_rect(frame, 0, H-72-116, 200, H-72, 6, (8,8,18), alpha=0.55)
    for i, (k,v) in enumerate([("Q","Quit"),("R","Recalibrate"),
                                ("A","Alternate"),("L","Left leg"),("K","Right leg")]):
        put_text(frame, f"{k}  {v}", 10, H-72-98+i*22, 0.47, (160,160,200), 1)

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
                cv2.putText(frame, "DEMO: Leg Raise", (dx+2, dy-5), cv2.FONT_HERSHEY_DUPLEX, 0.45, (0,0,0), 1)
            except Exception as e:
                pass

    cv2.imshow("Rehab Quest: Leg Raise", frame)

    key = cv2.waitKey(1) & 0xFF
    if   key == ord('q'): break
    elif key == ord('r'):
        reset_cal()
        leg_state  = {"R": LEG_DOWN, "L": LEG_DOWN}
        hold_count = {"R": 0, "L": 0}
        combo      = 0
        set_feedback("Recalibrating: stand straight, feet on floor...",
                     (255,255,150))
    elif key == ord('a'):
        mode = "ALTERNATE"; active_side = "R"
        set_feedback("Mode: Alternate (Right first)", (200,255,200))
        feedback_until = now + 2
    elif key == ord('l'):
        mode = "L"
        set_feedback("Mode: LEFT leg only", (0,200,255))
        feedback_until = now + 2
    elif key == ord('k'):
        mode = "R"
        set_feedback("Mode: RIGHT leg only", (0,255,200))
        feedback_until = now + 2

cap.release()
cv2.destroyAllWindows()
print(f"[DONE] Leg Raise Score:{score}  R:{reps_r}  L:{reps_l}")
