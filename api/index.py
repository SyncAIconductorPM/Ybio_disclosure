"""Vercel Python serverless entry point for FastAPI."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path (Vercel function cwd varies)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.main import app  # noqa: E402

# Vercel @vercel/python looks for ASGI `app`
__all__ = ["app"]
