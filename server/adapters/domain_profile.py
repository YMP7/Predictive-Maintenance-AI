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
    # Synthetic pre-training generator method name on DomainDatasetGenerator, if any.
    pretrain_generator: Optional[str] = None


# The domain whose model backs the default (benchmark) pipeline.
PRIMARY_DOMAIN = "cmapss"

DOMAIN_PROFILES: Dict[str, DomainProfile] = {
    "cmapss": DomainProfile("cmapss", ("best_model.pt", "cmapss_world_model.pt"), run_to_failure=True),
    "laptop": DomainProfile("laptop", ("laptop_world_model.pt",), pretrain_generator="generate_laptop_windows"),
    "mobile": DomainProfile("mobile", ("mobile_world_model.pt",), pretrain_generator="generate_mobile_windows"),
    "server": DomainProfile("server", ("server_world_model.pt",), pretrain_generator="generate_server_windows"),
}


def get_profile(domain: str) -> DomainProfile:
    """Profile for `domain`; unknown domains get the live-domain default."""
    return DOMAIN_PROFILES.get(domain) or DomainProfile(domain, (f"{domain}_world_model.pt",))
