"""Tests for the SPA static file handler in server/integrated_server.py."""
import asyncio

import pytest

from server.integrated_server import app, client_dist


def _get(path: str):
    """Issue a raw ASGI GET so the path is not normalized by an HTTP client."""
    captured = {}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]
        elif message["type"] == "http.response.body":
            captured.setdefault("body", b"")
            captured["body"] += message.get("body", b"")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    return captured


@pytest.mark.skipif(not client_dist.exists(), reason="frontend build not present")
@pytest.mark.parametrize(
    "path",
    [
        "/../../../../../../etc/passwd",
        "/../../.env",
        "/assets/../../../../../../etc/hostname",
    ],
)
def test_spa_rejects_path_traversal(path):
    response = _get(path)
    assert response["status"] == 404
    assert b"root:x:" not in response.get("body", b"")


@pytest.mark.skipif(not client_dist.exists(), reason="frontend build not present")
def test_spa_serves_index_for_unknown_route():
    response = _get("/dashboard")
    assert response["status"] == 200
    assert b"<!doctype html>" in response["body"].lower()
