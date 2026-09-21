"""Shared pytest configuration.

Environment variables come from `.env` for the whole test session; library
modules under `server/` no longer load dotenv at import time so that tests can
patch the environment.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
