"""
RUL for machines onboarded with a sensor profile (the Modbus motor-pump today).

A profiled machine's window lives in its ConfigurableAdapter, in the profile's own channel
order and value ranges. A trained domain model expects a fixed column order and scale
(DomainProfile.features). `model_window` returns the window in the model's layout, or the
reason it cannot: a profile that does not match the trained layout gets no prediction
rather than a wrong one.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.adapters.domain_profile import get_profile

SEQ_LEN = 30


def expected_ranges(domain: str) -> Optional[Dict[str, Tuple[float, float]]]:
    """Engineering range each feature was scaled with in training, when the domain fixes one."""
    if get_profile(domain).simulated_run_to_failure:
        from server.adapters.modbus_adapter import DEFAULT_REGISTER_MAP

        return {c.name: (c.min_val, c.max_val) for c in DEFAULT_REGISTER_MAP}
    return None


def model_window(adapter: Any) -> Tuple[Optional[List[List[float]]], Optional[str]]:
    """(window in the trained model's column order, None) or (None, why there is no prediction)."""
    sp = adapter.profile
    features = get_profile(sp.domain).features
    if not features:
        return None, f"No trained model layout for domain '{sp.domain}'."
    by_feature = {c.feature: (i, c) for i, c in enumerate(sp.channels)}
    missing = [f for f in features if f not in by_feature]
    if missing:
        return None, f"The sensor profile lacks channels the model was trained on: {', '.join(missing)}."
    ranges = expected_ranges(sp.domain) or {}
    off = [f for f in features if f in ranges
           and (abs(by_feature[f][1].valid_min - ranges[f][0]) > 1e-9 or abs(by_feature[f][1].valid_max - ranges[f][1]) > 1e-9)]
    if off:
        return None, f"The sensor profile scales {', '.join(off)} differently from the trained model."
    rows = adapter.window()
    if len(rows) < SEQ_LEN:
        return None, f"Warming up: {len(rows)}/{SEQ_LEN} readings."
    cols = [by_feature[f][0] for f in features]
    return [[row[i] for i in cols] for row in rows[-SEQ_LEN:]], None


@functools.lru_cache(maxsize=8)
def _metadata(path: str, mtime: float) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def model_metadata(domain: str) -> Dict[str, Any]:
    from server.atlas.world_model import MODELS_DIR

    p = Path(MODELS_DIR) / f"{domain}_model_metadata.json"
    return _metadata(str(p), p.stat().st_mtime) if p.exists() else {}


def profiled_rul(adapter: Any) -> Tuple[Optional[dict], Optional[str], bool]:
    """(rul dict for the TwinFrame, note when there is none, True when only warming up)."""
    import numpy as np

    import server.api as api
    from server.atlas.world_model import WorldModel, prepare_window

    domain = adapter.profile.domain
    profile = get_profile(domain)
    if not profile.features:
        return None, None, False
    if api._ace is not None:
        model = api._ace.get_world_model(domain, len(profile.features))
    else:  # the cognition engines start with the API; without them, read the checkpoint directly
        model = WorldModel.load_for_domain(domain)
    if model is None:
        return None, None, False
    window, reason = model_window(adapter)
    if window is None:
        return None, reason, bool(reason and reason.startswith("Warming up"))
    out = model.predict(prepare_window(np.asarray(window, dtype=np.float32), seq_len=SEQ_LEN, feature_dim=len(profile.features)))
    value = float(out.rul_pred)
    meta = model_metadata(domain)
    return ({"value": value, "unit": "cycles" if profile.rul_scale else "steps",
             # 1 sd of the error on the held-out simulated units (data/pump_rul_evaluation.json)
             "uncertainty": (meta.get("test") or {}).get("rmse"),
             "normalized": round(value / profile.rul_scale, 4) if profile.rul_scale else None,
             "confidence": None, "using_lstm": True,
             "provenance": meta.get("provenance")}, None, False)
