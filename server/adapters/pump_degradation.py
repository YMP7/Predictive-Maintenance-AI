"""
Simulated run-to-failure model for the Modbus motor-pump.

There is no real pump failure data in this project, so the pump's RUL model is trained on
runs generated here. Everything derived from this module is SIMULATED and is labelled so
wherever it is shown. It is the single source of the pump's wear behaviour: the training
set (server/atlas/train_pump_rul.py) and the live ModbusSimulator run-to-failure mode both
call `registers_at`, so the model sees the same register values in training and in the demo.

Wear model, per unit:
  - life L cycles, drawn per unit
  - wear d(t) in [0, 1] = a * (t / L) + (1 - a) * (t / L) ** p
      a slow linear part (bearing surface wear) plus an accelerating part (spalling),
      with a and p drawn per unit
  - load factor around 1.0, a slow AR(1) walk: an operating condition that moves the
    channels without being wear

At d = 1 the channels reach the simulator's existing 'degraded' state (about 78 degC,
5.6 mm/s, 22 A, 3520 rpm, 1.8 bar, power factor 0.72); at d = 0 they sit at 'nominal'.
Values are quantised to holding-register integers exactly as the simulator serves them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

from server.adapters.modbus_adapter import DEFAULT_REGISTER_MAP

FEATURES: Tuple[str, ...] = tuple(c.name for c in DEFAULT_REGISTER_MAP)
MAX_RUL_CAP = 125.0  # same piecewise-linear target cap as C-MAPSS
LIFE_RANGE = (160, 360)


@dataclass(frozen=True)
class PumpUnit:
    """One simulated pump's fixed traits."""
    life: int
    linear_share: float   # a
    exponent: float       # p
    temp_offset: float    # degC, unit-to-unit spread
    vib_offset: float     # mm/s


def draw_unit(rng: np.random.Generator) -> PumpUnit:
    return PumpUnit(
        life=int(rng.integers(LIFE_RANGE[0], LIFE_RANGE[1] + 1)),
        linear_share=float(rng.uniform(0.10, 0.30)),
        exponent=float(rng.uniform(3.0, 6.0)),
        temp_offset=float(rng.normal(0.0, 1.5)),
        vib_offset=float(rng.normal(0.0, 0.10)),
    )


def wear(unit: PumpUnit, cycle: int) -> float:
    f = min(1.0, max(0.0, cycle / unit.life))
    return unit.linear_share * f + (1.0 - unit.linear_share) * f ** unit.exponent


def next_load(load: float, rng: np.random.Generator) -> float:
    """Slow AR(1) walk of the load factor, kept in [0.85, 1.10]."""
    return float(np.clip(1.0 + 0.97 * (load - 1.0) + rng.normal(0.0, 0.012), 0.85, 1.10))


def registers_at(d: float, load: float, rng: np.random.Generator, unit: PumpUnit | None = None) -> List[int]:
    """Holding-register integers (default register map order) at wear d and load factor `load`."""
    t_off = unit.temp_offset if unit else 0.0
    v_off = unit.vib_offset if unit else 0.0
    temp = 45.0 + 33.0 * d + 20.0 * (load - 1.0) + t_off + rng.normal(0.0, 0.6)
    vib = 1.25 + 4.4 * d ** 1.3 + 0.5 * (load - 1.0) + v_off + rng.normal(0.0, 0.06)
    cur = 14.2 * load + 7.8 * d + rng.normal(0.0, 0.25)
    rpm = 3600.0 - 80.0 * d - 150.0 * (load - 1.0) + rng.normal(0.0, 12.0)
    bar = 3.2 * load - 1.4 * d + rng.normal(0.0, 0.04)
    pf = 0.88 - 0.16 * d + rng.normal(0.0, 0.01)
    eng = (temp, vib, cur, rpm, bar, pf)
    return [max(0, int(round((v - c.offset) / c.scale))) for v, c in zip(eng, DEFAULT_REGISTER_MAP)]


def normalise(registers: Sequence[int]) -> List[float]:
    """Register integers to the [0, 1] features the adapters emit (same scale, offset and range)."""
    out = []
    for raw, c in zip(registers, DEFAULT_REGISTER_MAP):
        eng = float(raw) * c.scale + c.offset
        span = c.max_val - c.min_val
        out.append(float(np.clip((eng - c.min_val) / (span if abs(span) > 1e-6 else 1.0), 0.0, 1.0)))
    return out


def simulate_unit(rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """One run to failure: features (life, 6) in [0, 1] and capped RUL labels (life,)."""
    unit = draw_unit(rng)
    load = float(rng.uniform(0.92, 1.05))
    rows, rul = [], []
    for cycle in range(1, unit.life + 1):
        load = next_load(load, rng)
        rows.append(normalise(registers_at(wear(unit, cycle), load, rng, unit)))
        rul.append(min(float(unit.life - cycle), MAX_RUL_CAP))
    return np.asarray(rows, dtype=np.float32), np.asarray(rul, dtype=np.float32)


def simulate_fleet(n_units: int, seed: int) -> List[Tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed)
    return [simulate_unit(rng) for _ in range(n_units)]


def windows(fleet: Sequence[Tuple[np.ndarray, np.ndarray]], seq_len: int = 30) -> Tuple[np.ndarray, np.ndarray]:
    """Every sliding window of every unit, with the RUL at the window's last cycle."""
    X, y = [], []
    for feats, rul in fleet:
        for end in range(seq_len, len(feats) + 1):
            X.append(feats[end - seq_len:end])
            y.append(rul[end - 1])
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32)


def population_mean(seed: int = 7, n_units: int = 40) -> np.ndarray:
    """Per-feature mean over a simulated fleet: the occlusion baseline for attribution."""
    return np.concatenate([f for f, _ in simulate_fleet(n_units, seed)]).mean(axis=0)
