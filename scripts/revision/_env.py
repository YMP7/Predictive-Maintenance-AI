"""Shared setup for revision scripts: project root on sys.path + Windows cert-store workaround."""
import ssl, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# shortcut: myenv's ssl aborts on a malformed Windows-store cert at aiohttp import;
# these offline scripts skip unreadable stores. Remove once the cert store is repaired.
_orig = ssl.SSLContext._load_windows_store_certs
def _safe(self, storename, purpose):
    try:
        _orig(self, storename, purpose)
    except ssl.SSLError:
        pass
ssl.SSLContext._load_windows_store_certs = _safe
