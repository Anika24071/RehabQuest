import cv2
import mediapipe as mp
import numpy as np
import time
import math
import collections
from enum import Enum, auto
try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════
#  SESSION CONFIGURATION
# ══════════════════════════════════════════════════════════════════
TOTAL_SETS          = 3
EXERCISE_DURATION   = 120   # seconds each exercise runs
REST_EX_DURATION    = 10    # seconds rest between exercises
REST_SET_DURATION   = 30    # seconds rest between sets
CAL_FRAMES_NEEDED   = 50    # frames for leg-raise body calibration

EXERCISE_ORDER = ['hand_raise', 'wrist_circle', 'leg_raise']

EXERCISE_NAMES = {
    'hand_raise':   'Hand Raise',
    'wrist_circle': 'Wrist 360',
    'leg_raise':    'Leg Raise',
}
VIDEO_FILES = {
    'hand_raise':   'Hand_Raise.mp4',
    'wrist_circle': 'Wrist.mp4',
    'leg_raise':    'Leg_Raise.mp4',
}
QUEUE_COLORS = {
    'hand_raise':   (0,  210, 210),
    'wrist_circle': (80, 180, 255),
    'leg_raise':    (80, 255, 120),
}
QUEUE_ICONS = {
    'hand_raise':   'HR',
    'wrist_circle': 'W360',
    'leg_raise':    'LR',
}

# Audio asset filenames (same folder as this script)
AUDIO_LETGO     = 'Letso_go_audio.mp3'
AUDIO_COUNTDOWN = 'Countdown.mp3'
AUDIO_ENERGETIC = 'Energetic_Audio.mp3'
COUNTDOWN_TRIGGER_SECS = 4   # fire countdown this many seconds before exercise ends

# Wrist hand-selection (set at Phase.HAND_SELECT)
wrist_hand_mode = 'right'   # 'right' | 'left' | 'alternate'

# ══════════════════════════════════════════════════════════════════
#  UI LAYOUT CONSTANTS
# ══════════════════════════════════════════════════════════════════
TOP_HUD_H = 78    # top bar height in pixels
QUEUE_H   = 68    # queue strip height - anchored flush to bottom
FB_H      = 52    # feedback bar height - sits directly above queue
BOTTOM_H  = QUEUE_H + FB_H   # total bottom panel = 120 px

DEMO_W, DEMO_H = 240, 135   # demo video thumbnail size

# ══════════════════════════════════════════════════════════════════
#  AUDIO MANAGER
#  Fix notes vs previous version:
#   - pygame.mixer.music used for energetic loop (streams MP3, no
#     memory limit, guaranteed loop support)
#   - pygame.mixer.Sound used for short one-shot cues (let's go,
#     countdown) on a dedicated channel so they never cut each other
#   - pre_init buffer reduced to 512 to minimise playback latency
#   - Explicit frequency/format args for cross-platform reliability
#   - _countdown_done guard prevents countdown re-firing each frame
# ══════════════════════════════════════════════════════════════════
class AudioManager:
    def __init__(self):
        self.enabled         = False
        self.snd_letgo       = None
        self.snd_countdown   = None
        self.ch_cue          = None   # dedicated channel for short cues
        self._countdown_done = False

        if not _PYGAME_AVAILABLE:
            print("[WARN] pygame not installed — audio disabled.  Run: pip install pygame")
            return
        try:
            # 44100 Hz, signed 16-bit, stereo, 512-sample buffer
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            self.ch_cue = pygame.mixer.Channel(0)   # channel 0 for short cues

            # Short cues — load into memory as Sound objects
            self.snd_letgo     = self._load_sound(AUDIO_LETGO)
            self.snd_countdown = self._load_sound(AUDIO_COUNTDOWN)
            # Long energetic track — loaded via music (streaming, no size limit)
            self._load_music(AUDIO_ENERGETIC)

            self.enabled = True
            print("[INFO] Audio system ready")
        except Exception as exc:
            print(f"[WARN] Audio disabled: {exc}")

    def _load_sound(self, path):
        try:
            snd = pygame.mixer.Sound(path)
            print(f"[INFO] Loaded sound: {path}")
            return snd
        except Exception as exc:
            print(f"[WARN] Could not load {path}: {exc}")
            return None

    def _load_music(self, path):
        try:
            pygame.mixer.music.load(path)
            print(f"[INFO] Loaded music: {path}")
        except Exception as exc:
            print(f"[WARN] Could not load music {path}: {exc}")

    # ── Public API ───────────────────────────────────────────────
    def play_lets_go(self):
        """Motivational cue at exercise start."""
        if not self.enabled or self.snd_letgo is None: return
        self._countdown_done = False   # reset for the new exercise
        self.ch_cue.stop()
        self.ch_cue.play(self.snd_letgo)

    def maybe_play_countdown(self, remaining_secs):
        """Call every frame during EXERCISE — fires countdown once when timer hits threshold."""
        if not self.enabled or self._countdown_done: return
        if self.snd_countdown is None: return
        if remaining_secs <= COUNTDOWN_TRIGGER_SECS:
            self._countdown_done = True
            self.ch_cue.stop()
            self.ch_cue.play(self.snd_countdown)

    def start_rest_audio(self):
        """Loop energetic music for the rest period."""
        if not self.enabled: return
        try:
            pygame.mixer.music.play(-1)   # -1 = loop indefinitely
        except Exception as exc:
            print(f"[WARN] Could not play rest music: {exc}")

    def stop_rest_audio(self):
        """Stop rest music when rest period ends."""
        if not self.enabled: return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def stop_all(self):
        """Hard stop everything — called on session end."""
        if not self.enabled: return
        try:
            self.ch_cue.stop()
            pygame.mixer.music.stop()
        except Exception:
            pass

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

# Mirror-aware landmark IDs (cv2.flip mirrors: screen-right = MP LEFT)
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
print(f"[INFO] Camera: {W}x{H}")

# ══════════════════════════════════════════════════════════════════
#  APPLE SPRITE  (Apple.png — case-sensitive filename)
# ══════════════════════════════════════════════════════════════════
_apple_img  = None   # resized BGR sprite
_apple_mask = None   # alpha mask (0-255) or None for fully opaque

def _load_apple_sprite(radius: int):
    """
    Load Apple.png (with alpha channel if present), resize to the apple
    circle diameter, and cache into module-level _apple_img / _apple_mask.
    Falls back silently so ExHandRaise draws a plain circle when missing.
    """
    global _apple_img, _apple_mask
    raw = cv2.imread('Apple.png', cv2.IMREAD_UNCHANGED)
    if raw is None:
        print("[WARN] Apple.png not found - will draw fallback circle for apple")
        return
    side = radius * 2
    resized = cv2.resize(raw, (side, side), interpolation=cv2.INTER_AREA)
    if resized.ndim == 3 and resized.shape[2] == 4:
        _apple_img  = resized[:, :, :3]   # BGR channels
        _apple_mask = resized[:, :,  3]   # alpha  0-255
    else:
        _apple_img  = resized             # BGR only (no alpha)
        _apple_mask = None                # treat as fully opaque
    print("[INFO] Apple.png loaded successfully")

def _draw_apple_sprite(frame, cx: int, cy: int, radius: int):
    """Alpha-composite the cached apple sprite centred at (cx, cy)."""
    if _apple_img is None:
        return   # sprite not loaded; caller draws the fallback circle
    side = radius * 2
    x0 = cx - radius; y0 = cy - radius
    x1 = x0 + side;   y1 = y0 + side
    # Clamp crop to frame bounds
    fx0 = max(x0, 0); fy0 = max(y0, 0)
    fx1 = min(x1, W); fy1 = min(y1, H)
    sx0 = fx0 - x0;   sy0 = fy0 - y0
    sx1 = sx0 + (fx1 - fx0); sy1 = sy0 + (fy1 - fy0)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    sprite_crop = _apple_img[sy0:sy1, sx0:sx1]
    frame_crop  = frame[fy0:fy1, fx0:fx1]
    if _apple_mask is not None:
        alpha  = _apple_mask[sy0:sy1, sx0:sx1].astype(np.float32) / 255.0
        alpha3 = np.stack([alpha, alpha, alpha], axis=2)
        frame[fy0:fy1, fx0:fx1] = (
            sprite_crop.astype(np.float32) * alpha3 +
            frame_crop.astype(np.float32)  * (1.0 - alpha3)
        ).astype(np.uint8)
    else:
        frame[fy0:fy1, fx0:fx1] = sprite_crop

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
    (SCREEN_LEFT_SHOULDER,  SCREEN_RIGHT_SHOULDER, (220,220,240), 3),
    (SCREEN_LEFT_SHOULDER,  SCREEN_LEFT_HIP,       (200,200,230), 3),
    (SCREEN_RIGHT_SHOULDER, SCREEN_RIGHT_HIP,      (200,200,230), 3),
    (SCREEN_LEFT_HIP,       SCREEN_RIGHT_HIP,      (200,200,230), 3),
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
        jx = int(lm_dict[jid][0]*W); jy = int(lm_dict[jid][1]*H)
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
    for cx, cy in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
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

def draw_divider(img, y, col=(0,150,150), alpha=0.9):
    ov = img.copy()
    cv2.line(ov, (0,y), (W,y), col, 1)
    cv2.addWeighted(ov, alpha, img, 1-alpha, 0, img)

# ══════════════════════════════════════════════════════════════════
#  DEMO VIDEO PLAYER
# ══════════════════════════════════════════════════════════════════
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
                print(f"[WARN] Demo not found: {path}")

    def set_exercise(self, key):
        self.current = key

    def get_frame(self):
        if not self.current or self.current not in self.caps: return None
        c = self.caps[self.current]
        ret, frm = c.read()
        if not ret:
            c.set(cv2.CAP_PROP_POS_FRAMES, 0); ret, frm = c.read()
        return cv2.resize(frm, (DEMO_W, DEMO_H)) if ret else None

    def overlay(self, frame, demo_frm, label="DEMO"):
        PAD   = 4; X0 = 10; Y0 = TOP_HUD_H + 8; LBL_H = 22
        bx1 = X0-3; by1 = Y0-3
        bx2 = X0+PAD+DEMO_W+PAD+3; by2 = Y0+LBL_H+PAD+DEMO_H+PAD+3
        cv2.rectangle(frame,(bx1-1,by1-1),(bx2+1,by2+1),(0,155,140),1,cv2.LINE_AA)
        rounded_rect(frame, bx1, by1, bx2, by2, 6, (8,28,28), alpha=0.96)
        rounded_rect(frame, bx1, by1, bx2, by1+LBL_H+2, 6, (0,55,52), alpha=0.97)
        put_text(frame, label, X0+PAD, Y0+LBL_H-4, 0.40, (0,220,185), 1)
        vy = Y0+LBL_H+PAD
        if demo_frm is not None:
            frame[vy:vy+DEMO_H, X0+PAD:X0+PAD+DEMO_W] = demo_frm
            cv2.rectangle(frame,(X0+PAD,vy),(X0+PAD+DEMO_W,vy+DEMO_H),(0,175,140),1)
        else:
            cv2.rectangle(frame,(X0+PAD,vy),(X0+PAD+DEMO_W,vy+DEMO_H),(28,40,48),-1)
            text_center(frame,"No Video",X0+PAD+DEMO_W//2,vy+DEMO_H//2+8,0.45,(80,95,108),1)

    def release(self):
        for c in self.caps.values(): c.release()

# ══════════════════════════════════════════════════════════════════
#  EXERCISE QUEUE BUILDER
# ══════════════════════════════════════════════════════════════════
def build_queue():
    q = []
    for s in range(1, TOTAL_SETS+1):
        for ex in EXERCISE_ORDER:
            q.append((s, ex))
    return q

FULL_QUEUE = build_queue()

# ══════════════════════════════════════════════════════════════════
#  PHASE ENUM
# ══════════════════════════════════════════════════════════════════
class Phase(Enum):
    HAND_SELECT   = auto()   # choose wrist hand before wrist exercise
    EXERCISE      = auto()   # active exercise running
    CALIBRATING   = auto()   # leg-raise body calibration
    REST_EXERCISE = auto()   # 10s between exercises
    REST_SET      = auto()   # 30s between sets
    SUMMARY       = auto()   # final results

# ══════════════════════════════════════════════════════════════════
#  EXERCISE CLASS — HAND RAISE
# ══════════════════════════════════════════════════════════════════
class ExHandRaise:
    APPLE_R = 42; PICK_D = 85; RESPAWN = 2.0; BURST_D = 0.4
    def __init__(self): self.reset()

    def reset(self):
        self.score=0; self.combo=0; self.visible=True; self.respawn=0.0
        self.burst_at=-99.0; self.trail=collections.deque(maxlen=20)
        self.particles=[]
        self.fb="Raise your RIGHT hand to grab the apple!"
        self.fb_col=np.array([255,255,255],dtype=float)
        self.fb_cur=np.array([255,255,255],dtype=float)

    def _fb(self,t,c): self.fb=t; self.fb_col=np.array(c,dtype=float)

    def _spawn(self,x,y,text,col):
        self.particles.append({'x':x,'y':y,'vy':-2.5,'text':text,
                               'color':col,'alpha':1.0,'birth':time.time()})

    def update(self, frame, lm, now):
        AX=W//2; AY=int(H*0.22)
        state=0; wp=None; prox=0.0; near=False
        if lm:
            rw=lm[SCREEN_RIGHT_WRIST]; rs=lm[SCREEN_RIGHT_SHOULDER]
            wp=(int(rw[0]*W),int(rw[1]*H)); self.trail.append(wp)
            state=1 if rw[1]<rs[1] else 0
            dist=math.hypot(wp[0]-AX,wp[1]-AY)
            prox=max(0.0,1.0-dist/250); near=dist<self.PICK_D
        delta=0
        if not self.visible:
            if now>=self.respawn: self.visible=True; self.combo=0; self._fb("New apple! Raise your hand!",(200,255,200))
        else:
            if state==1 and near:
                self.visible=False; self.respawn=now+self.RESPAWN
                self.combo+=1; pts=10*self.combo; self.score+=pts; delta=pts
                self.burst_at=now
                lbl=f"+{pts}!" if self.combo==1 else f"+{pts}  x{self.combo} COMBO!"
                self._spawn(AX-80,AY-60,lbl,(80,255,80))
                self._fb(f"Got it!  +{pts} pts!"+("  COMBO!" if self.combo>1 else ""),(80,255,80))
            elif state==1: self._fb("Almost there!  Reach for the apple!",(100,220,255))
            else: self._fb("Raise your hand higher!",(80,100,255))
        pts_t=list(self.trail)
        for i in range(1,len(pts_t)):
            al=i/len(pts_t); r2=max(2,int(al*8)); col=(0,int(al*255),int(al*200))
            cv2.circle(frame,pts_t[i],r2,(0,0,0),-1,cv2.LINE_AA)
            cv2.circle(frame,pts_t[i],r2,col,-1,cv2.LINE_AA)
            if i>1:
                t2=(i-1)/len(pts_t)
                cv2.line(frame,pts_t[i-1],pts_t[i],(0,int(t2*255),int(t2*200)),r2,cv2.LINE_AA)
        bp=min(1.0,(now-self.burst_at)/self.BURST_D)
        if self.visible:
            rr=self.APPLE_R+22; rc=(0,255,80) if prox>0.7 else (0,200,255)
            off=int(now*40)%30
            for i in range(12):
                a1=(30*i+off)%360
                cv2.ellipse(frame,(AX,AY),(rr,rr),0,a1,a1+14,rc,3,cv2.LINE_AA)
            if prox>0.05: cv2.ellipse(frame,(AX,AY),(rr+8,rr+8),-90,0,int(360*prox),(0,255,120),4,cv2.LINE_AA)
            # Draw Apple.png sprite if loaded, otherwise draw the fallback circle
            if _apple_img is not None:
                _draw_apple_sprite(frame, AX, AY, self.APPLE_R)
            else:
                cv2.circle(frame,(AX,AY),self.APPLE_R,(20,20,200),-1,cv2.LINE_AA)
                cv2.circle(frame,(AX,AY),self.APPLE_R,(0,0,120),2,cv2.LINE_AA)
                cv2.line(frame,(AX,AY-self.APPLE_R),(AX+7,AY-self.APPLE_R-15),(0,100,0),3,cv2.LINE_AA)
        else:
            if bp<1.0:
                rv=int(self.APPLE_R*(1+bp*3)); ov2=frame.copy()
                cv2.circle(ov2,(AX,AY),rv,(80,255,80),-1,cv2.LINE_AA)
                cv2.addWeighted(ov2,(1-bp)*0.5,frame,1-(1-bp)*0.5,0,frame)
            cv2.circle(frame,(AX,AY),self.APPLE_R+10,(80,80,80),2,cv2.LINE_AA)
            secs=max(0,self.respawn-now)
            text_center(frame,f"{secs:.1f}s",AX,AY+8,0.58,(160,160,160),1)
        if wp and near and self.visible:
            cx2,cy2=wp
            cv2.line(frame,(cx2-20,cy2),(cx2+20,cy2),(0,255,80),2,cv2.LINE_AA)
            cv2.line(frame,(cx2,cy2-20),(cx2,cy2+20),(0,255,80),2,cv2.LINE_AA)
            cv2.circle(frame,wp,22,(0,255,80),2,cv2.LINE_AA)
        alive=[]
        for p in self.particles:
            age=now-p['birth']
            if age>1.5: continue
            p['y']+=p['vy']; p['alpha']=max(0,1.0-age/1.2)
            c2=tuple(int(c*p['alpha']) for c in p['color'])
            cv2.putText(frame,p['text'],(int(p['x'])+2,int(p['y'])+2),cv2.FONT_HERSHEY_DUPLEX,1.1,(0,0,0),4,cv2.LINE_AA)
            cv2.putText(frame,p['text'],(int(p['x']),int(p['y'])),cv2.FONT_HERSHEY_DUPLEX,1.1,c2,2,cv2.LINE_AA)
            alive.append(p)
        self.particles[:]=alive
        self.fb_cur+=(self.fb_col-self.fb_cur)*0.12
        return delta, self.fb

# ══════════════════════════════════════════════════════════════════
#  EXERCISE CLASS — WRIST 360  (hand-aware)
# ══════════════════════════════════════════════════════════════════
class ExWristCircle:
    GUIDE_R = 90

    def __init__(self, hand_mode='right'):
        self.hand_mode = hand_mode
        self.reset()

    def set_hand_mode(self, mode):
        self.hand_mode = mode

    def reset(self):
        self.score=0; self.reps=0; self.trail=collections.deque(maxlen=80)
        self.prev_ang=None; self.ang_sum=0.0; self.particles=[]
        self.alt_side='right'; self.alt_reps=0
        self.fb=self._default_fb()
        self.fb_col=np.array([255,255,200],dtype=float)
        self.fb_cur=np.array([255,255,200],dtype=float)

    def _default_fb(self):
        lbl = self._active_label() if hasattr(self,'hand_mode') else 'RIGHT'
        return f"Move your {lbl} wrist in a full 360 circle!"

    def _active_wrist_id(self):
        if self.hand_mode=='right': return SCREEN_RIGHT_WRIST
        if self.hand_mode=='left':  return SCREEN_LEFT_WRIST
        return SCREEN_RIGHT_WRIST if self.alt_side=='right' else SCREEN_LEFT_WRIST

    def _active_label(self):
        if self.hand_mode=='right':  return 'RIGHT'
        if self.hand_mode=='left':   return 'LEFT'
        return self.alt_side.upper()

    def _fb(self,t,c): self.fb=t; self.fb_col=np.array(c,dtype=float)

    def _spawn(self,x,y,text,col):
        self.particles.append({'x':x,'y':y,'vy':-2.5,'text':text,
                               'color':col,'alpha':1.0,'birth':time.time()})

    def update(self, frame, lm, now):
        GX=W//2; GY=H//2
        wp=None; prox=0.0; delta=0
        wrist_id=self._active_wrist_id(); lbl=self._active_label()
        if lm and wrist_id in lm:
            rw=lm[wrist_id]; wp=(int(rw[0]*W),int(rw[1]*H))
            self.trail.append(wp)
            d2c=math.hypot(wp[0]-GX,wp[1]-GY)
            prox=max(0.0,1.0-d2c/(self.GUIDE_R*2.5))
            ang=(math.degrees(math.atan2(wp[1]-GY,wp[0]-GX))+90)%360
            if self.prev_ang is not None:
                dlt=ang-self.prev_ang
                if dlt> 180: dlt-=360
                if dlt<-180: dlt+=360
                self.ang_sum+=dlt
            self.prev_ang=ang
            if abs(self.ang_sum)>300:
                self.score+=20; self.reps+=1; delta=20
                dl="CW" if self.ang_sum>0 else "CCW"
                self._spawn(GX-60,GY-60,f"{lbl}  {dl}  +20  Rep {self.reps}",(80,255,120))
                self._fb(f"Full Circle!  Rep {self.reps}  +20 pts!",(80,255,120))
                self.ang_sum=0.0; self.trail.clear()
                if self.hand_mode=='alternate':
                    self.alt_reps+=1
                    self.alt_side='left' if self.alt_side=='right' else 'right'
                    self.prev_ang=None; nxt=self.alt_side.upper()
                    self._fb(f"Nice!  Now switch to your {nxt} wrist!",(100,220,255))
            elif abs(self.ang_sum)>60:
                pct=min(100,int(abs(self.ang_sum)/300*100))
                self._fb(f"Keep going!  {pct}% complete",(100,220,255))
            else:
                self._fb(f"Move your {lbl} wrist along the circle!",(255,255,200))
            cv2.circle(frame,wp,18,(0,255,180),2,cv2.LINE_AA)
            cv2.circle(frame,wp,10,(0,255,180),-1,cv2.LINE_AA)
            if abs(d2c-self.GUIDE_R)<30:
                cv2.line(frame,(wp[0]-20,wp[1]),(wp[0]+20,wp[1]),(0,255,80),2,cv2.LINE_AA)
                cv2.line(frame,(wp[0],wp[1]-20),(wp[0],wp[1]+20),(0,255,80),2,cv2.LINE_AA)
        pts_t=list(self.trail)
        for i in range(1,len(pts_t)):
            t2=i/len(pts_t)
            cv2.line(frame,pts_t[i-1],pts_t[i],(0,int(255*t2),200),int(2+t2*3),cv2.LINE_AA)
        col=(0,255,80) if prox>0.7 else (0,200,255)
        cv2.circle(frame,(GX,GY),self.GUIDE_R,(40,40,70),2,cv2.LINE_AA)
        off=int(now*40)%30
        for i in range(12):
            a1=(30*i+off)%360
            cv2.ellipse(frame,(GX,GY),(self.GUIDE_R,self.GUIDE_R),0,a1,a1+14,col,3,cv2.LINE_AA)
        if prox>0.05:
            cv2.ellipse(frame,(GX,GY),(self.GUIDE_R+10,self.GUIDE_R+10),-90,0,int(360*prox),(0,255,120),4,cv2.LINE_AA)
        cv2.line(frame,(GX,GY-self.GUIDE_R-15),(GX,GY+self.GUIDE_R+15),(40,40,70),1,cv2.LINE_AA)
        cv2.line(frame,(GX-self.GUIDE_R-15,GY),(GX+self.GUIDE_R+15,GY),(40,40,70),1,cv2.LINE_AA)
        # Active hand badge
        hx=W-165; hy=TOP_HUD_H+14
        hand_col=(0,230,230) if lbl=='RIGHT' else (100,180,255)
        if self.hand_mode=='alternate': hand_col=(80,255,120)
        rounded_rect(frame,hx,hy,W-8,hy+44,8,(15,15,35),alpha=0.90)
        text_center(frame,lbl+" WRIST",(hx+W-8)//2,hy+28,0.52,hand_col,2)
        # Rotation arc
        r3x=W-58; r3y=H-BOTTOM_H-62
        cv2.circle(frame,(r3x,r3y),40,(30,30,50),8)
        pct3=min(1.0,abs(self.ang_sum)/300)
        if pct3>0:
            ac=(0,255,80) if pct3>0.8 else (0,200,255)
            cv2.ellipse(frame,(r3x,r3y),(40,40),-90,0,int(360*pct3),ac,8,cv2.LINE_AA)
        text_center(frame,"ROT",r3x,r3y+8,0.40,(120,140,170),1)
        alive=[]
        for p in self.particles:
            age=now-p['birth']
            if age>1.5: continue
            p['y']+=p['vy']; p['alpha']=max(0,1.0-age/1.2)
            c2=tuple(int(c*p['alpha']) for c in p['color'])
            cv2.putText(frame,p['text'],(int(p['x'])+2,int(p['y'])+2),cv2.FONT_HERSHEY_DUPLEX,1.0,(0,0,0),4,cv2.LINE_AA)
            cv2.putText(frame,p['text'],(int(p['x']),int(p['y'])),cv2.FONT_HERSHEY_DUPLEX,1.0,c2,2,cv2.LINE_AA)
            alive.append(p)
        self.particles[:]=alive
        self.fb_cur+=(self.fb_col-self.fb_cur)*0.12
        return delta, self.fb

# ══════════════════════════════════════════════════════════════════
#  EXERCISE CLASS — LEG RAISE
# ══════════════════════════════════════════════════════════════════
class ExLegRaise:
    LEG_D="D"; LEG_U="U"; HOLD_N=10; TGT_F=0.18; KA=0.25; BURST_D=0.5
    def __init__(self): self.reset()

    def reset(self):
        self.score=0; self.reps_r=0; self.reps_l=0; self.combo=0
        self.active="R"; self.leg_st={"R":self.LEG_D,"L":self.LEG_D}
        self.hold_c={"R":0,"L":0}; self.smk={"R":None,"L":None}
        self.burst_s=None; self.burst_t=-99.0; self.tfl=0.0
        self.particles=[]; self.fb="Stand straight: calibrating..."
        self.fb_col=np.array([255,255,150],dtype=float)
        self.fb_cur=np.array([255,255,150],dtype=float); self.fb_until=0.0
        self.cal_n=0; self.cal_buf={"rh":[],"lh":[],"ra":[],"la":[]}
        self.calibrated=False
        self.hip_y={"R":H*0.45,"L":H*0.45}; self.ank_y={"R":H*0.85,"L":H*0.85}

    def _fb(self,t,c): self.fb=t; self.fb_col=np.array(c,dtype=float)

    def _spawn(self,x,y,text,col):
        self.particles.append({'x':x,'y':y,'vy':-2.5,'text':text,
                               'color':col,'alpha':1.0,'birth':time.time()})

    def _tgt(self,side):
        leg=abs(self.ank_y[side]-self.hip_y[side])
        return int(self.hip_y[side]+leg*self.TGT_F)

    def update(self, frame, lm, now):
        if not lm:
            self._fb("No person detected - step back for full body view",(150,150,150))
            return 0, self.fb

        def px(lid):
            v=lm[lid]; return (int(v[0]*W),int(v[1]*H)), float(v[1]*H)

        rhp,rhy=px(SCREEN_RIGHT_HIP); lhp,lhy=px(SCREEN_LEFT_HIP)
        rkp,rky=px(SCREEN_RIGHT_KNEE); lkp,lky=px(SCREEN_LEFT_KNEE)
        rap,ray=px(SCREEN_RIGHT_ANKLE); lap,lay=px(SCREEN_LEFT_ANKLE)

        if not self.calibrated:
            self.cal_n+=1
            self.cal_buf["rh"].append(rhy); self.cal_buf["lh"].append(lhy)
            self.cal_buf["ra"].append(ray); self.cal_buf["la"].append(lay)
            pct=self.cal_n/CAL_FRAMES_NEEDED
            bx=(W-360)//2; by=H//2+10
            rounded_rect(frame,bx-24,by-60,bx+384,by+54,10,(10,10,25),0.86)
            cv2.line(frame,(bx-24,by-60),(bx+384,by-60),(0,180,180),2)
            text_center(frame,"Calibrating - stand straight, feet flat on floor",
                        W//2,by-28,0.65,(200,230,255),1)
            cv2.rectangle(frame,(bx,by+5),(bx+360,by+28),(25,25,45),-1)
            cv2.rectangle(frame,(bx,by+5),(bx+int(360*pct),by+28),(0,200,255),-1)
            cv2.rectangle(frame,(bx,by+5),(bx+360,by+28),(60,80,120),2)
            text_center(frame,f"{int(pct*100)}%",W//2,by+22,0.50,(180,220,255),1)
            if self.cal_n>=CAL_FRAMES_NEEDED:
                self.hip_y["R"]=float(np.mean(self.cal_buf["rh"]))
                self.hip_y["L"]=float(np.mean(self.cal_buf["lh"]))
                self.ank_y["R"]=float(np.mean(self.cal_buf["ra"]))
                self.ank_y["L"]=float(np.mean(self.cal_buf["la"]))
                self.calibrated=True
                self._fb("Ready!  Raise your RIGHT knee to the line!",(80,255,120))
                self.fb_until=now+3.0
            return 0, self.fb

        for side,ky in [("R",rky),("L",lky)]:
            if self.smk[side] is None: self.smk[side]=ky
            else: self.smk[side]=self.KA*ky+(1-self.KA)*self.smk[side]

        for side,acol,dcol,lbl in [
            ("R",(0,255,180),(40,70,60),"TARGET: Right Knee"),
            ("L",(0,180,255),(40,60,80),"TARGET: Left Knee"),
        ]:
            tgt=self._tgt(side); act=(self.active==side)
            col=acol if act else dcol
            if act and now<self.tfl:
                al=0.5+0.5*math.sin(now*14); col=tuple(int(c*al) for c in acol)
            if act:
                ov2=frame.copy()
                cv2.line(ov2,(0,tgt),(W,tgt),acol,12,cv2.LINE_AA)
                cv2.addWeighted(ov2,0.25,frame,0.75,0,frame)
            x=0
            while x<W:
                cv2.line(frame,(x,tgt),(min(x+22,W),tgt),col,3,cv2.LINE_AA); x+=32
            rounded_rect(frame,8,tgt-18,210,tgt+18,6,(10,10,22),0.75)
            put_text(frame,lbl,16,tgt+9,0.50,col,1)

        for side,hip,ank,kv,ax2,lbl2 in [
            ("R",self.hip_y["R"],self.ank_y["R"],self.smk["R"] or rky,W-70,"R"),
            ("L",self.hip_y["L"],self.ank_y["L"],self.smk["L"] or lky,W-165,"L"),
        ]:
            if self.active!=side: continue
            tgt=self._tgt(side); den=max(1,hip-tgt)
            pct=max(0,min(1.0,(hip-kv)/den)); ac=(0,255,120) if pct>=0.95 else (0,200,255)
            acy=H-BOTTOM_H-62
            cv2.circle(frame,(ax2,acy),38,(30,30,50),8)
            if pct>0: cv2.ellipse(frame,(ax2,acy),(38,38),-90,0,int(360*pct),ac,8,cv2.LINE_AA)
            text_center(frame,lbl2,ax2,acy+8,0.62,ac,2)

        if self.burst_s is not None:
            prog=min(1.0,(now-self.burst_t)/self.BURST_D)
            if prog<1.0:
                kpx=rkp if self.burst_s=="R" else lkp; ov3=frame.copy()
                cv2.circle(ov3,kpx,int(20+prog*60),(80,255,80),-1,cv2.LINE_AA)
                cv2.addWeighted(ov3,(1-prog)*0.35,frame,1-(1-prog)*0.35,0,frame)
            else: self.burst_s=None

        delta=0
        for side in ["R","L"]:
            if self.active!=side: continue
            tgt=self._tgt(side); ks=self.smk[side] or (rky if side=="R" else lky)
            above=ks<=tgt
            if self.leg_st[side]==self.LEG_D:
                if above:
                    self.hold_c[side]+=1
                    if self.hold_c[side]>=self.HOLD_N:
                        self.leg_st[side]=self.LEG_U; self.combo+=1
                        pts=10*self.combo; self.score+=pts; delta=pts
                        self.tfl=now+0.8; self.burst_s=side; self.burst_t=now
                        kpx=rkp if side=="R" else lkp
                        lbl3=f"+{pts}!" if self.combo==1 else f"+{pts}  x{self.combo}!"
                        self._spawn(kpx[0]-30,kpx[1]-50,lbl3,(80,255,80))
                        if side=="R": self.reps_r+=1
                        else: self.reps_l+=1
                        sn="Right" if side=="R" else "Left"
                        self._fb(f"{sn} leg UP!  +{pts}!"+(" COMBO!" if self.combo>1 else ""),(80,255,120))
                        self.fb_until=now+2.0
                else: self.hold_c[side]=0
            elif self.leg_st[side]==self.LEG_U:
                if not above:
                    self.leg_st[side]=self.LEG_D; self.hold_c[side]=0; self.combo=0
                    self.active="L" if side=="R" else "R"
                    sn2="LEFT" if self.active=="L" else "RIGHT"
                    self._fb(f"Good!  Now raise your {sn2} knee!",(100,220,255))
                    self.fb_until=now+2.0

        if now>self.fb_until:
            sn3="RIGHT" if self.active=="R" else "LEFT"
            self._fb(f"Raise your {sn3} knee to the dashed line!",(200,210,255))

        put_text(frame,f"R: {self.reps_r}   L: {self.reps_l}",264,48,0.78,(200,210,80),2)
        arrow=">>> RIGHT <<<" if self.active=="R" else ">>> LEFT <<<"
        acol2=(0,255,200) if self.active=="R" else (0,200,255)
        text_center(frame,arrow,W//2,TOP_HUD_H+28,0.80,acol2,2)

        alive=[]
        for p in self.particles:
            age=now-p['birth']
            if age>1.5: continue
            p['y']+=p['vy']; p['alpha']=max(0,1.0-age/1.2)
            c2=tuple(int(c*p['alpha']) for c in p['color'])
            cv2.putText(frame,p['text'],(int(p['x'])+2,int(p['y'])+2),cv2.FONT_HERSHEY_DUPLEX,1.1,(0,0,0),4,cv2.LINE_AA)
            cv2.putText(frame,p['text'],(int(p['x']),int(p['y'])),cv2.FONT_HERSHEY_DUPLEX,1.1,c2,2,cv2.LINE_AA)
            alive.append(p)
        self.particles[:]=alive
        self.fb_cur+=(self.fb_col-self.fb_cur)*0.12
        return delta, self.fb

# ══════════════════════════════════════════════════════════════════
#  INSTANTIATE OBJECTS
# ══════════════════════════════════════════════════════════════════
exercises: dict = {
    'hand_raise':   ExHandRaise(),
    'wrist_circle': ExWristCircle(hand_mode='right'),
    'leg_raise':    ExLegRaise(),
}

# Load apple sprite now that ExHandRaise.APPLE_R is defined
_load_apple_sprite(ExHandRaise.APPLE_R)

demo  = DemoPlayer()
audio = AudioManager()

# ══════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════
queue_pos               = 0
current_set, current_ex = FULL_QUEUE[0]
phase                   = Phase.EXERCISE
phase_end               = time.time() + EXERCISE_DURATION
banked_score            = 0
set_start_bank          = 0
set_score_log: list     = []

exercises[current_ex].reset()
reset_smoothing()
demo.set_exercise(current_ex)

if current_ex == 'wrist_circle':
    phase = Phase.HAND_SELECT; phase_end = time.time() + 9999
elif current_ex == 'leg_raise':
    phase = Phase.CALIBRATING; phase_end = time.time() + 9999
else:
    phase = Phase.EXERCISE; phase_end = time.time() + EXERCISE_DURATION
    audio.play_lets_go()

# ══════════════════════════════════════════════════════════════════
#  HAND SELECT SCREEN
# ══════════════════════════════════════════════════════════════════
_HAND_OPTIONS = [
    ('R', 'Right Hand',  'Injury or preference for one side',  (0,225,225)),
    ('L', 'Left Hand',   'Injury or preference for one side',  (80,180,255)),
    ('A', 'Alternate',   'Bilateral training, both hands',     (80,255,120)),
]

def draw_hand_select_screen(frame, now):
    ov=frame.copy()
    cv2.rectangle(ov,(0,0),(W,H),(4,5,14),-1)
    cv2.addWeighted(ov,0.68,frame,0.32,0,frame)

    cw,ch=620,400; cxr=W//2-cw//2; cyr=H//2-ch//2-10

    cv2.rectangle(frame,(cxr-2,cyr-2),(cxr+cw+2,cyr+ch+2),(0,155,155),1,cv2.LINE_AA)
    rounded_rect(frame,cxr,cyr,cxr+cw,cyr+ch,16,(10,12,28),alpha=0.97)

    # Header
    rounded_rect(frame,cxr,cyr,cxr+cw,cyr+56,16,(0,55,65),alpha=0.97)
    text_center(frame,"WRIST 360  -  SELECT HAND",W//2,cyr+36,0.85,(0,225,190),2)
    cv2.line(frame,(cxr+16,cyr+56),(cxr+cw-16,cyr+56),(0,120,120),1)

    text_center(frame,"Which hand would you like to exercise?",
                W//2,cyr+84,0.60,(175,185,215),1)

    btn_w=cw-70; btn_h=70; btn_x=cxr+35
    pulse=0.82+0.18*math.sin(now*3.0)

    for i,(key,label,hint,col) in enumerate(_HAND_OPTIONS):
        by=cyr+104+i*(btn_h+10)
        rounded_rect(frame,btn_x,by,btn_x+btn_w,by+btn_h,10,
                     tuple(c//7 for c in col),alpha=0.90)
        pc=tuple(int(c*pulse) for c in col)
        cv2.rectangle(frame,(btn_x,by),(btn_x+btn_w,by+btn_h),pc,1,cv2.LINE_AA)
        # Key badge
        rounded_rect(frame,btn_x+10,by+12,btn_x+56,by+btn_h-12,8,
                     tuple(c//3 for c in col),alpha=0.95)
        text_center(frame,key,btn_x+33,by+btn_h//2+9,0.92,col,2)
        # Labels
        put_text(frame,label,btn_x+68,by+30,0.72,(230,235,255),2)
        put_text(frame,hint, btn_x+68,by+56,0.44,(108,118,142),1)

    text_center(frame,"Press  R  /  L  /  A  on your keyboard to select",
                W//2,cyr+ch-18,0.58,(115,130,165),1)

# ══════════════════════════════════════════════════════════════════
#  TOP HUD BAR
# ══════════════════════════════════════════════════════════════════
def draw_top_hud(frame, now, live_score):
    rounded_rect(frame,0,0,W,TOP_HUD_H,0,(10,11,22),alpha=0.92)
    draw_divider(frame,TOP_HUD_H,col=(0,150,150))

    # Left: Score badge
    rounded_rect(frame,6,8,215,TOP_HUD_H-8,8,(12,26,28),alpha=0.88)
    put_text(frame,"SCORE",16,32,0.43,(0,175,148),1)
    put_text(frame,f"  {live_score}",16,63,1.05,(80,255,140),2)

    # Centre: Set / Exercise
    ex_name=EXERCISE_NAMES.get(current_ex,current_ex)
    ex_col=QUEUE_COLORS.get(current_ex,(200,200,255))
    text_center(frame,f"SET {current_set} / {TOTAL_SETS}",W//2,28,0.50,(135,150,185),1)
    text_center(frame,ex_name,W//2,60,0.82,ex_col,2)

    # Right: Timer badge
    rem=max(0,phase_end-now)
    if phase==Phase.EXERCISE:
        if rem>30: tc=(0,225,130)
        elif rem>10: tc=(0,200,255)
        else:
            pulse=0.55+0.45*math.sin(now*7)
            tc=tuple(int(c*pulse) for c in (170,80,255))
        mm=int(rem)//60; ss=int(rem)%60; tt=f"  {mm}:{ss:02d}  "
    elif phase==Phase.CALIBRATING:
        tc=(255,242,90); tt="  CAL  "
    elif phase in (Phase.REST_EXERCISE,Phase.REST_SET):
        tc=(255,168,50); tt=f"  {int(rem)+1}s  "
    elif phase==Phase.HAND_SELECT:
        tc=(0,210,195); tt="  SELECT  "
    else:
        tc=(220,220,220); tt=""

    (tw,_),_=cv2.getTextSize(tt,cv2.FONT_HERSHEY_DUPLEX,0.95,2)
    rx1=W-tw-34
    rounded_rect(frame,rx1,8,W-6,TOP_HUD_H-8,8,(18,18,42),alpha=0.90)
    put_text(frame,"TIME",rx1+10,30,0.40,(95,115,155),1)
    put_text(frame,tt,rx1+2,62,0.95,tc,2)

# ══════════════════════════════════════════════════════════════════
#  BOTTOM FEEDBACK BAR  (anchored flush above queue)
# ══════════════════════════════════════════════════════════════════
def draw_bottom_hud(frame, fb_text, fb_cur):
    FB_Y=H-BOTTOM_H  # top edge of feedback bar
    FB_B=H-QUEUE_H   # bottom edge = top of queue
    rounded_rect(frame,0,FB_Y,W,FB_B,0,(10,10,20),alpha=0.84)
    draw_divider(frame,FB_Y,col=(0,118,118))
    col=tuple(int(c) for c in fb_cur)
    text_center(frame,fb_text,W//2,FB_Y+FB_H//2+9,0.72,col,2)

# ══════════════════════════════════════════════════════════════════
#  QUEUE STRIP  (anchored flush to screen bottom, no gap)
# ══════════════════════════════════════════════════════════════════
def draw_queue_strip(frame, view_start, active_idx):
    QY    = H - QUEUE_H   # top edge — fills exactly to H
    CARD_W = 152
    CARD_H = QUEUE_H - 12
    LABEL_X = 78

    # Full-width background down to H
    rounded_rect(frame, 0, QY, W, H, 0, (7,8,20), alpha=0.92)
    draw_divider(frame, QY, col=(0,128,128))

    # "QUEUE" label
    rounded_rect(frame,5,QY+7,70,H-7,6,(0,48,54),alpha=0.92)
    text_center(frame,"QUEUE",37,QY+QUEUE_H//2+7,0.38,(0,185,168),1)

    items = FULL_QUEUE[view_start: view_start+6]

    for i, (s_num, ex_key) in enumerate(items):
        idx       = view_start + i
        is_active = (idx == active_idx)
        cx        = LABEL_X + 6 + i*(CARD_W+5)
        cy        = QY + 6

        base_col = QUEUE_COLORS.get(ex_key,(150,150,150))
        icon     = QUEUE_ICONS.get(ex_key,'?')
        name     = EXERCISE_NAMES.get(ex_key,ex_key)

        if is_active:
            fill   = tuple(c//3 for c in base_col)
            border = base_col
            txt    = (255,255,255)
            alp    = 0.94
            # Active glow
            cv2.rectangle(frame,(cx-1,cy-1),(cx+CARD_W+1,cy+CARD_H+1),base_col,1,cv2.LINE_AA)
        else:
            fill   = (13,13,25)
            border = tuple(c//7 for c in base_col)
            txt    = (80,90,108)
            alp    = 0.56

        rounded_rect(frame,cx,cy,cx+CARD_W,cy+CARD_H,7,fill,alpha=alp)
        cv2.rectangle(frame,(cx,cy),(cx+CARD_W,cy+CARD_H),border,1)

        # Set badge
        put_text(frame,f"S{s_num}",  cx+6, cy+17,0.37, base_col if is_active else border,1)
        # Icon
        put_text(frame,icon,         cx+6, cy+36,0.38, base_col if is_active else border,1)
        # Exercise name
        put_text(frame,name[:13],    cx+50,cy+CARD_H-7,0.40,txt,1)

        # Upward pointer arrow on active card
        if is_active:
            ax=cx+CARD_W//2
            pts_arr=np.array([[ax,cy-2],[ax-6,cy-10],[ax+6,cy-10]],np.int32)
            cv2.fillPoly(frame,[pts_arr],base_col)

# ══════════════════════════════════════════════════════════════════
#  REST SCREEN OVERLAY
# ══════════════════════════════════════════════════════════════════
def draw_rest_screen(frame, now, is_set_rest, next_ex, next_set):
    rem=max(0,phase_end-now)
    ov=frame.copy()
    cv2.rectangle(ov,(0,0),(W,H),(4,5,14),-1)
    cv2.addWeighted(ov,0.58,frame,0.42,0,frame)

    cw,ch=560,290; cxr=W//2-cw//2
    # Position card so it sits clearly above the bottom panel
    cyr=H//2-ch//2-BOTTOM_H//4

    if is_set_rest:
        title=f"Set {current_set} Complete!  Great Job!"; sub=f"Prepare for Set {next_set}  -  {EXERCISE_NAMES.get(next_ex,'')}"; tc=(80,255,130); border=(0,195,130)
    else:
        title="Rest"; sub=f"Coming up:  {EXERCISE_NAMES.get(next_ex,'')}  (Set {next_set})"; tc=(0,210,255); border=(0,165,220)

    cv2.rectangle(frame,(cxr-2,cyr-2),(cxr+cw+2,cyr+ch+2),border,1,cv2.LINE_AA)
    rounded_rect(frame,cxr,cyr,cxr+cw,cyr+ch,16,(11,12,28),alpha=0.96)
    rounded_rect(frame,cxr,cyr,cxr+cw,cyr+52,16,tuple(c//5 for c in border),alpha=0.97)
    text_center(frame,title,W//2,cyr+34,0.88,tc,2)
    cv2.line(frame,(cxr+16,cyr+52),(cxr+cw-16,cyr+52),(0,115,115),1)
    text_center(frame,sub,W//2,cyr+86,0.63,(178,188,228),1)

    c_str=str(int(rem)+1)
    (cw2,_),_=cv2.getTextSize(c_str,cv2.FONT_HERSHEY_DUPLEX,3.4,6)
    put_text(frame,c_str,W//2-cw2//2,cyr+195,3.4,(255,255,255),6)
    text_center(frame,"seconds",W//2,cyr+252,0.62,(138,142,192),1)

# ══════════════════════════════════════════════════════════════════
#  SUMMARY SCREEN
# ══════════════════════════════════════════════════════════════════
def draw_summary_screen(frame, total):
    ov=frame.copy()
    cv2.rectangle(ov,(0,0),(W,H),(4,5,14),-1)
    cv2.addWeighted(ov,0.80,frame,0.20,0,frame)

    cw,ch=700,480; cx4=W//2-cw//2; cy4=H//2-ch//2
    cv2.rectangle(frame,(cx4-2,cy4-2),(cx4+cw+2,cy4+ch+2),(0,195,175),1,cv2.LINE_AA)
    rounded_rect(frame,cx4,cy4,cx4+cw,cy4+ch,20,(10,12,28),alpha=0.97)
    rounded_rect(frame,cx4,cy4,cx4+cw,cy4+62,20,(0,52,52),alpha=0.97)
    text_center(frame,"SESSION COMPLETE!",W//2,cy4+42,1.10,(80,255,130),3)
    cv2.line(frame,(cx4+20,cy4+62),(cx4+cw-20,cy4+62),(0,135,128),1)
    text_center(frame,f"TOTAL SCORE:  {total}",W//2,cy4+128,1.35,(255,220,70),4)
    cv2.line(frame,(cx4+40,cy4+148),(cx4+cw-40,cy4+148),(28,33,58),1)
    for i,sc in enumerate(set_score_log):
        text_center(frame,f"Set {i+1}  -  {sc} pts",W//2,cy4+190+i*50,0.88,(175,205,255),2)
    msg,mc=(
        ("Outstanding Performance!  Keep crushing it!",(80,255,130)) if total>500 else
        ("Great work!  You're making real progress!",  (100,220,255)) if total>200 else
        ("Good effort!  Keep practicing every day!",   (200,200,255))
    )
    cv2.line(frame,(cx4+40,cy4+356),(cx4+cw-40,cy4+356),(28,33,58),1)
    text_center(frame,msg,W//2,cy4+395,0.72,mc,2)
    text_center(frame,"Press  Q  to exit",W//2,cy4+444,0.58,(108,118,158),1)

# ══════════════════════════════════════════════════════════════════
#  PHASE ADVANCE
# ══════════════════════════════════════════════════════════════════
def advance_phase():
    global phase,phase_end,current_set,current_ex,queue_pos
    global banked_score,set_start_bank,set_score_log,wrist_hand_mode

    if phase in (Phase.EXERCISE,Phase.CALIBRATING):
        banked_score+=exercises[current_ex].score
        nxt=queue_pos+1
        if nxt>=len(FULL_QUEUE):
            set_score_log.append(banked_score-set_start_bank)
            audio.stop_all()
            phase=Phase.SUMMARY; return
        n_set,n_ex=FULL_QUEUE[nxt]
        if n_set>current_set:
            set_score_log.append(banked_score-set_start_bank)
            set_start_bank=banked_score
            phase=Phase.REST_SET; phase_end=time.time()+REST_SET_DURATION
        else:
            phase=Phase.REST_EXERCISE; phase_end=time.time()+REST_EX_DURATION
        demo.set_exercise(n_ex)
        audio.start_rest_audio()

    elif phase in (Phase.REST_EXERCISE,Phase.REST_SET):
        audio.stop_rest_audio()
        queue_pos+=1; current_set,current_ex=FULL_QUEUE[queue_pos]
        exercises[current_ex].reset(); reset_smoothing(); demo.set_exercise(current_ex)
        if current_ex=='wrist_circle':
            exercises['wrist_circle'].set_hand_mode(wrist_hand_mode)
            phase=Phase.HAND_SELECT; phase_end=time.time()+9999
        elif current_ex=='leg_raise':
            phase=Phase.CALIBRATING; phase_end=time.time()+9999
        else:
            phase=Phase.EXERCISE; phase_end=time.time()+EXERCISE_DURATION
            audio.play_lets_go()

    elif phase==Phase.HAND_SELECT:
        exercises['wrist_circle'].set_hand_mode(wrist_hand_mode)
        phase=Phase.EXERCISE; phase_end=time.time()+EXERCISE_DURATION
        audio.play_lets_go()

# ══════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════
print("[INFO] Rehab Quest v2 - Session Started.")
print("[INFO] Controls:  Q = quit  |  (hand-select screen)  R / L / A = hand choice")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    now   = time.time()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = pose.process(rgb)
    lm_dict: dict = {}
    if res.pose_landmarks:
        lm_dict = smooth_landmarks(res.pose_landmarks)
        if phase not in (Phase.REST_EXERCISE,Phase.REST_SET,Phase.SUMMARY,Phase.HAND_SELECT):
            draw_skeleton(frame, lm_dict)

    live_score = banked_score + exercises[current_ex].score

    # ── Phase dispatch ───────────────────────────────────────────
    if phase == Phase.HAND_SELECT:
        if res.pose_landmarks: draw_skeleton(frame, lm_dict)
        draw_hand_select_screen(frame, now)
        draw_top_hud(frame, now, live_score)

    elif phase == Phase.SUMMARY:
        draw_summary_screen(frame, banked_score)
        draw_top_hud(frame, now, banked_score)

    elif phase in (Phase.REST_EXERCISE, Phase.REST_SET):
        nxt_pos = queue_pos+1
        if nxt_pos < len(FULL_QUEUE): n_set,n_ex = FULL_QUEUE[nxt_pos]
        else: n_set,n_ex = current_set,current_ex

        df = demo.get_frame()
        demo.overlay(frame, df, label=f"NEXT: {EXERCISE_NAMES.get(n_ex,'')}")
        draw_rest_screen(frame, now, is_set_rest=(phase==Phase.REST_SET),
                         next_ex=n_ex, next_set=n_set)
        draw_queue_strip(frame, nxt_pos, nxt_pos)
        draw_top_hud(frame, now, live_score)
        if now >= phase_end: advance_phase()

    else:  # EXERCISE or CALIBRATING
        ex_obj = exercises[current_ex]
        _, fb_text = ex_obj.update(frame, lm_dict, now)
        df = demo.get_frame()
        demo.overlay(frame, df, label=f"DEMO: {EXERCISE_NAMES.get(current_ex,'')}")
        draw_queue_strip(frame, queue_pos, queue_pos)
        draw_top_hud(frame, now, live_score)
        draw_bottom_hud(frame, fb_text, ex_obj.fb_cur)
        if phase==Phase.EXERCISE:
            rem = phase_end - now
            audio.maybe_play_countdown(rem)
            if now>=phase_end: advance_phase()
        if phase==Phase.CALIBRATING and ex_obj.calibrated:
            phase=Phase.EXERCISE; phase_end=time.time()+EXERCISE_DURATION
            audio.play_lets_go()

    # ── Key handling ─────────────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break

    if phase == Phase.HAND_SELECT:
        if   key == ord('r'): wrist_hand_mode='right';    advance_phase()
        elif key == ord('l'): wrist_hand_mode='left';     advance_phase()
        elif key == ord('a'): wrist_hand_mode='alternate'; advance_phase()

    cv2.imshow("Rehab Quest", frame)

# ── Cleanup ───────────────────────────────────────────────────────
audio.stop_all()
cap.release(); cv2.destroyAllWindows(); demo.release(); pose.close()
final = banked_score + exercises[current_ex].score
print(f"\n[INFO] Session ended.  Final Score: {final}")
for i,sc in enumerate(set_score_log): print(f"       Set {i+1}: {sc} pts")