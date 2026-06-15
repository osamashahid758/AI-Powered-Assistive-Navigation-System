"""Frame annotation utilities — cv2 preferred, PIL+NumPy fallback when cv2 unavailable."""

from __future__ import annotations

from typing import Any

import numpy as np

from navigation.zones import ZoneAssigner
from vision.camera import require_cv2
from vision.detections import Detection


ZONE_COLORS = {
    "left":    (64,  180, 255),
    "centre":  (50,  220, 100),
    "right":   (255, 170, 60),
    "unknown": (190, 190, 190),
}

WARNING_COLORS = {
    "critical": (0,   0,   255),
    "high":     (0,   120, 255),
    "medium":   (0,   220, 255),
    "low":      (80,  220, 80),
    "none":     (180, 180, 180),
}


def _cv2_available() -> bool:
    try:
        require_cv2()
        return True
    except RuntimeError:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def annotate_frame(frame: Any, detections: list[Detection], draw_zones: bool = True, force_pil: bool = False) -> Any:
    """Draw zones, bounding boxes, labels, distance, and warning level.

    force_pil=True bypasses cv2 even if it's available (used for simulation and browser-snapshot frames).
    """
    if not force_pil and _cv2_available():
        return _annotate_cv2(frame, detections, draw_zones)
    return _annotate_pil(frame, detections, draw_zones)


def bgr_to_rgb(frame: Any) -> Any:
    """Convert a BGR frame to RGB for Streamlit."""
    try:
        cv2 = require_cv2()
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    except RuntimeError:
        arr = np.asarray(frame)
        return arr[..., ::-1].copy()


# ---------------------------------------------------------------------------
# cv2 path (fast, used when OpenCV is present)
# ---------------------------------------------------------------------------

def _annotate_cv2(frame: Any, detections: list[Detection], draw_zones: bool) -> Any:
    cv2 = require_cv2()
    output = frame.copy()
    height, width = output.shape[:2]
    if draw_zones:
        _draw_zone_overlay_cv2(cv2, output, width, height)
    for det in detections:
        x1, y1, x2, y2 = det.bbox.as_int_tuple()
        color = WARNING_COLORS.get(det.warning_level, WARNING_COLORS["none"])
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        dist_text = f"{det.estimated_distance:.2f}m" if det.estimated_distance else "n/a"
        label = f"{det.label} {det.confidence:.2f} | {det.zone or '?'} | {dist_text}"
        _draw_label_cv2(cv2, output, label, x1, max(18, y1 - 8), color)
    return output


def _draw_zone_overlay_cv2(cv2: Any, frame: Any, width: int, height: int) -> None:
    assigner = ZoneAssigner()
    lb, rb = assigner.boundaries_px(width)
    cv2.line(frame, (lb, 0), (lb, height), (255, 255, 255), 1)
    cv2.line(frame, (rb, 0), (rb, height), (255, 255, 255), 1)
    cv2.putText(frame, "LEFT",   (12, 24),       cv2.FONT_HERSHEY_SIMPLEX, 0.65, ZONE_COLORS["left"],   2)
    cv2.putText(frame, "CENTRE", (lb + 12, 24),  cv2.FONT_HERSHEY_SIMPLEX, 0.65, ZONE_COLORS["centre"], 2)
    cv2.putText(frame, "RIGHT",  (rb + 12, 24),  cv2.FONT_HERSHEY_SIMPLEX, 0.65, ZONE_COLORS["right"],  2)


def _draw_label_cv2(cv2: Any, frame: Any, label: str, x: int, y: int, color: tuple) -> None:
    font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
    cv2.rectangle(frame, (x, y - th - 8), (x + tw + 6, y + 4), color, -1)
    cv2.putText(frame, label, (x + 3, y - 3), font, scale, (255, 255, 255), thick, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# PIL fallback path (used on Streamlit Cloud when libgl1 not yet propagated)
# ---------------------------------------------------------------------------

def _annotate_pil(frame: Any, detections: list[Detection], draw_zones: bool) -> Any:
    """PIL-based annotation. Input is BGR (same as cv2 convention). Returns BGR."""
    from PIL import Image, ImageDraw, ImageFont

    arr = np.asarray(frame).astype(np.uint8)
    # All frames in this pipeline are BGR (cv2 convention) — convert to RGB for PIL
    rgb = arr[..., ::-1].copy()
    pil_img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_img)

    width, height = pil_img.size

    if draw_zones:
        assigner = ZoneAssigner()
        lb, rb = assigner.boundaries_px(width)
        draw.line([(lb, 0), (lb, height)], fill=(255, 255, 255), width=1)
        draw.line([(rb, 0), (rb, height)], fill=(255, 255, 255), width=1)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        # Colors stored as BGR — flip to RGB for PIL
        draw.text((12, 8),        "LEFT",   fill=ZONE_COLORS["left"][::-1],   font=font)
        draw.text((lb + 12, 8),   "CENTRE", fill=ZONE_COLORS["centre"][::-1], font=font)
        draw.text((rb + 12, 8),   "RIGHT",  fill=ZONE_COLORS["right"][::-1],  font=font)

    try:
        font_label = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_label = ImageFont.load_default()

    for det in detections:
        x1, y1, x2, y2 = det.bbox.as_int_tuple()
        color_bgr = WARNING_COLORS.get(det.warning_level, WARNING_COLORS["none"])
        color_rgb = color_bgr[::-1]  # PIL needs RGB
        draw.rectangle([x1, y1, x2, y2], outline=color_rgb, width=2)
        dist_text = f"{det.estimated_distance:.2f}m" if det.estimated_distance else "n/a"
        label = f"{det.label} {det.confidence:.2f} | {det.zone or '?'} | {dist_text}"
        bbox_text = draw.textbbox((x1, max(18, y1 - 8)), label, font=font_label)
        draw.rectangle(bbox_text, fill=color_rgb)
        draw.text((x1 + 2, max(18, y1 - 8)), label, fill=(255, 255, 255), font=font_label)

    # Convert back to BGR so the return value matches the cv2 path
    return np.array(pil_img)[..., ::-1].copy()
