"""
scripts/check_public_boundary.py — Public/private module boundary gate
======================================================================
Proves that the public surface (Adapter SDK, adapters, conformance suite)
builds and passes WITHOUT the IP-hold modules.

Two checks:
  1. Static: no public file imports an IP-hold module (AST scan, so imports
     inside functions and try-blocks are caught too).
  2. Dynamic: the public test set runs under pytest with an import blocker
     installed. Any import of an IP-hold module raises ImportError, so a
     transitive dependency fails the run instead of passing silently.

The IP-hold list mirrors docs/PUBLIC_PRIVATE_BOUNDARY.md. Keep them in sync.

Usage:
    python scripts/check_public_boundary.py            # static + dynamic
    python scripts/check_public_boundary.py --static   # static only (no deps)
    python scripts/check_public_boundary.py -- -k modbus   # extra pytest args
"""

from __future__ import annotations

import ast
import importlib.abc
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Modules implementing the patent-candidate methods. Matching is by prefix,
# so submodules are blocked too.
IP_HOLD_MODULES = (
    "server.atlas.simulation",
    "server.atlas.decision",
    "server.atlas.machine_dna",
    "server.atlas.explain",
    "server.atlas.adaptive_context",
    "server.agent_tools",
)

# Files that make up the public surface.
PUBLIC_GLOBS = (
    "server/adapters/*.py",
    "server/atlas/__init__.py",
    "server/atlas/world_model.py",
    "server/atlas/rul_engine.py",
)

PUBLIC_TESTS = (
    "tests/test_adapter_conformance.py",
    "tests/test_modbus_adapter.py",
    "tests/test_adapters.py",
)


def _is_ip_hold(name: str) -> bool:
    return any(name == m or name.startswith(m + ".") for m in IP_HOLD_MODULES)


def _imported_names(tree: ast.AST) -> list[tuple[int, str]]:
    names: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend((node.lineno, a.name) for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append((node.lineno, node.module))
            # `from server.atlas import explain` imports a submodule by name
            names.extend((node.lineno, f"{node.module}.{a.name}") for a in node.names)
    return names


def static_check() -> list[str]:
    files = sorted({p for g in PUBLIC_GLOBS + PUBLIC_TESTS for p in PROJECT_ROOT.glob(g)})
    violations = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, name in _imported_names(tree):
            if _is_ip_hold(name):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}: imports IP-hold module '{name}'")
    print(f"[static] scanned {len(files)} public files, {len(violations)} violation(s)")
    return violations


class _IPHoldBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if _is_ip_hold(fullname):
            raise ImportError(f"IP-hold module '{fullname}' is not available in the public build")
        return None


def dynamic_check(extra_args: list[str]) -> int:
    import pytest

    sys.meta_path.insert(0, _IPHoldBlocker())
    for mod in [m for m in sys.modules if _is_ip_hold(m)]:
        del sys.modules[mod]
    args = [str(PROJECT_ROOT / t) for t in PUBLIC_TESTS] + ["-q", "-p", "no:cacheprovider", *extra_args]
    print(f"[dynamic] running public test set with IP-hold imports blocked: {list(PUBLIC_TESTS)}")
    return int(pytest.main(args))


def main(argv: list[str]) -> int:
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    violations = static_check()
    for v in violations:
        print("  " + v)
    if violations:
        return 1
    if "--static" in argv:
        return 0
    return dynamic_check(extra)


if __name__ == "__main__":
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    sys.exit(main(sys.argv[1:]))
