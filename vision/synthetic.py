"""Synthetic frame helpers for simulation mode — pure NumPy, no OpenCV dependency."""

from __future__ import annotations

import math

import numpy as np


def _draw_line(frame: np.ndarray, p0: tuple, p1: tuple, color: tuple, thickness: int = 1) -> None:
    """Bresenham line on a numpy array (avoids cv2 dependency)."""
    x0, y0 = int(p0[0]), int(p0[1])
    x1, y1 = int(p1[0]), int(p1[1])
    h, w = frame.shape[:2]

    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    half = thickness // 2

    while True:
        for tx in range(-half, half + 1):
            for ty in range(-half, half + 1):
                px, py = x0 + tx, y0 + ty
                if 0 <= px < w and 0 <= py < h:
                    frame[py, px] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def _draw_rect(frame: np.ndarray, p0: tuple, p1: tuple, color: tuple, filled: bool = False, thickness: int = 1) -> None:
    x0, y0 = max(0, int(p0[0])), max(0, int(p0[1]))
    x1, y1 = min(frame.shape[1] - 1, int(p1[0])), min(frame.shape[0] - 1, int(p1[1]))
    if filled:
        frame[y0:y1 + 1, x0:x1 + 1] = color
    else:
        for t in range(thickness):
            if y0 + t < frame.shape[0]:
                frame[y0 + t, x0:x1 + 1] = color
            if y1 - t >= 0:
                frame[y1 - t, x0:x1 + 1] = color
            if x0 + t < frame.shape[1]:
                frame[y0:y1 + 1, x0 + t] = color
            if x1 - t >= 0:
                frame[y0:y1 + 1, x1 - t] = color


def _draw_circle(frame: np.ndarray, centre: tuple, radius: int, color: tuple) -> None:
    cx, cy = int(centre[0]), int(centre[1])
    h, w = frame.shape[:2]
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                px, py = cx + dx, cy + dy
                if 0 <= px < w and 0 <= py < h:
                    frame[py, px] = color


def _put_text(frame: np.ndarray, text: str, pos: tuple, color: tuple, scale: float = 1.0) -> None:
    """Draw text using PIL (available everywhere Streamlit is). Frame must be RGB."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        pil_img = Image.fromarray(frame)
        draw = ImageDraw.Draw(pil_img)
        font_size = max(8, int(14 * scale))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        draw.text(pos, text, fill=(color[0], color[1], color[2]), font=font)
        frame[:] = np.array(pil_img)
    except Exception:
        pass  # text is purely cosmetic — silently skip if PIL unavailable


def _put_text_bgr(frame: np.ndarray, text: str, pos: tuple, color_bgr: tuple, scale: float = 1.0) -> None:
    """Draw text on a BGR frame — swaps to RGB for PIL, then swaps back."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        rgb = frame[..., ::-1].copy()
        pil_img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil_img)
        font_size = max(8, int(14 * scale))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        r, g, b = color_bgr[2], color_bgr[1], color_bgr[0]  # BGR → RGB
        draw.text(pos, text, fill=(r, g, b), font=font)
        frame[:] = np.array(pil_img)[..., ::-1]
    except Exception:
        pass


def make_simulation_frame(frame_index: int, width: int = 960, height: int = 540) -> np.ndarray:
    """Create a synthetic navigation scene using pure NumPy + PIL — no OpenCV needed.

    Returns a BGR array to stay consistent with cv2.VideoCapture frames.
    """
    # Store as BGR (matching cv2 convention used everywhere else in the pipeline)
    frame = np.full((height, width, 3), (34, 39, 46), dtype=np.uint8)   # dark bg BGR

    # Ground plane
    horizon = int(height * 0.42)
    frame[horizon:, :] = (45, 52, 58)  # BGR

    # Perspective lane lines
    centre_x = width // 2
    for offset in (-260, -120, 120, 260):
        end_x = centre_x + offset
        _draw_line(frame, (centre_x, horizon), (end_x, height - 1), (90, 100, 108), thickness=2)

    # Pulsing waypoint dot (BGR: light blue)
    pulse = int(10 * math.sin(frame_index / 12.0))
    _draw_circle(frame, (centre_x, horizon + 20 + pulse), 5, (255, 180, 120))

    # Label — text uses PIL which expects RGB, so we swap, draw, swap back
    _put_text_bgr(frame, "SIMULATED CAMERA FEED", (24, height - 36), (230, 220, 210))

    return frame
