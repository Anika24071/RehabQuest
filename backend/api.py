import cv2
import threading
import importlib.util
import os
import time
import sys
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

latest_frame = None
active_thread = None
running = False
latest_key = -1
thread_lock = threading.Lock()

# Mock cv2.imshow to intercept frames gracefully
original_imshow = cv2.imshow
original_waitkey = cv2.waitKey

def mock_imshow(title, frame):
    global latest_frame
    latest_frame = frame.copy()

def mock_waitkey(delay=0):
    global running, latest_key
    # If running is False, tell the script 'q' was pressed so it breaks its loop
    if not running:
        return ord('q')
    
    k = latest_key
    latest_key = -1
    return k

cv2.imshow = mock_imshow
cv2.waitKey = mock_waitkey

def run_script(script_path):
    global running
    print(f"[FASTAPI] Starting backend script: {script_path}")
    
    parent_dir = os.path.dirname(script_path)
    os.chdir(parent_dir)
    sys.path.insert(0, parent_dir)
    
    try:
        spec = importlib.util.spec_from_file_location("exercise_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[FASTAPI] Script aborted or exited: {e}")
    finally:
        running = False
        print(f"[FASTAPI] Script {script_path} completed.")

@app.get("/start_stream")
def start_stream(exercise: str):
    global active_thread, running, latest_frame
    
    # Safely signal old thread to stop
    running = False
    
    with thread_lock:
        if active_thread and active_thread.is_alive():
            print("[FASTAPI] Waiting for previous script to release camera...")
            active_thread.join(timeout=5.0)
            
        latest_frame = None # clear previous
        running = True
        
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'DIS_Rehab_Quest')
        mapping = {
            'shoulder_raise': 'Rehab_Hand_Raise.py',
            'wrist_rotation': 'Rehab_Wrist_Exercise.py',
            'leg_raise': 'Rehab_Leg_Raise.py',
            'full_body': 'Rehab_Quest_Session_v2.py'
        }
        
        script_file = mapping.get(exercise, 'Rehab_Quest_Session_v2.py')
        script_path = os.path.abspath(os.path.join(base_dir, script_file))
        
        active_thread = threading.Thread(target=run_script, args=(script_path,))
        active_thread.daemon = True
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
    global latest_frame, running
    while True:
        if not running or latest_frame is None:
            time.sleep(0.05)
            continue
            
        ret, buffer = cv2.imencode('.jpg', latest_frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033) # max 30 fps

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
