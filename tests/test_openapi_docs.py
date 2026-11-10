"""Every API operation has a written summary or description in the OpenAPI document (D8)."""

from server.backend_api import app

_GENERATED = ("Get ", "Post ", "Put ", "Patch ", "Delete ")


def test_every_api_operation_is_described():
    spec = app.openapi()
    bare = [(m.upper(), p) for p, ops in spec["paths"].items() for m, op in ops.items()
            if not (op.get("description") or "").strip() and op.get("summary", "").startswith(_GENERATED)]
    assert bare == []
