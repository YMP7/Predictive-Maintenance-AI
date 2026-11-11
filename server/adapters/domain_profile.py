"""
Per-domain static facts that core ATLAS code needs but must not hard-code.

Core modules ask the profile instead of branching on a domain name, so adding a
domain means adding one entry here (next to its adapter), not editing the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class DomainProfile:
    name: str
    # World-model checkpoint filenames in MODELS_DIR, first existing one wins.
    checkpoints: Tuple[str, ...]
    # True when AMKB neighbours carry ground-truth RUL (run-to-failure data).
    run_to_failure: bool = False
    # Divisor mapping rul_cycles to a 0-1 scale; None when the engine already emits 0-1.
    rul_scale: Optional[float] = None
    # Synthetic pre-training generator method name on DomainDatasetGenerator, if any.
    pretrain_generator: Optional[str] = None
    # Feature names in the column order the domain's model was trained on. The live window
    # (NormalizedReading.feature_vector) uses this same order.
    features: Tuple[str, ...] = ()
    # True when the model is trained on simulator-generated run-to-failure data (server/adapters/pump_degradation.py).
    simulated_run_to_failure: bool = False


# The domain whose model backs the default (benchmark) pipeline.
PRIMARY_DOMAIN = "cmapss"

DOMAIN_PROFILES: Dict[str, DomainProfile] = {
    "cmapss": DomainProfile("cmapss", ("best_model.pt", "cmapss_world_model.pt"), run_to_failure=True, rul_scale=125.0),
    "laptop": DomainProfile("laptop", ("laptop_world_model.pt",), pretrain_generator="generate_laptop_windows",
                             features=("cpu_usage", "memory_usage", "disk_usage", "battery_percent", "is_charging")),
    "mobile": DomainProfile("mobile", ("mobile_world_model.pt",), pretrain_generator="generate_mobile_windows",
                             features=("battery_level", "battery_temp", "battery_current", "memory_used_percent", "cpu_usage")),
    "server": DomainProfile("server", ("server_world_model.pt",), pretrain_generator="generate_server_windows",
                             features=("cpu_usage", "memory_usage", "disk_usage", "network_io_rate", "gpu_utilization")),
    # Motor-pump: RUL in cycles from a model trained on SIMULATED run-to-failure data. Live AMKB
    # neighbours carry no ground truth, so run_to_failure stays False.
    "modbus": DomainProfile("modbus", ("modbus_world_model.pt",), rul_scale=125.0, simulated_run_to_failure=True,
                            features=("temperature_c", "vibration_mms", "current_a", "speed_rpm", "pressure_bar",
                                      "power_factor")),
}


def get_profile(domain: str) -> DomainProfile:
    """Profile for `domain`; unknown domains get the live-domain default."""
    return DOMAIN_PROFILES.get(domain) or DomainProfile(domain, (f"{domain}_world_model.pt",))
