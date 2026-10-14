"""Vercel serverless entrypoint for DealScreener.

Vercel's Python runtime serves the ASGI app named `app` from this module.
DEALSCREENER_DATA points at /tmp (the only writable dir on serverless);
app.py cold-start generates the fictional sample OMs there on first
invocation. Analysis itself is stateless per-PDF (tempfile), so uploads
work fine on serverless.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEALSCREENER_DATA", "/tmp/dealscreener-data")
os.environ.setdefault("PROVIDER", "local")

from app import app  # noqa: E402,F401  (Vercel serves this ASGI app)
