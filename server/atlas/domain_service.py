"""
ATLAS Domain Service — Live domain adapter management + persistence
==================================================================
Manages all active domain adapters, routes telemetry through the ATLAS
cognition pipeline (World Model → RUL Engine), and persists domain
snapshots to atlas_domain_snapshots for the dashboard.

This runs as a background thread alongside the existing DataService,
keeping the two systems independently operable during the transition period.

Month 1 scope: CMAPSSAdapter only. Month 6 will add Laptop/Mobile/Server.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from server.adapters.base_adapter import NormalizedReading
from server.adapters.cmapss_adapter import CMAPSSAdapter
from server.atlas.rul_engine import RULEngine, RULPrediction
from server.database import pool

logger = logging.getLogger("ATLAS.DomainService")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DomainService:
    """
    Manages ATLAS domain adapters and the LSTM-powered prediction pipeline.

    The service maintains a per-domain RULEngine instance and an in-memory
    snapshot cache keyed by (domain, machine_id). The dashboard fetches
    from this cache via the /api/atlas/ endpoints.

    Usage (from backend_api.py)
    ---------------------------
        service = get_domain_service()
        service.start()                          # starts background polling
        snapshot = service.get_snapshot("cmapss", "unit_1")
        all_domains = service.get_all_domain_status()
    """

    # Polling interval in seconds between adapter reads during streaming
    POLL_INTERVAL_S = 0.5

    def __init__(self) -> None:
        self._adapters: Dict[str, object] = {}          # domain_id -> adapter
        self._engines: Dict[str, RULEngine] = {}        # domain_id -> RULEngine
        self._snapshots: Dict[str, Dict] = {}           # "domain/machine_id" -> snapshot
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Adapter registration
    # ------------------------------------------------------------------

    def register_cmapss(
        self,
        subset: str = "FD001",
        max_units: Optional[int] = 10,
    ) -> bool:
        """
        Register the C-MAPSS adapter. Returns True if dataset files are found.
        Silently logs a warning and skips if files are missing (non-fatal).
        """
        try:
            from server.adapters.cmapss_adapter import CMAPSSAdapter, DatasetNotFoundError
            adapter = CMAPSSAdapter(subset=subset, split="train", max_units=max_units)
            adapter.connect()
            engine = RULEngine(domain="cmapss", cycles_per_day=1.0)
            with self._lock:
                self._adapters["cmapss"] = adapter
                self._engines["cmapss"] = engine
            logger.info(
                f"C-MAPSS adapter registered: {adapter.n_units} units (subset={subset})"
            )
            return True
        except Exception as e:
            logger.warning(
                f"C-MAPSS adapter not registered: {e}\n"
                "Download the dataset and place files in data/cmapss/ to enable."
            )
            return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background streaming loop."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("ATLAS DomainService started.")

    def stop(self) -> None:
        """Stop the streaming loop and disconnect all adapters."""
        with self._lock:
            self._is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        for adapter in self._adapters.values():
            try:
                adapter.disconnect()
            except Exception:
                pass
        logger.info("ATLAS DomainService stopped.")

    # ------------------------------------------------------------------
    # Streaming loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        while True:
            with self._lock:
                if not self._is_running:
                    break
                adapters = dict(self._adapters)
                engines = dict(self._engines)

            for domain_id, adapter in adapters.items():
                engine = engines.get(domain_id)
                if engine is None:
                    continue
                try:
                    for machine_id in adapter.machine_ids:
                        reading: NormalizedReading = adapter.get_reading(machine_id)
                        prediction: RULPrediction = engine.update(machine_id, reading)
                        self._update_snapshot(domain_id, machine_id, reading, prediction)
                except Exception as e:
                    logger.error(f"[{domain_id}] Streaming error: {e}")

            time.sleep(self.POLL_INTERVAL_S)

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    def _update_snapshot(
        self,
        domain: str,
        machine_id: str,
        reading: NormalizedReading,
        prediction: RULPrediction,
    ) -> None:
        snapshot = {
            "domain": domain,
            "machine_id": machine_id,
            "timestamp": _utc_now(),
            "health_index": reading.health_index,
            "cycle": reading.cycle,
            "rul_label": reading.rul_label,
            "rul_cycles": prediction.rul_cycles,
            "rul_days": prediction.rul_days,
            "confidence": prediction.confidence,
            "uncertainty": prediction.uncertainty,
            "status": prediction.status,
            "using_lstm": prediction.using_lstm,
            "features": reading.features,
            "operational_ctx": reading.operational_ctx,
            "adapter_status": reading.adapter_status,
            "metadata": reading.metadata,
        }
        key = f"{domain}/{machine_id}"
        with self._lock:
            self._snapshots[key] = snapshot

        # Persist to DB (fire-and-forget — don't block the loop)
        self._persist_snapshot_async(snapshot)

    def _persist_snapshot_async(self, snapshot: dict) -> None:
        def _write():
            try:
                with pool.connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO atlas_domain_snapshots
                            (time, domain, machine_id, health_index,
                             rul_cycles, rul_days, confidence, uncertainty,
                             status, using_lstm, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            snapshot["timestamp"],
                            snapshot["domain"],
                            snapshot["machine_id"],
                            snapshot["health_index"],
                            snapshot["rul_cycles"],
                            snapshot["rul_days"],
                            snapshot["confidence"],
                            snapshot["uncertainty"],
                            snapshot["status"],
                            snapshot["using_lstm"],
                            json.dumps(snapshot["metadata"]),
                        ),
                    )
                    conn.commit()
            except Exception as e:
                # Non-fatal — snapshot cache is authoritative for live reads
                logger.debug(f"Snapshot persist failed (non-fatal): {e}")

        t = threading.Thread(target=_write, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Read API (used by backend_api.py)
    # ------------------------------------------------------------------

    def get_snapshot(self, domain: str, machine_id: str) -> Optional[Dict]:
        key = f"{domain}/{machine_id}"
        with self._lock:
            return dict(self._snapshots.get(key, {})) or None

    def get_domain_snapshots(self, domain: str) -> List[Dict]:
        prefix = f"{domain}/"
        with self._lock:
            return [
                dict(v) for k, v in self._snapshots.items()
                if k.startswith(prefix)
            ]

    def get_all_domain_status(self) -> List[Dict]:
        """Summary of all active domains (for /api/atlas/domains)."""
        with self._lock:
            adapters_info = [
                a.describe() for a in self._adapters.values()
            ]
        return adapters_info

    def get_cross_domain_comparison(self) -> Dict:
        """
        All domains' latest snapshots side-by-side.
        The primary data source for the Cross-Domain Comparison Dashboard.
        """
        with self._lock:
            snapshots = dict(self._snapshots)
        result: Dict[str, List[Dict]] = {}
        for key, snap in snapshots.items():
            domain = snap["domain"]
            if domain not in result:
                result[domain] = []
            result[domain].append(snap)
        return result

    def get_engine(self, domain: str) -> Optional[RULEngine]:
        with self._lock:
            return self._engines.get(domain)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_domain_service: Optional[DomainService] = None


def get_domain_service() -> DomainService:
    global _domain_service
    if _domain_service is None:
        _domain_service = DomainService()
    return _domain_service
