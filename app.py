"""
Cloud entry point for Streamlit Community Cloud deployment.
Streamlit Cloud runs this file from the repo root.
All project modules (vision, navigation, feedback, ui) are now at repo root level.
"""

import sys
from pathlib import Path

# Add repo root to path so all internal imports resolve
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.streamlit_app import main  # noqa: E402

main()
