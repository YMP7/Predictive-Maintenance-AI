"""
Laptop Telemetry Streamer — Month 6 Week 2
============================================
Polls the LaptopAdapter every POLL_INTERVAL seconds and writes each reading
into the AMKB as a stored experience (domain="laptop", true_rul=None).

This is a standalone script that can be run independently of the integrated
server. It validates the full adapter → RULEngine → AMKB storage pipeline
for the laptop domain using EMA fallback (no trained WorldModel).

Usage:
    python scripts/stream_laptop.py                    # Default: 5s interval, run forever
    python scripts/stream_laptop.py --interval 10      # 10s interval
    python scripts/stream_laptop.py --max-readings 50  # Stop after 50 readings
"""

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from server.adapters.laptop_adapter import LaptopAdapter
from server.atlas.amkb import AMKB
from server.atlas.rul_engine import RULEngine
from server.atlas.world_model import WorldModelConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ATLAS.LaptopStreamer")

# Graceful shutdown
_running = True

def _handle_sigint(sig, frame):
    global _running
    logger.info("Received SIGINT — shutting down gracefully...")
    _running = False

signal.signal(signal.SIGINT, _handle_sigint)


def main():
    parser = argparse.ArgumentParser(description="Stream laptop telemetry into AMKB")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Polling interval in seconds (default: 5)")
    parser.add_argument("--max-readings", type=int, default=None,
                        help="Stop after N readings (default: run forever)")
    args = parser.parse_args()

    # 1. Initialize adapter
    adapter = LaptopAdapter()
    adapter.connect()
    machine_id = adapter.machine_ids[0]  # "laptop_local"

    # 2. Initialize RULEngine (EMA fallback — no trained laptop model)
    engine = RULEngine(domain="laptop", cycles_per_day=0.14)

    # 3. Initialize AMKB
    amkb = AMKB()

    logger.info(f"Starting laptop telemetry stream: interval={args.interval}s, "
                f"max_readings={args.max_readings or 'unlimited'}")
    logger.info(f"RUL engine mode: {'LSTM' if engine.using_lstm else 'EMA fallback'}")

    count = 0
    try:
        while _running:
            # Poll the adapter
            reading = adapter.get_reading(machine_id)

            # Feed to RULEngine for prediction + sliding window
            prediction = engine.update(machine_id, reading)

            # Store in AMKB
            state_vector = prediction.state_vector
            if state_vector is None:
                # EMA fallback doesn't produce state vectors — use a zero vector
                # so the experience is still stored (it won't be useful for
                # cosine retrieval until a trained model exists, but it preserves
                # the raw reading metadata for future reprocessing)
                import numpy as np
                state_vector = np.zeros(32, dtype=np.float32)

            exp_id = amkb.store_experience(
                domain="laptop",
                machine_id=machine_id,
                state_vector=state_vector,
                cycle=reading.cycle,
                event_type="normal",
                true_rul=None,  # Live domain — no known failure point
                predicted_rul=prediction.rul_cycles,
                health_index=reading.health_index,
                metadata={
                    "features": reading.features,
                    "raw_features": reading.raw_features,
                    "adapter_status": reading.adapter_status,
                    "rul_days": prediction.rul_days,
                    "confidence": prediction.confidence,
                    "status": prediction.status,
                    "using_lstm": prediction.using_lstm,
                },
            )

            count += 1
            logger.info(
                f"[{count}] Stored: health={reading.health_index:.4f} "
                f"rul_days={prediction.rul_days:.1f} "
                f"confidence={prediction.confidence:.4f} "
                f"status={prediction.status} "
                f"exp_id={exp_id}"
            )

            if args.max_readings and count >= args.max_readings:
                logger.info(f"Reached max readings ({args.max_readings}). Stopping.")
                break

            time.sleep(args.interval)

    finally:
        adapter.disconnect()
        logger.info(f"Laptop streamer stopped after {count} readings.")


if __name__ == "__main__":
    main()
