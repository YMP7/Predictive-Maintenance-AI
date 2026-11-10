"""Shop-floor machine registry: the single reader and writer of config/machines.json.

Every module that needs the machine list or per-machine thresholds reads it through
here, so admin edits made through the API apply everywhere without a restart.
"""
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Callable, Dict

from pydantic import BaseModel, Field, model_validator

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "config" / "machines.json"
MACHINE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"
_write_lock = threading.Lock()


class Limit(BaseModel):
    warning: float = Field(ge=0)
    critical: float = Field(ge=0)

    @model_validator(mode="after")
    def critical_above_warning(self):
        if self.critical <= self.warning:
            raise ValueError("critical must be greater than warning")
        return self


class Thresholds(BaseModel):
    vibration: Limit
    temperature: Limit
    current: Limit


class MachineConfig(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: str = Field(min_length=1, max_length=40)
    location: str = Field(default="", max_length=80)
    thresholds: Thresholds


class NewMachine(MachineConfig):
    machine_id: str = Field(pattern=MACHINE_ID_PATTERN)


def registry_exists() -> bool:
    return REGISTRY_PATH.exists()


def load_machines() -> Dict[str, dict]:
    """Return {machine_id: config}. A missing file means no registered machines."""
    if not REGISTRY_PATH.exists():
        return {}
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("machines", {})


def save_machines(machines: Dict[str, dict]) -> None:
    """Write atomically so a crash mid-write never leaves a half-written registry."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=REGISTRY_PATH.parent, prefix=".machines.", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"machines": machines}, f, indent=2)
            f.write("\n")
        os.replace(tmp, REGISTRY_PATH)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def mutate(change: Callable[[Dict[str, dict]], None]) -> Dict[str, dict]:
    """Apply change(machines) under a lock and persist it. change may raise to abort."""
    with _write_lock:
        machines = load_machines()
        change(machines)
        save_machines(machines)
        return machines
