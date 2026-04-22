import cv2
import threading
import importlib.util
import os
import time
import sys
import numpy as np
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared state ──────────────────────────────────────────────────────────────
latest_frame = None
active_thread = None
running = False
latest_key = -1
thread_lock = threading.Lock()

# ── Pre-warm the webcam ONCE at startup ───────────────────────────────────────
# This is the key fix: opening cv2.VideoCapture takes 3-8s on Windows.
# We open it once here so it is ready instantly when an exercise starts.
print("[FASTAPI] Pre-warming camera...")
_shared_cap = cv2.VideoCapture(0)
if _shared_cap.isOpened():
    _shared_cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    _shared_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    _shared_cap.set(cv2.CAP_PROP_FPS, 30)
    print("[FASTAPI] Camera ready.")
else:
    print("[FASTAPI] WARNING: Could not open camera at startup.")

# Inject the pre-warmed cap into builtins so exercise scripts can find it
import builtins
builtins._SHARED_CAP = _shared_cap

# ── Intercept cv2.VideoCapture so scripts reuse the shared cam ────────────────
_original_VideoCapture = cv2.VideoCapture

class _FastCapture:
    """Wraps the already-open shared camera instead of reopening it."""
    def __init__(self, src, *args, **kwargs):
        if isinstance(src, int):
            # Webcam request → reuse shared cap
            self._cap = _shared_cap
            print(f"[FASTAPI] Script requested camera {src} → using shared cap")
        else:
            # File/video source → open normally
            self._cap = _original_VideoCapture(src, *args, **kwargs)

    def isOpened(self):           return self._cap.isOpened()
    def read(self):               return self._cap.read()
    def get(self, prop):          return self._cap.get(prop)
    def set(self, prop, val):     return self._cap.set(prop, val)
    def release(self):
        # Don't actually release the shared cap — just no-op for webcam
        if self._cap is not _shared_cap:
            self._cap.release()

cv2.VideoCapture = _FastCapture

# ── Intercept cv2.imshow / waitKey ───────────────────────────────────────────
original_imshow   = cv2.imshow
original_waitkey  = cv2.waitKey

def mock_imshow(title, frame):
    global latest_frame
    latest_frame = frame.copy()

def mock_waitkey(delay=0):
    global running, latest_key
    if not running:
        return ord('q')
    k = latest_key
    latest_key = -1
    return k

cv2.imshow   = mock_imshow
cv2.waitKey  = mock_waitkey

# ── Run exercise script in background thread ──────────────────────────────────
def run_script(script_path):
    global running
    print(f"[FASTAPI] Starting script: {script_path}")
    parent_dir = os.path.dirname(script_path)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    os.chdir(parent_dir)
    try:
        spec   = importlib.util.spec_from_file_location("exercise_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[FASTAPI] Script ended: {e}")
    finally:
        running = False
        print(f"[FASTAPI] Script {script_path} completed.")

# ── Placeholder frame (shown instantly before exercise script produces frames) ─
def _make_placeholder():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (18, 18, 28)
    cv2.putText(frame, 'Camera ready — starting exercise...',
                (60, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 100, 220), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Please stand in front of the camera',
                (90, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 80, 140), 1, cv2.LINE_AA)
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()

_placeholder_bytes = _make_placeholder()

# ── Routes ────────────────────────────────────────────────────────────────────
EXERCISE_MAP = {
    'shoulder_raise': 'Rehab_Hand_Raise.py',
    'wrist_rotation': 'Rehab_Wrist_Exercise.py',
    'leg_raise':      'Rehab_Leg_Raise.py',
    'full_body':      'Rehab_Quest_Session_v2.py',
}

@app.get("/start_stream")
def start_stream(exercise: str):
    global active_thread, running, latest_frame

    running = False  # signal old thread to stop
    with thread_lock:
        if active_thread and active_thread.is_alive():
            print("[FASTAPI] Waiting for previous script to stop...")
            active_thread.join(timeout=4.0)

        latest_frame = None
        running = True

        base_dir    = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'DIS_Rehab_Quest')
        script_file = EXERCISE_MAP.get(exercise, 'Rehab_Quest_Session_v2.py')
        script_path = os.path.abspath(os.path.join(base_dir, script_file))

        active_thread = threading.Thread(target=run_script, args=(script_path,), daemon=True)
        active_thread.start()

    return {"status": "started", "exercise": exercise}

@app.get("/stop_stream")
def stop_stream():
    global running
    running = False
    return {"status": "stopped"}

@app.get("/send_key")
def send_key(key: str):
    global latest_key
    if len(key) > 0:
        latest_key = ord(key.lower()[0])
    return {"status": "ok"}

def generate_frames():
    """Always yields frames — placeholder until exercise script starts producing real ones."""
    global latest_frame, running
    while True:
        frame = latest_frame
        if frame is None:
            # Yield placeholder immediately so browser connects right away
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                   _placeholder_bytes + b'\r\n')
            time.sleep(0.08)
        else:
            ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                       buf.tobytes() + b'\r\n')
            time.sleep(0.033)  # ~30 fps

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
