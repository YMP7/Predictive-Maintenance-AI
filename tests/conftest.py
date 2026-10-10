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


def pytest_addoption(parser):
    parser.addoption(
        "--adapter",
        action="append",
        default=[],
        help=(
            "Restrict the adapter conformance suite to the given fixture id(s), "
            "e.g. --adapter modbus. Repeatable. Non-parametrized guardrail tests always run."
        ),
    )


def pytest_collection_modifyitems(config, items):
    selected_adapters = config.getoption("--adapter")
    if not selected_adapters:
        return
    keep, drop = [], []
    for item in items:
        callspec = getattr(item, "callspec", None)
        param = callspec.params.get("adapter_instance") if callspec else None
        (drop if param is not None and param not in selected_adapters else keep).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
