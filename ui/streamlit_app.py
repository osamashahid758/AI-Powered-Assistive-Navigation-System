"""Streamlit dashboard for the assistive navigation prototype."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from feedback.audio import AudioFeedback
from feedback.haptics import HapticController
from feedback.logger import DetectionLogger
from navigation.engine import NavigationEngine
from navigation.virtual_270 import VirtualNavigationSimulator
from ui.components import (
    build_sector_figure,
    build_session_chart,
    build_warning_level_chart,
    detection_table_rows,
)
from vision.annotator import annotate_frame, bgr_to_rgb
from vision.config import ModelConfig
from vision.detector import create_detector
from vision.synthetic import make_simulation_frame

_LEVEL_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}

_SHORT_DIRECTION = {
    "path ahead is relatively clear": "Clear",
    "prefer slight left": "Go left",
    "prefer slight right": "Go right",
    "slow down": "Slow down",
}


# ---------------------------------------------------------------------------
# Cloud detection — env vars only, never touches cv2
# Streamlit Cloud always sets HOME=/home/appuser
# ---------------------------------------------------------------------------

def _detect_cloud() -> bool:
    if os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit":
        return True
    if os.environ.get("HOME", "") == "/home/appuser":
        return True
    if os.environ.get("IS_STREAMLIT_CLOUD", "") == "true":
        return True
    return False


_IS_CLOUD = _detect_cloud()


# ---------------------------------------------------------------------------
# Width-kwarg helpers (Streamlit changed the API between versions)
# ---------------------------------------------------------------------------

def _make_width_kwarg(fn_name: str) -> dict:
    import inspect
    try:
        sig = inspect.signature(getattr(st, fn_name, None) or (lambda: None))
        if "use_container_width" in sig.parameters:
            return {"use_container_width": True}
        if "use_column_width" in sig.parameters:
            return {"use_column_width": True}
    except (ValueError, TypeError):
        pass
    return {"use_container_width": True}


_IMG_KW   = _make_width_kwarg("image")
_CHART_KW = _make_width_kwarg("plotly_chart")
_DF_KW    = _make_width_kwarg("dataframe")


def _img(placeholder, frame, **kwargs):
    placeholder.image(frame, **{**_IMG_KW, **kwargs})


def _chart(container, fig, **_ignored):
    container.plotly_chart(fig, **_CHART_KW)


def _df(container, data):
    container.dataframe(data, **_DF_KW)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Assistive Navigation",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0.5rem; }
        h1 { font-size: 1.4rem !important; margin-bottom: 0 !important; }
        .stTabs [data-baseweb="tab"] { font-size: 0.9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    tab_live, tab_eval, tab_about = st.tabs(["Live Navigation", "Evaluation", "About"])
    with tab_live:
        _render_live_tab()
    with tab_eval:
        _render_evaluation_tab()
    with tab_about:
        _render_about_tab()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _scan_cameras() -> list[tuple[int, str]]:
    try:
        import cv2
    except Exception:
        return [(0, "Camera 0 (default)")]
    found = []
    for idx in range(10):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0)
        if cap is not None and cap.isOpened():
            found.append((idx, f"Camera {idx}"))
            cap.release()
    return found if found else [(0, "Camera 0 (default)")]


def _build_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## Configuration")

        if _IS_CLOUD:
            source_options = ["Simulation", "Browser Camera", "Upload video"]
        else:
            source_options = ["Simulation", "Browser Camera", "Webcam (local)", "Video file", "Upload video"]

        source_mode = st.selectbox("Input source", source_options)

        if source_mode == "Browser Camera":
            st.caption("Allow camera access when your browser asks.")

        st.markdown("---")
        model_path = st.text_input("YOLO11 model", value="yolo11n.pt")
        confidence = st.slider("Confidence", 0.05, 0.95, 0.35, 0.05)
        use_mock   = st.checkbox("Simulation detector", value=(source_mode == "Simulation"))
        audio_on   = st.checkbox("Text-to-speech", value=False)
        max_frames = st.slider("Max frames", 30, 900, 180, 30)

        video_path    = None
        uploaded_file = None
        webcam_index  = 0

        if source_mode == "Webcam (local)":
            cameras = _scan_cameras()
            if len(cameras) == 1:
                webcam_index = cameras[0][0]
                st.info(f"Found: {cameras[0][1]}")
            else:
                labels = [label for _, label in cameras]
                choice = st.selectbox("Select camera", labels)
                webcam_index = cameras[labels.index(choice)][0]
            st.caption("DroidCam: start the desktop client first, then press Run.")
        elif source_mode == "Video file":
            video_path = st.text_input(
                "Video path",
                value=str(ROOT / "samples" / "left_person_right_vehicle.avi"),
            )
        elif source_mode == "Upload video":
            uploaded_file = st.file_uploader("Upload video", type=["mp4", "avi", "mov", "mkv"])

        st.markdown("---")
        run = st.button("Run navigation", type="primary")

    return dict(
        source_mode=source_mode,
        model_path=model_path,
        confidence=confidence,
        use_mock=use_mock,
        audio_on=audio_on,
        max_frames=max_frames,
        video_path=video_path,
        uploaded_file=uploaded_file,
        webcam_index=webcam_index,
        run=run,
    )


# ---------------------------------------------------------------------------
# Live Navigation tab
# ---------------------------------------------------------------------------

def _render_live_tab() -> None:
    st.markdown("# Assistive Navigation System")
    cfg = _build_sidebar()

    if cfg["source_mode"] == "Browser Camera":
        _render_browser_camera_mode(cfg)
        return

    if not cfg["run"]:
        _show_idle_screen()
        return

    # Webcam / video-file modes strictly require cv2 — block clearly on cloud
    if cfg["source_mode"] in ("Webcam (local)", "Video file"):
        try:
            import cv2  # noqa: F401
        except Exception:
            st.error(
                "OpenCV (cv2) is not available in this environment. "
                "Use **Browser Camera**, **Upload video**, or **Simulation** instead."
            )
            return

    # Upload video: decode frames with PIL — no cv2 needed
    if cfg["source_mode"] == "Upload video":
        _render_upload_mode(cfg)
        return

    # Simulation and local webcam/video-file go through the main loop
    _render_main_loop(cfg)


def _show_idle_screen() -> None:
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input sources", "4", "Browser cam / Upload / Simulation / Local webcam")
    c2.metric("AI model",      "YOLO11n", "Real-time detection")
    c3.metric("Object classes", "7", "Person, chair, stairs…")
    c4.metric("Feedback modes", "3", "Visual · Haptic · Audio")
    st.info("Select an input source in the sidebar, then press **Run navigation**.")


# ---------------------------------------------------------------------------
# Upload video mode — PIL frame extraction, zero cv2
# ---------------------------------------------------------------------------

def _render_upload_mode(cfg: dict) -> None:
    import numpy as np
    from PIL import Image as PILImage

    uploaded_file = cfg["uploaded_file"]
    if uploaded_file is None:
        st.info("Upload a video file using the sidebar, then press **Run navigation**.")
        return

    st.info("Extracting frames with PIL — processing key frames from your video.")

    # Save upload to a temp file so we can try cv2 or PIL extraction
    suffix = Path(uploaded_file.name).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.read())
    tmp.close()
    tmp_path = tmp.name

    # Try cv2 first (available locally), fall back to PIL single-frame for cloud
    frames = _extract_frames(tmp_path, cfg["max_frames"])

    if not frames:
        st.error("Could not extract frames from this video. Try uploading an MP4.")
        return

    _run_pipeline_on_frames(frames, cfg)


def _extract_frames(video_path: str, max_frames: int) -> list:
    """Extract frames as BGR numpy arrays. Uses cv2 if available, PIL otherwise."""
    import numpy as np

    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("cv2 could not open video")
        frames = []
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
        cap.release()
        return frames
    except Exception:
        pass

    # PIL fallback: read the file as a single image (works for single-frame uploads
    # like JPEG/PNG misnamed as video, or as a graceful degradation)
    try:
        from PIL import Image as PILImage
        img = PILImage.open(video_path).convert("RGB")
        arr = np.array(img)[..., ::-1].copy()  # RGB→BGR
        return [arr]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main frame loop — Simulation + local Webcam/Video file
# ---------------------------------------------------------------------------

def _render_main_loop(cfg: dict) -> None:
    # Build layout
    camera_ph = st.empty()
    col_info, col_sector = st.columns([5, 6])
    with col_info:
        mc = st.columns(2)
        fps_ph  = mc[0].empty()
        near_ph = mc[1].empty()
        det_ph  = mc[0].empty()
        dir_ph  = mc[1].empty()
        st.markdown("---")
        warn_ph = st.empty()
        st.markdown("---")
        st.caption("Haptic feedback")
        hap_l_ph = st.empty()
        hap_r_ph = st.empty()
    with col_sector:
        sector_ph = st.empty()
    chart_ph = st.empty()
    with st.expander("Detection log", expanded=False):
        table_ph = st.empty()

    try:
        source, frame_iter = _build_frame_iterator(cfg)
    except RuntimeError as exc:
        st.error(f"Could not open video source: {exc}")
        return

    detector   = create_detector(
        ModelConfig(model_path=cfg["model_path"], confidence=cfg["confidence"], use_mock=cfg["use_mock"]),
        fallback_to_mock=True,
    )
    nav_engine = NavigationEngine()
    haptics    = HapticController()
    simulator  = VirtualNavigationSimulator()
    audio      = AudioFeedback(enabled=cfg["audio_on"])
    logger     = DetectionLogger(ROOT / "logs" / "navigation_events.csv")

    history: list[dict] = []
    start       = time.perf_counter()
    frame_count = 0
    total_dets  = 0

    try:
        for frame_count, frame in frame_iter:
            detections = detector.detect(frame)
            enriched   = nav_engine.enrich(detections, frame.shape)
            signal     = haptics.generate(enriched)
            logger.log(enriched)
            spoken     = audio.speak_detections(enriched)
            readings   = simulator.build_awareness(enriched, frame.shape[1])
            direction  = simulator.suggested_direction(readings)

            annotated = annotate_frame(frame, enriched)
            _img(camera_ph, bgr_to_rgb(annotated), channels="RGB")

            elapsed     = max(1e-6, time.perf_counter() - start)
            fps         = (frame_count + 1) / elapsed
            total_dets += len(enriched)
            nearest     = min(
                (d.estimated_distance for d in enriched if d.estimated_distance is not None),
                default=None,
            )
            active_msgs = [d.message for d in enriched if d.message]
            top_level   = max(
                (d.warning_level for d in enriched),
                key=lambda lv: _LEVEL_ORDER.get(lv, 0),
                default="none",
            )

            fps_ph.metric("FPS",        f"{fps:.0f}")
            near_ph.metric("Nearest",   f"{nearest:.1f} m" if nearest is not None else "clear")
            det_ph.metric("Detections", len(enriched))
            dir_ph.metric("Direction",  _SHORT_DIRECTION.get(direction, direction.capitalize()))

            msg = " | ".join(spoken or active_msgs[:2])
            if msg and top_level == "critical":
                warn_ph.error(f"STOP — {msg}")
            elif msg and top_level == "high":
                warn_ph.warning(f"Warning — {msg}")
            elif msg and top_level == "medium":
                warn_ph.info(f"Caution — {msg}")
            else:
                warn_ph.success("Path clear")

            l_pct = int(signal.left_intensity * 100)
            r_pct = int(signal.right_intensity * 100)
            hap_l_ph.progress(signal.left_intensity, text=f"Left motor — {l_pct}%")
            hap_r_ph.progress(signal.right_intensity, text=f"Right motor — {r_pct}%")

            _chart(sector_ph, build_sector_figure(readings), key=f"sector_{frame_count}")

            level_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for d in enriched:
                if d.warning_level in level_counts:
                    level_counts[d.warning_level] += 1
            history.append({
                "frame":   frame_count,
                "count":   len(enriched),
                "nearest": nearest if nearest is not None else 0.0,
                **{f"level_{k}": v for k, v in level_counts.items()},
            })
            if len(history) >= 5:
                _chart(chart_ph, build_session_chart(history), key=f"chart_{frame_count}")

            _df(table_ph, detection_table_rows(enriched))

            if cfg["source_mode"] == "Simulation":
                time.sleep(0.03)

    finally:
        if source is not None:
            source.release()

    processed = frame_count + 1
    avg_fps   = processed / max(1e-6, time.perf_counter() - start)
    st.success(
        f"Done — **{processed}** frames at **{avg_fps:.1f} FPS** · "
        f"**{total_dets}** total detections · log saved to `logs/navigation_events.csv`"
    )


def _run_pipeline_on_frames(frames: list, cfg: dict) -> None:
    """Run the navigation pipeline on a pre-extracted list of BGR frames."""
    camera_ph = st.empty()
    col_info, col_sector = st.columns([5, 6])
    with col_info:
        mc = st.columns(2)
        fps_ph  = mc[0].empty()
        near_ph = mc[1].empty()
        det_ph  = mc[0].empty()
        dir_ph  = mc[1].empty()
        st.markdown("---")
        warn_ph = st.empty()
        st.markdown("---")
        st.caption("Haptic feedback")
        hap_l_ph = st.empty()
        hap_r_ph = st.empty()
    with col_sector:
        sector_ph = st.empty()
    chart_ph = st.empty()

    detector   = create_detector(
        ModelConfig(model_path=cfg["model_path"], confidence=cfg["confidence"], use_mock=cfg["use_mock"]),
        fallback_to_mock=True,
    )
    nav_engine = NavigationEngine()
    haptics    = HapticController()
    simulator  = VirtualNavigationSimulator()
    logger     = DetectionLogger(ROOT / "logs" / "navigation_events.csv")

    history: list[dict] = []
    start      = time.perf_counter()
    total_dets = 0

    for frame_count, frame in enumerate(frames):
        detections = detector.detect(frame)
        enriched   = nav_engine.enrich(detections, frame.shape)
        signal     = haptics.generate(enriched)
        logger.log(enriched)
        readings   = simulator.build_awareness(enriched, frame.shape[1])
        direction  = simulator.suggested_direction(readings)

        annotated = annotate_frame(frame, enriched)
        _img(camera_ph, bgr_to_rgb(annotated), channels="RGB")

        elapsed     = max(1e-6, time.perf_counter() - start)
        fps         = (frame_count + 1) / elapsed
        total_dets += len(enriched)
        nearest     = min(
            (d.estimated_distance for d in enriched if d.estimated_distance is not None),
            default=None,
        )
        active_msgs = [d.message for d in enriched if d.message]
        top_level   = max(
            (d.warning_level for d in enriched),
            key=lambda lv: _LEVEL_ORDER.get(lv, 0),
            default="none",
        )

        fps_ph.metric("FPS",        f"{fps:.0f}")
        near_ph.metric("Nearest",   f"{nearest:.1f} m" if nearest is not None else "clear")
        det_ph.metric("Detections", len(enriched))
        dir_ph.metric("Direction",  _SHORT_DIRECTION.get(direction, direction.capitalize()))

        msg = " | ".join(active_msgs[:2])
        if msg and top_level == "critical":
            warn_ph.error(f"STOP — {msg}")
        elif msg and top_level == "high":
            warn_ph.warning(f"Warning — {msg}")
        elif msg and top_level == "medium":
            warn_ph.info(f"Caution — {msg}")
        else:
            warn_ph.success("Path clear")

        l_pct = int(signal.left_intensity * 100)
        r_pct = int(signal.right_intensity * 100)
        hap_l_ph.progress(signal.left_intensity, text=f"Left motor — {l_pct}%")
        hap_r_ph.progress(signal.right_intensity, text=f"Right motor — {r_pct}%")

        _chart(sector_ph, build_sector_figure(readings), key=f"sector_{frame_count}")

        level_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for d in enriched:
            if d.warning_level in level_counts:
                level_counts[d.warning_level] += 1
        history.append({
            "frame":   frame_count,
            "count":   len(enriched),
            "nearest": nearest if nearest is not None else 0.0,
            **{f"level_{k}": v for k, v in level_counts.items()},
        })
        if len(history) >= 5:
            _chart(chart_ph, build_session_chart(history), key=f"chart_{frame_count}")

    processed = frame_count + 1
    avg_fps   = processed / max(1e-6, time.perf_counter() - start)
    st.success(
        f"Done — **{processed}** frames at **{avg_fps:.1f} FPS** · "
        f"**{total_dets}** total detections"
    )


# ---------------------------------------------------------------------------
# Frame iterator for Simulation + local webcam/video-file
# ---------------------------------------------------------------------------

def _build_frame_iterator(cfg: dict):
    mode = cfg["source_mode"]
    if mode in ("Webcam (local)", "Video file"):
        from vision.camera import VideoSource, parse_source
        if mode == "Webcam (local)":
            src = VideoSource(cfg["webcam_index"])
        else:
            src = VideoSource(parse_source(cfg["video_path"] or "0"))
        return src, src.frames(max_frames=cfg["max_frames"])
    # Simulation (default)
    return None, _sim_frames(cfg["max_frames"])


def _sim_frames(max_frames: int):
    for idx in range(max_frames):
        yield idx, make_simulation_frame(idx)


# ---------------------------------------------------------------------------
# Browser Camera — st.camera_input, zero extra dependencies
# Works on Streamlit Cloud, any browser, mobile included
# ---------------------------------------------------------------------------

def _render_browser_camera_mode(cfg: dict) -> None:
    import numpy as np
    from PIL import Image as PILImage

    detector   = create_detector(
        ModelConfig(
            model_path=cfg["model_path"],
            confidence=cfg["confidence"],
            use_mock=cfg["use_mock"],
        ),
        fallback_to_mock=True,
    )
    nav_engine = NavigationEngine()
    haptics    = HapticController()
    simulator  = VirtualNavigationSimulator()
    logger     = DetectionLogger(ROOT / "logs" / "navigation_events.csv")

    st.markdown(
        "Point your device camera at the scene and press **Take photo** — "
        "detection runs instantly on each captured frame."
    )

    col_cam, col_metrics = st.columns([3, 2])
    with col_cam:
        snap = st.camera_input("Take photo")

    if snap is None:
        with col_metrics:
            st.info("Waiting for a captured frame…")
        return

    # Decode JPEG → BGR numpy array (PIL, no cv2 needed)
    pil_img   = PILImage.open(snap).convert("RGB")
    frame_rgb = np.array(pil_img)
    frame_bgr = frame_rgb[..., ::-1].copy()

    detections = detector.detect(frame_bgr)
    enriched   = nav_engine.enrich(detections, frame_bgr.shape)
    signal     = haptics.generate(enriched)
    logger.log(enriched)
    readings   = simulator.build_awareness(enriched, frame_bgr.shape[1])
    direction  = simulator.suggested_direction(readings)

    annotated     = annotate_frame(frame_bgr, enriched)
    annotated_rgb = bgr_to_rgb(annotated)

    with col_cam:
        st.image(annotated_rgb, **_IMG_KW)

    nearest = min(
        (d.estimated_distance for d in enriched if d.estimated_distance is not None),
        default=None,
    )
    top_level = max(
        (d.warning_level for d in enriched),
        key=lambda lv: _LEVEL_ORDER.get(lv, 0),
        default="none",
    )
    active_msgs = [d.message for d in enriched if d.message]

    with col_metrics:
        mc = st.columns(2)
        mc[0].metric("Detections", len(enriched))
        mc[1].metric("Nearest",    f"{nearest:.1f} m" if nearest is not None else "clear")
        mc[0].metric("Direction",  _SHORT_DIRECTION.get(direction, direction.capitalize()))
        mc[1].metric("Warning",    top_level.capitalize())

        st.markdown("---")
        msg = " | ".join(active_msgs[:2])
        if msg and top_level == "critical":
            st.error(f"STOP — {msg}")
        elif msg and top_level == "high":
            st.warning(f"Warning — {msg}")
        elif msg and top_level == "medium":
            st.info(f"Caution — {msg}")
        else:
            st.success("Path clear")

        l_pct = int(signal.left_intensity * 100)
        r_pct = int(signal.right_intensity * 100)
        st.progress(signal.left_intensity,  text=f"Left motor — {l_pct}%")
        st.progress(signal.right_intensity, text=f"Right motor — {r_pct}%")

    st.plotly_chart(build_sector_figure(readings), **_CHART_KW)


# ---------------------------------------------------------------------------
# Evaluation tab
# ---------------------------------------------------------------------------

def _render_evaluation_tab() -> None:
    st.markdown("# Detection Evaluation")
    st.caption("Measure precision, recall, and F1 against ground-truth bounding-box CSVs.")

    col_gt, col_pred = st.columns(2)
    with col_gt:
        gt_file = st.file_uploader(
            "Ground-truth CSV", type=["csv"], key="gt_upload",
            help="Columns: frame_id, object, xmin, ymin, xmax, ymax",
        )
        use_sample_gt = st.checkbox("Use bundled sample", key="use_sample_gt")
    with col_pred:
        pred_file = st.file_uploader(
            "Predictions CSV", type=["csv"], key="pred_upload",
            help="Columns: frame_id, object, xmin, ymin, xmax, ymax, confidence",
        )
        use_sample_pred = st.checkbox("Use bundled sample", key="use_sample_pred")

    iou_threshold = st.slider("IoU threshold", 0.1, 0.9, 0.5, 0.05)

    if not st.button("Evaluate", type="primary"):
        return

    try:
        from evaluation.metrics import evaluate_precision_recall, load_box_csv
    except Exception as exc:
        st.error(f"Evaluation module error: {exc}")
        return

    gt_path   = ROOT / "samples" / "sample_ground_truth.csv" if use_sample_gt else None
    pred_path = ROOT / "samples" / "sample_predictions.csv"  if use_sample_pred else None

    try:
        if gt_file is not None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            tmp.write(gt_file.read()); tmp.close()
            gt_path = Path(tmp.name)
        if pred_file is not None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            tmp.write(pred_file.read()); tmp.close()
            pred_path = Path(tmp.name)
        if gt_path is None or pred_path is None:
            st.warning("Supply both CSVs or tick 'Use bundled sample'.")
            return
        gt      = load_box_csv(gt_path)
        preds   = load_box_csv(pred_path)
        metrics = evaluate_precision_recall(gt, preds, iou_threshold=iou_threshold)
    except Exception as exc:
        st.error(f"Evaluation failed: {exc}")
        return

    st.markdown("---")
    rc = st.columns(5)
    rc[0].metric("Precision",      f"{metrics.precision:.3f}")
    rc[1].metric("Recall",         f"{metrics.recall:.3f}")
    rc[2].metric("F1",             f"{metrics.f1:.3f}")
    rc[3].metric("True Positives", metrics.true_positives)
    rc[4].metric("FP / FN",        f"{metrics.false_positives} / {metrics.false_negatives}")

    _chart(st, _metrics_bar(metrics))

    with st.expander("Box counts"):
        st.metric("Ground-truth boxes", len(gt))
        st.metric("Prediction boxes",   len(preds))


def _metrics_bar(metrics):
    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=["Precision", "Recall", "F1"],
        y=[metrics.precision, metrics.recall, metrics.f1],
        marker_color=["#4e9af1", "#f77f00", "#2a9d8f"],
        text=[f"{v:.3f}" for v in [metrics.precision, metrics.recall, metrics.f1]],
        textposition="outside",
    ))
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(range=[0, 1.15], showgrid=False),
        xaxis=dict(showgrid=False),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font=dict(color="#fafafa", size=14),
    )
    return fig


# ---------------------------------------------------------------------------
# About tab
# ---------------------------------------------------------------------------

def _render_about_tab() -> None:
    st.markdown("# About this Prototype")
    st.markdown("""
An MSc dissertation prototype for **AI-powered assistive navigation** for visually impaired users.
YOLO11 detects obstacles in real time; a spatial pipeline converts detections into
directional warnings, haptic signals, and spoken alerts.

---

### System modules

| Module | Purpose |
|---|---|
| `vision/` | YOLO11 detector, webcam/video input, frame annotation |
| `navigation/` | Zone assignment (L/C/R), distance estimation, warning rules, 270° awareness |
| `feedback/` | Haptic simulation, pyttsx3 audio, CSV logging |
| `ui/` | This Streamlit dashboard |
| `evaluation/` | IoU precision/recall, latency/FPS benchmark |
| `scripts/` | CLI runner, synthetic video generator |

---

### Warning levels

| Level | Distance | Colour | Audio |
|---|---|---|---|
| Critical | ≤ 1.2 m | Red | Yes |
| High | ≤ 2.0 m | Orange | Yes |
| Medium | ≤ 3.5 m | Yellow | Yes |
| Low | > 3.5 m | Green | No |

Centre-zone obstacles escalate one level earlier (−0.25 m bias).

---

### Haptic mapping

- Left zone obstacle → left motor
- Right zone obstacle → right motor
- Centre zone obstacle → both motors
- Intensity = `1 − distance / 5 m` clamped to 10–100 %

---

### Dissertation scope

Distance values are **relative monocular estimates** from bounding-box scale and vertical
position — not calibrated metric depth. No LiDAR or stereo camera is used.
    """)
    st.caption("YOLO11 weights by Ultralytics. Not for clinical or safety-critical deployment.")


if __name__ == "__main__":
    main()
