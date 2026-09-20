"""Lenny Growth Assistant — FastAPI Application Package."""

import sys
from pathlib import Path

# Ensure repository root is on sys.path so root packages like `ingestion` resolve
# regardless of current working directory (e.g. Render rootDir: backend)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

__version__ = "0.1.0"

