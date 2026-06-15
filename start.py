"""
One-command launcher for the Assistive Navigation System.
Works on Windows, macOS, and Linux.

Usage:  python start.py
        (or double-click start.bat on Windows / bash start.sh on Mac/Linux)
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).resolve().parent
REQ            = ROOT / "requirements.txt"
SAMPLES_MARKER = ROOT / "samples" / "left_person_right_vehicle.avi"
APP            = ROOT / "ui" / "streamlit_app.py"
PORT           = 8501

# Windows MAX_PATH: if the project path is too long, put venv in home folder.
_WORST_TAIL = r"\.venv\Lib\site-packages\pkg_resources\tests\data\my-test-package_unpacked-egg\my_test_package-1.0-py3.7.egg"

def _pick_venv_dir() -> Path:
    local = ROOT / ".venv"
    if sys.platform != "win32" or len(str(local)) + len(_WORST_TAIL) <= 255:
        return local
    safe = Path.home() / ".assistive_nav_venv"
    print(f"  [INFO] Long path detected — venv placed at: {safe}")
    return safe

VENV = _pick_venv_dir()
VENV_PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


# ── Helpers ────────────────────────────────────────────────────────────────
def banner(msg: str) -> None:
    print(f"\n  >>> {msg}")


def run(cmd: list, **kwargs) -> None:
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed: {' '.join(str(c) for c in cmd)}")
        sys.exit(result.returncode)


# ── Step 1: Python version ──────────────────────────────────────────────────
def check_python_version() -> None:
    if sys.version_info < (3, 10):
        print(
            f"\n[ERROR] Python 3.10+ required. You have "
            f"{sys.version_info.major}.{sys.version_info.minor}.\n"
            "  Download: https://www.python.org/downloads/"
        )
        sys.exit(1)
    print(f"  [OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


# ── Step 2: Venv ────────────────────────────────────────────────────────────
def _venv_works() -> bool:
    if not VENV_PYTHON.exists():
        return False
    r = subprocess.run([str(VENV_PYTHON), "-c", "import sys"], capture_output=True)
    return r.returncode == 0


def ensure_venv() -> None:
    if _venv_works():
        print(f"  [OK] Virtual environment ready.")
        return
    if VENV.exists():
        banner("Virtual environment broken — rebuilding…")
        shutil.rmtree(VENV, ignore_errors=True)
    else:
        banner("Creating virtual environment…")
    run([sys.executable, "-m", "venv", str(VENV)])
    if not _venv_works():
        print("\n[ERROR] Could not create virtual environment.")
        sys.exit(1)
    print("  [OK] Virtual environment created.")


# ── Step 3: Packages ────────────────────────────────────────────────────────
def _packages_ready() -> bool:
    r = subprocess.run(
        [str(VENV_PYTHON), "-c", "import streamlit, cv2, ultralytics"],
        capture_output=True,
    )
    return r.returncode == 0


def install_requirements() -> None:
    if _packages_ready():
        print("  [OK] All packages already installed.")
        return
    banner("Installing packages — 2-4 minutes on first run…")
    print("  (streamlit, opencv, ultralytics/YOLO11, plotly, pyttsx3...)\n")
    run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"])
    pip_cmd = [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQ), "--no-build-isolation"]
    if sys.platform == "win32":
        tmp = Path.home() / ".pip_tmp"
        tmp.mkdir(exist_ok=True)
        env = {**os.environ, "TMPDIR": str(tmp), "TEMP": str(tmp), "TMP": str(tmp)}
        result = subprocess.run(pip_cmd, env=env)
    else:
        result = subprocess.run(pip_cmd)
    if result.returncode != 0:
        print("\n[ERROR] pip install failed.")
        print("  Try enabling Windows long paths (Admin PowerShell):")
        print("  Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name 'LongPathsEnabled' -Value 1")
        sys.exit(1)
    print("\n  [OK] All packages installed.")


# ── Step 4: Samples ─────────────────────────────────────────────────────────
def ensure_samples() -> None:
    if SAMPLES_MARKER.exists():
        print("  [OK] Sample videos ready.")
        return
    banner("Generating sample videos…")
    run([str(VENV_PYTHON), str(ROOT / "scripts" / "generate_sample_videos.py")])
    print("  [OK] Sample videos generated.")


# ── Step 5: Port check ──────────────────────────────────────────────────────
def _find_free_port(preferred: int) -> int:
    """Return preferred port if free, otherwise find the next free one."""
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    return preferred


# ── Step 6: Launch ──────────────────────────────────────────────────────────
def launch_app() -> None:
    port = _find_free_port(PORT)
    url  = f"http://localhost:{port}"

    print()
    print("=" * 52)
    print(f"  Dashboard:  {url}")
    print( "  Stop:       Ctrl+C")
    print("=" * 52)
    print()

    cmd = [
        str(VENV_PYTHON), "-m", "streamlit", "run", str(APP),
        "--server.address",   "0.0.0.0",   # bind all interfaces, not just localhost
        "--server.port",      str(port),
        "--server.headless",  "true",       # prevent Streamlit's own browser-open (we do it)
        "--browser.gatherUsageStats", "false",
    ]

    # Start Streamlit as a background process so we can open the browser after it's ready
    if sys.platform == "win32":
        proc = subprocess.Popen(cmd)
    else:
        proc = subprocess.Popen(cmd)

    # Wait until the port is actually accepting connections, then open the browser
    _wait_and_open(url, port, proc)

    # Wait for the process to finish (Ctrl+C)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\n  [Stopped]")


def _wait_and_open(url: str, port: int, proc: subprocess.Popen) -> None:
    """Poll until Streamlit is accepting connections, then open the browser."""
    print("  Waiting for server to start", end="", flush=True)
    for _ in range(40):           # wait up to 20 seconds
        time.sleep(0.5)
        print(".", end="", flush=True)
        if proc.poll() is not None:
            print("\n[ERROR] Streamlit exited unexpectedly.")
            sys.exit(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            try:
                s.connect(("127.0.0.1", port))
                print(f"\n  [OK] Server is up.\n")
                webbrowser.open(url)
                return
            except (ConnectionRefusedError, OSError):
                continue
    # Server didn't respond in time — open the browser anyway and let user retry
    print(f"\n  [INFO] Server taking longer than expected.")
    print(f"  Open manually: {url}\n")
    webbrowser.open(url)


# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(ROOT)

    print()
    print("=" * 52)
    print("  AI-Powered Assistive Navigation System")
    print("  MSc Dissertation Prototype")
    print("=" * 52)
    print()

    check_python_version()
    ensure_venv()
    install_requirements()
    ensure_samples()
    launch_app()
