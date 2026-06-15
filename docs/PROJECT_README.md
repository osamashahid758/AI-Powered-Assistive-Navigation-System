# AI-Powered Assistive Navigation System

> **MSc Dissertation Prototype** — Real-time obstacle detection and spatial awareness for visually impaired users, powered by YOLO11, OpenCV, and Streamlit.

---

## What This Project Does

This system uses a camera (webcam, phone camera, or video file) to **detect nearby obstacles in real time** and immediately tell the user where they are, how close they are, and which direction to avoid them — through three parallel feedback channels:

| Feedback channel | How it works |
|---|---|
| **Visual** | Annotated camera feed with colour-coded bounding boxes, zone lines, and distance labels |
| **Haptic (simulated)** | Left/right vibration motor intensity shown as progress bars — left obstacle → left motor, right → right |
| **Audio** | Spoken warnings via text-to-speech: *"Stairs ahead — stop"*, *"Person on your left"* |

Everything runs in a **single browser dashboard** — no hardware needed beyond a camera and Python.

---

## How It Works — System Pipeline

```
Camera / Video / Simulation
        │
        ▼
┌─────────────────────┐
│   YOLO11 Detector   │  ← detects person, chair, table, door, stairs, vehicle, wall
└─────────────────────┘
        │  list of bounding boxes + labels
        ▼
┌─────────────────────┐
│  Navigation Engine  │  ← assigns LEFT / CENTRE / RIGHT zone
│                     │  ← estimates relative distance (monocular)
│                     │  ← computes warning level: critical / high / medium / low
└─────────────────────┘
        │  enriched detections
        ▼
┌──────────────────────────────────────────────┐
│              Feedback Layer                   │
│  HapticController  → left/right intensity     │
│  AudioFeedback     → spoken alert (pyttsx3)   │
│  DetectionLogger   → CSV event log            │
└──────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│           Streamlit Dashboard                        │
│  Camera feed  │  Metrics  │  270° polar chart        │
│  Warning banner  │  Haptic bars  │  Session charts   │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start — One Command on Any Device

**The only requirement is Python 3.10 or later.**
The launcher creates the virtual environment, installs all packages, and generates sample videos automatically.

### Windows

```powershell
cd outputs\assistive_navigation_system
python start.py
```

Or **double-click `start.bat`** — no terminal needed.

### macOS / Linux

```bash
cd outputs/assistive_navigation_system
python3 start.py
```

Or run `bash start.sh`.

### What happens on first run

```
============================================
  AI-Powered Assistive Navigation System
  MSc Dissertation Prototype
============================================

  [OK] Python 3.12.4
  >>> Creating virtual environment at C:\Users\You\.assistive_nav_venv
  [OK] Virtual environment created.
  >>> Installing packages (streamlit, opencv, ultralytics/YOLO11, plotly, pyttsx3...)
      [takes 2-4 minutes — only happens once]
  [OK] All packages installed.
  [OK] Sample videos ready.

============================================
  Dashboard:  http://localhost:8501
  Stop:       Ctrl+C
============================================
```

Then open **http://localhost:8501** in your browser.

> **Windows long-path note:** If your project folder has a long path, `start.py` automatically places the virtual environment in `C:\Users\YourName\.assistive_nav_venv` to avoid Windows 260-character path errors.

> **Offline use:** Enable **"Simulation detector"** in the sidebar to run entirely offline — no camera, no YOLO download needed.

---

## Input Sources

Select the source from the **sidebar dropdown** before pressing Run:

### Simulation
Generates synthetic camera frames with animated obstacles (person, vehicle, chair, stairs, door, wall). **No camera required.** Best for demos, testing, and offline use. The mock detector produces deterministic, smoothly-moving detections — exactly as if a real camera saw those objects.

### Webcam
Opens a connected camera using OpenCV. The sidebar **automatically scans all available camera indices (0–9)** and shows a dropdown of detected cameras. If you have multiple cameras, you can pick the right one.

**Using DroidCam (phone as webcam):**
1. Install the [DroidCam Windows client](https://www.dev47apps.com/) on your PC
2. Install the DroidCam app on your Android/iPhone
3. Connect by USB or WiFi — the client shows a live preview
4. **Then** open the sidebar, select `Webcam` — DroidCam appears as `Camera 1` or `Camera 2`
5. Select it from the dropdown and press **Run navigation**

### Video File
Enter the path to any `.mp4`, `.avi`, `.mov`, or `.mkv` file. Two synthetic sample videos are included:
- `samples/left_person_right_vehicle.avi` — person on left, vehicle on right, chair in centre
- `samples/centre_stairs_door.avi` — stairs ahead, door right, wall and table left

### Upload Video
Drag and drop a video directly into the browser. The app saves it to a temp file and processes it the same way as a local file.

---

## Dashboard — Tab by Tab

### Tab 1: Live Navigation

The main operating view. Configure everything in the sidebar, then press **Run navigation**.

**Camera feed** — the annotated video with:
- White vertical lines dividing LEFT / CENTRE / RIGHT zones
- Bounding boxes colour-coded by urgency: red (critical) → orange (high) → yellow (medium) → green (low)
- Labels on every box: `object  confidence | zone | distance`
- Zone labels in the top corners

**2×2 status metrics** (update every frame):
- **FPS** — how many frames per second the pipeline processes
- **Nearest** — distance to the closest obstacle (e.g. `1.84 m`)
- **Detections** — number of obstacles visible in this frame
- **Direction** — avoidance suggestion: `Clear` / `Go left` / `Go right` / `Slow down`

**Warning banner** — colour changes with urgency:
- 🔴 `STOP — Stairs ahead — stop` (critical)
- 🟠 `Warning — Person on your left` (high)
- 🔵 `Caution — Vehicle on your right` (medium)
- 🟢 `Path clear` (nothing urgent)

**Haptic progress bars** — two bars showing left and right motor intensity (0–100%)

**270° sector chart** — a polar chart showing the simulated environmental awareness field. The 9 sectors span −135° to +135°. The central 3 sectors (−45° to +45°) are driven by live camera detections. Colour = warning level of the nearest obstacle in that sector.

**Session trend charts** (appear after 5 frames):
- Line chart: detection count + nearest distance per frame
- The charts grow in real time as the run progresses

**Detection log** (collapsed by default, click to expand):
- Full table: object, zone, distance, confidence, warning level, message

**Session summary** (shown when run finishes):
- Total frames processed, average FPS, total detections, log file location

---

### Tab 2: Evaluation

Measure the accuracy of any detection run against ground-truth annotations.

**How to use:**
1. Upload a **ground-truth CSV** (what the objects actually were)
2. Upload a **predictions CSV** (what the detector said)
3. Or tick **"Use bundled sample"** for both — loads the pre-generated sample files
4. Adjust the **IoU threshold** (default 0.50 — standard COCO metric)
5. Press **Evaluate**

**Results shown:**
- Precision, Recall, F1-score
- True Positives, False Positives, False Negatives
- Bar chart of all three metrics

**CSV format required:**

```
frame_id,object,xmin,ymin,xmax,ymax,confidence
left_person_right_vehicle.avi:0,person,35,64,69,166,0.91
```

`confidence` is optional in ground-truth files (defaults to 1.0).

---

### Tab 3: About

System reference — component table, warning level thresholds, haptic intensity formula, 270° field explanation, and dissertation scope notes.

---

## Warning Level Logic

Every detected obstacle is assigned a warning level based on its estimated distance and zone:

| Level | Side zone distance | Centre zone distance | Box colour | Audio | Haptic |
|---|---|---|---|---|---|
| **Critical** | ≤ 1.2 m | ≤ 0.95 m | Red | Yes | Yes |
| **High** | ≤ 2.0 m | ≤ 1.75 m | Orange | Yes | Yes |
| **Medium** | ≤ 3.5 m | ≤ 3.5 m | Yellow | Yes | Yes |
| **Low** | > 3.5 m | > 3.5 m | Green | No | No |

Centre-zone obstacles are treated as 0.25 m closer than they really are — they escalate one level sooner because the user is walking directly toward them.

---

## Haptic Feedback Logic

```
Left zone obstacle  →  left motor only
Right zone obstacle →  right motor only
Centre obstacle     →  both motors equally
```

**Intensity formula:** `intensity = 1 − (distance / 5 m)`, clamped to 10%–100%.

A 1.0 m obstacle = 80% intensity. A 4.5 m obstacle = 10% intensity.

The haptic state is shown in the dashboard as two live progress bars.

---

## Avoidance Direction Logic

After every frame, the 270° simulator computes a suggested direction:

| Situation | Suggestion shown |
|---|---|
| Centre sector risk < 35% | `Clear` |
| Left sectors riskier | `Go right` |
| Right sectors riskier | `Go left` |
| Balanced high risk | `Slow down` |

---

## Detected Obstacle Classes

| Dashboard label | Maps from (COCO / custom labels) | Works with default YOLO11? |
|---|---|---|
| `person` | person, people | Yes |
| `chair` | chair, couch, sofa, bench | Yes |
| `table` | dining table, table, desk | Yes |
| `vehicle` | car, bus, truck, motorcycle, bicycle, train, van | Yes |
| `door` | door | Needs custom weights or simulation |
| `wall` | wall | Needs custom weights or simulation |
| `stairs` | stairs, stair, staircase, steps | Needs custom weights or simulation |

---

## CLI Usage

All CLI scripts run from inside `outputs/assistive_navigation_system/` with the venv active.

### Run on a video file with display window
```powershell
python scripts\run_pipeline.py --source samples\left_person_right_vehicle.avi --mock --display
```

### Run on webcam (index 0 = built-in, 1 = DroidCam)
```powershell
python scripts\run_pipeline.py --source 1 --audio
```

### Run with real YOLO11 detection on a video
```powershell
python scripts\run_pipeline.py --source samples\centre_stairs_door.avi
```

### Run with a custom trained model
```powershell
python scripts\run_pipeline.py --source samples\centre_stairs_door.avi --model models\best.pt
```

### Limit to 60 frames
```powershell
python scripts\run_pipeline.py --source samples\left_person_right_vehicle.avi --mock --max-frames 60
```

### Measure detection accuracy (precision / recall / F1)
```powershell
python evaluation\evaluate_detections.py ^
  --ground-truth samples\sample_ground_truth.csv ^
  --predictions  samples\sample_predictions.csv ^
  --iou 0.5
```

### Benchmark latency and FPS
```powershell
python evaluation\benchmark.py --source samples\centre_stairs_door.avi --mock --frames 120
```

Saves results to `logs/benchmark_results.csv`.

---

## Project Structure

```
assistive_navigation_system/
│
├── start.py                    ONE-COMMAND LAUNCHER — run this first
├── start.bat                   Windows double-click launcher
├── start.sh                    macOS / Linux launcher
├── requirements.txt            All Python dependencies
├── pyproject.toml              Project metadata + pytest config
├── Dockerfile                  Docker image definition
├── docker-compose.yml          Docker Compose config
│
├── ui/
│   ├── streamlit_app.py        Main dashboard — 3 tabs: Live / Evaluation / About
│   └── components.py           Reusable Plotly charts, table helpers, haptic bar
│
├── vision/
│   ├── detector.py             YOLO11 wrapper + MockObstacleDetector (simulation)
│   ├── detections.py           BBox and Detection dataclasses
│   ├── annotator.py            OpenCV frame drawing: boxes, zone lines, labels
│   ├── camera.py               VideoSource: webcam and file iterator; camera scanner
│   ├── config.py               ModelConfig, COCO label aliases, known object widths
│   └── synthetic.py            Procedural simulation frame generator
│
├── navigation/
│   ├── engine.py               NavigationEngine: zone + distance + level + message
│   ├── zones.py                ZoneAssigner: left / centre / right from bbox position
│   ├── distance.py             DistanceEstimator: monocular pinhole + floor-position blend
│   ├── risk.py                 warning_level_for_distance() + warning_message()
│   └── virtual_270.py          VirtualNavigationSimulator: 9-sector 270° awareness
│
├── feedback/
│   ├── haptics.py              HapticController → HapticSignal (left/right intensities)
│   ├── audio.py                AudioFeedback: pyttsx3 TTS with per-message cooldown
│   └── logger.py               DetectionLogger: appends to CSV event log
│
├── evaluation/
│   ├── metrics.py              IoU matching, precision / recall / F1
│   ├── evaluate_detections.py  CLI: evaluate two CSVs and print JSON results
│   └── benchmark.py            CLI: measure mean latency, p95 latency, FPS
│
├── scripts/
│   ├── run_pipeline.py         CLI runner: webcam or video, optional display + audio
│   └── generate_sample_videos.py  Generates AVI videos + CSVs (stdlib only, no cv2)
│
├── samples/
│   ├── left_person_right_vehicle.avi   Synthetic video — person L, vehicle R, chair C
│   ├── centre_stairs_door.avi          Synthetic video — stairs C, door R, wall+table L
│   ├── simulation_scenarios.csv        Frame-by-frame scenario descriptions
│   ├── sample_ground_truth.csv         Ground-truth boxes for evaluation
│   └── sample_predictions.csv         Near-perfect predicted boxes for evaluation
│
├── logs/
│   └── navigation_events.csv   Auto-created; detection events appended each run
│
├── tests/
│   └── test_navigation_feedback_metrics.py   4 unit tests (pytest)
│
└── docs/
    ├── INSTALLATION.md         Full setup guide for all platforms
    ├── USER_MANUAL.md          Step-by-step dashboard and CLI usage
    ├── dissertation_notes.md   Research aims, evaluation design, limitations
    ├── architecture.md         Architecture overview
    └── uml.md                  UML class and sequence diagrams
```

---

## Running the Tests

```powershell
# Activate the venv first
.\.venv\Scripts\Activate.ps1        # Windows
source .venv/bin/activate           # macOS / Linux

# Run all tests
python -m pytest tests/ -v
```

Expected output — all 4 pass:

```
tests/test_navigation_feedback_metrics.py::test_zone_assignment_three_regions              PASSED
tests/test_navigation_feedback_metrics.py::test_distance_decreases_for_larger_box         PASSED
tests/test_navigation_feedback_metrics.py::test_navigation_and_haptics_centre_obstacle... PASSED
tests/test_navigation_feedback_metrics.py::test_precision_recall_perfect_match            PASSED
```

---

## Docker

No Python installation needed — Docker handles everything.

```powershell
# Build
docker build -t assistive-nav .

# Run (simulation mode — no camera)
docker run --rm -p 8501:8501 assistive-nav

# Run with webcam on Linux
docker run --rm -p 8501:8501 --device=/dev/video0 assistive-nav

# Run with GPU
docker run --rm -p 8501:8501 --gpus all assistive-nav
```

Open **http://localhost:8501**.

---

## CSV Log Reference

Every detection is appended to `logs/navigation_events.csv` during a run:

```
timestamp,object,zone,estimated_distance,warning_level
2025-06-15T10:23:01.123+00:00,person,left,1.84,high
2025-06-15T10:23:01.123+00:00,vehicle,right,2.41,medium
2025-06-15T10:23:01.123+00:00,chair,centre,2.10,medium
```

Delete this file between runs to start a fresh log.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named cv2` | Run `pip install opencv-python` inside the venv |
| YOLO weights fail to download | Tick **"Simulation detector"** in the sidebar — works fully offline |
| Webcam shows black screen | Try a different camera index in the sidebar dropdown |
| DroidCam not in camera list | Start the DroidCam desktop client and connect your phone first, then reopen the app |
| `WinError 206` filename too long | `start.py` handles this automatically by placing the venv in `~\.assistive_nav_venv` |
| `use_container_width` error | Already fixed — the app uses `use_column_width` which works on all Streamlit versions |
| Streamlit port in use | `streamlit run ui\streamlit_app.py --server.port 8502` |
| Audio not working | `pyttsx3` falls back silently — warnings still appear on screen |
| PowerShell script blocked | Run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## Dissertation Scope and Limitations

This is a **software prototype** built for MSc research purposes:

- **Distance values are relative monocular estimates** derived from bounding-box apparent size and vertical screen position. They are not calibrated metric depth. No LiDAR, stereo camera, or depth sensor is used.
- **Haptic feedback is simulated in software.** No physical vibration hardware is required or assumed.
- **YOLO11 COCO weights** detect person, chair, table, and vehicles out of the box. Door, wall, and stairs require custom-trained weights or the simulation mode.
- **Dashboard latency** differs from embedded deployment latency on a wearable device.
- Values are appropriate for **hazard urgency ranking and dissertation demonstration** — not for clinical or safety-critical navigation decisions.

---

## Technology Stack

| Component | Technology |
|---|---|
| Object detection | [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) |
| Computer vision | [OpenCV](https://opencv.org/) |
| Dashboard | [Streamlit](https://streamlit.io/) ≥ 1.28 |
| Charts | [Plotly](https://plotly.com/python/) |
| Text-to-speech | [pyttsx3](https://pyttsx3.readthedocs.io/) |
| Data handling | [pandas](https://pandas.pydata.org/), [numpy](https://numpy.org/) |
| Testing | [pytest](https://pytest.org/) |
| Language | Python 3.10+ |
| Containerisation | Docker |
