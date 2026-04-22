"""
╔══════════════════════════════════════════════════════════════════╗
║           REHAB QUEST — Full Session Orchestrator               ║
║  3 Sets × 3 Exercises × 120s each                               ║
║  10s rest between exercises │ 30s rest between sets             ║
║  Exercises: Hand Raise ➜ Wrist 360° ➜ Leg Raise                ║
╚══════════════════════════════════════════════════════════════════╝
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
import collections
from enum import Enum, auto

# ══════════════════════════════════════════════════════════════════
#  SESSION CONFIGURATION  (tweak here)
# ══════════════════════════════════════════════════════════════════
TOTAL_SETS          = 3
EXERCISE_DURATION   = 120   # seconds each exercise runs
REST_EX_DURATION    = 10    # seconds rest between exercises in a set
REST_SET_DURATION   = 30    # seconds rest between sets
CAL_FRAMES_NEEDED   = 50    # frames for leg-raise body calibration

EXERCISE_ORDER = ['hand_raise', 'wrist_circle', 'leg_raise']

EXERCISE_NAMES = {
    'hand_raise':   'Hand Raise',
    'wrist_circle': 'Wrist 360°',
    'leg_raise':    'Leg Raise',
}
VIDEO_FILES = {
    'hand_raise':   'Hand_Raise.mp4',
    'wrist_circle': 'Wrist.mp4',
    'leg_raise':    'Leg_Raise.mp4',
}
EXERCISE_INSTRUCTIONS = {
    'hand_raise':   'Raise your RIGHT hand to catch the apple!',
    'wrist_circle': 'Move your RIGHT wrist in a full 360° circle!',
    'leg_raise':    'Alternate raising your knees to the target line!',
}
QUEUE_COLORS = {
    'hand_raise':   (0, 200, 200),
    'wrist_circle': (80, 180, 255),
    'leg_raise':    (80, 255, 120),
}
QUEUE_ICONS = {
    'hand_raise':   'HAND',
    'wrist_circle': 'WRIST',
    'leg_raise':    'LEG',
}

# ══════════════════════════════════════════════════════════════════
#  MEDIAPIPE POSE
# ══════════════════════════════════════════════════════════════════
mp_pose = mp.solutions.pose
PL      = mp_pose.PoseLandmark

pose = mp_pose.Pose(
    model_complexity         = 1,
    min_detection_confidence = 0.6,
    min_tracking_confidence  = 0.6,
    smooth_landmarks         = True,
)

# Mirror-aware landmark IDs
# cv2.flip() mirrors the feed: screen-right = MediaPipe LEFT landmark
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
#  WEBCAM
# ══════════════════════════════════════════════════════════════════
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS,          30)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[INFO] Camera: {W}×{H}")

# ══════════════════════════════════════════════════════════════════
#  LANDMARK SMOOTHING
# ══════════════════════════════════════════════════════════════════
SMOOTH_ALPHA = 0.35
_smoothed_lm: dict = {}

def smooth_landmarks(raw):
    global _smoothed_lm
    out = {}
    for i, lm in enumerate(raw.landmark):
        if i not in _smoothed_lm:
            _smoothed_lm[i] = [lm.x, lm.y, lm.z]
        else:
            sx, sy, sz = _smoothed_lm[i]
            _smoothed_lm[i] = [
                SMOOTH_ALPHA * lm.x + (1 - SMOOTH_ALPHA) * sx,
                SMOOTH_ALPHA * lm.y + (1 - SMOOTH_ALPHA) * sy,
                SMOOTH_ALPHA * lm.z + (1 - SMOOTH_ALPHA) * sz,
            ]
        out[i] = _smoothed_lm[i]
    return out

def reset_smoothing():
    global _smoothed_lm
    _smoothed_lm = {}

# ══════════════════════════════════════════════════════════════════
#  SKELETON DRAW
# ══════════════════════════════════════════════════════════════════
_SEGS = [
    (SCREEN_LEFT_SHOULDER,  SCREEN_RIGHT_SHOULDER, (220,220,220), 3),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_HIP,       (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_LEFT_HIP,       SCREEN_RIGHT_HIP,      (220,220,220), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_ELBOW,    (0,230,230),   4),
    (SCREEN_RIGHT_ELBOW,    SCREEN_RIGHT_WRIST,    (0,255,200),   4),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_ELBOW,     (0,200,200),   3),
    (SCREEN_LEFT_ELBOW,     SCREEN_LEFT_WRIST,     (0,220,180),   3),
    (SCREEN_RIGHT_HIP,      SCREEN_RIGHT_KNEE,     (0,140,255),   4),
    (SCREEN_RIGHT_KNEE,     SCREEN_RIGHT_ANKLE,    (0,170,255),   4),
    (SCREEN_RIGHT_ANKLE,    SCREEN_RIGHT_HEEL,     (0,190,255),   3),
    (SCREEN_RIGHT_HEEL,     SCREEN_RIGHT_FOOT,     (0,200,255),   3),
    (SCREEN_LEFT_HIP,       SCREEN_LEFT_KNEE,      (0,120,220),   3),
    (SCREEN_LEFT_KNEE,      SCREEN_LEFT_ANKLE,     (0,150,220),   3),
    (SCREEN_LEFT_ANKLE,     SCREEN_LEFT_HEEL,      (0,170,220),   3),
    (SCREEN_LEFT_HEEL,      SCREEN_LEFT_FOOT,      (0,180,220),   3),
]
_JOINTS = [
    (SCREEN_RIGHT_WRIST,    (0,255,200),  10),
    (SCREEN_LEFT_WRIST,     (0,220,180),   8),
    (SCREEN_RIGHT_ELBOW,    (0,230,230),   8),
    (SCREEN_LEFT_ELBOW,     (0,200,200),   7),
    (SCREEN_RIGHT_SHOULDER, (200,200,255), 9),
    (SCREEN_LEFT_SHOULDER,  (180,180,255), 8),
    (SCREEN_RIGHT_HIP,      (200,200,200), 8),
    (SCREEN_LEFT_HIP,       (200,200,200), 8),
    (SCREEN_RIGHT_KNEE,     (0,170,255),   8),
    (SCREEN_LEFT_KNEE,      (0,150,220),   7),
    (SCREEN_RIGHT_ANKLE,    (0,190,255),   8),
    (SCREEN_LEFT_ANKLE,     (0,170,220),   7),
]

def draw_skeleton(frame, lm_dict):
    for (a, b, color, thick) in _SEGS:
        if a not in lm_dict or b not in lm_dict: continue
        ax, ay = int(lm_dict[a][0]*W), int(lm_dict[a][1]*H)
        bx, by = int(lm_dict[b][0]*W), int(lm_dict[b][1]*H)
        if not (0<ax<W and 0<ay<H and 0<bx<W and 0<by<H): continue
        cv2.line(frame, (ax,ay), (bx,by), (0,0,0),  thick+3, cv2.LINE_AA)
        cv2.line(frame, (ax,ay), (bx,by),  color,   thick,   cv2.LINE_AA)
    for (jid, color, r) in _JOINTS:
        if jid not in lm_dict: continue
        jx = int(lm_dict[jid][0]*W)
        jy = int(lm_dict[jid][1]*H)
        if not (0<jx<W and 0<jy<H): continue
        cv2.circle(frame, (jx,jy), r+2, (0,0,0),     -1, cv2.LINE_AA)
        cv2.circle(frame, (jx,jy), r,   color,        -1, cv2.LINE_AA)
        cv2.circle(frame, (jx,jy), r,   (255,255,255), 1, cv2.LINE_AA)

# ══════════════════════════════════════════════════════════════════
#  HUD PRIMITIVES
# ══════════════════════════════════════════════════════════════════
def rounded_rect(img, x1, y1, x2, y2, r, bgr, alpha=0.65):
    ov = img.copy()
    cv2.rectangle(ov, (x1+r, y1), (x2-r, y2), bgr, -1)
    cv2.rectangle(ov, (x1, y1+r), (x2, y2-r), bgr, -1)
    for cx, cy in [(x1+r,y1+r), (x2-r,y1+r), (x1+r,y2-r), (x2-r,y2-r)]:
        cv2.circle(ov, (cx,cy), r, bgr, -1)
    cv2.addWeighted(ov, alpha, img, 1-alpha, 0, img)

def put_text(img, text, x, y, scale=0.8, color=(255,255,255), thickness=2):
    cv2.putText(img, text, (x+2,y+2), cv2.FONT_HERSHEY_DUPLEX,
                scale, (0,0,0), thickness+2, cv2.LINE_AA)
    cv2.putText(img, text, (x,y),     cv2.FONT_HERSHEY_DUPLEX,
                scale,  color,       thickness,   cv2.LINE_AA)

def text_center(img, text, cx, y, scale, color, thickness=2):
    (tw,_), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    put_text(img, text, cx-tw//2, y, scale, color, thickness)

# ══════════════════════════════════════════════════════════════════
#  DEMO VIDEO PLAYER  (top-left corner overlay, looping)
# ══════════════════════════════════════════════════════════════════
DEMO_W, DEMO_H = 240, 135   # 16:9 thumbnail

class DemoPlayer:
    def __init__(self):
        self.caps    = {}
        self.current = None
        for key, path in VIDEO_FILES.items():
            c = cv2.VideoCapture(path)
            if c.isOpened():
                self.caps[key] = c
                print(f"[INFO] Demo loaded: {path}")
            else:
                print(f"[WARN] Demo not found: {path} (will show placeholder)")

    def set_exercise(self, key):
        self.current = key

    def get_frame(self):
        """Read next looped frame; returns BGR (DEMO_W×DEMO_H) or None."""
        if not self.current or self.current not in self.caps:
            return None
        c = self.caps[self.current]
        ret, frm = c.read()
        if not ret:
            c.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frm = c.read()
        return cv2.resize(frm, (DEMO_W, DEMO_H)) if ret else None

    def overlay(self, frame, demo_frm, label="DEMO"):
        """Paste demo thumbnail in top-left below the top HUD bar."""
        PAD  = 4
        X0   = 8
        Y0   = 80       # just below the top HUD bar
        LBL_H = 20

        bx1 = X0 - 2
        by1 = Y0 - 2
        bx2 = X0 + PAD + DEMO_W + PAD + 2
        by2 = Y0 + LBL_H + PAD + DEMO_H + PAD + 2
        rounded_rect(frame, bx1, by1, bx2, by2, 5, (0,60,60), alpha=0.92)

        # Label
        put_text(frame, label, X0+PAD, Y0+LBL_H-2, 0.40, (0,210,170), 1)

        # Video thumbnail
        vy = Y0 + LBL_H + PAD
        if demo_frm is not None:
            frame[vy:vy+DEMO_H, X0+PAD:X0+PAD+DEMO_W] = demo_frm
            cv2.rectangle(frame,
                          (X0+PAD,   vy),
                          (X0+PAD+DEMO_W, vy+DEMO_H),
                          (0,180,140), 1)
        else:
            # Placeholder when video file missing
            cv2.rectangle(frame,
                          (X0+PAD, vy),
                          (X0+PAD+DEMO_W, vy+DEMO_H),
                          (40,40,60), -1)
            text_center(frame, "No Video", X0+PAD+DEMO_W//2,
                        vy+DEMO_H//2+8, 0.45, (120,120,160), 1)

    def release(self):
        for c in self.caps.values():
            c.release()

# ══════════════════════════════════════════════════════════════════
#  EXERCISE QUEUE
# ══════════════════════════════════════════════════════════════════
def build_queue():
    """Returns list of (set_num, ex_key) for all 9 exercise slots."""
    q = []
    for s in range(1, TOTAL_SETS+1):
        for ex in EXERCISE_ORDER:
            q.append((s, ex))
    return q

FULL_QUEUE = build_queue()   # 9 items total

def draw_queue_strip(frame, view_start, active_idx):
    """
    Bottom strip showing the upcoming exercise sequence.
    view_start : first FULL_QUEUE index to render
    active_idx : which index is currently active (highlighted bright)
    """
    BAR_Y = H - 110
    BAR_H = 50
    CARD_W = 148
    CARD_H = 37
    START_X = 88

    rounded_rect(frame, 0, BAR_Y, W, BAR_Y+BAR_H, 0, (8,8,22), alpha=0.85)
    cv2.line(frame, (0,BAR_Y), (W,BAR_Y), (0,110,110), 1)
    put_text(frame, "QUEUE:", 8, BAR_Y+32, 0.48, (90,130,150), 1)

    items = FULL_QUEUE[view_start: view_start+6]

    for i, (s_num, ex_key) in enumerate(items):
        idx       = view_start + i
        is_active = (idx == active_idx)
        cx        = START_X + i * (CARD_W + 5)
        cy        = BAR_Y + 7

        base_col = QUEUE_COLORS.get(ex_key, (150,150,150))

        if is_active:
            fill   = tuple(c // 3 for c in base_col)
            border = base_col
            txt    = (255,255,255)
            alp    = 0.88
        else:
            fill   = (16,16,28)
            border = tuple(c // 5 for c in base_col)
            txt    = (100,110,120)
            alp    = 0.50

        rounded_rect(frame, cx, cy, cx+CARD_W, cy+CARD_H, 5, fill, alpha=alp)
        cv2.rectangle(frame, (cx,cy), (cx+CARD_W, cy+CARD_H), border, 1)

        icon = QUEUE_ICONS.get(ex_key, '??')
        name = EXERCISE_NAMES.get(ex_key, ex_key)
        put_text(frame, f"S{s_num} {icon}", cx+5, cy+15, 0.37,
                 base_col if is_active else border, 1)
        put_text(frame, name[:14], cx+5, cy+31, 0.38, txt, 1)

# ══════════════════════════════════════════════════════════════════
#  PHASE ENUM
# ══════════════════════════════════════════════════════════════════
class Phase(Enum):
    EXERCISE      = auto()   # active exercise running
    CALIBRATING   = auto()   # leg-raise body calibration (pre-exercise)
    REST_EXERCISE = auto()   # 10s between exercises within a set
    REST_SET      = auto()   # 30s between sets
    SUMMARY       = auto()   # final results screen

# ══════════════════════════════════════════════════════════════════
#  EXERCISE CLASS — HAND RAISE
# ══════════════════════════════════════════════════════════════════
class ExHandRaise:
    APPLE_R  = 42
    PICK_D   = 85
    RESPAWN  = 2.0
    BURST_D  = 0.4

    def __init__(self): self.reset()

    def reset(self):
        self.score     = 0
        self.combo     = 0
        self.visible   = True
        self.respawn   = 0.0
        self.burst_at  = -99.0
        self.trail     = collections.deque(maxlen=20)
        self.particles = []
        self.fb        = "Raise your RIGHT hand to grab the apple!"
        self.fb_col    = np.array([255,255,255], dtype=float)
        self.fb_cur    = np.array([255,255,255], dtype=float)

    def _fb(self, t, c):
        self.fb = t
        self.fb_col = np.array(c, dtype=float)

    def _spawn(self, x, y, text, col):
        self.particles.append({
            'x':x, 'y':y, 'vy':-2.5, 'text':text,
            'color':col, 'alpha':1.0, 'birth':time.time()
        })

    def update(self, frame, lm, now):
        """Process one frame. Returns (score_delta, feedback_text)."""
        AX = W // 2
        AY = int(H * 0.20)

        state = 0; wp = None; prox = 0.0; near = False

        if lm:
            rw = lm[SCREEN_RIGHT_WRIST]
            rs = lm[SCREEN_RIGHT_SHOULDER]
            wp = (int(rw[0]*W), int(rw[1]*H))
            self.trail.append(wp)
            state = 1 if rw[1] < rs[1] else 0
            dist  = math.hypot(wp[0]-AX, wp[1]-AY)
            prox  = max(0.0, 1.0 - dist/250)
            near  = dist < self.PICK_D

        delta = 0
        if not self.visible:
            if now >= self.respawn:
                self.visible = True; self.combo = 0
                self._fb("New apple! Raise your hands!", (200,255,200))
        else:
            if state == 1 and near:
                self.visible = False; self.respawn = now + self.RESPAWN
                self.combo  += 1; pts = 10 * self.combo
                self.score  += pts; delta = pts; self.burst_at = now
                lbl = f"+{pts}!" if self.combo == 1 else f"+{pts} x{self.combo}!"
                self._spawn(AX-60, AY-60, lbl, (80,255,80))
                self._fb(f"Amazing! +{pts} pts!" + (" COMBO!" if self.combo > 1 else ""),
                         (80,255,80))
            elif state == 1:
                self._fb("Almost there! Reach toward the apple!", (100,220,255))
            else:
                self._fb("Raise your hands higher!", (80,100,255))

        # ── Draw: wrist trail ──────────────────────────────────────
        pts_t = list(self.trail)
        for i in range(1, len(pts_t)):
            al = i / len(pts_t); r2 = max(2, int(al*8))
            col = (0, int(al*255), int(al*200))
            cv2.circle(frame, pts_t[i], r2, (0,0,0), -1, cv2.LINE_AA)
            cv2.circle(frame, pts_t[i], r2, col,     -1, cv2.LINE_AA)
            if i > 1:
                t2 = (i-1)/len(pts_t)
                cv2.line(frame, pts_t[i-1], pts_t[i],
                         (0,int(t2*255),int(t2*200)), r2, cv2.LINE_AA)

        # ── Draw: apple ───────────────────────────────────────────
        bp = min(1.0, (now - self.burst_at) / self.BURST_D)
        if self.visible:
            rr  = self.APPLE_R + 22
            rc  = (0,255,80) if prox > 0.7 else (0,200,255)
            off = int(now*40) % 30
            for i in range(12):
                a1 = (30*i + off) % 360
                cv2.ellipse(frame,(AX,AY),(rr,rr),0,a1,a1+14,rc,3,cv2.LINE_AA)
            if prox > 0.05:
                cv2.ellipse(frame,(AX,AY),(rr+8,rr+8),
                            -90,0,int(360*prox),(0,255,120),4,cv2.LINE_AA)
            cv2.circle(frame,(AX,AY),self.APPLE_R,(20,20,200),-1,cv2.LINE_AA)
            cv2.circle(frame,(AX,AY),self.APPLE_R,(0,0,120),2,cv2.LINE_AA)
            cv2.line(frame,(AX,AY-self.APPLE_R),(AX+7,AY-self.APPLE_R-15),
                     (0,100,0),3,cv2.LINE_AA)
        else:
            if bp < 1.0:
                rv = int(self.APPLE_R*(1+bp*3)); ov2 = frame.copy()
                cv2.circle(ov2,(AX,AY),rv,(80,255,80),-1,cv2.LINE_AA)
                cv2.addWeighted(ov2,(1-bp)*0.5,frame,1-(1-bp)*0.5,0,frame)
            cv2.circle(frame,(AX,AY),self.APPLE_R+10,(80,80,80),2,cv2.LINE_AA)
            secs = max(0, self.respawn-now)
            text_center(frame, f"{secs:.1f}s", AX, AY+8, 0.58,(160,160,160),1)

        # ── Draw: wrist crosshair when near ────────────────────────
        if wp and near and self.visible:
            cx2, cy2 = wp
            cv2.line(frame,(cx2-20,cy2),(cx2+20,cy2),(0,255,80),2,cv2.LINE_AA)
            cv2.line(frame,(cx2,cy2-20),(cx2,cy2+20),(0,255,80),2,cv2.LINE_AA)
            cv2.circle(frame, wp, 22, (0,255,80), 2, cv2.LINE_AA)

        # ── Draw: particles ───────────────────────────────────────
        alive = []
        for p in self.particles:
            age = now - p['birth']
            if age > 1.5: continue
            p['y'] += p['vy']; p['alpha'] = max(0, 1.0 - age/1.2)
            c2 = tuple(int(c*p['alpha']) for c in p['color'])
            cv2.putText(frame, p['text'], (int(p['x'])+2, int(p['y'])+2),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (0,0,0), 4, cv2.LINE_AA)
            cv2.putText(frame, p['text'], (int(p['x']), int(p['y'])),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, c2, 2, cv2.LINE_AA)
            alive.append(p)
        self.particles[:] = alive

        self.fb_cur += (self.fb_col - self.fb_cur) * 0.12
        return delta, self.fb

# ══════════════════════════════════════════════════════════════════
#  EXERCISE CLASS — WRIST 360° CIRCLE
# ══════════════════════════════════════════════════════════════════
class ExWristCircle:
    GUIDE_R = 90

    def __init__(self): self.reset()

    def reset(self):
        self.score     = 0
        self.reps      = 0
        self.trail     = collections.deque(maxlen=80)
        self.prev_ang  = None
        self.ang_sum   = 0.0
        self.particles = []
        self.fb        = "Move your RIGHT wrist in a full circle!"
        self.fb_col    = np.array([255,255,200], dtype=float)
        self.fb_cur    = np.array([255,255,200], dtype=float)

    def _fb(self, t, c):
        self.fb = t
        self.fb_col = np.array(c, dtype=float)

    def _spawn(self, x, y, text, col):
        self.particles.append({
            'x':x, 'y':y, 'vy':-2.5, 'text':text,
            'color':col, 'alpha':1.0, 'birth':time.time()
        })

    def update(self, frame, lm, now):
        GX = W // 2; GY = H // 2
        wp = None; prox = 0.0; delta = 0

        if lm:
            rw = lm[SCREEN_RIGHT_WRIST]
            wp = (int(rw[0]*W), int(rw[1]*H))
            self.trail.append(wp)

            d2c  = math.hypot(wp[0]-GX, wp[1]-GY)
            prox = max(0.0, 1.0 - d2c/(self.GUIDE_R*2.5))

            ang = (math.degrees(math.atan2(wp[1]-GY, wp[0]-GX)) + 90) % 360
            if self.prev_ang is not None:
                dlt = ang - self.prev_ang
                if dlt >  180: dlt -= 360
                if dlt < -180: dlt += 360
                self.ang_sum += dlt
            self.prev_ang = ang

            if abs(self.ang_sum) > 300:
                self.score += 20; self.reps += 1; delta = 20
                dl = "CW" if self.ang_sum > 0 else "CCW"
                self._spawn(GX-50, GY-60,
                            f"{dl} +20  Rep {self.reps}", (80,255,120))
                self._fb(f"Full Circle! Rep {self.reps} — +20 pts!", (80,255,120))
                self.ang_sum = 0.0; self.trail.clear()
            elif abs(self.ang_sum) > 60:
                pct = min(100, int(abs(self.ang_sum)/300*100))
                self._fb(f"Keep going!  {pct}% complete", (100,220,255))
            else:
                self._fb("Move your RIGHT wrist along the circle!", (255,255,200))

            # Wrist dot + near-ring crosshair
            cv2.circle(frame, wp, 18, (0,255,180),  2, cv2.LINE_AA)
            cv2.circle(frame, wp, 10, (0,255,180), -1, cv2.LINE_AA)
            if abs(d2c - self.GUIDE_R) < 30:
                cv2.line(frame,(wp[0]-20,wp[1]),(wp[0]+20,wp[1]),(0,255,80),2,cv2.LINE_AA)
                cv2.line(frame,(wp[0],wp[1]-20),(wp[0],wp[1]+20),(0,255,80),2,cv2.LINE_AA)

        # ── Draw: wrist trail ──────────────────────────────────────
        pts_t = list(self.trail)
        for i in range(1, len(pts_t)):
            t2 = i / len(pts_t)
            cv2.line(frame, pts_t[i-1], pts_t[i],
                     (0, int(255*t2), 200), int(2+t2*3), cv2.LINE_AA)

        # ── Draw: guide ring ──────────────────────────────────────
        col = (0,255,80) if prox > 0.7 else (0,200,255)
        cv2.circle(frame, (GX,GY), self.GUIDE_R, (40,40,70), 2, cv2.LINE_AA)
        off = int(now*40) % 30
        for i in range(12):
            a1 = (30*i + off) % 360
            cv2.ellipse(frame,(GX,GY),(self.GUIDE_R,self.GUIDE_R),0,a1,a1+14,col,3,cv2.LINE_AA)
        if prox > 0.05:
            cv2.ellipse(frame,(GX,GY),(self.GUIDE_R+10,self.GUIDE_R+10),
                        -90,0,int(360*prox),(0,255,120),4,cv2.LINE_AA)
        cv2.line(frame,(GX,GY-self.GUIDE_R-15),(GX,GY+self.GUIDE_R+15),(40,40,70),1,cv2.LINE_AA)
        cv2.line(frame,(GX-self.GUIDE_R-15,GY),(GX+self.GUIDE_R+15,GY),(40,40,70),1,cv2.LINE_AA)

        # ── Draw: rotation progress arc (right panel) ─────────────
        r3x, r3y, r3 = W-55, 155, 38
        cv2.circle(frame, (r3x,r3y), r3, (40,40,60), 8)
        pct3 = min(1.0, abs(self.ang_sum) / 300)
        if pct3 > 0:
            ac = (0,255,80) if pct3 > 0.8 else (0,200,255)
            cv2.ellipse(frame,(r3x,r3y),(r3,r3),-90,0,int(360*pct3),ac,8,cv2.LINE_AA)
        put_text(frame, "ROT", r3x-15, r3y+8, 0.37, (120,140,170), 1)

        # ── Draw: particles ───────────────────────────────────────
        alive = []
        for p in self.particles:
            age = now - p['birth']
            if age > 1.5: continue
            p['y'] += p['vy']; p['alpha'] = max(0, 1.0-age/1.2)
            c2 = tuple(int(c*p['alpha']) for c in p['color'])
            cv2.putText(frame,p['text'],(int(p['x'])+2,int(p['y'])+2),
                        cv2.FONT_HERSHEY_DUPLEX,1.1,(0,0,0),4,cv2.LINE_AA)
            cv2.putText(frame,p['text'],(int(p['x']),int(p['y'])),
                        cv2.FONT_HERSHEY_DUPLEX,1.1,c2,2,cv2.LINE_AA)
            alive.append(p)
        self.particles[:] = alive

        self.fb_cur += (self.fb_col - self.fb_cur) * 0.12
        return delta, self.fb

# ══════════════════════════════════════════════════════════════════
#  EXERCISE CLASS — LEG RAISE (with body calibration)
# ══════════════════════════════════════════════════════════════════
class ExLegRaise:
    LEG_D   = "D"; LEG_U = "U"
    HOLD_N  = 10
    TGT_F   = 0.18   # fraction of leg length above hip = target height
    KA      = 0.25   # knee extra smoothing alpha
    BURST_D = 0.5

    def __init__(self): self.reset()

    def reset(self):
        self.score     = 0
        self.reps_r    = 0; self.reps_l = 0; self.combo = 0
        self.active    = "R"
        self.leg_st    = {"R": self.LEG_D, "L": self.LEG_D}
        self.hold_c    = {"R": 0, "L": 0}
        self.smk       = {"R": None, "L": None}
        self.burst_s   = None; self.burst_t = -99.0
        self.tfl       = 0.0        # target flash end time
        self.particles = []
        self.fb        = "Stand straight: calibrating..."
        self.fb_col    = np.array([255,255,150], dtype=float)
        self.fb_cur    = np.array([255,255,150], dtype=float)
        self.fb_until  = 0.0
        # Calibration state
        self.cal_n     = 0
        self.cal_buf   = {"rh":[],"lh":[],"ra":[],"la":[]}
        self.calibrated= False
        self.hip_y     = {"R": H*0.45, "L": H*0.45}
        self.ank_y     = {"R": H*0.85, "L": H*0.85}

    def _fb(self, t, c): self.fb = t; self.fb_col = np.array(c, dtype=float)

    def _spawn(self, x, y, text, col):
        self.particles.append({
            'x':x,'y':y,'vy':-2.5,'text':text,
            'color':col,'alpha':1.0,'birth':time.time()
        })

    def _tgt(self, side):
        leg = abs(self.ank_y[side] - self.hip_y[side])
        return int(self.hip_y[side] + leg * self.TGT_F)

    def update(self, frame, lm, now):
        if not lm:
            self._fb("No person detected — step back for full body view", (150,150,150))
            return 0, self.fb

        def px(lid):
            v = lm[lid]
            return (int(v[0]*W), int(v[1]*H)), float(v[1]*H)

        rhp, rhy = px(SCREEN_RIGHT_HIP)
        lhp, lhy = px(SCREEN_LEFT_HIP)
        rkp, rky = px(SCREEN_RIGHT_KNEE)
        lkp, lky = px(SCREEN_LEFT_KNEE)
        rap, ray = px(SCREEN_RIGHT_ANKLE)
        lap, lay = px(SCREEN_LEFT_ANKLE)

        # ── Calibration (runs until CAL_FRAMES_NEEDED frames collected) ──
        if not self.calibrated:
            self.cal_n += 1
            self.cal_buf["rh"].append(rhy); self.cal_buf["lh"].append(lhy)
            self.cal_buf["ra"].append(ray); self.cal_buf["la"].append(lay)
            pct = self.cal_n / CAL_FRAMES_NEEDED
            bx  = (W-360)//2; by = H//2 + 10
            rounded_rect(frame, bx-24, by-60, bx+384, by+54, 10, (10,10,25), 0.82)
            cv2.line(frame,(bx-24,by-60),(bx+384,by-60),(0,180,180),2)
            text_center(frame,"Calibrating: stand straight, feet flat on floor",
                        W//2, by-28, 0.68, (200,230,255), 1)
            cv2.rectangle(frame,(bx,by+5),(bx+360,by+28),(30,30,50),-1)
            cv2.rectangle(frame,(bx,by+5),(bx+int(360*pct),by+28),(0,200,255),-1)
            cv2.rectangle(frame,(bx,by+5),(bx+360,by+28),(60,80,120),2)
            text_center(frame, f"{int(pct*100)}%", W//2, by+22, 0.50,(180,220,255),1)

            if self.cal_n >= CAL_FRAMES_NEEDED:
                self.hip_y["R"] = float(np.mean(self.cal_buf["rh"]))
                self.hip_y["L"] = float(np.mean(self.cal_buf["lh"]))
                self.ank_y["R"] = float(np.mean(self.cal_buf["ra"]))
                self.ank_y["L"] = float(np.mean(self.cal_buf["la"]))
                self.calibrated  = True
                self._fb("Ready! Raise your RIGHT knee to the line!", (80,255,120))
                self.fb_until = now + 3.0
            return 0, self.fb

        # ── Knee smoothing ────────────────────────────────────────
        for side, ky in [("R", rky), ("L", lky)]:
            if self.smk[side] is None: self.smk[side] = ky
            else: self.smk[side] = self.KA*ky + (1-self.KA)*self.smk[side]

        # ── Draw target lines ─────────────────────────────────────
        for side, acol, dcol, lbl in [
            ("R", (0,255,180), (40,70,60),  "TARGET: Right Knee"),
            ("L", (0,180,255), (40,60,80),  "TARGET: Left Knee"),
        ]:
            tgt = self._tgt(side)
            act = (self.active == side)
            col = acol if act else dcol

            if act and now < self.tfl:
                al = 0.5 + 0.5*math.sin(now*14)
                col = tuple(int(c*al) for c in acol)

            if act:
                ov2 = frame.copy()
                cv2.line(ov2,(0,tgt),(W,tgt),acol,12,cv2.LINE_AA)
                cv2.addWeighted(ov2,0.25,frame,0.75,0,frame)

            x = 0
            while x < W:
                cv2.line(frame,(x,tgt),(min(x+22,W),tgt),col,3,cv2.LINE_AA)
                x += 32

            rounded_rect(frame, 8, tgt-18, 202, tgt+18, 6, (10,10,22), 0.75)
            put_text(frame, lbl, 16, tgt+9, 0.50, col, 1)

        # ── Draw arc progress indicators ──────────────────────────
        for side, hip, ank, kv, ax2, lbl2 in [
            ("R", self.hip_y["R"], self.ank_y["R"],
             self.smk["R"] or rky, W-65,  "R"),
            ("L", self.hip_y["L"], self.ank_y["L"],
             self.smk["L"] or lky, W-155, "L"),
        ]:
            if self.active != side: continue
            tgt  = self._tgt(side)
            den  = max(1, hip - tgt)
            pct  = max(0, min(1.0, (hip - kv) / den))
            ac   = (0,255,120) if pct >= 0.95 else (0,200,255)
            cv2.circle(frame,(ax2,155),38,(30,30,50),8)
            if pct > 0:
                cv2.ellipse(frame,(ax2,155),(38,38),-90,0,int(360*pct),ac,8,cv2.LINE_AA)
            put_text(frame, lbl2, ax2-9, 163, 0.62, ac, 2)

        # ── Burst animation on successful rep ─────────────────────
        if self.burst_s is not None:
            prog = min(1.0, (now-self.burst_t)/self.BURST_D)
            if prog < 1.0:
                kpx = rkp if self.burst_s=="R" else lkp
                ov3 = frame.copy()
                cv2.circle(ov3, kpx, int(20+prog*60),(80,255,80),-1,cv2.LINE_AA)
                cv2.addWeighted(ov3,(1-prog)*0.35,frame,1-(1-prog)*0.35,0,frame)
            else:
                self.burst_s = None

        # ── Game logic ────────────────────────────────────────────
        delta = 0
        for side in ["R","L"]:
            if self.active != side: continue
            tgt  = self._tgt(side)
            ks   = self.smk[side] or (rky if side=="R" else lky)
            above = ks <= tgt

            if self.leg_st[side] == self.LEG_D:
                if above:
                    self.hold_c[side] += 1
                    if self.hold_c[side] >= self.HOLD_N:
                        self.leg_st[side] = self.LEG_U
                        self.combo += 1; pts = 10*self.combo
                        self.score += pts; delta = pts
                        self.tfl = now + 0.8
                        self.burst_s = side; self.burst_t = now
                        kpx = rkp if side=="R" else lkp
                        lbl3 = f"+{pts}!" if self.combo==1 else f"+{pts} x{self.combo}!"
                        self._spawn(kpx[0]-30, kpx[1]-50, lbl3, (80,255,80))
                        if side=="R": self.reps_r += 1
                        else:         self.reps_l += 1
                        sn = "Right" if side=="R" else "Left"
                        self._fb(f"{sn} leg UP!  +{pts}!" + (" COMBO!" if self.combo>1 else ""),
                                 (80,255,120))
                        self.fb_until = now + 2.0
                else:
                    self.hold_c[side] = 0

            elif self.leg_st[side] == self.LEG_U:
                if not above:
                    self.leg_st[side] = self.LEG_D
                    self.hold_c[side] = 0; self.combo = 0
                    self.active = "L" if side=="R" else "R"
                    sn2 = "LEFT" if self.active=="L" else "RIGHT"
                    self._fb(f"Good! Now raise your {sn2} knee!", (100,220,255))
                    self.fb_until = now + 2.0

        if now > self.fb_until:
            sn3 = "RIGHT" if self.active=="R" else "LEFT"
            self._fb(f"Raise your {sn3} knee to the dashed line!", (200,210,255))

        # Active side arrow + rep counter in HUD zone
        put_text(frame, f"R:{self.reps_r}  L:{self.reps_l}",
                 260, 48, 0.80, (200,210,80), 2)
        arrow = ">>> RIGHT <<<" if self.active=="R" else ">>> LEFT <<<"
        acol2 = (0,255,200) if self.active=="R" else (0,200,255)
        text_center(frame, arrow, W//2, 92, 0.78, acol2, 2)

        # Particles
        alive = []
        for p in self.particles:
            age = now - p['birth']
            if age > 1.5: continue
            p['y'] += p['vy']; p['alpha'] = max(0, 1.0-age/1.2)
            c2 = tuple(int(c*p['alpha']) for c in p['color'])
            cv2.putText(frame,p['text'],(int(p['x'])+2,int(p['y'])+2),
                        cv2.FONT_HERSHEY_DUPLEX,1.1,(0,0,0),4,cv2.LINE_AA)
            cv2.putText(frame,p['text'],(int(p['x']),int(p['y'])),
                        cv2.FONT_HERSHEY_DUPLEX,1.1,c2,2,cv2.LINE_AA)
            alive.append(p)
        self.particles[:] = alive

        self.fb_cur += (self.fb_col - self.fb_cur) * 0.12
        return delta, self.fb

# ══════════════════════════════════════════════════════════════════
#  INSTANTIATE ALL OBJECTS
# ══════════════════════════════════════════════════════════════════
exercises: dict = {
    'hand_raise':   ExHandRaise(),
    'wrist_circle': ExWristCircle(),
    'leg_raise':    ExLegRaise(),
}
demo = DemoPlayer()

# ══════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════
queue_pos               = 0
current_set, current_ex = FULL_QUEUE[0]
phase                   = Phase.EXERCISE
phase_end               = time.time() + EXERCISE_DURATION

banked_score            = 0    # sum of scores from all COMPLETED exercise slots
set_start_bank          = 0    # banked score at the start of the current set
set_score_log: list     = []   # per-set totals logged at end of each set [s1,s2,s3]

# Initialise first exercise
exercises[current_ex].reset()
reset_smoothing()
demo.set_exercise(current_ex)

# Leg raise always starts with calibration
if current_ex == 'leg_raise':
    phase     = Phase.CALIBRATING
    phase_end = time.time() + 9999

# ══════════════════════════════════════════════════════════════════
#  REST SCREEN OVERLAY
# ══════════════════════════════════════════════════════════════════
def draw_rest_screen(frame, now, is_set_rest, next_ex, next_set):
    rem = max(0, phase_end - now)

    # Dim whole frame
    ov = frame.copy()
    cv2.rectangle(ov,(0,0),(W,H),(5,5,15),-1)
    cv2.addWeighted(ov,0.55,frame,0.45,0,frame)

    # Card
    cw, ch = 540, 280
    cxr, cyr = W//2-cw//2, H//2-ch//2
    rounded_rect(frame, cxr, cyr, cxr+cw, cyr+ch, 18, (14,14,30), alpha=0.94)
    cv2.rectangle(frame,(cxr,cyr),(cxr+cw,cyr+ch),(0,180,180),2)

    if is_set_rest:
        title = f"Set {current_set} Complete!  Great Job!"
        sub   = f"Prepare for Set {next_set}  ·  {EXERCISE_NAMES.get(next_ex,'')}"
        tc    = (80,255,130)
    else:
        title = "Rest"
        sub   = f"Coming up:  {EXERCISE_NAMES.get(next_ex,'')}  (Set {next_set})"
        tc    = (0,200,255)

    text_center(frame, title, W//2, cyr+60,  0.95, tc, 2)
    text_center(frame, sub,   W//2, cyr+105, 0.70, (200,200,255), 1)

    # Big countdown number
    c_str = str(int(rem)+1)
    text_center(frame, c_str,     W//2, cyr+195, 3.4, (255,255,255), 6)
    text_center(frame, "seconds", W//2, cyr+248, 0.66,(150,150,200), 1)

# ══════════════════════════════════════════════════════════════════
#  SUMMARY SCREEN
# ══════════════════════════════════════════════════════════════════
def draw_summary_screen(frame, total):
    ov = frame.copy()
    cv2.rectangle(ov,(0,0),(W,H),(5,5,15),-1)
    cv2.addWeighted(ov,0.78,frame,0.22,0,frame)

    cw, ch = 700, 460
    cx4, cy4 = W//2-cw//2, H//2-ch//2
    rounded_rect(frame, cx4, cy4, cx4+cw, cy4+ch, 20, (12,12,28), alpha=0.96)
    cv2.rectangle(frame,(cx4,cy4),(cx4+cw,cy4+ch),(0,200,180),2)

    text_center(frame, "SESSION COMPLETE!",
                W//2, cy4+58, 1.15, (80,255,130), 3)
    cv2.line(frame,(cx4+24,cy4+78),(cx4+cw-24,cy4+78),(0,140,130),1)

    text_center(frame, f"TOTAL SCORE:  {total}",
                W//2, cy4+132, 1.4, (255,220,70), 4)

    for i, sc in enumerate(set_score_log):
        text_center(frame, f"Set {i+1} :  {sc} pts",
                    W//2, cy4+195+i*48, 0.88, (180,210,255), 2)

    msg, mc = (
        ("Outstanding Performance!  Keep crushing it!", (80,255,130)) if total > 500 else
        ("Great job!  You're making real progress!",    (100,220,255)) if total > 200 else
        ("Good effort!  Keep practicing every day!",    (200,200,255))
    )
    text_center(frame, msg,            W//2, cy4+380, 0.74, mc, 2)
    text_center(frame, "Press  Q  to exit",
                W//2, cy4+430, 0.60, (130,130,170), 1)

# ══════════════════════════════════════════════════════════════════
#  TOP HUD BAR
# ══════════════════════════════════════════════════════════════════
def draw_top_hud(frame, now, live_score):
    rounded_rect(frame, 0, 0, W, 72, 0, (12,12,18), alpha=0.84)
    cv2.line(frame,(0,72),(W,72),(0,180,180),1)

    # Left — live score
    put_text(frame, f"Score: {live_score}", 18, 48, 1.0, (80,255,130), 2)

    # Centre — set + exercise name
    ex_name = EXERCISE_NAMES.get(current_ex, current_ex)
    text_center(frame,
                f"Set {current_set} / {TOTAL_SETS}   —   {ex_name}",
                W//2, 46, 0.72, (180,210,255), 2)

    # Right — countdown timer
    rem = max(0, phase_end - now)
    if phase == Phase.EXERCISE:
        tc = (0,255,130) if rem > 30 else (0,200,255) if rem > 10 else (120,80,255)
        # Pulse effect in last 10 s
        if rem <= 10:
            pulse = 0.7 + 0.3 * math.sin(now * 6)
            tc = tuple(int(c*pulse) for c in tc)
        tt = f"  {int(rem):02d}s  "
    elif phase == Phase.CALIBRATING:
        tc = (255,255,150); tt = "  CALIBRATING...  "
    elif phase in (Phase.REST_EXERCISE, Phase.REST_SET):
        tc = (255,160,60);  tt = f"  REST {int(rem)+1}s  "
    else:
        tc = (255,255,255); tt = ""

    (tw,_),_ = cv2.getTextSize(tt, cv2.FONT_HERSHEY_DUPLEX, 0.95, 2)
    # Timer background pill
    rounded_rect(frame, W-tw-28, 8, W-4, 64, 8, (25,25,40), alpha=0.80)
    put_text(frame, tt, W-tw-22, 48, 0.95, tc, 2)

# ══════════════════════════════════════════════════════════════════
#  BOTTOM FEEDBACK BAR
# ══════════════════════════════════════════════════════════════════
def draw_bottom_hud(frame, fb_text, fb_cur):
    FB_Y = H - 165
    rounded_rect(frame, 0, FB_Y, W, FB_Y+55, 0, (12,12,18), alpha=0.75)
    cv2.line(frame,(0,FB_Y),(W,FB_Y),(0,180,180),1)
    col = tuple(int(c) for c in fb_cur)
    text_center(frame, fb_text, W//2, FB_Y+35, 0.82, col, 2)

# ══════════════════════════════════════════════════════════════════
#  PHASE ADVANCE — called when a phase ends
# ══════════════════════════════════════════════════════════════════
def advance_phase():
    global phase, phase_end, current_set, current_ex, queue_pos
    global banked_score, set_start_bank, set_score_log

    if phase in (Phase.EXERCISE, Phase.CALIBRATING):
        # Bank the score earned during this exercise slot
        banked_score += exercises[current_ex].score

        nxt = queue_pos + 1

        if nxt >= len(FULL_QUEUE):
            # All 9 exercise slots complete → summary
            set_score_log.append(banked_score - set_start_bank)
            phase = Phase.SUMMARY
            return

        n_set, n_ex = FULL_QUEUE[nxt]

        if n_set > current_set:
            # End of a set → long rest
            set_score_log.append(banked_score - set_start_bank)
            set_start_bank = banked_score
            phase     = Phase.REST_SET
            phase_end = time.time() + REST_SET_DURATION
        else:
            # Same set, different exercise → short rest
            phase     = Phase.REST_EXERCISE
            phase_end = time.time() + REST_EX_DURATION

        # Preview next exercise demo video during rest
        demo.set_exercise(n_ex)

    elif phase in (Phase.REST_EXERCISE, Phase.REST_SET):
        # Rest over → start next exercise
        queue_pos               += 1
        current_set, current_ex  = FULL_QUEUE[queue_pos]
        exercises[current_ex].reset()
        reset_smoothing()
        demo.set_exercise(current_ex)

        if current_ex == 'leg_raise':
            phase     = Phase.CALIBRATING
            phase_end = time.time() + 9999   # calibration self-terminates
        else:
            phase     = Phase.EXERCISE
            phase_end = time.time() + EXERCISE_DURATION

# ══════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════
print("[INFO] Rehab Quest — Session Started.  Press Q to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)   # mirror so user sees themselves naturally
    now   = time.time()

    # ── Pose detection ────────────────────────────────────────────
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = pose.process(rgb)
    lm_dict: dict = {}
    if res.pose_landmarks:
        lm_dict = smooth_landmarks(res.pose_landmarks)
        # Draw skeleton only during active exercise phases
        if phase not in (Phase.REST_EXERCISE, Phase.REST_SET, Phase.SUMMARY):
            draw_skeleton(frame, lm_dict)

    # Live score = already-banked + current exercise's running score
    live_score = banked_score + exercises[current_ex].score

    # ── Phase dispatch ────────────────────────────────────────────

    if phase == Phase.SUMMARY:
        draw_summary_screen(frame, banked_score)
        draw_top_hud(frame, now, banked_score)

    elif phase in (Phase.REST_EXERCISE, Phase.REST_SET):
        # Which exercise comes next?
        nxt_pos = queue_pos + 1
        if nxt_pos < len(FULL_QUEUE):
            n_set, n_ex = FULL_QUEUE[nxt_pos]
        else:
            n_set, n_ex = current_set, current_ex

        # Demo plays the NEXT exercise during rest (set by advance_phase)
        df = demo.get_frame()
        demo.overlay(frame, df,
                     label=f"NEXT: {EXERCISE_NAMES.get(n_ex,'')}")

        draw_rest_screen(frame, now,
                         is_set_rest=(phase == Phase.REST_SET),
                         next_ex=n_ex, next_set=n_set)

        # Queue shows upcoming items starting from the next exercise
        draw_queue_strip(frame, nxt_pos, nxt_pos)
        draw_top_hud(frame, now, live_score)

        if now >= phase_end:
            advance_phase()

    else:  # EXERCISE or CALIBRATING
        ex_obj = exercises[current_ex]
        _, fb_text = ex_obj.update(frame, lm_dict, now)

        # Demo shows current exercise
        df = demo.get_frame()
        demo.overlay(frame, df,
                     label=f"DEMO: {EXERCISE_NAMES.get(current_ex,'')}")

        draw_queue_strip(frame, queue_pos, queue_pos)
        draw_top_hud(frame, now, live_score)
        draw_bottom_hud(frame, fb_text, ex_obj.fb_cur)

        # Exercise timer expired
        if phase == Phase.EXERCISE and now >= phase_end:
            advance_phase()

        # Calibration done → switch to EXERCISE phase immediately
        if phase == Phase.CALIBRATING and ex_obj.calibrated:
            phase     = Phase.EXERCISE
            phase_end = time.time() + EXERCISE_DURATION

    # ── Display ───────────────────────────────────────────────────
    cv2.imshow("Rehab Quest", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Cleanup ───────────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()
demo.release()
pose.close()

final = banked_score + exercises[current_ex].score
print(f"\n[INFO] Session ended.")
print(f"       Final Total Score : {final}")
for i, sc in enumerate(set_score_log):
    print(f"       Set {i+1} Score        : {sc}")
