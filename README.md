---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Key Features](#-key-features)
- [Exercise & Workout System](#-exercise--workout-system)
- [User Flow](#-user-flow)
- [Design Concepts Integration](#-design-concepts-integration)
- [Tech Stack](#-tech-stack)
- [Folder Structure](#-folder-structure)
- [Installation & Setup](#-installation--setup)
- [Future Improvements](#-future-improvements)
- [Conclusion](#-conclusion)

---

## 🌟 Project Overview

**RehabQuest** is an AR-powered physiotherapy web application that transforms the often monotonous process of physical rehabilitation into an engaging, gamified experience. It is designed for patients recovering from musculoskeletal injuries — targeting shoulders, wrists, knees, and full-body mobility — who need consistent, structured exercise routines to recover effectively.

### The Problem

Traditional physiotherapy suffers from a well-documented engagement crisis:

- 🥱 **Low motivation** — Repetitive exercises quickly feel tedious without visible progress or feedback.
- 😶 **No real-time guidance** — Patients at home have no way to know if they're performing exercises correctly.
- 📉 **Poor adherence** — Studies show physiotherapy dropout rates exceed 50%, largely due to lack of engagement.
- 🏥 **Dependency on clinics** — Patients often need to visit a professional just to confirm correct form.

### The Solution

RehabQuest tackles all of these problems head-on by combining:

- 🎮 **Gamification** — Rep counting, session scoring, streaks, daily challenges, and saved workouts turn recovery into a rewarding game.
- 📷 **Real-time AR posture feedback** — A live camera feed with pose detection overlays landmarks on the user's body, counts reps automatically, and flags incorrect posture instantly.
- 🧭 **Structured programmes** — Injury-specific multi-week plans give users a clear recovery roadmap, reducing uncertainty.
- 📊 **Progress tracking** — Session history, weekly summaries, and streak counters provide measurable evidence of improvement, reinforcing motivation.

RehabQuest brings the physiotherapy clinic experience directly into your browser — no special hardware required beyond a standard webcam.

---

## ✨ Key Features

### 🦾 AR-Based Exercise Guidance
The live camera feed powered by OpenCV and MediaPipe draws real-time skeletal pose landmarks over the user's body. Visual animations and reference videos play alongside the camera view so users always know what the correct form looks like.

### 📐 Real-Time Posture Detection & Feedback
Joint angles are computed on every video frame. If a rep is performed correctly, the system registers it and encourages the user. If the posture deviates from the expected range, corrective feedback is displayed immediately — eliminating the guesswork of unsupervised home exercise.

### 🏆 Exercise Scoring System
Each completed rep and set contributes to a session score. Correct posture earns full points; near-correct form earns partial credit. This scoring loop keeps users engaged and striving for a perfect session.

### 🩺 Personalized Workout Programs Based on Injury
Upon login, users select their injury type (Shoulder, Wrist, Knee, or General). The Dashboard then **automatically filters and recommends** exercises relevant to their condition. The dedicated **Programmes** page offers structured multi-week plans:

| Programme | Target | Sessions | Duration |
|---|---|---|---|
| Shoulder Recovery Plan | Shoulder | 6 sessions | 2 weeks |
| Knee Rehab Series | Lower Body | 8 sessions | 3 weeks |
| Wrist & Hand Mobility | Wrist | 4 sessions | 1 week |
| Full Body Rehab | All | 12 sessions | 4 weeks |

### 📈 Progress Tracking & Activity History
The **Activity** page logs every completed session with date, exercise name, duration, and body focus area. Users can see their improvement over time, review past sessions, and monitor their weekly active minutes — all from the dashboard.

### 🔖 Saved Workouts
Users can bookmark any exercise with a single tap from the **Workouts** page. Saved exercises appear in the **Saved Workouts** section for quick retrieval, perfect for users who have a favourite routine.

### 🔥 Challenges & Engagement System
The **Challenges** page presents daily and weekly goals — streak challenges, rep milestones, and session targets — that push users beyond their comfort zone. A live 3-day streak counter on the dashboard provides a daily nudge to stay consistent.

### 🔊 Audio Cues
Three distinct audio tracks enhance the immersive exercise experience:
- 🎵 **Countdown audio** — Plays before a session begins, syncing the user mentally with the start.
- ⚡ **Rest-time energy boost** — Upbeat audio fires during rest intervals to keep motivation high and prevent users from disengaging.
- 🙌 **Motivational cue** — An enthusiastic "Let's go!" voice clip plays at key moments to celebrate effort.

### 🖥️ Smooth UI with Full Navigation
A persistent sidebar provides instant access to every section of the app:

| Route | Page | Purpose |
|---|---|---|
| `/dashboard` | Home | Stats, recommended exercises, recent sessions |
| `/workouts` | Workouts | Browse and filter all exercises |
| `/programmes` | Programmes | Injury-specific multi-week plans |
| `/saved` | Saved Workouts | Bookmarked exercises |
| `/activity` | Activity | Full session history |
| `/challenges` | Challenges | Daily/weekly goals |
| `/inbox` | Inbox | Notifications and reminders |

---

## 🏋️ Exercise & Workout System

This is the core of RehabQuest. Every exercise session is a tightly orchestrated pipeline of camera input, computer vision processing, and real-time UI feedback.

### Available Exercises

| Exercise | Script | Focus | Duration | Difficulty |
|---|---|---|---|---|
| Shoulder / Hand Raise | `Rehab_Hand_Raise.py` | Shoulder | 5 mins | Beginner |
| Wrist 360 Rotation | `Rehab_Wrist_Exercise.py` | Wrist | 5 mins | Intermediate |
| High Knee Leg Raises | `Rehab_Leg_Raise.py` | Knee / Lower Body | 8 mins | Beginner |
| Full Body Session | `Rehab_Quest_Session_v2.py` | Full Body | 20 mins | Advanced |

---

### How a Session Starts

1. The user selects an exercise from the Dashboard or Workouts page and taps **"Start"**.
2. The app navigates to a **Pre-Workout screen** showing the exercise summary, instructions, and a warm-up prompt.
3. Clicking **"Begin Session"** navigates to the **Active Session** page (`/session/:id`).
4. The **session timer starts immediately** in the browser — decoupled from camera initialisation so there's no perceived delay.
5. Simultaneously, the frontend calls `GET /start_stream?exercise=<id>` on the FastAPI backend.

### How the Camera / AR Tracking Works

The backend (`api.py`) implements a sophisticated camera pre-warming strategy:

- At **server startup**, the webcam is opened once (`cv2.VideoCapture(0)`) and kept alive in a shared object (`_shared_cap`). This eliminates the 3–8 second Windows camera initialisation delay that would otherwise occur on each exercise start.
- When an exercise script is requested, the backend **intercepts `cv2.VideoCapture`** so the script automatically reuses the already-open camera, bypassing any re-initialisation cost.
- The exercise Python script runs in a **background daemon thread**, leaving the FastAPI event loop free to serve the video stream.
- `cv2.imshow` and `cv2.waitKey` are **monkey-patched**: instead of opening a desktop window, `imshow` stores the latest frame in memory, and `waitKey` reads key presses forwarded from the browser via the `/send_key` endpoint.
- The frontend displays the live video by rendering an `<img>` tag that streams from `/video_feed` — a `multipart/x-mixed-replace` MJPEG stream served by the backend.
- While the exercise script is spinning up, a **placeholder frame** (dark screen with a "Camera ready" message) is served instantly so the browser never sees a blank connection.

### How Users Follow Visual Animations

- Each exercise script loads a **reference video** (`.mp4` file from `DIS_Rehab_Quest/`) and plays it in a panel alongside the live camera feed.
- Users can mirror their own movement against the animated guide, making it intuitive even for first-timers.
- MediaPipe Pose draws **real-time skeleton landmarks** (joints and connecting lines) over the live feed, making body positioning visually explicit.

### How Reps and Sets Are Counted

The exercise scripts implement a **finite-state machine** per exercise:

1. **Detection phase** — Pose landmarks are extracted from each frame using MediaPipe.
2. **Angle computation** — Key joint angles (e.g., elbow angle for arm raises, knee angle for leg raises) are calculated using vector mathematics on the landmark coordinates.
3. **State tracking** — The system alternates between `UP` and `DOWN` states based on whether the joint angle crosses defined thresholds. Each complete `DOWN → UP → DOWN` cycle increments the rep counter by one.
4. **Set tracking** — Once the target rep count for a set is reached, the system transitions to a **rest phase** and begins counting down the next set.

### How Feedback Is Given

| Situation | Feedback |
|---|---|
| Correct rep completed | Rep counter increments; visual confirmation shown |
| Posture out of range | On-screen corrective text message (e.g., "Raise arm higher") |
| Set completed | Rest timer appears with audio cue |
| Session complete | Score summary screen is displayed |

Feedback is rendered directly onto the OpenCV video frame as text overlays, which appear in the browser stream in real time.

### How Scoring Works

- A **base score** is awarded per correct rep.
- Completing a set without posture errors yields a **set bonus**.
- Finishing the full session awards a **completion bonus**.
- Scores are visible in the exercise overlay and are logged to the session history upon completion.

### How Rest Timers and Transitions Work

- After each set, a **countdown timer** appears on screen.
- The energetic rest-time audio (`Energetic Audio.mp3`) plays during this window to maintain arousal and prevent the user from switching off.
- Once the timer reaches zero, the next set begins automatically — the user does not need to interact with any UI element.
- The session ends when all sets across all exercises in the workout are complete, or when the user presses **"End Session"** manually.

### Example: Hand Raise Exercise

```
Target: 3 sets × 10 reps
Joint monitored: Shoulder (elbow-shoulder-hip angle)

Phase 1 (DOWN): Arm at side, angle ≈ 180°
Phase 2 (UP):   Arm raised to shoulder height, angle ≈ 90°

Threshold:
  - Rep registered when angle drops below 100° (arm up) then rises above 160° (arm down)
  - Feedback: "Lower arm fully" if DOWN phase angle stays above 160°

Rest: 15 seconds between sets
Audio: Countdown.mp3 before start, Energetic Audio.mp3 during rest
```

### Session Data Structure

```
Session
├── id           : exercise identifier (e.g., "shoulder_raise")
├── title        : human-readable name
├── sets         : number of sets (e.g., 3)
├── repsPerSet   : target reps per set (e.g., 10)
├── restInterval : seconds of rest between sets (e.g., 15)
└── duration     : actual time elapsed (recorded on end)
```

---

## 🗺️ User Flow

```
┌──────────────┐
│  Login Page  │  → Select injury type (Shoulder / Wrist / Knee / None)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Dashboard   │  → Personalised recommendations, stats, streak, recent sessions
└──────┬───────┘
       │  tap exercise card
       ▼
┌───────────────────┐
│  Pre-Workout Page │  → Exercise overview, tips, difficulty badge, "Begin" button
└──────┬────────────┘
       │  Begin Session
       ▼
┌────────────────────┐
│  Active Session    │  → Live AR camera stream + timer starts immediately
│  (Camera + Overlay)│  → Reference animation plays alongside live feed
└──────┬─────────────┘
       │  perform exercise
       ▼
┌──────────────────────────────┐
│  Real-Time Feedback Loop     │
│  ┌──────┐  correct  ┌──────┐ │
│  │ Rep  │ ────────► │ +1   │ │
│  │ Down │           │ rep  │ │
│  └──────┘           └──────┘ │
│      │ incorrect              │
│      ▼                        │
│  Corrective text overlay      │
└──────┬───────────────────────┘
       │  set complete
       ▼
┌─────────────────┐
│  Rest Timer     │  → Countdown + energetic audio
└──────┬──────────┘
       │  timer ends
       ▼
┌──────────────────┐
│  Next Set / End  │  → Repeat until all sets done
└──────┬───────────┘
       │  session ends
       ▼
┌──────────────────────┐
│  Session Summary     │  → Score, duration, reps completed
│  (logged to Activity)│
└──────┬───────────────┘
       │
       ▼
┌───────────────┐
│  Dashboard    │  → Updated streak, recent session visible
└───────────────┘
```

---

## 🧠 Design Concepts Integration

RehabQuest is not just a fitness app — it is grounded in established human-computer interaction theory. Each design decision maps to a concrete in-app feature.

---

### 1. Human Information Processing (Input → Processing → Output → Feedback)

> *The human mind processes information through sensory input, cognitive evaluation, and motor output.*

| HIP Stage | RehabQuest Implementation |
|---|---|
| **Input** | Camera captures user movement in real time |
| **Processing** | MediaPipe extracts pose landmarks; joint angles are computed per frame |
| **Output** | Rep count, posture status, and score are rendered onto the video stream |
| **Feedback** | Immediate corrective overlays close the loop — the user sees the result of their action within milliseconds |

This tight feedback loop — far faster than any human physiotherapist could provide — means users always know whether they are moving correctly, without waiting for an appointment.

---

### 2. Nathan Shedroff's Elements of Engagement

> *Engagement is sustained through identity, adaptivity, narrative, immersion, and flow.*

| Element | RehabQuest Implementation |
|---|---|
| **Identity** | User profile stores name and injury type; the dashboard greets the user personally ("Hello, Avni! 💪") |
| **Adaptivity** | Exercise recommendations dynamically filter based on the selected injury type, so every user sees a personalised home screen |
| **Narrative** | Structured programmes (e.g., "Shoulder Recovery Plan – Week 1 of 2") give the user a recovery story with a beginning, middle, and end |
| **Immersion** | Full-screen exercise mode removes all distractions; only the live feed, rep counter, and score are visible |
| **Flow** | Continuous rep counting, progressive set difficulty, rest timers, and session transitions maintain a steady state of challenge that matches the user's improving ability |

---

### 3. Memory and Attention

> *Cognitive load must be minimised; attention should be guided, not demanded.*

- **Minimal UI during exercise** — All sidebar navigation disappears during a session. Only essential elements (timer, rep count, end button) remain visible.
- **Visual instructions over text** — Reference `.mp4` videos demonstrate exercises visually; users do not need to read or remember textual step-by-step instructions.
- **Persistent AR cues** — Skeleton landmarks persist on every frame, providing a continuous spatial anchor so the user does not lose track of their body position.
- **Pre-Workout screen** — Key information (sets, reps, rest time) is presented before the session starts, offloading cognitive preparation to a lower-pressure context rather than mid-exercise.
- **Chunked information** — Stats on the dashboard (Sessions Done, Day Streak, This Week) are presented as three discrete numbers — well within working memory capacity.

---

### 4. Lazzaro's Four Keys to Emotion & Fun

> *Games are intrinsically motivating because they trigger emotional responses.*

| Emotion | Trigger | RehabQuest Implementation |
|---|---|---|
| **Fiero** (personal triumph) | Completing a difficult set | Score increment + completion bonus animation |
| **Naches** (reflected pride) | Seeing a growing streak | "3 Day Streak 🔥" counter on the dashboard |
| **Amusement** | Unexpected encouragement | "Let's go!" audio cue fires at motivational moments |
| **Wonder** | Seeing AR skeleton on your own body | Real-time pose landmark overlay creates a novel, engaging effect |

Corrective feedback is worded constructively (e.g., "Raise arm higher") rather than negatively, maintaining emotional positivity throughout the session.

---

### 5. Four Fun Model (Lazzaro)

> *Fun can be categorised as Hard Fun, Easy Fun, Serious Fun, and People Fun.*

| Fun Type | Description | RehabQuest Implementation |
|---|---|---|
| **Hard Fun** | Challenge, mastery, competition | Rep scoring, set challenges, daily/weekly challenge targets, difficulty badges (Beginner / Intermediate / Advanced) |
| **Easy Fun** | Curiosity, variety, exploration | Four distinct exercise types across different body areas; browse-and-filter Workouts page; bookmark favourite exercises |
| **Serious Fun** | Meaningful progress, real-world impact | Recovery programme tracking (2–4 week plans), session history, weekly minutes logged — users see genuine rehabilitation progress |
| **People Fun** | Social connection | (Foundation laid for future multiplayer challenges; Inbox page for notifications and community messages) |

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 19 | Component-based UI framework |
| React Router DOM | 7 | Client-side routing and navigation |
| Vite | 8 | Development server and bundler |
| Lucide React | 1.8 | Icon library (Bookmark, Play, Zap, etc.) |
| Vanilla CSS | — | Custom design system with CSS variables |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.100+ | REST API and MJPEG video stream server |
| Uvicorn | Latest | ASGI server to run FastAPI |
| OpenCV (cv2) | 4.x | Webcam capture and frame processing |
| MediaPipe | Latest | Real-time human pose landmark detection |
| NumPy | Latest | Joint angle vector mathematics |
| Python Threading | stdlib | Non-blocking background exercise script execution |

### AR / Pose Detection
- **MediaPipe Pose** — Detects 33 body landmarks at 30+ fps; provides normalised and world coordinates for accurate 3D joint angle computation.
- **OpenCV** — Handles video capture, frame rendering, text overlay, and JPEG encoding for the MJPEG stream.
- **MJPEG Streaming** — Frames are JPEG-encoded and served over HTTP as `multipart/x-mixed-replace`, making the live feed compatible with any browser `<img>` tag without WebSockets or WebRTC.

---

## 📁 Folder Structure

```
RehabQuest-main/
│
├── 📁 DIS_Rehab_Quest/              # Core AR exercise engine
│   ├── Rehab_Hand_Raise.py          # Shoulder/Hand Raise — pose detection & rep counting
│   ├── Rehab_Wrist_Exercise.py      # Wrist 360 Rotation — angle tracking
│   ├── Rehab_Leg_Raise.py           # High Knee Leg Raises — lower body tracking
│   ├── Rehab_Quest_Session.py       # Full body session (v1)
│   ├── Rehab_Quest_Session_v2.py    # Full body session (v2 — production)
│   ├── Rehab_Quest_Session_v3.py    # Full body session (v3 — experimental)
│   ├── Rehab_Quest_Hand_Mode.py     # Hand-only tracking mode
│   ├── Hand_Raise.mp4               # Reference animation: shoulder raise
│   ├── Wrist.mp4                    # Reference animation: wrist rotation
│   ├── Leg_Raise.mp4                # Reference animation: leg raise
│   ├── Countdown.mp3                # Pre-session countdown audio
│   ├── Energetic Audio.mp3          # Rest-time motivational audio
│   ├── Letso go audio.mp3           # "Let's go!" motivational cue
│   └── Apple.png                    # Visual asset
│
├── 📁 backend/
│   └── api.py                       # FastAPI server — camera management, routing, MJPEG stream
│
├── 📁 frontend/
│   ├── index.html                   # HTML entry point
│   ├── vite.config.js               # Vite build configuration
│   ├── package.json                 # npm dependencies
│   └── 📁 src/
│       ├── main.jsx                 # React app entry point
│       ├── App.jsx                  # Router and lazy-loaded page definitions
│       ├── AppContext.jsx           # Global state (injury type, saved workouts, sessions)
│       ├── index.css                # Base reset and global CSS
│       ├── ui.css                   # Full design system (variables, components, animations)
│       │
│       ├── 📁 components/
│       │   ├── Layout.jsx           # Wrapper: Sidebar + page content
│       │   ├── Sidebar.jsx          # Collapsible navigation sidebar
│       │   └── Navbar.jsx           # Top navigation bar
│       │
│       ├── 📁 pages/
│       │   ├── Login.jsx            # Login screen + injury type selection
│       │   ├── Dashboard.jsx        # Home: stats, recommended exercises, recent sessions
│       │   ├── PreWorkout.jsx       # Exercise preview before session start
│       │   ├── ActiveSession.jsx    # Live AR exercise session view
│       │   ├── Workouts.jsx         # Browse and filter all exercises
│       │   ├── Programmes.jsx       # Injury-specific multi-week plans
│       │   ├── SavedWorkouts.jsx    # Bookmarked exercises
│       │   ├── Activity.jsx         # Session history and progress log
│       │   ├── Challenges.jsx       # Daily/weekly challenge goals
│       │   └── Inbox.jsx            # Notifications and reminders
│       │
│       └── 📁 assets/
│           └── [exercise images]    # Thumbnail images for each exercise card
│
└── output.txt                       # Build/runtime output log
```

---

## ⚙️ Installation & Setup

### Prerequisites

Before you begin, ensure you have the following installed:

- [Node.js](https://nodejs.org/) (v18 or higher)
- [Python](https://python.org/) (v3.10 or higher)
- A working **webcam** connected to your system
- `pip` (Python package manager)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Anika24071/RehabQuest.git
cd RehabQuest
```

---

### Step 2 — Set Up the Backend

Navigate to the backend folder and install Python dependencies:

```bash
cd backend
pip install fastapi uvicorn opencv-python mediapipe numpy
```

> **Note:** MediaPipe may require additional system dependencies on Linux. On Windows and macOS, `pip install mediapipe` is sufficient.

Start the FastAPI backend server:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The backend will:
1. Pre-warm the webcam immediately on startup.
2. Expose the following endpoints:
   - `GET /start_stream?exercise=<id>` — Start an exercise script
   - `GET /stop_stream` — Stop the current exercise
   - `GET /video_feed` — MJPEG live stream
   - `GET /send_key?key=<char>` — Forward keyboard input to the exercise script

---

### Step 3 — Set Up the Frontend

Open a new terminal window and navigate to the frontend folder:

```bash
cd frontend
npm install
npm run dev
```

The development server will start, typically at:

```
http://localhost:5173
```

---

### Step 4 — Open the App

1. Open your browser and go to `http://localhost:5173`.
2. You will be redirected to the **Login page**.
3. Enter your name and select your **injury type**.
4. You'll land on the **Dashboard** — ready to start your first session!

> **Important:** Both the backend (`port 8000`) and frontend (`port 5173`) must be running simultaneously for the AR exercise streaming to work.

---

### Quick Reference

| Command | What it does |
|---|---|
| `uvicorn api:app --port 8000` | Starts the FastAPI backend |
| `npm run dev` | Starts the React/Vite frontend |
| `npm run build` | Builds the production bundle |
| `npm run lint` | Runs ESLint on frontend code |

---

## 🔮 Future Improvements

RehabQuest is built on a strong foundation with clear paths for expansion:

1. **🏋️ Expanded Exercise Library** — Add more body-specific exercises (ankle mobility, hip flexor stretches, cervical spine rotations) to cover a broader range of injuries and rehabilitation needs.

2. **🤖 AI-Powered Posture Correction** — Integrate a trained machine learning model (e.g., fine-tuned on physiotherapy datasets) to provide more nuanced, personalised form corrections beyond threshold-based angle detection.

3. **🌐 Multiplayer Challenges** — Enable friend challenges and leaderboards where users can compete on rep counts and session scores — introducing the "People Fun" quadrant of the Four Fun Model.

4. **⌚ Wearable Device Integration** — Connect with Apple Watch, Fitbit, or Garmin APIs to cross-reference heart rate, accelerometer, and HRV data with exercise performance for more accurate effort scoring.

5. **📱 Native Mobile App** — Package the frontend as a React Native or PWA app so users can access RehabQuest on their phone, expanding the camera placement options for different exercise types.

6. **👨‍⚕️ Physiotherapist Portal** — A separate dashboard where clinicians can assign custom programmes, review patient session logs, and adjust exercise prescriptions remotely.

7. **🧠 Adaptive Difficulty** — Automatically adjust rep targets, rest intervals, and exercise selection based on session performance history, ensuring the app grows with the user's improving fitness.

8. **🌍 Multi-Language Support** — Provide on-screen instructions and audio cues in multiple languages to make RehabQuest accessible to a global patient base.

---

## 🎯 Conclusion

RehabQuest demonstrates that physiotherapy does not have to be a chore. By combining **computer vision**, **real-time AR feedback**, **gamification mechanics**, and **evidence-based HCI design principles**, it transforms a clinically necessary but often abandoned routine into a daily habit that users are genuinely motivated to maintain.

The app is grounded in theory — Human Information Processing, Shedroff's Engagement Model, Lazzaro's Four Fun Keys — and every design decision maps directly to a feature that improves adherence, correctness, and motivation.

For patients recovering from shoulder, wrist, or knee injuries, RehabQuest is not just an app. It is a recovery companion — always available, always encouraging, and always watching to make sure you're moving the right way.

---

<div align="center">

**Built with 💙 and 🩷 — because recovery deserves better.**

*RehabQuest · AR Physiotherapy · Gamified Recovery*

</div>
