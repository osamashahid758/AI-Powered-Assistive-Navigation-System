# AI-Powered Assistive Navigation System

> **MSc Dissertation Prototype** — Real-time obstacle detection and spatial awareness for visually impaired users, powered by YOLO11, OpenCV, and Streamlit.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/osamashahid758/build-a-complete-msc-dissertation-prototype/main/app.py)

---

## Try it Online — No Installation Needed

Click the badge above **or** open this URL in any browser:

```
https://share.streamlit.io/osamashahid758/build-a-complete-msc-dissertation-prototype/main/app.py
```

> The cloud version runs **Simulation** and **Upload video** modes.  
> Webcam requires running locally (see Quick Start below).

---

## Deploy Your Own Copy to Streamlit Cloud (Free)

Anyone can host their own live version in 3 steps — no server, no cost.

### Step 1 — Sign up
Go to **https://share.streamlit.io** and sign in with your GitHub account.

### Step 2 — Create new app
Click **"New app"** and fill in:

| Field | Value |
|---|---|
| Repository | `osamashahid758/build-a-complete-msc-dissertation-prototype` |
| Branch | `main` |
| Main file path | `app.py` |

Click **Deploy**. Streamlit Cloud installs all packages and starts the app automatically (takes ~3 minutes first time).

### Step 3 — Share the link
Once deployed you get a public URL like:
```
https://yourname-assistive-nav.streamlit.app
```
Share it with anyone — they open it in a browser, no Python needed.

---

---

## What This Project Does

This system uses a camera (webcam, phone camera, or video file) to **detect nearby obstacles in real time** and immediately tell the user where they are, how close they are, and which direction to avoid — through three feedback channels:

| Feedback | How it works |
|---|---|
| **Visual** | Annotated camera feed with colour-coded bounding boxes, zone lines, and distance labels |
| **Haptic (simulated)** | Left / right vibration motor intensity shown as progress bars |
| **Audio** | Spoken warnings: *"Stairs ahead — stop"*, *"Person on your left"* |

Everything runs in a **single browser dashboard** — no hardware needed beyond a camera and Python.

---

## How to Run — One Command on Any Device

**The only requirement is Python 3.10 or later.**

### Windows

```powershell
cd build-a-complete-msc-dissertation-prototype\outputs\assistive_navigation_system
python start.py
```

Or **double-click `start.bat`** inside that folder.

### macOS / Linux

```bash
cd build-a-complete-msc-dissertation-prototype/outputs/assistive_navigation_system
python3 start.py
```

Or run `bash start.sh`.

### What the launcher does automatically

```
[OK] Python 3.12.4
 >>> Creating virtual environment...
 >>> Installing packages (streamlit, opencv, ultralytics/YOLO11, plotly, pyttsx3)
     [2-4 minutes on first run only]
[OK] All packages installed.
[OK] Sample videos ready.

  Dashboard: http://localhost:8501
  Stop:      Ctrl+C
```

Open **http://localhost:8501** in your browser. Done.

> **No internet needed after first run.**  
> Tick **"Simulation detector"** in the sidebar to run fully offline with no camera.

---

## System Pipeline

```
Camera / Video / Simulation
        │
        ▼
  YOLO11 Detector          detects person, chair, table, door, stairs, vehicle, wall
        │
        ▼
  Navigation Engine        LEFT / CENTRE / RIGHT zone  +  distance estimate  +  warning level
        │
        ▼
  Feedback Layer           Haptic signals  |  Audio (TTS)  |  CSV log
        │
        ▼
  Streamlit Dashboard      Live feed  |  Metrics  |  270° polar chart  |  Session charts
```

---

## Dashboard — Three Tabs

### Live Navigation
The main operating view. Pick a source in the sidebar, press **Run navigation**.

- **Annotated feed** — bounding boxes coloured red (critical) → orange → yellow → green (low risk)
- **Status metrics** — FPS · Nearest obstacle · Detections · Avoidance direction
- **Warning banner** — 🔴 STOP / 🟠 Warning / 🔵 Caution / 🟢 Path clear
- **Haptic bars** — left and right motor intensity (0–100%)
- **270° sector chart** — polar chart showing the full environmental awareness arc
- **Session trend charts** — detection count and nearest distance over time

### Evaluation
Upload ground-truth and prediction CSVs (or use the bundled samples) to compute **Precision / Recall / F1** with an adjustable IoU threshold.

### About
Full system reference — component table, warning thresholds, haptic rules, dissertation scope.

---

## Input Sources

| Source | Description |
|---|---|
| **Simulation** | Synthetic animated scene — no camera needed, works fully offline |
| **Webcam** | Auto-scans all camera indices, shows a dropdown to pick (built-in, DroidCam, etc.) |
| **Video file** | Local `.mp4 / .avi / .mov / .mkv` — two sample videos included |
| **Upload video** | Drag and drop a video into the browser |

**DroidCam (phone as webcam):** Start the DroidCam desktop client and connect your phone first, then select `Webcam` in the sidebar — it will appear in the camera dropdown as `Camera 1` or `Camera 2`.

---

## Warning Levels

| Level | Distance | Box colour | Audio | Haptic |
|---|---|---|---|---|
| **Critical** | ≤ 1.2 m | Red | Yes | Yes |
| **High** | ≤ 2.0 m | Orange | Yes | Yes |
| **Medium** | ≤ 3.5 m | Yellow | Yes | Yes |
| **Low** | > 3.5 m | Green | No | No |

Centre-zone obstacles escalate one level earlier (−0.25 m bias) because the user is walking directly toward them.

---

## CLI Usage

Run these from inside `build-a-complete-msc-dissertation-prototype/outputs/assistive_navigation_system/` with the venv active.

```powershell
# Run on a sample video with display window (simulation detector)
python scripts\run_pipeline.py --source samples\left_person_right_vehicle.avi --mock --display

# Run on webcam index 1 (DroidCam) with audio
python scripts\run_pipeline.py --source 1 --audio

# Evaluate detection accuracy
python evaluation\evaluate_detections.py ^
  --ground-truth samples\sample_ground_truth.csv ^
  --predictions  samples\sample_predictions.csv

# Benchmark latency and FPS
python evaluation\benchmark.py --source samples\centre_stairs_door.avi --mock --frames 120
```

---

## Project Structure

```
build-a-complete-msc-dissertation-prototype/
└── outputs/
    └── assistive_navigation_system/   ← main project folder
        │
        ├── start.py / start.bat / start.sh   ONE-COMMAND LAUNCHER
        ├── requirements.txt
        ├── Dockerfile / docker-compose.yml
        │
        ├── ui/                Streamlit dashboard + chart components
        ├── vision/            YOLO11 detector, camera, annotation
        ├── navigation/        Zones, distance, risk, 270° awareness
        ├── feedback/          Haptics, audio (TTS), CSV logger
        ├── evaluation/        Precision/recall metrics, FPS benchmark
        ├── scripts/           CLI runner, sample video generator
        ├── samples/           Two synthetic AVI videos + CSV files
        ├── logs/              Runtime detection log (auto-created)
        ├── tests/             4 unit tests (pytest)
        └── docs/              Installation guide, user manual, UML
```

Full file-by-file breakdown in [`outputs/assistive_navigation_system/README.md`](build-a-complete-msc-dissertation-prototype/outputs/assistive_navigation_system/README.md).

---

## Running Tests

```powershell
cd build-a-complete-msc-dissertation-prototype\outputs\assistive_navigation_system
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

All 4 tests cover: zone assignment, distance ordering, haptic logic, precision/recall metrics.

---

## Docker

```powershell
cd build-a-complete-msc-dissertation-prototype\outputs\assistive_navigation_system
docker build -t assistive-nav .
docker run --rm -p 8501:8501 assistive-nav
```

Open **http://localhost:8501**.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| GitHub says "Add a README" | You are reading it — make sure it is committed at the repo root |
| `WinError 206` filename too long | `start.py` handles this — venv goes to `~\.assistive_nav_venv` automatically |
| `use_container_width` error | Already fixed — app uses `use_column_width` (works on all Streamlit versions) |
| DroidCam not in camera list | Start the DroidCam desktop client first, then reload the sidebar |
| Webcam black screen | Try a different index in the camera dropdown |
| YOLO weights fail to download | Enable **"Simulation detector"** in the sidebar |
| Audio not working | `pyttsx3` falls back silently — warnings still appear on screen |

---

## Dissertation Scope

Distance values are **relative monocular estimates** from bounding-box scale and vertical position — not calibrated metric depth. No LiDAR, stereo camera, or depth sensor is used. This is intentional for a single RGB camera prototype and is appropriate for hazard ranking and dissertation demonstration purposes.

---

## Technology Stack

[Python 3.10+](https://python.org) · [YOLO11 / Ultralytics](https://docs.ultralytics.com/models/yolo11/) · [OpenCV](https://opencv.org) · [Streamlit](https://streamlit.io) · [Plotly](https://plotly.com/python/) · [pyttsx3](https://pyttsx3.readthedocs.io) · [pandas](https://pandas.pydata.org) · [pytest](https://pytest.org)
