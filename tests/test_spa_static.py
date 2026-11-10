"""The SPA catch-all route must never serve files from outside client/dist."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    not (PROJECT_ROOT / "client" / "dist").exists(),
    reason="SPA route is only mounted when client/dist is built",
)


@pytest.mark.parametrize("url", [
    "/..%2F..%2Fserver%2Fauth.py",
    "/%2E%2E/%2E%2E/server/auth.py",
    "/" + (PROJECT_ROOT / "server" / "auth.py").as_posix(),
])
def test_spa_route_blocks_path_traversal(url):
    from server.integrated_server import app

    res = TestClient(app).get(url)
    # Falls back to index.html (or 404); never the source file.
    assert "def get_current_user" not in res.text
